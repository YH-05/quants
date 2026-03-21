"""Tests for market.polymarket.client module.

Tests are organized by API group following the JQuants test pattern:
- Initialization and context manager
- Validation
- Gamma API (get_events, get_event, get_markets, get_market)
- CLOB API single (get_prices_history, get_midpoint, get_spread, get_orderbook)
- CLOB API bulk (get_midpoints, get_spreads, get_orderbooks, get_prices)
- Data API (get_open_interest, get_trades, get_leaderboard, get_holders)
"""

from collections.abc import Generator
from typing import Any
from unittest.mock import MagicMock, patch

import httpx
import pytest

from market.cache.cache import SQLiteCache, generate_cache_key
from market.polymarket.client import PolymarketClient
from market.polymarket.errors import PolymarketValidationError
from market.polymarket.models import (
    OrderBook,
    PolymarketEvent,
    PolymarketMarket,
    TradeRecord,
)
from market.polymarket.types import FetchOptions, PolymarketConfig
from market.types import MarketDataResult

# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture
def mock_cache() -> SQLiteCache:
    """Create an in-memory SQLiteCache for testing."""
    return SQLiteCache()


@pytest.fixture
def client(mock_cache: SQLiteCache) -> Generator[PolymarketClient]:
    """Create a PolymarketClient with mocked session."""
    with patch("market.polymarket.client.PolymarketSession") as mock_session_cls:
        mock_session_instance = MagicMock()
        mock_session_cls.return_value = mock_session_instance

        c = PolymarketClient(cache=mock_cache)
        c._session = mock_session_instance
        yield c
        c.close()


def _make_response(data: Any) -> MagicMock:
    """Create a mock httpx.Response returning given JSON data."""
    mock_response = MagicMock(spec=httpx.Response)
    mock_response.status_code = 200
    mock_response.json.return_value = data
    return mock_response


# =============================================================================
# Initialization & Context Manager
# =============================================================================


class TestPolymarketClientInit:
    """Tests for PolymarketClient initialization."""

    def test_正常系_初期化(self, client: PolymarketClient) -> None:
        assert client._cache is not None
        assert client._session is not None
        assert client._config is not None

    def test_正常系_カスタム設定(self, mock_cache: SQLiteCache) -> None:
        config = PolymarketConfig(timeout=60.0)
        with patch("market.polymarket.client.PolymarketSession"):
            c = PolymarketClient(config=config, cache=mock_cache)
            assert c._config.timeout == 60.0
            c.close()


class TestPolymarketClientContextManager:
    """Tests for context manager."""

    def test_正常系_コンテキストマネージャ(self, mock_cache: SQLiteCache) -> None:
        with (
            patch("market.polymarket.client.PolymarketSession"),
            PolymarketClient(cache=mock_cache) as c,
        ):
            assert isinstance(c, PolymarketClient)

    def test_正常系_closeが呼ばれる(self, mock_cache: SQLiteCache) -> None:
        with patch("market.polymarket.client.PolymarketSession") as mock_cls:
            mock_session = MagicMock()
            mock_cls.return_value = mock_session
            with PolymarketClient(cache=mock_cache):
                pass
            mock_session.close.assert_called_once()


# =============================================================================
# Validation
# =============================================================================


class TestPolymarketClientValidation:
    """Tests for input validation methods."""

    def test_異常系_空のID(self, client: PolymarketClient) -> None:
        with pytest.raises(PolymarketValidationError, match="must not be empty"):
            client._validate_id("", "test_id")

    def test_異常系_空白のみのID(self, client: PolymarketClient) -> None:
        with pytest.raises(PolymarketValidationError, match="must not be empty"):
            client._validate_id("   ", "test_id")

    def test_正常系_有効なID(self, client: PolymarketClient) -> None:
        # Should not raise
        client._validate_id("0xabc123", "test_id")

    def test_異常系_limitが0(self, client: PolymarketClient) -> None:
        with pytest.raises(PolymarketValidationError, match="limit must be between"):
            client._validate_pagination(0, 0)

    def test_異常系_負のoffset(self, client: PolymarketClient) -> None:
        with pytest.raises(
            PolymarketValidationError, match="offset must be non-negative"
        ):
            client._validate_pagination(10, -1)

    def test_異常系_空のtoken_ids(self, client: PolymarketClient) -> None:
        with pytest.raises(
            PolymarketValidationError, match="token_ids must not be empty"
        ):
            client._validate_token_ids([])

    def test_異常系_空文字列を含むtoken_ids(self, client: PolymarketClient) -> None:
        with pytest.raises(
            PolymarketValidationError,
            match="token_ids must not contain empty strings",
        ):
            client._validate_token_ids(["token1", ""])

    def test_異常系_limitが上限を超えてValidationError(
        self, client: PolymarketClient
    ) -> None:
        with pytest.raises(PolymarketValidationError, match="limit must be between"):
            client.get_events(limit=10_001)

    def test_異常系_不正文字を含むIDでValidationError(
        self, client: PolymarketClient
    ) -> None:
        with pytest.raises(PolymarketValidationError, match="invalid characters"):
            client.get_event("../admin")


