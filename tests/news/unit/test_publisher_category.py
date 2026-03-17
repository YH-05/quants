"""Unit tests for Publisher category-based Issue publishing.

Tests for:
- publish_category_batch() creates one Issue per CategoryGroup
- _check_category_issue_exists() title-based duplicate check
- dry_run mode
- Project integration (Status/Date fields)
- Error handling

Following TDD approach: Red -> Green -> Refactor
"""

from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from news.config.models import (
    CategoryLabelsConfig,
    NewsWorkflowConfig,
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
    SourceType,
    StructuredSummary,
    SummarizationStatus,
    SummarizedArticle,
)

# ===========================================================================
# Fixtures
# ===========================================================================


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
def sample_summarized_article() -> SummarizedArticle:
    """Create a sample SummarizedArticle for use in CategoryGroup."""
    source = ArticleSource(
        source_type=SourceType.RSS,
        source_name="CNBC Markets",
        category="market",
    )
    collected = CollectedArticle(
        url="https://www.cnbc.com/article/123",  # type: ignore[arg-type]
        title="Market Update: S&P 500 Rallies",
        published=datetime(2026, 2, 9, 10, 0, 0, tzinfo=timezone.utc),
        raw_summary="Stocks rose on positive earnings reports.",
        source=source,
        collected_at=datetime(2026, 2, 9, 12, 0, 0, tzinfo=timezone.utc),
    )
    extracted = ExtractedArticle(
        collected=collected,
        body_text="Full article content about the S&P 500 rally...",
        extraction_status=ExtractionStatus.SUCCESS,
        extraction_method="trafilatura",
    )
    summary = StructuredSummary(
        overview="S&P 500 rallied today.",
        key_points=["Point 1", "Point 2"],
        market_impact="Bullish sentiment continues.",
    )
    return SummarizedArticle(
        extracted=extracted,
        summary=summary,
        summarization_status=SummarizationStatus.SUCCESS,
    )


@pytest.fixture
def sample_category_group(
    sample_summarized_article: SummarizedArticle,
) -> CategoryGroup:
    """Create a sample CategoryGroup."""
    return CategoryGroup(
        category="index",
        category_label="株価指数",
        date="2026-02-09",
        articles=[sample_summarized_article],
    )


@pytest.fixture
def two_category_groups(
    sample_summarized_article: SummarizedArticle,
) -> list[CategoryGroup]:
    """Create two CategoryGroups for batch testing."""
    source_ai = ArticleSource(
        source_type=SourceType.RSS,
        source_name="Tech News",
        category="tech",
    )
    collected_ai = CollectedArticle(
        url="https://example.com/ai-article",  # type: ignore[arg-type]
        title="AI Breakthrough",
        published=datetime(2026, 2, 9, 10, 0, 0, tzinfo=timezone.utc),
        source=source_ai,
        collected_at=datetime(2026, 2, 9, 12, 0, 0, tzinfo=timezone.utc),
    )
    extracted_ai = ExtractedArticle(
        collected=collected_ai,
        body_text="AI content...",
        extraction_status=ExtractionStatus.SUCCESS,
        extraction_method="trafilatura",
    )
    summary_ai = StructuredSummary(
        overview="AI breakthrough.",
        key_points=["Key AI point"],
        market_impact="AI sector impact.",
    )
    article_ai = SummarizedArticle(
        extracted=extracted_ai,
        summary=summary_ai,
        summarization_status=SummarizationStatus.SUCCESS,
    )

    group_index = CategoryGroup(
        category="index",
        category_label="株価指数",
        date="2026-02-09",
        articles=[sample_summarized_article],
    )
    group_ai = CategoryGroup(
        category="ai",
        category_label="AI関連",
        date="2026-02-09",
        articles=[article_ai],
    )
    return [group_index, group_ai]


# ===========================================================================
# Tests: publish_category_batch
# ===========================================================================


