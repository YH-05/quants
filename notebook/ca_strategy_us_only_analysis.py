# /// script
# requires-python = ">=3.12"
# dependencies = [
#     "marimo",
#     "pandas>=2.0.0",
#     "numpy>=1.26.0",
#     "plotly>=5.18.0",
# ]
# ///

import marimo

__generated_with = "0.19.4"
app = marimo.App(width="medium")


@app.cell
def _():
    """Setup and imports."""
    import json
    from datetime import datetime
    from pathlib import Path

    import marimo as mo
    import numpy as np
    import pandas as pd

    mo.md(
        """
    # CA Strategy: US-Only Performance Analysis

    **目的**: 投資ユニバース395銘柄のうち、yfinance でデータ取得可能な米国株のみで
    ポートフォリオ・ベンチマークを再構築し、パフォーマンスを評価する。

    - **US-Only Universe Benchmark**: 米国株のみの時価総額加重ベンチマーク
    - **US-Only Portfolio**: 非米国株を除外し、ウェイトを再正規化したポートフォリオ
    - **Comparison**: Full Portfolio vs US-Only Portfolio の差分分析

    ---
    """
    )
    return Path, datetime, json, mo, np, pd


@app.cell
def _(mo):
    """Configuration controls."""
    RISK_FREE_RATE = mo.ui.number(
        value=0.045,
        start=0.0,
        stop=0.20,
        step=0.005,
        label="Risk-Free Rate (年率)",
    )

    RETURN_CAP = mo.ui.number(
        value=0.50,
        start=0.10,
        stop=1.00,
        step=0.05,
        label="Daily Return Cap (±)",
    )

    PORTFOLIO_SIZE = mo.ui.dropdown(
        options=["30", "60", "90"],
        value="30",
        label="Portfolio Size",
    )

    mo.hstack([PORTFOLIO_SIZE, RISK_FREE_RATE, RETURN_CAP])
    return PORTFOLIO_SIZE, RETURN_CAP, RISK_FREE_RATE


@app.cell
def _(Path, json, mo, pd):
    """Load universe & identify US stocks."""
    _list_path = Path("../data/Transcript/list_portfolio_20151224.json")

    if not _list_path.exists():
        mo.stop(
            True,
            mo.md("**Error**: `data/Transcript/list_portfolio_20151224.json` が見つかりません。"),
        )

    with open(_list_path) as _f:
        universe_data = json.load(_f)

    # Extract all Bloomberg tickers, identify US stocks by exchange="US"
    # Also include NR/NQ exchanges for US-domiciled companies
    us_short_tickers: set[str] = set()
    all_entries: list[dict] = []
    _us_entries: list[dict] = []
    _non_us_entries: list[dict] = []

    for _k, _entries in universe_data.items():
        _e = _entries[0]
        _bbg = _e.get("Bloomberg_Ticker", "")
        if not _bbg:
            continue
        _parts = _bbg.split()
        if len(_parts) < 3:
            continue

        _short, _exchange = _parts[0], _parts[1]
        _entry = {
            "short_ticker": _short,
            "exchange": _exchange,
            "country": _e["Country"],
            "name": _e["Name"],
            "sector": _e["GICS_Sector"],
            "mcap": _e.get("MSCI_Mkt_Cap_USD_MM", 0),
            "bbg_ticker": _bbg,
        }
        all_entries.append(_entry)

        _is_us = _exchange == "US"
        # NR/NQ exchanges that are actually US-domiciled
        if _exchange in ("NR", "NQ") and _e["Country"] == "UNITED STATES":
            _is_us = True

        if _is_us:
            us_short_tickers.add(_short)
            _us_entries.append(_entry)
        else:
            _non_us_entries.append(_entry)

    # Manual additions: these companies are US-listed but have non-US Bloomberg codes
    # or are not in the universe JSON
    _manual_us = {"AVGO", "DD", "CI"}
    us_short_tickers.update(_manual_us)

    _total_mcap = sum(e["mcap"] for e in all_entries if e["mcap"] > 0)
    _us_mcap = sum(e["mcap"] for e in _us_entries if e["mcap"] > 0)

    mo.md(
        f"""
    ### Universe & US Stock Identification

    | Item | Value |
    |------|-------|
    | Total Universe | {len(all_entries)} stocks |
    | US Stocks (exchange=US) | {len(_us_entries)} stocks |
    | Manual US additions | {sorted(_manual_us)} |
    | **Total US tickers** | **{len(us_short_tickers)}** |
    | Non-US Stocks | {len(_non_us_entries)} stocks |
    | US MCap Coverage | {_us_mcap / _total_mcap:.1%} of total |
    """
    )
    return all_entries, universe_data, us_short_tickers


