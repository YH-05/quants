"""Unit tests for market.bursa.errors module.

Test TODO List:
- [x] BursaError: base exception with message attribute
- [x] BursaAPIError: API response error
- [x] BursaRateLimitError: rate limit error
- [x] BursaParseError: parse error
- [x] BursaValidationError: validation error
- [x] Exception hierarchy validation
- [x] __all__ exports
"""

import pytest

from market.bursa.errors import (
    BursaAPIError,
    BursaError,
    BursaParseError,
    BursaRateLimitError,
    BursaValidationError,
)


class TestBursaError:
    def test_正常系_メッセージで初期化できる(self) -> None:
        error = BursaError("Bursa operation failed")
        assert error.message == "Bursa operation failed"
        assert str(error) == "Bursa operation failed"

    def test_正常系_Exceptionを直接継承している(self) -> None:
        assert issubclass(BursaError, Exception)
        assert Exception in BursaError.__bases__

    def test_正常系_raiseで例外として使用可能(self) -> None:
        with pytest.raises(BursaError, match="test error"):
            raise BursaError("test error")


class TestBursaAPIError:
    def test_正常系_全パラメータで初期化(self) -> None:
        error = BursaAPIError(
            "API returned HTTP 500",
            url="https://api.bursamalaysia.com/data",
            status_code=500,
            response_body='{"error": "Internal Server Error"}',
        )
        assert error.message == "API returned HTTP 500"
        assert error.url == "https://api.bursamalaysia.com/data"
        assert error.status_code == 500

    def test_正常系_BursaErrorを継承している(self) -> None:
        assert issubclass(BursaAPIError, BursaError)


class TestBursaRateLimitError:
    def test_正常系_全パラメータで初期化(self) -> None:
        error = BursaRateLimitError(
            "Rate limit exceeded", url="https://api.bursamalaysia.com", retry_after=60
        )
        assert error.retry_after == 60

    def test_正常系_BursaErrorを継承している(self) -> None:
        assert issubclass(BursaRateLimitError, BursaError)

    def test_正常系_retry_afterがNoneでも初期化可能(self) -> None:
        error = BursaRateLimitError("rate limited", url=None, retry_after=None)
        assert error.retry_after is None


class TestBursaParseError:
    def test_正常系_全パラメータで初期化(self) -> None:
        error = BursaParseError("parse error", raw_data='{"d": null}', field="d")
        assert error.raw_data == '{"d": null}'
        assert error.field == "d"

    def test_正常系_BursaErrorを継承している(self) -> None:
        assert issubclass(BursaParseError, BursaError)


class TestBursaValidationError:
    def test_正常系_全パラメータで初期化(self) -> None:
        error = BursaValidationError("Invalid", field="ticker", value="BAD")
        assert error.field == "ticker"
        assert error.value == "BAD"

    def test_正常系_BursaErrorを継承している(self) -> None:
        assert issubclass(BursaValidationError, BursaError)


class TestExceptionHierarchy:
    def test_正常系_全サブクラスがBursaErrorを継承(self) -> None:
        assert issubclass(BursaAPIError, BursaError)
        assert issubclass(BursaRateLimitError, BursaError)
        assert issubclass(BursaParseError, BursaError)
        assert issubclass(BursaValidationError, BursaError)


class TestModuleExports:
    def test_正常系_全クラスがエクスポートされている(self) -> None:
        from market.bursa import errors

        expected = {
            "BursaError",
            "BursaAPIError",
            "BursaRateLimitError",
            "BursaParseError",
            "BursaValidationError",
        }
        assert set(errors.__all__) == expected