# =============================================================================
# Gamma API: get_events
# =============================================================================


class TestGetEvents:
    """Tests for get_events method."""

    def test_正常系_イベント一覧取得(self, client: PolymarketClient) -> None:
        client._session.get_with_retry.return_value = _make_response(
            [
                {
                    "id": "event-001",
                    "title": "US Election 2028",
                    "slug": "us-election-2028",
                    "markets": [],
                },
                {
                    "id": "event-002",
                    "title": "Fed Rate Decision",
                    "slug": "fed-rate-decision",
                    "markets": [],
                },
            ]
        )

        events = client.get_events(limit=10)
        assert isinstance(events, list)
        assert len(events) == 2
        assert all(isinstance(e, PolymarketEvent) for e in events)
        assert events[0].title == "US Election 2028"

    def test_正常系_空の結果(self, client: PolymarketClient) -> None:
        client._session.get_with_retry.return_value = _make_response([])

        events = client.get_events()
        assert events == []

    def test_正常系_キャッシュヒット(
        self, client: PolymarketClient, mock_cache: SQLiteCache
    ) -> None:
        cached_events = [
            {
                "id": "event-001",
                "title": "Cached Event",
                "slug": "cached-event",
                "markets": [],
            }
        ]
        key = generate_cache_key(
            symbol="events_limit100_offset0",
            source="polymarket_gamma",
        )
        mock_cache.set(key, cached_events, ttl=3600)

        events = client.get_events()
        assert len(events) == 1
        assert events[0].title == "Cached Event"
        client._session.get_with_retry.assert_not_called()

    def test_正常系_キャッシュバイパス(self, client: PolymarketClient) -> None:
        client._session.get_with_retry.return_value = _make_response([])

        client.get_events(options=FetchOptions(force_refresh=True))
        client._session.get_with_retry.assert_called_once()

    def test_異常系_limitが0(self, client: PolymarketClient) -> None:
        with pytest.raises(PolymarketValidationError):
            client.get_events(limit=0)


# =============================================================================
# Gamma API: get_event
# =============================================================================


class TestGetEvent:
    """Tests for get_event method."""

    def test_正常系_単一イベント取得(self, client: PolymarketClient) -> None:
        client._session.get_with_retry.return_value = _make_response(
            {
                "id": "event-001",
                "title": "US Election 2028",
                "slug": "us-election-2028",
                "markets": [
                    {
                        "condition_id": "0xabc",
                        "question": "Who will win?",
                        "tokens": [
                            {"token_id": "tok1", "outcome": "Yes", "price": 0.65}
                        ],
                    }
                ],
            }
        )

        event = client.get_event("event-001")
        assert isinstance(event, PolymarketEvent)
        assert event.id == "event-001"
        assert len(event.markets) == 1

    def test_異常系_空のevent_id(self, client: PolymarketClient) -> None:
        with pytest.raises(PolymarketValidationError, match="must not be empty"):
            client.get_event("")

    def test_正常系_キャッシュヒット(
        self, client: PolymarketClient, mock_cache: SQLiteCache
    ) -> None:
        cached = {
            "id": "event-001",
            "title": "Cached",
            "slug": "cached",
            "markets": [],
        }
        key = generate_cache_key(
            symbol="event-001",
            source="polymarket_gamma_event",
        )
        mock_cache.set(key, cached, ttl=3600)

        event = client.get_event("event-001")
        assert event.title == "Cached"
        client._session.get_with_retry.assert_not_called()


# =============================================================================
# Gamma API: get_markets
# =============================================================================


