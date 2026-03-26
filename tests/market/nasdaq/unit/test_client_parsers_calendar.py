"""Unit tests for calendar endpoint parsers in client_parsers.py.

Tests cover:
- parse_earnings_calendar: normal, empty, malformed data
- parse_dividends_calendar: normal, empty, malformed data
- parse_splits_calendar: normal, empty, malformed data
- parse_ipo_calendar: normal, empty, malformed data

See Also
--------
market.nasdaq.client_parsers : Parser implementations.
market.nasdaq.client_types : Record dataclass definitions.
tests.market.nasdaq.unit.test_parser : Reference test patterns.
"""

from __future__ import annotations

from typing import Any

import pytest

from market.nasdaq.client_parsers import (
    parse_dividends_calendar,
    parse_earnings_calendar,
    parse_ipo_calendar,
    parse_splits_calendar,
)
from market.nasdaq.client_types import (
    DividendCalendarRecord,
    EarningsRecord,
    IpoRecord,
    SplitRecord,
)
from market.nasdaq.errors import NasdaqParseError

# =============================================================================
# Earnings Calendar Parser Tests
# =============================================================================


class TestParseEarningsCalendar:
    """Tests for parse_earnings_calendar parser."""

    def test_正常系_過去日のデータでEarningsRecordリストを返す(self) -> None:
        """Parses valid past-date earnings data with actual EPS."""
        data: dict[str, Any] = {
            "rows": [
                {
                    "symbol": "AAPL",
                    "name": "Apple Inc.",
                    "eps": "$2.40",
                    "surprise": "1.69",
                    "time": "time-not-supplied",
                    "fiscalQuarterEnding": "Dec/2024",
                    "epsForecast": "$2.36",
                    "noOfEsts": "11",
                    "marketCap": "$3,640,775,908,600",
                },
                {
                    "symbol": "MSFT",
                    "name": "Microsoft Corporation",
                    "eps": "$3.23",
                    "surprise": "4.19",
                    "time": "time-after-hours",
                    "fiscalQuarterEnding": "Dec/2024",
                    "epsForecast": "$3.10",
                    "noOfEsts": "28",
                    "marketCap": "$3,100,000,000,000",
                },
            ],
        }

        result = parse_earnings_calendar(data)

        assert len(result) == 2
        assert isinstance(result[0], EarningsRecord)
        assert result[0].symbol == "AAPL"
        assert result[0].name == "Apple Inc."
        assert result[0].eps_estimate == "$2.36"
        assert result[0].eps_actual == "$2.40"
        assert result[0].surprise == "1.69"
        assert result[0].fiscal_quarter_ending == "Dec/2024"
        assert result[0].market_cap == "$3,640,775,908,600"
        assert result[0].time == "time-not-supplied"
        assert result[0].no_of_ests == "11"

    def test_正常系_未来日のデータでEarningsRecordリストを返す(self) -> None:
        """Parses valid future-date earnings data without actual EPS."""
        data: dict[str, Any] = {
            "rows": [
                {
                    "symbol": "GME",
                    "name": "GameStop Corporation",
                    "lastYearRptDt": "N/A",
                    "lastYearEPS": "$0.30",
                    "time": "time-after-hours",
                    "fiscalQuarterEnding": "Jan/2026",
                    "epsForecast": "",
                    "noOfEsts": "1",
                    "marketCap": "$10,111,573,964",
                },
            ],
        }

        result = parse_earnings_calendar(data)

        assert len(result) == 1
        assert result[0].symbol == "GME"
        assert result[0].name == "GameStop Corporation"
        assert result[0].eps_estimate == ""
        assert result[0].eps_actual is None
        assert result[0].surprise is None
        assert result[0].fiscal_quarter_ending == "Jan/2026"
        assert result[0].market_cap == "$10,111,573,964"
        assert result[0].time == "time-after-hours"
        assert result[0].no_of_ests == "1"
        assert result[0].last_year_rpt_dt == "N/A"
        assert result[0].last_year_eps == "$0.30"

    def test_正常系_空データで空リストを返す(self) -> None:
        """Returns empty list when rows is empty."""
        data: dict[str, Any] = {"rows": []}
        result = parse_earnings_calendar(data)
        assert result == []

    def test_正常系_rows欠落で空リストを返す(self) -> None:
        """Returns empty list when rows key is missing."""
        data: dict[str, Any] = {}
        result = parse_earnings_calendar(data)
        assert result == []

    def test_異常系_rowsがlist以外でNasdaqParseError(self) -> None:
        """Raises NasdaqParseError when rows is not a list."""
        data: dict[str, Any] = {"rows": "not a list"}
        with pytest.raises(NasdaqParseError):
            parse_earnings_calendar(data)

    def test_正常系_frozen_dataclass(self) -> None:
        """EarningsRecord is immutable (frozen)."""
        data: dict[str, Any] = {
            "rows": [
                {
                    "symbol": "AAPL",
                    "name": "Apple Inc.",
                    "eps": "$2.40",
                    "surprise": "1.69",
                    "time": "time-not-supplied",
                    "fiscalQuarterEnding": "Dec/2024",
                    "epsForecast": "$2.36",
                    "noOfEsts": "11",
                    "marketCap": "$3,640,775,908,600",
                },
            ],
        }
        result = parse_earnings_calendar(data)
        with pytest.raises(AttributeError):
            result[0].symbol = "MSFT"

    def test_正常系_欠落フィールドでNoneが設定される(self) -> None:
        """Missing fields default to None."""
        data: dict[str, Any] = {
            "rows": [
                {
                    "symbol": "AAPL",
                    "name": "Apple Inc.",
                },
            ],
        }
        result = parse_earnings_calendar(data)
        assert len(result) == 1
        assert result[0].symbol == "AAPL"
        assert result[0].date is None
        assert result[0].eps_estimate is None
        assert result[0].eps_actual is None
        assert result[0].surprise is None
        assert result[0].time is None
        assert result[0].no_of_ests is None
        assert result[0].last_year_rpt_dt is None
        assert result[0].last_year_eps is None


