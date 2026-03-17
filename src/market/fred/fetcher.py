"""FRED data fetcher for economic indicator data retrieval.

This module provides a concrete implementation of BaseDataFetcher
using the fredapi library to fetch economic data from the Federal
Reserve Economic Data (FRED) service.
"""

import json
import os
from datetime import datetime
from pathlib import Path
from typing import Any, ClassVar

import pandas as pd
import requests
from fredapi import Fred

from market.errors import FREDFetchError, FREDValidationError
from utils_core.logging import get_logger
from utils_core.settings import load_project_env

from .base_fetcher import BaseDataFetcher
from .cache import SQLiteCache, generate_cache_key
from .constants import FRED_API_KEY_ENV, FRED_SERIES_PATTERN
from .types import (
    CacheConfig,
    DataSource,
    FetchOptions,
    Interval,
    MarketDataResult,
    RetryConfig,
)

logger = get_logger(__name__, module="fred_fetcher")

# Default path for FRED series presets configuration (fallback based on __file__)
DEFAULT_PRESETS_PATH = (
    Path(__file__).parents[3] / "data" / "config" / "fred_series.json"
)

# Environment variable for FRED series JSON source (URL or local path)
FRED_SERIES_JSON_ENV = "FRED_SERIES_ID_JSON"

# Relative path from current working directory
_CWD_RELATIVE_PRESETS_PATH = Path("data") / "config" / "fred_series.json"


def _get_default_presets_path() -> Path:
    """Get the default path for FRED series presets configuration.

    Priority order:
    1. FRED_SERIES_ID_JSON environment variable
    2. Relative path from current working directory (./data/config/fred_series.json)
    3. Fallback: __file__ based path (for backward compatibility)

    Returns
    -------
    Path
        Path to the FRED series presets configuration file.

    Examples
    --------
    >>> path = _get_default_presets_path()
    >>> path.suffix
    '.json'
    """
    # 1. Check environment variable first
    env_path = os.environ.get(FRED_SERIES_JSON_ENV)
    if env_path:
        logger.debug("Using FRED presets path from environment variable", path=env_path)
        return Path(env_path)

    # 2. Check current working directory relative path
    cwd_path = Path.cwd() / _CWD_RELATIVE_PRESETS_PATH
    if cwd_path.exists():
        logger.debug(
            "Using FRED presets path from current directory", path=str(cwd_path)
        )
        return cwd_path

    # 3. Fallback to __file__ based path
    logger.debug(
        "Using fallback FRED presets path from __file__", path=str(DEFAULT_PRESETS_PATH)
    )
    return DEFAULT_PRESETS_PATH


# Default URL for FRED series presets (used when env var not set and local file not found)
DEFAULT_PRESETS_URL = (
    "https://raw.githubusercontent.com/YH-05/quants/main/data/config/fred_series.json"
)


