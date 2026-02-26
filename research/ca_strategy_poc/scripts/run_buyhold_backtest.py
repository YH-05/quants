"""Full Buy-and-Hold backtest for CA Strategy portfolios.

Computes performance metrics for 30/60/90-stock portfolios using
Buy-and-Hold (drift weight) methodology. Compares against:
- MSCI Kokusai (TOK ETF)
- MCap-weighted universe benchmark (initial MCap + drift)

Risk-free rate: FRED DGS10 (US 10-Year Treasury yield, daily).

Outputs results to JSON for report and notebook generation.
"""

from __future__ import annotations

import json
import sys
from datetime import date
from pathlib import Path

import numpy as np
import pandas as pd

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
ROOT = Path(__file__).resolve().parents[3]
DATA_DIR = ROOT / "data" / "raw" / "yfinance" / "stocks"
CONFIG_DIR = ROOT / "research" / "ca_strategy_poc" / "config"
OUTPUT_DIR = ROOT / "research" / "ca_strategy_poc" / "workspaces" / "full_run" / "output"
RESULT_DIR = ROOT / "research" / "ca_strategy_poc" / "reports"
FRED_CACHE_DIR = ROOT / "data" / "raw" / "fred"

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
RISK_FREE_RATE_FALLBACK = 0.045  # annual fallback if FRED unavailable
RETURN_CAP = 0.50  # daily ±50%
START_DATE = date(2016, 1, 4)
END_DATE = date(2026, 2, 25)
TRADING_DAYS_PER_YEAR = 252


def fetch_dgs10_daily_rf() -> pd.Series:
    """Fetch FRED DGS10 (10-Year Treasury yield) and convert to daily rate.

    Returns a pd.Series with DatetimeIndex, values = daily risk-free rate.
    DGS10 is in annualized %, so we convert: (1 + yield/100)^(1/252) - 1.
    Missing values (weekends/holidays) are forward-filled.

    Falls back to flat RISK_FREE_RATE_FALLBACK if FRED API is unavailable.
    """
    cache_path = FRED_CACHE_DIR / "dgs10_daily.parquet"

    # Try cached file first
    if cache_path.exists():
        dgs10 = pd.read_parquet(cache_path)
        if isinstance(dgs10, pd.DataFrame):
            dgs10 = dgs10.iloc[:, 0]
        dgs10.index = pd.DatetimeIndex(dgs10.index)
        print(f"DGS10 loaded from cache: {len(dgs10)} observations")
        daily_rf = ((1 + dgs10 / 100) ** (1 / TRADING_DAYS_PER_YEAR) - 1).ffill()
        return daily_rf

    # Fetch from FRED API
    try:
        from fredapi import Fred

        from utils_core.settings import load_project_env

        load_project_env()
        import os

        api_key = os.environ.get("FRED_API_KEY")
        if not api_key:
            print("WARNING: FRED_API_KEY not set, using fallback risk-free rate")
            return pd.Series(dtype=float)

        fred = Fred(api_key=api_key)
        dgs10 = fred.get_series(
            "DGS10",
            observation_start="2015-12-01",
            observation_end="2026-03-01",
        )
        dgs10 = dgs10.dropna()
        dgs10.name = "DGS10"
        print(f"DGS10 fetched from FRED: {len(dgs10)} observations")
        print(f"  Period: {dgs10.index.min().date()} ~ {dgs10.index.max().date()}")
        print(f"  Range: {dgs10.min():.2f}% ~ {dgs10.max():.2f}%")
        print(f"  Mean: {dgs10.mean():.2f}%")

        # Cache for future use
        cache_path.parent.mkdir(parents=True, exist_ok=True)
        dgs10.to_frame().to_parquet(cache_path)
        print(f"  Cached to: {cache_path}")

        # Convert annual % to daily rate
        daily_rf = ((1 + dgs10 / 100) ** (1 / TRADING_DAYS_PER_YEAR) - 1).ffill()
        return daily_rf

    except Exception as e:
        print(f"WARNING: Failed to fetch DGS10 from FRED: {e}")
        print(f"  Using fallback risk-free rate: {RISK_FREE_RATE_FALLBACK:.1%}")
        return pd.Series(dtype=float)