# =============================================================================
# Dividends Calendar Parser Tests
# =============================================================================


class TestParseDividendsCalendar:
    """Tests for parse_dividends_calendar parser."""

    def test_正常系_有効なデータでDividendCalendarRecordリストを返す(self) -> None:
        """Parses valid dividends calendar data into DividendCalendarRecord list."""
        data: dict[str, Any] = {
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
                    {
                        "symbol": "MSFT",
                        "companyName": "Microsoft Corporation",
                        "dividend_Ex_Date": "02/19/2026",
                        "payment_Date": "03/12/2026",
                        "record_Date": "02/19/2026",
                        "dividend_Rate": "$0.83",
                        "indicated_Annual_Dividend": "$3.32",
                    },
                ],
            },
        }

        result = parse_dividends_calendar(data)

        assert len(result) == 2
        assert isinstance(result[0], DividendCalendarRecord)
        assert result[0].symbol == "AAPL"
        assert result[0].company_name == "Apple Inc."
        assert result[0].ex_date == "02/07/2026"
        assert result[0].payment_date == "02/13/2026"
        assert result[0].record_date == "02/10/2026"
        assert result[0].dividend_rate == "$0.25"
        assert result[0].annual_dividend == "$1.00"

    def test_正常系_空データで空リストを返す(self) -> None:
        """Returns empty list when calendar.rows is empty."""
        data: dict[str, Any] = {"calendar": {"rows": []}}
        result = parse_dividends_calendar(data)
        assert result == []

    def test_正常系_calendar欠落で空リストを返す(self) -> None:
        """Returns empty list when calendar key is missing."""
        data: dict[str, Any] = {}
        result = parse_dividends_calendar(data)
        assert result == []

    def test_正常系_rows欠落で空リストを返す(self) -> None:
        """Returns empty list when rows key is missing under calendar."""
        data: dict[str, Any] = {"calendar": {}}
        result = parse_dividends_calendar(data)
        assert result == []

    def test_異常系_rowsがlist以外でNasdaqParseError(self) -> None:
        """Raises NasdaqParseError when calendar.rows is not a list."""
        data: dict[str, Any] = {"calendar": {"rows": "not a list"}}
        with pytest.raises(NasdaqParseError):
            parse_dividends_calendar(data)

    def test_正常系_frozen_dataclass(self) -> None:
        """DividendCalendarRecord is immutable (frozen)."""
        data: dict[str, Any] = {
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
        }
        result = parse_dividends_calendar(data)
        with pytest.raises(AttributeError):
            result[0].symbol = "MSFT"


# =============================================================================
# Splits Calendar Parser Tests
# =============================================================================


