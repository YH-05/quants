"""Property-based tests for market.asean_common._utils and screener helpers.

Tests verify invariants of _is_nan and _extract_ticker_symbol using Hypothesis:
- _is_nan: float NaN always returns True, None returns False,
  int/str never return True
- _extract_ticker_symbol: "EXCHANGE:SYMBOL" format always extracts SYMBOL,
  plain strings are returned unchanged

Test TODO List:
- [x] _is_nan: float NaN は常に True
- [x] _is_nan: None は常に False
- [x] _is_nan: 任意の int は常に False
- [x] _is_nan: 任意の str は常に False
- [x] _extract_ticker_symbol: "EXCHANGE:SYMBOL" 形式で SYMBOL を抽出
- [x] _extract_ticker_symbol: コロンなし文字列はそのまま返却
- [x] _extract_ticker_symbol: 複数コロンは最初で分割
"""

from __future__ import annotations

from hypothesis import given, settings
from hypothesis import strategies as st

from market.asean_common._utils import _is_nan
from market.asean_common.screener import _extract_ticker_symbol


class TestIsNanProperty:
    """_is_nan のプロパティベーステスト。"""

    @given(
        value=st.just(float("nan")),
    )
    @settings(max_examples=50)
    def test_プロパティ_float_NaNは常にTrue(
        self,
        value: float,
    ) -> None:
        """float NaN を渡すと常に True を返すこと。"""
        assert _is_nan(value) is True

    @given(
        value=st.sampled_from([float("nan"), float("+nan"), float("-nan")]),
    )
    @settings(max_examples=50)
    def test_プロパティ_各種NaN表現は常にTrue(
        self,
        value: float,
    ) -> None:
        """各種 NaN 表現（nan, +nan, -nan）で常に True を返すこと。"""
        assert _is_nan(value) is True

    @given(
        value=st.none(),
    )
    @settings(max_examples=50)
    def test_プロパティ_Noneは常にFalse(
        self,
        value: None,
    ) -> None:
        """None を渡すと常に False を返すこと。"""
        assert _is_nan(value) is False

    @given(
        value=st.integers(min_value=-10_000, max_value=10_000),
    )
    @settings(max_examples=50)
    def test_プロパティ_任意のintは常にFalse(
        self,
        value: int,
    ) -> None:
        """任意の整数を渡すと常に False を返すこと。"""
        assert _is_nan(value) is False

    @given(
        value=st.text(min_size=0, max_size=50),
    )
    @settings(max_examples=50)
    def test_プロパティ_任意のstrは常にFalse(
        self,
        value: str,
    ) -> None:
        """任意の文字列を渡すと常に False を返すこと。"""
        assert _is_nan(value) is False

    @given(
        value=st.floats(allow_nan=False, allow_infinity=False),
    )
    @settings(max_examples=50)
    def test_プロパティ_NaN以外のfloatは常にFalse(
        self,
        value: float,
    ) -> None:
        """NaN 以外の有限 float を渡すと常に False を返すこと。"""
        assert _is_nan(value) is False


class TestExtractTickerSymbolProperty:
    """_extract_ticker_symbol のプロパティベーステスト。"""

    @given(
        exchange=st.text(
            alphabet=st.characters(whitelist_categories=("Lu",)),
            min_size=1,
            max_size=10,
        ),
        symbol=st.text(
            alphabet=st.characters(whitelist_categories=("Lu", "Nd")),
            min_size=1,
            max_size=10,
        ),
    )
    @settings(max_examples=50)
    def test_プロパティ_EXCHANGE_SYMBOL形式でSYMBOLを抽出(
        self,
        exchange: str,
        symbol: str,
    ) -> None:
        """'EXCHANGE:SYMBOL' 形式の入力から SYMBOL 部分を抽出すること。"""
        raw_ticker = f"{exchange}:{symbol}"
        result = _extract_ticker_symbol(raw_ticker)
        assert result == symbol

    @given(
        ticker=st.text(
            alphabet=st.characters(whitelist_categories=("Lu", "Ll", "Nd")),
            min_size=1,
            max_size=10,
        ).filter(lambda s: ":" not in s),
    )
    @settings(max_examples=50)
    def test_プロパティ_コロンなし文字列はそのまま返却(
        self,
        ticker: str,
    ) -> None:
        """コロンを含まない文字列はそのまま返すこと。"""
        result = _extract_ticker_symbol(ticker)
        assert result == ticker

    @given(
        exchange=st.text(
            alphabet=st.characters(whitelist_categories=("Lu",)),
            min_size=1,
            max_size=5,
        ),
        symbol=st.text(
            alphabet=st.characters(whitelist_categories=("Lu", "Nd")),
            min_size=1,
            max_size=5,
        ),
        extra=st.text(
            alphabet=st.characters(whitelist_categories=("Lu", "Nd")),
            min_size=1,
            max_size=5,
        ),
    )
    @settings(max_examples=50)
    def test_プロパティ_複数コロンは最初のコロンで分割(
        self,
        exchange: str,
        symbol: str,
        extra: str,
    ) -> None:
        """複数コロンがある場合、最初のコロンで分割し残りを全て返すこと。"""
        raw_ticker = f"{exchange}:{symbol}:{extra}"
        result = _extract_ticker_symbol(raw_ticker)
        assert result == f"{symbol}:{extra}"
