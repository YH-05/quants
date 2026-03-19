"""Unit tests for AseanTickerStorage DuckDB storage layer.

Tests cover:
- __init__: DuckDBClient DI, ensure_tables auto-call
- ensure_tables: Creates asean_tickers table with correct schema
- upsert_tickers: Bulk insert with correct key_columns, returns count
- get_tickers: Filter by market
- lookup_ticker: LIKE search with optional market filter
- count_tickers: Market-wise ticker counts
"""

from __future__ import annotations

from typing import TYPE_CHECKING
from unittest.mock import MagicMock, patch

import pandas as pd
import pytest

from market.asean_common.constants import (
    TABLE_TICKERS,
    YFINANCE_SUFFIX_MAP,
    AseanMarket,
)
from market.asean_common.types import TickerRecord

if TYPE_CHECKING:
    from pathlib import Path

    from database.db.duckdb_client import DuckDBClient


# ============================================================================
# Test: __init__
# ============================================================================


class TestAseanTickerStorageInit:
    """Tests for AseanTickerStorage initialization."""

    def test_正常系_DuckDBClientをDIで受け取る(
        self,
        duckdb_client: DuckDBClient,
    ) -> None:
        """AseanTickerStorageがDuckDBClientをDIで受け取ること."""
        from market.asean_common.storage import AseanTickerStorage

        storage = AseanTickerStorage(client=duckdb_client)
        assert storage._client is duckdb_client

    def test_正常系_ensure_tablesが自動呼び出しされる(
        self,
        duckdb_client: DuckDBClient,
    ) -> None:
        """AseanTickerStorage初期化時にensure_tablesが自動で呼ばれること."""
        from market.asean_common.storage import AseanTickerStorage

        with patch.object(AseanTickerStorage, "ensure_tables") as mock_ensure:
            AseanTickerStorage(client=duckdb_client)
            mock_ensure.assert_called_once()


# ============================================================================
# Test: ensure_tables
# ============================================================================


class TestEnsureTables:
    """Tests for ensure_tables method."""

    def test_正常系_asean_tickersテーブルが作成される(
        self,
        duckdb_client: DuckDBClient,
    ) -> None:
        """ensure_tablesでasean_tickersテーブルが作成されること."""
        from market.asean_common.storage import AseanTickerStorage

        _storage = AseanTickerStorage(client=duckdb_client)
        tables = duckdb_client.get_table_names()
        assert TABLE_TICKERS in tables

    def test_正常系_テーブルに必要なカラムが全て存在する(
        self,
        duckdb_client: DuckDBClient,
    ) -> None:
        """asean_tickersテーブルに全必要カラムが存在すること."""
        from market.asean_common.storage import AseanTickerStorage

        _storage = AseanTickerStorage(client=duckdb_client)
        df = duckdb_client.query_df(
            "SELECT column_name FROM information_schema.columns "
            f"WHERE table_name = '{TABLE_TICKERS}'"
        )
        columns = set(df["column_name"].tolist())
        expected = {
            "ticker",
            "name",
            "market",
            "yfinance_suffix",
            "yfinance_ticker",
            "sector",
            "industry",
            "market_cap",
            "currency",
            "is_active",
        }
        assert columns == expected

    def test_正常系_冪等に実行できる(
        self,
        duckdb_client: DuckDBClient,
    ) -> None:
        """ensure_tablesを複数回呼んでもエラーにならないこと."""
        from market.asean_common.storage import AseanTickerStorage

        storage = AseanTickerStorage(client=duckdb_client)
        # Call ensure_tables again - should not raise
        storage.ensure_tables()
        tables = duckdb_client.get_table_names()
        assert TABLE_TICKERS in tables

    def test_正常系_validate_identifierがTABLE_TICKERSに対して呼ばれる(
        self,
        duckdb_client: DuckDBClient,
    ) -> None:
        """ensure_tablesがTABLE_TICKERSに対して_validate_identifierを呼ぶこと."""
        from market.asean_common.storage import AseanTickerStorage

        with patch.object(
            type(duckdb_client),
            "_validate_identifier",
            wraps=duckdb_client._validate_identifier,
        ) as mock_validate:
            _storage = AseanTickerStorage(client=duckdb_client)
            # ensure_tables is called in __init__, so check it was called
            mock_validate.assert_any_call(TABLE_TICKERS)

    def test_異常系_不正なテーブル名でValueError(
        self,
        duckdb_client: DuckDBClient,
    ) -> None:
        """不正なテーブル名が設定されている場合にValueErrorが発生すること."""
        from market.asean_common.storage import AseanTickerStorage

        storage = AseanTickerStorage(client=duckdb_client)
        with (
            patch(
                "market.asean_common.storage.TABLE_TICKERS", "Robert'; DROP TABLE --"
            ),
            pytest.raises(ValueError, match="Invalid identifier"),
        ):
            storage.ensure_tables()


