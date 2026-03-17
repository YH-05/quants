"""Publisher for creating GitHub Issues from summarized articles.

This module provides the Publisher class that creates GitHub Issues from
summarized news articles and adds them to a GitHub Project.

The Publisher works with SummarizedArticle inputs (articles that have undergone
AI summarization) and produces PublishedArticle outputs with Issue information.

It also supports category-based publishing via publish_category_batch(), which
creates one Issue per CategoryGroup instead of per article, reducing GitHub API
calls by up to 98%.

Examples
--------
>>> from news.publisher import Publisher
>>> from news.config.models import load_config
>>> config = load_config("data/config/news-collection-config.yaml")
>>> publisher = Publisher(config=config)
>>> result = await publisher.publish(summarized_article)
>>> result.publication_status
<PublicationStatus.SUCCESS: 'success'>

>>> # Category-based publishing
>>> groups = grouper.group(summarized_articles)
>>> category_results = await publisher.publish_category_batch(groups)
>>> category_results[0].status
<PublicationStatus.SUCCESS: 'success'>
"""

from __future__ import annotations

import asyncio
import json
import subprocess  # nosec B404 - gh CLI is trusted
from datetime import datetime, timedelta, timezone
from typing import TYPE_CHECKING

from news.markdown_generator import CategoryMarkdownGenerator
from news.models import (
    CategoryPublishResult,
    PublicationStatus,
    PublishedArticle,
    SummarizedArticle,
)
from utils_core.logging import get_logger

if TYPE_CHECKING:
    from news.config.models import NewsWorkflowConfig
    from news.models import CategoryGroup

logger = get_logger(__name__, module="publisher")


