# リトライ・フォールバックパターン

外部 API 呼び出しやネットワーク処理での信頼性を向上させるパターンです。

## パターン一覧

| パターン | 用途 |
|---------|------|
| 指数バックオフ | 一時的な障害からの復帰 |
| 固定遅延リトライ | シンプルなリトライ |
| フォールバック | 代替手段への切り替え |
| サーキットブレーカー | 障害の連鎖防止 |

## 指数バックオフ

### 基本実装

```python
import time
import random
from typing import TypeVar, Callable
from utils_core.logging import get_logger

logger = get_logger(__name__)

T = TypeVar("T")


def retry_with_backoff(
    func: Callable[[], T],
    max_retries: int = 3,
    base_delay: float = 1.0,
    max_delay: float = 60.0,
    jitter: bool = True,
    exceptions: tuple[type[Exception], ...] = (Exception,),
) -> T:
    """指数バックオフでリトライする

    Parameters
    ----------
    func : Callable[[], T]
        実行する関数
    max_retries : int
        最大リトライ回数
    base_delay : float
        基本遅延時間（秒）
    max_delay : float
        最大遅延時間（秒）
    jitter : bool
        ジッターを追加するか（同時リトライの分散用）
    exceptions : tuple[type[Exception], ...]
        リトライ対象の例外

    Returns
    -------
    T
        関数の戻り値

    Raises
    ------
    Exception
        最大リトライ回数を超えた場合

    Examples
    --------
    >>> result = retry_with_backoff(
    ...     lambda: api_client.fetch("AAPL"),
    ...     max_retries=3,
    ...     exceptions=(NetworkError, RateLimitError),
    ... )
    """
    last_exception: Exception | None = None

    for attempt in range(max_retries + 1):
        try:
            return func()
        except exceptions as e:
            last_exception = e

            if attempt == max_retries:
                logger.error(
                    "Max retries exceeded",
                    attempt=attempt + 1,
                    max_retries=max_retries,
                    error=str(e),
                )
                raise

            # 指数バックオフ計算
            delay = min(base_delay * (2 ** attempt), max_delay)

            # ジッター追加（0.5〜1.5倍の範囲）
            if jitter:
                delay = delay * (0.5 + random.random())

            logger.warning(
                "Retry attempt",
                attempt=attempt + 1,
                delay=round(delay, 2),
                error=str(e),
            )
            time.sleep(delay)

    # 到達しないはずだが型チェックのため
    if last_exception:
        raise last_exception
    raise RuntimeError("Unexpected state in retry loop")
```

### デコレータ版

```python
from functools import wraps
from typing import ParamSpec

P = ParamSpec("P")


def with_retry(
    max_retries: int = 3,
    base_delay: float = 1.0,
    exceptions: tuple[type[Exception], ...] = (Exception,),
) -> Callable[[Callable[P, T]], Callable[P, T]]:
    """リトライデコレータ

    Examples
    --------
    >>> @with_retry(max_retries=3, exceptions=(NetworkError,))
    ... def fetch_data(symbol: str) -> DataFrame:
    ...     return api_client.fetch(symbol)
    """
    def decorator(func: Callable[P, T]) -> Callable[P, T]:
        @wraps(func)
        def wrapper(*args: P.args, **kwargs: P.kwargs) -> T:
            return retry_with_backoff(
                lambda: func(*args, **kwargs),
                max_retries=max_retries,
                base_delay=base_delay,
                exceptions=exceptions,
            )
        return wrapper
    return decorator


# 使用例
@with_retry(max_retries=3, exceptions=(DataFetchError,))
def fetch_stock_data(symbol: str) -> DataFrame:
    """リトライ付きデータ取得"""
    return yfinance_client.download(symbol)
```

## 固定遅延リトライ

シンプルなケースで使用：

