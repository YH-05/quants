"""Configuration models, errors, and loader for the news package.

This module defines the configuration models, exception classes, and loader
for the news package, including source configurations, sink configurations,
workflow configurations, and general settings.

Configuration Hierarchy
-----------------------
- NewsConfig (root for basic news collection)
  - SourcesConfig
    - YFinanceTickerSourceConfig
    - YFinanceSearchSourceConfig
  - SinksConfig
    - FileSinkConfig
    - GitHubSinkConfig
  - SettingsConfig
    - RetryConfig

- NewsWorkflowConfig (root for news collection workflow)
  - RssConfig
    - UserAgentRotationConfig
  - ExtractionConfig
    - UserAgentRotationConfig
    - PlaywrightFallbackConfig
  - SummarizationConfig
  - GitHubConfig
  - FilteringConfig
  - OutputConfig
  - DomainFilteringConfig

Exception Hierarchy
-------------------
- ConfigError (base, inherits from NewsError)
  - ConfigParseError (parsing errors)
  - ConfigValidationError (validation errors)

Examples
--------
>>> config = NewsConfig()
>>> config.settings.max_articles_per_source
10

>>> config = NewsConfig.model_validate({
...     "sources": {"yfinance_ticker": {"symbols_file": "symbols.yaml"}},
...     "settings": {"max_articles_per_source": 20},
... })

>>> from news.config.models import ConfigLoader
>>> loader = ConfigLoader()
>>> config = loader.load("data/config/news_sources.yaml")

>>> from news.config.models import load_config
>>> workflow_config = load_config("data/config/news-collection-config.yaml")
>>> workflow_config.version
'1.0'
"""

import json
from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel, Field
from pydantic import ValidationError as PydanticValidationError

from utils_core.logging import get_logger

from ..core.errors import NewsError

logger = get_logger(__name__, module="config.models")

# =============================================================================
# Exception Classes
# =============================================================================


class ConfigError(NewsError):
    """Base exception for configuration errors.

    All configuration-related exceptions should inherit from this class.
    This allows catching all config errors with a single except clause.

    Examples
    --------
    >>> try:
    ...     raise ConfigError("Configuration error")
    ... except ConfigError as e:
    ...     print(f"Config error: {e}")
    Config error: Configuration error
    """

    pass


class ConfigParseError(ConfigError):
    """Exception raised when parsing a configuration file fails.

    This exception is used for errors that occur while parsing configuration
    files (YAML, JSON, etc.).

    Parameters
    ----------
    message : str
        Human-readable error message.
    file_path : str
        Path to the configuration file that failed to parse.
    cause : Exception | None, optional
        Original exception that caused this error.

    Attributes
    ----------
    file_path : str
        Path to the configuration file.
    cause : Exception | None
        Original exception that caused this error.

    Examples
    --------
    >>> error = ConfigParseError(
    ...     message="Invalid YAML syntax",
    ...     file_path="/path/to/config.yaml",
    ... )
    >>> error.file_path
    '/path/to/config.yaml'
    """

    def __init__(
        self,
        message: str,
        file_path: str,
        cause: Exception | None = None,
    ) -> None:
        """Initialize ConfigParseError with file information."""
        super().__init__(f"{message} (file: {file_path})")
        self.file_path = file_path
        self.cause = cause

        logger.debug(
            "ConfigParseError created",
            message=message,
            file_path=file_path,
            has_cause=cause is not None,
        )


class ConfigValidationError(ConfigError):
    """Exception raised when configuration validation fails.

    This exception is used for validation errors, such as invalid values,
    missing required fields, or out-of-range parameters.

    Parameters
    ----------
    message : str
        Human-readable error message.
    field : str
        Name of the field that failed validation.
    value : object
        The invalid value that was provided.

    Attributes
    ----------
    field : str
        Name of the field that failed validation.
    value : object
        The invalid value that was provided.

    Examples
    --------
    >>> error = ConfigValidationError(
    ...     message="Value must be positive",
    ...     field="timeout",
    ...     value=-1,
    ... )
    >>> error.field
    'timeout'
    >>> error.value
    -1
    """

    def __init__(
        self,
        message: str,
        field: str,
        value: object,
    ) -> None:
        """Initialize ConfigValidationError with field information."""
        super().__init__(message)
        self.field = field
        self.value = value

        logger.debug(
            "ConfigValidationError created",
            message=message,
            field=field,
            value_type=type(value).__name__,
        )


# =============================================================================
# Basic Configuration Models (NewsConfig)
# =============================================================================


class RetryConfig(BaseModel):
    """Retry configuration for network operations.

    Parameters
    ----------
    max_attempts : int
        Maximum number of retry attempts (default: 3).
    initial_delay : float
        Initial delay in seconds before first retry (default: 1.0).

    Examples
    --------
    >>> config = RetryConfig()
    >>> config.max_attempts
    3
    """

    max_attempts: int = Field(
        default=3,
        ge=1,
        description="Maximum number of retry attempts",
    )
    initial_delay: float = Field(
        default=1.0,
        gt=0,
        description="Initial delay in seconds before first retry",
    )


