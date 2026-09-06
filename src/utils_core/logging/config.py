"""Structured logging configuration using structlog.

structlog ベースの構造化ロギング設定を提供する。

Features
--------
- structlog による構造化ロギング
- 日付別ログファイル出力（finance-YYYY-MM-DD.log 形式）
- 環境変数による設定（LOG_DIR, LOG_FILE_ENABLED, LOG_LEVEL, LOG_FORMAT）
- 重複ハンドラー追加の防止
- ProcessorFormatter による logging ハンドラー連携
"""

import contextlib
import functools
import inspect
import logging
import os
import stat
import sys
import time
from collections.abc import Iterator
from contextlib import contextmanager
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Protocol

import structlog
from structlog import BoundLogger
from structlog.contextvars import bind_contextvars, unbind_contextvars

from ..settings import (
    get_log_dir,
    get_log_format,
    get_log_level,
    get_project_env,
    load_project_env,
)
from ..types import LogFormat, LogLevel

_initialized = False


def _create_secure_log_file(log_file: Path) -> None:
    """Create log file atomically with secure permissions (CWE-732, TOCTOU).

    Uses os.open() with O_EXCL flag for atomic exclusive creation at 0o600,
    completely eliminating the TOCTOU window. If the file already exists,
    catches FileExistsError and corrects permissions via chmod.

    Parameters
    ----------
    log_file : Path
        Path to the log file to create or secure
    """
    log_file.parent.mkdir(parents=True, exist_ok=True)
    try:
        fd = os.open(
            log_file,
            os.O_CREAT | os.O_EXCL | os.O_WRONLY | os.O_APPEND,
            stat.S_IRUSR | stat.S_IWUSR,  # 0o600
        )
        os.close(fd)
    except FileExistsError:
        log_file.chmod(0o600)


def _get_shared_processors() -> list[Any]:
    """structlog と logging ハンドラーで共有するプロセッサーを返す."""
    return [
        structlog.contextvars.merge_contextvars,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        structlog.processors.UnicodeDecoder(),
    ]


def _ensure_basic_config() -> None:
    """get_logger 呼び出し前に最小限のロギング設定を確保する."""
    global _initialized
    if _initialized:
        return
    _initialized = True

    # AIDEV-NOTE: override=False は必須。理由は utils_core/settings.py の
    # モジュール末尾 AIDEV-NOTE を参照（明示設定された環境変数を .env より優先）。
    # 本関数は get_logger() の初回呼び出しで発火するため、ここが override=True だと
    # 実質すべてのエントリポイントでコンテナの環境変数が .env に上書きされる。
    load_project_env(override=False)

    # Clear cached environment variables to reflect any changes
    get_log_level.cache_clear()

    try:
        default_level = get_log_level()
    except ValueError:
        default_level = "INFO"

    # 共有プロセッサー
    shared_processors = _get_shared_processors()

    # コンソール用フォーマッター
    console_formatter = structlog.stdlib.ProcessorFormatter(
        foreign_pre_chain=shared_processors,
        processors=[
            structlog.stdlib.ProcessorFormatter.remove_processors_meta,
            structlog.dev.ConsoleRenderer(colors=True),
        ],
    )

    # ルートロガーを設定
    root_logger = logging.getLogger()
    root_logger.setLevel(getattr(logging, default_level))

    # 既存のハンドラーをクリア
    root_logger.handlers.clear()

    # コンソールハンドラーを追加
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(console_formatter)
    root_logger.addHandler(console_handler)

    # structlog を設定（ProcessorFormatter 用）
    structlog.configure(
        processors=[
            *shared_processors,
            structlog.stdlib.ProcessorFormatter.wrap_for_formatter,
        ],
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=False,
    )


class LoggerProtocol(Protocol):
    """構造化ロガーのプロトコル定義."""

    def bind(self, **kwargs: Any) -> "LoggerProtocol":
        """コンテキスト変数をロガーにバインドする."""
        ...

    def unbind(self, *keys: str) -> "LoggerProtocol":
        """コンテキスト変数をロガーからアンバインドする."""
        ...

    def debug(self, event: str, **kwargs: Any) -> None:
        """DEBUG レベルのログを出力する."""
        ...

    def info(self, event: str, **kwargs: Any) -> None:
        """INFO レベルのログを出力する."""
        ...

    def warning(self, event: str, **kwargs: Any) -> None:
        """WARNING レベルのログを出力する."""
        ...

    def error(self, event: str, **kwargs: Any) -> None:
        """ERROR レベルのログを出力する."""
        ...

    def critical(self, event: str, **kwargs: Any) -> None:
        """CRITICAL レベルのログを出力する."""
        ...


