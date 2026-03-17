# ロギング実装パターン

構造化ログの実装パターン集です。

## 基本セットアップ

```python
from utils_core.logging import get_logger

logger = get_logger(__name__)
```

## ログレベルの使い分け

| レベル | 用途 | 例 |
|--------|------|-----|
| DEBUG | 開発時のデバッグ情報 | 変数値、処理フロー |
| INFO | 通常の操作記録 | 処理開始/完了、重要なイベント |
| WARNING | 問題の可能性 | 非推奨機能の使用、リトライ発生 |
| ERROR | エラー発生 | 例外、処理失敗 |
| CRITICAL | 致命的エラー | システム停止が必要な状態 |

## 基本パターン

### 処理の開始と完了

```python
def process_data(data: list[dict]) -> list[dict]:
    """データを処理する。"""
    logger.debug("Processing started", item_count=len(data))

    try:
        result = transform(data)
        logger.info(
            "Processing completed",
            input_count=len(data),
            output_count=len(result),
        )
        return result
    except Exception as e:
        logger.error(
            "Processing failed",
            error=str(e),
            input_count=len(data),
            exc_info=True,
        )
        raise
```

### 非同期処理

```python
async def fetch_user_data(user_id: str) -> User:
    """ユーザーデータを取得する。"""
    logger.debug("Fetching user data", user_id=user_id)

    try:
        user = await repository.find_by_id(user_id)

        if user is None:
            logger.warning("User not found", user_id=user_id)
            raise NotFoundError("User", user_id)

        logger.info("User data fetched", user_id=user_id)
        return user

    except NotFoundError:
        raise
    except Exception as e:
        logger.error(
            "Failed to fetch user data",
            user_id=user_id,
            error=str(e),
            exc_info=True,
        )
        raise
```

### バッチ処理

```python
def process_batch(items: list[Item]) -> BatchResult:
    """バッチ処理を実行する。"""
    logger.info("Batch processing started", total_items=len(items))

    success_count = 0
    error_count = 0
    errors: list[dict] = []

    for i, item in enumerate(items):
        try:
            process_item(item)
            success_count += 1

            # 進捗ログ（大量データの場合）
            if (i + 1) % 100 == 0:
                logger.debug(
                    "Batch progress",
                    processed=i + 1,
                    total=len(items),
                    success=success_count,
                    errors=error_count,
                )

        except Exception as e:
            error_count += 1
            errors.append({
                "item_id": item.id,
                "error": str(e),
            })
            logger.warning(
                "Item processing failed",
                item_id=item.id,
                error=str(e),
            )

    logger.info(
        "Batch processing completed",
        total=len(items),
        success=success_count,
        errors=error_count,
    )

    return BatchResult(
        success_count=success_count,
        error_count=error_count,
        errors=errors,
    )
```

## 構造化ログのパターン

### キーワード引数で構造化

```python
# 良い例: キーワード引数で構造化
logger.info(
    "Order processed",
    order_id=order.id,
    user_id=order.user_id,
    total_amount=order.total,
    item_count=len(order.items),
)

# 悪い例: f-string で埋め込み（検索・解析が困難）
logger.info(f"Order {order.id} processed for user {order.user_id}")
```

### コンテキスト情報の付加

```python
def process_order(order: Order) -> ProcessedOrder:
    """注文を処理する。"""
    # 共通のコンテキスト
    ctx = {
        "order_id": order.id,
        "user_id": order.user_id,
    }

    logger.info("Order processing started", **ctx)

    try:
        # 在庫確認
        logger.debug("Checking inventory", **ctx, items=len(order.items))
        check_inventory(order)

        # 支払い処理
        logger.debug("Processing payment", **ctx, amount=order.total)
        process_payment(order)

        # 完了
        logger.info("Order processed successfully", **ctx)
        return ProcessedOrder(order)

    except InsufficientInventoryError as e:
        logger.warning(
            "Insufficient inventory",
            **ctx,
            missing_items=e.missing_items,
        )
        raise
    except PaymentError as e:
        logger.error(
            "Payment processing failed",
            **ctx,
            error=str(e),
            exc_info=True,
        )
        raise
```

### リクエスト追跡

```python
import uuid

def process_request(request: Request) -> Response:
    """リクエストを処理する。"""
    request_id = str(uuid.uuid4())
    ctx = {
        "request_id": request_id,
        "method": request.method,
        "path": request.path,
    }

    logger.info("Request received", **ctx)

    try:
        response = handle_request(request)

        logger.info(
            "Request completed",
            **ctx,
            status_code=response.status_code,
            duration_ms=response.duration_ms,
        )
        return response

    except Exception as e:
        logger.error(
            "Request failed",
            **ctx,
            error=str(e),
            exc_info=True,
        )
        raise
```

## エラーログのパターン

