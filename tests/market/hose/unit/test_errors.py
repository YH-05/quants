"""Unit tests for market.hose.errors module.

Test TODO List:
- [x] HoseError: base exception with message attribute
- [x] HoseAPIError: API response error
- [x] HoseRateLimitError: rate limit error
- [x] HoseParseError: parse error
- [x] HoseValidationError: validation error
- [x] Exception hierarchy validation
- [x] __all__ exports
"""

import pytest

from market.asean_common.errors import ExchangeError
from market.hose.errors import (
    HoseAPIError,
    HoseError,
    HoseParseError,
    HoseRateLimitError,
    HoseValidationError,
)


class TestHoseError:
    def test_正常系_メッセージで初期化できる(self) -> None:
        error = HoseError("HOSE operation failed")
        assert error.message == "HOSE operation failed"

    def test_正常系_ExchangeErrorを継承している(self) -> None:
        assert issubclass(HoseError, ExchangeError)
        assert ExchangeError in HoseError.__bases__
        assert issubclass(HoseError, Exception)

    def test_正常系_raiseで例外として使用可能(self) -> None:
        with pytest.raises(HoseError, match="test error"):
            raise HoseError("test error")


class TestHoseAPIError:
    def test_正常系_全パラメータで初期化(self) -> None:
        error = HoseAPIError(
            "API error",
            url="https://hose.vn/api",
            status_code=500,
            response_body="error",
        )
        assert error.status_code == 500

    def test_正常系_HoseErrorを継承している(self) -> None:
        assert issubclass(HoseAPIError, HoseError)


class TestHoseRateLimitError:
    def test_正常系_全パラメータで初期化(self) -> None:
        error = HoseRateLimitError("rate limited", url=None, retry_after=60)
        assert error.retry_after == 60

    def test_正常系_HoseErrorを継承している(self) -> None:
        assert issubclass(HoseRateLimitError, HoseError)


class TestHoseParseError:
    def test_正常系_全パラメータで初期化(self) -> None:
        error = HoseParseError("parse error", raw_data="data", field="f")
        assert error.field == "f"

    def test_正常系_HoseErrorを継承している(self) -> None:
        assert issubclass(HoseParseError, HoseError)


class TestHoseValidationError:
    def test_正常系_全パラメータで初期化(self) -> None:
        error = HoseValidationError("Invalid", field="ticker", value="BAD")
        assert error.field == "ticker"

    def test_正常系_HoseErrorを継承している(self) -> None:
        assert issubclass(HoseValidationError, HoseError)


class TestExceptionHierarchy:
    def test_正常系_全サブクラスがHoseErrorを継承(self) -> None:
        assert issubclass(HoseAPIError, HoseError)
        assert issubclass(HoseRateLimitError, HoseError)
        assert issubclass(HoseParseError, HoseError)
        assert issubclass(HoseValidationError, HoseError)


class TestModuleExports:
    def test_正常系_全クラスがエクスポートされている(self) -> None:
        from market.hose import errors

        expected = {
            "HoseError",
            "HoseAPIError",
            "HoseRateLimitError",
            "HoseParseError",
            "HoseValidationError",
        }
        assert set(errors.__all__) == expected
