"""Custom exception classes for the NASDAQ API module.

This module provides a hierarchy of exception classes for handling
various error conditions specific to NASDAQ API operations,
including API response failures, rate limiting, and response parsing errors.

Exception Hierarchy
-------------------
NasdaqError (base, inherits Exception)
    NasdaqAPIError (API response error - 4xx, 5xx)
    NasdaqRateLimitError (rate limit exceeded)
    NasdaqParseError (response parse failure)

Notes
-----
This follows the same ``Exception``-direct-inheritance pattern used by
``market.etfcom.errors.ETFComError``.

See Also
--------
market.errors : Unified error hierarchy for the market package.
market.etfcom.errors : ETF.com error hierarchy (reference implementation).
"""


class NasdaqError(Exception):
    """Base exception for all NASDAQ API operations.

    All NASDAQ-specific exceptions inherit from this class,
    providing a single catch point for callers that need to handle
    any NASDAQ-related failure generically.

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
    ...     raise NasdaqError("NASDAQ API operation failed")
    ... except NasdaqError as e:
    ...     print(e.message)
    NASDAQ API operation failed
    """

    def __init__(self, message: str) -> None:
        super().__init__(message)
        self.message = message


class NasdaqAPIError(NasdaqError):
    """Exception raised when the NASDAQ API returns an error response.

    This exception is raised when a request to the NASDAQ API
    returns a non-success HTTP status code (4xx or 5xx). It provides
    contextual attributes to aid debugging and error handling.

    Parameters
    ----------
    message : str
        Human-readable error message describing the API failure.
    url : str
        The API endpoint URL that returned the error.
    status_code : int
        The HTTP status code returned by the API (e.g. 400, 403, 500).
    response_body : str
        The raw response body returned by the API, useful for
        diagnosing unexpected response formats.

    Attributes
    ----------
    message : str
        The error message.
    url : str
        The API endpoint URL.
    status_code : int
        The HTTP status code.
    response_body : str
        The raw response body.

    Examples
    --------
    >>> raise NasdaqAPIError(
    ...     "API returned HTTP 500",
    ...     url="https://api.nasdaq.com/api/screener/stocks",
    ...     status_code=500,
    ...     response_body='{"error": "Internal Server Error"}',
    ... )
    """

    def __init__(
        self,
        message: str,
        url: str,
        status_code: int,
        response_body: str,
    ) -> None:
        super().__init__(message)
        self.url = url
        self.status_code = status_code
        # AIDEV-NOTE: response_body は内部デバッグ専用。
        # 上位レイヤーで例外を外部向けレスポンスに変換する際は、
        # このフィールドを含めないこと。
        self.response_body = response_body


class NasdaqRateLimitError(NasdaqError):
    """Exception raised when the NASDAQ API rate limit is exceeded.

    This exception is raised when the NASDAQ API returns a rate
    limiting response, indicating that too many requests have been
    sent in a given time period.

    Parameters
    ----------
    message : str
        Human-readable error message describing the rate limit.
    url : str | None
        The URL that triggered the rate limit.
    retry_after : int | None
        The number of seconds to wait before retrying, as suggested
        by the API response (e.g. from a Retry-After header).

    Attributes
    ----------
    message : str
        The error message.
    url : str | None
        The URL that triggered the rate limit.
    retry_after : int | None
        The suggested retry delay in seconds.

    Examples
    --------
    >>> raise NasdaqRateLimitError(
    ...     "Rate limit exceeded",
    ...     url="https://api.nasdaq.com/api/screener/stocks",
    ...     retry_after=60,
    ... )
    """

    def __init__(
        self,
        message: str,
        url: str | None,
        retry_after: int | None,
    ) -> None:
        super().__init__(message)
        self.url = url
        self.retry_after = retry_after


class NasdaqParseError(NasdaqError):
    """Exception raised when NASDAQ API response parsing fails.

    This exception is raised when the response from the NASDAQ API
    cannot be parsed as expected, typically because:

    - The JSON structure does not match the expected schema.
    - A required field is missing or has an unexpected type.
    - The response body is not valid JSON.

    Parameters
    ----------
    message : str
        Human-readable error message describing the parse failure.
    raw_data : str | None
        The raw response data that failed to parse.
    field : str | None
        The specific field that caused the parse failure.

    Attributes
    ----------
    message : str
        The error message.
    raw_data : str | None
        The raw response data.
    field : str | None
        The field that caused the failure.

    Examples
    --------
    >>> raise NasdaqParseError(
    ...     "Failed to parse stock screener response",
    ...     raw_data='{"data": {"rows": null}}',
    ...     field="rows",
    ... )
    """

    def __init__(
        self,
        message: str,
        raw_data: str | None,
        field: str | None,
    ) -> None:
        super().__init__(message)
        # AIDEV-NOTE: raw_data は内部デバッグ専用。
        # 上位レイヤーで例外を外部向けレスポンスに変換する際は、
        # このフィールドを含めないこと。
        self.raw_data = raw_data
        self.field = field


__all__ = [
    "NasdaqAPIError",
    "NasdaqError",
    "NasdaqParseError",
    "NasdaqRateLimitError",
]
