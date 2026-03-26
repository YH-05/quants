"""Tests for market.etfcom.constants module.

Tests verify all constant definitions for the ETF.com API client module,
including bot-blocking countermeasure constants, REST API endpoint URLs,
query definitions, HTTP headers, and authentication settings.

Test TODO List:
- [x] Module exports: __all__ completeness and importability
- [x] Bot-blocking: DEFAULT_USER_AGENTS count, Mozilla prefix, uniqueness
- [x] Bot-blocking: BROWSER_IMPERSONATE_TARGETS count and non-empty
- [x] Bot-blocking: delay/timeout/headers values
- [x] Base URLs: ETFCOM_BASE_URL, ETFCOM_API_BASE_URL
- [x] API endpoints: AUTH_DETAILS_URL, FUND_DETAILS_URL, DELAYED_QUOTES_URL
- [x] API endpoints: CHARTS_URL, PERFORMANCE_URL, TICKERS_URL
- [x] Query definitions: FUND_DETAILS_QUERY_NAMES (18 items)
- [x] Authentication: AUTH_TOKEN_TTL_SECONDS
- [x] REST API: API_HEADERS
- [x] REST API: DEFAULT_TICKER_CACHE_TTL_HOURS, DEFAULT_TICKER_CACHE_SUBDIR
- [x] REST API: DEFAULT_MAX_CONCURRENCY
- [x] Deleted constants: Playwright/CSS selectors no longer exist
- [x] Final annotations: all constants annotated with typing.Final
"""

from typing import get_type_hints

from market.etfcom.constants import (
    API_HEADERS,
    AUTH_DETAILS_URL,
    AUTH_TOKEN_TTL_SECONDS,
    BROWSER_IMPERSONATE_TARGETS,
    CHARTS_URL,
    DEFAULT_DELAY_JITTER,
    DEFAULT_HEADERS,
    DEFAULT_MAX_CONCURRENCY,
    DEFAULT_MAX_RETRIES,
    DEFAULT_POLITE_DELAY,
    DEFAULT_TICKER_CACHE_SUBDIR,
    DEFAULT_TICKER_CACHE_TTL_HOURS,
    DEFAULT_TIMEOUT,
    DEFAULT_USER_AGENTS,
    DELAYED_QUOTES_URL,
    ETFCOM_API_BASE_URL,
    ETFCOM_BASE_URL,
    FUND_DETAILS_QUERY_NAMES,
    FUND_DETAILS_URL,
    PERFORMANCE_URL,
    TICKERS_URL,
    __all__,
)

# =============================================================================
# Module exports
# =============================================================================


class TestModuleExports:
    """Test module __all__ exports and structure."""

    def test_正常系_モジュールがインポートできる(self) -> None:
        """constants モジュールが正常にインポートできること。"""
        from market.etfcom import constants

        assert constants is not None

    def test_正常系_allが定義されている(self) -> None:
        """__all__ がリストとして定義されていること。"""
        assert isinstance(__all__, list)
        assert len(__all__) > 0

    def test_正常系_allの全項目がモジュールに存在する(self) -> None:
        """__all__ の全項目がモジュールの属性として存在すること。"""
        from market.etfcom import constants

        for name in __all__:
            assert hasattr(constants, name), (
                f"{name} is not defined in constants module"
            )

    def test_正常系_allが21項目を含む(self) -> None:
        """__all__ が全21定数をエクスポートしていること。"""
        assert len(__all__) == 21

    def test_正常系_モジュールDocstringが存在する(self) -> None:
        """モジュールの docstring が存在すること。"""
        from market.etfcom import constants

        assert constants.__doc__ is not None
        assert len(constants.__doc__) > 0


# =============================================================================
# Bot-blocking countermeasure constants
# =============================================================================


