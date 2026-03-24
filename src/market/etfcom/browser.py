"""Playwright-based browser operation Mixin for ETF.com scraping.

This module provides the ``ETFComBrowserMixin`` class, a Mixin that adds
Playwright-based browser automation capabilities for scraping ETF.com pages
that require JavaScript rendering (e.g. the ETF screener page).

The Mixin provides stealth browser configuration to avoid bot detection,
polite navigation delays, cookie consent handling, pagination support,
and retry logic with exponential backoff.

Features
--------
- Stealth browser context (viewport, User-Agent, locale, timezone, init script)
- navigator.webdriver hiding, WebGL vendor/renderer spoofing, chrome.runtime
- Polite delay between navigations
- Cookie consent auto-acceptance
- Display-100 pagination support
- Retry with exponential backoff via RetryConfig
- Async context manager for resource management

Examples
--------
>>> from market.etfcom.browser import ETFComBrowserMixin
>>> from market.etfcom.types import ScrapingConfig
>>>
>>> async with ETFComBrowserMixin() as browser:
...     html = await browser._get_page_html("https://www.etf.com/SPY")
...     print(len(html))

See Also
--------
news.extractors.playwright : Similar Playwright pattern for news extraction.
market.etfcom.session : curl_cffi-based session for non-JS pages.
market.etfcom.constants : Stealth settings and CSS selectors.
market.etfcom.types : ScrapingConfig and RetryConfig dataclasses.
market.etfcom.errors : ETFComTimeoutError, ETFComNotFoundError for error handling.
"""

from __future__ import annotations

import asyncio
import random
from typing import Any

from market.etfcom.constants import DEFAULT_USER_AGENTS
from market.etfcom.errors import ETFComNotFoundError, ETFComTimeoutError
from market.etfcom.types import RetryConfig, ScrapingConfig
from utils_core.logging import get_logger

# AIDEV-NOTE: Legacy Playwright constants inlined after removal from constants.py
# (Wave 1 API migration). Will be removed when browser.py is rewritten in later Waves.
_LEGACY_STEALTH_VIEWPORT: dict[str, int] = {"width": 1920, "height": 1080}
_LEGACY_STEALTH_INIT_SCRIPT: str = """\
// Hide navigator.webdriver property
Object.defineProperty(navigator, 'webdriver', {
    get: () => undefined,
});

// Override WebGL vendor and renderer
const getParameter = WebGLRenderingContext.prototype.getParameter;
WebGLRenderingContext.prototype.getParameter = function(parameter) {
    if (parameter === 37445) {
        return 'Intel Inc.';
    }
    if (parameter === 37446) {
        return 'Intel Iris OpenGL Engine';
    }
    return getParameter.call(this, parameter);
};

// Add chrome.runtime to appear as a Chrome extension environment
if (!window.chrome) {
    window.chrome = {};
}
if (!window.chrome.runtime) {
    window.chrome.runtime = {};
}
"""
_LEGACY_COOKIE_CONSENT_SELECTOR: str = "button#onetrust-accept-btn-handler"
_LEGACY_DISPLAY_100_SELECTOR: str = "select.per-page-select option[value='100']"

logger = get_logger(__name__)


def _get_async_playwright() -> Any:
    """Import and return async_playwright from playwright.

    Returns
    -------
    Any
        The async_playwright context manager from playwright.

    Raises
    ------
    ImportError
        If playwright is not installed.
    """
    try:
        from playwright.async_api import (  # type: ignore[import-not-found]
            async_playwright as _async_playwright,
        )

        return _async_playwright()
    except ImportError as e:
        raise ImportError(
            "playwright is not installed. "
            "Install with: uv add playwright && playwright install chromium"
        ) from e


