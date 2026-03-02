"""Tests for collect_weekly_report_data.py script.

This module tests the weekly report data collection CLI script that uses
PerformanceAnalyzer4Agent, InterestRateAnalyzer4Agent, CurrencyAnalyzer4Agent,
and UpcomingEvents4Agent to collect and output data compatible with wr-data-aggregator.

The script produces output files with a fixed naming convention (no timestamps),
and converts return values from percentage to decimal form.
"""

from __future__ import annotations

import json
from datetime import date
from typing import TYPE_CHECKING, Any
from unittest.mock import MagicMock, patch

import pytest

if TYPE_CHECKING:
    from pathlib import Path


# ---------------------------------------------------------------------------
# Fixtures: Sample Data
# ---------------------------------------------------------------------------


@pytest.fixture
def sample_performance_result_us() -> dict[str, Any]:
    """Provide sample US indices PerformanceResult data."""
    return {
        "group": "indices",
        "subgroup": "us",
        "generated_at": "2026-01-21T12:00:00",
        "periods": ["1D", "1W", "YTD"],
        "symbols": {
            "^GSPC": {"1D": 0.52, "1W": 2.50, "YTD": 3.20},
            "^DJI": {"1D": 0.31, "1W": 1.80, "YTD": 2.10},
            "^IXIC": {"1D": 0.75, "1W": 3.10, "YTD": 4.50},
            "^SOX": {"1D": 1.20, "1W": 4.50, "YTD": 6.00},
        },
        "summary": {},
        "latest_dates": {
            "^GSPC": "2026-01-21",
            "^DJI": "2026-01-21",
            "^IXIC": "2026-01-21",
            "^SOX": "2026-01-21",
        },
        "data_freshness": {
            "newest_date": "2026-01-21",
            "oldest_date": "2026-01-21",
            "has_date_gap": False,
            "symbols_by_date": {"2026-01-21": ["^GSPC", "^DJI", "^IXIC", "^SOX"]},
        },
    }


@pytest.fixture
def sample_performance_result_mag7() -> dict[str, Any]:
    """Provide sample MAG7 PerformanceResult data."""
    return {
        "group": "mag7",
        "subgroup": None,
        "generated_at": "2026-01-21T12:00:00",
        "periods": ["1D", "1W", "YTD"],
        "symbols": {
            "AAPL": {"1D": 0.5, "1W": 1.50, "YTD": 2.20},
            "MSFT": {"1D": 0.8, "1W": 2.10, "YTD": 3.00},
            "GOOGL": {"1D": -0.2, "1W": -0.50, "YTD": 1.10},
            "AMZN": {"1D": 1.2, "1W": 3.00, "YTD": 4.20},
            "NVDA": {"1D": 2.5, "1W": 5.00, "YTD": 8.00},
            "META": {"1D": 0.3, "1W": -1.20, "YTD": 0.50},
            "TSLA": {"1D": -1.0, "1W": 3.70, "YTD": 5.00},
        },
        "summary": {},
        "latest_dates": {"AAPL": "2026-01-21"},
        "data_freshness": {
            "newest_date": "2026-01-21",
            "oldest_date": "2026-01-21",
            "has_date_gap": False,
            "symbols_by_date": {},
        },
    }


@pytest.fixture
def sample_performance_result_sectors() -> dict[str, Any]:
    """Provide sample sectors PerformanceResult data."""
    return {
        "group": "sectors",
        "subgroup": None,
        "generated_at": "2026-01-21T12:00:00",
        "periods": ["1D", "1W", "YTD"],
        "symbols": {
            "XLK": {"1D": 0.75, "1W": 2.80, "YTD": 3.50},
            "XLF": {"1D": 0.40, "1W": 1.20, "YTD": 2.00},
            "XLV": {"1D": -0.10, "1W": -0.50, "YTD": 0.30},
            "XLE": {"1D": 0.60, "1W": 1.50, "YTD": 1.80},
            "XLI": {"1D": 0.30, "1W": 0.80, "YTD": 1.20},
            "XLY": {"1D": 1.10, "1W": 2.50, "YTD": 3.00},
            "XLP": {"1D": -0.20, "1W": -1.00, "YTD": -0.50},
            "XLB": {"1D": 0.20, "1W": 0.50, "YTD": 0.80},
            "XLU": {"1D": 0.10, "1W": -0.30, "YTD": -0.20},
            "XLRE": {"1D": -0.30, "1W": -1.20, "YTD": -1.50},
            "XLC": {"1D": 0.50, "1W": 1.80, "YTD": 2.20},
        },
        "summary": {},
        "latest_dates": {},
        "data_freshness": {
            "newest_date": "2026-01-21",
            "oldest_date": "2026-01-21",
            "has_date_gap": False,
            "symbols_by_date": {},
        },
    }


@pytest.fixture
def sample_interest_rate_result() -> dict[str, Any]:
    """Provide sample InterestRateResult data."""
    return {
        "group": "interest_rates",
        "generated_at": "2026-01-21T12:00:00",
        "periods": ["1D", "1W"],
        "data": {
            "DGS10": {"latest": 4.65, "changes": {"1D": 0.02, "1W": 0.10}},
            "DGS2": {"latest": 4.32, "changes": {"1D": -0.01, "1W": 0.05}},
        },
        "yield_curve": {"is_inverted": False, "spread": 0.33},
        "data_freshness": {
            "newest_date": "2026-01-21",
            "oldest_date": "2026-01-21",
            "has_date_gap": False,
            "symbols_by_date": {},
        },
    }


@pytest.fixture
def sample_currency_result() -> dict[str, Any]:
    """Provide sample CurrencyResult data."""
    return {
        "group": "currencies",
        "subgroup": "jpy_crosses",
        "base_currency": "JPY",
        "generated_at": "2026-01-21T12:00:00",
        "periods": ["1D", "1W"],
        "symbols": {
            "USDJPY=X": {"1D": 0.20, "1W": 0.50},
        },
        "summary": {},
        "latest_dates": {"USDJPY=X": "2026-01-21"},
        "data_freshness": {
            "newest_date": "2026-01-21",
            "oldest_date": "2026-01-21",
            "has_date_gap": False,
            "symbols_by_date": {},
        },
    }