class TestPublishCategoryBatch:
    """Tests for publish_category_batch() method."""

    @pytest.mark.asyncio
    async def test_正常系_メソッドが存在する(
        self,
        sample_config: NewsWorkflowConfig,
    ) -> None:
        """publish_category_batch() should exist on Publisher."""
        from news.publisher import Publisher

        publisher = Publisher(config=sample_config)

        assert hasattr(publisher, "publish_category_batch")
        assert callable(publisher.publish_category_batch)

    @pytest.mark.asyncio
    async def test_正常系_空リストで空リストを返す(
        self,
        sample_config: NewsWorkflowConfig,
    ) -> None:
        """publish_category_batch() should return empty list for empty input."""
        from news.publisher import Publisher

        publisher = Publisher(config=sample_config)

        result = await publisher.publish_category_batch([])

        assert result == []

    @pytest.mark.asyncio
    async def test_正常系_カテゴリごとに1Issueを作成(
        self,
        sample_config: NewsWorkflowConfig,
        sample_category_group: CategoryGroup,
    ) -> None:
        """publish_category_batch() should create one Issue per CategoryGroup."""
        from news.publisher import Publisher

        publisher = Publisher(config=sample_config)

        with (
            patch.object(
                publisher,
                "_check_category_issue_exists",
                return_value=None,
            ),
            patch.object(
                publisher,
                "_create_category_issue",
                return_value=(100, "https://github.com/YH-05/quants/issues/100"),
            ),
            patch.object(publisher, "_add_category_to_project"),
        ):
            results = await publisher.publish_category_batch([sample_category_group])

            assert len(results) == 1
            assert results[0].status == PublicationStatus.SUCCESS
            assert results[0].issue_number == 100
            assert results[0].issue_url == "https://github.com/YH-05/quants/issues/100"
            assert results[0].category == "index"
            assert results[0].category_label == "株価指数"
            assert results[0].date == "2026-02-09"
            assert results[0].article_count == 1

    @pytest.mark.asyncio
    async def test_正常系_複数カテゴリで複数Issue作成(
        self,
        sample_config: NewsWorkflowConfig,
        two_category_groups: list[CategoryGroup],
    ) -> None:
        """publish_category_batch() should create Issues for multiple categories."""
        from news.publisher import Publisher

        publisher = Publisher(config=sample_config)

        issue_counter = iter(
            [
                (100, "https://github.com/YH-05/quants/issues/100"),
                (101, "https://github.com/YH-05/quants/issues/101"),
            ]
        )

        with (
            patch.object(
                publisher,
                "_check_category_issue_exists",
                return_value=None,
            ),
            patch.object(
                publisher,
                "_create_category_issue",
                side_effect=lambda g: next(issue_counter),
            ),
            patch.object(publisher, "_add_category_to_project"),
        ):
            results = await publisher.publish_category_batch(two_category_groups)

            assert len(results) == 2
            assert results[0].status == PublicationStatus.SUCCESS
            assert results[1].status == PublicationStatus.SUCCESS
            assert results[0].issue_number == 100
            assert results[1].issue_number == 101

    @pytest.mark.asyncio
    async def test_正常系_戻り値がCategoryPublishResultのリスト(
        self,
        sample_config: NewsWorkflowConfig,
        sample_category_group: CategoryGroup,
    ) -> None:
        """publish_category_batch() should return list of CategoryPublishResult."""
        from news.publisher import Publisher

        publisher = Publisher(config=sample_config)

        with (
            patch.object(
                publisher,
                "_check_category_issue_exists",
                return_value=None,
            ),
            patch.object(
                publisher,
                "_create_category_issue",
                return_value=(100, "https://github.com/YH-05/quants/issues/100"),
            ),
            patch.object(publisher, "_add_category_to_project"),
        ):
            results = await publisher.publish_category_batch([sample_category_group])

            assert isinstance(results[0], CategoryPublishResult)

    @pytest.mark.asyncio
    async def test_正常系_重複カテゴリはスキップ(
        self,
        sample_config: NewsWorkflowConfig,
        sample_category_group: CategoryGroup,
    ) -> None:
        """publish_category_batch() should skip duplicate categories."""
        from news.publisher import Publisher

        publisher = Publisher(config=sample_config)

        # _check_category_issue_exists returns existing issue number
        with patch.object(
            publisher,
            "_check_category_issue_exists",
            return_value=50,
        ):
            results = await publisher.publish_category_batch([sample_category_group])

            assert len(results) == 1
            assert results[0].status == PublicationStatus.DUPLICATE
            assert results[0].issue_number is None
            assert results[0].error_message is not None

    @pytest.mark.asyncio
    async def test_正常系_dry_runでIssue作成をスキップ(
        self,
        sample_config: NewsWorkflowConfig,
        sample_category_group: CategoryGroup,
    ) -> None:
        """publish_category_batch() should skip Issue creation in dry_run mode."""
        from news.publisher import Publisher

        publisher = Publisher(config=sample_config)

        with patch.object(
            publisher,
            "_check_category_issue_exists",
            return_value=None,
        ):
            results = await publisher.publish_category_batch(
                [sample_category_group], dry_run=True
            )

            assert len(results) == 1
            assert results[0].status == PublicationStatus.SUCCESS
            assert results[0].issue_number is None
            assert results[0].issue_url is None

    @pytest.mark.asyncio
    async def test_正常系_dry_runでも重複チェックは動作(
        self,
        sample_config: NewsWorkflowConfig,
        sample_category_group: CategoryGroup,
    ) -> None:
        """publish_category_batch() should check duplicates even in dry_run mode."""
        from news.publisher import Publisher

        publisher = Publisher(config=sample_config)

        with patch.object(
            publisher,
            "_check_category_issue_exists",
            return_value=50,
        ):
            results = await publisher.publish_category_batch(
                [sample_category_group], dry_run=True
            )

            assert len(results) == 1
            assert results[0].status == PublicationStatus.DUPLICATE

    @pytest.mark.asyncio
    async def test_異常系_Issue作成失敗でFAILEDステータス(
        self,
        sample_config: NewsWorkflowConfig,
        sample_category_group: CategoryGroup,
    ) -> None:
        """publish_category_batch() should return FAILED on Issue creation error."""
        import subprocess

        from news.publisher import Publisher

        publisher = Publisher(config=sample_config)

        with (
            patch.object(
                publisher,
                "_check_category_issue_exists",
                return_value=None,
            ),
            patch.object(
                publisher,
                "_create_category_issue",
                side_effect=subprocess.CalledProcessError(
                    1, "gh", stderr="Error creating issue"
                ),
            ),
        ):
            results = await publisher.publish_category_batch([sample_category_group])

            assert len(results) == 1
            assert results[0].status == PublicationStatus.FAILED
            assert results[0].issue_number is None
            assert results[0].error_message is not None

    @pytest.mark.asyncio
    async def test_異常系_1つ失敗しても他は継続(
        self,
        sample_config: NewsWorkflowConfig,
        two_category_groups: list[CategoryGroup],
    ) -> None:
        """publish_category_batch() should continue on individual failures."""
        import subprocess

        from news.publisher import Publisher

        publisher = Publisher(config=sample_config)

        call_count = 0

        async def mock_create(group: CategoryGroup) -> tuple[int, str]:
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                raise subprocess.CalledProcessError(
                    1, "gh", stderr="Error creating issue"
                )
            return (101, "https://github.com/YH-05/quants/issues/101")

        with (
            patch.object(
                publisher,
                "_check_category_issue_exists",
                return_value=None,
            ),
            patch.object(
                publisher,
                "_create_category_issue",
                side_effect=mock_create,
            ),
            patch.object(publisher, "_add_category_to_project"),
        ):
            results = await publisher.publish_category_batch(two_category_groups)

            assert len(results) == 2
            assert results[0].status == PublicationStatus.FAILED
            assert results[1].status == PublicationStatus.SUCCESS

    @pytest.mark.asyncio
    async def test_正常系_Project追加が呼ばれる(
        self,
        sample_config: NewsWorkflowConfig,
        sample_category_group: CategoryGroup,
    ) -> None:
        """publish_category_batch() should call _add_category_to_project."""
        from news.publisher import Publisher

        publisher = Publisher(config=sample_config)

        with (
            patch.object(
                publisher,
                "_check_category_issue_exists",
                return_value=None,
            ),
            patch.object(
                publisher,
                "_create_category_issue",
                return_value=(100, "https://github.com/YH-05/quants/issues/100"),
            ),
            patch.object(publisher, "_add_category_to_project") as mock_add_project,
        ):
            await publisher.publish_category_batch([sample_category_group])

            mock_add_project.assert_called_once_with(100, sample_category_group)


