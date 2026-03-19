"""Constants for SGX (Singapore Exchange) data retrieval module.

This module defines all constants used by the SGX data retrieval module,
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

EXCHANGE_CODE: Final[str] = "SGX"
"""Exchange code identifier.

Used as a standard reference for the Singapore Exchange
across the codebase.
"""

EXCHANGE_NAME: Final[str] = "Singapore Exchange"
"""Full name of the exchange."""

SUFFIX: Final[str] = ".SI"
"""yfinance ticker suffix for SGX-listed securities.

Examples
--------
>>> f"D05{SUFFIX}"
'D05.SI'
"""

CURRENCY: Final[str] = "SGD"
"""Primary trading currency (Singapore Dollar)."""

# ---------------------------------------------------------------------------
# 2. yfinance configuration
# ---------------------------------------------------------------------------

YFINANCE_SUPPORTED: Final[bool] = True
"""Whether yfinance supports this exchange for data retrieval."""

# ---------------------------------------------------------------------------
# 3. Output settings
# ---------------------------------------------------------------------------

DEFAULT_OUTPUT_DIR: Final[str] = "data/raw/sgx/"
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
