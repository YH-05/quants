"""Unit tests for the Alpha Vantage collector module.

Tests cover ``_camel_to_snake()`` conversion, ``CollectionResult`` /
``CollectionSummary`` dataclasses, ``AlphaVantageCollector`` orchestration
of Client -> Storage flow, error handling, and individual collect methods.
"""

from __future__ import annotations

from dataclasses import FrozenInstanceError
from typing import Any
from unittest.mock import MagicMock

import pandas as pd
import pytest

from market.alphavantage.collector import (
    AlphaVantageCollector,
    CollectionResult,
    CollectionSummary,
    _camel_to_snake,
)

# ============================================================================
# TestCamelToSnake
# ============================================================================


class TestCamelToSnake:
    """Tests for ``_camel_to_snake()`` helper function."""

    # --- Special key conversions ---

    def test_正常系_52WeekHighを正しく変換する(self) -> None:
        assert _camel_to_snake("52WeekHigh") == "week_52_high"

    def test_正常系_52WeekLowを正しく変換する(self) -> None:
        assert _camel_to_snake("52WeekLow") == "week_52_low"

    def test_正常系_50DayMovingAverageを正しく変換する(self) -> None:
        assert _camel_to_snake("50DayMovingAverage") == "day_50_moving_average"

    def test_正常系_200DayMovingAverageを正しく変換する(self) -> None:
        assert _camel_to_snake("200DayMovingAverage") == "day_200_moving_average"

    def test_正常系_EBITDAを正しく変換する(self) -> None:
        assert _camel_to_snake("EBITDA") == "ebitda"

    def test_正常系_PERatioを正しく変換する(self) -> None:
        assert _camel_to_snake("PERatio") == "pe_ratio"

    def test_正常系_PEGRatioを正しく変換する(self) -> None:
        assert _camel_to_snake("PEGRatio") == "peg_ratio"

    def test_正常系_EPSを正しく変換する(self) -> None:
        assert _camel_to_snake("EPS") == "eps"

    def test_正常系_DilutedEPSTTMを正しく変換する(self) -> None:
        assert _camel_to_snake("DilutedEPSTTM") == "diluted_eps_ttm"

    def test_正常系_EVToRevenueを正しく変換する(self) -> None:
        assert _camel_to_snake("EVToRevenue") == "ev_to_revenue"

    def test_正常系_EVToEBITDAを正しく変換する(self) -> None:
        assert _camel_to_snake("EVToEBITDA") == "ev_to_ebitda"

    def test_正常系_MarketCapitalizationを正しく変換する(self) -> None:
        assert _camel_to_snake("MarketCapitalization") == "market_capitalization"

    # --- Generic camelCase conversions ---

    def test_正常系_汎用camelCaseを変換する(self) -> None:
        assert _camel_to_snake("bookValue") == "book_value"

    def test_正常系_PascalCaseをsnake_caseに変換する(self) -> None:
        assert _camel_to_snake("BookValue") == "book_value"

    # --- Financial statement fields ---

    def test_正常系_fiscalDateEndingを変換する(self) -> None:
        assert _camel_to_snake("fiscalDateEnding") == "fiscal_date_ending"

    def test_正常系_reportedCurrencyを変換する(self) -> None:
        assert _camel_to_snake("reportedCurrency") == "reported_currency"

    def test_正常系_netIncomeを変換する(self) -> None:
        assert _camel_to_snake("netIncome") == "net_income"

    # --- Earnings fields ---

    def test_正常系_reportedEPSを変換する(self) -> None:
        assert _camel_to_snake("reportedEPS") == "reported_eps"

    def test_正常系_estimatedEPSを変換する(self) -> None:
        assert _camel_to_snake("estimatedEPS") == "estimated_eps"

    def test_正常系_surprisePercentageを変換する(self) -> None:
        assert _camel_to_snake("surprisePercentage") == "surprise_percentage"


# ============================================================================
# TestCollectionResult
# ============================================================================


