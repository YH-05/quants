"""Custom exception classes for the EODHD API module.

This module provides a hierarchy of exception classes for handling
various error conditions specific to EODHD API operations,
including authentication failures, API response errors, rate limiting,
and data validation errors.

Exception Hierarchy
-------------------
EodhdError (base, inherits Exception)
    EodhdAPIError (API response error - 4xx, 5xx)
    EodhdRateLimitError (rate limit exceeded)
    EodhdValidationError (data validation failure)
    EodhdAuthError (authentication / API key failure)

Notes
-----
This follows the same ``Exception``-direct-inheritance pattern used by
``market.jquants.errors.JQuantsError`` to avoid circular imports with
``market.errors.MarketError``.

See Also
--------
market.jquants.errors : J-Quants error hierarchy (reference implementation).
"""


class EodhdError(Exception):
    """Base exception for all EODHD API operations.

    All EODHD-specific exceptions inherit from this class,
    providing a single catch point for callers that need to handle
    any EODHD-related failure generically.

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
    ...     raise EodhdError("EODHD API operation failed")
    ... except EodhdError as e:
    ...     print(e.message)
    EODHD API operation failed
    """

    def __init__(self, message: str) -> None:
        super().__init__(message)
        self.message = message


class EodhdAPIError(EodhdError):
    """Exception raised when the EODHD API returns an error response.

    This exception is raised when a request to the EODHD API
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
    >>> raise EodhdAPIError(
    ...     "API returned HTTP 500",
    ...     url="https://eodhd.com/api/eod/AAPL.US",
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
        self.response_body = response_body


class EodhdRateLimitError(EodhdError):
    """Exception raised when the EODHD API rate limit is exceeded.

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
    >>> raise EodhdRateLimitError(
    ...     "Rate limit exceeded",
    ...     url="https://eodhd.com/api/eod/AAPL.US",
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


class EodhdValidationError(EodhdError):
    """Exception raised when EODHD data validation fails.

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
    >>> raise EodhdValidationError(
    ...     "Invalid symbol format",
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


class EodhdAuthError(EodhdError):
    """Exception raised when EODHD authentication fails.

    This exception is raised when:
    - API key is invalid or expired
    - API key has insufficient permissions
    - API key is missing

    Parameters
    ----------
    message : str
        Human-readable error message describing the auth failure.

    Examples
    --------
    >>> raise EodhdAuthError("Invalid API key")
    """

    def __init__(self, message: str) -> None:
        super().__init__(message)


__all__ = [
    "EodhdAPIError",
    "EodhdAuthError",
    "EodhdError",
    "EodhdRateLimitError",
    "EodhdValidationError",
]