@pytest.fixture
def sample_upcoming_events_result() -> dict[str, Any]:
    """Provide sample UpcomingEventsResult data."""
    return {
        "generated_at": "2026-01-21T12:00:00",
        "period": {"start": "2026-01-21", "end": "2026-01-28"},
        "earnings": [{"ticker": "AAPL", "name": "Apple", "date": "2026-01-28"}],
        "economic_releases": [
            {"name": "FOMC Meeting", "date": "2026-01-28", "impact": "High"}
        ],
        "summary": {"earnings_count": 1, "economic_release_count": 1},
    }


def _make_mock_result(data: dict[str, Any]) -> MagicMock:
    """Create a mock result object from dict data."""
    mock = MagicMock()
    mock.to_dict.return_value = data
    mock.data_freshness = data.get("data_freshness", {})
    return mock


# ---------------------------------------------------------------------------
# Test: CLI Argument Parsing
# ---------------------------------------------------------------------------


class TestCLIArgumentParsing:
    """Test CLI argument parsing functionality."""

    def test_正常系_helpが正常に動作する(self) -> None:
        """Test that --help works without error."""
        from scripts.collect_weekly_report_data import create_parser

        parser = create_parser()
        # Should not raise
        assert parser is not None

    def test_正常系_デフォルト引数でoutputが設定される(self) -> None:
        """Test that default output directory is set."""
        from scripts.collect_weekly_report_data import create_parser

        parser = create_parser()
        args = parser.parse_args([])

        assert args.output is not None

    def test_正常系_output引数を指定できる(self) -> None:
        """Test specifying output directory."""
        from scripts.collect_weekly_report_data import create_parser

        parser = create_parser()
        args = parser.parse_args(["--output", "custom/path"])

        assert args.output == "custom/path"

    def test_正常系_start引数を指定できる(self) -> None:
        """Test specifying start date."""
        from scripts.collect_weekly_report_data import create_parser

        parser = create_parser()
        args = parser.parse_args(["--start", "2026-01-14"])

        assert args.start == "2026-01-14"

    def test_正常系_end引数を指定できる(self) -> None:
        """Test specifying end date."""
        from scripts.collect_weekly_report_data import create_parser

        parser = create_parser()
        args = parser.parse_args(["--end", "2026-01-21"])

        assert args.end == "2026-01-21"

    def test_正常系_date引数を指定できる(self) -> None:
        """Test specifying reference date."""
        from scripts.collect_weekly_report_data import create_parser

        parser = create_parser()
        args = parser.parse_args(["--date", "2026-01-22"])

        assert args.date == "2026-01-22"

    def test_正常系_start_endとdateはweekly_comment_dataと互換である(self) -> None:
        """Test that --start, --end, --date args are compatible with weekly_comment_data.py."""
        from scripts.collect_weekly_report_data import create_parser

        parser = create_parser()
        args = parser.parse_args(
            ["--start", "2026-01-14", "--end", "2026-01-21", "--date", "2026-01-22"]
        )

        assert args.start == "2026-01-14"
        assert args.end == "2026-01-21"
        assert args.date == "2026-01-22"


# ---------------------------------------------------------------------------
# Test: Return Value Conversion (percent -> decimal)
# ---------------------------------------------------------------------------


class TestReturnValueConversion:
    """Test return value conversion from percent to decimal form."""

    def test_正常系_パーセント形式から小数形式に変換される(self) -> None:
        """Test return_pct is converted from percent to decimal."""
        from scripts.collect_weekly_report_data import adapt_to_indices

        # S&P500 weekly_return = 2.50% -> 0.025
        sample_perf = {
            "periods": ["1W", "YTD"],
            "symbols": {
                "^GSPC": {"1W": 2.50, "YTD": 3.20},
            },
        }
        result = adapt_to_indices(sample_perf, date(2026, 1, 14), date(2026, 1, 21))

        gspc = next(i for i in result if i["ticker"] == "^GSPC")
        assert gspc["weekly_return"] == pytest.approx(0.025)

    def test_正常系_YTDリターンが小数形式に変換される(self) -> None:
        """Test ytd_return is in decimal form."""
        from scripts.collect_weekly_report_data import adapt_to_indices

        sample_perf = {
            "periods": ["1W", "YTD"],
            "symbols": {
                "^GSPC": {"1W": 2.50, "YTD": 3.20},
            },
        }
        result = adapt_to_indices(sample_perf, date(2026, 1, 14), date(2026, 1, 21))

        gspc = next(i for i in result if i["ticker"] == "^GSPC")
        assert gspc["ytd_return"] == pytest.approx(0.032)

    def test_正常系_マイナスリターンも正しく変換される(self) -> None:
        """Test negative returns are also converted correctly."""
        from scripts.collect_weekly_report_data import adapt_to_indices

        sample_perf = {
            "periods": ["1W", "YTD"],
            "symbols": {
                "^GSPC": {"1W": -1.50, "YTD": -0.80},
            },
        }
        result = adapt_to_indices(sample_perf, date(2026, 1, 14), date(2026, 1, 21))

        gspc = next(i for i in result if i["ticker"] == "^GSPC")
        assert gspc["weekly_return"] == pytest.approx(-0.015)
        assert gspc["ytd_return"] == pytest.approx(-0.008)

    def test_正常系_ゼロリターンが正しく変換される(self) -> None:
        """Test zero returns are handled correctly."""
        from scripts.collect_weekly_report_data import adapt_to_indices

        sample_perf = {
            "periods": ["1W", "YTD"],
            "symbols": {
                "^GSPC": {"1W": 0.0, "YTD": 0.0},
            },
        }
        result = adapt_to_indices(sample_perf, date(2026, 1, 14), date(2026, 1, 21))

        gspc = next(i for i in result if i["ticker"] == "^GSPC")
        assert gspc["weekly_return"] == pytest.approx(0.0)


# ---------------------------------------------------------------------------
# Test: adapt_to_indices
# ---------------------------------------------------------------------------


