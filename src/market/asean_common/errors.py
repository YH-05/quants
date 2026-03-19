"""Custom exception classes for the ASEAN common module.

This module provides a hierarchy of exception classes for handling
various error conditions across ASEAN market sub-packages.

Base Exchange Error Hierarchy
-----------------------------
ExchangeError (base for all per-exchange errors, inherits Exception)
    ExchangeAPIError (API response error - 4xx, 5xx)
    ExchangeRateLimitError (rate limit exceeded)
    ExchangeParseError (response parse failure)
    ExchangeValidationError (data validation failure)

ASEAN Common Error Hierarchy
----------------------------
AseanError (base, inherits Exception)
    AseanStorageError (DuckDB storage operation failure)
    AseanScreenerError (tradingview-screener query failure)
    AseanLookupError (ticker lookup failure)

Notes
-----
Each per-exchange sub-package (sgx, bursa, set_exchange, idx, hose, pse)
defines thin subclasses of the ``Exchange*Error`` hierarchy so that
callers can still catch exchange-specific exceptions by name (e.g.
``SgxAPIError``) while eliminating ~1000 lines of duplicated logic.

See Also
--------
market.bse.errors : BSE error hierarchy (reference implementation).
"""


# =====================================================================
# Base Exchange Error Classes (shared by SGX / Bursa / SET / IDX / HOSE / PSE)
# =====================================================================


class ExchangeError(Exception):
    """Base exception for all per-exchange operations.

    All exchange-specific base exceptions (``SgxError``, ``BursaError``,
    etc.) inherit from this class, providing a single catch point for
    callers that need to handle any exchange-related failure generically.

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
    ...     raise ExchangeError("Exchange operation failed")
    ... except ExchangeError as e:
    ...     print(e.message)
    Exchange operation failed
    """

    def __init__(self, message: str) -> None:
        super().__init__(message)
        self.message = message


class ExchangeAPIError(ExchangeError):
    """Exception raised when an exchange API returns an error response.

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


class ExchangeRateLimitError(ExchangeError):
    """Exception raised when an exchange API rate limit is exceeded.

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


class ExchangeParseError(ExchangeError):
    """Exception raised when exchange API response parsing fails.

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


class ExchangeValidationError(ExchangeError):
    """Exception raised when exchange data validation fails.

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


# =====================================================================
# ASEAN Common Error Classes (storage / screener / lookup)
# =====================================================================


class AseanError(Exception):
    """Base exception for all ASEAN market operations.

    All ASEAN-specific exceptions inherit from this class,
    providing a single catch point for callers that need to handle
    any ASEAN-related failure generically.

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
    ...     raise AseanError("ASEAN operation failed")
    ... except AseanError as e:
    ...     print(e.message)
    ASEAN operation failed
    """

    def __init__(self, message: str) -> None:
        super().__init__(message)
        self.message = message


class AseanStorageError(AseanError):
    """Exception raised when a DuckDB storage operation fails.

    This exception is raised when reading from or writing to
    the ASEAN DuckDB database fails, including connection errors,
    schema mismatches, and data integrity violations.

    Parameters
    ----------
    message : str
        Human-readable error message describing the storage failure.

    Examples
    --------
    >>> raise AseanStorageError("Failed to write ticker data to DuckDB")
    """


class AseanScreenerError(AseanError):
    """Exception raised when a tradingview-screener query fails.

    This exception is raised when the tradingview-screener library
    returns an error, times out, or returns unexpected data.

    Parameters
    ----------
    message : str
        Human-readable error message describing the screener failure.

    Examples
    --------
    >>> raise AseanScreenerError("TradingView screener query timed out")
    """


class AseanLookupError(AseanError):
    """Exception raised when a ticker lookup fails.

    This exception is raised when a requested ticker cannot be found
    in the ASEAN ticker master database, including name-based lookups
    for numeric code tickers (e.g., Bursa Malaysia).

    Parameters
    ----------
    message : str
        Human-readable error message describing the lookup failure.

    Examples
    --------
    >>> raise AseanLookupError("Ticker not found: 1155.KL")
    """


__all__ = [
    "AseanError",
    "AseanLookupError",
    "AseanScreenerError",
    "AseanStorageError",
    "ExchangeAPIError",
    "ExchangeError",
    "ExchangeParseError",
    "ExchangeRateLimitError",
    "ExchangeValidationError",
]
