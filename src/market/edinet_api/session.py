"""HTTP session abstraction for EDINET disclosure API access.

This module provides the ``EdinetApiSession`` class, an httpx-based HTTP
session with X-API-Key header authentication, polite delays
(monotonic-clock-based), SSRF prevention via host whitelist, and
exponential backoff retry logic.

This module is for the **EDINET disclosure API** (``api.edinet-fsa.go.jp``)
and is completely separate from ``market.edinet.client`` which uses the
EDINET DB API (``edinetdb.jp``).

The design integrates patterns from:

- ``market.bse.session.BseSession`` (polite delay, SSRF prevention, retry)
- ``market.edinet.client.EdinetClient`` (httpx, X-API-Key, polite delay)

Examples
--------
Basic GET usage:

>>> with EdinetApiSession(config=EdinetApiConfig(api_key="key")) as session:
...     response = session.get(
...         "https://api.edinet-fsa.go.jp/api/v2/documents.json",
...         params={"date": "2025-01-15", "type": "2"},
...     )
...     print(response.status_code)
200

With retry:

>>> with EdinetApiSession(config=EdinetApiConfig(api_key="key")) as session:
...     response = session.get_with_retry(
...         "https://api.edinet-fsa.go.jp/api/v2/documents.json",
...         params={"date": "2025-01-15", "type": "2"},
...     )

See Also
--------
market.bse.session : httpx-based session pattern reference.
market.edinet.client : X-API-Key authentication reference.
market.edinet_api.constants : Default values, allowed hosts.
market.edinet_api.types : EdinetApiConfig and RetryConfig dataclasses.
market.edinet_api.errors : EdinetApiRateLimitError, EdinetApiAPIError.
"""

import random
import time
from typing import Any
from urllib.parse import urlparse

import httpx

from market.edinet_api.constants import ALLOWED_HOSTS
from market.edinet_api.errors import EdinetApiAPIError, EdinetApiRateLimitError
from market.edinet_api.types import EdinetApiConfig, RetryConfig
from utils_core.logging import get_logger

logger = get_logger(__name__)

# HTTP status code indicating rate limiting
_RATE_LIMIT_STATUS_CODE = 429

# Maximum length of response body stored in EdinetApiAPIError (CWE-209 mitigation)
_MAX_RESPONSE_BODY_LOG = 200