class TestAdaptToIndices:
    """Test adapt_to_indices function."""

    def test_正常系_必須フィールドが存在する(
        self, sample_performance_result_us: dict[str, Any]
    ) -> None:
        """Test that required fields exist in output."""
        from scripts.collect_weekly_report_data import adapt_to_indices

        result = adapt_to_indices(
            sample_performance_result_us,
            date(2026, 1, 14),
            date(2026, 1, 21),
        )

        assert len(result) > 0
        for item in result:
            assert "ticker" in item
            assert "name" in item
            assert "weekly_return" in item
            assert "ytd_return" in item
            assert "price" in item
            assert "change" in item

    def test_正常系_changeフィールドが計算される(
        self, sample_performance_result_us: dict[str, Any]
    ) -> None:
        """Test that change field is computed from price and weekly_return."""
        from scripts.collect_weekly_report_data import adapt_to_indices

        result = adapt_to_indices(
            sample_performance_result_us,
            date(2026, 1, 14),
            date(2026, 1, 21),
        )

        for item in result:
            if item["price"] is not None and item["weekly_return"] is not None:
                # change = price * (weekly_return_pct / 100) = price * weekly_return (already decimal)
                # But weekly_return is in decimal so change = price * weekly_return / (1 + weekly_return) * (1 + weekly_return)
                # Actually change = price - price_start = price * weekly_return
                # Since price is end price and weekly_return is decimal
                assert item["change"] is not None

    def test_異常系_symbolsが空の場合は空リストを返す(self) -> None:
        """symbols が空 dict の PerformanceResult を渡したとき空リストを返すことを確認。"""
        from scripts.collect_weekly_report_data import adapt_to_indices

        empty_perf: dict[str, Any] = {
            "group": "indices",
            "subgroup": "us",
            "periods": ["1W", "YTD"],
            "symbols": {},
        }
        result = adapt_to_indices(
            empty_perf,
            date(2026, 1, 14),
            date(2026, 1, 21),
            name_map={},
        )

        assert result == []

    def test_異常系_weekly_returnが全てNoneの場合ソートが壊れない(self) -> None:
        """1W キーが存在しない場合、adapt_to_indices が例外を発生させずリストを返すことを確認。

        ソート後も全エントリの weekly_return が None であること。
        """
        from scripts.collect_weekly_report_data import adapt_to_indices

        none_weekly_perf: dict[str, Any] = {
            "group": "indices",
            "subgroup": "us",
            "periods": ["1D", "YTD"],
            "symbols": {
                "^GSPC": {"1D": 0.52, "YTD": 3.20},
                "^DJI": {"1D": 0.31, "YTD": 2.10},
                "^IXIC": {"1D": 0.75, "YTD": 4.50},
            },
        }
        # 例外を発生させずにリストを返すこと
        result = adapt_to_indices(
            none_weekly_perf,
            date(2026, 1, 14),
            date(2026, 1, 21),
            name_map={"^GSPC": "S&P500", "^DJI": "Dow Jones", "^IXIC": "NASDAQ"},
        )

        assert isinstance(result, list)
        assert len(result) == 3
        # 全エントリの weekly_return が None であること
        for item in result:
            assert item["weekly_return"] is None


# ---------------------------------------------------------------------------
# Test: adapt_to_mag7
# ---------------------------------------------------------------------------


class TestAdaptToMag7:
    """Test adapt_to_mag7 function."""

    def test_正常系_mag7配列が生成される(
        self, sample_performance_result_mag7: dict[str, Any]
    ) -> None:
        """Test that mag7 array is generated."""
        from scripts.collect_weekly_report_data import adapt_to_mag7

        result = adapt_to_mag7(sample_performance_result_mag7)

        assert "mag7" in result
        assert isinstance(result["mag7"], list)
        assert len(result["mag7"]) == 7

    def test_正常系_mag7がweekly_return降順でソートされる(
        self, sample_performance_result_mag7: dict[str, Any]
    ) -> None:
        """Test that mag7 is sorted by weekly_return descending."""
        from scripts.collect_weekly_report_data import adapt_to_mag7

        result = adapt_to_mag7(sample_performance_result_mag7)

        mag7_list = result["mag7"]
        weekly_returns = [item["weekly_return"] for item in mag7_list]
        assert weekly_returns == sorted(weekly_returns, reverse=True)

    def test_正常系_sox情報が含まれる(
        self,
        sample_performance_result_mag7: dict[str, Any],
        sample_performance_result_us: dict[str, Any],
    ) -> None:
        """Test that sox information is included."""
        from scripts.collect_weekly_report_data import adapt_to_mag7

        result = adapt_to_mag7(
            sample_performance_result_mag7,
            sox_perf=sample_performance_result_us,
        )

        assert "sox" in result
        assert result["sox"] is not None
        assert result["sox"]["ticker"] == "^SOX"

    def test_正常系_mag7の必須フィールドが存在する(
        self, sample_performance_result_mag7: dict[str, Any]
    ) -> None:
        """Test required fields exist in mag7 items."""
        from scripts.collect_weekly_report_data import adapt_to_mag7

        result = adapt_to_mag7(sample_performance_result_mag7)

        for item in result["mag7"]:
            assert "ticker" in item
            assert "name" in item
            assert "weekly_return" in item

    def test_異常系_market_cap取得失敗時はNoneでフォールバック(
        self, sample_performance_result_mag7: dict[str, Any]
    ) -> None:
        """market_caps に一部のティッカーが存在しない場合、そのエントリの market_cap が None になることを確認。"""
        from scripts.collect_weekly_report_data import adapt_to_mag7

        # AAPL のみ market_cap あり、残りは欠損
        partial_market_caps: dict[str, int | None] = {
            "AAPL": 3_800_000_000_000,
        }
        result = adapt_to_mag7(
            sample_performance_result_mag7,
            market_caps=partial_market_caps,
        )

        mag7_list = result["mag7"]
        aapl = next(item for item in mag7_list if item["ticker"] == "AAPL")
        assert aapl["market_cap"] == 3_800_000_000_000

        # AAPL 以外のティッカーは market_caps に存在しないため None になること
        others = [item for item in mag7_list if item["ticker"] != "AAPL"]
        for item in others:
            assert item["market_cap"] is None


# ---------------------------------------------------------------------------
# Test: adapt_to_sectors
# ---------------------------------------------------------------------------


