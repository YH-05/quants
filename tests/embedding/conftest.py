"""embedding テストの共通フィクスチャ.

embedding パッケージのテストで使用する共通フィクスチャを定義する。
"""

import json
from pathlib import Path

import pytest

from embedding.types import ArticleRecord, ExtractionResult, PipelineConfig


@pytest.fixture
def sample_article_record() -> ArticleRecord:
    """基本的な ArticleRecord フィクスチャ."""
    return ArticleRecord(
        url="https://example.com/article/1",
        title="Test Article Title",
        published="2024-01-15T10:00:00+00:00",
        summary="Article summary",
        category="technology",
        source="cnbc",
        ticker="AAPL",
        author="John Doe",
        article_id="article-001",
        content="Article full content",
        extraction_method="trafilatura",
        extracted_at="2024-01-15T10:05:00+00:00",
        json_file="/data/raw/news/cnbc/2024-01-15.json",
    )


@pytest.fixture
def minimal_article_record() -> ArticleRecord:
    """必須フィールドのみの ArticleRecord フィクスチャ."""
    return ArticleRecord(
        url="https://example.com/article/minimal",
        title="Minimal Article",
    )


@pytest.fixture
def sample_pipeline_config() -> PipelineConfig:
    """デフォルト値の PipelineConfig フィクスチャ."""
    return PipelineConfig()


@pytest.fixture
def sample_extraction_result() -> ExtractionResult:
    """成功した ExtractionResult フィクスチャ."""
    return ExtractionResult(
        url="https://example.com/article/1",
        content="Extracted article content",
        method="trafilatura",
        extracted_at="2024-01-15T10:05:00+00:00",
    )


@pytest.fixture
def failed_extraction_result() -> ExtractionResult:
    """失敗した ExtractionResult フィクスチャ."""
    return ExtractionResult(
        url="https://example.com/article/failed",
        content="",
        method="failed",
        extracted_at="2024-01-15T10:05:00+00:00",
        error="All extraction methods failed",
    )


@pytest.fixture
def news_dir_with_data(tmp_path: Path) -> Path:
    """ニュース JSON ファイルを含む一時ディレクトリ."""
    news_dir = tmp_path / "news"
    news_dir.mkdir()

    # cnbc ソースのデータ
    cnbc_dir = news_dir / "cnbc"
    cnbc_dir.mkdir()
    cnbc_data = [
        {
            "url": "https://cnbc.com/article/1",
            "title": "CNBC Article 1",
            "published": "2024-01-15T10:00:00+00:00",
            "summary": "CNBC summary 1",
            "category": "markets",
            "ticker": "SPY",
            "author": "Reporter A",
            "article_id": "cnbc-001",
            "content": "CNBC content 1",
        },
        {
            "url": "https://cnbc.com/article/2",
            "title": "CNBC Article 2",
            "published": "2024-01-15T11:00:00+00:00",
            "summary": "CNBC summary 2",
            "category": "technology",
            "ticker": "AAPL",
            "author": "Reporter B",
            "article_id": "cnbc-002",
            "content": "CNBC content 2",
        },
    ]
    (cnbc_dir / "2024-01-15.json").write_text(
        json.dumps(cnbc_data, ensure_ascii=False), encoding="utf-8"
    )

    # nasdaq ソースのデータ
    nasdaq_dir = news_dir / "nasdaq"
    nasdaq_dir.mkdir()
    nasdaq_data = [
        {
            "url": "https://nasdaq.com/article/1",
            "title": "Nasdaq Article 1",
            "published": "2024-01-15T12:00:00+00:00",
            "summary": "Nasdaq summary 1",
            "category": "stocks",
            "ticker": "QQQ",
            "author": "Reporter C",
            "article_id": "nasdaq-001",
            "content": "Nasdaq content 1",
        },
    ]
    (nasdaq_dir / "2024-01-15.json").write_text(
        json.dumps(nasdaq_data, ensure_ascii=False), encoding="utf-8"
    )

    return news_dir


@pytest.fixture
def news_dir_empty(tmp_path: Path) -> Path:
    """空のニュースディレクトリ."""
    news_dir = tmp_path / "news_empty"
    news_dir.mkdir()
    return news_dir
