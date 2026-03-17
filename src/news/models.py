"""Data models for the news collection workflow.

This module provides core data models for representing news article sources
and their metadata in a unified format. These models are used throughout
the news collection pipeline.

Notes
-----
- `SourceType` represents the type of data source (RSS, yfinance, scraper)
- `ArticleSource` represents metadata about where an article came from
- `CollectedArticle` represents an article collected from a source

Examples
--------
>>> from news.models import SourceType, ArticleSource
>>> source = ArticleSource(
...     source_type=SourceType.RSS,
...     source_name="CNBC Markets",
...     category="market",
... )
>>> source.source_type
<SourceType.RSS: 'rss'>
"""

from datetime import datetime
from enum import StrEnum

from pydantic import BaseModel, Field, HttpUrl


class SourceType(StrEnum):
    """Type of news data source.

    Represents the type of source from which news articles are collected.
    This is used to determine how to fetch and process articles.

    Attributes
    ----------
    RSS : str
        RSS feed source. Articles are fetched via RSS/Atom feeds.
    YFINANCE : str
        Yahoo Finance source. Articles are fetched via yfinance API.
    SCRAPE : str
        Web scraping source. Articles are fetched via custom scrapers.

    Examples
    --------
    >>> SourceType.RSS
    <SourceType.RSS: 'rss'>
    >>> SourceType.RSS == "rss"
    True
    >>> SourceType.YFINANCE.value
    'yfinance'
    """

    RSS = "rss"
    YFINANCE = "yfinance"
    SCRAPE = "scrape"


class ArticleSource(BaseModel):
    """Metadata about the source of a news article.

    Represents information about where an article came from, including
    the source type, name, category for mapping, and optional feed ID.

    Attributes
    ----------
    source_type : SourceType
        The type of source (RSS, yfinance, or scraper).
    source_name : str
        Human-readable name of the source (e.g., "CNBC Markets", "NVDA").
    category : str
        Category for status mapping (e.g., "market", "yf_ai_stock").
        This is used to determine the GitHub Project status.
    feed_id : str | None
        Optional feed identifier for RSS sources.
        Not used for yfinance or scraper sources.

    Examples
    --------
    >>> from news.models import ArticleSource, SourceType
    >>> # RSS source
    >>> rss_source = ArticleSource(
    ...     source_type=SourceType.RSS,
    ...     source_name="CNBC Markets",
    ...     category="market",
    ...     feed_id="cnbc-markets-001",
    ... )
    >>> rss_source.source_type
    <SourceType.RSS: 'rss'>

    >>> # yfinance source
    >>> yf_source = ArticleSource(
    ...     source_type=SourceType.YFINANCE,
    ...     source_name="NVDA",
    ...     category="yf_ai_stock",
    ... )
    >>> yf_source.feed_id is None
    True
    """

    source_type: SourceType = Field(
        ...,
        description="Type of the data source (RSS, yfinance, or scraper)",
    )
    source_name: str = Field(
        ...,
        description="Human-readable name of the source",
    )
    category: str = Field(
        ...,
        description="Category for status mapping (e.g., 'market', 'yf_ai_stock')",
    )
    feed_id: str | None = Field(
        default=None,
        description="Optional feed identifier for RSS sources",
    )


class ExtractionStatus(StrEnum):
    """Status of article body extraction.

    Represents the result status of attempting to extract the main content
    from an article URL. This is used to track whether extraction succeeded
    or why it failed.

    Attributes
    ----------
    SUCCESS : str
        Extraction completed successfully. The body_text field will contain
        the extracted content.
    FAILED : str
        Extraction failed for an unspecified reason. Check error_message
        for details.
    PAYWALL : str
        The article is behind a paywall and content could not be extracted.
    TIMEOUT : str
        The extraction request timed out before completing.

    Examples
    --------
    >>> ExtractionStatus.SUCCESS
    <ExtractionStatus.SUCCESS: 'success'>
    >>> ExtractionStatus.SUCCESS == "success"
    True
    >>> ExtractionStatus.PAYWALL.value
    'paywall'
    """

    SUCCESS = "success"
    FAILED = "failed"
    PAYWALL = "paywall"
    TIMEOUT = "timeout"


