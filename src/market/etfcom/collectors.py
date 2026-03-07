"""ETF.com data collectors for tickers, fundamentals, and fund flows.

This module provides three ``DataCollector`` subclasses for scraping
ETF data from ETF.com:

- ``TickerCollector``: Scrapes the screener page for ETF ticker lists.
- ``FundamentalsCollector``: Scrapes individual ETF profile pages for
  key-value fundamental data (summary + classification).
- ``FundFlowsCollector``: Scrapes the fund flows page for daily flow data.

``FundamentalsCollector`` and ``FundFlowsCollector`` use a two-tier
HTML retrieval strategy: curl_cffi (via ``ETFComSession``) is the
primary method, with Playwright (via ``ETFComBrowserMixin``) as a
fallback when curl_cffi encounters bot-blocking or returns empty content.

Features
--------
- DataCollector abstract base class compliance (fetch/validate interface)
- curl_cffi-first + Playwright-fallback HTML retrieval
- Playwright-based browser automation via ETFComBrowserMixin
- Dependency injection for session and browser instances (testability)
- Pagination support (100 items per page) for TickerCollector
- ``'--'`` placeholder conversion to NaN / None
- BeautifulSoup HTML table parsing
- Comma-separated number parsing for fund flows

Examples
--------
>>> from market.etfcom.collectors import TickerCollector
>>> collector = TickerCollector()
>>> df = collector.collect()
>>> print(df.head())
  ticker                       name       issuer  ...
0    SPY  SPDR S&P 500 ETF Trust  State Street  ...

>>> from market.etfcom.collectors import FundamentalsCollector
>>> collector = FundamentalsCollector()
>>> df = collector.fetch(tickers=["SPY", "VOO"])

>>> from market.etfcom.collectors import FundFlowsCollector
>>> collector = FundFlowsCollector()
>>> df = collector.fetch(ticker="SPY")

See Also
--------
market.base_collector : DataCollector abstract base class.
market.etfcom.browser : ETFComBrowserMixin for Playwright operations.
market.etfcom.session : curl_cffi-based session for non-JS pages.
market.etfcom.constants : CSS selectors and URL constants.
market.tsa : TSAPassengerDataCollector (similar DataCollector pattern).
"""

from __future__ import annotations

import asyncio
import json
import math
import re
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd
from bs4 import BeautifulSoup, Tag

from market.base_collector import DataCollector
from market.etfcom.browser import ETFComBrowserMixin
from market.etfcom.constants import (
    CLASSIFICATION_DATA_ID,
    DEFAULT_MAX_CONCURRENCY,
    DEFAULT_TICKER_CACHE_DIR,
    DEFAULT_TICKER_CACHE_TTL_HOURS,
    FLOW_TABLE_ID,
    FUND_FLOWS_QUERY,
    FUND_FLOWS_URL_TEMPLATE,
    NEXT_PAGE_SELECTOR,
    PROFILE_URL_TEMPLATE,
    SCREENER_URL,
    SUMMARY_DATA_ID,
    TICKERS_API_URL,
)
from market.etfcom.errors import ETFComAPIError, ETFComBlockedError, ETFComNotFoundError
from market.etfcom.session import ETFComSession
from market.etfcom.types import RetryConfig, ScrapingConfig
from utils_core.logging import get_logger

logger = get_logger(__name__)

# Ticker symbol validation pattern (alphanumeric + hyphens, 1-10 chars)
_TICKER_PATTERN = re.compile(r"^[A-Z0-9\-]{1,10}$")


def _normalize_ticker(ticker: str) -> str:
    """Normalize and validate a ticker symbol.

    Parameters
    ----------
    ticker : str
        Raw ticker symbol (case-insensitive).

    Returns
    -------
    str
        Upper-cased ticker symbol.

    Raises
    ------
    ValueError
        If the ticker contains invalid characters or exceeds 10 characters.
    """
    normalized = ticker.strip().upper()
    if not _TICKER_PATTERN.match(normalized):
        raise ValueError(
            f"Invalid ticker symbol: {ticker!r}. "
            "Only alphanumeric characters and hyphens (1-10 chars) are allowed."
        )
    return normalized


# Column name mapping from raw screener table headers to snake_case
_COLUMN_MAP: dict[str, str] = {
    "ticker": "ticker",
    "fund name": "name",
    "issuer": "issuer",
    "segment": "category",
    "expense ratio": "expense_ratio",
    "aum": "aum",
}

# Placeholder value used by ETF.com for missing data
_PLACEHOLDER = "--"


