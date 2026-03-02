"""NASDAQ ニューススクレイパー.

curl-cffi（ブラウザ偽装）+ trafilatura（本文抽出）を使用。
カテゴリ別・銘柄別のニュース収集に対応。
"""

import asyncio
import json
import re
import time
from collections import defaultdict
from datetime import datetime
from pathlib import Path
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

try:
    # Playwright はオプション依存。インストール時のみモジュールスコープに公開し、
    # テスト時に patch("news_scraper.nasdaq.sync_playwright") でモック差し替えを可能にする。
    from playwright.async_api import async_playwright  # type: ignore[import-not-found]
    from playwright.sync_api import sync_playwright  # type: ignore[import-not-found]
except ImportError:  # pragma: no cover
    sync_playwright = None  # type: ignore[assignment]
    async_playwright = None  # type: ignore[assignment]


logger = get_logger(__name__)


# --- モジュール定数 ---
_NASDAQ_API_HEADERS: dict[str, str] = {
    "Accept": "application/json",
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
}
_TICKER_RE = re.compile(r"[A-Za-z0-9.\-]{1,10}")


def _validate_ticker(ticker: str) -> None:
    """ティッカーシンボルのバリデーション.

    Parameters
    ----------
    ticker : str
        検証するティッカーシンボル

    Raises
    ------
    ValueError
        ティッカーが不正な形式の場合
    """
    if not _TICKER_RE.fullmatch(ticker):
        raise ValueError(
            f"Invalid ticker symbol: {ticker!r}. "
            "Only alphanumeric characters, dots, and hyphens are allowed (max 10 chars)."
        )


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
        "%a, %d %b %Y %H:%M:%S %z",  # RSS/RFC 2822: Mon, 23 Feb 2026 12:00:00 +0000
    ]

    for fmt in formats:
        try:
            return datetime.strptime(normalized, fmt)
        except (ValueError, TypeError):
            continue

    logger.debug("Failed to parse date string", date_str=date_str)
    return None


def _parse_rss_entry(entry: object, category: str | None) -> Article:
    """feedparser のエントリを Article に変換する.

    Parameters
    ----------
    entry : object
        feedparser のエントリオブジェクト
    category : str | None
        カテゴリ名（None で "general"）

    Returns
    -------
    Article
        変換された記事情報
    """
    published_raw = str(entry.get("published", ""))  # type: ignore[union-attr]
    # RSSの日付フォーマット: "Mon, DD Mon YYYY HH:MM:SS +ZZZZ"
    parsed_dt = _parse_article_date(published_raw)
    published_iso = parsed_dt.isoformat() if parsed_dt else published_raw

    return Article(
        title=str(entry.get("title", "")),  # type: ignore[union-attr]
        url=str(entry.get("link", "")),  # type: ignore[union-attr]
        published=published_iso,
        summary=str(entry.get("summary", "")),  # type: ignore[union-attr]
        category=category or "general",
        source="nasdaq",
    )


def _row_to_article(row: dict[str, object], ticker_upper: str) -> Article:
    """NASDAQ API のレスポンス行を Article に変換する.

    Parameters
    ----------
    row : dict[str, object]
        APIレスポンスの rows 要素
    ticker_upper : str
        大文字のティッカーシンボル

    Returns
    -------
    Article
        変換された記事情報
    """
    return Article(
        title=str(row.get("title", "")),
        url=str(row.get("url", "")),
        published=str(row.get("created", "")),
        ticker=ticker_upper,
        author=str(row.get("provider", "")),
        source="nasdaq",
    )