class CollectedArticle(BaseModel):
    """An article collected from a news source.

    Represents an article immediately after collection, before any processing
    such as summarization or classification. This is the output of a Collector.

    Attributes
    ----------
    url : HttpUrl
        The original URL of the article.
    title : str
        The article title.
    published : datetime | None
        The publication date/time of the article, if available.
    raw_summary : str | None
        The original summary from the source (e.g., RSS summary field).
        This is the unprocessed summary from the data source.
    source : ArticleSource
        Metadata about where the article came from.
    collected_at : datetime
        The timestamp when the article was collected.

    Examples
    --------
    >>> from datetime import datetime, timezone
    >>> from news.models import ArticleSource, CollectedArticle, SourceType
    >>> source = ArticleSource(
    ...     source_type=SourceType.RSS,
    ...     source_name="CNBC Markets",
    ...     category="market",
    ... )
    >>> article = CollectedArticle(
    ...     url="https://www.cnbc.com/article/123",
    ...     title="Market Update",
    ...     source=source,
    ...     collected_at=datetime.now(tz=timezone.utc),
    ... )
    >>> article.title
    'Market Update'
    """

    url: HttpUrl = Field(
        ...,
        description="The original URL of the article",
    )
    title: str = Field(
        ...,
        description="The article title",
    )
    published: datetime | None = Field(
        default=None,
        description="The publication date/time of the article, if available",
    )
    raw_summary: str | None = Field(
        default=None,
        description="The original summary from the source (e.g., RSS summary field)",
    )
    source: ArticleSource = Field(
        ...,
        description="Metadata about where the article came from",
    )
    collected_at: datetime = Field(
        ...,
        description="The timestamp when the article was collected",
    )


class ExtractedArticle(BaseModel):
    """An article after body text extraction.

    Represents an article after attempting to extract its main body content
    from the original URL. This is the output of an Extractor component.

    The extraction may succeed (body_text contains content) or fail for
    various reasons (paywall, timeout, other errors).

    Attributes
    ----------
    collected : CollectedArticle
        The original collected article that was processed.
    body_text : str | None
        The extracted main body text of the article, or None if extraction
        failed.
    extraction_status : ExtractionStatus
        The status of the extraction attempt (SUCCESS, FAILED, PAYWALL, TIMEOUT).
    extraction_method : str
        The method used for extraction (e.g., "trafilatura", "fallback").
    error_message : str | None
        Error message if extraction failed, or None if successful.

    Examples
    --------
    >>> from datetime import datetime, timezone
    >>> from news.models import (
    ...     ArticleSource, CollectedArticle, ExtractedArticle,
    ...     ExtractionStatus, SourceType
    ... )
    >>> source = ArticleSource(
    ...     source_type=SourceType.RSS,
    ...     source_name="CNBC Markets",
    ...     category="market",
    ... )
    >>> collected = CollectedArticle(
    ...     url="https://www.cnbc.com/article/123",
    ...     title="Market Update",
    ...     source=source,
    ...     collected_at=datetime.now(tz=timezone.utc),
    ... )
    >>> extracted = ExtractedArticle(
    ...     collected=collected,
    ...     body_text="Full article content here...",
    ...     extraction_status=ExtractionStatus.SUCCESS,
    ...     extraction_method="trafilatura",
    ... )
    >>> extracted.extraction_status
    <ExtractionStatus.SUCCESS: 'success'>
    """

    collected: CollectedArticle = Field(
        ...,
        description="The original collected article that was processed",
    )
    body_text: str | None = Field(
        ...,
        description="The extracted main body text, or None if extraction failed",
    )
    extraction_status: ExtractionStatus = Field(
        ...,
        description="The status of the extraction attempt",
    )
    extraction_method: str = Field(
        ...,
        description="The method used for extraction (e.g., 'trafilatura', 'fallback')",
    )
    error_message: str | None = Field(
        default=None,
        description="Error message if extraction failed, or None if successful",
    )