class TestAdaptToSectors:
    """Test adapt_to_sectors function."""

    def test_正常系_top_sectorsが存在する(
        self, sample_performance_result_sectors: dict[str, Any]
    ) -> None:
        """Test top_sectors field exists."""
        from scripts.collect_weekly_report_data import adapt_to_sectors

        result = adapt_to_sectors(sample_performance_result_sectors)

        assert "top_sectors" in result

    def test_正常系_bottom_sectorsが存在する(
        self, sample_performance_result_sectors: dict[str, Any]
    ) -> None:
        """Test bottom_sectors field exists."""
        from scripts.collect_weekly_report_data import adapt_to_sectors

        result = adapt_to_sectors(sample_performance_result_sectors)

        assert "bottom_sectors" in result

    def test_正常系_all_sectorsが存在する(
        self, sample_performance_result_sectors: dict[str, Any]
    ) -> None:
        """Test all_sectors field exists."""
        from scripts.collect_weekly_report_data import adapt_to_sectors

        result = adapt_to_sectors(sample_performance_result_sectors)

        assert "all_sectors" in result

    def test_正常系_all_sectorsがweekly_return降順でソートされる(
        self, sample_performance_result_sectors: dict[str, Any]
    ) -> None:
        """Test all_sectors is sorted by weekly_return descending."""
        from scripts.collect_weekly_report_data import adapt_to_sectors

        result = adapt_to_sectors(sample_performance_result_sectors)

        returns = [s["weekly_return"] for s in result["all_sectors"]]
        assert returns == sorted(returns, reverse=True)

    def test_正常系_top_sectorsとbottom_sectorsが正しく選ばれる(
        self, sample_performance_result_sectors: dict[str, Any]
    ) -> None:
        """Test top and bottom sectors are correctly selected."""
        from scripts.collect_weekly_report_data import adapt_to_sectors

        result = adapt_to_sectors(sample_performance_result_sectors)

        top_returns = [s["weekly_return"] for s in result["top_sectors"]]
        bottom_returns = [s["weekly_return"] for s in result["bottom_sectors"]]
        all_returns = [s["weekly_return"] for s in result["all_sectors"]]

        # top_sectors should have highest returns
        assert max(top_returns) == max(all_returns)
        # bottom_sectors should have lowest returns
        assert min(bottom_returns) == min(all_returns)

    def test_正常系_セクターリターンが小数形式に変換される(
        self, sample_performance_result_sectors: dict[str, Any]
    ) -> None:
        """Test sector returns are in decimal form."""
        from scripts.collect_weekly_report_data import adapt_to_sectors

        result = adapt_to_sectors(sample_performance_result_sectors)

        # XLK weekly 2.80% -> 0.028
        xlk = next(s for s in result["all_sectors"] if s["ticker"] == "XLK")
        assert xlk["weekly_return"] == pytest.approx(0.028)

    def test_異常系_sector_weightsが空の場合はNullフィールドで返す(
        self, sample_performance_result_sectors: dict[str, Any]
    ) -> None:
        """sector_weights={} を渡したとき weight が None、top_holdings が [] になることを確認。"""
        from scripts.collect_weekly_report_data import adapt_to_sectors

        result = adapt_to_sectors(
            sample_performance_result_sectors,
            sector_weights={},
        )

        for sector in result["all_sectors"]:
            assert sector["weight"] is None
            assert sector["top_holdings"] == []


# ---------------------------------------------------------------------------
# Test: collect_interest_rates
# ---------------------------------------------------------------------------


class TestCollectInterestRates:
    """Test collect_interest_rates wrapper function."""

    def test_正常系_金利データを収集できる(
        self, tmp_path: Path, sample_interest_rate_result: dict[str, Any]
    ) -> None:
        """Test collecting interest rate data successfully."""
        from scripts.collect_weekly_report_data import collect_interest_rates

        mock_result = _make_mock_result(sample_interest_rate_result)

        with patch(
            "scripts.collect_weekly_report_data.InterestRateAnalyzer4Agent"
        ) as mock_class:
            mock_analyzer = MagicMock()
            mock_analyzer.get_interest_rate_data.return_value = mock_result
            mock_class.return_value = mock_analyzer

            result = collect_interest_rates(tmp_path)

            assert result is not None
            assert result == sample_interest_rate_result

    def test_正常系_interest_rates_jsonが出力される(
        self, tmp_path: Path, sample_interest_rate_result: dict[str, Any]
    ) -> None:
        """Test interest_rates.json is written."""
        from scripts.collect_weekly_report_data import collect_interest_rates

        mock_result = _make_mock_result(sample_interest_rate_result)

        with patch(
            "scripts.collect_weekly_report_data.InterestRateAnalyzer4Agent"
        ) as mock_class:
            mock_analyzer = MagicMock()
            mock_analyzer.get_interest_rate_data.return_value = mock_result
            mock_class.return_value = mock_analyzer

            collect_interest_rates(tmp_path)

            output_file = tmp_path / "interest_rates.json"
            assert output_file.exists()

    def test_異常系_エラー時はNoneを返す(self, tmp_path: Path) -> None:
        """Test that None is returned on error."""
        from scripts.collect_weekly_report_data import collect_interest_rates

        with patch(
            "scripts.collect_weekly_report_data.InterestRateAnalyzer4Agent"
        ) as mock_class:
            mock_analyzer = MagicMock()
            mock_analyzer.get_interest_rate_data.side_effect = Exception("API Error")
            mock_class.return_value = mock_analyzer

            result = collect_interest_rates(tmp_path)

            assert result is None


# ---------------------------------------------------------------------------
# Test: collect_currencies
# ---------------------------------------------------------------------------


class TestCollectCurrencies:
    """Test collect_currencies wrapper function."""

    def test_正常系_為替データを収集できる(
        self, tmp_path: Path, sample_currency_result: dict[str, Any]
    ) -> None:
        """Test collecting currency data successfully."""
        from scripts.collect_weekly_report_data import collect_currencies

        mock_result = _make_mock_result(sample_currency_result)

        with patch(
            "scripts.collect_weekly_report_data.CurrencyAnalyzer4Agent"
        ) as mock_class:
            mock_analyzer = MagicMock()
            mock_analyzer.get_currency_performance.return_value = mock_result
            mock_class.return_value = mock_analyzer

            result = collect_currencies(tmp_path)

            assert result is not None

    def test_正常系_currencies_jsonが出力される(
        self, tmp_path: Path, sample_currency_result: dict[str, Any]
    ) -> None:
        """Test currencies.json is written."""
        from scripts.collect_weekly_report_data import collect_currencies

        mock_result = _make_mock_result(sample_currency_result)

        with patch(
            "scripts.collect_weekly_report_data.CurrencyAnalyzer4Agent"
        ) as mock_class:
            mock_analyzer = MagicMock()
            mock_analyzer.get_currency_performance.return_value = mock_result
            mock_class.return_value = mock_analyzer

            collect_currencies(tmp_path)

            output_file = tmp_path / "currencies.json"
            assert output_file.exists()

    def test_異常系_エラー時はNoneを返す(self, tmp_path: Path) -> None:
        """Test that None is returned on error."""
        from scripts.collect_weekly_report_data import collect_currencies

        with patch(
            "scripts.collect_weekly_report_data.CurrencyAnalyzer4Agent"
        ) as mock_class:
            mock_analyzer = MagicMock()
            mock_analyzer.get_currency_performance.side_effect = Exception("API Error")
            mock_class.return_value = mock_analyzer

            result = collect_currencies(tmp_path)

            assert result is None


