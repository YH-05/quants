"""Unit tests for the NewsWorkflowOrchestrator class.

Tests for the orchestrator that integrates:
Collector -> Extractor -> Summarizer -> Publisher pipeline.

Following TDD approach: Red -> Green -> Refactor
"""

from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from news.config.models import NewsWorkflowConfig, PublishingConfig, SummarizationConfig
from news.models import (
    ArticleSource,
    CollectedArticle,
    ExtractedArticle,
    ExtractionStatus,
    FailureRecord,
    FeedError,
    PublicationStatus,
    PublishedArticle,
    SourceType,
    StructuredSummary,
    SummarizationStatus,
    SummarizedArticle,
    WorkflowResult,
)

# Fixtures


@pytest.fixture
def sample_config() -> NewsWorkflowConfig:
    """Create a sample NewsWorkflowConfig for testing.

    Uses per_article format to test legacy per-article publishing pipeline.
    For per_category tests, see test_orchestrator_integration.py.
    """
    return NewsWorkflowConfig(
        version="1.0",
        status_mapping={"market": "index", "tech": "ai", "finance": "finance"},
        github_status_ids={
            "index": "test-index-id",
            "ai": "test-ai-id",
            "finance": "test-finance-id",
        },
        rss={"presets_file": "data/config/rss-presets.json"},  # type: ignore[arg-type]
        summarization=SummarizationConfig(
            prompt_template="Summarize this article in Japanese: {body}",
        ),
        github={  # type: ignore[arg-type]
            "project_number": 15,
            "project_id": "PVT_test",
            "status_field_id": "PVTSSF_test",
            "published_date_field_id": "PVTF_test",
            "repository": "YH-05/quants",
        },
        output={"result_dir": "data/exports"},  # type: ignore[arg-type]
        publishing=PublishingConfig(format="per_article"),
    )


@pytest.fixture
def sample_source_market() -> ArticleSource:
    """Create a sample ArticleSource with market category."""
    return ArticleSource(
        source_type=SourceType.RSS,
        source_name="CNBC Markets",
        category="market",
    )


@pytest.fixture
def sample_source_tech() -> ArticleSource:
    """Create a sample ArticleSource with tech category."""
    return ArticleSource(
        source_type=SourceType.RSS,
        source_name="Tech News",
        category="tech",
    )


@pytest.fixture
def sample_collected_article(sample_source_market: ArticleSource) -> CollectedArticle:
    """Create a sample CollectedArticle."""
    return CollectedArticle(
        url="https://www.cnbc.com/article/123",  # type: ignore[arg-type]
        title="Market Update: S&P 500 Rallies",
        published=datetime(2025, 1, 15, 10, 0, 0, tzinfo=timezone.utc),
        raw_summary="Stocks rose on positive earnings reports.",
        source=sample_source_market,
        collected_at=datetime(2025, 1, 15, 12, 0, 0, tzinfo=timezone.utc),
    )


@pytest.fixture
def sample_collected_articles(
    sample_source_market: ArticleSource,
    sample_source_tech: ArticleSource,
) -> list[CollectedArticle]:
    """Create multiple sample CollectedArticles."""
    return [
        CollectedArticle(
            url="https://www.cnbc.com/article/1",  # type: ignore[arg-type]
            title="Market Update 1",
            published=datetime(2025, 1, 15, 10, 0, 0, tzinfo=timezone.utc),
            raw_summary="Summary 1",
            source=sample_source_market,
            collected_at=datetime(2025, 1, 15, 12, 0, 0, tzinfo=timezone.utc),
        ),
        CollectedArticle(
            url="https://www.cnbc.com/article/2",  # type: ignore[arg-type]
            title="Market Update 2",
            published=datetime(2025, 1, 15, 11, 0, 0, tzinfo=timezone.utc),
            raw_summary="Summary 2",
            source=sample_source_market,
            collected_at=datetime(2025, 1, 15, 12, 0, 0, tzinfo=timezone.utc),
        ),
        CollectedArticle(
            url="https://tech.example.com/article/3",  # type: ignore[arg-type]
            title="Tech Update 3",
            published=datetime(2025, 1, 15, 12, 0, 0, tzinfo=timezone.utc),
            raw_summary="Summary 3",
            source=sample_source_tech,
            collected_at=datetime(2025, 1, 15, 12, 0, 0, tzinfo=timezone.utc),
        ),
    ]


@pytest.fixture
def sample_extracted_article(
    sample_collected_article: CollectedArticle,
) -> ExtractedArticle:
    """Create a sample ExtractedArticle with success status."""
    return ExtractedArticle(
        collected=sample_collected_article,
        body_text="Full article content about the S&P 500 rally...",
        extraction_status=ExtractionStatus.SUCCESS,
        extraction_method="trafilatura",
    )


@pytest.fixture
def sample_summary() -> StructuredSummary:
    """Create a sample StructuredSummary."""
    return StructuredSummary(
        overview="S&P 500が上昇した。",
        key_points=["ポイント1", "ポイント2"],
        market_impact="市場への影響",
        related_info="関連情報",
    )


@pytest.fixture
def sample_summarized_article(
    sample_extracted_article: ExtractedArticle,
    sample_summary: StructuredSummary,
) -> SummarizedArticle:
    """Create a sample SummarizedArticle with success status."""
    return SummarizedArticle(
        extracted=sample_extracted_article,
        summary=sample_summary,
        summarization_status=SummarizationStatus.SUCCESS,
    )


@pytest.fixture
def sample_published_article(
    sample_summarized_article: SummarizedArticle,
) -> PublishedArticle:
    """Create a sample PublishedArticle with success status."""
    return PublishedArticle(
        summarized=sample_summarized_article,
        issue_number=123,
        issue_url="https://github.com/YH-05/quants/issues/123",
        publication_status=PublicationStatus.SUCCESS,
    )


# Tests


class TestOrchestratorInit:
    """Tests for NewsWorkflowOrchestrator initialization."""

    def test_正常系_コンストラクタで設定を受け取る(
        self, sample_config: NewsWorkflowConfig
    ) -> None:
        """Orchestrator should accept NewsWorkflowConfig in constructor."""
        from news.orchestrator import NewsWorkflowOrchestrator

        orchestrator = NewsWorkflowOrchestrator(config=sample_config)

        assert orchestrator._config is sample_config

    def test_正常系_各コンポーネントが初期化される(
        self, sample_config: NewsWorkflowConfig
    ) -> None:
        """Orchestrator should initialize all pipeline components."""
        from news.orchestrator import NewsWorkflowOrchestrator

        with (
            patch("news.orchestrator.RSSCollector") as mock_collector,
            patch("news.orchestrator.TrafilaturaExtractor") as mock_extractor,
            patch("news.orchestrator.Summarizer") as mock_summarizer,
            patch("news.orchestrator.Publisher") as mock_publisher,
        ):
            orchestrator = NewsWorkflowOrchestrator(config=sample_config)

            mock_collector.assert_called_once_with(sample_config)
            mock_extractor.assert_called_once_with(
                min_body_length=sample_config.extraction.min_body_length,
                max_retries=sample_config.extraction.max_retries,
                timeout_seconds=sample_config.extraction.timeout_seconds,
            )
            mock_summarizer.assert_called_once_with(sample_config)
            mock_publisher.assert_called_once_with(sample_config)


class TestOrchestratorRun:
    """Tests for run() method."""

    def test_正常系_runメソッドが存在する(
        self, sample_config: NewsWorkflowConfig
    ) -> None:
        """Orchestrator should have a run() method."""
        from news.orchestrator import NewsWorkflowOrchestrator

        with (
            patch("news.orchestrator.RSSCollector"),
            patch("news.orchestrator.TrafilaturaExtractor"),
            patch("news.orchestrator.Summarizer"),
            patch("news.orchestrator.Publisher"),
        ):
            orchestrator = NewsWorkflowOrchestrator(config=sample_config)

            assert hasattr(orchestrator, "run")
            assert callable(orchestrator.run)

    @pytest.mark.asyncio
    async def test_正常系_runがWorkflowResultを返す(
        self, sample_config: NewsWorkflowConfig
    ) -> None:
        """run() should return WorkflowResult."""
        from news.orchestrator import NewsWorkflowOrchestrator

        with (
            patch("news.orchestrator.RSSCollector") as mock_collector_cls,
            patch("news.orchestrator.TrafilaturaExtractor") as mock_extractor_cls,
            patch("news.orchestrator.Summarizer") as mock_summarizer_cls,
            patch("news.orchestrator.Publisher") as mock_publisher_cls,
        ):
            # Setup mocks
            mock_collector = MagicMock()
            mock_collector.collect = AsyncMock(return_value=[])
            mock_collector_cls.return_value = mock_collector

            mock_extractor = MagicMock()
            mock_extractor.extract = AsyncMock(return_value=[])
            mock_extractor_cls.return_value = mock_extractor

            mock_summarizer = MagicMock()
            mock_summarizer.summarize_batch = AsyncMock(return_value=[])
            mock_summarizer_cls.return_value = mock_summarizer

            mock_publisher = MagicMock()
            mock_publisher.publish_batch = AsyncMock(return_value=[])
            mock_publisher.get_existing_urls = AsyncMock(return_value=set())
            mock_publisher.is_duplicate_url = MagicMock(return_value=False)
            mock_publisher_cls.return_value = mock_publisher

            orchestrator = NewsWorkflowOrchestrator(config=sample_config)
            result = await orchestrator.run()

            assert isinstance(result, WorkflowResult)

    @pytest.mark.asyncio
    async def test_正常系_runが各ステージを順番に実行(
        self,
        sample_config: NewsWorkflowConfig,
        sample_collected_article: CollectedArticle,
        sample_extracted_article: ExtractedArticle,
        sample_summarized_article: SummarizedArticle,
        sample_published_article: PublishedArticle,
    ) -> None:
        """run() should execute all pipeline stages in order."""
        from news.orchestrator import NewsWorkflowOrchestrator

        with (
            patch("news.orchestrator.RSSCollector") as mock_collector_cls,
            patch("news.orchestrator.TrafilaturaExtractor") as mock_extractor_cls,
            patch("news.orchestrator.Summarizer") as mock_summarizer_cls,
            patch("news.orchestrator.Publisher") as mock_publisher_cls,
        ):
            # Setup mocks
            mock_collector = MagicMock()
            mock_collector.collect = AsyncMock(return_value=[sample_collected_article])
            mock_collector_cls.return_value = mock_collector

            mock_extractor = MagicMock()
            mock_extractor.extract = AsyncMock(return_value=sample_extracted_article)
            mock_extractor_cls.return_value = mock_extractor

            mock_summarizer = MagicMock()
            mock_summarizer.summarize_batch = AsyncMock(
                return_value=[sample_summarized_article]
            )
            mock_summarizer_cls.return_value = mock_summarizer

            mock_publisher = MagicMock()
            mock_publisher.publish_batch = AsyncMock(
                return_value=[sample_published_article]
            )
            mock_publisher.get_existing_urls = AsyncMock(return_value=set())
            mock_publisher.is_duplicate_url = MagicMock(return_value=False)
            mock_publisher_cls.return_value = mock_publisher

            orchestrator = NewsWorkflowOrchestrator(config=sample_config)
            result = await orchestrator.run()

            # Verify each stage was called
            mock_collector.collect.assert_called_once()
            mock_extractor.extract.assert_called()
            mock_summarizer.summarize_batch.assert_called_once()
            mock_publisher.publish_batch.assert_called_once()

            # Verify result counts
            assert result.total_collected == 1
            assert result.total_extracted == 1
            assert result.total_summarized == 1
            assert result.total_published == 1


