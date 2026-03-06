"""日本語ソース横断統合テスト.

全日本語ソース (toyokeizai, investing_jp, yahoo_jp, jpx, tdnet) を横断的にテストする。
外部 HTTP リクエストはモックで差し替える。
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pandas as pd
import pytest

from news_scraper.async_unified import async_collect_financial_news
from news_scraper.unified import collect_financial_news

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

JP_SOURCES = ["toyokeizai", "investing_jp", "yahoo_jp", "jpx", "tdnet"]


def _make_jp_articles_df(
    source: str,
    count: int = 2,
) -> pd.DataFrame:
    """テスト用日本語ソース記事 DataFrame を生成する."""
    records = [
        {
            "title": f"テスト記事 {source} {i}",
            "url": f"https://example.com/{source}/article-{i}",
            "published": "2026-03-06T12:00:00+09:00",
            "summary": f"概要 {source} {i}",
            "category": "economy",
            "source": source,
            "content": "",
            "ticker": "",
            "author": "",
            "article_id": f"{source}-{i}",
        }
        for i in range(count)
    ]
    return pd.DataFrame(records)


def _make_tdnet_articles(count: int = 2) -> list[MagicMock]:
    """TDnet 用のモック Article リストを生成する."""
    articles = []
    for i in range(count):
        article = MagicMock()
        article.to_dict.return_value = {
            "title": f"テスト記事 tdnet {i}",
            "url": f"https://example.com/tdnet/article-{i}",
            "published": "2026-03-06T12:00:00+09:00",
            "summary": f"概要 tdnet {i}",
            "category": "disclosure",
            "source": "tdnet",
            "content": "",
            "ticker": "7203",
            "author": "",
            "article_id": f"tdnet-{i}",
        }
        articles.append(article)
    return articles


# ---------------------------------------------------------------------------
# 同期版: 全日本語ソース横断テスト
# ---------------------------------------------------------------------------


@pytest.mark.integration
class TestJpIntegrationSync:
    """全日本語ソースを同期版 collect_financial_news で横断テストする."""

    def test_正常系_全日本語ソースを同時に収集できる(self) -> None:
        """5 ソース全てを指定して収集し、全結果が統合される."""
        dfs = {
            source: _make_jp_articles_df(source, 2)
            for source in JP_SOURCES
            if source != "tdnet"
        }

        with (
            patch(
                "news_scraper.unified.toyokeizai.fetch_multiple_categories"
            ) as mock_toyokeizai,
            patch(
                "news_scraper.unified.investing_jp.fetch_multiple_categories"
            ) as mock_investing,
            patch(
                "news_scraper.unified.yahoo_jp.fetch_multiple_categories"
            ) as mock_yahoo,
            patch("news_scraper.unified.jpx.fetch_multiple_categories") as mock_jpx,
            patch("news_scraper.unified.tdnet.fetch_disclosure_feed") as mock_tdnet,
            patch("news_scraper.unified.create_session") as mock_session,
        ):
            mock_session.return_value = MagicMock()
            mock_toyokeizai.return_value = dfs["toyokeizai"]
            mock_investing.return_value = dfs["investing_jp"]
            mock_yahoo.return_value = dfs["yahoo_jp"]
            mock_jpx.return_value = dfs["jpx"]
            mock_tdnet.return_value = _make_tdnet_articles(2)

            df = collect_financial_news(sources=JP_SOURCES)

        # 5 ソース x 2 記事 = 10 記事
        assert len(df) == 10
        assert set(df["source"].unique()) == set(JP_SOURCES)

    def test_正常系_一部ソースが失敗しても他は収集される(self) -> None:
        """一部のソースが例外を発生させても、残りのソースは正常に収集される."""
        df_yahoo = _make_jp_articles_df("yahoo_jp", 3)
        df_jpx = _make_jp_articles_df("jpx", 2)

        with (
            patch(
                "news_scraper.unified.toyokeizai.fetch_multiple_categories"
            ) as mock_toyokeizai,
            patch(
                "news_scraper.unified.investing_jp.fetch_multiple_categories"
            ) as mock_investing,
            patch(
                "news_scraper.unified.yahoo_jp.fetch_multiple_categories"
            ) as mock_yahoo,
            patch("news_scraper.unified.jpx.fetch_multiple_categories") as mock_jpx,
            patch("news_scraper.unified.tdnet.fetch_disclosure_feed") as mock_tdnet,
            patch("news_scraper.unified.create_session") as mock_session,
        ):
            mock_session.return_value = MagicMock()
            mock_toyokeizai.side_effect = RuntimeError("Toyokeizai failed")
            mock_investing.side_effect = RuntimeError("Investing failed")
            mock_yahoo.return_value = df_yahoo
            mock_jpx.return_value = df_jpx
            mock_tdnet.side_effect = RuntimeError("TDnet failed")

            df = collect_financial_news(sources=JP_SOURCES)

        assert len(df) == 5
        assert set(df["source"].unique()) == {"yahoo_jp", "jpx"}


# ---------------------------------------------------------------------------
# 非同期版: 全日本語ソース横断テスト
# ---------------------------------------------------------------------------


@pytest.mark.integration
class TestJpIntegrationAsync:
    """全日本語ソースを非同期版 async_collect_financial_news で横断テストする."""

    @pytest.mark.asyncio
    async def test_正常系_全日本語ソースを非同期で収集できる(self) -> None:
        """5 ソース全てを非同期で並列収集し、全結果が統合される."""
        dfs = {
            source: _make_jp_articles_df(source, 2)
            for source in JP_SOURCES
            if source != "tdnet"
        }

        with (
            patch(
                "news_scraper.async_unified.toyokeizai.async_fetch_multiple_categories",
                new_callable=AsyncMock,
            ) as mock_toyokeizai,
            patch(
                "news_scraper.async_unified.investing_jp.async_fetch_multiple_categories",
                new_callable=AsyncMock,
            ) as mock_investing,
            patch(
                "news_scraper.async_unified.yahoo_jp.async_fetch_multiple_categories",
                new_callable=AsyncMock,
            ) as mock_yahoo,
            patch(
                "news_scraper.async_unified.jpx.async_fetch_multiple_categories",
                new_callable=AsyncMock,
            ) as mock_jpx,
            patch(
                "news_scraper.async_unified.tdnet.async_fetch_disclosure_feed",
                new_callable=AsyncMock,
            ) as mock_tdnet,
            patch("news_scraper.async_unified.create_async_session") as mock_session,
        ):
            mock_session.return_value = MagicMock()
            mock_toyokeizai.return_value = dfs["toyokeizai"]
            mock_investing.return_value = dfs["investing_jp"]
            mock_yahoo.return_value = dfs["yahoo_jp"]
            mock_jpx.return_value = dfs["jpx"]
            mock_tdnet.return_value = _make_tdnet_articles(2)

            df = await async_collect_financial_news(sources=JP_SOURCES)

        # 5 ソース x 2 記事 = 10 記事
        assert len(df) == 10
        assert set(df["source"].unique()) == set(JP_SOURCES)
