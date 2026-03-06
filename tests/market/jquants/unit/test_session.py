"""Tests for market.jquants.session module."""

import json
from datetime import UTC, datetime, timedelta
from pathlib import Path
from unittest.mock import MagicMock, patch

import httpx
import pytest

from market.jquants.errors import (
    JQuantsAPIError,
    JQuantsAuthError,
    JQuantsRateLimitError,
)
from market.jquants.session import JQuantsSession
from market.jquants.types import JQuantsConfig, RetryConfig, TokenInfo


@pytest.fixture
def _mock_token_file(tmp_path: Path) -> Path:
    """Create a mock token file with valid tokens."""
    token_path = tmp_path / ".jquants" / "token.json"
    token_path.parent.mkdir(parents=True, exist_ok=True)
    future = datetime.now(UTC) + timedelta(hours=12)
    future_refresh = datetime.now(UTC) + timedelta(days=5)
    data = {
        "refresh_token": "rt_test",
        "id_token": "id_test",
        "refresh_token_expires_at": future_refresh.isoformat(),
        "id_token_expires_at": future.isoformat(),
    }
    token_path.write_text(json.dumps(data), encoding="utf-8")
    return token_path


@pytest.fixture
def config_with_token(tmp_path: Path, _mock_token_file: Path) -> JQuantsConfig:
    """Create a JQuantsConfig pointing to the mock token file."""
    return JQuantsConfig(
        token_file_path=str(_mock_token_file),
    )


@pytest.fixture
def config_no_token(tmp_path: Path) -> JQuantsConfig:
    """Create a JQuantsConfig pointing to nonexistent token file."""
    return JQuantsConfig(
        token_file_path=str(tmp_path / "nonexistent" / "token.json"),
    )


class TestJQuantsSessionInit:
    """Tests for JQuantsSession initialization."""

    def test_正常系_デフォルト設定で初期化(
        self, config_no_token: JQuantsConfig
    ) -> None:
        session = JQuantsSession(config=config_no_token)
        assert session._config == config_no_token
        session.close()

    def test_正常系_トークンファイルからロード(
        self, config_with_token: JQuantsConfig
    ) -> None:
        session = JQuantsSession(config=config_with_token)
        assert session._token_info.id_token == "id_test"
        assert session._token_info.refresh_token == "rt_test"
        session.close()


class TestJQuantsSessionContextManager:
    """Tests for context manager support."""

    def test_正常系_コンテキストマネージャ(
        self, config_no_token: JQuantsConfig
    ) -> None:
        with JQuantsSession(config=config_no_token) as session:
            assert isinstance(session, JQuantsSession)


class TestJQuantsSessionSSRF:
    """Tests for SSRF prevention."""

    def test_正常系_許可されたホスト(self, config_no_token: JQuantsConfig) -> None:
        session = JQuantsSession(config=config_no_token)
        # Should not raise
        session._validate_url("https://api.jquants.com/v1/listed/info")
        session.close()

    def test_異常系_不正なホスト(self, config_no_token: JQuantsConfig) -> None:
        session = JQuantsSession(config=config_no_token)
        with pytest.raises(ValueError, match="not in allowed hosts"):
            session._validate_url("https://evil.example.com/api")
        session.close()

    def test_異常系_不正なスキーム(self, config_no_token: JQuantsConfig) -> None:
        session = JQuantsSession(config=config_no_token)
        with pytest.raises(ValueError, match="URL scheme must be"):
            session._validate_url("ftp://api.jquants.com/v1/listed/info")
        session.close()


class TestJQuantsSessionPoliteDelay:
    """Tests for polite delay."""

    def test_正常系_初回リクエストはディレイなし(
        self, config_no_token: JQuantsConfig
    ) -> None:
        session = JQuantsSession(config=config_no_token)
        assert session._last_request_time == 0.0
        session.close()


