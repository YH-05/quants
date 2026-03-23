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

import json
import math
import os
from functools import lru_cache
from pathlib import Path
from typing import TYPE_CHECKING, Any

import pandas as pd

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
    from market.polymarket.models import (
        OrderBook,
        PolymarketEvent,
        PolymarketMarket,
        PricePoint,
        TradeRecord,
    )
    from market.polymarket.types import PriceInterval

logger = get_logger(__name__)


# ============================================================================
# Validation helpers
# ============================================================================


def _validate_finite(value: float | None, name: str) -> float | None:
    """Validate that a numeric value is finite (not NaN or Inf).

    Parameters
    ----------
    value : float | None
        Value to validate. ``None`` is passed through unchanged.
    name : str
        Field name for error messages.

    Returns
    -------
    float | None
        The validated value.

    Raises
    ------
    ValueError
        If the value is NaN or Inf.
    """
    if value is not None and not math.isfinite(value):
        msg = f"{name} must be finite, got {value}"
        raise ValueError(msg)
    return value


# ============================================================================
# SQL helper
# ============================================================================


@lru_cache(maxsize=16)
def _build_insert_sql(table_name: str, field_names: tuple[str, ...]) -> str:
    """Build an INSERT OR REPLACE SQL statement for the given table and fields.

    Parameters
    ----------
    table_name : str
        Target table name. Must be in ``_VALID_TABLE_NAMES``.
    field_names : tuple[str, ...]
        Tuple of column names (tuple required for lru_cache hashability).

    Returns
    -------
    str
        SQL INSERT OR REPLACE statement with ``?`` placeholders.
    """
    if table_name not in _VALID_TABLE_NAMES:
        msg = f"Invalid table name: '{table_name}'. Must be one of: {sorted(_VALID_TABLE_NAMES)}"
        raise ValueError(msg)
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
        """Initialize storage and create all 8 tables.

        Calls ``ensure_tables()`` automatically on initialization.
        """
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

        event_columns = (
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
        )
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
                    _validate_finite(event.volume, "event.volume"),
                    _validate_finite(event.liquidity, "event.liquidity"),
                    fetched_at,
                )
            )
            for market in event.markets:
                all_markets.append((market, event.id))

        self._client.execute_many(sql, params)
        logger.info("Events upserted", count=len(events))

        # Cascade: batch upsert child markets grouped by event_id
        markets_by_event: dict[str, list[PolymarketMarket]] = {}
        for market, eid in all_markets:
            markets_by_event.setdefault(eid, []).append(market)
        for eid, market_list in markets_by_event.items():
            self.upsert_markets(market_list, fetched_at=fetched_at, event_id=eid)

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

        market_columns = (
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
        )
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
                    _validate_finite(market.volume, "market.volume"),
                    _validate_finite(market.liquidity, "market.liquidity"),
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
                raw_price = tok.get("price")
                if isinstance(raw_price, float):
                    _validate_finite(raw_price, "token.price")
                token_params.append(
                    (
                        str(token_id),
                        market.condition_id,
                        str(outcome),
                        raw_price,
                        fetched_at,
                    )
                )

        self._client.execute_many(market_sql, market_params)
        logger.info("Markets upserted", count=len(markets))

        if token_params:
            token_columns = (
                "token_id",
                "condition_id",
                "outcome",
                "price",
                "fetched_at",
            )
            token_sql = _build_insert_sql(TABLE_TOKENS, token_columns)
            self._client.execute_many(token_sql, token_params)
            logger.info("Tokens upserted", count=len(token_params))

    def upsert_price_history(
        self,
        token_id: str,
        prices: list[PricePoint],
        interval: PriceInterval,
        *,
        fetched_at: str,
    ) -> None:
        """Upsert historical price data for a token.

        Inserts or replaces rows in ``pm_price_history`` using the composite
        primary key ``(token_id, timestamp, interval)``. Duplicate entries
        (same token, timestamp, and interval) are overwritten, ensuring
        idempotent behaviour.

        Parameters
        ----------
        token_id : str
            The token identifier to associate price data with.
        prices : list[PricePoint]
            List of price points. Each ``PricePoint`` has ``t`` (unix
            timestamp) and ``p`` (price value).
        interval : PriceInterval
            The time interval for the price data (e.g., ``PriceInterval.ONE_HOUR``).
        fetched_at : str
            ISO 8601 timestamp for the ``fetched_at`` column.
        """
        if not prices:
            logger.debug(
                "No price history to upsert, skipping",
                token_id=token_id,
            )
            return

        columns = (
            "token_id",
            "timestamp",
            "interval",
            "price",
            "fetched_at",
        )
        sql = _build_insert_sql(TABLE_PRICE_HISTORY, columns)

        params: list[tuple[Any, ...]] = [
            (
                token_id,
                price_point.t,
                str(interval),
                _validate_finite(price_point.p, "price_point.p"),
                fetched_at,
            )
            for price_point in prices
        ]

        self._client.execute_many(sql, params)
        logger.info(
            "Price history upserted",
            token_id=token_id,
            interval=str(interval),
            count=len(prices),
        )

    def upsert_trades(
        self,
        trades: list[TradeRecord],
        *,
        fetched_at: str,
    ) -> None:
        """Upsert trade execution records into ``pm_trades``.

        Inserts or replaces rows using the trade ``id`` as primary key.
        Duplicate trade IDs are overwritten, ensuring idempotent behaviour.

        Parameters
        ----------
        trades : list[TradeRecord]
            List of Pydantic trade models to persist.
        fetched_at : str
            ISO 8601 timestamp for the ``fetched_at`` column.
        """
        if not trades:
            logger.debug("No trades to upsert, skipping")
            return

        columns = (
            "id",
            "market",
            "asset_id",
            "price",
            "size",
            "side",
            "timestamp",
            "fetched_at",
        )
        sql = _build_insert_sql(TABLE_TRADES, columns)

        params: list[tuple[Any, ...]] = [
            (
                trade.id or "",
                trade.market or "",
                trade.asset_id,
                _validate_finite(trade.price, "trade.price"),
                _validate_finite(trade.size, "trade.size"),
                trade.side,
                trade.timestamp.isoformat() if trade.timestamp else None,
                fetched_at,
            )
            for trade in trades
        ]

        self._client.execute_many(sql, params)
        logger.info("Trades upserted", count=len(trades))

    def insert_oi_snapshot(
        self,
        condition_id: str,
        data: dict[str, Any],
        *,
        fetched_at: str,
    ) -> None:
        """Insert an open interest snapshot as JSON into ``pm_oi_snapshots``.

        Uses the composite primary key ``(condition_id, fetched_at)``.
        Duplicate entries are overwritten, ensuring idempotent behaviour.

        Parameters
        ----------
        condition_id : str
            The market condition ID.
        data : dict[str, Any]
            Open interest data to store as a JSON string.
        fetched_at : str
            ISO 8601 timestamp for the ``fetched_at`` column.
        """
        columns = ("condition_id", "fetched_at", "data_json")
        sql = _build_insert_sql(TABLE_OI_SNAPSHOTS, columns)

        data_json = json.dumps(data, ensure_ascii=False)
        self._client.execute(sql, (condition_id, fetched_at, data_json))
        logger.info(
            "OI snapshot inserted",
            condition_id=condition_id,
            fetched_at=fetched_at,
        )

    def insert_orderbook_snapshot(
        self,
        orderbook: OrderBook,
        *,
        fetched_at: str,
    ) -> None:
        """Insert an order book snapshot as JSON into ``pm_orderbook_snapshots``.

        Uses the composite primary key ``(condition_id, fetched_at)`` where
        ``condition_id`` is derived from ``orderbook.market``.

        Parameters
        ----------
        orderbook : OrderBook
            Pydantic order book model to persist.
        fetched_at : str
            ISO 8601 timestamp for the ``fetched_at`` column.
        """
        columns = ("condition_id", "fetched_at", "data_json")
        sql = _build_insert_sql(TABLE_ORDERBOOK_SNAPSHOTS, columns)

        data_json = orderbook.model_dump_json()
        self._client.execute(sql, (orderbook.market, fetched_at, data_json))
        logger.info(
            "Orderbook snapshot inserted",
            condition_id=orderbook.market,
            fetched_at=fetched_at,
        )

    def insert_leaderboard_snapshot(
        self,
        entries: list[dict[str, Any]],
        *,
        fetched_at: str,
    ) -> None:
        """Insert a leaderboard snapshot as JSON into ``pm_leaderboard_snapshots``.

        Uses ``fetched_at`` as the primary key. Duplicate timestamps
        are overwritten, ensuring idempotent behaviour.

        Parameters
        ----------
        entries : list[dict[str, Any]]
            List of leaderboard entries to store as a JSON string.
        fetched_at : str
            ISO 8601 timestamp for the ``fetched_at`` column.
        """
        columns = ("fetched_at", "data_json")
        sql = _build_insert_sql(TABLE_LEADERBOARD_SNAPSHOTS, columns)

        data_json = json.dumps(entries, ensure_ascii=False)
        self._client.execute(sql, (fetched_at, data_json))
        logger.info(
            "Leaderboard snapshot inserted",
            fetched_at=fetched_at,
            entry_count=len(entries),
        )

    def upsert_holders(
        self,
        condition_id: str,
        holders: list[dict[str, Any]],
    ) -> None:
        """Update the ``holders_json`` column in ``pm_markets``.

        Updates the existing market row identified by ``condition_id``
        with the serialized holders data. If the market row does not
        exist, the update silently affects zero rows.

        Parameters
        ----------
        condition_id : str
            The market condition ID to update.
        holders : list[dict[str, Any]]
            List of holder records to store as a JSON string.
        """
        holders_json = json.dumps(holders, ensure_ascii=False)
        sql = f"UPDATE {TABLE_MARKETS} SET holders_json = ? WHERE condition_id = ?"  # nosec B608
        self._client.execute(sql, (holders_json, condition_id))
        logger.info(
            "Holders upserted",
            condition_id=condition_id,
            holder_count=len(holders),
        )

    # ------------------------------------------------------------------
    # Query methods
    # ------------------------------------------------------------------

    def get_events(self, *, active_only: bool = False) -> pd.DataFrame:
        """Get events as a DataFrame.

        Parameters
        ----------
        active_only : bool
            If ``True``, return only events where ``active = 1``.
            Defaults to ``False`` (return all events).

        Returns
        -------
        pd.DataFrame
            Events data. Returns an empty DataFrame if no events match.
        """
        logger.debug("Getting events", active_only=active_only)
        sql = f"SELECT * FROM {TABLE_EVENTS}"  # nosec B608
        params: list[Any] = []
        if active_only:
            sql += " WHERE active = ?"
            params.append(1)
        with self._client.connection() as conn:
            df = pd.read_sql_query(sql, conn, params=params)
        logger.info("Events retrieved", count=len(df))
        return df

    def get_markets(
        self,
        *,
        event_id: str | None = None,
        active_only: bool = False,
    ) -> pd.DataFrame:
        """Get markets as a DataFrame.

        Parameters
        ----------
        event_id : str | None
            If provided, filter markets by parent event ID.
        active_only : bool
            If ``True``, return only markets where ``active = 1``.
            Defaults to ``False`` (return all markets).

        Returns
        -------
        pd.DataFrame
            Markets data. Returns an empty DataFrame if no markets match.
        """
        logger.debug("Getting markets", event_id=event_id, active_only=active_only)
        sql = f"SELECT * FROM {TABLE_MARKETS}"  # nosec B608
        conditions: list[str] = []
        params: list[Any] = []
        if event_id is not None:
            conditions.append("event_id = ?")
            params.append(event_id)
        if active_only:
            conditions.append("active = ?")
            params.append(1)
        if conditions:
            sql += " WHERE " + " AND ".join(conditions)
        with self._client.connection() as conn:
            df = pd.read_sql_query(sql, conn, params=params)
        logger.info("Markets retrieved", count=len(df))
        return df

    def get_tokens(self, condition_id: str) -> pd.DataFrame:
        """Get tokens for a specific market as a DataFrame.

        Parameters
        ----------
        condition_id : str
            The market condition ID to filter tokens by.

        Returns
        -------
        pd.DataFrame
            Tokens data. Returns an empty DataFrame if no tokens match.
        """
        logger.debug("Getting tokens", condition_id=condition_id)
        sql = f"SELECT * FROM {TABLE_TOKENS} WHERE condition_id = ?"  # nosec B608
        with self._client.connection() as conn:
            df = pd.read_sql_query(sql, conn, params=[condition_id])
        logger.info("Tokens retrieved", count=len(df))
        return df

    def get_price_history(
        self,
        token_id: str,
        interval: PriceInterval | None = None,
    ) -> pd.DataFrame:
        """Get price history for a token as a DataFrame.

        Parameters
        ----------
        token_id : str
            The token identifier to retrieve price data for.
        interval : PriceInterval | None
            If provided, filter by price interval. Defaults to ``None``
            (return all intervals).

        Returns
        -------
        pd.DataFrame
            Price history data. Returns an empty DataFrame if no data
            matches.
        """
        logger.debug(
            "Getting price history",
            token_id=token_id,
            interval=str(interval) if interval else None,
        )
        sql = f"SELECT * FROM {TABLE_PRICE_HISTORY} WHERE token_id = ?"  # nosec B608
        params: list[Any] = [token_id]
        if interval is not None:
            sql += " AND interval = ?"
            params.append(str(interval))
        with self._client.connection() as conn:
            df = pd.read_sql_query(sql, conn, params=params)
        logger.info("Price history retrieved", count=len(df))
        return df

    def get_trades(
        self,
        condition_id: str,
        limit: int | None = None,
    ) -> pd.DataFrame:
        """Get trades for a specific market as a DataFrame.

        Parameters
        ----------
        condition_id : str
            The market condition ID (stored in the ``market`` column).
        limit : int | None
            If provided, limit the number of returned rows.
            Defaults to ``None`` (return all trades).

        Returns
        -------
        pd.DataFrame
            Trades data. Returns an empty DataFrame if no trades match.
        """
        logger.debug(
            "Getting trades",
            condition_id=condition_id,
            limit=limit,
        )
        sql = f"SELECT * FROM {TABLE_TRADES} WHERE market = ?"  # nosec B608
        params: list[Any] = [condition_id]
        if limit is not None:
            sql += " LIMIT ?"
            params.append(limit)
        with self._client.connection() as conn:
            df = pd.read_sql_query(sql, conn, params=params)
        logger.info("Trades retrieved", count=len(df))
        return df

    def get_oi_snapshots(self, condition_id: str) -> pd.DataFrame:
        """Get open interest snapshots for a market as a DataFrame.

        Parameters
        ----------
        condition_id : str
            The market condition ID.

        Returns
        -------
        pd.DataFrame
            OI snapshot data. Returns an empty DataFrame if no data
            matches.
        """
        logger.debug("Getting OI snapshots", condition_id=condition_id)
        sql = f"SELECT * FROM {TABLE_OI_SNAPSHOTS} WHERE condition_id = ?"  # nosec B608
        with self._client.connection() as conn:
            df = pd.read_sql_query(sql, conn, params=[condition_id])
        logger.info("OI snapshots retrieved", count=len(df))
        return df

    # ------------------------------------------------------------------
    # Statistics
    # ------------------------------------------------------------------

    def count_records(self) -> dict[str, int]:
        """Get row counts for all 8 tables.

        This is an alias for ``get_stats()`` for API consistency
        with the Issue specification.

        Returns
        -------
        dict[str, int]
            Dictionary mapping table name to row count.
        """
        return self.get_stats()

    def get_collection_summary(self) -> dict[str, Any]:
        """Get a summary of collected data.

        Returns
        -------
        dict[str, Any]
            Summary dictionary containing:

            - ``record_counts``: dict mapping table name to row count
            - ``total_records``: total number of rows across all tables
            - ``event_count``: number of events
            - ``market_count``: number of markets
        """
        logger.debug("Getting collection summary")
        counts = self.get_stats()
        total = sum(counts.values())
        summary: dict[str, Any] = {
            "record_counts": counts,
            "total_records": total,
            "event_count": counts.get(TABLE_EVENTS, 0),
            "market_count": counts.get(TABLE_MARKETS, 0),
        }
        logger.info("Collection summary retrieved", total_records=total)
        return summary

    def get_stats(self) -> dict[str, int]:
        """Get row counts for all 8 tables.

        Returns
        -------
        dict[str, int]
            Dictionary mapping table name to row count.
        """
        logger.debug("Getting table statistics")
        tables = sorted(_VALID_TABLE_NAMES)
        union_sql = " UNION ALL ".join(
            f"SELECT '{tbl}' AS tbl, COUNT(*) AS cnt FROM {tbl}"  # nosec B608
            for tbl in tables
        )
        rows = self._client.execute(union_sql)
        stats = {row["tbl"]: row["cnt"] for row in rows}
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
