"""型定義モジュール.

ニュース記事エンベディングパイプラインで使用するデータクラスを定義する。

- ``ArticleRecord``: JSON 入力からのマッピング先
- ``PipelineConfig``: CLI 引数・デフォルト値の統一管理
- ``ExtractionResult``: 本文抽出結果の型安全な受け渡し
"""

from dataclasses import dataclass, field
from pathlib import Path

from database.db.connection import get_data_dir


@dataclass
class ArticleRecord:
    """JSON 入力からのマッピング先となる記事レコード.

    ``news_scraper.Article.to_dict()`` 形式の辞書から変換して使用する。

    Attributes
    ----------
    url : str
        記事 URL（必須、重複除去のキー）
    title : str
        記事タイトル（必須）
    published : str
        公開日時（ISO 8601 形式）
    summary : str
        記事要約
    category : str
        カテゴリ
    source : str
        ソース名（cnbc, nasdaq 等）
    ticker : str
        関連銘柄コード
    author : str
        著者名
    article_id : str
        記事固有 ID
    content : str
        記事本文
    extraction_method : str
        本文抽出方法（trafilatura / playwright / summary_fallback / failed）
    extracted_at : str
        本文抽出日時（ISO 8601 形式）
    json_file : str
        読み込み元 JSON ファイルパス
    """

    url: str
    title: str
    published: str = ""
    summary: str = ""
    category: str = ""
    source: str = ""
    ticker: str = ""
    author: str = ""
    article_id: str = ""
    content: str = ""
    extraction_method: str = ""
    extracted_at: str = ""
    json_file: str = ""


@dataclass
class PipelineConfig:
    """パイプライン設定.

    CLI 引数のデフォルト値を統一管理する。

    Attributes
    ----------
    news_dir : Path
        ニュース JSON の格納ディレクトリ
    chromadb_path : Path
        ChromaDB の永続化パス
    collection_name : str
        ChromaDB コレクション名（= embedding model 名）
    dummy_dim : int
        ダミーベクトルの次元数
    max_concurrency : int
        最大同時リクエスト数
    delay : float
        リクエスト間の待機秒数
    timeout : int
        タイムアウト秒数
    use_playwright_fallback : bool
        Playwright フォールバックを使用するか
    sources : list[str] | None
        対象ソースのフィルタリング（None で全ソース）
    """

    news_dir: Path = field(default_factory=lambda: get_data_dir() / "raw" / "news")
    chromadb_path: Path = field(default_factory=lambda: get_data_dir() / "chromadb")
    collection_name: str = "gemini-embedding-001"
    dummy_dim: int = 768
    max_concurrency: int = 3
    delay: float = 1.5
    timeout: int = 30
    use_playwright_fallback: bool = True
    sources: list[str] | None = None


@dataclass
class ExtractionResult:
    """本文抽出結果.

    抽出処理の結果を型安全に受け渡すためのデータクラス。

    Attributes
    ----------
    url : str
        対象記事の URL
    content : str
        抽出された本文テキスト
    method : str
        抽出方法（trafilatura / playwright / summary_fallback / failed）
    extracted_at : str
        抽出日時（ISO 8601 形式）
    error : str
        エラーメッセージ（エラー発生時のみ）
    """

    url: str
    content: str
    method: str
    extracted_at: str
    error: str = ""
