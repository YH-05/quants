"""Integrated industry report collector with CLI entry point.

This module provides the ``IndustryCollector`` class that orchestrates
all configured industry report scrapers (consulting firms, investment
banks) and collects reports in a single run.

CLI Usage
---------
Collect all reports for a sector::

    $ uv run python -m market.industry.collect --sector Technology

Collect reports for a specific ticker::

    $ uv run python -m market.industry.collect --ticker AAPL

Collect from a single source::

    $ uv run python -m market.industry.collect --source mckinsey

Features
--------
- Unified CLI with ``--sector``, ``--ticker``, and ``--source`` options
- Sequential execution of all matching scrapers
- Progress logging and result summary
- Graceful error handling (individual scraper failures do not stop batch)

See Also
--------
market.industry.scheduler : APScheduler weekly execution.
market.industry.scrapers : Individual scraper implementations.
rss.services.batch_scheduler : Reference implementation (RSS batch scheduler).
"""

from __future__ import annotations

import argparse
import asyncio
import time
from pathlib import Path

from pydantic import BaseModel, Field

from database.db.connection import get_data_dir
from utils_core.logging import get_logger

logger = get_logger(__name__)

# =============================================================================
# Default Configuration
# =============================================================================

DEFAULT_OUTPUT_SUBDIR: str = "raw/industry_reports"
"""Default subdirectory (relative to DATA_DIR) for saving collected industry reports.

See Also
--------
database.db.connection.get_data_dir
"""

# Source key to scraper class mapping
_SOURCE_REGISTRY: dict[str, str] = {
    "mckinsey": "McKinseyScraper",
    "bcg": "BCGScraper",
    "deloitte": "DeloitteScraper",
    "pwc": "PwCScraper",
    "bain": "BainScraper",
    "accenture": "AccentureScraper",
    "ey": "EYScraper",
    "kpmg": "KPMGScraper",
    "goldman": "GoldmanSachsScraper",
    "morgan_stanley": "MorganStanleyScraper",
    "jpmorgan": "JPMorganScraper",
}
"""Registry mapping source keys to scraper class names."""


# =============================================================================
# Data Models
# =============================================================================


class CollectionResult(BaseModel, frozen=True):
    """Result of a single source collection operation.

    Parameters
    ----------
    source : str
        Name of the data source.
    success : bool
        Whether the collection succeeded.
    report_count : int
        Number of reports collected.
    error_message : str | None
        Error message if the collection failed. Defaults to ``None``.
    duration_seconds : float
        Duration of the collection in seconds. Defaults to ``0.0``.

    Examples
    --------
    >>> result = CollectionResult(
    ...     source="McKinsey",
    ...     success=True,
    ...     report_count=5,
    ...     duration_seconds=2.5,
    ... )
    >>> result.report_count
    5
    """

    source: str
    success: bool
    report_count: int = 0
    error_message: str | None = None
    duration_seconds: float = 0.0


class CollectionStats(BaseModel, frozen=True):
    """Aggregated statistics from a collection run.

    Parameters
    ----------
    total_sources : int
        Total number of sources attempted.
    success_count : int
        Number of sources that succeeded.
    failure_count : int
        Number of sources that failed.
    total_reports : int
        Total number of reports collected across all sources.
    duration_seconds : float
        Total duration of the collection run in seconds.
    results : list[CollectionResult]
        Per-source collection results. Defaults to empty list.

    Examples
    --------
    >>> stats = CollectionStats(
    ...     total_sources=7,
    ...     success_count=5,
    ...     failure_count=2,
    ...     total_reports=42,
    ...     duration_seconds=120.5,
    ... )
    >>> stats.success_count
    5
    """

    total_sources: int
    success_count: int
    failure_count: int
    total_reports: int
    duration_seconds: float
    results: list[CollectionResult] = Field(default_factory=list)


# =============================================================================
# IndustryCollector
# =============================================================================