def _filter_article_by_date(
    pub_dt: datetime | None,
    start_date: datetime | None,
    end_date: datetime | None,
) -> tuple[bool, bool]:
    """記事の日付を start_date/end_date でフィルタリングする.

    Parameters
    ----------
    pub_dt : datetime | None
        記事の公開日時
    start_date : datetime | None
        この日時より古い記事を除外（None で制限なし）
    end_date : datetime | None
        この日時より新しい記事を除外（None で制限なし）

    Returns
    -------
    tuple[bool, bool]
        (skip_article, is_older_than_start)
        - skip_article: True なら記事をスキップ
        - is_older_than_start: True なら start_date より古い（ページ終了判定に使用）
    """
    if pub_dt is None:
        return False, False

    # tzinfo を除去して比較（naive datetime に統一）
    pub_naive = pub_dt.replace(tzinfo=None) if pub_dt.tzinfo else pub_dt

    # end_date フィルタリング
    if end_date is not None:
        end_naive = end_date.replace(tzinfo=None) if end_date.tzinfo else end_date
        if pub_naive > end_naive:
            return True, False

    # start_date フィルタリング
    if start_date is not None:
        start_naive = (
            start_date.replace(tzinfo=None) if start_date.tzinfo else start_date
        )
        if pub_naive < start_naive:
            return True, True  # 古い記事なのでスキップ & older_than_start フラグ
        return False, False  # start_date 以降の記事なのでスキップしない

    return False, False


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

    articles = [_parse_rss_entry(entry, category) for entry in feed.entries]

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

    articles = [_parse_rss_entry(entry, category) for entry in feed.entries]

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
    soup = BeautifulSoup(html, "html.parser")

    # trafilatura で本文抽出
    text = trafilatura.extract(
        html,
        include_comments=False,
        include_tables=False,
        no_fallback=False,
    )

    if not text:
        # フォールバック: BeautifulSoup
        article_el = soup.select_one("article") or soup.select_one(".article-body")
        if article_el:
            text = article_el.get_text(separator="\n", strip=True)

    if not text:
        return None

    # メタデータ抽出（soup を再利用）
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

    # BS4フォールバック・メタデータ抽出を1回のスレッドで処理（soup を再利用）
    def _bs4_parse(
        html_content: str, extracted_text: str | None
    ) -> tuple[str | None, str, str, str]:
        soup = BeautifulSoup(html_content, "html.parser")

        # フォールバック: BeautifulSoup で本文抽出
        result_text = extracted_text
        if not result_text:
            article_el = soup.select_one("article") or soup.select_one(".article-body")
            if article_el:
                result_text = article_el.get_text(separator="\n", strip=True)

        # メタデータ抽出（soup を再利用）
        title_el = soup.select_one("h1")
        title = title_el.get_text(strip=True) if title_el else ""
        time_el = soup.select_one("time")
        published = str(time_el.get("datetime", "")) if time_el else ""
        author_el = soup.select_one('[rel="author"]') or soup.select_one(".author")
        author = author_el.get_text(strip=True) if author_el else ""
        return result_text, title, published, author

    text, title, published, author = await asyncio.to_thread(_bs4_parse, html, text)

    if not text:
        return None

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
    _validate_ticker(ticker)

    url = f"https://api.nasdaq.com/api/news/topic/articlebysymbol?q={ticker}|STOCKS&offset=0&limit={limit}"

    logger.debug("Fetching NASDAQ stock news", ticker=ticker)

    try:
        resp = session.get(url, headers=_NASDAQ_API_HEADERS, timeout=timeout)
        resp.raise_for_status()
        data = resp.json()

        rows = data.get("data", {}).get("rows", [])
        ticker_upper = ticker.upper()
        articles = [_row_to_article(row, ticker_upper) for row in rows]

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
    _validate_ticker(ticker)

    url = f"https://api.nasdaq.com/api/news/topic/articlebysymbol?q={ticker.upper()}|STOCKS&offset=0&limit={limit}"

    logger.debug("Fetching NASDAQ stock news (async)", ticker=ticker)

    try:
        resp = await session.get(url, headers=_NASDAQ_API_HEADERS, timeout=timeout)
        resp.raise_for_status()
        data = resp.json()

        rows = data.get("data", {}).get("rows", [])
        articles = [_row_to_article(row, ticker.upper()) for row in rows]

        logger.info(
            "NASDAQ stock news fetched (async)",
            ticker=ticker,
            article_count=len(articles),
        )
        return articles

    except Exception as e:
        logger.error("NASDAQ API failed (async)", ticker=ticker, error=str(e))
        return []


def _build_pagination_url(ticker_upper: str, offset: int, page_size: int) -> str:
    """ページネーション取得用 URL を構築する."""
    return (
        f"https://api.nasdaq.com/api/news/topic/articlebysymbol"
        f"?q={ticker_upper}|STOCKS"
        f"&offset={offset}&limit={page_size}"
    )


