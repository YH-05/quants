"""Tests for market.polymarket.models module.

Tests for the 6 Pydantic V2 response models:
- PolymarketEvent
- PolymarketMarket
- PricePoint
- OrderBook
- OrderBookLevel
- TradeRecord
"""

from datetime import UTC, datetime

import pytest
from pydantic import ValidationError

from market.polymarket.models import (
    OrderBook,
    OrderBookLevel,
    PolymarketEvent,
    PolymarketMarket,
    PricePoint,
    TradeRecord,
)

# =============================================================================
# OrderBookLevel
# =============================================================================


class TestOrderBookLevel:
    """Tests for OrderBookLevel model."""

    def test_正常系_基本的なレベル(self) -> None:
        level = OrderBookLevel(price=0.55, size=1000.0)
        assert level.price == pytest.approx(0.55)
        assert level.size == pytest.approx(1000.0)

    def test_正常系_model_validate(self) -> None:
        data = {"price": 0.75, "size": 500.0}
        level = OrderBookLevel.model_validate(data)
        assert level.price == pytest.approx(0.75)
        assert level.size == pytest.approx(500.0)

    def test_正常系_extra_fieldsは無視される(self) -> None:
        data = {"price": 0.55, "size": 1000.0, "unknown_field": "ignored"}
        level = OrderBookLevel.model_validate(data)
        assert level.price == pytest.approx(0.55)
        assert level.size == pytest.approx(1000.0)
        assert not hasattr(level, "unknown_field")

    def test_異常系_price欠落でValidationError(self) -> None:
        with pytest.raises(ValidationError):
            OrderBookLevel.model_validate({"size": 1000.0})

    def test_異常系_size欠落でValidationError(self) -> None:
        with pytest.raises(ValidationError):
            OrderBookLevel.model_validate({"price": 0.55})

    def test_正常系_price境界値_0(self) -> None:
        level = OrderBookLevel(price=0.0, size=100.0)
        assert level.price == pytest.approx(0.0)

    def test_正常系_price境界値_1(self) -> None:
        level = OrderBookLevel(price=1.0, size=100.0)
        assert level.price == pytest.approx(1.0)


# =============================================================================
# PricePoint
# =============================================================================


class TestPricePoint:
    """Tests for PricePoint model."""

    def test_正常系_基本的な価格データ(self) -> None:
        point = PricePoint(t=1700000000, p=0.65)
        assert point.t == 1700000000
        assert point.p == pytest.approx(0.65)

    def test_正常系_model_validate(self) -> None:
        data = {"t": 1700000000, "p": 0.65}
        point = PricePoint.model_validate(data)
        assert point.t == 1700000000
        assert point.p == pytest.approx(0.65)

    def test_正常系_extra_fieldsは無視される(self) -> None:
        data = {"t": 1700000000, "p": 0.65, "extra": "value"}
        point = PricePoint.model_validate(data)
        assert point.t == 1700000000
        assert not hasattr(point, "extra")

    def test_異常系_t欠落でValidationError(self) -> None:
        with pytest.raises(ValidationError):
            PricePoint.model_validate({"p": 0.65})

    def test_異常系_p欠落でValidationError(self) -> None:
        with pytest.raises(ValidationError):
            PricePoint.model_validate({"t": 1700000000})


# =============================================================================
# OrderBook
# =============================================================================


class TestOrderBook:
    """Tests for OrderBook model."""

    def test_正常系_基本的なオーダーブック(self) -> None:
        book = OrderBook(
            market="0xabc123",
            asset_id="asset123",
            bids=[OrderBookLevel(price=0.50, size=100.0)],
            asks=[OrderBookLevel(price=0.55, size=200.0)],
            timestamp=datetime(2026, 1, 1, tzinfo=UTC),
        )
        assert book.market == "0xabc123"
        assert book.asset_id == "asset123"
        assert len(book.bids) == 1
        assert len(book.asks) == 1
        assert book.bids[0].price == pytest.approx(0.50)
        assert book.asks[0].price == pytest.approx(0.55)

    def test_正常系_model_validate(self) -> None:
        data = {
            "market": "0xabc123",
            "asset_id": "asset123",
            "bids": [{"price": 0.50, "size": 100.0}],
            "asks": [{"price": 0.55, "size": 200.0}],
            "timestamp": "2026-01-01T00:00:00Z",
        }
        book = OrderBook.model_validate(data)
        assert book.market == "0xabc123"
        assert len(book.bids) == 1

    def test_正常系_空のbidsとasks(self) -> None:
        book = OrderBook(
            market="0xabc123",
            asset_id="asset123",
            bids=[],
            asks=[],
        )
        assert book.bids == []
        assert book.asks == []

    def test_正常系_timestampはオプショナル(self) -> None:
        book = OrderBook(
            market="0xabc123",
            asset_id="asset123",
            bids=[],
            asks=[],
        )
        assert book.timestamp is None

    def test_正常系_extra_fieldsは無視される(self) -> None:
        data = {
            "market": "0xabc123",
            "asset_id": "asset123",
            "bids": [],
            "asks": [],
            "hash": "0xdeadbeef",
        }
        book = OrderBook.model_validate(data)
        assert book.market == "0xabc123"
        assert not hasattr(book, "hash")

    def test_異常系_market欠落でValidationError(self) -> None:
        with pytest.raises(ValidationError):
            OrderBook.model_validate({"asset_id": "asset123", "bids": [], "asks": []})


