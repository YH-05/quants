"""Tests for market.bse.types module.

Tests verify all type definitions for the BSE data retrieval module,
including Enum groups (BhavcopyType, ScripGroup, IndexName),
frozen dataclasses (BseConfig, RetryConfig, ScripQuote, FinancialResult,
Announcement, CorporateAction), and module exports.

Test TODO List:
- [x] Module exports: __all__ completeness and importability
- [x] BhavcopyType Enum: values, str inheritance, member count
- [x] ScripGroup Enum: values, str inheritance, member count
- [x] IndexName Enum: values, str inheritance, member count
- [x] BseConfig: frozen, defaults from constants, field types
- [x] BseConfig: timeout/polite_delay/delay_jitter range validation
- [x] RetryConfig: frozen, defaults, field types
- [x] RetryConfig: max_attempts range validation
- [x] ScripQuote: frozen, all fields, field types
- [x] FinancialResult: frozen, all fields, field types
- [x] Announcement: frozen, all fields, field types
- [x] CorporateAction: frozen, all fields, field types
"""

from dataclasses import FrozenInstanceError
from enum import Enum

import pytest

from market.bse.constants import (
    DEFAULT_DELAY_JITTER,
    DEFAULT_POLITE_DELAY,
    DEFAULT_TIMEOUT,
)
from market.bse.types import (
    Announcement,
    BhavcopyType,
    BseConfig,
    CorporateAction,
    FinancialResult,
    IndexName,
    RetryConfig,
    ScripGroup,
    ScripQuote,
    __all__,
)

# =============================================================================
# Module exports
# =============================================================================


class TestModuleExports:
    """Test module __all__ exports and structure."""

    def test_正常系_モジュールがインポートできる(self) -> None:
        """types モジュールが正常にインポートできること。"""
        from market.bse import types

        assert types is not None

    def test_正常系_allが定義されている(self) -> None:
        """__all__ がリストとして定義されていること。"""
        assert isinstance(__all__, list)
        assert len(__all__) > 0

    def test_正常系_allの全項目がモジュールに存在する(self) -> None:
        """__all__ の全項目がモジュールの属性として存在すること。"""
        from market.bse import types

        for name in __all__:
            assert hasattr(types, name), f"{name} is not defined in types module"

    def test_正常系_allが9項目を含む(self) -> None:
        """__all__ が全9型定義をエクスポートしていること。"""
        expected = {
            "Announcement",
            "BhavcopyType",
            "BseConfig",
            "CorporateAction",
            "FinancialResult",
            "IndexName",
            "RetryConfig",
            "ScripGroup",
            "ScripQuote",
        }
        assert set(__all__) == expected

    def test_正常系_モジュールDocstringが存在する(self) -> None:
        """モジュールの docstring が存在すること。"""
        from market.bse import types

        assert types.__doc__ is not None
        assert len(types.__doc__) > 0


# =============================================================================
# BhavcopyType Enum
# =============================================================================


class TestBhavcopyTypeEnum:
    """Test BhavcopyType Enum definition."""

    def test_正常系_strを継承している(self) -> None:
        """BhavcopyType が str と Enum を継承していること。"""
        assert issubclass(BhavcopyType, str)
        assert issubclass(BhavcopyType, Enum)

    def test_正常系_3つのメンバーを持つ(self) -> None:
        """BhavcopyType が EQUITY, DERIVATIVES, DEBT の3メンバーを持つこと。"""
        assert len(BhavcopyType) == 3

    def test_正常系_全メンバーの値が正しい(self) -> None:
        """BhavcopyType の全メンバーの値が設計通りであること。"""
        assert BhavcopyType.EQUITY.value == "equity"
        assert BhavcopyType.DERIVATIVES.value == "derivatives"
        assert BhavcopyType.DEBT.value == "debt"

    def test_正常系_文字列として使用できる(self) -> None:
        """BhavcopyType メンバーを文字列として直接使用できること。"""
        value: str = BhavcopyType.EQUITY
        assert isinstance(value, str)


# =============================================================================
# ScripGroup Enum
# =============================================================================