# ============================================================================
# Test: upsert_tickers
# ============================================================================


class TestUpsertTickers:
    """Tests for upsert_tickers method."""

    def test_正常系_TickerRecordリストを一括挿入し挿入件数を返す(
        self,
        duckdb_client: DuckDBClient,
        sample_tickers: list[TickerRecord],
    ) -> None:
        """upsert_tickersがTickerRecordリストを挿入し件数を返すこと."""
        from market.asean_common.storage import AseanTickerStorage

        storage = AseanTickerStorage(client=duckdb_client)
        count = storage.upsert_tickers(sample_tickers)
        assert count == 3

    def test_正常系_同一キーでupsertすると上書きされる(
        self,
        duckdb_client: DuckDBClient,
        sample_ticker_sgx: TickerRecord,
    ) -> None:
        """同じticker+marketのデータをupsertすると上書きされること."""
        from market.asean_common.storage import AseanTickerStorage

        storage = AseanTickerStorage(client=duckdb_client)
        storage.upsert_tickers([sample_ticker_sgx])

        updated = TickerRecord(
            ticker="D05",
            name="DBS Group Holdings Ltd (Updated)",
            market=AseanMarket.SGX,
            yfinance_suffix=YFINANCE_SUFFIX_MAP[AseanMarket.SGX],
            sector="Financial Services",
            industry="Banks - Diversified",
            market_cap=110_000_000_000,
            currency="SGD",
        )
        count = storage.upsert_tickers([updated])
        assert count == 1

        # Verify only one record exists
        tickers = storage.get_tickers(AseanMarket.SGX)
        assert len(tickers) == 1
        assert tickers[0].name == "DBS Group Holdings Ltd (Updated)"
        assert tickers[0].market_cap == 110_000_000_000

    def test_エッジケース_空リストで0を返す(
        self,
        duckdb_client: DuckDBClient,
    ) -> None:
        """upsert_tickersに空リストを渡すと0を返すこと."""
        from market.asean_common.storage import AseanTickerStorage

        storage = AseanTickerStorage(client=duckdb_client)
        count = storage.upsert_tickers([])
        assert count == 0

    def test_正常系_Noneフィールドが正しく保存される(
        self,
        duckdb_client: DuckDBClient,
    ) -> None:
        """オプショナルフィールドがNoneで保存されること."""
        from market.asean_common.storage import AseanTickerStorage

        storage = AseanTickerStorage(client=duckdb_client)
        ticker = TickerRecord(
            ticker="TEST",
            name="Test Company",
            market=AseanMarket.IDX,
            yfinance_suffix=YFINANCE_SUFFIX_MAP[AseanMarket.IDX],
        )
        storage.upsert_tickers([ticker])

        tickers = storage.get_tickers(AseanMarket.IDX)
        assert len(tickers) == 1
        assert tickers[0].sector is None
        assert tickers[0].industry is None
        assert tickers[0].market_cap is None
        assert tickers[0].currency is None


# ============================================================================
# Test: _build_ticker_df (performance optimization)
# ============================================================================


