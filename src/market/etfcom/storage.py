"""SQLite storage layer for ETF.com market data.

This module provides the ``ETFComStorage`` class that manages 9 SQLite
tables for persisting ETF.com data. It uses the existing
``SQLiteClient`` from ``database.db`` for all database operations,
leveraging ``INSERT OR REPLACE`` for idempotent data updates.

Tables managed
--------------
- ``etfcom_tickers`` -- ETF ticker master list from the screener
  (PK: ``ticker``)
- ``etfcom_fund_flows`` -- Daily fund flow data
  (PK: ``ticker``, ``nav_date``)
- ``etfcom_holdings`` -- Top holdings data
  (PK: ``ticker``, ``holding_ticker``, ``as_of_date``)
- ``etfcom_portfolio`` -- Portfolio characteristics
  (PK: ``ticker``)
- ``etfcom_allocations`` -- Sector/region/asset allocation breakdowns
  (PK: ``ticker``, ``allocation_type``, ``name``, ``as_of_date``)
- ``etfcom_tradability`` -- Tradability metrics (spread, volume, etc.)
  (PK: ``ticker``)
- ``etfcom_structure`` -- Fund structure metadata
  (PK: ``ticker``)
- ``etfcom_performance`` -- Historical return performance data
  (PK: ``ticker``)
- ``etfcom_quotes`` -- Delayed quote snapshots
  (PK: ``ticker``, ``quote_date``)

Examples
--------
>>> from market.etfcom.storage import get_etfcom_storage
>>> storage = get_etfcom_storage()
>>> tables = storage.get_table_names()
>>> len(tables)
9

See Also
--------
database.db.sqlite_client.SQLiteClient : Underlying SQLite client.
market.alphavantage.storage : Reference implementation (DDL dict + ensure_tables).
market.polymarket.storage : Reference implementation (DDL dict + _validate_finite).
market.etfcom.storage_constants : Table name constants.
market.etfcom.models : Storage record dataclasses.
"""

from __future__ import annotations

import dataclasses
import os
from functools import lru_cache
from pathlib import Path
from typing import TYPE_CHECKING, Any

import pandas as pd

from database.db.connection import get_db_path
from database.db.sqlite_client import SQLiteClient
from market.etfcom.storage_constants import (
    DEFAULT_DB_NAME,
    ETFCOM_DB_PATH_ENV,
    TABLE_ALLOCATIONS,
    TABLE_FUND_FLOWS,
    TABLE_HOLDINGS,
    TABLE_PERFORMANCE,
    TABLE_PORTFOLIO,
    TABLE_QUOTES,
    TABLE_STRUCTURE,
    TABLE_TICKERS,
    TABLE_TRADABILITY,
)
from utils_core.logging import get_logger

if TYPE_CHECKING:
    from market.etfcom.models import (
        AllocationRecord,
        FundFlowsRecord,
        HoldingRecord,
        PerformanceRecord,
        PortfolioRecord,
        QuoteRecord,
        StructureRecord,
        TickerRecord,
        TradabilityRecord,
    )

logger = get_logger(__name__)


# ============================================================================
# Dataclass helpers
# ============================================================================


