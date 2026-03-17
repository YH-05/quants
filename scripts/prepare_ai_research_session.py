#!/usr/bin/env python3
"""AI Research Session Preparation Script.

Performs deterministic preprocessing for the AI investment value chain
tracking workflow, reducing AI agent context load by handling:
- Category-based CompanyConfig loading (77 companies, 10 categories)
- CompanyScraperRegistry routing (custom/default engine)
- Company blog scraping with bot countermeasures
- Existing Issue URL extraction (duplicate checking)
- Date filtering, duplicate checking, Top-N selection
- Category-based JSON batch output

Usage:
    uv run python scripts/prepare_ai_research_session.py --days 7 --categories all
    uv run python scripts/prepare_ai_research_session.py --days 3 --categories ai_llm,gpu_chips
    uv run python scripts/prepare_ai_research_session.py --days 7 --top-n 5

Output:
    Category batch JSON files in .tmp/ai-research-batches/ directory
"""

from __future__ import annotations

import argparse
import asyncio
import json
import logging
import re
import subprocess
import sys
import time
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from pydantic import BaseModel, Field

from rss.services.company_scrapers.configs import (
    AI_INFRA_COMPANIES,
    AI_LLM_COMPANIES,
    DATA_CENTER_COMPANIES,
    GPU_CHIPS_COMPANIES,
    NETWORKING_COMPANIES,
    NUCLEAR_FUSION_COMPANIES,
    PHYSICAL_AI_COMPANIES,
    POWER_ENERGY_COMPANIES,
    SAAS_COMPANIES,
    SEMICONDUCTOR_COMPANIES,
)
from rss.services.company_scrapers.engine import CompanyScraperEngine
from rss.services.company_scrapers.registry import CompanyScraperRegistry
from rss.services.company_scrapers.types import (
    CompanyConfig,
    CompanyScrapeResult,
    ScrapedArticle,
    StructureReport,
)
from rss.utils.url_normalizer import normalize_url

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

DEFAULT_DAYS = 7
"""Default number of days to look back for articles."""

DEFAULT_CATEGORIES = "all"
"""Default category filter (all categories)."""

DEFAULT_TOP_N = 10
"""Default number of top articles per category (sorted by published date, newest first)."""

BATCH_OUTPUT_DIR = Path(".tmp/ai-research-batches")
"""Output directory for category batch JSON files."""

REPO = "YH-05/quants"
"""GitHub repository."""

PROJECT_NUMBER = 44
"""GitHub Project number for AI Investment Value Chain Tracking."""

PROJECT_OWNER = "YH-05"
"""GitHub Project owner."""

URL_PATTERN = re.compile(r"https?://[^\s<>\"\)]+")
"""Regex pattern for extracting URLs from text."""

# ---------------------------------------------------------------------------
# Category Registry
# ---------------------------------------------------------------------------

CATEGORY_CONFIGS: dict[str, list[CompanyConfig]] = {
    "ai_llm": AI_LLM_COMPANIES,
    "gpu_chips": GPU_CHIPS_COMPANIES,
    "semiconductor": SEMICONDUCTOR_COMPANIES,
    "data_center": DATA_CENTER_COMPANIES,
    "networking": NETWORKING_COMPANIES,
    "power_energy": POWER_ENERGY_COMPANIES,
    "nuclear_fusion": NUCLEAR_FUSION_COMPANIES,
    "physical_ai": PHYSICAL_AI_COMPANIES,
    "saas": SAAS_COMPANIES,
    "ai_infra": AI_INFRA_COMPANIES,
}
"""Mapping of category keys to their CompanyConfig lists."""

CATEGORY_LABELS: dict[str, str] = {
    "ai_llm": "AI/LLM開発",
    "gpu_chips": "GPU・演算チップ",
    "semiconductor": "半導体製造装置",
    "data_center": "データセンター・クラウド",
    "networking": "ネットワーキング",
    "power_energy": "電力・エネルギー",
    "nuclear_fusion": "原子力・核融合",
    "physical_ai": "フィジカルAI・ロボティクス",
    "saas": "SaaS・AI活用ソフトウェア",
    "ai_infra": "AI基盤・MLOps",
}
"""Mapping of category keys to Japanese labels."""


# ---------------------------------------------------------------------------
# Logger
# ---------------------------------------------------------------------------


