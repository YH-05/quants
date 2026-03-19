"""Unit tests for market.sgx.errors module.

SGX エラークラスのテストスイート。
5つのエラークラス（SgxError, SgxAPIError, SgxRateLimitError,
SgxParseError, SgxValidationError）の動作を検証する。

Test TODO List:
- [x] SgxError: base exception with message attribute
- [x] SgxAPIError: API response error with url, status_code, response_body
- [x] SgxRateLimitError: rate limit error with url, retry_after
- [x] SgxParseError: parse error with raw_data, field
- [x] SgxValidationError: validation error with field, value
- [x] Exception hierarchy validation
- [x] __all__ exports
"""

import pytest

from market.asean_common.errors import ExchangeError
from market.sgx.errors import (
    SgxAPIError,
    SgxError,
    SgxParseError,
    SgxRateLimitError,
    SgxValidationError,
)


class TestSgxError:
    """SgxError 基底例外クラスのテスト。"""

    def test_正常系_メッセージで初期化できる(self) -> None:
        error = SgxError("SGX operation failed")
        assert error.message == "SGX operation failed"
        assert str(error) == "SGX operation failed"

    def test_正常系_ExchangeErrorを継承している(self) -> None:
        assert issubclass(SgxError, ExchangeError)
        assert ExchangeError in SgxError.__bases__
        assert issubclass(SgxError, Exception)

    def test_正常系_raiseで例外として使用可能(self) -> None:
        with pytest.raises(SgxError, match="test error"):
            raise SgxError("test error")


class TestSgxAPIError:
    """SgxAPIError のテスト。"""

    def test_正常系_全パラメータで初期化(self) -> None:
        error = SgxAPIError(
            "API returned HTTP 500",
            url="https://api.sgx.com/data",
            status_code=500,
            response_body='{"error": "Internal Server Error"}',
        )
        assert error.message == "API returned HTTP 500"
        assert error.url == "https://api.sgx.com/data"
        assert error.status_code == 500
        assert error.response_body == '{"error": "Internal Server Error"}'

    def test_正常系_SgxErrorを継承している(self) -> None:
        assert issubclass(SgxAPIError, SgxError)
        error = SgxAPIError("err", url="u", status_code=400, response_body="b")
        assert isinstance(error, SgxError)
        assert isinstance(error, Exception)


class TestSgxRateLimitError:
    """SgxRateLimitError のテスト。"""

    def test_正常系_全パラメータで初期化(self) -> None:
        error = SgxRateLimitError(
            "Rate limit exceeded", url="https://api.sgx.com/data", retry_after=60
        )
        assert error.message == "Rate limit exceeded"
        assert error.url == "https://api.sgx.com/data"
        assert error.retry_after == 60

    def test_正常系_SgxErrorを継承している(self) -> None:
        assert issubclass(SgxRateLimitError, SgxError)

    def test_正常系_retry_afterがNoneでも初期化可能(self) -> None:
        error = SgxRateLimitError("rate limited", url=None, retry_after=None)
        assert error.retry_after is None
        assert error.url is None


class TestSgxParseError:
    """SgxParseError のテスト。"""

    def test_正常系_全パラメータで初期化(self) -> None:
        error = SgxParseError(
            "Failed to parse response", raw_data='{"data": null}', field="data"
        )
        assert error.message == "Failed to parse response"
        assert error.raw_data == '{"data": null}'
        assert error.field == "data"

    def test_正常系_SgxErrorを継承している(self) -> None:
        assert issubclass(SgxParseError, SgxError)

    def test_正常系_raw_dataがNoneでも初期化可能(self) -> None:
        error = SgxParseError("parse error", raw_data=None, field=None)
        assert error.raw_data is None
        assert error.field is None


class TestSgxValidationError:
    """SgxValidationError のテスト。"""

    def test_正常系_全パラメータで初期化(self) -> None:
        error = SgxValidationError("Invalid ticker", field="ticker", value="INVALID")
        assert error.message == "Invalid ticker"
        assert error.field == "ticker"
        assert error.value == "INVALID"

    def test_正常系_SgxErrorを継承している(self) -> None:
        assert issubclass(SgxValidationError, SgxError)

    def test_正常系_valueに様々な型を設定可能(self) -> None:
        error_int = SgxValidationError("invalid", field="code", value=42)
        assert error_int.value == 42
        error_list = SgxValidationError("invalid", field="codes", value=[1, 2])
        assert error_list.value == [1, 2]


class TestExceptionHierarchy:
    """例外クラスの継承階層テスト。"""

    def test_正常系_全サブクラスがSgxErrorを継承(self) -> None:
        assert issubclass(SgxAPIError, SgxError)
        assert issubclass(SgxRateLimitError, SgxError)
        assert issubclass(SgxParseError, SgxError)
        assert issubclass(SgxValidationError, SgxError)

    def test_正常系_SgxErrorがExchangeErrorを継承(self) -> None:
        assert issubclass(SgxError, ExchangeError)
        assert ExchangeError in SgxError.__bases__
        assert issubclass(SgxError, Exception)


class TestModuleExports:
    """__all__ エクスポートのテスト。"""

    def test_正常系_全クラスがエクスポートされている(self) -> None:
        from market.sgx import errors

        assert hasattr(errors, "__all__")
        expected = {
            "SgxError",
            "SgxAPIError",
            "SgxRateLimitError",
            "SgxParseError",
            "SgxValidationError",
        }
        assert set(errors.__all__) == expected
