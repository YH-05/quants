"""Custom exception classes for the market package.

This module provides a unified hierarchy of exception classes for handling
various error conditions across all market data sources (yfinance, Bloomberg,
FRED, NASDAQ, EDINET, ASEAN, EODHD, etc.).

All exceptions include:
- Error codes for programmatic handling
- Detailed error messages with context
- Optional cause chaining

Exception Hierarchy
-------------------
MarketError (base)
    ExportError (export operations)
    CacheError (cache operations)
    DataFetchError (data fetching - yfinance)
    ValidationError (input validation - yfinance)
    FREDError (FRED operations)
        FREDValidationError (FRED input validation)
        FREDFetchError (FRED data fetching)
            FREDCacheNotFoundError (FRED cache data not found)
    BloombergError (Bloomberg operations)
        BloombergConnectionError (connection failures)
        BloombergSessionError (session management)
        BloombergDataError (data fetching)
        BloombergValidationError (input validation)
    ETFComError (ETF.com scraping operations)
        ETFComScrapingError (HTML parse failure)
        ETFComTimeoutError (page load / navigation timeout)
        ETFComHTTPError (HTTP status code errors)
            ETFComBlockedError (bot-blocking detection)
            ETFComNotFoundError (HTTP 404 not found)
    NasdaqError (NASDAQ API operations)
        NasdaqAPIError (API response error - 4xx, 5xx)
        NasdaqRateLimitError (rate limit exceeded)
        NasdaqParseError (response parse failure)
    EdinetError (EDINET DB API operations)
        EdinetAPIError (API response error - 4xx, 5xx)
        EdinetRateLimitError (daily API call limit exceeded)
        EdinetValidationError (input validation failure)
        EdinetParseError (response parse failure)
    BseError (BSE API operations)
        BseAPIError (API response error - 4xx, 5xx)
        BseRateLimitError (rate limit exceeded)
        BseParseError (response parse failure)
        BseValidationError (data validation failure)
    JQuantsError (J-Quants API operations)
        JQuantsAPIError (API response error - 4xx, 5xx)
        JQuantsRateLimitError (rate limit exceeded)
        JQuantsValidationError (data validation failure)
        JQuantsAuthError (authentication failure)
    AseanError (ASEAN market operations)
        AseanStorageError (DuckDB storage failure)
        AseanScreenerError (tradingview-screener failure)
        AseanLookupError (ticker lookup failure)
    EodhdError (EODHD API operations)
        EodhdAPIError (API response error - 4xx, 5xx)
        EodhdRateLimitError (rate limit exceeded)
        EodhdValidationError (data validation failure)
        EodhdAuthError (authentication failure)
"""

from enum import Enum
from typing import Any

from market.asean_common.errors import (
    AseanError,
    AseanLookupError,
    AseanScreenerError,
    AseanStorageError,
)
from market.bse.errors import (
    BseAPIError,
    BseError,
    BseParseError,
    BseRateLimitError,
    BseValidationError,
)
from market.edinet.errors import (
    EdinetAPIError,
    EdinetError,
    EdinetParseError,
    EdinetRateLimitError,
    EdinetValidationError,
)
from market.eodhd.errors import (
    EodhdAPIError,
    EodhdAuthError,
    EodhdError,
    EodhdRateLimitError,
    EodhdValidationError,
)
from market.etfcom.errors import (
    ETFComBlockedError,
    ETFComError,
    ETFComHTTPError,
    ETFComNotFoundError,
    ETFComScrapingError,
    ETFComTimeoutError,
)
from market.nasdaq.errors import (
    NasdaqAPIError,
    NasdaqError,
    NasdaqParseError,
    NasdaqRateLimitError,
)


