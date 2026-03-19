"""Tests for market.eodhd.errors module."""

import pytest

from market.eodhd.errors import (
    EodhdAPIError,
    EodhdAuthError,
    EodhdError,
    EodhdRateLimitError,
    EodhdValidationError,
)


class TestEodhdError:
    """Tests for EodhdError base exception."""

    def test_正常系_Exceptionを継承(self) -> None:
        assert issubclass(EodhdError, Exception)

    def test_正常系_メッセージが設定される(self) -> None:
        error = EodhdError("test error")
        assert error.message == "test error"

    def test_正常系_strで取得可能(self) -> None:
        error = EodhdError("test error")
        assert str(error) == "test error"

    def test_正常系_raiseできる(self) -> None:
        with pytest.raises(EodhdError, match="test error"):
            raise EodhdError("test error")


class TestEodhdAPIError:
    """Tests for EodhdAPIError."""

    def test_正常系_EodhdErrorを継承(self) -> None:
        assert issubclass(EodhdAPIError, EodhdError)

    def test_正常系_属性が正しく設定される(self) -> None:
        error = EodhdAPIError(
            message="API error",
            url="https://eodhd.com/api/eod/AAPL.US",
            status_code=500,
            response_body='{"error": "Internal Server Error"}',
        )
        assert error.message == "API error"
        assert error.url == "https://eodhd.com/api/eod/AAPL.US"
        assert error.status_code == 500
        assert error.response_body == '{"error": "Internal Server Error"}'

    def test_正常系_raiseできる(self) -> None:
        with pytest.raises(EodhdAPIError):
            raise EodhdAPIError(
                message="Server error",
                url="https://eodhd.com/api/eod/AAPL.US",
                status_code=503,
                response_body="Service Unavailable",
            )

    def test_正常系_EodhdErrorでキャッチ可能(self) -> None:
        with pytest.raises(EodhdError):
            raise EodhdAPIError(
                message="Error",
                url="https://eodhd.com/api/eod/AAPL.US",
                status_code=400,
                response_body="Bad Request",
            )


class TestEodhdRateLimitError:
    """Tests for EodhdRateLimitError."""

    def test_正常系_EodhdErrorを継承(self) -> None:
        assert issubclass(EodhdRateLimitError, EodhdError)

    def test_正常系_属性が正しく設定される(self) -> None:
        error = EodhdRateLimitError(
            message="Rate limit exceeded",
            url="https://eodhd.com/api/eod/AAPL.US",
            retry_after=60,
        )
        assert error.message == "Rate limit exceeded"
        assert error.url == "https://eodhd.com/api/eod/AAPL.US"
        assert error.retry_after == 60

    def test_正常系_retry_afterがNone(self) -> None:
        error = EodhdRateLimitError(
            message="Rate limit",
            url=None,
            retry_after=None,
        )
        assert error.url is None
        assert error.retry_after is None


class TestEodhdValidationError:
    """Tests for EodhdValidationError."""

    def test_正常系_EodhdErrorを継承(self) -> None:
        assert issubclass(EodhdValidationError, EodhdError)

    def test_正常系_属性が正しく設定される(self) -> None:
        error = EodhdValidationError(
            message="Invalid symbol",
            field="symbol",
            value="",
        )
        assert error.message == "Invalid symbol"
        assert error.field == "symbol"
        assert error.value == ""

    def test_正常系_raiseできる(self) -> None:
        with pytest.raises(EodhdValidationError):
            raise EodhdValidationError(
                message="Invalid",
                field="symbol",
                value=-1,
            )


class TestEodhdAuthError:
    """Tests for EodhdAuthError."""

    def test_正常系_EodhdErrorを継承(self) -> None:
        assert issubclass(EodhdAuthError, EodhdError)

    def test_正常系_メッセージが設定される(self) -> None:
        error = EodhdAuthError("Invalid API key")
        assert error.message == "Invalid API key"

    def test_正常系_raiseできる(self) -> None:
        with pytest.raises(EodhdAuthError, match="Invalid API key"):
            raise EodhdAuthError("Invalid API key")

    def test_正常系_EodhdErrorでキャッチ可能(self) -> None:
        with pytest.raises(EodhdError):
            raise EodhdAuthError("Auth failed")


class TestErrorHierarchy:
    """Tests for the complete error hierarchy."""

    def test_正常系_全エラーがEodhdErrorのサブクラス(self) -> None:
        subclasses = [
            EodhdAPIError,
            EodhdRateLimitError,
            EodhdValidationError,
            EodhdAuthError,
        ]
        for cls in subclasses:
            assert issubclass(cls, EodhdError), (
                f"{cls.__name__} is not a subclass of EodhdError"
            )

    def test_正常系_全エラーがExceptionのサブクラス(self) -> None:
        subclasses = [
            EodhdError,
            EodhdAPIError,
            EodhdRateLimitError,
            EodhdValidationError,
            EodhdAuthError,
        ]
        for cls in subclasses:
            assert issubclass(cls, Exception), (
                f"{cls.__name__} is not a subclass of Exception"
            )
