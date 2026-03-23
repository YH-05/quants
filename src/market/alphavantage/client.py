"""High-level API client for the Alpha Vantage API.

This module provides the ``AlphaVantageClient`` class, a typed client
covering 6 categories (time series, real-time, fundamentals, forex,
cryptocurrency, economic indicators) with 20+ public methods.

The ``_get_cached_or_fetch()`` DRY helper keeps each method to ~3 lines:
parameter construction, parser selection, and TTL specification.

Features include:

- Session + SQLiteCache dependency injection
- ``_get_cached_or_fetch()`` for DRY cache hit / cache miss handling
- ``_validate_symbol()`` for input validation
- Context manager support

Examples
--------
>>> from market.alphavantage.client import AlphaVantageClient
>>> with AlphaVantageClient() as client:
...     df = client.get_daily("AAPL")
...     print(f"Got {len(df)} rows")

See Also
--------
market.jquants.client : Reference implementation for Session + Cache DI pattern.
market.alphavantage.session : Underlying HTTP session with rate limiting.
market.alphavantage.cache : TTL constants and cache helper.
market.alphavantage.parser : Response parsing functions.
"""

from __future__ import annotations

import re
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from collections.abc import Callable

import pandas as pd

from market.alphavantage.cache import (
    COMPANY_OVERVIEW_TTL,
    CRYPTO_TTL,
    ECONOMIC_INDICATOR_TTL,
    FOREX_TTL,
    FUNDAMENTALS_TTL,
    GLOBAL_QUOTE_TTL,
    TIME_SERIES_DAILY_TTL,
    TIME_SERIES_INTRADAY_TTL,
    get_alphavantage_cache,
)
from market.alphavantage.constants import BASE_URL
from market.alphavantage.errors import AlphaVantageValidationError
from market.alphavantage.parser import (
    parse_company_overview,
    parse_crypto_time_series,
    parse_earnings,
    parse_economic_indicator,
    parse_financial_statements,
    parse_forex_rate,
    parse_fx_time_series,
    parse_global_quote,
    parse_time_series,
)
from market.alphavantage.session import AlphaVantageSession
from market.alphavantage.types import (
    AlphaVantageConfig,
    FetchOptions,
    Interval,
    OutputSize,
    RetryConfig,
)
from market.cache.cache import SQLiteCache, generate_cache_key
from utils_core.logging import get_logger

logger = get_logger(__name__)

# Regex for symbol validation: 1-10 alphanumeric characters + dot
_SYMBOL_PATTERN: re.Pattern[str] = re.compile(r"^[A-Za-z0-9.]{1,10}$")


