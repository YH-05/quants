"""Unit tests for the Polymarket storage layer.

Tests cover table creation, factory function, basic introspection
methods, and upsert operations of ``PolymarketStorage``.
"""

import json
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd
import pytest

from market.polymarket.models import (
    OrderBook,
    OrderBookLevel,
    PolymarketEvent,
    PolymarketMarket,
    PricePoint,
    TradeRecord,
)
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
from market.polymarket.types import PriceInterval


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


# ============================================================================
# UpsertPriceHistory tests
# ============================================================================


class TestUpsertPriceHistory:
    """Tests for PolymarketStorage.upsert_price_history()."""

    def test_正常系_価格履歴が保存される(self, pm_storage: PolymarketStorage) -> None:
        """upsert_price_history() inserts price rows into pm_price_history."""
        prices = [
            PricePoint(t=1700000000, p=0.65),
            PricePoint(t=1700003600, p=0.70),
        ]
        pm_storage.upsert_price_history(
            token_id="tok-yes",
            prices=prices,
            interval=PriceInterval.ONE_HOUR,
            fetched_at=FETCHED_AT,
        )

        stats = pm_storage.get_stats()
        assert stats[TABLE_PRICE_HISTORY] == 2

    def test_正常系_保存データの内容が正しい(
        self, pm_storage: PolymarketStorage
    ) -> None:
        """upsert_price_history() stores correct token_id, timestamp, interval, price."""
        prices = [PricePoint(t=1700000000, p=0.65)]
        pm_storage.upsert_price_history(
            token_id="tok-yes",
            prices=prices,
            interval=PriceInterval.ONE_DAY,
            fetched_at=FETCHED_AT,
        )

        rows = pm_storage._client.execute(
            f"SELECT token_id, timestamp, interval, price, fetched_at "
            f"FROM {TABLE_PRICE_HISTORY}"
        )
        assert len(rows) == 1
        row = rows[0]
        assert row["token_id"] == "tok-yes"
        assert row["timestamp"] == 1700000000
        assert row["interval"] == "1d"
        assert row["price"] == pytest.approx(0.65)
        assert row["fetched_at"] == FETCHED_AT

    def test_エッジケース_空リストで何もしない(
        self, pm_storage: PolymarketStorage
    ) -> None:
        """upsert_price_history([]) is a no-op without errors."""
        pm_storage.upsert_price_history(
            token_id="tok-yes",
            prices=[],
            interval=PriceInterval.ONE_HOUR,
            fetched_at=FETCHED_AT,
        )

        stats = pm_storage.get_stats()
        assert stats[TABLE_PRICE_HISTORY] == 0

    def test_正常系_重複タイムスタンプで上書き(
        self, pm_storage: PolymarketStorage
    ) -> None:
        """upsert_price_history() with duplicate PK overwrites (idempotent)."""
        prices_v1 = [PricePoint(t=1700000000, p=0.65)]
        pm_storage.upsert_price_history(
            token_id="tok-yes",
            prices=prices_v1,
            interval=PriceInterval.ONE_HOUR,
            fetched_at=FETCHED_AT,
        )

        # Upsert again with updated price
        prices_v2 = [PricePoint(t=1700000000, p=0.80)]
        pm_storage.upsert_price_history(
            token_id="tok-yes",
            prices=prices_v2,
            interval=PriceInterval.ONE_HOUR,
            fetched_at="2026-03-24T00:00:00Z",
        )

        stats = pm_storage.get_stats()
        assert stats[TABLE_PRICE_HISTORY] == 1  # Not 2

        # Verify the price was updated
        rows = pm_storage._client.execute(
            f"SELECT price, fetched_at FROM {TABLE_PRICE_HISTORY} "
            f"WHERE token_id = 'tok-yes' AND timestamp = 1700000000"
        )
        assert rows[0]["price"] == pytest.approx(0.80)
        assert rows[0]["fetched_at"] == "2026-03-24T00:00:00Z"

    def test_正常系_異なるインターバルは別レコード(
        self, pm_storage: PolymarketStorage
    ) -> None:
        """Same token_id+timestamp with different intervals are separate rows."""
        prices = [PricePoint(t=1700000000, p=0.65)]
        pm_storage.upsert_price_history(
            token_id="tok-yes",
            prices=prices,
            interval=PriceInterval.ONE_HOUR,
            fetched_at=FETCHED_AT,
        )
        pm_storage.upsert_price_history(
            token_id="tok-yes",
            prices=prices,
            interval=PriceInterval.ONE_DAY,
            fetched_at=FETCHED_AT,
        )

        stats = pm_storage.get_stats()
        assert stats[TABLE_PRICE_HISTORY] == 2

    def test_正常系_複数トークンの価格履歴が保存される(
        self, pm_storage: PolymarketStorage
    ) -> None:
        """upsert_price_history() handles different token_ids correctly."""
        prices = [PricePoint(t=1700000000, p=0.65)]
        pm_storage.upsert_price_history(
            token_id="tok-yes",
            prices=prices,
            interval=PriceInterval.ONE_HOUR,
            fetched_at=FETCHED_AT,
        )
        pm_storage.upsert_price_history(
            token_id="tok-no",
            prices=prices,
            interval=PriceInterval.ONE_HOUR,
            fetched_at=FETCHED_AT,
        )

        stats = pm_storage.get_stats()
        assert stats[TABLE_PRICE_HISTORY] == 2

    def test_正常系_大量の価格データが保存される(
        self, pm_storage: PolymarketStorage
    ) -> None:
        """upsert_price_history() handles a large batch of price points."""
        prices = [
            PricePoint(t=1700000000 + i * 3600, p=0.50 + i * 0.01) for i in range(100)
        ]
        pm_storage.upsert_price_history(
            token_id="tok-yes",
            prices=prices,
            interval=PriceInterval.ONE_HOUR,
            fetched_at=FETCHED_AT,
        )

        stats = pm_storage.get_stats()
        assert stats[TABLE_PRICE_HISTORY] == 100