def add_timestamp(_: Any, __: Any, event_dict: dict[str, Any]) -> dict[str, Any]:
    """ログエントリに ISO タイムスタンプを追加する.

    Parameters
    ----------
    _ : Any
        ロガー（未使用）
    __ : Any
        メソッド名（未使用）
    event_dict : dict[str, Any]
        変更対象のイベント辞書

    Returns
    -------
    dict[str, Any]
        タイムスタンプを追加したイベント辞書
    """
    event_dict["timestamp"] = datetime.now(UTC).isoformat()
    return event_dict


def add_caller_info(_: Any, __: Any, event_dict: dict[str, Any]) -> dict[str, Any]:
    """ログエントリに呼び出し元情報（ファイル、関数、行番号）を追加する.

    Parameters
    ----------
    _ : Any
        ロガー（未使用）
    __ : Any
        メソッド名（未使用）
    event_dict : dict[str, Any]
        変更対象のイベント辞書

    Returns
    -------
    dict[str, Any]
        呼び出し元情報を追加したイベント辞書
    """
    try:
        frame = None
        stack = inspect.stack()

        for f in stack[4:12]:
            if f.filename and f.function:
                module = inspect.getmodule(f.frame)
                if (
                    module
                    and not module.__name__.startswith("structlog")
                    and not module.__name__.startswith("logging")
                    and "site-packages" not in f.filename
                ):
                    frame = f
                    break

        if frame:
            event_dict["caller"] = {
                "filename": Path(frame.filename).name,
                "function": frame.function,
                "line": frame.lineno,
            }
    except Exception:  # nosec B110
        pass

    return event_dict


def add_log_level_upper(_: Any, __: Any, event_dict: dict[str, Any]) -> dict[str, Any]:
    """ログレベルを大文字に変換する.

    Parameters
    ----------
    _ : Any
        ロガー（未使用）
    __ : Any
        メソッド名（未使用）
    event_dict : dict[str, Any]
        変更対象のイベント辞書

    Returns
    -------
    dict[str, Any]
        大文字のレベルを持つイベント辞書
    """
    if "level" in event_dict:
        event_dict["level"] = event_dict["level"].upper()
    return event_dict


def _get_date_based_log_file(log_dir: Path) -> Path:
    """日付ベースのログファイルパスを生成する.

    Parameters
    ----------
    log_dir : Path
        ログディレクトリのパス

    Returns
    -------
    Path
        finance-YYYY-MM-DD.log 形式のログファイルパス
    """
    today = datetime.now().strftime("%Y-%m-%d")
    return log_dir / f"finance-{today}.log"


