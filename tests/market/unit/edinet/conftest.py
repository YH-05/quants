"""Pytest configuration and fixtures for market.edinet tests."""

from __future__ import annotations

from typing import TYPE_CHECKING
from unittest.mock import patch

if TYPE_CHECKING:
    from collections.abc import Generator
    from pathlib import Path

import pytest

from market.edinet.types import (
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
        name="テスト株式会社",
        industry="情報・通信業",
    )


@pytest.fixture
def sample_financial_record() -> FinancialRecord:
    """テスト用の FinancialRecord サンプルデータを作成。

    API検証結果に基づく新フィールド構成（全フィールド Optional）。
    fiscal_year は int 型。period_type は削除済み。

    Returns
    -------
    FinancialRecord
        サンプル財務データ（24フィールド + edinet_code/fiscal_year）
    """
    return FinancialRecord(
        edinet_code="E00001",
        fiscal_year=2025,
        revenue=1_000_000_000.0,
        operating_income=100_000_000.0,
        ordinary_income=110_000_000.0,
        net_income=70_000_000.0,
        total_assets=5_000_000_000.0,
        net_assets=2_000_000_000.0,
        shareholders_equity=1_800_000_000.0,
        cf_operating=150_000_000.0,
        cf_investing=-80_000_000.0,
        cf_financing=-50_000_000.0,
        eps=350.0,
        bps=9_000.0,
        diluted_eps=345.0,
        dividend_per_share=100.0,
        num_employees=5_000,
        capex=80_000_000.0,
        depreciation=60_000_000.0,
        rnd_expenses=30_000_000.0,
        goodwill=10_000_000.0,
        cash=500_000_000.0,
        comprehensive_income=75_000_000.0,
        equity_ratio_official=36.0,
        payout_ratio=28.57,
        per=15.0,
        profit_before_tax=95_000_000.0,
        roe_official=3.89,
        accounting_standard="JP GAAP",
        submit_date="2025-06-15",
    )


@pytest.fixture
def sample_ratio_record() -> RatioRecord:
    """テスト用の RatioRecord サンプルデータを作成。

    API検証結果に基づく新フィールド構成（全フィールド Optional）。
    fiscal_year は int 型。period_type は削除済み。

    Returns
    -------
    RatioRecord
        サンプル財務比率データ（20フィールド + edinet_code/fiscal_year）
    """
    return RatioRecord(
        edinet_code="E00001",
        fiscal_year=2025,
        roe=3.89,
        roa=1.40,
        roe_official=3.89,
        net_margin=7.0,
        equity_ratio=36.0,
        equity_ratio_official=36.0,
        payout_ratio=28.57,
        asset_turnover=0.20,
        eps=350.0,
        diluted_eps=345.0,
        bps=9_000.0,
        dividend_per_share=100.0,
        adjusted_dividend_per_share=100.0,
        dividend_yield=2.5,
        per=15.0,
        fcf=70_000_000.0,
        net_income_per_employee=14_000.0,
        revenue_per_employee=200_000.0,
        split_adjustment_factor=1.0,
    )