class TestOrchestratorStatusFilter:
    """Tests for status filtering in run()."""

    @pytest.mark.asyncio
    async def test_正常系_statusesでフィルタリング(
        self,
        sample_config: NewsWorkflowConfig,
        sample_collected_articles: list[CollectedArticle],
    ) -> None:
        """run() should filter articles by statuses parameter."""
        from news.orchestrator import NewsWorkflowOrchestrator

        with (
            patch("news.orchestrator.RSSCollector") as mock_collector_cls,
            patch("news.orchestrator.TrafilaturaExtractor") as mock_extractor_cls,
            patch("news.orchestrator.Summarizer") as mock_summarizer_cls,
            patch("news.orchestrator.Publisher") as mock_publisher_cls,
        ):
            # Setup mocks
            mock_collector = MagicMock()
            mock_collector.collect = AsyncMock(return_value=sample_collected_articles)
            mock_collector_cls.return_value = mock_collector

            mock_extractor = MagicMock()
            mock_extractor.extract = AsyncMock(
                side_effect=lambda a: ExtractedArticle(
                    collected=a,
                    body_text="Content",
                    extraction_status=ExtractionStatus.SUCCESS,
                    extraction_method="trafilatura",
                )
            )
            mock_extractor_cls.return_value = mock_extractor

            mock_summarizer = MagicMock()
            mock_summarizer.summarize_batch = AsyncMock(return_value=[])
            mock_summarizer_cls.return_value = mock_summarizer

            mock_publisher = MagicMock()
            mock_publisher.publish_batch = AsyncMock(return_value=[])
            mock_publisher.get_existing_urls = AsyncMock(return_value=set())
            mock_publisher.is_duplicate_url = MagicMock(return_value=False)
            mock_publisher_cls.return_value = mock_publisher

            orchestrator = NewsWorkflowOrchestrator(config=sample_config)
            # Filter to only "index" status (market category maps to index)
            result = await orchestrator.run(statuses=["index"])

            # Should only process market articles (2 of 3)
            assert mock_extractor.extract.call_count == 2


class TestOrchestratorMaxArticles:
    """Tests for max_articles limit in run()."""

    @pytest.mark.asyncio
    async def test_正常系_max_articlesで件数制限(
        self,
        sample_config: NewsWorkflowConfig,
        sample_collected_articles: list[CollectedArticle],
    ) -> None:
        """run() should limit articles to max_articles parameter."""
        from news.orchestrator import NewsWorkflowOrchestrator

        with (
            patch("news.orchestrator.RSSCollector") as mock_collector_cls,
            patch("news.orchestrator.TrafilaturaExtractor") as mock_extractor_cls,
            patch("news.orchestrator.Summarizer") as mock_summarizer_cls,
            patch("news.orchestrator.Publisher") as mock_publisher_cls,
        ):
            # Setup mocks
            mock_collector = MagicMock()
            mock_collector.collect = AsyncMock(return_value=sample_collected_articles)
            mock_collector_cls.return_value = mock_collector

            mock_extractor = MagicMock()
            mock_extractor.extract = AsyncMock(
                side_effect=lambda a: ExtractedArticle(
                    collected=a,
                    body_text="Content",
                    extraction_status=ExtractionStatus.SUCCESS,
                    extraction_method="trafilatura",
                )
            )
            mock_extractor_cls.return_value = mock_extractor

            mock_summarizer = MagicMock()
            mock_summarizer.summarize_batch = AsyncMock(return_value=[])
            mock_summarizer_cls.return_value = mock_summarizer

            mock_publisher = MagicMock()
            mock_publisher.publish_batch = AsyncMock(return_value=[])
            mock_publisher.get_existing_urls = AsyncMock(return_value=set())
            mock_publisher.is_duplicate_url = MagicMock(return_value=False)
            mock_publisher_cls.return_value = mock_publisher

            orchestrator = NewsWorkflowOrchestrator(config=sample_config)
            # Limit to 2 articles
            result = await orchestrator.run(max_articles=2)

            # Should only process 2 articles
            assert mock_extractor.extract.call_count == 2


class TestOrchestratorDryRun:
    """Tests for dry_run mode in run()."""

    @pytest.mark.asyncio
    async def test_正常系_dry_runがPublisherに渡される(
        self,
        sample_config: NewsWorkflowConfig,
        sample_collected_article: CollectedArticle,
        sample_extracted_article: ExtractedArticle,
        sample_summarized_article: SummarizedArticle,
    ) -> None:
        """run() should pass dry_run parameter to publisher."""
        from news.orchestrator import NewsWorkflowOrchestrator

        with (
            patch("news.orchestrator.RSSCollector") as mock_collector_cls,
            patch("news.orchestrator.TrafilaturaExtractor") as mock_extractor_cls,
            patch("news.orchestrator.Summarizer") as mock_summarizer_cls,
            patch("news.orchestrator.Publisher") as mock_publisher_cls,
        ):
            # Setup mocks
            mock_collector = MagicMock()
            mock_collector.collect = AsyncMock(return_value=[sample_collected_article])
            mock_collector_cls.return_value = mock_collector

            mock_extractor = MagicMock()
            mock_extractor.extract = AsyncMock(return_value=sample_extracted_article)
            mock_extractor_cls.return_value = mock_extractor

            mock_summarizer = MagicMock()
            mock_summarizer.summarize_batch = AsyncMock(
                return_value=[sample_summarized_article]
            )
            mock_summarizer_cls.return_value = mock_summarizer

            mock_publisher = MagicMock()
            mock_publisher.publish_batch = AsyncMock(return_value=[])
            mock_publisher.get_existing_urls = AsyncMock(return_value=set())
            mock_publisher.is_duplicate_url = MagicMock(return_value=False)
            mock_publisher_cls.return_value = mock_publisher

            orchestrator = NewsWorkflowOrchestrator(config=sample_config)
            await orchestrator.run(dry_run=True)

            # Verify dry_run was passed to publisher
            mock_publisher.publish_batch.assert_called_once()
            call_kwargs = mock_publisher.publish_batch.call_args.kwargs
            assert call_kwargs.get("dry_run") is True


