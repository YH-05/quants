"""Unit tests for market.bse.errors module.

BSE API エラークラスのテストスイート。
5つのエラークラス（BseError, BseAPIError, BseRateLimitError,
BseParseError, BseValidationError）の動作を検証する。

Test TODO List:
- [x] BseError: base exception with message attribute
- [x] BseAPIError: API response error with url, status_code, response_body
- [x] BseRateLimitError: rate limit error with url, retry_after
- [x] BseParseError: parse error with raw_data, field
- [x] BseValidationError: validation error with field, value
- [x] Exception hierarchy validation
- [x] Common usage patterns (try-except, raise, cause chaining)
- [x] __all__ exports
"""

import pytest

from market.bse.errors import (
    BseAPIError,
    BseError,
    BseParseError,
    BseRateLimitError,
    BseValidationError,
)

# =============================================================================
# BseError (base exception)
# =============================================================================


class TestBseError:
    """BseError 基底例外クラスのテスト。"""

    def test_正常系_メッセージで初期化できる(self) -> None:
        """BseError がメッセージで初期化されること。"""
        error = BseError("BSE API operation failed")

        assert error.message == "BSE API operation failed"
        assert str(error) == "BSE API operation failed"

    def test_正常系_Exceptionを直接継承している(self) -> None:
        """BseError が Exception を直接継承していること。"""
        assert issubclass(BseError, Exception)
        assert Exception in BseError.__bases__

    def test_正常系_raiseで例外として使用可能(self) -> None:
        """raise で例外として使用できること。"""
        with pytest.raises(BseError, match="test error"):
            raise BseError("test error")

    def test_正常系_message属性にアクセスできる(self) -> None:
        """message 属性が正しく設定されること。"""
        error = BseError("some error message")

        assert hasattr(error, "message")
        assert error.message == "some error message"


# =============================================================================
# BseAPIError
# =============================================================================


class TestBseAPIError:
    """BseAPIError (APIレスポンスエラー) のテスト。"""

    def test_正常系_全パラメータで初期化(self) -> None:
        """BseAPIError が全パラメータで初期化されること。"""
        error = BseAPIError(
            "API returned HTTP 500",
            url="https://api.bseindia.com/BseIndiaAPI/api/getScripHeaderData",
            status_code=500,
            response_body='{"error": "Internal Server Error"}',
        )

        assert error.message == "API returned HTTP 500"
        assert (
            error.url == "https://api.bseindia.com/BseIndiaAPI/api/getScripHeaderData"
        )
        assert error.status_code == 500
        assert error.response_body == '{"error": "Internal Server Error"}'

    def test_正常系_BseErrorを継承している(self) -> None:
        """BseAPIError が BseError を継承していること。"""
        assert issubclass(BseAPIError, BseError)

        error = BseAPIError(
            "api error",
            url="https://api.bseindia.com/BseIndiaAPI/api/getScripHeaderData",
            status_code=400,
            response_body="Bad Request",
        )
        assert isinstance(error, BseError)
        assert isinstance(error, Exception)

    def test_正常系_strでメッセージが表示される(self) -> None:
        """str() でエラーメッセージが表示されること。"""
        error = BseAPIError(
            "API returned HTTP 403",
            url="https://api.bseindia.com/BseIndiaAPI/api/getScripHeaderData",
            status_code=403,
            response_body="Forbidden",
        )

        assert "API returned HTTP 403" in str(error)

    def test_正常系_BseErrorでキャッチできる(self) -> None:
        """BseError でキャッチできること。"""
        with pytest.raises(BseError):
            raise BseAPIError(
                "API error",
                url="https://api.bseindia.com/BseIndiaAPI/api/getScripHeaderData",
                status_code=500,
                response_body="error",
            )

    def test_正常系_HTTP4xxステータスコードで初期化可能(self) -> None:
        """HTTP 4xx ステータスコードで初期化できること。"""
        error = BseAPIError(
            "Bad Request",
            url="https://api.bseindia.com/BseIndiaAPI/api/getScripHeaderData",
            status_code=400,
            response_body="Bad Request",
        )

        assert error.status_code == 400

    def test_正常系_HTTP5xxステータスコードで初期化可能(self) -> None:
        """HTTP 5xx ステータスコードで初期化できること。"""
        error = BseAPIError(
            "Internal Server Error",
            url="https://api.bseindia.com/BseIndiaAPI/api/getScripHeaderData",
            status_code=500,
            response_body="Internal Server Error",
        )

        assert error.status_code == 500


# =============================================================================
# BseRateLimitError
# =============================================================================