def load_portfolio_weights(size: int) -> dict[str, float]:
    """Load portfolio weights from CSV."""
    suffix = "" if size == 30 else f"_{size}"
    path = OUTPUT_DIR / f"portfolio_weights{suffix}.csv"
    df = pd.read_csv(path)
    return dict(zip(df["ticker"], df["weight"]))


def load_corporate_actions() -> list[dict]:
    """Load corporate actions from config."""
    path = CONFIG_DIR / "corporate_actions.json"
    data = json.loads(path.read_text())
    return data["corporate_actions"]


def load_universe_mcap_weights() -> dict[str, float]:
    """Load MCap weights from universe JSON."""
    path = ROOT / "data" / "Transcript" / "list_portfolio_20151224.json"
    data = json.loads(path.read_text())

    mcap: dict[str, float] = {}
    for _id, entries in data.items():
        entry = entries[0]
        ticker_raw = entry.get("Bloomberg_Ticker", "")
        mcap_val = entry.get("MSCI_Mkt_Cap_USD_MM", 0)
        if not ticker_raw or not mcap_val:
            continue

        # Extract short ticker from Bloomberg format
        parts = ticker_raw.split()
        if parts:
            short_ticker = parts[0]
            mcap[short_ticker] = float(mcap_val)

    # Normalize to weights
    total = sum(mcap.values())
    return {t: v / total for t, v in mcap.items()} if total > 0 else {}


def load_price_data(size: int) -> pd.DataFrame:
    """Load portfolio price data."""
    suffix = "" if size == 30 else f"_{size}"
    path = DATA_DIR / f"ca_portfolio{suffix}_close_prices.parquet"
    df = pd.read_parquet(path)
    if not isinstance(df.index, pd.DatetimeIndex):
        df.index = pd.DatetimeIndex(df.index)
    return df


def load_universe_prices() -> pd.DataFrame:
    """Load universe benchmark prices."""
    path = DATA_DIR / "universe_benchmark_close_prices.parquet"
    df = pd.read_parquet(path)
    if not isinstance(df.index, pd.DatetimeIndex):
        df.index = pd.DatetimeIndex(df.index)
    return df


def load_msci_prices() -> pd.DataFrame:
    """Load MSCI benchmark prices."""
    path = DATA_DIR / "msci_benchmark_close_prices.parquet"
    df = pd.read_parquet(path)
    if not isinstance(df.index, pd.DatetimeIndex):
        df.index = pd.DatetimeIndex(df.index)
    return df


def compute_daily_returns(prices: pd.DataFrame) -> pd.DataFrame:
    """Compute daily returns from prices, capped at RETURN_CAP."""
    returns = prices.pct_change().iloc[1:]
    returns = returns.clip(lower=-RETURN_CAP, upper=RETURN_CAP)
    return returns


def compute_buyhold_portfolio_returns(
    returns_df: pd.DataFrame,
    initial_weights: dict[str, float],
    corporate_actions: dict[str, date],
) -> tuple[pd.Series, pd.DataFrame]:
    """Compute Buy-and-Hold weighted returns with drift.

    Returns (daily_returns, weights_history).
    """
    # Filter to tickers in returns_df
    active = set(returns_df.columns) & set(initial_weights.keys())
    current_weights = {t: initial_weights[t] for t in active}

    # Normalize
    total = sum(current_weights.values())
    if total > 0 and abs(total - 1.0) > 1e-10:
        current_weights = {k: v / total for k, v in current_weights.items()}

    weight_rows: list[dict[str, float]] = []

    for idx_date in returns_df.index:
        trading_date = idx_date.date() if hasattr(idx_date, "date") else idx_date

        # Corporate actions
        removed = set()
        for ticker, action_date in corporate_actions.items():
            if ticker in current_weights and trading_date >= action_date:
                removed.add(ticker)

        if removed:
            remaining = {k: v for k, v in current_weights.items() if k not in removed}
            rem_total = sum(remaining.values())
            if rem_total > 0:
                current_weights = {k: v / rem_total for k, v in remaining.items()}
            else:
                current_weights = {}

        # Record weights
        weight_rows.append(dict(current_weights))

        # Drift
        if current_weights:
            day_ret = returns_df.loc[idx_date]
            new_vals = {}
            for t, w in current_weights.items():
                r = day_ret.get(t, 0.0)
                if pd.isna(r):
                    r = 0.0
                new_vals[t] = w * (1.0 + r)
            drift_total = sum(new_vals.values())
            if drift_total > 0:
                current_weights = {t: v / drift_total for t, v in new_vals.items()}

    weights_df = pd.DataFrame(weight_rows, index=returns_df.index)
    weights_df = weights_df.reindex(columns=returns_df.columns, fill_value=0.0)

    daily_returns = (returns_df.fillna(0.0) * weights_df).sum(axis=1)
    return daily_returns, weights_df


