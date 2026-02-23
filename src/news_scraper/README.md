# news_scraper

金融ニューススクレイパーパッケージ。CNBC、NASDAQ、yfinance から金融ニュースを収集し、クオンツ分析用のデータセットを構築する。

## 特徴

- **ブラウザ偽装**: curl-cffi を使用してボット検知を回避
- **本文抽出**: trafilatura による高精度な記事本文抽出
- **カテゴリ別収集**: CNBC 30カテゴリ、NASDAQ 14カテゴリに対応
- **銘柄別収集**: NASDAQ API を使用した銘柄別ニュース取得
- **過去記事収集**: CNBC サイトマップからの過去記事収集（Playwright 使用）
- **yfinance ニュース**: yfinance Ticker / Search API を使用したニュース取得
- **プロキシ対応**: プロキシ経由でのアクセスに対応

## インストール

このパッケージは Quants プロジェクトの一部として含まれています。依存関係は `pyproject.toml` で管理されています。

```bash
# 依存関係のインストール
uv sync --all-extras

# Playwright ブラウザのインストール（過去記事収集に必要）
uv run playwright install chromium
```

## クイックスタート

### 基本的な使い方

```python
from news_scraper import collect_financial_news

# CNBC と NASDAQ から最新ニュースを収集
df = collect_financial_news()

print(f"収集記事数: {len(df)}")
print(df[["title", "source", "category"]].head())
```

### 銘柄別ニュースの収集

```python
from news_scraper import collect_financial_news

# 特定銘柄のニュースを収集
df = collect_financial_news(
    sources=["nasdaq"],
    tickers=["AAPL", "MSFT", "GOOGL", "NVDA", "AMZN"],
)
```

### 本文も含めて収集

```python
from news_scraper import collect_financial_news, ScraperConfig

config = ScraperConfig(
    include_content=True,  # 本文を取得
    delay=1.5,             # レート制限対策
)

df = collect_financial_news(
    config=config,
    output_dir="data/news",  # 結果を保存
)
```

## API リファレンス

### 統合関数

#### `collect_financial_news()`

複数ソースから金融ニュースを一括収集する。

```python
def collect_financial_news(
    sources: list[str] | None = None,           # ["cnbc", "nasdaq"]
    cnbc_categories: list[str] | None = None,   # CNBC カテゴリ
    nasdaq_categories: list[str] | None = None, # NASDAQ カテゴリ
    tickers: list[str] | None = None,           # 銘柄コード（NASDAQ）
    config: ScraperConfig | None = None,        # 設定
    output_dir: str | Path | None = None,       # 出力先
) -> pd.DataFrame:
```

**パラメータ:**

| パラメータ          | 型            | デフォルト            | 説明             |
| ------------------- | ------------- | --------------------- | ---------------- |
| `sources`           | list[str]     | `["cnbc", "nasdaq"]`  | 収集ソース       |
| `cnbc_categories`   | list[str]     | クオンツ向け8カテゴリ | CNBC カテゴリ    |
| `nasdaq_categories` | list[str]     | クオンツ向け7カテゴリ | NASDAQ カテゴリ  |
| `tickers`           | list[str]     | None                  | 銘柄コード       |
| `config`            | ScraperConfig | デフォルト設定        | スクレイパー設定 |
| `output_dir`        | str \| Path   | None                  | 出力ディレクトリ |

**戻り値:** `pd.DataFrame` - 収集した記事

**例:**

```python
# 基本的な使用
df = collect_financial_news()

# CNBC のみ、特定カテゴリ
df = collect_financial_news(
    sources=["cnbc"],
    cnbc_categories=["economy", "earnings", "technology"],
)

# NASDAQ 銘柄別
df = collect_financial_news(
    sources=["nasdaq"],
    nasdaq_categories=["Markets"],
    tickers=["AAPL", "MSFT"],
)

# ファイル出力付き
df = collect_financial_news(
    output_dir="data/financial_news",
)
# 出力: data/financial_news/news_YYYYMMDD_HHMMSS.json
#       data/financial_news/news_YYYYMMDD_HHMMSS.parquet
```

### CNBC 関数

#### `fetch_cnbc_categories()`

CNBC の複数カテゴリから RSS フィードを取得する。

