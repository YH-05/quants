"""Unit tests for market.bloomberg.errors module.

TDD Red Phase: These tests are designed to fail initially.
The implementation (market.bloomberg.errors) does not exist yet.

Test TODO List:
- [x] BloombergError: base exception with message, code, details
- [x] BloombergConnectionError: connection failures
- [x] BloombergSessionError: session management failures
- [x] BloombergDataError: data fetching failures
- [x] BloombergValidationError: input validation failures
"""

import pytest


class TestErrorCode:
    """Tests for ErrorCode enum."""

    def test_正常系_主要なエラーコードが定義されている(self) -> None:
        """必要なエラーコードが全て定義されていることを確認。"""
        from market.errors import ErrorCode

        # Connection related
        assert hasattr(ErrorCode, "CONNECTION_FAILED")
        assert hasattr(ErrorCode, "SESSION_ERROR")
        assert hasattr(ErrorCode, "SERVICE_ERROR")

        # Data related
        assert hasattr(ErrorCode, "INVALID_SECURITY")
        assert hasattr(ErrorCode, "INVALID_FIELD")
        assert hasattr(ErrorCode, "DATA_NOT_FOUND")

        # Validation related
        assert hasattr(ErrorCode, "INVALID_PARAMETER")
        assert hasattr(ErrorCode, "INVALID_DATE_RANGE")

    def test_正常系_str型を継承(self) -> None:
        """ErrorCode が str を継承していることを確認。"""
        from market.errors import ErrorCode

        assert isinstance(ErrorCode.CONNECTION_FAILED, str)


class TestBloombergError:
    """Tests for BloombergError base exception."""

    def test_正常系_基本的な初期化(self) -> None:
        """BloombergError が基本パラメータで初期化されることを確認。"""
        from market.errors import BloombergError

        error = BloombergError("Test error")
        assert error.message == "Test error"
        assert str(error) == "Test error"

    def test_正常系_エラーコード付きで初期化(self) -> None:
        """BloombergError がエラーコード付きで初期化されることを確認。"""
        from market.errors import BloombergError, ErrorCode

        error = BloombergError("Connection failed", code=ErrorCode.CONNECTION_FAILED)
        assert error.code == ErrorCode.CONNECTION_FAILED

    def test_正常系_詳細情報付きで初期化(self) -> None:
        """BloombergError が詳細情報付きで初期化されることを確認。"""
        from market.errors import BloombergError

        error = BloombergError(
            "Test error",
            details={"host": "localhost", "port": 8194},
        )
        assert error.details["host"] == "localhost"
        assert error.details["port"] == 8194

    def test_正常系_原因例外付きで初期化(self) -> None:
        """BloombergError が原因例外付きで初期化されることを確認。"""
        from market.errors import BloombergError

        cause = ConnectionError("Network unreachable")
        error = BloombergError("Connection failed", cause=cause)
        assert error.cause == cause

    def test_正常系_to_dictメソッド(self) -> None:
        """BloombergError.to_dict() が正しく動作することを確認。"""
        from market.errors import BloombergError, ErrorCode

        error = BloombergError(
            "Test error",
            code=ErrorCode.CONNECTION_FAILED,
            details={"host": "localhost"},
        )
        result = error.to_dict()

        assert result["message"] == "Test error"
        assert result["code"] == "CONNECTION_FAILED"
        assert result["details"]["host"] == "localhost"


class TestBloombergConnectionError:
    """Tests for BloombergConnectionError exception."""

    def test_正常系_基本的な初期化(self) -> None:
        """BloombergConnectionError が初期化されることを確認。"""
        from market.errors import BloombergConnectionError

        error = BloombergConnectionError("Failed to connect to Bloomberg Terminal")
        assert "Failed to connect" in str(error)

    def test_正常系_ホストポート情報付きで初期化(self) -> None:
        """BloombergConnectionError がホスト・ポート情報付きで初期化されることを確認。"""
        from market.errors import BloombergConnectionError, ErrorCode

        error = BloombergConnectionError(
            "Connection refused",
            host="localhost",
            port=8194,
        )
        assert error.host == "localhost"
        assert error.port == 8194
        assert error.code == ErrorCode.CONNECTION_FAILED

    def test_正常系_BloombergErrorを継承(self) -> None:
        """BloombergConnectionError が BloombergError を継承していることを確認。"""
        from market.errors import BloombergConnectionError, BloombergError

        error = BloombergConnectionError("Test")
        assert isinstance(error, BloombergError)


class TestBloombergSessionError:
    """Tests for BloombergSessionError exception."""

    def test_正常系_基本的な初期化(self) -> None:
        """BloombergSessionError が初期化されることを確認。"""
        from market.errors import BloombergSessionError

        error = BloombergSessionError("Session start failed")
        assert "Session start failed" in str(error)

    def test_正常系_セッション状態付きで初期化(self) -> None:
        """BloombergSessionError がセッション状態付きで初期化されることを確認。"""
        from market.errors import BloombergSessionError, ErrorCode

        error = BloombergSessionError(
            "Service not available",
            service="//blp/refdata",
        )
        assert error.service == "//blp/refdata"
        assert error.code == ErrorCode.SESSION_ERROR

    def test_正常系_BloombergErrorを継承(self) -> None:
        """BloombergSessionError が BloombergError を継承していることを確認。"""
        from market.errors import BloombergError, BloombergSessionError

        error = BloombergSessionError("Test")
        assert isinstance(error, BloombergError)


