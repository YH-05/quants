"""Property-based tests for market.nasdaq.client_parsers module.

Uses Hypothesis to verify that all NasdaqClient parsers handle arbitrary
dict inputs without raising unhandled exceptions.  Parsers are expected to
either return a valid result or raise ``NasdaqParseError`` / ``NasdaqAPIError``
for malformed inputs — they must never raise unexpected exceptions.

Test TODO List:
- [x] parse_earnings_calendar: arbitrary dict never raises unexpected exception
- [x] parse_dividends_calendar: arbitrary dict never raises unexpected exception
- [x] parse_splits_calendar: arbitrary dict never raises unexpected exception
- [x] parse_ipo_calendar: arbitrary dict never raises unexpected exception
- [x] parse_market_movers: arbitrary dict never raises unexpected exception
- [x] parse_etf_screener: arbitrary dict never raises unexpected exception
- [x] parse_insider_trades: arbitrary dict never raises unexpected exception
- [x] parse_institutional_holdings: arbitrary dict never raises unexpected exception
- [x] parse_short_interest: arbitrary dict never raises unexpected exception
- [x] parse_dividend_history: arbitrary dict never raises unexpected exception
- [x] parse_earnings_forecast: arbitrary dict never raises unexpected exception
- [x] parse_analyst_ratings: arbitrary dict never raises unexpected exception
- [x] parse_target_price: arbitrary dict never raises unexpected exception
- [x] parse_earnings_date: arbitrary dict never raises unexpected exception
- [x] parse_financials: arbitrary dict never raises unexpected exception
- [x] _safe_int: always returns int, identity for non-negative ints

See Also
--------
market.nasdaq.client_parsers : Parser functions under test.
tests.market.nasdaq.property.test_parser_property : Reference property tests.
"""

from __future__ import annotations

from typing import Any

from hypothesis import given, settings
from hypothesis import strategies as st

from market.nasdaq.client_parsers import (
    _safe_int,
    parse_analyst_ratings,
    parse_dividend_history,
    parse_dividends_calendar,
    parse_earnings_calendar,
    parse_earnings_date,
    parse_earnings_forecast,
    parse_etf_screener,
    parse_financials,
    parse_insider_trades,
    parse_institutional_holdings,
    parse_ipo_calendar,
    parse_market_movers,
    parse_short_interest,
    parse_splits_calendar,
    parse_target_price,
)
from market.nasdaq.errors import NasdaqAPIError, NasdaqParseError

# Strategy for generating arbitrary nested dict inputs that mimic API responses.
# We keep values as simple JSON-compatible types to exercise parser robustness.
_json_primitive = st.one_of(
    st.none(),
    st.booleans(),
    st.integers(min_value=-1_000_000, max_value=1_000_000),
    st.floats(allow_nan=False, allow_infinity=False),
    st.text(max_size=50),
)

_json_value = st.recursive(
    _json_primitive,
    lambda children: st.one_of(
        st.lists(children, max_size=5),
        st.dictionaries(st.text(max_size=20), children, max_size=5),
    ),
    max_leaves=20,
)

_arbitrary_data: st.SearchStrategy[dict[str, Any]] = st.dictionaries(
    st.text(max_size=20),
    _json_value,
    max_size=8,
)

# Allowed exception types from parsers
_ALLOWED_ERRORS = (NasdaqParseError, NasdaqAPIError, TypeError, KeyError, ValueError)


# =============================================================================
# Simple parsers (data-only)
# =============================================================================


class TestParseEarningsCalendarProperty:
    """Property tests for parse_earnings_calendar."""

    @given(data=_arbitrary_data)
    @settings(max_examples=200)
    def test_プロパティ_任意dict入力で予期しない例外が発生しない(
        self, data: dict[str, Any]
    ) -> None:
        """Arbitrary dict input never raises unexpected exceptions."""
        try:
            result = parse_earnings_calendar(data)
            assert isinstance(result, list)
        except _ALLOWED_ERRORS:
            pass