class YFinanceTickerSourceConfig(BaseModel):
    """Configuration for YFinance Ticker news source.

    Parameters
    ----------
    enabled : bool
        Whether this source is enabled (default: True).
    symbols_file : str
        Path to the symbols YAML file (required).
    categories : list[str]
        List of symbol categories to fetch (default: []).
        Available categories: indices, mag7, sectors, commodities, etc.

    Examples
    --------
    >>> config = YFinanceTickerSourceConfig(
    ...     symbols_file="src/analyze/config/symbols.yaml",
    ...     categories=["indices", "mag7"],
    ... )
    """

    enabled: bool = Field(default=True, description="Whether this source is enabled")
    symbols_file: str = Field(..., description="Path to the symbols YAML file")
    categories: list[str] = Field(
        default_factory=list,
        description="List of symbol categories to fetch",
    )


class YFinanceSearchSourceConfig(BaseModel):
    """Configuration for YFinance Search news source.

    Parameters
    ----------
    enabled : bool
        Whether this source is enabled (default: True).
    keywords_file : str
        Path to the keywords YAML file (required).

    Examples
    --------
    >>> config = YFinanceSearchSourceConfig(
    ...     keywords_file="data/config/news_search_keywords.yaml",
    ... )
    """

    enabled: bool = Field(default=True, description="Whether this source is enabled")
    keywords_file: str = Field(..., description="Path to the keywords YAML file")


class SourcesConfig(BaseModel):
    """Configuration for all news sources.

    Parameters
    ----------
    yfinance_ticker : YFinanceTickerSourceConfig | None
        Configuration for YFinance Ticker source (optional).
    yfinance_search : YFinanceSearchSourceConfig | None
        Configuration for YFinance Search source (optional).

    Examples
    --------
    >>> config = SourcesConfig()
    >>> config.yfinance_ticker is None
    True
    """

    yfinance_ticker: YFinanceTickerSourceConfig | None = Field(
        default=None,
        description="Configuration for YFinance Ticker source",
    )
    yfinance_search: YFinanceSearchSourceConfig | None = Field(
        default=None,
        description="Configuration for YFinance Search source",
    )


class FileSinkConfig(BaseModel):
    """Configuration for file output sink.

    Parameters
    ----------
    enabled : bool
        Whether this sink is enabled (default: True).
    output_dir : str
        Directory path for output files (required).
    filename_pattern : str
        Pattern for output filenames (default: "news_{date}.json").
        The {date} placeholder will be replaced with the current date.

    Examples
    --------
    >>> config = FileSinkConfig(output_dir="data/news")
    >>> config.filename_pattern
    'news_{date}.json'
    """

    enabled: bool = Field(default=True, description="Whether this sink is enabled")
    output_dir: str = Field(..., description="Directory path for output files")
    filename_pattern: str = Field(
        default="news_{date}.json",
        description="Pattern for output filenames",
    )


class GitHubSinkConfig(BaseModel):
    """Configuration for GitHub output sink.

    Parameters
    ----------
    enabled : bool
        Whether this sink is enabled (default: True).
    project_number : int
        GitHub Project number for posting news (required).

    Examples
    --------
    >>> config = GitHubSinkConfig(project_number=24)
    >>> config.enabled
    True
    """

    enabled: bool = Field(default=True, description="Whether this sink is enabled")
    project_number: int = Field(
        ...,
        ge=1,
        description="GitHub Project number for posting news",
    )


class SinksConfig(BaseModel):
    """Configuration for all output sinks.

    Parameters
    ----------
    file : FileSinkConfig | None
        Configuration for file output sink (optional).
    github : GitHubSinkConfig | None
        Configuration for GitHub output sink (optional).

    Examples
    --------
    >>> config = SinksConfig()
    >>> config.file is None
    True
    """

    file: FileSinkConfig | None = Field(
        default=None,
        description="Configuration for file output sink",
    )
    github: GitHubSinkConfig | None = Field(
        default=None,
        description="Configuration for GitHub output sink",
    )


class SettingsConfig(BaseModel):
    """General settings for news collection.

    Parameters
    ----------
    max_articles_per_source : int
        Maximum number of articles to fetch per source (default: 10).
    retry_config : RetryConfig
        Retry configuration for network operations.

    Examples
    --------
    >>> config = SettingsConfig()
    >>> config.max_articles_per_source
    10
    >>> config.retry_config.max_attempts
    3
    """

    max_articles_per_source: int = Field(
        default=10,
        ge=1,
        description="Maximum number of articles to fetch per source",
    )
    retry_config: RetryConfig = Field(
        default_factory=RetryConfig,
        description="Retry configuration for network operations",
    )


