"""Semantic Scholar API クライアント.

論文の著者・引用情報を Semantic Scholar Graph API から取得する。
httpx.Client ベースの同期 HTTP クライアントで、レート制限・リトライ・
エラーハンドリングを内蔵する。

主な機能
--------
- ``fetch_paper(arxiv_id)`` : 単一論文のメタデータ取得
- ``fetch_papers_batch(arxiv_ids)`` : バッチ取得（500件/リクエストで自動分割）
- HTTP エラーの例外マッピング（429, 404, 5xx）
- ``S2_API_KEY`` 環境変数 / ``AcademicConfig.s2_api_key`` による認証

Examples
--------
>>> from academic.s2_client import S2Client
>>> with S2Client() as client:
...     paper = client.fetch_paper("2301.00001")
...     print(paper["title"])

See Also
--------
academic.types : AcademicConfig データクラス
academic.errors : HTTP エラー例外クラス
academic.retry : リトライデコレータ
edgar.rate_limiter : RateLimiter クラス
"""

from __future__ import annotations

import os
from typing import Any

import httpx

# AIDEV-NOTE: RateLimiter は edgar パッケージに実装されているが、汎用的なレート制限
# ユーティリティとして academic でも再利用している。将来的に database パッケージ等の
# 共通レイヤーに移動する可能性があるが、現時点では edgar に依存したまま維持する。
from edgar.rate_limiter import RateLimiter
from utils_core.logging import get_logger

from .errors import PaperNotFoundError, RateLimitError, RetryableError
from .retry import classify_http_error, create_retry_decorator
from .types import AcademicConfig

logger = get_logger(__name__)

# Semantic Scholar Graph API のベース URL
_BASE_URL = "https://api.semanticscholar.org/graph/v1"

# fetch_paper で取得するフィールド
_PAPER_FIELDS = (
    "title,authors,externalIds,references,citations,"
    "abstract,publicationDate,fieldsOfStudy"
)

# バッチリクエストの最大件数（API 制限）
_BATCH_MAX_SIZE = 500