class TickerCollector(DataCollector):
    """Collector for ETF ticker list from ETF.com screener page.

    Scrapes the ETF.com screener page to extract a complete list of ETF
    tickers with basic metadata (name, issuer, category, expense_ratio,
    aum). Uses Playwright for JavaScript-rendered page content.

    The browser instance can be injected via the constructor for testing
    (dependency injection pattern).

    Parameters
    ----------
    browser : ETFComBrowserMixin | None
        Pre-configured browser instance. If None, a new instance is
        created internally using the provided config.
    config : ScrapingConfig | None
        Scraping configuration. Used when creating a new browser
        instance (ignored if browser is provided).

    Attributes
    ----------
    _browser_instance : ETFComBrowserMixin | None
        Injected browser instance (None if creating internally).
    _config : ScrapingConfig
        The scraping configuration.

    Examples
    --------
    >>> collector = TickerCollector()
    >>> df = collector.fetch()
    >>> print(f"Found {len(df)} ETFs")

    >>> # With dependency injection for testing
    >>> mock_browser = AsyncMock()
    >>> collector = TickerCollector(browser=mock_browser)
    """

    def __init__(
        self,
        browser: ETFComBrowserMixin | None = None,
        config: ScrapingConfig | None = None,
    ) -> None:
        """Initialize TickerCollector with optional browser and config.

        Parameters
        ----------
        browser : ETFComBrowserMixin | None
            Pre-configured browser instance for dependency injection.
            If None, a new ETFComBrowserMixin is created when fetch() is called.
        config : ScrapingConfig | None
            Scraping configuration. Defaults to ``ScrapingConfig()``.
        """
        self._browser_instance: ETFComBrowserMixin | None = browser
        self._config: ScrapingConfig = config or ScrapingConfig()

        logger.info(
            "TickerCollector initialized",
            browser_injected=browser is not None,
            headless=self._config.headless,
        )

    def fetch(self, **kwargs: Any) -> pd.DataFrame:
        """Fetch all ETF tickers from the ETF.com screener page.

        Delegates to ``_async_fetch()`` via ``asyncio.run()``.

        Parameters
        ----------
        **kwargs : Any
            Additional keyword arguments (currently unused).

        Returns
        -------
        pd.DataFrame
            DataFrame with columns: ticker, name, issuer, category,
            expense_ratio, aum.

        Raises
        ------
        ETFComTimeoutError
            If the screener page fails to load.

        Examples
        --------
        >>> collector = TickerCollector()
        >>> df = collector.fetch()
        >>> print(df.columns.tolist())
        ['ticker', 'name', 'issuer', 'category', 'expense_ratio', 'aum']
        """
        logger.info("Starting ticker collection from ETF.com screener")
        return asyncio.run(self._async_fetch(**kwargs))

    async def _async_fetch(self, **kwargs: Any) -> pd.DataFrame:
        """Asynchronously fetch all ETF tickers from the screener page.

        Workflow:
        1. Start browser (or use injected instance)
        2. Navigate to screener page
        3. Accept cookie consent
        4. Switch to 100 items per page
        5. Loop: extract table HTML -> parse rows -> check next page
        6. Combine all rows into a DataFrame

        Parameters
        ----------
        **kwargs : Any
            Additional keyword arguments (currently unused).

        Returns
        -------
        pd.DataFrame
            DataFrame containing all ETF ticker data.
        """
        all_rows: list[dict[str, str | None]] = []

        # Use injected browser or create a new one
        if self._browser_instance is not None:
            browser = self._browser_instance
            should_close = False
        else:
            browser = ETFComBrowserMixin(config=self._config)
            should_close = True

        try:
            # Ensure browser is ready
            await browser._ensure_browser()

            # Navigate to screener page
            logger.info("Navigating to screener page", url=SCREENER_URL)
            page = await browser._navigate(SCREENER_URL)

            # Accept cookie consent
            await browser._accept_cookies(page)

            # Switch to 100 items per page
            await browser._click_display_100(page)

            # Wait for table content to stabilize
            await asyncio.sleep(self._config.stability_wait)

            # Pagination loop
            page_number = 1
            while True:
                logger.debug(
                    "Scraping screener page",
                    page_number=page_number,
                )

                # Get current page HTML
                html: str = await page.content()
                rows = self._parse_screener_table(html)
                all_rows.extend(rows)

                logger.debug(
                    "Page scraped",
                    page_number=page_number,
                    row_count=len(rows),
                    total_rows=len(all_rows),
                )

                # Check for next page
                next_button = await page.query_selector(NEXT_PAGE_SELECTOR)
                if next_button is None:
                    logger.info(
                        "Last page reached",
                        page_number=page_number,
                        total_rows=len(all_rows),
                    )
                    break

                # Click next page
                await next_button.click()
                await asyncio.sleep(self._config.stability_wait)
                page_number += 1

            # Close the page
            await page.close()

        finally:
            if should_close:
                await browser.close()

        # Convert rows to DataFrame
        df = self._rows_to_dataframe(all_rows)

        logger.info(
            "Ticker collection completed",
            total_tickers=len(df),
            columns=list(df.columns) if not df.empty else [],
        )

        return df

    def _parse_screener_table(self, html: str) -> list[dict[str, str | None]]:
        """Parse the ETF screener HTML table into a list of row dicts.

        Extracts ticker, name, issuer, category, expense_ratio, and aum
        from the table body rows. The ``'--'`` placeholder values are
        converted to ``None``.

        Parameters
        ----------
        html : str
            Full HTML content of the screener page.

        Returns
        -------
        list[dict[str, str | None]]
            List of dicts, each representing one ETF row.
            Keys: ticker, name, issuer, category, expense_ratio, aum.
            Values are None where the original value was ``'--'``.
        """
        soup = BeautifulSoup(html, "html.parser")
        table = soup.find("table")

        if table is None:
            logger.warning("No table found in screener HTML")
            return []

        # Extract header names for column mapping
        headers: list[str] = []
        thead = table.find("thead")
        if thead:
            header_row = thead.find("tr")
            if header_row:
                headers = [
                    th.get_text(strip=True).lower() for th in header_row.find_all("th")
                ]

        # Extract table body rows
        tbody = table.find("tbody")
        if tbody is None:
            logger.warning("No tbody found in screener table")
            return []

        rows: list[dict[str, str | None]] = []

        for tr in tbody.find_all("tr"):
            cells = tr.find_all("td")
            if not cells:
                continue

            cell_values: list[str] = []
            for cell in cells:
                # Extract text, handling <a> tags
                text = cell.get_text(strip=True)
                cell_values.append(text)

            # Map cell values to column names
            row: dict[str, str | None] = {}
            for i, header in enumerate(headers):
                if i >= len(cell_values):
                    break

                mapped_key = _COLUMN_MAP.get(header)
                if mapped_key is None:
                    continue

                value = cell_values[i]
                # Convert '--' placeholder to None
                if value == _PLACEHOLDER:
                    row[mapped_key] = None
                else:
                    row[mapped_key] = value

            # Only add rows that have at least a ticker
            if row.get("ticker"):
                rows.append(row)

        logger.debug(
            "Screener table parsed",
            row_count=len(rows),
        )

        return rows

    def _rows_to_dataframe(self, rows: list[dict[str, str | None]]) -> pd.DataFrame:
        """Convert a list of row dicts to a pandas DataFrame.

        Parameters
        ----------
        rows : list[dict[str, str | None]]
            List of dicts from ``_parse_screener_table()``.

        Returns
        -------
        pd.DataFrame
            DataFrame with columns: ticker, name, issuer, category,
            expense_ratio, aum. Returns an empty DataFrame with the
            correct columns if the input list is empty.
        """
        if not rows:
            logger.debug("No rows to convert, returning empty DataFrame")
            return pd.DataFrame(
                columns=pd.Index(
                    ["ticker", "name", "issuer", "category", "expense_ratio", "aum"]
                )
            )

        df = pd.DataFrame(rows)

        # Ensure all required columns exist
        for col in ["ticker", "name", "issuer", "category", "expense_ratio", "aum"]:
            if col not in df.columns:
                df[col] = None

        logger.debug(
            "Rows converted to DataFrame",
            row_count=len(df),
            columns=list(df.columns),
        )

        return df

    def validate(self, df: pd.DataFrame) -> bool:
        """Validate the fetched ticker data.

        Checks that the DataFrame:
        - Is not empty
        - Contains the ``ticker`` column

        Parameters
        ----------
        df : pd.DataFrame
            DataFrame to validate.

        Returns
        -------
        bool
            True if the data is valid, False otherwise.

        Examples
        --------
        >>> collector = TickerCollector()
        >>> df = pd.DataFrame({"ticker": ["SPY"], "name": ["SPDR"]})
        >>> collector.validate(df)
        True
        >>> collector.validate(pd.DataFrame())
        False
        """
        if df.empty:
            logger.warning("Validation failed: DataFrame is empty")
            return False

        if "ticker" not in df.columns:
            logger.warning(
                "Validation failed: 'ticker' column not found",
                actual_columns=list(df.columns),
            )
            return False

        logger.debug(
            "Validation passed",
            row_count=len(df),
        )
        return True


# Minimum content length to consider a curl_cffi response as valid.
# Responses shorter than this threshold indicate empty or error pages
# and trigger a Playwright fallback.
_MIN_CONTENT_LENGTH: int = 500

# Key mapping from raw ETF.com profile labels to snake_case field names.
# Used by FundamentalsCollector._parse_profile() to normalise the
# key-value pairs extracted from #summary-data and #classification-data.
_PROFILE_KEY_MAP: dict[str, str] = {
    "issuer": "issuer",
    "inception date": "inception_date",
    "expense ratio": "expense_ratio",
    "aum": "aum",
    "index tracked": "index_tracked",
    "segment": "segment",
    "structure": "structure",
    "asset class": "asset_class",
    "category": "category",
    "focus": "focus",
    "niche": "niche",
    "region": "region",
    "geography": "geography",
    "weighting methodology": "index_weighting_methodology",
    "index weighting methodology": "index_weighting_methodology",
    "selection methodology": "index_selection_methodology",
    "index selection methodology": "index_selection_methodology",
    "segment benchmark": "segment_benchmark",
}

# Required columns for FundamentalsCollector validation.
_FUNDAMENTALS_REQUIRED_COLUMNS: frozenset[str] = frozenset(
    {"ticker", "issuer", "expense_ratio", "aum"}
)

# Required columns for FundFlowsCollector validation.
_FUND_FLOWS_REQUIRED_COLUMNS: frozenset[str] = frozenset(
    {"date", "ticker", "net_flows"}
)


