"""HTTP session abstraction for Alpha Vantage API access.

This module provides the ``AlphaVantageSession`` class, an httpx-based HTTP
session with API key query parameter injection, Alpha Vantage-specific HTTP 200
body error detection, polite delays (monotonic-clock-based), SSRF prevention
via host whitelist, rate limiter integration, and exponential backoff retry logic.

Alpha Vantage has a unique error pattern: the API always returns HTTP 200, but
the response body may contain error keys (``Error Message``, ``Note``,
``Information``) instead of the expected data. This session layer detects
these patterns and raises appropriate exceptions.

See Also
--------
market.jquants.session : Reference implementation for httpx session pattern.
market.alphavantage.constants : Default values, allowed hosts.
market.alphavantage.types : AlphaVantageConfig, RetryConfig dataclasses.
market.alphavantage.errors : AlphaVantageAuthError, AlphaVantageAPIError,
    AlphaVantageRateLimitError exceptions.
market.alphavantage.rate_limiter : DualWindowRateLimiter for request throttling.
"""

from __future__ import annotations

import os
import random
import time
from typing import Any
from urllib.parse import urlparse

import httpx

from market.alphavantage.constants import (
    ALLOWED_HOSTS,
    ALPHA_VANTAGE_API_KEY_ENV,
    BASE_URL,
    MAX_RESPONSE_BODY_LOG,
)
from market.alphavantage.errors import (
    AlphaVantageAPIError,
    AlphaVantageAuthError,
    AlphaVantageRateLimitError,
)
from market.alphavantage.rate_limiter import DualWindowRateLimiter
from market.alphavantage.types import AlphaVantageConfig, RetryConfig
from utils_core.logging import get_logger

logger = get_logger(__name__)

# HTTP status code indicating rate limiting
_RATE_LIMIT_STATUS_CODE = 429

# Keywords in Error Message that indicate auth failures
_AUTH_ERROR_KEYWORDS = ("apikey is invalid", "api key", "premium")


