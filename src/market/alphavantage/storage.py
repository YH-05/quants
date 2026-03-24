"""SQLite storage layer for Alpha Vantage market data.

This module provides the ``AlphaVantageStorage`` class that manages 8 SQLite
tables for persisting Alpha Vantage API data. It uses the existing
``SQLiteClient`` from ``database.db`` for all database operations,
leveraging ``INSERT OR REPLACE`` for idempotent data updates.

Tables managed
--------------
- ``av_daily_prices`` -- Daily OHLCV price data
  (PK: ``symbol``, ``date``)
- ``av_company_overview`` -- Company profile and fundamentals
  (PK: ``symbol``)
- ``av_income_statements`` -- Income statement data
  (PK: ``symbol``, ``fiscal_date_ending``, ``report_type``)
- ``av_balance_sheets`` -- Balance sheet data
  (PK: ``symbol``, ``fiscal_date_ending``, ``report_type``)
- ``av_cash_flows`` -- Cash flow statement data
  (PK: ``symbol``, ``fiscal_date_ending``, ``report_type``)
- ``av_earnings`` -- Earnings data
  (PK: ``symbol``, ``fiscal_date_ending``, ``period_type``)
- ``av_economic_indicators`` -- Macroeconomic indicator time-series
  (PK: ``indicator``, ``date``, ``interval``, ``maturity``)
- ``av_forex_daily`` -- Daily forex exchange rate data
  (PK: ``from_currency``, ``to_currency``, ``date``)

Examples
--------
>>> from market.alphavantage.storage import get_alphavantage_storage
>>> storage = get_alphavantage_storage()
>>> tables = storage.get_table_names()
>>> len(tables)
8

See Also
--------
database.db.sqlite_client.SQLiteClient : Underlying SQLite client.
market.polymarket.storage : Reference implementation (DDL dict + ensure_tables).
market.edinet.storage : Reference implementation (_migrate_add_missing_columns).
market.alphavantage.storage_constants : Table name constants.
market.alphavantage.models : Storage record dataclasses.
"""

from __future__ import annotations

import dataclasses
import math
import os
import re
from functools import lru_cache
from pathlib import Path
from typing import TYPE_CHECKING, Any

import pandas as pd

from database.db.connection import get_db_path
from database.db.sqlite_client import SQLiteClient
from market.alphavantage.storage_constants import (
    AV_DB_PATH_ENV,
    DEFAULT_DB_NAME,
    TABLE_BALANCE_SHEETS,
    TABLE_CASH_FLOWS,
    TABLE_COMPANY_OVERVIEW,
    TABLE_DAILY_PRICES,
    TABLE_EARNINGS,
    TABLE_ECONOMIC_INDICATORS,
    TABLE_FOREX_DAILY,
    TABLE_INCOME_STATEMENTS,
)
from utils_core.logging import get_logger

