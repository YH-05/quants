"""Tests for market.eodhd.client module."""

import pytest

from market.eodhd.client import EodhdClient
from market.eodhd.types import EodhdConfig


class TestEodhdClientInit:
    """Tests for EodhdClient initialization."""

    def test_正常系_デフォルト初期化(self) -> None:
        client = EodhdClient()
        assert client._config is not None
        assert client._config.api_key == ""

    def test_正常系_カスタムconfig(self) -> None:
        config = EodhdConfig(api_key="demo")
        client = EodhdClient(config=config)
        assert client._config.api_key == "demo"


class TestEodhdClientContextManager:
    """Tests for context manager."""

    def test_正常系_コンテキストマネージャ(self) -> None:
        with EodhdClient() as client:
            assert isinstance(client, EodhdClient)

    def test_正常系_close呼び出し(self) -> None:
        client = EodhdClient()
        # close() should not raise
        client.close()


class TestEodhdClientGetEodData:
    """Tests for get_eod_data method."""

    def test_正常系_NotImplementedErrorをraise(self) -> None:
        client = EodhdClient()
        with pytest.raises(NotImplementedError, match="get_eod_data"):
            client.get_eod_data("AAPL.US")

    def test_正常系_日付指定でもNotImplementedError(self) -> None:
        client = EodhdClient()
        with pytest.raises(NotImplementedError):
            client.get_eod_data("AAPL.US", from_date="2024-01-01", to_date="2024-12-31")


class TestEodhdClientGetFundamentals:
    """Tests for get_fundamentals method."""

    def test_正常系_NotImplementedErrorをraise(self) -> None:
        client = EodhdClient()
        with pytest.raises(NotImplementedError, match="get_fundamentals"):
            client.get_fundamentals("AAPL.US")


class TestEodhdClientGetExchangeSymbols:
    """Tests for get_exchange_symbols method."""

    def test_正常系_NotImplementedErrorをraise(self) -> None:
        client = EodhdClient()
        with pytest.raises(NotImplementedError, match="get_exchange_symbols"):
            client.get_exchange_symbols("US")


class TestEodhdClientGetExchangeDetails:
    """Tests for get_exchange_details method."""

    def test_正常系_NotImplementedErrorをraise(self) -> None:
        client = EodhdClient()
        with pytest.raises(NotImplementedError, match="get_exchange_details"):
            client.get_exchange_details("US")


class TestEodhdClientGetDividends:
    """Tests for get_dividends method."""

    def test_正常系_NotImplementedErrorをraise(self) -> None:
        client = EodhdClient()
        with pytest.raises(NotImplementedError, match="get_dividends"):
            client.get_dividends("AAPL.US")

    def test_正常系_日付指定でもNotImplementedError(self) -> None:
        client = EodhdClient()
        with pytest.raises(NotImplementedError):
            client.get_dividends(
                "AAPL.US", from_date="2024-01-01", to_date="2024-12-31"
            )


class TestEodhdClientGetSplits:
    """Tests for get_splits method."""

    def test_正常系_NotImplementedErrorをraise(self) -> None:
        client = EodhdClient()
        with pytest.raises(NotImplementedError, match="get_splits"):
            client.get_splits("AAPL.US")

    def test_正常系_日付指定でもNotImplementedError(self) -> None:
        client = EodhdClient()
        with pytest.raises(NotImplementedError):
            client.get_splits(
                "AAPL.US", from_date="2024-01-01", to_date="2024-12-31"
            )


class TestEodhdClientGetIntradayData:
    """Tests for get_intraday_data method."""

    def test_正常系_NotImplementedErrorをraise(self) -> None:
        client = EodhdClient()
        with pytest.raises(NotImplementedError, match="get_intraday_data"):
            client.get_intraday_data("AAPL.US")

    def test_正常系_パラメータ指定でもNotImplementedError(self) -> None:
        client = EodhdClient()
        with pytest.raises(NotImplementedError):
            client.get_intraday_data(
                "AAPL.US",
                interval="1m",
                from_timestamp=1700000000,
                to_timestamp=1700100000,
            )


class TestEodhdClientAllMethods:
    """Tests verifying all public methods raise NotImplementedError."""

    @pytest.fixture
    def client(self) -> EodhdClient:
        return EodhdClient()

    def test_正常系_全メソッドがNotImplementedErrorをraise(
        self, client: EodhdClient
    ) -> None:
        methods_and_args: list[tuple[str, list[object]]] = [
            ("get_eod_data", ["AAPL.US"]),
            ("get_fundamentals", ["AAPL.US"]),
            ("get_exchange_symbols", ["US"]),
            ("get_exchange_details", ["US"]),
            ("get_dividends", ["AAPL.US"]),
            ("get_splits", ["AAPL.US"]),
            ("get_intraday_data", ["AAPL.US"]),
        ]
        for method_name, args in methods_and_args:
            method = getattr(client, method_name)
            with pytest.raises(NotImplementedError):
                method(*args)
