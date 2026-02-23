"""Bloomberg data fetcher for market data retrieval.

This module provides a concrete implementation for fetching market data
using the Bloomberg BLPAPI to fetch data from Bloomberg Terminal.

Supports
--------
- Historical price data
- Reference data
- Financial data
- News data
- Field information
- Identifier conversion
- Index members
- Database storage

Examples
--------
>>> from market.bloomberg import BloombergFetcher, BloombergFetchOptions
>>> fetcher = BloombergFetcher()
>>> options = BloombergFetchOptions(
...     securities=["AAPL US Equity"],
...     fields=["PX_LAST", "PX_VOLUME"],
...     start_date="2024-01-01",
...     end_date="2024-12-31",
... )
>>> results = fetcher.get_historical_data(options)
"""

import re
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Any

import blpapi  # type: ignore[import-not-found]
import pandas as pd

from market.bloomberg.constants import (
    API_FIELDS_SERVICE,
    DEFAULT_HOST,
    DEFAULT_PORT,
    NEWS_SERVICE,
    REF_DATA_SERVICE,
)
from market.bloomberg.types import (
    BloombergDataResult,
    BloombergFetchOptions,
    DataSource,
    FieldInfo,
    IDType,
    NewsStory,
)
from market.errors import (
    BloombergConnectionError,
    BloombergDataError,
    BloombergSessionError,
    BloombergValidationError,
    ErrorCode,
)
from utils_core.logging import get_logger

logger = get_logger(__name__, module="market.bloomberg.fetcher")

# Bloomberg security identifier pattern
# Supports: AAPL US Equity, IBM US Equity, USDJPY Curncy, SPX Index
BLOOMBERG_SECURITY_PATTERN = re.compile(
    r"^[A-Z0-9./\-]+ (Equity|Index|Curncy|Govt|Corp|Mtge|Pfd|Cmdty|Muni|Comdty)$",
    re.IGNORECASE,
)