```python
from news_scraper import create_session, fetch_cnbc_categories

session = create_session()
df = fetch_cnbc_categories(
    session,
    categories=["economy", "finance", "investing"],
    delay=0.5,
)
```

#### `collect_cnbc_historical()`

CNBC の過去記事をサイトマップから収集する。

```python
from datetime import datetime
from news_scraper import collect_cnbc_historical, ScraperConfig

# 1週間分の過去記事を収集
df = collect_cnbc_historical(
    start_date=datetime(2024, 1, 1),
    end_date=datetime(2024, 1, 7),
    config=ScraperConfig(
        include_content=True,  # 本文も取得
        delay=1.5,
    ),
    output_dir="data/cnbc_historical",
)
```

**注意:** 過去記事収集には Playwright が必要です。

```bash
uv run playwright install chromium
```

#### `fetch_cnbc_content()`

CNBC の記事本文を取得する。

```python
from news_scraper import create_session, fetch_cnbc_content

session = create_session()
content = fetch_cnbc_content(
    session,
    "https://www.cnbc.com/2024/01/15/example-article.html",
)

if content:
    print(f"タイトル: {content['title']}")
    print(f"本文: {content['content'][:500]}")
```

### NASDAQ 関数

#### `fetch_nasdaq_categories()`

NASDAQ の複数カテゴリから RSS フィードを取得する。

```python
from news_scraper import create_session, fetch_nasdaq_categories

session = create_session()
df = fetch_nasdaq_categories(
    session,
    categories=["Markets", "Earnings", "Technology"],
    delay=0.5,
)
```

#### `fetch_nasdaq_stocks()`

NASDAQ API から銘柄別ニュースを取得する。

```python
from news_scraper import create_session, fetch_nasdaq_stocks

session = create_session()
df = fetch_nasdaq_stocks(
    session,
    tickers=["AAPL", "MSFT", "GOOGL", "NVDA", "AMZN"],
    limit=20,  # 各銘柄の取得件数
    delay=1.0,
)
```

#### `collect_nasdaq_news()`

NASDAQ ニュースを一括収集する。

```python
from news_scraper import collect_nasdaq_news

df = collect_nasdaq_news(
    categories=["Markets", "Earnings"],
    tickers=["AAPL", "MSFT"],
    output_dir="data/nasdaq_news",
)
```

### yfinance 関数

yfinance を使用したニュース取得。**Ticker 方式**（銘柄ページのニュース）と **Search 方式**（キーワード検索）の 2 つの取得方式を提供する。

| 方式 | 関数 | データソース | 特徴 |
| ---- | ---- | ------------ | ---- |
| Ticker | `fetch_yf_ticker_news()` | `yf.Ticker(ticker).news` | 銘柄固有のニュース、summary あり |
| Search | `fetch_yf_search_news()` | `yf.Search(query).news` | キーワード検索、relatedTickers あり |

#### `fetch_yf_ticker_news()`

単一ティッカーのニュース記事を取得する。`yf.Ticker` API を使用し、`Article` データモデルに変換して返す。

```python
from news_scraper import create_session, fetch_yf_ticker_news

session = create_session()
articles = fetch_yf_ticker_news(session, "AAPL")

for article in articles:
    print(f"{article.published} - {article.title}")
    print(f"  URL: {article.url}")
    print(f"  Source: {article.source}")  # "yfinance_ticker"
```

**パラメータ:**

| パラメータ | 型      | デフォルト | 説明                               |
| ---------- | ------- | ---------- | ---------------------------------- |
| `session`  | Session | (必須)     | HTTP セッション（curl_cffi）       |
| `ticker`   | str     | (必須)     | ティッカーシンボル（例: `"AAPL"`, `"7203.T"`） |
| `timeout`  | int     | `30`       | タイムアウト秒数                   |

**戻り値:** `list[Article]` - 記事リスト（`published` 降順）

#### `fetch_yf_search_news()`

キーワード検索でニュース記事を取得する。`yf.Search` API を使用する。

```python
from news_scraper import create_session, fetch_yf_search_news

session = create_session()
articles = fetch_yf_search_news(session, "AI stocks", news_count=30)

for article in articles:
    print(f"{article.published} - {article.title}")
    print(f"  Tickers: {article.ticker}")  # 関連銘柄（カンマ区切り）
    print(f"  Source: {article.source}")    # "yfinance_search"
```

