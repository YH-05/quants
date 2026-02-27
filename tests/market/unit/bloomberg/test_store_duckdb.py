"""Unit tests for BloombergFetcher DuckDB storage methods.

Tests for:
- store_to_database: uses DuckDBClient.store_df() instead of SQLite
- get_latest_date_from_db: uses DuckDBClient.query_df() instead of SQLite
"""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING
from unittest.mock import MagicMock, patch

import pandas as pd
import pytest

if TYPE_CHECKING:
    from market.bloomberg.fetcher import BloombergFetcher


class TestStoreToDatabaseDuckDB:
    """Tests for store_to_database using DuckDB backend."""

    def test_正常系_DuckDBClientのstore_dfを使用する(self, tmp_path: Path) -> None:
        """store_to_databaseがDuckDBClient.store_df()を呼び出すこと."""
        from market.bloomberg.fetcher import BloombergFetcher

        fetcher = BloombergFetcher()
        db_path = str(tmp_path / "test.duckdb")
        table_name = "historical_prices"
        df = pd.DataFrame(
            {
                "date": pd.to_datetime(["2024-01-01", "2024-01-02"]),
                "PX_LAST": [150.0, 151.0],
            }
        )

        mock_client = MagicMock()

        with patch("market.bloomberg.fetcher.DuckDBClient") as mock_cls:
            mock_cls.return_value = mock_client
            fetcher.store_to_database(data=df, db_path=db_path, table_name=table_name)

        # DuckDBClient should have been instantiated
        mock_cls.assert_called_once()
        # store_df should be called with the DataFrame and table_name
        mock_client.store_df.assert_called_once()

    def test_正常系_SQLiteを使用しない(self, tmp_path: Path) -> None:
        """store_to_databaseがsqlite3.connectを呼び出さないこと."""
        from market.bloomberg.fetcher import BloombergFetcher

        fetcher = BloombergFetcher()
        db_path = str(tmp_path / "test.duckdb")
        df = pd.DataFrame({"date": [datetime(2024, 1, 1)], "PX_LAST": [150.0]})

        mock_client = MagicMock()

        with patch("market.bloomberg.fetcher.DuckDBClient") as mock_cls:
            mock_cls.return_value = mock_client
            with patch("sqlite3.connect") as mock_sqlite:
                fetcher.store_to_database(data=df, db_path=db_path, table_name="prices")

        # sqlite3.connect should NOT be called
        mock_sqlite.assert_not_called()

    def test_正常系_データが正しく保存される(self, tmp_path: Path) -> None:
        """実際にDuckDBファイルにDataFrameを保存し読み取れること."""
        from database.db import DuckDBClient
        from market.bloomberg.fetcher import BloombergFetcher

        fetcher = BloombergFetcher()
        db_path = str(tmp_path / "bloomberg.duckdb")
        table_name = "prices"
        df = pd.DataFrame(
            {
                "date": pd.to_datetime(["2024-01-01", "2024-01-02", "2024-01-03"]),
                "security": ["AAPL US Equity"] * 3,
                "PX_LAST": [150.0, 151.0, 152.0],
            }
        )

        fetcher.store_to_database(data=df, db_path=db_path, table_name=table_name)

        # Verify data was actually saved
        client = DuckDBClient(Path(db_path))
        result = client.query_df(f"SELECT * FROM {table_name}")  # nosec B608
        assert len(result) == 3
        assert "PX_LAST" in result.columns

    def test_正常系_store_dfが正しいテーブル名で呼ばれる(self, tmp_path: Path) -> None:
        """store_dfが正しいtable_nameで呼ばれること."""
        from market.bloomberg.fetcher import BloombergFetcher

        fetcher = BloombergFetcher()
        db_path = str(tmp_path / "test.duckdb")
        df = pd.DataFrame({"date": [datetime(2024, 1, 1)], "PX_LAST": [150.0]})

        mock_client = MagicMock()

        with patch("market.bloomberg.fetcher.DuckDBClient") as mock_cls:
            mock_cls.return_value = mock_client
            fetcher.store_to_database(data=df, db_path=db_path, table_name="my_table")

        call_args = mock_client.store_df.call_args
        assert call_args is not None
        # store_df(data, table_name, if_exists="replace")
        # table_name is the second positional arg (index 1)
        positional_args = call_args.args if hasattr(call_args, "args") else call_args[0]
        assert positional_args[1] == "my_table"


