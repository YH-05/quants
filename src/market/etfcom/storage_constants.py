"""Storage constants for the ETF.com persistence layer.

This module defines SQLite table name constants and database path
settings for the ETF.com long-term storage layer. All table names
use the ``etfcom_`` prefix to avoid collisions with other market modules.

Tables managed
--------------
- ``etfcom_tickers`` -- ETF ticker master list from the screener
  (PK: ``ticker``)
- ``etfcom_fund_flows`` -- Daily fund flow data
  (PK: ``ticker``, ``date``)
- ``etfcom_holdings`` -- Top holdings data
  (PK: ``ticker``, ``holding_ticker``, ``fetched_at``)
- ``etfcom_portfolio`` -- Portfolio characteristics
  (PK: ``ticker``, ``fetched_at``)
- ``etfcom_allocations`` -- Sector/region/asset allocation breakdowns
  (PK: ``ticker``, ``allocation_type``, ``category``, ``fetched_at``)
- ``etfcom_tradability`` -- Tradability metrics (spread, volume, etc.)
  (PK: ``ticker``, ``fetched_at``)
- ``etfcom_structure`` -- Fund structure metadata
  (PK: ``ticker``, ``fetched_at``)
- ``etfcom_performance`` -- Historical return performance data
  (PK: ``ticker``, ``period``, ``fetched_at``)
- ``etfcom_quotes`` -- Intraday/daily quote snapshots
  (PK: ``ticker``, ``fetched_at``)

See Also
--------
market.etfcom.constants : API-level constants (base URLs, selectors).
market.alphavantage.storage_constants : Similar constant pattern used by Alpha Vantage.
market.polymarket.storage_constants : Similar constant pattern used by Polymarket.
"""

from typing import Final

# ---------------------------------------------------------------------------
# 1. Database path settings
# ---------------------------------------------------------------------------

ETFCOM_DB_PATH_ENV: Final[str] = "ETFCOM_DB_PATH"
"""Environment variable name for overriding the default SQLite file path.

When set, this takes precedence over the default path resolved by
``get_db_path("sqlite", "etfcom")``.
"""

DEFAULT_DB_NAME: Final[str] = "etfcom"
"""Default database name (without extension) for the ETF.com SQLite file.

Used as the second argument to ``get_db_path()`` when resolving the
default database path. The resulting file is ``etfcom.db``.
"""

# ---------------------------------------------------------------------------
# 2. SQLite table names (etfcom_ prefix)
# ---------------------------------------------------------------------------

TABLE_TICKERS: Final[str] = "etfcom_tickers"
"""SQLite table name for ETF ticker master list.

Primary key: ``ticker``. Contains ticker symbol, fund name,
asset class, and other screener metadata.
"""

TABLE_FUND_FLOWS: Final[str] = "etfcom_fund_flows"
"""SQLite table name for daily fund flow data.

Primary key: ``(ticker, date)``. Contains daily net fund flow
amounts for each ETF.
"""

TABLE_HOLDINGS: Final[str] = "etfcom_holdings"
"""SQLite table name for top holdings data.

Primary key: ``(ticker, holding_ticker, fetched_at)``. Contains
holding name, ticker, weight percentage, and shares.
"""

TABLE_PORTFOLIO: Final[str] = "etfcom_portfolio"
"""SQLite table name for portfolio characteristics.

Primary key: ``(ticker, fetched_at)``. Contains P/E ratio, P/B ratio,
dividend yield, and other portfolio-level metrics.
"""

TABLE_ALLOCATIONS: Final[str] = "etfcom_allocations"
"""SQLite table name for sector/region/asset allocation breakdowns.

Primary key: ``(ticker, allocation_type, category, fetched_at)``.
Contains allocation type (sector, region, asset class), category name,
and weight percentage.
"""

TABLE_TRADABILITY: Final[str] = "etfcom_tradability"
"""SQLite table name for tradability metrics.

Primary key: ``(ticker, fetched_at)``. Contains bid-ask spread,
average daily volume, and other liquidity/tradability indicators.
"""

TABLE_STRUCTURE: Final[str] = "etfcom_structure"
"""SQLite table name for fund structure metadata.

Primary key: ``(ticker, fetched_at)``. Contains legal structure,
expense ratio, inception date, issuer, and other structural attributes.
"""

TABLE_PERFORMANCE: Final[str] = "etfcom_performance"
"""SQLite table name for historical return performance data.

Primary key: ``(ticker, period, fetched_at)``. Contains total return
percentages for various time periods (1M, 3M, YTD, 1Y, 3Y, 5Y, 10Y).
"""

TABLE_QUOTES: Final[str] = "etfcom_quotes"
"""SQLite table name for intraday/daily quote snapshots.

Primary key: ``(ticker, fetched_at)``. Contains last price, change,
change percentage, volume, and other quote data.
"""

# ---------------------------------------------------------------------------
# Module exports
# ---------------------------------------------------------------------------

__all__ = [
    "DEFAULT_DB_NAME",
    "ETFCOM_DB_PATH_ENV",
    "TABLE_ALLOCATIONS",
    "TABLE_FUND_FLOWS",
    "TABLE_HOLDINGS",
    "TABLE_PERFORMANCE",
    "TABLE_PORTFOLIO",
    "TABLE_QUOTES",
    "TABLE_STRUCTURE",
    "TABLE_TICKERS",
    "TABLE_TRADABILITY",
]
