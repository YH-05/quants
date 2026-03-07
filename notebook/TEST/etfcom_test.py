import marimo

__generated_with = "0.19.6"
app = marimo.App()


@app.cell
def _():
    import pandas as pd
    from IPython.display import display

    from market.etfcom import TickerCollector
    from market.etfcom.types import ScrapingConfig

    return ScrapingConfig, TickerCollector, display


@app.cell
async def _(ScrapingConfig, TickerCollector, display):
    collector = TickerCollector(config=ScrapingConfig(timeout=600.0, headless=False))
    df = await collector._async_fetch()
    display(df)


if __name__ == "__main__":
    app.run()
