"""Unit tests for NasdaqClient quote data endpoint methods.

Tests cover:
- ShortInterestRecord type: fields, frozen, defaults
- DividendRecord type: fields, frozen, defaults
- get_short_interest: normal, cache hit/miss, symbol validation, empty data, force refresh
- get_dividend_history: normal, cache hit/miss, symbol validation, empty data, force refresh

See Also
--------
market.nasdaq.client : NasdaqClient implementation.
market.nasdaq.client_types : ShortInterestRecord, DividendRecord types.
market.nasdaq.client_parsers : parse_short_interest, parse_dividend_history.
tests.market.nasdaq.conftest : Shared fixtures.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any
from unittest.mock import MagicMock

import pytest

from market.nasdaq.client_types import (
    DividendRecord,
    NasdaqFetchOptions,
    ShortInterestRecord,
)

if TYPE_CHECKING:
    from market.nasdaq.client import NasdaqClient

# =============================================================================
# ShortInterestRecord Type Tests
# =============================================================================


class TestShortInterestRecordType:
    """Tests for ShortInterestRecord frozen dataclass."""

    def test_正常系_6フィールドを持つfrozen_dataclass(self) -> None:
        """ShortInterestRecord is a frozen dataclass with 6 fields."""
        record = ShortInterestRecord(
            settlement_date="03/15/2026",
            short_interest="15,000,000",
            avg_daily_volume="50,000,000",
            days_to_cover="0.30",
            change="-500,000",
            change_percent="-3.23%",
        )

        assert record.settlement_date == "03/15/2026"
        assert record.short_interest == "15,000,000"
        assert record.avg_daily_volume == "50,000,000"
        assert record.days_to_cover == "0.30"
        assert record.change == "-500,000"
        assert record.change_percent == "-3.23%"

    def test_正常系_frozen_dataclassであること(self) -> None:
        """ShortInterestRecord is immutable (frozen)."""
        record = ShortInterestRecord(settlement_date="03/15/2026")

        with pytest.raises(AttributeError):
            record.settlement_date = "changed"

    def test_正常系_オプショナルフィールドがNoneデフォルト(self) -> None:
        """Optional fields default to None."""
        record = ShortInterestRecord()

        assert record.settlement_date is None
        assert record.short_interest is None
        assert record.avg_daily_volume is None
        assert record.days_to_cover is None
        assert record.change is None
        assert record.change_percent is None


# =============================================================================
# DividendRecord Type Tests
# =============================================================================


class TestDividendRecordType:
    """Tests for DividendRecord frozen dataclass."""

    def test_正常系_7フィールドを持つfrozen_dataclass(self) -> None:
        """DividendRecord is a frozen dataclass with 7 fields."""
        record = DividendRecord(
            ex_date="02/07/2026",
            payment_date="02/13/2026",
            record_date="02/10/2026",
            declaration_date="01/30/2026",
            dividend_type="Cash",
            amount="$0.25",
            yield_="0.44%",
        )

        assert record.ex_date == "02/07/2026"
        assert record.payment_date == "02/13/2026"
        assert record.record_date == "02/10/2026"
        assert record.declaration_date == "01/30/2026"
        assert record.dividend_type == "Cash"
        assert record.amount == "$0.25"
        assert record.yield_ == "0.44%"

    def test_正常系_frozen_dataclassであること(self) -> None:
        """DividendRecord is immutable (frozen)."""
        record = DividendRecord(ex_date="02/07/2026")

        with pytest.raises(AttributeError):
            record.ex_date = "changed"

    def test_正常系_オプショナルフィールドがNoneデフォルト(self) -> None:
        """Optional fields default to None."""
        record = DividendRecord()

        assert record.ex_date is None
        assert record.payment_date is None
        assert record.record_date is None
        assert record.declaration_date is None
        assert record.dividend_type is None
        assert record.amount is None
        assert record.yield_ is None


# =============================================================================
# get_short_interest Tests
# =============================================================================


class TestGetShortInterest:
    """Tests for NasdaqClient.get_short_interest."""

    def test_正常系_short_interestを取得できる(
        self,
        nasdaq_client: NasdaqClient,
        mock_cache: MagicMock,
        mock_nasdaq_session: MagicMock,
    ) -> None:
        """Fetches short interest from API and returns list[ShortInterestRecord]."""
        mock_cache.get.return_value = None

        raw_response: dict[str, Any] = {
            "data": {
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
                            "change": "1,200,000",
                            "changePct": "8.39%",
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

        result = nasdaq_client.get_short_interest("AAPL")

        assert isinstance(result, list)
        assert len(result) == 2
        assert isinstance(result[0], ShortInterestRecord)
        assert result[0].settlement_date == "03/15/2026"
        assert result[0].short_interest == "15,000,000"
        assert result[0].avg_daily_volume == "50,000,000"
        assert result[0].days_to_cover == "0.30"
        assert result[0].change == "-500,000"
        assert result[0].change_percent == "-3.23%"
        assert result[1].settlement_date == "02/28/2026"

    def test_正常系_キャッシュヒット時にAPIを呼ばない(
        self,
        nasdaq_client: NasdaqClient,
        mock_cache: MagicMock,
        mock_nasdaq_session: MagicMock,
    ) -> None:
        """When cache has data, API is not called."""
        cached_data = [
            ShortInterestRecord(
                settlement_date="03/15/2026",
                short_interest="15,000,000",
            ),
        ]
        mock_cache.get.return_value = cached_data

        result = nasdaq_client.get_short_interest("AAPL")

        assert result == cached_data
        mock_nasdaq_session.get_with_retry.assert_not_called()

    def test_異常系_空シンボルでValueError(
        self,
        nasdaq_client: NasdaqClient,
    ) -> None:
        """Empty symbol raises ValueError."""
        with pytest.raises(ValueError, match="Symbol must not be empty"):
            nasdaq_client.get_short_interest("")

    def test_正常系_空データで空リストを返す(
        self,
        nasdaq_client: NasdaqClient,
        mock_cache: MagicMock,
        mock_nasdaq_session: MagicMock,
    ) -> None:
        """Empty short interest data returns empty list."""
        mock_cache.get.return_value = None

        raw_response: dict[str, Any] = {
            "data": {},
            "message": None,
            "status": {"rCode": 200, "bCodeMessage": None},
        }
        mock_response = MagicMock()
        mock_response.json.return_value = raw_response
        mock_nasdaq_session.get_with_retry.return_value = mock_response

        result = nasdaq_client.get_short_interest("AAPL")

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
        nasdaq_client.get_short_interest("AAPL", options=options)

        mock_cache.get.assert_not_called()
        mock_nasdaq_session.get_with_retry.assert_called_once()


# =============================================================================
# get_dividend_history Tests
# =============================================================================


class TestGetDividendHistory:
    """Tests for NasdaqClient.get_dividend_history."""

    def test_正常系_dividend_historyを取得できる(
        self,
        nasdaq_client: NasdaqClient,
        mock_cache: MagicMock,
        mock_nasdaq_session: MagicMock,
    ) -> None:
        """Fetches dividend history from API and returns list[DividendRecord]."""
        mock_cache.get.return_value = None

        raw_response: dict[str, Any] = {
            "data": {
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
                        {
                            "exOrEffDate": "11/07/2025",
                            "paymentDate": "11/14/2025",
                            "recordDate": "11/10/2025",
                            "declarationDate": "10/30/2025",
                            "type": "Cash",
                            "amount": "$0.25",
                            "yield": "0.42%",
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

        result = nasdaq_client.get_dividend_history("AAPL")

        assert isinstance(result, list)
        assert len(result) == 2
        assert isinstance(result[0], DividendRecord)
        assert result[0].ex_date == "02/07/2026"
        assert result[0].payment_date == "02/13/2026"
        assert result[0].record_date == "02/10/2026"
        assert result[0].declaration_date == "01/30/2026"
        assert result[0].dividend_type == "Cash"
        assert result[0].amount == "$0.25"
        assert result[0].yield_ == "0.44%"
        assert result[1].ex_date == "11/07/2025"

    def test_正常系_キャッシュヒット時にAPIを呼ばない(
        self,
        nasdaq_client: NasdaqClient,
        mock_cache: MagicMock,
        mock_nasdaq_session: MagicMock,
    ) -> None:
        """When cache has data, API is not called."""
        cached_data = [
            DividendRecord(
                ex_date="02/07/2026",
                amount="$0.25",
                dividend_type="Cash",
            ),
        ]
        mock_cache.get.return_value = cached_data

        result = nasdaq_client.get_dividend_history("AAPL")

        assert result == cached_data
        mock_nasdaq_session.get_with_retry.assert_not_called()

    def test_異常系_空シンボルでValueError(
        self,
        nasdaq_client: NasdaqClient,
    ) -> None:
        """Empty symbol raises ValueError."""
        with pytest.raises(ValueError, match="Symbol must not be empty"):
            nasdaq_client.get_dividend_history("")

    def test_正常系_空データで空リストを返す(
        self,
        nasdaq_client: NasdaqClient,
        mock_cache: MagicMock,
        mock_nasdaq_session: MagicMock,
    ) -> None:
        """Empty dividend history data returns empty list."""
        mock_cache.get.return_value = None

        raw_response: dict[str, Any] = {
            "data": {},
            "message": None,
            "status": {"rCode": 200, "bCodeMessage": None},
        }
        mock_response = MagicMock()
        mock_response.json.return_value = raw_response
        mock_nasdaq_session.get_with_retry.return_value = mock_response

        result = nasdaq_client.get_dividend_history("AAPL")

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
        nasdaq_client.get_dividend_history("AAPL", options=options)

        mock_cache.get.assert_not_called()
        mock_nasdaq_session.get_with_retry.assert_called_once()