def _dataclass_to_tuple(obj: object) -> tuple[Any, ...]:
    """Convert a dataclass instance to a tuple of field values.

    Parameters
    ----------
    obj : object
        A dataclass instance.

    Returns
    -------
    tuple[Any, ...]
        Tuple of all field values in field definition order.
    """
    return tuple(getattr(obj, f.name) for f in dataclasses.fields(obj))  # type: ignore[arg-type]


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

    Raises
    ------
    ValueError
        If ``table_name`` is not in the allowed table list.
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
    TABLE_TICKERS: f"""
        CREATE TABLE IF NOT EXISTS {TABLE_TICKERS} (
            ticker TEXT NOT NULL,
            fund_id INTEGER NOT NULL,
            name TEXT,
            issuer TEXT,
            asset_class TEXT,
            inception_date TEXT,
            segment TEXT,
            fetched_at TEXT NOT NULL,
            PRIMARY KEY (ticker)
        )
    """,
    TABLE_FUND_FLOWS: f"""
        CREATE TABLE IF NOT EXISTS {TABLE_FUND_FLOWS} (
            ticker TEXT NOT NULL,
            nav_date TEXT NOT NULL,
            nav REAL,
            nav_change REAL,
            nav_change_percent REAL,
            premium_discount REAL,
            fund_flows REAL,
            shares_outstanding REAL,
            aum REAL,
            fetched_at TEXT NOT NULL,
            PRIMARY KEY (ticker, nav_date)
        )
    """,
    TABLE_HOLDINGS: f"""
        CREATE TABLE IF NOT EXISTS {TABLE_HOLDINGS} (
            ticker TEXT NOT NULL,
            holding_ticker TEXT NOT NULL,
            as_of_date TEXT NOT NULL,
            holding_name TEXT,
            weight REAL,
            market_value REAL,
            shares REAL,
            fetched_at TEXT NOT NULL,
            PRIMARY KEY (ticker, holding_ticker, as_of_date)
        )
    """,
    TABLE_PORTFOLIO: f"""
        CREATE TABLE IF NOT EXISTS {TABLE_PORTFOLIO} (
            ticker TEXT NOT NULL,
            pe_ratio REAL,
            pb_ratio REAL,
            dividend_yield REAL,
            weighted_avg_market_cap REAL,
            number_of_holdings INTEGER,
            expense_ratio REAL,
            tracking_difference REAL,
            median_tracking_difference REAL,
            as_of_date TEXT,
            fetched_at TEXT NOT NULL,
            PRIMARY KEY (ticker)
        )
    """,
    TABLE_ALLOCATIONS: f"""
        CREATE TABLE IF NOT EXISTS {TABLE_ALLOCATIONS} (
            ticker TEXT NOT NULL,
            allocation_type TEXT NOT NULL,
            name TEXT NOT NULL,
            as_of_date TEXT NOT NULL,
            weight REAL,
            market_value REAL,
            count INTEGER,
            fetched_at TEXT NOT NULL,
            PRIMARY KEY (ticker, allocation_type, name, as_of_date)
        )
    """,
    TABLE_TRADABILITY: f"""
        CREATE TABLE IF NOT EXISTS {TABLE_TRADABILITY} (
            ticker TEXT NOT NULL,
            avg_daily_volume REAL,
            avg_daily_dollar_volume REAL,
            median_bid_ask_spread REAL,
            avg_bid_ask_spread REAL,
            creation_unit_size INTEGER,
            open_interest REAL,
            short_interest REAL,
            implied_liquidity REAL,
            block_liquidity REAL,
            as_of_date TEXT,
            fetched_at TEXT NOT NULL,
            PRIMARY KEY (ticker)
        )
    """,
    TABLE_STRUCTURE: f"""
        CREATE TABLE IF NOT EXISTS {TABLE_STRUCTURE} (
            ticker TEXT NOT NULL,
            legal_structure TEXT,
            fund_type TEXT,
            index_tracked TEXT,
            replication_method TEXT,
            uses_derivatives INTEGER,
            securities_lending INTEGER,
            tax_form TEXT,
            as_of_date TEXT,
            fetched_at TEXT NOT NULL,
            PRIMARY KEY (ticker)
        )
    """,
    TABLE_PERFORMANCE: f"""
        CREATE TABLE IF NOT EXISTS {TABLE_PERFORMANCE} (
            ticker TEXT NOT NULL,
            return_1m REAL,
            return_3m REAL,
            return_ytd REAL,
            return_1y REAL,
            return_3y REAL,
            return_5y REAL,
            return_10y REAL,
            r_squared REAL,
            beta REAL,
            standard_deviation REAL,
            as_of_date TEXT,
            fetched_at TEXT NOT NULL,
            PRIMARY KEY (ticker)
        )
    """,
    TABLE_QUOTES: f"""
        CREATE TABLE IF NOT EXISTS {TABLE_QUOTES} (
            ticker TEXT NOT NULL,
            quote_date TEXT NOT NULL,
            open REAL,
            high REAL,
            low REAL,
            close REAL,
            volume REAL,
            bid REAL,
            ask REAL,
            bid_size REAL,
            ask_size REAL,
            fetched_at TEXT NOT NULL,
            PRIMARY KEY (ticker, quote_date)
        )
    """,
}

# Valid table names whitelist for SQL injection prevention
_VALID_TABLE_NAMES: frozenset[str] = frozenset(_TABLE_DDL.keys())


