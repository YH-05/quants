"""TDnet 非公式 RSS スクレイパー.

yanoshin API 経由で TDnet（適時開示情報伝達システム）の RSS を取得する。
銘柄コード指定による適時開示情報の取得に対応し、Article.ticker に証券コードを設定する。

非公式 API のため、リトライ + graceful degradation（空リスト返却 + warning ログ）で対応。
"""

import asyncio
import re
import time

import feedparser
import pandas as pd
from curl_cffi import requests
from curl_cffi.requests import AsyncSession

from utils_core.logging import get_logger

from .async_core import RateLimiter, gather_with_errors
from .types import TDNET_BASE_URL, TDNET_DEFAULT_CODES, Article, ScraperConfig

logger = get_logger(__name__)

# 証券コードの正規表現パターン（4桁数字）
_CODE_PATTERN = re.compile(r"^\d{4,5}$")


def _validate_codes(codes: list[str]) -> list[str]:
    """証券コードのバリデーションを行い、有効なコードのみ返す.

    Parameters
    ----------
    codes : list[str]
        検証する証券コードのリスト

    Returns
    -------
    list[str]
        有効な証券コードのリスト

    Raises
    ------
    ValueError
        codes が空の場合
    """
    if not codes:
        msg = "codes must not be empty"
        raise ValueError(msg)

    valid_codes = []
    for code in codes:
        code = code.strip()
        if _CODE_PATTERN.match(code):
            valid_codes.append(code)
        else:
            logger.warning("Invalid stock code skipped", code=code)

    if not valid_codes:
        msg = f"No valid stock codes found in: {codes}"
        raise ValueError(msg)

    return valid_codes


def _build_tdnet_url(codes: list[str]) -> str:
    """証券コードリストから TDnet RSS URL を構築する.

    Parameters
    ----------
    codes : list[str]
        証券コードのリスト（バリデーション済み）

    Returns
    -------
    str
        TDnet RSS の URL
    """
    codes_str = ",".join(codes)
    return f"{TDNET_BASE_URL}/{codes_str}.rss"


def _extract_ticker_from_title(title: str, codes: list[str]) -> str:
    """タイトルから証券コードを抽出する.

    TDnet のタイトルには証券コードが含まれることが多い。
    リクエストしたコードリストと照合して抽出する。

    Parameters
    ----------
    title : str
        記事タイトル
    codes : list[str]
        リクエストした証券コードのリスト

    Returns
    -------
    str
        抽出された証券コード（見つからない場合は空文字列）
    """
    for code in codes:
        if code in title:
            return code
    return ""


def fetch_disclosure_feed(
    session: requests.Session,
    codes: list[str] | None = None,
    timeout: int = 30,
) -> list[Article]:
    """銘柄コード指定で TDnet 適時開示 RSS フィードを取得する.

    非公式 API のため、503/タイムアウト時には空リストを返却し warning ログを出力する
    graceful degradation パターンを適用する。

    Parameters
    ----------
    session : requests.Session
        HTTP セッション
    codes : list[str] | None
        証券コードのリスト（None で TDNET_DEFAULT_CODES を使用）
    timeout : int
        タイムアウト秒数

    Returns
    -------
    list[Article]
        適時開示記事のリスト（エラー時は空リスト）
    """
    if codes is None:
        codes = TDNET_DEFAULT_CODES

    try:
        valid_codes = _validate_codes(codes)
    except ValueError as e:
        logger.warning("TDnet code validation failed", error=str(e))
        return []

    url = _build_tdnet_url(valid_codes)

    logger.debug("Fetching TDnet RSS", codes=valid_codes, url=url)

    try:
        resp = session.get(url, timeout=timeout)
        resp.raise_for_status()
    except Exception as e:
        logger.warning(
            "TDnet RSS fetch failed (graceful degradation)",
            codes=valid_codes,
            error=str(e),
        )
        return []

    try:
        feed = feedparser.parse(resp.text)
    except Exception as e:
        logger.warning(
            "TDnet RSS parse failed (graceful degradation)",
            error=str(e),
        )
        return []

    articles = []
    for entry in feed.entries:
        title = str(entry.get("title", ""))
        ticker = _extract_ticker_from_title(title, valid_codes)

        articles.append(
            Article(
                title=title,
                url=str(entry.get("link", "")),
                published=str(entry.get("published", "")),
                summary=str(entry.get("summary", "")),
                category="disclosure",
                source="tdnet",
                ticker=ticker,
            )
        )

    logger.info(
        "TDnet RSS fetched",
        codes=valid_codes,
        article_count=len(articles),
    )
    return articles


