"""Unit tests for orchestrator performance metrics.

Tests for stage-level processing time, domain extraction success rates,
and the StageMetrics/DomainExtractionRate models in WorkflowResult.

Issue: #3404 - [Wave6] パフォーマンス改善・メトリクス追加
"""

from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from news.config.models import NewsWorkflowConfig, PublishingConfig, SummarizationConfig
from news.models import (
    ArticleSource,
    CollectedArticle,
    DomainExtractionRate,
    ExtractedArticle,
    ExtractionStatus,
    PublicationStatus,
    PublishedArticle,
    SourceType,
    StageMetrics,
    StructuredSummary,
    SummarizationStatus,
    SummarizedArticle,
    WorkflowResult,
)

# --- Fixtures ---


@pytest.fixture
def sample_config() -> NewsWorkflowConfig:
    """Create a sample NewsWorkflowConfig for testing.

    Uses per_article format to simplify pipeline stages in tests.
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
        source_name="TechCrunch",
        category="tech",
    )


# --- StageMetrics Model Tests ---


class TestStageMetricsModel:
    """Tests for the StageMetrics Pydantic model."""

    def test_正常系_StageMetricsを生成できる(self) -> None:
        """StageMetrics should be constructable with required fields."""
        metrics = StageMetrics(
            stage="extraction",
            elapsed_seconds=12.5,
            item_count=20,
        )
        assert metrics.stage == "extraction"
        assert metrics.elapsed_seconds == 12.5
        assert metrics.item_count == 20

    def test_正常系_StageMetricsをJSONにシリアライズできる(self) -> None:
        """StageMetrics should serialize to JSON correctly."""
        import json

        metrics = StageMetrics(
            stage="summarization",
            elapsed_seconds=45.3,
            item_count=15,
        )
        data = json.loads(metrics.model_dump_json())
        assert data["stage"] == "summarization"
        assert data["elapsed_seconds"] == 45.3
        assert data["item_count"] == 15


# --- DomainExtractionRate Model Tests ---


class TestDomainExtractionRateModel:
    """Tests for the DomainExtractionRate Pydantic model."""

    def test_正常系_DomainExtractionRateを生成できる(self) -> None:
        """DomainExtractionRate should be constructable with required fields."""
        rate = DomainExtractionRate(
            domain="cnbc.com",
            total=10,
            success=8,
            failed=2,
            success_rate=80.0,
        )
        assert rate.domain == "cnbc.com"
        assert rate.total == 10
        assert rate.success == 8
        assert rate.failed == 2
        assert rate.success_rate == 80.0

    def test_正常系_DomainExtractionRateをJSONにシリアライズできる(self) -> None:
        """DomainExtractionRate should serialize to JSON correctly."""
        import json

        rate = DomainExtractionRate(
            domain="reuters.com",
            total=5,
            success=3,
            failed=2,
            success_rate=60.0,
        )
        data = json.loads(rate.model_dump_json())
        assert data["domain"] == "reuters.com"
        assert data["success_rate"] == 60.0


# --- WorkflowResult with Metrics Tests ---


class TestWorkflowResultMetrics:
    """Tests for WorkflowResult stage_metrics and domain_extraction_rates fields."""

    def test_正常系_WorkflowResultにstage_metricsフィールドがある(self) -> None:
        """WorkflowResult should have stage_metrics field with default empty list."""
        result = WorkflowResult(
            total_collected=10,
            total_extracted=8,
            total_summarized=7,
            total_published=5,
            total_duplicates=0,
            extraction_failures=[],
            summarization_failures=[],
            publication_failures=[],
            started_at=datetime(2026, 1, 15, 10, 0, 0, tzinfo=timezone.utc),
            finished_at=datetime(2026, 1, 15, 10, 5, 0, tzinfo=timezone.utc),
            elapsed_seconds=300.0,
            published_articles=[],
        )
        assert result.stage_metrics == []

    def test_正常系_WorkflowResultにdomain_extraction_ratesフィールドがある(
        self,
    ) -> None:
        """WorkflowResult should have domain_extraction_rates field."""
        result = WorkflowResult(
            total_collected=10,
            total_extracted=8,
            total_summarized=7,
            total_published=5,
            total_duplicates=0,
            extraction_failures=[],
            summarization_failures=[],
            publication_failures=[],
            started_at=datetime(2026, 1, 15, 10, 0, 0, tzinfo=timezone.utc),
            finished_at=datetime(2026, 1, 15, 10, 5, 0, tzinfo=timezone.utc),
            elapsed_seconds=300.0,
            published_articles=[],
        )
        assert result.domain_extraction_rates == []

    def test_正常系_WorkflowResultにメトリクスを設定できる(self) -> None:
        """WorkflowResult should accept stage_metrics and domain_extraction_rates."""
        stage_metrics = [
            StageMetrics(stage="collection", elapsed_seconds=5.0, item_count=10),
            StageMetrics(stage="extraction", elapsed_seconds=15.0, item_count=10),
        ]
        domain_rates = [
            DomainExtractionRate(
                domain="cnbc.com",
                total=5,
                success=4,
                failed=1,
                success_rate=80.0,
            ),
        ]
        result = WorkflowResult(
            total_collected=10,
            total_extracted=8,
            total_summarized=7,
            total_published=5,
            total_duplicates=0,
            extraction_failures=[],
            summarization_failures=[],
            publication_failures=[],
            started_at=datetime(2026, 1, 15, 10, 0, 0, tzinfo=timezone.utc),
            finished_at=datetime(2026, 1, 15, 10, 5, 0, tzinfo=timezone.utc),
            elapsed_seconds=300.0,
            published_articles=[],
            stage_metrics=stage_metrics,
            domain_extraction_rates=domain_rates,
        )
        assert len(result.stage_metrics) == 2
        assert result.stage_metrics[0].stage == "collection"
        assert len(result.domain_extraction_rates) == 1
        assert result.domain_extraction_rates[0].domain == "cnbc.com"


# --- Orchestrator Stage Metrics Tests ---


class TestOrchestratorStageMetrics:
    """Tests for stage timing metrics in orchestrator.run()."""

    @pytest.mark.asyncio
    async def test_正常系_runがstage_metricsを含むWorkflowResultを返す(
        self,
        sample_config: NewsWorkflowConfig,
        sample_source_market: ArticleSource,
    ) -> None:
        """run() should include stage_metrics in WorkflowResult."""
        from news.orchestrator import NewsWorkflowOrchestrator

        collected = CollectedArticle(
            url="https://www.cnbc.com/article/1",  # type: ignore[arg-type]
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
            mock_collector = MagicMock()
            mock_collector.collect = AsyncMock(return_value=[collected])
            mock_collector.feed_errors = []
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

            # Should have stage metrics for collection, extraction,
            # summarization, publishing (4 stages in per_article mode)
            assert len(result.stage_metrics) == 4
            stage_names = [sm.stage for sm in result.stage_metrics]
            assert "collection" in stage_names
            assert "extraction" in stage_names
            assert "summarization" in stage_names
            assert "publishing" in stage_names

            # All elapsed_seconds should be >= 0
            for sm in result.stage_metrics:
                assert sm.elapsed_seconds >= 0
                assert sm.item_count >= 0

    @pytest.mark.asyncio
    async def test_正常系_記事なしでもstage_metricsが設定される(
        self,
        sample_config: NewsWorkflowConfig,
    ) -> None:
        """When no articles, stage_metrics should still include collection stage."""
        from news.orchestrator import NewsWorkflowOrchestrator

        with (
            patch("news.orchestrator.RSSCollector") as mock_collector_cls,
            patch("news.orchestrator.TrafilaturaExtractor") as mock_extractor_cls,
            patch("news.orchestrator.Summarizer") as mock_summarizer_cls,
            patch("news.orchestrator.Publisher") as mock_publisher_cls,
        ):
            mock_collector = MagicMock()
            mock_collector.collect = AsyncMock(return_value=[])
            mock_collector.feed_errors = []
            mock_collector_cls.return_value = mock_collector

            mock_extractor = MagicMock()
            mock_extractor_cls.return_value = mock_extractor

            mock_summarizer = MagicMock()
            mock_summarizer_cls.return_value = mock_summarizer

            mock_publisher = MagicMock()
            mock_publisher.get_existing_urls = AsyncMock(return_value=set())
            mock_publisher.is_duplicate_url = MagicMock(return_value=False)
            mock_publisher_cls.return_value = mock_publisher

            orchestrator = NewsWorkflowOrchestrator(config=sample_config)
            result = await orchestrator.run()

            # At least collection stage should be measured
            assert len(result.stage_metrics) >= 1
            assert result.stage_metrics[0].stage == "collection"


# --- Orchestrator Domain Extraction Rate Tests ---


class TestOrchestratorDomainExtractionRates:
    """Tests for domain-level extraction success rate computation."""

    @pytest.mark.asyncio
    async def test_正常系_domain_extraction_ratesがWorkflowResultに含まれる(
        self,
        sample_config: NewsWorkflowConfig,
        sample_source_market: ArticleSource,
    ) -> None:
        """run() should include domain_extraction_rates in WorkflowResult."""
        from news.orchestrator import NewsWorkflowOrchestrator

        collected1 = CollectedArticle(
            url="https://www.cnbc.com/article/1",  # type: ignore[arg-type]
            title="CNBC Article 1",
            source=sample_source_market,
            collected_at=datetime.now(tz=timezone.utc),
        )
        collected2 = CollectedArticle(
            url="https://www.cnbc.com/article/2",  # type: ignore[arg-type]
            title="CNBC Article 2",
            source=sample_source_market,
            collected_at=datetime.now(tz=timezone.utc),
        )
        collected3 = CollectedArticle(
            url="https://techcrunch.com/article/3",  # type: ignore[arg-type]
            title="TechCrunch Article",
            source=sample_source_market,
            collected_at=datetime.now(tz=timezone.utc),
        )

        # CNBC: 1 success, 1 fail; TechCrunch: 1 success
        extracted1 = ExtractedArticle(
            collected=collected1,
            body_text="Content 1",
            extraction_status=ExtractionStatus.SUCCESS,
            extraction_method="trafilatura",
        )
        extracted2 = ExtractedArticle(
            collected=collected2,
            body_text=None,
            extraction_status=ExtractionStatus.FAILED,
            extraction_method="trafilatura",
            error_message="Extraction failed",
        )
        extracted3 = ExtractedArticle(
            collected=collected3,
            body_text="Content 3",
            extraction_status=ExtractionStatus.SUCCESS,
            extraction_method="trafilatura",
        )

        summary = StructuredSummary(
            overview="Test",
            key_points=["Point"],
            market_impact="Impact",
        )
        summarized1 = SummarizedArticle(
            extracted=extracted1,
            summary=summary,
            summarization_status=SummarizationStatus.SUCCESS,
        )
        summarized3 = SummarizedArticle(
            extracted=extracted3,
            summary=summary,
            summarization_status=SummarizationStatus.SUCCESS,
        )

        with (
            patch("news.orchestrator.RSSCollector") as mock_collector_cls,
            patch("news.orchestrator.TrafilaturaExtractor") as mock_extractor_cls,
            patch("news.orchestrator.Summarizer") as mock_summarizer_cls,
            patch("news.orchestrator.Publisher") as mock_publisher_cls,
        ):
            mock_collector = MagicMock()
            mock_collector.collect = AsyncMock(
                return_value=[collected1, collected2, collected3]
            )
            mock_collector.feed_errors = []
            mock_collector_cls.return_value = mock_collector

            mock_extractor = MagicMock()
            mock_extractor.extract = AsyncMock(
                side_effect=[extracted1, extracted2, extracted3]
            )
            mock_extractor_cls.return_value = mock_extractor

            mock_summarizer = MagicMock()
            mock_summarizer.summarize_batch = AsyncMock(
                return_value=[summarized1, summarized3]
            )
            mock_summarizer_cls.return_value = mock_summarizer

            mock_publisher = MagicMock()
            mock_publisher.publish_batch = AsyncMock(return_value=[])
            mock_publisher.get_existing_urls = AsyncMock(return_value=set())
            mock_publisher.is_duplicate_url = MagicMock(return_value=False)
            mock_publisher_cls.return_value = mock_publisher

            orchestrator = NewsWorkflowOrchestrator(config=sample_config)
            result = await orchestrator.run()

            # Should have domain extraction rates
            assert len(result.domain_extraction_rates) == 2

            # Find rates by domain
            rates_by_domain = {r.domain: r for r in result.domain_extraction_rates}

            # CNBC: 2 total, 1 success, 1 failed (www. stripped)
            assert "cnbc.com" in rates_by_domain
            cnbc = rates_by_domain["cnbc.com"]
            assert cnbc.total == 2
            assert cnbc.success == 1
            assert cnbc.failed == 1
            assert cnbc.success_rate == 50.0

            # TechCrunch: 1 total, 1 success, 0 failed
            assert "techcrunch.com" in rates_by_domain
            tc = rates_by_domain["techcrunch.com"]
            assert tc.total == 1
            assert tc.success == 1
            assert tc.failed == 0
            assert tc.success_rate == 100.0


class TestComputeDomainExtractionRates:
    """Tests for _compute_domain_extraction_rates() method."""

    def test_正常系_空リストで空の結果を返す(
        self,
        sample_config: NewsWorkflowConfig,
    ) -> None:
        """Empty extraction list should return empty rates."""
        from news.orchestrator import NewsWorkflowOrchestrator

        with (
            patch("news.orchestrator.RSSCollector"),
            patch("news.orchestrator.TrafilaturaExtractor"),
            patch("news.orchestrator.Summarizer"),
            patch("news.orchestrator.Publisher"),
        ):
            orchestrator = NewsWorkflowOrchestrator(config=sample_config)
            rates = orchestrator._compute_domain_extraction_rates([])
            assert rates == []

    def test_正常系_wwwプレフィックスが除去される(
        self,
        sample_config: NewsWorkflowConfig,
        sample_source_market: ArticleSource,
    ) -> None:
        """www. prefix should be stripped from domain for grouping."""
        from news.orchestrator import NewsWorkflowOrchestrator

        collected = CollectedArticle(
            url="https://www.example.com/article/1",  # type: ignore[arg-type]
            title="Article",
            source=sample_source_market,
            collected_at=datetime.now(tz=timezone.utc),
        )
        extracted = ExtractedArticle(
            collected=collected,
            body_text="Content",
            extraction_status=ExtractionStatus.SUCCESS,
            extraction_method="trafilatura",
        )

        with (
            patch("news.orchestrator.RSSCollector"),
            patch("news.orchestrator.TrafilaturaExtractor"),
            patch("news.orchestrator.Summarizer"),
            patch("news.orchestrator.Publisher"),
        ):
            orchestrator = NewsWorkflowOrchestrator(config=sample_config)
            rates = orchestrator._compute_domain_extraction_rates([extracted])

            assert len(rates) == 1
            assert rates[0].domain == "example.com"

    def test_正常系_複数ドメインが正しく集計される(
        self,
        sample_config: NewsWorkflowConfig,
        sample_source_market: ArticleSource,
    ) -> None:
        """Multiple domains should be correctly aggregated."""
        from news.orchestrator import NewsWorkflowOrchestrator

        articles: list[ExtractedArticle] = []
        # 3 articles from cnbc.com: 2 success, 1 fail
        for i in range(3):
            collected = CollectedArticle(
                url=f"https://www.cnbc.com/article/{i}",  # type: ignore[arg-type]
                title=f"CNBC {i}",
                source=sample_source_market,
                collected_at=datetime.now(tz=timezone.utc),
            )
            status = ExtractionStatus.SUCCESS if i < 2 else ExtractionStatus.FAILED
            articles.append(
                ExtractedArticle(
                    collected=collected,
                    body_text="Content" if status == ExtractionStatus.SUCCESS else None,
                    extraction_status=status,
                    extraction_method="trafilatura",
                    error_message=None
                    if status == ExtractionStatus.SUCCESS
                    else "Failed",
                )
            )

        # 2 articles from bbc.com: all success
        for i in range(2):
            collected = CollectedArticle(
                url=f"https://bbc.com/news/{i}",  # type: ignore[arg-type]
                title=f"BBC {i}",
                source=sample_source_market,
                collected_at=datetime.now(tz=timezone.utc),
            )
            articles.append(
                ExtractedArticle(
                    collected=collected,
                    body_text="Content",
                    extraction_status=ExtractionStatus.SUCCESS,
                    extraction_method="trafilatura",
                )
            )

        with (
            patch("news.orchestrator.RSSCollector"),
            patch("news.orchestrator.TrafilaturaExtractor"),
            patch("news.orchestrator.Summarizer"),
            patch("news.orchestrator.Publisher"),
        ):
            orchestrator = NewsWorkflowOrchestrator(config=sample_config)
            rates = orchestrator._compute_domain_extraction_rates(articles)

            assert len(rates) == 2
            rates_by_domain = {r.domain: r for r in rates}

            cnbc = rates_by_domain["cnbc.com"]
            assert cnbc.total == 3
            assert cnbc.success == 2
            assert cnbc.failed == 1
            assert cnbc.success_rate == 66.7

            bbc = rates_by_domain["bbc.com"]
            assert bbc.total == 2
            assert bbc.success == 2
            assert bbc.failed == 0
            assert bbc.success_rate == 100.0


# --- Stage Metrics Display Tests ---


class TestStageMetricsDisplay:
    """Tests for stage metrics display in the final summary output."""

    @pytest.mark.asyncio
    async def test_正常系_ステージ別処理時間がコンソールに表示される(
        self,
        sample_config: NewsWorkflowConfig,
        sample_source_market: ArticleSource,
        capsys: pytest.CaptureFixture[str],
    ) -> None:
        """Final summary should display stage timing information."""
        from news.orchestrator import NewsWorkflowOrchestrator

        collected = CollectedArticle(
            url="https://www.cnbc.com/article/1",  # type: ignore[arg-type]
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
            mock_collector = MagicMock()
            mock_collector.collect = AsyncMock(return_value=[collected])
            mock_collector.feed_errors = []
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
            await orchestrator.run()

            captured = capsys.readouterr()
            assert "ステージ別処理時間" in captured.out
            assert "collection:" in captured.out
            assert "extraction:" in captured.out
            assert "summarization:" in captured.out
            assert "publishing:" in captured.out


# --- Domain Extraction Rate Display Tests ---


class TestDomainExtractionRateDisplay:
    """Tests for domain extraction rate display in the final summary output."""

    @pytest.mark.asyncio
    async def test_正常系_ドメイン別抽出成功率がコンソールに表示される(
        self,
        sample_config: NewsWorkflowConfig,
        sample_source_market: ArticleSource,
        capsys: pytest.CaptureFixture[str],
    ) -> None:
        """Final summary should display domain extraction success rate."""
        from news.orchestrator import NewsWorkflowOrchestrator

        collected = CollectedArticle(
            url="https://www.cnbc.com/article/1",  # type: ignore[arg-type]
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
            mock_collector = MagicMock()
            mock_collector.collect = AsyncMock(return_value=[collected])
            mock_collector.feed_errors = []
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
            await orchestrator.run()

            captured = capsys.readouterr()
            assert "ドメイン別抽出成功率" in captured.out
            assert "cnbc.com" in captured.out
            assert "100%" in captured.out


# --- Build Result Tests ---


class TestBuildResultMetrics:
    """Tests for _build_result() with metrics parameters."""

    def test_正常系_build_resultにstage_metricsが渡される(
        self,
        sample_config: NewsWorkflowConfig,
    ) -> None:
        """_build_result should accept and pass stage_metrics to WorkflowResult."""
        from news.orchestrator import NewsWorkflowOrchestrator

        with (
            patch("news.orchestrator.RSSCollector"),
            patch("news.orchestrator.TrafilaturaExtractor"),
            patch("news.orchestrator.Summarizer"),
            patch("news.orchestrator.Publisher"),
        ):
            orchestrator = NewsWorkflowOrchestrator(config=sample_config)

            metrics = [
                StageMetrics(stage="collection", elapsed_seconds=2.0, item_count=5),
            ]
            result = orchestrator._build_result(
                collected=[],
                extracted=[],
                summarized=[],
                published=[],
                started_at=datetime.now(tz=timezone.utc),
                finished_at=datetime.now(tz=timezone.utc),
                stage_metrics=metrics,
            )

            assert len(result.stage_metrics) == 1
            assert result.stage_metrics[0].stage == "collection"

    def test_正常系_build_resultにdomain_extraction_ratesが渡される(
        self,
        sample_config: NewsWorkflowConfig,
    ) -> None:
        """_build_result should accept domain_extraction_rates."""
        from news.orchestrator import NewsWorkflowOrchestrator

        with (
            patch("news.orchestrator.RSSCollector"),
            patch("news.orchestrator.TrafilaturaExtractor"),
            patch("news.orchestrator.Summarizer"),
            patch("news.orchestrator.Publisher"),
        ):
            orchestrator = NewsWorkflowOrchestrator(config=sample_config)

            rates = [
                DomainExtractionRate(
                    domain="cnbc.com",
                    total=3,
                    success=2,
                    failed=1,
                    success_rate=66.7,
                ),
            ]
            result = orchestrator._build_result(
                collected=[],
                extracted=[],
                summarized=[],
                published=[],
                started_at=datetime.now(tz=timezone.utc),
                finished_at=datetime.now(tz=timezone.utc),
                domain_extraction_rates=rates,
            )

            assert len(result.domain_extraction_rates) == 1
            assert result.domain_extraction_rates[0].domain == "cnbc.com"

    def test_正常系_build_resultのメトリクスデフォルトは空リスト(
        self,
        sample_config: NewsWorkflowConfig,
    ) -> None:
        """_build_result should default metrics to empty lists."""
        from news.orchestrator import NewsWorkflowOrchestrator

        with (
            patch("news.orchestrator.RSSCollector"),
            patch("news.orchestrator.TrafilaturaExtractor"),
            patch("news.orchestrator.Summarizer"),
            patch("news.orchestrator.Publisher"),
        ):
            orchestrator = NewsWorkflowOrchestrator(config=sample_config)

            result = orchestrator._build_result(
                collected=[],
                extracted=[],
                summarized=[],
                published=[],
                started_at=datetime.now(tz=timezone.utc),
                finished_at=datetime.now(tz=timezone.utc),
            )

            assert result.stage_metrics == []
            assert result.domain_extraction_rates == []
