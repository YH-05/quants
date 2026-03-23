"""Cache helpers for the Alpha Vantage API module.

This module provides TTL constants for each Alpha Vantage endpoint category
and a convenience function for obtaining a SQLiteCache instance configured
for Alpha Vantage data.

The implementation mirrors ``market.jquants.cache`` and delegates to the
shared ``market.cache`` infrastructure (``SQLiteCache``,
``create_persistent_cache``).

See Also
--------
market.cache.cache : Core SQLiteCache implementation.
market.jquants.cache : Reference implementation with identical pattern.
"""

from typing import Final

from market.cache.cache import SQLiteCache, create_persistent_cache
from utils_core.logging import get_logger

logger = get_logger(__name__)

# ---------------------------------------------------------------------------
# TTL constants (seconds)
# ---------------------------------------------------------------------------

TIME_SERIES_DAILY_TTL: Final[int] = 86400
"""TTL for daily time series data (24 hours).

Daily OHLCV data does not change once the trading day is complete.
"""

TIME_SERIES_INTRADAY_TTL: Final[int] = 3600
"""TTL for intraday time series data (1 hour).

Intraday data is more volatile and should be refreshed frequently.
"""

FUNDAMENTALS_TTL: Final[int] = 604800
"""TTL for fundamental financial statement data (7 days).

Income statement, balance sheet, and cash flow data change infrequently.
"""

ECONOMIC_INDICATOR_TTL: Final[int] = 86400
"""TTL for economic indicator data (24 hours).

Macroeconomic data (GDP, CPI, etc.) is typically released on fixed schedules.
"""

FOREX_TTL: Final[int] = 86400
"""TTL for foreign exchange rate data (24 hours).

Daily forex rates are fixed once the trading session concludes.
"""

CRYPTO_TTL: Final[int] = 86400
"""TTL for cryptocurrency data (24 hours).

Although crypto trades 24/7, daily aggregated data is suitable for caching.
"""

GLOBAL_QUOTE_TTL: Final[int] = 300
"""TTL for global quote (real-time price) data (5 minutes).

Real-time quotes require frequent refresh for timely price information.
"""

COMPANY_OVERVIEW_TTL: Final[int] = 604800
"""TTL for company overview / profile data (7 days).

Company profile information (sector, industry, description) changes rarely.
"""


def get_alphavantage_cache() -> SQLiteCache:
    """Get a SQLiteCache instance configured for Alpha Vantage data.

    Creates a persistent cache with a default TTL of 24 hours
    (``TIME_SERIES_DAILY_TTL``) and a capacity of 10 000 entries.

    Returns
    -------
    SQLiteCache
        A configured cache instance for Alpha Vantage data.

    Examples
    --------
    >>> cache = get_alphavantage_cache()
    >>> cache.set("av:daily:AAPL", data, ttl=TIME_SERIES_DAILY_TTL)
    """
    cache = create_persistent_cache(
        ttl_seconds=TIME_SERIES_DAILY_TTL,
        max_entries=10000,
    )
    logger.debug("Alpha Vantage cache instance created")
    return cache


__all__ = [
    "COMPANY_OVERVIEW_TTL",
    "CRYPTO_TTL",
    "ECONOMIC_INDICATOR_TTL",
    "FOREX_TTL",
    "FUNDAMENTALS_TTL",
    "GLOBAL_QUOTE_TTL",
    "TIME_SERIES_DAILY_TTL",
    "TIME_SERIES_INTRADAY_TTL",
    "get_alphavantage_cache",
]
