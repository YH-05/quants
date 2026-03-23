"""Tests for market.alphavantage.client module.

Tests follow the jquants/unit/test_client.py pattern:
- patch + in-memory SQLiteCache + Japanese test names
- Each public method has cache hit / cache miss tests
- _validate_symbol has valid / invalid tests
"""

from collections.abc import Generator
from typing import Any
from unittest.mock import MagicMock, patch

import pandas as pd
import pytest

from market.alphavantage.cache import (
    COMPANY_OVERVIEW_TTL,
    CRYPTO_TTL,
    ECONOMIC_INDICATOR_TTL,
    FOREX_TTL,
    FUNDAMENTALS_TTL,
    GLOBAL_QUOTE_TTL,
    TIME_SERIES_DAILY_TTL,
    TIME_SERIES_INTRADAY_TTL,
)
from market.alphavantage.client import AlphaVantageClient
from market.alphavantage.errors import AlphaVantageValidationError
from market.alphavantage.types import FetchOptions, Interval, OutputSize
from market.cache.cache import SQLiteCache, generate_cache_key

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def mock_cache() -> SQLiteCache:
    """Create an in-memory SQLiteCache for testing."""
    return SQLiteCache()


@pytest.fixture
def client(mock_cache: SQLiteCache) -> Generator[AlphaVantageClient]:
    """Create an AlphaVantageClient with mocked session."""
    with patch("market.alphavantage.client.AlphaVantageSession") as mock_session_cls:
        mock_session_instance = MagicMock()
        mock_session_cls.return_value = mock_session_instance

        c = AlphaVantageClient(cache=mock_cache)
        c._session = mock_session_instance
        yield c
        c.close()


def _make_mock_response(data: dict[str, Any]) -> MagicMock:
    """Create a mock httpx.Response that returns *data* from .json()."""
    resp = MagicMock()
    resp.status_code = 200
    resp.json.return_value = data
    return resp


# ---------------------------------------------------------------------------
# Initialization & Context Manager
# ---------------------------------------------------------------------------


class TestAlphaVantageClientInit:
    """Tests for AlphaVantageClient initialization."""

    def test_正常系_初期化(self, client: AlphaVantageClient) -> None:
        assert client._cache is not None
        assert client._session is not None

    def test_正常系_デフォルトキャッシュ(self) -> None:
        """Default cache is created when none is provided."""
        with (
            patch("market.alphavantage.client.AlphaVantageSession"),
            patch("market.alphavantage.client.get_alphavantage_cache") as mock_gc,
        ):
            mock_gc.return_value = SQLiteCache()
            c = AlphaVantageClient()
            assert c._cache is not None
            c.close()


class TestAlphaVantageClientContextManager:
    """Tests for context manager protocol."""

    def test_正常系_コンテキストマネージャ(self, mock_cache: SQLiteCache) -> None:
        with (
            patch("market.alphavantage.client.AlphaVantageSession"),
            AlphaVantageClient(cache=mock_cache) as c,
        ):
            assert isinstance(c, AlphaVantageClient)


# ---------------------------------------------------------------------------
# _validate_symbol
# ---------------------------------------------------------------------------


class TestValidateSymbol:
    """Tests for _validate_symbol."""

    def test_正常系_有効なシンボル_AAPL(self, client: AlphaVantageClient) -> None:
        client._validate_symbol("AAPL")  # should not raise

    def test_正常系_有効なシンボル_BRK_B(self, client: AlphaVantageClient) -> None:
        client._validate_symbol("BRK.B")  # should not raise

    def test_正常系_有効なシンボル_1文字(self, client: AlphaVantageClient) -> None:
        client._validate_symbol("A")  # should not raise

    def test_正常系_有効なシンボル_10文字(self, client: AlphaVantageClient) -> None:
        client._validate_symbol("ABCDEFGHIJ")  # 10 chars, should not raise

    def test_異常系_空文字列(self, client: AlphaVantageClient) -> None:
        with pytest.raises(AlphaVantageValidationError, match="must not be empty"):
            client._validate_symbol("")

    def test_異常系_空白のみ(self, client: AlphaVantageClient) -> None:
        with pytest.raises(AlphaVantageValidationError, match="must not be empty"):
            client._validate_symbol("   ")

    def test_異常系_11文字以上(self, client: AlphaVantageClient) -> None:
        with pytest.raises(AlphaVantageValidationError, match="1-10 characters"):
            client._validate_symbol("ABCDEFGHIJK")  # 11 chars

    def test_異常系_特殊文字(self, client: AlphaVantageClient) -> None:
        with pytest.raises(AlphaVantageValidationError, match="alphanumeric"):
            client._validate_symbol("AA$L")


