"""retry.py の単体テスト.

classify_http_error() と create_retry_decorator() の動作を検証する。
"""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from news_scraper.exceptions import (
    BotDetectionError,
    PermanentError,
    RateLimitError,
    RetryableError,
    ScraperError,
)
from news_scraper.retry import classify_http_error, create_retry_decorator


class TestClassifyHttpError:
    """classify_http_error() のテスト."""

    @pytest.fixture
    def mock_response_no_retry_after(self) -> MagicMock:
        """Retry-After ヘッダなしのモックレスポンスを返すフィクスチャ."""
        response = MagicMock()
        response.headers = {}
        return response

    @pytest.fixture
    def mock_response_with_retry_after(self) -> MagicMock:
        """Retry-After: 60 ヘッダ付きのモックレスポンスを返すフィクスチャ."""
        response = MagicMock()
        response.headers = {"Retry-After": "60"}
        return response

    def test_正常系_429がRateLimitErrorに分類される(
        self, mock_response_with_retry_after: MagicMock
    ) -> None:
        """HTTP 429 が RateLimitError に分類されることを確認。"""
        error = classify_http_error(429, mock_response_with_retry_after)

        assert isinstance(error, RateLimitError)
        assert error.status_code == 429

    def test_正常系_429でretry_afterが設定される(
        self, mock_response_with_retry_after: MagicMock
    ) -> None:
        """HTTP 429 で Retry-After ヘッダが parse されることを確認。"""
        error = classify_http_error(429, mock_response_with_retry_after)

        assert isinstance(error, RateLimitError)
        assert error.retry_after == 60

    def test_正常系_429でRetryAfterなしのとき_retry_afterはNone(
        self, mock_response_no_retry_after: MagicMock
    ) -> None:
        """HTTP 429 で Retry-After ヘッダがない場合 retry_after が None になることを確認。"""
        error = classify_http_error(429, mock_response_no_retry_after)

        assert isinstance(error, RateLimitError)
        assert error.retry_after is None

    def test_正常系_403がBotDetectionErrorに分類される(
        self, mock_response_no_retry_after: MagicMock
    ) -> None:
        """HTTP 403 が BotDetectionError に分類されることを確認。"""
        error = classify_http_error(403, mock_response_no_retry_after)

        assert isinstance(error, BotDetectionError)
        assert error.status_code == 403

    def test_正常系_404がPermanentErrorに分類される(
        self, mock_response_no_retry_after: MagicMock
    ) -> None:
        """HTTP 404 が PermanentError に分類されることを確認。"""
        error = classify_http_error(404, mock_response_no_retry_after)

        assert isinstance(error, PermanentError)
        assert error.status_code == 404

    def test_正常系_500がRetryableErrorに分類される(
        self, mock_response_no_retry_after: MagicMock
    ) -> None:
        """HTTP 500 が RetryableError に分類されることを確認。"""
        error = classify_http_error(500, mock_response_no_retry_after)

        assert isinstance(error, RetryableError)
        assert error.status_code == 500

    def test_正常系_502がRetryableErrorに分類される(
        self, mock_response_no_retry_after: MagicMock
    ) -> None:
        """HTTP 502 が RetryableError に分類されることを確認。"""
        error = classify_http_error(502, mock_response_no_retry_after)

        assert isinstance(error, RetryableError)
        assert error.status_code == 502

    def test_正常系_503がRetryableErrorに分類される(
        self, mock_response_no_retry_after: MagicMock
    ) -> None:
        """HTTP 503 が RetryableError に分類されることを確認。"""
        error = classify_http_error(503, mock_response_no_retry_after)

        assert isinstance(error, RetryableError)
        assert error.status_code == 503

    def test_正常系_504がRetryableErrorに分類される(
        self, mock_response_no_retry_after: MagicMock
    ) -> None:
        """HTTP 504 が RetryableError に分類されることを確認。"""
        error = classify_http_error(504, mock_response_no_retry_after)

        assert isinstance(error, RetryableError)
        assert error.status_code == 504

    def test_正常系_その他のステータスコードがPermanentErrorに分類される(
        self, mock_response_no_retry_after: MagicMock
    ) -> None:
        """200 や 301 などその他のコードが PermanentError に分類されることを確認。"""
        error = classify_http_error(400, mock_response_no_retry_after)

        assert isinstance(error, PermanentError)
        assert error.status_code == 400

    def test_正常系_戻り値がScraperErrorのサブクラスである(
        self, mock_response_no_retry_after: MagicMock
    ) -> None:
        """classify_http_error() の戻り値が ScraperError のサブクラスであることを確認。"""
        for status in [403, 404, 429, 500, 503]:
            error = classify_http_error(status, mock_response_no_retry_after)
            assert isinstance(error, ScraperError), (
                f"status={status} の戻り値が ScraperError のサブクラスではありません"
            )

    def test_正常系_403はRetryableErrorではない(
        self, mock_response_no_retry_after: MagicMock
    ) -> None:
        """HTTP 403 が RetryableError のサブクラスでないことを確認。"""
        error = classify_http_error(403, mock_response_no_retry_after)

        assert not isinstance(error, RetryableError)

    def test_正常系_404はRetryableErrorではない(
        self, mock_response_no_retry_after: MagicMock
    ) -> None:
        """HTTP 404 が RetryableError のサブクラスでないことを確認。"""
        error = classify_http_error(404, mock_response_no_retry_after)

        assert not isinstance(error, RetryableError)


