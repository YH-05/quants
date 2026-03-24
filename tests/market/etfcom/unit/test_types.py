"""Unit tests for market.etfcom.types module.

Tests cover:
- ScrapingConfig: bot-blocking countermeasure configuration
- RetryConfig: exponential backoff configuration
- TickerInfo: ticker API response data
- AuthConfig: API authentication configuration (NEW - Wave 1)
- Verification that legacy record types have been removed
- Module __all__ exports
"""

from datetime import datetime, timezone

import pytest

# ---------------------------------------------------------------------------
# ScrapingConfig tests
# ---------------------------------------------------------------------------


class TestScrapingConfig:
    """Tests for ScrapingConfig dataclass."""

    def test_正常系_デフォルト値で初期化(self) -> None:
        """ScrapingConfig がデフォルト値で初期化されることを確認。"""
        from market.etfcom.types import ScrapingConfig

        config = ScrapingConfig()
        assert config.polite_delay == 2.0
        assert config.delay_jitter == 1.0
        assert config.user_agents == ()
        assert config.impersonate == "chrome"
        assert config.timeout == 30.0
        assert config.headless is True
        assert config.stability_wait == 2.0
        assert config.max_page_retries == 5

    def test_正常系_カスタム値で初期化(self) -> None:
        """ScrapingConfig がカスタム値で初期化されることを確認。"""
        from market.etfcom.types import ScrapingConfig

        config = ScrapingConfig(
            polite_delay=5.0,
            delay_jitter=2.0,
            user_agents=("UA1", "UA2"),
            impersonate="edge99",
            timeout=60.0,
            headless=False,
            stability_wait=3.0,
            max_page_retries=10,
        )
        assert config.polite_delay == 5.0
        assert config.delay_jitter == 2.0
        assert config.user_agents == ("UA1", "UA2")
        assert config.impersonate == "edge99"
        assert config.timeout == 60.0
        assert config.headless is False
        assert config.stability_wait == 3.0
        assert config.max_page_retries == 10

    def test_正常系_frozenであること(self) -> None:
        """ScrapingConfig が frozen であり属性の変更が禁止されることを確認。"""
        from market.etfcom.types import ScrapingConfig

        config = ScrapingConfig()
        with pytest.raises(AttributeError):
            config.polite_delay = 99.0

    def test_正常系_constants_pyのデフォルト値と整合(self) -> None:
        """ScrapingConfig のデフォルト値が constants.py の定数と整合することを確認。"""
        from market.etfcom.constants import (
            DEFAULT_DELAY_JITTER,
            DEFAULT_POLITE_DELAY,
            DEFAULT_TIMEOUT,
        )
        from market.etfcom.types import _LEGACY_STABILITY_WAIT, ScrapingConfig

        config = ScrapingConfig()
        assert config.polite_delay == DEFAULT_POLITE_DELAY
        assert config.delay_jitter == DEFAULT_DELAY_JITTER
        assert config.timeout == DEFAULT_TIMEOUT
        assert config.stability_wait == _LEGACY_STABILITY_WAIT
        # max_page_retries はスクレイピング固有のリトライであり、
        # DEFAULT_MAX_RETRIES (HTTP リトライ) とは異なる用途のため値は異なる
        assert isinstance(config.max_page_retries, int)


# ---------------------------------------------------------------------------
# RetryConfig tests
# ---------------------------------------------------------------------------


class TestRetryConfig:
    """Tests for RetryConfig dataclass."""

    def test_正常系_デフォルト値で初期化(self) -> None:
        """RetryConfig がデフォルト値で初期化されることを確認。"""
        from market.etfcom.types import RetryConfig

        config = RetryConfig()
        assert config.max_attempts == 3
        assert config.initial_delay == 1.0
        assert config.max_delay == 30.0
        assert config.exponential_base == 2.0
        assert config.jitter is True

    def test_正常系_カスタム値で初期化(self) -> None:
        """RetryConfig がカスタム値で初期化されることを確認。"""
        from market.etfcom.types import RetryConfig

        config = RetryConfig(max_attempts=5, initial_delay=0.5, max_delay=60.0)
        assert config.max_attempts == 5
        assert config.initial_delay == 0.5
        assert config.max_delay == 60.0

    def test_正常系_frozenであること(self) -> None:
        """RetryConfig が frozen であり属性の変更が禁止されることを確認。"""
        from market.etfcom.types import RetryConfig

        config = RetryConfig()
        with pytest.raises(AttributeError):
            config.max_attempts = 99


# ---------------------------------------------------------------------------
# TickerInfo tests
# ---------------------------------------------------------------------------


