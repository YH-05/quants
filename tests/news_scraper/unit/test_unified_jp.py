"""unified.py 日本語ソース統合の単体テスト.

collect_financial_news() に日本語ソース (toyokeizai, investing_jp, yahoo_jp, jpx, tdnet)
を指定した場合の動作を検証する。外部 HTTP リクエストはモックで差し替える。
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pandas as pd
import pytest

from news_scraper.unified import _DEFAULT_SOURCES, collect_financial_news

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


def _make_jp_articles_df(
    source: str,
    count: int = 3,
) -> pd.DataFrame:
    """テスト用日本語ソース記事 DataFrame を生成する."""
    records = [
        {
            "title": f"テスト記事 {i}",
            "url": f"https://example.com/{source}/article-{i}",
            "published": "2026-03-06T12:00:00+09:00",
            "summary": f"概要 {i}",
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


# ---------------------------------------------------------------------------
# _DEFAULT_SOURCES 回帰テスト
# ---------------------------------------------------------------------------


class TestDefaultSources:
    """_DEFAULT_SOURCES が変更されていないことを確認する回帰テスト."""

    def test_正常系_デフォルトソースはcnbcとnasdaq(self) -> None:
        """_DEFAULT_SOURCES が ['cnbc', 'nasdaq'] のまま変更されていないこと."""
        assert _DEFAULT_SOURCES == ["cnbc", "nasdaq"]

    def test_正常系_日本語ソースはデフォルトに含まれない(self) -> None:
        """日本語ソースがデフォルトソースに含まれていないこと."""
        jp_sources = {"toyokeizai", "investing_jp", "yahoo_jp", "jpx", "tdnet"}
        assert not jp_sources.intersection(set(_DEFAULT_SOURCES))


# ---------------------------------------------------------------------------
# Toyokeizai 統合テスト
# ---------------------------------------------------------------------------


class TestCollectToyokeizai:
    """collect_financial_news(sources=['toyokeizai']) の動作を検証する."""

    def test_正常系_toyokeizaiソースで記事を収集できる(self) -> None:
        """sources=['toyokeizai'] で東洋経済の記事が収集される."""
        df_toyokeizai = _make_jp_articles_df("toyokeizai", 3)

        with (
            patch(
                "news_scraper.unified.toyokeizai.fetch_multiple_categories"
            ) as mock_toyokeizai,
            patch("news_scraper.unified.create_session") as mock_session,
        ):
            mock_session.return_value = MagicMock()
            mock_toyokeizai.return_value = df_toyokeizai

            df = collect_financial_news(sources=["toyokeizai"])

        assert not df.empty
        assert len(df) == 3
        assert all(df["source"] == "toyokeizai")
        mock_toyokeizai.assert_called_once()

    def test_異常系_toyokeizai例外でも他ソースは収集される(self) -> None:
        """toyokeizai 収集が失敗しても他ソースの収集は継続する."""
        df_yahoo = _make_jp_articles_df("yahoo_jp", 2)

        with (
            patch(
                "news_scraper.unified.toyokeizai.fetch_multiple_categories"
            ) as mock_toyokeizai,
            patch(
                "news_scraper.unified.yahoo_jp.fetch_multiple_categories"
            ) as mock_yahoo,
            patch("news_scraper.unified.create_session") as mock_session,
        ):
            mock_session.return_value = MagicMock()
            mock_toyokeizai.side_effect = RuntimeError("Toyokeizai fetch failed")
            mock_yahoo.return_value = df_yahoo

            df = collect_financial_news(sources=["toyokeizai", "yahoo_jp"])

        assert len(df) == 2
        assert all(df["source"] == "yahoo_jp")


# ---------------------------------------------------------------------------
# Investing.com JP 統合テスト
# ---------------------------------------------------------------------------


class TestCollectInvestingJp:
    """collect_financial_news(sources=['investing_jp']) の動作を検証する."""

    def test_正常系_investing_jpソースで記事を収集できる(self) -> None:
        """sources=['investing_jp'] で Investing.com JP の記事が収集される."""
        df_investing = _make_jp_articles_df("investing_jp", 4)

        with (
            patch(
                "news_scraper.unified.investing_jp.fetch_multiple_categories"
            ) as mock_investing,
            patch("news_scraper.unified.create_session") as mock_session,
        ):
            mock_session.return_value = MagicMock()
            mock_investing.return_value = df_investing

            df = collect_financial_news(sources=["investing_jp"])

        assert not df.empty
        assert len(df) == 4
        assert all(df["source"] == "investing_jp")


# ---------------------------------------------------------------------------
# Yahoo JP 統合テスト
# ---------------------------------------------------------------------------


class TestCollectYahooJp:
    """collect_financial_news(sources=['yahoo_jp']) の動作を検証する."""

    def test_正常系_yahoo_jpソースで記事を収集できる(self) -> None:
        """sources=['yahoo_jp'] で Yahoo JP の記事が収集される."""
        df_yahoo = _make_jp_articles_df("yahoo_jp", 5)

        with (
            patch(
                "news_scraper.unified.yahoo_jp.fetch_multiple_categories"
            ) as mock_yahoo,
            patch("news_scraper.unified.create_session") as mock_session,
        ):
            mock_session.return_value = MagicMock()
            mock_yahoo.return_value = df_yahoo

            df = collect_financial_news(sources=["yahoo_jp"])

        assert not df.empty
        assert len(df) == 5
        assert all(df["source"] == "yahoo_jp")


# ---------------------------------------------------------------------------
# JPX 統合テスト
# ---------------------------------------------------------------------------


class TestCollectJpx:
    """collect_financial_news(sources=['jpx']) の動作を検証する."""

    def test_正常系_jpxソースで記事を収集できる(self) -> None:
        """sources=['jpx'] で JPX の記事が収集される."""
        df_jpx = _make_jp_articles_df("jpx", 2)

        with (
            patch("news_scraper.unified.jpx.fetch_multiple_categories") as mock_jpx,
            patch("news_scraper.unified.create_session") as mock_session,
        ):
            mock_session.return_value = MagicMock()
            mock_jpx.return_value = df_jpx

            df = collect_financial_news(sources=["jpx"])

        assert not df.empty
        assert len(df) == 2
        assert all(df["source"] == "jpx")


# ---------------------------------------------------------------------------
# TDnet 統合テスト
# ---------------------------------------------------------------------------


class TestCollectTdnet:
    """collect_financial_news(sources=['tdnet']) の動作を検証する."""

    @staticmethod
    def _make_tdnet_articles(count: int = 3) -> list[MagicMock]:
        """TDnet 用のモック Article リストを生成する."""
        articles = []
        for i in range(count):
            article = MagicMock()
            article.to_dict.return_value = {
                "title": f"テスト記事 {i}",
                "url": f"https://example.com/tdnet/article-{i}",
                "published": "2026-03-06T12:00:00+09:00",
                "summary": f"概要 {i}",
                "category": "disclosure",
                "source": "tdnet",
                "content": "",
                "ticker": "7203",
                "author": "",
                "article_id": f"tdnet-{i}",
            }
            articles.append(article)
        return articles

    def test_正常系_tdnetソースで記事を収集できる(self) -> None:
        """sources=['tdnet'] で TDnet の記事が収集される."""
        mock_articles = self._make_tdnet_articles(3)

        with (
            patch("news_scraper.unified.tdnet.fetch_disclosure_feed") as mock_tdnet,
            patch("news_scraper.unified.create_session") as mock_session,
        ):
            mock_session.return_value = MagicMock()
            mock_tdnet.return_value = mock_articles

            df = collect_financial_news(sources=["tdnet"])

        assert not df.empty
        assert len(df) == 3
        assert all(df["source"] == "tdnet")

    def test_正常系_tdnet_codesパラメータがtdnetモジュールに伝搬される(self) -> None:
        """tdnet_codes パラメータが tdnet.fetch_disclosure_feed に渡される."""
        mock_articles = self._make_tdnet_articles(1)
        codes = ["7203", "6758"]

        with (
            patch("news_scraper.unified.tdnet.fetch_disclosure_feed") as mock_tdnet,
            patch("news_scraper.unified.create_session") as mock_session,
        ):
            mock_session.return_value = MagicMock()
            mock_tdnet.return_value = mock_articles

            collect_financial_news(sources=["tdnet"], tdnet_codes=codes)

        # fetch_disclosure_feed の呼び出し引数を検証
        mock_tdnet.assert_called_once()
        call_args = mock_tdnet.call_args
        # codes 引数が渡されていることを確認
        assert call_args.kwargs.get("codes") == codes

    def test_正常系_tdnet_codesがNoneの場合デフォルトコードが使用される(self) -> None:
        """tdnet_codes=None の場合、tdnet モジュールのデフォルトコードが使用される."""
        mock_articles = self._make_tdnet_articles(1)

        with (
            patch("news_scraper.unified.tdnet.fetch_disclosure_feed") as mock_tdnet,
            patch("news_scraper.unified.create_session") as mock_session,
        ):
            mock_session.return_value = MagicMock()
            mock_tdnet.return_value = mock_articles

            collect_financial_news(sources=["tdnet"])

        mock_tdnet.assert_called_once()
        call_args = mock_tdnet.call_args
        # codes が None で呼ばれる（tdnet モジュール内でデフォルトが適用される）
        assert call_args.kwargs.get("codes") is None


# ---------------------------------------------------------------------------
# 複数日本語ソース結合テスト
# ---------------------------------------------------------------------------


class TestCollectMultipleJpSources:
    """複数の日本語ソースを同時に指定した場合の動作を検証する."""

    def test_正常系_複数日本語ソースの結果が統合される(self) -> None:
        """toyokeizai + yahoo_jp の結果が正しく統合される."""
        df_toyokeizai = _make_jp_articles_df("toyokeizai", 2)
        df_yahoo = _make_jp_articles_df("yahoo_jp", 3)

        with (
            patch(
                "news_scraper.unified.toyokeizai.fetch_multiple_categories"
            ) as mock_toyokeizai,
            patch(
                "news_scraper.unified.yahoo_jp.fetch_multiple_categories"
            ) as mock_yahoo,
            patch("news_scraper.unified.create_session") as mock_session,
        ):
            mock_session.return_value = MagicMock()
            mock_toyokeizai.return_value = df_toyokeizai
            mock_yahoo.return_value = df_yahoo

            df = collect_financial_news(sources=["toyokeizai", "yahoo_jp"])

        assert len(df) == 5
        assert set(df["source"].unique()) == {"toyokeizai", "yahoo_jp"}

    def test_正常系_英語と日本語ソースの混合(self) -> None:
        """cnbc + toyokeizai のように英語と日本語ソースを混合できる."""
        df_cnbc = pd.DataFrame(
            [
                {
                    "title": "Test Article",
                    "url": "https://cnbc.com/article-0",
                    "published": "2026-03-06T12:00:00+00:00",
                    "summary": "Summary",
                    "category": "economy",
                    "source": "cnbc",
                    "content": "",
                    "ticker": "",
                    "author": "",
                    "article_id": "cnbc-0",
                }
            ]
        )
        df_toyokeizai = _make_jp_articles_df("toyokeizai", 2)

        with (
            patch("news_scraper.unified.cnbc.fetch_multiple_categories") as mock_cnbc,
            patch(
                "news_scraper.unified.toyokeizai.fetch_multiple_categories"
            ) as mock_toyokeizai,
            patch("news_scraper.unified.create_session") as mock_session,
        ):
            mock_session.return_value = MagicMock()
            mock_cnbc.return_value = df_cnbc
            mock_toyokeizai.return_value = df_toyokeizai

            df = collect_financial_news(sources=["cnbc", "toyokeizai"])

        assert len(df) == 3
        assert set(df["source"].unique()) == {"cnbc", "toyokeizai"}