# ---------------------------------------------------------------------------
# Time Series Methods
# ---------------------------------------------------------------------------


class TestGetDaily:
    """Tests for get_daily method."""

    def test_正常系_キャッシュミス(self, client: AlphaVantageClient) -> None:
        ts_data = {
            "Meta Data": {"1. Information": "Daily Prices"},
            "Time Series (Daily)": {
                "2024-01-02": {
                    "1. open": "185.0",
                    "2. high": "186.0",
                    "3. low": "184.0",
                    "4. close": "185.5",
                    "5. volume": "50000000",
                },
            },
        }
        client._session.get_with_retry.return_value = _make_mock_response(ts_data)

        df = client.get_daily("AAPL")
        assert isinstance(df, pd.DataFrame)
        assert len(df) == 1
        assert "open" in df.columns
        client._session.get_with_retry.assert_called_once()

    def test_正常系_キャッシュヒット(
        self, client: AlphaVantageClient, mock_cache: SQLiteCache
    ) -> None:
        cached_df = pd.DataFrame(
            [{"date": "2024-01-02", "open": 185.0, "close": 185.5}]
        )
        key = generate_cache_key(symbol="AAPL", source="av_daily")
        mock_cache.set(key, cached_df, ttl=TIME_SERIES_DAILY_TTL)

        df = client.get_daily("AAPL")
        assert isinstance(df, pd.DataFrame)
        assert len(df) == 1
        client._session.get_with_retry.assert_not_called()

    def test_正常系_キャッシュバイパス(self, client: AlphaVantageClient) -> None:
        ts_data = {
            "Meta Data": {},
            "Time Series (Daily)": {},
        }
        client._session.get_with_retry.return_value = _make_mock_response(ts_data)

        df = client.get_daily("AAPL", options=FetchOptions(force_refresh=True))
        assert isinstance(df, pd.DataFrame)
        client._session.get_with_retry.assert_called_once()

    def test_正常系_outputsize指定(self, client: AlphaVantageClient) -> None:
        ts_data = {
            "Meta Data": {},
            "Time Series (Daily)": {},
        }
        client._session.get_with_retry.return_value = _make_mock_response(ts_data)

        client.get_daily("AAPL", outputsize=OutputSize.FULL)
        call_args = client._session.get_with_retry.call_args
        params = (
            call_args[1].get("params") or call_args[0][1]
            if len(call_args[0]) > 1
            else call_args[1].get("params", {})
        )
        assert params.get("outputsize") == "full"

    def test_異常系_不正なシンボル(self, client: AlphaVantageClient) -> None:
        with pytest.raises(AlphaVantageValidationError):
            client.get_daily("")


class TestGetWeekly:
    """Tests for get_weekly method."""

    def test_正常系_キャッシュミス(self, client: AlphaVantageClient) -> None:
        ts_data = {
            "Meta Data": {},
            "Weekly Time Series": {
                "2024-01-05": {
                    "1. open": "185.0",
                    "2. high": "186.0",
                    "3. low": "184.0",
                    "4. close": "185.5",
                    "5. volume": "250000000",
                },
            },
        }
        client._session.get_with_retry.return_value = _make_mock_response(ts_data)

        df = client.get_weekly("AAPL")
        assert isinstance(df, pd.DataFrame)
        assert len(df) == 1

    def test_正常系_キャッシュヒット(
        self, client: AlphaVantageClient, mock_cache: SQLiteCache
    ) -> None:
        cached_df = pd.DataFrame([{"date": "2024-01-05", "open": 185.0}])
        key = generate_cache_key(symbol="AAPL", source="av_weekly")
        mock_cache.set(key, cached_df, ttl=TIME_SERIES_DAILY_TTL)

        df = client.get_weekly("AAPL")
        assert len(df) == 1
        client._session.get_with_retry.assert_not_called()


