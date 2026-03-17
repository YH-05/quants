"""Unit tests for category-based data models (CategoryGroup, CategoryPublishResult).

Tests for Issue #3399: カテゴリ別データモデル・設定追加

Tests follow t-wada TDD naming conventions with Japanese test names.
"""

from datetime import datetime, timezone
from typing import Any

import pytest
from pydantic import ValidationError

# =============================================================================
# CategoryGroup Tests
# =============================================================================


class TestCategoryGroup:
    """CategoryGroup Pydantic モデルのテストクラス."""

    def test_正常系_必須フィールドで作成できる(self) -> None:
        """category, category_label, date, articles で CategoryGroup を作成できる."""
        from news.models import CategoryGroup

        group = CategoryGroup(
            category="index",
            category_label="株価指数",
            date="2026-02-09",
            articles=[],
        )

        assert group.category == "index"
        assert group.category_label == "株価指数"
        assert group.date == "2026-02-09"
        assert group.articles == []

    def test_正常系_記事を含むグループを作成できる(self) -> None:
        """SummarizedArticle を含む CategoryGroup を作成できる."""
        from news.models import (
            ArticleSource,
            CategoryGroup,
            CollectedArticle,
            ExtractedArticle,
            ExtractionStatus,
            SourceType,
            StructuredSummary,
            SummarizationStatus,
            SummarizedArticle,
        )

        source = ArticleSource(
            source_type=SourceType.RSS,
            source_name="CNBC Markets",
            category="market",
        )
        collected = CollectedArticle(
            url="https://www.cnbc.com/article/123",  # type: ignore[arg-type]
            title="Market Update",
            source=source,
            collected_at=datetime.now(tz=timezone.utc),
        )
        extracted = ExtractedArticle(
            collected=collected,
            body_text="Full article content here...",
            extraction_status=ExtractionStatus.SUCCESS,
            extraction_method="trafilatura",
        )
        summary = StructuredSummary(
            overview="Markets rallied today",
            key_points=["S&P 500 up 1%", "Tech leads gains"],
            market_impact="Bullish sentiment continues",
        )
        summarized = SummarizedArticle(
            extracted=extracted,
            summary=summary,
            summarization_status=SummarizationStatus.SUCCESS,
        )

        group = CategoryGroup(
            category="index",
            category_label="株価指数",
            date="2026-02-09",
            articles=[summarized],
        )

        assert len(group.articles) == 1
        assert group.articles[0].summary is not None
        assert group.articles[0].summary.overview == "Markets rallied today"

    def test_正常系_複数記事を含むグループを作成できる(self) -> None:
        """複数の SummarizedArticle を含む CategoryGroup を作成できる."""
        from news.models import (
            ArticleSource,
            CategoryGroup,
            CollectedArticle,
            ExtractedArticle,
            ExtractionStatus,
            SourceType,
            StructuredSummary,
            SummarizationStatus,
            SummarizedArticle,
        )

        articles = []
        for i in range(3):
            source = ArticleSource(
                source_type=SourceType.RSS,
                source_name=f"Source {i}",
                category="market",
            )
            collected = CollectedArticle(
                url=f"https://example.com/article/{i}",  # type: ignore[arg-type]
                title=f"Article {i}",
                source=source,
                collected_at=datetime.now(tz=timezone.utc),
            )
            extracted = ExtractedArticle(
                collected=collected,
                body_text=f"Content {i}",
                extraction_status=ExtractionStatus.SUCCESS,
                extraction_method="trafilatura",
            )
            summary = StructuredSummary(
                overview=f"Overview {i}",
                key_points=[f"Point {i}"],
                market_impact=f"Impact {i}",
            )
            articles.append(
                SummarizedArticle(
                    extracted=extracted,
                    summary=summary,
                    summarization_status=SummarizationStatus.SUCCESS,
                )
            )

        group = CategoryGroup(
            category="stock",
            category_label="個別銘柄",
            date="2026-02-09",
            articles=articles,
        )

        assert len(group.articles) == 3

    def test_異常系_categoryが欠落でValidationError(self) -> None:
        """category が欠落している場合 ValidationError が発生する."""
        from news.models import CategoryGroup

        with pytest.raises(ValidationError):
            CategoryGroup(
                category_label="株価指数",
                date="2026-02-09",
                articles=[],
            )

    def test_異常系_category_labelが欠落でValidationError(self) -> None:
        """category_label が欠落している場合 ValidationError が発生する."""
        from news.models import CategoryGroup

        with pytest.raises(ValidationError):
            CategoryGroup(
                category="index",
                date="2026-02-09",
                articles=[],
            )

    def test_異常系_dateが欠落でValidationError(self) -> None:
        """date が欠落している場合 ValidationError が発生する."""
        from news.models import CategoryGroup

        with pytest.raises(ValidationError):
            CategoryGroup(
                category="index",
                category_label="株価指数",
                articles=[],
            )

    def test_異常系_articlesが欠落でValidationError(self) -> None:
        """articles が欠落している場合 ValidationError が発生する."""
        from news.models import CategoryGroup

        with pytest.raises(ValidationError):
            CategoryGroup(
                category="index",
                category_label="株価指数",
                date="2026-02-09",
            )

    def test_エッジケース_空文字列のcategoryで作成できる(self) -> None:
        """空文字列の category でも CategoryGroup を作成できる."""
        from news.models import CategoryGroup

        group = CategoryGroup(
            category="",
            category_label="",
            date="",
            articles=[],
        )

        assert group.category == ""

    def test_正常系_JSON直列化と復元ができる(self) -> None:
        """CategoryGroup を JSON に直列化して復元できる."""
        from news.models import CategoryGroup

        group = CategoryGroup(
            category="index",
            category_label="株価指数",
            date="2026-02-09",
            articles=[],
        )

        json_str = group.model_dump_json()
        restored = CategoryGroup.model_validate_json(json_str)

        assert restored.category == group.category
        assert restored.category_label == group.category_label
        assert restored.date == group.date
        assert restored.articles == group.articles


