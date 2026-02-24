"""Tests for ca_strategy return_calculator module.

PortfolioReturnCalculator calculates daily weighted portfolio returns with
corporate action handling (delisting/merger weight redistribution).

Key behaviors:
- calculate_returns() computes daily weighted returns from price data
- Corporate action on a given date sets affected ticker weight to 0 and
  redistributes proportionally to remaining tickers
- Weight sum is always approximately 1.0 after redistribution
- Data-missing tickers are excluded with a warning log
- Empty price data returns an empty Series
- calculate_benchmark_returns() uses equal weights (1/N)

Test requirements from Issue #3665:
- Normal: 3 tickers, 10 business days, correct weighted returns
- Corporate action: 1 ticker disappears, weight redistribution confirmed
- Weight invariant: weight sum == pytest.approx(1.0) before and after
- Edge case: all tickers missing data -> empty Series
- Edge case: PriceDataProvider returns empty dict
- Benchmark: equal-weight (1/N) initialization
- Property test: random weights/returns, sum(weights) ~ 1.0 at each step
"""

from __future__ import annotations

from datetime import date

import numpy as np
import pandas as pd
import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from dev.ca_strategy.price_provider import PriceDataProvider
from dev.ca_strategy.return_calculator import PortfolioReturnCalculator


# =============================================================================
# Helpers / Stubs
# =============================================================================
class StubPriceDataProvider:
    """Stub PriceDataProvider that returns pre-configured price data."""

    def __init__(self, data: dict[str, pd.Series]) -> None:
        self._data = data

    def fetch(
        self,
        tickers: list[str],
        start: date,
        end: date,
    ) -> dict[str, pd.Series]:
        return {t: self._data[t] for t in tickers if t in self._data}


class EmptyPriceDataProvider:
    """PriceDataProvider that always returns empty dict."""

    def fetch(
        self,
        tickers: list[str],
        start: date,
        end: date,
    ) -> dict[str, pd.Series]:
        return {}


def _make_price_series(
    prices: list[float],
    start: date = date(2024, 1, 2),
) -> pd.Series:
    """Create a price Series with business day index."""
    idx = pd.bdate_range(start=start, periods=len(prices), freq="B")
    return pd.Series(prices, index=idx, dtype=float)


# =============================================================================
# Test constants
# =============================================================================
_START = date(2024, 1, 2)
_END = date(2024, 1, 15)


def _make_3ticker_provider() -> StubPriceDataProvider:
    """Create a provider with 3 tickers over 10 business days.

    Prices:
    - AAPL: 100, 101, 102, 103, 104, 105, 106, 107, 108, 109
    - MSFT: 200, 202, 204, 206, 208, 210, 212, 214, 216, 218
    - GOOGL: 150, 149, 148, 147, 146, 145, 144, 143, 142, 141
    """
    return StubPriceDataProvider(
        {
            "AAPL": _make_price_series(
                [100, 101, 102, 103, 104, 105, 106, 107, 108, 109]
            ),
            "MSFT": _make_price_series(
                [200, 202, 204, 206, 208, 210, 212, 214, 216, 218]
            ),
            "GOOGL": _make_price_series(
                [150, 149, 148, 147, 146, 145, 144, 143, 142, 141]
            ),
        }
    )


# =============================================================================
# Normal case tests
# =============================================================================
class TestCalculateReturns:
    """calculate_returns() normal case tests."""

    def test_正常系_3銘柄10営業日で正しい加重リターンを計算(self) -> None:
        """3 tickers, 10 business days: correct weighted daily return."""
        provider = _make_3ticker_provider()
        calc = PortfolioReturnCalculator(
            price_provider=provider,
            corporate_actions=[],
        )
        weights = {"AAPL": 0.5, "MSFT": 0.3, "GOOGL": 0.2}
        result = calc.calculate_returns(weights=weights, start=_START, end=_END)

        assert isinstance(result, pd.Series)
        # 10 prices -> 9 daily returns
        assert len(result) == 9

        # Verify first daily return manually:
        # AAPL: (101-100)/100 = 0.01
        # MSFT: (202-200)/200 = 0.01
        # GOOGL: (149-150)/150 = -1/150
        expected_day1 = 0.5 * 0.01 + 0.3 * 0.01 + 0.2 * (-1 / 150)
        assert result.iloc[0] == pytest.approx(expected_day1, rel=1e-10)

    def test_正常系_返り値がDatetimeIndexを持つ(self) -> None:
        """Result Series should have a DatetimeIndex."""
        provider = _make_3ticker_provider()
        calc = PortfolioReturnCalculator(
            price_provider=provider,
            corporate_actions=[],
        )
        weights = {"AAPL": 0.5, "MSFT": 0.3, "GOOGL": 0.2}
        result = calc.calculate_returns(weights=weights, start=_START, end=_END)
        assert isinstance(result.index, pd.DatetimeIndex)

    def test_正常系_ウェイト合計が1でなくても動作する(self) -> None:
        """Weights not summing to 1.0 should still work (no normalization)."""
        provider = _make_3ticker_provider()
        calc = PortfolioReturnCalculator(
            price_provider=provider,
            corporate_actions=[],
        )
        weights = {"AAPL": 0.4, "MSFT": 0.4, "GOOGL": 0.2}
        result = calc.calculate_returns(weights=weights, start=_START, end=_END)
        assert len(result) == 9


