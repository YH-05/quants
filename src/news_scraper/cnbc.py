"""CNBC ニューススクレイパー.

curl-cffi（ブラウザ偽装）+ trafilatura（本文抽出）を使用。
カテゴリ別・日付別の過去記事収集に対応。
"""

import asyncio
import json
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Literal
from urllib.parse import urlparse

import feedparser
import pandas as pd
import trafilatura
from bs4 import BeautifulSoup
from curl_cffi import requests
from curl_cffi.requests import AsyncSession

from utils_core.logging import get_logger

from .async_core import RateLimiter, gather_with_errors
from .session import create_async_session, create_session
from .types import CNBC_FEEDS, CNBC_QUANT_CATEGORIES, Article, ScraperConfig

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
        カテゴリ名（CNBC_FEEDS のキー）
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
    if category not in CNBC_FEEDS:
        raise ValueError(
            f"Unknown category: {category}. Valid: {list(CNBC_FEEDS.keys())}"
        )

    feed_id = CNBC_FEEDS[category]
    url = f"https://search.cnbc.com/rs/search/combinedcms/view.xml?partnerId=wrss01&id={feed_id}"

    logger.debug("Fetching CNBC RSS", category=category)

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
                source="cnbc",
            )
        )

    logger.info("CNBC RSS fetched", category=category, article_count=len(articles))
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
        非同期 HTTP セッション（``create_async_session()`` で作成）
    category : str
        カテゴリ名（``CNBC_FEEDS`` のキー）
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

    Examples
    --------
    >>> import asyncio
    >>> from news_scraper.session import create_async_session
    >>> async def main():
    ...     session = create_async_session()
    ...     articles = await async_fetch_rss_feed(session, "top_news")
    ...     print(len(articles))
    >>> asyncio.run(main())
    """
    if category not in CNBC_FEEDS:
        raise ValueError(
            f"Unknown category: {category}. Valid: {list(CNBC_FEEDS.keys())}"
        )

    feed_id = CNBC_FEEDS[category]
    url = f"https://search.cnbc.com/rs/search/combinedcms/view.xml?partnerId=wrss01&id={feed_id}"

    logger.debug("Fetching CNBC RSS (async)", category=category)

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
                source="cnbc",
            )
        )

    logger.info(
        "CNBC RSS fetched (async)", category=category, article_count=len(articles)
    )
    return articles


async def async_fetch_multiple_categories(
    session: AsyncSession,
    categories: list[str] | None = None,
    config: ScraperConfig | None = None,
) -> pd.DataFrame:
    """複数カテゴリの RSS フィードを並列で非同期取得する.

    ``RateLimiter`` で同時実行数を ``config.max_concurrency`` に制限し、
    ``gather_with_errors`` でエラーを許容しながら並列実行する。

    Parameters
    ----------
    session : AsyncSession
        非同期 HTTP セッション（``create_async_session()`` で作成）
    categories : list[str] | None
        取得するカテゴリ（None で全カテゴリ）
    config : ScraperConfig | None
        スクレイパー設定（None でデフォルト）

    Returns
    -------
    pd.DataFrame
        全記事のデータフレーム

    Examples
    --------
    >>> import asyncio
    >>> from news_scraper.session import create_async_session
    >>> from news_scraper.types import ScraperConfig
    >>> async def main():
    ...     session = create_async_session()
    ...     df = await async_fetch_multiple_categories(
    ...         session, ["top_news", "economy"], ScraperConfig()
    ...     )
    ...     print(len(df))
    >>> asyncio.run(main())
    """
    if config is None:
        config = ScraperConfig()

    if categories is None:
        categories = list(CNBC_FEEDS.keys())

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
        categories = list(CNBC_FEEDS.keys())

    all_articles = []

    for category in categories:
        try:
            articles = fetch_rss_feed(session, category, timeout)
            all_articles.extend([a.to_dict() for a in articles])
        except Exception as e:
            logger.error("CNBC category fetch failed", category=category, error=str(e))

        time.sleep(delay)

    return pd.DataFrame(all_articles)


def fetch_article_content(
    session: requests.Session,
    url: str,
    timeout: int = 30,
) -> dict | None:
    """記事ページから本文を取得する.

    Parameters
    ----------
    session : requests.Session
        HTTP セッション
    url : str
        記事 URL
    timeout : int
        タイムアウト秒数

    Returns
    -------
    dict | None
        記事情報（取得失敗時は None）
    """
    parsed = urlparse(url)
    if parsed.scheme not in ("http", "https"):
        logger.warning(
            "Rejected URL with invalid scheme", url=url, scheme=parsed.scheme
        )
        return None

    try:
        resp = session.get(url, timeout=timeout)
        resp.raise_for_status()
    except Exception as e:
        logger.warning("Content fetch failed", url=url, error=str(e))
        return None

    html = resp.text

    # trafilatura で本文抽出
    text = trafilatura.extract(
        html,
        include_comments=False,
        include_tables=False,
        no_fallback=False,
    )

    if not text:
        # フォールバック: BeautifulSoup
        soup = BeautifulSoup(html, "html.parser")
        article_el = soup.select_one('[data-module="ArticleBody"]')
        if article_el:
            text = article_el.get_text(separator="\n", strip=True)

    if not text:
        return None

    # メタデータ抽出
    soup = BeautifulSoup(html, "html.parser")

    title_el = soup.select_one("h1")
    title = title_el.get_text(strip=True) if title_el else ""

    time_el = soup.select_one("time")
    published = time_el.get("datetime", "") if time_el else ""

    return {
        "url": url,
        "title": title,
        "published": published,
        "content": text,
    }


async def async_fetch_article_content(
    session: AsyncSession,
    url: str,
    timeout: int = 30,
) -> dict | None:
    """記事ページから本文を非同期で取得する.

    ``fetch_article_content`` の非同期版。HTTP 取得を ``await session.get()``
    で非同期化し、``trafilatura.extract()`` および BeautifulSoup による
    フォールバック処理を ``asyncio.to_thread()`` でスレッドプールへオフロードする。

    Parameters
    ----------
    session : AsyncSession
        非同期 HTTP セッション（``create_async_session()`` で作成）
    url : str
        記事 URL
    timeout : int
        タイムアウト秒数

    Returns
    -------
    dict | None
        記事情報（取得失敗時は None）。成功時のキー:
        - ``url``: 記事 URL
        - ``title``: 記事タイトル
        - ``published``: 公開日時
        - ``content``: 本文テキスト

    Examples
    --------
    >>> import asyncio
    >>> from news_scraper.session import create_async_session
    >>> async def main():
    ...     session = create_async_session()
    ...     result = await async_fetch_article_content(
    ...         session, "https://www.cnbc.com/2026/01/01/example.html"
    ...     )
    ...     if result:
    ...         print(result["title"])
    >>> asyncio.run(main())
    """
    parsed = urlparse(url)
    if parsed.scheme not in ("http", "https"):
        logger.warning(
            "Rejected URL with invalid scheme (async)", url=url, scheme=parsed.scheme
        )
        return None

    try:
        resp = await session.get(url, timeout=timeout)
        resp.raise_for_status()
    except Exception as e:
        logger.warning("Content fetch failed (async)", url=url, error=str(e))
        return None

    html = resp.text

    # trafilatura で本文抽出（スレッドプールへオフロード）
    text = await asyncio.to_thread(
        trafilatura.extract,
        html,
        include_comments=False,
        include_tables=False,
        no_fallback=False,
    )

    if not text:
        # フォールバック: BeautifulSoup（スレッドプールへオフロード）
        def _bs4_fallback(html_content: str) -> str | None:
            soup = BeautifulSoup(html_content, "html.parser")
            article_el = soup.select_one('[data-module="ArticleBody"]')
            if article_el:
                return article_el.get_text(separator="\n", strip=True)
            return None

        text = await asyncio.to_thread(_bs4_fallback, html)

    if not text:
        return None

    # メタデータ抽出（スレッドプールへオフロード）
    def _extract_metadata(html_content: str) -> tuple[str, str]:
        soup = BeautifulSoup(html_content, "html.parser")
        title_el = soup.select_one("h1")
        title = title_el.get_text(strip=True) if title_el else ""
        time_el = soup.select_one("time")
        published = str(time_el.get("datetime", "")) if time_el else ""
        return title, published

    title, published = await asyncio.to_thread(_extract_metadata, html)

    return {
        "url": url,
        "title": title,
        "published": published,
        "content": text,
    }


def fetch_sitemap_articles_playwright(
    year: int,
    month: int,
    day: int,
    browser=None,
) -> list[dict]:
    """Playwright を使ってサイトマップから指定日の記事一覧を取得する.

    Parameters
    ----------
    year, month, day : int
        対象日付
    browser : Browser | None
        既存のブラウザインスタンス（なければ新規作成）

    Returns
    -------
    list[dict]
        記事情報のリスト
    """
    from playwright.sync_api import sync_playwright  # type: ignore[import-not-found]

    month_names = [
        "",
        "January",
        "February",
        "March",
        "April",
        "May",
        "June",
        "July",
        "August",
        "September",
        "October",
        "November",
        "December",
    ]

    url = f"https://www.cnbc.com/site-map/articles/{year}/{month_names[month]}/{day}/"

    logger.debug("Fetching CNBC sitemap", year=year, month=month, day=day)

    close_browser = False
    playwright = None

    if browser is None:
        playwright = sync_playwright().start()
        browser = playwright.chromium.launch(headless=True)
        close_browser = True

    try:
        page = browser.new_page()
        page.goto(url, timeout=30000)
        page.wait_for_load_state("networkidle", timeout=15000)

        links = page.query_selector_all("a")

        articles = []
        seen = set()

        for link in links:
            href = link.get_attribute("href") or ""
            text = link.inner_text().strip()

            if f"/{year}/{month:02d}/" in href and len(text) > 15 and href not in seen:
                seen.add(href)

                # カテゴリを URL から推定
                category = "unknown"
                for cat in [
                    "markets",
                    "investing",
                    "technology",
                    "economy",
                    "politics",
                ]:
                    if cat in href.lower():
                        category = cat
                        break

                full_url = (
                    href if href.startswith("http") else f"https://www.cnbc.com{href}"
                )
                articles.append(
                    {
                        "title": text,
                        "url": full_url,
                        "date": f"{year}-{month:02d}-{day:02d}",
                        "category": category,
                        "source": "cnbc",
                    }
                )

        page.close()
        logger.info(
            "CNBC sitemap fetched",
            year=year,
            month=month,
            day=day,
            article_count=len(articles),
        )
        return articles

    except Exception as e:
        logger.error("Sitemap fetch failed", error=str(e))
        return []

    finally:
        if close_browser:
            browser.close()
            if playwright:
                playwright.stop()


async def async_fetch_sitemap_articles_playwright(
    year: int,
    month: int,
    day: int,
    browser=None,
) -> list[dict]:
    """Playwright を使ってサイトマップから指定日の記事一覧を非同期で取得する.

    ``fetch_sitemap_articles_playwright`` の非同期版。Playwright の非同期 API
    (``playwright.async_api``) を使用し、``await page.goto()`` や
    ``await page.wait_for_load_state()`` で非同期にブラウザ操作を行う。

    Parameters
    ----------
    year, month, day : int
        対象日付
    browser : Browser | None
        既存のブラウザインスタンス（なければ新規作成）

    Returns
    -------
    list[dict]
        記事情報のリスト。各 dict は以下のキーを持つ:
        - ``title``: 記事タイトル
        - ``url``: 記事 URL
        - ``date``: 日付 (YYYY-MM-DD)
        - ``category``: 推定カテゴリ
        - ``source``: "cnbc"

    Examples
    --------
    >>> import asyncio
    >>> async def main():
    ...     articles = await async_fetch_sitemap_articles_playwright(2026, 1, 15)
    ...     print(len(articles))
    >>> asyncio.run(main())
    """
    from playwright.async_api import async_playwright  # type: ignore[import-not-found]

    month_names = [
        "",
        "January",
        "February",
        "March",
        "April",
        "May",
        "June",
        "July",
        "August",
        "September",
        "October",
        "November",
        "December",
    ]

    url = f"https://www.cnbc.com/site-map/articles/{year}/{month_names[month]}/{day}/"

    logger.debug("Fetching CNBC sitemap (async)", year=year, month=month, day=day)

    close_browser = False
    playwright = None

    if browser is None:
        playwright = await async_playwright().start()
        browser = await playwright.chromium.launch(headless=True)
        close_browser = True

    try:
        page = await browser.new_page()
        await page.goto(url, timeout=30000)
        await page.wait_for_load_state("networkidle", timeout=15000)

        links = await page.query_selector_all("a")

        articles = []
        seen: set[str] = set()

        for link in links:
            href = await link.get_attribute("href") or ""
            text = (await link.inner_text()).strip()

            if f"/{year}/{month:02d}/" in href and len(text) > 15 and href not in seen:
                seen.add(href)

                # カテゴリを URL から推定
                category = "unknown"
                for cat in [
                    "markets",
                    "investing",
                    "technology",
                    "economy",
                    "politics",
                ]:
                    if cat in href.lower():
                        category = cat
                        break

                full_url = (
                    href if href.startswith("http") else f"https://www.cnbc.com{href}"
                )
                articles.append(
                    {
                        "title": text,
                        "url": full_url,
                        "date": f"{year}-{month:02d}-{day:02d}",
                        "category": category,
                        "source": "cnbc",
                    }
                )

        await page.close()
        logger.info(
            "CNBC sitemap fetched (async)",
            year=year,
            month=month,
            day=day,
            article_count=len(articles),
        )
        return articles

    except Exception as e:
        logger.error("Sitemap fetch failed (async)", error=str(e))
        return []

    finally:
        if close_browser:
            await browser.close()
            if playwright:
                await playwright.stop()


def collect_historical_news(
    start_date: datetime,
    end_date: datetime,
    config: ScraperConfig | None = None,
    output_dir: str | Path | None = None,
) -> pd.DataFrame:
    """指定期間の過去ニュースを収集する.

    Parameters
    ----------
    start_date : datetime
        開始日
    end_date : datetime
        終了日
    config : ScraperConfig | None
        スクレイパー設定
    output_dir : str | Path | None
        出力ディレクトリ（None で保存しない）

    Returns
    -------
    pd.DataFrame
        収集した記事のデータフレーム

    Examples
    --------
    >>> from datetime import datetime
    >>> df = collect_historical_news(
    ...     start_date=datetime(2024, 1, 1),
    ...     end_date=datetime(2024, 1, 7),
    ... )
    """
    from playwright.sync_api import sync_playwright  # type: ignore[import-not-found]

    if config is None:
        config = ScraperConfig()

    output_path: Path | None = None
    if output_dir:
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)

    session = create_session(impersonate=config.impersonate, proxy=config.proxy)
    all_articles = []

    # Playwright でブラウザを起動
    playwright = None
    browser = None
    if config.use_playwright:
        playwright = sync_playwright().start()
        browser = playwright.chromium.launch(headless=True)

    try:
        current = start_date
        while current <= end_date:
            logger.info("Collecting historical news", date=str(current.date()))

            if config.use_playwright:
                articles = fetch_sitemap_articles_playwright(
                    current.year,
                    current.month,
                    current.day,
                    browser=browser,
                )
            else:
                articles = []  # curl-cffi では JavaScript 非対応

            if config.include_content and articles:
                for article in articles:
                    content_data = fetch_article_content(
                        session, article["url"], config.timeout
                    )
                    if content_data:
                        article["content"] = content_data.get("content", "")
                    time.sleep(config.delay)

            all_articles.extend(articles)

            # 日別に保存
            if output_path:
                date_str = current.strftime("%Y-%m-%d")
                with open(output_path / f"{date_str}.json", "w", encoding="utf-8") as f:
                    json.dump(articles, f, ensure_ascii=False, indent=2)

            current += timedelta(days=1)
            time.sleep(config.delay)

    finally:
        if browser:
            browser.close()
        if playwright:
            playwright.stop()

    df = pd.DataFrame(all_articles)

    if output_path and not df.empty:
        df.to_parquet(output_path / "all_articles.parquet", index=False)

    return df


async def async_collect_historical_news(
    start_date: datetime,
    end_date: datetime,
    config: ScraperConfig | None = None,
    output_dir: str | Path | None = None,
) -> pd.DataFrame:
    """指定期間の過去ニュースを並列で非同期収集する.

    ``collect_historical_news`` の非同期版。サイトマップ取得を日付ごとに並列化し、
    本文取得も ``max_concurrency_content`` で同時実行数を制限しながら並列化する。

    Parameters
    ----------
    start_date : datetime
        開始日
    end_date : datetime
        終了日
    config : ScraperConfig | None
        スクレイパー設定（None でデフォルト）
    output_dir : str | Path | None
        出力ディレクトリ（None で保存しない）

    Returns
    -------
    pd.DataFrame
        収集した記事のデータフレーム

    Examples
    --------
    >>> import asyncio
    >>> from datetime import datetime
    >>> async def main():
    ...     df = await async_collect_historical_news(
    ...         start_date=datetime(2024, 1, 1),
    ...         end_date=datetime(2024, 1, 7),
    ...     )
    ...     print(len(df))
    >>> asyncio.run(main())
    """
    from playwright.async_api import async_playwright  # type: ignore[import-not-found]

    if config is None:
        config = ScraperConfig()

    output_path: Path | None = None
    if output_dir:
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)

    # 日付リストを生成
    dates: list[datetime] = []
    current = start_date
    while current <= end_date:
        dates.append(current)
        current += timedelta(days=1)

    # Playwright ブラウザを起動
    playwright = None
    browser = None
    if config.use_playwright:
        playwright = await async_playwright().start()
        browser = await playwright.chromium.launch(headless=True)

    try:
        # サイトマップ取得を日付ごとに並列化
        sitemap_limiter = RateLimiter(
            delay=config.delay, max_concurrency=config.max_concurrency
        )

        async def _fetch_sitemap_for_date(
            date: datetime,
        ) -> tuple[datetime, list[dict]]:
            async with sitemap_limiter:
                articles = await async_fetch_sitemap_articles_playwright(
                    date.year, date.month, date.day, browser=browser
                )
                return date, articles

        sitemap_tasks = [asyncio.create_task(_fetch_sitemap_for_date(d)) for d in dates]
        sitemap_results = await gather_with_errors(sitemap_tasks, logger)

        # 日付別に結果を整理
        all_articles: list[dict] = []
        date_articles_map: dict[str, list[dict]] = {}

        for date, articles in sitemap_results:
            date_str = date.strftime("%Y-%m-%d")
            date_articles_map[date_str] = articles
            all_articles.extend(articles)

        # 本文取得（include_content=True の場合）
        if config.include_content and all_articles:
            session = create_async_session(
                impersonate=config.impersonate,
                proxy=config.proxy,
            )

            content_limiter = RateLimiter(
                delay=config.delay,
                max_concurrency=config.max_concurrency_content,
            )

            async def _fetch_content(article: dict) -> tuple[str, str]:
                async with content_limiter:
                    content_data = await async_fetch_article_content(
                        session, article["url"], config.timeout
                    )
                    content = content_data.get("content", "") if content_data else ""
                    return article["url"], content

            content_tasks = [
                asyncio.create_task(_fetch_content(a)) for a in all_articles
            ]
            content_results = await gather_with_errors(content_tasks, logger)

            # URL をキーにした content マップ
            content_map: dict[str, str] = {}
            for url, content in content_results:
                content_map[url] = content

            # 記事に content を追加
            for article in all_articles:
                article["content"] = content_map.get(article["url"], "")

        # 日別に JSON 保存
        if output_path:
            for date_str, articles in date_articles_map.items():
                with open(output_path / f"{date_str}.json", "w", encoding="utf-8") as f:
                    json.dump(articles, f, ensure_ascii=False, indent=2)

    finally:
        if browser:
            await browser.close()
        if playwright:
            await playwright.stop()

    df = pd.DataFrame(all_articles)

    if output_path and not df.empty:
        df.to_parquet(output_path / "all_articles.parquet", index=False)

    return df


# 後方互換性のためのエイリアス
QUANT_CATEGORIES = CNBC_QUANT_CATEGORIES
