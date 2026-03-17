"""GitHub Issue/Project output sink for the news package.

This module provides the GitHubSink class for creating GitHub Issues from news
articles and adding them to a specified GitHub Project.

Examples
--------
>>> from news.sinks.github import GitHubSink, GitHubSinkConfig
>>> sink = GitHubSink(project_number=24)
>>> sink.write(articles)  # Creates GitHub Issues for each article
True

>>> config = GitHubSinkConfig(
...     project_number=24,
...     labels=["news", "finance"],
...     dry_run=True,
... )
>>> sink = GitHubSink(config=config)
>>> sink.write(articles)  # Dry run mode - no actual Issue creation
True
"""

from __future__ import annotations

import json
import subprocess  # nosec B404 - gh CLI is trusted
from typing import TYPE_CHECKING, Any

from pydantic import BaseModel, Field, field_validator

from utils_core.logging import get_logger

from ..core.sink import SinkType

if TYPE_CHECKING:
    from ..core.article import Article
    from ..core.result import FetchResult

logger = get_logger(__name__, module="sinks.github")


class GitHubSinkConfig(BaseModel):
    """Configuration for GitHubSink.

    Parameters
    ----------
    project_number : int
        GitHub Project number to add Issues to. Must be positive.
    repository : str | None, optional
        Repository in "owner/repo" format. If None, uses current repository.
    labels : list[str], optional
        Labels to add to created Issues. Default is empty list.
    dry_run : bool, optional
        If True, don't actually create Issues. Default is False.

    Attributes
    ----------
    project_number : int
        The GitHub Project number.
    repository : str | None
        The repository name.
    labels : list[str]
        Labels for Issues.
    dry_run : bool
        Whether to run in dry-run mode.

    Examples
    --------
    >>> config = GitHubSinkConfig(project_number=24)
    >>> config.project_number
    24

    >>> config = GitHubSinkConfig(
    ...     project_number=24,
    ...     repository="YH-05/quants",
    ...     labels=["news"],
    ...     dry_run=True,
    ... )
    """

    project_number: int = Field(
        ...,
        gt=0,
        description="GitHub Project number to add Issues to (must be positive)",
    )
    repository: str | None = Field(
        None,
        description="Repository in 'owner/repo' format. If None, uses current repository",
    )
    labels: list[str] = Field(
        default_factory=list,
        description="Labels to add to created Issues",
    )
    dry_run: bool = Field(
        False,
        description="If True, don't actually create Issues (for testing)",
    )

    @field_validator("project_number")
    @classmethod
    def validate_project_number(cls, v: int) -> int:
        """Validate that project_number is positive.

        Parameters
        ----------
        v : int
            The value to validate.

        Returns
        -------
        int
            The validated value.

        Raises
        ------
        ValueError
            If value is not positive.
        """
        if v <= 0:
            msg = f"project_number must be positive, got {v}"
            raise ValueError(msg)
        return v