# ============================================================================
# Helper factories for Wave 2 tests
# ============================================================================


def _make_trade(
    trade_id: str = "trade-001",
    *,
    market: str = "cond-001",
    asset_id: str = "asset-001",
    price: float = 0.65,
    size: float = 500.0,
    side: str | None = "BUY",
    timestamp: datetime | None = datetime(2026, 3, 23, 12, 0, 0, tzinfo=timezone.utc),
) -> TradeRecord:
    """Create a minimal TradeRecord for testing."""
    return TradeRecord(
        id=trade_id,
        market=market,
        asset_id=asset_id,
        price=price,
        size=size,
        side=side,
        timestamp=timestamp,
    )


def _make_orderbook(
    condition_id: str = "cond-001",
    asset_id: str = "asset-001",
) -> OrderBook:
    """Create a minimal OrderBook for testing."""
    return OrderBook(
        market=condition_id,
        asset_id=asset_id,
        bids=[OrderBookLevel(price=0.50, size=100.0)],
        asks=[OrderBookLevel(price=0.55, size=200.0)],
    )


# ============================================================================
# UpsertTrades tests
# ============================================================================


class TestUpsertTrades:
    """Tests for PolymarketStorage.upsert_trades()."""

    def test_正常系_トレードが保存される(self, pm_storage: PolymarketStorage) -> None:
        """upsert_trades() inserts trade rows into pm_trades."""
        trade = _make_trade("trade-001")
        pm_storage.upsert_trades([trade], fetched_at=FETCHED_AT)

        stats = pm_storage.get_stats()
        assert stats[TABLE_TRADES] == 1

    def test_正常系_複数トレードが保存される(
        self, pm_storage: PolymarketStorage
    ) -> None:
        """upsert_trades() inserts multiple trade rows."""
        trades = [_make_trade(f"trade-{i:03d}") for i in range(5)]
        pm_storage.upsert_trades(trades, fetched_at=FETCHED_AT)

        stats = pm_storage.get_stats()
        assert stats[TABLE_TRADES] == 5

    def test_正常系_保存データの内容が正しい(
        self, pm_storage: PolymarketStorage
    ) -> None:
        """upsert_trades() stores correct field values."""
        trade = _make_trade(
            "trade-001",
            market="cond-abc",
            asset_id="asset-xyz",
            price=0.72,
            size=1000.0,
            side="SELL",
            timestamp=datetime(2026, 3, 23, 15, 30, 0, tzinfo=timezone.utc),
        )
        pm_storage.upsert_trades([trade], fetched_at=FETCHED_AT)

        rows = pm_storage._client.execute(f"SELECT * FROM {TABLE_TRADES}")
        assert len(rows) == 1
        row = rows[0]
        assert row["id"] == "trade-001"
        assert row["market"] == "cond-abc"
        assert row["asset_id"] == "asset-xyz"
        assert row["price"] == pytest.approx(0.72)
        assert row["size"] == pytest.approx(1000.0)
        assert row["side"] == "SELL"
        assert row["timestamp"] == "2026-03-23T15:30:00+00:00"
        assert row["fetched_at"] == FETCHED_AT

    def test_正常系_同一IDの重複upsertで上書き(
        self, pm_storage: PolymarketStorage
    ) -> None:
        """upsert_trades() with duplicate trade ID overwrites (idempotent)."""
        trade_v1 = _make_trade("trade-001", price=0.50)
        pm_storage.upsert_trades([trade_v1], fetched_at=FETCHED_AT)

        trade_v2 = _make_trade("trade-001", price=0.75)
        pm_storage.upsert_trades([trade_v2], fetched_at="2026-03-24T00:00:00Z")

        stats = pm_storage.get_stats()
        assert stats[TABLE_TRADES] == 1

        rows = pm_storage._client.execute(
            f"SELECT price FROM {TABLE_TRADES} WHERE id = 'trade-001'"
        )
        assert rows[0]["price"] == pytest.approx(0.75)

    def test_エッジケース_空リストで何もしない(
        self, pm_storage: PolymarketStorage
    ) -> None:
        """upsert_trades([]) is a no-op without errors."""
        pm_storage.upsert_trades([], fetched_at=FETCHED_AT)
        stats = pm_storage.get_stats()
        assert stats[TABLE_TRADES] == 0

    def test_正常系_sideがNoneでも保存される(
        self, pm_storage: PolymarketStorage
    ) -> None:
        """upsert_trades() handles None side correctly."""
        trade = _make_trade("trade-001", side=None)
        pm_storage.upsert_trades([trade], fetched_at=FETCHED_AT)

        rows = pm_storage._client.execute(f"SELECT side FROM {TABLE_TRADES}")
        assert rows[0]["side"] is None