class NewsConfig(BaseModel):
    """Root configuration model for news collection.

    This is the main configuration class that contains all settings for
    the news collection pipeline.

    Parameters
    ----------
    sources : SourcesConfig
        Configuration for news sources.
    sinks : SinksConfig
        Configuration for output sinks.
    settings : SettingsConfig
        General settings.

    Examples
    --------
    >>> config = NewsConfig()
    >>> config.settings.max_articles_per_source
    10

    >>> data = {
    ...     "sources": {
    ...         "yfinance_ticker": {
    ...             "symbols_file": "symbols.yaml",
    ...             "categories": ["indices"],
    ...         }
    ...     },
    ...     "settings": {"max_articles_per_source": 5},
    ... }
    >>> config = NewsConfig.model_validate(data)
    >>> config.settings.max_articles_per_source
    5
    """

    sources: SourcesConfig = Field(
        default_factory=SourcesConfig,
        description="Configuration for news sources",
    )
    sinks: SinksConfig = Field(
        default_factory=SinksConfig,
        description="Configuration for output sinks",
    )
    settings: SettingsConfig = Field(
        default_factory=SettingsConfig,
        description="General settings",
    )


# =============================================================================
# Workflow Configuration Models (NewsWorkflowConfig)
# =============================================================================


class RssRetryConfig(BaseModel):
    """Retry configuration for RSS feed collection.

    Parameters
    ----------
    max_attempts : int
        Maximum number of retry attempts (default: 3).
    initial_delay_seconds : float
        Initial delay in seconds before first retry (default: 2.0).
    max_delay_seconds : float
        Maximum delay in seconds between retries (default: 30.0).
    exponential_base : float
        Base for exponential backoff calculation (default: 2.0).
    jitter : bool
        Whether to add random jitter to delays (default: True).

    Examples
    --------
    >>> config = RssRetryConfig()
    >>> config.max_attempts
    3
    >>> config.initial_delay_seconds
    2.0
    """

    max_attempts: int = Field(
        default=3,
        ge=1,
        description="Maximum number of retry attempts",
    )
    initial_delay_seconds: float = Field(
        default=2.0,
        gt=0,
        description="Initial delay in seconds before first retry",
    )
    max_delay_seconds: float = Field(
        default=30.0,
        gt=0,
        description="Maximum delay in seconds between retries",
    )
    exponential_base: float = Field(
        default=2.0,
        gt=1,
        description="Base for exponential backoff calculation",
    )
    jitter: bool = Field(
        default=True,
        description="Whether to add random jitter to delays",
    )


class UserAgentRotationConfig(BaseModel):
    """User-Agent rotation configuration.

    This configuration allows rotating User-Agent headers for HTTP requests,
    which can help avoid rate limiting and blocking by websites.

    Parameters
    ----------
    enabled : bool
        Whether User-Agent rotation is enabled (default: True).
    user_agents : list[str]
        List of User-Agent strings to rotate through.

    Examples
    --------
    >>> config = UserAgentRotationConfig(
    ...     user_agents=["Mozilla/5.0 (Windows)", "Mozilla/5.0 (Mac)"]
    ... )
    >>> ua = config.get_random_user_agent()
    >>> ua in config.user_agents
    True

    >>> disabled_config = UserAgentRotationConfig(enabled=False)
    >>> disabled_config.get_random_user_agent() is None
    True
    """

    enabled: bool = Field(
        default=True,
        description="Whether User-Agent rotation is enabled",
    )
    user_agents: list[str] = Field(
        default_factory=list,
        description="List of User-Agent strings to rotate through",
    )

    def get_random_user_agent(self) -> str | None:
        """Get a random User-Agent from the configured list.

        Returns
        -------
        str | None
            A randomly selected User-Agent string, or None if rotation is
            disabled or the list is empty.

        Examples
        --------
        >>> config = UserAgentRotationConfig(user_agents=["UA1", "UA2"])
        >>> ua = config.get_random_user_agent()
        >>> ua in ["UA1", "UA2"]
        True
        """
        if not self.enabled or not self.user_agents:
            return None

        import random

        return random.choice(self.user_agents)


class RssConfig(BaseModel):
    """RSS feed configuration.

    Parameters
    ----------
    presets_file : str
        Path to the RSS presets JSON file containing feed definitions.
    retry : RssRetryConfig
        Retry configuration for feed collection.
    user_agent_rotation : UserAgentRotationConfig
        User-Agent rotation configuration for RSS feed fetching.

    Examples
    --------
    >>> config = RssConfig(presets_file="data/config/rss-presets.json")
    >>> config.presets_file
    'data/config/rss-presets.json'
    >>> config.retry.max_attempts
    3
    >>> config.user_agent_rotation.enabled
    True
    """

    presets_file: str = Field(
        ...,
        description="Path to the RSS presets JSON file",
    )
    retry: RssRetryConfig = Field(
        default_factory=RssRetryConfig,
        description="Retry configuration for feed collection",
    )
    user_agent_rotation: UserAgentRotationConfig = Field(
        default_factory=UserAgentRotationConfig,
        description="User-Agent rotation configuration for RSS feed fetching",
    )