class TestOrchestratorSuccessFiltering:
    """Tests for filtering only successful articles at each stage."""

    @pytest.mark.asyncio
    async def test_正常系_抽出失敗の記事は要約に渡されない(
        self,
        sample_config: NewsWorkflowConfig,
        sample_source_market: ArticleSource,
    ) -> None:
        """Only successfully extracted articles should be passed to summarizer."""
        from news.orchestrator import NewsWorkflowOrchestrator

        # Create articles
        collected1 = CollectedArticle(
            url="https://example.com/1",  # type: ignore[arg-type]
            title="Article 1",
            source=sample_source_market,
            collected_at=datetime.now(tz=timezone.utc),
        )
        collected2 = CollectedArticle(
            url="https://example.com/2",  # type: ignore[arg-type]
            title="Article 2",
            source=sample_source_market,
            collected_at=datetime.now(tz=timezone.utc),
        )

        # One success, one failure
        extracted_success = ExtractedArticle(
            collected=collected1,
            body_text="Content",
            extraction_status=ExtractionStatus.SUCCESS,
            extraction_method="trafilatura",
        )
        extracted_fail = ExtractedArticle(
            collected=collected2,
            body_text=None,
            extraction_status=ExtractionStatus.FAILED,
            extraction_method="trafilatura",
            error_message="Failed",
        )

        with (
            patch("news.orchestrator.RSSCollector") as mock_collector_cls,
            patch("news.orchestrator.TrafilaturaExtractor") as mock_extractor_cls,
            patch("news.orchestrator.Summarizer") as mock_summarizer_cls,
            patch("news.orchestrator.Publisher") as mock_publisher_cls,
        ):
            # Setup mocks
            mock_collector = MagicMock()
            mock_collector.collect = AsyncMock(return_value=[collected1, collected2])
            mock_collector_cls.return_value = mock_collector

            mock_extractor = MagicMock()
            mock_extractor.extract = AsyncMock(
                side_effect=[extracted_success, extracted_fail]
            )
            mock_extractor_cls.return_value = mock_extractor

            mock_summarizer = MagicMock()
            mock_summarizer.summarize_batch = AsyncMock(return_value=[])
            mock_summarizer_cls.return_value = mock_summarizer

            mock_publisher = MagicMock()
            mock_publisher.publish_batch = AsyncMock(return_value=[])
            mock_publisher.get_existing_urls = AsyncMock(return_value=set())
            mock_publisher.is_duplicate_url = MagicMock(return_value=False)
            mock_publisher_cls.return_value = mock_publisher

            orchestrator = NewsWorkflowOrchestrator(config=sample_config)
            result = await orchestrator.run()

            # Summarizer should only receive successful extractions
            call_args = mock_summarizer.summarize_batch.call_args
            passed_articles = call_args[0][0]
            assert len(passed_articles) == 1
            assert passed_articles[0].extraction_status == ExtractionStatus.SUCCESS

    @pytest.mark.asyncio
    async def test_正常系_要約失敗の記事は公開に渡されない(
        self,
        sample_config: NewsWorkflowConfig,
        sample_source_market: ArticleSource,
    ) -> None:
        """Only successfully summarized articles should be passed to publisher."""
        from news.orchestrator import NewsWorkflowOrchestrator

        # Create articles
        collected = CollectedArticle(
            url="https://example.com/1",  # type: ignore[arg-type]
            title="Article 1",
            source=sample_source_market,
            collected_at=datetime.now(tz=timezone.utc),
        )
        extracted = ExtractedArticle(
            collected=collected,
            body_text="Content",
            extraction_status=ExtractionStatus.SUCCESS,
            extraction_method="trafilatura",
        )

        # One success, one failure
        summary = StructuredSummary(
            overview="Test",
            key_points=["Point"],
            market_impact="Impact",
        )
        summarized_success = SummarizedArticle(
            extracted=extracted,
            summary=summary,
            summarization_status=SummarizationStatus.SUCCESS,
        )
        summarized_fail = SummarizedArticle(
            extracted=extracted,
            summary=None,
            summarization_status=SummarizationStatus.FAILED,
            error_message="Failed",
        )

        with (
            patch("news.orchestrator.RSSCollector") as mock_collector_cls,
            patch("news.orchestrator.TrafilaturaExtractor") as mock_extractor_cls,
            patch("news.orchestrator.Summarizer") as mock_summarizer_cls,
            patch("news.orchestrator.Publisher") as mock_publisher_cls,
        ):
            # Setup mocks
            mock_collector = MagicMock()
            mock_collector.collect = AsyncMock(return_value=[collected, collected])
            mock_collector_cls.return_value = mock_collector

            mock_extractor = MagicMock()
            mock_extractor.extract = AsyncMock(return_value=extracted)
            mock_extractor_cls.return_value = mock_extractor

            mock_summarizer = MagicMock()
            mock_summarizer.summarize_batch = AsyncMock(
                return_value=[summarized_success, summarized_fail]
            )
            mock_summarizer_cls.return_value = mock_summarizer

            mock_publisher = MagicMock()
            mock_publisher.publish_batch = AsyncMock(return_value=[])
            mock_publisher.get_existing_urls = AsyncMock(return_value=set())
            mock_publisher.is_duplicate_url = MagicMock(return_value=False)
            mock_publisher_cls.return_value = mock_publisher

            orchestrator = NewsWorkflowOrchestrator(config=sample_config)
            result = await orchestrator.run()

            # Publisher should only receive successful summaries
            call_args = mock_publisher.publish_batch.call_args
            passed_articles = call_args[0][0]
            assert len(passed_articles) == 1
            assert (
                passed_articles[0].summarization_status == SummarizationStatus.SUCCESS
            )


class TestOrchestratorWorkflowResult:
    """Tests for WorkflowResult construction."""

    @pytest.mark.asyncio
    async def test_正常系_WorkflowResultに正しい統計が含まれる(
        self,
        sample_config: NewsWorkflowConfig,
        sample_source_market: ArticleSource,
    ) -> None:
        """WorkflowResult should contain correct statistics."""
        from news.orchestrator import NewsWorkflowOrchestrator

        # Create test data
        collected = CollectedArticle(
            url="https://example.com/1",  # type: ignore[arg-type]
            title="Article 1",
            source=sample_source_market,
            collected_at=datetime.now(tz=timezone.utc),
        )
        extracted = ExtractedArticle(
            collected=collected,
            body_text="Content",
            extraction_status=ExtractionStatus.SUCCESS,
            extraction_method="trafilatura",
        )
        summary = StructuredSummary(
            overview="Test",
            key_points=["Point"],
            market_impact="Impact",
        )
        summarized = SummarizedArticle(
            extracted=extracted,
            summary=summary,
            summarization_status=SummarizationStatus.SUCCESS,
        )
        published = PublishedArticle(
            summarized=summarized,
            issue_number=123,
            issue_url="https://github.com/YH-05/quants/issues/123",
            publication_status=PublicationStatus.SUCCESS,
        )

        with (
            patch("news.orchestrator.RSSCollector") as mock_collector_cls,
            patch("news.orchestrator.TrafilaturaExtractor") as mock_extractor_cls,
            patch("news.orchestrator.Summarizer") as mock_summarizer_cls,
            patch("news.orchestrator.Publisher") as mock_publisher_cls,
        ):
            # Setup mocks
            mock_collector = MagicMock()
            mock_collector.collect = AsyncMock(return_value=[collected])
            mock_collector_cls.return_value = mock_collector

            mock_extractor = MagicMock()
            mock_extractor.extract = AsyncMock(return_value=extracted)
            mock_extractor_cls.return_value = mock_extractor

            mock_summarizer = MagicMock()
            mock_summarizer.summarize_batch = AsyncMock(return_value=[summarized])
            mock_summarizer_cls.return_value = mock_summarizer

            mock_publisher = MagicMock()
            mock_publisher.publish_batch = AsyncMock(return_value=[published])
            mock_publisher.get_existing_urls = AsyncMock(return_value=set())
            mock_publisher.is_duplicate_url = MagicMock(return_value=False)
            mock_publisher_cls.return_value = mock_publisher

            orchestrator = NewsWorkflowOrchestrator(config=sample_config)
            result = await orchestrator.run()

            # Verify statistics
            assert result.total_collected == 1
            assert result.total_extracted == 1
            assert result.total_summarized == 1
            assert result.total_published == 1
            assert len(result.published_articles) == 1
            assert result.published_articles[0] is published

    @pytest.mark.asyncio
    async def test_正常系_WorkflowResultに失敗レコードが含まれる(
        self,
        sample_config: NewsWorkflowConfig,
        sample_source_market: ArticleSource,
    ) -> None:
        """WorkflowResult should contain failure records."""
        from news.orchestrator import NewsWorkflowOrchestrator

        # Create test data with failures
        collected = CollectedArticle(
            url="https://example.com/1",  # type: ignore[arg-type]
            title="Article 1",
            source=sample_source_market,
            collected_at=datetime.now(tz=timezone.utc),
        )
        extracted_fail = ExtractedArticle(
            collected=collected,
            body_text=None,
            extraction_status=ExtractionStatus.FAILED,
            extraction_method="trafilatura",
            error_message="Extraction failed",
        )

        with (
            patch("news.orchestrator.RSSCollector") as mock_collector_cls,
            patch("news.orchestrator.TrafilaturaExtractor") as mock_extractor_cls,
            patch("news.orchestrator.Summarizer") as mock_summarizer_cls,
            patch("news.orchestrator.Publisher") as mock_publisher_cls,
        ):
            # Setup mocks
            mock_collector = MagicMock()
            mock_collector.collect = AsyncMock(return_value=[collected])
            mock_collector_cls.return_value = mock_collector

            mock_extractor = MagicMock()
            mock_extractor.extract = AsyncMock(return_value=extracted_fail)
            mock_extractor_cls.return_value = mock_extractor

            mock_summarizer = MagicMock()
            mock_summarizer.summarize_batch = AsyncMock(return_value=[])
            mock_summarizer_cls.return_value = mock_summarizer

            mock_publisher = MagicMock()
            mock_publisher.publish_batch = AsyncMock(return_value=[])
            mock_publisher.get_existing_urls = AsyncMock(return_value=set())
            mock_publisher.is_duplicate_url = MagicMock(return_value=False)
            mock_publisher_cls.return_value = mock_publisher

            orchestrator = NewsWorkflowOrchestrator(config=sample_config)
            result = await orchestrator.run()

            # Verify failure records
            assert len(result.extraction_failures) == 1
            assert result.extraction_failures[0].stage == "extraction"
            assert result.extraction_failures[0].url == "https://example.com/1"

    @pytest.mark.asyncio
    async def test_正常系_WorkflowResultに重複数が含まれる(
        self,
        sample_config: NewsWorkflowConfig,
        sample_source_market: ArticleSource,
    ) -> None:
        """WorkflowResult should contain duplicate count."""
        from news.orchestrator import NewsWorkflowOrchestrator

        # Create test data
        collected = CollectedArticle(
            url="https://example.com/1",  # type: ignore[arg-type]
            title="Article 1",
            source=sample_source_market,
            collected_at=datetime.now(tz=timezone.utc),
        )
        extracted = ExtractedArticle(
            collected=collected,
            body_text="Content",
            extraction_status=ExtractionStatus.SUCCESS,
            extraction_method="trafilatura",
        )
        summary = StructuredSummary(
            overview="Test",
            key_points=["Point"],
            market_impact="Impact",
        )
        summarized = SummarizedArticle(
            extracted=extracted,
            summary=summary,
            summarization_status=SummarizationStatus.SUCCESS,
        )
        published_dup = PublishedArticle(
            summarized=summarized,
            issue_number=None,
            issue_url=None,
            publication_status=PublicationStatus.DUPLICATE,
        )

        with (
            patch("news.orchestrator.RSSCollector") as mock_collector_cls,
            patch("news.orchestrator.TrafilaturaExtractor") as mock_extractor_cls,
            patch("news.orchestrator.Summarizer") as mock_summarizer_cls,
            patch("news.orchestrator.Publisher") as mock_publisher_cls,
        ):
            # Setup mocks
            mock_collector = MagicMock()
            mock_collector.collect = AsyncMock(return_value=[collected])
            mock_collector_cls.return_value = mock_collector

            mock_extractor = MagicMock()
            mock_extractor.extract = AsyncMock(return_value=extracted)
            mock_extractor_cls.return_value = mock_extractor

            mock_summarizer = MagicMock()
            mock_summarizer.summarize_batch = AsyncMock(return_value=[summarized])
            mock_summarizer_cls.return_value = mock_summarizer

            mock_publisher = MagicMock()
            mock_publisher.publish_batch = AsyncMock(return_value=[published_dup])
            mock_publisher.get_existing_urls = AsyncMock(return_value=set())
            mock_publisher.is_duplicate_url = MagicMock(return_value=False)
            mock_publisher_cls.return_value = mock_publisher

            orchestrator = NewsWorkflowOrchestrator(config=sample_config)
            result = await orchestrator.run()

            # Verify duplicate count
            assert result.total_duplicates == 1
            assert result.total_published == 0

    @pytest.mark.asyncio
    async def test_正常系_WorkflowResultにタイムスタンプが含まれる(
        self,
        sample_config: NewsWorkflowConfig,
    ) -> None:
        """WorkflowResult should contain timestamps."""
        from news.orchestrator import NewsWorkflowOrchestrator

        with (
            patch("news.orchestrator.RSSCollector") as mock_collector_cls,
            patch("news.orchestrator.TrafilaturaExtractor") as mock_extractor_cls,
            patch("news.orchestrator.Summarizer") as mock_summarizer_cls,
            patch("news.orchestrator.Publisher") as mock_publisher_cls,
        ):
            # Setup mocks
            mock_collector = MagicMock()
            mock_collector.collect = AsyncMock(return_value=[])
            mock_collector_cls.return_value = mock_collector

            mock_extractor = MagicMock()
            mock_extractor_cls.return_value = mock_extractor

            mock_summarizer = MagicMock()
            mock_summarizer.summarize_batch = AsyncMock(return_value=[])
            mock_summarizer_cls.return_value = mock_summarizer

            mock_publisher = MagicMock()
            mock_publisher.publish_batch = AsyncMock(return_value=[])
            mock_publisher.get_existing_urls = AsyncMock(return_value=set())
            mock_publisher.is_duplicate_url = MagicMock(return_value=False)
            mock_publisher_cls.return_value = mock_publisher

            orchestrator = NewsWorkflowOrchestrator(config=sample_config)
            result = await orchestrator.run()

            # Verify timestamps
            assert result.started_at is not None
            assert result.finished_at is not None
            assert result.started_at <= result.finished_at
            assert result.elapsed_seconds >= 0