# ============================================================================
# InsertOiSnapshot tests
# ============================================================================


class TestInsertOiSnapshot:
    """Tests for PolymarketStorage.insert_oi_snapshot()."""

    def test_正常系_OIスナップショットが保存される(
        self, pm_storage: PolymarketStorage
    ) -> None:
        """insert_oi_snapshot() inserts a row into pm_oi_snapshots."""
        data = {"open_interest": 15000.0, "volume_24h": 5000.0}
        pm_storage.insert_oi_snapshot("cond-001", data, fetched_at=FETCHED_AT)

        stats = pm_storage.get_stats()
        assert stats[TABLE_OI_SNAPSHOTS] == 1

    def test_正常系_JSONデータが正しく保存される(
        self, pm_storage: PolymarketStorage
    ) -> None:
        """insert_oi_snapshot() stores data as JSON string in data_json."""
        data = {"open_interest": 15000.0, "tokens": ["tok-yes", "tok-no"]}
        pm_storage.insert_oi_snapshot("cond-001", data, fetched_at=FETCHED_AT)

        rows = pm_storage._client.execute(
            f"SELECT condition_id, fetched_at, data_json FROM {TABLE_OI_SNAPSHOTS}"
        )
        assert len(rows) == 1
        row = rows[0]
        assert row["condition_id"] == "cond-001"
        assert row["fetched_at"] == FETCHED_AT
        parsed = json.loads(row["data_json"])
        assert parsed["open_interest"] == 15000.0
        assert parsed["tokens"] == ["tok-yes", "tok-no"]

    def test_正常系_同一PKの重複insertで上書き(
        self, pm_storage: PolymarketStorage
    ) -> None:
        """insert_oi_snapshot() with same PK overwrites (idempotent)."""
        data_v1 = {"open_interest": 10000.0}
        pm_storage.insert_oi_snapshot("cond-001", data_v1, fetched_at=FETCHED_AT)

        data_v2 = {"open_interest": 20000.0}
        pm_storage.insert_oi_snapshot("cond-001", data_v2, fetched_at=FETCHED_AT)

        stats = pm_storage.get_stats()
        assert stats[TABLE_OI_SNAPSHOTS] == 1

        rows = pm_storage._client.execute(f"SELECT data_json FROM {TABLE_OI_SNAPSHOTS}")
        parsed = json.loads(rows[0]["data_json"])
        assert parsed["open_interest"] == 20000.0

    def test_正常系_異なるfetched_atは別レコード(
        self, pm_storage: PolymarketStorage
    ) -> None:
        """Different fetched_at for same condition_id creates separate rows."""
        data = {"open_interest": 15000.0}
        pm_storage.insert_oi_snapshot("cond-001", data, fetched_at=FETCHED_AT)
        pm_storage.insert_oi_snapshot(
            "cond-001", data, fetched_at="2026-03-24T00:00:00Z"
        )

        stats = pm_storage.get_stats()
        assert stats[TABLE_OI_SNAPSHOTS] == 2


# ============================================================================
# InsertOrderbookSnapshot tests
# ============================================================================


class TestInsertOrderbookSnapshot:
    """Tests for PolymarketStorage.insert_orderbook_snapshot()."""

    def test_正常系_注文板スナップショットが保存される(
        self, pm_storage: PolymarketStorage
    ) -> None:
        """insert_orderbook_snapshot() inserts a row into pm_orderbook_snapshots."""
        orderbook = _make_orderbook("cond-001")
        pm_storage.insert_orderbook_snapshot(orderbook, fetched_at=FETCHED_AT)

        stats = pm_storage.get_stats()
        assert stats[TABLE_ORDERBOOK_SNAPSHOTS] == 1

    def test_正常系_JSONデータが正しく保存される(
        self, pm_storage: PolymarketStorage
    ) -> None:
        """insert_orderbook_snapshot() stores orderbook as JSON in data_json."""
        orderbook = _make_orderbook("cond-001", "asset-xyz")
        pm_storage.insert_orderbook_snapshot(orderbook, fetched_at=FETCHED_AT)

        rows = pm_storage._client.execute(
            f"SELECT condition_id, data_json FROM {TABLE_ORDERBOOK_SNAPSHOTS}"
        )
        assert len(rows) == 1
        assert rows[0]["condition_id"] == "cond-001"
        parsed = json.loads(rows[0]["data_json"])
        assert parsed["market"] == "cond-001"
        assert parsed["asset_id"] == "asset-xyz"
        assert len(parsed["bids"]) == 1
        assert len(parsed["asks"]) == 1

    def test_正常系_同一PKの重複insertで上書き(
        self, pm_storage: PolymarketStorage
    ) -> None:
        """insert_orderbook_snapshot() with same PK overwrites (idempotent)."""
        orderbook = _make_orderbook("cond-001")
        pm_storage.insert_orderbook_snapshot(orderbook, fetched_at=FETCHED_AT)
        pm_storage.insert_orderbook_snapshot(orderbook, fetched_at=FETCHED_AT)

        stats = pm_storage.get_stats()
        assert stats[TABLE_ORDERBOOK_SNAPSHOTS] == 1

    def test_正常系_異なるfetched_atは別レコード(
        self, pm_storage: PolymarketStorage
    ) -> None:
        """Different fetched_at for same condition_id creates separate rows."""
        orderbook = _make_orderbook("cond-001")
        pm_storage.insert_orderbook_snapshot(orderbook, fetched_at=FETCHED_AT)
        pm_storage.insert_orderbook_snapshot(
            orderbook, fetched_at="2026-03-24T00:00:00Z"
        )

        stats = pm_storage.get_stats()
        assert stats[TABLE_ORDERBOOK_SNAPSHOTS] == 2