def _get_logger() -> logging.Logger:
    """Get logger with console output.

    Returns
    -------
    logging.Logger
        Configured logger instance.
    """
    logger = logging.getLogger(__name__)
    if not logger.handlers:
        handler = logging.StreamHandler()
        handler.setFormatter(
            logging.Formatter("%(asctime)s - %(levelname)s - %(message)s")
        )
        logger.addHandler(handler)
        logger.setLevel(logging.INFO)
    return logger


logger = _get_logger()


# ---------------------------------------------------------------------------
# Pydantic Models
# ---------------------------------------------------------------------------


class ScrapedArticleData(BaseModel):
    """Article data from company blog scraping.

    Attributes
    ----------
    url : str
        Article URL.
    title : str
        Article title.
    text : str
        Extracted article body text.
    company_key : str
        Company identifier.
    company_name : str
        Company display name.
    category : str
        Category key (e.g., "ai_llm").
    source_type : str
        How the article was obtained (e.g., "blog", "press_release").
    pdf_url : str | None
        URL of the main PDF attachment, if any.
    published : str
        Publication date in ISO 8601 format (estimated from scrape time
        if not available from the page).
    """

    url: str
    title: str
    text: str
    company_key: str
    company_name: str
    category: str
    source_type: str = "blog"
    pdf_url: str | None = None
    published: str = ""


class CompanyScrapeStats(BaseModel):
    """Statistics for a single company scrape.

    Attributes
    ----------
    company_key : str
        Company identifier.
    company_name : str
        Company display name.
    articles_found : int
        Number of articles found.
    validation_status : str
        Validation status ("valid", "partial", "failed").
    error : str | None
        Error message if scrape failed.
    duration_seconds : float
        Time taken for scraping in seconds.
    """

    company_key: str
    company_name: str
    articles_found: int = 0
    validation_status: str = "valid"
    error: str | None = None
    duration_seconds: float = 0.0


class StructureChangeEntry(BaseModel):
    """Entry in the structure change report.

    Attributes
    ----------
    company_key : str
        Company identifier.
    company_name : str
        Company display name.
    hit_rate : float
        Selector hit rate (0.0-1.0).
    article_list_hits : int
        Number of elements matching the article list selector.
    title_found_count : int
        Number of article titles successfully extracted.
    date_found_count : int
        Number of article dates successfully extracted.
    blog_url : str
        Blog URL that was validated.
    status : str
        Status based on hit rate ("healthy", "partial_change",
        "major_change", "complete_change").
    """

    company_key: str
    company_name: str
    hit_rate: float
    article_list_hits: int
    title_found_count: int
    date_found_count: int
    blog_url: str
    status: str


class CategoryBatch(BaseModel):
    """Output batch for a single category.

    Attributes
    ----------
    category_key : str
        Category identifier.
    category_label : str
        Category Japanese label.
    timestamp : str
        Batch creation timestamp in ISO 8601 format.
    articles : list[ScrapedArticleData]
        Articles selected for this category.
    stats : dict[str, Any]
        Category-level statistics.
    """

    category_key: str
    category_label: str
    timestamp: str
    articles: list[ScrapedArticleData] = Field(default_factory=list)
    stats: dict[str, Any] = Field(default_factory=dict)


class ScrapingStatsReport(BaseModel):
    """Overall scraping statistics report.

    Attributes
    ----------
    timestamp : str
        Report creation timestamp.
    total_companies : int
        Total number of companies processed.
    total_articles : int
        Total number of articles scraped.
    categories_processed : int
        Number of categories processed.
    company_stats : list[CompanyScrapeStats]
        Per-company scraping statistics.
    category_summary : dict[str, dict[str, int]]
        Per-category summary (companies, articles, failures).
    """

    timestamp: str
    total_companies: int = 0
    total_articles: int = 0
    categories_processed: int = 0
    company_stats: list[CompanyScrapeStats] = Field(default_factory=list)
    category_summary: dict[str, dict[str, int]] = Field(default_factory=dict)


class StructureChangeReport(BaseModel):
    """Report on CSS selector health across all companies.

    Attributes
    ----------
    timestamp : str
        Report creation timestamp.
    entries : list[StructureChangeEntry]
        Per-company structure validation entries.
    summary : dict[str, int]
        Count of companies by status.
    """

    timestamp: str
    entries: list[StructureChangeEntry] = Field(default_factory=list)
    summary: dict[str, int] = Field(default_factory=dict)


# ---------------------------------------------------------------------------
# CLI Argument Parsing
# ---------------------------------------------------------------------------