if TYPE_CHECKING:
    from market.alphavantage.models import (
        AnnualEarningsRecord,
        BalanceSheetRecord,
        CashFlowRecord,
        CompanyOverviewRecord,
        DailyPriceRecord,
        EarningsRecord,
        EconomicIndicatorRecord,
        ForexDailyRecord,
        IncomeStatementRecord,
        QuarterlyEarningsRecord,
    )

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
    TABLE_DAILY_PRICES: f"""
        CREATE TABLE IF NOT EXISTS {TABLE_DAILY_PRICES} (
            symbol TEXT NOT NULL,
            date TEXT NOT NULL,
            open REAL NOT NULL,
            high REAL NOT NULL,
            low REAL NOT NULL,
            close REAL NOT NULL,
            adjusted_close REAL,
            volume INTEGER NOT NULL,
            fetched_at TEXT NOT NULL,
            PRIMARY KEY (symbol, date)
        )
    """,
    TABLE_COMPANY_OVERVIEW: f"""
        CREATE TABLE IF NOT EXISTS {TABLE_COMPANY_OVERVIEW} (
            symbol TEXT NOT NULL,
            name TEXT,
            description TEXT,
            exchange TEXT,
            currency TEXT,
            country TEXT,
            sector TEXT,
            industry TEXT,
            fiscal_year_end TEXT,
            latest_quarter TEXT,
            market_capitalization REAL,
            ebitda REAL,
            pe_ratio REAL,
            peg_ratio REAL,
            book_value REAL,
            dividend_per_share REAL,
            dividend_yield REAL,
            eps REAL,
            diluted_eps_ttm REAL,
            week_52_high REAL,
            week_52_low REAL,
            day_50_moving_average REAL,
            day_200_moving_average REAL,
            shares_outstanding REAL,
            revenue_per_share_ttm REAL,
            profit_margin REAL,
            operating_margin_ttm REAL,
            return_on_assets_ttm REAL,
            return_on_equity_ttm REAL,
            revenue_ttm REAL,
            gross_profit_ttm REAL,
            quarterly_earnings_growth_yoy REAL,
            quarterly_revenue_growth_yoy REAL,
            analyst_target_price REAL,
            analyst_rating_strong_buy REAL,
            analyst_rating_buy REAL,
            analyst_rating_hold REAL,
            analyst_rating_sell REAL,
            analyst_rating_strong_sell REAL,
            trailing_pe REAL,
            forward_pe REAL,
            price_to_sales_ratio_ttm REAL,
            price_to_book_ratio REAL,
            ev_to_revenue REAL,
            ev_to_ebitda REAL,
            beta REAL,
            fetched_at TEXT NOT NULL,
            PRIMARY KEY (symbol)
        )
    """,
    TABLE_INCOME_STATEMENTS: f"""
        CREATE TABLE IF NOT EXISTS {TABLE_INCOME_STATEMENTS} (
            symbol TEXT NOT NULL,
            fiscal_date_ending TEXT NOT NULL,
            report_type TEXT NOT NULL,
            reported_currency TEXT,
            gross_profit REAL,
            total_revenue REAL,
            cost_of_revenue REAL,
            cost_of_goods_and_services_sold REAL,
            operating_income REAL,
            selling_general_and_administrative REAL,
            research_and_development REAL,
            operating_expenses REAL,
            net_income REAL,
            interest_income REAL,
            interest_expense REAL,
            income_before_tax REAL,
            income_tax_expense REAL,
            ebit REAL,
            ebitda REAL,
            depreciation_and_amortization REAL,
            fetched_at TEXT NOT NULL,
            PRIMARY KEY (symbol, fiscal_date_ending, report_type)
        )
    """,
    TABLE_BALANCE_SHEETS: f"""
        CREATE TABLE IF NOT EXISTS {TABLE_BALANCE_SHEETS} (
            symbol TEXT NOT NULL,
            fiscal_date_ending TEXT NOT NULL,
            report_type TEXT NOT NULL,
            reported_currency TEXT,
            total_assets REAL,
            total_current_assets REAL,
            cash_and_equivalents REAL,
            cash_and_short_term_investments REAL,
            inventory REAL,
            current_net_receivables REAL,
            total_non_current_assets REAL,
            property_plant_equipment REAL,
            intangible_assets REAL,
            goodwill REAL,
            investments REAL,
            long_term_investments REAL,
            short_term_investments REAL,
            total_liabilities REAL,
            total_current_liabilities REAL,
            current_long_term_debt REAL,
            short_term_debt REAL,
            current_accounts_payable REAL,
            total_non_current_liabilities REAL,
            long_term_debt REAL,
            total_shareholder_equity REAL,
            retained_earnings REAL,
            common_stock REAL,
            common_stock_shares_outstanding REAL,
            fetched_at TEXT NOT NULL,
            PRIMARY KEY (symbol, fiscal_date_ending, report_type)
        )
    """,
    TABLE_CASH_FLOWS: f"""
        CREATE TABLE IF NOT EXISTS {TABLE_CASH_FLOWS} (
            symbol TEXT NOT NULL,
            fiscal_date_ending TEXT NOT NULL,
            report_type TEXT NOT NULL,
            reported_currency TEXT,
            operating_cashflow REAL,
            payments_for_operating_activities REAL,
            change_in_operating_liabilities REAL,
            change_in_operating_assets REAL,
            depreciation_depletion_and_amortization REAL,
            capital_expenditures REAL,
            change_in_receivables REAL,
            change_in_inventory REAL,
            profit_loss REAL,
            cashflow_from_investment REAL,
            cashflow_from_financing REAL,
            dividend_payout REAL,
            proceeds_from_repurchase_of_equity REAL,
            proceeds_from_issuance_of_long_term_debt REAL,
            payments_for_repurchase_of_common_stock REAL,
            change_in_cash_and_equivalents REAL,
            net_income REAL,
            fetched_at TEXT NOT NULL,
            PRIMARY KEY (symbol, fiscal_date_ending, report_type)
        )
    """,
    TABLE_EARNINGS: f"""
        CREATE TABLE IF NOT EXISTS {TABLE_EARNINGS} (
            symbol TEXT NOT NULL,
            fiscal_date_ending TEXT NOT NULL,
            period_type TEXT NOT NULL,
            reported_date TEXT,
            reported_eps REAL,
            estimated_eps REAL,
            surprise REAL,
            surprise_percentage REAL,
            fetched_at TEXT NOT NULL,
            PRIMARY KEY (symbol, fiscal_date_ending, period_type)
        )
    """,
    TABLE_ECONOMIC_INDICATORS: f"""
        CREATE TABLE IF NOT EXISTS {TABLE_ECONOMIC_INDICATORS} (
            indicator TEXT NOT NULL,
            date TEXT NOT NULL,
            value REAL,
            interval TEXT NOT NULL DEFAULT '',
            maturity TEXT NOT NULL DEFAULT '',
            fetched_at TEXT NOT NULL,
            PRIMARY KEY (indicator, date, interval, maturity)
        )
    """,
    TABLE_FOREX_DAILY: f"""
        CREATE TABLE IF NOT EXISTS {TABLE_FOREX_DAILY} (
            from_currency TEXT NOT NULL,
            to_currency TEXT NOT NULL,
            date TEXT NOT NULL,
            open REAL NOT NULL,
            high REAL NOT NULL,
            low REAL NOT NULL,
            close REAL NOT NULL,
            fetched_at TEXT NOT NULL,
            PRIMARY KEY (from_currency, to_currency, date)
        )
    """,
}