```python
def retry_with_fixed_delay(
    func: Callable[[], T],
    max_retries: int = 3,
    delay: float = 1.0,
    exceptions: tuple[type[Exception], ...] = (Exception,),
) -> T:
    """固定遅延でリトライする

    Parameters
    ----------
    func : Callable[[], T]
        実行する関数
    max_retries : int
        最大リトライ回数
    delay : float
        リトライ間隔（秒）
    exceptions : tuple[type[Exception], ...]
        リトライ対象の例外
    """
    for attempt in range(max_retries + 1):
        try:
            return func()
        except exceptions as e:
            if attempt == max_retries:
                raise
            logger.warning(
                "Retry with fixed delay",
                attempt=attempt + 1,
                delay=delay,
            )
            time.sleep(delay)

    raise RuntimeError("Unreachable")
```

## フォールバック

### 基本パターン

```python
def fetch_with_fallback(
    symbol: str,
    primary: DataSource,
    fallback: DataSource,
) -> DataFrame:
    """プライマリ失敗時にフォールバックを使用

    Parameters
    ----------
    symbol : str
        取得するシンボル
    primary : DataSource
        プライマリデータソース
    fallback : DataSource
        フォールバックデータソース

    Returns
    -------
    DataFrame
        取得したデータ
    """
    try:
        logger.debug("Fetching from primary", source=primary.name)
        return primary.fetch(symbol)
    except DataFetchError as e:
        logger.warning(
            "Primary failed, trying fallback",
            primary=primary.name,
            fallback=fallback.name,
            error=str(e),
        )
        return fallback.fetch(symbol)
```

### 複数フォールバック

```python
def fetch_with_multiple_fallbacks(
    symbol: str,
    sources: list[DataSource],
) -> DataFrame:
    """複数のソースを順番に試行

    Parameters
    ----------
    symbol : str
        取得するシンボル
    sources : list[DataSource]
        データソースのリスト（優先順）

    Returns
    -------
    DataFrame
        取得したデータ

    Raises
    ------
    DataFetchError
        すべてのソースが失敗した場合
    """
    errors: list[Exception] = []

    for source in sources:
        try:
            logger.debug("Trying source", source=source.name)
            return source.fetch(symbol)
        except DataFetchError as e:
            logger.warning(
                "Source failed",
                source=source.name,
                error=str(e),
            )
            errors.append(e)

    raise DataFetchError(
        f"All {len(sources)} sources failed for {symbol}",
        symbol=symbol,
        details={"errors": [str(e) for e in errors]},
    )
```

## サーキットブレーカー

連続した障害を検出し、一時的にリクエストを遮断：

