"""yahoo_jp.py の単体テスト.

対象モジュール: src/news_scraper/yahoo_jp.py
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from news_scraper.types import YAHOO_JP_FEEDS, Article, ScraperConfig


class TestFetchRssFeed:
    """fetch_rss_feed() のテスト."""

    def test_異常系_不明カテゴリでValueError(self) -> None:
        """不明なカテゴリを指定したとき ValueError が発生することを確認。"""
        from news_scraper.yahoo_jp import fetch_rss_feed

        mock_session = MagicMock()

        with pytest.raises(ValueError, match="Unknown category"):
            fetch_rss_feed(mock_session, "unknown_category_xyz")

    def test_正常系_0件のフィードで空リストを返す(self) -> None:
        """RSS フィードにエントリが 0 件のとき空リストを返すことを確認。"""
        from news_scraper.yahoo_jp import fetch_rss_feed

        mock_session = MagicMock()
        mock_response = MagicMock()
        mock_response.text = "<rss><channel></channel></rss>"
        mock_session.get.return_value = mock_response

        mock_feed = MagicMock()
        mock_feed.entries = []

        with patch("news_scraper.yahoo_jp.feedparser.parse", return_value=mock_feed):
            result = fetch_rss_feed(mock_session, "business")

        assert result == []

    def test_正常系_複数エントリで記事リストを返す(self) -> None:
        """RSS エントリが複数あるとき Article のリストを返すことを確認。"""
        from news_scraper.yahoo_jp import fetch_rss_feed

        mock_session = MagicMock()
        mock_response = MagicMock()
        mock_response.text = "<rss/>"
        mock_session.get.return_value = mock_response

        entry1 = MagicMock()
        entry1.get = lambda k, d="": {
            "title": "Yahoo経済ニュース1",
            "link": "https://news.yahoo.co.jp/articles/1",
            "published": "Mon, 01 Jan 2026 00:00:00 +0900",
            "summary": "Yahoo要約1",
        }.get(k, d)

        entry2 = MagicMock()
        entry2.get = lambda k, d="": {
            "title": "Yahoo経済ニュース2",
            "link": "https://news.yahoo.co.jp/articles/2",
            "published": "Tue, 02 Jan 2026 00:00:00 +0900",
            "summary": "Yahoo要約2",
        }.get(k, d)

        mock_feed = MagicMock()
        mock_feed.entries = [entry1, entry2]

        with patch("news_scraper.yahoo_jp.feedparser.parse", return_value=mock_feed):
            result = fetch_rss_feed(mock_session, "business")

        assert len(result) == 2
        assert all(isinstance(a, Article) for a in result)
        assert result[0].source == "yahoo_jp"
        assert result[0].category == "business"

    def test_正常系_3カテゴリすべてが有効(self) -> None:
        """YAHOO_JP_FEEDS の全3カテゴリが有効であることを確認。"""
        from news_scraper.yahoo_jp import fetch_rss_feed

        expected_categories = {"business", "economy", "it"}
        assert set(YAHOO_JP_FEEDS.keys()) == expected_categories

        mock_session = MagicMock()
        mock_response = MagicMock()
        mock_response.text = "<rss/>"
        mock_session.get.return_value = mock_response

        mock_feed = MagicMock()
        mock_feed.entries = []

        for category in YAHOO_JP_FEEDS:
            with patch(
                "news_scraper.yahoo_jp.feedparser.parse",
                return_value=mock_feed,
            ):
                result = fetch_rss_feed(mock_session, category)
            assert result == []

    def test_正常系_カテゴリが記事に設定される(self) -> None:
        """category が Article.category に正しく設定されることを確認。"""
        from news_scraper.yahoo_jp import fetch_rss_feed

        mock_session = MagicMock()
        mock_response = MagicMock()
        mock_response.text = "<rss/>"
        mock_session.get.return_value = mock_response

        entry = MagicMock()
        entry.get = lambda k, d="": {
            "title": "IT記事",
            "link": "https://news.yahoo.co.jp/articles/3",
            "published": "",
            "summary": "",
        }.get(k, d)

        mock_feed = MagicMock()
        mock_feed.entries = [entry]

        with patch("news_scraper.yahoo_jp.feedparser.parse", return_value=mock_feed):
            result = fetch_rss_feed(mock_session, "it")

        assert result[0].category == "it"
        assert result[0].source == "yahoo_jp"

    def test_異常系_HTTPエラーで例外を送出(self) -> None:
        """HTTP リクエストが例外を送出したとき伝播されることを確認。"""
        from news_scraper.yahoo_jp import fetch_rss_feed

        mock_session = MagicMock()
        mock_session.get.side_effect = Exception("Connection error")

        with pytest.raises(Exception, match="Connection error"):
            fetch_rss_feed(mock_session, "business")


class TestAsyncFetchRssFeed:
    """async_fetch_rss_feed() のテスト."""

    @pytest.mark.asyncio
    async def test_異常系_不明カテゴリでValueError(self) -> None:
        """不明なカテゴリを指定したとき ValueError が発生することを確認。"""
        from news_scraper.yahoo_jp import async_fetch_rss_feed

        mock_session = AsyncMock()

        with pytest.raises(ValueError, match="Unknown category"):
            await async_fetch_rss_feed(mock_session, "unknown_category_xyz")

    @pytest.mark.asyncio
    async def test_正常系_複数エントリで記事リストを返す(self) -> None:
        """非同期で RSS エントリが複数あるとき Article のリストを返すことを確認。"""
        from news_scraper.yahoo_jp import async_fetch_rss_feed

        mock_session = AsyncMock()
        mock_response = AsyncMock()
        mock_response.text = "<rss/>"
        mock_session.get.return_value = mock_response

        entry1 = MagicMock()
        entry1.get = lambda k, d="": {
            "title": "非同期Yahoo記事",
            "link": "https://news.yahoo.co.jp/articles/10",
            "published": "Mon, 01 Jan 2026 00:00:00 +0900",
            "summary": "非同期要約",
        }.get(k, d)

        mock_feed = MagicMock()
        mock_feed.entries = [entry1]

        with patch("news_scraper.yahoo_jp.feedparser.parse", return_value=mock_feed):
            result = await async_fetch_rss_feed(mock_session, "business")

        assert len(result) == 1
        assert result[0].source == "yahoo_jp"


class TestFetchMultipleCategories:
    """fetch_multiple_categories() のテスト."""

    def test_正常系_全カテゴリ取得(self) -> None:
        """categories=None で全3カテゴリを取得することを確認。"""
        from news_scraper.yahoo_jp import fetch_multiple_categories

        mock_session = MagicMock()

        with (
            patch("news_scraper.yahoo_jp.fetch_rss_feed") as mock_fetch,
            patch("news_scraper.yahoo_jp.time.sleep"),
        ):
            mock_fetch.return_value = [
                Article(
                    title="記事",
                    url="https://news.yahoo.co.jp/1",
                    source="yahoo_jp",
                    category="business",
                )
            ]
            df = fetch_multiple_categories(mock_session)

        assert not df.empty
        assert mock_fetch.call_count == len(YAHOO_JP_FEEDS)

    def test_正常系_空カテゴリリストで空DataFrameを返す(self) -> None:
        """空のカテゴリリストを渡したとき空 DataFrame を返すことを確認。"""
        from news_scraper.yahoo_jp import fetch_multiple_categories

        mock_session = MagicMock()
        df = fetch_multiple_categories(mock_session, categories=[])

        assert df.empty

    def test_正常系_エラーカテゴリをスキップして残りを取得(self) -> None:
        """個別カテゴリの取得失敗をスキップし、成功分のみ返すことを確認。"""
        from news_scraper.yahoo_jp import fetch_multiple_categories

        mock_session = MagicMock()

        with (
            patch("news_scraper.yahoo_jp.fetch_rss_feed") as mock_fetch,
            patch("news_scraper.yahoo_jp.time.sleep"),
        ):
            mock_fetch.side_effect = [
                Exception("Feed error"),
                [
                    Article(
                        title="成功記事",
                        url="https://news.yahoo.co.jp/2",
                        source="yahoo_jp",
                        category="economy",
                    )
                ],
            ]
            df = fetch_multiple_categories(
                mock_session, categories=["business", "economy"]
            )

        assert len(df) == 1


class TestAsyncFetchMultipleCategories:
    """async_fetch_multiple_categories() のテスト."""

    @pytest.mark.asyncio
    async def test_正常系_空カテゴリリストで空DataFrameを返す(self) -> None:
        """空のカテゴリリストを渡したとき空 DataFrame を返すことを確認。"""
        from news_scraper.yahoo_jp import async_fetch_multiple_categories

        mock_session = AsyncMock()
        df = await async_fetch_multiple_categories(mock_session, categories=[])

        assert df.empty

    @pytest.mark.asyncio
    async def test_正常系_指定カテゴリで記事を取得(self) -> None:
        """指定カテゴリの記事を非同期で取得することを確認。"""
        from news_scraper.yahoo_jp import async_fetch_multiple_categories

        mock_session = AsyncMock()

        with patch("news_scraper.yahoo_jp.async_fetch_rss_feed") as mock_fetch:
            mock_fetch.return_value = [
                Article(
                    title="非同期記事",
                    url="https://news.yahoo.co.jp/1",
                    source="yahoo_jp",
                    category="business",
                )
            ]
            df = await async_fetch_multiple_categories(
                mock_session,
                categories=["business"],
                config=ScraperConfig(delay=0.0, max_concurrency=1),
            )

        assert not df.empty
        assert len(df) == 1
