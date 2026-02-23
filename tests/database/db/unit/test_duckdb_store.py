"""Unit tests for DuckDBClient store_df / get_table_names / _validate_identifier."""

from pathlib import Path

import pandas as pd
import pytest

from database.db.duckdb_client import DuckDBClient

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def client(duckdb_path: Path) -> DuckDBClient:
    """Return a fresh DuckDBClient backed by a temp file."""
    return DuckDBClient(duckdb_path)


@pytest.fixture
def simple_df() -> pd.DataFrame:
    """A small DataFrame used in most store_df tests."""
    return pd.DataFrame({"id": [1, 2, 3], "value": [10, 20, 30]})


# ---------------------------------------------------------------------------
# _validate_identifier
# ---------------------------------------------------------------------------


class TestValidateIdentifier:
    """Tests for DuckDBClient._validate_identifier()."""

    def test_正常系_英字のみのテーブル名を受け入れる(self) -> None:
        DuckDBClient._validate_identifier("prices")  # should not raise

    def test_正常系_英数字とアンダースコアを含むテーブル名を受け入れる(self) -> None:
        DuckDBClient._validate_identifier("stock_prices_2024")

    def test_正常系_アンダースコアで始まるテーブル名を受け入れる(self) -> None:
        DuckDBClient._validate_identifier("_internal_table")

    def test_異常系_数字で始まるテーブル名でValueErrorを送出する(self) -> None:
        with pytest.raises(ValueError, match="Invalid identifier"):
            DuckDBClient._validate_identifier("1prices")

    def test_異常系_ハイフンを含むテーブル名でValueErrorを送出する(self) -> None:
        with pytest.raises(ValueError, match="Invalid identifier"):
            DuckDBClient._validate_identifier("my-table")

    def test_異常系_セミコロンを含む名前でValueErrorを送出する(self) -> None:
        with pytest.raises(ValueError, match="Invalid identifier"):
            DuckDBClient._validate_identifier("prices; DROP TABLE prices")

    def test_異常系_スペースを含む名前でValueErrorを送出する(self) -> None:
        with pytest.raises(ValueError, match="Invalid identifier"):
            DuckDBClient._validate_identifier("my table")

    def test_異常系_空文字でValueErrorを送出する(self) -> None:
        with pytest.raises(ValueError, match="Invalid identifier"):
            DuckDBClient._validate_identifier("")

    def test_異常系_ドットを含む名前でValueErrorを送出する(self) -> None:
        with pytest.raises(ValueError, match="Invalid identifier"):
            DuckDBClient._validate_identifier("schema.table")


# ---------------------------------------------------------------------------
# get_table_names
# ---------------------------------------------------------------------------


class TestGetTableNames:
    """Tests for DuckDBClient.get_table_names()."""

    def test_正常系_テーブルなしで空リストを返す(self, client: DuckDBClient) -> None:
        names = client.get_table_names()
        assert names == []

    def test_正常系_1テーブル作成後にそのテーブル名を返す(
        self, client: DuckDBClient
    ) -> None:
        client.execute("CREATE TABLE foo (id INTEGER)")
        names = client.get_table_names()
        assert names == ["foo"]

    def test_正常系_複数テーブル作成後に全テーブル名を返す(
        self, client: DuckDBClient
    ) -> None:
        client.execute("CREATE TABLE foo (id INTEGER)")
        client.execute("CREATE TABLE bar (name VARCHAR)")
        names = client.get_table_names()
        assert sorted(names) == ["bar", "foo"]

    def test_正常系_戻り値がリストであること(self, client: DuckDBClient) -> None:
        names = client.get_table_names()
        assert isinstance(names, list)


# ---------------------------------------------------------------------------
# store_df — replace mode
# ---------------------------------------------------------------------------