# ===========================================================================
# Tests: _check_category_issue_exists
# ===========================================================================


class TestCheckCategoryIssueExists:
    """Tests for _check_category_issue_exists() method."""

    @pytest.mark.asyncio
    async def test_正常系_既存Issueがある場合Issue番号を返す(
        self,
        sample_config: NewsWorkflowConfig,
    ) -> None:
        """_check_category_issue_exists should return issue number when found."""
        from news.publisher import Publisher

        publisher = Publisher(config=sample_config)

        mock_proc = AsyncMock()
        mock_proc.returncode = 0
        mock_proc.communicate = AsyncMock(
            return_value=(
                b'[{"number": 50, "title": "[\\u682a\\u4fa1\\u6307\\u6570] \\u30cb\\u30e5\\u30fc\\u30b9\\u307e\\u3068\\u3081 - 2026-02-09"}]',
                b"",
            )
        )

        with patch(
            "news.publisher.asyncio.create_subprocess_exec",
            return_value=mock_proc,
        ):
            result = await publisher._check_category_issue_exists(
                "株価指数", "2026-02-09"
            )

            assert result == 50

    @pytest.mark.asyncio
    async def test_正常系_既存Issueがない場合Noneを返す(
        self,
        sample_config: NewsWorkflowConfig,
    ) -> None:
        """_check_category_issue_exists should return None when not found."""
        from news.publisher import Publisher

        publisher = Publisher(config=sample_config)

        mock_proc = AsyncMock()
        mock_proc.returncode = 0
        mock_proc.communicate = AsyncMock(return_value=(b"[]", b""))

        with patch(
            "news.publisher.asyncio.create_subprocess_exec",
            return_value=mock_proc,
        ):
            result = await publisher._check_category_issue_exists(
                "株価指数", "2026-02-09"
            )

            assert result is None

    @pytest.mark.asyncio
    async def test_正常系_検索クエリにカテゴリラベルと日付を含む(
        self,
        sample_config: NewsWorkflowConfig,
    ) -> None:
        """_check_category_issue_exists should search with category label and date."""
        from news.publisher import Publisher

        publisher = Publisher(config=sample_config)

        mock_proc = AsyncMock()
        mock_proc.returncode = 0
        mock_proc.communicate = AsyncMock(return_value=(b"[]", b""))

        with patch(
            "news.publisher.asyncio.create_subprocess_exec",
            return_value=mock_proc,
        ) as mock_exec:
            await publisher._check_category_issue_exists("株価指数", "2026-02-09")

            mock_exec.assert_called_once()
            call_args = mock_exec.call_args[0]

            # Should use gh issue list with --search
            assert call_args[0] == "gh"
            assert call_args[1] == "issue"
            assert call_args[2] == "list"
            assert "--search" in call_args
            assert "--repo" in call_args
            assert "YH-05/quants" in call_args

    @pytest.mark.asyncio
    async def test_異常系_ghコマンド失敗でNoneを返す(
        self,
        sample_config: NewsWorkflowConfig,
    ) -> None:
        """_check_category_issue_exists should return None on gh command failure."""
        from news.publisher import Publisher

        publisher = Publisher(config=sample_config)

        mock_proc = AsyncMock()
        mock_proc.returncode = 1
        mock_proc.communicate = AsyncMock(return_value=(b"", b"Error: auth required"))

        with patch(
            "news.publisher.asyncio.create_subprocess_exec",
            return_value=mock_proc,
        ):
            result = await publisher._check_category_issue_exists(
                "株価指数", "2026-02-09"
            )

            assert result is None