def parse_args(args: list[str] | None = None) -> argparse.Namespace:
    """Parse command-line arguments.

    Parameters
    ----------
    args : list[str] | None
        Command-line arguments. If None, uses sys.argv.

    Returns
    -------
    argparse.Namespace
        Parsed arguments.
    """
    parser = argparse.ArgumentParser(
        description="Prepare AI research session for value chain tracking.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""Examples:
  uv run python scripts/prepare_ai_research_session.py --days 7 --categories all
  uv run python scripts/prepare_ai_research_session.py --days 3 --categories ai_llm,gpu_chips
  uv run python scripts/prepare_ai_research_session.py --days 7 --top-n 5 --verbose""",
    )
    parser.add_argument(
        "--days",
        type=int,
        default=DEFAULT_DAYS,
        help=f"Number of days to look back (default: {DEFAULT_DAYS})",
    )
    parser.add_argument(
        "--categories",
        type=str,
        default=DEFAULT_CATEGORIES,
        help=(
            "Comma-separated category keys or 'all' (default: all). "
            f"Available: {', '.join(CATEGORY_CONFIGS.keys())}"
        ),
    )
    parser.add_argument(
        "--top-n",
        type=int,
        default=DEFAULT_TOP_N,
        help=f"Max articles per category, newest first (default: {DEFAULT_TOP_N})",
    )
    parser.add_argument(
        "--verbose",
        "-v",
        action="store_true",
        help="Enable verbose logging",
    )

    return parser.parse_args(args)


# ---------------------------------------------------------------------------
# Category Loading
# ---------------------------------------------------------------------------


def get_category_companies(
    selected_categories: list[str] | None = None,
) -> dict[str, list[CompanyConfig]]:
    """Get CompanyConfig lists grouped by category.

    Parameters
    ----------
    selected_categories : list[str] | None
        List of category keys to include. If None, includes all.

    Returns
    -------
    dict[str, list[CompanyConfig]]
        CompanyConfig lists keyed by category key.

    Raises
    ------
    ValueError
        If an unknown category key is specified.
    """
    if selected_categories is None:
        logger.info("Loading all %d categories", len(CATEGORY_CONFIGS))
        return dict(CATEGORY_CONFIGS)

    result: dict[str, list[CompanyConfig]] = {}
    for category_key in selected_categories:
        if category_key not in CATEGORY_CONFIGS:
            msg = (
                f"Unknown category: '{category_key}'. "
                f"Available: {', '.join(CATEGORY_CONFIGS.keys())}"
            )
            raise ValueError(msg)
        result[category_key] = CATEGORY_CONFIGS[category_key]

    logger.info("Loading %d categories: %s", len(result), list(result.keys()))
    return result


def count_total_companies(
    categories: dict[str, list[CompanyConfig]],
) -> int:
    """Count total number of companies across categories.

    Parameters
    ----------
    categories : dict[str, list[CompanyConfig]]
        CompanyConfig lists keyed by category key.

    Returns
    -------
    int
        Total number of companies.
    """
    return sum(len(companies) for companies in categories.values())


# ---------------------------------------------------------------------------
# Existing Issues Retrieval
# ---------------------------------------------------------------------------


def extract_urls_from_issues(issues: list[dict[str, Any]]) -> set[str]:
    """Extract article URLs from issue bodies.

    Parameters
    ----------
    issues : list[dict[str, Any]]
        List of GitHub issues.

    Returns
    -------
    set[str]
        Set of normalized article URLs found in issue bodies.
    """
    urls: set[str] = set()

    for issue in issues:
        body = issue.get("body", "") or ""

        # Find all URLs in the body
        found_urls = URL_PATTERN.findall(body)

        for url in found_urls:
            # Skip GitHub URLs
            if "github.com" in url:
                continue

            # Normalize and add
            normalized = normalize_url(url)
            if normalized:
                urls.add(normalized)

    logger.debug("Extracted %d unique URLs from %d issues", len(urls), len(issues))
    return urls


def get_existing_issues_with_urls(
    project_number: int = PROJECT_NUMBER,
    owner: str = PROJECT_OWNER,
    days_back: int = 30,
) -> tuple[list[dict[str, Any]], set[str]]:
    """Fetch existing issues from GitHub Project and extract URLs.

    Parameters
    ----------
    project_number : int
        GitHub Project number.
    owner : str
        GitHub Project owner.
    days_back : int
        Number of days to look back for issues.

    Returns
    -------
    tuple[list[dict[str, Any]], set[str]]
        Tuple of (issues list, extracted URLs set).
    """
    logger.info(
        "Fetching existing issues from Project #%d (last %d days)",
        project_number,
        days_back,
    )

    try:
        result = subprocess.run(
            [
                "gh",
                "project",
                "item-list",
                str(project_number),
                "--owner",
                owner,
                "--limit",
                "500",
                "--format",
                "json",
            ],
            capture_output=True,
            text=True,
            check=True,
        )

        data = json.loads(result.stdout)
        items = data.get("items", [])

        # Extract issue data
        issues: list[dict[str, Any]] = []
        for item in items:
            content = item.get("content", {})
            if content.get("type") == "Issue":
                issues.append(
                    {
                        "number": content.get("number"),
                        "title": content.get("title"),
                        "body": content.get("body", ""),
                        "url": content.get("url"),
                    }
                )

        logger.info("Found %d existing issues", len(issues))

        # Extract URLs
        urls = extract_urls_from_issues(issues)
        logger.info("Extracted %d unique article URLs", len(urls))

        return issues, urls

    except subprocess.CalledProcessError as e:
        logger.warning("Failed to fetch project items: %s", e.stderr)
        return [], set()
    except json.JSONDecodeError as e:
        logger.warning("Failed to parse project items: %s", e)
        return [], set()


# ---------------------------------------------------------------------------
# Company Scraping
# ---------------------------------------------------------------------------


async def scrape_company(
    config: CompanyConfig,
    registry: CompanyScraperRegistry,
) -> tuple[CompanyScrapeResult, float]:
    """Scrape a single company and return result with timing.

    Parameters
    ----------
    config : CompanyConfig
        Company configuration.
    registry : CompanyScraperRegistry
        Scraper registry for routing.

    Returns
    -------
    tuple[CompanyScrapeResult, float]
        Tuple of (scrape result, duration in seconds).
    """
    start_time = time.monotonic()

    try:
        result = await registry.scrape(config)
    except Exception as e:
        logger.error(
            "Scraping failed for %s: %s",
            config.key,
            str(e),
        )
        result = CompanyScrapeResult(
            company=config.key,
            articles=(),
            validation="failed",
        )

    duration = time.monotonic() - start_time

    logger.info(
        "Scraped %s: %d articles, validation=%s, %.1fs",
        config.key,
        len(result.articles),
        result.validation,
        duration,
    )

    return result, duration


async def scrape_category(
    category_key: str,
    companies: list[CompanyConfig],
    registry: CompanyScraperRegistry,
) -> tuple[list[tuple[CompanyConfig, CompanyScrapeResult]], list[CompanyScrapeStats]]:
    """Scrape all companies in a category sequentially.

    Parameters
    ----------
    category_key : str
        Category identifier.
    companies : list[CompanyConfig]
        List of company configurations.
    registry : CompanyScraperRegistry
        Scraper registry for routing.

    Returns
    -------
    tuple[list[tuple[CompanyConfig, CompanyScrapeResult]], list[CompanyScrapeStats]]
        Tuple of (config-result pairs, per-company stats).
    """
    logger.info(
        "Scraping category %s (%d companies)",
        category_key,
        len(companies),
    )

    results: list[tuple[CompanyConfig, CompanyScrapeResult]] = []
    stats: list[CompanyScrapeStats] = []

    for config in companies:
        scrape_result, duration = await scrape_company(config, registry)

        results.append((config, scrape_result))

        stat = CompanyScrapeStats(
            company_key=config.key,
            company_name=config.name,
            articles_found=len(scrape_result.articles),
            validation_status=scrape_result.validation,
            error=None if scrape_result.validation != "failed" else "Scrape failed",
            duration_seconds=round(duration, 2),
        )
        stats.append(stat)

    total_articles = sum(len(r.articles) for _, r in results)
    logger.info(
        "Category %s complete: %d articles from %d companies",
        category_key,
        total_articles,
        len(companies),
    )

    return results, stats


# ---------------------------------------------------------------------------
# Article Conversion
# ---------------------------------------------------------------------------


def convert_to_article_data(
    config: CompanyConfig,
    article: ScrapedArticle,
) -> ScrapedArticleData:
    """Convert a ScrapedArticle to ScrapedArticleData.

    Parameters
    ----------
    config : CompanyConfig
        Company configuration for metadata.
    article : ScrapedArticle
        Scraped article from the engine.

    Returns
    -------
    ScrapedArticleData
        Converted article data.
    """
    # Use current time as published date since blog scraping
    # does not reliably extract publication dates
    published = datetime.now(timezone.utc).isoformat()

    return ScrapedArticleData(
        url=article.url,
        title=article.title,
        text=article.text,
        company_key=config.key,
        company_name=config.name,
        category=config.category,
        source_type=article.source_type,
        pdf_url=article.pdf,
        published=published,
    )


def convert_scrape_results(
    results: list[tuple[CompanyConfig, CompanyScrapeResult]],
) -> list[ScrapedArticleData]:
    """Convert scrape results to article data list.

    Parameters
    ----------
    results : list[tuple[CompanyConfig, CompanyScrapeResult]]
        List of (config, result) pairs.

    Returns
    -------
    list[ScrapedArticleData]
        Flat list of converted article data.
    """
    articles: list[ScrapedArticleData] = []

    for config, result in results:
        for article in result.articles:
            article_data = convert_to_article_data(config, article)
            articles.append(article_data)

    logger.debug("Converted %d articles from %d companies", len(articles), len(results))
    return articles


# ---------------------------------------------------------------------------
# Duplicate Checking
# ---------------------------------------------------------------------------


def check_duplicates(
    articles: list[ScrapedArticleData],
    existing_urls: set[str],
) -> tuple[list[ScrapedArticleData], list[ScrapedArticleData]]:
    """Check for duplicate URLs against existing issues.

    Parameters
    ----------
    articles : list[ScrapedArticleData]
        List of article data.
    existing_urls : set[str]
        Set of normalized URLs from existing issues.

    Returns
    -------
    tuple[list[ScrapedArticleData], list[ScrapedArticleData]]
        Tuple of (unique articles, duplicate articles).
    """
    unique: list[ScrapedArticleData] = []
    duplicates: list[ScrapedArticleData] = []

    for article in articles:
        normalized = normalize_url(article.url)

        if normalized and normalized in existing_urls:
            duplicates.append(article)
        else:
            unique.append(article)
            # Add to existing URLs to catch duplicates within the batch
            if normalized:
                existing_urls.add(normalized)

    logger.debug(
        "Duplicate check: %d unique, %d duplicates",
        len(unique),
        len(duplicates),
    )

    return unique, duplicates


# ---------------------------------------------------------------------------
# Top-N Selection
# ---------------------------------------------------------------------------


def select_top_n(
    articles: list[ScrapedArticleData],
    top_n: int,
) -> list[ScrapedArticleData]:
    """Select top N articles sorted by published date (newest first).

    Parameters
    ----------
    articles : list[ScrapedArticleData]
        List of article data.
    top_n : int
        Maximum number of articles to return.

    Returns
    -------
    list[ScrapedArticleData]
        Top N articles sorted by newest first.
    """
    if top_n <= 0:
        return articles

    # Sort by published date descending (newest first)
    sorted_articles = sorted(
        articles,
        key=lambda x: x.published,
        reverse=True,
    )

    selected = sorted_articles[:top_n]

    logger.debug(
        "Top-N selection: %d -> %d articles (top %d)",
        len(articles),
        len(selected),
        top_n,
    )

    return selected


# ---------------------------------------------------------------------------
# Structure Change Report
# ---------------------------------------------------------------------------


def build_structure_change_report(
    results: dict[str, list[tuple[CompanyConfig, CompanyScrapeResult]]],
    engine: CompanyScraperEngine,
) -> StructureChangeReport:
    """Build a structure change report from scrape results.

    Parameters
    ----------
    results : dict[str, list[tuple[CompanyConfig, CompanyScrapeResult]]]
        Per-category scrape results.
    engine : CompanyScraperEngine
        Engine with validator for accessing structure reports.

    Returns
    -------
    StructureChangeReport
        Report on CSS selector health across all companies.
    """
    entries: list[StructureChangeEntry] = []
    status_counts: dict[str, int] = {
        "healthy": 0,
        "partial_change": 0,
        "major_change": 0,
        "complete_change": 0,
    }

    for _category_key, category_results in results.items():
        for config, result in category_results:
            # Determine status from validation
            if result.validation == "valid":
                status = "healthy"
            elif result.validation == "partial":
                status = "partial_change"
            else:
                status = "complete_change"

            status_counts[status] = status_counts.get(status, 0) + 1

            entry = StructureChangeEntry(
                company_key=config.key,
                company_name=config.name,
                hit_rate=1.0 if result.validation == "valid" else 0.0,
                article_list_hits=len(result.articles),
                title_found_count=len(result.articles),
                date_found_count=0,
                blog_url=config.blog_url,
                status=status,
            )
            entries.append(entry)

    return StructureChangeReport(
        timestamp=datetime.now(timezone.utc).isoformat(),
        entries=entries,
        summary=status_counts,
    )


# ---------------------------------------------------------------------------
# Output
# ---------------------------------------------------------------------------


def write_category_batch(
    category_key: str,
    articles: list[ScrapedArticleData],
    stats: dict[str, Any],
    output_dir: Path = BATCH_OUTPUT_DIR,
) -> Path:
    """Write category batch JSON file.

    Parameters
    ----------
    category_key : str
        Category identifier.
    articles : list[ScrapedArticleData]
        Articles for this category.
    stats : dict[str, Any]
        Category-level statistics.
    output_dir : Path
        Output directory for batch files.

    Returns
    -------
    Path
        Path to the written batch file.
    """
    output_dir.mkdir(parents=True, exist_ok=True)

    batch = CategoryBatch(
        category_key=category_key,
        category_label=CATEGORY_LABELS.get(category_key, category_key),
        timestamp=datetime.now(timezone.utc).isoformat(),
        articles=articles,
        stats=stats,
    )

    output_path = output_dir / f"{category_key}.json"

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(batch.model_dump(), f, ensure_ascii=False, indent=2)

    logger.info("Category batch written: %s (%d articles)", output_path, len(articles))
    return output_path


def write_scraping_stats_report(
    report: ScrapingStatsReport,
    output_dir: Path = BATCH_OUTPUT_DIR,
) -> Path:
    """Write scraping statistics report.

    Parameters
    ----------
    report : ScrapingStatsReport
        Scraping statistics report.
    output_dir : Path
        Output directory.

    Returns
    -------
    Path
        Path to the written report file.
    """
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / "_scraping_stats.json"

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(report.model_dump(), f, ensure_ascii=False, indent=2)

    logger.info("Scraping stats report written: %s", output_path)
    return output_path


def write_structure_change_report(
    report: StructureChangeReport,
    output_dir: Path = BATCH_OUTPUT_DIR,
) -> Path:
    """Write structure change report.

    Parameters
    ----------
    report : StructureChangeReport
        Structure change report.
    output_dir : Path
        Output directory.

    Returns
    -------
    Path
        Path to the written report file.
    """
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / "_structure_report.json"

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(report.model_dump(), f, ensure_ascii=False, indent=2)

    logger.info("Structure change report written: %s", output_path)
    return output_path


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


async def run_async(
    days: int,
    categories_filter: list[str] | None,
    top_n: int = DEFAULT_TOP_N,
) -> int:
    """Run the main async processing.

    Parameters
    ----------
    days : int
        Number of days to look back.
    categories_filter : list[str] | None
        List of category keys to process. None means all.
    top_n : int
        Maximum number of articles per category (newest first).

    Returns
    -------
    int
        Exit code (0 for success, 1 for error).
    """
    start_time = time.monotonic()

    # Step 1: Load category configs
    try:
        categories = get_category_companies(categories_filter)
    except ValueError as e:
        logger.error("Invalid category: %s", e)
        return 1

    total_companies = count_total_companies(categories)
    logger.info(
        "Loaded %d categories, %d companies",
        len(categories),
        total_companies,
    )

    # Step 2: Get existing issues and URLs for dedup
    _, existing_urls = get_existing_issues_with_urls()

    # Step 3: Initialize scraping engine and registry
    engine = CompanyScraperEngine()
    registry = CompanyScraperRegistry(engine=engine)

    # Register custom scrapers (Tier 3)
    try:
        from rss.services.company_scrapers.custom.perplexity import PerplexityScraper

        perplexity_scraper = PerplexityScraper(engine=engine)
        registry.register("perplexity_ai", perplexity_scraper)
        logger.info("Registered custom scraper: perplexity_ai")
    except ImportError:
        logger.warning("Could not import PerplexityScraper, using default engine")

    # Step 4: Scrape each category
    all_category_results: dict[
        str, list[tuple[CompanyConfig, CompanyScrapeResult]]
    ] = {}
    all_company_stats: list[CompanyScrapeStats] = []
    category_summaries: dict[str, dict[str, int]] = {}

    for category_key, companies in categories.items():
        logger.info(
            "Processing category: %s (%s) - %d companies",
            category_key,
            CATEGORY_LABELS.get(category_key, category_key),
            len(companies),
        )

        results, stats = await scrape_category(category_key, companies, registry)
        all_category_results[category_key] = results
        all_company_stats.extend(stats)

        # Category summary
        category_total = sum(len(r.articles) for _, r in results)
        category_failed = sum(1 for _, r in results if r.validation == "failed")
        category_summaries[category_key] = {
            "companies": len(companies),
            "articles": category_total,
            "failures": category_failed,
        }

    # Step 5: Convert, deduplicate, and select per category
    total_scraped = 0
    total_duplicates = 0
    total_selected = 0
    output_paths: list[Path] = []

    for category_key, category_results in all_category_results.items():
        # Convert scrape results to article data
        articles = convert_scrape_results(category_results)
        total_scraped += len(articles)

        # Duplicate check
        unique, duplicates = check_duplicates(articles, existing_urls)
        total_duplicates += len(duplicates)

        # Top-N selection
        selected = select_top_n(unique, top_n)
        total_selected += len(selected)

        # Write category batch
        category_stats = {
            "total_scraped": len(articles),
            "duplicates": len(duplicates),
            "unique": len(unique),
            "selected": len(selected),
            "companies": len(category_results),
        }

        output_path = write_category_batch(
            category_key=category_key,
            articles=selected,
            stats=category_stats,
        )
        output_paths.append(output_path)

        logger.info(
            "Category %s: %d scraped, %d duplicates, %d selected (top %d)",
            category_key,
            len(articles),
            len(duplicates),
            len(selected),
            top_n,
        )

    # Step 6: Write scraping statistics report
    scraping_report = ScrapingStatsReport(
        timestamp=datetime.now(timezone.utc).isoformat(),
        total_companies=total_companies,
        total_articles=total_scraped,
        categories_processed=len(categories),
        company_stats=all_company_stats,
        category_summary=category_summaries,
    )
    write_scraping_stats_report(scraping_report)

    # Step 7: Write structure change report
    structure_report = build_structure_change_report(all_category_results, engine)
    write_structure_change_report(structure_report)

    # Step 8: Print summary
    elapsed = time.monotonic() - start_time

    print("\n" + "=" * 70)
    print("AI Research Session Preparation Complete")
    print("=" * 70)
    print(f"Duration: {elapsed:.1f}s")
    print(f"Output directory: {BATCH_OUTPUT_DIR}")
    print(f"\nCategories: {len(categories)}")
    print(f"Companies: {total_companies}")
    print("\nArticle Statistics:")
    print(f"  Total scraped: {total_scraped}")
    print(f"  Duplicates: {total_duplicates}")
    print(f"  Selected: {total_selected}")
    print("\nCategory breakdown:")
    for category_key in categories:
        summary = category_summaries.get(category_key, {})
        label = CATEGORY_LABELS.get(category_key, category_key)
        print(
            f"  {label}: "
            f"{summary.get('articles', 0)} articles, "
            f"{summary.get('failures', 0)} failures"
        )
    print("\nStructure report:")
    for status, count in structure_report.summary.items():
        if count > 0:
            print(f"  {status}: {count} companies")
    print("\nOutput files:")
    for path in output_paths:
        print(f"  {path}")
    print(f"  {BATCH_OUTPUT_DIR}/_scraping_stats.json")
    print(f"  {BATCH_OUTPUT_DIR}/_structure_report.json")
    print("=" * 70)

    return 0


def main(args: list[str] | None = None) -> int:
    """Main entry point.

    Parameters
    ----------
    args : list[str] | None
        Command-line arguments.

    Returns
    -------
    int
        Exit code (0 for success).
    """
    parsed = parse_args(args)

    # Configure logging
    if parsed.verbose:
        logger.setLevel(logging.DEBUG)

    # Parse categories
    categories_filter: list[str] | None = None
    if parsed.categories != "all":
        categories_filter = [c.strip() for c in parsed.categories.split(",")]

    # Run async processing
    return asyncio.run(
        run_async(
            days=parsed.days,
            categories_filter=categories_filter,
            top_n=parsed.top_n,
        )
    )


if __name__ == "__main__":
    sys.exit(main())