class TestBotBlockingConstants:
    """Test bot-blocking countermeasure constants."""

    def test_正常系_DEFAULT_USER_AGENTSが12件含む(self) -> None:
        """DEFAULT_USER_AGENTS が12種類のUser-Agent文字列を含むこと。"""
        assert isinstance(DEFAULT_USER_AGENTS, list)
        assert len(DEFAULT_USER_AGENTS) == 12

    def test_正常系_DEFAULT_USER_AGENTSが10種類以上含む(self) -> None:
        """DEFAULT_USER_AGENTS が10種類以上のUser-Agent文字列を含むこと。"""
        assert len(DEFAULT_USER_AGENTS) >= 10

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

    def test_正常系_BROWSER_IMPERSONATE_TARGETSが空文字列を含まない(self) -> None:
        """BROWSER_IMPERSONATE_TARGETS の各要素が空文字列でないこと。"""
        for target in BROWSER_IMPERSONATE_TARGETS:
            assert isinstance(target, str)
            assert len(target.strip()) > 0

    def test_正常系_DEFAULT_POLITE_DELAYが正の浮動小数点数(self) -> None:
        """DEFAULT_POLITE_DELAY が正の float (2.0) であること。"""
        assert isinstance(DEFAULT_POLITE_DELAY, float)
        assert DEFAULT_POLITE_DELAY > 0
        assert DEFAULT_POLITE_DELAY == 2.0

    def test_正常系_DEFAULT_DELAY_JITTERが正の浮動小数点数(self) -> None:
        """DEFAULT_DELAY_JITTER が正の float (1.0) であること。"""
        assert isinstance(DEFAULT_DELAY_JITTER, float)
        assert DEFAULT_DELAY_JITTER > 0
        assert DEFAULT_DELAY_JITTER == 1.0

    def test_正常系_DEFAULT_TIMEOUTが正の浮動小数点数(self) -> None:
        """DEFAULT_TIMEOUT が正の float (30.0) であること。"""
        assert isinstance(DEFAULT_TIMEOUT, float)
        assert DEFAULT_TIMEOUT > 0
        assert DEFAULT_TIMEOUT == 30.0

    def test_正常系_DEFAULT_HEADERSが必須ヘッダーを含む(self) -> None:
        """DEFAULT_HEADERS が Accept/Accept-Language/Accept-Encoding/Connection を含むこと。"""
        assert isinstance(DEFAULT_HEADERS, dict)
        assert "Accept" in DEFAULT_HEADERS
        assert "Accept-Language" in DEFAULT_HEADERS
        assert "Accept-Encoding" in DEFAULT_HEADERS
        assert "Connection" in DEFAULT_HEADERS

    def test_正常系_DEFAULT_HEADERSの値が空でない(self) -> None:
        """DEFAULT_HEADERS の各値が空文字列でないこと。"""
        for key, value in DEFAULT_HEADERS.items():
            assert isinstance(key, str)
            assert isinstance(value, str)
            assert len(value.strip()) > 0

    def test_正常系_DEFAULT_HEADERSにUserAgentが含まれない(self) -> None:
        """DEFAULT_HEADERS に User-Agent が含まれないこと（別途設定されるため）。"""
        assert "User-Agent" not in DEFAULT_HEADERS


# =============================================================================
# Base URL constants
# =============================================================================


class TestBaseURLConstants:
    """Test base URL constants."""

    def test_正常系_ETFCOM_BASE_URLがhttpsで始まる(self) -> None:
        """ETFCOM_BASE_URL が https:// で始まること。"""
        assert isinstance(ETFCOM_BASE_URL, str)
        assert ETFCOM_BASE_URL.startswith("https://")

    def test_正常系_ETFCOM_BASE_URLがetfcomドメインを含む(self) -> None:
        """ETFCOM_BASE_URL が etf.com ドメインを含むこと。"""
        assert "etf.com" in ETFCOM_BASE_URL

    def test_正常系_ETFCOM_API_BASE_URLがhttpsで始まる(self) -> None:
        """ETFCOM_API_BASE_URL が https:// で始まること。"""
        assert isinstance(ETFCOM_API_BASE_URL, str)
        assert ETFCOM_API_BASE_URL.startswith("https://")

    def test_正常系_ETFCOM_API_BASE_URLがapi_prodドメインを含む(self) -> None:
        """ETFCOM_API_BASE_URL が api-prod.etf.com ドメインを含むこと。"""
        assert "api-prod.etf.com" in ETFCOM_API_BASE_URL