class FundamentalsCollector(DataCollector):
    """Collector for ETF fundamental data from ETF.com profile pages.

    Scrapes the ETF.com profile page (``etf.com/{ticker}``) for each
    requested ticker, extracting key-value data from the
    ``#summary-data`` and ``#classification-index-data`` sections.

    Uses a two-tier HTML retrieval strategy:

    1. **curl_cffi** (via ``ETFComSession.get_with_retry()``): fast,
       low-overhead HTTP request with TLS fingerprint impersonation.
    2. **Playwright** (via ``ETFComBrowserMixin._get_page_html_with_retry()``):
       full browser rendering as fallback when curl_cffi is blocked or
       returns empty content.

    Parameters
    ----------
    session : ETFComSession | None
        Pre-configured curl_cffi session. If None, a new session is
        created internally.
    browser : ETFComBrowserMixin | None
        Pre-configured Playwright browser. If None, created on demand
        when fallback is needed.
    config : ScrapingConfig | None
        Scraping configuration. Defaults to ``ScrapingConfig()``.
    retry_config : RetryConfig | None
        Retry configuration. Defaults to ``RetryConfig()``.

    Examples
    --------
    >>> collector = FundamentalsCollector()
    >>> df = collector.fetch(tickers=["SPY", "VOO"])
    >>> print(df.columns.tolist())
    ['ticker', 'issuer', 'inception_date', 'expense_ratio', ...]

    >>> # With dependency injection for testing
    >>> collector = FundamentalsCollector(session=mock_session)
    """

    def __init__(
        self,
        session: ETFComSession | None = None,
        browser: ETFComBrowserMixin | None = None,
        config: ScrapingConfig | None = None,
        retry_config: RetryConfig | None = None,
    ) -> None:
        """Initialize FundamentalsCollector with optional session, browser, and config.

        Parameters
        ----------
        session : ETFComSession | None
            Pre-configured curl_cffi session for dependency injection.
            If None, a new ETFComSession is created when fetch() is called.
        browser : ETFComBrowserMixin | None
            Pre-configured Playwright browser for dependency injection.
            If None, a new ETFComBrowserMixin is created when fallback is needed.
        config : ScrapingConfig | None
            Scraping configuration. Defaults to ``ScrapingConfig()``.
        retry_config : RetryConfig | None
            Retry configuration. Defaults to ``RetryConfig()``.
        """
        self._session_instance: ETFComSession | None = session
        self._browser_instance: ETFComBrowserMixin | None = browser
        self._config: ScrapingConfig = config or ScrapingConfig()
        self._retry_config: RetryConfig = retry_config or RetryConfig()

        logger.info(
            "FundamentalsCollector initialized",
            session_injected=session is not None,
            browser_injected=browser is not None,
        )

    def fetch(self, **kwargs: Any) -> pd.DataFrame:
        """Fetch fundamental data for the specified ETF tickers.

        Iterates over the given tickers sequentially, scraping each
        ETF profile page and extracting key-value data from the
        ``#summary-data`` and ``#classification-index-data`` sections.

        Parameters
        ----------
        **kwargs : Any
            Keyword arguments. Expected:
            - tickers (list[str]): List of ETF ticker symbols to fetch.

        Returns
        -------
        pd.DataFrame
            DataFrame with columns corresponding to the profile fields
            (ticker, issuer, inception_date, expense_ratio, aum,
            index_tracked, segment, structure, asset_class, category,
            focus, niche, region, geography,
            index_weighting_methodology, index_selection_methodology,
            segment_benchmark). Returns an empty DataFrame if tickers
            is empty.

        Examples
        --------
        >>> collector = FundamentalsCollector()
        >>> df = collector.fetch(tickers=["SPY", "VOO"])
        >>> print(df["ticker"].tolist())
        ['SPY', 'VOO']
        """
        tickers: list[str] = kwargs.get("tickers", [])

        if not tickers:
            logger.info("No tickers provided, returning empty DataFrame")
            return pd.DataFrame()

        logger.info(
            "Starting fundamentals collection",
            ticker_count=len(tickers),
        )

        # Resolve session: use injected or create new
        session = self._session_instance
        should_close_session = False
        if session is None:
            session = ETFComSession(
                config=self._config, retry_config=self._retry_config
            )
            should_close_session = True

        all_records: list[dict[str, str | None]] = []

        try:
            for ticker in tickers:
                normalized_ticker = _normalize_ticker(ticker)
                url = PROFILE_URL_TEMPLATE.format(ticker=normalized_ticker)
                logger.debug(
                    "Fetching fundamentals",
                    ticker=normalized_ticker,
                    url=url,
                )

                try:
                    html = self._get_html(url)
                    record = self._parse_profile(html, normalized_ticker)
                    all_records.append(record)

                    logger.debug(
                        "Fundamentals fetched",
                        ticker=normalized_ticker,
                        field_count=len(record),
                    )
                except ETFComNotFoundError:
                    logger.warning(
                        "ETF not found (HTTP 404), adding minimal record",
                        ticker=normalized_ticker,
                        url=url,
                    )
                    all_records.append({"ticker": normalized_ticker})
                except Exception as e:
                    logger.warning(
                        "Failed to fetch fundamentals",
                        ticker=normalized_ticker,
                        error=str(e),
                    )
                    # Add a minimal record with just the ticker
                    all_records.append({"ticker": normalized_ticker})
        finally:
            if should_close_session:
                session.close()

        if not all_records:
            return pd.DataFrame()

        df = pd.DataFrame(all_records)

        logger.info(
            "Fundamentals collection completed",
            total_tickers=len(df),
            columns=list(df.columns) if not df.empty else [],
        )

        return df

    def _get_html(self, url: str) -> str:
        """Retrieve HTML content using curl_cffi with Playwright fallback.

        1. Tries ``ETFComSession.get_with_retry(url)`` via curl_cffi.
        2. If the response is valid and has sufficient content, returns it.
        3. If blocked (``ETFComBlockedError``) or content is too short,
           falls back to ``ETFComBrowserMixin._get_page_html_with_retry(url)``.

        Parameters
        ----------
        url : str
            The URL to fetch HTML from.

        Returns
        -------
        str
            The HTML content of the page.

        Raises
        ------
        ETFComBlockedError
            If both curl_cffi and Playwright fail.
        ETFComNotFoundError
            If the requested ETF ticker returns HTTP 404.
        ETFComTimeoutError
            If Playwright fails with a timeout.
        """
        session = self._session_instance
        if session is None:
            session = ETFComSession(
                config=self._config, retry_config=self._retry_config
            )

        try:
            response = session.get_with_retry(url)
            html: str = response.text

            # Check if content is sufficient
            if len(html) >= _MIN_CONTENT_LENGTH:
                logger.debug(
                    "HTML retrieved via curl_cffi",
                    url=url,
                    content_length=len(html),
                )
                return html

            logger.debug(
                "curl_cffi response too short, falling back to Playwright",
                url=url,
                content_length=len(html),
            )

        except ETFComBlockedError:
            logger.debug(
                "curl_cffi blocked, falling back to Playwright",
                url=url,
            )

        # Fallback to Playwright
        return self._get_html_via_playwright(url)

    def _get_html_via_playwright(self, url: str) -> str:
        """Retrieve HTML content via Playwright browser.

        Parameters
        ----------
        url : str
            The URL to fetch HTML from.

        Returns
        -------
        str
            The HTML content of the page.
        """
        browser = self._browser_instance
        should_close = False
        if browser is None:
            browser = ETFComBrowserMixin(
                config=self._config, retry_config=self._retry_config
            )
            should_close = True

        try:
            loop = asyncio.new_event_loop()
            try:
                html: str = loop.run_until_complete(
                    self._async_get_html_via_playwright(browser, url)
                )
                return html
            finally:
                loop.close()
        finally:
            if should_close:
                close_loop = asyncio.new_event_loop()
                try:
                    close_loop.run_until_complete(browser.close())
                finally:
                    close_loop.close()

    async def _async_get_html_via_playwright(
        self,
        browser: ETFComBrowserMixin,
        url: str,
    ) -> str:
        """Asynchronously retrieve HTML via Playwright.

        Parameters
        ----------
        browser : ETFComBrowserMixin
            Browser instance to use.
        url : str
            The URL to fetch.

        Returns
        -------
        str
            The HTML content.
        """
        await browser._ensure_browser()
        html: str = await browser._get_page_html_with_retry(url)
        logger.debug(
            "HTML retrieved via Playwright",
            url=url,
            content_length=len(html),
        )
        return html

    def _parse_profile(self, html: str, ticker: str) -> dict[str, str | None]:
        """Parse an ETF profile page HTML to extract key-value data.

        Extracts data from the ``[data-testid='summary-data']`` and
        ``[data-testid='classification-data']`` sections. Each section
        contains a table with key-value rows (``<tr><td>Key</td><td>Value</td></tr>``).

        The ``'--'`` placeholder is converted to ``None``.

        Parameters
        ----------
        html : str
            Full HTML content of the ETF profile page.
        ticker : str
            The ETF ticker symbol (added to the result dict).

        Returns
        -------
        dict[str, str | None]
            Dictionary of parsed field values, keyed by snake_case names.
            Always includes ``ticker``. Other fields may be absent if
            the sections are not found in the HTML.

        Examples
        --------
        >>> collector = FundamentalsCollector()
        >>> data = collector._parse_profile(html, "SPY")
        >>> data["ticker"]
        'SPY'
        >>> data["issuer"]
        'State Street'
        """
        soup = BeautifulSoup(html, "html.parser")
        result: dict[str, str | None] = {"ticker": ticker}

        # Extract from both data sections
        for selector in [SUMMARY_DATA_ID, CLASSIFICATION_DATA_ID]:
            container = soup.select_one(selector)
            if container is None:
                logger.debug(
                    "Section not found in profile HTML",
                    ticker=ticker,
                    selector=selector,
                )
                continue

            table_tag = container.find("table")
            if table_tag is None or not isinstance(table_tag, Tag):
                continue

            tbody_tag = table_tag.find("tbody")
            if tbody_tag is None or not isinstance(tbody_tag, Tag):
                continue

            for tr in tbody_tag.find_all("tr"):
                cells = tr.find_all("td")
                if len(cells) != 2:
                    continue

                raw_key = cells[0].get_text(strip=True).lower()
                raw_value = cells[1].get_text(strip=True)

                # Map to snake_case field name
                field_name = _PROFILE_KEY_MAP.get(raw_key)
                if field_name is None:
                    logger.debug(
                        "Unknown profile field, skipping",
                        ticker=ticker,
                        raw_key=raw_key,
                    )
                    continue

                # Convert '--' placeholder to None
                if raw_value == _PLACEHOLDER:
                    result[field_name] = None
                else:
                    result[field_name] = raw_value

        logger.debug(
            "Profile parsed",
            ticker=ticker,
            field_count=len(result),
        )

        return result

    def validate(self, df: pd.DataFrame) -> bool:
        """Validate the fetched fundamentals data.

        Checks that the DataFrame:
        - Is not empty
        - Contains the required columns (ticker, issuer, expense_ratio, aum)

        Parameters
        ----------
        df : pd.DataFrame
            DataFrame to validate.

        Returns
        -------
        bool
            True if the data is valid, False otherwise.

        Examples
        --------
        >>> collector = FundamentalsCollector()
        >>> df = pd.DataFrame({"ticker": ["SPY"], "issuer": ["State Street"],
        ...                     "expense_ratio": ["0.09%"], "aum": ["$500B"]})
        >>> collector.validate(df)
        True
        """
        if df.empty:
            logger.warning("Validation failed: DataFrame is empty")
            return False

        missing = _FUNDAMENTALS_REQUIRED_COLUMNS - set(df.columns)
        if missing:
            logger.warning(
                "Validation failed: missing required columns",
                missing_columns=list(missing),
                actual_columns=list(df.columns),
            )
            return False

        logger.debug(
            "Validation passed",
            row_count=len(df),
        )
        return True


