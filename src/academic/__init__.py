"""academic - 学術論文データ取得・分析パッケージ.

arXiv 論文の著者・引用情報を自動取得するためのパッケージ。
Semantic Scholar API および arXiv API と連携し、
論文メタデータの収集・構造化を行う。

Examples
--------
>>> from academic.types import PaperMetadata, AuthorInfo
>>> author = AuthorInfo(name="John Doe")
>>> author.name
'John Doe'
"""

from .arxiv_client import ArxivClient
from .cache import get_academic_cache, make_cache_key
from .errors import (
    AcademicError,
    PaperNotFoundError,
    ParseError,
    PermanentError,
    RateLimitError,
    RetryableError,
)
from .fetcher import PaperFetcher, paper_metadata_to_dict
from .mapper import map_academic_papers
from .retry import classify_http_error, create_retry_decorator
from .s2_client import S2Client
from .types import AcademicConfig, AuthorInfo, CitationInfo, PaperMetadata

__all__ = [
    "AcademicConfig",
    "AcademicError",
    "ArxivClient",
    "AuthorInfo",
    "CitationInfo",
    "PaperFetcher",
    "PaperMetadata",
    "PaperNotFoundError",
    "ParseError",
    "PermanentError",
    "RateLimitError",
    "RetryableError",
    "S2Client",
    "classify_http_error",
    "create_retry_decorator",
    "get_academic_cache",
    "make_cache_key",
    "map_academic_papers",
    "paper_metadata_to_dict",
]

__version__ = "0.1.0"