def _process_pagination_page(
    data: dict,
    ticker_upper: str,
    start_date: datetime | None,
    end_date: datetime | None,
) -> tuple[list[Article], int, bool, bool]:
    """ページレスポンスデータを処理して記事リストと制御フラグを返す.

    Parameters
    ----------
    data : dict
        NASDAQ API のレスポンス JSON
    ticker_upper : str
        大文字化済みティッカーシンボル
    start_date : datetime | None
        取得開始日時
    end_date : datetime | None
        取得終了日時

    Returns
    -------
    tuple[list[Article], int, bool, bool]
        (articles, total_records, all_older_than_start, rows_empty)
        rows_empty が True のとき rows が空でループを打ち切る必要がある
    """
    data_section = data.get("data", {})
    rows = data_section.get("rows", [])
    total_records_str = data_section.get("totalrecords", "0")
    try:
        total_records = int(total_records_str)
    except (ValueError, TypeError):
        total_records = 0

    if not rows:
        return [], total_records, False, True

    page_articles: list[Article] = []
    all_older_than_start = start_date is not None

    for row in rows:
        pub_str = row.get("created", "")
        pub_dt = _parse_article_date(pub_str)
        skip, is_older = _filter_article_by_date(pub_dt, start_date, end_date)
        if not is_older:
            all_older_than_start = False
        if skip:
            continue
        page_articles.append(_row_to_article(row, ticker_upper))

    return page_articles, total_records, all_older_than_start, False


def fetch_stock_news_api_paginated(
    session: requests.Session,
    ticker: str,
    max_articles: int = 200,
    page_size: int = 20,
    start_date: datetime | None = None,
    end_date: datetime | None = None,
    config: ScraperConfig | None = None,
) -> list[Article]:
    """NASDAQ API から銘柄別ニュースをページネーションで取得する.

    ``offset`` パラメータを ``0, page_size, 2*page_size, ...`` とループしながら
    複数ページの記事を取得する。以下の条件のいずれかを満たすと終了する:

    - ``offset >= data.totalrecords``（全記事取得済み）
    - ``offset >= max_articles``（上限到達）
    - レスポンスの rows が空
    - 全記事が ``start_date`` より古い（日付フィルタリング）

    Parameters
    ----------
    session : requests.Session
        HTTP セッション
    ticker : str
        銘柄コード（例: AAPL, MSFT）
    max_articles : int
        最大取得件数
    page_size : int
        1 ページの取得件数
    start_date : datetime | None
        この日時より古い記事を除外（None で全期間）
    end_date : datetime | None
        この日時より新しい記事を除外（None で制限なし）
    config : ScraperConfig | None
        スクレイパー設定（None でデフォルト）

    Returns
    -------
    list[Article]
        記事情報のリスト（API エラー時は取得済みの部分結果）
    """
    _validate_ticker(ticker)

    if config is None:
        config = ScraperConfig()

    from .types import get_delay

    ticker_upper = ticker.upper()
    articles: list[Article] = []
    offset = 0

    logger.debug(
        "Fetching NASDAQ stock news paginated",
        ticker=ticker_upper,
        max_articles=max_articles,
        page_size=page_size,
    )

    while offset < max_articles:
        url = _build_pagination_url(ticker_upper, offset, page_size)

        try:
            resp = session.get(url, headers=_NASDAQ_API_HEADERS, timeout=config.timeout)
            resp.raise_for_status()
            data = resp.json()
        except Exception as e:
            logger.error(
                "NASDAQ paginated API failed",
                ticker=ticker_upper,
                offset=offset,
                error=str(e),
            )
            break

        page_articles, total_records, all_older_than_start, rows_empty = (
            _process_pagination_page(data, ticker_upper, start_date, end_date)
        )

        # 空 rows で早期終了
        if rows_empty:
            logger.debug(
                "Empty rows, stopping pagination", ticker=ticker_upper, offset=offset
            )
            break

        articles.extend(page_articles)
        offset += page_size

        # 全記事が start_date より古い場合は早期終了
        if all_older_than_start:
            logger.debug(
                "All articles older than start_date, stopping",
                ticker=ticker_upper,
                offset=offset,
            )
            break

        # totalrecords で終了判定
        if total_records > 0 and offset >= total_records:
            logger.debug(
                "Reached totalrecords, stopping pagination",
                ticker=ticker_upper,
                offset=offset,
                total_records=total_records,
            )
            break

        # ページ間レートリミット
        delay = get_delay(config)
        time.sleep(delay)

    logger.info(
        "NASDAQ stock news paginated fetch completed",
        ticker=ticker_upper,
        article_count=len(articles),
    )
    return articles