class TestGetMarkets:
    """Tests for get_markets method."""

    def test_正常系_マーケット一覧取得(self, client: PolymarketClient) -> None:
        client._session.get_with_retry.return_value = _make_response(
            [
                {
                    "condition_id": "0xabc",
                    "question": "Will X happen?",
                    "tokens": [{"token_id": "tok1", "outcome": "Yes", "price": 0.65}],
                },
            ]
        )

        markets = client.get_markets(limit=5)
        assert isinstance(markets, list)
        assert len(markets) == 1
        assert isinstance(markets[0], PolymarketMarket)
        assert markets[0].condition_id == "0xabc"

    def test_正常系_空の結果(self, client: PolymarketClient) -> None:
        client._session.get_with_retry.return_value = _make_response([])

        markets = client.get_markets()
        assert markets == []


# =============================================================================
# Gamma API: get_market
# =============================================================================


class TestGetMarket:
    """Tests for get_market method."""

    def test_正常系_単一マーケット取得(self, client: PolymarketClient) -> None:
        client._session.get_with_retry.return_value = _make_response(
            {
                "condition_id": "0xabc123",
                "question": "Will BTC reach 200k?",
                "tokens": [{"token_id": "tok1", "outcome": "Yes", "price": 0.35}],
                "volume": 1500000.0,
            }
        )

        market = client.get_market("0xabc123")
        assert isinstance(market, PolymarketMarket)
        assert market.condition_id == "0xabc123"
        assert market.volume == pytest.approx(1500000.0)

    def test_異常系_空のcondition_id(self, client: PolymarketClient) -> None:
        with pytest.raises(PolymarketValidationError, match="must not be empty"):
            client.get_market("")

    def test_正常系_キャッシュヒット(
        self, client: PolymarketClient, mock_cache: SQLiteCache
    ) -> None:
        cached = {
            "condition_id": "0xabc",
            "question": "Cached?",
            "tokens": [],
        }
        key = generate_cache_key(
            symbol="0xabc",
            source="polymarket_gamma_market",
        )
        mock_cache.set(key, cached, ttl=3600)

        market = client.get_market("0xabc")
        assert market.question == "Cached?"
        client._session.get_with_retry.assert_not_called()


# =============================================================================
# CLOB API single: get_prices_history
# =============================================================================


class TestGetPricesHistory:
    """Tests for get_prices_history method."""

    def test_正常系_価格履歴取得(self, client: PolymarketClient) -> None:
        client._session.get_with_retry.return_value = _make_response(
            {
                "history": [
                    {"t": 1700000000, "p": 0.55},
                    {"t": 1700003600, "p": 0.60},
                    {"t": 1700007200, "p": 0.58},
                ]
            }
        )

        result = client.get_prices_history("token123")
        assert isinstance(result, MarketDataResult)
        assert result.symbol == "token123"
        assert len(result.data) == 3
        assert "timestamp" in result.data.columns
        assert "price" in result.data.columns
        assert result.from_cache is False

    def test_正常系_空の履歴(self, client: PolymarketClient) -> None:
        client._session.get_with_retry.return_value = _make_response({"history": []})

        result = client.get_prices_history("token123")
        assert isinstance(result, MarketDataResult)
        assert result.data.empty

    def test_異常系_空のtoken_id(self, client: PolymarketClient) -> None:
        with pytest.raises(PolymarketValidationError, match="must not be empty"):
            client.get_prices_history("")

    def test_正常系_キャッシュヒット(
        self, client: PolymarketClient, mock_cache: SQLiteCache
    ) -> None:
        from datetime import UTC, datetime

        import pandas as pd

        from market.polymarket.types import PriceInterval
        from market.types import DataSource

        cached_result = MarketDataResult(
            symbol="token123",
            data=pd.DataFrame({"timestamp": [1700000000], "price": [0.55]}),
            source=DataSource.LOCAL,
            fetched_at=datetime.now(tz=UTC),
            from_cache=True,
        )
        key = generate_cache_key(
            symbol="token123",
            interval=str(PriceInterval.ONE_DAY),
            source="polymarket_clob_prices",
        )
        mock_cache.set(key, cached_result, ttl=3600)

        result = client.get_prices_history("token123")
        assert isinstance(result, MarketDataResult)
        assert len(result.data) == 1
        client._session.get_with_retry.assert_not_called()


# =============================================================================
# CLOB API single: get_midpoint
# =============================================================================


