"""academic パッケージのカスタム例外階層.

HTTP ステータスコードに基づいた例外分類を提供する。
リトライ可能/不可能なエラーを明確に区別し、
上位レイヤーでの適切なエラーハンドリングを支援する。

例外階層
--------
::

    AcademicError
    +-- RetryableError          (429, 5xx, タイムアウト, 接続エラー)
    |   +-- RateLimitError      (429)
    +-- PermanentError          (403, 404, パース失敗)
    |   +-- PaperNotFoundError  (404)
    +-- ParseError              (レスポンスのパース失敗)

HTTP ステータスコード -> 例外マッピング
--------------------------------------
| ステータス         | 例外クラス                          | リトライ |
|--------------------|-------------------------------------|----------|
| 404                | PaperNotFoundError                  | No       |
| 429                | RateLimitError                      | Yes      |
| 500, 502, 503, 504 | RetryableError                     | Yes      |
| その他 4xx         | PermanentError                      | No       |
| パース失敗         | ParseError                          | No       |
"""


class AcademicError(Exception):
    """academic パッケージの基底例外.

    全ての学術データ取得関連例外はこのクラスを継承する。
    上位レイヤーで一括キャッチする際に使用する。

    Parameters
    ----------
    message : str
        エラーメッセージ

    Examples
    --------
    >>> try:
    ...     raise AcademicError("データ取得中にエラーが発生しました")
    ... except AcademicError as e:
    ...     print(f"学術データエラー: {e}")
    """

    pass


class RetryableError(AcademicError):
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


class PermanentError(AcademicError):
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


class PaperNotFoundError(PermanentError):
    """論文が見つからないエラー（HTTP 404）.

    指定された arXiv ID や Semantic Scholar ID に対応する
    論文が存在しない場合のエラー。

    Parameters
    ----------
    message : str
        エラーメッセージ
    status_code : int | None
        HTTP ステータスコード（通常は 404）

    Examples
    --------
    >>> error = PaperNotFoundError("論文が見つかりません: 2301.00001", status_code=404)
    >>> error.status_code
    404
    >>> isinstance(error, PermanentError)
    True
    """

    pass


class ParseError(AcademicError):
    """レスポンスのパース失敗.

    API レスポンスや XML/JSON のパースに失敗した場合のエラー。
    API のレスポンスフォーマット変更やネットワーク上のデータ破損が原因。

    Parameters
    ----------
    message : str
        エラーメッセージ

    Examples
    --------
    >>> try:
    ...     raise ParseError("arXiv Atom フィードのパースに失敗しました")
    ... except AcademicError as e:
    ...     print(f"パースエラー: {e}")
    """

    pass


__all__ = [
    "AcademicError",
    "PaperNotFoundError",
    "ParseError",
    "PermanentError",
    "RateLimitError",
    "RetryableError",
]
