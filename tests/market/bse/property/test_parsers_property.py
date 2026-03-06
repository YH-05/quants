"""Property-based tests for market.bse.parsers module.

Uses Hypothesis to verify invariant properties of cleaning functions,
CSV round-trip consistency, and missing value handling.

Test TODO List:
- [x] clean_price: arbitrary string never raises exception, result is float|None
- [x] clean_volume: arbitrary string never raises exception, result is int|None
- [x] clean_indian_number: arbitrary string never raises exception, result is float|None
- [x] clean_price: type preservation (finite floats produce float results)
- [x] clean_volume: type preservation (non-negative ints produce int results)
- [x] clean_indian_number: round-trip (comma-stripped number equals original)
- [x] _MISSING_VALUES: all sentinel values produce None across all cleaners
- [x] parse_historical_csv: CSV round-trip preserves row count
- [x] clean_price: NaN/inf safety (non-finite values return None)
"""

import math

import pandas as pd
from hypothesis import given, settings
from hypothesis import strategies as st

from market.bse.parsers import (
    _MISSING_VALUES,
    clean_indian_number,
    clean_price,
    clean_volume,
    parse_historical_csv,
)

# =============================================================================
# Strategies
# =============================================================================

finite_floats = st.floats(
    min_value=-1e12,
    max_value=1e12,
    allow_nan=False,
    allow_infinity=False,
)
"""Finite float strategy for generating valid numeric values."""

non_negative_ints = st.integers(min_value=0, max_value=10**9)
"""Non-negative integer strategy for volume-like values."""


# =============================================================================
# clean_price properties
# =============================================================================


class TestCleanPriceProperty:
    """Hypothesis property tests for clean_price."""

    @given(value=st.text(max_size=200))
    @settings(max_examples=200)
    def test_プロパティ_任意文字列入力で例外が発生しない(self, value: str) -> None:
        """任意の文字列を入力しても例外が発生しないこと。"""
        result = clean_price(value)
        assert result is None or isinstance(result, float)

    @given(number=finite_floats)
    @settings(max_examples=100)
    def test_プロパティ_有効な数値文字列はfloat型を返す(self, number: float) -> None:
        """有効な数値文字列は float 型の結果を返すこと（型保持）。"""
        value = f"{number:,.2f}"
        result = clean_price(value)
        assert result is not None
        assert isinstance(result, float)

    @given(
        number=st.sampled_from(
            [float("nan"), float("inf"), float("-inf")],
        )
    )
    def test_プロパティ_非有限値文字列はNoneを返す(self, number: float) -> None:
        """NaN, inf, -inf の文字列表現は None を返すこと（NaN安全性）。"""
        result = clean_price(str(number))
        assert result is None

    @given(number=finite_floats)
    @settings(max_examples=100)
    def test_プロパティ_変換結果は常に有限値(self, number: float) -> None:
        """clean_price が値を返す場合、その値は常に有限であること。"""
        value = f"{number:.2f}"
        result = clean_price(value)
        if result is not None:
            assert math.isfinite(result)


# =============================================================================
# clean_volume properties
# =============================================================================


class TestCleanVolumeProperty:
    """Hypothesis property tests for clean_volume."""

    @given(value=st.text(max_size=200))
    @settings(max_examples=200)
    def test_プロパティ_任意文字列入力で例外が発生しない(self, value: str) -> None:
        """任意の文字列を入力しても例外が発生しないこと。"""
        result = clean_volume(value)
        assert result is None or isinstance(result, int)

    @given(number=non_negative_ints)
    @settings(max_examples=100)
    def test_プロパティ_有効な整数文字列はint型を返す(self, number: int) -> None:
        """有効な整数文字列は int 型の結果を返すこと（型保持）。"""
        value = f"{number:,}"
        result = clean_volume(value)
        assert result is not None
        assert isinstance(result, int)
        assert result == number


# =============================================================================
# clean_indian_number properties
# =============================================================================


