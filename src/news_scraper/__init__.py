"""金融ニューススクレイパーパッケージ.

CNBC と NASDAQ から金融ニュースを収集するためのパッケージ。
クオンツ分析用のニュースデータ収集に使用。

Examples
--------
>>> from news_scraper import collect_financial_news
>>> df = collect_financial_news(
...     sources=["cnbc", "nasdaq"],
...     tickers=["AAPL", "MSFT"],
... )

>>> # CNBC 過去記事収集
>>> from datetime import datetime
>>> from news_scraper import collect_cnbc_historical
>>> df = collect_cnbc_historical(
...     start_date=datetime(2024, 1, 1),
...     end_date=datetime(2024, 1, 7),
... )
"""

# AIDEV-NOTE: news_scraper.Article（dataclass）と news.Article（Pydantic BaseModel）は
# 同名だが完全に別の型。同一ファイルで使用する場合はエイリアスを推奨:
# from news_scraper.types import Article as ScraperArticle
# from news.core.article import Article as NewsArticle

from .async_core import RateLimiter, gather_with_errors
from .async_unified import async_collect_financial_news
from .cnbc import (
    async_collect_historical_news as async_collect_cnbc_historical,
)
from .cnbc import (
    async_fetch_article_content as async_fetch_cnbc_content,
)
from .cnbc import (
    async_fetch_multiple_categories as async_fetch_cnbc_categories,
)
from .cnbc import (
    async_fetch_rss_feed as async_fetch_cnbc_rss,
)
from .cnbc import (
    collect_historical_news as collect_cnbc_historical,
)
from .cnbc import (
    fetch_article_content as fetch_cnbc_content,
)
from .cnbc import (
    fetch_multiple_categories as fetch_cnbc_categories,
)
from .cnbc import (
    fetch_rss_feed as fetch_cnbc_rss,
)
from .exceptions import (
    BotDetectionError,
    ContentExtractionError,
    PermanentError,
    RateLimitError,
    RetryableError,
    ScraperError,
)
from .nasdaq import (
    async_collect_historical_news as async_collect_nasdaq_historical,
)
from .nasdaq import (
    async_collect_nasdaq_news,
    collect_nasdaq_news,
)
from .nasdaq import (
    async_fetch_article_content as async_fetch_nasdaq_content,
)
from .nasdaq import (
    async_fetch_multiple_categories as async_fetch_nasdaq_categories,
)
from .nasdaq import (
    async_fetch_multiple_stocks as async_fetch_nasdaq_stocks,
)
from .nasdaq import (
    async_fetch_rss_feed as async_fetch_nasdaq_rss,
)
from .nasdaq import (
    async_fetch_stock_news_api_paginated as async_fetch_nasdaq_stock_news_paginated,
)
from .nasdaq import (
    collect_historical_news as collect_nasdaq_historical,
)
from .nasdaq import (
    fetch_article_content as fetch_nasdaq_content,
)
from .nasdaq import (
    fetch_multiple_categories as fetch_nasdaq_categories,
)
from .nasdaq import (
    fetch_multiple_stocks as fetch_nasdaq_stocks,
)
from .nasdaq import (
    fetch_rss_feed as fetch_nasdaq_rss,
)
from .nasdaq import (
    fetch_stock_news_api as fetch_nasdaq_stock_news,
)
from .nasdaq import (
    fetch_stock_news_api_paginated as fetch_nasdaq_stock_news_paginated,
)
from .session import create_async_session, create_session
from .types import (
    CNBC_FEEDS,
    CNBC_QUANT_CATEGORIES,
    NASDAQ_CATEGORIES,
    NASDAQ_QUANT_CATEGORIES,
    Article,
    ScraperConfig,
    get_delay,
)
from .unified import collect_financial_news, collect_financial_news_fast
from .yfinance import collect_yfinance_news
from .yfinance import fetch_article_content as fetch_yf_content
from .yfinance import fetch_multiple_searches as fetch_yf_searches
from .yfinance import fetch_multiple_tickers as fetch_yf_tickers
from .yfinance import fetch_search_news as fetch_yf_search_news
from .yfinance import fetch_ticker_news as fetch_yf_ticker_news

__all__ = [
    # カテゴリ定義
    "CNBC_FEEDS",
    "CNBC_QUANT_CATEGORIES",
    "NASDAQ_CATEGORIES",
    "NASDAQ_QUANT_CATEGORIES",
    # 型・設定
    "Article",
    "BotDetectionError",
    "ContentExtractionError",
    "PermanentError",
    "RateLimitError",
    # 非同期コア
    "RateLimiter",
    "RetryableError",
    "ScraperConfig",
    # 例外
    "ScraperError",
    # CNBC
    "async_collect_cnbc_historical",
    # 統合
    "async_collect_financial_news",
    # NASDAQ
    "async_collect_nasdaq_historical",
    "async_collect_nasdaq_news",
    "async_fetch_cnbc_categories",
    "async_fetch_cnbc_content",
    "async_fetch_cnbc_rss",
    "async_fetch_nasdaq_categories",
    "async_fetch_nasdaq_content",
    "async_fetch_nasdaq_rss",
    "async_fetch_nasdaq_stock_news_paginated",
    "async_fetch_nasdaq_stocks",
    "collect_cnbc_historical",
    "collect_financial_news",
    "collect_financial_news_fast",
    "collect_nasdaq_historical",
    "collect_nasdaq_news",
    # yfinance
    "collect_yfinance_news",
    # セッション
    "create_async_session",
    "create_session",
    "fetch_cnbc_categories",
    "fetch_cnbc_content",
    "fetch_cnbc_rss",
    "fetch_nasdaq_categories",
    "fetch_nasdaq_content",
    "fetch_nasdaq_rss",
    "fetch_nasdaq_stock_news",
    "fetch_nasdaq_stock_news_paginated",
    "fetch_nasdaq_stocks",
    "fetch_yf_content",
    "fetch_yf_search_news",
    "fetch_yf_searches",
    "fetch_yf_ticker_news",
    "fetch_yf_tickers",
    "gather_with_errors",
    "get_delay",
]

__version__ = "0.1.0"
