"""Unit tests for NasdaqClient market movers endpoint and parser.

Tests cover:
- parse_market_movers: 3 sections, empty data, partial sections
- get_market_movers: normal, cache hit/miss, force refresh

See Also
--------
market.nasdaq.client : NasdaqClient implementation.
market.nasdaq.client_parsers : parse_market_movers implementation.
market.nasdaq.client_types : MarketMover and MoverSection types.
tests.market.nasdaq.unit.test_client_calendar : Reference test patterns.
tests.market.nasdaq.conftest : Shared fixtures.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any
from unittest.mock import MagicMock

import pytest

from market.nasdaq.client_parsers import parse_market_movers
from market.nasdaq.client_types import (
    MarketMover,
    MoverSection,
    NasdaqFetchOptions,
)

if TYPE_CHECKING:
    from market.nasdaq.client import NasdaqClient

# =============================================================================
# MoverSection Enum Tests
# =============================================================================


class TestMoverSection:
    """Tests for MoverSection str Enum."""

    def test_正常系_3値が定義されている(self) -> None:
        """MoverSection has exactly 3 values."""
        assert len(MoverSection) == 3

    def test_正常系_most_advancedの値(self) -> None:
        """MoverSection.MOST_ADVANCED value is 'most_advanced'."""
        assert MoverSection.MOST_ADVANCED.value == "most_advanced"

    def test_正常系_most_declinedの値(self) -> None:
        """MoverSection.MOST_DECLINED value is 'most_declined'."""
        assert MoverSection.MOST_DECLINED.value == "most_declined"

    def test_正常系_most_activeの値(self) -> None:
        """MoverSection.MOST_ACTIVE value is 'most_active'."""
        assert MoverSection.MOST_ACTIVE.value == "most_active"

    def test_正常系_strEnumとして文字列比較できる(self) -> None:
        """MoverSection values can be compared as strings."""
        assert MoverSection.MOST_ADVANCED == "most_advanced"


# =============================================================================
# MarketMover Dataclass Tests
# =============================================================================


class TestMarketMover:
    """Tests for MarketMover frozen dataclass."""

    def test_正常系_6フィールドを持つ(self) -> None:
        """MarketMover has 6 fields."""
        record = MarketMover(
            symbol="AAPL",
            name="Apple Inc.",
            price="$230.00",
            change="5.00",
            change_percent="2.22%",
            volume="48,123,456",
        )
        assert record.symbol == "AAPL"
        assert record.name == "Apple Inc."
        assert record.price == "$230.00"
        assert record.change == "5.00"
        assert record.change_percent == "2.22%"
        assert record.volume == "48,123,456"

    def test_正常系_frozenで変更不可(self) -> None:
        """MarketMover is frozen (immutable)."""
        record = MarketMover(symbol="AAPL")
        with pytest.raises(AttributeError):
            record.symbol = "MSFT"  # type: ignore[misc]

    def test_正常系_symbolのみ必須(self) -> None:
        """MarketMover only requires symbol; other fields default to None."""
        record = MarketMover(symbol="AAPL")
        assert record.symbol == "AAPL"
        assert record.name is None
        assert record.price is None
        assert record.change is None
        assert record.change_percent is None
        assert record.volume is None


# =============================================================================
# parse_market_movers Tests
# =============================================================================


class TestParseMarketMovers:
    """Tests for parse_market_movers parser function."""

    def test_正常系_3セクション全てをパースできる(self) -> None:
        """Parses all 3 sections into dict[str, list[MarketMover]]."""
        data: dict[str, Any] = {
            "MostAdvanced": {
                "rows": [
                    {
                        "symbol": "AAPL",
                        "name": "Apple Inc.",
                        "lastSale": "$230.00",
                        "netChange": "5.00",
                        "percentageChange": "2.22%",
                        "volume": "48,123,456",
                    },
                ],
            },
            "MostDeclined": {
                "rows": [
                    {
                        "symbol": "MSFT",
                        "name": "Microsoft",
                        "lastSale": "$410.00",
                        "netChange": "-3.50",
                        "percentageChange": "-0.85%",
                        "volume": "22,456,789",
                    },
                ],
            },
            "MostActive": {
                "rows": [
                    {
                        "symbol": "NVDA",
                        "name": "NVIDIA",
                        "lastSale": "$140.15",
                        "netChange": "1.00",
                        "percentageChange": "0.72%",
                        "volume": "312,456,789",
                    },
                ],
            },
        }

        result = parse_market_movers(data)

        assert len(result) == 3
        assert "most_advanced" in result
        assert "most_declined" in result
        assert "most_active" in result

        assert len(result["most_advanced"]) == 1
        assert isinstance(result["most_advanced"][0], MarketMover)
        assert result["most_advanced"][0].symbol == "AAPL"
        assert result["most_advanced"][0].price == "$230.00"

        assert result["most_declined"][0].symbol == "MSFT"
        assert result["most_declined"][0].change == "-3.50"

        assert result["most_active"][0].symbol == "NVDA"
        assert result["most_active"][0].volume == "312,456,789"

    def test_正常系_空データで空リストを返す(self) -> None:
        """Returns dict with empty lists when no rows exist."""
        data: dict[str, Any] = {}

        result = parse_market_movers(data)

        assert len(result) == 3
        assert result["most_advanced"] == []
        assert result["most_declined"] == []
        assert result["most_active"] == []

    def test_正常系_部分的なセクションのみ存在(self) -> None:
        """Handles partial sections (only some sections have data)."""
        data: dict[str, Any] = {
            "MostAdvanced": {
                "rows": [
                    {
                        "symbol": "AAPL",
                        "name": "Apple Inc.",
                        "lastSale": "$230.00",
                        "netChange": "5.00",
                        "percentageChange": "2.22%",
                        "volume": "48,123,456",
                    },
                ],
            },
        }

        result = parse_market_movers(data)

        assert len(result["most_advanced"]) == 1
        assert result["most_declined"] == []
        assert result["most_active"] == []

    def test_正常系_複数レコードを含むセクション(self) -> None:
        """Parses multiple records within a single section."""
        data: dict[str, Any] = {
            "MostAdvanced": {
                "rows": [
                    {"symbol": "AAPL", "name": "Apple"},
                    {"symbol": "MSFT", "name": "Microsoft"},
                    {"symbol": "GOOGL", "name": "Alphabet"},
                ],
            },
        }

        result = parse_market_movers(data)

        assert len(result["most_advanced"]) == 3
        assert result["most_advanced"][0].symbol == "AAPL"
        assert result["most_advanced"][1].symbol == "MSFT"
        assert result["most_advanced"][2].symbol == "GOOGL"


# =============================================================================
# NasdaqClient.get_market_movers Tests
# =============================================================================


class TestGetMarketMovers:
    """Tests for NasdaqClient.get_market_movers."""

    def test_正常系_market_moversを取得できる(
        self,
        nasdaq_client: NasdaqClient,
        mock_cache: MagicMock,
        mock_nasdaq_session: MagicMock,
    ) -> None:
        """Fetches market movers from API and returns parsed dict."""
        mock_cache.get.return_value = None

        raw_response: dict[str, Any] = {
            "data": {
                "MostAdvanced": {
                    "rows": [
                        {
                            "symbol": "AAPL",
                            "name": "Apple Inc.",
                            "lastSale": "$230.00",
                            "netChange": "5.00",
                            "percentageChange": "2.22%",
                            "volume": "48,123,456",
                        },
                    ],
                },
                "MostDeclined": {"rows": []},
                "MostActive": {"rows": []},
            },
            "message": None,
            "status": {"rCode": 200, "bCodeMessage": None},
        }
        mock_response = MagicMock()
        mock_response.json.return_value = raw_response
        mock_nasdaq_session.get_with_retry.return_value = mock_response

        result = nasdaq_client.get_market_movers()

        assert "most_advanced" in result
        assert len(result["most_advanced"]) == 1
        assert isinstance(result["most_advanced"][0], MarketMover)
        assert result["most_advanced"][0].symbol == "AAPL"

    def test_正常系_キャッシュヒット時にAPIを呼ばない(
        self,
        nasdaq_client: NasdaqClient,
        mock_cache: MagicMock,
        mock_nasdaq_session: MagicMock,
    ) -> None:
        """When cache has data, API is not called."""
        cached_data = {
            "most_advanced": [MarketMover(symbol="AAPL", name="Apple Inc.")],
            "most_declined": [],
            "most_active": [],
        }
        mock_cache.get.return_value = cached_data

        result = nasdaq_client.get_market_movers()

        assert result == cached_data
        mock_nasdaq_session.get_with_retry.assert_not_called()

    def test_正常系_force_refreshでキャッシュを無視(
        self,
        nasdaq_client: NasdaqClient,
        mock_cache: MagicMock,
        mock_nasdaq_session: MagicMock,
    ) -> None:
        """Force refresh bypasses cache."""
        mock_cache.get.return_value = "old_data"

        raw_response: dict[str, Any] = {
            "data": {},
            "message": None,
            "status": {"rCode": 200, "bCodeMessage": None},
        }
        mock_response = MagicMock()
        mock_response.json.return_value = raw_response
        mock_nasdaq_session.get_with_retry.return_value = mock_response

        options = NasdaqFetchOptions(force_refresh=True)
        nasdaq_client.get_market_movers(options=options)

        mock_cache.get.assert_not_called()
        mock_nasdaq_session.get_with_retry.assert_called_once()

    def test_正常系_キャッシュミス時にAPIを呼びキャッシュに保存(
        self,
        nasdaq_client: NasdaqClient,
        mock_cache: MagicMock,
        mock_nasdaq_session: MagicMock,
    ) -> None:
        """Cache miss triggers API call and stores result in cache."""
        mock_cache.get.return_value = None

        raw_response: dict[str, Any] = {
            "data": {
                "MostAdvanced": {"rows": []},
                "MostDeclined": {"rows": []},
                "MostActive": {"rows": []},
            },
            "message": None,
            "status": {"rCode": 200, "bCodeMessage": None},
        }
        mock_response = MagicMock()
        mock_response.json.return_value = raw_response
        mock_nasdaq_session.get_with_retry.return_value = mock_response

        nasdaq_client.get_market_movers()

        mock_nasdaq_session.get_with_retry.assert_called_once()
        mock_cache.set.assert_called_once()
