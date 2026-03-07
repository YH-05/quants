"""Tests for market.edinet.types module.

Tests verify all type definitions for the EDINET DB API module,
including configuration dataclasses (EdinetConfig, RetryConfig),
data record dataclasses (Company, FinancialRecord, RatioRecord,
AnalysisResult, TextBlock, RankingEntry, Industry, SyncProgress),
and the module exports.

Test TODO List:
- [x] Module exports: __all__ completeness and importability
- [x] EdinetConfig: frozen, defaults, db_path resolution (db_path > env > get_db_path)
- [x] EdinetConfig: sync_state_path derived from resolved_db_path
- [x] EdinetConfig: __post_init__ validation (timeout, polite_delay)
- [x] RetryConfig: frozen, defaults, __post_init__ validation
- [x] Company: frozen, all 6 fields
- [x] FinancialRecord: frozen, fiscal_year=int, all Optional fields, no period_type
- [x] RatioRecord: frozen, fiscal_year=int, all Optional fields, no period_type
- [x] AnalysisResult: frozen, all fields
- [x] TextBlock: frozen, all fields
- [x] RankingEntry: frozen, all fields
- [x] Industry: frozen, all fields
- [x] SyncProgress: frozen, all fields, defaults
"""

from dataclasses import FrozenInstanceError, fields
from pathlib import Path
from unittest.mock import patch

import pytest

from market.edinet.constants import (
    DEFAULT_BASE_URL,
    DEFAULT_DB_NAME,
    DEFAULT_POLITE_DELAY,
    DEFAULT_TIMEOUT,
    SYNC_STATE_FILENAME,
)
from market.edinet.types import (
    AnalysisResult,
    Company,
    EdinetConfig,
    FinancialRecord,
    Industry,
    RankingEntry,
    RatioRecord,
    RetryConfig,
    SyncProgress,
    TextBlock,
    __all__,
)

# =============================================================================
# Module exports
# =============================================================================


class TestModuleExports:
    """Test module __all__ exports and structure."""

    def test_正常系_モジュールがインポートできる(self) -> None:
        """types モジュールが正常にインポートできること。"""
        from market.edinet import types

        assert types is not None

    def test_正常系_allが定義されている(self) -> None:
        """__all__ がリストとして定義されていること。"""
        assert isinstance(__all__, list)
        assert len(__all__) > 0

    def test_正常系_allの全項目がモジュールに存在する(self) -> None:
        """__all__ の全項目がモジュールの属性として存在すること。"""
        from market.edinet import types

        for name in __all__:
            assert hasattr(types, name), f"{name} is not defined in types module"

    def test_正常系_allが10型定義を含む(self) -> None:
        """__all__ が全10型定義をエクスポートしていること。"""
        expected = {
            "AnalysisResult",
            "Company",
            "EdinetConfig",
            "FinancialRecord",
            "Industry",
            "RankingEntry",
            "RatioRecord",
            "RetryConfig",
            "SyncProgress",
            "TextBlock",
        }
        assert set(__all__) >= expected

    def test_正常系_モジュールDocstringが存在する(self) -> None:
        """モジュールの docstring が存在すること。"""
        from market.edinet import types

        assert types.__doc__ is not None
        assert len(types.__doc__) > 0


# =============================================================================
# EdinetConfig dataclass
# =============================================================================