# =============================================================================
# CategoryPublishResult Tests
# =============================================================================


class TestCategoryPublishResult:
    """CategoryPublishResult Pydantic モデルのテストクラス."""

    def test_正常系_成功時の結果を作成できる(self) -> None:
        """成功時の CategoryPublishResult を作成できる."""
        from news.models import CategoryPublishResult, PublicationStatus

        result = CategoryPublishResult(
            category="index",
            category_label="株価指数",
            date="2026-02-09",
            issue_number=100,
            issue_url="https://github.com/YH-05/quants/issues/100",
            article_count=5,
            status=PublicationStatus.SUCCESS,
        )

        assert result.category == "index"
        assert result.category_label == "株価指数"
        assert result.date == "2026-02-09"
        assert result.issue_number == 100
        assert result.issue_url == "https://github.com/YH-05/quants/issues/100"
        assert result.article_count == 5
        assert result.status == PublicationStatus.SUCCESS
        assert result.error_message is None

    def test_正常系_失敗時の結果を作成できる(self) -> None:
        """失敗時の CategoryPublishResult を作成できる."""
        from news.models import CategoryPublishResult, PublicationStatus

        result = CategoryPublishResult(
            category="stock",
            category_label="個別銘柄",
            date="2026-02-09",
            issue_number=None,
            issue_url=None,
            article_count=3,
            status=PublicationStatus.FAILED,
            error_message="GitHub API rate limit exceeded",
        )

        assert result.issue_number is None
        assert result.issue_url is None
        assert result.status == PublicationStatus.FAILED
        assert result.error_message == "GitHub API rate limit exceeded"

    def test_正常系_スキップ時の結果を作成できる(self) -> None:
        """スキップ時の CategoryPublishResult を作成できる."""
        from news.models import CategoryPublishResult, PublicationStatus

        result = CategoryPublishResult(
            category="macro",
            category_label="マクロ経済",
            date="2026-02-09",
            issue_number=None,
            issue_url=None,
            article_count=0,
            status=PublicationStatus.SKIPPED,
        )

        assert result.status == PublicationStatus.SKIPPED
        assert result.article_count == 0

    def test_正常系_error_messageのデフォルトはNone(self) -> None:
        """error_message はデフォルトで None."""
        from news.models import CategoryPublishResult, PublicationStatus

        result = CategoryPublishResult(
            category="index",
            category_label="株価指数",
            date="2026-02-09",
            issue_number=100,
            issue_url="https://github.com/YH-05/quants/issues/100",
            article_count=5,
            status=PublicationStatus.SUCCESS,
        )

        assert result.error_message is None

    def test_異常系_categoryが欠落でValidationError(self) -> None:
        """category が欠落している場合 ValidationError が発生する."""
        from news.models import CategoryPublishResult, PublicationStatus

        with pytest.raises(ValidationError):
            CategoryPublishResult(
                category_label="株価指数",
                date="2026-02-09",
                issue_number=100,
                issue_url="https://github.com/YH-05/quants/issues/100",
                article_count=5,
                status=PublicationStatus.SUCCESS,
            )

    def test_異常系_statusが欠落でValidationError(self) -> None:
        """status が欠落している場合 ValidationError が発生する."""
        from news.models import CategoryPublishResult

        with pytest.raises(ValidationError):
            CategoryPublishResult(
                category="index",
                category_label="株価指数",
                date="2026-02-09",
                issue_number=100,
                issue_url="https://github.com/YH-05/quants/issues/100",
                article_count=5,
            )

    def test_異常系_article_countが欠落でValidationError(self) -> None:
        """article_count が欠落している場合 ValidationError が発生する."""
        from news.models import CategoryPublishResult, PublicationStatus

        with pytest.raises(ValidationError):
            CategoryPublishResult(
                category="index",
                category_label="株価指数",
                date="2026-02-09",
                issue_number=100,
                issue_url="https://github.com/YH-05/quants/issues/100",
                status=PublicationStatus.SUCCESS,
            )

    def test_正常系_JSON直列化と復元ができる(self) -> None:
        """CategoryPublishResult を JSON に直列化して復元できる."""
        from news.models import CategoryPublishResult, PublicationStatus

        result = CategoryPublishResult(
            category="index",
            category_label="株価指数",
            date="2026-02-09",
            issue_number=100,
            issue_url="https://github.com/YH-05/quants/issues/100",
            article_count=5,
            status=PublicationStatus.SUCCESS,
        )

        json_str = result.model_dump_json()
        restored = CategoryPublishResult.model_validate_json(json_str)

        assert restored.category == result.category
        assert restored.issue_number == result.issue_number
        assert restored.status == result.status

    def test_正常系_全PublicationStatusで作成できる(self) -> None:
        """全ての PublicationStatus 値で CategoryPublishResult を作成できる."""
        from news.models import CategoryPublishResult, PublicationStatus

        for status in PublicationStatus:
            result = CategoryPublishResult(
                category="index",
                category_label="株価指数",
                date="2026-02-09",
                issue_number=None,
                issue_url=None,
                article_count=1,
                status=status,
            )
            assert result.status == status