class TestBloombergDataError:
    """Tests for BloombergDataError exception."""

    def test_正常系_基本的な初期化(self) -> None:
        """BloombergDataError が初期化されることを確認。"""
        from market.errors import BloombergDataError

        error = BloombergDataError("Failed to fetch data")
        assert "Failed to fetch data" in str(error)

    def test_正常系_セキュリティ情報付きで初期化(self) -> None:
        """BloombergDataError がセキュリティ情報付きで初期化されることを確認。"""
        from market.errors import BloombergDataError

        error = BloombergDataError(
            "No data for security",
            security="INVALID US Equity",
        )
        assert error.security == "INVALID US Equity"
        assert "INVALID US Equity" in error.details.get("security", "")

    def test_正常系_フィールド情報付きで初期化(self) -> None:
        """BloombergDataError がフィールド情報付きで初期化されることを確認。"""
        from market.errors import BloombergDataError

        error = BloombergDataError(
            "Invalid field",
            security="AAPL US Equity",
            fields=["PX_LAST", "INVALID_FIELD"],
        )
        assert error.security == "AAPL US Equity"
        assert error.fields == ["PX_LAST", "INVALID_FIELD"]

    def test_正常系_BloombergErrorを継承(self) -> None:
        """BloombergDataError が BloombergError を継承していることを確認。"""
        from market.errors import BloombergDataError, BloombergError

        error = BloombergDataError("Test")
        assert isinstance(error, BloombergError)


class TestBloombergValidationError:
    """Tests for BloombergValidationError exception."""

    def test_正常系_基本的な初期化(self) -> None:
        """BloombergValidationError が初期化されることを確認。"""
        from market.errors import BloombergValidationError

        error = BloombergValidationError("Invalid input")
        assert "Invalid input" in str(error)

    def test_正常系_フィールド情報付きで初期化(self) -> None:
        """BloombergValidationError がフィールド情報付きで初期化されることを確認。"""
        from market.errors import BloombergValidationError

        error = BloombergValidationError(
            "Invalid date format",
            field="start_date",
            value="not-a-date",
        )
        assert error.field == "start_date"
        assert error.value == "not-a-date"

    def test_正常系_デフォルトエラーコードがINVALID_PARAMETER(self) -> None:
        """BloombergValidationError のデフォルトエラーコードが INVALID_PARAMETER であることを確認。"""
        from market.errors import BloombergValidationError, ErrorCode

        error = BloombergValidationError("Invalid value")
        assert error.code == ErrorCode.INVALID_PARAMETER

    def test_正常系_BloombergErrorを継承(self) -> None:
        """BloombergValidationError が BloombergError を継承していることを確認。"""
        from market.errors import BloombergError, BloombergValidationError

        error = BloombergValidationError("Test")
        assert isinstance(error, BloombergError)


class TestExceptionHierarchy:
    """Tests for exception class hierarchy."""

    def test_正常系_例外階層が正しい(self) -> None:
        """例外クラスの継承関係が正しいことを確認。"""
        from market.errors import (
            BloombergConnectionError,
            BloombergDataError,
            BloombergError,
            BloombergSessionError,
            BloombergValidationError,
        )

        # All specific errors inherit from BloombergError
        assert issubclass(BloombergConnectionError, BloombergError)
        assert issubclass(BloombergSessionError, BloombergError)
        assert issubclass(BloombergDataError, BloombergError)
        assert issubclass(BloombergValidationError, BloombergError)

        # BloombergError inherits from Exception
        assert issubclass(BloombergError, Exception)

    def test_正常系_BloombergErrorがMarketErrorを継承(self) -> None:
        """BloombergError が MarketError を継承していることを確認。"""
        from market.errors import BloombergError, MarketError

        assert issubclass(BloombergError, MarketError)

    def test_正常系_BloombergErrorインスタンスがMarketError(self) -> None:
        """BloombergError インスタンスが MarketError として扱えることを確認。"""
        from market.errors import BloombergError, MarketError

        error = BloombergError("Test error")
        assert isinstance(error, MarketError)

    def test_正常系_BloombergサブクラスがMarketError(self) -> None:
        """Bloomberg サブクラスが全て MarketError を継承していることを確認。"""
        from market.errors import (
            BloombergConnectionError,
            BloombergDataError,
            BloombergSessionError,
            BloombergValidationError,
            MarketError,
        )

        assert issubclass(BloombergConnectionError, MarketError)
        assert issubclass(BloombergSessionError, MarketError)
        assert issubclass(BloombergDataError, MarketError)
        assert issubclass(BloombergValidationError, MarketError)

    def test_正常系_MarketErrorでキャッチ可能(self) -> None:
        """BloombergError を MarketError でキャッチできることを確認。"""
        from market.errors import BloombergConnectionError, MarketError

        with pytest.raises(MarketError):
            raise BloombergConnectionError("Test")


class TestExceptionUsagePatterns:
    """Tests for common exception usage patterns."""

    def test_正常系_try_exceptでキャッチできる(self) -> None:
        """例外がtry-exceptでキャッチできることを確認。"""
        from market.errors import BloombergConnectionError, BloombergError

        def raise_connection_error() -> None:
            raise BloombergConnectionError("Test")

        # Specific exception
        with pytest.raises(BloombergConnectionError):
            raise_connection_error()

        # Base exception
        with pytest.raises(BloombergError):
            raise_connection_error()

    def test_正常系_原因チェーンが機能する(self) -> None:
        """例外の原因チェーンが正しく機能することを確認。"""
        from market.errors import BloombergConnectionError

        original = OSError("Network error")
        error = BloombergConnectionError("Connection failed", cause=original)

        assert error.cause is original
        assert isinstance(error.cause, OSError)
