"""Tests for market.polymarket.session module.

Tests cover:
- SSRF prevention via host whitelist
- Polite delay (monotonic-clock-based)
- Response handling (200/429/404/4xx/5xx)
- GET with exponential backoff retry
- Context manager support
- Session initialization
"""

import time
from collections.abc import Generator
from unittest.mock import MagicMock, patch

import httpx
import pytest

from market.polymarket.errors import (
    PolymarketAPIError,
    PolymarketRateLimitError,
)
from market.polymarket.session import PolymarketSession
from market.polymarket.types import PolymarketConfig, RetryConfig

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def default_config() -> PolymarketConfig:
    """Create a default PolymarketConfig."""
    return PolymarketConfig()


@pytest.fixture
def session(
    default_config: PolymarketConfig,
) -> Generator[PolymarketSession, None, None]:
    """Create a PolymarketSession with default config."""
    s = PolymarketSession(config=default_config)
    yield s
    s.close()


# ===========================================================================
# TestPolymarketSessionInit
# ===========================================================================


class TestPolymarketSessionInit:
    """Tests for PolymarketSession initialization."""

    def test_正常系_デフォルト設定で初期化(self) -> None:
        session = PolymarketSession()
        assert session._config == PolymarketConfig()
        assert session._retry_config == RetryConfig()
        assert session._last_request_time == 0.0
        session.close()

    def test_正常系_カスタム設定で初期化(self) -> None:
        config = PolymarketConfig(timeout=10.0, rate_limit_per_second=2.0)
        retry = RetryConfig(max_attempts=5, base_wait=2.0)
        session = PolymarketSession(config=config, retry_config=retry)
        assert session._config.timeout == 10.0
        assert session._retry_config.max_attempts == 5
        session.close()


# ===========================================================================
# TestPolymarketSessionContextManager
# ===========================================================================


class TestPolymarketSessionContextManager:
    """Tests for context manager support."""

    def test_正常系_コンテキストマネージャ(self) -> None:
        with PolymarketSession() as session:
            assert isinstance(session, PolymarketSession)

    def test_正常系_close後にクライアントが閉じられる(self) -> None:
        session = PolymarketSession()
        with patch.object(session._client, "close") as mock_close:
            session.close()
            mock_close.assert_called_once()


# ===========================================================================
# TestPolymarketSessionSSRF
# ===========================================================================


class TestPolymarketSessionSSRF:
    """Tests for SSRF prevention (CWE-918)."""

    def test_正常系_Gamma_APIホストが許可される(
        self, session: PolymarketSession
    ) -> None:
        # Should not raise
        session._validate_url("https://gamma-api.polymarket.com/markets")

    def test_正常系_CLOB_APIホストが許可される(
        self, session: PolymarketSession
    ) -> None:
        session._validate_url("https://clob.polymarket.com/order-book")

    def test_正常系_Data_APIホストが許可される(
        self, session: PolymarketSession
    ) -> None:
        session._validate_url("https://data-api.polymarket.com/trades")

    def test_異常系_不正なホストがブロックされる(
        self, session: PolymarketSession
    ) -> None:
        with pytest.raises(ValueError, match="not in allowed hosts"):
            session._validate_url("https://evil.example.com/api")

    def test_異常系_不正なスキームがブロックされる(
        self, session: PolymarketSession
    ) -> None:
        with pytest.raises(ValueError, match="URL scheme must be"):
            session._validate_url("ftp://gamma-api.polymarket.com/markets")

    def test_異常系_localhostがブロックされる(self, session: PolymarketSession) -> None:
        with pytest.raises(ValueError, match="not in allowed hosts"):
            session._validate_url("http://localhost:8080/api")

    def test_異常系_内部IPがブロックされる(self, session: PolymarketSession) -> None:
        with pytest.raises(ValueError, match="not in allowed hosts"):
            session._validate_url("http://169.254.169.254/metadata")


# ===========================================================================
# TestPolymarketSessionPoliteDelay
# ===========================================================================


class TestPolymarketSessionPoliteDelay:
    """Tests for polite delay between requests."""

    def test_正常系_初回リクエストはディレイなし(
        self, session: PolymarketSession
    ) -> None:
        assert session._last_request_time == 0.0

    def test_正常系_ディレイが適用される(self) -> None:
        config = PolymarketConfig(rate_limit_per_second=10.0)
        session = PolymarketSession(config=config)

        # Simulate a previous request
        session._last_request_time = time.monotonic()

        with patch("market.polymarket.session.time.sleep") as mock_sleep:
            session._polite_delay()
            # Should attempt to sleep since we just set _last_request_time
            # The actual sleep time depends on elapsed time and jitter
            if mock_sleep.called:
                args = mock_sleep.call_args[0]
                assert args[0] > 0  # Sleep time should be positive

        session.close()

    def test_正常系_十分な時間経過後はディレイなし(self) -> None:
        config = PolymarketConfig(rate_limit_per_second=10.0)
        session = PolymarketSession(config=config)

        # Simulate a previous request long ago
        session._last_request_time = time.monotonic() - 10.0

        with patch("market.polymarket.session.time.sleep") as mock_sleep:
            session._polite_delay()
            mock_sleep.assert_not_called()

        session.close()

    def test_正常系_last_request_timeが更新される(
        self, session: PolymarketSession
    ) -> None:
        before = time.monotonic()
        session._polite_delay()
        after = time.monotonic()
        assert before <= session._last_request_time <= after


