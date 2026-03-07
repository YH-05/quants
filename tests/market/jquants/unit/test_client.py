"""Tests for market.jquants.client module."""

from collections.abc import Generator
from unittest.mock import MagicMock, patch

import httpx
import pandas as pd
import pytest

from market.cache.cache import SQLiteCache
from market.jquants.client import JQuantsClient
from market.jquants.errors import JQuantsValidationError
from market.jquants.types import FetchOptions, JQuantsConfig


@pytest.fixture
def mock_cache() -> SQLiteCache:
    """Create an in-memory SQLiteCache for testing."""
    return SQLiteCache()


@pytest.fixture
def mock_session() -> MagicMock:
    """Create a mock JQuantsSession."""
    return MagicMock()


@pytest.fixture
def client(
    tmp_path: object,
    mock_cache: SQLiteCache,
) -> Generator[JQuantsClient]:
    """Create a JQuantsClient with mocked dependencies."""
    config = JQuantsConfig(
        token_file_path="/tmp/nonexistent/token.json",
    )
    with patch("market.jquants.client.JQuantsSession") as mock_session_cls:
        mock_session_instance = MagicMock()
        mock_session_cls.return_value = mock_session_instance

        client = JQuantsClient(config=config, cache=mock_cache)
        client._session = mock_session_instance
        yield client
        client.close()


class TestJQuantsClientInit:
    """Tests for JQuantsClient initialization."""

    def test_正常系_初期化(self, client: JQuantsClient) -> None:
        assert client._cache is not None
        assert client._session is not None


class TestJQuantsClientContextManager:
    """Tests for context manager."""

    def test_正常系_コンテキストマネージャ(self, mock_cache: SQLiteCache) -> None:
        config = JQuantsConfig(
            token_file_path="/tmp/nonexistent/token.json",
        )
        with (
            patch("market.jquants.client.JQuantsSession"),
            JQuantsClient(config=config, cache=mock_cache) as c,
        ):
            assert isinstance(c, JQuantsClient)


class TestJQuantsClientValidation:
    """Tests for stock code validation."""

    def test_異常系_空の銘柄コード(self, client: JQuantsClient) -> None:
        with pytest.raises(JQuantsValidationError, match="must not be empty"):
            client._validate_code("")

    def test_異常系_数字以外の銘柄コード(self, client: JQuantsClient) -> None:
        with pytest.raises(JQuantsValidationError, match="must be 4-5 digits"):
            client._validate_code("ABC")

    def test_異常系_3桁の銘柄コード(self, client: JQuantsClient) -> None:
        with pytest.raises(JQuantsValidationError, match="must be 4-5 digits"):
            client._validate_code("123")

    def test_異常系_6桁の銘柄コード(self, client: JQuantsClient) -> None:
        with pytest.raises(JQuantsValidationError, match="must be 4-5 digits"):
            client._validate_code("123456")

    def test_正常系_4桁の銘柄コード(self, client: JQuantsClient) -> None:
        # Should not raise
        client._validate_code("7203")

    def test_正常系_5桁の銘柄コード(self, client: JQuantsClient) -> None:
        # Should not raise
        client._validate_code("72030")


class TestGetListedInfo:
    """Tests for get_listed_info method."""

    def test_正常系_全銘柄取得(self, client: JQuantsClient) -> None:
        mock_response = MagicMock(spec=httpx.Response)
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "info": [
                {"Code": "7203", "CompanyName": "トヨタ自動車"},
                {"Code": "6758", "CompanyName": "ソニーグループ"},
            ]
        }
        client._session.get_with_retry.return_value = mock_response

        df = client.get_listed_info()
        assert isinstance(df, pd.DataFrame)
        assert len(df) == 2
        assert "CompanyName" in df.columns

    def test_正常系_特定銘柄取得(self, client: JQuantsClient) -> None:
        mock_response = MagicMock(spec=httpx.Response)
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "info": [{"Code": "7203", "CompanyName": "トヨタ自動車"}]
        }
        client._session.get_with_retry.return_value = mock_response

        df = client.get_listed_info(code="7203")
        assert isinstance(df, pd.DataFrame)
        assert len(df) == 1

    def test_正常系_キャッシュヒット(
        self, client: JQuantsClient, mock_cache: SQLiteCache
    ) -> None:
        cached_df = pd.DataFrame([{"Code": "7203", "CompanyName": "トヨタ自動車"}])
        # Pre-populate cache
        from market.cache.cache import generate_cache_key

        key = generate_cache_key(symbol="ALL", source="jquants_listed")
        mock_cache.set(key, cached_df, ttl=3600)

        df = client.get_listed_info()
        assert isinstance(df, pd.DataFrame)
        assert len(df) == 1
        # Should NOT have called the API
        client._session.get_with_retry.assert_not_called()

    def test_正常系_キャッシュバイパス(self, client: JQuantsClient) -> None:
        mock_response = MagicMock(spec=httpx.Response)
        mock_response.status_code = 200
        mock_response.json.return_value = {"info": []}
        client._session.get_with_retry.return_value = mock_response

        df = client.get_listed_info(options=FetchOptions(force_refresh=True))
        assert isinstance(df, pd.DataFrame)
        client._session.get_with_retry.assert_called_once()

    def test_異常系_不正な銘柄コード(self, client: JQuantsClient) -> None:
        with pytest.raises(JQuantsValidationError):
            client.get_listed_info(code="ABC")


