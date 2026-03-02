"""Buy-and-Hold backtest for top-N portfolios (no sector neutralization).

Runs backtest on 6 portfolio variants:
- top30/60/90 x score-weighted / equal-weighted

Reuses Bloomberg data loading and metrics computation from
run_buyhold_backtest_bloomberg.py.

Usage:
    uv run python research/ca_strategy_poc/scripts/run_topn_backtest.py
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

# ---------------------------------------------------------------------------
# Path setup – add project root so 'research.ca_strategy_poc.scripts' is importable
# ---------------------------------------------------------------------------
ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))

from research.ca_strategy_poc.scripts import (  # noqa: E402
    run_buyhold_backtest_bloomberg as bt,
)

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
ROOT = Path(__file__).resolve().parents[3]
TOPN_DIR = (
    ROOT
    / "research"
    / "ca_strategy_poc"
    / "workspaces"
    / "full_run"
    / "output"
    / "topn"
)
RESULT_DIR = ROOT / "research" / "ca_strategy_poc" / "reports"

# ---------------------------------------------------------------------------
# Configuration (same as main backtest)
# ---------------------------------------------------------------------------
START_DATE = bt.START_DATE
END_DATE = bt.END_DATE
TRADING_DAYS_PER_YEAR = bt.TRADING_DAYS_PER_YEAR


def load_topn_weights(size: int, method: str) -> dict[str, float]:
    """Load top-N portfolio weights from CSV.

    Parameters
    ----------
    size : int
        Portfolio size (30, 60, 90).
    method : str
        "score_weighted" or "equal_weighted".
    """
    path = TOPN_DIR / f"top{size}_{method}.csv"
    df = pd.read_csv(path)
    return dict(zip(df["ticker"], df["weight"], strict=True))


def main() -> dict:
    """Run backtest for all top-N portfolio variants."""
    print("=" * 70)
    print("Top-N Portfolio Backtest (No Sector Neutralization, Bloomberg Data)")
    print("=" * 70)

    # ------------------------------------------------------------------
    # 1. Load shared data (same as main backtest)
    # ------------------------------------------------------------------
    bbg_prices = bt.load_bloomberg_prices()
    bbg_mcap = bt.load_bloomberg_mcap()

    short_to_bbg = bt.build_bbg_ticker_map()
    bbg_to_short = {v: k for k, v in short_to_bbg.items()}

    equity_cols = [c for c in bbg_prices.columns if "INDEX" not in c]
    available_cols = set(equity_cols)

    equity_prices = bbg_prices[equity_cols]
    all_returns = bt.compute_daily_returns(equity_prices)

    start_ts = pd.Timestamp(START_DATE)
    end_ts = pd.Timestamp(END_DATE)

    # MSCI Kokusai
    msci_prices = bbg_prices[[bt.MSCI_KOKUSAI_COL]].dropna()
    msci_returns = bt.compute_daily_returns(msci_prices)[bt.MSCI_KOKUSAI_COL]
    msci_returns = msci_returns[
        (msci_returns.index >= start_ts) & (msci_returns.index <= end_ts)
    ]
    print(f"\nMSCI Kokusai: {len(msci_returns)} days")

    # MSCI Kokusai EW
    msci_ew_prices = bbg_prices[[bt.MSCI_KOKUSAI_EW_COL]].dropna()
    msci_ew_returns = bt.compute_daily_returns(msci_ew_prices)[bt.MSCI_KOKUSAI_EW_COL]
    msci_ew_returns = msci_ew_returns[
        (msci_ew_returns.index >= start_ts) & (msci_ew_returns.index <= end_ts)
    ]

    # Align equity returns to MSCI trading days
    msci_trading_days = msci_returns.index
    all_returns = all_returns[
        (all_returns.index >= start_ts) & (all_returns.index <= end_ts)
    ]
    all_returns = all_returns.loc[all_returns.index.intersection(msci_trading_days)]
    print(
        f"Analysis period: {all_returns.index.min().date()} ~ {all_returns.index.max().date()}"
    )
    print(f"Trading days: {len(all_returns)}")

    # Risk-free rate
    daily_rf_series = bt.fetch_dgs10_daily_rf()

    # Corporate actions
    corporate_actions = bt.load_corporate_actions()

    # MCap benchmark
    print("\nBuilding MCap-weighted universe benchmark...")
    mcap_bench_returns = bt.compute_mcap_benchmark_returns(
        returns_df=all_returns,
        mcap_df=bbg_mcap,
        corporate_actions=corporate_actions,
        bbg_to_short=bbg_to_short,
    )

    # ------------------------------------------------------------------
    # 2. Also load sector-neutral portfolios for comparison
    # ------------------------------------------------------------------
    sn_results: dict = {}
    for size in [30, 60, 90]:
        sn_weights = bt.load_portfolio_weights(size)
        sn_mapped, _sn_missing = bt.map_portfolio_to_bbg(
            sn_weights, short_to_bbg, available_cols
        )
        sn_total = sum(sn_mapped.values())
        if sn_total > 0:
            sn_mapped = {k: v / sn_total for k, v in sn_mapped.items()}
        sn_returns, _ = bt.compute_buyhold_portfolio_returns(
            returns_df=all_returns,
            initial_weights=sn_mapped,
            corporate_actions=corporate_actions,
            bbg_to_short=bbg_to_short,
        )
        sn_results[size] = sn_returns

    # ------------------------------------------------------------------
    # 3. Run top-N backtests
    # ------------------------------------------------------------------
    all_results: dict = {
        "metadata": {
            "description": "Top-N portfolios ranked by aggregate_score (NO sector neutralization)",
            "data_source": "Bloomberg Terminal",
            "methodology": "Buy-and-Hold (drift weight)",
            "start_date": START_DATE.isoformat(),
            "end_date": END_DATE.isoformat(),
            "computed_at": pd.Timestamp.now().isoformat(),
        },
        "portfolios": {},
    }

    cum_data: dict = {}

    for size in [30, 60, 90]:
        for method in ["score_weighted", "equal_weighted"]:
            label = f"top{size}_{method}"
            print(f"\n{'─' * 60}")
            print(f"Processing: {label}")
            print(f"{'─' * 60}")

            # Load weights
            weights = load_topn_weights(size, method)
            mapped_weights, missing_tickers = bt.map_portfolio_to_bbg(
                weights, short_to_bbg, available_cols
            )

            print(f"  Original: {len(weights)} tickers")
            print(f"  Mapped: {len(mapped_weights)}")
            print(f"  Missing: {len(missing_tickers)} - {missing_tickers}")

            # Normalize
            mapped_total = sum(mapped_weights.values())
            if mapped_total > 0:
                mapped_weights = {
                    k: v / mapped_total for k, v in mapped_weights.items()
                }

            coverage_pct = len(mapped_weights) / len(weights) * 100

            # Buy-and-Hold returns
            port_returns, weight_history = bt.compute_buyhold_portfolio_returns(
                returns_df=all_returns,
                initial_weights=mapped_weights,
                corporate_actions=corporate_actions,
                bbg_to_short=bbg_to_short,
            )

            # Metrics vs MSCI Kokusai
            metrics_vs_msci = bt.compute_metrics(
                port_returns, msci_returns, daily_rf_series
            )

            # Metrics vs MCap benchmark
            metrics_vs_mcap = bt.compute_metrics(
                port_returns, mcap_bench_returns, daily_rf_series
            )

            # Metrics vs MSCI Kokusai EW
            metrics_vs_msci_ew = bt.compute_metrics(
                port_returns, msci_ew_returns, daily_rf_series
            )

            # Annual returns
            annual_vs_msci = bt.compute_annual_returns(port_returns, msci_returns)
            annual_vs_mcap = bt.compute_annual_returns(port_returns, mcap_bench_returns)

            # Weight drift
            drift_stats = bt.compute_weight_drift_stats(weight_history)

            # Sector breakdown (from mapped weights)
            sector_breakdown: dict[str, dict] = {}
            for bbg_ticker, w in mapped_weights.items():
                short = bbg_to_short.get(bbg_ticker, bbg_ticker.split()[0])
                # We don't have sector info in topn CSV, but we can get it from universe
                sector_breakdown.setdefault("_tickers", []).append(
                    {"ticker": short, "bbg": bbg_ticker, "weight": round(w, 6)}
                )

            all_results["portfolios"][label] = {
                "size": size,
                "method": method,
                "composition": {
                    "total_tickers": len(weights),
                    "data_available": len(mapped_weights),
                    "data_missing": len(missing_tickers),
                    "missing_tickers": sorted(missing_tickers),
                    "coverage_pct": round(coverage_pct, 1),
                },
                "vs_msci_kokusai": metrics_vs_msci,
                "vs_msci_kokusai_ew": metrics_vs_msci_ew,
                "vs_mcap_benchmark": metrics_vs_mcap,
                "annual_vs_msci": annual_vs_msci,
                "annual_vs_mcap": annual_vs_mcap,
                "weight_drift": drift_stats,
            }

            # Print summary
            print("\n  vs MSCI Kokusai:")
            print(
                f"    Ann Return:  {metrics_vs_msci['annualized_return']}% "
                f"(Bench: {metrics_vs_msci['benchmark_ann_return']}%)"
            )
            print(f"    Sharpe:      {metrics_vs_msci['sharpe_ratio']}")
            print(f"    Alpha:       {metrics_vs_msci['alpha_capm']}%")
            print(f"    Max DD:      {metrics_vs_msci['max_drawdown']}%")
            print(f"    IR:          {metrics_vs_msci['information_ratio']}")
            print(f"    Beta:        {metrics_vs_msci['beta']}")

            print("\n  vs MCap Benchmark:")
            print(
                f"    Ann Return:  {metrics_vs_mcap['annualized_return']}% "
                f"(Bench: {metrics_vs_mcap['benchmark_ann_return']}%)"
            )
            print(f"    Alpha:       {metrics_vs_mcap['alpha_capm']}%")
            print(f"    IR:          {metrics_vs_mcap['information_ratio']}")

            # Annual returns
            print("\n  Annual Returns vs MSCI Kokusai:")
            for yr in annual_vs_msci:
                sign = "+" if yr["active_return"] >= 0 else ""
                print(
                    f"    {yr['year']}: Port {yr['portfolio_return']:+.2f}% | "
                    f"Bench {yr['benchmark_return']:+.2f}% | "
                    f"Active {sign}{yr['active_return']:.2f}%"
                )

            # Cumulative returns for plotting
            common = port_returns.index.intersection(msci_returns.index)
            common = common.intersection(mcap_bench_returns.index)
            cum_data[label] = {
                "dates": [d.isoformat() for d in common],
                "portfolio": ((1 + port_returns.loc[common]).cumprod()).tolist(),
                "msci_kokusai": ((1 + msci_returns.loc[common]).cumprod()).tolist(),
                "mcap_universe": (
                    (1 + mcap_bench_returns.loc[common]).cumprod()
                ).tolist(),
            }

    # ------------------------------------------------------------------
    # 4. Comparison summary: top-N vs sector-neutral
    # ------------------------------------------------------------------
    print("\n" + "=" * 70)
    print("COMPARISON: Top-N vs Sector-Neutral Portfolios")
    print("=" * 70)

    comparison_rows = []
    for size in [30, 60, 90]:
        # Sector-neutral metrics
        sn_metrics = bt.compute_metrics(sn_results[size], msci_returns, daily_rf_series)

        for method in ["score_weighted", "equal_weighted"]:
            label = f"top{size}_{method}"
            tn_metrics = all_results["portfolios"][label]["vs_msci_kokusai"]

            method_short = "ScoreW" if method == "score_weighted" else "EqualW"
            comparison_rows.append(
                {
                    "portfolio": f"Top-{size} {method_short}",
                    "ann_return": tn_metrics["annualized_return"],
                    "sharpe": tn_metrics["sharpe_ratio"],
                    "alpha": tn_metrics["alpha_capm"],
                    "max_dd": tn_metrics["max_drawdown"],
                    "ir": tn_metrics["information_ratio"],
                    "beta": tn_metrics["beta"],
                }
            )

        comparison_rows.append(
            {
                "portfolio": f"SectorNeutral-{size}",
                "ann_return": sn_metrics["annualized_return"],
                "sharpe": sn_metrics["sharpe_ratio"],
                "alpha": sn_metrics["alpha_capm"],
                "max_dd": sn_metrics["max_drawdown"],
                "ir": sn_metrics["information_ratio"],
                "beta": sn_metrics["beta"],
            }
        )

    # Store comparison in results
    all_results["comparison_vs_sector_neutral"] = comparison_rows

    # Print comparison table
    header = f"{'Portfolio':<25s} {'AnnRet%':>8s} {'Sharpe':>7s} {'Alpha%':>7s} {'MaxDD%':>7s} {'IR':>7s} {'Beta':>6s}"
    print(header)
    print("─" * len(header))
    for row in comparison_rows:
        print(
            f"{row['portfolio']:<25s} "
            f"{row['ann_return']:>8.2f} "
            f"{row['sharpe']:>7.3f} "
            f"{row['alpha']:>7.2f} "
            f"{row['max_dd']:>7.2f} "
            f"{row['ir']:>7.3f} "
            f"{row['beta']:>6.3f}"
        )
        # Blank line between size groups
        if "SectorNeutral" in row["portfolio"]:
            print()

    # ------------------------------------------------------------------
    # 5. Save results
    # ------------------------------------------------------------------
    RESULT_DIR.mkdir(parents=True, exist_ok=True)

    result_path = RESULT_DIR / "topn_backtest_results.json"
    result_path.write_text(json.dumps(all_results, indent=2, ensure_ascii=False))
    print(f"\nResults saved to: {result_path}")

    cum_path = RESULT_DIR / "topn_cumulative_returns.json"
    cum_path.write_text(json.dumps(cum_data, ensure_ascii=False))
    print(f"Cumulative returns saved to: {cum_path}")

    return all_results


if __name__ == "__main__":
    results = main()
