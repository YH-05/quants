"""PaperFetcher オーケストレータ.

S2Client + ArxivClient + SQLiteCache を統合し、
cache -> S2 -> arXiv の3段フォールバックで論文メタデータを取得する。

主な機能
--------
- ``fetch_paper(arxiv_id)`` : 単一論文のメタデータ取得（3段フォールバック）
- ``fetch_papers_batch(arxiv_ids)`` : バッチ取得（キャッシュ分離 + S2 バッチ + arXiv 個別フォールバック）
- DI 対応（テスト時にモック注入可能）

フォールバック戦略
------------------
1. キャッシュチェック -> ヒットなら即 return
2. S2Client.fetch_paper() -> 成功なら PaperMetadata に変換 + キャッシュ保存
3. PaperNotFoundError / RetryableError -> ArxivClient.fetch_paper() フォールバック（著者のみ）

Examples
--------
>>> from academic.fetcher import PaperFetcher
>>> with PaperFetcher() as fetcher:
...     paper = fetcher.fetch_paper("2301.00001")
...     print(paper.title)

See Also
--------
academic.s2_client : Semantic Scholar クライアント
academic.arxiv_client : arXiv クライアント
academic.cache : キャッシュアダプタ
academic.types : PaperMetadata, AcademicConfig データクラス
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from utils_core.logging import get_logger

from .arxiv_client import ArxivClient
from .cache import get_academic_cache, make_cache_key
from .errors import AcademicError, PaperNotFoundError, RetryableError
from .s2_client import S2Client
from .types import (
    AcademicConfig,
    AuthorInfo,
    CitationInfo,
    PaperMetadata,
)

if TYPE_CHECKING:
    from market.cache.cache import SQLiteCache

logger = get_logger(__name__)


class PaperFetcher:
    """S2Client + ArxivClient + SQLiteCache を統合するオーケストレータ.

    cache -> S2 -> arXiv の3段フォールバックで論文メタデータを取得する。
    DI 対応で、テスト時にはモックを注入可能。

    Parameters
    ----------
    s2_client : S2Client | None
        Semantic Scholar クライアント。None の場合はデフォルト設定で生成する。
    arxiv_client : ArxivClient | None
        arXiv クライアント。None の場合はデフォルト設定で生成する。
    cache : SQLiteCache | None
        キャッシュインスタンス。None の場合はデフォルト設定で生成する。
    config : AcademicConfig | None
        API 設定。クライアント・キャッシュ生成時に使用する。

    Examples
    --------
    >>> # デフォルト設定
    >>> fetcher = PaperFetcher()
    >>> paper = fetcher.fetch_paper("2301.00001")

    >>> # DI 注入（テスト用）
    >>> fetcher = PaperFetcher(
    ...     s2_client=mock_s2,
    ...     arxiv_client=mock_arxiv,
    ...     cache=mock_cache,
    ... )
    """

    def __init__(
        self,
        s2_client: S2Client | Any | None = None,
        arxiv_client: ArxivClient | Any | None = None,
        cache: SQLiteCache | Any | None = None,
        config: AcademicConfig | None = None,
    ) -> None:
        if config is None:
            config = AcademicConfig()

        self._s2_client = s2_client or S2Client(config=config)
        self._arxiv_client = arxiv_client or ArxivClient(config=config)
        self._cache = cache or get_academic_cache(config=config)

        logger.info("PaperFetcher initialized")

    def fetch_paper(self, arxiv_id: str) -> PaperMetadata:
        """単一論文のメタデータを取得する.

        cache -> S2 -> arXiv の3段フォールバックで取得を試みる。

        Parameters
        ----------
        arxiv_id : str
            arXiv の論文 ID（例: "2301.00001"）

        Returns
        -------
        PaperMetadata
            論文メタデータ

        Raises
        ------
        PaperNotFoundError
            全ソースで論文が見つからない場合
        AcademicError
            その他の取得エラー

        Examples
        --------
        >>> fetcher = PaperFetcher()
        >>> paper = fetcher.fetch_paper("2301.00001")
        >>> print(paper.title)
        """
        # 1. キャッシュチェック
        cache_key = make_cache_key(arxiv_id)
        cached = self._cache.get(cache_key)
        if cached is not None:
            logger.info("Cache hit", arxiv_id=arxiv_id)
            return _dict_to_paper_metadata(cached)

        # 2. S2Client で取得を試みる
        try:
            raw = self._s2_client.fetch_paper(arxiv_id)
            paper = self._parse_s2_response(raw, arxiv_id)
            self._save_to_cache(cache_key, paper)
            return paper
        except (PaperNotFoundError, RetryableError) as exc:
            logger.warning(
                "S2 fetch failed, falling back to arXiv",
                arxiv_id=arxiv_id,
                error=str(exc),
            )

        # 3. ArxivClient でフォールバック
        paper = self._arxiv_client.fetch_paper(arxiv_id)
        self._save_to_cache(cache_key, paper)
        return paper

    def fetch_papers_batch(self, arxiv_ids: list[str]) -> list[PaperMetadata]:
        """複数論文のメタデータをバッチ取得する.

        1. キャッシュ済みとキャッシュなしを分離
        2. 未キャッシュは S2 バッチ取得
        3. S2 で取得できなかったものは arXiv 個別フォールバック

        Parameters
        ----------
        arxiv_ids : list[str]
            arXiv の論文 ID リスト

        Returns
        -------
        list[PaperMetadata]
            論文メタデータのリスト（入力と同じ順序）

        Examples
        --------
        >>> fetcher = PaperFetcher()
        >>> papers = fetcher.fetch_papers_batch(["2301.00001", "2301.00002"])
        """
        if not arxiv_ids:
            return []

        # 結果マップ（順序保持用）
        results: dict[str, PaperMetadata] = {}

        # 1. キャッシュ済みとキャッシュなしを分離
        uncached_ids: list[str] = []
        for arxiv_id in arxiv_ids:
            cache_key = make_cache_key(arxiv_id)
            cached = self._cache.get(cache_key)
            if cached is not None:
                logger.debug("Batch cache hit", arxiv_id=arxiv_id)
                results[arxiv_id] = _dict_to_paper_metadata(cached)
            else:
                uncached_ids.append(arxiv_id)

        if not uncached_ids:
            logger.info("All papers found in cache", count=len(arxiv_ids))
            return [results[aid] for aid in arxiv_ids]

        # 2. 未キャッシュは S2 バッチ取得
        s2_failed_ids: list[str] = []
        try:
            s2_results = self._s2_client.fetch_papers_batch(uncached_ids)

            for idx, arxiv_id in enumerate(uncached_ids):
                if idx >= len(s2_results):
                    s2_failed_ids.append(arxiv_id)
                    continue
                raw: dict[str, Any] | None = s2_results[idx]
                if raw is None:
                    s2_failed_ids.append(arxiv_id)
                    continue
                paper = self._parse_s2_response(raw, arxiv_id)
                results[arxiv_id] = paper
                self._save_to_cache(make_cache_key(arxiv_id), paper)

        except (RetryableError, AcademicError) as exc:
            logger.warning(
                "S2 batch fetch failed, falling back to arXiv for all uncached",
                error=str(exc),
            )
            s2_failed_ids = uncached_ids

        # 3. S2 で取得できなかったものは arXiv 個別フォールバック
        for arxiv_id in s2_failed_ids:
            try:
                paper = self._arxiv_client.fetch_paper(arxiv_id)
                results[arxiv_id] = paper
                self._save_to_cache(make_cache_key(arxiv_id), paper)
            except AcademicError as exc:
                logger.error(
                    "arXiv fallback also failed",
                    arxiv_id=arxiv_id,
                    error=str(exc),
                )

        # 入力順序で返す
        return [results[aid] for aid in arxiv_ids if aid in results]

    def _parse_s2_response(self, raw: dict[str, Any], arxiv_id: str) -> PaperMetadata:
        """S2 レスポンスを PaperMetadata に変換する.

        Parameters
        ----------
        raw : dict[str, Any]
            S2Client.fetch_paper() の戻り値
        arxiv_id : str
            arXiv の論文 ID

        Returns
        -------
        PaperMetadata
            変換済みの論文メタデータ
        """
        # 著者
        authors = tuple(
            AuthorInfo(
                name=a.get("name", "Unknown"),
                s2_author_id=a.get("authorId"),
            )
            for a in (raw.get("authors") or [])
        )

        # 参考文献
        references = tuple(
            CitationInfo(
                title=r.get("title", ""),
                arxiv_id=(r.get("externalIds") or {}).get("ArXiv"),
                s2_paper_id=r.get("paperId"),
            )
            for r in (raw.get("references") or [])
        )

        # 被引用
        citations = tuple(
            CitationInfo(
                title=c.get("title", ""),
                arxiv_id=(c.get("externalIds") or {}).get("ArXiv"),
                s2_paper_id=c.get("paperId"),
            )
            for c in (raw.get("citations") or [])
        )

        paper = PaperMetadata(
            arxiv_id=arxiv_id,
            title=raw.get("title", ""),
            authors=authors,
            references=references,
            citations=citations,
            abstract=raw.get("abstract"),
            s2_paper_id=raw.get("paperId"),
            published=raw.get("publicationDate"),
        )

        logger.debug(
            "S2 response parsed",
            arxiv_id=arxiv_id,
            title=paper.title,
            num_authors=len(authors),
            num_references=len(references),
            num_citations=len(citations),
        )

        return paper

    def _save_to_cache(self, cache_key: str, paper: PaperMetadata) -> None:
        """PaperMetadata をキャッシュに保存する.

        Parameters
        ----------
        cache_key : str
            キャッシュキー
        paper : PaperMetadata
            保存する論文メタデータ
        """
        data = _paper_metadata_to_dict(paper)
        try:
            self._cache.set(cache_key, data)
            logger.debug("Paper cached", cache_key=cache_key)
        except Exception as exc:
            # キャッシュ保存失敗は致命的ではない
            logger.warning(
                "Cache save failed",
                cache_key=cache_key,
                error=str(exc),
            )

    def close(self) -> None:
        """内部クライアントをクローズする.

        DI で注入されたクライアントもクローズする。
        """
        if hasattr(self._s2_client, "close"):
            self._s2_client.close()
        if hasattr(self._arxiv_client, "close"):
            self._arxiv_client.close()
        logger.debug("PaperFetcher closed")

    def __enter__(self) -> PaperFetcher:
        """コンテキストマネージャのエントリポイント."""
        return self

    def __exit__(self, *args: object) -> None:
        """コンテキストマネージャのクリーンアップ."""
        self.close()


def _paper_metadata_to_dict(paper: PaperMetadata) -> dict[str, Any]:
    """PaperMetadata を dict に変換する（キャッシュ保存用）.

    Parameters
    ----------
    paper : PaperMetadata
        変換する論文メタデータ

    Returns
    -------
    dict[str, Any]
        シリアライズ可能な辞書
    """
    return {
        "arxiv_id": paper.arxiv_id,
        "title": paper.title,
        "authors": [
            {
                "name": a.name,
                "s2_author_id": a.s2_author_id,
                "organization": a.organization,
            }
            for a in paper.authors
        ],
        "references": [
            {
                "title": r.title,
                "arxiv_id": r.arxiv_id,
                "s2_paper_id": r.s2_paper_id,
            }
            for r in paper.references
        ],
        "citations": [
            {
                "title": c.title,
                "arxiv_id": c.arxiv_id,
                "s2_paper_id": c.s2_paper_id,
            }
            for c in paper.citations
        ],
        "abstract": paper.abstract,
        "s2_paper_id": paper.s2_paper_id,
        "published": paper.published,
        "updated": paper.updated,
    }


def _dict_to_paper_metadata(data: dict[str, Any]) -> PaperMetadata:
    """dict を PaperMetadata に変換する（キャッシュ復元用）.

    Parameters
    ----------
    data : dict[str, Any]
        キャッシュから取得した辞書

    Returns
    -------
    PaperMetadata
        復元された論文メタデータ
    """
    authors = tuple(
        AuthorInfo(
            name=a.get("name", "Unknown"),
            s2_author_id=a.get("s2_author_id"),
            organization=a.get("organization"),
        )
        for a in (data.get("authors") or [])
    )

    references = tuple(
        CitationInfo(
            title=r.get("title", ""),
            arxiv_id=r.get("arxiv_id"),
            s2_paper_id=r.get("s2_paper_id"),
        )
        for r in (data.get("references") or [])
    )

    citations = tuple(
        CitationInfo(
            title=c.get("title", ""),
            arxiv_id=c.get("arxiv_id"),
            s2_paper_id=c.get("s2_paper_id"),
        )
        for c in (data.get("citations") or [])
    )

    return PaperMetadata(
        arxiv_id=data["arxiv_id"],
        title=data.get("title", ""),
        authors=authors,
        references=references,
        citations=citations,
        abstract=data.get("abstract"),
        s2_paper_id=data.get("s2_paper_id"),
        published=data.get("published"),
        updated=data.get("updated"),
    )


__all__ = ["PaperFetcher"]
