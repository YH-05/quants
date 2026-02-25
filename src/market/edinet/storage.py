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
# Table DDL definitions
# ============================================================================

_TABLE_DDL: dict[str, str] = {
    TABLE_COMPANIES: f"""
        CREATE TABLE IF NOT EXISTS {TABLE_COMPANIES} (
            edinet_code VARCHAR NOT NULL,
            sec_code VARCHAR NOT NULL,
            corp_name VARCHAR NOT NULL,
            industry_code VARCHAR NOT NULL,
            industry_name VARCHAR NOT NULL,
            listing_status VARCHAR NOT NULL
        )
    """,
    TABLE_FINANCIALS: f"""
        CREATE TABLE IF NOT EXISTS {TABLE_FINANCIALS} (
            edinet_code VARCHAR NOT NULL,
            fiscal_year VARCHAR NOT NULL,
            period_type VARCHAR NOT NULL,
            revenue BIGINT NOT NULL,
            operating_income BIGINT NOT NULL,
            ordinary_income BIGINT NOT NULL,
            net_income BIGINT NOT NULL,
            total_assets BIGINT NOT NULL,
            net_assets BIGINT NOT NULL,
            equity BIGINT NOT NULL,
            interest_bearing_debt BIGINT NOT NULL,
            operating_cf BIGINT NOT NULL,
            investing_cf BIGINT NOT NULL,
            financing_cf BIGINT NOT NULL,
            free_cf BIGINT NOT NULL,
            eps DOUBLE NOT NULL,
            bps DOUBLE NOT NULL,
            dividend_per_share DOUBLE NOT NULL,
            shares_outstanding BIGINT NOT NULL,
            employees BIGINT NOT NULL,
            capex BIGINT NOT NULL,
            depreciation BIGINT NOT NULL,
            rnd_expense BIGINT NOT NULL,
            goodwill BIGINT NOT NULL
        )
    """,
    TABLE_RATIOS: f"""
        CREATE TABLE IF NOT EXISTS {TABLE_RATIOS} (
            edinet_code VARCHAR NOT NULL,
            fiscal_year VARCHAR NOT NULL,
            period_type VARCHAR NOT NULL,
            roe DOUBLE NOT NULL,
            roa DOUBLE NOT NULL,
            operating_margin DOUBLE NOT NULL,
            net_margin DOUBLE NOT NULL,
            equity_ratio DOUBLE NOT NULL,
            debt_equity_ratio DOUBLE NOT NULL,
            current_ratio DOUBLE NOT NULL,
            interest_coverage_ratio DOUBLE NOT NULL,
            payout_ratio DOUBLE NOT NULL,
            asset_turnover DOUBLE NOT NULL,
            revenue_growth DOUBLE NOT NULL,
            operating_income_growth DOUBLE NOT NULL,
            net_income_growth DOUBLE NOT NULL
        )
    """,
    TABLE_ANALYSES: f"""
        CREATE TABLE IF NOT EXISTS {TABLE_ANALYSES} (
            edinet_code VARCHAR NOT NULL,
            health_score DOUBLE NOT NULL,
            benchmark_comparison VARCHAR NOT NULL,
            commentary VARCHAR NOT NULL
        )
    """,
    TABLE_TEXT_BLOCKS: f"""
        CREATE TABLE IF NOT EXISTS {TABLE_TEXT_BLOCKS} (
            edinet_code VARCHAR NOT NULL,
            fiscal_year VARCHAR NOT NULL,
            business_overview VARCHAR NOT NULL,
            risk_factors VARCHAR NOT NULL,
            management_analysis VARCHAR NOT NULL
        )
    """,
    TABLE_RANKINGS: f"""
        CREATE TABLE IF NOT EXISTS {TABLE_RANKINGS} (
            metric VARCHAR NOT NULL,
            rank INTEGER NOT NULL,
            edinet_code VARCHAR NOT NULL,
            corp_name VARCHAR NOT NULL,
            value DOUBLE NOT NULL
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
            slug VARCHAR NOT NULL
        )
    """,
}


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
        in the EDINET schema. Safe to call multiple times.
        """
        logger.debug("Ensuring EDINET tables exist")
        for table_name, ddl in _TABLE_DDL.items():
            self._client.execute(ddl)
            logger.debug("Table ensured", table_name=table_name)
        logger.info(
            "All EDINET tables ensured",
            table_count=len(_TABLE_DDL),
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
            key_columns=["edinet_code", "fiscal_year"],
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
        """Upsert detailed industry data from a DataFrame.

        Parameters
        ----------
        details_df : pd.DataFrame
            DataFrame containing detailed industry data.
            Must include a ``slug`` column as the primary key.
        """
        if details_df.empty:
            logger.debug("No industry details to upsert, skipping")
            return
        self._client.store_df(
            details_df,
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
        """Get row counts for all 8 tables.

        Returns
        -------
        dict[str, int]
            Dictionary mapping table name to row count.
        """
        logger.debug("Getting table statistics")
        stats: dict[str, int] = {}
        for table_name in _TABLE_DDL:
            result = self._client.query_df(
                f"SELECT COUNT(*) as count FROM {table_name}"  # nosec B608
            )
            stats[table_name] = int(result["count"].iloc[0])
        logger.info("Table statistics retrieved", stats=stats)
        return stats

    # ------------------------------------------------------------------
    # Raw query (SELECT-only)
    # ------------------------------------------------------------------

    def query(self, sql: str) -> pd.DataFrame:
        """Execute a read-only SQL query and return results.

        Only ``SELECT`` statements are allowed. Other SQL operations
        (INSERT, UPDATE, DELETE, DROP, etc.) are rejected to prevent
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
            If the SQL statement is not a SELECT query.
        """
        stripped = sql.strip().lstrip("(")
        if not stripped.upper().startswith("SELECT"):
            raise ValueError(
                "Only SELECT queries are allowed. "
                f"Got: {sql.split()[0] if sql.split() else '(empty)'}..."
            )
        logger.debug("Executing query", query_type="SELECT")
        return self._client.query_df(sql)
