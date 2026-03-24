"""Tests for market.nasdaq.constants module.

Tests verify all constant definitions for the NASDAQ Stock Screener module,
including API URL, default HTTP headers, User-Agent rotation list,
browser impersonation targets, polite delay, timeout, delay jitter,
output directory, and column name mapping.

Test TODO List:
- [x] Module exports: __all__ completeness and importability
- [x] API URL: NASDAQ_SCREENER_URL format and domain
- [x] Bot-blocking: DEFAULT_USER_AGENTS count, Mozilla prefix, uniqueness
- [x] Bot-blocking: BROWSER_IMPERSONATE_TARGETS count and non-empty
- [x] Bot-blocking: DEFAULT_POLITE_DELAY, DEFAULT_TIMEOUT, DEFAULT_DELAY_JITTER values
- [x] Headers: DEFAULT_HEADERS required keys and values
- [x] Output: DEFAULT_OUTPUT_DIR format
- [x] Column mapping: COLUMN_NAME_MAP keys and values
- [x] Final annotations: all constants annotated with typing.Final
"""

from typing import get_type_hints

from market.nasdaq.constants import (
    BROWSER_IMPERSONATE_TARGETS,
    COLUMN_NAME_MAP,
    DEFAULT_DELAY_JITTER,
    DEFAULT_HEADERS,
    DEFAULT_OUTPUT_DIR,
    DEFAULT_POLITE_DELAY,
    DEFAULT_TIMEOUT,
    DEFAULT_USER_AGENTS,
    NASDAQ_SCREENER_URL,
    __all__,
)

# =============================================================================
# Module exports
# =============================================================================


class TestModuleExports:
    """Test module __all__ exports and structure."""

    def test_正常系_モジュールがインポートできる(self) -> None:
        """constants モジュールが正常にインポートできること。"""
        from market.nasdaq import constants

        assert constants is not None

    def test_正常系_allが定義されている(self) -> None:
        """__all__ がリストとして定義されていること。"""
        assert isinstance(__all__, list)
        assert len(__all__) > 0

    def test_正常系_allの全項目がモジュールに存在する(self) -> None:
        """__all__ の全項目がモジュールの属性として存在すること。"""
        from market.nasdaq import constants

        for name in __all__:
            assert hasattr(constants, name), (
                f"{name} is not defined in constants module"
            )

    def test_正常系_allが23項目を含む(self) -> None:
        """__all__ が全23定数をエクスポートしていること。"""
        assert len(__all__) == 23

    def test_正常系_モジュールDocstringが存在する(self) -> None:
        """モジュールの docstring が存在すること。"""
        from market.nasdaq import constants

        assert constants.__doc__ is not None
        assert len(constants.__doc__) > 0


# =============================================================================
# API URL constants
# =============================================================================