# =============================================================================
# WorkflowResult category_results Tests
# =============================================================================


class TestWorkflowResultCategoryResults:
    """WorkflowResult の category_results フィールドのテストクラス."""

    def _make_workflow_result(self, **kwargs: Any) -> Any:
        """WorkflowResult の必須フィールドを含むヘルパー."""
        from news.models import WorkflowResult

        defaults: dict[str, Any] = {
            "total_collected": 10,
            "total_extracted": 8,
            "total_summarized": 7,
            "total_published": 5,
            "total_duplicates": 2,
            "extraction_failures": [],
            "summarization_failures": [],
            "publication_failures": [],
            "started_at": datetime(2026, 2, 9, 10, 0, 0, tzinfo=timezone.utc),
            "finished_at": datetime(2026, 2, 9, 10, 5, 0, tzinfo=timezone.utc),
            "elapsed_seconds": 300.0,
            "published_articles": [],
        }
        defaults.update(kwargs)
        return WorkflowResult(**defaults)

    def test_正常系_category_resultsのデフォルトは空リスト(self) -> None:
        """category_results はデフォルトで空リスト."""
        from news.models import WorkflowResult

        result = self._make_workflow_result()

        assert isinstance(result, WorkflowResult)
        assert result.category_results == []

    def test_正常系_category_resultsにCategoryPublishResultを設定できる(self) -> None:
        """category_results に CategoryPublishResult のリストを設定できる."""
        from news.models import CategoryPublishResult, PublicationStatus, WorkflowResult

        category_results = [
            CategoryPublishResult(
                category="index",
                category_label="株価指数",
                date="2026-02-09",
                issue_number=100,
                issue_url="https://github.com/YH-05/quants/issues/100",
                article_count=5,
                status=PublicationStatus.SUCCESS,
            ),
            CategoryPublishResult(
                category="stock",
                category_label="個別銘柄",
                date="2026-02-09",
                issue_number=101,
                issue_url="https://github.com/YH-05/quants/issues/101",
                article_count=3,
                status=PublicationStatus.SUCCESS,
            ),
        ]

        result = self._make_workflow_result(category_results=category_results)

        assert isinstance(result, WorkflowResult)
        assert len(result.category_results) == 2
        assert result.category_results[0].category == "index"
        assert result.category_results[1].category == "stock"

    def test_正常系_既存フィールドとcategory_resultsが共存できる(self) -> None:
        """既存の WorkflowResult フィールドと category_results が共存する."""
        from news.models import CategoryPublishResult, PublicationStatus, WorkflowResult

        category_results = [
            CategoryPublishResult(
                category="index",
                category_label="株価指数",
                date="2026-02-09",
                issue_number=100,
                issue_url="https://github.com/YH-05/quants/issues/100",
                article_count=5,
                status=PublicationStatus.SUCCESS,
            ),
        ]

        result = self._make_workflow_result(
            total_collected=20,
            category_results=category_results,
        )

        assert isinstance(result, WorkflowResult)
        assert result.total_collected == 20
        assert len(result.category_results) == 1