def compute_metrics(
    portfolio_returns: pd.Series,
    benchmark_returns: pd.Series,
    daily_rf_series: pd.Series | None = None,
) -> dict:
    """Compute comprehensive performance metrics.

    Parameters
    ----------
    daily_rf_series : pd.Series | None
        Daily risk-free rate series (DatetimeIndex).
        If None, falls back to flat RISK_FREE_RATE_FALLBACK.
    """
    # Align dates
    common_idx = portfolio_returns.index.intersection(benchmark_returns.index)
    port = portfolio_returns.loc[common_idx]
    bench = benchmark_returns.loc[common_idx]

    n_days = len(port)
    n_years = n_days / TRADING_DAYS_PER_YEAR

    # Returns
    cum_port = (1 + port).prod() - 1
    cum_bench = (1 + bench).prod() - 1
    ann_port = (1 + cum_port) ** (1 / n_years) - 1
    ann_bench = (1 + cum_bench) ** (1 / n_years) - 1

    # Daily risk-free rate: use DGS10 series or fallback
    if daily_rf_series is not None and len(daily_rf_series) > 0:
        # Align rf to portfolio dates, forward-fill gaps
        rf_aligned = daily_rf_series.reindex(port.index).ffill().bfill()
        daily_rf = rf_aligned
        # Annualized rf = geometric mean of daily rf over period
        ann_rf = float((1 + daily_rf).prod() ** (TRADING_DAYS_PER_YEAR / len(daily_rf)) - 1)
    else:
        daily_rf = (1 + RISK_FREE_RATE_FALLBACK) ** (1 / TRADING_DAYS_PER_YEAR) - 1
        ann_rf = RISK_FREE_RATE_FALLBACK

    # Excess returns (daily)
    excess = port - daily_rf
    port_vol = port.std() * np.sqrt(TRADING_DAYS_PER_YEAR)

    # Sharpe
    sharpe = (excess.mean() / excess.std()) * np.sqrt(TRADING_DAYS_PER_YEAR) if excess.std() > 0 else 0.0

    # Sortino
    downside = excess[excess < 0]
    downside_std = np.sqrt((downside**2).mean()) * np.sqrt(TRADING_DAYS_PER_YEAR) if len(downside) > 0 else 0.0
    sortino = (ann_port - ann_rf) / downside_std if downside_std > 0 else 0.0

    # Max Drawdown
    cum_wealth = (1 + port).cumprod()
    running_max = cum_wealth.cummax()
    drawdown = (cum_wealth - running_max) / running_max
    max_dd = drawdown.min()

    # Calmar
    calmar = ann_port / abs(max_dd) if abs(max_dd) > 0 else 0.0

    # Beta & Alpha (CAPM)
    cov_matrix = pd.DataFrame({"port": port, "bench": bench}).cov()
    bench_var = bench.var()
    beta = cov_matrix.loc["port", "bench"] / bench_var if bench_var > 0 else 1.0
    alpha = ann_port - ann_rf - beta * (ann_bench - ann_rf)

    # Tracking Error & IR
    active = port - bench
    tracking_error = active.std() * np.sqrt(TRADING_DAYS_PER_YEAR)
    ir = (ann_port - ann_bench) / tracking_error if tracking_error > 0 else 0.0

    # Win Rate
    win_rate = (active > 0).sum() / len(active) if len(active) > 0 else 0.0

    return {
        "n_days": n_days,
        "n_years": round(n_years, 2),
        "cumulative_return": round(cum_port * 100, 2),
        "annualized_return": round(ann_port * 100, 2),
        "benchmark_cum_return": round(cum_bench * 100, 2),
        "benchmark_ann_return": round(ann_bench * 100, 2),
        "volatility": round(port_vol * 100, 2),
        "sharpe_ratio": round(sharpe, 3),
        "sortino_ratio": round(sortino, 3),
        "max_drawdown": round(max_dd * 100, 2),
        "calmar_ratio": round(calmar, 3),
        "beta": round(beta, 3),
        "alpha_capm": round(alpha * 100, 2),
        "tracking_error": round(tracking_error * 100, 2),
        "information_ratio": round(ir, 3),
        "win_rate": round(win_rate * 100, 2),
        "risk_free_rate_ann": round(ann_rf * 100, 2),
    }


