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

from .errors import (
    AcademicError,
    PaperNotFoundError,
    ParseError,
    PermanentError,
    RateLimitError,
    RetryableError,
)
from .retry import classify_http_error, create_retry_decorator
from .types import AcademicConfig, AuthorInfo, CitationInfo, PaperMetadata

__all__ = [
    "AcademicConfig",
    "AcademicError",
    "AuthorInfo",
    "CitationInfo",
    "PaperMetadata",
    "PaperNotFoundError",
    "ParseError",
    "PermanentError",
    "RateLimitError",
    "RetryableError",
    "classify_http_error",
    "create_retry_decorator",
]

__version__ = "0.1.0"