class PlaywrightFallbackConfig(BaseModel):
    """Playwright fallback configuration for JS-rendered page extraction.

    This configuration controls the Playwright-based fallback extractor
    used when trafilatura fails to extract content from JavaScript-rendered pages.

    Parameters
    ----------
    enabled : bool
        Whether Playwright fallback is enabled (default: True).
    browser : str
        Browser to use: "chromium", "firefox", or "webkit" (default: "chromium").
    headless : bool
        Whether to run browser in headless mode (default: True).
    timeout_seconds : int
        Page load timeout in seconds (default: 30).

    Examples
    --------
    >>> config = PlaywrightFallbackConfig()
    >>> config.enabled
    True
    >>> config.browser
    'chromium'
    >>> config.headless
    True

    >>> config = PlaywrightFallbackConfig(browser="firefox", timeout_seconds=60)
    >>> config.browser
    'firefox'
    >>> config.timeout_seconds
    60
    """

    enabled: bool = Field(
        default=True,
        description="Whether Playwright fallback is enabled",
    )
    browser: str = Field(
        default="chromium",
        description='Browser to use: "chromium", "firefox", or "webkit"',
    )
    headless: bool = Field(
        default=True,
        description="Whether to run browser in headless mode",
    )
    timeout_seconds: int = Field(
        default=30,
        ge=1,
        description="Page load timeout in seconds",
    )


class ExtractionConfig(BaseModel):
    """Article body extraction configuration.

    Parameters
    ----------
    concurrency : int
        Number of concurrent extraction tasks (default: 5).
    timeout_seconds : int
        Timeout for each extraction request in seconds (default: 30).
    min_body_length : int
        Minimum body text length to consider extraction successful (default: 200).
    max_retries : int
        Maximum retry attempts for failed extractions (default: 3).
    user_agent_rotation : UserAgentRotationConfig
        User-Agent rotation configuration.
    playwright_fallback : PlaywrightFallbackConfig
        Playwright fallback configuration for JS-rendered pages.

    Examples
    --------
    >>> config = ExtractionConfig()
    >>> config.concurrency
    5
    >>> config.timeout_seconds
    30
    >>> config.user_agent_rotation.enabled
    True
    >>> config.playwright_fallback.enabled
    True
    """

    concurrency: int = Field(
        default=5,
        ge=1,
        description="Number of concurrent extraction tasks",
    )
    timeout_seconds: int = Field(
        default=30,
        ge=1,
        description="Timeout for each extraction request in seconds",
    )
    min_body_length: int = Field(
        default=200,
        ge=0,
        description="Minimum body text length for successful extraction",
    )
    max_retries: int = Field(
        default=3,
        ge=0,
        description="Maximum retry attempts for failed extractions",
    )
    user_agent_rotation: UserAgentRotationConfig = Field(
        default_factory=UserAgentRotationConfig,
        description="User-Agent rotation configuration",
    )
    playwright_fallback: PlaywrightFallbackConfig = Field(
        default_factory=PlaywrightFallbackConfig,
        description="Playwright fallback configuration for JS-rendered pages",
    )


class SummarizationConfig(BaseModel):
    """AI summarization configuration.

    Parameters
    ----------
    concurrency : int
        Number of concurrent summarization tasks (default: 3).
    timeout_seconds : int
        Timeout for each summarization request in seconds (default: 60).
    max_retries : int
        Maximum retry attempts for failed summarizations (default: 3).
    prompt_template : str
        Prompt template for the AI summarization.

    Examples
    --------
    >>> config = SummarizationConfig(prompt_template="Summarize: {body}")
    >>> config.concurrency
    3
    >>> config.timeout_seconds
    60
    """

    concurrency: int = Field(
        default=3,
        ge=1,
        description="Number of concurrent summarization tasks",
    )
    timeout_seconds: int = Field(
        default=60,
        ge=1,
        description="Timeout for each summarization request in seconds",
    )
    max_retries: int = Field(
        default=3,
        ge=0,
        description="Maximum retry attempts for failed summarizations",
    )
    prompt_template: str = Field(
        ...,
        description="Prompt template for AI summarization",
    )


class GitHubConfig(BaseModel):
    """GitHub Project and Issue configuration.

    Parameters
    ----------
    project_number : int
        GitHub Project number for posting news.
    project_id : str
        GitHub Project ID (PVT_...).
    status_field_id : str
        Status field ID in the GitHub Project.
    published_date_field_id : str
        Published date field ID in the GitHub Project.
    repository : str
        GitHub repository in "owner/repo" format.
    duplicate_check_days : int
        Number of days to check for duplicate articles (default: 7).
    dry_run : bool
        If True, skip actual Issue creation (default: False).

    Examples
    --------
    >>> config = GitHubConfig(
    ...     project_number=15,
    ...     project_id="PVT_kwHOBoK6AM4BMpw_",
    ...     status_field_id="PVTSSF_lAHOBoK6AM4BMpw_zg739ZE",
    ...     published_date_field_id="PVTF_lAHOBoK6AM4BMpw_zg8BzrI",
    ...     repository="YH-05/quants",
    ... )
    >>> config.project_number
    15
    >>> config.dry_run
    False
    """

    project_number: int = Field(
        ...,
        ge=1,
        description="GitHub Project number for posting news",
    )
    project_id: str = Field(
        ...,
        description="GitHub Project ID (PVT_...)",
    )
    status_field_id: str = Field(
        ...,
        description="Status field ID in the GitHub Project",
    )
    published_date_field_id: str = Field(
        ...,
        description="Published date field ID in the GitHub Project",
    )
    repository: str = Field(
        ...,
        description='GitHub repository in "owner/repo" format',
    )
    duplicate_check_days: int = Field(
        default=7,
        ge=1,
        description="Number of days to check for duplicate articles",
    )
    dry_run: bool = Field(
        default=False,
        description="If True, skip actual Issue creation",
    )


