"""DuckDB client for analytics."""

import re
from pathlib import Path
from typing import Literal

import duckdb
import pandas as pd

from utils_core.logging import get_logger

logger = get_logger(__name__)

# Regex for safe SQL identifiers (table names, column names)
_IDENTIFIER_RE = re.compile(r"^[a-zA-Z_][a-zA-Z0-9_]*$")


class DuckDBClient:
    """DuckDB analytics client.

    Parameters
    ----------
    db_path : Path
        Path to DuckDB database file

    Examples
    --------
    >>> from database.db import DuckDBClient, get_db_path
    >>> client = DuckDBClient(get_db_path("duckdb", "analytics"))
    >>> df = client.query_df("SELECT 1 as value")
    >>> df['value'].iloc[0]
    1
    """

    def __init__(self, db_path: Path) -> None:
        self._db_path = db_path
        self._db_path.parent.mkdir(parents=True, exist_ok=True)
        logger.debug("DuckDBClient initialized", db_path=str(db_path))

    @property
    def path(self) -> Path:
        """Get the database file path."""
        return self._db_path

    def query_df(self, sql: str) -> pd.DataFrame:
        """Execute query and return DataFrame.

        Parameters
        ----------
        sql : str
            SQL query to execute

        Returns
        -------
        pd.DataFrame
            Query results as DataFrame
        """
        logger.debug("Executing DuckDB query", sql_preview=sql[:100])
        with duckdb.connect(str(self._db_path)) as conn:
            result = conn.execute(sql).fetchdf()
            logger.debug("Query completed", row_count=len(result))
            return result

    def execute(self, sql: str) -> None:
        """Execute SQL without returning results.

        Parameters
        ----------
        sql : str
            SQL to execute
        """
        logger.debug("Executing DuckDB SQL", sql_preview=sql[:100])
        with duckdb.connect(str(self._db_path)) as conn:
            conn.execute(sql)

    def read_parquet(self, pattern: str) -> pd.DataFrame:
        """Read Parquet files matching pattern.

        Parameters
        ----------
        pattern : str
            Glob pattern for Parquet files

        Returns
        -------
        pd.DataFrame
            Combined data from matching files

        Examples
        --------
        >>> client = DuckDBClient(get_db_path("duckdb", "analytics"))
        >>> df = client.read_parquet("data/raw/yfinance/stocks/*.parquet")
        """
        sql = f"SELECT * FROM read_parquet('{pattern}')"  # nosec B608
        return self.query_df(sql)

    def write_parquet(self, df: pd.DataFrame, path: str | Path) -> None:
        """Write DataFrame to Parquet file.

        Parameters
        ----------
        df : pd.DataFrame
            DataFrame to write
        path : str | Path
            Output path for Parquet file
        """
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        logger.debug("Writing Parquet file", path=str(path), row_count=len(df))
        with duckdb.connect(str(self._db_path)) as conn:
            conn.execute(f"COPY df TO '{path}' (FORMAT PARQUET)")
        logger.info("Parquet file written", path=str(path))

    # ------------------------------------------------------------------
    # Identifier validation
    # ------------------------------------------------------------------

    @staticmethod
    def _validate_identifier(name: str) -> None:
        """Validate a SQL identifier (table name or column name).

        Parameters
        ----------
        name : str
            Identifier to validate

        Raises
        ------
        ValueError
            If the identifier does not match ``^[a-zA-Z_][a-zA-Z0-9_]*$``

        Examples
        --------
        >>> DuckDBClient._validate_identifier("prices")   # OK
        >>> DuckDBClient._validate_identifier("1bad")
        Traceback (most recent call last):
            ...
        ValueError: Invalid identifier: '1bad'. Must match ^[a-zA-Z_][a-zA-Z0-9_]*$
        """
        if not _IDENTIFIER_RE.match(name):
            raise ValueError(
                f"Invalid identifier: {name!r}. Must match ^[a-zA-Z_][a-zA-Z0-9_]*$"
            )

    # ------------------------------------------------------------------
    # Table management
    # ------------------------------------------------------------------

    def get_table_names(self) -> list[str]:
        """Return the names of all tables in the database.

        Returns
        -------
        list[str]
            Sorted list of table names

        Examples
        --------
        >>> client = DuckDBClient(get_db_path("duckdb", "analytics"))
        >>> client.execute("CREATE TABLE foo (id INTEGER)")
        >>> client.get_table_names()
        ['foo']
        """
        logger.debug("Fetching table names")
        with duckdb.connect(str(self._db_path)) as conn:
            rows = conn.execute("SHOW TABLES").fetchall()
        names = [row[0] for row in rows]
        logger.debug("Tables retrieved", table_count=len(names))
        return names

    # ------------------------------------------------------------------
    # DataFrame storage
    # ------------------------------------------------------------------

    def store_df(
        self,
        df: pd.DataFrame,
        table_name: str,
        *,
        if_exists: Literal["replace", "append", "upsert"] = "upsert",
        key_columns: list[str] | None = None,
    ) -> None:
        """Save a DataFrame to a DuckDB table.

        Parameters
        ----------
        df : pd.DataFrame
            DataFrame to store
        table_name : str
            Destination table name (must be a valid SQL identifier)
        if_exists : {'replace', 'append', 'upsert'}
            Behaviour when the table already exists:

            * ``replace`` – CREATE OR REPLACE TABLE; existing rows identical
              to new rows are skipped (full-column deduplication).
            * ``append`` – INSERT all rows without deduplication.
            * ``upsert`` – Delete rows whose ``key_columns`` match new rows,
              then insert the new rows.
        key_columns : list[str] | None
            Column(s) used as the unique key for ``upsert`` mode.
            Required (non-empty) when ``if_exists='upsert'``.

        Raises
        ------
        ValueError
            If ``table_name`` or any element of ``key_columns`` is not a
            valid SQL identifier, or if ``key_columns`` is absent/empty for
            ``upsert`` mode.

        Examples
        --------
        >>> import pandas as pd
        >>> from database.db import DuckDBClient, get_db_path
        >>> client = DuckDBClient(get_db_path("duckdb", "analytics"))
        >>> df = pd.DataFrame({"date": ["2024-01-01"], "ticker": ["AAPL"], "close": [100.0]})
        >>> client.store_df(df, "prices", if_exists="upsert", key_columns=["date", "ticker"])
        """
        # --- Validate identifiers ---
        self._validate_identifier(table_name)
        if key_columns is not None:
            for col in key_columns:
                self._validate_identifier(col)

        if if_exists == "upsert" and not key_columns:
            raise ValueError(
                "key_columns must be provided and non-empty for if_exists='upsert'"
            )

        logger.debug(
            "Storing DataFrame",
            table_name=table_name,
            if_exists=if_exists,
            row_count=len(df),
        )

        with duckdb.connect(str(self._db_path)) as conn:
            # Check whether the table already exists
            existing_tables = [row[0] for row in conn.execute("SHOW TABLES").fetchall()]
            table_exists = table_name in existing_tables

            if not table_exists:
                # First write: always CREATE TABLE AS SELECT
                conn.execute(f"CREATE TABLE {table_name} AS SELECT * FROM df")  # nosec B608
                logger.info(
                    "Table created",
                    table_name=table_name,
                    row_count=len(df),
                )

            elif if_exists == "replace":
                # Replace entire table contents with df
                conn.execute(  # nosec B608
                    f"CREATE OR REPLACE TABLE {table_name} AS SELECT * FROM df"
                )
                logger.info(
                    "Table replaced",
                    table_name=table_name,
                    row_count=len(df),
                )

            elif if_exists == "append":
                conn.execute(f"INSERT INTO {table_name} SELECT * FROM df")  # nosec B608
                logger.info(
                    "Rows appended",
                    table_name=table_name,
                    row_count=len(df),
                )

            elif if_exists == "upsert":
                # key_columns is guaranteed non-None/non-empty here
                assert key_columns is not None  # AIDEV-NOTE: narrowing for type checker
                key_cond = " AND ".join(f"existing.{c} = new.{c}" for c in key_columns)
                # Delete rows matching the keys
                conn.execute(f"""
                    DELETE FROM {table_name} existing
                    WHERE EXISTS (
                        SELECT 1 FROM df new
                        WHERE {key_cond}
                    )
                """)  # nosec B608
                # Insert new rows
                conn.execute(f"INSERT INTO {table_name} SELECT * FROM df")  # nosec B608
                row = conn.execute(  # nosec B608
                    f"SELECT COUNT(*) FROM {table_name}"
                ).fetchone()
                total = row[0] if row is not None else 0
                logger.info(
                    "Upsert completed",
                    table_name=table_name,
                    input_rows=len(df),
                    total_rows=total,
                )
