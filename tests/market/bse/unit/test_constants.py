"""Tests for market.bse.constants module.

Tests verify all constant definitions for the BSE data retrieval module,
including API URL, SSRF prevention whitelist, default HTTP headers,
User-Agent rotation list, polite delay, timeout, delay jitter,
output directory, and column name mapping.

Test TODO List:
- [x] Module exports: __all__ completeness and importability
- [x] API URL: BASE_URL format and domain
- [x] Security: ALLOWED_HOSTS contains BSE domains
- [x] Bot-blocking: DEFAULT_USER_AGENTS count, Mozilla prefix, uniqueness
- [x] Bot-blocking: DEFAULT_POLITE_DELAY, DEFAULT_TIMEOUT, DEFAULT_DELAY_JITTER values
- [x] Headers: DEFAULT_HEADERS required keys and values
- [x] Output: DEFAULT_OUTPUT_SUBDIR format
- [x] Column mapping: COLUMN_NAME_MAP keys and values
- [x] Final annotations: all constants annotated with typing.Final
"""

from typing import get_type_hints

from market.bse.constants import (
    ALLOWED_HOSTS,
    BASE_URL,
    COLUMN_NAME_MAP,
    DEFAULT_DELAY_JITTER,
    DEFAULT_HEADERS,
    DEFAULT_OUTPUT_SUBDIR,
    DEFAULT_POLITE_DELAY,
    DEFAULT_TIMEOUT,
    DEFAULT_USER_AGENTS,
    __all__,
)

# =============================================================================
# Module exports
# =============================================================================


class TestModuleExports:
    """Test module __all__ exports and structure."""

    def test_正常系_モジュールがインポートできる(self) -> None:
        """constants モジュールが正常にインポートできること。"""
        from market.bse import constants

        assert constants is not None

    def test_正常系_allが定義されている(self) -> None:
        """__all__ がリストとして定義されていること。"""
        assert isinstance(__all__, list)
        assert len(__all__) > 0

    def test_正常系_allの全項目がモジュールに存在する(self) -> None:
        """__all__ の全項目がモジュールの属性として存在すること。"""
        from market.bse import constants

        for name in __all__:
            assert hasattr(constants, name), (
                f"{name} is not defined in constants module"
            )

    def test_正常系_allが12項目を含む(self) -> None:
        """__all__ が全12定数をエクスポートしていること。"""
        assert len(__all__) == 12

    def test_正常系_モジュールDocstringが存在する(self) -> None:
        """モジュールの docstring が存在すること。"""
        from market.bse import constants

        assert constants.__doc__ is not None
        assert len(constants.__doc__) > 0


# =============================================================================
# API URL constants
# =============================================================================


class TestAPIURLConstants:
    """Test BSE API URL constants."""

    def test_正常系_BASE_URLがhttpsで始まる(self) -> None:
        """BASE_URL が https:// で始まること。"""
        assert isinstance(BASE_URL, str)
        assert BASE_URL.startswith("https://")

    def test_正常系_BASE_URLがbseindiaドメインを含む(self) -> None:
        """BASE_URL が api.bseindia.com ドメインを含むこと。"""
        assert "api.bseindia.com" in BASE_URL

    def test_正常系_BASE_URLがBseIndiaAPIパスを含む(self) -> None:
        """BASE_URL が BseIndiaAPI/api パスを含むこと。"""
        assert "BseIndiaAPI/api" in BASE_URL

    def test_正常系_BASE_URLが正しい値(self) -> None:
        """BASE_URL が設計通りの値であること。"""
        assert BASE_URL == "https://api.bseindia.com/BseIndiaAPI/api"


# =============================================================================
# Security constants
# =============================================================================


class TestSecurityConstants:
    """Test SSRF prevention constants."""

    def test_正常系_ALLOWED_HOSTSがfrozensetである(self) -> None:
        """ALLOWED_HOSTS が frozenset であること。"""
        assert isinstance(ALLOWED_HOSTS, frozenset)

    def test_正常系_ALLOWED_HOSTSにapi_bseindiaが含まれる(self) -> None:
        """ALLOWED_HOSTS に api.bseindia.com が含まれること。"""
        assert "api.bseindia.com" in ALLOWED_HOSTS

    def test_正常系_ALLOWED_HOSTSにwww_bseindiaが含まれる(self) -> None:
        """ALLOWED_HOSTS に www.bseindia.com が含まれること。"""
        assert "www.bseindia.com" in ALLOWED_HOSTS

    def test_正常系_ALLOWED_HOSTSが2件含む(self) -> None:
        """ALLOWED_HOSTS が2つのホストを含むこと。"""
        assert len(ALLOWED_HOSTS) == 2


