"""Unit tests for the Publisher class.

Tests for the basic Publisher class structure including:
- Constructor initialization with NewsWorkflowConfig
- publish() method signature and behavior with no summary
- publish_batch() method signature

Following TDD approach: Red -> Green -> Refactor
"""

from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from news.config.models import NewsWorkflowConfig, SummarizationConfig
from news.models import (
    ArticleSource,
    CollectedArticle,
    ExtractedArticle,
    ExtractionStatus,
    PublicationStatus,
    SourceType,
    StructuredSummary,
    SummarizationStatus,
    SummarizedArticle,
)

# Fixtures


@pytest.fixture
def sample_config() -> NewsWorkflowConfig:
    """Create a sample NewsWorkflowConfig for testing."""
    return NewsWorkflowConfig(
        version="1.0",
        status_mapping={"market": "index", "tech": "ai"},
        github_status_ids={
            "index": "test-index-id",
            "ai": "test-ai-id",
            "finance": "test-finance-id",
        },
        rss={"presets_file": "test.json"},  # type: ignore[arg-type]
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
    )


@pytest.fixture
def sample_source() -> ArticleSource:
    """Create a sample ArticleSource."""
    return ArticleSource(
        source_type=SourceType.RSS,
        source_name="CNBC Markets",
        category="market",
    )


@pytest.fixture
def sample_collected_article(sample_source: ArticleSource) -> CollectedArticle:
    """Create a sample CollectedArticle."""
    return CollectedArticle(
        url="https://www.cnbc.com/article/123",  # type: ignore[arg-type]
        title="Market Update: S&P 500 Rallies",
        published=datetime(2025, 1, 15, 10, 0, 0, tzinfo=timezone.utc),
        raw_summary="Stocks rose on positive earnings reports.",
        source=sample_source,
        collected_at=datetime(2025, 1, 15, 12, 0, 0, tzinfo=timezone.utc),
    )


@pytest.fixture
def sample_extracted_article(
    sample_collected_article: CollectedArticle,
) -> ExtractedArticle:
    """Create a sample ExtractedArticle with body text."""
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
def summarized_article_with_summary(
    sample_extracted_article: ExtractedArticle,
    sample_summary: StructuredSummary,
) -> SummarizedArticle:
    """Create a SummarizedArticle with summary."""
    return SummarizedArticle(
        extracted=sample_extracted_article,
        summary=sample_summary,
        summarization_status=SummarizationStatus.SUCCESS,
    )


@pytest.fixture
def summarized_article_no_summary(
    sample_extracted_article: ExtractedArticle,
) -> SummarizedArticle:
    """Create a SummarizedArticle without summary (summarization failed)."""
    return SummarizedArticle(
        extracted=sample_extracted_article,
        summary=None,
        summarization_status=SummarizationStatus.SKIPPED,
        error_message="No body text available",
    )


# Tests


class TestPublisher:
    """Tests for the Publisher class basic structure."""

    def test_正常系_コンストラクタで設定を受け取る(
        self, sample_config: NewsWorkflowConfig
    ) -> None:
        """Publisher should accept NewsWorkflowConfig in constructor."""
        from news.publisher import Publisher

        publisher = Publisher(config=sample_config)

        assert publisher._config is sample_config
        assert publisher._repo == sample_config.github.repository
        assert publisher._project_id == sample_config.github.project_id
        assert publisher._project_number == sample_config.github.project_number
        assert publisher._status_field_id == sample_config.github.status_field_id
        assert (
            publisher._published_date_field_id
            == sample_config.github.published_date_field_id
        )

    def test_正常系_status_mappingが設定される(
        self, sample_config: NewsWorkflowConfig
    ) -> None:
        """Publisher should store status_mapping from config."""
        from news.publisher import Publisher

        publisher = Publisher(config=sample_config)

        assert publisher._status_mapping == sample_config.status_mapping
        assert publisher._status_ids == sample_config.github_status_ids

    def test_正常系_publishメソッドが存在する(
        self, sample_config: NewsWorkflowConfig
    ) -> None:
        """Publisher should have a publish() method."""
        from news.publisher import Publisher

        publisher = Publisher(config=sample_config)

        # Check method exists and is callable
        assert hasattr(publisher, "publish")
        assert callable(publisher.publish)

    def test_正常系_publish_batchメソッドが存在する(
        self, sample_config: NewsWorkflowConfig
    ) -> None:
        """Publisher should have a publish_batch() method."""
        from news.publisher import Publisher

        publisher = Publisher(config=sample_config)

        # Check method exists and is callable
        assert hasattr(publisher, "publish_batch")
        assert callable(publisher.publish_batch)


class TestPublishNoSummary:
    """Tests for publish() when article has no summary."""

    @pytest.mark.asyncio
    async def test_正常系_要約なしでSKIPPEDステータスを返す(
        self,
        sample_config: NewsWorkflowConfig,
        summarized_article_no_summary: SummarizedArticle,
    ) -> None:
        """publish() should return SKIPPED status when summary is None."""
        from news.publisher import Publisher

        publisher = Publisher(config=sample_config)

        result = await publisher.publish(summarized_article_no_summary)

        assert result.publication_status == PublicationStatus.SKIPPED
        assert result.issue_number is None
        assert result.issue_url is None
        assert result.error_message == "No summary available"
        assert result.summarized is summarized_article_no_summary


class TestPublishBatch:
    """Tests for publish_batch() method."""

    @pytest.mark.asyncio
    async def test_正常系_空リストで空リストを返す(
        self, sample_config: NewsWorkflowConfig
    ) -> None:
        """publish_batch() should return empty list for empty input."""
        from news.publisher import Publisher

        publisher = Publisher(config=sample_config)

        result = await publisher.publish_batch([])

        assert result == []

    @pytest.mark.asyncio
    async def test_正常系_dry_runパラメータが受け付けられる(
        self,
        sample_config: NewsWorkflowConfig,
        summarized_article_no_summary: SummarizedArticle,
    ) -> None:
        """publish_batch() should accept dry_run parameter."""
        from news.publisher import Publisher

        publisher = Publisher(config=sample_config)

        # Mock _get_existing_issues to avoid gh CLI call
        with patch.object(publisher, "_get_existing_issues", return_value=set()):
            # Should not raise with dry_run parameter
            result = await publisher.publish_batch(
                [summarized_article_no_summary], dry_run=True
            )

            assert len(result) == 1
            # No summary -> SKIPPED regardless of dry_run
            assert result[0].publication_status == PublicationStatus.SKIPPED


