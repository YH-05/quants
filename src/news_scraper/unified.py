"""統合金融ニューススクレイパー（同期版）.

CNBC・NASDAQ・yfinance の複数ソースから金融ニュースを一括収集する。
各ソースを逐次実行し、結果を統合して返す。

Examples
--------
>>> from news_scraper.unified import collect_financial_news
>>>
>>> # 基本的な使用（全ソース）
>>> df = collect_financial_news()
>>> print(f"収集記事数: {len(df)}")
>>>
>>> # CNBC のみ
>>> df = collect_financial_news(
...     sources=["cnbc"],
...     cnbc_categories=["economy", "earnings"],
... )
"""

import asyncio
import json
import time
from datetime import datetime
from pathlib import Path

import pandas as pd

from utils_core.logging import get_logger

from . import cnbc, nasdaq, yfinance
from .async_unified import async_collect_financial_news
from .session import create_session
from .types import (
    CNBC_QUANT_CATEGORIES,
    NASDAQ_QUANT_CATEGORIES,
    ScraperConfig,
)

logger = get_logger(__name__)

# デフォルトソース
_DEFAULT_SOURCES = ["cnbc", "nasdaq"]


def _collect_cnbc(
    config: ScraperConfig,
    cnbc_categories: list[str],
) -> list[dict]:
    """CNBC からニュースを収集して記事辞書リストを返す."""
    session = create_session(impersonate=config.impersonate, proxy=config.proxy)
    df = cnbc.fetch_multiple_categories(
        session,
        categories=cnbc_categories,
        delay=config.delay,
        timeout=config.timeout,
    )
    if config.include_content and not df.empty:
        contents = []
        for _i, row in df.iterrows():
            content_data = cnbc.fetch_article_content(
                session, str(row["url"]), config.timeout
            )
            contents.append(content_data.get("content", "") if content_data else "")
            time.sleep(config.delay)
        df["content"] = contents
    logger.info("CNBC collection completed", article_count=len(df))
    return df.to_dict("records")


def _collect_nasdaq(
    config: ScraperConfig,
    nasdaq_categories: list[str],
    tickers: list[str] | None,
) -> list[dict]:
    """NASDAQ からニュースを収集して記事辞書リストを返す."""
    df = nasdaq.collect_nasdaq_news(
        categories=nasdaq_categories,
        tickers=tickers,
        config=config,
    )
    logger.info("NASDAQ collection completed", article_count=len(df))
    return df.to_dict("records")


def _collect_yfinance_ticker(
    config: ScraperConfig,
    tickers: list[str],
) -> list[dict]:
    """yfinance ticker からニュースを収集して記事辞書リストを返す."""
    session_yf = create_session(impersonate=config.impersonate, proxy=config.proxy)
    df = yfinance.fetch_multiple_tickers(
        session_yf, tickers, config=config, timeout=config.timeout
    )
    logger.info("yfinance ticker collection completed", article_count=len(df))
    return df.to_dict("records")


def _collect_yfinance_search(
    config: ScraperConfig,
    tickers: list[str],
) -> list[dict]:
    """yfinance search からニュースを収集して記事辞書リストを返す."""
    session_yf_s = create_session(impersonate=config.impersonate, proxy=config.proxy)
    df = yfinance.fetch_multiple_searches(
        session_yf_s,
        tickers,
        config=config,
        timeout=config.timeout,
    )
    logger.info("yfinance search collection completed", article_count=len(df))
    return df.to_dict("records")


