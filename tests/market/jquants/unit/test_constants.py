"""Tests for market.jquants.constants module."""

from market.jquants.constants import (
    ALLOWED_HOSTS,
    BASE_URL,
    DEFAULT_DELAY_JITTER,
    DEFAULT_POLITE_DELAY,
    DEFAULT_TIMEOUT,
    JQUANTS_MAIL_ADDRESS_ENV,
    JQUANTS_PASSWORD_ENV,
    TOKEN_FILE_PATH,
)


class TestBaseUrl:
    """Tests for BASE_URL constant."""

    def test_正常系_URLが正しい値(self) -> None:
        assert BASE_URL == "https://api.jquants.com/v1"

    def test_正常系_httpsスキーム(self) -> None:
        assert BASE_URL.startswith("https://")

    def test_正常系_v1バージョンを含む(self) -> None:
        assert "/v1" in BASE_URL


class TestAllowedHosts:
    """Tests for ALLOWED_HOSTS constant."""

    def test_正常系_frozensetである(self) -> None:
        assert isinstance(ALLOWED_HOSTS, frozenset)

    def test_正常系_api_jquants_comを含む(self) -> None:
        assert "api.jquants.com" in ALLOWED_HOSTS

    def test_正常系_不正なホストを含まない(self) -> None:
        assert "evil.example.com" not in ALLOWED_HOSTS


class TestEnvironmentVariableNames:
    """Tests for environment variable name constants."""

    def test_正常系_メールアドレス環境変数名(self) -> None:
        assert JQUANTS_MAIL_ADDRESS_ENV == "JQUANTS_MAIL_ADDRESS"

    def test_正常系_パスワード環境変数名(self) -> None:
        assert JQUANTS_PASSWORD_ENV == "JQUANTS_PASSWORD"


class TestTokenFilePath:
    """Tests for TOKEN_FILE_PATH constant."""

    def test_正常系_チルダで始まる(self) -> None:
        assert TOKEN_FILE_PATH.startswith("~")

    def test_正常系_jquantsディレクトリを含む(self) -> None:
        assert ".jquants" in TOKEN_FILE_PATH

    def test_正常系_token_jsonファイル名(self) -> None:
        assert TOKEN_FILE_PATH.endswith("token.json")

    def test_正常系_正しいパス(self) -> None:
        assert TOKEN_FILE_PATH == "~/.jquants/token.json"


class TestDefaultValues:
    """Tests for default configuration constants."""

    def test_正常系_デフォルトタイムアウト(self) -> None:
        assert DEFAULT_TIMEOUT == 30.0

    def test_正常系_デフォルトポライトディレイ(self) -> None:
        assert DEFAULT_POLITE_DELAY == 0.1

    def test_正常系_デフォルトディレイジッター(self) -> None:
        assert DEFAULT_DELAY_JITTER == 0.05

    def test_正常系_タイムアウトは正の値(self) -> None:
        assert DEFAULT_TIMEOUT > 0

    def test_正常系_ポライトディレイは正の値(self) -> None:
        assert DEFAULT_POLITE_DELAY > 0

    def test_正常系_ジッターは正の値(self) -> None:
        assert DEFAULT_DELAY_JITTER > 0
