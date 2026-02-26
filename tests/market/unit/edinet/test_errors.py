"""Unit tests for market.edinet.errors module.

Test TODO List:
- [x] EdinetError: base exception with message attribute
- [x] EdinetAPIError: HTTP 4xx/5xx (url, status_code, response_body)
- [x] EdinetRateLimitError: daily limit exceeded (calls_used, calls_limit)
- [x] EdinetValidationError: input validation (field, value)
- [x] EdinetParseError: response parse failure (raw_data)
- [x] Exception hierarchy verification
- [x] Usage patterns (try-except, base class catch)
"""

import pytest


class TestEdinetError:
    """Tests for EdinetError base exception."""

    def test_正常系_基本的な初期化(self) -> None:
        """EdinetError が基本パラメータで初期化されることを確認。"""
        from market.edinet.errors import EdinetError

        error = EdinetError("EDINET API operation failed")
        assert error.message == "EDINET API operation failed"
        assert str(error) == "EDINET API operation failed"

    def test_正常系_Exceptionを直接継承(self) -> None:
        """EdinetError が Exception を直接継承していることを確認。"""
        from market.edinet.errors import EdinetError

        assert issubclass(EdinetError, Exception)
        # 直接継承であること（MRO の2番目が Exception）
        assert EdinetError.__bases__ == (Exception,)

    def test_正常系_try_exceptでキャッチできる(self) -> None:
        """EdinetError が try-except でキャッチできることを確認。"""
        from market.edinet.errors import EdinetError

        with pytest.raises(EdinetError, match="test error"):
            raise EdinetError("test error")


class TestEdinetAPIError:
    """Tests for EdinetAPIError exception (HTTP 4xx/5xx)."""

    def test_正常系_全属性付きで初期化(self) -> None:
        """EdinetAPIError が全コンテキスト属性付きで初期化されることを確認。"""
        from market.edinet.errors import EdinetAPIError

        error = EdinetAPIError(
            "API returned HTTP 500",
            url="https://edinetdb.jp/v2/companies",
            status_code=500,
            response_body='{"error": "Internal Server Error"}',
        )
        assert error.message == "API returned HTTP 500"
        assert error.url == "https://edinetdb.jp/v2/companies"
        assert error.status_code == 500
        assert error.response_body == '{"error": "Internal Server Error"}'

    def test_正常系_str表現にmessageが含まれる(self) -> None:
        """str(EdinetAPIError) にメッセージが含まれることを確認。"""
        from market.edinet.errors import EdinetAPIError

        error = EdinetAPIError(
            "HTTP 403 Forbidden",
            url="https://edinetdb.jp/v2/companies",
            status_code=403,
            response_body="Forbidden",
        )
        assert str(error) == "HTTP 403 Forbidden"

    def test_正常系_EdinetErrorを継承(self) -> None:
        """EdinetAPIError が EdinetError を継承していることを確認。"""
        from market.edinet.errors import EdinetAPIError, EdinetError

        error = EdinetAPIError(
            "API error",
            url="https://edinetdb.jp/v2/companies",
            status_code=400,
            response_body="Bad Request",
        )
        assert isinstance(error, EdinetError)
        assert isinstance(error, Exception)


class TestEdinetRateLimitError:
    """Tests for EdinetRateLimitError exception (daily limit exceeded)."""

    def test_正常系_全属性付きで初期化(self) -> None:
        """EdinetRateLimitError が全コンテキスト属性付きで初期化されることを確認。"""
        from market.edinet.errors import EdinetRateLimitError

        error = EdinetRateLimitError(
            "Daily API limit exceeded",
            calls_used=1000,
            calls_limit=1000,
        )
        assert error.message == "Daily API limit exceeded"
        assert error.calls_used == 1000
        assert error.calls_limit == 1000

    def test_正常系_str表現にmessageが含まれる(self) -> None:
        """str(EdinetRateLimitError) にメッセージが含まれることを確認。"""
        from market.edinet.errors import EdinetRateLimitError

        error = EdinetRateLimitError(
            "Rate limit exceeded",
            calls_used=500,
            calls_limit=1000,
        )
        assert str(error) == "Rate limit exceeded"

    def test_正常系_EdinetErrorを継承(self) -> None:
        """EdinetRateLimitError が EdinetError を継承していることを確認。"""
        from market.edinet.errors import EdinetError, EdinetRateLimitError

        error = EdinetRateLimitError(
            "Rate limit",
            calls_used=100,
            calls_limit=1000,
        )
        assert isinstance(error, EdinetError)
        assert isinstance(error, Exception)


class TestEdinetValidationError:
    """Tests for EdinetValidationError exception (input validation)."""

    def test_正常系_全属性付きで初期化(self) -> None:
        """EdinetValidationError が全コンテキスト属性付きで初期化されることを確認。"""
        from market.edinet.errors import EdinetValidationError

        error = EdinetValidationError(
            "Invalid EDINET code format",
            field="edinet_code",
            value="INVALID",
        )
        assert error.message == "Invalid EDINET code format"
        assert error.field == "edinet_code"
        assert error.value == "INVALID"

    def test_正常系_valueがNoneの場合(self) -> None:
        """EdinetValidationError の value が None でも初期化されることを確認。"""
        from market.edinet.errors import EdinetValidationError

        error = EdinetValidationError(
            "Required field missing",
            field="edinet_code",
            value=None,
        )
        assert error.field == "edinet_code"
        assert error.value is None

    def test_正常系_str表現にmessageが含まれる(self) -> None:
        """str(EdinetValidationError) にメッセージが含まれることを確認。"""
        from market.edinet.errors import EdinetValidationError

        error = EdinetValidationError(
            "Invalid field",
            field="period",
            value="abc",
        )
        assert str(error) == "Invalid field"

    def test_正常系_EdinetErrorを継承(self) -> None:
        """EdinetValidationError が EdinetError を継承していることを確認。"""
        from market.edinet.errors import EdinetError, EdinetValidationError

        error = EdinetValidationError(
            "Validation error",
            field="test",
            value="x",
        )
        assert isinstance(error, EdinetError)
        assert isinstance(error, Exception)


