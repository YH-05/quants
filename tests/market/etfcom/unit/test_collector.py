"""Unit tests for the ETF.com collector orchestration layer.

Tests cover:
- ``ETFComCollector`` constructor (DI and default creation)
- ``collect_tickers()`` — ticker master list collection
- ``collect_daily()`` — 3 queries per ticker
- ``collect_weekly()`` — 6 queries per ticker
- ``collect_monthly()`` — 11 queries per ticker
- ``collect_all()`` — full pipeline (tickers + daily + weekly + monthly)
- ``CollectionSummary`` reporting (success/failure/row counts)
- Error handling (client exceptions accumulated, not raised)
- dict -> Record converter functions

See Also
--------
market.etfcom.collector : Implementation under test.
market.etfcom.models : CollectionResult / CollectionSummary dataclasses.
"""

from __future__ import annotations

from typing import Any
from unittest.mock import MagicMock, PropertyMock, patch

import pandas as pd
import pytest

from market.etfcom.collector import (
    ETFComCollector,
    _build_summary,
    _to_allocation_records,
    _to_fund_flows_records,
    _to_holding_records,
    _to_performance_records,
    _to_portfolio_records,
    _to_quote_records,
    _to_structure_records,
    _to_ticker_records,
    _to_tradability_records,
)
from market.etfcom.models import (
    AllocationRecord,
    CollectionResult,
    CollectionSummary,
    FundFlowsRecord,
    HoldingRecord,
    PerformanceRecord,
    PortfolioRecord,
    QuoteRecord,
    StructureRecord,
    TickerRecord,
    TradabilityRecord,
)
from market.etfcom.storage_constants import (
    TABLE_ALLOCATIONS,
    TABLE_FUND_FLOWS,
    TABLE_HOLDINGS,
    TABLE_PERFORMANCE,
    TABLE_PORTFOLIO,
    TABLE_QUOTES,
    TABLE_STRUCTURE,
    TABLE_TICKERS,
    TABLE_TRADABILITY,
)

# =============================================================================
# Constants
# =============================================================================

FETCHED_AT = "2026-03-24T12:00:00+00:00"


# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture
def mock_client() -> MagicMock:
    """Create a mock ETFComClient with all methods returning empty data."""
    client = MagicMock()
    # GET methods
    client.get_tickers.return_value = [
        {
            "ticker": "SPY",
            "fund_id": 1,
            "name": "SPDR S&P 500 ETF Trust",
            "issuer": "State Street",
            "asset_class": "Equity",
            "inception_date": "1993-01-22",
            "segment": "Equity: U.S. - Large Cap",
        }
    ]
    client.get_delayed_quotes.return_value = [
        {
            "ticker": "SPY",
            "last_trade_date": "2026-03-24",
            "open": 580.0,
            "high": 582.0,
            "low": 578.0,
            "close": 581.0,
            "volume": 75000000.0,
            "bid": 580.95,
            "ask": 581.05,
            "bid_size": 100.0,
            "ask_size": 200.0,
        }
    ]
    client.get_performance.return_value = {
        "return_1m": 0.02,
        "return_3m": 0.05,
        "return_ytd": 0.08,
        "return_1y": 0.265,
        "return_3y": 0.10,
        "return_5y": 0.12,
        "as_of_date": "2026-03-24",
    }

    # POST fund-details methods
    client.get_fund_flows.return_value = [
        {
            "nav_date": "2026-03-24",
            "nav": 580.25,
            "nav_change": 2.15,
            "nav_change_percent": 0.48,
            "premium_discount": -0.02,
            "fund_flows": 2787590000.0,
            "shares_outstanding": 920000000.0,
            "aum": 414230000000.0,
        }
    ]
    client.get_intra_data.return_value = [
        {"date": "2026-03-24", "price": 581.0, "volume": 1000000}
    ]
    client.get_holdings.return_value = [
        {
            "ticker": "AAPL",
            "name": "Apple Inc.",
            "weight": 0.072,
            "market_value": 29800000000.0,
            "shares": 130000000.0,
            "as_of_date": "2026-03-20",
        }
    ]
    client.get_portfolio_data.return_value = {
        "pe_ratio": 22.5,
        "pb_ratio": 4.1,
        "dividend_yield": 0.013,
        "number_of_holdings": 503,
        "as_of_date": "2026-03-20",
    }
    client.get_sector_breakdown.return_value = [
        {
            "name": "Technology",
            "weight": 0.32,
            "as_of_date": "2026-03-20",
        }
    ]
    client.get_spread_chart.return_value = [{"date": "2026-03-24", "spread": 0.01}]
    client.get_premium_chart.return_value = [{"date": "2026-03-24", "premium": -0.02}]
    client.get_tradability.return_value = [{"volume": 75000000, "date": "2026-03-24"}]
    client.get_regions.return_value = [
        {"name": "North America", "weight": 0.99, "as_of_date": "2026-03-20"}
    ]
    client.get_countries.return_value = [
        {"name": "United States", "weight": 0.99, "as_of_date": "2026-03-20"}
    ]
    client.get_econ_dev.return_value = [
        {"name": "Developed", "weight": 1.0, "as_of_date": "2026-03-20"}
    ]
    client.get_compare_ticker.return_value = [{"ticker": "VOO", "expense_ratio": 0.03}]
    client.get_tradability_summary.return_value = {
        "avg_daily_volume": 75000000.0,
        "median_bid_ask_spread": 0.0001,
        "as_of_date": "2026-03-20",
    }
    client.get_portfolio_management.return_value = {
        "expense_ratio": 0.0945,
        "tracking_difference": -0.01,
    }
    client.get_tax_exposures.return_value = {"tax_form": "1099"}
    client.get_structure.return_value = {
        "legal_structure": "UIT",
        "index_tracked": "S&P 500",
        "as_of_date": "2026-03-20",
    }
    client.get_rankings.return_value = {"overall_grade": "A"}
    client.get_performance_stats.return_value = {
        "return_1y": 0.265,
        "r_squared": 0.9998,
        "beta": 1.0,
        "as_of_date": "2026-03-20",
    }

    return client