class TestOrchestratorLogging:
    """Tests for logging at each stage."""

    @pytest.mark.asyncio
    async def test_正常系_各ステージで進捗が出力される(
        self,
        sample_config: NewsWorkflowConfig,
        sample_collected_article: CollectedArticle,
        sample_extracted_article: ExtractedArticle,
        sample_summarized_article: SummarizedArticle,
        sample_published_article: PublishedArticle,
        capsys: pytest.CaptureFixture[str],
    ) -> None:
        """run() should print progress at each stage."""
        from news.orchestrator import NewsWorkflowOrchestrator

        with (
            patch("news.orchestrator.RSSCollector") as mock_collector_cls,
            patch("news.orchestrator.TrafilaturaExtractor") as mock_extractor_cls,
            patch("news.orchestrator.Summarizer") as mock_summarizer_cls,
            patch("news.orchestrator.Publisher") as mock_publisher_cls,
        ):
            # Setup mocks with actual articles
            mock_collector = MagicMock()
            mock_collector.collect = AsyncMock(return_value=[sample_collected_article])
            mock_collector_cls.return_value = mock_collector

            mock_extractor = MagicMock()
            mock_extractor.extract = AsyncMock(return_value=sample_extracted_article)
            mock_extractor_cls.return_value = mock_extractor

            mock_summarizer = MagicMock()
            mock_summarizer.summarize_batch = AsyncMock(
                return_value=[sample_summarized_article]
            )
            mock_summarizer_cls.return_value = mock_summarizer

            mock_publisher = MagicMock()
            mock_publisher.publish_batch = AsyncMock(
                return_value=[sample_published_article]
            )
            mock_publisher.get_existing_urls = AsyncMock(return_value=set())
            mock_publisher.is_duplicate_url = MagicMock(return_value=False)
            mock_publisher_cls.return_value = mock_publisher

            orchestrator = NewsWorkflowOrchestrator(config=sample_config)
            await orchestrator.run()

            # Verify progress output
            captured = capsys.readouterr()
            assert "ニュース収集ワークフロー開始" in captured.out
            assert "[1/4]" in captured.out
            assert "[2/4]" in captured.out
            assert "[3/4]" in captured.out
            assert "[4/4]" in captured.out
            assert "ワークフロー完了" in captured.out

    @pytest.mark.asyncio
    async def test_正常系_記事なしの場合は早期終了メッセージが出力される(
        self,
        sample_config: NewsWorkflowConfig,
        capsys: pytest.CaptureFixture[str],
    ) -> None:
        """run() should show early exit message when no articles."""
        from news.orchestrator import NewsWorkflowOrchestrator

        with (
            patch("news.orchestrator.RSSCollector") as mock_collector_cls,
            patch("news.orchestrator.TrafilaturaExtractor") as mock_extractor_cls,
            patch("news.orchestrator.Summarizer") as mock_summarizer_cls,
            patch("news.orchestrator.Publisher") as mock_publisher_cls,
        ):
            # Setup mocks with empty list
            mock_collector = MagicMock()
            mock_collector.collect = AsyncMock(return_value=[])
            mock_collector_cls.return_value = mock_collector

            mock_extractor = MagicMock()
            mock_extractor_cls.return_value = mock_extractor

            mock_summarizer = MagicMock()
            mock_summarizer.summarize_batch = AsyncMock(return_value=[])
            mock_summarizer_cls.return_value = mock_summarizer

            mock_publisher = MagicMock()
            mock_publisher.publish_batch = AsyncMock(return_value=[])
            mock_publisher.get_existing_urls = AsyncMock(return_value=set())
            mock_publisher.is_duplicate_url = MagicMock(return_value=False)
            mock_publisher_cls.return_value = mock_publisher

            orchestrator = NewsWorkflowOrchestrator(config=sample_config)
            await orchestrator.run()

            # Verify early exit message
            captured = capsys.readouterr()
            assert "ニュース収集ワークフロー開始" in captured.out
            assert "[1/4]" in captured.out
            assert "処理対象の記事がありません" in captured.out


class TestOrchestratorBuildResult:
    """Tests for _build_result() helper method."""

    def test_正常系_build_resultが正しくWorkflowResultを生成(
        self,
        sample_config: NewsWorkflowConfig,
        sample_collected_article: CollectedArticle,
        sample_extracted_article: ExtractedArticle,
        sample_summarized_article: SummarizedArticle,
        sample_published_article: PublishedArticle,
    ) -> None:
        """_build_result should correctly construct WorkflowResult."""
        from news.orchestrator import NewsWorkflowOrchestrator

        with (
            patch("news.orchestrator.RSSCollector"),
            patch("news.orchestrator.TrafilaturaExtractor"),
            patch("news.orchestrator.Summarizer"),
            patch("news.orchestrator.Publisher"),
        ):
            orchestrator = NewsWorkflowOrchestrator(config=sample_config)

            started_at = datetime.now(tz=timezone.utc)
            finished_at = datetime.now(tz=timezone.utc)

            result = orchestrator._build_result(
                collected=[sample_collected_article],
                extracted=[sample_extracted_article],
                summarized=[sample_summarized_article],
                published=[sample_published_article],
                started_at=started_at,
                finished_at=finished_at,
            )

            assert isinstance(result, WorkflowResult)
            assert result.total_collected == 1
            assert result.total_extracted == 1
            assert result.total_summarized == 1
            assert result.total_published == 1
            assert result.started_at == started_at
            assert result.finished_at == finished_at