class TestGetMonthly:
    """Tests for get_monthly method."""

    def test_正常系_キャッシュミス(self, client: AlphaVantageClient) -> None:
        ts_data = {
            "Meta Data": {},
            "Monthly Time Series": {
                "2024-01-31": {
                    "1. open": "185.0",
                    "2. high": "196.0",
                    "3. low": "180.0",
                    "4. close": "190.5",
                    "5. volume": "1000000000",
                },
            },
        }
        client._session.get_with_retry.return_value = _make_mock_response(ts_data)

        df = client.get_monthly("AAPL")
        assert isinstance(df, pd.DataFrame)
        assert len(df) == 1

    def test_正常系_キャッシュヒット(
        self, client: AlphaVantageClient, mock_cache: SQLiteCache
    ) -> None:
        cached_df = pd.DataFrame([{"date": "2024-01-31", "open": 185.0}])
        key = generate_cache_key(symbol="AAPL", source="av_monthly")
        mock_cache.set(key, cached_df, ttl=TIME_SERIES_DAILY_TTL)

        df = client.get_monthly("AAPL")
        assert len(df) == 1
        client._session.get_with_retry.assert_not_called()


class TestGetIntraday:
    """Tests for get_intraday method."""

    def test_正常系_キャッシュミス(self, client: AlphaVantageClient) -> None:
        ts_data = {
            "Meta Data": {},
            "Time Series (5min)": {
                "2024-01-02 16:00:00": {
                    "1. open": "185.0",
                    "2. high": "185.5",
                    "3. low": "184.5",
                    "4. close": "185.2",
                    "5. volume": "1000000",
                },
            },
        }
        client._session.get_with_retry.return_value = _make_mock_response(ts_data)

        df = client.get_intraday("AAPL", interval=Interval.FIVE_MIN)
        assert isinstance(df, pd.DataFrame)
        assert len(df) == 1

    def test_正常系_キャッシュヒット(
        self, client: AlphaVantageClient, mock_cache: SQLiteCache
    ) -> None:
        cached_df = pd.DataFrame([{"date": "2024-01-02 16:00:00", "open": 185.0}])
        key = generate_cache_key(symbol="AAPL", source="av_intraday_5min")
        mock_cache.set(key, cached_df, ttl=TIME_SERIES_INTRADAY_TTL)

        df = client.get_intraday("AAPL", interval=Interval.FIVE_MIN)
        assert len(df) == 1
        client._session.get_with_retry.assert_not_called()


# ---------------------------------------------------------------------------
# Real-time Method
# ---------------------------------------------------------------------------


class TestGetGlobalQuote:
    """Tests for get_global_quote method."""

    def test_正常系_キャッシュミス(self, client: AlphaVantageClient) -> None:
        quote_data = {
            "Global Quote": {
                "01. symbol": "AAPL",
                "02. open": "185.0",
                "03. high": "186.0",
                "04. low": "184.0",
                "05. price": "185.5",
                "06. volume": "50000000",
                "07. latest trading day": "2024-01-02",
                "08. previous close": "184.0",
                "09. change": "1.50",
                "10. change percent": "0.8152%",
            }
        }
        client._session.get_with_retry.return_value = _make_mock_response(quote_data)

        result = client.get_global_quote("AAPL")
        assert isinstance(result, dict)
        assert "symbol" in result or "price" in result

    def test_正常系_キャッシュヒット(
        self, client: AlphaVantageClient, mock_cache: SQLiteCache
    ) -> None:
        cached_data = {"symbol": "AAPL", "price": 185.5}
        key = generate_cache_key(symbol="AAPL", source="av_global_quote")
        mock_cache.set(key, cached_data, ttl=GLOBAL_QUOTE_TTL)

        result = client.get_global_quote("AAPL")
        assert result["price"] == 185.5
        client._session.get_with_retry.assert_not_called()


# ---------------------------------------------------------------------------
# Fundamentals Methods
# ---------------------------------------------------------------------------


class TestGetCompanyOverview:
    """Tests for get_company_overview method."""

    def test_正常系_キャッシュミス(self, client: AlphaVantageClient) -> None:
        overview_data = {
            "Symbol": "AAPL",
            "Name": "Apple Inc",
            "MarketCapitalization": "3000000000000",
            "PERatio": "30.5",
        }
        client._session.get_with_retry.return_value = _make_mock_response(overview_data)

        result = client.get_company_overview("AAPL")
        assert isinstance(result, dict)
        assert result["Symbol"] == "AAPL"

    def test_正常系_キャッシュヒット(
        self, client: AlphaVantageClient, mock_cache: SQLiteCache
    ) -> None:
        cached_data = {"Symbol": "AAPL", "Name": "Apple Inc"}
        key = generate_cache_key(symbol="AAPL", source="av_overview")
        mock_cache.set(key, cached_data, ttl=COMPANY_OVERVIEW_TTL)

        result = client.get_company_overview("AAPL")
        assert result["Symbol"] == "AAPL"
        client._session.get_with_retry.assert_not_called()


