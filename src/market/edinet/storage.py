"""SQLite storage layer for EDINET data.

This module provides the ``EdinetStorage`` class that manages 6 SQLite
tables for persisting EDINET DB API data. It uses the existing
``SQLiteClient`` from ``database.db`` for all database operations,
leveraging ``INSERT OR REPLACE`` for idempotent data updates.

Tables managed
--------------
- ``companies`` -- Company master data (PK: ``edinet_code``)
- ``financials`` -- Annual financial statements (PK: ``edinet_code``, ``fiscal_year``)
- ``ratios`` -- Computed financial ratios (PK: ``edinet_code``, ``fiscal_year``)
- ``text_blocks`` -- Securities report text excerpts (PK: ``edinet_code``, ``fiscal_year``, ``section``)
- ``industries`` -- Industry master data (PK: ``slug``)
- ``industry_details`` -- Detailed industry data (PK: ``slug``)

Examples
--------
>>> from market.edinet.types import EdinetConfig
>>> config = EdinetConfig(api_key="key", db_path=Path("/tmp/edinet.db"))
>>> storage = EdinetStorage(config=config)
>>> storage.upsert_companies([company1, company2])
>>> df = storage.get_company("E00001")

See Also
--------
database.db.sqlite_client.SQLiteClient : Underlying SQLite client.
market.edinet.types : Data record dataclasses.
market.edinet.constants : Table name constants.
"""

from __future__ import annotations

import dataclasses
import re
from typing import TYPE_CHECKING, Any

import pandas as pd

from database.db.sqlite_client import SQLiteClient
from market.edinet.constants import (
    TABLE_COMPANIES,
    TABLE_FINANCIALS,
    TABLE_INDUSTRIES,
    TABLE_INDUSTRY_DETAILS,
    TABLE_RATIOS,
    TABLE_TEXT_BLOCKS,
)
from utils_core.logging import get_logger

if TYPE_CHECKING:
    from market.edinet.types import (
        Company,
        EdinetConfig,
        FinancialRecord,
        Industry,
        RatioRecord,
        TextBlock,
    )

logger = get_logger(__name__)

# ============================================================================
# Table DDL definitions (SQLite types)
# ============================================================================

