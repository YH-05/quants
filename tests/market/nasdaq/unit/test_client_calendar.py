"""Unit tests for NasdaqClient calendar endpoint methods.

Tests cover:
- get_earnings_calendar: normal, cache hit/miss, date parameter
- get_dividends_calendar: normal, cache hit/miss, date parameter
- get_splits_calendar: normal, cache hit/miss, date parameter
- get_ipo_calendar: normal, cache hit/miss, year_month parameter

See Also
--------
market.nasdaq.client : NasdaqClient implementation.
tests.market.nasdaq.unit.test_client_base : Reference test patterns.
tests.market.nasdaq.conftest : Shared fixtures.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any
from unittest.mock import MagicMock

import pytest

from market.nasdaq.client_types import (
    DividendCalendarRecord,
    EarningsRecord,
    IpoRecord,
    NasdaqFetchOptions,
    SplitRecord,
)

if TYPE_CHECKING:
    from market.nasdaq.client import NasdaqClient

# =============================================================================
# Earnings Calendar Tests
# =============================================================================


class TestGetEarningsCalendar:
    """Tests for NasdaqClient.get_earnings_calendar."""

    def test_正常系_earnings_calendarを取得できる(
        self,
        nasdaq_client: NasdaqClient,
        mock_cache: MagicMock,
        mock_nasdaq_session: MagicMock,
    ) -> None:
        """Fetches earnings calendar from API and returns EarningsRecord list."""
        mock_cache.get.return_value = None

        raw_response: dict[str, Any] = {
            "data": {
                "rows": [
                    {
                        "symbol": "AAPL",
                        "name": "Apple Inc.",
                        "date": "01/30/2026",
                        "epsEstimate": "$2.35",
                        "epsActual": "$2.40",
                        "surprise": "2.13%",
                        "fiscalQuarterEnding": "Dec/2025",
                        "marketCap": "3,435,123,456,789",
                    },
                ],
            },
            "message": None,
            "status": {"rCode": 200, "bCodeMessage": None},
        }
        mock_response = MagicMock()
        mock_response.json.return_value = raw_response
        mock_nasdaq_session.get_with_retry.return_value = mock_response

        result = nasdaq_client.get_earnings_calendar(date="2026-01-30")

        assert len(result) == 1
        assert isinstance(result[0], EarningsRecord)
        assert result[0].symbol == "AAPL"

    def test_正常系_キャッシュヒット時にAPIを呼ばない(
        self,
        nasdaq_client: NasdaqClient,
        mock_cache: MagicMock,
        mock_nasdaq_session: MagicMock,
    ) -> None:
        """When cache has data, API is not called."""
        cached_data = [
            EarningsRecord(
                symbol="AAPL",
                name="Apple Inc.",
                date="01/30/2026",
                eps_estimate="$2.35",
                eps_actual="$2.40",
                surprise="2.13%",
                fiscal_quarter_ending="Dec/2025",
                market_cap="3,435,123,456,789",
            ),
        ]
        mock_cache.get.return_value = cached_data

        result = nasdaq_client.get_earnings_calendar(date="2026-01-30")

        assert result == cached_data
        mock_nasdaq_session.get_with_retry.assert_not_called()

    def test_正常系_dateパラメータがAPIリクエストに渡される(
        self,
        nasdaq_client: NasdaqClient,
        mock_cache: MagicMock,
        mock_nasdaq_session: MagicMock,
    ) -> None:
        """Date parameter is forwarded to the API request."""
        mock_cache.get.return_value = None

        raw_response: dict[str, Any] = {
            "data": {"rows": []},
            "message": None,
            "status": {"rCode": 200, "bCodeMessage": None},
        }
        mock_response = MagicMock()
        mock_response.json.return_value = raw_response
        mock_nasdaq_session.get_with_retry.return_value = mock_response

        nasdaq_client.get_earnings_calendar(date="2026-03-24")

        mock_nasdaq_session.get_with_retry.assert_called_once()
        call_kwargs = mock_nasdaq_session.get_with_retry.call_args
        assert call_kwargs[1]["params"]["date"] == "2026-03-24"

    def test_正常系_force_refreshでキャッシュを無視(
        self,
        nasdaq_client: NasdaqClient,
        mock_cache: MagicMock,
        mock_nasdaq_session: MagicMock,
    ) -> None:
        """Force refresh bypasses cache."""
        mock_cache.get.return_value = "old_data"

        raw_response: dict[str, Any] = {
            "data": {"rows": []},
            "message": None,
            "status": {"rCode": 200, "bCodeMessage": None},
        }
        mock_response = MagicMock()
        mock_response.json.return_value = raw_response
        mock_nasdaq_session.get_with_retry.return_value = mock_response

        options = NasdaqFetchOptions(force_refresh=True)
        nasdaq_client.get_earnings_calendar(date="2026-01-30", options=options)

        mock_cache.get.assert_not_called()
        mock_nasdaq_session.get_with_retry.assert_called_once()


# =============================================================================
# Dividends Calendar Tests
# =============================================================================


class TestGetDividendsCalendar:
    """Tests for NasdaqClient.get_dividends_calendar."""

    def test_正常系_dividends_calendarを取得できる(
        self,
        nasdaq_client: NasdaqClient,
        mock_cache: MagicMock,
        mock_nasdaq_session: MagicMock,
    ) -> None:
        """Fetches dividends calendar from API and returns DividendCalendarRecord list."""
        mock_cache.get.return_value = None

        raw_response: dict[str, Any] = {
            "data": {
                "calendar": {
                    "rows": [
                        {
                            "symbol": "AAPL",
                            "companyName": "Apple Inc.",
                            "dividend_Ex_Date": "02/07/2026",
                            "payment_Date": "02/13/2026",
                            "record_Date": "02/10/2026",
                            "dividend_Rate": "$0.25",
                            "indicated_Annual_Dividend": "$1.00",
                        },
                    ],
                },
            },
            "message": None,
            "status": {"rCode": 200, "bCodeMessage": None},
        }
        mock_response = MagicMock()
        mock_response.json.return_value = raw_response
        mock_nasdaq_session.get_with_retry.return_value = mock_response

        result = nasdaq_client.get_dividends_calendar(date="2026-02-07")

        assert len(result) == 1
        assert isinstance(result[0], DividendCalendarRecord)
        assert result[0].symbol == "AAPL"
        assert result[0].company_name == "Apple Inc."

    def test_正常系_キャッシュヒット時にAPIを呼ばない(
        self,
        nasdaq_client: NasdaqClient,
        mock_cache: MagicMock,
        mock_nasdaq_session: MagicMock,
    ) -> None:
        """When cache has data, API is not called."""
        cached_data = [
            DividendCalendarRecord(
                symbol="AAPL",
                company_name="Apple Inc.",
                ex_date="02/07/2026",
                payment_date="02/13/2026",
                record_date="02/10/2026",
                dividend_rate="$0.25",
                annual_dividend="$1.00",
            ),
        ]
        mock_cache.get.return_value = cached_data

        result = nasdaq_client.get_dividends_calendar(date="2026-02-07")

        assert result == cached_data
        mock_nasdaq_session.get_with_retry.assert_not_called()

    def test_正常系_dateパラメータがAPIリクエストに渡される(
        self,
        nasdaq_client: NasdaqClient,
        mock_cache: MagicMock,
        mock_nasdaq_session: MagicMock,
    ) -> None:
        """Date parameter is forwarded to the API request."""
        mock_cache.get.return_value = None

        raw_response: dict[str, Any] = {
            "data": {"calendar": {"rows": []}},
            "message": None,
            "status": {"rCode": 200, "bCodeMessage": None},
        }
        mock_response = MagicMock()
        mock_response.json.return_value = raw_response
        mock_nasdaq_session.get_with_retry.return_value = mock_response

        nasdaq_client.get_dividends_calendar(date="2026-03-24")

        call_kwargs = mock_nasdaq_session.get_with_retry.call_args
        assert call_kwargs[1]["params"]["date"] == "2026-03-24"


# =============================================================================
# Splits Calendar Tests
# =============================================================================


class TestGetSplitsCalendar:
    """Tests for NasdaqClient.get_splits_calendar."""

    def test_正常系_splits_calendarを取得できる(
        self,
        nasdaq_client: NasdaqClient,
        mock_cache: MagicMock,
        mock_nasdaq_session: MagicMock,
    ) -> None:
        """Fetches splits calendar from API and returns SplitRecord list."""
        mock_cache.get.return_value = None

        raw_response: dict[str, Any] = {
            "data": {
                "rows": [
                    {
                        "symbol": "NVDA",
                        "name": "NVIDIA Corporation",
                        "executionDate": "06/10/2024",
                        "ratio": "10:1",
                        "optionable": "Y",
                    },
                ],
            },
            "message": None,
            "status": {"rCode": 200, "bCodeMessage": None},
        }
        mock_response = MagicMock()
        mock_response.json.return_value = raw_response
        mock_nasdaq_session.get_with_retry.return_value = mock_response

        result = nasdaq_client.get_splits_calendar(date="2024-06-10")

        assert len(result) == 1
        assert isinstance(result[0], SplitRecord)
        assert result[0].symbol == "NVDA"
        assert result[0].ratio == "10:1"

    def test_正常系_キャッシュヒット時にAPIを呼ばない(
        self,
        nasdaq_client: NasdaqClient,
        mock_cache: MagicMock,
        mock_nasdaq_session: MagicMock,
    ) -> None:
        """When cache has data, API is not called."""
        cached_data = [
            SplitRecord(
                symbol="NVDA",
                name="NVIDIA Corporation",
                execution_date="06/10/2024",
                ratio="10:1",
                optionable="Y",
            ),
        ]
        mock_cache.get.return_value = cached_data

        result = nasdaq_client.get_splits_calendar(date="2024-06-10")

        assert result == cached_data
        mock_nasdaq_session.get_with_retry.assert_not_called()

    def test_正常系_dateパラメータがAPIリクエストに渡される(
        self,
        nasdaq_client: NasdaqClient,
        mock_cache: MagicMock,
        mock_nasdaq_session: MagicMock,
    ) -> None:
        """Date parameter is forwarded to the API request."""
        mock_cache.get.return_value = None

        raw_response: dict[str, Any] = {
            "data": {"rows": []},
            "message": None,
            "status": {"rCode": 200, "bCodeMessage": None},
        }
        mock_response = MagicMock()
        mock_response.json.return_value = raw_response
        mock_nasdaq_session.get_with_retry.return_value = mock_response

        nasdaq_client.get_splits_calendar(date="2026-03-24")

        call_kwargs = mock_nasdaq_session.get_with_retry.call_args
        assert call_kwargs[1]["params"]["date"] == "2026-03-24"


# =============================================================================
# IPO Calendar Tests
# =============================================================================


class TestGetIpoCalendar:
    """Tests for NasdaqClient.get_ipo_calendar."""

    def test_正常系_ipo_calendarを取得できる(
        self,
        nasdaq_client: NasdaqClient,
        mock_cache: MagicMock,
        mock_nasdaq_session: MagicMock,
    ) -> None:
        """Fetches IPO calendar from API and returns IpoRecord list."""
        mock_cache.get.return_value = None

        raw_response: dict[str, Any] = {
            "data": {
                "priced": {
                    "rows": [
                        {
                            "dealID": "123456",
                            "proposedTickerSymbol": "NEWCO",
                            "companyName": "NewCo Inc.",
                            "proposedExchange": "NASDAQ",
                            "proposedSharePrice": "$15.00-$17.00",
                            "sharesOffered": "10,000,000",
                        },
                    ],
                },
            },
            "message": None,
            "status": {"rCode": 200, "bCodeMessage": None},
        }
        mock_response = MagicMock()
        mock_response.json.return_value = raw_response
        mock_nasdaq_session.get_with_retry.return_value = mock_response

        result = nasdaq_client.get_ipo_calendar(year_month="2026-03")

        assert len(result) == 1
        assert isinstance(result[0], IpoRecord)
        assert result[0].symbol == "NEWCO"
        assert result[0].company_name == "NewCo Inc."

    def test_正常系_キャッシュヒット時にAPIを呼ばない(
        self,
        nasdaq_client: NasdaqClient,
        mock_cache: MagicMock,
        mock_nasdaq_session: MagicMock,
    ) -> None:
        """When cache has data, API is not called."""
        cached_data = [
            IpoRecord(
                deal_id="123456",
                symbol="NEWCO",
                company_name="NewCo Inc.",
                exchange="NASDAQ",
                share_price="$15.00",
                shares_offered="10,000,000",
            ),
        ]
        mock_cache.get.return_value = cached_data

        result = nasdaq_client.get_ipo_calendar(year_month="2026-03")

        assert result == cached_data
        mock_nasdaq_session.get_with_retry.assert_not_called()

    def test_正常系_year_monthパラメータがAPIリクエストに渡される(
        self,
        nasdaq_client: NasdaqClient,
        mock_cache: MagicMock,
        mock_nasdaq_session: MagicMock,
    ) -> None:
        """year_month parameter is forwarded to the API request as 'date'."""
        mock_cache.get.return_value = None

        raw_response: dict[str, Any] = {
            "data": {"priced": {"rows": []}},
            "message": None,
            "status": {"rCode": 200, "bCodeMessage": None},
        }
        mock_response = MagicMock()
        mock_response.json.return_value = raw_response
        mock_nasdaq_session.get_with_retry.return_value = mock_response

        nasdaq_client.get_ipo_calendar(year_month="2026-03")

        call_kwargs = mock_nasdaq_session.get_with_retry.call_args
        assert call_kwargs[1]["params"]["date"] == "2026-03"

    def test_正常系_force_refreshでキャッシュを無視(
        self,
        nasdaq_client: NasdaqClient,
        mock_cache: MagicMock,
        mock_nasdaq_session: MagicMock,
    ) -> None:
        """Force refresh bypasses cache."""
        mock_cache.get.return_value = "old_data"

        raw_response: dict[str, Any] = {
            "data": {"priced": {"rows": []}},
            "message": None,
            "status": {"rCode": 200, "bCodeMessage": None},
        }
        mock_response = MagicMock()
        mock_response.json.return_value = raw_response
        mock_nasdaq_session.get_with_retry.return_value = mock_response

        options = NasdaqFetchOptions(force_refresh=True)
        nasdaq_client.get_ipo_calendar(year_month="2026-03", options=options)

        mock_cache.get.assert_not_called()
        mock_nasdaq_session.get_with_retry.assert_called_once()
