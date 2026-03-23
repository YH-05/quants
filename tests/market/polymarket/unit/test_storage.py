"""Unit tests for the Polymarket storage layer.

Tests cover table creation, factory function, and basic introspection
methods of ``PolymarketStorage``.
"""

from pathlib import Path

import pytest

from market.polymarket.storage import (
    _TABLE_DDL,
    PolymarketStorage,
    get_polymarket_storage,
)
from market.polymarket.storage_constants import (
    TABLE_EVENTS,
    TABLE_LEADERBOARD_SNAPSHOTS,
    TABLE_MARKETS,
    TABLE_OI_SNAPSHOTS,
    TABLE_ORDERBOOK_SNAPSHOTS,
    TABLE_PRICE_HISTORY,
    TABLE_TOKENS,
    TABLE_TRADES,
)


class TestEnsureTables:
    """Tests for PolymarketStorage.ensure_tables()."""

    def test_正常系_全テーブルが作成される(self, pm_storage: PolymarketStorage) -> None:
        """ensure_tables() creates all 8 expected tables."""
        table_names = pm_storage.get_table_names()
        expected = sorted(
            [
                TABLE_EVENTS,
                TABLE_MARKETS,
                TABLE_TOKENS,
                TABLE_PRICE_HISTORY,
                TABLE_TRADES,
                TABLE_OI_SNAPSHOTS,
                TABLE_ORDERBOOK_SNAPSHOTS,
                TABLE_LEADERBOARD_SNAPSHOTS,
            ]
        )
        assert table_names == expected
        assert len(table_names) == 8

    def test_正常系_DDL定義が8テーブル分存在する(self) -> None:
        """_TABLE_DDL contains exactly 8 table definitions."""
        assert len(_TABLE_DDL) == 8

    def test_正常系_全テーブル名にpm_プレフィクスがある(self) -> None:
        """All table names start with 'pm_' prefix."""
        for table_name in _TABLE_DDL:
            assert table_name.startswith("pm_"), (
                f"Table name '{table_name}' does not start with 'pm_'"
            )

    def test_正常系_ensure_tablesは冪等に動作する(
        self, pm_storage: PolymarketStorage
    ) -> None:
        """Calling ensure_tables() multiple times does not raise errors."""
        # ensure_tables() is called once during __init__; call it again
        pm_storage.ensure_tables()
        pm_storage.ensure_tables()
        # Verify tables still exist correctly
        assert len(pm_storage.get_table_names()) == 8

    def test_正常系_各テーブルにCREATE_TABLE_IF_NOT_EXISTSが含まれる(
        self,
    ) -> None:
        """Each DDL statement uses CREATE TABLE IF NOT EXISTS."""
        for table_name, ddl in _TABLE_DDL.items():
            assert "CREATE TABLE IF NOT EXISTS" in ddl, (
                f"DDL for '{table_name}' missing CREATE TABLE IF NOT EXISTS"
            )


class TestGetStats:
    """Tests for PolymarketStorage.get_stats()."""

    def test_正常系_空のテーブルで全カウントがゼロ(
        self, pm_storage: PolymarketStorage
    ) -> None:
        """get_stats() returns 0 for all tables in a fresh database."""
        stats = pm_storage.get_stats()
        assert len(stats) == 8
        for table_name, count in stats.items():
            assert count == 0, f"Expected 0 rows for '{table_name}', got {count}"


class TestGetPolymarketStorage:
    """Tests for the get_polymarket_storage() factory function."""

    def test_正常系_ファクトリ関数が動作する(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """get_polymarket_storage() returns a valid PolymarketStorage."""
        db_path = tmp_path / "factory_test.db"
        monkeypatch.setenv("POLYMARKET_DB_PATH", str(db_path))
        storage = get_polymarket_storage()
        assert isinstance(storage, PolymarketStorage)
        assert len(storage.get_table_names()) == 8

    def test_正常系_環境変数でDBパスをオーバーライドできる(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """POLYMARKET_DB_PATH env var overrides the default path."""
        custom_path = tmp_path / "custom.db"
        monkeypatch.setenv("POLYMARKET_DB_PATH", str(custom_path))
        storage = get_polymarket_storage()
        assert isinstance(storage, PolymarketStorage)
        assert custom_path.exists()


class TestPolymarketStorageInit:
    """Tests for PolymarketStorage initialization."""

    def test_正常系_初期化時にテーブルが自動作成される(self, tmp_path: Path) -> None:
        """PolymarketStorage creates tables during __init__."""
        db_path = tmp_path / "init_test.db"
        storage = PolymarketStorage(db_path=db_path)
        assert len(storage.get_table_names()) == 8

    def test_正常系_DBファイルが作成される(self, tmp_path: Path) -> None:
        """PolymarketStorage creates the database file on disk."""
        db_path = tmp_path / "file_test.db"
        assert not db_path.exists()
        PolymarketStorage(db_path=db_path)
        assert db_path.exists()
