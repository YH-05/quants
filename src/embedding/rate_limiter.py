"""レートリミッターモジュール.

asyncio.Semaphore ベースの自己完結型 RateLimiter を提供する。
非同期 context manager として使用し、同時実行数の制御とリクエスト間の
待機を行う。

Examples
--------
>>> import asyncio
>>> from embedding.rate_limiter import RateLimiter
>>>
>>> rate_limiter = RateLimiter(max_concurrent=3, delay_seconds=1.0)
>>>
>>> async def fetch(url: str) -> str:
...     async with rate_limiter:
...         return "result"
"""

import asyncio
import logging

logger = logging.getLogger(__name__)


class RateLimiter:
    """asyncio.Semaphore ベースの自己完結型レートリミッター.

    同時実行数の上限制御とリクエスト間の最小待機時間を組み合わせて、
    外部 API への過負荷を防ぐ。

    Attributes
    ----------
    max_concurrent : int
        最大同時実行数（デフォルト: 5）
    delay_seconds : float
        各実行後の待機秒数（デフォルト: 1.0）

    Examples
    --------
    >>> rate_limiter = RateLimiter(max_concurrent=3, delay_seconds=0.5)
    >>> async with rate_limiter:
    ...     await do_work()
    """

    def __init__(
        self,
        max_concurrent: int = 5,
        delay_seconds: float = 1.0,
    ) -> None:
        """RateLimiter を初期化する.

        Parameters
        ----------
        max_concurrent : int, optional
            最大同時実行数。デフォルトは 5。
        delay_seconds : float, optional
            各実行後の待機秒数。デフォルトは 1.0。

        Raises
        ------
        ValueError
            max_concurrent が 1 未満の場合
        ValueError
            delay_seconds が 0 未満の場合
        """
        if max_concurrent < 1:
            msg = f"max_concurrent must be >= 1, got {max_concurrent}"
            raise ValueError(msg)
        if delay_seconds < 0:
            msg = f"delay_seconds must be >= 0, got {delay_seconds}"
            raise ValueError(msg)

        self.max_concurrent = max_concurrent
        self.delay_seconds = delay_seconds
        self._semaphore = asyncio.Semaphore(max_concurrent)

        logger.debug(
            "RateLimiter initialized: max_concurrent=%d, delay_seconds=%.2f",
            max_concurrent,
            delay_seconds,
        )

    async def __aenter__(self) -> "RateLimiter":
        """セマフォを取得して実行を開始する."""
        await self._semaphore.acquire()
        logger.debug("RateLimiter: semaphore acquired")
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: object,
    ) -> None:
        """指定秒数待機してセマフォを解放する."""
        try:
            if self.delay_seconds > 0:
                logger.debug(
                    "RateLimiter: waiting %.2f seconds before release",
                    self.delay_seconds,
                )
                await asyncio.sleep(self.delay_seconds)
        finally:
            self._semaphore.release()
            logger.debug("RateLimiter: semaphore released")