class TestCreateRetryDecorator:
    """create_retry_decorator() のテスト."""

    def test_正常系_デフォルト引数でデコレータを生成できる(self) -> None:
        """デフォルト引数でリトライデコレータを生成できることを確認。"""
        decorator = create_retry_decorator()

        assert decorator is not None

    def test_正常系_カスタム引数でデコレータを生成できる(self) -> None:
        """カスタム引数でリトライデコレータを生成できることを確認。"""
        decorator = create_retry_decorator(max_attempts=5, base_wait=2.0, max_wait=60.0)

        assert decorator is not None

    def test_正常系_デコレータが関数に適用できる(self) -> None:
        """デコレータを関数に適用できることを確認。"""
        retry = create_retry_decorator(max_attempts=1)

        @retry
        def sample_func() -> str:
            return "success"

        result = sample_func()
        assert result == "success"

    def test_正常系_RetryableError発生時にリトライする(self) -> None:
        """RetryableError が発生したときにリトライすることを確認。"""
        call_count = 0

        retry = create_retry_decorator(
            max_attempts=3,
            base_wait=0.001,
            max_wait=0.01,
        )

        @retry
        def flaky_func() -> str:
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise RetryableError("temporary error")
            return "success"

        result = flaky_func()

        assert result == "success"
        assert call_count == 3

    def test_正常系_PermanentError発生時はリトライしない(self) -> None:
        """PermanentError が発生したときリトライせずに即座に再送出することを確認。"""
        call_count = 0

        retry = create_retry_decorator(
            max_attempts=3,
            base_wait=0.001,
            max_wait=0.01,
        )

        @retry
        def permanent_fail() -> str:
            nonlocal call_count
            call_count += 1
            raise PermanentError("permanent failure", status_code=404)

        with pytest.raises(PermanentError):
            permanent_fail()

        # リトライしないので1回のみ
        assert call_count == 1

    def test_正常系_最大試行回数を超えたらRetryableErrorを送出する(self) -> None:
        """最大試行回数を超えたときに RetryableError を送出することを確認。"""
        call_count = 0

        retry = create_retry_decorator(
            max_attempts=3,
            base_wait=0.001,
            max_wait=0.01,
        )

        @retry
        def always_fail() -> str:
            nonlocal call_count
            call_count += 1
            raise RetryableError("always fails")

        with pytest.raises(RetryableError):
            always_fail()

        assert call_count == 3

    def test_正常系_ScraperError以外の例外はリトライしない(self) -> None:
        """ScraperError 以外の例外はリトライせずに即座に再送出することを確認。"""
        call_count = 0

        retry = create_retry_decorator(
            max_attempts=3,
            base_wait=0.001,
            max_wait=0.01,
        )

        @retry
        def raises_value_error() -> str:
            nonlocal call_count
            call_count += 1
            raise ValueError("not a scraper error")

        with pytest.raises(ValueError, match="not a scraper error"):
            raises_value_error()

        assert call_count == 1
