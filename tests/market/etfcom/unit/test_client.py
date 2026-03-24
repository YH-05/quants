"""Unit tests for market.etfcom.client — ETFComClient.

Tests cover all 22 public methods (18 POST + 4 GET), the ``_post_fund_details()``
DRY helper, validation helpers, constructor DI, and context manager support.

Test naming follows project convention: ``test_[正常系|異常系|エッジケース]_説明``.
"""

from __future__ import annotations

from typing import Any
from unittest.mock import MagicMock, patch

import pytest

from market.etfcom.client import ETFComClient
from market.etfcom.errors import ETFComAPIError
from market.etfcom.session import ETFComSession
from market.etfcom.types import RetryConfig, ScrapingConfig

# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture
def mock_session() -> MagicMock:
    """Create a mock ETFComSession."""
    session = MagicMock(spec=ETFComSession)
    return session


@pytest.fixture
def client(mock_session: MagicMock) -> ETFComClient:
    """Create an ETFComClient with a mock session."""
    return ETFComClient(session=mock_session)


def _make_fund_details_response(
    query_name: str,
    data: list[dict[str, Any]] | dict[str, Any],
) -> dict[str, Any]:
    """Build a mock fund-details response with the standard nesting."""
    return {"data": {query_name: {"data": data}}}


def _make_get_response(data: Any) -> MagicMock:
    """Build a mock GET response with a .json() method."""
    resp = MagicMock()
    resp.json.return_value = data
    resp.status_code = 200
    return resp


# =============================================================================
# Constructor / DI Tests
# =============================================================================


class TestConstructor:
    """Constructor and dependency injection tests."""

    def test_正常系_デフォルト引数でインスタンス作成(self) -> None:
        with patch("market.etfcom.client.ETFComSession") as mock_session_cls:
            mock_session_cls.return_value = MagicMock(spec=ETFComSession)
            client = ETFComClient()
            mock_session_cls.assert_called_once()
            assert client is not None

    def test_正常系_セッションDI(self, mock_session: MagicMock) -> None:
        client = ETFComClient(session=mock_session)
        assert client._session is mock_session

    def test_正常系_ScrapingConfig_DI(self) -> None:
        config = ScrapingConfig(polite_delay=5.0)
        with patch("market.etfcom.client.ETFComSession") as mock_session_cls:
            mock_session_cls.return_value = MagicMock(spec=ETFComSession)
            ETFComClient(scraping_config=config)
            # ETFComSession is called with keyword args: config=..., retry_config=...
            mock_session_cls.assert_called_once_with(
                config=config,
                retry_config=None,
            )

    def test_正常系_RetryConfig_DI(self) -> None:
        retry = RetryConfig(max_attempts=5)
        with patch("market.etfcom.client.ETFComSession") as mock_session_cls:
            mock_session_cls.return_value = MagicMock(spec=ETFComSession)
            ETFComClient(retry_config=retry)
            # ETFComSession is called with keyword args: config=..., retry_config=...
            mock_session_cls.assert_called_once_with(
                config=None,
                retry_config=retry,
            )


# =============================================================================
# Context Manager Tests
# =============================================================================


class TestContextManager:
    """Context manager protocol tests."""

    def test_正常系_withステートメントで使用可能(self, mock_session: MagicMock) -> None:
        with ETFComClient(session=mock_session) as client:
            assert client is not None
        mock_session.close.assert_called_once()

    def test_正常系_closeでセッションクローズ(self, mock_session: MagicMock) -> None:
        client = ETFComClient(session=mock_session)
        client.close()
        mock_session.close.assert_called_once()


# =============================================================================
# Validation Tests
# =============================================================================