class TestStoreDfReplace:
    """Tests for store_df() with if_exists='replace'."""

    def test_正常系_replaceモードで新規テーブルを作成できる(
        self, client: DuckDBClient, simple_df: pd.DataFrame
    ) -> None:
        client.store_df(simple_df, "prices", if_exists="replace")
        result = client.query_df("SELECT * FROM prices ORDER BY id")
        assert len(result) == 3
        assert list(result["id"]) == [1, 2, 3]

    def test_正常系_replaceモードで既存テーブルを全置換できる(
        self, client: DuckDBClient, simple_df: pd.DataFrame
    ) -> None:
        client.store_df(simple_df, "prices", if_exists="replace")
        new_df = pd.DataFrame({"id": [10, 20], "value": [100, 200]})
        client.store_df(new_df, "prices", if_exists="replace")
        result = client.query_df("SELECT * FROM prices ORDER BY id")
        assert len(result) == 2
        assert list(result["id"]) == [10, 20]

    def test_正常系_replaceモードで同じDataFrameを再度保存すると同じ行数になる(
        self, client: DuckDBClient, simple_df: pd.DataFrame
    ) -> None:
        client.store_df(simple_df, "prices", if_exists="replace")
        # Storing the same data again replaces the table with identical content
        client.store_df(simple_df, "prices", if_exists="replace")
        result = client.query_df("SELECT * FROM prices")
        assert len(result) == 3

    def test_正常系_replaceモードで新しいDataFrameでテーブルが置き換わる(
        self, client: DuckDBClient, simple_df: pd.DataFrame
    ) -> None:
        client.store_df(simple_df, "prices", if_exists="replace")
        new_df = pd.DataFrame({"id": [1, 4], "value": [10, 40]})
        client.store_df(new_df, "prices", if_exists="replace")
        result = client.query_df("SELECT * FROM prices ORDER BY id")
        # The table now contains only the new_df rows
        assert len(result) == 2
        assert list(result["id"]) == [1, 4]


# ---------------------------------------------------------------------------
# store_df — append mode
# ---------------------------------------------------------------------------


class TestStoreDfAppend:
    """Tests for store_df() with if_exists='append'."""

    def test_正常系_appendモードで新規テーブルを作成できる(
        self, client: DuckDBClient, simple_df: pd.DataFrame
    ) -> None:
        client.store_df(simple_df, "prices", if_exists="append")
        result = client.query_df("SELECT * FROM prices")
        assert len(result) == 3

    def test_正常系_appendモードで既存テーブルに行を追記できる(
        self, client: DuckDBClient, simple_df: pd.DataFrame
    ) -> None:
        client.store_df(simple_df, "prices", if_exists="append")
        extra_df = pd.DataFrame({"id": [4, 5], "value": [40, 50]})
        client.store_df(extra_df, "prices", if_exists="append")
        result = client.query_df("SELECT * FROM prices")
        assert len(result) == 5

    def test_正常系_appendモードで重複行も追記される(
        self, client: DuckDBClient, simple_df: pd.DataFrame
    ) -> None:
        client.store_df(simple_df, "prices", if_exists="append")
        client.store_df(simple_df, "prices", if_exists="append")
        result = client.query_df("SELECT * FROM prices")
        assert len(result) == 6


# ---------------------------------------------------------------------------
# store_df — upsert mode
# ---------------------------------------------------------------------------