class TestGetIncomeStatement:
    """Tests for get_income_statement method."""

    def test_正常系_キャッシュミス(self, client: AlphaVantageClient) -> None:
        statement_data = {
            "symbol": "AAPL",
            "annualReports": [
                {
                    "fiscalDateEnding": "2023-09-30",
                    "reportedCurrency": "USD",
                    "totalRevenue": "383285000000",
                }
            ],
            "quarterlyReports": [],
        }
        client._session.get_with_retry.return_value = _make_mock_response(
            statement_data
        )

        df = client.get_income_statement("AAPL")
        assert isinstance(df, pd.DataFrame)
        assert len(df) == 1

    def test_正常系_キャッシュヒット(
        self, client: AlphaVantageClient, mock_cache: SQLiteCache
    ) -> None:
        cached_df = pd.DataFrame(
            [{"fiscalDateEnding": "2023-09-30", "totalRevenue": 383285000000.0}]
        )
        key = generate_cache_key(symbol="AAPL", source="av_income_statement")
        mock_cache.set(key, cached_df, ttl=FUNDAMENTALS_TTL)

        df = client.get_income_statement("AAPL")
        assert len(df) == 1
        client._session.get_with_retry.assert_not_called()


class TestGetBalanceSheet:
    """Tests for get_balance_sheet method."""

    def test_正常系_キャッシュミス(self, client: AlphaVantageClient) -> None:
        bs_data = {
            "symbol": "AAPL",
            "annualReports": [
                {
                    "fiscalDateEnding": "2023-09-30",
                    "reportedCurrency": "USD",
                    "totalAssets": "352583000000",
                }
            ],
            "quarterlyReports": [],
        }
        client._session.get_with_retry.return_value = _make_mock_response(bs_data)

        df = client.get_balance_sheet("AAPL")
        assert isinstance(df, pd.DataFrame)
        assert len(df) == 1

    def test_正常系_キャッシュヒット(
        self, client: AlphaVantageClient, mock_cache: SQLiteCache
    ) -> None:
        cached_df = pd.DataFrame(
            [{"fiscalDateEnding": "2023-09-30", "totalAssets": 352583000000.0}]
        )
        key = generate_cache_key(symbol="AAPL", source="av_balance_sheet")
        mock_cache.set(key, cached_df, ttl=FUNDAMENTALS_TTL)

        df = client.get_balance_sheet("AAPL")
        assert len(df) == 1
        client._session.get_with_retry.assert_not_called()


class TestGetCashFlow:
    """Tests for get_cash_flow method."""

    def test_正常系_キャッシュミス(self, client: AlphaVantageClient) -> None:
        cf_data = {
            "symbol": "AAPL",
            "annualReports": [
                {
                    "fiscalDateEnding": "2023-09-30",
                    "reportedCurrency": "USD",
                    "operatingCashflow": "110543000000",
                }
            ],
            "quarterlyReports": [],
        }
        client._session.get_with_retry.return_value = _make_mock_response(cf_data)

        df = client.get_cash_flow("AAPL")
        assert isinstance(df, pd.DataFrame)
        assert len(df) == 1

    def test_正常系_キャッシュヒット(
        self, client: AlphaVantageClient, mock_cache: SQLiteCache
    ) -> None:
        cached_df = pd.DataFrame(
            [{"fiscalDateEnding": "2023-09-30", "operatingCashflow": 110543000000.0}]
        )
        key = generate_cache_key(symbol="AAPL", source="av_cash_flow")
        mock_cache.set(key, cached_df, ttl=FUNDAMENTALS_TTL)

        df = client.get_cash_flow("AAPL")
        assert len(df) == 1
        client._session.get_with_retry.assert_not_called()


