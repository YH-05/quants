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
    # CA Strategy: Buy-and-Hold Performance Analysis

    **目的**: Buy-and-Hold（ドリフトウェイト）方式によるポートフォリオ・パフォーマンス評価

    ## 方法論
    - **Buy-and-Hold**: ウェイトは日次リターンに応じてドリフト（リバランスなし）
    - **ウェイト更新式**: w_i(t+1) = w_i(t) × (1+r_i(t)) / Σ_j[w_j(t) × (1+r_j(t))]
    - **ベンチマーク**: MSCI Kokusai (TOK), MCap加重ユニバース, 等金額ユニバース
    - **コーポレートアクション**: M&A/上場廃止8件のウェイト再分配処理

    ---
    """
    )
    return Path, json, mo, np, pd


@app.cell
def _(mo):
    """Configuration controls."""
    PORTFOLIO_SIZE = mo.ui.dropdown(
        options=["30", "60", "90"],
        value="30",
        label="Portfolio Size",
    )

    BENCHMARK = mo.ui.dropdown(
        options=["vs_msci_kokusai", "vs_mcap_benchmark", "vs_ew_benchmark"],
        value="vs_msci_kokusai",
        label="Benchmark",
    )

    mo.hstack([PORTFOLIO_SIZE, BENCHMARK])
    return BENCHMARK, PORTFOLIO_SIZE


@app.cell
def _(Path, json, mo):
    """Load backtest results JSON."""
    _results_path = Path("../research/ca_strategy_poc/reports/buyhold_backtest_results.json")

    if not _results_path.exists():
        mo.stop(
            True,
            mo.md(
                """
        **Error**: `buyhold_backtest_results.json` が見つかりません。

        `research/ca_strategy_poc/scripts/run_buyhold_backtest.py` を実行してください。
        """
            ),
        )

    with open(_results_path) as _f:
        backtest_results = json.load(_f)

    _meta = backtest_results["metadata"]
    _rf_ann = _meta.get("risk_free_rate_annualized", _meta.get("risk_free_rate", 0))
    _rf_source = _meta.get("risk_free_rate_source", "Fixed")
    mo.md(
        f"""
    ### Backtest Metadata

    | Item | Value |
    |------|-------|
    | Methodology | {_meta['methodology']} |
    | Period | {_meta['start_date']} ~ {_meta['end_date']} |
    | Risk-Free Rate | {_rf_source} |
    | Risk-Free Rate (Ann.) | {_rf_ann:.2%} |
    | Return Cap | ±{_meta['return_cap']:.0%} |
    | Computed At | {_meta['computed_at'][:19]} |
    """
    )
    return (backtest_results,)


@app.cell
def _(Path, json, mo):
    """Load cumulative returns time series."""
    _cum_path = Path("../research/ca_strategy_poc/reports/buyhold_cumulative_returns.json")

    if not _cum_path.exists():
        mo.stop(
            True,
            mo.md("**Error**: `buyhold_cumulative_returns.json` が見つかりません。"),
        )

    with open(_cum_path) as _f:
        cumulative_data = json.load(_f)

    mo.md(
        f"""
    ### Cumulative Returns Data Loaded

    | Portfolio | Data Points |
    |-----------|-------------|
    | 30-stock | {len(cumulative_data.get('30', {}).get('dates', []))} days |
    | 60-stock | {len(cumulative_data.get('60', {}).get('dates', []))} days |
    | 90-stock | {len(cumulative_data.get('90', {}).get('dates', []))} days |
    """
    )
    return (cumulative_data,)


@app.cell
def _(BENCHMARK, PORTFOLIO_SIZE, backtest_results, mo):
    """Performance summary table for selected portfolio."""
    _size = PORTFOLIO_SIZE.value
    _bench_key = BENCHMARK.value
    _portfolio = backtest_results["portfolios"][_size]
    _comp = _portfolio["composition"]
    _perf = _portfolio[_bench_key]

    _bench_labels = {
        "vs_msci_kokusai": "MSCI Kokusai (TOK)",
        "vs_mcap_benchmark": "MCap-Weighted Universe",
        "vs_ew_benchmark": "Equal-Weight Universe",
    }
    _bench_label = _bench_labels[_bench_key]

    mo.md(
        f"""
    ## {_size}-Stock Portfolio vs {_bench_label}

    ### Composition

    | Item | Value |
    |------|-------|
    | Total Tickers | {_comp['total_tickers']} |
    | Data Available | {_comp['data_available']} |
    | Data Missing | {_comp['data_missing']} |
    | US Tickers | {_comp['us_tickers']} ({_comp['us_weight']:.1%}) |
    | Non-US Tickers | {_comp['non_us_tickers']} ({_comp['non_us_weight']:.1%}) |

    ### Performance Metrics ({_perf['n_years']:.1f} years, {_perf['n_days']} trading days)

    | Metric | Portfolio | Benchmark | Active |
    |--------|:-:|:-:|:-:|
    | **Cumulative Return** | {_perf['cumulative_return']:.2f}% | {_perf['benchmark_cum_return']:.2f}% | {_perf['cumulative_return'] - _perf['benchmark_cum_return']:+.2f}% |
    | **Annualized Return** | {_perf['annualized_return']:.2f}% | {_perf['benchmark_ann_return']:.2f}% | {_perf['annualized_return'] - _perf['benchmark_ann_return']:+.2f}% |
    | **Volatility** | {_perf['volatility']:.2f}% | — | |
    | **Sharpe Ratio** | {_perf['sharpe_ratio']:.3f} | — | |
    | **Sortino Ratio** | {_perf['sortino_ratio']:.3f} | — | |
    | **Max Drawdown** | {_perf['max_drawdown']:.2f}% | — | |
    | **Calmar Ratio** | {_perf['calmar_ratio']:.3f} | — | |
    | **Beta** | {_perf['beta']:.3f} | 1.0 | |
    | **Alpha (CAPM)** | — | — | **{_perf['alpha_capm']:+.2f}%** |
    | **Tracking Error** | — | — | {_perf['tracking_error']:.2f}% |
    | **Information Ratio** | — | — | {_perf['information_ratio']:.3f} |
    | **Win Rate (日次)** | {_perf['win_rate']:.2f}% | — | |
    """
    )
    return


@app.cell
def _(backtest_results, mo, pd):
    """All portfolios comparison table (vs MSCI Kokusai)."""
    _rows = []
    for _size in ["30", "60", "90"]:
        _p = backtest_results["portfolios"][_size]
        _msci = _p["vs_msci_kokusai"]
        _mcap = _p["vs_mcap_benchmark"]
        _ew = _p["vs_ew_benchmark"]
        _comp = _p["composition"]
        _rows.append(
            {
                "Portfolio": f"{_size}-stock",
                "Tickers (avail)": f"{_comp['total_tickers']} ({_comp['data_available']})",
                "Ann. Return": f"{_msci['annualized_return']:.2f}%",
                "Sharpe": f"{_msci['sharpe_ratio']:.3f}",
                "Max DD": f"{_msci['max_drawdown']:.2f}%",
                "Alpha vs MSCI": f"{_msci['alpha_capm']:+.2f}%",
                "Alpha vs MCap": f"{_mcap['alpha_capm']:+.2f}%",
                "IR vs EW": f"{_ew['information_ratio']:.3f}",
            }
        )

    comparison_df = pd.DataFrame(_rows)
    mo.md("### All Portfolios Comparison")
    return (comparison_df,)


@app.cell
def _(comparison_df, mo):
    mo.ui.table(comparison_df)
    return


@app.cell
def _(PORTFOLIO_SIZE, cumulative_data, mo, pd):
    """Cumulative return chart: Portfolio vs 3 Benchmarks."""
    import plotly.graph_objects as go

    _size = PORTFOLIO_SIZE.value
    _data = cumulative_data[_size]
    _dates = pd.to_datetime(_data["dates"])

    fig_cum = go.Figure()

    fig_cum.add_trace(
        go.Scatter(
            x=_dates,
            y=_data["portfolio"],
            name="CA Portfolio",
            mode="lines",
            line={"width": 2.5, "color": "#2563eb"},
        )
    )

    fig_cum.add_trace(
        go.Scatter(
            x=_dates,
            y=_data["msci_kokusai"],
            name="MSCI Kokusai (TOK)",
            mode="lines",
            line={"width": 2, "dash": "dash", "color": "#dc2626"},
        )
    )

    fig_cum.add_trace(
        go.Scatter(
            x=_dates,
            y=_data["mcap_universe"],
            name="MCap Universe",
            mode="lines",
            line={"width": 2, "dash": "dot", "color": "#059669"},
        )
    )

    fig_cum.add_trace(
        go.Scatter(
            x=_dates,
            y=_data["ew_universe"],
            name="Equal-Weight Universe",
            mode="lines",
            line={"width": 1.5, "dash": "dashdot", "color": "#6b7280"},
        )
    )

    fig_cum.update_layout(
        title=f"Cumulative Returns: {_size}-Stock Portfolio vs Benchmarks (Buy-and-Hold)",
        xaxis_title="Date",
        yaxis_title="Growth of $1",
        template="plotly_white",
        height=550,
        legend={"yanchor": "top", "y": 0.99, "xanchor": "left", "x": 0.01},
    )

    mo.ui.plotly(fig_cum)
    return (fig_cum,)


@app.cell
def _(PORTFOLIO_SIZE, cumulative_data, mo, np, pd):
    """Drawdown chart."""
    import plotly.graph_objects as go

    _size = PORTFOLIO_SIZE.value
    _data = cumulative_data[_size]
    _dates = pd.to_datetime(_data["dates"])

    def _drawdown_from_cum(cum_values):
        arr = np.array(cum_values)
        running_max = np.maximum.accumulate(arr)
        return (arr / running_max - 1) * 100

    _dd_port = _drawdown_from_cum(_data["portfolio"])
    _dd_msci = _drawdown_from_cum(_data["msci_kokusai"])

    fig_dd = go.Figure()
    fig_dd.add_trace(
        go.Scatter(
            x=_dates,
            y=_dd_port,
            fill="tozeroy",
            name="CA Portfolio",
            line={"color": "#dc2626"},
        )
    )
    fig_dd.add_trace(
        go.Scatter(
            x=_dates,
            y=_dd_msci,
            name="MSCI Kokusai",
            mode="lines",
            line={"color": "#6b7280", "dash": "dash"},
        )
    )
    fig_dd.update_layout(
        title=f"Drawdown: {_size}-Stock Portfolio vs MSCI Kokusai",
        xaxis_title="Date",
        yaxis_title="Drawdown (%)",
        template="plotly_white",
        height=400,
    )

    mo.ui.plotly(fig_dd)
    return (fig_dd,)


@app.cell
def _(PORTFOLIO_SIZE, cumulative_data, mo, np, pd):
    """Rolling 1-Year metrics (Return, Volatility, Sharpe)."""
    import plotly.graph_objects as go
    from plotly.subplots import make_subplots

    _size = PORTFOLIO_SIZE.value
    _data = cumulative_data[_size]
    _dates = pd.to_datetime(_data["dates"])

    # Reconstruct daily returns from cumulative
    _cum = np.array(_data["portfolio"])
    _daily_ret = pd.Series(np.diff(_cum) / _cum[:-1], index=_dates[1:])

    _w = 252
    _rf = 0.045
    _rolling_ret = _daily_ret.rolling(_w).mean() * 252 * 100
    _rolling_vol = _daily_ret.rolling(_w).std() * np.sqrt(252) * 100
    _rolling_sharpe = (_daily_ret.rolling(_w).mean() * 252 - _rf) / (
        _daily_ret.rolling(_w).std() * np.sqrt(252)
    )

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
    fig_rolling.add_hline(y=0, line_dash="dash", line_color="gray", row=1, col=1)

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
        title_text=f"Rolling 1-Year Metrics: {_size}-Stock Portfolio (Buy-and-Hold)",
    )

    mo.ui.plotly(fig_rolling)
    return (fig_rolling,)


@app.cell
def _(PORTFOLIO_SIZE, cumulative_data, mo, np, pd):
    """Rolling 1-Year active return vs MSCI Kokusai."""
    import plotly.graph_objects as go
    from plotly.subplots import make_subplots

    _size = PORTFOLIO_SIZE.value
    _data = cumulative_data[_size]
    _dates = pd.to_datetime(_data["dates"])

    # Daily returns from cumulative
    _cum_p = np.array(_data["portfolio"])
    _cum_b = np.array(_data["msci_kokusai"])
    _dr_p = pd.Series(np.diff(_cum_p) / _cum_p[:-1], index=_dates[1:])
    _dr_b = pd.Series(np.diff(_cum_b) / _cum_b[:-1], index=_dates[1:])
    _active = _dr_p - _dr_b

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
        go.Scatter(
            x=_rolling_active.index,
            y=_rolling_active,
            name="Active Return",
            line={"color": "#2563eb"},
        ),
        row=1,
        col=1,
    )
    fig_active.add_hline(y=0, line_dash="dash", line_color="gray", row=1, col=1)

    fig_active.add_trace(
        go.Scatter(
            x=_rolling_te.index,
            y=_rolling_te,
            name="Tracking Error",
            line={"color": "orange"},
        ),
        row=2,
        col=1,
    )

    fig_active.add_trace(
        go.Scatter(
            x=_rolling_ir.index,
            y=_rolling_ir,
            name="Info Ratio",
            line={"color": "green"},
        ),
        row=3,
        col=1,
    )
    fig_active.add_hline(y=0, line_dash="dash", line_color="gray", row=3, col=1)

    fig_active.update_layout(
        height=800,
        template="plotly_white",
        showlegend=False,
        title_text=f"Rolling 1-Year Active Performance vs MSCI Kokusai: {_size}-Stock",
    )

    mo.ui.plotly(fig_active)
    return (fig_active,)


@app.cell
def _(PORTFOLIO_SIZE, backtest_results, mo):
    """Weight drift analysis."""
    _size = PORTFOLIO_SIZE.value
    _drift = backtest_results["portfolios"][_size]["weight_drift"]

    _hhi_change = _drift["final_hhi"] / _drift["initial_hhi"]

    mo.md(
        f"""
    ## Weight Drift Analysis: {_size}-Stock Portfolio

    Buy-and-Hold 方式ではリバランスを行わないため、高パフォーマンス銘柄のウェイトが
    時間とともに増加し、ポートフォリオ集中度が上昇します。

    | Metric | Initial | Final | Change |
    |--------|:-:|:-:|:-:|
    | **HHI (集中度)** | {_drift['initial_hhi']:.4f} | {_drift['final_hhi']:.4f} | ×{_hhi_change:.1f} |
    | **最大ウェイト** | {_drift['initial_max_weight']:.1%} | {_drift['final_max_weight']:.1%} | |
    | **Top 5 ウェイト** | {_drift['initial_top5_weight']:.1%} | {_drift['final_top5_weight']:.1%} | |
    | **最大ドリフト銘柄** | — | {_drift['max_drift_ticker']} | +{_drift['max_drift_value']:.1%} |

    ### HHI の解釈
    - **< 0.01**: 高度に分散
    - **0.01 ~ 0.15**: 分散型
    - **0.15 ~ 0.25**: 中程度の集中
    - **> 0.25**: 高度な集中

    **所見**: {_size}-stock ポートフォリオの HHI は {_drift['initial_hhi']:.4f} → {_drift['final_hhi']:.4f} へ
    ×{_hhi_change:.1f} 倍に上昇。{_drift['max_drift_ticker']} が最大ドリフト
    （初期 → 最終: +{_drift['max_drift_value']:.1%}）を記録。
    Top 5 銘柄のウェイトが全体の {_drift['final_top5_weight']:.1%} を占める状態に。
    """
    )
    return


@app.cell
def _(PORTFOLIO_SIZE, Path, mo, pd):
    """Per-stock weight and return analysis."""
    _size = PORTFOLIO_SIZE.value
    _base_dir = Path("../data/raw/yfinance/stocks")
    _weights_dir = Path("../research/ca_strategy_poc/workspaces/full_run/output")

    # Load price data
    if _size == "30":
        _price_file = "ca_portfolio_close_prices.parquet"
        _weights_file = "portfolio_weights.csv"
    else:
        _price_file = f"ca_portfolio_{_size}_close_prices.parquet"
        _weights_file = f"portfolio_weights_{_size}.csv"

    _price_path = _base_dir / _price_file
    _weights_path = _weights_dir / _weights_file

    if not _price_path.exists() or not _weights_path.exists():
        mo.stop(True, mo.md(f"**Error**: {_size}-stock のデータファイルが見つかりません。"))

    _close = pd.read_parquet(_price_path)
    _weights_df = pd.read_csv(_weights_path)

    # Compute per-stock metrics
    import numpy as _np

    _ann = 252
    _daily = _close.ffill().pct_change().iloc[1:].clip(-0.5, 0.5)
    _w_map = dict(zip(_weights_df["ticker"], _weights_df["weight"]))

    _stock_rows = []
    for _col in _daily.columns:
        _r = _daily[_col].dropna()
        if len(_r) < 100:
            continue
        _cum = float((1 + _r).prod() - 1)
        _n_yr = len(_r) / _ann
        _ann_r = float((1 + _cum) ** (1 / _n_yr) - 1) if _n_yr > 0 else 0
        _vol = float(_r.std() * _np.sqrt(_ann))
        _init_w = _w_map.get(_col, 0)

        # Compute final Buy-and-Hold weight
        _final_val = (1 + _cum) * _init_w
        _stock_rows.append(
            {
                "Ticker": _col,
                "Initial Weight (%)": round(_init_w * 100, 2),
                "Ann. Return (%)": round(_ann_r * 100, 2),
                "Ann. Vol (%)": round(_vol * 100, 2),
                "Cum. Return (%)": round(_cum * 100, 1),
                "Final Value (relative)": round(_final_val, 4),
            }
        )

    # Normalize final weights
    _total_final = sum(r["Final Value (relative)"] for r in _stock_rows)
    for r in _stock_rows:
        r["Final Weight (%)"] = round(r["Final Value (relative)"] / _total_final * 100, 2)

    stock_stats = pd.DataFrame(_stock_rows).sort_values("Final Weight (%)", ascending=False)
    stock_stats = stock_stats.drop(columns=["Final Value (relative)"])

    mo.md(f"### Per-Stock Statistics: {_size}-Stock Portfolio")
    return (stock_stats,)


@app.cell
def _(mo, stock_stats):
    mo.ui.table(stock_stats.reset_index(drop=True))
    return


@app.cell
def _(mo, np, pd, stock_stats):
    """Top/Bottom performers chart."""
    import plotly.graph_objects as go

    _sorted = stock_stats.sort_values("Ann. Return (%)", ascending=True)
    _top10 = _sorted.tail(10)
    _bot10 = _sorted.head(10)
    _combined = pd.concat([_bot10, _top10])

    _colors = [
        "#dc2626" if v < 0 else "#059669" for v in _combined["Ann. Return (%)"]
    ]

    fig_performers = go.Figure()
    fig_performers.add_trace(
        go.Bar(
            x=_combined["Ann. Return (%)"],
            y=_combined["Ticker"],
            orientation="h",
            marker_color=_colors,
            text=[f"{v:+.1f}%" for v in _combined["Ann. Return (%)"]],
            textposition="outside",
        )
    )
    fig_performers.update_layout(
        title="Top 10 / Bottom 10 Performers (Ann. Return %)",
        xaxis_title="Annualized Return (%)",
        yaxis_title="",
        template="plotly_white",
        height=500,
    )

    mo.ui.plotly(fig_performers)
    return (fig_performers,)


@app.cell
def _(mo, stock_stats):
    """Weight drift scatter: Initial vs Final weight."""
    import plotly.graph_objects as go

    fig_drift = go.Figure()
    fig_drift.add_trace(
        go.Scatter(
            x=stock_stats["Initial Weight (%)"],
            y=stock_stats["Final Weight (%)"],
            mode="markers+text",
            text=stock_stats["Ticker"],
            textposition="top center",
            textfont={"size": 8},
            marker={
                "size": 8,
                "color": stock_stats["Ann. Return (%)"],
                "colorscale": "RdYlGn",
                "showscale": True,
                "colorbar": {"title": "Ann. Return (%)"},
            },
        )
    )

    # 45-degree reference line
    _max_w = max(
        stock_stats["Initial Weight (%)"].max(),
        stock_stats["Final Weight (%)"].max(),
    )
    fig_drift.add_trace(
        go.Scatter(
            x=[0, _max_w * 1.1],
            y=[0, _max_w * 1.1],
            mode="lines",
            line={"dash": "dash", "color": "gray"},
            showlegend=False,
        )
    )

    fig_drift.update_layout(
        title="Weight Drift: Initial vs Final (Buy-and-Hold)",
        xaxis_title="Initial Weight (%)",
        yaxis_title="Final Weight (%)",
        template="plotly_white",
        height=500,
    )

    mo.ui.plotly(fig_drift)
    return (fig_drift,)


@app.cell
def _(PORTFOLIO_SIZE, cumulative_data, mo, np, pd):
    """Yearly returns table vs all benchmarks."""
    _size = PORTFOLIO_SIZE.value
    _data = cumulative_data[_size]
    _dates = pd.to_datetime(_data["dates"])

    # Daily returns from cumulative
    _cum_p = np.array(_data["portfolio"])
    _cum_msci = np.array(_data["msci_kokusai"])
    _cum_mcap = np.array(_data["mcap_universe"])
    _cum_ew = np.array(_data["ew_universe"])

    _dr_p = pd.Series(np.diff(_cum_p) / _cum_p[:-1], index=_dates[1:])
    _dr_msci = pd.Series(np.diff(_cum_msci) / _cum_msci[:-1], index=_dates[1:])
    _dr_mcap = pd.Series(np.diff(_cum_mcap) / _cum_mcap[:-1], index=_dates[1:])
    _dr_ew = pd.Series(np.diff(_cum_ew) / _cum_ew[:-1], index=_dates[1:])

    _yearly_rows = []
    for _y in sorted(_dr_p.index.year.unique()):
        _mask = _dr_p.index.year == _y
        _rp = float((1 + _dr_p[_mask]).prod() - 1)
        _rm = float((1 + _dr_msci[_mask]).prod() - 1)
        _rc = float((1 + _dr_mcap[_mask]).prod() - 1)
        _re = float((1 + _dr_ew[_mask]).prod() - 1)
        _yearly_rows.append(
            {
                "Year": str(_y),
                "Portfolio": f"{_rp:+.2%}",
                "MSCI Kokusai": f"{_rm:+.2%}",
                "MCap Universe": f"{_rc:+.2%}",
                "EW Universe": f"{_re:+.2%}",
                "Active vs MSCI": f"{_rp - _rm:+.2%}",
            }
        )

    yearly_df = pd.DataFrame(_yearly_rows)
    mo.md(f"### Yearly Returns: {_size}-Stock Portfolio vs Benchmarks")
    return (yearly_df,)


@app.cell
def _(mo, yearly_df):
    mo.ui.table(yearly_df)
    return


@app.cell
def _(PORTFOLIO_SIZE, cumulative_data, mo, np, pd):
    """Yearly returns bar chart."""
    import plotly.graph_objects as go

    _size = PORTFOLIO_SIZE.value
    _data = cumulative_data[_size]
    _dates = pd.to_datetime(_data["dates"])

    _cum_p = np.array(_data["portfolio"])
    _cum_msci = np.array(_data["msci_kokusai"])
    _dr_p = pd.Series(np.diff(_cum_p) / _cum_p[:-1], index=_dates[1:])
    _dr_msci = pd.Series(np.diff(_cum_msci) / _cum_msci[:-1], index=_dates[1:])

    _years = sorted(_dr_p.index.year.unique())
    _port_yearly = [float((1 + _dr_p[_dr_p.index.year == y]).prod() - 1) * 100 for y in _years]
    _msci_yearly = [float((1 + _dr_msci[_dr_msci.index.year == y]).prod() - 1) * 100 for y in _years]

    fig_yearly_bar = go.Figure()
    fig_yearly_bar.add_trace(
        go.Bar(
            x=[str(y) for y in _years],
            y=_port_yearly,
            name="CA Portfolio",
            marker_color="#2563eb",
        )
    )
    fig_yearly_bar.add_trace(
        go.Bar(
            x=[str(y) for y in _years],
            y=_msci_yearly,
            name="MSCI Kokusai",
            marker_color="#dc2626",
            opacity=0.7,
        )
    )
    fig_yearly_bar.update_layout(
        title=f"Yearly Returns: {_size}-Stock Portfolio vs MSCI Kokusai",
        xaxis_title="Year",
        yaxis_title="Return (%)",
        barmode="group",
        template="plotly_white",
        height=400,
    )

    mo.ui.plotly(fig_yearly_bar)
    return (fig_yearly_bar,)


@app.cell
def _(backtest_results, mo):
    """Cross-portfolio comparison of all benchmarks."""
    _sizes = ["30", "60", "90"]
    _benches = [
        ("vs_msci_kokusai", "MSCI Kokusai"),
        ("vs_mcap_benchmark", "MCap Universe"),
        ("vs_ew_benchmark", "EW Universe"),
    ]

    _lines = []
    for _bk, _bl in _benches:
        _lines.append(f"\n#### vs {_bl}\n")
        _lines.append("| Metric | 30-stock | 60-stock | 90-stock |")
        _lines.append("|--------|:-:|:-:|:-:|")

        _metrics = [
            ("Ann. Return", "annualized_return", "{}:.2f", "%"),
            ("Benchmark Ann. Return", "benchmark_ann_return", "{}:.2f", "%"),
            ("Alpha (CAPM)", "alpha_capm", "{}:+.2f", "%"),
            ("Sharpe", "sharpe_ratio", "{}:.3f", ""),
            ("Max DD", "max_drawdown", "{}:.2f", "%"),
            ("Beta", "beta", "{}:.3f", ""),
            ("IR", "information_ratio", "{}:.3f", ""),
            ("Tracking Error", "tracking_error", "{}:.2f", "%"),
        ]

        for _label, _key, _fmt, _suffix in _metrics:
            _vals = []
            for _s in _sizes:
                _v = backtest_results["portfolios"][_s][_bk][_key]
                _vals.append(f"{_v:{_fmt[3:]}}{_suffix}")
            _lines.append(f"| **{_label}** | {_vals[0]} | {_vals[1]} | {_vals[2]} |")

    mo.md("## Cross-Portfolio Benchmark Comparison\n" + "\n".join(_lines))
    return


@app.cell
def _(cumulative_data, mo, pd):
    """All portfolios cumulative returns on one chart."""
    import plotly.graph_objects as go

    fig_all = go.Figure()

    _colors = {"30": "#2563eb", "60": "#059669", "90": "#7c3aed"}
    _dash = {"30": "solid", "60": "dash", "90": "dot"}

    for _size in ["30", "60", "90"]:
        _data = cumulative_data[_size]
        _dates = pd.to_datetime(_data["dates"])
        fig_all.add_trace(
            go.Scatter(
                x=_dates,
                y=_data["portfolio"],
                name=f"{_size}-stock",
                line={"color": _colors[_size], "dash": _dash[_size], "width": 2.5},
            )
        )

    # Add MSCI Kokusai (from 30-stock data, same for all)
    _data30 = cumulative_data["30"]
    _dates30 = pd.to_datetime(_data30["dates"])
    fig_all.add_trace(
        go.Scatter(
            x=_dates30,
            y=_data30["msci_kokusai"],
            name="MSCI Kokusai",
            line={"color": "#dc2626", "dash": "dash", "width": 2},
        )
    )

    fig_all.update_layout(
        title="All Portfolios vs MSCI Kokusai (Buy-and-Hold)",
        xaxis_title="Date",
        yaxis_title="Growth of $1",
        template="plotly_white",
        height=550,
        legend={"yanchor": "top", "y": 0.99, "xanchor": "left", "x": 0.01},
    )

    mo.ui.plotly(fig_all)
    return (fig_all,)


@app.cell
def _(backtest_results, mo):
    """Weight drift comparison across portfolio sizes."""
    _rows = []
    for _size in ["30", "60", "90"]:
        _d = backtest_results["portfolios"][_size]["weight_drift"]
        _rows.append(
            {
                "Portfolio": f"{_size}-stock",
                "Initial HHI": f"{_d['initial_hhi']:.4f}",
                "Final HHI": f"{_d['final_hhi']:.4f}",
                "HHI Change": f"×{_d['final_hhi'] / _d['initial_hhi']:.1f}",
                "Max Drift": f"{_d['max_drift_ticker']} (+{_d['max_drift_value']:.1%})",
                "Initial Max Wt": f"{_d['initial_max_weight']:.1%}",
                "Final Max Wt": f"{_d['final_max_weight']:.1%}",
                "Initial Top5": f"{_d['initial_top5_weight']:.1%}",
                "Final Top5": f"{_d['final_top5_weight']:.1%}",
            }
        )

    mo.md(
        f"""
    ## Weight Drift Summary

    全ポートフォリオで AVGO が最大ドリフトを記録。集中度（HHI）は
    銘柄数が少ないほど大きく上昇。

    | Metric | 30-stock | 60-stock | 90-stock |
    |--------|:-:|:-:|:-:|
    | **Initial HHI** | {_rows[0]['Initial HHI']} | {_rows[1]['Initial HHI']} | {_rows[2]['Initial HHI']} |
    | **Final HHI** | {_rows[0]['Final HHI']} | {_rows[1]['Final HHI']} | {_rows[2]['Final HHI']} |
    | **HHI 変化** | {_rows[0]['HHI Change']} | {_rows[1]['HHI Change']} | {_rows[2]['HHI Change']} |
    | **最大ドリフト** | {_rows[0]['Max Drift']} | {_rows[1]['Max Drift']} | {_rows[2]['Max Drift']} |
    | **Initial Max Weight** | {_rows[0]['Initial Max Wt']} | {_rows[1]['Initial Max Wt']} | {_rows[2]['Initial Max Wt']} |
    | **Final Max Weight** | {_rows[0]['Final Max Wt']} | {_rows[1]['Final Max Wt']} | {_rows[2]['Final Max Wt']} |
    | **Initial Top5** | {_rows[0]['Initial Top5']} | {_rows[1]['Initial Top5']} | {_rows[2]['Initial Top5']} |
    | **Final Top5** | {_rows[0]['Final Top5']} | {_rows[1]['Final Top5']} | {_rows[2]['Final Top5']} |
    """
    )
    return


@app.cell
def _(backtest_results, mo):
    """Missing tickers analysis."""
    _lines = ["## Data Coverage Analysis\n"]

    for _size in ["30", "60", "90"]:
        _comp = backtest_results["portfolios"][_size]["composition"]
        _missing = _comp["missing_tickers"]
        _lines.append(f"### {_size}-Stock Portfolio")
        _lines.append(f"- Data Available: **{_comp['data_available']}** / {_comp['total_tickers']}")
        _lines.append(f"- US: {_comp['us_tickers']} ({_comp['us_weight']:.1%}), Non-US: {_comp['non_us_tickers']} ({_comp['non_us_weight']:.1%})")
        if _missing:
            _lines.append(f"- Missing ({len(_missing)}): `{'`, `'.join(_missing)}`")
        else:
            _lines.append("- Missing: None")
        _lines.append("")

    _lines.append(
        """
