"""Tests for market.edinet_api.constants module.

Tests verify all constant definitions for the EDINET disclosure API module,
including API URLs, SSRF prevention whitelist, environment variable name,
HTTP settings, and output directory.

Test TODO List:
- [x] Module exports: __all__ completeness and importability
- [x] API URL: BASE_URL format and domain
- [x] API URL: DOWNLOAD_BASE_URL format and domain
- [x] Security: ALLOWED_HOSTS contains EDINET disclosure API domains
- [x] Authentication: EDINET_FSA_API_KEY_ENV value
- [x] HTTP settings: DEFAULT_TIMEOUT, DEFAULT_POLITE_DELAY, DEFAULT_DELAY_JITTER values
- [x] Output: DEFAULT_OUTPUT_SUBDIR format
- [x] Final annotations: all constants annotated with typing.Final
"""

from typing import get_type_hints

from market.edinet_api.constants import (
    ALLOWED_HOSTS,
    BASE_URL,
    DEFAULT_DELAY_JITTER,
    DEFAULT_OUTPUT_SUBDIR,
    DEFAULT_POLITE_DELAY,
    DEFAULT_TIMEOUT,
    DOWNLOAD_BASE_URL,
    EDINET_FSA_API_KEY_ENV,
    __all__,
)

# =============================================================================
# Module exports
# =============================================================================


class TestModuleExports:
    """Test module __all__ exports and structure."""

    def test_正常系_モジュールがインポートできる(self) -> None:
        """constants モジュールが正常にインポートできること。"""
        from market.edinet_api import constants

        assert constants is not None

    def test_正常系_allが定義されている(self) -> None:
        """__all__ がリストとして定義されていること。"""
        assert isinstance(__all__, list)
        assert len(__all__) > 0

    def test_正常系_allの全項目がモジュールに存在する(self) -> None:
        """__all__ の全項目がモジュールの属性として存在すること。"""
        from market.edinet_api import constants

        for name in __all__:
            assert hasattr(constants, name), (
                f"{name} is not defined in constants module"
            )

    def test_正常系_allが8項目を含む(self) -> None:
        """__all__ が全8定数をエクスポートしていること。"""
        assert len(__all__) == 8

    def test_正常系_モジュールDocstringが存在する(self) -> None:
        """モジュールの docstring が存在すること。"""
        from market.edinet_api import constants

        assert constants.__doc__ is not None
        assert len(constants.__doc__) > 0


# =============================================================================
# API URL constants
# =============================================================================


class TestAPIURLConstants:
    """Test EDINET disclosure API URL constants."""

    def test_正常系_BASE_URLがhttpsで始まる(self) -> None:
        """BASE_URL が https:// で始まること。"""
        assert isinstance(BASE_URL, str)
        assert BASE_URL.startswith("https://")

    def test_正常系_BASE_URLがedinet_fsaドメインを含む(self) -> None:
        """BASE_URL が api.edinet-fsa.go.jp ドメインを含むこと。"""
        assert "api.edinet-fsa.go.jp" in BASE_URL

    def test_正常系_BASE_URLがv2パスを含む(self) -> None:
        """BASE_URL が /api/v2 パスを含むこと。"""
        assert "/api/v2" in BASE_URL

    def test_正常系_BASE_URLが正しい値(self) -> None:
        """BASE_URL が設計通りの値であること。"""
        assert BASE_URL == "https://api.edinet-fsa.go.jp/api/v2"

    def test_正常系_DOWNLOAD_BASE_URLがhttpsで始まる(self) -> None:
        """DOWNLOAD_BASE_URL が https:// で始まること。"""
        assert isinstance(DOWNLOAD_BASE_URL, str)
        assert DOWNLOAD_BASE_URL.startswith("https://")

    def test_正常系_DOWNLOAD_BASE_URLがdisclosure2dlドメインを含む(self) -> None:
        """DOWNLOAD_BASE_URL が disclosure2dl.edinet-fsa.go.jp を含むこと。"""
        assert "disclosure2dl.edinet-fsa.go.jp" in DOWNLOAD_BASE_URL

    def test_正常系_DOWNLOAD_BASE_URLが正しい値(self) -> None:
        """DOWNLOAD_BASE_URL が設計通りの値であること。"""
        assert DOWNLOAD_BASE_URL == "https://disclosure2dl.edinet-fsa.go.jp/api/v2"


# =============================================================================
# Security constants
# =============================================================================


