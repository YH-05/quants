"""パイプライン統合モジュール.

reader -> chromadb 差分チェック -> extractor -> store の全ステップを統合し、
エンドツーエンドのパイプラインとして実行する。

Examples
--------
>>> import asyncio
>>> from embedding.pipeline import run_pipeline
>>> from embedding.types import PipelineConfig
>>> config = PipelineConfig()
>>> stats = asyncio.run(run_pipeline(config))
>>> stats["stored"]
42
"""

import logging

from .chromadb_store import get_existing_ids, store_articles, url_to_chromadb_id
from .extractor import extract_contents
from .reader import read_all_news_json
from .types import ArticleRecord, ExtractionResult, PipelineConfig

logger = logging.getLogger(__name__)


async def run_pipeline(config: PipelineConfig) -> dict[str, int]:
    """パイプラインを実行し、実行統計を返す.

    データフロー::

        read_all_news_json() -> list[ArticleRecord]
            |
        get_existing_ids() -> 新規記事フィルタ
            |
        extract_contents() -> list[ExtractionResult]
            |
        抽出成功分フィルタ -> store_articles()
            |
        実行統計 dict を返却

    Parameters
    ----------
    config : PipelineConfig
        パイプライン設定

    Returns
    -------
    dict[str, int]
        実行統計。以下のキーを含む:

        - ``total_json_articles``: JSON から読み込んだ全記事数
        - ``already_in_chromadb``: 既に ChromaDB にある記事数
        - ``new_articles``: 新規記事数
        - ``extraction_success``: 本文抽出成功数
        - ``extraction_failed``: 本文抽出失敗数
        - ``stored``: ChromaDB に格納した数
    """
    # Step 1: JSON 読み込み
    logger.info("Step 1: Reading news JSON from %s", config.news_dir)
    all_articles = read_all_news_json(config.news_dir, config.sources)
    total_json_articles = len(all_articles)
    logger.info("Read %d articles from JSON", total_json_articles)

    if total_json_articles == 0:
        logger.info("No articles found, pipeline complete")
        return _build_stats(
            total_json_articles=0,
            already_in_chromadb=0,
            new_articles=0,
            extraction_success=0,
            extraction_failed=0,
            stored=0,
        )

    # Step 2: ChromaDB 差分チェック
    logger.info("Step 2: Checking existing articles in ChromaDB")
    existing_ids = get_existing_ids(config.chromadb_path, config.collection_name)

    new_articles = _filter_new_articles(all_articles, existing_ids)
    already_in_chromadb = total_json_articles - len(new_articles)
    logger.info(
        "Found %d new articles (%d already in ChromaDB)",
        len(new_articles),
        already_in_chromadb,
    )

    if not new_articles:
        logger.info("No new articles to process, pipeline complete")
        return _build_stats(
            total_json_articles=total_json_articles,
            already_in_chromadb=already_in_chromadb,
            new_articles=0,
            extraction_success=0,
            extraction_failed=0,
            stored=0,
        )

    # Step 3: 本文抽出
    logger.info("Step 3: Extracting article contents (%d articles)", len(new_articles))
    extraction_results = await extract_contents(new_articles, config)

    # 成功・失敗を分類
    success_articles, success_results, extraction_failed = _filter_successful(
        new_articles, extraction_results
    )
    extraction_success = len(success_articles)
    logger.info(
        "Extraction: %d success, %d failed",
        extraction_success,
        extraction_failed,
    )

    if not success_articles:
        logger.warning("All extractions failed, skipping store")
        return _build_stats(
            total_json_articles=total_json_articles,
            already_in_chromadb=already_in_chromadb,
            new_articles=len(new_articles),
            extraction_success=0,
            extraction_failed=extraction_failed,
            stored=0,
        )

    # Step 4: ChromaDB 格納
    logger.info("Step 4: Storing %d articles in ChromaDB", len(success_articles))
    stored = store_articles(
        success_articles,
        success_results,
        config.chromadb_path,
        config.collection_name,
        config.dummy_dim,
    )
    logger.info("Stored %d articles in ChromaDB", stored)

    return _build_stats(
        total_json_articles=total_json_articles,
        already_in_chromadb=already_in_chromadb,
        new_articles=len(new_articles),
        extraction_success=extraction_success,
        extraction_failed=extraction_failed,
        stored=stored,
    )


def _filter_new_articles(
    articles: list[ArticleRecord],
    existing_ids: set[str],
) -> list[ArticleRecord]:
    """既存 ID に含まれない新規記事のみをフィルタする.

    Parameters
    ----------
    articles : list[ArticleRecord]
        全記事リスト
    existing_ids : set[str]
        ChromaDB に既存の ID セット

    Returns
    -------
    list[ArticleRecord]
        新規記事のリスト
    """
    new_articles: list[ArticleRecord] = []
    for article in articles:
        chromadb_id = url_to_chromadb_id(article.url)
        if chromadb_id not in existing_ids:
            new_articles.append(article)
    return new_articles


def _filter_successful(
    articles: list[ArticleRecord],
    results: list[ExtractionResult],
) -> tuple[list[ArticleRecord], list[ExtractionResult], int]:
    """抽出成功した記事と結果を分離する.

    Parameters
    ----------
    articles : list[ArticleRecord]
        記事リスト
    results : list[ExtractionResult]
        抽出結果リスト（articles と同順）

    Returns
    -------
    tuple[list[ArticleRecord], list[ExtractionResult], int]
        (成功した記事リスト, 成功した抽出結果リスト, 失敗数)
    """
    success_articles: list[ArticleRecord] = []
    success_results: list[ExtractionResult] = []
    failed_count = 0

    for article, result in zip(articles, results, strict=True):
        if result.method != "failed":
            success_articles.append(article)
            success_results.append(result)
        else:
            failed_count += 1
            logger.debug("Extraction failed for: %s", article.url)

    return success_articles, success_results, failed_count


def _build_stats(
    *,
    total_json_articles: int,
    already_in_chromadb: int,
    new_articles: int,
    extraction_success: int,
    extraction_failed: int,
    stored: int,
) -> dict[str, int]:
    """実行統計 dict を構築する.

    Parameters
    ----------
    total_json_articles : int
        JSON から読み込んだ全記事数
    already_in_chromadb : int
        既に ChromaDB にある記事数
    new_articles : int
        新規記事数
    extraction_success : int
        本文抽出成功数
    extraction_failed : int
        本文抽出失敗数
    stored : int
        ChromaDB に格納した数

    Returns
    -------
    dict[str, int]
        実行統計
    """
    return {
        "total_json_articles": total_json_articles,
        "already_in_chromadb": already_in_chromadb,
        "new_articles": new_articles,
        "extraction_success": extraction_success,
        "extraction_failed": extraction_failed,
        "stored": stored,
    }
