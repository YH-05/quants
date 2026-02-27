"""Project configuration module.

frozen dataclass による一括環境変数バリデーション機能を提供する。
既存の settings.py の load_project_env() を再利用し、
Finance 固有フィールドを一元管理する。

Environment Variables
---------------------
FRED_API_KEY : str, optional
    FRED API Key (default: empty string)
LOG_LEVEL : str, optional
    Log level (default: INFO)
LOG_FORMAT : str, optional
    Log format (default: console)
LOG_DIR : str, optional
    Log directory (default: logs/)
PROJECT_ENV : str, optional
    Project environment (default: development)
DATA_DIR : str, optional
    Data root directory (default: data/)
RESEARCH_DIR : str, optional
    Research workspace directory (default: research/)
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import ClassVar

from .settings import load_project_env

# AIDEV-NOTE: frozen dataclass を使用することで、設定の不変性を保証する。
# インスタンス生成後はフィールドへの代入が FrozenInstanceError を引き起こす。

_VALID_LOG_LEVELS: tuple[str, ...] = ("DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL")
_VALID_LOG_FORMATS: tuple[str, ...] = ("json", "console")


def _find_project_root() -> Path:
    """pyproject.toml を目印にプロジェクトルートを検索する.

    Returns
    -------
    Path
        プロジェクトルートの絶対パス。

    Raises
    ------
    FileNotFoundError
        pyproject.toml が見つからない場合。
    """
    current = Path(__file__).resolve().parent
    for parent in [current, *current.parents]:
        if (parent / "pyproject.toml").exists():
            return parent
    msg = "Project root not found (pyproject.toml not found in parent directories)"
    raise FileNotFoundError(msg)


@dataclass(frozen=True)
class ProjectConfig:
    """Finance プロジェクトの設定を一括管理する frozen dataclass.

    環境変数から全フィールドを一括読み込み・バリデーションする。
    frozen=True により、インスタンス生成後の変更は不可。

    Parameters
    ----------
    fred_api_key : str
        FRED API Key。未設定の場合は空文字。
    log_level : str
        ログレベル。デフォルトは 'INFO'。
        有効値: DEBUG, INFO, WARNING, ERROR, CRITICAL
    log_format : str
        ログフォーマット。デフォルトは 'console'。
        有効値: json, console
    log_dir : str
        ログディレクトリのパス。デフォルトは 'logs/'。
    project_env : str
        プロジェクト環境。デフォルトは 'development'。
    data_dir : str
        データルートディレクトリ。デフォルトは 'data/'。
    research_dir : str
        リサーチワークスペースディレクトリ。デフォルトは 'research/'。

    Examples
    --------
    >>> # デフォルト値でインスタンス生成
    >>> config = ProjectConfig.from_defaults()
    >>> config.log_level
    'INFO'

    >>> # 環境変数から生成
    >>> config = ProjectConfig.from_env()
    >>> config.fred_api_key
    'your_api_key'

    >>> # frozen により変更不可
    >>> config.log_level = 'DEBUG'  # doctest: +IGNORE_EXCEPTION_DETAIL
    Traceback (most recent call last):
        ...
    dataclasses.FrozenInstanceError: cannot assign to field 'log_level'

    >>> # notebook など任意の CWD から絶対パスを取得
    >>> config = ProjectConfig.from_defaults()
    >>> config.data_path.is_absolute()
    True
    """

    # AIDEV-NOTE: ClassVar はデータクラスのフィールドとして扱われない。
    # バリデーション定数をクラス変数として保持する。
    _VALID_LOG_LEVELS: ClassVar[tuple[str, ...]] = _VALID_LOG_LEVELS
    _VALID_LOG_FORMATS: ClassVar[tuple[str, ...]] = _VALID_LOG_FORMATS

    fred_api_key: str
    log_level: str = "INFO"
    log_format: str = "console"
    log_dir: str = "logs/"
    project_env: str = "development"
    data_dir: str = "data/"
    research_dir: str = "research/"

    def __post_init__(self) -> None:
        """フィールドのバリデーションを実行する.

        Raises
        ------
        ValueError
            log_level または log_format が不正な値の場合。
        """
        self._validate()

    def _validate(self) -> None:
        """log_level と log_format のバリデーションを実行する.

        Raises
        ------
        ValueError
            log_level が不正な値の場合。
        ValueError
            log_format が不正な値の場合。
        """
        if self.log_level not in _VALID_LOG_LEVELS:
            msg = (
                f"Invalid log_level: {self.log_level!r}. "
                f"Valid values: {', '.join(_VALID_LOG_LEVELS)}"
            )
            raise ValueError(msg)

        if self.log_format not in _VALID_LOG_FORMATS:
            msg = (
                f"Invalid log_format: {self.log_format!r}. "
                f"Valid values: {', '.join(_VALID_LOG_FORMATS)}"
            )
            raise ValueError(msg)

    def _resolve_dir(self, dir_str: str) -> Path:
        """ディレクトリパスを絶対パスに解決する.

        絶対パスはそのまま返し、相対パスはプロジェクトルート起点で解決する。
        notebook など CWD がプロジェクトルート以外の場合でも正しく動作する。

        Parameters
        ----------
        dir_str : str
            解決対象のディレクトリパス文字列。

        Returns
        -------
        Path
            絶対パスに解決された Path オブジェクト。
        """
        p = Path(dir_str)
        if p.is_absolute():
            return p
        return _find_project_root() / p

    def get_path(self, env_var: str, default: str = "") -> Path:
        """任意の環境変数からパスを取得し、絶対パスに解決する.

        config.py を書き換えずに .env へ環境変数を追加するだけで
        新しいフォルダパスを利用できる汎用アクセサ。

        Parameters
        ----------
        env_var : str
            環境変数名（例: "ARTICLES_DIR"）。
        default : str
            環境変数が未設定の場合のデフォルト値。空文字の場合は ValueError を送出する。

        Returns
        -------
        Path
            絶対パスに解決された Path オブジェクト。

        Raises
        ------
        ValueError
            環境変数が未設定かつ default が空文字の場合。

        Examples
        --------
        >>> import os
        >>> os.environ["ARTICLES_DIR"] = "articles/"
        >>> config = ProjectConfig.from_defaults()
        >>> config.get_path("ARTICLES_DIR").is_absolute()
        True
        """
        value = os.environ.get(env_var, default)
        if not value:
            msg = (
                f"Environment variable {env_var!r} is not set and no default provided."
            )
            raise ValueError(msg)
        return self._resolve_dir(value)

    @property
    def data_path(self) -> Path:
        """データルートディレクトリの絶対パス.

        Returns
        -------
        Path
            data_dir をプロジェクトルート起点で解決した絶対パス。
        """
        return self._resolve_dir(self.data_dir)

    @property
    def research_path(self) -> Path:
        """リサーチワークスペースディレクトリの絶対パス.

        Returns
        -------
        Path
            research_dir をプロジェクトルート起点で解決した絶対パス。
        """
        return self._resolve_dir(self.research_dir)

    @classmethod
    def from_env(cls, env_path: Path | None = None) -> "ProjectConfig":
        """環境変数から ProjectConfig インスタンスを生成する.

        env_path が指定された場合はそのファイルを直接読み込む。
        None の場合は load_project_env() を使用して .env ファイルを自動探索する。

        Parameters
        ----------
        env_path : Path | None
            .env ファイルへの明示的なパス。
            None の場合は load_project_env() による自動探索を使用する。

        Returns
        -------
        ProjectConfig
            環境変数から生成された ProjectConfig インスタンス。

        Examples
        --------
        >>> config = ProjectConfig.from_env(Path("/path/to/.env"))
        >>> config.log_level
        'INFO'

        >>> config = ProjectConfig.from_env()  # 自動探索
        """
        if env_path is not None:
            from dotenv import load_dotenv

            load_dotenv(dotenv_path=env_path, override=True)
        else:
            load_project_env(override=True)

        return cls(
            fred_api_key=os.environ.get("FRED_API_KEY", ""),
            log_level=os.environ.get("LOG_LEVEL", "INFO"),
            log_format=os.environ.get("LOG_FORMAT", "console"),
            log_dir=os.environ.get("LOG_DIR", "logs/"),
            project_env=os.environ.get("PROJECT_ENV", "development"),
            data_dir=os.environ.get("DATA_DIR", "data/"),
            research_dir=os.environ.get("RESEARCH_DIR", "research/"),
        )

    @classmethod
    def from_defaults(cls) -> "ProjectConfig":
        """デフォルト値で ProjectConfig インスタンスを生成する.

        全フィールドにデフォルト値を使用する。
        fred_api_key は空文字として許容される。

        Returns
        -------
        ProjectConfig
            デフォルト値で生成された ProjectConfig インスタンス。

        Examples
        --------
        >>> config = ProjectConfig.from_defaults()
        >>> config.fred_api_key
        ''
        >>> config.log_level
        'INFO'
        """
        return cls(
            fred_api_key="",
            log_level="INFO",
            log_format="console",
            log_dir="logs/",
            project_env="development",
            data_dir="data/",
            research_dir="research/",
        )


__all__ = ["ProjectConfig"]
