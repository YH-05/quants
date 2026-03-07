"""Tests for market.jquants.types module."""

from datetime import UTC, datetime, timedelta

import pytest

from market.jquants.types import (
    FetchOptions,
    JQuantsConfig,
    RetryConfig,
    TokenInfo,
)


class TestJQuantsConfig:
    """Tests for JQuantsConfig dataclass."""

    def test_正常系_デフォルト値(self) -> None:
        config = JQuantsConfig()
        assert config.mail_address == ""
        assert config.password == ""
        assert config.token_file_path == "~/.jquants/token.json"
        assert config.timeout == 30.0
        assert config.polite_delay == 0.1
        assert config.delay_jitter == 0.05

    def test_正常系_カスタム値(self) -> None:
        config = JQuantsConfig(
            mail_address="user@example.com",
            password="secret",
            timeout=60.0,
            polite_delay=0.5,
        )
        assert config.mail_address == "user@example.com"
        assert config.password == "secret"
        assert config.timeout == 60.0
        assert config.polite_delay == 0.5

    def test_正常系_frozen(self) -> None:
        config = JQuantsConfig()
        with pytest.raises(AttributeError):
            config.timeout = 60.0  # type: ignore[misc]

    def test_異常系_タイムアウトが範囲外_小さすぎ(self) -> None:
        with pytest.raises(ValueError, match="timeout must be between"):
            JQuantsConfig(timeout=0.5)

    def test_異常系_タイムアウトが範囲外_大きすぎ(self) -> None:
        with pytest.raises(ValueError, match="timeout must be between"):
            JQuantsConfig(timeout=400.0)

    def test_異常系_ポライトディレイが範囲外(self) -> None:
        with pytest.raises(ValueError, match="polite_delay must be between"):
            JQuantsConfig(polite_delay=-1.0)

    def test_異常系_ジッターが範囲外(self) -> None:
        with pytest.raises(ValueError, match="delay_jitter must be between"):
            JQuantsConfig(delay_jitter=31.0)


class TestRetryConfig:
    """Tests for RetryConfig dataclass."""

    def test_正常系_デフォルト値(self) -> None:
        config = RetryConfig()
        assert config.max_attempts == 3
        assert config.exponential_base == 2.0
        assert config.max_delay == 30.0
        assert config.initial_delay == 1.0
        assert config.jitter is True

    def test_正常系_カスタム値(self) -> None:
        config = RetryConfig(max_attempts=5, exponential_base=3.0)
        assert config.max_attempts == 5
        assert config.exponential_base == 3.0

    def test_異常系_max_attemptsが範囲外_小さすぎ(self) -> None:
        with pytest.raises(ValueError, match="max_attempts must be between"):
            RetryConfig(max_attempts=0)

    def test_異常系_max_attemptsが範囲外_大きすぎ(self) -> None:
        with pytest.raises(ValueError, match="max_attempts must be between"):
            RetryConfig(max_attempts=11)


class TestFetchOptions:
    """Tests for FetchOptions dataclass."""

    def test_正常系_デフォルト値(self) -> None:
        options = FetchOptions()
        assert options.use_cache is True
        assert options.force_refresh is False

    def test_正常系_キャッシュ無効(self) -> None:
        options = FetchOptions(use_cache=False)
        assert options.use_cache is False

    def test_正常系_強制リフレッシュ(self) -> None:
        options = FetchOptions(force_refresh=True)
        assert options.force_refresh is True


class TestTokenInfo:
    """Tests for TokenInfo dataclass."""

    def test_正常系_デフォルト値(self) -> None:
        token = TokenInfo()
        assert token.refresh_token == ""
        assert token.id_token == ""

    def test_正常系_カスタム値(self) -> None:
        now = datetime.now(UTC)
        token = TokenInfo(
            refresh_token="rt_xxx",
            id_token="id_xxx",
            refresh_token_expires_at=now + timedelta(days=7),
            id_token_expires_at=now + timedelta(hours=24),
        )
        assert token.refresh_token == "rt_xxx"
        assert token.id_token == "id_xxx"

    def test_正常系_id_tokenが期限切れでない(self) -> None:
        token = TokenInfo(
            id_token="id_xxx",
            id_token_expires_at=datetime.now(UTC) + timedelta(hours=1),
        )
        assert token.is_id_token_expired() is False

    def test_正常系_id_tokenが期限切れ(self) -> None:
        token = TokenInfo(
            id_token="id_xxx",
            id_token_expires_at=datetime.now(UTC) - timedelta(hours=1),
        )
        assert token.is_id_token_expired() is True

    def test_正常系_refresh_tokenが期限切れでない(self) -> None:
        token = TokenInfo(
            refresh_token="rt_xxx",
            refresh_token_expires_at=datetime.now(UTC) + timedelta(days=1),
        )
        assert token.is_refresh_token_expired() is False

    def test_正常系_refresh_tokenが期限切れ(self) -> None:
        token = TokenInfo(
            refresh_token="rt_xxx",
            refresh_token_expires_at=datetime.now(UTC) - timedelta(days=1),
        )
        assert token.is_refresh_token_expired() is True

    def test_エッジケース_デフォルトトークンは期限切れ(self) -> None:
        token = TokenInfo()
        assert token.is_id_token_expired() is True
        assert token.is_refresh_token_expired() is True

    def test_正常系_mutable(self) -> None:
        """TokenInfo is mutable (not frozen) for token refresh."""
        token = TokenInfo()
        token.id_token = "new_token"
        assert token.id_token == "new_token"