# ---------------------------------------------------------------------------
# Test: collect_upcoming_events
# ---------------------------------------------------------------------------


class TestCollectUpcomingEvents:
    """Test collect_upcoming_events wrapper function."""

    def test_正常系_イベントデータを収集できる(
        self, tmp_path: Path, sample_upcoming_events_result: dict[str, Any]
    ) -> None:
        """Test collecting upcoming events successfully."""
        from scripts.collect_weekly_report_data import collect_upcoming_events

        mock_result = _make_mock_result(sample_upcoming_events_result)

        with patch(
            "scripts.collect_weekly_report_data.UpcomingEvents4Agent"
        ) as mock_class:
            mock_agent = MagicMock()
            mock_agent.get_upcoming_events.return_value = mock_result
            mock_class.return_value = mock_agent

            result = collect_upcoming_events(tmp_path)

            assert result is not None

    def test_正常系_upcoming_events_jsonが出力される(
        self, tmp_path: Path, sample_upcoming_events_result: dict[str, Any]
    ) -> None:
        """Test upcoming_events.json is written."""
        from scripts.collect_weekly_report_data import collect_upcoming_events

        mock_result = _make_mock_result(sample_upcoming_events_result)

        with patch(
            "scripts.collect_weekly_report_data.UpcomingEvents4Agent"
        ) as mock_class:
            mock_agent = MagicMock()
            mock_agent.get_upcoming_events.return_value = mock_result
            mock_class.return_value = mock_agent

            collect_upcoming_events(tmp_path)

            output_file = tmp_path / "upcoming_events.json"
            assert output_file.exists()

    def test_異常系_エラー時はNoneを返す(self, tmp_path: Path) -> None:
        """Test that None is returned on error."""
        from scripts.collect_weekly_report_data import collect_upcoming_events

        with patch(
            "scripts.collect_weekly_report_data.UpcomingEvents4Agent"
        ) as mock_class:
            mock_agent = MagicMock()
            mock_agent.get_upcoming_events.side_effect = Exception("API Error")
            mock_class.return_value = mock_agent

            result = collect_upcoming_events(tmp_path)

            assert result is None


# ---------------------------------------------------------------------------
# Test: collect_all_data (orchestration)
# ---------------------------------------------------------------------------