class PublicationStatus(StrEnum):
    """Status of article publication to GitHub Issues.

    Represents the result status of attempting to publish an article
    as a GitHub Issue. This is used to track whether publication succeeded
    or why it failed.

    Attributes
    ----------
    SUCCESS : str
        Publication completed successfully. The issue_number and issue_url
        fields will contain the created issue information.
    FAILED : str
        Publication failed for an unspecified reason. Check error_message
        for details.
    SKIPPED : str
        Publication was skipped because summarization failed.
        No summary was available to publish.
    DUPLICATE : str
        Publication was skipped because a duplicate issue was detected.
        The article has already been published.

    Examples
    --------
    >>> PublicationStatus.SUCCESS
    <PublicationStatus.SUCCESS: 'success'>
    >>> PublicationStatus.SUCCESS == "success"
    True
    >>> PublicationStatus.DUPLICATE.value
    'duplicate'
    """

    SUCCESS = "success"
    FAILED = "failed"
    SKIPPED = "skipped"
    DUPLICATE = "duplicate"


class SummarizationStatus(StrEnum):
    """Status of AI summarization.

    Represents the result status of attempting to summarize an article
    using an AI model. This is used to track whether summarization succeeded
    or why it failed.

    Attributes
    ----------
    SUCCESS : str
        Summarization completed successfully. The summary field will contain
        the structured summary.
    FAILED : str
        Summarization failed for an unspecified reason. Check error_message
        for details.
    TIMEOUT : str
        The summarization request timed out before completing.
    SKIPPED : str
        Summarization was skipped because body extraction failed.
        No body text was available to summarize.

    Examples
    --------
    >>> SummarizationStatus.SUCCESS
    <SummarizationStatus.SUCCESS: 'success'>
    >>> SummarizationStatus.SUCCESS == "success"
    True
    >>> SummarizationStatus.SKIPPED.value
    'skipped'
    """

    SUCCESS = "success"
    FAILED = "failed"
    TIMEOUT = "timeout"
    SKIPPED = "skipped"


class StructuredSummary(BaseModel):
    """A structured summary of an article in 4 sections.

    Represents the AI-generated summary of an article, organized into
    four distinct sections for consistent formatting and easy consumption.

    Attributes
    ----------
    overview : str
        Overview section describing the main thesis of the article.
    key_points : list[str]
        Key points section listing important facts extracted from the article.
    market_impact : str
        Market impact section describing implications for investors.
    related_info : str | None
        Optional related information section providing background context.

    Examples
    --------
    >>> from news.models import StructuredSummary
    >>> summary = StructuredSummary(
    ...     overview="The Federal Reserve held interest rates steady",
    ...     key_points=["Inflation approaching 2% target", "Rate cut signaled"],
    ...     market_impact="Bond markets may rally",
    ... )
    >>> summary.overview
    'The Federal Reserve held interest rates steady'
    >>> len(summary.key_points)
    2
    """

    overview: str = Field(
        ...,
        description="Overview section describing the main thesis of the article",
    )
    key_points: list[str] = Field(
        ...,
        description="Key points section listing important facts from the article",
    )
    market_impact: str = Field(
        ...,
        description="Market impact section describing implications for investors",
    )
    related_info: str | None = Field(
        default=None,
        description="Optional related information providing background context",
    )


class SummarizedArticle(BaseModel):
    """An article after AI summarization.

    Represents an article after attempting to generate an AI summary
    from its extracted body text. This is the output of a Summarizer component.

    The summarization may succeed (summary contains structured content) or fail
    for various reasons (API error, timeout, or skipped due to extraction failure).

    Attributes
    ----------
    extracted : ExtractedArticle
        The extracted article that was processed for summarization.
    summary : StructuredSummary | None
        The AI-generated structured summary, or None if summarization failed/skipped.
    summarization_status : SummarizationStatus
        The status of the summarization attempt (SUCCESS, FAILED, TIMEOUT, SKIPPED).
    error_message : str | None
        Error message if summarization failed, or None if successful.

    Examples
    --------
    >>> from datetime import datetime, timezone
    >>> from news.models import (
    ...     ArticleSource, CollectedArticle, ExtractedArticle,
    ...     ExtractionStatus, SourceType, StructuredSummary,
    ...     SummarizationStatus, SummarizedArticle
    ... )
    >>> source = ArticleSource(
    ...     source_type=SourceType.RSS,
    ...     source_name="CNBC Markets",
    ...     category="market",
    ... )
    >>> collected = CollectedArticle(
    ...     url="https://www.cnbc.com/article/123",
    ...     title="Market Update",
    ...     source=source,
    ...     collected_at=datetime.now(tz=timezone.utc),
    ... )
    >>> extracted = ExtractedArticle(
    ...     collected=collected,
    ...     body_text="Full article content here...",
    ...     extraction_status=ExtractionStatus.SUCCESS,
    ...     extraction_method="trafilatura",
    ... )
    >>> summary = StructuredSummary(
    ...     overview="Markets rallied today",
    ...     key_points=["S&P 500 up 1%", "Tech leads gains"],
    ...     market_impact="Bullish sentiment continues",
    ... )
    >>> summarized = SummarizedArticle(
    ...     extracted=extracted,
    ...     summary=summary,
    ...     summarization_status=SummarizationStatus.SUCCESS,
    ... )
    >>> summarized.summarization_status
    <SummarizationStatus.SUCCESS: 'success'>
    """

    extracted: ExtractedArticle = Field(
        ...,
        description="The extracted article that was processed for summarization",
    )
    summary: StructuredSummary | None = Field(
        ...,
        description="The AI-generated structured summary, or None if failed/skipped",
    )
    summarization_status: SummarizationStatus = Field(
        ...,
        description="The status of the summarization attempt",
    )
    error_message: str | None = Field(
        default=None,
        description="Error message if summarization failed, or None if successful",
    )


