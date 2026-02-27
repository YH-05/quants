"""Generate top-N portfolios ranked purely by aggregate_score (no sector neutralization).

Creates 6 portfolio CSV files:
- top30_score_weighted.csv  (score-proportional weights)
- top30_equal_weighted.csv  (1/N weights)
- top60_score_weighted.csv
- top60_equal_weighted.csv
- top90_score_weighted.csv
- top90_equal_weighted.csv

Usage:
    uv run python research/ca_strategy_poc/scripts/generate_topn_portfolios.py
"""

from __future__ import annotations

import csv
import json
import sys
from pathlib import Path

# ---------------------------------------------------------------------------
# Path setup
# ---------------------------------------------------------------------------
ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "src"))

from dev.ca_strategy.aggregator import ScoreAggregator  # noqa: E402
from dev.ca_strategy.types import ScoredClaim  # noqa: E402

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
CHECKPOINT_DIR = (
    ROOT / "research" / "ca_strategy_poc" / "workspaces" / "full_run" / "checkpoints"
)
OUTPUT_DIR = (
    ROOT
    / "research"
    / "ca_strategy_poc"
    / "workspaces"
    / "full_run"
    / "output"
    / "topn"
)


def load_scored_claims() -> dict[str, list[ScoredClaim]]:
    """Load Phase 2 scored claims from checkpoint."""
    path = CHECKPOINT_DIR / "phase2_scored.json"
    data = json.loads(path.read_text(encoding="utf-8"))
    return {
        ticker: [ScoredClaim.model_validate(c) for c in items]
        for ticker, items in data.items()
    }


def main() -> None:
    """Generate top-N portfolio weight CSVs."""
    print("=" * 60)
    print("Generating Top-N Portfolios (No Sector Neutralization)")
    print("=" * 60)

    # 1. Load and aggregate scores
    print("\nLoading scored claims...")
    scored_claims = load_scored_claims()
    print(f"  Tickers with claims: {len(scored_claims)}")

    aggregator = ScoreAggregator()
    scores = aggregator.aggregate(scored_claims)
    print(f"  Aggregated scores: {len(scores)}")

    # 2. Rank by aggregate_score descending
    ranked = sorted(
        scores.items(),
        key=lambda x: x[1].aggregate_score,
        reverse=True,
    )

    print("\n  Top 10 by score:")
    for i, (ticker, score) in enumerate(ranked[:10]):
        print(
            f"    {i + 1:3d}. {ticker:8s}  score={score.aggregate_score:.4f}  "
            f"claims={score.claim_count}  structural={score.structural_weight:.2f}"
        )

    print("\n  Bottom 5 by score:")
    for i, (ticker, score) in enumerate(ranked[-5:]):
        print(
            f"    {len(ranked) - 4 + i:3d}. {ticker:8s}  score={score.aggregate_score:.4f}  "
            f"claims={score.claim_count}"
        )

    # 3. Generate portfolios
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    for size in [30, 60, 90]:
        top_n = ranked[:size]

        # --- Score-weighted ---
        total_score = sum(s.aggregate_score for _, s in top_n)
        score_rows = []
        for ticker, score in top_n:
            weight = (
                score.aggregate_score / total_score if total_score > 0 else 1.0 / size
            )
            score_rows.append(
                {
                    "ticker": ticker,
                    "weight": weight,
                    "score": score.aggregate_score,
                    "claim_count": score.claim_count,
                    "structural_weight": score.structural_weight,
                }
            )

        sw_path = OUTPUT_DIR / f"top{size}_score_weighted.csv"
        with open(sw_path, "w", newline="") as f:
            writer = csv.DictWriter(
                f,
                fieldnames=[
                    "ticker",
                    "weight",
                    "score",
                    "claim_count",
                    "structural_weight",
                ],
            )
            writer.writeheader()
            writer.writerows(score_rows)

        # --- Equal-weighted ---
        ew_rows = []
        equal_weight = 1.0 / size
        for ticker, score in top_n:
            ew_rows.append(
                {
                    "ticker": ticker,
                    "weight": equal_weight,
                    "score": score.aggregate_score,
                    "claim_count": score.claim_count,
                    "structural_weight": score.structural_weight,
                }
            )

        ew_path = OUTPUT_DIR / f"top{size}_equal_weighted.csv"
        with open(ew_path, "w", newline="") as f:
            writer = csv.DictWriter(
                f,
                fieldnames=[
                    "ticker",
                    "weight",
                    "score",
                    "claim_count",
                    "structural_weight",
                ],
            )
            writer.writeheader()
            writer.writerows(ew_rows)

        # Summary
        sw_top_weight = max(r["weight"] for r in score_rows)
        sw_bottom_weight = min(r["weight"] for r in score_rows)
        min_score = top_n[-1][1].aggregate_score
        max_score = top_n[0][1].aggregate_score

        print(f"\n{'─' * 50}")
        print(f"Top-{size} Portfolio")
        print(f"{'─' * 50}")
        print(f"  Score range: {min_score:.4f} ~ {max_score:.4f}")
        print(
            f"  Score-weighted: max_w={sw_top_weight:.4f}, min_w={sw_bottom_weight:.4f}"
        )
        print(f"  Equal-weighted: w={equal_weight:.4f}")
        print(f"  Files: {sw_path.name}, {ew_path.name}")

    print(f"\nAll files saved to: {OUTPUT_DIR}")


if __name__ == "__main__":
    main()
