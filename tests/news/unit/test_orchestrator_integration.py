"""Unit tests for orchestrator integration with category-based publishing.

Tests the expanded pipeline: Collect -> Extract -> Summarize -> Group -> Export -> Publish.
Verifies --format per-category, --format per-article, and --export-only behavior.

Issue: #3402 - Orchestrator統合・CLIオプション追加
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
from news.models import (
    ArticleSource,
    CategoryGroup,
    CategoryPublishResult,
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

# --- Fixtures ---


@pytest.fixture
def sample_config() -> NewsWorkflowConfig:
    """Create a sample NewsWorkflowConfig for testing."""
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
        publishing=PublishingConfig(
            format="per_category",
            export_markdown=True,
            export_dir="data/exports/news-workflow",
        ),
        category_labels=CategoryLabelsConfig(),
    )


@pytest.fixture
def sample_config_per_article() -> NewsWorkflowConfig:
    """Create a sample config with per_article format."""
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
        publishing=PublishingConfig(
            format="per_article",
            export_markdown=False,
            export_dir="data/exports/news-workflow",
        ),
        category_labels=CategoryLabelsConfig(),
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


def _make_collected(url: str, title: str, source: ArticleSource) -> CollectedArticle:
    """Helper to create a CollectedArticle."""
    return CollectedArticle(
        url=url,  # type: ignore[arg-type]
        title=title,
        source=source,
        collected_at=datetime.now(tz=timezone.utc),
        published=datetime(2026, 2, 9, 12, 0, 0, tzinfo=timezone.utc),
    )


def _make_extracted(collected: CollectedArticle) -> ExtractedArticle:
    """Helper to create an ExtractedArticle."""
    return ExtractedArticle(
        collected=collected,
        body_text="Full article content here...",
        extraction_status=ExtractionStatus.SUCCESS,
        extraction_method="trafilatura",
    )


def _make_summarized(extracted: ExtractedArticle) -> SummarizedArticle:
    """Helper to create a SummarizedArticle."""
    return SummarizedArticle(
        extracted=extracted,
        summary=StructuredSummary(
            overview="Markets rallied today",
            key_points=["S&P 500 up 1%", "Tech leads gains"],
            market_impact="Bullish sentiment continues",
        ),
        summarization_status=SummarizationStatus.SUCCESS,
    )


# --- Tests ---


class TestOrchestratorPerCategoryFormat:
    """Tests for per-category format in the orchestrator."""

    @pytest.mark.asyncio
    async def test_正常系_per_categoryフォーマットでグルーピングと公開が実行される(
        self,
        sample_config: NewsWorkflowConfig,
        sample_source_market: ArticleSource,
    ) -> None:
        """Per-category format should group articles and use publish_category_batch.

        Given:
            - Config with format="per_category"
            - 2 articles collected and summarized
        When:
            - orchestrator.run() is called
        Then:
            - ArticleGrouper.group() is called with summarized articles
            - Publisher.publish_category_batch() is called with groups
            - Publisher.publish_batch() is NOT called
        """
        from news.orchestrator import NewsWorkflowOrchestrator

        collected1 = _make_collected(
            "https://www.cnbc.com/article/1", "Article 1", sample_source_market
        )
        collected2 = _make_collected(
            "https://www.cnbc.com/article/2", "Article 2", sample_source_market
        )

        extracted1 = _make_extracted(collected1)
        extracted2 = _make_extracted(collected2)

        summarized1 = _make_summarized(extracted1)
        summarized2 = _make_summarized(extracted2)

        with (
            patch("news.orchestrator.RSSCollector") as mock_collector_cls,
            patch("news.orchestrator.TrafilaturaExtractor") as mock_extractor_cls,
            patch("news.orchestrator.Summarizer") as mock_summarizer_cls,
            patch("news.orchestrator.Publisher") as mock_publisher_cls,
            patch("news.orchestrator.ArticleGrouper") as mock_grouper_cls,
            patch("news.orchestrator.MarkdownExporter") as mock_exporter_cls,
        ):
            # Setup collector
            mock_collector = MagicMock()
            mock_collector.collect = AsyncMock(return_value=[collected1, collected2])
            mock_collector.feed_errors = []
            mock_collector_cls.return_value = mock_collector

            # Setup extractor
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

            # Setup summarizer
            mock_summarizer = MagicMock()
            mock_summarizer.summarize_batch = AsyncMock(
                return_value=[summarized1, summarized2]
            )
            mock_summarizer_cls.return_value = mock_summarizer

            # Setup publisher
            mock_publisher = MagicMock()
            mock_publisher.get_existing_urls = AsyncMock(return_value=set())
            mock_publisher.is_duplicate_url = MagicMock(return_value=False)
            mock_publisher.publish_batch = AsyncMock(return_value=[])
            mock_publisher.publish_category_batch = AsyncMock(
                return_value=[
                    CategoryPublishResult(
                        category="index",
                        category_label="株価指数",
                        date="2026-02-09",
                        issue_number=100,
                        issue_url="https://github.com/YH-05/quants/issues/100",
                        article_count=2,
                        status=PublicationStatus.SUCCESS,
                    )
                ]
            )
            mock_publisher_cls.return_value = mock_publisher

            # Setup grouper
            mock_grouper = MagicMock()
            groups = [
                CategoryGroup(
                    category="index",
                    category_label="株価指数",
                    date="2026-02-09",
                    articles=[summarized1, summarized2],
                )
            ]
            mock_grouper.group = MagicMock(return_value=groups)
            mock_grouper_cls.return_value = mock_grouper

            # Setup exporter
            mock_exporter = MagicMock()
            mock_exporter.export = MagicMock(
                return_value=Path("data/exports/news-workflow/2026-02-09/index.md")
            )
            mock_exporter_cls.return_value = mock_exporter

            orchestrator = NewsWorkflowOrchestrator(config=sample_config)
            result = await orchestrator.run()

            # Verify: grouper was called
            mock_grouper.group.assert_called_once()

            # Verify: publish_category_batch was called (not publish_batch)
            mock_publisher.publish_category_batch.assert_called_once()
            mock_publisher.publish_batch.assert_not_called()

            # Verify: category_results in WorkflowResult
            assert len(result.category_results) == 1
            assert result.category_results[0].category == "index"
            assert result.category_results[0].issue_number == 100

    @pytest.mark.asyncio
    async def test_正常系_per_categoryでMarkdownエクスポートが実行される(
        self,
        sample_config: NewsWorkflowConfig,
        sample_source_market: ArticleSource,
    ) -> None:
        """Per-category format with export_markdown=True should call MarkdownExporter.

        Given:
            - Config with format="per_category" and export_markdown=True
            - 1 article collected and summarized
        When:
            - orchestrator.run() is called
        Then:
            - MarkdownExporter.export() is called for each group
        """
        from news.orchestrator import NewsWorkflowOrchestrator

        collected1 = _make_collected(
            "https://www.cnbc.com/article/1", "Article 1", sample_source_market
        )
        extracted1 = _make_extracted(collected1)
        summarized1 = _make_summarized(extracted1)

        with (
            patch("news.orchestrator.RSSCollector") as mock_collector_cls,
            patch("news.orchestrator.TrafilaturaExtractor") as mock_extractor_cls,
            patch("news.orchestrator.Summarizer") as mock_summarizer_cls,
            patch("news.orchestrator.Publisher") as mock_publisher_cls,
            patch("news.orchestrator.ArticleGrouper") as mock_grouper_cls,
            patch("news.orchestrator.MarkdownExporter") as mock_exporter_cls,
        ):
            mock_collector = MagicMock()
            mock_collector.collect = AsyncMock(return_value=[collected1])
            mock_collector.feed_errors = []
            mock_collector_cls.return_value = mock_collector

            mock_extractor = MagicMock()
            mock_extractor.extract = AsyncMock(return_value=extracted1)
            mock_extractor_cls.return_value = mock_extractor

            mock_summarizer = MagicMock()
            mock_summarizer.summarize_batch = AsyncMock(return_value=[summarized1])
            mock_summarizer_cls.return_value = mock_summarizer

            mock_publisher = MagicMock()
            mock_publisher.get_existing_urls = AsyncMock(return_value=set())
            mock_publisher.is_duplicate_url = MagicMock(return_value=False)
            mock_publisher.publish_category_batch = AsyncMock(
                return_value=[
                    CategoryPublishResult(
                        category="index",
                        category_label="株価指数",
                        date="2026-02-09",
                        issue_number=101,
                        issue_url="https://github.com/YH-05/quants/issues/101",
                        article_count=1,
                        status=PublicationStatus.SUCCESS,
                    )
                ]
            )
            mock_publisher_cls.return_value = mock_publisher

            group = CategoryGroup(
                category="index",
                category_label="株価指数",
                date="2026-02-09",
                articles=[summarized1],
            )
            mock_grouper = MagicMock()
            mock_grouper.group = MagicMock(return_value=[group])
            mock_grouper_cls.return_value = mock_grouper

            mock_exporter = MagicMock()
            mock_exporter.export = MagicMock(
                return_value=Path("data/exports/news-workflow/2026-02-09/index.md")
            )
            mock_exporter_cls.return_value = mock_exporter

            orchestrator = NewsWorkflowOrchestrator(config=sample_config)
            await orchestrator.run()

            # Verify: exporter was called for the group
            mock_exporter.export.assert_called_once_with(
                group, export_dir=Path("data/exports/news-workflow")
            )


class TestOrchestratorPerArticleFormat:
    """Tests for per-article format in the orchestrator (legacy mode)."""

    @pytest.mark.asyncio
    async def test_正常系_per_articleフォーマットで旧方式の公開が実行される(
        self,
        sample_config_per_article: NewsWorkflowConfig,
        sample_source_market: ArticleSource,
    ) -> None:
        """Per-article format should use existing publish_batch (not category-based).

        Given:
            - Config with format="per_article"
            - 2 articles collected and summarized
        When:
            - orchestrator.run() is called
        Then:
            - Publisher.publish_batch() is called (not publish_category_batch)
            - ArticleGrouper is NOT used
        """
        from news.orchestrator import NewsWorkflowOrchestrator

        collected1 = _make_collected(
            "https://www.cnbc.com/article/1", "Article 1", sample_source_market
        )
        collected2 = _make_collected(
            "https://www.cnbc.com/article/2", "Article 2", sample_source_market
        )

        extracted1 = _make_extracted(collected1)
        extracted2 = _make_extracted(collected2)

        summarized1 = _make_summarized(extracted1)
        summarized2 = _make_summarized(extracted2)

        published1 = PublishedArticle(
            summarized=summarized1,
            issue_number=200,
            issue_url="https://github.com/YH-05/quants/issues/200",
            publication_status=PublicationStatus.SUCCESS,
        )
        published2 = PublishedArticle(
            summarized=summarized2,
            issue_number=201,
            issue_url="https://github.com/YH-05/quants/issues/201",
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
            mock_collector.feed_errors = []
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
            mock_summarizer.summarize_batch = AsyncMock(
                return_value=[summarized1, summarized2]
            )
            mock_summarizer_cls.return_value = mock_summarizer

            mock_publisher = MagicMock()
            mock_publisher.get_existing_urls = AsyncMock(return_value=set())
            mock_publisher.is_duplicate_url = MagicMock(return_value=False)
            mock_publisher.publish_batch = AsyncMock(
                return_value=[published1, published2]
            )
            mock_publisher.publish_category_batch = AsyncMock(return_value=[])
            mock_publisher_cls.return_value = mock_publisher

            orchestrator = NewsWorkflowOrchestrator(config=sample_config_per_article)
            result = await orchestrator.run()

            # Verify: publish_batch was called (legacy per-article)
            mock_publisher.publish_batch.assert_called_once()

            # Verify: publish_category_batch was NOT called
            mock_publisher.publish_category_batch.assert_not_called()

            # Verify: published articles in result
            assert result.total_published == 2


class TestOrchestratorExportOnly:
    """Tests for --export-only mode in the orchestrator."""

    @pytest.mark.asyncio
    async def test_正常系_export_onlyでMarkdownエクスポートのみ実行される(
        self,
        sample_config: NewsWorkflowConfig,
        sample_source_market: ArticleSource,
    ) -> None:
        """Export-only mode should export markdown but skip Issue creation.

        Given:
            - Config with format="per_category" and export_only=True
            - 1 article collected and summarized
        When:
            - orchestrator.run(export_only=True) is called
        Then:
            - MarkdownExporter.export() is called
            - Publisher.publish_category_batch() is NOT called
            - Publisher.publish_batch() is NOT called
        """
        from news.orchestrator import NewsWorkflowOrchestrator

        collected1 = _make_collected(
            "https://www.cnbc.com/article/1", "Article 1", sample_source_market
        )
        extracted1 = _make_extracted(collected1)
        summarized1 = _make_summarized(extracted1)

        with (
            patch("news.orchestrator.RSSCollector") as mock_collector_cls,
            patch("news.orchestrator.TrafilaturaExtractor") as mock_extractor_cls,
            patch("news.orchestrator.Summarizer") as mock_summarizer_cls,
            patch("news.orchestrator.Publisher") as mock_publisher_cls,
            patch("news.orchestrator.ArticleGrouper") as mock_grouper_cls,
            patch("news.orchestrator.MarkdownExporter") as mock_exporter_cls,
        ):
            mock_collector = MagicMock()
            mock_collector.collect = AsyncMock(return_value=[collected1])
            mock_collector.feed_errors = []
            mock_collector_cls.return_value = mock_collector

            mock_extractor = MagicMock()
            mock_extractor.extract = AsyncMock(return_value=extracted1)
            mock_extractor_cls.return_value = mock_extractor

            mock_summarizer = MagicMock()
            mock_summarizer.summarize_batch = AsyncMock(return_value=[summarized1])
            mock_summarizer_cls.return_value = mock_summarizer

            mock_publisher = MagicMock()
            mock_publisher.get_existing_urls = AsyncMock(return_value=set())
            mock_publisher.is_duplicate_url = MagicMock(return_value=False)
            mock_publisher.publish_batch = AsyncMock(return_value=[])
            mock_publisher.publish_category_batch = AsyncMock(return_value=[])
            mock_publisher_cls.return_value = mock_publisher

            group = CategoryGroup(
                category="index",
                category_label="株価指数",
                date="2026-02-09",
                articles=[summarized1],
            )
            mock_grouper = MagicMock()
            mock_grouper.group = MagicMock(return_value=[group])
            mock_grouper_cls.return_value = mock_grouper

            mock_exporter = MagicMock()
            mock_exporter.export = MagicMock(
                return_value=Path("data/exports/news-workflow/2026-02-09/index.md")
            )
            mock_exporter_cls.return_value = mock_exporter

            orchestrator = NewsWorkflowOrchestrator(config=sample_config)
            result = await orchestrator.run(export_only=True)

            # Verify: exporter was called
            mock_exporter.export.assert_called_once()

            # Verify: neither publish method was called
            mock_publisher.publish_category_batch.assert_not_called()
            mock_publisher.publish_batch.assert_not_called()

            # Verify: result has no published articles
            assert result.total_published == 0

    @pytest.mark.asyncio
    async def test_正常系_export_onlyとdry_runの組み合わせが正しく動作する(
        self,
        sample_config: NewsWorkflowConfig,
        sample_source_market: ArticleSource,
    ) -> None:
        """Export-only with dry_run should still export but skip publishing.

        Given:
            - export_only=True and dry_run=True
        When:
            - orchestrator.run() is called
        Then:
            - Both export_only and dry_run work together
            - Publishing is completely skipped
        """
        from news.orchestrator import NewsWorkflowOrchestrator

        collected1 = _make_collected(
            "https://www.cnbc.com/article/1", "Article 1", sample_source_market
        )
        extracted1 = _make_extracted(collected1)
        summarized1 = _make_summarized(extracted1)

        with (
            patch("news.orchestrator.RSSCollector") as mock_collector_cls,
            patch("news.orchestrator.TrafilaturaExtractor") as mock_extractor_cls,
            patch("news.orchestrator.Summarizer") as mock_summarizer_cls,
            patch("news.orchestrator.Publisher") as mock_publisher_cls,
            patch("news.orchestrator.ArticleGrouper") as mock_grouper_cls,
            patch("news.orchestrator.MarkdownExporter") as mock_exporter_cls,
        ):
            mock_collector = MagicMock()
            mock_collector.collect = AsyncMock(return_value=[collected1])
            mock_collector.feed_errors = []
            mock_collector_cls.return_value = mock_collector

            mock_extractor = MagicMock()
            mock_extractor.extract = AsyncMock(return_value=extracted1)
            mock_extractor_cls.return_value = mock_extractor

            mock_summarizer = MagicMock()
            mock_summarizer.summarize_batch = AsyncMock(return_value=[summarized1])
            mock_summarizer_cls.return_value = mock_summarizer

            mock_publisher = MagicMock()
            mock_publisher.get_existing_urls = AsyncMock(return_value=set())
            mock_publisher.is_duplicate_url = MagicMock(return_value=False)
            mock_publisher_cls.return_value = mock_publisher

            group = CategoryGroup(
                category="index",
                category_label="株価指数",
                date="2026-02-09",
                articles=[summarized1],
            )
            mock_grouper = MagicMock()
            mock_grouper.group = MagicMock(return_value=[group])
            mock_grouper_cls.return_value = mock_grouper

            mock_exporter = MagicMock()
            mock_exporter.export = MagicMock(
                return_value=Path("data/exports/news-workflow/2026-02-09/index.md")
            )
            mock_exporter_cls.return_value = mock_exporter

            orchestrator = NewsWorkflowOrchestrator(config=sample_config)
            result = await orchestrator.run(dry_run=True, export_only=True)

            # Verify: exporter called, publisher not called
            mock_exporter.export.assert_called_once()
            mock_publisher.publish_batch.assert_not_called()
            mock_publisher.publish_category_batch.assert_not_called()

            assert result.total_published == 0


class TestOrchestratorCategoryResults:
    """Tests for category_results in WorkflowResult."""

    @pytest.mark.asyncio
    async def test_正常系_WorkflowResultにcategory_resultsが含まれる(
        self,
        sample_config: NewsWorkflowConfig,
        sample_source_market: ArticleSource,
        sample_source_tech: ArticleSource,
    ) -> None:
        """WorkflowResult should include category_results from per-category publishing.

        Given:
            - Config with format="per_category"
            - Articles from 2 different categories
        When:
            - orchestrator.run() is called
        Then:
            - WorkflowResult.category_results has entries for each category
        """
        from news.orchestrator import NewsWorkflowOrchestrator

        collected1 = _make_collected(
            "https://www.cnbc.com/article/1", "Market Article", sample_source_market
        )
        collected2 = _make_collected(
            "https://techcrunch.com/article/1", "Tech Article", sample_source_tech
        )

        extracted1 = _make_extracted(collected1)
        extracted2 = _make_extracted(collected2)

        summarized1 = _make_summarized(extracted1)
        summarized2 = _make_summarized(extracted2)

        category_results = [
            CategoryPublishResult(
                category="index",
                category_label="株価指数",
                date="2026-02-09",
                issue_number=100,
                issue_url="https://github.com/YH-05/quants/issues/100",
                article_count=1,
                status=PublicationStatus.SUCCESS,
            ),
            CategoryPublishResult(
                category="ai",
                category_label="AI関連",
                date="2026-02-09",
                issue_number=101,
                issue_url="https://github.com/YH-05/quants/issues/101",
                article_count=1,
                status=PublicationStatus.SUCCESS,
            ),
        ]

        with (
            patch("news.orchestrator.RSSCollector") as mock_collector_cls,
            patch("news.orchestrator.TrafilaturaExtractor") as mock_extractor_cls,
            patch("news.orchestrator.Summarizer") as mock_summarizer_cls,
            patch("news.orchestrator.Publisher") as mock_publisher_cls,
            patch("news.orchestrator.ArticleGrouper") as mock_grouper_cls,
            patch("news.orchestrator.MarkdownExporter") as mock_exporter_cls,
        ):
            mock_collector = MagicMock()
            mock_collector.collect = AsyncMock(return_value=[collected1, collected2])
            mock_collector.feed_errors = []
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
            mock_summarizer.summarize_batch = AsyncMock(
                return_value=[summarized1, summarized2]
            )
            mock_summarizer_cls.return_value = mock_summarizer

            mock_publisher = MagicMock()
            mock_publisher.get_existing_urls = AsyncMock(return_value=set())
            mock_publisher.is_duplicate_url = MagicMock(return_value=False)
            mock_publisher.publish_category_batch = AsyncMock(
                return_value=category_results
            )
            mock_publisher_cls.return_value = mock_publisher

            groups = [
                CategoryGroup(
                    category="index",
                    category_label="株価指数",
                    date="2026-02-09",
                    articles=[summarized1],
                ),
                CategoryGroup(
                    category="ai",
                    category_label="AI関連",
                    date="2026-02-09",
                    articles=[summarized2],
                ),
            ]
            mock_grouper = MagicMock()
            mock_grouper.group = MagicMock(return_value=groups)
            mock_grouper_cls.return_value = mock_grouper

            mock_exporter = MagicMock()
            mock_exporter.export = MagicMock(return_value=Path("export.md"))
            mock_exporter_cls.return_value = mock_exporter

            orchestrator = NewsWorkflowOrchestrator(config=sample_config)
            result = await orchestrator.run()

            # Verify: category_results has 2 entries
            assert len(result.category_results) == 2
            assert result.category_results[0].category == "index"
            assert result.category_results[1].category == "ai"

    @pytest.mark.asyncio
    async def test_正常系_per_articleでcategory_resultsが空リスト(
        self,
        sample_config_per_article: NewsWorkflowConfig,
        sample_source_market: ArticleSource,
    ) -> None:
        """Per-article format should have empty category_results.

        Given:
            - Config with format="per_article"
        When:
            - orchestrator.run() is called
        Then:
            - WorkflowResult.category_results is empty list
        """
        from news.orchestrator import NewsWorkflowOrchestrator

        collected1 = _make_collected(
            "https://www.cnbc.com/article/1", "Article 1", sample_source_market
        )
        extracted1 = _make_extracted(collected1)
        summarized1 = _make_summarized(extracted1)

        published1 = PublishedArticle(
            summarized=summarized1,
            issue_number=200,
            issue_url="https://github.com/YH-05/quants/issues/200",
            publication_status=PublicationStatus.SUCCESS,
        )

        with (
            patch("news.orchestrator.RSSCollector") as mock_collector_cls,
            patch("news.orchestrator.TrafilaturaExtractor") as mock_extractor_cls,
            patch("news.orchestrator.Summarizer") as mock_summarizer_cls,
            patch("news.orchestrator.Publisher") as mock_publisher_cls,
        ):
            mock_collector = MagicMock()
            mock_collector.collect = AsyncMock(return_value=[collected1])
            mock_collector.feed_errors = []
            mock_collector_cls.return_value = mock_collector

            mock_extractor = MagicMock()
            mock_extractor.extract = AsyncMock(return_value=extracted1)
            mock_extractor_cls.return_value = mock_extractor

            mock_summarizer = MagicMock()
            mock_summarizer.summarize_batch = AsyncMock(return_value=[summarized1])
            mock_summarizer_cls.return_value = mock_summarizer

            mock_publisher = MagicMock()
            mock_publisher.get_existing_urls = AsyncMock(return_value=set())
            mock_publisher.is_duplicate_url = MagicMock(return_value=False)
            mock_publisher.publish_batch = AsyncMock(return_value=[published1])
            mock_publisher_cls.return_value = mock_publisher

            orchestrator = NewsWorkflowOrchestrator(config=sample_config_per_article)
            result = await orchestrator.run()

            # Verify: category_results is empty for per-article format
            assert result.category_results == []
