"""Unit tests for the Polymarket storage layer.

Tests cover table creation, factory function, basic introspection
methods, and upsert operations of ``PolymarketStorage``.
"""

from pathlib import Path

import pytest

from market.polymarket.models import PolymarketEvent, PolymarketMarket
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


# ============================================================================
# Helper fixtures for upsert tests
# ============================================================================

FETCHED_AT = "2026-03-23T00:00:00Z"


def _make_event(
    event_id: str = "evt-001",
    *,
    markets: list[PolymarketMarket] | None = None,
) -> PolymarketEvent:
    """Create a minimal PolymarketEvent for testing."""
    if markets is None:
        markets = []
    return PolymarketEvent(
        id=event_id,
        title=f"Event {event_id}",
        slug=f"event-{event_id}",
        markets=markets,
        description="Test event description",
        start_date="2026-01-01T00:00:00Z",
        end_date="2026-12-31T23:59:59Z",
        active=True,
        closed=False,
        volume=1000.0,
        liquidity=500.0,
    )


def _make_market(
    condition_id: str = "cond-001",
    *,
    tokens: list[dict] | None = None,
) -> PolymarketMarket:
    """Create a minimal PolymarketMarket for testing."""
    if tokens is None:
        tokens = [
            {"token_id": "tok-yes", "outcome": "Yes", "price": 0.65},
            {"token_id": "tok-no", "outcome": "No", "price": 0.35},
        ]
    return PolymarketMarket(
        condition_id=condition_id,
        question=f"Market {condition_id}?",
        tokens=tokens,
        description="Test market",
        end_date_iso="2026-12-31T23:59:59Z",
        active=True,
        closed=False,
        volume=800.0,
        liquidity=400.0,
    )


# ============================================================================
# UpsertEvents tests
# ============================================================================


class TestUpsertEvents:
    """Tests for PolymarketStorage.upsert_events()."""

    def test_正常系_イベントが保存される(self, pm_storage: PolymarketStorage) -> None:
        """upsert_events() inserts event rows into pm_events."""
        event = _make_event("evt-001")
        pm_storage.upsert_events([event], fetched_at=FETCHED_AT)

        stats = pm_storage.get_stats()
        assert stats[TABLE_EVENTS] == 1

    def test_正常系_複数イベントが保存される(
        self, pm_storage: PolymarketStorage
    ) -> None:
        """upsert_events() inserts multiple event rows."""
        events = [_make_event(f"evt-{i:03d}") for i in range(3)]
        pm_storage.upsert_events(events, fetched_at=FETCHED_AT)

        stats = pm_storage.get_stats()
        assert stats[TABLE_EVENTS] == 3

    def test_正常系_イベントとマーケットとトークンが連鎖保存される(
        self, pm_storage: PolymarketStorage
    ) -> None:
        """upsert_events() cascades to pm_markets and pm_tokens."""
        market = _make_market(
            "cond-001",
            tokens=[
                {"token_id": "tok-yes", "outcome": "Yes", "price": 0.65},
                {"token_id": "tok-no", "outcome": "No", "price": 0.35},
            ],
        )
        event = _make_event("evt-001", markets=[market])
        pm_storage.upsert_events([event], fetched_at=FETCHED_AT)

        stats = pm_storage.get_stats()
        assert stats[TABLE_EVENTS] == 1
        assert stats[TABLE_MARKETS] == 1
        assert stats[TABLE_TOKENS] == 2

    def test_エッジケース_空リストで何もしない(
        self, pm_storage: PolymarketStorage
    ) -> None:
        """upsert_events([]) is a no-op without errors."""
        pm_storage.upsert_events([], fetched_at=FETCHED_AT)
        stats = pm_storage.get_stats()
        assert stats[TABLE_EVENTS] == 0

    def test_正常系_同一データの重複upsertで上書き(
        self, pm_storage: PolymarketStorage
    ) -> None:
        """upsert_events() with duplicate IDs overwrites (idempotent)."""
        event = _make_event("evt-001")
        pm_storage.upsert_events([event], fetched_at=FETCHED_AT)
        # Upsert again with updated title
        event_v2 = _make_event("evt-001")
        pm_storage.upsert_events([event_v2], fetched_at="2026-03-24T00:00:00Z")

        stats = pm_storage.get_stats()
        assert stats[TABLE_EVENTS] == 1  # Not 2

    def test_正常系_マーケットのevent_idが設定される(
        self, pm_storage: PolymarketStorage
    ) -> None:
        """Markets saved via upsert_events() have their event_id set."""
        market = _make_market("cond-001")
        event = _make_event("evt-001", markets=[market])
        pm_storage.upsert_events([event], fetched_at=FETCHED_AT)

        rows = pm_storage._client.execute(
            f"SELECT event_id FROM {TABLE_MARKETS} WHERE condition_id = 'cond-001'"
        )
        assert len(rows) == 1
        assert rows[0]["event_id"] == "evt-001"