# Valid table names whitelist for SQL injection prevention
_VALID_TABLE_NAMES: frozenset[str] = frozenset(_TABLE_DDL.keys())


# ============================================================================
# DDL parsing helper
# ============================================================================

# Regex to extract column definitions: "column_name TYPE [NOT NULL]"
_DDL_COLUMN_RE = re.compile(
    r"^\s+(\w+)\s+(TEXT|INTEGER|REAL|BLOB|NUMERIC)",
    re.MULTILINE,
)


def _parse_ddl_columns(ddl: str) -> set[str]:
    """Extract column names from a CREATE TABLE DDL statement.

    Parameters
    ----------
    ddl : str
        SQL CREATE TABLE statement to parse.

    Returns
    -------
    set[str]
        Set of column names found in the DDL.

    Examples
    --------
    >>> ddl = "CREATE TABLE t (id INTEGER, name TEXT)"
    >>> sorted(_parse_ddl_columns(ddl))
    ['id', 'name']
    """
    return {m.group(1) for m in _DDL_COLUMN_RE.finditer(ddl)}


# Pre-computed expected column sets from DDL (avoids re-parsing on each call)
_TABLE_EXPECTED_COLUMNS: dict[str, set[str]] = {
    name: _parse_ddl_columns(ddl) for name, ddl in _TABLE_DDL.items()
}


# ============================================================================
# AlphaVantageStorage class
# ============================================================================


