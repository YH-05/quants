"""Integration tests for NewsWorkflowOrchestrator.

E2E tests with mocked external dependencies (Claude Agent SDK, gh CLI, HTTP requests).
Tests the complete pipeline: Collector -> Extractor -> Summarizer -> Publisher.

Following the test specification from P6-005:
- E2E mock integration tests
- Status filtering tests
- Article count limiting tests
- Dry run tests
- JSON output tests
- Error continuation tests
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
    PublicationStatus,
    PublishedArticle,
    SourceType,
    StructuredSummary,
    SummarizationStatus,
    SummarizedArticle,
    WorkflowResult,
)
from news.orchestrator import NewsWorkflowOrchestrator


@pytest.fixture
def integration_config() -> NewsWorkflowConfig:
    """Create a NewsWorkflowConfig for integration testing.

    Uses per_article format to test legacy per-article publishing pipeline.
    For per_category integration tests, see test_orchestrator_integration.py.
    """
    return NewsWorkflowConfig(
        version="1.0",
        status_mapping={
            "market": "index",
            "tech": "ai",
            "finance": "finance",
            "sector": "sector",
        },
        github_status_ids={
            "index": "test-index-id",
            "ai": "test-ai-id",
            "finance": "test-finance-id",
            "sector": "test-sector-id",
        },
        rss={"presets_file": "data/config/rss-presets.json"},  # type: ignore[arg-type]
        summarization=SummarizationConfig(
            prompt_template="Summarize: {body}",
            concurrency=2,
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
def sample_sources() -> dict[str, ArticleSource]:
    """Create sample ArticleSources for different categories."""
    return {
        "market": ArticleSource(
            source_type=SourceType.RSS,
            source_name="CNBC Markets",
            category="market",
        ),
        "tech": ArticleSource(
            source_type=SourceType.RSS,
            source_name="Tech Crunch",
            category="tech",
        ),
        "finance": ArticleSource(
            source_type=SourceType.RSS,
            source_name="Bloomberg Finance",
            category="finance",
        ),
    }


@pytest.fixture
def sample_collected_articles(
    sample_sources: dict[str, ArticleSource],
) -> list[CollectedArticle]:
    """Create a set of CollectedArticles for testing."""
    now = datetime.now(tz=timezone.utc)
    return [
        CollectedArticle(
            url="https://www.cnbc.com/market/article1",  # type: ignore[arg-type]
            title="S&P 500 Hits New High",
            published=now,
            raw_summary="Markets rally on earnings.",
            source=sample_sources["market"],
            collected_at=now,
        ),
        CollectedArticle(
            url="https://www.cnbc.com/market/article2",  # type: ignore[arg-type]
            title="NASDAQ Surges",
            published=now,
            raw_summary="Tech stocks lead the way.",
            source=sample_sources["market"],
            collected_at=now,
        ),
        CollectedArticle(
            url="https://techcrunch.com/ai/article1",  # type: ignore[arg-type]
            title="AI Revolution Continues",
            published=now,
            raw_summary="AI companies report strong growth.",
            source=sample_sources["tech"],
            collected_at=now,
        ),
        CollectedArticle(
            url="https://bloomberg.com/finance/article1",  # type: ignore[arg-type]
            title="Fed Keeps Rates Steady",
            published=now,
            raw_summary="No change in interest rates.",
            source=sample_sources["finance"],
            collected_at=now,
        ),
    ]


def create_extracted_article(
    collected: CollectedArticle,
    success: bool = True,
) -> ExtractedArticle:
    """Helper to create ExtractedArticle from CollectedArticle."""
    if success:
        return ExtractedArticle(
            collected=collected,
            body_text=f"Full body text for {collected.title}...",
            extraction_status=ExtractionStatus.SUCCESS,
            extraction_method="trafilatura",
        )
    return ExtractedArticle(
        collected=collected,
        body_text=None,
        extraction_status=ExtractionStatus.FAILED,
        extraction_method="trafilatura",
        error_message="Extraction failed",
    )


def create_summarized_article(
    extracted: ExtractedArticle,
    success: bool = True,
) -> SummarizedArticle:
    """Helper to create SummarizedArticle from ExtractedArticle."""
    if success:
        summary = StructuredSummary(
            overview=f"Summary of {extracted.collected.title}",
            key_points=["Point 1", "Point 2"],
            market_impact="Positive market impact expected.",
        )
        return SummarizedArticle(
            extracted=extracted,
            summary=summary,
            summarization_status=SummarizationStatus.SUCCESS,
        )
    return SummarizedArticle(
        extracted=extracted,
        summary=None,
        summarization_status=SummarizationStatus.FAILED,
        error_message="Summarization failed",
    )


def create_published_article(
    summarized: SummarizedArticle,
    issue_number: int,
    success: bool = True,
    duplicate: bool = False,
) -> PublishedArticle:
    """Helper to create PublishedArticle from SummarizedArticle."""
    if duplicate:
        return PublishedArticle(
            summarized=summarized,
            issue_number=None,
            issue_url=None,
            publication_status=PublicationStatus.DUPLICATE,
            error_message="Duplicate article detected",
        )
    if success:
        return PublishedArticle(
            summarized=summarized,
            issue_number=issue_number,
            issue_url=f"https://github.com/YH-05/quants/issues/{issue_number}",
            publication_status=PublicationStatus.SUCCESS,
        )
    return PublishedArticle(
        summarized=summarized,
        issue_number=None,
        issue_url=None,
        publication_status=PublicationStatus.FAILED,
        error_message="Publication failed",
    )


class TestNewsWorkflowOrchestrator:
    """Integration tests for NewsWorkflowOrchestrator."""

    @pytest.mark.asyncio
    async def test_正常系_全パイプラインが正常に動作する(
        self,
        integration_config: NewsWorkflowConfig,
        sample_collected_articles: list[CollectedArticle],
        tmp_path: Path,
    ) -> None:
        """E2E test: all pipeline stages work correctly."""
        # Configure output directory
        integration_config.output.result_dir = str(tmp_path)

        with (
            patch("news.orchestrator.RSSCollector") as mock_collector_cls,
            patch("news.orchestrator.TrafilaturaExtractor") as mock_extractor_cls,
            patch("news.orchestrator.Summarizer") as mock_summarizer_cls,
            patch("news.orchestrator.Publisher") as mock_publisher_cls,
        ):
            # Setup collector mock
            mock_collector = MagicMock()
            mock_collector.collect = AsyncMock(return_value=sample_collected_articles)
            mock_collector_cls.return_value = mock_collector

            # Setup extractor mock - extract all articles successfully
            extracted_articles = [
                create_extracted_article(a) for a in sample_collected_articles
            ]
            mock_extractor = MagicMock()
            mock_extractor.extract = AsyncMock(side_effect=extracted_articles)
            mock_extractor_cls.return_value = mock_extractor

            # Setup summarizer mock - summarize all articles successfully
            # Create summarized articles for each extracted article
            summarized_articles = [
                create_summarized_article(e) for e in extracted_articles
            ]
            mock_summarizer = MagicMock()
            # summarize_batch is called with batches based on concurrency setting
            # We need to return the correct subset for each batch call
            # With concurrency=2 and 4 articles: batch1=[0,1], batch2=[2,3]
            mock_summarizer.summarize_batch = AsyncMock(
                side_effect=[
                    summarized_articles[:2],  # First batch
                    summarized_articles[2:],  # Second batch
                ]
            )
            mock_summarizer_cls.return_value = mock_summarizer

            # Setup publisher mock - publish all articles successfully
            published_articles = [
                create_published_article(s, i + 100)
                for i, s in enumerate(summarized_articles)
            ]
            mock_publisher = MagicMock()
            mock_publisher.publish_batch = AsyncMock(return_value=published_articles)
            mock_publisher.get_existing_urls = AsyncMock(return_value=set())
            mock_publisher.is_duplicate_url = MagicMock(return_value=False)
            mock_publisher_cls.return_value = mock_publisher

            # Run the orchestrator
            orchestrator = NewsWorkflowOrchestrator(config=integration_config)
            result = await orchestrator.run()

            # Verify full pipeline execution
            assert result.total_collected == 4
            assert result.total_extracted == 4
            assert result.total_summarized == 4
            assert result.total_published == 4
            assert result.total_duplicates == 0
            assert len(result.extraction_failures) == 0
            assert len(result.summarization_failures) == 0
            assert len(result.publication_failures) == 0
            assert len(result.published_articles) == 4

    @pytest.mark.asyncio
    async def test_正常系_Statusフィルタリングが機能する(
        self,
        integration_config: NewsWorkflowConfig,
        sample_collected_articles: list[CollectedArticle],
        tmp_path: Path,
    ) -> None:
        """Test: status filtering works correctly."""
        integration_config.output.result_dir = str(tmp_path)

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

            # Extractor returns success for each article
            mock_extractor = MagicMock()
            mock_extractor.extract = AsyncMock(
                side_effect=lambda a: create_extracted_article(a)
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

            orchestrator = NewsWorkflowOrchestrator(config=integration_config)
            # Filter to only "index" status (market category maps to index)
            result = await orchestrator.run(statuses=["index"])

            # Should only process 2 market articles (out of 4 total)
            # market category -> index status
            assert mock_extractor.extract.call_count == 2

    @pytest.mark.asyncio
    async def test_正常系_max_articlesで件数制限される(
        self,
        integration_config: NewsWorkflowConfig,
        sample_collected_articles: list[CollectedArticle],
        tmp_path: Path,
    ) -> None:
        """Test: max_articles limit is applied correctly."""
        integration_config.output.result_dir = str(tmp_path)

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
                side_effect=lambda a: create_extracted_article(a)
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

            orchestrator = NewsWorkflowOrchestrator(config=integration_config)
            # Limit to 2 articles
            result = await orchestrator.run(max_articles=2)

            # Should only process 2 articles
            assert mock_extractor.extract.call_count == 2

    @pytest.mark.asyncio
    async def test_正常系_dry_runでIssue作成スキップ(
        self,
        integration_config: NewsWorkflowConfig,
        sample_collected_articles: list[CollectedArticle],
        tmp_path: Path,
    ) -> None:
        """Test: dry_run mode skips actual Issue creation."""
        integration_config.output.result_dir = str(tmp_path)

        with (
            patch("news.orchestrator.RSSCollector") as mock_collector_cls,
            patch("news.orchestrator.TrafilaturaExtractor") as mock_extractor_cls,
            patch("news.orchestrator.Summarizer") as mock_summarizer_cls,
            patch("news.orchestrator.Publisher") as mock_publisher_cls,
        ):
            # Setup mocks
            mock_collector = MagicMock()
            mock_collector.collect = AsyncMock(
                return_value=[sample_collected_articles[0]]
            )
            mock_collector_cls.return_value = mock_collector

            extracted = create_extracted_article(sample_collected_articles[0])
            mock_extractor = MagicMock()
            mock_extractor.extract = AsyncMock(return_value=extracted)
            mock_extractor_cls.return_value = mock_extractor

            summarized = create_summarized_article(extracted)
            mock_summarizer = MagicMock()
            mock_summarizer.summarize_batch = AsyncMock(return_value=[summarized])
            mock_summarizer_cls.return_value = mock_summarizer

            mock_publisher = MagicMock()
            mock_publisher.publish_batch = AsyncMock(return_value=[])
            mock_publisher.get_existing_urls = AsyncMock(return_value=set())
            mock_publisher.is_duplicate_url = MagicMock(return_value=False)
            mock_publisher_cls.return_value = mock_publisher

            orchestrator = NewsWorkflowOrchestrator(config=integration_config)
            await orchestrator.run(dry_run=True)

            # Verify dry_run was passed to publisher
            mock_publisher.publish_batch.assert_called_once()
            call_kwargs = mock_publisher.publish_batch.call_args.kwargs
            assert call_kwargs.get("dry_run") is True

    @pytest.mark.asyncio
    async def test_正常系_結果JSONが保存される(
        self,
        integration_config: NewsWorkflowConfig,
        sample_collected_articles: list[CollectedArticle],
        tmp_path: Path,
    ) -> None:
        """Test: workflow result is saved as JSON file."""
        integration_config.output.result_dir = str(tmp_path)

        with (
            patch("news.orchestrator.RSSCollector") as mock_collector_cls,
            patch("news.orchestrator.TrafilaturaExtractor"),
            patch("news.orchestrator.Summarizer") as mock_summarizer_cls,
            patch("news.orchestrator.Publisher") as mock_publisher_cls,
        ):
            mock_collector = MagicMock()
            mock_collector.collect = AsyncMock(return_value=[])
            mock_collector_cls.return_value = mock_collector

            mock_summarizer = MagicMock()
            mock_summarizer.summarize_batch = AsyncMock(return_value=[])
            mock_summarizer_cls.return_value = mock_summarizer

            mock_publisher = MagicMock()
            mock_publisher.publish_batch = AsyncMock(return_value=[])
            mock_publisher.get_existing_urls = AsyncMock(return_value=set())
            mock_publisher.is_duplicate_url = MagicMock(return_value=False)
            mock_publisher_cls.return_value = mock_publisher

            orchestrator = NewsWorkflowOrchestrator(config=integration_config)
            await orchestrator.run()

            # Verify JSON file was created
            json_files = list(tmp_path.glob("workflow-result-*.json"))
            assert len(json_files) == 1

            # Verify JSON content structure
            import json

            with open(json_files[0], encoding="utf-8") as f:
                data = json.load(f)
            assert "total_collected" in data
            assert "total_extracted" in data
            assert "total_summarized" in data
            assert "total_published" in data
            assert "started_at" in data
            assert "finished_at" in data
            assert "elapsed_seconds" in data

    @pytest.mark.asyncio
    async def test_正常系_WorkflowResultが正しく構築される(
        self,
        integration_config: NewsWorkflowConfig,
        sample_collected_articles: list[CollectedArticle],
        tmp_path: Path,
    ) -> None:
        """Test: WorkflowResult is constructed correctly with all statistics."""
        integration_config.output.result_dir = str(tmp_path)

        with (
            patch("news.orchestrator.RSSCollector") as mock_collector_cls,
            patch("news.orchestrator.TrafilaturaExtractor") as mock_extractor_cls,
            patch("news.orchestrator.Summarizer") as mock_summarizer_cls,
            patch("news.orchestrator.Publisher") as mock_publisher_cls,
        ):
            # Use 2 articles for this test
            articles = sample_collected_articles[:2]

            mock_collector = MagicMock()
            mock_collector.collect = AsyncMock(return_value=articles)
            mock_collector_cls.return_value = mock_collector

            extracted = [create_extracted_article(a) for a in articles]
            mock_extractor = MagicMock()
            mock_extractor.extract = AsyncMock(side_effect=extracted)
            mock_extractor_cls.return_value = mock_extractor

            summarized = [create_summarized_article(e) for e in extracted]
            mock_summarizer = MagicMock()
            mock_summarizer.summarize_batch = AsyncMock(return_value=summarized)
            mock_summarizer_cls.return_value = mock_summarizer

            published = [
                create_published_article(s, 100 + i) for i, s in enumerate(summarized)
            ]
            mock_publisher = MagicMock()
            mock_publisher.publish_batch = AsyncMock(return_value=published)
            mock_publisher.get_existing_urls = AsyncMock(return_value=set())
            mock_publisher.is_duplicate_url = MagicMock(return_value=False)
            mock_publisher_cls.return_value = mock_publisher

            orchestrator = NewsWorkflowOrchestrator(config=integration_config)
            result = await orchestrator.run()

            # Verify WorkflowResult structure
            assert isinstance(result, WorkflowResult)
            assert result.total_collected == 2
            assert result.total_extracted == 2
            assert result.total_summarized == 2
            assert result.total_published == 2
            assert result.started_at is not None
            assert result.finished_at is not None
            assert result.finished_at >= result.started_at
            assert result.elapsed_seconds >= 0

    @pytest.mark.asyncio
    async def test_正常系_抽出失敗でも処理継続(
        self,
        integration_config: NewsWorkflowConfig,
        sample_collected_articles: list[CollectedArticle],
        tmp_path: Path,
    ) -> None:
        """Test: workflow continues even when extraction fails for some articles."""
        integration_config.output.result_dir = str(tmp_path)

        with (
            patch("news.orchestrator.RSSCollector") as mock_collector_cls,
            patch("news.orchestrator.TrafilaturaExtractor") as mock_extractor_cls,
            patch("news.orchestrator.Summarizer") as mock_summarizer_cls,
            patch("news.orchestrator.Publisher") as mock_publisher_cls,
        ):
            articles = sample_collected_articles[:2]
            mock_collector = MagicMock()
            mock_collector.collect = AsyncMock(return_value=articles)
            mock_collector_cls.return_value = mock_collector

            # First article succeeds, second fails
            extracted_success = create_extracted_article(articles[0], success=True)
            extracted_fail = create_extracted_article(articles[1], success=False)

            mock_extractor = MagicMock()
            mock_extractor.extract = AsyncMock(
                side_effect=[extracted_success, extracted_fail]
            )
            mock_extractor_cls.return_value = mock_extractor

            # Only the successful extraction is summarized
            summarized = create_summarized_article(extracted_success)
            mock_summarizer = MagicMock()
            mock_summarizer.summarize_batch = AsyncMock(return_value=[summarized])
            mock_summarizer_cls.return_value = mock_summarizer

            published = create_published_article(summarized, 100)
            mock_publisher = MagicMock()
            mock_publisher.publish_batch = AsyncMock(return_value=[published])
            mock_publisher.get_existing_urls = AsyncMock(return_value=set())
            mock_publisher.is_duplicate_url = MagicMock(return_value=False)
            mock_publisher_cls.return_value = mock_publisher

            orchestrator = NewsWorkflowOrchestrator(config=integration_config)
            result = await orchestrator.run()

            # Verify extraction failure is recorded but workflow continues
            assert result.total_collected == 2
            assert result.total_extracted == 1
            assert len(result.extraction_failures) == 1
            assert result.extraction_failures[0].stage == "extraction"
            # Summarizer should only receive the successful extraction
            call_args = mock_summarizer.summarize_batch.call_args[0][0]
            assert len(call_args) == 1

    @pytest.mark.asyncio
    async def test_正常系_要約失敗でも処理継続(
        self,
        integration_config: NewsWorkflowConfig,
        sample_collected_articles: list[CollectedArticle],
        tmp_path: Path,
    ) -> None:
        """Test: workflow continues even when summarization fails for some articles."""
        integration_config.output.result_dir = str(tmp_path)

        with (
            patch("news.orchestrator.RSSCollector") as mock_collector_cls,
            patch("news.orchestrator.TrafilaturaExtractor") as mock_extractor_cls,
            patch("news.orchestrator.Summarizer") as mock_summarizer_cls,
            patch("news.orchestrator.Publisher") as mock_publisher_cls,
        ):
            articles = sample_collected_articles[:2]
            mock_collector = MagicMock()
            mock_collector.collect = AsyncMock(return_value=articles)
            mock_collector_cls.return_value = mock_collector

            extracted = [create_extracted_article(a) for a in articles]
            mock_extractor = MagicMock()
            mock_extractor.extract = AsyncMock(side_effect=extracted)
            mock_extractor_cls.return_value = mock_extractor

            # First summarization succeeds, second fails
            summarized_success = create_summarized_article(extracted[0], success=True)
            summarized_fail = create_summarized_article(extracted[1], success=False)

            mock_summarizer = MagicMock()
            mock_summarizer.summarize_batch = AsyncMock(
                return_value=[summarized_success, summarized_fail]
            )
            mock_summarizer_cls.return_value = mock_summarizer

            # Only the successful summary is published
            published = create_published_article(summarized_success, 100)
            mock_publisher = MagicMock()
            mock_publisher.publish_batch = AsyncMock(return_value=[published])
            mock_publisher.get_existing_urls = AsyncMock(return_value=set())
            mock_publisher.is_duplicate_url = MagicMock(return_value=False)
            mock_publisher_cls.return_value = mock_publisher

            orchestrator = NewsWorkflowOrchestrator(config=integration_config)
            result = await orchestrator.run()

            # Verify summarization failure is recorded but workflow continues
            assert result.total_collected == 2
            assert result.total_extracted == 2
            assert result.total_summarized == 1
            assert len(result.summarization_failures) == 1
            assert result.summarization_failures[0].stage == "summarization"
            # Publisher should only receive the successful summary
            call_args = mock_publisher.publish_batch.call_args[0][0]
            assert len(call_args) == 1


class TestWorkflowResultBuild:
    """Tests for WorkflowResult construction in orchestrator."""

    def test_正常系_件数が正確に集計される(
        self,
        integration_config: NewsWorkflowConfig,
        sample_sources: dict[str, ArticleSource],
    ) -> None:
        """Test: counts are calculated correctly in WorkflowResult."""
        with (
            patch("news.orchestrator.RSSCollector"),
            patch("news.orchestrator.TrafilaturaExtractor"),
            patch("news.orchestrator.Summarizer"),
            patch("news.orchestrator.Publisher"),
        ):
            orchestrator = NewsWorkflowOrchestrator(config=integration_config)

            now = datetime.now(tz=timezone.utc)
            collected = CollectedArticle(
                url="https://example.com/1",  # type: ignore[arg-type]
                title="Article 1",
                source=sample_sources["market"],
                collected_at=now,
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
                issue_number=100,
                issue_url="https://github.com/YH-05/quants/issues/100",
                publication_status=PublicationStatus.SUCCESS,
            )

            result = orchestrator._build_result(
                collected=[collected],
                extracted=[extracted],
                summarized=[summarized],
                published=[published],
                started_at=now,
                finished_at=now,
            )

            assert result.total_collected == 1
            assert result.total_extracted == 1
            assert result.total_summarized == 1
            assert result.total_published == 1
            assert result.total_duplicates == 0

    def test_正常系_失敗記録が正しく生成される(
        self,
        integration_config: NewsWorkflowConfig,
        sample_sources: dict[str, ArticleSource],
    ) -> None:
        """Test: failure records are correctly generated for each stage."""
        with (
            patch("news.orchestrator.RSSCollector"),
            patch("news.orchestrator.TrafilaturaExtractor"),
            patch("news.orchestrator.Summarizer"),
            patch("news.orchestrator.Publisher"),
        ):
            orchestrator = NewsWorkflowOrchestrator(config=integration_config)

            now = datetime.now(tz=timezone.utc)

            # Create collected articles
            collected1 = CollectedArticle(
                url="https://example.com/1",  # type: ignore[arg-type]
                title="Article 1",
                source=sample_sources["market"],
                collected_at=now,
            )
            collected2 = CollectedArticle(
                url="https://example.com/2",  # type: ignore[arg-type]
                title="Article 2",
                source=sample_sources["market"],
                collected_at=now,
            )
            collected3 = CollectedArticle(
                url="https://example.com/3",  # type: ignore[arg-type]
                title="Article 3",
                source=sample_sources["market"],
                collected_at=now,
            )

            # Create extraction results (one failure)
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
                error_message="Network error",
            )

            # Create summarization results (one failure)
            summary = StructuredSummary(
                overview="Test",
                key_points=["Point"],
                market_impact="Impact",
            )
            summarized_success = SummarizedArticle(
                extracted=extracted_success,
                summary=summary,
                summarization_status=SummarizationStatus.SUCCESS,
            )

            # Create a separate extracted article for summarization failure
            extracted_for_sum_fail = ExtractedArticle(
                collected=collected3,
                body_text="Content 3",
                extraction_status=ExtractionStatus.SUCCESS,
                extraction_method="trafilatura",
            )
            summarized_fail = SummarizedArticle(
                extracted=extracted_for_sum_fail,
                summary=None,
                summarization_status=SummarizationStatus.FAILED,
                error_message="API error",
            )

            # Create publication results (one failure)
            published_success = PublishedArticle(
                summarized=summarized_success,
                issue_number=100,
                issue_url="https://github.com/YH-05/quants/issues/100",
                publication_status=PublicationStatus.SUCCESS,
            )
            published_fail = PublishedArticle(
                summarized=summarized_success,  # Use same summarized for simplicity
                issue_number=None,
                issue_url=None,
                publication_status=PublicationStatus.FAILED,
                error_message="gh command failed",
            )

            result = orchestrator._build_result(
                collected=[collected1, collected2, collected3],
                extracted=[extracted_success, extracted_fail, extracted_for_sum_fail],
                summarized=[summarized_success, summarized_fail],
                published=[published_success, published_fail],
                started_at=now,
                finished_at=now,
            )

            # Verify failure records
            assert len(result.extraction_failures) == 1
            assert result.extraction_failures[0].stage == "extraction"
            assert result.extraction_failures[0].url == "https://example.com/2"
            assert result.extraction_failures[0].error == "Network error"

            assert len(result.summarization_failures) == 1
            assert result.summarization_failures[0].stage == "summarization"
            assert result.summarization_failures[0].error == "API error"

            assert len(result.publication_failures) == 1
            assert result.publication_failures[0].stage == "publication"
            assert result.publication_failures[0].error == "gh command failed"

    def test_正常系_処理時間が正しく計算される(
        self,
        integration_config: NewsWorkflowConfig,
    ) -> None:
        """Test: elapsed time is calculated correctly."""
        with (
            patch("news.orchestrator.RSSCollector"),
            patch("news.orchestrator.TrafilaturaExtractor"),
            patch("news.orchestrator.Summarizer"),
            patch("news.orchestrator.Publisher"),
        ):
            orchestrator = NewsWorkflowOrchestrator(config=integration_config)

            from datetime import timedelta

            started_at = datetime(2026, 1, 15, 10, 0, 0, tzinfo=timezone.utc)
            finished_at = started_at + timedelta(minutes=5, seconds=30)

            result = orchestrator._build_result(
                collected=[],
                extracted=[],
                summarized=[],
                published=[],
                started_at=started_at,
                finished_at=finished_at,
            )

            # 5 minutes 30 seconds = 330 seconds
            assert result.elapsed_seconds == 330.0
            assert result.started_at == started_at
            assert result.finished_at == finished_at


class TestStatusFilteringIntegration:
    """Integration tests for status filtering functionality."""

    @pytest.mark.asyncio
    async def test_正常系_複数ステータスでフィルタリング(
        self,
        integration_config: NewsWorkflowConfig,
        sample_collected_articles: list[CollectedArticle],
        tmp_path: Path,
    ) -> None:
        """Test: filtering with multiple statuses works correctly."""
        integration_config.output.result_dir = str(tmp_path)

        with (
            patch("news.orchestrator.RSSCollector") as mock_collector_cls,
            patch("news.orchestrator.TrafilaturaExtractor") as mock_extractor_cls,
            patch("news.orchestrator.Summarizer") as mock_summarizer_cls,
            patch("news.orchestrator.Publisher") as mock_publisher_cls,
        ):
            mock_collector = MagicMock()
            mock_collector.collect = AsyncMock(return_value=sample_collected_articles)
            mock_collector_cls.return_value = mock_collector

            mock_extractor = MagicMock()
            mock_extractor.extract = AsyncMock(
                side_effect=lambda a: create_extracted_article(a)
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

            orchestrator = NewsWorkflowOrchestrator(config=integration_config)
            # Filter to "index" (market) and "ai" (tech) statuses
            await orchestrator.run(statuses=["index", "ai"])

            # Should process market (2) + tech (1) = 3 articles
            assert mock_extractor.extract.call_count == 3

    @pytest.mark.asyncio
    async def test_正常系_存在しないステータスでフィルタリング(
        self,
        integration_config: NewsWorkflowConfig,
        sample_collected_articles: list[CollectedArticle],
        tmp_path: Path,
    ) -> None:
        """Test: filtering with non-existent status returns no articles."""
        integration_config.output.result_dir = str(tmp_path)

        with (
            patch("news.orchestrator.RSSCollector") as mock_collector_cls,
            patch("news.orchestrator.TrafilaturaExtractor") as mock_extractor_cls,
            patch("news.orchestrator.Summarizer") as mock_summarizer_cls,
            patch("news.orchestrator.Publisher") as mock_publisher_cls,
        ):
            mock_collector = MagicMock()
            mock_collector.collect = AsyncMock(return_value=sample_collected_articles)
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

            orchestrator = NewsWorkflowOrchestrator(config=integration_config)
            # Filter to non-existent status
            result = await orchestrator.run(statuses=["nonexistent"])

            # Should process 0 articles
            assert mock_extractor.extract.call_count == 0
            assert result.total_collected == 0


class TestDuplicateHandlingIntegration:
    """Integration tests for duplicate article handling."""

    @pytest.mark.asyncio
    async def test_正常系_重複記事がカウントされる(
        self,
        integration_config: NewsWorkflowConfig,
        sample_sources: dict[str, ArticleSource],
        tmp_path: Path,
    ) -> None:
        """Test: duplicate articles are correctly counted."""
        integration_config.output.result_dir = str(tmp_path)

        with (
            patch("news.orchestrator.RSSCollector") as mock_collector_cls,
            patch("news.orchestrator.TrafilaturaExtractor") as mock_extractor_cls,
            patch("news.orchestrator.Summarizer") as mock_summarizer_cls,
            patch("news.orchestrator.Publisher") as mock_publisher_cls,
        ):
            now = datetime.now(tz=timezone.utc)
            collected = CollectedArticle(
                url="https://example.com/article1",  # type: ignore[arg-type]
                title="Article 1",
                source=sample_sources["market"],
                collected_at=now,
            )

            mock_collector = MagicMock()
            mock_collector.collect = AsyncMock(return_value=[collected])
            mock_collector_cls.return_value = mock_collector

            extracted = create_extracted_article(collected)
            mock_extractor = MagicMock()
            mock_extractor.extract = AsyncMock(return_value=extracted)
            mock_extractor_cls.return_value = mock_extractor

            summarized = create_summarized_article(extracted)
            mock_summarizer = MagicMock()
            mock_summarizer.summarize_batch = AsyncMock(return_value=[summarized])
            mock_summarizer_cls.return_value = mock_summarizer

            # Mark as duplicate
            published_dup = create_published_article(
                summarized, issue_number=0, duplicate=True
            )
            mock_publisher = MagicMock()
            mock_publisher.publish_batch = AsyncMock(return_value=[published_dup])
            mock_publisher.get_existing_urls = AsyncMock(return_value=set())
            mock_publisher.is_duplicate_url = MagicMock(return_value=False)
            mock_publisher_cls.return_value = mock_publisher

            orchestrator = NewsWorkflowOrchestrator(config=integration_config)
            result = await orchestrator.run()

            # Verify duplicate is counted
            assert result.total_duplicates == 1
            assert result.total_published == 0