class TestScripGroupEnum:
    """Test ScripGroup Enum definition."""

    def test_正常系_strを継承している(self) -> None:
        """ScripGroup が str と Enum を継承していること。"""
        assert issubclass(ScripGroup, str)
        assert issubclass(ScripGroup, Enum)

    def test_正常系_5つのメンバーを持つ(self) -> None:
        """ScripGroup が A, B, T, Z, X の5メンバーを持つこと。"""
        assert len(ScripGroup) == 5

    def test_正常系_全メンバーの値が正しい(self) -> None:
        """ScripGroup の全メンバーの値が設計通りであること。"""
        assert ScripGroup.A.value == "A"
        assert ScripGroup.B.value == "B"
        assert ScripGroup.T.value == "T"
        assert ScripGroup.Z.value == "Z"
        assert ScripGroup.X.value == "X"

    def test_正常系_文字列として使用できる(self) -> None:
        """ScripGroup メンバーを文字列として直接使用できること。"""
        value: str = ScripGroup.A
        assert isinstance(value, str)


# =============================================================================
# IndexName Enum
# =============================================================================


class TestIndexNameEnum:
    """Test IndexName Enum definition."""

    def test_正常系_strを継承している(self) -> None:
        """IndexName が str と Enum を継承していること。"""
        assert issubclass(IndexName, str)
        assert issubclass(IndexName, Enum)

    def test_正常系_12個のメンバーを持つ(self) -> None:
        """IndexName が12メンバーを持つこと。"""
        assert len(IndexName) == 12

    def test_正常系_SENSEXの値が正しい(self) -> None:
        """IndexName.SENSEX の値が 'SENSEX' であること。"""
        assert IndexName.SENSEX.value == "SENSEX"

    def test_正常系_BANKEXの値が正しい(self) -> None:
        """IndexName.BANKEX の値が 'BANKEX' であること。"""
        assert IndexName.BANKEX.value == "BANKEX"

    def test_正常系_主要インデックスが含まれている(self) -> None:
        """IndexName に主要インデックスが含まれていること。"""
        expected = {
            "SENSEX",
            "SENSEX 50",
            "BSE 100",
            "BSE 200",
            "BSE 500",
            "BSE MIDCAP",
            "BSE SMALLCAP",
            "BSE LARGECAP",
            "BANKEX",
            "BSE IT",
            "BSE HEALTHCARE",
            "BSE AUTO",
        }
        actual = {member.value for member in IndexName}
        assert actual == expected

    def test_正常系_文字列として使用できる(self) -> None:
        """IndexName メンバーを文字列として直接使用できること。"""
        value: str = IndexName.SENSEX
        assert isinstance(value, str)


# =============================================================================
# BseConfig dataclass
# =============================================================================


