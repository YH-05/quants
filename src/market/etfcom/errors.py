"""Custom exception classes for the ETF.com scraping module.

This module provides a hierarchy of exception classes for handling
various error conditions specific to ETF.com scraping operations,
including HTML parse failures, page load timeouts, bot-blocking
detection (HTTP 403/429, CAPTCHA redirects), and REST API errors.

Exception Hierarchy
-------------------
ETFComError (base, inherits Exception)
    ETFComScrapingError (HTML parse failure)
    ETFComTimeoutError (page load / navigation timeout)
    ETFComBlockedError (bot-blocking detection)
    ETFComNotFoundError (HTTP 404 not found)
    ETFComAPIError (REST API error response)

Notes
-----
This follows the same ``Exception``-direct-inheritance pattern used by
``market.errors.FREDError`` and ``market.errors.BloombergError``.

See Also
--------
market.errors : Unified error hierarchy for the market package.
market.etfcom.constants : Default timeout values referenced by callers.
"""


class ETFComError(Exception):
    """Base exception for all ETF.com scraping operations.

    All ETF.com-specific exceptions inherit from this class,
    providing a single catch point for callers that need to handle
    any ETF.com-related failure generically.

    Parameters
    ----------
    message : str
        Human-readable error message describing the failure.

    Attributes
    ----------
    message : str
        The error message.

    Examples
    --------
    >>> try:
    ...     raise ETFComError("ETF.com operation failed")
    ... except ETFComError as e:
    ...     print(e.message)
    ETF.com operation failed
    """

    def __init__(self, message: str) -> None:
        super().__init__(message)
        self.message = message


class ETFComScrapingError(ETFComError):
    """Exception raised when HTML parsing / data extraction fails.

    This exception is raised when the expected DOM structure is not
    found on an ETF.com page, typically because:

    - The CSS selector no longer matches (site redesign).
    - The page returned an unexpected format (e.g. error page).
    - Required data fields are missing from the parsed HTML.

    Parameters
    ----------
    message : str
        Human-readable error message describing the parse failure.
    url : str | None
        The URL of the page that failed to parse.
    selector : str | None
        The CSS selector that failed to match.

    Attributes
    ----------
    message : str
        The error message.
    url : str | None
        The URL of the page that failed to parse.
    selector : str | None
        The CSS selector that failed to match.

    Examples
    --------
    >>> raise ETFComScrapingError(
    ...     "Element not found on profile page",
    ...     url="https://www.etf.com/SPY",
    ...     selector="[data-testid='summary-data']",
    ... )
    """

    def __init__(
        self,
        message: str,
        url: str | None,
        selector: str | None,
    ) -> None:
        super().__init__(message)
        self.url = url
        self.selector = selector


class ETFComTimeoutError(ETFComError):
    """Exception raised when a page load or navigation times out.

    This exception is raised when Playwright or an HTTP client
    exceeds the configured timeout while waiting for an ETF.com
    page to load or for a specific element to appear.

    Parameters
    ----------
    message : str
        Human-readable error message describing the timeout.
    url : str | None
        The URL that timed out.
    timeout_seconds : float
        The timeout threshold in seconds that was exceeded.

    Attributes
    ----------
    message : str
        The error message.
    url : str | None
        The URL that timed out.
    timeout_seconds : float
        The timeout threshold in seconds.

    Examples
    --------
    >>> raise ETFComTimeoutError(
    ...     "Page load timed out",
    ...     url="https://www.etf.com/SPY",
    ...     timeout_seconds=30.0,
    ... )
    """

    def __init__(
        self,
        message: str,
        url: str | None,
        timeout_seconds: float,
    ) -> None:
        super().__init__(message)
        self.url = url
        self.timeout_seconds = timeout_seconds