class TestCollectionResult:
    """Tests for ``CollectionResult`` frozen dataclass."""

    def test_正常系_成功結果を作成できる(self) -> None:
        result = CollectionResult(
            symbol="AAPL",
            table="av_daily_prices",
            rows_upserted=100,
            success=True,
        )
        assert result.symbol == "AAPL"
        assert result.table == "av_daily_prices"
        assert result.rows_upserted == 100
        assert result.success is True
        assert result.error_message is None

    def test_正常系_失敗結果を作成できる(self) -> None:
        result = CollectionResult(
            symbol="AAPL",
            table="av_daily_prices",
            rows_upserted=0,
            success=False,
            error_message="API error",
        )
        assert result.success is False
        assert result.error_message == "API error"

    def test_正常系_デフォルト値が正しい(self) -> None:
        result = CollectionResult(symbol="AAPL", table="av_daily_prices")
        assert result.rows_upserted == 0
        assert result.success is True
        assert result.error_message is None

    def test_異常系_frozenで変更不可(self) -> None:
        result = CollectionResult(symbol="AAPL", table="av_daily_prices")
        with pytest.raises(FrozenInstanceError):
            result.symbol = "MSFT"


# ============================================================================
# TestCollectionSummary
# ============================================================================


class TestCollectionSummary:
    """Tests for ``CollectionSummary`` frozen dataclass."""

    def test_正常系_サマリーを作成できる(self) -> None:
        results = (
            CollectionResult("AAPL", "av_daily_prices", 100, True),
            CollectionResult("MSFT", "av_daily_prices", 80, True),
        )
        summary = CollectionSummary(
            results=results,
            total_symbols=2,
            successful=2,
            failed=0,
            total_rows=180,
        )
        assert summary.total_symbols == 2
        assert summary.successful == 2
        assert summary.failed == 0
        assert summary.total_rows == 180
        assert summary.has_failures is False

    def test_正常系_失敗ありのサマリー(self) -> None:
        results = (
            CollectionResult("AAPL", "av_daily_prices", 100, True),
            CollectionResult(
                "BAD", "av_daily_prices", 0, False, error_message="API error"
            ),
        )
        summary = CollectionSummary(
            results=results,
            total_symbols=2,
            successful=1,
            failed=1,
            total_rows=100,
        )
        assert summary.has_failures is True

    def test_正常系_デフォルト値が正しい(self) -> None:
        summary = CollectionSummary()
        assert summary.results == ()
        assert summary.total_symbols == 0
        assert summary.successful == 0
        assert summary.failed == 0
        assert summary.total_rows == 0
        assert summary.has_failures is False


# ============================================================================
# Fixtures
# ============================================================================


def _make_daily_df(rows: int = 5) -> pd.DataFrame:
    """Create a sample daily price DataFrame."""
    data = {
        "date": [f"2026-03-{17 + i}" for i in range(rows)],
        "open": [220.0 + i for i in range(rows)],
        "high": [222.0 + i for i in range(rows)],
        "low": [219.0 + i for i in range(rows)],
        "close": [221.0 + i for i in range(rows)],
        "volume": [30000000 + i * 1000000 for i in range(rows)],
    }
    return pd.DataFrame(data)


def _make_overview_dict() -> dict[str, Any]:
    """Create a sample parsed company overview dict."""
    return {
        "Symbol": "AAPL",
        "Name": "Apple Inc",
        "Description": "Apple Inc. designs...",
        "Exchange": "NASDAQ",
        "Currency": "USD",
        "Country": "USA",
        "Sector": "TECHNOLOGY",
        "Industry": "ELECTRONIC COMPUTERS",
        "FiscalYearEnd": "September",
        "LatestQuarter": "2025-12-31",
        "MarketCapitalization": 3435123456789.0,
        "EBITDA": 130541000000.0,
        "PERatio": 33.5,
        "PEGRatio": 2.1,
        "BookValue": 4.38,
        "DividendPerShare": 1.0,
        "DividendYield": 0.0043,
        "EPS": 6.88,
        "52WeekHigh": 260.1,
        "52WeekLow": 164.08,
    }


