"""DuckDB storage layer for EDINET data.

This module provides the ``EdinetStorage`` class that manages 8 DuckDB
tables for persisting EDINET DB API data. It uses the existing
``DuckDBClient`` from ``database.db`` for all database operations,
leveraging its ``store_df(if_exists='upsert', key_columns=[...])``
capability for idempotent data updates.

Tables managed
--------------
- ``companies`` — Company master data (PK: ``edinet_code``)
- ``financials`` — Annual financial statements (PK: ``edinet_code``, ``fiscal_year``)
- ``ratios`` — Computed financial ratios (PK: ``edinet_code``, ``fiscal_year``)
- ``analyses`` — Financial health analysis (PK: ``edinet_code``)
- ``text_blocks`` — Securities report text excerpts (PK: ``edinet_code``, ``fiscal_year``)
- ``rankings`` — Metric-based company rankings (PK: ``metric``, ``rank``)
- ``industries`` — Industry master data (PK: ``slug``)
- ``industry_details`` — Detailed industry data (PK: ``slug``)

Examples
--------
>>> from market.edinet.types import EdinetConfig
>>> config = EdinetConfig(api_key="key", db_path=Path("/tmp/edinet.duckdb"))
>>> storage = EdinetStorage(config=config)
>>> storage.upsert_companies([company1, company2])
>>> df = storage.get_company("E00001")

See Also
--------
database.db.duckdb_client.DuckDBClient : Underlying DuckDB client.
market.edinet.types : Data record dataclasses.
market.edinet.constants : Table name constants.
"""

from __future__ import annotations

import dataclasses
import re
from typing import TYPE_CHECKING

import pandas as pd

from database.db.duckdb_client import DuckDBClient
from market.edinet.constants import (
    TABLE_ANALYSES,
    TABLE_COMPANIES,
    TABLE_FINANCIALS,
    TABLE_INDUSTRIES,
    TABLE_INDUSTRY_DETAILS,
    TABLE_RANKINGS,
    TABLE_RATIOS,
    TABLE_TEXT_BLOCKS,
)
from utils_core.logging import get_logger

if TYPE_CHECKING:
    from market.edinet.types import (
        AnalysisResult,
        Company,
        EdinetConfig,
        FinancialRecord,
        Industry,
        RankingEntry,
        RatioRecord,
        TextBlock,
    )

logger = get_logger(__name__)

# ============================================================================
# Column rename mapping (old name -> new name)
# ============================================================================

_COLUMN_RENAMES: dict[str, str] = {
    "operating_cf": "cf_operating",
    "investing_cf": "cf_investing",
    "financing_cf": "cf_financing",
    "employees": "num_employees",
    "rnd_expense": "rnd_expenses",
    "corp_name": "name",
    "industry_name": "industry",
    # analyses table: old field → new field
    "benchmark_comparison": "benchmark_summary",
}
"""Mapping of old column names to new column names.

Used during schema migration to preserve data from renamed columns.
Keys are old column names that no longer exist in the current DDL.
Values are the corresponding new column names in the current DDL.
"""

_REVERSE_COLUMN_RENAMES: dict[str, str] = {v: k for k, v in _COLUMN_RENAMES.items()}
"""Reverse mapping of new column names to old column names.

Pre-computed at module level to avoid rebuilding on each migration call.
"""

# ============================================================================
# Table DDL definitions
# ============================================================================