class TestOrchestratorSaveResult:
    """Tests for _save_result() method that saves WorkflowResult to JSON."""

    def test_正常系_save_resultメソッドが存在する(
        self, sample_config: NewsWorkflowConfig
    ) -> None:
        """Orchestrator should have a _save_result() method."""
        from news.orchestrator import NewsWorkflowOrchestrator

        with (
            patch("news.orchestrator.RSSCollector"),
            patch("news.orchestrator.TrafilaturaExtractor"),
            patch("news.orchestrator.Summarizer"),
            patch("news.orchestrator.Publisher"),
        ):
            orchestrator = NewsWorkflowOrchestrator(config=sample_config)

            assert hasattr(orchestrator, "_save_result")
            assert callable(orchestrator._save_result)

    def test_正常系_JSONファイルが保存される(
        self,
        sample_config: NewsWorkflowConfig,
        tmp_path: Path,
    ) -> None:
        """_save_result should save WorkflowResult as JSON file."""
        import json

        from news.orchestrator import NewsWorkflowOrchestrator

        # Update config to use tmp_path
        sample_config.output.result_dir = str(tmp_path)

        with (
            patch("news.orchestrator.RSSCollector"),
            patch("news.orchestrator.TrafilaturaExtractor"),
            patch("news.orchestrator.Summarizer"),
            patch("news.orchestrator.Publisher"),
        ):
            orchestrator = NewsWorkflowOrchestrator(config=sample_config)

            # Create a sample WorkflowResult
            result = WorkflowResult(
                total_collected=10,
                total_extracted=8,
                total_summarized=7,
                total_published=6,
                total_duplicates=1,
                extraction_failures=[],
                summarization_failures=[],
                publication_failures=[],
                started_at=datetime(2026, 1, 15, 10, 0, 0, tzinfo=timezone.utc),
                finished_at=datetime(2026, 1, 15, 10, 15, 0, tzinfo=timezone.utc),
                elapsed_seconds=900.0,
                published_articles=[],
            )

            output_path = orchestrator._save_result(result)

            # Verify file was created
            assert output_path.exists()
            assert output_path.suffix == ".json"

            # Verify content
            with open(output_path, encoding="utf-8") as f:
                saved_data = json.load(f)
            assert saved_data["total_collected"] == 10
            assert saved_data["total_extracted"] == 8
            assert saved_data["total_summarized"] == 7
            assert saved_data["total_published"] == 6
            assert saved_data["total_duplicates"] == 1

    def test_正常系_ファイル名にタイムスタンプが含まれる(
        self,
        sample_config: NewsWorkflowConfig,
        tmp_path: Path,
    ) -> None:
        """_save_result should include timestamp in filename."""
        from news.orchestrator import NewsWorkflowOrchestrator

        # Update config to use tmp_path
        sample_config.output.result_dir = str(tmp_path)

        with (
            patch("news.orchestrator.RSSCollector"),
            patch("news.orchestrator.TrafilaturaExtractor"),
            patch("news.orchestrator.Summarizer"),
            patch("news.orchestrator.Publisher"),
        ):
            orchestrator = NewsWorkflowOrchestrator(config=sample_config)

            # Create a sample WorkflowResult
            result = WorkflowResult(
                total_collected=0,
                total_extracted=0,
                total_summarized=0,
                total_published=0,
                total_duplicates=0,
                extraction_failures=[],
                summarization_failures=[],
                publication_failures=[],
                started_at=datetime.now(tz=timezone.utc),
                finished_at=datetime.now(tz=timezone.utc),
                elapsed_seconds=0.0,
                published_articles=[],
            )

            output_path = orchestrator._save_result(result)

            # Verify filename contains timestamp pattern
            filename = output_path.name
            assert filename.startswith("workflow-result-")
            # Check timestamp format: YYYY-MM-DDTHH-MM-SS
            import re

            pattern = r"workflow-result-\d{4}-\d{2}-\d{2}T\d{2}-\d{2}-\d{2}\.json"
            assert re.match(pattern, filename), (
                f"Filename {filename} does not match expected pattern"
            )

    def test_正常系_出力先ディレクトリが自動作成される(
        self,
        sample_config: NewsWorkflowConfig,
        tmp_path: Path,
    ) -> None:
        """_save_result should create output directory if it doesn't exist."""
        from news.orchestrator import NewsWorkflowOrchestrator

        # Use a nested path that doesn't exist
        nested_dir = tmp_path / "nested" / "output" / "dir"
        sample_config.output.result_dir = str(nested_dir)

        with (
            patch("news.orchestrator.RSSCollector"),
            patch("news.orchestrator.TrafilaturaExtractor"),
            patch("news.orchestrator.Summarizer"),
            patch("news.orchestrator.Publisher"),
        ):
            orchestrator = NewsWorkflowOrchestrator(config=sample_config)

            result = WorkflowResult(
                total_collected=0,
                total_extracted=0,
                total_summarized=0,
                total_published=0,
                total_duplicates=0,
                extraction_failures=[],
                summarization_failures=[],
                publication_failures=[],
                started_at=datetime.now(tz=timezone.utc),
                finished_at=datetime.now(tz=timezone.utc),
                elapsed_seconds=0.0,
                published_articles=[],
            )

            output_path = orchestrator._save_result(result)

            # Verify directory was created
            assert nested_dir.exists()
            assert output_path.parent == nested_dir

    def test_正常系_保存先パスがログに出力される(
        self,
        sample_config: NewsWorkflowConfig,
        tmp_path: Path,
    ) -> None:
        """_save_result should log the output path."""
        from news.orchestrator import NewsWorkflowOrchestrator

        sample_config.output.result_dir = str(tmp_path)

        with (
            patch("news.orchestrator.RSSCollector"),
            patch("news.orchestrator.TrafilaturaExtractor"),
            patch("news.orchestrator.Summarizer"),
            patch("news.orchestrator.Publisher"),
            patch("news.orchestrator.logger") as mock_logger,
        ):
            orchestrator = NewsWorkflowOrchestrator(config=sample_config)

            result = WorkflowResult(
                total_collected=0,
                total_extracted=0,
                total_summarized=0,
                total_published=0,
                total_duplicates=0,
                extraction_failures=[],
                summarization_failures=[],
                publication_failures=[],
                started_at=datetime.now(tz=timezone.utc),
                finished_at=datetime.now(tz=timezone.utc),
                elapsed_seconds=0.0,
                published_articles=[],
            )

            output_path = orchestrator._save_result(result)

            # Verify structured log: "Result saved" message with path kwarg
            mock_logger.info.assert_called()
            call_args_list = mock_logger.info.call_args_list
            save_call = next(
                (
                    call
                    for call in call_args_list
                    if call.args and "Result saved" in str(call.args[0])
                ),
                None,
            )
            assert save_call is not None, (
                "Expected an info log call with 'Result saved' message"
            )
            assert "path" in save_call.kwargs, (
                "Expected 'path' key in structured log kwargs"
            )
            assert str(output_path) == save_call.kwargs["path"], (
                f"Expected path '{output_path}' in log kwargs, "
                f"got '{save_call.kwargs['path']}'"
            )

    def test_正常系_save_resultがPathを返す(
        self,
        sample_config: NewsWorkflowConfig,
        tmp_path: Path,
    ) -> None:
        """_save_result should return the output Path."""
        from news.orchestrator import NewsWorkflowOrchestrator

        sample_config.output.result_dir = str(tmp_path)

        with (
            patch("news.orchestrator.RSSCollector"),
            patch("news.orchestrator.TrafilaturaExtractor"),
            patch("news.orchestrator.Summarizer"),
            patch("news.orchestrator.Publisher"),
        ):
            orchestrator = NewsWorkflowOrchestrator(config=sample_config)

            result = WorkflowResult(
                total_collected=0,
                total_extracted=0,
                total_summarized=0,
                total_published=0,
                total_duplicates=0,
                extraction_failures=[],
                summarization_failures=[],
                publication_failures=[],
                started_at=datetime.now(tz=timezone.utc),
                finished_at=datetime.now(tz=timezone.utc),
                elapsed_seconds=0.0,
                published_articles=[],
            )

            output_path = orchestrator._save_result(result)

            assert isinstance(output_path, Path)