# =============================================================================
# TradeRecord
# =============================================================================


class TestTradeRecord:
    """Tests for TradeRecord model."""

    def test_正常系_基本的な取引(self) -> None:
        trade = TradeRecord(
            id="trade-001",
            market="0xabc123",
            asset_id="asset123",
            price=0.65,
            size=500.0,
            side="BUY",
            timestamp=datetime(2026, 1, 1, tzinfo=UTC),
        )
        assert trade.id == "trade-001"
        assert trade.market == "0xabc123"
        assert trade.price == pytest.approx(0.65)
        assert trade.size == pytest.approx(500.0)
        assert trade.side == "BUY"

    def test_正常系_model_validate(self) -> None:
        data = {
            "id": "trade-001",
            "market": "0xabc123",
            "asset_id": "asset123",
            "price": 0.65,
            "size": 500.0,
            "side": "SELL",
            "timestamp": "2026-01-01T00:00:00Z",
        }
        trade = TradeRecord.model_validate(data)
        assert trade.id == "trade-001"
        assert trade.side == "SELL"

    def test_正常系_オプショナルフィールド省略(self) -> None:
        trade = TradeRecord(
            id="trade-001",
            market="0xabc123",
            asset_id="asset123",
            price=0.65,
            size=500.0,
        )
        assert trade.side is None
        assert trade.timestamp is None

    def test_正常系_extra_fieldsは無視される(self) -> None:
        data = {
            "id": "trade-001",
            "market": "0xabc123",
            "asset_id": "asset123",
            "price": 0.65,
            "size": 500.0,
            "fee": 0.01,
        }
        trade = TradeRecord.model_validate(data)
        assert trade.id == "trade-001"
        assert not hasattr(trade, "fee")

    def test_正常系_id省略で合成IDが生成される(self) -> None:
        """When id is absent, a deterministic synthetic ID is generated."""
        trade = TradeRecord.model_validate(
            {
                "market": "0xabc123",
                "asset_id": "asset123",
                "price": 0.65,
                "size": 500.0,
            }
        )
        assert trade.id is not None
        assert len(trade.id) == 16  # SHA-256 hex[:16]

    def test_正常系_新APIスキーマでmodel_validate(self) -> None:
        """New Data API schema (asset, conditionId, Unix timestamp) parses correctly."""
        data = {
            "proxyWallet": "0x1234",
            "side": "BUY",
            "asset": "75467129615908319583031474642658885479135630431889036121812713428992454630178",
            "conditionId": "0xb48621f7eba07b0a3eeabc6afb09ae42490239903997b9d412b0f69aeb040c8b",
            "size": 3,
            "price": 0.251,
            "timestamp": 1774249691,
            "title": "BitBoy convicted?",
            "slug": "bitboy-convicted",
            "outcome": "Yes",
            "outcomeIndex": 0,
            "name": "wanglin2",
            "transactionHash": "0xdeadbeef",
            "eventSlug": "bitboy-convicted",
        }
        trade = TradeRecord.model_validate(data)
        assert (
            trade.asset_id
            == "75467129615908319583031474642658885479135630431889036121812713428992454630178"
        )
        assert (
            trade.market
            == "0xb48621f7eba07b0a3eeabc6afb09ae42490239903997b9d412b0f69aeb040c8b"
        )
        assert trade.price == pytest.approx(0.251)
        assert trade.size == pytest.approx(3.0)
        assert trade.side == "BUY"
        assert trade.timestamp is not None
        # Synthetic ID should be generated
        assert trade.id is not None
        assert len(trade.id) == 16

    def test_正常系_Unixタイムスタンプがdatetimeに変換される(self) -> None:
        """Integer Unix timestamps are converted to datetime objects."""
        trade = TradeRecord(
            asset_id="asset123",
            price=0.5,
            size=10,
            timestamp=1700000000,
        )
        assert trade.timestamp is not None
        assert trade.timestamp.year == 2023
        assert trade.timestamp.tzinfo is not None

    def test_正常系_合成IDは決定的(self) -> None:
        """Synthetic IDs are deterministic: same inputs produce same ID."""
        data = {
            "asset": "token1",
            "price": 0.5,
            "size": 10,
            "timestamp": 1700000000,
        }
        trade1 = TradeRecord.model_validate(data)
        trade2 = TradeRecord.model_validate(data)
        assert trade1.id == trade2.id

    def test_正常系_market省略でNoneからemptyに(self) -> None:
        """When market (conditionId) is absent, it defaults to None."""
        trade = TradeRecord(
            asset_id="asset123",
            price=0.5,
            size=10,
        )
        assert trade.market is None


