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
    from pathlib import Path

    import marimo as mo
    import numpy as np
    import pandas as pd

    mo.md(
        """
    # CA Strategy Phase 6: Portfolio Performance Analysis

    **目的**: CA Strategy ポートフォリオ（30/60/90銘柄）の yfinance / Bloomberg データ評価

    - Performance: Sharpe, Max DD, Beta, IR, Cumulative Return
    - Portfolio Sizes: 30-stock (full_run), 60-stock, 90-stock
    - Data Source: yfinance（Bloomberg 差し替え対応）

    ---
    """
    )
    return Path, json, mo, np, pd


@app.cell
def _(mo):
    """Configuration controls."""
    DATA_SOURCE = mo.ui.dropdown(
        options=["yfinance", "bloomberg"],
        value="yfinance",
        label="Data Source",
    )

    PORTFOLIO_SIZE = mo.ui.dropdown(
        options=["30", "60", "90"],
        value="30",
        label="Portfolio Size",
    )

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

    mo.hstack([DATA_SOURCE, PORTFOLIO_SIZE, RISK_FREE_RATE, RETURN_CAP])
    return DATA_SOURCE, PORTFOLIO_SIZE, RETURN_CAP, RISK_FREE_RATE


@app.cell
def _(DATA_SOURCE, PORTFOLIO_SIZE, Path, json, mo, pd):
    """Load price data and portfolio weights."""
    _source = DATA_SOURCE.value
    _size = PORTFOLIO_SIZE.value
    _base_dir = Path("../data/raw")
    _weights_dir = Path("../research/ca_strategy_poc/workspaces/full_run/output")

    # Portfolio file naming convention
    if _size == "30":
        _price_file = f"ca_portfolio_close_prices.parquet"
        _meta_file = f"ca_portfolio_close_prices.meta.json"
        _weights_file = "portfolio_weights.csv"
    else:
        _price_file = f"ca_portfolio_{_size}_close_prices.parquet"
        _meta_file = f"ca_portfolio_{_size}_close_prices.meta.json"
        _weights_file = f"portfolio_weights_{_size}.csv"

    _price_path = _base_dir / _source / "stocks" / _price_file
    _meta_path = _base_dir / _source / "stocks" / _meta_file
    _weights_path = _weights_dir / _weights_file

    if not _price_path.exists():
        mo.stop(
            True,
            mo.md(
                f"""
        **Error**: `{_price_path}` が見つかりません。

        {_size}-stock ポートフォリオの {_source} データを用意してください。
        """
            ),
        )

    close_prices = pd.read_parquet(_price_path)
    if not isinstance(close_prices.index, pd.DatetimeIndex):
        close_prices.index = pd.DatetimeIndex(close_prices.index)

    # Load metadata
    _meta = {}
    if _meta_path.exists():
        _meta = json.loads(_meta_path.read_text())

    # Load portfolio weights
    if _weights_path.exists():
        portfolio_weights = pd.read_csv(_weights_path)
    else:
        portfolio_weights = pd.DataFrame(
            {"ticker": close_prices.columns, "weight": 1.0 / len(close_prices.columns)}
        )

    # Ticker mismatch blacklist (non-US tickers returning wrong data on yfinance)
    _blacklist = {"IFC", "DHL", "CBA", "CON", "CPI"}

    # Filter to active tickers (in close_prices, not blacklisted, has data)
    _valid_tickers = [
        t
        for t in close_prices.columns
        if t not in _blacklist and not close_prices[t].isna().all()
    ]
    close_prices = close_prices[_valid_tickers]

    # Filter weights
    portfolio_weights = portfolio_weights[
        portfolio_weights["ticker"].isin(_valid_tickers)
    ].copy()
    _total_w = portfolio_weights["weight"].sum()
    portfolio_weights["weight"] = portfolio_weights["weight"] / _total_w

    mo.md(
        f"""
    ### Data Loaded: {_size}-stock Portfolio

    | Item | Value |
    |------|-------|
    | Source | **{_source}** |
    | Portfolio Size | {_size} (active: {len(_valid_tickers)}) |
    | Period | {close_prices.index.min().date()} ~ {close_prices.index.max().date()} |
    | Rows | {len(close_prices):,} |
    | Weight Coverage | {_total_w:.1%} of original weights |
    | Blacklisted | {_blacklist & set(close_prices.columns) if _blacklist else 'None'} |
    """
    )
    return close_prices, portfolio_weights


@app.cell
def _(RETURN_CAP, close_prices, mo, np, pd, portfolio_weights):
    """Compute returns and portfolio metrics."""
    _cap = RETURN_CAP.value

    # Forward-fill, compute returns, cap extremes
    _close = close_prices.ffill()
    daily_returns = _close.pct_change().iloc[1:].clip(-_cap, _cap)

    # Weighted portfolio returns
    _weights = portfolio_weights.set_index("ticker")["weight"]
    _aligned = _weights.reindex(daily_returns.columns).fillna(0)
    _aligned = _aligned / _aligned.sum()  # renormalize

    weighted_returns = (daily_returns.fillna(0) * _aligned).sum(axis=1)
    weighted_returns.name = "weighted"

    # Equal-weight benchmark
    ew_returns = daily_returns.mean(axis=1)
    ew_returns.name = "equal_weight"

    mo.md("### Returns Computed")
    return daily_returns, ew_returns, weighted_returns


