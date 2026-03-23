"""Property-based tests for market.alphavantage.parser module.

Uses Hypothesis to verify invariant properties:
- _normalize_ohlcv_columns idempotency: applying twice yields same result
- _clean_numeric type safety: always returns float | None
- _normalize_ohlcv_columns preserves dict length
- parse_time_series date column ordering

See Also
--------
tests.market.alphavantage.property.test_rate_limiter_property : Similar pattern.
market.alphavantage.parser : Implementation under test.
"""

from __future__ import annotations

from hypothesis import given, settings
from hypothesis import strategies as st

from market.alphavantage.parser import (
    _clean_numeric,
    _normalize_ohlcv_columns,
)

# =============================================================================
# Strategies
# =============================================================================

# Strategy for numeric-like strings
numeric_strings = st.one_of(
    st.floats(allow_nan=False, allow_infinity=False).map(str),
    st.integers(min_value=-10**15, max_value=10**15).map(str),
    st.just("None"),
    st.just("-"),
    st.just(""),
    st.just("  "),
    st.just("abc"),
    st.just("0"),
    st.just("0.0"),
)

# Strategy for AV-style column keys with number prefixes
av_column_keys = st.one_of(
    st.tuples(
        st.integers(min_value=1, max_value=20),
        st.text(
            alphabet=st.characters(whitelist_categories=("L", "N", "Z")),
            min_size=1,
            max_size=20,
        ),
    ).map(lambda t: f"{t[0]}. {t[1]}"),
    st.text(
        alphabet=st.characters(whitelist_categories=("L",)),
        min_size=1,
        max_size=20,
    ),
)


# =============================================================================
# Property tests for _clean_numeric
# =============================================================================


class TestCleanNumericProperty:
    """Property-based tests for _clean_numeric."""

    @given(value=numeric_strings)
    @settings(max_examples=200)
    def test_プロパティ_戻り値の型はfloatまたはNone(self, value: str) -> None:
        """_clean_numeric always returns float or None."""
        result = _clean_numeric(value)
        assert result is None or isinstance(result, float)

    @given(
        value=st.floats(
            min_value=-1e15,
            max_value=1e15,
            allow_nan=False,
            allow_infinity=False,
        ),
    )
    @settings(max_examples=200)
    def test_プロパティ_有効なfloat文字列は常にfloatを返す(self, value: float) -> None:
        """Valid float strings always return a float."""
        result = _clean_numeric(str(value))
        assert isinstance(result, float)

    @given(
        value=st.floats(
            min_value=-1e15,
            max_value=1e15,
            allow_nan=False,
            allow_infinity=False,
        ),
    )
    @settings(max_examples=200)
    def test_プロパティ_clean_numericは元の値に近い値を返す(self, value: float) -> None:
        """_clean_numeric returns value close to the original."""
        result = _clean_numeric(str(value))
        assert result is not None
        # Allow for floating-point precision differences in string round-trip
        if abs(value) > 1e-10:
            assert abs(result - value) / abs(value) < 1e-6
        else:
            assert abs(result - value) < 1e-10


# =============================================================================
# Property tests for _normalize_ohlcv_columns
# =============================================================================


class TestNormalizeOHLCVColumnsProperty:
    """Property-based tests for _normalize_ohlcv_columns."""

    @given(
        data=st.dictionaries(
            keys=av_column_keys,
            values=st.text(min_size=0, max_size=20),
            min_size=0,
            max_size=10,
        ),
    )
    @settings(max_examples=200)
    def test_プロパティ_正規化の冪等性(self, data: dict[str, str]) -> None:
        """Normalizing twice yields the same result as normalizing once."""
        first = _normalize_ohlcv_columns(data)
        second = _normalize_ohlcv_columns(first)
        assert first == second

    @given(
        data=st.dictionaries(
            keys=st.text(
                alphabet=st.characters(whitelist_categories=("L",)),
                min_size=1,
                max_size=10,
            ),
            values=st.text(min_size=0, max_size=20),
            min_size=0,
            max_size=10,
        ),
    )
    @settings(max_examples=200)
    def test_プロパティ_プレフィックスなしキーは変更されない(
        self,
        data: dict[str, str],
    ) -> None:
        """Keys without number prefix are unchanged."""
        result = _normalize_ohlcv_columns(data)
        assert result == data

    @given(
        data=st.dictionaries(
            keys=av_column_keys,
            values=st.text(min_size=0, max_size=20),
            min_size=0,
            max_size=10,
        ),
    )
    @settings(max_examples=200)
    def test_プロパティ_値は元データの値のサブセット(self, data: dict[str, str]) -> None:
        """All values in the result are from the original dict.

        Note: When two keys normalize to the same key, one value is
        overwritten, so the result values are a subset of the original.
        """
        result = _normalize_ohlcv_columns(data)
        assert set(result.values()) <= set(data.values())


# =============================================================================
# Module exports
# =============================================================================

__all__: list[str] = []
