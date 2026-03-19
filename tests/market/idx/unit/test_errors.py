"""Unit tests for market.idx.errors module.

Test TODO List:
- [x] IdxError: base exception with message attribute
- [x] IdxAPIError: API response error
- [x] IdxRateLimitError: rate limit error
- [x] IdxParseError: parse error
- [x] IdxValidationError: validation error
- [x] Exception hierarchy validation
- [x] __all__ exports
"""

import pytest

from market.asean_common.errors import ExchangeError
from market.idx.errors import (
    IdxAPIError,
    IdxError,
    IdxParseError,
    IdxRateLimitError,
    IdxValidationError,
)


class TestIdxError:
    def test_正常系_メッセージで初期化できる(self) -> None:
        error = IdxError("IDX operation failed")
        assert error.message == "IDX operation failed"

    def test_正常系_ExchangeErrorを継承している(self) -> None:
        assert issubclass(IdxError, ExchangeError)
        assert ExchangeError in IdxError.__bases__
        assert issubclass(IdxError, Exception)

    def test_正常系_raiseで例外として使用可能(self) -> None:
        with pytest.raises(IdxError, match="test error"):
            raise IdxError("test error")


class TestIdxAPIError:
    def test_正常系_全パラメータで初期化(self) -> None:
        error = IdxAPIError(
            "API error",
            url="https://idx.co.id/api",
            status_code=500,
            response_body="error",
        )
        assert error.status_code == 500

    def test_正常系_IdxErrorを継承している(self) -> None:
        assert issubclass(IdxAPIError, IdxError)


class TestIdxRateLimitError:
    def test_正常系_全パラメータで初期化(self) -> None:
        error = IdxRateLimitError("rate limited", url=None, retry_after=60)
        assert error.retry_after == 60

    def test_正常系_IdxErrorを継承している(self) -> None:
        assert issubclass(IdxRateLimitError, IdxError)


class TestIdxParseError:
    def test_正常系_全パラメータで初期化(self) -> None:
        error = IdxParseError("parse error", raw_data="data", field="f")
        assert error.field == "f"

    def test_正常系_IdxErrorを継承している(self) -> None:
        assert issubclass(IdxParseError, IdxError)


class TestIdxValidationError:
    def test_正常系_全パラメータで初期化(self) -> None:
        error = IdxValidationError("Invalid", field="ticker", value="BAD")
        assert error.field == "ticker"

    def test_正常系_IdxErrorを継承している(self) -> None:
        assert issubclass(IdxValidationError, IdxError)


class TestExceptionHierarchy:
    def test_正常系_全サブクラスがIdxErrorを継承(self) -> None:
        assert issubclass(IdxAPIError, IdxError)
        assert issubclass(IdxRateLimitError, IdxError)
        assert issubclass(IdxParseError, IdxError)
        assert issubclass(IdxValidationError, IdxError)


class TestModuleExports:
    def test_正常系_全クラスがエクスポートされている(self) -> None:
        from market.idx import errors

        expected = {
            "IdxError",
            "IdxAPIError",
            "IdxRateLimitError",
            "IdxParseError",
            "IdxValidationError",
        }
        assert set(errors.__all__) == expected