class TestTickerInfo:
    """Tests for TickerInfo dataclass."""

    def test_正常系_全フィールドで初期化(self) -> None:
        """TickerInfo が全6フィールドで初期化されることを確認。"""
        from market.etfcom.types import TickerInfo

        info = TickerInfo(
            ticker="SPY",
            fund_id=1,
            name="SPDR S&P 500 ETF Trust",
            issuer="State Street",
            asset_class="Equity",
            inception_date="1993-01-22",
        )
        assert info.ticker == "SPY"
        assert info.fund_id == 1
        assert info.name == "SPDR S&P 500 ETF Trust"
        assert info.issuer == "State Street"
        assert info.asset_class == "Equity"
        assert info.inception_date == "1993-01-22"

    def test_正常系_frozenであること(self) -> None:
        """TickerInfo が frozen であり属性の変更が禁止されることを確認。"""
        from market.etfcom.types import TickerInfo

        info = TickerInfo(
            ticker="SPY",
            fund_id=1,
            name="SPDR S&P 500 ETF Trust",
            issuer="State Street",
            asset_class="Equity",
            inception_date="1993-01-22",
        )
        with pytest.raises(AttributeError):
            info.ticker = "VOO"

    def test_正常系_フィールド数が6であること(self) -> None:
        """TickerInfo のフィールド数が6であることを確認。"""
        import dataclasses

        from market.etfcom.types import TickerInfo

        fields = dataclasses.fields(TickerInfo)
        assert len(fields) == 6

    def test_正常系_Optionalフィールドで初期化可能(self) -> None:
        """TickerInfo が Optional フィールドを None で初期化可能であることを確認。"""
        from market.etfcom.types import TickerInfo

        info = TickerInfo(
            ticker="UNKNOWN",
            fund_id=99999,
            name="Unknown ETF",
            issuer=None,
            asset_class=None,
            inception_date=None,
        )
        assert info.ticker == "UNKNOWN"
        assert info.fund_id == 99999
        assert info.issuer is None
        assert info.asset_class is None
        assert info.inception_date is None


# ---------------------------------------------------------------------------
# AuthConfig tests (NEW - Wave 1)
# ---------------------------------------------------------------------------


class TestAuthConfig:
    """Tests for AuthConfig dataclass.

    AuthConfig stores API authentication credentials returned by the
    ETF.com ``/api/v1/api-details`` endpoint. It has 7 fields matching
    the API response structure plus a ``fetched_at`` timestamp for
    cache TTL tracking.
    """

    def test_正常系_全フィールドで初期化(self) -> None:
        """AuthConfig が全7フィールドで初期化されることを確認。"""
        from market.etfcom.types import AuthConfig

        now = datetime.now(tz=timezone.utc)
        auth = AuthConfig(
            api_base_url="https://api-prod.etf.com",
            fund_api_key="fund-key-123",
            tools_api_key="tools-key-456",
            oauth_token="oauth-token-789",
            real_time_api_url="https://real-time-prod.etf.com/graphql",
            graphql_api_url="https://data.etf.com",
            fetched_at=now,
        )
        assert auth.api_base_url == "https://api-prod.etf.com"
        assert auth.fund_api_key == "fund-key-123"
        assert auth.tools_api_key == "tools-key-456"
        assert auth.oauth_token == "oauth-token-789"
        assert auth.real_time_api_url == "https://real-time-prod.etf.com/graphql"
        assert auth.graphql_api_url == "https://data.etf.com"
        assert auth.fetched_at == now

    def test_正常系_frozenであること(self) -> None:
        """AuthConfig が frozen であり属性の変更が禁止されることを確認。"""
        from market.etfcom.types import AuthConfig

        auth = AuthConfig(
            api_base_url="https://api-prod.etf.com",
            fund_api_key="key",
            tools_api_key="key",
            oauth_token="token",
            real_time_api_url="https://real-time-prod.etf.com/graphql",
            graphql_api_url="https://data.etf.com",
            fetched_at=datetime.now(tz=timezone.utc),
        )
        with pytest.raises(AttributeError):
            auth.oauth_token = "new-token"

    def test_正常系_フィールド数が7であること(self) -> None:
        """AuthConfig のフィールド数が7であることを確認。"""
        import dataclasses

        from market.etfcom.types import AuthConfig

        fields = dataclasses.fields(AuthConfig)
        assert len(fields) == 7

    def test_正常系_機密フィールドがreprに含まれない(self) -> None:
        """AuthConfig の機密フィールド（API キー、OAuth トークン）が repr に含まれないことを確認。

        CWE-532 (Information Exposure Through Log Files) 対策として、
        機密情報は repr 出力から除外されるべき。
        """
        from market.etfcom.types import AuthConfig

        auth = AuthConfig(
            api_base_url="https://api-prod.etf.com",
            fund_api_key="secret-fund-key",
            tools_api_key="secret-tools-key",
            oauth_token="secret-oauth-token",
            real_time_api_url="https://real-time-prod.etf.com/graphql",
            graphql_api_url="https://data.etf.com",
            fetched_at=datetime.now(tz=timezone.utc),
        )
        repr_str = repr(auth)
        assert "secret-fund-key" not in repr_str
        assert "secret-tools-key" not in repr_str
        assert "secret-oauth-token" not in repr_str

    def test_正常系_fetched_atがdatetime型(self) -> None:
        """AuthConfig の fetched_at が datetime 型であることを確認。"""
        from market.etfcom.types import AuthConfig

        now = datetime.now(tz=timezone.utc)
        auth = AuthConfig(
            api_base_url="https://api-prod.etf.com",
            fund_api_key="key",
            tools_api_key="key",
            oauth_token="token",
            real_time_api_url="https://real-time-prod.etf.com/graphql",
            graphql_api_url="https://data.etf.com",
            fetched_at=now,
        )
        assert isinstance(auth.fetched_at, datetime)

    def test_正常系_api_base_urlがreprに含まれる(self) -> None:
        """AuthConfig の非機密フィールド（URL）が repr に含まれることを確認。"""
        from market.etfcom.types import AuthConfig

        auth = AuthConfig(
            api_base_url="https://api-prod.etf.com",
            fund_api_key="key",
            tools_api_key="key",
            oauth_token="token",
            real_time_api_url="https://real-time-prod.etf.com/graphql",
            graphql_api_url="https://data.etf.com",
            fetched_at=datetime.now(tz=timezone.utc),
        )
        repr_str = repr(auth)
        assert "https://api-prod.etf.com" in repr_str


