"""Constants for PSE (Philippine Stock Exchange) data retrieval module.

This module defines all constants used by the PSE data retrieval module,
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

PSE is **not** supported by yfinance (``YFINANCE_SUPPORTED = False``).
Philippine equities can only be accessed via ADR tickers
(e.g. PHI, BDOUY, BPHLF) or alternative data providers such as EODHD.

See Also
--------
market.bse.constants : Similar constant pattern used by the BSE module.
market.asean_common.constants : Shared ASEAN constants (AseanMarket enum).
"""

from typing import Final

# ---------------------------------------------------------------------------
# 1. Exchange identification
# ---------------------------------------------------------------------------

EXCHANGE_CODE: Final[str] = "PSE"
"""Exchange code identifier.

Used as a standard reference for the Philippine Stock Exchange
across the codebase.
"""

EXCHANGE_NAME: Final[str] = "Philippine Stock Exchange"
"""Full name of the exchange."""

SUFFIX: Final[str] = ".PS"
"""yfinance ticker suffix for PSE-listed securities.

Note: yfinance does not reliably support PSE tickers.
This suffix is defined for consistency but may not return data.

Examples
--------
>>> f"SM{SUFFIX}"
'SM.PS'
"""

CURRENCY: Final[str] = "PHP"
"""Primary trading currency (Philippine Peso)."""

# ---------------------------------------------------------------------------
# 2. yfinance configuration
# ---------------------------------------------------------------------------

YFINANCE_SUPPORTED: Final[bool] = False
"""Whether yfinance supports this exchange for data retrieval.

PSE is **not** supported by yfinance. Philippine equities should
be accessed via ADR tickers or alternative data providers.
"""

# ---------------------------------------------------------------------------
# 3. Output settings
# ---------------------------------------------------------------------------

DEFAULT_OUTPUT_SUBDIR: Final[str] = "raw/pse"
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