# ============================================================================
# InsertLeaderboardSnapshot tests
# ============================================================================


class TestInsertLeaderboardSnapshot:
    """Tests for PolymarketStorage.insert_leaderboard_snapshot()."""

    def test_正常系_リーダーボードスナップショットが保存される(
        self, pm_storage: PolymarketStorage
    ) -> None:
        """insert_leaderboard_snapshot() inserts a row into pm_leaderboard_snapshots."""
        entries = [
            {"rank": 1, "user": "alice", "profit": 50000.0},
            {"rank": 2, "user": "bob", "profit": 30000.0},
        ]
        pm_storage.insert_leaderboard_snapshot(entries, fetched_at=FETCHED_AT)

        stats = pm_storage.get_stats()
        assert stats[TABLE_LEADERBOARD_SNAPSHOTS] == 1

    def test_正常系_JSONデータが正しく保存される(
        self, pm_storage: PolymarketStorage
    ) -> None:
        """insert_leaderboard_snapshot() stores entries as JSON in data_json."""
        entries = [
            {"rank": 1, "user": "alice", "profit": 50000.0},
        ]
        pm_storage.insert_leaderboard_snapshot(entries, fetched_at=FETCHED_AT)

        rows = pm_storage._client.execute(
            f"SELECT fetched_at, data_json FROM {TABLE_LEADERBOARD_SNAPSHOTS}"
        )
        assert len(rows) == 1
        assert rows[0]["fetched_at"] == FETCHED_AT
        parsed = json.loads(rows[0]["data_json"])
        assert len(parsed) == 1
        assert parsed[0]["rank"] == 1
        assert parsed[0]["user"] == "alice"

    def test_正常系_同一fetched_atの重複insertで上書き(
        self, pm_storage: PolymarketStorage
    ) -> None:
        """insert_leaderboard_snapshot() with same fetched_at overwrites."""
        entries_v1 = [{"rank": 1, "user": "alice"}]
        pm_storage.insert_leaderboard_snapshot(entries_v1, fetched_at=FETCHED_AT)

        entries_v2 = [{"rank": 1, "user": "bob"}]
        pm_storage.insert_leaderboard_snapshot(entries_v2, fetched_at=FETCHED_AT)

        stats = pm_storage.get_stats()
        assert stats[TABLE_LEADERBOARD_SNAPSHOTS] == 1

        rows = pm_storage._client.execute(
            f"SELECT data_json FROM {TABLE_LEADERBOARD_SNAPSHOTS}"
        )
        parsed = json.loads(rows[0]["data_json"])
        assert parsed[0]["user"] == "bob"

    def test_正常系_異なるfetched_atは別レコード(
        self, pm_storage: PolymarketStorage
    ) -> None:
        """Different fetched_at creates separate leaderboard snapshots."""
        entries = [{"rank": 1, "user": "alice"}]
        pm_storage.insert_leaderboard_snapshot(entries, fetched_at=FETCHED_AT)
        pm_storage.insert_leaderboard_snapshot(
            entries, fetched_at="2026-03-24T00:00:00Z"
        )

        stats = pm_storage.get_stats()
        assert stats[TABLE_LEADERBOARD_SNAPSHOTS] == 2


# ============================================================================
# UpsertHolders tests
# ============================================================================


