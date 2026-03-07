"""Unit tests for market.edinet_api.errors module.

EDINET disclosure API エラークラスのテストスイート。
4つのエラークラス（EdinetApiError, EdinetApiAPIError, EdinetApiRateLimitError,
EdinetApiValidationError）の動作を検証する。

Test TODO List:
- [x] EdinetApiError: base exception with message attribute
- [x] EdinetApiAPIError: API response error with url, status_code, response_body
- [x] EdinetApiRateLimitError: rate limit error with url, retry_after
- [x] EdinetApiValidationError: validation error with field, value
- [x] Exception hierarchy validation (MarketError inheritance)
- [x] Common usage patterns (try-except, raise, cause chaining)
- [x] __all__ exports
"""

import pytest

from market.edinet_api.errors import (
    EdinetApiAPIError,
    EdinetApiError,
    EdinetApiRateLimitError,
    EdinetApiValidationError,
)
from market.errors import MarketError

# =============================================================================
# EdinetApiError (base exception)
# =============================================================================


class TestEdinetApiError:
    """EdinetApiError 基底例外クラスのテスト。"""

    def test_正常系_メッセージで初期化できる(self) -> None:
        """EdinetApiError がメッセージで初期化されること。"""
        error = EdinetApiError("EDINET disclosure API operation failed")

        assert error.message == "EDINET disclosure API operation failed"
        assert "EDINET disclosure API operation failed" in str(error)

    def test_正常系_MarketErrorを継承している(self) -> None:
        """EdinetApiError が MarketError を継承していること。"""
        assert issubclass(EdinetApiError, MarketError)

        error = EdinetApiError("test")
        assert isinstance(error, MarketError)
        assert isinstance(error, Exception)

    def test_正常系_raiseで例外として使用可能(self) -> None:
        """raise で例外として使用できること。"""
        with pytest.raises(EdinetApiError, match="test error"):
            raise EdinetApiError("test error")

    def test_正常系_message属性にアクセスできる(self) -> None:
        """message 属性が正しく設定されること。"""
        error = EdinetApiError("some error message")

        assert hasattr(error, "message")
        assert error.message == "some error message"


# =============================================================================
# EdinetApiAPIError
# =============================================================================


class TestEdinetApiAPIError:
    """EdinetApiAPIError (APIレスポンスエラー) のテスト。"""

    def test_正常系_全パラメータで初期化(self) -> None:
        """EdinetApiAPIError が全パラメータで初期化されること。"""
        error = EdinetApiAPIError(
            "API returned HTTP 500",
            url="https://api.edinet-fsa.go.jp/api/v2/documents.json",
            status_code=500,
            response_body='{"message": "Internal Server Error"}',
        )

        assert error.message == "API returned HTTP 500"
        assert error.url == "https://api.edinet-fsa.go.jp/api/v2/documents.json"
        assert error.status_code == 500
        assert error.response_body == '{"message": "Internal Server Error"}'

    def test_正常系_EdinetApiErrorを継承している(self) -> None:
        """EdinetApiAPIError が EdinetApiError を継承していること。"""
        assert issubclass(EdinetApiAPIError, EdinetApiError)

        error = EdinetApiAPIError(
            "api error",
            url="https://api.edinet-fsa.go.jp/api/v2/documents.json",
            status_code=400,
            response_body="Bad Request",
        )
        assert isinstance(error, EdinetApiError)
        assert isinstance(error, MarketError)
        assert isinstance(error, Exception)

    def test_正常系_strでメッセージが表示される(self) -> None:
        """str() でエラーメッセージが表示されること。"""
        error = EdinetApiAPIError(
            "API returned HTTP 403",
            url="https://api.edinet-fsa.go.jp/api/v2/documents.json",
            status_code=403,
            response_body="Forbidden",
        )

        assert "API returned HTTP 403" in str(error)

    def test_正常系_EdinetApiErrorでキャッチできる(self) -> None:
        """EdinetApiError でキャッチできること。"""
        with pytest.raises(EdinetApiError):
            raise EdinetApiAPIError(
                "API error",
                url="https://api.edinet-fsa.go.jp/api/v2/documents.json",
                status_code=500,
                response_body="error",
            )

    def test_正常系_HTTP4xxステータスコードで初期化可能(self) -> None:
        """HTTP 4xx ステータスコードで初期化できること。"""
        error = EdinetApiAPIError(
            "Bad Request",
            url="https://api.edinet-fsa.go.jp/api/v2/documents.json",
            status_code=400,
            response_body="Bad Request",
        )

        assert error.status_code == 400

    def test_正常系_HTTP5xxステータスコードで初期化可能(self) -> None:
        """HTTP 5xx ステータスコードで初期化できること。"""
        error = EdinetApiAPIError(
            "Internal Server Error",
            url="https://api.edinet-fsa.go.jp/api/v2/documents.json",
            status_code=500,
            response_body="Internal Server Error",
        )

        assert error.status_code == 500


# =============================================================================
# EdinetApiRateLimitError
# =============================================================================


