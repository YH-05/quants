"""Storage constants for the Polymarket persistence layer.

This module defines SQLite table name constants and database path
settings for the Polymarket long-term storage layer. All table names
use the ``pm_`` prefix to avoid collisions with other market modules.

Tables managed
--------------
- ``pm_events`` -- Top-level prediction events (PK: ``id``)
- ``pm_markets`` -- Individual prediction markets (PK: ``condition_id``)
- ``pm_tokens`` -- Tokens within markets (PK: ``token_id``)
- ``pm_price_history`` -- Historical price time-series
  (PK: ``token_id``, ``timestamp``, ``interval``)
- ``pm_trades`` -- Trade execution records (PK: ``id``)
- ``pm_oi_snapshots`` -- Open interest snapshots as JSON
  (PK: ``condition_id``, ``fetched_at``)
- ``pm_orderbook_snapshots`` -- Order book snapshots as JSON
  (PK: ``condition_id``, ``fetched_at``)
- ``pm_leaderboard_snapshots`` -- Leaderboard snapshots as JSON
  (PK: ``fetched_at``)

See Also
--------
market.edinet.constants : Similar constant pattern used by the EDINET module.
market.polymarket.constants : API-level constants (base URLs, rate limits).
"""

from typing import Final

# ---------------------------------------------------------------------------
# 1. Database path settings
# ---------------------------------------------------------------------------

PM_DB_PATH_ENV: Final[str] = "POLYMARKET_DB_PATH"
"""Environment variable name for overriding the default SQLite file path.

When set, this takes precedence over the default path resolved by
``get_db_path("sqlite", "polymarket")``.
"""

DEFAULT_DB_SUBDIR: Final[str] = "sqlite"
"""Default subdirectory name under ``DATA_DIR`` for SQLite files.

Used as the first argument to ``get_db_path()`` when resolving the
default database path.
"""

DEFAULT_DB_NAME: Final[str] = "polymarket"
"""Default database name (without extension) for the Polymarket SQLite file.

Used as the second argument to ``get_db_path()`` when resolving the
default database path. The resulting file is ``polymarket.db``.
"""

# ---------------------------------------------------------------------------
# 2. SQLite table names (pm_ prefix)
# ---------------------------------------------------------------------------

TABLE_EVENTS: Final[str] = "pm_events"
"""SQLite table name for top-level prediction events.

Primary key: ``id``. Contains event metadata such as title, slug,
description, start/end dates, and aggregate volume/liquidity.
"""

TABLE_MARKETS: Final[str] = "pm_markets"
"""SQLite table name for individual prediction markets.

Primary key: ``condition_id``. Contains market question, description,
status flags, volume, liquidity, and optional holders JSON.
"""

TABLE_TOKENS: Final[str] = "pm_tokens"
"""SQLite table name for tokens within markets.

Primary key: ``token_id``. Contains token outcome label, price,
and the parent market's condition_id as a foreign key reference.
"""

TABLE_PRICE_HISTORY: Final[str] = "pm_price_history"
"""SQLite table name for historical price time-series.

Primary key: ``(token_id, timestamp, interval)``. Stores price
data points at various time intervals (1h, 6h, 1d, 1w, 1m).
"""

TABLE_TRADES: Final[str] = "pm_trades"
"""SQLite table name for trade execution records.

Primary key: ``id``. Contains trade price, size, side, and
the associated market/asset identifiers.
"""

TABLE_OI_SNAPSHOTS: Final[str] = "pm_oi_snapshots"
"""SQLite table name for open interest snapshots.

Primary key: ``(condition_id, fetched_at)``. Stores open interest
data as a JSON string to accommodate variable schema.
"""

TABLE_ORDERBOOK_SNAPSHOTS: Final[str] = "pm_orderbook_snapshots"
"""SQLite table name for order book snapshots.

Primary key: ``(condition_id, fetched_at)``. Stores full order book
(bids and asks) as a JSON string.
"""

TABLE_LEADERBOARD_SNAPSHOTS: Final[str] = "pm_leaderboard_snapshots"
"""SQLite table name for leaderboard snapshots.

Primary key: ``fetched_at``. Stores the full leaderboard ranking
as a JSON string.
"""

# ---------------------------------------------------------------------------
# Module exports
# ---------------------------------------------------------------------------

__all__ = [
    "DEFAULT_DB_NAME",
    "DEFAULT_DB_SUBDIR",
    "PM_DB_PATH_ENV",
    "TABLE_EVENTS",
    "TABLE_LEADERBOARD_SNAPSHOTS",
    "TABLE_MARKETS",
    "TABLE_OI_SNAPSHOTS",
    "TABLE_ORDERBOOK_SNAPSHOTS",
    "TABLE_PRICE_HISTORY",
    "TABLE_TOKENS",
    "TABLE_TRADES",
]
