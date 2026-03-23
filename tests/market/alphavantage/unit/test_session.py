"""Tests for market.alphavantage.session module.

Tests cover the AlphaVantageSession class including:
- Initialization and context manager
- API key injection as query parameter
- SSRF prevention via allowed hosts whitelist
- HTTP 200 body error detection (Error Message, Note, Information)
- Polite delay between requests
- Exponential backoff retry logic
- Rate limiter integration

See Also
--------
tests.market.jquants.unit.test_client : Similar test pattern reference.
market.alphavantage.session : Implementation under test.
"""

from __future__ import annotations

import time
from typing import Any
from unittest.mock import MagicMock, patch

import httpx
import pytest

from market.alphavantage.errors import (
    AlphaVantageAPIError,
    AlphaVantageAuthError,
    AlphaVantageRateLimitError,
)
from market.alphavantage.session import AlphaVantageSession
from market.alphavantage.types import AlphaVantageConfig, RetryConfig

# =============================================================================
# Fixtures
# =============================================================================

_AV_URL = "https://www.alphavantage.co/query"


@pytest.fixture
def zero_delay_config() -> AlphaVantageConfig:
    """Create config with zero delays for fast tests."""
    return AlphaVantageConfig(
        api_key="test-api-key",
        polite_delay=0.0,
        delay_jitter=0.0,
        timeout=5.0,
    )


@pytest.fixture
def retry_config() -> RetryConfig:
    """Create retry config for testing."""
    return RetryConfig(
        max_attempts=3,
        initial_delay=0.0,
        max_delay=0.0,
        exponential_base=2.0,
        jitter=False,
    )


@pytest.fixture
def single_retry_config() -> RetryConfig:
    """Create single-attempt retry config."""
    return RetryConfig(
        max_attempts=1,
        initial_delay=0.0,
        max_delay=0.0,
        jitter=False,
    )


def _make_mock_response(
    status_code: int = 200,
    json_data: dict[str, Any] | None = None,
    text: str = "",
    headers: dict[str, str] | None = None,
) -> MagicMock:
    """Create a mock httpx.Response."""
    resp = MagicMock(spec=httpx.Response)
    resp.status_code = status_code
    resp.json.return_value = json_data or {}
    resp.text = text or str(json_data or {})
    resp.headers = headers or {"Content-Type": "application/json"}
    return resp


# =============================================================================
# TestAlphaVantageSessionInit
# =============================================================================


class TestAlphaVantageSessionInit:
    """Tests for AlphaVantageSession initialization."""

    def test_正常系_デフォルト設定で初期化(self) -> None:
        """Session initializes with default config."""
        with patch.dict("os.environ", {"ALPHA_VANTAGE_API_KEY": "env-key"}):
            session = AlphaVantageSession()
            assert session is not None
            session.close()

    def test_正常系_カスタム設定で初期化(
        self,
        zero_delay_config: AlphaVantageConfig,
    ) -> None:
        """Session initializes with custom config."""
        session = AlphaVantageSession(config=zero_delay_config)
        assert session is not None
        session.close()

    def test_正常系_リトライ設定で初期化(
        self,
        zero_delay_config: AlphaVantageConfig,
        retry_config: RetryConfig,
    ) -> None:
        """Session initializes with custom retry config."""
        session = AlphaVantageSession(
            config=zero_delay_config,
            retry_config=retry_config,
        )
        assert session is not None
        session.close()


# =============================================================================
# TestAlphaVantageSessionContextManager
# =============================================================================


class TestAlphaVantageSessionContextManager:
    """Tests for context manager protocol."""

    def test_正常系_コンテキストマネージャで使用(
        self,
        zero_delay_config: AlphaVantageConfig,
    ) -> None:
        """Session can be used as context manager."""
        with AlphaVantageSession(config=zero_delay_config) as session:
            assert isinstance(session, AlphaVantageSession)


# =============================================================================
# TestAPIKeyInjection
# =============================================================================