**パラメータ:**

| パラメータ   | 型      | デフォルト | 説明                         |
| ------------ | ------- | ---------- | ---------------------------- |
| `session`    | Session | (必須)     | HTTP セッション（curl_cffi） |
| `query`      | str     | (必須)     | 検索クエリ（例: `"AAPL"`, `"AI stocks"`） |
| `news_count` | int     | `50`       | 取得するニュース数           |
| `timeout`    | int     | `30`       | タイムアウト秒数             |

**戻り値:** `list[Article]` - 記事リスト（`published` 降順）

#### `fetch_yf_tickers()`

複数ティッカーのニュースを逐次取得する。各ティッカーに対して `fetch_yf_ticker_news()` を呼び出し、ジッター付き遅延を挟む。

```python
from news_scraper import create_session, fetch_yf_tickers
from news_scraper import ScraperConfig

session = create_session()
config = ScraperConfig(delay=1.0, jitter=0.5)
df = fetch_yf_tickers(session, ["AAPL", "MSFT", "GOOG"], config=config)
print(df[["ticker", "title"]].head())
```

**パラメータ:**

| パラメータ | 型             | デフォルト | 説明                         |
| ---------- | -------------- | ---------- | ---------------------------- |
| `session`  | Session        | (必須)     | HTTP セッション（curl_cffi） |
| `tickers`  | list[str]      | (必須)     | ティッカーリスト             |
| `config`   | ScraperConfig  | `None`     | スクレイパー設定             |
| `timeout`  | int            | `30`       | タイムアウト秒数             |

**戻り値:** `pd.DataFrame` - 全ティッカーの記事を結合した DataFrame

#### `fetch_yf_searches()`

複数クエリのニュースを逐次取得する。各クエリに対して `fetch_yf_search_news()` を呼び出す。

```python
from news_scraper import create_session, fetch_yf_searches
from news_scraper import ScraperConfig

session = create_session()
config = ScraperConfig(delay=1.0)
df = fetch_yf_searches(
    session,
    ["AI stocks", "EV market", "crypto"],
    news_count=30,
    config=config,
)
print(df[["category", "title"]].head())
```

**パラメータ:**

| パラメータ   | 型             | デフォルト | 説明                         |
| ------------ | -------------- | ---------- | ---------------------------- |
| `session`    | Session        | (必須)     | HTTP セッション（curl_cffi） |
| `queries`    | list[str]      | (必須)     | 検索クエリリスト             |
| `news_count` | int            | `50`       | 各クエリの取得ニュース数     |
| `config`     | ScraperConfig  | `None`     | スクレイパー設定             |
| `delay`      | float          | `1.0`      | リクエスト間の基本遅延秒数   |
| `timeout`    | int            | `30`       | タイムアウト秒数             |

**戻り値:** `pd.DataFrame` - 全クエリの記事を結合した DataFrame

#### `collect_yfinance_news()`

yfinance ニュースを一括収集する。ティッカー別取得とクエリ別取得を統合し、重複除去・本文取得・ファイル保存をオーケストレーションする。

```python
from news_scraper import collect_yfinance_news, ScraperConfig

# Ticker 方式で収集
df = collect_yfinance_news(tickers=["AAPL", "MSFT", "GOOGL"])

# Search 方式で収集
df = collect_yfinance_news(queries=["AI stocks", "EV market"])

# 両方を組み合わせ
df = collect_yfinance_news(
    tickers=["AAPL", "MSFT"],
    queries=["AI stocks"],
)

# 本文も取得 + ファイル保存
config = ScraperConfig(include_content=True, delay=1.5)
df = collect_yfinance_news(
    tickers=["AAPL"],
    config=config,
    output_dir="data/raw/yfinance",
)
# 出力: data/raw/yfinance/yfinance_YYYYMMDD_HHMMSS.json
#       data/raw/yfinance/yfinance_YYYYMMDD_HHMMSS.parquet
```

**パラメータ:**

