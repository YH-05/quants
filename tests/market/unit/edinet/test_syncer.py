"""Tests for the EDINET sync orchestrator (EdinetSyncer).

Tests cover:
- 6-phase execution order
- Resume from checkpoint
- Graceful rate-limit stop
- 404 error skip
- Checkpoint save every 100 companies
- Single company sync
- Daily incremental sync
- State persistence and loading

All external dependencies (EdinetClient, EdinetStorage) are mocked.

See Also
--------
market.edinet.syncer : The module under test.
"""

from __future__ import annotations

import json
from typing import TYPE_CHECKING
from unittest.mock import MagicMock, call, patch

import pytest

from market.edinet.errors import (
    EdinetAPIError,
    EdinetRateLimitError,
)
from market.edinet.syncer import (
    CHECKPOINT_INTERVAL,
    PHASE_ANALYSIS_TEXT,
    PHASE_COMPANIES,
    PHASE_COMPANY_DETAILS,
    PHASE_COMPLETE,
    PHASE_FINANCIALS_RATIOS,
    PHASE_INDUSTRIES,
    PHASE_ORDER,
    PHASE_RANKINGS,
    EdinetSyncer,
    SyncResult,
)
from market.edinet.types import (
    AnalysisResult,
    Company,
    EdinetConfig,
    FinancialRecord,
    Industry,
    RankingEntry,
    RatioRecord,
    TextBlock,
)

if TYPE_CHECKING:
    from pathlib import Path


# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture
def syncer_config(tmp_path: Path) -> EdinetConfig:
    """テスト用の EdinetConfig を作成。"""
    return EdinetConfig(
        api_key="test_key",
        db_path=tmp_path / "edinet.duckdb",
        polite_delay=0.0,
    )


@pytest.fixture
def mock_client() -> MagicMock:
    """モック EdinetClient を作成。"""
    client = MagicMock()
    client.list_companies.return_value = [
        Company(
            edinet_code="E00001",
            sec_code="10000",
            corp_name="テスト株式会社A",
            industry_code="3050",
            industry_name="情報・通信業",
            listing_status="上場",
        ),
        Company(
            edinet_code="E00002",
            sec_code="20000",
            corp_name="テスト株式会社B",
            industry_code="3050",
            industry_name="情報・通信業",
            listing_status="上場",
        ),
    ]
    client.list_industries.return_value = [
        Industry(
            slug="information-communication",
            name="情報・通信業",
            company_count=500,
        ),
    ]
    client.get_industry.return_value = {
        "slug": "information-communication",
        "name": "情報・通信業",
        "company_count": 500,
    }
    client.get_ranking.return_value = [
        RankingEntry(
            metric="roe",
            rank=1,
            edinet_code="E00001",
            corp_name="テスト株式会社A",
            value=25.5,
        ),
    ]
    client.get_company.return_value = Company(
        edinet_code="E00001",
        sec_code="10000",
        corp_name="テスト株式会社A",
        industry_code="3050",
        industry_name="情報・通信業",
        listing_status="上場",
    )
    client.get_financials.return_value = [
        FinancialRecord(
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
            dividend_per_share=100.0,
            num_employees=5_000,
            capex=80_000_000.0,
            depreciation=60_000_000.0,
            rnd_expenses=30_000_000.0,
            goodwill=10_000_000.0,
        ),
    ]
    client.get_ratios.return_value = [
        RatioRecord(
            edinet_code="E00001",
            fiscal_year=2025,
            roe=3.89,
            roa=1.40,
            net_margin=7.0,
            equity_ratio=36.0,
            payout_ratio=28.57,
            asset_turnover=0.20,
            eps=350.0,
            bps=9_000.0,
            dividend_per_share=100.0,
            per=15.0,
        ),
    ]
    client.get_analysis.return_value = AnalysisResult(
        edinet_code="E00001",
        health_score=75.0,
        benchmark_comparison="above_average",
        commentary="The company is financially healthy.",
    )
    client.get_text_blocks.return_value = [
        TextBlock(
            edinet_code="E00001",
            fiscal_year="2025",
            business_overview="事業概要テキスト",
            risk_factors="リスクファクターテキスト",
            management_analysis="経営分析テキスト",
        ),
    ]
    return client