class AlphaVantageSession:
    """httpx-based HTTP session for Alpha Vantage API.

    Provides API key injection as query parameter, HTTP 200 body error
    detection (``Error Message``, ``Note``, ``Information`` keys), polite
    delays between requests (using ``time.monotonic()``), SSRF prevention
    via host whitelist, ``DualWindowRateLimiter`` integration, and
    exponential backoff retry logic.

    Parameters
    ----------
    config : AlphaVantageConfig | None
        Alpha Vantage configuration. If ``None``, defaults are used.
    retry_config : RetryConfig | None
        Retry configuration. If ``None``, defaults are used.

    Examples
    --------
    >>> with AlphaVantageSession() as session:
    ...     response = session.get(
    ...         "https://www.alphavantage.co/query",
    ...         params={"function": "TIME_SERIES_DAILY", "symbol": "AAPL"},
    ...     )
    ...     data = response.json()
    """

    def __init__(
        self,
        config: AlphaVantageConfig | None = None,
        retry_config: RetryConfig | None = None,
    ) -> None:
        """Initialize AlphaVantageSession with configuration.

        Parameters
        ----------
        config : AlphaVantageConfig | None
            Alpha Vantage configuration. Defaults to ``AlphaVantageConfig()``.
        retry_config : RetryConfig | None
            Retry configuration. Defaults to ``RetryConfig()``.
        """
        self._config: AlphaVantageConfig = config or AlphaVantageConfig()
        self._retry_config: RetryConfig = retry_config or RetryConfig()
        self._last_request_time: float = 0.0

        # Initialize rate limiter with config values
        self._rate_limiter = DualWindowRateLimiter(
            requests_per_minute=self._config.requests_per_minute,
            requests_per_hour=self._config.requests_per_hour,
        )

        # Create httpx client with timeout and explicit SSL verification
        self._client: httpx.Client = httpx.Client(
            timeout=httpx.Timeout(self._config.timeout),
            verify=True,
        )

        logger.info(
            "AlphaVantageSession initialized",
            polite_delay=self._config.polite_delay,
            delay_jitter=self._config.delay_jitter,
            timeout=self._config.timeout,
            max_retry_attempts=self._retry_config.max_attempts,
            base_url=BASE_URL,
        )

    # =========================================================================
    # Public API
    # =========================================================================

    def get(
        self,
        url: str,
        params: dict[str, str] | None = None,
    ) -> httpx.Response:
        """Send a GET request with API key injection, polite delay, and error detection.

        Applies the following before each request:

        1. URL whitelist validation (SSRF prevention)
        2. API key resolution and injection
        3. Rate limiter acquisition
        4. Polite delay (monotonic-clock-based interval control)
        5. HTTP request execution
        6. Response status and body error detection

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
        AlphaVantageAuthError
            If the API key is missing or the API returns an auth error.
        AlphaVantageRateLimitError
            If the API returns a rate limit error (HTTP 429 or body ``Note``).
        AlphaVantageAPIError
            If the API returns an error response.
        """
        # 0. URL whitelist validation (SSRF prevention, CWE-918)
        self._validate_url(url)

        # 1. Resolve API key and inject into params
        api_key = self._resolve_api_key()
        params = dict(params) if params else {}
        params["apikey"] = api_key

        # 2. Acquire rate limiter slot
        self._rate_limiter.acquire()

        # 3. Apply polite delay (monotonic-clock-based)
        self._polite_delay()

        logger.debug("Sending GET request", url=url)

        # 4. Execute request
        response: httpx.Response = self._client.get(
            url,
            params=params,
        )

        # 5. Handle response status codes
        self._handle_response_status(response, url)

        # 6. Handle HTTP 200 body errors
        self._handle_response_body(response, url)

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
        is retried after an exponentially increasing delay.

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
        AlphaVantageRateLimitError
            If all retry attempts fail due to rate limiting.
        AlphaVantageAPIError
            If all retry attempts fail due to server errors.
        """
        last_error: AlphaVantageRateLimitError | AlphaVantageAPIError | None = None

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

            except (AlphaVantageRateLimitError, AlphaVantageAPIError) as e:
                # Only retry on rate limit and 5xx errors
                if isinstance(e, AlphaVantageAPIError) and e.status_code < 500:
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
        logger.debug("AlphaVantageSession closed")

    def __enter__(self) -> AlphaVantageSession:
        """Support context manager protocol.

        Returns
        -------
        AlphaVantageSession
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

    def _resolve_api_key(self) -> str:
        """Resolve the API key from config or environment variable.

        Returns
        -------
        str
            The resolved API key.

        Raises
        ------
        AlphaVantageAuthError
            If no API key is available.
        """
        api_key = self._config.api_key or os.environ.get(ALPHA_VANTAGE_API_KEY_ENV, "")

        if not api_key:
            raise AlphaVantageAuthError(
                f"Alpha Vantage API key not provided. "
                f"Set {ALPHA_VANTAGE_API_KEY_ENV} environment variable "
                f"or pass it via AlphaVantageConfig(api_key=...)."
            )

        return api_key

    def _validate_url(self, url: str) -> None:
        """Validate URL against the allowed hosts whitelist (SSRF prevention).

        Parameters
        ----------
        url : str
            The URL to validate.

        Raises
        ------
        ValueError
            If the URL host is not in ``ALLOWED_HOSTS`` or the scheme
            is not http/https.
        """
        parsed = urlparse(url)
        if parsed.scheme not in ("http", "https"):
            raise ValueError(
                f"URL scheme must be 'http' or 'https', got '{parsed.scheme}'"
            )
        parsed_host = parsed.netloc
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
            required_delay = self._config.polite_delay + random.uniform(  # nosec B311
                0, self._config.delay_jitter
            )
            remaining = required_delay - elapsed
            if remaining > 0:
                time.sleep(remaining)
                logger.debug("Polite delay applied", delay_seconds=remaining)

        self._last_request_time = time.monotonic()

    def _handle_response_status(self, response: httpx.Response, url: str) -> None:
        """Check HTTP status code and raise appropriate exceptions.

        Parameters
        ----------
        response : httpx.Response
            The HTTP response to check.
        url : str
            The request URL for error context.

        Raises
        ------
        AlphaVantageRateLimitError
            If HTTP 429 is returned.
        AlphaVantageAPIError
            If HTTP 4xx or 5xx is returned.
        """
        status = response.status_code

        # 429: rate limit
        if status == _RATE_LIMIT_STATUS_CODE:
            retry_after_header = response.headers.get("Retry-After")
            retry_after = int(retry_after_header) if retry_after_header else None
            logger.warning(
                "Rate limit detected (HTTP 429)",
                url=url,
                status_code=status,
                retry_after=retry_after,
            )
            raise AlphaVantageRateLimitError(
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
            raise AlphaVantageAPIError(
                message=f"Client error: HTTP {status}",
                url=url,
                status_code=status,
                response_body=response.text[:MAX_RESPONSE_BODY_LOG],
            )

        # 5xx: server error
        if status >= 500:
            logger.warning(
                "Server error",
                url=url,
                status_code=status,
            )
            raise AlphaVantageAPIError(
                message=f"Server error: HTTP {status}",
                url=url,
                status_code=status,
                response_body=response.text[:MAX_RESPONSE_BODY_LOG],
            )

    def _handle_response_body(self, response: httpx.Response, url: str) -> None:
        """Detect Alpha Vantage-specific errors in HTTP 200 response bodies.

        Alpha Vantage returns HTTP 200 for all responses, including errors.
        This method inspects the response body for known error keys:

        - ``Note`` -> ``AlphaVantageRateLimitError`` (API call frequency limit)
        - ``Error Message`` -> ``AlphaVantageAPIError`` or ``AlphaVantageAuthError``
        - ``Information`` -> ``AlphaVantageAuthError`` (premium endpoint restriction)

        Parameters
        ----------
        response : httpx.Response
            The HTTP 200 response to inspect.
        url : str
            The request URL for error context.

        Raises
        ------
        AlphaVantageRateLimitError
            If the response contains a ``Note`` key indicating rate limiting.
        AlphaVantageAuthError
            If the response contains an auth-related error.
        AlphaVantageAPIError
            If the response contains an ``Error Message`` key.
        """
        try:
            data = response.json()
        except Exception:
            # If we can't parse JSON, it's not an AV error pattern
            return

        if not isinstance(data, dict):
            return

        # Check for "Note" key -> rate limit
        if "Note" in data:
            note_msg = str(data["Note"])
            logger.warning(
                "Rate limit detected in response body (Note key)",
                url=url,
                note=note_msg[:MAX_RESPONSE_BODY_LOG],
            )
            raise AlphaVantageRateLimitError(
                message=f"Rate limit detected: {note_msg[:MAX_RESPONSE_BODY_LOG]}",
                url=url,
                retry_after=60,
            )

        # Check for "Error Message" key
        if "Error Message" in data:
            error_msg = str(data["Error Message"])
            error_msg_lower = error_msg.lower()

            # Check if it's an auth error
            if any(keyword in error_msg_lower for keyword in _AUTH_ERROR_KEYWORDS):
                logger.warning(
                    "Authentication error detected in response body",
                    url=url,
                    error=error_msg[:MAX_RESPONSE_BODY_LOG],
                )
                raise AlphaVantageAuthError(
                    f"Authentication error: {error_msg[:MAX_RESPONSE_BODY_LOG]}"
                )

            # Generic API error
            logger.warning(
                "API error detected in response body (Error Message key)",
                url=url,
                error=error_msg[:MAX_RESPONSE_BODY_LOG],
            )
            raise AlphaVantageAPIError(
                message=f"API error: {error_msg[:MAX_RESPONSE_BODY_LOG]}",
                url=url,
                status_code=200,
                response_body=error_msg[:MAX_RESPONSE_BODY_LOG],
            )

        # Check for "Information" key -> premium endpoint / auth
        if "Information" in data:
            info_msg = str(data["Information"])
            logger.warning(
                "Auth/premium error detected in response body (Information key)",
                url=url,
                information=info_msg[:MAX_RESPONSE_BODY_LOG],
            )
            raise AlphaVantageAuthError(
                f"Premium endpoint or authentication error: {info_msg[:MAX_RESPONSE_BODY_LOG]}"
            )

    def _calculate_backoff_delay(self, attempt: int) -> float:
        """Calculate exponential backoff delay.

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
            self._retry_config.initial_delay
            * (self._retry_config.exponential_base**attempt),
            self._retry_config.max_delay,
        )
        if self._retry_config.jitter:
            delay *= 0.5 + random.random()  # nosec B311
        return delay


__all__ = ["AlphaVantageSession"]