| パラメータ   | 型             | デフォルト | 説明                               |
| ------------ | -------------- | ---------- | ---------------------------------- |
| `tickers`    | list[str]      | `None`     | ティッカーリスト（None でスキップ） |
| `queries`    | list[str]      | `None`     | 検索クエリリスト（None でスキップ） |
| `news_count` | int            | `50`       | 各クエリの取得ニュース数           |
| `config`     | ScraperConfig  | `None`     | スクレイパー設定                   |
| `output_dir` | str \| Path    | `None`     | 出力ディレクトリ                   |

**戻り値:** `pd.DataFrame` - 収集した全記事（`article_id` による重複除去済み）

#### 統合関数からの利用

`collect_financial_news()` の `sources` パラメータに `"yfinance_ticker"` / `"yfinance_search"` を指定して利用することもできる。

```python
from news_scraper import collect_financial_news

# yfinance Ticker ニュースを統合関数経由で取得
df = collect_financial_news(
    sources=["yfinance_ticker"],
    yf_tickers=["AAPL", "MSFT"],
)

# yfinance Search ニュースを統合関数経由で取得
df = collect_financial_news(
    sources=["yfinance_search"],
    yf_queries=["AI stocks", "EV market"],
    yf_news_count=30,
)

# CNBC + NASDAQ + yfinance を全て収集
df = collect_financial_news(
    sources=["cnbc", "nasdaq", "yfinance_ticker"],
    tickers=["AAPL", "MSFT"],      # NASDAQ 銘柄別
    yf_tickers=["AAPL", "MSFT"],   # yfinance Ticker
)
```

#### yfinance エラーハンドリング

yfinance 関数は `news_scraper` 共通のカスタム例外階層を使用する。リトライデコレータ（tenacity ベース、最大 3 回、指数バックオフ + ジッター）が `fetch_yf_ticker_news()` と `fetch_yf_search_news()` に適用されている。

**例外階層:**

```
ScraperError
├── RetryableError          (429, 5xx, タイムアウト, 接続エラー)
│   └── RateLimitError      (429)
├── PermanentError          (403, 404, パース失敗)
│   └── BotDetectionError   (403 + ボット検知パターン)
└── ContentExtractionError  (本文抽出失敗)
```

**リトライ戦略:**

| パラメータ   | 値                  | 説明                                |
| ------------ | ------------------- | ----------------------------------- |
| 最大試行回数 | 3                   | `stop_after_attempt(3)`             |
| 初回待機     | 1 秒                | `wait_exponential(multiplier=1)`    |
| 最大待機     | 30 秒               | `max=30.0`                          |
| ジッター     | 0 - 1 秒            | `wait_random(0, 1)`                 |
| リトライ条件 | `RetryableError` のみ | `PermanentError` ではリトライしない |

**エラーハンドリング例:**

```python
from news_scraper import (
    create_session,
    fetch_yf_ticker_news,
    RetryableError,
    PermanentError,
    ScraperError,
)

session = create_session()
try:
    articles = fetch_yf_ticker_news(session, "AAPL")
except PermanentError as e:
    print(f"恒久的エラー（リトライ不可）: {e}")
    # 403, 404 など
except RetryableError as e:
    print(f"一時的エラー（リトライ上限到達）: {e}")
    # 429, 5xx, 接続エラー
except ScraperError as e:
    print(f"その他のスクレイパーエラー: {e}")
```

> **注意:** バッチ取得関数（`fetch_yf_tickers()`, `fetch_yf_searches()`）は個別のエラーをスキップし、バッチ全体は中断しない。失敗した銘柄/クエリはログに警告出力される。

#### yfinance DuckDB テーブル構成

`collect_yfinance_news()` が返す DataFrame を DuckDB に格納するには `yfinance_news_to_duckdb()` を使用する。

**テーブル構成:**

| テーブル名               | 用途                  | key_columns                  |
| ------------------------ | --------------------- | ---------------------------- |
| `yfinance_ticker_news`   | Ticker 方式のニュース | `["article_id", "ticker"]`   |
| `yfinance_search_news`   | Search 方式のニュース | `["article_id", "category"]` |

**使用例:**