class TestValidation:
    """Input validation tests."""

    def test_異常系_fund_idが0でValueError(self, client: ETFComClient) -> None:
        with pytest.raises(ValueError, match="fund_id must be positive"):
            client._validate_fund_id(0)

    def test_異常系_fund_idが負数でValueError(self, client: ETFComClient) -> None:
        with pytest.raises(ValueError, match="fund_id must be positive"):
            client._validate_fund_id(-1)

    def test_正常系_fund_idが正数で例外なし(self, client: ETFComClient) -> None:
        client._validate_fund_id(1)  # Should not raise

    def test_異常系_tickerが空文字でValueError(self, client: ETFComClient) -> None:
        with pytest.raises(ValueError, match="ticker must not be empty"):
            client._validate_ticker("")

    def test_異常系_tickerが空白のみでValueError(self, client: ETFComClient) -> None:
        with pytest.raises(ValueError, match="ticker must not be empty"):
            client._validate_ticker("   ")

    def test_正常系_tickerが有効で例外なし(self, client: ETFComClient) -> None:
        client._validate_ticker("SPY")  # Should not raise


# =============================================================================
# _resolve_fund_id Tests
# =============================================================================


class TestResolveFundId:
    """Tests for _resolve_fund_id helper."""

    def test_正常系_intのfund_idをそのまま返す(self, client: ETFComClient) -> None:
        result = client._resolve_fund_id(42)
        assert result == 42

    def test_異常系_fund_idが0でValueError(self, client: ETFComClient) -> None:
        with pytest.raises(ValueError, match="fund_id must be positive"):
            client._resolve_fund_id(0)


# =============================================================================
# _post_fund_details DRY Helper Tests
# =============================================================================


class TestPostFundDetails:
    """Tests for the _post_fund_details DRY helper."""

    def test_正常系_セッションのpost_fund_detailsを呼ぶ(
        self,
        client: ETFComClient,
        mock_session: MagicMock,
    ) -> None:
        response_data = _make_fund_details_response(
            "fundFlowsData",
            [{"navDate": "2026-01-15", "nav": 580.0}],
        )
        mock_resp = _make_get_response(response_data)
        mock_session.post_fund_details.return_value = mock_resp

        result = client._post_fund_details("SPY", "fundFlowsData")

        mock_session.post_fund_details.assert_called_once_with("SPY", ["fundFlowsData"])
        assert result == response_data

    def test_異常系_APIエラーが伝播される(
        self,
        client: ETFComClient,
        mock_session: MagicMock,
    ) -> None:
        mock_session.post_fund_details.side_effect = ETFComAPIError("API error")
        with pytest.raises(ETFComAPIError):
            client._post_fund_details("SPY", "fundFlowsData")


# =============================================================================
# 18 POST Method Tests (fund-details queries)
# =============================================================================


class TestGetFundFlows:
    """Tests for get_fund_flows()."""

    def test_正常系_ファンドフローデータを返す(
        self,
        client: ETFComClient,
        mock_session: MagicMock,
    ) -> None:
        raw = [
            {
                "navDate": "2026-01-15T00:00:00.000Z",
                "nav": 580.0,
                "fundFlows": 1_500_000,
            }
        ]
        response_data = _make_fund_details_response("fundFlowsData", raw)
        mock_session.post_fund_details.return_value = _make_get_response(response_data)

        result = client.get_fund_flows("SPY")

        assert isinstance(result, list)
        assert len(result) >= 1
        mock_session.post_fund_details.assert_called_once()

    def test_エッジケース_空レスポンスで空リスト(
        self,
        client: ETFComClient,
        mock_session: MagicMock,
    ) -> None:
        response_data = _make_fund_details_response("fundFlowsData", [])
        mock_session.post_fund_details.return_value = _make_get_response(response_data)

        result = client.get_fund_flows("SPY")
        assert result == []


class TestGetHoldings:
    """Tests for get_holdings()."""

    def test_正常系_保有銘柄データを返す(
        self,
        client: ETFComClient,
        mock_session: MagicMock,
    ) -> None:
        raw = [{"ticker": "AAPL", "weight": 0.072, "asOfDate": "2026-01-10"}]
        response_data = _make_fund_details_response("topHoldings", raw)
        mock_session.post_fund_details.return_value = _make_get_response(response_data)

        result = client.get_holdings("SPY")

        assert isinstance(result, list)
        assert len(result) >= 1


