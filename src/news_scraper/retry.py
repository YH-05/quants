"""news_scraper 用リトライデコレータ・エラー分類ユーティリティ.

tenacity ベースのリトライデコレータと、HTTP ステータスコードに基づく
エラー分類関数を提供する。

リトライ戦略
-----------
| パラメータ     | デフォルト値 | 説明                               |
|---------------|-------------|-------------------------------------|
| 最大試行回数   | 3           | ``stop_after_attempt(3)``          |
| 初回待機       | 1秒         | ``wait_exponential(multiplier=1)`` |
| 最大待機       | 30秒        | ``max=30.0``                       |
| ジッター       | 0〜1秒      | ``wait_random(0, 1)``              |
| リトライ条件   | RetryableError のみ | PermanentError ではリトライしない |

HTTP ステータスコード → 例外マッピング
--------------------------------------
| ステータス          | 例外クラス         | リトライ |
|--------------------|--------------------|----------|
| 429                | RateLimitError     | Yes      |
| 403                | BotDetectionError  | No       |
| 404                | PermanentError     | No       |
| 500, 502, 503, 504 | RetryableError    | Yes      |
| その他              | PermanentError    | No       |
"""

from typing import Any

import tenacity

from utils_core.logging import get_logger

from .exceptions import (
    BotDetectionError,
    PermanentError,
    RateLimitError,
    RetryableError,
    ScraperError,
)

logger = get_logger(__name__)


def create_retry_decorator(
    max_attempts: int = 3,
    base_wait: float = 1.0,
    max_wait: float = 30.0,
) -> Any:
    """news_scraper 用リトライデコレータを生成する.

    RetryableError（およびそのサブクラス）が発生した場合のみリトライし、
    指数バックオフ + ジッターで待機する。PermanentError やその他の例外では
    リトライせずに即座に再送出する。

    Parameters
    ----------
    max_attempts : int
        最大試行回数（デフォルト: 3）
    base_wait : float
        指数バックオフの基底待機時間（秒、デフォルト: 1.0）
    max_wait : float
        最大待機時間（秒、デフォルト: 30.0）

    Returns
    -------
    Any
        tenacity リトライデコレータ

    Examples
    --------
    >>> retry = create_retry_decorator(max_attempts=3)
    >>> @retry
    ... def fetch_data():
    ...     # RetryableError が発生した場合、最大3回リトライ
    ...     pass
    """
    return tenacity.retry(
        retry=tenacity.retry_if_exception_type(RetryableError),
        stop=tenacity.stop_after_attempt(max_attempts),
        wait=tenacity.wait_exponential(multiplier=base_wait, max=max_wait)
        + tenacity.wait_random(0, 1),
        before_sleep=_log_retry,
        reraise=True,
    )


def classify_http_error(status_code: int, response: Any) -> ScraperError:
    """HTTP ステータスコードからエラーを分類する.

    ステータスコードに応じて適切な例外クラスのインスタンスを返す。
    リトライ可能なエラー（429, 5xx）は RetryableError 系、
    リトライ不可能なエラー（403, 404 等）は PermanentError 系として分類する。

    Parameters
    ----------
    status_code : int
        HTTP ステータスコード
    response : Any
        HTTP レスポンスオブジェクト（Retry-After ヘッダの取得に使用）

    Returns
    -------
    ScraperError
        分類された例外インスタンス

    Examples
    --------
    >>> from unittest.mock import MagicMock
    >>> resp = MagicMock()
    >>> resp.headers = {"Retry-After": "60"}
    >>> error = classify_http_error(429, resp)
    >>> isinstance(error, RateLimitError)
    True
    >>> error.retry_after
    60
    """
    if status_code == 429:
        retry_after_f = _parse_retry_after(response)
        retry_after: int | None = (
            int(retry_after_f) if retry_after_f is not None else None
        )
        return RateLimitError(
            f"Rate limited ({status_code})",
            status_code=429,
            retry_after=retry_after,
        )
    elif status_code == 403:
        return BotDetectionError(
            f"Blocked ({status_code})",
            status_code=403,
        )
    elif status_code == 404:
        return PermanentError(
            f"Not found ({status_code})",
            status_code=404,
        )
    elif status_code >= 500:
        return RetryableError(
            f"Server error ({status_code})",
            status_code=status_code,
        )
    else:
        return PermanentError(
            f"HTTP {status_code}",
            status_code=status_code,
        )


def _parse_retry_after(response: Any) -> float | None:
    """Retry-After ヘッダをパースして秒数を返す.

    レスポンスの Retry-After ヘッダから待機秒数を取得する。
    ヘッダが存在しない場合やパースに失敗した場合は None を返す。

    Parameters
    ----------
    response : Any
        HTTP レスポンスオブジェクト（headers 属性を持つ）

    Returns
    -------
    float | None
        待機秒数、またはパース不可の場合は None

    Examples
    --------
    >>> from unittest.mock import MagicMock
    >>> resp = MagicMock()
    >>> resp.headers = {"Retry-After": "120"}
    >>> _parse_retry_after(resp)
    120.0
    >>> resp.headers = {}
    >>> _parse_retry_after(resp) is None
    True
    """
    if response is None:
        return None

    if not hasattr(response, "headers"):
        return None

    retry_after_value = response.headers.get("Retry-After")
    if retry_after_value is None:
        return None

    try:
        return float(retry_after_value)
    except (ValueError, TypeError):
        logger.debug(
            "Retry-After ヘッダのパースに失敗",
            retry_after_value=retry_after_value,
        )
        return None


def _log_retry(retry_state: tenacity.RetryCallState) -> None:
    """リトライ前のログ出力.

    tenacity の before_sleep コールバックとして使用し、
    リトライ試行回数と発生した例外をログに出力する。

    Parameters
    ----------
    retry_state : tenacity.RetryCallState
        tenacity のリトライ状態オブジェクト

    Examples
    --------
    >>> # tenacity が内部的に呼び出す（直接呼び出しは通常不要）
    """
    exception = retry_state.outcome.exception()  # type: ignore[union-attr]
    logger.warning(
        "リトライ実行",
        attempt_number=retry_state.attempt_number,
        exception=str(exception),
    )
