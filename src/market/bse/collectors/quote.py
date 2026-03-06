"""BSE Quote data collector with DataCollector ABC compliance.

This module provides ``QuoteCollector``, the main entry point for
fetching scrip quote data and historical price data from the BSE India API.
It inherits from ``DataCollector`` and implements the ``fetch()`` /
``validate()`` interface with additional convenience methods for
quote retrieval and historical data download.

Features
--------
- DataCollector ABC compliance (fetch / validate interface)
- Dependency injection for BseSession (testability)
- Single quote fetching via ``fetch_quote()``
- Historical CSV data fetching via ``fetch_historical()``

Examples
--------
Basic quote fetch:

>>> collector = QuoteCollector()
>>> quote = collector.fetch_quote("500325")
>>> print(f"Close: {quote.close}")

Historical data:

>>> df = collector.fetch_historical("500325")
>>> print(f"Found {len(df)} rows")

See Also
--------
market.base_collector : DataCollector abstract base class.
market.bse.session : BseSession with bot-blocking countermeasures.
market.bse.parsers : JSON response parser and CSV parser.
market.bse.types : ScripQuote dataclass.
market.nasdaq.collector : Reference DataCollector implementation.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

import pandas as pd

from market.base_collector import DataCollector
from market.bse.collectors._base import BseCollectorMixin
from market.bse.constants import BASE_URL
from market.bse.errors import BseParseError
from market.bse.parsers import parse_historical_csv, parse_quote_response
from utils_core.logging import get_logger

if TYPE_CHECKING:
    from market.bse.session import BseSession
    from market.bse.types import ScripQuote

logger = get_logger(__name__)

# Required columns for validation
_REQUIRED_COLUMNS: frozenset[str] = frozenset({"scrip_code", "scrip_name"})

# BSE API endpoints
_QUOTE_ENDPOINT: str = f"{BASE_URL}/getScripHeaderData"
_HISTORICAL_ENDPOINT: str = f"{BASE_URL}/StockReachGraph/stockreachgraphdata/1/"


class QuoteCollector(BseCollectorMixin, DataCollector):
    """Collector for BSE scrip quote and historical price data.

    Fetches quote data from the BSE India API, parsing the JSON response
    into ``ScripQuote`` dataclasses or pandas DataFrames.

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
    >>> collector = QuoteCollector()
    >>> df = collector.collect(scrip_code="500325")
    >>> print(f"Collected {len(df)} rows")

    >>> # With dependency injection for testing
    >>> from unittest.mock import MagicMock
    >>> mock_session = MagicMock(spec=BseSession)
    >>> collector = QuoteCollector(session=mock_session)
    """

    def __init__(self, session: BseSession | None = None) -> None:
        """Initialize QuoteCollector with optional session injection.

        Parameters
        ----------
        session : BseSession | None
            Pre-configured BseSession for dependency injection.
            If None, a new BseSession is created when needed.
        """
        BseCollectorMixin.__init__(self, session=session)

        logger.info(
            "QuoteCollector initialized",
            session_injected=session is not None,
        )

    def fetch(self, **kwargs: Any) -> pd.DataFrame:
        """Fetch scrip quote data from the BSE API as a DataFrame.

        Sends a GET request to the BSE API's ``getScripHeaderData``
        endpoint, parses the JSON response, and returns a single-row
        DataFrame with the quote data.

        Parameters
        ----------
        **kwargs : Any
            Keyword arguments.  Expected:
            - scrip_code (str): BSE scrip code (e.g., ``"500325"``).

        Returns
        -------
        pd.DataFrame
            Single-row DataFrame with columns matching ``ScripQuote`` fields.

        Raises
        ------
        BseParseError
            If the JSON response cannot be parsed.
        BseAPIError
            If the API returns an error status code.
        BseRateLimitError
            If rate limiting is detected.
        ValueError
            If ``scrip_code`` is not provided.

        Examples
        --------
        >>> collector = QuoteCollector()
        >>> df = collector.fetch(scrip_code="500325")
        >>> df["scrip_code"].iloc[0]
        '500325'
        """
        scrip_code: str | None = kwargs.get("scrip_code")
        if not scrip_code:
            msg = "scrip_code is required for fetch()"
            raise ValueError(msg)

        logger.info(
            "Fetching quote data",
            scrip_code=scrip_code,
        )

        quote = self.fetch_quote(scrip_code)

        # Convert ScripQuote to single-row DataFrame
        from dataclasses import asdict

        df = pd.DataFrame([asdict(quote)])

        logger.info(
            "Quote data fetched as DataFrame",
            scrip_code=scrip_code,
            columns=list(df.columns),
        )

        return df

    def validate(self, df: pd.DataFrame) -> bool:
        """Validate the fetched quote data.

        Checks that the DataFrame:
        - Is not empty
        - Contains the required columns (``scrip_code``, ``scrip_name``)

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
        >>> collector = QuoteCollector()
        >>> df = pd.DataFrame({"scrip_code": ["500325"], "scrip_name": ["RELIANCE"]})
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

    def fetch_quote(self, scrip_code: str) -> ScripQuote:
        """Fetch a single scrip quote from the BSE API.

        Sends a GET request to the BSE API's ``getScripHeaderData``
        endpoint and parses the JSON response into a ``ScripQuote``
        dataclass.

        Parameters
        ----------
        scrip_code : str
            BSE scrip code (e.g., ``"500325"`` for Reliance Industries).

        Returns
        -------
        ScripQuote
            A frozen dataclass containing the parsed quote data.

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
        >>> collector = QuoteCollector()
        >>> quote = collector.fetch_quote("500325")
        >>> quote.scrip_code
        '500325'
        """
        logger.info(
            "Fetching quote",
            scrip_code=scrip_code,
        )

        session, should_close = self._get_session()
        try:
            response = session.get_with_retry(
                _QUOTE_ENDPOINT,
                params={
                    "Ession_id": "",
                    "scripcode": scrip_code,
                },
            )

            json_data: dict[str, Any] = response.json()
            quote = parse_quote_response(json_data)

            logger.info(
                "Quote fetched",
                scrip_code=quote.scrip_code,
                scrip_name=quote.scrip_name,
            )

            return quote
        finally:
            if should_close:
                session.close()

    def fetch_historical(
        self,
        scrip_code: str,
    ) -> pd.DataFrame:
        """Fetch historical price data for a scrip from the BSE API.

        Downloads CSV data from the BSE historical data endpoint and
        parses it into a pandas DataFrame with cleaned numeric columns.

        Parameters
        ----------
        scrip_code : str
            BSE scrip code (e.g., ``"500325"`` for Reliance Industries).

        Returns
        -------
        pd.DataFrame
            DataFrame with historical price data (date, open, high, low,
            close, volume, etc.).

        Raises
        ------
        BseParseError
            If the CSV content cannot be parsed.
        BseAPIError
            If the API returns an error status code.
        BseRateLimitError
            If rate limiting is detected.

        Examples
        --------
        >>> collector = QuoteCollector()
        >>> df = collector.fetch_historical("500325")
        >>> len(df) > 0
        True
        """
        logger.info(
            "Fetching historical data",
            scrip_code=scrip_code,
        )

        url = f"{_HISTORICAL_ENDPOINT}{scrip_code}"

        session, should_close = self._get_session()
        try:
            response = session.get_with_retry(url)
            content = response.text

            if not content.strip():
                raise BseParseError(
                    f"Empty historical data response for scrip {scrip_code}",
                    raw_data=None,
                    field=None,
                )

            df = parse_historical_csv(content)

            logger.info(
                "Historical data fetched",
                scrip_code=scrip_code,
                row_count=len(df),
            )

            return df
        finally:
            if should_close:
                session.close()


__all__ = ["QuoteCollector"]
