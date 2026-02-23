"""非同期処理コアモジュール.

同時実行数制限、リクエスト間隔制御、および並列タスク実行を提供する。

Examples
--------
>>> import asyncio
>>> from news_scraper.async_core import RateLimiter, gather_with_errors
>>>
>>> async def main():
...     limiter = RateLimiter(delay=1.0, max_concurrency=5)
...     async with limiter:
...         print("rate-limited request")
>>>
>>> asyncio.run(main())
"""

import asyncio
import time
from typing import Any


class RateLimiter:
    """同時実行数とリクエスト間隔を制御するレートリミッター.

    ``asyncio.Semaphore`` で同時実行数を制限し、
    時間ベースの delay でリクエスト間の最小間隔を保証する。

    Parameters
    ----------
    delay : float
        リクエスト間の最小待機秒数（0 以上）
    max_concurrency : int
        同時実行可能な最大リクエスト数（1 以上）

    Raises
    ------
    ValueError
        delay が負数、または max_concurrency が 0 以下の場合

    Examples
    --------
    >>> limiter = RateLimiter(delay=1.0, max_concurrency=5)
    >>> async with limiter:
    ...     await fetch_data()

    >>> # 手動制御
    >>> await limiter.acquire()
    >>> try:
    ...     await fetch_data()
    ... finally:
    ...     limiter.release()
    """

    def __init__(self, delay: float, max_concurrency: int) -> None:
        if delay < 0:
            msg = f"delay must be non-negative, got {delay}"
            raise ValueError(msg)
        if max_concurrency <= 0:
            msg = f"max_concurrency must be positive, got {max_concurrency}"
            raise ValueError(msg)

        self._delay = delay
        self._semaphore = asyncio.Semaphore(max_concurrency)
        self._last_request_time: float = 0.0
        self._lock = asyncio.Lock()

    async def acquire(self) -> None:
        """レートリミットを取得する.

        セマフォの取得と delay の適用を行う。
        同時実行数が ``max_concurrency`` に達している場合は、
        空きが出るまで待機する。
        前回のリクエストから ``delay`` 秒未満の場合は、
        残り時間だけ待機する。
        """
        await self._semaphore.acquire()
        async with self._lock:
            now = time.monotonic()
            elapsed = now - self._last_request_time
            if elapsed < self._delay:
                await asyncio.sleep(self._delay - elapsed)
            self._last_request_time = time.monotonic()

    def release(self) -> None:
        """レートリミットを解放する.

        セマフォを解放し、次のリクエストが実行可能になる。
        """
        self._semaphore.release()

    async def __aenter__(self) -> "RateLimiter":
        """非同期コンテキストマネージャのエントリーポイント.

        Returns
        -------
        RateLimiter
            自身のインスタンス
        """
        await self.acquire()
        return self

    async def __aexit__(self, *args: object) -> None:
        """非同期コンテキストマネージャの終了処理.

        セマフォを解放する。
        """
        self.release()


async def gather_with_errors[T](
    tasks: list[asyncio.Task[T]],
    # AIDEV-NOTE: structlog.BoundLogger は logging.Logger を継承しないため Any を使用
    logger: Any,
) -> list[T]:
    """複数の非同期タスクを並列実行し、成功結果のみを返す.

    ``asyncio.gather(return_exceptions=True)`` のラッパー。
    失敗したタスクはエラーログに記録してスキップし、
    成功したタスクの結果のみをリストで返す。

    Parameters
    ----------
    tasks : list[asyncio.Task[T]]
        実行する非同期タスクのリスト
    logger : Any
        エラーログ出力に使用するロガー（logging.Logger または structlog.BoundLogger）

    Returns
    -------
    list[T]
        成功したタスクの結果リスト（元の順序を維持）

    Examples
    --------
    >>> import asyncio
    >>> import logging
    >>> logger = logging.getLogger(__name__)
    >>> async def fetch(url: str) -> str:
    ...     return f"data from {url}"
    >>> async def main():
    ...     tasks = [asyncio.create_task(fetch(u)) for u in ["a", "b"]]
    ...     results = await gather_with_errors(tasks, logger)
    ...     print(results)
    >>> asyncio.run(main())
    """
    results = await asyncio.gather(*tasks, return_exceptions=True)
    successes: list[T] = []
    for i, result in enumerate(results):
        if isinstance(result, BaseException):
            logger.error("Task %d failed: %s", i, result)
        else:
            successes.append(result)
    return successes
