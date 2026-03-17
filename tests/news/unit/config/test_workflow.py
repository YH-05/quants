"""Unit tests for NewsWorkflowConfig and load_config function.

Tests for Issue #2370: config.py 設定ファイル読み込み機能

This module tests the workflow configuration models and loading function
for the news collection workflow.
"""

from pathlib import Path

import pytest
from pydantic import ValidationError


class TestRssConfig:
    """Test RssConfig Pydantic model."""

    def test_正常系_必須パラメータで作成できる(self) -> None:
        """RssConfigを必須パラメータで作成できることを確認。"""
        from news.config.models import RssConfig

        config = RssConfig(presets_file="data/config/rss-presets.json")

        assert config.presets_file == "data/config/rss-presets.json"

    def test_異常系_presets_file未指定でValidationError(self) -> None:
        """presets_fileが未指定の場合、ValidationErrorが発生することを確認。"""
        from news.config.models import RssConfig

        with pytest.raises(ValidationError):
            RssConfig()


class TestRssConfigWithUserAgentRotation:
    """Test RssConfig with user_agent_rotation field."""

    def test_正常系_user_agent_rotationがデフォルト値で作成される(self) -> None:
        """RssConfigのuser_agent_rotationがデフォルト値で作成されることを確認。"""
        from news.config.models import RssConfig, UserAgentRotationConfig

        config = RssConfig(presets_file="data/config/rss-presets.json")

        assert isinstance(config.user_agent_rotation, UserAgentRotationConfig)
        assert config.user_agent_rotation.enabled is True
        assert config.user_agent_rotation.user_agents == []

    def test_正常系_user_agent_rotationをカスタム値で作成できる(self) -> None:
        """RssConfigのuser_agent_rotationをカスタム値で作成できることを確認。"""
        from news.config.models import RssConfig, UserAgentRotationConfig

        ua_config = UserAgentRotationConfig(
            enabled=True,
            user_agents=["UA1", "UA2"],
        )
        config = RssConfig(
            presets_file="data/config/rss-presets.json",
            user_agent_rotation=ua_config,
        )

        assert config.user_agent_rotation.enabled is True
        assert config.user_agent_rotation.user_agents == ["UA1", "UA2"]

    def test_正常系_dictからuser_agent_rotationを含めて作成できる(self) -> None:
        """RssConfigを辞書からuser_agent_rotationを含めて作成できることを確認。"""
        from news.config.models import RssConfig

        data = {
            "presets_file": "data/config/rss-presets.json",
            "user_agent_rotation": {
                "enabled": True,
                "user_agents": ["Mozilla/5.0 (Windows)", "Mozilla/5.0 (Mac)"],
            },
        }
        config = RssConfig.model_validate(data)

        assert config.user_agent_rotation.enabled is True
        assert len(config.user_agent_rotation.user_agents) == 2

    def test_正常系_user_agent_rotation無効化できる(self) -> None:
        """RssConfigのuser_agent_rotationをenabled=Falseで作成できることを確認。"""
        from news.config.models import RssConfig, UserAgentRotationConfig

        ua_config = UserAgentRotationConfig(
            enabled=False,
            user_agents=["UA1"],
        )
        config = RssConfig(
            presets_file="data/config/rss-presets.json",
            user_agent_rotation=ua_config,
        )

        assert config.user_agent_rotation.enabled is False
        assert config.user_agent_rotation.get_random_user_agent() is None


class TestExtractionConfig:
    """Test ExtractionConfig Pydantic model."""

    def test_正常系_デフォルト値で作成できる(self) -> None:
        """ExtractionConfigをデフォルト値で作成できることを確認。"""
        from news.config.models import ExtractionConfig

        config = ExtractionConfig()

        assert config.concurrency == 5
        assert config.timeout_seconds == 30
        assert config.min_body_length == 200
        assert config.max_retries == 3

    def test_正常系_カスタム値で作成できる(self) -> None:
        """ExtractionConfigをカスタム値で作成できることを確認。"""
        from news.config.models import ExtractionConfig

        config = ExtractionConfig(
            concurrency=10,
            timeout_seconds=60,
            min_body_length=100,
            max_retries=5,
        )

        assert config.concurrency == 10
        assert config.timeout_seconds == 60
        assert config.min_body_length == 100
        assert config.max_retries == 5

    def test_異常系_負のconcurrencyでValidationError(self) -> None:
        """concurrencyが負の値の場合、ValidationErrorが発生することを確認。"""
        from news.config.models import ExtractionConfig

        with pytest.raises(ValidationError):
            ExtractionConfig(concurrency=-1)


