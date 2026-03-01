"""NASDAQ ニューススクレイパー.

curl-cffi（ブラウザ偽装）+ trafilatura（本文抽出）を使用。
カテゴリ別・銘柄別のニュース収集に対応。
"""

import asyncio
import re
import time
from datetime import datetime
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
from .types import NASDAQ_CATEGORIES, NASDAQ_QUANT_CATEGORIES, Article, ScraperConfig

logger = get_logger(__name__)


def _parse_article_date(date_str: str) -> datetime | None:
    """NASDAQ API/ページの日付文字列を datetime にパースする.

    複数の日付フォーマットを順次試行し、最初にパース成功した datetime を返す。
    いずれのフォーマットにもマッチしない場合は None を返す。

    Parameters
    ----------
    date_str : str
        パース対象の日付文字列。対応フォーマット:
        - ISO 8601: "2026-02-23T12:00:00+00:00", "2026-02-23T12:00:00Z"
        - "MM/DD/YYYY": "02/23/2026"
        - "Month DD, YYYY": "February 23, 2026"
        - "Mon DD, YYYY": "Feb 23, 2026"

    Returns
    -------
    datetime | None
        パース成功時は datetime オブジェクト、失敗時は None
    """
    if not date_str:
        return None

    # ISO 8601: "2026-02-23T12:00:00Z" のZサフィックスを標準形式に変換
    normalized = date_str.strip()
    if normalized.endswith("Z"):
        normalized = normalized[:-1] + "+00:00"

    # 試行するフォーマット一覧（優先順）
    formats = [
        "%Y-%m-%dT%H:%M:%S%z",  # ISO 8601 with timezone: 2026-02-23T12:00:00+00:00
        "%Y-%m-%dT%H:%M:%S",  # ISO 8601 without timezone: 2026-02-23T12:00:00
        "%Y-%m-%d",  # ISO 8601 date only: 2026-02-23
        "%m/%d/%Y",  # MM/DD/YYYY: 02/23/2026
        "%B %d, %Y",  # Month DD, YYYY: February 23, 2026
        "%b %d, %Y",  # Mon DD, YYYY: Feb 23, 2026
    ]

    for fmt in formats:
        try:
            return datetime.strptime(normalized, fmt)
        except (ValueError, TypeError):
            continue

    logger.debug("Failed to parse date string", date_str=date_str)
    return None


def _category_to_url_segment(category: str) -> str:
    """NASDAQ_CATEGORIES をアーカイブページの URL パスに変換する.

    カテゴリ名を小文字に変換し、URL セグメントとして適切な形式を返す。
    NASDAQ_CATEGORIES に含まれないカテゴリを渡した場合は ValueError を送出する。

    Parameters
    ----------
    category : str
        NASDAQ_CATEGORIES に含まれるカテゴリ名（例: "Markets", "Personal-Finance"）

    Returns
    -------
    str
        URL パスセグメント（小文字）。例: "markets", "personal-finance"

    Raises
    ------
    ValueError
        category が NASDAQ_CATEGORIES に含まれない場合

    Examples
    --------
    >>> _category_to_url_segment("Markets")
    'markets'
    >>> _category_to_url_segment("Personal-Finance")
    'personal-finance'
    """
    if category not in NASDAQ_CATEGORIES:
        raise ValueError(
            f"Unknown NASDAQ category: {category!r}. "
            f"Valid categories: {sorted(NASDAQ_CATEGORIES)}"
        )
    return category.lower()


def fetch_rss_feed(
    session: requests.Session,
    category: str | None = None,
    timeout: int = 30,
) -> list[Article]:
    """カテゴリ別 RSS フィードから記事一覧を取得する.

    Parameters
    ----------
    session : requests.Session
        HTTP セッション
    category : str | None
        カテゴリ名（None で全体フィード）
    timeout : int
        タイムアウト秒数

    Returns
    -------
    list[Article]
        記事情報のリスト
    """
    if category:
        if category not in NASDAQ_CATEGORIES:
            raise ValueError(
                f"Invalid NASDAQ category: {category!r}. "
                f"Valid categories: {sorted(NASDAQ_CATEGORIES)}"
            )
        url = f"https://www.nasdaq.com/feed/rssoutbound?category={category}"
    else:
        url = "https://www.nasdaq.com/feed/rssoutbound"

    logger.debug("Fetching NASDAQ RSS", category=category or "general")

    resp = session.get(url, timeout=timeout)
    resp.raise_for_status()

    feed = feedparser.parse(resp.text)

    articles = []
    for entry in feed.entries:
        # 公開日時のパース
        published_raw = str(entry.get("published", ""))
        try:
            pub_dt = datetime.strptime(published_raw, "%a, %d %b %Y %H:%M:%S %z")
            published_iso = pub_dt.isoformat()
        except (ValueError, TypeError):
            published_iso = published_raw

        articles.append(
            Article(
                title=str(entry.get("title", "")),
                url=str(entry.get("link", "")),
                published=published_iso,
                summary=str(entry.get("summary", "")),
                category=category or "general",
                source="nasdaq",
            )
        )

    logger.info(
        "NASDAQ RSS fetched",
        category=category or "general",
        article_count=len(articles),
    )
    return articles