class FilteringConfig(BaseModel):
    """Article filtering configuration.

    Parameters
    ----------
    max_age_hours : int
        Maximum age of articles to collect in hours (default: 168 = 7 days).

    Examples
    --------
    >>> config = FilteringConfig()
    >>> config.max_age_hours
    168
    """

    max_age_hours: int = Field(
        default=168,  # 7 days
        ge=1,
        description="Maximum age of articles to collect in hours",
    )


class OutputConfig(BaseModel):
    """Output file configuration.

    Parameters
    ----------
    result_dir : str
        Directory path for output result files.

    Examples
    --------
    >>> config = OutputConfig(result_dir="data/exports/news-workflow")
    >>> config.result_dir
    'data/exports/news-workflow'
    """

    result_dir: str = Field(
        ...,
        description="Directory path for output result files",
    )


class DomainFilteringConfig(BaseModel):
    """Domain filtering configuration for blocking specific news sources.

    This configuration allows blocking articles from specific domains,
    including subdomains.

    Parameters
    ----------
    enabled : bool
        Whether domain filtering is enabled (default: True).
    log_blocked : bool
        Whether to log blocked domains (default: True).
    blocked_domains : list[str]
        List of domains to block. Subdomains are also blocked.
        For example, "seekingalpha.com" blocks both "seekingalpha.com"
        and "www.seekingalpha.com".

    Examples
    --------
    >>> config = DomainFilteringConfig(
    ...     blocked_domains=["seekingalpha.com", "example.com"]
    ... )
    >>> config.is_blocked("https://seekingalpha.com/article/123")
    True
    >>> config.is_blocked("https://www.seekingalpha.com/article/123")
    True
    >>> config.is_blocked("https://cnbc.com/article/123")
    False
    """

    enabled: bool = Field(
        default=True,
        description="Whether domain filtering is enabled",
    )
    log_blocked: bool = Field(
        default=True,
        description="Whether to log blocked domains",
    )
    blocked_domains: list[str] = Field(
        default_factory=list,
        description="List of domains to block (subdomains also blocked)",
    )

    def is_blocked(self, url: str) -> bool:
        """Check if a URL is blocked based on domain filtering rules.

        Parameters
        ----------
        url : str
            The URL to check.

        Returns
        -------
        bool
            True if the URL is blocked, False otherwise.

        Examples
        --------
        >>> config = DomainFilteringConfig(
        ...     blocked_domains=["seekingalpha.com"]
        ... )
        >>> config.is_blocked("https://seekingalpha.com/article/123")
        True
        >>> config.is_blocked("https://www.seekingalpha.com/article/123")
        True
        >>> config.is_blocked("https://cnbc.com/article/123")
        False
        """
        if not self.enabled:
            return False

        from urllib.parse import urlparse

        parsed = urlparse(url)
        domain = parsed.netloc.lower()

        # Check both exact match and subdomain match
        for blocked in self.blocked_domains:
            blocked_lower = blocked.lower()
            if domain == blocked_lower or domain.endswith(f".{blocked_lower}"):
                return True

        return False


class PublishingConfig(BaseModel):
    """Publishing format configuration for the news workflow.

    Controls how articles are published to GitHub Issues, including
    the publishing format (per-category vs per-article) and export settings.

    Parameters
    ----------
    format : str
        Publishing format: "per_category" or "per_article" (default: "per_category").
    export_markdown : bool
        Whether to export markdown files for each category (default: True).
    export_dir : str
        Directory for exported markdown files (default: "data/exports/news-workflow").

    Examples
    --------
    >>> config = PublishingConfig()
    >>> config.format
    'per_category'
    >>> config.export_markdown
    True
    """

    format: str = Field(
        default="per_category",
        description='Publishing format: "per_category" or "per_article"',
    )
    export_markdown: bool = Field(
        default=True,
        description="Whether to export markdown files for each category",
    )
    export_dir: str = Field(
        default="data/exports/news-workflow",
        description="Directory for exported markdown files",
    )


