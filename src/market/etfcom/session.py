"""HTTP session abstraction for ETF.com scraping with bot-blocking countermeasures.

This module provides the ``ETFComSession`` class, a curl_cffi-based HTTP session
with TLS fingerprint impersonation, User-Agent rotation, polite delays,
bot-block detection, and exponential backoff retry logic.

The session supports both GET requests (for HTML scraping) and POST requests
(for REST API access). Common request logic is unified in ``_request()`` and
``_request_with_retry()`` to avoid duplication.

Examples
--------
Basic GET usage:

>>> with ETFComSession() as session:
...     response = session.get("https://www.etf.com/SPY")
...     print(response.status_code)
200

POST to REST API:

>>> with ETFComSession() as session:
...     response = session.post(
...         "https://api-prod.etf.com/private/apps/fundflows/fund-flows-query",
...         json={"fundId": 1},
...     )
...     print(response.status_code)
200

With retry:

>>> with ETFComSession() as session:
...     response = session.post_with_retry(
...         "https://api-prod.etf.com/private/apps/fundflows/fund-flows-query",
...         json={"fundId": 1},
...     )
...     print(response.status_code)
200

See Also
--------
market.yfinance.session : Similar session pattern for yfinance module.
market.yfinance.fetcher : Session rotation reference implementation.
market.etfcom.constants : Default values, impersonation targets, and API headers.
market.etfcom.types : ScrapingConfig and RetryConfig dataclasses.
market.etfcom.errors : ETFComBlockedError for bot-block detection,
    ETFComNotFoundError for HTTP 404 detection.
"""

import random
import time
from typing import Any, cast

from curl_cffi import requests as curl_requests
from curl_cffi.requests import BrowserTypeLiteral, HttpMethod

from market.etfcom.constants import (
    API_HEADERS,
    BROWSER_IMPERSONATE_TARGETS,
    DEFAULT_HEADERS,
    DEFAULT_USER_AGENTS,
    ETFCOM_BASE_URL,
)
from market.etfcom.errors import ETFComBlockedError, ETFComNotFoundError
from market.etfcom.types import RetryConfig, ScrapingConfig
from utils_core.logging import get_logger

logger = get_logger(__name__)

# HTTP status codes indicating bot-blocking
_BLOCKED_STATUS_CODES: frozenset[int] = frozenset({403, 429})


