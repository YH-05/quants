"""Unit tests for market.set_exchange.errors module.

Test TODO List:
- [x] SetError: base exception with message attribute
- [x] SetAPIError: API response error
- [x] SetRateLimitError: rate limit error
- [x] SetParseError: parse error
- [x] SetValidationError: validation error
- [x] Exception hierarchy validation
- [x] __all__ exports
"""

import pytest

from market.set_exchange.errors import (
    SetAPIError,
    SetError,
    SetParseError,
    SetRateLimitError,
    SetValidationError,
)


class TestSetError:
    def test_正常系_メッセージで初期化できる(self) -> None:
        error = SetError("SET operation failed")
        assert error.message == "SET operation failed"

    def test_正常系_Exceptionを直接継承している(self) -> None:
        assert issubclass(SetError, Exception)
        assert Exception in SetError.__bases__

    def test_正常系_raiseで例外として使用可能(self) -> None:
        with pytest.raises(SetError, match="test error"):
            raise SetError("test error")


class TestSetAPIError:
    def test_正常系_全パラメータで初期化(self) -> None:
        error = SetAPIError(
            "API error",
            url="https://api.set.or.th",
            status_code=500,
            response_body="error",
        )
        assert error.status_code == 500

    def test_正常系_SetErrorを継承している(self) -> None:
        assert issubclass(SetAPIError, SetError)


class TestSetRateLimitError:
    def test_正常系_全パラメータで初期化(self) -> None:
        error = SetRateLimitError("rate limited", url=None, retry_after=60)
        assert error.retry_after == 60

    def test_正常系_SetErrorを継承している(self) -> None:
        assert issubclass(SetRateLimitError, SetError)


class TestSetParseError:
    def test_正常系_全パラメータで初期化(self) -> None:
        error = SetParseError("parse error", raw_data="data", field="f")
        assert error.field == "f"

    def test_正常系_SetErrorを継承している(self) -> None:
        assert issubclass(SetParseError, SetError)


class TestSetValidationError:
    def test_正常系_全パラメータで初期化(self) -> None:
        error = SetValidationError("Invalid", field="ticker", value="BAD")
        assert error.field == "ticker"

    def test_正常系_SetErrorを継承している(self) -> None:
        assert issubclass(SetValidationError, SetError)


class TestExceptionHierarchy:
    def test_正常系_全サブクラスがSetErrorを継承(self) -> None:
        assert issubclass(SetAPIError, SetError)
        assert issubclass(SetRateLimitError, SetError)
        assert issubclass(SetParseError, SetError)
        assert issubclass(SetValidationError, SetError)


class TestModuleExports:
    def test_正常系_全クラスがエクスポートされている(self) -> None:
        from market.set_exchange import errors

        expected = {
            "SetError",
            "SetAPIError",
            "SetRateLimitError",
            "SetParseError",
            "SetValidationError",
        }
        assert set(errors.__all__) == expected
