"""Pytest fixtures for market.bloomberg tests.

This module provides common fixtures for Bloomberg module testing.
All fixtures use mocks to avoid actual Bloomberg API connections.

The mock Element factory section provides helpers that mimic the BLPAPI
Event/Message/Element hierarchy without requiring a Bloomberg Terminal.
"""

from datetime import datetime
from typing import Any
from unittest.mock import MagicMock, patch

import pandas as pd
import pytest


@pytest.fixture
def mock_blpapi():
    """Mock the blpapi module.

    This fixture patches the blpapi import to prevent actual Bloomberg
    API connections during testing.
    """
    with patch("market.bloomberg.fetcher.blpapi") as mock:
        # Setup default successful connection
        mock_session = MagicMock()
        mock_session.start.return_value = True
        mock_session.openService.return_value = True
        mock_session.stop.return_value = None
        mock.Session.return_value = mock_session

        yield mock


@pytest.fixture
def sample_historical_df() -> pd.DataFrame:
    """Create a sample historical data DataFrame.

    Returns
    -------
    pd.DataFrame
        DataFrame with date, PX_LAST, PX_VOLUME, PX_OPEN, PX_HIGH, PX_LOW columns
    """
    return pd.DataFrame(
        {
            "date": pd.to_datetime(
                ["2024-01-01", "2024-01-02", "2024-01-03", "2024-01-04", "2024-01-05"]
            ),
            "PX_LAST": [150.0, 151.0, 152.0, 151.5, 153.0],
            "PX_VOLUME": [1000000, 1100000, 1200000, 900000, 1300000],
            "PX_OPEN": [149.0, 150.0, 151.0, 152.0, 151.0],
            "PX_HIGH": [151.0, 152.0, 153.0, 152.5, 154.0],
            "PX_LOW": [148.0, 149.0, 150.0, 150.5, 150.0],
        }
    )


@pytest.fixture
def sample_reference_df() -> pd.DataFrame:
    """Create a sample reference data DataFrame.

    Returns
    -------
    pd.DataFrame
        DataFrame with security, NAME, GICS_SECTOR_NAME, CRNCY columns
    """
    return pd.DataFrame(
        {
            "security": ["AAPL US Equity", "MSFT US Equity", "GOOGL US Equity"],
            "NAME": ["Apple Inc", "Microsoft Corp", "Alphabet Inc"],
            "GICS_SECTOR_NAME": [
                "Information Technology",
                "Information Technology",
                "Communication Services",
            ],
            "CRNCY": ["USD", "USD", "USD"],
        }
    )


@pytest.fixture
def sample_financial_df() -> pd.DataFrame:
    """Create a sample financial data DataFrame.

    Returns
    -------
    pd.DataFrame
        DataFrame with security, IS_EPS, SALES_REV_TURN columns
    """
    return pd.DataFrame(
        {
            "security": ["AAPL US Equity"],
            "IS_EPS": [6.5],
            "SALES_REV_TURN": [394328000000],
            "NET_INCOME": [99803000000],
            "EBITDA": [130541000000],
        }
    )


@pytest.fixture
def sample_news_stories() -> list:
    """Create sample news stories.

    Note: This returns dicts because NewsStory may not be importable yet.
    In actual tests, convert these to NewsStory objects.

    Returns
    -------
    list
        List of news story dictionaries
    """
    return [
        {
            "story_id": "BBG123456789",
            "headline": "Apple Reports Q4 Earnings Beat",
            "datetime": datetime(2024, 1, 15, 9, 30),
            "body": "Apple Inc. reported quarterly earnings that exceeded analyst expectations...",
            "source": "Bloomberg News",
        },
        {
            "story_id": "BBG987654321",
            "headline": "Tech Stocks Rally on Strong Earnings",
            "datetime": datetime(2024, 1, 16, 14, 0),
            "body": "Technology stocks rose sharply following strong earnings reports...",
            "source": "Bloomberg News",
        },
    ]