class TestGetEarnings:
    """Tests for get_earnings method."""

    def test_正常系_キャッシュミス(self, client: AlphaVantageClient) -> None:
        earnings_data = {
            "symbol": "AAPL",
            "annualEarnings": [
                {"fiscalDateEnding": "2023-09-30", "reportedEPS": "6.13"}
            ],
            "quarterlyEarnings": [
                {
                    "fiscalDateEnding": "2023-09-30",
                    "reportedDate": "2023-11-02",
                    "reportedEPS": "1.46",
                    "estimatedEPS": "1.39",
                }
            ],
        }
        client._session.get_with_retry.return_value = _make_mock_response(earnings_data)

        annual, quarterly = client.get_earnings("AAPL")
        assert isinstance(annual, pd.DataFrame)
        assert isinstance(quarterly, pd.DataFrame)
        assert len(annual) == 1
        assert len(quarterly) == 1

    def test_正常系_キャッシュヒット(
        self, client: AlphaVantageClient, mock_cache: SQLiteCache
    ) -> None:
        cached_data = (
            pd.DataFrame([{"fiscalDateEnding": "2023-09-30", "reportedEPS": 6.13}]),
            pd.DataFrame([{"fiscalDateEnding": "2023-09-30", "reportedEPS": 1.46}]),
        )
        key = generate_cache_key(symbol="AAPL", source="av_earnings")
        mock_cache.set(key, cached_data, ttl=FUNDAMENTALS_TTL)

        annual, quarterly = client.get_earnings("AAPL")
        assert len(annual) == 1
        assert len(quarterly) == 1
        client._session.get_with_retry.assert_not_called()


# ---------------------------------------------------------------------------
# Forex Methods
# ---------------------------------------------------------------------------


class TestGetExchangeRate:
    """Tests for get_exchange_rate method."""

    def test_正常系_キャッシュミス(self, client: AlphaVantageClient) -> None:
        fx_data = {
            "Realtime Currency Exchange Rate": {
                "1. From_Currency Code": "USD",
                "2. From_Currency Name": "United States Dollar",
                "3. To_Currency Code": "JPY",
                "4. To_Currency Name": "Japanese Yen",
                "5. Exchange Rate": "148.5000",
                "6. Last Refreshed": "2024-01-02 16:00:00",
                "7. Time Zone": "UTC",
                "8. Bid Price": "148.4900",
                "9. Ask Price": "148.5100",
            }
        }
        client._session.get_with_retry.return_value = _make_mock_response(fx_data)

        result = client.get_exchange_rate("USD", "JPY")
        assert isinstance(result, dict)

    def test_正常系_キャッシュヒット(
        self, client: AlphaVantageClient, mock_cache: SQLiteCache
    ) -> None:
        cached_data = {"Exchange Rate": 148.5}
        key = generate_cache_key(symbol="USD_JPY", source="av_exchange_rate")
        mock_cache.set(key, cached_data, ttl=FOREX_TTL)

        result = client.get_exchange_rate("USD", "JPY")
        assert result["Exchange Rate"] == 148.5
        client._session.get_with_retry.assert_not_called()


class TestGetFxDaily:
    """Tests for get_fx_daily method."""

    def test_正常系_キャッシュミス(self, client: AlphaVantageClient) -> None:
        fx_data = {
            "Meta Data": {},
            "Time Series FX (Daily)": {
                "2024-01-02": {
                    "1. open": "148.0",
                    "2. high": "149.0",
                    "3. low": "147.5",
                    "4. close": "148.5",
                },
            },
        }
        client._session.get_with_retry.return_value = _make_mock_response(fx_data)

        df = client.get_fx_daily("USD", "JPY")
        assert isinstance(df, pd.DataFrame)
        assert len(df) == 1

    def test_正常系_キャッシュヒット(
        self, client: AlphaVantageClient, mock_cache: SQLiteCache
    ) -> None:
        cached_df = pd.DataFrame([{"date": "2024-01-02", "open": 148.0}])
        key = generate_cache_key(symbol="USD_JPY", source="av_fx_daily")
        mock_cache.set(key, cached_df, ttl=FOREX_TTL)

        df = client.get_fx_daily("USD", "JPY")
        assert len(df) == 1
        client._session.get_with_retry.assert_not_called()


# ---------------------------------------------------------------------------
# Cryptocurrency Method
# ---------------------------------------------------------------------------