@app.cell
def _(Path, all_entries, mo, np, pd, universe_data, us_short_tickers):
    """Build US-Only Universe Benchmark (MCap-weighted)."""
    _univ_path = Path("../data/raw/yfinance/stocks/universe_benchmark_close_prices.parquet")

    if not _univ_path.exists():
        mo.stop(
            True,
            mo.md("**Error**: `universe_benchmark_close_prices.parquet` が見つかりません。"),
        )

    _univ_close = pd.read_parquet(_univ_path)
    if not isinstance(_univ_close.index, pd.DatetimeIndex):
        _univ_close.index = pd.DatetimeIndex(_univ_close.index)

    # Bloomberg -> yfinance ticker mapping
    _exchange_map = {
        "US": "", "LN": ".L", "SW": ".SW", "VX": ".SW", "GR": ".DE",
        "HK": ".HK", "CN": ".TO", "AU": ".AX", "FP": ".PA", "SJ": ".JO",
        "IJ": ".JK", "BZ": ".SA", "KS": ".KS", "NA": ".AS", "SS": ".SS",
        "IN": ".NS", "IM": ".MI", "MM": ".MX", "TT": ".TW", "TB": ".BK",
        "DC": ".CO", "BB": ".BR", "PM": ".PS", "MK": ".KL", "SM": ".MC",
        "NO": ".OL", "FH": ".HE", "PL": ".WA", "NR": "", "NQ": "", "QM": "",
        "GK": "", "LI": "", "TI": "",
    }
    _manual_bbg_to_yf = {
        "GSK": "GSK", "AZN": "AZN", "BA/": "BAESY", "DGE": "DEO",
        "BATS": None, "PRU": "PUK", "CBG": None, "STJ": None,
        "RB/": "RBGLY", "VOD": "VOD", "ULVR": "UL", "ABI": "BUD",
        "SAB": None, "SKY": None, "ARM": None, "ADN": None,
        "NESN": "NSRGY", "NOVN": "NVS", "ROG": "RHHBY", "SCMN": None,
        "SAP": "SAP", "BAYN": None, "CON": None, "HNR1": None,
        "IFC": None, "DHL": None, "CBA": None, "CPI": None,
        "005930": None, "COLOB": None,
    }

    def _bbg_to_yf(bbg_ticker: str) -> str | None:
        if not bbg_ticker:
            return None
        parts = bbg_ticker.split()
        if len(parts) < 3:
            return None
        short, exchange = parts[0], parts[1]
        if short in _manual_bbg_to_yf:
            return _manual_bbg_to_yf[short]
        suffix = _exchange_map.get(exchange, "")
        return f"{short}{suffix}" if suffix or exchange in ("US", "NR", "NQ") else short

    # Build MCap weights for US-only stocks
    _valid_cols = set(_univ_close.columns)
    _valid_cols = {c for c in _valid_cols if _univ_close[c].dropna().shape[0] >= 252}

    _us_yf_weights: dict[str, float] = {}
    _us_yf_sectors: dict[str, str] = {}
    _total_us_mcap = 0.0

    for _k, _entries in universe_data.items():
        _e = _entries[0]
        _bbg = _e.get("Bloomberg_Ticker", "")
        _mcap = _e.get("MSCI_Mkt_Cap_USD_MM", 0)
        if not _bbg or _mcap <= 0:
            continue
        _parts = _bbg.split()
        if len(_parts) < 3:
            continue
        _short = _parts[0]

        # Only US stocks
        if _short not in us_short_tickers:
            continue

        _yft = _bbg_to_yf(_bbg)
        if _yft and _yft in _valid_cols:
            _us_yf_weights[_yft] = _us_yf_weights.get(_yft, 0) + _mcap
            _us_yf_sectors[_yft] = _e["GICS_Sector"]
            _total_us_mcap += _mcap

    # Normalize weights
    for _t in _us_yf_weights:
        _us_yf_weights[_t] /= _total_us_mcap

    # Compute benchmark return
    _bench_cols = list(_us_yf_weights.keys())
    _bench_close = _univ_close[_bench_cols].ffill()
    _bench_daily = _bench_close.pct_change().iloc[1:].clip(-0.5, 0.5)
    _w_ser = pd.Series(_us_yf_weights).reindex(_bench_daily.columns).fillna(0)
    _w_ser = _w_ser / _w_ser.sum()
    us_universe_ret = (_bench_daily.fillna(0) * _w_ser).sum(axis=1)
    us_universe_ret.name = "us_universe"

    # Also compute full universe benchmark for comparison
    _all_yf_weights: dict[str, float] = {}
    _total_all_mcap = 0.0
    for _k, _entries in universe_data.items():
        _e = _entries[0]
        _bbg = _e.get("Bloomberg_Ticker", "")
        _mcap = _e.get("MSCI_Mkt_Cap_USD_MM", 0)
        if not _bbg or _mcap <= 0:
            continue
        _yft = _bbg_to_yf(_bbg)
        if _yft and _yft in _valid_cols:
            _all_yf_weights[_yft] = _all_yf_weights.get(_yft, 0) + _mcap
            _total_all_mcap += _mcap
    for _t in _all_yf_weights:
        _all_yf_weights[_t] /= _total_all_mcap
    _all_cols = list(_all_yf_weights.keys())
    _all_close = _univ_close[_all_cols].ffill()
    _all_daily = _all_close.pct_change().iloc[1:].clip(-0.5, 0.5)
    _all_w_ser = pd.Series(_all_yf_weights).reindex(_all_daily.columns).fillna(0)
    _all_w_ser = _all_w_ser / _all_w_ser.sum()
    full_universe_ret = (_all_daily.fillna(0) * _all_w_ser).sum(axis=1)
    full_universe_ret.name = "full_universe"

    us_univ_sectors = _us_yf_sectors
    us_univ_weights = _us_yf_weights

    mo.md(
        f"""
    ### US-Only Universe Benchmark

    | Item | Value |
    |------|-------|
    | US-Only Universe Stocks | **{len(_bench_cols)}** (with sufficient price data) |
    | Full Universe Stocks | {len(_all_cols)} |
    | US MCap (of available) | {_total_us_mcap:,.0f} MM USD |
    | Period | {_bench_daily.index.min().date()} ~ {_bench_daily.index.max().date()} |
    | Rows | {len(_bench_daily):,} |
    """
    )
    return (
        full_universe_ret,
        us_univ_sectors,
        us_univ_weights,
        us_universe_ret,
    )