async def async_fetch_stock_news_api_paginated(
    session: AsyncSession,
    ticker: str,
    max_articles: int = 200,
    page_size: int = 20,
    start_date: datetime | None = None,
    end_date: datetime | None = None,
    config: ScraperConfig | None = None,
) -> list[Article]:
    """NASDAQ API から銘柄別ニュースをページネーションで非同期取得する.

    ``fetch_stock_news_api_paginated`` の非同期版。HTTP 取得を
    ``await session.get()`` で非同期化し、ページ間の待機を
    ``asyncio.sleep()`` で実行する。

    Parameters
    ----------
    session : AsyncSession
        非同期 HTTP セッション（``create_async_session()`` で作成）
    ticker : str
        銘柄コード（例: AAPL, MSFT）
    max_articles : int
        最大取得件数
    page_size : int
        1 ページの取得件数
    start_date : datetime | None
        この日時より古い記事を除外（None で全期間）
    end_date : datetime | None
        この日時より新しい記事を除外（None で制限なし）
    config : ScraperConfig | None
        スクレイパー設定（None でデフォルト）

    Returns
    -------
    list[Article]
        記事情報のリスト（API エラー時は取得済みの部分結果）

    Examples
    --------
    >>> import asyncio
    >>> from datetime import datetime
    >>> from news_scraper.session import create_async_session
    >>> async def main():
    ...     session = create_async_session()
    ...     articles = await async_fetch_stock_news_api_paginated(
    ...         session, "AAPL", max_articles=100
    ...     )
    ...     print(len(articles))
    >>> asyncio.run(main())
    """
    _validate_ticker(ticker)

    if config is None:
        config = ScraperConfig()

    from .types import get_delay

    ticker_upper = ticker.upper()
    articles: list[Article] = []
    offset = 0

    logger.debug(
        "Fetching NASDAQ stock news paginated (async)",
        ticker=ticker_upper,
        max_articles=max_articles,
        page_size=page_size,
    )

    while offset < max_articles:
        url = _build_pagination_url(ticker_upper, offset, page_size)

        try:
            resp = await session.get(
                url, headers=_NASDAQ_API_HEADERS, timeout=config.timeout
            )
            resp.raise_for_status()
            data = resp.json()
        except Exception as e:
            logger.error(
                "NASDAQ paginated API failed (async)",
                ticker=ticker_upper,
                offset=offset,
                error=str(e),
            )
            break

        page_articles, total_records, all_older_than_start, rows_empty = (
            _process_pagination_page(data, ticker_upper, start_date, end_date)
        )

        # 空 rows で早期終了
        if rows_empty:
            logger.debug(
                "Empty rows, stopping pagination (async)",
                ticker=ticker_upper,
                offset=offset,
            )
            break

        articles.extend(page_articles)
        offset += page_size

        # 全記事が start_date より古い場合は早期終了
        if all_older_than_start:
            logger.debug(
                "All articles older than start_date, stopping (async)",
                ticker=ticker_upper,
                offset=offset,
            )
            break

        # totalrecords で終了判定
        if total_records > 0 and offset >= total_records:
            logger.debug(
                "Reached totalrecords, stopping pagination (async)",
                ticker=ticker_upper,
                offset=offset,
                total_records=total_records,
            )
            break

        # ページ間レートリミット
        delay = get_delay(config)
        await asyncio.sleep(delay)

    logger.info(
        "NASDAQ stock news paginated fetch completed (async)",
        ticker=ticker_upper,
        article_count=len(articles),
    )
    return articles


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


