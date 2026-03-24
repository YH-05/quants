"""Unit tests for NasdaqClient company data endpoint methods.

Tests cover:
- get_insider_trades: normal, cache hit/miss, symbol validation, empty data, force refresh
- get_institutional_holdings: normal, cache hit/miss, symbol validation, empty data, force refresh
- get_financials: normal, cache hit/miss, symbol validation, empty data, frequency param, force refresh

See Also
--------
market.nasdaq.client : NasdaqClient implementation.
market.nasdaq.client_types : InsiderTrade, InstitutionalHolding, FinancialStatement types.
market.nasdaq.client_parsers : parse_insider_trades, parse_institutional_holdings, parse_financials.
tests.market.nasdaq.conftest : Shared fixtures.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any
from unittest.mock import MagicMock

import pytest

from market.nasdaq.client_types import (
    FinancialStatement,
    FinancialStatementRow,
    InsiderTrade,
    InstitutionalHolding,
    NasdaqFetchOptions,
)

if TYPE_CHECKING:
    from market.nasdaq.client import NasdaqClient

# =============================================================================
# InsiderTrade Type Tests
# =============================================================================


class TestInsiderTradeType:
    """Tests for InsiderTrade frozen dataclass."""

    def test_正常系_10フィールドを持つfrozen_dataclass(self) -> None:
        """InsiderTrade is a frozen dataclass with 10 fields."""
        trade = InsiderTrade(
            insider_name="John Smith",
            relation="Officer",
            transaction_type="Sold",
            ownership_type="Direct",
            shares_traded="10,000",
            price="$150.00",
            value="$1,500,000",
            date="03/15/2026",
            shares_held="50,000",
            url="/insider-trades/john-smith",
        )

        assert trade.insider_name == "John Smith"
        assert trade.relation == "Officer"
        assert trade.transaction_type == "Sold"
        assert trade.ownership_type == "Direct"
        assert trade.shares_traded == "10,000"
        assert trade.price == "$150.00"
        assert trade.value == "$1,500,000"
        assert trade.date == "03/15/2026"
        assert trade.shares_held == "50,000"
        assert trade.url == "/insider-trades/john-smith"

    def test_正常系_frozen_dataclassであること(self) -> None:
        """InsiderTrade is immutable (frozen)."""
        trade = InsiderTrade(insider_name="John Smith")

        with pytest.raises(AttributeError):
            trade.insider_name = "changed"

    def test_正常系_オプショナルフィールドがNoneデフォルト(self) -> None:
        """Optional fields default to None."""
        trade = InsiderTrade()

        assert trade.insider_name is None
        assert trade.relation is None
        assert trade.transaction_type is None
        assert trade.ownership_type is None
        assert trade.shares_traded is None
        assert trade.price is None
        assert trade.value is None
        assert trade.date is None
        assert trade.shares_held is None
        assert trade.url is None


# =============================================================================
# InstitutionalHolding Type Tests
# =============================================================================


class TestInstitutionalHoldingType:
    """Tests for InstitutionalHolding frozen dataclass."""

    def test_正常系_8フィールドを持つfrozen_dataclass(self) -> None:
        """InstitutionalHolding is a frozen dataclass with 8 fields."""
        holding = InstitutionalHolding(
            holder_name="Vanguard Group Inc",
            shares="1,200,000,000",
            value="$180,000,000,000",
            change="5,000,000",
            change_percent="0.42%",
            date_reported="12/31/2025",
            filing_date="02/14/2026",
            url="/institutional-holdings/vanguard",
        )

        assert holding.holder_name == "Vanguard Group Inc"
        assert holding.shares == "1,200,000,000"
        assert holding.value == "$180,000,000,000"
        assert holding.change == "5,000,000"
        assert holding.change_percent == "0.42%"
        assert holding.date_reported == "12/31/2025"
        assert holding.filing_date == "02/14/2026"
        assert holding.url == "/institutional-holdings/vanguard"

    def test_正常系_frozen_dataclassであること(self) -> None:
        """InstitutionalHolding is immutable (frozen)."""
        holding = InstitutionalHolding(holder_name="Vanguard Group Inc")

        with pytest.raises(AttributeError):
            holding.holder_name = "changed"

    def test_正常系_オプショナルフィールドがNoneデフォルト(self) -> None:
        """Optional fields default to None."""
        holding = InstitutionalHolding()

        assert holding.holder_name is None
        assert holding.shares is None
        assert holding.value is None
        assert holding.change is None
        assert holding.change_percent is None
        assert holding.date_reported is None
        assert holding.filing_date is None
        assert holding.url is None


# =============================================================================
# FinancialStatement Type Tests
# =============================================================================


class TestFinancialStatementType:
    """Tests for FinancialStatement frozen dataclass."""

    def test_正常系_3セクションを持つ構造体(self) -> None:
        """FinancialStatement has income_statement, balance_sheet, cash_flow sections."""
        row = FinancialStatementRow(
            label="Total Revenue",
            values=["$394,328", "$383,285", "$365,817"],
        )
        statement = FinancialStatement(
            symbol="AAPL",
            frequency="annual",
            headers=["2025", "2024", "2023"],
            income_statement=[row],
            balance_sheet=[],
            cash_flow=[],
        )

        assert statement.symbol == "AAPL"
        assert statement.frequency == "annual"
        assert len(statement.headers) == 3
        assert len(statement.income_statement) == 1
        assert statement.income_statement[0].label == "Total Revenue"
        assert isinstance(statement.balance_sheet, list)
        assert isinstance(statement.cash_flow, list)

    def test_正常系_frozen_dataclassであること(self) -> None:
        """FinancialStatement is immutable (frozen)."""
        statement = FinancialStatement(
            symbol="AAPL",
            frequency="annual",
            headers=[],
            income_statement=[],
            balance_sheet=[],
            cash_flow=[],
        )

        with pytest.raises(AttributeError):
            statement.symbol = "changed"

    def test_正常系_FinancialStatementRowがfrozen(self) -> None:
        """FinancialStatementRow is immutable (frozen)."""
        row = FinancialStatementRow(label="Revenue", values=["$100"])

        with pytest.raises(AttributeError):
            row.label = "changed"


# =============================================================================
# get_insider_trades Tests
# =============================================================================


class TestGetInsiderTrades:
    """Tests for NasdaqClient.get_insider_trades."""

    def test_正常系_insider_tradesを取得できる(
        self,
        nasdaq_client: NasdaqClient,
        mock_cache: MagicMock,
        mock_nasdaq_session: MagicMock,
    ) -> None:
        """Fetches insider trades from API and returns list[InsiderTrade]."""
        mock_cache.get.return_value = None

        raw_response: dict[str, Any] = {
            "data": {
                "insiderTransactions": {
                    "rows": [
                        {
                            "insider": "WILLIAMS JEFFREY E",
                            "relation": "Officer",
                            "lastDate": "03/15/2026",
                            "transactionType": "Sold",
                            "ownType": "Direct",
                            "sharesTraded": "50,000",
                            "price": "$227.63",
                            "sharesHeld": "100,000",
                            "value": "$11,381,500",
                            "url": "",
                        },
                        {
                            "insider": "COOK TIMOTHY D",
                            "relation": "Chief Executive Officer",
                            "lastDate": "03/10/2026",
                            "transactionType": "Sold",
                            "ownType": "Direct",
                            "sharesTraded": "200,000",
                            "price": "$230.00",
                            "sharesHeld": "3,280,000",
                            "value": "$46,000,000",
                            "url": "",
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

        result = nasdaq_client.get_insider_trades("AAPL")

        assert isinstance(result, list)
        assert len(result) == 2
        assert isinstance(result[0], InsiderTrade)
        assert result[0].insider_name == "WILLIAMS JEFFREY E"
        assert result[0].relation == "Officer"
        assert result[0].transaction_type == "Sold"
        assert result[0].shares_traded == "50,000"
        assert result[0].price == "$227.63"
        assert result[0].value == "$11,381,500"
        assert result[0].date == "03/15/2026"
        assert result[1].insider_name == "COOK TIMOTHY D"

    def test_正常系_キャッシュヒット時にAPIを呼ばない(
        self,
        nasdaq_client: NasdaqClient,
        mock_cache: MagicMock,
        mock_nasdaq_session: MagicMock,
    ) -> None:
        """When cache has data, API is not called."""
        cached_data = [
            InsiderTrade(
                insider_name="COOK TIMOTHY D",
                relation="Chief Executive Officer",
                transaction_type="Sold",
            ),
        ]
        mock_cache.get.return_value = cached_data

        result = nasdaq_client.get_insider_trades("AAPL")

        assert result == cached_data
        mock_nasdaq_session.get_with_retry.assert_not_called()

    def test_異常系_空シンボルでValueError(
        self,
        nasdaq_client: NasdaqClient,
    ) -> None:
        """Empty symbol raises ValueError."""
        with pytest.raises(ValueError, match="Symbol must not be empty"):
            nasdaq_client.get_insider_trades("")

    def test_正常系_空データで空リストを返す(
        self,
        nasdaq_client: NasdaqClient,
        mock_cache: MagicMock,
        mock_nasdaq_session: MagicMock,
    ) -> None:
        """Empty insider trades data returns empty list."""
        mock_cache.get.return_value = None

        raw_response: dict[str, Any] = {
            "data": {},
            "message": None,
            "status": {"rCode": 200, "bCodeMessage": None},
        }
        mock_response = MagicMock()
        mock_response.json.return_value = raw_response
        mock_nasdaq_session.get_with_retry.return_value = mock_response

        result = nasdaq_client.get_insider_trades("AAPL")

        assert isinstance(result, list)
        assert result == []

    def test_正常系_force_refreshでキャッシュを無視(
        self,
        nasdaq_client: NasdaqClient,
        mock_cache: MagicMock,
        mock_nasdaq_session: MagicMock,
    ) -> None:
        """Force refresh bypasses cache."""
        mock_cache.get.return_value = "old_data"

        raw_response: dict[str, Any] = {
            "data": {},
            "message": None,
            "status": {"rCode": 200, "bCodeMessage": None},
        }
        mock_response = MagicMock()
        mock_response.json.return_value = raw_response
        mock_nasdaq_session.get_with_retry.return_value = mock_response

        options = NasdaqFetchOptions(force_refresh=True)
        nasdaq_client.get_insider_trades("AAPL", options=options)

        mock_cache.get.assert_not_called()
        mock_nasdaq_session.get_with_retry.assert_called_once()


# =============================================================================
# get_institutional_holdings Tests
# =============================================================================


class TestGetInstitutionalHoldings:
    """Tests for NasdaqClient.get_institutional_holdings."""

    def test_正常系_institutional_holdingsを取得できる(
        self,
        nasdaq_client: NasdaqClient,
        mock_cache: MagicMock,
        mock_nasdaq_session: MagicMock,
    ) -> None:
        """Fetches institutional holdings from API and returns list[InstitutionalHolding]."""
        mock_cache.get.return_value = None

        raw_response: dict[str, Any] = {
            "data": {
                "holdingsTransactions": {
                    "rows": [
                        {
                            "ownerName": "Vanguard Group Inc",
                            "date": "12/31/2025",
                            "sharesHeld": "1,200,000,000",
                            "marketValue": "$180,000,000,000",
                            "sharesChange": "5,000,000",
                            "sharesChangePct": "0.42%",
                            "filingDate": "02/14/2026",
                            "url": "",
                        },
                        {
                            "ownerName": "BlackRock Inc",
                            "date": "12/31/2025",
                            "sharesHeld": "1,050,000,000",
                            "marketValue": "$157,500,000,000",
                            "sharesChange": "-2,000,000",
                            "sharesChangePct": "-0.19%",
                            "filingDate": "02/10/2026",
                            "url": "",
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

        result = nasdaq_client.get_institutional_holdings("AAPL")

        assert isinstance(result, list)
        assert len(result) == 2
        assert isinstance(result[0], InstitutionalHolding)
        assert result[0].holder_name == "Vanguard Group Inc"
        assert result[0].shares == "1,200,000,000"
        assert result[0].value == "$180,000,000,000"
        assert result[0].change == "5,000,000"
        assert result[0].change_percent == "0.42%"
        assert result[0].date_reported == "12/31/2025"
        assert result[0].filing_date == "02/14/2026"
        assert result[1].holder_name == "BlackRock Inc"

    def test_正常系_キャッシュヒット時にAPIを呼ばない(
        self,
        nasdaq_client: NasdaqClient,
        mock_cache: MagicMock,
        mock_nasdaq_session: MagicMock,
    ) -> None:
        """When cache has data, API is not called."""
        cached_data = [
            InstitutionalHolding(
                holder_name="Vanguard Group Inc",
                shares="1,200,000,000",
            ),
        ]
        mock_cache.get.return_value = cached_data

        result = nasdaq_client.get_institutional_holdings("AAPL")

        assert result == cached_data
        mock_nasdaq_session.get_with_retry.assert_not_called()

    def test_異常系_空シンボルでValueError(
        self,
        nasdaq_client: NasdaqClient,
    ) -> None:
        """Empty symbol raises ValueError."""
        with pytest.raises(ValueError, match="Symbol must not be empty"):
            nasdaq_client.get_institutional_holdings("")

    def test_正常系_空データで空リストを返す(
        self,
        nasdaq_client: NasdaqClient,
        mock_cache: MagicMock,
        mock_nasdaq_session: MagicMock,
    ) -> None:
        """Empty institutional holdings data returns empty list."""
        mock_cache.get.return_value = None

        raw_response: dict[str, Any] = {
            "data": {},
            "message": None,
            "status": {"rCode": 200, "bCodeMessage": None},
        }
        mock_response = MagicMock()
        mock_response.json.return_value = raw_response
        mock_nasdaq_session.get_with_retry.return_value = mock_response

        result = nasdaq_client.get_institutional_holdings("AAPL")

        assert isinstance(result, list)
        assert result == []

    def test_正常系_force_refreshでキャッシュを無視(
        self,
        nasdaq_client: NasdaqClient,
        mock_cache: MagicMock,
        mock_nasdaq_session: MagicMock,
    ) -> None:
        """Force refresh bypasses cache."""
        mock_cache.get.return_value = "old_data"

        raw_response: dict[str, Any] = {
            "data": {},
            "message": None,
            "status": {"rCode": 200, "bCodeMessage": None},
        }
        mock_response = MagicMock()
        mock_response.json.return_value = raw_response
        mock_nasdaq_session.get_with_retry.return_value = mock_response

        options = NasdaqFetchOptions(force_refresh=True)
        nasdaq_client.get_institutional_holdings("AAPL", options=options)

        mock_cache.get.assert_not_called()
        mock_nasdaq_session.get_with_retry.assert_called_once()


# =============================================================================
# get_financials Tests
# =============================================================================


class TestGetFinancials:
    """Tests for NasdaqClient.get_financials."""

    def test_正常系_financialsを取得できる(
        self,
        nasdaq_client: NasdaqClient,
        mock_cache: MagicMock,
        mock_nasdaq_session: MagicMock,
    ) -> None:
        """Fetches financials from API and returns FinancialStatement."""
        mock_cache.get.return_value = None

        raw_response: dict[str, Any] = {
            "data": {
                "incomeStatementTable": {
                    "headers": {
                        "values": ["", "2025", "2024", "2023"],
                    },
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
                            "value3": "$96,995",
                            "value4": "$94,680",
                        },
                    ],
                },
                "balanceSheetTable": {
                    "headers": {
                        "values": ["", "2025", "2024", "2023"],
                    },
                    "rows": [
                        {
                            "value1": "Total Assets",
                            "value2": "$352,583",
                            "value3": "$352,755",
                            "value4": "$338,516",
                        },
                    ],
                },
                "cashFlowTable": {
                    "headers": {
                        "values": ["", "2025", "2024", "2023"],
                    },
                    "rows": [
                        {
                            "value1": "Operating Cash Flow",
                            "value2": "$118,254",
                            "value3": "$110,543",
                            "value4": "$110,543",
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

        result = nasdaq_client.get_financials("AAPL")

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
        assert result.balance_sheet[0].label == "Total Assets"
        assert len(result.cash_flow) == 1
        assert result.cash_flow[0].label == "Operating Cash Flow"

    def test_正常系_frequencyパラメータでquarterlyを指定できる(
        self,
        nasdaq_client: NasdaqClient,
        mock_cache: MagicMock,
        mock_nasdaq_session: MagicMock,
    ) -> None:
        """Frequency parameter is passed to API and stored in result."""
        mock_cache.get.return_value = None

        raw_response: dict[str, Any] = {
            "data": {
                "incomeStatementTable": {
                    "headers": {
                        "values": ["", "Q1 2026", "Q4 2025"],
                    },
                    "rows": [
                        {
                            "value1": "Total Revenue",
                            "value2": "$95,000",
                            "value3": "$124,300",
                        },
                    ],
                },
                "balanceSheetTable": {
                    "headers": {"values": ["", "Q1 2026", "Q4 2025"]},
                    "rows": [],
                },
                "cashFlowTable": {
                    "headers": {"values": ["", "Q1 2026", "Q4 2025"]},
                    "rows": [],
                },
            },
            "message": None,
            "status": {"rCode": 200, "bCodeMessage": None},
        }
        mock_response = MagicMock()
        mock_response.json.return_value = raw_response
        mock_nasdaq_session.get_with_retry.return_value = mock_response

        result = nasdaq_client.get_financials("AAPL", frequency="quarterly")

        assert result.frequency == "quarterly"
        assert result.headers == ["Q1 2026", "Q4 2025"]
        # Verify query params passed to API
        call_args = mock_nasdaq_session.get_with_retry.call_args
        assert call_args is not None
        params = call_args.kwargs.get("params") or (
            call_args[1].get("params") if len(call_args) > 1 else None
        )
        assert params is not None
        assert params.get("frequency") == "quarterly"

    def test_正常系_キャッシュヒット時にAPIを呼ばない(
        self,
        nasdaq_client: NasdaqClient,
        mock_cache: MagicMock,
        mock_nasdaq_session: MagicMock,
    ) -> None:
        """When cache has data, API is not called."""
        cached_data = FinancialStatement(
            symbol="AAPL",
            frequency="annual",
            headers=["2025", "2024"],
            income_statement=[],
            balance_sheet=[],
            cash_flow=[],
        )
        mock_cache.get.return_value = cached_data

        result = nasdaq_client.get_financials("AAPL")

        assert result == cached_data
        mock_nasdaq_session.get_with_retry.assert_not_called()

    def test_異常系_空シンボルでValueError(
        self,
        nasdaq_client: NasdaqClient,
    ) -> None:
        """Empty symbol raises ValueError."""
        with pytest.raises(ValueError, match="Symbol must not be empty"):
            nasdaq_client.get_financials("")

    def test_異常系_不正なfrequencyでValueError(
        self,
        nasdaq_client: NasdaqClient,
    ) -> None:
        """Raise ValueError for invalid frequency values."""
        with pytest.raises(ValueError, match="frequency must be one of"):
            nasdaq_client.get_financials("AAPL", frequency="invalid")  # type: ignore[arg-type]

    def test_正常系_空データで空リストを返す(
        self,
        nasdaq_client: NasdaqClient,
        mock_cache: MagicMock,
        mock_nasdaq_session: MagicMock,
    ) -> None:
        """Empty financials data returns FinancialStatement with empty sections."""
        mock_cache.get.return_value = None

        raw_response: dict[str, Any] = {
            "data": {},
            "message": None,
            "status": {"rCode": 200, "bCodeMessage": None},
        }
        mock_response = MagicMock()
        mock_response.json.return_value = raw_response
        mock_nasdaq_session.get_with_retry.return_value = mock_response

        result = nasdaq_client.get_financials("AAPL")

        assert isinstance(result, FinancialStatement)
        assert result.income_statement == []
        assert result.balance_sheet == []
        assert result.cash_flow == []

    def test_正常系_force_refreshでキャッシュを無視(
        self,
        nasdaq_client: NasdaqClient,
        mock_cache: MagicMock,
        mock_nasdaq_session: MagicMock,
    ) -> None:
        """Force refresh bypasses cache."""
        mock_cache.get.return_value = "old_data"

        raw_response: dict[str, Any] = {
            "data": {},
            "message": None,
            "status": {"rCode": 200, "bCodeMessage": None},
        }
        mock_response = MagicMock()
        mock_response.json.return_value = raw_response
        mock_nasdaq_session.get_with_retry.return_value = mock_response

        options = NasdaqFetchOptions(force_refresh=True)
        nasdaq_client.get_financials("AAPL", options=options)

        mock_cache.get.assert_not_called()
        mock_nasdaq_session.get_with_retry.assert_called_once()

    def test_正常系_annualとquarterlyで異なるキャッシュキー(
        self,
        nasdaq_client: NasdaqClient,
        mock_cache: MagicMock,
        mock_nasdaq_session: MagicMock,
    ) -> None:
        """Annual and quarterly use different cache keys."""
        mock_cache.get.return_value = None

        raw_response: dict[str, Any] = {
            "data": {},
            "message": None,
            "status": {"rCode": 200, "bCodeMessage": None},
        }
        mock_response = MagicMock()
        mock_response.json.return_value = raw_response
        mock_nasdaq_session.get_with_retry.return_value = mock_response

        nasdaq_client.get_financials("AAPL", frequency="annual")
        nasdaq_client.get_financials("AAPL", frequency="quarterly")

        # Verify two different cache keys were checked
        cache_keys = [call.args[0] for call in mock_cache.get.call_args_list]
        assert len(cache_keys) == 2
        assert cache_keys[0] != cache_keys[1]
        assert "annual" in cache_keys[0]
        assert "quarterly" in cache_keys[1]