@app.cell
def _(PORTFOLIO_SIZE, RETURN_CAP, Path, mo, np, pd, us_short_tickers):
    """Build US-Only Portfolio."""
    _size = PORTFOLIO_SIZE.value
    _cap = RETURN_CAP.value
    _base_dir = Path("../data/raw/yfinance/stocks")
    _weights_dir = Path("../research/ca_strategy_poc/workspaces/full_run/output")

    # File naming
    if _size == "30":
        _price_file = "ca_portfolio_close_prices.parquet"
        _weights_file = "portfolio_weights.csv"
    else:
        _price_file = f"ca_portfolio_{_size}_close_prices.parquet"
        _weights_file = f"portfolio_weights_{_size}.csv"

    _price_path = _base_dir / _price_file
    _weights_path = _weights_dir / _weights_file

    if not _price_path.exists():
        mo.stop(True, mo.md(f"**Error**: `{_price_path}` が見つかりません。"))

    # Load price data
    close_prices_all = pd.read_parquet(_price_path)
    if not isinstance(close_prices_all.index, pd.DatetimeIndex):
        close_prices_all.index = pd.DatetimeIndex(close_prices_all.index)

    # Load weights
    if _weights_path.exists():
        weights_all = pd.read_csv(_weights_path)
    else:
        weights_all = pd.DataFrame(
            {"ticker": close_prices_all.columns, "weight": 1.0 / len(close_prices_all.columns)}
        )

    # Known non-US tickers (from instructions)
    _known_non_us = {
        "ITV", "CCEP", "ENB", "IFC", "HNR1", "CSL", "BAYN", "SHP", "CPI",
        "AMS", "SAP", "SCMN", "FTI", "ROG", "COLOB", "DHL", "ASML", "NESN",
        "KBC", "CON", "MC", "OR", "ITUB4", "AGU", "QIA", "BXB", "NOVN",
        "005930", "SOL", "CBA", "CBG", "ML", "BATS", "RADL3",
    }

    # Blacklist tickers with bad data
    _blacklist = {"IFC", "DHL", "CBA", "CON", "CPI"}

    # Identify US tickers: in us_short_tickers OR not in known_non_us
    # Use a conservative approach: ticker is US if it's in the universe US set
    # or manually added US set, AND not in known_non_us
    _all_tickers = set(close_prices_all.columns)

    _us_tickers = []
    _non_us_tickers = []
    for _t in _all_tickers:
        if _t in _blacklist:
            continue
        if _t in _known_non_us:
            _non_us_tickers.append(_t)
        elif _t in us_short_tickers:
            _us_tickers.append(_t)
        else:
            # Tickers not in either list - check if they appear in portfolio
            # but not in universe (e.g., delisted/renamed US stocks)
            # Default: if not in known_non_us list, treat as potentially US
            # but only if they have valid data
            if not close_prices_all[_t].isna().all():
                _us_tickers.append(_t)
            else:
                _non_us_tickers.append(_t)

    _us_tickers = sorted(_us_tickers)

    # --- Full portfolio (for comparison later) ---
    _full_valid = [
        t for t in close_prices_all.columns
        if t not in _blacklist and not close_prices_all[t].isna().all()
    ]
    full_close = close_prices_all[_full_valid].ffill()
    full_returns = full_close.pct_change().iloc[1:].clip(-_cap, _cap)
    full_weights_df = weights_all[weights_all["ticker"].isin(_full_valid)].copy()
    _full_total_w = full_weights_df["weight"].sum()
    full_weights_df["weight"] = full_weights_df["weight"] / _full_total_w
    _full_w = full_weights_df.set_index("ticker")["weight"]
    _full_aligned = _full_w.reindex(full_returns.columns).fillna(0)
    _full_aligned = _full_aligned / _full_aligned.sum()
    full_port_ret = (full_returns.fillna(0) * _full_aligned).sum(axis=1)
    full_port_ret.name = "full_portfolio"

    # --- US-Only portfolio ---
    _us_valid = [t for t in _us_tickers if not close_prices_all[t].isna().all()]
    us_close = close_prices_all[_us_valid].ffill()
    us_daily_returns = us_close.pct_change().iloc[1:].clip(-_cap, _cap)

    us_weights_df = weights_all[weights_all["ticker"].isin(_us_valid)].copy()
    _orig_us_weight = us_weights_df["weight"].sum()
    _orig_total_weight = weights_all["weight"].sum()
    us_weights_df["weight"] = us_weights_df["weight"] / _orig_us_weight  # renormalize to 1.0

    _us_w = us_weights_df.set_index("ticker")["weight"]
    _us_aligned = _us_w.reindex(us_daily_returns.columns).fillna(0)
    _us_aligned = _us_aligned / _us_aligned.sum()
    us_port_ret = (us_daily_returns.fillna(0) * _us_aligned).sum(axis=1)
    us_port_ret.name = "us_portfolio"

    mo.md(
        f"""
    ### US-Only Portfolio ({_size}-stock)

    | Item | Value |
    |------|-------|
    | Original Portfolio | {len(weights_all)} stocks |
    | US-Only Portfolio | **{len(_us_valid)}** stocks |
    | Removed (non-US) | {sorted(_non_us_tickers)} |
    | Removed (blacklist) | {sorted(_blacklist & _all_tickers)} |
    | Original US Weight | {_orig_us_weight:.1%} of total |
    | Period | {us_close.index.min().date()} ~ {us_close.index.max().date()} |

    **US tickers**: {', '.join(sorted(_us_valid))}
    """
    )
    return (
        close_prices_all,
        full_port_ret,
        full_returns,
        full_weights_df,
        us_close,
        us_daily_returns,
        us_port_ret,
        us_weights_df,
        weights_all,
    )


