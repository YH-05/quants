"""yfinance ニューススクレイパー.

yf.Ticker / yf.Search を使用してニュース記事を取得する。
CNBC/NASDAQ スクレイパーと統一された Article データモデルを使用し、
リトライ・エラー分類機能を備える。
"""

import re
import time
from datetime import UTC, datetime
from pathlib import Path
from typing import Literal
from urllib.parse import urlparse

import pandas as pd
import trafilatura
import yfinance as yf
from curl_cffi.requests import Session
from curl_cffi.requests.errors import RequestsError

from utils_core.logging import get_logger

from .exceptions import ContentExtractionError, PermanentError, RetryableError
from .retry import classify_http_error, create_retry_decorator
from .session import create_session
from .types import YFINANCE_JP_TICKERS, Article, ScraperConfig, get_delay

logger = get_logger(__name__)

retry = create_retry_decorator(max_attempts=3)


@retry
def fetch_ticker_news(
    session: Session,
    ticker: str,
    timeout: int = 30,
) -> list[Article]:
    """単一ティッカーのニュース記事を取得する.

    yf.Ticker API を使用してニュースを取得し、統一された
    Article データモデルに変換して返す。記事は公開日時
    (published) の降順でソートされる。

    Parameters
    ----------
    session : Session
        HTTP セッション（curl_cffi）
    ticker : str
        ティッカーシンボル（例: "AAPL", "7203.T"）
    timeout : int
        タイムアウト秒数（デフォルト: 30）

    Returns
    -------
    list[Article]
        Article のリスト（published 降順）

    Raises
    ------
    RetryableError
        接続エラーやサーバーエラー（429, 5xx）の場合
    PermanentError
        恒久的なエラー（403, 404）の場合

    Examples
    --------
    >>> from news_scraper.session import create_session
    >>> session = create_session()
    >>> articles = fetch_ticker_news(session, "AAPL")
    >>> for a in articles:
    ...     print(a.title, a.published)
    """
    logger.debug("Fetching ticker news", ticker=ticker, timeout=timeout)

    try:
        ticker_news = yf.Ticker(ticker, session=session).news
    except RequestsError as e:
        if hasattr(e, "response") and e.response is not None:
            raise classify_http_error(e.response.status_code, e.response) from e
        raise RetryableError(f"Connection error for {ticker}: {e}") from e

    articles = []
    for item in ticker_news:
        content = item.get("content")
        if content is None:
            logger.debug("Skipping item without content field")
            continue

        canonical_url = content.get("canonicalUrl", {})
        url = canonical_url.get("url", "") if isinstance(canonical_url, dict) else ""

        metadata: dict = {}
        if "contentType" in content:
            metadata["contentType"] = content["contentType"]
        if "finance" in content:
            metadata["finance"] = content["finance"]

        articles.append(
            Article(
                title=content.get("title", ""),
                url=url,
                published=content.get("pubDate", ""),
                summary=content.get("summary", ""),
                source="yfinance_ticker",
                ticker=ticker,
                article_id=content.get("id", ""),
                metadata=metadata,
            )
        )

    # published で降順ソート
    articles.sort(key=lambda a: a.published, reverse=True)

    logger.info("Ticker news fetched", ticker=ticker, article_count=len(articles))
    return articles


def _unix_to_iso8601(timestamp: int | None) -> str:
    """Unix タイムスタンプを ISO 8601 形式の文字列に変換する.

    Parameters
    ----------
    timestamp : int | None
        Unix タイムスタンプ（秒）

    Returns
    -------
    str
        ISO 8601 形式の日時文字列、または timestamp が None の場合は空文字
    """
    if timestamp is None:
        return ""
    return datetime.fromtimestamp(timestamp, tz=UTC).isoformat()