class TestGetCryptoDaily:
    """Tests for get_crypto_daily method."""

    def test_正常系_キャッシュミス(self, client: AlphaVantageClient) -> None:
        crypto_data = {
            "Meta Data": {},
            "Time Series (Digital Currency Daily)": {
                "2024-01-02": {
                    "1. open": "42000.00",
                    "2. high": "43000.00",
                    "3. low": "41500.00",
                    "4. close": "42500.00",
                    "5. volume": "15000",
                },
            },
        }
        client._session.get_with_retry.return_value = _make_mock_response(crypto_data)

        df = client.get_crypto_daily("BTC", market="USD")
        assert isinstance(df, pd.DataFrame)
        assert len(df) == 1

    def test_正常系_キャッシュヒット(
        self, client: AlphaVantageClient, mock_cache: SQLiteCache
    ) -> None:
        cached_df = pd.DataFrame([{"date": "2024-01-02", "open": 42000.0}])
        key = generate_cache_key(symbol="BTC_USD", source="av_crypto_daily")
        mock_cache.set(key, cached_df, ttl=CRYPTO_TTL)

        df = client.get_crypto_daily("BTC", market="USD")
        assert len(df) == 1
        client._session.get_with_retry.assert_not_called()


# ---------------------------------------------------------------------------
# Economic Indicator Methods
# ---------------------------------------------------------------------------


class TestGetRealGdp:
    """Tests for get_real_gdp method."""

    def test_正常系_キャッシュミス(self, client: AlphaVantageClient) -> None:
        gdp_data = {
            "name": "Real Gross Domestic Product",
            "data": [{"date": "2023-10-01", "value": "27956.998"}],
        }
        client._session.get_with_retry.return_value = _make_mock_response(gdp_data)

        df = client.get_real_gdp()
        assert isinstance(df, pd.DataFrame)
        assert len(df) == 1

    def test_正常系_キャッシュヒット(
        self, client: AlphaVantageClient, mock_cache: SQLiteCache
    ) -> None:
        cached_df = pd.DataFrame([{"date": "2023-10-01", "value": 27956.998}])
        key = generate_cache_key(symbol="REAL_GDP", source="av_economic")
        mock_cache.set(key, cached_df, ttl=ECONOMIC_INDICATOR_TTL)

        df = client.get_real_gdp()
        assert len(df) == 1
        client._session.get_with_retry.assert_not_called()


class TestGetCpi:
    """Tests for get_cpi method."""

    def test_正常系_キャッシュミス(self, client: AlphaVantageClient) -> None:
        cpi_data = {
            "name": "Consumer Price Index",
            "data": [{"date": "2023-12-01", "value": "306.746"}],
        }
        client._session.get_with_retry.return_value = _make_mock_response(cpi_data)

        df = client.get_cpi()
        assert isinstance(df, pd.DataFrame)
        assert len(df) == 1

    def test_正常系_キャッシュヒット(
        self, client: AlphaVantageClient, mock_cache: SQLiteCache
    ) -> None:
        cached_df = pd.DataFrame([{"date": "2023-12-01", "value": 306.746}])
        key = generate_cache_key(symbol="CPI", source="av_economic")
        mock_cache.set(key, cached_df, ttl=ECONOMIC_INDICATOR_TTL)

        df = client.get_cpi()
        assert len(df) == 1
        client._session.get_with_retry.assert_not_called()


class TestGetInflation:
    """Tests for get_inflation method."""

    def test_正常系_キャッシュミス(self, client: AlphaVantageClient) -> None:
        inflation_data = {
            "name": "Inflation - US Consumer Prices",
            "data": [{"date": "2023-01-01", "value": "6.04"}],
        }
        client._session.get_with_retry.return_value = _make_mock_response(
            inflation_data
        )

        df = client.get_inflation()
        assert isinstance(df, pd.DataFrame)
        assert len(df) == 1

    def test_正常系_キャッシュヒット(
        self, client: AlphaVantageClient, mock_cache: SQLiteCache
    ) -> None:
        cached_df = pd.DataFrame([{"date": "2023-01-01", "value": 6.04}])
        key = generate_cache_key(symbol="INFLATION", source="av_economic")
        mock_cache.set(key, cached_df, ttl=ECONOMIC_INDICATOR_TTL)

        df = client.get_inflation()
        assert len(df) == 1
        client._session.get_with_retry.assert_not_called()