@app.cell
def _(Path, RETURN_CAP, RISK_FREE_RATE, mo, np, pd, us_port_ret, us_universe_ret):
    """Performance Summary Table: US-Only Portfolio vs US-Only Universe vs MSCI Kokusai."""
    _rf = RISK_FREE_RATE.value
    _cap = RETURN_CAP.value
    _ann = 252

    # Load MSCI Kokusai (TOK)
    _bench_path = Path("../data/raw/yfinance/stocks/msci_benchmark_close_prices.parquet")
    if not _bench_path.exists():
        mo.stop(True, mo.md("**Error**: MSCI benchmark データが見つかりません。"))

    _bench_close = pd.read_parquet(_bench_path)
    _tok = _bench_close["TOK"].ffill()
    msci_ret = _tok.pct_change().iloc[1:].clip(-_cap, _cap)
    msci_ret.name = "msci_kokusai"

    # Align all three
    _aligned = pd.concat(
        [us_port_ret, us_universe_ret, msci_ret],
        axis=1,
    ).dropna()

    _p = _aligned["us_portfolio"]
    _u = _aligned["us_universe"]
    _m = _aligned["msci_kokusai"]
    _n_yr = len(_aligned) / _ann

    def _metrics(ret: pd.Series, name: str, bench: pd.Series | None = None) -> dict:
        excess = ret - _rf / _ann
        std = ret.std()
        cum = (1 + ret).cumprod()
        cum_ret = float((1 + ret).prod() - 1)
        n_yr = len(ret) / _ann
        ann_ret = float((1 + cum_ret) ** (1 / n_yr) - 1) if n_yr > 0 else 0
        ann_vol = float(std * np.sqrt(_ann))
        sharpe = float(excess.mean() / std * np.sqrt(_ann)) if std > 0 else 0
        max_dd = float((cum / cum.cummax() - 1).min())

        # Sortino
        down = ret[ret < 0]
        down_std = float(down.std() * np.sqrt(_ann)) if len(down) > 0 else 1
        sortino = float((ret.mean() * _ann - _rf) / down_std)

        # Calmar
        calmar = ann_ret / abs(max_dd) if max_dd != 0 else 0

        # Win rate (vs 0)
        win_rate = float((ret > 0).mean())

        result = {
            "Name": name,
            "Sharpe": round(sharpe, 4),
            "Sortino": round(sortino, 4),
            "Calmar": round(calmar, 4),
            "Max DD": round(max_dd, 4),
            "Cum. Return": round(cum_ret, 4),
            "Ann. Return": round(ann_ret, 4),
            "Ann. Vol": round(ann_vol, 4),
            "Win Rate": round(win_rate, 4),
        }

        if bench is not None:
            active = ret - bench
            cov = np.cov(ret, bench)
            beta = float(cov[0, 1] / cov[1, 1]) if cov[1, 1] > 0 else 1.0
            ann_b = float((1 + float((1 + bench).prod() - 1)) ** (1 / n_yr) - 1) if n_yr > 0 else 0
            alpha = ann_ret - (_rf + beta * (ann_b - _rf))
            te = float(active.std() * np.sqrt(_ann))
            ir = float(active.mean() / active.std() * np.sqrt(_ann)) if active.std() > 0 else 0

            # Up/Down capture
            up_mask = bench > 0
            dn_mask = bench < 0
            up_cap = float(ret[up_mask].mean() / bench[up_mask].mean() * 100) if bench[up_mask].mean() != 0 else 0
            dn_cap = float(ret[dn_mask].mean() / bench[dn_mask].mean() * 100) if bench[dn_mask].mean() != 0 else 0

            result.update({
                "Beta": round(beta, 4),
                "Alpha": round(alpha, 4),
                "TE": round(te, 4),
                "IR": round(ir, 4),
                "Up Cap": round(up_cap, 1),
                "Dn Cap": round(dn_cap, 1),
            })

        return result

    _port_vs_univ = _metrics(_p, "US-Only Portfolio", _u)
    _port_vs_msci = _metrics(_p, "US-Only Portfolio", _m)
    _univ_metrics = _metrics(_u, "US-Only Universe", _m)
    _msci_metrics = _metrics(_m, "MSCI Kokusai")

    mo.md(
        f"""
    ### Performance Summary: US-Only Analysis

    #### Core Metrics

    | Metric | US-Only Portfolio | US-Only Universe | MSCI Kokusai |
    |--------|:-:|:-:|:-:|
    | **Sharpe Ratio** | {_port_vs_msci['Sharpe']:.4f} | {_univ_metrics['Sharpe']:.4f} | {_msci_metrics['Sharpe']:.4f} |
    | **Sortino Ratio** | {_port_vs_msci['Sortino']:.4f} | {_univ_metrics['Sortino']:.4f} | {_msci_metrics['Sortino']:.4f} |
    | **Calmar Ratio** | {_port_vs_msci['Calmar']:.4f} | {_univ_metrics['Calmar']:.4f} | {_msci_metrics['Calmar']:.4f} |
    | **Max Drawdown** | {_port_vs_msci['Max DD']:.2%} | {_univ_metrics['Max DD']:.2%} | {_msci_metrics['Max DD']:.2%} |
    | **Cum. Return** | {_port_vs_msci['Cum. Return']:.2%} | {_univ_metrics['Cum. Return']:.2%} | {_msci_metrics['Cum. Return']:.2%} |
    | **Ann. Return** | {_port_vs_msci['Ann. Return']:.2%} | {_univ_metrics['Ann. Return']:.2%} | {_msci_metrics['Ann. Return']:.2%} |
    | **Ann. Volatility** | {_port_vs_msci['Ann. Vol']:.2%} | {_univ_metrics['Ann. Vol']:.2%} | {_msci_metrics['Ann. Vol']:.2%} |
    | **Win Rate (日次)** | {_port_vs_msci['Win Rate']:.1%} | {_univ_metrics['Win Rate']:.1%} | {_msci_metrics['Win Rate']:.1%} |

    #### vs MSCI Kokusai

    | Metric | US-Only Portfolio | US-Only Universe |
    |--------|:-:|:-:|
    | **Beta** | {_port_vs_msci['Beta']:.4f} | {_univ_metrics['Beta']:.4f} |
    | **Alpha (CAPM)** | {_port_vs_msci['Alpha']:+.2%} | {_univ_metrics['Alpha']:+.2%} |
    | **Tracking Error** | {_port_vs_msci['TE']:.2%} | {_univ_metrics['TE']:.2%} |
    | **Information Ratio** | {_port_vs_msci['IR']:.4f} | {_univ_metrics['IR']:.4f} |
    | **Up Capture** | {_port_vs_msci['Up Cap']:.1f}% | {_univ_metrics['Up Cap']:.1f}% |
    | **Down Capture** | {_port_vs_msci['Dn Cap']:.1f}% | {_univ_metrics['Dn Cap']:.1f}% |

    #### vs US-Only Universe

    | Metric | US-Only Portfolio |
    |--------|:-:|
    | **Beta** | {_port_vs_univ['Beta']:.4f} |
    | **Alpha (CAPM)** | {_port_vs_univ['Alpha']:+.2%} |
    | **Tracking Error** | {_port_vs_univ['TE']:.2%} |
    | **Information Ratio** | {_port_vs_univ['IR']:.4f} |
    | **Up Capture** | {_port_vs_univ['Up Cap']:.1f}% |
    | **Down Capture** | {_port_vs_univ['Dn Cap']:.1f}% |
    """
    )
    return (msci_ret,)