class TestSummarizationConfig:
    """Test SummarizationConfig Pydantic model."""

    def test_正常系_デフォルト値で作成できる(self) -> None:
        """SummarizationConfigをデフォルト値で作成できることを確認。"""
        from news.config.models import SummarizationConfig

        config = SummarizationConfig(prompt_template="test template")

        assert config.concurrency == 3
        assert config.timeout_seconds == 60
        assert config.max_retries == 3
        assert config.prompt_template == "test template"

    def test_異常系_prompt_template未指定でValidationError(self) -> None:
        """prompt_templateが未指定の場合、ValidationErrorが発生することを確認。"""
        from news.config.models import SummarizationConfig

        with pytest.raises(ValidationError):
            SummarizationConfig()


class TestGitHubConfig:
    """Test GitHubConfig Pydantic model for workflow."""

    def test_正常系_必須パラメータで作成できる(self) -> None:
        """GitHubConfigを必須パラメータで作成できることを確認。"""
        from news.config.models import GitHubConfig

        config = GitHubConfig(
            project_number=15,
            project_id="PVT_kwHOBoK6AM4BMpw_",
            status_field_id="PVTSSF_lAHOBoK6AM4BMpw_zg739ZE",
            published_date_field_id="PVTF_lAHOBoK6AM4BMpw_zg8BzrI",
            repository="YH-05/quants",
        )

        assert config.project_number == 15
        assert config.project_id == "PVT_kwHOBoK6AM4BMpw_"
        assert config.status_field_id == "PVTSSF_lAHOBoK6AM4BMpw_zg739ZE"
        assert config.published_date_field_id == "PVTF_lAHOBoK6AM4BMpw_zg8BzrI"
        assert config.repository == "YH-05/quants"
        assert config.duplicate_check_days == 7  # デフォルト値
        assert config.dry_run is False  # デフォルト値

    def test_正常系_全パラメータで作成できる(self) -> None:
        """GitHubConfigを全パラメータで作成できることを確認。"""
        from news.config.models import GitHubConfig

        config = GitHubConfig(
            project_number=15,
            project_id="PVT_kwHOBoK6AM4BMpw_",
            status_field_id="PVTSSF_lAHOBoK6AM4BMpw_zg739ZE",
            published_date_field_id="PVTF_lAHOBoK6AM4BMpw_zg8BzrI",
            repository="YH-05/quants",
            duplicate_check_days=14,
            dry_run=True,
        )

        assert config.duplicate_check_days == 14
        assert config.dry_run is True

    def test_異常系_project_number未指定でValidationError(self) -> None:
        """project_numberが未指定の場合、ValidationErrorが発生することを確認。"""
        from news.config.models import GitHubConfig

        with pytest.raises(ValidationError):
            GitHubConfig(
                project_id="PVT_kwHOBoK6AM4BMpw_",
                status_field_id="PVTSSF_lAHOBoK6AM4BMpw_zg739ZE",
                published_date_field_id="PVTF_lAHOBoK6AM4BMpw_zg8BzrI",
                repository="YH-05/quants",
            )


class TestFilteringConfig:
    """Test FilteringConfig Pydantic model."""

    def test_正常系_デフォルト値で作成できる(self) -> None:
        """FilteringConfigをデフォルト値で作成できることを確認。"""
        from news.config.models import FilteringConfig

        config = FilteringConfig()

        assert config.max_age_hours == 168  # 7日

    def test_正常系_カスタム値で作成できる(self) -> None:
        """FilteringConfigをカスタム値で作成できることを確認。"""
        from news.config.models import FilteringConfig

        config = FilteringConfig(max_age_hours=24)

        assert config.max_age_hours == 24


class TestOutputConfig:
    """Test OutputConfig Pydantic model."""

    def test_正常系_必須パラメータで作成できる(self) -> None:
        """OutputConfigを必須パラメータで作成できることを確認。"""
        from news.config.models import OutputConfig

        config = OutputConfig(result_dir="data/exports/news-workflow")

        assert config.result_dir == "data/exports/news-workflow"

    def test_異常系_result_dir未指定でValidationError(self) -> None:
        """result_dirが未指定の場合、ValidationErrorが発生することを確認。"""
        from news.config.models import OutputConfig

        with pytest.raises(ValidationError):
            OutputConfig()


