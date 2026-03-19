"""Constants for IDX (Indonesia Stock Exchange) data retrieval module.

This module defines all constants used by the IDX data retrieval module,
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

EXCHANGE_CODE: Final[str] = "IDX"
"""Exchange code identifier.

Used as a standard reference for the Indonesia Stock Exchange
across the codebase.
"""

EXCHANGE_NAME: Final[str] = "Indonesia Stock Exchange"
"""Full name of the exchange."""

SUFFIX: Final[str] = ".JK"
"""yfinance ticker suffix for IDX-listed securities.

Examples
--------
>>> f"BBCA{SUFFIX}"
'BBCA.JK'
"""

CURRENCY: Final[str] = "IDR"
"""Primary trading currency (Indonesian Rupiah)."""

# ---------------------------------------------------------------------------
# 2. yfinance configuration
# ---------------------------------------------------------------------------

YFINANCE_SUPPORTED: Final[bool] = True
"""Whether yfinance supports this exchange for data retrieval."""

# ---------------------------------------------------------------------------
# 3. Output settings
# ---------------------------------------------------------------------------

DEFAULT_OUTPUT_DIR: Final[str] = "data/raw/idx/"
"""Default directory for output files.

Follows the project convention of ``data/raw/<source>/``.
"""

# ---------------------------------------------------------------------------
# Module exports
# ---------------------------------------------------------------------------

__all__ = [
    "CURRENCY",
    "DEFAULT_OUTPUT_DIR",
    "EXCHANGE_CODE",
    "EXCHANGE_NAME",
    "SUFFIX",
    "YFINANCE_SUPPORTED",
]