class FundFlowsCollector(DataCollector):
    """Collector for ETF fund flow data from ETF.com.

    Scrapes the ETF.com fund flows page for a given ticker, extracting
    daily net flow data from the fund flows table.

    Uses a two-tier HTML retrieval strategy:

    1. **curl_cffi** (via ``ETFComSession.get_with_retry()``): fast,
       low-overhead HTTP request with TLS fingerprint impersonation.
    2. **Playwright** (via ``ETFComBrowserMixin._get_page_html_with_retry()``):
       full browser rendering as fallback when curl_cffi is blocked or
       returns empty content.

    Parameters
    ----------
    session : ETFComSession | None
        Pre-configured curl_cffi session. If None, a new session is
        created internally.
    browser : ETFComBrowserMixin | None
        Pre-configured Playwright browser. If None, created on demand.
    config : ScrapingConfig | None
        Scraping configuration. Defaults to ``ScrapingConfig()``.
    retry_config : RetryConfig | None
        Retry configuration. Defaults to ``RetryConfig()``.

    Examples
    --------
    >>> collector = FundFlowsCollector()
    >>> df = collector.fetch(ticker="SPY")
    >>> print(df.columns.tolist())
    ['date', 'ticker', 'net_flows']
    """

    def __init__(
        self,
        session: ETFComSession | None = None,
        browser: ETFComBrowserMixin | None = None,
        config: ScrapingConfig | None = None,
        retry_config: RetryConfig | None = None,
    ) -> None:
        """Initialize FundFlowsCollector with optional session, browser, and config.

        Parameters
        ----------
        session : ETFComSession | None
            Pre-configured curl_cffi session for dependency injection.
        browser : ETFComBrowserMixin | None
            Pre-configured Playwright browser for dependency injection.
        config : ScrapingConfig | None
            Scraping configuration. Defaults to ``ScrapingConfig()``.
        retry_config : RetryConfig | None
            Retry configuration. Defaults to ``RetryConfig()``.
        """
        self._session_instance: ETFComSession | None = session
        self._browser_instance: ETFComBrowserMixin | None = browser
        self._config: ScrapingConfig = config or ScrapingConfig()
        self._retry_config: RetryConfig = retry_config or RetryConfig()

        logger.info(
            "FundFlowsCollector initialized",
            session_injected=session is not None,
            browser_injected=browser is not None,
        )

    def fetch(self, **kwargs: Any) -> pd.DataFrame:
        """Fetch fund flow data for the specified ETF ticker.

        Parameters
        ----------
        **kwargs : Any
            Keyword arguments. Expected:
            - ticker (str): ETF ticker symbol to fetch fund flows for.

        Returns
        -------
        pd.DataFrame
            DataFrame with columns: date, ticker, net_flows.
            Returns an empty DataFrame if no data is found.

        Examples
        --------
        >>> collector = FundFlowsCollector()
        >>> df = collector.fetch(ticker="SPY")
        >>> print(df.head())
               date ticker  net_flows
        0  2025-09-10    SPY    2787.59
        """
        ticker: str = kwargs.get("ticker", "")

        if not ticker:
            logger.info("No ticker provided, returning empty DataFrame")
            return pd.DataFrame()

        ticker = _normalize_ticker(ticker)

        url = FUND_FLOWS_URL_TEMPLATE.format(ticker=ticker)
        logger.info(
            "Starting fund flows collection",
            ticker=ticker,
            url=url,
        )

        # Resolve session
        session = self._session_instance
        should_close_session = False
        if session is None:
            session = ETFComSession(
                config=self._config, retry_config=self._retry_config
            )
            should_close_session = True

        try:
            html = self._get_html(url)
        finally:
            if should_close_session:
                session.close()

        rows = self._parse_fund_flows_table(html)

        if not rows:
            logger.warning(
                "No fund flow data found",
                ticker=ticker,
            )
            return pd.DataFrame(columns=pd.Index(["date", "ticker", "net_flows"]))

        # Add ticker to each row
        for row in rows:
            row["ticker"] = ticker

        df = pd.DataFrame(rows)

        logger.info(
            "Fund flows collection completed",
            ticker=ticker,
            row_count=len(df),
        )

        return df

    def _get_html(self, url: str) -> str:
        """Retrieve HTML content using curl_cffi with Playwright fallback.

        Uses the same two-tier strategy as FundamentalsCollector:
        curl_cffi first, Playwright on failure or empty content.

        Parameters
        ----------
        url : str
            The URL to fetch HTML from.

        Returns
        -------
        str
            The HTML content of the page.

        Raises
        ------
        ETFComBlockedError
            If both curl_cffi and Playwright fail.
        ETFComNotFoundError
            If the requested ETF ticker returns HTTP 404.
        ETFComTimeoutError
            If Playwright fails with a timeout.
        """
        session = self._session_instance
        if session is None:
            session = ETFComSession(
                config=self._config, retry_config=self._retry_config
            )

        try:
            response = session.get_with_retry(url)
            html: str = response.text

            if len(html) >= _MIN_CONTENT_LENGTH:
                logger.debug(
                    "HTML retrieved via curl_cffi",
                    url=url,
                    content_length=len(html),
                )
                return html

            logger.debug(
                "curl_cffi response too short, falling back to Playwright",
                url=url,
                content_length=len(html),
            )

        except ETFComBlockedError:
            logger.debug(
                "curl_cffi blocked, falling back to Playwright",
                url=url,
            )

        # Fallback to Playwright
        browser = self._browser_instance
        should_close = False
        if browser is None:
            browser = ETFComBrowserMixin(
                config=self._config, retry_config=self._retry_config
            )
            should_close = True

        try:
            loop = asyncio.new_event_loop()
            try:
                html = loop.run_until_complete(
                    self._async_get_html_via_playwright(browser, url)
                )
                return html
            finally:
                loop.close()
        finally:
            if should_close:
                close_loop = asyncio.new_event_loop()
                try:
                    close_loop.run_until_complete(browser.close())
                finally:
                    close_loop.close()

    async def _async_get_html_via_playwright(
        self,
        browser: ETFComBrowserMixin,
        url: str,
    ) -> str:
        """Asynchronously retrieve HTML via Playwright.

        Parameters
        ----------
        browser : ETFComBrowserMixin
            Browser instance to use.
        url : str
            The URL to fetch.

        Returns
        -------
        str
            The HTML content.
        """
        await browser._ensure_browser()
        html: str = await browser._get_page_html_with_retry(url)
        logger.debug(
            "HTML retrieved via Playwright",
            url=url,
            content_length=len(html),
        )
        return html

    def _parse_fund_flows_table(self, html: str) -> list[dict[str, Any]]:
        """Parse the fund flows HTML table into a list of row dicts.

        Extracts date and net flow values from the
        ``[data-testid='fund-flows-table']`` section. Comma-separated
        numbers (e.g. ``"2,787.59"``) are converted to floats.
        The ``'--'`` placeholder is converted to ``NaN``.

        Parameters
        ----------
        html : str
            Full HTML content of the fund flows page.

        Returns
        -------
        list[dict[str, Any]]
            List of dicts with keys ``date`` (str) and ``net_flows`` (float).
            Returns an empty list if the table is not found.

        Examples
        --------
        >>> collector = FundFlowsCollector()
        >>> rows = collector._parse_fund_flows_table(html)
        >>> rows[0]
        {'date': '2025-09-10', 'net_flows': 2787.59}
        """
        soup = BeautifulSoup(html, "html.parser")

        # Find the fund flows table container
        container = soup.select_one(FLOW_TABLE_ID)
        if container is None:
            logger.warning("Fund flows table not found in HTML")
            return []

        table_tag = container.find("table")
        if table_tag is None or not isinstance(table_tag, Tag):
            logger.warning("No table found in fund flows container")
            return []

        tbody_tag = table_tag.find("tbody")
        if tbody_tag is None or not isinstance(tbody_tag, Tag):
            logger.warning("No tbody found in fund flows table")
            return []

        rows: list[dict[str, Any]] = []

        for tr in tbody_tag.find_all("tr"):
            cells = tr.find_all("td")
            if len(cells) < 2:
                continue

            date_text = cells[0].get_text(strip=True)
            flow_text = cells[1].get_text(strip=True)

            # Convert '--' placeholder to NaN
            if flow_text == _PLACEHOLDER:
                net_flows: float = math.nan
            else:
                # Remove commas and convert to float
                try:
                    net_flows = float(flow_text.replace(",", ""))
                except ValueError:
                    logger.debug(
                        "Failed to parse net flows value",
                        date=date_text,
                        raw_value=flow_text,
                    )
                    net_flows = math.nan

            rows.append({"date": date_text, "net_flows": net_flows})

        logger.debug(
            "Fund flows table parsed",
            row_count=len(rows),
        )

        return rows

    def validate(self, df: pd.DataFrame) -> bool:
        """Validate the fetched fund flow data.

        Checks that the DataFrame:
        - Is not empty
        - Contains the required columns (date, ticker, net_flows)

        Parameters
        ----------
        df : pd.DataFrame
            DataFrame to validate.

        Returns
        -------
        bool
            True if the data is valid, False otherwise.

        Examples
        --------
        >>> collector = FundFlowsCollector()
        >>> df = pd.DataFrame({"date": ["2025-09-10"], "ticker": ["SPY"],
        ...                     "net_flows": [2787.59]})
        >>> collector.validate(df)
        True
        """
        if df.empty:
            logger.warning("Validation failed: DataFrame is empty")
            return False

        missing = _FUND_FLOWS_REQUIRED_COLUMNS - set(df.columns)
        if missing:
            logger.warning(
                "Validation failed: missing required columns",
                missing_columns=list(missing),
                actual_columns=list(df.columns),
            )
            return False

        logger.debug(
            "Validation passed",
            row_count=len(df),
        )
        return True