class TestStoreDfUpsert:
    """Tests for store_df() with if_exists='upsert'."""

    def test_正常系_upsertモードで新規テーブルを作成できる(
        self, client: DuckDBClient, simple_df: pd.DataFrame
    ) -> None:
        client.store_df(simple_df, "prices", if_exists="upsert", key_columns=["id"])
        result = client.query_df("SELECT * FROM prices ORDER BY id")
        assert len(result) == 3

    def test_正常系_upsertモードでキー一致行を更新できる(
        self, client: DuckDBClient, simple_df: pd.DataFrame
    ) -> None:
        client.store_df(simple_df, "prices", if_exists="upsert", key_columns=["id"])
        updated_df = pd.DataFrame({"id": [1, 2], "value": [999, 888]})
        client.store_df(updated_df, "prices", if_exists="upsert", key_columns=["id"])
        result = client.query_df("SELECT value FROM prices WHERE id = 1")
        assert result["value"].iloc[0] == 999

    def test_正常系_upsertモードで重複行がない場合の総行数(
        self, client: DuckDBClient, simple_df: pd.DataFrame
    ) -> None:
        client.store_df(simple_df, "prices", if_exists="upsert", key_columns=["id"])
        result = client.query_df("SELECT * FROM prices")
        assert len(result) == 3

    def test_正常系_upsertモードで複合キーでの更新ができる(
        self, client: DuckDBClient
    ) -> None:
        df1 = pd.DataFrame(
            {
                "date": ["2024-01-01", "2024-01-02"],
                "ticker": ["AAPL", "AAPL"],
                "close": [100.0, 102.0],
            }
        )
        client.store_df(
            df1, "prices", if_exists="upsert", key_columns=["date", "ticker"]
        )
        df2 = pd.DataFrame(
            {"date": ["2024-01-01"], "ticker": ["AAPL"], "close": [999.0]}
        )
        client.store_df(
            df2, "prices", if_exists="upsert", key_columns=["date", "ticker"]
        )
        result = client.query_df(
            "SELECT close FROM prices WHERE date = '2024-01-01' AND ticker = 'AAPL'"
        )
        assert result["close"].iloc[0] == 999.0

    def test_異常系_upsertモードでkey_columnsなしでValueErrorを送出する(
        self, client: DuckDBClient, simple_df: pd.DataFrame
    ) -> None:
        with pytest.raises(ValueError, match="key_columns"):
            client.store_df(simple_df, "prices", if_exists="upsert")

    def test_異常系_upsertモードで空のkey_columnsでValueErrorを送出する(
        self, client: DuckDBClient, simple_df: pd.DataFrame
    ) -> None:
        with pytest.raises(ValueError, match="key_columns"):
            client.store_df(simple_df, "prices", if_exists="upsert", key_columns=[])


# ---------------------------------------------------------------------------
# store_df — validation / edge cases
# ---------------------------------------------------------------------------


class TestStoreDfValidation:
    """Tests for store_df() input validation and edge cases."""

    def test_異常系_不正なテーブル名でValueErrorを送出する(
        self, client: DuckDBClient, simple_df: pd.DataFrame
    ) -> None:
        with pytest.raises(ValueError, match="Invalid identifier"):
            client.store_df(simple_df, "1invalid", if_exists="replace")

    def test_異常系_upsertモードで不正なキーカラム名でValueErrorを送出する(
        self, client: DuckDBClient, simple_df: pd.DataFrame
    ) -> None:
        with pytest.raises(ValueError, match="Invalid identifier"):
            client.store_df(
                simple_df, "prices", if_exists="upsert", key_columns=["bad-col"]
            )

    def test_エッジケース_空のDataFrameでreplaceモードが動作する(
        self, client: DuckDBClient
    ) -> None:
        empty_df = pd.DataFrame(
            {"id": pd.Series([], dtype="int64"), "value": pd.Series([], dtype="int64")}
        )
        client.store_df(empty_df, "prices", if_exists="replace")
        result = client.query_df("SELECT * FROM prices")
        assert len(result) == 0

    def test_エッジケース_空のDataFrameでappendモードが動作する(
        self, client: DuckDBClient, simple_df: pd.DataFrame
    ) -> None:
        client.store_df(simple_df, "prices", if_exists="append")
        empty_df = pd.DataFrame(
            {"id": pd.Series([], dtype="int64"), "value": pd.Series([], dtype="int64")}
        )
        client.store_df(empty_df, "prices", if_exists="append")
        result = client.query_df("SELECT * FROM prices")
        assert len(result) == 3

    def test_正常系_store_df後にget_table_namesでテーブルが確認できる(
        self, client: DuckDBClient, simple_df: pd.DataFrame
    ) -> None:
        client.store_df(simple_df, "prices", if_exists="replace")
        names = client.get_table_names()
        assert "prices" in names
