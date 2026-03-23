"""Dual-window sliding rate limiter for the Alpha Vantage API module.

This module provides ``DualWindowRateLimiter`` (synchronous) and
``AsyncDualWindowRateLimiter`` (asynchronous) classes that enforce
both per-minute and per-hour request limits using a sliding window
algorithm backed by ``collections.deque`` timestamp tracking.

The sliding window approach ensures precise rate limiting: each
request is timestamped with ``time.monotonic()``, and only timestamps
within the relevant window (60 s for minute, 3600 s for hour) are
counted against the limit.

Notes
-----
This module is intentionally separated from session/client code to
improve testability and adhere to the single-responsibility principle.
The limiters are designed to be injected into session classes for
request throttling.

The design differs fundamentally from ``market.edinet.rate_limiter``
which uses daily counting with file persistence. This module uses
in-memory sliding windows suitable for per-minute and per-hour limits.

See Also
--------
market.alphavantage.constants : Default values for
    ``DEFAULT_REQUESTS_PER_MINUTE`` and ``DEFAULT_REQUESTS_PER_HOUR``.
"""

from __future__ import annotations

import asyncio
import threading
import time
from collections import deque

from market.alphavantage.constants import (
    DEFAULT_REQUESTS_PER_HOUR,
    DEFAULT_REQUESTS_PER_MINUTE,
)
from utils_core.logging import get_logger

logger = get_logger(__name__)

# Window durations in seconds
_MINUTE_WINDOW: float = 60.0
_HOUR_WINDOW: float = 3600.0