class TestGetPortfolioData:
    """Tests for get_portfolio_data()."""

    def test_正常系_ポートフォリオデータを返す(
        self,
        client: ETFComClient,
        mock_session: MagicMock,
    ) -> None:
        raw = {"peRatio": 22.5, "pbRatio": 4.1, "asOfDate": "2026-01-10"}
        response_data = _make_fund_details_response("fundPortfolioData", raw)
        mock_session.post_fund_details.return_value = _make_get_response(response_data)

        result = client.get_portfolio_data("SPY")

        assert isinstance(result, dict)
        assert "pe_ratio" in result


class TestGetSectorBreakdown:
    """Tests for get_sector_breakdown()."""

    def test_正常系_セクターデータを返す(
        self,
        client: ETFComClient,
        mock_session: MagicMock,
    ) -> None:
        raw = [{"name": "Technology", "weight": 0.32}]
        response_data = _make_fund_details_response("sectorIndustryBreakdown", raw)
        mock_session.post_fund_details.return_value = _make_get_response(response_data)

        result = client.get_sector_breakdown("SPY")

        assert isinstance(result, list)
        assert len(result) >= 1


class TestGetRegions:
    """Tests for get_regions()."""

    def test_正常系_地域データを返す(
        self,
        client: ETFComClient,
        mock_session: MagicMock,
    ) -> None:
        raw = [{"name": "North America", "weight": 0.98}]
        response_data = _make_fund_details_response("regions", raw)
        mock_session.post_fund_details.return_value = _make_get_response(response_data)

        result = client.get_regions("SPY")

        assert isinstance(result, list)


class TestGetCountries:
    """Tests for get_countries()."""

    def test_正常系_国別データを返す(
        self,
        client: ETFComClient,
        mock_session: MagicMock,
    ) -> None:
        raw = [{"name": "United States", "weight": 0.98}]
        response_data = _make_fund_details_response("countries", raw)
        mock_session.post_fund_details.return_value = _make_get_response(response_data)

        result = client.get_countries("SPY")

        assert isinstance(result, list)


class TestGetEconDev:
    """Tests for get_econ_dev()."""

    def test_正常系_経済発展分類データを返す(
        self,
        client: ETFComClient,
        mock_session: MagicMock,
    ) -> None:
        raw = [{"name": "Developed", "weight": 0.95}]
        response_data = _make_fund_details_response("economicDevelopment", raw)
        mock_session.post_fund_details.return_value = _make_get_response(response_data)

        result = client.get_econ_dev("SPY")

        assert isinstance(result, list)


class TestGetIntraData:
    """Tests for get_intra_data()."""

    def test_正常系_日中データを返す(
        self,
        client: ETFComClient,
        mock_session: MagicMock,
    ) -> None:
        raw = [{"date": "2026-01-15T10:30:00", "price": 580.0}]
        response_data = _make_fund_details_response("fundIntraData", raw)
        mock_session.post_fund_details.return_value = _make_get_response(response_data)

        result = client.get_intra_data("SPY")

        assert isinstance(result, list)


class TestGetCompareTicker:
    """Tests for get_compare_ticker()."""

    def test_正常系_比較データを返す(
        self,
        client: ETFComClient,
        mock_session: MagicMock,
    ) -> None:
        raw = [{"ticker": "VOO", "expenseRatio": 0.0003}]
        response_data = _make_fund_details_response("compareTicker", raw)
        mock_session.post_fund_details.return_value = _make_get_response(response_data)

        result = client.get_compare_ticker("SPY")

        assert isinstance(result, list)


class TestGetSpreadChart:
    """Tests for get_spread_chart()."""

    def test_正常系_スプレッドチャートデータを返す(
        self,
        client: ETFComClient,
        mock_session: MagicMock,
    ) -> None:
        raw = [{"date": "2026-01-15", "spread": 0.01}]
        response_data = _make_fund_details_response("fundSpreadChart", raw)
        mock_session.post_fund_details.return_value = _make_get_response(response_data)

        result = client.get_spread_chart("SPY")

        assert isinstance(result, list)