class TestNewsWorkflowConfig:
    """Test NewsWorkflowConfig root Pydantic model."""

    def test_正常系_必須パラメータで作成できる(self) -> None:
        """NewsWorkflowConfigを必須パラメータで作成できることを確認。"""
        from news.config.models import (
            ExtractionConfig,
            FilteringConfig,
            GitHubConfig,
            NewsWorkflowConfig,
            OutputConfig,
            RssConfig,
            SummarizationConfig,
        )

        config = NewsWorkflowConfig(
            version="1.0",
            status_mapping={"tech": "ai", "market": "index"},
            github_status_ids={"ai": "6fbb43d0", "index": "3925acc3"},
            rss=RssConfig(presets_file="data/config/rss-presets.json"),
            extraction=ExtractionConfig(),
            summarization=SummarizationConfig(prompt_template="test template"),
            github=GitHubConfig(
                project_number=15,
                project_id="PVT_kwHOBoK6AM4BMpw_",
                status_field_id="PVTSSF_lAHOBoK6AM4BMpw_zg739ZE",
                published_date_field_id="PVTF_lAHOBoK6AM4BMpw_zg8BzrI",
                repository="YH-05/quants",
            ),
            filtering=FilteringConfig(),
            output=OutputConfig(result_dir="data/exports/news-workflow"),
        )

        assert config.version == "1.0"
        assert config.status_mapping == {"tech": "ai", "market": "index"}
        assert config.github_status_ids == {"ai": "6fbb43d0", "index": "3925acc3"}
        assert config.rss.presets_file == "data/config/rss-presets.json"
        assert config.extraction.concurrency == 5
        assert config.summarization.prompt_template == "test template"
        assert config.github.project_number == 15
        assert config.filtering.max_age_hours == 168
        assert config.output.result_dir == "data/exports/news-workflow"

    def test_正常系_status_mappingでカテゴリからStatusを解決できる(self) -> None:
        """status_mappingでカテゴリからGitHub Statusを解決できることを確認。"""
        from news.config.models import (
            ExtractionConfig,
            FilteringConfig,
            GitHubConfig,
            NewsWorkflowConfig,
            OutputConfig,
            RssConfig,
            SummarizationConfig,
        )

        config = NewsWorkflowConfig(
            version="1.0",
            status_mapping={
                "tech": "ai",
                "market": "index",
                "finance": "finance",
                "yf_index": "index",
                "yf_stock": "stock",
            },
            github_status_ids={
                "ai": "6fbb43d0",
                "index": "3925acc3",
                "finance": "ac4a91b1",
                "stock": "f762022e",
            },
            rss=RssConfig(presets_file="data/config/rss-presets.json"),
            extraction=ExtractionConfig(),
            summarization=SummarizationConfig(prompt_template="test"),
            github=GitHubConfig(
                project_number=15,
                project_id="PVT_kwHOBoK6AM4BMpw_",
                status_field_id="PVTSSF_lAHOBoK6AM4BMpw_zg739ZE",
                published_date_field_id="PVTF_lAHOBoK6AM4BMpw_zg8BzrI",
                repository="YH-05/quants",
            ),
            filtering=FilteringConfig(),
            output=OutputConfig(result_dir="data/exports"),
        )

        # カテゴリからStatusを解決
        assert config.status_mapping["tech"] == "ai"
        assert config.status_mapping["yf_index"] == "index"

        # Status名からIDを解決
        assert config.github_status_ids["ai"] == "6fbb43d0"
        assert config.github_status_ids["index"] == "3925acc3"

    def test_正常系_dictから作成できる(self) -> None:
        """NewsWorkflowConfigを辞書から作成できることを確認。"""
        from news.config.models import NewsWorkflowConfig

        data = {
            "version": "1.0",
            "status_mapping": {"tech": "ai", "market": "index"},
            "github_status_ids": {"ai": "6fbb43d0", "index": "3925acc3"},
            "rss": {"presets_file": "data/config/rss-presets.json"},
            "extraction": {"concurrency": 10},
            "summarization": {"prompt_template": "test template"},
            "github": {
                "project_number": 15,
                "project_id": "PVT_kwHOBoK6AM4BMpw_",
                "status_field_id": "PVTSSF_lAHOBoK6AM4BMpw_zg739ZE",
                "published_date_field_id": "PVTF_lAHOBoK6AM4BMpw_zg8BzrI",
                "repository": "YH-05/quants",
            },
            "filtering": {"max_age_hours": 24},
            "output": {"result_dir": "data/exports"},
        }

        config = NewsWorkflowConfig.model_validate(data)

        assert config.version == "1.0"
        assert config.extraction.concurrency == 10
        assert config.filtering.max_age_hours == 24


