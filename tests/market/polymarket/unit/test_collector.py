"""Unit tests for the Polymarket collector module.

Tests cover ``CollectionResult`` dataclass, ``PolymarketCollector``
orchestration of Client -> Storage flow, error handling, and
individual collect methods.
"""

from __future__ import annotations

from dataclasses import FrozenInstanceError
from datetime import UTC, datetime
from typing import Any
from unittest.mock import MagicMock, patch

import pytest

from market.polymarket.collector import CollectionResult, PolymarketCollector
from market.polymarket.models import (
    OrderBook,
    OrderBookLevel,
    PolymarketEvent,
    PolymarketMarket,
    PricePoint,
    TradeRecord,
)
from market.polymarket.types import PriceInterval

# ============================================================================
# Fixtures
# ============================================================================


def _make_event(
    event_id: str = "evt-001",
    title: str = "Test Event",
    slug: str = "test-event",
) -> PolymarketEvent:
    """Create a sample PolymarketEvent with nested market and tokens."""
    return PolymarketEvent(
        id=event_id,
        title=title,
        slug=slug,
        markets=[
            PolymarketMarket(
                condition_id="cond-001",
                question="Will test pass?",
                tokens=[
                    {
                        "token_id": "tok-yes",
                        "outcome": "Yes",
                        "price": 0.65,
                    },
                    {
                        "token_id": "tok-no",
                        "outcome": "No",
                        "price": 0.35,
                    },
                ],
                active=True,
                volume=1000.0,
            ),
        ],
        active=True,
        volume=1000.0,
    )


def _make_trade(trade_id: str = "trade-001") -> TradeRecord:
    """Create a sample TradeRecord."""
    return TradeRecord(
        id=trade_id,
        market="cond-001",
        asset_id="tok-yes",
        price=0.65,
        size=100.0,
        side="BUY",
    )


def _make_orderbook() -> OrderBook:
    """Create a sample OrderBook."""
    return OrderBook(
        market="cond-001",
        asset_id="tok-yes",
        bids=[OrderBookLevel(price=0.64, size=500.0)],
        asks=[OrderBookLevel(price=0.66, size=300.0)],
    )


@pytest.fixture()
def mock_client() -> MagicMock:
    """Create a mock PolymarketClient with default return values."""
    client = MagicMock()

    events = [_make_event()]
    client.get_events.return_value = events

    # Price history: return a MagicMock with .data attribute for DataFrame
    price_result = MagicMock()
    price_result.data = MagicMock()
    # get_prices_history returns MarketDataResult, but collector needs PricePoint list
    # The collector will use the client to get raw history
    client.get_prices_history.return_value = price_result

    client.get_trades.return_value = [_make_trade()]
    client.get_open_interest.return_value = {"total_oi": 5000.0}
    client.get_orderbook.return_value = _make_orderbook()
    client.get_leaderboard.return_value = [{"address": "0xabc", "profit": 1000.0}]
    client.get_holders.return_value = [{"address": "0xdef", "shares": 500}]

    return client


@pytest.fixture()
def mock_storage() -> MagicMock:
    """Create a mock PolymarketStorage with spec."""
    from market.polymarket.storage import PolymarketStorage

    storage = MagicMock(spec=PolymarketStorage)
    return storage


@pytest.fixture()
def collector(mock_client: MagicMock, mock_storage: MagicMock) -> PolymarketCollector:
    """Create a PolymarketCollector with mock dependencies."""
    return PolymarketCollector(client=mock_client, storage=mock_storage)


# ============================================================================
# CollectionResult tests
# ============================================================================