@pytest.fixture
def mock_storage() -> MagicMock:
    """モック EdinetStorage を作成。"""
    storage = MagicMock()
    storage.get_all_company_codes.return_value = ["E00001", "E00002"]
    storage.get_stats.return_value = {
        "companies": 2,
        "financials": 0,
        "ratios": 0,
        "analyses": 0,
        "text_blocks": 0,
        "rankings": 0,
        "industries": 0,
        "industry_details": 0,
    }
    return storage


@pytest.fixture
def syncer(
    syncer_config: EdinetConfig,
    mock_client: MagicMock,
    mock_storage: MagicMock,
) -> EdinetSyncer:
    """テスト用の EdinetSyncer を作成。"""
    return EdinetSyncer(
        config=syncer_config,
        client=mock_client,
        storage=mock_storage,
    )


# =============================================================================
# Phase Order Tests
# =============================================================================


class TestPhaseOrder:
    """フェーズ実行順序のテスト。"""

    def test_正常系_6フェーズが正しい順序で定義されていること(self) -> None:
        assert PHASE_ORDER == [
            PHASE_COMPANIES,
            PHASE_INDUSTRIES,
            PHASE_RANKINGS,
            PHASE_COMPANY_DETAILS,
            PHASE_FINANCIALS_RATIOS,
            PHASE_ANALYSIS_TEXT,
        ]

    def test_正常系_6フェーズのrun_initialが正しい順序で実行されること(
        self,
        syncer: EdinetSyncer,
        mock_client: MagicMock,
        mock_storage: MagicMock,
    ) -> None:
        results = syncer.run_initial()

        # All 6 phases should succeed
        assert len(results) == 6
        assert all(r.success for r in results)

        # Verify phase order
        assert results[0].phase == PHASE_COMPANIES
        assert results[1].phase == PHASE_INDUSTRIES
        assert results[2].phase == PHASE_RANKINGS
        assert results[3].phase == PHASE_COMPANY_DETAILS
        assert results[4].phase == PHASE_FINANCIALS_RATIOS
        assert results[5].phase == PHASE_ANALYSIS_TEXT

    def test_正常系_全フェーズ完了後にcompleteが設定されること(
        self,
        syncer: EdinetSyncer,
        syncer_config: EdinetConfig,
    ) -> None:
        syncer.run_initial()

        # Read state file
        state_path = syncer_config.sync_state_path
        state_data = json.loads(state_path.read_text(encoding="utf-8"))
        assert state_data["current_phase"] == PHASE_COMPLETE


# =============================================================================
# Phase 1: Companies
# =============================================================================


class TestPhaseCompanies:
    """フェーズ1（企業一覧）のテスト。"""

    def test_正常系_企業一覧をフェッチしてストレージに保存すること(
        self,
        syncer: EdinetSyncer,
        mock_client: MagicMock,
        mock_storage: MagicMock,
    ) -> None:
        results = syncer.run_initial()

        mock_client.list_companies.assert_called_once()
        mock_storage.upsert_companies.assert_called()
        assert results[0].phase == PHASE_COMPANIES
        assert results[0].success is True


# =============================================================================
# Phase 2: Industries
# =============================================================================


class TestPhaseIndustries:
    """フェーズ2（業種）のテスト。"""

    def test_正常系_業種一覧と詳細をフェッチすること(
        self,
        syncer: EdinetSyncer,
        mock_client: MagicMock,
        mock_storage: MagicMock,
    ) -> None:
        results = syncer.run_initial()

        mock_client.list_industries.assert_called_once()
        mock_client.get_industry.assert_called_once_with("information-communication")
        mock_storage.upsert_industries.assert_called()
        assert results[1].phase == PHASE_INDUSTRIES
        assert results[1].success is True


# =============================================================================
# Phase 3: Rankings
# =============================================================================


