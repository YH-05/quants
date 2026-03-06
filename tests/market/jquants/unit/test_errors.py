"""Tests for market.jquants.errors module."""

import pytest

from market.jquants.errors import (
    JQuantsAPIError,
    JQuantsAuthError,
    JQuantsError,
    JQuantsRateLimitError,
    JQuantsValidationError,
)


class TestJQuantsError:
    """Tests for JQuantsError base exception."""

    def test_正常系_Exceptionを継承(self) -> None:
        assert issubclass(JQuantsError, Exception)

    def test_正常系_メッセージが設定される(self) -> None:
        error = JQuantsError("test error")
        assert error.message == "test error"

    def test_正常系_strで取得可能(self) -> None:
        error = JQuantsError("test error")
        assert str(error) == "test error"

    def test_正常系_raiseできる(self) -> None:
        with pytest.raises(JQuantsError, match="test error"):
            raise JQuantsError("test error")


class TestJQuantsAPIError:
    """Tests for JQuantsAPIError."""

    def test_正常系_JQuantsErrorを継承(self) -> None:
        assert issubclass(JQuantsAPIError, JQuantsError)

    def test_正常系_属性が正しく設定される(self) -> None:
        error = JQuantsAPIError(
            message="API error",
            url="https://api.jquants.com/v1/listed/info",
            status_code=500,
            response_body='{"error": "Internal Server Error"}',
        )
        assert error.message == "API error"
        assert error.url == "https://api.jquants.com/v1/listed/info"
        assert error.status_code == 500
        assert error.response_body == '{"error": "Internal Server Error"}'

    def test_正常系_raiseできる(self) -> None:
        with pytest.raises(JQuantsAPIError):
            raise JQuantsAPIError(
                message="Server error",
                url="https://api.jquants.com/v1/test",
                status_code=503,
                response_body="Service Unavailable",
            )

    def test_正常系_JQuantsErrorでキャッチ可能(self) -> None:
        with pytest.raises(JQuantsError):
            raise JQuantsAPIError(
                message="Error",
                url="https://api.jquants.com/v1/test",
                status_code=400,
                response_body="Bad Request",
            )


class TestJQuantsRateLimitError:
    """Tests for JQuantsRateLimitError."""

    def test_正常系_JQuantsErrorを継承(self) -> None:
        assert issubclass(JQuantsRateLimitError, JQuantsError)

    def test_正常系_属性が正しく設定される(self) -> None:
        error = JQuantsRateLimitError(
            message="Rate limit exceeded",
            url="https://api.jquants.com/v1/listed/info",
            retry_after=60,
        )
        assert error.message == "Rate limit exceeded"
        assert error.url == "https://api.jquants.com/v1/listed/info"
        assert error.retry_after == 60

    def test_正常系_retry_afterがNone(self) -> None:
        error = JQuantsRateLimitError(
            message="Rate limit",
            url=None,
            retry_after=None,
        )
        assert error.url is None
        assert error.retry_after is None


class TestJQuantsValidationError:
    """Tests for JQuantsValidationError."""

    def test_正常系_JQuantsErrorを継承(self) -> None:
        assert issubclass(JQuantsValidationError, JQuantsError)

    def test_正常系_属性が正しく設定される(self) -> None:
        error = JQuantsValidationError(
            message="Invalid code",
            field="code",
            value="ABC",
        )
        assert error.message == "Invalid code"
        assert error.field == "code"
        assert error.value == "ABC"

    def test_正常系_raiseできる(self) -> None:
        with pytest.raises(JQuantsValidationError):
            raise JQuantsValidationError(
                message="Invalid",
                field="code",
                value=-1,
            )


class TestJQuantsAuthError:
    """Tests for JQuantsAuthError."""

    def test_正常系_JQuantsErrorを継承(self) -> None:
        assert issubclass(JQuantsAuthError, JQuantsError)

    def test_正常系_メッセージが設定される(self) -> None:
        error = JQuantsAuthError("Invalid credentials")
        assert error.message == "Invalid credentials"

    def test_正常系_raiseできる(self) -> None:
        with pytest.raises(JQuantsAuthError, match="Invalid credentials"):
            raise JQuantsAuthError("Invalid credentials")

    def test_正常系_JQuantsErrorでキャッチ可能(self) -> None:
        with pytest.raises(JQuantsError):
            raise JQuantsAuthError("Auth failed")


class TestErrorHierarchy:
    """Tests for the complete error hierarchy."""

    def test_正常系_全エラーがJQuantsErrorのサブクラス(self) -> None:
        subclasses = [
            JQuantsAPIError,
            JQuantsRateLimitError,
            JQuantsValidationError,
            JQuantsAuthError,
        ]
        for cls in subclasses:
            assert issubclass(cls, JQuantsError), (
                f"{cls.__name__} is not a subclass of JQuantsError"
            )

    def test_正常系_全エラーがExceptionのサブクラス(self) -> None:
        subclasses = [
            JQuantsError,
            JQuantsAPIError,
            JQuantsRateLimitError,
            JQuantsValidationError,
            JQuantsAuthError,
        ]
        for cls in subclasses:
            assert issubclass(cls, Exception), (
                f"{cls.__name__} is not a subclass of Exception"
            )
