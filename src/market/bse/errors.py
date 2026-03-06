"""Custom exception classes for the BSE API module.

This module provides a hierarchy of exception classes for handling
various error conditions specific to BSE API operations,
including API response failures, rate limiting, response parsing errors,
and data validation errors.

Exception Hierarchy
-------------------
BseError (base, inherits Exception)
    BseAPIError (API response error - 4xx, 5xx)
    BseRateLimitError (rate limit exceeded)
    BseParseError (response parse failure)
    BseValidationError (data validation failure)

Notes
-----
This follows the same ``Exception``-direct-inheritance pattern used by
``market.nasdaq.errors.NasdaqError``.

See Also
--------
market.nasdaq.errors : NASDAQ error hierarchy (reference implementation).
"""


class BseError(Exception):
    """Base exception for all BSE API operations.

    All BSE-specific exceptions inherit from this class,
    providing a single catch point for callers that need to handle
    any BSE-related failure generically.

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
    ...     raise BseError("BSE API operation failed")
    ... except BseError as e:
    ...     print(e.message)
    BSE API operation failed
    """

    def __init__(self, message: str) -> None:
        super().__init__(message)
        self.message = message


class BseAPIError(BseError):
    """Exception raised when the BSE API returns an error response.

    This exception is raised when a request to the BSE API
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
    >>> raise BseAPIError(
    ...     "API returned HTTP 500",
    ...     url="https://api.bseindia.com/BseIndiaAPI/api/getScripHeaderData",
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


class BseRateLimitError(BseError):
    """Exception raised when the BSE API rate limit is exceeded.

    This exception is raised when the BSE API returns a rate
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
    >>> raise BseRateLimitError(
    ...     "Rate limit exceeded",
    ...     url="https://api.bseindia.com/BseIndiaAPI/api/getScripHeaderData",
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


class BseParseError(BseError):
    """Exception raised when BSE API response parsing fails.

    This exception is raised when the response from the BSE API
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
    >>> raise BseParseError(
    ...     "Failed to parse scrip header response",
    ...     raw_data='{"Table": null}',
    ...     field="Table",
    ... )
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


class BseValidationError(BseError):
    """Exception raised when BSE data validation fails.

    This exception is raised when data retrieved from the BSE API
    fails validation checks, such as invalid scrip codes, unexpected
    field values, or data integrity issues.

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

    Examples
    --------
    >>> raise BseValidationError(
    ...     "Invalid scrip code: must be a positive integer",
    ...     field="scrip_code",
    ...     value=-1,
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


__all__ = [
    "BseAPIError",
    "BseError",
    "BseParseError",
    "BseRateLimitError",
    "BseValidationError",
]
