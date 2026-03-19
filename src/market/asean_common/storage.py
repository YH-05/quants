"""DuckDB storage layer for ASEAN ticker master data.

This module provides the ``AseanTickerStorage`` class that manages the
``asean_tickers`` DuckDB table for persisting ASEAN exchange-listed ticker
data. It follows the same patterns as ``market.edinet.storage``, using
``DuckDBClient`` for all database operations.

Tables managed
--------------
- ``asean_tickers`` -- Ticker master for all 6 ASEAN exchanges
  (PK: ``ticker``, ``market``)

Examples
--------
>>> from pathlib import Path
>>> from database.db.duckdb_client import DuckDBClient
>>> client = DuckDBClient(Path("data/processed/asean.duckdb"))
>>> storage = AseanTickerStorage(client=client)
>>> storage.upsert_tickers([ticker_record])
1
>>> tickers = storage.get_tickers(AseanMarket.SGX)

See Also
--------
database.db.duckdb_client.DuckDBClient : Underlying DuckDB client.
market.asean_common.types : TickerRecord dataclass.
market.asean_common.constants : TABLE_TICKERS and AseanMarket enum.
market.edinet.storage : Reference storage implementation.
"""

from __future__ import annotations

import dataclasses
from typing import TYPE_CHECKING

import pandas as pd
import pandera.pandas as pa

from market.asean_common._utils import _coerce_optional_int, _coerce_optional_str
from market.asean_common.constants import TABLE_TICKERS, AseanMarket
from market.asean_common.types import TickerRecord
from utils_core.logging import get_logger

if TYPE_CHECKING:
    from database.db.duckdb_client import DuckDBClient

logger = get_logger(__name__)


# ============================================================================
# pandera DataFrame schema for asean_tickers table
# ============================================================================

TICKER_DF_SCHEMA: pa.DataFrameSchema = pa.DataFrameSchema(
    columns={
        "ticker": pa.Column(str, nullable=False),
        "name": pa.Column(str, nullable=False),
        "market": pa.Column(str, nullable=False),
        "yfinance_suffix": pa.Column(str, nullable=False),
        "yfinance_ticker": pa.Column(str, nullable=False),
        "sector": pa.Column(str, nullable=True),
        "industry": pa.Column(str, nullable=True),
        "market_cap": pa.Column(
            "Int64",
            nullable=True,
            coerce=True,
        ),
        "currency": pa.Column(str, nullable=True),
        "is_active": pa.Column(bool, nullable=False, coerce=True),
    },
    strict=False,
    name="AseanTickerSchema",
)


# ============================================================================
# Table DDL definition
# ============================================================================

_TABLE_DDL: str = f"""
    CREATE TABLE IF NOT EXISTS {TABLE_TICKERS} (
        ticker VARCHAR NOT NULL,
        name VARCHAR NOT NULL,
        market VARCHAR NOT NULL,
        yfinance_suffix VARCHAR NOT NULL,
        yfinance_ticker VARCHAR NOT NULL,
        sector VARCHAR,
        industry VARCHAR,
        market_cap BIGINT,
        currency VARCHAR,
        is_active BOOLEAN NOT NULL DEFAULT TRUE
    )
"""


