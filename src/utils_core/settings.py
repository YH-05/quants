"""Environment variable management module.

環境変数の取得と型安全性を提供する。

Features
--------
- 環境変数の遅延読み込み (lazy loading)
- 型変換とバリデーション
- デフォルト値の提供
- 必須環境変数のチェック
- プロジェクトルートの .env ファイルを明示的に読み込み
- .env ファイルの柔軟な探索（DOTENV_PATH、カレントディレクトリ、親ディレクトリ）

Environment Variables
---------------------
DOTENV_PATH : str, optional
    .env ファイルへの明示的なパス。設定されている場合、他の探索をスキップ。
FRED_API_KEY : str
    FRED API Key (required)
LOG_LEVEL : LogLevel
    Log level (default: INFO)
LOG_FORMAT : LogFormat
    Log format (default: console)
LOG_DIR : str
    Log directory (default: logs/)
PROJECT_ENV : str
    Project environment (default: development)
"""

from __future__ import annotations

import logging
import os
from functools import lru_cache
from pathlib import Path
from typing import TYPE_CHECKING

from dotenv import load_dotenv

if TYPE_CHECKING:
    from .types import LogFormat, LogLevel

# Module-level logger
# Note: 基本的な logging.getLogger を使用（循環インポート回避のため）
logger = logging.getLogger(__name__)

# AIDEV-NOTE: PROJECT_ROOT と ENV_FILE_PATH は後方互換性のため残しているが、
# site-packages 環境では正しく動作しない可能性がある。
# 新しいコードでは _find_env_file() を使用すること。

# Project root directory (finance/)
# Deprecated: Use _find_env_file() instead for .env file discovery
PROJECT_ROOT: Path = Path(__file__).parent.parent.parent

# Path to .env file at project root
# Deprecated: Use _find_env_file() instead for .env file discovery
ENV_FILE_PATH: Path = PROJECT_ROOT / ".env"

# Maximum number of parent directory levels to search for .env file
_MAX_PARENT_LEVELS: int = 5


def _find_env_file() -> Path | None:
    """Find .env file using multiple search strategies.

    以下の優先順位で .env ファイルを探索する:
    1. DOTENV_PATH 環境変数で明示的に指定されたパス
    2. カレントディレクトリの .env
    3. 親ディレクトリを遡って探索（最大5レベル）

    Returns
    -------
    Path | None
        見つかった .env ファイルのパス。見つからない場合は None。

    Examples
    --------
    >>> # DOTENV_PATH が設定されている場合
    >>> os.environ["DOTENV_PATH"] = "/path/to/.env"
    >>> _find_env_file()
    PosixPath('/path/to/.env')

    >>> # カレントディレクトリに .env がある場合
    >>> _find_env_file()
    PosixPath('/current/dir/.env')
    """
    # 1. DOTENV_PATH 環境変数による明示的な指定
    dotenv_path = os.environ.get("DOTENV_PATH")
    if dotenv_path:
        path = Path(dotenv_path)
        if path.is_file():
            return path
        return None

    # 2. カレントディレクトリから親ディレクトリを遡って探索
    current = Path.cwd()
    for _ in range(_MAX_PARENT_LEVELS + 1):  # +1 はカレントディレクトリ自身を含む
        env_file = current / ".env"
        if env_file.is_file():
            return env_file
        parent = current.parent
        if parent == current:  # ルートディレクトリに到達
            break
        current = parent

    return None


def load_project_env(*, override: bool = False) -> bool:
    """Load environment variables from .env file.

    以下の優先順位で .env ファイルを探索し、環境変数を読み込む:
    1. DOTENV_PATH 環境変数で明示的に指定されたパス
    2. カレントディレクトリの .env
    3. 親ディレクトリを遡って探索（最大5レベル）

    Parameters
    ----------
    override : bool
        True の場合、既存の環境変数を上書きする。
        デフォルトは False（既存の環境変数を優先）。

    Returns
    -------
    bool
        .env ファイルが見つかり読み込まれた場合は True、
        ファイルが存在しない場合は False。

    Examples
    --------
    >>> load_project_env()
    True
    >>> load_project_env(override=True)  # 既存の環境変数を上書き
    True
    """
    env_file = _find_env_file()

    if env_file is None:
        logger.debug("No .env file found")
        return False

    logger.debug("Loading .env file", extra={"env_file": str(env_file)})
    load_dotenv(dotenv_path=env_file, override=override)
    logger.info("Loaded .env file", extra={"env_file": str(env_file)})
    return True


