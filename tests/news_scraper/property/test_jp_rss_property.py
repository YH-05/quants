"""日本語 RSS スクレイパー共通プロパティテスト.

3ソース（東洋経済・Investing.com・Yahoo!ニュース）の共通不変条件をテストする。
feedparser entry -> Article 変換の不変条件:
- Article.source が各ソース固定値
- URL が文字列型
- タイトルが非空（entry にタイトルがある場合）
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

from hypothesis import given, settings
from hypothesis import strategies as st

from news_scraper.types import (
    INVESTING_JP_FEEDS,
    TOYOKEIZAI_FEEDS,
    YAHOO_JP_FEEDS,
    Article,
)


def _make_feed_entry(title: str, link: str, published: str, summary: str) -> MagicMock:
    """テスト用の feedparser entry モックを作成する."""
    entry = MagicMock()
    entry.get = lambda k, d="": {
        "title": title,
        "link": link,
        "published": published,
        "summary": summary,
    }.get(k, d)
    return entry


def _make_mock_session_and_feed(
    entries: list[MagicMock],
) -> tuple[MagicMock, MagicMock]:
    """モック session と feed を作成する."""
    mock_session = MagicMock()
    mock_response = MagicMock()
    mock_response.text = "<rss/>"
    mock_session.get.return_value = mock_response

    mock_feed = MagicMock()
    mock_feed.entries = entries
    return mock_session, mock_feed


# 日本語テキストを含む文字列戦略（サロゲートペア Cs を除外）
jp_text_strategy = st.text(
    alphabet=st.characters(
        categories=("L", "N", "P", "Z"),
    ),
    min_size=1,
    max_size=200,
)

url_strategy = st.from_regex(r"https?://[a-z0-9.]+/[a-z0-9/-]+", fullmatch=True)


class TestToyokeizaiProperty:
    """東洋経済オンラインスクレイパーのプロパティテスト."""

    @given(
        title=jp_text_strategy,
        link=url_strategy,
        published=st.text(min_size=0, max_size=50),
        summary=st.text(min_size=0, max_size=500),
    )
    @settings(max_examples=30)
    def test_プロパティ_Article_sourceが固定値toyokeizai(
        self, title: str, link: str, published: str, summary: str
    ) -> None:
        """任意の entry データから変換された Article.source が "toyokeizai" であること。"""
        from news_scraper.toyokeizai import fetch_rss_feed

        entry = _make_feed_entry(title, link, published, summary)
        mock_session, mock_feed = _make_mock_session_and_feed([entry])

        with patch("news_scraper.toyokeizai.feedparser.parse", return_value=mock_feed):
            result = fetch_rss_feed(mock_session, "all")

        assert len(result) == 1
        assert result[0].source == "toyokeizai"
        assert isinstance(result[0].url, str)
        assert isinstance(result[0].title, str)
        assert len(result[0].title) > 0

    @given(
        titles=st.lists(jp_text_strategy, min_size=0, max_size=10),
    )
    @settings(max_examples=20)
    def test_プロパティ_エントリ数と記事数が一致(self, titles: list[str]) -> None:
        """feedparser エントリ数と返却 Article 数が常に一致すること。"""
        from news_scraper.toyokeizai import fetch_rss_feed

        entries = [
            _make_feed_entry(t, f"https://toyokeizai.net/{i}", "", "")
            for i, t in enumerate(titles)
        ]
        mock_session, mock_feed = _make_mock_session_and_feed(entries)

        with patch("news_scraper.toyokeizai.feedparser.parse", return_value=mock_feed):
            result = fetch_rss_feed(mock_session, "all")

        assert len(result) == len(titles)


class TestInvestingJpProperty:
    """Investing.com 日本版スクレイパーのプロパティテスト."""

    @given(
        title=jp_text_strategy,
        link=url_strategy,
        published=st.text(min_size=0, max_size=50),
        summary=st.text(min_size=0, max_size=500),
        category=st.sampled_from(list(INVESTING_JP_FEEDS.keys())),
    )
    @settings(max_examples=30)
    def test_プロパティ_Article_sourceが固定値investing_jp(
        self,
        title: str,
        link: str,
        published: str,
        summary: str,
        category: str,
    ) -> None:
        """任意の entry データから変換された Article.source が "investing_jp" であること。"""
        from news_scraper.investing_jp import fetch_rss_feed

        entry = _make_feed_entry(title, link, published, summary)
        mock_session, mock_feed = _make_mock_session_and_feed([entry])

        with patch(
            "news_scraper.investing_jp.feedparser.parse",
            return_value=mock_feed,
        ):
            result = fetch_rss_feed(mock_session, category)

        assert len(result) == 1
        assert result[0].source == "investing_jp"
        assert isinstance(result[0].url, str)
        assert isinstance(result[0].title, str)
        assert len(result[0].title) > 0

    @given(
        titles=st.lists(jp_text_strategy, min_size=0, max_size=10),
    )
    @settings(max_examples=20)
    def test_プロパティ_エントリ数と記事数が一致(self, titles: list[str]) -> None:
        """feedparser エントリ数と返却 Article 数が常に一致すること。"""
        from news_scraper.investing_jp import fetch_rss_feed

        entries = [
            _make_feed_entry(t, f"https://jp.investing.com/{i}", "", "")
            for i, t in enumerate(titles)
        ]
        mock_session, mock_feed = _make_mock_session_and_feed(entries)

        with patch(
            "news_scraper.investing_jp.feedparser.parse",
            return_value=mock_feed,
        ):
            result = fetch_rss_feed(mock_session, "forex")

        assert len(result) == len(titles)


class TestYahooJpProperty:
    """Yahoo!ニュース経済スクレイパーのプロパティテスト."""

    @given(
        title=jp_text_strategy,
        link=url_strategy,
        published=st.text(min_size=0, max_size=50),
        summary=st.text(min_size=0, max_size=500),
        category=st.sampled_from(list(YAHOO_JP_FEEDS.keys())),
    )
    @settings(max_examples=30)
    def test_プロパティ_Article_sourceが固定値yahoo_jp(
        self,
        title: str,
        link: str,
        published: str,
        summary: str,
        category: str,
    ) -> None:
        """任意の entry データから変換された Article.source が "yahoo_jp" であること。"""
        from news_scraper.yahoo_jp import fetch_rss_feed

        entry = _make_feed_entry(title, link, published, summary)
        mock_session, mock_feed = _make_mock_session_and_feed([entry])

        with patch("news_scraper.yahoo_jp.feedparser.parse", return_value=mock_feed):
            result = fetch_rss_feed(mock_session, category)

        assert len(result) == 1
        assert result[0].source == "yahoo_jp"
        assert isinstance(result[0].url, str)
        assert isinstance(result[0].title, str)
        assert len(result[0].title) > 0

    @given(
        titles=st.lists(jp_text_strategy, min_size=0, max_size=10),
    )
    @settings(max_examples=20)
    def test_プロパティ_エントリ数と記事数が一致(self, titles: list[str]) -> None:
        """feedparser エントリ数と返却 Article 数が常に一致すること。"""
        from news_scraper.yahoo_jp import fetch_rss_feed

        entries = [
            _make_feed_entry(t, f"https://news.yahoo.co.jp/{i}", "", "")
            for i, t in enumerate(titles)
        ]
        mock_session, mock_feed = _make_mock_session_and_feed(entries)

        with patch("news_scraper.yahoo_jp.feedparser.parse", return_value=mock_feed):
            result = fetch_rss_feed(mock_session, "business")

        assert len(result) == len(titles)
