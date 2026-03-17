# ロギング統合パターン

structlog と例外処理を統合するパターンです。

## 基本原則

1. **すべてのエラーはログに記録する**
2. **構造化されたコンテキストを含める**
3. **ログレベルを適切に使い分ける**
4. **トレーサビリティを確保する**

## ログレベルの使い分け

| レベル | 用途 | 例 |
|-------|------|-----|
| DEBUG | 詳細なデバッグ情報 | 処理開始、中間状態 |
| INFO | 正常な処理の記録 | 処理完了、成功 |
| WARNING | 問題だが継続可能 | リトライ成功、フォールバック使用 |
| ERROR | エラー発生 | 処理失敗、例外発生 |
| CRITICAL | 致命的エラー | システム停止、データ損失 |

## structlog の基本設定

```python
from utils_core.logging import get_logger

logger = get_logger(__name__)
```

## エラーハンドリングとロギングの統合

### 基本パターン

```python
def process_data(data: list[dict]) -> list[dict]:
    """データを処理する

    Parameters
    ----------
    data : list[dict]
        処理対象のデータ

    Returns
    -------
    list[dict]
        処理結果
    """
    logger.debug("Processing started", item_count=len(data))

    try:
        result = transform(data)
        logger.info(
            "Processing completed",
            input_count=len(data),
            output_count=len(result),
        )
        return result
    except ValidationError as e:
        logger.warning(
            "Validation failed",
            error=str(e),
            field=e.field,
            value=e.value,
        )
        raise
    except DataError as e:
        logger.error(
            "Data processing failed",
            error=str(e),
            error_code=e.code.value if hasattr(e, "code") else None,
            exc_info=True,  # スタックトレースを含める
        )
        raise
```

### 例外属性のログ出力

```python
def fetch_stock_data(symbol: str) -> DataFrame:
    """株価データを取得する"""
    logger.debug("Fetching stock data", symbol=symbol)

    try:
        data = api_client.fetch(symbol)
        logger.info(
            "Stock data fetched",
            symbol=symbol,
            rows=len(data),
        )
        return data
    except DataFetchError as e:
        # 例外の属性をログに含める
        logger.error(
            "Stock data fetch failed",
            symbol=symbol,
            source=e.source,
            error_code=e.code.value,
            details=e.details,
            exc_info=True,
        )
        raise
    except RateLimitError as e:
        logger.warning(
            "Rate limit exceeded",
            symbol=symbol,
            retry_after=e.retry_after,
            source=e.source,
        )
        raise
```

## コンテキスト情報の収集

### bind でコンテキストを追加

```python
def process_order(order_id: str, user_id: str) -> Order:
    """注文を処理する"""
    # コンテキストをバインド
    log = logger.bind(
        order_id=order_id,
        user_id=user_id,
    )

    log.info("Processing order started")

    try:
        order = validate_order(order_id)
        log.debug("Order validated", status=order.status)

        result = execute_order(order)
        log.info("Order processed", result=result.status)

        return result
    except ValidationError as e:
        log.warning("Order validation failed", error=str(e))
        raise
    except OrderError as e:
        log.error(
            "Order processing failed",
            error=str(e),
            exc_info=True,
        )
        raise
```

### リクエスト ID によるトレース

```python
import uuid


def with_request_id(func):
    """リクエスト ID を付与するデコレータ"""
    @wraps(func)
    def wrapper(*args, **kwargs):
        request_id = str(uuid.uuid4())
        log = logger.bind(request_id=request_id)

        log.info("Request started")
        try:
            result = func(*args, **kwargs)
            log.info("Request completed")
            return result
        except Exception as e:
            log.error(
                "Request failed",
                error=str(e),
                error_type=type(e).__name__,
                exc_info=True,
            )
            raise

    return wrapper


@with_request_id
def handle_api_request(data: dict) -> Response:
    """API リクエストを処理"""
    # request_id は自動的にログに含まれる
    logger.debug("Processing request", data_keys=list(data.keys()))
    # ...
```

## エラーレポート用のログ

### 構造化されたエラーログ