# =============================================================================
# PolymarketMarket
# =============================================================================


class TestPolymarketMarket:
    """Tests for PolymarketMarket model."""

    def test_正常系_基本的なマーケット(self) -> None:
        market = PolymarketMarket(
            condition_id="0xabc123",
            question="Will X happen?",
            tokens=[
                {"token_id": "tok1", "outcome": "Yes", "price": 0.65},
                {"token_id": "tok2", "outcome": "No", "price": 0.35},
            ],
        )
        assert market.condition_id == "0xabc123"
        assert market.question == "Will X happen?"
        assert len(market.tokens) == 2

    def test_正常系_model_validate(self) -> None:
        data = {
            "condition_id": "0xabc123",
            "question": "Will X happen?",
            "tokens": [
                {"token_id": "tok1", "outcome": "Yes", "price": 0.65},
            ],
            "description": "Detailed description",
            "end_date_iso": "2026-12-31T00:00:00Z",
            "active": True,
            "closed": False,
            "volume": 1000000.0,
            "liquidity": 500000.0,
        }
        market = PolymarketMarket.model_validate(data)
        assert market.condition_id == "0xabc123"
        assert market.description == "Detailed description"
        assert market.active is True
        assert market.closed is False
        assert market.volume == pytest.approx(1000000.0)
        assert market.liquidity == pytest.approx(500000.0)

    def test_正常系_部分フィールドのみ(self) -> None:
        data = {
            "condition_id": "0xabc123",
            "question": "Will X happen?",
            "tokens": [],
        }
        market = PolymarketMarket.model_validate(data)
        assert market.description is None
        assert market.end_date_iso is None
        assert market.active is None
        assert market.closed is None
        assert market.volume is None
        assert market.liquidity is None

    def test_正常系_extra_fieldsは無視される(self) -> None:
        data = {
            "condition_id": "0xabc123",
            "question": "Will X happen?",
            "tokens": [],
            "slug": "will-x-happen",
            "market_slug": "elections",
        }
        market = PolymarketMarket.model_validate(data)
        assert market.condition_id == "0xabc123"
        assert not hasattr(market, "slug")

    def test_異常系_condition_id欠落でValidationError(self) -> None:
        with pytest.raises(ValidationError):
            PolymarketMarket.model_validate(
                {"question": "Will X happen?", "tokens": []}
            )

    def test_異常系_question欠落でValidationError(self) -> None:
        with pytest.raises(ValidationError):
            PolymarketMarket.model_validate({"condition_id": "0xabc123", "tokens": []})

    def test_正常系_camelCaseのconditionIdでmodel_validate(self) -> None:
        """conditionId (camelCase alias) is accepted via populate_by_name."""
        data = {
            "conditionId": "0xabc123",
            "question": "Will X happen?",
        }
        market = PolymarketMarket.model_validate(data)
        assert market.condition_id == "0xabc123"

    def test_正常系_camelCaseのendDateIsoでmodel_validate(self) -> None:
        """endDateIso (camelCase alias) is accepted."""
        data = {
            "conditionId": "0xabc123",
            "question": "Will X happen?",
            "endDateIso": "2026-12-31",
        }
        market = PolymarketMarket.model_validate(data)
        assert market.end_date_iso == "2026-12-31"

    def test_正常系_tokensが省略されると空リスト(self) -> None:
        """tokens defaults to empty list when not provided."""
        data = {
            "condition_id": "0xabc123",
            "question": "Will X happen?",
        }
        market = PolymarketMarket.model_validate(data)
        assert market.tokens == []

    def test_正常系_clobTokenIdsからtokensを構築(self) -> None:
        """tokens are built from clobTokenIds + outcomes + outcomePrices."""
        data = {
            "conditionId": "0xabc123",
            "question": "Will X happen?",
            "clobTokenIds": '["tok1", "tok2"]',
            "outcomes": '["Yes", "No"]',
            "outcomePrices": '["0.65", "0.35"]',
        }
        market = PolymarketMarket.model_validate(data)
        assert len(market.tokens) == 2
        assert market.tokens[0]["token_id"] == "tok1"
        assert market.tokens[0]["outcome"] == "Yes"
        assert market.tokens[0]["price"] == pytest.approx(0.65)
        assert market.tokens[1]["token_id"] == "tok2"
        assert market.tokens[1]["outcome"] == "No"
        assert market.tokens[1]["price"] == pytest.approx(0.35)

    def test_正常系_clobTokenIdsがリストの場合もtokens構築(self) -> None:
        """clobTokenIds can also be a Python list (not only JSON string)."""
        data = {
            "conditionId": "0xabc123",
            "question": "Will X happen?",
            "clobTokenIds": ["tok1", "tok2"],
            "outcomes": ["Yes", "No"],
            "outcomePrices": ["0.65", "0.35"],
        }
        market = PolymarketMarket.model_validate(data)
        assert len(market.tokens) == 2
        assert market.tokens[0]["token_id"] == "tok1"

    def test_正常系_tokensが存在する場合clobTokenIdsは無視(self) -> None:
        """When tokens is already provided, clobTokenIds is not used."""
        data = {
            "conditionId": "0xabc123",
            "question": "Will X happen?",
            "tokens": [{"token_id": "existing", "outcome": "Yes", "price": 0.5}],
            "clobTokenIds": '["overridden"]',
        }
        market = PolymarketMarket.model_validate(data)
        assert len(market.tokens) == 1
        assert market.tokens[0]["token_id"] == "existing"

    def test_正常系_volumeとliquidityが文字列でも変換(self) -> None:
        """volume and liquidity accept string values and coerce to float."""
        data = {
            "condition_id": "0xabc123",
            "question": "Will X happen?",
            "volume": "32257.445115",
            "liquidity": "0",
        }
        market = PolymarketMarket.model_validate(data)
        assert market.volume == pytest.approx(32257.445115)
        assert market.liquidity == pytest.approx(0.0)

    def test_正常系_Gamma_API風の完全レスポンスでmodel_validate(self) -> None:
        """Full Gamma API-style response (camelCase, JSON strings) parses correctly."""
        data = {
            "id": "239826",
            "conditionId": "0xabc123def456",
            "question": "Will X happen by 2026?",
            "slug": "will-x-happen",
            "endDateIso": "2026-12-31",
            "active": True,
            "closed": False,
            "volume": "1000000.50",
            "liquidity": "50000",
            "clobTokenIds": '["tok-yes-123", "tok-no-456"]',
            "outcomes": '["Yes", "No"]',
            "outcomePrices": '["0.65", "0.35"]',
            "marketType": "normal",
            "archived": False,
        }
        market = PolymarketMarket.model_validate(data)
        assert market.condition_id == "0xabc123def456"
        assert market.end_date_iso == "2026-12-31"
        assert market.volume == pytest.approx(1000000.50)
        assert market.liquidity == pytest.approx(50000.0)
        assert len(market.tokens) == 2
        assert market.tokens[0]["token_id"] == "tok-yes-123"
        assert market.tokens[0]["outcome"] == "Yes"
        assert market.tokens[0]["price"] == pytest.approx(0.65)