def identify_country(
    weights: dict[str, float],
    universe_data: dict,
) -> dict[str, str]:
    """Identify country for each ticker from universe data."""
    ticker_country: dict[str, str] = {}
    for _id, entries in universe_data.items():
        entry = entries[0]
        bloomberg = entry.get("Bloomberg_Ticker", "")
        if bloomberg:
            short = bloomberg.split()[0]
            country = entry.get("Country", "UNKNOWN")
            ticker_country[short] = country
    return ticker_country


def compute_weight_drift_stats(weights_df: pd.DataFrame) -> dict:
    """Compute weight drift statistics."""
    if weights_df.empty:
        return {}

    # Initial vs final weights
    initial = weights_df.iloc[0]
    final = weights_df.iloc[-1]

    # Max weight drift
    drift = (final - initial).abs()
    max_drift_ticker = drift.idxmax()
    max_drift_value = drift.max()

    # Concentration (HHI)
    initial_hhi = (initial**2).sum()
    final_hhi = (final**2).sum()

    return {
        "initial_hhi": round(float(initial_hhi), 4),
        "final_hhi": round(float(final_hhi), 4),
        "max_drift_ticker": str(max_drift_ticker),
        "max_drift_value": round(float(max_drift_value), 4),
        "initial_max_weight": round(float(initial.max()), 4),
        "final_max_weight": round(float(final.max()), 4),
        "initial_top5_weight": round(float(initial.nlargest(5).sum()), 4),
        "final_top5_weight": round(float(final.nlargest(5).sum()), 4),
    }


