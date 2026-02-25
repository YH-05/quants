"""Pytest configuration and fixtures for market.edinet tests."""

from collections.abc import Generator
from pathlib import Path
from unittest.mock import patch

import pytest

from market.edinet.types import (  # type: ignore[import-not-found]  # AIDEV-NOTE: #3671
    Company,
    EdinetConfig,
    FinancialRecord,
    RatioRecord,
)


@pytest.fixture(autouse=True)
def mock_load_project_env() -> Generator[None]:
    """Disable load_project_env during tests to ensure env var mocking works.

    Note: load_project_env is now in utils_core.settings, not market.edinet modules.
    """
    with patch("utils_core.settings.load_project_env"):
        yield


@pytest.fixture
def mock_api_key(monkeypatch: pytest.MonkeyPatch) -> str:
    """環境変数にモック API キーを設定。

    Returns
    -------
    str
        設定したモック API キー
    """
    api_key = "test_edinet_api_key_12345"
    monkeypatch.setenv("EDINET_DB_API_KEY", api_key)
    return api_key


@pytest.fixture
def sample_config(tmp_path: Path) -> EdinetConfig:
    """テスト用の EdinetConfig を tmp_path で作成。

    Parameters
    ----------
    tmp_path : Path
        pytest 提供の一時ディレクトリ

    Returns
    -------
    EdinetConfig
        一時ディレクトリを使用した EDINET 設定
    """
    return EdinetConfig(
        api_key="test_edinet_api_key_12345",
        db_path=tmp_path / "edinet.duckdb",
    )


@pytest.fixture
def sample_company() -> Company:
    """テスト用の Company サンプルデータを作成。

    Returns
    -------
    Company
        サンプル企業データ
    """
    return Company(
        edinet_code="E00001",
        sec_code="10000",
        corp_name="テスト株式会社",
        industry_code="3050",
        industry_name="情報・通信業",
        listing_status="上場",
    )


@pytest.fixture
def sample_financial_record() -> FinancialRecord:
    """テスト用の FinancialRecord サンプルデータを作成。

    Returns
    -------
    FinancialRecord
        サンプル財務データ（24指標）
    """
    return FinancialRecord(
        edinet_code="E00001",
        fiscal_year="2025",
        period_type="annual",
        revenue=1_000_000_000,
        operating_income=100_000_000,
        ordinary_income=110_000_000,
        net_income=70_000_000,
        total_assets=5_000_000_000,
        net_assets=2_000_000_000,
        equity=1_800_000_000,
        interest_bearing_debt=1_000_000_000,
        operating_cf=150_000_000,
        investing_cf=-80_000_000,
        financing_cf=-50_000_000,
        free_cf=70_000_000,
        eps=350.0,
        bps=9_000.0,
        dividend_per_share=100.0,
        shares_outstanding=200_000,
        employees=5_000,
        capex=80_000_000,
        depreciation=60_000_000,
        rnd_expense=30_000_000,
        goodwill=10_000_000,
    )


@pytest.fixture
def sample_ratio_record() -> RatioRecord:
    """テスト用の RatioRecord サンプルデータを作成。

    Returns
    -------
    RatioRecord
        サンプル財務比率データ（13指標）
    """
    return RatioRecord(
        edinet_code="E00001",
        fiscal_year="2025",
        period_type="annual",
        roe=3.89,
        roa=1.40,
        operating_margin=10.0,
        net_margin=7.0,
        equity_ratio=36.0,
        debt_equity_ratio=0.56,
        current_ratio=1.50,
        interest_coverage_ratio=5.0,
        payout_ratio=28.57,
        asset_turnover=0.20,
        revenue_growth=5.0,
        operating_income_growth=8.0,
        net_income_growth=6.0,
    )
