"""Shared pytest fixtures for the ca_strategy test suite.

Provides common test data used across unit and integration tests:
- ``sample_ranked_stocks``: 10 stocks across 3 sectors
- ``sample_benchmark_weights``: 3 sector weights summing to 1.0
- ``sample_portfolio_result``: valid PortfolioResult with 3 holdings
- ``sample_stock_scores``: StockScore map for 10 tickers
- ``sample_analyst_scores``: AnalystScore list for 10 tickers
- ``make_scored_claim_dict``: ScoredClaim 辞書表現を生成するヘルパー関数

All fixtures use ``np.random.seed(42)`` style reproducibility where
random data is generated.
"""

from __future__ import annotations

from datetime import date
from typing import Any

import numpy as np
import pytest

from dev.ca_strategy.portfolio_builder import RankedStock
from dev.ca_strategy.types import (
    AnalystScore,
    BenchmarkWeight,
    PortfolioHolding,
    PortfolioResult,
    SectorAllocation,
    StockScore,
)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
_AS_OF_DATE: date = date(2015, 9, 30)

# 10 stocks across 3 sectors
_TICKER_SECTOR_MAP: list[tuple[str, str, float, int]] = [
    # (ticker, sector, score, sector_rank)
    ("AAPL", "Information Technology", 0.90, 1),
    ("MSFT", "Information Technology", 0.80, 2),
    ("GOOGL", "Information Technology", 0.70, 3),
    ("NVDA", "Information Technology", 0.60, 4),
    ("JPM", "Financials", 0.85, 1),
    ("GS", "Financials", 0.72, 2),
    ("BAC", "Financials", 0.55, 3),
    ("JNJ", "Health Care", 0.88, 1),
    ("PFE", "Health Care", 0.65, 2),
    ("MRK", "Health Care", 0.50, 3),
]

# Benchmark weights for 3 sectors (sum = 1.0)
_SECTOR_WEIGHTS: list[tuple[str, float]] = [
    ("Information Technology", 0.40),
    ("Financials", 0.35),
    ("Health Care", 0.25),
]


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------
@pytest.fixture()
def sample_ranked_stocks() -> list[RankedStock]:
    """10 ranked stocks across 3 sectors for portfolio construction testing.

    Sectors:
    - Information Technology: AAPL (0.90), MSFT (0.80), GOOGL (0.70), NVDA (0.60)
    - Financials: JPM (0.85), GS (0.72), BAC (0.55)
    - Health Care: JNJ (0.88), PFE (0.65), MRK (0.50)

    Returns
    -------
    list[RankedStock]
        10 RankedStock entries with deterministic scores.
    """
    rng = np.random.default_rng(42)
    return [
        RankedStock(
            ticker=ticker,
            aggregate_score=score,
            gics_sector=sector,
            sector_rank=rank,
            claim_count=int(rng.integers(2, 8)),
            structural_weight=float(rng.uniform(0.4, 0.8)),
        )
        for ticker, sector, score, rank in _TICKER_SECTOR_MAP
    ]


@pytest.fixture()
def sample_benchmark_weights() -> list[BenchmarkWeight]:
    """3 sector benchmark weights summing to exactly 1.0.

    Returns
    -------
    list[BenchmarkWeight]
        [IT=0.40, Financials=0.35, Health Care=0.25]
    """
    return [
        BenchmarkWeight(sector=sector, weight=weight)
        for sector, weight in _SECTOR_WEIGHTS
    ]