```python
from pathlib import Path
from news_scraper import collect_yfinance_news
from src.database.store_news_json_to_duckdb import yfinance_news_to_duckdb

# Ticker ニュースを収集して DuckDB に格納
df_ticker = collect_yfinance_news(tickers=["AAPL", "MSFT"])
yfinance_news_to_duckdb(
    df=df_ticker,
    duckdb_path=Path("data/raw.duckdb"),
    table_name="yfinance_ticker_news",
    key_columns=["article_id", "ticker"],
)

# Search ニュースを収集して DuckDB に格納
df_search = collect_yfinance_news(queries=["AI stocks"])
yfinance_news_to_duckdb(
    df=df_search,
    duckdb_path=Path("data/raw.duckdb"),
    table_name="yfinance_search_news",
    key_columns=["article_id", "category"],
)
```

**DataFrame カラム（yfinance 固有）:**

| カラム       | 型   | 説明                                          |
| ------------ | ---- | --------------------------------------------- |
| `title`      | str  | 記事タイトル                                  |
| `url`        | str  | 記事 URL                                      |
| `published`  | str  | 公開日時（ISO 8601）                          |
| `summary`    | str  | 記事要約（Ticker 方式のみ）                   |
| `category`   | str  | カテゴリ（Search 方式: クエリ文字列）         |
| `source`     | str  | `"yfinance_ticker"` or `"yfinance_search"`    |
| `content`    | str  | 記事本文（`include_content=True` 時のみ）     |
| `ticker`     | str  | 銘柄コード（Search: カンマ区切りの関連銘柄）  |
| `author`     | str  | 著者名（Search 方式: publisher）              |
| `article_id` | str  | 記事固有 ID（Ticker: `id`, Search: `uuid`）   |
| `metadata`   | dict | ソース固有データ（`contentType`, `finance` 等）|

### 非同期 API（async）

#### `async_collect_financial_news()`

`collect_financial_news()` の非同期版。CNBC カテゴリ取得・NASDAQ カテゴリ取得・NASDAQ 銘柄取得を全て並列実行し、大幅に高速化する。

```python
import asyncio
from news_scraper import async_collect_financial_news, ScraperConfig

async def main():
    # 基本的な使用（全ソースを並列収集）
    df = await async_collect_financial_news(
        sources=["cnbc", "nasdaq"],
        tickers=["AAPL", "MSFT", "GOOGL"],
    )
    print(f"収集記事数: {len(df)}")

    # 本文も並列取得
    config = ScraperConfig(
        include_content=True,
        delay=1.5,
        max_concurrency_content=5,  # 本文取得の同時実行数
    )
    df = await async_collect_financial_news(
        config=config,
        output_dir="data/news",
    )

asyncio.run(main())
```

**パラメータ:** `collect_financial_news()` と同一のシグネチャ。

#### `collect_financial_news_fast()`

`async_collect_financial_news()` の同期ラッパー。`asyncio.run()` 経由で非同期版を実行する。同期版 `collect_financial_news()` と同じインターフェースで、内部では並列実行により高速に動作する。

```python
from news_scraper import collect_financial_news_fast, ScraperConfig

# collect_financial_news() と同じ使い方で高速化
df = collect_financial_news_fast(
    sources=["cnbc", "nasdaq"],
    tickers=["AAPL", "MSFT", "GOOGL", "NVDA", "AMZN"],
)

# 本文取得も並列化
config = ScraperConfig(
    include_content=True,
    max_concurrency=5,          # RSS/API の同時リクエスト数
    max_concurrency_content=3,  # 本文取得の同時リクエスト数
)
df = collect_financial_news_fast(config=config)
```

**パラメータ:** `collect_financial_news()` と同一のシグネチャ。

> **注意:** Jupyter Notebook 環境では `collect_financial_news_fast()` は使用できません（後述の「Jupyter での使用」を参照）。

#### Jupyter での使用

Jupyter Notebook / IPython 環境では、既にイベントループが実行中のため `asyncio.run()` が `RuntimeError` を発生させます。`collect_financial_news_fast()` は内部で `asyncio.run()` を使用しているため、Jupyter 環境では直接使用できません。

**方法 1: `await` で直接呼び出す（推奨）**

```python
# Jupyter セル内で直接 await を使用
from news_scraper import async_collect_financial_news

df = await async_collect_financial_news(
    sources=["cnbc", "nasdaq"],
    tickers=["AAPL", "MSFT"],
)
```

**方法 2: `nest_asyncio` を使用する**