class TestGenerateIssueBody:
    """Tests for _generate_issue_body() method (P5-002)."""

    def test_正常系_4セクション構造でIssue本文を生成(
        self,
        sample_config: NewsWorkflowConfig,
        summarized_article_with_summary: SummarizedArticle,
    ) -> None:
        """_generate_issue_body should include 4 sections."""
        from news.publisher import Publisher

        publisher = Publisher(config=sample_config)

        body = publisher._generate_issue_body(summarized_article_with_summary)

        # Check all 4 sections exist
        assert "## 概要" in body
        assert "## キーポイント" in body
        assert "## 市場への影響" in body
        assert "## 関連情報" in body

    def test_正常系_メタデータが含まれる(
        self,
        sample_config: NewsWorkflowConfig,
        summarized_article_with_summary: SummarizedArticle,
    ) -> None:
        """_generate_issue_body should include source, published date, and URL."""
        from news.publisher import Publisher

        publisher = Publisher(config=sample_config)

        body = publisher._generate_issue_body(summarized_article_with_summary)

        # Check metadata section
        assert "**ソース**:" in body
        assert "CNBC Markets" in body
        assert "**公開日**:" in body
        assert "2025-01-15 10:00" in body
        assert "**URL**:" in body
        assert "https://www.cnbc.com/article/123" in body

    def test_正常系_キーポイントがマークダウンリストで出力(
        self,
        sample_config: NewsWorkflowConfig,
        summarized_article_with_summary: SummarizedArticle,
    ) -> None:
        """_generate_issue_body should output key_points as markdown list."""
        from news.publisher import Publisher

        publisher = Publisher(config=sample_config)

        body = publisher._generate_issue_body(summarized_article_with_summary)

        # Check key points are formatted as markdown list
        assert "- ポイント1" in body
        assert "- ポイント2" in body

    def test_正常系_関連情報なしでセクション省略(
        self,
        sample_config: NewsWorkflowConfig,
        sample_extracted_article: ExtractedArticle,
    ) -> None:
        """_generate_issue_body should omit related_info section when None."""
        from news.publisher import Publisher

        # Create summary without related_info
        summary_no_related = StructuredSummary(
            overview="S&P 500が上昇した。",
            key_points=["ポイント1", "ポイント2"],
            market_impact="市場への影響",
            related_info=None,
        )
        article = SummarizedArticle(
            extracted=sample_extracted_article,
            summary=summary_no_related,
            summarization_status=SummarizationStatus.SUCCESS,
        )

        publisher = Publisher(config=sample_config)

        body = publisher._generate_issue_body(article)

        # Related info section should not exist
        assert "## 関連情報" not in body
        # Other sections should still exist
        assert "## 概要" in body
        assert "## キーポイント" in body
        assert "## 市場への影響" in body

    def test_正常系_公開日なしで不明と表示(
        self,
        sample_config: NewsWorkflowConfig,
        sample_source: ArticleSource,
        sample_summary: StructuredSummary,
    ) -> None:
        """_generate_issue_body should show '不明' when published is None."""
        from news.publisher import Publisher

        # Create article without published date
        collected = CollectedArticle(
            url="https://www.cnbc.com/article/123",  # type: ignore[arg-type]
            title="Market Update",
            published=None,
            source=sample_source,
            collected_at=datetime(2025, 1, 15, 12, 0, 0, tzinfo=timezone.utc),
        )
        extracted = ExtractedArticle(
            collected=collected,
            body_text="Content",
            extraction_status=ExtractionStatus.SUCCESS,
            extraction_method="trafilatura",
        )
        article = SummarizedArticle(
            extracted=extracted,
            summary=sample_summary,
            summarization_status=SummarizationStatus.SUCCESS,
        )

        publisher = Publisher(config=sample_config)

        body = publisher._generate_issue_body(article)

        assert "**公開日**: 不明" in body

    def test_正常系_タイトルが本文の先頭に含まれる(
        self,
        sample_config: NewsWorkflowConfig,
        summarized_article_with_summary: SummarizedArticle,
    ) -> None:
        """_generate_issue_body should include article title at the start."""
        from news.publisher import Publisher

        publisher = Publisher(config=sample_config)

        body = publisher._generate_issue_body(summarized_article_with_summary)

        # Title should be at the start as h1
        assert body.startswith("# Market Update: S&P 500 Rallies")


class TestGenerateIssueTitle:
    """Tests for _generate_issue_title() method (P5-002)."""

    def test_正常系_カテゴリプレフィックスが付与される(
        self,
        sample_config: NewsWorkflowConfig,
        summarized_article_with_summary: SummarizedArticle,
    ) -> None:
        """_generate_issue_title should add category prefix from status_mapping."""
        from news.publisher import Publisher

        publisher = Publisher(config=sample_config)

        title = publisher._generate_issue_title(summarized_article_with_summary)

        # category is "market", which maps to "index"
        assert title == "[index] Market Update: S&P 500 Rallies"

    def test_正常系_マッピングにないカテゴリでotherプレフィックス(
        self,
        sample_config: NewsWorkflowConfig,
        sample_extracted_article: ExtractedArticle,
        sample_summary: StructuredSummary,
    ) -> None:
        """_generate_issue_title should use 'other' for unknown categories."""
        from news.publisher import Publisher

        # Create article with unknown category
        unknown_source = ArticleSource(
            source_type=SourceType.RSS,
            source_name="Unknown Source",
            category="unknown_category",
        )
        collected = CollectedArticle(
            url="https://example.com/article",  # type: ignore[arg-type]
            title="Unknown Article",
            source=unknown_source,
            collected_at=datetime(2025, 1, 15, 12, 0, 0, tzinfo=timezone.utc),
        )
        extracted = ExtractedArticle(
            collected=collected,
            body_text="Content",
            extraction_status=ExtractionStatus.SUCCESS,
            extraction_method="trafilatura",
        )
        article = SummarizedArticle(
            extracted=extracted,
            summary=sample_summary,
            summarization_status=SummarizationStatus.SUCCESS,
        )

        publisher = Publisher(config=sample_config)

        title = publisher._generate_issue_title(article)

        assert title == "[other] Unknown Article"

    def test_正常系_techカテゴリでaiプレフィックス(
        self,
        sample_config: NewsWorkflowConfig,
        sample_extracted_article: ExtractedArticle,
        sample_summary: StructuredSummary,
    ) -> None:
        """_generate_issue_title should map 'tech' category to 'ai' prefix."""
        from news.publisher import Publisher

        # Create article with tech category
        tech_source = ArticleSource(
            source_type=SourceType.RSS,
            source_name="Tech News",
            category="tech",
        )
        collected = CollectedArticle(
            url="https://example.com/tech-article",  # type: ignore[arg-type]
            title="AI Breakthrough",
            source=tech_source,
            collected_at=datetime(2025, 1, 15, 12, 0, 0, tzinfo=timezone.utc),
        )
        extracted = ExtractedArticle(
            collected=collected,
            body_text="Content",
            extraction_status=ExtractionStatus.SUCCESS,
            extraction_method="trafilatura",
        )
        article = SummarizedArticle(
            extracted=extracted,
            summary=sample_summary,
            summarization_status=SummarizationStatus.SUCCESS,
        )

        publisher = Publisher(config=sample_config)

        title = publisher._generate_issue_title(article)

        assert title == "[ai] AI Breakthrough"