class TestEdinetParseError:
    """Tests for EdinetParseError exception (response parse failure)."""

    def test_正常系_全属性付きで初期化(self) -> None:
        """EdinetParseError が全コンテキスト属性付きで初期化されることを確認。"""
        from market.edinet.errors import EdinetParseError

        error = EdinetParseError(
            "Failed to parse company list response",
            raw_data='{"unexpected": "format"}',
        )
        assert error.message == "Failed to parse company list response"
        assert error.raw_data == '{"unexpected": "format"}'

    def test_正常系_raw_dataがNoneの場合(self) -> None:
        """EdinetParseError の raw_data が None でも初期化されることを確認。"""
        from market.edinet.errors import EdinetParseError

        error = EdinetParseError(
            "Empty response body",
            raw_data=None,
        )
        assert error.raw_data is None

    def test_正常系_str表現にmessageが含まれる(self) -> None:
        """str(EdinetParseError) にメッセージが含まれることを確認。"""
        from market.edinet.errors import EdinetParseError

        error = EdinetParseError(
            "Parse failed",
            raw_data="not json",
        )
        assert str(error) == "Parse failed"

    def test_正常系_EdinetErrorを継承(self) -> None:
        """EdinetParseError が EdinetError を継承していることを確認。"""
        from market.edinet.errors import EdinetError, EdinetParseError

        error = EdinetParseError(
            "Parse error",
            raw_data="data",
        )
        assert isinstance(error, EdinetError)
        assert isinstance(error, Exception)


class TestExceptionHierarchy:
    """Tests for exception class hierarchy."""

    def test_正常系_例外階層が正しい(self) -> None:
        """例外クラスの継承関係が正しいことを確認。"""
        from market.edinet.errors import (
            EdinetAPIError,
            EdinetError,
            EdinetParseError,
            EdinetRateLimitError,
            EdinetValidationError,
        )

        # All specific errors inherit from EdinetError
        assert issubclass(EdinetAPIError, EdinetError)
        assert issubclass(EdinetRateLimitError, EdinetError)
        assert issubclass(EdinetValidationError, EdinetError)
        assert issubclass(EdinetParseError, EdinetError)

        # EdinetError inherits from Exception
        assert issubclass(EdinetError, Exception)

    def test_正常系_サブクラスはEdinetError同士で兄弟関係(self) -> None:
        """サブクラス同士が互いにサブクラス関係でないことを確認。"""
        from market.edinet.errors import (
            EdinetAPIError,
            EdinetParseError,
            EdinetRateLimitError,
            EdinetValidationError,
        )

        subclasses = [
            EdinetAPIError,
            EdinetRateLimitError,
            EdinetValidationError,
            EdinetParseError,
        ]
        for i, cls_a in enumerate(subclasses):
            for j, cls_b in enumerate(subclasses):
                if i != j:
                    assert not issubclass(cls_a, cls_b)


class TestExceptionUsagePatterns:
    """Tests for common exception usage patterns."""

    def test_正常系_基底クラスで全サブクラスをキャッチできる(self) -> None:
        """EdinetError で全サブクラスをキャッチできることを確認。"""
        from market.edinet.errors import (
            EdinetAPIError,
            EdinetError,
            EdinetParseError,
            EdinetRateLimitError,
            EdinetValidationError,
        )

        # EdinetAPIError
        with pytest.raises(EdinetError):
            raise EdinetAPIError(
                "API error",
                url="https://edinetdb.jp/v2/companies",
                status_code=500,
                response_body="error",
            )

        # EdinetRateLimitError
        with pytest.raises(EdinetError):
            raise EdinetRateLimitError(
                "Rate limit",
                calls_used=1000,
                calls_limit=1000,
            )

        # EdinetValidationError
        with pytest.raises(EdinetError):
            raise EdinetValidationError(
                "Validation",
                field="test",
                value="x",
            )

        # EdinetParseError
        with pytest.raises(EdinetError):
            raise EdinetParseError(
                "Parse",
                raw_data="data",
            )

    def test_正常系_特定のサブクラスでキャッチできる(self) -> None:
        """特定のサブクラスのみキャッチできることを確認。"""
        from market.edinet.errors import (
            EdinetAPIError,
            EdinetRateLimitError,
        )

        with pytest.raises(EdinetAPIError):
            raise EdinetAPIError(
                "API error",
                url="https://edinetdb.jp/v2/companies",
                status_code=500,
                response_body="error",
            )

        # EdinetAPIError は EdinetRateLimitError としてキャッチされない
        with pytest.raises(EdinetAPIError):
            try:
                raise EdinetAPIError(
                    "API error",
                    url="https://edinetdb.jp/v2/companies",
                    status_code=500,
                    response_body="error",
                )
            except EdinetRateLimitError:
                pytest.fail(
                    "EdinetAPIError should not be caught by EdinetRateLimitError"
                )