class DualWindowRateLimiter:
    """Thread-safe dual-window sliding rate limiter.

    Enforces both per-minute and per-hour request limits using a sliding
    window algorithm. Each ``acquire()`` call records a timestamp; when
    the number of timestamps within a window reaches its limit, the
    caller is blocked (via ``time.sleep``) until a slot opens.

    Parameters
    ----------
    requests_per_minute : int
        Maximum number of requests allowed per 60-second window
        (default: ``DEFAULT_REQUESTS_PER_MINUTE`` = 25).
    requests_per_hour : int
        Maximum number of requests allowed per 3600-second window
        (default: ``DEFAULT_REQUESTS_PER_HOUR`` = 500).

    Raises
    ------
    ValueError
        If ``requests_per_minute`` or ``requests_per_hour`` is not positive.

    Examples
    --------
    >>> limiter = DualWindowRateLimiter(requests_per_minute=5, requests_per_hour=100)
    >>> limiter.available_minute
    5
    >>> waited = limiter.acquire()
    >>> limiter.available_minute
    4
    """

    def __init__(
        self,
        requests_per_minute: int = DEFAULT_REQUESTS_PER_MINUTE,
        requests_per_hour: int = DEFAULT_REQUESTS_PER_HOUR,
    ) -> None:
        if requests_per_minute <= 0:
            raise ValueError(
                f"requests_per_minute must be positive, got {requests_per_minute}"
            )
        if requests_per_hour <= 0:
            raise ValueError(
                f"requests_per_hour must be positive, got {requests_per_hour}"
            )

        self._requests_per_minute = requests_per_minute
        self._requests_per_hour = requests_per_hour
        self._timestamps: deque[float] = deque()
        self._lock = threading.Lock()

        logger.debug(
            "DualWindowRateLimiter initialized",
            requests_per_minute=requests_per_minute,
            requests_per_hour=requests_per_hour,
        )

    @property
    def available_minute(self) -> int:
        """Return the number of remaining requests in the current minute window.

        Returns
        -------
        int
            Remaining requests allowed in the current 60-second window.
            Always in ``[0, requests_per_minute]``.
        """
        now = time.monotonic()
        minute_cutoff = now - _MINUTE_WINDOW
        count_in_minute = sum(1 for ts in self._timestamps if ts > minute_cutoff)
        return max(0, self._requests_per_minute - count_in_minute)

    @property
    def available_hour(self) -> int:
        """Return the number of remaining requests in the current hour window.

        Returns
        -------
        int
            Remaining requests allowed in the current 3600-second window.
            Always in ``[0, requests_per_hour]``.
        """
        now = time.monotonic()
        hour_cutoff = now - _HOUR_WINDOW
        count_in_hour = sum(1 for ts in self._timestamps if ts > hour_cutoff)
        return max(0, self._requests_per_hour - count_in_hour)

    def acquire(self) -> float:
        """Acquire a rate limit slot, blocking if necessary.

        If both the minute and hour windows have available capacity,
        records the current timestamp and returns immediately with
        ``0.0``. Otherwise, sleeps until the earliest slot opens
        and returns the total time waited in seconds.

        Returns
        -------
        float
            Total time waited in seconds (``0.0`` if no wait was needed).

        Examples
        --------
        >>> limiter = DualWindowRateLimiter(requests_per_minute=25)
        >>> waited = limiter.acquire()  # returns 0.0 if under limit
        """
        total_waited = 0.0

        while True:
            with self._lock:
                wait_time = self._compute_wait_time()

                if wait_time <= 0.0:
                    now = time.monotonic()
                    self._timestamps.append(now)
                    logger.debug(
                        "Rate limit slot acquired",
                        total_waited=total_waited,
                        available_minute=self.available_minute,
                        available_hour=self.available_hour,
                    )
                    return total_waited

                logger.info(
                    "Rate limit reached, waiting",
                    wait_seconds=wait_time,
                )

            # Sleep outside the lock to allow other threads to proceed
            time.sleep(wait_time)
            total_waited += wait_time

    def _compute_wait_time(self) -> float:
        """Compute wait time needed before a request slot opens.

        Should be called while holding ``_lock``.

        Returns
        -------
        float
            Seconds to wait (``0.0`` or negative if a slot is available).
        """
        now = time.monotonic()
        self._purge_old()

        minute_cutoff = now - _MINUTE_WINDOW
        hour_cutoff = now - _HOUR_WINDOW

        count_in_minute = sum(1 for ts in self._timestamps if ts > minute_cutoff)
        count_in_hour = sum(1 for ts in self._timestamps if ts > hour_cutoff)

        wait_minute = 0.0
        wait_hour = 0.0

        if count_in_minute >= self._requests_per_minute:
            oldest_in_minute = min(
                (ts for ts in self._timestamps if ts > minute_cutoff),
                default=now,
            )
            wait_minute = oldest_in_minute + _MINUTE_WINDOW - now

        if count_in_hour >= self._requests_per_hour:
            oldest_in_hour = min(
                (ts for ts in self._timestamps if ts > hour_cutoff),
                default=now,
            )
            wait_hour = oldest_in_hour + _HOUR_WINDOW - now

        return max(wait_minute, wait_hour)

    def _purge_old(self) -> None:
        """Remove timestamps older than 1 hour from the deque.

        This method should be called while holding ``_lock``.
        Timestamps older than ``_HOUR_WINDOW`` (3600 seconds) are
        removed from the left side of the deque since they can no
        longer affect either the minute or hour window counts.
        """
        now = time.monotonic()
        cutoff = now - _HOUR_WINDOW
        while self._timestamps and self._timestamps[0] <= cutoff:
            self._timestamps.popleft()


