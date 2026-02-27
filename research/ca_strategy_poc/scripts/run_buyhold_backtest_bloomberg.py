"""Full Buy-and-Hold backtest for CA Strategy portfolios using Bloomberg data.

Replaces yfinance-based backtest with Bloomberg terminal data for:
- More complete universe coverage (370/395 vs 278/395 with yfinance)
- Direct MSCI Kokusai index data (MXKO INDEX, not TOK ETF proxy)
- Historical market cap for MCap-weighted benchmark

Data sources:
- list_port_and_index_price_2015_2026.csv: Daily prices (USD) for all universe tickers + indices
- list_port_mcap_2015_2026.json: Monthly market cap for MCap-weighted benchmark

Compares against:
- MSCI Kokusai (MXKO INDEX, direct index level)
- MSCI Kokusai Equal Weight (MXKOEW INDEX)
- MCap-weighted universe benchmark (historical MCap + drift)
- Equal-weight universe benchmark

Risk-free rate: FRED DGS10 (US 10-Year Treasury yield, daily).

Outputs results to JSON for report generation.
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
BBG_CSV = ROOT / "data" / "Transcript" / "list_port_and_index_price_2015_2026.csv"
BBG_MCAP_JSON = ROOT / "data" / "Transcript" / "list_port_mcap_2015_2026.json"
UNIVERSE_JSON = ROOT / "data" / "Transcript" / "list_portfolio_20151224.json"
CONFIG_DIR = ROOT / "research" / "ca_strategy_poc" / "config"
OUTPUT_DIR = (
    ROOT / "research" / "ca_strategy_poc" / "workspaces" / "full_run" / "output"
)
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

# Index column names in Bloomberg CSV
MSCI_KOKUSAI_COL = "MXKO INDEX"
MSCI_KOKUSAI_EW_COL = "MXKOEW INDEX"
MSCI_WORLD_COL = "MXWDJ INDEX"


def fetch_dgs10_daily_rf() -> pd.Series:
    """Fetch FRED DGS10 (10-Year Treasury yield) and convert to daily rate."""
    cache_path = FRED_CACHE_DIR / "dgs10_daily.parquet"

    if cache_path.exists():
        dgs10 = pd.read_parquet(cache_path)
        if isinstance(dgs10, pd.DataFrame):
            dgs10 = dgs10.iloc[:, 0]
        dgs10.index = pd.DatetimeIndex(dgs10.index)
        print(f"DGS10 loaded from cache: {len(dgs10)} observations")
        daily_rf = ((1 + dgs10 / 100) ** (1 / TRADING_DAYS_PER_YEAR) - 1).ffill()
        return daily_rf

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

        cache_path.parent.mkdir(parents=True, exist_ok=True)
        dgs10.to_frame().to_parquet(cache_path)

        daily_rf = ((1 + dgs10 / 100) ** (1 / TRADING_DAYS_PER_YEAR) - 1).ffill()
        return daily_rf

    except Exception as e:
        print(f"WARNING: Failed to fetch DGS10 from FRED: {e}")
        return pd.Series(dtype=float)


def load_bloomberg_prices() -> pd.DataFrame:
    """Load Bloomberg price data from CSV.

    Returns DataFrame with DatetimeIndex and Bloomberg ticker columns.
    Non-trading days (all NaN rows) are dropped.
    """
    print("Loading Bloomberg price data...")
    df = pd.read_csv(BBG_CSV, parse_dates=["Date"], index_col="Date")
    df.index = pd.DatetimeIndex(df.index)

    # Drop rows where ALL values are NaN (weekends/holidays)
    df = df.dropna(how="all")

    # Sort by date
    df = df.sort_index()

    print(f"  Rows: {len(df)}, Columns: {len(df.columns)}")
    print(f"  Date range: {df.index.min().date()} ~ {df.index.max().date()}")

    # Count non-index equity columns
    equity_cols = [c for c in df.columns if "INDEX" not in c]
    index_cols = [c for c in df.columns if "INDEX" in c]
    print(f"  Equity columns: {len(equity_cols)}")
    print(f"  Index columns: {index_cols}")

    return df


def load_bloomberg_mcap() -> pd.DataFrame:
    """Load Bloomberg market cap data from JSON.

    Returns DataFrame with DatetimeIndex and Bloomberg ticker columns.
    Values are market cap in USD (units from Bloomberg).
    """
    print("Loading Bloomberg market cap data...")
    with open(BBG_MCAP_JSON) as f:
        data = json.load(f)

    df = pd.DataFrame(data)
    df["Date"] = pd.to_datetime(df["Date"])
    df = df.set_index("Date").sort_index()

    # Drop rows where ALL values are NaN
    ticker_cols = [c for c in df.columns if c != "Date"]
    df = df.dropna(how="all", subset=ticker_cols if ticker_cols else None)

    print(f"  Rows: {len(df)}, Columns: {len(df.columns)}")
    print(f"  Date range: {df.index.min().date()} ~ {df.index.max().date()}")

    return df


def build_bbg_ticker_map() -> dict[str, str]:
    """Build short ticker -> Bloomberg ticker mapping from universe JSON.

    Returns dict mapping e.g. 'AAPL' -> 'AAPL US Equity'.
    """
    with open(UNIVERSE_JSON) as f:
        data = json.load(f)

    short_to_bbg: dict[str, str] = {}
    for _id, entries in data.items():
        entry = entries[0]
        bbg = entry.get("Bloomberg_Ticker", "")
        if bbg:
            short = bbg.split()[0]
            short_to_bbg[short] = bbg

    return short_to_bbg


def load_universe_data() -> dict:
    """Load universe JSON for sector/country/MCap info."""
    with open(UNIVERSE_JSON) as f:
        return json.load(f)


def load_portfolio_weights(size: int) -> dict[str, float]:
    """Load portfolio weights from CSV."""
    suffix = "" if size == 30 else f"_{size}"
    path = OUTPUT_DIR / f"portfolio_weights{suffix}.csv"
    df = pd.read_csv(path)
    return dict(zip(df["ticker"], df["weight"], strict=True))


def load_corporate_actions() -> dict[str, date]:
    """Load corporate actions from config."""
    path = CONFIG_DIR / "corporate_actions.json"
    data = json.loads(path.read_text())
    return {
        a["ticker"]: date.fromisoformat(a["action_date"])
        for a in data["corporate_actions"]
    }


def map_portfolio_to_bbg(
    weights: dict[str, float],
    short_to_bbg: dict[str, str],
    available_cols: set[str],
) -> tuple[dict[str, float], list[str]]:
    """Map portfolio short tickers to Bloomberg columns.

    Returns (mapped_weights, missing_tickers).
    mapped_weights keys are Bloomberg ticker format (e.g. 'AAPL US Equity').
    """
    mapped: dict[str, float] = {}
    missing: list[str] = []

    for short_ticker, weight in weights.items():
        bbg = short_to_bbg.get(short_ticker)
        if bbg and bbg in available_cols:
            mapped[bbg] = weight
        else:
            # Try common exchange suffixes
            candidates = [
                f"{short_ticker} US Equity",
                f"{short_ticker} LN Equity",
                f"{short_ticker} FP Equity",
                f"{short_ticker} GR Equity",
                f"{short_ticker} SW Equity",
                f"{short_ticker} CN Equity",
                f"{short_ticker} AU Equity",
                f"{short_ticker} NA Equity",
                f"{short_ticker} SM Equity",
                f"{short_ticker} IM Equity",
                f"{short_ticker} DC Equity",
                f"{short_ticker} SS Equity",
                f"{short_ticker} HK Equity",
                f"{short_ticker} TT Equity",
                f"{short_ticker} KS Equity",
                f"{short_ticker} IJ Equity",
                f"{short_ticker} BZ Equity",
                f"{short_ticker} IN Equity",
                f"{short_ticker} TB Equity",
                f"{short_ticker} SJ Equity",
                f"{short_ticker} BB Equity",
                f"{short_ticker} PM Equity",
                f"{short_ticker} MK Equity",
                f"{short_ticker} TI Equity",
                f"{short_ticker} FH Equity",
                f"{short_ticker} NO Equity",
                f"{short_ticker} PL Equity",
                f"{short_ticker} MM Equity",
            ]
            found = False
            for c in candidates:
                if c in available_cols:
                    mapped[c] = weight
                    found = True
                    break
            if not found:
                missing.append(short_ticker)

    return mapped, missing


def compute_daily_returns(prices: pd.DataFrame) -> pd.DataFrame:
    """Compute daily returns from prices, capped at RETURN_CAP."""
    returns = prices.pct_change().iloc[1:]
    returns = returns.clip(lower=-RETURN_CAP, upper=RETURN_CAP)
    return returns


def compute_buyhold_portfolio_returns(
    returns_df: pd.DataFrame,
    initial_weights: dict[str, float],
    corporate_actions: dict[str, date],
    bbg_to_short: dict[str, str] | None = None,
) -> tuple[pd.Series, pd.DataFrame]:
    """Compute Buy-and-Hold weighted returns with drift.

    Parameters
    ----------
    returns_df : pd.DataFrame
        Daily returns with Bloomberg ticker columns.
    initial_weights : dict[str, float]
        Initial weights keyed by Bloomberg ticker (e.g. 'AAPL US Equity').
    corporate_actions : dict[str, date]
        Corporate actions keyed by short ticker (e.g. 'ARM').
    bbg_to_short : dict[str, str] | None
        Bloomberg -> short ticker map for corporate action matching.

    Returns
    -------
    tuple[pd.Series, pd.DataFrame]
        (daily_returns, weights_history)
    """
    # Filter to tickers in returns_df
    active = set(returns_df.columns) & set(initial_weights.keys())
    current_weights = {t: initial_weights[t] for t in active}

    # Normalize
    total = sum(current_weights.values())
    if total > 0 and abs(total - 1.0) > 1e-10:
        current_weights = {k: v / total for k, v in current_weights.items()}

    # Map corporate actions to Bloomberg format if mapping provided
    ca_bbg: dict[str, date] = {}
    if bbg_to_short:
        short_to_bbg_rev = {v: k for k, v in bbg_to_short.items()}
        for short_ticker, action_date in corporate_actions.items():
            bbg = short_to_bbg_rev.get(short_ticker)
            if bbg:
                ca_bbg[bbg] = action_date
    else:
        ca_bbg = {k: v for k, v in corporate_actions.items()}

    weight_rows: list[dict[str, float]] = []

    for idx_date in returns_df.index:
        trading_date = idx_date.date() if hasattr(idx_date, "date") else idx_date

        # Corporate actions
        removed = set()
        for ticker, action_date in ca_bbg.items():
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


def compute_mcap_benchmark_returns(
    returns_df: pd.DataFrame,
    mcap_df: pd.DataFrame,
    corporate_actions: dict[str, date],
    bbg_to_short: dict[str, str],
) -> pd.Series:
    """Compute MCap-weighted universe benchmark using initial MCap weights.

    Uses the closest MCap snapshot to START_DATE with forward-fill to maximize
    ticker coverage. Bloomberg MCap data is monthly and sparse on non-month-end
    dates, so forward-fill ensures we pick up the 2015-12-31 snapshot.
    """
    # Forward-fill MCap data to handle sparse monthly reporting
    mcap_ffill = mcap_df.ffill()

    # Find initial MCap snapshot (closest to START_DATE)
    start_ts = pd.Timestamp(START_DATE)
    mcap_before_start = mcap_ffill[mcap_ffill.index <= start_ts]

    if len(mcap_before_start) == 0:
        initial_mcap = mcap_ffill.iloc[0]
    else:
        initial_mcap = mcap_before_start.iloc[-1]

    # Build initial weights from MCap
    mcap_weights: dict[str, float] = {}
    for col in mcap_df.columns:
        val = initial_mcap.get(col)
        if pd.notna(val) and val > 0 and col in returns_df.columns:
            mcap_weights[col] = float(val)

    # Normalize to weights
    total = sum(mcap_weights.values())
    if total > 0:
        mcap_weights = {k: v / total for k, v in mcap_weights.items()}

    print(f"  MCap benchmark: {len(mcap_weights)} tickers, total MCap = {total:,.0f}")

    mcap_returns, _ = compute_buyhold_portfolio_returns(
        returns_df=returns_df,
        initial_weights=mcap_weights,
        corporate_actions=corporate_actions,
        bbg_to_short=bbg_to_short,
    )

    return mcap_returns


def compute_metrics(
    portfolio_returns: pd.Series,
    benchmark_returns: pd.Series,
    daily_rf_series: pd.Series | None = None,
) -> dict:
    """Compute comprehensive performance metrics."""
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

    # Daily risk-free rate
    if daily_rf_series is not None and len(daily_rf_series) > 0:
        rf_aligned = daily_rf_series.reindex(port.index).ffill().bfill()
        daily_rf = rf_aligned
        ann_rf = float(
            (1 + daily_rf).prod() ** (TRADING_DAYS_PER_YEAR / len(daily_rf)) - 1
        )
    else:
        daily_rf = (1 + RISK_FREE_RATE_FALLBACK) ** (1 / TRADING_DAYS_PER_YEAR) - 1
        ann_rf = RISK_FREE_RATE_FALLBACK

    # Excess returns (daily)
    excess = port - daily_rf
    port_vol = port.std() * np.sqrt(TRADING_DAYS_PER_YEAR)

    # Sharpe
    sharpe = (
        (excess.mean() / excess.std()) * np.sqrt(TRADING_DAYS_PER_YEAR)
        if excess.std() > 0
        else 0.0
    )

    # Sortino
    downside = excess[excess < 0]
    downside_std = (
        np.sqrt((downside**2).mean()) * np.sqrt(TRADING_DAYS_PER_YEAR)
        if len(downside) > 0
        else 0.0
    )
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

    # Up/Down Capture
    up_days = bench > 0
    down_days = bench < 0
    up_capture = (
        (port[up_days].mean() / bench[up_days].mean()) * 100
        if up_days.sum() > 0
        else 0.0
    )
    down_capture = (
        (port[down_days].mean() / bench[down_days].mean()) * 100
        if down_days.sum() > 0
        else 0.0
    )

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
        "up_capture": round(up_capture, 1),
        "down_capture": round(down_capture, 1),
        "risk_free_rate_ann": round(ann_rf * 100, 2),
    }


def compute_annual_returns(
    portfolio_returns: pd.Series,
    benchmark_returns: pd.Series,
) -> list[dict]:
    """Compute annual returns and active returns."""
    common_idx = portfolio_returns.index.intersection(benchmark_returns.index)
    port = portfolio_returns.loc[common_idx]
    bench = benchmark_returns.loc[common_idx]

    years = sorted(set(port.index.year))
    annual_data = []

    for year in years:
        mask = port.index.year == year
        p = port[mask]
        b = bench[mask]

        if len(p) < 10:
            continue

        cum_p = (1 + p).prod() - 1
        cum_b = (1 + b).prod() - 1

        annual_data.append(
            {
                "year": year,
                "portfolio_return": round(cum_p * 100, 2),
                "benchmark_return": round(cum_b * 100, 2),
                "active_return": round((cum_p - cum_b) * 100, 2),
            }
        )

    return annual_data


def compute_weight_drift_stats(weights_df: pd.DataFrame) -> dict:
    """Compute weight drift statistics."""
    if weights_df.empty:
        return {}

    initial = weights_df.iloc[0]
    final = weights_df.iloc[-1]

    drift = (final - initial).abs()
    max_drift_ticker = drift.idxmax()
    max_drift_value = drift.max()

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


def main() -> dict:
    """Run the full Buy-and-Hold backtest using Bloomberg data."""
    print("=" * 70)
    print("CA Strategy Buy-and-Hold Backtest (Bloomberg Data)")
    print("=" * 70)

    # -----------------------------------------------------------------------
    # 1. Load data
    # -----------------------------------------------------------------------
    bbg_prices = load_bloomberg_prices()
    bbg_mcap = load_bloomberg_mcap()

    # Build ticker mapping
    short_to_bbg = build_bbg_ticker_map()
    bbg_to_short = {v: k for k, v in short_to_bbg.items()}

    # Separate equity and index columns
    equity_cols = [c for c in bbg_prices.columns if "INDEX" not in c]
    available_cols = set(equity_cols)

    # Compute returns for all equities
    equity_prices = bbg_prices[equity_cols]
    all_returns = compute_daily_returns(equity_prices)

    # Filter to analysis period
    start_ts = pd.Timestamp(START_DATE)
    end_ts = pd.Timestamp(END_DATE)

    # -----------------------------------------------------------------------
    # 2. Benchmarks
    # -----------------------------------------------------------------------
    # MSCI Kokusai (direct index, not ETF proxy)
    msci_prices = bbg_prices[[MSCI_KOKUSAI_COL]].dropna()
    msci_returns = compute_daily_returns(msci_prices)[MSCI_KOKUSAI_COL]
    msci_returns = msci_returns[
        (msci_returns.index >= start_ts) & (msci_returns.index <= end_ts)
    ]
    print(f"\nMSCI Kokusai (MXKO INDEX): {len(msci_returns)} days")

    # MSCI Kokusai Equal Weight
    msci_ew_prices = bbg_prices[[MSCI_KOKUSAI_EW_COL]].dropna()
    msci_ew_returns = compute_daily_returns(msci_ew_prices)[MSCI_KOKUSAI_EW_COL]
    msci_ew_returns = msci_ew_returns[
        (msci_ew_returns.index >= start_ts) & (msci_ew_returns.index <= end_ts)
    ]
    print(f"MSCI Kokusai EW (MXKOEW INDEX): {len(msci_ew_returns)} days")

    # Align all equity returns to MSCI Kokusai trading days for consistency.
    # Bloomberg price data includes non-trading days (some markets open when
    # MSCI is closed), which would introduce spurious returns if not filtered.
    msci_trading_days = msci_returns.index
    all_returns = all_returns[
        (all_returns.index >= start_ts) & (all_returns.index <= end_ts)
    ]
    all_returns = all_returns.loc[all_returns.index.intersection(msci_trading_days)]
    print(
        f"\nAnalysis period: {all_returns.index.min().date()} ~ {all_returns.index.max().date()}"
    )
    print(f"Trading days (aligned to MSCI): {len(all_returns)}")

    # Risk-free rate
    daily_rf_series = fetch_dgs10_daily_rf()
    if len(daily_rf_series) > 0:
        rf_source = "FRED DGS10 (US 10-Year Treasury)"
        _rf_ann = float(
            (1 + daily_rf_series).prod()
            ** (TRADING_DAYS_PER_YEAR / len(daily_rf_series))
            - 1
        )
        print(f"\nRisk-free rate: {rf_source}")
        print(f"  Annualized (geometric mean): {_rf_ann:.2%}")
    else:
        rf_source = f"Fixed {RISK_FREE_RATE_FALLBACK:.1%}"
        _rf_ann = RISK_FREE_RATE_FALLBACK
        print(f"\nRisk-free rate: {rf_source} (FRED unavailable)")

    # Corporate actions
    corporate_actions = load_corporate_actions()
    print(f"Corporate actions: {len(corporate_actions)}")

    # MCap-weighted universe benchmark (using Bloomberg MCap data)
    print("\nBuilding MCap-weighted universe benchmark...")
    mcap_bench_returns = compute_mcap_benchmark_returns(
        returns_df=all_returns,
        mcap_df=bbg_mcap,
        corporate_actions=corporate_actions,
        bbg_to_short=bbg_to_short,
    )

    # Equal-weight universe benchmark
    print("Building equal-weight universe benchmark...")
    valid_cols = [c for c in all_returns.columns if all_returns[c].notna().sum() > 100]
    ew_weights = {c: 1.0 / len(valid_cols) for c in valid_cols}
    ew_bench_returns, _ = compute_buyhold_portfolio_returns(
        returns_df=all_returns,
        initial_weights=ew_weights,
        corporate_actions=corporate_actions,
        bbg_to_short=bbg_to_short,
    )
    print(f"  Equal-weight benchmark: {len(valid_cols)} tickers")

    # -----------------------------------------------------------------------
    # 3. Portfolio analysis
    # -----------------------------------------------------------------------
    all_results: dict = {
        "metadata": {
            "data_source": "Bloomberg Terminal",
            "methodology": "Buy-and-Hold (drift weight)",
            "risk_free_rate_source": rf_source,
            "risk_free_rate_annualized": round(_rf_ann, 4),
            "return_cap": RETURN_CAP,
            "start_date": START_DATE.isoformat(),
            "end_date": END_DATE.isoformat(),
            "trading_days_per_year": TRADING_DAYS_PER_YEAR,
            "msci_benchmark": "MXKO INDEX (direct, not TOK ETF proxy)",
            "computed_at": pd.Timestamp.now().isoformat(),
        },
        "portfolios": {},
        "benchmarks": {},
    }

    # Cumulative returns for plotting
    cum_data: dict = {}

    for size in [30, 60, 90]:
        print(f"\n{'─' * 60}")
        print(f"Processing {size}-stock portfolio (Bloomberg)")
        print(f"{'─' * 60}")

        # Load weights and map to Bloomberg tickers
        weights = load_portfolio_weights(size)
        mapped_weights, missing_tickers = map_portfolio_to_bbg(
            weights, short_to_bbg, available_cols
        )

        print(f"  Original tickers: {len(weights)}")
        print(f"  Mapped to Bloomberg: {len(mapped_weights)}")
        print(f"  Missing: {len(missing_tickers)} - {missing_tickers}")

        # Normalize mapped weights
        mapped_total = sum(mapped_weights.values())
        if mapped_total > 0:
            mapped_weights = {k: v / mapped_total for k, v in mapped_weights.items()}

        # Coverage stats
        data_available = len(mapped_weights)
        data_missing = len(missing_tickers)
        coverage_pct = data_available / len(weights) * 100

        # Identify US vs non-US from Bloomberg ticker suffix
        us_tickers = [t for t in mapped_weights if "US Equity" in t]
        non_us_tickers = [t for t in mapped_weights if "US Equity" not in t]
        us_weight = sum(mapped_weights.get(t, 0) for t in us_tickers)
        non_us_weight = sum(mapped_weights.get(t, 0) for t in non_us_tickers)

        print(f"  US tickers: {len(us_tickers)} ({us_weight:.1%})")
        print(f"  Non-US tickers: {len(non_us_tickers)} ({non_us_weight:.1%})")
        print(f"  Coverage: {coverage_pct:.1f}%")

        # Buy-and-Hold portfolio returns
        port_returns, weight_history = compute_buyhold_portfolio_returns(
            returns_df=all_returns,
            initial_weights=mapped_weights,
            corporate_actions=corporate_actions,
            bbg_to_short=bbg_to_short,
        )

        # Weight drift stats
        drift_stats = compute_weight_drift_stats(weight_history)

        # Metrics vs MSCI Kokusai (direct index)
        metrics_vs_msci = compute_metrics(port_returns, msci_returns, daily_rf_series)

        # Metrics vs MSCI Kokusai Equal Weight
        metrics_vs_msci_ew = compute_metrics(
            port_returns, msci_ew_returns, daily_rf_series
        )

        # Metrics vs MCap benchmark
        metrics_vs_mcap = compute_metrics(
            port_returns, mcap_bench_returns, daily_rf_series
        )

        # Metrics vs Equal-Weight benchmark
        metrics_vs_ew = compute_metrics(port_returns, ew_bench_returns, daily_rf_series)

        # Annual returns
        annual_vs_msci = compute_annual_returns(port_returns, msci_returns)
        annual_vs_mcap = compute_annual_returns(port_returns, mcap_bench_returns)

        # Portfolio composition info
        portfolio_info = {
            "total_tickers": len(weights),
            "data_available": data_available,
            "data_missing": data_missing,
            "missing_tickers": sorted(missing_tickers),
            "coverage_pct": round(coverage_pct, 1),
            "us_tickers": len(us_tickers),
            "non_us_tickers": len(non_us_tickers),
            "us_weight": round(us_weight, 4),
            "non_us_weight": round(non_us_weight, 4),
        }

        all_results["portfolios"][str(size)] = {
            "composition": portfolio_info,
            "vs_msci_kokusai": metrics_vs_msci,
            "vs_msci_kokusai_ew": metrics_vs_msci_ew,
            "vs_mcap_benchmark": metrics_vs_mcap,
            "vs_ew_benchmark": metrics_vs_ew,
            "annual_vs_msci": annual_vs_msci,
            "annual_vs_mcap": annual_vs_mcap,
            "weight_drift": drift_stats,
        }

        # Print summary
        print("\n  vs MSCI Kokusai (MXKO INDEX):")
        print(
            f"    Ann Return:  {metrics_vs_msci['annualized_return']}% (Bench: {metrics_vs_msci['benchmark_ann_return']}%)"
        )
        print(f"    Sharpe:      {metrics_vs_msci['sharpe_ratio']}")
        print(f"    Alpha:       {metrics_vs_msci['alpha_capm']}%")
        print(f"    Max DD:      {metrics_vs_msci['max_drawdown']}%")
        print(f"    IR:          {metrics_vs_msci['information_ratio']}")
        print(f"    Beta:        {metrics_vs_msci['beta']}")
        print(f"    Up Capture:  {metrics_vs_msci['up_capture']}%")
        print(f"    Down Capture:{metrics_vs_msci['down_capture']}%")

        print("\n  vs MCap Benchmark:")
        print(
            f"    Ann Return:  {metrics_vs_mcap['annualized_return']}% (Bench: {metrics_vs_mcap['benchmark_ann_return']}%)"
        )
        print(f"    Alpha:       {metrics_vs_mcap['alpha_capm']}%")
        print(f"    IR:          {metrics_vs_mcap['information_ratio']}")

        print("\n  Annual Returns vs MSCI Kokusai:")
        for yr in annual_vs_msci:
            sign = "+" if yr["active_return"] >= 0 else ""
            print(
                f"    {yr['year']}: Port {yr['portfolio_return']:+.2f}% | Bench {yr['benchmark_return']:+.2f}% | Active {sign}{yr['active_return']:.2f}%"
            )

        # Cumulative returns for plotting
        common = port_returns.index.intersection(msci_returns.index)
        common = common.intersection(mcap_bench_returns.index)
        common = common.intersection(ew_bench_returns.index)
        common = common.intersection(msci_ew_returns.index)

        cum_data[str(size)] = {
            "dates": [d.isoformat() for d in common],
            "portfolio": ((1 + port_returns.loc[common]).cumprod()).tolist(),
            "msci_kokusai": ((1 + msci_returns.loc[common]).cumprod()).tolist(),
            "msci_kokusai_ew": ((1 + msci_ew_returns.loc[common]).cumprod()).tolist(),
            "mcap_universe": ((1 + mcap_bench_returns.loc[common]).cumprod()).tolist(),
            "ew_universe": ((1 + ew_bench_returns.loc[common]).cumprod()).tolist(),
        }

    # -----------------------------------------------------------------------
    # 4. Benchmark info
    # -----------------------------------------------------------------------
    # MSCI Kokusai stats
    msci_period = msci_returns[
        (msci_returns.index >= start_ts) & (msci_returns.index <= end_ts)
    ]
    n_msci = len(msci_period)
    cum_msci = (1 + msci_period).prod() - 1
    ann_msci = (1 + cum_msci) ** (TRADING_DAYS_PER_YEAR / n_msci) - 1

    all_results["benchmarks"] = {
        "msci_kokusai": {
            "source": "MXKO INDEX (Bloomberg, direct index level)",
            "ann_return": round(ann_msci * 100, 2),
            "cum_return": round(cum_msci * 100, 2),
            "n_days": n_msci,
        },
        "msci_kokusai_ew": {
            "source": "MXKOEW INDEX (Bloomberg)",
        },
        "mcap_universe": {
            "source": "Bloomberg MCap data",
            "description": "Initial MCap weights from Bloomberg + Buy-and-Hold drift",
        },
        "data_coverage": {
            "universe_total": 395,
            "bloomberg_available": len(
                [c for c in equity_cols if c in set(short_to_bbg.values())]
            ),
            "total_equity_cols": len(equity_cols),
            "yfinance_comparison": "278 (70.4% coverage)",
            "bloomberg_coverage_note": "370/395 = 93.7% universe coverage",
        },
    }

    # -----------------------------------------------------------------------
    # 5. Save results
    # -----------------------------------------------------------------------
    RESULT_DIR.mkdir(parents=True, exist_ok=True)

    result_path = RESULT_DIR / "buyhold_backtest_results_bloomberg.json"
    result_path.write_text(json.dumps(all_results, indent=2, ensure_ascii=False))
    print(f"\n\nResults saved to: {result_path}")

    # Save cumulative returns
    if len(daily_rf_series) > 0:
        cum_data["dgs10"] = {
            "dates": [d.isoformat() for d in daily_rf_series.index],
            "annual_rate_pct": [
                round(float(((1 + v) ** TRADING_DAYS_PER_YEAR - 1) * 100), 3)
                for v in daily_rf_series.values
            ],
        }

    cum_path = RESULT_DIR / "buyhold_cumulative_returns_bloomberg.json"
    cum_path.write_text(json.dumps(cum_data, ensure_ascii=False))
    print(f"Cumulative returns saved to: {cum_path}")

    return all_results


if __name__ == "__main__":
    results = main()