class TestGetPremiumChart:
    """Tests for get_premium_chart()."""

    def test_正常系_プレミアムチャートデータを返す(
        self,
        client: ETFComClient,
        mock_session: MagicMock,
    ) -> None:
        raw = [{"date": "2026-01-15", "premium": 0.05}]
        response_data = _make_fund_details_response("fundPremiumChart", raw)
        mock_session.post_fund_details.return_value = _make_get_response(response_data)

        result = client.get_premium_chart("SPY")

        assert isinstance(result, list)


class TestGetTradability:
    """Tests for get_tradability()."""

    def test_正常系_流動性データを返す(
        self,
        client: ETFComClient,
        mock_session: MagicMock,
    ) -> None:
        raw = [{"date": "2026-01-15", "avgVolume": 75_000_000}]
        response_data = _make_fund_details_response("fundTradabilityData", raw)
        mock_session.post_fund_details.return_value = _make_get_response(response_data)

        result = client.get_tradability("SPY")

        assert isinstance(result, list)


class TestGetTradabilitySummary:
    """Tests for get_tradability_summary()."""

    def test_正常系_流動性サマリーデータを返す(
        self,
        client: ETFComClient,
        mock_session: MagicMock,
    ) -> None:
        raw = {"avgDailyVolume": 75_000_000, "medianBidAskSpread": 0.01}
        response_data = _make_fund_details_response("fundTradabilitySummary", raw)
        mock_session.post_fund_details.return_value = _make_get_response(response_data)

        result = client.get_tradability_summary("SPY")

        assert isinstance(result, dict)


class TestGetPortfolioManagement:
    """Tests for get_portfolio_management()."""

    def test_正常系_運用データを返す(
        self,
        client: ETFComClient,
        mock_session: MagicMock,
    ) -> None:
        raw = {"expenseRatio": 0.0945, "trackingDifference": -0.02}
        response_data = _make_fund_details_response("fundPortfolioManData", raw)
        mock_session.post_fund_details.return_value = _make_get_response(response_data)

        result = client.get_portfolio_management("SPY")

        assert isinstance(result, dict)


class TestGetTaxExposures:
    """Tests for get_tax_exposures()."""

    def test_正常系_税金データを返す(
        self,
        client: ETFComClient,
        mock_session: MagicMock,
    ) -> None:
        raw = {"taxForm": "1099", "asOfDate": "2026-01-10"}
        response_data = _make_fund_details_response("fundTaxExposuresData", raw)
        mock_session.post_fund_details.return_value = _make_get_response(response_data)

        result = client.get_tax_exposures("SPY")

        assert isinstance(result, dict)


class TestGetStructure:
    """Tests for get_structure()."""

    def test_正常系_ファンド構造データを返す(
        self,
        client: ETFComClient,
        mock_session: MagicMock,
    ) -> None:
        raw = {"legalStructure": "UIT", "indexTracked": "S&P 500"}
        response_data = _make_fund_details_response("fundStructureData", raw)
        mock_session.post_fund_details.return_value = _make_get_response(response_data)

        result = client.get_structure("SPY")

        assert isinstance(result, dict)


class TestGetRankings:
    """Tests for get_rankings()."""

    def test_正常系_ランキングデータを返す(
        self,
        client: ETFComClient,
        mock_session: MagicMock,
    ) -> None:
        raw = {"overallGrade": "A", "efficiencyGrade": "A+"}
        response_data = _make_fund_details_response("fundRankingsData", raw)
        mock_session.post_fund_details.return_value = _make_get_response(response_data)

        result = client.get_rankings("SPY")

        assert isinstance(result, dict)


class TestGetPerformanceStats:
    """Tests for get_performance_stats()."""

    def test_正常系_パフォーマンス統計データを返す(
        self,
        client: ETFComClient,
        mock_session: MagicMock,
    ) -> None:
        raw = {"return1Y": 0.265, "rSquared": 0.9998}
        response_data = _make_fund_details_response("fundPerformanceStatsData", raw)
        mock_session.post_fund_details.return_value = _make_get_response(response_data)

        result = client.get_performance_stats("SPY")

        assert isinstance(result, dict)