### Missing Tickers の主な原因

| カテゴリ | 銘柄例 | 原因 |
|----------|--------|------|
| M&A/上場廃止 (US) | ALXN, CELG, XLNX, RTN, STJ | 買収・合併により上場廃止 |
| 非US (欧州) | NESN, SCMN, BAYN, COLOB | スイス・デンマーク等のティッカー形式不一致 |
| 非US (その他) | ITUB4, HNR1, 005930 | ブラジル・ドイツ・韓国等の特殊形式 |
| ティッカー変更 | FL, KBC, MHFI | yfinance でのデータ取得不可 |
"""
    )

    mo.md("\n".join(_lines))
    return


@app.cell
def _(mo):
    """Methodology notes."""
    mo.md(
        """
    ---

    ## Methodology Notes

    ### リスクフリーレート: FRED DGS10

    | 項目 | 値 |
    |------|-----|
    | データソース | FRED (Federal Reserve Economic Data) |
    | シリーズID | DGS10 |
    | 定義 | 米国債10年物利回り (Constant Maturity) |
    | 頻度 | 日次 |
    | 期間平均 | 2.71% |
    | 範囲 | 0.52% (2020年8月) ~ 4.98% (2023年10月) |

    日次変換: `rf_daily(t) = (1 + DGS10(t)/100)^(1/252) - 1`

    ### Buy-and-Hold vs Constant Weight（日次リバランス）

    | 特性 | Buy-and-Hold | Constant Weight |
    |------|:---:|:---:|
    | ウェイト変動 | ドリフト（自然変動） | 固定（毎日リバランス） |
    | 取引コスト | ゼロ | 高い（日次売買） |
    | 現実性 | **高い** | 低い |
    | ボラティリティ収穫 | なし | あり（ミーンリバージョン時） |
    | 集中リスク | 増加（勝者偏重） | なし |

    ### ベンチマーク定義

    | ベンチマーク | 構成 | ウェイト方式 |
    |-------------|------|-------------|
    | **MSCI Kokusai** | TOK ETF | 時価総額加重（MSCI公式） |
    | **MCap Universe** | 343/390銘柄 | MSCI時価総額初期値→ドリフト |
    | **EW Universe** | 278銘柄（252日以上データ有） | 等金額初期値→ドリフト |

    ### コーポレートアクション処理

    M&A/上場廃止の8件について、アクション日以降のウェイトを0にし、
    残存銘柄にプロポーショナル配分で再分配。

    | 銘柄 | 日付 | イベント |
    |------|------|---------|
    | ARM | 2016-09-05 | SoftBank による買収 |
    | EMC | 2016-09-07 | Dell Technologies との合併 |
    | ALTR | 2016-12-28 | Intel による買収 |
    | MON | 2018-06-07 | Bayer による買収 |
    | CA | 2018-11-05 | Broadcom による買収 |
    | LIN | 2019-03-01 | Linde plc 再編 |
    | UTX | 2020-04-03 | Raytheon との合併 |
    | S | 2020-04-01 | T-Mobile との合併 |
    """
    )
    return


if __name__ == "__main__":
    app.run()