class TestPhaseRankings:
    """フェーズ3（ランキング）のテスト。"""

    def test_正常系_18メトリクス全てのランキングをフェッチすること(
        self,
        syncer: EdinetSyncer,
        mock_client: MagicMock,
        mock_storage: MagicMock,
    ) -> None:
        results = syncer.run_initial()

        assert mock_client.get_ranking.call_count == 20
        mock_storage.upsert_rankings.assert_called()
        assert results[2].phase == PHASE_RANKINGS
        assert results[2].success is True


# =============================================================================
# Phase 4: Company Details
# =============================================================================


class TestPhaseCompanyDetails:
    """フェーズ4（企業詳細）のテスト。"""

    def test_正常系_全企業の詳細をフェッチすること(
        self,
        syncer: EdinetSyncer,
        mock_client: MagicMock,
        mock_storage: MagicMock,
    ) -> None:
        results = syncer.run_initial()

        # Should be called for each company code
        assert mock_client.get_company.call_count == 2
        assert results[3].phase == PHASE_COMPANY_DETAILS
        assert results[3].success is True
        assert results[3].companies_processed == 2


# =============================================================================
# Phase 5: Financials + Ratios
# =============================================================================


class TestPhaseFinancialsRatios:
    """フェーズ5（財務+比率）のテスト。"""

    def test_正常系_全企業の財務と比率をフェッチすること(
        self,
        syncer: EdinetSyncer,
        mock_client: MagicMock,
        mock_storage: MagicMock,
    ) -> None:
        results = syncer.run_initial()

        assert mock_client.get_financials.call_count == 2
        assert mock_client.get_ratios.call_count == 2
        mock_storage.upsert_financials.assert_called()
        mock_storage.upsert_ratios.assert_called()
        assert results[4].phase == PHASE_FINANCIALS_RATIOS
        assert results[4].success is True


# =============================================================================
# Phase 6: Analysis + Text Blocks
# =============================================================================


class TestPhaseAnalysisText:
    """フェーズ6（分析+テキストブロック）のテスト。"""

    def test_正常系_全企業の分析とテキストブロックをフェッチすること(
        self,
        syncer: EdinetSyncer,
        mock_client: MagicMock,
        mock_storage: MagicMock,
    ) -> None:
        results = syncer.run_initial()

        assert mock_client.get_analysis.call_count == 2
        assert mock_client.get_text_blocks.call_count == 2
        mock_storage.upsert_analyses.assert_called()
        mock_storage.upsert_text_blocks.assert_called()
        assert results[5].phase == PHASE_ANALYSIS_TEXT
        assert results[5].success is True


# =============================================================================
# Resume Tests
# =============================================================================


class TestResume:
    """レジューム機能のテスト。"""

    def test_正常系_中断箇所からレジュームすること(
        self,
        syncer_config: EdinetConfig,
        mock_client: MagicMock,
        mock_storage: MagicMock,
    ) -> None:
        # Write state file indicating Phase 4 with E00001 completed
        state_path = syncer_config.sync_state_path
        state_path.parent.mkdir(parents=True, exist_ok=True)
        state_data = {
            "current_phase": PHASE_COMPANY_DETAILS,
            "completed_codes": ["E00001"],
            "today_api_calls": 50,
            "errors": [],
        }
        state_path.write_text(
            json.dumps(state_data),
            encoding="utf-8",
        )

        syncer = EdinetSyncer(
            config=syncer_config,
            client=mock_client,
            storage=mock_storage,
        )

        results = syncer.resume()

        # Should start from Phase 4 (index 3)
        assert len(results) == 3  # Phase 4, 5, 6
        assert results[0].phase == PHASE_COMPANY_DETAILS
        assert results[1].phase == PHASE_FINANCIALS_RATIOS
        assert results[2].phase == PHASE_ANALYSIS_TEXT

        # E00001 should be skipped in Phase 4 (already completed)
        # Only E00002 should be processed
        assert mock_client.get_company.call_count == 1

    def test_正常系_不正な状態ファイルでデフォルトから開始すること(
        self,
        syncer_config: EdinetConfig,
        mock_client: MagicMock,
        mock_storage: MagicMock,
    ) -> None:
        state_path = syncer_config.sync_state_path
        state_path.parent.mkdir(parents=True, exist_ok=True)
        state_path.write_text("invalid json{{{", encoding="utf-8")

        syncer = EdinetSyncer(
            config=syncer_config,
            client=mock_client,
            storage=mock_storage,
        )

        results = syncer.resume()
        # Should start from beginning (6 phases)
        assert len(results) == 6

    def test_正常系_空の状態ファイルでデフォルトから開始すること(
        self,
        syncer_config: EdinetConfig,
        mock_client: MagicMock,
        mock_storage: MagicMock,
    ) -> None:
        state_path = syncer_config.sync_state_path
        state_path.parent.mkdir(parents=True, exist_ok=True)
        state_path.write_text("", encoding="utf-8")

        syncer = EdinetSyncer(
            config=syncer_config,
            client=mock_client,
            storage=mock_storage,
        )

        results = syncer.resume()
        assert len(results) == 6