# ---------------------------------------------------------------------------
# Legacy record types removal verification
# ---------------------------------------------------------------------------


class TestLegacyRecordTypesRemoved:
    """Verify that legacy HTML scraping record types have been removed.

    Wave 1 API migration requires removing the following 4 types:
    - FundamentalsRecord
    - FundFlowRecord
    - ETFRecord
    - HistoricalFundFlowRecord
    """

    def test_正常系_FundamentalsRecordが削除済み(self) -> None:
        """FundamentalsRecord が types モジュールから削除されていることを確認。"""
        import market.etfcom.types as types_mod

        assert not hasattr(types_mod, "FundamentalsRecord")

    def test_正常系_FundFlowRecordが削除済み(self) -> None:
        """FundFlowRecord が types モジュールから削除されていることを確認。"""
        import market.etfcom.types as types_mod

        assert not hasattr(types_mod, "FundFlowRecord")

    def test_正常系_ETFRecordが削除済み(self) -> None:
        """ETFRecord が types モジュールから削除されていることを確認。"""
        import market.etfcom.types as types_mod

        assert not hasattr(types_mod, "ETFRecord")

    def test_正常系_HistoricalFundFlowRecordが削除済み(self) -> None:
        """HistoricalFundFlowRecord が types モジュールから削除されていることを確認。"""
        import market.etfcom.types as types_mod

        assert not hasattr(types_mod, "HistoricalFundFlowRecord")


# ---------------------------------------------------------------------------
# __all__ export tests
# ---------------------------------------------------------------------------


class TestModuleExports:
    """Tests for module-level __all__ exports."""

    def test_正常系_allに全クラスが含まれる(self) -> None:
        """__all__ に全4クラスがエクスポートされていることを確認。

        Wave 1 後の期待値:
        - ScrapingConfig (維持)
        - RetryConfig (維持)
        - TickerInfo (維持)
        - AuthConfig (新規)
        """
        from market.etfcom.types import __all__

        expected = {
            "AuthConfig",
            "RetryConfig",
            "ScrapingConfig",
            "TickerInfo",
        }
        assert set(__all__) == expected

    def test_正常系_各クラスがインポート可能(self) -> None:
        """__all__ の各クラスが正常にインポートできることを確認。"""
        from market.etfcom.types import (
            AuthConfig,
            RetryConfig,
            ScrapingConfig,
            TickerInfo,
        )

        assert ScrapingConfig is not None
        assert RetryConfig is not None
        assert TickerInfo is not None
        assert AuthConfig is not None

    def test_正常系_旧レコード型がallに含まれない(self) -> None:
        """旧レコード型が __all__ に含まれないことを確認。"""
        from market.etfcom.types import __all__

        removed_types = {
            "FundamentalsRecord",
            "FundFlowRecord",
            "ETFRecord",
            "HistoricalFundFlowRecord",
        }
        assert removed_types.isdisjoint(set(__all__))
