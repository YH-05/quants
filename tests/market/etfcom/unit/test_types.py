"""Unit tests for market.etfcom.types module."""

from datetime import date

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
# FundamentalsRecord tests
# ---------------------------------------------------------------------------


class TestFundamentalsRecord:
    """Tests for FundamentalsRecord dataclass."""

    def test_正常系_全フィールドで初期化(self) -> None:
        """FundamentalsRecord が全17フィールドで初期化されることを確認。"""
        from market.etfcom.types import FundamentalsRecord

        record = FundamentalsRecord(
            ticker="VOO",
            issuer="Vanguard",
            inception_date="09/07/10",
            expense_ratio="0.03%",
            aum="$751.49B",
            index_tracked="S&P 500",
            segment="MSCI USA Large Cap",
            structure="Open-Ended Fund",
            asset_class="Equity",
            category="Size and Style",
            focus="Large Cap",
            niche="Broad-based",
            region="North America",
            geography="U.S.",
            index_weighting_methodology="Market Cap",
            index_selection_methodology="Committee",
            segment_benchmark="MSCI USA Large Cap",
        )
        assert record.ticker == "VOO"
        assert record.issuer == "Vanguard"
        assert record.inception_date == "09/07/10"
        assert record.expense_ratio == "0.03%"
        assert record.aum == "$751.49B"
        assert record.index_tracked == "S&P 500"
        assert record.segment == "MSCI USA Large Cap"
        assert record.structure == "Open-Ended Fund"
        assert record.asset_class == "Equity"
        assert record.category == "Size and Style"
        assert record.focus == "Large Cap"
        assert record.niche == "Broad-based"
        assert record.region == "North America"
        assert record.geography == "U.S."
        assert record.index_weighting_methodology == "Market Cap"
        assert record.index_selection_methodology == "Committee"
        assert record.segment_benchmark == "MSCI USA Large Cap"

    def test_正常系_frozenであること(self) -> None:
        """FundamentalsRecord が frozen であり属性の変更が禁止されることを確認。"""
        from market.etfcom.types import FundamentalsRecord

        record = FundamentalsRecord(
            ticker="SPY",
            issuer="State Street",
            inception_date="01/22/93",
            expense_ratio="0.09%",
            aum="$500.00B",
            index_tracked="S&P 500",
            segment="MSCI USA Large Cap",
            structure="Unit Investment Trust",
            asset_class="Equity",
            category="Size and Style",
            focus="Large Cap",
            niche="Broad-based",
            region="North America",
            geography="U.S.",
            index_weighting_methodology="Market Cap",
            index_selection_methodology="Committee",
            segment_benchmark="MSCI USA Large Cap",
        )
        with pytest.raises(AttributeError):
            record.ticker = "QQQ"

    def test_正常系_フィールド数が17であること(self) -> None:
        """FundamentalsRecord のフィールド数が17であることを確認。"""
        import dataclasses

        from market.etfcom.types import FundamentalsRecord

        fields = dataclasses.fields(FundamentalsRecord)
        assert len(fields) == 17

    def test_正常系_Noneフィールドで初期化可能(self) -> None:
        """FundamentalsRecord が None フィールドで初期化可能であることを確認。

        ETF.com のデータは '--' プレースホルダーが存在するため、
        Optional フィールドが必要。
        """
        from market.etfcom.types import FundamentalsRecord

        record = FundamentalsRecord(
            ticker="PFFL",
            issuer=None,
            inception_date=None,
            expense_ratio=None,
            aum=None,
            index_tracked=None,
            segment=None,
            structure=None,
            asset_class=None,
            category=None,
            focus=None,
            niche=None,
            region=None,
            geography=None,
            index_weighting_methodology=None,
            index_selection_methodology=None,
            segment_benchmark=None,
        )
        assert record.ticker == "PFFL"
        assert record.issuer is None


# ---------------------------------------------------------------------------
# FundFlowRecord tests
# ---------------------------------------------------------------------------


