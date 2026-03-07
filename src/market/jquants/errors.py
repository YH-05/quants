"""Custom exception classes for the J-Quants API module.

This module provides a hierarchy of exception classes for handling
various error conditions specific to J-Quants API operations,
including authentication failures, API response errors, rate limiting,
and data validation errors.

Exception Hierarchy
-------------------
JQuantsError (base, inherits Exception)
    JQuantsAPIError (API response error - 4xx, 5xx)
    JQuantsRateLimitError (rate limit exceeded)
    JQuantsValidationError (data validation failure)
    JQuantsAuthError (authentication failure)

Notes
-----
This follows the same ``Exception``-direct-inheritance pattern used by
``market.bse.errors.BseError`` to avoid circular imports with
``market.errors.MarketError``.

See Also
--------
market.bse.errors : BSE error hierarchy (reference implementation).
"""


class JQuantsError(Exception):
    """Base exception for all J-Quants API operations.

    All J-Quants-specific exceptions inherit from this class,
    providing a single catch point for callers that need to handle
    any J-Quants-related failure generically.

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
    ...     raise JQuantsError("J-Quants API operation failed")
    ... except JQuantsError as e:
    ...     print(e.message)
    J-Quants API operation failed
    """

    def __init__(self, message: str) -> None:
        super().__init__(message)
        self.message = message


class JQuantsAPIError(JQuantsError):
    """Exception raised when the J-Quants API returns an error response.

    This exception is raised when a request to the J-Quants API
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
    >>> raise JQuantsAPIError(
    ...     "API returned HTTP 500",
    ...     url="https://api.jquants.com/v1/listed/info",
    ...     status_code=500,
    ...     response_body='{"message": "Internal Server Error"}',
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


class JQuantsRateLimitError(JQuantsError):
    """Exception raised when the J-Quants API rate limit is exceeded.

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
    >>> raise JQuantsRateLimitError(
    ...     "Rate limit exceeded",
    ...     url="https://api.jquants.com/v1/listed/info",
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


class JQuantsValidationError(JQuantsError):
    """Exception raised when J-Quants data validation fails.

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
    >>> raise JQuantsValidationError(
    ...     "Invalid stock code: must be 4 digits",
    ...     field="code",
    ...     value="ABC",
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


class JQuantsAuthError(JQuantsError):
    """Exception raised when J-Quants authentication fails.

    This exception is raised when:
    - email/password login fails
    - refresh_token is invalid or expired and re-login also fails
    - id_token refresh fails

    Parameters
    ----------
    message : str
        Human-readable error message describing the auth failure.

    Examples
    --------
    >>> raise JQuantsAuthError("Invalid credentials")
    """

    def __init__(self, message: str) -> None:
        super().__init__(message)


__all__ = [
    "JQuantsAPIError",
    "JQuantsAuthError",
    "JQuantsError",
    "JQuantsRateLimitError",
    "JQuantsValidationError",
]