class ErrorCode(str, Enum):
    """Error codes for categorizing exceptions.

    Unified error codes for all market data sources.

    Attributes
    ----------
    UNKNOWN : str
        Unknown or unclassified error
    NETWORK_ERROR : str
        Network connectivity issues
    API_ERROR : str
        External API errors
    RATE_LIMIT : str
        API rate limit exceeded
    INVALID_SYMBOL : str
        Invalid ticker symbol
    INVALID_DATE : str
        Invalid date format or range
    INVALID_PARAMETER : str
        Invalid function parameter
    DATA_NOT_FOUND : str
        Requested data not found
    CACHE_ERROR : str
        Cache read/write errors
    TIMEOUT : str
        Operation timeout
    EXPORT_ERROR : str
        Error during export
    CONNECTION_FAILED : str
        Failed to connect (Bloomberg)
    SESSION_ERROR : str
        Session management error (Bloomberg)
    SERVICE_ERROR : str
        Service startup error (Bloomberg)
    INVALID_SECURITY : str
        Invalid or unknown security identifier (Bloomberg)
    INVALID_FIELD : str
        Invalid Bloomberg field
    INVALID_DATE_RANGE : str
        Invalid date range specified
    SCRAPING_ERROR : str
        HTML scraping / parsing failure (ETF.com)
    PAGE_LOAD_TIMEOUT : str
        Page load or navigation timeout (ETF.com)
    NASDAQ_API_ERROR : str
        NASDAQ API response error (4xx, 5xx)
    NASDAQ_RATE_LIMIT : str
        NASDAQ API rate limit exceeded
    NASDAQ_PARSE_ERROR : str
        NASDAQ API response parse failure
    EDINET_API_ERROR : str
        EDINET DB API response error (4xx, 5xx)
    EDINET_RATE_LIMIT : str
        EDINET DB API daily call limit exceeded
    BSE_API_ERROR : str
        BSE API response error (4xx, 5xx)
    BSE_RATE_LIMIT : str
        BSE API rate limit exceeded
    BSE_PARSE_ERROR : str
        BSE API response parse failure
    BSE_VALIDATION_ERROR : str
        BSE data validation failure
    JQUANTS_API_ERROR : str
        J-Quants API response error (4xx, 5xx)
    JQUANTS_RATE_LIMIT : str
        J-Quants API rate limit exceeded
    JQUANTS_VALIDATION_ERROR : str
        J-Quants data validation failure
    JQUANTS_AUTH_ERROR : str
        J-Quants authentication failure
    ASEAN_STORAGE_ERROR : str
        ASEAN DuckDB storage operation failure
    ASEAN_SCREENER_ERROR : str
        ASEAN tradingview-screener query failure
    ASEAN_LOOKUP_ERROR : str
        ASEAN ticker lookup failure
    EODHD_API_ERROR : str
        EODHD API response error (4xx, 5xx)
    EODHD_RATE_LIMIT : str
        EODHD API rate limit exceeded
    EODHD_VALIDATION_ERROR : str
        EODHD data validation failure
    EODHD_AUTH_ERROR : str
        EODHD authentication failure
    """

    UNKNOWN = "UNKNOWN"
    NETWORK_ERROR = "NETWORK_ERROR"
    API_ERROR = "API_ERROR"
    RATE_LIMIT = "RATE_LIMIT"
    INVALID_SYMBOL = "INVALID_SYMBOL"
    INVALID_DATE = "INVALID_DATE"
    INVALID_PARAMETER = "INVALID_PARAMETER"
    DATA_NOT_FOUND = "DATA_NOT_FOUND"
    CACHE_ERROR = "CACHE_ERROR"
    TIMEOUT = "TIMEOUT"
    EXPORT_ERROR = "EXPORT_ERROR"
    CONNECTION_FAILED = "CONNECTION_FAILED"
    SESSION_ERROR = "SESSION_ERROR"
    SERVICE_ERROR = "SERVICE_ERROR"
    INVALID_SECURITY = "INVALID_SECURITY"
    INVALID_FIELD = "INVALID_FIELD"
    INVALID_DATE_RANGE = "INVALID_DATE_RANGE"
    SCRAPING_ERROR = "SCRAPING_ERROR"
    PAGE_LOAD_TIMEOUT = "PAGE_LOAD_TIMEOUT"
    NASDAQ_API_ERROR = "NASDAQ_API_ERROR"
    NASDAQ_RATE_LIMIT = "NASDAQ_RATE_LIMIT"
    NASDAQ_PARSE_ERROR = "NASDAQ_PARSE_ERROR"
    EDINET_API_ERROR = "EDINET_API_ERROR"
    EDINET_RATE_LIMIT = "EDINET_RATE_LIMIT"
    BSE_API_ERROR = "BSE_API_ERROR"
    BSE_RATE_LIMIT = "BSE_RATE_LIMIT"
    BSE_PARSE_ERROR = "BSE_PARSE_ERROR"
    BSE_VALIDATION_ERROR = "BSE_VALIDATION_ERROR"
    JQUANTS_API_ERROR = "JQUANTS_API_ERROR"
    JQUANTS_RATE_LIMIT = "JQUANTS_RATE_LIMIT"
    JQUANTS_VALIDATION_ERROR = "JQUANTS_VALIDATION_ERROR"
    JQUANTS_AUTH_ERROR = "JQUANTS_AUTH_ERROR"
    ASEAN_STORAGE_ERROR = "ASEAN_STORAGE_ERROR"
    ASEAN_SCREENER_ERROR = "ASEAN_SCREENER_ERROR"
    ASEAN_LOOKUP_ERROR = "ASEAN_LOOKUP_ERROR"
    EODHD_API_ERROR = "EODHD_API_ERROR"
    EODHD_RATE_LIMIT = "EODHD_RATE_LIMIT"
    EODHD_VALIDATION_ERROR = "EODHD_VALIDATION_ERROR"
    EODHD_AUTH_ERROR = "EODHD_AUTH_ERROR"


