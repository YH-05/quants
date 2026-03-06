"""BSE Index data collector with DataCollector ABC compliance.

This module provides ``IndexCollector``, the entry point for fetching
BSE index historical data (SENSEX, BANKEX, BSE 100, etc.) from the
BSE India API.  It inherits from ``DataCollector`` and implements
the ``fetch()`` / ``validate()`` interface with additional convenience
methods for listing indices and fetching historical data.

Features
--------
- DataCollector ABC compliance (fetch / validate interface)
- Dependency injection for BseSession (testability)
- Index listing via ``list_indices()``
- Historical index data fetching via ``fetch_historical()``

Examples
--------
Basic index data fetch:

>>> collector = IndexCollector()
>>> df = collector.fetch_historical(IndexName.SENSEX)
>>> print(f"Found {len(df)} rows")

List all available indices:

>>> indices = IndexCollector.list_indices()
>>> "SENSEX" in indices
True

See Also
--------
market.base_collector : DataCollector abstract base class.
market.bse.session : BseSession with bot-blocking countermeasures.
market.bse.parsers : Index data parser.
market.bse.types : IndexName enum.
market.bse.collectors.quote : Reference DataCollector implementation.
"""

from __future__ import annotations

import datetime
from typing import TYPE_CHECKING, Any

import pandas as pd

from market.base_collector import DataCollector
from market.bse.constants import BASE_URL
from market.bse.errors import BseParseError
from market.bse.parsers import parse_index_data
from market.bse.session import BseSession
from market.bse.types import IndexName
from utils_core.logging import get_logger

logger = get_logger(__name__)

# Required columns for validation
_REQUIRED_COLUMNS: frozenset[str] = frozenset({"date", "close"})

# BSE API endpoint for index data
_INDEX_ENDPOINT: str = f"{BASE_URL}/IndexArchDaily"

# Default date range: 1 year
_DEFAULT_DAYS: int = 365