class TestResolveStatus:
    """Tests for _resolve_status() method (P5-003)."""

    def test_正常系_カテゴリからStatusを解決(
        self,
        sample_config: NewsWorkflowConfig,
        summarized_article_with_summary: SummarizedArticle,
    ) -> None:
        """_resolve_status should resolve category to status name and ID."""
        from news.publisher import Publisher

        publisher = Publisher(config=sample_config)

        # category is "market", which maps to "index"
        status_name, status_id = publisher._resolve_status(
            summarized_article_with_summary
        )

        assert status_name == "index"
        assert status_id == "test-index-id"

    def test_正常系_techカテゴリでaiステータス(
        self,
        sample_config: NewsWorkflowConfig,
        sample_extracted_article: ExtractedArticle,
        sample_summary: StructuredSummary,
    ) -> None:
        """_resolve_status should map 'tech' category to 'ai' status."""
        from news.publisher import Publisher

        # Create article with tech category
        tech_source = ArticleSource(
            source_type=SourceType.RSS,
            source_name="Tech News",
            category="tech",
        )
        collected = CollectedArticle(
            url="https://example.com/tech-article",  # type: ignore[arg-type]
            title="AI Breakthrough",
            source=tech_source,
            collected_at=datetime(2025, 1, 15, 12, 0, 0, tzinfo=timezone.utc),
        )
        extracted = ExtractedArticle(
            collected=collected,
            body_text="Content",
            extraction_status=ExtractionStatus.SUCCESS,
            extraction_method="trafilatura",
        )
        article = SummarizedArticle(
            extracted=extracted,
            summary=sample_summary,
            summarization_status=SummarizationStatus.SUCCESS,
        )

        publisher = Publisher(config=sample_config)

        status_name, status_id = publisher._resolve_status(article)

        assert status_name == "ai"
        assert status_id == "test-ai-id"

    def test_正常系_未知のカテゴリでfinanceフォールバック(
        self,
        sample_extracted_article: ExtractedArticle,
        sample_summary: StructuredSummary,
    ) -> None:
        """_resolve_status should fallback to 'finance' for unknown categories."""
        from news.publisher import Publisher

        # Config with finance fallback
        config_with_finance = NewsWorkflowConfig(
            version="1.0",
            status_mapping={"market": "index", "tech": "ai"},
            github_status_ids={
                "index": "test-index-id",
                "ai": "test-ai-id",
                "finance": "test-finance-id",
            },
            rss={"presets_file": "test.json"},  # type: ignore[arg-type]
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
        )

        # Create article with unknown category
        unknown_source = ArticleSource(
            source_type=SourceType.RSS,
            source_name="Unknown Source",
            category="unknown_category",
        )
        collected = CollectedArticle(
            url="https://example.com/article",  # type: ignore[arg-type]
            title="Unknown Article",
            source=unknown_source,
            collected_at=datetime(2025, 1, 15, 12, 0, 0, tzinfo=timezone.utc),
        )
        extracted = ExtractedArticle(
            collected=collected,
            body_text="Content",
            extraction_status=ExtractionStatus.SUCCESS,
            extraction_method="trafilatura",
        )
        article = SummarizedArticle(
            extracted=extracted,
            summary=sample_summary,
            summarization_status=SummarizationStatus.SUCCESS,
        )

        publisher = Publisher(config=config_with_finance)

        status_name, status_id = publisher._resolve_status(article)

        # Should fallback to "finance"
        assert status_name == "finance"
        assert status_id == "test-finance-id"

    def test_正常系_戻り値がタプル(
        self,
        sample_config: NewsWorkflowConfig,
        summarized_article_with_summary: SummarizedArticle,
    ) -> None:
        """_resolve_status should return a tuple of (status_name, status_id)."""
        from news.publisher import Publisher

        publisher = Publisher(config=sample_config)

        result = publisher._resolve_status(summarized_article_with_summary)

        assert isinstance(result, tuple)
        assert len(result) == 2
        assert isinstance(result[0], str)
        assert isinstance(result[1], str)


class TestCreateIssue:
    """Tests for _create_issue() method (P5-004)."""

    @pytest.mark.asyncio
    async def test_正常系_Issue作成でIssue番号とURLを返す(
        self,
        sample_config: NewsWorkflowConfig,
        summarized_article_with_summary: SummarizedArticle,
    ) -> None:
        """_create_issue should return issue number and URL on success."""
        from news.publisher import Publisher

        publisher = Publisher(config=sample_config)

        # Mock subprocess.run for gh issue create
        with patch("news.publisher.subprocess.run") as mock_run:
            mock_result = MagicMock()
            mock_result.stdout = "https://github.com/YH-05/quants/issues/123\n"
            mock_result.returncode = 0
            mock_run.return_value = mock_result

            issue_number, issue_url = await publisher._create_issue(
                summarized_article_with_summary
            )

            assert issue_number == 123
            assert issue_url == "https://github.com/YH-05/quants/issues/123"

    @pytest.mark.asyncio
    async def test_正常系_ghコマンドに正しい引数を渡す(
        self,
        sample_config: NewsWorkflowConfig,
        summarized_article_with_summary: SummarizedArticle,
    ) -> None:
        """_create_issue should call gh with correct arguments."""
        from news.publisher import Publisher

        publisher = Publisher(config=sample_config)

        # Mock subprocess.run
        with patch("news.publisher.subprocess.run") as mock_run:
            mock_result = MagicMock()
            mock_result.stdout = "https://github.com/YH-05/quants/issues/123\n"
            mock_result.returncode = 0
            mock_run.return_value = mock_result

            await publisher._create_issue(summarized_article_with_summary)

            # Verify the call was made
            mock_run.assert_called_once()
            call_args = mock_run.call_args[0][0]

            assert call_args[0] == "gh"
            assert call_args[1] == "issue"
            assert call_args[2] == "create"
            assert "--repo" in call_args
            assert "YH-05/quants" in call_args
            assert "--title" in call_args
            assert "--body" in call_args