class TestCollectionResult:
    """Tests for the CollectionResult frozen dataclass."""

    def test_正常系_デフォルト値で生成できる(self) -> None:
        """CollectionResult can be created with default values."""
        result = CollectionResult()
        assert result.events_collected == 0
        assert result.markets_collected == 0
        assert result.price_histories_collected == 0
        assert result.trades_collected == 0
        assert result.oi_snapshots_collected == 0
        assert result.orderbook_snapshots_collected == 0
        assert result.leaderboard_collected == 0
        assert result.holders_collected == 0
        assert result.errors == ()
        assert result.started_at is not None
        assert result.finished_at is None

    def test_正常系_カスタム値で生成できる(self) -> None:
        """CollectionResult can be created with custom values."""
        now = datetime.now(tz=UTC)
        result = CollectionResult(
            events_collected=5,
            markets_collected=10,
            errors=("error1", "error2"),
            started_at=now,
        )
        assert result.events_collected == 5
        assert result.markets_collected == 10
        assert result.errors == ("error1", "error2")
        assert result.started_at == now

    def test_正常系_frozenであること(self) -> None:
        """CollectionResult is immutable (frozen)."""
        result = CollectionResult()
        with pytest.raises(FrozenInstanceError):
            result.events_collected = 99

    def test_正常系_total_collectedプロパティ(self) -> None:
        """total_collected returns sum of all collected counts."""
        result = CollectionResult(
            events_collected=2,
            markets_collected=4,
            price_histories_collected=6,
            trades_collected=8,
            oi_snapshots_collected=1,
            orderbook_snapshots_collected=3,
            leaderboard_collected=1,
            holders_collected=5,
        )
        assert result.total_collected == 30

    def test_正常系_has_errorsプロパティ(self) -> None:
        """has_errors returns True when errors exist."""
        result_ok = CollectionResult()
        assert result_ok.has_errors is False

        result_err = CollectionResult(errors=("some error",))
        assert result_err.has_errors is True


# ============================================================================
# PolymarketCollector construction tests
# ============================================================================


class TestPolymarketCollectorInit:
    """Tests for PolymarketCollector initialization."""

    def test_正常系_clientとstorageで初期化できる(
        self,
        mock_client: MagicMock,
        mock_storage: MagicMock,
    ) -> None:
        """Collector initializes with client and storage."""
        collector = PolymarketCollector(client=mock_client, storage=mock_storage)
        assert collector is not None


# ============================================================================
# collect_events tests
# ============================================================================


class TestCollectEvents:
    """Tests for PolymarketCollector.collect_events()."""

    def test_正常系_イベント収集と保存(
        self,
        collector: PolymarketCollector,
        mock_client: MagicMock,
        mock_storage: MagicMock,
    ) -> None:
        """collect_events fetches from client and saves to storage."""
        count, events = collector.collect_events()
        assert count == 1
        assert len(events) == 1
        mock_client.get_events.assert_called_once()
        mock_storage.upsert_events.assert_called_once()

    def test_異常系_クライアントエラーで0と空リストを返す(
        self,
        collector: PolymarketCollector,
        mock_client: MagicMock,
        mock_storage: MagicMock,
    ) -> None:
        """collect_events returns (0, []) and records error on client failure."""
        mock_client.get_events.side_effect = RuntimeError("API down")
        count, events = collector.collect_events()
        assert count == 0
        assert events == []
        mock_storage.upsert_events.assert_not_called()

    def test_エッジケース_空リストで0と空リストを返す(
        self,
        collector: PolymarketCollector,
        mock_client: MagicMock,
    ) -> None:
        """collect_events returns (0, []) when no events found."""
        mock_client.get_events.return_value = []
        count, events = collector.collect_events()
        assert count == 0
        assert events == []


# ============================================================================
# collect_price_history tests
# ============================================================================


class TestCollectPriceHistory:
    """Tests for PolymarketCollector.collect_price_history()."""

    def test_正常系_価格履歴収集と保存(
        self,
        collector: PolymarketCollector,
        mock_client: MagicMock,
        mock_storage: MagicMock,
    ) -> None:
        """collect_price_history fetches from client and saves to storage."""
        import pandas as pd

        df = pd.DataFrame(
            {"timestamp": [1700000000, 1700003600], "price": [0.65, 0.70]}
        )
        mock_result = MagicMock()
        mock_result.data = df
        mock_client.get_prices_history.return_value = mock_result

        count = collector.collect_price_history("tok-yes")
        assert count == 2
        mock_storage.upsert_price_history.assert_called_once()

    def test_エッジケース_空DataFrameで0を返す(
        self,
        collector: PolymarketCollector,
        mock_client: MagicMock,
        mock_storage: MagicMock,
    ) -> None:
        """collect_price_history returns 0 when DataFrame is empty."""
        import pandas as pd

        mock_result = MagicMock()
        mock_result.data = pd.DataFrame()
        mock_client.get_prices_history.return_value = mock_result

        count = collector.collect_price_history("tok-yes")
        assert count == 0
        mock_storage.upsert_price_history.assert_not_called()

    def test_異常系_クライアントエラーで0を返す(
        self,
        collector: PolymarketCollector,
        mock_client: MagicMock,
        mock_storage: MagicMock,
    ) -> None:
        """collect_price_history returns 0 and records error on failure."""
        mock_client.get_prices_history.side_effect = RuntimeError("API error")
        count = collector.collect_price_history("tok-yes")
        assert count == 0
        mock_storage.upsert_price_history.assert_not_called()

    def test_異常系_不正intervalでエラー記録(
        self,
        collector: PolymarketCollector,
        mock_client: MagicMock,
    ) -> None:
        """collect_price_history records error for invalid interval."""
        count = collector.collect_price_history("tok-yes", interval="invalid")
        assert count == 0


