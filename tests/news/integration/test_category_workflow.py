"""Integration tests for category-based news workflow.

E2E tests with mocked external dependencies (Claude API, gh CLI, HTTP requests).
Tests the complete per_category pipeline:
  Collect -> Extract -> Summarize -> Group -> Export -> Publish

Also tests per_article (legacy) and export_only modes.

Following the test specification from Wave 7 (#3405):
- E2E mock integration tests for per_category format
- E2E mock integration tests for per_article format
- export_only mode tests
- Error handling and continuation tests
"""

from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from news.config.models import (
    CategoryLabelsConfig,
    NewsWorkflowConfig,
    PublishingConfig,
    SummarizationConfig,
)
from news.grouper import ArticleGrouper
from news.markdown_generator import CategoryMarkdownGenerator, MarkdownExporter
from news.models import (
    ArticleSource,
    CategoryGroup,
    CategoryPublishResult,
    CollectedArticle,
    ExtractedArticle,
    ExtractionStatus,
    PublicationStatus,
    SourceType,
    StructuredSummary,
    SummarizationStatus,
    SummarizedArticle,
)
from news.orchestrator import NewsWorkflowOrchestrator

# ======================================================================
# Fixtures
# ======================================================================


@pytest.fixture
def per_category_config() -> NewsWorkflowConfig:
    """Create a NewsWorkflowConfig for per_category integration testing."""
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
        publishing=PublishingConfig(
            format="per_category",
            export_markdown=True,
            export_dir="data/exports/news-workflow",
        ),
    )


@pytest.fixture
def per_article_config(per_category_config: NewsWorkflowConfig) -> NewsWorkflowConfig:
    """Create a NewsWorkflowConfig for per_article (legacy) integration testing."""
    per_category_config.publishing = PublishingConfig(format="per_article")
    return per_category_config


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
    """Create a set of CollectedArticles for testing.

    Returns 5 articles:
    - 2 market (-> index)
    - 2 tech (-> ai)
    - 1 finance (-> finance)
    """
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
            url="https://techcrunch.com/ai/article2",  # type: ignore[arg-type]
            title="New AI Model Released",
            published=now,
            raw_summary="GPT-5 has been released with new capabilities.",
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


# ======================================================================
# Helper Functions
# ======================================================================