# =============================================================================
# REST API endpoint URL constants
# =============================================================================


class TestAPIEndpointConstants:
    """Test REST API endpoint URL constants."""

    def test_正常系_AUTH_DETAILS_URLがetfcomドメインを含む(self) -> None:
        """AUTH_DETAILS_URL が www.etf.com ドメインを含むこと。"""
        assert isinstance(AUTH_DETAILS_URL, str)
        assert "www.etf.com" in AUTH_DETAILS_URL

    def test_正常系_AUTH_DETAILS_URLがapi_v1パスを含む(self) -> None:
        """AUTH_DETAILS_URL が /api/v1/api-details パスを含むこと。"""
        assert "/api/v1/api-details" in AUTH_DETAILS_URL

    def test_正常系_AUTH_DETAILS_URLの値が正確(self) -> None:
        """AUTH_DETAILS_URL が正確な値であること。"""
        assert AUTH_DETAILS_URL == "https://www.etf.com/api/v1/api-details"

    def test_正常系_FUND_DETAILS_URLがAPI_BASE_URLから始まる(self) -> None:
        """FUND_DETAILS_URL が ETFCOM_API_BASE_URL を基にしていること。"""
        assert isinstance(FUND_DETAILS_URL, str)
        assert FUND_DETAILS_URL.startswith(ETFCOM_API_BASE_URL)

    def test_正常系_FUND_DETAILS_URLがv2パスを含む(self) -> None:
        """FUND_DETAILS_URL が /v2/fund/fund-details パスを含むこと。"""
        assert "/v2/fund/fund-details" in FUND_DETAILS_URL

    def test_正常系_DELAYED_QUOTES_URLがAPI_BASE_URLから始まる(self) -> None:
        """DELAYED_QUOTES_URL が ETFCOM_API_BASE_URL を基にしていること。"""
        assert isinstance(DELAYED_QUOTES_URL, str)
        assert DELAYED_QUOTES_URL.startswith(ETFCOM_API_BASE_URL)

    def test_正常系_DELAYED_QUOTES_URLがdelayedquotesパスを含む(self) -> None:
        """DELAYED_QUOTES_URL が delayedquotes パスを含むこと。"""
        assert "delayedquotes" in DELAYED_QUOTES_URL

    def test_正常系_CHARTS_URLがAPI_BASE_URLから始まる(self) -> None:
        """CHARTS_URL が ETFCOM_API_BASE_URL を基にしていること。"""
        assert isinstance(CHARTS_URL, str)
        assert CHARTS_URL.startswith(ETFCOM_API_BASE_URL)

    def test_正常系_CHARTS_URLがchartsパスを含む(self) -> None:
        """CHARTS_URL が charts パスを含むこと。"""
        assert "/v2/fund/charts" in CHARTS_URL

    def test_正常系_PERFORMANCE_URLがAPI_BASE_URLから始まる(self) -> None:
        """PERFORMANCE_URL が ETFCOM_API_BASE_URL を基にしていること。"""
        assert isinstance(PERFORMANCE_URL, str)
        assert PERFORMANCE_URL.startswith(ETFCOM_API_BASE_URL)

    def test_正常系_PERFORMANCE_URLがperformanceパスを含む(self) -> None:
        """PERFORMANCE_URL が performance パスを含むこと。"""
        assert "/v2/fund/performance" in PERFORMANCE_URL

    def test_正常系_TICKERS_URLがAPI_BASE_URLから始まる(self) -> None:
        """TICKERS_URL が ETFCOM_API_BASE_URL を基にしていること。"""
        assert isinstance(TICKERS_URL, str)
        assert TICKERS_URL.startswith(ETFCOM_API_BASE_URL)

    def test_正常系_TICKERS_URLがv2パスを含む(self) -> None:
        """TICKERS_URL が /v2/fund/tickers パスを含むこと。"""
        assert "/v2/fund/tickers" in TICKERS_URL

    def test_正常系_全エンドポイントURLがhttpsで始まる(self) -> None:
        """全エンドポイント URL が https:// で始まること。"""
        endpoints = [
            AUTH_DETAILS_URL,
            FUND_DETAILS_URL,
            DELAYED_QUOTES_URL,
            CHARTS_URL,
            PERFORMANCE_URL,
            TICKERS_URL,
        ]
        for url in endpoints:
            assert url.startswith("https://"), (
                f"URL does not start with https://: {url}"
            )