# =============================================================================
# PublishingConfig Tests
# =============================================================================


class TestPublishingConfig:
    """PublishingConfig 設定モデルのテストクラス."""

    def test_正常系_デフォルト値で作成できる(self) -> None:
        """デフォルト値で PublishingConfig を作成できる."""
        from news.config.models import PublishingConfig

        config = PublishingConfig()

        assert config.format == "per_category"
        assert config.export_markdown is True
        assert config.export_dir == "data/exports/news-workflow"

    def test_正常系_カスタム値で作成できる(self) -> None:
        """カスタム値で PublishingConfig を作成できる."""
        from news.config.models import PublishingConfig

        config = PublishingConfig(
            format="per_article",
            export_markdown=False,
            export_dir="/custom/path",
        )

        assert config.format == "per_article"
        assert config.export_markdown is False
        assert config.export_dir == "/custom/path"

    def test_正常系_JSON直列化と復元ができる(self) -> None:
        """PublishingConfig を JSON に直列化して復元できる."""
        from news.config.models import PublishingConfig

        config = PublishingConfig(
            format="per_category",
            export_markdown=True,
            export_dir="data/exports/news-workflow",
        )

        json_str = config.model_dump_json()
        restored = PublishingConfig.model_validate_json(json_str)

        assert restored.format == config.format
        assert restored.export_markdown == config.export_markdown
        assert restored.export_dir == config.export_dir


# =============================================================================
# CategoryLabelsConfig Tests
# =============================================================================


class TestCategoryLabelsConfig:
    """CategoryLabelsConfig 設定モデルのテストクラス."""

    def test_正常系_デフォルト値で作成できる(self) -> None:
        """デフォルトのカテゴリラベルで作成できる."""
        from news.config.models import CategoryLabelsConfig

        config = CategoryLabelsConfig()

        assert config.index == "株価指数"
        assert config.stock == "個別銘柄"
        assert config.sector == "セクター"
        assert config.macro == "マクロ経済"
        assert config.ai == "AI関連"
        assert config.finance == "金融"

    def test_正常系_カスタム値で作成できる(self) -> None:
        """カスタムラベルで CategoryLabelsConfig を作成できる."""
        from news.config.models import CategoryLabelsConfig

        config = CategoryLabelsConfig(
            index="Index",
            stock="Stock",
            sector="Sector",
            macro="Macro",
            ai="AI",
            finance="Finance",
        )

        assert config.index == "Index"
        assert config.stock == "Stock"

    def test_正常系_get_labelでカテゴリ名からラベルを取得できる(self) -> None:
        """get_label メソッドでカテゴリ名から日本語ラベルを取得できる."""
        from news.config.models import CategoryLabelsConfig

        config = CategoryLabelsConfig()

        assert config.get_label("index") == "株価指数"
        assert config.get_label("stock") == "個別銘柄"
        assert config.get_label("sector") == "セクター"
        assert config.get_label("macro") == "マクロ経済"
        assert config.get_label("ai") == "AI関連"
        assert config.get_label("finance") == "金融"

    def test_正常系_get_labelで未知のカテゴリはカテゴリ名をそのまま返す(self) -> None:
        """get_label で未知のカテゴリはカテゴリ名をそのまま返す."""
        from news.config.models import CategoryLabelsConfig

        config = CategoryLabelsConfig()

        assert config.get_label("unknown") == "unknown"
        assert config.get_label("custom_category") == "custom_category"

    def test_正常系_JSON直列化と復元ができる(self) -> None:
        """CategoryLabelsConfig を JSON に直列化して復元できる."""
        from news.config.models import CategoryLabelsConfig

        config = CategoryLabelsConfig()

        json_str = config.model_dump_json()
        restored = CategoryLabelsConfig.model_validate_json(json_str)

        assert restored.index == config.index
        assert restored.stock == config.stock
        assert restored.sector == config.sector


