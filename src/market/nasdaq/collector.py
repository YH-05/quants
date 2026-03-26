"""NASDAQ Stock Screener collector with DataCollector ABC compliance.

This module provides ``ScreenerCollector``, the main entry point for
fetching stock screening data from the NASDAQ Stock Screener API.
It inherits from ``DataCollector`` and implements the ``fetch()`` /
``validate()`` interface with additional convenience methods for
category-based bulk fetching and CSV download.

Features
--------
- DataCollector ABC compliance (fetch / validate interface)
- Dependency injection for NasdaqSession (testability)
- Category-based bulk fetching via ``fetch_by_category()``
- CSV download with utf-8-sig encoding via ``download_csv()``
- Polite delay between consecutive requests in bulk operations

Examples
--------
Basic fetch:

>>> collector = ScreenerCollector()
>>> df = collector.fetch()
>>> print(f"Found {len(df)} stocks")

With filter:

>>> from market.nasdaq.types import ScreenerFilter, Exchange, Sector
>>> filter_ = ScreenerFilter(exchange=Exchange.NASDAQ, sector=Sector.TECHNOLOGY)
>>> df = collector.fetch(filter=filter_)

Category-based CSV download:

>>> from market.nasdaq.types import Sector
>>> paths = collector.download_by_category(Sector, output_dir=Path("data/raw/nasdaq"))

See Also
--------
market.base_collector : DataCollector abstract base class.
market.nasdaq.session : NasdaqSession with bot-blocking countermeasures.
market.nasdaq.parser : JSON response parser and numeric cleaning.
market.nasdaq.types : ScreenerFilter, FilterCategory, and related types.
market.etfcom.collector : Reference ETFComCollector implementation.
"""

from __future__ import annotations

import time
from datetime import date
from pathlib import Path
from typing import Any

import pandas as pd

from database.db.connection import get_data_dir
from market.base_collector import DataCollector
from market.nasdaq.constants import DEFAULT_OUTPUT_SUBDIR, NASDAQ_SCREENER_URL
from market.nasdaq.parser import parse_screener_response
from market.nasdaq.session import NasdaqSession
from market.nasdaq.types import (
    Exchange,
    FilterCategory,
    MarketCap,
    Recommendation,
    Region,
    ScreenerFilter,
    Sector,
)
from utils_core.logging import get_logger

logger = get_logger(__name__)

# Required columns for validation
_REQUIRED_COLUMNS: frozenset[str] = frozenset({"symbol", "name"})

# Declarative mapping from filter category Enum type to ScreenerFilter field name.
# Used by _build_category_filter() to avoid repetitive if/elif chains.
_CATEGORY_FIELD_MAP: dict[type, str] = {
    Exchange: "exchange",
    MarketCap: "marketcap",
    Sector: "sector",
    Recommendation: "recommendation",
    Region: "region",
}