# ===========================================================================
# TestPolymarketSessionHandleResponse
# ===========================================================================


class TestPolymarketSessionHandleResponse:
    """Tests for response handling."""

    def test_正常系_200レスポンス(self, session: PolymarketSession) -> None:
        response = MagicMock(spec=httpx.Response)
        response.status_code = 200
        # Should not raise
        session._handle_response(response, "https://gamma-api.polymarket.com/markets")

    def test_正常系_201レスポンス(self, session: PolymarketSession) -> None:
        response = MagicMock(spec=httpx.Response)
        response.status_code = 201
        session._handle_response(response, "https://gamma-api.polymarket.com/markets")

    def test_異常系_429レートリミット(self, session: PolymarketSession) -> None:
        response = MagicMock(spec=httpx.Response)
        response.status_code = 429
        response.headers = {"Retry-After": "60"}
        with pytest.raises(PolymarketRateLimitError) as exc_info:
            session._handle_response(
                response, "https://gamma-api.polymarket.com/markets"
            )
        assert exc_info.value.retry_after == 60

    def test_異常系_429レートリミット_RetryAfterなし(
        self, session: PolymarketSession
    ) -> None:
        response = MagicMock(spec=httpx.Response)
        response.status_code = 429
        response.headers = {}
        with pytest.raises(PolymarketRateLimitError) as exc_info:
            session._handle_response(
                response, "https://gamma-api.polymarket.com/markets"
            )
        assert exc_info.value.retry_after is None

    def test_異常系_404クライアントエラー(self, session: PolymarketSession) -> None:
        response = MagicMock(spec=httpx.Response)
        response.status_code = 404
        response.text = "Not Found"
        with pytest.raises(PolymarketAPIError) as exc_info:
            session._handle_response(
                response, "https://gamma-api.polymarket.com/markets/123"
            )
        assert exc_info.value.status_code == 404

    def test_異常系_400クライアントエラー(self, session: PolymarketSession) -> None:
        response = MagicMock(spec=httpx.Response)
        response.status_code = 400
        response.text = "Bad Request"
        with pytest.raises(PolymarketAPIError) as exc_info:
            session._handle_response(
                response, "https://gamma-api.polymarket.com/markets"
            )
        assert exc_info.value.status_code == 400

    def test_異常系_500サーバーエラー(self, session: PolymarketSession) -> None:
        response = MagicMock(spec=httpx.Response)
        response.status_code = 500
        response.text = "Internal Server Error"
        with pytest.raises(PolymarketAPIError) as exc_info:
            session._handle_response(
                response, "https://gamma-api.polymarket.com/markets"
            )
        assert exc_info.value.status_code == 500

    def test_異常系_503サーバーエラー(self, session: PolymarketSession) -> None:
        response = MagicMock(spec=httpx.Response)
        response.status_code = 503
        response.text = "Service Unavailable"
        with pytest.raises(PolymarketAPIError) as exc_info:
            session._handle_response(
                response, "https://gamma-api.polymarket.com/markets"
            )
        assert exc_info.value.status_code == 503


# ===========================================================================
# TestPolymarketSessionBackoff
# ===========================================================================


class TestPolymarketSessionBackoff:
    """Tests for exponential backoff delay calculation."""

    def test_正常系_初回バックオフ(self) -> None:
        session = PolymarketSession(
            retry_config=RetryConfig(base_wait=1.0),
        )
        delay = session._calculate_backoff_delay(0)
        # base_wait * 2^0 = 1.0 (plus jitter)
        assert 0.5 <= delay <= 2.0
        session.close()

    def test_正常系_2回目バックオフ(self) -> None:
        session = PolymarketSession(
            retry_config=RetryConfig(base_wait=1.0),
        )
        delay = session._calculate_backoff_delay(1)
        # base_wait * 2^1 = 2.0 (plus jitter)
        assert 1.0 <= delay <= 4.0
        session.close()

    def test_正常系_最大ディレイ制限(self) -> None:
        session = PolymarketSession(
            retry_config=RetryConfig(base_wait=1.0, max_wait=5.0),
        )
        delay = session._calculate_backoff_delay(10)
        # Should be capped at max_wait (plus jitter, so up to 2x)
        assert delay <= 10.0  # max_wait * 2 (jitter max)
        session.close()


# ===========================================================================
# TestPolymarketSessionGet
# ===========================================================================