# camelCase field name mapping for REST API responses.
# Maps camelCase API keys to snake_case DataFrame column names.
_CAMEL_TO_SNAKE_PATTERN: re.Pattern[str] = re.compile(r"(?<=[a-z0-9])(?=[A-Z])")

# Required columns for HistoricalFundFlowsCollector validation.
_HISTORICAL_REQUIRED_COLUMNS: frozenset[str] = frozenset(
    {"ticker", "nav_date", "fund_flows"}
)


def _camel_to_snake(name: str) -> str:
    """Convert a camelCase string to snake_case.

    Parameters
    ----------
    name : str
        camelCase string to convert.

    Returns
    -------
    str
        The snake_case equivalent.

    Examples
    --------
    >>> _camel_to_snake("navChangePercent")
    'nav_change_percent'
    >>> _camel_to_snake("aum")
    'aum'
    """
    return _CAMEL_TO_SNAKE_PATTERN.sub("_", name).lower()


class HistoricalFundFlowsCollector(DataCollector):
    """Collector for historical fund flow data from the ETF.com REST API.

    Uses the ETF.com REST API (``api-prod.etf.com``) to fetch historical
    daily fund flow data for individual ETFs. Unlike ``FundFlowsCollector``
    which scrapes HTML pages, this collector targets the JSON REST API
    directly and does not require a browser.

    The workflow for fetching fund flows is:

    1. Resolve the ticker symbol to a fund ID via ``_resolve_fund_id()``.
    2. POST to the ``fund-flows-query`` endpoint with the fund ID.
    3. Parse the camelCase JSON response into a snake_case DataFrame.

    Parameters
    ----------
    session : ETFComSession | None
        Pre-configured curl_cffi session. If None, a new session is
        created internally.
    config : ScrapingConfig | None
        Scraping configuration (delays, timeout). Defaults to ``ScrapingConfig()``.
    retry_config : RetryConfig | None
        Retry configuration. Defaults to ``RetryConfig()``.
    cache_dir : str | None
        Directory for ticker list file cache. Defaults to
        ``DEFAULT_TICKER_CACHE_DIR`` (``data/raw/etfcom``).
    cache_ttl_hours : int | None
        TTL for ticker list file cache in hours. Defaults to
        ``DEFAULT_TICKER_CACHE_TTL_HOURS`` (24).

    Attributes
    ----------
    _session_instance : ETFComSession | None
        Injected session instance (None if creating internally).
    _config : ScrapingConfig
        The scraping configuration.
    _retry_config : RetryConfig
        The retry configuration.
    _fund_id_cache : dict[str, int]
        In-memory cache mapping ticker symbols to fund IDs.
    _cache_dir : str
        Directory for ticker list file cache.
    _cache_ttl_hours : int
        TTL for ticker list file cache in hours.

    Examples
    --------
    >>> collector = HistoricalFundFlowsCollector()
    >>> df = collector.fetch(ticker="SPY")
    >>> print(df.columns.tolist())
    ['ticker', 'nav_date', 'nav', 'nav_change', ...]

    >>> # Fetch multiple tickers with parallel execution
    >>> df = collector.fetch_multiple(tickers=["SPY", "VOO", "QQQ"])

    See Also
    --------
    FundFlowsCollector : HTML scraping-based fund flow collector.
    market.etfcom.types.HistoricalFundFlowRecord : Data record type.
    market.etfcom.constants : REST API URL constants.
    """

    def __init__(
        self,
        session: ETFComSession | None = None,
        config: ScrapingConfig | None = None,
        retry_config: RetryConfig | None = None,
        cache_dir: str | None = None,
        cache_ttl_hours: int | None = None,
    ) -> None:
        """Initialize HistoricalFundFlowsCollector.

        Parameters
        ----------
        session : ETFComSession | None
            Pre-configured curl_cffi session for dependency injection.
            If None, a new ETFComSession is created when fetch() is called.
        config : ScrapingConfig | None
            Scraping configuration. Defaults to ``ScrapingConfig()``.
        retry_config : RetryConfig | None
            Retry configuration. Defaults to ``RetryConfig()``.
        cache_dir : str | None
            Directory for ticker list file cache. Defaults to
            ``DEFAULT_TICKER_CACHE_DIR`` (``data/raw/etfcom``).
        cache_ttl_hours : int | None
            TTL for ticker list file cache in hours. Defaults to
            ``DEFAULT_TICKER_CACHE_TTL_HOURS`` (24).
        """
        self._session_instance: ETFComSession | None = session
        self._config: ScrapingConfig = config or ScrapingConfig()
        self._retry_config: RetryConfig = retry_config or RetryConfig()
        self._fund_id_cache: dict[str, int] = {}
        self._cache_dir: str = cache_dir or DEFAULT_TICKER_CACHE_DIR
        self._cache_ttl_hours: int = cache_ttl_hours or DEFAULT_TICKER_CACHE_TTL_HOURS

        logger.info(
            "HistoricalFundFlowsCollector initialized",
            session_injected=session is not None,
            cache_dir=self._cache_dir,
            cache_ttl_hours=self._cache_ttl_hours,
        )

    def _get_session(self) -> tuple[ETFComSession, bool]:
        """Resolve the session: use injected or create new.

        Returns
        -------
        tuple[ETFComSession, bool]
            A tuple of (session, should_close). ``should_close`` is True
            when a new session was created internally.
        """
        if self._session_instance is not None:
            return self._session_instance, False
        return ETFComSession(config=self._config, retry_config=self._retry_config), True

    # -----------------------------------------------------------------
    # File cache methods
    # -----------------------------------------------------------------

    def _get_cache_path(self) -> Path:
        """Return the path to the ticker cache JSON file.

        Returns
        -------
        Path
            The full path to ``tickers.json`` within ``_cache_dir``.
        """
        return Path(self._cache_dir) / "tickers.json"

    def _load_ticker_cache(self) -> dict[str, Any]:
        """Load the ticker cache from a JSON file.

        Returns an empty dict if the file does not exist or cannot be
        parsed.

        Returns
        -------
        dict[str, Any]
            The cached data with ``cached_at`` (ISO timestamp) and
            ``tickers`` (dict mapping ticker to fund_id) keys, or an
            empty dict if no valid cache is found.
        """
        cache_path = self._get_cache_path()

        if not cache_path.exists():
            logger.debug("Ticker cache file not found", path=str(cache_path))
            return {}

        try:
            data: dict[str, Any] = json.loads(cache_path.read_text(encoding="utf-8"))
            logger.debug(
                "Ticker cache loaded from file",
                path=str(cache_path),
                ticker_count=len(data.get("tickers", {})),
            )
            return data
        except (json.JSONDecodeError, OSError) as e:
            logger.warning(
                "Failed to load ticker cache file",
                path=str(cache_path),
                error=str(e),
            )
            return {}

    def _save_ticker_cache(self) -> None:
        """Save the in-memory ticker cache to a JSON file.

        Creates the cache directory if it does not exist. The JSON file
        includes a ``cached_at`` ISO timestamp for TTL validation.
        """
        cache_path = self._get_cache_path()

        # Ensure directory exists
        cache_path.parent.mkdir(parents=True, exist_ok=True)

        cache_data: dict[str, Any] = {
            "cached_at": datetime.now(tz=timezone.utc).isoformat(),
            "tickers": self._fund_id_cache,
        }

        try:
            cache_path.write_text(
                json.dumps(cache_data, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
            logger.info(
                "Ticker cache saved to file",
                path=str(cache_path),
                ticker_count=len(self._fund_id_cache),
            )
        except OSError as e:
            logger.warning(
                "Failed to save ticker cache file",
                path=str(cache_path),
                error=str(e),
            )

    def _is_cache_valid(self, cache_data: dict[str, Any]) -> bool:
        """Check whether the cached data is within the TTL.

        Parameters
        ----------
        cache_data : dict[str, Any]
            The cache data dict, expected to contain a ``cached_at``
            ISO timestamp string.

        Returns
        -------
        bool
            True if the cache is within the TTL, False otherwise.
        """
        cached_at_str = cache_data.get("cached_at")
        if cached_at_str is None:
            logger.debug("Cache data missing 'cached_at' field")
            return False

        try:
            cached_at = datetime.fromisoformat(str(cached_at_str))
            age_hours = (
                datetime.now(tz=timezone.utc) - cached_at
            ).total_seconds() / 3600

            is_valid = age_hours < self._cache_ttl_hours
            logger.debug(
                "Cache validity check",
                age_hours=round(age_hours, 2),
                ttl_hours=self._cache_ttl_hours,
                is_valid=is_valid,
            )
            return is_valid
        except (ValueError, TypeError) as e:
            logger.warning(
                "Failed to parse cache timestamp",
                cached_at=cached_at_str,
                error=str(e),
            )
            return False

    def fetch(self, **kwargs: Any) -> pd.DataFrame:
        """Fetch historical fund flow data for a single ETF ticker.

        Parameters
        ----------
        **kwargs : Any
            Keyword arguments. Expected:
            - ticker (str): ETF ticker symbol to fetch fund flows for.
            - start_date (str | None): ISO format start date filter (inclusive).
            - end_date (str | None): ISO format end date filter (inclusive).

        Returns
        -------
        pd.DataFrame
            DataFrame with columns: ticker, nav_date, nav, nav_change,
            nav_change_percent, premium_discount, fund_flows,
            shares_outstanding, aum. Returns an empty DataFrame if
            ticker is not provided.

        Raises
        ------
        ETFComAPIError
            If the ticker cannot be resolved or the API returns an error.

        Examples
        --------
        >>> collector = HistoricalFundFlowsCollector()
        >>> df = collector.fetch(ticker="SPY")
        >>> print(df.head())
        """
        ticker: str = kwargs.get("ticker", "")
        start_date: str | None = kwargs.get("start_date")
        end_date: str | None = kwargs.get("end_date")

        if not ticker:
            logger.info("No ticker provided, returning empty DataFrame")
            return pd.DataFrame()

        ticker = _normalize_ticker(ticker)

        logger.info(
            "Starting historical fund flow collection",
            ticker=ticker,
            start_date=start_date,
            end_date=end_date,
        )

        session, should_close = self._get_session()
        try:
            # Step 1: Resolve ticker to fund_id
            fund_id = self._resolve_fund_id(ticker)

            # Step 2: Fetch raw fund flow records
            raw_records = self._fetch_fund_flows(fund_id=fund_id, ticker=ticker)

            # Step 3: Parse response into DataFrame
            df = self._parse_response(
                raw_records,
                ticker=ticker,
                start_date=start_date,
                end_date=end_date,
            )

            logger.info(
                "Historical fund flow collection completed",
                ticker=ticker,
                row_count=len(df),
            )

            return df
        finally:
            if should_close:
                session.close()

    def fetch_tickers(self) -> pd.DataFrame:
        """Fetch the list of all available ETF tickers with fund IDs.

        Calls ``GET /v2/fund/tickers`` to retrieve the full ticker list
        from the ETF.com REST API. The response is parsed into a
        snake_case DataFrame.

        Returns
        -------
        pd.DataFrame
            DataFrame with columns: ticker, fund_id, name, issuer,
            asset_class, inception_date.

        Raises
        ------
        ETFComAPIError
            If the API returns a non-200 status code.

        Examples
        --------
        >>> collector = HistoricalFundFlowsCollector()
        >>> df = collector.fetch_tickers()
        >>> print(f"Found {len(df)} tickers")
        """
        logger.info("Fetching ticker list from ETF.com API")

        session, should_close = self._get_session()
        try:
            response = session.get_with_retry(TICKERS_API_URL)
            data: list[dict[str, Any]] = response.json()

            if not data:
                logger.warning("Ticker API returned empty response")
                return pd.DataFrame()

            # Convert camelCase keys to snake_case
            records: list[dict[str, Any]] = []
            for item in data:
                record: dict[str, Any] = {}
                for key, value in item.items():
                    snake_key = _camel_to_snake(key)
                    # Normalise 'fund_name' -> 'name' for consistency
                    if snake_key == "fund_name":
                        snake_key = "name"
                    record[snake_key] = value
                records.append(record)

            df = pd.DataFrame(records)

            logger.info(
                "Ticker list fetched",
                ticker_count=len(df),
            )

            return df
        finally:
            if should_close:
                session.close()

    def _resolve_fund_id(self, ticker: str) -> int:
        """Resolve a ticker symbol to a fund ID via 3-tier cache.

        Resolution order:

        1. **In-memory cache**: fastest, populated during session.
        2. **File cache**: ``data/raw/etfcom/tickers.json`` with TTL check.
        3. **API call**: ``GET /v2/fund/tickers``, populates both caches.

        Parameters
        ----------
        ticker : str
            ETF ticker symbol (e.g. ``"SPY"``).

        Returns
        -------
        int
            The fund ID for the given ticker.

        Raises
        ------
        ETFComAPIError
            If the ticker is not found in the ticker list.

        Examples
        --------
        >>> collector = HistoricalFundFlowsCollector()
        >>> fund_id = collector._resolve_fund_id("SPY")
        >>> fund_id
        1
        """
        # Tier 1: In-memory cache
        if ticker in self._fund_id_cache:
            logger.debug("Fund ID resolved from in-memory cache", ticker=ticker)
            return self._fund_id_cache[ticker]

        # Tier 2: File cache
        cache_data = self._load_ticker_cache()
        if cache_data and self._is_cache_valid(cache_data):
            tickers_map: dict[str, int] = cache_data.get("tickers", {})
            if ticker in tickers_map:
                # Populate in-memory cache from file cache
                self._fund_id_cache.update({k: int(v) for k, v in tickers_map.items()})
                logger.debug(
                    "Fund ID resolved from file cache",
                    ticker=ticker,
                    fund_id=tickers_map[ticker],
                )
                return int(tickers_map[ticker])

        # Tier 3: API call
        logger.debug("Fund ID cache miss, fetching ticker list from API", ticker=ticker)

        session, should_close = self._get_session()
        try:
            response = session.get_with_retry(TICKERS_API_URL)
            data: list[dict[str, Any]] = response.json()

            for item in data:
                t = str(item.get("ticker", ""))
                fid = item.get("fundId")
                if t and fid is not None:
                    self._fund_id_cache[t] = int(fid)
        finally:
            if should_close:
                session.close()

        # Save to file cache after API fetch
        self._save_ticker_cache()

        if ticker not in self._fund_id_cache:
            msg = f"Ticker not found in ETF.com API: {ticker}"
            logger.error("Fund ID resolution failed", ticker=ticker)
            raise ETFComAPIError(
                msg,
                url=TICKERS_API_URL,
                ticker=ticker,
            )

        fund_id = self._fund_id_cache[ticker]
        logger.debug(
            "Fund ID resolved from API",
            ticker=ticker,
            fund_id=fund_id,
        )
        return fund_id

    def _fetch_fund_flows(
        self,
        fund_id: int,
        ticker: str,
    ) -> list[dict[str, Any]]:
        """Fetch raw fund flow records from the REST API.

        Sends a POST request to the ``fund-flows-query`` endpoint with
        the fund ID to retrieve daily fund flow data.

        Parameters
        ----------
        fund_id : int
            The fund ID obtained from ``_resolve_fund_id()``.
        ticker : str
            The ETF ticker symbol (for error reporting).

        Returns
        -------
        list[dict[str, Any]]
            A list of raw fund flow records as dicts with camelCase keys.

        Raises
        ------
        ETFComAPIError
            If the API returns a non-200 status code or unexpected response.

        Examples
        --------
        >>> records = collector._fetch_fund_flows(fund_id=1, ticker="SPY")
        >>> len(records)
        250
        """
        logger.debug(
            "Fetching fund flows from API",
            fund_id=fund_id,
            ticker=ticker,
        )

        session, should_close = self._get_session()
        try:
            response = session.post_with_retry(
                FUND_FLOWS_QUERY,
                json={"fundId": fund_id},
            )

            if response.status_code != 200:
                msg = (
                    f"Fund flows API returned HTTP {response.status_code} "
                    f"for ticker={ticker}, fund_id={fund_id}"
                )
                logger.error(
                    "Fund flows API error",
                    ticker=ticker,
                    fund_id=fund_id,
                    status_code=response.status_code,
                )
                raise ETFComAPIError(
                    msg,
                    url=FUND_FLOWS_QUERY,
                    status_code=response.status_code,
                    response_body=response.text,
                    ticker=ticker,
                    fund_id=fund_id,
                )

            data: dict[str, Any] = response.json()
            records: list[dict[str, Any]] = data.get("results", [])

            logger.debug(
                "Fund flows fetched",
                ticker=ticker,
                record_count=len(records),
            )

            return records
        finally:
            if should_close:
                session.close()

    def _parse_response(
        self,
        records: list[dict[str, Any]],
        *,
        ticker: str,
        start_date: str | None = None,
        end_date: str | None = None,
    ) -> pd.DataFrame:
        """Parse raw API records into a snake_case DataFrame.

        Performs the following transformations:

        1. Convert camelCase keys to snake_case.
        2. Parse ``nav_date`` strings to ``datetime.date`` objects.
        3. Add ``ticker`` column.
        4. Filter by ``start_date`` / ``end_date`` if provided.
        5. Sort by ``nav_date`` ascending.

        Parameters
        ----------
        records : list[dict[str, Any]]
            Raw API records with camelCase keys.
        ticker : str
            ETF ticker symbol to add as a column.
        start_date : str | None
            ISO format start date filter (inclusive). If None, no lower bound.
        end_date : str | None
            ISO format end date filter (inclusive). If None, no upper bound.

        Returns
        -------
        pd.DataFrame
            DataFrame with snake_case columns, filtered and sorted.
            Returns an empty DataFrame if records is empty.
        """
        if not records:
            logger.debug("No records to parse, returning empty DataFrame")
            return pd.DataFrame()

        # Step 1: Convert camelCase to snake_case
        parsed_records: list[dict[str, Any]] = []
        for record in records:
            parsed: dict[str, Any] = {}
            for key, value in record.items():
                parsed[_camel_to_snake(key)] = value
            parsed_records.append(parsed)

        df = pd.DataFrame(parsed_records)

        # Step 2: Parse nav_date to datetime.date
        if "nav_date" in df.columns:
            df["nav_date"] = pd.to_datetime(df["nav_date"]).dt.date

        # Step 3: Add ticker column
        df["ticker"] = ticker

        # Step 4: Date filtering
        if start_date is not None:
            start = date.fromisoformat(start_date)
            df = df[df["nav_date"] >= start]

        if end_date is not None:
            end = date.fromisoformat(end_date)
            df = df[df["nav_date"] <= end]

        # Step 5: Sort by nav_date ascending
        df = df.sort_values("nav_date", ascending=True).reset_index(drop=True)

        logger.debug(
            "Response parsed",
            ticker=ticker,
            row_count=len(df),
        )

        return df

    def fetch_multiple(
        self,
        tickers: list[str] | None = None,
        *,
        max_concurrency: int | None = None,
        **kwargs: Any,
    ) -> pd.DataFrame:
        """Fetch historical fund flow data for multiple tickers in parallel.

        Uses ``asyncio.Semaphore`` to limit the number of concurrent
        API requests. The public interface is synchronous (uses
        ``asyncio.run()`` internally).

        Parameters
        ----------
        tickers : list[str] | None
            List of ETF ticker symbols to fetch.
        max_concurrency : int | None
            Maximum number of concurrent API requests. Defaults to
            ``DEFAULT_MAX_CONCURRENCY`` (5).
        **kwargs : Any
            Additional keyword arguments passed to ``fetch()``.

        Returns
        -------
        pd.DataFrame
            Combined DataFrame with fund flow data for all tickers.
            Returns an empty DataFrame if tickers is None or empty.

        Examples
        --------
        >>> collector = HistoricalFundFlowsCollector()
        >>> df = collector.fetch_multiple(tickers=["SPY", "VOO"])

        >>> # With custom concurrency limit
        >>> df = collector.fetch_multiple(
        ...     tickers=["SPY", "VOO", "QQQ"],
        ...     max_concurrency=2,
        ... )
        """
        if not tickers:
            logger.info("No tickers provided, returning empty DataFrame")
            return pd.DataFrame()

        concurrency = max_concurrency or DEFAULT_MAX_CONCURRENCY

        logger.info(
            "Starting multi-ticker fund flow collection",
            ticker_count=len(tickers),
            max_concurrency=concurrency,
        )

        return asyncio.run(
            self._async_fetch_multiple(
                tickers=tickers,
                max_concurrency=concurrency,
                **kwargs,
            )
        )

    async def _async_fetch_multiple(
        self,
        tickers: list[str],
        max_concurrency: int,
        **kwargs: Any,
    ) -> pd.DataFrame:
        """Asynchronously fetch fund flows for multiple tickers with concurrency limit.

        Parameters
        ----------
        tickers : list[str]
            List of ETF ticker symbols to fetch.
        max_concurrency : int
            Maximum number of concurrent fetches.
        **kwargs : Any
            Additional keyword arguments passed to ``fetch()``.

        Returns
        -------
        pd.DataFrame
            Combined DataFrame with fund flow data for all tickers.
        """
        semaphore = asyncio.Semaphore(max_concurrency)

        async def _fetch_one(ticker: str) -> pd.DataFrame | None:
            async with semaphore:
                try:
                    loop = asyncio.get_running_loop()
                    df = await loop.run_in_executor(
                        None,
                        lambda: self.fetch(ticker=ticker, **kwargs),
                    )
                    if not df.empty:
                        return df
                except ETFComAPIError as e:
                    logger.warning(
                        "Failed to fetch fund flows for ticker",
                        ticker=ticker,
                        error=str(e),
                    )
                return None

        tasks = [_fetch_one(ticker) for ticker in tickers]
        results = await asyncio.gather(*tasks)

        all_dfs: list[pd.DataFrame] = [df for df in results if df is not None]

        if not all_dfs:
            logger.warning("No fund flow data collected for any ticker")
            return pd.DataFrame()

        combined = pd.concat(all_dfs, ignore_index=True)

        logger.info(
            "Multi-ticker collection completed",
            ticker_count=len(tickers),
            total_rows=len(combined),
        )

        return combined

    def validate(self, df: pd.DataFrame) -> bool:
        """Validate the fetched historical fund flow data.

        Checks that the DataFrame:
        - Is not empty
        - Contains the required columns (ticker, nav_date, fund_flows)

        Parameters
        ----------
        df : pd.DataFrame
            DataFrame to validate.

        Returns
        -------
        bool
            True if the data is valid, False otherwise.

        Examples
        --------
        >>> collector = HistoricalFundFlowsCollector()
        >>> df = pd.DataFrame({
        ...     "ticker": ["SPY"],
        ...     "nav_date": [date(2025, 9, 10)],
        ...     "fund_flows": [2787590000.0],
        ... })
        >>> collector.validate(df)
        True
        """
        if df.empty:
            logger.warning("Validation failed: DataFrame is empty")
            return False

        missing = _HISTORICAL_REQUIRED_COLUMNS - set(df.columns)
        if missing:
            logger.warning(
                "Validation failed: missing required columns",
                missing_columns=list(missing),
                actual_columns=list(df.columns),
            )
            return False

        logger.debug(
            "Validation passed",
            row_count=len(df),
        )
        return True


__all__ = [
    "FundFlowsCollector",
    "FundamentalsCollector",
    "HistoricalFundFlowsCollector",
    "TickerCollector",
]
