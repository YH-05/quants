"""errors.py の単体テスト.

例外階層と isinstance チェックを検証する。
"""

from __future__ import annotations

import pytest

from academic.errors import (
    AcademicError,
    PaperNotFoundError,
    ParseError,
    PermanentError,
    RateLimitError,
    RetryableError,
)


class TestAcademicError:
    """AcademicError 基底例外のテスト."""

    def test_正常系_メッセージ付きで生成できる(self) -> None:
        """AcademicError をメッセージ付きで生成できることを確認。"""
        error = AcademicError("データ取得中にエラー")

        assert str(error) == "データ取得中にエラー"

    def test_正常系_Exceptionのサブクラスである(self) -> None:
        """AcademicError が Exception のサブクラスであることを確認。"""
        error = AcademicError("test")

        assert isinstance(error, Exception)

    def test_正常系_raiseできる(self) -> None:
        """AcademicError を raise できることを確認。"""
        with pytest.raises(AcademicError, match="エラーメッセージ"):
            raise AcademicError("エラーメッセージ")


class TestRetryableError:
    """RetryableError のテスト."""

    def test_正常系_メッセージのみで生成できる(self) -> None:
        """メッセージのみで RetryableError を生成できることを確認。"""
        error = RetryableError("Server error")

        assert str(error) == "Server error"
        assert error.status_code is None
        assert error.retry_after is None

    def test_正常系_status_code付きで生成できる(self) -> None:
        """status_code 付きで RetryableError を生成できることを確認。"""
        error = RetryableError("Server error", status_code=503)

        assert error.status_code == 503
        assert error.retry_after is None

    def test_正常系_retry_after付きで生成できる(self) -> None:
        """retry_after 付きで RetryableError を生成できることを確認。"""
        error = RetryableError("Rate limited", status_code=429, retry_after=30)

        assert error.status_code == 429
        assert error.retry_after == 30

    def test_正常系_AcademicErrorのサブクラスである(self) -> None:
        """RetryableError が AcademicError のサブクラスであることを確認。"""
        error = RetryableError("test")

        assert isinstance(error, AcademicError)

    def test_正常系_raiseできる(self) -> None:
        """RetryableError を raise できることを確認。"""
        with pytest.raises(RetryableError):
            raise RetryableError("timeout")

    def test_正常系_AcademicErrorとしてキャッチできる(self) -> None:
        """RetryableError を AcademicError としてキャッチできることを確認。"""
        with pytest.raises(AcademicError):
            raise RetryableError("timeout")


class TestPermanentError:
    """PermanentError のテスト."""

    def test_正常系_メッセージのみで生成できる(self) -> None:
        """メッセージのみで PermanentError を生成できることを確認。"""
        error = PermanentError("Not found")

        assert str(error) == "Not found"
        assert error.status_code is None

    def test_正常系_status_code付きで生成できる(self) -> None:
        """status_code 付きで PermanentError を生成できることを確認。"""
        error = PermanentError("Not found", status_code=404)

        assert error.status_code == 404

    def test_正常系_AcademicErrorのサブクラスである(self) -> None:
        """PermanentError が AcademicError のサブクラスであることを確認。"""
        error = PermanentError("test")

        assert isinstance(error, AcademicError)

    def test_正常系_RetryableErrorとは無関係(self) -> None:
        """PermanentError が RetryableError のサブクラスでないことを確認。"""
        error = PermanentError("test")

        assert not isinstance(error, RetryableError)

    def test_正常系_raiseできる(self) -> None:
        """PermanentError を raise できることを確認。"""
        with pytest.raises(PermanentError, match="forbidden"):
            raise PermanentError("forbidden", status_code=403)


class TestRateLimitError:
    """RateLimitError のテスト."""

    def test_正常系_全フィールドで生成できる(self) -> None:
        """全フィールドで RateLimitError を生成できることを確認。"""
        error = RateLimitError("Too Many Requests", status_code=429, retry_after=60)

        assert str(error) == "Too Many Requests"
        assert error.status_code == 429
        assert error.retry_after == 60

    def test_正常系_RetryableErrorのサブクラスである(self) -> None:
        """RateLimitError が RetryableError のサブクラスであることを確認。"""
        error = RateLimitError("rate limited")

        assert isinstance(error, RetryableError)

    def test_正常系_AcademicErrorのサブクラスである(self) -> None:
        """RateLimitError が AcademicError のサブクラスであることを確認。"""
        error = RateLimitError("rate limited")

        assert isinstance(error, AcademicError)

    def test_正常系_retry_afterがNoneのデフォルト(self) -> None:
        """retry_after のデフォルトが None であることを確認。"""
        error = RateLimitError("rate limited", status_code=429)

        assert error.retry_after is None

    def test_正常系_raiseできる(self) -> None:
        """RateLimitError を raise できることを確認。"""
        with pytest.raises(RateLimitError):
            raise RateLimitError("too many requests", status_code=429, retry_after=30)

    def test_正常系_RetryableErrorとしてキャッチできる(self) -> None:
        """RateLimitError を RetryableError としてキャッチできることを確認。"""
        with pytest.raises(RetryableError):
            raise RateLimitError("rate limited", status_code=429)