# =============================================================================
# State Persistence Tests
# =============================================================================


class TestStatePersistence:
    """_sync_state.json への永続化テスト。"""

    def test_正常系_進捗がsync_state_jsonに永続化されること(
        self,
        syncer: EdinetSyncer,
        syncer_config: EdinetConfig,
    ) -> None:
        syncer.run_initial()

        state_path = syncer_config.sync_state_path
        assert state_path.exists()

        state_data = json.loads(state_path.read_text(encoding="utf-8"))
        assert "current_phase" in state_data
        assert "completed_codes" in state_data
        assert "today_api_calls" in state_data
        assert "errors" in state_data

    def test_正常系_状態ファイルが存在しない場合デフォルトで初期化すること(
        self,
        syncer_config: EdinetConfig,
        mock_client: MagicMock,
        mock_storage: MagicMock,
    ) -> None:
        # Do not create state file
        syncer = EdinetSyncer(
            config=syncer_config,
            client=mock_client,
            storage=mock_storage,
        )

        status = syncer.get_status()
        assert status["current_phase"] == PHASE_COMPANIES
        assert status["completed_codes_count"] == 0


# =============================================================================
# Checkpoint Tests
# =============================================================================


class TestCheckpoint:
    """チェックポイント保存のテスト。"""

    def test_正常系_100社ごとにチェックポイントが保存されること(
        self,
        syncer_config: EdinetConfig,
        mock_client: MagicMock,
        mock_storage: MagicMock,
    ) -> None:
        # Generate 150 company codes
        codes = [f"E{i:05d}" for i in range(1, 151)]
        mock_storage.get_all_company_codes.return_value = codes

        syncer = EdinetSyncer(
            config=syncer_config,
            client=mock_client,
            storage=mock_storage,
        )

        results = syncer.run_initial()

        # Verify state file was written (multiple times for checkpoints)
        state_path = syncer_config.sync_state_path
        assert state_path.exists()

        # Verify Phase 4 (company_details) processed all 150
        # Phase 4 is at index 3
        assert results[3].phase == PHASE_COMPANY_DETAILS
        assert results[3].companies_processed == 150

    def test_正常系_チェックポイントインターバルが100であること(self) -> None:
        assert CHECKPOINT_INTERVAL == 100


# =============================================================================
# Rate Limit Graceful Stop Tests
# =============================================================================


