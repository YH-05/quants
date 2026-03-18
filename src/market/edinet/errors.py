"""Custom exception classes for the EDINET DB API module.

This module provides a hierarchy of exception classes for handling
various error conditions specific to EDINET DB API operations,
including HTTP errors, rate limiting, input validation, and response
parsing failures.

Exception Hierarchy
-------------------
EdinetError (base, inherits Exception)
    EdinetAPIError (HTTP 4xx/5xx response)
    EdinetRateLimitError (daily API call limit exceeded)
    EdinetValidationError (input validation failure)
    EdinetParseError (response parse failure)

Notes
-----
This follows the same ``Exception``-direct-inheritance pattern used by
``market.nasdaq.errors.NasdaqError`` and ``market.etfcom.errors.ETFComError``.

See Also
--------
market.nasdaq.errors : NASDAQ error hierarchy (reference implementation).
market.etfcom.errors : ETF.com error hierarchy (reference implementation).
"""


class EdinetError(Exception):
    """Base exception for all EDINET DB API operations.

    All EDINET-specific exceptions inherit from this class,
    providing a single catch point for callers that need to handle
    any EDINET-related failure generically.

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
    ...     raise EdinetError("EDINET API operation failed")
    ... except EdinetError as e:
    ...     print(e.message)
    EDINET API operation failed
    """

    def __init__(self, message: str) -> None:
        super().__init__(message)
        self.message = message


class EdinetAPIError(EdinetError):
    """Exception raised when the EDINET DB API returns an error response.

    This exception is raised when a request to the EDINET DB API
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
    >>> raise EdinetAPIError(
    ...     "API returned HTTP 500",
    ...     url="https://edinetdb.jp/v2/companies",
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


class EdinetRateLimitError(EdinetError):
    """Exception raised when the EDINET DB API daily call limit is exceeded.

    This exception is raised when the number of API calls used reaches
    or exceeds the daily limit imposed by the EDINET DB API.

    Parameters
    ----------
    message : str
        Human-readable error message describing the rate limit.
    calls_used : int
        The number of API calls already consumed.
    calls_limit : int
        The maximum number of API calls allowed per day.
    reset_date : str | None
        Date when the rate limit resets (e.g. ``"2026-03-19"``),
        from the ``x-ratelimit-reset`` response header.

    Attributes
    ----------
    message : str
        The error message.
    calls_used : int
        The number of API calls consumed.
    calls_limit : int
        The daily API call limit.
    reset_date : str | None
        Date when the rate limit resets.

    Examples
    --------
    >>> raise EdinetRateLimitError(
    ...     "Daily API limit exceeded",
    ...     calls_used=100,
    ...     calls_limit=100,
    ...     reset_date="2026-03-19",
    ... )
    """

    def __init__(
        self,
        message: str,
        calls_used: int,
        calls_limit: int,
        reset_date: str | None = None,
    ) -> None:
        super().__init__(message)
        self.calls_used = calls_used
        self.calls_limit = calls_limit
        self.reset_date = reset_date


class EdinetValidationError(EdinetError):
    """Exception raised when input validation fails for an EDINET API request.

    This exception is raised when caller-provided arguments do not meet
    the expected format or constraints, such as an invalid EDINET code
    or an unsupported date format.

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
    >>> raise EdinetValidationError(
    ...     "Invalid EDINET code format",
    ...     field="edinet_code",
    ...     value="INVALID",
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


class EdinetParseError(EdinetError):
    """Exception raised when EDINET DB API response parsing fails.

    This exception is raised when the response from the EDINET DB API
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

    Attributes
    ----------
    message : str
        The error message.
    raw_data : str | None
        The raw response data.

    Examples
    --------
    >>> raise EdinetParseError(
    ...     "Failed to parse company list response",
    ...     raw_data='{"unexpected": "format"}',
    ... )
    """

    def __init__(
        self,
        message: str,
        raw_data: str | None,
    ) -> None:
        super().__init__(message)
        self.raw_data = raw_data


__all__ = [
    "EdinetAPIError",
    "EdinetError",
    "EdinetParseError",
    "EdinetRateLimitError",
    "EdinetValidationError",
]