class TestGetMidpoint:
    """Tests for get_midpoint method."""

    def test_正常系_ミッドポイント取得(self, client: PolymarketClient) -> None:
        client._session.get_with_retry.return_value = _make_response({"mid": "0.65"})

        mid = client.get_midpoint("token123")
        assert isinstance(mid, float)
        assert mid == pytest.approx(0.65)

    def test_正常系_ゼロのミッドポイント(self, client: PolymarketClient) -> None:
        client._session.get_with_retry.return_value = _make_response({})

        mid = client.get_midpoint("token123")
        assert mid == pytest.approx(0.0)

    def test_異常系_空のtoken_id(self, client: PolymarketClient) -> None:
        with pytest.raises(PolymarketValidationError, match="must not be empty"):
            client.get_midpoint("")


# =============================================================================
# CLOB API single: get_spread
# =============================================================================


class TestGetSpread:
    """Tests for get_spread method."""

    def test_正常系_スプレッド取得(self, client: PolymarketClient) -> None:
        client._session.get_with_retry.return_value = _make_response(
            {"bid": "0.60", "ask": "0.65", "spread": "0.05"}
        )

        spread = client.get_spread("token123")
        assert isinstance(spread, dict)
        assert spread["bid"] == pytest.approx(0.60)
        assert spread["ask"] == pytest.approx(0.65)
        assert spread["spread"] == pytest.approx(0.05)

    def test_正常系_空のレスポンス(self, client: PolymarketClient) -> None:
        client._session.get_with_retry.return_value = _make_response({})

        spread = client.get_spread("token123")
        assert spread["bid"] == pytest.approx(0.0)
        assert spread["ask"] == pytest.approx(0.0)
        assert spread["spread"] == pytest.approx(0.0)

    def test_異常系_空のtoken_id(self, client: PolymarketClient) -> None:
        with pytest.raises(PolymarketValidationError, match="must not be empty"):
            client.get_spread("")


# =============================================================================
# CLOB API single: get_orderbook
# =============================================================================


class TestGetOrderbook:
    """Tests for get_orderbook method."""

    def test_正常系_オーダーブック取得(self, client: PolymarketClient) -> None:
        client._session.get_with_retry.return_value = _make_response(
            {
                "market": "0xabc",
                "asset_id": "token123",
                "bids": [
                    {"price": 0.60, "size": 1000.0},
                    {"price": 0.59, "size": 500.0},
                ],
                "asks": [
                    {"price": 0.65, "size": 800.0},
                ],
            }
        )

        book = client.get_orderbook("token123")
        assert isinstance(book, OrderBook)
        assert len(book.bids) == 2
        assert len(book.asks) == 1
        assert book.bids[0].price == pytest.approx(0.60)
        assert book.asks[0].price == pytest.approx(0.65)

    def test_正常系_空のオーダーブック(self, client: PolymarketClient) -> None:
        client._session.get_with_retry.return_value = _make_response(
            {"market": "", "asset_id": "token123", "bids": [], "asks": []}
        )

        book = client.get_orderbook("token123")
        assert isinstance(book, OrderBook)
        assert len(book.bids) == 0
        assert len(book.asks) == 0

    def test_異常系_空のtoken_id(self, client: PolymarketClient) -> None:
        with pytest.raises(PolymarketValidationError, match="must not be empty"):
            client.get_orderbook("")

    def test_正常系_キャッシュヒット(
        self, client: PolymarketClient, mock_cache: SQLiteCache
    ) -> None:
        cached_book = {
            "market": "0xabc",
            "asset_id": "token123",
            "bids": [],
            "asks": [],
        }
        key = generate_cache_key(
            symbol="token123",
            source="polymarket_clob_orderbook",
        )
        mock_cache.set(key, cached_book, ttl=3600)

        book = client.get_orderbook("token123")
        assert isinstance(book, OrderBook)
        assert book.market == "0xabc"
        client._session.get_with_retry.assert_not_called()


# =============================================================================
# CLOB API bulk: get_midpoints
# =============================================================================


class TestGetMidpoints:
    """Tests for get_midpoints method."""

    def test_正常系_複数ミッドポイント取得(self, client: PolymarketClient) -> None:
        client._session.get_with_retry.return_value = _make_response(
            {"token1": "0.55", "token2": "0.70"}
        )

        mids = client.get_midpoints(["token1", "token2"])
        assert isinstance(mids, dict)
        assert mids["token1"] == pytest.approx(0.55)
        assert mids["token2"] == pytest.approx(0.70)

    def test_異常系_空のリスト(self, client: PolymarketClient) -> None:
        with pytest.raises(PolymarketValidationError, match="must not be empty"):
            client.get_midpoints([])


# =============================================================================
# CLOB API bulk: get_spreads
# =============================================================================


