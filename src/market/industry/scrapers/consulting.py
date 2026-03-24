"""Consulting firm report scrapers.

This module provides scrapers for extracting published insights and reports
from major consulting firms:

- **McKinsey Insights** (``mckinsey.com/featured-insights``)
- **BCG Publications** (``bcg.com/publications``)
- **Deloitte Insights** (``deloitte.com/insights``)
- **PwC Strategy&** (``strategyand.pwc.com``)
- **Bain Insights** (``bain.com/insights``)
- **Accenture Insights** (``accenture.com/us-en/insights``)
- **EY Insights** (``ey.com/en_us/insights``)
- **KPMG Insights** (``kpmg.com/us/en/insights.html``)

Each scraper inherits from ``ConsultingScraper`` (which extends ``BaseScraper``)
and implements site-specific HTML parsing logic. The 2-layer fallback
(curl_cffi -> Playwright) and retry logic are provided by the base classes.

Features
--------
- Article listing page scraping for each site
- Body text extraction via trafilatura + Playwright fallback
- Rate limiting compliance (polite delay between requests)
- JSON output saving to ``data/raw/industry_reports/{source}/``
- Robust date parsing for multiple date formats

Examples
--------
>>> async with McKinseyScraper(sector="Technology") as scraper:
...     result = await scraper.scrape()
...     if result.success:
...         paths = await scraper.save_reports(result.reports)

See Also
--------
market.industry.scrapers.base : BaseScraper abstract base class.
market.etfcom.session : ETFComSession (curl_cffi + Cloudflare bypass reference).
news.extractors.trafilatura : Trafilatura extraction reference.
"""

from __future__ import annotations

import asyncio
import json
import re
from abc import abstractmethod
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from market.industry.scrapers.base import BaseScraper
from market.industry.types import (
    IndustryReport,
    RetryConfig,
    ScrapingConfig,
    ScrapingResult,
    SourceTier,
)
from utils_core.logging import get_logger

logger = get_logger(__name__)

# =============================================================================
# Default configuration
# =============================================================================

DEFAULT_OUTPUT_BASE: Path = Path("data/raw/industry_reports")
"""Default base directory for saving scraped report JSON files."""


# =============================================================================
# Utility functions
# =============================================================================


def _parse_date(date_str: str) -> datetime | None:
    """Parse a date string into a timezone-aware datetime.

    Supports multiple date formats commonly used on consulting firm websites:

    - ``"January 15, 2026"`` (full month name)
    - ``"Jan 10, 2026"`` (abbreviated month name)
    - ``"2026-01-15"`` (ISO 8601 date)
    - ``"Feb 1, 2026"`` (abbreviated month, single-digit day)

    Parameters
    ----------
    date_str : str
        The date string to parse.

    Returns
    -------
    datetime | None
        A timezone-aware datetime (UTC) if parsing succeeds, or ``None``
        if the string cannot be parsed.

    Examples
    --------
    >>> _parse_date("January 15, 2026")
    datetime.datetime(2026, 1, 15, 0, 0, tzinfo=datetime.timezone.utc)

    >>> _parse_date("2026-01-15")
    datetime.datetime(2026, 1, 15, 0, 0, tzinfo=datetime.timezone.utc)

    >>> _parse_date("not a date") is None
    True
    """
    if not date_str or not date_str.strip():
        return None

    date_str = date_str.strip()

    formats = [
        "%B %d, %Y",  # January 15, 2026
        "%b %d, %Y",  # Jan 15, 2026
        "%Y-%m-%d",  # 2026-01-15
        "%B %d %Y",  # January 15 2026
        "%b %d %Y",  # Jan 15 2026
        "%d %B %Y",  # 15 January 2026
        "%d %b %Y",  # 15 Jan 2026
        "%m/%d/%Y",  # 01/15/2026
    ]

    for fmt in formats:
        try:
            dt = datetime.strptime(date_str, fmt)
            return dt.replace(tzinfo=timezone.utc)
        except ValueError:
            continue

    logger.debug("Failed to parse date string", date_str=date_str)
    return None


def _title_to_slug(title: str, max_length: int = 80) -> str:
    """Convert a title string to a URL-friendly slug.

    Parameters
    ----------
    title : str
        The title to convert.
    max_length : int
        Maximum length of the resulting slug. Defaults to 80.

    Returns
    -------
    str
        A lowercase, hyphen-separated slug.

    Examples
    --------
    >>> _title_to_slug("Semiconductor Outlook 2026")
    'semiconductor-outlook-2026'

    >>> _title_to_slug("AI & Machine Learning: The Future!")
    'ai-machine-learning-the-future'
    """
    slug = title.lower()
    # Remove non-alphanumeric characters (except spaces and hyphens)
    slug = re.sub(r"[^\w\s-]", "", slug)
    # Replace whitespace with hyphens
    slug = re.sub(r"[\s_]+", "-", slug)
    # Remove leading/trailing hyphens
    slug = slug.strip("-")
    # Collapse multiple hyphens
    slug = re.sub(r"-+", "-", slug)
    # Truncate to max_length
    if len(slug) > max_length:
        slug = slug[:max_length].rstrip("-")
    return slug


