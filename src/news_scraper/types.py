"""型定義モジュール."""

import random
from dataclasses import dataclass, field
from typing import Literal


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
        Playwright を使用するか（CNBC サイトマップ用・NASDAQ 過去記事取得用）
    max_concurrency : int
        RSS/API の最大同時リクエスト数
    max_concurrency_content : int
        本文取得の最大同時リクエスト数
    max_retries : int
        リトライ回数
    """

    impersonate: Literal["chrome", "chrome131", "safari", "firefox"] = "chrome131"
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

# 日本語 RSS フィード定数

TOYOKEIZAI_FEEDS: dict[str, str] = {
    "all": "https://toyokeizai.net/list/feed/rss",
}

INVESTING_JP_FEEDS: dict[str, str] = {
    "forex": "https://jp.investing.com/rss/news_301.rss",
    "commodities": "https://jp.investing.com/rss/news_302.rss",
    "stocks": "https://jp.investing.com/rss/news_303.rss",
    "economy": "https://jp.investing.com/rss/news_304.rss",
    "bonds": "https://jp.investing.com/rss/news_305.rss",
}

YAHOO_JP_FEEDS: dict[str, str] = {
    "business": "https://news.yahoo.co.jp/rss/topics/business.xml",
    "economy": "https://news.yahoo.co.jp/rss/topics/economy.xml",
    "it": "https://news.yahoo.co.jp/rss/topics/it.xml",
}

JPX_FEEDS: dict[str, str] = {
    "news_release": "https://www.jpx.co.jp/corporate/news-releases/news-release.rss",
    "listing": "https://www.jpx.co.jp/listing/stocks/new/new.rss",
    "market_news": "https://www.jpx.co.jp/markets/equities/market-news/market-news.rss",
    "regulations": "https://www.jpx.co.jp/regulation/public-comment/public-comment.rss",
}

TDNET_BASE_URL: str = "https://webapi.yanoshin.jp/webapi/tdnet/list"

TDNET_DEFAULT_CODES: list[str] = [
    "7203",  # トヨタ自動車
    "6758",  # ソニーグループ
    "9984",  # ソフトバンクグループ
    "8306",  # 三菱UFJフィナンシャル・グループ
    "6861",  # キーエンス
    "6098",  # リクルートホールディングス
    "9432",  # 日本電信電話 (NTT)
    "6501",  # 日立製作所
    "8035",  # 東京エレクトロン
    "6902",  # デンソー
]

# yfinance 日本株プリセット

YFINANCE_JP_TICKERS: list[str] = [
    "7203.T",  # トヨタ自動車
    "6758.T",  # ソニーグループ
    "9984.T",  # ソフトバンクグループ
    "8306.T",  # 三菱UFJフィナンシャル・グループ
    "6861.T",  # キーエンス
    "6902.T",  # デンソー
    "9432.T",  # 日本電信電話 (NTT)
    "6501.T",  # 日立製作所
    "7741.T",  # HOYA
    "8035.T",  # 東京エレクトロン
    "6098.T",  # リクルートホールディングス
    "9433.T",  # KDDI
    "4063.T",  # 信越化学工業
    "6367.T",  # ダイキン工業
    "8058.T",  # 三菱商事
    "8031.T",  # 三井物産
    "6981.T",  # 村田製作所
    "7974.T",  # 任天堂
    "4519.T",  # 中外製薬
    "6594.T",  # 日本電産
    "8766.T",  # 東京海上ホールディングス
    "4568.T",  # 第一三共
    "6723.T",  # ルネサスエレクトロニクス
    "6857.T",  # アドバンテスト
    "9983.T",  # ファーストリテイリング
]

YFINANCE_JP_INDICES: list[str] = [
    "^N225",  # 日経平均株価
    "^TOPX",  # TOPIX
]
