"""Custom exception classes for the Alpha Vantage API module.

This module provides a hierarchy of exception classes for handling
various error conditions specific to Alpha Vantage API operations,
including authentication failures, API response errors, rate limiting,
data validation errors, and response parsing errors.

Exception Hierarchy
-------------------
AlphaVantageError (base, inherits Exception)
    AlphaVantageAPIError (API response error - 4xx, 5xx)
    AlphaVantageRateLimitError (rate limit exceeded)
    AlphaVantageValidationError (data validation failure)
    AlphaVantageParseError (response parsing failure)
    AlphaVantageAuthError (authentication / API key failure)

Notes
-----
This follows the same ``Exception``-direct-inheritance pattern used by
``market.jquants.errors.JQuantsError`` to avoid circular imports with
``market.errors.MarketError``.

See Also
--------
market.jquants.errors : J-Quants error hierarchy (reference implementation).
"""


class AlphaVantageError(Exception):
    """Base exception for all Alpha Vantage API operations.

    All Alpha Vantage-specific exceptions inherit from this class,
    providing a single catch point for callers that need to handle
    any Alpha Vantage-related failure generically.

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
    ...     raise AlphaVantageError("Alpha Vantage API operation failed")
    ... except AlphaVantageError as e:
    ...     print(e.message)
    Alpha Vantage API operation failed
    """

    def __init__(self, message: str) -> None:
        super().__init__(message)
        self.message = message


class AlphaVantageAPIError(AlphaVantageError):
    """Exception raised when the Alpha Vantage API returns an error response.

    This exception is raised when a request to the Alpha Vantage API
    returns a non-success HTTP status code (4xx or 5xx).

    Parameters
    ----------
    message : str
        Human-readable error message describing the API failure.
    url : str
        The API endpoint URL that returned the error.
    status_code : int
        The HTTP status code returned by the API.
    response_body : str
        The raw response body returned by the API.

    Attributes
    ----------
    url : str
        The API endpoint URL.
    status_code : int
        The HTTP status code.
    response_body : str
        The raw response body.

    Examples
    --------
    >>> raise AlphaVantageAPIError(
    ...     "API returned HTTP 500",
    ...     url="https://www.alphavantage.co/query?function=TIME_SERIES_DAILY",
    ...     status_code=500,
    ...     response_body='{"Error Message": "Internal Server Error"}',
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
        self.response_body = response_body


class AlphaVantageRateLimitError(AlphaVantageError):
    """Exception raised when the Alpha Vantage API rate limit is exceeded.

    Parameters
    ----------
    message : str
        Human-readable error message describing the rate limit.
    url : str | None
        The URL that triggered the rate limit.
    retry_after : int | None
        The number of seconds to wait before retrying.

    Attributes
    ----------
    url : str | None
        The URL that triggered the rate limit.
    retry_after : int | None
        The suggested retry delay in seconds.

    Examples
    --------
    >>> raise AlphaVantageRateLimitError(
    ...     "Rate limit exceeded",
    ...     url="https://www.alphavantage.co/query",
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


class AlphaVantageValidationError(AlphaVantageError):
    """Exception raised when Alpha Vantage data validation fails.

    Parameters
    ----------
    message : str
        Human-readable error message describing the validation failure.
    field : str
        The field that failed validation.
    value : object
        The invalid value that caused the validation failure.

    Attributes
    ----------
    field : str
        The field that failed validation.
    value : object
        The invalid value.

    Examples
    --------
    >>> raise AlphaVantageValidationError(
    ...     "Invalid symbol: must be non-empty",
    ...     field="symbol",
    ...     value="",
    ... )
    """

    def __init__(
        self,
        message: str,
        field: str,
        value: object,
    ) -> None:
        super().__init__(message)
        self.field = field
        self.value = value


class AlphaVantageParseError(AlphaVantageError):
    """Exception raised when Alpha Vantage response parsing fails.

    This exception is specific to Alpha Vantage and is raised when
    the API returns a response that cannot be parsed into the expected
    data structure (e.g., missing expected keys like ``Time Series (Daily)``).

    Parameters
    ----------
    message : str
        Human-readable error message describing the parse failure.
    raw_data : str
        The raw data that could not be parsed.
    field : str
        The field or key that was expected but missing or malformed.

    Attributes
    ----------
    raw_data : str
        The raw data that could not be parsed.
    field : str
        The expected field or key.

    Examples
    --------
    >>> raise AlphaVantageParseError(
    ...     "Missing 'Time Series (Daily)' key in response",
    ...     raw_data='{"Note": "API call frequency limit"}',
    ...     field="Time Series (Daily)",
    ... )
    """

    def __init__(
        self,
        message: str,
        raw_data: str,
        field: str,
    ) -> None:
        super().__init__(message)
        self.raw_data = raw_data
        self.field = field


class AlphaVantageAuthError(AlphaVantageError):
    """Exception raised when Alpha Vantage authentication fails.

    This exception is raised when:
    - The API key is missing or invalid
    - The API key has expired or been revoked
    - The API returns an authentication-related error message

    Parameters
    ----------
    message : str
        Human-readable error message describing the auth failure.

    Examples
    --------
    >>> raise AlphaVantageAuthError("Invalid API key")
    """

    def __init__(self, message: str) -> None:
        super().__init__(message)


__all__ = [
    "AlphaVantageAPIError",
    "AlphaVantageAuthError",
    "AlphaVantageError",
    "AlphaVantageParseError",
    "AlphaVantageRateLimitError",
    "AlphaVantageValidationError",
]