```python
import nest_asyncio
nest_asyncio.apply()

from news_scraper import collect_financial_news_fast

# nest_asyncio 適用後は asyncio.run() が使用可能
df = collect_financial_news_fast(
    sources=["cnbc", "nasdaq"],
    tickers=["AAPL", "MSFT"],
)
```

#### 期待されるパフォーマンス改善

| シナリオ             | 同期版（逐次） | 非同期版（並列） | 改善率 |
| -------------------- | -------------- | ---------------- | ------ |
| CNBC + NASDAQ カテゴリ | ~15秒          | ~4秒             | ~3-4x  |
| 10銘柄ニュース       | ~15秒          | ~5秒             | ~3x    |
| 50記事本文取得       | ~75秒          | ~20秒            | ~3-4x  |

### 設定

#### `ScraperConfig`

スクレイパーの動作を設定するデータクラス。

```python
from news_scraper import ScraperConfig

config = ScraperConfig(
    impersonate="chrome",           # ブラウザ偽装（chrome, safari, firefox）
    proxy=None,                     # プロキシ URL
    delay=1.0,                      # リクエスト間隔（秒）
    timeout=30,                     # タイムアウト（秒）
    include_content=False,          # 本文を取得するか
    use_playwright=True,            # Playwright を使用するか
    max_concurrency=5,              # RSS/API の最大同時リクエスト数
    max_concurrency_content=3,      # 本文取得の最大同時リクエスト数
)
```

**プロキシ使用例:**

```python
config = ScraperConfig(
    proxy="http://user:pass@host:port",
)

df = collect_financial_news(config=config)
```

#### `create_session()`

ブラウザを偽装した HTTP セッションを作成する。

```python
from news_scraper import create_session

# Chrome を偽装
session = create_session(impersonate="chrome")

# Safari を偽装 + プロキシ
session = create_session(
    impersonate="safari",
    proxy="http://localhost:8080",
)
```

### カテゴリ定義

#### CNBC カテゴリ（30種類）

```python
from news_scraper import CNBC_FEEDS, CNBC_QUANT_CATEGORIES

# 全カテゴリ
print(list(CNBC_FEEDS.keys()))
# ['top_news', 'world_news', 'us_news', 'asia_news', 'europe_news',
#  'business', 'earnings', 'commentary', 'economy', 'finance',
#  'investing', 'financial_advisors', 'buffett_watch', 'trader_talk',
#  'futures_now', 'options_action', 'bonds', 'commodities', 'technology',
#  'energy', 'health_care', 'real_estate', 'autos', 'personal_finance',
#  'wealth', 'taxes', 'politics', 'law', 'travel', 'charting_asia']

# クオンツ向け推奨カテゴリ
print(CNBC_QUANT_CATEGORIES)
# ['economy', 'finance', 'investing', 'earnings',
#  'bonds', 'commodities', 'technology', 'energy']
```

#### NASDAQ カテゴリ（14種類）

```python
from news_scraper import NASDAQ_CATEGORIES, NASDAQ_QUANT_CATEGORIES

# 全カテゴリ
print(NASDAQ_CATEGORIES)
# ['Markets', 'Technology', 'Earnings', 'Commodities', 'Currencies',
#  'Stocks', 'ETFs', 'IPOs', 'Economy', 'Investing', 'Personal-Finance',
#  'Retirement', 'World', 'Politics']

# クオンツ向け推奨カテゴリ
print(NASDAQ_QUANT_CATEGORIES)
# ['Markets', 'Earnings', 'Economy', 'Commodities',
#  'Currencies', 'Technology', 'Stocks']
```

### データ形式

#### DataFrame カラム

| カラム      | 型  | 説明                            |
| ----------- | --- | ------------------------------- |
| `title`     | str | 記事タイトル                    |
| `url`       | str | 記事 URL                        |
| `published` | str | 公開日時（ISO 8601）            |
| `summary`   | str | 記事要約                        |
| `category`  | str | カテゴリ                        |
| `source`    | str | ソース（cnbc, nasdaq）          |
| `content`   | str | 記事本文（オプション）          |
| `ticker`    | str | 銘柄コード（NASDAQ 銘柄別のみ） |
| `author`    | str | 著者名                          |

#### 出力ファイル形式

```
output_dir/
├── news_20240115_123456.json      # JSON（可読性重視）
└── news_20240115_123456.parquet   # Parquet（分析用）
```

