"""Tests for market.etfcom.constants module.

Tests verify all constant definitions for the ETF.com API client module,
including bot-blocking countermeasure constants, REST API endpoint URLs,
query definitions, and authentication settings.
"""

from typing import get_type_hints


class TestModuleExports:
    """Test module __all__ exports and structure."""

    def test_正常系_モジュールがインポートできる(self) -> None:
        from market.etfcom import constants

        assert constants is not None

    def test_正常系_allが定義されている(self) -> None:
        from market.etfcom.constants import __all__

        assert isinstance(__all__, list)
        assert len(__all__) > 0

    def test_正常系_allの全項目がモジュールに存在する(self) -> None:
        from market.etfcom import constants
        from market.etfcom.constants import __all__

        for name in __all__:
            assert hasattr(constants, name), (
                f"{name} is not defined in constants module"
            )

    def test_正常系_モジュールDocstringが存在する(self) -> None:
        from market.etfcom import constants

        assert constants.__doc__ is not None
        assert len(constants.__doc__) > 0


class TestBotBlockingConstants:
    """Test bot-blocking countermeasure constants."""

    def test_正常系_DEFAULT_USER_AGENTSが10種類以上含む(self) -> None:
        from market.etfcom.constants import DEFAULT_USER_AGENTS

        assert isinstance(DEFAULT_USER_AGENTS, list)
        assert len(DEFAULT_USER_AGENTS) >= 10

    def test_正常系_各UserAgentにMozillaが含まれる(self) -> None:
        from market.etfcom.constants import DEFAULT_USER_AGENTS

        for ua in DEFAULT_USER_AGENTS:
            assert "Mozilla" in ua, f"User-Agent does not contain 'Mozilla': {ua}"

    def test_正常系_UserAgent文字列が空でない(self) -> None:
        from market.etfcom.constants import DEFAULT_USER_AGENTS

        for ua in DEFAULT_USER_AGENTS:
            assert isinstance(ua, str)
            assert len(ua.strip()) > 0

    def test_正常系_UserAgentが重複していない(self) -> None:
        from market.etfcom.constants import DEFAULT_USER_AGENTS

        assert len(DEFAULT_USER_AGENTS) == len(set(DEFAULT_USER_AGENTS))

    def test_正常系_BROWSER_IMPERSONATE_TARGETSが5種類以上含む(self) -> None:
        from market.etfcom.constants import BROWSER_IMPERSONATE_TARGETS

        assert isinstance(BROWSER_IMPERSONATE_TARGETS, list)
        assert len(BROWSER_IMPERSONATE_TARGETS) >= 5

    def test_正常系_BROWSER_IMPERSONATE_TARGETSが空文字列を含まない(self) -> None:
        from market.etfcom.constants import BROWSER_IMPERSONATE_TARGETS

        for target in BROWSER_IMPERSONATE_TARGETS:
            assert isinstance(target, str)
            assert len(target.strip()) > 0

    def test_正常系_DEFAULT_POLITE_DELAYが正の浮動小数点数(self) -> None:
        from market.etfcom.constants import DEFAULT_POLITE_DELAY

        assert isinstance(DEFAULT_POLITE_DELAY, float)
        assert DEFAULT_POLITE_DELAY > 0
        assert DEFAULT_POLITE_DELAY == 2.0

    def test_正常系_DEFAULT_DELAY_JITTERが正の浮動小数点数(self) -> None:
        from market.etfcom.constants import DEFAULT_DELAY_JITTER

        assert isinstance(DEFAULT_DELAY_JITTER, float)
        assert DEFAULT_DELAY_JITTER > 0
        assert DEFAULT_DELAY_JITTER == 1.0

    def test_正常系_DEFAULT_TIMEOUTが正の浮動小数点数(self) -> None:
        from market.etfcom.constants import DEFAULT_TIMEOUT

        assert isinstance(DEFAULT_TIMEOUT, float)
        assert DEFAULT_TIMEOUT > 0
        assert DEFAULT_TIMEOUT == 30.0

    def test_正常系_DEFAULT_HEADERSが必須ヘッダーを含む(self) -> None:
        from market.etfcom.constants import DEFAULT_HEADERS

        assert isinstance(DEFAULT_HEADERS, dict)
        assert "Accept" in DEFAULT_HEADERS
        assert "Accept-Language" in DEFAULT_HEADERS
        assert "Accept-Encoding" in DEFAULT_HEADERS
        assert "Connection" in DEFAULT_HEADERS

    def test_正常系_DEFAULT_HEADERSの値が空でない(self) -> None:
        from market.etfcom.constants import DEFAULT_HEADERS

        for key, value in DEFAULT_HEADERS.items():
            assert isinstance(key, str)
            assert isinstance(value, str)
            assert len(value.strip()) > 0