@app.cell
def _(RISK_FREE_RATE, daily_returns, ew_returns, mo, np, pd, weighted_returns):
    """Portfolio performance metrics table."""
    _rf = RISK_FREE_RATE.value
    _ann = 252

    def _compute_metrics(ret, name):
        excess = ret - _rf / _ann
        std = ret.std()
        cum = (1 + ret).cumprod()
        cum_ret = float((1 + ret).prod() - 1)
        n_years = len(ret) / _ann
        return {
            "Portfolio": name,
            "Sharpe": round(float(excess.mean() / std * np.sqrt(_ann)) if std > 0 else 0, 4),
            "Max DD": round(float((cum / cum.cummax() - 1).min()), 4),
            "Cum. Return": round(cum_ret, 4),
            "Ann. Return": round(float((1 + cum_ret) ** (1 / n_years) - 1) if n_years > 0 else 0, 4),
            "Ann. Vol": round(float(std * np.sqrt(_ann)), 4),
        }

    _rows = [
        _compute_metrics(weighted_returns, "Score-Weighted"),
        _compute_metrics(ew_returns, "Equal-Weight"),
    ]

    metrics_df = pd.DataFrame(_rows)

    # Beta & IR
    _aligned = pd.concat([weighted_returns, ew_returns], axis=1).dropna()
    if len(_aligned) > 1 and _aligned.iloc[:, 1].std() > 0:
        _cov = np.cov(_aligned.iloc[:, 0], _aligned.iloc[:, 1])
        _beta = round(float(_cov[0, 1] / _cov[1, 1]), 4)
    else:
        _beta = None

    _tracking = weighted_returns - ew_returns
    _te = _tracking.std()
    _ir = round(float(_tracking.mean() / _te * np.sqrt(_ann)), 4) if _te > 0 else None

    mo.md(
        f"""
    ### Performance Summary

    | Metric | Score-Weighted | Equal-Weight |
    |--------|:-:|:-:|
    | **Sharpe Ratio** | {_rows[0]['Sharpe']:.4f} | {_rows[1]['Sharpe']:.4f} |
    | **Max Drawdown** | {_rows[0]['Max DD']:.2%} | {_rows[1]['Max DD']:.2%} |
    | **Cumulative Return** | {_rows[0]['Cum. Return']:.2%} | {_rows[1]['Cum. Return']:.2%} |
    | **Ann. Return** | {_rows[0]['Ann. Return']:.2%} | {_rows[1]['Ann. Return']:.2%} |
    | **Ann. Volatility** | {_rows[0]['Ann. Vol']:.2%} | {_rows[1]['Ann. Vol']:.2%} |
    | **Beta vs EW** | {_beta} | — |
    | **Information Ratio** | {_ir} | — |
    """
    )
    return (metrics_df,)


@app.cell
def _(ew_returns, mo, np, pd, weighted_returns):
    """Yearly returns comparison."""
    _all_years = sorted(set(weighted_returns.index.year) | set(ew_returns.index.year))

    _yearly = []
    for y in _all_years:
        _wr = weighted_returns[weighted_returns.index.year == y]
        _er = ew_returns[ew_returns.index.year == y]
        _yearly.append(
            {
                "Year": str(y),
                "Score-Weighted": f"{float((1 + _wr).prod() - 1):+.2%}",
                "Equal-Weight": f"{float((1 + _er).prod() - 1):+.2%}",
                "Diff": f"{float((1 + _wr).prod() - (1 + _er).prod()):+.2%}",
            }
        )

    yearly_df = pd.DataFrame(_yearly)
    mo.md("### Yearly Returns")
    return (yearly_df,)


@app.cell
def _(mo, yearly_df):
    mo.ui.table(yearly_df)
    return


@app.cell
def _(daily_returns, ew_returns, mo, np, pd, portfolio_weights, weighted_returns):
    """Per-stock statistics table."""
    _ann = 252
    _weights = portfolio_weights.set_index("ticker")

    _rows = []
    for col in daily_returns.columns:
        r = daily_returns[col].dropna()
        if len(r) == 0:
            continue
        cum_r = float((1 + r).prod() - 1)
        n_yr = len(r) / _ann
        ann_r = float((1 + cum_r) ** (1 / n_yr) - 1) if n_yr > 0 else 0

        row = {
            "Ticker": col,
            "Weight (%)": round(_weights.loc[col, "weight"] * 100, 2) if col in _weights.index else 0,
            "Ann. Return (%)": round(ann_r * 100, 2),
            "Ann. Vol (%)": round(float(r.std() * np.sqrt(_ann) * 100), 2),
            "Cum. Return (%)": round(cum_r * 100, 2),
        }

        if "sector" in _weights.columns and col in _weights.index:
            row["Sector"] = _weights.loc[col, "sector"]
        if "score" in _weights.columns and col in _weights.index:
            row["Score"] = round(float(_weights.loc[col, "score"]), 3)

        _rows.append(row)

    stock_stats = pd.DataFrame(_rows).sort_values("Weight (%)", ascending=False)
    mo.md("### Per-Stock Statistics")
    return (stock_stats,)