# =============================================================================
# Corporate action tests
# =============================================================================
class TestCorporateActions:
    """Corporate action handling tests."""

    def test_正常系_コーポレートアクション発生時にウェイト再配分(self) -> None:
        """When a ticker has a corporate action, its weight goes to 0 and is
        redistributed proportionally to remaining tickers.
        """
        provider = _make_3ticker_provider()
        # GOOGL delisted on day 5 (2024-01-08, a Monday)
        actions = [
            {
                "ticker": "GOOGL",
                "action_date": "2024-01-08",
                "action_type": "delisting",
                "company_name": "Alphabet",
                "reason": "Test delisting",
            }
        ]
        calc = PortfolioReturnCalculator(
            price_provider=provider,
            corporate_actions=actions,
        )
        weights = {"AAPL": 0.5, "MSFT": 0.3, "GOOGL": 0.2}
        result = calc.calculate_returns(weights=weights, start=_START, end=_END)

        assert isinstance(result, pd.Series)
        assert len(result) == 9

        # After action date, GOOGL weight should be 0 and redistributed.
        # Before action (first 3 returns): GOOGL still has weight.
        # After action (from day 5 onward): Only AAPL and MSFT get weight.
        # Verify the return on day 5 and beyond excludes GOOGL contribution
        # by checking the post-action returns match AAPL/MSFT only.
        # After redistribution: AAPL = 0.5/(0.5+0.3) = 0.625, MSFT = 0.3/(0.5+0.3) = 0.375

        # Day 5 (index 4) return: prices from day 5 to day 6
        # AAPL: (105-104)/104
        # MSFT: (210-208)/208
        aapl_ret_day5 = (105 - 104) / 104
        msft_ret_day5 = (210 - 208) / 208
        expected_day5 = 0.625 * aapl_ret_day5 + 0.375 * msft_ret_day5
        assert result.iloc[4] == pytest.approx(expected_day5, rel=1e-10)

    def test_正常系_merger型コーポレートアクションでもウェイト再配分(self) -> None:
        """Merger action type should also trigger weight redistribution."""
        provider = _make_3ticker_provider()
        actions = [
            {
                "ticker": "MSFT",
                "action_date": "2024-01-05",
                "action_type": "merger",
                "company_name": "Microsoft",
                "reason": "Test merger",
            }
        ]
        calc = PortfolioReturnCalculator(
            price_provider=provider,
            corporate_actions=actions,
        )
        weights = {"AAPL": 0.5, "MSFT": 0.3, "GOOGL": 0.2}
        result = calc.calculate_returns(weights=weights, start=_START, end=_END)
        assert isinstance(result, pd.Series)
        assert len(result) == 9