class TestPaperNotFoundError:
    """PaperNotFoundError のテスト."""

    def test_正常系_メッセージとstatus_codeで生成できる(self) -> None:
        """メッセージと status_code で PaperNotFoundError を生成できることを確認。"""
        error = PaperNotFoundError("論文が見つかりません", status_code=404)

        assert str(error) == "論文が見つかりません"
        assert error.status_code == 404

    def test_正常系_PermanentErrorのサブクラスである(self) -> None:
        """PaperNotFoundError が PermanentError のサブクラスであることを確認。"""
        error = PaperNotFoundError("not found")

        assert isinstance(error, PermanentError)

    def test_正常系_AcademicErrorのサブクラスである(self) -> None:
        """PaperNotFoundError が AcademicError のサブクラスであることを確認。"""
        error = PaperNotFoundError("not found")

        assert isinstance(error, AcademicError)

    def test_正常系_RetryableErrorではない(self) -> None:
        """PaperNotFoundError が RetryableError のサブクラスでないことを確認。"""
        error = PaperNotFoundError("not found")

        assert not isinstance(error, RetryableError)

    def test_正常系_raiseできる(self) -> None:
        """PaperNotFoundError を raise できることを確認。"""
        with pytest.raises(PaperNotFoundError, match=r"2301\.00001"):
            raise PaperNotFoundError(
                "論文が見つかりません: 2301.00001", status_code=404
            )

    def test_正常系_PermanentErrorとしてキャッチできる(self) -> None:
        """PaperNotFoundError を PermanentError としてキャッチできることを確認。"""
        with pytest.raises(PermanentError):
            raise PaperNotFoundError("not found", status_code=404)


class TestParseError:
    """ParseError のテスト."""

    def test_正常系_メッセージ付きで生成できる(self) -> None:
        """メッセージ付きで ParseError を生成できることを確認。"""
        error = ParseError("XML パースに失敗しました")

        assert str(error) == "XML パースに失敗しました"

    def test_正常系_AcademicErrorのサブクラスである(self) -> None:
        """ParseError が AcademicError のサブクラスであることを確認。"""
        error = ParseError("parse failed")

        assert isinstance(error, AcademicError)

    def test_正常系_RetryableErrorではない(self) -> None:
        """ParseError が RetryableError のサブクラスでないことを確認。"""
        error = ParseError("parse failed")

        assert not isinstance(error, RetryableError)

    def test_正常系_PermanentErrorではない(self) -> None:
        """ParseError が PermanentError のサブクラスでないことを確認。"""
        error = ParseError("parse failed")

        assert not isinstance(error, PermanentError)

    def test_正常系_raiseできる(self) -> None:
        """ParseError を raise できることを確認。"""
        with pytest.raises(ParseError):
            raise ParseError("パース失敗")

    def test_正常系_AcademicErrorとしてキャッチできる(self) -> None:
        """ParseError を AcademicError としてキャッチできることを確認。"""
        with pytest.raises(AcademicError):
            raise ParseError("parse failed")


class TestExceptionHierarchy:
    """例外階層の全体テスト."""

    def test_正常系_階層の整合性_RateLimitErrorはRetryableError(self) -> None:
        """RateLimitError が RetryableError のサブクラスであることを確認。"""
        assert issubclass(RateLimitError, RetryableError)

    def test_正常系_階層の整合性_PaperNotFoundErrorはPermanentError(self) -> None:
        """PaperNotFoundError が PermanentError のサブクラスであることを確認。"""
        assert issubclass(PaperNotFoundError, PermanentError)

    def test_正常系_階層の整合性_RetryableErrorはAcademicError(self) -> None:
        """RetryableError が AcademicError のサブクラスであることを確認。"""
        assert issubclass(RetryableError, AcademicError)

    def test_正常系_階層の整合性_PermanentErrorはAcademicError(self) -> None:
        """PermanentError が AcademicError のサブクラスであることを確認。"""
        assert issubclass(PermanentError, AcademicError)

    def test_正常系_階層の整合性_ParseErrorはAcademicError(self) -> None:
        """ParseError が AcademicError のサブクラスであることを確認。"""
        assert issubclass(ParseError, AcademicError)

    def test_正常系_全例外をAcademicErrorで一括キャッチできる(self) -> None:
        """全例外を AcademicError で一括キャッチできることを確認。"""
        exceptions_to_test = [
            RetryableError("test"),
            PermanentError("test"),
            RateLimitError("test"),
            PaperNotFoundError("test"),
            ParseError("test"),
        ]

        for exc in exceptions_to_test:
            assert isinstance(exc, AcademicError), (
                f"{type(exc).__name__} は AcademicError のサブクラスである必要があります"
            )
