"""Custom exception classes for the Bursa module.

This module provides a hierarchy of exception classes for handling
various error conditions specific to Bursa Malaysia operations,
including API response failures, rate limiting, response parsing errors,
and data validation errors.

Exception Hierarchy
-------------------
BursaError (base, inherits Exception)
    BursaAPIError (API response error - 4xx, 5xx)
    BursaRateLimitError (rate limit exceeded)
    BursaParseError (response parse failure)
    BursaValidationError (data validation failure)

Notes
-----
This follows the same ``Exception``-direct-inheritance pattern used by
``market.bse.errors.BseError``.

See Also
--------
market.bse.errors : BSE error hierarchy (reference implementation).
"""


class BursaError(Exception):
    """Base exception for all Bursa Malaysia operations.

    All Bursa-specific exceptions inherit from this class,
    providing a single catch point for callers that need to handle
    any Bursa-related failure generically.

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
    ...     raise BursaError("Bursa operation failed")
    ... except BursaError as e:
    ...     print(e.message)
    Bursa operation failed
    """

    def __init__(self, message: str) -> None:
        super().__init__(message)
        self.message = message


class BursaAPIError(BursaError):
    """Exception raised when a Bursa API returns an error response.

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


class BursaRateLimitError(BursaError):
    """Exception raised when the Bursa API rate limit is exceeded.

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


class BursaParseError(BursaError):
    """Exception raised when Bursa API response parsing fails.

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


class BursaValidationError(BursaError):
    """Exception raised when Bursa data validation fails.

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
    "BursaAPIError",
    "BursaError",
    "BursaParseError",
    "BursaRateLimitError",
    "BursaValidationError",
]
