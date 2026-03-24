"""Unit tests for non-calendar parsers in market.nasdaq.client_parsers module.

Tests cover direct invocation of parser functions that handle quote, company,
analyst, and financial data. Each parser is tested with representative data
(normal case), empty data (edge case), and structure-specific variations.

Test TODO List:
- [x] parse_short_interest: normal, empty rows, empty data
- [x] parse_dividend_history: normal, empty rows, empty data
- [x] parse_insider_trades: normal, empty rows, empty data
- [x] parse_institutional_holdings: normal, empty rows, empty data
- [x] parse_analyst_ratings: normal, empty rows, empty data
- [x] parse_target_price: nested structure, flat structure, empty data
- [x] parse_earnings_forecast: normal, empty data
- [x] parse_earnings_date: flat structure, nested structure, empty data
- [x] parse_financials: normal, empty data

See Also
--------
market.nasdaq.client_parsers : Parser functions under test.
tests.market.nasdaq.unit.test_client_parsers_calendar : Calendar parser tests.
"""

from __future__ import annotations

from typing import Any

import pytest

from market.nasdaq.client_parsers import (
    parse_analyst_ratings,
    parse_dividend_history,
    parse_earnings_date,
    parse_earnings_forecast,
    parse_financials,
    parse_insider_trades,
    parse_institutional_holdings,
    parse_short_interest,
    parse_target_price,
)
from market.nasdaq.client_types import (
    AnalystRatings,
    DividendRecord,
    EarningsDate,
    EarningsForecast,
    FinancialStatement,
    InsiderTrade,
    InstitutionalHolding,
    ShortInterestRecord,
    TargetPrice,
)

# =============================================================================
# parse_short_interest
# =============================================================================


class TestParseShortInterest:
    """Unit tests for parse_short_interest parser."""

    def test_正常系_代表的なデータでパース成功(self) -> None:
        """Parse short interest data with representative rows."""
        data: dict[str, Any] = {
            "shortInterestTable": {
                "rows": [
                    {
                        "settlementDate": "03/15/2026",
                        "interest": "15,000,000",
                        "averageDailyVolume": "50,000,000",
                        "daysToCover": "0.30",
                        "change": "-500,000",
                        "changePct": "-3.23%",
                    },
                    {
                        "settlementDate": "02/28/2026",
                        "interest": "15,500,000",
                        "averageDailyVolume": "48,000,000",
                        "daysToCover": "0.32",
                        "change": "200,000",
                        "changePct": "1.31%",
                    },
                ],
            },
        }

        result = parse_short_interest(data)

        assert len(result) == 2
        assert isinstance(result[0], ShortInterestRecord)
        assert result[0].settlement_date == "03/15/2026"
        assert result[0].short_interest == "15,000,000"
        assert result[0].avg_daily_volume == "50,000,000"
        assert result[0].days_to_cover == "0.30"
        assert result[0].change == "-500,000"
        assert result[0].change_percent == "-3.23%"

    def test_エッジケース_rows空で空リストを返す(self) -> None:
        """Return empty list when rows is an empty list."""
        data: dict[str, Any] = {"shortInterestTable": {"rows": []}}

        result = parse_short_interest(data)

        assert result == []

    def test_エッジケース_空dictで空リストを返す(self) -> None:
        """Return empty list when data is an empty dict."""
        result = parse_short_interest({})

        assert result == []


# =============================================================================
# parse_dividend_history
# =============================================================================


