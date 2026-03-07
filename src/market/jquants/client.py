"""API client for the J-Quants API.

This module provides the ``JQuantsClient`` class, a high-level client
for the J-Quants API that wraps ``JQuantsSession`` with typed methods
and SQLiteCache integration.

Features include:

- Typed methods for each API endpoint returning ``pd.DataFrame``
- SQLiteCache integration with configurable TTL per endpoint
- ``_request()`` + ``_handle_response()`` pattern (EDINET-style)
- Context manager support

Examples
--------
>>> from market.jquants import JQuantsClient, JQuantsConfig
>>> config = JQuantsConfig(
...     mail_address="user@example.com",
...     password="secret",
... )
>>> with JQuantsClient(config=config) as client:
...     df = client.get_listed_info()
...     print(f"Found {len(df)} companies")

See Also
--------
market.edinet.client : _request + _handle_response pattern reference.
market.jquants.session : Underlying HTTP session with auth.
market.jquants.cache : TTL constants and cache helper.
"""

from typing import Any

import pandas as pd

from market.cache.cache import SQLiteCache, generate_cache_key
from market.jquants.cache import (
    DAILY_QUOTES_TTL,
    FINANCIAL_TTL,
    LISTED_INFO_TTL,
    TRADING_CALENDAR_TTL,
    get_jquants_cache,
)
from market.jquants.constants import BASE_URL
from market.jquants.errors import JQuantsAPIError, JQuantsValidationError
from market.jquants.session import JQuantsSession
from market.jquants.types import FetchOptions, JQuantsConfig, RetryConfig
from utils_core.logging import get_logger

logger = get_logger(__name__)