class AseanTickerStorage:
    """DuckDB storage layer for ASEAN ticker master data.

    Manages the ``asean_tickers`` DuckDB table and provides
    upsert/query methods for ticker data. Uses ``DuckDBClient``
    injected via constructor for all database operations.

    Parameters
    ----------
    client : DuckDBClient
        DuckDB client instance for database operations.

    Examples
    --------
    >>> from database.db.duckdb_client import DuckDBClient
    >>> client = DuckDBClient(Path("data/processed/asean.duckdb"))
    >>> storage = AseanTickerStorage(client=client)
    >>> storage.upsert_tickers([ticker])
    1
    """

    def __init__(self, client: DuckDBClient) -> None:
        self._client = client
        logger.debug(
            "AseanTickerStorage initialized",
            db_path=str(client.path),
        )
        self.ensure_tables()

    # ------------------------------------------------------------------
    # Schema management
    # ------------------------------------------------------------------

    def ensure_tables(self) -> None:
        """Create the asean_tickers table if it does not already exist.

        Validates ``TABLE_TICKERS`` via ``DuckDBClient._validate_identifier``
        before executing DDL to prevent SQL injection if the table name is
        ever sourced from external configuration.

        Executes ``CREATE TABLE IF NOT EXISTS`` for the ticker master
        table. Safe to call multiple times.

        Raises
        ------
        ValueError
            If ``TABLE_TICKERS`` is not a valid SQL identifier.
        """
        logger.debug("Ensuring ASEAN ticker table exists")
        self._client._validate_identifier(TABLE_TICKERS)
        self._client.execute(_TABLE_DDL)
        logger.info("ASEAN ticker table ensured", table_name=TABLE_TICKERS)

    # ------------------------------------------------------------------
    # Upsert methods
    # ------------------------------------------------------------------

    def upsert_tickers(self, tickers: list[TickerRecord]) -> int:
        """Upsert ticker records into the asean_tickers table.

        Performs a delete-then-insert upsert using ``(ticker, market)``
        as the composite primary key. Validates the DataFrame against
        ``TICKER_DF_SCHEMA`` before writing to DuckDB.

        Parameters
        ----------
        tickers : list[TickerRecord]
            List of TickerRecord dataclass instances to upsert.

        Returns
        -------
        int
            Number of records upserted.

        Raises
        ------
        pandera.errors.SchemaError
            If the DataFrame fails schema validation (e.g. invalid
            ``market_cap`` type, missing required columns).
        """
        if not tickers:
            logger.debug("No tickers to upsert, skipping")
            return 0

        df = self._build_ticker_df(tickers)
        logger.debug("Validating ticker DataFrame against schema", rows=len(df))
        df = TICKER_DF_SCHEMA.validate(df)
        logger.debug("Schema validation passed", rows=len(df))
        self._client.store_df(
            df,
            TABLE_TICKERS,
            if_exists="upsert",
            key_columns=["ticker", "market"],
        )
        count = len(tickers)
        logger.info("Tickers upserted", count=count)
        return count

    @staticmethod
    def _build_ticker_df(tickers: list[TickerRecord]) -> pd.DataFrame:
        """Convert TickerRecord list to a DataFrame suitable for storage.

        Converts dataclass instances to dicts via ``dataclasses.asdict``
        and coerces ``AseanMarket`` enum values to plain strings.

        Parameters
        ----------
        tickers : list[TickerRecord]
            TickerRecord instances to convert.

        Returns
        -------
        pd.DataFrame
            DataFrame with columns matching the ``asean_tickers`` DDL.
        """
        df = pd.DataFrame([dataclasses.asdict(t) for t in tickers])
        # Convert AseanMarket enum to string for storage
        df["market"] = df["market"].apply(
            lambda m: m.value if isinstance(m, AseanMarket) else str(m)
        )
        return df

    # ------------------------------------------------------------------
    # Query methods
    # ------------------------------------------------------------------

    def get_tickers(self, market: AseanMarket) -> list[TickerRecord]:
        """Get all tickers for a specific ASEAN market.

        Parameters
        ----------
        market : AseanMarket
            The ASEAN exchange to filter by.

        Returns
        -------
        list[TickerRecord]
            List of TickerRecord instances for the specified market.
            Empty list if no tickers found.
        """
        logger.debug("Getting tickers", market=market.value)
        df = self._client.query_df(
            f"SELECT * FROM {TABLE_TICKERS} WHERE market = $1",  # nosec B608
            params=[market.value],
        )
        if df.empty:
            logger.debug("No tickers found", market=market.value)
            return []

        result = self._df_to_ticker_records(df)
        logger.info(
            "Tickers retrieved",
            market=market.value,
            count=len(result),
        )
        return result

    def lookup_ticker(
        self,
        name: str,
        market: AseanMarket | None = None,
    ) -> list[TickerRecord]:
        """Look up tickers by name using case-insensitive LIKE search.

        Performs a partial match search on the ``name`` column using
        SQL ``ILIKE`` for case-insensitive matching.

        Parameters
        ----------
        name : str
            Search string for partial name matching.
        market : AseanMarket | None
            Optional market filter. If ``None``, searches all markets.

        Returns
        -------
        list[TickerRecord]
            List of matching TickerRecord instances.
            Empty list if no matches found.
        """
        logger.debug(
            "Looking up ticker",
            name=name,
            market=market.value if market else None,
        )
        pattern = f"%{name}%"

        if market is not None:
            df = self._client.query_df(
                f"SELECT * FROM {TABLE_TICKERS} "  # nosec B608
                "WHERE name ILIKE $1 AND market = $2",
                params=[pattern, market.value],
            )
        else:
            df = self._client.query_df(
                f"SELECT * FROM {TABLE_TICKERS} WHERE name ILIKE $1",  # nosec B608
                params=[pattern],
            )

        if df.empty:
            logger.debug("No tickers found for lookup", name=name)
            return []

        result = self._df_to_ticker_records(df)
        logger.info("Ticker lookup completed", name=name, count=len(result))
        return result

    # ------------------------------------------------------------------
    # Statistics
    # ------------------------------------------------------------------

    def count_tickers(self) -> dict[str, int]:
        """Get ticker counts grouped by market.

        Returns
        -------
        dict[str, int]
            Dictionary mapping market name (str) to ticker count.
            Empty dict if no data exists.
        """
        logger.debug("Counting tickers by market")
        df = self._client.query_df(
            f"SELECT market, COUNT(*) AS cnt FROM {TABLE_TICKERS} "  # nosec B608
            "GROUP BY market ORDER BY market"
        )
        if df.empty:
            logger.debug("No tickers in database")
            return {}

        counts = dict(
            zip(
                df["market"].tolist(),
                df["cnt"].astype(int).tolist(),
                strict=True,
            )
        )
        logger.info("Ticker counts retrieved", counts=counts)
        return counts

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _df_to_ticker_records(df: pd.DataFrame) -> list[TickerRecord]:
        """Convert a DataFrame to a list of TickerRecord instances.

        Parameters
        ----------
        df : pd.DataFrame
            DataFrame with columns matching TickerRecord fields.

        Returns
        -------
        list[TickerRecord]
            List of TickerRecord instances.
        """
        records: list[TickerRecord] = []
        for row_dict in df.to_dict(orient="records"):
            market = AseanMarket(str(row_dict["market"]))
            records.append(
                TickerRecord(
                    ticker=str(row_dict["ticker"]),
                    name=str(row_dict["name"]),
                    market=market,
                    yfinance_suffix=str(row_dict["yfinance_suffix"]),
                    sector=_coerce_optional_str(row_dict["sector"]),
                    industry=_coerce_optional_str(row_dict["industry"]),
                    market_cap=_coerce_optional_int(row_dict["market_cap"]),
                    currency=_coerce_optional_str(row_dict["currency"]),
                    is_active=bool(row_dict["is_active"]),
                )
            )
        return records
