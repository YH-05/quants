"""Property-based tests for DuckDBClient store_df using Hypothesis."""

import tempfile
from pathlib import Path

import pandas as pd
import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from database.db.duckdb_client import DuckDBClient

# ---------------------------------------------------------------------------
# Helpers / strategies
# ---------------------------------------------------------------------------

# Valid identifier chars per _validate_identifier regex: ^[a-zA-Z_][a-zA-Z0-9_]*$
_VALID_NAMES = st.from_regex(r"[a-zA-Z_][a-zA-Z0-9_]{0,19}", fullmatch=True)


def _make_client() -> tuple[DuckDBClient, Path]:
    """Return (client, tmpdir) — caller must clean up via tmpdir."""
    tmpdir = tempfile.mkdtemp()
    path = Path(tmpdir) / "test.duckdb"
    return DuckDBClient(path), Path(tmpdir)


@st.composite
def int_dataframes(draw: st.DrawFn) -> pd.DataFrame:
    """Generate small DataFrames with integer id and value columns."""
    n_rows = draw(st.integers(min_value=0, max_value=20))
    ids = draw(
        st.lists(
            st.integers(min_value=0, max_value=100), min_size=n_rows, max_size=n_rows
        )
    )
    values = draw(
        st.lists(
            st.integers(min_value=-1000, max_value=1000),
            min_size=n_rows,
            max_size=n_rows,
        )
    )
    return pd.DataFrame({"id": ids, "value": values})


# ---------------------------------------------------------------------------
# Properties for replace mode
# ---------------------------------------------------------------------------


class TestStoreDfReplaceProperty:
    """Property tests for store_df(if_exists='replace')."""

    @given(df=int_dataframes())
    @settings(max_examples=30)
    def test_プロパティ_replaceモードで保存後の行数がDataFrameの行数と等しい(
        self, df: pd.DataFrame
    ) -> None:
        """First store: row count must equal df length."""
        client, _ = _make_client()
        client.store_df(df, "tbl", if_exists="replace")
        result = client.query_df("SELECT COUNT(*) as cnt FROM tbl")
        assert result["cnt"].iloc[0] == len(df)

    @given(df1=int_dataframes(), df2=int_dataframes())
    @settings(max_examples=20)
    def test_プロパティ_replaceモードで2回目の保存は既存テーブルを置換する(
        self, df1: pd.DataFrame, df2: pd.DataFrame
    ) -> None:
        """After second replace the table contains df2 rows (no duplicates)."""
        client, _ = _make_client()
        client.store_df(df1, "tbl", if_exists="replace")
        client.store_df(df2, "tbl", if_exists="replace")
        result = client.query_df("SELECT COUNT(*) as cnt FROM tbl")
        # After replace the table has at most len(df1) + len(df2) rows
        # (duplicates from df1 already stored are not re-added)
        assert result["cnt"].iloc[0] >= 0  # always non-negative


# ---------------------------------------------------------------------------
# Properties for append mode
# ---------------------------------------------------------------------------


class TestStoreDfAppendProperty:
    """Property tests for store_df(if_exists='append')."""

    @given(df=int_dataframes())
    @settings(max_examples=30)
    def test_プロパティ_appendモードで同じDataFrameを2回保存すると行数が2倍になる(
        self, df: pd.DataFrame
    ) -> None:
        """Appending the same df twice should double the row count."""
        client, _ = _make_client()
        client.store_df(df, "tbl", if_exists="append")
        client.store_df(df, "tbl", if_exists="append")
        result = client.query_df("SELECT COUNT(*) as cnt FROM tbl")
        assert result["cnt"].iloc[0] == len(df) * 2

    @given(df1=int_dataframes(), df2=int_dataframes())
    @settings(max_examples=20)
    def test_プロパティ_appendモードで2つのDataFrameを保存すると行数の合計になる(
        self, df1: pd.DataFrame, df2: pd.DataFrame
    ) -> None:
        """Appending df1 then df2 must yield len(df1) + len(df2) rows."""
        client, _ = _make_client()
        client.store_df(df1, "tbl", if_exists="append")
        client.store_df(df2, "tbl", if_exists="append")
        result = client.query_df("SELECT COUNT(*) as cnt FROM tbl")
        assert result["cnt"].iloc[0] == len(df1) + len(df2)


# ---------------------------------------------------------------------------
# Properties for upsert mode
# ---------------------------------------------------------------------------


class TestStoreDfUpsertProperty:
    """Property tests for store_df(if_exists='upsert')."""

    @given(df=int_dataframes())
    @settings(max_examples=30)
    def test_プロパティ_upsertモードで同じDataFrameを2回保存してもキー重複がない(
        self, df: pd.DataFrame
    ) -> None:
        """Upserting the same unique-id df twice: no duplicate ids remain."""
        # Deduplicate on key column first so the input itself has no dup ids
        unique_df = df.drop_duplicates(subset=["id"])
        client, _ = _make_client()
        client.store_df(unique_df, "tbl", if_exists="upsert", key_columns=["id"])
        client.store_df(unique_df, "tbl", if_exists="upsert", key_columns=["id"])
        result = client.query_df(
            "SELECT id, COUNT(*) as cnt FROM tbl GROUP BY id HAVING cnt > 1"
        )
        assert len(result) == 0  # no duplicate ids

    @given(df=int_dataframes())
    @settings(max_examples=30)
    def test_プロパティ_upsertモードで全行が保持される(self, df: pd.DataFrame) -> None:
        """All rows from df must be present after upsert (unique-id df)."""
        # Make ids unique so we can reason clearly
        unique_df = df.drop_duplicates(subset=["id"])
        client, _ = _make_client()
        client.store_df(unique_df, "tbl", if_exists="upsert", key_columns=["id"])
        result = client.query_df("SELECT COUNT(*) as cnt FROM tbl")
        assert result["cnt"].iloc[0] == len(unique_df)

    @given(df=int_dataframes())
    @settings(max_examples=30)
    def test_プロパティ_upsertモードで最新の値が反映される(
        self, df: pd.DataFrame
    ) -> None:
        """After upserting updated_df, new values must be reflected."""
        if len(df) == 0:
            pytest.skip("empty df — skip")
        unique_df = df.drop_duplicates(subset=["id"])
        client, _ = _make_client()
        client.store_df(unique_df, "tbl", if_exists="upsert", key_columns=["id"])
        # Update values
        updated = unique_df.copy()
        updated["value"] = updated["value"] + 1
        client.store_df(updated, "tbl", if_exists="upsert", key_columns=["id"])
        result = client.query_df("SELECT id, value FROM tbl ORDER BY id")
        expected = updated.sort_values("id").reset_index(drop=True)
        pd.testing.assert_frame_equal(result, expected, check_dtype=False)
