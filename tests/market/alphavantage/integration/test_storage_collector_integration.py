"""Integration tests for Storage + Collector pipeline.

These tests use a mock ``AlphaVantageClient`` combined with a real
``AlphaVantageStorage`` backed by a temporary SQLite database. This verifies
the end-to-end pipeline: Client -> Collector -> Storage -> get methods.

Test cases
----------
- ``collect_daily`` -> ``get_daily_prices`` roundtrip
- ``collect_earnings`` -> ``get_earnings`` Annual/Quarterly distinction
- ``collect_company_overview`` -> ``get_company_overview`` CompanyOverviewRecord
- ``collect_all`` multi-symbol CollectionSummary aggregation

See Also
--------
market.alphavantage.collector : Collector under test.
market.alphavantage.storage : Storage under test.
tests.market.alphavantage.conftest : ``av_storage`` fixture.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any
from unittest.mock import MagicMock

import pandas as pd
import pytest

from market.alphavantage.collector import (
    AlphaVantageCollector,
    CollectionSummary,
)
from market.alphavantage.models import CompanyOverviewRecord

if TYPE_CHECKING:
    from market.alphavantage.storage import AlphaVantageStorage


# =============================================================================
# Helpers — mock client data builders
# =============================================================================


def _make_daily_df(symbol: str = "AAPL", rows: int = 5) -> pd.DataFrame:
    """Create a sample daily price DataFrame as returned by client.get_daily."""
    data = {
        "date": [f"2026-03-{17 + i}" for i in range(rows)],
        "open": [220.0 + i for i in range(rows)],
        "high": [222.0 + i for i in range(rows)],
        "low": [219.0 + i for i in range(rows)],
        "close": [221.0 + i for i in range(rows)],
        "volume": [30_000_000 + i * 1_000_000 for i in range(rows)],
    }
    return pd.DataFrame(data)


def _make_overview_dict(symbol: str = "AAPL") -> dict[str, Any]:
    """Create a sample parsed company overview dict (PascalCase keys)."""
    return {
        "Symbol": symbol,
        "Name": "Apple Inc",
        "Description": "Apple designs and manufactures electronics.",
        "Exchange": "NASDAQ",
        "Currency": "USD",
        "Country": "USA",
        "Sector": "TECHNOLOGY",
        "Industry": "ELECTRONIC COMPUTERS",
        "FiscalYearEnd": "September",
        "LatestQuarter": "2025-12-31",
        "MarketCapitalization": 3_435_123_456_789.0,
        "EBITDA": 130_541_000_000.0,
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


def _make_income_df() -> pd.DataFrame:
    """Create a sample income statement DataFrame (camelCase columns)."""
    return pd.DataFrame(
        [
            {
                "fiscalDateEnding": "2025-09-30",
                "reportedCurrency": "USD",
                "grossProfit": 170_782_000_000.0,
                "totalRevenue": 394_328_000_000.0,
                "netIncome": 93_736_000_000.0,
            },
        ]
    )


def _make_economic_df(rows: int = 4) -> pd.DataFrame:
    """Create a sample economic indicator DataFrame."""
    data = {
        "date": [f"2025-{1 + i * 3:02d}-01" for i in range(rows)],
        "value": [22600.0 + i * 300 for i in range(rows)],
    }
    return pd.DataFrame(data)


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


# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture()
def mock_client() -> MagicMock:
    """Create a mock AlphaVantageClient with realistic return values."""
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
def collector(
    mock_client: MagicMock,
    av_storage: AlphaVantageStorage,
) -> AlphaVantageCollector:
    """Create an AlphaVantageCollector with mock client and real storage."""
    return AlphaVantageCollector(client=mock_client, storage=av_storage)


# =============================================================================
# TestCollectDailyRoundtrip
# =============================================================================


class TestCollectDailyRoundtrip:
    """collect_daily -> get_daily_prices roundtrip with mock client + real DB."""

    def test_正常系_collect_dailyで取得したデータをget_daily_pricesで読める(
        self,
        collector: AlphaVantageCollector,
        av_storage: AlphaVantageStorage,
    ) -> None:
        """Data collected via collect_daily is retrievable via get_daily_prices."""
        result = collector.collect_daily("AAPL")

        assert result.success is True
        assert result.table == "av_daily_prices"
        assert result.rows_upserted == 5

        df = av_storage.get_daily_prices("AAPL")
        assert len(df) == 5
        assert list(df.columns)[:6] == [
            "symbol",
            "date",
            "open",
            "high",
            "low",
            "close",
        ]
        # Verify date ordering
        assert list(df["date"]) == sorted(df["date"])

    def test_正常系_date_rangeフィルタが正しく動作する(
        self,
        collector: AlphaVantageCollector,
        av_storage: AlphaVantageStorage,
    ) -> None:
        """get_daily_prices date range filter works after collect_daily."""
        collector.collect_daily("AAPL")

        df_filtered = av_storage.get_daily_prices(
            "AAPL",
            start_date="2026-03-19",
            end_date="2026-03-20",
        )
        assert len(df_filtered) == 2
        assert all("2026-03-19" <= d <= "2026-03-20" for d in df_filtered["date"])

    def test_正常系_別シンボルのデータが混在しない(
        self,
        collector: AlphaVantageCollector,
        av_storage: AlphaVantageStorage,
        mock_client: MagicMock,
    ) -> None:
        """Data for different symbols does not leak across get_daily_prices."""
        collector.collect_daily("AAPL")

        mock_client.get_daily.return_value = _make_daily_df("MSFT", rows=3)
        collector.collect_daily("MSFT")

        df_aapl = av_storage.get_daily_prices("AAPL")
        df_msft = av_storage.get_daily_prices("MSFT")
        assert len(df_aapl) == 5
        assert len(df_msft) == 3
        assert all(s == "AAPL" for s in df_aapl["symbol"])
        assert all(s == "MSFT" for s in df_msft["symbol"])


# =============================================================================
# TestCollectEarningsRoundtrip
# =============================================================================


class TestCollectEarningsRoundtrip:
    """collect_earnings -> get_earnings with Annual/Quarterly distinction."""

    def test_正常系_annualとquarterlyが区別されて保存される(
        self,
        collector: AlphaVantageCollector,
        av_storage: AlphaVantageStorage,
    ) -> None:
        """Annual and quarterly earnings are stored with distinct period_type."""
        result = collector.collect_earnings("AAPL")

        assert result.success is True
        assert result.table == "av_earnings"
        # 2 annual + 1 quarterly = 3
        assert result.rows_upserted == 3

        # Retrieve all
        df_all = av_storage.get_earnings("AAPL")
        assert len(df_all) == 3

        # Filter by period_type
        df_annual = av_storage.get_earnings("AAPL", period_type="annual")
        df_quarterly = av_storage.get_earnings("AAPL", period_type="quarterly")
        assert len(df_annual) == 2
        assert len(df_quarterly) == 1

    def test_正常系_annual_recordsにquarterly固有フィールドがNone(
        self,
        collector: AlphaVantageCollector,
        av_storage: AlphaVantageStorage,
    ) -> None:
        """Annual earnings records have quarterly-only fields set to None."""
        collector.collect_earnings("AAPL")

        df_annual = av_storage.get_earnings("AAPL", period_type="annual")
        for _, row in df_annual.iterrows():
            assert row["reported_date"] is None
            assert row["estimated_eps"] is None
            assert row["surprise"] is None
            assert row["surprise_percentage"] is None

    def test_正常系_quarterly_recordsにquarterly固有フィールドが存在する(
        self,
        collector: AlphaVantageCollector,
        av_storage: AlphaVantageStorage,
    ) -> None:
        """Quarterly earnings records have reported_date and surprise fields."""
        collector.collect_earnings("AAPL")

        df_quarterly = av_storage.get_earnings("AAPL", period_type="quarterly")
        row = df_quarterly.iloc[0]
        assert row["reported_date"] == "2026-01-30"
        assert row["reported_eps"] == pytest.approx(2.40)
        assert row["estimated_eps"] == pytest.approx(2.35)
        assert row["surprise"] == pytest.approx(0.05)
        assert row["surprise_percentage"] == pytest.approx(2.1277)


# =============================================================================
# TestCollectCompanyOverviewRoundtrip
# =============================================================================


class TestCollectCompanyOverviewRoundtrip:
    """collect_company_overview -> get_company_overview CompanyOverviewRecord."""

    def test_正常系_CompanyOverviewRecordが正しく返却される(
        self,
        collector: AlphaVantageCollector,
        av_storage: AlphaVantageStorage,
    ) -> None:
        """Collected company overview is retrievable as CompanyOverviewRecord."""
        result = collector.collect_company_overview("AAPL")

        assert result.success is True
        assert result.rows_upserted == 1

        record = av_storage.get_company_overview("AAPL")
        assert record is not None
        assert isinstance(record, CompanyOverviewRecord)
        assert record.symbol == "AAPL"
        assert record.name == "Apple Inc"
        assert record.exchange == "NASDAQ"
        assert record.sector == "TECHNOLOGY"

    def test_正常系_PascalCase変換後の数値フィールドが正しい(
        self,
        collector: AlphaVantageCollector,
        av_storage: AlphaVantageStorage,
    ) -> None:
        """PascalCase -> snake_case numeric fields survive roundtrip."""
        collector.collect_company_overview("AAPL")

        record = av_storage.get_company_overview("AAPL")
        assert record is not None
        assert record.market_capitalization == pytest.approx(3_435_123_456_789.0)
        assert record.ebitda == pytest.approx(130_541_000_000.0)
        assert record.pe_ratio == pytest.approx(33.5)
        assert record.peg_ratio == pytest.approx(2.1)
        assert record.week_52_high == pytest.approx(260.1)
        assert record.week_52_low == pytest.approx(164.08)
        assert record.eps == pytest.approx(6.88)

    def test_正常系_存在しないシンボルでNoneが返る(
        self,
        av_storage: AlphaVantageStorage,
    ) -> None:
        """get_company_overview returns None for uncollected symbol."""
        record = av_storage.get_company_overview("NONEXISTENT")
        assert record is None


# =============================================================================
# TestCollectAllSummary
# =============================================================================


class TestCollectAllSummary:
    """collect_all multi-symbol CollectionSummary aggregation."""

    def test_正常系_複数銘柄でCollectionSummaryが正しく集計される(
        self,
        collector: AlphaVantageCollector,
        mock_client: MagicMock,
    ) -> None:
        """collect_all aggregates results across multiple symbols."""
        summary = collector.collect_all(
            ["AAPL", "MSFT"],
            include_fundamentals=True,
            include_economic=True,
        )

        assert isinstance(summary, CollectionSummary)
        assert summary.total_symbols == 2
        assert summary.has_failures is False
        # Each symbol: daily + overview + income + balance + cash_flow + earnings = 6
        # Plus 6 economic indicators = 6
        # Total: 2 * 6 + 6 = 18 results
        assert len(summary.results) == 18
        assert summary.successful == 18
        assert summary.failed == 0
        assert summary.total_rows > 0

    def test_正常系_fundamentals無しでdailyのみ収集(
        self,
        collector: AlphaVantageCollector,
    ) -> None:
        """collect_all with include_fundamentals=False collects only daily."""
        summary = collector.collect_all(
            ["AAPL"],
            include_fundamentals=False,
            include_economic=False,
        )

        assert summary.total_symbols == 1
        # 1 symbol * daily only = 1
        assert len(summary.results) == 1
        assert summary.results[0].table == "av_daily_prices"
        assert summary.results[0].success is True

    def test_正常系_部分的APIエラーでも他は成功する(
        self,
        collector: AlphaVantageCollector,
        mock_client: MagicMock,
    ) -> None:
        """Partial API failures do not affect other collections."""
        # Make company overview fail for any symbol
        mock_client.get_company_overview.side_effect = RuntimeError("API error")

        summary = collector.collect_all(
            ["AAPL"],
            include_fundamentals=True,
            include_economic=False,
        )

        assert summary.has_failures is True
        # 1 daily (success) + 1 overview (fail) + 1 income (success)
        # + 1 balance (success) + 1 cash_flow (success) + 1 earnings (success) = 6
        assert len(summary.results) == 6

        failed = [r for r in summary.results if not r.success]
        assert len(failed) == 1
        assert failed[0].table == "av_company_overview"
        assert failed[0].error_message == "API error"

        succeeded = [r for r in summary.results if r.success]
        assert len(succeeded) == 5

    def test_正常系_collect_allのtotal_rowsが正しく集計される(
        self,
        collector: AlphaVantageCollector,
    ) -> None:
        """total_rows in CollectionSummary sums across all results."""
        summary = collector.collect_all(
            ["AAPL"],
            include_fundamentals=False,
            include_economic=False,
        )

        # Daily: 5 rows
        assert summary.total_rows == 5
        assert summary.total_rows == sum(r.rows_upserted for r in summary.results)
