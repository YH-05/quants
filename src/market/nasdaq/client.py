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
    ANALYST_EARNINGS_DATE_TTL,
    ANALYST_FORECAST_TTL,
    ANALYST_RATINGS_TTL,
    ANALYST_TARGET_PRICE_TTL,
    DIVIDENDS_CALENDAR_TTL,
    EARNINGS_CALENDAR_TTL,
    ETF_SCREENER_TTL,
    FINANCIALS_TTL,
    INSIDER_TRADES_TTL,
    INSTITUTIONAL_HOLDINGS_TTL,
    IPO_CALENDAR_TTL,
    MARKET_MOVERS_TTL,
    SPLITS_CALENDAR_TTL,
    get_nasdaq_cache,
)
from market.nasdaq.client_parsers import (
    parse_analyst_ratings,
    parse_dividends_calendar,
    parse_earnings_calendar,
    parse_earnings_date,
    parse_earnings_forecast,
    parse_etf_screener,
    parse_financials,
    parse_insider_trades,
    parse_institutional_holdings,
    parse_ipo_calendar,
    parse_market_movers,
    parse_splits_calendar,
    parse_target_price,
    unwrap_envelope,
)
from market.nasdaq.client_types import (
    AnalystRatings,
    AnalystSummary,
    DividendCalendarRecord,
    EarningsDate,
    EarningsForecast,
    EarningsRecord,
    EtfRecord,
    FinancialStatement,
    InsiderTrade,
    InstitutionalHolding,
    IpoRecord,
    MarketMover,
    NasdaqFetchOptions,
    SplitRecord,
    TargetPrice,
)
from market.nasdaq.constants import (
    ANALYST_EARNINGS_DATE_URL,
    ANALYST_FORECAST_URL,
    ANALYST_RATINGS_URL,
    ANALYST_TARGET_PRICE_URL,
    DIVIDENDS_CALENDAR_URL,
    EARNINGS_CALENDAR_URL,
    ETF_SCREENER_URL,
    FINANCIALS_URL,
    INSIDER_TRADES_URL,
    INSTITUTIONAL_HOLDINGS_URL,
    IPO_CALENDAR_URL,
    MARKET_MOVERS_URL,
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

    # =========================================================================
    # Market Movers / ETF Endpoints
    # =========================================================================

    def get_market_movers(
        self,
        options: NasdaqFetchOptions | None = None,
    ) -> dict[str, list[MarketMover]]:
        """Fetch market movers data (gainers, losers, most active).

        Parameters
        ----------
        options : NasdaqFetchOptions | None
            Fetch options (cache control). Defaults to using cache.

        Returns
        -------
        dict[str, list[MarketMover]]
            A dictionary keyed by section name (``"most_advanced"``,
            ``"most_declined"``, ``"most_active"``), each mapping to a
            list of ``MarketMover`` records.

        Raises
        ------
        NasdaqAPIError
            If the API returns a non-200 rCode.
        NasdaqParseError
            If the response cannot be parsed.

        Examples
        --------
        >>> with NasdaqClient() as client:
        ...     movers = client.get_market_movers()
        ...     gainers = movers["most_advanced"]
        """
        cache_key = "nasdaq:market_movers"
        return self._fetch_and_parse(
            url=MARKET_MOVERS_URL,
            cache_key=cache_key,
            parser=parse_market_movers,
            ttl=MARKET_MOVERS_TTL,
            options=options,
        )

    def get_etf_screener(
        self,
        options: NasdaqFetchOptions | None = None,
    ) -> list[EtfRecord]:
        """Fetch ETF screener data.

        Parameters
        ----------
        options : NasdaqFetchOptions | None
            Fetch options (cache control). Defaults to using cache.

        Returns
        -------
        list[EtfRecord]
            List of ETF records from the screener.

        Raises
        ------
        NasdaqAPIError
            If the API returns a non-200 rCode.
        NasdaqParseError
            If the response cannot be parsed.

        Examples
        --------
        >>> with NasdaqClient() as client:
        ...     etfs = client.get_etf_screener()
        """
        cache_key = "nasdaq:etf_screener"
        return self._fetch_and_parse(
            url=ETF_SCREENER_URL,
            cache_key=cache_key,
            parser=parse_etf_screener,
            ttl=ETF_SCREENER_TTL,
            options=options,
            params={"limit": "0"},
        )

    # =========================================================================
    # Company Data Endpoints
    # =========================================================================

    def get_insider_trades(
        self,
        symbol: str,
        options: NasdaqFetchOptions | None = None,
    ) -> list[InsiderTrade]:
        """Fetch insider trades data for a symbol.

        Returns a list of insider trade records including insider name,
        transaction type, shares traded, price, and value.

        Parameters
        ----------
        symbol : str
            Ticker symbol (e.g. ``"AAPL"``).
        options : NasdaqFetchOptions | None
            Fetch options (cache control). Defaults to using cache.

        Returns
        -------
        list[InsiderTrade]
            List of insider trade records.

        Raises
        ------
        ValueError
            If the symbol is empty or invalid.
        NasdaqAPIError
            If the API returns a non-200 rCode.
        NasdaqParseError
            If the response cannot be parsed.

        Examples
        --------
        >>> with NasdaqClient() as client:
        ...     trades = client.get_insider_trades("AAPL")
        """
        self._validate_symbol(symbol)
        upper = symbol.strip().upper()
        cache_key = f"nasdaq:company:insider_trades:{upper}"
        url = INSIDER_TRADES_URL.format(symbol=upper)

        return self._fetch_and_parse(
            url=url,
            cache_key=cache_key,
            parser=parse_insider_trades,
            ttl=INSIDER_TRADES_TTL,
            options=options,
        )

    def get_institutional_holdings(
        self,
        symbol: str,
        options: NasdaqFetchOptions | None = None,
    ) -> list[InstitutionalHolding]:
        """Fetch institutional holdings data for a symbol.

        Returns a list of institutional holding records including
        holder name, shares, market value, and filing information.

        Parameters
        ----------
        symbol : str
            Ticker symbol (e.g. ``"AAPL"``).
        options : NasdaqFetchOptions | None
            Fetch options (cache control). Defaults to using cache.

        Returns
        -------
        list[InstitutionalHolding]
            List of institutional holding records.

        Raises
        ------
        ValueError
            If the symbol is empty or invalid.
        NasdaqAPIError
            If the API returns a non-200 rCode.
        NasdaqParseError
            If the response cannot be parsed.

        Examples
        --------
        >>> with NasdaqClient() as client:
        ...     holdings = client.get_institutional_holdings("AAPL")
        """
        self._validate_symbol(symbol)
        upper = symbol.strip().upper()
        cache_key = f"nasdaq:company:institutional_holdings:{upper}"
        url = INSTITUTIONAL_HOLDINGS_URL.format(symbol=upper)

        return self._fetch_and_parse(
            url=url,
            cache_key=cache_key,
            parser=parse_institutional_holdings,
            ttl=INSTITUTIONAL_HOLDINGS_TTL,
            options=options,
        )

    def get_financials(
        self,
        symbol: str,
        frequency: str = "annual",
        options: NasdaqFetchOptions | None = None,
    ) -> FinancialStatement:
        """Fetch financial statements data for a symbol.

        Returns income statement, balance sheet, and cash flow statement
        data for the given frequency (annual or quarterly).

        Parameters
        ----------
        symbol : str
            Ticker symbol (e.g. ``"AAPL"``).
        frequency : str
            Data frequency, either ``"annual"`` or ``"quarterly"``.
            Default is ``"annual"``.
        options : NasdaqFetchOptions | None
            Fetch options (cache control). Defaults to using cache.

        Returns
        -------
        FinancialStatement
            Financial statements with income, balance sheet, and cash flow.

        Raises
        ------
        ValueError
            If the symbol is empty or invalid.
        NasdaqAPIError
            If the API returns a non-200 rCode.
        NasdaqParseError
            If the response cannot be parsed.

        Examples
        --------
        >>> with NasdaqClient() as client:
        ...     financials = client.get_financials("AAPL")
        ...     quarterly = client.get_financials("AAPL", frequency="quarterly")
        """
        self._validate_symbol(symbol)
        upper = symbol.strip().upper()
        cache_key = f"nasdaq:company:financials:{upper}:{frequency}"
        url = FINANCIALS_URL.format(symbol=upper)

        def parser(data: dict[str, Any]) -> FinancialStatement:
            return parse_financials(data, symbol=upper, frequency=frequency)

        return self._fetch_and_parse(
            url=url,
            cache_key=cache_key,
            parser=parser,
            ttl=FINANCIALS_TTL,
            options=options,
            params={"frequency": frequency},
        )

    # =========================================================================
    # Analyst Endpoints
    # =========================================================================

    def get_earnings_forecast(
        self,
        symbol: str,
        options: NasdaqFetchOptions | None = None,
    ) -> EarningsForecast:
        """Fetch earnings forecast data for a symbol.

        Returns yearly and quarterly EPS forecasts with consensus estimates,
        number of analysts, and high/low ranges.

        Parameters
        ----------
        symbol : str
            Ticker symbol (e.g. ``"AAPL"``).
        options : NasdaqFetchOptions | None
            Fetch options (cache control). Defaults to using cache.

        Returns
        -------
        EarningsForecast
            Earnings forecast with yearly and quarterly periods.

        Raises
        ------
        ValueError
            If the symbol is empty or invalid.
        NasdaqAPIError
            If the API returns a non-200 rCode.
        NasdaqParseError
            If the response cannot be parsed.

        Examples
        --------
        >>> with NasdaqClient() as client:
        ...     forecast = client.get_earnings_forecast("AAPL")
        """
        self._validate_symbol(symbol)
        upper = symbol.strip().upper()
        cache_key = f"nasdaq:analyst:forecast:{upper}"
        url = ANALYST_FORECAST_URL.format(symbol=upper)

        def parser(data: dict[str, Any]) -> EarningsForecast:
            return parse_earnings_forecast(data, symbol=upper)

        return self._fetch_and_parse(
            url=url,
            cache_key=cache_key,
            parser=parser,
            ttl=ANALYST_FORECAST_TTL,
            options=options,
        )

    def get_analyst_ratings(
        self,
        symbol: str,
        options: NasdaqFetchOptions | None = None,
    ) -> AnalystRatings:
        """Fetch analyst ratings data for a symbol.

        Returns buy/sell/hold/strong-buy/strong-sell counts with
        historical snapshots.

        Parameters
        ----------
        symbol : str
            Ticker symbol (e.g. ``"AAPL"``).
        options : NasdaqFetchOptions | None
            Fetch options (cache control). Defaults to using cache.

        Returns
        -------
        AnalystRatings
            Analyst ratings with history.

        Raises
        ------
        ValueError
            If the symbol is empty or invalid.
        NasdaqAPIError
            If the API returns a non-200 rCode.
        NasdaqParseError
            If the response cannot be parsed.

        Examples
        --------
        >>> with NasdaqClient() as client:
        ...     ratings = client.get_analyst_ratings("AAPL")
        """
        self._validate_symbol(symbol)
        upper = symbol.strip().upper()
        cache_key = f"nasdaq:analyst:ratings:{upper}"
        url = ANALYST_RATINGS_URL.format(symbol=upper)

        def parser(data: dict[str, Any]) -> AnalystRatings:
            return parse_analyst_ratings(data, symbol=upper)

        return self._fetch_and_parse(
            url=url,
            cache_key=cache_key,
            parser=parser,
            ttl=ANALYST_RATINGS_TTL,
            options=options,
        )

    def get_target_price(
        self,
        symbol: str,
        options: NasdaqFetchOptions | None = None,
    ) -> TargetPrice:
        """Fetch analyst target price data for a symbol.

        Returns high, low, mean, and median analyst price targets.

        Parameters
        ----------
        symbol : str
            Ticker symbol (e.g. ``"AAPL"``).
        options : NasdaqFetchOptions | None
            Fetch options (cache control). Defaults to using cache.

        Returns
        -------
        TargetPrice
            Target price with high/low/mean/median.

        Raises
        ------
        ValueError
            If the symbol is empty or invalid.
        NasdaqAPIError
            If the API returns a non-200 rCode.
        NasdaqParseError
            If the response cannot be parsed.

        Examples
        --------
        >>> with NasdaqClient() as client:
        ...     tp = client.get_target_price("AAPL")
        """
        self._validate_symbol(symbol)
        upper = symbol.strip().upper()
        cache_key = f"nasdaq:analyst:target_price:{upper}"
        url = ANALYST_TARGET_PRICE_URL.format(symbol=upper)

        def parser(data: dict[str, Any]) -> TargetPrice:
            return parse_target_price(data, symbol=upper)

        return self._fetch_and_parse(
            url=url,
            cache_key=cache_key,
            parser=parser,
            ttl=ANALYST_TARGET_PRICE_TTL,
            options=options,
        )

    def get_earnings_date(
        self,
        symbol: str,
        options: NasdaqFetchOptions | None = None,
    ) -> EarningsDate:
        """Fetch upcoming earnings date information for a symbol.

        Parameters
        ----------
        symbol : str
            Ticker symbol (e.g. ``"AAPL"``).
        options : NasdaqFetchOptions | None
            Fetch options (cache control). Defaults to using cache.

        Returns
        -------
        EarningsDate
            Earnings date information.

        Raises
        ------
        ValueError
            If the symbol is empty or invalid.
        NasdaqAPIError
            If the API returns a non-200 rCode.
        NasdaqParseError
            If the response cannot be parsed.

        Examples
        --------
        >>> with NasdaqClient() as client:
        ...     ed = client.get_earnings_date("AAPL")
        """
        self._validate_symbol(symbol)
        upper = symbol.strip().upper()
        cache_key = f"nasdaq:analyst:earnings_date:{upper}"
        url = ANALYST_EARNINGS_DATE_URL.format(symbol=upper)

        def parser(data: dict[str, Any]) -> EarningsDate:
            return parse_earnings_date(data, symbol=upper)

        return self._fetch_and_parse(
            url=url,
            cache_key=cache_key,
            parser=parser,
            ttl=ANALYST_EARNINGS_DATE_TTL,
            options=options,
        )

    def get_analyst_summary(
        self,
        symbol: str,
        options: NasdaqFetchOptions | None = None,
    ) -> AnalystSummary:
        """Fetch aggregated analyst data for a symbol.

        Calls ``get_earnings_forecast()``, ``get_analyst_ratings()``,
        ``get_target_price()``, and ``get_earnings_date()`` internally
        and combines the results into a single ``AnalystSummary``.

        If any individual endpoint fails, the corresponding field in
        the summary is set to ``None`` and a warning is logged.

        Parameters
        ----------
        symbol : str
            Ticker symbol (e.g. ``"AAPL"``).
        options : NasdaqFetchOptions | None
            Fetch options (cache control). Defaults to using cache.

        Returns
        -------
        AnalystSummary
            Aggregated analyst data.

        Raises
        ------
        ValueError
            If the symbol is empty or invalid.

        Examples
        --------
        >>> with NasdaqClient() as client:
        ...     summary = client.get_analyst_summary("AAPL")
        ...     if summary.target_price:
        ...         print(summary.target_price.mean)
        """
        self._validate_symbol(symbol)
        upper = symbol.strip().upper()

        forecast: EarningsForecast | None = None
        ratings: AnalystRatings | None = None
        target: TargetPrice | None = None
        earnings_dt: EarningsDate | None = None

        try:
            forecast = self.get_earnings_forecast(upper, options=options)
        except Exception:
            logger.warning(
                "Failed to fetch earnings forecast", symbol=upper, exc_info=True
            )

        try:
            ratings = self.get_analyst_ratings(upper, options=options)
        except Exception:
            logger.warning(
                "Failed to fetch analyst ratings", symbol=upper, exc_info=True
            )

        try:
            target = self.get_target_price(upper, options=options)
        except Exception:
            logger.warning("Failed to fetch target price", symbol=upper, exc_info=True)

        try:
            earnings_dt = self.get_earnings_date(upper, options=options)
        except Exception:
            logger.warning("Failed to fetch earnings date", symbol=upper, exc_info=True)

        logger.info(
            "Analyst summary assembled",
            symbol=upper,
            has_forecast=forecast is not None,
            has_ratings=ratings is not None,
            has_target_price=target is not None,
            has_earnings_date=earnings_dt is not None,
        )

        return AnalystSummary(
            symbol=upper,
            forecast=forecast,
            ratings=ratings,
            target_price=target,
            earnings_date=earnings_dt,
        )


__all__ = ["NasdaqClient"]
