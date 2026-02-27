"""Compare list portfolio (investment universe) vs MSCI Kokusai.

Computes full risk/return metrics for:
1. MCap-weighted universe (296 tickers) vs MSCI Kokusai
2. Equal-weight universe vs MSCI Kokusai
3. MCap-weighted universe vs MSCI Kokusai EW

Also computes annual returns breakdown.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

# Add parent to path so we can import from the backtest script
sys.path.insert(0, str(Path(__file__).parent))

import numpy as np
import pandas as pd
from run_buyhold_backtest_bloomberg import (
    END_DATE,
    MSCI_KOKUSAI_COL,
    MSCI_KOKUSAI_EW_COL,
    START_DATE,
    TRADING_DAYS_PER_YEAR,
    build_bbg_ticker_map,
    compute_annual_returns,
    compute_buyhold_portfolio_returns,
    compute_daily_returns,
    compute_mcap_benchmark_returns,
    compute_metrics,
    fetch_dgs10_daily_rf,
    load_bloomberg_mcap,
    load_bloomberg_prices,
    load_corporate_actions,
)

ROOT = Path(__file__).resolve().parents[3]
RESULT_DIR = ROOT / "research" / "ca_strategy_poc" / "reports"


def main() -> None:
    print("=" * 70)
    print("List Portfolio (Universe) vs MSCI Kokusai Comparison")
    print("=" * 70)

    # 1. Load data
    bbg_prices = load_bloomberg_prices()
    bbg_mcap = load_bloomberg_mcap()
    short_to_bbg = build_bbg_ticker_map()
    bbg_to_short = {v: k for k, v in short_to_bbg.items()}

    equity_cols = [c for c in bbg_prices.columns if "INDEX" not in c]
    available_cols = set(equity_cols)

    all_returns = compute_daily_returns(bbg_prices[equity_cols])

    start_ts = pd.Timestamp(START_DATE)
    end_ts = pd.Timestamp(END_DATE)

    # 2. MSCI Kokusai
    msci_prices = bbg_prices[[MSCI_KOKUSAI_COL]].dropna()
    msci_returns = compute_daily_returns(msci_prices)[MSCI_KOKUSAI_COL]
    msci_returns = msci_returns[
        (msci_returns.index >= start_ts) & (msci_returns.index <= end_ts)
    ]

    # MSCI Kokusai EW
    msci_ew_prices = bbg_prices[[MSCI_KOKUSAI_EW_COL]].dropna()
    msci_ew_returns = compute_daily_returns(msci_ew_prices)[MSCI_KOKUSAI_EW_COL]
    msci_ew_returns = msci_ew_returns[
        (msci_ew_returns.index >= start_ts) & (msci_ew_returns.index <= end_ts)
    ]

    # Align equity returns to MSCI trading days
    msci_trading_days = msci_returns.index
    all_returns = all_returns[
        (all_returns.index >= start_ts) & (all_returns.index <= end_ts)
    ]
    all_returns = all_returns.loc[all_returns.index.intersection(msci_trading_days)]
    print(f"\nTrading days (aligned to MSCI): {len(all_returns)}")

    # Risk-free rate
    daily_rf_series = fetch_dgs10_daily_rf()

    # Corporate actions
    corporate_actions = load_corporate_actions()

    # 3. Build universe benchmarks
    print("\n--- MCap-weighted Universe Benchmark ---")
    mcap_bench_returns = compute_mcap_benchmark_returns(
        returns_df=all_returns,
        mcap_df=bbg_mcap,
        corporate_actions=corporate_actions,
        bbg_to_short=bbg_to_short,
    )

    print("\n--- Equal-weight Universe Benchmark ---")
    valid_cols = [c for c in all_returns.columns if all_returns[c].notna().sum() > 100]
    ew_weights = {c: 1.0 / len(valid_cols) for c in valid_cols}
    ew_bench_returns, _ = compute_buyhold_portfolio_returns(
        returns_df=all_returns,
        initial_weights=ew_weights,
        corporate_actions=corporate_actions,
        bbg_to_short=bbg_to_short,
    )
    print(f"  Equal-weight tickers: {len(valid_cols)}")

    # 4. Compute metrics
    print("\n" + "=" * 70)
    print("RESULTS")
    print("=" * 70)

    results = {}

    # --- MCap Universe vs MSCI Kokusai ---
    m1 = compute_metrics(mcap_bench_returns, msci_returns, daily_rf_series)
    a1 = compute_annual_returns(mcap_bench_returns, msci_returns)
    results["mcap_universe_vs_msci_kokusai"] = {"metrics": m1, "annual": a1}

    print("\n[1] MCap-weighted Universe vs MSCI Kokusai")
    print(
        f"    Universe: {m1['annualized_return']:.2f}%  |  MSCI: {m1['benchmark_ann_return']:.2f}%"
    )
    print(
        f"    Active Return: {m1['annualized_return'] - m1['benchmark_ann_return']:+.2f}%"
    )
    print(f"    Alpha (CAPM): {m1['alpha_capm']:+.2f}%  |  Beta: {m1['beta']:.3f}")
    print(f"    Sharpe: {m1['sharpe_ratio']:.3f}  |  IR: {m1['information_ratio']:.3f}")
    print(f"    Tracking Error: {m1['tracking_error']:.2f}%")
    print(f"    Max DD: {m1['max_drawdown']:.2f}%")
    print(
        f"    Up Capture: {m1['up_capture']:.1f}%  |  Down Capture: {m1['down_capture']:.1f}%"
    )
    print(f"    Volatility: {m1['volatility']:.2f}%")

    # --- EW Universe vs MSCI Kokusai ---
    m2 = compute_metrics(ew_bench_returns, msci_returns, daily_rf_series)
    a2 = compute_annual_returns(ew_bench_returns, msci_returns)
    results["ew_universe_vs_msci_kokusai"] = {"metrics": m2, "annual": a2}

    print("\n[2] Equal-weight Universe vs MSCI Kokusai")
    print(
        f"    Universe: {m2['annualized_return']:.2f}%  |  MSCI: {m2['benchmark_ann_return']:.2f}%"
    )
    print(
        f"    Active Return: {m2['annualized_return'] - m2['benchmark_ann_return']:+.2f}%"
    )
    print(f"    Alpha (CAPM): {m2['alpha_capm']:+.2f}%  |  Beta: {m2['beta']:.3f}")
    print(f"    Sharpe: {m2['sharpe_ratio']:.3f}  |  IR: {m2['information_ratio']:.3f}")
    print(f"    Tracking Error: {m2['tracking_error']:.2f}%")
    print(f"    Max DD: {m2['max_drawdown']:.2f}%")
    print(
        f"    Up Capture: {m2['up_capture']:.1f}%  |  Down Capture: {m2['down_capture']:.1f}%"
    )
    print(f"    Volatility: {m2['volatility']:.2f}%")

    # --- MCap Universe vs MSCI Kokusai EW ---
    m3 = compute_metrics(mcap_bench_returns, msci_ew_returns, daily_rf_series)
    a3 = compute_annual_returns(mcap_bench_returns, msci_ew_returns)
    results["mcap_universe_vs_msci_kokusai_ew"] = {"metrics": m3, "annual": a3}

    print("\n[3] MCap-weighted Universe vs MSCI Kokusai EW")
    print(
        f"    Universe: {m3['annualized_return']:.2f}%  |  MSCI EW: {m3['benchmark_ann_return']:.2f}%"
    )
    print(
        f"    Active Return: {m3['annualized_return'] - m3['benchmark_ann_return']:+.2f}%"
    )
    print(f"    Alpha (CAPM): {m3['alpha_capm']:+.2f}%  |  Beta: {m3['beta']:.3f}")

    # --- EW Universe vs MSCI Kokusai EW ---
    m4 = compute_metrics(ew_bench_returns, msci_ew_returns, daily_rf_series)
    a4 = compute_annual_returns(ew_bench_returns, msci_ew_returns)
    results["ew_universe_vs_msci_kokusai_ew"] = {"metrics": m4, "annual": a4}

    print("\n[4] Equal-weight Universe vs MSCI Kokusai EW")
    print(
        f"    Universe: {m4['annualized_return']:.2f}%  |  MSCI EW: {m4['benchmark_ann_return']:.2f}%"
    )
    print(
        f"    Active Return: {m4['annualized_return'] - m4['benchmark_ann_return']:+.2f}%"
    )
    print(f"    Alpha (CAPM): {m4['alpha_capm']:+.2f}%  |  Beta: {m4['beta']:.3f}")

    # --- MSCI Kokusai standalone metrics ---
    # Compute MSCI Kokusai's own risk metrics (vs risk-free)
    msci_cum = (1 + msci_returns).prod() - 1
    msci_ann = (1 + msci_cum) ** (1 / (len(msci_returns) / TRADING_DAYS_PER_YEAR)) - 1
    msci_vol = msci_returns.std() * np.sqrt(TRADING_DAYS_PER_YEAR)

    cum_wealth = (1 + msci_returns).cumprod()
    running_max = cum_wealth.cummax()
    drawdown = (cum_wealth - running_max) / running_max
    msci_max_dd = drawdown.min()

    if len(daily_rf_series) > 0:
        rf_aligned = daily_rf_series.reindex(msci_returns.index).ffill().bfill()
        excess = msci_returns - rf_aligned
        ann_rf = float(
            (1 + rf_aligned).prod() ** (TRADING_DAYS_PER_YEAR / len(rf_aligned)) - 1
        )
    else:
        ann_rf = 0.045
        daily_rf_val = (1 + ann_rf) ** (1 / TRADING_DAYS_PER_YEAR) - 1
        excess = msci_returns - daily_rf_val

    msci_sharpe = (
        (excess.mean() / excess.std()) * np.sqrt(TRADING_DAYS_PER_YEAR)
        if excess.std() > 0
        else 0.0
    )

    downside = excess[excess < 0]
    downside_std = (
        np.sqrt((downside**2).mean()) * np.sqrt(TRADING_DAYS_PER_YEAR)
        if len(downside) > 0
        else 0.0
    )
    msci_sortino = (msci_ann - ann_rf) / downside_std if downside_std > 0 else 0.0
    msci_calmar = msci_ann / abs(msci_max_dd) if abs(msci_max_dd) > 0 else 0.0

    results["msci_kokusai_standalone"] = {
        "annualized_return": round(msci_ann * 100, 2),
        "cumulative_return": round(msci_cum * 100, 2),
        "volatility": round(msci_vol * 100, 2),
        "sharpe_ratio": round(msci_sharpe, 3),
        "sortino_ratio": round(msci_sortino, 3),
        "max_drawdown": round(msci_max_dd * 100, 2),
        "calmar_ratio": round(msci_calmar, 3),
        "n_days": len(msci_returns),
    }

    print("\n[Ref] MSCI Kokusai Standalone")
    print(f"    Ann Return: {msci_ann * 100:.2f}%  |  Cum: {msci_cum * 100:.2f}%")
    print(f"    Vol: {msci_vol * 100:.2f}%  |  Sharpe: {msci_sharpe:.3f}")
    print(f"    Max DD: {msci_max_dd * 100:.2f}%  |  Calmar: {msci_calmar:.3f}")

    # --- Annual returns table ---
    print("\n" + "=" * 70)
    print("Annual Returns: Universe vs MSCI Kokusai")
    print("=" * 70)
    print(
        f"{'Year':>6} | {'MCap Univ':>10} | {'EW Univ':>10} | {'MSCI':>10} | {'MCap Active':>12} | {'EW Active':>12}"
    )
    print("-" * 70)
    for row_m, row_e in zip(a1, a2, strict=False):
        y = row_m["year"]
        print(
            f"{y:>6} | {row_m['portfolio_return']:>9.2f}% | {row_e['portfolio_return']:>9.2f}% | "
            f"{row_m['benchmark_return']:>9.2f}% | {row_m['active_return']:>+11.2f}% | {row_e['active_return']:>+11.2f}%"
        )

    # Save results
    out_path = RESULT_DIR / "universe_vs_msci_comparison.json"
    with open(out_path, "w") as f:
        json.dump(results, f, indent=2, default=str)
    print(f"\nResults saved to: {out_path}")


if __name__ == "__main__":
    main()