class CategoryGroup(BaseModel):
    """A group of articles belonging to the same category.

    Represents a collection of summarized articles grouped by category,
    used for category-based Issue publishing where one Issue is created
    per category instead of per article.

    Attributes
    ----------
    category : str
        Category key (e.g., "index", "stock", "sector").
    category_label : str
        Human-readable category label in Japanese (e.g., "株価指数", "個別銘柄").
    date : str
        Date string for the group (e.g., "2026-02-09").
    articles : list[SummarizedArticle]
        List of summarized articles belonging to this category.

    Examples
    --------
    >>> from news.models import CategoryGroup
    >>> group = CategoryGroup(
    ...     category="index",
    ...     category_label="株価指数",
    ...     date="2026-02-09",
    ...     articles=[],
    ... )
    >>> group.category
    'index'
    """

    category: str = Field(
        ...,
        description="Category key (e.g., 'index', 'stock', 'sector')",
    )
    category_label: str = Field(
        ...,
        description="Human-readable category label in Japanese (e.g., '株価指数')",
    )
    date: str = Field(
        ...,
        description="Date string for the group (e.g., '2026-02-09')",
    )
    articles: list["SummarizedArticle"] = Field(
        ...,
        description="List of summarized articles belonging to this category",
    )


class CategoryPublishResult(BaseModel):
    """Result of publishing a category group as a GitHub Issue.

    Represents the outcome of attempting to publish a category-based Issue,
    including the Issue number and URL if successful, or error details if failed.

    Attributes
    ----------
    category : str
        Category key (e.g., "index", "stock").
    category_label : str
        Human-readable category label in Japanese (e.g., "株価指数").
    date : str
        Date string for the published group (e.g., "2026-02-09").
    issue_number : int | None
        The GitHub Issue number if publication succeeded, or None if failed.
    issue_url : str | None
        The GitHub Issue URL if publication succeeded, or None if failed.
    article_count : int
        The number of articles included in this category group.
    status : PublicationStatus
        The status of the publication attempt.
    error_message : str | None
        Error message if publication failed, or None if successful.

    Examples
    --------
    >>> from news.models import CategoryPublishResult, PublicationStatus
    >>> result = CategoryPublishResult(
    ...     category="index",
    ...     category_label="株価指数",
    ...     date="2026-02-09",
    ...     issue_number=100,
    ...     issue_url="https://github.com/YH-05/quants/issues/100",
    ...     article_count=5,
    ...     status=PublicationStatus.SUCCESS,
    ... )
    >>> result.status
    <PublicationStatus.SUCCESS: 'success'>
    """

    category: str = Field(
        ...,
        description="Category key (e.g., 'index', 'stock')",
    )
    category_label: str = Field(
        ...,
        description="Human-readable category label in Japanese (e.g., '株価指数')",
    )
    date: str = Field(
        ...,
        description="Date string for the published group (e.g., '2026-02-09')",
    )
    issue_number: int | None = Field(
        ...,
        description="The GitHub Issue number if publication succeeded, or None if failed",
    )
    issue_url: str | None = Field(
        ...,
        description="The GitHub Issue URL if publication succeeded, or None if failed",
    )
    article_count: int = Field(
        ...,
        description="The number of articles included in this category group",
    )
    status: PublicationStatus = Field(
        ...,
        description="The status of the publication attempt",
    )
    error_message: str | None = Field(
        default=None,
        description="Error message if publication failed, or None if successful",
    )