# =============================================================================
# Bot-blocking countermeasure constants
# =============================================================================


class TestBotBlockingConstants:
    """Test bot-blocking countermeasure constants."""

    def test_正常系_DEFAULT_USER_AGENTSが12件含む(self) -> None:
        """DEFAULT_USER_AGENTS が12種類のUser-Agent文字列を含むこと。"""
        assert isinstance(DEFAULT_USER_AGENTS, list)
        assert len(DEFAULT_USER_AGENTS) == 12

    def test_正常系_各UserAgentにMozillaが含まれる(self) -> None:
        """全User-AgentにMozillaプレフィックスが含まれること。"""
        for ua in DEFAULT_USER_AGENTS:
            assert "Mozilla" in ua, f"User-Agent does not contain 'Mozilla': {ua}"

    def test_正常系_UserAgent文字列が空でない(self) -> None:
        """全User-Agent文字列が空文字列でないこと。"""
        for ua in DEFAULT_USER_AGENTS:
            assert isinstance(ua, str)
            assert len(ua.strip()) > 0

    def test_正常系_UserAgentが重複していない(self) -> None:
        """User-Agent文字列に重複がないこと。"""
        assert len(DEFAULT_USER_AGENTS) == len(set(DEFAULT_USER_AGENTS))

    def test_正常系_DEFAULT_POLITE_DELAYが正の浮動小数点数(self) -> None:
        """DEFAULT_POLITE_DELAY が正の float (0.15) であること。"""
        assert isinstance(DEFAULT_POLITE_DELAY, float)
        assert DEFAULT_POLITE_DELAY > 0
        assert DEFAULT_POLITE_DELAY == 0.15

    def test_正常系_DEFAULT_TIMEOUTが正の浮動小数点数(self) -> None:
        """DEFAULT_TIMEOUT が正の float (30.0) であること。"""
        assert isinstance(DEFAULT_TIMEOUT, float)
        assert DEFAULT_TIMEOUT > 0
        assert DEFAULT_TIMEOUT == 30.0

    def test_正常系_DEFAULT_DELAY_JITTERが正の浮動小数点数(self) -> None:
        """DEFAULT_DELAY_JITTER が正の float (0.05) であること。"""
        assert isinstance(DEFAULT_DELAY_JITTER, float)
        assert DEFAULT_DELAY_JITTER > 0
        assert DEFAULT_DELAY_JITTER == 0.05


# =============================================================================
# HTTP Headers constants
# =============================================================================


class TestHTTPHeaderConstants:
    """Test default HTTP header constants."""

    def test_正常系_DEFAULT_HEADERSが必須ヘッダーを含む(self) -> None:
        """DEFAULT_HEADERS が必須ヘッダーを全て含むこと。"""
        assert isinstance(DEFAULT_HEADERS, dict)
        assert "User-Agent" in DEFAULT_HEADERS
        assert "Accept" in DEFAULT_HEADERS
        assert "Accept-Language" in DEFAULT_HEADERS
        assert "Accept-Encoding" in DEFAULT_HEADERS
        assert "Referer" in DEFAULT_HEADERS

    def test_正常系_DEFAULT_HEADERSの値が空でない(self) -> None:
        """DEFAULT_HEADERS の各値が空文字列でないこと。"""
        for key, value in DEFAULT_HEADERS.items():
            assert isinstance(key, str)
            assert isinstance(value, str)
            assert len(value.strip()) > 0, f"Header {key} has empty value"

    def test_正常系_DEFAULT_HEADERSのAcceptがJSONを含む(self) -> None:
        """DEFAULT_HEADERS の Accept が application/json を含むこと。"""
        assert "application/json" in DEFAULT_HEADERS["Accept"]

    def test_正常系_DEFAULT_HEADERSのUserAgentにMozillaが含まれる(self) -> None:
        """DEFAULT_HEADERS の User-Agent に Mozilla が含まれること。"""
        assert "Mozilla" in DEFAULT_HEADERS["User-Agent"]

    def test_正常系_DEFAULT_HEADERSのRefererがbseindiaを含む(self) -> None:
        """DEFAULT_HEADERS の Referer が bseindia.com を含むこと。"""
        assert "bseindia.com" in DEFAULT_HEADERS["Referer"]


# =============================================================================
# Output directory constants
# =============================================================================