class MarketError(Exception):
    """Base exception for all market package errors.

    All custom exceptions in this package inherit from this class,
    providing a consistent interface for error handling.

    Parameters
    ----------
    message : str
        Human-readable error message
    code : ErrorCode
        Error code for programmatic handling
    details : dict[str, Any] | None
        Additional context about the error
    cause : Exception | None
        The underlying exception that caused this error

    Attributes
    ----------
    message : str
        The error message
    code : ErrorCode
        The error code
    details : dict[str, Any]
        Additional error details
    cause : Exception | None
        The original exception if available

    Examples
    --------
    >>> try:
    ...     raise MarketError(
    ...         "Failed to process data",
    ...         code=ErrorCode.UNKNOWN,
    ...         details={"symbol": "AAPL"},
    ...     )
    ... except MarketError as e:
    ...     print(e.code)
    UNKNOWN
    """

    def __init__(
        self,
        message: str,
        code: ErrorCode = ErrorCode.UNKNOWN,
        details: dict[str, Any] | None = None,
        cause: Exception | None = None,
    ) -> None:
        super().__init__(message)
        self.message = message
        self.code = code
        self.details = details or {}
        self.cause = cause

    def __str__(self) -> str:
        """Return a formatted error message."""
        parts = [f"[{self.code.value}] {self.message}"]

        if self.details:
            details_str = ", ".join(f"{k}={v!r}" for k, v in self.details.items())
            parts.append(f"Details: {details_str}")

        if self.cause:
            parts.append(f"Caused by: {type(self.cause).__name__}: {self.cause}")

        return " | ".join(parts)

    def __repr__(self) -> str:
        """Return a developer-friendly representation."""
        return (
            f"{self.__class__.__name__}("
            f"message={self.message!r}, "
            f"code={self.code!r}, "
            f"details={self.details!r})"
        )

    def to_dict(self) -> dict[str, Any]:
        """Convert exception to dictionary for serialization.

        Returns
        -------
        dict[str, Any]
            Dictionary representation of the error
        """
        result: dict[str, Any] = {
            "error_type": self.__class__.__name__,
            "code": self.code.value,
            "message": self.message,
            "details": self.details,
        }

        if self.cause:
            result["cause"] = {
                "type": type(self.cause).__name__,
                "message": str(self.cause),
            }

        return result


class ExportError(MarketError):
    """Exception raised when data export fails.

    This exception is raised for errors during data serialization
    or file writing operations.

    Parameters
    ----------
    message : str
        Human-readable error message
    format : str | None
        The export format that failed
    path : str | None
        The output path
    code : ErrorCode
        Error code (defaults to EXPORT_ERROR)
    details : dict[str, Any] | None
        Additional context
    cause : Exception | None
        The underlying exception

    Examples
    --------
    >>> raise ExportError(
    ...     "Failed to write CSV file",
    ...     format="csv",
    ...     path="/data/output.csv",
    ... )
    """

    def __init__(
        self,
        message: str,
        format: str | None = None,
        path: str | None = None,
        code: ErrorCode = ErrorCode.EXPORT_ERROR,
        details: dict[str, Any] | None = None,
        cause: Exception | None = None,
    ) -> None:
        details = details or {}
        if format:
            details["format"] = format
        if path:
            details["path"] = path

        super().__init__(message, code=code, details=details, cause=cause)
        self.format = format
        self.path = path


