"""HTTP session abstraction for ETF.com scraping with bot-blocking countermeasures.

This module provides the ``ETFComSession`` class, a curl_cffi-based HTTP session
with TLS fingerprint impersonation, User-Agent rotation, polite delays,
bot-block detection, exponential backoff retry logic, and API authentication
(Cloudflare bypass + ``/api/v1/api-details`` fundApiKey acquisition).

The session supports both GET requests (for HTML scraping) and POST requests
(for REST API access). Common request logic is unified in ``_request()`` and
``_request_with_retry()`` to avoid duplication.

Authentication is lazy: the first call to ``_ensure_authenticated()`` triggers
the Cloudflare bypass + api-details flow. The resulting ``fundApiKey`` is
cached in memory with a 24-hour TTL (``AUTH_TOKEN_TTL_SECONDS``).

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

Authenticated fund details:

>>> with ETFComSession() as session:
...     response = session.post_fund_details("SPY", ["fundFlowsData"])
...     print(response.status_code)
200

See Also
--------
market.yfinance.session : Similar session pattern for yfinance module.
market.yfinance.fetcher : Session rotation reference implementation.
market.alphavantage.session : Reference implementation for auth injection pattern.
market.etfcom.constants : Default values, impersonation targets, and API headers.
market.etfcom.types : ScrapingConfig, RetryConfig, and AuthConfig dataclasses.
market.etfcom.errors : ETFComBlockedError for bot-block detection,
    ETFComNotFoundError for HTTP 404 detection,
    ETFComAPIError for authentication and API errors.
"""

import random
import time
from datetime import datetime, timezone
from typing import Any, cast

from curl_cffi import requests as curl_requests
from curl_cffi.requests import BrowserTypeLiteral, HttpMethod

from market.etfcom.constants import (
    API_HEADERS,
    AUTH_DETAILS_URL,
    AUTH_TOKEN_TTL_SECONDS,
    BROWSER_IMPERSONATE_TARGETS,
    DEFAULT_HEADERS,
    DEFAULT_USER_AGENTS,
    ETFCOM_BASE_URL,
    FUND_DETAILS_URL,
)
from market.etfcom.errors import (
    ETFComAPIError,
    ETFComBlockedError,
    ETFComNotFoundError,
)
from market.etfcom.types import AuthConfig, RetryConfig, ScrapingConfig
from utils_core.logging import get_logger

logger = get_logger(__name__)

# HTTP status codes indicating bot-blocking
_BLOCKED_STATUS_CODES: frozenset[int] = frozenset({403, 429})

# Sensitive keys in the api-details response that must not leak to logs/exceptions
_AUTH_SENSITIVE_KEYS: frozenset[str] = frozenset(
    {"fundApiKey", "toolsApiKey", "oauthToken"}
)

# Required keys in the api-details response (Fix #12: defined once as frozenset)
_AUTH_REQUIRED_KEYS: frozenset[str] = frozenset(
    {
        "apiBaseUrl",
        "fundApiKey",
        "toolsApiKey",
        "oauthToken",
        "realTimeApiUrl",
        "graphQLApiUrl",
    }
)