# Load .env file once at module import
# AIDEV-NOTE: override=False は必須。明示的に設定済みの環境変数（コンテナランタイム、
# uv run --env-file、CI、シェル）を .env より優先させるため。
# override=True にすると、リポジトリごと /app にマウントされる Docker 環境で
# docker-compose の DATA_DIR 等がホスト用パスに上書きされる。
load_project_env(override=False)


@lru_cache(maxsize=1)
def get_fred_api_key() -> str:
    """Get FRED API Key from environment variable.

    FRED API Key を環境変数 FRED_API_KEY から取得する。

    Returns
    -------
    str
        FRED API Key

    Raises
    ------
    ValueError
        FRED_API_KEY が設定されていない場合
    """
    api_key = os.environ.get("FRED_API_KEY")
    if not api_key:
        msg = "FRED_API_KEY is required. Set it in .env file or environment variable."
        raise ValueError(msg)
    return api_key


@lru_cache(maxsize=1)
def get_log_level() -> str:
    """Get log level from environment variable.

    ログレベルを環境変数 LOG_LEVEL から取得する。
    未設定の場合は INFO を返す。

    Returns
    -------
    LogLevel
        ログレベル (DEBUG, INFO, WARNING, ERROR, CRITICAL のいずれか)

    Raises
    ------
    ValueError
        不正なログレベルが設定されている場合
    """
    level_str = os.environ.get("LOG_LEVEL", "INFO").upper()
    valid_levels: tuple[LogLevel, ...] = (
        "DEBUG",
        "INFO",
        "WARNING",
        "ERROR",
        "CRITICAL",
    )

    if level_str not in valid_levels:
        msg = f"Invalid LOG_LEVEL: {level_str}. Valid values: {', '.join(valid_levels)}"
        raise ValueError(msg)

    return level_str


@lru_cache(maxsize=1)
def get_log_format() -> str:
    """Get log format from environment variable.

    ログフォーマットを環境変数 LOG_FORMAT から取得する。
    未設定の場合は console を返す。

    Returns
    -------
    LogFormat
        ログフォーマット (json または console)

    Raises
    ------
    ValueError
        不正なログフォーマットが設定されている場合
    """
    format_str = os.environ.get("LOG_FORMAT", "console").lower()
    valid_formats: tuple[LogFormat, ...] = ("json", "console")

    if format_str not in valid_formats:
        msg = (
            f"Invalid LOG_FORMAT: {format_str}. "
            f"Valid values: {', '.join(valid_formats)}"
        )
        raise ValueError(msg)

    return format_str


@lru_cache(maxsize=1)
def get_log_dir() -> str:
    """Get log directory from environment variable.

    ログディレクトリを環境変数 LOG_DIR から取得する。
    未設定の場合は logs/ を返す。

    Returns
    -------
    str
        ログディレクトリのパス
    """
    return os.environ.get("LOG_DIR", "logs/")


@lru_cache(maxsize=1)
def get_project_env() -> str:
    """Get project environment from environment variable.

    プロジェクト環境を環境変数 PROJECT_ENV から取得する。
    未設定の場合は development を返す。

    Returns
    -------
    str
        プロジェクト環境 (development, production など)
    """
    return os.environ.get("PROJECT_ENV", "development")


__all__ = [
    "ENV_FILE_PATH",
    "PROJECT_ROOT",
    "_find_env_file",
    "get_fred_api_key",
    "get_log_dir",
    "get_log_format",
    "get_log_level",
    "get_project_env",
    "load_project_env",
]