class CacheError(MarketError):
    """Exception raised when cache operations fail.

    This exception is raised for errors during cache read, write,
    or management operations.

    Parameters
    ----------
    message : str
        Human-readable error message
    operation : str | None
        The cache operation that failed (e.g., "get", "set", "delete")
    key : str | None
        The cache key involved in the operation
    code : ErrorCode
        Error code (defaults to CACHE_ERROR)
    details : dict[str, Any] | None
        Additional context
    cause : Exception | None
        The underlying exception

    Examples
    --------
    >>> raise CacheError(
    ...     "Failed to write cache entry",
    ...     operation="set",
    ...     key="AAPL_data",
    ... )
    """

    def __init__(
        self,
        message: str,
        operation: str | None = None,
        key: str | None = None,
        code: ErrorCode = ErrorCode.CACHE_ERROR,
        details: dict[str, Any] | None = None,
        cause: Exception | None = None,
    ) -> None:
        details = details or {}
        if operation:
            details["operation"] = operation
        if key:
            details["key"] = key

        super().__init__(message, code=code, details=details, cause=cause)
        self.operation = operation
        self.key = key


# =============================================================================
# YFinance Errors
# =============================================================================


class DataFetchError(MarketError):
    """Exception raised when data fetching fails (yfinance).

    This exception is raised for errors during data retrieval from
    external sources (yfinance, etc.).

    Parameters
    ----------
    message : str
        Human-readable error message
    symbol : str | None
        The symbol that failed to fetch
    source : str | None
        The data source that was used
    code : ErrorCode
        Error code (defaults to API_ERROR)
    details : dict[str, Any] | None
        Additional context
    cause : Exception | None
        The underlying exception

    Examples
    --------
    >>> raise DataFetchError(
    ...     "Failed to fetch price data for AAPL",
    ...     symbol="AAPL",
    ...     source="yfinance",
    ... )
    """

    def __init__(
        self,
        message: str,
        symbol: str | None = None,
        source: str | None = None,
        code: ErrorCode = ErrorCode.API_ERROR,
        details: dict[str, Any] | None = None,
        cause: Exception | None = None,
    ) -> None:
        details = details or {}
        if symbol:
            details["symbol"] = symbol
        if source:
            details["source"] = source

        super().__init__(message, code=code, details=details, cause=cause)
        self.symbol = symbol
        self.source = source


class ValidationError(MarketError):
    """Exception raised when input validation fails (yfinance).

    This exception is raised when function parameters or input data
    fail validation checks.

    Parameters
    ----------
    message : str
        Human-readable error message
    field : str | None
        The field that failed validation
    value : Any
        The invalid value
    code : ErrorCode
        Error code (defaults to INVALID_PARAMETER)
    details : dict[str, Any] | None
        Additional context
    cause : Exception | None
        The underlying exception

    Examples
    --------
    >>> raise ValidationError(
    ...     "Start date must be before end date",
    ...     field="start_date",
    ...     value="2024-12-31",
    ... )
    """

    def __init__(
        self,
        message: str,
        field: str | None = None,
        value: Any = None,
        code: ErrorCode = ErrorCode.INVALID_PARAMETER,
        details: dict[str, Any] | None = None,
        cause: Exception | None = None,
    ) -> None:
        details = details or {}
        if field:
            details["field"] = field
        if value is not None:
            details["value"] = repr(value)

        super().__init__(message, code=code, details=details, cause=cause)
        self.field = field
        self.value = value


# =============================================================================
# FRED Errors
# =============================================================================


class FREDError(Exception):
    """Base exception for FRED operations.

    All FRED-specific exceptions inherit from this class.

    Parameters
    ----------
    message : str
        Human-readable error message
    """


class FREDValidationError(FREDError):
    """Exception raised when FRED input validation fails.

    This exception is raised when:
    - API key is not provided or invalid
    - Series ID format is invalid
    - Required parameters are missing or malformed

    Parameters
    ----------
    message : str
        Human-readable error message describing the validation failure

    Examples
    --------
    >>> raise FREDValidationError("FRED API key not provided")
    >>> raise FREDValidationError("Invalid series ID: gdp (must be uppercase)")
    """


class FREDFetchError(FREDError):
    """Exception raised when FRED data fetching fails.

    This exception is raised when:
    - FRED API returns an error
    - Network connectivity issues occur
    - Requested data is not found
    - API rate limits are exceeded

    Parameters
    ----------
    message : str
        Human-readable error message describing the fetch failure

    Examples
    --------
    >>> raise FREDFetchError("Failed to fetch FRED series GDP: API Error")
    >>> raise FREDFetchError("No data found for FRED series: INVALID")
    """


