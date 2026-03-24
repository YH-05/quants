"""Investment bank report scrapers (Goldman Sachs, Morgan Stanley, JP Morgan).

This module provides scrapers for extracting published insights and reports
from the three major investment banks:

- **Goldman Sachs Insights** (``goldmansachs.com/insights``)
- **Morgan Stanley Ideas** (``morganstanley.com/ideas``)
- **JP Morgan Research** (``jpmorgan.com/insights/research``)

Each scraper inherits from ``InvestmentBankScraper`` (which extends
``BaseScraper``) and implements site-specific HTML parsing logic. The
2-layer fallback (curl_cffi -> Playwright) and retry logic are provided
by the base classes.

Features
--------
- Article listing page scraping for each site
- Body text extraction via trafilatura + Playwright fallback
- Rate limiting compliance (polite delay between requests)
- robots.txt URL tracking for compliance verification
- JSON output saving to ``data/raw/industry_reports/{source}/``
- Robust date parsing for multiple date formats

Examples
--------
>>> async with GoldmanSachsScraper(sector="Technology") as scraper:
...     result = await scraper.scrape()
...     if result.success:
...         paths = await scraper.save_reports(result.reports)

See Also
--------
market.industry.scrapers.base : BaseScraper abstract base class.
market.industry.scrapers.consulting : ConsultingScraper (reference pattern).
market.etfcom.session : ETFComSession (curl_cffi + Cloudflare bypass reference).
"""

from __future__ import annotations

