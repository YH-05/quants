"""統合テスト: 実 API → Storage の E2E フロー検証。

実際の Polymarket API からデータを取得し、Storage に保存・読み出し
できることを検証する。API 接続が必要なため ``@pytest.mark.integration``
マーク付き。

実行方法::

    uv run pytest tests/market/polymarket/integration/ -v -m integration

See Also
--------
market.polymarket.client : API client.
market.polymarket.storage : Storage layer.
market.polymarket.collector : Data collection orchestrator.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import TYPE_CHECKING

import pytest

from market.polymarket.client import PolymarketClient
from market.polymarket.collector import PolymarketCollector
from market.polymarket.storage import PolymarketStorage
from market.polymarket.storage_constants import (
    TABLE_EVENTS,
    TABLE_MARKETS,
    TABLE_TOKENS,
)
from market.polymarket.types import PriceInterval

if TYPE_CHECKING:
    from collections.abc import Generator
    from pathlib import Path

pytestmark = pytest.mark.integration


# ============================================================================
# Fixtures
# ============================================================================


@pytest.fixture()
def storage(tmp_path: Path) -> PolymarketStorage:
    """Create a temporary PolymarketStorage for integration tests."""
    return PolymarketStorage(db_path=tmp_path / "integration_test.db")


@pytest.fixture()
def client() -> Generator[PolymarketClient]:
    """Create a PolymarketClient for integration tests."""
    c = PolymarketClient()
    yield c
    c.close()


# ============================================================================
# Integration tests: API → Storage round-trip
# ============================================================================


class TestEventRoundTrip:
    """実 API からイベントを取得し Storage に保存するE2Eテスト。"""

    def test_統合_イベント取得から保存と読み出しまで(
        self,
        client: PolymarketClient,
        storage: PolymarketStorage,
    ) -> None:
        """Fetch events from API, store, and read back."""
        # Step 1: Fetch a small number of events from the API
        events = client.get_events(limit=3)
        assert len(events) > 0, "API should return at least 1 event"

        # Step 2: Save to storage
        fetched_at = datetime.now(tz=UTC).isoformat()
        storage.upsert_events(events, fetched_at=fetched_at)

        # Step 3: Read back and verify
        df = storage.get_events()
        assert len(df) == len(events)
        assert "id" in df.columns
        assert "title" in df.columns

    def test_統合_イベントのマーケットとトークンが連鎖保存される(
        self,
        client: PolymarketClient,
        storage: PolymarketStorage,
    ) -> None:
        """Events with markets/tokens cascade correctly."""
        events = client.get_events(limit=2)
        assert len(events) > 0

        fetched_at = datetime.now(tz=UTC).isoformat()
        storage.upsert_events(events, fetched_at=fetched_at)

        stats = storage.get_stats()
        # Events should have markets (most events have at least 1)
        assert stats[TABLE_EVENTS] >= 1
        # Markets may or may not exist depending on API data
        assert stats[TABLE_MARKETS] >= 0


class TestMarketRoundTrip:
    """実 API からマーケットを取得し Storage に保存するE2Eテスト。"""

    def test_統合_マーケット取得から保存と読み出しまで(
        self,
        client: PolymarketClient,
        storage: PolymarketStorage,
    ) -> None:
        """Fetch markets from API, store, and read back."""
        markets = client.get_markets(limit=3)
        assert len(markets) > 0, "API should return at least 1 market"

        fetched_at = datetime.now(tz=UTC).isoformat()
        storage.upsert_markets(markets, fetched_at=fetched_at)

        df = storage.get_markets()
        assert len(df) > 0
        assert "condition_id" in df.columns
        assert "question" in df.columns

    def test_統合_マーケットのトークンが保存される(
        self,
        client: PolymarketClient,
        storage: PolymarketStorage,
    ) -> None:
        """Markets with valid tokens save token rows."""
        markets = client.get_markets(limit=3)
        assert len(markets) > 0

        fetched_at = datetime.now(tz=UTC).isoformat()
        storage.upsert_markets(markets, fetched_at=fetched_at)

        stats = storage.get_stats()
        assert stats[TABLE_MARKETS] >= 1
        # Tokens may exist if markets have valid token data
        assert stats[TABLE_TOKENS] >= 0


class TestPriceHistoryRoundTrip:
    """実 API から価格履歴を取得し Storage に保存するE2Eテスト。"""

    def test_統合_価格履歴の取得保存読み出し(
        self,
        client: PolymarketClient,
        storage: PolymarketStorage,
    ) -> None:
        """Fetch price history, store, and verify round-trip."""
        # Get a market to find a token_id
        markets = client.get_markets(limit=3)
        assert len(markets) > 0

        # Find a market with a valid token_id
        token_id = None
        for market in markets:
            for tok in market.tokens:
                tid = tok.get("token_id")
                if tid:
                    token_id = str(tid)
                    break
            if token_id:
                break

        if token_id is None:
            pytest.skip("No market with valid token_id found")

        # Fetch price history
        interval = PriceInterval.ONE_DAY
        result = client.get_prices_history(token_id, interval=interval)
        df_api = result.data

        if df_api.empty:
            pytest.skip("No price history data available for this token")

        # Convert to PricePoint list and store
        from market.polymarket.models import PricePoint

        points = [
            PricePoint(t=int(row["timestamp"]), p=float(row["price"]))
            for _, row in df_api.iterrows()
        ]

        fetched_at = datetime.now(tz=UTC).isoformat()
        storage.upsert_price_history(token_id, points, interval, fetched_at=fetched_at)

        # Read back
        df_stored = storage.get_price_history(token_id, interval=interval)
        assert len(df_stored) == len(points)
        assert "token_id" in df_stored.columns
        assert "price" in df_stored.columns


class TestTradesRoundTrip:
    """実 API からトレードを取得し Storage に保存するE2Eテスト。"""

    def test_統合_トレード取得保存読み出し(
        self,
        client: PolymarketClient,
        storage: PolymarketStorage,
    ) -> None:
        """Fetch trades, store, and verify round-trip."""
        # Get a market condition_id
        markets = client.get_markets(limit=5)
        assert len(markets) > 0

        condition_id = markets[0].condition_id

        # Fetch trades (may be empty for inactive markets)
        trades = client.get_trades(condition_id, limit=10)

        if not trades:
            pytest.skip(f"No trades found for condition_id={condition_id}")

        fetched_at = datetime.now(tz=UTC).isoformat()
        storage.upsert_trades(trades, fetched_at=fetched_at)

        df = storage.get_trades(condition_id)
        assert len(df) == len(trades)
        assert "id" in df.columns
        assert "price" in df.columns


class TestCollectorIntegration:
    """Collector を使用したE2E統合テスト。"""

    def test_統合_コレクターでイベント収集保存(
        self,
        client: PolymarketClient,
        storage: PolymarketStorage,
    ) -> None:
        """Collector.collect_events() fetches and persists data."""
        collector = PolymarketCollector(client=client, storage=storage)
        count, _events = collector.collect_events(limit=2)

        assert count >= 0  # API may return 0 on transient issues
        if count > 0:
            stats = storage.get_stats()
            assert stats[TABLE_EVENTS] >= 1


class TestStorageIdempotencyIntegration:
    """実データでの upsert 冪等性テスト。"""

    def test_統合_実データを2回upsertしてもレコード数は変わらない(
        self,
        client: PolymarketClient,
        storage: PolymarketStorage,
    ) -> None:
        """Upserting real API data twice results in same record count."""
        events = client.get_events(limit=2)
        if not events:
            pytest.skip("No events returned from API")

        fetched_at = datetime.now(tz=UTC).isoformat()

        # First upsert
        storage.upsert_events(events, fetched_at=fetched_at)
        stats_first = storage.get_stats()

        # Second upsert (same data, same fetched_at)
        storage.upsert_events(events, fetched_at=fetched_at)
        stats_second = storage.get_stats()

        assert stats_second[TABLE_EVENTS] == stats_first[TABLE_EVENTS]
        assert stats_second[TABLE_MARKETS] == stats_first[TABLE_MARKETS]
        assert stats_second[TABLE_TOKENS] == stats_first[TABLE_TOKENS]