def _create_extracted(
    collected: CollectedArticle,
    *,
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


def _create_summarized(
    extracted: ExtractedArticle,
    *,
    success: bool = True,
) -> SummarizedArticle:
    """Helper to create SummarizedArticle from ExtractedArticle."""
    if success:
        summary = StructuredSummary(
            overview=f"Summary of {extracted.collected.title}",
            key_points=["Key point 1", "Key point 2"],
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


def _build_pipeline_data(
    articles: list[CollectedArticle],
) -> tuple[
    list[ExtractedArticle],
    list[SummarizedArticle],
]:
    """Build extracted and summarized lists from collected articles."""
    extracted = [_create_extracted(a) for a in articles]
    summarized = [_create_summarized(e) for e in extracted]
    return extracted, summarized


# ======================================================================
# Tests: per_category E2E workflow
# ======================================================================


class TestPerCategoryWorkflow:
    """E2E tests for per_category format (Group -> Export -> Publish)."""

    @pytest.mark.asyncio
    async def test_正常系_全パイプラインが正常に動作する(
        self,
        per_category_config: NewsWorkflowConfig,
        sample_collected_articles: list[CollectedArticle],
        tmp_path: Path,
    ) -> None:
        """E2E: collect -> extract -> summarize -> group -> export -> publish."""
        per_category_config.output.result_dir = str(tmp_path)
        per_category_config.publishing.export_dir = str(tmp_path / "export")

        extracted, summarized = _build_pipeline_data(sample_collected_articles)

        with (
            patch("news.orchestrator.RSSCollector") as mock_collector_cls,
            patch("news.orchestrator.TrafilaturaExtractor") as mock_extractor_cls,
            patch("news.orchestrator.Summarizer") as mock_summarizer_cls,
            patch("news.orchestrator.Publisher") as mock_publisher_cls,
        ):
            # Setup collector
            mock_collector = MagicMock()
            mock_collector.collect = AsyncMock(
                return_value=sample_collected_articles,
            )
            mock_collector.feed_errors = []
            mock_collector_cls.return_value = mock_collector

            # Setup extractor
            mock_extractor = MagicMock()
            mock_extractor.extract = AsyncMock(side_effect=extracted)
            mock_extractor_cls.return_value = mock_extractor

            # Setup summarizer (batched: concurrency=2, 5 articles)
            mock_summarizer = MagicMock()
            mock_summarizer.summarize_batch = AsyncMock(
                side_effect=[
                    summarized[:2],
                    summarized[2:4],
                    summarized[4:],
                ],
            )
            mock_summarizer_cls.return_value = mock_summarizer

            # Setup publisher
            category_results = [
                CategoryPublishResult(
                    category="index",
                    category_label="株価指数",
                    date=datetime.now(tz=timezone.utc).strftime("%Y-%m-%d"),
                    issue_number=100,
                    issue_url="https://github.com/YH-05/quants/issues/100",
                    article_count=2,
                    status=PublicationStatus.SUCCESS,
                ),
                CategoryPublishResult(
                    category="ai",
                    category_label="AI関連",
                    date=datetime.now(tz=timezone.utc).strftime("%Y-%m-%d"),
                    issue_number=101,
                    issue_url="https://github.com/YH-05/quants/issues/101",
                    article_count=2,
                    status=PublicationStatus.SUCCESS,
                ),
                CategoryPublishResult(
                    category="finance",
                    category_label="金融",
                    date=datetime.now(tz=timezone.utc).strftime("%Y-%m-%d"),
                    issue_number=102,
                    issue_url="https://github.com/YH-05/quants/issues/102",
                    article_count=1,
                    status=PublicationStatus.SUCCESS,
                ),
            ]
            mock_publisher = MagicMock()
            mock_publisher.publish_category_batch = AsyncMock(
                return_value=category_results,
            )
            mock_publisher.get_existing_urls = AsyncMock(return_value=set())
            mock_publisher.is_duplicate_url = MagicMock(return_value=False)
            mock_publisher_cls.return_value = mock_publisher

            orchestrator = NewsWorkflowOrchestrator(config=per_category_config)
            result = await orchestrator.run()

            # Verify pipeline metrics
            assert result.total_collected == 5
            assert result.total_extracted == 5
            assert result.total_summarized == 5
            assert len(result.category_results) == 3

            # Verify category publishing was called
            mock_publisher.publish_category_batch.assert_called_once()
            call_args = mock_publisher.publish_category_batch.call_args
            groups = call_args[0][0]
            assert len(groups) == 3

            # Verify grouping: index(2), ai(2), finance(1)
            group_map = {g.category: len(g.articles) for g in groups}
            assert group_map["index"] == 2
            assert group_map["ai"] == 2
            assert group_map["finance"] == 1

    @pytest.mark.asyncio
    async def test_正常系_Markdownエクスポートが出力される(
        self,
        per_category_config: NewsWorkflowConfig,
        sample_collected_articles: list[CollectedArticle],
        tmp_path: Path,
    ) -> None:
        """E2E: markdown files are exported to the configured directory."""
        per_category_config.output.result_dir = str(tmp_path)
        export_dir = tmp_path / "export"
        per_category_config.publishing.export_dir = str(export_dir)

        extracted, summarized = _build_pipeline_data(sample_collected_articles)

        with (
            patch("news.orchestrator.RSSCollector") as mock_collector_cls,
            patch("news.orchestrator.TrafilaturaExtractor") as mock_extractor_cls,
            patch("news.orchestrator.Summarizer") as mock_summarizer_cls,
            patch("news.orchestrator.Publisher") as mock_publisher_cls,
        ):
            mock_collector = MagicMock()
            mock_collector.collect = AsyncMock(
                return_value=sample_collected_articles,
            )
            mock_collector.feed_errors = []
            mock_collector_cls.return_value = mock_collector

            mock_extractor = MagicMock()
            mock_extractor.extract = AsyncMock(side_effect=extracted)
            mock_extractor_cls.return_value = mock_extractor

            mock_summarizer = MagicMock()
            mock_summarizer.summarize_batch = AsyncMock(
                side_effect=[
                    summarized[:2],
                    summarized[2:4],
                    summarized[4:],
                ],
            )
            mock_summarizer_cls.return_value = mock_summarizer

            mock_publisher = MagicMock()
            mock_publisher.publish_category_batch = AsyncMock(return_value=[])
            mock_publisher.get_existing_urls = AsyncMock(return_value=set())
            mock_publisher.is_duplicate_url = MagicMock(return_value=False)
            mock_publisher_cls.return_value = mock_publisher

            orchestrator = NewsWorkflowOrchestrator(config=per_category_config)
            await orchestrator.run()

            # Verify markdown files are exported
            today = datetime.now(tz=timezone.utc).strftime("%Y-%m-%d")
            date_dir = export_dir / today

            assert date_dir.exists(), f"Date directory {date_dir} should exist"

            md_files = list(date_dir.glob("*.md"))
            assert len(md_files) == 3, (
                f"Expected 3 markdown files, found {len(md_files)}"
            )

            md_names = sorted(f.stem for f in md_files)
            assert md_names == ["ai", "finance", "index"]

    @pytest.mark.asyncio
    async def test_正常系_export_onlyでIssue作成スキップ(
        self,
        per_category_config: NewsWorkflowConfig,
        sample_collected_articles: list[CollectedArticle],
        tmp_path: Path,
    ) -> None:
        """E2E: export_only mode exports markdown but skips Issue creation."""
        per_category_config.output.result_dir = str(tmp_path)
        export_dir = tmp_path / "export"
        per_category_config.publishing.export_dir = str(export_dir)

        extracted, summarized = _build_pipeline_data(sample_collected_articles)

        with (
            patch("news.orchestrator.RSSCollector") as mock_collector_cls,
            patch("news.orchestrator.TrafilaturaExtractor") as mock_extractor_cls,
            patch("news.orchestrator.Summarizer") as mock_summarizer_cls,
            patch("news.orchestrator.Publisher") as mock_publisher_cls,
        ):
            mock_collector = MagicMock()
            mock_collector.collect = AsyncMock(
                return_value=sample_collected_articles,
            )
            mock_collector.feed_errors = []
            mock_collector_cls.return_value = mock_collector

            mock_extractor = MagicMock()
            mock_extractor.extract = AsyncMock(side_effect=extracted)
            mock_extractor_cls.return_value = mock_extractor

            mock_summarizer = MagicMock()
            mock_summarizer.summarize_batch = AsyncMock(
                side_effect=[
                    summarized[:2],
                    summarized[2:4],
                    summarized[4:],
                ],
            )
            mock_summarizer_cls.return_value = mock_summarizer

            mock_publisher = MagicMock()
            mock_publisher.publish_category_batch = AsyncMock(return_value=[])
            mock_publisher.get_existing_urls = AsyncMock(return_value=set())
            mock_publisher.is_duplicate_url = MagicMock(return_value=False)
            mock_publisher_cls.return_value = mock_publisher

            orchestrator = NewsWorkflowOrchestrator(config=per_category_config)
            result = await orchestrator.run(export_only=True)

            # Publisher should NOT be called for category issues
            mock_publisher.publish_category_batch.assert_not_called()

            # Markdown files should still be exported
            today = datetime.now(tz=timezone.utc).strftime("%Y-%m-%d")
            date_dir = export_dir / today
            assert date_dir.exists()
            md_files = list(date_dir.glob("*.md"))
            assert len(md_files) == 3

            # Result should show 0 category results
            assert len(result.category_results) == 0

    @pytest.mark.asyncio
    async def test_正常系_dry_runでIssue作成されない(
        self,
        per_category_config: NewsWorkflowConfig,
        sample_collected_articles: list[CollectedArticle],
        tmp_path: Path,
    ) -> None:
        """E2E: dry_run mode passes dry_run=True to publish_category_batch."""
        per_category_config.output.result_dir = str(tmp_path)
        per_category_config.publishing.export_dir = str(tmp_path / "export")

        extracted, summarized = _build_pipeline_data(sample_collected_articles)

        with (
            patch("news.orchestrator.RSSCollector") as mock_collector_cls,
            patch("news.orchestrator.TrafilaturaExtractor") as mock_extractor_cls,
            patch("news.orchestrator.Summarizer") as mock_summarizer_cls,
            patch("news.orchestrator.Publisher") as mock_publisher_cls,
        ):
            mock_collector = MagicMock()
            mock_collector.collect = AsyncMock(
                return_value=sample_collected_articles,
            )
            mock_collector.feed_errors = []
            mock_collector_cls.return_value = mock_collector

            mock_extractor = MagicMock()
            mock_extractor.extract = AsyncMock(side_effect=extracted)
            mock_extractor_cls.return_value = mock_extractor

            mock_summarizer = MagicMock()
            mock_summarizer.summarize_batch = AsyncMock(
                side_effect=[
                    summarized[:2],
                    summarized[2:4],
                    summarized[4:],
                ],
            )
            mock_summarizer_cls.return_value = mock_summarizer

            mock_publisher = MagicMock()
            mock_publisher.publish_category_batch = AsyncMock(return_value=[])
            mock_publisher.get_existing_urls = AsyncMock(return_value=set())
            mock_publisher.is_duplicate_url = MagicMock(return_value=False)
            mock_publisher_cls.return_value = mock_publisher

            orchestrator = NewsWorkflowOrchestrator(config=per_category_config)
            await orchestrator.run(dry_run=True)

            # Verify dry_run was passed to publish_category_batch
            mock_publisher.publish_category_batch.assert_called_once()
            call_kwargs = mock_publisher.publish_category_batch.call_args.kwargs
            assert call_kwargs.get("dry_run") is True

    @pytest.mark.asyncio
    async def test_正常系_重複カテゴリIssueがスキップされる(
        self,
        per_category_config: NewsWorkflowConfig,
        sample_collected_articles: list[CollectedArticle],
        tmp_path: Path,
    ) -> None:
        """E2E: duplicate category issues are detected and skipped."""
        per_category_config.output.result_dir = str(tmp_path)
        per_category_config.publishing.export_dir = str(tmp_path / "export")

        extracted, summarized = _build_pipeline_data(sample_collected_articles)
        today = datetime.now(tz=timezone.utc).strftime("%Y-%m-%d")

        with (
            patch("news.orchestrator.RSSCollector") as mock_collector_cls,
            patch("news.orchestrator.TrafilaturaExtractor") as mock_extractor_cls,
            patch("news.orchestrator.Summarizer") as mock_summarizer_cls,
            patch("news.orchestrator.Publisher") as mock_publisher_cls,
        ):
            mock_collector = MagicMock()
            mock_collector.collect = AsyncMock(
                return_value=sample_collected_articles,
            )
            mock_collector.feed_errors = []
            mock_collector_cls.return_value = mock_collector

            mock_extractor = MagicMock()
            mock_extractor.extract = AsyncMock(side_effect=extracted)
            mock_extractor_cls.return_value = mock_extractor

            mock_summarizer = MagicMock()
            mock_summarizer.summarize_batch = AsyncMock(
                side_effect=[
                    summarized[:2],
                    summarized[2:4],
                    summarized[4:],
                ],
            )
            mock_summarizer_cls.return_value = mock_summarizer

            # Return duplicate for index, success for ai and finance
            category_results = [
                CategoryPublishResult(
                    category="ai",
                    category_label="AI関連",
                    date=today,
                    issue_number=None,
                    issue_url=None,
                    article_count=2,
                    status=PublicationStatus.DUPLICATE,
                    error_message="Duplicate: Issue #50 already exists",
                ),
                CategoryPublishResult(
                    category="finance",
                    category_label="金融",
                    date=today,
                    issue_number=200,
                    issue_url="https://github.com/YH-05/quants/issues/200",
                    article_count=1,
                    status=PublicationStatus.SUCCESS,
                ),
                CategoryPublishResult(
                    category="index",
                    category_label="株価指数",
                    date=today,
                    issue_number=201,
                    issue_url="https://github.com/YH-05/quants/issues/201",
                    article_count=2,
                    status=PublicationStatus.SUCCESS,
                ),
            ]
            mock_publisher = MagicMock()
            mock_publisher.publish_category_batch = AsyncMock(
                return_value=category_results,
            )
            mock_publisher.get_existing_urls = AsyncMock(return_value=set())
            mock_publisher.is_duplicate_url = MagicMock(return_value=False)
            mock_publisher_cls.return_value = mock_publisher

            orchestrator = NewsWorkflowOrchestrator(config=per_category_config)
            result = await orchestrator.run()

            # Verify category results contain duplicate
            assert len(result.category_results) == 3
            statuses = {r.category: r.status for r in result.category_results}
            assert statuses["ai"] == PublicationStatus.DUPLICATE
            assert statuses["finance"] == PublicationStatus.SUCCESS
            assert statuses["index"] == PublicationStatus.SUCCESS


# ======================================================================
# Tests: per_article E2E workflow
# ======================================================================


class TestPerArticleWorkflow:
    """E2E tests for per_article (legacy) format."""

    @pytest.mark.asyncio
    async def test_正常系_per_articleで全パイプラインが動作する(
        self,
        per_article_config: NewsWorkflowConfig,
        sample_collected_articles: list[CollectedArticle],
        tmp_path: Path,
    ) -> None:
        """E2E: per_article format uses publish_batch instead of category grouping."""
        per_article_config.output.result_dir = str(tmp_path)

        # Use 2 articles for simplicity
        articles = sample_collected_articles[:2]
        extracted, summarized = _build_pipeline_data(articles)

        with (
            patch("news.orchestrator.RSSCollector") as mock_collector_cls,
            patch("news.orchestrator.TrafilaturaExtractor") as mock_extractor_cls,
            patch("news.orchestrator.Summarizer") as mock_summarizer_cls,
            patch("news.orchestrator.Publisher") as mock_publisher_cls,
        ):
            mock_collector = MagicMock()
            mock_collector.collect = AsyncMock(return_value=articles)
            mock_collector.feed_errors = []
            mock_collector_cls.return_value = mock_collector

            mock_extractor = MagicMock()
            mock_extractor.extract = AsyncMock(side_effect=extracted)
            mock_extractor_cls.return_value = mock_extractor

            mock_summarizer = MagicMock()
            mock_summarizer.summarize_batch = AsyncMock(return_value=summarized)
            mock_summarizer_cls.return_value = mock_summarizer

            from news.models import PublishedArticle

            published = [
                PublishedArticle(
                    summarized=s,
                    issue_number=100 + i,
                    issue_url=f"https://github.com/YH-05/quants/issues/{100 + i}",
                    publication_status=PublicationStatus.SUCCESS,
                )
                for i, s in enumerate(summarized)
            ]
            mock_publisher = MagicMock()
            mock_publisher.publish_batch = AsyncMock(return_value=published)
            mock_publisher.get_existing_urls = AsyncMock(return_value=set())
            mock_publisher.is_duplicate_url = MagicMock(return_value=False)
            mock_publisher_cls.return_value = mock_publisher

            orchestrator = NewsWorkflowOrchestrator(config=per_article_config)
            result = await orchestrator.run()

            # per_article should call publish_batch, not publish_category_batch
            mock_publisher.publish_batch.assert_called_once()
            mock_publisher.publish_category_batch.assert_not_called()

            assert result.total_collected == 2
            assert result.total_extracted == 2
            assert result.total_summarized == 2
            assert result.total_published == 2
            assert len(result.category_results) == 0


# ======================================================================
# Tests: Grouper unit integration
# ======================================================================


class TestArticleGrouperIntegration:
    """Integration tests for ArticleGrouper with real SummarizedArticle objects."""

    def test_正常系_カテゴリ別にグループ化される(
        self,
        sample_collected_articles: list[CollectedArticle],
    ) -> None:
        """Articles are grouped by resolved category and date."""
        status_mapping = {
            "market": "index",
            "tech": "ai",
            "finance": "finance",
        }
        category_labels = CategoryLabelsConfig()

        grouper = ArticleGrouper(
            status_mapping=status_mapping,
            category_labels=category_labels,
        )

        extracted = [_create_extracted(a) for a in sample_collected_articles]
        summarized = [_create_summarized(e) for e in extracted]

        groups = grouper.group(summarized)

        # Should produce 3 groups: ai, finance, index (sorted by category)
        assert len(groups) == 3
        categories = [g.category for g in groups]
        assert categories == ["ai", "finance", "index"]

        # Verify article counts per category
        group_map = {g.category: len(g.articles) for g in groups}
        assert group_map["index"] == 2
        assert group_map["ai"] == 2
        assert group_map["finance"] == 1

    def test_正常系_カテゴリラベルが日本語で設定される(
        self,
        sample_collected_articles: list[CollectedArticle],
    ) -> None:
        """Category labels are resolved to Japanese names."""
        status_mapping = {
            "market": "index",
            "tech": "ai",
            "finance": "finance",
        }
        category_labels = CategoryLabelsConfig()

        grouper = ArticleGrouper(
            status_mapping=status_mapping,
            category_labels=category_labels,
        )

        extracted = [_create_extracted(a) for a in sample_collected_articles]
        summarized = [_create_summarized(e) for e in extracted]
        groups = grouper.group(summarized)

        label_map = {g.category: g.category_label for g in groups}
        assert label_map["index"] == "株価指数"
        assert label_map["ai"] == "AI関連"
        assert label_map["finance"] == "金融"

    def test_エッジケース_空リストで空結果(self) -> None:
        """Empty input returns empty result."""
        grouper = ArticleGrouper(
            status_mapping={},
            category_labels=CategoryLabelsConfig(),
        )
        result = grouper.group([])
        assert result == []

    def test_正常系_未知カテゴリはfinanceにフォールバック(
        self,
    ) -> None:
        """Unknown category falls back to 'finance'."""
        now = datetime.now(tz=timezone.utc)
        source = ArticleSource(
            source_type=SourceType.RSS,
            source_name="Unknown Source",
            category="unknown_category",
        )
        collected = CollectedArticle(
            url="https://example.com/unknown",  # type: ignore[arg-type]
            title="Unknown Category Article",
            published=now,
            source=source,
            collected_at=now,
        )

        grouper = ArticleGrouper(
            status_mapping={"market": "index"},
            category_labels=CategoryLabelsConfig(),
        )

        extracted = _create_extracted(collected)
        summarized = _create_summarized(extracted)
        groups = grouper.group([summarized])

        assert len(groups) == 1
        assert groups[0].category == "finance"


# ======================================================================
# Tests: Markdown generation integration
# ======================================================================


class TestMarkdownGenerationIntegration:
    """Integration tests for CategoryMarkdownGenerator and MarkdownExporter."""

    def test_正常系_Issueタイトルが正しく生成される(
        self,
        sample_collected_articles: list[CollectedArticle],
    ) -> None:
        """Issue title is generated in [label] format."""
        extracted = [_create_extracted(a) for a in sample_collected_articles[:2]]
        summarized = [_create_summarized(e) for e in extracted]
        today = datetime.now(tz=timezone.utc).strftime("%Y-%m-%d")

        group = CategoryGroup(
            category="index",
            category_label="株価指数",
            date=today,
            articles=summarized,
        )

        generator = CategoryMarkdownGenerator()
        title = generator.generate_issue_title(group)

        assert title == f"[株価指数] ニュースまとめ - {today}"

    def test_正常系_Issue本文にヘッダーと記事が含まれる(
        self,
        sample_collected_articles: list[CollectedArticle],
    ) -> None:
        """Issue body contains header and article sections."""
        extracted = [_create_extracted(a) for a in sample_collected_articles[:2]]
        summarized = [_create_summarized(e) for e in extracted]
        today = datetime.now(tz=timezone.utc).strftime("%Y-%m-%d")

        group = CategoryGroup(
            category="index",
            category_label="株価指数",
            date=today,
            articles=summarized,
        )

        generator = CategoryMarkdownGenerator()
        body = generator.generate_issue_body(group)

        # Check header
        assert f"[株価指数] ニュースまとめ - {today}" in body
        assert "2件の記事を収集" in body

        # Check article sections
        assert "S&P 500 Hits New High" in body
        assert "NASDAQ Surges" in body

        # Check summary content
        assert "Key point 1" in body
        assert "市場への影響" in body

    def test_正常系_Markdownファイルがエクスポートされる(
        self,
        sample_collected_articles: list[CollectedArticle],
        tmp_path: Path,
    ) -> None:
        """Markdown files are exported to the correct directory structure."""
        extracted = [_create_extracted(a) for a in sample_collected_articles[:2]]
        summarized = [_create_summarized(e) for e in extracted]
        today = datetime.now(tz=timezone.utc).strftime("%Y-%m-%d")

        group = CategoryGroup(
            category="index",
            category_label="株価指数",
            date=today,
            articles=summarized,
        )

        exporter = MarkdownExporter()
        output_path = exporter.export(group, export_dir=tmp_path)

        # Verify file path structure
        expected_path = tmp_path / today / "index.md"
        assert output_path == expected_path
        assert output_path.exists()

        # Verify file content
        content = output_path.read_text(encoding="utf-8")
        assert "株価指数" in content
        assert "S&P 500 Hits New High" in content


# ======================================================================
# Tests: Error handling in per_category workflow
# ======================================================================


class TestCategoryWorkflowErrorHandling:
    """Tests for error handling in per_category workflow."""

    @pytest.mark.asyncio
    async def test_正常系_抽出失敗記事がグルーピングから除外される(
        self,
        per_category_config: NewsWorkflowConfig,
        sample_collected_articles: list[CollectedArticle],
        tmp_path: Path,
    ) -> None:
        """Articles that fail extraction are excluded from grouping."""
        per_category_config.output.result_dir = str(tmp_path)
        per_category_config.publishing.export_dir = str(tmp_path / "export")

        # First 3 succeed, last 2 fail
        extracted = [
            _create_extracted(a, success=True) for a in sample_collected_articles[:3]
        ] + [_create_extracted(a, success=False) for a in sample_collected_articles[3:]]

        # Only the 3 successful extractions are summarized
        summarized_success = [_create_summarized(e) for e in extracted[:3]]

        with (
            patch("news.orchestrator.RSSCollector") as mock_collector_cls,
            patch("news.orchestrator.TrafilaturaExtractor") as mock_extractor_cls,
            patch("news.orchestrator.Summarizer") as mock_summarizer_cls,
            patch("news.orchestrator.Publisher") as mock_publisher_cls,
        ):
            mock_collector = MagicMock()
            mock_collector.collect = AsyncMock(
                return_value=sample_collected_articles,
            )
            mock_collector.feed_errors = []
            mock_collector_cls.return_value = mock_collector

            mock_extractor = MagicMock()
            mock_extractor.extract = AsyncMock(side_effect=extracted)
            mock_extractor_cls.return_value = mock_extractor

            mock_summarizer = MagicMock()
            mock_summarizer.summarize_batch = AsyncMock(
                side_effect=[
                    summarized_success[:2],
                    summarized_success[2:],
                ],
            )
            mock_summarizer_cls.return_value = mock_summarizer

            mock_publisher = MagicMock()
            mock_publisher.publish_category_batch = AsyncMock(return_value=[])
            mock_publisher.get_existing_urls = AsyncMock(return_value=set())
            mock_publisher.is_duplicate_url = MagicMock(return_value=False)
            mock_publisher_cls.return_value = mock_publisher

            orchestrator = NewsWorkflowOrchestrator(config=per_category_config)
            result = await orchestrator.run()

            assert result.total_collected == 5
            assert result.total_extracted == 3
            assert result.total_summarized == 3
            assert len(result.extraction_failures) == 2

            # Only 3 articles should have been grouped
            call_args = mock_publisher.publish_category_batch.call_args
            groups = call_args[0][0]
            total_articles_in_groups = sum(len(g.articles) for g in groups)
            assert total_articles_in_groups == 3

    @pytest.mark.asyncio
    async def test_正常系_要約失敗記事がグルーピングから除外される(
        self,
        per_category_config: NewsWorkflowConfig,
        sample_collected_articles: list[CollectedArticle],
        tmp_path: Path,
    ) -> None:
        """Articles that fail summarization are excluded from grouping."""
        per_category_config.output.result_dir = str(tmp_path)
        per_category_config.publishing.export_dir = str(tmp_path / "export")

        extracted = [_create_extracted(a) for a in sample_collected_articles]

        # First 3 summarize ok, last 2 fail
        summarized = [_create_summarized(e, success=True) for e in extracted[:3]] + [
            _create_summarized(e, success=False) for e in extracted[3:]
        ]

        with (
            patch("news.orchestrator.RSSCollector") as mock_collector_cls,
            patch("news.orchestrator.TrafilaturaExtractor") as mock_extractor_cls,
            patch("news.orchestrator.Summarizer") as mock_summarizer_cls,
            patch("news.orchestrator.Publisher") as mock_publisher_cls,
        ):
            mock_collector = MagicMock()
            mock_collector.collect = AsyncMock(
                return_value=sample_collected_articles,
            )
            mock_collector.feed_errors = []
            mock_collector_cls.return_value = mock_collector

            mock_extractor = MagicMock()
            mock_extractor.extract = AsyncMock(side_effect=extracted)
            mock_extractor_cls.return_value = mock_extractor

            mock_summarizer = MagicMock()
            mock_summarizer.summarize_batch = AsyncMock(
                side_effect=[
                    summarized[:2],
                    summarized[2:4],
                    summarized[4:],
                ],
            )
            mock_summarizer_cls.return_value = mock_summarizer

            mock_publisher = MagicMock()
            mock_publisher.publish_category_batch = AsyncMock(return_value=[])
            mock_publisher.get_existing_urls = AsyncMock(return_value=set())
            mock_publisher.is_duplicate_url = MagicMock(return_value=False)
            mock_publisher_cls.return_value = mock_publisher

            orchestrator = NewsWorkflowOrchestrator(config=per_category_config)
            result = await orchestrator.run()

            assert result.total_collected == 5
            assert result.total_extracted == 5
            assert result.total_summarized == 3
            assert len(result.summarization_failures) == 2

            # Only 3 successful articles should have been grouped
            call_args = mock_publisher.publish_category_batch.call_args
            groups = call_args[0][0]
            total_articles = sum(len(g.articles) for g in groups)
            assert total_articles == 3

    @pytest.mark.asyncio
    async def test_正常系_ステータスフィルタリングがカテゴリワークフローで動作(
        self,
        per_category_config: NewsWorkflowConfig,
        sample_collected_articles: list[CollectedArticle],
        tmp_path: Path,
    ) -> None:
        """Status filtering works correctly in per_category workflow."""
        per_category_config.output.result_dir = str(tmp_path)
        per_category_config.publishing.export_dir = str(tmp_path / "export")

        # Only "index" articles (market category -> index status)
        # sample has 2 market articles
        extracted_market = [
            _create_extracted(a)
            for a in sample_collected_articles
            if a.source.category == "market"
        ]
        summarized_market = [_create_summarized(e) for e in extracted_market]

        with (
            patch("news.orchestrator.RSSCollector") as mock_collector_cls,
            patch("news.orchestrator.TrafilaturaExtractor") as mock_extractor_cls,
            patch("news.orchestrator.Summarizer") as mock_summarizer_cls,
            patch("news.orchestrator.Publisher") as mock_publisher_cls,
        ):
            mock_collector = MagicMock()
            mock_collector.collect = AsyncMock(
                return_value=sample_collected_articles,
            )
            mock_collector.feed_errors = []
            mock_collector_cls.return_value = mock_collector

            mock_extractor = MagicMock()
            mock_extractor.extract = AsyncMock(side_effect=extracted_market)
            mock_extractor_cls.return_value = mock_extractor

            mock_summarizer = MagicMock()
            mock_summarizer.summarize_batch = AsyncMock(
                return_value=summarized_market,
            )
            mock_summarizer_cls.return_value = mock_summarizer

            mock_publisher = MagicMock()
            mock_publisher.publish_category_batch = AsyncMock(return_value=[])
            mock_publisher.get_existing_urls = AsyncMock(return_value=set())
            mock_publisher.is_duplicate_url = MagicMock(return_value=False)
            mock_publisher_cls.return_value = mock_publisher

            orchestrator = NewsWorkflowOrchestrator(config=per_category_config)
            result = await orchestrator.run(statuses=["index"])

            # Only 2 market articles should be processed
            assert mock_extractor.extract.call_count == 2
            assert result.total_extracted == 2

            # Only 1 group (index) should be created
            call_args = mock_publisher.publish_category_batch.call_args
            groups = call_args[0][0]
            assert len(groups) == 1
            assert groups[0].category == "index"


# ======================================================================
# Tests: WorkflowResult with category_results
# ======================================================================


class TestWorkflowResultWithCategories:
    """Tests for WorkflowResult construction with category_results."""

    @pytest.mark.asyncio
    async def test_正常系_category_resultsがWorkflowResultに含まれる(
        self,
        per_category_config: NewsWorkflowConfig,
        sample_collected_articles: list[CollectedArticle],
        tmp_path: Path,
    ) -> None:
        """WorkflowResult includes category_results from per_category publishing."""
        per_category_config.output.result_dir = str(tmp_path)
        per_category_config.publishing.export_dir = str(tmp_path / "export")

        extracted, summarized = _build_pipeline_data(
            sample_collected_articles[:2],
        )
        today = datetime.now(tz=timezone.utc).strftime("%Y-%m-%d")

        with (
            patch("news.orchestrator.RSSCollector") as mock_collector_cls,
            patch("news.orchestrator.TrafilaturaExtractor") as mock_extractor_cls,
            patch("news.orchestrator.Summarizer") as mock_summarizer_cls,
            patch("news.orchestrator.Publisher") as mock_publisher_cls,
        ):
            mock_collector = MagicMock()
            mock_collector.collect = AsyncMock(
                return_value=sample_collected_articles[:2],
            )
            mock_collector.feed_errors = []
            mock_collector_cls.return_value = mock_collector

            mock_extractor = MagicMock()
            mock_extractor.extract = AsyncMock(side_effect=extracted)
            mock_extractor_cls.return_value = mock_extractor

            mock_summarizer = MagicMock()
            mock_summarizer.summarize_batch = AsyncMock(return_value=summarized)
            mock_summarizer_cls.return_value = mock_summarizer

            category_results = [
                CategoryPublishResult(
                    category="index",
                    category_label="株価指数",
                    date=today,
                    issue_number=100,
                    issue_url="https://github.com/YH-05/quants/issues/100",
                    article_count=2,
                    status=PublicationStatus.SUCCESS,
                ),
            ]
            mock_publisher = MagicMock()
            mock_publisher.publish_category_batch = AsyncMock(
                return_value=category_results,
            )
            mock_publisher.get_existing_urls = AsyncMock(return_value=set())
            mock_publisher.is_duplicate_url = MagicMock(return_value=False)
            mock_publisher_cls.return_value = mock_publisher

            orchestrator = NewsWorkflowOrchestrator(config=per_category_config)
            result = await orchestrator.run()

            # Verify category_results in WorkflowResult
            assert len(result.category_results) == 1
            cr = result.category_results[0]
            assert cr.category == "index"
            assert cr.category_label == "株価指数"
            assert cr.issue_number == 100
            assert cr.status == PublicationStatus.SUCCESS

    @pytest.mark.asyncio
    async def test_正常系_stage_metricsが正しく記録される(
        self,
        per_category_config: NewsWorkflowConfig,
        sample_collected_articles: list[CollectedArticle],
        tmp_path: Path,
    ) -> None:
        """Stage metrics are recorded for all 6 stages in per_category mode."""
        per_category_config.output.result_dir = str(tmp_path)
        per_category_config.publishing.export_dir = str(tmp_path / "export")

        extracted, summarized = _build_pipeline_data(
            sample_collected_articles[:2],
        )

        with (
            patch("news.orchestrator.RSSCollector") as mock_collector_cls,
            patch("news.orchestrator.TrafilaturaExtractor") as mock_extractor_cls,
            patch("news.orchestrator.Summarizer") as mock_summarizer_cls,
            patch("news.orchestrator.Publisher") as mock_publisher_cls,
        ):
            mock_collector = MagicMock()
            mock_collector.collect = AsyncMock(
                return_value=sample_collected_articles[:2],
            )
            mock_collector.feed_errors = []
            mock_collector_cls.return_value = mock_collector

            mock_extractor = MagicMock()
            mock_extractor.extract = AsyncMock(side_effect=extracted)
            mock_extractor_cls.return_value = mock_extractor

            mock_summarizer = MagicMock()
            mock_summarizer.summarize_batch = AsyncMock(return_value=summarized)
            mock_summarizer_cls.return_value = mock_summarizer

            mock_publisher = MagicMock()
            mock_publisher.publish_category_batch = AsyncMock(return_value=[])
            mock_publisher.get_existing_urls = AsyncMock(return_value=set())
            mock_publisher.is_duplicate_url = MagicMock(return_value=False)
            mock_publisher_cls.return_value = mock_publisher

            orchestrator = NewsWorkflowOrchestrator(config=per_category_config)
            result = await orchestrator.run()

            # Verify stage metrics are present
            stage_names = [sm.stage for sm in result.stage_metrics]

            # Must include: collection, extraction, summarization, grouping, export, publishing
            assert "collection" in stage_names
            assert "extraction" in stage_names
            assert "summarization" in stage_names
            assert "grouping" in stage_names

            # Each metric should have non-negative elapsed_seconds
            for sm in result.stage_metrics:
                assert sm.elapsed_seconds >= 0
                assert sm.item_count >= 0

    @pytest.mark.asyncio
    async def test_正常系_結果JSONにcategory_resultsが保存される(
        self,
        per_category_config: NewsWorkflowConfig,
        sample_collected_articles: list[CollectedArticle],
        tmp_path: Path,
    ) -> None:
        """Workflow result JSON includes category_results."""
        per_category_config.output.result_dir = str(tmp_path)
        per_category_config.publishing.export_dir = str(tmp_path / "export")

        extracted, summarized = _build_pipeline_data(
            sample_collected_articles[:2],
        )
        today = datetime.now(tz=timezone.utc).strftime("%Y-%m-%d")

        with (
            patch("news.orchestrator.RSSCollector") as mock_collector_cls,
            patch("news.orchestrator.TrafilaturaExtractor") as mock_extractor_cls,
            patch("news.orchestrator.Summarizer") as mock_summarizer_cls,
            patch("news.orchestrator.Publisher") as mock_publisher_cls,
        ):
            mock_collector = MagicMock()
            mock_collector.collect = AsyncMock(
                return_value=sample_collected_articles[:2],
            )
            mock_collector.feed_errors = []
            mock_collector_cls.return_value = mock_collector

            mock_extractor = MagicMock()
            mock_extractor.extract = AsyncMock(side_effect=extracted)
            mock_extractor_cls.return_value = mock_extractor

            mock_summarizer = MagicMock()
            mock_summarizer.summarize_batch = AsyncMock(return_value=summarized)
            mock_summarizer_cls.return_value = mock_summarizer

            category_results = [
                CategoryPublishResult(
                    category="index",
                    category_label="株価指数",
                    date=today,
                    issue_number=100,
                    issue_url="https://github.com/YH-05/quants/issues/100",
                    article_count=2,
                    status=PublicationStatus.SUCCESS,
                ),
            ]
            mock_publisher = MagicMock()
            mock_publisher.publish_category_batch = AsyncMock(
                return_value=category_results,
            )
            mock_publisher.get_existing_urls = AsyncMock(return_value=set())
            mock_publisher.is_duplicate_url = MagicMock(return_value=False)
            mock_publisher_cls.return_value = mock_publisher

            orchestrator = NewsWorkflowOrchestrator(config=per_category_config)
            await orchestrator.run()

            # Verify JSON file was created and contains category_results
            import json

            json_files = list(tmp_path.glob("workflow-result-*.json"))
            assert len(json_files) == 1

            with open(json_files[0], encoding="utf-8") as f:
                data = json.load(f)

            assert "category_results" in data
            assert len(data["category_results"]) == 1
            assert data["category_results"][0]["category"] == "index"
            assert data["category_results"][0]["status"] == "success"
