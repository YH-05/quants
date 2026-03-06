"""BSE Bhavcopy (daily market data) collector with DataCollector ABC compliance.

This module provides ``BhavcopyCollector``, the entry point for fetching
daily Bhavcopy CSV files from the BSE India website.  It inherits from
``DataCollector`` and implements the ``fetch()`` / ``validate()`` interface
with additional convenience methods for equity, derivative, and date-range
fetching.

Features
--------
- DataCollector ABC compliance (fetch / validate interface)
- Dependency injection for BseSession (testability)
- Equity bhavcopy fetching via ``fetch_equity()``
- Derivative bhavcopy fetching via ``fetch_derivative()``
- Date range fetching via ``fetch_date_range()``
- URL pattern construction via ``_build_url()``

Examples
--------
Basic equity bhavcopy fetch:

>>> import datetime
>>> collector = BhavcopyCollector()
>>> df = collector.fetch_equity(datetime.date(2026, 3, 5))
>>> print(f"Found {len(df)} rows")

Date range fetch:

>>> df = collector.fetch_date_range(
...     datetime.date(2026, 3, 3),
...     datetime.date(2026, 3, 5),
... )

See Also
--------
market.base_collector : DataCollector abstract base class.
market.bse.session : BseSession with bot-blocking countermeasures.
market.bse.parsers : Bhavcopy CSV parser.
market.bse.types : BhavcopyType enum.
"""

from __future__ import annotations

import datetime
from typing import Any

import pandas as pd

from market.base_collector import DataCollector
from market.bse.constants import BHAVCOPY_DOWNLOAD_BASE_URL
from market.bse.parsers import parse_bhavcopy_csv
from market.bse.session import BseSession
from market.bse.types import BhavcopyType
from utils_core.logging import get_logger

logger = get_logger(__name__)

# Required columns for validation
_REQUIRED_COLUMNS: frozenset[str] = frozenset(
    {"scrip_code", "scrip_name", "trading_date"}
)

# URL patterns for different bhavcopy types
_EQUITY_URL_TEMPLATE: str = "{base}/BhavCopy_BSE_CM_0_0_0_{date}_F_0000.CSV"
_DERIVATIVES_URL_TEMPLATE: str = "{base}/BhavCopy_BSE_FO_0_0_0_{date}_F_0000.CSV"
_DEBT_URL_TEMPLATE: str = "{base}/BhavCopy_BSE_DM_0_0_0_{date}_F_0000.CSV"

_URL_TEMPLATES: dict[BhavcopyType, str] = {
    BhavcopyType.EQUITY: _EQUITY_URL_TEMPLATE,
    BhavcopyType.DERIVATIVES: _DERIVATIVES_URL_TEMPLATE,
    BhavcopyType.DEBT: _DEBT_URL_TEMPLATE,
}


