"""unified.py の単体テスト.

collect_financial_news(), collect_financial_news_fast() の動作を検証する。
外部 HTTP リクエストはモックで差し替える。
"""

from __future__ import annotations

from typing import TYPE_CHECKING
from unittest.mock import AsyncMock, MagicMock, patch

if TYPE_CHECKING:
    from pathlib import Path

import pandas as pd
import pytest

from news_scraper.types import ScraperConfig
from news_scraper.unified import collect_financial_news, collect_financial_news_fast

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


def _make_articles_df(
    source: str = "cnbc",
    count: int = 3,
) -> pd.DataFrame:
    """テスト用記事 DataFrame を生成する."""
    records = [
        {
            "title": f"Test Article {i}",
            "url": f"https://example.com/{source}/article-{i}",
            "published": "2026-02-23T12:00:00+00:00",
            "summary": f"Summary {i}",
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
# collect_financial_news
# ---------------------------------------------------------------------------


class TestCollectFinancialNews:
    """collect_financial_news() の動作を検証する."""

    def test_正常系_デフォルト引数で記事を収集できる(
        self,
        tmp_path: Path,
    ) -> None:
        """sources=None の場合 cnbc + nasdaq が収集される."""
        df_cnbc = _make_articles_df("cnbc", 2)
        df_nasdaq = _make_articles_df("nasdaq", 3)

        with (
            patch("news_scraper.unified.cnbc.fetch_multiple_categories") as mock_cnbc,
            patch("news_scraper.unified.nasdaq.collect_nasdaq_news") as mock_nasdaq,
            patch("news_scraper.unified.create_session") as mock_session,
        ):
            mock_session.return_value = MagicMock()
            mock_cnbc.return_value = df_cnbc
            mock_nasdaq.return_value = df_nasdaq

            df = collect_financial_news()

        assert not df.empty
        assert len(df) == 5
        assert set(df["source"].unique()) == {"cnbc", "nasdaq"}

    def test_正常系_cnbcのみのソース指定(self) -> None:
        """sources=['cnbc'] の場合 CNBC のみ収集される."""
        df_cnbc = _make_articles_df("cnbc", 4)

        with (
            patch("news_scraper.unified.cnbc.fetch_multiple_categories") as mock_cnbc,
            patch("news_scraper.unified.nasdaq.collect_nasdaq_news") as mock_nasdaq,
            patch("news_scraper.unified.create_session") as mock_session,
        ):
            mock_session.return_value = MagicMock()
            mock_cnbc.return_value = df_cnbc

            df = collect_financial_news(sources=["cnbc"])

        assert len(df) == 4
        assert all(df["source"] == "cnbc")
        mock_nasdaq.assert_not_called()

    def test_正常系_URL重複が除去される(self) -> None:
        """同じ URL を持つ記事が重複除去される."""
        # CNBC と NASDAQ が同じ URL を返す
        df_cnbc = _make_articles_df("cnbc", 2)
        df_nasdaq = df_cnbc.copy()  # 同じ URL を含む

        with (
            patch("news_scraper.unified.cnbc.fetch_multiple_categories") as mock_cnbc,
            patch("news_scraper.unified.nasdaq.collect_nasdaq_news") as mock_nasdaq,
            patch("news_scraper.unified.create_session") as mock_session,
        ):
            mock_session.return_value = MagicMock()
            mock_cnbc.return_value = df_cnbc
            mock_nasdaq.return_value = df_nasdaq

            df = collect_financial_news()

        # 重複が除去されて元の件数と同じになる
        assert len(df) == len(df_cnbc)

    def test_正常系_出力ディレクトリに保存される(self, tmp_path: Path) -> None:
        """output_dir 指定時に JSON + Parquet が保存される."""
        df_cnbc = _make_articles_df("cnbc", 2)

        with (
            patch("news_scraper.unified.cnbc.fetch_multiple_categories") as mock_cnbc,
            patch("news_scraper.unified.nasdaq.collect_nasdaq_news") as mock_nasdaq,
            patch("news_scraper.unified.create_session") as mock_session,
        ):
            mock_session.return_value = MagicMock()
            mock_cnbc.return_value = df_cnbc
            mock_nasdaq.return_value = pd.DataFrame()

            collect_financial_news(output_dir=str(tmp_path))

        # JSON ファイルが生成されていることを確認
        json_files = list(tmp_path.glob("news_*.json"))
        parquet_files = list(tmp_path.glob("news_*.parquet"))
        assert len(json_files) == 1
        assert len(parquet_files) == 1

    def test_正常系_空のDataFrameが返される_ソースなし(self) -> None:
        """収集ソースが空リストの場合、空の DataFrame が返される."""
        df = collect_financial_news(sources=[])
        assert df.empty

    def test_正常系_全ソースが空の場合空のDataFrameを返す(self) -> None:
        """全ソースが空の DataFrame を返す場合、空の DataFrame が返される."""
        with (
            patch("news_scraper.unified.cnbc.fetch_multiple_categories") as mock_cnbc,
            patch("news_scraper.unified.nasdaq.collect_nasdaq_news") as mock_nasdaq,
            patch("news_scraper.unified.create_session") as mock_session,
        ):
            mock_session.return_value = MagicMock()
            mock_cnbc.return_value = pd.DataFrame()
            mock_nasdaq.return_value = pd.DataFrame()

            df = collect_financial_news()

        assert df.empty

    def test_正常系_カスタムcnbcカテゴリが渡される(self) -> None:
        """cnbc_categories 引数が fetch_multiple_categories に渡される."""
        custom_categories = ["economy", "technology"]
        df_cnbc = _make_articles_df("cnbc", 1)

        with (
            patch("news_scraper.unified.cnbc.fetch_multiple_categories") as mock_cnbc,
            patch("news_scraper.unified.nasdaq.collect_nasdaq_news") as mock_nasdaq,
            patch("news_scraper.unified.create_session") as mock_session,
        ):
            mock_session.return_value = MagicMock()
            mock_cnbc.return_value = df_cnbc
            mock_nasdaq.return_value = pd.DataFrame()

            collect_financial_news(
                sources=["cnbc"],
                cnbc_categories=custom_categories,
            )

        # fetch_multiple_categories が custom_categories を受け取る
        call_kwargs = mock_cnbc.call_args
        assert call_kwargs is not None
        # keyword 引数で categories が渡される
        assert call_kwargs.kwargs.get("categories") == custom_categories

    def test_異常系_CNBCが例外を発生させてもNASDAQは収集される(self) -> None:
        """CNBC 収集が失敗しても NASDAQ の収集は継続する."""
        df_nasdaq = _make_articles_df("nasdaq", 3)

        with (
            patch("news_scraper.unified.cnbc.fetch_multiple_categories") as mock_cnbc,
            patch("news_scraper.unified.nasdaq.collect_nasdaq_news") as mock_nasdaq,
            patch("news_scraper.unified.create_session") as mock_session,
        ):
            mock_session.return_value = MagicMock()
            mock_cnbc.side_effect = RuntimeError("CNBC fetch failed")
            mock_nasdaq.return_value = df_nasdaq

            df = collect_financial_news()

        assert len(df) == 3
        assert all(df["source"] == "nasdaq")

    def test_正常系_ScraperConfigが渡される(self) -> None:
        """カスタム ScraperConfig が使用される."""
        config = ScraperConfig(delay=2.0, timeout=60)
        df_cnbc = _make_articles_df("cnbc", 1)

        with (
            patch("news_scraper.unified.cnbc.fetch_multiple_categories") as mock_cnbc,
            patch("news_scraper.unified.nasdaq.collect_nasdaq_news") as mock_nasdaq,
            patch("news_scraper.unified.create_session") as mock_session,
        ):
            mock_session.return_value = MagicMock()
            mock_cnbc.return_value = df_cnbc
            mock_nasdaq.return_value = pd.DataFrame()

            collect_financial_news(sources=["cnbc"], config=config)

        # create_session が config の impersonate で呼ばれる
        mock_session.assert_called_once_with(
            impersonate=config.impersonate,
            proxy=config.proxy,
        )


# ---------------------------------------------------------------------------
# collect_financial_news_fast
# ---------------------------------------------------------------------------


class TestCollectFinancialNewsFast:
    """collect_financial_news_fast() の動作を検証する."""

    def test_正常系_asyncio_runが呼ばれる(self) -> None:
        """collect_financial_news_fast が asyncio.run() 経由で非同期版を呼ぶ."""
        df_mock = _make_articles_df("cnbc", 3)

        with patch("news_scraper.unified.asyncio") as mock_asyncio:
            mock_asyncio.run.return_value = df_mock

            result = collect_financial_news_fast(sources=["cnbc"])

        # asyncio.run が呼ばれていることを確認
        assert mock_asyncio.run.called
        assert len(result) == 3

    def test_正常系_引数が非同期版に渡される(self) -> None:
        """引数が async_collect_financial_news に正しく渡される."""
        df_mock = _make_articles_df("cnbc", 2)
        config = ScraperConfig(delay=0.5)
        tickers = ["AAPL", "MSFT"]

        with patch("news_scraper.unified.asyncio") as mock_asyncio:
            mock_asyncio.run.return_value = df_mock

            collect_financial_news_fast(
                sources=["cnbc"],
                tickers=tickers,
                config=config,
            )

        # asyncio.run が呼ばれたことを確認
        assert mock_asyncio.run.called