```python
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum


class CircuitState(Enum):
    CLOSED = "closed"      # 正常
    OPEN = "open"          # 遮断中
    HALF_OPEN = "half_open"  # 試行中


@dataclass
class CircuitBreaker:
    """サーキットブレーカー

    Parameters
    ----------
    failure_threshold : int
        オープンにする失敗回数
    recovery_timeout : float
        回復までの秒数
    half_open_max_calls : int
        ハーフオープン時の最大試行回数
    """

    failure_threshold: int = 5
    recovery_timeout: float = 60.0
    half_open_max_calls: int = 1

    state: CircuitState = field(default=CircuitState.CLOSED)
    failure_count: int = field(default=0)
    last_failure_time: datetime | None = field(default=None)
    half_open_calls: int = field(default=0)

    def call(self, func: Callable[[], T]) -> T:
        """サーキットブレーカー経由で関数を呼び出す"""
        if not self._can_execute():
            raise CircuitOpenError(
                "Circuit is open",
                recovery_in=self._time_until_recovery(),
            )

        try:
            result = func()
            self._on_success()
            return result
        except Exception as e:
            self._on_failure()
            raise

    def _can_execute(self) -> bool:
        """実行可能かどうかを判定"""
        if self.state == CircuitState.CLOSED:
            return True

        if self.state == CircuitState.OPEN:
            if self._should_try_recovery():
                self.state = CircuitState.HALF_OPEN
                self.half_open_calls = 0
                return True
            return False

        # HALF_OPEN
        return self.half_open_calls < self.half_open_max_calls

    def _should_try_recovery(self) -> bool:
        """回復を試みるべきかどうか"""
        if self.last_failure_time is None:
            return True
        elapsed = datetime.now() - self.last_failure_time
        return elapsed > timedelta(seconds=self.recovery_timeout)

    def _time_until_recovery(self) -> float:
        """回復までの残り時間"""
        if self.last_failure_time is None:
            return 0.0
        elapsed = datetime.now() - self.last_failure_time
        remaining = self.recovery_timeout - elapsed.total_seconds()
        return max(0.0, remaining)

    def _on_success(self) -> None:
        """成功時の処理"""
        self.failure_count = 0
        self.state = CircuitState.CLOSED
        logger.info("Circuit closed", state=self.state.value)

    def _on_failure(self) -> None:
        """失敗時の処理"""
        self.failure_count += 1
        self.last_failure_time = datetime.now()

        if self.state == CircuitState.HALF_OPEN:
            self.state = CircuitState.OPEN
            logger.warning(
                "Circuit re-opened",
                failure_count=self.failure_count,
            )
        elif self.failure_count >= self.failure_threshold:
            self.state = CircuitState.OPEN
            logger.warning(
                "Circuit opened",
                failure_count=self.failure_count,
                threshold=self.failure_threshold,
            )


class CircuitOpenError(Exception):
    """サーキットがオープン状態の場合の例外"""

    def __init__(self, message: str, recovery_in: float) -> None:
        super().__init__(message)
        self.recovery_in = recovery_in
```

### サーキットブレーカーの使用例

```python
# グローバルなサーキットブレーカー
yfinance_circuit = CircuitBreaker(
    failure_threshold=5,
    recovery_timeout=60.0,
)


def fetch_stock_data(symbol: str) -> DataFrame:
    """サーキットブレーカー付きデータ取得"""
    try:
        return yfinance_circuit.call(
            lambda: yfinance_client.download(symbol)
        )
    except CircuitOpenError as e:
        logger.warning(
            "Circuit is open, using cache",
            recovery_in=e.recovery_in,
        )
        return cache.get(symbol)
```

## ベストプラクティス

### リトライ対象の例外を明示

```python
# 良い例：具体的な例外を指定
RETRYABLE_EXCEPTIONS = (
    ConnectionError,
    TimeoutError,
    RateLimitError,
)

retry_with_backoff(
    func,
    exceptions=RETRYABLE_EXCEPTIONS,
)

# 悪い例：すべての例外をリトライ
retry_with_backoff(
    func,
    exceptions=(Exception,),  # 避ける
)
```

### リトライしてはいけない例外

以下の例外はリトライしても解決しない：

- `ValidationError`: 入力が不正
- `AuthenticationError`: 認証情報が無効
- `NotFoundError`: リソースが存在しない
- `PermissionDeniedError`: 権限がない

```python
# リトライ不可の例外を除外
def is_retryable(e: Exception) -> bool:
    """リトライ可能な例外かどうか判定"""
    non_retryable = (
        ValidationError,
        AuthenticationError,
        NotFoundError,
        PermissionDeniedError,
    )
    return not isinstance(e, non_retryable)
```

### ログの重要性

```python
def retry_with_logging(func: Callable[[], T]) -> T:
    """ログ付きリトライ"""
    for attempt in range(max_retries + 1):
        try:
            result = func()
            if attempt > 0:
                logger.info(
                    "Retry succeeded",
                    attempt=attempt + 1,
                )
            return result
        except Exception as e:
            logger.warning(
                "Attempt failed",
                attempt=attempt + 1,
                error=str(e),
                error_type=type(e).__name__,
            )
            # ...
```

## 参照実装

このプロジェクトでの参照実装：

- `src/market_analysis/utils/retry.py`: リトライユーティリティ
- `src/rss/core/http_client.py`: HTTP クライアントのリトライ