class FailureRecord(BaseModel):
    """A record of a failed processing step in the workflow.

    Represents information about an article that failed to process during
    one of the workflow stages (extraction, summarization, or publication).
    This is used for error tracking and reporting in WorkflowResult.

    Attributes
    ----------
    url : str
        The URL of the article that failed to process.
    title : str
        The title of the article that failed to process.
    stage : str
        The processing stage where the failure occurred.
        Typically one of: "extraction", "summarization", "publication".
    error : str
        A description of the error that caused the failure.

    Examples
    --------
    >>> from news.models import FailureRecord
    >>> failure = FailureRecord(
    ...     url="https://example.com/article",
    ...     title="Failed Article",
    ...     stage="extraction",
    ...     error="Connection timeout after 30 seconds",
    ... )
    >>> failure.stage
    'extraction'
    """

    url: str = Field(
        ...,
        description="The URL of the article that failed to process",
    )
    title: str = Field(
        ...,
        description="The title of the article that failed to process",
    )
    stage: str = Field(
        ...,
        description="The processing stage where the failure occurred (extraction, summarization, publication)",
    )
    error: str = Field(
        ...,
        description="A description of the error that caused the failure",
    )


class PublishedArticle(BaseModel):
    """An article after publication to GitHub Issues.

    Represents an article after attempting to publish it as a GitHub Issue.
    This is the output of a Publisher component.

    The publication may succeed (issue_number and issue_url contain values) or fail
    for various reasons (API error, duplicate detection, summarization failure).

    Attributes
    ----------
    summarized : SummarizedArticle
        The summarized article that was processed for publication.
    issue_number : int | None
        The GitHub Issue number if publication succeeded, or None if failed/skipped.
    issue_url : str | None
        The GitHub Issue URL if publication succeeded, or None if failed/skipped.
    publication_status : PublicationStatus
        The status of the publication attempt (SUCCESS, FAILED, SKIPPED, DUPLICATE).
    error_message : str | None
        Error message if publication failed, or None if successful.

    Examples
    --------
    >>> from datetime import datetime, timezone
    >>> from news.models import (
    ...     ArticleSource, CollectedArticle, ExtractedArticle,
    ...     ExtractionStatus, SourceType, StructuredSummary,
    ...     SummarizationStatus, SummarizedArticle,
    ...     PublicationStatus, PublishedArticle
    ... )
    >>> source = ArticleSource(
    ...     source_type=SourceType.RSS,
    ...     source_name="CNBC Markets",
    ...     category="market",
    ... )
    >>> collected = CollectedArticle(
    ...     url="https://www.cnbc.com/article/123",
    ...     title="Market Update",
    ...     source=source,
    ...     collected_at=datetime.now(tz=timezone.utc),
    ... )
    >>> extracted = ExtractedArticle(
    ...     collected=collected,
    ...     body_text="Full article content here...",
    ...     extraction_status=ExtractionStatus.SUCCESS,
    ...     extraction_method="trafilatura",
    ... )
    >>> summary = StructuredSummary(
    ...     overview="Markets rallied today",
    ...     key_points=["S&P 500 up 1%", "Tech leads gains"],
    ...     market_impact="Bullish sentiment continues",
    ... )
    >>> summarized = SummarizedArticle(
    ...     extracted=extracted,
    ...     summary=summary,
    ...     summarization_status=SummarizationStatus.SUCCESS,
    ... )
    >>> published = PublishedArticle(
    ...     summarized=summarized,
    ...     issue_number=123,
    ...     issue_url="https://github.com/YH-05/quants/issues/123",
    ...     publication_status=PublicationStatus.SUCCESS,
    ... )
    >>> published.publication_status
    <PublicationStatus.SUCCESS: 'success'>
    """

    summarized: SummarizedArticle = Field(
        ...,
        description="The summarized article that was processed for publication",
    )
    issue_number: int | None = Field(
        ...,
        description="The GitHub Issue number if publication succeeded, or None if failed/skipped",
    )
    issue_url: str | None = Field(
        ...,
        description="The GitHub Issue URL if publication succeeded, or None if failed/skipped",
    )
    publication_status: PublicationStatus = Field(
        ...,
        description="The status of the publication attempt",
    )
    error_message: str | None = Field(
        default=None,
        description="Error message if publication failed, or None if successful",
    )