class CategoryLabelsConfig(BaseModel):
    """Category label mapping configuration.

    Maps category keys to human-readable Japanese labels used in
    GitHub Issue titles and content.

    Parameters
    ----------
    index : str
        Label for index category (default: "株価指数").
    stock : str
        Label for stock category (default: "個別銘柄").
    sector : str
        Label for sector category (default: "セクター").
    macro : str
        Label for macro category (default: "マクロ経済").
    ai : str
        Label for AI category (default: "AI関連").
    finance : str
        Label for finance category (default: "金融").

    Examples
    --------
    >>> config = CategoryLabelsConfig()
    >>> config.index
    '株価指数'
    >>> config.get_label("stock")
    '個別銘柄'
    >>> config.get_label("unknown")
    'unknown'
    """

    index: str = Field(
        default="株価指数",
        description="Label for index category",
    )
    stock: str = Field(
        default="個別銘柄",
        description="Label for stock category",
    )
    sector: str = Field(
        default="セクター",
        description="Label for sector category",
    )
    macro: str = Field(
        default="マクロ経済",
        description="Label for macro category",
    )
    ai: str = Field(
        default="AI関連",
        description="Label for AI category",
    )
    finance: str = Field(
        default="金融",
        description="Label for finance category",
    )

    def get_label(self, category: str) -> str:
        """Get the human-readable label for a category key.

        Parameters
        ----------
        category : str
            The category key to look up (e.g., "index", "stock").

        Returns
        -------
        str
            The human-readable label if the category is known,
            otherwise returns the category key as-is.

        Examples
        --------
        >>> config = CategoryLabelsConfig()
        >>> config.get_label("index")
        '株価指数'
        >>> config.get_label("unknown")
        'unknown'
        """
        return getattr(self, category, category)


class NewsWorkflowConfig(BaseModel):
    """Root configuration model for news collection workflow.

    This is the main configuration class that contains all settings for
    the news collection workflow pipeline.

    Parameters
    ----------
    version : str
        Configuration version string.
    status_mapping : dict[str, str]
        Mapping from article category to GitHub Status name.
    github_status_ids : dict[str, str]
        Mapping from GitHub Status name to Status ID.
    rss : RssConfig
        RSS feed configuration.
    extraction : ExtractionConfig
        Article body extraction configuration.
    summarization : SummarizationConfig
        AI summarization configuration.
    github : GitHubConfig
        GitHub Project/Issue configuration.
    filtering : FilteringConfig
        Article filtering configuration.
    output : OutputConfig
        Output file configuration.
    domain_filtering : DomainFilteringConfig
        Domain filtering configuration for blocking specific sources.

    Examples
    --------
    >>> config = NewsWorkflowConfig(
    ...     version="1.0",
    ...     status_mapping={"tech": "ai"},
    ...     github_status_ids={"ai": "6fbb43d0"},
    ...     rss=RssConfig(presets_file="rss-presets.json"),
    ...     extraction=ExtractionConfig(),
    ...     summarization=SummarizationConfig(prompt_template="test"),
    ...     github=GitHubConfig(
    ...         project_number=15,
    ...         project_id="PVT_test",
    ...         status_field_id="PVTSSF_test",
    ...         published_date_field_id="PVTF_test",
    ...         repository="owner/repo",
    ...     ),
    ...     filtering=FilteringConfig(),
    ...     output=OutputConfig(result_dir="data/exports"),
    ... )
    >>> config.version
    '1.0'

    Notes
    -----
    To resolve a category to a GitHub Status ID:

    1. Get the status name from status_mapping:
       status_name = config.status_mapping.get("tech")  # "ai"

    2. Get the status ID from github_status_ids:
       status_id = config.github_status_ids.get(status_name)  # "6fbb43d0"
    """

    version: str = Field(
        ...,
        description="Configuration version string",
    )
    status_mapping: dict[str, str] = Field(
        ...,
        description="Mapping from article category to GitHub Status name",
    )
    github_status_ids: dict[str, str] = Field(
        ...,
        description="Mapping from GitHub Status name to Status ID",
    )
    rss: RssConfig = Field(
        ...,
        description="RSS feed configuration",
    )
    extraction: ExtractionConfig = Field(
        default_factory=ExtractionConfig,
        description="Article body extraction configuration",
    )
    summarization: SummarizationConfig = Field(
        ...,
        description="AI summarization configuration",
    )
    github: GitHubConfig = Field(
        ...,
        description="GitHub Project/Issue configuration",
    )
    filtering: FilteringConfig = Field(
        default_factory=FilteringConfig,
        description="Article filtering configuration",
    )
    output: OutputConfig = Field(
        ...,
        description="Output file configuration",
    )
    domain_filtering: DomainFilteringConfig = Field(
        default_factory=DomainFilteringConfig,
        description="Domain filtering configuration for blocking specific sources",
    )
    publishing: PublishingConfig = Field(
        default_factory=PublishingConfig,
        description="Publishing format configuration",
    )
    category_labels: CategoryLabelsConfig = Field(
        default_factory=CategoryLabelsConfig,
        description="Category label mapping configuration",
    )


# =============================================================================
# Configuration Loader
# =============================================================================

# Default configuration file path
DEFAULT_CONFIG_PATH = Path("data/config/news_sources.yaml")


