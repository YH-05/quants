"""HTTP session abstraction for Polymarket API access.

This module provides the ``PolymarketSession`` class, an httpx-based HTTP session
with polite delays (monotonic-clock-based), SSRF prevention via host whitelist,
response status handling, and exponential backoff retry logic.

Unlike ``market.jquants.session.JQuantsSession``, this session does **not**
require authentication — Polymarket APIs are public. The core HTTP communication
patterns (SSRF prevention, polite delay, retry, response handling) are extracted
from the J-Quants session and adapted for Polymarket's three API endpoints
(Gamma, CLOB, Data).

See Also
--------
market.jquants.session : Reference implementation with authentication.
market.polymarket.constants : Allowed hosts, default values.
market.polymarket.types : PolymarketConfig, RetryConfig dataclasses.
market.polymarket.errors : PolymarketAPIError, PolymarketRateLimitError.
"""

import random
import time
from typing import Any
from urllib.parse import urlparse

import httpx

from market.polymarket.constants import ALLOWED_HOSTS
from market.polymarket.errors import (
    PolymarketAPIError,
    PolymarketRateLimitError,
)
from market.polymarket.types import PolymarketConfig, RetryConfig
from utils_core.logging import get_logger

logger = get_logger(__name__)

# HTTP status code indicating rate limiting
_RATE_LIMIT_STATUS_CODE = 429

# Maximum length of response body stored in PolymarketAPIError (CWE-209 mitigation)
_MAX_RESPONSE_BODY_LOG = 200

# Exponential base for backoff calculation
_BACKOFF_EXPONENTIAL_BASE = 2


