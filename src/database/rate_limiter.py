"""Generic thread-safe rate limiter.

This module provides a thread-safe rate limiter that can be used across
packages. It uses a minimum interval approach to enforce the rate limit.

Notes
-----
Originally implemented in ``edgar.rate_limiter`` for the SEC EDGAR API.
Moved to the ``database`` package as a shared utility to avoid import
conflicts with the external ``edgartools`` library, which also installs
as ``edgar`` in site-packages.
"""

from __future__ import annotations

import threading
import time

from utils_core.logging import get_logger

logger = get_logger(__name__)

# Default rate limit (requests per second)
_DEFAULT_RATE_LIMIT_PER_SECOND = 10


class RateLimiter:
    """Thread-safe rate limiter.

    Uses a minimum interval approach to enforce the rate limit.
    Each call to ``acquire()`` ensures that enough time has passed
    since the last request before proceeding.

    Parameters
    ----------
    max_requests_per_second : int
        Maximum number of requests allowed per second.
        Defaults to 10.

    Attributes
    ----------
    max_requests_per_second : int
        The configured maximum requests per second
    _min_interval : float
        Minimum time (in seconds) between consecutive requests
    _last_request_time : float
        Monotonic timestamp of the last request
    _lock : threading.Lock
        Lock for thread-safe access to timing state

    Raises
    ------
    ValueError
        If max_requests_per_second is not positive

    Examples
    --------
    >>> limiter = RateLimiter(max_requests_per_second=10)
    >>> limiter.acquire()  # First request passes immediately
    >>> limiter.acquire()  # Second request may sleep if too fast
    """

    def __init__(
        self,
        max_requests_per_second: int = _DEFAULT_RATE_LIMIT_PER_SECOND,
    ) -> None:
        if max_requests_per_second <= 0:
            msg = (
                f"max_requests_per_second must be positive, "
                f"got {max_requests_per_second}"
            )
            raise ValueError(msg)

        self.max_requests_per_second = max_requests_per_second
        self._min_interval = 1.0 / max_requests_per_second
        self._last_request_time = 0.0
        self._lock = threading.Lock()

        logger.debug(
            "RateLimiter initialized",
            max_requests_per_second=max_requests_per_second,
            min_interval_ms=round(self._min_interval * 1000, 1),
        )

    def acquire(self) -> None:
        """Acquire permission to make a request, blocking if necessary.

        This method is thread-safe. If the rate limit would be exceeded,
        it sleeps for the remaining time before allowing the request
        to proceed.

        The sleep duration is calculated as the difference between the
        minimum interval and the time elapsed since the last request.
        """
        with self._lock:
            now = time.monotonic()
            elapsed = now - self._last_request_time
            wait_time = self._min_interval - elapsed

            if wait_time > 0:
                logger.debug(
                    "Rate limit: waiting before next request",
                    wait_ms=round(wait_time * 1000, 1),
                )
                time.sleep(wait_time)

            self._last_request_time = time.monotonic()

    def __repr__(self) -> str:
        """Return string representation.

        Returns
        -------
        str
            String representation including the rate limit configuration
        """
        return f"RateLimiter(max_requests_per_second={self.max_requests_per_second})"


__all__ = [
    "RateLimiter",
]
