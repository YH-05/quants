"""embedding.extractor モジュールの単体テスト.

テストTODOリスト:
- [x] extract_contents: 空リストで空結果を返すこと
- [x] extract_contents: trafilatura 成功時に ExtractionResult.method == "trafilatura"
- [x] extract_contents: trafilatura 失敗時に playwright fallback が呼ばれること
- [x] extract_contents: 両方失敗時に ExtractionResult.method == "failed"
- [x] extract_contents: 結果が入力と同順・同サイズであること
- [x] extract_contents: playwright 未インストール時にフォールバックなしで "failed" を返すこと
- [x] _extract_with_trafilatura: 正常系で本文を返すこと
- [x] _extract_with_trafilatura: fetch_url が None を返す場合に None を返すこと
- [x] _extract_with_trafilatura: タイムアウト時に None を返すこと
- [x] _extract_with_playwright: async_playwright が None の場合に None を返すこと
"""

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from embedding.extractor import (
    _extract_single,
    _extract_with_playwright,
    _extract_with_trafilatura,
    extract_contents,
)
from embedding.types import ArticleRecord, PipelineConfig


@pytest.fixture
def sample_articles() -> list[ArticleRecord]:
    """テスト用記事リスト."""
    return [
        ArticleRecord(url="https://example.com/article/1", title="Article 1"),
        ArticleRecord(url="https://example.com/article/2", title="Article 2"),
    ]


@pytest.fixture
def pipeline_config_no_playwright() -> PipelineConfig:
    """playwright fallback を無効にした PipelineConfig."""
    return PipelineConfig(
        use_playwright_fallback=False,
        max_concurrency=2,
        delay=0.0,
        timeout=5,
    )


@pytest.fixture
def pipeline_config_with_playwright() -> PipelineConfig:
    """playwright fallback を有効にした PipelineConfig."""
    return PipelineConfig(
        use_playwright_fallback=True,
        max_concurrency=2,
        delay=0.0,
        timeout=5,
    )


class TestExtractContents:
    def test_正常系_空リストで空結果を返すこと(
        self, pipeline_config_no_playwright: PipelineConfig
    ) -> None:
        results = asyncio.run(extract_contents([], pipeline_config_no_playwright))
        assert results == []

    def test_正常系_trafilatura成功時にtrafilaturaメソッドを返すこと(
        self,
        sample_articles: list[ArticleRecord],
        pipeline_config_no_playwright: PipelineConfig,
    ) -> None:
        with (
            patch("embedding.extractor.trafilatura.fetch_url", return_value="<html>"),
            patch(
                "embedding.extractor.trafilatura.extract",
                return_value="Article content",
            ),
        ):
            results = asyncio.run(
                extract_contents(sample_articles, pipeline_config_no_playwright)
            )

        assert len(results) == 2
        for result in results:
            assert result.method == "trafilatura"
            assert result.content == "Article content"

    def test_正常系_結果が入力と同順同サイズであること(
        self,
        sample_articles: list[ArticleRecord],
        pipeline_config_no_playwright: PipelineConfig,
    ) -> None:
        with (
            patch("embedding.extractor.trafilatura.fetch_url", return_value=None),
        ):
            results = asyncio.run(
                extract_contents(sample_articles, pipeline_config_no_playwright)
            )

        assert len(results) == len(sample_articles)
        for article, result in zip(sample_articles, results, strict=False):
            assert result.url == article.url

    def test_正常系_trafilatura失敗でplaywrightフォールバックが呼ばれること(
        self,
        pipeline_config_with_playwright: PipelineConfig,
    ) -> None:
        articles = [ArticleRecord(url="https://example.com/js-page", title="JS Page")]

        async def mock_playwright_extract(url: str, timeout: int) -> str | None:
            return "Playwright content"

        with (
            patch("embedding.extractor.trafilatura.fetch_url", return_value=None),
            patch(
                "embedding.extractor._extract_with_playwright",
                side_effect=mock_playwright_extract,
            ),
        ):
            results = asyncio.run(
                extract_contents(articles, pipeline_config_with_playwright)
            )

        assert len(results) == 1
        assert results[0].method == "playwright"
        assert results[0].content == "Playwright content"

    def test_異常系_両方失敗時にfailedメソッドを返すこと(
        self,
        sample_articles: list[ArticleRecord],
        pipeline_config_no_playwright: PipelineConfig,
    ) -> None:
        with patch("embedding.extractor.trafilatura.fetch_url", return_value=None):
            results = asyncio.run(
                extract_contents(sample_articles, pipeline_config_no_playwright)
            )

        assert len(results) == 2
        for result in results:
            assert result.method == "failed"
            assert result.content == ""
            assert result.error != ""

    def test_異常系_playwright未インストール時にfailedを返すこと(
        self,
        pipeline_config_with_playwright: PipelineConfig,
    ) -> None:
        articles = [ArticleRecord(url="https://example.com/page", title="Page")]

        with (
            patch("embedding.extractor.trafilatura.fetch_url", return_value=None),
            patch("embedding.extractor.async_playwright", None),
        ):
            results = asyncio.run(
                extract_contents(articles, pipeline_config_with_playwright)
            )

        assert len(results) == 1
        assert results[0].method == "failed"


