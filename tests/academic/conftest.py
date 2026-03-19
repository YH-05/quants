"""academic テスト用共通フィクスチャ."""

from unittest.mock import MagicMock

import pytest

from academic.errors import (
    AcademicError,
    PaperNotFoundError,
    ParseError,
    PermanentError,
    RateLimitError,
    RetryableError,
)
from academic.types import AcademicConfig, AuthorInfo, CitationInfo, PaperMetadata


@pytest.fixture
def sample_author() -> AuthorInfo:
    """テスト用のサンプル AuthorInfo を返すフィクスチャ."""
    return AuthorInfo(
        name="John Doe",
        s2_author_id="12345",
        organization="MIT",
    )


@pytest.fixture
def sample_author_minimal() -> AuthorInfo:
    """必須フィールドのみの AuthorInfo を返すフィクスチャ."""
    return AuthorInfo(name="Jane Smith")


@pytest.fixture
def sample_citation() -> CitationInfo:
    """テスト用のサンプル CitationInfo を返すフィクスチャ."""
    return CitationInfo(
        title="Attention Is All You Need",
        arxiv_id="1706.03762",
        s2_paper_id="s2-abc123",
    )


@pytest.fixture
def sample_citation_minimal() -> CitationInfo:
    """必須フィールドのみの CitationInfo を返すフィクスチャ."""
    return CitationInfo(title="Sample Paper")


@pytest.fixture
def sample_paper_metadata() -> PaperMetadata:
    """テスト用のサンプル PaperMetadata を返すフィクスチャ."""
    return PaperMetadata(
        arxiv_id="2301.00001",
        title="Sample Research Paper",
        authors=(
            AuthorInfo(name="Alice", s2_author_id="a1"),
            AuthorInfo(name="Bob", organization="Stanford"),
        ),
        references=(CitationInfo(title="Ref Paper 1", arxiv_id="2001.00001"),),
        citations=(CitationInfo(title="Citing Paper 1", s2_paper_id="s2-cite1"),),
        abstract="This is a sample abstract.",
        s2_paper_id="s2-paper-001",
        published="2023-01-01T00:00:00Z",
        updated="2023-06-15T00:00:00Z",
    )


@pytest.fixture
def sample_paper_metadata_minimal() -> PaperMetadata:
    """必須フィールドのみの PaperMetadata を返すフィクスチャ."""
    return PaperMetadata(
        arxiv_id="2301.00001",
        title="Minimal Paper",
    )


@pytest.fixture
def sample_config() -> AcademicConfig:
    """テスト用のデフォルト AcademicConfig を返すフィクスチャ."""
    return AcademicConfig()


@pytest.fixture
def sample_config_with_key() -> AcademicConfig:
    """API キー付きの AcademicConfig を返すフィクスチャ."""
    return AcademicConfig(
        s2_api_key="test-api-key",
        s2_rate_limit=0.5,
        arxiv_rate_limit=1.0,
        cache_ttl=3600,
        max_retries=5,
        timeout=60.0,
    )


@pytest.fixture
def mock_response() -> MagicMock:
    """モック HTTP レスポンスを返すフィクスチャ."""
    response = MagicMock()
    response.status_code = 200
    response.headers = {}
    return response


@pytest.fixture
def mock_response_429() -> MagicMock:
    """HTTP 429 レスポンスのモックを返すフィクスチャ."""
    response = MagicMock()
    response.status_code = 429
    response.headers = {"Retry-After": "60"}
    return response


@pytest.fixture
def mock_response_404() -> MagicMock:
    """HTTP 404 レスポンスのモックを返すフィクスチャ."""
    response = MagicMock()
    response.status_code = 404
    response.headers = {}
    return response


@pytest.fixture
def mock_response_500() -> MagicMock:
    """HTTP 500 レスポンスのモックを返すフィクスチャ."""
    response = MagicMock()
    response.status_code = 500
    response.headers = {}
    return response


@pytest.fixture
def sample_academic_error() -> AcademicError:
    """AcademicError のサンプルを返すフィクスチャ."""
    return AcademicError("学術データ取得エラー")


@pytest.fixture
def sample_rate_limit_error() -> RateLimitError:
    """RateLimitError のサンプルを返すフィクスチャ."""
    return RateLimitError("Too Many Requests", status_code=429, retry_after=60)


@pytest.fixture
def sample_paper_not_found_error() -> PaperNotFoundError:
    """PaperNotFoundError のサンプルを返すフィクスチャ."""
    return PaperNotFoundError("論文が見つかりません", status_code=404)


@pytest.fixture
def sample_permanent_error() -> PermanentError:
    """PermanentError のサンプルを返すフィクスチャ."""
    return PermanentError("Forbidden", status_code=403)


@pytest.fixture
def sample_retryable_error() -> RetryableError:
    """RetryableError のサンプルを返すフィクスチャ."""
    return RetryableError("Server Error", status_code=503)


@pytest.fixture
def sample_parse_error() -> ParseError:
    """ParseError のサンプルを返すフィクスチャ."""
    return ParseError("XML パースに失敗しました")