class TestLoadConfig:
    """Test load_config function."""

    def test_正常系_YAML設定ファイルを読み込める(self, tmp_path: Path) -> None:
        """load_configがYAML設定ファイルを読み込めることを確認。"""
        from news.config.models import load_config

        # Arrange: YAML設定ファイルを作成
        config_file = tmp_path / "config.yaml"
        config_file.write_text(
            """
version: "1.0"

status_mapping:
  tech: "ai"
  market: "index"

github_status_ids:
  ai: "6fbb43d0"
  index: "3925acc3"

rss:
  presets_file: "data/config/rss-presets.json"

extraction:
  concurrency: 10
  timeout_seconds: 60
  min_body_length: 100
  max_retries: 5

summarization:
  concurrency: 5
  timeout_seconds: 120
  max_retries: 3
  prompt_template: |
    Test prompt template.

github:
  project_number: 15
  project_id: "PVT_kwHOBoK6AM4BMpw_"
  status_field_id: "PVTSSF_lAHOBoK6AM4BMpw_zg739ZE"
  published_date_field_id: "PVTF_lAHOBoK6AM4BMpw_zg8BzrI"
  repository: "YH-05/quants"
  duplicate_check_days: 14
  dry_run: true

filtering:
  max_age_hours: 48

output:
  result_dir: "data/exports/news-workflow"
"""
        )

        # Act
        config = load_config(config_file)

        # Assert
        assert config.version == "1.0"
        assert config.status_mapping == {"tech": "ai", "market": "index"}
        assert config.github_status_ids == {"ai": "6fbb43d0", "index": "3925acc3"}
        assert config.rss.presets_file == "data/config/rss-presets.json"
        assert config.extraction.concurrency == 10
        assert config.summarization.concurrency == 5
        assert config.github.project_number == 15
        assert config.github.dry_run is True
        assert config.filtering.max_age_hours == 48
        assert config.output.result_dir == "data/exports/news-workflow"

    def test_正常系_文字列パスで読み込める(self, tmp_path: Path) -> None:
        """load_configが文字列パスでも読み込めることを確認。"""
        from news.config.models import load_config

        # Arrange
        config_file = tmp_path / "config.yaml"
        config_file.write_text(
            """
version: "1.0"
status_mapping:
  tech: "ai"
github_status_ids:
  ai: "6fbb43d0"
rss:
  presets_file: "data/config/rss-presets.json"
extraction: {}
summarization:
  prompt_template: "test"
github:
  project_number: 15
  project_id: "PVT_kwHOBoK6AM4BMpw_"
  status_field_id: "PVTSSF_lAHOBoK6AM4BMpw_zg739ZE"
  published_date_field_id: "PVTF_lAHOBoK6AM4BMpw_zg8BzrI"
  repository: "YH-05/quants"
filtering: {}
output:
  result_dir: "data/exports"
"""
        )

        # Act - 文字列パスで呼び出し
        config = load_config(str(config_file))

        # Assert
        assert config.version == "1.0"

    def test_異常系_存在しないファイルでFileNotFoundError(self) -> None:
        """存在しないファイルを読み込むとFileNotFoundErrorが発生することを確認。"""
        from news.config.models import load_config

        with pytest.raises(FileNotFoundError):
            load_config(Path("/nonexistent/config.yaml"))

    def test_異常系_不正なYAMLでエラー(self, tmp_path: Path) -> None:
        """不正なYAMLファイルを読み込むとエラーが発生することを確認。"""
        from yaml import YAMLError

        from news.config.models import load_config

        # Arrange: 不正なYAMLファイルを作成
        config_file = tmp_path / "invalid.yaml"
        config_file.write_text(
            """
version: "1.0"
  - this is invalid yaml structure
"""
        )

        # Act & Assert
        with pytest.raises(YAMLError):
            load_config(config_file)

    def test_異常系_バリデーションエラー(self, tmp_path: Path) -> None:
        """必須フィールドがない場合、ValidationErrorが発生することを確認。"""
        from news.config.models import load_config

        # Arrange: 必須フィールドがないYAMLファイルを作成
        config_file = tmp_path / "incomplete.yaml"
        config_file.write_text(
            """
version: "1.0"
# rss, github など必須フィールドが欠けている
"""
        )

        # Act & Assert
        with pytest.raises(ValidationError):
            load_config(config_file)