# =============================================================================
# API query definitions
# =============================================================================


class TestFundDetailsQueryNames:
    """Test FUND_DETAILS_QUERY_NAMES constant."""

    def test_正常系_FUND_DETAILS_QUERY_NAMESが18件含む(self) -> None:
        """FUND_DETAILS_QUERY_NAMES が18種類のクエリ名を含むこと。"""
        assert isinstance(FUND_DETAILS_QUERY_NAMES, list)
        assert len(FUND_DETAILS_QUERY_NAMES) == 18

    def test_正常系_全クエリ名が空でない文字列(self) -> None:
        """FUND_DETAILS_QUERY_NAMES の各要素が空でない文字列であること。"""
        for name in FUND_DETAILS_QUERY_NAMES:
            assert isinstance(name, str)
            assert len(name.strip()) > 0

    def test_正常系_クエリ名が重複していない(self) -> None:
        """FUND_DETAILS_QUERY_NAMES に重複がないこと。"""
        assert len(FUND_DETAILS_QUERY_NAMES) == len(set(FUND_DETAILS_QUERY_NAMES))

    def test_正常系_fundFlowsDataが含まれる(self) -> None:
        """FUND_DETAILS_QUERY_NAMES に fundFlowsData が含まれること。"""
        assert "fundFlowsData" in FUND_DETAILS_QUERY_NAMES

    def test_正常系_topHoldingsが含まれる(self) -> None:
        """FUND_DETAILS_QUERY_NAMES に topHoldings が含まれること。"""
        assert "topHoldings" in FUND_DETAILS_QUERY_NAMES

    def test_正常系_fundPortfolioDataが含まれる(self) -> None:
        """FUND_DETAILS_QUERY_NAMES に fundPortfolioData が含まれること。"""
        assert "fundPortfolioData" in FUND_DETAILS_QUERY_NAMES

    def test_正常系_sectorIndustryBreakdownが含まれる(self) -> None:
        """FUND_DETAILS_QUERY_NAMES に sectorIndustryBreakdown が含まれること。"""
        assert "sectorIndustryBreakdown" in FUND_DETAILS_QUERY_NAMES

    def test_正常系_fundPerformanceStatsDataが含まれる(self) -> None:
        """FUND_DETAILS_QUERY_NAMES に fundPerformanceStatsData が含まれること。"""
        assert "fundPerformanceStatsData" in FUND_DETAILS_QUERY_NAMES

    def test_正常系_全クエリ名がcamelCaseである(self) -> None:
        """FUND_DETAILS_QUERY_NAMES の全要素が camelCase 形式であること。"""
        for name in FUND_DETAILS_QUERY_NAMES:
            # camelCase: starts with lowercase, no underscores, no spaces
            assert name[0].islower(), f"Query name does not start lowercase: {name}"
            assert "_" not in name, f"Query name contains underscore: {name}"
            assert " " not in name, f"Query name contains space: {name}"


# =============================================================================
# HTTP headers and authentication
# =============================================================================