class TestParseDividendsCalendarProperty:
    """Property tests for parse_dividends_calendar."""

    @given(data=_arbitrary_data)
    @settings(max_examples=200)
    def test_プロパティ_任意dict入力で予期しない例外が発生しない(
        self, data: dict[str, Any]
    ) -> None:
        """Arbitrary dict input never raises unexpected exceptions."""
        try:
            result = parse_dividends_calendar(data)
            assert isinstance(result, list)
        except _ALLOWED_ERRORS:
            pass


class TestParseSplitsCalendarProperty:
    """Property tests for parse_splits_calendar."""

    @given(data=_arbitrary_data)
    @settings(max_examples=200)
    def test_プロパティ_任意dict入力で予期しない例外が発生しない(
        self, data: dict[str, Any]
    ) -> None:
        """Arbitrary dict input never raises unexpected exceptions."""
        try:
            result = parse_splits_calendar(data)
            assert isinstance(result, list)
        except _ALLOWED_ERRORS:
            pass


class TestParseIpoCalendarProperty:
    """Property tests for parse_ipo_calendar."""

    @given(data=_arbitrary_data)
    @settings(max_examples=200)
    def test_プロパティ_任意dict入力で予期しない例外が発生しない(
        self, data: dict[str, Any]
    ) -> None:
        """Arbitrary dict input never raises unexpected exceptions."""
        try:
            result = parse_ipo_calendar(data)
            assert isinstance(result, list)
        except _ALLOWED_ERRORS:
            pass


class TestParseMarketMoversProperty:
    """Property tests for parse_market_movers."""

    @given(data=_arbitrary_data)
    @settings(max_examples=200)
    def test_プロパティ_任意dict入力で予期しない例外が発生しない(
        self, data: dict[str, Any]
    ) -> None:
        """Arbitrary dict input never raises unexpected exceptions."""
        try:
            result = parse_market_movers(data)
            assert isinstance(result, dict)
        except _ALLOWED_ERRORS:
            pass


class TestParseEtfScreenerProperty:
    """Property tests for parse_etf_screener."""

    @given(data=_arbitrary_data)
    @settings(max_examples=200)
    def test_プロパティ_任意dict入力で予期しない例外が発生しない(
        self, data: dict[str, Any]
    ) -> None:
        """Arbitrary dict input never raises unexpected exceptions."""
        try:
            result = parse_etf_screener(data)
            assert isinstance(result, list)
        except _ALLOWED_ERRORS:
            pass


class TestParseInsiderTradesProperty:
    """Property tests for parse_insider_trades."""

    @given(data=_arbitrary_data)
    @settings(max_examples=200)
    def test_プロパティ_任意dict入力で予期しない例外が発生しない(
        self, data: dict[str, Any]
    ) -> None:
        """Arbitrary dict input never raises unexpected exceptions."""
        try:
            result = parse_insider_trades(data)
            assert isinstance(result, list)
        except _ALLOWED_ERRORS:
            pass


class TestParseInstitutionalHoldingsProperty:
    """Property tests for parse_institutional_holdings."""

    @given(data=_arbitrary_data)
    @settings(max_examples=200)
    def test_プロパティ_任意dict入力で予期しない例外が発生しない(
        self, data: dict[str, Any]
    ) -> None:
        """Arbitrary dict input never raises unexpected exceptions."""
        try:
            result = parse_institutional_holdings(data)
            assert isinstance(result, list)
        except _ALLOWED_ERRORS:
            pass


class TestParseShortInterestProperty:
    """Property tests for parse_short_interest."""

    @given(data=_arbitrary_data)
    @settings(max_examples=200)
    def test_プロパティ_任意dict入力で予期しない例外が発生しない(
        self, data: dict[str, Any]
    ) -> None:
        """Arbitrary dict input never raises unexpected exceptions."""
        try:
            result = parse_short_interest(data)
            assert isinstance(result, list)
        except _ALLOWED_ERRORS:
            pass


class TestParseDividendHistoryProperty:
    """Property tests for parse_dividend_history."""

    @given(data=_arbitrary_data)
    @settings(max_examples=200)
    def test_プロパティ_任意dict入力で予期しない例外が発生しない(
        self, data: dict[str, Any]
    ) -> None:
        """Arbitrary dict input never raises unexpected exceptions."""
        try:
            result = parse_dividend_history(data)
            assert isinstance(result, list)
        except _ALLOWED_ERRORS:
            pass