@pytest.fixture
def mock_storage() -> MagicMock:
    """Create a mock ETFComStorage with all upsert methods returning 1."""
    storage = MagicMock()
    storage.upsert_tickers.return_value = 1
    storage.upsert_fund_flows.return_value = 1
    storage.upsert_quotes.return_value = 1
    storage.upsert_holdings.return_value = 1
    storage.upsert_portfolio.return_value = 1
    storage.upsert_allocations.return_value = 1
    storage.upsert_tradability.return_value = 1
    storage.upsert_structure.return_value = 1
    storage.upsert_performance.return_value = 1
    # get_tickers returns a DataFrame with fund_id for performance GET
    storage.get_tickers.return_value = pd.DataFrame([{"ticker": "SPY", "fund_id": 1}])
    return storage


@pytest.fixture
def collector(mock_client: MagicMock, mock_storage: MagicMock) -> ETFComCollector:
    """Create an ETFComCollector with mock client and storage."""
    return ETFComCollector(client=mock_client, storage=mock_storage)


# =============================================================================
# Tests: Constructor
# =============================================================================


class TestETFComCollectorInit:
    """Tests for ETFComCollector constructor."""

    def test_正常系_DIでクライアントとストレージを注入できる(
        self,
        mock_client: MagicMock,
        mock_storage: MagicMock,
    ) -> None:
        c = ETFComCollector(client=mock_client, storage=mock_storage)
        assert c._client is mock_client
        assert c._storage is mock_storage

    def test_正常系_クライアントなしでデフォルト生成される(
        self,
        mock_storage: MagicMock,
    ) -> None:
        with patch("market.etfcom.client.ETFComClient") as mock_cls:
            mock_cls.return_value = MagicMock()
            c = ETFComCollector(client=None, storage=mock_storage)
            mock_cls.assert_called_once()
            assert c._storage is mock_storage

    def test_正常系_ストレージなしでデフォルト生成される(
        self,
        mock_client: MagicMock,
    ) -> None:
        with patch("market.etfcom.storage.get_etfcom_storage") as mock_factory:
            mock_factory.return_value = MagicMock()
            c = ETFComCollector(client=mock_client, storage=None)
            mock_factory.assert_called_once()
            assert c._client is mock_client


# =============================================================================
# Tests: collect_tickers
# =============================================================================


class TestCollectTickers:
    """Tests for collect_tickers()."""

    def test_正常系_ティッカーリストを取得し永続化できる(
        self,
        collector: ETFComCollector,
        mock_client: MagicMock,
        mock_storage: MagicMock,
    ) -> None:
        summary = collector.collect_tickers()

        mock_client.get_tickers.assert_called_once()
        mock_storage.upsert_tickers.assert_called_once()
        assert summary.successful == 1
        assert summary.failed == 0
        assert not summary.has_failures
        assert summary.total_rows == 1

    def test_異常系_クライアント例外でエラー結果を返す(
        self,
        collector: ETFComCollector,
        mock_client: MagicMock,
    ) -> None:
        mock_client.get_tickers.side_effect = RuntimeError("API down")
        summary = collector.collect_tickers()

        assert summary.failed == 1
        assert summary.successful == 0
        assert summary.has_failures
        result = summary.results[0]
        assert not result.success
        assert "API down" in (result.error_message or "")