### 例外情報の記録

```python
try:
    result = risky_operation()
except ValueError as e:
    # 予期されるエラー: WARNING + 詳細
    logger.warning(
        "Validation failed",
        error=str(e),
        input_value=input_value,
    )
    raise

except Exception as e:
    # 予期しないエラー: ERROR + スタックトレース
    logger.error(
        "Unexpected error occurred",
        error=str(e),
        error_type=type(e).__name__,
        exc_info=True,  # スタックトレースを含める
    )
    raise
```

### リトライログ

```python
async def fetch_with_retry(
    url: str,
    max_retries: int = 3,
) -> Response:
    """リトライ付きでデータを取得する。"""
    last_error: Exception | None = None

    for attempt in range(1, max_retries + 1):
        try:
            logger.debug(
                "Fetch attempt",
                url=url,
                attempt=attempt,
                max_retries=max_retries,
            )

            response = await fetch(url)

            if attempt > 1:
                logger.info(
                    "Fetch succeeded after retry",
                    url=url,
                    attempt=attempt,
                )

            return response

        except Exception as e:
            last_error = e
            logger.warning(
                "Fetch failed, will retry",
                url=url,
                attempt=attempt,
                max_retries=max_retries,
                error=str(e),
            )

            if attempt < max_retries:
                await asyncio.sleep(2 ** attempt)

    logger.error(
        "Fetch failed after all retries",
        url=url,
        max_retries=max_retries,
        error=str(last_error),
    )
    raise last_error
```

## パフォーマンスログ

### 処理時間の計測

```python
import time

def slow_operation(data: list) -> Result:
    """重い処理を実行する。"""
    start_time = time.perf_counter()

    logger.debug("Slow operation started", data_size=len(data))

    result = process(data)

    elapsed_ms = (time.perf_counter() - start_time) * 1000

    logger.info(
        "Slow operation completed",
        data_size=len(data),
        elapsed_ms=round(elapsed_ms, 2),
    )

    # 閾値を超えた場合は警告
    if elapsed_ms > 1000:
        logger.warning(
            "Slow operation took too long",
            elapsed_ms=round(elapsed_ms, 2),
            threshold_ms=1000,
        )

    return result
```

### コンテキストマネージャでの計測

```python
from contextlib import contextmanager
import time

@contextmanager
def log_duration(operation: str, **extra):
    """処理時間をログに記録するコンテキストマネージャ。"""
    start = time.perf_counter()
    logger.debug(f"{operation} started", **extra)

    try:
        yield
    finally:
        elapsed_ms = (time.perf_counter() - start) * 1000
        logger.info(
            f"{operation} completed",
            elapsed_ms=round(elapsed_ms, 2),
            **extra,
        )


# 使用例
with log_duration("Data processing", batch_id=batch_id):
    process_data(data)
```

## ログレベル別の使用例

### DEBUG

```python
# 変数値の確認
logger.debug("Input parameters", params=params)

# 処理フローの追跡
logger.debug("Entering validation phase")
logger.debug("Validation passed, proceeding to processing")

# 詳細な中間状態
logger.debug("Intermediate result", partial_result=partial)
```

### INFO

```python
# 重要な処理の開始/完了
logger.info("Server started", port=8080)
logger.info("Database migration completed", version="1.2.0")

# ビジネスイベント
logger.info("User registered", user_id=user.id)
logger.info("Order placed", order_id=order.id, total=order.total)
```

### WARNING

```python
# 非推奨機能の使用
logger.warning(
    "Deprecated function called",
    function="old_api",
    replacement="new_api",
)

# リソースの枯渇傾向
logger.warning(
    "Connection pool nearly exhausted",
    active=95,
    max=100,
)

# リトライ発生
logger.warning("Request failed, retrying", attempt=2, max=3)
```

### ERROR

```python
# 処理の失敗
logger.error(
    "Failed to process order",
    order_id=order.id,
    error=str(e),
    exc_info=True,
)

# 外部サービスのエラー
logger.error(
    "External API error",
    service="payment",
    status_code=500,
    response=response.text[:200],
)
```

### CRITICAL

```python
# システムレベルの問題
logger.critical(
    "Database connection lost",
    host=db_host,
    error=str(e),
)

# セキュリティ問題
logger.critical(
    "Potential security breach detected",
    source_ip=request.ip,
    pattern="sql_injection",
)
```

## チェックリスト

ロギング実装時の確認項目：

- [ ] 適切なログレベルを使用している
- [ ] 構造化データをキーワード引数で渡している
- [ ] 処理の開始と完了をログしている
- [ ] エラー時に `exc_info=True` を使用している
- [ ] センシティブ情報（パスワード等）をログしていない
- [ ] 大量ループ内で過剰にログしていない
- [ ] 一意の識別子（ID）を含めている