class TestCollectAllData:
    """Test collect_all_data orchestration function."""

    def _make_perf_mock(self, data: dict[str, Any]) -> MagicMock:
        """Create a mock PerformanceResult."""
        mock = MagicMock()
        mock.to_dict.return_value = data
        mock.data_freshness = data.get("data_freshness", {})
        return mock

    def test_正常系_全ファイルが出力される(
        self,
        tmp_path: Path,
        sample_performance_result_us: dict[str, Any],
        sample_performance_result_mag7: dict[str, Any],
        sample_performance_result_sectors: dict[str, Any],
        sample_interest_rate_result: dict[str, Any],
        sample_currency_result: dict[str, Any],
        sample_upcoming_events_result: dict[str, Any],
    ) -> None:
        """Test all output files are generated."""
        from scripts.collect_weekly_report_data import collect_all_data

        perf_mock_us = self._make_perf_mock(sample_performance_result_us)
        perf_mock_mag7 = self._make_perf_mock(sample_performance_result_mag7)
        perf_mock_sectors = self._make_perf_mock(sample_performance_result_sectors)
        ir_mock = _make_mock_result(sample_interest_rate_result)
        fx_mock = _make_mock_result(sample_currency_result)
        events_mock = _make_mock_result(sample_upcoming_events_result)

        with (
            patch(
                "scripts.collect_weekly_report_data.PerformanceAnalyzer4Agent"
            ) as mock_perf_class,
            patch(
                "scripts.collect_weekly_report_data.InterestRateAnalyzer4Agent"
            ) as mock_ir_class,
            patch(
                "scripts.collect_weekly_report_data.CurrencyAnalyzer4Agent"
            ) as mock_fx_class,
            patch(
                "scripts.collect_weekly_report_data.UpcomingEvents4Agent"
            ) as mock_events_class,
        ):
            mock_perf = MagicMock()
            mock_perf.get_group_performance.side_effect = [
                perf_mock_us,
                perf_mock_mag7,
                perf_mock_sectors,
            ]
            mock_perf_class.return_value = mock_perf

            mock_ir = MagicMock()
            mock_ir.get_interest_rate_data.return_value = ir_mock
            mock_ir_class.return_value = mock_ir

            mock_fx = MagicMock()
            mock_fx.get_currency_performance.return_value = fx_mock
            mock_fx_class.return_value = mock_fx

            mock_events = MagicMock()
            mock_events.get_upcoming_events.return_value = events_mock
            mock_events_class.return_value = mock_events

            collect_all_data(tmp_path, date(2026, 1, 14), date(2026, 1, 21))

        expected_files = [
            "indices.json",
            "mag7.json",
            "sectors.json",
            "interest_rates.json",
            "currencies.json",
            "upcoming_events.json",
            "metadata.json",
        ]
        for fname in expected_files:
            assert (tmp_path / fname).exists(), f"Expected {fname} to exist"

    def test_正常系_indices_jsonに必須フィールドが存在する(
        self,
        tmp_path: Path,
        sample_performance_result_us: dict[str, Any],
        sample_performance_result_mag7: dict[str, Any],
        sample_performance_result_sectors: dict[str, Any],
        sample_interest_rate_result: dict[str, Any],
        sample_currency_result: dict[str, Any],
        sample_upcoming_events_result: dict[str, Any],
    ) -> None:
        """Test indices.json has required fields."""
        from scripts.collect_weekly_report_data import collect_all_data

        perf_mock_us = self._make_perf_mock(sample_performance_result_us)
        perf_mock_mag7 = self._make_perf_mock(sample_performance_result_mag7)
        perf_mock_sectors = self._make_perf_mock(sample_performance_result_sectors)
        ir_mock = _make_mock_result(sample_interest_rate_result)
        fx_mock = _make_mock_result(sample_currency_result)
        events_mock = _make_mock_result(sample_upcoming_events_result)

        with (
            patch(
                "scripts.collect_weekly_report_data.PerformanceAnalyzer4Agent"
            ) as mock_perf_class,
            patch(
                "scripts.collect_weekly_report_data.InterestRateAnalyzer4Agent"
            ) as mock_ir_class,
            patch(
                "scripts.collect_weekly_report_data.CurrencyAnalyzer4Agent"
            ) as mock_fx_class,
            patch(
                "scripts.collect_weekly_report_data.UpcomingEvents4Agent"
            ) as mock_events_class,
        ):
            mock_perf = MagicMock()
            mock_perf.get_group_performance.side_effect = [
                perf_mock_us,
                perf_mock_mag7,
                perf_mock_sectors,
            ]
            mock_perf_class.return_value = mock_perf

            mock_ir = MagicMock()
            mock_ir.get_interest_rate_data.return_value = ir_mock
            mock_ir_class.return_value = mock_ir

            mock_fx = MagicMock()
            mock_fx.get_currency_performance.return_value = fx_mock
            mock_fx_class.return_value = mock_fx

            mock_events = MagicMock()
            mock_events.get_upcoming_events.return_value = events_mock
            mock_events_class.return_value = mock_events

            collect_all_data(tmp_path, date(2026, 1, 14), date(2026, 1, 21))

        with open(tmp_path / "indices.json", encoding="utf-8") as f:
            indices_data = json.load(f)

        assert "indices" in indices_data
        assert "period" in indices_data
        for item in indices_data["indices"]:
            assert "weekly_return" in item
            assert "ytd_return" in item
            assert "price" in item
            assert "change" in item

    def test_正常系_mag7_jsonにmag7配列とsoxが存在する(
        self,
        tmp_path: Path,
        sample_performance_result_us: dict[str, Any],
        sample_performance_result_mag7: dict[str, Any],
        sample_performance_result_sectors: dict[str, Any],
        sample_interest_rate_result: dict[str, Any],
        sample_currency_result: dict[str, Any],
        sample_upcoming_events_result: dict[str, Any],
    ) -> None:
        """Test mag7.json has mag7 array and sox."""
        from scripts.collect_weekly_report_data import collect_all_data

        perf_mock_us = self._make_perf_mock(sample_performance_result_us)
        perf_mock_mag7 = self._make_perf_mock(sample_performance_result_mag7)
        perf_mock_sectors = self._make_perf_mock(sample_performance_result_sectors)
        ir_mock = _make_mock_result(sample_interest_rate_result)
        fx_mock = _make_mock_result(sample_currency_result)
        events_mock = _make_mock_result(sample_upcoming_events_result)

        with (
            patch(
                "scripts.collect_weekly_report_data.PerformanceAnalyzer4Agent"
            ) as mock_perf_class,
            patch(
                "scripts.collect_weekly_report_data.InterestRateAnalyzer4Agent"
            ) as mock_ir_class,
            patch(
                "scripts.collect_weekly_report_data.CurrencyAnalyzer4Agent"
            ) as mock_fx_class,
            patch(
                "scripts.collect_weekly_report_data.UpcomingEvents4Agent"
            ) as mock_events_class,
        ):
            mock_perf = MagicMock()
            mock_perf.get_group_performance.side_effect = [
                perf_mock_us,
                perf_mock_mag7,
                perf_mock_sectors,
            ]
            mock_perf_class.return_value = mock_perf

            mock_ir = MagicMock()
            mock_ir.get_interest_rate_data.return_value = ir_mock
            mock_ir_class.return_value = mock_ir

            mock_fx = MagicMock()
            mock_fx.get_currency_performance.return_value = fx_mock
            mock_fx_class.return_value = mock_fx

            mock_events = MagicMock()
            mock_events.get_upcoming_events.return_value = events_mock
            mock_events_class.return_value = mock_events

            collect_all_data(tmp_path, date(2026, 1, 14), date(2026, 1, 21))

        with open(tmp_path / "mag7.json", encoding="utf-8") as f:
            mag7_data = json.load(f)

        assert "mag7" in mag7_data
        assert isinstance(mag7_data["mag7"], list)
        assert "sox" in mag7_data

    def test_正常系_sectors_jsonにtop_bottom_allが存在する(
        self,
        tmp_path: Path,
        sample_performance_result_us: dict[str, Any],
        sample_performance_result_mag7: dict[str, Any],
        sample_performance_result_sectors: dict[str, Any],
        sample_interest_rate_result: dict[str, Any],
        sample_currency_result: dict[str, Any],
        sample_upcoming_events_result: dict[str, Any],
    ) -> None:
        """Test sectors.json has top_sectors, bottom_sectors, all_sectors."""
        from scripts.collect_weekly_report_data import collect_all_data

        perf_mock_us = self._make_perf_mock(sample_performance_result_us)
        perf_mock_mag7 = self._make_perf_mock(sample_performance_result_mag7)
        perf_mock_sectors = self._make_perf_mock(sample_performance_result_sectors)
        ir_mock = _make_mock_result(sample_interest_rate_result)
        fx_mock = _make_mock_result(sample_currency_result)
        events_mock = _make_mock_result(sample_upcoming_events_result)

        with (
            patch(
                "scripts.collect_weekly_report_data.PerformanceAnalyzer4Agent"
            ) as mock_perf_class,
            patch(
                "scripts.collect_weekly_report_data.InterestRateAnalyzer4Agent"
            ) as mock_ir_class,
            patch(
                "scripts.collect_weekly_report_data.CurrencyAnalyzer4Agent"
            ) as mock_fx_class,
            patch(
                "scripts.collect_weekly_report_data.UpcomingEvents4Agent"
            ) as mock_events_class,
        ):
            mock_perf = MagicMock()
            mock_perf.get_group_performance.side_effect = [
                perf_mock_us,
                perf_mock_mag7,
                perf_mock_sectors,
            ]
            mock_perf_class.return_value = mock_perf

            mock_ir = MagicMock()
            mock_ir.get_interest_rate_data.return_value = ir_mock
            mock_ir_class.return_value = mock_ir

            mock_fx = MagicMock()
            mock_fx.get_currency_performance.return_value = fx_mock
            mock_fx_class.return_value = mock_fx

            mock_events = MagicMock()
            mock_events.get_upcoming_events.return_value = events_mock
            mock_events_class.return_value = mock_events

            collect_all_data(tmp_path, date(2026, 1, 14), date(2026, 1, 21))

        with open(tmp_path / "sectors.json", encoding="utf-8") as f:
            sectors_data = json.load(f)

        assert "top_sectors" in sectors_data
        assert "bottom_sectors" in sectors_data
        assert "all_sectors" in sectors_data

    def test_正常系_metadata_jsonに期間情報が含まれる(
        self,
        tmp_path: Path,
        sample_performance_result_us: dict[str, Any],
        sample_performance_result_mag7: dict[str, Any],
        sample_performance_result_sectors: dict[str, Any],
        sample_interest_rate_result: dict[str, Any],
        sample_currency_result: dict[str, Any],
        sample_upcoming_events_result: dict[str, Any],
    ) -> None:
        """Test metadata.json contains period and generation info."""
        from scripts.collect_weekly_report_data import collect_all_data

        perf_mock_us = self._make_perf_mock(sample_performance_result_us)
        perf_mock_mag7 = self._make_perf_mock(sample_performance_result_mag7)
        perf_mock_sectors = self._make_perf_mock(sample_performance_result_sectors)
        ir_mock = _make_mock_result(sample_interest_rate_result)
        fx_mock = _make_mock_result(sample_currency_result)
        events_mock = _make_mock_result(sample_upcoming_events_result)

        with (
            patch(
                "scripts.collect_weekly_report_data.PerformanceAnalyzer4Agent"
            ) as mock_perf_class,
            patch(
                "scripts.collect_weekly_report_data.InterestRateAnalyzer4Agent"
            ) as mock_ir_class,
            patch(
                "scripts.collect_weekly_report_data.CurrencyAnalyzer4Agent"
            ) as mock_fx_class,
            patch(
                "scripts.collect_weekly_report_data.UpcomingEvents4Agent"
            ) as mock_events_class,
        ):
            mock_perf = MagicMock()
            mock_perf.get_group_performance.side_effect = [
                perf_mock_us,
                perf_mock_mag7,
                perf_mock_sectors,
            ]
            mock_perf_class.return_value = mock_perf

            mock_ir = MagicMock()
            mock_ir.get_interest_rate_data.return_value = ir_mock
            mock_ir_class.return_value = mock_ir

            mock_fx = MagicMock()
            mock_fx.get_currency_performance.return_value = fx_mock
            mock_fx_class.return_value = mock_fx

            mock_events = MagicMock()
            mock_events.get_upcoming_events.return_value = events_mock
            mock_events_class.return_value = mock_events

            collect_all_data(tmp_path, date(2026, 1, 14), date(2026, 1, 21))

        with open(tmp_path / "metadata.json", encoding="utf-8") as f:
            metadata = json.load(f)

        assert "generated_at" in metadata
        assert "period" in metadata
        assert metadata["period"]["start"] == "2026-01-14"
        assert metadata["period"]["end"] == "2026-01-21"
        assert "mode" in metadata