class TestBseRateLimitError:
    """BseRateLimitError (レートリミット) のテスト。"""

    def test_正常系_全パラメータで初期化(self) -> None:
        """BseRateLimitError が全パラメータで初期化されること。"""
        error = BseRateLimitError(
            "Rate limit exceeded",
            url="https://api.bseindia.com/BseIndiaAPI/api/getScripHeaderData",
            retry_after=60,
        )

        assert error.message == "Rate limit exceeded"
        assert (
            error.url == "https://api.bseindia.com/BseIndiaAPI/api/getScripHeaderData"
        )
        assert error.retry_after == 60

    def test_正常系_BseErrorを継承している(self) -> None:
        """BseRateLimitError が BseError を継承していること。"""
        assert issubclass(BseRateLimitError, BseError)

        error = BseRateLimitError(
            "rate limited",
            url="https://api.bseindia.com/BseIndiaAPI/api/getScripHeaderData",
            retry_after=30,
        )
        assert isinstance(error, BseError)
        assert isinstance(error, Exception)

    def test_正常系_strでメッセージが表示される(self) -> None:
        """str() でエラーメッセージが表示されること。"""
        error = BseRateLimitError(
            "Too many requests, retry after 60s",
            url="https://api.bseindia.com/BseIndiaAPI/api/getScripHeaderData",
            retry_after=60,
        )

        assert "Too many requests, retry after 60s" in str(error)

    def test_正常系_BseErrorでキャッチできる(self) -> None:
        """BseError でキャッチできること。"""
        with pytest.raises(BseError):
            raise BseRateLimitError(
                "rate limited",
                url="https://api.bseindia.com/BseIndiaAPI/api/getScripHeaderData",
                retry_after=120,
            )

    def test_正常系_retry_afterがNoneでも初期化可能(self) -> None:
        """retry_after が None でも初期化できること。"""
        error = BseRateLimitError(
            "rate limited",
            url="https://api.bseindia.com/BseIndiaAPI/api/getScripHeaderData",
            retry_after=None,
        )

        assert error.retry_after is None

    def test_正常系_url属性がNoneでも初期化可能(self) -> None:
        """url が None でも初期化できること (リクエストURL不明の場合)。"""
        error = BseRateLimitError(
            "rate limited",
            url=None,
            retry_after=60,
        )

        assert error.url is None
        assert error.retry_after == 60


# =============================================================================
# BseParseError
# =============================================================================


class TestBseParseError:
    """BseParseError (パースエラー) のテスト。"""

    def test_正常系_全パラメータで初期化(self) -> None:
        """BseParseError が全パラメータで初期化されること。"""
        error = BseParseError(
            "Failed to parse scrip header response",
            raw_data='{"Table": null}',
            field="Table",
        )

        assert error.message == "Failed to parse scrip header response"
        assert error.raw_data == '{"Table": null}'
        assert error.field == "Table"

    def test_正常系_BseErrorを継承している(self) -> None:
        """BseParseError が BseError を継承していること。"""
        assert issubclass(BseParseError, BseError)

        error = BseParseError(
            "parse error",
            raw_data="bad data",
            field="scrip_code",
        )
        assert isinstance(error, BseError)
        assert isinstance(error, Exception)

    def test_正常系_strでメッセージが表示される(self) -> None:
        """str() でエラーメッセージが表示されること。"""
        error = BseParseError(
            "Unexpected response format",
            raw_data="not json",
            field="data",
        )

        assert "Unexpected response format" in str(error)

    def test_正常系_BseErrorでキャッチできる(self) -> None:
        """BseError でキャッチできること。"""
        with pytest.raises(BseError):
            raise BseParseError(
                "parse error",
                raw_data="bad",
                field="field",
            )

    def test_正常系_raw_dataがNoneでも初期化可能(self) -> None:
        """raw_data が None でも初期化できること。"""
        error = BseParseError(
            "parse error",
            raw_data=None,
            field="Table",
        )

        assert error.raw_data is None
        assert error.field == "Table"

    def test_正常系_field属性がNoneでも初期化可能(self) -> None:
        """field が None でも初期化できること。"""
        error = BseParseError(
            "parse error",
            raw_data="some data",
            field=None,
        )

        assert error.raw_data == "some data"
        assert error.field is None


# =============================================================================
# BseValidationError
# =============================================================================


class TestBseValidationError:
    """BseValidationError (バリデーションエラー) のテスト。"""

    def test_正常系_全パラメータで初期化(self) -> None:
        """BseValidationError が全パラメータで初期化されること。"""
        error = BseValidationError(
            "Invalid scrip code: must be a positive integer",
            field="scrip_code",
            value=-1,
        )

        assert error.message == "Invalid scrip code: must be a positive integer"
        assert error.field == "scrip_code"
        assert error.value == -1

    def test_正常系_BseErrorを継承している(self) -> None:
        """BseValidationError が BseError を継承していること。"""
        assert issubclass(BseValidationError, BseError)

        error = BseValidationError(
            "validation error",
            field="scrip_group",
            value="INVALID",
        )
        assert isinstance(error, BseError)
        assert isinstance(error, Exception)

    def test_正常系_strでメッセージが表示される(self) -> None:
        """str() でエラーメッセージが表示されること。"""
        error = BseValidationError(
            "Invalid scrip group",
            field="scrip_group",
            value="INVALID",
        )

        assert "Invalid scrip group" in str(error)

    def test_正常系_BseErrorでキャッチできる(self) -> None:
        """BseError でキャッチできること。"""
        with pytest.raises(BseError):
            raise BseValidationError(
                "validation error",
                field="scrip_code",
                value="abc",
            )

    def test_正常系_valueにNoneを設定可能(self) -> None:
        """value に None を設定できること。"""
        error = BseValidationError(
            "Missing required field",
            field="scrip_code",
            value=None,
        )

        assert error.value is None

    def test_正常系_valueに様々な型を設定可能(self) -> None:
        """value に様々な型（int, str, list）を設定できること。"""
        error_int = BseValidationError("invalid", field="code", value=42)
        assert error_int.value == 42

        error_str = BseValidationError("invalid", field="name", value="bad")
        assert error_str.value == "bad"

        error_list = BseValidationError("invalid", field="codes", value=[1, 2])
        assert error_list.value == [1, 2]


