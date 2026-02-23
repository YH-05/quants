"""ChromaDB 格納モジュール.

URL-hash ベースの決定論的 ID 生成により、重複排除と差分更新を実現する。
ニュース収集 CLI で収集した記事を ChromaDB に格納する。

chromadb はオプション依存。未インストール環境でも ``import embedding`` が可能。

Examples
--------
>>> from pathlib import Path
>>> from embedding.chromadb_store import store_articles, get_existing_ids
>>> existing = get_existing_ids(Path("data/chromadb"), "gemini-embedding-001")
>>> count = store_articles(articles, results, Path("data/chromadb"), "gemini-embedding-001", 768)
"""

import hashlib
import logging
from pathlib import Path

import numpy as np

from .types import ArticleRecord, ExtractionResult

logger = logging.getLogger(__name__)

# chromadb はオプション依存。未インストール時は None にフォールバック。
try:
    import chromadb as _chromadb  # type: ignore[import-not-found]
except ImportError:
    _chromadb = None  # type: ignore[assignment]

# バッチサイズ: ChromaDB の add() を分割実行する単位
_BATCH_SIZE = 100


def url_to_chromadb_id(url: str) -> str:
    """URL から決定論的な ChromaDB ID を生成する.

    SHA-256 ハッシュの先頭16文字を使用することで、
    同じ URL は常に同じ ID にマッピングされる。

    Parameters
    ----------
    url : str
        記事の URL

    Returns
    -------
    str
        SHA-256 ハッシュの先頭16文字（16進数）
    """
    return hashlib.sha256(url.encode()).hexdigest()[:16]


def get_existing_ids(
    chromadb_path: Path,
    collection_name: str,
) -> set[str]:
    """コレクション内の既存 ID セットを取得する.

    Parameters
    ----------
    chromadb_path : Path
        ChromaDB の永続化パス
    collection_name : str
        コレクション名

    Returns
    -------
    set[str]
        コレクション内の全 ID のセット

    Raises
    ------
    ImportError
        chromadb がインストールされていない場合
    """
    if _chromadb is None:
        msg = "chromadb is not installed. Install it with: uv add chromadb"
        raise ImportError(msg)

    client = _chromadb.PersistentClient(str(chromadb_path))
    collection = client.get_or_create_collection(name=collection_name)

    count = collection.count()
    if count == 0:
        logger.debug("Collection '%s' is empty", collection_name)
        return set()

    data = collection.get()
    existing = set(data["ids"])
    logger.info(
        "Found %d existing IDs in collection '%s'", len(existing), collection_name
    )
    return existing


def _build_document(
    article: ArticleRecord,
    extraction: ExtractionResult,
) -> str:
    """ドキュメント文字列を構築する.

    ``"{title}\\n\\n{content_or_summary}"`` 形式で構築。
    ExtractionResult.content が空の場合は ArticleRecord.summary にフォールバックする。

    Parameters
    ----------
    article : ArticleRecord
        記事レコード
    extraction : ExtractionResult
        本文抽出結果

    Returns
    -------
    str
        ``"{title}\\n\\n{content}"`` 形式のドキュメント文字列
    """
    content = extraction.content if extraction.content else article.summary
    return f"{article.title}\n\n{content}"


def _build_metadata(
    article: ArticleRecord,
    extraction: ExtractionResult,
) -> dict[str, str]:
    """メタデータ辞書を構築する.

    全値を文字列型で返す。

    Parameters
    ----------
    article : ArticleRecord
        記事レコード
    extraction : ExtractionResult
        本文抽出結果

    Returns
    -------
    dict[str, str]
        メタデータ辞書
    """
    return {
        "url": article.url,
        "title": article.title,
        "source": article.source,
        "category": article.category,
        "ticker": article.ticker,
        "published": article.published,
        "author": article.author,
        "extraction_method": extraction.method,
        "extracted_at": extraction.extracted_at,
        "has_embedding": "false",
        "json_file": article.json_file,
    }


def store_articles(
    articles: list[ArticleRecord],
    results: list[ExtractionResult],
    chromadb_path: Path,
    collection_name: str,
    dummy_dim: int,
) -> int:
    """新規記事を ChromaDB にバッチ格納する.

    URL-hash ベースの決定論的 ID により、既存 ID と重複する記事はスキップする。
    100件単位でバッチ処理を行い、大量データの安定処理を実現する。

    Parameters
    ----------
    articles : list[ArticleRecord]
        格納する記事レコードのリスト
    results : list[ExtractionResult]
        本文抽出結果のリスト（articles と同順）
    chromadb_path : Path
        ChromaDB の永続化パス
    collection_name : str
        コレクション名
    dummy_dim : int
        ダミーベクトルの次元数

    Returns
    -------
    int
        新規格納した記事数

    Raises
    ------
    ImportError
        chromadb または numpy がインストールされていない場合
    """
    if _chromadb is None:
        msg = "chromadb is not installed. Install it with: uv add chromadb"
        raise ImportError(msg)

    if not articles:
        logger.info("No articles to store")
        return 0

    # 既存 ID を取得して重複をスキップ
    existing_ids = get_existing_ids(chromadb_path, collection_name)

    # 新規記事のみを抽出
    new_ids: list[str] = []
    new_documents: list[str] = []
    new_embeddings: list[list[float]] = []
    new_metadatas: list[dict[str, str]] = []

    dummy_vector = np.zeros(dummy_dim).tolist()

    for article, extraction in zip(articles, results, strict=True):
        chromadb_id = url_to_chromadb_id(article.url)

        if chromadb_id in existing_ids:
            logger.debug(
                "Skipping existing article: %s (id=%s)", article.url, chromadb_id
            )
            continue

        new_ids.append(chromadb_id)
        new_documents.append(_build_document(article, extraction))
        new_embeddings.append(dummy_vector)
        new_metadatas.append(_build_metadata(article, extraction))

    if not new_ids:
        logger.info("No new articles to store (all already exist)")
        return 0

    # ChromaDB に格納
    client = _chromadb.PersistentClient(str(chromadb_path))
    collection = client.get_or_create_collection(name=collection_name)

    total_stored = 0

    # バッチ分割して格納
    for batch_start in range(0, len(new_ids), _BATCH_SIZE):
        batch_end = min(batch_start + _BATCH_SIZE, len(new_ids))
        batch_ids = new_ids[batch_start:batch_end]
        batch_docs = new_documents[batch_start:batch_end]
        batch_embs = new_embeddings[batch_start:batch_end]
        batch_metas = new_metadatas[batch_start:batch_end]

        collection.add(
            ids=batch_ids,
            documents=batch_docs,
            embeddings=batch_embs,
            metadatas=batch_metas,
        )

        batch_size = len(batch_ids)
        total_stored += batch_size
        logger.info(
            "Stored batch %d-%d (%d articles)",
            batch_start,
            batch_end - 1,
            batch_size,
        )

    logger.info(
        "Total stored: %d new articles in collection '%s'",
        total_stored,
        collection_name,
    )
    return total_stored