def _make_earnings_dfs() -> tuple[pd.DataFrame, pd.DataFrame]:
    """Create sample earnings DataFrames (annual, quarterly)."""
    annual = pd.DataFrame(
        [
            {"fiscalDateEnding": "2025-09-30", "reportedEPS": 6.88},
            {"fiscalDateEnding": "2024-09-30", "reportedEPS": 6.57},
        ]
    )
    quarterly = pd.DataFrame(
        [
            {
                "fiscalDateEnding": "2025-12-31",
                "reportedDate": "2026-01-30",
                "reportedEPS": 2.40,
                "estimatedEPS": 2.35,
                "surprise": 0.05,
                "surprisePercentage": 2.1277,
            },
        ]
    )
    return annual, quarterly


def _make_economic_df(rows: int = 4) -> pd.DataFrame:
    """Create a sample economic indicator DataFrame."""
    data = {
        "date": [f"2025-{1 + i * 3:02d}-01" for i in range(rows)],
        "value": [22600.0 + i * 300 for i in range(rows)],
    }
    return pd.DataFrame(data)


def _make_income_df() -> pd.DataFrame:
    """Create a sample income statement DataFrame (camelCase columns)."""
    return pd.DataFrame(
        [
            {
                "fiscalDateEnding": "2025-09-30",
                "reportedCurrency": "USD",
                "grossProfit": 170782000000.0,
                "totalRevenue": 394328000000.0,
                "netIncome": 93736000000.0,
                "ebit": 109000000000.0,
                "ebitda": 130541000000.0,
            },
        ]
    )


def _make_forex_df(rows: int = 3) -> pd.DataFrame:
    """Create a sample forex daily DataFrame."""
    data = {
        "date": [f"2026-03-{17 + i}" for i in range(rows)],
        "open": [150.0 + i for i in range(rows)],
        "high": [151.0 + i for i in range(rows)],
        "low": [149.0 + i for i in range(rows)],
        "close": [150.5 + i for i in range(rows)],
    }
    return pd.DataFrame(data)


@pytest.fixture()
def mock_client() -> MagicMock:
    """Create a mock AlphaVantageClient with default return values."""
    client = MagicMock()
    client.get_daily.return_value = _make_daily_df()
    client.get_company_overview.return_value = _make_overview_dict()
    client.get_income_statement.return_value = _make_income_df()
    client.get_balance_sheet.return_value = pd.DataFrame()
    client.get_cash_flow.return_value = pd.DataFrame()
    client.get_earnings.return_value = _make_earnings_dfs()
    client.get_real_gdp.return_value = _make_economic_df()
    client.get_cpi.return_value = _make_economic_df()
    client.get_inflation.return_value = _make_economic_df()
    client.get_unemployment.return_value = _make_economic_df()
    client.get_treasury_yield.return_value = _make_economic_df()
    client.get_federal_funds_rate.return_value = _make_economic_df()
    client.get_fx_daily.return_value = _make_forex_df()
    return client


@pytest.fixture()
def mock_storage() -> MagicMock:
    """Create a mock AlphaVantageStorage with default return values."""
    storage = MagicMock()
    storage.upsert_daily_prices.return_value = 5
    storage.upsert_company_overview.return_value = 1
    storage.upsert_income_statements.return_value = 1
    storage.upsert_balance_sheets.return_value = 0
    storage.upsert_cash_flows.return_value = 0
    storage.upsert_earnings.return_value = 3
    storage.upsert_economic_indicators.return_value = 4
    storage.upsert_forex_daily.return_value = 3
    return storage


@pytest.fixture()
def collector(mock_client: MagicMock, mock_storage: MagicMock) -> AlphaVantageCollector:
    """Create an AlphaVantageCollector with mocked client and storage."""
    return AlphaVantageCollector(client=mock_client, storage=mock_storage)


# ============================================================================
# TestCollectDaily
# ============================================================================