class TestParseSplitsCalendar:
    """Tests for parse_splits_calendar parser."""

    def test_正常系_有効なデータでSplitRecordリストを返す(self) -> None:
        """Parses valid splits calendar data into SplitRecord list."""
        data: dict[str, Any] = {
            "rows": [
                {
                    "symbol": "NVDA",
                    "name": "NVIDIA Corporation",
                    "executionDate": "06/10/2024",
                    "ratio": "10:1",
                    "optionable": "Y",
                },
                {
                    "symbol": "AMZN",
                    "name": "Amazon.com, Inc.",
                    "executionDate": "06/06/2022",
                    "ratio": "20:1",
                    "optionable": "Y",
                },
            ],
        }

        result = parse_splits_calendar(data)

        assert len(result) == 2
        assert isinstance(result[0], SplitRecord)
        assert result[0].symbol == "NVDA"
        assert result[0].name == "NVIDIA Corporation"
        assert result[0].execution_date == "06/10/2024"
        assert result[0].ratio == "10:1"
        assert result[0].optionable == "Y"

    def test_正常系_空データで空リストを返す(self) -> None:
        """Returns empty list when rows is empty."""
        data: dict[str, Any] = {"rows": []}
        result = parse_splits_calendar(data)
        assert result == []

    def test_正常系_rows欠落で空リストを返す(self) -> None:
        """Returns empty list when rows key is missing."""
        data: dict[str, Any] = {}
        result = parse_splits_calendar(data)
        assert result == []

    def test_異常系_rowsがlist以外でNasdaqParseError(self) -> None:
        """Raises NasdaqParseError when rows is not a list."""
        data: dict[str, Any] = {"rows": {"not": "a list"}}
        with pytest.raises(NasdaqParseError):
            parse_splits_calendar(data)

    def test_正常系_frozen_dataclass(self) -> None:
        """SplitRecord is immutable (frozen)."""
        data: dict[str, Any] = {
            "rows": [
                {
                    "symbol": "NVDA",
                    "name": "NVIDIA Corporation",
                    "executionDate": "06/10/2024",
                    "ratio": "10:1",
                    "optionable": "Y",
                },
            ],
        }
        result = parse_splits_calendar(data)
        with pytest.raises(AttributeError):
            result[0].symbol = "AAPL"


# =============================================================================
# IPO Calendar Parser Tests
# =============================================================================


class TestParseIpoCalendar:
    """Tests for parse_ipo_calendar parser."""

    def test_正常系_有効なデータでIpoRecordリストを返す(self) -> None:
        """Parses valid IPO calendar data into IpoRecord list."""
        data: dict[str, Any] = {
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
                    {
                        "dealID": "789012",
                        "proposedTickerSymbol": "TECH",
                        "companyName": "Tech Corp.",
                        "proposedExchange": "NYSE",
                        "proposedSharePrice": "$20.00",
                        "sharesOffered": "5,000,000",
                    },
                ],
            },
        }

        result = parse_ipo_calendar(data)

        assert len(result) == 2
        assert isinstance(result[0], IpoRecord)
        assert result[0].deal_id == "123456"
        assert result[0].symbol == "NEWCO"
        assert result[0].company_name == "NewCo Inc."
        assert result[0].exchange == "NASDAQ"
        assert result[0].share_price == "$15.00-$17.00"
        assert result[0].shares_offered == "10,000,000"

    def test_正常系_空データで空リストを返す(self) -> None:
        """Returns empty list when priced.rows is empty."""
        data: dict[str, Any] = {"priced": {"rows": []}}
        result = parse_ipo_calendar(data)
        assert result == []

    def test_正常系_priced欠落で空リストを返す(self) -> None:
        """Returns empty list when priced key is missing."""
        data: dict[str, Any] = {}
        result = parse_ipo_calendar(data)
        assert result == []

    def test_正常系_rows欠落で空リストを返す(self) -> None:
        """Returns empty list when rows key is missing under priced."""
        data: dict[str, Any] = {"priced": {}}
        result = parse_ipo_calendar(data)
        assert result == []

    def test_異常系_rowsがlist以外でNasdaqParseError(self) -> None:
        """Raises NasdaqParseError when priced.rows is not a list."""
        data: dict[str, Any] = {"priced": {"rows": 42}}
        with pytest.raises(NasdaqParseError):
            parse_ipo_calendar(data)

    def test_正常系_frozen_dataclass(self) -> None:
        """IpoRecord is immutable (frozen)."""
        data: dict[str, Any] = {
            "priced": {
                "rows": [
                    {
                        "dealID": "123456",
                        "proposedTickerSymbol": "NEWCO",
                        "companyName": "NewCo Inc.",
                        "proposedExchange": "NASDAQ",
                        "proposedSharePrice": "$15.00",
                        "sharesOffered": "10,000,000",
                    },
                ],
            },
        }
        result = parse_ipo_calendar(data)
        with pytest.raises(AttributeError):
            result[0].symbol = "AAPL"

    def test_正常系_upcomingとfiledからもパースできる(self) -> None:
        """Can also parse from upcoming and filed sections."""
        data: dict[str, Any] = {
            "upcoming": {
                "rows": [
                    {
                        "dealID": "111",
                        "proposedTickerSymbol": "UP1",
                        "companyName": "Upcoming Co.",
                        "proposedExchange": "NASDAQ",
                        "proposedSharePrice": "$10.00",
                        "sharesOffered": "1,000,000",
                    },
                ],
            },
        }
        result = parse_ipo_calendar(data)
        assert len(result) == 1
        assert result[0].symbol == "UP1"
