"""HTTP session abstraction for BSE API access.

This module provides the ``BseSession`` class, an httpx-based HTTP session
with User-Agent rotation, polite delays (monotonic-clock-based),
SSRF prevention via host whitelist, and exponential backoff retry logic.

The design integrates patterns from:

- ``market.edinet.client.EdinetClient`` (httpx, polite delay, retry)
- ``market.nasdaq.session.NasdaqSession`` (UA rotation, SSRF prevention)

Examples
--------
Basic GET usage:

>>> with BseSession() as session:
...     response = session.get(
...         "https://api.bseindia.com/BseIndiaAPI/api/getScripHeaderData",
...         params={"scripcode": "500325"},
...     )
...     print(response.status_code)
200

With retry:

>>> with BseSession() as session:
...     response = session.get_with_retry(
...         "https://api.bseindia.com/BseIndiaAPI/api/getScripHeaderData",
...         params={"scripcode": "500325"},
...     )

Download binary:

>>> with BseSession() as session:
...     content = session.download(
...         "https://www.bseindia.com/download/BhsavCopy/Equity/bhavcopy.csv"
...     )

See Also
--------
market.edinet.client : httpx-based client pattern reference.
market.nasdaq.session : UA rotation / SSRF prevention reference.
market.bse.constants : Default values, allowed hosts, and headers.
market.bse.types : BseConfig and RetryConfig dataclasses.
market.bse.errors : BseRateLimitError, BseAPIError exceptions.
"""

import random
import time
from typing import Any
from urllib.parse import urlparse

import httpx

from market.bse.constants import (
    ALLOWED_HOSTS,
    DEFAULT_HEADERS,
    DEFAULT_USER_AGENTS,
)
from market.bse.errors import BseAPIError, BseRateLimitError
from market.bse.types import BseConfig, RetryConfig
from utils_core.logging import get_logger

logger = get_logger(__name__)

# HTTP status code indicating rate limiting
_RATE_LIMIT_STATUS_CODE = 429