class AlphaVantageStorage:
    """SQLite storage layer for Alpha Vantage market data.

    Manages 8 SQLite tables and provides ``ensure_tables()`` for schema
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
    >>> storage = AlphaVantageStorage(db_path=Path("/tmp/av_test.db"))
    >>> tables = storage.get_table_names()
    >>> len(tables)
    8
    """

    def __init__(self, db_path: Path | None = None) -> None:
        """Initialize storage and create all 8 tables.

        Calls ``ensure_tables()`` automatically on initialization.
        """
        path = db_path or _resolve_db_path()
        self._client = SQLiteClient(path)
        logger.debug("AlphaVantageStorage initialized", db_path=str(path))
        self.ensure_tables()

    # ------------------------------------------------------------------
    # Schema management
    # ------------------------------------------------------------------

    def ensure_tables(self) -> None:
        """Create all 8 tables if they do not already exist.

        Executes ``CREATE TABLE IF NOT EXISTS`` for each table defined
        in the Alpha Vantage schema. After creating tables, runs a
        lightweight migration to add any missing columns.
        Safe to call multiple times.
        """
        logger.debug("Ensuring Alpha Vantage tables exist")
        for table_name, ddl in _TABLE_DDL.items():
            self._client.execute(ddl)
            logger.debug("Table ensured", table_name=table_name)
        logger.info(
            "All Alpha Vantage tables ensured",
            table_count=len(_TABLE_DDL),
        )
        self._migrate_add_missing_columns()

    # ------------------------------------------------------------------
    # Schema migration helpers
    # ------------------------------------------------------------------

    def _table_exists(self, table_name: str) -> bool:
        """Check whether a table exists in the database.

        Parameters
        ----------
        table_name : str
            Name of the table to check.

        Returns
        -------
        bool
            ``True`` if the table exists, ``False`` otherwise.
        """
        tables = self._client.get_tables()
        return table_name in tables

    def _get_column_info(self, table_name: str) -> dict[str, str]:
        """Get column names and types for an existing table.

        Uses ``PRAGMA table_info()`` to inspect the table schema.

        Parameters
        ----------
        table_name : str
            Name of the table to inspect. Must be in ``_VALID_TABLE_NAMES``.

        Returns
        -------
        dict[str, str]
            Mapping of column name to column type string.

        Raises
        ------
        ValueError
            If ``table_name`` is not in the allowed table list.
        """
        if table_name not in _VALID_TABLE_NAMES:
            msg = f"Unknown table: {table_name!r}"
            raise ValueError(msg)
        rows = self._client.execute(f"PRAGMA table_info({table_name})")  # nosec B608
        return {row["name"]: row["type"] for row in rows}

    def _migrate_add_missing_columns(self) -> None:
        """Add missing columns to existing tables.

        For each table, compares existing columns against the DDL
        definition. Any missing columns are added via
        ``ALTER TABLE ADD COLUMN``. This is a forward-only migration
        that does not remove or rename columns.
        """
        for table_name in _TABLE_DDL:
            if not self._table_exists(table_name):
                continue
            existing_cols = set(self._get_column_info(table_name).keys())
            expected_cols = _TABLE_EXPECTED_COLUMNS.get(table_name, set())
            missing = expected_cols - existing_cols
            if not missing:
                continue

            ddl = _TABLE_DDL[table_name]
            ddl_types = {m.group(1): m.group(2) for m in _DDL_COLUMN_RE.finditer(ddl)}
            for col_name in sorted(missing):
                col_type = ddl_types.get(col_name, "TEXT")
                alter_sql = f"ALTER TABLE {table_name} ADD COLUMN {col_name} {col_type}"  # nosec B608
                self._client.execute(alter_sql)
                logger.info(
                    "Added missing column",
                    table_name=table_name,
                    column=col_name,
                    column_type=col_type,
                )

    # ------------------------------------------------------------------
    # Introspection / utility
    # ------------------------------------------------------------------

    def get_table_names(self) -> list[str]:
        """Get the list of managed Alpha Vantage table names.

        Returns
        -------
        list[str]
            Sorted list of the 8 table names managed by this storage.
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

    # ------------------------------------------------------------------
    # Upsert methods
    # ------------------------------------------------------------------

    def upsert_daily_prices(self, records: list[DailyPriceRecord]) -> int:
        """Upsert daily OHLCV price records.

        Parameters
        ----------
        records : list[DailyPriceRecord]
            List of daily price records to upsert.

        Returns
        -------
        int
            Number of rows affected.
        """
        if not records:
            logger.debug("No daily price records to upsert, skipping")
            return 0

        field_names = tuple(f.name for f in dataclasses.fields(records[0]))
        sql = _build_insert_sql(TABLE_DAILY_PRICES, field_names)

        params = [_dataclass_to_tuple(r) for r in records]
        self._client.execute_many(sql, params)
        logger.info("Daily prices upserted", count=len(records))
        return len(records)

    def upsert_company_overview(self, record: CompanyOverviewRecord) -> int:
        """Upsert a single company overview record.

        Parameters
        ----------
        record : CompanyOverviewRecord
            Company overview record to upsert.

        Returns
        -------
        int
            Number of rows affected (always 1).
        """
        field_names = tuple(f.name for f in dataclasses.fields(record))
        sql = _build_insert_sql(TABLE_COMPANY_OVERVIEW, field_names)

        params = _dataclass_to_tuple(record)
        self._client.execute(sql, params)
        logger.info("Company overview upserted", symbol=record.symbol)
        return 1

    def upsert_income_statements(self, records: list[IncomeStatementRecord]) -> int:
        """Upsert income statement records.

        Parameters
        ----------
        records : list[IncomeStatementRecord]
            List of income statement records to upsert.

        Returns
        -------
        int
            Number of rows affected.
        """
        if not records:
            logger.debug("No income statement records to upsert, skipping")
            return 0

        field_names = tuple(f.name for f in dataclasses.fields(records[0]))
        sql = _build_insert_sql(TABLE_INCOME_STATEMENTS, field_names)

        params = [_dataclass_to_tuple(r) for r in records]
        self._client.execute_many(sql, params)
        logger.info("Income statements upserted", count=len(records))
        return len(records)

    def upsert_balance_sheets(self, records: list[BalanceSheetRecord]) -> int:
        """Upsert balance sheet records.

        Parameters
        ----------
        records : list[BalanceSheetRecord]
            List of balance sheet records to upsert.

        Returns
        -------
        int
            Number of rows affected.
        """
        if not records:
            logger.debug("No balance sheet records to upsert, skipping")
            return 0

        field_names = tuple(f.name for f in dataclasses.fields(records[0]))
        sql = _build_insert_sql(TABLE_BALANCE_SHEETS, field_names)

        params = [_dataclass_to_tuple(r) for r in records]
        self._client.execute_many(sql, params)
        logger.info("Balance sheets upserted", count=len(records))
        return len(records)

    def upsert_cash_flows(self, records: list[CashFlowRecord]) -> int:
        """Upsert cash flow records.

        Parameters
        ----------
        records : list[CashFlowRecord]
            List of cash flow records to upsert.

        Returns
        -------
        int
            Number of rows affected.
        """
        if not records:
            logger.debug("No cash flow records to upsert, skipping")
            return 0

        field_names = tuple(f.name for f in dataclasses.fields(records[0]))
        sql = _build_insert_sql(TABLE_CASH_FLOWS, field_names)

        params = [_dataclass_to_tuple(r) for r in records]
        self._client.execute_many(sql, params)
        logger.info("Cash flows upserted", count=len(records))
        return len(records)

    def upsert_earnings(
        self, records: list[AnnualEarningsRecord | QuarterlyEarningsRecord]
    ) -> int:
        """Upsert earnings records (annual and/or quarterly).

        Accepts a mixed list of ``AnnualEarningsRecord`` and
        ``QuarterlyEarningsRecord``. Each record is normalised to the
        full ``av_earnings`` column set (9 columns) before upsert.
        Annual records will have ``reported_date``, ``estimated_eps``,
        ``surprise``, and ``surprise_percentage`` set to ``None``.

        Parameters
        ----------
        records : list[AnnualEarningsRecord | QuarterlyEarningsRecord]
            List of earnings records to upsert.

        Returns
        -------
        int
            Number of rows affected.
        """
        if not records:
            logger.debug("No earnings records to upsert, skipping")
            return 0

        # Use the full earnings column set (9 columns from DDL)
        columns = (
            "symbol",
            "fiscal_date_ending",
            "period_type",
            "reported_date",
            "reported_eps",
            "estimated_eps",
            "surprise",
            "surprise_percentage",
            "fetched_at",
        )
        sql = _build_insert_sql(TABLE_EARNINGS, columns)

        params: list[tuple[Any, ...]] = []
        for record in records:
            row = (
                record.symbol,
                record.fiscal_date_ending,
                record.period_type,
                getattr(record, "reported_date", None),
                getattr(record, "reported_eps", None),
                getattr(record, "estimated_eps", None),
                getattr(record, "surprise", None),
                getattr(record, "surprise_percentage", None),
                record.fetched_at,
            )
            params.append(row)

        self._client.execute_many(sql, params)
        logger.info("Earnings upserted", count=len(records))
        return len(records)

    def upsert_economic_indicators(self, records: list[EconomicIndicatorRecord]) -> int:
        """Upsert economic indicator records.

        Parameters
        ----------
        records : list[EconomicIndicatorRecord]
            List of economic indicator records to upsert.

        Returns
        -------
        int
            Number of rows affected.
        """
        if not records:
            logger.debug("No economic indicator records to upsert, skipping")
            return 0

        field_names = tuple(f.name for f in dataclasses.fields(records[0]))
        sql = _build_insert_sql(TABLE_ECONOMIC_INDICATORS, field_names)

        params = [_dataclass_to_tuple(r) for r in records]
        self._client.execute_many(sql, params)
        logger.info("Economic indicators upserted", count=len(records))
        return len(records)

    def upsert_forex_daily(self, records: list[ForexDailyRecord]) -> int:
        """Upsert daily forex exchange rate records.

        Parameters
        ----------
        records : list[ForexDailyRecord]
            List of forex daily records to upsert.

        Returns
        -------
        int
            Number of rows affected.
        """
        if not records:
            logger.debug("No forex daily records to upsert, skipping")
            return 0

        field_names = tuple(f.name for f in dataclasses.fields(records[0]))
        sql = _build_insert_sql(TABLE_FOREX_DAILY, field_names)

        params = [_dataclass_to_tuple(r) for r in records]
        self._client.execute_many(sql, params)
        logger.info("Forex daily upserted", count=len(records))
        return len(records)

    # ------------------------------------------------------------------
    # Get methods
    # ------------------------------------------------------------------

    def get_daily_prices(
        self,
        symbol: str,
        start_date: str | None = None,
        end_date: str | None = None,
    ) -> pd.DataFrame:
        """Get daily price data for a symbol.

        Parameters
        ----------
        symbol : str
            Ticker symbol to filter by.
        start_date : str | None
            If provided, return only rows where ``date >= start_date``.
        end_date : str | None
            If provided, return only rows where ``date <= end_date``.

        Returns
        -------
        pd.DataFrame
            Daily price data. Returns an empty DataFrame if no data matches.
        """
        logger.debug(
            "Getting daily prices",
            symbol=symbol,
            start_date=start_date,
            end_date=end_date,
        )
        sql = f"SELECT * FROM {TABLE_DAILY_PRICES} WHERE symbol = ?"  # nosec B608
        params: list[Any] = [symbol]
        if start_date is not None:
            sql += " AND date >= ?"
            params.append(start_date)
        if end_date is not None:
            sql += " AND date <= ?"
            params.append(end_date)
        sql += " ORDER BY date"
        with self._client.connection() as conn:
            df = pd.read_sql_query(sql, conn, params=params)
        logger.info("Daily prices retrieved", count=len(df))
        return df

    def get_company_overview(self, symbol: str) -> CompanyOverviewRecord | None:
        """Get company overview for a symbol.

        Parameters
        ----------
        symbol : str
            Ticker symbol to look up.

        Returns
        -------
        CompanyOverviewRecord | None
            The company overview record, or ``None`` if not found.
        """
        from market.alphavantage.models import CompanyOverviewRecord

        logger.debug("Getting company overview", symbol=symbol)
        sql = f"SELECT * FROM {TABLE_COMPANY_OVERVIEW} WHERE symbol = ?"  # nosec B608
        rows = self._client.execute(sql, (symbol,))
        if not rows:
            logger.debug("Company overview not found", symbol=symbol)
            return None

        row = rows[0]
        # Build kwargs from the row, matching CompanyOverviewRecord fields
        row_keys = set(row.keys())
        fields = {f.name for f in dataclasses.fields(CompanyOverviewRecord)}
        kwargs = {k: row[k] for k in fields if k in row_keys}
        return CompanyOverviewRecord(**kwargs)

    def get_income_statements(
        self,
        symbol: str,
        report_type: str | None = None,
    ) -> pd.DataFrame:
        """Get income statement data for a symbol.

        Parameters
        ----------
        symbol : str
            Ticker symbol to filter by.
        report_type : str | None
            If provided, filter by ``"annual"`` or ``"quarterly"``.

        Returns
        -------
        pd.DataFrame
            Income statement data. Returns an empty DataFrame if no data matches.
        """
        logger.debug(
            "Getting income statements",
            symbol=symbol,
            report_type=report_type,
        )
        sql = f"SELECT * FROM {TABLE_INCOME_STATEMENTS} WHERE symbol = ?"  # nosec B608
        params: list[Any] = [symbol]
        if report_type is not None:
            sql += " AND report_type = ?"
            params.append(report_type)
        sql += " ORDER BY fiscal_date_ending"
        with self._client.connection() as conn:
            df = pd.read_sql_query(sql, conn, params=params)
        logger.info("Income statements retrieved", count=len(df))
        return df

    def get_balance_sheets(
        self,
        symbol: str,
        report_type: str | None = None,
    ) -> pd.DataFrame:
        """Get balance sheet data for a symbol.

        Parameters
        ----------
        symbol : str
            Ticker symbol to filter by.
        report_type : str | None
            If provided, filter by ``"annual"`` or ``"quarterly"``.

        Returns
        -------
        pd.DataFrame
            Balance sheet data. Returns an empty DataFrame if no data matches.
        """
        logger.debug(
            "Getting balance sheets",
            symbol=symbol,
            report_type=report_type,
        )
        sql = f"SELECT * FROM {TABLE_BALANCE_SHEETS} WHERE symbol = ?"  # nosec B608
        params: list[Any] = [symbol]
        if report_type is not None:
            sql += " AND report_type = ?"
            params.append(report_type)
        sql += " ORDER BY fiscal_date_ending"
        with self._client.connection() as conn:
            df = pd.read_sql_query(sql, conn, params=params)
        logger.info("Balance sheets retrieved", count=len(df))
        return df

    def get_cash_flows(
        self,
        symbol: str,
        report_type: str | None = None,
    ) -> pd.DataFrame:
        """Get cash flow data for a symbol.

        Parameters
        ----------
        symbol : str
            Ticker symbol to filter by.
        report_type : str | None
            If provided, filter by ``"annual"`` or ``"quarterly"``.

        Returns
        -------
        pd.DataFrame
            Cash flow data. Returns an empty DataFrame if no data matches.
        """
        logger.debug(
            "Getting cash flows",
            symbol=symbol,
            report_type=report_type,
        )
        sql = f"SELECT * FROM {TABLE_CASH_FLOWS} WHERE symbol = ?"  # nosec B608
        params: list[Any] = [symbol]
        if report_type is not None:
            sql += " AND report_type = ?"
            params.append(report_type)
        sql += " ORDER BY fiscal_date_ending"
        with self._client.connection() as conn:
            df = pd.read_sql_query(sql, conn, params=params)
        logger.info("Cash flows retrieved", count=len(df))
        return df

    def get_earnings(
        self,
        symbol: str,
        period_type: str | None = None,
    ) -> pd.DataFrame:
        """Get earnings data for a symbol.

        Parameters
        ----------
        symbol : str
            Ticker symbol to filter by.
        period_type : str | None
            If provided, filter by ``"annual"`` or ``"quarterly"``.

        Returns
        -------
        pd.DataFrame
            Earnings data. Returns an empty DataFrame if no data matches.
        """
        logger.debug(
            "Getting earnings",
            symbol=symbol,
            period_type=period_type,
        )
        sql = f"SELECT * FROM {TABLE_EARNINGS} WHERE symbol = ?"  # nosec B608
        params: list[Any] = [symbol]
        if period_type is not None:
            sql += " AND period_type = ?"
            params.append(period_type)
        sql += " ORDER BY fiscal_date_ending"
        with self._client.connection() as conn:
            df = pd.read_sql_query(sql, conn, params=params)
        logger.info("Earnings retrieved", count=len(df))
        return df

    def get_economic_indicators(
        self,
        indicator: str,
        interval: str | None = None,
        maturity: str | None = None,
    ) -> pd.DataFrame:
        """Get economic indicator data.

        Parameters
        ----------
        indicator : str
            Indicator name to filter by (e.g. ``"REAL_GDP"``).
        interval : str | None
            If provided, filter by interval (e.g. ``"quarterly"``).
        maturity : str | None
            If provided, filter by maturity (e.g. ``"10year"``).

        Returns
        -------
        pd.DataFrame
            Economic indicator data. Returns an empty DataFrame if no
            data matches.
        """
        logger.debug(
            "Getting economic indicators",
            indicator=indicator,
            interval=interval,
            maturity=maturity,
        )
        sql = f"SELECT * FROM {TABLE_ECONOMIC_INDICATORS} WHERE indicator = ?"  # nosec B608
        params: list[Any] = [indicator]
        if interval is not None:
            sql += " AND interval = ?"
            params.append(interval)
        if maturity is not None:
            sql += " AND maturity = ?"
            params.append(maturity)
        sql += " ORDER BY date"
        with self._client.connection() as conn:
            df = pd.read_sql_query(sql, conn, params=params)
        logger.info("Economic indicators retrieved", count=len(df))
        return df

    def get_forex_daily(
        self,
        from_currency: str,
        to_currency: str,
        start_date: str | None = None,
        end_date: str | None = None,
    ) -> pd.DataFrame:
        """Get daily forex data for a currency pair.

        Parameters
        ----------
        from_currency : str
            Source currency code (e.g. ``"USD"``).
        to_currency : str
            Target currency code (e.g. ``"JPY"``).
        start_date : str | None
            If provided, return only rows where ``date >= start_date``.
        end_date : str | None
            If provided, return only rows where ``date <= end_date``.

        Returns
        -------
        pd.DataFrame
            Forex daily data. Returns an empty DataFrame if no data matches.
        """
        logger.debug(
            "Getting forex daily",
            from_currency=from_currency,
            to_currency=to_currency,
            start_date=start_date,
            end_date=end_date,
        )
        sql = (
            f"SELECT * FROM {TABLE_FOREX_DAILY}"  # nosec B608
            " WHERE from_currency = ? AND to_currency = ?"
        )
        params: list[Any] = [from_currency, to_currency]
        if start_date is not None:
            sql += " AND date >= ?"
            params.append(start_date)
        if end_date is not None:
            sql += " AND date <= ?"
            params.append(end_date)
        sql += " ORDER BY date"
        with self._client.connection() as conn:
            df = pd.read_sql_query(sql, conn, params=params)
        logger.info("Forex daily retrieved", count=len(df))
        return df


# ============================================================================
# Factory function
# ============================================================================


def _resolve_db_path() -> Path:
    """Resolve the Alpha Vantage SQLite database path.

    Resolution priority:

    1. ``ALPHA_VANTAGE_DB_PATH`` environment variable (if set and non-empty)
    2. Default path via ``get_db_path("sqlite", "alphavantage")``

    Returns
    -------
    Path
        Resolved path to the SQLite database file.
    """
    env_path = os.environ.get(AV_DB_PATH_ENV, "")
    if env_path:
        return Path(env_path)
    return get_db_path("sqlite", DEFAULT_DB_NAME)


def get_alphavantage_storage(
    db_path: Path | None = None,
) -> AlphaVantageStorage:
    """Create an ``AlphaVantageStorage`` instance.

    The database path is resolved by ``_resolve_db_path()`` which checks
    the ``ALPHA_VANTAGE_DB_PATH`` environment variable first, then falls
    back to the default ``data/sqlite/alphavantage.db`` location.

    ``lru_cache`` is intentionally not used to avoid global state sharing
    in test environments. Follows the ``get_polymarket_storage()`` pattern.

    Parameters
    ----------
    db_path : Path | None
        Optional explicit database path. When ``None``, uses the resolved
        default path.

    Returns
    -------
    AlphaVantageStorage
        A configured storage instance with all 8 tables ensured.

    Examples
    --------
    >>> storage = get_alphavantage_storage()
    >>> TABLE_DAILY_PRICES in storage.get_table_names()
    True
    """
    logger.info("Creating AlphaVantageStorage", db_path=str(db_path))
    return AlphaVantageStorage(db_path=db_path)


# ============================================================================
# Module exports
# ============================================================================

__all__ = [
    "AlphaVantageStorage",
    "get_alphavantage_storage",
]