class TestGetUnemployment:
    """Tests for get_unemployment method."""

    def test_正常系_キャッシュミス(self, client: AlphaVantageClient) -> None:
        unemp_data = {
            "name": "Unemployment Rate",
            "data": [{"date": "2023-12-01", "value": "3.7"}],
        }
        client._session.get_with_retry.return_value = _make_mock_response(unemp_data)

        df = client.get_unemployment()
        assert isinstance(df, pd.DataFrame)
        assert len(df) == 1

    def test_正常系_キャッシュヒット(
        self, client: AlphaVantageClient, mock_cache: SQLiteCache
    ) -> None:
        cached_df = pd.DataFrame([{"date": "2023-12-01", "value": 3.7}])
        key = generate_cache_key(symbol="UNEMPLOYMENT", source="av_economic")
        mock_cache.set(key, cached_df, ttl=ECONOMIC_INDICATOR_TTL)

        df = client.get_unemployment()
        assert len(df) == 1
        client._session.get_with_retry.assert_not_called()


class TestGetTreasuryYield:
    """Tests for get_treasury_yield method."""

    def test_正常系_キャッシュミス(self, client: AlphaVantageClient) -> None:
        yield_data = {
            "name": "Treasury Yield",
            "data": [{"date": "2024-01-02", "value": "3.95"}],
        }
        client._session.get_with_retry.return_value = _make_mock_response(yield_data)

        df = client.get_treasury_yield()
        assert isinstance(df, pd.DataFrame)
        assert len(df) == 1

    def test_正常系_キャッシュヒット(
        self, client: AlphaVantageClient, mock_cache: SQLiteCache
    ) -> None:
        cached_df = pd.DataFrame([{"date": "2024-01-02", "value": 3.95}])
        key = generate_cache_key(symbol="TREASURY_YIELD", source="av_economic")
        mock_cache.set(key, cached_df, ttl=ECONOMIC_INDICATOR_TTL)

        df = client.get_treasury_yield()
        assert len(df) == 1
        client._session.get_with_retry.assert_not_called()


class TestGetFederalFundsRate:
    """Tests for get_federal_funds_rate method."""

    def test_正常系_キャッシュミス(self, client: AlphaVantageClient) -> None:
        ffr_data = {
            "name": "Federal Funds Rate",
            "data": [{"date": "2024-01-02", "value": "5.33"}],
        }
        client._session.get_with_retry.return_value = _make_mock_response(ffr_data)

        df = client.get_federal_funds_rate()
        assert isinstance(df, pd.DataFrame)
        assert len(df) == 1

    def test_正常系_キャッシュヒット(
        self, client: AlphaVantageClient, mock_cache: SQLiteCache
    ) -> None:
        cached_df = pd.DataFrame([{"date": "2024-01-02", "value": 5.33}])
        key = generate_cache_key(symbol="FEDERAL_FUNDS_RATE", source="av_economic")
        mock_cache.set(key, cached_df, ttl=ECONOMIC_INDICATOR_TTL)

        df = client.get_federal_funds_rate()
        assert len(df) == 1
        client._session.get_with_retry.assert_not_called()


# ---------------------------------------------------------------------------
# _get_cached_or_fetch (internal DRY helper)
# ---------------------------------------------------------------------------


class TestGetCachedOrFetch:
    """Tests for _get_cached_or_fetch internal method."""

    def test_正常系_キャッシュミスでパーサー呼び出し(
        self, client: AlphaVantageClient
    ) -> None:
        raw_data = {"key": "value"}
        client._session.get_with_retry.return_value = _make_mock_response(raw_data)

        def parser(d: dict[str, Any]) -> str:
            return "parsed"

        result = client._get_cached_or_fetch(
            cache_key="test_key",
            params={"function": "TEST"},
            parser=parser,
            ttl=3600,
        )
        assert result == "parsed"

    def test_正常系_キャッシュヒットでAPI未呼び出し(
        self, client: AlphaVantageClient, mock_cache: SQLiteCache
    ) -> None:
        mock_cache.set("test_key", "cached_value", ttl=3600)

        def parser(d: dict[str, Any]) -> str:
            return "should_not_be_called"

        result = client._get_cached_or_fetch(
            cache_key="test_key",
            params={"function": "TEST"},
            parser=parser,
            ttl=3600,
        )
        assert result == "cached_value"
        client._session.get_with_retry.assert_not_called()