class TestUpsertHolders:
    """Tests for PolymarketStorage.upsert_holders()."""

    def test_正常系_ホルダーが保存される(self, pm_storage: PolymarketStorage) -> None:
        """upsert_holders() updates holders_json in pm_markets."""
        # First, insert a market row
        market = _make_market("cond-001")
        pm_storage.upsert_markets([market], fetched_at=FETCHED_AT)

        holders = [
            {"address": "0xabc", "shares": 1000},
            {"address": "0xdef", "shares": 500},
        ]
        pm_storage.upsert_holders("cond-001", holders)

        rows = pm_storage._client.execute(
            f"SELECT holders_json FROM {TABLE_MARKETS} WHERE condition_id = 'cond-001'"
        )
        assert rows[0]["holders_json"] is not None
        parsed = json.loads(rows[0]["holders_json"])
        assert len(parsed) == 2
        assert parsed[0]["address"] == "0xabc"
        assert parsed[1]["shares"] == 500

    def test_正常系_冪等に動作する(self, pm_storage: PolymarketStorage) -> None:
        """upsert_holders() is idempotent -- same data produces same result."""
        market = _make_market("cond-001")
        pm_storage.upsert_markets([market], fetched_at=FETCHED_AT)

        holders = [{"address": "0xabc", "shares": 1000}]
        pm_storage.upsert_holders("cond-001", holders)
        pm_storage.upsert_holders("cond-001", holders)

        rows = pm_storage._client.execute(
            f"SELECT holders_json FROM {TABLE_MARKETS} WHERE condition_id = 'cond-001'"
        )
        parsed = json.loads(rows[0]["holders_json"])
        assert len(parsed) == 1

    def test_正常系_ホルダーが更新される(self, pm_storage: PolymarketStorage) -> None:
        """upsert_holders() overwrites previous holders data."""
        market = _make_market("cond-001")
        pm_storage.upsert_markets([market], fetched_at=FETCHED_AT)

        holders_v1 = [{"address": "0xabc", "shares": 1000}]
        pm_storage.upsert_holders("cond-001", holders_v1)

        holders_v2 = [{"address": "0xdef", "shares": 2000}]
        pm_storage.upsert_holders("cond-001", holders_v2)

        rows = pm_storage._client.execute(
            f"SELECT holders_json FROM {TABLE_MARKETS} WHERE condition_id = 'cond-001'"
        )
        parsed = json.loads(rows[0]["holders_json"])
        assert len(parsed) == 1
        assert parsed[0]["address"] == "0xdef"

    def test_正常系_空リストでNULL化(self, pm_storage: PolymarketStorage) -> None:
        """upsert_holders() with empty list stores empty JSON array."""
        market = _make_market("cond-001")
        pm_storage.upsert_markets([market], fetched_at=FETCHED_AT)

        pm_storage.upsert_holders("cond-001", [])

        rows = pm_storage._client.execute(
            f"SELECT holders_json FROM {TABLE_MARKETS} WHERE condition_id = 'cond-001'"
        )
        parsed = json.loads(rows[0]["holders_json"])
        assert parsed == []

    def test_エッジケース_存在しないcondition_idは影響なし(
        self, pm_storage: PolymarketStorage
    ) -> None:
        """upsert_holders() for non-existent condition_id updates zero rows."""
        holders = [{"address": "0xabc", "shares": 1000}]
        # Should not raise -- UPDATE simply affects 0 rows
        pm_storage.upsert_holders("non-existent", holders)

        stats = pm_storage.get_stats()
        assert stats[TABLE_MARKETS] == 0


# ============================================================================
# Wave 3: Query method tests
# ============================================================================


class TestGetEvents:
    """Tests for PolymarketStorage.get_events()."""

    def test_正常系_全イベントを取得する(self, pm_storage: PolymarketStorage) -> None:
        """get_events() returns all events as a DataFrame."""
        events = [_make_event(f"evt-{i:03d}") for i in range(3)]
        pm_storage.upsert_events(events, fetched_at=FETCHED_AT)

        df = pm_storage.get_events()
        assert isinstance(df, pd.DataFrame)
        assert len(df) == 3

    def test_正常系_active_onlyでアクティブイベントのみ取得(
        self, pm_storage: PolymarketStorage
    ) -> None:
        """get_events(active_only=True) returns only active events."""
        active_event = _make_event("evt-active")
        inactive_event = PolymarketEvent(
            id="evt-inactive",
            title="Inactive Event",
            slug="inactive-event",
            markets=[],
            active=False,
            closed=True,
        )
        pm_storage.upsert_events([active_event, inactive_event], fetched_at=FETCHED_AT)

        df = pm_storage.get_events(active_only=True)
        assert len(df) == 1
        assert df.iloc[0]["id"] == "evt-active"

    def test_正常系_active_only_Falseで全イベント取得(
        self, pm_storage: PolymarketStorage
    ) -> None:
        """get_events(active_only=False) returns all events including inactive."""
        active_event = _make_event("evt-active")
        inactive_event = PolymarketEvent(
            id="evt-inactive",
            title="Inactive Event",
            slug="inactive-event",
            markets=[],
            active=False,
            closed=True,
        )
        pm_storage.upsert_events([active_event, inactive_event], fetched_at=FETCHED_AT)

        df = pm_storage.get_events(active_only=False)
        assert len(df) == 2

    def test_エッジケース_空テーブルで空DataFrame(
        self, pm_storage: PolymarketStorage
    ) -> None:
        """get_events() returns empty DataFrame when table is empty."""
        df = pm_storage.get_events()
        assert isinstance(df, pd.DataFrame)
        assert len(df) == 0

    def test_正常系_DataFrameのカラムが正しい(
        self, pm_storage: PolymarketStorage
    ) -> None:
        """get_events() DataFrame has expected columns."""
        event = _make_event("evt-001")
        pm_storage.upsert_events([event], fetched_at=FETCHED_AT)

        df = pm_storage.get_events()
        expected_columns = {
            "id",
            "title",
            "slug",
            "description",
            "start_date",
            "end_date",
            "active",
            "closed",
            "volume",
            "liquidity",
            "fetched_at",
        }
        assert expected_columns.issubset(set(df.columns))