@pytest.fixture()
def sample_portfolio_result() -> PortfolioResult:
    """Valid PortfolioResult with 3 holdings (one per sector).

    Holdings:
    - AAPL (IT, weight=0.40, score=0.90)
    - JPM (Financials, weight=0.35, score=0.85)
    - JNJ (Health Care, weight=0.25, score=0.88)

    Sector allocations match benchmark weights (IT=0.40, Fin=0.35, HC=0.25).

    Returns
    -------
    PortfolioResult
        Portfolio with 3 holdings, sector_allocations, and as_of_date.
    """
    holdings = [
        PortfolioHolding(
            ticker="AAPL",
            weight=0.40,
            sector="Information Technology",
            score=0.90,
            rationale_summary="Sector rank 1, score 0.90",
        ),
        PortfolioHolding(
            ticker="JPM",
            weight=0.35,
            sector="Financials",
            score=0.85,
            rationale_summary="Sector rank 1, score 0.85",
        ),
        PortfolioHolding(
            ticker="JNJ",
            weight=0.25,
            sector="Health Care",
            score=0.88,
            rationale_summary="Sector rank 1, score 0.88",
        ),
    ]
    sector_allocations = [
        SectorAllocation(
            sector="Information Technology",
            benchmark_weight=0.40,
            actual_weight=0.40,
            stock_count=1,
        ),
        SectorAllocation(
            sector="Financials",
            benchmark_weight=0.35,
            actual_weight=0.35,
            stock_count=1,
        ),
        SectorAllocation(
            sector="Health Care",
            benchmark_weight=0.25,
            actual_weight=0.25,
            stock_count=1,
        ),
    ]
    return PortfolioResult(
        holdings=holdings,
        sector_allocations=sector_allocations,
        as_of_date=_AS_OF_DATE,
    )


@pytest.fixture()
def sample_stock_scores() -> dict[str, StockScore]:
    """StockScore map for all 10 tickers.

    Returns
    -------
    dict[str, StockScore]
        Mapping of ticker -> StockScore for the 10 test tickers.
    """
    rng = np.random.default_rng(42)
    return {
        ticker: StockScore(
            ticker=ticker,
            aggregate_score=score,
            claim_count=int(rng.integers(2, 8)),
            structural_weight=float(rng.uniform(0.4, 0.8)),
        )
        for ticker, _sector, score, _rank in _TICKER_SECTOR_MAP
    }


@pytest.fixture()
def sample_analyst_scores() -> list[AnalystScore]:
    """AnalystScore list for all 10 tickers.

    KY and AK scores are integer ranks in [1, 10] generated with seed=42.

    Returns
    -------
    list[AnalystScore]
        10 AnalystScore entries with deterministic rank values.
    """
    rng = np.random.default_rng(42)
    return [
        AnalystScore(
            ticker=ticker,
            ky=int(rng.integers(1, 11)),
            ak=int(rng.integers(1, 11)),
        )
        for ticker, _sector, _score, _rank in _TICKER_SECTOR_MAP
    ]


# ---------------------------------------------------------------------------
# Shared helper functions (not fixtures)
# ---------------------------------------------------------------------------


def make_scored_claim_dict(
    claim_id: str,
    *,
    final_confidence: float = 0.7,
) -> dict[str, Any]:
    """ScoredClaim の辞書表現を生成するテストヘルパー。

    単体テストと統合テストの両方で使用される共通ファクトリ関数。

    Parameters
    ----------
    claim_id : str
        クレームのID（例: "AAPL-CA-001"）。
    final_confidence : float, default=0.7
        最終確信度スコア（0.0〜1.0）。

    Returns
    -------
    dict[str, Any]
        ScoredClaim.model_dump() 互換の辞書。

    Examples
    --------
    >>> claim = make_scored_claim_dict("AAPL-CA-001", final_confidence=0.8)
    >>> claim["id"]
    'AAPL-CA-001'
    >>> claim["final_confidence"]
    0.8
    """
    return {
        "id": claim_id,
        "claim_type": "competitive_advantage",
        "claim": f"Claim text for {claim_id}",
        "evidence": "Evidence for claim.",
        "rule_evaluation": {
            "applied_rules": ["rule_1_t"],
            "results": {"rule_1_t": True},
            "confidence": 0.7,
            "adjustments": [],
        },
        "final_confidence": final_confidence,
        "adjustments": [],
        "gatekeeper": None,
        "kb1_evaluations": [],
        "kb2_patterns": [],
        "overall_reasoning": "Good claim.",
    }