class TestAPIURLConstants:
    """Test NASDAQ API URL constants."""

    def test_正常系_NASDAQ_SCREENER_URLがhttpsで始まる(self) -> None:
        """NASDAQ_SCREENER_URL が https:// で始まること。"""
        assert isinstance(NASDAQ_SCREENER_URL, str)
        assert NASDAQ_SCREENER_URL.startswith("https://")

    def test_正常系_NASDAQ_SCREENER_URLがnasdaqドメインを含む(self) -> None:
        """NASDAQ_SCREENER_URL が api.nasdaq.com ドメインを含むこと。"""
        assert "api.nasdaq.com" in NASDAQ_SCREENER_URL

    def test_正常系_NASDAQ_SCREENER_URLがscreener_stocksパスを含む(self) -> None:
        """NASDAQ_SCREENER_URL が screener/stocks パスを含むこと。"""
        assert "screener/stocks" in NASDAQ_SCREENER_URL

    def test_正常系_NASDAQ_SCREENER_URLが正しい値(self) -> None:
        """NASDAQ_SCREENER_URL が設計通りの値であること。"""
        assert NASDAQ_SCREENER_URL == "https://api.nasdaq.com/api/screener/stocks"


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

    def test_正常系_BROWSER_IMPERSONATE_TARGETSが5種類以上含む(self) -> None:
        """BROWSER_IMPERSONATE_TARGETS が5種類以上含むこと。"""
        assert isinstance(BROWSER_IMPERSONATE_TARGETS, list)
        assert len(BROWSER_IMPERSONATE_TARGETS) >= 5

    def test_正常系_BROWSER_IMPERSONATE_TARGETSにchromeが含まれる(self) -> None:
        """BROWSER_IMPERSONATE_TARGETS にデフォルトの 'chrome' が含まれること。"""
        assert "chrome" in BROWSER_IMPERSONATE_TARGETS

    def test_正常系_BROWSER_IMPERSONATE_TARGETSにchrome120が含まれる(self) -> None:
        """BROWSER_IMPERSONATE_TARGETS に 'chrome120' が含まれること。"""
        assert "chrome120" in BROWSER_IMPERSONATE_TARGETS

    def test_正常系_BROWSER_IMPERSONATE_TARGETSが空文字列を含まない(self) -> None:
        """BROWSER_IMPERSONATE_TARGETS の各要素が空文字列でないこと。"""
        for target in BROWSER_IMPERSONATE_TARGETS:
            assert isinstance(target, str)
            assert len(target.strip()) > 0

    def test_正常系_DEFAULT_POLITE_DELAYが正の浮動小数点数(self) -> None:
        """DEFAULT_POLITE_DELAY が正の float (1.0) であること。"""
        assert isinstance(DEFAULT_POLITE_DELAY, float)
        assert DEFAULT_POLITE_DELAY > 0
        assert DEFAULT_POLITE_DELAY == 1.0

    def test_正常系_DEFAULT_TIMEOUTが正の浮動小数点数(self) -> None:
        """DEFAULT_TIMEOUT が正の float (30.0) であること。"""
        assert isinstance(DEFAULT_TIMEOUT, float)
        assert DEFAULT_TIMEOUT > 0
        assert DEFAULT_TIMEOUT == 30.0

    def test_正常系_DEFAULT_DELAY_JITTERが正の浮動小数点数(self) -> None:
        """DEFAULT_DELAY_JITTER が正の float (0.5) であること。"""
        assert isinstance(DEFAULT_DELAY_JITTER, float)
        assert DEFAULT_DELAY_JITTER > 0
        assert DEFAULT_DELAY_JITTER == 0.5


# =============================================================================
# HTTP Headers constants
# =============================================================================


class TestHTTPHeaderConstants:
    """Test default HTTP header constants."""

    def test_正常系_DEFAULT_HEADERSが必須ヘッダーを含む(self) -> None:
        """DEFAULT_HEADERS が User-Agent/Accept/Accept-Language/Accept-Encoding を含むこと。"""
        assert isinstance(DEFAULT_HEADERS, dict)
        assert "User-Agent" in DEFAULT_HEADERS
        assert "Accept" in DEFAULT_HEADERS
        assert "Accept-Language" in DEFAULT_HEADERS
        assert "Accept-Encoding" in DEFAULT_HEADERS

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


# =============================================================================
# Output directory constants
# =============================================================================


class TestOutputConstants:
    """Test output directory constants."""

    def test_正常系_DEFAULT_OUTPUT_DIRが空でない文字列(self) -> None:
        """DEFAULT_OUTPUT_DIR が空でない文字列であること。"""
        assert isinstance(DEFAULT_OUTPUT_DIR, str)
        assert len(DEFAULT_OUTPUT_DIR.strip()) > 0

    def test_正常系_DEFAULT_OUTPUT_DIRがdata_rawを含む(self) -> None:
        """DEFAULT_OUTPUT_DIR が data/raw パスを含むこと。"""
        assert "data/raw" in DEFAULT_OUTPUT_DIR

    def test_正常系_DEFAULT_OUTPUT_DIRがnasdaqを含む(self) -> None:
        """DEFAULT_OUTPUT_DIR が nasdaq を含むこと。"""
        assert "nasdaq" in DEFAULT_OUTPUT_DIR

    def test_正常系_DEFAULT_OUTPUT_DIRが正しい値(self) -> None:
        """DEFAULT_OUTPUT_DIR が設計通りの値であること。"""
        assert DEFAULT_OUTPUT_DIR == "data/raw/nasdaq"