class TestEdinetApiRateLimitError:
    """EdinetApiRateLimitError (レートリミット) のテスト。"""

    def test_正常系_全パラメータで初期化(self) -> None:
        """EdinetApiRateLimitError が全パラメータで初期化されること。"""
        error = EdinetApiRateLimitError(
            "Rate limit exceeded",
            url="https://api.edinet-fsa.go.jp/api/v2/documents.json",
            retry_after=60,
        )

        assert error.message == "Rate limit exceeded"
        assert error.url == "https://api.edinet-fsa.go.jp/api/v2/documents.json"
        assert error.retry_after == 60

    def test_正常系_EdinetApiErrorを継承している(self) -> None:
        """EdinetApiRateLimitError が EdinetApiError を継承していること。"""
        assert issubclass(EdinetApiRateLimitError, EdinetApiError)

        error = EdinetApiRateLimitError(
            "rate limited",
            url="https://api.edinet-fsa.go.jp/api/v2/documents.json",
            retry_after=30,
        )
        assert isinstance(error, EdinetApiError)
        assert isinstance(error, MarketError)
        assert isinstance(error, Exception)

    def test_正常系_retry_afterがNoneでも初期化可能(self) -> None:
        """retry_after が None でも初期化できること。"""
        error = EdinetApiRateLimitError(
            "rate limited",
            url="https://api.edinet-fsa.go.jp/api/v2/documents.json",
            retry_after=None,
        )

        assert error.retry_after is None

    def test_正常系_url属性がNoneでも初期化可能(self) -> None:
        """url が None でも初期化できること。"""
        error = EdinetApiRateLimitError(
            "rate limited",
            url=None,
            retry_after=60,
        )

        assert error.url is None
        assert error.retry_after == 60

    def test_正常系_EdinetApiErrorでキャッチできる(self) -> None:
        """EdinetApiError でキャッチできること。"""
        with pytest.raises(EdinetApiError):
            raise EdinetApiRateLimitError(
                "rate limited",
                url=None,
                retry_after=120,
            )


# =============================================================================
# EdinetApiValidationError
# =============================================================================


class TestEdinetApiValidationError:
    """EdinetApiValidationError (バリデーションエラー) のテスト。"""

    def test_正常系_全パラメータで初期化(self) -> None:
        """EdinetApiValidationError が全パラメータで初期化されること。"""
        error = EdinetApiValidationError(
            "Invalid date format: expected YYYY-MM-DD",
            field="date",
            value="2025/01/15",
        )

        assert error.message == "Invalid date format: expected YYYY-MM-DD"
        assert error.field == "date"
        assert error.value == "2025/01/15"

    def test_正常系_EdinetApiErrorを継承している(self) -> None:
        """EdinetApiValidationError が EdinetApiError を継承していること。"""
        assert issubclass(EdinetApiValidationError, EdinetApiError)

        error = EdinetApiValidationError(
            "validation error",
            field="date",
            value="invalid",
        )
        assert isinstance(error, EdinetApiError)
        assert isinstance(error, MarketError)
        assert isinstance(error, Exception)

    def test_正常系_valueに様々な型を設定可能(self) -> None:
        """value に様々な型（str, int, list）を設定できること。"""
        error_str = EdinetApiValidationError("invalid", field="date", value="bad")
        assert error_str.value == "bad"

        error_int = EdinetApiValidationError("invalid", field="year", value=1999)
        assert error_int.value == 1999

        error_list = EdinetApiValidationError("invalid", field="dates", value=[1, 2])
        assert error_list.value == [1, 2]

    def test_正常系_EdinetApiErrorでキャッチできる(self) -> None:
        """EdinetApiError でキャッチできること。"""
        with pytest.raises(EdinetApiError):
            raise EdinetApiValidationError(
                "validation error",
                field="date",
                value="bad",
            )


# =============================================================================
# Exception Hierarchy
# =============================================================================


class TestExceptionHierarchy:
    """例外クラスの継承階層テスト。"""

    def test_正常系_全サブクラスがEdinetApiErrorを継承(self) -> None:
        """全サブクラスが EdinetApiError を継承していること。"""
        assert issubclass(EdinetApiAPIError, EdinetApiError)
        assert issubclass(EdinetApiRateLimitError, EdinetApiError)
        assert issubclass(EdinetApiValidationError, EdinetApiError)

    def test_正常系_EdinetApiErrorがMarketErrorを継承(self) -> None:
        """EdinetApiError が MarketError を継承していること。"""
        assert issubclass(EdinetApiError, MarketError)

    def test_正常系_サブクラスはExceptionのインスタンスである(self) -> None:
        """サブクラスのインスタンスが Exception のインスタンスであること。"""
        api_err = EdinetApiAPIError(
            "test",
            url="https://api.edinet-fsa.go.jp/api/v2/documents.json",
            status_code=500,
            response_body="error",
        )
        assert isinstance(api_err, Exception)

        rate_err = EdinetApiRateLimitError(
            "test",
            url=None,
            retry_after=60,
        )
        assert isinstance(rate_err, Exception)

        val_err = EdinetApiValidationError(
            "test",
            field="date",
            value="bad",
        )
        assert isinstance(val_err, Exception)


# =============================================================================
# Usage Patterns
# =============================================================================


class TestExceptionUsagePatterns:
    """例外クラスの使用パターンテスト。"""

    def test_正常系_原因チェーンが機能する(self) -> None:
        """例外の from チェーンが正しく機能すること。"""
        original = ConnectionError("Connection refused")

        try:
            raise EdinetApiAPIError(
                "API request failed",
                url="https://api.edinet-fsa.go.jp/api/v2/documents.json",
                status_code=503,
                response_body="Service Unavailable",
            ) from original
        except EdinetApiAPIError as e:
            assert e.__cause__ is original
            assert isinstance(e.__cause__, ConnectionError)


# =============================================================================
# Module Exports
# =============================================================================


class TestModuleExports:
    """__all__ エクスポートのテスト。"""

    def test_正常系_全クラスがエクスポートされている(self) -> None:
        """__all__ に全4クラスが含まれていること。"""
        from market.edinet_api import errors

        assert hasattr(errors, "__all__")
        expected = {
            "EdinetApiError",
            "EdinetApiAPIError",
            "EdinetApiRateLimitError",
            "EdinetApiValidationError",
        }
        assert set(errors.__all__) == expected