class TestOrchestratorEarlyDuplicateCheck:
    """Tests for early duplicate check after phase 1 collection."""

    @pytest.mark.asyncio
    async def test_正常系_フェーズ1後にget_existing_urlsが呼ばれる(
        self,
        sample_config: NewsWorkflowConfig,
        sample_collected_article: CollectedArticle,
        sample_extracted_article: ExtractedArticle,
        sample_summarized_article: SummarizedArticle,
        sample_published_article: PublishedArticle,
    ) -> None:
        """run() should call get_existing_urls() after collection phase."""
        from news.orchestrator import NewsWorkflowOrchestrator

        with (
            patch("news.orchestrator.RSSCollector") as mock_collector_cls,
            patch("news.orchestrator.TrafilaturaExtractor") as mock_extractor_cls,
            patch("news.orchestrator.Summarizer") as mock_summarizer_cls,
            patch("news.orchestrator.Publisher") as mock_publisher_cls,
        ):
            mock_collector = MagicMock()
            mock_collector.collect = AsyncMock(return_value=[sample_collected_article])
            mock_collector_cls.return_value = mock_collector

            mock_extractor = MagicMock()
            mock_extractor.extract = AsyncMock(return_value=sample_extracted_article)
            mock_extractor_cls.return_value = mock_extractor

            mock_summarizer = MagicMock()
            mock_summarizer.summarize_batch = AsyncMock(
                return_value=[sample_summarized_article]
            )
            mock_summarizer_cls.return_value = mock_summarizer

            mock_publisher = MagicMock()
            mock_publisher.publish_batch = AsyncMock(
                return_value=[sample_published_article]
            )
            mock_publisher.get_existing_urls = AsyncMock(return_value=set())
            mock_publisher.is_duplicate_url = MagicMock(return_value=False)
            mock_publisher_cls.return_value = mock_publisher

            orchestrator = NewsWorkflowOrchestrator(config=sample_config)
            await orchestrator.run()

            mock_publisher.get_existing_urls.assert_called_once()

    @pytest.mark.asyncio
    async def test_正常系_重複記事がフェーズ2前に除外される(
        self,
        sample_config: NewsWorkflowConfig,
        sample_source_market: ArticleSource,
    ) -> None:
        """Duplicate articles should be excluded before extraction phase."""
        from news.orchestrator import NewsWorkflowOrchestrator

        collected1 = CollectedArticle(
            url="https://www.cnbc.com/article/1",  # type: ignore[arg-type]
            title="Article 1",
            source=sample_source_market,
            collected_at=datetime.now(tz=timezone.utc),
        )
        collected2 = CollectedArticle(
            url="https://www.cnbc.com/article/2",  # type: ignore[arg-type]
            title="Article 2 (duplicate)",
            source=sample_source_market,
            collected_at=datetime.now(tz=timezone.utc),
        )

        with (
            patch("news.orchestrator.RSSCollector") as mock_collector_cls,
            patch("news.orchestrator.TrafilaturaExtractor") as mock_extractor_cls,
            patch("news.orchestrator.Summarizer") as mock_summarizer_cls,
            patch("news.orchestrator.Publisher") as mock_publisher_cls,
        ):
            mock_collector = MagicMock()
            mock_collector.collect = AsyncMock(return_value=[collected1, collected2])
            mock_collector_cls.return_value = mock_collector

            mock_extractor = MagicMock()
            mock_extractor.extract = AsyncMock(
                side_effect=lambda a: ExtractedArticle(
                    collected=a,
                    body_text="Content",
                    extraction_status=ExtractionStatus.SUCCESS,
                    extraction_method="trafilatura",
                )
            )
            mock_extractor_cls.return_value = mock_extractor

            mock_summarizer = MagicMock()
            mock_summarizer.summarize_batch = AsyncMock(return_value=[])
            mock_summarizer_cls.return_value = mock_summarizer

            mock_publisher = MagicMock()
            mock_publisher.publish_batch = AsyncMock(return_value=[])
            # article/2 is a duplicate
            existing_urls = {"https://www.cnbc.com/article/2"}
            mock_publisher.get_existing_urls = AsyncMock(return_value=existing_urls)
            mock_publisher.is_duplicate_url = MagicMock(
                side_effect=lambda url, urls: url in urls
            )
            mock_publisher_cls.return_value = mock_publisher

            orchestrator = NewsWorkflowOrchestrator(config=sample_config)
            await orchestrator.run()

            # Only non-duplicate article should reach extraction
            assert mock_extractor.extract.call_count == 1

    @pytest.mark.asyncio
    async def test_正常系_重複除外件数がコンソールに表示される(
        self,
        sample_config: NewsWorkflowConfig,
        sample_source_market: ArticleSource,
        capsys: pytest.CaptureFixture[str],
    ) -> None:
        """Early duplicate count should be printed to console."""
        from news.orchestrator import NewsWorkflowOrchestrator

        collected1 = CollectedArticle(
            url="https://www.cnbc.com/article/1",  # type: ignore[arg-type]
            title="Article 1",
            source=sample_source_market,
            collected_at=datetime.now(tz=timezone.utc),
        )
        collected2 = CollectedArticle(
            url="https://www.cnbc.com/article/2",  # type: ignore[arg-type]
            title="Article 2 (duplicate)",
            source=sample_source_market,
            collected_at=datetime.now(tz=timezone.utc),
        )

        with (
            patch("news.orchestrator.RSSCollector") as mock_collector_cls,
            patch("news.orchestrator.TrafilaturaExtractor") as mock_extractor_cls,
            patch("news.orchestrator.Summarizer") as mock_summarizer_cls,
            patch("news.orchestrator.Publisher") as mock_publisher_cls,
        ):
            mock_collector = MagicMock()
            mock_collector.collect = AsyncMock(return_value=[collected1, collected2])
            mock_collector_cls.return_value = mock_collector

            mock_extractor = MagicMock()
            mock_extractor.extract = AsyncMock(
                side_effect=lambda a: ExtractedArticle(
                    collected=a,
                    body_text="Content",
                    extraction_status=ExtractionStatus.SUCCESS,
                    extraction_method="trafilatura",
                )
            )
            mock_extractor_cls.return_value = mock_extractor

            mock_summarizer = MagicMock()
            mock_summarizer.summarize_batch = AsyncMock(return_value=[])
            mock_summarizer_cls.return_value = mock_summarizer

            mock_publisher = MagicMock()
            mock_publisher.publish_batch = AsyncMock(return_value=[])
            existing_urls = {"https://www.cnbc.com/article/2"}
            mock_publisher.get_existing_urls = AsyncMock(return_value=existing_urls)
            mock_publisher.is_duplicate_url = MagicMock(
                side_effect=lambda url, urls: url in urls
            )
            mock_publisher_cls.return_value = mock_publisher

            orchestrator = NewsWorkflowOrchestrator(config=sample_config)
            await orchestrator.run()

            captured = capsys.readouterr()
            assert "重複除外" in captured.out
            assert "2 -> 1件" in captured.out

    @pytest.mark.asyncio
    async def test_正常系_全記事が重複の場合に空のWorkflowResultが返される(
        self,
        sample_config: NewsWorkflowConfig,
        sample_source_market: ArticleSource,
    ) -> None:
        """When all articles are duplicates, empty WorkflowResult should be returned."""
        from news.orchestrator import NewsWorkflowOrchestrator

        collected1 = CollectedArticle(
            url="https://www.cnbc.com/article/1",  # type: ignore[arg-type]
            title="Article 1",
            source=sample_source_market,
            collected_at=datetime.now(tz=timezone.utc),
        )

        with (
            patch("news.orchestrator.RSSCollector") as mock_collector_cls,
            patch("news.orchestrator.TrafilaturaExtractor") as mock_extractor_cls,
            patch("news.orchestrator.Summarizer") as mock_summarizer_cls,
            patch("news.orchestrator.Publisher") as mock_publisher_cls,
        ):
            mock_collector = MagicMock()
            mock_collector.collect = AsyncMock(return_value=[collected1])
            mock_collector_cls.return_value = mock_collector

            mock_extractor = MagicMock()
            mock_extractor_cls.return_value = mock_extractor

            mock_summarizer = MagicMock()
            mock_summarizer_cls.return_value = mock_summarizer

            mock_publisher = MagicMock()
            existing_urls = {"https://www.cnbc.com/article/1"}
            mock_publisher.get_existing_urls = AsyncMock(return_value=existing_urls)
            mock_publisher.is_duplicate_url = MagicMock(
                side_effect=lambda url, urls: url in urls
            )
            mock_publisher_cls.return_value = mock_publisher

            orchestrator = NewsWorkflowOrchestrator(config=sample_config)
            result = await orchestrator.run()

            assert isinstance(result, WorkflowResult)
            assert result.total_collected == 0
            assert result.total_extracted == 0
            # Extractor should not be called at all
            mock_extractor.extract = AsyncMock()
            assert not mock_extractor.extract.called

    @pytest.mark.asyncio
    async def test_正常系_WorkflowResultにtotal_early_duplicatesが設定される(
        self,
        sample_config: NewsWorkflowConfig,
        sample_source_market: ArticleSource,
    ) -> None:
        """WorkflowResult.total_early_duplicates should be set correctly."""
        from news.orchestrator import NewsWorkflowOrchestrator

        collected1 = CollectedArticle(
            url="https://www.cnbc.com/article/1",  # type: ignore[arg-type]
            title="Article 1",
            source=sample_source_market,
            collected_at=datetime.now(tz=timezone.utc),
        )
        collected2 = CollectedArticle(
            url="https://www.cnbc.com/article/2",  # type: ignore[arg-type]
            title="Article 2 (duplicate)",
            source=sample_source_market,
            collected_at=datetime.now(tz=timezone.utc),
        )

        with (
            patch("news.orchestrator.RSSCollector") as mock_collector_cls,
            patch("news.orchestrator.TrafilaturaExtractor") as mock_extractor_cls,
            patch("news.orchestrator.Summarizer") as mock_summarizer_cls,
            patch("news.orchestrator.Publisher") as mock_publisher_cls,
        ):
            mock_collector = MagicMock()
            mock_collector.collect = AsyncMock(return_value=[collected1, collected2])
            mock_collector_cls.return_value = mock_collector

            mock_extractor = MagicMock()
            mock_extractor.extract = AsyncMock(
                side_effect=lambda a: ExtractedArticle(
                    collected=a,
                    body_text="Content",
                    extraction_status=ExtractionStatus.SUCCESS,
                    extraction_method="trafilatura",
                )
            )
            mock_extractor_cls.return_value = mock_extractor

            mock_summarizer = MagicMock()
            mock_summarizer.summarize_batch = AsyncMock(return_value=[])
            mock_summarizer_cls.return_value = mock_summarizer

            mock_publisher = MagicMock()
            mock_publisher.publish_batch = AsyncMock(return_value=[])
            existing_urls = {"https://www.cnbc.com/article/2"}
            mock_publisher.get_existing_urls = AsyncMock(return_value=existing_urls)
            mock_publisher.is_duplicate_url = MagicMock(
                side_effect=lambda url, urls: url in urls
            )
            mock_publisher_cls.return_value = mock_publisher

            orchestrator = NewsWorkflowOrchestrator(config=sample_config)
            result = await orchestrator.run()

            assert result.total_early_duplicates == 1

    @pytest.mark.asyncio
    async def test_正常系_最終サマリーに早期重複除外件数が表示される(
        self,
        sample_config: NewsWorkflowConfig,
        sample_source_market: ArticleSource,
        capsys: pytest.CaptureFixture[str],
    ) -> None:
        """Final summary should display early duplicate count."""
        from news.orchestrator import NewsWorkflowOrchestrator

        collected1 = CollectedArticle(
            url="https://www.cnbc.com/article/1",  # type: ignore[arg-type]
            title="Article 1",
            source=sample_source_market,
            collected_at=datetime.now(tz=timezone.utc),
        )
        collected2 = CollectedArticle(
            url="https://www.cnbc.com/article/2",  # type: ignore[arg-type]
            title="Article 2 (duplicate)",
            source=sample_source_market,
            collected_at=datetime.now(tz=timezone.utc),
        )
        extracted = ExtractedArticle(
            collected=collected1,
            body_text="Content",
            extraction_status=ExtractionStatus.SUCCESS,
            extraction_method="trafilatura",
        )
        summary = StructuredSummary(
            overview="Test",
            key_points=["Point"],
            market_impact="Impact",
        )
        summarized = SummarizedArticle(
            extracted=extracted,
            summary=summary,
            summarization_status=SummarizationStatus.SUCCESS,
        )
        published = PublishedArticle(
            summarized=summarized,
            issue_number=123,
            issue_url="https://github.com/YH-05/quants/issues/123",
            publication_status=PublicationStatus.SUCCESS,
        )

        with (
            patch("news.orchestrator.RSSCollector") as mock_collector_cls,
            patch("news.orchestrator.TrafilaturaExtractor") as mock_extractor_cls,
            patch("news.orchestrator.Summarizer") as mock_summarizer_cls,
            patch("news.orchestrator.Publisher") as mock_publisher_cls,
        ):
            mock_collector = MagicMock()
            mock_collector.collect = AsyncMock(return_value=[collected1, collected2])
            mock_collector_cls.return_value = mock_collector

            mock_extractor = MagicMock()
            mock_extractor.extract = AsyncMock(return_value=extracted)
            mock_extractor_cls.return_value = mock_extractor

            mock_summarizer = MagicMock()
            mock_summarizer.summarize_batch = AsyncMock(return_value=[summarized])
            mock_summarizer_cls.return_value = mock_summarizer

            mock_publisher = MagicMock()
            mock_publisher.publish_batch = AsyncMock(return_value=[published])
            existing_urls = {"https://www.cnbc.com/article/2"}
            mock_publisher.get_existing_urls = AsyncMock(return_value=existing_urls)
            mock_publisher.is_duplicate_url = MagicMock(
                side_effect=lambda url, urls: url in urls
            )
            mock_publisher_cls.return_value = mock_publisher

            orchestrator = NewsWorkflowOrchestrator(config=sample_config)
            await orchestrator.run()

            captured = capsys.readouterr()
            assert "重複除外（早期）" in captured.out
            assert "1件" in captured.out


