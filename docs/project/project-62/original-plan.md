# NASDAQ 過去ニュース記事取得機能の追加

## Context

現在 `news_scraper` パッケージでは CNBC のみ過去記事取得（`collect_historical_news` + Playwright サイトマップ）に対応している。NASDAQ は RSS（直近のみ）と API（`offset=0` 固定）のため過去記事を遡れない。NASDAQ API の `offset` パラメータを活用したページネーションと、Playwright によるニュースアーカイブページのスクレイピングの2戦略で過去記事取得を実現する。

## 戦略

| 戦略 | 方式 | 対象 | 特徴 |
|------|------|------|------|
| **A. API ページネーション** | `offset` を増やして API を順次呼び出し | ティッカー指定 | シンプル・高信頼・構造化データ |
| **B. Playwright アーカイブ** | ニュースアーカイブページをスクレイピング | カテゴリ指定 | 幅広い記事発見・JS レンダリング必要 |

## 変更ファイル

### 1. `src/news_scraper/nasdaq.py` — メイン実装（6関数 + 2ヘルパー追加）

#### ヘルパー関数

**`_parse_article_date(date_str: str) -> datetime | None`**
- NASDAQ API/ページの日付文字列を datetime にパース
- ISO 8601, "MM/DD/YYYY", "Month DD, YYYY" 等の複数フォーマット対応

**`_category_to_url_segment(category: str) -> str`**
- `NASDAQ_CATEGORIES` をアーカイブページの URL パスに変換
- 例: `"Markets"` → `"markets"`, `"Personal-Finance"` → `"personal-finance"`

#### 戦略A: API ページネーション

**`fetch_stock_news_api_paginated(session, ticker, max_articles=200, page_size=20, start_date=None, end_date=None, config=None) -> list[Article]`**
- URL: `https://api.nasdaq.com/api/news/topic/articlebysymbol?q={ticker}|STOCKS&offset={offset}&limit={page_size}`
- `offset` を `0, page_size, 2*page_size, ...` とループ
- 終了条件: (a) `offset >= data.totalrecords` (b) `offset >= max_articles` (c) 空 rows (d) 全記事が `start_date` より古い
- 既存の `fetch_stock_news_api` と同じヘッダー・Article マッピングを再利用
- ページ間に `time.sleep(get_delay(config))` でレートリミット

**`async_fetch_stock_news_api_paginated(...)` — async 版**
- `await session.get()` + `asyncio.sleep()` で非同期化

#### 戦略B: Playwright アーカイブスクレイピング

**`fetch_news_archive_playwright(category, max_articles=100, browser=None) -> list[dict]`**
- URL: `https://www.nasdaq.com/news-and-insights/topic/{url_segment}`
- Playwright で JS レンダリング後、記事リンクを抽出
- "Load More" ボタンを繰り返しクリックして過去記事を取得
- CNBC の `fetch_sitemap_articles_playwright` と同じパターン:
  - Playwright lazy import
  - browser 引数で既存インスタンスを再利用 or 新規作成
  - `page.wait_for_load_state("networkidle")`
- 出力: `[{"title", "url", "date", "category", "source": "nasdaq"}]`

**`async_fetch_news_archive_playwright(...)` — async 版**
- `playwright.async_api` 使用

#### 統合オーケストレーター

**`collect_historical_news(start_date, end_date, tickers=None, categories=None, config=None, output_dir=None) -> pd.DataFrame`**
- CNBC の `collect_historical_news` と同じインターフェース
- `tickers` 指定 → 戦略A（API ページネーション）
- `categories` + `config.use_playwright=True` → 戦略B（Playwright アーカイブ）
- `config.include_content=True` → 既存の `fetch_article_content` で本文取得
- 保存: 日別 JSON + 全体 Parquet（CNBC と同じ形式）

**`async_collect_historical_news(...)` — async 版**
- ティッカー間の並列化: `RateLimiter` + `gather_with_errors`
- 本文取得の並列化: `max_concurrency_content` で制御

### 2. `src/news_scraper/__init__.py` — export 追加

```python
from .nasdaq import collect_historical_news as collect_nasdaq_historical
from .nasdaq import async_collect_historical_news as async_collect_nasdaq_historical
from .nasdaq import fetch_stock_news_api_paginated as fetch_nasdaq_stock_news_paginated
from .nasdaq import async_fetch_stock_news_api_paginated as async_fetch_nasdaq_stock_news_paginated
```