class TestParseDividendHistory:
    """Unit tests for parse_dividend_history parser."""

    def test_正常系_代表的なデータでパース成功(self) -> None:
        """Parse dividend history data with representative rows."""
        data: dict[str, Any] = {
            "dividends": {
                "rows": [
                    {
                        "exOrEffDate": "02/07/2026",
                        "paymentDate": "02/13/2026",
                        "recordDate": "02/10/2026",
                        "declarationDate": "01/30/2026",
                        "type": "Cash",
                        "amount": "$0.25",
                        "yield": "0.44%",
                    },
                ],
            },
        }

        result = parse_dividend_history(data)

        assert len(result) == 1
        assert isinstance(result[0], DividendRecord)
        assert result[0].ex_date == "02/07/2026"
        assert result[0].payment_date == "02/13/2026"
        assert result[0].record_date == "02/10/2026"
        assert result[0].declaration_date == "01/30/2026"
        assert result[0].dividend_type == "Cash"
        assert result[0].amount == "$0.25"
        assert result[0].yield_ == "0.44%"

    def test_エッジケース_rows空で空リストを返す(self) -> None:
        """Return empty list when rows is an empty list."""
        data: dict[str, Any] = {"dividends": {"rows": []}}

        result = parse_dividend_history(data)

        assert result == []

    def test_エッジケース_空dictで空リストを返す(self) -> None:
        """Return empty list when data is an empty dict."""
        result = parse_dividend_history({})

        assert result == []


# =============================================================================
# parse_insider_trades
# =============================================================================


class TestParseInsiderTrades:
    """Unit tests for parse_insider_trades parser."""

    def test_正常系_代表的なデータでパース成功(self) -> None:
        """Parse insider trades data with representative rows."""
        data: dict[str, Any] = {
            "insiderTransactions": {
                "rows": [
                    {
                        "insider": "COOK TIMOTHY D",
                        "relation": "Chief Executive Officer",
                        "transactionType": "Sold",
                        "ownType": "Direct",
                        "sharesTraded": "50,000",
                        "price": "$227.63",
                        "value": "$11,381,500",
                        "lastDate": "03/15/2026",
                        "sharesHeld": "100,000",
                        "url": "/insider/cook-timothy-d",
                    },
                ],
            },
        }

        result = parse_insider_trades(data)

        assert len(result) == 1
        assert isinstance(result[0], InsiderTrade)
        assert result[0].insider_name == "COOK TIMOTHY D"
        assert result[0].relation == "Chief Executive Officer"
        assert result[0].transaction_type == "Sold"
        assert result[0].ownership_type == "Direct"
        assert result[0].shares_traded == "50,000"
        assert result[0].price == "$227.63"
        assert result[0].value == "$11,381,500"
        assert result[0].date == "03/15/2026"
        assert result[0].shares_held == "100,000"
        assert result[0].url == "/insider/cook-timothy-d"

    def test_エッジケース_rows空で空リストを返す(self) -> None:
        """Return empty list when rows is an empty list."""
        data: dict[str, Any] = {"insiderTransactions": {"rows": []}}

        result = parse_insider_trades(data)

        assert result == []

    def test_エッジケース_空dictで空リストを返す(self) -> None:
        """Return empty list when data is an empty dict."""
        result = parse_insider_trades({})

        assert result == []


# =============================================================================
# parse_institutional_holdings
# =============================================================================


class TestParseInstitutionalHoldings:
    """Unit tests for parse_institutional_holdings parser."""

    def test_正常系_代表的なデータでパース成功(self) -> None:
        """Parse institutional holdings data with representative rows."""
        data: dict[str, Any] = {
            "holdingsTransactions": {
                "rows": [
                    {
                        "ownerName": "Vanguard Group Inc",
                        "sharesHeld": "1,200,000,000",
                        "marketValue": "$180,000,000,000",
                        "sharesChange": "5,000,000",
                        "sharesChangePct": "0.42%",
                        "date": "12/31/2025",
                        "filingDate": "02/14/2026",
                        "url": "/institutional/vanguard",
                    },
                ],
            },
        }

        result = parse_institutional_holdings(data)

        assert len(result) == 1
        assert isinstance(result[0], InstitutionalHolding)
        assert result[0].holder_name == "Vanguard Group Inc"
        assert result[0].shares == "1,200,000,000"
        assert result[0].value == "$180,000,000,000"
        assert result[0].change == "5,000,000"
        assert result[0].change_percent == "0.42%"
        assert result[0].date_reported == "12/31/2025"
        assert result[0].filing_date == "02/14/2026"
        assert result[0].url == "/institutional/vanguard"

    def test_エッジケース_rows空で空リストを返す(self) -> None:
        """Return empty list when rows is an empty list."""
        data: dict[str, Any] = {"holdingsTransactions": {"rows": []}}

        result = parse_institutional_holdings(data)

        assert result == []

    def test_エッジケース_空dictで空リストを返す(self) -> None:
        """Return empty list when data is an empty dict."""
        result = parse_institutional_holdings({})

        assert result == []


