"""Tests for market.alphavantage.parser module.

Tests cover all 7 parse functions and 3 internal helpers:
- parse_time_series: TIME_SERIES_DAILY/WEEKLY/MONTHLY/INTRADAY
- parse_global_quote: GLOBAL_QUOTE
- parse_company_overview: OVERVIEW
- parse_financial_statements: INCOME_STATEMENT/BALANCE_SHEET/CASH_FLOW
- parse_earnings: EARNINGS
- parse_economic_indicator: REAL_GDP/CPI/etc.
- parse_forex_rate: CURRENCY_EXCHANGE_RATE

Internal helpers:
- _detect_time_series_key: whitelist-based key detection
- _normalize_ohlcv_columns: '1. open' -> 'open' normalization
- _clean_numeric: string -> float conversion with missing-data handling

See Also
--------
tests.market.nasdaq.unit.test_parser : Similar test pattern reference.
market.alphavantage.parser : Implementation under test.
"""

from __future__ import annotations

import pandas as pd
import pytest

from market.alphavantage.errors import AlphaVantageParseError
from market.alphavantage.parser import (
    _clean_numeric,
    _detect_time_series_key,
    _normalize_ohlcv_columns,
    parse_company_overview,
    parse_earnings,
    parse_economic_indicator,
    parse_financial_statements,
    parse_forex_rate,
    parse_global_quote,
    parse_time_series,
)

# =============================================================================
# Test _clean_numeric
# =============================================================================


class TestCleanNumeric:
    """Tests for _clean_numeric helper."""

    def test_正常系_有効な数値文字列で変換成功(self) -> None:
        """Valid numeric string converts to float."""
        assert _clean_numeric("228.5000") == 228.5

    def test_正常系_整数文字列で変換成功(self) -> None:
        """Integer string converts to float."""
        assert _clean_numeric("45123456") == 45123456.0

    def test_正常系_負の数値で変換成功(self) -> None:
        """Negative numeric string converts correctly."""
        assert _clean_numeric("-1.95") == -1.95

    def test_エッジケース_None文字列でNone(self) -> None:
        """'None' string returns None."""
        assert _clean_numeric("None") is None

    def test_エッジケース_ハイフンでNone(self) -> None:
        """'-' string returns None."""
        assert _clean_numeric("-") is None

    def test_エッジケース_空文字列でNone(self) -> None:
        """Empty string returns None."""
        assert _clean_numeric("") is None

    def test_エッジケース_空白文字列でNone(self) -> None:
        """Whitespace-only string returns None."""
        assert _clean_numeric("  ") is None

    def test_正常系_パーセント文字列で変換成功(self) -> None:
        """Percentage string value (without % sign) converts."""
        assert _clean_numeric("1.0965") == pytest.approx(1.0965)

    def test_エッジケース_ゼロ文字列で変換成功(self) -> None:
        """Zero string converts to 0.0."""
        assert _clean_numeric("0") == 0.0

    def test_エッジケース_不正な文字列でNone(self) -> None:
        """Non-numeric string returns None."""
        assert _clean_numeric("abc") is None


# =============================================================================
# Test _normalize_ohlcv_columns
# =============================================================================


class TestNormalizeOHLCVColumns:
    """Tests for _normalize_ohlcv_columns helper."""

    def test_正常系_番号プレフィックスを除去(self) -> None:
        """Removes number prefixes from column keys."""
        raw = {
            "1. open": "228.5000",
            "2. high": "232.1000",
            "3. low": "227.0000",
            "4. close": "230.5000",
            "5. volume": "45123456",
        }
        result = _normalize_ohlcv_columns(raw)
        assert set(result.keys()) == {"open", "high", "low", "close", "volume"}
        assert result["open"] == "228.5000"

    def test_正常系_番号プレフィックスなしはそのまま(self) -> None:
        """Keys without number prefix are kept as-is."""
        raw = {"open": "100.0", "close": "105.0"}
        result = _normalize_ohlcv_columns(raw)
        assert result == {"open": "100.0", "close": "105.0"}

    def test_エッジケース_空辞書で空辞書返却(self) -> None:
        """Empty dict returns empty dict."""
        assert _normalize_ohlcv_columns({}) == {}

    def test_正常系_2桁番号プレフィックスも除去(self) -> None:
        """Handles two-digit number prefixes (e.g., '10. change percent')."""
        raw = {"10. change percent": "1.0965%"}
        result = _normalize_ohlcv_columns(raw)
        assert "change percent" in result

    def test_正常系_混在するキーの正規化(self) -> None:
        """Handles mix of numbered and non-numbered keys."""
        raw = {
            "1. open": "100.0",
            "date": "2026-03-21",
            "5. volume": "1000000",
        }
        result = _normalize_ohlcv_columns(raw)
        assert "open" in result
        assert "date" in result
        assert "volume" in result