class PolymarketSession:
    """httpx-based HTTP session for Polymarket API without authentication.

    Provides polite delays between requests (using ``time.monotonic()``),
    SSRF prevention via host whitelist, response status handling, and
    exponential backoff retry logic.

    Parameters
    ----------
    config : PolymarketConfig | None
        Polymarket configuration. If ``None``, defaults are used.
    retry_config : RetryConfig | None
        Retry configuration. If ``None``, defaults are used.

    Examples
    --------
    >>> with PolymarketSession() as session:
    ...     response = session.get(
    ...         "https://gamma-api.polymarket.com/markets",
    ...     )
    ...     print(response.status_code)
    200
    """

    def __init__(
        self,
        config: PolymarketConfig | None = None,
        retry_config: RetryConfig | None = None,
    ) -> None:
        """Initialize PolymarketSession with configuration.

        Parameters
        ----------
        config : PolymarketConfig | None
            Polymarket configuration. Defaults to ``PolymarketConfig()``.
        retry_config : RetryConfig | None
            Retry configuration. Defaults to ``RetryConfig()``.
        """
        self._config: PolymarketConfig = config or PolymarketConfig()
        self._retry_config: RetryConfig = retry_config or RetryConfig()
        self._last_request_time: float = 0.0

        # Derive polite delay from rate_limit_per_second
        # e.g., 1.5 req/s -> 0.667s delay between requests
        self._polite_delay_seconds: float = 1.0 / self._config.rate_limit_per_second

        # Random jitter range (10% of polite delay)
        self._delay_jitter: float = self._polite_delay_seconds * 0.1

        # Create httpx client with timeout and explicit SSL verification
        self._client: httpx.Client = httpx.Client(
            timeout=httpx.Timeout(self._config.timeout),
            verify=True,
        )

        logger.info(
            "PolymarketSession initialized",
            polite_delay=self._polite_delay_seconds,
            delay_jitter=self._delay_jitter,
            timeout=self._config.timeout,
            max_retry_attempts=self._retry_config.max_attempts,
        )

    # =========================================================================
    # Public API
    # =========================================================================

    def get(
        self,
        url: str,
        params: dict[str, str] | None = None,
    ) -> httpx.Response:
        """Send a GET request with polite delay and status handling.

        Applies the following before each request:

        1. URL whitelist validation (SSRF prevention)
        2. Polite delay (monotonic-clock-based interval control)

        Parameters
        ----------
        url : str
            The URL to send the GET request to.
        params : dict[str, str] | None
            Optional query parameters for the request.

        Returns
        -------
        httpx.Response
            The HTTP response object.

        Raises
        ------
        ValueError
            If the URL host is not in the allowed hosts whitelist.
        PolymarketRateLimitError
            If the response status code is 429.
        PolymarketAPIError
            If the response status code indicates an error.
        """
        # 1. URL whitelist validation (SSRF prevention, CWE-918)
        self._validate_url(url)

        # 2. Apply polite delay (monotonic-clock-based)
        self._polite_delay()

        # 3. Build headers (no auth needed for Polymarket)
        headers: dict[str, str] = {
            "Accept": "application/json",
        }

        logger.debug("Sending GET request", url=url)

        # 4. Execute request
        response: httpx.Response = self._client.get(
            url,
            headers=headers,
            params=params,
        )

        # 5. Handle response status
        self._handle_response(response, url)

        logger.debug(
            "GET request completed",
            url=url,
            status_code=response.status_code,
        )
        return response

    def get_with_retry(
        self,
        url: str,
        params: dict[str, str] | None = None,
    ) -> httpx.Response:
        """Send a GET request with exponential backoff retry.

        On each failed attempt (rate limit or server error), the request
        is retried after an exponentially increasing delay. Only 429
        and 5xx errors trigger retries; 4xx client errors are raised
        immediately.

        Parameters
        ----------
        url : str
            The URL to send the GET request to.
        params : dict[str, str] | None
            Optional query parameters for the request.

        Returns
        -------
        httpx.Response
            The HTTP response object.

        Raises
        ------
        PolymarketRateLimitError
            If all retry attempts fail due to rate limiting.
        PolymarketAPIError
            If all retry attempts fail due to server errors,
            or if a 4xx client error is encountered.
        """
        last_error: PolymarketRateLimitError | PolymarketAPIError | None = None

        for attempt in range(self._retry_config.max_attempts):
            try:
                response = self.get(url, params=params)

                if attempt > 0:
                    logger.info(
                        "Request succeeded after retry",
                        url=url,
                        attempt=attempt + 1,
                    )
                return response

            except (PolymarketRateLimitError, PolymarketAPIError) as e:
                # Only retry on rate limit (429) and 5xx server errors.
                # Re-raise 4xx client errors immediately (except 429).
                is_rate_limit = isinstance(e, PolymarketRateLimitError)
                if not is_rate_limit and e.status_code < 500:
                    raise
                last_error = e
                logger.warning(
                    "Request failed, will retry",
                    url=url,
                    attempt=attempt + 1,
                    max_attempts=self._retry_config.max_attempts,
                    error=str(e),
                )

                # If this is not the last attempt, apply backoff
                if attempt < self._retry_config.max_attempts - 1:
                    delay = self._calculate_backoff_delay(attempt)
                    logger.debug(
                        "Backoff before retry",
                        delay_seconds=delay,
                        next_attempt=attempt + 2,
                    )
                    time.sleep(delay)

        # All attempts exhausted
        logger.error(
            "All retry attempts failed",
            url=url,
            max_attempts=self._retry_config.max_attempts,
        )
        if last_error is None:
            raise RuntimeError("Unexpected: no error recorded after exhausting retries")
        raise last_error

    # =========================================================================
    # Context Manager
    # =========================================================================

    def close(self) -> None:
        """Close the session and release resources."""
        self._client.close()
        logger.debug("PolymarketSession closed")

    def __enter__(self) -> "PolymarketSession":
        """Support context manager protocol.

        Returns
        -------
        PolymarketSession
            Self for use in with statement.
        """
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: Any,
    ) -> None:
        """Close session on context exit."""
        self.close()

    # =========================================================================
    # Internal Methods
    # =========================================================================

    def _validate_url(self, url: str) -> None:
        """Validate URL against the allowed hosts whitelist (SSRF prevention).

        Parameters
        ----------
        url : str
            The URL to validate.

        Raises
        ------
        ValueError
            If the URL scheme is not https or the host is not
            in ``ALLOWED_HOSTS``.
        """
        parsed = urlparse(url)
        if parsed.scheme != "https":
            raise ValueError(
                f"URL scheme must be 'https', got '{parsed.scheme}'. "
                "Only HTTPS is permitted for Polymarket API access."
            )
        parsed_host = parsed.hostname or ""
        if parsed_host not in ALLOWED_HOSTS:
            logger.warning(
                "Request blocked: host not in allowed hosts",
                url=url,
                host=parsed_host,
                allowed_hosts=list(ALLOWED_HOSTS),
            )
            raise ValueError(
                f"Host '{parsed_host}' is not in allowed hosts: {sorted(ALLOWED_HOSTS)}"
            )

    def _polite_delay(self) -> None:
        """Apply polite delay between consecutive requests.

        Uses ``time.monotonic()`` to measure elapsed time since the
        last request. Sleeps for the remaining delay if not enough
        time has passed. Adds random jitter to avoid thundering herd.
        """
        now = time.monotonic()

        if self._last_request_time > 0:
            elapsed = now - self._last_request_time
            required_delay = self._polite_delay_seconds + random.uniform(  # nosec B311
                0, self._delay_jitter
            )
            remaining = required_delay - elapsed
            if remaining > 0:
                time.sleep(remaining)
                logger.debug("Polite delay applied", delay_seconds=remaining)

        self._last_request_time = time.monotonic()

    def _handle_response(self, response: httpx.Response, url: str) -> None:
        """Check response status and raise appropriate exceptions.

        Parameters
        ----------
        response : httpx.Response
            The HTTP response to check.
        url : str
            The request URL for error context.

        Raises
        ------
        PolymarketRateLimitError
            If HTTP 429 is returned.
        PolymarketAPIError
            If HTTP 4xx or 5xx is returned.
        """
        status = response.status_code

        # 429: rate limit
        if status == _RATE_LIMIT_STATUS_CODE:
            retry_after_header = response.headers.get("Retry-After")
            retry_after = int(retry_after_header) if retry_after_header else None
            logger.warning(
                "Rate limit detected",
                url=url,
                status_code=status,
                retry_after=retry_after,
            )
            raise PolymarketRateLimitError(
                message=f"Rate limit detected: HTTP {status}",
                url=url,
                retry_after=retry_after,
            )

        # 4xx: client error (except 429)
        if 400 <= status < 500:
            logger.warning(
                "Client error",
                url=url,
                status_code=status,
            )
            raise PolymarketAPIError(
                message=f"Client error: HTTP {status}",
                url=url,
                status_code=status,
                response_body=response.text[:_MAX_RESPONSE_BODY_LOG],
            )

        # 5xx: server error
        if status >= 500:
            logger.warning(
                "Server error",
                url=url,
                status_code=status,
            )
            raise PolymarketAPIError(
                message=f"Server error: HTTP {status}",
                url=url,
                status_code=status,
                response_body=response.text[:_MAX_RESPONSE_BODY_LOG],
            )

    def _calculate_backoff_delay(self, attempt: int) -> float:
        """Calculate exponential backoff delay with jitter.

        Parameters
        ----------
        attempt : int
            Current attempt number (0-indexed).

        Returns
        -------
        float
            Delay in seconds.
        """
        delay = min(
            self._retry_config.base_wait * (_BACKOFF_EXPONENTIAL_BASE**attempt),
            self._retry_config.max_wait,
        )
        # Apply jitter: multiply by 0.5 to 1.5
        delay *= 0.5 + random.random()  # nosec B311
        return delay


__all__ = ["PolymarketSession"]