class TestGetSpreads:
    """Tests for get_spreads method."""

    def test_正常系_複数スプレッド取得(self, client: PolymarketClient) -> None:
        client._session.get_with_retry.return_value = _make_response(
            {
                "token1": {"bid": "0.55", "ask": "0.60", "spread": "0.05"},
                "token2": {"bid": "0.70", "ask": "0.75", "spread": "0.05"},
            }
        )

        spreads = client.get_spreads(["token1", "token2"])
        assert isinstance(spreads, dict)
        assert spreads["token1"]["bid"] == pytest.approx(0.55)
        assert spreads["token2"]["ask"] == pytest.approx(0.75)

    def test_異常系_空のリスト(self, client: PolymarketClient) -> None:
        with pytest.raises(PolymarketValidationError, match="must not be empty"):
            client.get_spreads([])


# =============================================================================
# CLOB API bulk: get_orderbooks
# =============================================================================


class TestGetOrderbooks:
    """Tests for get_orderbooks method."""

    def test_正常系_複数オーダーブック取得(self, client: PolymarketClient) -> None:
        client._session.get_with_retry.return_value = _make_response(
            {
                "token1": {
                    "market": "0xabc",
                    "asset_id": "token1",
                    "bids": [{"price": 0.50, "size": 100.0}],
                    "asks": [{"price": 0.55, "size": 200.0}],
                },
                "token2": {
                    "market": "0xdef",
                    "asset_id": "token2",
                    "bids": [],
                    "asks": [],
                },
            }
        )

        books = client.get_orderbooks(["token1", "token2"])
        assert isinstance(books, dict)
        assert len(books) == 2
        assert isinstance(books["token1"], OrderBook)
        assert len(books["token1"].bids) == 1

    def test_異常系_空のリスト(self, client: PolymarketClient) -> None:
        with pytest.raises(PolymarketValidationError, match="must not be empty"):
            client.get_orderbooks([])


# =============================================================================
# CLOB API bulk: get_prices
# =============================================================================


class TestGetPrices:
    """Tests for get_prices method."""

    def test_正常系_複数価格取得(self, client: PolymarketClient) -> None:
        client._session.get_with_retry.return_value = _make_response(
            {"token1": "0.55", "token2": "0.70"}
        )

        prices = client.get_prices(["token1", "token2"])
        assert isinstance(prices, dict)
        assert prices["token1"] == pytest.approx(0.55)
        assert prices["token2"] == pytest.approx(0.70)

    def test_異常系_空のリスト(self, client: PolymarketClient) -> None:
        with pytest.raises(PolymarketValidationError, match="must not be empty"):
            client.get_prices([])

    def test_正常系_キャッシュバイパス(self, client: PolymarketClient) -> None:
        client._session.get_with_retry.return_value = _make_response({"token1": "0.55"})

        client.get_prices(["token1"], options=FetchOptions(force_refresh=True))
        client._session.get_with_retry.assert_called_once()


# =============================================================================
# Data API: get_open_interest
# =============================================================================


class TestGetOpenInterest:
    """Tests for get_open_interest method."""

    def test_正常系_OI取得(self, client: PolymarketClient) -> None:
        client._session.get_with_retry.return_value = _make_response(
            {"total_oi": 5000000, "yes_oi": 3000000, "no_oi": 2000000}
        )

        oi = client.get_open_interest("0xabc123")
        assert isinstance(oi, dict)
        assert oi["total_oi"] == 5000000

    def test_異常系_空のcondition_id(self, client: PolymarketClient) -> None:
        with pytest.raises(PolymarketValidationError, match="must not be empty"):
            client.get_open_interest("")

    def test_正常系_キャッシュヒット(
        self, client: PolymarketClient, mock_cache: SQLiteCache
    ) -> None:
        cached = {"total_oi": 1000}
        key = generate_cache_key(
            symbol="0xabc",
            source="polymarket_data_oi",
        )
        mock_cache.set(key, cached, ttl=3600)

        oi = client.get_open_interest("0xabc")
        assert oi["total_oi"] == 1000
        client._session.get_with_retry.assert_not_called()


# =============================================================================
# Data API: get_trades
# =============================================================================