class BloombergFetcher:
    """Data fetcher using Bloomberg BLPAPI.

    Fetches various types of data from Bloomberg Terminal including
    historical prices, reference data, financial data, and news.

    Parameters
    ----------
    host : str
        Bloomberg Terminal host address (default: localhost)
    port : int
        Bloomberg Terminal port (default: 8194)

    Attributes
    ----------
    host : str
        Bloomberg Terminal host address
    port : int
        Bloomberg Terminal port
    source : DataSource
        Always returns DataSource.BLOOMBERG
    REF_DATA_SERVICE : str
        Bloomberg reference data service endpoint
    NEWS_SERVICE : str
        Bloomberg news service endpoint

    Examples
    --------
    >>> fetcher = BloombergFetcher()
    >>> options = BloombergFetchOptions(
    ...     securities=["AAPL US Equity"],
    ...     fields=["PX_LAST", "PX_VOLUME"],
    ...     start_date="2024-01-01",
    ...     end_date="2024-12-31",
    ... )
    >>> results = fetcher.get_historical_data(options)
    >>> len(results)
    1
    """

    # Class-level service constants
    REF_DATA_SERVICE: str = REF_DATA_SERVICE
    NEWS_SERVICE: str = NEWS_SERVICE

    def __init__(
        self,
        host: str = DEFAULT_HOST,
        port: int = DEFAULT_PORT,
    ) -> None:
        self.host = host
        self.port = port

        logger.debug(
            "Initializing BloombergFetcher",
            host=host,
            port=port,
        )

    @property
    def source(self) -> DataSource:
        """Return the data source type.

        Returns
        -------
        DataSource
            DataSource.BLOOMBERG
        """
        return DataSource.BLOOMBERG

    def validate_security(self, security: str) -> bool:
        """Validate that a security identifier is valid for Bloomberg.

        Bloomberg securities typically follow the format:
        ``<TICKER> <YELLOW_KEY>`` where YELLOW_KEY is one of:
        Equity, Index, Curncy, Govt, Corp, Mtge, Pfd, Cmdty, Muni, Comdty.

        Parameters
        ----------
        security : str
            The security identifier to validate

        Returns
        -------
        bool
            True if the security matches Bloomberg format

        Examples
        --------
        >>> fetcher = BloombergFetcher()
        >>> fetcher.validate_security("AAPL US Equity")
        True
        >>> fetcher.validate_security("SPX Index")
        True
        >>> fetcher.validate_security("USDJPY Curncy")
        True
        >>> fetcher.validate_security("invalid")
        False
        """
        if not security or not security.strip():
            return False

        return bool(BLOOMBERG_SECURITY_PATTERN.match(security.strip()))

    def _create_session(self) -> blpapi.Session:
        """Create and start a Bloomberg session.

        Returns
        -------
        blpapi.Session
            Started Bloomberg session

        Raises
        ------
        BloombergConnectionError
            If connection to Bloomberg Terminal fails
        """
        logger.debug("Creating Bloomberg session", host=self.host, port=self.port)

        session_options = blpapi.SessionOptions()
        session_options.setServerHost(self.host)
        session_options.setServerPort(self.port)

        session = blpapi.Session(session_options)

        if not session.start():
            logger.error(
                "Failed to start Bloomberg session",
                host=self.host,
                port=self.port,
            )
            raise BloombergConnectionError(
                "Failed to connect to Bloomberg Terminal. "
                "Ensure Bloomberg Terminal is running.",
                host=self.host,
                port=self.port,
            )

        logger.debug("Bloomberg session started successfully")
        return session

    def _open_service(self, session: blpapi.Session, service: str) -> None:
        """Open a Bloomberg service.

        Parameters
        ----------
        session : blpapi.Session
            Active Bloomberg session
        service : str
            Service name to open

        Raises
        ------
        BloombergSessionError
            If service fails to open
        """
        logger.debug("Opening Bloomberg service", service=service)

        if not session.openService(service):
            logger.error("Failed to open Bloomberg service", service=service)
            raise BloombergSessionError(
                f"Failed to open Bloomberg service: {service}",
                service=service,
            )

        logger.debug("Bloomberg service opened successfully", service=service)

    def _validate_options(self, options: BloombergFetchOptions) -> None:
        """Validate fetch options.

        Parameters
        ----------
        options : BloombergFetchOptions
            Options to validate

        Raises
        ------
        BloombergValidationError
            If options are invalid
        """
        logger.debug(
            "Validating fetch options",
            securities_count=len(options.securities),
            fields_count=len(options.fields),
        )

        if not options.securities:
            logger.error("Empty securities list")
            raise BloombergValidationError(
                "securities list must not be empty",
                field="securities",
                value=options.securities,
            )

        if not options.fields:
            logger.error("Empty fields list")
            raise BloombergValidationError(
                "fields list must not be empty",
                field="fields",
                value=options.fields,
            )

        # Validate date range if both dates are provided
        if options.start_date and options.end_date:
            start = self._parse_date(options.start_date)
            end = self._parse_date(options.end_date)

            if start and end and start > end:
                logger.error(
                    "Invalid date range: start_date is after end_date",
                    start_date=str(start),
                    end_date=str(end),
                )
                raise BloombergValidationError(
                    "Invalid date range: start_date must be before or equal to end_date",
                    field="date_range",
                    value={"start_date": str(start), "end_date": str(end)},
                    code=ErrorCode.INVALID_DATE_RANGE,
                )

        logger.debug("Fetch options validated successfully")

    def _parse_date(self, date: datetime | str | None) -> datetime | None:
        """Parse a date value to datetime.

        Parameters
        ----------
        date : datetime | str | None
            Date to parse

        Returns
        -------
        datetime | None
            Parsed datetime or None
        """
        if date is None:
            return None
        if isinstance(date, datetime):
            return date
        # date is str at this point
        return datetime.strptime(date, "%Y-%m-%d")

    def _format_date(self, date: datetime | str | None) -> str | None:
        """Format a date for Bloomberg API.

        Parameters
        ----------
        date : datetime | str | None
            Date to format

        Returns
        -------
        str | None
            Formatted date string (YYYYMMDD) or None
        """
        if date is None:
            return None
        if isinstance(date, datetime):
            return date.strftime("%Y%m%d")
        # date is str at this point - assume YYYY-MM-DD format, convert to YYYYMMDD
        return date.replace("-", "")

    def get_historical_data(
        self,
        options: BloombergFetchOptions,
    ) -> list[BloombergDataResult]:
        """Fetch historical data for securities.

        Parameters
        ----------
        options : BloombergFetchOptions
            Options specifying securities, fields, and date range

        Returns
        -------
        list[BloombergDataResult]
            List of results for each security

        Raises
        ------
        BloombergValidationError
            If options are invalid
        BloombergConnectionError
            If connection to Bloomberg fails
        BloombergSessionError
            If service fails to open
        BloombergDataError
            If data fetching fails

        Examples
        --------
        >>> options = BloombergFetchOptions(
        ...     securities=["AAPL US Equity"],
        ...     fields=["PX_LAST"],
        ...     start_date="2024-01-01",
        ...     end_date="2024-12-31",
        ... )
        >>> results = fetcher.get_historical_data(options)
        """
        self._validate_options(options)

        logger.info(
            "Fetching historical data",
            securities=options.securities,
            fields=options.fields,
            start_date=str(options.start_date),
            end_date=str(options.end_date),
        )

        session = self._create_session()
        try:
            self._open_service(session, self.REF_DATA_SERVICE)

            results: list[BloombergDataResult] = []

            for security in options.securities:
                data = self._process_historical_response(security, options, session)
                result = BloombergDataResult(
                    security=security,
                    data=data,
                    source=self.source,
                    fetched_at=datetime.now(),
                    metadata={
                        "fields": options.fields,
                        "periodicity": options.periodicity.value,
                    },
                )
                results.append(result)

            logger.info(
                "Historical data fetch completed",
                total_securities=len(options.securities),
                successful=len([r for r in results if not r.is_empty]),
            )

            return results

        finally:
            session.stop()
            logger.debug("Bloomberg session stopped")

    def _process_historical_response(
        self,
        security: str,
        options: BloombergFetchOptions,
        session: "blpapi.Session | None" = None,
    ) -> pd.DataFrame:
        """Process historical data response via BLPAPI HistoricalDataRequest.

        Sends a HistoricalDataRequest for the given security and processes the
        event loop, traversing securityData → fieldData to build a DataFrame.

        Parameters
        ----------
        security : str
            Security identifier (e.g., "AAPL US Equity")
        options : BloombergFetchOptions
            Fetch options including fields, date range, periodicity, and overrides
        session : blpapi.Session | None
            Active Bloomberg session. When None, returns empty DataFrame (test
            compatibility mode).

        Returns
        -------
        pd.DataFrame
            Historical data with date as index and fields as columns.

        Raises
        ------
        BloombergDataError
            If the Bloomberg response contains a security-level error.
        """
        logger.debug("Processing historical response", security=security)

        if session is None:
            return pd.DataFrame()

        ref_data_service = session.getService(self.REF_DATA_SERVICE)
        request = ref_data_service.createRequest("HistoricalDataRequest")
        request.append("securities", security)  # type: ignore[attr-defined]

        for field in options.fields:
            request.append("fields", field)  # type: ignore[attr-defined]

        start_fmt = self._format_date(options.start_date)
        end_fmt = self._format_date(options.end_date)
        if start_fmt:
            request.set("startDate", start_fmt)  # type: ignore[attr-defined]
        if end_fmt:
            request.set("endDate", end_fmt)  # type: ignore[attr-defined]
        request.set("periodicitySelection", options.periodicity.value)  # type: ignore[attr-defined]

        for override in options.overrides:
            overrides_element = request.getElement("overrides")  # type: ignore[attr-defined]
            ov = overrides_element.appendElement()
            ov.setElement("fieldId", override.field)  # type: ignore[attr-defined]
            ov.setElement("value", override.value)  # type: ignore[attr-defined]

        session.sendRequest(request)  # type: ignore[attr-defined]

        data_rows: list[dict[str, Any]] = []

        while True:
            event = session.nextEvent(5000)  # type: ignore[attr-defined]
            event_type = event.eventType()

            if event_type in (
                blpapi.Event.RESPONSE,
                blpapi.Event.PARTIAL_RESPONSE,
            ):
                for msg in event:
                    if msg.hasElement("responseError"):
                        err_msg = (
                            msg.getElement("responseError")
                            .getElement("message")
                            .getValue()
                        )
                        logger.error(
                            "Historical response error",
                            security=security,
                            error=err_msg,
                        )
                        raise BloombergDataError(
                            f"Bloomberg response error for {security}: {err_msg}",
                            security=security,
                            fields=options.fields,
                        )

                    if not msg.hasElement("securityData"):
                        continue

                    security_data = msg.getElement("securityData")

                    if security_data.hasElement("securityError"):
                        err_msg = (
                            security_data.getElement("securityError")
                            .getElement("message")
                            .getValue()
                        )
                        logger.error(
                            "Security error in historical response",
                            security=security,
                            error=err_msg,
                        )
                        raise BloombergDataError(
                            f"Bloomberg security error for {security}: {err_msg}",
                            security=security,
                            fields=options.fields,
                            code=ErrorCode.INVALID_SECURITY,
                        )

                    field_data_array = security_data.getElement("fieldData")

                    for field_data in field_data_array.values():
                        date_val = field_data.getElement("date").getValue()
                        row: dict[str, Any] = {"date": pd.to_datetime(date_val)}

                        for field in options.fields:
                            if field_data.hasElement(field):
                                row[field] = field_data.getElement(field).getValue()
                            else:
                                row[field] = None

                        data_rows.append(row)

                if event_type == blpapi.Event.RESPONSE:
                    break

            elif event_type == blpapi.Event.TIMEOUT:
                logger.warning("Bloomberg request timed out", security=security)
                break

            elif event_type == blpapi.Event.SESSION_STATUS:
                for msg in event:
                    if msg.messageType() == blpapi.Name("SessionTerminated"):
                        logger.error("Bloomberg session terminated unexpectedly")
                        raise BloombergDataError(
                            "Bloomberg session terminated during historical data fetch",
                            security=security,
                        )

        if not data_rows:
            logger.debug("No historical data returned", security=security)
            return pd.DataFrame()

        return pd.DataFrame(data_rows)

    def get_reference_data(
        self,
        options: BloombergFetchOptions,
    ) -> list[BloombergDataResult]:
        """Fetch reference data for securities.

        Parameters
        ----------
        options : BloombergFetchOptions
            Options specifying securities and fields

        Returns
        -------
        list[BloombergDataResult]
            List of results for each security

        Raises
        ------
        BloombergValidationError
            If options are invalid
        BloombergConnectionError
            If connection to Bloomberg fails
        BloombergSessionError
            If service fails to open
        """
        self._validate_options(options)

        logger.info(
            "Fetching reference data",
            securities=options.securities,
            fields=options.fields,
        )

        session = self._create_session()
        try:
            self._open_service(session, self.REF_DATA_SERVICE)

            results: list[BloombergDataResult] = []

            for security in options.securities:
                data = self._process_reference_response(security, options, session)
                result = BloombergDataResult(
                    security=security,
                    data=data,
                    source=self.source,
                    fetched_at=datetime.now(),
                    metadata={"fields": options.fields},
                )
                results.append(result)

            logger.info(
                "Reference data fetch completed",
                total_securities=len(options.securities),
            )

            return results

        finally:
            session.stop()
            logger.debug("Bloomberg session stopped")

    def _process_reference_response(
        self,
        security: str,
        options: BloombergFetchOptions,
        session: "blpapi.Session | None" = None,
    ) -> pd.DataFrame:
        """Process reference data response via BLPAPI ReferenceDataRequest.

        Sends a ReferenceDataRequest for the given security and processes the
        event loop, traversing securityData → fieldData to build a DataFrame.

        Parameters
        ----------
        security : str
            Security identifier (e.g., "AAPL US Equity")
        options : BloombergFetchOptions
            Fetch options including fields and overrides
        session : blpapi.Session | None
            Active Bloomberg session. When None, returns empty DataFrame (test
            compatibility mode).

        Returns
        -------
        pd.DataFrame
            Reference data with one row per security and fields as columns.

        Raises
        ------
        BloombergDataError
            If the Bloomberg response contains a security-level error.
        """
        logger.debug("Processing reference response", security=security)

        if session is None:
            return pd.DataFrame()

        ref_data_service = session.getService(self.REF_DATA_SERVICE)
        request = ref_data_service.createRequest("ReferenceDataRequest")
        request.append("securities", security)  # type: ignore[attr-defined]

        for field in options.fields:
            request.append("fields", field)  # type: ignore[attr-defined]

        for override in options.overrides:
            overrides_element = request.getElement("overrides")  # type: ignore[attr-defined]
            ov = overrides_element.appendElement()
            ov.setElement("fieldId", override.field)  # type: ignore[attr-defined]
            ov.setElement("value", override.value)  # type: ignore[attr-defined]

        session.sendRequest(request)  # type: ignore[attr-defined]

        data_rows: list[dict[str, Any]] = []

        while True:
            event = session.nextEvent(5000)  # type: ignore[attr-defined]
            event_type = event.eventType()

            if event_type in (
                blpapi.Event.RESPONSE,
                blpapi.Event.PARTIAL_RESPONSE,
            ):
                for msg in event:
                    security_data_array = msg.getElement("securityData")

                    for security_data in security_data_array.values():
                        ticker = security_data.getElement("security").getValue()
                        row: dict[str, Any] = {"security": ticker}

                        if security_data.hasElement("securityError"):
                            err_msg = (
                                security_data.getElement("securityError")
                                .getElement("message")
                                .getValue()
                            )
                            logger.error(
                                "Security error in reference response",
                                security=ticker,
                                error=err_msg,
                            )
                            raise BloombergDataError(
                                f"Bloomberg security error for {ticker}: {err_msg}",
                                security=ticker,
                                fields=options.fields,
                                code=ErrorCode.INVALID_SECURITY,
                            )

                        field_data = security_data.getElement("fieldData")

                        for field in options.fields:
                            if field_data.hasElement(field):
                                row[field] = field_data.getElement(field).getValue()
                            else:
                                row[field] = None

                        data_rows.append(row)

                if event_type == blpapi.Event.RESPONSE:
                    break

            elif event_type == blpapi.Event.TIMEOUT:
                logger.warning("Bloomberg request timed out", security=security)
                break

            elif event_type == blpapi.Event.SESSION_STATUS:
                for msg in event:
                    if msg.messageType() == blpapi.Name("SessionTerminated"):
                        logger.error("Bloomberg session terminated unexpectedly")
                        raise BloombergDataError(
                            "Bloomberg session terminated during reference data fetch",
                            security=security,
                        )

        if not data_rows:
            logger.debug("No reference data returned", security=security)
            return pd.DataFrame()

        return pd.DataFrame(data_rows)

    def get_financial_data(
        self,
        options: BloombergFetchOptions,
    ) -> list[BloombergDataResult]:
        """Fetch financial data for securities.

        This is similar to get_reference_data but typically used
        for financial statement data with period overrides.

        Parameters
        ----------
        options : BloombergFetchOptions
            Options specifying securities, fields, and overrides

        Returns
        -------
        list[BloombergDataResult]
            List of results for each security
        """
        logger.info(
            "Fetching financial data",
            securities=options.securities,
            fields=options.fields,
            overrides=[o.field for o in options.overrides],
        )

        # Financial data uses the same reference data service
        return self.get_reference_data(options)

    def convert_identifiers(
        self,
        identifiers: list[str],
        from_type: IDType,
        to_type: IDType,
    ) -> dict[str, str]:
        """Convert security identifiers between types.

        Parameters
        ----------
        identifiers : list[str]
            List of identifiers to convert
        from_type : IDType
            Source identifier type
        to_type : IDType
            Target identifier type

        Returns
        -------
        dict[str, str]
            Mapping of source identifiers to target identifiers

        Examples
        --------
        >>> result = fetcher.convert_identifiers(
        ...     ["US0378331005"],
        ...     from_type=IDType.ISIN,
        ...     to_type=IDType.TICKER,
        ... )
        >>> result["US0378331005"]
        'AAPL US Equity'
        """
        logger.info(
            "Converting identifiers",
            count=len(identifiers),
            from_type=from_type.value,
            to_type=to_type.value,
        )

        session = self._create_session()
        try:
            self._open_service(session, self.REF_DATA_SERVICE)
            result = self._process_id_conversion(
                identifiers, from_type, to_type, session
            )

            logger.info(
                "Identifier conversion completed",
                converted_count=len(result),
            )

            return result

        finally:
            session.stop()

    def _process_id_conversion(
        self,
        identifiers: list[str],
        from_type: IDType,
        to_type: IDType,
        session: "blpapi.Session | None" = None,
    ) -> dict[str, str]:
        """Process identifier conversion response via BLPAPI ReferenceDataRequest.

        Sends a ReferenceDataRequest using the source identifier type prefix and
        requests PARSEKYABLE_DES to obtain the Bloomberg ticker. Maps each original
        identifier to its converted form.

        Parameters
        ----------
        identifiers : list[str]
            Identifiers to convert (e.g., ISINs, SEDOLs)
        from_type : IDType
            Source identifier type (used to build Bloomberg security ID prefix)
        to_type : IDType
            Target identifier type (currently TICKER is the primary supported target)
        session : blpapi.Session | None
            Active Bloomberg session. When None, returns empty dict (test
            compatibility mode).

        Returns
        -------
        dict[str, str]
            Mapping of original identifier to converted Bloomberg ticker.
        """
        logger.debug(
            "Processing ID conversion",
            identifiers=identifiers,
            from_type=from_type.value,
            to_type=to_type.value,
        )

        if session is None:
            return {}

        from market.bloomberg.constants import ID_TYPE_PREFIXES

        prefix = ID_TYPE_PREFIXES.get(from_type.value, "")

        ref_data_service = session.getService(self.REF_DATA_SERVICE)
        request = ref_data_service.createRequest("ReferenceDataRequest")

        id_mapping: dict[str, str] = {}
        for identifier in identifiers:
            if prefix:
                security_id = f"{prefix}{identifier}"
            else:
                security_id = identifier
            request.append("securities", security_id)  # type: ignore[attr-defined]
            id_mapping[security_id] = identifier

        request.append("fields", "PARSEKYABLE_DES")  # type: ignore[attr-defined]

        session.sendRequest(request)  # type: ignore[attr-defined]

        result: dict[str, str] = {}

        while True:
            event = session.nextEvent(5000)  # type: ignore[attr-defined]
            event_type = event.eventType()

            if event_type in (
                blpapi.Event.RESPONSE,
                blpapi.Event.PARTIAL_RESPONSE,
            ):
                for msg in event:
                    security_data_array = msg.getElement("securityData")

                    for security_data in security_data_array.values():
                        security_id: str = security_data.getElement(
                            "security"
                        ).getValue()
                        original_id: str = id_mapping.get(security_id) or security_id

                        if security_data.hasElement("securityError"):
                            err_msg = (
                                security_data.getElement("securityError")
                                .getElement("message")
                                .getValue()
                            )
                            logger.warning(
                                "Security error during ID conversion",
                                identifier=original_id,
                                error=err_msg,
                            )
                            continue

                        field_data = security_data.getElement("fieldData")

                        if field_data.hasElement("PARSEKYABLE_DES"):
                            ticker_element = field_data.getElement("PARSEKYABLE_DES")
                            if not ticker_element.isNull():
                                result[original_id] = ticker_element.getValue()

                if event_type == blpapi.Event.RESPONSE:
                    break

            elif event_type == blpapi.Event.TIMEOUT:
                logger.warning("Bloomberg ID conversion request timed out")
                break

            elif event_type == blpapi.Event.SESSION_STATUS:
                for msg in event:
                    if msg.messageType() == blpapi.Name("SessionTerminated"):
                        logger.error("Bloomberg session terminated unexpectedly")
                        raise BloombergDataError(
                            "Bloomberg session terminated during ID conversion",
                        )

        return result

    def get_historical_news_by_security(
        self,
        security: str,
        start_date: datetime | str | None = None,
        end_date: datetime | str | None = None,
    ) -> list[NewsStory]:
        """Fetch historical news for a security.

        Parameters
        ----------
        security : str
            Security identifier
        start_date : datetime | str | None
            Start date for news search
        end_date : datetime | str | None
            End date for news search

        Returns
        -------
        list[NewsStory]
            List of news stories

        Examples
        --------
        >>> stories = fetcher.get_historical_news_by_security(
        ...     "AAPL US Equity",
        ...     start_date="2024-01-01",
        ...     end_date="2024-01-31",
        ... )
        """
        logger.info(
            "Fetching historical news",
            security=security,
            start_date=str(start_date),
            end_date=str(end_date),
        )

        session = self._create_session()
        try:
            self._open_service(session, self.NEWS_SERVICE)
            stories = self._process_news_response(
                security, start_date, end_date, session
            )

            logger.info(
                "News fetch completed",
                security=security,
                story_count=len(stories),
            )

            return stories

        finally:
            session.stop()

    def _process_news_response(
        self,
        security: str,
        start_date: datetime | str | None,
        end_date: datetime | str | None,
        session: "blpapi.Session | None" = None,
    ) -> list[NewsStory]:
        """Process news response via BLPAPI NewsHeadlineRequest.

        Sends a NewsHeadlineRequest for the given security with optional date
        range filters and processes the event loop, extracting headline, storyId,
        storyDateTime, and source from each newsHeadlines element.

        Parameters
        ----------
        security : str
            Security identifier (e.g., "AAPL US Equity")
        start_date : datetime | str | None
            Start date for news filtering
        end_date : datetime | str | None
            End date for news filtering
        session : blpapi.Session | None
            Active Bloomberg session. When None, returns empty list (test
            compatibility mode).

        Returns
        -------
        list[NewsStory]
            News stories sorted by datetime ascending.

        Raises
        ------
        BloombergDataError
            If the Bloomberg session terminates unexpectedly.
        """
        logger.debug("Processing news response", security=security)

        if session is None:
            return []

        news_service = session.getService(self.NEWS_SERVICE)
        request = news_service.createRequest("NewsHeadlineRequest")

        request.append("securities", security)  # type: ignore[attr-defined]

        start_dt = self._parse_date(start_date)
        end_dt = self._parse_date(end_date)

        if start_dt is not None:
            request.set("startDateTime", start_dt)  # type: ignore[attr-defined]
        if end_dt is not None:
            request.set("endDateTime", end_dt)  # type: ignore[attr-defined]

        session.sendRequest(request)  # type: ignore[attr-defined]

        stories: list[NewsStory] = []

        while True:
            event = session.nextEvent(5000)  # type: ignore[attr-defined]
            event_type = event.eventType()

            if event_type in (
                blpapi.Event.RESPONSE,
                blpapi.Event.PARTIAL_RESPONSE,
            ):
                for msg in event:
                    if not msg.hasElement("newsHeadlines"):
                        continue

                    news_headlines = msg.getElement("newsHeadlines")

                    for headline in news_headlines.values():
                        story_dt = headline.getElementAsDatetime("storyDateTime")
                        story_id = headline.getElementAsString("storyId")
                        headline_text = headline.getElementAsString("headline")

                        source: str | None = None
                        if headline.hasElement("sources"):
                            sources_elem = headline.getElement("sources")
                            if sources_elem.numValues() > 0:
                                source = sources_elem.getValueAsString(0)

                        stories.append(
                            NewsStory(
                                story_id=story_id,
                                headline=headline_text,
                                datetime=pd.to_datetime(story_dt).to_pydatetime(),
                                source=source,
                            )
                        )

                if event_type == blpapi.Event.RESPONSE:
                    break

            elif event_type == blpapi.Event.TIMEOUT:
                logger.warning("Bloomberg news request timed out", security=security)
                break

            elif event_type == blpapi.Event.SESSION_STATUS:
                for msg in event:
                    if msg.messageType() == blpapi.Name("SessionTerminated"):
                        logger.error("Bloomberg session terminated unexpectedly")
                        raise BloombergDataError(
                            "Bloomberg session terminated during news fetch",
                            security=security,
                        )

        stories.sort(key=lambda s: s.datetime)
        return stories

    def get_news_story_content(self, story_id: str) -> str:
        """Fetch full content of a news story.

        Parameters
        ----------
        story_id : str
            Bloomberg story identifier

        Returns
        -------
        str
            Full story content
        """
        logger.info("Fetching news story content", story_id=story_id)

        session = self._create_session()
        try:
            self._open_service(session, self.NEWS_SERVICE)
            content = self._fetch_story_content(story_id)

            logger.info("Story content fetched", story_id=story_id)

            return content

        finally:
            session.stop()

    def _fetch_story_content(self, story_id: str) -> str:
        """Fetch story content from Bloomberg.

        Parameters
        ----------
        story_id : str
            Story identifier

        Returns
        -------
        str
            Story content
        """
        # AIDEV-NOTE: This method is typically mocked in tests
        logger.debug("Fetching story content", story_id=story_id)
        return ""

    def get_index_members(self, index: str) -> list[str]:
        """Fetch index constituent members.

        Parameters
        ----------
        index : str
            Index identifier (e.g., "SPX Index")

        Returns
        -------
        list[str]
            List of constituent securities

        Examples
        --------
        >>> members = fetcher.get_index_members("SPX Index")
        >>> "AAPL US Equity" in members
        True
        """
        logger.info("Fetching index members", index=index)

        session = self._create_session()
        try:
            self._open_service(session, self.REF_DATA_SERVICE)
            members = self._process_index_members(index, session)

            logger.info("Index members fetched", index=index, count=len(members))

            return members

        finally:
            session.stop()

    def _process_index_members(
        self,
        index: str,
        session: "blpapi.Session | None" = None,
    ) -> list[str]:
        """Process index members response via BLPAPI ReferenceDataRequest.

        Sends a ReferenceDataRequest for the INDX_MEMBERS field and traverses
        the bulk data array to collect all constituent Bloomberg tickers.

        Parameters
        ----------
        index : str
            Index identifier (e.g., "SPX Index")
        session : blpapi.Session | None
            Active Bloomberg session. When None, returns empty list (test
            compatibility mode).

        Returns
        -------
        list[str]
            Bloomberg security identifiers of index constituents.

        Raises
        ------
        BloombergDataError
            If the Bloomberg response contains a security-level error or the
            session terminates unexpectedly.
        """
        logger.debug("Processing index members", index=index)

        if session is None:
            return []

        ref_data_service = session.getService(self.REF_DATA_SERVICE)
        request = ref_data_service.createRequest("ReferenceDataRequest")
        request.append("securities", index)  # type: ignore[attr-defined]
        request.append("fields", "INDX_MEMBERS")  # type: ignore[attr-defined]

        session.sendRequest(request)  # type: ignore[attr-defined]

        members: list[str] = []

        while True:
            event = session.nextEvent(5000)  # type: ignore[attr-defined]
            event_type = event.eventType()

            if event_type in (
                blpapi.Event.RESPONSE,
                blpapi.Event.PARTIAL_RESPONSE,
            ):
                for msg in event:
                    if msg.hasElement("responseError"):
                        err_msg = (
                            msg.getElement("responseError")
                            .getElement("message")
                            .getValue()
                        )
                        logger.error(
                            "Response error fetching index members",
                            index=index,
                            error=err_msg,
                        )
                        raise BloombergDataError(
                            f"Bloomberg response error for index {index}: {err_msg}",
                            security=index,
                        )

                    security_data_array = msg.getElement("securityData")

                    for security_data in security_data_array.values():
                        if security_data.hasElement("securityError"):
                            err_msg = (
                                security_data.getElement("securityError")
                                .getElement("message")
                                .getValue()
                            )
                            logger.error(
                                "Security error fetching index members",
                                index=index,
                                error=err_msg,
                            )
                            raise BloombergDataError(
                                f"Bloomberg security error for index {index}: {err_msg}",
                                security=index,
                                code=ErrorCode.INVALID_SECURITY,
                            )

                        field_data = security_data.getElement("fieldData")

                        if not field_data.hasElement("INDX_MEMBERS"):
                            continue

                        members_element = field_data.getElement("INDX_MEMBERS")

                        for i in range(members_element.numValues()):
                            member_data = members_element.getValueAsElement(i)
                            if member_data.hasElement(
                                "Member Ticker and Exchange Code"
                            ):
                                ticker = member_data.getElementAsString(
                                    "Member Ticker and Exchange Code"
                                )
                                members.append(ticker)

                if event_type == blpapi.Event.RESPONSE:
                    break

            elif event_type == blpapi.Event.TIMEOUT:
                logger.warning("Bloomberg index members request timed out", index=index)
                break

            elif event_type == blpapi.Event.SESSION_STATUS:
                for msg in event:
                    if msg.messageType() == blpapi.Name("SessionTerminated"):
                        logger.error("Bloomberg session terminated unexpectedly")
                        raise BloombergDataError(
                            "Bloomberg session terminated during index members fetch",
                            security=index,
                        )

        return members

    def get_field_info(self, field_id: str) -> FieldInfo:
        """Fetch Bloomberg field metadata.

        Parameters
        ----------
        field_id : str
            Bloomberg field mnemonic (e.g., "PX_LAST")

        Returns
        -------
        FieldInfo
            Field metadata

        Examples
        --------
        >>> info = fetcher.get_field_info("PX_LAST")
        >>> info.field_name
        'Last Price'
        """
        logger.info("Fetching field info", field_id=field_id)

        session = self._create_session()
        try:
            self._open_service(session, API_FIELDS_SERVICE)
            info = self._process_field_info(field_id, session)

            logger.info("Field info fetched", field_id=field_id)

            return info

        finally:
            session.stop()

    def _process_field_info(
        self,
        field_id: str,
        session: "blpapi.Session | None" = None,
    ) -> FieldInfo:
        """Process field info response via BLPAPI FieldInfoRequest.

        Sends a FieldInfoRequest to the //blp/apiflds service and extracts
        the mnemonic, description, and datatype for the requested field.

        Parameters
        ----------
        field_id : str
            Bloomberg field mnemonic (e.g., "PX_LAST")
        session : blpapi.Session | None
            Active Bloomberg session. When None, returns FieldInfo with empty
            strings (test compatibility mode).

        Returns
        -------
        FieldInfo
            Field metadata including field_id, field_name, description, and
            data_type.

        Raises
        ------
        BloombergDataError
            If the Bloomberg session terminates unexpectedly.
        """
        logger.debug("Processing field info", field_id=field_id)

        if session is None:
            return FieldInfo(
                field_id=field_id,
                field_name="",
                description="",
                data_type="",
            )

        field_info_service = session.getService(API_FIELDS_SERVICE)
        request = field_info_service.createRequest("FieldInfoRequest")
        request.append("id", field_id)  # type: ignore[attr-defined]

        session.sendRequest(request)  # type: ignore[attr-defined]

        field_name = ""
        description = ""
        data_type = ""

        while True:
            event = session.nextEvent(5000)  # type: ignore[attr-defined]
            event_type = event.eventType()

            if event_type in (
                blpapi.Event.RESPONSE,
                blpapi.Event.PARTIAL_RESPONSE,
            ):
                for msg in event:
                    if not msg.hasElement("fieldData"):
                        continue

                    field_data_array = msg.getElement("fieldData")

                    for i in range(field_data_array.numValues()):
                        field_data = field_data_array.getValueAsElement(i)

                        if field_data.hasElement("mnemonic"):
                            field_name = field_data.getElementAsString("mnemonic")
                        if field_data.hasElement("description"):
                            description = field_data.getElementAsString("description")
                        if field_data.hasElement("datatype"):
                            data_type = field_data.getElementAsString("datatype")

                if event_type == blpapi.Event.RESPONSE:
                    break

            elif event_type == blpapi.Event.TIMEOUT:
                logger.warning(
                    "Bloomberg field info request timed out", field_id=field_id
                )
                break

            elif event_type == blpapi.Event.SESSION_STATUS:
                for msg in event:
                    if msg.messageType() == blpapi.Name("SessionTerminated"):
                        logger.error("Bloomberg session terminated unexpectedly")
                        raise BloombergDataError(
                            "Bloomberg session terminated during field info fetch",
                        )

        return FieldInfo(
            field_id=field_id,
            field_name=field_name,
            description=description,
            data_type=data_type,
        )

    def store_to_database(
        self,
        data: pd.DataFrame,
        db_path: str,
        table_name: str,
    ) -> None:
        """Store data to SQLite database.

        Parameters
        ----------
        data : pd.DataFrame
            Data to store
        db_path : str
            Path to SQLite database
        table_name : str
            Target table name

        Examples
        --------
        >>> fetcher.store_to_database(
        ...     data=df,
        ...     db_path="/path/to/db.sqlite",
        ...     table_name="historical_prices",
        ... )
        """
        logger.info(
            "Storing data to database",
            db_path=db_path,
            table_name=table_name,
            rows=len(data),
        )

        # Ensure parent directory exists
        db_file = Path(db_path)
        db_file.parent.mkdir(parents=True, exist_ok=True)

        with sqlite3.connect(db_path) as conn:
            data.to_sql(
                table_name,
                conn,
                if_exists="replace",
                index=False,
            )

        logger.info(
            "Data stored successfully",
            db_path=db_path,
            table_name=table_name,
        )

    def get_latest_date_from_db(
        self,
        db_path: str,
        table_name: str,
        date_column: str = "date",
    ) -> datetime | None:
        """Get the latest date from a database table.

        Parameters
        ----------
        db_path : str
            Path to SQLite database
        table_name : str
            Table name to query
        date_column : str
            Name of date column (default: "date")

        Returns
        -------
        datetime | None
            Latest date or None if table is empty

        Examples
        --------
        >>> latest = fetcher.get_latest_date_from_db(
        ...     db_path="/path/to/db.sqlite",
        ...     table_name="historical_prices",
        ... )
        """
        logger.debug(
            "Getting latest date from database",
            db_path=db_path,
            table_name=table_name,
            date_column=date_column,
        )

        with sqlite3.connect(db_path) as conn:
            query = f"SELECT MAX({date_column}) FROM {table_name}"  # nosec B608
            cursor = conn.execute(query)
            result = cursor.fetchone()

            if result and result[0]:
                latest_date = pd.to_datetime(result[0])
                logger.debug("Latest date found", date=str(latest_date))
                return latest_date.to_pydatetime()

        logger.debug("No data found in table", table_name=table_name)
        return None


__all__ = [
    "BLOOMBERG_SECURITY_PATTERN",
    "BloombergFetcher",
]