@app.cell
def _(RISK_FREE_RATE, full_port_ret, mo, np, pd, us_port_ret):
    """Comparison Table: Full Portfolio vs US-Only Portfolio."""
    _rf = RISK_FREE_RATE.value
    _ann = 252

    _aligned = pd.concat(
        [full_port_ret.rename("full"), us_port_ret.rename("us")],
        axis=1,
    ).dropna()

    _full = _aligned["full"]
    _us = _aligned["us"]
    _n_yr = len(_aligned) / _ann

    def _compute(ret: pd.Series) -> dict:
        excess = ret - _rf / _ann
        std = ret.std()
        cum = (1 + ret).cumprod()
        cum_ret = float((1 + ret).prod() - 1)
        n_yr = len(ret) / _ann
        ann_ret = float((1 + cum_ret) ** (1 / n_yr) - 1) if n_yr > 0 else 0
        ann_vol = float(std * np.sqrt(_ann))
        sharpe = float(excess.mean() / std * np.sqrt(_ann)) if std > 0 else 0
        max_dd = float((cum / cum.cummax() - 1).min())
        down = ret[ret < 0]
        down_std = float(down.std() * np.sqrt(_ann)) if len(down) > 0 else 1
        sortino = float((ret.mean() * _ann - _rf) / down_std)
        calmar = ann_ret / abs(max_dd) if max_dd != 0 else 0
        return {
            "sharpe": sharpe,
            "sortino": sortino,
            "calmar": calmar,
            "max_dd": max_dd,
            "cum_ret": cum_ret,
            "ann_ret": ann_ret,
            "ann_vol": ann_vol,
        }

    _f = _compute(_full)
    _u = _compute(_us)

    mo.md(
        f"""
    ### Full Portfolio vs US-Only Portfolio

    | Metric | Full Portfolio | US-Only Portfolio | Difference |
    |--------|:-:|:-:|:-:|
    | **Sharpe Ratio** | {_f['sharpe']:.4f} | {_u['sharpe']:.4f} | {_u['sharpe'] - _f['sharpe']:+.4f} |
    | **Sortino Ratio** | {_f['sortino']:.4f} | {_u['sortino']:.4f} | {_u['sortino'] - _f['sortino']:+.4f} |
    | **Calmar Ratio** | {_f['calmar']:.4f} | {_u['calmar']:.4f} | {_u['calmar'] - _f['calmar']:+.4f} |
    | **Max Drawdown** | {_f['max_dd']:.2%} | {_u['max_dd']:.2%} | {_u['max_dd'] - _f['max_dd']:+.2%} |
    | **Cum. Return** | {_f['cum_ret']:.2%} | {_u['cum_ret']:.2%} | {_u['cum_ret'] - _f['cum_ret']:+.2%} |
    | **Ann. Return** | {_f['ann_ret']:.2%} | {_u['ann_ret']:.2%} | {_u['ann_ret'] - _f['ann_ret']:+.2%} |
    | **Ann. Volatility** | {_f['ann_vol']:.2%} | {_u['ann_vol']:.2%} | {_u['ann_vol'] - _f['ann_vol']:+.2%} |

    > Positive difference = US-Only is better than Full.
    > Negative difference = Full is better than US-Only.
    """
    )
    return


