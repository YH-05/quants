"""investing_jp.py の単体テスト.

対象モジュール: src/news_scraper/investing_jp.py
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from news_scraper.types import INVESTING_JP_FEEDS, Article, ScraperConfig


class TestFetchRssFeed:
    """fetch_rss_feed() のテスト."""

    def test_異常系_不明カテゴリでValueError(self) -> None:
        """不明なカテゴリを指定したとき ValueError が発生することを確認。"""
        from news_scraper.investing_jp import fetch_rss_feed

        mock_session = MagicMock()

        with pytest.raises(ValueError, match="Unknown category"):
            fetch_rss_feed(mock_session, "unknown_category_xyz")

    def test_正常系_0件のフィードで空リストを返す(self) -> None:
        """RSS フィードにエントリが 0 件のとき空リストを返すことを確認。"""
        from news_scraper.investing_jp import fetch_rss_feed

        mock_session = MagicMock()
        mock_response = MagicMock()
        mock_response.text = "<rss><channel></channel></rss>"
        mock_session.get.return_value = mock_response

        mock_feed = MagicMock()
        mock_feed.entries = []

        with patch(
            "news_scraper.investing_jp.feedparser.parse", return_value=mock_feed
        ):
            result = fetch_rss_feed(mock_session, "forex")

        assert result == []

    def test_正常系_複数エントリで記事リストを返す(self) -> None:
        """RSS エントリが複数あるとき Article のリストを返すことを確認。"""
        from news_scraper.investing_jp import fetch_rss_feed

        mock_session = MagicMock()
        mock_response = MagicMock()
        mock_response.text = "<rss/>"
        mock_session.get.return_value = mock_response

        entry1 = MagicMock()
        entry1.get = lambda k, d="": {
            "title": "ドル円レート速報",
            "link": "https://jp.investing.com/news/forex-news/1",
            "published": "Mon, 01 Jan 2026 00:00:00 +0900",
            "summary": "為替要約1",
        }.get(k, d)

        entry2 = MagicMock()
        entry2.get = lambda k, d="": {
            "title": "金価格の動向",
            "link": "https://jp.investing.com/news/commodities-news/2",
            "published": "Tue, 02 Jan 2026 00:00:00 +0900",
            "summary": "商品要約2",
        }.get(k, d)

        mock_feed = MagicMock()
        mock_feed.entries = [entry1, entry2]

        with patch(
            "news_scraper.investing_jp.feedparser.parse", return_value=mock_feed
        ):
            result = fetch_rss_feed(mock_session, "forex")

        assert len(result) == 2
        assert all(isinstance(a, Article) for a in result)
        assert result[0].source == "investing_jp"
        assert result[0].category == "forex"

    def test_正常系_5カテゴリすべてが有効(self) -> None:
        """INVESTING_JP_FEEDS の全5カテゴリが有効であることを確認。"""
        from news_scraper.investing_jp import fetch_rss_feed

        expected_categories = {"forex", "commodities", "stocks", "economy", "bonds"}
        assert set(INVESTING_JP_FEEDS.keys()) == expected_categories

        mock_session = MagicMock()
        mock_response = MagicMock()
        mock_response.text = "<rss/>"
        mock_session.get.return_value = mock_response

        mock_feed = MagicMock()
        mock_feed.entries = []

        for category in INVESTING_JP_FEEDS:
            with patch(
                "news_scraper.investing_jp.feedparser.parse",
                return_value=mock_feed,
            ):
                result = fetch_rss_feed(mock_session, category)
            assert result == []

    def test_異常系_HTTPエラーで例外を送出(self) -> None:
        """HTTP リクエストが例外を送出したとき伝播されることを確認。"""
        from news_scraper.investing_jp import fetch_rss_feed

        mock_session = MagicMock()
        mock_session.get.side_effect = Exception("Connection error")

        with pytest.raises(Exception, match="Connection error"):
            fetch_rss_feed(mock_session, "forex")


class TestAsyncFetchRssFeed:
    """async_fetch_rss_feed() のテスト."""

    @pytest.mark.asyncio
    async def test_異常系_不明カテゴリでValueError(self) -> None:
        """不明なカテゴリを指定したとき ValueError が発生することを確認。"""
        from news_scraper.investing_jp import async_fetch_rss_feed

        mock_session = AsyncMock()

        with pytest.raises(ValueError, match="Unknown category"):
            await async_fetch_rss_feed(mock_session, "unknown_category_xyz")

    @pytest.mark.asyncio
    async def test_正常系_複数エントリで記事リストを返す(self) -> None:
        """非同期で RSS エントリが複数あるとき Article のリストを返すことを確認。"""
        from news_scraper.investing_jp import async_fetch_rss_feed

        mock_session = AsyncMock()
        mock_response = AsyncMock()
        mock_response.text = "<rss/>"
        mock_session.get.return_value = mock_response

        entry1 = MagicMock()
        entry1.get = lambda k, d="": {
            "title": "非同期為替記事",
            "link": "https://jp.investing.com/news/forex-news/10",
            "published": "Mon, 01 Jan 2026 00:00:00 +0900",
            "summary": "非同期要約",
        }.get(k, d)

        mock_feed = MagicMock()
        mock_feed.entries = [entry1]

        with patch(
            "news_scraper.investing_jp.feedparser.parse", return_value=mock_feed
        ):
            result = await async_fetch_rss_feed(mock_session, "forex")

        assert len(result) == 1
        assert result[0].source == "investing_jp"


class TestFetchMultipleCategories:
    """fetch_multiple_categories() のテスト."""

    def test_正常系_全カテゴリ取得(self) -> None:
        """categories=None で全5カテゴリを取得することを確認。"""
        from news_scraper.investing_jp import fetch_multiple_categories

        mock_session = MagicMock()

        with (
            patch("news_scraper.investing_jp.fetch_rss_feed") as mock_fetch,
            patch("news_scraper.investing_jp.time.sleep"),
        ):
            mock_fetch.return_value = [
                Article(
                    title="記事",
                    url="https://jp.investing.com/1",
                    source="investing_jp",
                    category="forex",
                )
            ]
            df = fetch_multiple_categories(mock_session)

        assert not df.empty
        assert mock_fetch.call_count == len(INVESTING_JP_FEEDS)

    def test_正常系_空カテゴリリストで空DataFrameを返す(self) -> None:
        """空のカテゴリリストを渡したとき空 DataFrame を返すことを確認。"""
        from news_scraper.investing_jp import fetch_multiple_categories

        mock_session = MagicMock()
        df = fetch_multiple_categories(mock_session, categories=[])

        assert df.empty

    def test_正常系_エラーカテゴリをスキップして残りを取得(self) -> None:
        """個別カテゴリの取得失敗をスキップし、成功分のみ返すことを確認。"""
        from news_scraper.investing_jp import fetch_multiple_categories

        mock_session = MagicMock()

        with (
            patch("news_scraper.investing_jp.fetch_rss_feed") as mock_fetch,
            patch("news_scraper.investing_jp.time.sleep"),
        ):
            mock_fetch.side_effect = [
                Exception("Feed error"),
                [
                    Article(
                        title="成功記事",
                        url="https://jp.investing.com/2",
                        source="investing_jp",
                        category="commodities",
                    )
                ],
            ]
            df = fetch_multiple_categories(
                mock_session, categories=["forex", "commodities"]
            )

        assert len(df) == 1


class TestAsyncFetchMultipleCategories:
    """async_fetch_multiple_categories() のテスト."""

    @pytest.mark.asyncio
    async def test_正常系_空カテゴリリストで空DataFrameを返す(self) -> None:
        """空のカテゴリリストを渡したとき空 DataFrame を返すことを確認。"""
        from news_scraper.investing_jp import async_fetch_multiple_categories

        mock_session = AsyncMock()
        df = await async_fetch_multiple_categories(mock_session, categories=[])

        assert df.empty

    @pytest.mark.asyncio
    async def test_正常系_指定カテゴリで記事を取得(self) -> None:
        """指定カテゴリの記事を非同期で取得することを確認。"""
        from news_scraper.investing_jp import async_fetch_multiple_categories

        mock_session = AsyncMock()

        with patch("news_scraper.investing_jp.async_fetch_rss_feed") as mock_fetch:
            mock_fetch.return_value = [
                Article(
                    title="非同期記事",
                    url="https://jp.investing.com/1",
                    source="investing_jp",
                    category="forex",
                )
            ]
            df = await async_fetch_multiple_categories(
                mock_session,
                categories=["forex"],
                config=ScraperConfig(delay=0.0, max_concurrency=1),
            )

        assert not df.empty
        assert len(df) == 1