# =============================================================================
# Weight invariant tests
# =============================================================================
class TestWeightInvariant:
    """Weight sum invariant tests."""

    def test_正常系_コーポレートアクション前後でウェイト合計が1(self) -> None:
        """Weight sum must remain approx 1.0 before and after corporate action."""
        provider = _make_3ticker_provider()
        actions = [
            {
                "ticker": "GOOGL",
                "action_date": "2024-01-08",
                "action_type": "delisting",
                "company_name": "Alphabet",
                "reason": "Test",
            }
        ]
        calc = PortfolioReturnCalculator(
            price_provider=provider,
            corporate_actions=actions,
        )
        weights = {"AAPL": 0.5, "MSFT": 0.3, "GOOGL": 0.2}

        # Access internal weight tracking via the result
        # We verify indirectly: the calculator should produce valid returns
        # that are consistent with weights summing to 1.0
        result = calc.calculate_returns(weights=weights, start=_START, end=_END)
        assert len(result) == 9

        # More direct check: use the _redistribute_weights helper
        new_weights = calc._redistribute_weights(
            current_weights=weights,
            removed_tickers={"GOOGL"},
        )
        assert sum(new_weights.values()) == pytest.approx(1.0)
        assert "GOOGL" not in new_weights

    def test_正常系_複数銘柄同時消失でもウェイト合計が1(self) -> None:
        """Multiple tickers removed at once: weight sum stays at 1.0."""
        calc = PortfolioReturnCalculator(
            price_provider=EmptyPriceDataProvider(),
            corporate_actions=[],
        )
        weights = {"AAPL": 0.4, "MSFT": 0.3, "GOOGL": 0.2, "JPM": 0.1}
        new_weights = calc._redistribute_weights(
            current_weights=weights,
            removed_tickers={"GOOGL", "JPM"},
        )
        assert sum(new_weights.values()) == pytest.approx(1.0)
        assert "GOOGL" not in new_weights
        assert "JPM" not in new_weights
        # AAPL: 0.4/0.7, MSFT: 0.3/0.7
        assert new_weights["AAPL"] == pytest.approx(0.4 / 0.7)
        assert new_weights["MSFT"] == pytest.approx(0.3 / 0.7)