@pytest.fixture
def sample_index_members() -> list[str]:
    """Create sample S&P 500 index members.

    Returns
    -------
    list[str]
        List of Bloomberg security identifiers
    """
    return [
        "AAPL US Equity",
        "MSFT US Equity",
        "GOOGL US Equity",
        "AMZN US Equity",
        "NVDA US Equity",
        "META US Equity",
        "TSLA US Equity",
        "BRK/B US Equity",
        "UNH US Equity",
        "JPM US Equity",
    ]


@pytest.fixture
def temp_db_path(tmp_path) -> str:
    """Create a temporary database path.

    Parameters
    ----------
    tmp_path : Path
        Pytest temporary path fixture

    Returns
    -------
    str
        Path to temporary SQLite database
    """
    return str(tmp_path / "bloomberg_test.db")


# =============================================================================
# Mock Element Factory Fixtures
#
# These fixtures simulate the BLPAPI Event → Message → Element hierarchy.
# Each factory function returns a MagicMock configured to behave like the
# corresponding BLPAPI type, allowing _process_* methods to be tested without
# a live Bloomberg Terminal.
# =============================================================================


def make_mock_element(value: object = None, name: str = "") -> MagicMock:
    """Create a mock BLPAPI Element.

    Parameters
    ----------
    value : object
        Value returned by getValue(), getElementAsString(), etc.
    name : str
        Element name (used for debugging)

    Returns
    -------
    MagicMock
        Configured mock element
    """
    elem = MagicMock()
    elem.getValue.return_value = value
    elem.getElementAsString.return_value = str(value) if value is not None else ""
    elem.getElementAsDatetime.return_value = value
    elem.isNull.return_value = False
    return elem


def make_mock_field_data(fields: dict) -> MagicMock:
    """Create a mock BLPAPI fieldData Element.

    Parameters
    ----------
    fields : dict
        Mapping of field name to value (value=None means field is absent)

    Returns
    -------
    MagicMock
        Mock fieldData element with hasElement and getElement configured
    """
    fd = MagicMock()
    present_fields = {k: v for k, v in fields.items() if v is not None}

    def _has_element(field_name: str) -> bool:
        return field_name in present_fields

    def _get_element(field_name: str) -> MagicMock:
        return make_mock_element(present_fields.get(field_name))

    fd.hasElement.side_effect = _has_element
    fd.getElement.side_effect = _get_element
    return fd


def make_mock_security_data(
    security: str,
    field_data: MagicMock,
    has_error: bool = False,
    error_message: str = "Unknown security",
) -> MagicMock:
    """Create a mock BLPAPI securityData Element.

    Parameters
    ----------
    security : str
        Bloomberg security identifier
    field_data : MagicMock
        Mock fieldData element (from make_mock_field_data)
    has_error : bool
        Whether securityError element is present
    error_message : str
        Error message text when has_error is True

    Returns
    -------
    MagicMock
        Mock securityData element
    """
    sd = MagicMock()
    sd.getElement.side_effect = lambda name: (
        make_mock_element(security) if name == "security" else field_data
    )

    if has_error:
        err_elem = MagicMock()
        err_msg_elem = make_mock_element(error_message)
        err_elem.getElement.return_value = err_msg_elem
        sd.hasElement.side_effect = (
            lambda name: name in ("securityError", "fieldData")
            if has_error
            else lambda name: name == "fieldData"
        )
        sd.getElement.side_effect = lambda name: (
            err_elem if name == "securityError" else make_mock_element(security)
        )
    else:
        sd.hasElement.side_effect = lambda name: name == "fieldData"

    sd.getElement.side_effect = lambda name: (
        make_mock_element(security)
        if name == "security"
        else (
            _make_error_element(error_message)
            if name == "securityError"
            else field_data
        )
    )
    sd.hasElement.side_effect = lambda name: (
        name == "securityError" if has_error else name == "fieldData"
    )
    return sd


