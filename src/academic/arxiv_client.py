"""arXiv API クライアント（Semantic Scholar のフォールバック用）.

arXiv Atom API を使用して論文メタデータを取得する。
feedparser で Atom XML をパースし、PaperMetadata に変換する。

主な機能
--------
- ``fetch_paper(arxiv_id)`` : 単一論文のメタデータ取得
- feedparser による Atom XML パース
- RateLimiter(3 req/sec) によるレート制限
- HTTP エラーの例外マッピング

Notes
-----
arXiv API は引用情報（references/citations）を提供しないため、
これらのフィールドは常に空タプルとなる。引用情報が必要な場合は
S2Client（Semantic Scholar）を使用すること。

Examples
--------
>>> from academic.arxiv_client import ArxivClient
>>> with ArxivClient() as client:
...     paper = client.fetch_paper("2301.00001")
...     print(paper.title)

See Also
--------
academic.types : PaperMetadata, AcademicConfig データクラス
academic.errors : 例外クラス
academic.s2_client : Semantic Scholar クライアント（プライマリ）
edgar.rate_limiter : RateLimiter クラス
"""

from __future__ import annotations

import xml.etree.ElementTree as ET
from typing import Any

import feedparser
import httpx

# AIDEV-NOTE: RateLimiter は edgar パッケージに実装されているが、汎用的なレート制限
# ユーティリティとして academic でも再利用している。将来的に database パッケージ等の
# 共通レイヤーに移動する可能性があるが、現時点では edgar に依存したまま維持する。
from edgar.rate_limiter import RateLimiter
from utils_core.logging import get_logger

from .errors import PaperNotFoundError, ParseError
from .retry import classify_http_error, create_retry_decorator
from .types import AcademicConfig, AuthorInfo, PaperMetadata

logger = get_logger(__name__)

# arXiv API ベース URL
_BASE_URL = "https://export.arxiv.org/api"


class ArxivClient:
    """arXiv API クライアント.

    httpx.Client ベースの同期 HTTP クライアント。
    RateLimiter でレート制限を適用し、feedparser で Atom XML をパースする。

    Parameters
    ----------
    config : AcademicConfig | None
        API 設定。None の場合はデフォルト設定を使用する。

    Attributes
    ----------
    _http_client : httpx.Client
        内部の HTTP クライアント
    _rate_limiter : RateLimiter
        レート制限（デフォルト: 3 req/sec）

    Examples
    --------
    >>> with ArxivClient() as client:
    ...     paper = client.fetch_paper("2301.00001")
    ...     print(paper.title)

    >>> config = AcademicConfig(arxiv_rate_limit=5, timeout=60.0)
    >>> client = ArxivClient(config=config)
    >>> try:
    ...     paper = client.fetch_paper("2301.00001")
    ... finally:
    ...     client.close()
    """

    def __init__(self, config: AcademicConfig | None = None) -> None:
        if config is None:
            config = AcademicConfig()

        # httpx.Client 初期化
        self._http_client = httpx.Client(
            base_url=_BASE_URL,
            timeout=config.timeout,
        )

        # レート制限: arxiv_rate_limit を max_requests_per_second に変換
        # arxiv_rate_limit はリクエスト間隔（秒）ではなく、1秒あたりのリクエスト数として扱う
        # デフォルト値 3 → 3 req/sec
        max_rps = max(1, int(config.arxiv_rate_limit))
        self._rate_limiter = RateLimiter(max_requests_per_second=max_rps)

        # リトライデコレータ
        self._retry = create_retry_decorator(
            max_attempts=config.max_retries,
            base_wait=1.0,
            max_wait=30.0,
        )

        logger.info(
            "ArxivClient initialized",
            rate_limit_rps=max_rps,
            max_retries=config.max_retries,
            timeout=config.timeout,
        )

    def fetch_paper(self, arxiv_id: str) -> PaperMetadata:
        """単一論文のメタデータを arXiv API から取得する.

        arXiv Atom API の ``query?id_list={id}`` エンドポイントを使用し、
        論文メタデータを取得して PaperMetadata に変換する。

        Parameters
        ----------
        arxiv_id : str
            arXiv の論文 ID（例: "2301.00001"）

        Returns
        -------
        PaperMetadata
            パース済みの論文メタデータ

        Raises
        ------
        PaperNotFoundError
            指定された arXiv ID の論文が見つからない場合（entries 空）
        ParseError
            Atom XML のパースに失敗した場合
        RetryableError
            サーバーエラーが発生した場合（HTTP 5xx）

        Examples
        --------
        >>> with ArxivClient() as client:
        ...     paper = client.fetch_paper("2301.00001")
        ...     print(paper.title)
        ...     print(paper.authors)
        """

        @self._retry
        def _do_fetch() -> PaperMetadata:
            self._rate_limiter.acquire()

            url = "/query"
            params = {"id_list": arxiv_id}
            logger.debug("Fetching paper from arXiv", arxiv_id=arxiv_id, url=url)

            response = self._http_client.get(url, params=params)

            if response.status_code != 200:
                raise classify_http_error(response.status_code, response)

            return _parse_atom_response(response.text, arxiv_id)

        return _do_fetch()

    def close(self) -> None:
        """HTTP クライアントをクローズする.

        内部の httpx.Client を閉じ、コネクションプールを解放する。
        ArxivClient 使用後は必ず呼び出すか、with 文を使用すること。
        """
        self._http_client.close()
        logger.debug("ArxivClient closed")

    def __enter__(self) -> ArxivClient:
        """コンテキストマネージャのエントリポイント."""
        return self

    def __exit__(self, *args: object) -> None:
        """コンテキストマネージャのクリーンアップ."""
        self.close()