@retry
def fetch_search_news(
    session: Session,
    query: str,
    news_count: int = 50,
    timeout: int = 30,
) -> list[Article]:
    """単一クエリのニュース記事を取得する.

    yf.Search API を使用してニュースを検索し、統一された
    Article データモデルに変換して返す。記事は公開日時
    (published) の降順でソートされる。

    Parameters
    ----------
    session : Session
        HTTP セッション（curl_cffi）
    query : str
        検索クエリ（例: "AAPL", "AI stocks"）
    news_count : int
        取得するニュース数（デフォルト: 50）
    timeout : int
        タイムアウト秒数（デフォルト: 30）

    Returns
    -------
    list[Article]
        Article のリスト（published 降順）

    Raises
    ------
    RetryableError
        接続エラーやサーバーエラー（429, 5xx）の場合
    PermanentError
        恒久的なエラー（403, 404）の場合

    Examples
    --------
    >>> from news_scraper.session import create_session
    >>> session = create_session()
    >>> articles = fetch_search_news(session, "AAPL")
    >>> for a in articles:
    ...     print(a.title, a.published)
    """
    logger.debug(
        "Fetching search news",
        query=query,
        news_count=news_count,
        timeout=timeout,
    )

    try:
        search_news = yf.Search(query, news_count=news_count, session=session).news
    except RequestsError as e:
        if hasattr(e, "response") and e.response is not None:
            raise classify_http_error(e.response.status_code, e.response) from e
        raise RetryableError(f"Connection error for query '{query}': {e}") from e

    articles = []
    for item in search_news:
        related_tickers = item.get("relatedTickers", [])
        ticker_str = ",".join(related_tickers) if related_tickers else ""

        provider_publish_time = item.get("providerPublishTime")
        published = _unix_to_iso8601(provider_publish_time)

        metadata: dict = {}
        if "type" in item:
            metadata["type"] = item["type"]
        metadata["query"] = query

        articles.append(
            Article(
                title=item.get("title", ""),
                url=item.get("link", ""),
                published=published,
                summary="",
                category=query,
                source="yfinance_search",
                ticker=ticker_str,
                author=item.get("publisher", ""),
                article_id=item.get("uuid", ""),
                metadata=metadata,
            )
        )

    # published で降順ソート
    articles.sort(key=lambda a: a.published, reverse=True)

    logger.info("Search news fetched", query=query, article_count=len(articles))
    return articles


def fetch_article_content(
    session: Session,
    url: str,
    timeout: int = 30,
) -> dict | None:
    """記事ページから本文を取得する.

    curl_cffi セッションで URL を取得し、trafilatura で本文を抽出する。
    cnbc/nasdaq の同名関数と同じインターフェース（``dict | None``）を返す。

    Parameters
    ----------
    session : Session
        HTTP セッション（curl_cffi）
    url : str
        記事 URL
    timeout : int
        タイムアウト秒数（デフォルト: 30）

    Returns
    -------
    dict | None
        記事情報（取得失敗時は None）。成功時のキー:
        - ``url``: 記事 URL
        - ``title``: 記事タイトル（trafilatura 抽出）
        - ``content``: 本文テキスト

    Examples
    --------
    >>> from news_scraper.session import create_session
    >>> session = create_session()
    >>> result = fetch_article_content(
    ...     session, "https://finance.yahoo.com/news/example"
    ... )
    >>> if result:
    ...     print(result["content"][:100])
    """
    logger.debug("Fetching article content", url=url, timeout=timeout)

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
        logger.warning(
            "Content extraction failed",
            url=url,
            exc_info=ContentExtractionError(f"本文抽出失敗: {url}"),
        )
        return None

    # trafilatura からメタデータも抽出
    metadata = trafilatura.extract(
        html,
        include_comments=False,
        include_tables=False,
        no_fallback=False,
        output_format="xmltei",
    )

    title = ""
    if metadata:
        # TEI XML から title を取得
        title_match = re.search(r"<title[^>]*>(.*?)</title>", metadata)
        if title_match:
            title = title_match.group(1).strip()

    return {
        "url": url,
        "title": title,
        "content": text,
    }


def fetch_multiple_searches(
    session: Session,
    queries: list[str],
    news_count: int = 50,
    config: ScraperConfig | None = None,
    delay: float = 1.0,
    timeout: int = 30,
) -> pd.DataFrame:
    """複数クエリのニュースを逐次取得する.

    各クエリに対して ``fetch_search_news()`` を逐次呼び出し、
    ``get_delay(config)`` によるジッター付き遅延を挟みながら取得する。
    個別クエリの失敗（PermanentError, RetryableError）はスキップし、
    バッチ全体の統計をログ出力する。

    Parameters
    ----------
    session : Session
        HTTP セッション（curl_cffi）
    queries : list[str]
        検索クエリのリスト（例: ["AI stocks", "EV market", "crypto"]）
    news_count : int
        各クエリで取得するニュース数（デフォルト: 50）
    config : ScraperConfig | None
        スクレイパー設定（None の場合はデフォルト設定を使用）
    delay : float
        リクエスト間の基本遅延秒数（デフォルト: 1.0）。
        config が指定された場合は config.delay が優先される。
    timeout : int
        タイムアウト秒数（デフォルト: 30）

    Returns
    -------
    pd.DataFrame
        全クエリの記事を結合した DataFrame。
        カラムは Article.to_dict() のキーに対応する。
        記事が無い場合は空の DataFrame を返す。

    Examples
    --------
    >>> from news_scraper.session import create_session
    >>> from news_scraper.types import ScraperConfig
    >>> session = create_session()
    >>> config = ScraperConfig(delay=1.0, jitter=0.5)
    >>> df = fetch_multiple_searches(
    ...     session, ["AI stocks", "EV market"], config=config
    ... )
    >>> print(df[["category", "title"]].head())
    """
    if config is None:
        config = ScraperConfig(delay=delay)

    all_articles: list[dict] = []
    success_count = 0
    failed_count = 0

    for query in queries:
        try:
            articles = fetch_search_news(
                session, query, news_count=news_count, timeout=timeout
            )
            all_articles.extend([a.to_dict() for a in articles])
            success_count += 1
        except PermanentError as e:
            logger.warning("Query skipped (permanent)", query=query, error=str(e))
            failed_count += 1
        except RetryableError as e:
            logger.warning("Query skipped (retryable)", query=query, error=str(e))
            failed_count += 1

        delay_sec = get_delay(config)
        time.sleep(delay_sec)

    logger.info(
        "Batch complete",
        total_queries=len(queries),
        success_count=success_count,
        failed_count=failed_count,
        article_count=len(all_articles),
    )

    return pd.DataFrame(all_articles)