class TestAddToProject:
    """Tests for _add_to_project() method (P5-004)."""

    @pytest.mark.asyncio
    async def test_正常系_Projectに追加してフィールドを設定(
        self,
        sample_config: NewsWorkflowConfig,
        summarized_article_with_summary: SummarizedArticle,
    ) -> None:
        """_add_to_project should add issue and set fields."""
        from news.publisher import Publisher

        publisher = Publisher(config=sample_config)

        # Mock subprocess.run
        with patch("news.publisher.subprocess.run") as mock_run:
            mock_result = MagicMock()
            mock_result.stdout = "PVTI_test_item_id\n"
            mock_result.returncode = 0
            mock_run.return_value = mock_result

            await publisher._add_to_project(123, summarized_article_with_summary)

            # Should be called 3 times: item-add, item-edit (status), item-edit (date)
            assert mock_run.call_count == 3

    @pytest.mark.asyncio
    async def test_正常系_item_addで正しい引数を渡す(
        self,
        sample_config: NewsWorkflowConfig,
        summarized_article_with_summary: SummarizedArticle,
    ) -> None:
        """_add_to_project should call gh project item-add correctly."""
        from news.publisher import Publisher

        publisher = Publisher(config=sample_config)

        with (
            patch.object(publisher, "_get_existing_project_item", return_value=None),
            patch("news.publisher.subprocess.run") as mock_run,
        ):
            mock_result = MagicMock()
            mock_result.stdout = "PVTI_test_item_id\n"
            mock_result.returncode = 0
            mock_run.return_value = mock_result

            await publisher._add_to_project(123, summarized_article_with_summary)

            # Check first call (item-add)
            first_call_args = mock_run.call_args_list[0][0][0]
            assert first_call_args[0] == "gh"
            assert first_call_args[1] == "project"
            assert first_call_args[2] == "item-add"
            assert "15" in first_call_args  # project_number
            assert "--owner" in first_call_args
            assert "YH-05" in first_call_args
            assert "--url" in first_call_args
            assert "https://github.com/YH-05/quants/issues/123" in first_call_args

    @pytest.mark.asyncio
    async def test_正常系_Statusフィールドを設定(
        self,
        sample_config: NewsWorkflowConfig,
        summarized_article_with_summary: SummarizedArticle,
    ) -> None:
        """_add_to_project should set Status field."""
        from news.publisher import Publisher

        publisher = Publisher(config=sample_config)

        with patch("news.publisher.subprocess.run") as mock_run:
            mock_result = MagicMock()
            mock_result.stdout = "PVTI_test_item_id\n"
            mock_result.returncode = 0
            mock_run.return_value = mock_result

            await publisher._add_to_project(123, summarized_article_with_summary)

            # Check second call (status field edit)
            second_call_args = mock_run.call_args_list[1][0][0]
            assert second_call_args[0] == "gh"
            assert second_call_args[1] == "project"
            assert second_call_args[2] == "item-edit"
            assert "--project-id" in second_call_args
            assert "PVT_test" in second_call_args
            assert "--id" in second_call_args
            assert "PVTI_test_item_id" in second_call_args
            assert "--field-id" in second_call_args
            assert "PVTSSF_test" in second_call_args
            assert "--single-select-option-id" in second_call_args

    @pytest.mark.asyncio
    async def test_正常系_PublishedDateフィールドを設定(
        self,
        sample_config: NewsWorkflowConfig,
        summarized_article_with_summary: SummarizedArticle,
    ) -> None:
        """_add_to_project should set PublishedDate field."""
        from news.publisher import Publisher

        publisher = Publisher(config=sample_config)

        with patch("news.publisher.subprocess.run") as mock_run:
            mock_result = MagicMock()
            mock_result.stdout = "PVTI_test_item_id\n"
            mock_result.returncode = 0
            mock_run.return_value = mock_result

            await publisher._add_to_project(123, summarized_article_with_summary)

            # Check third call (date field edit)
            third_call_args = mock_run.call_args_list[2][0][0]
            assert third_call_args[0] == "gh"
            assert third_call_args[1] == "project"
            assert third_call_args[2] == "item-edit"
            assert "--project-id" in third_call_args
            assert "--id" in third_call_args
            assert "--field-id" in third_call_args
            assert "PVTF_test" in third_call_args  # published_date_field_id
            assert "--date" in third_call_args
            assert "2025-01-15" in third_call_args  # ISO format date

    @pytest.mark.asyncio
    async def test_正常系_公開日なしでDateフィールドをスキップ(
        self,
        sample_config: NewsWorkflowConfig,
        sample_source: ArticleSource,
        sample_summary: StructuredSummary,
    ) -> None:
        """_add_to_project should skip date field when published is None."""
        from news.publisher import Publisher

        # Create article without published date
        collected = CollectedArticle(
            url="https://www.cnbc.com/article/123",  # type: ignore[arg-type]
            title="Market Update",
            published=None,
            source=sample_source,
            collected_at=datetime(2025, 1, 15, 12, 0, 0, tzinfo=timezone.utc),
        )
        extracted = ExtractedArticle(
            collected=collected,
            body_text="Content",
            extraction_status=ExtractionStatus.SUCCESS,
            extraction_method="trafilatura",
        )
        article_no_date = SummarizedArticle(
            extracted=extracted,
            summary=sample_summary,
            summarization_status=SummarizationStatus.SUCCESS,
        )

        publisher = Publisher(config=sample_config)

        with patch("news.publisher.subprocess.run") as mock_run:
            mock_result = MagicMock()
            mock_result.stdout = "PVTI_test_item_id\n"
            mock_result.returncode = 0
            mock_run.return_value = mock_result

            await publisher._add_to_project(123, article_no_date)

            # Should be called only 2 times: item-add, item-edit (status only)
            assert mock_run.call_count == 2

    @pytest.mark.asyncio
    async def test_異常系_item_id空でフィールド設定をスキップ(
        self,
        sample_config: NewsWorkflowConfig,
        summarized_article_with_summary: SummarizedArticle,
    ) -> None:
        """_add_to_project should skip field updates when item_id is empty.

        When gh project item-add returns an empty item_id (e.g., when the issue
        already exists in the project), the method should:
        1. Log a warning with issue_number and stderr
        2. Skip all subsequent field update operations
        3. Not raise any exception (graceful degradation)
        """
        from news.publisher import Publisher

        publisher = Publisher(config=sample_config)

        with (
            patch.object(publisher, "_get_existing_project_item", return_value=None),
            patch("news.publisher.subprocess.run") as mock_run,
        ):
            # item-add returns empty stdout (empty item_id)
            mock_result = MagicMock()
            mock_result.stdout = ""  # Empty item_id
            mock_result.stderr = "Already exists"
            mock_result.returncode = 0
            mock_run.return_value = mock_result

            # Should not raise any exception
            await publisher._add_to_project(123, summarized_article_with_summary)

            # Should only call item-add, NOT item-edit (no field updates)
            assert mock_run.call_count == 1

            # Verify it was item-add that was called
            first_call_args = mock_run.call_args_list[0][0][0]
            assert first_call_args[0] == "gh"
            assert first_call_args[1] == "project"
            assert first_call_args[2] == "item-add"

    @pytest.mark.asyncio
    async def test_異常系_item_id空で警告ログを出力(
        self,
        sample_config: NewsWorkflowConfig,
        summarized_article_with_summary: SummarizedArticle,
    ) -> None:
        """_add_to_project should log warning when item_id is empty."""
        from news.publisher import Publisher

        publisher = Publisher(config=sample_config)

        with (
            patch("news.publisher.subprocess.run") as mock_run,
            patch("news.publisher.logger") as mock_logger,
        ):
            mock_result = MagicMock()
            mock_result.stdout = ""  # Empty item_id
            mock_result.stderr = "Already exists in project"
            mock_result.returncode = 0
            mock_run.return_value = mock_result

            await publisher._add_to_project(123, summarized_article_with_summary)

            # Verify warning was logged with required information
            mock_logger.warning.assert_called_once()
            call_kwargs = mock_logger.warning.call_args[1]

            # Should include issue_number and stderr
            assert "issue_number" in call_kwargs
            assert call_kwargs["issue_number"] == 123
            assert "stderr" in call_kwargs
            assert call_kwargs["stderr"] == "Already exists in project"


class TestPublishWithIssueCreation:
    """Tests for publish() method with Issue creation (P5-004)."""

    @pytest.mark.asyncio
    async def test_正常系_要約ありでIssue作成成功(
        self,
        sample_config: NewsWorkflowConfig,
        summarized_article_with_summary: SummarizedArticle,
    ) -> None:
        """publish() should create Issue and return SUCCESS status."""
        from news.publisher import Publisher

        publisher = Publisher(config=sample_config)

        # Mock subprocess.run for all gh commands
        with patch("news.publisher.subprocess.run") as mock_run:
            mock_result = MagicMock()
            mock_result.stdout = "https://github.com/YH-05/quants/issues/456\n"
            mock_result.returncode = 0
            mock_run.return_value = mock_result

            # Mock _add_to_project to avoid complex mocking
            with patch.object(publisher, "_add_to_project"):
                result = await publisher.publish(summarized_article_with_summary)

            assert result.publication_status == PublicationStatus.SUCCESS
            assert result.issue_number == 456
            assert result.issue_url == "https://github.com/YH-05/quants/issues/456"
            assert result.summarized is summarized_article_with_summary

    @pytest.mark.asyncio
    async def test_異常系_Issue作成失敗でFAILEDステータス(
        self,
        sample_config: NewsWorkflowConfig,
        summarized_article_with_summary: SummarizedArticle,
    ) -> None:
        """publish() should return FAILED status when Issue creation fails."""
        import subprocess

        from news.publisher import Publisher

        publisher = Publisher(config=sample_config)

        # Mock subprocess.run to raise CalledProcessError
        with patch("news.publisher.subprocess.run") as mock_run:
            mock_run.side_effect = subprocess.CalledProcessError(
                1, "gh", stderr="Error creating issue"
            )

            result = await publisher.publish(summarized_article_with_summary)

            assert result.publication_status == PublicationStatus.FAILED
            assert result.issue_number is None
            assert result.issue_url is None
            assert result.error_message is not None


def _make_mock_process(stdout: str, returncode: int = 0, stderr: str = "") -> AsyncMock:
    """Create a mock asyncio subprocess process.

    Parameters
    ----------
    stdout : str
        The stdout output to return.
    returncode : int
        The process return code.
    stderr : str
        The stderr output to return.

    Returns
    -------
    AsyncMock
        A mock process object with communicate() method.
    """
    mock_proc = AsyncMock()
    mock_proc.returncode = returncode
    mock_proc.communicate = AsyncMock(return_value=(stdout.encode(), stderr.encode()))
    return mock_proc