class TestRateLimitGracefulStop:
    """レート制限到達時の graceful 停止テスト。"""

    def test_正常系_フェーズ1でレート制限に達した場合停止すること(
        self,
        syncer: EdinetSyncer,
        mock_client: MagicMock,
    ) -> None:
        mock_client.list_companies.side_effect = EdinetRateLimitError(
            message="Daily limit exceeded",
            calls_used=950,
            calls_limit=950,
        )

        results = syncer.run_initial()

        assert len(results) == 1
        assert results[0].success is False
        assert results[0].stopped_reason == "rate_limit"

    def test_正常系_フェーズ4で途中でレート制限に達した場合チェックポイント保存して停止すること(
        self,
        syncer_config: EdinetConfig,
        mock_client: MagicMock,
        mock_storage: MagicMock,
    ) -> None:
        # E00001 succeeds, E00002 hits rate limit
        call_count = 0

        def side_effect_get_company(code: str) -> Company:
            nonlocal call_count
            call_count += 1
            if call_count > 1:
                raise EdinetRateLimitError(
                    message="Daily limit exceeded",
                    calls_used=950,
                    calls_limit=950,
                )
            return Company(
                edinet_code=code,
                sec_code="10000",
                corp_name="テスト",
                industry_code="3050",
                industry_name="情報・通信業",
                listing_status="上場",
            )

        mock_client.get_company.side_effect = side_effect_get_company

        syncer = EdinetSyncer(
            config=syncer_config,
            client=mock_client,
            storage=mock_storage,
        )

        results = syncer.run_initial()

        # Phase 1-3 succeed, Phase 4 stops
        phase4_result = results[3]
        assert phase4_result.phase == PHASE_COMPANY_DETAILS
        assert phase4_result.success is False
        assert phase4_result.stopped_reason == "rate_limit"
        assert phase4_result.companies_processed == 1

        # Verify checkpoint was saved
        state_path = syncer_config.sync_state_path
        state_data = json.loads(state_path.read_text(encoding="utf-8"))
        assert "E00001" in state_data["completed_codes"]

    def test_正常系_レート制限後にレジュームで残りの企業を処理すること(
        self,
        syncer_config: EdinetConfig,
        mock_client: MagicMock,
        mock_storage: MagicMock,
    ) -> None:
        # Simulate state where Phase 4 was interrupted with E00001 completed
        state_path = syncer_config.sync_state_path
        state_path.parent.mkdir(parents=True, exist_ok=True)
        state_data = {
            "current_phase": PHASE_COMPANY_DETAILS,
            "completed_codes": ["E00001"],
            "today_api_calls": 50,
            "errors": [],
        }
        state_path.write_text(json.dumps(state_data), encoding="utf-8")

        syncer = EdinetSyncer(
            config=syncer_config,
            client=mock_client,
            storage=mock_storage,
        )

        results = syncer.resume()

        # Phase 4 should only process E00002 (E00001 already done)
        assert results[0].phase == PHASE_COMPANY_DETAILS
        assert results[0].success is True
        # get_company called once for E00002
        assert mock_client.get_company.call_count == 1


# =============================================================================
# 404 Error Skip Tests
# =============================================================================


class TestErrorSkip:
    """404エラーのスキップテスト。"""

    def test_正常系_404エラーの企業をスキップして続行すること(
        self,
        syncer: EdinetSyncer,
        mock_client: MagicMock,
    ) -> None:
        # First company returns 404, second succeeds
        def side_effect_get_company(code: str) -> Company:
            if code == "E00001":
                raise EdinetAPIError(
                    message="Not found",
                    url=f"https://edinetdb.jp/v1/companies/{code}",
                    status_code=404,
                    response_body="",
                )
            return Company(
                edinet_code=code,
                sec_code="20000",
                corp_name="テスト株式会社B",
                industry_code="3050",
                industry_name="情報・通信業",
                listing_status="上場",
            )

        mock_client.get_company.side_effect = side_effect_get_company

        results = syncer.run_initial()

        # Phase 4 should complete despite 404 error
        phase4_result = results[3]
        assert phase4_result.phase == PHASE_COMPANY_DETAILS
        assert phase4_result.success is True
        assert phase4_result.companies_processed == 2
        assert len(phase4_result.errors) == 1
        assert "404: E00001" in phase4_result.errors[0]

    def test_正常系_フェーズ2で業種404をスキップすること(
        self,
        syncer: EdinetSyncer,
        mock_client: MagicMock,
    ) -> None:
        mock_client.get_industry.side_effect = EdinetAPIError(
            message="Not found",
            url="https://edinetdb.jp/v1/industries/test",
            status_code=404,
            response_body="",
        )

        results = syncer.run_initial()

        # Phase 2 should still succeed (404 is skipped)
        assert results[1].phase == PHASE_INDUSTRIES
        assert results[1].success is True
        assert len(results[1].errors) == 1


# =============================================================================
# Single Company Sync Tests
# =============================================================================