class TestDomainFilteringConfig:
    """Test DomainFilteringConfig Pydantic model."""

    def test_正常系_デフォルト値で作成できる(self) -> None:
        """DomainFilteringConfigをデフォルト値で作成できることを確認。"""
        from news.config.models import DomainFilteringConfig

        config = DomainFilteringConfig()

        assert config.enabled is True
        assert config.log_blocked is True
        assert config.blocked_domains == []

    def test_正常系_ブロックドメインがTrueを返す(self) -> None:
        """ブロックドメインに対してis_blockedがTrueを返すことを確認。"""
        from news.config.models import DomainFilteringConfig

        config = DomainFilteringConfig(blocked_domains=["seekingalpha.com"])

        assert config.is_blocked("https://seekingalpha.com/article/123")

    def test_正常系_サブドメインもブロックされる(self) -> None:
        """サブドメインもブロックされることを確認。"""
        from news.config.models import DomainFilteringConfig

        config = DomainFilteringConfig(blocked_domains=["seekingalpha.com"])

        assert config.is_blocked("https://www.seekingalpha.com/article/123")
        assert config.is_blocked("https://api.seekingalpha.com/v1/data")

    def test_正常系_許可ドメインはFalseを返す(self) -> None:
        """許可ドメインに対してis_blockedがFalseを返すことを確認。"""
        from news.config.models import DomainFilteringConfig

        config = DomainFilteringConfig(blocked_domains=["seekingalpha.com"])

        assert not config.is_blocked("https://cnbc.com/article/123")
        assert not config.is_blocked("https://www.cnbc.com/article/123")

    def test_正常系_無効時は全て許可(self) -> None:
        """enabled=Falseの時は全てのドメインが許可されることを確認。"""
        from news.config.models import DomainFilteringConfig

        config = DomainFilteringConfig(
            enabled=False,
            blocked_domains=["seekingalpha.com"],
        )

        assert not config.is_blocked("https://seekingalpha.com/article/123")
        assert not config.is_blocked("https://www.seekingalpha.com/article/123")

    def test_正常系_大文字小文字を区別しない(self) -> None:
        """ドメインの大文字小文字を区別しないことを確認。"""
        from news.config.models import DomainFilteringConfig

        config = DomainFilteringConfig(blocked_domains=["SeekingAlpha.com"])

        assert config.is_blocked("https://seekingalpha.com/article/123")
        assert config.is_blocked("https://SEEKINGALPHA.COM/article/123")

    def test_正常系_複数ドメインをブロックできる(self) -> None:
        """複数のドメインをブロックできることを確認。"""
        from news.config.models import DomainFilteringConfig

        config = DomainFilteringConfig(
            blocked_domains=["seekingalpha.com", "example.com", "test.org"]
        )

        assert config.is_blocked("https://seekingalpha.com/article/123")
        assert config.is_blocked("https://example.com/page")
        assert config.is_blocked("https://test.org/")
        assert not config.is_blocked("https://cnbc.com/")

    def test_正常系_空リストで全て許可(self) -> None:
        """空のブロックリストで全てのドメインが許可されることを確認。"""
        from news.config.models import DomainFilteringConfig

        config = DomainFilteringConfig(blocked_domains=[])

        assert not config.is_blocked("https://seekingalpha.com/article/123")
        assert not config.is_blocked("https://cnbc.com/article/123")

    def test_エッジケース_類似ドメイン名は許可される(self) -> None:
        """類似しているが異なるドメインは許可されることを確認。"""
        from news.config.models import DomainFilteringConfig

        config = DomainFilteringConfig(blocked_domains=["example.com"])

        # notexample.com は example.com のサブドメインではない
        assert not config.is_blocked("https://notexample.com/page")
        # myexample.com も許可
        assert not config.is_blocked("https://myexample.com/page")