class TestGetMarkets:
    """Tests for PolymarketStorage.get_markets()."""

    def test_正常系_全マーケットを取得する(self, pm_storage: PolymarketStorage) -> None:
        """get_markets() returns all markets as a DataFrame."""
        markets = [_make_market(f"cond-{i:03d}") for i in range(3)]
        pm_storage.upsert_markets(markets, fetched_at=FETCHED_AT)

        df = pm_storage.get_markets()
        assert isinstance(df, pd.DataFrame)
        assert len(df) == 3

    def test_正常系_event_idでフィルタリング(
        self, pm_storage: PolymarketStorage
    ) -> None:
        """get_markets(event_id=...) returns only markets for that event."""
        market1 = _make_market("cond-001")
        market2 = _make_market("cond-002")
        pm_storage.upsert_markets([market1], fetched_at=FETCHED_AT, event_id="evt-001")
        pm_storage.upsert_markets([market2], fetched_at=FETCHED_AT, event_id="evt-002")

        df = pm_storage.get_markets(event_id="evt-001")
        assert len(df) == 1
        assert df.iloc[0]["condition_id"] == "cond-001"

    def test_正常系_active_onlyでアクティブマーケットのみ取得(
        self, pm_storage: PolymarketStorage
    ) -> None:
        """get_markets(active_only=True) returns only active markets."""
        active_market = _make_market("cond-active")
        inactive_market = PolymarketMarket(
            condition_id="cond-inactive",
            question="Inactive Market?",
            tokens=[],
            active=False,
            closed=True,
        )
        pm_storage.upsert_markets(
            [active_market, inactive_market], fetched_at=FETCHED_AT
        )

        df = pm_storage.get_markets(active_only=True)
        assert len(df) == 1
        assert df.iloc[0]["condition_id"] == "cond-active"

    def test_正常系_event_idとactive_onlyの組み合わせ(
        self, pm_storage: PolymarketStorage
    ) -> None:
        """get_markets(event_id=..., active_only=True) applies both filters."""
        active_in_evt1 = _make_market("cond-001")
        inactive_in_evt1 = PolymarketMarket(
            condition_id="cond-002",
            question="Inactive in evt-001?",
            tokens=[],
            active=False,
            closed=True,
        )
        active_in_evt2 = _make_market("cond-003")
        pm_storage.upsert_markets(
            [active_in_evt1, inactive_in_evt1],
            fetched_at=FETCHED_AT,
            event_id="evt-001",
        )
        pm_storage.upsert_markets(
            [active_in_evt2], fetched_at=FETCHED_AT, event_id="evt-002"
        )

        df = pm_storage.get_markets(event_id="evt-001", active_only=True)
        assert len(df) == 1
        assert df.iloc[0]["condition_id"] == "cond-001"

    def test_エッジケース_空テーブルで空DataFrame(
        self, pm_storage: PolymarketStorage
    ) -> None:
        """get_markets() returns empty DataFrame when table is empty."""
        df = pm_storage.get_markets()
        assert isinstance(df, pd.DataFrame)
        assert len(df) == 0

    def test_エッジケース_存在しないevent_idで空DataFrame(
        self, pm_storage: PolymarketStorage
    ) -> None:
        """get_markets(event_id=...) returns empty DataFrame for unknown event."""
        market = _make_market("cond-001")
        pm_storage.upsert_markets([market], fetched_at=FETCHED_AT, event_id="evt-001")

        df = pm_storage.get_markets(event_id="evt-nonexistent")
        assert len(df) == 0


class TestGetTokens:
    """Tests for PolymarketStorage.get_tokens()."""

    def test_正常系_condition_idでトークンを取得(
        self, pm_storage: PolymarketStorage
    ) -> None:
        """get_tokens(condition_id) returns tokens for that market."""
        market = _make_market(
            "cond-001",
            tokens=[
                {"token_id": "tok-yes", "outcome": "Yes", "price": 0.65},
                {"token_id": "tok-no", "outcome": "No", "price": 0.35},
            ],
        )
        pm_storage.upsert_markets([market], fetched_at=FETCHED_AT)

        df = pm_storage.get_tokens("cond-001")
        assert isinstance(df, pd.DataFrame)
        assert len(df) == 2

    def test_正常系_異なるcondition_idのトークンは含まれない(
        self, pm_storage: PolymarketStorage
    ) -> None:
        """get_tokens() only returns tokens for the specified condition_id."""
        market1 = _make_market(
            "cond-001",
            tokens=[{"token_id": "tok-1", "outcome": "Yes", "price": 0.65}],
        )
        market2 = _make_market(
            "cond-002",
            tokens=[{"token_id": "tok-2", "outcome": "No", "price": 0.35}],
        )
        pm_storage.upsert_markets([market1, market2], fetched_at=FETCHED_AT)

        df = pm_storage.get_tokens("cond-001")
        assert len(df) == 1
        assert df.iloc[0]["token_id"] == "tok-1"

    def test_エッジケース_空テーブルで空DataFrame(
        self, pm_storage: PolymarketStorage
    ) -> None:
        """get_tokens() returns empty DataFrame when no tokens exist."""
        df = pm_storage.get_tokens("cond-nonexistent")
        assert isinstance(df, pd.DataFrame)
        assert len(df) == 0


