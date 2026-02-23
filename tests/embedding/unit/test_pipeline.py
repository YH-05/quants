"""embedding.pipeline モジュールの単体テスト.

テストTODOリスト:
- [x] run_pipeline: 記事ゼロ時に全統計 0 を返すこと
- [x] run_pipeline: 全記事が ChromaDB 既存の場合に new_articles=0 を返すこと
- [x] run_pipeline: 新規記事があり抽出成功時に正しい統計を返すこと
- [x] run_pipeline: 全抽出失敗時に stored=0 を返すこと
- [x] run_pipeline: 4ステップを正しい順序で実行すること
- [x] _filter_new_articles: 既存 ID の記事をフィルタすること
- [x] _filter_new_articles: 全記事新規の場合に全件返すこと
- [x] _filter_successful: 成功した記事と失敗数を分離すること
- [x] _filter_successful: 全成功時に失敗数 0 を返すこと
- [x] _build_stats: 指定したキーと値で dict を構築すること
"""

import asyncio
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from embedding.chromadb_store import url_to_chromadb_id
from embedding.pipeline import (
    _build_stats,
    _filter_new_articles,
    _filter_successful,
    run_pipeline,
)
from embedding.types import ArticleRecord, ExtractionResult, PipelineConfig


@pytest.fixture
def sample_articles() -> list[ArticleRecord]:
    """テスト用記事リスト."""
    return [
        ArticleRecord(url="https://example.com/article/1", title="Article 1"),
        ArticleRecord(url="https://example.com/article/2", title="Article 2"),
        ArticleRecord(url="https://example.com/article/3", title="Article 3"),
    ]


@pytest.fixture
def test_pipeline_config(tmp_path: Path) -> PipelineConfig:
    """テスト用 PipelineConfig."""
    return PipelineConfig(
        news_dir=tmp_path / "news",
        chromadb_path=tmp_path / "chromadb",
        collection_name="test-collection",
        max_concurrency=2,
        delay=0.0,
        timeout=5,
    )


@pytest.fixture
def successful_extractions(
    sample_articles: list[ArticleRecord],
) -> list[ExtractionResult]:
    """全記事分の成功した抽出結果."""
    return [
        ExtractionResult(
            url=article.url,
            content=f"Content for {article.title}",
            method="trafilatura",
            extracted_at="2024-01-15T10:05:00+00:00",
        )
        for article in sample_articles
    ]


@pytest.fixture
def failed_extractions(
    sample_articles: list[ArticleRecord],
) -> list[ExtractionResult]:
    """全記事分の失敗した抽出結果."""
    return [
        ExtractionResult(
            url=article.url,
            content="",
            method="failed",
            extracted_at="2024-01-15T10:05:00+00:00",
            error="All extraction methods failed",
        )
        for article in sample_articles
    ]


class TestRunPipeline:
    def test_正常系_記事ゼロ時に全統計0を返すこと(
        self, test_pipeline_config: PipelineConfig
    ) -> None:
        test_pipeline_config.news_dir.mkdir(parents=True)

        with patch("embedding.pipeline.read_all_news_json", return_value=[]):
            stats = asyncio.run(run_pipeline(test_pipeline_config))

        assert stats["total_json_articles"] == 0
        assert stats["already_in_chromadb"] == 0
        assert stats["new_articles"] == 0
        assert stats["extraction_success"] == 0
        assert stats["extraction_failed"] == 0
        assert stats["stored"] == 0

    def test_正常系_全記事がChromaDB既存の場合にnew_articles0を返すこと(
        self,
        test_pipeline_config: PipelineConfig,
        sample_articles: list[ArticleRecord],
    ) -> None:
        test_pipeline_config.news_dir.mkdir(parents=True)
        existing_ids = {url_to_chromadb_id(a.url) for a in sample_articles}

        with (
            patch(
                "embedding.pipeline.read_all_news_json", return_value=sample_articles
            ),
            patch("embedding.pipeline.get_existing_ids", return_value=existing_ids),
        ):
            stats = asyncio.run(run_pipeline(test_pipeline_config))

        assert stats["total_json_articles"] == 3
        assert stats["already_in_chromadb"] == 3
        assert stats["new_articles"] == 0
        assert stats["stored"] == 0

    def test_正常系_新規記事があり抽出成功時に正しい統計を返すこと(
        self,
        test_pipeline_config: PipelineConfig,
        sample_articles: list[ArticleRecord],
        successful_extractions: list[ExtractionResult],
    ) -> None:
        test_pipeline_config.news_dir.mkdir(parents=True)

        async def mock_extract(
            articles: list[ArticleRecord], config: PipelineConfig
        ) -> list[ExtractionResult]:
            return successful_extractions

        with (
            patch(
                "embedding.pipeline.read_all_news_json", return_value=sample_articles
            ),
            patch("embedding.pipeline.get_existing_ids", return_value=set()),
            patch("embedding.pipeline.extract_contents", side_effect=mock_extract),
            patch("embedding.pipeline.store_articles", return_value=3),
        ):
            stats = asyncio.run(run_pipeline(test_pipeline_config))

        assert stats["total_json_articles"] == 3
        assert stats["already_in_chromadb"] == 0
        assert stats["new_articles"] == 3
        assert stats["extraction_success"] == 3
        assert stats["extraction_failed"] == 0
        assert stats["stored"] == 3

    def test_異常系_全抽出失敗時にstored0を返すこと(
        self,
        test_pipeline_config: PipelineConfig,
        sample_articles: list[ArticleRecord],
        failed_extractions: list[ExtractionResult],
    ) -> None:
        test_pipeline_config.news_dir.mkdir(parents=True)

        async def mock_extract(
            articles: list[ArticleRecord], config: PipelineConfig
        ) -> list[ExtractionResult]:
            return failed_extractions

        with (
            patch(
                "embedding.pipeline.read_all_news_json", return_value=sample_articles
            ),
            patch("embedding.pipeline.get_existing_ids", return_value=set()),
            patch("embedding.pipeline.extract_contents", side_effect=mock_extract),
        ):
            stats = asyncio.run(run_pipeline(test_pipeline_config))

        assert stats["extraction_success"] == 0
        assert stats["extraction_failed"] == 3
        assert stats["stored"] == 0

    def test_正常系_4ステップが正しい順序で実行されること(
        self,
        test_pipeline_config: PipelineConfig,
        sample_articles: list[ArticleRecord],
        successful_extractions: list[ExtractionResult],
    ) -> None:
        test_pipeline_config.news_dir.mkdir(parents=True)
        call_order: list[str] = []

        def mock_read(*args: object, **kwargs: object) -> list[ArticleRecord]:
            call_order.append("read")
            return sample_articles

        def mock_get_ids(*args: object, **kwargs: object) -> set[str]:
            call_order.append("get_ids")
            return set()

        async def mock_extract(
            articles: list[ArticleRecord], config: PipelineConfig
        ) -> list[ExtractionResult]:
            call_order.append("extract")
            return successful_extractions

        def mock_store(*args: object, **kwargs: object) -> int:
            call_order.append("store")
            return 3

        with (
            patch("embedding.pipeline.read_all_news_json", side_effect=mock_read),
            patch("embedding.pipeline.get_existing_ids", side_effect=mock_get_ids),
            patch("embedding.pipeline.extract_contents", side_effect=mock_extract),
            patch("embedding.pipeline.store_articles", side_effect=mock_store),
        ):
            asyncio.run(run_pipeline(test_pipeline_config))

        assert call_order == ["read", "get_ids", "extract", "store"]