def setup_logging(
    *,
    level: LogLevel | str = "INFO",
    file_level: LogLevel | str | None = None,
    format: LogFormat = "console",
    log_file: str | Path | None = None,
    include_timestamp: bool = True,
    include_caller_info: bool = True,
    force: bool = False,
) -> None:
    """構造化ロギングの設定をセットアップする.

    Parameters
    ----------
    level : LogLevel | str
        コンソール出力のログレベル（DEBUG, INFO, WARNING, ERROR, CRITICAL）。
        LOG_LEVEL 環境変数でも設定可能。
    file_level : LogLevel | str | None
        ファイル出力のログレベル。None の場合は level と同じ。
        コンソールはクリーンに保ちつつ、ファイルに詳細ログを保存する場合に有用。
        例: level="INFO", file_level="DEBUG" でコンソールは INFO、ファイルは DEBUG。
    format : LogFormat
        出力フォーマット: "json", "console", "plain"
        - json: 構造化 JSON 出力（本番環境向け）
        - console: カラー付き人間可読出力（開発環境向け）
        - plain: シンプルな key=value 出力
    log_file : str | Path | None
        ログ出力先ファイルパス（LOG_DIR より優先）
    include_timestamp : bool
        ISO タイムスタンプをログに追加するか
    include_caller_info : bool
        呼び出し元情報（ファイル、関数、行番号）を追加するか
    force : bool
        既存の設定があっても強制的に再設定するか
    """
    global _initialized

    # AIDEV-NOTE: override=False は必須。理由は utils_core/settings.py の
    # モジュール末尾 AIDEV-NOTE を参照（明示設定された環境変数を .env より優先）。
    load_project_env(override=False)

    # Clear cached environment variables to reflect any changes
    get_log_level.cache_clear()
    get_log_format.cache_clear()
    get_log_dir.cache_clear()
    get_project_env.cache_clear()

    # Override with environment variables if set
    if os.environ.get("LOG_LEVEL"):
        with contextlib.suppress(ValueError):
            # Invalid level in env var, use default
            level = get_log_level()

    if os.environ.get("LOG_FORMAT"):
        with contextlib.suppress(ValueError):
            # Invalid format in env var, use default
            format_value = get_log_format()
            # Support legacy "plain" format as alias for "console"
            if format_value == "plain":  # type: ignore[comparison-overlap]
                format = "console"
            else:
                format = format_value  # type: ignore

    env_log_dir = get_log_dir()
    log_file_enabled = os.environ.get("LOG_FILE_ENABLED", "true").lower() != "false"

    final_log_file: Path | None = None
    if log_file:
        final_log_file = Path(log_file)
    elif log_file_enabled and env_log_dir:
        log_dir = Path(env_log_dir)
        log_dir.mkdir(parents=True, exist_ok=True)
        final_log_file = _get_date_based_log_file(log_dir)

    level_str = level.upper()
    level_value = getattr(logging, level_str)

    # file_level が指定されている場合は別のレベル値を使用
    if file_level is not None:
        file_level_str = file_level.upper()
        file_level_value = getattr(logging, file_level_str)
    else:
        file_level_value = level_value

    # 共有プロセッサーを構築
    shared_processors: list[Any] = [
        structlog.contextvars.merge_contextvars,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
    ]

    if include_timestamp:
        shared_processors.append(add_timestamp)

    if include_caller_info:
        shared_processors.append(add_caller_info)

    shared_processors.extend(
        [
            add_log_level_upper,
            structlog.stdlib.PositionalArgumentsFormatter(),
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            structlog.processors.UnicodeDecoder(),
        ]
    )

    # フォーマットに応じたレンダラーを選択
    is_development = get_project_env() == "development" or format == "console"

    if format == "json":
        console_renderer: Any = structlog.processors.JSONRenderer()
        file_renderer: Any = structlog.processors.JSONRenderer()
    elif format == "console" and is_development:
        console_renderer = structlog.dev.ConsoleRenderer(colors=True)
        file_renderer = structlog.dev.ConsoleRenderer(colors=False)
    else:
        console_renderer = structlog.processors.KeyValueRenderer()
        file_renderer = structlog.processors.KeyValueRenderer()

    # ルートロガーを設定
    root_logger = logging.getLogger()

    if force:
        root_logger.handlers.clear()
        _initialized = False

    # ルートロガーのレベルは最も寛容なレベルに設定
    # （file_level が DEBUG で level が INFO の場合、DEBUG ログを通す必要がある）
    root_logger_level = min(level_value, file_level_value)
    root_logger.setLevel(root_logger_level)

    # コンソールハンドラーを追加（重複チェック）
    has_console_handler = any(
        isinstance(h, logging.StreamHandler) and not isinstance(h, logging.FileHandler)
        for h in root_logger.handlers
    )

    if not has_console_handler:
        console_formatter = structlog.stdlib.ProcessorFormatter(
            foreign_pre_chain=shared_processors,
            processors=[
                structlog.stdlib.ProcessorFormatter.remove_processors_meta,
                console_renderer,
            ],
        )
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setFormatter(console_formatter)
        console_handler.setLevel(level_value)
        root_logger.addHandler(console_handler)

    # ファイルハンドラーを追加（指定された場合）
    if final_log_file:
        # TOCTOU対策: FileHandler作成前に安全なパーミッションでファイルを作成（CWE-732）
        _create_secure_log_file(final_log_file)

        existing_file_handlers = [
            h
            for h in root_logger.handlers
            if isinstance(h, logging.FileHandler)
            and h.baseFilename == str(final_log_file.resolve())
        ]

        if not existing_file_handlers:
            file_formatter = structlog.stdlib.ProcessorFormatter(
                foreign_pre_chain=shared_processors,
                processors=[
                    structlog.stdlib.ProcessorFormatter.remove_processors_meta,
                    file_renderer,
                ],
            )
            file_handler = logging.FileHandler(final_log_file, encoding="utf-8")
            file_handler.setFormatter(file_formatter)
            file_handler.setLevel(file_level_value)
            root_logger.addHandler(file_handler)

    # structlog を設定（ProcessorFormatter 用）
    structlog.configure(
        processors=[
            *shared_processors,
            structlog.stdlib.ProcessorFormatter.wrap_for_formatter,
        ],
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=not force,
    )

    _initialized = True

    if level_str != "DEBUG":
        for logger_name in ["urllib3", "asyncio", "filelock"]:
            logging.getLogger(logger_name).setLevel(logging.WARNING)