# =============================================================================
# Tests: collect_daily
# =============================================================================


class TestCollectDaily:
    """Tests for collect_daily()."""

    def test_正常系_3クエリを実行し結果を永続化する(
        self,
        collector: ETFComCollector,
        mock_client: MagicMock,
        mock_storage: MagicMock,
    ) -> None:
        summary = collector.collect_daily(["SPY"])

        # 3 queries per ticker
        assert len(summary.results) == 3
        assert summary.successful == 3
        assert summary.failed == 0
        mock_client.get_fund_flows.assert_called_once_with("SPY")
        mock_client.get_delayed_quotes.assert_called_once_with("SPY")
        mock_client.get_intra_data.assert_called_once_with("SPY")

    def test_正常系_複数ティッカーで各3クエリ実行(
        self,
        collector: ETFComCollector,
    ) -> None:
        summary = collector.collect_daily(["SPY", "QQQ"])
        assert len(summary.results) == 6  # 3 * 2

    def test_異常系_一部クエリ失敗でもエラー累積する(
        self,
        collector: ETFComCollector,
        mock_client: MagicMock,
    ) -> None:
        mock_client.get_fund_flows.side_effect = RuntimeError("timeout")
        summary = collector.collect_daily(["SPY"])

        # fund_flows fails, quotes + intra succeed
        assert summary.failed == 1
        assert summary.successful == 2
        assert summary.has_failures


# =============================================================================
# Tests: collect_weekly
# =============================================================================


class TestCollectWeekly:
    """Tests for collect_weekly()."""

    def test_正常系_6クエリを実行し結果を永続化する(
        self,
        collector: ETFComCollector,
        mock_client: MagicMock,
    ) -> None:
        summary = collector.collect_weekly(["SPY"])

        # 6 queries per ticker
        assert len(summary.results) == 6
        assert summary.successful == 6
        assert summary.failed == 0
        mock_client.get_holdings.assert_called_once_with("SPY")
        mock_client.get_portfolio_data.assert_called_once_with("SPY")
        mock_client.get_sector_breakdown.assert_called_once_with("SPY")
        mock_client.get_spread_chart.assert_called_once_with("SPY")
        mock_client.get_premium_chart.assert_called_once_with("SPY")
        mock_client.get_tradability.assert_called_once_with("SPY")

    def test_異常系_一部クエリ失敗でもエラー累積する(
        self,
        collector: ETFComCollector,
        mock_client: MagicMock,
    ) -> None:
        mock_client.get_holdings.side_effect = RuntimeError("blocked")
        summary = collector.collect_weekly(["SPY"])

        assert summary.failed == 1
        assert summary.successful == 5


# =============================================================================
# Tests: collect_monthly
# =============================================================================


class TestCollectMonthly:
    """Tests for collect_monthly()."""

    def test_正常系_11クエリを実行し結果を永続化する(
        self,
        collector: ETFComCollector,
        mock_client: MagicMock,
    ) -> None:
        summary = collector.collect_monthly(["SPY"])

        # 11 queries per ticker
        assert len(summary.results) == 11
        assert summary.successful == 11
        assert summary.failed == 0

    def test_正常系_地域アロケーションが正しいテーブルに保存される(
        self,
        collector: ETFComCollector,
        mock_storage: MagicMock,
    ) -> None:
        collector.collect_monthly(["SPY"])

        # upsert_allocations should be called for regions, countries, econ_dev
        assert mock_storage.upsert_allocations.call_count == 3

    def test_異常系_fund_id未解決でperformance_GETスキップ(
        self,
        collector: ETFComCollector,
        mock_storage: MagicMock,
    ) -> None:
        mock_storage.get_tickers.return_value = pd.DataFrame()
        summary = collector.collect_monthly(["UNKNOWN"])

        # Should still be 11 results, all successful (perf GET skipped with 0 rows)
        assert summary.successful == 11


# =============================================================================
# Tests: collect_all
# =============================================================================