class TestNewsWorkflowConfigWithDomainFiltering:
    """Test NewsWorkflowConfig with domain_filtering field."""

    def test_正常系_domain_filteringがデフォルト値で作成される(self) -> None:
        """domain_filteringがデフォルト値で作成されることを確認。"""
        from news.config.models import (
            DomainFilteringConfig,
            ExtractionConfig,
            FilteringConfig,
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
            rss=RssConfig(presets_file="data/config/rss-presets.json"),
            extraction=ExtractionConfig(),
            summarization=SummarizationConfig(prompt_template="test"),
            github=GitHubConfig(
                project_number=15,
                project_id="PVT_test",
                status_field_id="PVTSSF_test",
                published_date_field_id="PVTF_test",
                repository="owner/repo",
            ),
            filtering=FilteringConfig(),
            output=OutputConfig(result_dir="data/exports"),
        )

        assert isinstance(config.domain_filtering, DomainFilteringConfig)
        assert config.domain_filtering.enabled is True
        assert config.domain_filtering.blocked_domains == []

    def test_正常系_domain_filteringをカスタム値で作成できる(self) -> None:
        """domain_filteringをカスタム値で作成できることを確認。"""
        from news.config.models import (
            DomainFilteringConfig,
            ExtractionConfig,
            FilteringConfig,
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
            rss=RssConfig(presets_file="data/config/rss-presets.json"),
            extraction=ExtractionConfig(),
            summarization=SummarizationConfig(prompt_template="test"),
            github=GitHubConfig(
                project_number=15,
                project_id="PVT_test",
                status_field_id="PVTSSF_test",
                published_date_field_id="PVTF_test",
                repository="owner/repo",
            ),
            filtering=FilteringConfig(),
            output=OutputConfig(result_dir="data/exports"),
            domain_filtering=DomainFilteringConfig(
                enabled=True,
                log_blocked=False,
                blocked_domains=["seekingalpha.com", "example.com"],
            ),
        )

        assert config.domain_filtering.enabled is True
        assert config.domain_filtering.log_blocked is False
        assert config.domain_filtering.blocked_domains == [
            "seekingalpha.com",
            "example.com",
        ]


class TestLoadConfigWithDomainFiltering:
    """Test load_config function with domain_filtering."""

    def test_正常系_domain_filteringセクションを読み込める(
        self, tmp_path: Path
    ) -> None:
        """load_configがdomain_filteringセクションを読み込めることを確認。"""
        from news.config.models import load_config

        # Arrange
        config_file = tmp_path / "config.yaml"
        config_file.write_text(
            """
version: "1.0"
status_mapping:
  tech: "ai"
github_status_ids:
  ai: "6fbb43d0"
rss:
  presets_file: "data/config/rss-presets.json"
summarization:
  prompt_template: "test"
github:
  project_number: 15
  project_id: "PVT_test"
  status_field_id: "PVTSSF_test"
  published_date_field_id: "PVTF_test"
  repository: "owner/repo"
output:
  result_dir: "data/exports"
domain_filtering:
  enabled: true
  log_blocked: false
  blocked_domains:
    - "seekingalpha.com"
    - "example.com"
"""
        )

        # Act
        config = load_config(config_file)

        # Assert
        assert config.domain_filtering.enabled is True
        assert config.domain_filtering.log_blocked is False
        assert config.domain_filtering.blocked_domains == [
            "seekingalpha.com",
            "example.com",
        ]

    def test_正常系_トップレベルblocked_domainsを変換できる(
        self, tmp_path: Path
    ) -> None:
        """load_configがトップレベルのblocked_domainsをdomain_filteringに変換することを確認。"""
        from news.config.models import load_config

        # Arrange: トップレベルに blocked_domains を配置
        config_file = tmp_path / "config.yaml"
        config_file.write_text(
            """
version: "1.0"
status_mapping:
  tech: "ai"
github_status_ids:
  ai: "6fbb43d0"
rss:
  presets_file: "data/config/rss-presets.json"
summarization:
  prompt_template: "test"
github:
  project_number: 15
  project_id: "PVT_test"
  status_field_id: "PVTSSF_test"
  published_date_field_id: "PVTF_test"
  repository: "owner/repo"
output:
  result_dir: "data/exports"
blocked_domains:
  - "seekingalpha.com"
  - "example.com"
"""
        )

        # Act
        config = load_config(config_file)

        # Assert
        assert config.domain_filtering.blocked_domains == [
            "seekingalpha.com",
            "example.com",
        ]
        assert config.domain_filtering.enabled is True  # デフォルト値

    def test_正常系_domain_filteringなしでデフォルト値が設定される(
        self, tmp_path: Path
    ) -> None:
        """load_configでdomain_filteringがない場合、デフォルト値が設定されることを確認。"""
        from news.config.models import load_config

        # Arrange
        config_file = tmp_path / "config.yaml"
        config_file.write_text(
            """
version: "1.0"
status_mapping:
  tech: "ai"
github_status_ids:
  ai: "6fbb43d0"
rss:
  presets_file: "data/config/rss-presets.json"
summarization:
  prompt_template: "test"
github:
  project_number: 15
  project_id: "PVT_test"
  status_field_id: "PVTSSF_test"
  published_date_field_id: "PVTF_test"
  repository: "owner/repo"
output:
  result_dir: "data/exports"
"""
        )

        # Act
        config = load_config(config_file)

        # Assert
        assert config.domain_filtering.enabled is True
        assert config.domain_filtering.log_blocked is True
        assert config.domain_filtering.blocked_domains == []


