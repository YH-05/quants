"""Custom exception classes for the SET Exchange module.

This module provides a hierarchy of exception classes for handling
various error conditions specific to SET (Stock Exchange of Thailand)
operations, including API response failures, rate limiting, response
parsing errors, and data validation errors.

Exception Hierarchy
-------------------
SetError (base, inherits Exception)
    SetAPIError (API response error - 4xx, 5xx)
    SetRateLimitError (rate limit exceeded)
    SetParseError (response parse failure)
    SetValidationError (data validation failure)

Notes
-----
This follows the same ``Exception``-direct-inheritance pattern used by
``market.bse.errors.BseError``.

The package name is ``set_exchange`` to avoid collision with the
Python built-in ``set`` type. The error class prefix is ``Set``
for brevity.

See Also
--------
market.bse.errors : BSE error hierarchy (reference implementation).
"""


class SetError(Exception):
    """Base exception for all SET operations.

    All SET-specific exceptions inherit from this class,
    providing a single catch point for callers that need to handle
    any SET-related failure generically.

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
    ...     raise SetError("SET operation failed")
    ... except SetError as e:
    ...     print(e.message)
    SET operation failed
    """

    def __init__(self, message: str) -> None:
        super().__init__(message)
        self.message = message


class SetAPIError(SetError):
    """Exception raised when a SET API returns an error response.

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
    message : str
        The error message.
    url : str
        The API endpoint URL.
    status_code : int
        The HTTP status code.
    response_body : str
        The raw response body.
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


class SetRateLimitError(SetError):
    """Exception raised when the SET API rate limit is exceeded.

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
    message : str
        The error message.
    url : str | None
        The URL that triggered the rate limit.
    retry_after : int | None
        The suggested retry delay in seconds.
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


class SetParseError(SetError):
    """Exception raised when SET API response parsing fails.

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
    """

    def __init__(
        self,
        message: str,
        raw_data: str | None,
        field: str | None,
    ) -> None:
        super().__init__(message)
        self.raw_data = raw_data
        self.field = field


class SetValidationError(SetError):
    """Exception raised when SET data validation fails.

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
    message : str
        The error message.
    field : str
        The field that failed validation.
    value : object
        The invalid value.
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


__all__ = [
    "SetAPIError",
    "SetError",
    "SetParseError",
    "SetRateLimitError",
    "SetValidationError",
]