class IndexCollector(DataCollector):
    """Collector for BSE index historical data.

    Fetches index data from the BSE India API, parsing the JSON response
    into pandas DataFrames with cleaned numeric columns.

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
    >>> collector = IndexCollector()
    >>> df = collector.collect(index_name="SENSEX")
    >>> print(f"Collected {len(df)} rows")

    >>> # With dependency injection for testing
    >>> from unittest.mock import MagicMock
    >>> mock_session = MagicMock(spec=BseSession)
    >>> collector = IndexCollector(session=mock_session)
    """

    def __init__(self, session: BseSession | None = None) -> None:
        """Initialize IndexCollector with optional session injection.

        Parameters
        ----------
        session : BseSession | None
            Pre-configured BseSession for dependency injection.
            If None, a new BseSession is created when needed.
        """
        self._session_instance: BseSession | None = session

        logger.info(
            "IndexCollector initialized",
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

    @staticmethod
    def list_indices() -> list[str]:
        """Return a list of all available BSE index names.

        The returned names correspond to the ``IndexName`` enum values
        and can be used as the ``index_name`` parameter for
        ``fetch_historical()``.

        Returns
        -------
        list[str]
            Sorted list of available index names.

        Examples
        --------
        >>> indices = IndexCollector.list_indices()
        >>> "SENSEX" in indices
        True
        >>> "BANKEX" in indices
        True
        """
        return sorted(member.value for member in IndexName)

    def fetch(self, **kwargs: Any) -> pd.DataFrame:
        """Fetch index data from the BSE API as a DataFrame.

        This is the DataCollector ABC interface method.  It fetches
        historical index data for the specified index name.

        Parameters
        ----------
        **kwargs : Any
            Keyword arguments.  Expected:
            - index_name (str): BSE index name (e.g., ``"SENSEX"``).
            - start (str | None): Start date in ``YYYY-MM-DD`` format.
            - end (str | None): End date in ``YYYY-MM-DD`` format.

        Returns
        -------
        pd.DataFrame
            DataFrame with historical index data.

        Raises
        ------
        ValueError
            If ``index_name`` is not provided.
        BseParseError
            If the JSON response cannot be parsed.

        Examples
        --------
        >>> collector = IndexCollector()
        >>> df = collector.fetch(index_name="SENSEX")
        >>> "close" in df.columns
        True
        """
        index_name: str | None = kwargs.get("index_name")
        if not index_name:
            msg = "index_name is required for fetch()"
            raise ValueError(msg)

        # Resolve IndexName enum
        try:
            index_enum = IndexName(index_name)
        except ValueError:
            msg = (
                f"Unknown index name: {index_name!r}. "
                f"Available: {IndexCollector.list_indices()}"
            )
            raise ValueError(msg) from None

        start_str: str | None = kwargs.get("start")
        end_str: str | None = kwargs.get("end")

        start = datetime.date.fromisoformat(start_str) if start_str else None
        end = datetime.date.fromisoformat(end_str) if end_str else None

        return self.fetch_historical(index_enum, start=start, end=end)

    def validate(self, df: pd.DataFrame) -> bool:
        """Validate the fetched index data.

        Checks that the DataFrame:
        - Is not empty
        - Contains the required columns (``date``, ``close``)

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
        >>> import pandas as pd
        >>> collector = IndexCollector()
        >>> df = pd.DataFrame({"date": ["2026-01-01"], "close": [74000.0]})
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

    def fetch_historical(
        self,
        index_name: IndexName,
        *,
        start: datetime.date | None = None,
        end: datetime.date | None = None,
    ) -> pd.DataFrame:
        """Fetch historical data for a BSE index.

        Sends a GET request to the BSE Index API and parses the JSON
        response into a pandas DataFrame with cleaned columns.

        Parameters
        ----------
        index_name : IndexName
            The BSE index to fetch (e.g., ``IndexName.SENSEX``).
        start : datetime.date | None
            Start date for the data range.  Defaults to 1 year before
            *end*.
        end : datetime.date | None
            End date for the data range.  Defaults to today.

        Returns
        -------
        pd.DataFrame
            DataFrame with columns including ``date``, ``open``,
            ``high``, ``low``, ``close``, and optionally ``pe``,
            ``pb``, ``yield``.

        Raises
        ------
        BseParseError
            If the JSON response cannot be parsed.
        BseAPIError
            If the API returns an error status code.
        BseRateLimitError
            If rate limiting is detected.

        Examples
        --------
        >>> collector = IndexCollector()
        >>> df = collector.fetch_historical(IndexName.SENSEX)
        >>> len(df) > 0
        True
        """
        if end is None:
            end = datetime.date.today()
        if start is None:
            start = end - datetime.timedelta(days=_DEFAULT_DAYS)

        logger.info(
            "Fetching index historical data",
            index_name=index_name.value,
            start=str(start),
            end=str(end),
        )

        # BSE API expects dates in dd/MM/yyyy format
        start_str = start.strftime("%d/%m/%Y")
        end_str = end.strftime("%d/%m/%Y")

        session, should_close = self._get_session()
        try:
            response = session.get_with_retry(
                _INDEX_ENDPOINT,
                params={
                    "index": index_name.value,
                    "fmdt": start_str,
                    "todt": end_str,
                },
            )

            json_data: list[dict[str, Any]] = response.json()

            if not isinstance(json_data, list):
                raise BseParseError(
                    f"Expected list from index API, got {type(json_data).__name__}",
                    raw_data=str(json_data)[:500],
                    field=None,
                )

            if not json_data:
                logger.warning(
                    "Empty response from index API",
                    index_name=index_name.value,
                    start=str(start),
                    end=str(end),
                )
                return pd.DataFrame()

            df = parse_index_data(json_data)

            logger.info(
                "Index historical data fetched",
                index_name=index_name.value,
                row_count=len(df),
            )

            return df
        finally:
            if should_close:
                session.close()


__all__ = ["IndexCollector"]