`__all__` に4つ追加。

### 3. `src/news_scraper/types.py` — docstring 更新

`ScraperConfig.use_playwright` の説明を NASDAQ 対応に更新（docstring のみ）。

### 4. `tests/news_scraper/unit/test_nasdaq.py` — テスト追加（~20テスト）

| テストクラス | テスト内容 |
|-------------|-----------|
| `TestFetchStockNewsApiPaginated` | 複数ページ取得、totalrecords で終了、日付フィルタ、max_articles 制限、空 rows 早期終了、API エラー時の部分結果返却 |
| `TestAsyncFetchStockNewsApiPaginated` | 非同期版の同等テスト |
| `TestFetchNewsArchivePlaywright` | 記事一覧取得、Load More クリック、ブラウザ新規作成/再利用、エラー時空リスト |
| `TestAsyncFetchNewsArchivePlaywright` | async Playwright 版 |
| `TestCollectHistoricalNews` | ティッカー経由の収集、カテゴリ経由の収集、ファイル保存、use_playwright=False スキップ、include_content |
| `TestCategoryToUrlSegment` | 全カテゴリ変換、不明カテゴリで ValueError |
| `TestParseArticleDate` | 複数フォーマットのパース、不正形式で None |

## 再利用する既存コード

| コード | パス | 用途 |
|--------|------|------|
| `RateLimiter` | `async_core.py` | async 並列制御 |
| `gather_with_errors` | `async_core.py` | フォールトトレラント並列実行 |
| `get_delay(config)` | `types.py` | ジッター付きディレイ計算 |
| `fetch_article_content` | `nasdaq.py:288` | 本文取得（trafilatura + BS4） |
| `async_fetch_article_content` | `nasdaq.py:364` | async 本文取得 |
| `create_session` / `create_async_session` | `session.py` | HTTP セッション生成 |
| CNBC `collect_historical_news` パターン | `cnbc.py:682` | Playwright ライフサイクル・ファイル保存の参考 |

## 実装順序

1. **Phase 1**: ヘルパー関数（`_parse_article_date`, `_category_to_url_segment`）+ テスト
2. **Phase 2**: API ページネーション（sync + async）+ テスト
3. **Phase 3**: Playwright アーカイブ（sync + async）+ テスト
4. **Phase 4**: 統合オーケストレーター（sync + async）+ テスト
5. **Phase 5**: `__init__.py` export + `types.py` docstring + `make check-all`

## 検証方法

```python
# 1. API ページネーション（ティッカー指定）
from news_scraper import create_session, ScraperConfig
from news_scraper.nasdaq import fetch_stock_news_api_paginated
from datetime import datetime

session = create_session()
articles = fetch_stock_news_api_paginated(
    session, "AAPL", max_articles=50,
    start_date=datetime(2026, 2, 1), end_date=datetime(2026, 2, 28),
)
print(f"API: {len(articles)} articles")

# 2. Playwright アーカイブ（カテゴリ指定）
from news_scraper.nasdaq import fetch_news_archive_playwright
articles = fetch_news_archive_playwright("Markets", max_articles=30)
print(f"Playwright: {len(articles)} articles")

# 3. 統合オーケストレーター
from news_scraper.nasdaq import collect_historical_news
df = collect_historical_news(
    start_date=datetime(2026, 2, 1), end_date=datetime(2026, 2, 28),
    tickers=["AAPL", "MSFT"],
    categories=["Markets", "Technology"],
    config=ScraperConfig(use_playwright=True, include_content=True),
    output_dir="data/news/nasdaq_historical",
)
print(f"Total: {len(df)} articles")

# 4. テスト実行
# make check-all
```

## リスクと対策

| リスク | 対策 |
|--------|------|
| NASDAQ ボット検知（403） | 既存 `BotDetectionError` 処理 + Playwright の User-Agent + `config.delay` |
| "Load More" ボタンのセレクタ変更 | 複数フォールバックセレクタ + ログ警告 |
| API レートリミット（429） | `get_delay(config)` + ジッター + `Retry-After` ヘッダー尊重 |
| `totalrecords` の不正確さ | 空 rows チェックも終了条件に含める |
| Playwright 未インストール | lazy import + `use_playwright=False` でスキップ |