# ============================================================================
# UpsertMarkets tests
# ============================================================================


class TestUpsertMarkets:
    """Tests for PolymarketStorage.upsert_markets()."""

    def test_正常系_マーケットが保存される(self, pm_storage: PolymarketStorage) -> None:
        """upsert_markets() inserts market rows into pm_markets."""
        market = _make_market("cond-001")
        pm_storage.upsert_markets([market], fetched_at=FETCHED_AT)

        stats = pm_storage.get_stats()
        assert stats[TABLE_MARKETS] == 1

    def test_正常系_マーケットとトークンが連鎖保存される(
        self, pm_storage: PolymarketStorage
    ) -> None:
        """upsert_markets() cascades token upsert to pm_tokens."""
        market = _make_market(
            "cond-001",
            tokens=[
                {"token_id": "tok-yes", "outcome": "Yes", "price": 0.65},
                {"token_id": "tok-no", "outcome": "No", "price": 0.35},
            ],
        )
        pm_storage.upsert_markets([market], fetched_at=FETCHED_AT)

        stats = pm_storage.get_stats()
        assert stats[TABLE_MARKETS] == 1
        assert stats[TABLE_TOKENS] == 2

    def test_正常系_event_idが指定できる(self, pm_storage: PolymarketStorage) -> None:
        """upsert_markets() with event_id sets the foreign key."""
        market = _make_market("cond-001")
        pm_storage.upsert_markets([market], fetched_at=FETCHED_AT, event_id="evt-001")

        rows = pm_storage._client.execute(
            f"SELECT event_id FROM {TABLE_MARKETS} WHERE condition_id = 'cond-001'"
        )
        assert rows[0]["event_id"] == "evt-001"

    def test_エッジケース_空リストで何もしない(
        self, pm_storage: PolymarketStorage
    ) -> None:
        """upsert_markets([]) is a no-op without errors."""
        pm_storage.upsert_markets([], fetched_at=FETCHED_AT)
        stats = pm_storage.get_stats()
        assert stats[TABLE_MARKETS] == 0

    def test_正常系_同一データの重複upsertで上書き(
        self, pm_storage: PolymarketStorage
    ) -> None:
        """upsert_markets() with duplicate condition_id overwrites."""
        market = _make_market("cond-001")
        pm_storage.upsert_markets([market], fetched_at=FETCHED_AT)
        pm_storage.upsert_markets([market], fetched_at="2026-03-24T00:00:00Z")

        stats = pm_storage.get_stats()
        assert stats[TABLE_MARKETS] == 1

    def test_正常系_トークンにtoken_idがない場合はスキップ(
        self, pm_storage: PolymarketStorage
    ) -> None:
        """Tokens without token_id are safely skipped."""
        market = _make_market(
            "cond-001",
            tokens=[
                {"outcome": "Yes", "price": 0.65},  # Missing token_id
                {"token_id": "tok-no", "outcome": "No", "price": 0.35},
            ],
        )
        pm_storage.upsert_markets([market], fetched_at=FETCHED_AT)

        stats = pm_storage.get_stats()
        assert stats[TABLE_TOKENS] == 1  # Only tok-no saved

    def test_正常系_トークンにoutcomeがない場合はスキップ(
        self, pm_storage: PolymarketStorage
    ) -> None:
        """Tokens without outcome are safely skipped."""
        market = _make_market(
            "cond-001",
            tokens=[
                {"token_id": "tok-yes", "price": 0.65},  # Missing outcome
                {"token_id": "tok-no", "outcome": "No", "price": 0.35},
            ],
        )
        pm_storage.upsert_markets([market], fetched_at=FETCHED_AT)

        stats = pm_storage.get_stats()
        assert stats[TABLE_TOKENS] == 1  # Only tok-no saved

    def test_正常系_複数マーケットが保存される(
        self, pm_storage: PolymarketStorage
    ) -> None:
        """upsert_markets() handles multiple markets correctly."""
        markets = [_make_market(f"cond-{i:03d}") for i in range(3)]
        pm_storage.upsert_markets(markets, fetched_at=FETCHED_AT)

        stats = pm_storage.get_stats()
        assert stats[TABLE_MARKETS] == 3
