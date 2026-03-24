"""Storage constants for the Alpha Vantage persistence layer.

This module defines SQLite table name constants and database path
settings for the Alpha Vantage long-term storage layer. All table names
use the ``av_`` prefix to avoid collisions with other market modules.

Tables managed
--------------
- ``av_daily_prices`` -- Daily OHLCV price data (PK: ``symbol``, ``date``)
- ``av_company_overview`` -- Company profile and fundamentals
  (PK: ``symbol``)
- ``av_income_statements`` -- Income statement data
  (PK: ``symbol``, ``fiscal_date_ending``, ``reported_currency``)
- ``av_balance_sheets`` -- Balance sheet data
  (PK: ``symbol``, ``fiscal_date_ending``, ``reported_currency``)
- ``av_cash_flows`` -- Cash flow statement data
  (PK: ``symbol``, ``fiscal_date_ending``, ``reported_currency``)
- ``av_earnings`` -- Earnings data
  (PK: ``symbol``, ``fiscal_date_ending``)
- ``av_economic_indicators`` -- Macroeconomic indicator time-series
  (PK: ``indicator``, ``date``)
- ``av_forex_daily`` -- Daily forex exchange rate data
  (PK: ``from_currency``, ``to_currency``, ``date``)

See Also
--------
market.alphavantage.constants : API-level constants (base URL, rate limits).
market.polymarket.storage_constants : Similar constant pattern used by Polymarket.
"""

from typing import Final

# ---------------------------------------------------------------------------
# 1. Database path settings
# ---------------------------------------------------------------------------

AV_DB_PATH_ENV: Final[str] = "ALPHA_VANTAGE_DB_PATH"
"""Environment variable name for overriding the default SQLite file path.

When set, this takes precedence over the default path resolved by
``get_db_path("sqlite", "alphavantage")``.
"""

DEFAULT_DB_NAME: Final[str] = "alphavantage"
"""Default database name (without extension) for the Alpha Vantage SQLite file.

Used as the second argument to ``get_db_path()`` when resolving the
default database path. The resulting file is ``alphavantage.db``.
"""

# ---------------------------------------------------------------------------
# 2. SQLite table names (av_ prefix)
# ---------------------------------------------------------------------------

TABLE_DAILY_PRICES: Final[str] = "av_daily_prices"
"""SQLite table name for daily OHLCV price data.

Primary key: ``(symbol, date)``. Contains open, high, low, close,
adjusted_close, and volume for each trading day.
"""

TABLE_COMPANY_OVERVIEW: Final[str] = "av_company_overview"
"""SQLite table name for company profile and fundamentals.

Primary key: ``symbol``. Contains company metadata such as name,
description, sector, industry, and key financial metrics.
"""

TABLE_INCOME_STATEMENTS: Final[str] = "av_income_statements"
"""SQLite table name for income statement data.

Primary key: ``(symbol, fiscal_date_ending, reported_currency)``.
Contains revenue, gross profit, operating income, net income, and
other income statement line items.
"""

TABLE_BALANCE_SHEETS: Final[str] = "av_balance_sheets"
"""SQLite table name for balance sheet data.

Primary key: ``(symbol, fiscal_date_ending, reported_currency)``.
Contains total assets, total liabilities, shareholder equity, and
other balance sheet line items.
"""

TABLE_CASH_FLOWS: Final[str] = "av_cash_flows"
"""SQLite table name for cash flow statement data.

Primary key: ``(symbol, fiscal_date_ending, reported_currency)``.
Contains operating, investing, and financing cash flow data.
"""

TABLE_EARNINGS: Final[str] = "av_earnings"
"""SQLite table name for earnings data.

Primary key: ``(symbol, fiscal_date_ending)``. Contains reported EPS,
estimated EPS, surprise, and surprise percentage.
"""

TABLE_ECONOMIC_INDICATORS: Final[str] = "av_economic_indicators"
"""SQLite table name for macroeconomic indicator time-series.

Primary key: ``(indicator, date)``. Stores values for indicators
such as GDP, CPI, inflation rate, federal funds rate, etc.
"""

TABLE_FOREX_DAILY: Final[str] = "av_forex_daily"
"""SQLite table name for daily forex exchange rate data.

Primary key: ``(from_currency, to_currency, date)``. Contains
open, high, low, close prices for currency pairs.
"""

# ---------------------------------------------------------------------------
# Module exports
# ---------------------------------------------------------------------------

__all__ = [
    "AV_DB_PATH_ENV",
    "DEFAULT_DB_NAME",
    "TABLE_BALANCE_SHEETS",
    "TABLE_CASH_FLOWS",
    "TABLE_COMPANY_OVERVIEW",
    "TABLE_DAILY_PRICES",
    "TABLE_EARNINGS",
    "TABLE_ECONOMIC_INDICATORS",
    "TABLE_FOREX_DAILY",
    "TABLE_INCOME_STATEMENTS",
]