def main() -> None:
    """Run the full Buy-and-Hold backtest."""
    print("=" * 70)
    print("CA Strategy Buy-and-Hold Backtest")
    print("=" * 70)

    # Fetch FRED DGS10 risk-free rate
    daily_rf_series = fetch_dgs10_daily_rf()
    if len(daily_rf_series) > 0:
        rf_source = "FRED DGS10 (US 10-Year Treasury)"
        # Compute annualized rf for metadata
        _rf_ann = float((1 + daily_rf_series).prod() ** (TRADING_DAYS_PER_YEAR / len(daily_rf_series)) - 1)
        print(f"Risk-free rate: {rf_source}")
        print(f"  Annualized (geometric mean): {_rf_ann:.2%}")
    else:
        rf_source = f"Fixed {RISK_FREE_RATE_FALLBACK:.1%}"
        _rf_ann = RISK_FREE_RATE_FALLBACK
        print(f"Risk-free rate: {rf_source} (FRED unavailable)")

    # Load corporate actions
    ca_raw = load_corporate_actions()
    corporate_actions: dict[str, date] = {}
    for a in ca_raw:
        corporate_actions[a["ticker"]] = date.fromisoformat(a["action_date"])
    print(f"Corporate actions: {len(corporate_actions)}")

    # Load MSCI benchmark
    msci_prices = load_msci_prices()
    msci_returns = compute_daily_returns(msci_prices)
    tok_returns = msci_returns["TOK"]
    print(f"MSCI Kokusai (TOK): {len(tok_returns)} days")

    # Load universe data for MCap & country
    universe_raw = json.loads(
        (ROOT / "data" / "Transcript" / "list_portfolio_20151224.json").read_text()
    )
    ticker_country = identify_country({}, universe_raw)
    mcap_weights = load_universe_mcap_weights()
    print(f"Universe MCap tickers: {len(mcap_weights)}")

    # Load universe prices for MCap benchmark
    universe_prices = load_universe_prices()
    universe_returns = compute_daily_returns(universe_prices)
    print(f"Universe prices: {universe_prices.shape[1]} tickers")

    # Compute MCap-weighted universe benchmark (Buy-and-Hold drift)
    # Map MCap weight tickers to columns in universe_prices
    # Universe prices use mixed tickers - need to find matching ones
    mcap_mapped: dict[str, float] = {}
    for ticker, weight in mcap_weights.items():
        if ticker in universe_returns.columns:
            mcap_mapped[ticker] = weight
        # Also try with yfinance suffix variants
        for suffix in [".L", ".PA", ".DE", ".SW", ".AS", ".AX", ".TO", ".T", ".HK",
                        ".MI", ".MC", ".ST", ".CO", ".OL", ".HE", ".BR", ".SA",
                        ".SI", ".KS", ".JK", ".BK"]:
            candidate = f"{ticker}{suffix}"
            if candidate in universe_returns.columns:
                mcap_mapped[candidate] = weight
                break

    print(f"MCap benchmark mapped tickers: {len(mcap_mapped)}")

    # Compute MCap benchmark returns
    mcap_bench_returns, _ = compute_buyhold_portfolio_returns(
        returns_df=universe_returns,
        initial_weights=mcap_mapped,
        corporate_actions=corporate_actions,
    )

    # Compute equal-weight universe benchmark (Buy-and-Hold drift)
    valid_universe_cols = [c for c in universe_returns.columns
                          if universe_returns[c].notna().sum() > 100]
    ew_weights = {c: 1.0 / len(valid_universe_cols) for c in valid_universe_cols}
    ew_bench_returns, _ = compute_buyhold_portfolio_returns(
        returns_df=universe_returns,
        initial_weights=ew_weights,
        corporate_actions=corporate_actions,
    )

    # Results collection
    all_results: dict = {
        "metadata": {
            "methodology": "Buy-and-Hold (drift weight)",
            "risk_free_rate_source": rf_source,
            "risk_free_rate_annualized": round(_rf_ann, 4),
            "return_cap": RETURN_CAP,
            "start_date": START_DATE.isoformat(),
            "end_date": END_DATE.isoformat(),
            "trading_days_per_year": TRADING_DAYS_PER_YEAR,
            "computed_at": pd.Timestamp.now().isoformat(),
        },
        "portfolios": {},
        "benchmarks": {},
    }

    # Process each portfolio size
    for size in [30, 60, 90]:
        print(f"\n{'─' * 50}")
        print(f"Processing {size}-stock portfolio")
        print(f"{'─' * 50}")

        # Load weights and prices
        weights = load_portfolio_weights(size)
        prices_df = load_price_data(size)
        returns_df = compute_daily_returns(prices_df)

        print(f"  Weights: {len(weights)} tickers")
        print(f"  Price data: {prices_df.shape[1]} tickers available")
        print(f"  Missing: {set(weights.keys()) - set(returns_df.columns)}")

        # Identify US vs non-US
        us_tickers = [t for t in weights if ticker_country.get(t, "") == "UNITED STATES"]
        non_us_tickers = [t for t in weights if ticker_country.get(t, "") != "UNITED STATES"]
        us_weight = sum(weights.get(t, 0) for t in us_tickers)
        non_us_weight = sum(weights.get(t, 0) for t in non_us_tickers)
        data_available = set(weights.keys()) & set(returns_df.columns)
        data_missing = set(weights.keys()) - set(returns_df.columns)

        print(f"  US tickers: {len(us_tickers)} ({us_weight:.1%})")
        print(f"  Non-US tickers: {len(non_us_tickers)} ({non_us_weight:.1%})")
        print(f"  Data available: {len(data_available)}")
        print(f"  Data missing: {len(data_missing)} - {data_missing}")

        # Buy-and-Hold portfolio returns
        port_returns, weight_history = compute_buyhold_portfolio_returns(
            returns_df=returns_df,
            initial_weights=weights,
            corporate_actions=corporate_actions,
        )

        # Weight drift stats
        drift_stats = compute_weight_drift_stats(weight_history)

        # Metrics vs MSCI Kokusai
        metrics_vs_msci = compute_metrics(port_returns, tok_returns, daily_rf_series)

        # Metrics vs MCap benchmark
        metrics_vs_mcap = compute_metrics(port_returns, mcap_bench_returns, daily_rf_series)

        # Metrics vs Equal-Weight benchmark
        metrics_vs_ew = compute_metrics(port_returns, ew_bench_returns, daily_rf_series)

        # Portfolio composition info
        portfolio_info = {
            "total_tickers": len(weights),
            "data_available": len(data_available),
            "data_missing": len(data_missing),
            "missing_tickers": sorted(data_missing),
            "us_tickers": len(us_tickers),
            "non_us_tickers": len(non_us_tickers),
            "us_weight": round(us_weight, 4),
            "non_us_weight": round(non_us_weight, 4),
        }

        all_results["portfolios"][str(size)] = {
            "composition": portfolio_info,
            "vs_msci_kokusai": metrics_vs_msci,
            "vs_mcap_benchmark": metrics_vs_mcap,
            "vs_ew_benchmark": metrics_vs_ew,
            "weight_drift": drift_stats,
        }

        # Print summary
        print(f"\n  vs MSCI Kokusai:")
        print(f"    Sharpe: {metrics_vs_msci['sharpe_ratio']}")
        print(f"    Ann Return: {metrics_vs_msci['annualized_return']}%")
        print(f"    Alpha: {metrics_vs_msci['alpha_capm']}%")
        print(f"    Max DD: {metrics_vs_msci['max_drawdown']}%")
        print(f"    IR: {metrics_vs_msci['information_ratio']}")

        print(f"\n  vs MCap Benchmark:")
        print(f"    Alpha: {metrics_vs_mcap['alpha_capm']}%")
        print(f"    IR: {metrics_vs_mcap['information_ratio']}")

    # Store benchmark info
    all_results["benchmarks"] = {
        "msci_kokusai": {
            "etf": "TOK",
            "ann_return": round(
                ((1 + tok_returns).prod() ** (TRADING_DAYS_PER_YEAR / len(tok_returns)) - 1) * 100, 2
            ),
            "cum_return": round(((1 + tok_returns).prod() - 1) * 100, 2),
        },
        "mcap_universe": {
            "mapped_tickers": len(mcap_mapped),
            "total_universe": len(mcap_weights),
        },
    }

    # Save results
    result_path = RESULT_DIR / "buyhold_backtest_results.json"
    result_path.write_text(json.dumps(all_results, indent=2, ensure_ascii=False))
    print(f"\n\nResults saved to: {result_path}")

    # Also save cumulative returns for plotting (structured per portfolio)
    cum_data: dict = {}
    for size in [30, 60, 90]:
        weights = load_portfolio_weights(size)
        prices_df = load_price_data(size)
        returns_df = compute_daily_returns(prices_df)
        port_returns, _ = compute_buyhold_portfolio_returns(
            returns_df=returns_df,
            initial_weights=weights,
            corporate_actions=corporate_actions,
        )

        # Align all series to portfolio dates
        common = port_returns.index.intersection(tok_returns.index)
        common = common.intersection(mcap_bench_returns.index)
        common = common.intersection(ew_bench_returns.index)

        cum_data[str(size)] = {
            "dates": [d.isoformat() for d in common],
            "portfolio": ((1 + port_returns.loc[common]).cumprod()).tolist(),
            "msci_kokusai": ((1 + tok_returns.loc[common]).cumprod()).tolist(),
            "mcap_universe": ((1 + mcap_bench_returns.loc[common]).cumprod()).tolist(),
            "ew_universe": ((1 + ew_bench_returns.loc[common]).cumprod()).tolist(),
        }

    # Also save DGS10 time series for notebook
    if len(daily_rf_series) > 0:
        cum_data["dgs10"] = {
            "dates": [d.isoformat() for d in daily_rf_series.index],
            "annual_rate_pct": [round(float(((1 + v) ** TRADING_DAYS_PER_YEAR - 1) * 100), 3)
                                for v in daily_rf_series.values],
        }

    cum_path = RESULT_DIR / "buyhold_cumulative_returns.json"
    cum_path.write_text(json.dumps(cum_data, ensure_ascii=False))
    print(f"Cumulative returns saved to: {cum_path}")

    return all_results


if __name__ == "__main__":
    results = main()