class IndustryCollector:
    """Orchestrator for collecting industry reports from all configured sources.

    Provides a unified interface for running multiple scrapers (consulting
    firms and investment banks) with optional filtering by sector, ticker,
    or individual source.

    Parameters
    ----------
    sector : str
        Target sector for scraping. Defaults to ``"all"``.
    ticker : str | None
        Target ticker symbol for sector lookup. Defaults to ``None``.
    source : str | None
        Specific source key to run (e.g. ``"mckinsey"``).
        If ``None``, runs all sources. Defaults to ``None``.
    output_dir : Path | None
        Base output directory for reports.
        Defaults to ``data/raw/industry_reports``.

    Examples
    --------
    >>> collector = IndustryCollector(sector="Technology")
    >>> stats = asyncio.run(collector.collect())
    >>> print(f"Collected {stats.total_reports} reports")
    """

    def __init__(
        self,
        sector: str = "all",
        ticker: str | None = None,
        source: str | None = None,
        output_dir: Path | None = None,
    ) -> None:
        self.sector: str = sector
        self.ticker: str | None = ticker
        self.source: str | None = source
        self.output_dir: Path = output_dir or (get_data_dir() / DEFAULT_OUTPUT_SUBDIR)

        logger.info(
            "IndustryCollector initialized",
            sector=sector,
            ticker=ticker,
            source=source,
            output_dir=str(self.output_dir),
        )

    def _get_scrapers(self) -> list:
        """Build the list of scraper instances based on filter settings.

        Returns a list of scraper instances matching the current
        ``source`` filter. If ``source`` is ``None``, all available
        scrapers are returned.

        Returns
        -------
        list
            List of scraper instances (subclasses of BaseScraper).
        """
        from market.industry.scrapers.consulting import (
            AccentureScraper,
            BainScraper,
            BCGScraper,
            DeloitteScraper,
            EYScraper,
            KPMGScraper,
            McKinseyScraper,
            PwCScraper,
        )
        from market.industry.scrapers.investment_bank import (
            GoldmanSachsScraper,
            JPMorganScraper,
            MorganStanleyScraper,
        )

        all_scrapers = {
            "mckinsey": lambda: McKinseyScraper(
                sector=self.sector,
                output_dir=self.output_dir / "mckinsey",
            ),
            "bcg": lambda: BCGScraper(
                sector=self.sector,
                output_dir=self.output_dir / "bcg",
            ),
            "deloitte": lambda: DeloitteScraper(
                sector=self.sector,
                output_dir=self.output_dir / "deloitte",
            ),
            "pwc": lambda: PwCScraper(
                sector=self.sector,
                output_dir=self.output_dir / "pwc",
            ),
            "bain": lambda: BainScraper(
                sector=self.sector,
                output_dir=self.output_dir / "bain",
            ),
            "accenture": lambda: AccentureScraper(
                sector=self.sector,
                output_dir=self.output_dir / "accenture",
            ),
            "ey": lambda: EYScraper(
                sector=self.sector,
                output_dir=self.output_dir / "ey",
            ),
            "kpmg": lambda: KPMGScraper(
                sector=self.sector,
                output_dir=self.output_dir / "kpmg",
            ),
            "goldman": lambda: GoldmanSachsScraper(
                sector=self.sector,
                output_dir=self.output_dir / "goldman",
            ),
            "morgan_stanley": lambda: MorganStanleyScraper(
                sector=self.sector,
                output_dir=self.output_dir / "morgan_stanley",
            ),
            "jpmorgan": lambda: JPMorganScraper(
                sector=self.sector,
                output_dir=self.output_dir / "jpmorgan",
            ),
        }

        if self.source is not None:
            source_key = self.source.lower()
            if source_key in all_scrapers:
                return [all_scrapers[source_key]()]
            logger.warning(
                "Unknown source key, returning empty list",
                source=self.source,
                valid_sources=list(all_scrapers.keys()),
            )
            return []

        return [factory() for factory in all_scrapers.values()]

    async def collect(self) -> CollectionStats:
        """Execute collection from all matching sources.

        Runs each scraper sequentially, collecting reports and
        aggregating statistics. Individual scraper failures do not
        stop the batch.

        Returns
        -------
        CollectionStats
            Aggregated collection statistics.
        """
        scrapers = self._get_scrapers()
        start_time = time.perf_counter()

        logger.info(
            "Starting industry report collection",
            scraper_count=len(scrapers),
            sector=self.sector,
            source=self.source,
        )

        results: list[CollectionResult] = []

        for scraper in scrapers:
            source_start = time.perf_counter()

            try:
                async with scraper:
                    scraping_result = await scraper.scrape()

                source_duration = time.perf_counter() - source_start

                if scraping_result.success:
                    # Save reports to disk
                    if hasattr(scraper, "save_reports") and scraping_result.reports:
                        await scraper.save_reports(scraping_result.reports)

                    results.append(
                        CollectionResult(
                            source=scraper.source_name,
                            success=True,
                            report_count=len(scraping_result.reports),
                            duration_seconds=round(source_duration, 3),
                        )
                    )

                    logger.info(
                        "Source collection succeeded",
                        source=scraper.source_name,
                        report_count=len(scraping_result.reports),
                        duration_seconds=round(source_duration, 3),
                    )
                else:
                    results.append(
                        CollectionResult(
                            source=scraper.source_name,
                            success=False,
                            report_count=0,
                            error_message=scraping_result.error_message,
                            duration_seconds=round(source_duration, 3),
                        )
                    )

                    logger.warning(
                        "Source collection failed",
                        source=scraper.source_name,
                        error=scraping_result.error_message,
                        duration_seconds=round(source_duration, 3),
                    )

            except Exception as e:
                source_duration = time.perf_counter() - source_start
                results.append(
                    CollectionResult(
                        source=scraper.source_name,
                        success=False,
                        report_count=0,
                        error_message=str(e),
                        duration_seconds=round(source_duration, 3),
                    )
                )
                logger.error(
                    "Source collection raised exception",
                    source=scraper.source_name,
                    error=str(e),
                    exc_info=True,
                )

        total_duration = time.perf_counter() - start_time
        success_count = sum(1 for r in results if r.success)
        failure_count = len(results) - success_count
        total_reports = sum(r.report_count for r in results)

        stats = CollectionStats(
            total_sources=len(results),
            success_count=success_count,
            failure_count=failure_count,
            total_reports=total_reports,
            duration_seconds=round(total_duration, 3),
            results=results,
        )

        logger.info(
            "Industry report collection completed",
            total_sources=stats.total_sources,
            success_count=stats.success_count,
            failure_count=stats.failure_count,
            total_reports=stats.total_reports,
            duration_seconds=stats.duration_seconds,
        )

        return stats