# ============================================================================
# collect_trades tests
# ============================================================================


class TestCollectTrades:
    """Tests for PolymarketCollector.collect_trades()."""

    def test_正常系_トレード収集と保存(
        self,
        collector: PolymarketCollector,
        mock_client: MagicMock,
        mock_storage: MagicMock,
    ) -> None:
        """collect_trades fetches from client and saves to storage."""
        count = collector.collect_trades(condition_id="cond-001")
        assert count == 1
        mock_client.get_trades.assert_called_once_with(
            "cond-001",
            limit=100,
        )
        mock_storage.upsert_trades.assert_called_once()

    def test_異常系_クライアントエラーで0を返す(
        self,
        collector: PolymarketCollector,
        mock_client: MagicMock,
        mock_storage: MagicMock,
    ) -> None:
        """collect_trades returns 0 and records error on failure."""
        mock_client.get_trades.side_effect = RuntimeError("API error")
        count = collector.collect_trades(condition_id="cond-001")
        assert count == 0
        mock_storage.upsert_trades.assert_not_called()


# ============================================================================
# collect_open_interest tests
# ============================================================================


class TestCollectOpenInterest:
    """Tests for PolymarketCollector.collect_open_interest()."""

    def test_正常系_OI収集と保存(
        self,
        collector: PolymarketCollector,
        mock_client: MagicMock,
        mock_storage: MagicMock,
    ) -> None:
        """collect_open_interest fetches from client and saves snapshot."""
        count = collector.collect_open_interest(condition_id="cond-001")
        assert count == 1
        mock_client.get_open_interest.assert_called_once_with("cond-001")
        mock_storage.insert_oi_snapshot.assert_called_once()

    def test_異常系_クライアントエラーで0を返す(
        self,
        collector: PolymarketCollector,
        mock_client: MagicMock,
    ) -> None:
        """collect_open_interest returns 0 on client failure."""
        mock_client.get_open_interest.side_effect = RuntimeError("fail")
        count = collector.collect_open_interest(condition_id="cond-001")
        assert count == 0


# ============================================================================
# collect_orderbooks tests
# ============================================================================


class TestCollectOrderbooks:
    """Tests for PolymarketCollector.collect_orderbooks()."""

    def test_正常系_オーダーブック収集と保存(
        self,
        collector: PolymarketCollector,
        mock_client: MagicMock,
        mock_storage: MagicMock,
    ) -> None:
        """collect_orderbooks fetches and saves for each token."""
        count = collector.collect_orderbooks(token_ids=["tok-yes"])
        assert count == 1
        mock_client.get_orderbook.assert_called_once_with("tok-yes")
        mock_storage.insert_orderbook_snapshot.assert_called_once()

    def test_異常系_部分エラーでも処理継続(
        self,
        collector: PolymarketCollector,
        mock_client: MagicMock,
        mock_storage: MagicMock,
    ) -> None:
        """collect_orderbooks continues on per-token errors."""
        mock_client.get_orderbook.side_effect = [
            RuntimeError("fail"),
            _make_orderbook(),
        ]
        count = collector.collect_orderbooks(token_ids=["tok-fail", "tok-ok"])
        assert count == 1
        assert mock_storage.insert_orderbook_snapshot.call_count == 1


# ============================================================================
# collect_leaderboard tests
# ============================================================================