class TestBaseURLConstants:
    """Test base URL constants."""

    def test_正常系_ETFCOM_BASE_URLがhttpsで始まる(self) -> None:
        from market.etfcom.constants import ETFCOM_BASE_URL

        assert isinstance(ETFCOM_BASE_URL, str)
        assert ETFCOM_BASE_URL.startswith("https://")

    def test_正常系_ETFCOM_BASE_URLがetfcomドメインを含む(self) -> None:
        from market.etfcom.constants import ETFCOM_BASE_URL

        assert "etf.com" in ETFCOM_BASE_URL

    def test_正常系_ETFCOM_API_BASE_URLがhttpsで始まる(self) -> None:
        from market.etfcom.constants import ETFCOM_API_BASE_URL

        assert isinstance(ETFCOM_API_BASE_URL, str)
        assert ETFCOM_API_BASE_URL.startswith("https://")

    def test_正常系_ETFCOM_API_BASE_URLがapi_prodドメインを含む(self) -> None:
        from market.etfcom.constants import ETFCOM_API_BASE_URL

        assert "api-prod.etf.com" in ETFCOM_API_BASE_URL


class TestAPIEndpointConstants:
    """Test REST API endpoint URL constants."""

    def test_正常系_AUTH_DETAILS_URLが正確な値を持つ(self) -> None:
        from market.etfcom.constants import AUTH_DETAILS_URL

        assert AUTH_DETAILS_URL == "https://www.etf.com/api/v1/api-details"

    def test_正常系_FUND_DETAILS_URLがv2パスを含む(self) -> None:
        from market.etfcom.constants import FUND_DETAILS_URL

        assert "/v2/fund/fund-details" in FUND_DETAILS_URL

    def test_正常系_TICKERS_URLがv2パスを含む(self) -> None:
        from market.etfcom.constants import TICKERS_URL

        assert "/v2/fund/tickers" in TICKERS_URL

    def test_正常系_DELAYED_QUOTES_URLがdelayedquotesパスを含む(self) -> None:
        from market.etfcom.constants import DELAYED_QUOTES_URL

        assert "delayedquotes" in DELAYED_QUOTES_URL

    def test_正常系_CHARTS_URLがchartsパスを含む(self) -> None:
        from market.etfcom.constants import CHARTS_URL

        assert "/v2/fund/charts" in CHARTS_URL

    def test_正常系_PERFORMANCE_URLがperformanceパスを含む(self) -> None:
        from market.etfcom.constants import PERFORMANCE_URL

        assert "/v2/fund/performance" in PERFORMANCE_URL


class TestFundDetailsQueryNames:
    """Test FUND_DETAILS_QUERY_NAMES constant."""

    def test_正常系_FUND_DETAILS_QUERY_NAMESが18件含む(self) -> None:
        from market.etfcom.constants import FUND_DETAILS_QUERY_NAMES

        assert isinstance(FUND_DETAILS_QUERY_NAMES, list)
        assert len(FUND_DETAILS_QUERY_NAMES) == 18

    def test_正常系_全クエリ名が空でない文字列(self) -> None:
        from market.etfcom.constants import FUND_DETAILS_QUERY_NAMES

        for name in FUND_DETAILS_QUERY_NAMES:
            assert isinstance(name, str)
            assert len(name.strip()) > 0

    def test_正常系_クエリ名が重複していない(self) -> None:
        from market.etfcom.constants import FUND_DETAILS_QUERY_NAMES

        assert len(FUND_DETAILS_QUERY_NAMES) == len(set(FUND_DETAILS_QUERY_NAMES))

    def test_正常系_fundFlowsDataが含まれる(self) -> None:
        from market.etfcom.constants import FUND_DETAILS_QUERY_NAMES

        assert "fundFlowsData" in FUND_DETAILS_QUERY_NAMES


