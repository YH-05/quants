"""Constants for HOSE (Ho Chi Minh Stock Exchange) data retrieval module.

This module defines all constants used by the HOSE data retrieval module,
including exchange identification, yfinance configuration, and output
directory path.

Constants are organized into the following categories:

1. Exchange identification (code, name, suffix, currency)
2. yfinance configuration (supported flag)
3. Output settings (data directory)

Notes
-----
All constants use ``typing.Final`` type annotations to prevent reassignment.
The ``__all__`` list exports all public constants for use by other modules.

See Also
--------
market.bse.constants : Similar constant pattern used by the BSE module.
market.asean_common.constants : Shared ASEAN constants (AseanMarket enum).
"""

from typing import Final

# ---------------------------------------------------------------------------
# 1. Exchange identification
# ---------------------------------------------------------------------------

EXCHANGE_CODE: Final[str] = "HOSE"
"""Exchange code identifier.

Used as a standard reference for the Ho Chi Minh Stock Exchange
across the codebase.
"""

EXCHANGE_NAME: Final[str] = "Ho Chi Minh Stock Exchange"
"""Full name of the exchange."""

SUFFIX: Final[str] = ".VN"
"""yfinance ticker suffix for HOSE-listed securities.

Examples
--------
>>> f"VNM{SUFFIX}"
'VNM.VN'
"""

CURRENCY: Final[str] = "VND"
"""Primary trading currency (Vietnamese Dong)."""

# ---------------------------------------------------------------------------
# 2. yfinance configuration
# ---------------------------------------------------------------------------

YFINANCE_SUPPORTED: Final[bool] = True
"""Whether yfinance supports this exchange for data retrieval."""

# ---------------------------------------------------------------------------
# 3. Output settings
# ---------------------------------------------------------------------------

DEFAULT_OUTPUT_SUBDIR: Final[str] = "raw/hose"
"""Default subdirectory (relative to DATA_DIR) for output files.

Appended to the base data directory resolved by
``database.db.connection.get_data_dir()`` at runtime.

See Also
--------
database.db.connection.get_data_dir : Resolves the base data directory
    from the ``DATA_DIR`` environment variable.
"""

# ---------------------------------------------------------------------------
# Module exports
# ---------------------------------------------------------------------------

__all__ = [
    "CURRENCY",
    "DEFAULT_OUTPUT_SUBDIR",
    "EXCHANGE_CODE",
    "EXCHANGE_NAME",
    "SUFFIX",
    "YFINANCE_SUPPORTED",
]
