"""統合金融ニューススクレイパー（非同期版）.

CNBC・NASDAQ・yfinance の複数ソースから金融ニュースを並列収集する。
``asyncio.gather()`` を使用して全ソースを並列実行し、高速に結果を統合する。

Examples
--------
>>> import asyncio
>>> from news_scraper.async_unified import async_collect_financial_news
>>>
>>> async def main():
...     df = await async_collect_financial_news(
...         sources=["cnbc", "nasdaq"],
...         tickers=["AAPL", "MSFT"],
...     )
...     print(f"収集記事数: {len(df)}")
>>>
>>> asyncio.run(main())
"""

import asyncio
import json
from datetime import datetime
from pathlib import Path

import pandas as pd

from utils_core.logging import get_logger

from . import cnbc, nasdaq
from .async_core import RateLimiter, gather_with_errors
from .session import create_async_session
from .types import (
    CNBC_QUANT_CATEGORIES,
    NASDAQ_QUANT_CATEGORIES,
    ScraperConfig,
)

logger = get_logger(__name__)

# デフォルトソース
_DEFAULT_SOURCES = ["cnbc", "nasdaq"]


async def async_collect_financial_news(
    sources: list[str] | None = None,
    cnbc_categories: list[str] | None = None,
    nasdaq_categories: list[str] | None = None,
    tickers: list[str] | None = None,
    config: ScraperConfig | None = None,
    output_dir: str | Path | None = None,
) -> pd.DataFrame:
    """複数ソースから金融ニュースを並列収集する（非同期版）.

    CNBC・NASDAQ・yfinance（ticker/search）の複数ソースを ``asyncio.gather()``
    で並列実行し、全記事を統合したデータフレームを返す。
    ``include_content=True`` 時の本文取得も並列化する。

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
    >>> import asyncio
    >>> async def main():
    ...     df = await async_collect_financial_news()
    ...     df = await async_collect_financial_news(
    ...         sources=["cnbc", "nasdaq"],
    ...         tickers=["AAPL", "MSFT", "GOOGL"],
    ...     )
    >>> asyncio.run(main())
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

    logger.info(
        "Starting async financial news collection",
        sources=sources,
        cnbc_categories=cnbc_categories,
        nasdaq_categories=nasdaq_categories,
        tickers=tickers,
    )

    # 並列実行するタスクを構築
    gather_tasks: list[asyncio.Task[pd.DataFrame]] = []
    task_labels: list[str] = []

    # CNBC 非同期収集
    if "cnbc" in sources:
        session_cnbc = create_async_session(
            impersonate=config.impersonate,  # type: ignore[arg-type]
            proxy=config.proxy,
        )
        gather_tasks.append(
            asyncio.create_task(
                cnbc.async_fetch_multiple_categories(
                    session_cnbc, cnbc_categories, config
                )
            )
        )
        task_labels.append("cnbc")

    # NASDAQ 非同期収集
    if "nasdaq" in sources:
        session_nasdaq = create_async_session(
            impersonate=config.impersonate,  # type: ignore[arg-type]
            proxy=config.proxy,
        )
        gather_tasks.append(
            asyncio.create_task(
                nasdaq.async_collect_nasdaq_news(
                    categories=nasdaq_categories,
                    tickers=tickers,
                    config=config,
                )
            )
        )
        task_labels.append("nasdaq")

    # yfinance ticker 非同期収集（同期関数をコルーチンでラップして実行）
    if "yfinance_ticker" in sources and tickers:
        from . import yfinance as yf_module
        from .session import create_session

        async def _async_collect_yfinance_ticker() -> pd.DataFrame:
            from typing import Literal

            imp: Literal["chrome", "chrome131", "safari", "firefox"] = (
                config.impersonate  # type: ignore[assignment]
            )
            session_yf = create_session(impersonate=imp, proxy=config.proxy)
            loop = asyncio.get_running_loop()
            return await loop.run_in_executor(
                None,
                lambda: yf_module.fetch_multiple_tickers(
                    session_yf, tickers, config=config, timeout=config.timeout
                ),
            )

        gather_tasks.append(asyncio.create_task(_async_collect_yfinance_ticker()))
        task_labels.append("yfinance_ticker")

    # yfinance search 非同期収集（同期関数をコルーチンでラップして実行）
    if "yfinance_search" in sources and tickers:
        from . import yfinance as yf_module2
        from .session import create_session

        async def _async_collect_yfinance_search() -> pd.DataFrame:
            from typing import Literal

            imp: Literal["chrome", "chrome131", "safari", "firefox"] = (
                config.impersonate  # type: ignore[assignment]
            )
            session_yf_s = create_session(impersonate=imp, proxy=config.proxy)
            loop = asyncio.get_running_loop()
            return await loop.run_in_executor(
                None,
                lambda: yf_module2.fetch_multiple_searches(
                    session_yf_s,
                    tickers,
                    config=config,
                    timeout=config.timeout,
                ),
            )

        gather_tasks.append(asyncio.create_task(_async_collect_yfinance_search()))
        task_labels.append("yfinance_search")

    if not gather_tasks:
        logger.info("No sources to collect")
        return pd.DataFrame()

    # 並列実行
    results = await gather_with_errors(gather_tasks, logger)

    # 結果を統合
    all_articles: list[dict] = []
    for label, df_result in zip(task_labels, results, strict=False):
        if not df_result.empty:
            article_count = len(df_result)
            all_articles.extend(df_result.to_dict("records"))
            logger.info(
                "Source collection completed", source=label, count=article_count
            )
        else:
            logger.info("Source returned no articles", source=label)

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

    # 本文並列取得（include_content=True の場合）
    if config.include_content:
        # CNBC と NASDAQ のセッションを使用
        session_content = create_async_session(
            impersonate=config.impersonate,  # type: ignore[arg-type]
            proxy=config.proxy,
        )
        content_limiter = RateLimiter(
            delay=config.delay,
            max_concurrency=config.max_concurrency_content,
        )

        async def _fetch_content(url: str) -> tuple[str, str]:
            async with content_limiter:
                content_data = await cnbc.async_fetch_article_content(
                    session_content, url, config.timeout
                )
                content = content_data.get("content", "") if content_data else ""
                return url, content

        content_tasks = [
            asyncio.create_task(_fetch_content(str(row["url"])))
            for _, row in df.iterrows()
        ]
        content_results = await gather_with_errors(content_tasks, logger)

        content_map: dict[str, str] = {}
        for url, content in content_results:
            content_map[url] = content

        df["content"] = df["url"].map(lambda u: content_map.get(u, ""))
        logger.info("Content fetching completed", fetched=len(content_map))

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

    logger.info("Async financial news collection finished", total_articles=len(df))
    return df