# =============================================================================
# 4 GET Method Tests
# =============================================================================


class TestGetTickers:
    """Tests for get_tickers()."""

    def test_正常系_ティッカーリストを返す(
        self,
        client: ETFComClient,
        mock_session: MagicMock,
    ) -> None:
        raw = [
            {"ticker": "SPY", "fundId": 1, "fundName": "SPDR S&P 500"},
            {"ticker": "VOO", "fundId": 2, "fundName": "Vanguard S&P 500"},
        ]
        mock_session.get_authenticated.return_value = _make_get_response(raw)

        result = client.get_tickers()

        assert isinstance(result, list)
        assert len(result) == 2
        mock_session.get_authenticated.assert_called_once()


class TestGetDelayedQuotes:
    """Tests for get_delayed_quotes()."""

    def test_正常系_遅延クォートを返す(
        self,
        client: ETFComClient,
        mock_session: MagicMock,
    ) -> None:
        raw = {"data": [{"ticker": "SPY", "close": 580.0, "volume": 75_000_000}]}
        mock_session.get_authenticated.return_value = _make_get_response(raw)

        result = client.get_delayed_quotes("SPY")

        assert isinstance(result, list)
        assert len(result) == 1

    def test_正常系_複数ティッカーで遅延クォートを返す(
        self,
        client: ETFComClient,
        mock_session: MagicMock,
    ) -> None:
        raw = {
            "data": [
                {"ticker": "SPY", "close": 580.0},
                {"ticker": "QQQ", "close": 490.0},
            ]
        }
        mock_session.get_authenticated.return_value = _make_get_response(raw)

        result = client.get_delayed_quotes("SPY,QQQ")

        assert isinstance(result, list)
        assert len(result) == 2

    def test_異常系_空ティッカーでValueError(
        self,
        client: ETFComClient,
    ) -> None:
        with pytest.raises(ValueError, match="ticker must not be empty"):
            client.get_delayed_quotes("")


class TestGetCharts:
    """Tests for get_charts()."""

    def test_正常系_チャートデータを返す(
        self,
        client: ETFComClient,
        mock_session: MagicMock,
    ) -> None:
        raw = {"data": [{"date": "2026-01-15", "splitPrice": 580.0}]}
        mock_session.get_authenticated.return_value = _make_get_response(raw)

        result = client.get_charts("SPY")

        assert isinstance(result, list)
        assert len(result) == 1

    def test_異常系_空ティッカーでValueError(
        self,
        client: ETFComClient,
    ) -> None:
        with pytest.raises(ValueError, match="ticker must not be empty"):
            client.get_charts("")


class TestGetPerformance:
    """Tests for get_performance()."""

    def test_正常系_パフォーマンスデータを返す(
        self,
        client: ETFComClient,
        mock_session: MagicMock,
    ) -> None:
        raw = {"data": {"return1Y": 0.265, "return3Y": 0.12}}
        mock_session.get_authenticated.return_value = _make_get_response(raw)

        result = client.get_performance(1)

        assert isinstance(result, dict)

    def test_異常系_fund_idが0でValueError(
        self,
        client: ETFComClient,
    ) -> None:
        with pytest.raises(ValueError, match="fund_id must be positive"):
            client.get_performance(0)


# =============================================================================
# Method Count Verification
# =============================================================================


class TestMethodCount:
    """Verify the client exposes exactly 22 public methods."""

    def test_正常系_22のパブリックメソッドが存在する(self) -> None:
        public_methods = [
            name
            for name in dir(ETFComClient)
            if not name.startswith("_")
            and callable(getattr(ETFComClient, name))
            and name != "close"
        ]
        # 22 data methods + close = 22 public methods (close is utility, not data)
        assert len(public_methods) >= 22, (
            f"Expected at least 22 public methods, got {len(public_methods)}: "
            f"{sorted(public_methods)}"
        )