# =============================================================================
# parse_analyst_ratings
# =============================================================================


class TestParseAnalystRatings:
    """Unit tests for parse_analyst_ratings parser."""

    def test_正常系_代表的なデータでパース成功(self) -> None:
        """Parse analyst ratings with representative data."""
        data: dict[str, Any] = {
            "ratings": [
                {
                    "date": "Current Quarter",
                    "strongBuy": 10,
                    "buy": 15,
                    "hold": 5,
                    "sell": 1,
                    "strongSell": 0,
                },
                {
                    "date": "1 Month Ago",
                    "strongBuy": 9,
                    "buy": 14,
                    "hold": 6,
                    "sell": 2,
                    "strongSell": 0,
                },
            ],
        }

        result = parse_analyst_ratings(data, symbol="AAPL")

        assert isinstance(result, AnalystRatings)
        assert result.symbol == "AAPL"
        assert len(result.ratings) == 2
        assert result.ratings[0].date == "Current Quarter"
        assert result.ratings[0].strong_buy == 10
        assert result.ratings[0].buy == 15
        assert result.ratings[0].hold == 5
        assert result.ratings[0].sell == 1
        assert result.ratings[0].strong_sell == 0

    def test_エッジケース_ratings空で空リストを返す(self) -> None:
        """Return AnalystRatings with empty list when ratings is empty."""
        data: dict[str, Any] = {"ratings": []}

        result = parse_analyst_ratings(data, symbol="AAPL")

        assert isinstance(result, AnalystRatings)
        assert result.symbol == "AAPL"
        assert result.ratings == []

    def test_エッジケース_空dictで空リストを返す(self) -> None:
        """Return AnalystRatings with empty list when data is an empty dict."""
        result = parse_analyst_ratings({}, symbol="AAPL")

        assert isinstance(result, AnalystRatings)
        assert result.symbol == "AAPL"
        assert result.ratings == []


# =============================================================================
# parse_target_price
# =============================================================================


class TestParseTargetPrice:
    """Unit tests for parse_target_price parser."""

    def test_正常系_ネスト構造でパース成功(self) -> None:
        """Parse target price from nested structure (targetPrice key present)."""
        data: dict[str, Any] = {
            "targetPrice": {
                "high": "$280.00",
                "low": "$200.00",
                "mean": "$250.00",
                "median": "$248.00",
            },
        }

        result = parse_target_price(data, symbol="AAPL")

        assert isinstance(result, TargetPrice)
        assert result.symbol == "AAPL"
        assert result.high == "$280.00"
        assert result.low == "$200.00"
        assert result.mean == "$250.00"
        assert result.median == "$248.00"

    def test_正常系_フラット構造でパース成功(self) -> None:
        """Parse target price from flat structure (no targetPrice key, direct high/low)."""
        data: dict[str, Any] = {
            "high": "$300.00",
            "low": "$210.00",
            "mean": "$260.00",
            "median": "$255.00",
        }

        result = parse_target_price(data, symbol="MSFT")

        assert isinstance(result, TargetPrice)
        assert result.symbol == "MSFT"
        assert result.high == "$300.00"
        assert result.low == "$210.00"
        assert result.mean == "$260.00"
        assert result.median == "$255.00"

    def test_エッジケース_targetPriceがdict以外の場合フラットにフォールバック(
        self,
    ) -> None:
        """Fall back to flat structure when targetPrice is not a dict."""
        data: dict[str, Any] = {
            "targetPrice": "N/A",
            "high": "$150.00",
            "low": "$100.00",
            "mean": "$130.00",
            "median": "$128.00",
        }

        result = parse_target_price(data, symbol="GOOG")

        assert result.high == "$150.00"
        assert result.low == "$100.00"
        assert result.mean == "$130.00"
        assert result.median == "$128.00"

    def test_エッジケース_空dictで全フィールドNone(self) -> None:
        """Return TargetPrice with all None fields when data is empty."""
        result = parse_target_price({}, symbol="AAPL")

        assert isinstance(result, TargetPrice)
        assert result.symbol == "AAPL"
        assert result.high is None
        assert result.low is None
        assert result.mean is None
        assert result.median is None