class TestCollectAll:
    """Tests for collect_all()."""

    def test_正常系_tickers_daily_weekly_monthlyの順で全実行する(
        self,
        collector: ETFComCollector,
        mock_client: MagicMock,
    ) -> None:
        summary = collector.collect_all(["SPY"])

        # 1 (tickers) + 3 (daily) + 6 (weekly) + 11 (monthly) = 21
        assert len(summary.results) == 21
        assert summary.failed == 0
        assert not summary.has_failures

    def test_正常系_成功失敗スキップの統計を報告する(
        self,
        collector: ETFComCollector,
        mock_client: MagicMock,
    ) -> None:
        mock_client.get_fund_flows.side_effect = RuntimeError("error")
        summary = collector.collect_all(["SPY"])

        assert summary.has_failures
        assert summary.failed == 1
        assert summary.successful == 20  # 21 - 1
        assert summary.total_rows > 0

    def test_正常系_空ティッカーリストでティッカーのみ取得(
        self,
        collector: ETFComCollector,
    ) -> None:
        summary = collector.collect_all([])

        # Only tickers collection (1 result)
        assert len(summary.results) == 1
        assert summary.successful == 1


# =============================================================================
# Tests: CollectionSummary reporting
# =============================================================================


class TestCollectionSummaryReporting:
    """Tests for CollectionSummary properties and _build_summary."""

    def test_正常系_成功結果のサマリーを正しく集計する(self) -> None:
        results = [
            CollectionResult("SPY", TABLE_FUND_FLOWS, 250, True),
            CollectionResult("SPY", TABLE_QUOTES, 1, True),
        ]
        summary = _build_summary(results)

        assert summary.total_tickers == 1  # unique tickers
        assert summary.successful == 2
        assert summary.failed == 0
        assert summary.total_rows == 251
        assert not summary.has_failures

    def test_正常系_失敗結果を含むサマリー(self) -> None:
        results = [
            CollectionResult("SPY", TABLE_FUND_FLOWS, 250, True),
            CollectionResult(
                "SPY",
                TABLE_QUOTES,
                0,
                False,
                error_message="timeout",
            ),
        ]
        summary = _build_summary(results)

        assert summary.successful == 1
        assert summary.failed == 1
        assert summary.has_failures
        assert summary.total_rows == 250

    def test_正常系_空結果リストのサマリー(self) -> None:
        summary = _build_summary([])

        assert summary.total_tickers == 0
        assert summary.successful == 0
        assert summary.failed == 0
        assert summary.total_rows == 0


# =============================================================================
# Tests: dict -> Record converters
# =============================================================================


class TestToFundFlowsRecords:
    """Tests for _to_fund_flows_records."""

    def test_正常系_有効なデータでレコードに変換できる(self) -> None:
        rows = [
            {
                "nav_date": "2026-03-24",
                "nav": 580.25,
                "fund_flows": 2787590000.0,
            }
        ]
        records = _to_fund_flows_records("SPY", rows, FETCHED_AT)

        assert len(records) == 1
        assert isinstance(records[0], FundFlowsRecord)
        assert records[0].ticker == "SPY"
        assert records[0].nav_date == "2026-03-24"
        assert records[0].nav == 580.25

    def test_エッジケース_nav_date欠落でスキップ(self) -> None:
        rows = [{"nav": 580.25}]
        records = _to_fund_flows_records("SPY", rows, FETCHED_AT)
        assert records == []

    def test_エッジケース_空リストで空結果(self) -> None:
        records = _to_fund_flows_records("SPY", [], FETCHED_AT)
        assert records == []


class TestToQuoteRecords:
    """Tests for _to_quote_records."""

    def test_正常系_有効なデータでレコードに変換できる(self) -> None:
        rows = [
            {
                "ticker": "SPY",
                "last_trade_date": "2026-03-24",
                "close": 581.0,
                "volume": 75000000.0,
            }
        ]
        records = _to_quote_records(rows, FETCHED_AT)

        assert len(records) == 1
        assert isinstance(records[0], QuoteRecord)
        assert records[0].ticker == "SPY"
        assert records[0].quote_date == "2026-03-24"

    def test_エッジケース_ticker欠落でスキップ(self) -> None:
        rows = [{"last_trade_date": "2026-03-24"}]
        records = _to_quote_records(rows, FETCHED_AT)
        assert records == []


class TestToHoldingRecords:
    """Tests for _to_holding_records."""

    def test_正常系_有効なデータでレコードに変換できる(self) -> None:
        rows = [
            {
                "ticker": "AAPL",
                "name": "Apple Inc.",
                "weight": 0.072,
                "as_of_date": "2026-03-20",
            }
        ]
        records = _to_holding_records("SPY", rows, FETCHED_AT)

        assert len(records) == 1
        assert isinstance(records[0], HoldingRecord)
        assert records[0].ticker == "SPY"
        assert records[0].holding_ticker == "AAPL"


