"""Tests for Orchestrator Phase 6 updates.

Tests the new benchmark_ticker and analyst_scores_path parameters
added to Orchestrator for Phase 6 evaluation.

Key behaviors:
- benchmark_ticker: when set, uses price_provider to fetch benchmark
  index data instead of equal-weight universe returns
- analyst_scores_path: when set, loads analyst scores from the
  specified JSON file and passes to the evaluator
- Backward compatible: both new params are optional (None by default)
"""

from __future__ import annotations

import json
from datetime import date
from typing import TYPE_CHECKING, Any
from unittest.mock import MagicMock, patch

import pandas as pd
import pytest

from dev.ca_strategy.orchestrator import Orchestrator
from dev.ca_strategy.pit import EVALUATION_END_DATE, PORTFOLIO_DATE
from dev.ca_strategy.types import (
    AnalystCorrelation,
    AnalystScore,
    EvaluationResult,
    PerformanceMetrics,
    PortfolioHolding,
    PortfolioResult,
    SectorAllocation,
    StockScore,
    TransparencyMetrics,
)

if TYPE_CHECKING:
    from pathlib import Path


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------
@pytest.fixture()
def config_dir(tmp_path: Path) -> Path:
    """Create config directory with universe.json and benchmark_weights.json."""
    config = tmp_path / "config"
    config.mkdir()

    universe_data = {
        "tickers": [
            {
                "ticker": "AAPL",
                "gics_sector": "Information Technology",
                "bloomberg_ticker": "AAPL US Equity",
            },
            {
                "ticker": "MSFT",
                "gics_sector": "Information Technology",
                "bloomberg_ticker": "MSFT US Equity",
            },
            {
                "ticker": "JPM",
                "gics_sector": "Financials",
                "bloomberg_ticker": "JPM US Equity",
            },
        ]
    }
    (config / "universe.json").write_text(
        json.dumps(universe_data, ensure_ascii=False, indent=2)
    )

    benchmark_data = {
        "weights": {
            "Information Technology": 0.60,
            "Financials": 0.40,
        }
    }
    (config / "benchmark_weights.json").write_text(
        json.dumps(benchmark_data, ensure_ascii=False, indent=2)
    )

    return config


@pytest.fixture()
def workspace_dir(tmp_path: Path) -> Path:
    """Create workspace directory."""
    ws = tmp_path / "workspace"
    ws.mkdir()
    return ws


def _make_portfolio_result() -> PortfolioResult:
    """Create sample portfolio result."""
    return PortfolioResult(
        holdings=[
            PortfolioHolding(
                ticker="AAPL",
                weight=0.6,
                sector="Information Technology",
                score=0.85,
                rationale_summary="Sector rank 1, score 0.85",
            ),
            PortfolioHolding(
                ticker="JPM",
                weight=0.4,
                sector="Financials",
                score=0.7,
                rationale_summary="Sector rank 1, score 0.70",
            ),
        ],
        sector_allocations=[
            SectorAllocation(
                sector="Information Technology",
                benchmark_weight=0.6,
                actual_weight=0.6,
                stock_count=1,
            ),
            SectorAllocation(
                sector="Financials",
                benchmark_weight=0.4,
                actual_weight=0.4,
                stock_count=1,
            ),
        ],
        as_of_date=date(2015, 9, 30),
    )


def _make_stock_scores() -> dict[str, StockScore]:
    """Create sample stock scores."""
    return {
        "AAPL": StockScore(
            ticker="AAPL",
            aggregate_score=0.85,
            claim_count=1,
            structural_weight=0.5,
        ),
        "JPM": StockScore(
            ticker="JPM",
            aggregate_score=0.7,
            claim_count=1,
            structural_weight=0.4,
        ),
    }