class AlphaVantageClient:
    """High-level typed API client for the Alpha Vantage API.

    Provides 20+ public methods across 6 categories:

    - **Time series**: ``get_daily``, ``get_weekly``, ``get_monthly``, ``get_intraday``
    - **Real-time**: ``get_global_quote``
    - **Fundamentals**: ``get_company_overview``, ``get_income_statement``,
      ``get_balance_sheet``, ``get_cash_flow``, ``get_earnings``
    - **Forex**: ``get_exchange_rate``, ``get_fx_daily``
    - **Cryptocurrency**: ``get_crypto_daily``
    - **Economic indicators**: ``get_real_gdp``, ``get_cpi``, ``get_inflation``,
      ``get_unemployment``, ``get_treasury_yield``, ``get_federal_funds_rate``

    Parameters
    ----------
    config : AlphaVantageConfig | None
        Alpha Vantage configuration. If ``None``, defaults are used.
    retry_config : RetryConfig | None
        Retry configuration. If ``None``, defaults are used.
    cache : SQLiteCache | None
        Cache instance. If ``None``, a default persistent cache is created.

    Examples
    --------
    >>> with AlphaVantageClient() as client:
    ...     df = client.get_daily("AAPL")
    ...     quote = client.get_global_quote("MSFT")
    """

    def __init__(
        self,
        config: AlphaVantageConfig | None = None,
        retry_config: RetryConfig | None = None,
        cache: SQLiteCache | None = None,
    ) -> None:
        self._session = AlphaVantageSession(config=config, retry_config=retry_config)
        self._cache: SQLiteCache = cache or get_alphavantage_cache()

        logger.info("AlphaVantageClient initialized")

    # =========================================================================
    # Context Manager
    # =========================================================================

    def __enter__(self) -> AlphaVantageClient:
        """Support context manager protocol."""
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: Any,
    ) -> None:
        """Close client on context exit."""
        self.close()

    def close(self) -> None:
        """Close the client and release resources."""
        self._session.close()
        logger.debug("AlphaVantageClient closed")

    # =========================================================================
    # Time Series Methods
    # =========================================================================

    def get_daily(
        self,
        symbol: str,
        outputsize: OutputSize = OutputSize.COMPACT,
        options: FetchOptions | None = None,
    ) -> pd.DataFrame:
        """Get daily time series (OHLCV) data.

        Calls ``TIME_SERIES_DAILY``.

        Parameters
        ----------
        symbol : str
            Stock ticker symbol (e.g. ``"AAPL"``).
        outputsize : OutputSize
            ``COMPACT`` (last 100 points) or ``FULL`` (20+ years).
        options : FetchOptions | None
            Fetch options (cache control).

        Returns
        -------
        pd.DataFrame
            DataFrame with columns: date, open, high, low, close, volume.

        Raises
        ------
        AlphaVantageValidationError
            If the symbol is invalid.
        """
        self._validate_symbol(symbol)
        options = options or FetchOptions()

        params: dict[str, str] = {
            "function": "TIME_SERIES_DAILY",
            "symbol": symbol,
            "outputsize": str(outputsize.value),
        }
        cache_key = generate_cache_key(symbol=symbol, source="av_daily")

        return self._get_cached_or_fetch(
            cache_key=cache_key,
            params=params,
            parser=parse_time_series,
            ttl=TIME_SERIES_DAILY_TTL,
            options=options,
        )

    def get_weekly(
        self,
        symbol: str,
        options: FetchOptions | None = None,
    ) -> pd.DataFrame:
        """Get weekly time series data.

        Calls ``TIME_SERIES_WEEKLY``.

        Parameters
        ----------
        symbol : str
            Stock ticker symbol.
        options : FetchOptions | None
            Fetch options (cache control).

        Returns
        -------
        pd.DataFrame
            DataFrame with weekly OHLCV data.
        """
        self._validate_symbol(symbol)
        options = options or FetchOptions()

        params: dict[str, str] = {
            "function": "TIME_SERIES_WEEKLY",
            "symbol": symbol,
        }
        cache_key = generate_cache_key(symbol=symbol, source="av_weekly")

        return self._get_cached_or_fetch(
            cache_key=cache_key,
            params=params,
            parser=parse_time_series,
            ttl=TIME_SERIES_DAILY_TTL,
            options=options,
        )

    def get_monthly(
        self,
        symbol: str,
        options: FetchOptions | None = None,
    ) -> pd.DataFrame:
        """Get monthly time series data.

        Calls ``TIME_SERIES_MONTHLY``.

        Parameters
        ----------
        symbol : str
            Stock ticker symbol.
        options : FetchOptions | None
            Fetch options (cache control).

        Returns
        -------
        pd.DataFrame
            DataFrame with monthly OHLCV data.
        """
        self._validate_symbol(symbol)
        options = options or FetchOptions()

        params: dict[str, str] = {
            "function": "TIME_SERIES_MONTHLY",
            "symbol": symbol,
        }
        cache_key = generate_cache_key(symbol=symbol, source="av_monthly")

        return self._get_cached_or_fetch(
            cache_key=cache_key,
            params=params,
            parser=parse_time_series,
            ttl=TIME_SERIES_DAILY_TTL,
            options=options,
        )

    def get_intraday(
        self,
        symbol: str,
        interval: Interval = Interval.FIVE_MIN,
        outputsize: OutputSize = OutputSize.COMPACT,
        options: FetchOptions | None = None,
    ) -> pd.DataFrame:
        """Get intraday time series data.

        Calls ``TIME_SERIES_INTRADAY``.

        Parameters
        ----------
        symbol : str
            Stock ticker symbol.
        interval : Interval
            Time interval between data points (default: 5min).
        outputsize : OutputSize
            ``COMPACT`` (last 100 points) or ``FULL`` (full month).
        options : FetchOptions | None
            Fetch options (cache control).

        Returns
        -------
        pd.DataFrame
            DataFrame with intraday OHLCV data.
        """
        self._validate_symbol(symbol)
        options = options or FetchOptions()

        params: dict[str, str] = {
            "function": "TIME_SERIES_INTRADAY",
            "symbol": symbol,
            "interval": str(interval.value),
            "outputsize": str(outputsize.value),
        }
        cache_key = generate_cache_key(
            symbol=symbol, source=f"av_intraday_{interval.value}"
        )

        return self._get_cached_or_fetch(
            cache_key=cache_key,
            params=params,
            parser=parse_time_series,
            ttl=TIME_SERIES_INTRADAY_TTL,
            options=options,
        )

    # =========================================================================
    # Real-time Methods
    # =========================================================================

    def get_global_quote(
        self,
        symbol: str,
        options: FetchOptions | None = None,
    ) -> dict[str, Any]:
        """Get real-time global quote for a symbol.

        Calls ``GLOBAL_QUOTE``.

        Parameters
        ----------
        symbol : str
            Stock ticker symbol.
        options : FetchOptions | None
            Fetch options (cache control).

        Returns
        -------
        dict[str, Any]
            Normalized quote dictionary with keys like ``symbol``,
            ``price``, ``volume``, etc.
        """
        self._validate_symbol(symbol)
        options = options or FetchOptions()

        params: dict[str, str] = {
            "function": "GLOBAL_QUOTE",
            "symbol": symbol,
        }
        cache_key = generate_cache_key(symbol=symbol, source="av_global_quote")

        return self._get_cached_or_fetch(
            cache_key=cache_key,
            params=params,
            parser=parse_global_quote,
            ttl=GLOBAL_QUOTE_TTL,
            options=options,
        )

    # =========================================================================
    # Fundamentals Methods
    # =========================================================================

    def get_company_overview(
        self,
        symbol: str,
        options: FetchOptions | None = None,
    ) -> dict[str, Any]:
        """Get company overview / profile data.

        Calls ``OVERVIEW``.

        Parameters
        ----------
        symbol : str
            Stock ticker symbol.
        options : FetchOptions | None
            Fetch options (cache control).

        Returns
        -------
        dict[str, Any]
            Dictionary with company profile data (sector, industry,
            market cap, PE ratio, etc.).
        """
        self._validate_symbol(symbol)
        options = options or FetchOptions()

        params: dict[str, str] = {
            "function": "OVERVIEW",
            "symbol": symbol,
        }
        cache_key = generate_cache_key(symbol=symbol, source="av_overview")

        return self._get_cached_or_fetch(
            cache_key=cache_key,
            params=params,
            parser=parse_company_overview,
            ttl=COMPANY_OVERVIEW_TTL,
            options=options,
        )

    def get_income_statement(
        self,
        symbol: str,
        report_type: str = "annualReports",
        options: FetchOptions | None = None,
    ) -> pd.DataFrame:
        """Get income statement data.

        Calls ``INCOME_STATEMENT``.

        Parameters
        ----------
        symbol : str
            Stock ticker symbol.
        report_type : str
            ``'annualReports'`` or ``'quarterlyReports'``.
        options : FetchOptions | None
            Fetch options (cache control).

        Returns
        -------
        pd.DataFrame
            DataFrame with income statement data.
        """
        self._validate_symbol(symbol)
        options = options or FetchOptions()

        params: dict[str, str] = {
            "function": "INCOME_STATEMENT",
            "symbol": symbol,
        }
        cache_key = generate_cache_key(
            symbol=symbol, source=f"av_income_statement_{report_type}"
        )

        def parser(data: dict[str, Any]) -> pd.DataFrame:
            return parse_financial_statements(data, report_type=report_type)

        return self._get_cached_or_fetch(
            cache_key=cache_key,
            params=params,
            parser=parser,
            ttl=FUNDAMENTALS_TTL,
            options=options,
        )

    def get_balance_sheet(
        self,
        symbol: str,
        report_type: str = "annualReports",
        options: FetchOptions | None = None,
    ) -> pd.DataFrame:
        """Get balance sheet data.

        Calls ``BALANCE_SHEET``.

        Parameters
        ----------
        symbol : str
            Stock ticker symbol.
        report_type : str
            ``'annualReports'`` or ``'quarterlyReports'``.
        options : FetchOptions | None
            Fetch options (cache control).

        Returns
        -------
        pd.DataFrame
            DataFrame with balance sheet data.
        """
        self._validate_symbol(symbol)
        options = options or FetchOptions()

        params: dict[str, str] = {
            "function": "BALANCE_SHEET",
            "symbol": symbol,
        }
        cache_key = generate_cache_key(
            symbol=symbol, source=f"av_balance_sheet_{report_type}"
        )

        def parser(data: dict[str, Any]) -> pd.DataFrame:
            return parse_financial_statements(data, report_type=report_type)

        return self._get_cached_or_fetch(
            cache_key=cache_key,
            params=params,
            parser=parser,
            ttl=FUNDAMENTALS_TTL,
            options=options,
        )

    def get_cash_flow(
        self,
        symbol: str,
        report_type: str = "annualReports",
        options: FetchOptions | None = None,
    ) -> pd.DataFrame:
        """Get cash flow statement data.

        Calls ``CASH_FLOW``.

        Parameters
        ----------
        symbol : str
            Stock ticker symbol.
        report_type : str
            ``'annualReports'`` or ``'quarterlyReports'``.
        options : FetchOptions | None
            Fetch options (cache control).

        Returns
        -------
        pd.DataFrame
            DataFrame with cash flow data.
        """
        self._validate_symbol(symbol)
        options = options or FetchOptions()

        params: dict[str, str] = {
            "function": "CASH_FLOW",
            "symbol": symbol,
        }
        cache_key = generate_cache_key(
            symbol=symbol, source=f"av_cash_flow_{report_type}"
        )

        def parser(data: dict[str, Any]) -> pd.DataFrame:
            return parse_financial_statements(data, report_type=report_type)

        return self._get_cached_or_fetch(
            cache_key=cache_key,
            params=params,
            parser=parser,
            ttl=FUNDAMENTALS_TTL,
            options=options,
        )

    def get_earnings(
        self,
        symbol: str,
        options: FetchOptions | None = None,
    ) -> tuple[pd.DataFrame, pd.DataFrame]:
        """Get earnings data (annual and quarterly).

        Calls ``EARNINGS``.

        Parameters
        ----------
        symbol : str
            Stock ticker symbol.
        options : FetchOptions | None
            Fetch options (cache control).

        Returns
        -------
        tuple[pd.DataFrame, pd.DataFrame]
            A tuple of (annual_earnings, quarterly_earnings) DataFrames.
        """
        self._validate_symbol(symbol)
        options = options or FetchOptions()

        params: dict[str, str] = {
            "function": "EARNINGS",
            "symbol": symbol,
        }
        cache_key = generate_cache_key(symbol=symbol, source="av_earnings")

        return self._get_cached_or_fetch(
            cache_key=cache_key,
            params=params,
            parser=parse_earnings,
            ttl=FUNDAMENTALS_TTL,
            options=options,
        )

    # =========================================================================
    # Forex Methods
    # =========================================================================

    def get_exchange_rate(
        self,
        from_currency: str,
        to_currency: str,
        options: FetchOptions | None = None,
    ) -> dict[str, Any]:
        """Get real-time exchange rate between two currencies.

        Calls ``CURRENCY_EXCHANGE_RATE``.

        Parameters
        ----------
        from_currency : str
            Source currency code (e.g. ``"USD"``).
        to_currency : str
            Destination currency code (e.g. ``"JPY"``).
        options : FetchOptions | None
            Fetch options (cache control).

        Returns
        -------
        dict[str, Any]
            Normalized exchange rate dictionary.
        """
        options = options or FetchOptions()

        params: dict[str, str] = {
            "function": "CURRENCY_EXCHANGE_RATE",
            "from_currency": from_currency,
            "to_currency": to_currency,
        }
        cache_key = generate_cache_key(
            symbol=f"{from_currency}_{to_currency}", source="av_exchange_rate"
        )

        return self._get_cached_or_fetch(
            cache_key=cache_key,
            params=params,
            parser=parse_forex_rate,
            ttl=FOREX_TTL,
            options=options,
        )

    def get_fx_daily(
        self,
        from_symbol: str,
        to_symbol: str,
        outputsize: OutputSize = OutputSize.COMPACT,
        options: FetchOptions | None = None,
    ) -> pd.DataFrame:
        """Get daily forex time series data.

        Calls ``FX_DAILY``.

        Parameters
        ----------
        from_symbol : str
            Source currency code (e.g. ``"USD"``).
        to_symbol : str
            Destination currency code (e.g. ``"JPY"``).
        outputsize : OutputSize
            ``COMPACT`` (last 100 points) or ``FULL`` (20+ years).
        options : FetchOptions | None
            Fetch options (cache control).

        Returns
        -------
        pd.DataFrame
            DataFrame with daily forex OHLC data.
        """
        options = options or FetchOptions()

        params: dict[str, str] = {
            "function": "FX_DAILY",
            "from_symbol": from_symbol,
            "to_symbol": to_symbol,
            "outputsize": str(outputsize.value),
        }
        cache_key = generate_cache_key(
            symbol=f"{from_symbol}_{to_symbol}", source="av_fx_daily"
        )

        return self._get_cached_or_fetch(
            cache_key=cache_key,
            params=params,
            parser=parse_fx_time_series,
            ttl=FOREX_TTL,
            options=options,
        )

    # =========================================================================
    # Cryptocurrency Methods
    # =========================================================================

    def get_crypto_daily(
        self,
        symbol: str,
        market: str = "USD",
        options: FetchOptions | None = None,
    ) -> pd.DataFrame:
        """Get daily cryptocurrency data.

        Calls ``DIGITAL_CURRENCY_DAILY``.

        Parameters
        ----------
        symbol : str
            Cryptocurrency symbol (e.g. ``"BTC"``).
        market : str
            Exchange market (e.g. ``"USD"``). Default: ``"USD"``.
        options : FetchOptions | None
            Fetch options (cache control).

        Returns
        -------
        pd.DataFrame
            DataFrame with daily crypto OHLCV data.
        """
        options = options or FetchOptions()

        params: dict[str, str] = {
            "function": "DIGITAL_CURRENCY_DAILY",
            "symbol": symbol,
            "market": market,
        }
        cache_key = generate_cache_key(
            symbol=f"{symbol}_{market}", source="av_crypto_daily"
        )

        return self._get_cached_or_fetch(
            cache_key=cache_key,
            params=params,
            parser=parse_crypto_time_series,
            ttl=CRYPTO_TTL,
            options=options,
        )

    # =========================================================================
    # Economic Indicator Methods
    # =========================================================================

    def get_real_gdp(
        self,
        interval: str = "quarterly",
        options: FetchOptions | None = None,
    ) -> pd.DataFrame:
        """Get Real GDP data.

        Calls ``REAL_GDP``.

        Parameters
        ----------
        interval : str
            ``'quarterly'`` or ``'annual'``. Default: ``'quarterly'``.
        options : FetchOptions | None
            Fetch options (cache control).

        Returns
        -------
        pd.DataFrame
            DataFrame with columns: date, value.
        """
        options = options or FetchOptions()

        params: dict[str, str] = {
            "function": "REAL_GDP",
            "interval": interval,
        }
        cache_key = generate_cache_key(symbol="REAL_GDP", source="av_economic")

        return self._get_cached_or_fetch(
            cache_key=cache_key,
            params=params,
            parser=parse_economic_indicator,
            ttl=ECONOMIC_INDICATOR_TTL,
            options=options,
        )

    def get_cpi(
        self,
        interval: str = "monthly",
        options: FetchOptions | None = None,
    ) -> pd.DataFrame:
        """Get Consumer Price Index data.

        Calls ``CPI``.

        Parameters
        ----------
        interval : str
            ``'monthly'`` or ``'semiannual'``. Default: ``'monthly'``.
        options : FetchOptions | None
            Fetch options (cache control).

        Returns
        -------
        pd.DataFrame
            DataFrame with columns: date, value.
        """
        options = options or FetchOptions()

        params: dict[str, str] = {
            "function": "CPI",
            "interval": interval,
        }
        cache_key = generate_cache_key(symbol="CPI", source="av_economic")

        return self._get_cached_or_fetch(
            cache_key=cache_key,
            params=params,
            parser=parse_economic_indicator,
            ttl=ECONOMIC_INDICATOR_TTL,
            options=options,
        )

    def get_inflation(
        self,
        options: FetchOptions | None = None,
    ) -> pd.DataFrame:
        """Get inflation rate data.

        Calls ``INFLATION``.

        Parameters
        ----------
        options : FetchOptions | None
            Fetch options (cache control).

        Returns
        -------
        pd.DataFrame
            DataFrame with columns: date, value.
        """
        options = options or FetchOptions()

        params: dict[str, str] = {"function": "INFLATION"}
        cache_key = generate_cache_key(symbol="INFLATION", source="av_economic")

        return self._get_cached_or_fetch(
            cache_key=cache_key,
            params=params,
            parser=parse_economic_indicator,
            ttl=ECONOMIC_INDICATOR_TTL,
            options=options,
        )

    def get_unemployment(
        self,
        options: FetchOptions | None = None,
    ) -> pd.DataFrame:
        """Get unemployment rate data.

        Calls ``UNEMPLOYMENT``.

        Parameters
        ----------
        options : FetchOptions | None
            Fetch options (cache control).

        Returns
        -------
        pd.DataFrame
            DataFrame with columns: date, value.
        """
        options = options or FetchOptions()

        params: dict[str, str] = {"function": "UNEMPLOYMENT"}
        cache_key = generate_cache_key(symbol="UNEMPLOYMENT", source="av_economic")

        return self._get_cached_or_fetch(
            cache_key=cache_key,
            params=params,
            parser=parse_economic_indicator,
            ttl=ECONOMIC_INDICATOR_TTL,
            options=options,
        )

    def get_treasury_yield(
        self,
        interval: str = "monthly",
        maturity: str = "10year",
        options: FetchOptions | None = None,
    ) -> pd.DataFrame:
        """Get US Treasury yield data.

        Calls ``TREASURY_YIELD``.

        Parameters
        ----------
        interval : str
            ``'daily'``, ``'weekly'``, or ``'monthly'``. Default: ``'monthly'``.
        maturity : str
            Bond maturity: ``'3month'``, ``'2year'``, ``'5year'``,
            ``'7year'``, ``'10year'``, or ``'30year'``. Default: ``'10year'``.
        options : FetchOptions | None
            Fetch options (cache control).

        Returns
        -------
        pd.DataFrame
            DataFrame with columns: date, value.
        """
        options = options or FetchOptions()

        params: dict[str, str] = {
            "function": "TREASURY_YIELD",
            "interval": interval,
            "maturity": maturity,
        }
        cache_key = generate_cache_key(symbol="TREASURY_YIELD", source="av_economic")

        return self._get_cached_or_fetch(
            cache_key=cache_key,
            params=params,
            parser=parse_economic_indicator,
            ttl=ECONOMIC_INDICATOR_TTL,
            options=options,
        )

    def get_federal_funds_rate(
        self,
        interval: str = "monthly",
        options: FetchOptions | None = None,
    ) -> pd.DataFrame:
        """Get Federal Funds Rate data.

        Calls ``FEDERAL_FUNDS_RATE``.

        Parameters
        ----------
        interval : str
            ``'daily'``, ``'weekly'``, or ``'monthly'``. Default: ``'monthly'``.
        options : FetchOptions | None
            Fetch options (cache control).

        Returns
        -------
        pd.DataFrame
            DataFrame with columns: date, value.
        """
        options = options or FetchOptions()

        params: dict[str, str] = {
            "function": "FEDERAL_FUNDS_RATE",
            "interval": interval,
        }
        cache_key = generate_cache_key(
            symbol="FEDERAL_FUNDS_RATE", source="av_economic"
        )

        return self._get_cached_or_fetch(
            cache_key=cache_key,
            params=params,
            parser=parse_economic_indicator,
            ttl=ECONOMIC_INDICATOR_TTL,
            options=options,
        )

    # =========================================================================
    # Internal Methods
    # =========================================================================

    def _get_cached_or_fetch[T](
        self,
        cache_key: str,
        params: dict[str, str],
        parser: Callable[[dict[str, Any]], T],
        ttl: int,
        options: FetchOptions | None = None,
    ) -> T:
        """Fetch data from cache or API with DRY cache management.

        This is the core DRY helper that every public method delegates to.
        It handles cache hit / cache miss / force refresh logic in one place.

        Parameters
        ----------
        cache_key : str
            Cache key for this request.
        params : dict[str, str]
            Alpha Vantage API query parameters.
        parser : Callable[[dict[str, Any]], T]
            Function to parse the raw JSON response.
        ttl : int
            Cache TTL in seconds.
        options : FetchOptions | None
            Fetch options (cache control). Defaults to using cache.

        Returns
        -------
        T
            Parsed result (DataFrame, dict, tuple, etc.).

        Raises
        ------
        AlphaVantageAuthError
            If the API key is missing or invalid.
        AlphaVantageRateLimitError
            If the API rate limit is exceeded after all retries.
        AlphaVantageAPIError
            If the API returns an error response.
        AlphaVantageParseError
            If the response cannot be parsed.
        """
        options = options or FetchOptions()

        # Check cache
        if options.use_cache and not options.force_refresh:
            cached = self._cache.get(cache_key)
            if cached is not None:
                logger.debug("Cache hit", cache_key=cache_key)
                return cached

        # Fetch from API
        # AIDEV-NOTE: params には apikey は含まれない（session 層で注入されるため安全）
        safe_params = {
            k: v for k, v in params.items() if k.lower() not in ("apikey", "api_key")
        }
        logger.debug("Fetching from API", params=safe_params)
        response = self._session.get_with_retry(BASE_URL, params=params)
        raw_data: dict[str, Any] = response.json()

        # Parse
        result = parser(raw_data)

        # Store in cache
        self._cache.set(cache_key, result, ttl=ttl)
        logger.info(
            "Data fetched and cached",
            cache_key=cache_key,
            ttl=ttl,
        )

        return result

    def _validate_symbol(self, symbol: str) -> None:
        """Validate a stock/currency symbol format.

        Valid symbols are 1-10 characters, alphanumeric plus dot (for
        symbols like ``BRK.B``).

        Parameters
        ----------
        symbol : str
            The symbol to validate.

        Raises
        ------
        AlphaVantageValidationError
            If the symbol is empty, too long, or contains invalid characters.
        """
        if not symbol or not symbol.strip():
            raise AlphaVantageValidationError(
                message="Symbol must not be empty",
                field="symbol",
                value=symbol,
            )

        stripped = symbol.strip()
        if len(stripped) > 10:
            raise AlphaVantageValidationError(
                message=f"Symbol must be 1-10 characters, got '{symbol}' ({len(stripped)} chars)",
                field="symbol",
                value=symbol,
            )

        if not _SYMBOL_PATTERN.match(stripped):
            raise AlphaVantageValidationError(
                message=f"Symbol must be alphanumeric (plus dot), got '{symbol}'",
                field="symbol",
                value=symbol,
            )


__all__ = ["AlphaVantageClient"]