class ETFComSession:
    """curl_cffi-based HTTP session with bot-blocking countermeasures.

    Provides TLS fingerprint impersonation via curl_cffi's ``impersonate``
    parameter, random User-Agent rotation, polite delays between requests,
    bot-block detection (HTTP 403/429), HTTP 404 not-found detection, and
    exponential backoff retry logic with session rotation on failure.
    HTTP 404 responses raise ``ETFComNotFoundError`` immediately without
    retry, since retrying a non-existent resource is meaningless.

    Parameters
    ----------
    config : ScrapingConfig | None
        Scraping configuration. If None, defaults are used.
    retry_config : RetryConfig | None
        Retry configuration. If None, defaults are used.

    Attributes
    ----------
    _config : ScrapingConfig
        The scraping configuration.
    _retry_config : RetryConfig
        The retry configuration.
    _session : curl_requests.Session
        The underlying curl_cffi session instance.
    _user_agents : list[str]
        User-Agent strings for rotation.

    Examples
    --------
    >>> session = ETFComSession()
    >>> response = session.get("https://www.etf.com/SPY")
    >>> session.close()

    >>> with ETFComSession() as session:
    ...     response = session.get_with_retry("https://www.etf.com/SPY")
    """

    def __init__(
        self,
        config: ScrapingConfig | None = None,
        retry_config: RetryConfig | None = None,
    ) -> None:
        """Initialize ETFComSession with configuration.

        Parameters
        ----------
        config : ScrapingConfig | None
            Scraping configuration. Defaults to ``ScrapingConfig()``.
        retry_config : RetryConfig | None
            Retry configuration. Defaults to ``RetryConfig()``.
        """
        self._config: ScrapingConfig = config or ScrapingConfig()
        self._retry_config: RetryConfig = retry_config or RetryConfig()

        # Resolve user agents: use config value or fall back to defaults
        self._user_agents: list[str] = (
            list(self._config.user_agents)
            if self._config.user_agents
            else list(DEFAULT_USER_AGENTS)
        )

        # Create curl_cffi session with TLS fingerprint impersonation
        self._session: curl_requests.Session = curl_requests.Session(
            impersonate=cast("BrowserTypeLiteral", self._config.impersonate),
        )

        logger.info(
            "ETFComSession initialized",
            impersonate=self._config.impersonate,
            polite_delay=self._config.polite_delay,
            delay_jitter=self._config.delay_jitter,
            timeout=self._config.timeout,
            max_retry_attempts=self._retry_config.max_attempts,
        )

    def _request(
        self, method: HttpMethod, url: str, **kwargs: Any
    ) -> curl_requests.Response:
        """Send an HTTP request with polite delay, header rotation, and block detection.

        This is the shared implementation for ``get()`` and ``post()``.
        Applies the following before each request:

        1. Polite delay (``config.polite_delay`` + random jitter)
        2. Random User-Agent header selection
        3. Referer header set to ``ETFCOM_BASE_URL``
        4. Default browser-like headers from ``DEFAULT_HEADERS``

        After receiving a response, checks for bot-blocking status codes
        (403, 429) and raises ``ETFComBlockedError`` if detected. Also
        checks for HTTP 404 and raises ``ETFComNotFoundError`` immediately
        (without retry, since the resource does not exist).

        Parameters
        ----------
        method : HttpMethod
            The HTTP method (e.g. ``'GET'``, ``'POST'``).
        url : str
            The URL to send the request to.
        **kwargs : Any
            Additional keyword arguments passed to
            ``curl_cffi.Session.request()``.

        Returns
        -------
        curl_requests.Response
            The HTTP response object.

        Raises
        ------
        ETFComBlockedError
            If the response status code is 403 or 429.
        ETFComNotFoundError
            If the response status code is 404.
        """
        # 1. Apply polite delay
        delay = self._config.polite_delay + random.uniform(  # nosec B311
            0, self._config.delay_jitter
        )
        time.sleep(delay)
        logger.debug("Polite delay applied", delay_seconds=delay, url=url)

        # 2. Build headers with User-Agent rotation and Referer
        user_agent = random.choice(self._user_agents)  # nosec B311
        headers: dict[str, str] = {
            **DEFAULT_HEADERS,
            "User-Agent": user_agent,
            "Referer": ETFCOM_BASE_URL,
        }

        # Merge any caller-provided headers
        if "headers" in kwargs:
            headers.update(kwargs.pop("headers"))

        logger.debug(
            "Sending request",
            method=method,
            url=url,
            user_agent=user_agent[:50],
        )

        # 3. Execute request
        response: curl_requests.Response = self._session.request(
            method,
            url,
            headers=headers,
            timeout=self._config.timeout,
            **kwargs,
        )

        # 4. Check for bot-blocking
        if response.status_code in _BLOCKED_STATUS_CODES:
            logger.warning(
                "Bot block detected",
                method=method,
                url=url,
                status_code=response.status_code,
            )
            raise ETFComBlockedError(
                f"Bot detected: HTTP {response.status_code}",
                url=url,
                status_code=response.status_code,
            )

        # 5. Check for 404 Not Found (independent of bot-blocking)
        if response.status_code == 404:
            logger.warning(
                "Resource not found",
                method=method,
                url=url,
                status_code=response.status_code,
            )
            raise ETFComNotFoundError(
                "Resource not found: HTTP 404",
                url=url,
            )

        logger.debug(
            "Request completed",
            method=method,
            url=url,
            status_code=response.status_code,
        )
        return response

    def get(self, url: str, **kwargs: Any) -> curl_requests.Response:
        """Send a GET request with polite delay, header rotation, and block detection.

        Delegates to ``_request('GET', ...)`` with all shared logic
        (polite delay, User-Agent rotation, Referer header, block detection).

        Parameters
        ----------
        url : str
            The URL to send the GET request to.
        **kwargs : Any
            Additional keyword arguments passed to
            ``curl_cffi.Session.request()``.

        Returns
        -------
        curl_requests.Response
            The HTTP response object.

        Raises
        ------
        ETFComBlockedError
            If the response status code is 403 or 429.

        Examples
        --------
        >>> response = session.get("https://www.etf.com/SPY")
        >>> response.status_code
        200
        """
        return self._request("GET", url, **kwargs)

    def post(self, url: str, **kwargs: Any) -> curl_requests.Response:
        """Send a POST request with API headers, polite delay, and block detection.

        Merges ``API_HEADERS`` into the kwargs headers before delegating to
        ``_request('POST', ...)``. The ``API_HEADERS`` include
        ``Content-Type: application/json``, ``Origin``, and ``Referer``
        headers required by the ETF.com REST API.

        Caller-provided headers in ``kwargs`` take precedence over
        ``API_HEADERS`` values.

        Parameters
        ----------
        url : str
            The URL to send the POST request to.
        **kwargs : Any
            Additional keyword arguments passed to
            ``curl_cffi.Session.request()``. Common kwargs include
            ``json`` for JSON payloads and ``headers`` for additional
            headers.

        Returns
        -------
        curl_requests.Response
            The HTTP response object.

        Raises
        ------
        ETFComBlockedError
            If the response status code is 403 or 429.

        Examples
        --------
        >>> response = session.post(
        ...     "https://api-prod.etf.com/private/apps/fundflows/fund-flows-query",
        ...     json={"fundId": 1},
        ... )
        >>> response.status_code
        200
        """
        # Merge API_HEADERS with caller-provided headers
        caller_headers: dict[str, str] = kwargs.pop("headers", {})
        merged_headers: dict[str, str] = {**API_HEADERS, **caller_headers}
        kwargs["headers"] = merged_headers

        return self._request("POST", url, **kwargs)

    def _request_with_retry(
        self, method: HttpMethod, url: str, **kwargs: Any
    ) -> curl_requests.Response:
        """Send an HTTP request with exponential backoff retry and session rotation.

        This is the shared implementation for ``get_with_retry()`` and
        ``post_with_retry()``. On each failed attempt
        (``ETFComBlockedError``), the session is rotated to a new TLS
        fingerprint via ``rotate_session()`` and the request is retried
        after an exponentially increasing delay.

        Parameters
        ----------
        method : HttpMethod
            The HTTP method (e.g. ``'GET'``, ``'POST'``).
        url : str
            The URL to send the request to.
        **kwargs : Any
            Additional keyword arguments passed to ``_request()``.

        Returns
        -------
        curl_requests.Response
            The HTTP response object.

        Raises
        ------
        ETFComBlockedError
            If all retry attempts fail due to bot-blocking.
        """
        last_error: ETFComBlockedError | None = None

        for attempt in range(self._retry_config.max_attempts):
            try:
                # Use the public method for correct header setup (e.g. post()
                # merges API_HEADERS before calling _request()).
                if method == "POST":
                    response = self.post(url, **kwargs)
                else:
                    response = self._request(method, url, **kwargs)

                if attempt > 0:
                    logger.info(
                        "Request succeeded after retry",
                        method=method,
                        url=url,
                        attempt=attempt + 1,
                    )
                return response

            except ETFComBlockedError as e:
                last_error = e
                logger.warning(
                    "Request blocked, will retry",
                    method=method,
                    url=url,
                    attempt=attempt + 1,
                    max_attempts=self._retry_config.max_attempts,
                    status_code=e.status_code,
                )

                # If this is not the last attempt, apply backoff and rotate
                if attempt < self._retry_config.max_attempts - 1:
                    # Calculate exponential backoff delay
                    delay = min(
                        self._retry_config.initial_delay
                        * (self._retry_config.exponential_base**attempt),
                        self._retry_config.max_delay,
                    )

                    # Add jitter if configured
                    if self._retry_config.jitter:
                        delay *= 0.5 + random.random()  # nosec B311

                    logger.debug(
                        "Backoff before retry",
                        delay_seconds=delay,
                        next_attempt=attempt + 2,
                    )
                    time.sleep(delay)

                    # Rotate browser fingerprint
                    self.rotate_session()

        # All attempts exhausted
        logger.error(
            "All retry attempts failed",
            method=method,
            url=url,
            max_attempts=self._retry_config.max_attempts,
        )
        assert last_error is not None
        raise last_error

    def get_with_retry(self, url: str, **kwargs: Any) -> curl_requests.Response:
        """Send a GET request with exponential backoff retry and session rotation.

        Delegates to ``_request_with_retry('GET', ...)`` with all shared
        retry logic (exponential backoff, session rotation).

        Parameters
        ----------
        url : str
            The URL to send the GET request to.
        **kwargs : Any
            Additional keyword arguments passed to ``_request()``.

        Returns
        -------
        curl_requests.Response
            The HTTP response object.

        Raises
        ------
        ETFComBlockedError
            If all retry attempts fail due to bot-blocking.

        Examples
        --------
        >>> response = session.get_with_retry("https://www.etf.com/SPY")
        >>> response.status_code
        200
        """
        return self._request_with_retry("GET", url, **kwargs)

    def post_with_retry(self, url: str, **kwargs: Any) -> curl_requests.Response:
        """Send a POST request with exponential backoff retry and session rotation.

        Delegates to ``_request_with_retry('POST', ...)`` with all shared
        retry logic. The ``API_HEADERS`` are applied on each attempt via
        ``post()``.

        Parameters
        ----------
        url : str
            The URL to send the POST request to.
        **kwargs : Any
            Additional keyword arguments passed to ``post()``. Common
            kwargs include ``json`` for JSON payloads and ``headers``
            for additional headers.

        Returns
        -------
        curl_requests.Response
            The HTTP response object.

        Raises
        ------
        ETFComBlockedError
            If all retry attempts fail due to bot-blocking.

        Examples
        --------
        >>> response = session.post_with_retry(
        ...     "https://api-prod.etf.com/private/apps/fundflows/fund-flows-query",
        ...     json={"fundId": 1},
        ... )
        >>> response.status_code
        200
        """
        return self._request_with_retry("POST", url, **kwargs)

    def rotate_session(self) -> None:
        """Rotate to a new browser impersonation target.

        Closes the current curl_cffi session and creates a new one with
        a randomly selected browser impersonation target from
        ``BROWSER_IMPERSONATE_TARGETS``.

        Examples
        --------
        >>> session.rotate_session()
        """
        self._session.close()

        new_target: str = random.choice(BROWSER_IMPERSONATE_TARGETS)  # nosec B311
        self._session = curl_requests.Session(
            impersonate=cast("BrowserTypeLiteral", new_target),
        )

        logger.info(
            "Session rotated",
            new_impersonate=new_target,
        )

    def close(self) -> None:
        """Close the session and release resources.

        Examples
        --------
        >>> session.close()
        """
        self._session.close()
        logger.debug("ETFComSession closed")

    def __enter__(self) -> "ETFComSession":
        """Support context manager protocol.

        Returns
        -------
        ETFComSession
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


__all__ = ["ETFComSession"]