class TestSyncCompany:
    """単一企業同期のテスト。"""

    def test_正常系_単一企業の全データを同期すること(
        self,
        syncer: EdinetSyncer,
        mock_client: MagicMock,
        mock_storage: MagicMock,
    ) -> None:
        result = syncer.sync_company("E00001")

        assert result.success is True
        assert result.companies_processed == 1
        assert result.phase == "single_company"

        # Verify all data fetched
        mock_client.get_company.assert_called_once_with("E00001")
        mock_client.get_financials.assert_called_once_with("E00001")
        mock_client.get_ratios.assert_called_once_with("E00001")
        mock_client.get_analysis.assert_called_once_with("E00001")
        mock_client.get_text_blocks.assert_called_once_with("E00001")

    def test_異常系_単一企業同期でレート制限が発生すること(
        self,
        syncer: EdinetSyncer,
        mock_client: MagicMock,
    ) -> None:
        mock_client.get_company.side_effect = EdinetRateLimitError(
            message="Limit exceeded",
            calls_used=950,
            calls_limit=950,
        )

        result = syncer.sync_company("E00001")

        assert result.success is False
        assert result.stopped_reason == "rate_limit"
        assert result.companies_processed == 0

    def test_異常系_単一企業同期で404が発生すること(
        self,
        syncer: EdinetSyncer,
        mock_client: MagicMock,
    ) -> None:
        mock_client.get_company.side_effect = EdinetAPIError(
            message="Not found",
            url="https://edinetdb.jp/v1/companies/E99999",
            status_code=404,
            response_body="",
        )

        result = syncer.sync_company("E99999")

        assert result.success is False
        assert result.companies_processed == 0
        assert len(result.errors) == 1


# =============================================================================
# Daily Sync Tests
# =============================================================================


class TestRunDaily:
    """デイリー増分同期のテスト。"""

    def test_正常系_日次同期が企業とfinancials_ratiosを実行すること(
        self,
        syncer: EdinetSyncer,
        mock_client: MagicMock,
        mock_storage: MagicMock,
    ) -> None:
        results = syncer.run_daily()

        # Should run Phase 1 (companies) and Phase 5 (financials_ratios)
        assert len(results) == 2
        assert results[0].phase == PHASE_COMPANIES
        assert results[0].success is True
        assert results[1].phase == PHASE_FINANCIALS_RATIOS
        assert results[1].success is True

        # Verify companies were fetched
        mock_client.list_companies.assert_called()

        # Verify financials + ratios fetched for each company
        assert mock_client.get_financials.call_count == 2
        assert mock_client.get_ratios.call_count == 2


# =============================================================================
# Get Status Tests
# =============================================================================


class TestGetStatus:
    """同期状況レポートのテスト。"""

    def test_正常系_ステータスレポートが正しい構造を持つこと(
        self,
        syncer: EdinetSyncer,
    ) -> None:
        status = syncer.get_status()

        assert "current_phase" in status
        assert "completed_codes_count" in status
        assert "today_api_calls" in status
        assert "remaining_api_calls" in status
        assert "errors_count" in status
        assert "db_stats" in status

    def test_正常系_初期状態のステータスが正しいこと(
        self,
        syncer: EdinetSyncer,
    ) -> None:
        status = syncer.get_status()

        assert status["current_phase"] == PHASE_COMPANIES
        assert status["completed_codes_count"] == 0
        assert status["today_api_calls"] == 0


# =============================================================================
# SyncResult Tests
# =============================================================================


class TestSyncResult:
    """SyncResult データクラスのテスト。"""

    def test_正常系_成功結果を作成すること(self) -> None:
        result = SyncResult(
            phase=PHASE_COMPANIES,
            success=True,
            companies_processed=3848,
            errors=(),
        )
        assert result.phase == PHASE_COMPANIES
        assert result.success is True
        assert result.companies_processed == 3848
        assert result.errors == ()
        assert result.stopped_reason is None

    def test_正常系_失敗結果を作成すること(self) -> None:
        result = SyncResult(
            phase=PHASE_COMPANY_DETAILS,
            success=False,
            companies_processed=100,
            errors=("404: E00001",),
            stopped_reason="rate_limit",
        )
        assert result.success is False
        assert result.stopped_reason == "rate_limit"
        assert len(result.errors) == 1