# =============================================================================
# Edge case tests
# =============================================================================
class TestEdgeCases:
    """Edge case tests."""

    def test_エッジケース_全銘柄データ欠損で空Series(self) -> None:
        """When all tickers have no data, return empty Series."""
        provider = EmptyPriceDataProvider()
        calc = PortfolioReturnCalculator(
            price_provider=provider,
            corporate_actions=[],
        )
        weights = {"AAPL": 0.5, "MSFT": 0.5}
        result = calc.calculate_returns(weights=weights, start=_START, end=_END)
        assert isinstance(result, pd.Series)
        assert len(result) == 0

    def test_エッジケース_PriceDataProviderが空dictを返す(self) -> None:
        """PriceDataProvider returning empty dict should return empty Series."""
        provider = EmptyPriceDataProvider()
        calc = PortfolioReturnCalculator(
            price_provider=provider,
            corporate_actions=[],
        )
        weights = {"AAPL": 0.5, "MSFT": 0.3, "GOOGL": 0.2}
        result = calc.calculate_returns(weights=weights, start=_START, end=_END)
        assert isinstance(result, pd.Series)
        assert len(result) == 0

    def test_エッジケース_一部銘柄のみデータ欠損(self) -> None:
        """When some tickers have no data, they are excluded and weights are
        redistributed among available tickers.
        """
        # Only AAPL has data
        provider = StubPriceDataProvider(
            {"AAPL": _make_price_series([100, 101, 102, 103, 104])}
        )
        calc = PortfolioReturnCalculator(
            price_provider=provider,
            corporate_actions=[],
        )
        weights = {"AAPL": 0.5, "MSFT": 0.3, "GOOGL": 0.2}
        result = calc.calculate_returns(weights=weights, start=_START, end=_END)
        # Only AAPL returns should be present (4 daily returns from 5 prices)
        assert isinstance(result, pd.Series)
        assert len(result) == 4

    def test_エッジケース_全銘柄コーポレートアクションで消失(self) -> None:
        """When all tickers are removed by corporate actions, returns should
        be zero (or stop) from that point.
        """
        provider = _make_3ticker_provider()
        actions = [
            {
                "ticker": "AAPL",
                "action_date": "2024-01-04",
                "action_type": "delisting",
                "company_name": "Apple",
                "reason": "Test",
            },
            {
                "ticker": "MSFT",
                "action_date": "2024-01-04",
                "action_type": "delisting",
                "company_name": "Microsoft",
                "reason": "Test",
            },
            {
                "ticker": "GOOGL",
                "action_date": "2024-01-04",
                "action_type": "delisting",
                "company_name": "Alphabet",
                "reason": "Test",
            },
        ]
        calc = PortfolioReturnCalculator(
            price_provider=provider,
            corporate_actions=actions,
        )
        weights = {"AAPL": 0.5, "MSFT": 0.3, "GOOGL": 0.2}
        result = calc.calculate_returns(weights=weights, start=_START, end=_END)
        assert isinstance(result, pd.Series)
        # After all tickers removed, returns should be 0.0
        # First return (day 1->2) is before action, should be normal
        # Day 2 onward (after 2024-01-04): all weights are 0
        for i in range(2, len(result)):
            assert result.iloc[i] == pytest.approx(0.0)

    def test_エッジケース_同一日に複数コーポレートアクション発生(self) -> None:
        """Multiple corporate actions on the same date should remove all
        affected tickers simultaneously and redistribute weights once.
        """
        provider = _make_3ticker_provider()
        # AAPL and GOOGL both delist on 2024-01-08
        actions = [
            {
                "ticker": "AAPL",
                "action_date": "2024-01-08",
                "action_type": "delisting",
                "company_name": "Apple",
                "reason": "Test",
            },
            {
                "ticker": "GOOGL",
                "action_date": "2024-01-08",
                "action_type": "merger",
                "company_name": "Alphabet",
                "reason": "Test",
            },
        ]
        calc = PortfolioReturnCalculator(
            price_provider=provider,
            corporate_actions=actions,
        )
        weights = {"AAPL": 0.5, "MSFT": 0.3, "GOOGL": 0.2}
        result = calc.calculate_returns(weights=weights, start=_START, end=_END)

        assert isinstance(result, pd.Series)
        assert len(result) == 9

        # After 2024-01-08 (day 5+), only MSFT remains with weight 1.0
        # Day 5 (index 4): MSFT return = (210-208)/208
        msft_ret_day5 = (210 - 208) / 208
        assert result.iloc[4] == pytest.approx(msft_ret_day5, rel=1e-10)

    def test_エッジケース_NaN含む価格データでの振る舞い(self) -> None:
        """NaN values in price data should be treated as 0 return contribution."""
        prices_with_nan = {
            "AAPL": _make_price_series([100, 101, 102, 103, 104]),
            "MSFT": pd.Series(
                [200, float("nan"), 204, 206, 208],
                index=pd.bdate_range(start=_START, periods=5, freq="B"),
                dtype=float,
            ),
        }
        provider = StubPriceDataProvider(prices_with_nan)
        calc = PortfolioReturnCalculator(
            price_provider=provider,
            corporate_actions=[],
        )
        weights = {"AAPL": 0.5, "MSFT": 0.5}
        result = calc.calculate_returns(weights=weights, start=_START, end=_END)

        assert isinstance(result, pd.Series)
        # Should produce returns without crashing
        assert len(result) == 4
        # All values should be finite (NaN returns are treated as 0)
        assert all(np.isfinite(result))


# =============================================================================
# Benchmark returns tests
# =============================================================================
class TestCalculateBenchmarkReturns:
    """calculate_benchmark_returns() tests."""

    def test_正常系_等ウェイトで初期化される(self) -> None:
        """Benchmark returns use equal weight (1/N) for all tickers."""
        provider = _make_3ticker_provider()
        calc = PortfolioReturnCalculator(
            price_provider=provider,
            corporate_actions=[],
        )
        result = calc.calculate_benchmark_returns(
            tickers=["AAPL", "MSFT", "GOOGL"],
            start=_START,
            end=_END,
        )
        assert isinstance(result, pd.Series)
        assert len(result) == 9

        # Verify first return: equal weight = 1/3 each
        aapl_ret = (101 - 100) / 100
        msft_ret = (202 - 200) / 200
        googl_ret = (149 - 150) / 150
        expected = (aapl_ret + msft_ret + googl_ret) / 3
        assert result.iloc[0] == pytest.approx(expected, rel=1e-10)

    def test_エッジケース_空のtickerリスト(self) -> None:
        """Empty tickers list returns empty Series."""
        provider = _make_3ticker_provider()
        calc = PortfolioReturnCalculator(
            price_provider=provider,
            corporate_actions=[],
        )
        result = calc.calculate_benchmark_returns(tickers=[], start=_START, end=_END)
        assert isinstance(result, pd.Series)
        assert len(result) == 0

    def test_エッジケース_一部銘柄データなし(self) -> None:
        """Tickers without data are excluded from benchmark calculation."""
        provider = StubPriceDataProvider(
            {
                "AAPL": _make_price_series([100, 101, 102]),
                "MSFT": _make_price_series([200, 202, 204]),
            }
        )
        calc = PortfolioReturnCalculator(
            price_provider=provider,
            corporate_actions=[],
        )
        result = calc.calculate_benchmark_returns(
            tickers=["AAPL", "MSFT", "MISSING"],
            start=_START,
            end=_END,
        )
        assert isinstance(result, pd.Series)
        # 2 returns from 3 prices
        assert len(result) == 2