async def async_fetch_rss_feed(
    session: AsyncSession,
    category: str | None = None,
    timeout: int = 30,
) -> list[Article]:
    """カテゴリ別 RSS フィードから記事一覧を非同期で取得する.

    ``fetch_rss_feed`` の非同期版。HTTP 取得を ``await session.get()``
    で非同期化し、``feedparser.parse()`` による XML 解析は同期のまま実行する。
    公開日時は ISO 8601 形式に変換する。

    Parameters
    ----------
    session : AsyncSession
        非同期 HTTP セッション（``create_async_session()`` で作成）
    category : str | None
        カテゴリ名（None で全体フィード）
    timeout : int
        タイムアウト秒数

    Returns
    -------
    list[Article]
        記事情報のリスト

    Examples
    --------
    >>> import asyncio
    >>> from news_scraper.session import create_async_session
    >>> async def main():
    ...     session = create_async_session()
    ...     articles = await async_fetch_rss_feed(session, "Markets")
    ...     print(len(articles))
    >>> asyncio.run(main())
    """
    if category:
        url = f"https://www.nasdaq.com/feed/rssoutbound?category={category}"
    else:
        url = "https://www.nasdaq.com/feed/rssoutbound"

    logger.debug("Fetching NASDAQ RSS (async)", category=category or "general")

    resp = await session.get(url, timeout=timeout)
    resp.raise_for_status()

    feed = feedparser.parse(resp.text)

    articles = []
    for entry in feed.entries:
        # 公開日時のパース
        published_raw = str(entry.get("published", ""))
        try:
            pub_dt = datetime.strptime(published_raw, "%a, %d %b %Y %H:%M:%S %z")
            published_iso = pub_dt.isoformat()
        except (ValueError, TypeError):
            published_iso = published_raw

        articles.append(
            Article(
                title=str(entry.get("title", "")),
                url=str(entry.get("link", "")),
                published=published_iso,
                summary=str(entry.get("summary", "")),
                category=category or "general",
                source="nasdaq",
            )
        )

    logger.info(
        "NASDAQ RSS fetched (async)",
        category=category or "general",
        article_count=len(articles),
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
    URL ベースの重複除去を行い、ユニークな記事のみを返す。

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
        全記事のデータフレーム（URL ベースの重複除去済み）

    Examples
    --------
    >>> import asyncio
    >>> from news_scraper.session import create_async_session
    >>> from news_scraper.types import ScraperConfig
    >>> async def main():
    ...     session = create_async_session()
    ...     df = await async_fetch_multiple_categories(
    ...         session, ["Markets", "Earnings"], ScraperConfig()
    ...     )
    ...     print(len(df))
    >>> asyncio.run(main())
    """
    if config is None:
        config = ScraperConfig()

    if categories is None:
        categories = NASDAQ_CATEGORIES

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

    df = pd.DataFrame(all_articles)
    if not df.empty:
        df = df.drop_duplicates(subset=["url"])

    return df


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
        全記事のデータフレーム（重複除去済み）
    """
    if categories is None:
        categories = NASDAQ_CATEGORIES

    all_articles = []

    for category in categories:
        try:
            articles = fetch_rss_feed(session, category, timeout)
            all_articles.extend([a.to_dict() for a in articles])
        except Exception as e:
            logger.error(
                "NASDAQ category fetch failed", category=category, error=str(e)
            )

        time.sleep(delay)

    df = pd.DataFrame(all_articles)
    if not df.empty:
        df = df.drop_duplicates(subset=["url"])

    return df


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
        article_el = soup.select_one("article") or soup.select_one(".article-body")
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

    author_el = soup.select_one('[rel="author"]') or soup.select_one(".author")
    author = author_el.get_text(strip=True) if author_el else ""

    return {
        "url": url,
        "title": title,
        "published": published,
        "author": author,
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
    著者情報の抽出も含む。

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
        - ``author``: 著者名
        - ``content``: 本文テキスト

    Examples
    --------
    >>> import asyncio
    >>> from news_scraper.session import create_async_session
    >>> async def main():
    ...     session = create_async_session()
    ...     result = await async_fetch_article_content(
    ...         session, "https://www.nasdaq.com/articles/example"
    ...     )
    ...     if result:
    ...         print(result["title"])
    >>> asyncio.run(main())
    """
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
            article_el = soup.select_one("article") or soup.select_one(".article-body")
            if article_el:
                return article_el.get_text(separator="\n", strip=True)
            return None

        text = await asyncio.to_thread(_bs4_fallback, html)

    if not text:
        return None

    # メタデータ抽出（スレッドプールへオフロード）
    def _extract_metadata(html_content: str) -> tuple[str, str, str]:
        soup = BeautifulSoup(html_content, "html.parser")
        title_el = soup.select_one("h1")
        title = title_el.get_text(strip=True) if title_el else ""
        time_el = soup.select_one("time")
        published = str(time_el.get("datetime", "")) if time_el else ""
        author_el = soup.select_one('[rel="author"]') or soup.select_one(".author")
        author = author_el.get_text(strip=True) if author_el else ""
        return title, published, author

    title, published, author = await asyncio.to_thread(_extract_metadata, html)

    return {
        "url": url,
        "title": title,
        "published": published,
        "author": author,
        "content": text,
    }


def fetch_stock_news_api(
    session: requests.Session,
    ticker: str,
    limit: int = 20,
    timeout: int = 30,
) -> list[Article]:
    """NASDAQ API から銘柄別ニュースを取得する.

    Parameters
    ----------
    session : requests.Session
        HTTP セッション
    ticker : str
        銘柄コード（例: AAPL, MSFT）
    limit : int
        取得件数
    timeout : int
        タイムアウト秒数

    Returns
    -------
    list[Article]
        記事情報のリスト
    """
    if not re.fullmatch(r"[A-Za-z0-9.\-]{1,10}", ticker):
        raise ValueError(
            f"Invalid ticker symbol: {ticker!r}. "
            "Only alphanumeric characters, dots, and hyphens are allowed (max 10 chars)."
        )

    url = f"https://api.nasdaq.com/api/news/topic/articlebysymbol?q={ticker}|STOCKS&offset=0&limit={limit}"

    headers = {
        "Accept": "application/json",
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
    }

    logger.debug("Fetching NASDAQ stock news", ticker=ticker)

    try:
        resp = session.get(url, headers=headers, timeout=timeout)
        resp.raise_for_status()
        data = resp.json()

        articles = []
        rows = data.get("data", {}).get("rows", [])

        for row in rows:
            articles.append(
                Article(
                    title=row.get("title", ""),
                    url=row.get("url", ""),
                    published=row.get("created", ""),
                    ticker=ticker.upper(),
                    author=row.get("provider", ""),
                    source="nasdaq",
                )
            )

        logger.info(
            "NASDAQ stock news fetched", ticker=ticker, article_count=len(articles)
        )
        return articles

    except Exception as e:
        logger.error("NASDAQ API failed", ticker=ticker, error=str(e))
        return []


async def async_fetch_stock_news_api(
    session: AsyncSession,
    ticker: str,
    limit: int = 20,
    timeout: int = 30,
) -> list[Article]:
    """NASDAQ API から銘柄別ニュースを非同期で取得する.

    ``fetch_stock_news_api`` の非同期版。HTTP 取得を ``await session.get()``
    で非同期化し、JSON レスポンスのパースは同期で実行する。
    API エラー時は空リストを返しログ出力する。

    Parameters
    ----------
    session : AsyncSession
        非同期 HTTP セッション（``create_async_session()`` で作成）
    ticker : str
        銘柄コード（例: AAPL, MSFT）
    limit : int
        取得件数
    timeout : int
        タイムアウト秒数

    Returns
    -------
    list[Article]
        記事情報のリスト

    Examples
    --------
    >>> import asyncio
    >>> from news_scraper.session import create_async_session
    >>> async def main():
    ...     session = create_async_session()
    ...     articles = await async_fetch_stock_news_api(session, "AAPL")
    ...     print(len(articles))
    >>> asyncio.run(main())
    """
    if not re.fullmatch(r"[A-Za-z0-9.\-]{1,10}", ticker):
        raise ValueError(
            f"Invalid ticker symbol: {ticker!r}. "
            "Only alphanumeric characters, dots, and hyphens are allowed (max 10 chars)."
        )

    url = f"https://api.nasdaq.com/api/news/topic/articlebysymbol?q={ticker.upper()}|STOCKS&offset=0&limit={limit}"

    headers = {
        "Accept": "application/json",
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
    }

    logger.debug("Fetching NASDAQ stock news (async)", ticker=ticker)

    try:
        resp = await session.get(url, headers=headers, timeout=timeout)
        resp.raise_for_status()
        data = resp.json()

        articles = []
        rows = data.get("data", {}).get("rows", [])

        for row in rows:
            articles.append(
                Article(
                    title=row.get("title", ""),
                    url=row.get("url", ""),
                    published=row.get("created", ""),
                    ticker=ticker.upper(),
                    author=row.get("provider", ""),
                    source="nasdaq",
                )
            )

        logger.info(
            "NASDAQ stock news fetched (async)",
            ticker=ticker,
            article_count=len(articles),
        )
        return articles

    except Exception as e:
        logger.error("NASDAQ API failed (async)", ticker=ticker, error=str(e))
        return []


async def async_fetch_multiple_stocks(
    session: AsyncSession,
    tickers: list[str],
    limit: int = 20,
    config: ScraperConfig | None = None,
) -> pd.DataFrame:
    """複数銘柄のニュースを並列で非同期取得する.

    ``RateLimiter`` で同時実行数を ``config.max_concurrency`` に制限し、
    ``gather_with_errors`` でエラーを許容しながら並列実行する。
    URL ベースの重複除去を行い、ユニークな記事のみを返す。

    Parameters
    ----------
    session : AsyncSession
        非同期 HTTP セッション（``create_async_session()`` で作成）
    tickers : list[str]
        銘柄コードのリスト（例: ["AAPL", "MSFT"]）
    limit : int
        各銘柄の取得件数
    config : ScraperConfig | None
        スクレイパー設定（None でデフォルト）

    Returns
    -------
    pd.DataFrame
        全記事のデータフレーム（URL ベースの重複除去済み）

    Examples
    --------
    >>> import asyncio
    >>> from news_scraper.session import create_async_session
    >>> from news_scraper.types import ScraperConfig
    >>> async def main():
    ...     session = create_async_session()
    ...     df = await async_fetch_multiple_stocks(
    ...         session, ["AAPL", "MSFT"], limit=20, config=ScraperConfig()
    ...     )
    ...     print(len(df))
    >>> asyncio.run(main())
    """
    if config is None:
        config = ScraperConfig()

    if not tickers:
        return pd.DataFrame()

    limiter = RateLimiter(delay=config.delay, max_concurrency=config.max_concurrency)

    async def _fetch_ticker(ticker: str) -> list[Article]:
        async with limiter:
            return await async_fetch_stock_news_api(
                session, ticker, limit, config.timeout
            )

    tasks = [asyncio.create_task(_fetch_ticker(t)) for t in tickers]
    results = await gather_with_errors(tasks, logger)

    all_articles: list[dict] = []
    for article_list in results:
        all_articles.extend([a.to_dict() for a in article_list])

    df = pd.DataFrame(all_articles)
    if not df.empty:
        df = df.drop_duplicates(subset=["url"])

    return df


def fetch_multiple_stocks(
    session: requests.Session,
    tickers: list[str],
    limit: int = 20,
    delay: float = 1.0,
    timeout: int = 30,
) -> pd.DataFrame:
    """複数銘柄のニュースを取得する.

    Parameters
    ----------
    session : requests.Session
        HTTP セッション
    tickers : list[str]
        銘柄コードのリスト
    limit : int
        各銘柄の取得件数
    delay : float
        リクエスト間の待機秒数
    timeout : int
        タイムアウト秒数

    Returns
    -------
    pd.DataFrame
        全記事のデータフレーム（重複除去済み）
    """
    all_articles = []

    for ticker in tickers:
        try:
            articles = fetch_stock_news_api(session, ticker, limit, timeout)
            all_articles.extend([a.to_dict() for a in articles])
        except Exception as e:
            logger.error("NASDAQ ticker fetch failed", ticker=ticker, error=str(e))

        time.sleep(delay)

    df = pd.DataFrame(all_articles)
    if not df.empty:
        df = df.drop_duplicates(subset=["url"])

    return df


def collect_nasdaq_news(
    categories: list[str] | None = None,
    tickers: list[str] | None = None,
    config: ScraperConfig | None = None,
    output_dir: str | Path | None = None,
) -> pd.DataFrame:
    """NASDAQ ニュースを一括収集する.

    Parameters
    ----------
    categories : list[str] | None
        収集するカテゴリ
    tickers : list[str] | None
        収集する銘柄コード
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
    >>> df = collect_nasdaq_news(
    ...     categories=["Markets", "Earnings"],
    ...     tickers=["AAPL", "MSFT"],
    ... )
    """
    if config is None:
        config = ScraperConfig()

    output_path: Path | None = None
    if output_dir:
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)

    session = create_session(impersonate=config.impersonate, proxy=config.proxy)
    all_articles = []

    # カテゴリ別収集
    if categories:
        df_cat = fetch_multiple_categories(
            session, categories, config.delay, config.timeout
        )
        all_articles.extend(df_cat.to_dict("records"))

    # 銘柄別収集
    if tickers:
        df_stock = fetch_multiple_stocks(
            session, tickers, delay=config.delay, timeout=config.timeout
        )
        all_articles.extend(df_stock.to_dict("records"))

    df = pd.DataFrame(all_articles)

    if df.empty:
        return df

    df = df.drop_duplicates(subset=["url"])

    # 本文取得
    if config.include_content:
        contents = []
        for _i, row in df.iterrows():
            content_data = fetch_article_content(
                session, str(row["url"]), config.timeout
            )
            contents.append(content_data.get("content", "") if content_data else "")
            time.sleep(config.delay)
        df["content"] = contents

    # 保存
    if output_path and not df.empty:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        df.to_json(
            output_path / f"nasdaq_{timestamp}.json",
            orient="records",
            force_ascii=False,
            indent=2,
        )
        df.to_parquet(output_path / f"nasdaq_{timestamp}.parquet", index=False)

    return df


async def async_collect_nasdaq_news(
    categories: list[str] | None = None,
    tickers: list[str] | None = None,
    config: ScraperConfig | None = None,
    output_dir: str | Path | None = None,
) -> pd.DataFrame:
    """NASDAQ ニュースを非同期で一括収集する.

    ``collect_nasdaq_news`` の非同期版。カテゴリ取得と銘柄取得を
    ``asyncio.gather()`` で並列実行し、``include_content=True`` 時の
    本文取得を ``max_concurrency_content`` で並列化する。

    Parameters
    ----------
    categories : list[str] | None
        収集するカテゴリ（None で収集しない）
    tickers : list[str] | None
        収集する銘柄コード（None で収集しない）
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
    >>> async def main():
    ...     df = await async_collect_nasdaq_news(
    ...         categories=["Markets", "Earnings"],
    ...         tickers=["AAPL", "MSFT"],
    ...     )
    ...     print(len(df))
    >>> asyncio.run(main())
    """
    if config is None:
        config = ScraperConfig()

    output_path: Path | None = None
    if output_dir:
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)

    session = create_async_session(
        impersonate=config.impersonate,
        proxy=config.proxy,
    )

    # カテゴリ取得と銘柄取得を並列実行
    gather_tasks: list[asyncio.Task[pd.DataFrame]] = []

    if categories:
        gather_tasks.append(
            asyncio.create_task(
                async_fetch_multiple_categories(session, categories, config)
            )
        )

    if tickers:
        gather_tasks.append(
            asyncio.create_task(
                async_fetch_multiple_stocks(session, tickers, config=config)
            )
        )

    if not gather_tasks:
        return pd.DataFrame()

    results = await gather_with_errors(gather_tasks, logger)

    # 結果を結合
    all_articles: list[dict] = []
    for df_result in results:
        if not df_result.empty:
            all_articles.extend(df_result.to_dict("records"))

    df = pd.DataFrame(all_articles)

    if df.empty:
        return df

    # URL ベースの重複除去
    df = df.drop_duplicates(subset=["url"])

    # 本文取得（include_content=True の場合）
    if config.include_content:
        content_limiter = RateLimiter(
            delay=config.delay,
            max_concurrency=config.max_concurrency_content,
        )

        async def _fetch_content(url: str) -> tuple[str, str]:
            async with content_limiter:
                content_data = await async_fetch_article_content(
                    session, url, config.timeout
                )
                content = content_data.get("content", "") if content_data else ""
                return url, content

        content_tasks = [
            asyncio.create_task(_fetch_content(str(row["url"])))
            for _, row in df.iterrows()
        ]
        content_results = await gather_with_errors(content_tasks, logger)

        # URL をキーにした content マップ
        content_map: dict[str, str] = {}
        for url, content in content_results:
            content_map[url] = content

        df["content"] = df["url"].map(lambda u: content_map.get(u, ""))

    # 保存
    if output_path and not df.empty:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        df.to_json(
            output_path / f"nasdaq_{timestamp}.json",
            orient="records",
            force_ascii=False,
            indent=2,
        )
        df.to_parquet(output_path / f"nasdaq_{timestamp}.parquet", index=False)

    return df


# 後方互換性のためのエイリアス
QUANT_CATEGORIES = NASDAQ_QUANT_CATEGORIES