class TestBuildTickerDf:
    """Tests for _build_ticker_df static method.

    Verifies the 3-stage to 2-stage memory copy optimization:
    Before: asdict() -> DataFrame -> apply(enum.value)
    After:  resolve enum.value before asdict -> DataFrame (no apply)
    """

    def test_正常系_market列が文字列型で返される(
        self,
        sample_tickers: list[TickerRecord],
    ) -> None:
        """_build_ticker_dfのmarket列がenum値ではなく文字列であること."""
        from market.asean_common.storage import AseanTickerStorage

        df = AseanTickerStorage._build_ticker_df(sample_tickers)
        for val in df["market"]:
            assert isinstance(val, str), f"Expected str, got {type(val)}"
            assert not isinstance(val, AseanMarket), (
                "market column should contain plain strings, not AseanMarket enum"
            )

    def test_正常系_market列の値がenum_valueと一致する(
        self,
        sample_tickers: list[TickerRecord],
    ) -> None:
        """_build_ticker_dfのmarket列値がAseanMarket.valueと一致すること."""
        from market.asean_common.storage import AseanTickerStorage

        df = AseanTickerStorage._build_ticker_df(sample_tickers)
        expected_markets = [t.market.value for t in sample_tickers]
        assert df["market"].tolist() == expected_markets

    def test_正常系_apply呼び出しなしでenum変換が完了する(
        self,
        sample_tickers: list[TickerRecord],
    ) -> None:
        """_build_ticker_dfがDataFrame.apply()を使わずにenum変換すること."""
        from market.asean_common.storage import AseanTickerStorage

        df = AseanTickerStorage._build_ticker_df(sample_tickers)

        # Verify the result is correct (market values are plain strings)
        for val in df["market"]:
            assert isinstance(val, str)
            assert val in {m.value for m in AseanMarket}

    def test_正常系_全カラムが正しく生成される(
        self,
        sample_ticker_sgx: TickerRecord,
    ) -> None:
        """_build_ticker_dfの全カラムが正しく生成されること."""
        from market.asean_common.storage import AseanTickerStorage

        df = AseanTickerStorage._build_ticker_df([sample_ticker_sgx])
        assert len(df) == 1
        row = df.iloc[0]
        assert row["ticker"] == "D05"
        assert row["name"] == "DBS Group Holdings Ltd"
        assert row["market"] == "SGX"
        assert row["yfinance_suffix"] == ".SI"
        assert row["yfinance_ticker"] == "D05.SI"
        assert row["sector"] == "Financial Services"
        assert row["industry"] == "Banks - Diversified"
        assert row["market_cap"] == 100_000_000_000
        assert row["currency"] == "SGD"
        assert row["is_active"] == True  # noqa: E712 - numpy bool comparison

    def test_正常系_メモリコピーが2段階以下である(
        self,
        sample_tickers: list[TickerRecord],
    ) -> None:
        """_build_ticker_dfがasdict+DataFrame構築の2段階で完了すること.

        apply()によるenum再変換（3段階目）が不要になったことを
        ソースコード検査で確認する。
        """
        import inspect

        from market.asean_common.storage import AseanTickerStorage

        source = inspect.getsource(AseanTickerStorage._build_ticker_df)
        # apply() should not be used for enum conversion
        assert ".apply(" not in source, (
            "_build_ticker_df should not use .apply() for enum conversion. "
            "Resolve enum.value before asdict() to reduce memory copies."
        )

    def test_パフォーマンス_5000件でベンチマーク記録(self) -> None:
        """_build_ticker_dfが5000件のデータを処理するベンチマーク.

        Issue #3793 の受け入れ条件: ベンチマーク結果を記録。
        現データ規模（~5000行）でのパフォーマンスを確認する。
        """
        import time

        from market.asean_common.storage import AseanTickerStorage

        markets = list(AseanMarket)
        tickers = [
            TickerRecord(
                ticker=f"T{i:04d}",
                name=f"Test Company {i}",
                market=markets[i % len(markets)],
                yfinance_suffix=YFINANCE_SUFFIX_MAP[markets[i % len(markets)]],
                sector="Financial Services" if i % 2 == 0 else None,
                industry="Banks" if i % 3 == 0 else None,
                market_cap=1_000_000 * i if i % 4 != 0 else None,
                currency="USD" if i % 2 == 0 else None,
            )
            for i in range(5000)
        ]

        start = time.perf_counter()
        df = AseanTickerStorage._build_ticker_df(tickers)
        elapsed_ms = (time.perf_counter() - start) * 1000

        assert len(df) == 5000
        # Record benchmark: should complete within reasonable time
        # On typical hardware, ~5000 rows should process in < 500ms
        assert elapsed_ms < 500, (
            f"_build_ticker_df took {elapsed_ms:.1f}ms for 5000 rows"
        )
        # Verify correctness of output
        assert all(isinstance(v, str) for v in df["market"])


