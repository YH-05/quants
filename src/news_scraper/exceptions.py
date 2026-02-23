"""news_scraper パッケージのカスタム例外階層.

HTTP ステータスコードに基づいた例外分類を提供する。
リトライ可能/不可能なエラーを明確に区別し、
上位レイヤーでの適切なエラーハンドリングを支援する。

例外階層
--------
::

    ScraperError
    ├── RetryableError          (429, 5xx, タイムアウト, 接続エラー)
    │   └── RateLimitError      (429)
    ├── PermanentError          (403, 404, パース失敗)
    │   └── BotDetectionError   (403 + ボット検知パターン)
    └── ContentExtractionError  (本文抽出失敗)

HTTP ステータスコード → 例外マッピング
--------------------------------------
| ステータス         | 例外クラス                           | リトライ |
|--------------------|--------------------------------------|----------|
| 403                | BotDetectionError / PermanentError   | No       |
| 404                | PermanentError                       | No       |
| 429                | RateLimitError                       | Yes      |
| 500, 502, 503, 504 | RetryableError                      | Yes      |
| タイムアウト       | RetryableError                       | Yes      |
"""


class ScraperError(Exception):
    """news_scraper パッケージの基底例外.

    全てのスクレイパー関連例外はこのクラスを継承する。
    上位レイヤーで一括キャッチする際に使用する。

    Parameters
    ----------
    message : str
        エラーメッセージ

    Examples
    --------
    >>> try:
    ...     raise ScraperError("スクレイピング中にエラーが発生しました")
    ... except ScraperError as e:
    ...     print(f"スクレイパーエラー: {e}")
    """

    pass


class RetryableError(ScraperError):
    """リトライで回復可能なエラー（429, 5xx, タイムアウト, 接続エラー）.

    一時的な障害で、時間をおいてリトライすることで
    回復する可能性があるエラーを表す。

    Parameters
    ----------
    message : str
        エラーメッセージ
    status_code : int | None
        HTTP ステータスコード（タイムアウト等の場合は None）
    retry_after : int | None
        リトライまでの待機秒数（Retry-After ヘッダーの値）

    Attributes
    ----------
    status_code : int | None
        HTTP ステータスコード
    retry_after : int | None
        リトライまでの待機秒数

    Examples
    --------
    >>> error = RetryableError("サーバーエラー", status_code=503)
    >>> error.status_code
    503
    >>> error.retry_after is None
    True
    """

    def __init__(
        self,
        message: str,
        *,
        status_code: int | None = None,
        retry_after: int | None = None,
    ) -> None:
        super().__init__(message)
        self.status_code = status_code
        self.retry_after = retry_after


class PermanentError(ScraperError):
    """リトライしても回復不可能なエラー（403, 404, パース失敗）.

    リトライしても結果が変わらない、永続的なエラーを表す。
    エラー原因の調査・修正が必要。

    Parameters
    ----------
    message : str
        エラーメッセージ
    status_code : int | None
        HTTP ステータスコード（パース失敗等の場合は None）

    Attributes
    ----------
    status_code : int | None
        HTTP ステータスコード

    Examples
    --------
    >>> error = PermanentError("Not Found", status_code=404)
    >>> error.status_code
    404
    """

    def __init__(
        self,
        message: str,
        *,
        status_code: int | None = None,
    ) -> None:
        super().__init__(message)
        self.status_code = status_code


class RateLimitError(RetryableError):
    """レート制限エラー（HTTP 429）.

    サーバーのレート制限に達した場合のエラー。
    Retry-After ヘッダーの値を尊重してリトライする。

    Parameters
    ----------
    message : str
        エラーメッセージ
    status_code : int | None
        HTTP ステータスコード（通常は 429）
    retry_after : int | None
        リトライまでの待機秒数（Retry-After ヘッダーの値）

    Examples
    --------
    >>> error = RateLimitError("Too Many Requests", status_code=429, retry_after=60)
    >>> error.status_code
    429
    >>> error.retry_after
    60
    """

    pass


class BotDetectionError(PermanentError):
    """ボット検知によるブロック（HTTP 403 + 特定パターン）.

    サーバー側のボット検知機構によってアクセスが
    ブロックされた場合のエラー。User-Agent の変更や
    プロキシの切り替え等の対策が必要。

    Parameters
    ----------
    message : str
        エラーメッセージ
    status_code : int | None
        HTTP ステータスコード（通常は 403）

    Examples
    --------
    >>> error = BotDetectionError("ボット検知によりブロックされました", status_code=403)
    >>> error.status_code
    403
    >>> isinstance(error, PermanentError)
    True
    """

    pass


class ContentExtractionError(ScraperError):
    """本文抽出失敗.

    ニュース記事の本文を HTML から抽出する際に
    失敗した場合のエラー。ページ構造の変更や
    予期しないフォーマットが原因。

    Parameters
    ----------
    message : str
        エラーメッセージ

    Examples
    --------
    >>> try:
    ...     raise ContentExtractionError("本文要素が見つかりません")
    ... except ScraperError as e:
    ...     print(f"抽出エラー: {e}")
    """

    pass