# =============================================================================
# Exception Hierarchy
# =============================================================================


class TestExceptionHierarchy:
    """例外クラスの継承階層テスト。"""

    def test_正常系_全サブクラスがBseErrorを継承(self) -> None:
        """全サブクラスが BseError を継承していること。"""
        assert issubclass(BseAPIError, BseError)
        assert issubclass(BseRateLimitError, BseError)
        assert issubclass(BseParseError, BseError)
        assert issubclass(BseValidationError, BseError)

    def test_正常系_BseErrorがExceptionを直接継承(self) -> None:
        """BseError が Exception を直接継承していること。"""
        assert issubclass(BseError, Exception)
        assert Exception in BseError.__bases__

    def test_正常系_サブクラスはExceptionのインスタンスである(self) -> None:
        """サブクラスのインスタンスが Exception のインスタンスであること。"""
        api_err = BseAPIError(
            "test",
            url="https://api.bseindia.com/BseIndiaAPI/api/getScripHeaderData",
            status_code=500,
            response_body="error",
        )
        assert isinstance(api_err, Exception)

        rate_err = BseRateLimitError(
            "test",
            url="https://api.bseindia.com/BseIndiaAPI/api/getScripHeaderData",
            retry_after=60,
        )
        assert isinstance(rate_err, Exception)

        parse_err = BseParseError(
            "test",
            raw_data="data",
            field="field",
        )
        assert isinstance(parse_err, Exception)

        val_err = BseValidationError(
            "test",
            field="scrip_code",
            value=-1,
        )
        assert isinstance(val_err, Exception)


# =============================================================================
# Usage Patterns
# =============================================================================


class TestExceptionUsagePatterns:
    """例外クラスの使用パターンテスト。"""

    def test_正常系_try_exceptで適切にキャッチできる(self) -> None:
        """try-except で適切にキャッチできること。"""

        def fetch_scrip(url: str) -> None:
            raise BseAPIError(
                f"Failed to fetch from {url}",
                url=url,
                status_code=500,
                response_body="Internal Server Error",
            )

        with pytest.raises(BseAPIError) as exc_info:
            fetch_scrip("https://api.bseindia.com/BseIndiaAPI/api/getScripHeaderData")

        assert (
            exc_info.value.url
            == "https://api.bseindia.com/BseIndiaAPI/api/getScripHeaderData"
        )

        with pytest.raises(BseError):
            fetch_scrip("https://api.bseindia.com/BseIndiaAPI/api/getScripHeaderData")

    def test_正常系_原因チェーンが機能する(self) -> None:
        """例外の from チェーンが正しく機能すること。"""
        original = ConnectionError("Connection refused")

        try:
            raise BseAPIError(
                "API request failed",
                url="https://api.bseindia.com/BseIndiaAPI/api/getScripHeaderData",
                status_code=503,
                response_body="Service Unavailable",
            ) from original
        except BseAPIError as e:
            assert e.__cause__ is original
            assert isinstance(e.__cause__, ConnectionError)

    def test_正常系_レートリミットのリトライパターン(self) -> None:
        """レートリミットエラーの retry_after を使用したリトライパターン。"""
        error = BseRateLimitError(
            "Rate limit exceeded",
            url="https://api.bseindia.com/BseIndiaAPI/api/getScripHeaderData",
            retry_after=30,
        )

        assert error.retry_after == 30

    def test_正常系_パースエラーのデバッグパターン(self) -> None:
        """パースエラーの raw_data と field を使用したデバッグパターン。"""
        raw = '{"Table": null}'
        error = BseParseError(
            "Expected list for Table field, got null",
            raw_data=raw,
            field="Table",
        )

        assert error.raw_data == raw
        assert error.field == "Table"

    def test_正常系_バリデーションエラーのデバッグパターン(self) -> None:
        """バリデーションエラーの field と value を使用したデバッグパターン。"""
        error = BseValidationError(
            "Expected positive integer for scrip_code",
            field="scrip_code",
            value=-1,
        )

        assert error.field == "scrip_code"
        assert error.value == -1


# =============================================================================
# Module Exports
# =============================================================================


class TestModuleExports:
    """__all__ エクスポートのテスト。"""

    def test_正常系_全クラスがエクスポートされている(self) -> None:
        """__all__ に全5クラスが含まれていること。"""
        from market.bse import errors

        assert hasattr(errors, "__all__")
        expected = {
            "BseError",
            "BseAPIError",
            "BseRateLimitError",
            "BseParseError",
            "BseValidationError",
        }
        assert set(errors.__all__) == expected