class TestGetLatestDateFromDbDuckDB:
    """Tests for get_latest_date_from_db using DuckDB backend."""

    def test_正常系_DuckDBClientのquery_dfを使用する(self, tmp_path: Path) -> None:
        """get_latest_date_from_dbがDuckDBClient.query_df()を呼び出すこと."""
        from market.bloomberg.fetcher import BloombergFetcher

        fetcher = BloombergFetcher()
        db_path = str(tmp_path / "test.duckdb")

        mock_client = MagicMock()
        mock_client.query_df.return_value = pd.DataFrame(
            {"max_date": [pd.Timestamp("2024-03-15")]}
        )

        with patch("market.bloomberg.fetcher.DuckDBClient") as mock_cls:
            mock_cls.return_value = mock_client
            result = fetcher.get_latest_date_from_db(
                db_path=db_path,
                table_name="prices",
                date_column="date",
            )

        mock_cls.assert_called_once()
        mock_client.query_df.assert_called_once()

    def test_正常系_SQLiteを使用しない(self, tmp_path: Path) -> None:
        """get_latest_date_from_dbがsqlite3.connectを呼び出さないこと."""
        from market.bloomberg.fetcher import BloombergFetcher

        fetcher = BloombergFetcher()
        db_path = str(tmp_path / "test.duckdb")

        mock_client = MagicMock()
        mock_client.query_df.return_value = pd.DataFrame({"max_date": [None]})

        with patch("market.bloomberg.fetcher.DuckDBClient") as mock_cls:
            mock_cls.return_value = mock_client
            with patch("sqlite3.connect") as mock_sqlite:
                fetcher.get_latest_date_from_db(db_path=db_path, table_name="prices")

        mock_sqlite.assert_not_called()

    def test_正常系_最新日付を返す(self, tmp_path: Path) -> None:
        """テーブルにデータがある場合、最大日付をdatetimeで返すこと."""
        from database.db import DuckDBClient
        from market.bloomberg.fetcher import BloombergFetcher

        fetcher = BloombergFetcher()
        db_path = str(tmp_path / "bloomberg.duckdb")
        table_name = "prices"

        # Pre-populate the DuckDB with test data
        client = DuckDBClient(Path(db_path))
        df = pd.DataFrame(
            {
                "date": pd.to_datetime(["2024-01-10", "2024-02-15", "2024-03-20"]),
                "PX_LAST": [150.0, 155.0, 160.0],
            }
        )
        client.store_df(df, table_name, if_exists="replace")

        result = fetcher.get_latest_date_from_db(
            db_path=db_path,
            table_name=table_name,
            date_column="date",
        )

        assert result is not None
        assert isinstance(result, datetime)
        assert result.year == 2024
        assert result.month == 3
        assert result.day == 20

    def test_正常系_テーブルが空でNoneを返す(self, tmp_path: Path) -> None:
        """テーブルが空またはデータがない場合、Noneを返すこと."""
        from market.bloomberg.fetcher import BloombergFetcher

        fetcher = BloombergFetcher()
        db_path = str(tmp_path / "test.duckdb")

        mock_client = MagicMock()
        # Simulate empty result
        mock_client.query_df.return_value = pd.DataFrame({"max_date": [None]})

        with patch("market.bloomberg.fetcher.DuckDBClient") as mock_cls:
            mock_cls.return_value = mock_client
            result = fetcher.get_latest_date_from_db(
                db_path=db_path,
                table_name="prices",
            )

        assert result is None

    def test_正常系_デフォルトdate_columnがdateである(self, tmp_path: Path) -> None:
        """date_columnのデフォルト値が'date'であること."""
        from market.bloomberg.fetcher import BloombergFetcher

        fetcher = BloombergFetcher()
        db_path = str(tmp_path / "test.duckdb")

        mock_client = MagicMock()
        mock_client.query_df.return_value = pd.DataFrame({"max_date": [None]})

        with patch("market.bloomberg.fetcher.DuckDBClient") as mock_cls:
            mock_cls.return_value = mock_client
            # Call without date_column → should use default "date"
            fetcher.get_latest_date_from_db(db_path=db_path, table_name="prices")

        # Check the SQL query uses "date" as the column name
        call_args = mock_client.query_df.call_args
        assert call_args is not None
        sql_arg = call_args.args[0] if call_args.args else call_args[0][0]
        assert "date" in sql_arg.lower()

    def test_エッジケース_テーブル不存在でNoneを返す(self, tmp_path: Path) -> None:
        """テーブルが存在しない場合、Noneを返すこと（エラーを握り潰す）."""
        from market.bloomberg.fetcher import BloombergFetcher

        fetcher = BloombergFetcher()
        db_path = str(tmp_path / "test.duckdb")

        mock_client = MagicMock()
        # Simulate table not found → query_df raises an exception
        mock_client.query_df.side_effect = Exception("Table 'prices' does not exist")

        with patch("market.bloomberg.fetcher.DuckDBClient") as mock_cls:
            mock_cls.return_value = mock_client
            result = fetcher.get_latest_date_from_db(
                db_path=db_path,
                table_name="prices",
            )

        assert result is None