class TestCollectDaily:
    """Tests for ``AlphaVantageCollector.collect_daily()``."""

    def test_正常系_日次データを収集できる(
        self,
        collector: AlphaVantageCollector,
        mock_client: MagicMock,
        mock_storage: MagicMock,
    ) -> None:
        result = collector.collect_daily("AAPL")

        assert result.success is True
        assert result.symbol == "AAPL"
        assert result.table == "av_daily_prices"
        assert result.rows_upserted == 5
        mock_client.get_daily.assert_called_once_with("AAPL")
        mock_storage.upsert_daily_prices.assert_called_once()

    def test_正常系_空DataFrameで成功(
        self,
        collector: AlphaVantageCollector,
        mock_client: MagicMock,
        mock_storage: MagicMock,
    ) -> None:
        mock_client.get_daily.return_value = pd.DataFrame()

        result = collector.collect_daily("AAPL")

        assert result.success is True
        assert result.rows_upserted == 0
        mock_storage.upsert_daily_prices.assert_not_called()

    def test_異常系_APIエラーで失敗結果を返す(
        self,
        collector: AlphaVantageCollector,
        mock_client: MagicMock,
    ) -> None:
        mock_client.get_daily.side_effect = RuntimeError("API timeout")

        result = collector.collect_daily("AAPL")

        assert result.success is False
        assert result.rows_upserted == 0
        assert result.error_message == "API timeout"


# ============================================================================
# TestCollectCompanyOverview
# ============================================================================


class TestCollectCompanyOverview:
    """Tests for ``AlphaVantageCollector.collect_company_overview()``."""

    def test_正常系_PascalCaseからsnake_caseへ変換してupsertする(
        self,
        collector: AlphaVantageCollector,
        mock_client: MagicMock,
        mock_storage: MagicMock,
    ) -> None:
        result = collector.collect_company_overview("AAPL")

        assert result.success is True
        assert result.table == "av_company_overview"
        assert result.rows_upserted == 1
        mock_storage.upsert_company_overview.assert_called_once()

        # Verify the record was converted correctly
        record = mock_storage.upsert_company_overview.call_args[0][0]
        assert record.symbol == "AAPL"
        assert record.name == "Apple Inc"
        assert record.market_capitalization == 3435123456789.0
        assert record.pe_ratio == 33.5
        assert record.week_52_high == 260.1
        assert record.week_52_low == 164.08
        assert record.ebitda == 130541000000.0

    def test_正常系_空データで成功(
        self,
        collector: AlphaVantageCollector,
        mock_client: MagicMock,
        mock_storage: MagicMock,
    ) -> None:
        mock_client.get_company_overview.return_value = {}

        result = collector.collect_company_overview("AAPL")

        assert result.success is True
        assert result.rows_upserted == 0
        mock_storage.upsert_company_overview.assert_not_called()

    def test_異常系_APIエラーで失敗結果を返す(
        self,
        collector: AlphaVantageCollector,
        mock_client: MagicMock,
    ) -> None:
        mock_client.get_company_overview.side_effect = RuntimeError("API error")

        result = collector.collect_company_overview("AAPL")

        assert result.success is False
        assert result.error_message == "API error"


# ============================================================================
# TestCollectEarnings
# ============================================================================


class TestCollectEarnings:
    """Tests for ``AlphaVantageCollector.collect_earnings()``."""

    def test_正常系_annual_quarterly型分離変換(
        self,
        collector: AlphaVantageCollector,
        mock_client: MagicMock,
        mock_storage: MagicMock,
    ) -> None:
        result = collector.collect_earnings("AAPL")

        assert result.success is True
        assert result.table == "av_earnings"
        mock_storage.upsert_earnings.assert_called_once()

        # Verify type separation
        records = mock_storage.upsert_earnings.call_args[0][0]
        from market.alphavantage.models import (
            AnnualEarningsRecord,
            QuarterlyEarningsRecord,
        )

        annual_records = [r for r in records if isinstance(r, AnnualEarningsRecord)]
        quarterly_records = [
            r for r in records if isinstance(r, QuarterlyEarningsRecord)
        ]

        assert len(annual_records) == 2
        assert len(quarterly_records) == 1

        # Check annual record
        assert annual_records[0].period_type == "annual"
        assert annual_records[0].reported_eps == 6.88

        # Check quarterly record
        assert quarterly_records[0].period_type == "quarterly"
        assert quarterly_records[0].reported_eps == 2.40
        assert quarterly_records[0].estimated_eps == 2.35
        assert quarterly_records[0].surprise == 0.05
        assert quarterly_records[0].reported_date == "2026-01-30"

    def test_正常系_空earnings(
        self,
        collector: AlphaVantageCollector,
        mock_client: MagicMock,
    ) -> None:
        mock_client.get_earnings.return_value = (pd.DataFrame(), pd.DataFrame())

        result = collector.collect_earnings("AAPL")

        assert result.success is True
        assert result.rows_upserted == 0

    def test_異常系_APIエラーで失敗結果を返す(
        self,
        collector: AlphaVantageCollector,
        mock_client: MagicMock,
    ) -> None:
        mock_client.get_earnings.side_effect = RuntimeError("Parse error")

        result = collector.collect_earnings("AAPL")

        assert result.success is False
        assert "Parse error" in (result.error_message or "")


