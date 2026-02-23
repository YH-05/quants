"""Unit tests for utils_core.config module."""

from __future__ import annotations

import dataclasses
from typing import TYPE_CHECKING

import pytest

if TYPE_CHECKING:
    from pathlib import Path

from utils_core.config import ProjectConfig


class TestProjectConfigFromDefaults:
    """ProjectConfig.from_defaults() のテスト."""

    def test_正常系_デフォルト値でインスタンスが生成される(self) -> None:
        """from_defaults() がデフォルト値でインスタンスを生成できること."""
        config = ProjectConfig.from_defaults()

        assert config.fred_api_key == ""
        assert config.log_level == "INFO"
        assert config.log_format == "console"
        assert config.log_dir == "logs/"
        assert config.project_env == "development"

    def test_正常系_ProjectConfigのインスタンスである(self) -> None:
        """from_defaults() が ProjectConfig インスタンスを返すこと."""
        config = ProjectConfig.from_defaults()

        assert isinstance(config, ProjectConfig)

    def test_正常系_frozenによりフィールドが変更不可(self) -> None:
        """frozen=True により、フィールドへの代入が FrozenInstanceError を発生させること."""
        config = ProjectConfig.from_defaults()

        with pytest.raises((dataclasses.FrozenInstanceError, AttributeError)):
            config.fred_api_key = "new_key"  # type: ignore[misc]

    def test_正常系_同じデフォルト値なら等しい(self) -> None:
        """同じデフォルト値のインスタンスは等しいこと."""
        config1 = ProjectConfig.from_defaults()
        config2 = ProjectConfig.from_defaults()

        assert config1 == config2


