"""Unit tests for NasdaqClient ETF screener endpoint and parser.

Tests cover:
- EtfRecord: field count, frozen, defaults
- parse_etf_screener: normal, empty data, partial fields
- get_etf_screener: normal, cache hit/miss, force refresh

See Also
--------
market.nasdaq.client : NasdaqClient implementation.
market.nasdaq.client_parsers : parse_etf_screener implementation.
market.nasdaq.client_types : EtfRecord type.
tests.market.nasdaq.unit.test_client_calendar : Reference test patterns.
tests.market.nasdaq.conftest : Shared fixtures.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any
from unittest.mock import MagicMock

import pytest

from market.nasdaq.client_parsers import parse_etf_screener
from market.nasdaq.client_types import (
    EtfRecord,
    NasdaqFetchOptions,
)

if TYPE_CHECKING:
    from market.nasdaq.client import NasdaqClient

# =============================================================================
# EtfRecord Dataclass Tests
# =============================================================================


class TestEtfRecord:
    """Tests for EtfRecord frozen dataclass."""

    def test_正常系_10フィールドを持つ(self) -> None:
        """EtfRecord has 10 fields."""
        record = EtfRecord(
            symbol="SPY",
            name="SPDR S&P 500 ETF Trust",
            last_sale="$590.50",
            net_change="-2.30",
            pct_change="-0.39%",
            volume="48,123,456",
            country="United States",
            sector="Technology",
            industry="Index Fund",
            url="/market-activity/funds-and-etfs/spy",
        )
        assert record.symbol == "SPY"
        assert record.name == "SPDR S&P 500 ETF Trust"
        assert record.last_sale == "$590.50"
        assert record.net_change == "-2.30"
        assert record.pct_change == "-0.39%"
        assert record.volume == "48,123,456"
        assert record.country == "United States"
        assert record.sector == "Technology"
        assert record.industry == "Index Fund"
        assert record.url == "/market-activity/funds-and-etfs/spy"

    def test_正常系_frozenで変更不可(self) -> None:
        """EtfRecord is frozen (immutable)."""
        record = EtfRecord(symbol="SPY")
        with pytest.raises(AttributeError):
            record.symbol = "QQQ"  # type: ignore[misc]

    def test_正常系_symbolのみ必須(self) -> None:
        """EtfRecord only requires symbol; other fields default to None."""
        record = EtfRecord(symbol="SPY")
        assert record.symbol == "SPY"
        assert record.name is None
        assert record.last_sale is None
        assert record.net_change is None
        assert record.pct_change is None
        assert record.volume is None
        assert record.country is None
        assert record.sector is None
        assert record.industry is None
        assert record.url is None


# =============================================================================
# parse_etf_screener Tests
# =============================================================================


class TestParseEtfScreener:
    """Tests for parse_etf_screener parser function."""

    def test_正常系_data_table_rows構造をパースできる(self) -> None:
        """Parses data.table.rows structure into EtfRecord list."""
        data: dict[str, Any] = {
            "table": {
                "rows": [
                    {
                        "symbol": "SPY",
                        "name": "SPDR S&P 500 ETF Trust",
                        "lastsale": "$590.50",
                        "netchange": "-2.30",
                        "pctchange": "-0.39%",
                        "volume": "48,123,456",
                        "country": "United States",
                        "sector": "",
                        "industry": "",
                        "url": "/market-activity/funds-and-etfs/spy",
                    },
                ],
            },
        }

        result = parse_etf_screener(data)

        assert len(result) == 1
        assert isinstance(result[0], EtfRecord)
        assert result[0].symbol == "SPY"
        assert result[0].name == "SPDR S&P 500 ETF Trust"
        assert result[0].last_sale == "$590.50"
        assert result[0].net_change == "-2.30"
        assert result[0].pct_change == "-0.39%"
        assert result[0].volume == "48,123,456"
        assert result[0].country == "United States"
        assert result[0].url == "/market-activity/funds-and-etfs/spy"

    def test_正常系_空データで空リストを返す(self) -> None:
        """Returns empty list when no rows exist."""
        data: dict[str, Any] = {"table": {"rows": []}}

        result = parse_etf_screener(data)

        assert result == []

    def test_正常系_tableキーがない場合空リストを返す(self) -> None:
        """Returns empty list when table key is missing."""
        data: dict[str, Any] = {}

        result = parse_etf_screener(data)

        assert result == []

    def test_正常系_複数レコードをパースできる(self) -> None:
        """Parses multiple ETF records."""
        data: dict[str, Any] = {
            "table": {
                "rows": [
                    {
                        "symbol": "SPY",
                        "name": "SPDR S&P 500 ETF Trust",
                        "lastsale": "$590.50",
                        "netchange": "-2.30",
                        "pctchange": "-0.39%",
                        "volume": "48,123,456",
                        "country": "United States",
                        "sector": "",
                        "industry": "",
                        "url": "/market-activity/funds-and-etfs/spy",
                    },
                    {
                        "symbol": "QQQ",
                        "name": "Invesco QQQ Trust",
                        "lastsale": "$490.20",
                        "netchange": "1.50",
                        "pctchange": "0.31%",
                        "volume": "32,456,789",
                        "country": "United States",
                        "sector": "",
                        "industry": "",
                        "url": "/market-activity/funds-and-etfs/qqq",
                    },
                    {
                        "symbol": "IWM",
                        "name": "iShares Russell 2000 ETF",
                        "lastsale": "$210.30",
                        "netchange": "-0.80",
                        "pctchange": "-0.38%",
                        "volume": "18,234,567",
                        "country": "United States",
                        "sector": "",
                        "industry": "",
                        "url": "/market-activity/funds-and-etfs/iwm",
                    },
                ],
            },
        }

        result = parse_etf_screener(data)

        assert len(result) == 3
        assert result[0].symbol == "SPY"
        assert result[1].symbol == "QQQ"
        assert result[2].symbol == "IWM"

    def test_正常系_部分的なフィールドでもパースできる(self) -> None:
        """Handles records with missing optional fields."""
        data: dict[str, Any] = {
            "table": {
                "rows": [
                    {
                        "symbol": "XYZ",
                        "name": "Test ETF",
                    },
                ],
            },
        }

        result = parse_etf_screener(data)

        assert len(result) == 1
        assert result[0].symbol == "XYZ"
        assert result[0].name == "Test ETF"
        assert result[0].last_sale is None
        assert result[0].volume is None

    def test_正常系_records_data_rows構造をパースできる(self) -> None:
        """Parses new API structure: records -> data -> rows."""
        data: dict[str, Any] = {
            "records": {
                "totalrecords": 4405,
                "data": {
                    "rows": [
                        {
                            "symbol": "CSRE",
                            "companyName": "Cohen & Steers Real Estate Active ETF",
                            "lastSalePrice": "$26.15",
                            "netChange": "-0.10",
                            "percentageChange": "-0.38%",
                            "volume": "1,234",
                            "country": "United States",
                            "sector": "Real Estate",
                            "industry": "Real Estate",
                            "url": "/market-activity/funds-and-etfs/csre",
                        },
                        {
                            "symbol": "SPY",
                            "companyName": "SPDR S&P 500 ETF Trust",
                            "lastSalePrice": "$590.50",
                            "netChange": "-2.30",
                            "percentageChange": "-0.39%",
                            "volume": "48,123,456",
                            "country": "United States",
                            "sector": "",
                            "industry": "",
                            "url": "/market-activity/funds-and-etfs/spy",
                        },
                    ],
                },
            },
        }

        result = parse_etf_screener(data)

        assert len(result) == 2
        assert isinstance(result[0], EtfRecord)
        assert result[0].symbol == "CSRE"
        assert result[0].name == "Cohen & Steers Real Estate Active ETF"
        assert result[0].last_sale == "$26.15"
        assert result[0].net_change == "-0.10"
        assert result[0].pct_change == "-0.38%"
        assert result[0].volume == "1,234"
        assert result[1].symbol == "SPY"

    def test_正常系_新APIフィールド名でもフォールバックで旧名を使う(self) -> None:
        """New API field names (companyName, lastSalePrice) are used with fallback to old."""
        data: dict[str, Any] = {
            "table": {
                "rows": [
                    {
                        "symbol": "TEST",
                        "companyName": "Test ETF via companyName",
                        "lastSalePrice": "$100.00",
                        "netChange": "1.50",
                        "percentageChange": "1.52%",
                        "volume": "999",
                    },
                ],
            },
        }

        result = parse_etf_screener(data)

        assert len(result) == 1
        assert result[0].name == "Test ETF via companyName"
        assert result[0].last_sale == "$100.00"
        assert result[0].net_change == "1.50"
        assert result[0].pct_change == "1.52%"


# =============================================================================
# NasdaqClient.get_etf_screener Tests
# =============================================================================


class TestGetEtfScreener:
    """Tests for NasdaqClient.get_etf_screener."""

    def test_正常系_etf_screenerを取得できる(
        self,
        nasdaq_client: NasdaqClient,
        mock_cache: MagicMock,
        mock_nasdaq_session: MagicMock,
    ) -> None:
        """Fetches ETF screener from API and returns EtfRecord list."""
        mock_cache.get.return_value = None

        raw_response: dict[str, Any] = {
            "data": {
                "table": {
                    "rows": [
                        {
                            "symbol": "SPY",
                            "name": "SPDR S&P 500 ETF Trust",
                            "lastsale": "$590.50",
                            "netchange": "-2.30",
                            "pctchange": "-0.39%",
                            "volume": "48,123,456",
                            "country": "United States",
                            "sector": "",
                            "industry": "",
                            "url": "/market-activity/funds-and-etfs/spy",
                        },
                    ],
                },
            },
            "message": None,
            "status": {"rCode": 200, "bCodeMessage": None},
        }
        mock_response = MagicMock()
        mock_response.json.return_value = raw_response
        mock_nasdaq_session.get_with_retry.return_value = mock_response

        result = nasdaq_client.get_etf_screener()

        assert len(result) == 1
        assert isinstance(result[0], EtfRecord)
        assert result[0].symbol == "SPY"

    def test_正常系_キャッシュヒット時にAPIを呼ばない(
        self,
        nasdaq_client: NasdaqClient,
        mock_cache: MagicMock,
        mock_nasdaq_session: MagicMock,
    ) -> None:
        """When cache has raw data, parser is re-applied and API is not called."""
        cached_raw_data: dict[str, Any] = {
            "table": {
                "rows": [
                    {
                        "symbol": "SPY",
                        "name": "SPDR S&P 500 ETF Trust",
                        "lastsale": "$590.50",
                        "netchange": "-2.30",
                        "pctchange": "-0.39%",
                        "volume": "48,123,456",
                        "country": "United States",
                        "sector": "",
                        "industry": "",
                        "url": "/market-activity/funds-and-etfs/spy",
                    },
                ],
            },
        }
        mock_cache.get.return_value = cached_raw_data

        result = nasdaq_client.get_etf_screener()

        assert len(result) == 1
        assert isinstance(result[0], EtfRecord)
        assert result[0].symbol == "SPY"
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
            "data": {"table": {"rows": []}},
            "message": None,
            "status": {"rCode": 200, "bCodeMessage": None},
        }
        mock_response = MagicMock()
        mock_response.json.return_value = raw_response
        mock_nasdaq_session.get_with_retry.return_value = mock_response

        options = NasdaqFetchOptions(force_refresh=True)
        nasdaq_client.get_etf_screener(options=options)

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
            "data": {"table": {"rows": []}},
            "message": None,
            "status": {"rCode": 200, "bCodeMessage": None},
        }
        mock_response = MagicMock()
        mock_response.json.return_value = raw_response
        mock_nasdaq_session.get_with_retry.return_value = mock_response

        nasdaq_client.get_etf_screener()

        mock_nasdaq_session.get_with_retry.assert_called_once()
        mock_cache.set.assert_called_once()

    def test_正常系_limitパラメータがAPIリクエストに渡される(
        self,
        nasdaq_client: NasdaqClient,
        mock_cache: MagicMock,
        mock_nasdaq_session: MagicMock,
    ) -> None:
        """limit=99999 parameter is forwarded to the API request."""
        mock_cache.get.return_value = None

        raw_response: dict[str, Any] = {
            "data": {"table": {"rows": []}},
            "message": None,
            "status": {"rCode": 200, "bCodeMessage": None},
        }
        mock_response = MagicMock()
        mock_response.json.return_value = raw_response
        mock_nasdaq_session.get_with_retry.return_value = mock_response

        nasdaq_client.get_etf_screener()

        call_kwargs = mock_nasdaq_session.get_with_retry.call_args
        assert call_kwargs[1]["params"]["limit"] == "99999"