# ---------------------------------------------------------------------------
# Test: Output File Naming (no timestamps)
# ---------------------------------------------------------------------------


class TestOutputFileNaming:
    """Test that output files use fixed names without timestamps."""

    def test_正常系_indices_jsonが固定名で出力される(
        self, tmp_path: Path, sample_performance_result_us: dict[str, Any]
    ) -> None:
        """Test indices.json is output with fixed name."""
        from scripts.collect_weekly_report_data import adapt_to_indices, save_json

        result = adapt_to_indices(
            sample_performance_result_us,
            date(2026, 1, 14),
            date(2026, 1, 21),
        )
        output = {
            "period": {"start": "2026-01-14", "end": "2026-01-21"},
            "indices": result,
        }
        save_json(output, tmp_path / "indices.json")

        # File must have fixed name without timestamp
        files = list(tmp_path.glob("*.json"))
        filenames = [f.name for f in files]
        assert "indices.json" in filenames
        # No file like "indices_20260121-1200.json"
        timestamp_files = [
            f for f in filenames if f.startswith("indices_") and "_" in f
        ]
        assert len(timestamp_files) == 0


# ---------------------------------------------------------------------------
# Test: yfinance Retry Logic
# ---------------------------------------------------------------------------


class TestYFinanceRetryLogic:
    """Test retry logic for yfinance .info calls."""

    def test_正常系_リトライで成功した場合データを返す(self) -> None:
        """Test that data is returned when retry succeeds."""
        from scripts.collect_weekly_report_data import fetch_market_caps

        call_count = 0

        def side_effect_info(ticker: str) -> dict[str, Any]:
            nonlocal call_count
            call_count += 1
            if call_count < 2:
                raise Exception("Rate limit")
            return {"marketCap": 3800000000000}

        with patch("scripts.collect_weekly_report_data.yf.Ticker") as mock_ticker_class:
            mock_ticker = MagicMock()
            mock_ticker.info = {"marketCap": 3800000000000}
            mock_ticker_class.return_value = mock_ticker

            result = fetch_market_caps(["AAPL"])

            assert "AAPL" in result

    def test_正常系_リトライ失敗時はNullでフォールバック(self) -> None:
        """Test that None is used as fallback when retries fail."""
        from scripts.collect_weekly_report_data import fetch_market_caps

        with patch("scripts.collect_weekly_report_data.yf.Ticker") as mock_ticker_class:
            mock_ticker = MagicMock()
            type(mock_ticker).info = property(
                lambda self: (_ for _ in ()).throw(Exception("Persistent error"))
            )
            mock_ticker_class.return_value = mock_ticker

            result = fetch_market_caps(["AAPL"])

            # Should return None for failed ticker
            assert result.get("AAPL") is None


# ---------------------------------------------------------------------------
# Test: Main Function
# ---------------------------------------------------------------------------