class TestBseConfig:
    """Test BseConfig frozen dataclass."""

    def test_正常系_frozenである(self) -> None:
        """BseConfig がフィールド変更不可であること。"""
        config = BseConfig()
        with pytest.raises(FrozenInstanceError):
            config.polite_delay = 5.0  # type: ignore[misc]

    def test_正常系_デフォルト値がconstantsと一致(self) -> None:
        """BseConfig のデフォルト値が constants の値と一致すること。"""
        config = BseConfig()
        assert config.polite_delay == DEFAULT_POLITE_DELAY
        assert config.delay_jitter == DEFAULT_DELAY_JITTER
        assert config.timeout == DEFAULT_TIMEOUT

    def test_正常系_user_agentsのデフォルトがタプル(self) -> None:
        """BseConfig の user_agents のデフォルトが空タプルであること。"""
        config = BseConfig()
        assert isinstance(config.user_agents, tuple)
        assert config.user_agents == ()

    def test_正常系_カスタム値で生成できる(self) -> None:
        """BseConfig をカスタム値で生成できること。"""
        config = BseConfig(
            polite_delay=0.5,
            delay_jitter=0.1,
            user_agents=("UA1", "UA2"),
            timeout=60.0,
        )
        assert config.polite_delay == 0.5
        assert config.delay_jitter == 0.1
        assert config.user_agents == ("UA1", "UA2")
        assert config.timeout == 60.0

    def test_正常系_全フィールドが存在する(self) -> None:
        """BseConfig が設計通りの4フィールドを持つこと。"""
        config = BseConfig()
        assert hasattr(config, "polite_delay")
        assert hasattr(config, "delay_jitter")
        assert hasattr(config, "user_agents")
        assert hasattr(config, "timeout")

    def test_正常系_境界値でtimeoutが受け入れられる(self) -> None:
        """timeout の境界値（1.0, 300.0）が受け入れられること。"""
        config_min = BseConfig(timeout=1.0)
        assert config_min.timeout == 1.0
        config_max = BseConfig(timeout=300.0)
        assert config_max.timeout == 300.0

    def test_異常系_timeoutが範囲外でValueError(self) -> None:
        """timeout が範囲外の場合 ValueError が発生すること。"""
        with pytest.raises(
            ValueError, match=r"timeout must be between 1\.0 and 300\.0"
        ):
            BseConfig(timeout=0.5)
        with pytest.raises(
            ValueError, match=r"timeout must be between 1\.0 and 300\.0"
        ):
            BseConfig(timeout=301.0)

    def test_正常系_境界値でpolite_delayが受け入れられる(self) -> None:
        """polite_delay の境界値（0.0, 60.0）が受け入れられること。"""
        config_min = BseConfig(polite_delay=0.0)
        assert config_min.polite_delay == 0.0
        config_max = BseConfig(polite_delay=60.0)
        assert config_max.polite_delay == 60.0

    def test_異常系_polite_delayが範囲外でValueError(self) -> None:
        """polite_delay が範囲外の場合 ValueError が発生すること。"""
        with pytest.raises(
            ValueError, match=r"polite_delay must be between 0\.0 and 60\.0"
        ):
            BseConfig(polite_delay=-0.1)
        with pytest.raises(
            ValueError, match=r"polite_delay must be between 0\.0 and 60\.0"
        ):
            BseConfig(polite_delay=61.0)

    def test_正常系_境界値でdelay_jitterが受け入れられる(self) -> None:
        """delay_jitter の境界値（0.0, 30.0）が受け入れられること。"""
        config_min = BseConfig(delay_jitter=0.0)
        assert config_min.delay_jitter == 0.0
        config_max = BseConfig(delay_jitter=30.0)
        assert config_max.delay_jitter == 30.0

    def test_異常系_delay_jitterが範囲外でValueError(self) -> None:
        """delay_jitter が範囲外の場合 ValueError が発生すること。"""
        with pytest.raises(
            ValueError, match=r"delay_jitter must be between 0\.0 and 30\.0"
        ):
            BseConfig(delay_jitter=-0.1)
        with pytest.raises(
            ValueError, match=r"delay_jitter must be between 0\.0 and 30\.0"
        ):
            BseConfig(delay_jitter=31.0)


# =============================================================================
# RetryConfig dataclass
# =============================================================================


class TestRetryConfig:
    """Test RetryConfig frozen dataclass."""

    def test_正常系_frozenである(self) -> None:
        """RetryConfig がフィールド変更不可であること。"""
        config = RetryConfig()
        with pytest.raises(FrozenInstanceError):
            config.max_attempts = 10  # type: ignore[misc]

    def test_正常系_デフォルト値が正しい(self) -> None:
        """RetryConfig のデフォルト値が設計通りであること。"""
        config = RetryConfig()
        assert config.max_attempts == 3
        assert config.initial_delay == 1.0
        assert config.max_delay == 30.0
        assert config.exponential_base == 2.0
        assert config.jitter is True

    def test_正常系_カスタム値で生成できる(self) -> None:
        """RetryConfig をカスタム値で生成できること。"""
        config = RetryConfig(
            max_attempts=5,
            initial_delay=0.5,
            max_delay=60.0,
            exponential_base=3.0,
            jitter=False,
        )
        assert config.max_attempts == 5
        assert config.initial_delay == 0.5
        assert config.max_delay == 60.0
        assert config.exponential_base == 3.0
        assert config.jitter is False

    def test_正常系_全フィールドが存在する(self) -> None:
        """RetryConfig が設計通りの5フィールドを持つこと。"""
        config = RetryConfig()
        assert hasattr(config, "max_attempts")
        assert hasattr(config, "initial_delay")
        assert hasattr(config, "max_delay")
        assert hasattr(config, "exponential_base")
        assert hasattr(config, "jitter")

    def test_正常系_境界値でmax_attemptsが受け入れられる(self) -> None:
        """max_attempts の境界値（1, 10）が受け入れられること。"""
        config_min = RetryConfig(max_attempts=1)
        assert config_min.max_attempts == 1
        config_max = RetryConfig(max_attempts=10)
        assert config_max.max_attempts == 10

    def test_異常系_max_attemptsが範囲外でValueError(self) -> None:
        """max_attempts が範囲外の場合 ValueError が発生すること。"""
        with pytest.raises(ValueError, match="max_attempts must be between 1 and 10"):
            RetryConfig(max_attempts=0)
        with pytest.raises(ValueError, match="max_attempts must be between 1 and 10"):
            RetryConfig(max_attempts=11)