class TestUserAgentRotationConfig:
    """Test UserAgentRotationConfig Pydantic model."""

    def test_正常系_デフォルト値で作成できる(self) -> None:
        """UserAgentRotationConfigをデフォルト値で作成できることを確認。"""
        from news.config.models import UserAgentRotationConfig

        config = UserAgentRotationConfig()

        assert config.enabled is True
        assert config.user_agents == []

    def test_正常系_カスタム値で作成できる(self) -> None:
        """UserAgentRotationConfigをカスタム値で作成できることを確認。"""
        from news.config.models import UserAgentRotationConfig

        user_agents = [
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120.0.0.0",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) Safari/605.1.15",
        ]
        config = UserAgentRotationConfig(
            enabled=True,
            user_agents=user_agents,
        )

        assert config.enabled is True
        assert config.user_agents == user_agents

    def test_正常系_User_Agentがランダムに選択される(self) -> None:
        """User-Agentがランダムに選択されることを確認。"""
        from news.config.models import UserAgentRotationConfig

        config = UserAgentRotationConfig(
            user_agents=["UA1", "UA2", "UA3"],
        )

        # 100回試行して複数種類が選択されることを確認
        selections = {config.get_random_user_agent() for _ in range(100)}

        assert len(selections) >= 2  # 複数種類が選択される

    def test_正常系_無効時はNoneを返す(self) -> None:
        """enabled=Falseの時はNoneを返すことを確認。"""
        from news.config.models import UserAgentRotationConfig

        config = UserAgentRotationConfig(
            enabled=False,
            user_agents=["UA1", "UA2"],
        )

        assert config.get_random_user_agent() is None

    def test_正常系_空リストでNoneを返す(self) -> None:
        """user_agentsが空の時はNoneを返すことを確認。"""
        from news.config.models import UserAgentRotationConfig

        config = UserAgentRotationConfig(
            enabled=True,
            user_agents=[],
        )

        assert config.get_random_user_agent() is None

    def test_正常系_1つのUser_Agentで常に同じものを返す(self) -> None:
        """user_agentsが1つの場合、常にそれを返すことを確認。"""
        from news.config.models import UserAgentRotationConfig

        config = UserAgentRotationConfig(
            user_agents=["SingleUA"],
        )

        for _ in range(10):
            assert config.get_random_user_agent() == "SingleUA"


class TestExtractionConfigWithUserAgentRotation:
    """Test ExtractionConfig with user_agent_rotation field."""

    def test_正常系_user_agent_rotationがデフォルト値で作成される(self) -> None:
        """user_agent_rotationがデフォルト値で作成されることを確認。"""
        from news.config.models import ExtractionConfig, UserAgentRotationConfig

        config = ExtractionConfig()

        assert isinstance(config.user_agent_rotation, UserAgentRotationConfig)
        assert config.user_agent_rotation.enabled is True
        assert config.user_agent_rotation.user_agents == []

    def test_正常系_user_agent_rotationをカスタム値で作成できる(self) -> None:
        """user_agent_rotationをカスタム値で作成できることを確認。"""
        from news.config.models import ExtractionConfig, UserAgentRotationConfig

        ua_config = UserAgentRotationConfig(
            enabled=True,
            user_agents=["UA1", "UA2"],
        )
        config = ExtractionConfig(user_agent_rotation=ua_config)

        assert config.user_agent_rotation.enabled is True
        assert config.user_agent_rotation.user_agents == ["UA1", "UA2"]