# =============================================================================
# Column name mapping constants
# =============================================================================


class TestColumnNameMapConstants:
    """Test column name mapping constants."""

    def test_正常系_COLUMN_NAME_MAPがdictである(self) -> None:
        """COLUMN_NAME_MAP が dict であること。"""
        assert isinstance(COLUMN_NAME_MAP, dict)

    def test_正常系_COLUMN_NAME_MAPが全APIカラムを含む(self) -> None:
        """COLUMN_NAME_MAP が NASDAQ API の全レスポンスカラムをマッピングすること。"""
        expected_keys = {
            "symbol",
            "name",
            "lastsale",
            "netchange",
            "pctchange",
            "marketCap",
            "country",
            "ipoyear",
            "volume",
            "sector",
            "industry",
            "url",
        }
        assert set(COLUMN_NAME_MAP.keys()) == expected_keys

    def test_正常系_COLUMN_NAME_MAPの値がsnake_caseである(self) -> None:
        """COLUMN_NAME_MAP の値が snake_case 形式であること。"""
        for key, value in COLUMN_NAME_MAP.items():
            assert isinstance(value, str)
            assert len(value.strip()) > 0, f"Mapping for {key} is empty"
            # snake_case: lowercase with underscores only
            assert value == value.lower(), (
                f"Value '{value}' for key '{key}' is not lowercase"
            )
            assert " " not in value, f"Value '{value}' for key '{key}' contains spaces"

    def test_正常系_COLUMN_NAME_MAPのmarketCapがmarket_capにマッピング(self) -> None:
        """COLUMN_NAME_MAP の marketCap が market_cap にマッピングされること。"""
        assert COLUMN_NAME_MAP["marketCap"] == "market_cap"

    def test_正常系_COLUMN_NAME_MAPのlastsaleがlast_saleにマッピング(self) -> None:
        """COLUMN_NAME_MAP の lastsale が last_sale にマッピングされること。"""
        assert COLUMN_NAME_MAP["lastsale"] == "last_sale"

    def test_正常系_COLUMN_NAME_MAPのnetchangeがnet_changeにマッピング(self) -> None:
        """COLUMN_NAME_MAP の netchange が net_change にマッピングされること。"""
        assert COLUMN_NAME_MAP["netchange"] == "net_change"

    def test_正常系_COLUMN_NAME_MAPのpctchangeがpct_changeにマッピング(self) -> None:
        """COLUMN_NAME_MAP の pctchange が pct_change にマッピングされること。"""
        assert COLUMN_NAME_MAP["pctchange"] == "pct_change"

    def test_正常系_COLUMN_NAME_MAPのipoyearがipo_yearにマッピング(self) -> None:
        """COLUMN_NAME_MAP の ipoyear が ipo_year にマッピングされること。"""
        assert COLUMN_NAME_MAP["ipoyear"] == "ipo_year"

    def test_正常系_COLUMN_NAME_MAPのsymbolがsymbolにマッピング(self) -> None:
        """COLUMN_NAME_MAP の symbol が symbol のままであること。"""
        assert COLUMN_NAME_MAP["symbol"] == "symbol"

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
        from market.nasdaq import constants

        annotations = get_type_hints(constants, include_extras=True)

        for name in __all__:
            assert name in annotations, (
                f"{name} does not have a type annotation in the module"
            )
            annotation_str = str(annotations[name])
            assert "Final" in annotation_str, (
                f"{name} is not annotated with Final. Got: {annotation_str}"
            )