class FREDCacheNotFoundError(FREDFetchError):
    """FRED series data not found in local cache.

    This exception is raised when requested FRED series data
    is not available in the local cache and needs to be synced.

    Parameters
    ----------
    series_ids : list[str]
        Missing series IDs that were not found in cache

    Attributes
    ----------
    series_ids : list[str]
        The series IDs that were not found

    Examples
    --------
    >>> raise FREDCacheNotFoundError(series_ids=["GDP", "CPIAUCSL"])
    >>> # To recover, sync the missing data:
    >>> # HistoricalCache().sync_series("GDP")
    """

    def __init__(self, series_ids: list[str]) -> None:
        self.series_ids = series_ids
        series_str = ", ".join(series_ids)
        first_series = series_ids[0] if series_ids else ""
        message = (
            f"FRED series not found in cache: {series_str}. "
            f'Sync data using: HistoricalCache().sync_series("{first_series}")'
        )
        super().__init__(message)


# =============================================================================
# Bloomberg Errors
# =============================================================================


class BloombergError(Exception):
    """Base exception for Bloomberg operations.

    Parameters
    ----------
    message : str
        Error message
    code : ErrorCode
        Error code (default: INVALID_PARAMETER)
    details : dict[str, Any] | None
        Additional error details
    cause : Exception | None
        Original exception that caused this error

    Attributes
    ----------
    message : str
        Error message
    code : ErrorCode
        Error code
    details : dict[str, Any]
        Additional error details
    cause : Exception | None
        Original exception

    Examples
    --------
    >>> error = BloombergError("Connection failed", code=ErrorCode.CONNECTION_FAILED)
    >>> error.code
    <ErrorCode.CONNECTION_FAILED: 'CONNECTION_FAILED'>
    """

    def __init__(
        self,
        message: str,
        code: ErrorCode = ErrorCode.INVALID_PARAMETER,
        details: dict[str, Any] | None = None,
        cause: Exception | None = None,
    ) -> None:
        super().__init__(message)
        self.message = message
        self.code = code
        self.details = details or {}
        self.cause = cause

    def to_dict(self) -> dict[str, Any]:
        """Convert error to dictionary representation.

        Returns
        -------
        dict[str, Any]
            Dictionary containing error information

        Examples
        --------
        >>> error = BloombergError("Test", code=ErrorCode.CONNECTION_FAILED)
        >>> error.to_dict()
        {'message': 'Test', 'code': 'CONNECTION_FAILED', 'details': {}}
        """
        result = {
            "message": self.message,
            "code": self.code.value,
            "details": self.details,
        }
        if self.cause is not None:
            result["cause"] = str(self.cause)
        return result


class BloombergConnectionError(BloombergError):
    """Exception for Bloomberg connection failures.

    Parameters
    ----------
    message : str
        Error message
    host : str | None
        Host that connection was attempted to
    port : int | None
        Port that connection was attempted to
    cause : Exception | None
        Original exception

    Attributes
    ----------
    host : str | None
        Host that connection was attempted to
    port : int | None
        Port that connection was attempted to

    Examples
    --------
    >>> error = BloombergConnectionError(
    ...     "Connection refused",
    ...     host="localhost",
    ...     port=8194,
    ... )
    >>> error.host
    'localhost'
    """

    def __init__(
        self,
        message: str,
        host: str | None = None,
        port: int | None = None,
        cause: Exception | None = None,
    ) -> None:
        details: dict[str, Any] = {}
        if host is not None:
            details["host"] = host
        if port is not None:
            details["port"] = port

        super().__init__(
            message,
            code=ErrorCode.CONNECTION_FAILED,
            details=details,
            cause=cause,
        )
        self.host = host
        self.port = port


class BloombergSessionError(BloombergError):
    """Exception for Bloomberg session management failures.

    Parameters
    ----------
    message : str
        Error message
    service : str | None
        Bloomberg service that failed
    cause : Exception | None
        Original exception

    Attributes
    ----------
    service : str | None
        Bloomberg service that failed

    Examples
    --------
    >>> error = BloombergSessionError(
    ...     "Service not available",
    ...     service="//blp/refdata",
    ... )
    >>> error.service
    '//blp/refdata'
    """

    def __init__(
        self,
        message: str,
        service: str | None = None,
        cause: Exception | None = None,
    ) -> None:
        details: dict[str, Any] = {}
        if service is not None:
            details["service"] = service

        super().__init__(
            message,
            code=ErrorCode.SESSION_ERROR,
            details=details,
            cause=cause,
        )
        self.service = service