class TestJQuantsSessionHandleResponse:
    """Tests for response handling."""

    def test_正常系_200レスポンス(self, config_no_token: JQuantsConfig) -> None:
        session = JQuantsSession(config=config_no_token)
        response = MagicMock(spec=httpx.Response)
        response.status_code = 200
        # Should not raise
        session._handle_response(response, "https://api.jquants.com/v1/test")
        session.close()

    def test_異常系_429レートリミット(self, config_no_token: JQuantsConfig) -> None:
        session = JQuantsSession(config=config_no_token)
        response = MagicMock(spec=httpx.Response)
        response.status_code = 429
        response.headers = {"Retry-After": "60"}
        with pytest.raises(JQuantsRateLimitError) as exc_info:
            session._handle_response(response, "https://api.jquants.com/v1/test")
        assert exc_info.value.retry_after == 60
        session.close()

    def test_異常系_429レートリミット_RetryAfterなし(
        self, config_no_token: JQuantsConfig
    ) -> None:
        session = JQuantsSession(config=config_no_token)
        response = MagicMock(spec=httpx.Response)
        response.status_code = 429
        response.headers = {}
        with pytest.raises(JQuantsRateLimitError) as exc_info:
            session._handle_response(response, "https://api.jquants.com/v1/test")
        assert exc_info.value.retry_after is None
        session.close()

    def test_異常系_400クライアントエラー(self, config_no_token: JQuantsConfig) -> None:
        session = JQuantsSession(config=config_no_token)
        response = MagicMock(spec=httpx.Response)
        response.status_code = 400
        response.text = "Bad Request"
        with pytest.raises(JQuantsAPIError) as exc_info:
            session._handle_response(response, "https://api.jquants.com/v1/test")
        assert exc_info.value.status_code == 400
        session.close()

    def test_異常系_500サーバーエラー(self, config_no_token: JQuantsConfig) -> None:
        session = JQuantsSession(config=config_no_token)
        response = MagicMock(spec=httpx.Response)
        response.status_code = 500
        response.text = "Internal Server Error"
        with pytest.raises(JQuantsAPIError) as exc_info:
            session._handle_response(response, "https://api.jquants.com/v1/test")
        assert exc_info.value.status_code == 500
        session.close()


class TestJQuantsSessionBackoff:
    """Tests for backoff delay calculation."""

    def test_正常系_初回バックオフ(self, config_no_token: JQuantsConfig) -> None:
        session = JQuantsSession(
            config=config_no_token,
            retry_config=RetryConfig(jitter=False),
        )
        delay = session._calculate_backoff_delay(0)
        assert delay == 1.0  # initial_delay * base^0
        session.close()

    def test_正常系_2回目バックオフ(self, config_no_token: JQuantsConfig) -> None:
        session = JQuantsSession(
            config=config_no_token,
            retry_config=RetryConfig(jitter=False),
        )
        delay = session._calculate_backoff_delay(1)
        assert delay == 2.0  # initial_delay * base^1
        session.close()

    def test_正常系_最大ディレイ制限(self, config_no_token: JQuantsConfig) -> None:
        session = JQuantsSession(
            config=config_no_token,
            retry_config=RetryConfig(jitter=False, max_delay=5.0),
        )
        delay = session._calculate_backoff_delay(10)
        assert delay == 5.0  # max_delay cap
        session.close()