class TestExtractWithTrafilatura:
    def test_正常系_本文を返すこと(self) -> None:
        with (
            patch(
                "embedding.extractor.trafilatura.fetch_url", return_value="<html>body"
            ),
            patch(
                "embedding.extractor.trafilatura.extract",
                return_value="Extracted text",
            ),
        ):
            result = asyncio.run(
                _extract_with_trafilatura("https://example.com", timeout=10)
            )

        assert result == "Extracted text"

    def test_異常系_fetch_urlがNoneを返す場合にNoneを返すこと(self) -> None:
        with patch("embedding.extractor.trafilatura.fetch_url", return_value=None):
            result = asyncio.run(
                _extract_with_trafilatura("https://example.com", timeout=10)
            )

        assert result is None

    def test_異常系_extractがNoneを返す場合にNoneを返すこと(self) -> None:
        with (
            patch("embedding.extractor.trafilatura.fetch_url", return_value="<html>"),
            patch("embedding.extractor.trafilatura.extract", return_value=None),
        ):
            result = asyncio.run(
                _extract_with_trafilatura("https://example.com", timeout=10)
            )

        assert result is None

    def test_異常系_タイムアウト時にNoneを返すこと(self) -> None:
        async def slow_fetch() -> str:
            await asyncio.sleep(10)
            return "content"

        with patch(
            "embedding.extractor.trafilatura.fetch_url",
            side_effect=TimeoutError("timeout"),
        ):
            result = asyncio.run(
                _extract_with_trafilatura("https://example.com", timeout=1)
            )

        assert result is None

    def test_異常系_例外発生時にNoneを返すこと(self) -> None:
        with patch(
            "embedding.extractor.trafilatura.fetch_url",
            side_effect=Exception("Network error"),
        ):
            result = asyncio.run(
                _extract_with_trafilatura("https://example.com", timeout=10)
            )

        assert result is None


class TestExtractWithPlaywright:
    def test_異常系_async_playwrightがNoneの場合にNoneを返すこと(self) -> None:
        with patch("embedding.extractor.async_playwright", None):
            result = asyncio.run(
                _extract_with_playwright("https://example.com", timeout=10)
            )

        assert result is None

    def test_正常系_playwright成功時に本文を返すこと(self) -> None:
        mock_page = AsyncMock()
        mock_page.goto = AsyncMock()
        mock_page.content = AsyncMock(return_value="<html><body>Content</body></html>")

        mock_context = AsyncMock()
        mock_context.new_page = AsyncMock(return_value=mock_page)

        mock_browser = AsyncMock()
        mock_browser.new_context = AsyncMock(return_value=mock_context)
        mock_browser.close = AsyncMock()

        mock_p = MagicMock()
        mock_p.chromium.launch = AsyncMock(return_value=mock_browser)

        mock_playwright_cm = AsyncMock()
        mock_playwright_cm.__aenter__ = AsyncMock(return_value=mock_p)
        mock_playwright_cm.__aexit__ = AsyncMock(return_value=None)

        mock_async_playwright = MagicMock(return_value=mock_playwright_cm)

        with (
            patch("embedding.extractor.async_playwright", mock_async_playwright),
            patch(
                "embedding.extractor.trafilatura.extract",
                return_value="Playwright content",
            ),
        ):
            result = asyncio.run(
                _extract_with_playwright("https://example.com", timeout=10)
            )

        assert result == "Playwright content"

    def test_異常系_playwright例外時にNoneを返すこと(self) -> None:
        mock_playwright_cm = AsyncMock()
        mock_playwright_cm.__aenter__ = AsyncMock(
            side_effect=Exception("Browser error")
        )
        mock_playwright_cm.__aexit__ = AsyncMock(return_value=None)

        mock_async_playwright = MagicMock(return_value=mock_playwright_cm)

        with patch("embedding.extractor.async_playwright", mock_async_playwright):
            result = asyncio.run(
                _extract_with_playwright("https://example.com", timeout=10)
            )

        assert result is None


class TestExtractSingle:
    def test_正常系_trafilatura成功時にtrafilaturaメソッドを返すこと(self) -> None:
        with (
            patch("embedding.extractor.trafilatura.fetch_url", return_value="<html>"),
            patch(
                "embedding.extractor.trafilatura.extract",
                return_value="Article content",
            ),
        ):
            result = asyncio.run(
                _extract_single("https://example.com", timeout=10, use_playwright=False)
            )

        assert result.method == "trafilatura"
        assert result.content == "Article content"
        assert result.url == "https://example.com"
        assert result.error == ""

    def test_異常系_trafilatura失敗かつplaywrightなし時にfailedを返すこと(
        self,
    ) -> None:
        with patch("embedding.extractor.trafilatura.fetch_url", return_value=None):
            result = asyncio.run(
                _extract_single("https://example.com", timeout=10, use_playwright=False)
            )

        assert result.method == "failed"
        assert result.content == ""
        assert "failed" in result.error.lower()

    def test_正常系_extracted_atがISO8601形式であること(self) -> None:
        with patch("embedding.extractor.trafilatura.fetch_url", return_value=None):
            result = asyncio.run(
                _extract_single("https://example.com", timeout=10, use_playwright=False)
            )

        assert result.extracted_at != ""
        # ISO 8601 形式の基本確認
        assert "T" in result.extracted_at
