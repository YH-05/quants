"""Tests for market.alphavantage.errors module."""

import pytest

from market.alphavantage.errors import (
    AlphaVantageAPIError,
    AlphaVantageAuthError,
    AlphaVantageError,
    AlphaVantageParseError,
    AlphaVantageRateLimitError,
    AlphaVantageValidationError,
)


class TestAlphaVantageError:
    """Tests for AlphaVantageError base exception."""

    def test_正常系_Exceptionを継承(self) -> None:
        assert issubclass(AlphaVantageError, Exception)

    def test_正常系_メッセージが設定される(self) -> None:
        error = AlphaVantageError("test error")
        assert error.message == "test error"

    def test_正常系_strで取得可能(self) -> None:
        error = AlphaVantageError("test error")
        assert str(error) == "test error"

    def test_正常系_raiseできる(self) -> None:
        with pytest.raises(AlphaVantageError, match="test error"):
            raise AlphaVantageError("test error")


class TestAlphaVantageAPIError:
    """Tests for AlphaVantageAPIError."""

    def test_正常系_AlphaVantageErrorを継承(self) -> None:
        assert issubclass(AlphaVantageAPIError, AlphaVantageError)

    def test_正常系_属性が正しく設定される(self) -> None:
        error = AlphaVantageAPIError(
            message="API error",
            url="https://www.alphavantage.co/query?function=TIME_SERIES_DAILY",
            status_code=500,
            response_body='{"Error Message": "Internal Server Error"}',
        )
        assert error.message == "API error"
        assert (
            error.url == "https://www.alphavantage.co/query?function=TIME_SERIES_DAILY"
        )
        assert error.status_code == 500
        assert error.response_body == '{"Error Message": "Internal Server Error"}'

    def test_正常系_raiseできる(self) -> None:
        with pytest.raises(AlphaVantageAPIError):
            raise AlphaVantageAPIError(
                message="Server error",
                url="https://www.alphavantage.co/query",
                status_code=503,
                response_body="Service Unavailable",
            )

    def test_正常系_AlphaVantageErrorでキャッチ可能(self) -> None:
        with pytest.raises(AlphaVantageError):
            raise AlphaVantageAPIError(
                message="Error",
                url="https://www.alphavantage.co/query",
                status_code=400,
                response_body="Bad Request",
            )


class TestAlphaVantageRateLimitError:
    """Tests for AlphaVantageRateLimitError."""

    def test_正常系_AlphaVantageErrorを継承(self) -> None:
        assert issubclass(AlphaVantageRateLimitError, AlphaVantageError)

    def test_正常系_属性が正しく設定される(self) -> None:
        error = AlphaVantageRateLimitError(
            message="Rate limit exceeded",
            url="https://www.alphavantage.co/query",
            retry_after=60,
        )
        assert error.message == "Rate limit exceeded"
        assert error.url == "https://www.alphavantage.co/query"
        assert error.retry_after == 60

    def test_正常系_retry_afterがNone(self) -> None:
        error = AlphaVantageRateLimitError(
            message="Rate limit",
            url=None,
            retry_after=None,
        )
        assert error.url is None
        assert error.retry_after is None


class TestAlphaVantageValidationError:
    """Tests for AlphaVantageValidationError."""

    def test_正常系_AlphaVantageErrorを継承(self) -> None:
        assert issubclass(AlphaVantageValidationError, AlphaVantageError)

    def test_正常系_属性が正しく設定される(self) -> None:
        error = AlphaVantageValidationError(
            message="Invalid symbol",
            field="symbol",
            value="",
        )
        assert error.message == "Invalid symbol"
        assert error.field == "symbol"
        assert error.value == ""

    def test_正常系_raiseできる(self) -> None:
        with pytest.raises(AlphaVantageValidationError):
            raise AlphaVantageValidationError(
                message="Invalid",
                field="interval",
                value=-1,
            )


class TestAlphaVantageParseError:
    """Tests for AlphaVantageParseError."""

    def test_正常系_AlphaVantageErrorを継承(self) -> None:
        assert issubclass(AlphaVantageParseError, AlphaVantageError)

    def test_正常系_属性が正しく設定される(self) -> None:
        error = AlphaVantageParseError(
            message="Failed to parse response",
            raw_data='{"invalid": "data"}',
            field="Time Series (Daily)",
        )
        assert error.message == "Failed to parse response"
        assert error.raw_data == '{"invalid": "data"}'
        assert error.field == "Time Series (Daily)"

    def test_正常系_raiseできる(self) -> None:
        with pytest.raises(AlphaVantageParseError):
            raise AlphaVantageParseError(
                message="Parse failed",
                raw_data="not json",
                field="open",
            )

    def test_正常系_AlphaVantageErrorでキャッチ可能(self) -> None:
        with pytest.raises(AlphaVantageError):
            raise AlphaVantageParseError(
                message="Error",
                raw_data="",
                field="close",
            )


class TestAlphaVantageAuthError:
    """Tests for AlphaVantageAuthError."""

    def test_正常系_AlphaVantageErrorを継承(self) -> None:
        assert issubclass(AlphaVantageAuthError, AlphaVantageError)

    def test_正常系_メッセージが設定される(self) -> None:
        error = AlphaVantageAuthError("Invalid API key")
        assert error.message == "Invalid API key"

    def test_正常系_raiseできる(self) -> None:
        with pytest.raises(AlphaVantageAuthError, match="Invalid API key"):
            raise AlphaVantageAuthError("Invalid API key")

    def test_正常系_AlphaVantageErrorでキャッチ可能(self) -> None:
        with pytest.raises(AlphaVantageError):
            raise AlphaVantageAuthError("Auth failed")


class TestErrorHierarchy:
    """Tests for the complete error hierarchy."""

    def test_正常系_全エラーがAlphaVantageErrorのサブクラス(self) -> None:
        subclasses = [
            AlphaVantageAPIError,
            AlphaVantageRateLimitError,
            AlphaVantageValidationError,
            AlphaVantageParseError,
            AlphaVantageAuthError,
        ]
        for cls in subclasses:
            assert issubclass(cls, AlphaVantageError), (
                f"{cls.__name__} is not a subclass of AlphaVantageError"
            )

    # AIDEV-NOTE: test_正常系_全エラーがExceptionのサブクラス は削除。
    # AlphaVantageError が Exception を継承し、全サブクラスが AlphaVantageError を
    # 継承していることは上の test_正常系_全エラーがAlphaVantageErrorのサブクラス で
    # 推移的に担保されている。


class TestAllExports:
    """Tests for __all__ completeness."""

    def test_正常系_allが定義されている(self) -> None:
        from market.alphavantage import errors

        assert hasattr(errors, "__all__")

    def test_正常系_全例外クラスがallに含まれる(self) -> None:
        from market.alphavantage import errors

        expected = {
            "AlphaVantageAPIError",
            "AlphaVantageAuthError",
            "AlphaVantageError",
            "AlphaVantageParseError",
            "AlphaVantageRateLimitError",
            "AlphaVantageValidationError",
        }
        assert set(errors.__all__) == expected