class TestAPIKeyInjection:
    """Tests for API key injection as query parameter."""

    def test_正常系_APIキーがクエリパラメータに注入される(
        self,
        zero_delay_config: AlphaVantageConfig,
    ) -> None:
        """API key is injected into query params."""
        mock_response = _make_mock_response(
            json_data={"Meta Data": {}, "Time Series (Daily)": {}},
        )

        with AlphaVantageSession(config=zero_delay_config) as session:  # noqa: SIM117
            with patch.object(
                session._client, "get", return_value=mock_response
            ) as mock_get:
                session.get(
                    _AV_URL,
                    params={"function": "TIME_SERIES_DAILY", "symbol": "AAPL"},
                )

                # Verify API key was added to params
                call_kwargs = mock_get.call_args
                actual_params = call_kwargs.kwargs.get("params") or call_kwargs[1].get(
                    "params"
                )
                assert actual_params["apikey"] == "test-api-key"

    def test_正常系_環境変数からAPIキー取得(self) -> None:
        """API key is read from environment variable when not in config."""
        config = AlphaVantageConfig(
            api_key="",
            polite_delay=0.0,
            delay_jitter=0.0,
            timeout=5.0,
        )
        mock_response = _make_mock_response(
            json_data={"Meta Data": {}, "Time Series (Daily)": {}},
        )

        with patch.dict(  # noqa: SIM117
            "os.environ", {"ALPHA_VANTAGE_API_KEY": "env-api-key"}
        ):
            with AlphaVantageSession(config=config) as session:
                with patch.object(
                    session._client, "get", return_value=mock_response
                ) as mock_get:
                    session.get(
                        _AV_URL,
                        params={"function": "TIME_SERIES_DAILY"},
                    )

                    call_kwargs = mock_get.call_args
                    actual_params = call_kwargs.kwargs.get("params") or call_kwargs[
                        1
                    ].get("params")
                    assert actual_params["apikey"] == "env-api-key"

    def test_異常系_APIキー未設定でAuthError(self) -> None:
        """Raises AlphaVantageAuthError when API key is missing."""
        config = AlphaVantageConfig(
            api_key="",
            polite_delay=0.0,
            delay_jitter=0.0,
            timeout=5.0,
        )

        with patch.dict("os.environ", {}, clear=True):  # noqa: SIM117
            with AlphaVantageSession(config=config) as session:
                with pytest.raises(AlphaVantageAuthError, match="API key"):
                    session.get(
                        _AV_URL,
                        params={"function": "TIME_SERIES_DAILY"},
                    )


# =============================================================================
# TestSSRFPrevention
# =============================================================================


class TestSSRFPrevention:
    """Tests for SSRF prevention via host whitelist."""

    def test_異常系_許可されていないホストでValueError(
        self,
        zero_delay_config: AlphaVantageConfig,
    ) -> None:
        """Raises ValueError for non-whitelisted host."""
        with AlphaVantageSession(config=zero_delay_config) as session, pytest.raises(
            ValueError, match="not in allowed hosts"
        ):
            session.get("https://evil.com/query")

    def test_異常系_不正なスキームでValueError(
        self,
        zero_delay_config: AlphaVantageConfig,
    ) -> None:
        """Raises ValueError for non-http(s) scheme."""
        with AlphaVantageSession(config=zero_delay_config) as session, pytest.raises(
            ValueError, match="scheme"
        ):
            session.get("ftp://www.alphavantage.co/query")

    def test_正常系_許可されたホストでリクエスト成功(
        self,
        zero_delay_config: AlphaVantageConfig,
    ) -> None:
        """Allows requests to whitelisted host."""
        mock_response = _make_mock_response(
            json_data={"Meta Data": {}},
        )

        with AlphaVantageSession(config=zero_delay_config) as session:  # noqa: SIM117
            with patch.object(session._client, "get", return_value=mock_response):
                # Should not raise
                session.get(_AV_URL)


# =============================================================================
# TestHTTP200ErrorDetection
# =============================================================================