class TestAPIHeadersAndAuth:
    """Test API headers and authentication constants."""

    def test_正常系_API_HEADERSがJSON_Content_Typeを含む(self) -> None:
        """API_HEADERS が application/json の Content-Type を含むこと。"""
        assert isinstance(API_HEADERS, dict)
        assert "Content-Type" in API_HEADERS
        assert "application/json" in API_HEADERS["Content-Type"]

    def test_正常系_API_HEADERSがOriginとRefererを含む(self) -> None:
        """API_HEADERS が Origin と Referer ヘッダーを含むこと（CORS対策）。"""
        assert "Origin" in API_HEADERS
        assert "Referer" in API_HEADERS
        assert "etf.com" in API_HEADERS["Origin"]
        assert "etf.com" in API_HEADERS["Referer"]

    def test_正常系_API_HEADERSの値が空でない(self) -> None:
        """API_HEADERS の各値が空文字列でないこと。"""
        for key, value in API_HEADERS.items():
            assert isinstance(key, str)
            assert isinstance(value, str)
            assert len(value.strip()) > 0, f"Header {key} has empty value"

    def test_正常系_AUTH_TOKEN_TTL_SECONDSが正の整数(self) -> None:
        """AUTH_TOKEN_TTL_SECONDS が正の整数であること。"""
        assert isinstance(AUTH_TOKEN_TTL_SECONDS, int)
        assert AUTH_TOKEN_TTL_SECONDS > 0

    def test_正常系_AUTH_TOKEN_TTL_SECONDSが24時間未満(self) -> None:
        """AUTH_TOKEN_TTL_SECONDS が24時間（86400秒）未満であること（安全マージン）。"""
        assert AUTH_TOKEN_TTL_SECONDS < 86400

    def test_正常系_AUTH_TOKEN_TTL_SECONDSが82800秒(self) -> None:
        """AUTH_TOKEN_TTL_SECONDS が82800秒（23時間）であること。"""
        assert AUTH_TOKEN_TTL_SECONDS == 82800


# =============================================================================
# Default settings
# =============================================================================


class TestDefaultSettings:
    """Test default configuration constants."""

    def test_正常系_DEFAULT_MAX_RETRIESが正の整数(self) -> None:
        """DEFAULT_MAX_RETRIES が正の整数であること。"""
        assert isinstance(DEFAULT_MAX_RETRIES, int)
        assert DEFAULT_MAX_RETRIES > 0
        assert DEFAULT_MAX_RETRIES == 3

    def test_正常系_DEFAULT_TICKER_CACHE_TTL_HOURSが正の整数(self) -> None:
        """DEFAULT_TICKER_CACHE_TTL_HOURS が正の整数 (24) であること。"""
        assert isinstance(DEFAULT_TICKER_CACHE_TTL_HOURS, int)
        assert DEFAULT_TICKER_CACHE_TTL_HOURS > 0
        assert DEFAULT_TICKER_CACHE_TTL_HOURS == 24

    def test_正常系_DEFAULT_TICKER_CACHE_SUBDIRが空でない文字列(self) -> None:
        """DEFAULT_TICKER_CACHE_SUBDIR が空でない文字列であること。"""
        assert isinstance(DEFAULT_TICKER_CACHE_SUBDIR, str)
        assert len(DEFAULT_TICKER_CACHE_SUBDIR.strip()) > 0

    def test_正常系_DEFAULT_TICKER_CACHE_SUBDIRがrawで始まる(self) -> None:
        """DEFAULT_TICKER_CACHE_SUBDIR が raw/ で始まること。"""
        assert DEFAULT_TICKER_CACHE_SUBDIR.startswith("raw/")

    def test_正常系_DEFAULT_MAX_CONCURRENCYが正の整数(self) -> None:
        """DEFAULT_MAX_CONCURRENCY が正の整数 (5) であること。"""
        assert isinstance(DEFAULT_MAX_CONCURRENCY, int)
        assert DEFAULT_MAX_CONCURRENCY > 0
        assert DEFAULT_MAX_CONCURRENCY == 5


# =============================================================================
# Deleted constants verification
# =============================================================================


