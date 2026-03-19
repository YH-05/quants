"""Custom exception classes for the ASEAN common module.

This module provides a hierarchy of exception classes for handling
various error conditions across ASEAN market sub-packages.

Exception Hierarchy
-------------------
AseanError (base, inherits Exception)
    AseanStorageError (DuckDB storage operation failure)
    AseanScreenerError (tradingview-screener query failure)
    AseanLookupError (ticker lookup failure)

Notes
-----
This follows the same ``Exception``-direct-inheritance pattern used by
``market.bse.errors.BseError``.

See Also
--------
market.bse.errors : BSE error hierarchy (reference implementation).
"""


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
]