# =============================================================================
# Test _detect_time_series_key
# =============================================================================


class TestDetectTimeSeriesKey:
    """Tests for _detect_time_series_key helper."""

    def test_正常系_DailyのキーをDetect(self) -> None:
        """Detects 'Time Series (Daily)' key."""
        data = {
            "Meta Data": {},
            "Time Series (Daily)": {"2026-03-21": {}},
        }
        assert _detect_time_series_key(data) == "Time Series (Daily)"

    def test_正常系_WeeklyのキーをDetect(self) -> None:
        """Detects 'Weekly Time Series' key."""
        data = {
            "Meta Data": {},
            "Weekly Time Series": {"2026-03-21": {}},
        }
        assert _detect_time_series_key(data) == "Weekly Time Series"

    def test_正常系_MonthlyのキーをDetect(self) -> None:
        """Detects 'Monthly Time Series' key."""
        data = {
            "Meta Data": {},
            "Monthly Time Series": {"2026-03-21": {}},
        }
        assert _detect_time_series_key(data) == "Monthly Time Series"

    def test_正常系_IntradayのキーをDetect(self) -> None:
        """Detects 'Time Series (5min)' key."""
        data = {
            "Meta Data": {},
            "Time Series (5min)": {"2026-03-21 16:00:00": {}},
        }
        assert _detect_time_series_key(data) == "Time Series (5min)"

    def test_正常系_DailyAdjustedのキーをDetect(self) -> None:
        """Detects 'Time Series (Daily)' key for adjusted data."""
        data = {
            "Meta Data": {},
            "Time Series (Daily)": {"2026-03-21": {}},
        }
        assert _detect_time_series_key(data) == "Time Series (Daily)"

    def test_異常系_時系列キーなしでNone(self) -> None:
        """Returns None when no time series key is found."""
        data = {"Meta Data": {}, "unrelated_key": {}}
        assert _detect_time_series_key(data) is None

    def test_エッジケース_空の辞書でNone(self) -> None:
        """Returns None for empty dict."""
        assert _detect_time_series_key({}) is None


# =============================================================================
# Test parse_time_series
# =============================================================================


class TestParseTimeSeries:
    """Tests for parse_time_series function."""

    def test_正常系_DailyTimeSeriesを正しくパース(
        self,
        sample_time_series_response: dict[str, object],
    ) -> None:
        """Parses daily time series into DataFrame with correct columns."""
        df = parse_time_series(sample_time_series_response)
        assert isinstance(df, pd.DataFrame)
        assert len(df) == 5
        assert "open" in df.columns
        assert "high" in df.columns
        assert "low" in df.columns
        assert "close" in df.columns
        assert "volume" in df.columns
        assert "date" in df.columns

    def test_正常系_数値カラムがfloat型(
        self,
        sample_time_series_response: dict[str, object],
    ) -> None:
        """Numeric columns are converted to float."""
        df = parse_time_series(sample_time_series_response)
        assert df["open"].iloc[0] == pytest.approx(228.5)
        assert df["volume"].iloc[0] == pytest.approx(45123456.0)

    def test_正常系_日付カラムが含まれる(
        self,
        sample_time_series_response: dict[str, object],
    ) -> None:
        """Date column is present with correct values."""
        df = parse_time_series(sample_time_series_response)
        assert "2026-03-21" in df["date"].values

    def test_異常系_時系列キーがないレスポンスでParseError(self) -> None:
        """Raises AlphaVantageParseError when time series key is missing."""
        data: dict[str, object] = {"Meta Data": {}, "unrelated": {}}
        with pytest.raises(AlphaVantageParseError):
            parse_time_series(data)

    def test_エッジケース_空の時系列データで空DataFrame(self) -> None:
        """Returns empty DataFrame for empty time series data."""
        data: dict[str, object] = {
            "Meta Data": {},
            "Time Series (Daily)": {},
        }
        df = parse_time_series(data)
        assert isinstance(df, pd.DataFrame)
        assert len(df) == 0

    def test_正常系_WeeklyTimeSeriesをパース(self) -> None:
        """Parses weekly time series response."""
        data: dict[str, object] = {
            "Meta Data": {},
            "Weekly Time Series": {
                "2026-03-21": {
                    "1. open": "228.5000",
                    "2. high": "232.1000",
                    "3. low": "227.0000",
                    "4. close": "230.5000",
                    "5. volume": "45123456",
                },
            },
        }
        df = parse_time_series(data)
        assert len(df) == 1
        assert df["open"].iloc[0] == pytest.approx(228.5)