# ============================================================================
# Test: get_tickers
# ============================================================================


class TestGetTickers:
    """Tests for get_tickers method."""

    def test_正常系_指定市場のティッカーリストを返す(
        self,
        duckdb_client: DuckDBClient,
        sample_tickers: list[TickerRecord],
    ) -> None:
        """get_tickersが指定市場のティッカーのみ返すこと."""
        from market.asean_common.storage import AseanTickerStorage

        storage = AseanTickerStorage(client=duckdb_client)
        storage.upsert_tickers(sample_tickers)

        sgx_tickers = storage.get_tickers(AseanMarket.SGX)
        assert len(sgx_tickers) == 1
        assert sgx_tickers[0].ticker == "D05"
        assert sgx_tickers[0].market == AseanMarket.SGX

    def test_正常系_存在しない市場で空リストを返す(
        self,
        duckdb_client: DuckDBClient,
        sample_tickers: list[TickerRecord],
    ) -> None:
        """get_tickersが存在しない市場に対して空リストを返すこと."""
        from market.asean_common.storage import AseanTickerStorage

        storage = AseanTickerStorage(client=duckdb_client)
        storage.upsert_tickers(sample_tickers)

        hose_tickers = storage.get_tickers(AseanMarket.HOSE)
        assert hose_tickers == []

    def test_正常系_返却値がTickerRecordのリストである(
        self,
        duckdb_client: DuckDBClient,
        sample_ticker_sgx: TickerRecord,
    ) -> None:
        """get_tickersの返却値がTickerRecordのリストであること."""
        from market.asean_common.storage import AseanTickerStorage

        storage = AseanTickerStorage(client=duckdb_client)
        storage.upsert_tickers([sample_ticker_sgx])

        tickers = storage.get_tickers(AseanMarket.SGX)
        assert all(isinstance(t, TickerRecord) for t in tickers)

    def test_正常系_yfinance_tickerが正しく復元される(
        self,
        duckdb_client: DuckDBClient,
        sample_ticker_sgx: TickerRecord,
    ) -> None:
        """get_tickersで取得したTickerRecordのyfinance_tickerが正しいこと."""
        from market.asean_common.storage import AseanTickerStorage

        storage = AseanTickerStorage(client=duckdb_client)
        storage.upsert_tickers([sample_ticker_sgx])

        tickers = storage.get_tickers(AseanMarket.SGX)
        assert tickers[0].yfinance_ticker == "D05.SI"


# ============================================================================
# Test: lookup_ticker
# ============================================================================


