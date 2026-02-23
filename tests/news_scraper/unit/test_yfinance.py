"""yfinance.py の単体テスト.

対象モジュール: src/news_scraper/yfinance.py
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from news_scraper.types import Article, ScraperConfig


class TestFetchTickerNews:
    """fetch_ticker_news() のテスト."""

    def test_正常系_有効なティッカーで記事リストを返す(self) -> None:
        """有効なティッカーを指定したとき Article リストを返すことを確認。"""
        from news_scraper.yfinance import fetch_ticker_news

        mock_session = MagicMock()
        news_item = {
            "content": {
                "title": "Apple Earnings Beat",
                "canonicalUrl": {
                    "url": "https://finance.yahoo.com/news/apple-earnings"
                },
                "pubDate": "2026-02-23T12:00:00+00:00",
                "summary": "Apple beat earnings expectations.",
                "id": "article-001",
            }
        }

        mock_ticker = MagicMock()
        mock_ticker.news = [news_item]

        with patch("news_scraper.yfinance.yf.Ticker", return_value=mock_ticker):
            result = fetch_ticker_news(mock_session, "AAPL")

        assert len(result) == 1
        assert isinstance(result[0], Article)
        assert result[0].title == "Apple Earnings Beat"
        assert result[0].ticker == "AAPL"
        assert result[0].source == "yfinance_ticker"

    def test_正常系_contentがNoneのエントリをスキップする(self) -> None:
        """content が None のエントリはスキップして Article に変換しないことを確認。"""
        from news_scraper.yfinance import fetch_ticker_news

        mock_session = MagicMock()
        news_items = [
            {"content": None},  # スキップされるべきエントリ
            {
                "content": {
                    "title": "Valid Article",
                    "canonicalUrl": {"url": "https://finance.yahoo.com/news/valid"},
                    "pubDate": "2026-02-23T10:00:00+00:00",
                    "summary": "Valid summary.",
                    "id": "article-002",
                }
            },
        ]

        mock_ticker = MagicMock()
        mock_ticker.news = news_items

        with patch("news_scraper.yfinance.yf.Ticker", return_value=mock_ticker):
            result = fetch_ticker_news(mock_session, "AAPL")

        assert len(result) == 1
        assert result[0].title == "Valid Article"

    def test_正常系_全エントリがcontentNoneのとき空リストを返す(self) -> None:
        """全エントリの content が None のとき空リストを返すことを確認。"""
        from news_scraper.yfinance import fetch_ticker_news

        mock_session = MagicMock()
        news_items = [
            {"content": None},
            {"content": None},
        ]

        mock_ticker = MagicMock()
        mock_ticker.news = news_items

        with patch("news_scraper.yfinance.yf.Ticker", return_value=mock_ticker):
            result = fetch_ticker_news(mock_session, "AAPL")

        assert result == []

    def test_正常系_ニュースが0件のとき空リストを返す(self) -> None:
        """yf.Ticker.news が空リストのとき空リストを返すことを確認。"""
        from news_scraper.yfinance import fetch_ticker_news

        mock_session = MagicMock()
        mock_ticker = MagicMock()
        mock_ticker.news = []

        with patch("news_scraper.yfinance.yf.Ticker", return_value=mock_ticker):
            result = fetch_ticker_news(mock_session, "AAPL")

        assert result == []

    def test_正常系_記事がpublishedの降順でソートされる(self) -> None:
        """取得した記事が published の降順でソートされることを確認。"""
        from news_scraper.yfinance import fetch_ticker_news

        mock_session = MagicMock()
        news_items = [
            {
                "content": {
                    "title": "Older Article",
                    "canonicalUrl": {"url": "https://finance.yahoo.com/news/old"},
                    "pubDate": "2026-01-01T00:00:00+00:00",
                    "summary": "",
                    "id": "old-001",
                }
            },
            {
                "content": {
                    "title": "Newer Article",
                    "canonicalUrl": {"url": "https://finance.yahoo.com/news/new"},
                    "pubDate": "2026-02-23T12:00:00+00:00",
                    "summary": "",
                    "id": "new-001",
                }
            },
        ]

        mock_ticker = MagicMock()
        mock_ticker.news = news_items

        with patch("news_scraper.yfinance.yf.Ticker", return_value=mock_ticker):
            result = fetch_ticker_news(mock_session, "AAPL")

        assert len(result) == 2
        assert result[0].title == "Newer Article"
        assert result[1].title == "Older Article"

    def test_正常系_canonicalUrlが辞書でない場合URLが空文字になる(self) -> None:
        """canonicalUrl が dict でないとき url が空文字になることを確認。"""
        from news_scraper.yfinance import fetch_ticker_news

        mock_session = MagicMock()
        news_items = [
            {
                "content": {
                    "title": "No URL Article",
                    "canonicalUrl": "not-a-dict",
                    "pubDate": "2026-02-23T10:00:00+00:00",
                    "summary": "",
                    "id": "no-url-001",
                }
            }
        ]

        mock_ticker = MagicMock()
        mock_ticker.news = news_items

        with patch("news_scraper.yfinance.yf.Ticker", return_value=mock_ticker):
            result = fetch_ticker_news(mock_session, "MSFT")

        assert result[0].url == ""


class TestFetchArticleContent:
    """fetch_article_content() のテスト."""

    def test_正常系_trafilaturaで本文取得成功(self) -> None:
        """trafilatura が本文を返すとき記事情報 dict を返すことを確認。"""
        from news_scraper.yfinance import fetch_article_content

        html = "<html><body><h1>Finance Article</h1><p>Article body content.</p></body></html>"
        mock_session = MagicMock()
        mock_response = MagicMock()
        mock_response.text = html
        mock_session.get.return_value = mock_response

        with patch("news_scraper.yfinance.trafilatura.extract") as mock_extract:
            mock_extract.side_effect = ["Article body content.", None]
            result = fetch_article_content(
                mock_session, "https://finance.yahoo.com/news/test"
            )

        assert result is not None
        assert result["url"] == "https://finance.yahoo.com/news/test"
        assert result["content"] == "Article body content."

    def test_正常系_trafilatura本文抽出失敗でNoneを返す(self) -> None:
        """trafilatura が本文を返せないとき None を返すことを確認。"""
        from news_scraper.yfinance import fetch_article_content

        html = "<html><body></body></html>"
        mock_session = MagicMock()
        mock_response = MagicMock()
        mock_response.text = html
        mock_session.get.return_value = mock_response

        with patch("news_scraper.yfinance.trafilatura.extract", return_value=None):
            result = fetch_article_content(
                mock_session, "https://finance.yahoo.com/news/fail"
            )

        assert result is None

    def test_異常系_HTTPエラーでNoneを返す(self) -> None:
        """HTTP リクエストが例外を送出したとき None を返すことを確認。"""
        from news_scraper.yfinance import fetch_article_content

        mock_session = MagicMock()
        mock_session.get.side_effect = Exception("Connection error")

        result = fetch_article_content(
            mock_session, "https://finance.yahoo.com/news/error"
        )

        assert result is None

    def test_正常系_TEI_XMLからタイトルを抽出する(self) -> None:
        """xmltei 形式のメタデータから title が抽出されることを確認。"""
        from news_scraper.yfinance import fetch_article_content

        html = "<html><body><p>Content here.</p></body></html>"
        mock_session = MagicMock()
        mock_response = MagicMock()
        mock_response.text = html
        mock_session.get.return_value = mock_response

        tei_xml = "<TEI><teiHeader><title>Extracted Title</title></teiHeader></TEI>"

        with patch("news_scraper.yfinance.trafilatura.extract") as mock_extract:
            mock_extract.side_effect = ["Content here.", tei_xml]
            result = fetch_article_content(
                mock_session, "https://finance.yahoo.com/news/tei"
            )

        assert result is not None
        assert result["title"] == "Extracted Title"

    def test_正常系_TEI_XMLがNoneのときタイトルが空文字になる(self) -> None:
        """xmltei メタデータが None のとき title が空文字になることを確認。"""
        from news_scraper.yfinance import fetch_article_content

        html = "<html><body><p>Some content.</p></body></html>"
        mock_session = MagicMock()
        mock_response = MagicMock()
        mock_response.text = html
        mock_session.get.return_value = mock_response

        with patch("news_scraper.yfinance.trafilatura.extract") as mock_extract:
            mock_extract.side_effect = ["Some content.", None]
            result = fetch_article_content(
                mock_session, "https://finance.yahoo.com/news/notitle"
            )

        assert result is not None
        assert result["title"] == ""