# =============================================================================
# parse_earnings_forecast
# =============================================================================


class TestParseEarningsForecast:
    """Unit tests for parse_earnings_forecast parser."""

    def test_正常系_代表的なデータでパース成功(self) -> None:
        """Parse earnings forecast with yearly and quarterly rows."""
        data: dict[str, Any] = {
            "yearlyForecast": {
                "rows": [
                    {
                        "fiscalEnd": "Dec 2025",
                        "consensusEPSForecast": "$6.70",
                        "numOfEstimates": "38",
                        "highEPSForecast": "$7.10",
                        "lowEPSForecast": "$6.30",
                    },
                ],
            },
            "quarterlyForecast": {
                "rows": [
                    {
                        "fiscalEnd": "Q1 2026",
                        "consensusEPSForecast": "$2.35",
                        "numOfEstimates": "28",
                        "highEPSForecast": "$2.60",
                        "lowEPSForecast": "$2.10",
                    },
                ],
            },
        }

        result = parse_earnings_forecast(data, symbol="AAPL")

        assert isinstance(result, EarningsForecast)
        assert result.symbol == "AAPL"
        assert len(result.yearly) == 1
        assert len(result.quarterly) == 1
        assert result.yearly[0].fiscal_end == "Dec 2025"
        assert result.yearly[0].consensus_eps_forecast == "$6.70"
        assert result.quarterly[0].fiscal_end == "Q1 2026"

    def test_エッジケース_空dictで空リストを返す(self) -> None:
        """Return EarningsForecast with empty lists when data is empty."""
        result = parse_earnings_forecast({}, symbol="AAPL")

        assert isinstance(result, EarningsForecast)
        assert result.symbol == "AAPL"
        assert result.yearly == []
        assert result.quarterly == []


# =============================================================================
# parse_earnings_date
# =============================================================================


class TestParseEarningsDate:
    """Unit tests for parse_earnings_date parser."""

    def test_正常系_フラット構造でパース成功(self) -> None:
        """Parse earnings date from flat structure (earningsDate is a string)."""
        data: dict[str, Any] = {
            "earningsDate": "01/30/2026",
            "earningsTime": "After Market Close",
            "fiscalQuarterEnding": "Dec/2025",
            "epsForecast": "$2.35",
        }

        result = parse_earnings_date(data, symbol="AAPL")

        assert isinstance(result, EarningsDate)
        assert result.symbol == "AAPL"
        assert result.date == "01/30/2026"
        assert result.time == "After Market Close"
        assert result.fiscal_quarter_ending == "Dec/2025"
        assert result.eps_forecast == "$2.35"

    def test_正常系_ネスト構造でパース成功(self) -> None:
        """Parse earnings date from nested structure (earningsDate is a dict)."""
        data: dict[str, Any] = {
            "earningsDate": {
                "date": "04/25/2026",
                "time": "Before Market Open",
                "fiscalQuarterEnding": "Mar/2026",
                "epsForecast": "$1.80",
            },
        }

        result = parse_earnings_date(data, symbol="MSFT")

        assert isinstance(result, EarningsDate)
        assert result.symbol == "MSFT"
        assert result.date == "04/25/2026"
        assert result.time == "Before Market Open"
        assert result.fiscal_quarter_ending == "Mar/2026"
        assert result.eps_forecast == "$1.80"

    def test_エッジケース_空dictで全フィールドNone(self) -> None:
        """Return EarningsDate with all None fields when data is empty."""
        result = parse_earnings_date({}, symbol="AAPL")

        assert isinstance(result, EarningsDate)
        assert result.symbol == "AAPL"
        assert result.date is None
        assert result.time is None
        assert result.fiscal_quarter_ending is None
        assert result.eps_forecast is None

    def test_エッジケース_earningsDateがNoneの場合dateキーにフォールバック(
        self,
    ) -> None:
        """Fall back to 'date' key when earningsDate is None."""
        data: dict[str, Any] = {
            "earningsDate": None,
            "date": "05/15/2026",
            "earningsTime": "After Market Close",
            "fiscalQuarterEnding": "Mar/2026",
            "epsForecast": "$3.00",
        }

        result = parse_earnings_date(data, symbol="GOOGL")

        assert result.date == "05/15/2026"
        assert result.time == "After Market Close"