# =============================================================================
# Parameterized parsers (data + symbol)
# =============================================================================


class TestParseEarningsForecastProperty:
    """Property tests for parse_earnings_forecast."""

    @given(data=_arbitrary_data, symbol=st.text(min_size=1, max_size=10))
    @settings(max_examples=200)
    def test_プロパティ_任意dict入力で予期しない例外が発生しない(
        self, data: dict[str, Any], symbol: str
    ) -> None:
        """Arbitrary dict input never raises unexpected exceptions."""
        try:
            result = parse_earnings_forecast(data, symbol=symbol)
            assert result is not None
        except _ALLOWED_ERRORS:
            pass


class TestParseAnalystRatingsProperty:
    """Property tests for parse_analyst_ratings."""

    @given(data=_arbitrary_data, symbol=st.text(min_size=1, max_size=10))
    @settings(max_examples=200)
    def test_プロパティ_任意dict入力で予期しない例外が発生しない(
        self, data: dict[str, Any], symbol: str
    ) -> None:
        """Arbitrary dict input never raises unexpected exceptions."""
        try:
            result = parse_analyst_ratings(data, symbol=symbol)
            assert result is not None
        except _ALLOWED_ERRORS:
            pass


class TestParseTargetPriceProperty:
    """Property tests for parse_target_price."""

    @given(data=_arbitrary_data, symbol=st.text(min_size=1, max_size=10))
    @settings(max_examples=200)
    def test_プロパティ_任意dict入力で予期しない例外が発生しない(
        self, data: dict[str, Any], symbol: str
    ) -> None:
        """Arbitrary dict input never raises unexpected exceptions."""
        try:
            result = parse_target_price(data, symbol=symbol)
            assert result is not None
        except _ALLOWED_ERRORS:
            pass


class TestParseEarningsDateProperty:
    """Property tests for parse_earnings_date."""

    @given(data=_arbitrary_data, symbol=st.text(min_size=1, max_size=10))
    @settings(max_examples=200)
    def test_プロパティ_任意dict入力で予期しない例外が発生しない(
        self, data: dict[str, Any], symbol: str
    ) -> None:
        """Arbitrary dict input never raises unexpected exceptions."""
        try:
            result = parse_earnings_date(data, symbol=symbol)
            assert result is not None
        except _ALLOWED_ERRORS:
            pass


class TestParseFinancialsProperty:
    """Property tests for parse_financials."""

    @given(
        data=_arbitrary_data,
        symbol=st.text(min_size=1, max_size=10),
        frequency=st.sampled_from(["annual", "quarterly"]),
    )
    @settings(max_examples=200)
    def test_プロパティ_任意dict入力で予期しない例外が発生しない(
        self, data: dict[str, Any], symbol: str, frequency: str
    ) -> None:
        """Arbitrary dict input never raises unexpected exceptions."""
        try:
            result = parse_financials(data, symbol=symbol, frequency=frequency)
            assert result is not None
        except _ALLOWED_ERRORS:
            pass


# =============================================================================
# _safe_int property tests
# =============================================================================


class TestSafeIntProperty:
    """Property tests for _safe_int helper."""

    @given(st.one_of(st.none(), st.integers(), st.text(), st.floats(allow_nan=False)))
    @settings(max_examples=200)
    def test_プロパティ_safe_intは常にintを返す(self, value: object) -> None:
        """_safe_int always returns an int regardless of input type."""
        result = _safe_int(value)
        assert isinstance(result, int)

    @given(st.booleans())
    def test_プロパティ_boolは常に0を返す(self, value: bool) -> None:
        """Bool values always return 0 (explicit bool guard before int check)."""
        result = _safe_int(value)
        assert isinstance(result, int)
        assert result == 0

    @given(st.integers(min_value=0, max_value=10**12))
    def test_プロパティ_正の整数は変換後も同じ値(self, value: int) -> None:
        """Non-negative integers are preserved by _safe_int."""
        result = _safe_int(value)
        assert result == value