async def _extract_body_text(url: str, timeout: float = 30.0) -> str | None:
    """Extract article body text using trafilatura.

    Attempts to download and extract the main body text from the given URL
    using trafilatura. Falls back gracefully on failure.

    Parameters
    ----------
    url : str
        The article URL to extract body text from.
    timeout : float
        Request timeout in seconds. Defaults to 30.0.

    Returns
    -------
    str | None
        The extracted body text, or ``None`` if extraction fails.
    """
    try:
        import trafilatura  # type: ignore[import-untyped]

        downloaded = await asyncio.to_thread(
            trafilatura.fetch_url,
            url,
        )

        if downloaded is None:
            logger.debug("trafilatura fetch returned None", url=url)
            return None

        text: str | None = trafilatura.extract(downloaded)

        if text and len(text) > 100:
            logger.debug(
                "Body text extracted successfully",
                url=url,
                text_length=len(text),
            )
            return text

        logger.debug(
            "Extracted text too short or empty",
            url=url,
            text_length=len(text) if text else 0,
        )
        return None

    except ImportError:
        logger.warning("trafilatura not installed. Install with: uv add trafilatura")
        return None

    except Exception as e:
        logger.warning(
            "Body text extraction failed",
            url=url,
            error=str(e),
        )
        return None


def _parse_html_with_bs4(html: str) -> Any:
    """Parse HTML using BeautifulSoup 4.

    Parameters
    ----------
    html : str
        Raw HTML content.

    Returns
    -------
    Any
        A BeautifulSoup object.

    Raises
    ------
    ImportError
        If beautifulsoup4 is not installed.
    """
    try:
        from bs4 import BeautifulSoup  # type: ignore[import-untyped]
    except ImportError as e:
        raise ImportError(
            "beautifulsoup4 is not installed. Install with: uv add beautifulsoup4"
        ) from e

    return BeautifulSoup(html, "html.parser")


# =============================================================================
# ConsultingScraper Base Class
# =============================================================================