def _parse_atom_response(text: str, arxiv_id: str) -> PaperMetadata:
    """arXiv Atom XML レスポンスをパースして PaperMetadata に変換する.

    feedparser でエントリのメタデータを取得し、ElementTree で著者情報
    （arxiv:affiliation を含む）を抽出する。XML パースは ET.fromstring() で
    1回のみ行い、feedparser と ET の結果を統合する。

    Parameters
    ----------
    text : str
        arXiv API の Atom XML レスポンス本文
    arxiv_id : str
        リクエストした arXiv ID（エラーメッセージ用）

    Returns
    -------
    PaperMetadata
        パース済みの論文メタデータ

    Raises
    ------
    PaperNotFoundError
        entries が空の場合
    ParseError
        XML パースに失敗した場合
    """
    # AIDEV-NOTE: feedparser と ET の2段階パースを統合。
    # ET.fromstring() で1回だけ XML をパースし、feedparser の結果と合わせて
    # PaperMetadata を構築する。feedparser は entry の title / summary /
    # published / updated 等を安全に抽出するために使用し、ET は
    # arxiv:affiliation を含む著者情報の抽出に使用する。

    # 1. ET で XML をパース（1回のみ）
    try:
        root = ET.fromstring(text)
    except ET.ParseError as exc:
        raise ParseError(f"arXiv Atom フィードのパースに失敗しました: {exc}") from exc

    # 2. feedparser でエントリメタデータを取得
    try:
        feed = feedparser.parse(text)
    except Exception as exc:
        raise ParseError(f"arXiv Atom フィードのパースに失敗しました: {exc}") from exc

    # feedparser はパースエラーでも空の feed を返す場合がある
    if feed.bozo and not feed.entries:
        bozo_exception = feed.get("bozo_exception", "Unknown parse error")
        raise ParseError(f"arXiv Atom フィードのパースに失敗しました: {bozo_exception}")

    if not feed.entries:
        raise PaperNotFoundError(
            f"論文が見つかりません: {arxiv_id}",
            status_code=404,
        )

    entry = feed.entries[0]

    # 3. 著者抽出: ET の既にパース済み root を再利用
    authors = _extract_authors_from_root(root)

    return _entry_to_paper_metadata(entry, arxiv_id, authors)


def _entry_to_paper_metadata(
    entry: Any, arxiv_id: str, authors: list[AuthorInfo]
) -> PaperMetadata:
    """feedparser の entry を PaperMetadata に変換する.

    Parameters
    ----------
    entry : Any
        feedparser の FeedParserDict エントリ
    arxiv_id : str
        arXiv ID
    authors : list[AuthorInfo]
        ElementTree でパース済みの著者リスト

    Returns
    -------
    PaperMetadata
        変換済みメタデータ
    """
    # タイトル: 改行を除去
    title = entry.get("title", "").replace("\n", " ").strip()

    # アブストラクト
    abstract = entry.get("summary", "").strip() or None

    # 公開日・更新日
    published = entry.get("published")
    updated = entry.get("updated")

    logger.debug(
        "Parsed arXiv entry",
        arxiv_id=arxiv_id,
        title=title,
        num_authors=len(authors),
    )

    return PaperMetadata(
        arxiv_id=arxiv_id,
        title=title,
        authors=tuple(authors),
        references=(),  # arXiv API は引用情報を提供しない
        citations=(),  # arXiv API は被引用情報を提供しない
        abstract=abstract,
        s2_paper_id=None,
        published=published,
        updated=updated,
    )


def _extract_authors_from_root(root: ET.Element) -> list[AuthorInfo]:
    """パース済み XML ルートから著者情報（名前 + アフィリエーション）を抽出する.

    feedparser は arxiv:affiliation を per-author で保持しないため、
    xml.etree.ElementTree でパース済みのルート要素から直接抽出する。

    Parameters
    ----------
    root : ET.Element
        ET.fromstring() でパース済みの XML ルート要素

    Returns
    -------
    list[AuthorInfo]
        著者情報のリスト
    """
    ns = {
        "atom": "http://www.w3.org/2005/Atom",
        "arxiv": "http://arxiv.org/schemas/atom",
    }

    authors: list[AuthorInfo] = []

    # entry 要素内の author 要素を走査
    for entry_elem in root.findall("atom:entry", ns):
        for author_elem in entry_elem.findall("atom:author", ns):
            name_elem = author_elem.find("atom:name", ns)
            if name_elem is None or not (name_elem.text or "").strip():
                continue

            name = (name_elem.text or "").strip()

            # arxiv:affiliation の取得
            affiliation_elem = author_elem.find("arxiv:affiliation", ns)
            organization = None
            if affiliation_elem is not None and affiliation_elem.text:
                organization = affiliation_elem.text.strip() or None

            authors.append(
                AuthorInfo(
                    name=name,
                    s2_author_id=None,
                    organization=organization,
                )
            )

    return authors


__all__ = ["ArxivClient"]