# ===========================================================================
# Tests: _create_category_issue
# ===========================================================================


class TestCreateCategoryIssue:
    """Tests for _create_category_issue() method."""

    @pytest.mark.asyncio
    async def test_正常系_Issue番号とURLを返す(
        self,
        sample_config: NewsWorkflowConfig,
        sample_category_group: CategoryGroup,
    ) -> None:
        """_create_category_issue should return issue number and URL."""
        from news.publisher import Publisher

        publisher = Publisher(config=sample_config)

        with patch("news.publisher.subprocess.run") as mock_run:
            mock_result = MagicMock()
            mock_result.stdout = "https://github.com/YH-05/quants/issues/100\n"
            mock_result.returncode = 0
            mock_run.return_value = mock_result

            issue_number, issue_url = await publisher._create_category_issue(
                sample_category_group
            )

            assert issue_number == 100
            assert issue_url == "https://github.com/YH-05/quants/issues/100"

    @pytest.mark.asyncio
    async def test_正常系_CategoryMarkdownGeneratorでタイトルと本文を生成(
        self,
        sample_config: NewsWorkflowConfig,
        sample_category_group: CategoryGroup,
    ) -> None:
        """_create_category_issue should use CategoryMarkdownGenerator."""
        from news.publisher import Publisher

        publisher = Publisher(config=sample_config)

        with patch("news.publisher.subprocess.run") as mock_run:
            mock_result = MagicMock()
            mock_result.stdout = "https://github.com/YH-05/quants/issues/100\n"
            mock_result.returncode = 0
            mock_run.return_value = mock_result

            await publisher._create_category_issue(sample_category_group)

            # Verify gh issue create was called with correct title and body
            mock_run.assert_called_once()
            call_args = mock_run.call_args[0][0]

            assert "--title" in call_args
            title_idx = call_args.index("--title")
            title = call_args[title_idx + 1]
            assert title == "[株価指数] ニュースまとめ - 2026-02-09"

            assert "--body" in call_args
            body_idx = call_args.index("--body")
            body = call_args[body_idx + 1]
            assert "# [株価指数] ニュースまとめ - 2026-02-09" in body
            assert "1件の記事を収集" in body

    @pytest.mark.asyncio
    async def test_正常系_ghコマンドに正しいリポジトリを渡す(
        self,
        sample_config: NewsWorkflowConfig,
        sample_category_group: CategoryGroup,
    ) -> None:
        """_create_category_issue should pass correct repo to gh CLI."""
        from news.publisher import Publisher

        publisher = Publisher(config=sample_config)

        with patch("news.publisher.subprocess.run") as mock_run:
            mock_result = MagicMock()
            mock_result.stdout = "https://github.com/YH-05/quants/issues/100\n"
            mock_result.returncode = 0
            mock_run.return_value = mock_result

            await publisher._create_category_issue(sample_category_group)

            call_args = mock_run.call_args[0][0]
            assert "--repo" in call_args
            assert "YH-05/quants" in call_args


