"""Constants for Bursa (Bursa Malaysia) data retrieval module.

This module defines all constants used by the Bursa data retrieval module,
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

Bursa Malaysia uses numeric ticker codes (e.g. ``1155`` for Maybank).
The ``market.asean_common`` module provides ``lookup_ticker()`` for
name-based lookups of these numeric codes.

See Also
--------
market.bse.constants : Similar constant pattern used by the BSE module.
market.asean_common.constants : Shared ASEAN constants (AseanMarket enum).
"""

from typing import Final

# ---------------------------------------------------------------------------
# 1. Exchange identification
# ---------------------------------------------------------------------------

EXCHANGE_CODE: Final[str] = "BURSA"
"""Exchange code identifier.

Used as a standard reference for Bursa Malaysia
across the codebase.
"""

EXCHANGE_NAME: Final[str] = "Bursa Malaysia"
"""Full name of the exchange."""

SUFFIX: Final[str] = ".KL"
"""yfinance ticker suffix for Bursa-listed securities.

Bursa Malaysia uses numeric ticker codes. For example,
Maybank is ``1155.KL``.

Examples
--------
>>> f"1155{SUFFIX}"
'1155.KL'
"""

CURRENCY: Final[str] = "MYR"
"""Primary trading currency (Malaysian Ringgit)."""

# ---------------------------------------------------------------------------
# 2. yfinance configuration
# ---------------------------------------------------------------------------

YFINANCE_SUPPORTED: Final[bool] = True
"""Whether yfinance supports this exchange for data retrieval."""

# ---------------------------------------------------------------------------
# 3. Output settings
# ---------------------------------------------------------------------------

DEFAULT_OUTPUT_DIR: Final[str] = "data/raw/bursa/"
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