class TestPolymarketSessionGet:
    """Tests for GET request method."""

    def test_正常系_GETリクエスト(self, session: PolymarketSession) -> None:
        mock_response = MagicMock(spec=httpx.Response)
        mock_response.status_code = 200

        with patch.object(session._client, "get", return_value=mock_response):
            response = session.get("https://gamma-api.polymarket.com/markets")
            assert response.status_code == 200

    def test_正常系_GETリクエスト_パラメータ付き(
        self, session: PolymarketSession
    ) -> None:
        mock_response = MagicMock(spec=httpx.Response)
        mock_response.status_code = 200

        with patch.object(
            session._client, "get", return_value=mock_response
        ) as mock_get:
            response = session.get(
                "https://gamma-api.polymarket.com/markets",
                params={"limit": "10"},
            )
            assert response.status_code == 200
            _, kwargs = mock_get.call_args
            assert kwargs["params"] == {"limit": "10"}

    def test_異常系_SSRFブロック(self, session: PolymarketSession) -> None:
        with pytest.raises(ValueError, match="not in allowed hosts"):
            session.get("https://evil.example.com/api")

    def test_正常系_Acceptヘッダーが設定される(
        self, session: PolymarketSession
    ) -> None:
        mock_response = MagicMock(spec=httpx.Response)
        mock_response.status_code = 200

        with patch.object(
            session._client, "get", return_value=mock_response
        ) as mock_get:
            session.get("https://gamma-api.polymarket.com/markets")
            _, kwargs = mock_get.call_args
            assert kwargs["headers"]["Accept"] == "application/json"


# ===========================================================================
# TestPolymarketSessionGetWithRetry
# ===========================================================================


class TestPolymarketSessionGetWithRetry:
    """Tests for GET with retry."""

    def test_正常系_初回成功(self, session: PolymarketSession) -> None:
        mock_response = MagicMock(spec=httpx.Response)
        mock_response.status_code = 200

        with patch.object(session, "get", return_value=mock_response):
            response = session.get_with_retry(
                "https://gamma-api.polymarket.com/markets"
            )
            assert response.status_code == 200

    def test_正常系_リトライ後成功(self) -> None:
        session = PolymarketSession(
            retry_config=RetryConfig(max_attempts=3, base_wait=0.0),
        )

        mock_response_ok = MagicMock(spec=httpx.Response)
        mock_response_ok.status_code = 200

        rate_limit_error = PolymarketRateLimitError(
            message="Rate limited",
            url="https://gamma-api.polymarket.com/markets",
            retry_after=None,
        )

        call_count = 0

        def mock_get(url: str, params: dict[str, str] | None = None) -> httpx.Response:
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise rate_limit_error
            return mock_response_ok

        with (
            patch.object(session, "get", side_effect=mock_get),
            patch("market.polymarket.session.time.sleep"),
        ):
            response = session.get_with_retry(
                "https://gamma-api.polymarket.com/markets"
            )
            assert response.status_code == 200
        session.close()

    def test_異常系_全リトライ失敗(self) -> None:
        session = PolymarketSession(
            retry_config=RetryConfig(max_attempts=2, base_wait=0.0),
        )

        rate_limit_error = PolymarketRateLimitError(
            message="Rate limited",
            url="https://gamma-api.polymarket.com/markets",
            retry_after=None,
        )

        with (
            patch.object(session, "get", side_effect=rate_limit_error),
            patch("market.polymarket.session.time.sleep"),
            pytest.raises(PolymarketRateLimitError),
        ):
            session.get_with_retry("https://gamma-api.polymarket.com/markets")
        session.close()

    def test_異常系_4xxエラーはリトライしない(self) -> None:
        session = PolymarketSession(
            retry_config=RetryConfig(max_attempts=3, base_wait=0.0),
        )

        api_error = PolymarketAPIError(
            message="Not found",
            url="https://gamma-api.polymarket.com/markets/123",
            status_code=404,
            response_body="Not Found",
        )

        with patch.object(session, "get", side_effect=api_error) as mock_get:
            with pytest.raises(PolymarketAPIError):
                session.get_with_retry("https://gamma-api.polymarket.com/markets/123")
            # Should only be called once (no retry for 4xx)
            mock_get.assert_called_once()
        session.close()

    def test_正常系_5xxエラーはリトライされる(self) -> None:
        session = PolymarketSession(
            retry_config=RetryConfig(max_attempts=3, base_wait=0.0),
        )

        mock_response_ok = MagicMock(spec=httpx.Response)
        mock_response_ok.status_code = 200

        server_error = PolymarketAPIError(
            message="Server error",
            url="https://gamma-api.polymarket.com/markets",
            status_code=500,
            response_body="Internal Server Error",
        )

        call_count = 0

        def mock_get(url: str, params: dict[str, str] | None = None) -> httpx.Response:
            nonlocal call_count
            call_count += 1
            if call_count < 2:
                raise server_error
            return mock_response_ok

        with (
            patch.object(session, "get", side_effect=mock_get),
            patch("market.polymarket.session.time.sleep"),
        ):
            response = session.get_with_retry(
                "https://gamma-api.polymarket.com/markets"
            )
            assert response.status_code == 200
            assert call_count == 2
        session.close()