def fetch_news_archive_playwright(
    category: str,
    max_articles: int = 100,
    browser=None,
) -> list[dict]:
    """Playwright を使って NASDAQ ニュースアーカイブページから記事一覧を取得する.

    JS レンダリング後に記事リンクを抽出し、"Load More" ボタンを繰り返しクリックして
    過去記事を取得する。CNBC の ``fetch_sitemap_articles_playwright`` と同じパターンを踏襲。

    Parameters
    ----------
    category : str
        NASDAQ_CATEGORIES に含まれるカテゴリ名（例: "Markets", "Technology"）
    max_articles : int
        最大取得件数
    browser : Browser | None
        既存の Playwright ブラウザインスタンス。None の場合は新規作成して終了時に閉じる。

    Returns
    -------
    list[dict]
        記事情報のリスト。各 dict は以下のキーを持つ:
        - ``title``: 記事タイトル
        - ``url``: 記事 URL
        - ``date``: 取得日付（YYYY-MM-DD 形式）
        - ``category``: カテゴリ名
        - ``source``: "nasdaq"

    Examples
    --------
    >>> articles = fetch_news_archive_playwright("Markets", max_articles=50)
    >>> print(len(articles))
    """
    url_segment = _category_to_url_segment(category)
    url = f"https://www.nasdaq.com/news-and-insights/topic/{url_segment}"

    logger.debug("Fetching NASDAQ archive (playwright)", category=category, url=url)

    close_browser = False
    playwright_ctx = None

    if browser is None:
        if sync_playwright is None:  # pragma: no cover
            raise ImportError(
                "playwright is not installed. Run: uv add playwright && playwright install"
            )
        playwright_ctx = sync_playwright().start()
        browser = playwright_ctx.chromium.launch(headless=True)
        close_browser = True

    try:
        page = browser.new_page()
        page.goto(url, timeout=30000)
        page.wait_for_load_state("networkidle", timeout=15000)

        # "Load More" ボタンを繰り返しクリックして記事を追加読み込み
        while True:
            load_more = page.query_selector("button:has-text('Load More')")
            if load_more is None:
                break

            # 現在の記事数が max_articles に達したら追加クリックを停止
            links = page.query_selector_all("a")
            current_count = sum(
                1
                for link in links
                if "/articles/" in (link.get_attribute("href") or "")
                and "nasdaq.com" in (link.get_attribute("href") or "")
            )
            if current_count >= max_articles:
                break

            load_more.click()
            page.wait_for_load_state("networkidle", timeout=15000)

        links = page.query_selector_all("a")

        articles = []
        seen: set[str] = set()
        today = datetime.now().strftime("%Y-%m-%d")

        for link in links:
            if len(articles) >= max_articles:
                break

            href = link.get_attribute("href") or ""
            text = link.inner_text().strip()

            # NASDAQ ドメインの記事リンクのみ対象
            if (
                "nasdaq.com" not in href
                or "/articles/" not in href
                or not text
                or href in seen
            ):
                continue

            seen.add(href)
            articles.append(
                {
                    "title": text,
                    "url": href,
                    "date": today,
                    "category": category,
                    "source": "nasdaq",
                }
            )

        page.close()
        logger.info(
            "NASDAQ archive fetched (playwright)",
            category=category,
            article_count=len(articles),
        )
        return articles

    except Exception as e:
        logger.error(
            "NASDAQ archive fetch failed (playwright)", category=category, error=str(e)
        )
        return []

    finally:
        if close_browser:
            browser.close()
            if playwright_ctx:
                playwright_ctx.stop()


