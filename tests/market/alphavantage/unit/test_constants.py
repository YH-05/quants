"""Tests for market.alphavantage.constants module."""

from market.alphavantage.constants import (
    ALLOWED_HOSTS,
    ALPHA_VANTAGE_API_KEY_ENV,
    BASE_URL,
    DEFAULT_DELAY_JITTER,
    DEFAULT_POLITE_DELAY,
    DEFAULT_REQUESTS_PER_HOUR,
    DEFAULT_REQUESTS_PER_MINUTE,
    DEFAULT_TIMEOUT,
    MAX_RESPONSE_BODY_LOG,
)


class TestBaseUrl:
    """Tests for BASE_URL constant."""

    def test_正常系_URLが正しい値(self) -> None:
        assert BASE_URL == "https://www.alphavantage.co/query"

    def test_正常系_httpsスキーム(self) -> None:
        assert BASE_URL.startswith("https://")

    def test_正常系_queryパスを含む(self) -> None:
        assert "/query" in BASE_URL


class TestAllowedHosts:
    """Tests for ALLOWED_HOSTS constant."""

    def test_正常系_frozensetである(self) -> None:
        assert isinstance(ALLOWED_HOSTS, frozenset)

    def test_正常系_alphavantage_coを含む(self) -> None:
        assert "www.alphavantage.co" in ALLOWED_HOSTS

    def test_正常系_不正なホストを含まない(self) -> None:
        assert "evil.example.com" not in ALLOWED_HOSTS


class TestEnvironmentVariableNames:
    """Tests for environment variable name constants."""

    def test_正常系_APIキー環境変数名(self) -> None:
        assert ALPHA_VANTAGE_API_KEY_ENV == "ALPHA_VANTAGE_API_KEY"


class TestRateLimitDefaults:
    """Tests for rate limit default constants."""

    def test_正常系_デフォルト毎分リクエスト数(self) -> None:
        assert DEFAULT_REQUESTS_PER_MINUTE == 25

    def test_正常系_デフォルト毎時リクエスト数(self) -> None:
        assert DEFAULT_REQUESTS_PER_HOUR == 500

    def test_正常系_毎分リクエスト数は正の値(self) -> None:
        assert DEFAULT_REQUESTS_PER_MINUTE > 0

    def test_正常系_毎時リクエスト数は正の値(self) -> None:
        assert DEFAULT_REQUESTS_PER_HOUR > 0

    def test_正常系_毎時は毎分より大きい(self) -> None:
        assert DEFAULT_REQUESTS_PER_HOUR > DEFAULT_REQUESTS_PER_MINUTE


class TestHttpDefaults:
    """Tests for HTTP default configuration constants."""

    def test_正常系_デフォルトタイムアウト(self) -> None:
        assert DEFAULT_TIMEOUT == 30.0

    def test_正常系_デフォルトポライトディレイ(self) -> None:
        assert DEFAULT_POLITE_DELAY == 2.5

    def test_正常系_デフォルトディレイジッター(self) -> None:
        assert DEFAULT_DELAY_JITTER == 0.5

    def test_正常系_タイムアウトは正の値(self) -> None:
        assert DEFAULT_TIMEOUT > 0

    def test_正常系_ポライトディレイは正の値(self) -> None:
        assert DEFAULT_POLITE_DELAY > 0

    def test_正常系_ジッターは正の値(self) -> None:
        assert DEFAULT_DELAY_JITTER > 0


class TestSecurityConstants:
    """Tests for security-related constants."""

    def test_正常系_レスポンスボディログ最大値(self) -> None:
        assert MAX_RESPONSE_BODY_LOG == 200

    def test_正常系_レスポンスボディログ最大値は正の値(self) -> None:
        assert MAX_RESPONSE_BODY_LOG > 0


class TestAllExports:
    """Tests for __all__ completeness."""

    def test_正常系_allが定義されている(self) -> None:
        from market.alphavantage import constants

        assert hasattr(constants, "__all__")

    def test_正常系_全定数がallに含まれる(self) -> None:
        from market.alphavantage import constants

        expected = {
            "ALLOWED_HOSTS",
            "ALPHA_VANTAGE_API_KEY_ENV",
            "BASE_URL",
            "DEFAULT_DELAY_JITTER",
            "DEFAULT_POLITE_DELAY",
            "DEFAULT_REQUESTS_PER_HOUR",
            "DEFAULT_REQUESTS_PER_MINUTE",
            "DEFAULT_TIMEOUT",
            "MAX_RESPONSE_BODY_LOG",
        }
        assert set(constants.__all__) == expected
