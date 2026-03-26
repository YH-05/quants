"""yfinance macro economics news source module.

This module provides the MacroNewsSource class for fetching macro economics
news using yfinance Search API with keyword-based queries.

Classes
-------
MacroNewsSource
    Fetches macro economics news using keyword search queries
    (e.g., "Federal Reserve", "GDP growth", "inflation CPI").

Examples
--------
>>> from news.sources.yfinance.macro import MacroNewsSource
>>> source = MacroNewsSource(keywords_file="data/config/news_search_keywords.yaml")
>>> result = source.fetch("Federal Reserve", count=10)
>>> result.article_count
10
"""

from pathlib import Path
from typing import Any

import yfinance as yf

from database.db.connection import get_data_dir
from utils_core.logging import get_logger

from ...config.models import ConfigLoader
from ...core.article import ArticleSource
from ...core.errors import SourceError
from ...core.result import FetchResult, RetryConfig
from .base import (
    DEFAULT_YFINANCE_RETRY_CONFIG,
    fetch_all_with_polite_delay,
    fetch_with_retry,
    search_news_to_article,
    validate_query,
)

logger = get_logger(__name__, module="yfinance.macro")

# Default keywords file path
DEFAULT_KEYWORDS_FILE = get_data_dir() / "config" / "news_search_keywords.yaml"

# Default retry configuration (shared across all yfinance sources)
DEFAULT_RETRY_CONFIG = DEFAULT_YFINANCE_RETRY_CONFIG