class ConfigLoader:
    """Configuration loader for news package.

    Loads configuration from YAML or JSON files and provides access to
    symbol definitions from symbols.yaml files.

    Examples
    --------
    >>> loader = ConfigLoader()
    >>> config = loader.load("config.yaml")
    >>> config.settings.max_articles_per_source
    10

    >>> symbols = loader.load_symbols("symbols.yaml", categories=["mag7"])
    >>> len(symbols["mag7"])
    7
    """

    def load(self, file_path: str | Path) -> NewsConfig:
        """Load configuration from a YAML or JSON file.

        Parameters
        ----------
        file_path : str | Path
            Path to the configuration file. Supports .yaml, .yml, and .json
            extensions.

        Returns
        -------
        NewsConfig
            Parsed and validated configuration object.

        Raises
        ------
        FileNotFoundError
            If the configuration file does not exist.
        ConfigParseError
            If the file format is unsupported or parsing fails.

        Examples
        --------
        >>> loader = ConfigLoader()
        >>> config = loader.load("config.yaml")
        >>> config.settings.max_articles_per_source
        10
        """
        path = Path(file_path)

        if not path.exists():
            logger.error("Configuration file not found", file_path=str(path))
            raise FileNotFoundError(f"Configuration file not found: {path}")

        logger.debug("Loading configuration", file_path=str(path))

        data = self._read_file(path)

        try:
            config = NewsConfig.model_validate(data or {})
            logger.info(
                "Configuration loaded successfully",
                file_path=str(path),
                sources_configured=config.sources.yfinance_ticker is not None
                or config.sources.yfinance_search is not None,
            )
            return config
        except PydanticValidationError as e:
            logger.error(
                "Configuration validation failed",
                file_path=str(path),
                error=str(e),
            )
            raise ConfigParseError(
                message=f"Invalid configuration: {e}",
                file_path=str(path),
                cause=e,
            ) from e

    def load_from_default(self) -> NewsConfig:
        """Load configuration from the default path.

        If the default configuration file does not exist, returns a
        default configuration object.

        Returns
        -------
        NewsConfig
            Parsed configuration or default configuration.

        Examples
        --------
        >>> loader = ConfigLoader()
        >>> config = loader.load_from_default()
        >>> config.settings.max_articles_per_source
        10
        """
        if DEFAULT_CONFIG_PATH.exists():
            logger.debug(
                "Loading from default path",
                file_path=str(DEFAULT_CONFIG_PATH),
            )
            return self.load(DEFAULT_CONFIG_PATH)

        logger.info(
            "Default configuration file not found, using defaults",
            default_path=str(DEFAULT_CONFIG_PATH),
        )
        return NewsConfig()

    def load_symbols(
        self,
        file_path: str | Path,
        categories: list[str] | None = None,
    ) -> dict[str, Any]:
        """Load symbol definitions from a YAML file.

        Parameters
        ----------
        file_path : str | Path
            Path to the symbols YAML file.
        categories : list[str] | None, optional
            List of categories to load. If None, loads all categories.

        Returns
        -------
        dict[str, Any]
            Dictionary of symbol definitions by category.

        Raises
        ------
        FileNotFoundError
            If the symbols file does not exist.
        ConfigParseError
            If parsing fails.

        Examples
        --------
        >>> loader = ConfigLoader()
        >>> symbols = loader.load_symbols("symbols.yaml")
        >>> "mag7" in symbols
        True

        >>> symbols = loader.load_symbols("symbols.yaml", categories=["mag7"])
        >>> "indices" in symbols
        False
        """
        path = Path(file_path)

        if not path.exists():
            logger.error("Symbols file not found", file_path=str(path))
            raise FileNotFoundError(f"Symbols file not found: {path}")

        logger.debug(
            "Loading symbols",
            file_path=str(path),
            categories=categories,
        )

        data = self._read_yaml(path)

        if data is None:
            return {}

        if categories is None:
            return data

        # Filter by specified categories
        result = {}
        for category in categories:
            if category in data:
                result[category] = data[category]

        logger.debug(
            "Symbols loaded",
            file_path=str(path),
            loaded_categories=list(result.keys()),
        )
        return result

    def get_ticker_symbols(
        self,
        file_path: str | Path,
        categories: list[str] | None = None,
    ) -> list[str]:
        """Get a flat list of ticker symbols from a symbols file.

        Parameters
        ----------
        file_path : str | Path
            Path to the symbols YAML file.
        categories : list[str] | None, optional
            List of categories to include. If None, includes all categories.

        Returns
        -------
        list[str]
            Flat list of ticker symbols.

        Examples
        --------
        >>> loader = ConfigLoader()
        >>> tickers = loader.get_ticker_symbols("symbols.yaml", categories=["mag7"])
        >>> "AAPL" in tickers
        True
        """
        symbols_data = self.load_symbols(file_path, categories)
        tickers: list[str] = []

        for category_data in symbols_data.values():
            tickers.extend(self._extract_symbols(category_data))

        logger.debug(
            "Extracted ticker symbols",
            count=len(tickers),
            categories=categories,
        )
        return tickers

    def _read_file(self, path: Path) -> dict[str, Any] | None:
        """Read and parse a configuration file.

        Parameters
        ----------
        path : Path
            Path to the file.

        Returns
        -------
        dict[str, Any] | None
            Parsed data or None if empty.

        Raises
        ------
        ConfigParseError
            If the file format is unsupported or parsing fails.
        """
        suffix = path.suffix.lower()

        if suffix in {".yaml", ".yml"}:
            return self._read_yaml(path)
        elif suffix == ".json":
            return self._read_json(path)
        else:
            raise ConfigParseError(
                message=f"Unsupported file format: {suffix}",
                file_path=str(path),
            )

    def _read_yaml(self, path: Path) -> dict[str, Any] | None:
        """Read and parse a YAML file.

        Parameters
        ----------
        path : Path
            Path to the YAML file.

        Returns
        -------
        dict[str, Any] | None
            Parsed YAML data or None if empty.

        Raises
        ------
        ConfigParseError
            If YAML parsing fails.
        """
        try:
            content = path.read_text(encoding="utf-8")
            data = yaml.safe_load(content)

            if data is None:
                return None

            if not isinstance(data, dict):
                raise ConfigParseError(
                    message="YAML root must be a mapping",
                    file_path=str(path),
                )

            return data
        except yaml.YAMLError as e:
            raise ConfigParseError(
                message=f"Invalid YAML: {e}",
                file_path=str(path),
                cause=e,
            ) from e

    def _read_json(self, path: Path) -> dict[str, Any] | None:
        """Read and parse a JSON file.

        Parameters
        ----------
        path : Path
            Path to the JSON file.

        Returns
        -------
        dict[str, Any] | None
            Parsed JSON data or None if empty.

        Raises
        ------
        ConfigParseError
            If JSON parsing fails.
        """
        try:
            content = path.read_text(encoding="utf-8")

            if not content.strip():
                return None

            data = json.loads(content)

            if not isinstance(data, dict):
                raise ConfigParseError(
                    message="JSON root must be an object",
                    file_path=str(path),
                )

            return data
        except json.JSONDecodeError as e:
            raise ConfigParseError(
                message=f"Invalid JSON: {e}",
                file_path=str(path),
                cause=e,
            ) from e

    def _extract_symbols(self, data: Any) -> list[str]:
        """Extract symbol strings from nested data structures.

        Handles various formats:
        - List of dicts with 'symbol' key: [{"symbol": "AAPL", "name": "Apple"}]
        - Dict with nested lists: {"us": [{"symbol": "^GSPC"}], "global": [...]}

        Parameters
        ----------
        data : Any
            Symbol data structure.

        Returns
        -------
        list[str]
            List of extracted symbol strings.
        """
        symbols: list[str] = []

        if isinstance(data, list):
            for item in data:
                if isinstance(item, dict) and "symbol" in item:
                    symbols.append(item["symbol"])
        elif isinstance(data, dict):
            for value in data.values():
                symbols.extend(self._extract_symbols(value))

        return symbols


