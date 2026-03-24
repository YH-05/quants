"""Cache helpers for the NasdaqClient module.

This module provides TTL constants for each NASDAQ API endpoint category
and a convenience function for obtaining a SQLiteCache instance configured
for NASDAQ API data.

The implementation mirrors ``market.alphavantage.cache`` and delegates to the
shared ``market.cache`` infrastructure (``SQLiteCache``,
``create_persistent_cache``).

See Also
--------
market.cache.cache : Core SQLiteCache implementation.
market.alphavantage.cache : Reference implementation with identical pattern.
market.nasdaq.client : NasdaqClient that consumes this cache.
"""

from typing import Final

from market.cache.cache import SQLiteCache, create_persistent_cache
from utils_core.logging import get_logger

logger = get_logger(__name__)

# ---------------------------------------------------------------------------
# TTL constants (seconds)
# ---------------------------------------------------------------------------

EARNINGS_CALENDAR_TTL: Final[int] = 86400
"""TTL for earnings calendar data (24 hours).

Earnings calendar data is updated daily.
"""

DIVIDENDS_CALENDAR_TTL: Final[int] = 86400
"""TTL for dividends calendar data (24 hours).

Dividends calendar data is updated daily.
"""

SPLITS_CALENDAR_TTL: Final[int] = 86400
"""TTL for stock splits calendar data (24 hours).

Splits calendar data is updated daily.
"""

IPO_CALENDAR_TTL: Final[int] = 86400
"""TTL for IPO calendar data (24 hours).

IPO calendar data is updated daily.
"""

INSTITUTIONAL_HOLDINGS_TTL: Final[int] = 604800
"""TTL for institutional holdings data (7 days).

Institutional holdings data is reported quarterly and changes rarely.
"""

INSIDER_TRADES_TTL: Final[int] = 86400
"""TTL for insider trading data (24 hours).

Insider trades are disclosed with a delay; daily refresh is sufficient.
"""

FINANCIALS_TTL: Final[int] = 86400
"""TTL for financial statements data (24 hours).

Financial statements data is reported quarterly and changes rarely.
"""

ANALYST_FORECAST_TTL: Final[int] = 86400
"""TTL for analyst forecast / recommendations data (24 hours).

Analyst forecasts are updated infrequently; daily refresh is appropriate.
"""

ANALYST_RATINGS_TTL: Final[int] = 86400
"""TTL for analyst ratings data (24 hours).

Analyst buy/sell/hold ratings are updated infrequently; daily refresh
is appropriate.
"""

ANALYST_TARGET_PRICE_TTL: Final[int] = 86400
"""TTL for analyst target price data (24 hours).

Target price data is updated infrequently; daily refresh is appropriate.
"""

ANALYST_EARNINGS_DATE_TTL: Final[int] = 43200
"""TTL for earnings date data (12 hours).

Earnings date data may change more frequently closer to the announcement
date; semi-daily refresh is appropriate.
"""

SHORT_INTEREST_TTL: Final[int] = 86400
"""TTL for short interest data (24 hours).

Short interest data is reported bi-monthly; daily refresh is sufficient.
"""

DIVIDEND_HISTORY_TTL: Final[int] = 86400
"""TTL for dividend history data (24 hours).

Dividend history data changes infrequently; daily refresh is sufficient.
"""

MARKET_MOVERS_TTL: Final[int] = 300
"""TTL for market movers data (5 minutes).

Market movers data changes frequently during market hours; frequent
refresh is needed for timely gainers/losers/most active information.
"""

ETF_SCREENER_TTL: Final[int] = 3600
"""TTL for ETF screener data (1 hour).

ETF screener results change less frequently than real-time quotes.
"""


def get_nasdaq_cache() -> SQLiteCache:
    """Get a SQLiteCache instance configured for NASDAQ API data.

    Creates a persistent cache with a default TTL of 24 hours
    and a capacity of 10 000 entries.

    Returns
    -------
    SQLiteCache
        A configured cache instance for NASDAQ API data.

    Examples
    --------
    >>> cache = get_nasdaq_cache()
    >>> cache.set("nasdaq:quote:AAPL", data, ttl=EARNINGS_CALENDAR_TTL)
    """
    # max_entries=10000 は全エンドポイント x ユニークキー数の上限。
    # 1エントリは平均 1-50KB（ETF screener が最大、全ETF一括で ~50KB）。
    # 読み書きのみ（行検索不要）のためSQLiteで十分な規模。
    cache = create_persistent_cache(
        ttl_seconds=EARNINGS_CALENDAR_TTL,
        max_entries=10000,
    )
    logger.debug("NASDAQ client cache instance created")
    return cache


__all__ = [
    "ANALYST_EARNINGS_DATE_TTL",
    "ANALYST_FORECAST_TTL",
    "ANALYST_RATINGS_TTL",
    "ANALYST_TARGET_PRICE_TTL",
    "DIVIDENDS_CALENDAR_TTL",
    "DIVIDEND_HISTORY_TTL",
    "EARNINGS_CALENDAR_TTL",
    "ETF_SCREENER_TTL",
    "FINANCIALS_TTL",
    "INSIDER_TRADES_TTL",
    "INSTITUTIONAL_HOLDINGS_TTL",
    "IPO_CALENDAR_TTL",
    "MARKET_MOVERS_TTL",
    "SHORT_INTEREST_TTL",
    "SPLITS_CALENDAR_TTL",
    "get_nasdaq_cache",
]