# ============================================================================
# TestCollectEconomicIndicators
# ============================================================================


class TestCollectEconomicIndicators:
    """Tests for ``AlphaVantageCollector.collect_economic_indicators()``."""

    def test_正常系_6指標一括収集(
        self,
        collector: AlphaVantageCollector,
        mock_storage: MagicMock,
    ) -> None:
        results = collector.collect_economic_indicators()

        assert len(results) == 6
        assert all(r.success for r in results)
        assert all(r.table == "av_economic_indicators" for r in results)

    def test_正常系_部分エラーでもpartial_success(
        self,
        collector: AlphaVantageCollector,
        mock_client: MagicMock,
    ) -> None:
        # CPI だけ失敗
        mock_client.get_cpi.side_effect = RuntimeError("CPI API error")

        results = collector.collect_economic_indicators()

        successful = [r for r in results if r.success]
        failed = [r for r in results if not r.success]
        assert len(successful) == 5
        assert len(failed) == 1
        assert failed[0].symbol == "CPI"

    def test_正常系_カスタム指標リスト(
        self,
        collector: AlphaVantageCollector,
        mock_storage: MagicMock,
    ) -> None:
        results = collector.collect_economic_indicators(indicators=("REAL_GDP", "CPI"))

        assert len(results) == 2
        assert results[0].symbol == "REAL_GDP"
        assert results[1].symbol == "CPI"

    def test_異常系_未サポート指標でValueError(
        self,
        collector: AlphaVantageCollector,
    ) -> None:
        results = collector.collect_economic_indicators(
            indicators=("UNSUPPORTED_INDICATOR",)
        )

        assert len(results) == 1
        assert results[0].success is False
        assert "Unsupported" in (results[0].error_message or "")


# ============================================================================
# TestCollectAll
# ============================================================================


class TestCollectAll:
    """Tests for ``AlphaVantageCollector.collect_all()``."""

    def test_正常系_複数銘柄で収集完了(
        self,
        collector: AlphaVantageCollector,
        mock_storage: MagicMock,
    ) -> None:
        summary = collector.collect_all(["AAPL", "MSFT"])

        assert summary.total_symbols == 2
        assert summary.total_rows > 0
        assert summary.has_failures is False

        # 2 symbols * (daily + 5 fundamentals) + 6 economic = 18
        assert len(summary.results) == 18

    def test_正常系_fundamentals無しで収集(
        self,
        collector: AlphaVantageCollector,
    ) -> None:
        summary = collector.collect_all(
            ["AAPL"], include_fundamentals=False, include_economic=False
        )

        # Only daily for 1 symbol
        assert len(summary.results) == 1
        assert summary.total_symbols == 1

    def test_正常系_partial_success(
        self,
        collector: AlphaVantageCollector,
        mock_client: MagicMock,
    ) -> None:
        # AAPL succeeds, MSFT daily fails
        call_count = 0

        def side_effect(symbol: str) -> pd.DataFrame:
            nonlocal call_count
            call_count += 1
            if symbol == "BAD":
                raise RuntimeError("API error")
            return _make_daily_df()

        mock_client.get_daily.side_effect = side_effect

        summary = collector.collect_all(
            ["AAPL", "BAD"], include_fundamentals=False, include_economic=False
        )

        assert summary.total_symbols == 2
        assert summary.has_failures is True
        assert summary.failed >= 1
        assert summary.successful >= 1


# ============================================================================
# TestCollectForexDaily
# ============================================================================