class TestGetExistingIssues:
    """Tests for _get_existing_issues() method (P32-005).

    Now uses asyncio.create_subprocess_exec instead of subprocess.run.
    """

    @pytest.mark.asyncio
    async def test_正常系_直近7日のIssueからURLを取得(
        self,
        sample_config: NewsWorkflowConfig,
    ) -> None:
        """_get_existing_issues should return URLs from recent Issues."""
        from datetime import datetime, timezone

        from news.publisher import Publisher

        publisher = Publisher(config=sample_config)

        # Use dynamic dates relative to "now" to avoid flaky tests
        now = datetime.now(timezone.utc)
        date_1_day_ago = (
            (now.replace(hour=10, minute=0, second=0, microsecond=0))
            .isoformat()
            .replace("+00:00", "Z")
        )
        date_2_days_ago = (
            (now.replace(hour=10, minute=0, second=0, microsecond=0))
            .isoformat()
            .replace("+00:00", "Z")
        )

        # Mock gh issue list response
        mock_issues = [
            {
                "body": "**URL**: https://www.cnbc.com/article/123",
                "createdAt": date_1_day_ago,
            },
            {
                "body": "**URL**: https://www.cnbc.com/article/456",
                "createdAt": date_2_days_ago,
            },
        ]

        import json

        mock_proc = _make_mock_process(json.dumps(mock_issues))

        with patch(
            "news.publisher.asyncio.create_subprocess_exec", return_value=mock_proc
        ):
            urls = await publisher._get_existing_issues(days=7)

            assert "https://www.cnbc.com/article/123" in urls
            assert "https://www.cnbc.com/article/456" in urls
            assert len(urls) == 2

    @pytest.mark.asyncio
    async def test_正常系_asyncio_create_subprocess_execを使用(
        self,
        sample_config: NewsWorkflowConfig,
    ) -> None:
        """_get_existing_issues should use asyncio.create_subprocess_exec."""
        from news.publisher import Publisher

        publisher = Publisher(config=sample_config)

        mock_proc = _make_mock_process("[]")

        with patch(
            "news.publisher.asyncio.create_subprocess_exec",
            return_value=mock_proc,
        ) as mock_exec:
            await publisher._get_existing_issues(days=7)

            mock_exec.assert_called_once()
            call_args = mock_exec.call_args[0]

            assert call_args[0] == "gh"
            assert call_args[1] == "issue"
            assert call_args[2] == "list"
            assert "--repo" in call_args
            assert "YH-05/quants" in call_args
            assert "--state" in call_args
            assert "all" in call_args
            assert "--limit" in call_args
            assert "1000" in call_args
            assert "--json" in call_args
            assert "body,createdAt" in call_args

    @pytest.mark.asyncio
    async def test_正常系_limit1000でページネーション対応(
        self,
        sample_config: NewsWorkflowConfig,
    ) -> None:
        """_get_existing_issues should use --limit 1000 (not 500)."""
        from news.publisher import Publisher

        publisher = Publisher(config=sample_config)

        mock_proc = _make_mock_process("[]")

        with patch(
            "news.publisher.asyncio.create_subprocess_exec",
            return_value=mock_proc,
        ) as mock_exec:
            await publisher._get_existing_issues(days=7)

            call_args = mock_exec.call_args[0]
            # Find the --limit argument and verify it's 1000
            limit_idx = list(call_args).index("--limit")
            assert call_args[limit_idx + 1] == "1000"

    @pytest.mark.asyncio
    async def test_正常系_古いIssueは除外(
        self,
        sample_config: NewsWorkflowConfig,
    ) -> None:
        """_get_existing_issues should exclude Issues older than specified days."""
        from datetime import datetime, timedelta, timezone

        from news.publisher import Publisher

        publisher = Publisher(config=sample_config)

        # Use dynamic dates relative to "now" to avoid flaky tests
        now = datetime.now(timezone.utc)
        recent_date = now.isoformat().replace("+00:00", "Z")
        old_date = (now - timedelta(days=10)).isoformat().replace("+00:00", "Z")

        # Mix of recent and old Issues
        mock_issues = [
            {
                "body": "**URL**: https://www.cnbc.com/article/recent",
                "createdAt": recent_date,  # Recent (within 7 days)
            },
            {
                "body": "**URL**: https://www.cnbc.com/article/old",
                "createdAt": old_date,  # Old (more than 7 days)
            },
        ]

        import json

        mock_proc = _make_mock_process(json.dumps(mock_issues))

        with patch(
            "news.publisher.asyncio.create_subprocess_exec", return_value=mock_proc
        ):
            urls = await publisher._get_existing_issues(days=7)

            assert "https://www.cnbc.com/article/recent" in urls
            assert "https://www.cnbc.com/article/old" not in urls
            assert len(urls) == 1

    @pytest.mark.asyncio
    async def test_正常系_URL形式以外の本文は無視(
        self,
        sample_config: NewsWorkflowConfig,
    ) -> None:
        """_get_existing_issues should ignore Issues without URL pattern."""
        from datetime import datetime, timezone

        from news.publisher import Publisher

        publisher = Publisher(config=sample_config)

        # Use dynamic date to avoid flaky tests
        now = datetime.now(timezone.utc)
        recent_date = now.isoformat().replace("+00:00", "Z")

        mock_issues = [
            {
                "body": "**URL**: https://www.cnbc.com/article/123",
                "createdAt": recent_date,
            },
            {
                "body": "This Issue has no URL field",
                "createdAt": recent_date,
            },
            {
                "body": None,  # Empty body
                "createdAt": recent_date,
            },
        ]

        import json

        mock_proc = _make_mock_process(json.dumps(mock_issues))

        with patch(
            "news.publisher.asyncio.create_subprocess_exec", return_value=mock_proc
        ):
            urls = await publisher._get_existing_issues(days=7)

            assert len(urls) == 1
            assert "https://www.cnbc.com/article/123" in urls

    @pytest.mark.asyncio
    async def test_正常系_空のリストで空のセットを返す(
        self,
        sample_config: NewsWorkflowConfig,
    ) -> None:
        """_get_existing_issues should return empty set for no Issues."""
        from news.publisher import Publisher

        publisher = Publisher(config=sample_config)

        mock_proc = _make_mock_process("[]")

        with patch(
            "news.publisher.asyncio.create_subprocess_exec", return_value=mock_proc
        ):
            urls = await publisher._get_existing_issues(days=7)

            assert urls == set()

    @pytest.mark.asyncio
    async def test_異常系_ghコマンド失敗で空のセットを返す(
        self,
        sample_config: NewsWorkflowConfig,
    ) -> None:
        """_get_existing_issues should return empty set when gh command fails."""
        from news.publisher import Publisher

        publisher = Publisher(config=sample_config)

        mock_proc = _make_mock_process(
            "", returncode=1, stderr="Error: gh auth required"
        )

        with patch(
            "news.publisher.asyncio.create_subprocess_exec", return_value=mock_proc
        ):
            urls = await publisher._get_existing_issues(days=7)

            assert urls == set()