# =============================================================================
# Test parse_global_quote
# =============================================================================


class TestParseGlobalQuote:
    """Tests for parse_global_quote function."""

    def test_正常系_GlobalQuoteを辞書にパース(
        self,
        sample_global_quote_response: dict[str, object],
    ) -> None:
        """Parses global quote into normalized dict."""
        result = parse_global_quote(sample_global_quote_response)
        assert isinstance(result, dict)
        assert "symbol" in result
        assert result["symbol"] == "AAPL"
        assert "price" in result
        assert result["price"] == pytest.approx(230.5)

    def test_正常系_番号プレフィックスが除去される(
        self,
        sample_global_quote_response: dict[str, object],
    ) -> None:
        """Number prefixes are removed from keys."""
        result = parse_global_quote(sample_global_quote_response)
        # Should not have '01. symbol', should have 'symbol'
        assert all(not key.startswith(("0", "1")) for key in result)

    def test_異常系_GlobalQuoteキーがないレスポンスでParseError(self) -> None:
        """Raises AlphaVantageParseError when Global Quote key is missing."""
        with pytest.raises(AlphaVantageParseError):
            parse_global_quote({"unrelated": {}})


# =============================================================================
# Test parse_company_overview
# =============================================================================


class TestParseCompanyOverview:
    """Tests for parse_company_overview function."""

    def test_正常系_Overviewを辞書にパース(
        self,
        sample_overview_response: dict[str, object],
    ) -> None:
        """Parses company overview into dict with numeric conversions."""
        result = parse_company_overview(sample_overview_response)
        assert isinstance(result, dict)
        assert result["Symbol"] == "AAPL"
        assert result["Name"] == "Apple Inc"

    def test_正常系_数値フィールドが変換される(
        self,
        sample_overview_response: dict[str, object],
    ) -> None:
        """Numeric fields are converted to float."""
        result = parse_company_overview(sample_overview_response)
        assert isinstance(result["MarketCapitalization"], float)
        assert isinstance(result["PERatio"], float)

    def test_異常系_空のレスポンスでParseError(self) -> None:
        """Raises AlphaVantageParseError for empty response."""
        with pytest.raises(AlphaVantageParseError):
            parse_company_overview({})


# =============================================================================
# Test parse_financial_statements
# =============================================================================


class TestParseFinancialStatements:
    """Tests for parse_financial_statements function."""

    def test_正常系_IncomeStatementをDataFrameにパース(self) -> None:
        """Parses income statement into DataFrame."""
        data: dict[str, object] = {
            "symbol": "AAPL",
            "annualReports": [
                {
                    "fiscalDateEnding": "2025-09-30",
                    "totalRevenue": "394328000000",
                    "netIncome": "96995000000",
                    "operatingIncome": "123216000000",
                },
                {
                    "fiscalDateEnding": "2024-09-30",
                    "totalRevenue": "383285000000",
                    "netIncome": "93736000000",
                    "operatingIncome": "118658000000",
                },
            ],
            "quarterlyReports": [],
        }
        df = parse_financial_statements(data, report_type="annualReports")
        assert isinstance(df, pd.DataFrame)
        assert len(df) == 2
        assert "fiscalDateEnding" in df.columns

    def test_正常系_QuarterlyReportsをパース(self) -> None:
        """Parses quarterly reports."""
        data: dict[str, object] = {
            "symbol": "AAPL",
            "annualReports": [],
            "quarterlyReports": [
                {
                    "fiscalDateEnding": "2025-12-31",
                    "totalRevenue": "124300000000",
                    "netIncome": "36330000000",
                },
            ],
        }
        df = parse_financial_statements(data, report_type="quarterlyReports")
        assert len(df) == 1

    def test_異常系_不正なreport_typeでParseError(self) -> None:
        """Raises AlphaVantageParseError for invalid report type."""
        data: dict[str, object] = {"symbol": "AAPL"}
        with pytest.raises(AlphaVantageParseError):
            parse_financial_statements(data, report_type="invalid")

    def test_エッジケース_空のレポートで空DataFrame(self) -> None:
        """Returns empty DataFrame for empty report list."""
        data: dict[str, object] = {
            "symbol": "AAPL",
            "annualReports": [],
            "quarterlyReports": [],
        }
        df = parse_financial_statements(data, report_type="annualReports")
        assert isinstance(df, pd.DataFrame)
        assert len(df) == 0


