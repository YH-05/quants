"""exceptions.py の単体テスト.

例外階層と isinstance チェックを検証する。
"""

from __future__ import annotations

import pytest

from news_scraper.exceptions import (
    BotDetectionError,
    ContentExtractionError,
    PermanentError,
    RateLimitError,
    RetryableError,
    ScraperError,
)


class TestScraperError:
    """ScraperError 基底例外のテスト."""

    def test_正常系_メッセージ付きで生成できる(self) -> None:
        """ScraperError をメッセージ付きで生成できることを確認。"""
        error = ScraperError("スクレイピング中にエラー")

        assert str(error) == "スクレイピング中にエラー"

    def test_正常系_Exceptionのサブクラスである(self) -> None:
        """ScraperError が Exception のサブクラスであることを確認。"""
        error = ScraperError("test")

        assert isinstance(error, Exception)

    def test_正常系_raiseできる(self) -> None:
        """ScraperError を raise できることを確認。"""
        with pytest.raises(ScraperError, match="エラーメッセージ"):
            raise ScraperError("エラーメッセージ")


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

    def test_正常系_ScraperErrorのサブクラスである(self) -> None:
        """RetryableError が ScraperError のサブクラスであることを確認。"""
        error = RetryableError("test")

        assert isinstance(error, ScraperError)

    def test_正常系_raiseできる(self) -> None:
        """RetryableError を raise できることを確認。"""
        with pytest.raises(RetryableError):
            raise RetryableError("timeout")

    def test_正常系_ScraperErrorとしてキャッチできる(self) -> None:
        """RetryableError を ScraperError としてキャッチできることを確認。"""
        with pytest.raises(ScraperError):
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

    def test_正常系_ScraperErrorのサブクラスである(self) -> None:
        """PermanentError が ScraperError のサブクラスであることを確認。"""
        error = PermanentError("test")

        assert isinstance(error, ScraperError)

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

    def test_正常系_ScraperErrorのサブクラスである(self) -> None:
        """RateLimitError が ScraperError のサブクラスであることを確認。"""
        error = RateLimitError("rate limited")

        assert isinstance(error, ScraperError)

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


class TestBotDetectionError:
    """BotDetectionError のテスト."""

    def test_正常系_メッセージとstatus_codeで生成できる(self) -> None:
        """メッセージと status_code で BotDetectionError を生成できることを確認。"""
        error = BotDetectionError("Bot detected", status_code=403)

        assert str(error) == "Bot detected"
        assert error.status_code == 403

    def test_正常系_PermanentErrorのサブクラスである(self) -> None:
        """BotDetectionError が PermanentError のサブクラスであることを確認。"""
        error = BotDetectionError("bot blocked")

        assert isinstance(error, PermanentError)

    def test_正常系_ScraperErrorのサブクラスである(self) -> None:
        """BotDetectionError が ScraperError のサブクラスであることを確認。"""
        error = BotDetectionError("bot blocked")

        assert isinstance(error, ScraperError)

    def test_正常系_RetryableErrorではない(self) -> None:
        """BotDetectionError が RetryableError のサブクラスでないことを確認。"""
        error = BotDetectionError("bot blocked")

        assert not isinstance(error, RetryableError)

    def test_正常系_raiseできる(self) -> None:
        """BotDetectionError を raise できることを確認。"""
        with pytest.raises(BotDetectionError, match="ボット検知"):
            raise BotDetectionError("ボット検知によりブロック", status_code=403)

    def test_正常系_PermanentErrorとしてキャッチできる(self) -> None:
        """BotDetectionError を PermanentError としてキャッチできることを確認。"""
        with pytest.raises(PermanentError):
            raise BotDetectionError("bot blocked", status_code=403)


class TestContentExtractionError:
    """ContentExtractionError のテスト."""

    def test_正常系_メッセージ付きで生成できる(self) -> None:
        """メッセージ付きで ContentExtractionError を生成できることを確認。"""
        error = ContentExtractionError("本文要素が見つかりません")

        assert str(error) == "本文要素が見つかりません"

    def test_正常系_ScraperErrorのサブクラスである(self) -> None:
        """ContentExtractionError が ScraperError のサブクラスであることを確認。"""
        error = ContentExtractionError("extraction failed")

        assert isinstance(error, ScraperError)

    def test_正常系_RetryableErrorではない(self) -> None:
        """ContentExtractionError が RetryableError のサブクラスでないことを確認。"""
        error = ContentExtractionError("extraction failed")

        assert not isinstance(error, RetryableError)

    def test_正常系_PermanentErrorではない(self) -> None:
        """ContentExtractionError が PermanentError のサブクラスでないことを確認。"""
        error = ContentExtractionError("extraction failed")

        assert not isinstance(error, PermanentError)

    def test_正常系_raiseできる(self) -> None:
        """ContentExtractionError を raise できることを確認。"""
        with pytest.raises(ContentExtractionError):
            raise ContentExtractionError("本文抽出失敗")

    def test_正常系_ScraperErrorとしてキャッチできる(self) -> None:
        """ContentExtractionError を ScraperError としてキャッチできることを確認。"""
        with pytest.raises(ScraperError):
            raise ContentExtractionError("extraction failed")


class TestExceptionHierarchy:
    """例外階層の全体テスト."""

    def test_正常系_階層の整合性_RateLimitErrorはRetryableError(self) -> None:
        """RateLimitError が RetryableError のサブクラスであることを確認。"""
        assert issubclass(RateLimitError, RetryableError)

    def test_正常系_階層の整合性_BotDetectionErrorはPermanentError(self) -> None:
        """BotDetectionError が PermanentError のサブクラスであることを確認。"""
        assert issubclass(BotDetectionError, PermanentError)

    def test_正常系_階層の整合性_RetryableErrorはScraperError(self) -> None:
        """RetryableError が ScraperError のサブクラスであることを確認。"""
        assert issubclass(RetryableError, ScraperError)

    def test_正常系_階層の整合性_PermanentErrorはScraperError(self) -> None:
        """PermanentError が ScraperError のサブクラスであることを確認。"""
        assert issubclass(PermanentError, ScraperError)

    def test_正常系_階層の整合性_ContentExtractionErrorはScraperError(self) -> None:
        """ContentExtractionError が ScraperError のサブクラスであることを確認。"""
        assert issubclass(ContentExtractionError, ScraperError)

    def test_正常系_全例外をScraperErrorで一括キャッチできる(self) -> None:
        """全例外を ScraperError で一括キャッチできることを確認。"""
        exceptions_to_test = [
            RetryableError("test"),
            PermanentError("test"),
            RateLimitError("test"),
            BotDetectionError("test"),
            ContentExtractionError("test"),
        ]

        for exc in exceptions_to_test:
            assert isinstance(exc, ScraperError), (
                f"{type(exc).__name__} は ScraperError のサブクラスである必要があります"
            )
