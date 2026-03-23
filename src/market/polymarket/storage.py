"""SQLite storage layer for Polymarket prediction market data.

This module provides the ``PolymarketStorage`` class that manages 8 SQLite
tables for persisting Polymarket API data. It uses the existing
``SQLiteClient`` from ``database.db`` for all database operations.

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

Examples
--------
>>> from market.polymarket.storage import get_polymarket_storage
>>> storage = get_polymarket_storage()
>>> tables = storage.get_table_names()
>>> len(tables)
8

See Also
--------
database.db.sqlite_client.SQLiteClient : Underlying SQLite client.
market.edinet.storage : Reference implementation (DDL dict + ensure_tables).
market.polymarket.storage_constants : Table name constants.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import TYPE_CHECKING, Any

from database.db.connection import get_db_path
from database.db.sqlite_client import SQLiteClient
from market.polymarket.storage_constants import (
    DEFAULT_DB_NAME,
    PM_DB_PATH_ENV,
    TABLE_EVENTS,
    TABLE_LEADERBOARD_SNAPSHOTS,
    TABLE_MARKETS,
    TABLE_OI_SNAPSHOTS,
    TABLE_ORDERBOOK_SNAPSHOTS,
    TABLE_PRICE_HISTORY,
    TABLE_TOKENS,
    TABLE_TRADES,
)
from utils_core.logging import get_logger

if TYPE_CHECKING:
    from market.polymarket.models import PolymarketEvent, PolymarketMarket

logger = get_logger(__name__)


# ============================================================================
# SQL helper
# ============================================================================


def _build_insert_sql(table_name: str, field_names: list[str]) -> str:
    """Build an INSERT OR REPLACE SQL statement for the given table and fields.

    Parameters
    ----------
    table_name : str
        Target table name. Must be in ``_VALID_TABLE_NAMES``.
    field_names : list[str]
        List of column names.

    Returns
    -------
    str
        SQL INSERT OR REPLACE statement with ``?`` placeholders.
    """
    cols = ", ".join(field_names)
    placeholders = ", ".join("?" for _ in field_names)
    return f"INSERT OR REPLACE INTO {table_name} ({cols}) VALUES ({placeholders})"  # nosec B608


# ============================================================================
# Table DDL definitions (SQLite types)
# ============================================================================

_TABLE_DDL: dict[str, str] = {
    TABLE_EVENTS: f"""
        CREATE TABLE IF NOT EXISTS {TABLE_EVENTS} (
            id TEXT NOT NULL,
            title TEXT NOT NULL,
            slug TEXT NOT NULL,
            description TEXT,
            start_date TEXT,
            end_date TEXT,
            active INTEGER,
            closed INTEGER,
            volume REAL,
            liquidity REAL,
            fetched_at TEXT NOT NULL,
            PRIMARY KEY (id)
        )
    """,
    TABLE_MARKETS: f"""
        CREATE TABLE IF NOT EXISTS {TABLE_MARKETS} (
            condition_id TEXT NOT NULL,
            event_id TEXT,
            question TEXT NOT NULL,
            description TEXT,
            end_date_iso TEXT,
            active INTEGER,
            closed INTEGER,
            volume REAL,
            liquidity REAL,
            holders_json TEXT,
            fetched_at TEXT NOT NULL,
            PRIMARY KEY (condition_id)
        )
    """,
    TABLE_TOKENS: f"""
        CREATE TABLE IF NOT EXISTS {TABLE_TOKENS} (
            token_id TEXT NOT NULL,
            condition_id TEXT NOT NULL,
            outcome TEXT NOT NULL,
            price REAL,
            fetched_at TEXT NOT NULL,
            PRIMARY KEY (token_id)
        )
    """,
    TABLE_PRICE_HISTORY: f"""
        CREATE TABLE IF NOT EXISTS {TABLE_PRICE_HISTORY} (
            token_id TEXT NOT NULL,
            timestamp INTEGER NOT NULL,
            interval TEXT NOT NULL,
            price REAL NOT NULL,
            fetched_at TEXT NOT NULL,
            PRIMARY KEY (token_id, timestamp, interval)
        )
    """,
    TABLE_TRADES: f"""
        CREATE TABLE IF NOT EXISTS {TABLE_TRADES} (
            id TEXT NOT NULL,
            market TEXT NOT NULL,
            asset_id TEXT NOT NULL,
            price REAL NOT NULL,
            size REAL NOT NULL,
            side TEXT,
            timestamp TEXT,
            fetched_at TEXT NOT NULL,
            PRIMARY KEY (id)
        )
    """,
    TABLE_OI_SNAPSHOTS: f"""
        CREATE TABLE IF NOT EXISTS {TABLE_OI_SNAPSHOTS} (
            condition_id TEXT NOT NULL,
            fetched_at TEXT NOT NULL,
            data_json TEXT NOT NULL,
            PRIMARY KEY (condition_id, fetched_at)
        )
    """,
    TABLE_ORDERBOOK_SNAPSHOTS: f"""
        CREATE TABLE IF NOT EXISTS {TABLE_ORDERBOOK_SNAPSHOTS} (
            condition_id TEXT NOT NULL,
            fetched_at TEXT NOT NULL,
            data_json TEXT NOT NULL,
            PRIMARY KEY (condition_id, fetched_at)
        )
    """,
    TABLE_LEADERBOARD_SNAPSHOTS: f"""
        CREATE TABLE IF NOT EXISTS {TABLE_LEADERBOARD_SNAPSHOTS} (
            fetched_at TEXT NOT NULL,
            data_json TEXT NOT NULL,
            PRIMARY KEY (fetched_at)
        )
    """,
}

# Valid table names whitelist for SQL injection prevention
_VALID_TABLE_NAMES: frozenset[str] = frozenset(_TABLE_DDL.keys())


# ============================================================================
# PolymarketStorage class
# ============================================================================


class PolymarketStorage:
    """SQLite storage layer for Polymarket prediction market data.

    Manages 8 SQLite tables and provides ``ensure_tables()`` for schema
    creation. Uses ``CREATE TABLE IF NOT EXISTS`` for idempotent DDL.

    Parameters
    ----------
    db_path : Path
        Path to the SQLite database file.

    Examples
    --------
    >>> from pathlib import Path
    >>> storage = PolymarketStorage(db_path=Path("/tmp/polymarket.db"))
    >>> tables = storage.get_table_names()
    >>> len(tables)
    8
    """

    def __init__(self, db_path: Path) -> None:
        self._client = SQLiteClient(db_path)
        logger.debug(
            "PolymarketStorage initialized",
            db_path=str(db_path),
        )
        self.ensure_tables()

    # ------------------------------------------------------------------
    # Schema management
    # ------------------------------------------------------------------

    def ensure_tables(self) -> None:
        """Create all 8 tables if they do not already exist.

        Executes ``CREATE TABLE IF NOT EXISTS`` for each table defined
        in the Polymarket schema. Safe to call multiple times.
        """
        logger.debug("Ensuring Polymarket tables exist")
        for table_name, ddl in _TABLE_DDL.items():
            self._client.execute(ddl)
            logger.debug("Table ensured", table_name=table_name)
        logger.info(
            "All Polymarket tables ensured",
            table_count=len(_TABLE_DDL),
        )

    # ------------------------------------------------------------------
    # Introspection
    # ------------------------------------------------------------------

    def get_table_names(self) -> list[str]:
        """Get the list of managed Polymarket table names.

        Returns
        -------
        list[str]
            Sorted list of the 8 table names managed by this storage.
        """
        return sorted(_VALID_TABLE_NAMES)

    # ------------------------------------------------------------------
    # Upsert methods
    # ------------------------------------------------------------------

    def upsert_events(
        self,
        events: list[PolymarketEvent],
        *,
        fetched_at: str,
    ) -> None:
        """Upsert events with cascading saves of child markets and tokens.

        For each event, the event row is inserted/replaced in ``pm_events``,
        then ``upsert_markets()`` is called for the event's markets with
        the event's ``id`` as the ``event_id`` foreign key.

        Parameters
        ----------
        events : list[PolymarketEvent]
            List of Pydantic event models to persist.
        fetched_at : str
            ISO 8601 timestamp for the ``fetched_at`` column.
        """
        if not events:
            logger.debug("No events to upsert, skipping")
            return

        event_columns = [
            "id",
            "title",
            "slug",
            "description",
            "start_date",
            "end_date",
            "active",
            "closed",
            "volume",
            "liquidity",
            "fetched_at",
        ]
        sql = _build_insert_sql(TABLE_EVENTS, event_columns)

        params: list[tuple[Any, ...]] = []
        all_markets: list[tuple[PolymarketMarket, str]] = []

        for event in events:
            params.append(
                (
                    event.id,
                    event.title,
                    event.slug,
                    event.description,
                    event.start_date,
                    event.end_date,
                    int(event.active) if event.active is not None else None,
                    int(event.closed) if event.closed is not None else None,
                    event.volume,
                    event.liquidity,
                    fetched_at,
                )
            )
            for market in event.markets:
                all_markets.append((market, event.id))

        self._client.execute_many(sql, params)
        logger.info("Events upserted", count=len(events))

        # Cascade: upsert child markets grouped by event_id
        for market, event_id in all_markets:
            self.upsert_markets([market], fetched_at=fetched_at, event_id=event_id)

    def upsert_markets(
        self,
        markets: list[PolymarketMarket],
        *,
        fetched_at: str,
        event_id: str | None = None,
    ) -> None:
        """Upsert markets with cascading saves of child tokens.

        Each market row is inserted/replaced in ``pm_markets``. Valid
        tokens (those containing both ``token_id`` and ``outcome``) are
        extracted and upserted into ``pm_tokens``.

        Parameters
        ----------
        markets : list[PolymarketMarket]
            List of Pydantic market models to persist.
        fetched_at : str
            ISO 8601 timestamp for the ``fetched_at`` column.
        event_id : str | None
            Optional parent event ID to set as foreign key. When called
            from ``upsert_events()``, this is set automatically.
        """
        if not markets:
            logger.debug("No markets to upsert, skipping")
            return

        market_columns = [
            "condition_id",
            "event_id",
            "question",
            "description",
            "end_date_iso",
            "active",
            "closed",
            "volume",
            "liquidity",
            "holders_json",
            "fetched_at",
        ]
        market_sql = _build_insert_sql(TABLE_MARKETS, market_columns)

        market_params: list[tuple[Any, ...]] = []
        token_params: list[tuple[Any, ...]] = []

        for market in markets:
            market_params.append(
                (
                    market.condition_id,
                    event_id,
                    market.question,
                    market.description,
                    market.end_date_iso,
                    int(market.active) if market.active is not None else None,
                    int(market.closed) if market.closed is not None else None,
                    market.volume,
                    market.liquidity,
                    None,  # holders_json — not in the Pydantic model
                    fetched_at,
                )
            )

            # Extract valid tokens
            for tok in market.tokens:
                token_id = tok.get("token_id")
                outcome = tok.get("outcome")
                if not token_id or not outcome:
                    logger.debug(
                        "Skipping token missing token_id or outcome",
                        condition_id=market.condition_id,
                        token_keys=list(tok.keys()),
                    )
                    continue
                token_params.append(
                    (
                        str(token_id),
                        market.condition_id,
                        str(outcome),
                        tok.get("price"),
                        fetched_at,
                    )
                )

        self._client.execute_many(market_sql, market_params)
        logger.info("Markets upserted", count=len(markets))

        if token_params:
            token_columns = [
                "token_id",
                "condition_id",
                "outcome",
                "price",
                "fetched_at",
            ]
            token_sql = _build_insert_sql(TABLE_TOKENS, token_columns)
            self._client.execute_many(token_sql, token_params)
            logger.info("Tokens upserted", count=len(token_params))

    # ------------------------------------------------------------------
    # Statistics
    # ------------------------------------------------------------------

    def get_stats(self) -> dict[str, int]:
        """Get row counts for all 8 tables.

        Returns
        -------
        dict[str, int]
            Dictionary mapping table name to row count.
        """
        logger.debug("Getting table statistics")
        stats: dict[str, int] = {}
        for tbl in sorted(_VALID_TABLE_NAMES):
            rows = self._client.execute(
                f"SELECT COUNT(*) AS cnt FROM {tbl}"  # nosec B608
            )
            stats[tbl] = rows[0]["cnt"]
        logger.info("Table statistics retrieved", stats=stats)
        return stats


# ============================================================================
# Factory function
# ============================================================================


def _resolve_db_path() -> Path:
    """Resolve the Polymarket SQLite database path.

    Resolution priority:

    1. ``POLYMARKET_DB_PATH`` environment variable (if set and non-empty)
    2. Default path via ``get_db_path("sqlite", "polymarket")``

    Returns
    -------
    Path
        Resolved path to the SQLite database file.
    """
    env_path = os.environ.get(PM_DB_PATH_ENV, "")
    if env_path:
        return Path(env_path)
    return get_db_path("sqlite", DEFAULT_DB_NAME)


def get_polymarket_storage() -> PolymarketStorage:
    """Create a ``PolymarketStorage`` instance with the resolved DB path.

    The database path is resolved by ``_resolve_db_path()`` which checks
    the ``POLYMARKET_DB_PATH`` environment variable first, then falls back
    to the default ``data/sqlite/polymarket.db`` location.

    Returns
    -------
    PolymarketStorage
        A configured storage instance with all 8 tables ensured.

    Examples
    --------
    >>> storage = get_polymarket_storage()
    >>> "pm_events" in storage.get_table_names()
    True
    """
    db_path = _resolve_db_path()
    logger.info("Creating PolymarketStorage", db_path=str(db_path))
    return PolymarketStorage(db_path=db_path)