# =============================================================================
# Input validation tests
# =============================================================================
class TestParseActionsValidation:
    """_parse_actions input validation tests."""

    def test_異常系_tickerフィールド欠損でスキップされる(self) -> None:
        """Action missing 'ticker' field should be skipped, not crash."""
        actions = [
            {"action_date": "2024-01-05", "action_type": "delisting"},
        ]
        calc = PortfolioReturnCalculator(
            price_provider=EmptyPriceDataProvider(),
            corporate_actions=actions,
        )
        assert len(calc._corporate_actions) == 0

    def test_異常系_action_dateフィールド欠損でスキップされる(self) -> None:
        """Action missing 'action_date' field should be skipped."""
        actions = [
            {"ticker": "AAPL", "action_type": "delisting"},
        ]
        calc = PortfolioReturnCalculator(
            price_provider=EmptyPriceDataProvider(),
            corporate_actions=actions,
        )
        assert len(calc._corporate_actions) == 0

    def test_異常系_不正な日付フォーマットでスキップされる(self) -> None:
        """Invalid date format should be skipped."""
        actions = [
            {"ticker": "AAPL", "action_date": "not-a-date", "action_type": "delisting"},
        ]
        calc = PortfolioReturnCalculator(
            price_provider=EmptyPriceDataProvider(),
            corporate_actions=actions,
        )
        assert len(calc._corporate_actions) == 0

    def test_正常系_有効と無効が混在する場合は有効分のみ解析(self) -> None:
        """Mix of valid and invalid actions: only valid ones are parsed."""
        actions = [
            {"ticker": "AAPL", "action_date": "2024-01-05", "action_type": "delisting"},
            {"action_date": "2024-01-06", "action_type": "merger"},  # missing ticker
            {"ticker": "MSFT", "action_date": "bad-date", "action_type": "delisting"},
            {"ticker": "GOOGL", "action_date": "2024-01-08", "action_type": "merger"},
        ]
        calc = PortfolioReturnCalculator(
            price_provider=EmptyPriceDataProvider(),
            corporate_actions=actions,
        )
        assert len(calc._corporate_actions) == 2
        assert "AAPL" in calc._corporate_actions
        assert "GOOGL" in calc._corporate_actions


# =============================================================================
# Property tests
# =============================================================================
class TestPropertyWeightInvariant:
    """Property-based tests for weight invariant."""

    @given(
        weights=st.dictionaries(
            keys=st.sampled_from(["A", "B", "C", "D", "E"]),
            values=st.floats(min_value=0.01, max_value=1.0),
            min_size=2,
            max_size=5,
        ),
        remove_count=st.integers(min_value=0, max_value=3),
    )
    @settings(max_examples=50)
    def test_プロパティ_再配分後のウェイト合計が常に1(
        self,
        weights: dict[str, float],
        remove_count: int,
    ) -> None:
        """After weight redistribution, sum(weights) should approx 1.0."""
        # Normalize weights to sum to 1.0
        total = sum(weights.values())
        if total == 0:
            return  # skip degenerate case
        normalized = {k: v / total for k, v in weights.items()}

        calc = PortfolioReturnCalculator(
            price_provider=EmptyPriceDataProvider(),
            corporate_actions=[],
        )

        # Remove up to remove_count tickers (but leave at least 1)
        tickers = list(normalized.keys())
        max_removable = len(tickers) - 1
        actual_remove = min(remove_count, max_removable)
        removed = set(tickers[:actual_remove])

        if not removed:
            return  # nothing to test

        new_weights = calc._redistribute_weights(
            current_weights=normalized,
            removed_tickers=removed,
        )
        assert sum(new_weights.values()) == pytest.approx(1.0, abs=1e-10)
        for ticker in removed:
            assert ticker not in new_weights