@app.cell
def _(mo, msci_ret, np, pd, us_port_ret, us_universe_ret):
    """Yearly Returns Table: US-Only Portfolio vs US Universe vs MSCI Kokusai."""
    _aligned = pd.concat(
        [us_port_ret.rename("port"), us_universe_ret.rename("univ"), msci_ret.rename("msci")],
        axis=1,
    ).dropna()

    _rows = []
    for _y in sorted(_aligned.index.year.unique()):
        _yp = _aligned.loc[_aligned.index.year == _y, "port"]
        _yu = _aligned.loc[_aligned.index.year == _y, "univ"]
        _ym = _aligned.loc[_aligned.index.year == _y, "msci"]
        rp = float((1 + _yp).prod() - 1)
        ru = float((1 + _yu).prod() - 1)
        rm = float((1 + _ym).prod() - 1)
        _rows.append(
            {
                "Year": str(_y),
                "US Portfolio": f"{rp:+.2%}",
                "US Universe": f"{ru:+.2%}",
                "MSCI Kokusai": f"{rm:+.2%}",
                "Active vs Univ": f"{rp - ru:+.2%}",
                "Active vs MSCI": f"{rp - rm:+.2%}",
            }
        )

    yearly_us_df = pd.DataFrame(_rows)
    mo.md("### Yearly Returns: US-Only")
    return (yearly_us_df,)


@app.cell
def _(mo, yearly_us_df):
    """Display yearly returns table."""
    mo.ui.table(yearly_us_df, selection=None)
    return


@app.cell
def _(mo, msci_ret, pd, us_port_ret, us_universe_ret):
    """Cumulative Return Chart: US-Only Portfolio vs US Universe vs MSCI Kokusai."""
    import plotly.graph_objects as go

    _aligned = pd.concat(
        [us_port_ret.rename("port"), us_universe_ret.rename("univ"), msci_ret.rename("msci")],
        axis=1,
    ).dropna()

    _cum_p = (1 + _aligned["port"]).cumprod()
    _cum_u = (1 + _aligned["univ"]).cumprod()
    _cum_m = (1 + _aligned["msci"]).cumprod()

    fig_cum = go.Figure()
    fig_cum.add_trace(
        go.Scatter(
            x=_cum_p.index,
            y=_cum_p.values,
            name="US-Only Portfolio",
            mode="lines",
            line={"width": 2.5, "color": "#2563eb"},
        )
    )
    fig_cum.add_trace(
        go.Scatter(
            x=_cum_u.index,
            y=_cum_u.values,
            name="US-Only Universe",
            mode="lines",
            line={"width": 2, "dash": "dash", "color": "#d97706"},
        )
    )
    fig_cum.add_trace(
        go.Scatter(
            x=_cum_m.index,
            y=_cum_m.values,
            name="MSCI Kokusai (TOK)",
            mode="lines",
            line={"width": 2, "dash": "dot", "color": "#dc2626"},
        )
    )

    fig_cum.update_layout(
        title="Cumulative Returns: US-Only Portfolio vs Benchmarks",
        xaxis_title="Date",
        yaxis_title="Growth of $1",
        template="plotly_white",
        height=500,
    )

    mo.ui.plotly(fig_cum)
    return (fig_cum,)


@app.cell
def _(mo, msci_ret, pd, us_port_ret, us_universe_ret):
    """Drawdown Chart: US-Only Portfolio vs benchmarks."""
    import plotly.graph_objects as go

    _aligned = pd.concat(
        [us_port_ret.rename("port"), us_universe_ret.rename("univ"), msci_ret.rename("msci")],
        axis=1,
    ).dropna()

    def _drawdown(ret: pd.Series) -> pd.Series:
        cum = (1 + ret).cumprod()
        return (cum / cum.cummax() - 1) * 100

    _dd_p = _drawdown(_aligned["port"])
    _dd_u = _drawdown(_aligned["univ"])
    _dd_m = _drawdown(_aligned["msci"])

    fig_dd = go.Figure()
    fig_dd.add_trace(
        go.Scatter(
            x=_dd_p.index,
            y=_dd_p.values,
            fill="tozeroy",
            name="US-Only Portfolio",
            line={"color": "#2563eb"},
            fillcolor="rgba(37, 99, 235, 0.15)",
        )
    )
    fig_dd.add_trace(
        go.Scatter(
            x=_dd_u.index,
            y=_dd_u.values,
            name="US-Only Universe",
            mode="lines",
            line={"color": "#d97706", "dash": "dash"},
        )
    )
    fig_dd.add_trace(
        go.Scatter(
            x=_dd_m.index,
            y=_dd_m.values,
            name="MSCI Kokusai",
            mode="lines",
            line={"color": "#dc2626", "dash": "dot"},
        )
    )

    fig_dd.update_layout(
        title="Drawdown: US-Only Portfolio vs Benchmarks",
        xaxis_title="Date",
        yaxis_title="Drawdown (%)",
        template="plotly_white",
        height=450,
    )

    mo.ui.plotly(fig_dd)
    return (fig_dd,)