# ============================================================================
# ETFComStorage class
# ============================================================================


class ETFComStorage:
    """SQLite storage layer for ETF.com market data.

    Manages 9 SQLite tables and provides ``ensure_tables()`` for schema
    creation. Uses ``CREATE TABLE IF NOT EXISTS`` for idempotent DDL
    and ``INSERT OR REPLACE`` for idempotent writes.

    Parameters
    ----------
    db_path : Path | None
        Path to the SQLite database file. When ``None``, the path is
        resolved via ``_resolve_db_path()``.

    Examples
    --------
    >>> from pathlib import Path
    >>> storage = ETFComStorage(db_path=Path("/tmp/etfcom_test.db"))
    >>> tables = storage.get_table_names()
    >>> len(tables)
    9
    """

    def __init__(self, db_path: Path | None = None) -> None:
        """Initialize storage and create all 9 tables.

        Calls ``ensure_tables()`` automatically on initialization.
        """
        path = db_path or _resolve_db_path()
        self._client = SQLiteClient(path)
        logger.debug("ETFComStorage initialized", db_path=str(path))
        self.ensure_tables()

    # ------------------------------------------------------------------
    # Schema management
    # ------------------------------------------------------------------

    def ensure_tables(self) -> None:
        """Create all 9 tables if they do not already exist.

        Executes ``CREATE TABLE IF NOT EXISTS`` for each table defined
        in the ETF.com schema. Safe to call multiple times.
        """
        logger.debug("Ensuring ETF.com tables exist")
        for table_name, ddl in _TABLE_DDL.items():
            self._client.execute(ddl)
            logger.debug("Table ensured", table_name=table_name)
        logger.info(
            "All ETF.com tables ensured",
            table_count=len(_TABLE_DDL),
        )

    # ------------------------------------------------------------------
    # Introspection / utility
    # ------------------------------------------------------------------

    def get_table_names(self) -> list[str]:
        """Get the list of managed ETF.com table names.

        Returns
        -------
        list[str]
            Sorted list of the 9 table names managed by this storage.
        """
        return sorted(_VALID_TABLE_NAMES)

    def get_row_count(self, table_name: str) -> int:
        """Get the row count for a specific table.

        Parameters
        ----------
        table_name : str
            Name of the table to count. Must be in ``_VALID_TABLE_NAMES``.

        Returns
        -------
        int
            Number of rows in the table.

        Raises
        ------
        ValueError
            If ``table_name`` is not in the allowed table list.
        """
        if table_name not in _VALID_TABLE_NAMES:
            msg = f"Invalid table name: '{table_name}'. Must be one of: {sorted(_VALID_TABLE_NAMES)}"
            raise ValueError(msg)
        rows = self._client.execute(
            f"SELECT COUNT(*) AS cnt FROM {table_name}"  # nosec B608
        )
        return rows[0]["cnt"]

    def get_stats(self) -> dict[str, int]:
        """Get row counts for all 9 tables.

        Returns
        -------
        dict[str, int]
            Dictionary mapping table name to row count.
        """
        logger.debug("Getting table statistics")
        tables = sorted(_VALID_TABLE_NAMES)
        # AIDEV-NOTE: tables は sorted(_VALID_TABLE_NAMES) 由来のため安全。
        union_sql = " UNION ALL ".join(
            f"SELECT '{tbl}' AS tbl, COUNT(*) AS cnt FROM {tbl}"  # nosec B608
            for tbl in tables
        )
        rows = self._client.execute(union_sql)
        stats = {row["tbl"]: row["cnt"] for row in rows}
        logger.info("Table statistics retrieved", stats=stats)
        return stats

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _upsert_records(
        self,
        table_name: str,
        records: list[Any],
        label: str,
    ) -> int:
        """Upsert a list of dataclass records into the given table.

        Parameters
        ----------
        table_name : str
            Target table name (must be in ``_VALID_TABLE_NAMES``).
        records : list[Any]
            List of frozen dataclass records.
        label : str
            Human-readable label for log messages.

        Returns
        -------
        int
            Number of records upserted.
        """
        if not records:
            return 0
        field_names = tuple(f.name for f in dataclasses.fields(records[0]))
        sql = _build_insert_sql(table_name, field_names)
        data = [_dataclass_to_tuple(r) for r in records]
        self._client.execute_many(sql, data)
        logger.info(
            "Records upserted", table=table_name, label=label, count=len(records)
        )
        return len(records)

    # ------------------------------------------------------------------
    # Upsert methods
    # ------------------------------------------------------------------

    def upsert_tickers(self, records: list[TickerRecord]) -> int:
        """Upsert ETF ticker records.

        Parameters
        ----------
        records : list[TickerRecord]
            List of ticker records to upsert.

        Returns
        -------
        int
            Number of rows affected.
        """
        return self._upsert_records(TABLE_TICKERS, records, "Tickers")

    def upsert_fund_flows(self, records: list[FundFlowsRecord]) -> int:
        """Upsert daily fund flow records.

        Parameters
        ----------
        records : list[FundFlowsRecord]
            List of fund flow records to upsert.

        Returns
        -------
        int
            Number of rows affected.
        """
        return self._upsert_records(TABLE_FUND_FLOWS, records, "Fund flows")

    def upsert_holdings(self, records: list[HoldingRecord]) -> int:
        """Upsert top holding records.

        Parameters
        ----------
        records : list[HoldingRecord]
            List of holding records to upsert.

        Returns
        -------
        int
            Number of rows affected.
        """
        return self._upsert_records(TABLE_HOLDINGS, records, "Holdings")

    def upsert_portfolio(self, records: list[PortfolioRecord]) -> int:
        """Upsert portfolio characteristic records.

        Parameters
        ----------
        records : list[PortfolioRecord]
            List of portfolio records to upsert.

        Returns
        -------
        int
            Number of rows affected.
        """
        return self._upsert_records(TABLE_PORTFOLIO, records, "Portfolio")

    def upsert_allocations(self, records: list[AllocationRecord]) -> int:
        """Upsert allocation breakdown records.

        Parameters
        ----------
        records : list[AllocationRecord]
            List of allocation records to upsert.

        Returns
        -------
        int
            Number of rows affected.
        """
        return self._upsert_records(TABLE_ALLOCATIONS, records, "Allocations")

    def upsert_tradability(self, records: list[TradabilityRecord]) -> int:
        """Upsert tradability metric records.

        Parameters
        ----------
        records : list[TradabilityRecord]
            List of tradability records to upsert.

        Returns
        -------
        int
            Number of rows affected.
        """
        return self._upsert_records(TABLE_TRADABILITY, records, "Tradability")

    def upsert_structure(self, records: list[StructureRecord]) -> int:
        """Upsert fund structure records.

        Parameters
        ----------
        records : list[StructureRecord]
            List of structure records to upsert.

        Returns
        -------
        int
            Number of rows affected.
        """
        return self._upsert_records(TABLE_STRUCTURE, records, "Structure")

    def upsert_performance(self, records: list[PerformanceRecord]) -> int:
        """Upsert performance statistic records.

        Parameters
        ----------
        records : list[PerformanceRecord]
            List of performance records to upsert.

        Returns
        -------
        int
            Number of rows affected.
        """
        return self._upsert_records(TABLE_PERFORMANCE, records, "Performance")

    def upsert_quotes(self, records: list[QuoteRecord]) -> int:
        """Upsert delayed quote records.

        Parameters
        ----------
        records : list[QuoteRecord]
            List of quote records to upsert.

        Returns
        -------
        int
            Number of rows affected.
        """
        return self._upsert_records(TABLE_QUOTES, records, "Quotes")

    # ------------------------------------------------------------------
    # Get methods
    # ------------------------------------------------------------------

    def get_tickers(self) -> pd.DataFrame:
        """Get all ticker records.

        Returns
        -------
        pd.DataFrame
            All ticker records. Returns an empty DataFrame if no data exists.
        """
        logger.debug("Getting all tickers")
        sql = f"SELECT * FROM {TABLE_TICKERS} ORDER BY ticker"  # nosec B608
        with self._client.connection() as conn:
            df = pd.read_sql_query(sql, conn)
        logger.info("Tickers retrieved", count=len(df))
        return df

    def get_fund_flows(
        self,
        ticker: str,
        start_date: str | None = None,
        end_date: str | None = None,
    ) -> pd.DataFrame:
        """Get fund flow data for a ticker.

        Parameters
        ----------
        ticker : str
            ETF ticker symbol to filter by.
        start_date : str | None
            If provided, return only rows where ``nav_date >= start_date``.
        end_date : str | None
            If provided, return only rows where ``nav_date <= end_date``.

        Returns
        -------
        pd.DataFrame
            Fund flow data. Returns an empty DataFrame if no data matches.
        """
        logger.debug(
            "Getting fund flows",
            ticker=ticker,
            start_date=start_date,
            end_date=end_date,
        )
        sql = f"SELECT * FROM {TABLE_FUND_FLOWS} WHERE ticker = ?"  # nosec B608
        params: list[Any] = [ticker]
        if start_date is not None:
            sql += " AND nav_date >= ?"
            params.append(start_date)
        if end_date is not None:
            sql += " AND nav_date <= ?"
            params.append(end_date)
        sql += " ORDER BY nav_date"
        with self._client.connection() as conn:
            df = pd.read_sql_query(sql, conn, params=params)
        logger.info("Fund flows retrieved", count=len(df))
        return df

    def get_holdings(
        self,
        ticker: str,
        as_of_date: str | None = None,
    ) -> pd.DataFrame:
        """Get holding data for a ticker.

        Parameters
        ----------
        ticker : str
            ETF ticker symbol to filter by.
        as_of_date : str | None
            If provided, filter by specific as-of date.

        Returns
        -------
        pd.DataFrame
            Holding data. Returns an empty DataFrame if no data matches.
        """
        logger.debug("Getting holdings", ticker=ticker, as_of_date=as_of_date)
        sql = f"SELECT * FROM {TABLE_HOLDINGS} WHERE ticker = ?"  # nosec B608
        params: list[Any] = [ticker]
        if as_of_date is not None:
            sql += " AND as_of_date = ?"
            params.append(as_of_date)
        sql += " ORDER BY weight DESC"
        with self._client.connection() as conn:
            df = pd.read_sql_query(sql, conn, params=params)
        logger.info("Holdings retrieved", count=len(df))
        return df

    def get_portfolio(self, ticker: str) -> pd.DataFrame:
        """Get portfolio characteristics for a ticker.

        Parameters
        ----------
        ticker : str
            ETF ticker symbol to filter by.

        Returns
        -------
        pd.DataFrame
            Portfolio data. Returns an empty DataFrame if no data matches.
        """
        logger.debug("Getting portfolio", ticker=ticker)
        sql = f"SELECT * FROM {TABLE_PORTFOLIO} WHERE ticker = ?"  # nosec B608
        with self._client.connection() as conn:
            df = pd.read_sql_query(sql, conn, params=[ticker])
        logger.info("Portfolio retrieved", count=len(df))
        return df

    def get_allocations(
        self,
        ticker: str,
        allocation_type: str | None = None,
    ) -> pd.DataFrame:
        """Get allocation breakdown data for a ticker.

        Parameters
        ----------
        ticker : str
            ETF ticker symbol to filter by.
        allocation_type : str | None
            If provided, filter by allocation type (e.g. ``"sector"``).

        Returns
        -------
        pd.DataFrame
            Allocation data. Returns an empty DataFrame if no data matches.
        """
        logger.debug(
            "Getting allocations",
            ticker=ticker,
            allocation_type=allocation_type,
        )
        sql = f"SELECT * FROM {TABLE_ALLOCATIONS} WHERE ticker = ?"  # nosec B608
        params: list[Any] = [ticker]
        if allocation_type is not None:
            sql += " AND allocation_type = ?"
            params.append(allocation_type)
        sql += " ORDER BY weight DESC"
        with self._client.connection() as conn:
            df = pd.read_sql_query(sql, conn, params=params)
        logger.info("Allocations retrieved", count=len(df))
        return df

    def get_tradability(self, ticker: str) -> pd.DataFrame:
        """Get tradability metrics for a ticker.

        Parameters
        ----------
        ticker : str
            ETF ticker symbol to filter by.

        Returns
        -------
        pd.DataFrame
            Tradability data. Returns an empty DataFrame if no data matches.
        """
        logger.debug("Getting tradability", ticker=ticker)
        sql = f"SELECT * FROM {TABLE_TRADABILITY} WHERE ticker = ?"  # nosec B608
        with self._client.connection() as conn:
            df = pd.read_sql_query(sql, conn, params=[ticker])
        logger.info("Tradability retrieved", count=len(df))
        return df

    def get_structure(self, ticker: str) -> pd.DataFrame:
        """Get fund structure data for a ticker.

        Parameters
        ----------
        ticker : str
            ETF ticker symbol to filter by.

        Returns
        -------
        pd.DataFrame
            Structure data. Returns an empty DataFrame if no data matches.
        """
        logger.debug("Getting structure", ticker=ticker)
        sql = f"SELECT * FROM {TABLE_STRUCTURE} WHERE ticker = ?"  # nosec B608
        with self._client.connection() as conn:
            df = pd.read_sql_query(sql, conn, params=[ticker])
        logger.info("Structure retrieved", count=len(df))
        return df

    def get_performance(self, ticker: str) -> pd.DataFrame:
        """Get performance data for a ticker.

        Parameters
        ----------
        ticker : str
            ETF ticker symbol to filter by.

        Returns
        -------
        pd.DataFrame
            Performance data. Returns an empty DataFrame if no data matches.
        """
        logger.debug("Getting performance", ticker=ticker)
        sql = f"SELECT * FROM {TABLE_PERFORMANCE} WHERE ticker = ?"  # nosec B608
        with self._client.connection() as conn:
            df = pd.read_sql_query(sql, conn, params=[ticker])
        logger.info("Performance retrieved", count=len(df))
        return df

    def get_quotes(
        self,
        ticker: str,
        start_date: str | None = None,
        end_date: str | None = None,
    ) -> pd.DataFrame:
        """Get quote data for a ticker.

        Parameters
        ----------
        ticker : str
            ETF ticker symbol to filter by.
        start_date : str | None
            If provided, return only rows where ``quote_date >= start_date``.
        end_date : str | None
            If provided, return only rows where ``quote_date <= end_date``.

        Returns
        -------
        pd.DataFrame
            Quote data. Returns an empty DataFrame if no data matches.
        """
        logger.debug(
            "Getting quotes",
            ticker=ticker,
            start_date=start_date,
            end_date=end_date,
        )
        sql = f"SELECT * FROM {TABLE_QUOTES} WHERE ticker = ?"  # nosec B608
        params: list[Any] = [ticker]
        if start_date is not None:
            sql += " AND quote_date >= ?"
            params.append(start_date)
        if end_date is not None:
            sql += " AND quote_date <= ?"
            params.append(end_date)
        sql += " ORDER BY quote_date"
        with self._client.connection() as conn:
            df = pd.read_sql_query(sql, conn, params=params)
        logger.info("Quotes retrieved", count=len(df))
        return df