class BseSession:
    """httpx-based HTTP session for BSE API with bot-blocking countermeasures.

    Provides User-Agent rotation, polite delays between requests
    (using ``time.monotonic()`` to measure elapsed time), SSRF
    prevention via host whitelist, response status handling
    (429 -> ``BseRateLimitError``, 403/5xx -> ``BseAPIError``),
    and exponential backoff retry logic.

    Parameters
    ----------
    config : BseConfig | None
        BSE configuration. If ``None``, defaults are used.
    retry_config : RetryConfig | None
        Retry configuration. If ``None``, defaults are used.

    Attributes
    ----------
    _config : BseConfig
        The BSE configuration.
    _retry_config : RetryConfig
        The retry configuration.
    _client : httpx.Client
        The underlying httpx client instance.
    _user_agents : list[str]
        User-Agent strings for rotation.
    _last_request_time : float
        Monotonic timestamp of the last request (for polite delay).

    Examples
    --------
    >>> session = BseSession()
    >>> response = session.get(
    ...     "https://api.bseindia.com/BseIndiaAPI/api/getScripHeaderData",
    ... )
    >>> session.close()

    >>> with BseSession() as session:
    ...     response = session.get_with_retry(
    ...         "https://api.bseindia.com/BseIndiaAPI/api/getScripHeaderData",
    ...         params={"scripcode": "500325"},
    ...     )
    """

    def __init__(
        self,
        config: BseConfig | None = None,
        retry_config: RetryConfig | None = None,
    ) -> None:
        """Initialize BseSession with configuration.

        Parameters
        ----------
        config : BseConfig | None
            BSE configuration. Defaults to ``BseConfig()``.
        retry_config : RetryConfig | None
            Retry configuration. Defaults to ``RetryConfig()``.
        """
        self._config: BseConfig = config or BseConfig()
        self._retry_config: RetryConfig = retry_config or RetryConfig()
        self._last_request_time: float = 0.0

        # Resolve user agents: use config value or fall back to defaults
        self._user_agents: list[str] = (
            list(self._config.user_agents)
            if self._config.user_agents
            else list(DEFAULT_USER_AGENTS)
        )

        # Create httpx client with timeout
        self._client: httpx.Client = httpx.Client(
            timeout=httpx.Timeout(self._config.timeout),
        )

        logger.info(
            "BseSession initialized",
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
        """Send a GET request with polite delay, header rotation, and status handling.

        Applies the following before each request:

        1. URL whitelist validation (SSRF prevention)
        2. Polite delay (monotonic-clock-based interval control)
        3. Random User-Agent header selection
        4. Default browser-like headers

        After receiving a response, checks for error status codes:

        - 429 -> ``BseRateLimitError``
        - 403 -> ``BseAPIError``
        - 5xx -> ``BseAPIError``

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
        BseRateLimitError
            If the response status code is 429.
        BseAPIError
            If the response status code is 403 or 5xx.

        Examples
        --------
        >>> response = session.get(
        ...     "https://api.bseindia.com/BseIndiaAPI/api/getScripHeaderData",
        ...     params={"scripcode": "500325"},
        ... )
        >>> response.status_code
        200
        """
        # 0. URL whitelist validation (SSRF prevention, CWE-918)
        self._validate_url(url)

        # 1. Apply polite delay (monotonic-clock-based)
        self._polite_delay()

        # 2. Build headers with User-Agent rotation
        user_agent = self._rotate_user_agent()
        headers: dict[str, str] = {
            **DEFAULT_HEADERS,
            "User-Agent": user_agent,
        }

        logger.debug(
            "Sending GET request",
            url=url,
            user_agent=user_agent[:50],
        )

        # 3. Execute request
        response: httpx.Response = self._client.get(
            url,
            headers=headers,
            params=params,
            timeout=self._config.timeout,
        )

        # 4. Handle response status
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

        On each failed attempt (``BseRateLimitError``), the request is
        retried after an exponentially increasing delay.

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
        BseRateLimitError
            If all retry attempts fail due to rate limiting.

        Examples
        --------
        >>> response = session.get_with_retry(
        ...     "https://api.bseindia.com/BseIndiaAPI/api/getScripHeaderData",
        ...     params={"scripcode": "500325"},
        ... )
        >>> response.status_code
        200
        """
        last_error: BseRateLimitError | None = None

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

            except BseRateLimitError as e:
                last_error = e
                logger.warning(
                    "Request rate-limited, will retry",
                    url=url,
                    attempt=attempt + 1,
                    max_attempts=self._retry_config.max_attempts,
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
        assert last_error is not None
        raise last_error

    def download(self, url: str) -> bytes:
        """Download binary content (CSV, ZIP, etc.).

        Sends a GET request and returns the raw response content
        as bytes. Validates URL and handles error responses.

        Parameters
        ----------
        url : str
            The URL to download from.

        Returns
        -------
        bytes
            The raw response content.

        Raises
        ------
        ValueError
            If the URL host is not in the allowed hosts whitelist.
        BseRateLimitError
            If the response status code is 429.
        BseAPIError
            If the response status code indicates an error.

        Examples
        --------
        >>> content = session.download(
        ...     "https://www.bseindia.com/download/BhavCopy/bhavcopy.csv",
        ... )
        >>> len(content) > 0
        True
        """
        response = self.get(url)
        logger.info(
            "Download completed",
            url=url,
            content_length=len(response.content),
        )
        return response.content

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
        logger.debug("BseSession closed")

    def __enter__(self) -> "BseSession":
        """Support context manager protocol.

        Returns
        -------
        BseSession
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
        parsed_host = urlparse(url).netloc
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

    def _rotate_user_agent(self) -> str:
        """Select a random User-Agent string for rotation.

        Returns
        -------
        str
            A randomly selected User-Agent string.
        """
        return random.choice(self._user_agents)  # nosec B311 (cryptographic randomness not required for UA rotation)

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
        BseRateLimitError
            If HTTP 429 is returned.
        BseAPIError
            If HTTP 403 or 5xx is returned.
        """
        status = response.status_code

        # 429: rate limit
        if status == _RATE_LIMIT_STATUS_CODE:
            logger.warning(
                "Rate limit detected",
                url=url,
                status_code=status,
            )
            raise BseRateLimitError(
                message=f"Rate limit detected: HTTP {status}",
                url=url,
                retry_after=None,
            )

        # 403: forbidden / bot block
        if status == 403:
            logger.warning(
                "Access forbidden",
                url=url,
                status_code=status,
            )
            raise BseAPIError(
                message=f"Access forbidden: HTTP {status}",
                url=url,
                status_code=status,
                response_body=response.text,
            )

        # 5xx: server error
        if status >= 500:
            logger.warning(
                "Server error",
                url=url,
                status_code=status,
            )
            raise BseAPIError(
                message=f"Server error: HTTP {status}",
                url=url,
                status_code=status,
                response_body=response.text,
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


__all__ = ["BseSession"]
