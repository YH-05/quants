"""Unit tests for ETF.com JSON response parser.

Verifies all 22 parser functions (18 POST + 4 GET) and the shared helpers
(``_camel_to_snake``, ``_normalize_date``, ``_extract_fund_details_data``,
``_convert_keys``).

Each parser is tested for:
- Normal case with realistic API response data
- Empty / missing data handling (returns empty list or dict)
- Null value handling (None values passed through safely)

See Also
--------
market.etfcom.parser : Implementation under test.
market.etfcom.constants : Query name definitions.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from market.etfcom.parser import (
    _camel_to_snake,
    _convert_keys,
    _extract_fund_details_data,
    _normalize_date,
    parse_charts,
    parse_compare_ticker,
    parse_countries,
    parse_delayed_quotes,
    parse_econ_dev,
    parse_fund_flows,
    parse_holdings,
    parse_intra_data,
    parse_performance,
    parse_performance_stats,
    parse_portfolio_data,
    parse_portfolio_management,
    parse_premium_chart,
    parse_rankings,
    parse_regions,
    parse_sector_breakdown,
    parse_spread_chart,
    parse_structure,
    parse_tax_exposures,
    parse_tickers,
    parse_tradability,
    parse_tradability_summary,
)

# =============================================================================
# Sample data directory
# =============================================================================

_SAMPLE_DIR = Path(__file__).resolve().parent.parent / "fixtures"


def _load_dict(filename: str) -> dict[str, Any]:
    """Load a sample JSON file expected to contain a dict."""
    path = _SAMPLE_DIR / filename
    data = json.loads(path.read_text(encoding="utf-8"))
    assert isinstance(data, dict)
    return data


def _load_list(filename: str) -> list[dict[str, Any]]:
    """Load a sample JSON file expected to contain a list."""
    path = _SAMPLE_DIR / filename
    data = json.loads(path.read_text(encoding="utf-8"))
    assert isinstance(data, list)
    return data


# =============================================================================
# Helper: _camel_to_snake
# =============================================================================


class TestCamelToSnake:
    """Tests for the _camel_to_snake helper function."""

    def test_正常系_基本的なcamelCaseを変換できる(self) -> None:
        assert _camel_to_snake("navChangePercent") == "nav_change_percent"

    def test_正常系_単一小文字語はそのまま返す(self) -> None:
        assert _camel_to_snake("aum") == "aum"

    def test_正常系_navはそのまま返す(self) -> None:
        assert _camel_to_snake("nav") == "nav"

    def test_正常系_iivはそのまま返す(self) -> None:
        assert _camel_to_snake("iiv") == "iiv"

    def test_正常系_peRatioを正しく変換する(self) -> None:
        assert _camel_to_snake("peRatio") == "pe_ratio"

    def test_正常系_pbRatioを正しく変換する(self) -> None:
        assert _camel_to_snake("pbRatio") == "pb_ratio"

    def test_正常系_rSquaredを正しく変換する(self) -> None:
        assert _camel_to_snake("rSquared") == "r_squared"

    def test_正常系_fundNameをnameに変換する(self) -> None:
        assert _camel_to_snake("fundName") == "name"

    def test_正常系_returnYTDを正しく変換する(self) -> None:
        assert _camel_to_snake("returnYTD") == "return_ytd"

    def test_正常系_return1Yを正しく変換する(self) -> None:
        assert _camel_to_snake("return1Y") == "return_1y"

    def test_正常系_return10Yを正しく変換する(self) -> None:
        assert _camel_to_snake("return10Y") == "return_10y"

    def test_正常系_return1Mを正しく変換する(self) -> None:
        assert _camel_to_snake("return1M") == "return_1m"

    def test_正常系_return3Mを正しく変換する(self) -> None:
        assert _camel_to_snake("return3M") == "return_3m"

    def test_正常系_通常のcamelCaseキーを変換する(self) -> None:
        assert _camel_to_snake("sharesOutstanding") == "shares_outstanding"

    def test_正常系_数字混在のキーを変換する(self) -> None:
        assert _camel_to_snake("medianSpread30Day") == "median_spread30_day"

    def test_正常系_holdingTickerを変換する(self) -> None:
        assert _camel_to_snake("holdingTicker") == "holding_ticker"

    def test_正常系_asOfDateを変換する(self) -> None:
        assert _camel_to_snake("asOfDate") == "as_of_date"


# =============================================================================
# Helper: _normalize_date
# =============================================================================


class TestNormalizeDate:
    """Tests for the _normalize_date helper function."""

    def test_正常系_ISO8601タイムスタンプを日付のみに変換する(self) -> None:
        assert _normalize_date("2026-03-21T00:00:00.000Z") == "2026-03-21"

    def test_正常系_日付のみ文字列はそのまま返す(self) -> None:
        assert _normalize_date("2026-03-21") == "2026-03-21"

    def test_正常系_Noneを渡すとNoneを返す(self) -> None:
        assert _normalize_date(None) is None

    def test_正常系_T付きの別形式でも日付部分を抽出する(self) -> None:
        assert _normalize_date("2026-03-21T14:30:00.000Z") == "2026-03-21"


# =============================================================================
# Helper: _convert_keys
# =============================================================================


class TestConvertKeys:
    """Tests for the _convert_keys helper function."""

    def test_正常系_複数キーを一括変換する(self) -> None:
        record = {"navDate": "2026-03-21", "nav": 580.25, "fundFlows": 100.0}
        result = _convert_keys(record)
        assert "nav_date" in result
        assert "nav" in result
        assert "fund_flows" in result

    def test_正常系_空dictは空dictを返す(self) -> None:
        assert _convert_keys({}) == {}


# =============================================================================
# Helper: _extract_fund_details_data
# =============================================================================


class TestExtractFundDetailsData:
    """Tests for the _extract_fund_details_data helper function."""

    def test_正常系_listデータを抽出できる(self) -> None:
        response = {
            "data": {
                "fundFlowsData": {"data": [{"navDate": "2026-03-21", "nav": 580.25}]}
            }
        }
        result = _extract_fund_details_data(response, "fundFlowsData")
        assert isinstance(result, list)
        assert len(result) == 1

    def test_正常系_dictデータを抽出できる(self) -> None:
        response = {"data": {"fundPortfolioData": {"data": {"peRatio": 22.5}}}}
        result = _extract_fund_details_data(response, "fundPortfolioData")
        assert isinstance(result, dict)
        assert result["peRatio"] == 22.5

    def test_異常系_dataキーがない場合Noneを返す(self) -> None:
        assert _extract_fund_details_data({}, "fundFlowsData") is None

    def test_異常系_queryNameがない場合Noneを返す(self) -> None:
        assert _extract_fund_details_data({"data": {}}, "fundFlowsData") is None

    def test_異常系_innerDataがない場合Noneを返す(self) -> None:
        response = {"data": {"fundFlowsData": {}}}
        assert _extract_fund_details_data(response, "fundFlowsData") is None

    def test_異常系_dataがdictでない場合Noneを返す(self) -> None:
        response = {"data": "not a dict"}
        assert _extract_fund_details_data(response, "fundFlowsData") is None


# =============================================================================
# Parser: parse_fund_flows
# =============================================================================


class TestParseFundFlows:
    """Tests for parse_fund_flows."""

    def test_正常系_サンプルデータを正しくパースする(self) -> None:
        response = _load_dict("spy_fund_flows_data.json")
        result = parse_fund_flows(response)
        assert isinstance(result, list)
        assert len(result) == 3
        first = result[0]
        assert first["nav_date"] == "2026-03-21"
        assert first["nav"] == 580.25
        assert first["fund_flows"] == 2787590000.0

    def test_異常系_空レスポンスで空リストを返す(self) -> None:
        assert parse_fund_flows({}) == []

    def test_異常系_dataがNoneで空リストを返す(self) -> None:
        response: dict[str, Any] = {"data": {"fundFlowsData": {"data": None}}}
        assert parse_fund_flows(response) == []


# =============================================================================
# Parser: parse_holdings
# =============================================================================


class TestParseHoldings:
    """Tests for parse_holdings."""

    def test_正常系_サンプルデータを正しくパースする(self) -> None:
        response = _load_dict("spy_top_holdings.json")
        result = parse_holdings(response)
        assert isinstance(result, list)
        assert len(result) == 3
        first = result[0]
        assert first["holding_ticker"] == "AAPL"
        assert first["holding_name"] == "Apple Inc."
        assert first["weight"] == 0.072
        assert first["as_of_date"] == "2026-03-15"

    def test_異常系_空レスポンスで空リストを返す(self) -> None:
        assert parse_holdings({}) == []


# =============================================================================
# Parser: parse_portfolio_data
# =============================================================================


class TestParsePortfolioData:
    """Tests for parse_portfolio_data."""

    def test_正常系_サンプルデータを正しくパースする(self) -> None:
        response = _load_dict("spy_portfolio_data.json")
        result = parse_portfolio_data(response)
        assert isinstance(result, dict)
        assert result["pe_ratio"] == 22.5
        assert result["pb_ratio"] == 4.1
        assert result["dividend_yield"] == 0.0132
        assert result["number_of_holdings"] == 503
        assert result["as_of_date"] == "2026-03-15"

    def test_異常系_空レスポンスで空dictを返す(self) -> None:
        assert parse_portfolio_data({}) == {}


# =============================================================================
# Parser: parse_sector_breakdown
# =============================================================================


class TestParseSectorBreakdown:
    """Tests for parse_sector_breakdown."""

    def test_正常系_サンプルデータを正しくパースする(self) -> None:
        response = _load_dict("spy_sector_breakdown.json")
        result = parse_sector_breakdown(response)
        assert isinstance(result, list)
        assert len(result) == 3
        assert result[0]["name"] == "Technology"
        assert result[0]["weight"] == 0.32
        assert result[0]["as_of_date"] == "2026-03-15"

    def test_異常系_空レスポンスで空リストを返す(self) -> None:
        assert parse_sector_breakdown({}) == []


# =============================================================================
# Parser: parse_regions
# =============================================================================


class TestParseRegions:
    """Tests for parse_regions."""

    def test_正常系_サンプルデータを正しくパースする(self) -> None:
        response = _load_dict("spy_regions.json")
        result = parse_regions(response)
        assert isinstance(result, list)
        assert len(result) == 3
        assert result[0]["name"] == "North America"
        assert result[0]["weight"] == 0.98
        assert result[0]["as_of_date"] == "2026-03-15"

    def test_異常系_空レスポンスで空リストを返す(self) -> None:
        assert parse_regions({}) == []


# =============================================================================
# Parser: parse_countries
# =============================================================================


class TestParseCountries:
    """Tests for parse_countries."""

    def test_正常系_サンプルデータを正しくパースする(self) -> None:
        response = _load_dict("spy_countries.json")
        result = parse_countries(response)
        assert isinstance(result, list)
        assert len(result) == 3
        assert result[0]["name"] == "United States"
        assert result[0]["as_of_date"] == "2026-03-15"

    def test_異常系_空レスポンスで空リストを返す(self) -> None:
        assert parse_countries({}) == []


# =============================================================================
# Parser: parse_econ_dev
# =============================================================================


class TestParseEconDev:
    """Tests for parse_econ_dev."""

    def test_正常系_サンプルデータを正しくパースする(self) -> None:
        response = _load_dict("spy_econ_dev.json")
        result = parse_econ_dev(response)
        assert isinstance(result, list)
        assert len(result) == 2
        assert result[0]["name"] == "Developed"
        assert result[0]["weight"] == 0.99

    def test_異常系_空レスポンスで空リストを返す(self) -> None:
        assert parse_econ_dev({}) == []


# =============================================================================
# Parser: parse_intra_data
# =============================================================================


class TestParseIntraData:
    """Tests for parse_intra_data."""

    def test_正常系_サンプルデータを正しくパースする(self) -> None:
        response = _load_dict("spy_intra_data.json")
        result = parse_intra_data(response)
        assert isinstance(result, list)
        assert len(result) == 3
        assert result[0]["price"] == 580.50
        assert result[0]["date"] == "2026-03-21"

    def test_異常系_空レスポンスで空リストを返す(self) -> None:
        assert parse_intra_data({}) == []


# =============================================================================
# Parser: parse_compare_ticker
# =============================================================================


class TestParseCompareTicker:
    """Tests for parse_compare_ticker."""

    def test_正常系_サンプルデータを正しくパースする(self) -> None:
        response = _load_dict("spy_compare_ticker.json")
        result = parse_compare_ticker(response)
        assert isinstance(result, list)
        assert len(result) == 2
        assert result[0]["ticker"] == "VOO"
        assert result[0]["expense_ratio"] == 0.03

    def test_異常系_空レスポンスで空リストを返す(self) -> None:
        assert parse_compare_ticker({}) == []


# =============================================================================
# Parser: parse_spread_chart
# =============================================================================


class TestParseSpreadChart:
    """Tests for parse_spread_chart."""

    def test_正常系_サンプルデータを正しくパースする(self) -> None:
        response = _load_dict("spy_spread_chart.json")
        result = parse_spread_chart(response)
        assert isinstance(result, list)
        assert len(result) == 3
        assert result[0]["bid_ask_spread"] == 0.0001
        assert result[0]["date"] == "2026-03-21"

    def test_異常系_空レスポンスで空リストを返す(self) -> None:
        assert parse_spread_chart({}) == []


# =============================================================================
# Parser: parse_premium_chart
# =============================================================================


class TestParsePremiumChart:
    """Tests for parse_premium_chart."""

    def test_正常系_サンプルデータを正しくパースする(self) -> None:
        response = _load_dict("spy_premium_chart.json")
        result = parse_premium_chart(response)
        assert isinstance(result, list)
        assert len(result) == 3
        assert result[0]["premium_discount"] == -0.02
        assert result[0]["date"] == "2026-03-21"

    def test_異常系_空レスポンスで空リストを返す(self) -> None:
        assert parse_premium_chart({}) == []


# =============================================================================
# Parser: parse_tradability
# =============================================================================


class TestParseTradability:
    """Tests for parse_tradability."""

    def test_正常系_サンプルデータを正しくパースする(self) -> None:
        response = _load_dict("spy_tradability.json")
        result = parse_tradability(response)
        assert isinstance(result, list)
        assert len(result) == 2
        assert result[0]["volume"] == 75000000
        assert result[0]["date"] == "2026-03-21"

    def test_異常系_空レスポンスで空リストを返す(self) -> None:
        assert parse_tradability({}) == []


# =============================================================================
# Parser: parse_tradability_summary
# =============================================================================


class TestParseTradabilitySummary:
    """Tests for parse_tradability_summary."""

    def test_正常系_サンプルデータを正しくパースする(self) -> None:
        response = _load_dict("spy_tradability_summary.json")
        result = parse_tradability_summary(response)
        assert isinstance(result, dict)
        assert result["avg_daily_volume"] == 75000000.0
        assert result["median_bid_ask_spread"] == 0.0001
        assert result["creation_unit_size"] == 50000
        assert result["as_of_date"] == "2026-03-21"

    def test_異常系_空レスポンスで空dictを返す(self) -> None:
        assert parse_tradability_summary({}) == {}


# =============================================================================
# Parser: parse_portfolio_management
# =============================================================================


class TestParsePortfolioManagement:
    """Tests for parse_portfolio_management."""

    def test_正常系_サンプルデータを正しくパースする(self) -> None:
        response = _load_dict("spy_portfolio_management.json")
        result = parse_portfolio_management(response)
        assert isinstance(result, dict)
        assert result["expense_ratio"] == 0.0945
        assert result["as_of_date"] == "2026-03-15"

    def test_異常系_空レスポンスで空dictを返す(self) -> None:
        assert parse_portfolio_management({}) == {}


# =============================================================================
# Parser: parse_tax_exposures
# =============================================================================


class TestParseTaxExposures:
    """Tests for parse_tax_exposures."""

    def test_正常系_サンプルデータを正しくパースする(self) -> None:
        response = _load_dict("spy_tax_exposures.json")
        result = parse_tax_exposures(response)
        assert isinstance(result, dict)
        assert result["tax_form"] == "1099"
        assert result["tax_exempt"] is False
        assert result["as_of_date"] == "2026-03-15"

    def test_異常系_空レスポンスで空dictを返す(self) -> None:
        assert parse_tax_exposures({}) == {}


# =============================================================================
# Parser: parse_structure
# =============================================================================


class TestParseStructure:
    """Tests for parse_structure."""

    def test_正常系_サンプルデータを正しくパースする(self) -> None:
        response = _load_dict("spy_structure.json")
        result = parse_structure(response)
        assert isinstance(result, dict)
        assert result["legal_structure"] == "UIT"
        assert result["index_tracked"] == "S&P 500"
        assert result["replication_method"] == "Full Replication"
        assert result["uses_derivatives"] is False
        assert result["as_of_date"] == "2026-03-15"

    def test_異常系_空レスポンスで空dictを返す(self) -> None:
        assert parse_structure({}) == {}


# =============================================================================
# Parser: parse_rankings
# =============================================================================


class TestParseRankings:
    """Tests for parse_rankings."""

    def test_正常系_サンプルデータを正しくパースする(self) -> None:
        response = _load_dict("spy_rankings.json")
        result = parse_rankings(response)
        assert isinstance(result, dict)
        assert result["overall_rating"] == "A"
        assert result["efficiency_grade"] == "A"
        assert result["as_of_date"] == "2026-03-15"

    def test_異常系_空レスポンスで空dictを返す(self) -> None:
        assert parse_rankings({}) == {}


# =============================================================================
# Parser: parse_performance_stats
# =============================================================================


class TestParsePerformanceStats:
    """Tests for parse_performance_stats."""

    def test_正常系_サンプルデータを正しくパースする(self) -> None:
        response = _load_dict("spy_performance_stats.json")
        result = parse_performance_stats(response)
        assert isinstance(result, dict)
        assert result["return_1y"] == 0.265
        assert result["r_squared"] == 0.9998
        assert result["beta"] == 1.0
        assert result["standard_deviation"] == 0.156
        assert result["as_of_date"] == "2026-03-15"

    def test_異常系_空レスポンスで空dictを返す(self) -> None:
        assert parse_performance_stats({}) == {}


# =============================================================================
# Parser: parse_tickers (GET)
# =============================================================================


class TestParseTickers:
    """Tests for parse_tickers."""

    def test_正常系_サンプルデータを正しくパースする(self) -> None:
        response = _load_list("spy_tickers.json")
        result = parse_tickers(response)
        assert isinstance(result, list)
        assert len(result) == 3
        assert result[0]["ticker"] == "SPY"
        assert result[0]["fund_id"] == 1
        assert result[0]["name"] == "SPDR S&P 500 ETF Trust"

    def test_異常系_dictを渡すと空リストを返す(self) -> None:
        assert parse_tickers({}) == []

    def test_異常系_空リストで空リストを返す(self) -> None:
        assert parse_tickers([]) == []


# =============================================================================
# Parser: parse_delayed_quotes (GET)
# =============================================================================


class TestParseDelayedQuotes:
    """Tests for parse_delayed_quotes."""

    def test_正常系_サンプルデータを正しくパースする(self) -> None:
        response = _load_dict("spy_delayed_quotes.json")
        result = parse_delayed_quotes(response)
        assert isinstance(result, list)
        assert len(result) == 1
        first = result[0]
        assert first["ticker"] == "SPY"
        assert first["open"] == 579.50
        assert first["close"] == 580.25
        assert first["volume"] == 75000000
        assert first["last_trade_date"] == "2026-03-21"

    def test_異常系_空レスポンスで空リストを返す(self) -> None:
        assert parse_delayed_quotes({}) == []


# =============================================================================
# Parser: parse_charts (GET)
# =============================================================================


class TestParseCharts:
    """Tests for parse_charts."""

    def test_正常系_サンプルデータを正しくパースする(self) -> None:
        response = _load_dict("spy_charts.json")
        result = parse_charts(response)
        assert isinstance(result, list)
        assert len(result) == 3
        assert result[0]["split_price"] == 580.25
        assert result[0]["date"] == "2026-03-21"

    def test_異常系_空レスポンスで空リストを返す(self) -> None:
        assert parse_charts({}) == []


# =============================================================================
# Parser: parse_performance (GET)
# =============================================================================


class TestParsePerformance:
    """Tests for parse_performance."""

    def test_正常系_サンプルデータを正しくパースする(self) -> None:
        response = _load_dict("spy_performance.json")
        result = parse_performance(response)
        assert isinstance(result, dict)
        assert result["return_1y"] == 0.265
        assert result["return_ytd"] == 0.105
        assert result["as_of_date"] == "2026-03-15"

    def test_異常系_空レスポンスで空dictを返す(self) -> None:
        assert parse_performance({}) == {}


# =============================================================================
# Null value handling
# =============================================================================


class TestNullHandling:
    """Tests that null values in API responses are handled safely."""

    def test_正常系_nullフィールドを含むfundFlowsレコードをパースできる(self) -> None:
        response: dict[str, Any] = {
            "data": {
                "fundFlowsData": {
                    "data": [
                        {
                            "navDate": "2026-03-21T00:00:00.000Z",
                            "nav": None,
                            "navChange": None,
                            "navChangePercent": None,
                            "premiumDiscount": None,
                            "fundFlows": None,
                            "sharesOutstanding": None,
                            "aum": None,
                        }
                    ]
                }
            }
        }
        result = parse_fund_flows(response)
        assert len(result) == 1
        assert result[0]["nav"] is None
        assert result[0]["fund_flows"] is None
        assert result[0]["nav_date"] == "2026-03-21"

    def test_正常系_nullフィールドを含むholdingsレコードをパースできる(self) -> None:
        response: dict[str, Any] = {
            "data": {
                "topHoldings": {
                    "data": [
                        {
                            "holdingTicker": "AAPL",
                            "holdingName": None,
                            "weight": None,
                            "marketValue": None,
                            "shares": None,
                            "asOfDate": None,
                        }
                    ]
                }
            }
        }
        result = parse_holdings(response)
        assert len(result) == 1
        assert result[0]["holding_ticker"] == "AAPL"
        assert result[0]["holding_name"] is None
        assert result[0]["as_of_date"] is None


# =============================================================================
# 22 parser function count verification
# =============================================================================


class TestParserExports:
    """Verify that all 22 parser functions are exported."""

    def test_正常系_22個のパーサー関数がexportされている(self) -> None:
        from market.etfcom import parser

        exported = parser.__all__
        assert len(exported) == 22

    @pytest.mark.parametrize(
        "func_name",
        [
            "parse_fund_flows",
            "parse_holdings",
            "parse_portfolio_data",
            "parse_sector_breakdown",
            "parse_regions",
            "parse_countries",
            "parse_econ_dev",
            "parse_intra_data",
            "parse_compare_ticker",
            "parse_spread_chart",
            "parse_premium_chart",
            "parse_tradability",
            "parse_tradability_summary",
            "parse_portfolio_management",
            "parse_tax_exposures",
            "parse_structure",
            "parse_rankings",
            "parse_performance_stats",
            "parse_tickers",
            "parse_delayed_quotes",
            "parse_charts",
            "parse_performance",
        ],
    )
    def test_パラメトライズ_各パーサー関数がモジュールに存在する(
        self, func_name: str
    ) -> None:
        from market.etfcom import parser

        assert hasattr(parser, func_name), f"{func_name} not found in parser module"
        assert callable(getattr(parser, func_name))