def fetch_multiple_tickers(
    session: Session,
    tickers: list[str],
    config: ScraperConfig | None = None,
    timeout: int = 30,
) -> pd.DataFrame:
    """複数ティッカーのニュースを逐次取得する.

    各ティッカーに対して ``fetch_ticker_news()`` を逐次呼び出し、
    ``get_delay(config)`` によるジッター付き遅延を挟みながら取得する。
    個別ティッカーの失敗（PermanentError, RetryableError）はスキップし、
    バッチ全体の統計をログ出力する。

    Parameters
    ----------
    session : Session
        HTTP セッション（curl_cffi）
    tickers : list[str]
        ティッカーシンボルのリスト（例: ["AAPL", "MSFT", "7203.T"]）
    config : ScraperConfig | None
        スクレイパー設定（None の場合はデフォルト設定を使用）
    timeout : int
        タイムアウト秒数（デフォルト: 30）

    Returns
    -------
    pd.DataFrame
        全ティッカーの記事を結合した DataFrame。
        カラムは Article.to_dict() のキーに対応する。
        記事が無い場合は空の DataFrame を返す。

    Examples
    --------
    >>> from news_scraper.session import create_session
    >>> from news_scraper.types import ScraperConfig
    >>> session = create_session()
    >>> config = ScraperConfig(delay=1.0, jitter=0.5)
    >>> df = fetch_multiple_tickers(
    ...     session, ["AAPL", "MSFT", "GOOG"], config=config
    ... )
    >>> print(df[["ticker", "title"]].head())
    """
    if config is None:
        config = ScraperConfig()

    all_articles: list[dict] = []
    success_count = 0
    failed_count = 0

    for ticker in tickers:
        try:
            articles = fetch_ticker_news(session, ticker, timeout=timeout)
            all_articles.extend([a.to_dict() for a in articles])
            success_count += 1
        except PermanentError as e:
            logger.warning("Ticker skipped (permanent)", ticker=ticker, error=str(e))
            failed_count += 1
        except RetryableError as e:
            logger.warning("Ticker skipped (retryable)", ticker=ticker, error=str(e))
            failed_count += 1

        delay = get_delay(config)
        time.sleep(delay)

    logger.info(
        "Batch complete",
        total_tickers=len(tickers),
        success_count=success_count,
        failed_count=failed_count,
        article_count=len(all_articles),
    )

    return pd.DataFrame(all_articles)