class FeedError(BaseModel):
    """Information about a feed collection error.

    Represents an error that occurred while attempting to collect articles
    from a specific RSS feed. This is used to track which feeds failed and why.

    Attributes
    ----------
    feed_url : str
        The URL of the feed that failed.
    feed_name : str
        The human-readable name of the feed that failed.
    error : str
        A description of the error that occurred.
    error_type : str
        The type of error (e.g., "validation", "fetch", "parse").
    timestamp : datetime
        The time when the error occurred.

    Examples
    --------
    >>> from datetime import datetime, timezone
    >>> from news.models import FeedError
    >>> error = FeedError(
    ...     feed_url="https://example.com/feed.xml",
    ...     feed_name="Example Feed",
    ...     error="Connection timeout",
    ...     error_type="fetch",
    ...     timestamp=datetime.now(tz=timezone.utc),
    ... )
    >>> error.error_type
    'fetch'
    """

    feed_url: str = Field(
        ...,
        description="The URL of the feed that failed",
    )
    feed_name: str = Field(
        ...,
        description="The human-readable name of the feed that failed",
    )
    error: str = Field(
        ...,
        description="A description of the error that occurred",
    )
    error_type: str = Field(
        ...,
        description="The type of error (e.g., 'validation', 'fetch', 'parse')",
    )
    timestamp: datetime = Field(
        ...,
        description="The time when the error occurred",
    )


class StageMetrics(BaseModel):
    """Processing time metrics for a single workflow stage.

    Represents timing information for one stage of the news collection
    workflow pipeline (e.g., collection, extraction, summarization, publishing).

    Attributes
    ----------
    stage : str
        Name of the workflow stage (e.g., "collection", "extraction",
        "summarization", "grouping", "export", "publishing").
    elapsed_seconds : float
        Total elapsed time for this stage in seconds.
    item_count : int
        Number of items processed in this stage.

    Examples
    --------
    >>> from news.models import StageMetrics
    >>> metrics = StageMetrics(
    ...     stage="extraction",
    ...     elapsed_seconds=12.5,
    ...     item_count=20,
    ... )
    >>> metrics.stage
    'extraction'
    >>> metrics.elapsed_seconds
    12.5
    """

    stage: str = Field(
        ...,
        description="Name of the workflow stage (e.g., 'collection', 'extraction')",
    )
    elapsed_seconds: float = Field(
        ...,
        description="Total elapsed time for this stage in seconds",
    )
    item_count: int = Field(
        ...,
        description="Number of items processed in this stage",
    )


class DomainExtractionRate(BaseModel):
    """Extraction success rate for a specific domain.

    Represents how many articles from a particular domain were
    successfully extracted versus failed, providing visibility into
    which sources are reliable for content extraction.

    Attributes
    ----------
    domain : str
        The domain name (e.g., "cnbc.com", "reuters.com").
    total : int
        Total number of extraction attempts for this domain.
    success : int
        Number of successful extractions.
    failed : int
        Number of failed extractions.
    success_rate : float
        Success rate as a percentage (0.0 to 100.0).

    Examples
    --------
    >>> from news.models import DomainExtractionRate
    >>> rate = DomainExtractionRate(
    ...     domain="cnbc.com",
    ...     total=10,
    ...     success=8,
    ...     failed=2,
    ...     success_rate=80.0,
    ... )
    >>> rate.success_rate
    80.0
    """

    domain: str = Field(
        ...,
        description="The domain name (e.g., 'cnbc.com')",
    )
    total: int = Field(
        ...,
        description="Total number of extraction attempts for this domain",
    )
    success: int = Field(
        ...,
        description="Number of successful extractions",
    )
    failed: int = Field(
        ...,
        description="Number of failed extractions",
    )
    success_rate: float = Field(
        ...,
        description="Success rate as a percentage (0.0 to 100.0)",
    )