class MacroNewsSource:
    """News source for macro economics using yfinance Search API.

    This class implements the SourceProtocol interface for fetching macro
    economics news using keyword-based search queries. Keywords are loaded
    from a configuration file organized by category (monetary_policy,
    economic_indicators, trade, global, market_sentiment).

    Parameters
    ----------
    keywords_file : str | Path
        Path to the keywords YAML file containing search keywords.
    categories : list[str] | None, optional
        List of keyword categories to include
        (e.g., ["monetary_policy", "trade"]).
        If None, includes all categories.
    retry_config : RetryConfig | None, optional
        Retry configuration for network operations.
        If None, uses default configuration.

    Attributes
    ----------
    source_name : str
        Name of this source ("yfinance_search_macro").
    source_type : ArticleSource
        Type of this source (YFINANCE_SEARCH).

    Examples
    --------
    >>> source = MacroNewsSource(
    ...     keywords_file="data/config/news_search_keywords.yaml",
    ...     categories=["monetary_policy"],
    ... )
    >>> result = source.fetch("Federal Reserve", count=5)
    >>> result.success
    True

    >>> results = source.fetch_all(["Federal Reserve", "GDP growth"], count=10)
    >>> len(results)
    2
    """

    def __init__(
        self,
        keywords_file: str | Path,
        categories: list[str] | None = None,
        retry_config: RetryConfig | None = None,
    ) -> None:
        """Initialize MacroNewsSource.

        Parameters
        ----------
        keywords_file : str | Path
            Path to the keywords YAML file.
        categories : list[str] | None, optional
            List of categories to include. If None, includes all.
        retry_config : RetryConfig | None, optional
            Retry configuration. If None, uses defaults.

        Raises
        ------
        FileNotFoundError
            If the keywords file does not exist.
        """
        self._keywords_file = Path(keywords_file)
        self._categories = categories
        self._retry_config = retry_config or DEFAULT_RETRY_CONFIG

        logger.info(
            "Initializing MacroNewsSource",
            keywords_file=str(self._keywords_file),
            categories=self._categories,
        )

        # Validate keywords file exists
        if not self._keywords_file.exists():
            logger.error("Keywords file not found", file_path=str(self._keywords_file))
            raise FileNotFoundError(f"Keywords file not found: {self._keywords_file}")

        # Load keywords
        self._loader = ConfigLoader()
        self._keywords_data = self._loader.load_symbols(self._keywords_file)
        self._keywords: list[str] = []
        self._load_keywords()

        logger.info(
            "MacroNewsSource initialized",
            keyword_count=len(self._keywords),
        )

    @property
    def source_name(self) -> str:
        """Return the name of this source.

        Returns
        -------
        str
            Source name ("yfinance_search_macro").
        """
        return "yfinance_search_macro"

    @property
    def source_type(self) -> ArticleSource:
        """Return the type of this source.

        Returns
        -------
        ArticleSource
            Source type (YFINANCE_SEARCH).
        """
        return ArticleSource.YFINANCE_SEARCH

    def get_keywords(self) -> list[str]:
        """Get the list of macro economics search keywords.

        Returns the list of search keywords loaded from the configuration
        file, optionally filtered by categories.

        Returns
        -------
        list[str]
            List of search keywords for macro economics news.

        Examples
        --------
        >>> source = MacroNewsSource("keywords.yaml")
        >>> keywords = source.get_keywords()
        >>> "Federal Reserve" in keywords
        True
        >>> "GDP growth" in keywords
        True
        """
        return self._keywords.copy()

    def fetch(self, identifier: str, count: int = 10) -> FetchResult:
        """Fetch news for a single search query.

        Parameters
        ----------
        identifier : str
            Search query for macro economics news
            (e.g., "Federal Reserve", "GDP growth").
        count : int, optional
            Maximum number of articles to fetch (default: 10).

        Returns
        -------
        FetchResult
            Result containing fetched articles and status.
            On success: success=True, articles contains fetched items.
            On failure: success=False, error contains error details.

        Examples
        --------
        >>> source = MacroNewsSource("keywords.yaml")
        >>> result = source.fetch("Federal Reserve", count=5)
        >>> result.success
        True
        """
        logger.debug(
            "Fetching macro economics news",
            query=identifier,
            count=count,
        )

        try:
            # Validate query
            validated_query = validate_query(identifier)

            # Define fetch function for retry logic
            def do_fetch() -> list[dict[str, Any]]:
                search = yf.Search(validated_query, news_count=count)
                return search.news if search.news else []

            # Execute with retry
            raw_news = fetch_with_retry(do_fetch, self._retry_config)

            # Convert to Article models
            articles = []
            for raw_item in raw_news:
                try:
                    article = search_news_to_article(raw_item, validated_query)
                    articles.append(article)
                except Exception as e:
                    logger.warning(
                        "Failed to convert news item",
                        query=validated_query,
                        error=str(e),
                    )
                    continue

            logger.info(
                "Successfully fetched macro economics news",
                query=validated_query,
                article_count=len(articles),
            )

            return FetchResult(
                articles=articles,
                success=True,
                query=validated_query,
            )

        except SourceError as e:
            logger.error(
                "Source error fetching macro economics news",
                query=identifier,
                error=str(e),
            )
            return FetchResult(
                articles=[],
                success=False,
                query=identifier,
                error=e,
            )
        except Exception as e:
            logger.error(
                "Unexpected error fetching macro economics news",
                query=identifier,
                error=str(e),
                error_type=type(e).__name__,
            )
            return FetchResult(
                articles=[],
                success=False,
                query=identifier,
                error=SourceError(
                    message=str(e),
                    source=self.source_name,
                    cause=e,
                ),
            )

    def fetch_all(
        self,
        identifiers: list[str],
        count: int = 10,
    ) -> list[FetchResult]:
        """Fetch news for multiple search queries.

        Parameters
        ----------
        identifiers : list[str]
            List of search queries
            (e.g., ["Federal Reserve", "GDP growth"]).
        count : int, optional
            Maximum number of articles to fetch per query (default: 10).

        Returns
        -------
        list[FetchResult]
            List of FetchResult objects, one per query.
            Results are in the same order as the input identifiers.

        Notes
        -----
        If an error occurs for one query, processing continues to the next.
        Failed queries will have success=False in their FetchResult.

        Examples
        --------
        >>> source = MacroNewsSource("keywords.yaml")
        >>> results = source.fetch_all(["Federal Reserve", "GDP growth"], count=5)
        >>> len(results)
        2
        """
        return fetch_all_with_polite_delay(identifiers, self.fetch, count)

    def _load_keywords(self) -> None:
        """Load macro economics keywords from the keywords data.

        Extracts keywords from the 'macro_keywords' section of the
        keywords YAML file, optionally filtering by categories.
        """
        macro_keywords_data = self._keywords_data.get("macro_keywords", {})

        if not isinstance(macro_keywords_data, dict):
            logger.warning(
                "macro_keywords section is not a dict",
                data_type=type(macro_keywords_data).__name__,
            )
            return

        for category, keywords_list in macro_keywords_data.items():
            # Skip if categories filter is specified and this category is excluded
            if self._categories and category not in self._categories:
                continue

            if isinstance(keywords_list, list):
                for keyword in keywords_list:
                    if isinstance(keyword, str) and keyword.strip():
                        self._keywords.append(keyword.strip())
            else:
                logger.warning(
                    "Category value is not a list, skipping",
                    category=category,
                    data_type=type(keywords_list).__name__,
                )

        logger.debug(
            "Loaded macro economics keywords",
            count=len(self._keywords),
            categories=self._categories or "all",
        )


# Export all public symbols
__all__ = [
    "MacroNewsSource",
]
