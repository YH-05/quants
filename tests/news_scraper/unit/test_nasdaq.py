"""nasdaq.py の単体テスト.

対象モジュール: src/news_scraper/nasdaq.py
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from news_scraper.types import Article, ScraperConfig


class TestFetchRssFeed:
    """fetch_rss_feed() のテスト."""

    def test_正常系_categoryNoneで全体フィードURLを使用する(self) -> None:
        """category=None のとき全体フィード URL でリクエストすることを確認。"""
        from news_scraper.nasdaq import fetch_rss_feed

        mock_session = MagicMock()
        mock_response = MagicMock()
        mock_response.text = "<rss/>"
        mock_session.get.return_value = mock_response

        mock_feed = MagicMock()
        mock_feed.entries = []

        with patch("news_scraper.nasdaq.feedparser.parse", return_value=mock_feed):
            result = fetch_rss_feed(mock_session, category=None)

        # 全体フィード URL を使用していることを確認
        call_args = mock_session.get.call_args
        assert "rssoutbound" in call_args[0][0]
        assert "category=" not in call_args[0][0]
        assert result == []

    def test_正常系_カテゴリ指定でカテゴリURLを使用する(self) -> None:
        """category='Markets' を指定したとき category パラメータ付き URL を使うことを確認。"""
        from news_scraper.nasdaq import fetch_rss_feed

        mock_session = MagicMock()
        mock_response = MagicMock()
        mock_response.text = "<rss/>"
        mock_session.get.return_value = mock_response

        mock_feed = MagicMock()
        mock_feed.entries = []

        with patch("news_scraper.nasdaq.feedparser.parse", return_value=mock_feed):
            fetch_rss_feed(mock_session, category="Markets")

        call_args = mock_session.get.call_args
        assert "category=Markets" in call_args[0][0]

    def test_正常系_有効な日付形式でISOフォーマットに変換される(self) -> None:
        """RFC 2822 形式の published が ISO 8601 に変換されることを確認。"""
        from news_scraper.nasdaq import fetch_rss_feed

        mock_session = MagicMock()
        mock_response = MagicMock()
        mock_response.text = "<rss/>"
        mock_session.get.return_value = mock_response

        entry = MagicMock()
        entry.get = lambda k, d="": {
            "title": "Market Update",
            "link": "https://nasdaq.com/article/1",
            "published": "Mon, 23 Feb 2026 12:00:00 +0000",
            "summary": "Summary here",
        }.get(k, d)

        mock_feed = MagicMock()
        mock_feed.entries = [entry]

        with patch("news_scraper.nasdaq.feedparser.parse", return_value=mock_feed):
            result = fetch_rss_feed(mock_session, category="Markets")

        assert len(result) == 1
        assert "2026-02-23" in result[0].published

    def test_正常系_日付パース失敗時は生文字列をフォールバックとして使用する(
        self,
    ) -> None:
        """日付パースが失敗したとき published に生文字列をそのまま使うことを確認。"""
        from news_scraper.nasdaq import fetch_rss_feed

        mock_session = MagicMock()
        mock_response = MagicMock()
        mock_response.text = "<rss/>"
        mock_session.get.return_value = mock_response

        entry = MagicMock()
        entry.get = lambda k, d="": {
            "title": "Article",
            "link": "https://nasdaq.com/article/2",
            "published": "invalid-date-format",
            "summary": "",
        }.get(k, d)

        mock_feed = MagicMock()
        mock_feed.entries = [entry]

        with patch("news_scraper.nasdaq.feedparser.parse", return_value=mock_feed):
            result = fetch_rss_feed(mock_session, category="Markets")

        assert len(result) == 1
        assert result[0].published == "invalid-date-format"

    def test_正常系_0件のフィードで空リストを返す(self) -> None:
        """RSS フィードにエントリが 0 件のとき空リストを返すことを確認。"""
        from news_scraper.nasdaq import fetch_rss_feed

        mock_session = MagicMock()
        mock_response = MagicMock()
        mock_response.text = "<rss/>"
        mock_session.get.return_value = mock_response

        mock_feed = MagicMock()
        mock_feed.entries = []

        with patch("news_scraper.nasdaq.feedparser.parse", return_value=mock_feed):
            result = fetch_rss_feed(mock_session, category="Markets")

        assert result == []

    def test_正常系_categoryNoneのとき記事のcategoryがgeneralになる(self) -> None:
        """category=None のとき Article.category が 'general' に設定されることを確認。"""
        from news_scraper.nasdaq import fetch_rss_feed

        mock_session = MagicMock()
        mock_response = MagicMock()
        mock_response.text = "<rss/>"
        mock_session.get.return_value = mock_response

        entry = MagicMock()
        entry.get = lambda k, d="": {
            "title": "General News",
            "link": "https://nasdaq.com/3",
            "published": "",
            "summary": "",
        }.get(k, d)

        mock_feed = MagicMock()
        mock_feed.entries = [entry]

        with patch("news_scraper.nasdaq.feedparser.parse", return_value=mock_feed):
            result = fetch_rss_feed(mock_session, category=None)

        assert result[0].category == "general"


class TestFetchArticleContent:
    """fetch_article_content() のテスト."""

    def test_正常系_trafilaturaで本文取得成功(self) -> None:
        """trafilatura が本文を返すとき記事情報 dict を返すことを確認。"""
        from news_scraper.nasdaq import fetch_article_content

        html = (
            "<html><body><h1>NASDAQ Article</h1>"
            "<time datetime='2026-01-20T08:00:00+00:00'>Jan 20</time>"
            "<p>Article body content.</p></body></html>"
        )
        mock_session = MagicMock()
        mock_response = MagicMock()
        mock_response.text = html
        mock_session.get.return_value = mock_response

        with patch(
            "news_scraper.nasdaq.trafilatura.extract",
            return_value="Article body content.",
        ):
            result = fetch_article_content(
                mock_session, "https://nasdaq.com/articles/test"
            )

        assert result is not None
        assert result["url"] == "https://nasdaq.com/articles/test"
        assert result["content"] == "Article body content."

    def test_正常系_trafilatura失敗後BeautifulSoupフォールバックで本文取得(
        self,
    ) -> None:
        """trafilatura が None を返し、article 要素が存在するとき本文を返すことを確認。"""
        from news_scraper.nasdaq import fetch_article_content

        html = (
            "<html><body>"
            "<article><p>Fallback article text from BS4.</p></article>"
            "</body></html>"
        )
        mock_session = MagicMock()
        mock_response = MagicMock()
        mock_response.text = html
        mock_session.get.return_value = mock_response

        with patch("news_scraper.nasdaq.trafilatura.extract", return_value=None):
            result = fetch_article_content(
                mock_session, "https://nasdaq.com/articles/test"
            )

        assert result is not None
        assert "Fallback article text from BS4." in result["content"]

    def test_正常系_trafilaturaもBeautifulSoupも失敗でNoneを返す(self) -> None:
        """trafilatura も BS4 フォールバックも失敗したとき None を返すことを確認。"""
        from news_scraper.nasdaq import fetch_article_content

        html = "<html><body><p>No structured content.</p></body></html>"
        mock_session = MagicMock()
        mock_response = MagicMock()
        mock_response.text = html
        mock_session.get.return_value = mock_response

        with patch("news_scraper.nasdaq.trafilatura.extract", return_value=None):
            result = fetch_article_content(
                mock_session, "https://nasdaq.com/articles/test"
            )

        assert result is None

    def test_異常系_HTTPエラーでNoneを返す(self) -> None:
        """HTTP リクエストが例外を送出したとき None を返すことを確認。"""
        from news_scraper.nasdaq import fetch_article_content

        mock_session = MagicMock()
        mock_session.get.side_effect = Exception("Connection refused")

        result = fetch_article_content(mock_session, "https://nasdaq.com/articles/fail")

        assert result is None


class TestFetchStockNewsApi:
    """fetch_stock_news_api() のテスト."""

    def test_正常系_API正常応答で記事リストを返す(self) -> None:
        """NASDAQ API が記事リストを返すとき Article リストを返すことを確認。"""
        from news_scraper.nasdaq import fetch_stock_news_api

        mock_session = MagicMock()
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "data": {
                "rows": [
                    {
                        "title": "Apple Reports Strong Earnings",
                        "url": "https://nasdaq.com/articles/apple-earnings",
                        "created": "2026-02-23T10:00:00+00:00",
                        "provider": "Reuters",
                    }
                ]
            }
        }
        mock_session.get.return_value = mock_response

        result = fetch_stock_news_api(mock_session, "AAPL")

        assert len(result) == 1
        assert isinstance(result[0], Article)
        assert result[0].title == "Apple Reports Strong Earnings"
        assert result[0].ticker == "AAPL"
        assert result[0].source == "nasdaq"

    def test_正常系_rowsが空のとき空リストを返す(self) -> None:
        """API レスポンスの rows が空のとき空リストを返すことを確認。"""
        from news_scraper.nasdaq import fetch_stock_news_api

        mock_session = MagicMock()
        mock_response = MagicMock()
        mock_response.json.return_value = {"data": {"rows": []}}
        mock_session.get.return_value = mock_response

        result = fetch_stock_news_api(mock_session, "AAPL")

        assert result == []

    def test_正常系_APIエラーで空リストを返す(self) -> None:
        """HTTP リクエストが例外を送出したとき空リストを返すことを確認。"""
        from news_scraper.nasdaq import fetch_stock_news_api

        mock_session = MagicMock()
        mock_session.get.side_effect = Exception("API error")

        result = fetch_stock_news_api(mock_session, "MSFT")

        assert result == []

    def test_正常系_tickerが大文字に正規化される(self) -> None:
        """小文字ティッカーを渡したとき Article.ticker が大文字になることを確認。"""
        from news_scraper.nasdaq import fetch_stock_news_api

        mock_session = MagicMock()
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "data": {
                "rows": [
                    {
                        "title": "News",
                        "url": "https://nasdaq.com/n",
                        "created": "2026-01-01",
                        "provider": "CNBC",
                    }
                ]
            }
        }
        mock_session.get.return_value = mock_response

        result = fetch_stock_news_api(mock_session, "aapl")

        assert result[0].ticker == "AAPL"


class TestAsyncFetchStockNewsApi:
    """async_fetch_stock_news_api() のテスト."""

    @pytest.mark.asyncio
    async def test_正常系_API正常応答で記事リストを返す(self) -> None:
        """NASDAQ API が記事リストを返すとき Article リストを返すことを確認。"""
        from news_scraper.nasdaq import async_fetch_stock_news_api

        mock_session = AsyncMock()
        mock_response = MagicMock()  # json() は同期呼び出しのため MagicMock を使用
        mock_response.raise_for_status = MagicMock()
        mock_response.json.return_value = {
            "data": {
                "rows": [
                    {
                        "title": "MSFT AI Strategy",
                        "url": "https://nasdaq.com/msft-ai",
                        "created": "2026-02-23T09:00:00+00:00",
                        "provider": "Bloomberg",
                    }
                ]
            }
        }
        mock_session.get.return_value = mock_response

        result = await async_fetch_stock_news_api(mock_session, "MSFT")

        assert len(result) == 1
        assert isinstance(result[0], Article)
        assert result[0].ticker == "MSFT"

    @pytest.mark.asyncio
    async def test_正常系_APIエラーで空リストを返す(self) -> None:
        """HTTP リクエストが例外を送出したとき空リストを返すことを確認。"""
        from news_scraper.nasdaq import async_fetch_stock_news_api

        mock_session = AsyncMock()
        mock_session.get.side_effect = Exception("Async API error")

        result = await async_fetch_stock_news_api(mock_session, "GOOG")

        assert result == []


class TestParseArticleDate:
    """_parse_article_date() のテスト."""

    def test_正常系_ISO8601形式をパースできる(self) -> None:
        """ISO 8601 形式の日付文字列を datetime にパースできることを確認。"""
        from datetime import datetime, timezone

        from news_scraper.nasdaq import _parse_article_date

        result = _parse_article_date("2026-02-23T12:00:00+00:00")

        assert result is not None
        assert isinstance(result, datetime)
        assert result.year == 2026
        assert result.month == 2
        assert result.day == 23

    def test_正常系_ISO8601形式Zサフィックスをパースできる(self) -> None:
        """ISO 8601 形式（Z サフィックス）の日付文字列をパースできることを確認。"""
        from news_scraper.nasdaq import _parse_article_date

        result = _parse_article_date("2026-01-15T08:30:00Z")

        assert result is not None
        assert result.year == 2026
        assert result.month == 1
        assert result.day == 15

    def test_正常系_MM_DD_YYYY形式をパースできる(self) -> None:
        """'MM/DD/YYYY' 形式の日付文字列を datetime にパースできることを確認。"""
        from news_scraper.nasdaq import _parse_article_date

        result = _parse_article_date("02/23/2026")

        assert result is not None
        assert result.year == 2026
        assert result.month == 2
        assert result.day == 23

    def test_正常系_Month_DD_YYYY形式をパースできる(self) -> None:
        """'Month DD, YYYY' 形式の日付文字列を datetime にパースできることを確認。"""
        from news_scraper.nasdaq import _parse_article_date

        result = _parse_article_date("February 23, 2026")

        assert result is not None
        assert result.year == 2026
        assert result.month == 2
        assert result.day == 23

    def test_正常系_月名省略形Month_DD_YYYY形式をパースできる(self) -> None:
        """'Mon DD, YYYY' 形式（月名省略形）の日付文字列をパースできることを確認。"""
        from news_scraper.nasdaq import _parse_article_date

        result = _parse_article_date("Feb 23, 2026")

        assert result is not None
        assert result.year == 2026
        assert result.month == 2
        assert result.day == 23

    def test_異常系_不正形式でNoneを返す(self) -> None:
        """認識できない形式の日付文字列で None を返すことを確認。"""
        from news_scraper.nasdaq import _parse_article_date

        result = _parse_article_date("not-a-date")

        assert result is None

    def test_異常系_空文字列でNoneを返す(self) -> None:
        """空文字列を渡したとき None を返すことを確認。"""
        from news_scraper.nasdaq import _parse_article_date

        result = _parse_article_date("")

        assert result is None

    def test_エッジケース_数字のみでNoneを返す(self) -> None:
        """数字のみの文字列を渡したとき None を返すことを確認。"""
        from news_scraper.nasdaq import _parse_article_date

        result = _parse_article_date("12345")

        assert result is None


class TestCategoryToUrlSegment:
    """_category_to_url_segment() のテスト."""

    def test_正常系_Marketsをmarketsに変換する(self) -> None:
        """'Markets' カテゴリを 'markets' URL セグメントに変換することを確認。"""
        from news_scraper.nasdaq import _category_to_url_segment

        result = _category_to_url_segment("Markets")

        assert result == "markets"

    def test_正常系_PersonalFinanceをpersonal_financeに変換する(self) -> None:
        """'Personal-Finance' カテゴリを 'personal-finance' URL セグメントに変換することを確認。"""
        from news_scraper.nasdaq import _category_to_url_segment

        result = _category_to_url_segment("Personal-Finance")

        assert result == "personal-finance"

    def test_正常系_全NASDAQ_CATEGORIESを正しく変換する(self) -> None:
        """全 NASDAQ_CATEGORIES が ValueError を送出せずに変換できることを確認。"""
        from news_scraper.nasdaq import _category_to_url_segment
        from news_scraper.types import NASDAQ_CATEGORIES

        for category in NASDAQ_CATEGORIES:
            result = _category_to_url_segment(category)
            assert isinstance(result, str)
            assert len(result) > 0
            # URL セグメントは小文字であることを確認
            assert result == result.lower()

    def test_正常系_Technologyをtechnologyに変換する(self) -> None:
        """'Technology' カテゴリを 'technology' URL セグメントに変換することを確認。"""
        from news_scraper.nasdaq import _category_to_url_segment

        result = _category_to_url_segment("Technology")

        assert result == "technology"

    def test_正常系_ETFsをetfsに変換する(self) -> None:
        """'ETFs' カテゴリを 'etfs' URL セグメントに変換することを確認。"""
        from news_scraper.nasdaq import _category_to_url_segment

        result = _category_to_url_segment("ETFs")

        assert result == "etfs"

    def test_正常系_IPOsをiposに変換する(self) -> None:
        """'IPOs' カテゴリを 'ipos' URL セグメントに変換することを確認。"""
        from news_scraper.nasdaq import _category_to_url_segment

        result = _category_to_url_segment("IPOs")

        assert result == "ipos"

    def test_異常系_不明カテゴリでValueErrorを送出する(self) -> None:
        """NASDAQ_CATEGORIES に含まれない不明カテゴリで ValueError を送出することを確認。"""
        from news_scraper.nasdaq import _category_to_url_segment

        with pytest.raises(ValueError, match="Unknown NASDAQ category"):
            _category_to_url_segment("UnknownCategory")

    def test_異常系_空文字列でValueErrorを送出する(self) -> None:
        """空文字列を渡したとき ValueError を送出することを確認。"""
        from news_scraper.nasdaq import _category_to_url_segment

        with pytest.raises(ValueError, match="Unknown NASDAQ category"):
            _category_to_url_segment("")


class TestFetchStockNewsApiPaginated:
    """fetch_stock_news_api_paginated() のテスト."""

    def _make_page_response(
        self,
        rows: list[dict],
        total_records: int = 40,
    ) -> MagicMock:
        """ページレスポンスモックを生成するヘルパー."""
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "data": {
                "rows": rows,
                "totalrecords": str(total_records),
            }
        }
        return mock_response

    def test_正常系_複数ページの記事を取得できる(self) -> None:
        """2 ページ分の記事が正しく結合されることを確認。"""
        from news_scraper.nasdaq import fetch_stock_news_api_paginated

        page1_rows = [
            {
                "title": f"Article {i}",
                "url": f"https://nasdaq.com/article/{i}",
                "created": "2026-02-23T10:00:00+00:00",
                "provider": "Reuters",
            }
            for i in range(3)
        ]
        page2_rows = [
            {
                "title": f"Article {i + 3}",
                "url": f"https://nasdaq.com/article/{i + 3}",
                "created": "2026-02-22T10:00:00+00:00",
                "provider": "Reuters",
            }
            for i in range(3)
        ]

        mock_session = MagicMock()
        mock_session.get.side_effect = [
            self._make_page_response(page1_rows, total_records=6),
            self._make_page_response(page2_rows, total_records=6),
        ]

        with patch("news_scraper.nasdaq.time.sleep"):
            result = fetch_stock_news_api_paginated(
                mock_session, "AAPL", max_articles=10, page_size=3
            )

        assert len(result) == 6
        assert all(isinstance(a, Article) for a in result)

    def test_正常系_totalrecordsで自動終了する(self) -> None:
        """totalrecords に達したとき追加リクエストを送らないことを確認。"""
        from news_scraper.nasdaq import fetch_stock_news_api_paginated

        rows = [
            {
                "title": "Article",
                "url": "https://nasdaq.com/a",
                "created": "2026-02-23T10:00:00+00:00",
                "provider": "Reuters",
            }
        ]

        mock_session = MagicMock()
        mock_session.get.return_value = self._make_page_response(rows, total_records=1)

        with patch("news_scraper.nasdaq.time.sleep"):
            result = fetch_stock_news_api_paginated(
                mock_session, "AAPL", max_articles=100, page_size=1
            )

        assert mock_session.get.call_count == 1
        assert len(result) == 1

    def test_正常系_max_articlesで取得数を制限できる(self) -> None:
        """max_articles を超えたとき取得を停止することを確認。"""
        from news_scraper.nasdaq import fetch_stock_news_api_paginated

        rows = [
            {
                "title": f"Article {i}",
                "url": f"https://nasdaq.com/article/{i}",
                "created": "2026-02-23T10:00:00+00:00",
                "provider": "Reuters",
            }
            for i in range(5)
        ]

        mock_session = MagicMock()
        mock_session.get.return_value = self._make_page_response(
            rows, total_records=100
        )

        with patch("news_scraper.nasdaq.time.sleep"):
            result = fetch_stock_news_api_paginated(
                mock_session, "AAPL", max_articles=5, page_size=5
            )

        assert mock_session.get.call_count == 1
        assert len(result) == 5

    def test_正常系_空rowsで早期終了する(self) -> None:
        """rows が空のとき追加リクエストを送らないことを確認。"""
        from news_scraper.nasdaq import fetch_stock_news_api_paginated

        mock_session = MagicMock()
        mock_session.get.return_value = self._make_page_response([], total_records=10)

        with patch("news_scraper.nasdaq.time.sleep"):
            result = fetch_stock_news_api_paginated(
                mock_session, "AAPL", max_articles=100, page_size=20
            )

        assert mock_session.get.call_count == 1
        assert result == []

    def test_正常系_start_dateより古い記事を除外する(self) -> None:
        """start_date より古い記事がフィルタリングされることを確認。"""
        from datetime import datetime

        from news_scraper.nasdaq import fetch_stock_news_api_paginated

        rows = [
            {
                "title": "New Article",
                "url": "https://nasdaq.com/new",
                "created": "2026-02-23T10:00:00+00:00",
                "provider": "Reuters",
            },
            {
                "title": "Old Article",
                "url": "https://nasdaq.com/old",
                "created": "2026-01-01T10:00:00+00:00",
                "provider": "Reuters",
            },
        ]

        mock_session = MagicMock()
        mock_session.get.return_value = self._make_page_response(rows, total_records=2)

        with patch("news_scraper.nasdaq.time.sleep"):
            result = fetch_stock_news_api_paginated(
                mock_session,
                "AAPL",
                max_articles=100,
                page_size=20,
                start_date=datetime(2026, 2, 1),
            )

        assert len(result) == 1
        assert result[0].title == "New Article"

    def test_正常系_end_dateより新しい記事を除外する(self) -> None:
        """end_date より新しい記事がフィルタリングされることを確認。"""
        from datetime import datetime

        from news_scraper.nasdaq import fetch_stock_news_api_paginated

        rows = [
            {
                "title": "Future Article",
                "url": "https://nasdaq.com/future",
                "created": "2026-03-01T10:00:00+00:00",
                "provider": "Reuters",
            },
            {
                "title": "Old Article",
                "url": "https://nasdaq.com/old",
                "created": "2026-01-15T10:00:00+00:00",
                "provider": "Reuters",
            },
        ]

        mock_session = MagicMock()
        mock_session.get.return_value = self._make_page_response(rows, total_records=2)

        with patch("news_scraper.nasdaq.time.sleep"):
            result = fetch_stock_news_api_paginated(
                mock_session,
                "AAPL",
                max_articles=100,
                page_size=20,
                end_date=datetime(2026, 2, 28),
            )

        assert len(result) == 1
        assert result[0].title == "Old Article"

    def test_正常系_全記事がstart_dateより古い場合に早期終了する(self) -> None:
        """ページ内の全記事が start_date より古い場合に次ページを取得しないことを確認。"""
        from datetime import datetime

        from news_scraper.nasdaq import fetch_stock_news_api_paginated

        rows = [
            {
                "title": "Very Old Article",
                "url": "https://nasdaq.com/very-old",
                "created": "2025-01-01T10:00:00+00:00",
                "provider": "Reuters",
            }
        ]

        mock_session = MagicMock()
        mock_session.get.return_value = self._make_page_response(
            rows, total_records=100
        )

        with patch("news_scraper.nasdaq.time.sleep"):
            result = fetch_stock_news_api_paginated(
                mock_session,
                "AAPL",
                max_articles=100,
                page_size=1,
                start_date=datetime(2026, 1, 1),
            )

        assert mock_session.get.call_count == 1
        assert result == []

    def test_正常系_APIエラー時に取得済みの部分結果を返す(self) -> None:
        """1 ページ目成功・2 ページ目エラーのとき 1 ページ目の記事を返すことを確認。"""
        from news_scraper.nasdaq import fetch_stock_news_api_paginated

        rows = [
            {
                "title": "Article 1",
                "url": "https://nasdaq.com/1",
                "created": "2026-02-23T10:00:00+00:00",
                "provider": "Reuters",
            }
        ]

        mock_session = MagicMock()
        mock_session.get.side_effect = [
            self._make_page_response(rows, total_records=100),
            Exception("Network error"),
        ]

        with patch("news_scraper.nasdaq.time.sleep"):
            result = fetch_stock_news_api_paginated(
                mock_session, "AAPL", max_articles=100, page_size=1
            )

        assert len(result) == 1
        assert result[0].title == "Article 1"

    def test_正常系_ページ間にget_delayでレートリミットする(self) -> None:
        """複数ページ取得時に time.sleep が呼ばれることを確認。"""
        from news_scraper.nasdaq import fetch_stock_news_api_paginated

        rows = [
            {
                "title": "Article",
                "url": "https://nasdaq.com/a",
                "created": "2026-02-23T10:00:00+00:00",
                "provider": "Reuters",
            }
        ]

        mock_session = MagicMock()
        mock_session.get.side_effect = [
            self._make_page_response(rows, total_records=3),
            self._make_page_response(rows, total_records=3),
            self._make_page_response(rows, total_records=3),
        ]

        config = ScraperConfig(delay=1.0, jitter=0.0)

        with patch("news_scraper.nasdaq.time.sleep") as mock_sleep:
            fetch_stock_news_api_paginated(
                mock_session, "AAPL", max_articles=3, page_size=1, config=config
            )

        assert mock_sleep.call_count >= 1

    def test_異常系_不正なtickerでValueErrorを送出する(self) -> None:
        """不正な ticker シンボルで ValueError を送出することを確認。"""
        from news_scraper.nasdaq import fetch_stock_news_api_paginated

        mock_session = MagicMock()

        with pytest.raises(ValueError, match="Invalid ticker symbol"):
            fetch_stock_news_api_paginated(mock_session, "INVALID!!!!")

    def test_正常系_tickerが大文字に正規化される(self) -> None:
        """小文字ティッカーを渡したとき Article.ticker が大文字になることを確認。"""
        from news_scraper.nasdaq import fetch_stock_news_api_paginated

        rows = [
            {
                "title": "Article",
                "url": "https://nasdaq.com/a",
                "created": "2026-02-23T10:00:00+00:00",
                "provider": "Reuters",
            }
        ]

        mock_session = MagicMock()
        mock_session.get.return_value = self._make_page_response(rows, total_records=1)

        with patch("news_scraper.nasdaq.time.sleep"):
            result = fetch_stock_news_api_paginated(
                mock_session, "aapl", max_articles=100, page_size=1
            )

        assert result[0].ticker == "AAPL"

    def test_正常系_configがNoneのときデフォルトScraperConfigを使用する(self) -> None:
        """config=None のときデフォルト ScraperConfig で動作することを確認。"""
        from news_scraper.nasdaq import fetch_stock_news_api_paginated

        mock_session = MagicMock()
        mock_session.get.return_value = self._make_page_response([], total_records=0)

        with patch("news_scraper.nasdaq.time.sleep"):
            result = fetch_stock_news_api_paginated(
                mock_session, "AAPL", max_articles=100, page_size=20, config=None
            )

        assert result == []


class TestAsyncFetchStockNewsApiPaginated:
    """async_fetch_stock_news_api_paginated() のテスト."""

    def _make_page_response(
        self,
        rows: list[dict],
        total_records: int = 40,
    ) -> MagicMock:
        """ページレスポンスモックを生成するヘルパー."""
        mock_response = MagicMock()
        mock_response.raise_for_status = MagicMock()
        mock_response.json.return_value = {
            "data": {
                "rows": rows,
                "totalrecords": str(total_records),
            }
        }
        return mock_response

    @pytest.mark.asyncio
    async def test_正常系_複数ページの記事を取得できる(self) -> None:
        """2 ページ分の記事が正しく結合されることを確認（非同期版）。"""
        from news_scraper.nasdaq import async_fetch_stock_news_api_paginated

        page1_rows = [
            {
                "title": f"Article {i}",
                "url": f"https://nasdaq.com/article/{i}",
                "created": "2026-02-23T10:00:00+00:00",
                "provider": "Reuters",
            }
            for i in range(3)
        ]
        page2_rows = [
            {
                "title": f"Article {i + 3}",
                "url": f"https://nasdaq.com/article/{i + 3}",
                "created": "2026-02-22T10:00:00+00:00",
                "provider": "Reuters",
            }
            for i in range(3)
        ]

        mock_session = AsyncMock()
        mock_session.get.side_effect = [
            self._make_page_response(page1_rows, total_records=6),
            self._make_page_response(page2_rows, total_records=6),
        ]

        with patch("news_scraper.nasdaq.asyncio.sleep"):
            result = await async_fetch_stock_news_api_paginated(
                mock_session, "AAPL", max_articles=10, page_size=3
            )

        assert len(result) == 6
        assert all(isinstance(a, Article) for a in result)

    @pytest.mark.asyncio
    async def test_正常系_totalrecordsで自動終了する(self) -> None:
        """totalrecords に達したとき追加リクエストを送らないことを確認（非同期版）。"""
        from news_scraper.nasdaq import async_fetch_stock_news_api_paginated

        rows = [
            {
                "title": "Article",
                "url": "https://nasdaq.com/a",
                "created": "2026-02-23T10:00:00+00:00",
                "provider": "Reuters",
            }
        ]

        mock_session = AsyncMock()
        mock_session.get.return_value = self._make_page_response(rows, total_records=1)

        with patch("news_scraper.nasdaq.asyncio.sleep"):
            result = await async_fetch_stock_news_api_paginated(
                mock_session, "AAPL", max_articles=100, page_size=1
            )

        assert mock_session.get.call_count == 1
        assert len(result) == 1

    @pytest.mark.asyncio
    async def test_正常系_空rowsで早期終了する(self) -> None:
        """rows が空のとき追加リクエストを送らないことを確認（非同期版）。"""
        from news_scraper.nasdaq import async_fetch_stock_news_api_paginated

        mock_session = AsyncMock()
        mock_session.get.return_value = self._make_page_response([], total_records=10)

        with patch("news_scraper.nasdaq.asyncio.sleep"):
            result = await async_fetch_stock_news_api_paginated(
                mock_session, "AAPL", max_articles=100, page_size=20
            )

        assert mock_session.get.call_count == 1
        assert result == []

    @pytest.mark.asyncio
    async def test_正常系_start_dateより古い記事を除外する(self) -> None:
        """start_date より古い記事がフィルタリングされることを確認（非同期版）。"""
        from datetime import datetime

        from news_scraper.nasdaq import async_fetch_stock_news_api_paginated

        rows = [
            {
                "title": "New Article",
                "url": "https://nasdaq.com/new",
                "created": "2026-02-23T10:00:00+00:00",
                "provider": "Reuters",
            },
            {
                "title": "Old Article",
                "url": "https://nasdaq.com/old",
                "created": "2026-01-01T10:00:00+00:00",
                "provider": "Reuters",
            },
        ]

        mock_session = AsyncMock()
        mock_session.get.return_value = self._make_page_response(rows, total_records=2)

        with patch("news_scraper.nasdaq.asyncio.sleep"):
            result = await async_fetch_stock_news_api_paginated(
                mock_session,
                "AAPL",
                max_articles=100,
                page_size=20,
                start_date=datetime(2026, 2, 1),
            )

        assert len(result) == 1
        assert result[0].title == "New Article"

    @pytest.mark.asyncio
    async def test_正常系_end_dateより新しい記事を除外する(self) -> None:
        """end_date より新しい記事がフィルタリングされることを確認（非同期版）。"""
        from datetime import datetime

        from news_scraper.nasdaq import async_fetch_stock_news_api_paginated

        rows = [
            {
                "title": "Future Article",
                "url": "https://nasdaq.com/future",
                "created": "2026-03-01T10:00:00+00:00",
                "provider": "Reuters",
            },
            {
                "title": "Old Article",
                "url": "https://nasdaq.com/old",
                "created": "2026-01-15T10:00:00+00:00",
                "provider": "Reuters",
            },
        ]

        mock_session = AsyncMock()
        mock_session.get.return_value = self._make_page_response(rows, total_records=2)

        with patch("news_scraper.nasdaq.asyncio.sleep"):
            result = await async_fetch_stock_news_api_paginated(
                mock_session,
                "AAPL",
                max_articles=100,
                page_size=20,
                end_date=datetime(2026, 2, 28),
            )

        assert len(result) == 1
        assert result[0].title == "Old Article"

    @pytest.mark.asyncio
    async def test_正常系_全記事がstart_dateより古い場合に早期終了する(self) -> None:
        """全記事が start_date より古いとき次ページを取得しないことを確認（非同期版）。"""
        from datetime import datetime

        from news_scraper.nasdaq import async_fetch_stock_news_api_paginated

        rows = [
            {
                "title": "Very Old Article",
                "url": "https://nasdaq.com/very-old",
                "created": "2025-01-01T10:00:00+00:00",
                "provider": "Reuters",
            }
        ]

        mock_session = AsyncMock()
        mock_session.get.return_value = self._make_page_response(
            rows, total_records=100
        )

        with patch("news_scraper.nasdaq.asyncio.sleep"):
            result = await async_fetch_stock_news_api_paginated(
                mock_session,
                "AAPL",
                max_articles=100,
                page_size=1,
                start_date=datetime(2026, 1, 1),
            )

        assert mock_session.get.call_count == 1
        assert result == []

    @pytest.mark.asyncio
    async def test_正常系_APIエラー時に取得済みの部分結果を返す(self) -> None:
        """1 ページ目成功・2 ページ目エラーのとき 1 ページ目の記事を返すことを確認（非同期版）。"""
        from news_scraper.nasdaq import async_fetch_stock_news_api_paginated

        rows = [
            {
                "title": "Article 1",
                "url": "https://nasdaq.com/1",
                "created": "2026-02-23T10:00:00+00:00",
                "provider": "Reuters",
            }
        ]

        mock_session = AsyncMock()
        mock_session.get.side_effect = [
            self._make_page_response(rows, total_records=100),
            Exception("Network error"),
        ]

        with patch("news_scraper.nasdaq.asyncio.sleep"):
            result = await async_fetch_stock_news_api_paginated(
                mock_session, "AAPL", max_articles=100, page_size=1
            )

        assert len(result) == 1
        assert result[0].title == "Article 1"

    @pytest.mark.asyncio
    async def test_正常系_ページ間にasyncio_sleepでレートリミットする(self) -> None:
        """複数ページ取得時に asyncio.sleep が呼ばれることを確認。"""
        from news_scraper.nasdaq import async_fetch_stock_news_api_paginated

        rows = [
            {
                "title": "Article",
                "url": "https://nasdaq.com/a",
                "created": "2026-02-23T10:00:00+00:00",
                "provider": "Reuters",
            }
        ]

        mock_session = AsyncMock()
        mock_session.get.side_effect = [
            self._make_page_response(rows, total_records=3),
            self._make_page_response(rows, total_records=3),
            self._make_page_response(rows, total_records=3),
        ]

        config = ScraperConfig(delay=1.0, jitter=0.0)

        with patch("news_scraper.nasdaq.asyncio.sleep") as mock_sleep:
            await async_fetch_stock_news_api_paginated(
                mock_session, "AAPL", max_articles=3, page_size=1, config=config
            )

        assert mock_sleep.call_count >= 1

    @pytest.mark.asyncio
    async def test_異常系_不正なtickerでValueErrorを送出する(self) -> None:
        """不正な ticker シンボルで ValueError を送出することを確認（非同期版）。"""
        from news_scraper.nasdaq import async_fetch_stock_news_api_paginated

        mock_session = AsyncMock()

        with pytest.raises(ValueError, match="Invalid ticker symbol"):
            await async_fetch_stock_news_api_paginated(mock_session, "INVALID!!!!")

    @pytest.mark.asyncio
    async def test_正常系_tickerが大文字に正規化される(self) -> None:
        """小文字ティッカーを渡したとき Article.ticker が大文字になることを確認（非同期版）。"""
        from news_scraper.nasdaq import async_fetch_stock_news_api_paginated

        rows = [
            {
                "title": "Article",
                "url": "https://nasdaq.com/a",
                "created": "2026-02-23T10:00:00+00:00",
                "provider": "Reuters",
            }
        ]

        mock_session = AsyncMock()
        mock_session.get.return_value = self._make_page_response(rows, total_records=1)

        with patch("news_scraper.nasdaq.asyncio.sleep"):
            result = await async_fetch_stock_news_api_paginated(
                mock_session, "msft", max_articles=100, page_size=1
            )

        assert result[0].ticker == "MSFT"

    @pytest.mark.asyncio
    async def test_正常系_max_articlesで取得数を制限できる(self) -> None:
        """max_articles を超えたとき取得を停止することを確認（非同期版）。"""
        from news_scraper.nasdaq import async_fetch_stock_news_api_paginated

        rows = [
            {
                "title": f"Article {i}",
                "url": f"https://nasdaq.com/article/{i}",
                "created": "2026-02-23T10:00:00+00:00",
                "provider": "Reuters",
            }
            for i in range(5)
        ]

        mock_session = AsyncMock()
        mock_session.get.return_value = self._make_page_response(
            rows, total_records=100
        )

        with patch("news_scraper.nasdaq.asyncio.sleep"):
            result = await async_fetch_stock_news_api_paginated(
                mock_session, "AAPL", max_articles=5, page_size=5
            )

        assert mock_session.get.call_count == 1
        assert len(result) == 5


class TestFetchNewsArchivePlaywright:
    """fetch_news_archive_playwright() のテスト."""

    def _make_playwright_mocks(
        self,
        mock_page: MagicMock,
    ) -> tuple[MagicMock, MagicMock]:
        """sync_playwright と browser のモックを生成するヘルパー.

        実装の sync_playwright().start() パターンに対応したモックを返す。

        Returns
        -------
        tuple[MagicMock, MagicMock]
            (mock_sync_playwright_fn, mock_browser)
        """
        mock_browser = MagicMock()
        mock_browser.new_page.return_value = mock_page

        mock_pw_instance = MagicMock()
        mock_pw_instance.chromium.launch.return_value = mock_browser

        mock_sync_pw = MagicMock()
        mock_sync_pw.return_value.start.return_value = mock_pw_instance

        return mock_sync_pw, mock_browser

    def _make_mock_page(
        self,
        article_links: list[tuple[str, str]],
        has_load_more: bool = False,
    ) -> MagicMock:
        """ページモックを生成するヘルパー.

        Parameters
        ----------
        article_links : list[tuple[str, str]]
            (href, text) のリスト
        has_load_more : bool
            "Load More" ボタンが存在するか
        """
        page = MagicMock()

        def _make_link(href: str, text: str) -> MagicMock:
            link = MagicMock()
            link.get_attribute.return_value = href
            link.inner_text.return_value = text
            return link

        links = [_make_link(href, text) for href, text in article_links]
        page.query_selector_all.return_value = links

        if has_load_more:
            load_more_btn = MagicMock()
            page.query_selector.return_value = load_more_btn
        else:
            page.query_selector.return_value = None

        return page

    def test_正常系_記事一覧を取得できる(self) -> None:
        """ページに記事リンクが存在するとき記事リストを返すことを確認。"""
        from news_scraper.nasdaq import fetch_news_archive_playwright

        article_links = [
            ("https://www.nasdaq.com/articles/test-article-1", "Test Article One"),
            ("https://www.nasdaq.com/articles/test-article-2", "Another Article"),
        ]

        mock_page = self._make_mock_page(article_links, has_load_more=False)
        mock_sync_pw, mock_browser = self._make_playwright_mocks(mock_page)

        with patch("news_scraper.nasdaq.sync_playwright", mock_sync_pw):
            result = fetch_news_archive_playwright("Markets", max_articles=10)

        assert len(result) == 2
        assert result[0]["title"] == "Test Article One"
        assert result[0]["url"] == "https://www.nasdaq.com/articles/test-article-1"
        assert result[0]["source"] == "nasdaq"
        assert result[0]["category"] == "Markets"

    def test_正常系_出力形式がtitle_url_date_category_sourceを含む(self) -> None:
        """各記事 dict が必須キーを含むことを確認。"""
        from news_scraper.nasdaq import fetch_news_archive_playwright

        article_links = [
            ("https://www.nasdaq.com/articles/sample", "Sample Article Title"),
        ]
        mock_page = self._make_mock_page(article_links, has_load_more=False)
        mock_sync_pw, mock_browser = self._make_playwright_mocks(mock_page)

        with patch("news_scraper.nasdaq.sync_playwright", mock_sync_pw):
            result = fetch_news_archive_playwright("Markets", max_articles=10)

        assert len(result) == 1
        article = result[0]
        assert "title" in article
        assert "url" in article
        assert "date" in article
        assert "category" in article
        assert "source" in article
        assert article["source"] == "nasdaq"

    def test_正常系_browserNoneで新規ブラウザを作成し終了する(self) -> None:
        """browser=None のとき新規ブラウザを起動して終了することを確認。"""
        from news_scraper.nasdaq import fetch_news_archive_playwright

        mock_page = self._make_mock_page([], has_load_more=False)
        mock_sync_pw, mock_browser = self._make_playwright_mocks(mock_page)

        with patch("news_scraper.nasdaq.sync_playwright", mock_sync_pw):
            fetch_news_archive_playwright("Markets", max_articles=10, browser=None)

        mock_sync_pw.assert_called_once()
        mock_browser.close.assert_called_once()

    def test_正常系_browser指定で既存インスタンスを再利用する(self) -> None:
        """browser 引数を渡したとき新規ブラウザを起動しないことを確認。"""
        from news_scraper.nasdaq import fetch_news_archive_playwright

        mock_page = self._make_mock_page([], has_load_more=False)
        mock_browser = MagicMock()
        mock_browser.new_page.return_value = mock_page

        mock_sync_pw = MagicMock()

        with patch("news_scraper.nasdaq.sync_playwright", mock_sync_pw):
            fetch_news_archive_playwright(
                "Markets", max_articles=10, browser=mock_browser
            )
            mock_sync_pw.assert_not_called()

        mock_browser.close.assert_not_called()

    def test_正常系_LoadMoreボタンを繰り返しクリックできる(self) -> None:
        """Load More ボタンが存在するとき click() が呼ばれることを確認。"""
        from news_scraper.nasdaq import fetch_news_archive_playwright

        article_links = [
            ("https://www.nasdaq.com/articles/article-1", "Article One"),
        ]
        mock_page = MagicMock()

        def _make_link(href: str, text: str) -> MagicMock:
            link = MagicMock()
            link.get_attribute.return_value = href
            link.inner_text.return_value = text
            return link

        links = [_make_link(href, text) for href, text in article_links]
        mock_page.query_selector_all.return_value = links

        # 1回クリック後に None を返す（ボタンが消える）
        load_more = MagicMock()
        mock_page.query_selector.side_effect = [load_more, None]

        mock_sync_pw, mock_browser = self._make_playwright_mocks(mock_page)

        with patch("news_scraper.nasdaq.sync_playwright", mock_sync_pw):
            fetch_news_archive_playwright("Markets", max_articles=100)

        load_more.click.assert_called_once()

    def test_正常系_エラー時に空リストを返す(self) -> None:
        """ページ取得が例外を送出したとき空リストを返すことを確認。"""
        from news_scraper.nasdaq import fetch_news_archive_playwright

        mock_browser = MagicMock()
        mock_browser.new_page.side_effect = Exception("Browser error")

        result = fetch_news_archive_playwright(
            "Markets", max_articles=10, browser=mock_browser
        )

        assert result == []

    def test_正常系_max_articlesで取得数を制限できる(self) -> None:
        """max_articles を超えたとき取得を停止することを確認。"""
        from news_scraper.nasdaq import fetch_news_archive_playwright

        article_links = [
            (f"https://www.nasdaq.com/articles/article-{i}", f"Article {i}")
            for i in range(10)
        ]
        mock_page = self._make_mock_page(article_links, has_load_more=False)
        mock_sync_pw, mock_browser = self._make_playwright_mocks(mock_page)

        with patch("news_scraper.nasdaq.sync_playwright", mock_sync_pw):
            result = fetch_news_archive_playwright("Markets", max_articles=3)

        assert len(result) <= 3

    def test_正常系_URLにnasdaqドメイン以外のリンクを除外する(self) -> None:
        """NASDAQ ドメイン以外の URL を含む記事が除外されることを確認。"""
        from news_scraper.nasdaq import fetch_news_archive_playwright

        article_links = [
            ("https://www.nasdaq.com/articles/valid-article", "Valid Article"),
            ("https://external.com/news/external-link", "External Article"),
        ]
        mock_page = self._make_mock_page(article_links, has_load_more=False)
        mock_sync_pw, mock_browser = self._make_playwright_mocks(mock_page)

        with patch("news_scraper.nasdaq.sync_playwright", mock_sync_pw):
            result = fetch_news_archive_playwright("Markets", max_articles=10)

        urls = [a["url"] for a in result]
        assert all("nasdaq.com" in u for u in urls)


class TestAsyncFetchNewsArchivePlaywright:
    """async_fetch_news_archive_playwright() のテスト."""

    def _make_playwright_mocks(
        self,
        mock_page: AsyncMock,
    ) -> tuple[MagicMock, AsyncMock]:
        """async_playwright と browser のモックを生成するヘルパー.

        実装の async_playwright().start() パターン（await あり）に対応したモックを返す。

        Returns
        -------
        tuple[MagicMock, AsyncMock]
            (mock_async_playwright_fn, mock_browser)
        """
        mock_browser = AsyncMock()
        mock_browser.new_page.return_value = mock_page

        mock_pw_instance = AsyncMock()
        mock_pw_instance.chromium.launch.return_value = mock_browser

        mock_async_pw = MagicMock()
        # async_playwright().start() は await されるので AsyncMock にする
        mock_async_pw.return_value.start = AsyncMock(return_value=mock_pw_instance)

        return mock_async_pw, mock_browser

    def _make_mock_page(
        self,
        article_links: list[tuple[str, str]],
        has_load_more: bool = False,
    ) -> AsyncMock:
        """非同期ページモックを生成するヘルパー."""
        page = AsyncMock()

        def _make_link(href: str, text: str) -> AsyncMock:
            link = AsyncMock()
            link.get_attribute.return_value = href
            link.inner_text.return_value = text
            return link

        links = [_make_link(href, text) for href, text in article_links]
        page.query_selector_all.return_value = links

        if has_load_more:
            load_more_btn = AsyncMock()
            page.query_selector.return_value = load_more_btn
        else:
            page.query_selector.return_value = None

        return page

    @pytest.mark.asyncio
    async def test_正常系_記事一覧を取得できる(self) -> None:
        """ページに記事リンクが存在するとき記事リストを返すことを確認（非同期版）。"""
        from news_scraper.nasdaq import async_fetch_news_archive_playwright

        article_links = [
            ("https://www.nasdaq.com/articles/test-article-1", "Test Article One"),
            ("https://www.nasdaq.com/articles/test-article-2", "Another Article"),
        ]

        mock_page = self._make_mock_page(article_links, has_load_more=False)
        mock_async_pw, mock_browser = self._make_playwright_mocks(mock_page)

        with patch("news_scraper.nasdaq.async_playwright", mock_async_pw):
            result = await async_fetch_news_archive_playwright(
                "Markets", max_articles=10
            )

        assert len(result) == 2
        assert result[0]["title"] == "Test Article One"
        assert result[0]["url"] == "https://www.nasdaq.com/articles/test-article-1"
        assert result[0]["source"] == "nasdaq"
        assert result[0]["category"] == "Markets"

    @pytest.mark.asyncio
    async def test_正常系_出力形式がtitle_url_date_category_sourceを含む(
        self,
    ) -> None:
        """各記事 dict が必須キーを含むことを確認（非同期版）。"""
        from news_scraper.nasdaq import async_fetch_news_archive_playwright

        article_links = [
            ("https://www.nasdaq.com/articles/sample", "Sample Article Title"),
        ]
        mock_page = self._make_mock_page(article_links, has_load_more=False)
        mock_async_pw, mock_browser = self._make_playwright_mocks(mock_page)

        with patch("news_scraper.nasdaq.async_playwright", mock_async_pw):
            result = await async_fetch_news_archive_playwright(
                "Markets", max_articles=10
            )

        assert len(result) == 1
        article = result[0]
        assert "title" in article
        assert "url" in article
        assert "date" in article
        assert "category" in article
        assert "source" in article
        assert article["source"] == "nasdaq"

    @pytest.mark.asyncio
    async def test_正常系_browserNoneで新規ブラウザを作成し終了する(self) -> None:
        """browser=None のとき新規ブラウザを起動して終了することを確認（非同期版）。"""
        from news_scraper.nasdaq import async_fetch_news_archive_playwright

        mock_page = self._make_mock_page([], has_load_more=False)
        mock_async_pw, mock_browser = self._make_playwright_mocks(mock_page)

        with patch("news_scraper.nasdaq.async_playwright", mock_async_pw):
            await async_fetch_news_archive_playwright(
                "Markets", max_articles=10, browser=None
            )

        mock_async_pw.assert_called_once()
        mock_browser.close.assert_called_once()

    @pytest.mark.asyncio
    async def test_正常系_browser指定で既存インスタンスを再利用する(self) -> None:
        """browser 引数を渡したとき新規ブラウザを起動しないことを確認（非同期版）。"""
        from news_scraper.nasdaq import async_fetch_news_archive_playwright

        mock_page = self._make_mock_page([], has_load_more=False)
        mock_browser = AsyncMock()
        mock_browser.new_page.return_value = mock_page

        mock_async_pw = MagicMock()

        with patch("news_scraper.nasdaq.async_playwright", mock_async_pw):
            await async_fetch_news_archive_playwright(
                "Markets", max_articles=10, browser=mock_browser
            )
            mock_async_pw.assert_not_called()

        mock_browser.close.assert_not_called()

    @pytest.mark.asyncio
    async def test_正常系_LoadMoreボタンを繰り返しクリックできる(self) -> None:
        """Load More ボタンが存在するとき click() が呼ばれることを確認（非同期版）。"""
        from news_scraper.nasdaq import async_fetch_news_archive_playwright

        article_links = [
            ("https://www.nasdaq.com/articles/article-1", "Article One"),
        ]
        mock_page = AsyncMock()

        def _make_link(href: str, text: str) -> AsyncMock:
            link = AsyncMock()
            link.get_attribute.return_value = href
            link.inner_text.return_value = text
            return link

        links = [_make_link(href, text) for href, text in article_links]
        mock_page.query_selector_all.return_value = links

        load_more = AsyncMock()
        mock_page.query_selector.side_effect = [load_more, None]

        mock_async_pw, mock_browser = self._make_playwright_mocks(mock_page)

        with patch("news_scraper.nasdaq.async_playwright", mock_async_pw):
            await async_fetch_news_archive_playwright("Markets", max_articles=100)

        load_more.click.assert_called_once()

    @pytest.mark.asyncio
    async def test_正常系_エラー時に空リストを返す(self) -> None:
        """ページ取得が例外を送出したとき空リストを返すことを確認（非同期版）。"""
        from news_scraper.nasdaq import async_fetch_news_archive_playwright

        mock_browser = AsyncMock()
        mock_browser.new_page.side_effect = Exception("Browser error")

        result = await async_fetch_news_archive_playwright(
            "Markets", max_articles=10, browser=mock_browser
        )

        assert result == []

    @pytest.mark.asyncio
    async def test_正常系_max_articlesで取得数を制限できる(self) -> None:
        """max_articles を超えたとき取得を停止することを確認（非同期版）。"""
        from news_scraper.nasdaq import async_fetch_news_archive_playwright

        article_links = [
            (f"https://www.nasdaq.com/articles/article-{i}", f"Article {i}")
            for i in range(10)
        ]
        mock_page = self._make_mock_page(article_links, has_load_more=False)
        mock_async_pw, mock_browser = self._make_playwright_mocks(mock_page)

        with patch("news_scraper.nasdaq.async_playwright", mock_async_pw):
            result = await async_fetch_news_archive_playwright(
                "Markets", max_articles=3
            )

        assert len(result) <= 3