class GitHubSink:
    """GitHub Issue/Project output sink for news articles.

    Creates GitHub Issues from news articles and adds them to a specified
    GitHub Project using the `gh` CLI tool.

    Parameters
    ----------
    config : GitHubSinkConfig | None, optional
        Configuration for the sink. If provided, other parameters are ignored.
    project_number : int | None, optional
        GitHub Project number. Required if config is not provided.
    check_duplicates : bool, optional
        Whether to check for duplicate articles before creating Issues.
        Default is True.

    Attributes
    ----------
    config : GitHubSinkConfig
        The sink configuration.
    check_duplicates : bool
        Whether duplicate checking is enabled.

    Examples
    --------
    >>> sink = GitHubSink(project_number=24)
    >>> sink.sink_name
    'github_issue'
    >>> sink.sink_type
    <SinkType.GITHUB: 'github'>

    Notes
    -----
    - Requires `gh` CLI to be installed and authenticated.
    - Issues are created in the current repository unless specified in config.
    - Duplicate check uses the article URL in Issue body.
    """

    def __init__(
        self,
        config: GitHubSinkConfig | None = None,
        project_number: int | None = None,
        check_duplicates: bool = True,
    ) -> None:
        """Initialize GitHubSink with configuration.

        Parameters
        ----------
        config : GitHubSinkConfig | None, optional
            Configuration for the sink.
        project_number : int | None, optional
            GitHub Project number (used if config is not provided).
        check_duplicates : bool, optional
            Whether to check for duplicates. Default is True.
        """
        if config is not None:
            self._config = config
        elif project_number is not None:
            self._config = GitHubSinkConfig(project_number=project_number)
        else:
            msg = "Either config or project_number must be provided"
            raise ValueError(msg)

        self._check_duplicates = check_duplicates

        logger.info(
            "GitHubSink initialized",
            project_number=self._config.project_number,
            repository=self._config.repository,
            labels=self._config.labels,
            dry_run=self._config.dry_run,
            check_duplicates=check_duplicates,
        )

    @property
    def config(self) -> GitHubSinkConfig:
        """Return the sink configuration.

        Returns
        -------
        GitHubSinkConfig
            The current configuration.
        """
        return self._config

    @property
    def check_duplicates(self) -> bool:
        """Return whether duplicate checking is enabled.

        Returns
        -------
        bool
            True if duplicate checking is enabled.
        """
        return self._check_duplicates

    @property
    def sink_name(self) -> str:
        """Return the sink name.

        Returns
        -------
        str
            The name "github_issue".
        """
        return "github_issue"

    @property
    def sink_type(self) -> SinkType:
        """Return the sink type.

        Returns
        -------
        SinkType
            SinkType.GITHUB.
        """
        return SinkType.GITHUB

    def write(
        self,
        articles: list[Article],
        metadata: dict[str, Any] | None = None,
    ) -> bool:
        """Write articles as GitHub Issues.

        Creates a GitHub Issue for each article and adds it to the specified
        GitHub Project.

        Parameters
        ----------
        articles : list[Article]
            List of articles to create Issues from.
        metadata : dict[str, Any] | None, optional
            Additional metadata (currently unused). Default is None.

        Returns
        -------
        bool
            True if all Issues were created successfully, False otherwise.

        Notes
        -----
        - Empty articles list returns True.
        - In dry_run mode, no actual Issues are created.
        - If check_duplicates is True, articles with existing Issues are skipped.
        """
        if not articles:
            logger.debug("No articles to write, returning True")
            return True

        if self._config.dry_run:
            logger.info(
                "Dry run mode - would create Issues",
                article_count=len(articles),
            )
            for article in articles:
                logger.debug(
                    "Would create Issue",
                    title=article.title,
                    url=str(article.url),
                )
            return True

        success = True
        for article in articles:
            try:
                # Check for duplicates if enabled
                if self._check_duplicates and self._is_duplicate(article):
                    logger.debug(
                        "Skipping duplicate article",
                        url=str(article.url),
                        title=article.title,
                    )
                    continue

                # Create Issue
                issue_url = self._create_issue(article)
                if issue_url is None:
                    success = False
                    continue

                # Add to Project
                self._add_to_project(issue_url)

            except subprocess.SubprocessError as e:
                logger.error(
                    "Subprocess error while creating Issue",
                    error=str(e),
                    article_title=article.title,
                )
                success = False
            except Exception as e:
                logger.error(
                    "Unexpected error while creating Issue",
                    error=str(e),
                    error_type=type(e).__name__,
                    article_title=article.title,
                )
                success = False

        return success

    def write_batch(self, results: list[FetchResult]) -> bool:
        """Write multiple fetch results as GitHub Issues.

        Parameters
        ----------
        results : list[FetchResult]
            List of FetchResult objects to write.

        Returns
        -------
        bool
            True if all successful FetchResults were written, False otherwise.

        Notes
        -----
        - Only successful FetchResults (success=True) are processed.
        - Failed FetchResults are logged and skipped.
        """
        if not results:
            logger.debug("No results to write, returning True")
            return True

        # Collect all articles from successful results
        all_articles: list[Article] = []
        for result in results:
            if result.success:
                all_articles.extend(result.articles)
            else:
                logger.debug(
                    "Skipping failed FetchResult",
                    source_identifier=result.source_identifier,
                )

        return self.write(all_articles)

    def _is_duplicate(self, article: Article) -> bool:
        """Check if an article already has a corresponding Issue.

        Parameters
        ----------
        article : Article
            The article to check.

        Returns
        -------
        bool
            True if a duplicate Issue exists, False otherwise.
        """
        try:
            cmd = [
                "gh",
                "issue",
                "list",
                "--json",
                "number,title,body",
                "--search",
                str(article.url),
            ]

            if self._config.repository:
                cmd.extend(["--repo", self._config.repository])

            result = subprocess.run(  # nosec B603 - gh CLI with safe args
                cmd,
                capture_output=True,
                text=True,
                check=False,
            )

            if result.returncode != 0:
                logger.warning(
                    "Failed to check for duplicates",
                    stderr=result.stderr,
                )
                return False

            issues = json.loads(result.stdout) if result.stdout.strip() else []

            # Check if any Issue body contains the article URL
            article_url = str(article.url)
            for issue in issues:
                body = issue.get("body", "")
                if article_url in body:
                    logger.debug(
                        "Found duplicate Issue",
                        issue_number=issue.get("number"),
                        article_url=article_url,
                    )
                    return True

            return False

        except (json.JSONDecodeError, subprocess.SubprocessError) as e:
            logger.warning(
                "Error checking for duplicates",
                error=str(e),
            )
            return False

    def _create_issue(self, article: Article) -> str | None:
        """Create a GitHub Issue from an article.

        Parameters
        ----------
        article : Article
            The article to create an Issue from.

        Returns
        -------
        str | None
            The URL of the created Issue, or None if creation failed.
        """
        title = article.title
        body = self._build_issue_body(article)

        cmd = [
            "gh",
            "issue",
            "create",
            "--title",
            title,
            "--body",
            body,
        ]

        # Add repository if specified
        if self._config.repository:
            cmd.extend(["--repo", self._config.repository])

        # Add labels
        for label in self._config.labels:
            cmd.extend(["--label", label])

        result = subprocess.run(  # nosec B603 - gh CLI with safe args
            cmd,
            capture_output=True,
            text=True,
            check=False,
        )

        if result.returncode != 0:
            logger.error(
                "Failed to create Issue",
                stderr=result.stderr,
                article_title=article.title,
            )
            return None

        issue_url = result.stdout.strip()
        logger.info(
            "Created Issue",
            issue_url=issue_url,
            article_title=article.title,
        )
        return issue_url

    def _add_to_project(self, issue_url: str) -> bool:
        """Add an Issue to the GitHub Project.

        Parameters
        ----------
        issue_url : str
            The URL of the Issue to add.

        Returns
        -------
        bool
            True if the Issue was added successfully, False otherwise.
        """
        cmd = [
            "gh",
            "project",
            "item-add",
            str(self._config.project_number),
            "--owner",
            "@me",
            "--url",
            issue_url,
        ]

        result = subprocess.run(  # nosec B603 - gh CLI with safe args
            cmd,
            capture_output=True,
            text=True,
            check=False,
        )

        if result.returncode != 0:
            logger.warning(
                "Failed to add Issue to Project",
                stderr=result.stderr,
                issue_url=issue_url,
                project_number=self._config.project_number,
            )
            return False

        logger.info(
            "Added Issue to Project",
            issue_url=issue_url,
            project_number=self._config.project_number,
        )
        return True

    def _build_issue_body(self, article: Article) -> str:
        """Build the Issue body from an article.

        Parameters
        ----------
        article : Article
            The article to build the body from.

        Returns
        -------
        str
            The formatted Issue body following project.md specification.
        """
        # Format published date
        published_date = article.published_at.strftime("%Y-%m-%d %H:%M:%S UTC")

        # Format provider
        provider_name = article.provider.name if article.provider else "Unknown"

        # Format related tickers
        tickers_str = (
            ", ".join(article.related_tickers) if article.related_tickers else "N/A"
        )

        # Format tags
        tags_str = ", ".join(article.tags) if article.tags else "N/A"

        # Build body following the Issue format from project.md
        body = f"""# {article.title}

## 概要

{article.summary or article.title}

## 詳細

- URL: {article.url}
- 公開日時: {published_date}
- ソース: {provider_name}
- 関連ティッカー: {tickers_str}

## タグ

{tags_str}
"""
        return body


# Export all public symbols
__all__ = [
    "GitHubSink",
    "GitHubSinkConfig",
]
