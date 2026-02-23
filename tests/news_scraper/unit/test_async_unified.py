"""async_unified.py の単体テスト.

async_collect_financial_news() の動作を検証する。
外部 HTTP リクエストはモックで差し替える。
"""

from __future__ import annotations

import asyncio
from typing import TYPE_CHECKING
from unittest.mock import AsyncMock, MagicMock, patch

if TYPE_CHECKING:
    from pathlib import Path

import pandas as pd
import pytest

from news_scraper.async_unified import async_collect_financial_news
from news_scraper.types import ScraperConfig

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
# async_collect_financial_news
# ---------------------------------------------------------------------------


class TestAsyncCollectFinancialNews:
    """async_collect_financial_news() の動作を検証する."""

    def test_正常系_デフォルト引数で記事を収集できる(self) -> None:
        """sources=None の場合 cnbc + nasdaq が収集される."""
        df_cnbc = _make_articles_df("cnbc", 2)
        df_nasdaq = _make_articles_df("nasdaq", 3)

        async def _run() -> pd.DataFrame:
            with (
                patch(
                    "news_scraper.async_unified.cnbc.async_fetch_multiple_categories",
                    new_callable=AsyncMock,
                ) as mock_cnbc,
                patch(
                    "news_scraper.async_unified.nasdaq.async_collect_nasdaq_news",
                    new_callable=AsyncMock,
                ) as mock_nasdaq,
                patch(
                    "news_scraper.async_unified.create_async_session"
                ) as mock_session,
            ):
                mock_session.return_value = MagicMock()
                mock_cnbc.return_value = df_cnbc
                mock_nasdaq.return_value = df_nasdaq
                return await async_collect_financial_news()

        df = asyncio.run(_run())
        assert not df.empty
        assert len(df) == 5

    def test_正常系_URL重複が除去される(self) -> None:
        """同じ URL を持つ記事が重複除去される."""
        df_cnbc = _make_articles_df("cnbc", 3)
        # 同じ URL を含む DataFrame を NASDAQ として返す
        df_nasdaq = df_cnbc.copy()

        async def _run() -> pd.DataFrame:
            with (
                patch(
                    "news_scraper.async_unified.cnbc.async_fetch_multiple_categories",
                    new_callable=AsyncMock,
                ) as mock_cnbc,
                patch(
                    "news_scraper.async_unified.nasdaq.async_collect_nasdaq_news",
                    new_callable=AsyncMock,
                ) as mock_nasdaq,
                patch(
                    "news_scraper.async_unified.create_async_session"
                ) as mock_session,
            ):
                mock_session.return_value = MagicMock()
                mock_cnbc.return_value = df_cnbc
                mock_nasdaq.return_value = df_nasdaq
                return await async_collect_financial_news()

        df = asyncio.run(_run())
        # 重複除去後は元の件数になる
        assert len(df) == len(df_cnbc)

    def test_正常系_空の結果を返す_ソースなし(self) -> None:
        """収集ソースが空リストの場合、空の DataFrame が返される."""

        async def _run() -> pd.DataFrame:
            return await async_collect_financial_news(sources=[])

        df = asyncio.run(_run())
        assert df.empty

    def test_正常系_全ソースが空の場合空のDataFrameを返す(self) -> None:
        """全ソースが空の DataFrame を返す場合、空の DataFrame が返される."""

        async def _run() -> pd.DataFrame:
            with (
                patch(
                    "news_scraper.async_unified.cnbc.async_fetch_multiple_categories",
                    new_callable=AsyncMock,
                ) as mock_cnbc,
                patch(
                    "news_scraper.async_unified.nasdaq.async_collect_nasdaq_news",
                    new_callable=AsyncMock,
                ) as mock_nasdaq,
                patch(
                    "news_scraper.async_unified.create_async_session"
                ) as mock_session,
            ):
                mock_session.return_value = MagicMock()
                mock_cnbc.return_value = pd.DataFrame()
                mock_nasdaq.return_value = pd.DataFrame()
                return await async_collect_financial_news()

        df = asyncio.run(_run())
        assert df.empty

    def test_正常系_出力ディレクトリに保存される(self, tmp_path: Path) -> None:
        """output_dir 指定時に JSON + Parquet が保存される."""
        df_cnbc = _make_articles_df("cnbc", 2)

        async def _run() -> pd.DataFrame:
            with (
                patch(
                    "news_scraper.async_unified.cnbc.async_fetch_multiple_categories",
                    new_callable=AsyncMock,
                ) as mock_cnbc,
                patch(
                    "news_scraper.async_unified.nasdaq.async_collect_nasdaq_news",
                    new_callable=AsyncMock,
                ) as mock_nasdaq,
                patch(
                    "news_scraper.async_unified.create_async_session"
                ) as mock_session,
            ):
                mock_session.return_value = MagicMock()
                mock_cnbc.return_value = df_cnbc
                mock_nasdaq.return_value = pd.DataFrame()
                return await async_collect_financial_news(output_dir=str(tmp_path))

        asyncio.run(_run())

        json_files = list(tmp_path.glob("news_*.json"))
        parquet_files = list(tmp_path.glob("news_*.parquet"))
        assert len(json_files) == 1
        assert len(parquet_files) == 1

    def test_正常系_cnbcのみのソース指定(self) -> None:
        """sources=['cnbc'] の場合 CNBC のみ収集される."""
        df_cnbc = _make_articles_df("cnbc", 4)

        async def _run() -> tuple[pd.DataFrame, MagicMock]:
            with (
                patch(
                    "news_scraper.async_unified.cnbc.async_fetch_multiple_categories",
                    new_callable=AsyncMock,
                ) as mock_cnbc,
                patch(
                    "news_scraper.async_unified.nasdaq.async_collect_nasdaq_news",
                    new_callable=AsyncMock,
                ) as mock_nasdaq,
                patch(
                    "news_scraper.async_unified.create_async_session"
                ) as mock_session,
            ):
                mock_session.return_value = MagicMock()
                mock_cnbc.return_value = df_cnbc
                df = await async_collect_financial_news(sources=["cnbc"])
                return df, mock_nasdaq

        df, mock_nasdaq = asyncio.run(_run())
        assert len(df) == 4
        mock_nasdaq.assert_not_called()
