import marimo

__generated_with = "0.19.2"
app = marimo.App()


@app.cell
def _():
    import os

    from tavily import TavilyClient

    tavily_client = TavilyClient(api_key=os.environ["TAVILY_API_KEY"])
    response = tavily_client.search("Who is Leo Messi?")

    print(response)
    return (response,)


@app.cell
def _(display, response):
    display(response)


if __name__ == "__main__":
    app.run()
