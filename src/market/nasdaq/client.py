"""High-level API client for the NASDAQ API.

This module provides the ``NasdaqClient`` class, a typed client
for accessing NASDAQ API endpoints (quote, chart, earnings calendar,
dividends calendar, institutional holdings, insider trades, SEC filings,
analyst forecasts, company profile, and stock screener).

The ``_fetch_and_parse()`` DRY helper keeps each public method to ~3 lines:
URL construction, parser selection, and TTL specification.

Features include:

- Session + SQLiteCache dependency injection
- ``_fetch_and_parse[T]()`` for DRY cache hit / cache miss handling
- ``_validate_symbol()`` for input validation
- ``_build_referer()`` for per-endpoint Referer headers
- Context manager support

Examples
--------
>>> from market.nasdaq.client import NasdaqClient
>>> with NasdaqClient() as client:
...     pass  # endpoint methods will be added in subsequent Waves

See Also
--------
market.alphavantage.client : Reference implementation for Session + Cache DI pattern.
market.nasdaq.session : Underlying HTTP session with bot-blocking countermeasures.
market.nasdaq.client_cache : TTL constants and cache helper.
market.nasdaq.client_parsers : Response parsing helpers.
"""

from __future__ import annotations

import re
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from collections.abc import Callable

    from market.cache.cache import SQLiteCache
    from market.nasdaq.types import NasdaqConfig, RetryConfig

from market.cache.cache import generate_cache_key
from market.nasdaq.client_cache import (
    DIVIDENDS_CALENDAR_TTL,
    EARNINGS_CALENDAR_TTL,
    IPO_CALENDAR_TTL,
    SPLITS_CALENDAR_TTL,
    get_nasdaq_cache,
)
from market.nasdaq.client_parsers import (
    parse_dividends_calendar,
    parse_earnings_calendar,
    parse_ipo_calendar,
    parse_splits_calendar,
    unwrap_envelope,
)
from market.nasdaq.client_types import (
    DividendCalendarRecord,
    EarningsRecord,
    IpoRecord,
    NasdaqFetchOptions,
    SplitRecord,
)
from market.nasdaq.constants import (
    DIVIDENDS_CALENDAR_URL,
    EARNINGS_CALENDAR_URL,
    IPO_CALENDAR_URL,
    NASDAQ_API_BASE,
    SPLITS_CALENDAR_URL,
)
from market.nasdaq.session import NasdaqSession
from utils_core.logging import get_logger

logger = get_logger(__name__)

# Regex for symbol validation: 1-10 alphanumeric characters, dot, or hyphen
_SYMBOL_PATTERN: re.Pattern[str] = re.compile(r"^[A-Za-z0-9.\-]{1,10}$")