def collect_yfinance_news(
    tickers: list[str] | None = None,
    queries: list[str] | None = None,
    news_count: int = 50,
    config: ScraperConfig | None = None,
    output_dir: str | Path | None = None,
) -> pd.DataFrame:
    """yfinance ニュースを一括収集する.

    ティッカー別取得（``fetch_multiple_tickers``）とクエリ別取得
    （``fetch_multiple_searches``）を統合し、重複除去・本文取得・
    ファイル保存をオーケストレーションする。

    Parameters
    ----------
    tickers : list[str] | None
        取得するティッカーシンボルのリスト（例: ["AAPL", "MSFT"]）。
        None の場合はティッカー別取得をスキップする。
    queries : list[str] | None
        検索クエリのリスト（例: ["AI stocks", "EV market"]）。
        None の場合はクエリ別取得をスキップする。
    news_count : int
        各クエリで取得するニュース数（デフォルト: 50）。
        ``fetch_multiple_searches`` に渡される。
    config : ScraperConfig | None
        スクレイパー設定（None の場合はデフォルト設定を使用）
    output_dir : str | Path | None
        出力ディレクトリ（None の場合はファイル保存しない）。
        指定時は JSON + Parquet 形式で保存する。

    Returns
    -------
    pd.DataFrame
        収集した全記事のデータフレーム（``article_id`` による重複除去済み）。
        tickers と queries の両方が None の場合は空の DataFrame を返す。

    Examples
    --------
    >>> df = collect_yfinance_news(
    ...     tickers=["AAPL", "MSFT"],
    ...     queries=["AI stocks"],
    ... )
    >>> print(df[["ticker", "title"]].head())

    >>> # ファイル保存付き
    >>> df = collect_yfinance_news(
    ...     tickers=["AAPL"],
    ...     output_dir="data/raw/yfinance",
    ... )
    """
    if config is None:
        config = ScraperConfig()

    output_path: Path | None = None
    if output_dir:
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)

    session = create_session(impersonate=config.impersonate, proxy=config.proxy)
    all_articles: list[dict] = []

    # ティッカー別収集
    if tickers:
        df_tickers = fetch_multiple_tickers(
            session, tickers, config=config, timeout=config.timeout
        )
        if not df_tickers.empty:
            all_articles.extend(df_tickers.to_dict("records"))

    # クエリ別収集
    if queries:
        df_searches = fetch_multiple_searches(
            session,
            queries,
            news_count=news_count,
            config=config,
            timeout=config.timeout,
        )
        if not df_searches.empty:
            all_articles.extend(df_searches.to_dict("records"))

    df = pd.DataFrame(all_articles)

    if df.empty:
        return df

    # article_id をキーに重複除去
    df = df.drop_duplicates(subset=["article_id"])

    # 本文取得（include_content=True の場合）
    if config.include_content:
        contents: list[str] = []
        for _i, row in df.iterrows():
            content_data = fetch_article_content(
                session, str(row["url"]), config.timeout
            )
            contents.append(content_data.get("content", "") if content_data else "")
            time.sleep(config.delay)
        df["content"] = contents

    # ファイル保存（output_dir 指定時）
    if output_path and not df.empty:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        df.to_json(
            output_path / f"yfinance_{timestamp}.json",
            orient="records",
            force_ascii=False,
            indent=2,
        )
        df.to_parquet(output_path / f"yfinance_{timestamp}.parquet", index=False)

    return df


def fetch_jp_stock_news(
    session: Session,
    tickers: list[str] | None = None,
    timeout: int = 30,
) -> list[Article]:
    """日本株プリセットティッカーのニュース記事を取得する.

    ``fetch_multiple_tickers()`` の薄いラッパーで、デフォルトで主要
    日本株 25 銘柄のニュースを取得できる便利関数。

    Parameters
    ----------
    session : Session
        HTTP セッション（curl_cffi）
    tickers : list[str] | None
        取得するティッカーシンボルのリスト。None の場合は
        ``YFINANCE_JP_TICKERS``（主要日本株 25 銘柄）をデフォルトで使用する。
    timeout : int
        タイムアウト秒数（デフォルト: 30）

    Returns
    -------
    list[Article]
        Article のリスト

    Examples
    --------
    >>> from news_scraper.session import create_session
    >>> session = create_session()
    >>> articles = fetch_jp_stock_news(session)
    >>> for a in articles:
    ...     print(a.ticker, a.title)

    >>> # カスタムティッカー指定
    >>> articles = fetch_jp_stock_news(session, tickers=["7203.T", "6758.T"])
    """
    if tickers is None:
        tickers = YFINANCE_JP_TICKERS

    logger.info(
        "Fetching JP stock news",
        ticker_count=len(tickers),
        timeout=timeout,
    )

    df = fetch_multiple_tickers(session, tickers, timeout=timeout)

    if df.empty:
        return []

    articles: list[Article] = []
    for record in df.to_dict("records"):
        articles.append(
            Article(
                title=str(record.get("title", "")),
                url=str(record.get("url", "")),
                published=str(record.get("published", "")),
                summary=str(record.get("summary", "")),
                category=str(record.get("category", "")),
                source=str(record.get("source", "yfinance_ticker")),
                content=str(record.get("content", "")),
                ticker=str(record.get("ticker", "")),
                author=str(record.get("author", "")),
                article_id=str(record.get("article_id", "")),
                metadata=record.get("metadata") or {},
            )
        )

    logger.info("JP stock news fetched", article_count=len(articles))
    return articles