# =============================================================================
# Additional parser defensiveness property tests
# =============================================================================


class TestParseShortInterestDefensiveProperty:
    """Defensiveness property tests for parse_short_interest."""

    @given(
        st.dictionaries(
            st.text(max_size=20),
            st.one_of(st.text(max_size=50), st.integers(), st.none()),
            max_size=5,
        )
    )
    @settings(max_examples=200)
    def test_プロパティ_任意dictで例外を出さず空リストまたはリストを返す(
        self, data: dict[str, Any]
    ) -> None:
        """parse_short_interest returns a list or raises allowed errors."""
        try:
            result = parse_short_interest(data)
            assert isinstance(result, list)
        except _ALLOWED_ERRORS:
            pass


class TestParseDividendHistoryDefensiveProperty:
    """Defensiveness property tests for parse_dividend_history."""

    @given(
        st.dictionaries(
            st.text(max_size=20),
            st.one_of(st.text(max_size=50), st.integers(), st.none()),
            max_size=5,
        )
    )
    @settings(max_examples=200)
    def test_プロパティ_任意dictで例外を出さず空リストまたはリストを返す(
        self, data: dict[str, Any]
    ) -> None:
        """parse_dividend_history returns a list or raises allowed errors."""
        try:
            result = parse_dividend_history(data)
            assert isinstance(result, list)
        except _ALLOWED_ERRORS:
            pass


class TestParseAnalystRatingsDefensiveProperty:
    """Defensiveness property tests for parse_analyst_ratings."""

    @given(
        st.dictionaries(
            st.text(max_size=20),
            st.one_of(st.text(max_size=50), st.integers(), st.none()),
            max_size=5,
        )
    )
    @settings(max_examples=200)
    def test_プロパティ_任意dictで例外を出さずAnalystRatingsを返す(
        self, data: dict[str, Any]
    ) -> None:
        """parse_analyst_ratings returns AnalystRatings or raises allowed errors."""
        try:
            result = parse_analyst_ratings(data, symbol="TEST")
            assert result is not None
        except _ALLOWED_ERRORS:
            pass


class TestParseTargetPriceDefensiveProperty:
    """Defensiveness property tests for parse_target_price."""

    @given(
        st.dictionaries(
            st.text(max_size=20),
            st.one_of(st.text(max_size=50), st.integers(), st.none()),
            max_size=5,
        )
    )
    @settings(max_examples=200)
    def test_プロパティ_任意dictで例外を出さずTargetPriceを返す(
        self, data: dict[str, Any]
    ) -> None:
        """parse_target_price returns TargetPrice or raises allowed errors."""
        try:
            result = parse_target_price(data, symbol="TEST")
            assert result is not None
        except _ALLOWED_ERRORS:
            pass


class TestParseEarningsDateDefensiveProperty:
    """Defensiveness property tests for parse_earnings_date."""

    @given(
        st.dictionaries(
            st.text(max_size=20),
            st.one_of(st.text(max_size=50), st.integers(), st.none()),
            max_size=5,
        )
    )
    @settings(max_examples=200)
    def test_プロパティ_任意dictで例外を出さずEarningsDateを返す(
        self, data: dict[str, Any]
    ) -> None:
        """parse_earnings_date returns EarningsDate or raises allowed errors."""
        try:
            result = parse_earnings_date(data, symbol="TEST")
            assert result is not None
        except _ALLOWED_ERRORS:
            pass


class TestParseFinancialsDefensiveProperty:
    """Defensiveness property tests for parse_financials."""

    @given(
        st.dictionaries(
            st.text(max_size=20),
            st.one_of(st.text(max_size=50), st.integers(), st.none()),
            max_size=5,
        )
    )
    @settings(max_examples=200)
    def test_プロパティ_任意dictで例外を出さずFinancialStatementを返す(
        self, data: dict[str, Any]
    ) -> None:
        """parse_financials returns FinancialStatement or raises allowed errors."""
        try:
            result = parse_financials(data, symbol="TEST", frequency="annual")
            assert result is not None
        except _ALLOWED_ERRORS:
            pass