async def async_fetch_news_archive_playwright(
    category: str,
    max_articles: int = 100,
    browser=None,
) -> list[dict]:
    """Playwright を使って NASDAQ ニュースアーカイブページから記事一覧を非同期で取得する.

    ``fetch_news_archive_playwright`` の非同期版。Playwright の非同期 API
    (``playwright.async_api``) を使用し、``await page.goto()`` や
    ``await page.wait_for_load_state()`` で非同期にブラウザ操作を行う。

    Parameters
    ----------
    category : str
        NASDAQ_CATEGORIES に含まれるカテゴリ名（例: "Markets", "Technology"）
    max_articles : int
        最大取得件数
    browser : Browser | None
        既存の Playwright ブラウザインスタンス。None の場合は新規作成して終了時に閉じる。

    Returns
    -------
    list[dict]
        記事情報のリスト。各 dict は以下のキーを持つ:
        - ``title``: 記事タイトル
        - ``url``: 記事 URL
        - ``date``: 取得日付（YYYY-MM-DD 形式）
        - ``category``: カテゴリ名
        - ``source``: "nasdaq"

    Examples
    --------
    >>> import asyncio
    >>> async def main():
    ...     articles = await async_fetch_news_archive_playwright("Markets", max_articles=50)
    ...     print(len(articles))
    >>> asyncio.run(main())
    """
    url_segment = _category_to_url_segment(category)
    url = f"https://www.nasdaq.com/news-and-insights/topic/{url_segment}"

    logger.debug(
        "Fetching NASDAQ archive (playwright, async)", category=category, url=url
    )

    close_browser = False
    playwright_ctx = None

    if browser is None:
        if async_playwright is None:  # pragma: no cover
            raise ImportError(
                "playwright is not installed. Run: uv add playwright && playwright install"
            )
        playwright_ctx = await async_playwright().start()
        browser = await playwright_ctx.chromium.launch(headless=True)
        close_browser = True

    try:
        page = await browser.new_page()
        await page.goto(url, timeout=30000)
        await page.wait_for_load_state("networkidle", timeout=15000)

        # "Load More" ボタンを繰り返しクリックして記事を追加読み込み
        while True:
            load_more = await page.query_selector("button:has-text('Load More')")
            if load_more is None:
                break

            # 現在の記事数が max_articles に達したら追加クリックを停止
            links = await page.query_selector_all("a")
            current_count = 0
            for link in links:
                href = await link.get_attribute("href") or ""
                if "/articles/" in href and "nasdaq.com" in href:
                    current_count += 1
            if current_count >= max_articles:
                break

            await load_more.click()
            await page.wait_for_load_state("networkidle", timeout=15000)

        links = await page.query_selector_all("a")

        articles = []
        seen: set[str] = set()
        today = datetime.now().strftime("%Y-%m-%d")

        for link in links:
            if len(articles) >= max_articles:
                break

            href = await link.get_attribute("href") or ""
            text = (await link.inner_text()).strip()

            # NASDAQ ドメインの記事リンクのみ対象
            if (
                "nasdaq.com" not in href
                or "/articles/" not in href
                or not text
                or href in seen
            ):
                continue

            seen.add(href)
            articles.append(
                {
                    "title": text,
                    "url": href,
                    "date": today,
                    "category": category,
                    "source": "nasdaq",
                }
            )

        await page.close()
        logger.info(
            "NASDAQ archive fetched (playwright, async)",
            category=category,
            article_count=len(articles),
        )
        return articles

    except Exception as e:
        logger.error(
            "NASDAQ archive fetch failed (playwright, async)",
            category=category,
            error=str(e),
        )
        return []

    finally:
        if close_browser:
            await browser.close()
            if playwright_ctx:
                await playwright_ctx.stop()


def collect_historical_news(
    start_date: datetime,
    end_date: datetime,
    tickers: list[str] | None = None,
    categories: list[str] | None = None,
    config: ScraperConfig | None = None,
    output_dir: str | Path | None = None,
) -> pd.DataFrame:
    """指定期間の NASDAQ 過去ニュースを収集する統合オーケストレーター.

    CNBC の ``collect_historical_news`` と同じインターフェースで NASDAQ の過去記事を収集する。
    ``tickers`` 指定時は API ページネーション（戦略A）、``categories`` + ``use_playwright=True``
    では Playwright アーカイブ（戦略B）を使用する。

    Parameters
    ----------
    start_date : datetime
        開始日時
    end_date : datetime
        終了日時
    tickers : list[str] | None
        銘柄コードリスト。指定時は API ページネーション（戦略A）を使用。
    categories : list[str] | None
        カテゴリリスト（``NASDAQ_CATEGORIES`` のいずれか）。
        ``config.use_playwright=True`` のとき Playwright アーカイブ（戦略B）を使用。
        None のときデフォルトカテゴリ（``NASDAQ_QUANT_CATEGORIES``）を使用。
    config : ScraperConfig | None
        スクレイパー設定（None でデフォルト）
    output_dir : str | Path | None
        出力ディレクトリ（None で保存しない）。日別 JSON + 全体 Parquet を保存。

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
    ...     tickers=["AAPL", "MSFT"],
    ... )
    """
    if config is None:
        config = ScraperConfig()

    from .types import get_delay

    output_path: Path | None = None
    if output_dir:
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)

    all_articles: list[dict] = []

    # AIDEV-NOTE: 収集戦略の選択。Strategy A (API) / Strategy B (Playwright)
    # 新たな収集方法を追加する場合は、_collect_with_*(strategy) のような
    # プライベート関数に抽出してここで選択するパターンを検討してください。

    # Strategy A: ティッカー別 API ページネーション
    if tickers:
        session = create_session(impersonate=config.impersonate, proxy=config.proxy)

        for ticker in tickers:
            logger.info(
                "Collecting historical news via API",
                ticker=ticker,
                start_date=str(start_date.date()),
                end_date=str(end_date.date()),
            )
            try:
                articles = fetch_stock_news_api_paginated(
                    session,
                    ticker,
                    start_date=start_date,
                    end_date=end_date,
                    config=config,
                )
                all_articles.extend([a.to_dict() for a in articles])
            except Exception as e:
                logger.error(
                    "Ticker fetch failed",
                    ticker=ticker,
                    error=str(e),
                )

            time.sleep(get_delay(config))

    # Strategy B: Playwright によるアーカイブページスクレイピング
    if config.use_playwright:
        cats = categories if categories is not None else list(NASDAQ_QUANT_CATEGORIES)

        close_playwright = False
        playwright_ctx = None
        browser = None

        if sync_playwright is None:  # pragma: no cover
            logger.warning("playwright not installed, skipping archive collection")
        else:
            playwright_ctx = sync_playwright().start()
            browser = playwright_ctx.chromium.launch(headless=True)
            close_playwright = True

        try:
            for category in cats:
                logger.info(
                    "Collecting historical news via Playwright archive",
                    category=category,
                )
                try:
                    archive_articles = fetch_news_archive_playwright(
                        category,
                        browser=browser,
                    )
                    all_articles.extend(archive_articles)
                except Exception as e:
                    logger.error(
                        "Archive fetch failed",
                        category=category,
                        error=str(e),
                    )

                time.sleep(get_delay(config))
        finally:
            if close_playwright:
                if browser is not None:
                    browser.close()
                if playwright_ctx is not None:
                    playwright_ctx.stop()

    # include_content=True のとき本文取得
    if config.include_content and all_articles:
        session = create_session(impersonate=config.impersonate, proxy=config.proxy)

        for article in all_articles:
            url = article.get("url", "")
            if not url:
                continue
            content_data = fetch_article_content(session, url, config.timeout)
            if content_data:
                article["content"] = content_data.get("content", "")
            time.sleep(get_delay(config))

    df = pd.DataFrame(all_articles)

    # 日別 JSON + 全体 Parquet 保存
    if output_path and not df.empty:
        _save_articles_by_date(df, output_path)

    return df