class TestIsDuplicate:
    """Tests for _is_duplicate() method (P5-005)."""

    def test_正常系_重複URLでTrue(
        self,
        sample_config: NewsWorkflowConfig,
        summarized_article_with_summary: SummarizedArticle,
    ) -> None:
        """_is_duplicate should return True when URL exists in existing_urls."""
        from news.publisher import Publisher

        publisher = Publisher(config=sample_config)

        existing_urls = {"https://www.cnbc.com/article/123"}

        is_duplicate = publisher._is_duplicate(
            summarized_article_with_summary, existing_urls
        )

        assert is_duplicate is True

    def test_正常系_非重複URLでFalse(
        self,
        sample_config: NewsWorkflowConfig,
        summarized_article_with_summary: SummarizedArticle,
    ) -> None:
        """_is_duplicate should return False when URL not in existing_urls."""
        from news.publisher import Publisher

        publisher = Publisher(config=sample_config)

        existing_urls = {"https://www.cnbc.com/article/different"}

        is_duplicate = publisher._is_duplicate(
            summarized_article_with_summary, existing_urls
        )

        assert is_duplicate is False

    def test_正常系_空のセットでFalse(
        self,
        sample_config: NewsWorkflowConfig,
        summarized_article_with_summary: SummarizedArticle,
    ) -> None:
        """_is_duplicate should return False for empty existing_urls set."""
        from news.publisher import Publisher

        publisher = Publisher(config=sample_config)

        existing_urls: set[str] = set()

        is_duplicate = publisher._is_duplicate(
            summarized_article_with_summary, existing_urls
        )

        assert is_duplicate is False


class TestPublishBatchWithDuplicateCheck:
    """Tests for publish_batch() with duplicate check (P5-005)."""

    @pytest.mark.asyncio
    async def test_正常系_重複記事をDUPLICATEステータスでスキップ(
        self,
        sample_config: NewsWorkflowConfig,
        summarized_article_with_summary: SummarizedArticle,
    ) -> None:
        """publish_batch should mark duplicate articles as DUPLICATE."""
        from news.publisher import Publisher

        publisher = Publisher(config=sample_config)

        # Mock _get_existing_issues to return the article URL as existing
        with patch.object(
            publisher,
            "_get_existing_issues",
            return_value={"https://www.cnbc.com/article/123"},
        ):
            results = await publisher.publish_batch(
                [summarized_article_with_summary], dry_run=False
            )

            assert len(results) == 1
            assert results[0].publication_status == PublicationStatus.DUPLICATE
            assert results[0].issue_number is None
            assert results[0].issue_url is None

    @pytest.mark.asyncio
    async def test_正常系_非重複記事は正常に公開(
        self,
        sample_config: NewsWorkflowConfig,
        summarized_article_with_summary: SummarizedArticle,
    ) -> None:
        """publish_batch should publish non-duplicate articles."""
        from news.publisher import Publisher

        publisher = Publisher(config=sample_config)

        # Mock _get_existing_issues to return different URL
        with (
            patch.object(
                publisher,
                "_get_existing_issues",
                return_value={"https://www.cnbc.com/article/different"},
            ),
            patch("news.publisher.subprocess.run") as mock_run,
            patch.object(publisher, "_add_to_project"),
        ):
            mock_result = MagicMock()
            mock_result.stdout = "https://github.com/YH-05/quants/issues/789\n"
            mock_result.returncode = 0
            mock_run.return_value = mock_result

            results = await publisher.publish_batch(
                [summarized_article_with_summary], dry_run=False
            )

            assert len(results) == 1
            assert results[0].publication_status == PublicationStatus.SUCCESS

    @pytest.mark.asyncio
    async def test_正常系_バッチ処理統計に重複数を含む(
        self,
        sample_config: NewsWorkflowConfig,
        sample_extracted_article: ExtractedArticle,
        sample_summary: StructuredSummary,
    ) -> None:
        """publish_batch should track duplicate count in logs."""
        from news.publisher import Publisher

        # Create two articles with different URLs
        article1 = SummarizedArticle(
            extracted=sample_extracted_article,
            summary=sample_summary,
            summarization_status=SummarizationStatus.SUCCESS,
        )

        # Second article with different URL
        collected2 = CollectedArticle(
            url="https://www.cnbc.com/article/456",  # type: ignore[arg-type]
            title="Different Article",
            source=sample_extracted_article.collected.source,
            collected_at=datetime(2025, 1, 15, 12, 0, 0, tzinfo=timezone.utc),
        )
        extracted2 = ExtractedArticle(
            collected=collected2,
            body_text="Content",
            extraction_status=ExtractionStatus.SUCCESS,
            extraction_method="trafilatura",
        )
        article2 = SummarizedArticle(
            extracted=extracted2,
            summary=sample_summary,
            summarization_status=SummarizationStatus.SUCCESS,
        )

        publisher = Publisher(config=sample_config)

        # First article is duplicate, second is not
        with (
            patch.object(
                publisher,
                "_get_existing_issues",
                return_value={
                    "https://www.cnbc.com/article/123"
                },  # Only article1 is dup
            ),
            patch("news.publisher.subprocess.run") as mock_run,
            patch.object(publisher, "_add_to_project"),
        ):
            mock_result = MagicMock()
            mock_result.stdout = "https://github.com/YH-05/quants/issues/789\n"
            mock_result.returncode = 0
            mock_run.return_value = mock_result

            results = await publisher.publish_batch([article1, article2], dry_run=False)

            assert len(results) == 2
            # First should be duplicate
            assert results[0].publication_status == PublicationStatus.DUPLICATE
            # Second should be success
            assert results[1].publication_status == PublicationStatus.SUCCESS