class TestHTTP200ErrorDetection:
    """Tests for HTTP 200 body error detection."""

    def test_異常系_NoteキーでRateLimitError(
        self,
        zero_delay_config: AlphaVantageConfig,
    ) -> None:
        """Detects 'Note' key as rate limit error."""
        mock_response = _make_mock_response(
            json_data={
                "Note": (
                    "Thank you for using Alpha Vantage! "
                    "Our standard API rate limit is 25 requests per day."
                )
            },
        )

        with AlphaVantageSession(config=zero_delay_config) as session:  # noqa: SIM117
            with patch.object(session._client, "get", return_value=mock_response):
                with pytest.raises(AlphaVantageRateLimitError):
                    session.get(_AV_URL)

    def test_異常系_ErrorMessageキーでAPIError(
        self,
        zero_delay_config: AlphaVantageConfig,
    ) -> None:
        """Detects 'Error Message' key as API error."""
        mock_response = _make_mock_response(
            json_data={
                "Error Message": (
                    "Invalid API call. Please retry or visit the documentation."
                )
            },
        )

        with AlphaVantageSession(config=zero_delay_config) as session:  # noqa: SIM117
            with patch.object(session._client, "get", return_value=mock_response):
                with pytest.raises(AlphaVantageAPIError):
                    session.get(_AV_URL)

    def test_異常系_ErrorMessageにinvalid_api_keyでAuthError(
        self,
        zero_delay_config: AlphaVantageConfig,
    ) -> None:
        """Detects 'Error Message' with invalid API key hint as auth error."""
        mock_response = _make_mock_response(
            json_data={
                "Error Message": (
                    "the parameter apikey is invalid or missing. "
                    "Please claim your free API key on "
                    "(https://www.alphavantage.co/support/#api-key)."
                )
            },
        )

        with AlphaVantageSession(config=zero_delay_config) as session:  # noqa: SIM117
            with patch.object(session._client, "get", return_value=mock_response):
                with pytest.raises(AlphaVantageAuthError):
                    session.get(_AV_URL)

    def test_異常系_InformationキーでAuthError(
        self,
        zero_delay_config: AlphaVantageConfig,
    ) -> None:
        """Detects 'Information' key as auth error (premium endpoint)."""
        mock_response = _make_mock_response(
            json_data={
                "Information": (
                    "Thank you for using Alpha Vantage! "
                    "This is a premium endpoint."
                )
            },
        )

        with AlphaVantageSession(config=zero_delay_config) as session:  # noqa: SIM117
            with patch.object(session._client, "get", return_value=mock_response):
                with pytest.raises(AlphaVantageAuthError):
                    session.get(_AV_URL)

    def test_正常系_エラーキーなしで正常応答(
        self,
        zero_delay_config: AlphaVantageConfig,
    ) -> None:
        """Normal response without error keys passes through."""
        mock_response = _make_mock_response(
            json_data={"Meta Data": {}, "Time Series (Daily)": {}},
        )

        with AlphaVantageSession(config=zero_delay_config) as session:  # noqa: SIM117
            with patch.object(session._client, "get", return_value=mock_response):
                response = session.get(_AV_URL)
                assert response.status_code == 200


# =============================================================================
# TestHTTPStatusErrorDetection
# =============================================================================


class TestHTTPStatusErrorDetection:
    """Tests for standard HTTP error status code handling."""

    def test_異常系_HTTP429でRateLimitError(
        self,
        zero_delay_config: AlphaVantageConfig,
    ) -> None:
        """HTTP 429 raises AlphaVantageRateLimitError."""
        mock_response = _make_mock_response(
            status_code=429,
            text="Rate limit exceeded",
            headers={"Retry-After": "60"},
        )

        with AlphaVantageSession(config=zero_delay_config) as session:  # noqa: SIM117
            with patch.object(session._client, "get", return_value=mock_response):
                with pytest.raises(AlphaVantageRateLimitError):
                    session.get(_AV_URL)

    def test_異常系_HTTP500でAPIError(
        self,
        zero_delay_config: AlphaVantageConfig,
    ) -> None:
        """HTTP 500 raises AlphaVantageAPIError."""
        mock_response = _make_mock_response(
            status_code=500,
            text="Internal Server Error",
        )

        with AlphaVantageSession(config=zero_delay_config) as session:  # noqa: SIM117
            with patch.object(session._client, "get", return_value=mock_response):
                with pytest.raises(AlphaVantageAPIError):
                    session.get(_AV_URL)

    def test_異常系_HTTP403でAPIError(
        self,
        zero_delay_config: AlphaVantageConfig,
    ) -> None:
        """HTTP 403 raises AlphaVantageAPIError."""
        mock_response = _make_mock_response(
            status_code=403,
            text="Forbidden",
        )

        with AlphaVantageSession(config=zero_delay_config) as session:  # noqa: SIM117
            with patch.object(session._client, "get", return_value=mock_response):
                with pytest.raises(AlphaVantageAPIError):
                    session.get(_AV_URL)


# =============================================================================
# TestPoliteDelay
# =============================================================================


class TestPoliteDelay:
    """Tests for polite delay between requests."""

    def test_正常系_最初のリクエストは遅延なし(
        self,
        zero_delay_config: AlphaVantageConfig,
    ) -> None:
        """First request has no polite delay."""
        mock_response = _make_mock_response(json_data={"Meta Data": {}})

        with AlphaVantageSession(config=zero_delay_config) as session:  # noqa: SIM117
            with patch.object(session._client, "get", return_value=mock_response):
                start = time.monotonic()
                session.get(_AV_URL)
                elapsed = time.monotonic() - start
                # Should complete quickly with zero delay config
                assert elapsed < 1.0

    def test_正常系_ポライトディレイが適用される(self) -> None:
        """Polite delay is applied between consecutive requests."""
        config = AlphaVantageConfig(
            api_key="test-key",
            polite_delay=0.1,
            delay_jitter=0.0,
            timeout=5.0,
        )
        mock_response = _make_mock_response(json_data={"Meta Data": {}})

        with AlphaVantageSession(config=config) as session:  # noqa: SIM117
            with patch.object(session._client, "get", return_value=mock_response):
                session.get(_AV_URL)
                start = time.monotonic()
                session.get(_AV_URL)
                elapsed = time.monotonic() - start
                # Second request should have at least polite_delay
                assert elapsed >= 0.09  # Allow small tolerance