class FREDFetcher(BaseDataFetcher):
    """Data fetcher using Federal Reserve Economic Data (FRED) API.

    Fetches economic indicator data such as interest rates, GDP,
    inflation rates, and other macroeconomic data from FRED.

    Parameters
    ----------
    api_key : str | None
        FRED API key. If None, reads from FRED_API_KEY environment variable.
    cache : SQLiteCache | None
        Cache instance for storing fetched data.
        If None, caching is disabled.
    cache_config : CacheConfig | None
        Configuration for cache behavior.
    retry_config : RetryConfig | None
        Configuration for retry behavior on API errors.

    Attributes
    ----------
    source : DataSource
        Always returns DataSource.FRED

    Raises
    ------
    FREDValidationError
        If API key is not provided and not found in environment variables.

    Examples
    --------
    >>> fetcher = FREDFetcher()  # Uses FRED_API_KEY env var
    >>> options = FetchOptions(
    ...     symbols=["GDP", "CPIAUCSL"],
    ...     start_date="2020-01-01",
    ...     end_date="2024-12-31",
    ... )
    >>> results = fetcher.fetch(options)

    Using presets:
    >>> fetcher.load_presets()  # Load from default config
    >>> symbols = fetcher.get_preset_symbols("Treasury Yields")
    >>> results = fetcher.fetch_preset("Treasury Yields", start_date="2020-01-01")
    """

    # Class-level cache for presets data
    _presets: ClassVar[dict[str, dict[str, Any]] | None] = None
    _presets_path: ClassVar[str | None] = None  # Can be file path or URL

    def __init__(
        self,
        api_key: str | None = None,
        cache: SQLiteCache | None = None,
        cache_config: CacheConfig | None = None,
        retry_config: RetryConfig | None = None,
    ) -> None:
        # Load .env from project root before reading environment variables
        # Use override=False so explicit environment variables take precedence
        load_project_env()

        self._api_key = api_key or os.environ.get(FRED_API_KEY_ENV)
        self._cache = cache
        self._cache_config = cache_config
        self._retry_config = retry_config
        self._fred: Fred | None = None

        logger.debug(
            "Initializing FREDFetcher",
            api_key_source="parameter" if api_key else "environment",
            cache_enabled=cache is not None,
        )

        if not self._api_key:
            logger.error(
                "FRED API key not found",
                env_var=FRED_API_KEY_ENV,
            )
            raise FREDValidationError(
                f"FRED API key not provided. Set {FRED_API_KEY_ENV} environment "
                "variable or pass api_key parameter."
            )

    @property
    def source(self) -> DataSource:
        """Return the data source type.

        Returns
        -------
        DataSource
            DataSource.FRED
        """
        return DataSource.FRED

    @property
    def default_interval(self) -> Interval:
        """Return the default data interval.

        FRED data is typically monthly or quarterly, but we return
        MONTHLY as the most common interval.

        Returns
        -------
        Interval
            Interval.MONTHLY
        """
        return Interval.MONTHLY

    def _get_fred_client(self) -> Fred:
        """Get or create the FRED API client.

        Returns
        -------
        Fred
            The FRED API client instance
        """
        if self._fred is None:
            self._fred = Fred(api_key=self._api_key)
            logger.debug("FRED client initialized")
        return self._fred

    def validate_symbol(self, symbol: str) -> bool:
        """Validate that a symbol (series ID) is valid for FRED.

        FRED series IDs are uppercase alphanumeric strings that
        may contain underscores, starting with a letter.

        Parameters
        ----------
        symbol : str
            The series ID to validate

        Returns
        -------
        bool
            True if the series ID matches FRED format

        Examples
        --------
        >>> fetcher.validate_symbol("GDP")
        True
        >>> fetcher.validate_symbol("CPIAUCSL")
        True
        >>> fetcher.validate_symbol("DGS10")
        True
        >>> fetcher.validate_symbol("")
        False
        >>> fetcher.validate_symbol("invalid")
        False
        """
        if not symbol or not symbol.strip():
            return False

        return bool(FRED_SERIES_PATTERN.match(symbol.strip()))

    def fetch(
        self,
        options: FetchOptions,
    ) -> list[MarketDataResult]:
        """Fetch economic data for the given options.

        Note: For FRED data, the symbols are interpreted as FRED series IDs.

        Parameters
        ----------
        options : FetchOptions
            Options specifying series IDs, date range, and other parameters.
            The `symbols` field should contain FRED series IDs.

        Returns
        -------
        list[MarketDataResult]
            List of results for each requested series

        Raises
        ------
        FREDFetchError
            If fetching fails for any series
        FREDValidationError
            If options contain invalid parameters

        Examples
        --------
        >>> options = FetchOptions(symbols=["GDP"])
        >>> results = fetcher.fetch(options)
        >>> results[0].symbol
        'GDP'
        """
        self._validate_options(options)

        logger.info(
            "Fetching FRED data",
            series_ids=options.symbols,
            start_date=str(options.start_date),
            end_date=str(options.end_date),
        )

        results: list[MarketDataResult] = []

        for series_id in options.symbols:
            result = self._fetch_single(series_id, options)
            results.append(result)

        logger.info(
            "FRED fetch completed",
            total_series=len(options.symbols),
            successful=len([r for r in results if not r.is_empty]),
            from_cache=len([r for r in results if r.from_cache]),
        )

        return results

    def _fetch_single(
        self,
        series_id: str,
        options: FetchOptions,
    ) -> MarketDataResult:
        """Fetch data for a single FRED series.

        Parameters
        ----------
        series_id : str
            The FRED series ID
        options : FetchOptions
            Fetch options

        Returns
        -------
        MarketDataResult
            The fetch result
        """
        logger.debug("Fetching single series", series_id=series_id)

        # Check cache first
        if self._cache is not None and options.use_cache:
            cached = self._get_from_cache(series_id, options)
            if cached is not None:
                return cached

        # Fetch from API
        data = self._fetch_from_api(series_id, options)

        # Cache the result
        if self._cache is not None and options.use_cache and not data.empty:
            self._save_to_cache(series_id, options, data)

        return self._create_result(
            symbol=series_id,
            data=data,
            from_cache=False,
            metadata={
                "source": "fred",
                "series_id": series_id,
            },
        )

    def _build_cache_key(
        self,
        series_id: str,
        options: FetchOptions,
    ) -> str:
        """Build a cache key for the given series and options."""
        return generate_cache_key(
            symbol=series_id,
            start_date=options.start_date,
            end_date=options.end_date,
            interval=options.interval.value,
            source=self.source.value,
        )

    def _get_from_cache(
        self,
        series_id: str,
        options: FetchOptions,
    ) -> MarketDataResult | None:
        """Try to get data from cache.

        Parameters
        ----------
        series_id : str
            The series ID to look up
        options : FetchOptions
            Fetch options for cache key

        Returns
        -------
        MarketDataResult | None
            Cached result if found, None otherwise
        """
        cache_key = self._build_cache_key(series_id, options)

        assert self._cache is not None  # nosec B101
        cached_data = self._cache.get(cache_key)

        if cached_data is not None and isinstance(cached_data, pd.DataFrame):
            logger.debug("Cache hit", series_id=series_id)
            return self._create_result(
                symbol=series_id,
                data=cached_data,
                from_cache=True,
                metadata={
                    "source": "cache",
                    "series_id": series_id,
                },
            )

        return None

    def _save_to_cache(
        self,
        series_id: str,
        options: FetchOptions,
        data: pd.DataFrame,
    ) -> None:
        """Save data to cache.

        Parameters
        ----------
        series_id : str
            The series ID
        options : FetchOptions
            Fetch options for cache key
        data : pd.DataFrame
            Data to cache
        """
        cache_key = self._build_cache_key(series_id, options)
        ttl = self._cache_config.ttl_seconds if self._cache_config else None

        assert self._cache is not None  # nosec B101
        self._cache.set(
            cache_key,
            data,
            ttl=ttl,
            metadata={"series_id": series_id},
        )

        logger.debug("Data cached", series_id=series_id)

    def _fetch_from_api(
        self,
        series_id: str,
        options: FetchOptions,
    ) -> pd.DataFrame:
        """Fetch data from FRED API.

        Parameters
        ----------
        series_id : str
            The series ID to fetch
        options : FetchOptions
            Fetch options

        Returns
        -------
        pd.DataFrame
            Data with 'value' column

        Raises
        ------
        FREDFetchError
            If the API call fails
        """
        logger.debug("Fetching from FRED API", series_id=series_id)

        try:
            if self._retry_config:
                return self._fetch_with_retry(series_id, options)
            else:
                return self._do_fetch(series_id, options)

        except FREDFetchError:
            raise
        except Exception as e:
            logger.error(
                "FRED API fetch failed",
                series_id=series_id,
                error=str(e),
                error_type=type(e).__name__,
            )
            raise FREDFetchError(f"Failed to fetch FRED series {series_id}: {e}") from e

    def _fetch_with_retry(
        self,
        series_id: str,
        options: FetchOptions,
    ) -> pd.DataFrame:
        """Fetch with retry logic applied.

        Parameters
        ----------
        series_id : str
            The series ID to fetch
        options : FetchOptions
            Fetch options

        Returns
        -------
        pd.DataFrame
            Fetched data
        """
        import time

        assert self._retry_config is not None  # nosec B101

        last_exception: Exception | None = None
        for attempt in range(self._retry_config.max_attempts):
            try:
                return self._do_fetch(series_id, options)
            except Exception as e:
                last_exception = e
                if attempt < self._retry_config.max_attempts - 1:
                    delay = min(
                        self._retry_config.initial_delay
                        * (self._retry_config.exponential_base**attempt),
                        self._retry_config.max_delay,
                    )
                    logger.warning(
                        "Retry attempt",
                        attempt=attempt + 1,
                        delay=delay,
                        error=str(e),
                    )
                    time.sleep(delay)

        # Should not reach here, but satisfy type checker
        raise FREDFetchError(
            f"Failed to fetch FRED series {series_id} after "
            f"{self._retry_config.max_attempts} attempts"
        ) from last_exception

    def _do_fetch(
        self,
        series_id: str,
        options: FetchOptions,
    ) -> pd.DataFrame:
        """Execute the actual FRED API fetch.

        Parameters
        ----------
        series_id : str
            The series ID to fetch
        options : FetchOptions
            Fetch options

        Returns
        -------
        pd.DataFrame
            Data with 'value' column containing the time series data.
            Index is DatetimeIndex.

        Raises
        ------
        FREDFetchError
            If the series ID is invalid or no data is returned
        """
        fred = self._get_fred_client()

        # Format dates
        start = self._format_date(options.start_date)
        end = self._format_date(options.end_date)

        logger.debug(
            "Calling FRED API",
            series_id=series_id,
            start=start,
            end=end,
        )

        try:
            # Get series data
            series = fred.get_series(
                series_id,
                observation_start=start,
                observation_end=end,
            )

            if series.empty:
                logger.warning("No data returned for series", series_id=series_id)
                raise FREDFetchError(f"No data found for FRED series: {series_id}")

            # Convert Series to DataFrame with single 'value' column
            # FRED data is a single time series, not OHLCV data
            df = pd.DataFrame({"value": series}, index=series.index)

            # Ensure index is DatetimeIndex
            if not isinstance(df.index, pd.DatetimeIndex):
                df.index = pd.to_datetime(df.index)

            df = df.sort_index()

            logger.debug(
                "Data fetched successfully",
                series_id=series_id,
                rows=len(df),
                date_range=f"{df.index.min()} to {df.index.max()}"
                if not df.empty
                else "empty",
            )

            return df

        except FREDFetchError:
            raise
        except ValueError as e:
            # fredapi raises ValueError for invalid series IDs
            logger.error(
                "Invalid FRED series ID",
                series_id=series_id,
                error=str(e),
            )
            raise FREDFetchError(f"Invalid FRED series ID: {series_id}") from e

    def _format_date(
        self,
        date: datetime | str | None,
    ) -> str | None:
        """Format a date for FRED API.

        Parameters
        ----------
        date : datetime | str | None
            Date to format

        Returns
        -------
        str | None
            Formatted date string (YYYY-MM-DD) or None
        """
        if date is None:
            return None
        if isinstance(date, datetime):
            return date.strftime("%Y-%m-%d")
        return str(date)

    def get_series_info(self, series_id: str) -> dict[str, Any]:
        """Get metadata about a FRED series.

        Parameters
        ----------
        series_id : str
            The FRED series ID

        Returns
        -------
        dict[str, Any]
            Series metadata including title, units, frequency, etc.

        Examples
        --------
        >>> info = fetcher.get_series_info("GDP")
        >>> info['title']
        'Gross Domestic Product'
        """
        fred = self._get_fred_client()

        try:
            info = fred.get_series_info(series_id)
            return info.to_dict() if hasattr(info, "to_dict") else dict(info)
        except Exception as e:
            logger.error(
                "Failed to get series info",
                series_id=series_id,
                error=str(e),
            )
            raise FREDFetchError(
                f"Failed to get info for series {series_id}: {e}"
            ) from e

    # =========================================================================
    # Preset Methods
    # =========================================================================

    @classmethod
    def load_presets(
        cls,
        config_path: str | Path | None = None,
        *,
        force_reload: bool = False,
    ) -> dict[str, dict[str, Any]]:
        """Load FRED series presets from JSON configuration file or URL.

        Parameters
        ----------
        config_path : str | Path | None
            Path or URL to the JSON configuration.
            If None, checks FRED_SERIES_ID_JSON environment variable first,
            then falls back to local file or default GitHub URL.
        force_reload : bool
            If True, reload presets even if already loaded.

        Returns
        -------
        dict[str, dict[str, Any]]
            Loaded presets data with category -> series_id -> info structure.

        Raises
        ------
        FileNotFoundError
            If the configuration file does not exist (for local paths).
        ValueError
            If the configuration is not valid JSON.
        requests.RequestException
            If URL fetch fails.

        Examples
        --------
        >>> FREDFetcher.load_presets()
        >>> FREDFetcher.load_presets("/custom/path/fred_series.json")
        >>> FREDFetcher.load_presets("https://example.com/fred_series.json")
        """
        load_project_env()

        # Determine source: argument > _get_default_presets_path > URL default
        source = config_path
        if source is None:
            # Use _get_default_presets_path for local file resolution
            # (env var > cwd relative > __file__ based)
            default_path = _get_default_presets_path()
            if default_path.exists():
                source = str(default_path)
            else:
                source = DEFAULT_PRESETS_URL

        source_str = str(source)

        # Return cached presets if already loaded from same source
        if (
            not force_reload
            and cls._presets is not None
            and cls._presets_path == source_str
        ):
            logger.debug("Using cached presets", source=source_str)
            return cls._presets

        # Determine if source is URL or local path
        is_url = source_str.startswith("http://") or source_str.startswith("https://")

        try:
            if is_url:
                cls._presets = cls._load_presets_from_url(source_str)
            else:
                cls._presets = cls._load_presets_from_file(Path(source_str))

            cls._presets_path = source_str

            logger.info(
                "FRED presets loaded",
                source=source_str,
                is_url=is_url,
                categories=list(cls._presets.keys()) if cls._presets else [],
                total_series=sum(len(series) for series in cls._presets.values())
                if cls._presets
                else 0,
            )

            return cls._presets or {}

        except json.JSONDecodeError as e:
            logger.error("Invalid JSON in presets", source=source_str, error=str(e))
            raise ValueError(f"Invalid JSON in presets {source_str}: {e}") from e

    @classmethod
    def _load_presets_from_file(cls, path: Path) -> dict[str, dict[str, Any]]:
        """Load presets from a local file.

        Parameters
        ----------
        path : Path
            Path to the JSON file.

        Returns
        -------
        dict[str, dict[str, Any]]
            Loaded presets data.

        Raises
        ------
        FileNotFoundError
            If the file does not exist.
        """
        if not path.exists():
            logger.error("Presets file not found", path=str(path))
            raise FileNotFoundError(f"FRED presets file not found: {path}")

        with open(path, encoding="utf-8") as f:
            return json.load(f)

    @classmethod
    def _load_presets_from_url(
        cls,
        url: str,
        timeout: int = 30,
    ) -> dict[str, dict[str, Any]]:
        """Load presets from a URL.

        Parameters
        ----------
        url : str
            URL to the JSON file.
        timeout : int
            Request timeout in seconds.

        Returns
        -------
        dict[str, dict[str, Any]]
            Loaded presets data.

        Raises
        ------
        requests.RequestException
            If the request fails.
        """
        logger.debug("Fetching presets from URL", url=url)

        response = requests.get(url, timeout=timeout)
        response.raise_for_status()

        return response.json()

    @classmethod
    def get_preset_categories(cls) -> list[str]:
        """Get list of available preset categories.

        Returns
        -------
        list[str]
            List of category names (e.g., "Treasury Yields", "Economic Indicators").

        Raises
        ------
        RuntimeError
            If presets have not been loaded.

        Examples
        --------
        >>> FREDFetcher.load_presets()
        >>> categories = FREDFetcher.get_preset_categories()
        >>> print(categories)
        ['Treasury Yields', 'Economic Indicators', ...]
        """
        if cls._presets is None:
            raise RuntimeError("Presets not loaded. Call load_presets() first.")

        return list(cls._presets.keys())

    @classmethod
    def get_preset_symbols(cls, category: str | None = None) -> list[str]:
        """Get list of series IDs from presets.

        Parameters
        ----------
        category : str | None
            Category name to filter by.
            If None, returns all series IDs from all categories.

        Returns
        -------
        list[str]
            List of FRED series IDs.

        Raises
        ------
        RuntimeError
            If presets have not been loaded.
        KeyError
            If the specified category does not exist.

        Examples
        --------
        >>> FREDFetcher.load_presets()
        >>> symbols = FREDFetcher.get_preset_symbols("Treasury Yields")
        >>> print(symbols)
        ['DGS1MO', 'DGS3MO', 'DGS6MO', ...]

        >>> all_symbols = FREDFetcher.get_preset_symbols()  # All categories
        """
        if cls._presets is None:
            raise RuntimeError("Presets not loaded. Call load_presets() first.")

        if category is not None:
            if category not in cls._presets:
                raise KeyError(
                    f"Category '{category}' not found. "
                    f"Available: {list(cls._presets.keys())}"
                )
            return list(cls._presets[category].keys())

        # Return all symbols from all categories
        symbols: list[str] = []
        for cat_series in cls._presets.values():
            symbols.extend(cat_series.keys())
        return symbols

    @classmethod
    def get_preset_info(cls, series_id: str) -> dict[str, Any] | None:
        """Get preset information for a specific series ID.

        Parameters
        ----------
        series_id : str
            The FRED series ID to look up.

        Returns
        -------
        dict[str, Any] | None
            Series information from presets, or None if not found.

        Raises
        ------
        RuntimeError
            If presets have not been loaded.

        Examples
        --------
        >>> FREDFetcher.load_presets()
        >>> info = FREDFetcher.get_preset_info("DGS10")
        >>> print(info["name_ja"])
        '10年国債利回り'
        """
        if cls._presets is None:
            raise RuntimeError("Presets not loaded. Call load_presets() first.")

        for category, series_dict in cls._presets.items():
            if series_id in series_dict:
                info = series_dict[series_id].copy()
                info["category_name"] = category
                return info

        return None

    def fetch_preset(
        self,
        category: str | None = None,
        start_date: datetime | str | None = None,
        end_date: datetime | str | None = None,
        *,
        use_cache: bool = True,
    ) -> list[MarketDataResult]:
        """Fetch data for all series in a preset category.

        Parameters
        ----------
        category : str | None
            Category name to fetch.
            If None, fetches all series from all categories.
        start_date : datetime | str | None
            Start date for data range.
        end_date : datetime | str | None
            End date for data range.
        use_cache : bool
            Whether to use cache.

        Returns
        -------
        list[MarketDataResult]
            List of results for each series in the category.

        Raises
        ------
        RuntimeError
            If presets have not been loaded.
        KeyError
            If the specified category does not exist.

        Examples
        --------
        >>> fetcher = FREDFetcher()
        >>> fetcher.load_presets()
        >>> results = fetcher.fetch_preset(
        ...     "Treasury Yields",
        ...     start_date="2020-01-01",
        ... )
        >>> for r in results:
        ...     print(f"{r.symbol}: {r.row_count} rows")
        """
        symbols = self.get_preset_symbols(category)

        logger.info(
            "Fetching preset data",
            category=category or "all",
            symbol_count=len(symbols),
            start_date=str(start_date),
            end_date=str(end_date),
        )

        options = FetchOptions(
            symbols=symbols,
            start_date=start_date,
            end_date=end_date,
            use_cache=use_cache,
        )

        return self.fetch(options)


__all__ = [
    "DEFAULT_PRESETS_PATH",
    "DEFAULT_PRESETS_URL",
    "FRED_SERIES_JSON_ENV",
    "FREDFetcher",
]