class TestFundFlowRecord:
    """Tests for FundFlowRecord dataclass."""

    def test_正常系_全フィールドで初期化(self) -> None:
        """FundFlowRecord が全フィールドで初期化されることを確認。"""
        from market.etfcom.types import FundFlowRecord

        record = FundFlowRecord(
            date=date(2025, 9, 10),
            ticker="VOO",
            net_flows=2787.59,
        )
        assert record.date == date(2025, 9, 10)
        assert record.ticker == "VOO"
        assert record.net_flows == 2787.59

    def test_正常系_frozenであること(self) -> None:
        """FundFlowRecord が frozen であり属性の変更が禁止されることを確認。"""
        from market.etfcom.types import FundFlowRecord

        record = FundFlowRecord(
            date=date(2025, 1, 1),
            ticker="SPY",
            net_flows=100.0,
        )
        with pytest.raises(AttributeError):
            record.net_flows = 999.0

    def test_正常系_負のnet_flowsで初期化可能(self) -> None:
        """FundFlowRecord が負の net_flows で初期化可能であることを確認。"""
        from market.etfcom.types import FundFlowRecord

        record = FundFlowRecord(
            date=date(2025, 9, 8),
            ticker="VOO",
            net_flows=-104.61,
        )
        assert record.net_flows == -104.61


# ---------------------------------------------------------------------------
# ETFRecord tests
# ---------------------------------------------------------------------------


class TestETFRecord:
    """Tests for ETFRecord dataclass."""

    def test_正常系_全フィールドで初期化(self) -> None:
        """ETFRecord が全フィールドで初期化されることを確認。"""
        from market.etfcom.types import ETFRecord

        record = ETFRecord(
            ticker="VOO",
            name="Vanguard S&P 500 ETF",
            issuer="Vanguard",
            category="Size and Style",
            expense_ratio=0.03,
            aum=751.49e9,
            inception_date=date(2010, 9, 7),
        )
        assert record.ticker == "VOO"
        assert record.name == "Vanguard S&P 500 ETF"
        assert record.issuer == "Vanguard"
        assert record.category == "Size and Style"
        assert record.expense_ratio == 0.03
        assert record.aum == 751.49e9
        assert record.inception_date == date(2010, 9, 7)

    def test_正常系_Optionalフィールドのデフォルト値(self) -> None:
        """ETFRecord の Optional フィールドがデフォルト None であることを確認。"""
        from market.etfcom.types import ETFRecord

        record = ETFRecord(
            ticker="UNKNOWN",
            name="Unknown ETF",
        )
        assert record.issuer is None
        assert record.category is None
        assert record.expense_ratio is None
        assert record.aum is None
        assert record.inception_date is None

    def test_正常系_frozenでないこと(self) -> None:
        """ETFRecord が frozen でなく属性の変更が可能であることを確認。

        Issue仕様では ETFRecord に frozen=True が指定されていないため、
        mutable であるべき。
        """
        from market.etfcom.types import ETFRecord

        record = ETFRecord(ticker="VOO", name="Vanguard S&P 500 ETF")
        record.name = "Updated Name"
        assert record.name == "Updated Name"


# ---------------------------------------------------------------------------
# HistoricalFundFlowRecord tests
# ---------------------------------------------------------------------------