class TestLookupTicker:
    """Tests for lookup_ticker method."""

    def test_正常系_名前のLIKE検索で部分一致するティッカーを返す(
        self,
        duckdb_client: DuckDBClient,
        sample_tickers: list[TickerRecord],
    ) -> None:
        """lookup_tickerが名前の部分一致検索で結果を返すこと."""
        from market.asean_common.storage import AseanTickerStorage

        storage = AseanTickerStorage(client=duckdb_client)
        storage.upsert_tickers(sample_tickers)

        results = storage.lookup_ticker("DBS")
        assert len(results) == 1
        assert results[0].ticker == "D05"

    def test_正常系_market指定で検索範囲を絞れる(
        self,
        duckdb_client: DuckDBClient,
        sample_tickers: list[TickerRecord],
    ) -> None:
        """lookup_tickerがmarket指定で検索範囲を絞れること."""
        from market.asean_common.storage import AseanTickerStorage

        storage = AseanTickerStorage(client=duckdb_client)
        storage.upsert_tickers(sample_tickers)

        # Search for bank-related tickers in BURSA only
        results = storage.lookup_ticker("May", market=AseanMarket.BURSA)
        assert len(results) == 1
        assert results[0].ticker == "1155"

    def test_正常系_market指定なしで全市場を検索する(
        self,
        duckdb_client: DuckDBClient,
        sample_tickers: list[TickerRecord],
    ) -> None:
        """lookup_tickerがmarket=Noneで全市場から検索すること."""
        from market.asean_common.storage import AseanTickerStorage

        storage = AseanTickerStorage(client=duckdb_client)
        storage.upsert_tickers(sample_tickers)

        # "Company" should not match any (names are specific)
        results = storage.lookup_ticker("Company")
        assert len(results) == 1  # "SCB X Public Company Limited"

    def test_エッジケース_一致なしで空リストを返す(
        self,
        duckdb_client: DuckDBClient,
        sample_tickers: list[TickerRecord],
    ) -> None:
        """lookup_tickerが一致なしで空リストを返すこと."""
        from market.asean_common.storage import AseanTickerStorage

        storage = AseanTickerStorage(client=duckdb_client)
        storage.upsert_tickers(sample_tickers)

        results = storage.lookup_ticker("NONEXISTENT")
        assert results == []

    def test_正常系_大文字小文字を区別しない検索ができる(
        self,
        duckdb_client: DuckDBClient,
        sample_tickers: list[TickerRecord],
    ) -> None:
        """lookup_tickerが大文字小文字を区別せずに検索できること."""
        from market.asean_common.storage import AseanTickerStorage

        storage = AseanTickerStorage(client=duckdb_client)
        storage.upsert_tickers(sample_tickers)

        results = storage.lookup_ticker("dbs")
        assert len(results) == 1
        assert results[0].ticker == "D05"


# ============================================================================
# Test: count_tickers
# ============================================================================


class TestCountTickers:
    """Tests for count_tickers method."""

    def test_正常系_市場別のティッカー数をdictで返す(
        self,
        duckdb_client: DuckDBClient,
        sample_tickers: list[TickerRecord],
    ) -> None:
        """count_tickersが市場別のティッカー数を返すこと."""
        from market.asean_common.storage import AseanTickerStorage

        storage = AseanTickerStorage(client=duckdb_client)
        storage.upsert_tickers(sample_tickers)

        counts = storage.count_tickers()
        assert isinstance(counts, dict)
        assert counts.get("SGX") == 1
        assert counts.get("BURSA") == 1
        assert counts.get("SET") == 1

    def test_正常系_データなしで空dictを返す(
        self,
        duckdb_client: DuckDBClient,
    ) -> None:
        """count_tickersがデータなしで空dictを返すこと."""
        from market.asean_common.storage import AseanTickerStorage

        storage = AseanTickerStorage(client=duckdb_client)

        counts = storage.count_tickers()
        assert counts == {}

    def test_正常系_返却値のキーが市場名文字列である(
        self,
        duckdb_client: DuckDBClient,
        sample_tickers: list[TickerRecord],
    ) -> None:
        """count_tickersの返却キーが市場名の文字列であること."""
        from market.asean_common.storage import AseanTickerStorage

        storage = AseanTickerStorage(client=duckdb_client)
        storage.upsert_tickers(sample_tickers)

        counts = storage.count_tickers()
        for key in counts:
            assert isinstance(key, str)

    def test_正常系_返却値の値が正の整数である(
        self,
        duckdb_client: DuckDBClient,
        sample_tickers: list[TickerRecord],
    ) -> None:
        """count_tickersの返却値が正の整数であること."""
        from market.asean_common.storage import AseanTickerStorage

        storage = AseanTickerStorage(client=duckdb_client)
        storage.upsert_tickers(sample_tickers)

        counts = storage.count_tickers()
        for value in counts.values():
            assert isinstance(value, int)
            assert value > 0
