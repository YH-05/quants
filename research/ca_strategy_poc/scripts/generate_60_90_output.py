"""Generate OutputGenerator output for 60/90-stock portfolios.

Loads Phase 2 checkpoint (scored_claims), runs Phase 3 (aggregation +
neutralization) and Phase 4 (portfolio construction) for target_size=60
and target_size=90, then runs Phase 5 (OutputGenerator.generate_all)
to produce rationale files and consistent CSV output.

Usage:
    uv run python research/ca_strategy_poc/scripts/generate_60_90_output.py
"""

from __future__ import annotations

import json
import sys
from datetime import date
from pathlib import Path
from typing import cast

import pandas as pd

# ---------------------------------------------------------------------------
# Path setup
# ---------------------------------------------------------------------------
ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "src"))

from dev.ca_strategy.aggregator import ScoreAggregator  # noqa: E402
from dev.ca_strategy.neutralizer import SectorNeutralizer  # noqa: E402
from dev.ca_strategy.output import OutputGenerator  # noqa: E402
from dev.ca_strategy.pit import CUTOFF_DATE, PORTFOLIO_DATE  # noqa: E402
from dev.ca_strategy.portfolio_builder import (  # noqa: E402
    PortfolioBuilder,
    RankedStock,
)
from dev.ca_strategy.types import (  # noqa: E402
    BenchmarkWeight,
    ScoredClaim,
    StockScore,
    UniverseConfig,
)

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
WORKSPACE = ROOT / "research" / "ca_strategy_poc" / "workspaces" / "full_run"
CONFIG_DIR = ROOT / "research" / "ca_strategy_poc" / "config"
CHECKPOINT_DIR = WORKSPACE / "checkpoints"
OUTPUT_BASE = WORKSPACE / "output"


def load_scored_claims() -> dict[str, list[ScoredClaim]]:
    """Load Phase 2 scored claims from checkpoint."""
    path = CHECKPOINT_DIR / "phase2_scored.json"
    data = json.loads(path.read_text(encoding="utf-8"))
    return {
        ticker: [ScoredClaim.model_validate(c) for c in items]
        for ticker, items in data.items()
    }


def load_benchmark_weights() -> list[BenchmarkWeight]:
    """Load benchmark sector weights from config."""
    path = CONFIG_DIR / "benchmark_weights.json"
    data = json.loads(path.read_text(encoding="utf-8"))
    return [
        BenchmarkWeight(sector=sector, weight=weight)
        for sector, weight in data["weights"].items()
    ]


def load_universe() -> UniverseConfig:
    """Load universe config."""
    path = CONFIG_DIR / "universe.json"
    data = json.loads(path.read_text(encoding="utf-8"))
    return UniverseConfig.model_validate(data)


def run_phase3(
    scored_claims: dict[str, list[ScoredClaim]],
    scores: dict[str, StockScore],
    universe: UniverseConfig,
) -> pd.DataFrame:
    """Run Phase 3: aggregation + sector neutralization."""
    scores_data = [
        {
            "ticker": ticker,
            "aggregate_score": score.aggregate_score,
            "claim_count": score.claim_count,
            "structural_weight": score.structural_weight,
            "as_of_date": CUTOFF_DATE,
        }
        for ticker, score in scores.items()
    ]
    scores_df = pd.DataFrame(scores_data)
    neutralizer = SectorNeutralizer(min_samples=2)
    return neutralizer.neutralize(scores_df, universe)


def run_phase4(
    ranked: pd.DataFrame,
    benchmark: list[BenchmarkWeight],
    target_size: int,
) -> "PortfolioResult":
    """Run Phase 4: portfolio construction for given target_size."""
    builder = PortfolioBuilder(target_size=target_size)
    ranked_list = cast("list[RankedStock]", ranked.to_dict("records"))
    return builder.build(
        ranked=ranked_list,
        benchmark=benchmark,
        as_of_date=PORTFOLIO_DATE,
    )


def run_phase5(
    portfolio: "PortfolioResult",
    scored_claims: dict[str, list[ScoredClaim]],
    scores: dict[str, StockScore],
    output_dir: Path,
) -> None:
    """Run Phase 5: output generation."""
    generator = OutputGenerator()
    generator.generate_all(
        portfolio=portfolio,
        claims=scored_claims,
        scores=scores,
        output_dir=output_dir,
    )


def main() -> None:
    """Generate output for 60 and 90 stock portfolios."""
    print("=" * 60)
    print("Generating 60/90-stock portfolio output via OutputGenerator")
    print("=" * 60)

    # Load shared data
    print("\nLoading scored claims from checkpoint...")
    scored_claims = load_scored_claims()
    print(f"  Tickers: {len(scored_claims)}")
    print(f"  Total claims: {sum(len(v) for v in scored_claims.values())}")

    print("Loading benchmark weights...")
    benchmark = load_benchmark_weights()
    print(f"  Sectors: {len(benchmark)}")

    print("Loading universe...")
    universe = load_universe()
    print(f"  Tickers: {len(universe.tickers)}")

    # Aggregate scores (Phase 2 → StockScore)
    print("\nAggregating scores...")
    aggregator = ScoreAggregator()
    scores = aggregator.aggregate(scored_claims)
    print(f"  Scored tickers: {len(scores)}")

    # Run Phase 3 (shared for both sizes)
    print("Running Phase 3 (neutralization)...")
    ranked = run_phase3(scored_claims, scores, universe)
    print(f"  Ranked tickers: {len(ranked)}")

    # Process each target size
    for target_size in [60, 90]:
        print(f"\n{'─' * 50}")
        print(f"Processing {target_size}-stock portfolio")
        print(f"{'─' * 50}")

        # Phase 4
        portfolio = run_phase4(ranked, benchmark, target_size)
        print(f"  Holdings: {len(portfolio.holdings)}")
        print(f"  Sectors: {len(portfolio.sector_allocations)}")

        # Phase 5
        suffix = f"_{target_size}"
        output_dir = OUTPUT_BASE / f"size{suffix}"
        print(f"  Output dir: {output_dir}")

        run_phase5(portfolio, scored_claims, scores, output_dir)

        # Count generated files
        rationale_dir = output_dir / "rationale"
        if rationale_dir.exists():
            rationale_count = len(list(rationale_dir.glob("*_rationale.md")))
        else:
            rationale_count = 0

        print(f"  Rationale files: {rationale_count}")
        print(
            f"  portfolio_weights.csv: {(output_dir / 'portfolio_weights.csv').exists()}"
        )
        print(
            f"  portfolio_weights.json: {(output_dir / 'portfolio_weights.json').exists()}"
        )
        print(
            f"  portfolio_summary.md: {(output_dir / 'portfolio_summary.md').exists()}"
        )

    print("\n" + "=" * 60)
    print("Done!")
    print("=" * 60)


if __name__ == "__main__":
    main()
