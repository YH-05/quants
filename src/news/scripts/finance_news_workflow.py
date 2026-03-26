#!/usr/bin/env python
"""Finance news collection workflow CLI.

This module provides the CLI entry point for the news collection workflow,
orchestrating the complete pipeline:

- per-category (default): Collect -> Extract -> Summarize -> Group -> Export -> Publish
- per-article (legacy): Collect -> Extract -> Summarize -> Publish

Usage
-----
Run with default configuration (per-category format):

    python -m news.scripts.finance_news_workflow

Run with legacy per-article format:

    python -m news.scripts.finance_news_workflow --format per-article

Export Markdown only (skip Issue creation):

    python -m news.scripts.finance_news_workflow --export-only

Run in dry-run mode (skip Issue creation):

    python -m news.scripts.finance_news_workflow --dry-run

Filter by status:

    python -m news.scripts.finance_news_workflow --status index,stock

Limit articles:

    python -m news.scripts.finance_news_workflow --max-articles 10

Enable verbose logging:

    python -m news.scripts.finance_news_workflow --verbose

Use a specific config file:

    python -m news.scripts.finance_news_workflow --config data/config/news-collection-config.yaml
"""

from __future__ import annotations

import argparse
import asyncio
import logging
import sys
from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING

from database.db.connection import get_data_dir
from news.config.models import load_config
from news.orchestrator import NewsWorkflowOrchestrator
from utils_core.logging import get_logger
from utils_core.logging import setup_logging as _setup_logging

if TYPE_CHECKING:
    from news.models import WorkflowResult

logger = get_logger(__name__, module="scripts.finance_news_workflow")

# Default configuration file path
DEFAULT_CONFIG_PATH = get_data_dir() / "config" / "news-collection-config.yaml"

# Default log directory
DEFAULT_LOG_DIR = Path("logs")


def setup_logging(
    *,
    verbose: bool = False,
    log_dir: Path | None = None,
) -> Path:
    """Initialize logging configuration for the workflow.

    Sets up logging to both console and file. The log file is named
    with the current date: `logs/news-workflow-{date}.log`.

    - Console: verbose=True -> DEBUG, False -> INFO
    - File: Always DEBUG (for detailed failure analysis)

    Parameters
    ----------
    verbose : bool, optional
        If True, sets console log level to DEBUG. Default is INFO.
    log_dir : Path | None, optional
        Directory for log files. Default is `logs/`.

    Returns
    -------
    Path
        Path to the created log file.

    Examples
    --------
    >>> log_file = setup_logging(verbose=False)
    >>> log_file.name
    'news-workflow-2026-01-30.log'

    >>> log_file = setup_logging(verbose=True)
    >>> logging.root.level == logging.DEBUG
    True
    """
    console_level = "DEBUG" if verbose else "INFO"
    file_level = "DEBUG"  # Always DEBUG for detailed failure analysis

    # Use default log directory if not specified
    if log_dir is None:
        log_dir = DEFAULT_LOG_DIR

    # Create log directory if it doesn't exist
    log_dir.mkdir(parents=True, exist_ok=True)

    # Generate date-based log file name
    date_str = datetime.now().strftime("%Y-%m-%d")
    log_file = log_dir / f"news-workflow-{date_str}.log"

    # Setup logging using the utils_core.logging module
    _setup_logging(
        level=console_level,
        file_level=file_level,
        format="console",
        log_file=log_file,
        include_timestamp=True,
        include_caller_info=True,
        force=True,
    )

    logger.info(
        "Logging initialized",
        log_file=str(log_file),
        console_level=console_level,
        file_level=file_level,
    )

    return log_file