class TestGetPriceHistory:
    """Tests for PolymarketStorage.get_price_history()."""

    def test_正常系_token_idで価格履歴を取得(
        self, pm_storage: PolymarketStorage
    ) -> None:
        """get_price_history(token_id) returns price data as DataFrame."""
        prices = [
            PricePoint(t=1700000000, p=0.65),
            PricePoint(t=1700003600, p=0.70),
        ]
        pm_storage.upsert_price_history(
            token_id="tok-yes",
            prices=prices,
            interval=PriceInterval.ONE_HOUR,
            fetched_at=FETCHED_AT,
        )

        df = pm_storage.get_price_history("tok-yes")
        assert isinstance(df, pd.DataFrame)
        assert len(df) == 2

    def test_正常系_intervalでフィルタリング(
        self, pm_storage: PolymarketStorage
    ) -> None:
        """get_price_history(token_id, interval=...) filters by interval."""
        prices = [PricePoint(t=1700000000, p=0.65)]
        pm_storage.upsert_price_history(
            token_id="tok-yes",
            prices=prices,
            interval=PriceInterval.ONE_HOUR,
            fetched_at=FETCHED_AT,
        )
        pm_storage.upsert_price_history(
            token_id="tok-yes",
            prices=prices,
            interval=PriceInterval.ONE_DAY,
            fetched_at=FETCHED_AT,
        )

        df = pm_storage.get_price_history("tok-yes", interval=PriceInterval.ONE_HOUR)
        assert len(df) == 1
        assert df.iloc[0]["interval"] == "1h"

    def test_正常系_interval指定なしで全インターバル取得(
        self, pm_storage: PolymarketStorage
    ) -> None:
        """get_price_history(token_id) without interval returns all intervals."""
        prices = [PricePoint(t=1700000000, p=0.65)]
        pm_storage.upsert_price_history(
            token_id="tok-yes",
            prices=prices,
            interval=PriceInterval.ONE_HOUR,
            fetched_at=FETCHED_AT,
        )
        pm_storage.upsert_price_history(
            token_id="tok-yes",
            prices=prices,
            interval=PriceInterval.ONE_DAY,
            fetched_at=FETCHED_AT,
        )

        df = pm_storage.get_price_history("tok-yes")
        assert len(df) == 2

    def test_エッジケース_空テーブルで空DataFrame(
        self, pm_storage: PolymarketStorage
    ) -> None:
        """get_price_history() returns empty DataFrame when no data exists."""
        df = pm_storage.get_price_history("tok-nonexistent")
        assert isinstance(df, pd.DataFrame)
        assert len(df) == 0


class TestGetTrades:
    """Tests for PolymarketStorage.get_trades()."""

    def test_正常系_condition_idでトレードを取得(
        self, pm_storage: PolymarketStorage
    ) -> None:
        """get_trades(condition_id) returns trades for that market."""
        trades = [
            _make_trade("trade-001", market="cond-001"),
            _make_trade("trade-002", market="cond-001"),
        ]
        pm_storage.upsert_trades(trades, fetched_at=FETCHED_AT)

        df = pm_storage.get_trades("cond-001")
        assert isinstance(df, pd.DataFrame)
        assert len(df) == 2

    def test_正常系_limitでレコード数を制限(
        self, pm_storage: PolymarketStorage
    ) -> None:
        """get_trades(condition_id, limit=N) returns at most N rows."""
        trades = [_make_trade(f"trade-{i:03d}", market="cond-001") for i in range(10)]
        pm_storage.upsert_trades(trades, fetched_at=FETCHED_AT)

        df = pm_storage.get_trades("cond-001", limit=3)
        assert len(df) == 3

    def test_正常系_異なるcondition_idのトレードは含まれない(
        self, pm_storage: PolymarketStorage
    ) -> None:
        """get_trades() only returns trades for the specified condition_id."""
        trades = [
            _make_trade("trade-001", market="cond-001"),
            _make_trade("trade-002", market="cond-002"),
        ]
        pm_storage.upsert_trades(trades, fetched_at=FETCHED_AT)

        df = pm_storage.get_trades("cond-001")
        assert len(df) == 1

    def test_エッジケース_空テーブルで空DataFrame(
        self, pm_storage: PolymarketStorage
    ) -> None:
        """get_trades() returns empty DataFrame when no trades exist."""
        df = pm_storage.get_trades("cond-nonexistent")
        assert isinstance(df, pd.DataFrame)
        assert len(df) == 0

    def test_正常系_limit指定なしで全トレード取得(
        self, pm_storage: PolymarketStorage
    ) -> None:
        """get_trades(condition_id) without limit returns all trades."""
        trades = [_make_trade(f"trade-{i:03d}", market="cond-001") for i in range(5)]
        pm_storage.upsert_trades(trades, fetched_at=FETCHED_AT)

        df = pm_storage.get_trades("cond-001")
        assert len(df) == 5


