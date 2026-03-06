"""Cache helpers for the J-Quants API module.

This module provides TTL constants and a convenience function for
obtaining a SQLiteCache instance configured for J-Quants data.

See Also
--------
market.cache.cache : Core SQLiteCache implementation.
"""

from typing import Final

from market.cache.cache import SQLiteCache, create_persistent_cache
from utils_core.logging import get_logger

logger = get_logger(__name__)

# ---------------------------------------------------------------------------
# TTL constants (seconds)
# ---------------------------------------------------------------------------

DAILY_QUOTES_TTL: Final[int] = 86400
"""TTL for daily stock quotes (24 hours).

Daily OHLC data does not change once the trading day is complete.
"""

LISTED_INFO_TTL: Final[int] = 604800
"""TTL for listed company information (7 days).

Listed info rarely changes; weekly refresh is sufficient.
"""

FINANCIAL_TTL: Final[int] = 86400
"""TTL for financial statement data (24 hours).

Financial data may be updated after earnings releases.
"""

TRADING_CALENDAR_TTL: Final[int] = 604800
"""TTL for trading calendar data (7 days).

Trading calendar is published well in advance and changes infrequently.
"""


def get_jquants_cache() -> SQLiteCache:
    """Get a SQLiteCache instance configured for J-Quants data.

    Creates a persistent cache with a default TTL of 24 hours
    and the source identifier ``"jquants"``.

    Returns
    -------
    SQLiteCache
        A configured cache instance for J-Quants data.

    Examples
    --------
    >>> cache = get_jquants_cache()
    >>> cache.set("jquants:listed:7203", data, ttl=LISTED_INFO_TTL)
    """
    cache = create_persistent_cache(
        ttl_seconds=DAILY_QUOTES_TTL,
        max_entries=10000,
    )
    logger.debug("J-Quants cache instance created")
    return cache


__all__ = [
    "DAILY_QUOTES_TTL",
    "FINANCIAL_TTL",
    "LISTED_INFO_TTL",
    "TRADING_CALENDAR_TTL",
    "get_jquants_cache",
]