_TABLE_DDL: dict[str, str] = {
    TABLE_COMPANIES: f"""
        CREATE TABLE IF NOT EXISTS {TABLE_COMPANIES} (
            edinet_code TEXT NOT NULL,
            sec_code TEXT NOT NULL,
            name TEXT NOT NULL,
            industry TEXT NOT NULL,
            name_en TEXT,
            name_ja TEXT,
            accounting_standard TEXT,
            credit_rating TEXT,
            credit_score INTEGER,
            PRIMARY KEY (edinet_code)
        )
    """,
    TABLE_FINANCIALS: f"""
        CREATE TABLE IF NOT EXISTS {TABLE_FINANCIALS} (
            edinet_code TEXT NOT NULL,
            fiscal_year INTEGER NOT NULL,
            revenue REAL,
            operating_income REAL,
            ordinary_income REAL,
            net_income REAL,
            profit_before_tax REAL,
            comprehensive_income REAL,
            total_assets REAL,
            net_assets REAL,
            shareholders_equity REAL,
            cash REAL,
            goodwill REAL,
            cf_operating REAL,
            cf_investing REAL,
            cf_financing REAL,
            eps REAL,
            diluted_eps REAL,
            bps REAL,
            dividend_per_share REAL,
            equity_ratio_official REAL,
            payout_ratio REAL,
            per REAL,
            roe_official REAL,
            num_employees INTEGER,
            capex REAL,
            depreciation REAL,
            rnd_expenses REAL,
            accounting_standard TEXT,
            submit_date TEXT,
            PRIMARY KEY (edinet_code, fiscal_year)
        )
    """,
    TABLE_RATIOS: f"""
        CREATE TABLE IF NOT EXISTS {TABLE_RATIOS} (
            edinet_code TEXT NOT NULL,
            fiscal_year INTEGER NOT NULL,
            roe REAL,
            roa REAL,
            roe_official REAL,
            net_margin REAL,
            equity_ratio REAL,
            equity_ratio_official REAL,
            payout_ratio REAL,
            dividend_per_share REAL,
            adjusted_dividend_per_share REAL,
            dividend_yield REAL,
            asset_turnover REAL,
            eps REAL,
            diluted_eps REAL,
            bps REAL,
            per REAL,
            fcf REAL,
            net_income_per_employee REAL,
            revenue_per_employee REAL,
            financial_leverage REAL,
            invested_capital REAL,
            split_adjustment_factor REAL,
            PRIMARY KEY (edinet_code, fiscal_year)
        )
    """,
    TABLE_TEXT_BLOCKS: f"""
        CREATE TABLE IF NOT EXISTS {TABLE_TEXT_BLOCKS} (
            edinet_code TEXT NOT NULL,
            fiscal_year INTEGER NOT NULL,
            section TEXT NOT NULL,
            text TEXT NOT NULL,
            PRIMARY KEY (edinet_code, fiscal_year, section)
        )
    """,
    TABLE_INDUSTRIES: f"""
        CREATE TABLE IF NOT EXISTS {TABLE_INDUSTRIES} (
            slug TEXT NOT NULL,
            name TEXT NOT NULL,
            company_count INTEGER NOT NULL,
            PRIMARY KEY (slug)
        )
    """,
    TABLE_INDUSTRY_DETAILS: f"""
        CREATE TABLE IF NOT EXISTS {TABLE_INDUSTRY_DETAILS} (
            slug TEXT NOT NULL,
            data TEXT NOT NULL,
            PRIMARY KEY (slug)
        )
    """,
}


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
    >>> _parse_ddl_columns(ddl)
    {'id', 'name'}
    """
    return {m.group(1) for m in _DDL_COLUMN_RE.finditer(ddl)}


# Pre-computed expected column sets from DDL (avoids re-parsing on each call)
_TABLE_EXPECTED_COLUMNS: dict[str, set[str]] = {
    name: _parse_ddl_columns(ddl) for name, ddl in _TABLE_DDL.items()
}

# Valid table names whitelist for SQL injection prevention
_VALID_TABLE_NAMES: frozenset[str] = frozenset(_TABLE_DDL.keys())


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


def _build_insert_sql(table_name: str, field_names: list[str]) -> str:
    """Build an INSERT OR REPLACE SQL statement for the given table and fields.

    Parameters
    ----------
    table_name : str
        Target table name.
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