class TestLoadConfigWithRssUserAgentRotation:
    """Test load_config function with rss.user_agent_rotation."""

    def test_正常系_rssのuser_agent_rotationセクションを読み込める(
        self, tmp_path: Path
    ) -> None:
        """load_configがrss.user_agent_rotationセクションを読み込めることを確認。"""
        from news.config.models import load_config

        # Arrange
        config_file = tmp_path / "config.yaml"
        config_file.write_text(
            """
version: "1.0"
status_mapping:
  tech: "ai"
github_status_ids:
  ai: "6fbb43d0"
rss:
  presets_file: "data/config/rss-presets.json"
  user_agent_rotation:
    enabled: true
    user_agents:
      - "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"
      - "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)"
summarization:
  prompt_template: "test"
github:
  project_number: 15
  project_id: "PVT_test"
  status_field_id: "PVTSSF_test"
  published_date_field_id: "PVTF_test"
  repository: "owner/repo"
output:
  result_dir: "data/exports"
"""
        )

        # Act
        config = load_config(config_file)

        # Assert
        assert config.rss.user_agent_rotation.enabled is True
        assert len(config.rss.user_agent_rotation.user_agents) == 2
        assert (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"
            in config.rss.user_agent_rotation.user_agents
        )

    def test_正常系_rssのuser_agent_rotationなしでデフォルト値が設定される(
        self, tmp_path: Path
    ) -> None:
        """load_configでrss.user_agent_rotationがない場合、デフォルト値が設定されることを確認。"""
        from news.config.models import load_config

        # Arrange
        config_file = tmp_path / "config.yaml"
        config_file.write_text(
            """
version: "1.0"
status_mapping:
  tech: "ai"
github_status_ids:
  ai: "6fbb43d0"
rss:
  presets_file: "data/config/rss-presets.json"
summarization:
  prompt_template: "test"
github:
  project_number: 15
  project_id: "PVT_test"
  status_field_id: "PVTSSF_test"
  published_date_field_id: "PVTF_test"
  repository: "owner/repo"
output:
  result_dir: "data/exports"
"""
        )

        # Act
        config = load_config(config_file)

        # Assert
        assert config.rss.user_agent_rotation.enabled is True
        assert config.rss.user_agent_rotation.user_agents == []


class TestLoadConfigWithUserAgentRotation:
    """Test load_config function with user_agent_rotation."""

    def test_正常系_user_agent_rotationセクションを読み込める(
        self, tmp_path: Path
    ) -> None:
        """load_configがuser_agent_rotationセクションを読み込めることを確認。"""
        from news.config.models import load_config

        # Arrange
        config_file = tmp_path / "config.yaml"
        config_file.write_text(
            """
version: "1.0"
status_mapping:
  tech: "ai"
github_status_ids:
  ai: "6fbb43d0"
rss:
  presets_file: "data/config/rss-presets.json"
extraction:
  user_agent_rotation:
    enabled: true
    user_agents:
      - "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"
      - "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)"
summarization:
  prompt_template: "test"
github:
  project_number: 15
  project_id: "PVT_test"
  status_field_id: "PVTSSF_test"
  published_date_field_id: "PVTF_test"
  repository: "owner/repo"
output:
  result_dir: "data/exports"
"""
        )

        # Act
        config = load_config(config_file)

        # Assert
        assert config.extraction.user_agent_rotation.enabled is True
        assert len(config.extraction.user_agent_rotation.user_agents) == 2
        assert (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"
            in config.extraction.user_agent_rotation.user_agents
        )

    def test_正常系_user_agent_rotationなしでデフォルト値が設定される(
        self, tmp_path: Path
    ) -> None:
        """load_configでuser_agent_rotationがない場合、デフォルト値が設定されることを確認。"""
        from news.config.models import load_config

        # Arrange
        config_file = tmp_path / "config.yaml"
        config_file.write_text(
            """
version: "1.0"
status_mapping:
  tech: "ai"
github_status_ids:
  ai: "6fbb43d0"
rss:
  presets_file: "data/config/rss-presets.json"
summarization:
  prompt_template: "test"
github:
  project_number: 15
  project_id: "PVT_test"
  status_field_id: "PVTSSF_test"
  published_date_field_id: "PVTF_test"
  repository: "owner/repo"
output:
  result_dir: "data/exports"
"""
        )

        # Act
        config = load_config(config_file)

        # Assert
        assert config.extraction.user_agent_rotation.enabled is True
        assert config.extraction.user_agent_rotation.user_agents == []
