"""Abstract base class for industry report scrapers.

This module provides the ``BaseScraper`` abstract base class that defines
the common interface and 2-layer fallback scraping strategy for all
industry report scrapers.

The 2-layer fallback follows the same pattern as ``market.etfcom``:

1. **Layer 1 (curl_cffi)**: Fast HTTP session with TLS fingerprint
   impersonation. Suitable for pages that do not require JavaScript rendering.
2. **Layer 2 (Playwright)**: Headless browser automation for pages that
   require JavaScript rendering (e.g. dynamically loaded content, SPA pages).

If Layer 1 fails (e.g. bot detection, JavaScript-required page), the scraper
automatically falls back to Layer 2.

Features
--------
- 2-layer fallback: curl_cffi -> Playwright
- Polite delays between requests
- Exponential backoff retry logic
- User-Agent rotation
- Async context manager for resource management

Examples
--------
>>> class McKinseyScraper(BaseScraper):
...     async def scrape(self) -> ScrapingResult:
...         html = await self._fetch_html(self.base_url)
...         reports = await self.parse_html(html)
...         return ScrapingResult(success=True, source=self.source_name,
...                               url=self.base_url, reports=reports)
...
...     async def parse_html(self, html: str) -> list[IndustryReport]:
...         # Parse HTML and extract reports
...         ...

See Also
--------
market.etfcom.session : ETFComSession (curl_cffi + Cloudflare bypass reference).
market.etfcom.client : ETFComClient (API client reference).
market.nasdaq.session : NasdaqSession (curl_cffi session reference).
"""

from __future__ import annotations

import asyncio
import random
from abc import ABC, abstractmethod
from typing import Any

from market.industry.types import (
    IndustryReport,
    RetryConfig,
    ScrapingConfig,
    ScrapingResult,
)
from utils_core.logging import get_logger

logger = get_logger(__name__)

# Default User-Agent strings for HTTP requests (aligned with etfcom/nasdaq)
_DEFAULT_USER_AGENTS: list[str] = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:133.0) Gecko/20100101 Firefox/133.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:133.0) Gecko/20100101 Firefox/133.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/18.2 Safari/605.1.15",
]