# =============================================================================
# NewsWorkflowConfig Integration Tests
# =============================================================================


class TestNewsWorkflowConfigWithPublishing:
    """NewsWorkflowConfig に publishing, category_labels が統合されたテスト."""

    def test_正常系_publishingとcategory_labelsのデフォルト値(self) -> None:
        """NewsWorkflowConfig で publishing, category_labels がデフォルト値を持つ."""
        from news.config.models import (
            GitHubConfig,
            NewsWorkflowConfig,
            OutputConfig,
            RssConfig,
            SummarizationConfig,
        )

        config = NewsWorkflowConfig(
            version="1.0",
            status_mapping={"tech": "ai"},
            github_status_ids={"ai": "6fbb43d0"},
            rss=RssConfig(presets_file="rss-presets.json"),
            summarization=SummarizationConfig(prompt_template="test"),
            github=GitHubConfig(
                project_number=15,
                project_id="PVT_test",
                status_field_id="PVTSSF_test",
                published_date_field_id="PVTF_test",
                repository="owner/repo",
            ),
            output=OutputConfig(result_dir="data/exports"),
        )

        assert config.publishing.format == "per_category"
        assert config.publishing.export_markdown is True
        assert config.category_labels.index == "株価指数"

    def test_正常系_publishingとcategory_labelsをカスタム設定できる(self) -> None:
        """NewsWorkflowConfig で publishing, category_labels をカスタム設定できる."""
        from news.config.models import (
            CategoryLabelsConfig,
            GitHubConfig,
            NewsWorkflowConfig,
            OutputConfig,
            PublishingConfig,
            RssConfig,
            SummarizationConfig,
        )

        config = NewsWorkflowConfig(
            version="1.0",
            status_mapping={"tech": "ai"},
            github_status_ids={"ai": "6fbb43d0"},
            rss=RssConfig(presets_file="rss-presets.json"),
            summarization=SummarizationConfig(prompt_template="test"),
            github=GitHubConfig(
                project_number=15,
                project_id="PVT_test",
                status_field_id="PVTSSF_test",
                published_date_field_id="PVTF_test",
                repository="owner/repo",
            ),
            output=OutputConfig(result_dir="data/exports"),
            publishing=PublishingConfig(
                format="per_article",
                export_markdown=False,
            ),
            category_labels=CategoryLabelsConfig(
                index="Indices",
            ),
        )

        assert config.publishing.format == "per_article"
        assert config.publishing.export_markdown is False
        assert config.category_labels.index == "Indices"


# =============================================================================
# __all__ Exports Tests
# =============================================================================


class TestModelsExports:
    """models.py の __all__ エクスポートのテストクラス."""

    def test_正常系_CategoryGroupがエクスポートされている(self) -> None:
        """CategoryGroup が __all__ に含まれている."""
        from news.models import __all__ as models_all

        assert "CategoryGroup" in models_all

    def test_正常系_CategoryPublishResultがエクスポートされている(self) -> None:
        """CategoryPublishResult が __all__ に含まれている."""
        from news.models import __all__ as models_all

        assert "CategoryPublishResult" in models_all


class TestConfigModelsExports:
    """config/models.py の __all__ エクスポートのテストクラス."""

    def test_正常系_PublishingConfigがエクスポートされている(self) -> None:
        """PublishingConfig が __all__ に含まれている."""
        from news.config.models import __all__ as config_all

        assert "PublishingConfig" in config_all

    def test_正常系_CategoryLabelsConfigがエクスポートされている(self) -> None:
        """CategoryLabelsConfig が __all__ に含まれている."""
        from news.config.models import __all__ as config_all

        assert "CategoryLabelsConfig" in config_all
