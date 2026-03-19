"""Constants for ASEAN common foundation module.

This module defines all shared constants used across ASEAN market
sub-packages (SGX, Bursa, SET, IDX, HOSE, PSE), including:

1. AseanMarket Enum (6 ASEAN exchanges)
2. YFINANCE_SUFFIX_MAP (yfinance ticker suffixes per market)
3. SCREENER_EXCHANGE_MAP (tradingview-screener exchange names)
4. SCREENER_MARKET_MAP (tradingview-screener market/country names)
5. TABLE_TICKERS (DuckDB table name for ticker master)
6. DB_PATH (DuckDB database file path)

Notes
-----
All non-enum constants use ``typing.Final`` type annotations to prevent
reassignment. The ``__all__`` list exports all public constants.

See Also
--------
market.bse.constants : Similar constant pattern used by the BSE module.
"""

from enum import Enum
from typing import Final

# ---------------------------------------------------------------------------
# 1. AseanMarket Enum
# ---------------------------------------------------------------------------


class AseanMarket(str, Enum):
    """ASEAN stock exchange identifiers.

    Represents the 6 major ASEAN stock exchanges covered by
    this package. Inherits from ``str`` so members can be used
    directly as string values.

    Parameters
    ----------
    value : str
        The exchange identifier string.

    Examples
    --------
    >>> AseanMarket.SGX
    <AseanMarket.SGX: 'SGX'>
    >>> str(AseanMarket.SGX)
    'SGX'
    """

    SGX = "SGX"
    """Singapore Exchange."""

    BURSA = "BURSA"
    """Bursa Malaysia."""

    SET = "SET"
    """Stock Exchange of Thailand."""

    IDX = "IDX"
    """Indonesia Stock Exchange."""

    HOSE = "HOSE"
    """Ho Chi Minh Stock Exchange (Vietnam)."""

    PSE = "PSE"
    """Philippine Stock Exchange."""


# ---------------------------------------------------------------------------
# 2. yfinance suffix mapping
# ---------------------------------------------------------------------------

YFINANCE_SUFFIX_MAP: Final[dict[AseanMarket, str]] = {
    AseanMarket.SGX: ".SI",
    AseanMarket.BURSA: ".KL",
    AseanMarket.SET: ".BK",
    AseanMarket.IDX: ".JK",
    AseanMarket.HOSE: ".VN",
    AseanMarket.PSE: ".PS",
}
"""Mapping from AseanMarket to yfinance ticker suffix.

Each ASEAN exchange has a specific suffix used by yfinance
to identify the exchange. For example, DBS Group (SGX) is
``D05.SI`` and Maybank (Bursa) is ``1155.KL``.

Examples
--------
>>> YFINANCE_SUFFIX_MAP[AseanMarket.SGX]
'.SI'
>>> YFINANCE_SUFFIX_MAP[AseanMarket.BURSA]
'.KL'
"""

# ---------------------------------------------------------------------------
# 3. tradingview-screener exchange mapping
# ---------------------------------------------------------------------------

SCREENER_EXCHANGE_MAP: Final[dict[AseanMarket, str]] = {
    AseanMarket.SGX: "SGX",
    AseanMarket.BURSA: "MYX",
    AseanMarket.SET: "SET",
    AseanMarket.IDX: "IDX",
    AseanMarket.HOSE: "HOSE",
    AseanMarket.PSE: "PSE",
}
"""Mapping from AseanMarket to tradingview-screener exchange name.

The tradingview-screener library uses exchange names that may
differ from the standard AseanMarket identifiers. For example,
Bursa Malaysia is ``MYX`` in tradingview-screener.

Examples
--------
>>> SCREENER_EXCHANGE_MAP[AseanMarket.BURSA]
'MYX'
"""

# ---------------------------------------------------------------------------
# 4. tradingview-screener market (country) mapping
# ---------------------------------------------------------------------------

SCREENER_MARKET_MAP: Final[dict[AseanMarket, str]] = {
    AseanMarket.SGX: "singapore",
    AseanMarket.BURSA: "malaysia",
    AseanMarket.SET: "thailand",
    AseanMarket.IDX: "indonesia",
    AseanMarket.HOSE: "vietnam",
    AseanMarket.PSE: "philippines",
}
"""Mapping from AseanMarket to tradingview-screener market/country name.

The tradingview-screener ``Query.set_markets()`` method accepts
country/market names (lowercase) rather than exchange codes.
For example, Bursa Malaysia uses ``"malaysia"`` as the market name.

Examples
--------
>>> SCREENER_MARKET_MAP[AseanMarket.BURSA]
'malaysia'
>>> SCREENER_MARKET_MAP[AseanMarket.SGX]
'singapore'
"""

# ---------------------------------------------------------------------------
# 5. DuckDB table name
# ---------------------------------------------------------------------------

TABLE_TICKERS: Final[str] = "asean_tickers"
"""DuckDB table name for the ASEAN ticker master.

Stores all ASEAN exchange-listed tickers with metadata
(name, sector, industry, market cap, currency, active status).
"""

# ---------------------------------------------------------------------------
# 6. DuckDB database path
# ---------------------------------------------------------------------------

DB_PATH: Final[str] = "data/processed/asean.duckdb"
"""Path to the ASEAN DuckDB database file.

Follows the project convention of ``data/processed/<domain>.duckdb``.
"""

# ---------------------------------------------------------------------------
# Module exports
# ---------------------------------------------------------------------------

__all__ = [
    "DB_PATH",
    "SCREENER_EXCHANGE_MAP",
    "SCREENER_MARKET_MAP",
    "TABLE_TICKERS",
    "YFINANCE_SUFFIX_MAP",
    "AseanMarket",
]