async def async_fetch_disclosure_feed(
    session: AsyncSession,
    codes: list[str] | None = None,
    timeout: int = 30,
) -> list[Article]:
    """銘柄コード指定で TDnet 適時開示 RSS フィードを非同期で取得する.

    ``fetch_disclosure_feed`` の非同期版。HTTP 取得を ``await session.get()``
    で非同期化し、``feedparser.parse()`` による XML 解析は同期のまま実行する。

    非公式 API のため、503/タイムアウト時には空リストを返却し warning ログを出力する
    graceful degradation パターンを適用する。

    Parameters
    ----------
    session : AsyncSession
        非同期 HTTP セッション
    codes : list[str] | None
        証券コードのリスト（None で TDNET_DEFAULT_CODES を使用）
    timeout : int
        タイムアウト秒数

    Returns
    -------
    list[Article]
        適時開示記事のリスト（エラー時は空リスト）
    """
    if codes is None:
        codes = TDNET_DEFAULT_CODES

    try:
        valid_codes = _validate_codes(codes)
    except ValueError as e:
        logger.warning("TDnet code validation failed (async)", error=str(e))
        return []

    url = _build_tdnet_url(valid_codes)

    logger.debug("Fetching TDnet RSS (async)", codes=valid_codes, url=url)

    try:
        resp = await session.get(url, timeout=timeout)
        resp.raise_for_status()
    except Exception as e:
        logger.warning(
            "TDnet RSS fetch failed (async, graceful degradation)",
            codes=valid_codes,
            error=str(e),
        )
        return []

    try:
        feed = feedparser.parse(resp.text)
    except Exception as e:
        logger.warning(
            "TDnet RSS parse failed (async, graceful degradation)",
            error=str(e),
        )
        return []

    articles = []
    for entry in feed.entries:
        title = str(entry.get("title", ""))
        ticker = _extract_ticker_from_title(title, valid_codes)

        articles.append(
            Article(
                title=title,
                url=str(entry.get("link", "")),
                published=str(entry.get("published", "")),
                summary=str(entry.get("summary", "")),
                category="disclosure",
                source="tdnet",
                ticker=ticker,
            )
        )

    logger.info(
        "TDnet RSS fetched (async)",
        codes=valid_codes,
        article_count=len(articles),
    )
    return articles


def fetch_multiple_codes(
    session: requests.Session,
    code_groups: list[list[str]] | None = None,
    delay: float = 0.5,
    timeout: int = 30,
) -> pd.DataFrame:
    """複数のコードグループの適時開示情報を取得する.

    コードグループごとにリクエストを分割して取得する。

    Parameters
    ----------
    session : requests.Session
        HTTP セッション
    code_groups : list[list[str]] | None
        コードグループのリスト（None で TDNET_DEFAULT_CODES を1グループとして使用）
    delay : float
        リクエスト間の待機秒数
    timeout : int
        タイムアウト秒数

    Returns
    -------
    pd.DataFrame
        全記事のデータフレーム
    """
    if code_groups is None:
        code_groups = [TDNET_DEFAULT_CODES]

    all_articles: list[dict] = []

    for codes in code_groups:
        try:
            articles = fetch_disclosure_feed(session, codes, timeout)
            all_articles.extend([a.to_dict() for a in articles])
        except Exception as e:
            logger.error(
                "TDnet code group fetch failed",
                codes=codes,
                error=str(e),
            )

        time.sleep(delay)

    return pd.DataFrame(all_articles)


async def async_fetch_multiple_codes(
    session: AsyncSession,
    code_groups: list[list[str]] | None = None,
    config: ScraperConfig | None = None,
) -> pd.DataFrame:
    """複数のコードグループの適時開示情報を並列で非同期取得する.

    Parameters
    ----------
    session : AsyncSession
        非同期 HTTP セッション
    code_groups : list[list[str]] | None
        コードグループのリスト（None で TDNET_DEFAULT_CODES を1グループとして使用）
    config : ScraperConfig | None
        スクレイパー設定（None でデフォルト）

    Returns
    -------
    pd.DataFrame
        全記事のデータフレーム
    """
    if config is None:
        config = ScraperConfig()

    if code_groups is None:
        code_groups = [TDNET_DEFAULT_CODES]

    if not code_groups:
        return pd.DataFrame()

    limiter = RateLimiter(delay=config.delay, max_concurrency=config.max_concurrency)

    async def _fetch_group(codes: list[str]) -> list[Article]:
        async with limiter:
            return await async_fetch_disclosure_feed(session, codes, config.timeout)

    tasks = [asyncio.create_task(_fetch_group(codes)) for codes in code_groups]
    results = await gather_with_errors(tasks, logger)

    all_articles: list[dict] = []
    for article_list in results:
        all_articles.extend([a.to_dict() for a in article_list])

    return pd.DataFrame(all_articles)