## 使用例

### クオンツ分析用データセット構築

```python
from datetime import datetime, timedelta
from news_scraper import (
    collect_financial_news,
    collect_cnbc_historical,
    ScraperConfig,
)

# 1. 最新ニュースの収集（日次実行）
df_latest = collect_financial_news(
    tickers=["AAPL", "MSFT", "GOOGL", "NVDA", "AMZN", "META", "TSLA"],
    output_dir="data/news/latest",
)

# 2. 過去データの収集（初回のみ）
config = ScraperConfig(
    include_content=True,
    delay=1.5,
)

df_historical = collect_cnbc_historical(
    start_date=datetime(2024, 1, 1),
    end_date=datetime(2024, 12, 31),
    config=config,
    output_dir="data/news/historical",
)
```

### Embedding 用前処理

```python
import pandas as pd
from sentence_transformers import SentenceTransformer

# ニュースデータ読み込み
df = pd.read_parquet("data/news/latest/news_20240115_123456.parquet")

# 本文がない場合は要約を使用
df["text"] = df["content"].fillna("") + " " + df["summary"].fillna("")
df["text"] = df["text"].str.strip()

# Embedding 生成
model = SentenceTransformer("ProsusAI/finbert")
embeddings = model.encode(df["text"].tolist(), show_progress_bar=True)

# DataFrame に追加
df["embedding"] = list(embeddings)
```

### 定期収集スクリプト

```python
#!/usr/bin/env python
"""日次ニュース収集スクリプト."""

from datetime import datetime
from pathlib import Path

from news_scraper import collect_financial_news, ScraperConfig
from src.configuration.log import setup_logging

# ロギング設定
setup_logging()

# 出力ディレクトリ
output_dir = Path("data/news/daily") / datetime.now().strftime("%Y/%m")
output_dir.mkdir(parents=True, exist_ok=True)

# 収集
config = ScraperConfig(
    include_content=True,
    delay=1.0,
)

df = collect_financial_news(
    tickers=["AAPL", "MSFT", "GOOGL", "NVDA", "AMZN"],
    config=config,
    output_dir=output_dir,
)

print(f"Collected {len(df)} articles")
```

## 収集速度の目安

| 方式                         | 速度              | 1年分（推定） |
| ---------------------------- | ----------------- | ------------- |
| RSS のみ                     | 約30秒/全カテゴリ | -             |
| サイトマップ（タイトルのみ） | 約2秒/日          | 約12分        |
| サイトマップ + 本文          | 約1.5分/日        | 約9時間       |

## 注意事項

1. **レート制限**: 大量リクエスト時は `delay` を適切に設定してください
2. **robots.txt**: 個人の研究・分析目的での使用を想定しています
3. **Playwright**: CNBC の過去記事収集には Playwright が必要です
4. **プロキシ**: 大量収集時はプロキシの使用を検討してください

## ディレクトリ構成

```
src/news_scraper/
├── __init__.py       # パッケージ初期化・公開 API
├── types.py          # 型定義・カテゴリ定数
├── session.py        # HTTP セッション管理（同期・非同期）
├── async_core.py     # 非同期処理コア（RateLimiter, gather_with_errors）
├── cnbc.py           # CNBC スクレイパー（同期・非同期）
├── nasdaq.py         # NASDAQ スクレイパー（同期・非同期）
├── yfinance.py       # yfinance スクレイパー（Ticker / Search）
├── exceptions.py     # カスタム例外階層
├── retry.py          # リトライデコレータ・エラー分類
├── unified.py        # 統合スクレイパー（同期版 + fast ラッパー）
├── async_unified.py  # 非同期統合スクレイパー
└── README.md         # このファイル
```

## 技術スタック

| ライブラリ    | 用途                           |
| ------------- | ------------------------------ |
| curl-cffi     | ブラウザ偽装 HTTP クライアント |
| yfinance      | Yahoo Finance ニュース取得     |
| Playwright    | JavaScript レンダリング        |
| trafilatura   | 記事本文抽出                   |
| feedparser    | RSS 解析                       |
| tenacity      | リトライ制御                   |
| pandas        | データフレーム操作             |
| BeautifulSoup | HTML パース（フォールバック）  |

## ライセンス

このパッケージは Quants プロジェクトの一部です。