class TestGetTrades:
    """Tests for get_trades method."""

    def test_正常系_取引履歴取得(self, client: PolymarketClient) -> None:
        client._session.get_with_retry.return_value = _make_response(
            [
                {
                    "id": "trade-001",
                    "market": "0xabc",
                    "asset_id": "token1",
                    "price": 0.65,
                    "size": 500.0,
                    "side": "BUY",
                },
                {
                    "id": "trade-002",
                    "market": "0xabc",
                    "asset_id": "token1",
                    "price": 0.64,
                    "size": 300.0,
                    "side": "SELL",
                },
            ]
        )

        trades = client.get_trades("0xabc", limit=10)
        assert isinstance(trades, list)
        assert len(trades) == 2
        assert all(isinstance(t, TradeRecord) for t in trades)
        assert trades[0].price == pytest.approx(0.65)

    def test_正常系_空の取引(self, client: PolymarketClient) -> None:
        client._session.get_with_retry.return_value = _make_response([])

        trades = client.get_trades("0xabc")
        assert trades == []

    def test_異常系_空のcondition_id(self, client: PolymarketClient) -> None:
        with pytest.raises(PolymarketValidationError, match="must not be empty"):
            client.get_trades("")

    def test_異常系_負のlimit(self, client: PolymarketClient) -> None:
        with pytest.raises(PolymarketValidationError, match="limit must be positive"):
            client.get_trades("0xabc", limit=-1)


# =============================================================================
# Data API: get_leaderboard
# =============================================================================


class TestGetLeaderboard:
    """Tests for get_leaderboard method."""

    def test_正常系_リーダーボード取得(self, client: PolymarketClient) -> None:
        client._session.get_with_retry.return_value = _make_response(
            [
                {"rank": 1, "address": "0x111", "profit": 50000.0},
                {"rank": 2, "address": "0x222", "profit": 30000.0},
            ]
        )

        board = client.get_leaderboard(limit=10)
        assert isinstance(board, list)
        assert len(board) == 2
        assert board[0]["rank"] == 1

    def test_正常系_空のリーダーボード(self, client: PolymarketClient) -> None:
        client._session.get_with_retry.return_value = _make_response([])

        board = client.get_leaderboard()
        assert board == []

    def test_異常系_limitが0(self, client: PolymarketClient) -> None:
        with pytest.raises(PolymarketValidationError, match="limit must be positive"):
            client.get_leaderboard(limit=0)


# =============================================================================
# Data API: get_holders
# =============================================================================


class TestGetHolders:
    """Tests for get_holders method."""

    def test_正常系_ホルダー一覧取得(self, client: PolymarketClient) -> None:
        client._session.get_with_retry.return_value = _make_response(
            [
                {"address": "0x111", "balance": 1000.0},
                {"address": "0x222", "balance": 500.0},
            ]
        )

        holders = client.get_holders("0xabc123")
        assert isinstance(holders, list)
        assert len(holders) == 2

    def test_異常系_空のcondition_id(self, client: PolymarketClient) -> None:
        with pytest.raises(PolymarketValidationError, match="must not be empty"):
            client.get_holders("")

    def test_正常系_キャッシュヒット(
        self, client: PolymarketClient, mock_cache: SQLiteCache
    ) -> None:
        cached = [{"address": "0x111", "balance": 1000.0}]
        key = generate_cache_key(
            symbol="0xabc",
            source="polymarket_data_holders",
        )
        mock_cache.set(key, cached, ttl=3600)

        holders = client.get_holders("0xabc")
        assert len(holders) == 1
        client._session.get_with_retry.assert_not_called()


# =============================================================================
# Internal: _request
# =============================================================================


class TestRequest:
    """Tests for internal _request method."""

    def test_正常系_GammaAPIリクエスト(self, client: PolymarketClient) -> None:
        client._session.get_with_retry.return_value = _make_response({"key": "value"})

        result = client._gamma_request("/test")
        assert result == {"key": "value"}
        # Verify URL contains gamma base
        call_url = client._session.get_with_retry.call_args[0][0]
        assert "gamma-api.polymarket.com" in call_url

    def test_正常系_CLOBAPIリクエスト(self, client: PolymarketClient) -> None:
        client._session.get_with_retry.return_value = _make_response({"key": "value"})

        result = client._clob_request("/test")
        assert result == {"key": "value"}
        call_url = client._session.get_with_retry.call_args[0][0]
        assert "clob.polymarket.com" in call_url

    def test_正常系_DataAPIリクエスト(self, client: PolymarketClient) -> None:
        client._session.get_with_retry.return_value = _make_response({"key": "value"})

        result = client._data_request("/test")
        assert result == {"key": "value"}
        call_url = client._session.get_with_retry.call_args[0][0]
        assert "data-api.polymarket.com" in call_url