class EdinetApiSession:
    """httpx-based HTTP session for EDINET disclosure API.

    Provides X-API-Key header authentication, polite delays between
    requests (using ``time.monotonic()`` to measure elapsed time),
    SSRF prevention via host whitelist, response status handling
    (429 -> ``EdinetApiRateLimitError``, 4xx/5xx -> ``EdinetApiAPIError``),
    and exponential backoff retry logic.

    Parameters
    ----------
    config : EdinetApiConfig | None
        EDINET API configuration. If ``None``, defaults are used.
    retry_config : RetryConfig | None
        Retry configuration. If ``None``, defaults are used.

    Attributes
    ----------
    _config : EdinetApiConfig
        The EDINET API configuration.
    _retry_config : RetryConfig
        The retry configuration.
    _client : httpx.Client
        The underlying httpx client instance.
    _last_request_time : float
        Monotonic timestamp of the last request (for polite delay).

    Examples
    --------
    >>> session = EdinetApiSession(config=EdinetApiConfig(api_key="key"))
    >>> response = session.get(
    ...     "https://api.edinet-fsa.go.jp/api/v2/documents.json",
    ...     params={"date": "2025-01-15", "type": "2"},
    ... )
    >>> session.close()

    >>> with EdinetApiSession(config=EdinetApiConfig(api_key="key")) as session:
    ...     response = session.get_with_retry(
    ...         "https://api.edinet-fsa.go.jp/api/v2/documents.json",
    ...         params={"date": "2025-01-15", "type": "2"},
    ...     )
    """

    def __init__(
        self,
        config: EdinetApiConfig | None = None,
        retry_config: RetryConfig | None = None,
    ) -> None:
        """Initialize EdinetApiSession with configuration.

        Parameters
        ----------
        config : EdinetApiConfig | None
            EDINET API configuration. Defaults to ``EdinetApiConfig()``.
        retry_config : RetryConfig | None
            Retry configuration. Defaults to ``RetryConfig()``.
        """
        self._config: EdinetApiConfig = config or EdinetApiConfig()
        self._retry_config: RetryConfig = retry_config or RetryConfig()
        self._last_request_time: float = 0.0

        # Create httpx client with timeout, SSL verification, and X-API-Key header
        self._client: httpx.Client = httpx.Client(
            timeout=httpx.Timeout(self._config.timeout),
            verify=True,
            headers={"X-API-Key": self._config.api_key},
        )

        logger.info(
            "EdinetApiSession initialized",
            polite_delay=self._config.polite_delay,
            delay_jitter=self._config.delay_jitter,
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
        """Send a GET request with polite delay, SSRF prevention, and status handling.

        Applies the following before each request:

        1. URL whitelist validation (SSRF prevention)
        2. Polite delay (monotonic-clock-based interval control)

        After receiving a response, checks for error status codes:

        - 429 -> ``EdinetApiRateLimitError``
        - 4xx -> ``EdinetApiAPIError``
        - 5xx -> ``EdinetApiAPIError``

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
        EdinetApiRateLimitError
            If the response status code is 429.
        EdinetApiAPIError
            If the response status code is 4xx or 5xx.

        Examples
        --------
        >>> response = session.get(
        ...     "https://api.edinet-fsa.go.jp/api/v2/documents.json",
        ...     params={"date": "2025-01-15", "type": "2"},
        ... )
        >>> response.status_code
        200
        """
        # 0. URL whitelist validation (SSRF prevention, CWE-918)
        self._validate_url(url)

        # 1. Apply polite delay (monotonic-clock-based)
        self._polite_delay()

        logger.debug("Sending GET request", url=url)

        # 2. Execute request
        response: httpx.Response = self._client.get(
            url,
            params=params,
            timeout=self._config.timeout,
        )

        # 3. Handle response status
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

        On each failed attempt (``EdinetApiRateLimitError`` or 5xx),
        the request is retried after an exponentially increasing delay.

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
        EdinetApiRateLimitError
            If all retry attempts fail due to rate limiting.
        EdinetApiAPIError
            If all retry attempts fail due to server errors.

        Examples
        --------
        >>> response = session.get_with_retry(
        ...     "https://api.edinet-fsa.go.jp/api/v2/documents.json",
        ...     params={"date": "2025-01-15", "type": "2"},
        ... )
        >>> response.status_code
        200
        """
        last_error: EdinetApiRateLimitError | EdinetApiAPIError | None = None

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

            except EdinetApiRateLimitError as e:
                last_error = e
                logger.warning(
                    "Request rate-limited, will retry",
                    url=url,
                    attempt=attempt + 1,
                    max_attempts=self._retry_config.max_attempts,
                )

                if attempt < self._retry_config.max_attempts - 1:
                    delay = self._calculate_backoff_delay(attempt)
                    logger.debug(
                        "Backoff before retry",
                        delay_seconds=delay,
                        next_attempt=attempt + 2,
                    )
                    time.sleep(delay)

            except EdinetApiAPIError as e:
                # Only retry on 5xx server errors
                if e.status_code < 500:
                    raise

                last_error = e
                logger.warning(
                    "Server error, will retry",
                    url=url,
                    status_code=e.status_code,
                    attempt=attempt + 1,
                    max_attempts=self._retry_config.max_attempts,
                )

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
        assert last_error is not None
        raise last_error

    def download(self, url: str, params: dict[str, str] | None = None) -> bytes:
        """Download binary content via streaming.

        Sends a GET request and returns the raw response content
        as bytes using streaming download. Validates URL and handles
        error responses.

        Parameters
        ----------
        url : str
            The URL to download from.
        params : dict[str, str] | None
            Optional query parameters for the request.

        Returns
        -------
        bytes
            The raw response content.

        Raises
        ------
        ValueError
            If the URL host is not in the allowed hosts whitelist.
        EdinetApiRateLimitError
            If the response status code is 429.
        EdinetApiAPIError
            If the response status code indicates an error.

        Examples
        --------
        >>> content = session.download(
        ...     "https://disclosure2dl.edinet-fsa.go.jp/api/v2/documents/S100ABCD",
        ...     params={"type": "1"},
        ... )
        >>> len(content) > 0
        True
        """
        # 0. URL whitelist validation (SSRF prevention)
        self._validate_url(url)

        # 1. Apply polite delay
        self._polite_delay()

        logger.debug("Starting streaming download", url=url)

        # 2. Execute streaming request
        chunks: list[bytes] = []
        with self._client.stream(
            "GET",
            url,
            params=params,
            timeout=self._config.timeout,
        ) as response:
            # 3. Handle response status before reading body
            self._handle_response(response, url)

            for chunk in response.iter_bytes():
                chunks.append(chunk)

        content = b"".join(chunks)
        logger.info(
            "Download completed",
            url=url,
            content_length=len(content),
        )
        return content

    # =========================================================================
    # Context Manager
    # =========================================================================

    def close(self) -> None:
        """Close the session and release resources.

        Examples
        --------
        >>> session.close()
        """
        self._client.close()
        logger.debug("EdinetApiSession closed")

    def __enter__(self) -> "EdinetApiSession":
        """Support context manager protocol.

        Returns
        -------
        EdinetApiSession
            Self for use in with statement.
        """
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: Any,
    ) -> None:
        """Close session on context exit.

        Parameters
        ----------
        exc_type : type[BaseException] | None
            Exception type if an exception was raised.
        exc_val : BaseException | None
            Exception instance if an exception was raised.
        exc_tb : Any
            Traceback if an exception was raised.
        """
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
            If the URL host is not in ``ALLOWED_HOSTS``.
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
        time has passed. Adds random jitter to appear more human-like.
        """
        now = time.monotonic()

        if self._last_request_time > 0:
            elapsed = now - self._last_request_time
            required_delay = self._config.polite_delay + random.uniform(  # nosec B311 (cryptographic randomness not required for delay jitter)
                0, self._config.delay_jitter
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
        EdinetApiRateLimitError
            If HTTP 429 is returned.
        EdinetApiAPIError
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
            raise EdinetApiRateLimitError(
                message=f"Rate limit detected: HTTP {status}",
                url=url,
                retry_after=retry_after,
            )

        # 4xx: client error
        if 400 <= status < 500:
            logger.warning(
                "Client error",
                url=url,
                status_code=status,
            )
            raise EdinetApiAPIError(
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
            raise EdinetApiAPIError(
                message=f"Server error: HTTP {status}",
                url=url,
                status_code=status,
                response_body=response.text[:_MAX_RESPONSE_BODY_LOG],
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
            delay *= 0.5 + random.random()  # nosec B311 (cryptographic randomness not required for retry jitter)
        return delay


__all__ = ["EdinetApiSession"]