class TestProjectConfigFromEnv:
    """ProjectConfig.from_env() のテスト."""

    def test_正常系_環境変数から全フィールドを取得できる(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """.env から全フィールドを正しく取得できること."""
        env_file = tmp_path / ".env"
        env_file.write_text(
            "FRED_API_KEY=test_key_12345\n"
            "LOG_LEVEL=DEBUG\n"
            "LOG_FORMAT=json\n"
            "LOG_DIR=/var/log/finance/\n"
            "PROJECT_ENV=production\n"
        )

        config = ProjectConfig.from_env(env_file)

        assert config.fred_api_key == "test_key_12345"
        assert config.log_level == "DEBUG"
        assert config.log_format == "json"
        assert config.log_dir == "/var/log/finance/"
        assert config.project_env == "production"

    def test_正常系_env_pathがNoneの場合は自動探索を使用(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """env_path が None のとき、load_project_env() 経由で自動探索すること."""
        env_file = tmp_path / ".env"
        env_file.write_text("FRED_API_KEY=auto_found_key\nLOG_LEVEL=WARNING\n")
        monkeypatch.delenv("DOTENV_PATH", raising=False)
        monkeypatch.chdir(tmp_path)
        # 環境変数をクリア
        monkeypatch.delenv("FRED_API_KEY", raising=False)
        monkeypatch.delenv("LOG_LEVEL", raising=False)
        monkeypatch.delenv("LOG_FORMAT", raising=False)
        monkeypatch.delenv("LOG_DIR", raising=False)
        monkeypatch.delenv("PROJECT_ENV", raising=False)

        config = ProjectConfig.from_env()

        assert config.fred_api_key == "auto_found_key"
        assert config.log_level == "WARNING"

    def test_正常系_未設定フィールドはデフォルト値が使われる(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """一部の環境変数が未設定の場合、デフォルト値が使われること."""
        env_file = tmp_path / ".env"
        env_file.write_text("FRED_API_KEY=partial_key\n")
        # 他の環境変数をクリア
        monkeypatch.delenv("LOG_LEVEL", raising=False)
        monkeypatch.delenv("LOG_FORMAT", raising=False)
        monkeypatch.delenv("LOG_DIR", raising=False)
        monkeypatch.delenv("PROJECT_ENV", raising=False)

        config = ProjectConfig.from_env(env_file)

        assert config.fred_api_key == "partial_key"
        assert config.log_level == "INFO"
        assert config.log_format == "console"
        assert config.log_dir == "logs/"
        assert config.project_env == "development"

    def test_正常系_FRED_API_KEYが未設定の場合は空文字(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """FRED_API_KEY が未設定の場合、空文字になること."""
        env_file = tmp_path / ".env"
        env_file.write_text("")
        monkeypatch.delenv("FRED_API_KEY", raising=False)
        monkeypatch.delenv("LOG_LEVEL", raising=False)
        monkeypatch.delenv("LOG_FORMAT", raising=False)
        monkeypatch.delenv("LOG_DIR", raising=False)
        monkeypatch.delenv("PROJECT_ENV", raising=False)

        config = ProjectConfig.from_env(env_file)

        assert config.fred_api_key == ""

    def test_正常系_from_envはProjectConfigインスタンスを返す(
        self, tmp_path: Path
    ) -> None:
        """from_env() が ProjectConfig インスタンスを返すこと."""
        env_file = tmp_path / ".env"
        env_file.write_text("FRED_API_KEY=test_key\n")

        config = ProjectConfig.from_env(env_file)

        assert isinstance(config, ProjectConfig)


class TestProjectConfigFrozen:
    """ProjectConfig の frozen 属性のテスト."""

    def test_正常系_frozenデータクラスである(self) -> None:
        """ProjectConfig が frozen=True のデータクラスであること."""
        assert dataclasses.is_dataclass(ProjectConfig)
        # frozen であることを確認（FrozenInstanceError が発生すること）
        config = ProjectConfig.from_defaults()
        with pytest.raises((dataclasses.FrozenInstanceError, AttributeError)):
            config.log_level = "DEBUG"  # type: ignore[misc]

    def test_正常系_フィールドへの直接代入が不可(self) -> None:
        """直接代入が FrozenInstanceError を発生させること."""
        config = ProjectConfig.from_defaults()

        with pytest.raises((dataclasses.FrozenInstanceError, AttributeError)):
            config.log_format = "json"  # type: ignore[misc]

    def test_正常系_log_levelフィールドへの代入が不可(self) -> None:
        """log_level フィールドへの代入が不可であること."""
        config = ProjectConfig.from_defaults()

        with pytest.raises((dataclasses.FrozenInstanceError, AttributeError)):
            config.log_level = "ERROR"  # type: ignore[misc]


class TestProjectConfigValidate:
    """ProjectConfig._validate() バリデーションのテスト."""

    @pytest.mark.parametrize(
        "log_level",
        ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"],
    )
    def test_正常系_有効なlog_levelで作成できる(self, log_level: str) -> None:
        """有効な log_level でインスタンスが作成できること."""
        config = ProjectConfig(
            fred_api_key="key",
            log_level=log_level,
            log_format="console",
            log_dir="logs/",
            project_env="development",
        )

        assert config.log_level == log_level

    @pytest.mark.parametrize(
        "log_format",
        ["json", "console"],
    )
    def test_正常系_有効なlog_formatで作成できる(self, log_format: str) -> None:
        """有効な log_format でインスタンスが作成できること."""
        config = ProjectConfig(
            fred_api_key="key",
            log_level="INFO",
            log_format=log_format,
            log_dir="logs/",
            project_env="development",
        )

        assert config.log_format == log_format

    @pytest.mark.parametrize(
        "invalid_log_level",
        ["TRACE", "FATAL", "verbose", "invalid", ""],
    )
    def test_異常系_不正なlog_levelでValueErrorが発生(
        self, invalid_log_level: str
    ) -> None:
        """不正な log_level で ValueError が発生すること."""
        with pytest.raises(ValueError, match="Invalid log_level"):
            ProjectConfig(
                fred_api_key="key",
                log_level=invalid_log_level,
                log_format="console",
                log_dir="logs/",
                project_env="development",
            )

    @pytest.mark.parametrize(
        "invalid_log_format",
        ["xml", "yaml", "text", "invalid", ""],
    )
    def test_異常系_不正なlog_formatでValueErrorが発生(
        self, invalid_log_format: str
    ) -> None:
        """不正な log_format で ValueError が発生すること."""
        with pytest.raises(ValueError, match="Invalid log_format"):
            ProjectConfig(
                fred_api_key="key",
                log_level="INFO",
                log_format=invalid_log_format,
                log_dir="logs/",
                project_env="development",
            )

    def test_正常系_デフォルト値のみで直接インスタンス化できる(self) -> None:
        """デフォルト値を指定してインスタンスが作成できること."""
        config = ProjectConfig(
            fred_api_key="",
            log_level="INFO",
            log_format="console",
            log_dir="logs/",
            project_env="development",
        )

        assert config.fred_api_key == ""
        assert config.log_level == "INFO"
        assert config.log_format == "console"
        assert config.log_dir == "logs/"
        assert config.project_env == "development"


class TestProjectConfigFields:
    """ProjectConfig のフィールド定義のテスト."""

    def test_正常系_fred_api_keyフィールドが存在する(self) -> None:
        """fred_api_key フィールドが存在すること."""
        config = ProjectConfig.from_defaults()

        assert hasattr(config, "fred_api_key")
        assert isinstance(config.fred_api_key, str)

    def test_正常系_log_levelフィールドが存在する(self) -> None:
        """log_level フィールドが存在すること."""
        config = ProjectConfig.from_defaults()

        assert hasattr(config, "log_level")
        assert isinstance(config.log_level, str)

    def test_正常系_log_formatフィールドが存在する(self) -> None:
        """log_format フィールドが存在すること."""
        config = ProjectConfig.from_defaults()

        assert hasattr(config, "log_format")
        assert isinstance(config.log_format, str)

    def test_正常系_log_dirフィールドが存在する(self) -> None:
        """log_dir フィールドが存在すること."""
        config = ProjectConfig.from_defaults()

        assert hasattr(config, "log_dir")
        assert isinstance(config.log_dir, str)

    def test_正常系_project_envフィールドが存在する(self) -> None:
        """project_env フィールドが存在すること."""
        config = ProjectConfig.from_defaults()

        assert hasattr(config, "project_env")
        assert isinstance(config.project_env, str)