class TestOrchestratorBuildResultEarlyDuplicates:
    """Tests for _build_result() with early_duplicates parameter."""

    def test_正常系_build_resultにearly_duplicatesパラメータが追加されている(
        self,
        sample_config: NewsWorkflowConfig,
        sample_collected_article: CollectedArticle,
        sample_extracted_article: ExtractedArticle,
        sample_summarized_article: SummarizedArticle,
        sample_published_article: PublishedArticle,
    ) -> None:
        """_build_result should accept early_duplicates parameter."""
        from news.orchestrator import NewsWorkflowOrchestrator

        with (
            patch("news.orchestrator.RSSCollector"),
            patch("news.orchestrator.TrafilaturaExtractor"),
            patch("news.orchestrator.Summarizer"),
            patch("news.orchestrator.Publisher"),
        ):
            orchestrator = NewsWorkflowOrchestrator(config=sample_config)

            started_at = datetime.now(tz=timezone.utc)
            finished_at = datetime.now(tz=timezone.utc)

            result = orchestrator._build_result(
                collected=[sample_collected_article],
                extracted=[sample_extracted_article],
                summarized=[sample_summarized_article],
                published=[sample_published_article],
                started_at=started_at,
                finished_at=finished_at,
                early_duplicates=5,
            )

            assert result.total_early_duplicates == 5

    def test_正常系_early_duplicatesのデフォルトは0(
        self,
        sample_config: NewsWorkflowConfig,
        sample_collected_article: CollectedArticle,
        sample_extracted_article: ExtractedArticle,
        sample_summarized_article: SummarizedArticle,
        sample_published_article: PublishedArticle,
    ) -> None:
        """_build_result should default early_duplicates to 0."""
        from news.orchestrator import NewsWorkflowOrchestrator

        with (
            patch("news.orchestrator.RSSCollector"),
            patch("news.orchestrator.TrafilaturaExtractor"),
            patch("news.orchestrator.Summarizer"),
            patch("news.orchestrator.Publisher"),
        ):
            orchestrator = NewsWorkflowOrchestrator(config=sample_config)

            started_at = datetime.now(tz=timezone.utc)
            finished_at = datetime.now(tz=timezone.utc)

            result = orchestrator._build_result(
                collected=[sample_collected_article],
                extracted=[sample_extracted_article],
                summarized=[sample_summarized_article],
                published=[sample_published_article],
                started_at=started_at,
                finished_at=finished_at,
            )

            assert result.total_early_duplicates == 0


class TestOrchestratorRunSavesResult:
    """Tests for run() calling _save_result."""

    @pytest.mark.asyncio
    async def test_正常系_runがsave_resultを呼び出す(
        self,
        sample_config: NewsWorkflowConfig,
        sample_collected_article: CollectedArticle,
        sample_extracted_article: ExtractedArticle,
        sample_summarized_article: SummarizedArticle,
        sample_published_article: PublishedArticle,
        tmp_path: Path,
    ) -> None:
        """run() should call _save_result with the result."""
        from news.orchestrator import NewsWorkflowOrchestrator

        sample_config.output.result_dir = str(tmp_path)

        with (
            patch("news.orchestrator.RSSCollector") as mock_collector_cls,
            patch("news.orchestrator.TrafilaturaExtractor") as mock_extractor_cls,
            patch("news.orchestrator.Summarizer") as mock_summarizer_cls,
            patch("news.orchestrator.Publisher") as mock_publisher_cls,
        ):
            # Setup mocks with actual articles to ensure workflow doesn't early return
            mock_collector = MagicMock()
            mock_collector.collect = AsyncMock(return_value=[sample_collected_article])
            mock_collector_cls.return_value = mock_collector

            mock_extractor = MagicMock()
            mock_extractor.extract = AsyncMock(return_value=sample_extracted_article)
            mock_extractor_cls.return_value = mock_extractor

            mock_summarizer = MagicMock()
            mock_summarizer.summarize_batch = AsyncMock(
                return_value=[sample_summarized_article]
            )
            mock_summarizer_cls.return_value = mock_summarizer

            mock_publisher = MagicMock()
            mock_publisher.publish_batch = AsyncMock(
                return_value=[sample_published_article]
            )
            mock_publisher.get_existing_urls = AsyncMock(return_value=set())
            mock_publisher.is_duplicate_url = MagicMock(return_value=False)
            mock_publisher_cls.return_value = mock_publisher

            orchestrator = NewsWorkflowOrchestrator(config=sample_config)
            result = await orchestrator.run()

            # Verify JSON file was created
            json_files = list(tmp_path.glob("workflow-result-*.json"))
            assert len(json_files) == 1