class ETFComBrowserMixin:
    """Playwright-based browser operation Mixin for ETF.com scraping.

    Provides stealth browser configuration, polite navigation, cookie consent
    handling, pagination support, and retry logic with exponential backoff.
    Designed to be used by FundamentalsCollector and FundFlowsCollector as a
    fallback when curl_cffi fails.

    Parameters
    ----------
    config : ScrapingConfig | None
        Scraping configuration. If None, defaults are used.
    retry_config : RetryConfig | None
        Retry configuration. If None, defaults are used.

    Attributes
    ----------
    _config : ScrapingConfig
        The scraping configuration.
    _retry_config : RetryConfig
        The retry configuration.
    _playwright : Any | None
        The Playwright instance (None until ``_ensure_browser()`` is called).
    _browser : Any | None
        The browser instance (None until ``_ensure_browser()`` is called).
    _context : Any | None
        The current stealth browser context (None until created).
    _user_agents : list[str]
        User-Agent strings for rotation.

    Examples
    --------
    >>> async with ETFComBrowserMixin() as browser:
    ...     html = await browser._get_page_html("https://www.etf.com/SPY")

    >>> mixin = ETFComBrowserMixin(config=ScrapingConfig(headless=False))
    >>> await mixin._ensure_browser()
    >>> page = await mixin._navigate("https://www.etf.com/SPY")
    >>> await mixin.close()
    """

    def __init__(
        self,
        config: ScrapingConfig | None = None,
        retry_config: RetryConfig | None = None,
    ) -> None:
        """Initialize ETFComBrowserMixin with configuration.

        Parameters
        ----------
        config : ScrapingConfig | None
            Scraping configuration. Defaults to ``ScrapingConfig()``.
        retry_config : RetryConfig | None
            Retry configuration. Defaults to ``RetryConfig()``.
        """
        self._config: ScrapingConfig = config or ScrapingConfig()
        self._retry_config: RetryConfig = retry_config or RetryConfig()

        # Resolve user agents: use config value or fall back to defaults
        self._user_agents: list[str] = (
            list(self._config.user_agents)
            if self._config.user_agents
            else list(DEFAULT_USER_AGENTS)
        )

        # Playwright resources (initialized lazily)
        self._playwright: Any | None = None
        self._browser: Any | None = None
        self._context: Any | None = None

        logger.info(
            "ETFComBrowserMixin initialized",
            headless=self._config.headless,
            polite_delay=self._config.polite_delay,
            delay_jitter=self._config.delay_jitter,
            timeout=self._config.timeout,
            max_retry_attempts=self._retry_config.max_attempts,
        )

    async def __aenter__(self) -> ETFComBrowserMixin:
        """Start async context manager and ensure browser is ready.

        Returns
        -------
        ETFComBrowserMixin
            Self for use in async with statement.
        """
        await self._ensure_browser()
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

    async def _ensure_browser(self) -> None:
        """Ensure the Playwright browser instance is running.

        Launches a Chromium browser in the configured headless mode.
        Subsequent calls are no-ops if the browser is already running.

        Raises
        ------
        ImportError
            If playwright is not installed.
        """
        if self._browser is not None:
            return

        pw_context_manager = _get_async_playwright()
        playwright = await pw_context_manager.start()
        self._playwright = playwright

        self._browser = await playwright.chromium.launch(
            headless=self._config.headless,
        )

        logger.debug(
            "Playwright browser started",
            headless=self._config.headless,
        )

    async def _create_stealth_context(self) -> Any:
        """Create a new stealth browser context with anti-detection settings.

        Configures the context with:

        - Viewport: 1920x1080 (common desktop resolution)
        - User-Agent: Randomly selected from the configured list
        - Locale: en-US
        - Timezone: America/New_York
        - Init script: _LEGACY_STEALTH_INIT_SCRIPT (hides webdriver, spoofs WebGL, adds
          chrome.runtime)

        Returns
        -------
        Any
            A Playwright BrowserContext with stealth settings applied.

        Raises
        ------
        RuntimeError
            If ``_ensure_browser()`` has not been called.
        """
        if self._browser is None:
            msg = "Browser not initialized. Call _ensure_browser() first."
            raise RuntimeError(msg)

        user_agent = random.choice(self._user_agents)  # nosec B311

        context = await self._browser.new_context(
            viewport=_LEGACY_STEALTH_VIEWPORT,
            user_agent=user_agent,
            locale="en-US",
            timezone_id="America/New_York",
        )

        # Inject stealth init script into every new page
        await context.add_init_script(_LEGACY_STEALTH_INIT_SCRIPT)

        self._context = context

        logger.debug(
            "Stealth context created",
            viewport=_LEGACY_STEALTH_VIEWPORT,
            user_agent=user_agent[:50],
            locale="en-US",
            timezone="America/New_York",
        )

        return context

    async def _navigate(
        self,
        url: str,
        wait_until: str = "networkidle",
    ) -> Any:
        """Navigate to a URL with polite delay and stealth context.

        Creates a new stealth context and page, applies a polite delay,
        then navigates to the specified URL.

        Parameters
        ----------
        url : str
            The URL to navigate to.
        wait_until : str
            The Playwright wait condition (default: ``'networkidle'``).

        Returns
        -------
        Any
            The Playwright Page object after navigation.

        Raises
        ------
        ETFComTimeoutError
            If the page load exceeds the configured timeout.
        ETFComNotFoundError
            If the page returns HTTP 404 or a ``TargetClosedError`` occurs.
        """
        # Apply polite delay
        delay = self._config.polite_delay + random.uniform(  # nosec B311
            0, self._config.delay_jitter
        )
        await asyncio.sleep(delay)
        logger.debug("Polite delay applied", delay_seconds=delay, url=url)

        # Create stealth context and page
        context = await self._create_stealth_context()
        page = await context.new_page()

        timeout_ms = self._config.timeout * 1000

        try:
            response = await page.goto(url, timeout=timeout_ms, wait_until=wait_until)

            # Check for HTTP 404
            if response is not None and response.status == 404:
                logger.warning(
                    "HTTP 404 Not Found",
                    url=url,
                    status_code=404,
                )
                await page.close()
                raise ETFComNotFoundError(
                    "HTTP 404 Not Found",
                    url=url,
                )

            logger.debug(
                "Navigation completed",
                url=url,
                wait_until=wait_until,
            )
            return page
        except ETFComNotFoundError:
            raise
        except (asyncio.TimeoutError, Exception) as e:
            # Close the page on failure
            await page.close()

            if isinstance(e, asyncio.TimeoutError):
                logger.warning(
                    "Navigation timed out",
                    url=url,
                    timeout_seconds=self._config.timeout,
                )
                raise ETFComTimeoutError(
                    f"Page load timed out after {self._config.timeout}s",
                    url=url,
                    timeout_seconds=self._config.timeout,
                ) from e

            # AIDEV-NOTE: playwright is an optional dependency and may not be
            # imported at module level. Checking by class name avoids a hard
            # import of playwright.async_api.TargetClosedError.
            if type(e).__name__ == "TargetClosedError":
                logger.warning(
                    "TargetClosedError detected, wrapping as NotFound",
                    url=url,
                    error_type=type(e).__name__,
                )
                raise ETFComNotFoundError(
                    "Target closed (likely 404 redirect)",
                    url=url,
                ) from e

            logger.error(
                "Navigation failed",
                url=url,
                error=str(e),
            )
            raise

    async def _get_page_html(self, url: str) -> str:
        """Get the full HTML content of a page.

        Navigates to the URL and returns the page HTML. The page is
        closed after content extraction.

        Parameters
        ----------
        url : str
            The URL to fetch HTML from.

        Returns
        -------
        str
            The full HTML content of the page.

        Raises
        ------
        ETFComTimeoutError
            If the page load exceeds the configured timeout.
        ETFComNotFoundError
            If the page returns HTTP 404 or a ``TargetClosedError`` occurs.
        """
        page = await self._navigate(url)
        try:
            html: str = await page.content()
            logger.debug(
                "Page HTML retrieved",
                url=url,
                html_length=len(html),
            )
            return html
        finally:
            await page.close()

    async def _get_page_html_with_retry(self, url: str) -> str:
        """Get page HTML with retry and exponential backoff.

        Retries the page fetch according to ``RetryConfig`` settings
        when ``ETFComTimeoutError`` is raised.

        Parameters
        ----------
        url : str
            The URL to fetch HTML from.

        Returns
        -------
        str
            The full HTML content of the page.

        Raises
        ------
        ETFComTimeoutError
            If all retry attempts fail.
        """
        last_error: ETFComTimeoutError | None = None

        for attempt in range(self._retry_config.max_attempts):
            try:
                html = await self._get_page_html(url)
                if attempt > 0:
                    logger.info(
                        "Page fetch succeeded after retry",
                        url=url,
                        attempt=attempt + 1,
                    )
                return html

            except ETFComTimeoutError as e:
                last_error = e
                logger.warning(
                    "Page fetch failed, will retry",
                    url=url,
                    attempt=attempt + 1,
                    max_attempts=self._retry_config.max_attempts,
                )

                # If not the last attempt, apply exponential backoff
                if attempt < self._retry_config.max_attempts - 1:
                    delay = min(
                        self._retry_config.initial_delay
                        * (self._retry_config.exponential_base**attempt),
                        self._retry_config.max_delay,
                    )

                    if self._retry_config.jitter:
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
            max_attempts=self._retry_config.max_attempts,
        )
        if last_error is None:
            raise RuntimeError("Retry loop exited without capturing an error")
        raise last_error

    async def _accept_cookies(self, page: Any) -> None:
        """Accept cookie consent dialog if present.

        Clicks the cookie consent accept button if found on the page.
        Silently returns if the button is not found or an error occurs.

        Parameters
        ----------
        page : Any
            The Playwright Page object.
        """
        try:
            button = await page.query_selector(_LEGACY_COOKIE_CONSENT_SELECTOR)
            if button:
                await button.click()
                logger.debug("Cookie consent accepted")
            else:
                logger.debug("Cookie consent button not found, skipping")
        except Exception:  # nosec B110
            # Cookie consent is non-critical; log and continue
            logger.debug("Cookie consent handling failed, continuing")

    async def _wait_for_content_loaded(
        self,
        page: Any,
        selector: str,
    ) -> None:
        """Wait for a specific element to appear on the page.

        Parameters
        ----------
        page : Any
            The Playwright Page object.
        selector : str
            The CSS selector to wait for.

        Raises
        ------
        ETFComTimeoutError
            If the element does not appear within the timeout.
        """
        timeout_ms = self._config.timeout * 1000
        try:
            await page.wait_for_selector(selector, timeout=timeout_ms)
            logger.debug(
                "Content loaded",
                selector=selector,
            )
        except (asyncio.TimeoutError, Exception) as e:
            if isinstance(e, asyncio.TimeoutError):
                raise ETFComTimeoutError(
                    f"Waiting for selector '{selector}' timed out",
                    url=None,
                    timeout_seconds=self._config.timeout,
                ) from e
            raise

    async def _click_display_100(self, page: Any) -> None:
        """Click the 'Display 100' pagination option if present.

        Selects the option to display 100 results per page on the
        ETF.com screener. Silently returns if the element is not found.

        Parameters
        ----------
        page : Any
            The Playwright Page object.
        """
        try:
            element = await page.query_selector(_LEGACY_DISPLAY_100_SELECTOR)
            if element:
                await element.click()
                logger.debug("Display 100 option selected")
            else:
                logger.debug("Display 100 option not found, skipping")
        except Exception:  # nosec B110
            logger.debug("Display 100 selection failed, continuing")

    async def close(self) -> None:
        """Close the browser, context, and Playwright instances.

        Safely releases all Playwright resources. Can be called
        multiple times safely.
        """
        if self._context:
            await self._context.close()
            self._context = None

        if self._browser:
            await self._browser.close()
            self._browser = None

        if self._playwright:
            await self._playwright.stop()
            self._playwright = None

        logger.debug("ETFComBrowserMixin resources released")


__all__ = ["ETFComBrowserMixin"]
