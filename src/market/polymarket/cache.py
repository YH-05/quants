"""Cache helpers for the Polymarket API module.

This module provides TTL constants for a 6-tier caching strategy
and a convenience function for obtaining a SQLiteCache instance
configured for Polymarket data.

The TTL tiers correspond to data volatility:

1. ``ORDERBOOK_TTL`` (30s) - Real-time order book snapshots
2. ``ACTIVE_PRICES_TTL`` (60s) - Active market prices
3. ``OI_TRADES_TTL`` (300s) - Open interest and trade data
4. ``METADATA_TTL`` (3600s) - Market/event metadata
5. ``LEADERBOARD_TTL`` (3600s) - Leaderboard rankings
6. ``RESOLVED_TTL`` (2592000s) - Resolved/settled market data (30 days)

See Also
--------
market.cache.cache : Core SQLiteCache implementation.
market.jquants.cache : Similar cache pattern for the J-Quants module.
"""

from typing import Final

from market.cache.cache import SQLiteCache, create_persistent_cache
from utils_core.logging import get_logger

logger = get_logger(__name__)

# ---------------------------------------------------------------------------
# TTL constants (seconds)
# ---------------------------------------------------------------------------

ORDERBOOK_TTL: Final[int] = 30
"""TTL for order book snapshots (30 seconds).

Order book data is highly volatile and changes with every trade.
"""

ACTIVE_PRICES_TTL: Final[int] = 60
"""TTL for active market prices (60 seconds).

Prices update frequently but less often than the full order book.
"""

OI_TRADES_TTL: Final[int] = 300
"""TTL for open interest and trade data (5 minutes).

Aggregate trade and OI data can tolerate slightly stale values.
"""

METADATA_TTL: Final[int] = 3600
"""TTL for market and event metadata (1 hour).

Market descriptions, questions, and event details change infrequently.
"""

LEADERBOARD_TTL: Final[int] = 3600
"""TTL for leaderboard data (1 hour).

Leaderboard rankings are updated periodically by the platform.
"""

RESOLVED_TTL: Final[int] = 2592000
"""TTL for resolved/settled market data (30 days).

Once a market is resolved, its data is immutable and can be cached
for a long period.
"""


def get_polymarket_cache() -> SQLiteCache:
    """Get a SQLiteCache instance configured for Polymarket data.

    Creates a persistent cache with a default TTL matching
    ``ACTIVE_PRICES_TTL`` (60 seconds) and the source identifier
    ``"polymarket"``.

    Returns
    -------
    SQLiteCache
        A configured cache instance for Polymarket data.

    Examples
    --------
    >>> cache = get_polymarket_cache()
    >>> cache.set("polymarket:orderbook:0xabc", data, ttl=ORDERBOOK_TTL)
    """
    cache = create_persistent_cache(
        ttl_seconds=ACTIVE_PRICES_TTL,
        max_entries=10000,
    )
    logger.debug("Polymarket cache instance created")
    return cache


__all__ = [
    "ACTIVE_PRICES_TTL",
    "LEADERBOARD_TTL",
    "METADATA_TTL",
    "OI_TRADES_TTL",
    "ORDERBOOK_TTL",
    "RESOLVED_TTL",
    "get_polymarket_cache",
]