class BloombergDataError(BloombergError):
    """Exception for Bloomberg data fetching failures.

    Parameters
    ----------
    message : str
        Error message
    security : str | None
        Security that caused the error
    fields : list[str] | None
        Fields that caused the error
    code : ErrorCode
        Error code (default: INVALID_SECURITY)
    cause : Exception | None
        Original exception

    Attributes
    ----------
    security : str | None
        Security that caused the error
    fields : list[str] | None
        Fields that caused the error

    Examples
    --------
    >>> error = BloombergDataError(
    ...     "Invalid security",
    ...     security="INVALID US Equity",
    ... )
    >>> error.security
    'INVALID US Equity'
    """

    def __init__(
        self,
        message: str,
        security: str | None = None,
        fields: list[str] | None = None,
        code: ErrorCode = ErrorCode.INVALID_SECURITY,
        cause: Exception | None = None,
    ) -> None:
        details: dict[str, Any] = {}
        if security is not None:
            details["security"] = security
        if fields is not None:
            details["fields"] = fields

        super().__init__(
            message,
            code=code,
            details=details,
            cause=cause,
        )
        self.security = security
        self.fields = fields


class BloombergValidationError(BloombergError):
    """Exception for Bloomberg input validation failures.

    Parameters
    ----------
    message : str
        Error message
    field : str | None
        Field that failed validation
    value : Any
        Invalid value
    code : ErrorCode
        Error code (default: INVALID_PARAMETER)
    cause : Exception | None
        Original exception

    Attributes
    ----------
    field : str | None
        Field that failed validation
    value : Any
        Invalid value

    Examples
    --------
    >>> error = BloombergValidationError(
    ...     "Invalid date format",
    ...     field="start_date",
    ...     value="not-a-date",
    ... )
    >>> error.field
    'start_date'
    """

    def __init__(
        self,
        message: str,
        field: str | None = None,
        value: Any = None,
        code: ErrorCode = ErrorCode.INVALID_PARAMETER,
        cause: Exception | None = None,
    ) -> None:
        details: dict[str, Any] = {}
        if field is not None:
            details["field"] = field
        if value is not None:
            details["value"] = value

        super().__init__(
            message,
            code=code,
            details=details,
            cause=cause,
        )
        self.field = field
        self.value = value


# =============================================================================
# ETFCom Errors (re-exported from market.etfcom.errors)
# =============================================================================
# ETFComBlockedError, ETFComError, ETFComHTTPError, ETFComNotFoundError,
# ETFComScrapingError, ETFComTimeoutError
# are imported at the top of this file and included in __all__.

__all__ = [
    # ASEAN errors
    "AseanError",
    "AseanLookupError",
    "AseanScreenerError",
    "AseanStorageError",
    # Bloomberg errors
    "BloombergConnectionError",
    "BloombergDataError",
    "BloombergError",
    "BloombergSessionError",
    "BloombergValidationError",
    # BSE errors
    "BseAPIError",
    "BseError",
    "BseParseError",
    "BseRateLimitError",
    "BseValidationError",
    "CacheError",
    "DataFetchError",
    # ETF.com errors
    "ETFComBlockedError",
    "ETFComError",
    "ETFComHTTPError",
    "ETFComNotFoundError",
    "ETFComScrapingError",
    "ETFComTimeoutError",
    # EDINET errors
    "EdinetAPIError",
    "EdinetError",
    "EdinetParseError",
    "EdinetRateLimitError",
    "EdinetValidationError",
    # EODHD errors
    "EodhdAPIError",
    "EodhdAuthError",
    "EodhdError",
    "EodhdRateLimitError",
    "EodhdValidationError",
    "ErrorCode",
    "ExportError",
    "FREDCacheNotFoundError",
    "FREDError",
    "FREDFetchError",
    "FREDValidationError",
    "MarketError",
    "NasdaqAPIError",
    "NasdaqError",
    "NasdaqParseError",
    "NasdaqRateLimitError",
    "ValidationError",
]