import asyncio
import json
import re
from abc import abstractmethod
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

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

    Supports multiple date formats commonly used on investment bank websites:

    - ``"January 18, 2026"`` (full month name)
    - ``"Jan 18, 2026"`` (abbreviated month name)
    - ``"2026-01-18"`` (ISO 8601 date)
    - ``"Feb 3, 2026"`` (abbreviated month, single-digit day)

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
    >>> _parse_date("January 18, 2026")
    datetime.datetime(2026, 1, 18, 0, 0, tzinfo=datetime.timezone.utc)

    >>> _parse_date("2026-01-18")
    datetime.datetime(2026, 1, 18, 0, 0, tzinfo=datetime.timezone.utc)

    >>> _parse_date("not a date") is None
    True
    """
    if not date_str or not date_str.strip():
        return None

    date_str = date_str.strip()

    formats = [
        "%B %d, %Y",  # January 18, 2026
        "%b %d, %Y",  # Jan 18, 2026
        "%Y-%m-%d",  # 2026-01-18
        "%B %d %Y",  # January 18 2026
        "%b %d %Y",  # Jan 18 2026
        "%d %B %Y",  # 18 January 2026
        "%d %b %Y",  # 18 Jan 2026
        "%m/%d/%Y",  # 01/18/2026
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
    >>> _title_to_slug("Global Macro Outlook 2026")
    'global-macro-outlook-2026'

    >>> _title_to_slug("Top of Mind: AI Investment Trends")
    'top-of-mind-ai-investment-trends'
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
# InvestmentBankScraper Base Class
# =============================================================================


class InvestmentBankScraper(BaseScraper):
    """Base class for investment bank report scrapers.

    Extends ``BaseScraper`` with investment-bank-specific functionality:

    - Sector filtering
    - Report saving to JSON files
    - Body text extraction via trafilatura
    - robots.txt URL tracking for compliance
    - Common scrape() workflow

    Subclasses must implement ``parse_html()`` for their site-specific
    HTML structure.

    Parameters
    ----------
    source_name : str
        Human-readable name of the investment bank.
    base_url : str
        Base URL of the insights/research page.
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

        # Build robots.txt URL from base_url
        parsed = urlparse(base_url)
        self.robots_txt_url: str = f"{parsed.scheme}://{parsed.netloc}/robots.txt"

        logger.info(
            "InvestmentBankScraper initialized",
            source_name=source_name,
            sector=sector,
            output_dir=str(self.output_dir),
            robots_txt_url=self.robots_txt_url,
        )

    async def scrape(self) -> ScrapingResult:
        """Execute the scraping operation for this investment bank source.

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
        >>> async with GoldmanSachsScraper() as scraper:
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
        fallback if trafilatura fails.

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
        ``{date}_{slug}.json`` (e.g. ``2026-01-18_global-macro-outlook.json``)

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
# Goldman Sachs Scraper
# =============================================================================


class GoldmanSachsScraper(InvestmentBankScraper):
    """Scraper for Goldman Sachs Insights (goldmansachs.com/insights).

    Extracts articles from Goldman Sachs' insights page, parsing
    article titles, URLs, publication dates, and descriptions.

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
    >>> async with GoldmanSachsScraper(sector="Technology") as scraper:
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
            source_name="Goldman Sachs",
            base_url="https://www.goldmansachs.com/insights",
            source_key="goldman",
            sector=sector,
            output_dir=output_dir,
            config=config,
            retry_config=retry_config,
        )

    async def parse_html(self, html: str) -> list[IndustryReport]:
        """Parse Goldman Sachs Insights HTML and extract reports.

        Looks for article cards with the following CSS selectors:

        - Article container: ``article.article-card`` or
          ``[data-testid="article-card"]``
        - Title: ``.article-card__title`` or ``h3``
        - Link: ``.article-card__link`` or ``a[href]``
        - Date: ``time.article-card__date`` (with ``datetime`` attr)
        - Description: ``.article-card__description``

        Parameters
        ----------
        html : str
            Raw HTML from Goldman Sachs' insights page.

        Returns
        -------
        list[IndustryReport]
            List of extracted Goldman Sachs reports.
        """
        soup = _parse_html_with_bs4(html)
        reports: list[IndustryReport] = []

        # Find article cards
        articles = soup.find_all(
            ["article", "div"],
            attrs={"data-testid": "article-card"},
        )
        if not articles:
            articles = soup.find_all(
                ["article", "div"],
                class_=re.compile(r"article-card"),
            )

        for article in articles:
            try:
                # Extract title
                title_tag = article.find(
                    class_=re.compile(r"article-card__title")
                ) or article.find(["h2", "h3", "h4"])
                if not title_tag:
                    continue
                title = title_tag.get_text(strip=True)

                # Extract URL
                link_tag = article.find(
                    "a", class_=re.compile(r"article-card__link")
                ) or article.find("a", href=True)
                if not link_tag or not link_tag.get("href"):
                    continue
                href = link_tag["href"]
                url = (
                    href
                    if href.startswith("http")
                    else f"https://www.goldmansachs.com{href}"
                )

                # Extract date - prefer datetime attribute on <time> element
                date_tag = article.find(
                    "time", class_=re.compile(r"article-card__date")
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

                # Extract description
                desc_tag = article.find(class_=re.compile(r"article-card__description"))
                summary = desc_tag.get_text(strip=True) if desc_tag else None

                reports.append(
                    IndustryReport(
                        source="Goldman Sachs",
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
                    "Failed to parse Goldman Sachs article",
                    error=str(e),
                )
                continue

        logger.debug(
            "Goldman Sachs HTML parsed",
            article_count=len(reports),
        )

        return reports


# =============================================================================
# Morgan Stanley Scraper
# =============================================================================


class MorganStanleyScraper(InvestmentBankScraper):
    """Scraper for Morgan Stanley Ideas (morganstanley.com/ideas).

    Extracts articles from Morgan Stanley's ideas page, parsing
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
    >>> async with MorganStanleyScraper() as scraper:
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
            source_name="Morgan Stanley",
            base_url="https://www.morganstanley.com/ideas",
            source_key="morgan_stanley",
            sector=sector,
            output_dir=output_dir,
            config=config,
            retry_config=retry_config,
        )

    async def parse_html(self, html: str) -> list[IndustryReport]:
        """Parse Morgan Stanley Ideas HTML and extract reports.

        Looks for thought leadership cards with the following CSS selectors:

        - Card container: ``div.thought-leadership-card``
        - Title: ``.thought-leadership-card__title`` or ``h3``
        - Link: ``.thought-leadership-card__link`` or ``a[href]``
        - Date: ``.thought-leadership-card__date``
        - Summary: ``.thought-leadership-card__summary``

        Parameters
        ----------
        html : str
            Raw HTML from Morgan Stanley's ideas page.

        Returns
        -------
        list[IndustryReport]
            List of extracted Morgan Stanley reports.
        """
        soup = _parse_html_with_bs4(html)
        reports: list[IndustryReport] = []

        articles = soup.find_all(
            ["div", "article"],
            class_=re.compile(r"thought-leadership-card"),
        )

        for article in articles:
            try:
                # Extract title
                title_tag = article.find(
                    class_=re.compile(r"thought-leadership-card__title")
                ) or article.find(["h2", "h3", "h4"])
                if not title_tag:
                    continue
                title = title_tag.get_text(strip=True)

                # Extract URL
                link_tag = article.find(
                    "a", class_=re.compile(r"thought-leadership-card__link")
                ) or article.find("a", href=True)
                if not link_tag or not link_tag.get("href"):
                    continue
                href = link_tag["href"]
                url = (
                    href
                    if href.startswith("http")
                    else f"https://www.morganstanley.com{href}"
                )

                # Extract date
                date_tag = article.find(
                    class_=re.compile(r"thought-leadership-card__date")
                )
                published_at = (
                    _parse_date(date_tag.get_text(strip=True)) if date_tag else None
                )
                if published_at is None:
                    published_at = datetime.now(tz=timezone.utc)

                # Extract summary
                summary_tag = article.find(
                    class_=re.compile(r"thought-leadership-card__summary")
                )
                summary = summary_tag.get_text(strip=True) if summary_tag else None

                reports.append(
                    IndustryReport(
                        source="Morgan Stanley",
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
                    "Failed to parse Morgan Stanley article",
                    error=str(e),
                )
                continue

        logger.debug(
            "Morgan Stanley HTML parsed",
            article_count=len(reports),
        )

        return reports


# =============================================================================
# JP Morgan Scraper
# =============================================================================


class JPMorganScraper(InvestmentBankScraper):
    """Scraper for JP Morgan Research (jpmorgan.com/insights/research).

    Extracts articles from JP Morgan's research insights page, parsing
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
    >>> async with JPMorganScraper() as scraper:
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
            source_name="JP Morgan",
            base_url="https://www.jpmorgan.com/insights/research",
            source_key="jpmorgan",
            sector=sector,
            output_dir=output_dir,
            config=config,
            retry_config=retry_config,
        )

    async def parse_html(self, html: str) -> list[IndustryReport]:
        """Parse JP Morgan Research HTML and extract reports.

        Looks for research cards with the following CSS selectors:

        - Card container: ``div.research-card`` or
          ``[data-type="research"]``
        - Title: ``.research-card__title`` or ``h3``
        - Link: ``.research-card__link`` or ``a[href]``
        - Date: ``.research-card__date``
        - Excerpt: ``.research-card__excerpt``

        Parameters
        ----------
        html : str
            Raw HTML from JP Morgan's research page.

        Returns
        -------
        list[IndustryReport]
            List of extracted JP Morgan reports.
        """
        soup = _parse_html_with_bs4(html)
        reports: list[IndustryReport] = []

        # Find research cards
        articles = soup.find_all(
            ["div", "article"],
            attrs={"data-type": "research"},
        )
        if not articles:
            articles = soup.find_all(
                ["div", "article"],
                class_=re.compile(r"research-card"),
            )

        for article in articles:
            try:
                # Extract title
                title_tag = article.find(
                    class_=re.compile(r"research-card__title")
                ) or article.find(["h2", "h3", "h4"])
                if not title_tag:
                    continue
                title = title_tag.get_text(strip=True)

                # Extract URL
                link_tag = article.find(
                    "a", class_=re.compile(r"research-card__link")
                ) or article.find("a", href=True)
                if not link_tag or not link_tag.get("href"):
                    continue
                href = link_tag["href"]
                url = (
                    href
                    if href.startswith("http")
                    else f"https://www.jpmorgan.com{href}"
                )

                # Extract date
                date_tag = article.find(class_=re.compile(r"research-card__date"))
                published_at = (
                    _parse_date(date_tag.get_text(strip=True)) if date_tag else None
                )
                if published_at is None:
                    published_at = datetime.now(tz=timezone.utc)

                # Extract excerpt
                excerpt_tag = article.find(class_=re.compile(r"research-card__excerpt"))
                summary = excerpt_tag.get_text(strip=True) if excerpt_tag else None

                reports.append(
                    IndustryReport(
                        source="JP Morgan",
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
                    "Failed to parse JP Morgan article",
                    error=str(e),
                )
                continue

        logger.debug(
            "JP Morgan HTML parsed",
            article_count=len(reports),
        )

        return reports


# =============================================================================
# Module exports
# =============================================================================

__all__ = [
    "GoldmanSachsScraper",
    "InvestmentBankScraper",
    "JPMorganScraper",
    "MorganStanleyScraper",
]