class TestEdinetConfig:
    """Test EdinetConfig frozen dataclass."""

    def test_正常系_frozenである(self) -> None:
        """EdinetConfig がフィールド変更不可であること。"""
        config = EdinetConfig(api_key="test_key")
        with pytest.raises(FrozenInstanceError):
            config.api_key = "new_key"

    def test_正常系_デフォルト値が正しい(self) -> None:
        """EdinetConfig のデフォルト値が設計通りであること。"""
        config = EdinetConfig(api_key="test_key")
        assert config.api_key == "test_key"
        assert config.base_url == DEFAULT_BASE_URL
        assert config.timeout == DEFAULT_TIMEOUT
        assert config.polite_delay == DEFAULT_POLITE_DELAY
        assert config.db_path is None

    def test_正常系_カスタム値で生成できる(self) -> None:
        """EdinetConfig をカスタム値で生成できること。"""
        custom_path = Path("/custom/edinet.duckdb")
        config = EdinetConfig(
            api_key="custom_key",
            base_url="https://custom.api.example.com",
            timeout=60.0,
            polite_delay=0.5,
            db_path=custom_path,
        )
        assert config.api_key == "custom_key"
        assert config.base_url == "https://custom.api.example.com"
        assert config.timeout == 60.0
        assert config.polite_delay == 0.5
        assert config.db_path == custom_path

    def test_正常系_resolved_db_pathがdb_pathを最優先する(self) -> None:
        """resolved_db_path が db_path > env > get_db_path の優先順位で解決すること。"""
        custom_path = Path("/custom/edinet.duckdb")
        config = EdinetConfig(api_key="test_key", db_path=custom_path)
        assert config.resolved_db_path == custom_path

    def test_正常系_resolved_db_pathが環境変数を参照する(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """db_path が None の場合、環境変数 EDINET_DB_PATH を参照すること。"""
        env_path = "/env/edinet.duckdb"
        monkeypatch.setenv("EDINET_DB_PATH", env_path)
        config = EdinetConfig(api_key="test_key")
        assert config.resolved_db_path == Path(env_path)

    def test_正常系_resolved_db_pathがget_db_pathにフォールバックする(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """db_path も環境変数もない場合、get_db_path() にフォールバックすること。"""
        monkeypatch.delenv("EDINET_DB_PATH", raising=False)
        fallback_path = Path("/fallback/duckdb/edinet.duckdb")
        with patch(
            "market.edinet.types.get_db_path", return_value=fallback_path
        ) as mock_get:
            config = EdinetConfig(api_key="test_key")
            result = config.resolved_db_path
            assert result == fallback_path
            mock_get.assert_called_once_with("duckdb", DEFAULT_DB_NAME)

    def test_正常系_sync_state_pathがresolved_db_pathの隣に生成される(self) -> None:
        """sync_state_path が resolved_db_path と同じディレクトリに生成されること。"""
        custom_path = Path("/data/duckdb/edinet.duckdb")
        config = EdinetConfig(api_key="test_key", db_path=custom_path)
        expected = Path("/data/duckdb") / SYNC_STATE_FILENAME
        assert config.sync_state_path == expected

    def test_正常系_境界値でtimeoutが受け入れられる(self) -> None:
        """timeout の境界値（1.0, 300.0）が受け入れられること。"""
        config_min = EdinetConfig(api_key="k", timeout=1.0)
        assert config_min.timeout == 1.0
        config_max = EdinetConfig(api_key="k", timeout=300.0)
        assert config_max.timeout == 300.0

    def test_異常系_timeoutが範囲外でValueError(self) -> None:
        """timeout が範囲外の場合 ValueError が発生すること。"""
        with pytest.raises(
            ValueError, match=r"timeout must be between 1\.0 and 300\.0"
        ):
            EdinetConfig(api_key="k", timeout=0.5)
        with pytest.raises(
            ValueError, match=r"timeout must be between 1\.0 and 300\.0"
        ):
            EdinetConfig(api_key="k", timeout=301.0)

    def test_正常系_境界値でpolite_delayが受け入れられる(self) -> None:
        """polite_delay の境界値（0.0, 60.0）が受け入れられること。"""
        config_min = EdinetConfig(api_key="k", polite_delay=0.0)
        assert config_min.polite_delay == 0.0
        config_max = EdinetConfig(api_key="k", polite_delay=60.0)
        assert config_max.polite_delay == 60.0

    def test_異常系_polite_delayが範囲外でValueError(self) -> None:
        """polite_delay が範囲外の場合 ValueError が発生すること。"""
        with pytest.raises(
            ValueError, match=r"polite_delay must be between 0\.0 and 60\.0"
        ):
            EdinetConfig(api_key="k", polite_delay=-0.1)
        with pytest.raises(
            ValueError, match=r"polite_delay must be between 0\.0 and 60\.0"
        ):
            EdinetConfig(api_key="k", polite_delay=61.0)

    def test_正常系_全フィールドが存在する(self) -> None:
        """EdinetConfig が設計通りのフィールドを持つこと。"""
        config = EdinetConfig(api_key="test_key")
        assert hasattr(config, "api_key")
        assert hasattr(config, "base_url")
        assert hasattr(config, "timeout")
        assert hasattr(config, "polite_delay")
        assert hasattr(config, "db_path")


# =============================================================================
# RetryConfig dataclass
# =============================================================================


class TestRetryConfig:
    """Test RetryConfig frozen dataclass."""

    def test_正常系_frozenである(self) -> None:
        """RetryConfig がフィールド変更不可であること。"""
        config = RetryConfig()
        with pytest.raises(FrozenInstanceError):
            config.max_attempts = 10

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

    def test_異常系_initial_delayが負でValueError(self) -> None:
        """initial_delay が負の場合 ValueError が発生すること。"""
        with pytest.raises(ValueError, match="initial_delay must be positive"):
            RetryConfig(initial_delay=-0.1)

    def test_異常系_max_delayがinitial_delay未満でValueError(self) -> None:
        """max_delay が initial_delay 未満の場合 ValueError が発生すること。"""
        with pytest.raises(ValueError, match="max_delay must be >= initial_delay"):
            RetryConfig(initial_delay=10.0, max_delay=5.0)

    def test_正常系_全フィールドが存在する(self) -> None:
        """RetryConfig が設計通りの5フィールドを持つこと。"""
        config = RetryConfig()
        assert hasattr(config, "max_attempts")
        assert hasattr(config, "initial_delay")
        assert hasattr(config, "max_delay")
        assert hasattr(config, "exponential_base")
        assert hasattr(config, "jitter")


# =============================================================================
# Company dataclass
# =============================================================================


class TestCompany:
    """Test Company frozen dataclass."""

    def test_正常系_frozenである(self) -> None:
        """Company がフィールド変更不可であること。"""
        company = Company(
            edinet_code="E00001",
            sec_code="10000",
            corp_name="テスト株式会社",
            industry_code="3050",
            industry_name="情報・通信業",
            listing_status="上場",
        )
        with pytest.raises(FrozenInstanceError):
            company.corp_name = "変更"

    def test_正常系_全フィールドが正しく設定される(self) -> None:
        """Company の全6フィールドが正しく設定されること。"""
        company = Company(
            edinet_code="E00001",
            sec_code="10000",
            corp_name="テスト株式会社",
            industry_code="3050",
            industry_name="情報・通信業",
            listing_status="上場",
        )
        assert company.edinet_code == "E00001"
        assert company.sec_code == "10000"
        assert company.corp_name == "テスト株式会社"
        assert company.industry_code == "3050"
        assert company.industry_name == "情報・通信業"
        assert company.listing_status == "上場"

    def test_正常系_全フィールドがstr型(self) -> None:
        """Company の全フィールドが str であること。"""
        company = Company(
            edinet_code="E00001",
            sec_code="10000",
            corp_name="テスト",
            industry_code="3050",
            industry_name="情報・通信業",
            listing_status="上場",
        )
        for field_name in [
            "edinet_code",
            "sec_code",
            "corp_name",
            "industry_code",
            "industry_name",
            "listing_status",
        ]:
            assert isinstance(getattr(company, field_name), str), (
                f"Field {field_name} is not str"
            )


# =============================================================================
# FinancialRecord dataclass
# =============================================================================


class TestFinancialRecord:
    """Test FinancialRecord frozen dataclass (API-verified fields)."""

    def test_正常系_frozenである(self) -> None:
        """FinancialRecord がフィールド変更不可であること。"""
        record = FinancialRecord(
            edinet_code="E00001",
            fiscal_year=2025,
            revenue=1_000_000_000.0,
        )
        with pytest.raises(FrozenInstanceError):
            record.revenue = 0.0

    def test_正常系_fiscal_yearがint型である(self) -> None:
        """fiscal_year が int 型であること（API検証結果に基づく）。"""
        record = FinancialRecord(edinet_code="E00001", fiscal_year=2025)
        assert isinstance(record.fiscal_year, int)
        assert record.fiscal_year == 2025

    def test_正常系_period_typeフィールドが存在しない(self) -> None:
        """period_type フィールドが削除されていること。"""
        assert not hasattr(
            FinancialRecord(edinet_code="E00001", fiscal_year=2025),
            "period_type",
        )
        field_names = {f.name for f in fields(FinancialRecord)}
        assert "period_type" not in field_names

    def test_正常系_全Optionalフィールドのデフォルトがnone(self) -> None:
        """全財務フィールドが default=None であること。"""
        record = FinancialRecord(edinet_code="E00001", fiscal_year=2025)
        # API検証で確認された24フィールド（edinet_code, fiscal_year 除く）
        optional_fields = [
            "accounting_standard",
            "bps",
            "cash",
            "cf_financing",
            "cf_investing",
            "cf_operating",
            "comprehensive_income",
            "diluted_eps",
            "dividend_per_share",
            "eps",
            "equity_ratio_official",
            "net_assets",
            "net_income",
            "num_employees",
            "ordinary_income",
            "payout_ratio",
            "per",
            "profit_before_tax",
            "revenue",
            "roe_official",
            "shareholders_equity",
            "submit_date",
            "total_assets",
            # JP GAAP追加フィールド
            "operating_income",
            "capex",
            "depreciation",
            "rnd_expenses",
            "goodwill",
        ]
        for field_name in optional_fields:
            value = getattr(record, field_name)
            assert value is None, (
                f"Field {field_name} default should be None, got {value}"
            )

    def test_正常系_新フィールド名が存在する(self) -> None:
        """API検証で確認された新フィールド名が存在すること。"""
        field_names = {f.name for f in fields(FinancialRecord)}
        # APIレスポンスで確認されたフィールド
        expected_new_fields = {
            "cf_operating",
            "cf_investing",
            "cf_financing",
            "num_employees",
            "rnd_expenses",
            "shareholders_equity",
            "cash",
            "comprehensive_income",
            "diluted_eps",
            "equity_ratio_official",
            "payout_ratio",
            "per",
            "profit_before_tax",
            "roe_official",
            "accounting_standard",
            "submit_date",
        }
        for field_name in expected_new_fields:
            assert field_name in field_names, (
                f"New field {field_name} is missing from FinancialRecord"
            )

    def test_正常系_削除済みフィールドが存在しない(self) -> None:
        """旧フィールドが削除されていること。"""
        field_names = {f.name for f in fields(FinancialRecord)}
        deleted_fields = {
            "equity",
            "interest_bearing_debt",
            "operating_cf",
            "investing_cf",
            "financing_cf",
            "free_cf",
            "shares_outstanding",
            "employees",
            "rnd_expense",
            "period_type",
        }
        for field_name in deleted_fields:
            assert field_name not in field_names, (
                f"Deleted field {field_name} still exists in FinancialRecord"
            )

    def test_正常系_全フィールドが正しく設定される(
        self, sample_financial_record: FinancialRecord
    ) -> None:
        """FinancialRecord の全フィールドが正しく設定されること。"""
        record = sample_financial_record
        assert record.edinet_code == "E00001"
        assert record.fiscal_year == 2025
        assert record.revenue == pytest.approx(1_000_000_000.0)
        assert record.operating_income == pytest.approx(100_000_000.0)
        assert record.ordinary_income == pytest.approx(110_000_000.0)
        assert record.net_income == pytest.approx(70_000_000.0)
        assert record.total_assets == pytest.approx(5_000_000_000.0)
        assert record.net_assets == pytest.approx(2_000_000_000.0)
        assert record.shareholders_equity == pytest.approx(1_800_000_000.0)
        assert record.cf_operating == pytest.approx(150_000_000.0)
        assert record.cf_investing == pytest.approx(-80_000_000.0)
        assert record.cf_financing == pytest.approx(-50_000_000.0)
        assert record.eps == pytest.approx(350.0)
        assert record.bps == pytest.approx(9_000.0)
        assert record.diluted_eps == pytest.approx(345.0)
        assert record.dividend_per_share == pytest.approx(100.0)
        assert record.num_employees == 5_000
        assert record.capex == pytest.approx(80_000_000.0)
        assert record.depreciation == pytest.approx(60_000_000.0)
        assert record.rnd_expenses == pytest.approx(30_000_000.0)
        assert record.goodwill == pytest.approx(10_000_000.0)
        assert record.cash == pytest.approx(500_000_000.0)
        assert record.comprehensive_income == pytest.approx(75_000_000.0)
        assert record.equity_ratio_official == pytest.approx(36.0)
        assert record.payout_ratio == pytest.approx(28.57)
        assert record.per == pytest.approx(15.0)
        assert record.profit_before_tax == pytest.approx(95_000_000.0)
        assert record.roe_official == pytest.approx(3.89)
        assert record.accounting_standard == "JP GAAP"
        assert record.submit_date == "2025-06-15"

    def test_正常系_最小構成で生成できる(self) -> None:
        """edinet_code と fiscal_year のみで生成できること。"""
        record = FinancialRecord(edinet_code="E00001", fiscal_year=2025)
        assert record.edinet_code == "E00001"
        assert record.fiscal_year == 2025
        assert record.revenue is None

    def test_正常系_数値フィールドがfloat_or_none型(self) -> None:
        """FinancialRecord の数値フィールドが float | None であること。"""
        record = FinancialRecord(
            edinet_code="E00001",
            fiscal_year=2025,
            revenue=100.0,
            eps=17.5,
            bps=90.0,
        )
        assert isinstance(record.revenue, float)
        assert isinstance(record.eps, float)
        assert isinstance(record.bps, float)

    def test_正常系_num_employeesがint_or_none型(self) -> None:
        """num_employees が int | None であること。"""
        record = FinancialRecord(
            edinet_code="E00001",
            fiscal_year=2025,
            num_employees=5000,
        )
        assert isinstance(record.num_employees, int)

    def test_正常系_str型フィールドがstr_or_none型(self) -> None:
        """accounting_standard, submit_date が str | None であること。"""
        record = FinancialRecord(
            edinet_code="E00001",
            fiscal_year=2025,
            accounting_standard="JP GAAP",
            submit_date="2025-06-15",
        )
        assert isinstance(record.accounting_standard, str)
        assert isinstance(record.submit_date, str)


# =============================================================================
# RatioRecord dataclass
# =============================================================================


class TestRatioRecord:
    """Test RatioRecord frozen dataclass (API-verified fields)."""

    def test_正常系_frozenである(self) -> None:
        """RatioRecord がフィールド変更不可であること。"""
        record = RatioRecord(edinet_code="E00001", fiscal_year=2025, roe=3.89)
        with pytest.raises(FrozenInstanceError):
            record.roe = 0.0

    def test_正常系_fiscal_yearがint型である(self) -> None:
        """fiscal_year が int 型であること（API検証結果に基づく）。"""
        record = RatioRecord(edinet_code="E00001", fiscal_year=2025)
        assert isinstance(record.fiscal_year, int)
        assert record.fiscal_year == 2025

    def test_正常系_period_typeフィールドが存在しない(self) -> None:
        """period_type フィールドが削除されていること。"""
        assert not hasattr(
            RatioRecord(edinet_code="E00001", fiscal_year=2025),
            "period_type",
        )
        field_names = {f.name for f in fields(RatioRecord)}
        assert "period_type" not in field_names

    def test_正常系_全Optionalフィールドのデフォルトがnone(self) -> None:
        """全比率フィールドが default=None であること。"""
        record = RatioRecord(edinet_code="E00001", fiscal_year=2025)
        # API検証で確認された20フィールド（edinet_code, fiscal_year 除く）
        optional_fields = [
            "adjusted_dividend_per_share",
            "asset_turnover",
            "bps",
            "diluted_eps",
            "dividend_per_share",
            "dividend_yield",
            "eps",
            "equity_ratio",
            "equity_ratio_official",
            "fcf",
            "net_income_per_employee",
            "net_margin",
            "payout_ratio",
            "per",
            "revenue_per_employee",
            "roa",
            "roe",
            "roe_official",
            "split_adjustment_factor",
        ]
        for field_name in optional_fields:
            value = getattr(record, field_name)
            assert value is None, (
                f"Field {field_name} default should be None, got {value}"
            )

    def test_正常系_新フィールド名が存在する(self) -> None:
        """API検証で確認された新フィールド名が存在すること。"""
        field_names = {f.name for f in fields(RatioRecord)}
        expected_new_fields = {
            "adjusted_dividend_per_share",
            "dividend_yield",
            "equity_ratio_official",
            "fcf",
            "net_income_per_employee",
            "per",
            "revenue_per_employee",
            "roe_official",
            "split_adjustment_factor",
            "diluted_eps",
            "bps",
        }
        for field_name in expected_new_fields:
            assert field_name in field_names, (
                f"New field {field_name} is missing from RatioRecord"
            )

    def test_正常系_削除済みフィールドが存在しない(self) -> None:
        """旧フィールドが削除されていること。"""
        field_names = {f.name for f in fields(RatioRecord)}
        deleted_fields = {
            "operating_margin",
            "debt_equity_ratio",
            "current_ratio",
            "interest_coverage_ratio",
            "revenue_growth",
            "operating_income_growth",
            "net_income_growth",
            "period_type",
        }
        for field_name in deleted_fields:
            assert field_name not in field_names, (
                f"Deleted field {field_name} still exists in RatioRecord"
            )

    def test_正常系_全フィールドが正しく設定される(
        self, sample_ratio_record: RatioRecord
    ) -> None:
        """RatioRecord の全フィールドが正しく設定されること。"""
        record = sample_ratio_record
        assert record.edinet_code == "E00001"
        assert record.fiscal_year == 2025
        assert record.roe == pytest.approx(3.89)
        assert record.roa == pytest.approx(1.40)
        assert record.roe_official == pytest.approx(3.89)
        assert record.net_margin == pytest.approx(7.0)
        assert record.equity_ratio == pytest.approx(36.0)
        assert record.equity_ratio_official == pytest.approx(36.0)
        assert record.payout_ratio == pytest.approx(28.57)
        assert record.asset_turnover == pytest.approx(0.20)
        assert record.eps == pytest.approx(350.0)
        assert record.diluted_eps == pytest.approx(345.0)
        assert record.bps == pytest.approx(9_000.0)
        assert record.dividend_per_share == pytest.approx(100.0)
        assert record.adjusted_dividend_per_share == pytest.approx(100.0)
        assert record.dividend_yield == pytest.approx(2.5)
        assert record.per == pytest.approx(15.0)
        assert record.fcf == pytest.approx(70_000_000.0)
        assert record.net_income_per_employee == pytest.approx(14_000.0)
        assert record.revenue_per_employee == pytest.approx(200_000.0)
        assert record.split_adjustment_factor == pytest.approx(1.0)

    def test_正常系_最小構成で生成できる(self) -> None:
        """edinet_code と fiscal_year のみで生成できること。"""
        record = RatioRecord(edinet_code="E00001", fiscal_year=2025)
        assert record.edinet_code == "E00001"
        assert record.fiscal_year == 2025
        assert record.roe is None

    def test_正常系_全比率フィールドがfloat_or_none型(self) -> None:
        """RatioRecord の比率フィールドが float | None であること。"""
        record = RatioRecord(
            edinet_code="E00001",
            fiscal_year=2025,
            roe=3.89,
            roa=1.40,
            net_margin=7.0,
        )
        assert isinstance(record.roe, float)
        assert isinstance(record.roa, float)
        assert isinstance(record.net_margin, float)


# =============================================================================
# AnalysisResult dataclass
# =============================================================================


class TestAnalysisResult:
    """Test AnalysisResult frozen dataclass."""

    def test_正常系_frozenである(self) -> None:
        """AnalysisResult がフィールド変更不可であること。"""
        result = AnalysisResult(
            edinet_code="E00001",
            health_score=75.0,
            benchmark_comparison="above_average",
            commentary="財務健全性は平均以上です。",
        )
        with pytest.raises(FrozenInstanceError):
            result.health_score = 0.0

    def test_正常系_全フィールドが正しく設定される(self) -> None:
        """AnalysisResult の全フィールドが正しく設定されること。"""
        result = AnalysisResult(
            edinet_code="E00001",
            health_score=75.0,
            benchmark_comparison="above_average",
            commentary="財務健全性は平均以上です。",
        )
        assert result.edinet_code == "E00001"
        assert result.health_score == 75.0
        assert result.benchmark_comparison == "above_average"
        assert result.commentary == "財務健全性は平均以上です。"


# =============================================================================
# TextBlock dataclass
# =============================================================================


class TestTextBlock:
    """Test TextBlock frozen dataclass."""

    def test_正常系_frozenである(self) -> None:
        """TextBlock がフィールド変更不可であること。"""
        block = TextBlock(
            edinet_code="E00001",
            fiscal_year="2025",
            business_overview="事業概要テキスト",
            risk_factors="リスクファクターテキスト",
            management_analysis="経営分析テキスト",
        )
        with pytest.raises(FrozenInstanceError):
            block.business_overview = "変更"

    def test_正常系_全フィールドが正しく設定される(self) -> None:
        """TextBlock の全フィールドが正しく設定されること。"""
        block = TextBlock(
            edinet_code="E00001",
            fiscal_year="2025",
            business_overview="事業概要テキスト",
            risk_factors="リスクファクターテキスト",
            management_analysis="経営分析テキスト",
        )
        assert block.edinet_code == "E00001"
        assert block.fiscal_year == "2025"
        assert block.business_overview == "事業概要テキスト"
        assert block.risk_factors == "リスクファクターテキスト"
        assert block.management_analysis == "経営分析テキスト"

    def test_正常系_全フィールドがstr型(self) -> None:
        """TextBlock の全フィールドが str であること。"""
        block = TextBlock(
            edinet_code="E00001",
            fiscal_year="2025",
            business_overview="概要",
            risk_factors="リスク",
            management_analysis="分析",
        )
        for field_name in [
            "edinet_code",
            "fiscal_year",
            "business_overview",
            "risk_factors",
            "management_analysis",
        ]:
            assert isinstance(getattr(block, field_name), str), (
                f"Field {field_name} is not str"
            )


# =============================================================================
# RankingEntry dataclass
# =============================================================================


class TestRankingEntry:
    """Test RankingEntry frozen dataclass."""

    def test_正常系_frozenである(self) -> None:
        """RankingEntry がフィールド変更不可であること。"""
        entry = RankingEntry(
            metric="roe",
            rank=1,
            edinet_code="E00001",
            corp_name="テスト株式会社",
            value=25.5,
        )
        with pytest.raises(FrozenInstanceError):
            entry.rank = 2

    def test_正常系_全フィールドが正しく設定される(self) -> None:
        """RankingEntry の全フィールドが正しく設定されること。"""
        entry = RankingEntry(
            metric="roe",
            rank=1,
            edinet_code="E00001",
            corp_name="テスト株式会社",
            value=25.5,
        )
        assert entry.metric == "roe"
        assert entry.rank == 1
        assert entry.edinet_code == "E00001"
        assert entry.corp_name == "テスト株式会社"
        assert entry.value == 25.5

    def test_正常系_rankがint型でvalueがfloat型(self) -> None:
        """RankingEntry の rank が int で value が float であること。"""
        entry = RankingEntry(
            metric="eps",
            rank=100,
            edinet_code="E00002",
            corp_name="別の会社",
            value=1500.0,
        )
        assert isinstance(entry.rank, int)
        assert isinstance(entry.value, float)


# =============================================================================
# Industry dataclass
# =============================================================================


class TestIndustry:
    """Test Industry frozen dataclass."""

    def test_正常系_frozenである(self) -> None:
        """Industry がフィールド変更不可であること。"""
        industry = Industry(
            slug="information-communication",
            name="情報・通信業",
            company_count=500,
        )
        with pytest.raises(FrozenInstanceError):
            industry.name = "変更"

    def test_正常系_全フィールドが正しく設定される(self) -> None:
        """Industry の全フィールドが正しく設定されること。"""
        industry = Industry(
            slug="information-communication",
            name="情報・通信業",
            company_count=500,
        )
        assert industry.slug == "information-communication"
        assert industry.name == "情報・通信業"
        assert industry.company_count == 500

    def test_正常系_company_countがint型(self) -> None:
        """Industry の company_count が int であること。"""
        industry = Industry(
            slug="manufacturing",
            name="製造業",
            company_count=1200,
        )
        assert isinstance(industry.company_count, int)


# =============================================================================
# SyncProgress dataclass
# =============================================================================


class TestSyncProgress:
    """Test SyncProgress frozen dataclass."""

    def test_正常系_frozenである(self) -> None:
        """SyncProgress がフィールド変更不可であること。"""
        progress = SyncProgress(
            current_phase="companies",
            completed_codes=(),
            today_api_calls=0,
            errors=(),
        )
        with pytest.raises(FrozenInstanceError):
            progress.current_phase = "financials"

    def test_正常系_デフォルト値が正しい(self) -> None:
        """SyncProgress のデフォルト値が設計通りであること。"""
        progress = SyncProgress(
            current_phase="companies",
        )
        assert progress.current_phase == "companies"
        assert progress.completed_codes == ()
        assert progress.today_api_calls == 0
        assert progress.errors == ()

    def test_正常系_カスタム値で生成できる(self) -> None:
        """SyncProgress をカスタム値で生成できること。"""
        progress = SyncProgress(
            current_phase="financials",
            completed_codes=("E00001", "E00002"),
            today_api_calls=150,
            errors=("E00003: timeout",),
        )
        assert progress.current_phase == "financials"
        assert progress.completed_codes == ("E00001", "E00002")
        assert progress.today_api_calls == 150
        assert progress.errors == ("E00003: timeout",)

    def test_正常系_全フィールドが存在する(self) -> None:
        """SyncProgress が設計通りのフィールドを持つこと。"""
        progress = SyncProgress(current_phase="companies")
        assert hasattr(progress, "current_phase")
        assert hasattr(progress, "completed_codes")
        assert hasattr(progress, "today_api_calls")
        assert hasattr(progress, "errors")

    def test_正常系_completed_codesがタプルで不変(self) -> None:
        """completed_codes がタプルで不変であること。"""
        progress = SyncProgress(
            current_phase="companies",
            completed_codes=("E00001", "E00002"),
        )
        assert isinstance(progress.completed_codes, tuple)