class TestPublishBatchDryRun:
    """Tests for publish_batch() with dry_run mode (P5-006)."""

    @pytest.mark.asyncio
    async def test_正常系_dry_runでIssue作成をスキップ(
        self,
        sample_config: NewsWorkflowConfig,
        summarized_article_with_summary: SummarizedArticle,
    ) -> None:
        """publish_batch should skip Issue creation when dry_run=True."""
        from news.publisher import Publisher

        publisher = Publisher(config=sample_config)

        # Mock _get_existing_issues to return empty set (no duplicates)
        # Should NOT call subprocess.run for gh issue create
        with (
            patch.object(
                publisher,
                "_get_existing_issues",
                return_value=set(),
            ) as mock_get_existing,
            patch("news.publisher.subprocess.run") as mock_run,
        ):
            results = await publisher.publish_batch(
                [summarized_article_with_summary], dry_run=True
            )

            assert len(results) == 1
            assert results[0].publication_status == PublicationStatus.SUCCESS
            # Issue should NOT be created
            assert results[0].issue_number is None
            assert results[0].issue_url is None

            # subprocess.run should NOT be called for issue creation
            # (only _get_existing_issues should be called)
            mock_get_existing.assert_called_once()
            mock_run.assert_not_called()

    @pytest.mark.asyncio
    async def test_正常系_dry_runでも重複チェックは動作(
        self,
        sample_config: NewsWorkflowConfig,
        summarized_article_with_summary: SummarizedArticle,
    ) -> None:
        """publish_batch should still check duplicates when dry_run=True."""
        from news.publisher import Publisher

        publisher = Publisher(config=sample_config)

        # Mock _get_existing_issues to return the article URL (duplicate)
        with patch.object(
            publisher,
            "_get_existing_issues",
            return_value={"https://www.cnbc.com/article/123"},
        ):
            results = await publisher.publish_batch(
                [summarized_article_with_summary], dry_run=True
            )

            assert len(results) == 1
            # Should be DUPLICATE, not SUCCESS
            assert results[0].publication_status == PublicationStatus.DUPLICATE

    @pytest.mark.asyncio
    async def test_正常系_dry_runで要約なし記事はSKIPPED(
        self,
        sample_config: NewsWorkflowConfig,
        summarized_article_no_summary: SummarizedArticle,
    ) -> None:
        """publish_batch should return SKIPPED for articles without summary even in dry_run."""
        from news.publisher import Publisher

        publisher = Publisher(config=sample_config)

        with patch.object(
            publisher,
            "_get_existing_issues",
            return_value=set(),
        ):
            results = await publisher.publish_batch(
                [summarized_article_no_summary], dry_run=True
            )

            assert len(results) == 1
            # No summary -> SKIPPED (not affected by dry_run)
            assert results[0].publication_status == PublicationStatus.SKIPPED

    @pytest.mark.asyncio
    async def test_正常系_dry_runでログにWould_create_issueと出力(
        self,
        sample_config: NewsWorkflowConfig,
        summarized_article_with_summary: SummarizedArticle,
    ) -> None:
        """publish_batch should log 'Would create issue' when dry_run=True."""
        from news.publisher import Publisher

        publisher = Publisher(config=sample_config)

        # Mock the logger to capture calls
        with (
            patch.object(
                publisher,
                "_get_existing_issues",
                return_value=set(),
            ),
            patch("news.publisher.logger") as mock_logger,
        ):
            await publisher.publish_batch(
                [summarized_article_with_summary], dry_run=True
            )

            # Check that logger.info was called with dry run message
            info_calls = [call for call in mock_logger.info.call_args_list]
            dry_run_logged = any(
                "[DRY RUN] Would create issue" in str(call) for call in info_calls
            )
            assert dry_run_logged, f"Expected dry run log message, got: {info_calls}"

    @pytest.mark.asyncio
    async def test_正常系_dry_runで複数記事を処理(
        self,
        sample_config: NewsWorkflowConfig,
        sample_extracted_article: ExtractedArticle,
        sample_summary: StructuredSummary,
    ) -> None:
        """publish_batch should process multiple articles correctly in dry_run mode."""
        from news.publisher import Publisher

        # Create two articles with different URLs
        article1 = SummarizedArticle(
            extracted=sample_extracted_article,
            summary=sample_summary,
            summarization_status=SummarizationStatus.SUCCESS,
        )

        # Second article with different URL
        collected2 = CollectedArticle(
            url="https://www.cnbc.com/article/456",  # type: ignore[arg-type]
            title="Second Article",
            source=sample_extracted_article.collected.source,
            collected_at=datetime(2025, 1, 15, 12, 0, 0, tzinfo=timezone.utc),
        )
        extracted2 = ExtractedArticle(
            collected=collected2,
            body_text="Content",
            extraction_status=ExtractionStatus.SUCCESS,
            extraction_method="trafilatura",
        )
        article2 = SummarizedArticle(
            extracted=extracted2,
            summary=sample_summary,
            summarization_status=SummarizationStatus.SUCCESS,
        )

        publisher = Publisher(config=sample_config)

        with patch.object(
            publisher,
            "_get_existing_issues",
            return_value=set(),
        ):
            results = await publisher.publish_batch([article1, article2], dry_run=True)

            assert len(results) == 2
            # Both should be SUCCESS (dry run)
            assert results[0].publication_status == PublicationStatus.SUCCESS
            assert results[1].publication_status == PublicationStatus.SUCCESS
            # But no Issue numbers
            assert results[0].issue_number is None
            assert results[1].issue_number is None


class TestGetExistingProjectItem:
    """Tests for _get_existing_project_item() method (P10-004).

    This method searches for an existing Project Item by Issue URL
    and returns its item_id if found.
    """

    @pytest.mark.asyncio
    async def test_正常系_既存Itemがある場合item_idを返す(
        self,
        sample_config: NewsWorkflowConfig,
    ) -> None:
        """_get_existing_project_item should return item_id when Issue exists in Project."""
        from news.publisher import Publisher

        publisher = Publisher(config=sample_config)
        issue_url = "https://github.com/YH-05/quants/issues/123"

        with patch("news.publisher.subprocess.run") as mock_run:
            mock_result = MagicMock()
            mock_result.stdout = "PVTI_xxx\n"
            mock_result.returncode = 0
            mock_run.return_value = mock_result

            item_id = await publisher._get_existing_project_item(issue_url)

            assert item_id == "PVTI_xxx"

    @pytest.mark.asyncio
    async def test_正常系_既存Itemがない場合Noneを返す(
        self,
        sample_config: NewsWorkflowConfig,
    ) -> None:
        """_get_existing_project_item should return None when Issue not in Project."""
        from news.publisher import Publisher

        publisher = Publisher(config=sample_config)
        issue_url = "https://github.com/YH-05/quants/issues/999"

        with patch("news.publisher.subprocess.run") as mock_run:
            mock_result = MagicMock()
            mock_result.stdout = ""  # Empty output means no match
            mock_result.returncode = 0
            mock_run.return_value = mock_result

            item_id = await publisher._get_existing_project_item(issue_url)

            assert item_id is None

    @pytest.mark.asyncio
    async def test_正常系_ghコマンドに正しい引数を渡す(
        self,
        sample_config: NewsWorkflowConfig,
    ) -> None:
        """_get_existing_project_item should call gh with correct arguments."""
        from news.publisher import Publisher

        publisher = Publisher(config=sample_config)
        issue_url = "https://github.com/YH-05/quants/issues/123"

        with patch("news.publisher.subprocess.run") as mock_run:
            mock_result = MagicMock()
            mock_result.stdout = "PVTI_xxx\n"
            mock_result.returncode = 0
            mock_run.return_value = mock_result

            await publisher._get_existing_project_item(issue_url)

            mock_run.assert_called_once()
            call_args = mock_run.call_args[0][0]

            assert call_args[0] == "gh"
            assert call_args[1] == "project"
            assert call_args[2] == "item-list"
            assert "15" in call_args  # project_number
            assert "--owner" in call_args
            assert "YH-05" in call_args
            assert "--format" in call_args
            assert "json" in call_args
            assert "--jq" in call_args
            # jq filter should select by content.url
            jq_idx = call_args.index("--jq")
            jq_filter = call_args[jq_idx + 1]
            assert ".items[]" in jq_filter
            assert "select" in jq_filter
            assert issue_url in jq_filter

    @pytest.mark.asyncio
    async def test_正常系_コマンドエラーでNoneを返す(
        self,
        sample_config: NewsWorkflowConfig,
    ) -> None:
        """_get_existing_project_item should return None on command error."""
        from news.publisher import Publisher

        publisher = Publisher(config=sample_config)
        issue_url = "https://github.com/YH-05/quants/issues/123"

        with patch("news.publisher.subprocess.run") as mock_run:
            mock_result = MagicMock()
            mock_result.stdout = ""
            mock_result.returncode = 1  # Non-zero return code
            mock_run.return_value = mock_result

            item_id = await publisher._get_existing_project_item(issue_url)

            assert item_id is None