class TestCollectLeaderboard:
    """Tests for PolymarketCollector.collect_leaderboard()."""

    def test_正常系_リーダーボード収集と保存(
        self,
        collector: PolymarketCollector,
        mock_client: MagicMock,
        mock_storage: MagicMock,
    ) -> None:
        """collect_leaderboard fetches and saves snapshot."""
        count = collector.collect_leaderboard()
        assert count == 1
        mock_client.get_leaderboard.assert_called_once()
        mock_storage.insert_leaderboard_snapshot.assert_called_once()

    def test_異常系_クライアントエラーで0を返す(
        self,
        collector: PolymarketCollector,
        mock_client: MagicMock,
    ) -> None:
        """collect_leaderboard returns 0 on failure."""
        mock_client.get_leaderboard.side_effect = RuntimeError("fail")
        count = collector.collect_leaderboard()
        assert count == 0


# ============================================================================
# collect_holders tests
# ============================================================================


class TestCollectHolders:
    """Tests for PolymarketCollector.collect_holders()."""

    def test_正常系_ホルダー収集と保存(
        self,
        collector: PolymarketCollector,
        mock_client: MagicMock,
        mock_storage: MagicMock,
    ) -> None:
        """collect_holders fetches and saves for each condition_id."""
        count = collector.collect_holders(condition_ids=["cond-001"])
        assert count == 1
        mock_client.get_holders.assert_called_once_with("cond-001")
        mock_storage.upsert_holders.assert_called_once()

    def test_異常系_部分エラーでも処理継続(
        self,
        collector: PolymarketCollector,
        mock_client: MagicMock,
    ) -> None:
        """collect_holders continues on per-condition errors."""
        mock_client.get_holders.side_effect = [
            RuntimeError("fail"),
            [{"address": "0xabc"}],
        ]
        count = collector.collect_holders(condition_ids=["cond-fail", "cond-ok"])
        assert count == 1


# ============================================================================
# collect_all tests
# ============================================================================


class TestCollectAll:
    """Tests for PolymarketCollector.collect_all()."""

    def test_正常系_全データ収集でCollectionResult返却(
        self,
        collector: PolymarketCollector,
        mock_client: MagicMock,
        mock_storage: MagicMock,
    ) -> None:
        """collect_all orchestrates full collection and returns result."""
        result = collector.collect_all()

        assert isinstance(result, CollectionResult)
        assert result.events_collected == 1
        assert result.finished_at is not None
        assert result.has_errors is False
        mock_client.get_events.assert_called_once()
        mock_storage.upsert_events.assert_called_once()

    def test_異常系_部分エラー時もCollectionResult返却(
        self,
        collector: PolymarketCollector,
        mock_client: MagicMock,
    ) -> None:
        """collect_all returns result with errors when some steps fail."""
        mock_client.get_events.return_value = [_make_event()]
        mock_client.get_trades.side_effect = RuntimeError("trades API down")
        mock_client.get_open_interest.side_effect = RuntimeError("OI API down")

        result = collector.collect_all()

        assert isinstance(result, CollectionResult)
        assert result.events_collected == 1
        assert result.has_errors is True
        assert result.finished_at is not None

    def test_異常系_イベント取得失敗でも処理継続(
        self,
        collector: PolymarketCollector,
        mock_client: MagicMock,
    ) -> None:
        """collect_all continues even if event collection fails."""
        mock_client.get_events.side_effect = RuntimeError("events fail")

        result = collector.collect_all()

        assert isinstance(result, CollectionResult)
        assert result.events_collected == 0
        assert result.has_errors is True
        assert result.finished_at is not None

    def test_正常系_started_atとfinished_atが設定される(
        self,
        collector: PolymarketCollector,
    ) -> None:
        """collect_all sets both started_at and finished_at timestamps."""
        result = collector.collect_all()
        assert result.started_at is not None
        assert result.finished_at is not None
        assert result.finished_at >= result.started_at


# ============================================================================
# Error tracking tests
# ============================================================================


class TestErrorTracking:
    """Tests for error tracking across collect operations."""

    def test_正常系_エラーがerrorsリストに記録される(
        self,
        collector: PolymarketCollector,
        mock_client: MagicMock,
    ) -> None:
        """Errors during collection are recorded in the errors list."""
        mock_client.get_events.side_effect = RuntimeError("events fail")
        mock_client.get_trades.side_effect = RuntimeError("trades fail")

        result = collector.collect_all()

        assert result.has_errors is True
        assert len(result.errors) >= 1
        # Error messages should contain descriptive info
        error_text = " ".join(result.errors)
        assert "events" in error_text.lower() or "event" in error_text.lower()