# =============================================================================
# parse_financials
# =============================================================================


class TestParseFinancials:
    """Unit tests for parse_financials parser."""

    def test_正常系_代表的なデータでパース成功(self) -> None:
        """Parse financials with income statement, balance sheet, cash flow."""
        data: dict[str, Any] = {
            "incomeStatementTable": {
                "headers": {"values": ["", "2025", "2024", "2023"]},
                "rows": [
                    {
                        "value1": "Total Revenue",
                        "value2": "$394,328",
                        "value3": "$383,285",
                        "value4": "$365,817",
                    },
                    {
                        "value1": "Net Income",
                        "value2": "$93,736",
                        "value3": "$97,000",
                        "value4": "$96,995",
                    },
                ],
            },
            "balanceSheetTable": {
                "headers": {"values": ["", "2025", "2024", "2023"]},
                "rows": [
                    {
                        "value1": "Total Assets",
                        "value2": "$352,583",
                        "value3": "$352,755",
                        "value4": "$352,583",
                    },
                ],
            },
            "cashFlowTable": {
                "headers": {"values": ["", "2025", "2024", "2023"]},
                "rows": [
                    {
                        "value1": "Operating Cash Flow",
                        "value2": "$118,254",
                        "value3": "$110,543",
                        "value4": "$110,543",
                    },
                ],
            },
        }

        result = parse_financials(data, symbol="AAPL", frequency="annual")

        assert isinstance(result, FinancialStatement)
        assert result.symbol == "AAPL"
        assert result.frequency == "annual"
        assert result.headers == ["2025", "2024", "2023"]
        assert len(result.income_statement) == 2
        assert result.income_statement[0].label == "Total Revenue"
        assert result.income_statement[0].values == [
            "$394,328",
            "$383,285",
            "$365,817",
        ]
        assert len(result.balance_sheet) == 1
        assert len(result.cash_flow) == 1

    def test_エッジケース_空dictで空FinancialStatementを返す(self) -> None:
        """Return FinancialStatement with empty lists when data is empty."""
        result = parse_financials({}, symbol="AAPL", frequency="annual")

        assert isinstance(result, FinancialStatement)
        assert result.symbol == "AAPL"
        assert result.frequency == "annual"
        assert result.headers == []
        assert result.income_statement == []
        assert result.balance_sheet == []
        assert result.cash_flow == []

    def test_正常系_quarterly頻度でパース成功(self) -> None:
        """Parse financials with quarterly frequency."""
        data: dict[str, Any] = {
            "incomeStatementTable": {
                "headers": {"values": ["", "Q1 2026", "Q4 2025"]},
                "rows": [
                    {
                        "value1": "Total Revenue",
                        "value2": "$98,000",
                        "value3": "$95,000",
                    },
                ],
            },
        }

        result = parse_financials(data, symbol="AAPL", frequency="quarterly")

        assert result.frequency == "quarterly"
        assert result.headers == ["Q1 2026", "Q4 2025"]
        assert len(result.income_statement) == 1
