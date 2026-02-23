"""news_scraper テスト用共通フィクスチャ."""

import tempfile
from collections.abc import Iterator
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from news_scraper.exceptions import (
    BotDetectionError,
    ContentExtractionError,
    PermanentError,
    RateLimitError,
    RetryableError,
    ScraperError,
)
from news_scraper.types import Article, ScraperConfig


@pytest.fixture
def sample_article() -> Article:
    """テスト用のサンプル Article を返すフィクスチャ."""
    return Article(
        title="Test Article Title",
        url="https://example.com/news/test-article",
        published="2026-02-23T12:00:00+00:00",
        summary="This is a test article summary.",
        category="economy",
        source="cnbc",
        content="Full article content here.",
        ticker="AAPL",
        author="Test Author",
        article_id="cnbc-test-001",
        metadata={"editors_pick": True},
    )


@pytest.fixture
def sample_article_minimal() -> Article:
    """必須フィールドのみの Article を返すフィクスチャ."""
    return Article(
        title="Minimal Article",
        url="https://example.com/minimal",
    )


@pytest.fixture
def sample_config() -> ScraperConfig:
    """テスト用のデフォルト ScraperConfig を返すフィクスチャ."""
    return ScraperConfig(
        impersonate="chrome131",
        proxy=None,
        delay=1.0,
        jitter=0.5,
        timeout=30,
        include_content=False,
        use_playwright=False,
        max_concurrency=5,
        max_concurrency_content=3,
        max_retries=3,
    )


@pytest.fixture
def sample_config_fast() -> ScraperConfig:
    """遅延なしの ScraperConfig を返すフィクスチャ（高速テスト用）."""
    return ScraperConfig(
        delay=0.0,
        jitter=0.0,
        timeout=10,
        max_concurrency=1,
    )


@pytest.fixture
def temp_dir() -> Iterator[Path]:
    """テスト用の一時ディレクトリを返すフィクスチャ."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


@pytest.fixture
def mock_response() -> MagicMock:
    """モック HTTP レスポンスを返すフィクスチャ."""
    response = MagicMock()
    response.status_code = 200
    response.headers = {}
    response.text = "<html><body>Content</body></html>"
    return response


@pytest.fixture
def mock_response_429() -> MagicMock:
    """HTTP 429 レスポンスのモックを返すフィクスチャ."""
    response = MagicMock()
    response.status_code = 429
    response.headers = {"Retry-After": "60"}
    return response


@pytest.fixture
def mock_response_403() -> MagicMock:
    """HTTP 403 レスポンスのモックを返すフィクスチャ."""
    response = MagicMock()
    response.status_code = 403
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
def sample_scraper_error() -> ScraperError:
    """ScraperError のサンプルを返すフィクスチャ."""
    return ScraperError("スクレイピング中にエラーが発生しました")


@pytest.fixture
def sample_rate_limit_error() -> RateLimitError:
    """RateLimitError のサンプルを返すフィクスチャ."""
    return RateLimitError("Too Many Requests", status_code=429, retry_after=60)


@pytest.fixture
def sample_bot_detection_error() -> BotDetectionError:
    """BotDetectionError のサンプルを返すフィクスチャ."""
    return BotDetectionError("ボット検知によりブロックされました", status_code=403)


@pytest.fixture
def sample_permanent_error() -> PermanentError:
    """PermanentError のサンプルを返すフィクスチャ."""
    return PermanentError("Not Found", status_code=404)


@pytest.fixture
def sample_retryable_error() -> RetryableError:
    """RetryableError のサンプルを返すフィクスチャ."""
    return RetryableError("Server Error", status_code=503)


@pytest.fixture
def sample_content_extraction_error() -> ContentExtractionError:
    """ContentExtractionError のサンプルを返すフィクスチャ."""
    return ContentExtractionError("本文要素が見つかりません")