class TestOutputConstants:
    """Test output directory constants."""

    def test_正常系_DEFAULT_OUTPUT_SUBDIRが空でない文字列(self) -> None:
        """DEFAULT_OUTPUT_SUBDIR が空でない文字列であること。"""
        assert isinstance(DEFAULT_OUTPUT_SUBDIR, str)
        assert len(DEFAULT_OUTPUT_SUBDIR.strip()) > 0

    def test_正常系_DEFAULT_OUTPUT_SUBDIRがraw_を含む(self) -> None:
        """DEFAULT_OUTPUT_SUBDIR が raw/ パスを含むこと。"""
        assert "raw/" in DEFAULT_OUTPUT_SUBDIR

    def test_正常系_DEFAULT_OUTPUT_SUBDIRがbseを含む(self) -> None:
        """DEFAULT_OUTPUT_SUBDIR が bse を含むこと。"""
        assert "bse" in DEFAULT_OUTPUT_SUBDIR

    def test_正常系_DEFAULT_OUTPUT_SUBDIRが正しい値(self) -> None:
        """DEFAULT_OUTPUT_SUBDIR が設計通りの値であること。"""
        assert DEFAULT_OUTPUT_SUBDIR == "raw/bse"


# =============================================================================
# Column name mapping constants
# =============================================================================


class TestColumnNameMapConstants:
    """Test column name mapping constants."""

    def test_正常系_COLUMN_NAME_MAPがdictである(self) -> None:
        """COLUMN_NAME_MAP が dict であること。"""
        assert isinstance(COLUMN_NAME_MAP, dict)

    def test_正常系_COLUMN_NAME_MAPが全APIカラムを含む(self) -> None:
        """COLUMN_NAME_MAP が BSE API の主要レスポンスカラムをマッピングすること。"""
        expected_keys = {
            "ScripCode",
            "ScripName",
            "ScripGroup",
            "Open",
            "High",
            "Low",
            "Close",
            "last",
            "PrevClose",
            "No_Trades",
            "No_of_Shrs",
            "Net_Turnov",
            "TotalTradedValue",
            "TotalTradedQuantity",
        }
        assert set(COLUMN_NAME_MAP.keys()) == expected_keys

    def test_正常系_COLUMN_NAME_MAPの値がsnake_caseである(self) -> None:
        """COLUMN_NAME_MAP の値が snake_case 形式であること。"""
        for key, value in COLUMN_NAME_MAP.items():
            assert isinstance(value, str)
            assert len(value.strip()) > 0, f"Mapping for {key} is empty"
            assert value == value.lower(), (
                f"Value '{value}' for key '{key}' is not lowercase"
            )
            assert " " not in value, f"Value '{value}' for key '{key}' contains spaces"

    def test_正常系_COLUMN_NAME_MAPのScripCodeがscrip_codeにマッピング(self) -> None:
        """COLUMN_NAME_MAP の ScripCode が scrip_code にマッピングされること。"""
        assert COLUMN_NAME_MAP["ScripCode"] == "scrip_code"

    def test_正常系_COLUMN_NAME_MAPのPrevCloseがprev_closeにマッピング(self) -> None:
        """COLUMN_NAME_MAP の PrevClose が prev_close にマッピングされること。"""
        assert COLUMN_NAME_MAP["PrevClose"] == "prev_close"

    def test_正常系_COLUMN_NAME_MAPのNo_Tradesがnum_tradesにマッピング(self) -> None:
        """COLUMN_NAME_MAP の No_Trades が num_trades にマッピングされること。"""
        assert COLUMN_NAME_MAP["No_Trades"] == "num_trades"

    def test_正常系_COLUMN_NAME_MAPのキーと値が重複しない(self) -> None:
        """COLUMN_NAME_MAP の値に重複がないこと。"""
        values = list(COLUMN_NAME_MAP.values())
        assert len(values) == len(set(values)), "Duplicate values in COLUMN_NAME_MAP"


# =============================================================================
# Final type annotations
# =============================================================================


class TestFinalAnnotations:
    """Test that all constants have Final type annotations."""

    def test_正常系_全定数にFinal型アノテーションが付与されている(self) -> None:
        """__all__ の全定数に typing.Final アノテーションが付与されていること。"""
        from market.bse import constants

        annotations = get_type_hints(constants, include_extras=True)

        for name in __all__:
            assert name in annotations, (
                f"{name} does not have a type annotation in the module"
            )
            annotation_str = str(annotations[name])
            assert "Final" in annotation_str, (
                f"{name} is not annotated with Final. Got: {annotation_str}"
            )
