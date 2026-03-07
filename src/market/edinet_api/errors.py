"""Custom exception classes for the EDINET disclosure API module.

This module provides a hierarchy of exception classes for handling
various error conditions specific to EDINET disclosure API operations
(``api.edinet-fsa.go.jp``), including API response failures,
rate limiting, and data validation errors.

This module is for the **EDINET disclosure API** and is completely
separate from ``market.edinet.errors`` which covers the EDINET DB API.

Exception Hierarchy
-------------------
EdinetApiError (base, inherits MarketError)
    EdinetApiAPIError (HTTP 4xx/5xx response)
    EdinetApiRateLimitError (rate limit exceeded)
    EdinetApiValidationError (input validation failure)

Notes
-----
This follows the same inheritance pattern used by
``market.bse.errors.BseError`` and ``market.edinet.errors.EdinetError``,
but inherits from ``MarketError`` as specified in the issue.

See Also
--------
market.edinet.errors : EDINET DB API error hierarchy.
market.bse.errors : BSE error hierarchy (reference implementation).
"""

from market.errors import MarketError


class EdinetApiError(MarketError):
    """Base exception for all EDINET disclosure API operations.

    All EDINET disclosure API-specific exceptions inherit from this class,
    providing a single catch point for callers that need to handle
    any EDINET disclosure API-related failure generically.

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
    ...     raise EdinetApiError("EDINET disclosure API operation failed")
    ... except EdinetApiError as e:
    ...     print(e.message)
    EDINET disclosure API operation failed
    """

    def __init__(self, message: str) -> None:
        super().__init__(message)
        self.message = message


class EdinetApiAPIError(EdinetApiError):
    """Exception raised when the EDINET disclosure API returns an error response.

    This exception is raised when a request to the EDINET disclosure API
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
    >>> raise EdinetApiAPIError(
    ...     "API returned HTTP 500",
    ...     url="https://api.edinet-fsa.go.jp/api/v2/documents.json",
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


class EdinetApiRateLimitError(EdinetApiError):
    """Exception raised when the EDINET disclosure API rate limit is exceeded.

    This exception is raised when the EDINET disclosure API returns
    a rate limiting response (HTTP 429), indicating that too many
    requests have been sent in a given time period.

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
    >>> raise EdinetApiRateLimitError(
    ...     "Rate limit exceeded",
    ...     url="https://api.edinet-fsa.go.jp/api/v2/documents.json",
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


class EdinetApiValidationError(EdinetApiError):
    """Exception raised when input validation fails for an EDINET API request.

    This exception is raised when caller-provided arguments do not meet
    the expected format or constraints, such as an invalid date format
    or an unsupported document type.

    Parameters
    ----------
    message : str
        Human-readable error message describing the validation failure.
    field : str
        The name of the field that failed validation.
    value : object
        The invalid value that was provided.

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
    >>> raise EdinetApiValidationError(
    ...     "Invalid date format: expected YYYY-MM-DD",
    ...     field="date",
    ...     value="2025/01/15",
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
    "EdinetApiAPIError",
    "EdinetApiError",
    "EdinetApiRateLimitError",
    "EdinetApiValidationError",
]