class TestDeletedConstants:
    """Test that Playwright and CSS selector constants have been removed."""

    def test_正常系_STEALTH_VIEWPORTが削除されている(self) -> None:
        """STEALTH_VIEWPORT が constants モジュールに存在しないこと。"""
        from market.etfcom import constants

        assert not hasattr(constants, "STEALTH_VIEWPORT")

    def test_正常系_STEALTH_INIT_SCRIPTが削除されている(self) -> None:
        """STEALTH_INIT_SCRIPT が constants モジュールに存在しないこと。"""
        from market.etfcom import constants

        assert not hasattr(constants, "STEALTH_INIT_SCRIPT")

    def test_正常系_SCREENER_URLが削除されている(self) -> None:
        """SCREENER_URL が constants モジュールに存在しないこと。"""
        from market.etfcom import constants

        assert not hasattr(constants, "SCREENER_URL")

    def test_正常系_PROFILE_URL_TEMPLATEが削除されている(self) -> None:
        """PROFILE_URL_TEMPLATE が constants モジュールに存在しないこと。"""
        from market.etfcom import constants

        assert not hasattr(constants, "PROFILE_URL_TEMPLATE")

    def test_正常系_FUND_FLOWS_URL_TEMPLATEが削除されている(self) -> None:
        """FUND_FLOWS_URL_TEMPLATE が constants モジュールに存在しないこと。"""
        from market.etfcom import constants

        assert not hasattr(constants, "FUND_FLOWS_URL_TEMPLATE")

    def test_正常系_SUMMARY_DATA_IDが削除されている(self) -> None:
        """SUMMARY_DATA_ID が constants モジュールに存在しないこと。"""
        from market.etfcom import constants

        assert not hasattr(constants, "SUMMARY_DATA_ID")

    def test_正常系_CLASSIFICATION_DATA_IDが削除されている(self) -> None:
        """CLASSIFICATION_DATA_ID が constants モジュールに存在しないこと。"""
        from market.etfcom import constants

        assert not hasattr(constants, "CLASSIFICATION_DATA_ID")

    def test_正常系_FLOW_TABLE_IDが削除されている(self) -> None:
        """FLOW_TABLE_ID が constants モジュールに存在しないこと。"""
        from market.etfcom import constants

        assert not hasattr(constants, "FLOW_TABLE_ID")

    def test_正常系_COOKIE_CONSENT_SELECTORが削除されている(self) -> None:
        """COOKIE_CONSENT_SELECTOR が constants モジュールに存在しないこと。"""
        from market.etfcom import constants

        assert not hasattr(constants, "COOKIE_CONSENT_SELECTOR")

    def test_正常系_DISPLAY_100_SELECTORが削除されている(self) -> None:
        """DISPLAY_100_SELECTOR が constants モジュールに存在しないこと。"""
        from market.etfcom import constants

        assert not hasattr(constants, "DISPLAY_100_SELECTOR")

    def test_正常系_NEXT_PAGE_SELECTORが削除されている(self) -> None:
        """NEXT_PAGE_SELECTOR が constants モジュールに存在しないこと。"""
        from market.etfcom import constants

        assert not hasattr(constants, "NEXT_PAGE_SELECTOR")

    def test_正常系_DEFAULT_STABILITY_WAITが削除されている(self) -> None:
        """DEFAULT_STABILITY_WAIT が constants モジュールに存在しないこと。"""
        from market.etfcom import constants

        assert not hasattr(constants, "DEFAULT_STABILITY_WAIT")


# =============================================================================
# Final type annotations
# =============================================================================


class TestFinalAnnotations:
    """Test that all constants have Final type annotations."""

    def test_正常系_全定数にFinal型アノテーションが付与されている(self) -> None:
        """__all__ の全定数に typing.Final アノテーションが付与されていること。"""
        from market.etfcom import constants

        annotations = get_type_hints(constants, include_extras=True)

        for name in __all__:
            assert name in annotations, (
                f"{name} does not have a type annotation in the module"
            )
            annotation_str = str(annotations[name])
            assert "Final" in annotation_str, (
                f"{name} is not annotated with Final. Got: {annotation_str}"
            )
