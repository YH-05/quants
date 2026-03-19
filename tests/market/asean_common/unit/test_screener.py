"""Unit tests for market.asean_common.screener module.

Tests cover:
- fetch_tickers_from_screener: Single market ticker fetching via tradingview-screener
- fetch_all_asean_tickers: All 6 ASEAN markets ticker fetching
- Error handling: ModuleNotFoundError, API errors → AseanScreenerError
- DataFrame to TickerRecord conversion

All tests mock the tradingview-screener library to avoid external API calls.

Test TODO List:
- [x] fetch_tickers_from_screener: Returns list[TickerRecord] for valid market
- [x] fetch_tickers_from_screener: Maps ticker format correctly (EXCHANGE:SYMBOL → SYMBOL)
- [x] fetch_tickers_from_screener: Handles optional fields (sector, industry, market_cap, currency)
- [x] fetch_tickers_from_screener: Returns empty list when tradingview-screener not installed
- [x] fetch_tickers_from_screener: Raises AseanScreenerError on API error
- [x] fetch_all_asean_tickers: Returns dict with all 6 markets
- [x] fetch_all_asean_tickers: Aggregates results from all markets
- [x] fetch_all_asean_tickers: Returns empty lists when tradingview-screener not installed
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pandas as pd
import pytest

from market.asean_common.constants import (
    SCREENER_MARKET_MAP,
    YFINANCE_SUFFIX_MAP,
    AseanMarket,
)
from market.asean_common.errors import AseanScreenerError
from market.asean_common.types import TickerRecord

# ============================================================================
# Fixtures
# ============================================================================


@pytest.fixture
def mock_scanner_df_sgx() -> pd.DataFrame:
    """Provide a mock tradingview-screener DataFrame for SGX.

    Returns
    -------
    pd.DataFrame
        DataFrame mimicking tradingview-screener output for SGX.
    """
    return pd.DataFrame(
        {
            "ticker": ["SGX:D05", "SGX:O39", "SGX:U11"],
            "name": ["D05", "O39", "U11"],
            "exchange": ["SGX", "SGX", "SGX"],
            "market": ["singapore", "singapore", "singapore"],
            "type": ["stock", "stock", "stock"],
            "sector": ["Finance", "Finance", "Finance"],
            "industry": ["Major Banks", "Major Banks", "Major Banks"],
            "market_cap_basic": [162194553211, 94824926519, 60936841071],
            "currency": ["SGD", "SGD", "SGD"],
        }
    )


@pytest.fixture
def mock_scanner_df_with_none() -> pd.DataFrame:
    """Provide a mock tradingview-screener DataFrame with None values.

    Returns
    -------
    pd.DataFrame
        DataFrame with some None/NaN fields.
    """
    return pd.DataFrame(
        {
            "ticker": ["SGX:TEST"],
            "name": ["TEST"],
            "exchange": ["SGX"],
            "market": ["singapore"],
            "type": ["stock"],
            "sector": [None],
            "industry": [None],
            "market_cap_basic": [None],
            "currency": [None],
        }
    )


# ============================================================================
# Test: fetch_tickers_from_screener
# ============================================================================


class TestFetchTickersFromScreener:
    """Tests for fetch_tickers_from_screener function."""

    def test_正常系_有効な市場でTickerRecordリストを返す(
        self,
        mock_scanner_df_sgx: pd.DataFrame,
    ) -> None:
        """fetch_tickers_from_screener が有効な市場に対して TickerRecord リストを返すこと."""
        with patch("market.asean_common.screener._query_screener") as mock_query:
            mock_query.return_value = (3, mock_scanner_df_sgx)

            from market.asean_common.screener import fetch_tickers_from_screener

            result = fetch_tickers_from_screener(AseanMarket.SGX)

        assert isinstance(result, list)
        assert len(result) == 3
        assert all(isinstance(t, TickerRecord) for t in result)

    def test_正常系_ティッカーフォーマットが正しく変換される(
        self,
        mock_scanner_df_sgx: pd.DataFrame,
    ) -> None:
        """EXCHANGE:SYMBOL 形式から SYMBOL のみに変換されること."""
        with patch("market.asean_common.screener._query_screener") as mock_query:
            mock_query.return_value = (3, mock_scanner_df_sgx)

            from market.asean_common.screener import fetch_tickers_from_screener

            result = fetch_tickers_from_screener(AseanMarket.SGX)

        assert result[0].ticker == "D05"
        assert result[1].ticker == "O39"
        assert result[2].ticker == "U11"

    def test_正常系_yfinance_tickerが正しく生成される(
        self,
        mock_scanner_df_sgx: pd.DataFrame,
    ) -> None:
        """yfinance_ticker が ticker + yfinance_suffix で正しく生成されること."""
        with patch("market.asean_common.screener._query_screener") as mock_query:
            mock_query.return_value = (3, mock_scanner_df_sgx)

            from market.asean_common.screener import fetch_tickers_from_screener

            result = fetch_tickers_from_screener(AseanMarket.SGX)

        assert result[0].yfinance_ticker == "D05.SI"
        assert result[0].yfinance_suffix == ".SI"

    def test_正常系_marketフィールドが正しく設定される(
        self,
        mock_scanner_df_sgx: pd.DataFrame,
    ) -> None:
        """TickerRecord の market フィールドが正しい AseanMarket に設定されること."""
        with patch("market.asean_common.screener._query_screener") as mock_query:
            mock_query.return_value = (3, mock_scanner_df_sgx)

            from market.asean_common.screener import fetch_tickers_from_screener

            result = fetch_tickers_from_screener(AseanMarket.SGX)

        assert all(t.market == AseanMarket.SGX for t in result)

    def test_正常系_オプショナルフィールドが正しく設定される(
        self,
        mock_scanner_df_sgx: pd.DataFrame,
    ) -> None:
        """sector, industry, market_cap, currency が正しく設定されること."""
        with patch("market.asean_common.screener._query_screener") as mock_query:
            mock_query.return_value = (3, mock_scanner_df_sgx)

            from market.asean_common.screener import fetch_tickers_from_screener

            result = fetch_tickers_from_screener(AseanMarket.SGX)

        assert result[0].sector == "Finance"
        assert result[0].industry == "Major Banks"
        assert result[0].market_cap == 162194553211
        assert result[0].currency == "SGD"

    def test_正常系_Noneフィールドが正しくNoneになる(
        self,
        mock_scanner_df_with_none: pd.DataFrame,
    ) -> None:
        """None/NaN フィールドが TickerRecord で None になること."""
        with patch("market.asean_common.screener._query_screener") as mock_query:
            mock_query.return_value = (1, mock_scanner_df_with_none)

            from market.asean_common.screener import fetch_tickers_from_screener

            result = fetch_tickers_from_screener(AseanMarket.SGX)

        assert len(result) == 1
        assert result[0].sector is None
        assert result[0].industry is None
        assert result[0].market_cap is None
        assert result[0].currency is None

    def test_正常系_tradingview_screener未インストール時に空リストを返す(
        self,
    ) -> None:
        """tradingview-screener 未インストール時に空リストを返すこと."""
        with patch(
            "market.asean_common.screener._query_screener",
            side_effect=ModuleNotFoundError("No module named 'tradingview_screener'"),
        ):
            from market.asean_common.screener import fetch_tickers_from_screener

            result = fetch_tickers_from_screener(AseanMarket.SGX)

        assert result == []

    def test_異常系_APIエラー時にAseanScreenerErrorを送出する(
        self,
    ) -> None:
        """API エラー時に AseanScreenerError を raise すること."""
        with patch(
            "market.asean_common.screener._query_screener",
            side_effect=Exception("API connection failed"),
        ):
            from market.asean_common.screener import fetch_tickers_from_screener

            with pytest.raises(AseanScreenerError, match="API connection failed"):
                fetch_tickers_from_screener(AseanMarket.SGX)

    def test_正常系_空のDataFrameで空リストを返す(self) -> None:
        """API が空の DataFrame を返した場合に空リストを返すこと."""
        empty_df = pd.DataFrame(
            columns=pd.Index(
                [
                    "ticker",
                    "name",
                    "exchange",
                    "market",
                    "type",
                    "sector",
                    "industry",
                    "market_cap_basic",
                    "currency",
                ]
            ),
        )
        with patch("market.asean_common.screener._query_screener") as mock_query:
            mock_query.return_value = (0, empty_df)

            from market.asean_common.screener import fetch_tickers_from_screener

            result = fetch_tickers_from_screener(AseanMarket.SGX)

        assert result == []


# ============================================================================
# Test: fetch_all_asean_tickers
# ============================================================================


class TestFetchAllAseanTickers:
    """Tests for fetch_all_asean_tickers function."""

    def test_正常系_全6市場のキーを持つdictを返す(self) -> None:
        """fetch_all_asean_tickers が全6市場のキーを持つ dict を返すこと."""
        with patch(
            "market.asean_common.screener.fetch_tickers_from_screener"
        ) as mock_fetch:
            mock_fetch.return_value = []

            from market.asean_common.screener import fetch_all_asean_tickers

            result = fetch_all_asean_tickers()

        assert isinstance(result, dict)
        assert len(result) == 6
        for market in AseanMarket:
            assert market in result

    def test_正常系_各市場の結果がlist型である(self) -> None:
        """各市場の結果が list[TickerRecord] であること."""
        mock_ticker = TickerRecord(
            ticker="D05",
            name="DBS",
            market=AseanMarket.SGX,
            yfinance_suffix=YFINANCE_SUFFIX_MAP[AseanMarket.SGX],
        )
        with patch(
            "market.asean_common.screener.fetch_tickers_from_screener"
        ) as mock_fetch:
            mock_fetch.return_value = [mock_ticker]

            from market.asean_common.screener import fetch_all_asean_tickers

            result = fetch_all_asean_tickers()

        for _market, tickers in result.items():
            assert isinstance(tickers, list)

    def test_正常系_fetch_tickers_from_screenerが各市場で呼ばれる(self) -> None:
        """fetch_tickers_from_screener が全6市場で呼ばれること."""
        with patch(
            "market.asean_common.screener.fetch_tickers_from_screener"
        ) as mock_fetch:
            mock_fetch.return_value = []

            from market.asean_common.screener import fetch_all_asean_tickers

            fetch_all_asean_tickers()

        assert mock_fetch.call_count == 6
        called_markets = {call.args[0] for call in mock_fetch.call_args_list}
        assert called_markets == set(AseanMarket)

    def test_正常系_tradingview_screener未インストール時に全市場空リスト(
        self,
    ) -> None:
        """tradingview-screener 未インストール時に全市場が空リストになること."""
        with patch(
            "market.asean_common.screener.fetch_tickers_from_screener"
        ) as mock_fetch:
            mock_fetch.return_value = []

            from market.asean_common.screener import fetch_all_asean_tickers

            result = fetch_all_asean_tickers()

        for _market, tickers in result.items():
            assert tickers == []


# ============================================================================
# Test: _query_screener (internal helper)
# ============================================================================


class TestQueryScreener:
    """Tests for _query_screener internal helper."""

    def test_正常系_Queryオブジェクトを正しく構築する(self) -> None:
        """_query_screener が正しいパラメータで Query を構築すること."""
        mock_query_instance = MagicMock()
        mock_query_instance.set_markets.return_value = mock_query_instance
        mock_query_instance.select.return_value = mock_query_instance
        mock_query_instance.where.return_value = mock_query_instance
        mock_query_instance.limit.return_value = mock_query_instance
        mock_query_instance.get_scanner_data.return_value = (
            0,
            pd.DataFrame(),
        )

        mock_query_cls = MagicMock(return_value=mock_query_instance)
        mock_column_cls = MagicMock()

        mock_module = MagicMock()
        mock_module.Query = mock_query_cls
        mock_module.Column = mock_column_cls

        with patch.dict(
            "sys.modules",
            {"tradingview_screener": mock_module},
        ):
            from market.asean_common.screener import _query_screener

            _query_screener(AseanMarket.SGX)

        mock_query_instance.set_markets.assert_called_once_with("singapore")

    def test_異常系_ModuleNotFoundErrorがそのまま伝播する(self) -> None:
        """tradingview_screener 未インストール時に ModuleNotFoundError が伝播すること."""
        import builtins
        from typing import Any

        original_import = builtins.__import__

        def mock_import(name: str, *args: Any, **kwargs: Any) -> Any:
            if name == "tradingview_screener":
                raise ModuleNotFoundError("No module named 'tradingview_screener'")
            return original_import(name, *args, **kwargs)

        with patch("builtins.__import__", side_effect=mock_import):
            from market.asean_common.screener import _query_screener

            with pytest.raises(ModuleNotFoundError):
                _query_screener(AseanMarket.SGX)