class EdinetStorage:
    """SQLite storage layer for EDINET data.

    Manages 6 SQLite tables and provides upsert/query methods for
    each data type. Uses ``INSERT OR REPLACE`` for idempotent writes
    with primary key-based upsert.

    Parameters
    ----------
    config : EdinetConfig
        EDINET configuration containing the resolved DB path.

    Examples
    --------
    >>> from market.edinet.types import EdinetConfig
    >>> config = EdinetConfig(api_key="key", db_path=Path("/tmp/edinet.db"))
    >>> storage = EdinetStorage(config=config)
    >>> storage.upsert_companies([company1])
    >>> df = storage.get_company("E00001")
    """

    def __init__(self, config: EdinetConfig) -> None:
        self._client = SQLiteClient(config.resolved_db_path)
        logger.debug(
            "EdinetStorage initialized",
            db_path=str(config.resolved_db_path),
        )
        self.ensure_tables()

    # ------------------------------------------------------------------
    # Schema management
    # ------------------------------------------------------------------

    def ensure_tables(self) -> None:
        """Create all 6 tables if they do not already exist.

        Executes ``CREATE TABLE IF NOT EXISTS`` for each table defined
        in the EDINET schema. After creating tables, runs a lightweight
        migration to add any missing columns. Safe to call multiple times.
        """
        logger.debug("Ensuring EDINET tables exist")
        for table_name, ddl in _TABLE_DDL.items():
            self._client.execute(ddl)
            logger.debug("Table ensured", table_name=table_name)
        logger.info(
            "All EDINET tables ensured",
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
            Mapping of column name to column type string
            (e.g. ``{"edinet_code": "TEXT", "revenue": "REAL"}``).

        Raises
        ------
        ValueError
            If ``table_name`` is not in the allowed table list.
        """
        if table_name not in _VALID_TABLE_NAMES:
            raise ValueError(f"Unknown table: {table_name!r}")
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
            for col_name in missing:
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
    # Upsert methods
    # ------------------------------------------------------------------

    def upsert_companies(self, companies: list[Company]) -> None:
        """Upsert company master data.

        Parameters
        ----------
        companies : list[Company]
            List of Company dataclass instances to upsert.
        """
        if not companies:
            logger.debug("No companies to upsert, skipping")
            return
        field_names = [f.name for f in dataclasses.fields(companies[0])]
        sql = _build_insert_sql(TABLE_COMPANIES, field_names)
        params = [_dataclass_to_tuple(c) for c in companies]
        self._client.execute_many(sql, params)
        logger.info("Companies upserted", count=len(companies))

    def upsert_financials(self, records: list[FinancialRecord]) -> None:
        """Upsert annual financial statement data.

        Parameters
        ----------
        records : list[FinancialRecord]
            List of FinancialRecord dataclass instances to upsert.
        """
        if not records:
            logger.debug("No financial records to upsert, skipping")
            return
        field_names = [f.name for f in dataclasses.fields(records[0])]
        sql = _build_insert_sql(TABLE_FINANCIALS, field_names)
        params = [_dataclass_to_tuple(r) for r in records]
        self._client.execute_many(sql, params)
        logger.info("Financial records upserted", count=len(records))

    def upsert_ratios(self, records: list[RatioRecord]) -> None:
        """Upsert computed financial ratio data.

        Parameters
        ----------
        records : list[RatioRecord]
            List of RatioRecord dataclass instances to upsert.
        """
        if not records:
            logger.debug("No ratio records to upsert, skipping")
            return
        field_names = [f.name for f in dataclasses.fields(records[0])]
        sql = _build_insert_sql(TABLE_RATIOS, field_names)
        params = [_dataclass_to_tuple(r) for r in records]
        self._client.execute_many(sql, params)
        logger.info("Ratio records upserted", count=len(records))

    def upsert_text_blocks(self, blocks: list[TextBlock]) -> None:
        """Upsert securities report text excerpts.

        Parameters
        ----------
        blocks : list[TextBlock]
            List of TextBlock dataclass instances to upsert.
        """
        if not blocks:
            logger.debug("No text blocks to upsert, skipping")
            return
        field_names = [f.name for f in dataclasses.fields(blocks[0])]
        sql = _build_insert_sql(TABLE_TEXT_BLOCKS, field_names)
        params = [_dataclass_to_tuple(b) for b in blocks]
        self._client.execute_many(sql, params)
        logger.info("Text blocks upserted", count=len(blocks))

    def upsert_industries(self, industries: list[Industry]) -> None:
        """Upsert industry master data.

        Parameters
        ----------
        industries : list[Industry]
            List of Industry dataclass instances to upsert.
        """
        if not industries:
            logger.debug("No industries to upsert, skipping")
            return
        field_names = [f.name for f in dataclasses.fields(industries[0])]
        sql = _build_insert_sql(TABLE_INDUSTRIES, field_names)
        params = [_dataclass_to_tuple(i) for i in industries]
        self._client.execute_many(sql, params)
        logger.info("Industries upserted", count=len(industries))

    def upsert_industry_details(self, details_df: pd.DataFrame) -> None:
        """Upsert detailed industry data as JSON.

        Converts the full DataFrame row to a JSON string and stores it
        in the ``data`` column. This handles the variable-width API
        response (600+ columns) without requiring a fixed DDL.

        Parameters
        ----------
        details_df : pd.DataFrame
            DataFrame containing detailed industry data.
            Must include a ``slug`` column as the primary key.
        """
        if details_df.empty:
            logger.debug("No industry details to upsert, skipping")
            return
        import json

        params: list[tuple[Any, ...]] = []
        for _, row in details_df.iterrows():
            slug = str(row.get("slug", ""))
            data = json.dumps(row.to_dict(), ensure_ascii=False, default=str)
            params.append((slug, data))
        sql = _build_insert_sql(TABLE_INDUSTRY_DETAILS, ["slug", "data"])
        self._client.execute_many(sql, params)
        logger.info("Industry details upserted", count=len(details_df))

    # ------------------------------------------------------------------
    # Query methods
    # ------------------------------------------------------------------

    def get_company(self, edinet_code: str) -> pd.DataFrame | None:
        """Get company data by EDINET code.

        Parameters
        ----------
        edinet_code : str
            EDINET code to look up (e.g. ``"E00001"``).

        Returns
        -------
        pd.DataFrame | None
            Company data as a single-row DataFrame, or ``None`` if
            no matching record is found.
        """
        logger.debug("Getting company", edinet_code=edinet_code)
        with self._client.connection() as conn:
            df = pd.read_sql_query(
                f"SELECT * FROM {TABLE_COMPANIES} WHERE edinet_code = ?",  # nosec B608
                conn,
                params=[edinet_code],
            )
        if df.empty:
            logger.debug("Company not found", edinet_code=edinet_code)
            return None
        return df

    def get_financials(self, edinet_code: str) -> pd.DataFrame | None:
        """Get financial data by EDINET code.

        Parameters
        ----------
        edinet_code : str
            EDINET code to look up.

        Returns
        -------
        pd.DataFrame | None
            Financial records as a DataFrame, or ``None`` if no
            matching records are found.
        """
        logger.debug("Getting financials", edinet_code=edinet_code)
        with self._client.connection() as conn:
            df = pd.read_sql_query(
                f"SELECT * FROM {TABLE_FINANCIALS} WHERE edinet_code = ?",  # nosec B608
                conn,
                params=[edinet_code],
            )
        if df.empty:
            logger.debug("Financials not found", edinet_code=edinet_code)
            return None
        return df

    def get_all_company_codes(self) -> list[str]:
        """Get all EDINET codes from the companies table.

        Returns
        -------
        list[str]
            Sorted list of all EDINET codes.
        """
        logger.debug("Getting all company codes")
        rows = self._client.execute(
            f"SELECT edinet_code FROM {TABLE_COMPANIES} ORDER BY edinet_code"  # nosec B608
        )
        codes: list[str] = [row["edinet_code"] for row in rows]
        logger.debug("Company codes retrieved", count=len(codes))
        return codes

    # ------------------------------------------------------------------
    # Statistics
    # ------------------------------------------------------------------

    def get_stats(self) -> dict[str, int]:
        """Get row counts for all 6 tables.

        Returns
        -------
        dict[str, int]
            Dictionary mapping table name to row count.
        """
        logger.debug("Getting table statistics")
        stats: dict[str, int] = {}
        for tbl in _VALID_TABLE_NAMES:
            rows = self._client.execute(
                f"SELECT COUNT(*) AS cnt FROM {tbl}"  # nosec B608
            )
            stats[tbl] = rows[0]["cnt"]
        logger.info("Table statistics retrieved", stats=stats)
        return stats

    # ------------------------------------------------------------------
    # Raw query (SELECT-only)
    # ------------------------------------------------------------------

    def query(self, sql: str) -> pd.DataFrame:
        """Execute a read-only SQL query and return results.

        Only single ``SELECT`` statements are allowed. Other SQL
        operations (INSERT, UPDATE, DELETE, DROP, etc.) and multiple
        statements separated by semicolons are rejected to prevent
        unintended data modification.

        Parameters
        ----------
        sql : str
            SQL SELECT query to execute.

        Returns
        -------
        pd.DataFrame
            Query results as a DataFrame.

        Raises
        ------
        ValueError
            If the SQL statement is not a SELECT query or contains
            multiple statements.
        """
        stripped = sql.strip().lstrip("(")
        if not stripped.upper().startswith("SELECT"):
            raise ValueError(
                "Only SELECT queries are allowed. "
                f"Got: {sql.split()[0] if sql.split() else '(empty)'}..."
            )
        if ";" in sql:
            raise ValueError(
                "Multiple statements are not allowed in query(). "
                "Use a single SELECT statement."
            )
        logger.debug("Executing query", query_type="SELECT")
        with self._client.connection() as conn:
            return pd.read_sql_query(sql, conn)
