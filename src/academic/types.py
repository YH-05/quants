"""academic パッケージの型定義.

学術論文メタデータの構造化に使用する frozen dataclass を提供する。

型定義一覧
----------
- AuthorInfo: 論文著者の情報
- CitationInfo: 引用論文の情報
- PaperMetadata: 論文メタデータの全体構造
- AcademicConfig: API 設定

全て frozen=True で不変オブジェクトとして定義されている。
"""

from dataclasses import dataclass, field


@dataclass(frozen=True)
class AuthorInfo:
    """論文著者の情報.

    Parameters
    ----------
    name : str
        著者名
    s2_author_id : str | None
        Semantic Scholar の著者 ID
    organization : str | None
        所属組織

    Examples
    --------
    >>> author = AuthorInfo(name="John Doe")
    >>> author.name
    'John Doe'
    >>> author.s2_author_id is None
    True

    >>> author_with_id = AuthorInfo(
    ...     name="Jane Smith",
    ...     s2_author_id="12345",
    ...     organization="MIT",
    ... )
    >>> author_with_id.organization
    'MIT'
    """

    name: str
    s2_author_id: str | None = None
    organization: str | None = None


@dataclass(frozen=True)
class CitationInfo:
    """引用論文の情報.

    Parameters
    ----------
    title : str
        引用先論文のタイトル
    arxiv_id : str | None
        arXiv の論文 ID（例: "2301.00001"）
    s2_paper_id : str | None
        Semantic Scholar の論文 ID

    Examples
    --------
    >>> citation = CitationInfo(title="Attention Is All You Need")
    >>> citation.title
    'Attention Is All You Need'
    >>> citation.arxiv_id is None
    True

    >>> citation_full = CitationInfo(
    ...     title="BERT",
    ...     arxiv_id="1810.04805",
    ...     s2_paper_id="s2-abc123",
    ... )
    >>> citation_full.arxiv_id
    '1810.04805'
    """

    title: str
    arxiv_id: str | None = None
    s2_paper_id: str | None = None


@dataclass(frozen=True)
class PaperMetadata:
    """論文メタデータの全体構造.

    arXiv 論文の著者・引用・参照情報を含む包括的なメタデータ。

    Parameters
    ----------
    arxiv_id : str
        arXiv の論文 ID（例: "2301.00001"）
    title : str
        論文タイトル
    authors : tuple[AuthorInfo, ...]
        著者リスト（順序保持）
    references : tuple[CitationInfo, ...]
        参考文献リスト
    citations : tuple[CitationInfo, ...]
        被引用リスト
    abstract : str | None
        論文の要旨
    s2_paper_id : str | None
        Semantic Scholar の論文 ID
    published : str | None
        公開日（ISO 8601 形式）
    updated : str | None
        更新日（ISO 8601 形式）

    Examples
    --------
    >>> paper = PaperMetadata(
    ...     arxiv_id="2301.00001",
    ...     title="Sample Paper",
    ...     authors=(AuthorInfo(name="Alice"),),
    ...     references=(),
    ...     citations=(),
    ... )
    >>> paper.arxiv_id
    '2301.00001'
    >>> len(paper.authors)
    1
    """

    arxiv_id: str
    title: str
    authors: tuple[AuthorInfo, ...] = field(default_factory=tuple)
    references: tuple[CitationInfo, ...] = field(default_factory=tuple)
    citations: tuple[CitationInfo, ...] = field(default_factory=tuple)
    abstract: str | None = None
    s2_paper_id: str | None = None
    published: str | None = None
    updated: str | None = None


@dataclass(frozen=True)
class AcademicConfig:
    """API 設定.

    Semantic Scholar / arXiv API のレート制限やキャッシュ設定を管理する。

    Parameters
    ----------
    s2_api_key : str | None
        Semantic Scholar API キー（None の場合はレート制限が厳しくなる）
    s2_rate_limit : float
        Semantic Scholar API のリクエスト間隔（秒、デフォルト: 1）
    arxiv_rate_limit : float
        arXiv API のリクエスト間隔（秒、デフォルト: 3）
    cache_ttl : int
        キャッシュの有効期間（秒、デフォルト: 604800 = 7日）
    max_retries : int
        最大リトライ回数（デフォルト: 3）
    timeout : float
        HTTP リクエストタイムアウト（秒、デフォルト: 30.0）

    Examples
    --------
    >>> config = AcademicConfig()
    >>> config.s2_rate_limit
    1.0
    >>> config.cache_ttl
    604800

    >>> config_with_key = AcademicConfig(
    ...     s2_api_key="my-api-key",
    ...     s2_rate_limit=0.5,
    ... )
    >>> config_with_key.s2_api_key
    'my-api-key'
    """

    s2_api_key: str | None = None
    s2_rate_limit: float = 1.0
    arxiv_rate_limit: float = 3.0
    cache_ttl: int = 604800
    max_retries: int = 3
    timeout: float = 30.0


__all__ = [
    "AcademicConfig",
    "AuthorInfo",
    "CitationInfo",
    "PaperMetadata",
]