class TestSecurityConstants:
    """Test SSRF prevention constants."""

    def test_正常系_ALLOWED_HOSTSがfrozensetである(self) -> None:
        """ALLOWED_HOSTS が frozenset であること。"""
        assert isinstance(ALLOWED_HOSTS, frozenset)

    def test_正常系_ALLOWED_HOSTSにapi_edinet_fsaが含まれる(self) -> None:
        """ALLOWED_HOSTS に api.edinet-fsa.go.jp が含まれること。"""
        assert "api.edinet-fsa.go.jp" in ALLOWED_HOSTS

    def test_正常系_ALLOWED_HOSTSにdisclosure2dlが含まれる(self) -> None:
        """ALLOWED_HOSTS に disclosure2dl.edinet-fsa.go.jp が含まれること。"""
        assert "disclosure2dl.edinet-fsa.go.jp" in ALLOWED_HOSTS

    def test_正常系_ALLOWED_HOSTSが2件含む(self) -> None:
        """ALLOWED_HOSTS が2つのホストを含むこと。"""
        assert len(ALLOWED_HOSTS) == 2


# =============================================================================
# Authentication constants
# =============================================================================


class TestAuthenticationConstants:
    """Test authentication environment variable constants."""

    def test_正常系_EDINET_FSA_API_KEY_ENVが文字列である(self) -> None:
        """EDINET_FSA_API_KEY_ENV が文字列であること。"""
        assert isinstance(EDINET_FSA_API_KEY_ENV, str)

    def test_正常系_EDINET_FSA_API_KEY_ENVが正しい値(self) -> None:
        """EDINET_FSA_API_KEY_ENV が設計通りの値であること。"""
        assert EDINET_FSA_API_KEY_ENV == "EDINET_FSA_API_KEY"


# =============================================================================
# HTTP settings constants
# =============================================================================


class TestHTTPSettingsConstants:
    """Test HTTP settings constants."""

    def test_正常系_DEFAULT_TIMEOUTが正の浮動小数点数(self) -> None:
        """DEFAULT_TIMEOUT が正の float (30.0) であること。"""
        assert isinstance(DEFAULT_TIMEOUT, float)
        assert DEFAULT_TIMEOUT > 0
        assert DEFAULT_TIMEOUT == 30.0

    def test_正常系_DEFAULT_POLITE_DELAYが正の浮動小数点数(self) -> None:
        """DEFAULT_POLITE_DELAY が正の float (0.5) であること。"""
        assert isinstance(DEFAULT_POLITE_DELAY, float)
        assert DEFAULT_POLITE_DELAY > 0
        assert DEFAULT_POLITE_DELAY == 0.5

    def test_正常系_DEFAULT_DELAY_JITTERが正の浮動小数点数(self) -> None:
        """DEFAULT_DELAY_JITTER が正の float (0.1) であること。"""
        assert isinstance(DEFAULT_DELAY_JITTER, float)
        assert DEFAULT_DELAY_JITTER > 0
        assert DEFAULT_DELAY_JITTER == 0.1


# =============================================================================
# Output directory constants
# =============================================================================


class TestOutputConstants:
    """Test output directory constants."""

    def test_正常系_DEFAULT_OUTPUT_SUBDIRが空でない文字列(self) -> None:
        """DEFAULT_OUTPUT_SUBDIR が空でない文字列であること。"""
        assert isinstance(DEFAULT_OUTPUT_SUBDIR, str)
        assert len(DEFAULT_OUTPUT_SUBDIR.strip()) > 0

    def test_正常系_DEFAULT_OUTPUT_SUBDIRがrawで始まる(self) -> None:
        """DEFAULT_OUTPUT_SUBDIR が raw/ で始まること。"""
        assert DEFAULT_OUTPUT_SUBDIR.startswith("raw/")

    def test_正常系_DEFAULT_OUTPUT_SUBDIRがedinet_apiを含む(self) -> None:
        """DEFAULT_OUTPUT_SUBDIR が edinet_api を含むこと。"""
        assert "edinet_api" in DEFAULT_OUTPUT_SUBDIR

    def test_正常系_DEFAULT_OUTPUT_SUBDIRが正しい値(self) -> None:
        """DEFAULT_OUTPUT_SUBDIR が設計通りの値であること。"""
        assert DEFAULT_OUTPUT_SUBDIR == "raw/edinet_api"


# =============================================================================
# Final type annotations
# =============================================================================


class TestFinalAnnotations:
    """Test that all constants have Final type annotations."""

    def test_正常系_全定数にFinal型アノテーションが付与されている(self) -> None:
        """__all__ の全定数に typing.Final アノテーションが付与されていること。"""
        from market.edinet_api import constants

        annotations = get_type_hints(constants, include_extras=True)

        for name in __all__:
            assert name in annotations, (
                f"{name} does not have a type annotation in the module"
            )
            annotation_str = str(annotations[name])
            assert "Final" in annotation_str, (
                f"{name} is not annotated with Final. Got: {annotation_str}"
            )