class ETFComBlockedError(ETFComError):
    """Exception raised when bot-blocking is detected.

    This exception is raised when ETF.com returns an HTTP 403
    (Forbidden), 429 (Too Many Requests), or redirects to a
    CAPTCHA verification page, indicating that the scraping
    request has been identified as automated traffic.

    Parameters
    ----------
    message : str
        Human-readable error message describing the block.
    url : str | None
        The URL that triggered the block.
    status_code : int
        The HTTP status code returned (e.g. 403, 429).

    Attributes
    ----------
    message : str
        The error message.
    url : str | None
        The URL that triggered the block.
    status_code : int
        The HTTP status code.

    Examples
    --------
    >>> raise ETFComBlockedError(
    ...     "Bot detected: HTTP 403",
    ...     url="https://www.etf.com/SPY",
    ...     status_code=403,
    ... )
    """

    def __init__(
        self,
        message: str,
        url: str | None,
        status_code: int,
    ) -> None:
        super().__init__(message)
        self.url = url
        self.status_code = status_code


class ETFComNotFoundError(ETFComError):
    """Exception raised when an ETF.com page returns HTTP 404 Not Found.

    This exception is raised when a request to ETF.com returns an
    HTTP 404 status code, indicating that the requested resource
    (e.g. an ETF profile page) does not exist.

    Parameters
    ----------
    message : str
        Human-readable error message describing the not-found condition.
    url : str | None
        The URL that returned 404.
    status_code : int
        The HTTP status code returned (default: 404).

    Attributes
    ----------
    message : str
        The error message.
    url : str | None
        The URL that returned 404.
    status_code : int
        The HTTP status code.

    Examples
    --------
    >>> raise ETFComNotFoundError(
    ...     "ETF not found: HTTP 404",
    ...     url="https://www.etf.com/INVALID",
    ... )
    """

    def __init__(
        self,
        message: str,
        url: str | None,
        status_code: int = 404,
    ) -> None:
        super().__init__(message)
        self.url = url
        self.status_code = status_code


class ETFComAPIError(ETFComError):
    """Exception raised when the ETF.com REST API returns an error response.

    This exception is raised when a request to the ETF.com REST API
    (``api-prod.etf.com``) returns a non-success HTTP status code or
    an unexpected response body. It provides contextual attributes
    to aid debugging and error handling.

    Parameters
    ----------
    message : str
        Human-readable error message describing the API failure.
    url : str | None
        The API endpoint URL that returned the error.
    status_code : int | None
        The HTTP status code returned by the API (e.g. 400, 403, 500).
    response_body : str | None
        The raw response body returned by the API, useful for
        diagnosing unexpected response formats.
    ticker : str | None
        The ETF ticker symbol associated with the failed request,
        if applicable (e.g. during fund flow queries).
    fund_id : int | None
        The fund ID associated with the failed request, if applicable
        (e.g. during fund flow queries after ticker resolution).

    Attributes
    ----------
    message : str
        The error message.
    url : str | None
        The API endpoint URL.
    status_code : int | None
        The HTTP status code.
    response_body : str | None
        The raw response body.
    ticker : str | None
        The ETF ticker symbol.
    fund_id : int | None
        The fund ID.

    Examples
    --------
    >>> raise ETFComAPIError(
    ...     "API returned HTTP 403",
    ...     url="https://api-prod.etf.com/private/apps/fundflows/fund-flows-query",
    ...     status_code=403,
    ...     response_body='{"error": "Forbidden"}',
    ...     ticker="SPY",
    ...     fund_id=1,
    ... )
    """

    def __init__(
        self,
        message: str,
        url: str | None = None,
        status_code: int | None = None,
        response_body: str | None = None,
        ticker: str | None = None,
        fund_id: int | None = None,
    ) -> None:
        super().__init__(message)
        self.url = url
        self.status_code = status_code
        self.response_body = response_body
        self.ticker = ticker
        self.fund_id = fund_id


__all__ = [
    "ETFComAPIError",
    "ETFComBlockedError",
    "ETFComError",
    "ETFComNotFoundError",
    "ETFComScrapingError",
    "ETFComTimeoutError",
]