class Publisher:
    """GitHub Issue作成とProject追加。

    要約済み記事を GitHub Issue として作成し、
    指定された Project に追加する。

    Parameters
    ----------
    config : NewsWorkflowConfig
        ワークフロー設定。github セクションから Issue 作成先の
        リポジトリ、Project ID、Status フィールド ID などを取得する。

    Attributes
    ----------
    _config : NewsWorkflowConfig
        ワークフロー設定の参照。
    _repo : str
        Issue を作成する GitHub リポジトリ（"owner/repo" 形式）。
    _project_id : str
        GitHub Project ID（PVT_...）。
    _project_number : int
        GitHub Project 番号。
    _status_field_id : str
        GitHub Project の Status フィールド ID。
    _published_date_field_id : str
        GitHub Project の公開日フィールド ID。
    _status_mapping : dict[str, str]
        カテゴリから GitHub Status 名へのマッピング。
    _status_ids : dict[str, str]
        GitHub Status 名から Status ID へのマッピング。

    Examples
    --------
    >>> from news.publisher import Publisher
    >>> from news.config.models import load_config
    >>> config = load_config("config.yaml")
    >>> publisher = Publisher(config=config)
    >>> result = await publisher.publish(summarized_article)
    >>> result.issue_number
    123

    Notes
    -----
    - 要約が失敗している記事（summary が None）は SKIPPED ステータスで返す
    - 重複チェックは publish_batch() 内で行う
    - 実際の Issue 作成処理は P5-002 以降で実装
    """

    def __init__(self, config: NewsWorkflowConfig) -> None:
        """Publisher を初期化する。

        Parameters
        ----------
        config : NewsWorkflowConfig
            ワークフロー設定。github セクションを使用する。
        """
        self._config = config
        self._repo = config.github.repository
        self._project_id = config.github.project_id
        self._project_number = config.github.project_number
        self._status_field_id = config.github.status_field_id
        self._published_date_field_id = config.github.published_date_field_id
        self._status_mapping = config.status_mapping
        self._status_ids = config.github_status_ids

        logger.debug(
            "Publisher initialized",
            repository=self._repo,
            project_number=self._project_number,
            status_mapping_count=len(self._status_mapping),
        )

    async def publish(self, article: SummarizedArticle) -> PublishedArticle:
        """単一記事をIssueとして公開。

        要約済み記事を分析し、GitHub Issue を作成する。
        要約が失敗している記事は SKIPPED ステータスで即座に返す。

        Parameters
        ----------
        article : SummarizedArticle
            要約済み記事。summarization_status が SUCCESS で summary が
            存在する場合のみ Issue を作成する。

        Returns
        -------
        PublishedArticle
            公開結果を含むオブジェクト。以下のいずれかの状態：
            - SUCCESS: Issue 作成成功。issue_number と issue_url を含む
            - SKIPPED: 要約なしでスキップ
            - FAILED: Issue 作成中にエラー発生
            - DUPLICATE: 重複 Issue が検出されスキップ

        Notes
        -----
        - 非同期メソッドとして実装されており、await が必要
        - 実際の Issue 作成は P5-002 以降で実装

        Examples
        --------
        >>> result = await publisher.publish(summarized_article)
        >>> if result.publication_status == PublicationStatus.SUCCESS:
        ...     print(f"Created Issue #{result.issue_number}")
        """
        logger.debug(
            "Starting publish",
            article_url=str(article.extracted.collected.url),
            has_summary=article.summary is not None,
            summarization_status=str(article.summarization_status),
        )

        # 要約が失敗している場合はスキップ
        if article.summary is None:
            logger.info(
                "Skipping publish: no summary",
                article_url=str(article.extracted.collected.url),
                summarization_status=str(article.summarization_status),
            )
            return PublishedArticle(
                summarized=article,
                issue_number=None,
                issue_url=None,
                publication_status=PublicationStatus.SKIPPED,
                error_message="No summary available",
            )

        # Issue 本文とタイトルを生成
        issue_body = self._generate_issue_body(article)
        issue_title = self._generate_issue_title(article)

        logger.debug(
            "Generated issue content",
            article_url=str(article.extracted.collected.url),
            title_length=len(issue_title),
            body_length=len(issue_body),
        )

        # Issue 作成
        try:
            issue_number, issue_url = await self._create_issue(article)

            # Project に追加してフィールドを設定
            await self._add_to_project(issue_number, article)

            logger.info(
                "Issue created successfully",
                issue_number=issue_number,
                issue_url=issue_url,
                article_url=str(article.extracted.collected.url),
            )

            return PublishedArticle(
                summarized=article,
                issue_number=issue_number,
                issue_url=issue_url,
                publication_status=PublicationStatus.SUCCESS,
            )

        except subprocess.CalledProcessError as e:
            error_msg = f"gh command failed: {e.stderr if e.stderr else str(e)}"
            logger.error(
                "Issue creation failed",
                error=error_msg,
                article_url=str(article.extracted.collected.url),
            )
            return PublishedArticle(
                summarized=article,
                issue_number=None,
                issue_url=None,
                publication_status=PublicationStatus.FAILED,
                error_message=error_msg,
            )
        except Exception as e:
            error_msg = f"Unexpected error: {e}"
            logger.error(
                "Issue creation failed unexpectedly",
                error=error_msg,
                error_type=type(e).__name__,
                article_url=str(article.extracted.collected.url),
            )
            return PublishedArticle(
                summarized=article,
                issue_number=None,
                issue_url=None,
                publication_status=PublicationStatus.FAILED,
                error_message=error_msg,
            )

    async def publish_batch(
        self,
        articles: list[SummarizedArticle],
        dry_run: bool = False,
    ) -> list[PublishedArticle]:
        """複数記事を公開（重複チェック含む）。

        指定された記事を順番に GitHub Issue として公開する。
        重複チェックを行い、既に公開済みの記事はスキップする。

        Parameters
        ----------
        articles : list[SummarizedArticle]
            要約済み記事のリスト。空リストの場合は空リストを返す。
        dry_run : bool, optional
            True の場合、実際の Issue 作成をスキップする。
            デフォルトは False。

        Returns
        -------
        list[PublishedArticle]
            公開結果のリスト。入力と同じ順序を保持する。

        Notes
        -----
        - 個々の記事の公開が失敗しても他の記事は継続
        - dry_run=True の場合、Issue は作成されないがログ出力は行う
        - 重複チェックにより既存 Issue と同じ URL の記事は DUPLICATE ステータス

        Examples
        --------
        >>> articles = [article1, article2, article3]
        >>> results = await publisher.publish_batch(articles, dry_run=True)
        >>> len(results)
        3
        """
        if not articles:
            logger.debug("publish_batch called with empty list")
            return []

        logger.info(
            "Starting batch publish",
            article_count=len(articles),
            dry_run=dry_run,
        )

        # 重複チェック用に既存 Issue の URL を取得
        existing_urls = await self._get_existing_issues(days=7)

        results: list[PublishedArticle] = []
        duplicate_count = 0

        for article in articles:
            # 要約がない場合はスキップ
            if article.summary is None:
                result = PublishedArticle(
                    summarized=article,
                    issue_number=None,
                    issue_url=None,
                    publication_status=PublicationStatus.SKIPPED,
                    error_message="No summary available",
                )
                results.append(result)
                continue

            # 重複チェック
            if self._is_duplicate(article, existing_urls):
                duplicate_count += 1
                result = PublishedArticle(
                    summarized=article,
                    issue_number=None,
                    issue_url=None,
                    publication_status=PublicationStatus.DUPLICATE,
                    error_message="Duplicate article detected",
                )
                results.append(result)
                continue

            # ドライランの場合は Issue 作成をスキップ
            if dry_run:
                logger.info(
                    "[DRY RUN] Would create issue",
                    title=article.extracted.collected.title,
                    url=str(article.extracted.collected.url),
                )
                result = PublishedArticle(
                    summarized=article,
                    issue_number=None,
                    issue_url=None,
                    publication_status=PublicationStatus.SUCCESS,
                )
                results.append(result)
                continue

            result = await self.publish(article)
            results.append(result)

        logger.info(
            "Batch publish completed",
            total=len(results),
            success=sum(
                1 for r in results if r.publication_status == PublicationStatus.SUCCESS
            ),
            skipped=sum(
                1 for r in results if r.publication_status == PublicationStatus.SKIPPED
            ),
            failed=sum(
                1 for r in results if r.publication_status == PublicationStatus.FAILED
            ),
            duplicates=duplicate_count,
        )

        return results

    async def publish_category_batch(
        self,
        groups: list[CategoryGroup],
        dry_run: bool = False,
    ) -> list[CategoryPublishResult]:
        """カテゴリ別にIssueを作成。

        CategoryGroup のリストを受け取り、各カテゴリにつき1つの Issue を作成する。
        タイトルベースの重複チェックを行い、既に同じカテゴリ・日付の Issue が
        存在する場合はスキップする。

        Parameters
        ----------
        groups : list[CategoryGroup]
            カテゴリグループのリスト。空リストの場合は空リストを返す。
        dry_run : bool, optional
            True の場合、実際の Issue 作成をスキップする。
            デフォルトは False。

        Returns
        -------
        list[CategoryPublishResult]
            各カテゴリの公開結果のリスト。入力と同じ順序を保持する。

        Notes
        -----
        - 個々のカテゴリの公開が失敗しても他のカテゴリは継続する
        - Markdown 生成は CategoryMarkdownGenerator を使用する
        - Project 追加・Status/Date フィールド設定は _add_category_to_project() で行う

        Examples
        --------
        >>> groups = grouper.group(summarized_articles)
        >>> results = await publisher.publish_category_batch(groups)
        >>> results[0].status
        <PublicationStatus.SUCCESS: 'success'>
        """
        if not groups:
            logger.debug("publish_category_batch called with empty list")
            return []

        logger.info(
            "Starting category batch publish",
            group_count=len(groups),
            dry_run=dry_run,
        )

        results: list[CategoryPublishResult] = []
        duplicate_count = 0
        success_count = 0
        failed_count = 0

        for group in groups:
            # 重複チェック
            existing_issue = await self._check_category_issue_exists(
                group.category_label, group.date
            )

            if existing_issue is not None:
                duplicate_count += 1
                logger.info(
                    "Category issue already exists, skipping",
                    category=group.category,
                    date=group.date,
                    existing_issue=existing_issue,
                )
                results.append(
                    CategoryPublishResult(
                        category=group.category,
                        category_label=group.category_label,
                        date=group.date,
                        issue_number=None,
                        issue_url=None,
                        article_count=len(group.articles),
                        status=PublicationStatus.DUPLICATE,
                        error_message=f"Duplicate: Issue #{existing_issue} already exists",
                    )
                )
                continue

            # ドライランの場合は Issue 作成をスキップ
            if dry_run:
                logger.info(
                    "[DRY RUN] Would create category issue",
                    category=group.category,
                    category_label=group.category_label,
                    date=group.date,
                    article_count=len(group.articles),
                )
                results.append(
                    CategoryPublishResult(
                        category=group.category,
                        category_label=group.category_label,
                        date=group.date,
                        issue_number=None,
                        issue_url=None,
                        article_count=len(group.articles),
                        status=PublicationStatus.SUCCESS,
                    )
                )
                continue

            # Issue 作成
            try:
                issue_number, issue_url = await self._create_category_issue(group)

                # Project に追加してフィールドを設定
                await self._add_category_to_project(issue_number, group)

                success_count += 1
                logger.info(
                    "Category issue created successfully",
                    issue_number=issue_number,
                    issue_url=issue_url,
                    category=group.category,
                    date=group.date,
                    article_count=len(group.articles),
                )

                results.append(
                    CategoryPublishResult(
                        category=group.category,
                        category_label=group.category_label,
                        date=group.date,
                        issue_number=issue_number,
                        issue_url=issue_url,
                        article_count=len(group.articles),
                        status=PublicationStatus.SUCCESS,
                    )
                )

            except subprocess.CalledProcessError as e:
                failed_count += 1
                error_msg = f"gh command failed: {e.stderr if e.stderr else str(e)}"
                logger.error(
                    "Category issue creation failed",
                    error=error_msg,
                    category=group.category,
                    date=group.date,
                )
                results.append(
                    CategoryPublishResult(
                        category=group.category,
                        category_label=group.category_label,
                        date=group.date,
                        issue_number=None,
                        issue_url=None,
                        article_count=len(group.articles),
                        status=PublicationStatus.FAILED,
                        error_message=error_msg,
                    )
                )

            except Exception as e:
                failed_count += 1
                error_msg = f"Unexpected error: {e}"
                logger.error(
                    "Category issue creation failed unexpectedly",
                    error=error_msg,
                    error_type=type(e).__name__,
                    category=group.category,
                    date=group.date,
                )
                results.append(
                    CategoryPublishResult(
                        category=group.category,
                        category_label=group.category_label,
                        date=group.date,
                        issue_number=None,
                        issue_url=None,
                        article_count=len(group.articles),
                        status=PublicationStatus.FAILED,
                        error_message=error_msg,
                    )
                )

        logger.info(
            "Category batch publish completed",
            total=len(results),
            success=success_count,
            duplicates=duplicate_count,
            failed=failed_count,
        )

        return results

    async def _check_category_issue_exists(
        self, category_label: str, date: str
    ) -> int | None:
        """カテゴリ別Issueの重複チェック。

        タイトルベースの検索で、同じカテゴリラベル・日付の Issue が
        既に存在するかチェックする。

        Parameters
        ----------
        category_label : str
            カテゴリの日本語ラベル（例: "株価指数"）。
        date : str
            日付文字列（例: "2026-02-09"）。

        Returns
        -------
        int | None
            既存 Issue の番号。存在しない場合は None。

        Notes
        -----
        - タイトル "[{category_label}] ニュースまとめ - {date}" で検索
        - gh issue list --search を使用（非同期）
        - gh コマンドが失敗した場合は None を返す（graceful degradation）

        Examples
        --------
        >>> issue_num = await publisher._check_category_issue_exists(
        ...     "株価指数", "2026-02-09"
        ... )
        >>> issue_num
        50
        """
        search_query = f"[{category_label}] ニュースまとめ - {date}"

        logger.debug(
            "Checking for existing category issue",
            category_label=category_label,
            date=date,
            search_query=search_query,
        )

        proc = await asyncio.create_subprocess_exec(
            "gh",
            "issue",
            "list",
            "--repo",
            self._repo,
            "--search",
            search_query,
            "--state",
            "all",
            "--limit",
            "5",
            "--json",
            "number,title",
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await proc.communicate()

        if proc.returncode != 0:
            logger.error(
                "Failed to search for existing category issues",
                stderr=stderr.decode(),
                returncode=proc.returncode,
            )
            return None

        issues = json.loads(stdout.decode())

        # タイトルが完全一致する Issue を探す
        expected_title = f"[{category_label}] ニュースまとめ - {date}"
        for issue in issues:
            if issue.get("title") == expected_title:
                issue_number = issue["number"]
                logger.info(
                    "Found existing category issue",
                    issue_number=issue_number,
                    category_label=category_label,
                    date=date,
                )
                return issue_number

        logger.debug(
            "No existing category issue found",
            category_label=category_label,
            date=date,
        )
        return None

    async def _create_category_issue(self, group: CategoryGroup) -> tuple[int, str]:
        """カテゴリ別 Issue を作成。

        CategoryMarkdownGenerator を使用してタイトルと本文を生成し、
        gh issue create コマンドで Issue を作成する。

        Parameters
        ----------
        group : CategoryGroup
            カテゴリグループ。

        Returns
        -------
        tuple[int, str]
            (Issue番号, Issue URL) のタプル。

        Raises
        ------
        subprocess.CalledProcessError
            gh コマンドの実行に失敗した場合。

        Examples
        --------
        >>> issue_number, issue_url = await publisher._create_category_issue(group)
        >>> issue_number
        100
        """
        generator = CategoryMarkdownGenerator()
        title = generator.generate_issue_title(group)
        body = generator.generate_issue_body(group)

        logger.debug(
            "Creating category issue",
            category=group.category,
            date=group.date,
            title_length=len(title),
            body_length=len(body),
            article_count=len(group.articles),
        )

        return self._execute_gh_issue_create(title, body)

    async def _ensure_project_item(self, issue_number: int) -> str | None:
        """Issue を Project に追加し、item_id を返す。

        既に Project に存在する場合はその item_id を返し、
        存在しない場合は新規追加して item_id を返す。

        Parameters
        ----------
        issue_number : int
            追加する Issue 番号。

        Returns
        -------
        str | None
            Project item の ID。取得できない場合は None。
        """
        issue_url = f"https://github.com/{self._repo}/issues/{issue_number}"
        owner = self._repo.split("/")[0]

        item_id = await self._get_existing_project_item(issue_url)
        if item_id is not None:
            logger.info(
                "Issue already in project, updating fields only",
                issue_number=issue_number,
                item_id=item_id,
            )
            return item_id

        add_result = subprocess.run(  # nosec B603 - gh CLI with safe args
            [
                "gh",
                "project",
                "item-add",
                str(self._project_number),
                "--owner",
                owner,
                "--url",
                issue_url,
                "--format",
                "json",
            ],
            capture_output=True,
            text=True,
            check=True,
        )

        try:
            add_data = json.loads(add_result.stdout)
            item_id = add_data.get("id", "")
        except json.JSONDecodeError:
            item_id = ""

        if not item_id:
            logger.warning(
                "Empty item_id from project item-add, skipping field updates",
                issue_number=issue_number,
                issue_url=issue_url,
                stderr=add_result.stderr,
                stdout=add_result.stdout,
            )
            return None

        logger.debug(
            "Added issue to project",
            issue_number=issue_number,
            project_number=self._project_number,
            item_id=item_id,
        )
        return item_id

    def _set_project_fields(
        self, item_id: str, status_id: str, date_str: str | None
    ) -> None:
        """Project item の Status と PublishedDate フィールドを設定する。

        Parameters
        ----------
        item_id : str
            Project item の ID。
        status_id : str
            設定する Status Option ID。
        date_str : str | None
            設定する日付文字列（YYYY-MM-DD 形式）。None の場合は日付設定をスキップ。
        """
        subprocess.run(  # nosec B603 - gh CLI with safe args
            [
                "gh",
                "project",
                "item-edit",
                "--project-id",
                self._project_id,
                "--id",
                item_id,
                "--field-id",
                self._status_field_id,
                "--single-select-option-id",
                status_id,
            ],
            capture_output=True,
            text=True,
            check=True,
        )
        logger.debug("Set status field", item_id=item_id, status_id=status_id)

        if date_str:
            subprocess.run(  # nosec B603 - gh CLI with safe args
                [
                    "gh",
                    "project",
                    "item-edit",
                    "--project-id",
                    self._project_id,
                    "--id",
                    item_id,
                    "--field-id",
                    self._published_date_field_id,
                    "--date",
                    date_str,
                ],
                capture_output=True,
                text=True,
                check=True,
            )
            logger.debug("Set published date field", item_id=item_id, date=date_str)

    async def _add_category_to_project(
        self, issue_number: int, group: CategoryGroup
    ) -> None:
        """カテゴリ Issue を Project に追加し、フィールドを設定。

        Parameters
        ----------
        issue_number : int
            追加する Issue 番号。
        group : CategoryGroup
            カテゴリグループ。Status 解決と日付設定に使用する。

        Raises
        ------
        subprocess.CalledProcessError
            gh コマンドの実行に失敗した場合。
        """
        item_id = await self._ensure_project_item(issue_number)
        if item_id is None:
            return

        status_name = group.category
        status_id = self._status_ids.get(
            status_name, self._status_ids.get("finance", "")
        )
        self._set_project_fields(item_id, status_id, group.date)

    async def get_existing_urls(self, days: int | None = None) -> set[str]:
        """直近N日の既存 Issue から記事 URL を取得する。

        指定された期間内の GitHub Issue を検索し、Issue 本文に含まれる
        記事 URL を抽出して返す。重複チェックの前処理として使用する。

        Parameters
        ----------
        days : int | None, optional
            取得対象期間（日数）。None の場合は設定ファイルの
            github.duplicate_check_days の値を使用する（デフォルト: 7日）。

        Returns
        -------
        set[str]
            既存 Issue の記事 URL セット。

        Examples
        --------
        >>> urls = await publisher.get_existing_urls()
        >>> "https://www.cnbc.com/article/123" in urls
        True

        >>> urls = await publisher.get_existing_urls(days=14)
        >>> len(urls)
        42
        """
        check_days = (
            days if days is not None else self._config.github.duplicate_check_days
        )
        return await self._get_existing_issues(days=check_days)

    def is_duplicate_url(self, url: str, existing_urls: set[str]) -> bool:
        """URL が既存 Issue に含まれるか判定する。

        指定された URL が既存 Issue の URL セットに含まれているか確認する。
        重複チェックに使用する。

        Parameters
        ----------
        url : str
            チェック対象の記事 URL。
        existing_urls : set[str]
            既存 Issue の URL セット。get_existing_urls() で取得する。

        Returns
        -------
        bool
            URL が既存 Issue に含まれる場合 True、そうでない場合 False。

        Examples
        --------
        >>> existing = await publisher.get_existing_urls()
        >>> publisher.is_duplicate_url("https://www.cnbc.com/article/123", existing)
        True
        >>> publisher.is_duplicate_url("https://www.cnbc.com/article/new", existing)
        False
        """
        is_dup = url in existing_urls

        if is_dup:
            logger.debug(
                "Duplicate URL detected",
                url=url,
            )

        return is_dup

    def _generate_issue_body(self, article: SummarizedArticle) -> str:
        """Issue本文を生成。

        4セクション構造（概要、キーポイント、市場への影響、関連情報）と
        メタデータ（ソース、公開日、URL）を含むMarkdown形式の本文を生成する。

        Parameters
        ----------
        article : SummarizedArticle
            要約済み記事。summary が存在することを前提とする。

        Returns
        -------
        str
            Markdown形式のIssue本文。

        Notes
        -----
        - summary が None の場合の動作は未定義（呼び出し元で事前にチェックすること）
        - related_info が None の場合、関連情報セクションは省略される
        - published が None の場合、公開日は「不明」と表示される
        """
        # article.summary is not None であることは呼び出し元で保証されている
        summary = article.summary
        if summary is None:  # pragma: no cover
            raise ValueError("summary must not be None")

        collected = article.extracted.collected

        # キーポイントをマークダウンリストに変換
        key_points_md = "\n".join(f"- {point}" for point in summary.key_points)

        # 関連情報（オプション）
        related_info_section = ""
        if summary.related_info:
            related_info_section = f"""
## 関連情報
{summary.related_info}
"""

        # 公開日のフォーマット
        published_str = (
            collected.published.strftime("%Y-%m-%d %H:%M")
            if collected.published
            else "不明"
        )

        body = f"""# {collected.title}

## 概要
{summary.overview}

## キーポイント
{key_points_md}

## 市場への影響
{summary.market_impact}
{related_info_section}
---
**ソース**: {collected.source.source_name}
**公開日**: {published_str}
**URL**: {collected.url}
"""
        return body

    def _generate_issue_title(self, article: SummarizedArticle) -> str:
        """Issueタイトルを生成。

        カテゴリに基づくプレフィックスを付与したタイトルを生成する。

        Parameters
        ----------
        article : SummarizedArticle
            要約済み記事。

        Returns
        -------
        str
            プレフィックス付きのIssueタイトル（例: "[index] 記事タイトル"）。

        Notes
        -----
        - カテゴリから status へのマッピングは _status_mapping を使用
        - マッピングにないカテゴリの場合は "other" をプレフィックスとして使用
        """
        category = article.extracted.collected.source.category
        status = self._status_mapping.get(category, "other")
        return f"[{status}] {article.extracted.collected.title}"

    def _resolve_status(self, article: SummarizedArticle) -> tuple[str, str]:
        """カテゴリからGitHub Statusを解決。

        ArticleSource.category から status_mapping を使用して Status 名を取得し、
        github_status_ids から Status Option ID を取得する。

        Parameters
        ----------
        article : SummarizedArticle
            要約済み記事。

        Returns
        -------
        tuple[str, str]
            (Status名, Status Option ID) のタプル。
            - Status名: "index", "stock", "sector", "macro", "ai", "finance" など
            - Status Option ID: GitHub Project の Status フィールドの Option ID

        Notes
        -----
        - 未知のカテゴリの場合は "finance" がデフォルト Status 名として使用される
        - Status 名が github_status_ids に存在しない場合も "finance" の ID が使用される

        Examples
        --------
        >>> publisher._resolve_status(article)
        ("index", "3925acc3")
        """
        category = article.extracted.collected.source.category

        # status_mapping でカテゴリ → Status名 を解決
        # 例: "market" → "index", "tech" → "ai"
        status_name = self._status_mapping.get(category, "finance")

        # github_status_ids で Status名 → Option ID を解決
        # 例: "index" → "3925acc3"
        status_id = self._status_ids.get(status_name, self._status_ids["finance"])

        logger.debug(
            "Resolved status from category",
            category=category,
            status_name=status_name,
            status_id=status_id,
        )

        return status_name, status_id

    def _execute_gh_issue_create(self, title: str, body: str) -> tuple[int, str]:
        """gh issue create を実行し Issue 番号と URL を返す。

        Parameters
        ----------
        title : str
            Issue タイトル。
        body : str
            Issue 本文（Markdown形式）。

        Returns
        -------
        tuple[int, str]
            (Issue番号, Issue URL) のタプル。

        Raises
        ------
        subprocess.CalledProcessError
            gh コマンドの実行に失敗した場合。
        """
        result = subprocess.run(  # nosec B603 - gh CLI with safe args
            [
                "gh",
                "issue",
                "create",
                "--repo",
                self._repo,
                "--title",
                title,
                "--body",
                body,
            ],
            capture_output=True,
            text=True,
            check=True,
        )

        issue_url = result.stdout.strip()
        issue_number = int(issue_url.split("/")[-1])

        logger.debug(
            "Created issue via gh CLI",
            issue_number=issue_number,
            issue_url=issue_url,
        )

        return issue_number, issue_url

    async def _create_issue(self, article: SummarizedArticle) -> tuple[int, str]:
        """Issue を作成。

        gh issue create コマンドを使用して GitHub Issue を作成する。

        Parameters
        ----------
        article : SummarizedArticle
            要約済み記事。summary が存在することを前提とする。

        Returns
        -------
        tuple[int, str]
            (Issue番号, Issue URL) のタプル。

        Raises
        ------
        subprocess.CalledProcessError
            gh コマンドの実行に失敗した場合。

        Examples
        --------
        >>> issue_number, issue_url = await publisher._create_issue(article)
        >>> issue_number
        123
        >>> issue_url
        'https://github.com/YH-05/quants/issues/123'
        """
        title = self._generate_issue_title(article)
        body = self._generate_issue_body(article)
        return self._execute_gh_issue_create(title, body)

    async def _get_existing_project_item(self, issue_url: str) -> str | None:
        """Project 内の既存 Item を検索し item_id を返す。

        gh project item-list コマンドで Project 内の Item を検索し、
        指定された Issue URL に一致する Item の ID を取得する。

        Parameters
        ----------
        issue_url : str
            検索する Issue の URL。

        Returns
        -------
        str | None
            既存の item_id、存在しない場合は None。

        Notes
        -----
        - gh コマンドが失敗した場合も None を返す（graceful degradation）
        - --jq フィルタで content.url が一致する Item の id を抽出

        Examples
        --------
        >>> item_id = await publisher._get_existing_project_item(
        ...     "https://github.com/YH-05/quants/issues/123"
        ... )
        >>> item_id
        'PVTI_xxx'
        """
        owner = self._repo.split("/")[0]

        # jq フィルタ: Issue URL に一致する Item の ID を取得
        jq_filter = f'.items[] | select(.content.url == "{issue_url}") | .id'

        result = subprocess.run(  # nosec B603 - gh CLI with safe args
            [
                "gh",
                "project",
                "item-list",
                str(self._project_number),
                "--owner",
                owner,
                "--format",
                "json",
                "--jq",
                jq_filter,
            ],
            capture_output=True,
            text=True,
            check=False,
        )

        if result.returncode == 0 and result.stdout.strip():
            item_id = result.stdout.strip()
            logger.debug(
                "Found existing project item",
                issue_url=issue_url,
                item_id=item_id,
            )
            return item_id

        return None

    async def _add_to_project(
        self, issue_number: int, article: SummarizedArticle
    ) -> None:
        """Issue を Project に追加し、フィールドを設定。

        Parameters
        ----------
        issue_number : int
            追加する Issue 番号。
        article : SummarizedArticle
            要約済み記事。Status 解決と公開日取得に使用する。

        Raises
        ------
        subprocess.CalledProcessError
            gh コマンドの実行に失敗した場合。
        """
        item_id = await self._ensure_project_item(issue_number)
        if item_id is None:
            return

        _, status_id = self._resolve_status(article)
        published = article.extracted.collected.published
        date_str = published.strftime("%Y-%m-%d") if published else None
        self._set_project_fields(item_id, status_id, date_str)

    async def _get_existing_issues(self, days: int = 7) -> set[str]:
        """直近N日のIssue URLを取得。

        GitHub Issue 一覧を非同期で取得し、Issue 本文から記事 URL を抽出する。
        重複チェックに使用する。

        Parameters
        ----------
        days : int, optional
            取得対象期間（デフォルト: 7日）。
            この期間内に作成された Issue のみを対象とする。

        Returns
        -------
        set[str]
            既存 Issue の記事 URL セット。

        Notes
        -----
        - asyncio.create_subprocess_exec を使用してイベントループをブロックしない
        - Issue 本文から "**URL**: https://..." の形式で URL を抽出する
        - 指定期間より古い Issue は除外される
        - URL パターンが見つからない Issue は無視される
        - gh コマンドが失敗した場合は空のセットを返す（graceful degradation）

        Examples
        --------
        >>> urls = await publisher._get_existing_issues(days=7)
        >>> "https://www.cnbc.com/article/123" in urls
        True
        """
        since_date = datetime.now(timezone.utc) - timedelta(days=days)

        logger.debug(
            "Fetching existing issues",
            since_date=since_date.isoformat(),
            days=days,
        )

        proc = await asyncio.create_subprocess_exec(
            "gh",
            "issue",
            "list",
            "--repo",
            self._repo,
            "--state",
            "all",
            "--limit",
            "1000",
            "--json",
            "body,createdAt",
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await proc.communicate()

        if proc.returncode != 0:
            logger.error(
                "Failed to fetch issues",
                stderr=stderr.decode(),
                returncode=proc.returncode,
            )
            return set()

        issues = json.loads(stdout.decode())
        urls: set[str] = set()

        for issue in issues:
            created_at = datetime.fromisoformat(
                issue["createdAt"].replace("Z", "+00:00")
            )
            if created_at >= since_date:
                # Issue 本文から URL を抽出（**URL**: https://... の形式）
                body = issue.get("body") or ""
                if "**URL**:" in body:
                    for line in body.split("\n"):
                        if line.startswith("**URL**:"):
                            url = line.replace("**URL**:", "").strip()
                            urls.add(url)

        logger.debug(
            "Found existing issue URLs",
            url_count=len(urls),
        )

        return urls

    def _is_duplicate(
        self, article: SummarizedArticle, existing_urls: set[str]
    ) -> bool:
        """記事が重複しているか判定。

        記事の URL が既存 Issue の URL セットに含まれているか確認する。

        Parameters
        ----------
        article : SummarizedArticle
            要約済み記事。
        existing_urls : set[str]
            既存 Issue の URL セット。_get_existing_issues() で取得する。

        Returns
        -------
        bool
            重複している場合 True、そうでない場合 False。

        Examples
        --------
        >>> existing_urls = {"https://www.cnbc.com/article/123"}
        >>> is_dup = publisher._is_duplicate(article, existing_urls)
        >>> is_dup
        True
        """
        article_url = str(article.extracted.collected.url)
        is_dup = article_url in existing_urls

        if is_dup:
            logger.debug(
                "Duplicate article detected",
                article_url=article_url,
            )

        return is_dup


__all__ = [
    "Publisher",
]