@app.cell
def _(mo, stock_stats):
    mo.ui.table(stock_stats.reset_index(drop=True))
    return


@app.cell
def _(daily_returns, ew_returns, mo, weighted_returns):
    """Cumulative return chart: Score-Weighted vs Equal-Weight."""
    import plotly.graph_objects as go

    _cum_sw = (1 + weighted_returns).cumprod()
    _cum_ew = (1 + ew_returns).cumprod()

    fig_cum = go.Figure()
    fig_cum.add_trace(
        go.Scatter(
            x=_cum_sw.index,
            y=_cum_sw.values,
            name="Score-Weighted",
            mode="lines",
            line={"width": 2.5, "color": "#2563eb"},
        )
    )
    fig_cum.add_trace(
        go.Scatter(
            x=_cum_ew.index,
            y=_cum_ew.values,
            name="Equal-Weight",
            mode="lines",
            line={"width": 2, "dash": "dash", "color": "#6b7280"},
        )
    )

    fig_cum.update_layout(
        title="Cumulative Returns: Score-Weighted vs Equal-Weight",
        xaxis_title="Date",
        yaxis_title="Growth of $1",
        template="plotly_white",
        height=500,
    )

    mo.ui.plotly(fig_cum)
    return (fig_cum,)


@app.cell
def _(ew_returns, mo, weighted_returns):
    """Drawdown comparison chart."""
    import plotly.graph_objects as go

    def _drawdown(ret):
        cum = (1 + ret).cumprod()
        return (cum / cum.cummax() - 1) * 100

    _dd_sw = _drawdown(weighted_returns)
    _dd_ew = _drawdown(ew_returns)

    fig_dd = go.Figure()
    fig_dd.add_trace(
        go.Scatter(
            x=_dd_sw.index,
            y=_dd_sw.values,
            fill="tozeroy",
            name="Score-Weighted",
            line={"color": "#dc2626"},
        )
    )
    fig_dd.add_trace(
        go.Scatter(
            x=_dd_ew.index,
            y=_dd_ew.values,
            name="Equal-Weight",
            mode="lines",
            line={"color": "#6b7280", "dash": "dash"},
        )
    )
    fig_dd.update_layout(
        title="Portfolio Drawdown Comparison",
        xaxis_title="Date",
        yaxis_title="Drawdown (%)",
        template="plotly_white",
        height=400,
    )

    mo.ui.plotly(fig_dd)
    return (fig_dd,)