class TestFilterNewArticles:
    def test_正常系_全記事新規の場合に全件返すこと(
        self, sample_articles: list[ArticleRecord]
    ) -> None:
        result = _filter_new_articles(sample_articles, set())
        assert len(result) == len(sample_articles)
        assert result == sample_articles

    def test_正常系_既存IDの記事をフィルタすること(
        self, sample_articles: list[ArticleRecord]
    ) -> None:
        # 最初の記事を既存とする
        existing_id = url_to_chromadb_id(sample_articles[0].url)
        result = _filter_new_articles(sample_articles, {existing_id})
        assert len(result) == 2
        assert sample_articles[0] not in result

    def test_エッジケース_空リストで空結果を返すこと(self) -> None:
        result = _filter_new_articles([], {"some-id"})
        assert result == []

    def test_エッジケース_全記事が既存の場合に空リストを返すこと(
        self, sample_articles: list[ArticleRecord]
    ) -> None:
        existing_ids = {url_to_chromadb_id(a.url) for a in sample_articles}
        result = _filter_new_articles(sample_articles, existing_ids)
        assert result == []


class TestFilterSuccessful:
    def test_正常系_全成功時に失敗数0を返すこと(
        self,
        sample_articles: list[ArticleRecord],
        successful_extractions: list[ExtractionResult],
    ) -> None:
        success_articles, success_results, failed_count = _filter_successful(
            sample_articles, successful_extractions
        )
        assert len(success_articles) == 3
        assert len(success_results) == 3
        assert failed_count == 0

    def test_正常系_成功と失敗を正しく分離すること(
        self,
        sample_articles: list[ArticleRecord],
    ) -> None:
        mixed_extractions = [
            ExtractionResult(
                url=sample_articles[0].url,
                content="Content",
                method="trafilatura",
                extracted_at="2024-01-15T10:05:00+00:00",
            ),
            ExtractionResult(
                url=sample_articles[1].url,
                content="",
                method="failed",
                extracted_at="2024-01-15T10:05:00+00:00",
                error="Failed",
            ),
            ExtractionResult(
                url=sample_articles[2].url,
                content="Content",
                method="playwright",
                extracted_at="2024-01-15T10:05:00+00:00",
            ),
        ]

        success_articles, success_results, failed_count = _filter_successful(
            sample_articles, mixed_extractions
        )
        assert len(success_articles) == 2
        assert len(success_results) == 2
        assert failed_count == 1
        assert success_articles[0].url == sample_articles[0].url
        assert success_articles[1].url == sample_articles[2].url

    def test_エッジケース_全失敗時に空リストと失敗数を返すこと(
        self,
        sample_articles: list[ArticleRecord],
        failed_extractions: list[ExtractionResult],
    ) -> None:
        success_articles, success_results, failed_count = _filter_successful(
            sample_articles, failed_extractions
        )
        assert success_articles == []
        assert success_results == []
        assert failed_count == 3


class TestBuildStats:
    def test_正常系_指定したキーと値でdictを構築すること(self) -> None:
        stats = _build_stats(
            total_json_articles=10,
            already_in_chromadb=3,
            new_articles=7,
            extraction_success=5,
            extraction_failed=2,
            stored=5,
        )
        assert stats == {
            "total_json_articles": 10,
            "already_in_chromadb": 3,
            "new_articles": 7,
            "extraction_success": 5,
            "extraction_failed": 2,
            "stored": 5,
        }

    def test_正常系_6つのキーを含むこと(self) -> None:
        stats = _build_stats(
            total_json_articles=0,
            already_in_chromadb=0,
            new_articles=0,
            extraction_success=0,
            extraction_failed=0,
            stored=0,
        )
        assert len(stats) == 6
        expected_keys = {
            "total_json_articles",
            "already_in_chromadb",
            "new_articles",
            "extraction_success",
            "extraction_failed",
            "stored",
        }
        assert set(stats.keys()) == expected_keys