class WorkflowResult(BaseModel):
    """The result of a complete news collection workflow execution.

    Represents comprehensive statistics and details about a workflow run,
    including counts at each stage, failure records, timing information,
    and the list of successfully published articles.

    Attributes
    ----------
    total_collected : int
        The total number of articles collected from all sources.
    total_extracted : int
        The number of articles with successfully extracted body text.
    total_summarized : int
        The number of articles with successfully generated summaries.
    total_published : int
        The number of articles successfully published as GitHub Issues.
    total_duplicates : int
        The number of articles skipped due to duplicate detection.
    total_early_duplicates : int
        The number of articles excluded by early duplicate check (before extraction).
        Defaults to 0 for backward compatibility.
    extraction_failures : list[FailureRecord]
        Records of articles that failed during the extraction stage.
    summarization_failures : list[FailureRecord]
        Records of articles that failed during the summarization stage.
    publication_failures : list[FailureRecord]
        Records of articles that failed during the publication stage.
    started_at : datetime
        The timestamp when the workflow started.
    finished_at : datetime
        The timestamp when the workflow finished.
    elapsed_seconds : float
        The total elapsed time in seconds.
    published_articles : list[PublishedArticle]
        The list of successfully published articles.

    Examples
    --------
    >>> from datetime import datetime, timezone
    >>> from news.models import WorkflowResult
    >>> result = WorkflowResult(
    ...     total_collected=10,
    ...     total_extracted=8,
    ...     total_summarized=7,
    ...     total_published=5,
    ...     total_duplicates=2,
    ...     extraction_failures=[],
    ...     summarization_failures=[],
    ...     publication_failures=[],
    ...     started_at=datetime(2025, 1, 15, 10, 0, 0, tzinfo=timezone.utc),
    ...     finished_at=datetime(2025, 1, 15, 10, 5, 0, tzinfo=timezone.utc),
    ...     elapsed_seconds=300.0,
    ...     published_articles=[],
    ... )
    >>> result.total_published
    5
    """

    total_collected: int = Field(
        ...,
        description="The total number of articles collected from all sources",
    )
    total_extracted: int = Field(
        ...,
        description="The number of articles with successfully extracted body text",
    )
    total_summarized: int = Field(
        ...,
        description="The number of articles with successfully generated summaries",
    )
    total_published: int = Field(
        ...,
        description="The number of articles successfully published as GitHub Issues",
    )
    total_duplicates: int = Field(
        ...,
        description="The number of articles skipped due to duplicate detection",
    )
    total_early_duplicates: int = Field(
        default=0,
        description="Number of articles excluded by early duplicate check (before extraction)",
    )
    extraction_failures: list[FailureRecord] = Field(
        ...,
        description="Records of articles that failed during the extraction stage",
    )
    summarization_failures: list[FailureRecord] = Field(
        ...,
        description="Records of articles that failed during the summarization stage",
    )
    publication_failures: list[FailureRecord] = Field(
        ...,
        description="Records of articles that failed during the publication stage",
    )
    started_at: datetime = Field(
        ...,
        description="The timestamp when the workflow started",
    )
    finished_at: datetime = Field(
        ...,
        description="The timestamp when the workflow finished",
    )
    elapsed_seconds: float = Field(
        ...,
        description="The total elapsed time in seconds",
    )
    published_articles: list[PublishedArticle] = Field(
        ...,
        description="The list of successfully published articles",
    )
    feed_errors: list[FeedError] = Field(
        default_factory=list,
        description="Records of feeds that failed during collection",
    )
    category_results: list[CategoryPublishResult] = Field(
        default_factory=list,
        description="Results of category-based Issue publishing",
    )
    stage_metrics: list[StageMetrics] = Field(
        default_factory=list,
        description="Processing time metrics for each workflow stage",
    )
    domain_extraction_rates: list[DomainExtractionRate] = Field(
        default_factory=list,
        description="Extraction success rate per domain",
    )


__all__ = [
    "ArticleSource",
    "CategoryGroup",
    "CategoryPublishResult",
    "CollectedArticle",
    "DomainExtractionRate",
    "ExtractedArticle",
    "ExtractionStatus",
    "FailureRecord",
    "FeedError",
    "PublicationStatus",
    "PublishedArticle",
    "SourceType",
    "StageMetrics",
    "StructuredSummary",
    "SummarizationStatus",
    "SummarizedArticle",
    "WorkflowResult",
]
