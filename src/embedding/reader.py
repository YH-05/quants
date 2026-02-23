"""JSON 読み込みモジュール.

ニュース収集 CLI で収集したニュースデータ（``data/raw/news/{source}/*.json``）を
読み込み、``ArticleRecord`` に変換する。URL ベースの重複除去も行う。

Examples
--------
>>> from pathlib import Path
>>> from embedding.reader import read_all_news_json
>>> records = read_all_news_json(Path("data/raw/news"))
>>> len(records)
42
"""

import json
import logging
from pathlib import Path

from .types import ArticleRecord

logger = logging.getLogger(__name__)


def read_all_news_json(
    news_dir: Path,
    sources: list[str] | None = None,
) -> list[ArticleRecord]:
    """指定ディレクトリ以下の全 JSON を読み込み、URL 重複除去済みリストを返す.

    Parameters
    ----------
    news_dir : Path
        ニュース JSON の格納ディレクトリ（``data/raw/news/`` 等）。
        直下にソース名のサブディレクトリがある想定。
    sources : list[str] | None, optional
        対象ソース名のリスト。None で全ソース。
        空リスト ``[]`` の場合は空結果を返す。

    Returns
    -------
    list[ArticleRecord]
        URL 重複除去済みの記事レコードリスト

    Raises
    ------
    FileNotFoundError
        ``news_dir`` が存在しない場合
    """
    if not news_dir.exists():
        msg = f"News directory not found: {news_dir}"
        raise FileNotFoundError(msg)

    if sources is not None and len(sources) == 0:
        logger.info("Empty sources list provided, returning empty result")
        return []

    all_articles: list[ArticleRecord] = []

    # ソースディレクトリを列挙
    source_dirs = sorted(news_dir.iterdir()) if news_dir.is_dir() else []

    for source_path in source_dirs:
        if not source_path.is_dir():
            continue

        source_name = source_path.name

        # ソースフィルタリング
        if sources is not None and source_name not in sources:
            logger.debug("Skipping source: %s (not in filter)", source_name)
            continue

        # JSON ファイルを列挙して解析
        json_files = sorted(source_path.glob("*.json"))
        logger.info("Reading source: %s (%d files)", source_name, len(json_files))

        for json_path in json_files:
            records = _parse_json_file(json_path, source=source_name)
            all_articles.extend(records)

    logger.info("Total articles before dedup: %d", len(all_articles))
    deduplicated = deduplicate_by_url(all_articles)
    logger.info("Total articles after dedup: %d", len(deduplicated))

    return deduplicated


def _parse_json_file(
    json_path: Path,
    source: str,
) -> list[ArticleRecord]:
    """単一 JSON ファイルを解析し、ArticleRecord リストに変換する.

    各レコードを ``ArticleRecord`` に変換する。
    不正な JSON や必須フィールド欠落のレコードはスキップする。

    Parameters
    ----------
    json_path : Path
        解析対象の JSON ファイルパス
    source : str
        ソース名（ディレクトリ名から取得）

    Returns
    -------
    list[ArticleRecord]
        変換された記事レコードのリスト。エラー時は空リスト。
    """
    try:
        raw_text = json_path.read_text(encoding="utf-8")
        data = json.loads(raw_text)
    except (json.JSONDecodeError, UnicodeDecodeError) as e:
        logger.warning("Failed to parse JSON file: %s (%s)", json_path, e)
        return []

    if not isinstance(data, list):
        logger.warning(
            "Expected JSON array, got %s in file: %s",
            type(data).__name__,
            json_path,
        )
        return []

    records: list[ArticleRecord] = []

    for i, item in enumerate(data):
        if not isinstance(item, dict):
            logger.warning("Skipping non-dict item at index %d in %s", i, json_path)
            continue

        # 必須フィールドのチェック
        url = item.get("url", "")
        title = item.get("title", "")

        if not url:
            logger.warning(
                "Skipping record without url at index %d in %s", i, json_path
            )
            continue

        if not title:
            logger.warning(
                "Skipping record without title at index %d in %s", i, json_path
            )
            continue

        record = ArticleRecord(
            url=url,
            title=title,
            published=item.get("published", ""),
            summary=item.get("summary", ""),
            category=item.get("category", ""),
            source=source,
            ticker=item.get("ticker", ""),
            author=item.get("author", ""),
            article_id=item.get("article_id", ""),
            content=item.get("content", ""),
            json_file=str(json_path),
        )
        records.append(record)

    logger.debug("Parsed %d records from %s", len(records), json_path.name)
    return records


def deduplicate_by_url(
    articles: list[ArticleRecord],
) -> list[ArticleRecord]:
    """URL ベースで重複除去する（最初の出現を保持）.

    Parameters
    ----------
    articles : list[ArticleRecord]
        重複除去対象の記事リスト

    Returns
    -------
    list[ArticleRecord]
        重複除去済みの記事リスト（出現順序を維持）
    """
    seen_urls: set[str] = set()
    unique_articles: list[ArticleRecord] = []

    for article in articles:
        if article.url not in seen_urls:
            seen_urls.add(article.url)
            unique_articles.append(article)

    return unique_articles