class ETFComSession:
    """curl_cffi-based HTTP session with bot-blocking countermeasures.

    Provides TLS fingerprint impersonation via curl_cffi's ``impersonate``
    parameter, random User-Agent rotation, polite delays between requests,
    bot-block detection (HTTP 403/429), HTTP 404 not-found detection,
    exponential backoff retry logic with session rotation on failure,
    and lazy API authentication (Cloudflare bypass + fundApiKey acquisition).
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
    _fund_api_key : str | None
        Cached fundApiKey from ``/api/v1/api-details``.
    _auth_expires_at : float
        Monotonic clock time when the cached auth token expires.

    Examples
    --------
    >>> session = ETFComSession()
    >>> response = session.get("https://www.etf.com/SPY")
    >>> session.close()

    >>> with ETFComSession() as session:
    ...     response = session.get_with_retry("https://www.etf.com/SPY")

    >>> with ETFComSession() as session:
    ...     response = session.post_fund_details("SPY", ["fundFlowsData"])
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

        # Authentication state (lazy initialization via _ensure_authenticated)
        self._fund_api_key: str | None = None
        self._auth_expires_at: float = 0.0  # monotonic clock; 0 means not authenticated

        logger.debug(
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
        ETFComNotFoundError
            If the response status code is 404.

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
        ETFComNotFoundError
            If the response status code is 404.

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
        ETFComNotFoundError
            If the response status code is 404 (propagated immediately,
            no retry).
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
        if last_error is None:
            raise RuntimeError("Retry loop exited without capturing an error")
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
        ETFComNotFoundError
            If the response status code is 404 (propagated immediately,
            no retry).

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
        ETFComNotFoundError
            If the response status code is 404 (propagated immediately,
            no retry).

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

    # =========================================================================
    # Authentication methods
    # =========================================================================

    def _authenticate(self) -> AuthConfig:
        """Perform the full authentication flow: Cloudflare bypass + api-details.

        Steps:

        1. GET ``https://www.etf.com`` to acquire Cloudflare cookies.
        2. GET ``/api/v1/api-details`` to retrieve ``fundApiKey``,
           ``toolsApiKey``, ``oauthToken``, and other API configuration.

        Returns
        -------
        AuthConfig
            The parsed authentication credentials.

        Raises
        ------
        ETFComBlockedError
            If the Cloudflare bypass request is blocked (403/429).
        ETFComAPIError
            If the api-details endpoint returns a non-200 status or
            the response JSON is missing required keys.
        """
        # Step 1: Cloudflare bypass — GET www.etf.com to acquire cookies
        logger.info("Starting authentication: Cloudflare bypass")
        self.get(ETFCOM_BASE_URL)

        # Step 2: GET /api/v1/api-details to retrieve API keys
        logger.info("Fetching API details", url=AUTH_DETAILS_URL)
        api_response = self.get(AUTH_DETAILS_URL)

        if api_response.status_code != 200:
            # AIDEV-NOTE: response_body=None to prevent leaking API keys
            # that may be present in the raw response (CWE-532).
            raise ETFComAPIError(
                f"Authentication failed: HTTP {api_response.status_code} "
                f"from {AUTH_DETAILS_URL}",
                url=AUTH_DETAILS_URL,
                status_code=api_response.status_code,
                response_body=None,
            )

        data: dict[str, Any] = api_response.json()

        # Validate required keys (uses module-level frozenset constant)
        missing_keys = sorted(_AUTH_REQUIRED_KEYS - data.keys())
        if missing_keys:
            # AIDEV-NOTE: Mask sensitive key names in response_body to
            # prevent leaking API keys (CWE-532).
            safe_keys = sorted(data.keys() - _AUTH_SENSITIVE_KEYS)
            raise ETFComAPIError(
                f"Missing required keys in api-details response: "
                f"{', '.join(missing_keys)}",
                url=AUTH_DETAILS_URL,
                status_code=200,
                response_body=f"available keys (non-sensitive): {safe_keys}",
            )

        auth_config = AuthConfig(
            api_base_url=data["apiBaseUrl"],
            fund_api_key=data["fundApiKey"],
            tools_api_key=data["toolsApiKey"],
            oauth_token=data["oauthToken"],
            real_time_api_url=data["realTimeApiUrl"],
            graphql_api_url=data["graphQLApiUrl"],
            fetched_at=datetime.now(tz=timezone.utc),
        )

        logger.info(
            "Authentication completed",
            api_base_url=auth_config.api_base_url,
        )
        return auth_config

    def _ensure_authenticated(self) -> None:
        """Ensure the session has a valid fundApiKey, authenticating if needed.

        Uses ``time.monotonic()`` to track token expiry. If the cached
        ``_fund_api_key`` is ``None`` or the TTL has expired, triggers
        ``_authenticate()`` to refresh the credentials.
        """
        now = time.monotonic()
        if self._fund_api_key is not None and now < self._auth_expires_at:
            logger.debug("Auth cache hit, skipping re-authentication")
            return

        logger.info("Auth cache miss or expired, authenticating")
        auth_config = self._authenticate()

        # Cache the auth credentials
        self._fund_api_key = auth_config.fund_api_key
        self._auth_expires_at = time.monotonic() + AUTH_TOKEN_TTL_SECONDS

        logger.info(
            "Auth credentials cached",
            ttl_seconds=AUTH_TOKEN_TTL_SECONDS,
        )

    def post_fund_details(
        self,
        ticker: str,
        query_names: list[str],
        **kwargs: Any,
    ) -> curl_requests.Response:
        """Send an authenticated POST to the fund-details endpoint.

        Ensures authentication is current via ``_ensure_authenticated()``,
        then sends a POST request to ``FUND_DETAILS_URL`` with the
        ``fundApiKey`` header and a JSON payload containing the ticker
        and query names.

        Parameters
        ----------
        ticker : str
            The ETF ticker symbol (e.g. ``"SPY"``).
        query_names : list[str]
            List of query names to include in the request
            (from ``FUND_DETAILS_QUERY_NAMES``).
        **kwargs : Any
            Additional keyword arguments passed to ``post()``.

        Returns
        -------
        curl_requests.Response
            The HTTP response object.

        Raises
        ------
        ETFComBlockedError
            If the request is blocked by bot detection.
        ETFComAPIError
            If authentication fails.

        Examples
        --------
        >>> response = session.post_fund_details("SPY", ["fundFlowsData"])
        >>> data = response.json()
        """
        self._ensure_authenticated()

        # AIDEV-NOTE: Explicit guard — _ensure_authenticated must set _fund_api_key.
        # Empty-string fallback would silently send unauthenticated requests.
        if self._fund_api_key is None:
            raise ETFComAPIError(
                "Authentication succeeded but fund_api_key is None",
                url=FUND_DETAILS_URL,
            )

        # Build auth headers
        auth_headers: dict[str, str] = {"fundApiKey": self._fund_api_key}
        caller_headers: dict[str, str] = kwargs.pop("headers", {})
        merged_headers = {**auth_headers, **caller_headers}

        payload = {
            "ticker": ticker,
            "queryNames": query_names,
        }

        logger.debug(
            "Sending authenticated fund details request",
            ticker=ticker,
            query_count=len(query_names),
        )

        return self.post(
            FUND_DETAILS_URL,
            json=payload,
            headers=merged_headers,
            **kwargs,
        )

    def get_authenticated(self, url: str, **kwargs: Any) -> curl_requests.Response:
        """Send an authenticated GET request with the fundApiKey header.

        Ensures authentication is current via ``_ensure_authenticated()``,
        then sends a GET request with the ``fundApiKey`` header injected.

        Parameters
        ----------
        url : str
            The URL to send the GET request to.
        **kwargs : Any
            Additional keyword arguments passed to ``get()``.

        Returns
        -------
        curl_requests.Response
            The HTTP response object.

        Raises
        ------
        ETFComBlockedError
            If the request is blocked by bot detection.
        ETFComAPIError
            If authentication fails.

        Examples
        --------
        >>> response = session.get_authenticated(
        ...     "https://api-prod.etf.com/v2/quotes/delayedquotes?tickers=SPY"
        ... )
        >>> data = response.json()
        """
        self._ensure_authenticated()

        # AIDEV-NOTE: Explicit guard — _ensure_authenticated must set _fund_api_key.
        if self._fund_api_key is None:
            raise ETFComAPIError(
                "Authentication succeeded but fund_api_key is None",
                url=url,
            )

        auth_headers: dict[str, str] = {"fundApiKey": self._fund_api_key}
        caller_headers: dict[str, str] = kwargs.pop("headers", {})
        merged_headers = {**auth_headers, **caller_headers}

        logger.debug("Sending authenticated GET request", url=url)

        return self.get(url, headers=merged_headers, **kwargs)

    # =========================================================================
    # Session rotation
    # =========================================================================

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