def create_parser() -> argparse.ArgumentParser:
    """Create the argument parser for the workflow script.

    Returns
    -------
    argparse.ArgumentParser
        Configured argument parser with all supported options.

    Examples
    --------
    >>> parser = create_parser()
    >>> args = parser.parse_args(["--dry-run", "--status", "index"])
    >>> args.dry_run
    True
    >>> args.status
    'index'
    """
    parser = argparse.ArgumentParser(
        prog="finance-news-workflow",
        description="Run the finance news collection workflow pipeline.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""\
examples:
  %(prog)s                                Run with default config (per-category)
  %(prog)s --dry-run                      Run without creating Issues
  %(prog)s --format per-article           Use legacy per-article publishing
  %(prog)s --export-only                  Export Markdown only, skip Issue creation
  %(prog)s --status index,stock           Filter by status
  %(prog)s --max-articles 10              Limit to 10 articles
  %(prog)s --config config.yaml           Use specific config file
""",
    )

    parser.add_argument(
        "--config",
        type=str,
        default=None,
        help="Path to YAML configuration file (default: data/config/news-collection-config.yaml)",
    )

    parser.add_argument(
        "--dry-run",
        action="store_true",
        default=False,
        help="Run workflow without creating GitHub Issues",
    )

    parser.add_argument(
        "--status",
        type=str,
        default=None,
        help="Comma-separated list of statuses to filter by (e.g., 'index,stock')",
    )

    parser.add_argument(
        "--max-articles",
        type=int,
        default=None,
        help="Maximum number of articles to process",
    )

    parser.add_argument(
        "--format",
        type=str,
        choices=["per-category", "per-article"],
        default="per-category",
        help="Publishing format: per-category (default) or per-article (legacy)",
    )

    parser.add_argument(
        "--export-only",
        action="store_true",
        default=False,
        help="Export Markdown files only, skip GitHub Issue creation",
    )

    parser.add_argument(
        "--verbose",
        "-v",
        action="store_true",
        default=False,
        help="Enable verbose (DEBUG level) logging output",
    )

    return parser


def parse_statuses(status_str: str | None) -> list[str] | None:
    """Parse comma-separated status string into a list.

    Parameters
    ----------
    status_str : str | None
        Comma-separated status string, or None.

    Returns
    -------
    list[str] | None
        List of status strings, or None if input was None.

    Examples
    --------
    >>> parse_statuses("index,stock")
    ['index', 'stock']
    >>> parse_statuses("index")
    ['index']
    >>> parse_statuses(None) is None
    True
    """
    if status_str is None:
        return None
    return [s.strip() for s in status_str.split(",")]


def print_failure_summary(result: WorkflowResult) -> None:
    """Print failure summary if any failures occurred.

    Parameters
    ----------
    result : WorkflowResult
        The workflow execution result.
    """
    total_failures = (
        len(result.extraction_failures)
        + len(result.summarization_failures)
        + len(result.publication_failures)
    )

    if total_failures == 0:
        return

    print(f"\n{'=' * 60}")
    print(f"失敗詳細 ({total_failures}件)")
    print(f"{'=' * 60}")

    if result.extraction_failures:
        print(f"\n  [抽出失敗] {len(result.extraction_failures)}件")
        for f in result.extraction_failures[:5]:  # Show first 5
            title = f.title[:35] + "..." if len(f.title) > 35 else f.title
            print(f"    - {title}")
            print(f"      {f.error}")
        if len(result.extraction_failures) > 5:
            print(f"    ... 他 {len(result.extraction_failures) - 5}件")

    if result.summarization_failures:
        print(f"\n  [要約失敗] {len(result.summarization_failures)}件")
        for f in result.summarization_failures[:5]:
            title = f.title[:35] + "..." if len(f.title) > 35 else f.title
            print(f"    - {title}")
            print(f"      {f.error}")
        if len(result.summarization_failures) > 5:
            print(f"    ... 他 {len(result.summarization_failures) - 5}件")

    if result.publication_failures:
        print(f"\n  [公開失敗] {len(result.publication_failures)}件")
        for f in result.publication_failures[:5]:
            title = f.title[:35] + "..." if len(f.title) > 35 else f.title
            print(f"    - {title}")
            print(f"      {f.error}")
        if len(result.publication_failures) > 5:
            print(f"    ... 他 {len(result.publication_failures) - 5}件")


async def run_workflow(
    config_path: Path,
    dry_run: bool = False,
    statuses: list[str] | None = None,
    max_articles: int | None = None,
    publish_format: str = "per-category",
    export_only: bool = False,
) -> int:
    """Run the workflow asynchronously.

    Parameters
    ----------
    config_path : Path
        Path to the configuration file.
    dry_run : bool, optional
        If True, skip actual Issue creation. Default is False.
    statuses : list[str] | None, optional
        Filter articles by status. None means no filtering.
    max_articles : int | None, optional
        Maximum number of articles to process. None means no limit.
    publish_format : str, optional
        Publishing format: "per-category" (default) or "per-article" (legacy).
    export_only : bool, optional
        If True, export Markdown only without creating Issues. Default is False.

    Returns
    -------
    int
        Exit code: 0 for success, 1 for failure.
    """
    logger.info(
        "Starting finance news workflow",
        config_path=str(config_path),
        dry_run=dry_run,
        statuses=statuses,
        max_articles=max_articles,
        publish_format=publish_format,
        export_only=export_only,
    )

    try:
        config = load_config(config_path)

        # Override publishing format from CLI argument
        # Convert CLI format ("per-category") to config format ("per_category")
        config_format = publish_format.replace("-", "_")
        config.publishing.format = config_format

        orchestrator = NewsWorkflowOrchestrator(config)

        result = await orchestrator.run(
            statuses=statuses,
            max_articles=max_articles,
            dry_run=dry_run,
            export_only=export_only,
        )

        # Show failure details if any
        print_failure_summary(result)

        logger.debug(
            "Workflow completed successfully",
            total_collected=result.total_collected,
            total_published=result.total_published,
            elapsed_seconds=result.elapsed_seconds,
        )

        return 0

    except FileNotFoundError as e:
        logger.error("Configuration file not found", error=str(e))
        print(f"Error: {e}", file=sys.stderr)
        return 1

    except Exception as e:
        logger.error(
            "Workflow failed with exception",
            error=str(e),
            error_type=type(e).__name__,
            exc_info=True,
        )
        print(f"Error: {e}", file=sys.stderr)
        return 1


def main(argv: list[str] | None = None) -> int:
    """Main entry point for the finance news workflow script.

    Parameters
    ----------
    argv : list[str] | None, optional
        Command line arguments. If None, uses sys.argv[1:].

    Returns
    -------
    int
        Exit code: 0 for success, 1 for failure.

    Examples
    --------
    >>> exit_code = main(["--dry-run"])
    >>> exit_code
    0

    >>> exit_code = main(["--config", "config.yaml", "--status", "index"])
    """
    parser = create_parser()
    args = parser.parse_args(argv)

    # Setup logging with file output and console output
    setup_logging(verbose=args.verbose)

    logger.info(
        "Finance news workflow script started",
        config=args.config,
        dry_run=args.dry_run,
        status=args.status,
        max_articles=args.max_articles,
        verbose=args.verbose,
        format=args.format,
        export_only=args.export_only,
    )

    # Determine config path
    config_path = Path(args.config) if args.config else DEFAULT_CONFIG_PATH

    # Parse statuses
    statuses = parse_statuses(args.status)

    # Run the workflow
    return asyncio.run(
        run_workflow(
            config_path=config_path,
            dry_run=args.dry_run,
            statuses=statuses,
            max_articles=args.max_articles,
            publish_format=args.format,
            export_only=args.export_only,
        )
    )


if __name__ == "__main__":
    sys.exit(main())


# Export all public symbols
__all__ = [
    "DEFAULT_CONFIG_PATH",
    "DEFAULT_LOG_DIR",
    "create_parser",
    "main",
    "parse_statuses",
    "print_failure_summary",
    "run_workflow",
    "setup_logging",
]