# =============================================================================
# ScripQuote dataclass
# =============================================================================


class TestScripQuote:
    """Test ScripQuote frozen dataclass."""

    def _make_quote(self, **overrides: str) -> ScripQuote:
        """Create a ScripQuote with default values."""
        defaults = {
            "scrip_code": "500325",
            "scrip_name": "RELIANCE INDUSTRIES LTD",
            "scrip_group": "A",
            "open": "2450.00",
            "high": "2480.50",
            "low": "2440.00",
            "close": "2470.25",
            "last": "2469.90",
            "prev_close": "2445.00",
            "num_trades": "125000",
            "num_shares": "5000000",
            "net_turnover": "12345678900",
        }
        defaults.update(overrides)
        return ScripQuote(**defaults)  # type: ignore[arg-type]

    def test_正常系_frozenである(self) -> None:
        """ScripQuote がフィールド変更不可であること。"""
        quote = self._make_quote()
        with pytest.raises(FrozenInstanceError):
            quote.scrip_code = "500180"  # type: ignore[misc]

    def test_正常系_全フィールドが正しく設定される(self) -> None:
        """ScripQuote の全12フィールドが正しく設定されること。"""
        quote = self._make_quote()
        assert quote.scrip_code == "500325"
        assert quote.scrip_name == "RELIANCE INDUSTRIES LTD"
        assert quote.scrip_group == "A"
        assert quote.open == "2450.00"
        assert quote.high == "2480.50"
        assert quote.low == "2440.00"
        assert quote.close == "2470.25"
        assert quote.last == "2469.90"
        assert quote.prev_close == "2445.00"
        assert quote.num_trades == "125000"
        assert quote.num_shares == "5000000"
        assert quote.net_turnover == "12345678900"

    def test_正常系_全フィールドがstr型(self) -> None:
        """ScripQuote の全フィールドが str であること。"""
        quote = self._make_quote()
        for field_name in [
            "scrip_code",
            "scrip_name",
            "scrip_group",
            "open",
            "high",
            "low",
            "close",
            "last",
            "prev_close",
            "num_trades",
            "num_shares",
            "net_turnover",
        ]:
            assert isinstance(getattr(quote, field_name), str), (
                f"Field {field_name} is not str"
            )


# =============================================================================
# FinancialResult dataclass
# =============================================================================


class TestFinancialResult:
    """Test FinancialResult frozen dataclass."""

    def _make_result(self, **overrides: str) -> FinancialResult:
        """Create a FinancialResult with default values."""
        defaults = {
            "scrip_code": "500325",
            "scrip_name": "RELIANCE INDUSTRIES LTD",
            "period_ended": "31-Mar-2025",
            "revenue": "250000",
            "net_profit": "18500",
            "eps": "27.35",
        }
        defaults.update(overrides)
        return FinancialResult(**defaults)  # type: ignore[arg-type]

    def test_正常系_frozenである(self) -> None:
        """FinancialResult がフィールド変更不可であること。"""
        result = self._make_result()
        with pytest.raises(FrozenInstanceError):
            result.scrip_code = "500180"  # type: ignore[misc]

    def test_正常系_全フィールドが正しく設定される(self) -> None:
        """FinancialResult の全6フィールドが正しく設定されること。"""
        result = self._make_result()
        assert result.scrip_code == "500325"
        assert result.scrip_name == "RELIANCE INDUSTRIES LTD"
        assert result.period_ended == "31-Mar-2025"
        assert result.revenue == "250000"
        assert result.net_profit == "18500"
        assert result.eps == "27.35"

    def test_正常系_全フィールドがstr型(self) -> None:
        """FinancialResult の全フィールドが str であること。"""
        result = self._make_result()
        for field_name in [
            "scrip_code",
            "scrip_name",
            "period_ended",
            "revenue",
            "net_profit",
            "eps",
        ]:
            assert isinstance(getattr(result, field_name), str), (
                f"Field {field_name} is not str"
            )