def _make_error_element(message: str) -> MagicMock:
    """Create a mock BLPAPI error Element with a message sub-element."""
    err = MagicMock()
    err.getElement.return_value = make_mock_element(message)
    return err


def make_mock_historical_field_data_array(
    dates: list[str],
    fields: list[str],
    values: list[list[Any]],
) -> MagicMock:
    """Create a mock BLPAPI fieldData array for historical data.

    Parameters
    ----------
    dates : list[str]
        Date strings (e.g., ["2024-01-01", "2024-01-02"])
    fields : list[str]
        Field names (e.g., ["PX_LAST", "PX_VOLUME"])
    values : list[list[Any]]
        Values per row, outer list = dates, inner list = fields

    Returns
    -------
    MagicMock
        Mock fieldData array iterable
    """
    row_mocks = []
    for i, date_str in enumerate(dates):
        row_fields: dict[str, Any] = {"date": pd.to_datetime(date_str)}
        for j, field in enumerate(fields):
            row_fields[field] = values[i][j] if i < len(values) else None

        row_fd = make_mock_field_data(row_fields)
        row_fd.getElement.side_effect = lambda name, _date=date_str, _rf=row_fields: (
            make_mock_element(pd.to_datetime(_date))
            if name == "date"
            else make_mock_element(_rf.get(name))
        )
        row_mocks.append(row_fd)

    fda = MagicMock()
    fda.values.return_value = iter(row_mocks)
    return fda


def make_mock_historical_security_data(
    security: str,
    field_data_array: MagicMock,
    has_error: bool = False,
    error_message: str = "Unknown security",
) -> MagicMock:
    """Create a mock BLPAPI securityData Element for historical responses.

    Parameters
    ----------
    security : str
        Bloomberg security identifier
    field_data_array : MagicMock
        Mock fieldData array (from make_mock_historical_field_data_array)
    has_error : bool
        Whether securityError element is present
    error_message : str
        Error message text when has_error is True

    Returns
    -------
    MagicMock
        Mock securityData element suitable for historical data processing
    """
    sd = MagicMock()
    sd.getElement.side_effect = lambda name: (
        make_mock_element(security)
        if name == "security"
        else (
            _make_error_element(error_message)
            if name == "securityError"
            else field_data_array
        )
    )
    sd.hasElement.side_effect = lambda name: (
        name == "securityError" if has_error else name == "fieldData"
    )
    return sd


def make_mock_message(
    has_security_data: bool = True,
    security_data: MagicMock | None = None,
    has_response_error: bool = False,
    error_message: str = "Request failed",
    security_data_is_array: bool = False,
) -> MagicMock:
    """Create a mock BLPAPI Message.

    Parameters
    ----------
    has_security_data : bool
        Whether the message contains a securityData element
    security_data : MagicMock | None
        Mock securityData (single) or None
    has_response_error : bool
        Whether the message contains a responseError element
    error_message : str
        Error message text when has_response_error is True
    security_data_is_array : bool
        If True, getElement("securityData") returns an array that supports
        .values() iteration (used for reference/id-conversion responses)

    Returns
    -------
    MagicMock
        Mock message
    """
    msg = MagicMock()

    def _has_element(name: str) -> bool:
        if name == "responseError":
            return has_response_error
        if name == "securityData":
            return has_security_data
        if name == "newsHeadlines":
            return False
        if name == "fieldData":
            return False
        return False

    msg.hasElement.side_effect = _has_element

    def _get_element(name: str) -> MagicMock:
        if name == "responseError":
            return _make_error_element(error_message)
        if name == "securityData":
            if security_data_is_array:
                arr = MagicMock()
                arr.values.return_value = (
                    iter([security_data]) if security_data is not None else iter([])
                )
                return arr
            return security_data or MagicMock()
        return MagicMock()

    msg.getElement.side_effect = _get_element
    return msg