```python
def log_error_report(
    error: Exception,
    context: dict[str, Any] | None = None,
) -> None:
    """エラーレポートをログに出力

    Parameters
    ----------
    error : Exception
        発生した例外
    context : dict[str, Any] | None
        追加のコンテキスト情報
    """
    error_data = {
        "error_type": type(error).__name__,
        "error_message": str(error),
    }

    # リッチパターンの例外の場合
    if hasattr(error, "code"):
        error_data["error_code"] = error.code.value
    if hasattr(error, "details"):
        error_data["error_details"] = error.details
    if hasattr(error, "cause") and error.cause:
        error_data["cause_type"] = type(error.cause).__name__
        error_data["cause_message"] = str(error.cause)

    # コンテキストをマージ
    if context:
        error_data.update(context)

    logger.error(
        "Error occurred",
        **error_data,
        exc_info=True,
    )
```

### 使用例

```python
try:
    result = process_complex_operation(data)
except PackageError as e:
    log_error_report(
        e,
        context={
            "operation": "process_complex_operation",
            "data_size": len(data),
            "user_id": current_user.id,
        },
    )
    raise
```

## 非同期処理でのロギング

```python
import asyncio


async def fetch_multiple(symbols: list[str]) -> dict[str, DataFrame]:
    """複数のシンボルを並列取得"""
    logger.info("Starting parallel fetch", symbol_count=len(symbols))

    results = {}
    errors = []

    async def fetch_one(symbol: str) -> tuple[str, DataFrame | None]:
        log = logger.bind(symbol=symbol)
        try:
            data = await async_fetch(symbol)
            log.debug("Fetch succeeded", rows=len(data))
            return symbol, data
        except DataFetchError as e:
            log.warning("Fetch failed", error=str(e))
            errors.append((symbol, e))
            return symbol, None

    tasks = [fetch_one(s) for s in symbols]
    fetched = await asyncio.gather(*tasks)

    for symbol, data in fetched:
        if data is not None:
            results[symbol] = data

    logger.info(
        "Parallel fetch completed",
        success_count=len(results),
        error_count=len(errors),
    )

    if errors:
        logger.warning(
            "Some fetches failed",
            failed_symbols=[s for s, _ in errors],
        )

    return results
```

## ログフォーマットの例

### 開発環境（text フォーマット）

```
2026-01-21 10:30:45.123 | INFO     | fetch_stock_data | Stock data fetched | symbol=AAPL rows=252
2026-01-21 10:30:45.456 | ERROR    | fetch_stock_data | Stock data fetch failed | symbol=INVALID error_code=DATA_NOT_FOUND
Traceback (most recent call last):
  ...
DataFetchError: [DATA_NOT_FOUND] Symbol 'INVALID' not found
```

### 本番環境（JSON フォーマット）

```json
{
  "timestamp": "2026-01-21T10:30:45.123456Z",
  "level": "info",
  "logger": "market_analysis.fetcher",
  "message": "Stock data fetched",
  "symbol": "AAPL",
  "rows": 252,
  "request_id": "abc123"
}
```

## ベストプラクティス

### DO（推奨）

```python
# 1. 構造化されたコンテキストを含める
logger.error(
    "Processing failed",
    symbol=symbol,
    error_code=e.code.value,
    attempt=attempt,
)

# 2. exc_info=True でスタックトレースを含める
logger.error("Unexpected error", exc_info=True)

# 3. 適切なログレベルを使用
logger.warning("Using fallback")  # 問題だが継続可能
logger.error("Operation failed")  # エラー発生

# 4. 成功時もログを出力
logger.info("Operation completed", result_count=len(results))
```

### DON'T（非推奨）

```python
# 1. print を使用しない
print(f"Error: {e}")  # 避ける

# 2. 文字列フォーマットを使用しない
logger.error(f"Error: {error}")  # 避ける
logger.error("Error", error=error)  # 推奨

# 3. 機密情報をログに含めない
logger.error("Auth failed", api_key=api_key)  # 絶対に避ける

# 4. 過度なログを避ける
for item in large_list:
    logger.debug("Processing item", item=item)  # ループ内は避ける
```

## 参照実装

このプロジェクトでの参照実装：

- `src/finance/utils/logging_config.py`: ロギング設定
- `src/market_analysis/core/fetcher.py`: データ取得のログ
- `.claude/rules/common-instructions.md`: ロギングの共通指示