async def async_collect_historical_news(
    start_date: datetime,
    end_date: datetime,
    tickers: list[str] | None = None,
    categories: list[str] | None = None,
    config: ScraperConfig | None = None,
    output_dir: str | Path | None = None,
) -> pd.DataFrame:
    """指定期間の NASDAQ 過去ニュースを並列で非同期収集する統合オーケストレーター.

    ``collect_historical_news`` の非同期版。ティッカー間の並列化を ``RateLimiter`` +
    ``gather_with_errors`` で実現し、本文取得の並列化も ``max_concurrency_content``
    で制御する。

    Parameters
    ----------
    start_date : datetime
        開始日時
    end_date : datetime
        終了日時
    tickers : list[str] | None
        銘柄コードリスト。指定時は API ページネーション（戦略A）を使用。
        ティッカー間の並列化は ``RateLimiter`` + ``gather_with_errors`` で実行。
    categories : list[str] | None
        カテゴリリスト（``NASDAQ_CATEGORIES`` のいずれか）。
        ``config.use_playwright=True`` のとき Playwright アーカイブ（戦略B）を使用。
        None のときデフォルトカテゴリ（``NASDAQ_QUANT_CATEGORIES``）を使用。
    config : ScraperConfig | None
        スクレイパー設定（None でデフォルト）
    output_dir : str | Path | None
        出力ディレクトリ（None で保存しない）。日別 JSON + 全体 Parquet を保存。

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

    all_articles: list[dict] = []

    # 戦略A: tickers 指定時は API ページネーション（RateLimiter + gather_with_errors で並列化）
    if tickers:
        ticker_session = create_async_session(
            impersonate=config.impersonate, proxy=config.proxy
        )
        ticker_limiter = RateLimiter(
            delay=config.delay, max_concurrency=config.max_concurrency
        )

        async def _fetch_ticker(ticker: str) -> list[Article]:
            async with ticker_limiter:
                logger.info(
                    "Collecting historical news via API (async)",
                    ticker=ticker,
                    start_date=str(start_date.date()),
                    end_date=str(end_date.date()),
                )
                return await async_fetch_stock_news_api_paginated(
                    ticker_session,
                    ticker,
                    start_date=start_date,
                    end_date=end_date,
                    config=config,
                )

        ticker_tasks = [asyncio.create_task(_fetch_ticker(t)) for t in tickers]
        ticker_results = await gather_with_errors(ticker_tasks, logger)

        for article_list in ticker_results:
            all_articles.extend([a.to_dict() for a in article_list])

    # 戦略B: categories + use_playwright=True のとき Playwright アーカイブ
    if config.use_playwright:
        cats = categories if categories is not None else list(NASDAQ_QUANT_CATEGORIES)

        close_playwright = False
        playwright_ctx = None
        browser = None

        if async_playwright is None:  # pragma: no cover
            logger.warning("playwright not installed, skipping archive collection")
        else:
            playwright_ctx = await async_playwright().start()
            browser = await playwright_ctx.chromium.launch(headless=True)
            close_playwright = True

        try:
            for category in cats:
                logger.info(
                    "Collecting historical news via Playwright archive (async)",
                    category=category,
                )
                try:
                    archive_articles = await async_fetch_news_archive_playwright(
                        category,
                        browser=browser,
                    )
                    all_articles.extend(archive_articles)
                except Exception as e:
                    logger.error(
                        "Archive fetch failed (async)",
                        category=category,
                        error=str(e),
                    )

                await asyncio.sleep(config.delay)
        finally:
            if close_playwright:
                if browser is not None:
                    await browser.close()
                if playwright_ctx is not None:
                    await playwright_ctx.stop()

    # include_content=True のとき本文取得（max_concurrency_content で並列化）
    if config.include_content and all_articles:
        content_session = create_async_session(
            impersonate=config.impersonate, proxy=config.proxy
        )
        content_limiter = RateLimiter(
            delay=config.delay, max_concurrency=config.max_concurrency_content
        )

        async def _fetch_content(article: dict) -> tuple[str, str]:
            url = article.get("url", "")
            async with content_limiter:
                content_data = await async_fetch_article_content(
                    content_session, url, config.timeout
                )
                content = content_data.get("content", "") if content_data else ""
                return url, content

        content_tasks = [
            asyncio.create_task(_fetch_content(a)) for a in all_articles if a.get("url")
        ]
        content_results = await gather_with_errors(content_tasks, logger)

        content_map: dict[str, str] = {}
        for url, content in content_results:
            content_map[url] = content

        for article in all_articles:
            url = article.get("url", "")
            if url in content_map:
                article["content"] = content_map[url]

    df = pd.DataFrame(all_articles)

    # 日別 JSON + 全体 Parquet 保存
    if output_path and not df.empty:
        _save_articles_by_date(df, output_path)

    return df


def _save_articles_by_date(df: pd.DataFrame, output_path: Path) -> None:
    """記事を日別 JSON と全体 Parquet に保存する内部ヘルパー.

    ``published`` カラムが存在する場合は日付でグループ化して日別 JSON を保存する。
    全体は ``all_articles.parquet`` として保存する。

    Parameters
    ----------
    df : pd.DataFrame
        保存する記事データフレーム
    output_path : Path
        出力ディレクトリ
    """
    # metadata カラムが空辞書の場合は Parquet 書き込みでエラーになるため文字列化する
    df_to_save = df.copy()
    if "metadata" in df_to_save.columns:
        df_to_save["metadata"] = df_to_save["metadata"].apply(
            lambda v: str(v) if isinstance(v, dict) else v
        )

    # 全体 Parquet 保存
    df_to_save.to_parquet(output_path / "all_articles.parquet", index=False)

    # 日別 JSON 保存（published カラムがある場合）
    if "published" not in df.columns:
        return

    # 日付別に記事をインメモリ集約し、ファイル I/O をユニーク日付数に削減
    date_groups: defaultdict[str, list[dict]] = defaultdict(list)
    for article in df.to_dict(orient="records"):
        pub_str = article.get("published", "")
        date_str = ""
        if pub_str:
            try:
                dt = _parse_article_date(str(pub_str))
                if dt:
                    date_str = dt.strftime("%Y-%m-%d")
            except Exception as e:
                logger.debug(
                    "Date parse failed for grouping", pub_str=pub_str, error=str(e)
                )
        if not date_str:
            date_str = "unknown"
        date_groups[date_str].append(article)

    # 日付ごとに 1 回の read-modify-write（N 件 → D 件のファイル操作）
    for date_str, new_articles in date_groups.items():
        date_file = output_path / f"{date_str}.json"
        existing: list[dict] = []
        if date_file.exists():
            with open(date_file, encoding="utf-8") as f:
                existing = json.load(f)
        existing.extend(new_articles)
        with open(date_file, "w", encoding="utf-8") as f:
            json.dump(existing, f, ensure_ascii=False, indent=2)


# 後方互換性のためのエイリアス
QUANT_CATEGORIES = NASDAQ_QUANT_CATEGORIES