def collect_financial_news(
    sources: list[str] | None = None,
    cnbc_categories: list[str] | None = None,
    nasdaq_categories: list[str] | None = None,
    tickers: list[str] | None = None,
    config: ScraperConfig | None = None,
    output_dir: str | Path | None = None,
) -> pd.DataFrame:
    """複数ソースから金融ニュースを一括収集する（同期版）.

    CNBC・NASDAQ・yfinance（ticker/search）の複数ソースを逐次実行し、
    全記事を統合したデータフレームを返す。重複は URL をキーに除去する。

    Parameters
    ----------
    sources : list[str] | None
        収集するソース名のリスト。デフォルトは ``["cnbc", "nasdaq"]``。
        有効な値: ``"cnbc"``, ``"nasdaq"``,
        ``"yfinance_ticker"``, ``"yfinance_search"``
    cnbc_categories : list[str] | None
        CNBC の収集カテゴリ。None でクオンツ向けデフォルト 8 カテゴリを使用。
    nasdaq_categories : list[str] | None
        NASDAQ の収集カテゴリ。None でクオンツ向けデフォルト 7 カテゴリを使用。
    tickers : list[str] | None
        銘柄コードのリスト（例: ``["AAPL", "MSFT"]``）。
        NASDAQ 銘柄別取得と yfinance_ticker 取得で使用。
    config : ScraperConfig | None
        スクレイパー設定。None でデフォルト設定を使用。
    output_dir : str | Path | None
        出力ディレクトリ。None の場合はファイル保存しない。
        指定時は JSON + Parquet 形式でタイムスタンプ付きファイルを保存。

    Returns
    -------
    pd.DataFrame
        収集した全記事のデータフレーム（URL による重複除去済み）。
        空の場合は空の DataFrame を返す。

    Examples
    --------
    >>> df = collect_financial_news()
    >>> df = collect_financial_news(
    ...     sources=["cnbc"],
    ...     cnbc_categories=["economy", "earnings", "technology"],
    ... )
    >>> df = collect_financial_news(
    ...     sources=["nasdaq"],
    ...     nasdaq_categories=["Markets"],
    ...     tickers=["AAPL", "MSFT"],
    ... )
    >>> df = collect_financial_news(output_dir="data/financial_news")
    """
    if sources is None:
        sources = list(_DEFAULT_SOURCES)

    if config is None:
        config = ScraperConfig()

    if cnbc_categories is None:
        cnbc_categories = list(CNBC_QUANT_CATEGORIES)

    if nasdaq_categories is None:
        nasdaq_categories = list(NASDAQ_QUANT_CATEGORIES)

    output_path: Path | None = None
    if output_dir:
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)

    all_articles: list[dict] = []

    logger.info(
        "Starting financial news collection",
        sources=sources,
        cnbc_categories=cnbc_categories,
        nasdaq_categories=nasdaq_categories,
        tickers=tickers,
    )

    if "cnbc" in sources:
        try:
            all_articles.extend(_collect_cnbc(config, cnbc_categories))
        except Exception as e:
            logger.error("CNBC collection failed", error=str(e))

    if "nasdaq" in sources:
        try:
            all_articles.extend(_collect_nasdaq(config, nasdaq_categories, tickers))
        except Exception as e:
            logger.error("NASDAQ collection failed", error=str(e))

    if "yfinance_ticker" in sources and tickers:
        try:
            all_articles.extend(_collect_yfinance_ticker(config, tickers))
        except Exception as e:
            logger.error("yfinance ticker collection failed", error=str(e))

    if "yfinance_search" in sources and tickers:
        try:
            all_articles.extend(_collect_yfinance_search(config, tickers))
        except Exception as e:
            logger.error("yfinance search collection failed", error=str(e))

    df = pd.DataFrame(all_articles)

    if df.empty:
        logger.info("No articles collected")
        return df

    # URL ベースの重複除去
    before_dedup = len(df)
    df = df.drop_duplicates(subset=["url"])
    logger.info(
        "Deduplication completed",
        before=before_dedup,
        after=len(df),
        removed=before_dedup - len(df),
    )

    # ファイル保存
    if output_path and not df.empty:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        json_path = output_path / f"news_{timestamp}.json"
        parquet_path = output_path / f"news_{timestamp}.parquet"

        records = df.to_dict("records")
        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(records, f, ensure_ascii=False, indent=2)

        df.to_parquet(parquet_path, index=False)

        logger.info(
            "Saved collection results",
            json_path=str(json_path),
            parquet_path=str(parquet_path),
            article_count=len(df),
        )

    logger.info("Financial news collection finished", total_articles=len(df))
    return df


def collect_financial_news_fast(
    sources: list[str] | None = None,
    cnbc_categories: list[str] | None = None,
    nasdaq_categories: list[str] | None = None,
    tickers: list[str] | None = None,
    config: ScraperConfig | None = None,
    output_dir: str | Path | None = None,
) -> pd.DataFrame:
    """複数ソースから金融ニュースを高速一括収集する（同期ラッパー）.

    ``async_collect_financial_news`` の同期ラッパー。
    ``asyncio.run()`` 経由で非同期版を実行することで、
    内部では並列実行により ``collect_financial_news`` より高速に動作する。

    .. note::
        Jupyter Notebook 環境では ``asyncio.run()`` が ``RuntimeError`` を
        発生させるため使用できない。その場合は ``async_collect_financial_news``
        を ``await`` で直接呼び出すこと。

    Parameters
    ----------
    sources : list[str] | None
        収集するソース名のリスト。デフォルトは ``["cnbc", "nasdaq"]``。
        有効な値: ``"cnbc"``, ``"nasdaq"``,
        ``"yfinance_ticker"``, ``"yfinance_search"``
    cnbc_categories : list[str] | None
        CNBC の収集カテゴリ。None でクオンツ向けデフォルト 8 カテゴリを使用。
    nasdaq_categories : list[str] | None
        NASDAQ の収集カテゴリ。None でクオンツ向けデフォルト 7 カテゴリを使用。
    tickers : list[str] | None
        銘柄コードのリスト（例: ``["AAPL", "MSFT"]``）。
    config : ScraperConfig | None
        スクレイパー設定。None でデフォルト設定を使用。
    output_dir : str | Path | None
        出力ディレクトリ。None の場合はファイル保存しない。

    Returns
    -------
    pd.DataFrame
        収集した全記事のデータフレーム（URL による重複除去済み）。

    Examples
    --------
    >>> df = collect_financial_news_fast(
    ...     sources=["cnbc", "nasdaq"],
    ...     tickers=["AAPL", "MSFT", "GOOGL"],
    ... )
    >>> df = collect_financial_news_fast(
    ...     config=ScraperConfig(include_content=True, max_concurrency=5),
    ... )
    """
    return asyncio.run(
        async_collect_financial_news(
            sources=sources,
            cnbc_categories=cnbc_categories,
            nasdaq_categories=nasdaq_categories,
            tickers=tickers,
            config=config,
            output_dir=output_dir,
        )
    )