# =============================================================================
# TestRateLimiterIntegration
# =============================================================================


class TestRateLimiterIntegration:
    """Tests for DualWindowRateLimiter integration."""

    def test_正常系_レートリミッターが統合されている(
        self,
        zero_delay_config: AlphaVantageConfig,
    ) -> None:
        """Rate limiter acquire() is called before each request."""
        mock_response = _make_mock_response(json_data={"Meta Data": {}})

        with AlphaVantageSession(config=zero_delay_config) as session:  # noqa: SIM117
            with patch.object(session._rate_limiter, "acquire") as mock_acquire:
                mock_acquire.return_value = 0.0
                with patch.object(
                    session._client, "get", return_value=mock_response
                ):
                    session.get(_AV_URL)
                    mock_acquire.assert_called_once()


# =============================================================================
# TestExponentialBackoffRetry
# =============================================================================


class TestExponentialBackoffRetry:
    """Tests for get_with_retry exponential backoff."""

    def test_正常系_初回成功でリトライなし(
        self,
        zero_delay_config: AlphaVantageConfig,
        retry_config: RetryConfig,
    ) -> None:
        """Returns immediately on first success."""
        mock_response = _make_mock_response(json_data={"Meta Data": {}})

        with AlphaVantageSession(
            config=zero_delay_config, retry_config=retry_config
        ) as session, patch.object(
            session._client, "get", return_value=mock_response
        ):
            response = session.get_with_retry(_AV_URL)
            assert response.status_code == 200

    def test_正常系_リトライ後に成功(
        self,
        zero_delay_config: AlphaVantageConfig,
        retry_config: RetryConfig,
    ) -> None:
        """Retries on server error and succeeds on subsequent attempt."""
        error_response = _make_mock_response(status_code=500, text="Server Error")
        ok_response = _make_mock_response(json_data={"Meta Data": {}})

        with AlphaVantageSession(
            config=zero_delay_config, retry_config=retry_config
        ) as session, patch.object(
            session._client, "get", side_effect=[error_response, ok_response]
        ):
            response = session.get_with_retry(_AV_URL)
            assert response.status_code == 200

    def test_異常系_全リトライ失敗(
        self,
        zero_delay_config: AlphaVantageConfig,
        retry_config: RetryConfig,
    ) -> None:
        """Raises after all retry attempts exhausted."""
        error_response = _make_mock_response(status_code=500, text="Server Error")

        with AlphaVantageSession(
            config=zero_delay_config, retry_config=retry_config
        ) as session, patch.object(
            session._client,
            "get",
            return_value=error_response,
        ), pytest.raises(AlphaVantageAPIError):
            session.get_with_retry(_AV_URL)

    def test_異常系_4xxエラーはリトライしない(
        self,
        zero_delay_config: AlphaVantageConfig,
        retry_config: RetryConfig,
    ) -> None:
        """Does not retry on client errors (4xx except 429)."""
        error_response = _make_mock_response(status_code=403, text="Forbidden")

        with AlphaVantageSession(  # noqa: SIM117
            config=zero_delay_config, retry_config=retry_config
        ) as session:
            with patch.object(
                session._client, "get", return_value=error_response
            ) as mock_get:
                with pytest.raises(AlphaVantageAPIError):
                    session.get_with_retry(_AV_URL)
                # Should only be called once (no retry)
                assert mock_get.call_count == 1

    def test_正常系_RateLimitErrorはリトライ対象(
        self,
        zero_delay_config: AlphaVantageConfig,
        retry_config: RetryConfig,
    ) -> None:
        """Retries on rate limit (HTTP 429) and body-based rate limit."""
        rate_limit_response = _make_mock_response(
            status_code=429,
            text="Rate limited",
            headers={"Retry-After": "1"},
        )
        ok_response = _make_mock_response(json_data={"Meta Data": {}})

        with AlphaVantageSession(
            config=zero_delay_config, retry_config=retry_config
        ) as session, patch.object(
            session._client,
            "get",
            side_effect=[rate_limit_response, ok_response],
        ):
            response = session.get_with_retry(_AV_URL)
            assert response.status_code == 200


# =============================================================================
# Module exports
# =============================================================================

__all__: list[str] = []