def get_logger(name: str, **context: Any) -> BoundLogger:
    """オプションのコンテキスト付きで構造化ロガーインスタンスを取得する.

    Parameters
    ----------
    name : str
        ロガー名（通常は __name__）
    **context : Any
        ロガーにバインドする初期コンテキスト

    Returns
    -------
    BoundLogger
        設定済みの structlog ロガーインスタンス

    Examples
    --------
    >>> logger = get_logger(__name__)
    >>> logger.info("Processing started", items_count=100)

    >>> logger = get_logger(__name__, module="data_processor", version="1.0")
    >>> logger.error("Processing failed", error_type="ValidationError")
    """
    _ensure_basic_config()

    logger: BoundLogger = structlog.get_logger(name)

    if context:
        logger = logger.bind(**context)

    return logger


@contextmanager
def log_context(**kwargs: Any) -> Iterator[None]:
    """コンテキスト変数を一時的にバインドするコンテキストマネージャ.

    Parameters
    ----------
    **kwargs : Any
        バインドするコンテキスト変数

    Yields
    ------
    None

    Examples
    --------
    >>> logger = get_logger(__name__)
    >>> with log_context(user_id=123, request_id="abc"):
    ...     logger.info("Processing user request")
    """
    bind_contextvars(**kwargs)
    try:
        yield
    finally:
        unbind_contextvars(*kwargs.keys())


def set_log_level(level: LogLevel | str, logger_name: str | None = None) -> None:
    """ログレベルを動的に変更する.

    Parameters
    ----------
    level : LogLevel | str
        新しいログレベル
    logger_name : str | None
        更新対象のロガー名。None の場合はルートロガーを更新

    Raises
    ------
    AttributeError
        level が有効なログレベルでない場合
    """
    level_value = getattr(logging, level.upper())

    if logger_name:
        logging.getLogger(logger_name).setLevel(level_value)
    else:
        logging.root.setLevel(level_value)
        for handler in logging.root.handlers:
            handler.setLevel(level_value)


def log_performance(logger: BoundLogger) -> Any:
    """Decorator to log function performance metrics.

    Parameters
    ----------
    logger : BoundLogger
        Logger instance to use

    Returns
    -------
    Callable
        Decorated function

    Examples
    --------
    >>> logger = get_logger(__name__)
    >>> @log_performance(logger)
    ... def process_data(items):
    ...     return [item * 2 for item in items]
    """

    def decorator(func: Any) -> Any:
        @functools.wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            start_time = time.perf_counter()
            func_name = func.__name__

            # Log function call
            logger.debug(
                f"Function {func_name} started",
                function=func_name,
                args_count=len(args),
                kwargs_count=len(kwargs),
            )

            try:
                result = func(*args, **kwargs)
                duration_ms = (time.perf_counter() - start_time) * 1000

                # Log successful completion with duration
                logger.debug(
                    f"Function {func_name} completed",
                    function=func_name,
                    duration_ms=round(duration_ms, 2),
                    success=True,
                )

                return result

            except Exception as e:
                duration_ms = (time.perf_counter() - start_time) * 1000

                # Log error with duration
                logger.error(
                    f"Function {func_name} failed",
                    function=func_name,
                    duration_ms=round(duration_ms, 2),
                    success=False,
                    error_type=type(e).__name__,
                    error_message=str(e),
                    exc_info=True,
                )
                raise

        return wrapper

    return decorator
