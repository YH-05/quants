"""yfinance 日本株プリセットの単体テスト.

対象モジュール: src/news_scraper/yfinance.py (fetch_jp_stock_news)
対象定数: src/news_scraper/types.py (YFINANCE_JP_TICKERS, YFINANCE_JP_INDICES)
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pandas as pd
import pytest

from news_scraper.types import Article


class TestYfinanceJpConstants:
    """YFINANCE_JP_TICKERS / YFINANCE_JP_INDICES 定数のテスト."""

    def test_正常系_YFINANCE_JP_TICKERSが存在しリストである(self) -> None:
        """YFINANCE_JP_TICKERS が list[str] であることを確認。"""
        from news_scraper.types import YFINANCE_JP_TICKERS

        assert isinstance(YFINANCE_JP_TICKERS, list)
        assert len(YFINANCE_JP_TICKERS) >= 20
        assert all(isinstance(t, str) for t in YFINANCE_JP_TICKERS)

    def test_正常系_YFINANCE_JP_TICKERSが_Tサフィックスを持つ(self) -> None:
        """全ティッカーが .T サフィックスを持つことを確認。"""
        from news_scraper.types import YFINANCE_JP_TICKERS

        for ticker in YFINANCE_JP_TICKERS:
            assert ticker.endswith(".T"), f"{ticker} does not end with .T"

    def test_正常系_YFINANCE_JP_TICKERSに主要銘柄が含まれる(self) -> None:
        """主要な日本株銘柄が含まれることを確認。"""
        from news_scraper.types import YFINANCE_JP_TICKERS

        expected_tickers = [
            "7203.T",  # トヨタ
            "6758.T",  # ソニー
            "9984.T",  # ソフトバンクG
            "8306.T",  # 三菱UFJ
            "6861.T",  # キーエンス
            "9432.T",  # NTT
            "6501.T",  # 日立
            "8035.T",  # 東京エレクトロン
        ]
        for ticker in expected_tickers:
            assert ticker in YFINANCE_JP_TICKERS, f"{ticker} not in YFINANCE_JP_TICKERS"

    def test_正常系_YFINANCE_JP_INDICESが存在しリストである(self) -> None:
        """YFINANCE_JP_INDICES が list[str] であることを確認。"""
        from news_scraper.types import YFINANCE_JP_INDICES

        assert isinstance(YFINANCE_JP_INDICES, list)
        assert len(YFINANCE_JP_INDICES) >= 2

    def test_正常系_YFINANCE_JP_INDICESに日経225とTOPIXが含まれる(self) -> None:
        """日経225 と TOPIX が含まれることを確認。"""
        from news_scraper.types import YFINANCE_JP_INDICES

        assert "^N225" in YFINANCE_JP_INDICES
        assert "^TOPX" in YFINANCE_JP_INDICES

    def test_正常系_YFINANCE_JP_TICKERSに重複がない(self) -> None:
        """ティッカーリストに重複がないことを確認。"""
        from news_scraper.types import YFINANCE_JP_TICKERS

        assert len(YFINANCE_JP_TICKERS) == len(set(YFINANCE_JP_TICKERS))


class TestFetchJpStockNews:
    """fetch_jp_stock_news() のテスト."""

    def test_正常系_デフォルトティッカーでYFINANCE_JP_TICKERSが使われる(
        self,
    ) -> None:
        """tickers=None のとき YFINANCE_JP_TICKERS がデフォルトで使用されることを確認。"""
        from news_scraper.types import YFINANCE_JP_TICKERS
        from news_scraper.yfinance import fetch_jp_stock_news

        mock_session = MagicMock()
        mock_df = pd.DataFrame(
            [
                {
                    "title": "Test Article",
                    "url": "https://example.com",
                    "ticker": "7203.T",
                }
            ]
        )

        with patch(
            "news_scraper.yfinance.fetch_multiple_tickers", return_value=mock_df
        ) as mock_fetch:
            result = fetch_jp_stock_news(mock_session)

        mock_fetch.assert_called_once()
        call_args = mock_fetch.call_args
        assert call_args[0][0] is mock_session
        assert call_args[0][1] == YFINANCE_JP_TICKERS
        assert isinstance(result, list)

    def test_正常系_カスタムティッカー指定時にそのティッカーが使われる(
        self,
    ) -> None:
        """カスタムティッカーを指定したとき、そのティッカーリストが使用されることを確認。"""
        from news_scraper.yfinance import fetch_jp_stock_news

        mock_session = MagicMock()
        custom_tickers = ["7203.T", "6758.T"]
        mock_df = pd.DataFrame(
            [
                {
                    "title": "Toyota News",
                    "url": "https://example.com/toyota",
                    "ticker": "7203.T",
                }
            ]
        )

        with patch(
            "news_scraper.yfinance.fetch_multiple_tickers", return_value=mock_df
        ) as mock_fetch:
            result = fetch_jp_stock_news(mock_session, tickers=custom_tickers)

        mock_fetch.assert_called_once()
        call_args = mock_fetch.call_args
        assert call_args[0][1] == custom_tickers
        assert isinstance(result, list)

    def test_正常系_fetch_multiple_tickersの呼び出し引数を検証(self) -> None:
        """fetch_multiple_tickers に session, tickers, timeout が正しく渡されることを確認。"""
        from news_scraper.yfinance import fetch_jp_stock_news

        mock_session = MagicMock()
        mock_df = pd.DataFrame()

        with patch(
            "news_scraper.yfinance.fetch_multiple_tickers", return_value=mock_df
        ) as mock_fetch:
            fetch_jp_stock_news(mock_session, timeout=60)

        mock_fetch.assert_called_once()
        call_args = mock_fetch.call_args
        assert call_args[0][0] is mock_session
        assert call_args[1]["timeout"] == 60

    def test_正常系_DataFrameの各行がArticleに変換される(self) -> None:
        """fetch_multiple_tickers の DataFrame 結果が Article リストに変換されることを確認。"""
        from news_scraper.yfinance import fetch_jp_stock_news

        mock_session = MagicMock()
        mock_df = pd.DataFrame(
            [
                {
                    "title": "Article 1",
                    "url": "https://example.com/1",
                    "published": "2026-03-01T00:00:00+00:00",
                    "summary": "Summary 1",
                    "category": "",
                    "source": "yfinance_ticker",
                    "content": "",
                    "ticker": "7203.T",
                    "author": "",
                    "article_id": "id-001",
                    "metadata": {},
                },
                {
                    "title": "Article 2",
                    "url": "https://example.com/2",
                    "published": "2026-03-02T00:00:00+00:00",
                    "summary": "Summary 2",
                    "category": "",
                    "source": "yfinance_ticker",
                    "content": "",
                    "ticker": "6758.T",
                    "author": "",
                    "article_id": "id-002",
                    "metadata": {},
                },
            ]
        )

        with patch(
            "news_scraper.yfinance.fetch_multiple_tickers", return_value=mock_df
        ):
            result = fetch_jp_stock_news(mock_session)

        assert len(result) == 2
        assert all(isinstance(a, Article) for a in result)
        assert result[0].title == "Article 1"
        assert result[1].title == "Article 2"

    def test_エッジケース_空のDataFrameで空リストを返す(self) -> None:
        """fetch_multiple_tickers が空 DataFrame を返したとき空リストを返すことを確認。"""
        from news_scraper.yfinance import fetch_jp_stock_news

        mock_session = MagicMock()
        mock_df = pd.DataFrame()

        with patch(
            "news_scraper.yfinance.fetch_multiple_tickers", return_value=mock_df
        ):
            result = fetch_jp_stock_news(mock_session)

        assert result == []

    def test_正常系_戻り値の型がlist_Articleである(self) -> None:
        """戻り値が list[Article] であることを確認。"""
        from news_scraper.yfinance import fetch_jp_stock_news

        mock_session = MagicMock()
        mock_df = pd.DataFrame(
            [
                {
                    "title": "Test",
                    "url": "https://example.com",
                    "published": "",
                    "summary": "",
                    "category": "",
                    "source": "yfinance_ticker",
                    "content": "",
                    "ticker": "7203.T",
                    "author": "",
                    "article_id": "id-001",
                    "metadata": {},
                }
            ]
        )

        with patch(
            "news_scraper.yfinance.fetch_multiple_tickers", return_value=mock_df
        ):
            result = fetch_jp_stock_news(mock_session)

        assert isinstance(result, list)
        assert all(isinstance(a, Article) for a in result)