@app.cell
def _(mo, msci_ret, np, pd, us_port_ret):
    """Rolling 1Y Active Return vs MSCI Kokusai."""
    import plotly.graph_objects as go
    from plotly.subplots import make_subplots

    _aligned = pd.concat(
        [us_port_ret.rename("port"), msci_ret.rename("msci")],
        axis=1,
    ).dropna()

    _active = _aligned["port"] - _aligned["msci"]
    _w = 252

    _rolling_active = _active.rolling(_w).mean() * 252 * 100
    _rolling_te = _active.rolling(_w).std() * np.sqrt(252) * 100
    _rolling_ir = _rolling_active / _rolling_te

    fig_rolling = make_subplots(
        rows=3,
        cols=1,
        shared_xaxes=True,
        subplot_titles=[
            "Rolling 1Y Active Return vs MSCI Kokusai (%)",
            "Rolling 1Y Tracking Error (%)",
            "Rolling 1Y Information Ratio",
        ],
        vertical_spacing=0.08,
    )

    fig_rolling.add_trace(
        go.Scatter(
            x=_rolling_active.index,
            y=_rolling_active,
            name="Active Return",
            line={"color": "#2563eb"},
        ),
        row=1,
        col=1,
    )
    fig_rolling.add_hline(y=0, line_dash="dash", line_color="gray", row=1, col=1)

    fig_rolling.add_trace(
        go.Scatter(
            x=_rolling_te.index,
            y=_rolling_te,
            name="Tracking Error",
            line={"color": "orange"},
        ),
        row=2,
        col=1,
    )

    fig_rolling.add_trace(
        go.Scatter(
            x=_rolling_ir.index,
            y=_rolling_ir,
            name="Info Ratio",
            line={"color": "green"},
        ),
        row=3,
        col=1,
    )
    fig_rolling.add_hline(y=0, line_dash="dash", line_color="gray", row=3, col=1)

    fig_rolling.update_layout(
        height=800,
        template="plotly_white",
        showlegend=False,
        title_text="Rolling 1-Year Active Performance vs MSCI Kokusai (US-Only)",
    )

    mo.ui.plotly(fig_rolling)
    return (fig_rolling,)


@app.cell
def _(PORTFOLIO_SIZE, mo, pd, us_weights_df, weights_all):
    """Sector Weights Comparison: Full vs US-Only Portfolio."""
    import plotly.graph_objects as go

    _size = PORTFOLIO_SIZE.value

    # Full portfolio sector weights
    if "sector" not in weights_all.columns:
        mo.stop(True, mo.md("**Warning**: sector column not available in weights CSV."))

    _full_sector = weights_all.groupby("sector")["weight"].sum()
    _full_sector = _full_sector / _full_sector.sum()

    # US-only sector weights
    _us_sector = us_weights_df.groupby("sector")["weight"].sum()
    _us_sector = _us_sector / _us_sector.sum()

    # Combine
    _sectors = sorted(set(_full_sector.index) | set(_us_sector.index))
    _full_vals = [_full_sector.get(s, 0) for s in _sectors]
    _us_vals = [_us_sector.get(s, 0) for s in _sectors]

    fig_sector = go.Figure()
    fig_sector.add_trace(
        go.Bar(
            name=f"Full Portfolio ({_size})",
            x=_sectors,
            y=[v * 100 for v in _full_vals],
            marker_color="#6b7280",
        )
    )
    fig_sector.add_trace(
        go.Bar(
            name="US-Only Portfolio",
            x=_sectors,
            y=[v * 100 for v in _us_vals],
            marker_color="#2563eb",
        )
    )

    fig_sector.update_layout(
        title=f"Sector Weights: Full vs US-Only ({_size}-stock)",
        xaxis_title="Sector",
        yaxis_title="Weight (%)",
        barmode="group",
        template="plotly_white",
        height=450,
    )

    # Also build a comparison table
    _table_rows = []
    for _s in _sectors:
        _fv = _full_sector.get(_s, 0)
        _uv = _us_sector.get(_s, 0)
        _table_rows.append(
            {
                "Sector": _s,
                "Full (%)": f"{_fv:.1%}",
                "US-Only (%)": f"{_uv:.1%}",
                "Diff (pp)": f"{(_uv - _fv) * 100:+.1f}",
            }
        )

    _sector_df = pd.DataFrame(_table_rows)

    mo.vstack([
        mo.md(f"### Sector Weights: Full vs US-Only ({_size}-stock)"),
        mo.ui.plotly(fig_sector),
        mo.ui.table(_sector_df, selection=None),
    ])
    return (fig_sector,)