class AsyncDualWindowRateLimiter:
    """Async-safe dual-window sliding rate limiter.

    Provides the same dual-window rate limiting algorithm as
    ``DualWindowRateLimiter`` but uses ``asyncio.Lock`` and
    ``asyncio.sleep`` for non-blocking async operation.

    Parameters
    ----------
    requests_per_minute : int
        Maximum number of requests allowed per 60-second window
        (default: ``DEFAULT_REQUESTS_PER_MINUTE`` = 25).
    requests_per_hour : int
        Maximum number of requests allowed per 3600-second window
        (default: ``DEFAULT_REQUESTS_PER_HOUR`` = 500).

    Raises
    ------
    ValueError
        If ``requests_per_minute`` or ``requests_per_hour`` is not positive.

    Examples
    --------
    >>> import asyncio
    >>> limiter = AsyncDualWindowRateLimiter(requests_per_minute=5)
    >>> waited = asyncio.run(limiter.acquire())
    """

    def __init__(
        self,
        requests_per_minute: int = DEFAULT_REQUESTS_PER_MINUTE,
        requests_per_hour: int = DEFAULT_REQUESTS_PER_HOUR,
    ) -> None:
        if requests_per_minute <= 0:
            raise ValueError(
                f"requests_per_minute must be positive, got {requests_per_minute}"
            )
        if requests_per_hour <= 0:
            raise ValueError(
                f"requests_per_hour must be positive, got {requests_per_hour}"
            )

        self._requests_per_minute = requests_per_minute
        self._requests_per_hour = requests_per_hour
        self._timestamps: deque[float] = deque()
        self._lock = asyncio.Lock()

        logger.debug(
            "AsyncDualWindowRateLimiter initialized",
            requests_per_minute=requests_per_minute,
            requests_per_hour=requests_per_hour,
        )

    @property
    def available_minute(self) -> int:
        """Return the number of remaining requests in the current minute window.

        Returns
        -------
        int
            Remaining requests allowed in the current 60-second window.
        """
        now = time.monotonic()
        minute_cutoff = now - _MINUTE_WINDOW
        count_in_minute = sum(1 for ts in self._timestamps if ts > minute_cutoff)
        return max(0, self._requests_per_minute - count_in_minute)

    @property
    def available_hour(self) -> int:
        """Return the number of remaining requests in the current hour window.

        Returns
        -------
        int
            Remaining requests allowed in the current 3600-second window.
        """
        now = time.monotonic()
        hour_cutoff = now - _HOUR_WINDOW
        count_in_hour = sum(1 for ts in self._timestamps if ts > hour_cutoff)
        return max(0, self._requests_per_hour - count_in_hour)

    async def acquire(self) -> float:
        """Acquire a rate limit slot, sleeping asynchronously if necessary.

        If both the minute and hour windows have available capacity,
        records the current timestamp and returns immediately with
        ``0.0``. Otherwise, sleeps asynchronously until the earliest
        slot opens and returns the total time waited in seconds.

        Returns
        -------
        float
            Total time waited in seconds (``0.0`` if no wait was needed).
        """
        total_waited = 0.0

        while True:
            async with self._lock:
                wait_time = self._compute_wait_time()

                if wait_time <= 0.0:
                    now = time.monotonic()
                    self._timestamps.append(now)
                    logger.debug(
                        "Async rate limit slot acquired",
                        total_waited=total_waited,
                        available_minute=self.available_minute,
                        available_hour=self.available_hour,
                    )
                    return total_waited

                logger.info(
                    "Async rate limit reached, waiting",
                    wait_seconds=wait_time,
                )

            # Sleep outside the lock to allow other coroutines to proceed
            await asyncio.sleep(wait_time)
            total_waited += wait_time

    def _compute_wait_time(self) -> float:
        """Compute wait time needed before a request slot opens.

        Should be called while holding ``_lock``.

        Returns
        -------
        float
            Seconds to wait (``0.0`` or negative if a slot is available).
        """
        now = time.monotonic()
        self._purge_old()

        minute_cutoff = now - _MINUTE_WINDOW
        hour_cutoff = now - _HOUR_WINDOW

        count_in_minute = sum(1 for ts in self._timestamps if ts > minute_cutoff)
        count_in_hour = sum(1 for ts in self._timestamps if ts > hour_cutoff)

        wait_minute = 0.0
        wait_hour = 0.0

        if count_in_minute >= self._requests_per_minute:
            oldest_in_minute = min(
                (ts for ts in self._timestamps if ts > minute_cutoff),
                default=now,
            )
            wait_minute = oldest_in_minute + _MINUTE_WINDOW - now

        if count_in_hour >= self._requests_per_hour:
            oldest_in_hour = min(
                (ts for ts in self._timestamps if ts > hour_cutoff),
                default=now,
            )
            wait_hour = oldest_in_hour + _HOUR_WINDOW - now

        return max(wait_minute, wait_hour)

    def _purge_old(self) -> None:
        """Remove timestamps older than 1 hour from the deque.

        Should be called while holding ``_lock``.
        """
        now = time.monotonic()
        cutoff = now - _HOUR_WINDOW
        while self._timestamps and self._timestamps[0] <= cutoff:
            self._timestamps.popleft()


__all__ = [
    "AsyncDualWindowRateLimiter",
    "DualWindowRateLimiter",
]