_TABLE_DDL: dict[str, str] = {
    TABLE_COMPANIES: f"""
        CREATE TABLE IF NOT EXISTS {TABLE_COMPANIES} (
            edinet_code VARCHAR NOT NULL,
            sec_code VARCHAR NOT NULL,
            name VARCHAR NOT NULL,
            industry VARCHAR NOT NULL,
            name_en VARCHAR,
            name_ja VARCHAR,
            accounting_standard VARCHAR,
            credit_rating VARCHAR,
            credit_score INTEGER
        )
    """,
    TABLE_FINANCIALS: f"""
        CREATE TABLE IF NOT EXISTS {TABLE_FINANCIALS} (
            edinet_code VARCHAR NOT NULL,
            fiscal_year INTEGER NOT NULL,
            revenue DOUBLE,
            operating_income DOUBLE,
            ordinary_income DOUBLE,
            net_income DOUBLE,
            profit_before_tax DOUBLE,
            comprehensive_income DOUBLE,
            total_assets DOUBLE,
            net_assets DOUBLE,
            shareholders_equity DOUBLE,
            cash DOUBLE,
            goodwill DOUBLE,
            cf_operating DOUBLE,
            cf_investing DOUBLE,
            cf_financing DOUBLE,
            eps DOUBLE,
            diluted_eps DOUBLE,
            bps DOUBLE,
            dividend_per_share DOUBLE,
            equity_ratio_official DOUBLE,
            payout_ratio DOUBLE,
            per DOUBLE,
            roe_official DOUBLE,
            num_employees BIGINT,
            capex DOUBLE,
            depreciation DOUBLE,
            rnd_expenses DOUBLE,
            accounting_standard VARCHAR,
            submit_date VARCHAR
        )
    """,
    TABLE_RATIOS: f"""
        CREATE TABLE IF NOT EXISTS {TABLE_RATIOS} (
            edinet_code VARCHAR NOT NULL,
            fiscal_year INTEGER NOT NULL,
            roe DOUBLE,
            roa DOUBLE,
            roe_official DOUBLE,
            net_margin DOUBLE,
            equity_ratio DOUBLE,
            equity_ratio_official DOUBLE,
            payout_ratio DOUBLE,
            dividend_per_share DOUBLE,
            adjusted_dividend_per_share DOUBLE,
            dividend_yield DOUBLE,
            asset_turnover DOUBLE,
            eps DOUBLE,
            diluted_eps DOUBLE,
            bps DOUBLE,
            per DOUBLE,
            fcf DOUBLE,
            net_income_per_employee DOUBLE,
            revenue_per_employee DOUBLE,
            financial_leverage DOUBLE,
            invested_capital DOUBLE,
            split_adjustment_factor DOUBLE
        )
    """,
    TABLE_ANALYSES: f"""
        CREATE TABLE IF NOT EXISTS {TABLE_ANALYSES} (
            edinet_code VARCHAR NOT NULL,
            health_score DOUBLE,
            credit_score INTEGER,
            credit_rating VARCHAR,
            benchmark_summary VARCHAR,
            commentary VARCHAR,
            fiscal_year INTEGER
        )
    """,
    TABLE_TEXT_BLOCKS: f"""
        CREATE TABLE IF NOT EXISTS {TABLE_TEXT_BLOCKS} (
            edinet_code VARCHAR NOT NULL,
            section VARCHAR NOT NULL,
            text VARCHAR NOT NULL
        )
    """,
    TABLE_RANKINGS: f"""
        CREATE TABLE IF NOT EXISTS {TABLE_RANKINGS} (
            metric VARCHAR NOT NULL,
            rank INTEGER NOT NULL,
            edinet_code VARCHAR NOT NULL,
            name VARCHAR NOT NULL,
            value DOUBLE NOT NULL,
            sec_code VARCHAR,
            industry VARCHAR,
            fiscal_year INTEGER,
            unit VARCHAR
        )
    """,
    TABLE_INDUSTRIES: f"""
        CREATE TABLE IF NOT EXISTS {TABLE_INDUSTRIES} (
            slug VARCHAR NOT NULL,
            name VARCHAR NOT NULL,
            company_count INTEGER NOT NULL
        )
    """,
    TABLE_INDUSTRY_DETAILS: f"""
        CREATE TABLE IF NOT EXISTS {TABLE_INDUSTRY_DETAILS} (
            slug VARCHAR NOT NULL,
            data VARCHAR NOT NULL
        )
    """,
}


# ============================================================================
# DDL parsing helper
# ============================================================================

