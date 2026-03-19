"""Unit tests for market.pse.errors module.

Test TODO List:
- [x] PseError: base exception with message attribute
- [x] PseAPIError: API response error
- [x] PseRateLimitError: rate limit error
- [x] PseParseError: parse error
- [x] PseValidationError: validation error
- [x] Exception hierarchy validation
- [x] __all__ exports
"""

import pytest

from market.asean_common.errors import ExchangeError
from market.pse.errors import (
    PseAPIError,
    PseError,
    PseParseError,
    PseRateLimitError,
    PseValidationError,
)


class TestPseError:
    def test_正常系_メッセージで初期化できる(self) -> None:
        error = PseError("PSE operation failed")
        assert error.message == "PSE operation failed"

    def test_正常系_ExchangeErrorを継承している(self) -> None:
        assert issubclass(PseError, ExchangeError)
        assert ExchangeError in PseError.__bases__
        assert issubclass(PseError, Exception)

    def test_正常系_raiseで例外として使用可能(self) -> None:
        with pytest.raises(PseError, match="test error"):
            raise PseError("test error")


class TestPseAPIError:
    def test_正常系_全パラメータで初期化(self) -> None:
        error = PseAPIError(
            "API error",
            url="https://pse.com.ph/api",
            status_code=500,
            response_body="error",
        )
        assert error.status_code == 500

    def test_正常系_PseErrorを継承している(self) -> None:
        assert issubclass(PseAPIError, PseError)


class TestPseRateLimitError:
    def test_正常系_全パラメータで初期化(self) -> None:
        error = PseRateLimitError("rate limited", url=None, retry_after=60)
        assert error.retry_after == 60

    def test_正常系_PseErrorを継承している(self) -> None:
        assert issubclass(PseRateLimitError, PseError)


class TestPseParseError:
    def test_正常系_全パラメータで初期化(self) -> None:
        error = PseParseError("parse error", raw_data="data", field="f")
        assert error.field == "f"

    def test_正常系_PseErrorを継承している(self) -> None:
        assert issubclass(PseParseError, PseError)


class TestPseValidationError:
    def test_正常系_全パラメータで初期化(self) -> None:
        error = PseValidationError("Invalid", field="ticker", value="BAD")
        assert error.field == "ticker"

    def test_正常系_PseErrorを継承している(self) -> None:
        assert issubclass(PseValidationError, PseError)


class TestExceptionHierarchy:
    def test_正常系_全サブクラスがPseErrorを継承(self) -> None:
        assert issubclass(PseAPIError, PseError)
        assert issubclass(PseRateLimitError, PseError)
        assert issubclass(PseParseError, PseError)
        assert issubclass(PseValidationError, PseError)


class TestModuleExports:
    def test_正常系_全クラスがエクスポートされている(self) -> None:
        from market.pse import errors

        expected = {
            "PseError",
            "PseAPIError",
            "PseRateLimitError",
            "PseParseError",
            "PseValidationError",
        }
        assert set(errors.__all__) == expected