# =============================================================================
# Announcement dataclass
# =============================================================================


class TestAnnouncement:
    """Test Announcement frozen dataclass."""

    def _make_announcement(self, **overrides: str) -> Announcement:
        """Create an Announcement with default values."""
        defaults = {
            "scrip_code": "500325",
            "scrip_name": "RELIANCE INDUSTRIES LTD",
            "subject": "Board Meeting Outcome",
            "announcement_date": "15-Jan-2025",
            "category": "Board Meeting",
        }
        defaults.update(overrides)
        return Announcement(**defaults)  # type: ignore[arg-type]

    def test_正常系_frozenである(self) -> None:
        """Announcement がフィールド変更不可であること。"""
        ann = self._make_announcement()
        with pytest.raises(FrozenInstanceError):
            ann.subject = "New subject"  # type: ignore[misc]

    def test_正常系_全フィールドが正しく設定される(self) -> None:
        """Announcement の全5フィールドが正しく設定されること。"""
        ann = self._make_announcement()
        assert ann.scrip_code == "500325"
        assert ann.scrip_name == "RELIANCE INDUSTRIES LTD"
        assert ann.subject == "Board Meeting Outcome"
        assert ann.announcement_date == "15-Jan-2025"
        assert ann.category == "Board Meeting"

    def test_正常系_全フィールドがstr型(self) -> None:
        """Announcement の全フィールドが str であること。"""
        ann = self._make_announcement()
        for field_name in [
            "scrip_code",
            "scrip_name",
            "subject",
            "announcement_date",
            "category",
        ]:
            assert isinstance(getattr(ann, field_name), str), (
                f"Field {field_name} is not str"
            )


# =============================================================================
# CorporateAction dataclass
# =============================================================================


class TestCorporateAction:
    """Test CorporateAction frozen dataclass."""

    def _make_action(self, **overrides: str) -> CorporateAction:
        """Create a CorporateAction with default values."""
        defaults = {
            "scrip_code": "500325",
            "scrip_name": "RELIANCE INDUSTRIES LTD",
            "ex_date": "01-Feb-2025",
            "purpose": "Dividend - Rs 8 Per Share",
            "record_date": "03-Feb-2025",
        }
        defaults.update(overrides)
        return CorporateAction(**defaults)  # type: ignore[arg-type]

    def test_正常系_frozenである(self) -> None:
        """CorporateAction がフィールド変更不可であること。"""
        action = self._make_action()
        with pytest.raises(FrozenInstanceError):
            action.purpose = "New purpose"  # type: ignore[misc]

    def test_正常系_全フィールドが正しく設定される(self) -> None:
        """CorporateAction の全5フィールドが正しく設定されること。"""
        action = self._make_action()
        assert action.scrip_code == "500325"
        assert action.scrip_name == "RELIANCE INDUSTRIES LTD"
        assert action.ex_date == "01-Feb-2025"
        assert action.purpose == "Dividend - Rs 8 Per Share"
        assert action.record_date == "03-Feb-2025"

    def test_正常系_全フィールドがstr型(self) -> None:
        """CorporateAction の全フィールドが str であること。"""
        action = self._make_action()
        for field_name in [
            "scrip_code",
            "scrip_name",
            "ex_date",
            "purpose",
            "record_date",
        ]:
            assert isinstance(getattr(action, field_name), str), (
                f"Field {field_name} is not str"
            )