class TestAPIHeadersAndAuth:
    """Test API headers and authentication constants."""

    def test_正常系_API_HEADERSがJSON_Content_Typeを含む(self) -> None:
        from market.etfcom.constants import API_HEADERS

        assert isinstance(API_HEADERS, dict)
        assert "Content-Type" in API_HEADERS
        assert "application/json" in API_HEADERS["Content-Type"]

    def test_正常系_API_HEADERSがOriginとRefererを含む(self) -> None:
        from market.etfcom.constants import API_HEADERS

        assert "Origin" in API_HEADERS
        assert "Referer" in API_HEADERS

    def test_正常系_AUTH_TOKEN_TTL_SECONDSが正の整数(self) -> None:
        from market.etfcom.constants import AUTH_TOKEN_TTL_SECONDS

        assert isinstance(AUTH_TOKEN_TTL_SECONDS, int)
        assert AUTH_TOKEN_TTL_SECONDS > 0

    def test_正常系_AUTH_TOKEN_TTL_SECONDSが24時間未満(self) -> None:
        from market.etfcom.constants import AUTH_TOKEN_TTL_SECONDS

        assert AUTH_TOKEN_TTL_SECONDS < 86400


class TestDefaultSettings:
    """Test default configuration constants."""

    def test_正常系_DEFAULT_MAX_RETRIESが正の整数(self) -> None:
        from market.etfcom.constants import DEFAULT_MAX_RETRIES

        assert isinstance(DEFAULT_MAX_RETRIES, int)
        assert DEFAULT_MAX_RETRIES > 0

    def test_正常系_DEFAULT_TICKER_CACHE_TTL_HOURSが正の整数(self) -> None:
        from market.etfcom.constants import DEFAULT_TICKER_CACHE_TTL_HOURS

        assert isinstance(DEFAULT_TICKER_CACHE_TTL_HOURS, int)
        assert DEFAULT_TICKER_CACHE_TTL_HOURS > 0

    def test_正常系_DEFAULT_MAX_CONCURRENCYが正の整数(self) -> None:
        from market.etfcom.constants import DEFAULT_MAX_CONCURRENCY

        assert isinstance(DEFAULT_MAX_CONCURRENCY, int)
        assert DEFAULT_MAX_CONCURRENCY > 0


class TestDeletedConstants:
    """Test that Playwright and CSS selector constants have been removed."""

    def test_正常系_Playwright関連定数が削除されている(self) -> None:
        from market.etfcom import constants

        deleted_names = [
            "STEALTH_VIEWPORT",
            "STEALTH_INIT_SCRIPT",
            "SCREENER_URL",
            "PROFILE_URL_TEMPLATE",
            "FUND_FLOWS_URL_TEMPLATE",
            "SUMMARY_DATA_ID",
            "CLASSIFICATION_DATA_ID",
            "FLOW_TABLE_ID",
            "COOKIE_CONSENT_SELECTOR",
            "DISPLAY_100_SELECTOR",
            "NEXT_PAGE_SELECTOR",
            "DEFAULT_STABILITY_WAIT",
        ]
        for name in deleted_names:
            assert not hasattr(constants, name), (
                f"{name} should have been deleted but still exists"
            )


class TestFinalAnnotations:
    """Test that all constants have Final type annotations."""

    def test_正常系_全定数にFinal型アノテーションが付与されている(self) -> None:
        from market.etfcom import constants
        from market.etfcom.constants import __all__

        annotations = get_type_hints(constants, include_extras=True)

        for name in __all__:
            assert name in annotations, (
                f"{name} does not have a type annotation in the module"
            )
            annotation_str = str(annotations[name])
            assert "Final" in annotation_str, (
                f"{name} is not annotated with Final. Got: {annotation_str}"
            )