# =============================================================================
# CLI
# =============================================================================


def build_parser() -> argparse.ArgumentParser:
    """Build the argument parser for the industry collector CLI.

    Returns
    -------
    argparse.ArgumentParser
        Configured argument parser.
    """
    parser = argparse.ArgumentParser(
        prog="python -m market.industry.collect",
        description="Collect industry reports from consulting firms and investment banks.",
    )
    parser.add_argument(
        "--sector",
        type=str,
        default="all",
        help="Target sector (e.g. Technology, Healthcare). Default: all",
    )
    parser.add_argument(
        "--ticker",
        type=str,
        default=None,
        help="Target ticker symbol for sector lookup (e.g. AAPL)",
    )
    parser.add_argument(
        "--source",
        type=str,
        default=None,
        help=(
            "Specific source to run "
            "(mckinsey, bcg, deloitte, pwc, bain, accenture, ey, kpmg, "
            "goldman, morgan_stanley, jpmorgan)"
        ),
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=None,
        help="Output directory for reports. Default: data/raw/industry_reports",
    )
    return parser


def main() -> int:
    """CLI entry point for the industry report collector.

    Returns
    -------
    int
        Exit code (0 for success, 1 for failure).
    """
    parser = build_parser()
    args = parser.parse_args()

    logger.info(
        "Industry collector CLI started",
        sector=args.sector,
        ticker=args.ticker,
        source=args.source,
    )

    collector = IndustryCollector(
        sector=args.sector,
        ticker=args.ticker,
        source=args.source,
        output_dir=args.output_dir,
    )

    try:
        stats = asyncio.run(collector.collect())
    except KeyboardInterrupt:
        logger.info("Collection interrupted by user")
        return 1
    except Exception as e:
        logger.error("Collection failed", error=str(e), exc_info=True)
        return 1

    # Print summary
    _print_summary(stats)

    return 0 if stats.failure_count == 0 else 1


def _print_summary(stats: CollectionStats) -> None:
    """Print a human-readable summary of collection results.

    Parameters
    ----------
    stats : CollectionStats
        The collection statistics to summarize.
    """
    logger.info(
        "Collection summary",
        total_sources=stats.total_sources,
        success=stats.success_count,
        failed=stats.failure_count,
        total_reports=stats.total_reports,
        duration=f"{stats.duration_seconds:.1f}s",
    )

    for result in stats.results:
        if result.success:
            logger.info(
                "Source result",
                source=result.source,
                status="OK",
                reports=result.report_count,
                duration=f"{result.duration_seconds:.1f}s",
            )
        else:
            logger.warning(
                "Source result",
                source=result.source,
                status="FAILED",
                error=result.error_message,
                duration=f"{result.duration_seconds:.1f}s",
            )


# =============================================================================
# Module exports
# =============================================================================

__all__ = [
    "DEFAULT_OUTPUT_SUBDIR",
    "CollectionResult",
    "CollectionStats",
    "IndustryCollector",
    "build_parser",
    "main",
]
