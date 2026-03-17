"""Unit tests for early duplicate check in NewsWorkflowOrchestrator.

Verifies that duplicate articles are excluded before phase 2 (extraction)
and that the WorkflowResult correctly reflects early duplicate counts.

Issue: #3082 - 重複チェック前倒しの検証テスト
"""

from datetime import datetime, timezone
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

# --- Fixtures ---


@pytest.fixture
def sample_config() -> NewsWorkflowConfig:
    """Create a sample NewsWorkflowConfig for testing.

    Uses per_article format to test legacy per-article publishing pipeline.
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


# --- Tests ---


class TestEarlyDuplicateCheck:
    """Tests for early duplicate check functionality in the orchestrator.

    Verifies that:
    1. Duplicate articles are excluded before extraction (phase 2)
    2. All-duplicate scenarios result in early return with empty WorkflowResult
    3. Early duplicate count is correctly reflected in WorkflowResult
    """

    @pytest.mark.asyncio
    async def test_正常系_重複記事がフェーズ2前に除外される(
        self,
        sample_config: NewsWorkflowConfig,
        sample_source_market: ArticleSource,
    ) -> None:
        """Duplicate articles should be excluded before extraction phase.

        Given:
            - RSSCollector returns 3 articles
            - Publisher.get_existing_urls() returns a set containing 1 of those URLs
        When:
            - orchestrator.run() is called
        Then:
            - Only 2 non-duplicate articles are passed to the extractor
            - The duplicate article is not processed in phase 2
        """
        from news.orchestrator import NewsWorkflowOrchestrator

        # Create 3 collected articles, one of which is a duplicate
        collected_new_1 = CollectedArticle(
            url="https://www.cnbc.com/article/new-1",  # type: ignore[arg-type]
            title="New Article 1",
            source=sample_source_market,
            collected_at=datetime.now(tz=timezone.utc),
        )
        collected_new_2 = CollectedArticle(
            url="https://www.cnbc.com/article/new-2",  # type: ignore[arg-type]
            title="New Article 2",
            source=sample_source_market,
            collected_at=datetime.now(tz=timezone.utc),
        )
        collected_duplicate = CollectedArticle(
            url="https://www.cnbc.com/article/existing",  # type: ignore[arg-type]
            title="Existing Article (duplicate)",
            source=sample_source_market,
            collected_at=datetime.now(tz=timezone.utc),
        )

        with (
            patch("news.orchestrator.RSSCollector") as mock_collector_cls,
            patch("news.orchestrator.TrafilaturaExtractor") as mock_extractor_cls,
            patch("news.orchestrator.Summarizer") as mock_summarizer_cls,
            patch("news.orchestrator.Publisher") as mock_publisher_cls,
        ):
            # Setup collector to return 3 articles
            mock_collector = MagicMock()
            mock_collector.collect = AsyncMock(
                return_value=[collected_new_1, collected_new_2, collected_duplicate]
            )
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

            # Setup summarizer (returns empty to simplify test)
            mock_summarizer = MagicMock()
            mock_summarizer.summarize_batch = AsyncMock(return_value=[])
            mock_summarizer_cls.return_value = mock_summarizer

            # Setup publisher with existing URL set
            mock_publisher = MagicMock()
            mock_publisher.publish_batch = AsyncMock(return_value=[])
            existing_urls = {"https://www.cnbc.com/article/existing"}
            mock_publisher.get_existing_urls = AsyncMock(return_value=existing_urls)
            mock_publisher.is_duplicate_url = MagicMock(
                side_effect=lambda url, urls: url in urls
            )
            mock_publisher_cls.return_value = mock_publisher

            orchestrator = NewsWorkflowOrchestrator(config=sample_config)
            await orchestrator.run()

            # Verify: only 2 non-duplicate articles reach extraction
            assert mock_extractor.extract.call_count == 2

            # Verify: the duplicate article was NOT passed to extraction
            extracted_urls = {
                str(call.args[0].url) for call in mock_extractor.extract.call_args_list
            }
            assert "https://www.cnbc.com/article/existing/" not in extracted_urls

    @pytest.mark.asyncio
    async def test_正常系_重複除外後に記事が0件で早期リターン(
        self,
        sample_config: NewsWorkflowConfig,
        sample_source_market: ArticleSource,
    ) -> None:
        """When all articles are duplicates, empty WorkflowResult should be returned.

        Given:
            - RSSCollector returns 2 articles
            - Publisher.get_existing_urls() returns a set containing ALL those URLs
        When:
            - orchestrator.run() is called
        Then:
            - An empty WorkflowResult is returned (total_collected=0)
            - Extractor is never called (no articles reach phase 2)
        """
        from news.orchestrator import NewsWorkflowOrchestrator

        collected1 = CollectedArticle(
            url="https://www.cnbc.com/article/dup-1",  # type: ignore[arg-type]
            title="Duplicate Article 1",
            source=sample_source_market,
            collected_at=datetime.now(tz=timezone.utc),
        )
        collected2 = CollectedArticle(
            url="https://www.cnbc.com/article/dup-2",  # type: ignore[arg-type]
            title="Duplicate Article 2",
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
            mock_extractor.extract = AsyncMock()
            mock_extractor_cls.return_value = mock_extractor

            mock_summarizer = MagicMock()
            mock_summarizer_cls.return_value = mock_summarizer

            # All URLs are existing (duplicates)
            mock_publisher = MagicMock()
            existing_urls = {
                "https://www.cnbc.com/article/dup-1",
                "https://www.cnbc.com/article/dup-2",
            }
            mock_publisher.get_existing_urls = AsyncMock(return_value=existing_urls)
            mock_publisher.is_duplicate_url = MagicMock(
                side_effect=lambda url, urls: url in urls
            )
            mock_publisher_cls.return_value = mock_publisher

            orchestrator = NewsWorkflowOrchestrator(config=sample_config)
            result = await orchestrator.run()

            # Verify: empty WorkflowResult is returned
            assert isinstance(result, WorkflowResult)
            assert result.total_collected == 0
            assert result.total_extracted == 0
            assert result.total_summarized == 0
            assert result.total_published == 0

            # Verify: extractor was never called
            mock_extractor.extract.assert_not_called()

    @pytest.mark.asyncio
    async def test_正常系_重複件数がWorkflowResultに反映される(
        self,
        sample_config: NewsWorkflowConfig,
        sample_source_market: ArticleSource,
    ) -> None:
        """total_early_duplicates in WorkflowResult should reflect early dedup count.

        Given:
            - RSSCollector returns 4 articles
            - Publisher.get_existing_urls() returns a set containing 2 of those URLs
        When:
            - orchestrator.run() is called
        Then:
            - WorkflowResult.total_early_duplicates == 2
            - Only 2 non-duplicate articles reach extraction
        """
        from news.orchestrator import NewsWorkflowOrchestrator

        collected_new_1 = CollectedArticle(
            url="https://www.cnbc.com/article/a",  # type: ignore[arg-type]
            title="New A",
            source=sample_source_market,
            collected_at=datetime.now(tz=timezone.utc),
        )
        collected_new_2 = CollectedArticle(
            url="https://www.cnbc.com/article/b",  # type: ignore[arg-type]
            title="New B",
            source=sample_source_market,
            collected_at=datetime.now(tz=timezone.utc),
        )
        collected_dup_1 = CollectedArticle(
            url="https://www.cnbc.com/article/dup-x",  # type: ignore[arg-type]
            title="Duplicate X",
            source=sample_source_market,
            collected_at=datetime.now(tz=timezone.utc),
        )
        collected_dup_2 = CollectedArticle(
            url="https://www.cnbc.com/article/dup-y",  # type: ignore[arg-type]
            title="Duplicate Y",
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
            mock_collector.collect = AsyncMock(
                return_value=[
                    collected_new_1,
                    collected_new_2,
                    collected_dup_1,
                    collected_dup_2,
                ]
            )
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

            # 2 of 4 URLs are existing (duplicates)
            mock_publisher = MagicMock()
            existing_urls = {
                "https://www.cnbc.com/article/dup-x",
                "https://www.cnbc.com/article/dup-y",
            }
            mock_publisher.get_existing_urls = AsyncMock(return_value=existing_urls)
            mock_publisher.is_duplicate_url = MagicMock(
                side_effect=lambda url, urls: url in urls
            )
            mock_publisher.publish_batch = AsyncMock(return_value=[])
            mock_publisher_cls.return_value = mock_publisher

            orchestrator = NewsWorkflowOrchestrator(config=sample_config)
            result = await orchestrator.run()

            # Verify: total_early_duplicates reflects the 2 excluded articles
            assert result.total_early_duplicates == 2

            # Verify: only 2 non-duplicate articles reached extraction
            assert mock_extractor.extract.call_count == 2
