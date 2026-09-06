"""Unit tests for utils_core.settings module."""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path
from typing import TYPE_CHECKING

import pytest

from utils_core.settings import (
    _find_env_file,
    get_fred_api_key,
    get_log_dir,
    get_log_format,
    get_log_level,
    get_project_env,
    load_project_env,
)

if TYPE_CHECKING:
    from utils_core.types import LogFormat, LogLevel


class TestGetFredApiKey:
    """get_fred_api_key() のテスト."""

    def test_正常系_環境変数が設定されている場合にAPIキーを返す(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """環境変数が設定されている場合、APIキーを返す."""
        monkeypatch.setenv("FRED_API_KEY", "test_api_key_12345")
        get_fred_api_key.cache_clear()

        result = get_fred_api_key()

        assert result == "test_api_key_12345"

    def test_異常系_環境変数が未設定の場合にValueErrorを発生(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """環境変数が未設定の場合、ValueErrorを発生させる."""
        monkeypatch.delenv("FRED_API_KEY", raising=False)
        get_fred_api_key.cache_clear()

        with pytest.raises(ValueError, match="FRED_API_KEY is required"):
            get_fred_api_key()

    def test_遅延読み込み_キャッシュが機能する(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """遅延読み込みとキャッシュが機能することを確認."""
        monkeypatch.setenv("FRED_API_KEY", "cached_key")
        get_fred_api_key.cache_clear()

        # 1回目の呼び出し
        result1 = get_fred_api_key()

        # 環境変数を変更
        monkeypatch.setenv("FRED_API_KEY", "new_key")

        # 2回目の呼び出し（キャッシュされた値が返る）
        result2 = get_fred_api_key()

        assert result1 == result2 == "cached_key"


class TestGetLogLevel:
    """get_log_level() のテスト."""

    @pytest.mark.parametrize(
        ("env_value", "expected"),
        [
            ("DEBUG", "DEBUG"),
            ("INFO", "INFO"),
            ("WARNING", "WARNING"),
            ("ERROR", "ERROR"),
            ("CRITICAL", "CRITICAL"),
            ("debug", "DEBUG"),  # 小文字も受け入れ
            ("info", "INFO"),
        ],
    )
    def test_正常系_有効なログレベルを返す(
        self,
        env_value: str,
        expected: LogLevel,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """有効なログレベルの場合、正しく変換して返す."""
        monkeypatch.setenv("LOG_LEVEL", env_value)
        get_log_level.cache_clear()

        result = get_log_level()

        assert result == expected

    def test_正常系_未設定の場合にINFOを返す(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """環境変数が未設定の場合、デフォルト値 INFO を返す."""
        monkeypatch.delenv("LOG_LEVEL", raising=False)
        get_log_level.cache_clear()

        result = get_log_level()

        assert result == "INFO"

    @pytest.mark.parametrize("invalid_value", ["TRACE", "FATAL", "invalid"])
    def test_異常系_不正なログレベルでValueErrorを発生(
        self, invalid_value: str, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """不正なログレベルの場合、ValueErrorを発生させる."""
        monkeypatch.setenv("LOG_LEVEL", invalid_value)
        get_log_level.cache_clear()

        with pytest.raises(ValueError, match="Invalid LOG_LEVEL"):
            get_log_level()


class TestGetLogFormat:
    """get_log_format() のテスト."""

    @pytest.mark.parametrize(
        ("env_value", "expected"),
        [
            ("json", "json"),
            ("console", "console"),
            ("JSON", "json"),  # 大文字も受け入れ
            ("CONSOLE", "console"),
        ],
    )
    def test_正常系_有効なログフォーマットを返す(
        self,
        env_value: str,
        expected: LogFormat,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """有効なログフォーマットの場合、正しく変換して返す."""
        monkeypatch.setenv("LOG_FORMAT", env_value)
        get_log_format.cache_clear()

        result = get_log_format()

        assert result == expected

    def test_正常系_未設定の場合にconsoleを返す(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """環境変数が未設定の場合、デフォルト値 console を返す."""
        monkeypatch.delenv("LOG_FORMAT", raising=False)
        get_log_format.cache_clear()

        result = get_log_format()

        assert result == "console"

    @pytest.mark.parametrize("invalid_value", ["xml", "yaml", "invalid"])
    def test_異常系_不正なログフォーマットでValueErrorを発生(
        self, invalid_value: str, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """不正なログフォーマットの場合、ValueErrorを発生させる."""
        monkeypatch.setenv("LOG_FORMAT", invalid_value)
        get_log_format.cache_clear()

        with pytest.raises(ValueError, match="Invalid LOG_FORMAT"):
            get_log_format()


class TestGetLogDir:
    """get_log_dir() のテスト."""

    def test_正常系_環境変数が設定されている場合にディレクトリパスを返す(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """環境変数が設定されている場合、ディレクトリパスを返す."""
        monkeypatch.setenv("LOG_DIR", "/var/log/finance/")
        get_log_dir.cache_clear()

        result = get_log_dir()

        assert result == "/var/log/finance/"

    def test_正常系_未設定の場合にデフォルト値を返す(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """環境変数が未設定の場合、デフォルト値 logs/ を返す."""
        monkeypatch.delenv("LOG_DIR", raising=False)
        get_log_dir.cache_clear()

        result = get_log_dir()

        assert result == "logs/"


class TestGetProjectEnv:
    """get_project_env() のテスト."""

    @pytest.mark.parametrize(
        "env_value",
        ["development", "production", "staging", "test"],
    )
    def test_正常系_環境変数が設定されている場合に環境名を返す(
        self, env_value: str, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """環境変数が設定されている場合、環境名を返す."""
        monkeypatch.setenv("PROJECT_ENV", env_value)
        get_project_env.cache_clear()

        result = get_project_env()

        assert result == env_value

    def test_正常系_未設定の場合にデフォルト値を返す(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """環境変数が未設定の場合、デフォルト値 development を返す."""
        monkeypatch.delenv("PROJECT_ENV", raising=False)
        get_project_env.cache_clear()

        result = get_project_env()

        assert result == "development"


class TestFindEnvFile:
    """_find_env_file() のテスト."""

    def test_正常系_DOTENV_PATH環境変数で指定されたパスを返す(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """DOTENV_PATH 環境変数が設定されている場合、そのパスを返す."""
        env_file = tmp_path / ".env"
        env_file.write_text("TEST=value")
        monkeypatch.setenv("DOTENV_PATH", str(env_file))

        result = _find_env_file()

        assert result == env_file

    def test_正常系_DOTENV_PATH環境変数のファイルが存在しない場合はNone(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """DOTENV_PATH で指定されたファイルが存在しない場合、None を返す."""
        non_existent = tmp_path / "non_existent" / ".env"
        monkeypatch.setenv("DOTENV_PATH", str(non_existent))

        result = _find_env_file()

        assert result is None

    def test_正常系_カレントディレクトリのenvファイルを検出(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """カレントディレクトリに .env がある場合、そのパスを返す."""
        monkeypatch.delenv("DOTENV_PATH", raising=False)
        env_file = tmp_path / ".env"
        env_file.write_text("TEST=value")
        monkeypatch.chdir(tmp_path)

        result = _find_env_file()

        assert result == env_file

    def test_正常系_親ディレクトリのenvファイルを検出(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """親ディレクトリに .env がある場合、そのパスを返す."""
        monkeypatch.delenv("DOTENV_PATH", raising=False)
        env_file = tmp_path / ".env"
        env_file.write_text("TEST=value")
        child_dir = tmp_path / "child"
        child_dir.mkdir()
        monkeypatch.chdir(child_dir)

        result = _find_env_file()

        assert result == env_file

    def test_正常系_5レベル上の親ディレクトリのenvファイルを検出(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """5レベル上の親ディレクトリに .env がある場合、そのパスを返す."""
        monkeypatch.delenv("DOTENV_PATH", raising=False)
        env_file = tmp_path / ".env"
        env_file.write_text("TEST=value")
        # 5レベル深いディレクトリを作成
        deep_dir = tmp_path / "l1" / "l2" / "l3" / "l4" / "l5"
        deep_dir.mkdir(parents=True)
        monkeypatch.chdir(deep_dir)

        result = _find_env_file()

        assert result == env_file

    def test_正常系_6レベル以上上のenvファイルは検出しない(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """6レベル以上上の親ディレクトリの .env は検出しない（最大5レベル）."""
        monkeypatch.delenv("DOTENV_PATH", raising=False)
        env_file = tmp_path / ".env"
        env_file.write_text("TEST=value")
        # 6レベル深いディレクトリを作成
        deep_dir = tmp_path / "l1" / "l2" / "l3" / "l4" / "l5" / "l6"
        deep_dir.mkdir(parents=True)
        monkeypatch.chdir(deep_dir)

        result = _find_env_file()

        assert result is None

    def test_エッジケース_envファイルが見つからない場合はNone(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """.env ファイルが見つからない場合、None を返す."""
        monkeypatch.delenv("DOTENV_PATH", raising=False)
        empty_dir = tmp_path / "empty"
        empty_dir.mkdir()
        monkeypatch.chdir(empty_dir)

        result = _find_env_file()

        assert result is None

    def test_正常系_近いディレクトリのenvファイルを優先(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """複数の .env がある場合、カレントディレクトリに近い方を返す."""
        monkeypatch.delenv("DOTENV_PATH", raising=False)
        # 親ディレクトリに .env を作成
        parent_env = tmp_path / ".env"
        parent_env.write_text("PARENT=value")
        # 子ディレクトリに .env を作成
        child_dir = tmp_path / "child"
        child_dir.mkdir()
        child_env = child_dir / ".env"
        child_env.write_text("CHILD=value")
        monkeypatch.chdir(child_dir)

        result = _find_env_file()

        assert result == child_env


class TestLoadProjectEnv:
    """load_project_env() のテスト."""

    def test_正常系_envファイルが見つかった場合にTrueを返す(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """.env ファイルが見つかった場合、True を返す."""
        env_file = tmp_path / ".env"
        env_file.write_text("TEST_VAR=test_value")
        monkeypatch.delenv("DOTENV_PATH", raising=False)
        monkeypatch.chdir(tmp_path)

        result = load_project_env()

        assert result is True

    def test_正常系_envファイルが見つからない場合にFalseを返す(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """.env ファイルが見つからない場合、False を返す."""
        empty_dir = tmp_path / "empty"
        empty_dir.mkdir()
        monkeypatch.delenv("DOTENV_PATH", raising=False)
        monkeypatch.chdir(empty_dir)

        result = load_project_env()

        assert result is False

    def test_正常系_DOTENV_PATHで指定されたファイルを読み込む(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """DOTENV_PATH で指定された .env ファイルを読み込む."""
        env_file = tmp_path / "custom.env"
        env_file.write_text("CUSTOM_VAR=custom_value")
        monkeypatch.setenv("DOTENV_PATH", str(env_file))
        # テスト前に変数をクリア
        monkeypatch.delenv("CUSTOM_VAR", raising=False)

        result = load_project_env()

        assert result is True
        import os

        assert os.environ.get("CUSTOM_VAR") == "custom_value"

    def test_正常系_親ディレクトリのenvファイルを読み込む(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """親ディレクトリの .env ファイルを読み込む."""
        env_file = tmp_path / ".env"
        env_file.write_text("PARENT_VAR=parent_value")
        child_dir = tmp_path / "child"
        child_dir.mkdir()
        monkeypatch.delenv("DOTENV_PATH", raising=False)
        monkeypatch.delenv("PARENT_VAR", raising=False)
        monkeypatch.chdir(child_dir)

        result = load_project_env()

        assert result is True
        import os

        assert os.environ.get("PARENT_VAR") == "parent_value"

    def test_正常系_overrideがTrueの場合に既存の環境変数を上書き(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """override=True の場合、既存の環境変数を上書きする."""
        env_file = tmp_path / ".env"
        env_file.write_text("OVERRIDE_VAR=new_value")
        monkeypatch.delenv("DOTENV_PATH", raising=False)
        monkeypatch.setenv("OVERRIDE_VAR", "old_value")
        monkeypatch.chdir(tmp_path)

        result = load_project_env(override=True)

        assert result is True
        import os

        assert os.environ.get("OVERRIDE_VAR") == "new_value"

    def test_正常系_overrideがFalseの場合に既存の環境変数を保持(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """override=False の場合、既存の環境変数を保持する."""
        env_file = tmp_path / ".env"
        env_file.write_text("PRESERVE_VAR=new_value")
        monkeypatch.delenv("DOTENV_PATH", raising=False)
        monkeypatch.setenv("PRESERVE_VAR", "old_value")
        monkeypatch.chdir(tmp_path)

        result = load_project_env(override=False)

        assert result is True
        import os

        assert os.environ.get("PRESERVE_VAR") == "old_value"


# 実在の設定キーと衝突しないテスト専用の変数名
_PROBE_VAR = "QUANTS_TEST_ENV_OVERRIDE_PROBE"

# サブプロセスで trigger を実行し、その後の環境変数値を JSON で出力するスクリプト
_PROBE_SCRIPT_TEMPLATE = """
import json
import os

{trigger}

print(json.dumps({{"value": os.environ.get({var!r})}}))
"""


def _run_env_probe(
    *,
    tmp_path: Path,
    trigger: str,
    dotenv_value: str,
    preset_value: str | None,
) -> str | None:
    """サブプロセスで trigger を実行し、環境変数の最終値を取得する.

    .env の読み込みは import 時・ロガー初期化時などプロセス全体に副作用を及ぼす。
    pytest プロセスの環境を汚さずに検証するため、専用のサブプロセスを起動し、
    その中で trigger を実行した後の環境変数を観測する。

    Parameters
    ----------
    tmp_path : Path
        .env ファイルを作成する一時ディレクトリ。
    trigger : str
        サブプロセス内で実行する Python コード片（import やロガー初期化）。
    dotenv_value : str
        .env に書き込む値。
    preset_value : str | None
        trigger 実行前に環境変数へ設定しておく値。None の場合は未設定にする。

    Returns
    -------
    str | None
        trigger 実行後にサブプロセス内で観測された環境変数の値。
    """
    env_file = tmp_path / ".env"
    env_file.write_text(f"{_PROBE_VAR}={dotenv_value}\n", encoding="utf-8")

    src_path = Path(__file__).parents[3] / "src"

    env = os.environ.copy()
    # .env の探索結果を固定し、リポジトリの実 .env に依存させない
    env["DOTENV_PATH"] = str(env_file)
    env["PYTHONPATH"] = os.pathsep.join(
        [str(src_path), env.get("PYTHONPATH", "")]
    ).rstrip(os.pathsep)
    # setup_logging 等がリポジトリの logs/ に書き込まないよう隔離する
    env["LOG_DIR"] = str(tmp_path / "logs")

    if preset_value is None:
        env.pop(_PROBE_VAR, None)
    else:
        env[_PROBE_VAR] = preset_value

    script = _PROBE_SCRIPT_TEMPLATE.format(trigger=trigger, var=_PROBE_VAR)
    result = subprocess.run(
        [sys.executable, "-c", script],
        capture_output=True,
        text=True,
        env=env,
        cwd=tmp_path,
        check=False,
    )

    assert result.returncode == 0, (
        f"サブプロセスが失敗しました (returncode={result.returncode})\n"
        f"stdout: {result.stdout}\nstderr: {result.stderr}"
    )

    payload: dict[str, str | None] = json.loads(result.stdout.strip())
    return payload["value"]


class TestEnvOverridePrecedence:
    """.env より明示設定された環境変数が優先されることのテスト.

    ``load_project_env(override=True)`` を使うと、コンテナランタイム・
    ``uv run --env-file``・CI・シェルが明示的に設定した環境変数が .env の値で
    上書きされる。リポジトリごと ``/app`` にマウントされる Docker 構成では
    ホスト用パスが注入されて壊れるため、以下の全経路で ``override=False``
    でなければならない。

    - ``import utils_core.settings``（モジュール末尾の呼び出し）
    - ``get_logger()``（初回呼び出しで ``_ensure_basic_config()`` が発火）
    - ``setup_logging()``
    - ``ProjectConfig.from_env()``（env_path 未指定の分岐）
    """

    _TRIGGER_IMPORT = "import utils_core.settings  # noqa: F401"
    _TRIGGER_GET_LOGGER = (
        "from utils_core.logging import get_logger\n\nget_logger('probe')"
    )
    _TRIGGER_SETUP_LOGGING = (
        "from utils_core.logging import setup_logging\n\nsetup_logging()"
    )
    _TRIGGER_FROM_ENV = (
        "from utils_core.config import ProjectConfig\n\nProjectConfig.from_env()"
    )

    def test_正常系_設定済みの環境変数はimport時にenvで上書きされない(
        self, tmp_path: Path
    ) -> None:
        """import utils_core.settings が明示設定された環境変数を保持すること."""
        result = _run_env_probe(
            tmp_path=tmp_path,
            trigger=self._TRIGGER_IMPORT,
            dotenv_value="from_dotenv",
            preset_value="from_container_runtime",
        )

        assert result == "from_container_runtime"

    def test_正常系_設定済みの環境変数はget_logger経由でenvで上書きされない(
        self, tmp_path: Path
    ) -> None:
        """get_logger() が明示設定された環境変数を保持すること（リグレッション）.

        get_logger() の初回呼び出しは _ensure_basic_config() を発火させる。
        全エントリポイントがロガーを生成するため、ここが最も影響範囲が広い。
        """
        result = _run_env_probe(
            tmp_path=tmp_path,
            trigger=self._TRIGGER_GET_LOGGER,
            dotenv_value="from_dotenv",
            preset_value="from_container_runtime",
        )

        assert result == "from_container_runtime"

    def test_正常系_設定済みの環境変数はsetup_logging経由でenvで上書きされない(
        self, tmp_path: Path
    ) -> None:
        """setup_logging() が明示設定された環境変数を保持すること."""
        result = _run_env_probe(
            tmp_path=tmp_path,
            trigger=self._TRIGGER_SETUP_LOGGING,
            dotenv_value="from_dotenv",
            preset_value="from_container_runtime",
        )

        assert result == "from_container_runtime"

    def test_正常系_設定済みの環境変数はProjectConfig生成でenvで上書きされない(
        self, tmp_path: Path
    ) -> None:
        """ProjectConfig.from_env() が明示設定された環境変数を保持すること."""
        result = _run_env_probe(
            tmp_path=tmp_path,
            trigger=self._TRIGGER_FROM_ENV,
            dotenv_value="from_dotenv",
            preset_value="from_container_runtime",
        )

        assert result == "from_container_runtime"

    def test_正常系_未設定の環境変数はimport時にenvから読み込まれる(
        self, tmp_path: Path
    ) -> None:
        """環境変数が未設定の場合は import 時に .env の値が読み込まれること."""
        result = _run_env_probe(
            tmp_path=tmp_path,
            trigger=self._TRIGGER_IMPORT,
            dotenv_value="from_dotenv",
            preset_value=None,
        )

        assert result == "from_dotenv"

    def test_正常系_未設定の環境変数はget_logger経由でenvから読み込まれる(
        self, tmp_path: Path
    ) -> None:
        """環境変数が未設定の場合は get_logger() 経由で .env の値が読み込まれること."""
        result = _run_env_probe(
            tmp_path=tmp_path,
            trigger=self._TRIGGER_GET_LOGGER,
            dotenv_value="from_dotenv",
            preset_value=None,
        )

        assert result == "from_dotenv"