class TestJQuantsSessionAuth:
    """Tests for authentication flow."""

    def test_異常系_認証情報なしでログイン(
        self, config_no_token: JQuantsConfig
    ) -> None:
        session = JQuantsSession(config=config_no_token)
        with pytest.raises(JQuantsAuthError, match="credentials not provided"):
            session._login()
        session.close()

    @patch.dict(
        "os.environ",
        {
            "JQUANTS_MAIL_ADDRESS": "test@example.com",
            "JQUANTS_PASSWORD": "test_password",
        },
    )
    def test_異常系_ログインAPIがエラーを返す(
        self, config_no_token: JQuantsConfig
    ) -> None:
        session = JQuantsSession(config=config_no_token)
        mock_response = MagicMock(spec=httpx.Response)
        mock_response.status_code = 401
        mock_response.text = "Unauthorized"

        with (
            patch.object(session._client, "post", return_value=mock_response),
            pytest.raises(JQuantsAuthError, match="Login failed"),
        ):
            session._login()
        session.close()

    @patch.dict(
        "os.environ",
        {
            "JQUANTS_MAIL_ADDRESS": "test@example.com",
            "JQUANTS_PASSWORD": "test_password",
        },
    )
    def test_正常系_ログイン成功(self, tmp_path: Path) -> None:
        config = JQuantsConfig(
            token_file_path=str(tmp_path / ".jquants" / "token.json"),
        )
        session = JQuantsSession(config=config)

        # Mock auth_user response
        auth_user_response = MagicMock(spec=httpx.Response)
        auth_user_response.status_code = 200
        auth_user_response.json.return_value = {"refreshToken": "rt_new_token"}

        # Mock auth_refresh response
        auth_refresh_response = MagicMock(spec=httpx.Response)
        auth_refresh_response.status_code = 200
        auth_refresh_response.json.return_value = {"idToken": "id_new_token"}

        with patch.object(
            session._client,
            "post",
            side_effect=[auth_user_response, auth_refresh_response],
        ):
            session._login()

        assert session._token_info.refresh_token == "rt_new_token"
        assert session._token_info.id_token == "id_new_token"
        assert not session._token_info.is_id_token_expired()
        assert not session._token_info.is_refresh_token_expired()

        # Verify tokens were persisted
        token_path = tmp_path / ".jquants" / "token.json"
        assert token_path.exists()
        saved_data = json.loads(token_path.read_text(encoding="utf-8"))
        assert saved_data["refresh_token"] == "rt_new_token"
        assert saved_data["id_token"] == "id_new_token"

        session.close()

    def test_正常系_リフレッシュ成功(
        self, config_with_token: JQuantsConfig, tmp_path: Path
    ) -> None:
        session = JQuantsSession(config=config_with_token)

        # Expire the id_token but keep refresh_token valid
        session._token_info.id_token_expires_at = datetime.now(UTC) - timedelta(hours=1)

        # Mock auth_refresh response
        refresh_response = MagicMock(spec=httpx.Response)
        refresh_response.status_code = 200
        refresh_response.json.return_value = {"idToken": "id_refreshed"}

        with patch.object(session._client, "post", return_value=refresh_response):
            session._refresh_id_token()

        assert session._token_info.id_token == "id_refreshed"
        assert not session._token_info.is_id_token_expired()
        session.close()

    def test_正常系_ensure_authenticated_有効なトークン(
        self, config_with_token: JQuantsConfig
    ) -> None:
        session = JQuantsSession(config=config_with_token)
        # Token is already valid, should not call login
        with (
            patch.object(session, "_login") as mock_login,
            patch.object(session, "_refresh_id_token") as mock_refresh,
        ):
            session._ensure_authenticated()
            mock_login.assert_not_called()
            mock_refresh.assert_not_called()
        session.close()

    def test_正常系_ensure_authenticated_期限切れでリフレッシュ(
        self, config_with_token: JQuantsConfig
    ) -> None:
        session = JQuantsSession(config=config_with_token)
        # Expire id_token
        session._token_info.id_token_expires_at = datetime.now(UTC) - timedelta(hours=1)

        with patch.object(session, "_refresh_id_token") as mock_refresh:
            session._ensure_authenticated()
            mock_refresh.assert_called_once()
        session.close()

    def test_正常系_ensure_authenticated_リフレッシュ失敗で再ログイン(
        self, config_with_token: JQuantsConfig
    ) -> None:
        session = JQuantsSession(config=config_with_token)
        # Expire id_token
        session._token_info.id_token_expires_at = datetime.now(UTC) - timedelta(hours=1)

        with (
            patch.object(
                session, "_refresh_id_token", side_effect=JQuantsAuthError("fail")
            ),
            patch.object(session, "_login") as mock_login,
        ):
            session._ensure_authenticated()
            mock_login.assert_called_once()
        session.close()


class TestJQuantsSessionTokenPersistence:
    """Tests for token file persistence."""

    def test_正常系_トークンファイルが存在しない(
        self, config_no_token: JQuantsConfig
    ) -> None:
        session = JQuantsSession(config=config_no_token)
        assert session._token_info.id_token == ""
        assert session._token_info.refresh_token == ""
        session.close()

    def test_正常系_トークンファイルから復元(
        self, config_with_token: JQuantsConfig
    ) -> None:
        session = JQuantsSession(config=config_with_token)
        assert session._token_info.id_token == "id_test"
        assert session._token_info.refresh_token == "rt_test"
        session.close()

    def test_異常系_不正なトークンファイル(self, tmp_path: Path) -> None:
        token_path = tmp_path / ".jquants" / "token.json"
        token_path.parent.mkdir(parents=True, exist_ok=True)
        token_path.write_text("invalid json", encoding="utf-8")

        config = JQuantsConfig(token_file_path=str(token_path))
        session = JQuantsSession(config=config)
        # Should fallback to empty tokens
        assert session._token_info.id_token == ""
        assert session._token_info.refresh_token == ""
        session.close()

    def test_正常系_トークン保存(self, tmp_path: Path) -> None:
        token_path = tmp_path / ".jquants" / "token.json"
        config = JQuantsConfig(token_file_path=str(token_path))
        session = JQuantsSession(config=config)

        session._token_info.refresh_token = "rt_save"
        session._token_info.id_token = "id_save"
        session._token_info.refresh_token_expires_at = datetime.now(UTC) + timedelta(
            days=7
        )
        session._token_info.id_token_expires_at = datetime.now(UTC) + timedelta(
            hours=24
        )

        session._save_tokens()

        assert token_path.exists()
        saved = json.loads(token_path.read_text(encoding="utf-8"))
        assert saved["refresh_token"] == "rt_save"
        assert saved["id_token"] == "id_save"
        session.close()