# =============================================================================
# Test parse_earnings
# =============================================================================


class TestParseEarnings:
    """Tests for parse_earnings function."""

    def test_正常系_AnnualEarningsをDataFrameにパース(
        self,
        sample_earnings_response: dict[str, object],
    ) -> None:
        """Parses annual earnings into DataFrame."""
        annual, _quarterly = parse_earnings(sample_earnings_response)
        assert isinstance(annual, pd.DataFrame)
        assert len(annual) == 2
        assert "fiscalDateEnding" in annual.columns
        assert "reportedEPS" in annual.columns

    def test_正常系_QuarterlyEarningsをDataFrameにパース(
        self,
        sample_earnings_response: dict[str, object],
    ) -> None:
        """Parses quarterly earnings into DataFrame."""
        _annual, quarterly = parse_earnings(sample_earnings_response)
        assert isinstance(quarterly, pd.DataFrame)
        assert len(quarterly) == 2
        assert "estimatedEPS" in quarterly.columns
        assert "surprise" in quarterly.columns

    def test_異常系_earningsキーがないレスポンスでParseError(self) -> None:
        """Raises AlphaVantageParseError when earnings keys are missing."""
        with pytest.raises(AlphaVantageParseError):
            parse_earnings({"symbol": "AAPL"})


# =============================================================================
# Test parse_economic_indicator
# =============================================================================


class TestParseEconomicIndicator:
    """Tests for parse_economic_indicator function."""

    def test_正常系_GDPデータをDataFrameにパース(
        self,
        sample_economic_indicator_response: dict[str, object],
    ) -> None:
        """Parses GDP indicator into DataFrame."""
        df = parse_economic_indicator(sample_economic_indicator_response)
        assert isinstance(df, pd.DataFrame)
        assert len(df) == 4
        assert "date" in df.columns
        assert "value" in df.columns

    def test_正常系_数値カラムがfloat型(
        self,
        sample_economic_indicator_response: dict[str, object],
    ) -> None:
        """Value column is converted to float."""
        df = parse_economic_indicator(sample_economic_indicator_response)
        assert df["value"].iloc[0] == pytest.approx(23500.0)

    def test_異常系_dataキーがないレスポンスでParseError(self) -> None:
        """Raises AlphaVantageParseError when 'data' key is missing."""
        with pytest.raises(AlphaVantageParseError):
            parse_economic_indicator({"name": "GDP"})


# =============================================================================
# Test parse_forex_rate
# =============================================================================


class TestParseForexRate:
    """Tests for parse_forex_rate function."""

    def test_正常系_ForexRateを辞書にパース(self) -> None:
        """Parses forex exchange rate into normalized dict."""
        data: dict[str, object] = {
            "Realtime Currency Exchange Rate": {
                "1. From_Currency Code": "USD",
                "2. From_Currency Name": "United States Dollar",
                "3. To_Currency Code": "JPY",
                "4. To_Currency Name": "Japanese Yen",
                "5. Exchange Rate": "149.5000",
                "6. Last Refreshed": "2026-03-21 16:00:00",
                "7. Time Zone": "UTC",
                "8. Bid Price": "149.4500",
                "9. Ask Price": "149.5500",
            },
        }
        result = parse_forex_rate(data)
        assert isinstance(result, dict)
        assert "From_Currency Code" in result or "from_currency_code" in result

    def test_異常系_ForexRateキーがないレスポンスでParseError(self) -> None:
        """Raises AlphaVantageParseError when forex key is missing."""
        with pytest.raises(AlphaVantageParseError):
            parse_forex_rate({"unrelated": {}})


# =============================================================================
# Module exports
# =============================================================================

__all__: list[str] = []