# ===========================================================================
# Tests: _add_category_to_project
# ===========================================================================


class TestAddCategoryToProject:
    """Tests for _add_category_to_project() method."""

    @pytest.mark.asyncio
    async def test_正常系_Projectに追加してフィールドを設定(
        self,
        sample_config: NewsWorkflowConfig,
        sample_category_group: CategoryGroup,
    ) -> None:
        """_add_category_to_project should add to project and set fields."""
        from news.publisher import Publisher

        publisher = Publisher(config=sample_config)

        with (
            patch.object(publisher, "_get_existing_project_item", return_value=None),
            patch("news.publisher.subprocess.run") as mock_run,
        ):
            mock_result = MagicMock()
            mock_result.stdout = '{"id": "PVTI_category_item"}\n'
            mock_result.returncode = 0
            mock_run.return_value = mock_result

            await publisher._add_category_to_project(100, sample_category_group)

            # Should call: item-add, item-edit (status), item-edit (date)
            assert mock_run.call_count == 3

    @pytest.mark.asyncio
    async def test_正常系_Statusフィールドにカテゴリのステータスを設定(
        self,
        sample_config: NewsWorkflowConfig,
        sample_category_group: CategoryGroup,
    ) -> None:
        """_add_category_to_project should set correct status for category."""
        from news.publisher import Publisher

        publisher = Publisher(config=sample_config)

        with (
            patch.object(publisher, "_get_existing_project_item", return_value=None),
            patch("news.publisher.subprocess.run") as mock_run,
        ):
            mock_result = MagicMock()
            mock_result.stdout = '{"id": "PVTI_category_item"}\n'
            mock_result.returncode = 0
            mock_run.return_value = mock_result

            await publisher._add_category_to_project(100, sample_category_group)

            # Check the status field edit call (second call)
            status_call_args = mock_run.call_args_list[1][0][0]
            assert "--single-select-option-id" in status_call_args
            # "index" category should use "test-index-id"
            assert "test-index-id" in status_call_args

    @pytest.mark.asyncio
    async def test_正常系_PublishedDateフィールドにグループ日付を設定(
        self,
        sample_config: NewsWorkflowConfig,
        sample_category_group: CategoryGroup,
    ) -> None:
        """_add_category_to_project should set date from group."""
        from news.publisher import Publisher

        publisher = Publisher(config=sample_config)

        with (
            patch.object(publisher, "_get_existing_project_item", return_value=None),
            patch("news.publisher.subprocess.run") as mock_run,
        ):
            mock_result = MagicMock()
            mock_result.stdout = '{"id": "PVTI_category_item"}\n'
            mock_result.returncode = 0
            mock_run.return_value = mock_result

            await publisher._add_category_to_project(100, sample_category_group)

            # Check the date field edit call (third call)
            date_call_args = mock_run.call_args_list[2][0][0]
            assert "--date" in date_call_args
            assert "2026-02-09" in date_call_args