class TestJQuantsSessionGet:
    """Tests for GET request method."""

    def test_正常系_GETリクエスト(self, config_with_token: JQuantsConfig) -> None:
        session = JQuantsSession(config=config_with_token)

        mock_response = MagicMock(spec=httpx.Response)
        mock_response.status_code = 200

        with patch.object(session._client, "get", return_value=mock_response):
            response = session.get("https://api.jquants.com/v1/listed/info")
            assert response.status_code == 200
        session.close()

    def test_異常系_SSRFブロック(self, config_with_token: JQuantsConfig) -> None:
        session = JQuantsSession(config=config_with_token)
        with pytest.raises(ValueError, match="not in allowed hosts"):
            session.get("https://evil.example.com/api")
        session.close()


class TestJQuantsSessionGetWithRetry:
    """Tests for GET with retry."""

    def test_正常系_リトライ成功(self, config_with_token: JQuantsConfig) -> None:
        session = JQuantsSession(
            config=config_with_token,
            retry_config=RetryConfig(max_attempts=3, jitter=False),
        )

        mock_response_ok = MagicMock(spec=httpx.Response)
        mock_response_ok.status_code = 200

        # First call succeeds
        with patch.object(session, "get", return_value=mock_response_ok):
            response = session.get_with_retry("https://api.jquants.com/v1/listed/info")
            assert response.status_code == 200
        session.close()

    def test_正常系_リトライ後成功(self, config_with_token: JQuantsConfig) -> None:
        session = JQuantsSession(
            config=config_with_token,
            retry_config=RetryConfig(max_attempts=3, jitter=False),
        )

        mock_response_ok = MagicMock(spec=httpx.Response)
        mock_response_ok.status_code = 200

        rate_limit_error = JQuantsRateLimitError(
            message="Rate limited",
            url="https://api.jquants.com/v1/test",
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
            patch("market.jquants.session.time.sleep"),
        ):
            response = session.get_with_retry("https://api.jquants.com/v1/test")
            assert response.status_code == 200
        session.close()

    def test_異常系_全リトライ失敗(self, config_with_token: JQuantsConfig) -> None:
        session = JQuantsSession(
            config=config_with_token,
            retry_config=RetryConfig(max_attempts=2, jitter=False),
        )

        rate_limit_error = JQuantsRateLimitError(
            message="Rate limited",
            url="https://api.jquants.com/v1/test",
            retry_after=None,
        )

        with (
            patch.object(session, "get", side_effect=rate_limit_error),
            patch("market.jquants.session.time.sleep"),
            pytest.raises(JQuantsRateLimitError),
        ):
            session.get_with_retry("https://api.jquants.com/v1/test")
        session.close()

    def test_異常系_4xxエラーはリトライしない(
        self, config_with_token: JQuantsConfig
    ) -> None:
        session = JQuantsSession(
            config=config_with_token,
            retry_config=RetryConfig(max_attempts=3, jitter=False),
        )

        api_error = JQuantsAPIError(
            message="Not found",
            url="https://api.jquants.com/v1/test",
            status_code=404,
            response_body="Not Found",
        )

        with patch.object(session, "get", side_effect=api_error) as mock_get:
            with pytest.raises(JQuantsAPIError):
                session.get_with_retry("https://api.jquants.com/v1/test")
            # Should only be called once (no retry for 4xx)
            mock_get.assert_called_once()
        session.close()