def load_config(path: Path | str) -> NewsWorkflowConfig:
    """Load workflow configuration from a YAML file.

    Parameters
    ----------
    path : Path | str
        Path to the YAML configuration file.

    Returns
    -------
    NewsWorkflowConfig
        Parsed and validated workflow configuration object.

    Raises
    ------
    FileNotFoundError
        If the configuration file does not exist.
    yaml.YAMLError
        If YAML parsing fails.
    pydantic.ValidationError
        If configuration validation fails.

    Examples
    --------
    >>> config = load_config("data/config/news-collection-config.yaml")
    >>> config.version
    '1.0'
    >>> config.extraction.concurrency
    5
    """
    file_path = Path(path)

    if not file_path.exists():
        logger.error("Configuration file not found", file_path=str(file_path))
        raise FileNotFoundError(f"Configuration file not found: {file_path}")

    logger.debug("Loading workflow configuration", file_path=str(file_path))

    content = file_path.read_text(encoding="utf-8")
    data = yaml.safe_load(content)

    # Convert top-level blocked_domains to domain_filtering config
    if "blocked_domains" in data:
        blocked_domains = data.pop("blocked_domains")
        existing_domain_filtering = data.get("domain_filtering", {})
        data["domain_filtering"] = {
            "blocked_domains": blocked_domains,
            **existing_domain_filtering,
        }

    config = NewsWorkflowConfig.model_validate(data)

    logger.info(
        "Workflow configuration loaded successfully",
        file_path=str(file_path),
        version=config.version,
    )

    return config


# Export all public symbols (sorted alphabetically per RUF022)
__all__ = [
    "DEFAULT_CONFIG_PATH",
    "CategoryLabelsConfig",
    "ConfigError",
    "ConfigLoader",
    "ConfigParseError",
    "ConfigValidationError",
    "DomainFilteringConfig",
    "ExtractionConfig",
    "FileSinkConfig",
    "FilteringConfig",
    "GitHubConfig",
    "GitHubSinkConfig",
    "NewsConfig",
    "NewsWorkflowConfig",
    "OutputConfig",
    "PlaywrightFallbackConfig",
    "PublishingConfig",
    "RetryConfig",
    "RssConfig",
    "RssRetryConfig",
    "SettingsConfig",
    "SinksConfig",
    "SourcesConfig",
    "SummarizationConfig",
    "UserAgentRotationConfig",
    "YFinanceSearchSourceConfig",
    "YFinanceTickerSourceConfig",
    "load_config",
]
