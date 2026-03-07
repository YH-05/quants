"""JPX（日本取引所グループ）公式 RSS スクレイパー.

curl-cffi（ブラウザ偽装）+ feedparser（RSS 解析）を使用。
JPX 公式サイトのニュースリリース・上場情報・市場ニュース等を取得する。
"""

import asyncio
import time

import feedparser
import pandas as pd
from curl_cffi import requests
from curl_cffi.requests import AsyncSession

from utils_core.logging import get_logger

from .async_core import RateLimiter, gather_with_errors
from .types import JPX_FEEDS, Article, ScraperConfig

logger = get_logger(__name__)


def fetch_rss_feed(
    session: requests.Session,
    category: str,
    timeout: int = 30,
) -> list[Article]:
    """カテゴリ別 RSS フィードから記事一覧を取得する.

    Parameters
    ----------
    session : requests.Session
        HTTP セッション
    category : str
        カテゴリ名（JPX_FEEDS のキー）
    timeout : int
        タイムアウト秒数

    Returns
    -------
    list[Article]
        記事情報のリスト

    Raises
    ------
    ValueError
        不明なカテゴリが指定された場合
    """
    if category not in JPX_FEEDS:
        raise ValueError(
            f"Unknown category: {category}. Valid: {list(JPX_FEEDS.keys())}"
        )

    url = JPX_FEEDS[category]

    logger.debug("Fetching JPX RSS", category=category)

    resp = session.get(url, timeout=timeout)
    resp.raise_for_status()

    feed = feedparser.parse(resp.text)

    articles = []
    for entry in feed.entries:
        articles.append(
            Article(
                title=str(entry.get("title", "")),
                url=str(entry.get("link", "")),
                published=str(entry.get("published", "")),
                summary=str(entry.get("summary", "")),
                category=category,
                source="jpx",
            )
        )

    logger.info("JPX RSS fetched", category=category, article_count=len(articles))
    return articles


async def async_fetch_rss_feed(
    session: AsyncSession,
    category: str,
    timeout: int = 30,
) -> list[Article]:
    """カテゴリ別 RSS フィードから記事一覧を非同期で取得する.

    ``fetch_rss_feed`` の非同期版。HTTP 取得を ``await session.get()``
    で非同期化し、``feedparser.parse()`` による XML 解析は同期のまま実行する。

    Parameters
    ----------
    session : AsyncSession
        非同期 HTTP セッション
    category : str
        カテゴリ名（JPX_FEEDS のキー）
    timeout : int
        タイムアウト秒数

    Returns
    -------
    list[Article]
        記事情報のリスト

    Raises
    ------
    ValueError
        不明なカテゴリが指定された場合
    """
    if category not in JPX_FEEDS:
        raise ValueError(
            f"Unknown category: {category}. Valid: {list(JPX_FEEDS.keys())}"
        )

    url = JPX_FEEDS[category]

    logger.debug("Fetching JPX RSS (async)", category=category)

    resp = await session.get(url, timeout=timeout)
    resp.raise_for_status()

    feed = feedparser.parse(resp.text)

    articles = []
    for entry in feed.entries:
        articles.append(
            Article(
                title=str(entry.get("title", "")),
                url=str(entry.get("link", "")),
                published=str(entry.get("published", "")),
                summary=str(entry.get("summary", "")),
                category=category,
                source="jpx",
            )
        )

    logger.info(
        "JPX RSS fetched (async)", category=category, article_count=len(articles)
    )
    return articles


def fetch_multiple_categories(
    session: requests.Session,
    categories: list[str] | None = None,
    delay: float = 0.5,
    timeout: int = 30,
) -> pd.DataFrame:
    """複数カテゴリの RSS フィードを取得する.

    Parameters
    ----------
    session : requests.Session
        HTTP セッション
    categories : list[str] | None
        取得するカテゴリ（None で全カテゴリ）
    delay : float
        リクエスト間の待機秒数
    timeout : int
        タイムアウト秒数

    Returns
    -------
    pd.DataFrame
        全記事のデータフレーム
    """
    if categories is None:
        categories = list(JPX_FEEDS.keys())

    all_articles: list[dict] = []

    for category in categories:
        try:
            articles = fetch_rss_feed(session, category, timeout)
            all_articles.extend([a.to_dict() for a in articles])
        except Exception as e:
            logger.error(
                "JPX category fetch failed",
                category=category,
                error=str(e),
            )

        time.sleep(delay)

    return pd.DataFrame(all_articles)


async def async_fetch_multiple_categories(
    session: AsyncSession,
    categories: list[str] | None = None,
    config: ScraperConfig | None = None,
) -> pd.DataFrame:
    """複数カテゴリの RSS フィードを並列で非同期取得する.

    Parameters
    ----------
    session : AsyncSession
        非同期 HTTP セッション
    categories : list[str] | None
        取得するカテゴリ（None で全カテゴリ）
    config : ScraperConfig | None
        スクレイパー設定（None でデフォルト）

    Returns
    -------
    pd.DataFrame
        全記事のデータフレーム
    """
    if config is None:
        config = ScraperConfig()

    if categories is None:
        categories = list(JPX_FEEDS.keys())

    if not categories:
        return pd.DataFrame()

    limiter = RateLimiter(delay=config.delay, max_concurrency=config.max_concurrency)

    async def _fetch_category(category: str) -> list[Article]:
        async with limiter:
            return await async_fetch_rss_feed(session, category, config.timeout)

    tasks = [asyncio.create_task(_fetch_category(cat)) for cat in categories]
    results = await gather_with_errors(tasks, logger)

    all_articles: list[dict] = []
    for article_list in results:
        all_articles.extend([a.to_dict() for a in article_list])

    return pd.DataFrame(all_articles)