class ScreenerCollector(DataCollector):
    """Collector for NASDAQ Stock Screener data.

    Fetches stock screening data from the NASDAQ Screener API, parsing
    the JSON response into a pandas DataFrame with cleaned numeric columns.
    Supports filtering by exchange, market cap, sector, recommendation,
    region, and country via ``ScreenerFilter``.

    The ``NasdaqSession`` can be injected via the constructor for testing
    (dependency injection pattern).  When no session is provided, a new
    session is created internally for each operation.

    Parameters
    ----------
    session : NasdaqSession | None
        Pre-configured NasdaqSession instance.  If None, a new session is
        created internally when needed.

    Attributes
    ----------
    _session_instance : NasdaqSession | None
        Injected session instance (None if creating internally).

    Examples
    --------
    >>> collector = ScreenerCollector()
    >>> df = collector.collect()
    >>> print(f"Collected {len(df)} stocks")

    >>> # With dependency injection for testing
    >>> mock_session = MagicMock(spec=NasdaqSession)
    >>> collector = ScreenerCollector(session=mock_session)
    """

    def __init__(self, session: NasdaqSession | None = None) -> None:
        """Initialize ScreenerCollector with optional session injection.

        Parameters
        ----------
        session : NasdaqSession | None
            Pre-configured NasdaqSession for dependency injection.
            If None, a new NasdaqSession is created when needed.
        """
        self._session_instance: NasdaqSession | None = session

        logger.info(
            "ScreenerCollector initialized",
            session_injected=session is not None,
        )

    def _get_session(self) -> tuple[NasdaqSession, bool]:
        """Resolve the session: use injected or create new.

        Returns
        -------
        tuple[NasdaqSession, bool]
            A tuple of (session, should_close).  ``should_close`` is True
            when a new session was created internally and must be closed
            by the caller.

        Examples
        --------
        >>> collector = ScreenerCollector()
        >>> session, should_close = collector._get_session()
        >>> try:
        ...     response = session.get_with_retry(url)
        ... finally:
        ...     if should_close:
        ...         session.close()
        """
        if self._session_instance is not None:
            return self._session_instance, False
        return NasdaqSession(), True

    @staticmethod
    def _resolve_output_dir() -> Path:
        """Resolve the default output directory using DATA_DIR env var.

        Returns
        -------
        Path
            ``get_data_dir() / DEFAULT_OUTPUT_SUBDIR``, which respects
            the ``DATA_DIR`` environment variable.
        """
        return get_data_dir() / DEFAULT_OUTPUT_SUBDIR

    def fetch(self, **kwargs: Any) -> pd.DataFrame:
        """Fetch stock screening data from the NASDAQ API.

        Sends a GET request to the NASDAQ Screener API with optional
        filter parameters, parses the JSON response, and returns a
        cleaned DataFrame.

        Parameters
        ----------
        **kwargs : Any
            Keyword arguments.  Expected:
            - filter (ScreenerFilter | None): Optional filter conditions.

        Returns
        -------
        pd.DataFrame
            DataFrame with columns: symbol, name, last_sale, net_change,
            pct_change, market_cap, country, ipo_year, volume, sector,
            industry, url.

        Raises
        ------
        NasdaqAPIError
            If the API returns an error status code.
        NasdaqRateLimitError
            If rate limiting is detected.
        NasdaqParseError
            If the JSON response cannot be parsed.

        Examples
        --------
        >>> collector = ScreenerCollector()
        >>> df = collector.fetch()
        >>> df["symbol"].iloc[0]
        'AAPL'

        >>> from market.nasdaq.types import ScreenerFilter, Exchange
        >>> df = collector.fetch(filter=ScreenerFilter(exchange=Exchange.NASDAQ))
        """
        filter_: ScreenerFilter | None = kwargs.get("filter")

        params = filter_.to_params() if filter_ is not None else {"limit": "0"}

        logger.info(
            "Fetching screener data",
            params=params,
        )

        session, should_close = self._get_session()
        try:
            response = session.get_with_retry(
                NASDAQ_SCREENER_URL,
                params=params,
            )
            json_data: dict[str, Any] = response.json()
            df = parse_screener_response(json_data)

            logger.info(
                "Screener data fetched",
                row_count=len(df),
            )

            return df
        finally:
            if should_close:
                session.close()

    def validate(self, df: pd.DataFrame) -> bool:
        """Validate the fetched screener data.

        Checks that the DataFrame:
        - Is not empty
        - Contains the required columns (``symbol``, ``name``)

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
        >>> collector = ScreenerCollector()
        >>> df = pd.DataFrame({"symbol": ["AAPL"], "name": ["Apple Inc."]})
        >>> collector.validate(df)
        True
        >>> collector.validate(pd.DataFrame())
        False
        """
        if df.empty:
            logger.warning("Validation failed: DataFrame is empty")
            return False

        missing = _REQUIRED_COLUMNS - set(df.columns)
        if missing:
            logger.warning(
                "Validation failed: missing required columns",
                missing_columns=sorted(missing),
                actual_columns=list(df.columns),
            )
            return False

        logger.debug(
            "Validation passed",
            row_count=len(df),
        )
        return True

    def fetch_by_category(
        self,
        category: FilterCategory,
        *,
        base_filter: ScreenerFilter | None = None,
    ) -> dict[str, pd.DataFrame]:
        """Fetch screener data for all values of a filter category.

        Iterates over every member of the given Enum category
        (e.g. ``Exchange``, ``Sector``), creates a ``ScreenerFilter``
        with that value, and calls ``fetch()``.  A polite delay is
        inserted between each request.

        Parameters
        ----------
        category : FilterCategory
            The Enum class to iterate over (e.g. ``Exchange``, ``Sector``).
        base_filter : ScreenerFilter | None
            Optional base filter to merge with the category value.
            If None, a new ScreenerFilter is created for each value.

        Returns
        -------
        dict[str, pd.DataFrame]
            A dict mapping each Enum value (as string) to the fetched DataFrame.

        Examples
        --------
        >>> from market.nasdaq.types import Exchange
        >>> collector = ScreenerCollector()
        >>> results = collector.fetch_by_category(Exchange)
        >>> results["nasdaq"].head()
        """
        logger.info(
            "Starting category-based fetch",
            category=category.__name__,
            member_count=len(category),
        )

        results: dict[str, pd.DataFrame] = {}

        for i, member in enumerate(category):
            value: str = member.value
            logger.debug(
                "Fetching category member",
                category=category.__name__,
                value=value,
                index=i,
            )

            # Build filter with the category value
            filter_ = self._build_category_filter(category, member, base_filter)

            # Polite delay between requests (skip first)
            if i > 0:
                time.sleep(1.0)

            df = self.fetch(filter=filter_)
            results[value] = df

            logger.debug(
                "Category member fetched",
                category=category.__name__,
                value=value,
                row_count=len(df),
            )

        logger.info(
            "Category-based fetch completed",
            category=category.__name__,
            total_results=len(results),
        )

        return results

    def _build_category_filter(
        self,
        category: FilterCategory,
        member: Any,
        base_filter: ScreenerFilter | None,
    ) -> ScreenerFilter:
        """Build a ScreenerFilter with a specific category value.

        Uses the module-level ``_CATEGORY_FIELD_MAP`` to resolve the
        ScreenerFilter field name from the category Enum type, replacing
        repetitive if/elif chains with a declarative lookup.

        Parameters
        ----------
        category : FilterCategory
            The Enum class being iterated.
        member : Any
            The specific Enum member value.
        base_filter : ScreenerFilter | None
            Optional base filter to copy fields from.

        Returns
        -------
        ScreenerFilter
            A new ScreenerFilter with the category value set.

        Raises
        ------
        ValueError
            If the category type is not in ``_CATEGORY_FIELD_MAP``.
        """
        from dataclasses import asdict

        # Start from base_filter or empty
        base = base_filter or ScreenerFilter()

        # Declarative lookup via module-level _CATEGORY_FIELD_MAP
        field_name = _CATEGORY_FIELD_MAP.get(category)
        if field_name is None:
            msg = f"Unsupported category type: {category}"
            raise ValueError(msg)

        # Create new filter with the category field set
        kwargs = asdict(base)
        kwargs[field_name] = member
        return ScreenerFilter(**kwargs)

    def download_csv(
        self,
        filter: ScreenerFilter | None = None,
        *,
        output_dir: str | Path | None = None,
        filename: str = "screener.csv",
    ) -> Path:
        """Fetch data and save as a CSV file with utf-8-sig encoding.

        Parameters
        ----------
        filter : ScreenerFilter | None
            Optional filter conditions for the API request.
        output_dir : str | Path | None
            Directory to save the CSV file.  If None, defaults to
            ``get_data_dir() / DEFAULT_OUTPUT_SUBDIR`` which respects
            the ``DATA_DIR`` environment variable.
        filename : str
            The output filename.  Defaults to ``"screener.csv"``.

        Returns
        -------
        Path
            The path to the saved CSV file.

        Examples
        --------
        >>> collector = ScreenerCollector()
        >>> path = collector.download_csv(output_dir="data/raw/nasdaq")
        >>> print(f"Saved to {path}")
        """
        output_dir = (
            Path(output_dir) if output_dir is not None else self._resolve_output_dir()
        )
        output_dir.mkdir(parents=True, exist_ok=True)
        output_path = (output_dir / filename).resolve()

        # Path traversal protection (CWE-22): ensure output stays within output_dir
        if not output_path.is_relative_to(output_dir.resolve()):
            msg = (
                f"Output path {output_path} is outside the output directory "
                f"{output_dir.resolve()}"
            )
            raise ValueError(msg)

        logger.info(
            "Downloading screener data to CSV",
            output_path=str(output_path),
        )

        df = self.fetch(filter=filter)
        df.to_csv(output_path, index=False, encoding="utf-8-sig")

        logger.info(
            "CSV saved",
            output_path=str(output_path),
            row_count=len(df),
        )

        return output_path

    def download_by_category(
        self,
        category: FilterCategory,
        *,
        output_dir: str | Path | None = None,
        base_filter: ScreenerFilter | None = None,
    ) -> list[Path]:
        """Fetch all category values and save each as a separate CSV file.

        Generates CSV files with naming convention:
        ``{category}_{value}_{YYYY-MM-DD}.csv``

        Parameters
        ----------
        category : FilterCategory
            The Enum class to iterate over.
        output_dir : str | Path
            Directory to save CSV files.
        base_filter : ScreenerFilter | None
            Optional base filter to merge with each category value.

        Returns
        -------
        list[Path]
            List of paths to the saved CSV files.

        Examples
        --------
        >>> from market.nasdaq.types import Sector
        >>> collector = ScreenerCollector()
        >>> paths = collector.download_by_category(
        ...     Sector, output_dir=Path("data/raw/nasdaq")
        ... )
        """
        resolved_dir = (
            Path(output_dir) if output_dir is not None else self._resolve_output_dir()
        )
        resolved_dir.mkdir(parents=True, exist_ok=True)
        today_str = date.today().isoformat()
        category_name = category.__name__.lower()

        logger.info(
            "Starting category-based CSV download",
            category=category_name,
            output_dir=str(resolved_dir),
        )

        resolved_output_dir = resolved_dir.resolve()
        results = self.fetch_by_category(category, base_filter=base_filter)
        paths: list[Path] = []

        for value, df in results.items():
            filename = f"{category_name}_{value}_{today_str}.csv"
            output_path = (resolved_dir / filename).resolve()

            # Path traversal protection (CWE-22)
            if not output_path.is_relative_to(resolved_output_dir):
                msg = (
                    f"Output path {output_path} is outside the output "
                    f"directory {resolved_output_dir}"
                )
                raise ValueError(msg)

            df.to_csv(output_path, index=False, encoding="utf-8-sig")
            paths.append(output_path)

            logger.debug(
                "Category CSV saved",
                filename=filename,
                row_count=len(df),
            )

        logger.info(
            "Category-based CSV download completed",
            category=category_name,
            file_count=len(paths),
        )

        return paths


__all__ = ["_CATEGORY_FIELD_MAP", "ScreenerCollector"]
