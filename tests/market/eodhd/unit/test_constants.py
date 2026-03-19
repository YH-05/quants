"""EODHD constants のテスト。"""

from __future__ import annotations

from market.eodhd.constants import (
    ALLOWED_HOSTS,
    BASE_URL,
    DEFAULT_FORMAT,
    DEFAULT_TIMEOUT,
    EODHD_API_KEY_ENV,
)


class TestEodhdConstants:
    """EODHD constants モジュールのテスト。"""

    def test_正常系_ALLOWED_HOSTSがfrozensetである(self) -> None:
        assert isinstance(ALLOWED_HOSTS, frozenset)

    def test_正常系_ALLOWED_HOSTSにeodhd_comが含まれる(self) -> None:
        assert "eodhd.com" in ALLOWED_HOSTS

    def test_正常系_EODHD_API_KEY_ENVの値が正しい(self) -> None:
        assert EODHD_API_KEY_ENV == "EODHD_API_KEY"

    def test_正常系_BASE_URLの値が正しい(self) -> None:
        assert BASE_URL == "https://eodhd.com/api"

    def test_正常系_DEFAULT_TIMEOUTの値が正しい(self) -> None:
        assert DEFAULT_TIMEOUT == 30.0

    def test_正常系_DEFAULT_FORMATの値が正しい(self) -> None:
        assert DEFAULT_FORMAT == "json"

    def test_正常系___all__が全定数を網羅している(self) -> None:
        import market.eodhd.constants as mod

        expected = {
            "ALLOWED_HOSTS",
            "BASE_URL",
            "DEFAULT_FORMAT",
            "DEFAULT_TIMEOUT",
            "EODHD_API_KEY_ENV",
        }
        assert set(mod.__all__) == expected