def make_mock_event(
    event_type: int,
    messages: list[MagicMock],
) -> MagicMock:
    """Create a mock BLPAPI Event.

    Parameters
    ----------
    event_type : int
        BLPAPI event type constant (e.g., blpapi.Event.RESPONSE)
    messages : list[MagicMock]
        List of mock messages contained in this event

    Returns
    -------
    MagicMock
        Mock event that iterates over messages
    """
    event = MagicMock()
    event.eventType.return_value = event_type
    event.__iter__ = MagicMock(return_value=iter(messages))
    return event


@pytest.fixture
def mock_blpapi_session_factory():
    """Fixture that returns a factory for creating mock BLPAPI sessions.

    The returned factory accepts a list of events and returns a mock session
    whose nextEvent() call yields each event in sequence.

    Returns
    -------
    callable
        Factory function: (events: list[MagicMock]) -> MagicMock session
    """

    def _factory(events: list[MagicMock]) -> MagicMock:
        session = MagicMock()
        session.start.return_value = True
        session.openService.return_value = True
        session.stop.return_value = None

        # Service mocks
        ref_service = MagicMock()
        news_service = MagicMock()
        apiflds_service = MagicMock()

        request_mock = MagicMock()
        ref_service.createRequest.return_value = request_mock
        news_service.createRequest.return_value = request_mock
        apiflds_service.createRequest.return_value = request_mock

        def _get_service(name: str) -> MagicMock:
            if "news" in name:
                return news_service
            if "apiflds" in name:
                return apiflds_service
            return ref_service

        session.getService.side_effect = _get_service

        event_iter = iter(events)

        def _next_event(timeout: int = 5000) -> MagicMock:
            try:
                return next(event_iter)
            except StopIteration:
                # Return a TIMEOUT event if events are exhausted
                timeout_event = MagicMock()
                timeout_event.eventType.return_value = 6  # blpapi.Event.TIMEOUT
                return timeout_event

        session.nextEvent.side_effect = _next_event
        return session

    return _factory


@pytest.fixture
def mock_historical_session(mock_blpapi_session_factory):
    """Pre-built mock session for a successful historical data response.

    Provides data for "AAPL US Equity" with PX_LAST and PX_VOLUME over 3 dates.

    Returns
    -------
    MagicMock
        Configured mock BLPAPI session
    """
    import blpapi  # type: ignore[import-not-found]

    dates = ["2024-01-01", "2024-01-02", "2024-01-03"]
    fields = ["PX_LAST", "PX_VOLUME"]
    values = [[150.0, 1000000], [151.0, 1100000], [152.0, 1200000]]

    fda = make_mock_historical_field_data_array(dates, fields, values)
    sd = make_mock_historical_security_data("AAPL US Equity", fda)
    msg = make_mock_message(has_security_data=True, security_data=sd)
    event = make_mock_event(blpapi.Event.RESPONSE, [msg])

    return mock_blpapi_session_factory([event])


@pytest.fixture
def mock_reference_session(mock_blpapi_session_factory):
    """Pre-built mock session for a successful reference data response.

    Provides NAME and GICS_SECTOR_NAME data for "AAPL US Equity".

    Returns
    -------
    MagicMock
        Configured mock BLPAPI session
    """
    import blpapi  # type: ignore[import-not-found]

    fields_data = {
        "security": "AAPL US Equity",
        "NAME": "Apple Inc",
        "GICS_SECTOR_NAME": "Information Technology",
    }
    fd = make_mock_field_data(fields_data)
    sd = make_mock_security_data("AAPL US Equity", fd)
    sd_array = MagicMock()
    sd_array.values.return_value = iter([sd])

    msg = MagicMock()
    msg.hasElement.side_effect = lambda name: name == "securityData"
    msg.getElement.return_value = sd_array

    event = make_mock_event(blpapi.Event.RESPONSE, [msg])
    return mock_blpapi_session_factory([event])