class TestCleanIndianNumberProperty:
    """Hypothesis property tests for clean_indian_number."""

    @given(value=st.text(max_size=200))
    @settings(max_examples=200)
    def test_プロパティ_任意文字列入力で例外が発生しない(self, value: str) -> None:
        """任意の文字列を入力しても例外が発生しないこと。"""
        result = clean_indian_number(value)
        assert result is None or isinstance(result, float)

    @given(number=st.integers(min_value=0, max_value=10**12))
    @settings(max_examples=100)
    def test_プロパティ_カンマ除去ラウンドトリップで元の値に戻る(
        self, number: int
    ) -> None:
        """カンマ付き数値文字列をパースすると元の値に等しいこと（ラウンドトリップ）。"""
        # Format as Indian-style comma-separated string
        s = str(number)
        if len(s) > 3:
            # Build Indian comma-separated format: last 3 digits, then groups of 2
            last_three = s[-3:]
            remaining = s[:-3]
            groups = []
            while remaining:
                groups.append(remaining[-2:])
                remaining = remaining[:-2]
            groups.reverse()
            indian_str = ",".join(groups) + "," + last_three
        else:
            indian_str = s

        result = clean_indian_number(indian_str)
        assert result is not None
        assert result == float(number)

    @given(number=finite_floats)
    @settings(max_examples=100)
    def test_プロパティ_変換結果は常に有限値(self, number: float) -> None:
        """clean_indian_number が値を返す場合、その値は常に有限であること。"""
        value = str(number)
        result = clean_indian_number(value)
        if result is not None:
            assert math.isfinite(result)


# =============================================================================
# _MISSING_VALUES sentinel handling
# =============================================================================


class TestMissingValuesProperty:
    """Hypothesis property tests for _MISSING_VALUES sentinel handling."""

    @given(sentinel=st.sampled_from(sorted(_MISSING_VALUES)))
    def test_プロパティ_全欠損値センチネルがNoneに変換される(
        self, sentinel: str
    ) -> None:
        """_MISSING_VALUES 内の全値が全クリーナーで None を返すこと。"""
        assert clean_price(sentinel) is None
        assert clean_volume(sentinel) is None
        assert clean_indian_number(sentinel) is None

    @given(
        sentinel=st.sampled_from(sorted(_MISSING_VALUES)),
        padding=st.sampled_from(["", " ", "  "]),
    )
    def test_プロパティ_前後空白付き欠損値もNoneに変換される(
        self, sentinel: str, padding: str
    ) -> None:
        """前後に空白が付いた欠損値もNoneを返すこと。"""
        padded = padding + sentinel + padding
        assert clean_price(padded) is None
        assert clean_indian_number(padded) is None


# =============================================================================
# parse_historical_csv round-trip properties
# =============================================================================


class TestParseHistoricalCsvProperty:
    """Hypothesis property tests for parse_historical_csv."""

    @given(
        num_rows=st.integers(min_value=1, max_value=20),
        price=finite_floats.filter(lambda x: 0.01 <= abs(x) <= 1e6),
    )
    @settings(max_examples=50)
    def test_プロパティ_CSVラウンドトリップで行数が保持される(
        self,
        num_rows: int,
        price: float,
    ) -> None:
        """N行のCSVをパースするとN行のDataFrameが生成されること。"""
        price_str = f"{price:.2f}"
        header = "ScripCode,ScripName,Open,High,Low,Close"
        rows = [
            f"{500000 + i},STOCK_{i},{price_str},{price_str},{price_str},{price_str}"
            for i in range(num_rows)
        ]
        csv_content = header + "\n" + "\n".join(rows) + "\n"

        df = parse_historical_csv(csv_content)

        assert isinstance(df, pd.DataFrame)
        assert len(df) == num_rows
        # Column renaming must have occurred
        assert "scrip_code" in df.columns
        assert "open" in df.columns
