"""型定義モジュール."""

import random
from dataclasses import dataclass, field


@dataclass
class Article:
    """ニュース記事を表すデータクラス.

    Attributes
    ----------
    title : str
        記事タイトル
    url : str
        記事 URL
    published : str
        公開日時（ISO 8601 形式）
    summary : str
        記事要約
    category : str
        カテゴリ
    source : str
        ソース（cnbc, nasdaq）
    content : str
        記事本文
    ticker : str
        関連銘柄コード
    author : str
        著者名
    article_id : str
        記事固有 ID（重複排除用）
    metadata : dict
        ソース固有の追加データ
    """

    title: str
    url: str
    published: str = ""
    summary: str = ""
    category: str = ""
    source: str = ""
    content: str = ""
    ticker: str = ""
    author: str = ""
    article_id: str = ""
    metadata: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        """辞書形式に変換する."""
        return {
            "title": self.title,
            "url": self.url,
            "published": self.published,
            "summary": self.summary,
            "category": self.category,
            "source": self.source,
            "content": self.content,
            "ticker": self.ticker,
            "author": self.author,
            "article_id": self.article_id,
            "metadata": self.metadata,
        }


@dataclass
class ScraperConfig:
    """スクレイパー設定.

    Attributes
    ----------
    impersonate : str
        偽装するブラウザ（chrome131, safari, firefox）
    proxy : str | None
        プロキシ URL
    delay : float
        リクエスト間の待機秒数
    jitter : float
        delay +/- jitter（秒）のランダム化幅
    timeout : int
        タイムアウト秒数
    include_content : bool
        本文を取得するか
    use_playwright : bool
        Playwright を使用するか（CNBC サイトマップ用）
    max_concurrency : int
        RSS/API の最大同時リクエスト数
    max_concurrency_content : int
        本文取得の最大同時リクエスト数
    max_retries : int
        リトライ回数
    """

    impersonate: str = "chrome131"
    proxy: str | None = None
    delay: float = 1.0
    jitter: float = 0.5
    timeout: int = 30
    include_content: bool = False
    use_playwright: bool = True
    max_concurrency: int = 5
    max_concurrency_content: int = 3
    max_retries: int = 3


def get_delay(config: ScraperConfig) -> float:
    """ジッター付き遅延時間を計算する.

    Parameters
    ----------
    config : ScraperConfig
        スクレイパー設定

    Returns
    -------
    float
        delay +/- jitter の範囲でランダムに計算された遅延時間（秒）
    """
    return config.delay + random.uniform(-config.jitter, config.jitter)  # nosec B311


# カテゴリ定義
CNBC_FEEDS: dict[str, int] = {
    # 主要カテゴリ
    "top_news": 100003114,
    "world_news": 100727362,
    "us_news": 15837362,
    "asia_news": 19832390,
    "europe_news": 19794221,
    # ビジネス
    "business": 10001147,
    "earnings": 15839135,
    "commentary": 100370673,
    "economy": 20910258,
    # マーケット
    "finance": 10000664,
    "investing": 15839069,
    "financial_advisors": 100646281,
    "buffett_watch": 19206666,
    "trader_talk": 20409666,
    "futures_now": 100004038,
    "options_action": 28282083,
    "bonds": 100003241,
    "commodities": 100003242,
    # テック
    "technology": 19854910,
    # 産業
    "energy": 19836768,
    "health_care": 10000108,
    "real_estate": 10000115,
    "autos": 10000101,
    # パーソナルファイナンス
    "personal_finance": 21324812,
    "wealth": 10001054,
    "taxes": 10000117,
    # その他
    "politics": 10000113,
    "law": 10000114,
    "travel": 10000739,
    "charting_asia": 23103686,
}

CNBC_QUANT_CATEGORIES: list[str] = [
    "economy",
    "finance",
    "investing",
    "earnings",
    "bonds",
    "commodities",
    "technology",
    "energy",
]

NASDAQ_CATEGORIES: list[str] = [
    "Markets",
    "Technology",
    "Earnings",
    "Commodities",
    "Currencies",
    "Stocks",
    "ETFs",
    "IPOs",
    "Economy",
    "Investing",
    "Personal-Finance",
    "Retirement",
    "World",
    "Politics",
]

NASDAQ_QUANT_CATEGORIES: list[str] = [
    "Markets",
    "Earnings",
    "Economy",
    "Commodities",
    "Currencies",
    "Technology",
    "Stocks",
]