# ============================================================================
# DB path resolution
# ============================================================================


def _resolve_db_path() -> Path:
    """Resolve the ETF.com SQLite database path.

    Resolution priority:

    1. ``ETFCOM_DB_PATH`` environment variable (if set and non-empty)
    2. Default path via ``get_db_path("sqlite", "etfcom")``

    Returns
    -------
    Path
        Resolved path to the SQLite database file.
    """
    env_path = os.environ.get(ETFCOM_DB_PATH_ENV, "")
    if env_path:
        return Path(env_path)
    return get_db_path("sqlite", DEFAULT_DB_NAME)


# ============================================================================
# Factory function
# ============================================================================


def get_etfcom_storage(
    db_path: Path | None = None,
) -> ETFComStorage:
    """Create an ``ETFComStorage`` instance.

    The database path is resolved by ``_resolve_db_path()`` which checks
    the ``ETFCOM_DB_PATH`` environment variable first, then falls
    back to the default ``data/sqlite/etfcom.db`` location.

    ``lru_cache`` is intentionally not used to avoid global state sharing
    in test environments. Follows the ``get_alphavantage_storage()`` pattern.

    Parameters
    ----------
    db_path : Path | None
        Optional explicit database path. When ``None``, uses the resolved
        default path.

    Returns
    -------
    ETFComStorage
        A configured storage instance with all 9 tables ensured.

    Examples
    --------
    >>> storage = get_etfcom_storage()
    >>> TABLE_TICKERS in storage.get_table_names()
    True
    """
    logger.info("Creating ETFComStorage", db_path=str(db_path))
    return ETFComStorage(db_path=db_path)