class S2Client:
    """Semantic Scholar API クライアント.

    httpx.Client ベースの同期 HTTP クライアント。
    RateLimiter(1 req/sec) でレート制限を適用し、
    tenacity ベースのリトライデコレータでリトライを行う。

    Parameters
    ----------
    config : AcademicConfig | None
        API 設定。None の場合はデフォルト設定を使用する。

    Attributes
    ----------
    _http_client : httpx.Client
        内部の HTTP クライアント
    _rate_limiter : RateLimiter
        レート制限
    _api_key : str | None
        Semantic Scholar API キー

    Examples
    --------
    >>> with S2Client() as client:
    ...     paper = client.fetch_paper("2301.00001")

    >>> config = AcademicConfig(s2_api_key="my-key", s2_rate_limit=0.5)
    >>> client = S2Client(config=config)
    >>> try:
    ...     papers = client.fetch_papers_batch(["2301.00001", "2301.00002"])
    ... finally:
    ...     client.close()
    """

    def __init__(self, config: AcademicConfig | None = None) -> None:
        if config is None:
            config = AcademicConfig()

        # API キー: config > 環境変数 の優先順位
        self._api_key = config.s2_api_key or os.environ.get("S2_API_KEY")

        # HTTP ヘッダー構築
        headers: dict[str, str] = {
            "Accept": "application/json",
        }
        if self._api_key is not None:
            headers["x-api-key"] = self._api_key

        # httpx.Client 初期化
        self._http_client = httpx.Client(
            base_url=_BASE_URL,
            headers=headers,
            timeout=config.timeout,
        )

        # レート制限: s2_rate_limit を max_requests_per_second に変換
        # s2_rate_limit=1 → 1 req/sec, s2_rate_limit=0.5 → 2 req/sec
        max_rps = (
            max(1, int(1.0 / config.s2_rate_limit)) if config.s2_rate_limit > 0 else 1
        )
        self._rate_limiter = RateLimiter(max_requests_per_second=max_rps)

        # リトライデコレータ
        self._retry = create_retry_decorator(
            max_attempts=config.max_retries,
            base_wait=0.5,
            max_wait=30.0,
        )

        logger.info(
            "S2Client initialized",
            has_api_key=self._api_key is not None,
            rate_limit_rps=max_rps,
            max_retries=config.max_retries,
            timeout=config.timeout,
        )

    def fetch_paper(self, arxiv_id: str) -> dict[str, Any]:
        """単一論文のメタデータを取得する.

        Semantic Scholar Graph API の ``/paper/arXiv:{id}`` エンドポイントを使用し、
        論文のタイトル・著者・引用・参照情報を取得する。

        Parameters
        ----------
        arxiv_id : str
            arXiv の論文 ID（例: "2301.00001"）

        Returns
        -------
        dict[str, Any]
            Semantic Scholar API のレスポンス JSON

        Raises
        ------
        PaperNotFoundError
            指定された arXiv ID の論文が見つからない場合（HTTP 404）
        RateLimitError
            レート制限に達した場合（HTTP 429）
        RetryableError
            サーバーエラーが発生した場合（HTTP 5xx）

        Examples
        --------
        >>> with S2Client() as client:
        ...     paper = client.fetch_paper("2301.00001")
        ...     print(paper["title"])
        """

        @self._retry
        def _do_fetch() -> dict[str, Any]:
            self._rate_limiter.acquire()

            url = f"/paper/arXiv:{arxiv_id}"
            logger.debug("Fetching paper", arxiv_id=arxiv_id, url=url)

            response = self._http_client.get(url, params={"fields": _PAPER_FIELDS})

            if response.status_code != 200:
                raise classify_http_error(response.status_code, response)

            data: dict[str, Any] = response.json()
            logger.info("Paper fetched", arxiv_id=arxiv_id, title=data.get("title"))
            return data

        return _do_fetch()

    def fetch_papers_batch(self, arxiv_ids: list[str]) -> list[dict[str, Any]]:
        """複数論文のメタデータをバッチ取得する.

        Semantic Scholar Graph API の ``POST /paper/batch`` エンドポイントを使用し、
        複数論文を一括取得する。500件を超える場合は自動的に分割してリクエストする。

        Parameters
        ----------
        arxiv_ids : list[str]
            arXiv の論文 ID リスト（例: ["2301.00001", "2301.00002"]）

        Returns
        -------
        list[dict[str, Any]]
            Semantic Scholar API のレスポンス JSON リスト

        Raises
        ------
        RateLimitError
            レート制限に達した場合（HTTP 429）
        RetryableError
            サーバーエラーが発生した場合（HTTP 5xx）

        Examples
        --------
        >>> with S2Client() as client:
        ...     papers = client.fetch_papers_batch(["2301.00001", "2301.00002"])
        ...     for p in papers:
        ...         print(p["title"])
        """
        if not arxiv_ids:
            return []

        results: list[dict[str, Any]] = []

        # 500件ずつに分割
        chunks = [
            arxiv_ids[i : i + _BATCH_MAX_SIZE]
            for i in range(0, len(arxiv_ids), _BATCH_MAX_SIZE)
        ]

        logger.info(
            "Batch fetch started",
            total_ids=len(arxiv_ids),
            num_chunks=len(chunks),
        )

        for chunk_idx, chunk in enumerate(chunks):
            chunk_results = self._fetch_batch_chunk(chunk, chunk_idx)
            results.extend(chunk_results)

        logger.info(
            "Batch fetch completed",
            total_ids=len(arxiv_ids),
            total_results=len(results),
        )

        return results

    def _fetch_batch_chunk(
        self, arxiv_ids: list[str], chunk_idx: int
    ) -> list[dict[str, Any]]:
        """バッチチャンク1つ分の論文を取得する.

        Parameters
        ----------
        arxiv_ids : list[str]
            arXiv ID リスト（最大500件）
        chunk_idx : int
            チャンクインデックス（ログ用）

        Returns
        -------
        list[dict[str, Any]]
            取得した論文データのリスト
        """

        @self._retry
        def _do_fetch() -> list[dict[str, Any]]:
            self._rate_limiter.acquire()

            ids_payload = [f"arXiv:{aid}" for aid in arxiv_ids]
            logger.debug(
                "Fetching batch chunk",
                chunk_idx=chunk_idx,
                chunk_size=len(arxiv_ids),
            )

            response = self._http_client.post(
                "/paper/batch",
                params={"fields": _PAPER_FIELDS},
                json={"ids": ids_payload},
            )

            if response.status_code != 200:
                raise classify_http_error(response.status_code, response)

            data: list[dict[str, Any]] = response.json()
            logger.info(
                "Batch chunk fetched",
                chunk_idx=chunk_idx,
                results_count=len(data),
            )
            return data

        return _do_fetch()

    def close(self) -> None:
        """HTTP クライアントをクローズする.

        内部の httpx.Client を閉じ、コネクションプールを解放する。
        S2Client 使用後は必ず呼び出すか、with 文を使用すること。
        """
        self._http_client.close()
        logger.debug("S2Client closed")

    def __enter__(self) -> S2Client:
        """コンテキストマネージャのエントリポイント."""
        return self

    def __exit__(self, *args: object) -> None:
        """コンテキストマネージャのクリーンアップ."""
        self.close()


__all__ = ["S2Client"]