# Regex to extract column definitions: "column_name TYPE [NOT NULL]"
_DDL_COLUMN_RE = re.compile(
    r"^\s+(\w+)\s+(VARCHAR|INTEGER|DOUBLE|BIGINT|BOOLEAN|DATE|TIMESTAMP)",
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
    >>> ddl = "CREATE TABLE t (id INTEGER, name VARCHAR)"
    >>> _parse_ddl_columns(ddl)
    {'id', 'name'}
    """
    return {m.group(1) for m in _DDL_COLUMN_RE.finditer(ddl)}


def _parse_ddl_columns_ordered(ddl: str) -> list[str]:
    """Extract column names from a DDL in declaration order.

    Parameters
    ----------
    ddl : str
        SQL CREATE TABLE statement to parse.

    Returns
    -------
    list[str]
        List of column names in the order they appear in the DDL.
    """
    return [m.group(1) for m in _DDL_COLUMN_RE.finditer(ddl)]


# Pre-computed expected column sets from DDL (avoids re-parsing on each call)
_TABLE_EXPECTED_COLUMNS: dict[str, set[str]] = {
    name: _parse_ddl_columns(ddl) for name, ddl in _TABLE_DDL.items()
}

# Valid table names whitelist for SQL injection prevention
_VALID_TABLE_NAMES: frozenset[str] = frozenset(_TABLE_DDL.keys())


class EdinetStorage:
    """DuckDB storage layer for EDINET data.

    Manages 8 DuckDB tables and provides upsert/query methods for
    each data type. Uses ``DuckDBClient.store_df()`` for idempotent
    writes with primary key-based upsert.

    Parameters
    ----------
    config : EdinetConfig
        EDINET configuration containing the resolved DB path.

    Examples
    --------
    >>> from market.edinet.types import EdinetConfig
    >>> config = EdinetConfig(api_key="key", db_path=Path("/tmp/edinet.duckdb"))
    >>> storage = EdinetStorage(config=config)
    >>> storage.upsert_companies([company1])
    >>> df = storage.get_company("E00001")
    """

    def __init__(self, config: EdinetConfig) -> None:
        self._client = DuckDBClient(config.resolved_db_path)
        logger.debug(
            "EdinetStorage initialized",
            db_path=str(config.resolved_db_path),
        )
        self.ensure_tables()

    # ------------------------------------------------------------------
    # Schema management
    # ------------------------------------------------------------------

    def ensure_tables(self) -> None:
        """Create all 8 tables if they do not already exist.

        Executes ``CREATE TABLE IF NOT EXISTS`` for each table defined
        in the EDINET schema. After creating tables, runs schema
        migration to handle column additions, renames, and type changes
        from older schema versions. Safe to call multiple times.
        """
        logger.debug("Ensuring EDINET tables exist")
        for table_name, ddl in _TABLE_DDL.items():
            self._client.execute(ddl)
            logger.debug("Table ensured", table_name=table_name)
        logger.info(
            "All EDINET tables ensured",
            table_count=len(_TABLE_DDL),
        )
        self._migrate_schema()

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
        tables = self._client.get_table_names()
        return table_name in tables

    def _get_column_info(self, table_name: str) -> dict[str, str]:
        """Get column names and types for an existing table.

        Parameters
        ----------
        table_name : str
            Name of the table to inspect. Must be in ``_VALID_TABLE_NAMES``.

        Returns
        -------
        dict[str, str]
            Mapping of column name to column type string
            (e.g. ``{"edinet_code": "VARCHAR", "revenue": "DOUBLE"}``).

        Raises
        ------
        ValueError
            If ``table_name`` is not in the allowed table list.
        """
        if table_name not in _VALID_TABLE_NAMES:
            raise ValueError(f"Unknown table: {table_name!r}")
        df = self._client.query_df(
            "SELECT column_name, data_type FROM information_schema.columns "  # nosec B608 - table_name validated against _VALID_TABLE_NAMES whitelist
            f"WHERE table_name = '{table_name}'"
        )
        return dict(zip(df["column_name"], df["data_type"], strict=True))

    def _schema_matches(self, table_name: str) -> bool:
        """Check whether an existing table's columns match the current DDL.

        Parameters
        ----------
        table_name : str
            Name of the table to compare.

        Returns
        -------
        bool
            ``True`` if the existing table's column set matches the
            DDL definition exactly, ``False`` otherwise.
        """
        if table_name not in _TABLE_EXPECTED_COLUMNS:
            return True

        existing_columns = set(self._get_column_info(table_name).keys())
        return existing_columns == _TABLE_EXPECTED_COLUMNS[table_name]

    def _migrate_schema(self) -> None:
        """Migrate all tables whose schemas differ from the current DDL.

        For each table defined in ``_TABLE_DDL``, compares the existing
        schema against the expected DDL columns. If a mismatch is
        detected (added, removed, or renamed columns), the table is
        migrated using ``_migrate_table()``.

        This method is called automatically by ``ensure_tables()``.
        """
        existing_tables = set(self._client.get_table_names())
        for table_name in _TABLE_DDL:
            if table_name not in existing_tables:
                continue
            if self._schema_matches(table_name):
                logger.debug(
                    "Schema matches, skipping migration",
                    table_name=table_name,
                )
                continue
            logger.info(
                "Schema mismatch detected, migrating table",
                table_name=table_name,
            )
            self._migrate_table(table_name)

    def _migrate_table(self, table_name: str) -> None:
        """Migrate a single table using backup-DROP-CREATE-INSERT strategy.

        Steps:
        1. Rename existing table to ``{table_name}_backup``
        2. Create new table with current DDL
        3. INSERT data from backup with column mapping and CAST
        4. Drop backup table

        If an error occurs during migration, the backup table is
        restored to preserve data.

        Parameters
        ----------
        table_name : str
            Name of the table to migrate.

        Raises
        ------
        Exception
            Re-raises any exception after restoring the backup table.
        """
        if table_name not in _VALID_TABLE_NAMES:
            raise ValueError(f"Unknown table for migration: {table_name!r}")
        backup_name = f"{table_name}_backup"
        ddl = _TABLE_DDL[table_name]

        # Get existing column info before migration
        existing_cols = self._get_column_info(table_name)
        # Single regex pass: extract ordered columns and type dict simultaneously
        matches = list(_DDL_COLUMN_RE.finditer(ddl))
        expected_cols_ordered = [m.group(1) for m in matches]
        ddl_types: dict[str, str] = {m.group(1): m.group(2) for m in matches}

        try:
            # Step 1: Backup
            self._client.execute(
                f"ALTER TABLE {table_name} RENAME TO {backup_name}"  # nosec B608
            )
            logger.debug(
                "Table backed up",
                table_name=table_name,
                backup_name=backup_name,
            )

            # Step 2: Create new table with current DDL
            self._client.execute(ddl)
            logger.debug("New table created", table_name=table_name)

            # Step 3: Build column mapping for INSERT (in DDL order)
            select_exprs: list[str] = []
            for col_name in expected_cols_ordered:
                expr = self._build_select_expr(
                    col_name,
                    ddl_types,
                    existing_cols,
                    _REVERSE_COLUMN_RENAMES,
                )
                select_exprs.append(expr)

            target_sql = ", ".join(expected_cols_ordered)
            select_sql = ", ".join(select_exprs)
            insert_sql = (
                f"INSERT INTO {table_name} ({target_sql}) "  # nosec B608
                f"SELECT {select_sql} FROM {backup_name}"
            )
            self._client.execute(insert_sql)
            logger.debug(
                "Data migrated",
                table_name=table_name,
                column_count=len(select_exprs),
            )

            # Step 4: Drop backup
            self._client.execute(f"DROP TABLE {backup_name}")  # nosec B608
            logger.info(
                "Migration completed successfully",
                table_name=table_name,
            )

        except Exception:
            logger.error(
                "Migration failed, restoring backup",
                table_name=table_name,
            )
            # Restore backup
            try:
                # Drop the partially created new table if it exists
                if self._table_exists(table_name):
                    self._client.execute(f"DROP TABLE {table_name}")  # nosec B608
                # Restore backup
                if self._table_exists(backup_name):
                    self._client.execute(
                        f"ALTER TABLE {backup_name} "  # nosec B608
                        f"RENAME TO {table_name}"
                    )
                    logger.info(
                        "Backup restored",
                        table_name=table_name,
                    )
            except Exception:
                logger.error(
                    "Failed to restore backup",
                    table_name=table_name,
                    backup_name=backup_name,
                    exc_info=True,
                )
            raise

    def _build_select_expr(
        self,
        col_name: str,
        ddl_types: dict[str, str],
        existing_cols: dict[str, str],
        reverse_renames: dict[str, str],
    ) -> str:
        """Build a SELECT expression for a single column during migration.

        Handles three cases:
        1. Column exists in old table (with optional type CAST)
        2. Column was renamed (map from old name, with optional CAST)
        3. Column is new (fill with NULL)

        Parameters
        ----------
        col_name : str
            Target column name in the new DDL.
        ddl_types : dict[str, str]
            Pre-computed column name -> type mapping from the DDL.
        existing_cols : dict[str, str]
            Column name -> type mapping from the old table.
        reverse_renames : dict[str, str]
            New name -> old name mapping from ``_COLUMN_RENAMES``.

        Returns
        -------
        str
            SQL expression for the SELECT clause.
        """
        # Case 1: Column exists in old table
        if col_name in existing_cols:
            return self._cast_if_needed(col_name, col_name, ddl_types, existing_cols)

        # Case 2: Column was renamed
        if col_name in reverse_renames:
            old_name = reverse_renames[col_name]
            if old_name in existing_cols:
                return self._cast_if_needed(
                    old_name,
                    col_name,
                    ddl_types,
                    existing_cols,
                )

        # Case 3: New column
        return "NULL"

    @staticmethod
    def _cast_if_needed(
        source_col: str,
        target_col: str,
        ddl_types: dict[str, str],
        existing_cols: dict[str, str],
    ) -> str:
        """Wrap a source column with CAST if the type has changed.

        Parameters
        ----------
        source_col : str
            Column name in the old (backup) table.
        target_col : str
            Column name in the new DDL (for type lookup).
        ddl_types : dict[str, str]
            Pre-computed column name -> type mapping from the DDL.
        existing_cols : dict[str, str]
            Column name -> type mapping from the old table.

        Returns
        -------
        str
            ``source_col`` or ``CAST(source_col AS new_type)``.
        """
        old_type = existing_cols[source_col].upper()
        expected_type = ddl_types.get(target_col)
        if expected_type and old_type != expected_type.upper():
            return f"CAST({source_col} AS {expected_type})"
        return source_col

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
        df = pd.DataFrame([dataclasses.asdict(c) for c in companies])
        self._client.store_df(
            df,
            TABLE_COMPANIES,
            if_exists="upsert",
            key_columns=["edinet_code"],
        )
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
        df = pd.DataFrame([dataclasses.asdict(r) for r in records])
        self._client.store_df(
            df,
            TABLE_FINANCIALS,
            if_exists="upsert",
            key_columns=["edinet_code", "fiscal_year"],
        )
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
        df = pd.DataFrame([dataclasses.asdict(r) for r in records])
        self._client.store_df(
            df,
            TABLE_RATIOS,
            if_exists="upsert",
            key_columns=["edinet_code", "fiscal_year"],
        )
        logger.info("Ratio records upserted", count=len(records))

    def upsert_analyses(self, analyses: list[AnalysisResult]) -> None:
        """Upsert financial health analysis results.

        Parameters
        ----------
        analyses : list[AnalysisResult]
            List of AnalysisResult dataclass instances to upsert.
        """
        if not analyses:
            logger.debug("No analyses to upsert, skipping")
            return
        df = pd.DataFrame([dataclasses.asdict(a) for a in analyses])
        self._client.store_df(
            df,
            TABLE_ANALYSES,
            if_exists="upsert",
            key_columns=["edinet_code"],
        )
        logger.info("Analyses upserted", count=len(analyses))

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
        df = pd.DataFrame([dataclasses.asdict(b) for b in blocks])
        self._client.store_df(
            df,
            TABLE_TEXT_BLOCKS,
            if_exists="upsert",
            key_columns=["edinet_code", "section"],
        )
        logger.info("Text blocks upserted", count=len(blocks))

    def upsert_rankings(self, entries: list[RankingEntry]) -> None:
        """Upsert metric-based company rankings.

        Parameters
        ----------
        entries : list[RankingEntry]
            List of RankingEntry dataclass instances to upsert.
        """
        if not entries:
            logger.debug("No ranking entries to upsert, skipping")
            return
        df = pd.DataFrame([dataclasses.asdict(e) for e in entries])
        self._client.store_df(
            df,
            TABLE_RANKINGS,
            if_exists="upsert",
            key_columns=["metric", "rank"],
        )
        logger.info("Ranking entries upserted", count=len(entries))

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
        df = pd.DataFrame([dataclasses.asdict(i) for i in industries])
        self._client.store_df(
            df,
            TABLE_INDUSTRIES,
            if_exists="upsert",
            key_columns=["slug"],
        )
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

        rows: list[dict[str, str]] = []
        for _, row in details_df.iterrows():
            slug = row.get("slug", "")
            rows.append(
                {
                    "slug": slug,
                    "data": json.dumps(row.to_dict(), ensure_ascii=False, default=str),
                }
            )
        compact_df = pd.DataFrame(rows)
        self._client.store_df(
            compact_df,
            TABLE_INDUSTRY_DETAILS,
            if_exists="upsert",
            key_columns=["slug"],
        )
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
        result = self._client.query_df(
            f"SELECT * FROM {TABLE_COMPANIES} WHERE edinet_code = $1",
            params=[edinet_code],
        )
        if result.empty:
            logger.debug("Company not found", edinet_code=edinet_code)
            return None
        return result

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
        result = self._client.query_df(
            f"SELECT * FROM {TABLE_FINANCIALS} WHERE edinet_code = $1",
            params=[edinet_code],
        )
        if result.empty:
            logger.debug("Financials not found", edinet_code=edinet_code)
            return None
        return result

    def get_all_company_codes(self) -> list[str]:
        """Get all EDINET codes from the companies table.

        Returns
        -------
        list[str]
            Sorted list of all EDINET codes.
        """
        logger.debug("Getting all company codes")
        result = self._client.query_df(
            f"SELECT edinet_code FROM {TABLE_COMPANIES} ORDER BY edinet_code"  # nosec B608
        )
        codes: list[str] = result["edinet_code"].tolist()
        logger.debug("Company codes retrieved", count=len(codes))
        return codes

    # ------------------------------------------------------------------
    # Statistics
    # ------------------------------------------------------------------

    def get_stats(self) -> dict[str, int]:
        """Get row counts for all 8 tables in a single query.

        Returns
        -------
        dict[str, int]
            Dictionary mapping table name to row count.
        """
        logger.debug("Getting table statistics")
        # Use UNION ALL to fetch all counts in a single query
        union_sql = " UNION ALL ".join(
            f"SELECT '{tbl}' AS tbl, COUNT(*) AS cnt FROM {tbl}"  # nosec B608 - tbl from _VALID_TABLE_NAMES constant
            for tbl in _VALID_TABLE_NAMES
        )
        df = self._client.query_df(union_sql)
        stats = dict(zip(df["tbl"], df["cnt"].astype(int), strict=True))
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
        return self._client.query_df(sql)