class TestAddToProjectWithExistingItemCheck:
    """Tests for _add_to_project() with existing item check (P10-004).

    Modified _add_to_project behavior:
    - First checks if Issue already exists in Project
    - If exists: skip item-add, use existing item_id for field updates
    - If not exists: add to project, then update fields
    """

    @pytest.mark.asyncio
    async def test_正常系_新規Issueは通常通り追加される(
        self,
        sample_config: NewsWorkflowConfig,
        summarized_article_with_summary: SummarizedArticle,
    ) -> None:
        """_add_to_project should add new Issue normally."""
        from news.publisher import Publisher

        publisher = Publisher(config=sample_config)

        with (
            patch.object(
                publisher, "_get_existing_project_item", return_value=None
            ) as mock_check,
            patch("news.publisher.subprocess.run") as mock_run,
        ):
            mock_result = MagicMock()
            mock_result.stdout = '{"id": "PVTI_new_item"}\n'
            mock_result.returncode = 0
            mock_run.return_value = mock_result

            await publisher._add_to_project(123, summarized_article_with_summary)

            # Should check for existing item
            mock_check.assert_called_once_with(
                "https://github.com/YH-05/quants/issues/123"
            )

            # Should call item-add (new item)
            first_call_args = mock_run.call_args_list[0][0][0]
            assert first_call_args[2] == "item-add"

            # Should also call item-edit for fields (status + date = 2 more calls)
            assert mock_run.call_count == 3

    @pytest.mark.asyncio
    async def test_正常系_既存Issueはフィールド更新のみ実行(
        self,
        sample_config: NewsWorkflowConfig,
        summarized_article_with_summary: SummarizedArticle,
    ) -> None:
        """_add_to_project should only update fields for existing Issue."""
        from news.publisher import Publisher

        publisher = Publisher(config=sample_config)

        with (
            patch.object(
                publisher, "_get_existing_project_item", return_value="PVTI_existing"
            ) as mock_check,
            patch("news.publisher.subprocess.run") as mock_run,
        ):
            mock_result = MagicMock()
            mock_result.returncode = 0
            mock_run.return_value = mock_result

            await publisher._add_to_project(123, summarized_article_with_summary)

            # Should check for existing item
            mock_check.assert_called_once()

            # Should NOT call item-add (existing item)
            for call in mock_run.call_args_list:
                call_args = call[0][0]
                assert call_args[2] != "item-add", (
                    "Should not call item-add for existing item"
                )

            # Should call item-edit for fields only (status + date = 2 calls)
            assert mock_run.call_count == 2

            # Verify field updates use the existing item_id
            for call in mock_run.call_args_list:
                call_args = call[0][0]
                assert "PVTI_existing" in call_args

    @pytest.mark.asyncio
    async def test_正常系_既存Issueで既存item_idが正しく使用される(
        self,
        sample_config: NewsWorkflowConfig,
        summarized_article_with_summary: SummarizedArticle,
    ) -> None:
        """_add_to_project should use correct existing item_id for field updates."""
        from news.publisher import Publisher

        publisher = Publisher(config=sample_config)
        existing_item_id = "PVTI_abc123"

        with (
            patch.object(
                publisher, "_get_existing_project_item", return_value=existing_item_id
            ),
            patch("news.publisher.subprocess.run") as mock_run,
        ):
            mock_result = MagicMock()
            mock_result.returncode = 0
            mock_run.return_value = mock_result

            await publisher._add_to_project(123, summarized_article_with_summary)

            # Both item-edit calls should use existing item_id
            for call in mock_run.call_args_list:
                call_args = call[0][0]
                assert existing_item_id in call_args

    @pytest.mark.asyncio
    async def test_正常系_既存Issueでログを出力(
        self,
        sample_config: NewsWorkflowConfig,
        summarized_article_with_summary: SummarizedArticle,
    ) -> None:
        """_add_to_project should log when updating existing Issue."""
        from news.publisher import Publisher

        publisher = Publisher(config=sample_config)

        with (
            patch.object(
                publisher, "_get_existing_project_item", return_value="PVTI_existing"
            ),
            patch("news.publisher.subprocess.run") as mock_run,
            patch("news.publisher.logger") as mock_logger,
        ):
            mock_result = MagicMock()
            mock_result.returncode = 0
            mock_run.return_value = mock_result

            await publisher._add_to_project(123, summarized_article_with_summary)

            # Should log info about existing item
            info_calls = mock_logger.info.call_args_list
            existing_logged = any(
                "already in project" in str(call).lower()
                or "existing" in str(call).lower()
                for call in info_calls
            )
            assert existing_logged, (
                f"Expected log about existing item, got: {info_calls}"
            )


class TestGetExistingUrls:
    """Tests for get_existing_urls() public method (P32-005)."""

    @pytest.mark.asyncio
    async def test_正常系_デフォルトでconfig値を使用(
        self,
        sample_config: NewsWorkflowConfig,
    ) -> None:
        """get_existing_urls should use config.github.duplicate_check_days as default."""
        from news.publisher import Publisher

        publisher = Publisher(config=sample_config)

        with patch.object(
            publisher,
            "_get_existing_issues",
            return_value={"https://www.cnbc.com/article/123"},
        ) as mock_get:
            urls = await publisher.get_existing_urls()

            # Should use config default (7 days)
            mock_get.assert_called_once_with(
                days=sample_config.github.duplicate_check_days
            )
            assert "https://www.cnbc.com/article/123" in urls

    @pytest.mark.asyncio
    async def test_正常系_days指定で指定値を使用(
        self,
        sample_config: NewsWorkflowConfig,
    ) -> None:
        """get_existing_urls should use specified days parameter."""
        from news.publisher import Publisher

        publisher = Publisher(config=sample_config)

        with patch.object(
            publisher,
            "_get_existing_issues",
            return_value=set(),
        ) as mock_get:
            await publisher.get_existing_urls(days=14)

            mock_get.assert_called_once_with(days=14)

    @pytest.mark.asyncio
    async def test_正常系_戻り値がセット(
        self,
        sample_config: NewsWorkflowConfig,
    ) -> None:
        """get_existing_urls should return a set of URL strings."""
        from news.publisher import Publisher

        publisher = Publisher(config=sample_config)

        expected_urls = {
            "https://www.cnbc.com/article/1",
            "https://www.cnbc.com/article/2",
        }

        with patch.object(
            publisher,
            "_get_existing_issues",
            return_value=expected_urls,
        ):
            urls = await publisher.get_existing_urls()

            assert isinstance(urls, set)
            assert urls == expected_urls


class TestIsDuplicateUrl:
    """Tests for is_duplicate_url() public method (P32-005)."""

    def test_正常系_重複URLでTrue(
        self,
        sample_config: NewsWorkflowConfig,
    ) -> None:
        """is_duplicate_url should return True when URL exists in set."""
        from news.publisher import Publisher

        publisher = Publisher(config=sample_config)

        existing_urls = {"https://www.cnbc.com/article/123"}

        assert (
            publisher.is_duplicate_url(
                "https://www.cnbc.com/article/123", existing_urls
            )
            is True
        )

    def test_正常系_非重複URLでFalse(
        self,
        sample_config: NewsWorkflowConfig,
    ) -> None:
        """is_duplicate_url should return False when URL not in set."""
        from news.publisher import Publisher

        publisher = Publisher(config=sample_config)

        existing_urls = {"https://www.cnbc.com/article/different"}

        assert (
            publisher.is_duplicate_url(
                "https://www.cnbc.com/article/123", existing_urls
            )
            is False
        )

    def test_正常系_空のセットでFalse(
        self,
        sample_config: NewsWorkflowConfig,
    ) -> None:
        """is_duplicate_url should return False for empty set."""
        from news.publisher import Publisher

        publisher = Publisher(config=sample_config)

        assert (
            publisher.is_duplicate_url("https://www.cnbc.com/article/123", set())
            is False
        )

    def test_正常系_重複検出時にdebugログを出力(
        self,
        sample_config: NewsWorkflowConfig,
    ) -> None:
        """is_duplicate_url should log at debug level when duplicate detected."""
        from news.publisher import Publisher

        publisher = Publisher(config=sample_config)

        existing_urls = {"https://www.cnbc.com/article/123"}

        with patch("news.publisher.logger") as mock_logger:
            publisher.is_duplicate_url(
                "https://www.cnbc.com/article/123", existing_urls
            )

            mock_logger.debug.assert_called()
            call_kwargs = mock_logger.debug.call_args[1]
            assert "url" in call_kwargs