class JQuantsClient:
    """High-level client for the J-Quants API.

    Provides typed methods for each API endpoint, returning
    ``pd.DataFrame`` objects. Integrates with SQLiteCache for
    data persistence.

    Parameters
    ----------
    config : JQuantsConfig | None
        J-Quants configuration. If ``None``, defaults are used.
    retry_config : RetryConfig | None
        Retry configuration. If ``None``, defaults are used.
    cache : SQLiteCache | None
        Cache instance. If ``None``, a default persistent cache is created.

    Examples
    --------
    >>> with JQuantsClient() as client:
    ...     df = client.get_listed_info(code="7203")
    ...     print(df.columns.tolist())
    """

    def __init__(
        self,
        config: JQuantsConfig | None = None,
        retry_config: RetryConfig | None = None,
        cache: SQLiteCache | None = None,
    ) -> None:
        self._session = JQuantsSession(config=config, retry_config=retry_config)
        self._cache: SQLiteCache = cache or get_jquants_cache()

        logger.info("JQuantsClient initialized")

    # =========================================================================
    # Context Manager
    # =========================================================================

    def __enter__(self) -> "JQuantsClient":
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
        logger.debug("JQuantsClient closed")

    # =========================================================================
    # Public API Methods
    # =========================================================================

    def get_listed_info(
        self,
        code: str | None = None,
        options: FetchOptions | None = None,
    ) -> pd.DataFrame:
        """Get listed company information.

        Calls ``GET /listed/info``. Returns all listed companies
        or a specific company if ``code`` is provided.

        Parameters
        ----------
        code : str | None
            Stock code (e.g. ``"7203"``). If ``None``, returns all.
        options : FetchOptions | None
            Fetch options (cache control). Defaults to using cache.

        Returns
        -------
        pd.DataFrame
            DataFrame with listed company information.

        Raises
        ------
        JQuantsAPIError
            If the API returns an error response.
        JQuantsValidationError
            If the stock code format is invalid.

        Examples
        --------
        >>> df = client.get_listed_info(code="7203")
        >>> df["CompanyName"].iloc[0]
        'トヨタ自動車'
        """
        if code is not None:
            self._validate_code(code)

        options = options or FetchOptions()
        params: dict[str, str] = {}
        if code is not None:
            params["code"] = code

        cache_key = generate_cache_key(
            symbol=code or "ALL",
            source="jquants_listed",
        )

        # Check cache
        if options.use_cache and not options.force_refresh:
            cached = self._cache.get(cache_key)
            if cached is not None:
                logger.debug("Cache hit for listed info", code=code)
                return cached

        logger.debug("Fetching listed info", code=code)
        data = self._request("/listed/info", params=params)
        info_list = data.get("info", [])
        df = pd.DataFrame(info_list)

        # Store in cache
        self._cache.set(cache_key, df, ttl=LISTED_INFO_TTL)
        logger.info("Listed info retrieved", code=code, rows=len(df))
        return df

    def get_daily_quotes(
        self,
        code: str,
        from_date: str,
        to_date: str,
        options: FetchOptions | None = None,
    ) -> pd.DataFrame:
        """Get daily stock quotes (OHLC).

        Calls ``GET /prices/daily_quotes``.

        Parameters
        ----------
        code : str
            Stock code (e.g. ``"7203"``).
        from_date : str
            Start date in ``YYYYMMDD`` or ``YYYY-MM-DD`` format.
        to_date : str
            End date in ``YYYYMMDD`` or ``YYYY-MM-DD`` format.
        options : FetchOptions | None
            Fetch options (cache control).

        Returns
        -------
        pd.DataFrame
            DataFrame with daily OHLC data.

        Raises
        ------
        JQuantsAPIError
            If the API returns an error response.
        JQuantsValidationError
            If the stock code or date format is invalid.

        Examples
        --------
        >>> df = client.get_daily_quotes("7203", "20240101", "20240131")
        >>> list(df.columns[:5])
        ['Date', 'Code', 'Open', 'High', 'Low']
        """
        self._validate_code(code)
        options = options or FetchOptions()

        # Normalize date format (remove hyphens)
        from_date_norm = from_date.replace("-", "")
        to_date_norm = to_date.replace("-", "")

        params: dict[str, str] = {
            "code": code,
            "from": from_date_norm,
            "to": to_date_norm,
        }

        cache_key = generate_cache_key(
            symbol=code,
            start_date=from_date_norm,
            end_date=to_date_norm,
            source="jquants_daily",
        )

        # Check cache
        if options.use_cache and not options.force_refresh:
            cached = self._cache.get(cache_key)
            if cached is not None:
                logger.debug(
                    "Cache hit for daily quotes",
                    code=code,
                    from_date=from_date_norm,
                    to_date=to_date_norm,
                )
                return cached

        logger.debug(
            "Fetching daily quotes",
            code=code,
            from_date=from_date_norm,
            to_date=to_date_norm,
        )
        data = self._request("/prices/daily_quotes", params=params)
        quotes_list = data.get("daily_quotes", [])
        df = pd.DataFrame(quotes_list)

        # Store in cache
        self._cache.set(cache_key, df, ttl=DAILY_QUOTES_TTL)
        logger.info(
            "Daily quotes retrieved",
            code=code,
            rows=len(df),
            from_date=from_date_norm,
            to_date=to_date_norm,
        )
        return df

    def get_financial_statements(
        self,
        code: str,
        options: FetchOptions | None = None,
    ) -> pd.DataFrame:
        """Get financial statement data.

        Calls ``GET /fins/statements``.

        Parameters
        ----------
        code : str
            Stock code (e.g. ``"7203"``).
        options : FetchOptions | None
            Fetch options (cache control).

        Returns
        -------
        pd.DataFrame
            DataFrame with financial statement data.

        Raises
        ------
        JQuantsAPIError
            If the API returns an error response.
        JQuantsValidationError
            If the stock code format is invalid.

        Examples
        --------
        >>> df = client.get_financial_statements("7203")
        >>> "NetSales" in df.columns
        True
        """
        self._validate_code(code)
        options = options or FetchOptions()

        params: dict[str, str] = {"code": code}

        cache_key = generate_cache_key(
            symbol=code,
            source="jquants_financial",
        )

        # Check cache
        if options.use_cache and not options.force_refresh:
            cached = self._cache.get(cache_key)
            if cached is not None:
                logger.debug("Cache hit for financial statements", code=code)
                return cached

        logger.debug("Fetching financial statements", code=code)
        data = self._request("/fins/statements", params=params)
        statements_list = data.get("statements", [])
        df = pd.DataFrame(statements_list)

        # Store in cache
        self._cache.set(cache_key, df, ttl=FINANCIAL_TTL)
        logger.info("Financial statements retrieved", code=code, rows=len(df))
        return df

    def get_trading_calendar(
        self,
        options: FetchOptions | None = None,
    ) -> pd.DataFrame:
        """Get trading calendar.

        Calls ``GET /markets/trading_calendar``.

        Parameters
        ----------
        options : FetchOptions | None
            Fetch options (cache control).

        Returns
        -------
        pd.DataFrame
            DataFrame with trading calendar data.

        Raises
        ------
        JQuantsAPIError
            If the API returns an error response.

        Examples
        --------
        >>> df = client.get_trading_calendar()
        >>> "Date" in df.columns
        True
        """
        options = options or FetchOptions()

        cache_key = generate_cache_key(
            symbol="TRADING_CALENDAR",
            source="jquants_calendar",
        )

        # Check cache
        if options.use_cache and not options.force_refresh:
            cached = self._cache.get(cache_key)
            if cached is not None:
                logger.debug("Cache hit for trading calendar")
                return cached

        logger.debug("Fetching trading calendar")
        data = self._request("/markets/trading_calendar")
        calendar_list = data.get("trading_calendar", [])
        df = pd.DataFrame(calendar_list)

        # Store in cache
        self._cache.set(cache_key, df, ttl=TRADING_CALENDAR_TTL)
        logger.info("Trading calendar retrieved", rows=len(df))
        return df

    # =========================================================================
    # Internal Methods
    # =========================================================================

    def _request(
        self,
        path: str,
        params: dict[str, str] | None = None,
    ) -> dict[str, Any]:
        """Execute an API request via the session.

        Parameters
        ----------
        path : str
            API endpoint path (e.g. ``"/listed/info"``).
        params : dict[str, str] | None
            Optional query parameters.

        Returns
        -------
        dict[str, Any]
            Parsed JSON response body.

        Raises
        ------
        JQuantsAPIError
            If the API returns an error.
        """
        url = f"{BASE_URL}{path}"
        response = self._session.get_with_retry(url, params=params)
        result: dict[str, Any] = response.json()
        return result

    def _validate_code(self, code: str) -> None:
        """Validate a stock code format.

        Parameters
        ----------
        code : str
            The stock code to validate.

        Raises
        ------
        JQuantsValidationError
            If the code is not a valid format.
        """
        if not code or not code.strip():
            raise JQuantsValidationError(
                message="Stock code must not be empty",
                field="code",
                value=code,
            )
        # J-Quants accepts 4-5 digit codes
        stripped = code.strip()
        if not stripped.isdigit() or not (4 <= len(stripped) <= 5):
            raise JQuantsValidationError(
                message=f"Stock code must be 4-5 digits, got '{code}'",
                field="code",
                value=code,
            )


__all__ = ["JQuantsClient"]
