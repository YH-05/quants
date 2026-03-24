"""Unit tests for NasdaqClient analyst endpoint methods.

Tests cover:
- get_earnings_forecast: normal, cache hit/miss, symbol validation, empty data
- get_analyst_ratings: normal, cache hit/miss, symbol validation, empty data
- get_target_price: normal, cache hit/miss, symbol validation, empty data
- get_earnings_date: normal, cache hit/miss, symbol validation, empty data
- get_analyst_summary: normal, aggregation, partial failure resilience

See Also
--------
market.nasdaq.client : NasdaqClient implementation.
tests.market.nasdaq.unit.test_client_calendar : Reference test patterns.
tests.market.nasdaq.conftest : Shared fixtures.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any
from unittest.mock import MagicMock

import pytest

from market.nasdaq.client_types import (
    AnalystRatings,
    AnalystSummary,
    EarningsDate,
    EarningsForecast,
    EarningsForecastPeriod,
    NasdaqFetchOptions,
    RatingCount,
    TargetPrice,
)
from market.nasdaq.errors import NasdaqAPIError

if TYPE_CHECKING:
    from market.nasdaq.client import NasdaqClient

# =============================================================================
# Earnings Forecast Tests
# =============================================================================


class TestGetEarningsForecast:
    """Tests for NasdaqClient.get_earnings_forecast."""

    def test_正常系_earnings_forecastを取得できる(
        self,
        nasdaq_client: NasdaqClient,
        mock_cache: MagicMock,
        mock_nasdaq_session: MagicMock,
    ) -> None:
        """Fetches earnings forecast from API and returns EarningsForecast."""
        mock_cache.get.return_value = None

        raw_response: dict[str, Any] = {
            "data": {
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
            },
            "message": None,
            "status": {"rCode": 200, "bCodeMessage": None},
        }
        mock_response = MagicMock()
        mock_response.json.return_value = raw_response
        mock_nasdaq_session.get_with_retry.return_value = mock_response

        result = nasdaq_client.get_earnings_forecast("AAPL")

        assert isinstance(result, EarningsForecast)
        assert result.symbol == "AAPL"
        assert len(result.yearly) == 1
        assert len(result.quarterly) == 1
        assert result.yearly[0].fiscal_end == "Dec 2025"
        assert result.yearly[0].consensus_eps_forecast == "$6.70"
        assert result.quarterly[0].fiscal_end == "Q1 2026"

    def test_正常系_キャッシュヒット時にAPIを呼ばない(
        self,
        nasdaq_client: NasdaqClient,
        mock_cache: MagicMock,
        mock_nasdaq_session: MagicMock,
    ) -> None:
        """When cache has data, API is not called."""
        cached_data = EarningsForecast(
            symbol="AAPL",
            yearly=[
                EarningsForecastPeriod(
                    fiscal_end="Dec 2025",
                    consensus_eps_forecast="$6.70",
                ),
            ],
            quarterly=[],
        )
        mock_cache.get.return_value = cached_data

        result = nasdaq_client.get_earnings_forecast("AAPL")

        assert result == cached_data
        mock_nasdaq_session.get_with_retry.assert_not_called()

    def test_異常系_空シンボルでValueError(
        self,
        nasdaq_client: NasdaqClient,
    ) -> None:
        """Empty symbol raises ValueError."""
        with pytest.raises(ValueError, match="Symbol must not be empty"):
            nasdaq_client.get_earnings_forecast("")

    def test_正常系_空データで空リストを返す(
        self,
        nasdaq_client: NasdaqClient,
        mock_cache: MagicMock,
        mock_nasdaq_session: MagicMock,
    ) -> None:
        """Empty forecast data returns EarningsForecast with empty lists."""
        mock_cache.get.return_value = None

        raw_response: dict[str, Any] = {
            "data": {},
            "message": None,
            "status": {"rCode": 200, "bCodeMessage": None},
        }
        mock_response = MagicMock()
        mock_response.json.return_value = raw_response
        mock_nasdaq_session.get_with_retry.return_value = mock_response

        result = nasdaq_client.get_earnings_forecast("AAPL")

        assert isinstance(result, EarningsForecast)
        assert result.yearly == []
        assert result.quarterly == []

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
        nasdaq_client.get_earnings_forecast("AAPL", options=options)

        mock_cache.get.assert_not_called()
        mock_nasdaq_session.get_with_retry.assert_called_once()

    def test_正常系_yearly_forecastの全フィールドをパースできる(
        self,
        nasdaq_client: NasdaqClient,
        mock_cache: MagicMock,
        mock_nasdaq_session: MagicMock,
    ) -> None:
        """All fields of yearly forecast are parsed correctly."""
        mock_cache.get.return_value = None

        raw_response: dict[str, Any] = {
            "data": {
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
                "quarterlyForecast": {"rows": []},
            },
            "message": None,
            "status": {"rCode": 200, "bCodeMessage": None},
        }
        mock_response = MagicMock()
        mock_response.json.return_value = raw_response
        mock_nasdaq_session.get_with_retry.return_value = mock_response

        result = nasdaq_client.get_earnings_forecast("AAPL")

        period = result.yearly[0]
        assert period.fiscal_end == "Dec 2025"
        assert period.consensus_eps_forecast == "$6.70"
        assert period.num_of_estimates == "38"
        assert period.high_eps_forecast == "$7.10"
        assert period.low_eps_forecast == "$6.30"


# =============================================================================
# Analyst Ratings Tests
# =============================================================================


class TestGetAnalystRatings:
    """Tests for NasdaqClient.get_analyst_ratings."""

    def test_正常系_analyst_ratingsを取得できる(
        self,
        nasdaq_client: NasdaqClient,
        mock_cache: MagicMock,
        mock_nasdaq_session: MagicMock,
    ) -> None:
        """Fetches analyst ratings from API and returns AnalystRatings."""
        mock_cache.get.return_value = None

        raw_response: dict[str, Any] = {
            "data": {
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
            },
            "message": None,
            "status": {"rCode": 200, "bCodeMessage": None},
        }
        mock_response = MagicMock()
        mock_response.json.return_value = raw_response
        mock_nasdaq_session.get_with_retry.return_value = mock_response

        result = nasdaq_client.get_analyst_ratings("AAPL")

        assert isinstance(result, AnalystRatings)
        assert result.symbol == "AAPL"
        assert len(result.ratings) == 2
        assert result.ratings[0].strong_buy == 10
        assert result.ratings[0].buy == 15
        assert result.ratings[0].hold == 5
        assert result.ratings[0].sell == 1
        assert result.ratings[0].strong_sell == 0
        assert result.ratings[0].date == "Current Quarter"

    def test_正常系_キャッシュヒット時にAPIを呼ばない(
        self,
        nasdaq_client: NasdaqClient,
        mock_cache: MagicMock,
        mock_nasdaq_session: MagicMock,
    ) -> None:
        """When cache has data, API is not called."""
        cached_data = AnalystRatings(
            symbol="AAPL",
            ratings=[
                RatingCount(
                    date="Current Quarter",
                    strong_buy=10,
                    buy=15,
                    hold=5,
                    sell=1,
                    strong_sell=0,
                ),
            ],
        )
        mock_cache.get.return_value = cached_data

        result = nasdaq_client.get_analyst_ratings("AAPL")

        assert result == cached_data
        mock_nasdaq_session.get_with_retry.assert_not_called()

    def test_異常系_空シンボルでValueError(
        self,
        nasdaq_client: NasdaqClient,
    ) -> None:
        """Empty symbol raises ValueError."""
        with pytest.raises(ValueError, match="Symbol must not be empty"):
            nasdaq_client.get_analyst_ratings("")

    def test_正常系_空データで空リストを返す(
        self,
        nasdaq_client: NasdaqClient,
        mock_cache: MagicMock,
        mock_nasdaq_session: MagicMock,
    ) -> None:
        """Empty ratings data returns AnalystRatings with empty list."""
        mock_cache.get.return_value = None

        raw_response: dict[str, Any] = {
            "data": {},
            "message": None,
            "status": {"rCode": 200, "bCodeMessage": None},
        }
        mock_response = MagicMock()
        mock_response.json.return_value = raw_response
        mock_nasdaq_session.get_with_retry.return_value = mock_response

        result = nasdaq_client.get_analyst_ratings("AAPL")

        assert isinstance(result, AnalystRatings)
        assert result.ratings == []

    def test_正常系_force_refreshでキャッシュを無視(
        self,
        nasdaq_client: NasdaqClient,
        mock_cache: MagicMock,
        mock_nasdaq_session: MagicMock,
    ) -> None:
        """Force refresh bypasses cache."""
        mock_cache.get.return_value = "old_data"

        raw_response: dict[str, Any] = {
            "data": {"ratings": []},
            "message": None,
            "status": {"rCode": 200, "bCodeMessage": None},
        }
        mock_response = MagicMock()
        mock_response.json.return_value = raw_response
        mock_nasdaq_session.get_with_retry.return_value = mock_response

        options = NasdaqFetchOptions(force_refresh=True)
        nasdaq_client.get_analyst_ratings("AAPL", options=options)

        mock_cache.get.assert_not_called()
        mock_nasdaq_session.get_with_retry.assert_called_once()

    def test_正常系_buy_sell_holdカウントを保持する(
        self,
        nasdaq_client: NasdaqClient,
        mock_cache: MagicMock,
        mock_nasdaq_session: MagicMock,
    ) -> None:
        """AnalystRatings correctly holds buy/sell/hold counts and history."""
        mock_cache.get.return_value = None

        raw_response: dict[str, Any] = {
            "data": {
                "ratings": [
                    {
                        "date": "Current Quarter",
                        "strongBuy": 12,
                        "buy": 18,
                        "hold": 4,
                        "sell": 0,
                        "strongSell": 1,
                    },
                    {
                        "date": "1 Month Ago",
                        "strongBuy": 11,
                        "buy": 17,
                        "hold": 5,
                        "sell": 1,
                        "strongSell": 1,
                    },
                    {
                        "date": "2 Months Ago",
                        "strongBuy": 10,
                        "buy": 16,
                        "hold": 6,
                        "sell": 2,
                        "strongSell": 0,
                    },
                    {
                        "date": "3 Months Ago",
                        "strongBuy": 9,
                        "buy": 15,
                        "hold": 7,
                        "sell": 2,
                        "strongSell": 1,
                    },
                ],
            },
            "message": None,
            "status": {"rCode": 200, "bCodeMessage": None},
        }
        mock_response = MagicMock()
        mock_response.json.return_value = raw_response
        mock_nasdaq_session.get_with_retry.return_value = mock_response

        result = nasdaq_client.get_analyst_ratings("MSFT")

        assert len(result.ratings) == 4
        current = result.ratings[0]
        assert current.strong_buy == 12
        assert current.buy == 18
        assert current.hold == 4
        assert current.sell == 0
        assert current.strong_sell == 1
        assert result.ratings[3].date == "3 Months Ago"


# =============================================================================
# Target Price Tests
# =============================================================================


class TestGetTargetPrice:
    """Tests for NasdaqClient.get_target_price."""

    def test_正常系_target_priceを取得できる(
        self,
        nasdaq_client: NasdaqClient,
        mock_cache: MagicMock,
        mock_nasdaq_session: MagicMock,
    ) -> None:
        """Fetches target price from API and returns TargetPrice."""
        mock_cache.get.return_value = None

        raw_response: dict[str, Any] = {
            "data": {
                "targetPrice": {
                    "high": "$280.00",
                    "low": "$200.00",
                    "mean": "$250.00",
                    "median": "$248.00",
                },
            },
            "message": None,
            "status": {"rCode": 200, "bCodeMessage": None},
        }
        mock_response = MagicMock()
        mock_response.json.return_value = raw_response
        mock_nasdaq_session.get_with_retry.return_value = mock_response

        result = nasdaq_client.get_target_price("AAPL")

        assert isinstance(result, TargetPrice)
        assert result.symbol == "AAPL"
        assert result.high == "$280.00"
        assert result.low == "$200.00"
        assert result.mean == "$250.00"
        assert result.median == "$248.00"

    def test_正常系_キャッシュヒット時にAPIを呼ばない(
        self,
        nasdaq_client: NasdaqClient,
        mock_cache: MagicMock,
        mock_nasdaq_session: MagicMock,
    ) -> None:
        """When cache has data, API is not called."""
        cached_data = TargetPrice(
            symbol="AAPL",
            high="$280.00",
            low="$200.00",
            mean="$250.00",
            median="$248.00",
        )
        mock_cache.get.return_value = cached_data

        result = nasdaq_client.get_target_price("AAPL")

        assert result == cached_data
        mock_nasdaq_session.get_with_retry.assert_not_called()

    def test_異常系_空シンボルでValueError(
        self,
        nasdaq_client: NasdaqClient,
    ) -> None:
        """Empty symbol raises ValueError."""
        with pytest.raises(ValueError, match="Symbol must not be empty"):
            nasdaq_client.get_target_price("")

    def test_正常系_high_low_mean_medianの4値を持つ(
        self,
        nasdaq_client: NasdaqClient,
        mock_cache: MagicMock,
        mock_nasdaq_session: MagicMock,
    ) -> None:
        """TargetPrice holds all 4 values."""
        mock_cache.get.return_value = None

        raw_response: dict[str, Any] = {
            "data": {
                "targetPrice": {
                    "high": "$300.00",
                    "low": "$180.00",
                    "mean": "$240.00",
                    "median": "$235.00",
                },
            },
            "message": None,
            "status": {"rCode": 200, "bCodeMessage": None},
        }
        mock_response = MagicMock()
        mock_response.json.return_value = raw_response
        mock_nasdaq_session.get_with_retry.return_value = mock_response

        result = nasdaq_client.get_target_price("MSFT")

        assert result.high is not None
        assert result.low is not None
        assert result.mean is not None
        assert result.median is not None

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
        nasdaq_client.get_target_price("AAPL", options=options)

        mock_cache.get.assert_not_called()
        mock_nasdaq_session.get_with_retry.assert_called_once()


# =============================================================================
# Earnings Date Tests
# =============================================================================


class TestGetEarningsDate:
    """Tests for NasdaqClient.get_earnings_date."""

    def test_正常系_earnings_dateを取得できる(
        self,
        nasdaq_client: NasdaqClient,
        mock_cache: MagicMock,
        mock_nasdaq_session: MagicMock,
    ) -> None:
        """Fetches earnings date from API and returns EarningsDate."""
        mock_cache.get.return_value = None

        raw_response: dict[str, Any] = {
            "data": {
                "earningsDate": "01/30/2026",
                "earningsTime": "After Market Close",
                "fiscalQuarterEnding": "Dec/2025",
                "epsForecast": "$2.35",
            },
            "message": None,
            "status": {"rCode": 200, "bCodeMessage": None},
        }
        mock_response = MagicMock()
        mock_response.json.return_value = raw_response
        mock_nasdaq_session.get_with_retry.return_value = mock_response

        result = nasdaq_client.get_earnings_date("AAPL")

        assert isinstance(result, EarningsDate)
        assert result.symbol == "AAPL"
        assert result.date == "01/30/2026"
        assert result.time == "After Market Close"
        assert result.fiscal_quarter_ending == "Dec/2025"
        assert result.eps_forecast == "$2.35"

    def test_正常系_キャッシュヒット時にAPIを呼ばない(
        self,
        nasdaq_client: NasdaqClient,
        mock_cache: MagicMock,
        mock_nasdaq_session: MagicMock,
    ) -> None:
        """When cache has data, API is not called."""
        cached_data = EarningsDate(
            symbol="AAPL",
            date="01/30/2026",
            time="After Market Close",
            fiscal_quarter_ending="Dec/2025",
            eps_forecast="$2.35",
        )
        mock_cache.get.return_value = cached_data

        result = nasdaq_client.get_earnings_date("AAPL")

        assert result == cached_data
        mock_nasdaq_session.get_with_retry.assert_not_called()

    def test_異常系_空シンボルでValueError(
        self,
        nasdaq_client: NasdaqClient,
    ) -> None:
        """Empty symbol raises ValueError."""
        with pytest.raises(ValueError, match="Symbol must not be empty"):
            nasdaq_client.get_earnings_date("")

    def test_正常系_4フィールドを持つfrozen_dataclass(self) -> None:
        """EarningsDate is a frozen dataclass with 4+1 fields."""
        ed = EarningsDate(
            symbol="AAPL",
            date="01/30/2026",
            time="After Market Close",
            fiscal_quarter_ending="Dec/2025",
            eps_forecast="$2.35",
        )

        # Verify frozen
        with pytest.raises(AttributeError):
            ed.date = "changed"  # type: ignore[misc]

        # Verify fields
        assert ed.symbol == "AAPL"
        assert ed.date == "01/30/2026"
        assert ed.time == "After Market Close"
        assert ed.fiscal_quarter_ending == "Dec/2025"
        assert ed.eps_forecast == "$2.35"

    def test_正常系_force_refreshでキャッシュを無視(
        self,
        nasdaq_client: NasdaqClient,
        mock_cache: MagicMock,
        mock_nasdaq_session: MagicMock,
    ) -> None:
        """Force refresh bypasses cache."""
        mock_cache.get.return_value = "old_data"

        raw_response: dict[str, Any] = {
            "data": {
                "earningsDate": "01/30/2026",
                "earningsTime": "After Market Close",
                "fiscalQuarterEnding": "Dec/2025",
                "epsForecast": "$2.35",
            },
            "message": None,
            "status": {"rCode": 200, "bCodeMessage": None},
        }
        mock_response = MagicMock()
        mock_response.json.return_value = raw_response
        mock_nasdaq_session.get_with_retry.return_value = mock_response

        options = NasdaqFetchOptions(force_refresh=True)
        nasdaq_client.get_earnings_date("AAPL", options=options)

        mock_cache.get.assert_not_called()
        mock_nasdaq_session.get_with_retry.assert_called_once()


# =============================================================================
# Analyst Summary Tests
# =============================================================================


class TestGetAnalystSummary:
    """Tests for NasdaqClient.get_analyst_summary."""

    def _setup_mock_responses(
        self,
        mock_nasdaq_session: MagicMock,
        mock_cache: MagicMock,
        responses: list[dict[str, Any]],
    ) -> None:
        """Set up mock responses for sequential API calls.

        Parameters
        ----------
        mock_nasdaq_session : MagicMock
            Mock session to configure.
        mock_cache : MagicMock
            Mock cache (always miss).
        responses : list[dict[str, Any]]
            List of raw API responses for sequential calls.
        """
        mock_cache.get.return_value = None
        side_effects = []
        for resp in responses:
            mock_resp = MagicMock()
            mock_resp.json.return_value = resp
            side_effects.append(mock_resp)
        mock_nasdaq_session.get_with_retry.side_effect = side_effects

    def test_正常系_4メソッドの結果をAnalystSummaryに集約(
        self,
        nasdaq_client: NasdaqClient,
        mock_cache: MagicMock,
        mock_nasdaq_session: MagicMock,
    ) -> None:
        """get_analyst_summary aggregates results from all 4 endpoints."""
        forecast_resp: dict[str, Any] = {
            "data": {
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
                "quarterlyForecast": {"rows": []},
            },
            "message": None,
            "status": {"rCode": 200, "bCodeMessage": None},
        }
        ratings_resp: dict[str, Any] = {
            "data": {
                "ratings": [
                    {
                        "date": "Current Quarter",
                        "strongBuy": 10,
                        "buy": 15,
                        "hold": 5,
                        "sell": 1,
                        "strongSell": 0,
                    },
                ],
            },
            "message": None,
            "status": {"rCode": 200, "bCodeMessage": None},
        }
        target_resp: dict[str, Any] = {
            "data": {
                "targetPrice": {
                    "high": "$280.00",
                    "low": "$200.00",
                    "mean": "$250.00",
                    "median": "$248.00",
                },
            },
            "message": None,
            "status": {"rCode": 200, "bCodeMessage": None},
        }
        earnings_date_resp: dict[str, Any] = {
            "data": {
                "earningsDate": "01/30/2026",
                "earningsTime": "After Market Close",
                "fiscalQuarterEnding": "Dec/2025",
                "epsForecast": "$2.35",
            },
            "message": None,
            "status": {"rCode": 200, "bCodeMessage": None},
        }
        self._setup_mock_responses(
            mock_nasdaq_session,
            mock_cache,
            [forecast_resp, ratings_resp, target_resp, earnings_date_resp],
        )

        result = nasdaq_client.get_analyst_summary("AAPL")

        assert isinstance(result, AnalystSummary)
        assert result.symbol == "AAPL"
        assert result.forecast is not None
        assert result.ratings is not None
        assert result.target_price is not None
        assert result.earnings_date is not None
        assert result.forecast.symbol == "AAPL"
        assert result.ratings.ratings[0].strong_buy == 10
        assert result.target_price.mean == "$250.00"
        assert result.earnings_date.date == "01/30/2026"

    def test_正常系_部分失敗時に残りの結果を返す(
        self,
        nasdaq_client: NasdaqClient,
        mock_cache: MagicMock,
        mock_nasdaq_session: MagicMock,
    ) -> None:
        """When one endpoint fails, the summary still contains other results."""
        mock_cache.get.return_value = None

        # First call (forecast) raises an error
        error_response = MagicMock()
        error_response.json.return_value = {
            "data": None,
            "status": {"rCode": 400, "bCodeMessage": "Not Found"},
        }

        # Remaining calls succeed
        ratings_resp: dict[str, Any] = {
            "data": {
                "ratings": [
                    {
                        "date": "Current Quarter",
                        "strongBuy": 10,
                        "buy": 15,
                        "hold": 5,
                        "sell": 1,
                        "strongSell": 0,
                    },
                ],
            },
            "message": None,
            "status": {"rCode": 200, "bCodeMessage": None},
        }
        target_resp: dict[str, Any] = {
            "data": {
                "targetPrice": {
                    "high": "$280.00",
                    "low": "$200.00",
                    "mean": "$250.00",
                    "median": "$248.00",
                },
            },
            "message": None,
            "status": {"rCode": 200, "bCodeMessage": None},
        }
        earnings_date_resp: dict[str, Any] = {
            "data": {
                "earningsDate": "01/30/2026",
                "earningsTime": "After Market Close",
                "fiscalQuarterEnding": "Dec/2025",
                "epsForecast": "$2.35",
            },
            "message": None,
            "status": {"rCode": 200, "bCodeMessage": None},
        }

        mock_responses = []
        for resp in [
            error_response,
            ratings_resp,
            target_resp,
            earnings_date_resp,
        ]:
            if isinstance(resp, MagicMock):
                mock_responses.append(resp)
            else:
                mock_resp = MagicMock()
                mock_resp.json.return_value = resp
                mock_responses.append(mock_resp)

        mock_nasdaq_session.get_with_retry.side_effect = mock_responses

        result = nasdaq_client.get_analyst_summary("AAPL")

        assert result.symbol == "AAPL"
        assert result.forecast is None  # Failed
        assert result.ratings is not None
        assert result.target_price is not None
        assert result.earnings_date is not None

    def test_異常系_空シンボルでValueError(
        self,
        nasdaq_client: NasdaqClient,
    ) -> None:
        """Empty symbol raises ValueError."""
        with pytest.raises(ValueError, match="Symbol must not be empty"):
            nasdaq_client.get_analyst_summary("")

    def test_正常系_内部で4メソッドを呼び出す(
        self,
        nasdaq_client: NasdaqClient,
        mock_cache: MagicMock,
        mock_nasdaq_session: MagicMock,
    ) -> None:
        """get_analyst_summary calls all 4 internal methods."""
        mock_cache.get.return_value = None

        # All endpoints return empty data
        empty_resp: dict[str, Any] = {
            "data": {},
            "message": None,
            "status": {"rCode": 200, "bCodeMessage": None},
        }
        mock_responses = []
        for _ in range(4):
            mock_resp = MagicMock()
            mock_resp.json.return_value = empty_resp
            mock_responses.append(mock_resp)
        mock_nasdaq_session.get_with_retry.side_effect = mock_responses

        nasdaq_client.get_analyst_summary("AAPL")

        # Should have been called 4 times (one for each sub-method)
        assert mock_nasdaq_session.get_with_retry.call_count == 4

    def test_正常系_validate_symbolが呼ばれる(
        self,
        nasdaq_client: NasdaqClient,
    ) -> None:
        """Symbol validation is performed in get_analyst_summary."""
        with pytest.raises(ValueError, match="Symbol must not be empty"):
            nasdaq_client.get_analyst_summary("   ")