class BhavcopyCollector(DataCollector):
    """Collector for BSE Bhavcopy (daily market data) CSV files.

    Fetches daily bhavcopy CSV files from the BSE India website,
    parses them into pandas DataFrames with cleaned numeric columns.

    The ``BseSession`` can be injected via the constructor for testing
    (dependency injection pattern).  When no session is provided, a new
    session is created internally for each operation.

    Parameters
    ----------
    session : BseSession | None
        Pre-configured BseSession instance.  If None, a new session is
        created internally when needed.

    Attributes
    ----------
    _session_instance : BseSession | None
        Injected session instance (None if creating internally).

    Examples
    --------
    >>> collector = BhavcopyCollector()
    >>> df = collector.fetch(date="2026-03-05")
    >>> print(f"Collected {len(df)} rows")

    >>> # With dependency injection for testing
    >>> from unittest.mock import MagicMock
    >>> mock_session = MagicMock(spec=BseSession)
    >>> collector = BhavcopyCollector(session=mock_session)
    """

    def __init__(self, session: BseSession | None = None) -> None:
        """Initialize BhavcopyCollector with optional session injection.

        Parameters
        ----------
        session : BseSession | None
            Pre-configured BseSession for dependency injection.
            If None, a new BseSession is created when needed.
        """
        self._session_instance: BseSession | None = session

        logger.info(
            "BhavcopyCollector initialized",
            session_injected=session is not None,
        )

    def _get_session(self) -> tuple[BseSession, bool]:
        """Resolve the session: use injected or create new.

        Returns
        -------
        tuple[BseSession, bool]
            A tuple of (session, should_close).  ``should_close`` is True
            when a new session was created internally and must be closed
            by the caller.
        """
        if self._session_instance is not None:
            return self._session_instance, False
        return BseSession(), True

    def _build_url(
        self,
        date: datetime.date,
        bhavcopy_type: BhavcopyType,
    ) -> str:
        """Build the download URL for a bhavcopy file.

        Parameters
        ----------
        date : datetime.date
            The trading date for the bhavcopy.
        bhavcopy_type : BhavcopyType
            The type of bhavcopy (equity, derivatives, debt).

        Returns
        -------
        str
            The full download URL.

        Examples
        --------
        >>> collector = BhavcopyCollector()
        >>> url = collector._build_url(
        ...     datetime.date(2026, 3, 5), BhavcopyType.EQUITY
        ... )
        >>> "20260305" in url
        True
        """
        date_str = date.strftime("%Y%m%d")
        template = _URL_TEMPLATES[bhavcopy_type]
        url = template.format(base=BHAVCOPY_DOWNLOAD_BASE_URL, date=date_str)

        logger.debug(
            "Built bhavcopy URL",
            date=date_str,
            bhavcopy_type=bhavcopy_type.value,
            url=url,
        )

        return url

    def fetch(self, **kwargs: Any) -> pd.DataFrame:
        """Fetch equity bhavcopy data for a given date.

        This is the DataCollector ABC interface method.  It fetches
        equity bhavcopy data for the specified date.

        Parameters
        ----------
        **kwargs : Any
            Keyword arguments.  Expected:
            - date (str): Trading date in ``YYYY-MM-DD`` format.

        Returns
        -------
        pd.DataFrame
            DataFrame with bhavcopy data.

        Raises
        ------
        ValueError
            If ``date`` is not provided.
        BseParseError
            If the CSV content cannot be parsed.

        Examples
        --------
        >>> collector = BhavcopyCollector()
        >>> df = collector.fetch(date="2026-03-05")
        """
        date_str: str | None = kwargs.get("date")
        if not date_str:
            msg = "date is required for fetch() (format: YYYY-MM-DD)"
            raise ValueError(msg)

        date = datetime.date.fromisoformat(date_str)
        return self.fetch_equity(date)

    def validate(self, df: pd.DataFrame) -> bool:
        """Validate the fetched bhavcopy data.

        Checks that the DataFrame:
        - Is not empty
        - Contains the required columns (scrip_code, scrip_name, trading_date)

        Parameters
        ----------
        df : pd.DataFrame
            DataFrame to validate.

        Returns
        -------
        bool
            True if the data is valid, False otherwise.
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

    def fetch_equity(self, date: datetime.date) -> pd.DataFrame:
        """Fetch equity bhavcopy for a specific date.

        Parameters
        ----------
        date : datetime.date
            The trading date.

        Returns
        -------
        pd.DataFrame
            DataFrame with equity bhavcopy data.

        Raises
        ------
        BseParseError
            If the CSV content cannot be parsed.
        BseAPIError
            If the download fails.

        Examples
        --------
        >>> import datetime
        >>> collector = BhavcopyCollector()
        >>> df = collector.fetch_equity(datetime.date(2026, 3, 5))
        """
        logger.info("Fetching equity bhavcopy", date=str(date))

        url = self._build_url(date, BhavcopyType.EQUITY)
        return self._download_and_parse(url, date)

    def fetch_derivative(self, date: datetime.date) -> pd.DataFrame:
        """Fetch derivative bhavcopy for a specific date.

        Parameters
        ----------
        date : datetime.date
            The trading date.

        Returns
        -------
        pd.DataFrame
            DataFrame with derivative bhavcopy data.

        Raises
        ------
        BseParseError
            If the CSV content cannot be parsed.
        BseAPIError
            If the download fails.

        Examples
        --------
        >>> import datetime
        >>> collector = BhavcopyCollector()
        >>> df = collector.fetch_derivative(datetime.date(2026, 3, 5))
        """
        logger.info("Fetching derivative bhavcopy", date=str(date))

        url = self._build_url(date, BhavcopyType.DERIVATIVES)
        return self._download_and_parse(url, date)

    def fetch_date_range(
        self,
        start: datetime.date,
        end: datetime.date,
        bhavcopy_type: BhavcopyType = BhavcopyType.EQUITY,
    ) -> pd.DataFrame:
        """Fetch bhavcopy data for a date range.

        Iterates over each date in the range (inclusive) and fetches
        the bhavcopy.  Dates that fail (e.g. holidays, weekends) are
        logged and skipped.

        Parameters
        ----------
        start : datetime.date
            Start date (inclusive).
        end : datetime.date
            End date (inclusive).
        bhavcopy_type : BhavcopyType
            The type of bhavcopy to fetch (default: EQUITY).

        Returns
        -------
        pd.DataFrame
            Concatenated DataFrame for all successful dates.

        Raises
        ------
        ValueError
            If start date is after end date.

        Examples
        --------
        >>> import datetime
        >>> collector = BhavcopyCollector()
        >>> df = collector.fetch_date_range(
        ...     datetime.date(2026, 3, 3),
        ...     datetime.date(2026, 3, 5),
        ... )
        """
        if start > end:
            msg = f"start date ({start}) must not be after end date ({end})"
            raise ValueError(msg)

        logger.info(
            "Fetching bhavcopy date range",
            start=str(start),
            end=str(end),
            bhavcopy_type=bhavcopy_type.value,
        )

        frames: list[pd.DataFrame] = []
        current = start
        one_day = datetime.timedelta(days=1)

        session, should_close = self._get_session()
        try:
            while current <= end:
                url = self._build_url(current, bhavcopy_type)
                try:
                    content = session.download(url)
                    df = parse_bhavcopy_csv(content)
                    if not df.empty:
                        frames.append(df)
                    logger.debug(
                        "Date fetched successfully",
                        date=str(current),
                        row_count=len(df),
                    )
                except Exception:
                    logger.warning(
                        "Failed to fetch bhavcopy for date, skipping",
                        date=str(current),
                        exc_info=True,
                    )
                current += one_day
        finally:
            if should_close:
                session.close()

        if not frames:
            logger.warning(
                "No bhavcopy data fetched for date range",
                start=str(start),
                end=str(end),
            )
            return pd.DataFrame()

        result = pd.concat(frames, ignore_index=True)

        logger.info(
            "Date range fetch completed",
            start=str(start),
            end=str(end),
            total_rows=len(result),
            days_fetched=len(frames),
        )

        return result

    def _download_and_parse(
        self,
        url: str,
        date: datetime.date,
    ) -> pd.DataFrame:
        """Download a bhavcopy CSV and parse it.

        Parameters
        ----------
        url : str
            The download URL.
        date : datetime.date
            The trading date (for logging).

        Returns
        -------
        pd.DataFrame
            Parsed bhavcopy DataFrame.
        """
        session, should_close = self._get_session()
        try:
            content = session.download(url)
            df = parse_bhavcopy_csv(content)

            logger.info(
                "Bhavcopy fetched",
                date=str(date),
                row_count=len(df),
            )

            return df
        finally:
            if should_close:
                session.close()


__all__ = ["BhavcopyCollector"]