class NasdaqClient:
    """High-level typed API client for the NASDAQ API.

    Provides a foundation for accessing NASDAQ API endpoints with
    caching, input validation, and session management.  Endpoint-specific
    methods will be added in subsequent Waves.

    Parameters
    ----------
    session : NasdaqSession | None
        NASDAQ HTTP session. If ``None``, a default session is created.
    config : NasdaqConfig | None
        NASDAQ configuration (used only when ``session`` is ``None``).
    retry_config : RetryConfig | None
        Retry configuration (used only when ``session`` is ``None``).
    cache : SQLiteCache | None
        Cache instance. If ``None``, a default persistent cache is created.

    Examples
    --------
    >>> with NasdaqClient() as client:
    ...     pass  # endpoint methods will be added in subsequent Waves

    >>> from market.nasdaq.session import NasdaqSession
    >>> from market.cache.cache import SQLiteCache
    >>> session = NasdaqSession()
    >>> cache = SQLiteCache()
    >>> client = NasdaqClient(session=session, cache=cache)
    >>> client.close()
    """

    def __init__(
        self,
        session: NasdaqSession | None = None,
        config: NasdaqConfig | None = None,
        retry_config: RetryConfig | None = None,
        cache: SQLiteCache | None = None,
    ) -> None:
        self._session: NasdaqSession = session or NasdaqSession(
            config=config, retry_config=retry_config
        )
        self._cache: SQLiteCache = cache or get_nasdaq_cache()
        self._owns_session: bool = session is None

        logger.info("NasdaqClient initialized")

    # =========================================================================
    # Context Manager
    # =========================================================================

    def __enter__(self) -> NasdaqClient:
        """Support context manager protocol.

        Returns
        -------
        NasdaqClient
            Self for use in ``with`` statement.
        """
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: Any,
    ) -> None:
        """Close client on context exit.

        Parameters
        ----------
        exc_type : type[BaseException] | None
            Exception type if an exception was raised.
        exc_val : BaseException | None
            Exception instance if an exception was raised.
        exc_tb : Any
            Traceback if an exception was raised.
        """
        self.close()

    def close(self) -> None:
        """Close the client and release resources.

        Only closes the underlying session if the client owns it
        (i.e., the session was not injected via constructor).
        """
        if self._owns_session:
            self._session.close()
        logger.debug("NasdaqClient closed")

    # =========================================================================
    # Core DRY Helper
    # =========================================================================

    def _fetch_and_parse[T](
        self,
        url: str,
        cache_key: str,
        parser: Callable[[dict[str, Any]], T],
        ttl: int,
        options: NasdaqFetchOptions | None = None,
        params: dict[str, str] | None = None,
    ) -> T:
        """Fetch data from cache or NASDAQ API with DRY cache management.

        This is the core DRY helper that every public method delegates to.
        It handles the cache hit / cache miss / force refresh logic, API
        fetch with retry, envelope unwrapping, and result parsing.

        Parameters
        ----------
        url : str
            The NASDAQ API endpoint URL.
        cache_key : str
            Cache key for this request.
        parser : Callable[[dict[str, Any]], T]
            Function to parse the unwrapped ``data`` payload.
        ttl : int
            Cache TTL in seconds.
        options : NasdaqFetchOptions | None
            Fetch options (cache control). Defaults to using cache.
        params : dict[str, str] | None
            Optional query parameters for the request.

        Returns
        -------
        T
            Parsed result (DataFrame, dict, list, etc.).

        Raises
        ------
        NasdaqAPIError
            If the API returns a non-200 rCode.
        NasdaqRateLimitError
            If the API rate limit is exceeded after all retries.
        NasdaqParseError
            If the response cannot be parsed.
        """
        options = options or NasdaqFetchOptions()

        # Check cache
        if options.use_cache and not options.force_refresh:
            cached = self._cache.get(cache_key)
            if cached is not None:
                logger.debug("Cache hit", cache_key=cache_key)
                return cached

        # Fetch from API
        logger.debug("Fetching from NASDAQ API", url=url, params=params)
        response = self._session.get_with_retry(url, params=params)
        raw_data: dict[str, Any] = response.json()

        # Unwrap envelope
        data = unwrap_envelope(raw_data, url)

        # Parse
        result = parser(data)

        # Store in cache
        self._cache.set(cache_key, result, ttl=ttl)
        logger.info(
            "Data fetched and cached",
            cache_key=cache_key,
            ttl=ttl,
        )

        return result

    # =========================================================================
    # Validation Helpers
    # =========================================================================

    @staticmethod
    def _validate_symbol(symbol: str) -> None:
        """Validate a stock ticker symbol format.

        Valid symbols are 1-10 characters consisting of letters, digits,
        dots (e.g. ``BRK.B``), or hyphens (e.g. ``BF-B``).

        Parameters
        ----------
        symbol : str
            The ticker symbol to validate.

        Raises
        ------
        ValueError
            If the symbol is empty, too long, or contains invalid characters.

        Examples
        --------
        >>> NasdaqClient._validate_symbol("AAPL")  # OK
        >>> NasdaqClient._validate_symbol("BRK.B")  # OK
        >>> NasdaqClient._validate_symbol("")  # raises ValueError
        Traceback (most recent call last):
            ...
        ValueError: Symbol must not be empty
        """
        if not symbol or not symbol.strip():
            raise ValueError("Symbol must not be empty")

        stripped = symbol.strip()
        if len(stripped) > 10:
            raise ValueError(
                f"Symbol must be 1-10 characters, got '{symbol}' ({len(stripped)} chars)"
            )

        if not _SYMBOL_PATTERN.match(stripped):
            raise ValueError(
                f"Symbol must be alphanumeric (plus dot/hyphen), got '{symbol}'"
            )

    # =========================================================================
    # URL Helpers
    # =========================================================================

    @staticmethod
    def _build_referer(symbol: str | None = None) -> str:
        """Build a Referer header URL for a NASDAQ API request.

        Constructs a plausible Referer URL that mimics browser navigation
        on the NASDAQ website, which helps avoid bot detection.

        Parameters
        ----------
        symbol : str | None
            If provided, constructs a symbol-specific Referer URL.
            If ``None``, returns the generic NASDAQ market activity page.

        Returns
        -------
        str
            A Referer URL string.

        Examples
        --------
        >>> NasdaqClient._build_referer("AAPL")
        'https://www.nasdaq.com/market-activity/stocks/aapl'

        >>> NasdaqClient._build_referer()
        'https://www.nasdaq.com/market-activity'
        """
        if symbol:
            return f"https://www.nasdaq.com/market-activity/stocks/{symbol.lower()}"
        return "https://www.nasdaq.com/market-activity"

    # =========================================================================
    # Calendar Endpoints
    # =========================================================================

    def get_earnings_calendar(
        self,
        date: str,
        options: NasdaqFetchOptions | None = None,
    ) -> list[EarningsRecord]:
        """Fetch earnings calendar data for a specific date.

        Parameters
        ----------
        date : str
            Date string (e.g. ``"2026-01-30"``).
        options : NasdaqFetchOptions | None
            Fetch options (cache control). Defaults to using cache.

        Returns
        -------
        list[EarningsRecord]
            List of earnings records for the given date.

        Raises
        ------
        NasdaqAPIError
            If the API returns a non-200 rCode.
        NasdaqParseError
            If the response cannot be parsed.

        Examples
        --------
        >>> with NasdaqClient() as client:
        ...     records = client.get_earnings_calendar(date="2026-01-30")
        """
        cache_key = f"nasdaq:calendar:earnings:{date}"
        return self._fetch_and_parse(
            url=EARNINGS_CALENDAR_URL,
            cache_key=cache_key,
            parser=parse_earnings_calendar,
            ttl=EARNINGS_CALENDAR_TTL,
            options=options,
            params={"date": date},
        )

    def get_dividends_calendar(
        self,
        date: str,
        options: NasdaqFetchOptions | None = None,
    ) -> list[DividendCalendarRecord]:
        """Fetch dividends calendar data for a specific date.

        Parameters
        ----------
        date : str
            Date string (e.g. ``"2026-02-07"``).
        options : NasdaqFetchOptions | None
            Fetch options (cache control). Defaults to using cache.

        Returns
        -------
        list[DividendCalendarRecord]
            List of dividend records for the given date.

        Raises
        ------
        NasdaqAPIError
            If the API returns a non-200 rCode.
        NasdaqParseError
            If the response cannot be parsed.

        Examples
        --------
        >>> with NasdaqClient() as client:
        ...     records = client.get_dividends_calendar(date="2026-02-07")
        """
        cache_key = f"nasdaq:calendar:dividends:{date}"
        return self._fetch_and_parse(
            url=DIVIDENDS_CALENDAR_URL,
            cache_key=cache_key,
            parser=parse_dividends_calendar,
            ttl=DIVIDENDS_CALENDAR_TTL,
            options=options,
            params={"date": date},
        )

    def get_splits_calendar(
        self,
        date: str,
        options: NasdaqFetchOptions | None = None,
    ) -> list[SplitRecord]:
        """Fetch stock splits calendar data for a specific date.

        Parameters
        ----------
        date : str
            Date string (e.g. ``"2024-06-10"``).
        options : NasdaqFetchOptions | None
            Fetch options (cache control). Defaults to using cache.

        Returns
        -------
        list[SplitRecord]
            List of split records for the given date.

        Raises
        ------
        NasdaqAPIError
            If the API returns a non-200 rCode.
        NasdaqParseError
            If the response cannot be parsed.

        Examples
        --------
        >>> with NasdaqClient() as client:
        ...     records = client.get_splits_calendar(date="2024-06-10")
        """
        cache_key = f"nasdaq:calendar:splits:{date}"
        return self._fetch_and_parse(
            url=SPLITS_CALENDAR_URL,
            cache_key=cache_key,
            parser=parse_splits_calendar,
            ttl=SPLITS_CALENDAR_TTL,
            options=options,
            params={"date": date},
        )

    def get_ipo_calendar(
        self,
        year_month: str,
        options: NasdaqFetchOptions | None = None,
    ) -> list[IpoRecord]:
        """Fetch IPO calendar data for a specific year-month.

        Parameters
        ----------
        year_month : str
            Year-month string (e.g. ``"2026-03"``).
        options : NasdaqFetchOptions | None
            Fetch options (cache control). Defaults to using cache.

        Returns
        -------
        list[IpoRecord]
            List of IPO records for the given year-month.

        Raises
        ------
        NasdaqAPIError
            If the API returns a non-200 rCode.
        NasdaqParseError
            If the response cannot be parsed.

        Examples
        --------
        >>> with NasdaqClient() as client:
        ...     records = client.get_ipo_calendar(year_month="2026-03")
        """
        cache_key = f"nasdaq:calendar:ipo:{year_month}"
        return self._fetch_and_parse(
            url=IPO_CALENDAR_URL,
            cache_key=cache_key,
            parser=parse_ipo_calendar,
            ttl=IPO_CALENDAR_TTL,
            options=options,
            params={"date": year_month},
        )


__all__ = ["NasdaqClient"]