class TestHistoricalFundFlowRecord:
    """Tests for HistoricalFundFlowRecord dataclass."""

    def test_正常系_全フィールドで初期化(self) -> None:
        """HistoricalFundFlowRecord が全9フィールドで初期化されることを確認。"""
        from market.etfcom.types import HistoricalFundFlowRecord

        record = HistoricalFundFlowRecord(
            ticker="SPY",
            nav_date=date(2025, 9, 10),
            nav=450.25,
            nav_change=2.15,
            nav_change_percent=0.48,
            premium_discount=-0.02,
            fund_flows=2787590000.0,
            shares_outstanding=920000000.0,
            aum=414230000000.0,
        )
        assert record.ticker == "SPY"
        assert record.nav_date == date(2025, 9, 10)
        assert record.nav == 450.25
        assert record.nav_change == 2.15
        assert record.nav_change_percent == 0.48
        assert record.premium_discount == -0.02
        assert record.fund_flows == 2787590000.0
        assert record.shares_outstanding == 920000000.0
        assert record.aum == 414230000000.0

    def test_正常系_frozenであること(self) -> None:
        """HistoricalFundFlowRecord が frozen であり属性の変更が禁止されることを確認。"""
        from market.etfcom.types import HistoricalFundFlowRecord

        record = HistoricalFundFlowRecord(
            ticker="SPY",
            nav_date=date(2025, 9, 10),
            nav=450.25,
            nav_change=2.15,
            nav_change_percent=0.48,
            premium_discount=-0.02,
            fund_flows=2787590000.0,
            shares_outstanding=920000000.0,
            aum=414230000000.0,
        )
        with pytest.raises(AttributeError):
            record.ticker = "VOO"

    def test_正常系_フィールド数が9であること(self) -> None:
        """HistoricalFundFlowRecord のフィールド数が9であることを確認。"""
        import dataclasses

        from market.etfcom.types import HistoricalFundFlowRecord

        fields = dataclasses.fields(HistoricalFundFlowRecord)
        assert len(fields) == 9

    def test_正常系_Noneフィールドで初期化可能(self) -> None:
        """HistoricalFundFlowRecord が None フィールドで初期化可能であることを確認。

        API がデータ欠損時に null を返すため、数値フィールドは None 許容。
        """
        from market.etfcom.types import HistoricalFundFlowRecord

        record = HistoricalFundFlowRecord(
            ticker="UNKNOWN",
            nav_date=date(2025, 1, 1),
            nav=None,
            nav_change=None,
            nav_change_percent=None,
            premium_discount=None,
            fund_flows=None,
            shares_outstanding=None,
            aum=None,
        )
        assert record.ticker == "UNKNOWN"
        assert record.nav is None
        assert record.fund_flows is None

    def test_正常系_負のfund_flowsで初期化可能(self) -> None:
        """HistoricalFundFlowRecord が負の fund_flows で初期化可能であることを確認。"""
        from market.etfcom.types import HistoricalFundFlowRecord

        record = HistoricalFundFlowRecord(
            ticker="SPY",
            nav_date=date(2025, 9, 8),
            nav=448.10,
            nav_change=-2.15,
            nav_change_percent=-0.48,
            premium_discount=0.01,
            fund_flows=-1500000000.0,
            shares_outstanding=920000000.0,
            aum=412000000000.0,
        )
        assert record.fund_flows == -1500000000.0
        assert record.nav_change == -2.15


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
# __all__ export tests
# ---------------------------------------------------------------------------


class TestModuleExports:
    """Tests for module-level __all__ exports."""

    def test_正常系_allに全クラスが含まれる(self) -> None:
        """__all__ に全7クラスがエクスポートされていることを確認。"""
        from market.etfcom.types import __all__

        expected = {
            "ScrapingConfig",
            "RetryConfig",
            "FundamentalsRecord",
            "FundFlowRecord",
            "ETFRecord",
            "HistoricalFundFlowRecord",
            "TickerInfo",
        }
        assert set(__all__) == expected

    def test_正常系_各クラスがインポート可能(self) -> None:
        """__all__ の各クラスが正常にインポートできることを確認。"""
        from market.etfcom.types import (
            ETFRecord,
            FundamentalsRecord,
            FundFlowRecord,
            HistoricalFundFlowRecord,
            RetryConfig,
            ScrapingConfig,
            TickerInfo,
        )

        assert ScrapingConfig is not None
        assert RetryConfig is not None
        assert FundamentalsRecord is not None
        assert FundFlowRecord is not None
        assert ETFRecord is not None
        assert HistoricalFundFlowRecord is not None
        assert TickerInfo is not None
