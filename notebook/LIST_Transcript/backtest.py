import marimo

__generated_with = "0.19.6"
app = marimo.App()


@app.cell
def _():
    from __future__ import annotations

    import json
    import sys
    from datetime import date
    from pathlib import Path

    import numpy as np
    import pandas as pd
    from IPython.display import display

    # プロジェクトルートを sys.path に追加（notebook/LIST_Transcript/ の2つ上）
    _project_root = Path().resolve().parents[1]
    if str(_project_root) not in sys.path:
        sys.path.insert(0, str(_project_root))

    from utils_core.config import ProjectConfig

    config = ProjectConfig.from_env()
    from research.ca_strategy_poc.scripts import run_buyhold_backtest_bloomberg as bt

    # ---------------------------------------------------------------------------
    # Paths
    # ---------------------------------------------------------------------------
    ROOT = config.data_path.parent  # finance/
    BBG_CSV = (
        config.data_path / "Transcript" / "list_port_and_index_price_2015_2026.csv"
    )
    BBG_MCAP_JSON = config.data_path / "Transcript" / "list_port_mcap_2015_2026.json"
    UNIVERSE_JSON = config.data_path / "Transcript" / "list_portfolio_20151224.json"
    CONFIG_DIR = config.research_path / "ca_strategy_poc" / "config"
    OUTPUT_DIR = (
        config.research_path / "ca_strategy_poc" / "workspaces" / "full_run" / "output"
    )
    RESULT_DIR = config.research_path / "ca_strategy_poc" / "reports"
    FRED_CACHE_DIR = config.data_path / "raw" / "fred"

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
    return bt, display, pd


@app.cell
def _(bt):
    rf = bt.fetch_dgs10_daily_rf()
    price = bt.load_bloomberg_prices()
    mcap = bt.load_bloomberg_mcap()

    universe_data = bt.load_universe_data()

    mapping = bt.build_bbg_ticker_map()
    return mcap, price, universe_data


@app.cell
def _(display, pd, universe_data):
    df_universe_data = pd.DataFrame.from_dict(universe_data, orient="index")
    df_universe_data = df_universe_data[0].apply(pd.Series)
    df_universe_data.index.name = "sedol"
    df_universe_data = df_universe_data.reset_index()
    display(df_universe_data)


@app.cell
def _(display, price):
    display(price)


@app.cell
def _(display, price):
    returns = price.pct_change()
    display(returns)


@app.cell
def _(display, mcap):
    display(mcap[["WTB LN Equity"]].dropna())


@app.cell
def _(display, mcap, pd):
    mcap_ffill = mcap.ffill()
    initial_mcap = pd.DataFrame(mcap_ffill.loc["2015-12-31"])
    display(initial_mcap)
    display(initial_mcap.dropna())


if __name__ == "__main__":
    app.run()