# ===========================================================================
# Phase 6: benchmark_ticker
# ===========================================================================
class TestOrchestratorBenchmarkTicker:
    """Orchestrator benchmark_ticker parameter tests."""

    def test_正常系_benchmark_ticker設定時のリターン計算(
        self,
        config_dir: Path,
        workspace_dir: Path,
    ) -> None:
        """When benchmark_ticker is set, uses price_provider.fetch for benchmark."""
        # Create a stub price provider
        mock_provider = MagicMock()
        idx = pd.date_range("2016-01-04", periods=5, freq="B")
        mock_provider.fetch.return_value = {
            "AAPL": pd.Series([100.0, 101.0, 102.0, 103.0, 104.0], index=idx),
            "JPM": pd.Series([50.0, 50.5, 51.0, 51.5, 52.0], index=idx),
            "MXKOKUS": pd.Series([1000.0, 1010.0, 1020.0, 1030.0, 1040.0], index=idx),
        }

        orch = Orchestrator(
            config_path=config_dir,
            kb_base_dir=None,
            workspace_dir=workspace_dir,
            price_provider=mock_provider,
            benchmark_ticker="MXKOKUS",
        )

        portfolio = _make_portfolio_result()
        _portfolio_returns, benchmark_returns = orch._calculate_phase6_returns(
            portfolio
        )

        # benchmark_returns should be derived from MXKOKUS price data
        # not from equal-weight universe returns
        assert len(benchmark_returns) > 0
        # Verify price_provider.fetch was called with benchmark_ticker
        fetch_calls = mock_provider.fetch.call_args_list
        # Should have been called twice: once for portfolio, once for benchmark
        assert len(fetch_calls) == 2
        # Second call should include the benchmark ticker
        second_call = fetch_calls[1]
        # Extract tickers from positional or keyword args
        if second_call.kwargs and "tickers" in second_call.kwargs:
            second_call_tickers = second_call.kwargs["tickers"]
        else:
            second_call_tickers = second_call.args[0]
        assert "MXKOKUS" in second_call_tickers

    def test_正常系_benchmark_tickerがNoneの場合は従来方式(
        self,
        config_dir: Path,
        workspace_dir: Path,
    ) -> None:
        """When benchmark_ticker is None, uses equal-weight universe returns."""
        mock_provider = MagicMock()
        idx = pd.date_range("2016-01-04", periods=5, freq="B")
        mock_provider.fetch.return_value = {
            "AAPL": pd.Series([100.0, 101.0, 102.0, 103.0, 104.0], index=idx),
            "JPM": pd.Series([50.0, 50.5, 51.0, 51.5, 52.0], index=idx),
            "MSFT": pd.Series([80.0, 81.0, 82.0, 83.0, 84.0], index=idx),
        }

        orch = Orchestrator(
            config_path=config_dir,
            kb_base_dir=None,
            workspace_dir=workspace_dir,
            price_provider=mock_provider,
            benchmark_ticker=None,  # Default
        )

        portfolio = _make_portfolio_result()
        _portfolio_returns, _benchmark_returns = orch._calculate_phase6_returns(
            portfolio
        )

        # Should have called calculate_benchmark_returns via the old path
        # (which calls price_provider.fetch with universe tickers)
        assert mock_provider.fetch.called


# ===========================================================================
# Phase 6: analyst_scores_path
# ===========================================================================
class TestOrchestratorAnalystScoresPath:
    """Orchestrator analyst_scores_path parameter tests."""

    def test_正常系_analyst_scores_path設定時のスコア受け渡し(
        self,
        config_dir: Path,
        workspace_dir: Path,
        tmp_path: Path,
    ) -> None:
        """When analyst_scores_path is set, loads and passes scores to evaluator."""
        # Create analyst scores portfolio JSON
        portfolio_list_path = tmp_path / "portfolio_list.json"
        portfolio_data = {
            "001": [
                {
                    "Name": "Apple Inc.",
                    "Country": "US",
                    "GICS_Sector": "Information Technology",
                    "GICS_Industry": "Technology Hardware",
                    "MSCI_Mkt_Cap_USD_MM": 100000.0,
                    "KY": 2,
                    "AK": 3,
                    "Total": 5,
                    "Target_Weight": " ",
                    "LIST": "LIST",
                    "date": "2015-12-24T00:00:00.000",
                    "Bloomberg_Ticker": "AAPL US Equity",
                    "FIGI": "BBG000B9XRY4",
                }
            ],
        }
        portfolio_list_path.write_text(
            json.dumps(portfolio_data, ensure_ascii=False),
            encoding="utf-8",
        )

        orch = Orchestrator(
            config_path=config_dir,
            kb_base_dir=None,
            workspace_dir=workspace_dir,
            analyst_scores_path=portfolio_list_path,
        )

        portfolio = _make_portfolio_result()
        scores = _make_stock_scores()

        # Mock StrategyEvaluator to capture analyst_scores argument
        mock_evaluation = EvaluationResult(
            threshold=0.5,
            portfolio_size=2,
            performance=PerformanceMetrics(
                sharpe_ratio=0.0,
                max_drawdown=0.0,
                beta=0.0,
                information_ratio=0.0,
                cumulative_return=0.0,
            ),
            analyst_correlation=AnalystCorrelation(
                spearman_correlation=None,
                sample_size=0,
                p_value=None,
                hit_rate=None,
            ),
            transparency=TransparencyMetrics(
                mean_claim_count=0.0,
                mean_structural_weight=0.0,
                coverage_rate=0.0,
            ),
            as_of_date=date(2026, 2, 28),
        )

        with patch(
            "dev.ca_strategy.orchestrator.StrategyEvaluator"
        ) as mock_evaluator_cls:
            mock_evaluator = MagicMock()
            mock_evaluator.evaluate.return_value = mock_evaluation
            mock_evaluator_cls.return_value = mock_evaluator

            _result = orch._run_phase6_evaluation(portfolio, scores, 0.5)

            # Check that analyst_scores was passed (not empty dict)
            call_kwargs = mock_evaluator.evaluate.call_args
            analyst_scores_arg = call_kwargs[1].get(
                "analyst_scores", call_kwargs[0][4] if len(call_kwargs[0]) > 4 else {}
            )
            assert "AAPL" in analyst_scores_arg
            assert analyst_scores_arg["AAPL"].ky == 2
            assert analyst_scores_arg["AAPL"].ak == 3