class TestOrchestratorFeedErrors:
    """Tests for feed error count display in final summary."""

    @pytest.mark.asyncio
    async def test_正常系_フィードエラーがある場合にサマリーに表示される(
        self,
        sample_config: NewsWorkflowConfig,
        sample_collected_article: CollectedArticle,
        sample_extracted_article: ExtractedArticle,
        sample_summarized_article: SummarizedArticle,
        sample_published_article: PublishedArticle,
        capsys: pytest.CaptureFixture[str],
    ) -> None:
        """Final summary should display feed error count when errors exist."""
        from news.orchestrator import NewsWorkflowOrchestrator

        feed_errors = [
            FeedError(
                feed_url="https://example.com/feed.xml",
                feed_name="Example Feed",
                error="Connection timeout",
                error_type="fetch",
                timestamp=datetime(2026, 1, 15, 10, 0, 0, tzinfo=timezone.utc),
            ),
            FeedError(
                feed_url="https://example.com/feed2.xml",
                feed_name="Example Feed 2",
                error="Parse error",
                error_type="parse",
                timestamp=datetime(2026, 1, 15, 10, 0, 0, tzinfo=timezone.utc),
            ),
        ]

        with (
            patch("news.orchestrator.RSSCollector") as mock_collector_cls,
            patch("news.orchestrator.TrafilaturaExtractor") as mock_extractor_cls,
            patch("news.orchestrator.Summarizer") as mock_summarizer_cls,
            patch("news.orchestrator.Publisher") as mock_publisher_cls,
        ):
            mock_collector = MagicMock()
            mock_collector.collect = AsyncMock(return_value=[sample_collected_article])
            mock_collector.feed_errors = feed_errors
            mock_collector_cls.return_value = mock_collector

            mock_extractor = MagicMock()
            mock_extractor.extract = AsyncMock(return_value=sample_extracted_article)
            mock_extractor_cls.return_value = mock_extractor

            mock_summarizer = MagicMock()
            mock_summarizer.summarize_batch = AsyncMock(
                return_value=[sample_summarized_article]
            )
            mock_summarizer_cls.return_value = mock_summarizer

            mock_publisher = MagicMock()
            mock_publisher.publish_batch = AsyncMock(
                return_value=[sample_published_article]
            )
            mock_publisher.get_existing_urls = AsyncMock(return_value=set())
            mock_publisher.is_duplicate_url = MagicMock(return_value=False)
            mock_publisher_cls.return_value = mock_publisher

            orchestrator = NewsWorkflowOrchestrator(config=sample_config)
            result = await orchestrator.run()

            captured = capsys.readouterr()
            assert "フィードエラー: 2件" in captured.out

    @pytest.mark.asyncio
    async def test_正常系_フィードエラーがない場合はサマリーに表示されない(
        self,
        sample_config: NewsWorkflowConfig,
        sample_collected_article: CollectedArticle,
        sample_extracted_article: ExtractedArticle,
        sample_summarized_article: SummarizedArticle,
        sample_published_article: PublishedArticle,
        capsys: pytest.CaptureFixture[str],
    ) -> None:
        """Final summary should NOT display feed error line when no errors."""
        from news.orchestrator import NewsWorkflowOrchestrator

        with (
            patch("news.orchestrator.RSSCollector") as mock_collector_cls,
            patch("news.orchestrator.TrafilaturaExtractor") as mock_extractor_cls,
            patch("news.orchestrator.Summarizer") as mock_summarizer_cls,
            patch("news.orchestrator.Publisher") as mock_publisher_cls,
        ):
            mock_collector = MagicMock()
            mock_collector.collect = AsyncMock(return_value=[sample_collected_article])
            mock_collector.feed_errors = []
            mock_collector_cls.return_value = mock_collector

            mock_extractor = MagicMock()
            mock_extractor.extract = AsyncMock(return_value=sample_extracted_article)
            mock_extractor_cls.return_value = mock_extractor

            mock_summarizer = MagicMock()
            mock_summarizer.summarize_batch = AsyncMock(
                return_value=[sample_summarized_article]
            )
            mock_summarizer_cls.return_value = mock_summarizer

            mock_publisher = MagicMock()
            mock_publisher.publish_batch = AsyncMock(
                return_value=[sample_published_article]
            )
            mock_publisher.get_existing_urls = AsyncMock(return_value=set())
            mock_publisher.is_duplicate_url = MagicMock(return_value=False)
            mock_publisher_cls.return_value = mock_publisher

            orchestrator = NewsWorkflowOrchestrator(config=sample_config)
            result = await orchestrator.run()

            captured = capsys.readouterr()
            assert "フィードエラー" not in captured.out

    @pytest.mark.asyncio
    async def test_正常系_フィードエラーの表示位置が収集の直後(
        self,
        sample_config: NewsWorkflowConfig,
        sample_collected_article: CollectedArticle,
        sample_extracted_article: ExtractedArticle,
        sample_summarized_article: SummarizedArticle,
        sample_published_article: PublishedArticle,
        capsys: pytest.CaptureFixture[str],
    ) -> None:
        """Feed error line should appear between collection and extraction lines."""
        from news.orchestrator import NewsWorkflowOrchestrator

        feed_errors = [
            FeedError(
                feed_url="https://example.com/feed.xml",
                feed_name="Example Feed",
                error="Connection timeout",
                error_type="fetch",
                timestamp=datetime(2026, 1, 15, 10, 0, 0, tzinfo=timezone.utc),
            ),
        ]

        with (
            patch("news.orchestrator.RSSCollector") as mock_collector_cls,
            patch("news.orchestrator.TrafilaturaExtractor") as mock_extractor_cls,
            patch("news.orchestrator.Summarizer") as mock_summarizer_cls,
            patch("news.orchestrator.Publisher") as mock_publisher_cls,
        ):
            mock_collector = MagicMock()
            mock_collector.collect = AsyncMock(return_value=[sample_collected_article])
            mock_collector.feed_errors = feed_errors
            mock_collector_cls.return_value = mock_collector

            mock_extractor = MagicMock()
            mock_extractor.extract = AsyncMock(return_value=sample_extracted_article)
            mock_extractor_cls.return_value = mock_extractor

            mock_summarizer = MagicMock()
            mock_summarizer.summarize_batch = AsyncMock(
                return_value=[sample_summarized_article]
            )
            mock_summarizer_cls.return_value = mock_summarizer

            mock_publisher = MagicMock()
            mock_publisher.publish_batch = AsyncMock(
                return_value=[sample_published_article]
            )
            mock_publisher.get_existing_urls = AsyncMock(return_value=set())
            mock_publisher.is_duplicate_url = MagicMock(return_value=False)
            mock_publisher_cls.return_value = mock_publisher

            orchestrator = NewsWorkflowOrchestrator(config=sample_config)
            await orchestrator.run()

            captured = capsys.readouterr()
            lines = captured.out.split("\n")

            # Find the indices of relevant lines in the final summary
            collection_line_idx = None
            feed_error_line_idx = None
            extraction_line_idx = None
            for i, line in enumerate(lines):
                if "収集:" in line and "件" in line:
                    collection_line_idx = i
                if "フィードエラー:" in line:
                    feed_error_line_idx = i
                if "抽出:" in line and "件" in line:
                    extraction_line_idx = i

            assert collection_line_idx is not None, "収集 line not found"
            assert feed_error_line_idx is not None, "フィードエラー line not found"
            assert extraction_line_idx is not None, "抽出 line not found"
            assert collection_line_idx < feed_error_line_idx < extraction_line_idx

    @pytest.mark.asyncio
    async def test_正常系_WorkflowResultにfeed_errorsが正しく設定される(
        self,
        sample_config: NewsWorkflowConfig,
        sample_collected_article: CollectedArticle,
        sample_extracted_article: ExtractedArticle,
        sample_summarized_article: SummarizedArticle,
        sample_published_article: PublishedArticle,
    ) -> None:
        """WorkflowResult.feed_errors should be set from collector."""
        from news.orchestrator import NewsWorkflowOrchestrator

        feed_errors = [
            FeedError(
                feed_url="https://example.com/feed.xml",
                feed_name="Example Feed",
                error="Connection timeout",
                error_type="fetch",
                timestamp=datetime(2026, 1, 15, 10, 0, 0, tzinfo=timezone.utc),
            ),
        ]

        with (
            patch("news.orchestrator.RSSCollector") as mock_collector_cls,
            patch("news.orchestrator.TrafilaturaExtractor") as mock_extractor_cls,
            patch("news.orchestrator.Summarizer") as mock_summarizer_cls,
            patch("news.orchestrator.Publisher") as mock_publisher_cls,
        ):
            mock_collector = MagicMock()
            mock_collector.collect = AsyncMock(return_value=[sample_collected_article])
            mock_collector.feed_errors = feed_errors
            mock_collector_cls.return_value = mock_collector

            mock_extractor = MagicMock()
            mock_extractor.extract = AsyncMock(return_value=sample_extracted_article)
            mock_extractor_cls.return_value = mock_extractor

            mock_summarizer = MagicMock()
            mock_summarizer.summarize_batch = AsyncMock(
                return_value=[sample_summarized_article]
            )
            mock_summarizer_cls.return_value = mock_summarizer

            mock_publisher = MagicMock()
            mock_publisher.publish_batch = AsyncMock(
                return_value=[sample_published_article]
            )
            mock_publisher.get_existing_urls = AsyncMock(return_value=set())
            mock_publisher.is_duplicate_url = MagicMock(return_value=False)
            mock_publisher_cls.return_value = mock_publisher

            orchestrator = NewsWorkflowOrchestrator(config=sample_config)
            result = await orchestrator.run()

            assert len(result.feed_errors) == 1
            assert result.feed_errors[0].feed_url == "https://example.com/feed.xml"
            assert result.feed_errors[0].error_type == "fetch"

    def test_正常系_build_resultにfeed_errorsが渡される(
        self,
        sample_config: NewsWorkflowConfig,
        sample_collected_article: CollectedArticle,
        sample_extracted_article: ExtractedArticle,
        sample_summarized_article: SummarizedArticle,
        sample_published_article: PublishedArticle,
    ) -> None:
        """_build_result should accept and pass feed_errors to WorkflowResult."""
        from news.orchestrator import NewsWorkflowOrchestrator

        feed_errors = [
            FeedError(
                feed_url="https://example.com/feed.xml",
                feed_name="Example Feed",
                error="Connection timeout",
                error_type="fetch",
                timestamp=datetime(2026, 1, 15, 10, 0, 0, tzinfo=timezone.utc),
            ),
        ]

        with (
            patch("news.orchestrator.RSSCollector"),
            patch("news.orchestrator.TrafilaturaExtractor"),
            patch("news.orchestrator.Summarizer"),
            patch("news.orchestrator.Publisher"),
        ):
            orchestrator = NewsWorkflowOrchestrator(config=sample_config)

            started_at = datetime.now(tz=timezone.utc)
            finished_at = datetime.now(tz=timezone.utc)

            result = orchestrator._build_result(
                collected=[sample_collected_article],
                extracted=[sample_extracted_article],
                summarized=[sample_summarized_article],
                published=[sample_published_article],
                started_at=started_at,
                finished_at=finished_at,
                feed_errors=feed_errors,
            )

            assert len(result.feed_errors) == 1
            assert result.feed_errors[0].feed_name == "Example Feed"

    def test_正常系_build_resultのfeed_errorsデフォルトは空リスト(
        self,
        sample_config: NewsWorkflowConfig,
        sample_collected_article: CollectedArticle,
        sample_extracted_article: ExtractedArticle,
        sample_summarized_article: SummarizedArticle,
        sample_published_article: PublishedArticle,
    ) -> None:
        """_build_result should default feed_errors to empty list."""
        from news.orchestrator import NewsWorkflowOrchestrator

        with (
            patch("news.orchestrator.RSSCollector"),
            patch("news.orchestrator.TrafilaturaExtractor"),
            patch("news.orchestrator.Summarizer"),
            patch("news.orchestrator.Publisher"),
        ):
            orchestrator = NewsWorkflowOrchestrator(config=sample_config)

            started_at = datetime.now(tz=timezone.utc)
            finished_at = datetime.now(tz=timezone.utc)

            result = orchestrator._build_result(
                collected=[sample_collected_article],
                extracted=[sample_extracted_article],
                summarized=[sample_summarized_article],
                published=[sample_published_article],
                started_at=started_at,
                finished_at=finished_at,
            )

            assert result.feed_errors == []