@app.cell
def _(
    PORTFOLIO_SIZE,
    Path,
    RISK_FREE_RATE,
    datetime,
    json,
    mo,
    msci_ret,
    np,
    pd,
    us_close,
    us_daily_returns,
    us_port_ret,
    us_universe_ret,
    us_weights_df,
):
    """Export results as JSON."""
    _size = PORTFOLIO_SIZE.value
    _rf = RISK_FREE_RATE.value
    _ann = 252

    # Aligned returns
    _aligned = pd.concat(
        [us_port_ret.rename("port"), us_universe_ret.rename("univ"), msci_ret.rename("msci")],
        axis=1,
    ).dropna()

    _p = _aligned["port"]
    _u = _aligned["univ"]
    _m = _aligned["msci"]
    _n_yr = len(_aligned) / _ann

    # Portfolio metrics
    _excess = _p - _rf / _ann
    _std = _p.std()
    _cum_ret = float((1 + _p).prod() - 1)
    _ann_ret = float((1 + _cum_ret) ** (1 / _n_yr) - 1) if _n_yr > 0 else 0
    _ann_vol = float(_std * np.sqrt(_ann))
    _sharpe = float(_excess.mean() / _std * np.sqrt(_ann)) if _std > 0 else 0
    _cum_curve = (1 + _p).cumprod()
    _max_dd = float((_cum_curve / _cum_curve.cummax() - 1).min())

    # vs MSCI
    _active_msci = _p - _m
    _te_msci = float(_active_msci.std() * np.sqrt(_ann))
    _ir_msci = float(_active_msci.mean() / _active_msci.std() * np.sqrt(_ann)) if _active_msci.std() > 0 else 0
    _cov_msci = np.cov(_p, _m)
    _beta_msci = float(_cov_msci[0, 1] / _cov_msci[1, 1]) if _cov_msci[1, 1] > 0 else 1.0
    _ann_m = float((1 + float((1 + _m).prod() - 1)) ** (1 / _n_yr) - 1)
    _alpha_msci = _ann_ret - (_rf + _beta_msci * (_ann_m - _rf))

    # vs Universe
    _active_univ = _p - _u
    _te_univ = float(_active_univ.std() * np.sqrt(_ann))
    _ir_univ = float(_active_univ.mean() / _active_univ.std() * np.sqrt(_ann)) if _active_univ.std() > 0 else 0
    _cov_univ = np.cov(_p, _u)
    _beta_univ = float(_cov_univ[0, 1] / _cov_univ[1, 1]) if _cov_univ[1, 1] > 0 else 1.0
    _ann_u = float((1 + float((1 + _u).prod() - 1)) ** (1 / _n_yr) - 1)
    _alpha_univ = _ann_ret - (_rf + _beta_univ * (_ann_u - _rf))

    # Yearly
    _yearly = {}
    for _y in sorted(_aligned.index.year.unique()):
        _yp = _aligned.loc[_aligned.index.year == _y, "port"]
        _yearly[str(_y)] = round(float((1 + _yp).prod() - 1), 4)

    # Per-stock
    _weights = us_weights_df.set_index("ticker")
    _per_stock = {}
    for col in us_daily_returns.columns:
        r = us_daily_returns[col].dropna()
        if len(r) > 0 and col in _weights.index:
            cum_r = float((1 + r).prod() - 1)
            n_yr = len(r) / _ann
            _per_stock[col] = {
                "weight": round(float(_weights.loc[col, "weight"]), 4),
                "sector": _weights.loc[col, "sector"] if "sector" in _weights.columns else "",
                "score": round(float(_weights.loc[col, "score"]), 4) if "score" in _weights.columns else 0,
                "cum_return": round(cum_r, 4),
                "ann_return": round(float((1 + cum_r) ** (1 / n_yr) - 1) if n_yr > 0 else 0, 4),
            }

    export_result = {
        "analysis_type": "us_only",
        "portfolio": f"ca_strategy_{_size}_stock_us_only",
        "evaluated_at": datetime.now().isoformat(),
        "period": {
            "start": str(us_close.index.min().date()),
            "end": str(us_close.index.max().date()),
        },
        "config": {
            "weights": "score_weighted_sector_neutral_us_only",
            "risk_free_rate": _rf,
            "active_holdings": len(us_daily_returns.columns),
        },
        "performance": {
            "sharpe_ratio": round(_sharpe, 4),
            "max_drawdown": round(_max_dd, 4),
            "cumulative_return": round(_cum_ret, 4),
            "annualized_return": round(_ann_ret, 4),
            "annualized_volatility": round(_ann_vol, 4),
        },
        "vs_msci_kokusai": {
            "beta": round(_beta_msci, 4),
            "alpha": round(_alpha_msci, 4),
            "tracking_error": round(_te_msci, 4),
            "information_ratio": round(_ir_msci, 4),
        },
        "vs_us_universe": {
            "beta": round(_beta_univ, 4),
            "alpha": round(_alpha_univ, 4),
            "tracking_error": round(_te_univ, 4),
            "information_ratio": round(_ir_univ, 4),
        },
        "yearly_returns": _yearly,
        "per_stock": _per_stock,
    }

    _output_dir = Path("../data/processed/evaluation/yfinance")
    _output_dir.mkdir(parents=True, exist_ok=True)
    _out_name = f"ca_portfolio_{_size}_us_only_evaluation.json"
    _output_path = _output_dir / _out_name
    _output_path.write_text(json.dumps(export_result, indent=2, ensure_ascii=False))

    mo.md(
        f"""
    ### Evaluation Exported

    **Path**: `data/processed/evaluation/yfinance/{_out_name}`

    ```json
    {{
      "analysis_type": "us_only",
      "portfolio": "{export_result['portfolio']}",
      "active_holdings": {export_result['config']['active_holdings']},
      "sharpe_ratio": {export_result['performance']['sharpe_ratio']},
      "annualized_return": {export_result['performance']['annualized_return']:.4f},
      "max_drawdown": {export_result['performance']['max_drawdown']:.4f},
      "alpha_vs_msci": {export_result['vs_msci_kokusai']['alpha']:.4f},
      "ir_vs_msci": {export_result['vs_msci_kokusai']['information_ratio']:.4f},
      "alpha_vs_us_univ": {export_result['vs_us_universe']['alpha']:.4f},
      "ir_vs_us_univ": {export_result['vs_us_universe']['information_ratio']:.4f}
    }}
    ```
    """
    )
    return (export_result,)


if __name__ == "__main__":
    app.run()