# =============================================================================
# PolymarketEvent
# =============================================================================


class TestPolymarketEvent:
    """Tests for PolymarketEvent model."""

    def test_正常系_基本的なイベント(self) -> None:
        event = PolymarketEvent(
            id="event-001",
            title="US Presidential Election 2028",
            slug="us-presidential-election-2028",
            markets=[],
        )
        assert event.id == "event-001"
        assert event.title == "US Presidential Election 2028"
        assert event.slug == "us-presidential-election-2028"
        assert event.markets == []

    def test_正常系_model_validate(self) -> None:
        data = {
            "id": "event-001",
            "title": "US Presidential Election 2028",
            "slug": "us-presidential-election-2028",
            "markets": [
                {
                    "condition_id": "0xabc123",
                    "question": "Who will win?",
                    "tokens": [],
                }
            ],
            "description": "Event description",
            "start_date": "2028-01-01T00:00:00Z",
            "end_date": "2028-11-05T00:00:00Z",
            "active": True,
            "closed": False,
            "volume": 5000000.0,
            "liquidity": 2000000.0,
        }
        event = PolymarketEvent.model_validate(data)
        assert event.id == "event-001"
        assert len(event.markets) == 1
        assert isinstance(event.markets[0], PolymarketMarket)
        assert event.description == "Event description"
        assert event.active is True
        assert event.volume == pytest.approx(5000000.0)

    def test_正常系_部分フィールドのみ(self) -> None:
        data = {
            "id": "event-001",
            "title": "Event",
            "slug": "event",
            "markets": [],
        }
        event = PolymarketEvent.model_validate(data)
        assert event.description is None
        assert event.start_date is None
        assert event.end_date is None
        assert event.active is None
        assert event.closed is None
        assert event.volume is None
        assert event.liquidity is None

    def test_正常系_extra_fieldsは無視される(self) -> None:
        data = {
            "id": "event-001",
            "title": "Event",
            "slug": "event",
            "markets": [],
            "category": "politics",
            "tags": ["election"],
        }
        event = PolymarketEvent.model_validate(data)
        assert event.id == "event-001"
        assert not hasattr(event, "category")
        assert not hasattr(event, "tags")

    def test_異常系_id欠落でValidationError(self) -> None:
        with pytest.raises(ValidationError):
            PolymarketEvent.model_validate(
                {"title": "Event", "slug": "event", "markets": []}
            )

    def test_正常系_ネストされたマーケットのextraフィールドも無視(self) -> None:
        data = {
            "id": "event-001",
            "title": "Event",
            "slug": "event",
            "markets": [
                {
                    "condition_id": "0xabc123",
                    "question": "Q?",
                    "tokens": [],
                    "slug": "q",
                    "extra_nested": True,
                }
            ],
        }
        event = PolymarketEvent.model_validate(data)
        assert len(event.markets) == 1
        assert not hasattr(event.markets[0], "extra_nested")

    def test_正常系_model_dump(self) -> None:
        event = PolymarketEvent(
            id="event-001",
            title="Event",
            slug="event",
            markets=[],
        )
        dumped = event.model_dump()
        assert dumped["id"] == "event-001"
        assert dumped["title"] == "Event"
        assert dumped["markets"] == []

    def test_正常系_camelCaseのstartDateとendDateで検証(self) -> None:
        """startDate and endDate (camelCase aliases) are accepted."""
        data = {
            "id": "event-001",
            "title": "Event",
            "slug": "event",
            "markets": [],
            "startDate": "2026-01-01T00:00:00Z",
            "endDate": "2026-12-31T00:00:00Z",
        }
        event = PolymarketEvent.model_validate(data)
        assert event.start_date == "2026-01-01T00:00:00Z"
        assert event.end_date == "2026-12-31T00:00:00Z"

    def test_正常系_volumeとliquidityが文字列でも変換(self) -> None:
        """volume and liquidity accept string values and coerce to float."""
        data = {
            "id": "event-001",
            "title": "Event",
            "slug": "event",
            "markets": [],
            "volume": "5000000.0",
            "liquidity": "2000000",
        }
        event = PolymarketEvent.model_validate(data)
        assert event.volume == pytest.approx(5000000.0)
        assert event.liquidity == pytest.approx(2000000.0)

    def test_正常系_ネストされたマーケットでcamelCase対応(self) -> None:
        """Nested markets with camelCase fields parse correctly."""
        data = {
            "id": "event-001",
            "title": "Event",
            "slug": "event",
            "markets": [
                {
                    "conditionId": "0xabc123",
                    "question": "Will X happen?",
                    "clobTokenIds": '["tok1"]',
                    "outcomes": '["Yes"]',
                    "outcomePrices": '["0.75"]',
                    "endDateIso": "2026-12-31",
                    "volume": "1000",
                }
            ],
        }
        event = PolymarketEvent.model_validate(data)
        assert len(event.markets) == 1
        market = event.markets[0]
        assert market.condition_id == "0xabc123"
        assert market.end_date_iso == "2026-12-31"
        assert market.volume == pytest.approx(1000.0)
        assert len(market.tokens) == 1
        assert market.tokens[0]["token_id"] == "tok1"
        assert market.tokens[0]["outcome"] == "Yes"
        assert market.tokens[0]["price"] == pytest.approx(0.75)