class BaseScraper(ABC):
    """Abstract base class for industry report scrapers.

    Provides the common 2-layer fallback scraping infrastructure
    (curl_cffi -> Playwright) and retry logic. Subclasses must implement
    ``scrape()`` and ``parse_html()`` methods.

    Parameters
    ----------
    source_name : str
        Human-readable name of the data source (e.g. ``"McKinsey"``).
    base_url : str
        Base URL of the data source.
    config : ScrapingConfig | None
        Scraping configuration. If ``None``, defaults are used.
    retry_config : RetryConfig | None
        Retry configuration. If ``None``, defaults are used.

    Attributes
    ----------
    source_name : str
        The data source name.
    base_url : str
        The base URL.
    config : ScrapingConfig
        The scraping configuration.
    retry_config : RetryConfig
        The retry configuration.

    Examples
    --------
    >>> class MyScraper(BaseScraper):
    ...     async def scrape(self) -> ScrapingResult: ...
    ...     async def parse_html(self, html: str) -> list[IndustryReport]: ...
    """

    def __init__(
        self,
        source_name: str,
        base_url: str,
        config: ScrapingConfig | None = None,
        retry_config: RetryConfig | None = None,
    ) -> None:
        self.source_name: str = source_name
        self.base_url: str = base_url
        self.config: ScrapingConfig = config or ScrapingConfig()
        self.retry_config: RetryConfig = retry_config or RetryConfig()

        # User-Agent list for rotation
        self._user_agents: list[str] = (
            list(self.config.user_agents)
            if self.config.user_agents
            else list(_DEFAULT_USER_AGENTS)
        )

        # Lazy-initialized resources
        self._session: Any | None = None
        self._playwright: Any | None = None
        self._browser: Any | None = None

        logger.info(
            "BaseScraper initialized",
            source_name=source_name,
            base_url=base_url,
            polite_delay=self.config.polite_delay,
            timeout=self.config.timeout,
            max_retry_attempts=self.retry_config.max_attempts,
        )

    # =========================================================================
    # Abstract Methods
    # =========================================================================

    @abstractmethod
    async def scrape(self) -> ScrapingResult:
        """Execute the scraping operation for this source.

        Subclasses must implement this method to define source-specific
        scraping logic, including URL construction, HTML fetching,
        and report extraction.

        Returns
        -------
        ScrapingResult
            The result of the scraping operation.
        """

    @abstractmethod
    async def parse_html(self, html: str) -> list[IndustryReport]:
        """Parse HTML content and extract industry reports.

        Subclasses must implement this method to define source-specific
        HTML parsing logic.

        Parameters
        ----------
        html : str
            Raw HTML content to parse.

        Returns
        -------
        list[IndustryReport]
            List of extracted industry report records.
        """

    # =========================================================================
    # 2-Layer Fallback: curl_cffi -> Playwright
    # =========================================================================

    async def _fetch_html(self, url: str) -> str:
        """Fetch HTML content using 2-layer fallback strategy.

        Attempts to fetch the page using curl_cffi (Layer 1). If that fails
        (e.g. bot detection, JS-required page), falls back to Playwright
        (Layer 2).

        Parameters
        ----------
        url : str
            The URL to fetch.

        Returns
        -------
        str
            The HTML content of the page.

        Raises
        ------
        Exception
            If both Layer 1 and Layer 2 fail.
        """
        try:
            html = await self._fetch_with_session(url)
            logger.debug(
                "Layer 1 (curl_cffi) succeeded",
                url=url,
                html_length=len(html),
            )
            return html

        except Exception as session_error:
            logger.warning(
                "Layer 1 (curl_cffi) failed, falling back to Playwright",
                url=url,
                error=str(session_error),
            )
            html = await self._fetch_with_browser(url)
            logger.debug(
                "Layer 2 (Playwright) succeeded",
                url=url,
                html_length=len(html),
            )
            return html

    async def _fetch_with_session(self, url: str) -> str:
        """Fetch HTML using curl_cffi session (Layer 1).

        Creates a curl_cffi session with TLS fingerprint impersonation
        and polite delay, then fetches the specified URL.

        Parameters
        ----------
        url : str
            The URL to fetch.

        Returns
        -------
        str
            The HTML content of the response.

        Raises
        ------
        Exception
            If the request fails or returns a non-200 status.
        """
        # Apply polite delay
        delay = self.config.polite_delay + random.uniform(  # nosec B311
            0, self.config.delay_jitter
        )
        await asyncio.sleep(delay)
        logger.debug("Polite delay applied", delay_seconds=delay, url=url)

        # Lazy import curl_cffi to avoid hard dependency
        try:
            from curl_cffi import requests as curl_requests
        except ImportError as e:
            raise ImportError(
                "curl_cffi is not installed. Install with: uv add curl_cffi"
            ) from e

        # Create session if not exists
        if self._session is None:
            from typing import cast

            from curl_cffi.requests import BrowserTypeLiteral

            self._session = curl_requests.Session(
                impersonate=cast("BrowserTypeLiteral", self.config.impersonate),
            )

        # Build headers
        user_agent = random.choice(self._user_agents)  # nosec B311
        headers: dict[str, str] = {
            "User-Agent": user_agent,
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.9",
            "Accept-Encoding": "gzip, deflate, br",
        }

        response = self._session.get(
            url,
            headers=headers,
            timeout=self.config.timeout,
        )

        if response.status_code != 200:
            raise RuntimeError(f"HTTP {response.status_code} from {url}")

        html: str = response.text
        return html

    async def _fetch_with_browser(self, url: str) -> str:
        """Fetch HTML using Playwright headless browser (Layer 2).

        Launches a Playwright Chromium browser with stealth settings
        and navigates to the specified URL. Used as fallback when
        curl_cffi fails.

        Parameters
        ----------
        url : str
            The URL to fetch.

        Returns
        -------
        str
            The HTML content of the page.

        Raises
        ------
        ImportError
            If playwright is not installed.
        """
        # Apply polite delay
        delay = self.config.polite_delay + random.uniform(  # nosec B311
            0, self.config.delay_jitter
        )
        await asyncio.sleep(delay)

        # Lazy import playwright
        try:
            from playwright.async_api import (  # type: ignore[import-not-found]
                async_playwright,
            )
        except ImportError as e:
            raise ImportError(
                "playwright is not installed. "
                "Install with: uv add playwright && playwright install chromium"
            ) from e

        async with async_playwright() as p:
            browser = await p.chromium.launch(
                headless=self.config.headless,
            )

            user_agent = random.choice(self._user_agents)  # nosec B311
            context = await browser.new_context(
                viewport={"width": 1920, "height": 1080},
                user_agent=user_agent,
                locale="en-US",
                timezone_id="America/New_York",
            )

            page = await context.new_page()
            timeout_ms = int(self.config.timeout * 1000)

            try:
                await page.goto(url, timeout=timeout_ms, wait_until="networkidle")
                html: str = await page.content()
                return html
            finally:
                await browser.close()

    # =========================================================================
    # Retry Logic
    # =========================================================================

    async def _fetch_html_with_retry(self, url: str) -> str:
        """Fetch HTML with retry and exponential backoff.

        Retries the page fetch according to ``RetryConfig`` settings
        when any exception is raised.

        Parameters
        ----------
        url : str
            The URL to fetch.

        Returns
        -------
        str
            The HTML content of the page.

        Raises
        ------
        Exception
            If all retry attempts fail (re-raises the last error).
        """
        last_error: Exception | None = None

        for attempt in range(self.retry_config.max_attempts):
            try:
                html = await self._fetch_html(url)
                if attempt > 0:
                    logger.info(
                        "Fetch succeeded after retry",
                        url=url,
                        attempt=attempt + 1,
                    )
                return html

            except Exception as e:
                last_error = e
                logger.warning(
                    "Fetch failed, will retry",
                    url=url,
                    attempt=attempt + 1,
                    max_attempts=self.retry_config.max_attempts,
                    error=str(e),
                )

                # Apply exponential backoff if not the last attempt
                if attempt < self.retry_config.max_attempts - 1:
                    delay = min(
                        self.retry_config.initial_delay
                        * (self.retry_config.exponential_base**attempt),
                        self.retry_config.max_delay,
                    )

                    if self.retry_config.jitter:
                        delay *= 0.5 + random.random()  # nosec B311

                    logger.debug(
                        "Backoff before retry",
                        delay_seconds=delay,
                        next_attempt=attempt + 2,
                    )
                    await asyncio.sleep(delay)

        # All attempts exhausted
        logger.error(
            "All retry attempts failed",
            url=url,
            max_attempts=self.retry_config.max_attempts,
        )
        assert last_error is not None
        raise last_error

    # =========================================================================
    # Context Manager
    # =========================================================================

    async def __aenter__(self) -> BaseScraper:
        """Start async context manager.

        Returns
        -------
        BaseScraper
            Self for use in async with statement.
        """
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: Any,
    ) -> None:
        """Close async context manager and release all resources.

        Parameters
        ----------
        exc_type : type[BaseException] | None
            Exception type if an exception was raised.
        exc_val : BaseException | None
            Exception value if an exception was raised.
        exc_tb : Any
            Exception traceback if an exception was raised.
        """
        await self.close()

    async def close(self) -> None:
        """Close all resources (session, browser, playwright).

        Safely releases all resources. Can be called multiple times safely.
        """
        if self._session is not None:
            self._session.close()
            self._session = None

        if self._browser is not None:
            await self._browser.close()
            self._browser = None

        if self._playwright is not None:
            await self._playwright.stop()
            self._playwright = None

        logger.debug(
            "BaseScraper resources released",
            source_name=self.source_name,
        )


__all__ = ["BaseScraper"]
