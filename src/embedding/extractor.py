"""本文抽出モジュール.

記事 URL から本文を抽出する。trafilatura を優先し、失敗時は playwright fallback で
JS レンダリングページに対応する。``RateLimiter`` で並行数制御を行う。

抽出戦略:
1. **trafilatura**: ``trafilatura.fetch_url()`` + ``trafilatura.extract()`` で本文抽出
2. **playwright fallback**: trafilatura 失敗時、JS レンダリングが必要なページ用
3. **両方失敗**: ``ExtractionResult.method == "failed"`` で返却

Examples
--------
>>> import asyncio
>>> from embedding.extractor import extract_contents
>>> from embedding.types import ArticleRecord, PipelineConfig
>>> config = PipelineConfig()
>>> articles = [ArticleRecord(url="https://example.com", title="Test")]
>>> results = asyncio.run(extract_contents(articles, config))
"""

import asyncio
import logging
from datetime import UTC, datetime

import trafilatura

from .rate_limiter import RateLimiter
from .types import ArticleRecord, ExtractionResult, PipelineConfig

logger = logging.getLogger(__name__)

# playwright はオプション依存。未インストール時は None にフォールバック。
try:
    from playwright.async_api import async_playwright  # type: ignore[import-not-found]
except ImportError:
    async_playwright = None  # type: ignore[assignment]


async def extract_contents(
    articles: list[ArticleRecord],
    config: PipelineConfig,
) -> list[ExtractionResult]:
    """非同期並列で記事本文を抽出する.

    ``RateLimiter`` で並行数とリクエスト間隔を制御しながら、
    各記事の URL から本文を抽出する。

    Parameters
    ----------
    articles : list[ArticleRecord]
        本文抽出対象の記事レコードリスト
    config : PipelineConfig
        パイプライン設定（max_concurrency, delay, timeout, use_playwright_fallback）

    Returns
    -------
    list[ExtractionResult]
        抽出結果リスト（articles と同順、同サイズ）
    """
    if not articles:
        logger.info("No articles to extract")
        return []

    rate_limiter = RateLimiter(
        max_concurrent=config.max_concurrency,
        delay_seconds=config.delay,
    )

    logger.info(
        "Starting extraction for %d articles (concurrency=%d, delay=%.1fs)",
        len(articles),
        config.max_concurrency,
        config.delay,
    )

    async def _rate_limited_extract(article: ArticleRecord) -> ExtractionResult:
        async with rate_limiter:
            return await _extract_single(
                article.url,
                timeout=config.timeout,
                use_playwright=config.use_playwright_fallback,
            )

    tasks = [
        asyncio.create_task(_rate_limited_extract(article)) for article in articles
    ]
    results = await asyncio.gather(*tasks)

    success_count = sum(1 for r in results if r.method != "failed")
    logger.info(
        "Extraction completed: %d/%d successful",
        success_count,
        len(articles),
    )

    return list(results)


async def _extract_single(
    url: str,
    timeout: int,
    use_playwright: bool,
) -> ExtractionResult:
    """単一 URL から本文を抽出する.

    trafilatura を最初に試行し、失敗時に playwright fallback を実行する。

    Parameters
    ----------
    url : str
        抽出対象の記事 URL
    timeout : int
        タイムアウト秒数
    use_playwright : bool
        playwright fallback を使用するか

    Returns
    -------
    ExtractionResult
        抽出結果
    """
    now = datetime.now(UTC).isoformat()

    # 1. trafilatura で抽出を試行
    logger.debug("Trying trafilatura for: %s", url)
    content = await _extract_with_trafilatura(url, timeout)
    if content:
        logger.debug("trafilatura succeeded for: %s", url)
        return ExtractionResult(
            url=url,
            content=content,
            method="trafilatura",
            extracted_at=now,
        )

    # 2. playwright fallback
    if use_playwright:
        logger.debug("Trying playwright fallback for: %s", url)
        content = await _extract_with_playwright(url, timeout)
        if content:
            logger.debug("playwright succeeded for: %s", url)
            return ExtractionResult(
                url=url,
                content=content,
                method="playwright",
                extracted_at=now,
            )

    # 3. 両方失敗
    logger.warning("All extraction methods failed for: %s", url)
    return ExtractionResult(
        url=url,
        content="",
        method="failed",
        extracted_at=now,
        error=f"All extraction methods failed for {url}",
    )


async def _extract_with_trafilatura(url: str, timeout: int) -> str | None:
    """trafilatura で本文を抽出する.

    ``asyncio.to_thread`` でブロッキング処理をオフロードする。

    Parameters
    ----------
    url : str
        抽出対象の記事 URL
    timeout : int
        タイムアウト秒数

    Returns
    -------
    str | None
        抽出された本文テキスト。失敗時は None。
    """
    try:

        def _fetch_and_extract() -> str | None:
            html = trafilatura.fetch_url(url)
            if html is None:
                return None
            return trafilatura.extract(html)

        content = await asyncio.wait_for(
            asyncio.to_thread(_fetch_and_extract),
            timeout=timeout,
        )
        if content is None:
            logger.debug("trafilatura extraction returned None for: %s", url)
            return None

        return content
    except Exception:
        logger.debug("trafilatura extraction failed for: %s", url, exc_info=True)
        return None


async def _extract_with_playwright(url: str, timeout: int) -> str | None:
    """playwright で JS レンダリングページの本文を取得する.

    playwright 未インストール時は ``None`` を返却する。
    取得した HTML を trafilatura.extract で本文抽出する。

    Parameters
    ----------
    url : str
        抽出対象の記事 URL
    timeout : int
        タイムアウト秒数（playwright は ms 単位）

    Returns
    -------
    str | None
        抽出された本文テキスト。失敗時は None。
    """
    if async_playwright is None:
        logger.debug("playwright is not installed, skipping fallback for: %s", url)
        return None

    try:
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            context = await browser.new_context()
            page = await context.new_page()

            await page.goto(url, timeout=timeout * 1000, wait_until="networkidle")
            html = await page.content()

            await browser.close()

        # trafilatura で HTML から本文抽出
        content = trafilatura.extract(html)
        return content
    except Exception:
        logger.debug("playwright extraction failed for: %s", url, exc_info=True)
        return None