class TestToPortfolioRecords:
    """Tests for _to_portfolio_records."""

    def test_正常系_有効なデータで1レコードに変換できる(self) -> None:
        data: dict[str, Any] = {"pe_ratio": 22.5, "pb_ratio": 4.1}
        records = _to_portfolio_records("SPY", data, FETCHED_AT)

        assert len(records) == 1
        assert isinstance(records[0], PortfolioRecord)
        assert records[0].pe_ratio == 22.5

    def test_エッジケース_空辞書で空結果(self) -> None:
        records = _to_portfolio_records("SPY", {}, FETCHED_AT)
        assert records == []


class TestToAllocationRecords:
    """Tests for _to_allocation_records."""

    def test_正常系_セクターアロケーションをレコードに変換できる(
        self,
    ) -> None:
        rows = [{"name": "Technology", "weight": 0.32, "as_of_date": "2026-03-20"}]
        records = _to_allocation_records("SPY", rows, "sector", FETCHED_AT)

        assert len(records) == 1
        assert isinstance(records[0], AllocationRecord)
        assert records[0].allocation_type == "sector"
        assert records[0].name == "Technology"


class TestToTradabilityRecords:
    """Tests for _to_tradability_records."""

    def test_正常系_サマリーdictからレコードに変換できる(self) -> None:
        data: dict[str, Any] = {
            "avg_daily_volume": 75000000.0,
            "median_bid_ask_spread": 0.0001,
        }
        records = _to_tradability_records("SPY", data, FETCHED_AT)

        assert len(records) == 1
        assert isinstance(records[0], TradabilityRecord)
        assert records[0].avg_daily_volume == 75000000.0

    def test_正常系_時系列リストから最新レコードに変換できる(self) -> None:
        data = [{"volume": 75000000, "date": "2026-03-24"}]
        records = _to_tradability_records("SPY", data, FETCHED_AT)

        assert len(records) == 1

    def test_エッジケース_空辞書で空結果(self) -> None:
        records = _to_tradability_records("SPY", {}, FETCHED_AT)
        assert records == []


class TestToStructureRecords:
    """Tests for _to_structure_records."""

    def test_正常系_有効なデータで1レコードに変換できる(self) -> None:
        data: dict[str, Any] = {
            "legal_structure": "UIT",
            "index_tracked": "S&P 500",
        }
        records = _to_structure_records("SPY", data, FETCHED_AT)

        assert len(records) == 1
        assert isinstance(records[0], StructureRecord)
        assert records[0].legal_structure == "UIT"

    def test_エッジケース_空辞書で空結果(self) -> None:
        records = _to_structure_records("SPY", {}, FETCHED_AT)
        assert records == []


class TestToPerformanceRecords:
    """Tests for _to_performance_records."""

    def test_正常系_有効なデータで1レコードに変換できる(self) -> None:
        data: dict[str, Any] = {"return_1y": 0.265, "r_squared": 0.9998}
        records = _to_performance_records("SPY", data, FETCHED_AT)

        assert len(records) == 1
        assert isinstance(records[0], PerformanceRecord)
        assert records[0].return_1y == 0.265

    def test_エッジケース_空辞書で空結果(self) -> None:
        records = _to_performance_records("SPY", {}, FETCHED_AT)
        assert records == []


class TestToTickerRecords:
    """Tests for _to_ticker_records."""

    def test_正常系_有効なデータでレコードに変換できる(self) -> None:
        rows = [{"ticker": "SPY", "fund_id": 1, "name": "SPDR S&P 500 ETF Trust"}]
        records = _to_ticker_records(rows, FETCHED_AT)

        assert len(records) == 1
        assert isinstance(records[0], TickerRecord)
        assert records[0].ticker == "SPY"
        assert records[0].fund_id == 1

    def test_エッジケース_ticker欠落でスキップ(self) -> None:
        rows: list[dict[str, Any]] = [{"fund_id": 1}]
        records = _to_ticker_records(rows, FETCHED_AT)
        assert records == []

    def test_エッジケース_fund_id欠落でスキップ(self) -> None:
        rows: list[dict[str, Any]] = [{"ticker": "SPY"}]
        records = _to_ticker_records(rows, FETCHED_AT)
        assert records == []
