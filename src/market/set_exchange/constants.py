"""Constants for SET (Stock Exchange of Thailand) data retrieval module.

This module defines all constants used by the SET data retrieval module,
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

The package name is ``set_exchange`` instead of ``set`` to avoid
collision with the Python built-in ``set`` type.

See Also
--------
market.bse.constants : Similar constant pattern used by the BSE module.
market.asean_common.constants : Shared ASEAN constants (AseanMarket enum).
"""

from typing import Final

# ---------------------------------------------------------------------------
# 1. Exchange identification
# ---------------------------------------------------------------------------

EXCHANGE_CODE: Final[str] = "SET"
"""Exchange code identifier.

Used as a standard reference for the Stock Exchange of Thailand
across the codebase.
"""

EXCHANGE_NAME: Final[str] = "Stock Exchange of Thailand"
"""Full name of the exchange."""

SUFFIX: Final[str] = ".BK"
"""yfinance ticker suffix for SET-listed securities.

Examples
--------
>>> f"PTT{SUFFIX}"
'PTT.BK'
"""

CURRENCY: Final[str] = "THB"
"""Primary trading currency (Thai Baht)."""

# ---------------------------------------------------------------------------
# 2. yfinance configuration
# ---------------------------------------------------------------------------

YFINANCE_SUPPORTED: Final[bool] = True
"""Whether yfinance supports this exchange for data retrieval."""

# ---------------------------------------------------------------------------
# 3. Output settings
# ---------------------------------------------------------------------------

DEFAULT_OUTPUT_SUBDIR: Final[str] = "raw/set_exchange"
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