class TestGetOiSnapshots:
    """Tests for PolymarketStorage.get_oi_snapshots()."""

    def test_正常系_condition_idでOIスナップショットを取得(
        self, pm_storage: PolymarketStorage
    ) -> None:
        """get_oi_snapshots(condition_id) returns snapshots as DataFrame."""
        data = {"open_interest": 15000.0}
        pm_storage.insert_oi_snapshot("cond-001", data, fetched_at=FETCHED_AT)
        pm_storage.insert_oi_snapshot(
            "cond-001", data, fetched_at="2026-03-24T00:00:00Z"
        )

        df = pm_storage.get_oi_snapshots("cond-001")
        assert isinstance(df, pd.DataFrame)
        assert len(df) == 2

    def test_正常系_異なるcondition_idのスナップショットは含まれない(
        self, pm_storage: PolymarketStorage
    ) -> None:
        """get_oi_snapshots() only returns snapshots for the specified condition_id."""
        data = {"open_interest": 15000.0}
        pm_storage.insert_oi_snapshot("cond-001", data, fetched_at=FETCHED_AT)
        pm_storage.insert_oi_snapshot("cond-002", data, fetched_at=FETCHED_AT)

        df = pm_storage.get_oi_snapshots("cond-001")
        assert len(df) == 1

    def test_エッジケース_空テーブルで空DataFrame(
        self, pm_storage: PolymarketStorage
    ) -> None:
        """get_oi_snapshots() returns empty DataFrame when no data exists."""
        df = pm_storage.get_oi_snapshots("cond-nonexistent")
        assert isinstance(df, pd.DataFrame)
        assert len(df) == 0


class TestCountRecords:
    """Tests for PolymarketStorage.count_records()."""

    def test_正常系_全テーブルのレコード数を返す(
        self, pm_storage: PolymarketStorage
    ) -> None:
        """count_records() returns record counts for all tables."""
        # Insert some data
        event = _make_event("evt-001", markets=[_make_market("cond-001")])
        pm_storage.upsert_events([event], fetched_at=FETCHED_AT)

        result = pm_storage.count_records()
        assert isinstance(result, dict)
        assert len(result) == 8
        assert result[TABLE_EVENTS] == 1
        assert result[TABLE_MARKETS] == 1
        assert result[TABLE_TOKENS] == 2  # 2 tokens from _make_market default

    def test_エッジケース_空テーブルで全カウントがゼロ(
        self, pm_storage: PolymarketStorage
    ) -> None:
        """count_records() returns 0 for all tables in a fresh database."""
        result = pm_storage.count_records()
        assert len(result) == 8
        for table_name, count in result.items():
            assert count == 0, f"Expected 0 rows for '{table_name}', got {count}"

    def test_正常系_get_statsと同じ結果を返す(
        self, pm_storage: PolymarketStorage
    ) -> None:
        """count_records() returns the same result as get_stats()."""
        event = _make_event("evt-001")
        pm_storage.upsert_events([event], fetched_at=FETCHED_AT)

        assert pm_storage.count_records() == pm_storage.get_stats()


class TestGetCollectionSummary:
    """Tests for PolymarketStorage.get_collection_summary()."""

    def test_正常系_収集状況サマリを返す(self, pm_storage: PolymarketStorage) -> None:
        """get_collection_summary() returns summary dict with expected keys."""
        # Insert some data
        market = _make_market("cond-001")
        event = _make_event("evt-001", markets=[market])
        pm_storage.upsert_events([event], fetched_at=FETCHED_AT)

        prices = [PricePoint(t=1700000000, p=0.65)]
        pm_storage.upsert_price_history(
            token_id="tok-yes",
            prices=prices,
            interval=PriceInterval.ONE_HOUR,
            fetched_at=FETCHED_AT,
        )

        summary = pm_storage.get_collection_summary()
        assert isinstance(summary, dict)
        assert "record_counts" in summary
        assert "total_records" in summary
        assert summary["record_counts"][TABLE_EVENTS] == 1
        assert summary["total_records"] > 0

    def test_エッジケース_空テーブルでも正常に動作する(
        self, pm_storage: PolymarketStorage
    ) -> None:
        """get_collection_summary() works on an empty database."""
        summary = pm_storage.get_collection_summary()
        assert isinstance(summary, dict)
        assert summary["total_records"] == 0
        assert "record_counts" in summary

    def test_正常系_event_countとmarket_countが含まれる(
        self, pm_storage: PolymarketStorage
    ) -> None:
        """get_collection_summary() includes event_count and market_count."""
        events = [_make_event(f"evt-{i:03d}") for i in range(3)]
        pm_storage.upsert_events(events, fetched_at=FETCHED_AT)
        markets = [_make_market(f"cond-{i:03d}") for i in range(5)]
        pm_storage.upsert_markets(markets, fetched_at=FETCHED_AT)

        summary = pm_storage.get_collection_summary()
        assert summary["event_count"] == 3
        assert summary["market_count"] == 5