@app.cell
def _(mo, np, weighted_returns):
    """Rolling 1-year metrics."""
    import plotly.graph_objects as go
    from plotly.subplots import make_subplots

    _w = 252
    _rolling_ret = weighted_returns.rolling(_w).mean() * 252 * 100
    _rolling_vol = weighted_returns.rolling(_w).std() * np.sqrt(252) * 100
    _rolling_sharpe = _rolling_ret / _rolling_vol

    fig_rolling = make_subplots(
        rows=3,
        cols=1,
        shared_xaxes=True,
        subplot_titles=[
            "Rolling 1Y Ann. Return (%)",
            "Rolling 1Y Ann. Volatility (%)",
            "Rolling 1Y Sharpe Ratio",
        ],
        vertical_spacing=0.08,
    )

    fig_rolling.add_trace(
        go.Scatter(
            x=_rolling_ret.index,
            y=_rolling_ret,
            name="Return",
            line={"color": "steelblue"},
        ),
        row=1,
        col=1,
    )
    fig_rolling.add_trace(
        go.Scatter(
            x=_rolling_vol.index,
            y=_rolling_vol,
            name="Volatility",
            line={"color": "orange"},
        ),
        row=2,
        col=1,
    )
    fig_rolling.add_trace(
        go.Scatter(
            x=_rolling_sharpe.index,
            y=_rolling_sharpe,
            name="Sharpe",
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
        title_text="Rolling 1-Year Metrics (Score-Weighted Portfolio)",
    )

    mo.ui.plotly(fig_rolling)
    return (fig_rolling,)


@app.cell
def _(DATA_SOURCE, Path, daily_returns, ew_returns, mo, np, pd, portfolio_weights, weighted_returns):
    """vs MSCI Kokusai benchmark analysis."""
    import plotly.graph_objects as go

    _source = DATA_SOURCE.value
    _bench_path = Path(f"../data/raw/{_source}/stocks/msci_benchmark_close_prices.parquet")

    if not _bench_path.exists():
        mo.stop(True, mo.md("**MSCI Kokusai データが未取得です。** yfinance で TOK/URTH/ACWI を取得してください。"))

    _bench_close = pd.read_parquet(_bench_path)
    _tok = _bench_close["TOK"].ffill()
    bench_msci_ret = _tok.pct_change().iloc[1:].clip(-0.5, 0.5)

    _ann = 252
    _rf = 0.045

    # Align portfolio returns with benchmark
    _aligned = pd.concat(
        [weighted_returns.rename("port"), ew_returns.rename("ew"), bench_msci_ret.rename("bench")],
        axis=1,
    ).dropna()

    _p = _aligned["port"]
    _ew = _aligned["ew"]
    _b = _aligned["bench"]
    _active = _p - _b
    _n_yr = len(_aligned) / _ann

    # Cumulative
    _cum_p = float((1 + _p).prod() - 1)
    _cum_b = float((1 + _b).prod() - 1)
    _ann_p = float((1 + _cum_p) ** (1 / _n_yr) - 1)
    _ann_b = float((1 + _cum_b) ** (1 / _n_yr) - 1)
    _ann_active = _ann_p - _ann_b

    # Tracking error & IR
    _te = float(_active.std() * np.sqrt(_ann))
    _ir = float(_active.mean() / _active.std() * np.sqrt(_ann)) if _active.std() > 0 else 0

    # Beta & Alpha
    _cov = np.cov(_p, _b)
    _beta = float(_cov[0, 1] / _cov[1, 1]) if _cov[1, 1] > 0 else 1.0
    _alpha = _ann_p - (_rf + _beta * (_ann_b - _rf))

    # Sharpe
    _sharpe_p = float((_p.mean() - _rf / _ann) / _p.std() * np.sqrt(_ann))
    _sharpe_b = float((_b.mean() - _rf / _ann) / _b.std() * np.sqrt(_ann))

    # Max DD
    _cum_curve_p = (1 + _p).cumprod()
    _cum_curve_b = (1 + _b).cumprod()
    _mdd_p = float((_cum_curve_p / _cum_curve_p.cummax() - 1).min())
    _mdd_b = float((_cum_curve_b / _cum_curve_b.cummax() - 1).min())

    # Sortino
    _down = _p[_p < 0]
    _down_std = float(_down.std() * np.sqrt(_ann)) if len(_down) > 0 else 1
    _sortino = float((_p.mean() * _ann - _rf) / _down_std)

    # Calmar
    _calmar = _ann_p / abs(_mdd_p) if _mdd_p != 0 else 0

    # Up/Down capture
    _up = _b > 0
    _dn = _b < 0
    _up_cap = float(_p[_up].mean() / _b[_up].mean() * 100) if _b[_up].mean() != 0 else 0
    _dn_cap = float(_p[_dn].mean() / _b[_dn].mean() * 100) if _b[_dn].mean() != 0 else 0

    # Win rate
    _win = float((_active > 0).mean())

    mo.md(
        f"""
    ### vs MSCI Kokusai (TOK ETF)

    | Metric | Portfolio | MSCI Kokusai | Active |
    |--------|:-:|:-:|:-:|
    | **Ann. Return** | {_ann_p:.2%} | {_ann_b:.2%} | **{_ann_active:+.2%}** |
    | **Cum. Return** | {_cum_p:.2%} | {_cum_b:.2%} | {_cum_p - _cum_b:+.2%} |
    | **Sharpe Ratio** | {_sharpe_p:.4f} | {_sharpe_b:.4f} | {_sharpe_p - _sharpe_b:+.4f} |
    | **Max Drawdown** | {_mdd_p:.2%} | {_mdd_b:.2%} | |
    | **Beta** | {_beta:.4f} | 1.0 | |
    | **Alpha (CAPM)** | | | **{_alpha:+.2%}** |
    | **Tracking Error** | | | {_te:.2%} |
    | **Information Ratio** | | | {_ir:.4f} |
    | **Sortino Ratio** | {_sortino:.4f} | | |
    | **Calmar Ratio** | {_calmar:.4f} | | |
    | **Up Capture** | {_up_cap:.1f}% | | |
    | **Down Capture** | {_dn_cap:.1f}% | | |
    | **Win Rate (日次)** | {_win:.1%} | | |
    """
    )
    return bench_msci_ret


@app.cell
def _(bench_msci_ret, ew_returns, mo, pd, weighted_returns):
    """Yearly active return table vs MSCI Kokusai."""
    _aligned = pd.concat(
        [weighted_returns.rename("port"), ew_returns.rename("ew"), bench_msci_ret.rename("bench")],
        axis=1,
    ).dropna()

    _rows = []
    for y in sorted(_aligned.index.year.unique()):
        _yp = _aligned.loc[_aligned.index.year == y, "port"]
        _yb = _aligned.loc[_aligned.index.year == y, "bench"]
        _ye = _aligned.loc[_aligned.index.year == y, "ew"]
        rp = float((1 + _yp).prod() - 1)
        rb = float((1 + _yb).prod() - 1)
        re = float((1 + _ye).prod() - 1)
        _rows.append(
            {
                "Year": str(y),
                "Portfolio": f"{rp:+.2%}",
                "MSCI Kokusai": f"{rb:+.2%}",
                "Active (SW)": f"{rp - rb:+.2%}",
                "EW": f"{re:+.2%}",
                "Active (EW)": f"{re - rb:+.2%}",
            }
        )

    yearly_vs_bench = pd.DataFrame(_rows)
    mo.md("### Yearly Returns vs MSCI Kokusai")
    return (yearly_vs_bench,)


@app.cell
def _(mo, yearly_vs_bench):
    mo.ui.table(yearly_vs_bench)
    return


@app.cell
def _(bench_msci_ret, ew_returns, mo, np, pd, weighted_returns):
    """Cumulative return chart: Portfolio vs MSCI Kokusai."""
    import plotly.graph_objects as go

    _aligned = pd.concat(
        [weighted_returns.rename("port"), ew_returns.rename("ew"), bench_msci_ret.rename("bench")],
        axis=1,
    ).dropna()

    _cum_sw = (1 + _aligned["port"]).cumprod()
    _cum_ew = (1 + _aligned["ew"]).cumprod()
    _cum_bm = (1 + _aligned["bench"]).cumprod()

    fig_vs_bench = go.Figure()
    fig_vs_bench.add_trace(
        go.Scatter(x=_cum_sw.index, y=_cum_sw, name="Score-Weighted", line={"width": 2.5, "color": "#2563eb"})
    )
    fig_vs_bench.add_trace(
        go.Scatter(x=_cum_ew.index, y=_cum_ew, name="Equal-Weight", line={"width": 2, "dash": "dot", "color": "#6b7280"})
    )
    fig_vs_bench.add_trace(
        go.Scatter(x=_cum_bm.index, y=_cum_bm, name="MSCI Kokusai", line={"width": 2.5, "dash": "dash", "color": "#dc2626"})
    )
    fig_vs_bench.update_layout(
        title="Cumulative Returns: Portfolio vs MSCI Kokusai",
        xaxis_title="Date",
        yaxis_title="Growth of $1",
        template="plotly_white",
        height=500,
    )

    mo.ui.plotly(fig_vs_bench)
    return (fig_vs_bench,)


@app.cell
def _(bench_msci_ret, mo, np, pd, weighted_returns):
    """Rolling 1Y active return vs MSCI Kokusai."""
    import plotly.graph_objects as go
    from plotly.subplots import make_subplots

    _aligned = pd.concat(
        [weighted_returns.rename("port"), bench_msci_ret.rename("bench")],
        axis=1,
    ).dropna()

    _active = _aligned["port"] - _aligned["bench"]
    _w = 252

    _rolling_active = _active.rolling(_w).mean() * 252 * 100
    _rolling_te = _active.rolling(_w).std() * np.sqrt(252) * 100
    _rolling_ir = _rolling_active / _rolling_te

    fig_active = make_subplots(
        rows=3,
        cols=1,
        shared_xaxes=True,
        subplot_titles=[
            "Rolling 1Y Active Return (%)",
            "Rolling 1Y Tracking Error (%)",
            "Rolling 1Y Information Ratio",
        ],
        vertical_spacing=0.08,
    )

    fig_active.add_trace(
        go.Scatter(x=_rolling_active.index, y=_rolling_active, name="Active Return", line={"color": "#2563eb"}),
        row=1, col=1,
    )
    fig_active.add_hline(y=0, line_dash="dash", line_color="gray", row=1, col=1)

    fig_active.add_trace(
        go.Scatter(x=_rolling_te.index, y=_rolling_te, name="Tracking Error", line={"color": "orange"}),
        row=2, col=1,
    )

    fig_active.add_trace(
        go.Scatter(x=_rolling_ir.index, y=_rolling_ir, name="Info Ratio", line={"color": "green"}),
        row=3, col=1,
    )
    fig_active.add_hline(y=0, line_dash="dash", line_color="gray", row=3, col=1)

    fig_active.update_layout(
        height=800,
        template="plotly_white",
        showlegend=False,
        title_text="Rolling 1-Year Active Performance vs MSCI Kokusai",
    )

    mo.ui.plotly(fig_active)
    return (fig_active,)


@app.cell
def _(DATA_SOURCE, Path, daily_returns, ew_returns, mo, np, pd, portfolio_weights, weighted_returns):
    """vs List Portfolio Universe benchmark analysis."""
    import plotly.graph_objects as go

    _source = DATA_SOURCE.value
    _univ_path = Path(f"../data/raw/{_source}/stocks/universe_benchmark_close_prices.parquet")

    if not _univ_path.exists():
        mo.stop(True, mo.md("**Universe benchmark データが未取得です。** `/tmp/build_universe_benchmark.py` を実行してください。"))

    _univ_close = pd.read_parquet(_univ_path)

    # Load universe weights from list_portfolio
    _list_path = Path("../data/Transcript/list_portfolio_20151224.json")
    import json as _json

    with open(_list_path) as _f:
        _list_data = _json.load(_f)

    # Bloomberg → yfinance mapping (simplified)
    _exchange_map = {
        "US": "", "LN": ".L", "SW": ".SW", "VX": ".SW", "GR": ".DE",
        "HK": ".HK", "CN": ".TO", "AU": ".AX", "FP": ".PA", "SJ": ".JO",
        "IJ": ".JK", "BZ": ".SA", "KS": ".KS", "NA": ".AS", "SS": ".SS",
        "IN": ".NS", "IM": ".MI", "MM": ".MX", "TT": ".TW", "TB": ".BK",
        "DC": ".CO", "BB": ".BR", "PM": ".PS", "MK": ".KL", "SM": ".MC",
        "NO": ".OL", "FH": ".HE", "PL": ".WA", "NR": "", "NQ": "", "QM": "",
        "GK": "", "LI": "", "TI": "",
    }
    _manual = {
        "GSK": "GSK", "AZN": "AZN", "BA/": "BAESY", "DGE": "DEO",
        "BATS": None, "PRU": "PUK", "CBG": None, "STJ": None,
        "RB/": "RBGLY", "VOD": "VOD", "ULVR": "UL", "ABI": "BUD",
        "SAB": None, "SKY": None, "ARM": None, "ADN": None,
        "NESN": "NSRGY", "NOVN": "NVS", "ROG": "RHHBY", "SCMN": None,
        "SAP": "SAP", "BAYN": None, "CON": None, "HNR1": None,
        "IFC": None, "DHL": None, "CBA": None, "CPI": None,
        "005930": None, "COLOB": None,
    }

    def _bbg_to_yf(bbg_ticker):
        if not bbg_ticker:
            return None
        parts = bbg_ticker.split()
        if len(parts) < 3:
            return None
        short, exchange = parts[0], parts[1]
        if short in _manual:
            return _manual[short]
        suffix = _exchange_map.get(exchange, "")
        return f"{short}{suffix}" if suffix or exchange == "US" else short

    # Build market-cap weights
    _valid_cols = set(_univ_close.columns)
    _valid_cols = {c for c in _valid_cols if _univ_close[c].dropna().shape[0] >= 252}
    _yf_weights = {}
    _yf_sectors = {}
    _total_mcap = 0
    for _k, _entries in _list_data.items():
        _e = _entries[0]
        _bbg = _e.get("Bloomberg_Ticker")
        _mcap = _e.get("MSCI_Mkt_Cap_USD_MM", 0)
        if not _bbg or _mcap <= 0:
            continue
        _yft = _bbg_to_yf(_bbg)
        if _yft and _yft in _valid_cols:
            _yf_weights[_yft] = _yf_weights.get(_yft, 0) + _mcap
            _yf_sectors[_yft] = _e["GICS_Sector"]
            _total_mcap += _mcap

    # Normalize
    for _t in _yf_weights:
        _yf_weights[_t] /= _total_mcap

    # Compute benchmark return
    _bench_cols = list(_yf_weights.keys())
    _bench_close = _univ_close[_bench_cols].ffill()
    _bench_daily = _bench_close.pct_change().iloc[1:].clip(-0.5, 0.5)
    _w_ser = pd.Series(_yf_weights).reindex(_bench_daily.columns).fillna(0)
    _w_ser = _w_ser / _w_ser.sum()
    bench_univ_ret = (_bench_daily.fillna(0) * _w_ser).sum(axis=1)

    _ann = 252
    _rf = 0.045

    _aligned = pd.concat(
        [weighted_returns.rename("port"), ew_returns.rename("ew"), bench_univ_ret.rename("bench")],
        axis=1,
    ).dropna()

    _p = _aligned["port"]
    _b = _aligned["bench"]
    _active = _p - _b
    _n_yr = len(_aligned) / _ann

    _cum_p = float((1 + _p).prod() - 1)
    _cum_b = float((1 + _b).prod() - 1)
    _ann_p = float((1 + _cum_p) ** (1 / _n_yr) - 1)
    _ann_b = float((1 + _cum_b) ** (1 / _n_yr) - 1)
    _ann_active = _ann_p - _ann_b

    _te = float(_active.std() * np.sqrt(_ann))
    _ir = float(_active.mean() / _active.std() * np.sqrt(_ann)) if _active.std() > 0 else 0

    _cov = np.cov(_p, _b)
    _beta = float(_cov[0, 1] / _cov[1, 1]) if _cov[1, 1] > 0 else 1.0
    _alpha = _ann_p - (_rf + _beta * (_ann_b - _rf))

    _sharpe_p = float((_p.mean() - _rf / _ann) / _p.std() * np.sqrt(_ann))
    _sharpe_b = float((_b.mean() - _rf / _ann) / _b.std() * np.sqrt(_ann))

    _cum_curve_p = (1 + _p).cumprod()
    _cum_curve_b = (1 + _b).cumprod()
    _mdd_p = float((_cum_curve_p / _cum_curve_p.cummax() - 1).min())
    _mdd_b = float((_cum_curve_b / _cum_curve_b.cummax() - 1).min())

    _down = _p[_p < 0]
    _down_std = float(_down.std() * np.sqrt(_ann)) if len(_down) > 0 else 1
    _sortino = float((_p.mean() * _ann - _rf) / _down_std)
    _calmar = _ann_p / abs(_mdd_p) if _mdd_p != 0 else 0

    _up = _b > 0
    _dn = _b < 0
    _up_cap = float(_p[_up].mean() / _b[_up].mean() * 100) if _b[_up].mean() != 0 else 0
    _dn_cap = float(_p[_dn].mean() / _b[_dn].mean() * 100) if _b[_dn].mean() != 0 else 0
    _win = float((_active > 0).mean())

    mo.md(
        f"""
    ### vs List Portfolio Universe (MCap-weighted, {len(_yf_weights)} stocks)

    投資ユニバース（list_portfolio_20151224.json）の時価総額加重ベンチマーク

    | Metric | Portfolio | Universe | Active |
    |--------|:-:|:-:|:-:|
    | **Ann. Return** | {_ann_p:.2%} | {_ann_b:.2%} | **{_ann_active:+.2%}** |
    | **Cum. Return** | {_cum_p:.2%} | {_cum_b:.2%} | {_cum_p - _cum_b:+.2%} |
    | **Sharpe Ratio** | {_sharpe_p:.4f} | {_sharpe_b:.4f} | {_sharpe_p - _sharpe_b:+.4f} |
    | **Max Drawdown** | {_mdd_p:.2%} | {_mdd_b:.2%} | |
    | **Beta** | {_beta:.4f} | 1.0 | |
    | **Alpha (CAPM)** | | | **{_alpha:+.2%}** |
    | **Tracking Error** | | | {_te:.2%} |
    | **Information Ratio** | | | {_ir:.4f} |
    | **Sortino Ratio** | {_sortino:.4f} | | |
    | **Calmar Ratio** | {_calmar:.4f} | | |
    | **Up Capture** | {_up_cap:.1f}% | | |
    | **Down Capture** | {_dn_cap:.1f}% | | |
    | **Win Rate (日次)** | {_win:.1%} | | |
    """
    )
    return bench_univ_ret


@app.cell
def _(bench_univ_ret, ew_returns, mo, pd, weighted_returns):
    """Yearly active return table vs Universe."""
    _aligned = pd.concat(
        [weighted_returns.rename("port"), ew_returns.rename("ew"), bench_univ_ret.rename("bench")],
        axis=1,
    ).dropna()

    _rows = []
    for _y in sorted(_aligned.index.year.unique()):
        _yp = _aligned["port"][_aligned.index.year == _y]
        _yb = _aligned["bench"][_aligned.index.year == _y]
        _rp = float((1 + _yp).prod() - 1)
        _rb = float((1 + _yb).prod() - 1)
        _rows.append(
            {
                "Year": _y,
                "Portfolio": f"{_rp:+.2%}",
                "Universe": f"{_rb:+.2%}",
                "Active": f"{_rp - _rb:+.2%}",
            }
        )

    mo.md("### Yearly Returns vs Universe")
    _yearly_df = pd.DataFrame(_rows)
    mo.ui.table(_yearly_df, selection=None)
    return


@app.cell
def _(bench_univ_ret, mo, pd, weighted_returns):
    """Cumulative return chart: Portfolio vs Universe."""
    import plotly.graph_objects as go

    _aligned = pd.concat([weighted_returns.rename("port"), bench_univ_ret.rename("bench")], axis=1).dropna()
    _cum_p = (1 + _aligned["port"]).cumprod()
    _cum_bm = (1 + _aligned["bench"]).cumprod()

    fig_univ = go.Figure()
    fig_univ.add_trace(
        go.Scatter(x=_cum_p.index, y=_cum_p, name="CA Strategy Portfolio", line={"width": 2.5, "color": "#2563eb"})
    )
    fig_univ.add_trace(
        go.Scatter(x=_cum_bm.index, y=_cum_bm, name="Universe (MCap)", line={"width": 2.5, "dash": "dash", "color": "#d97706"})
    )
    fig_univ.update_layout(
        title="Cumulative Returns: Portfolio vs Universe",
        yaxis_title="Cumulative Return",
        xaxis_title="Date",
        template="plotly_white",
        height=450,
    )

    mo.ui.plotly(fig_univ)
    return (fig_univ,)


@app.cell
def _(
    DATA_SOURCE,
    PORTFOLIO_SIZE,
    RISK_FREE_RATE,
    Path,
    close_prices,
    daily_returns,
    ew_returns,
    json,
    metrics_df,
    mo,
    np,
    pd,
    portfolio_weights,
    weighted_returns,
):
    """Export evaluation results as JSON."""
    from datetime import datetime

    _source = DATA_SOURCE.value
    _size = PORTFOLIO_SIZE.value
    _rf = RISK_FREE_RATE.value
    _ann = 252

    # Compute all metrics for export
    _excess = weighted_returns - _rf / _ann
    _std = weighted_returns.std()
    _cum_ret = float((1 + weighted_returns).prod() - 1)
    _n_yr = len(weighted_returns) / _ann

    _cum = (1 + weighted_returns).cumprod()
    _max_dd = float((_cum / _cum.cummax() - 1).min())

    _ann_ret = float((1 + _cum_ret) ** (1 / _n_yr) - 1) if _n_yr > 0 else 0
    _ann_vol = float(_std * np.sqrt(_ann))
    _sharpe = float(_excess.mean() / _std * np.sqrt(_ann)) if _std > 0 else 0

    # Beta & IR
    _aligned = pd.concat([weighted_returns, ew_returns], axis=1).dropna()
    _cov = np.cov(_aligned.iloc[:, 0], _aligned.iloc[:, 1])
    _beta = float(_cov[0, 1] / _cov[1, 1]) if _aligned.iloc[:, 1].std() > 0 else 0
    _tracking = weighted_returns - ew_returns
    _te = _tracking.std()
    _ir = float(_tracking.mean() / _te * np.sqrt(_ann)) if _te > 0 else 0

    # Yearly
    _yearly = {}
    for y in sorted(weighted_returns.index.year.unique()):
        yr = weighted_returns[weighted_returns.index.year == y]
        _yearly[str(y)] = round(float((1 + yr).prod() - 1), 4)

    # Per-stock
    _weights = portfolio_weights.set_index("ticker")
    _per_stock = {}
    for col in daily_returns.columns:
        r = daily_returns[col].dropna()
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

    evaluation_result = {
        "source": _source,
        "portfolio": f"ca_strategy_{_size}_stock",
        "evaluated_at": datetime.now().isoformat(),
        "period": {
            "start": str(close_prices.index.min().date()),
            "end": str(close_prices.index.max().date()),
        },
        "config": {
            "weights": "score_weighted_sector_neutral",
            "risk_free_rate": _rf,
            "active_holdings": len(daily_returns.columns),
        },
        "performance": {
            "sharpe_ratio": round(_sharpe, 4),
            "max_drawdown": round(_max_dd, 4),
            "cumulative_return": round(_cum_ret, 4),
            "annualized_return": round(_ann_ret, 4),
            "annualized_volatility": round(_ann_vol, 4),
            "beta_vs_ew": round(_beta, 4),
            "information_ratio": round(_ir, 4),
        },
        "yearly_returns": _yearly,
        "per_stock": _per_stock,
    }

    _output_dir = Path(f"../data/processed/evaluation/{_source}")
    _output_dir.mkdir(parents=True, exist_ok=True)
    _out_name = f"ca_portfolio_{'phase6' if _size == '30' else _size + '_phase6'}_evaluation.json"
    _output_path = _output_dir / _out_name
    _output_path.write_text(json.dumps(evaluation_result, indent=2, ensure_ascii=False))

    mo.md(
        f"""
    ### Evaluation Exported

    **Path**: `data/processed/evaluation/{_source}/{_out_name}`

    Bloomberg データで再分析する際は:
    1. `data/raw/bloomberg/stocks/ca_portfolio_*_close_prices.parquet` を配置
    2. Data Source を **bloomberg** に切り替え
    3. セルを再実行

    ---

    **Cross-Portfolio Comparison vs MSCI Kokusai**:

    | Size | Sharpe | Alpha | Active Return | IR | Cum. Return | MSCI Kokusai |
    |------|--------|-------|---------------|-----|-------------|-------------|
    | 30 | 0.698 | +4.22% | +2.81% | 0.260 | +349.1% | +250.5% |
    | 60 | 0.701 | +3.88% | +2.99% | 0.342 | +356.1% | +250.5% |
    | 90 | 0.666 | +3.13% | +2.15% | 0.247 | +323.9% | +250.5% |

    **Cross-Portfolio Comparison vs Universe (MCap-weighted)**:

    | Size | Sharpe | Alpha | Active Return | IR | Cum. Return | Universe |
    |------|--------|-------|---------------|-----|-------------|----------|
    | 30 | 0.698 | +1.05% | +1.14% | 0.177 | +349.1% | +306.2% |
    | 60 | 0.701 | +0.55% | +1.32% | 0.272 | +356.1% | +306.2% |
    | 90 | 0.666 | -0.28% | +0.48% | 0.154 | +323.9% | +306.2% |

    vs MSCI Kokusai: 全ポートフォリオが年率 +2〜3% アウトパフォーム。60銘柄が最高の IR (0.342)。
    vs Universe: 銘柄選択による付加価値は年率 +0.5〜1.3%。60銘柄が最高の IR (0.272)。
    """
    )
    return (evaluation_result,)


if __name__ == "__main__":
    app.run()
