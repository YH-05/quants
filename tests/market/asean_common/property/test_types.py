"""Property-based tests for market.asean_common.types module.

Tests verify TickerRecord invariants using Hypothesis:
- yfinance_ticker is always ticker + yfinance_suffix
- frozen instances cannot be mutated
- all markets produce valid yfinance_ticker

Test TODO List:
- [x] yfinance_ticker == ticker + suffix for any ticker string
- [x] frozen: mutation raises FrozenInstanceError
- [x] all 6 markets produce valid records
"""

from dataclasses import FrozenInstanceError

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from market.asean_common.constants import YFINANCE_SUFFIX_MAP, AseanMarket
from market.asean_common.types import TickerRecord

# Strategy for valid ticker strings (non-empty alphanumeric)
ticker_strategy = st.text(
    alphabet=st.characters(whitelist_categories=("Lu", "Ll", "Nd")),
    min_size=1,
    max_size=10,
)

# Strategy for AseanMarket enum members
market_strategy = st.sampled_from(list(AseanMarket))


class TestTickerRecordProperty:
    """TickerRecord のプロパティベーステスト。"""

    @settings(max_examples=50, deadline=None)
    @given(
        ticker=ticker_strategy,
        market=market_strategy,
    )
    def test_プロパティ_yfinance_tickerはticker_plus_suffixである(
        self,
        ticker: str,
        market: AseanMarket,
    ) -> None:
        """yfinance_ticker が常に ticker + yfinance_suffix であること。"""
        suffix = YFINANCE_SUFFIX_MAP[market]
        record = TickerRecord(
            ticker=ticker,
            name="Test Company",
            market=market,
            yfinance_suffix=suffix,
        )
        assert record.yfinance_ticker == f"{ticker}{suffix}"

    @settings(max_examples=50, deadline=None)
    @given(
        ticker=ticker_strategy,
        market=market_strategy,
    )
    def test_プロパティ_frozenインスタンスは変更不可(
        self,
        ticker: str,
        market: AseanMarket,
    ) -> None:
        """frozen=True により全インスタンスが変更不可であること。"""
        suffix = YFINANCE_SUFFIX_MAP[market]
        record = TickerRecord(
            ticker=ticker,
            name="Test Company",
            market=market,
            yfinance_suffix=suffix,
        )
        with pytest.raises(FrozenInstanceError):
            record.ticker = "CHANGED"

    @settings(max_examples=50, deadline=None)
    @given(
        ticker=ticker_strategy,
        suffix_body=st.text(
            alphabet=st.characters(whitelist_categories=("Lu",)),
            min_size=1,
            max_size=3,
        ),
    )
    def test_プロパティ_任意のサフィックスでyfinance_tickerが正しい(
        self,
        ticker: str,
        suffix_body: str,
    ) -> None:
        """任意のサフィックス文字列でも yfinance_ticker が正しく生成されること。"""
        suffix = f".{suffix_body}"
        record = TickerRecord(
            ticker=ticker,
            name="Test Company",
            market=AseanMarket.SGX,
            yfinance_suffix=suffix,
        )
        assert record.yfinance_ticker == f"{ticker}{suffix}"

    def test_プロパティ_全6市場で有効なレコードが生成できる(self) -> None:
        """全6市場で有効な TickerRecord が生成できること。"""
        for market in AseanMarket:
            suffix = YFINANCE_SUFFIX_MAP[market]
            record = TickerRecord(
                ticker="TEST",
                name="Test Company",
                market=market,
                yfinance_suffix=suffix,
            )
            assert record.market == market
            assert record.yfinance_suffix == suffix
            assert record.yfinance_ticker == f"TEST{suffix}"
            assert record.is_active is True
            assert record.sector is None
            assert record.industry is None
            assert record.market_cap is None
            assert record.currency is None
