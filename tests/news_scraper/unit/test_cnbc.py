"""cnbc.py の単体テスト.

対象モジュール: src/news_scraper/cnbc.py
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from news_scraper.types import Article, ScraperConfig


class TestFetchRssFeed:
    """fetch_rss_feed() のテスト."""

    def test_異常系_不明カテゴリでValueError(self) -> None:
        """不明なカテゴリを指定したとき ValueError が発生することを確認。"""
        from news_scraper.cnbc import fetch_rss_feed

        mock_session = MagicMock()

        with pytest.raises(ValueError, match="Unknown category"):
            fetch_rss_feed(mock_session, "unknown_category_xyz")

    def test_正常系_0件のフィードで空リストを返す(self) -> None:
        """RSS フィードにエントリが 0 件のとき空リストを返すことを確認。"""
        from news_scraper.cnbc import fetch_rss_feed

        mock_session = MagicMock()
        mock_response = MagicMock()
        mock_response.text = "<rss><channel></channel></rss>"
        mock_session.get.return_value = mock_response

        mock_feed = MagicMock()
        mock_feed.entries = []

        with patch("news_scraper.cnbc.feedparser.parse", return_value=mock_feed):
            result = fetch_rss_feed(mock_session, "top_news")

        assert result == []

    def test_正常系_複数エントリで記事リストを返す(self) -> None:
        """RSS エントリが複数あるとき Article のリストを返すことを確認。"""
        from news_scraper.cnbc import fetch_rss_feed

        mock_session = MagicMock()
        mock_response = MagicMock()
        mock_response.text = "<rss/>"
        mock_session.get.return_value = mock_response

        entry1 = MagicMock()
        entry1.get = lambda k, d="": {
            "title": "Article 1",
            "link": "https://cnbc.com/1",
            "published": "Mon, 01 Jan 2026 00:00:00 +0000",
            "summary": "Summary 1",
        }.get(k, d)

        entry2 = MagicMock()
        entry2.get = lambda k, d="": {
            "title": "Article 2",
            "link": "https://cnbc.com/2",
            "published": "Tue, 02 Jan 2026 00:00:00 +0000",
            "summary": "Summary 2",
        }.get(k, d)

        mock_feed = MagicMock()
        mock_feed.entries = [entry1, entry2]

        with patch("news_scraper.cnbc.feedparser.parse", return_value=mock_feed):
            result = fetch_rss_feed(mock_session, "economy")

        assert len(result) == 2
        assert all(isinstance(a, Article) for a in result)
        assert result[0].source == "cnbc"
        assert result[0].category == "economy"

    def test_正常系_カテゴリが記事に設定される(self) -> None:
        """category が Article.category に正しく設定されることを確認。"""
        from news_scraper.cnbc import fetch_rss_feed

        mock_session = MagicMock()
        mock_response = MagicMock()
        mock_response.text = "<rss/>"
        mock_session.get.return_value = mock_response

        entry = MagicMock()
        entry.get = lambda k, d="": {
            "title": "Tech News",
            "link": "https://cnbc.com/tech",
            "published": "",
            "summary": "",
        }.get(k, d)

        mock_feed = MagicMock()
        mock_feed.entries = [entry]

        with patch("news_scraper.cnbc.feedparser.parse", return_value=mock_feed):
            result = fetch_rss_feed(mock_session, "technology")

        assert result[0].category == "technology"


class TestFetchArticleContent:
    """fetch_article_content() のテスト."""

    def test_正常系_trafilaturaで本文取得成功(self) -> None:
        """trafilatura が本文テキストを返すとき記事情報 dict を返すことを確認。"""
        from news_scraper.cnbc import fetch_article_content

        mock_session = MagicMock()
        mock_response = MagicMock()
        mock_response.text = (
            "<html><body><h1>Test Title</h1><time datetime='2026-01-01T00:00:00'>...</time>"
            "<p>Article body text here.</p></body></html>"
        )
        mock_session.get.return_value = mock_response

        with patch(
            "news_scraper.cnbc.trafilatura.extract",
            return_value="Article body text here.",
        ):
            result = fetch_article_content(mock_session, "https://cnbc.com/article")

        assert result is not None
        assert result["url"] == "https://cnbc.com/article"
        assert result["content"] == "Article body text here."

    def test_正常系_trafilatura失敗後BeautifulSoupフォールバックで本文取得(
        self,
    ) -> None:
        """trafilatura が None を返し、BeautifulSoup の ArticleBody 要素が存在するとき本文を返すことを確認。"""
        from news_scraper.cnbc import fetch_article_content

        html = (
            "<html><body>"
            '<div data-module="ArticleBody"><p>Fallback content via BS4.</p></div>'
            "</body></html>"
        )
        mock_session = MagicMock()
        mock_response = MagicMock()
        mock_response.text = html
        mock_session.get.return_value = mock_response

        with patch("news_scraper.cnbc.trafilatura.extract", return_value=None):
            result = fetch_article_content(mock_session, "https://cnbc.com/article")

        assert result is not None
        assert "Fallback content via BS4." in result["content"]

    def test_正常系_trafilaturaもBeautifulSoupも失敗でNoneを返す(self) -> None:
        """trafilatura も BeautifulSoup フォールバックも失敗したとき None を返すことを確認。"""
        from news_scraper.cnbc import fetch_article_content

        html = "<html><body><p>No article body element here.</p></body></html>"
        mock_session = MagicMock()
        mock_response = MagicMock()
        mock_response.text = html
        mock_session.get.return_value = mock_response

        with patch("news_scraper.cnbc.trafilatura.extract", return_value=None):
            result = fetch_article_content(mock_session, "https://cnbc.com/article")

        assert result is None

    def test_異常系_HTTPエラーでNoneを返す(self) -> None:
        """HTTP リクエストが例外を送出したとき None を返すことを確認。"""
        from news_scraper.cnbc import fetch_article_content

        mock_session = MagicMock()
        mock_session.get.side_effect = Exception("Connection error")

        result = fetch_article_content(mock_session, "https://cnbc.com/article")

        assert result is None

    def test_正常系_メタデータが抽出される(self) -> None:
        """h1 タグと time タグからタイトルと公開日時が抽出されることを確認。"""
        from news_scraper.cnbc import fetch_article_content

        html = (
            "<html><body>"
            "<h1>My Article Title</h1>"
            "<time datetime='2026-02-23T12:00:00+00:00'>Feb 23</time>"
            "</body></html>"
        )
        mock_session = MagicMock()
        mock_response = MagicMock()
        mock_response.text = html
        mock_session.get.return_value = mock_response

        with patch(
            "news_scraper.cnbc.trafilatura.extract", return_value="Some content text"
        ):
            result = fetch_article_content(mock_session, "https://cnbc.com/article")

        assert result is not None
        assert result["title"] == "My Article Title"
        assert result["published"] == "2026-02-23T12:00:00+00:00"


class TestAsyncFetchArticleContent:
    """async_fetch_article_content() のテスト."""

    @pytest.mark.asyncio
    async def test_正常系_本文取得成功でdictを返す(self) -> None:
        """正常に HTML を取得しテキストを抽出したとき dict を返すことを確認。"""
        from news_scraper.cnbc import async_fetch_article_content

        html = (
            "<html><body><h1>Async Title</h1>"
            "<time datetime='2026-01-15T10:00:00+00:00'>Jan 15</time>"
            "</body></html>"
        )
        mock_session = AsyncMock()
        mock_response = AsyncMock()
        mock_response.text = html
        mock_session.get.return_value = mock_response

        with patch(
            "news_scraper.cnbc.asyncio.to_thread",
            side_effect=[
                "Async article body text.",  # trafilatura.extract
                ("Async Title", "2026-01-15T10:00:00+00:00"),  # _extract_metadata
            ],
        ):
            result = await async_fetch_article_content(
                mock_session, "https://cnbc.com/async"
            )

        assert result is not None
        assert result["url"] == "https://cnbc.com/async"
        assert result["content"] == "Async article body text."

    @pytest.mark.asyncio
    async def test_異常系_HTTPエラーでNoneを返す(self) -> None:
        """HTTP リクエストが例外を送出したとき None を返すことを確認。"""
        from news_scraper.cnbc import async_fetch_article_content

        mock_session = AsyncMock()
        mock_session.get.side_effect = Exception("Async connection error")

        result = await async_fetch_article_content(
            mock_session, "https://cnbc.com/async"
        )

        assert result is None

    @pytest.mark.asyncio
    async def test_正常系_trafilaturaとBS4両方失敗でNoneを返す(self) -> None:
        """trafilatura も BS4 フォールバックも None を返したとき None を返すことを確認。"""
        from news_scraper.cnbc import async_fetch_article_content

        html = "<html><body><p>No structured content.</p></body></html>"
        mock_session = AsyncMock()
        mock_response = AsyncMock()
        mock_response.text = html
        mock_session.get.return_value = mock_response

        with patch("news_scraper.cnbc.asyncio.to_thread", side_effect=[None, None]):
            result = await async_fetch_article_content(
                mock_session, "https://cnbc.com/async"
            )

        assert result is None