class ConsultingScraper(BaseScraper):
    """Base class for consulting firm report scrapers.

    Extends ``BaseScraper`` with consulting-specific functionality:

    - Sector filtering
    - Report saving to JSON files
    - Body text extraction via trafilatura
    - Common scrape() workflow

    Subclasses must implement ``parse_html()`` for their site-specific
    HTML structure.

    Parameters
    ----------
    source_name : str
        Human-readable name of the consulting firm.
    base_url : str
        Base URL of the insights/publications page.
    source_key : str
        Short lowercase key for the source (used in file paths).
    sector : str
        Target sector to filter reports. Defaults to ``"all"``.
    output_dir : Path | None
        Output directory for saved reports. If ``None``, uses
        ``data/raw/industry_reports/{source_key}/``.
    config : ScrapingConfig | None
        Scraping configuration. If ``None``, defaults are used.
    retry_config : RetryConfig | None
        Retry configuration. If ``None``, defaults are used.
    """

    def __init__(
        self,
        source_name: str,
        base_url: str,
        source_key: str,
        sector: str = "all",
        output_dir: Path | None = None,
        config: ScrapingConfig | None = None,
        retry_config: RetryConfig | None = None,
    ) -> None:
        super().__init__(
            source_name=source_name,
            base_url=base_url,
            config=config,
            retry_config=retry_config,
        )
        self.sector: str = sector
        self.source_key: str = source_key
        self.output_dir: Path = output_dir or (DEFAULT_OUTPUT_BASE / source_key)

        logger.info(
            "ConsultingScraper initialized",
            source_name=source_name,
            sector=sector,
            output_dir=str(self.output_dir),
        )

    async def scrape(self) -> ScrapingResult:
        """Execute the scraping operation for this consulting source.

        Fetches the article listing page using the 2-layer fallback
        strategy (curl_cffi -> Playwright), parses the HTML to extract
        report metadata, and returns a ``ScrapingResult``.

        Returns
        -------
        ScrapingResult
            The result of the scraping operation, containing extracted
            reports on success or an error message on failure.

        Examples
        --------
        >>> async with McKinseyScraper() as scraper:
        ...     result = await scraper.scrape()
        ...     if result.success:
        ...         print(f"Found {len(result.reports)} reports")
        """
        try:
            logger.info(
                "Starting scrape",
                source=self.source_name,
                url=self.base_url,
            )

            html = await self._fetch_html_with_retry(self.base_url)
            reports = await self.parse_html(html)

            logger.info(
                "Scrape completed successfully",
                source=self.source_name,
                report_count=len(reports),
            )

            return ScrapingResult(
                success=True,
                source=self.source_name,
                url=self.base_url,
                reports=reports,
            )

        except Exception as e:
            logger.error(
                "Scrape failed",
                source=self.source_name,
                error=str(e),
                exc_info=True,
            )
            return ScrapingResult(
                success=False,
                source=self.source_name,
                url=self.base_url,
                reports=[],
                error_message=str(e),
            )

    @abstractmethod
    async def parse_html(self, html: str) -> list[IndustryReport]:
        """Parse HTML content and extract industry reports.

        Subclasses must implement this method for their site-specific
        HTML structure.

        Parameters
        ----------
        html : str
            Raw HTML content from the article listing page.

        Returns
        -------
        list[IndustryReport]
            List of extracted industry report records.
        """

    async def extract_body(self, url: str) -> str | None:
        """Extract article body text from the given URL.

        Uses trafilatura for body text extraction with a Playwright
        fallback if trafilatura fails (via the base class's browser
        fallback).

        Parameters
        ----------
        url : str
            The article URL to extract body text from.

        Returns
        -------
        str | None
            The extracted body text, or ``None`` if extraction fails.
        """
        return await _extract_body_text(url, timeout=self.config.timeout)

    async def save_reports(self, reports: list[IndustryReport]) -> list[Path]:
        """Save a list of reports as individual JSON files.

        Each report is saved as a JSON file in the output directory
        with the naming convention:
        ``{date}_{slug}.json`` (e.g. ``2026-01-15_semiconductor-outlook.json``)

        Parameters
        ----------
        reports : list[IndustryReport]
            The reports to save.

        Returns
        -------
        list[Path]
            List of paths to the saved JSON files.
        """
        if not reports:
            return []

        self.output_dir.mkdir(parents=True, exist_ok=True)
        saved_paths: list[Path] = []

        for report in reports:
            date_str = report.published_at.strftime("%Y-%m-%d")
            slug = _title_to_slug(report.title)
            filename = f"{date_str}_{slug}.json"
            filepath = self.output_dir / filename

            data = report.model_dump(mode="json")

            filepath.write_text(
                json.dumps(data, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )

            saved_paths.append(filepath)
            logger.debug(
                "Report saved",
                filepath=str(filepath),
                title=report.title,
            )

        logger.info(
            "Reports saved",
            source=self.source_name,
            count=len(saved_paths),
            output_dir=str(self.output_dir),
        )

        return saved_paths


# =============================================================================
# McKinsey Scraper
# =============================================================================


class McKinseyScraper(ConsultingScraper):
    """Scraper for McKinsey Insights (mckinsey.com/featured-insights).

    Extracts articles from McKinsey's featured insights page, parsing
    article titles, URLs, publication dates, and summaries.

    Parameters
    ----------
    sector : str
        Target sector to filter reports. Defaults to ``"all"``.
    output_dir : Path | None
        Output directory for saved reports.
    config : ScrapingConfig | None
        Scraping configuration.
    retry_config : RetryConfig | None
        Retry configuration.

    Examples
    --------
    >>> async with McKinseyScraper(sector="Technology") as scraper:
    ...     result = await scraper.scrape()
    """

    def __init__(
        self,
        sector: str = "all",
        output_dir: Path | None = None,
        config: ScrapingConfig | None = None,
        retry_config: RetryConfig | None = None,
    ) -> None:
        super().__init__(
            source_name="McKinsey",
            base_url="https://www.mckinsey.com/featured-insights",
            source_key="mckinsey",
            sector=sector,
            output_dir=output_dir,
            config=config,
            retry_config=retry_config,
        )

    async def parse_html(self, html: str) -> list[IndustryReport]:
        """Parse McKinsey Insights HTML and extract reports.

        Looks for article items with the following CSS selectors:

        - Article container: ``[data-component="article-item"]`` or
          ``.article-item``
        - Title: ``.article-item__title`` or ``h3``
        - Link: ``.article-item__link`` or ``a[href]``
        - Date: ``.article-item__date``
        - Summary: ``.article-item__description``

        Parameters
        ----------
        html : str
            Raw HTML from McKinsey's insights page.

        Returns
        -------
        list[IndustryReport]
            List of extracted McKinsey reports.
        """
        soup = _parse_html_with_bs4(html)
        reports: list[IndustryReport] = []

        # Find article items
        articles = soup.find_all(
            ["div", "article"],
            attrs={
                "data-component": "article-item",
            },
        )
        if not articles:
            articles = soup.find_all(
                ["div", "article"],
                class_=re.compile(r"article-item"),
            )

        for article in articles:
            try:
                # Extract title
                title_tag = article.find(
                    class_=re.compile(r"article-item__title")
                ) or article.find(["h2", "h3", "h4"])
                if not title_tag:
                    continue
                title = title_tag.get_text(strip=True)

                # Extract URL
                link_tag = article.find(
                    "a", class_=re.compile(r"article-item__link")
                ) or article.find("a", href=True)
                if not link_tag or not link_tag.get("href"):
                    continue
                href = link_tag["href"]
                url = (
                    href
                    if href.startswith("http")
                    else f"https://www.mckinsey.com{href}"
                )

                # Extract date
                date_tag = article.find(class_=re.compile(r"article-item__date"))
                published_at = (
                    _parse_date(date_tag.get_text(strip=True)) if date_tag else None
                )
                if published_at is None:
                    published_at = datetime.now(tz=timezone.utc)

                # Extract summary
                summary_tag = article.find(
                    class_=re.compile(r"article-item__description")
                )
                summary = summary_tag.get_text(strip=True) if summary_tag else None

                reports.append(
                    IndustryReport(
                        source="McKinsey",
                        title=title,
                        url=url,
                        published_at=published_at,
                        sector=self.sector,
                        summary=summary,
                        tier=SourceTier.SCRAPING,
                    )
                )

            except Exception as e:
                logger.warning(
                    "Failed to parse McKinsey article",
                    error=str(e),
                )
                continue

        logger.debug(
            "McKinsey HTML parsed",
            article_count=len(reports),
        )

        return reports


# =============================================================================
# BCG Scraper
# =============================================================================


class BCGScraper(ConsultingScraper):
    """Scraper for BCG Publications (bcg.com/publications).

    Extracts articles from BCG's publications page, parsing article
    titles, URLs, publication dates, and summaries.

    Parameters
    ----------
    sector : str
        Target sector to filter reports. Defaults to ``"all"``.
    output_dir : Path | None
        Output directory for saved reports.
    config : ScrapingConfig | None
        Scraping configuration.
    retry_config : RetryConfig | None
        Retry configuration.

    Examples
    --------
    >>> async with BCGScraper() as scraper:
    ...     result = await scraper.scrape()
    """

    def __init__(
        self,
        sector: str = "all",
        output_dir: Path | None = None,
        config: ScrapingConfig | None = None,
        retry_config: RetryConfig | None = None,
    ) -> None:
        super().__init__(
            source_name="BCG",
            base_url="https://www.bcg.com/publications",
            source_key="bcg",
            sector=sector,
            output_dir=output_dir,
            config=config,
            retry_config=retry_config,
        )

    async def parse_html(self, html: str) -> list[IndustryReport]:
        """Parse BCG Publications HTML and extract reports.

        Looks for publication cards with the following CSS selectors:

        - Article container: ``article.publication-card``
        - Title: ``.publication-card__title`` or ``h2``
        - Link: ``.publication-card__link`` or ``a[href]``
        - Date: ``time.publication-card__date`` (with ``datetime`` attr)
        - Summary: ``.publication-card__summary``

        Parameters
        ----------
        html : str
            Raw HTML from BCG's publications page.

        Returns
        -------
        list[IndustryReport]
            List of extracted BCG reports.
        """
        soup = _parse_html_with_bs4(html)
        reports: list[IndustryReport] = []

        articles = soup.find_all(
            ["article", "div"],
            class_=re.compile(r"publication-card"),
        )

        for article in articles:
            try:
                # Extract title
                title_tag = article.find(
                    class_=re.compile(r"publication-card__title")
                ) or article.find(["h2", "h3", "h4"])
                if not title_tag:
                    continue
                title = title_tag.get_text(strip=True)

                # Extract URL
                link_tag = article.find(
                    "a", class_=re.compile(r"publication-card__link")
                ) or article.find("a", href=True)
                if not link_tag or not link_tag.get("href"):
                    continue
                href = link_tag["href"]
                url = href if href.startswith("http") else f"https://www.bcg.com{href}"

                # Extract date - prefer datetime attribute
                date_tag = article.find(
                    "time", class_=re.compile(r"publication-card__date")
                ) or article.find("time")
                published_at = None
                if date_tag:
                    dt_attr = date_tag.get("datetime")
                    if dt_attr:
                        published_at = _parse_date(dt_attr)
                    if published_at is None:
                        published_at = _parse_date(date_tag.get_text(strip=True))
                if published_at is None:
                    published_at = datetime.now(tz=timezone.utc)

                # Extract summary
                summary_tag = article.find(
                    class_=re.compile(r"publication-card__summary")
                )
                summary = summary_tag.get_text(strip=True) if summary_tag else None

                reports.append(
                    IndustryReport(
                        source="BCG",
                        title=title,
                        url=url,
                        published_at=published_at,
                        sector=self.sector,
                        summary=summary,
                        tier=SourceTier.SCRAPING,
                    )
                )

            except Exception as e:
                logger.warning(
                    "Failed to parse BCG article",
                    error=str(e),
                )
                continue

        logger.debug(
            "BCG HTML parsed",
            article_count=len(reports),
        )

        return reports


# =============================================================================
# Deloitte Scraper
# =============================================================================


class DeloitteScraper(ConsultingScraper):
    """Scraper for Deloitte Insights (deloitte.com/insights).

    Extracts articles from Deloitte's insights page, parsing article
    titles, URLs, publication dates, and descriptions.

    Parameters
    ----------
    sector : str
        Target sector to filter reports. Defaults to ``"all"``.
    output_dir : Path | None
        Output directory for saved reports.
    config : ScrapingConfig | None
        Scraping configuration.
    retry_config : RetryConfig | None
        Retry configuration.

    Examples
    --------
    >>> async with DeloitteScraper() as scraper:
    ...     result = await scraper.scrape()
    """

    def __init__(
        self,
        sector: str = "all",
        output_dir: Path | None = None,
        config: ScrapingConfig | None = None,
        retry_config: RetryConfig | None = None,
    ) -> None:
        super().__init__(
            source_name="Deloitte",
            base_url="https://www2.deloitte.com/insights",
            source_key="deloitte",
            sector=sector,
            output_dir=output_dir,
            config=config,
            retry_config=retry_config,
        )

    async def parse_html(self, html: str) -> list[IndustryReport]:
        """Parse Deloitte Insights HTML and extract reports.

        Looks for promo cards with the following CSS selectors:

        - Card container: ``.promo-card`` or ``[data-component="promo-card"]``
        - Title: ``.promo-card__title`` or ``h3``
        - Link: ``.promo-card__link`` or ``a[href]``
        - Date: ``.promo-card__date``
        - Summary: ``.promo-card__description``

        Parameters
        ----------
        html : str
            Raw HTML from Deloitte's insights page.

        Returns
        -------
        list[IndustryReport]
            List of extracted Deloitte reports.
        """
        soup = _parse_html_with_bs4(html)
        reports: list[IndustryReport] = []

        articles = soup.find_all(
            ["div", "article"],
            attrs={"data-component": "promo-card"},
        )
        if not articles:
            articles = soup.find_all(
                ["div", "article"],
                class_=re.compile(r"promo-card"),
            )

        for article in articles:
            try:
                # Extract title
                title_tag = article.find(
                    class_=re.compile(r"promo-card__title")
                ) or article.find(["h2", "h3", "h4"])
                if not title_tag:
                    continue
                title = title_tag.get_text(strip=True)

                # Extract URL
                link_tag = article.find(
                    "a", class_=re.compile(r"promo-card__link")
                ) or article.find("a", href=True)
                if not link_tag or not link_tag.get("href"):
                    continue
                href = link_tag["href"]
                url = (
                    href
                    if href.startswith("http")
                    else f"https://www2.deloitte.com{href}"
                )

                # Extract date
                date_tag = article.find(class_=re.compile(r"promo-card__date"))
                published_at = (
                    _parse_date(date_tag.get_text(strip=True)) if date_tag else None
                )
                if published_at is None:
                    published_at = datetime.now(tz=timezone.utc)

                # Extract summary
                summary_tag = article.find(
                    class_=re.compile(r"promo-card__description")
                )
                summary = summary_tag.get_text(strip=True) if summary_tag else None

                reports.append(
                    IndustryReport(
                        source="Deloitte",
                        title=title,
                        url=url,
                        published_at=published_at,
                        sector=self.sector,
                        summary=summary,
                        tier=SourceTier.SCRAPING,
                    )
                )

            except Exception as e:
                logger.warning(
                    "Failed to parse Deloitte article",
                    error=str(e),
                )
                continue

        logger.debug(
            "Deloitte HTML parsed",
            article_count=len(reports),
        )

        return reports


# =============================================================================
# PwC Scraper
# =============================================================================


class PwCScraper(ConsultingScraper):
    """Scraper for PwC Strategy& (strategyand.pwc.com).

    Extracts articles from PwC's strategy publications page, parsing
    article titles, URLs, publication dates, and excerpts.

    Parameters
    ----------
    sector : str
        Target sector to filter reports. Defaults to ``"all"``.
    output_dir : Path | None
        Output directory for saved reports.
    config : ScrapingConfig | None
        Scraping configuration.
    retry_config : RetryConfig | None
        Retry configuration.

    Examples
    --------
    >>> async with PwCScraper() as scraper:
    ...     result = await scraper.scrape()
    """

    def __init__(
        self,
        sector: str = "all",
        output_dir: Path | None = None,
        config: ScrapingConfig | None = None,
        retry_config: RetryConfig | None = None,
    ) -> None:
        super().__init__(
            source_name="PwC",
            base_url="https://www.strategyand.pwc.com/gx/en/insights.html",
            source_key="pwc",
            sector=sector,
            output_dir=output_dir,
            config=config,
            retry_config=retry_config,
        )

    async def parse_html(self, html: str) -> list[IndustryReport]:
        """Parse PwC Strategy& HTML and extract reports.

        Looks for content cards with the following CSS selectors:

        - Card container: ``.content-card``
        - Title: ``.content-card__title`` or ``h3``
        - Link: ``.content-card__link`` or ``a[href]``
        - Date: ``.content-card__date``
        - Summary: ``.content-card__excerpt``

        Parameters
        ----------
        html : str
            Raw HTML from PwC Strategy& page.

        Returns
        -------
        list[IndustryReport]
            List of extracted PwC reports.
        """
        soup = _parse_html_with_bs4(html)
        reports: list[IndustryReport] = []

        articles = soup.find_all(
            ["div", "article"],
            class_=re.compile(r"content-card"),
        )

        for article in articles:
            try:
                # Extract title
                title_tag = article.find(
                    class_=re.compile(r"content-card__title")
                ) or article.find(["h2", "h3", "h4"])
                if not title_tag:
                    continue
                title = title_tag.get_text(strip=True)

                # Extract URL
                link_tag = article.find(
                    "a", class_=re.compile(r"content-card__link")
                ) or article.find("a", href=True)
                if not link_tag or not link_tag.get("href"):
                    continue
                href = link_tag["href"]
                url = (
                    href
                    if href.startswith("http")
                    else f"https://www.strategyand.pwc.com{href}"
                )

                # Extract date
                date_tag = article.find(class_=re.compile(r"content-card__date"))
                published_at = (
                    _parse_date(date_tag.get_text(strip=True)) if date_tag else None
                )
                if published_at is None:
                    published_at = datetime.now(tz=timezone.utc)

                # Extract summary
                summary_tag = article.find(class_=re.compile(r"content-card__excerpt"))
                summary = summary_tag.get_text(strip=True) if summary_tag else None

                reports.append(
                    IndustryReport(
                        source="PwC",
                        title=title,
                        url=url,
                        published_at=published_at,
                        sector=self.sector,
                        summary=summary,
                        tier=SourceTier.SCRAPING,
                    )
                )

            except Exception as e:
                logger.warning(
                    "Failed to parse PwC article",
                    error=str(e),
                )
                continue

        logger.debug(
            "PwC HTML parsed",
            article_count=len(reports),
        )

        return reports


# =============================================================================
# Bain Scraper
# =============================================================================


class BainScraper(ConsultingScraper):
    """Scraper for Bain Insights (bain.com/insights).

    Extracts articles from Bain's insights page, parsing article
    titles, URLs, publication dates, and descriptions.

    Parameters
    ----------
    sector : str
        Target sector to filter reports. Defaults to ``"all"``.
    output_dir : Path | None
        Output directory for saved reports.
    config : ScrapingConfig | None
        Scraping configuration.
    retry_config : RetryConfig | None
        Retry configuration.

    Examples
    --------
    >>> async with BainScraper() as scraper:
    ...     result = await scraper.scrape()
    """

    def __init__(
        self,
        sector: str = "all",
        output_dir: Path | None = None,
        config: ScrapingConfig | None = None,
        retry_config: RetryConfig | None = None,
    ) -> None:
        super().__init__(
            source_name="Bain",
            base_url="https://www.bain.com/insights/",
            source_key="bain",
            sector=sector,
            output_dir=output_dir,
            config=config,
            retry_config=retry_config,
        )

    async def parse_html(self, html: str) -> list[IndustryReport]:
        """Parse Bain Insights HTML and extract reports.

        Looks for insight cards with the following CSS selectors:

        - Card container: ``div.insight-card`` or
          ``[data-component="insight-card"]``
        - Title: ``.insight-card__title`` or ``h3``
        - Link: ``.insight-card__link`` or ``a[href]``
        - Date: ``.insight-card__date``
        - Description: ``.insight-card__description``

        Parameters
        ----------
        html : str
            Raw HTML from Bain's insights page.

        Returns
        -------
        list[IndustryReport]
            List of extracted Bain reports.
        """
        soup = _parse_html_with_bs4(html)
        reports: list[IndustryReport] = []

        # Find insight cards
        articles = soup.find_all(
            ["div", "article"],
            attrs={"data-component": "insight-card"},
        )
        if not articles:
            articles = soup.find_all(
                ["div", "article"],
                class_=re.compile(r"insight-card"),
            )

        for article in articles:
            try:
                # Extract title
                title_tag = article.find(
                    class_=re.compile(r"insight-card__title")
                ) or article.find(["h2", "h3", "h4"])
                if not title_tag:
                    continue
                title = title_tag.get_text(strip=True)

                # Extract URL
                link_tag = article.find(
                    "a", class_=re.compile(r"insight-card__link")
                ) or article.find("a", href=True)
                if not link_tag or not link_tag.get("href"):
                    continue
                href = link_tag["href"]
                url = href if href.startswith("http") else f"https://www.bain.com{href}"

                # Extract date
                date_tag = article.find(class_=re.compile(r"insight-card__date"))
                published_at = (
                    _parse_date(date_tag.get_text(strip=True)) if date_tag else None
                )
                if published_at is None:
                    published_at = datetime.now(tz=timezone.utc)

                # Extract description
                desc_tag = article.find(class_=re.compile(r"insight-card__description"))
                summary = desc_tag.get_text(strip=True) if desc_tag else None

                reports.append(
                    IndustryReport(
                        source="Bain",
                        title=title,
                        url=url,
                        published_at=published_at,
                        sector=self.sector,
                        summary=summary,
                        tier=SourceTier.SCRAPING,
                    )
                )

            except Exception as e:
                logger.warning(
                    "Failed to parse Bain article",
                    error=str(e),
                )
                continue

        logger.debug(
            "Bain HTML parsed",
            article_count=len(reports),
        )

        return reports


# =============================================================================
# Accenture Scraper
# =============================================================================


class AccentureScraper(ConsultingScraper):
    """Scraper for Accenture Insights (accenture.com/us-en/insights).

    Extracts articles from Accenture's insights page, parsing article
    titles, URLs, publication dates, and descriptions.

    Parameters
    ----------
    sector : str
        Target sector to filter reports. Defaults to ``"all"``.
    output_dir : Path | None
        Output directory for saved reports.
    config : ScrapingConfig | None
        Scraping configuration.
    retry_config : RetryConfig | None
        Retry configuration.

    Examples
    --------
    >>> async with AccentureScraper() as scraper:
    ...     result = await scraper.scrape()
    """

    def __init__(
        self,
        sector: str = "all",
        output_dir: Path | None = None,
        config: ScrapingConfig | None = None,
        retry_config: RetryConfig | None = None,
    ) -> None:
        super().__init__(
            source_name="Accenture",
            base_url="https://www.accenture.com/us-en/insights",
            source_key="accenture",
            sector=sector,
            output_dir=output_dir,
            config=config,
            retry_config=retry_config,
        )

    async def parse_html(self, html: str) -> list[IndustryReport]:
        """Parse Accenture Insights HTML and extract reports.

        Looks for rad-card elements with the following CSS selectors:

        - Card container: ``div.rad-card`` or
          ``[data-component="rad-card"]``
        - Title: ``.rad-card__title`` or ``h3`` / ``h4``
        - Link: ``.rad-card__link`` or ``a[href]``
        - Date: ``.rad-card__date``
        - Description: ``.rad-card__description``

        Parameters
        ----------
        html : str
            Raw HTML from Accenture's insights page.

        Returns
        -------
        list[IndustryReport]
            List of extracted Accenture reports.
        """
        soup = _parse_html_with_bs4(html)
        reports: list[IndustryReport] = []

        # Find rad-card elements
        articles = soup.find_all(
            ["div", "article"],
            attrs={"data-component": "rad-card"},
        )
        if not articles:
            articles = soup.find_all(
                ["div", "article"],
                class_=re.compile(r"rad-card"),
            )

        for article in articles:
            try:
                # Extract title
                title_tag = article.find(
                    class_=re.compile(r"rad-card__title")
                ) or article.find(["h2", "h3", "h4"])
                if not title_tag:
                    continue
                title = title_tag.get_text(strip=True)

                # Extract URL
                link_tag = article.find(
                    "a", class_=re.compile(r"rad-card__link")
                ) or article.find("a", href=True)
                if not link_tag or not link_tag.get("href"):
                    continue
                href = link_tag["href"]
                url = (
                    href
                    if href.startswith("http")
                    else f"https://www.accenture.com{href}"
                )

                # Extract date
                date_tag = article.find(class_=re.compile(r"rad-card__date"))
                published_at = (
                    _parse_date(date_tag.get_text(strip=True)) if date_tag else None
                )
                if published_at is None:
                    published_at = datetime.now(tz=timezone.utc)

                # Extract description
                desc_tag = article.find(class_=re.compile(r"rad-card__description"))
                summary = desc_tag.get_text(strip=True) if desc_tag else None

                reports.append(
                    IndustryReport(
                        source="Accenture",
                        title=title,
                        url=url,
                        published_at=published_at,
                        sector=self.sector,
                        summary=summary,
                        tier=SourceTier.SCRAPING,
                    )
                )

            except Exception as e:
                logger.warning(
                    "Failed to parse Accenture article",
                    error=str(e),
                )
                continue

        logger.debug(
            "Accenture HTML parsed",
            article_count=len(reports),
        )

        return reports


# =============================================================================
# EY Scraper
# =============================================================================


class EYScraper(ConsultingScraper):
    """Scraper for EY Insights (ey.com/en_us/insights).

    Extracts articles from EY's insights page, parsing article
    titles, URLs, publication dates, and descriptions.

    Parameters
    ----------
    sector : str
        Target sector to filter reports. Defaults to ``"all"``.
    output_dir : Path | None
        Output directory for saved reports.
    config : ScrapingConfig | None
        Scraping configuration.
    retry_config : RetryConfig | None
        Retry configuration.

    Examples
    --------
    >>> async with EYScraper() as scraper:
    ...     result = await scraper.scrape()
    """

    def __init__(
        self,
        sector: str = "all",
        output_dir: Path | None = None,
        config: ScrapingConfig | None = None,
        retry_config: RetryConfig | None = None,
    ) -> None:
        super().__init__(
            source_name="EY",
            base_url="https://www.ey.com/en_us/insights",
            source_key="ey",
            sector=sector,
            output_dir=output_dir,
            config=config,
            retry_config=retry_config,
        )

    async def parse_html(self, html: str) -> list[IndustryReport]:
        """Parse EY Insights HTML and extract reports.

        Looks for insight-article elements with the following CSS selectors:

        - Article container: ``article.insight-article`` or
          ``[data-component="insight-article"]``
        - Title: ``.insight-article__title`` or ``h3``
        - Link: ``.insight-article__link`` or ``a[href]``
        - Date: ``.insight-article__date``
        - Description: ``.insight-article__description``

        Parameters
        ----------
        html : str
            Raw HTML from EY's insights page.

        Returns
        -------
        list[IndustryReport]
            List of extracted EY reports.
        """
        soup = _parse_html_with_bs4(html)
        reports: list[IndustryReport] = []

        # Find insight-article elements
        articles = soup.find_all(
            ["div", "article"],
            attrs={"data-component": "insight-article"},
        )
        if not articles:
            articles = soup.find_all(
                ["div", "article"],
                class_=re.compile(r"insight-article"),
            )

        for article in articles:
            try:
                # Extract title
                title_tag = article.find(
                    class_=re.compile(r"insight-article__title")
                ) or article.find(["h2", "h3", "h4"])
                if not title_tag:
                    continue
                title = title_tag.get_text(strip=True)

                # Extract URL
                link_tag = article.find(
                    "a", class_=re.compile(r"insight-article__link")
                ) or article.find("a", href=True)
                if not link_tag or not link_tag.get("href"):
                    continue
                href = link_tag["href"]
                url = href if href.startswith("http") else f"https://www.ey.com{href}"

                # Extract date
                date_tag = article.find(class_=re.compile(r"insight-article__date"))
                published_at = (
                    _parse_date(date_tag.get_text(strip=True)) if date_tag else None
                )
                if published_at is None:
                    published_at = datetime.now(tz=timezone.utc)

                # Extract description
                desc_tag = article.find(
                    class_=re.compile(r"insight-article__description")
                )
                summary = desc_tag.get_text(strip=True) if desc_tag else None

                reports.append(
                    IndustryReport(
                        source="EY",
                        title=title,
                        url=url,
                        published_at=published_at,
                        sector=self.sector,
                        summary=summary,
                        tier=SourceTier.SCRAPING,
                    )
                )

            except Exception as e:
                logger.warning(
                    "Failed to parse EY article",
                    error=str(e),
                )
                continue

        logger.debug(
            "EY HTML parsed",
            article_count=len(reports),
        )

        return reports


# =============================================================================
# KPMG Scraper
# =============================================================================


class KPMGScraper(ConsultingScraper):
    """Scraper for KPMG Insights (kpmg.com/us/en/insights.html).

    Extracts articles from KPMG's insights page, parsing article
    titles, URLs, publication dates, and descriptions.

    Parameters
    ----------
    sector : str
        Target sector to filter reports. Defaults to ``"all"``.
    output_dir : Path | None
        Output directory for saved reports.
    config : ScrapingConfig | None
        Scraping configuration.
    retry_config : RetryConfig | None
        Retry configuration.

    Examples
    --------
    >>> async with KPMGScraper() as scraper:
    ...     result = await scraper.scrape()
    """

    def __init__(
        self,
        sector: str = "all",
        output_dir: Path | None = None,
        config: ScrapingConfig | None = None,
        retry_config: RetryConfig | None = None,
    ) -> None:
        super().__init__(
            source_name="KPMG",
            base_url="https://kpmg.com/us/en/insights.html",
            source_key="kpmg",
            sector=sector,
            output_dir=output_dir,
            config=config,
            retry_config=retry_config,
        )

    async def parse_html(self, html: str) -> list[IndustryReport]:
        """Parse KPMG Insights HTML and extract reports.

        Looks for kpmg-card elements with the following CSS selectors:

        - Card container: ``div.kpmg-card`` or
          ``[data-component="kpmg-card"]``
        - Title: ``.kpmg-card__title`` or ``h3``
        - Link: ``.kpmg-card__link`` or ``a[href]``
        - Date: ``.kpmg-card__date``
        - Description: ``.kpmg-card__description``

        Parameters
        ----------
        html : str
            Raw HTML from KPMG's insights page.

        Returns
        -------
        list[IndustryReport]
            List of extracted KPMG reports.
        """
        soup = _parse_html_with_bs4(html)
        reports: list[IndustryReport] = []

        # Find kpmg-card elements
        articles = soup.find_all(
            ["div", "article"],
            attrs={"data-component": "kpmg-card"},
        )
        if not articles:
            articles = soup.find_all(
                ["div", "article"],
                class_=re.compile(r"kpmg-card"),
            )

        for article in articles:
            try:
                # Extract title
                title_tag = article.find(
                    class_=re.compile(r"kpmg-card__title")
                ) or article.find(["h2", "h3", "h4"])
                if not title_tag:
                    continue
                title = title_tag.get_text(strip=True)

                # Extract URL
                link_tag = article.find(
                    "a", class_=re.compile(r"kpmg-card__link")
                ) or article.find("a", href=True)
                if not link_tag or not link_tag.get("href"):
                    continue
                href = link_tag["href"]
                url = href if href.startswith("http") else f"https://kpmg.com{href}"

                # Extract date
                date_tag = article.find(class_=re.compile(r"kpmg-card__date"))
                published_at = (
                    _parse_date(date_tag.get_text(strip=True)) if date_tag else None
                )
                if published_at is None:
                    published_at = datetime.now(tz=timezone.utc)

                # Extract description
                desc_tag = article.find(class_=re.compile(r"kpmg-card__description"))
                summary = desc_tag.get_text(strip=True) if desc_tag else None

                reports.append(
                    IndustryReport(
                        source="KPMG",
                        title=title,
                        url=url,
                        published_at=published_at,
                        sector=self.sector,
                        summary=summary,
                        tier=SourceTier.SCRAPING,
                    )
                )

            except Exception as e:
                logger.warning(
                    "Failed to parse KPMG article",
                    error=str(e),
                )
                continue

        logger.debug(
            "KPMG HTML parsed",
            article_count=len(reports),
        )

        return reports


# =============================================================================
# Module exports
# =============================================================================

__all__ = [
    "AccentureScraper",
    "BCGScraper",
    "BainScraper",
    "ConsultingScraper",
    "DeloitteScraper",
    "EYScraper",
    "KPMGScraper",
    "McKinseyScraper",
    "PwCScraper",
]