class TestGetDailyQuotes:
    """Tests for get_daily_quotes method."""

    def test_正常系_日足データ取得(self, client: JQuantsClient) -> None:
        mock_response = MagicMock(spec=httpx.Response)
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "daily_quotes": [
                {
                    "Date": "2024-01-04",
                    "Code": "7203",
                    "Open": 2600.0,
                    "High": 2650.0,
                    "Low": 2590.0,
                    "Close": 2640.0,
                    "Volume": 5000000,
                },
            ]
        }
        client._session.get_with_retry.return_value = mock_response

        df = client.get_daily_quotes("7203", "20240104", "20240131")
        assert isinstance(df, pd.DataFrame)
        assert len(df) == 1
        assert "Open" in df.columns

    def test_正常系_ハイフン日付正規化(self, client: JQuantsClient) -> None:
        mock_response = MagicMock(spec=httpx.Response)
        mock_response.status_code = 200
        mock_response.json.return_value = {"daily_quotes": []}
        client._session.get_with_retry.return_value = mock_response

        df = client.get_daily_quotes("7203", "2024-01-04", "2024-01-31")
        assert isinstance(df, pd.DataFrame)
        # Verify params were normalized
        call_args = client._session.get_with_retry.call_args
        url = call_args[0][0]
        assert "from" in str(call_args) or url.endswith("daily_quotes")

    def test_異常系_不正な銘柄コード(self, client: JQuantsClient) -> None:
        with pytest.raises(JQuantsValidationError):
            client.get_daily_quotes("ABC", "20240104", "20240131")


class TestGetFinancialStatements:
    """Tests for get_financial_statements method."""

    def test_正常系_財務データ取得(self, client: JQuantsClient) -> None:
        mock_response = MagicMock(spec=httpx.Response)
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "statements": [
                {
                    "DisclosedDate": "2024-02-01",
                    "Code": "7203",
                    "NetSales": "30000000",
                },
            ]
        }
        client._session.get_with_retry.return_value = mock_response

        df = client.get_financial_statements("7203")
        assert isinstance(df, pd.DataFrame)
        assert len(df) == 1

    def test_異常系_不正な銘柄コード(self, client: JQuantsClient) -> None:
        with pytest.raises(JQuantsValidationError):
            client.get_financial_statements("ABC")


class TestGetTradingCalendar:
    """Tests for get_trading_calendar method."""

    def test_正常系_取引カレンダー取得(self, client: JQuantsClient) -> None:
        mock_response = MagicMock(spec=httpx.Response)
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "trading_calendar": [
                {"Date": "2024-01-04", "HolidayDivision": "1"},
                {"Date": "2024-01-05", "HolidayDivision": "1"},
            ]
        }
        client._session.get_with_retry.return_value = mock_response

        df = client.get_trading_calendar()
        assert isinstance(df, pd.DataFrame)
        assert len(df) == 2

    def test_正常系_キャッシュヒット(
        self, client: JQuantsClient, mock_cache: SQLiteCache
    ) -> None:
        cached_df = pd.DataFrame([{"Date": "2024-01-04", "HolidayDivision": "1"}])
        from market.cache.cache import generate_cache_key

        key = generate_cache_key(symbol="TRADING_CALENDAR", source="jquants_calendar")
        mock_cache.set(key, cached_df, ttl=3600)

        df = client.get_trading_calendar()
        assert isinstance(df, pd.DataFrame)
        assert len(df) == 1
        client._session.get_with_retry.assert_not_called()


class TestGetDailyQuotesCache:
    """Tests for daily quotes caching."""

    def test_正常系_キャッシュヒット(
        self, client: JQuantsClient, mock_cache: SQLiteCache
    ) -> None:
        cached_df = pd.DataFrame(
            [
                {
                    "Date": "2024-01-04",
                    "Code": "7203",
                    "Open": 2600.0,
                    "Close": 2640.0,
                }
            ]
        )
        from market.cache.cache import generate_cache_key

        key = generate_cache_key(
            symbol="7203",
            start_date="20240104",
            end_date="20240131",
            source="jquants_daily",
        )
        mock_cache.set(key, cached_df, ttl=3600)

        df = client.get_daily_quotes("7203", "20240104", "20240131")
        assert isinstance(df, pd.DataFrame)
        assert len(df) == 1
        client._session.get_with_retry.assert_not_called()