class TestCollectForexDaily:
    """Tests for ``AlphaVantageCollector.collect_forex_daily()``."""

    def test_正常系_通貨ペアデータを収集できる(
        self,
        collector: AlphaVantageCollector,
        mock_client: MagicMock,
        mock_storage: MagicMock,
    ) -> None:
        result = collector.collect_forex_daily("USD", "JPY")

        assert result.success is True
        assert result.symbol == "USD/JPY"
        assert result.table == "av_forex_daily"
        assert result.rows_upserted == 3
        mock_client.get_fx_daily.assert_called_once_with("USD", "JPY")

    def test_正常系_空データで成功(
        self,
        collector: AlphaVantageCollector,
        mock_client: MagicMock,
        mock_storage: MagicMock,
    ) -> None:
        mock_client.get_fx_daily.return_value = pd.DataFrame()

        result = collector.collect_forex_daily("USD", "JPY")

        assert result.success is True
        assert result.rows_upserted == 0

    def test_異常系_APIエラーで失敗結果を返す(
        self,
        collector: AlphaVantageCollector,
        mock_client: MagicMock,
    ) -> None:
        mock_client.get_fx_daily.side_effect = RuntimeError("Forex API error")

        result = collector.collect_forex_daily("USD", "JPY")

        assert result.success is False
        assert "Forex API error" in (result.error_message or "")


# ============================================================================
# TestCollectIncomeStatement
# ============================================================================


class TestCollectIncomeStatement:
    """Tests for ``AlphaVantageCollector.collect_income_statement()``."""

    def test_正常系_損益計算書を収集できる(
        self,
        collector: AlphaVantageCollector,
        mock_client: MagicMock,
        mock_storage: MagicMock,
    ) -> None:
        result = collector.collect_income_statement("AAPL")

        assert result.success is True
        assert result.table == "av_income_statements"

        # Both annual and quarterly should be fetched
        assert mock_client.get_income_statement.call_count == 2

    def test_異常系_APIエラーで失敗結果を返す(
        self,
        collector: AlphaVantageCollector,
        mock_client: MagicMock,
    ) -> None:
        mock_client.get_income_statement.side_effect = RuntimeError("Statement error")

        result = collector.collect_income_statement("AAPL")

        assert result.success is False
        assert "Statement error" in (result.error_message or "")


# ============================================================================
# TestCollectBalanceSheet
# ============================================================================


class TestCollectBalanceSheet:
    """Tests for ``AlphaVantageCollector.collect_balance_sheet()``."""

    def test_正常系_貸借対照表を収集できる(
        self,
        collector: AlphaVantageCollector,
        mock_client: MagicMock,
        mock_storage: MagicMock,
    ) -> None:
        result = collector.collect_balance_sheet("AAPL")

        assert result.success is True
        assert result.table == "av_balance_sheets"
        assert mock_client.get_balance_sheet.call_count == 2


# ============================================================================
# TestCollectCashFlow
# ============================================================================


class TestCollectCashFlow:
    """Tests for ``AlphaVantageCollector.collect_cash_flow()``."""

    def test_正常系_キャッシュフローを収集できる(
        self,
        collector: AlphaVantageCollector,
        mock_client: MagicMock,
        mock_storage: MagicMock,
    ) -> None:
        result = collector.collect_cash_flow("AAPL")

        assert result.success is True
        assert result.table == "av_cash_flows"
        assert mock_client.get_cash_flow.call_count == 2

    def test_異常系_APIエラーで失敗結果を返す(
        self,
        collector: AlphaVantageCollector,
        mock_client: MagicMock,
    ) -> None:
        mock_client.get_cash_flow.side_effect = RuntimeError("Cash flow error")

        result = collector.collect_cash_flow("AAPL")

        assert result.success is False


# ============================================================================
# TestCollectorDI
# ============================================================================


class TestCollectorDI:
    """Tests for AlphaVantageCollector dependency injection."""

    def test_正常系_明示的なDI引数で初期化できる(self) -> None:
        """Verify the collector can be created with explicit DI args."""
        mock_client = MagicMock()
        mock_storage = MagicMock()
        mock_client.get_daily.return_value = pd.DataFrame()

        collector = AlphaVantageCollector(client=mock_client, storage=mock_storage)
        collector.collect_daily("AAPL")
        mock_client.get_daily.assert_called_once()
