"""Tests for market.polymarket.constants module."""

from market.polymarket.constants import (
    ALLOWED_HOSTS,
    CLOB_BASE_URL,
    DATA_BASE_URL,
    DEFAULT_RATE_LIMIT_PER_SECOND,
    DEFAULT_TIMEOUT,
    GAMMA_BASE_URL,
    MAX_LIMIT,
)


class TestGammaBaseUrl:
    """Tests for GAMMA_BASE_URL constant."""

    def test_正常系_URLが正しい値(self) -> None:
        assert GAMMA_BASE_URL == "https://gamma-api.polymarket.com"

    def test_正常系_httpsスキーム(self) -> None:
        assert GAMMA_BASE_URL.startswith("https://")

    def test_正常系_gammaを含む(self) -> None:
        assert "gamma" in GAMMA_BASE_URL.lower()


class TestClobBaseUrl:
    """Tests for CLOB_BASE_URL constant."""

    def test_正常系_URLが正しい値(self) -> None:
        assert CLOB_BASE_URL == "https://clob.polymarket.com"

    def test_正常系_httpsスキーム(self) -> None:
        assert CLOB_BASE_URL.startswith("https://")

    def test_正常系_clobを含む(self) -> None:
        assert "clob" in CLOB_BASE_URL.lower()


class TestDataBaseUrl:
    """Tests for DATA_BASE_URL constant."""

    def test_正常系_URLが正しい値(self) -> None:
        assert DATA_BASE_URL == "https://data-api.polymarket.com"

    def test_正常系_httpsスキーム(self) -> None:
        assert DATA_BASE_URL.startswith("https://")

    def test_正常系_dataを含む(self) -> None:
        assert "data" in DATA_BASE_URL.lower()


class TestAllBaseUrls:
    """Cross-cutting tests for all base URL constants."""

    def test_正常系_全URLがhttpsスキーム(self) -> None:
        for url in (GAMMA_BASE_URL, CLOB_BASE_URL, DATA_BASE_URL):
            assert url.startswith("https://"), f"{url} does not start with https://"

    def test_正常系_全URLが末尾スラッシュなし(self) -> None:
        for url in (GAMMA_BASE_URL, CLOB_BASE_URL, DATA_BASE_URL):
            assert not url.endswith("/"), f"{url} ends with /"

    def test_正常系_全URLがpolymarket_comドメイン(self) -> None:
        for url in (GAMMA_BASE_URL, CLOB_BASE_URL, DATA_BASE_URL):
            assert "polymarket.com" in url, f"{url} is not a polymarket.com domain"


class TestAllowedHosts:
    """Tests for ALLOWED_HOSTS constant."""

    def test_正常系_frozensetである(self) -> None:
        assert isinstance(ALLOWED_HOSTS, frozenset)

    def test_正常系_3ホストを含む(self) -> None:
        assert len(ALLOWED_HOSTS) == 3

    def test_正常系_gamma_apiホストを含む(self) -> None:
        assert "gamma-api.polymarket.com" in ALLOWED_HOSTS

    def test_正常系_clobホストを含む(self) -> None:
        assert "clob.polymarket.com" in ALLOWED_HOSTS

    def test_正常系_data_apiホストを含む(self) -> None:
        assert "data-api.polymarket.com" in ALLOWED_HOSTS

    def test_正常系_不正なホストを含まない(self) -> None:
        assert "evil.example.com" not in ALLOWED_HOSTS

    def test_正常系_全ホストがベースURLと対応(self) -> None:
        """ALLOWED_HOSTS の各ホストが対応するベースURLのホスト部分と一致する。"""
        from urllib.parse import urlparse

        for url in (GAMMA_BASE_URL, CLOB_BASE_URL, DATA_BASE_URL):
            host = urlparse(url).hostname
            assert host in ALLOWED_HOSTS, f"{host} not in ALLOWED_HOSTS"


class TestDefaultValues:
    """Tests for default configuration constants."""

    def test_正常系_デフォルトタイムアウト(self) -> None:
        assert DEFAULT_TIMEOUT == 30.0

    def test_正常系_タイムアウトは正の値(self) -> None:
        assert DEFAULT_TIMEOUT > 0

    def test_正常系_タイムアウトはfloat型(self) -> None:
        assert isinstance(DEFAULT_TIMEOUT, float)

    def test_正常系_デフォルトレートリミット(self) -> None:
        assert DEFAULT_RATE_LIMIT_PER_SECOND == 1.5

    def test_正常系_レートリミットは正の値(self) -> None:
        assert DEFAULT_RATE_LIMIT_PER_SECOND > 0

    def test_正常系_レートリミットはfloat型(self) -> None:
        assert isinstance(DEFAULT_RATE_LIMIT_PER_SECOND, float)

    def test_正常系_MAX_LIMITが正の整数(self) -> None:
        assert isinstance(MAX_LIMIT, int)
        assert MAX_LIMIT > 0