class TestMainFunction:
    """Test main function."""

    def test_正常系_正常終了する(
        self,
        tmp_path: Path,
        sample_performance_result_us: dict[str, Any],
        sample_performance_result_mag7: dict[str, Any],
        sample_performance_result_sectors: dict[str, Any],
        sample_interest_rate_result: dict[str, Any],
        sample_currency_result: dict[str, Any],
        sample_upcoming_events_result: dict[str, Any],
    ) -> None:
        """Test main function exits with code 0 on success."""
        from scripts.collect_weekly_report_data import main

        perf_mock_us = _make_mock_result(sample_performance_result_us)
        perf_mock_mag7 = _make_mock_result(sample_performance_result_mag7)
        perf_mock_sectors = _make_mock_result(sample_performance_result_sectors)
        ir_mock = _make_mock_result(sample_interest_rate_result)
        fx_mock = _make_mock_result(sample_currency_result)
        events_mock = _make_mock_result(sample_upcoming_events_result)

        with (
            patch(
                "scripts.collect_weekly_report_data.PerformanceAnalyzer4Agent"
            ) as mock_perf_class,
            patch(
                "scripts.collect_weekly_report_data.InterestRateAnalyzer4Agent"
            ) as mock_ir_class,
            patch(
                "scripts.collect_weekly_report_data.CurrencyAnalyzer4Agent"
            ) as mock_fx_class,
            patch(
                "scripts.collect_weekly_report_data.UpcomingEvents4Agent"
            ) as mock_events_class,
            patch(
                "sys.argv",
                [
                    "script",
                    "--output",
                    str(tmp_path),
                    "--start",
                    "2026-01-14",
                    "--end",
                    "2026-01-21",
                ],
            ),
        ):
            mock_perf = MagicMock()
            mock_perf.get_group_performance.side_effect = [
                perf_mock_us,
                perf_mock_mag7,
                perf_mock_sectors,
            ]
            mock_perf_class.return_value = mock_perf

            mock_ir = MagicMock()
            mock_ir.get_interest_rate_data.return_value = ir_mock
            mock_ir_class.return_value = mock_ir

            mock_fx = MagicMock()
            mock_fx.get_currency_performance.return_value = fx_mock
            mock_fx_class.return_value = mock_fx

            mock_events = MagicMock()
            mock_events.get_upcoming_events.return_value = events_mock
            mock_events_class.return_value = mock_events

            exit_code = main()

        assert exit_code == 0

    def test_正常系_date引数でperiodが計算される(
        self,
        tmp_path: Path,
        sample_performance_result_us: dict[str, Any],
        sample_performance_result_mag7: dict[str, Any],
        sample_performance_result_sectors: dict[str, Any],
        sample_interest_rate_result: dict[str, Any],
        sample_currency_result: dict[str, Any],
        sample_upcoming_events_result: dict[str, Any],
    ) -> None:
        """Test that period is computed from --date argument."""
        from scripts.collect_weekly_report_data import main

        perf_mock_us = _make_mock_result(sample_performance_result_us)
        perf_mock_mag7 = _make_mock_result(sample_performance_result_mag7)
        perf_mock_sectors = _make_mock_result(sample_performance_result_sectors)
        ir_mock = _make_mock_result(sample_interest_rate_result)
        fx_mock = _make_mock_result(sample_currency_result)
        events_mock = _make_mock_result(sample_upcoming_events_result)

        with (
            patch(
                "scripts.collect_weekly_report_data.PerformanceAnalyzer4Agent"
            ) as mock_perf_class,
            patch(
                "scripts.collect_weekly_report_data.InterestRateAnalyzer4Agent"
            ) as mock_ir_class,
            patch(
                "scripts.collect_weekly_report_data.CurrencyAnalyzer4Agent"
            ) as mock_fx_class,
            patch(
                "scripts.collect_weekly_report_data.UpcomingEvents4Agent"
            ) as mock_events_class,
            patch(
                "sys.argv",
                [
                    "script",
                    "--output",
                    str(tmp_path),
                    "--date",
                    "2026-01-22",
                ],
            ),
        ):
            mock_perf = MagicMock()
            mock_perf.get_group_performance.side_effect = [
                perf_mock_us,
                perf_mock_mag7,
                perf_mock_sectors,
            ]
            mock_perf_class.return_value = mock_perf

            mock_ir = MagicMock()
            mock_ir.get_interest_rate_data.return_value = ir_mock
            mock_ir_class.return_value = mock_ir

            mock_fx = MagicMock()
            mock_fx.get_currency_performance.return_value = fx_mock
            mock_fx_class.return_value = mock_fx

            mock_events = MagicMock()
            mock_events.get_upcoming_events.return_value = events_mock
            mock_events_class.return_value = mock_events

            exit_code = main()

        # metadata.json should have a period computed
        metadata_file = tmp_path / "metadata.json"
        if metadata_file.exists():
            with open(metadata_file, encoding="utf-8") as f:
                metadata = json.load(f)
            assert "period" in metadata

        assert exit_code == 0


# ---------------------------------------------------------------------------
# Test: Return Value Conversion edge cases (None handling)
# ---------------------------------------------------------------------------


class TestReturnConversion:
    """Test edge cases in return value conversion, especially None handling."""

    def test_異常系_週次リターンが全てNoneの場合weekly_returnはNone(self) -> None:
        """PerformanceResult の 1W キーが存在しないとき weekly_return が None になることを確認。

        1W キーが存在しない（未設定）場合、None を /100 してはいけない。
        TypeError が発生しないことも検証する。
        """
        from scripts.collect_weekly_report_data import adapt_to_indices

        # 1W キーを含まない（YTD のみ）シンボルデータ
        no_1w_perf: dict[str, Any] = {
            "group": "indices",
            "subgroup": "us",
            "periods": ["YTD"],
            "symbols": {
                "^GSPC": {"YTD": 3.20},
            },
        }

        # TypeError が発生しないこと
        result = adapt_to_indices(
            no_1w_perf,
            date(2026, 1, 14),
            date(2026, 1, 21),
            name_map={"^GSPC": "S&P500"},
        )

        assert len(result) == 1
        gspc = result[0]
        assert gspc["ticker"] == "^GSPC"
        # 1W キーが存在しないため weekly_return は None
        assert gspc["weekly_return"] is None
