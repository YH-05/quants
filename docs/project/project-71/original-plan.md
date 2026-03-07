# 日本株情報源の実装計画（Tier 1 + Tier 2）

## Context

既存の `news_scraper` パッケージは CNBC/NASDAQ/yfinance の3ソース（全て米国向け）のみ対応。日本株・日本市場の投資判断に使える情報源を追加し、日本語ニュース収集と日本市場データ取得を可能にする。

調査の結果、以下を Tier 1（即実装可能）+ Tier 2（中優先度）として選定した:

- **RSS系**: 東洋経済オンライン、Investing.com日本版、Yahoo!ニュース経済、JPX公式、TDnet非公式
- **API系**: J-Quants API（JPX公式）、EDINET開示API（金融庁）
- **既存拡張**: yfinance 日本株プリセット

---

## Wave 分割

```
Wave 1: RSS スクレイパー追加（依存なし、feedparser既存）
  Issue 1: 東洋経済 + Investing.com + Yahoo!ニュース
  Issue 2: JPX公式 + TDnet非公式
  Issue 3: yfinance 日本株プリセット

Wave 2: Market API クライアント（新依存あり、Wave 1 と並行可）
  Issue 4: J-Quants API クライアント
  Issue 5: EDINET 開示 API クライアント

Wave 3: 統合（Wave 1, 2 完了後）
  Issue 6: news_scraper 統合（unified.py + async_unified.py + __init__.py）
  Issue 7: market パッケージ統合 + RSS フィード登録
```

---

## Issue 1: 日本語 RSS スクレイパー（東洋経済・Investing.com・Yahoo!ニュース）

### 新規ファイル

| ファイル | 責務 |
|---------|------|
| `src/news_scraper/toyokeizai.py` | 東洋経済オンライン RSS スクレイパー |
| `src/news_scraper/investing_jp.py` | Investing.com 日本版 RSS スクレイパー（複数フィード） |
| `src/news_scraper/yahoo_jp.py` | Yahoo!ニュース経済 RSS スクレイパー |
| `tests/news_scraper/unit/test_toyokeizai.py` | |
| `tests/news_scraper/unit/test_investing_jp.py` | |
| `tests/news_scraper/unit/test_yahoo_jp.py` | |
| `tests/news_scraper/property/test_jp_rss_property.py` | 3ソース共通プロパティテスト |

### 変更ファイル

| ファイル | 変更内容 |
|---------|---------|
| `src/news_scraper/types.py` | フィード定数追加（末尾に append） |

### types.py への追加定数

```python
# 東洋経済オンライン
TOYOKEIZAI_FEEDS: dict[str, str] = {
    "all": "https://toyokeizai.net/list/feed/rss",
}

# Investing.com 日本版
INVESTING_JP_FEEDS: dict[str, str] = {
    "forex": "https://jp.investing.com/rss/news_1.rss",
    "commodities": "https://jp.investing.com/rss/news_11.rss",
    "stocks": "https://jp.investing.com/rss/news_25.rss",
    "economy": "https://jp.investing.com/rss/news_14.rss",
    "bonds": "https://jp.investing.com/rss/news_95.rss",
}

# Yahoo!ニュース日本
YAHOO_JP_FEEDS: dict[str, str] = {
    "business": "https://news.yahoo.co.jp/rss/categories/business.xml",
    "economy": "https://news.yahoo.co.jp/rss/categories/world.xml",
    "it": "https://news.yahoo.co.jp/rss/categories/it.xml",
}
```

### 各モジュールの実装パターン

`cnbc.py` (L31-86) をそのまま踏襲:

```python
# toyokeizai.py の構造例
def fetch_rss_feed(session, category, timeout=30) -> list[Article]:
    # 1. TOYOKEIZAI_FEEDS[category] でURL取得
    # 2. session.get(url) → feedparser.parse(resp.text)
    # 3. entry → Article(source="toyokeizai") に変換

async def async_fetch_rss_feed(session, category, timeout=30) -> list[Article]:
    # HTTP GETのみ await、feedparser は同期

def fetch_multiple_categories(session, categories, delay, timeout) -> pd.DataFrame:
    # ループ + time.sleep(delay)

async def async_fetch_multiple_categories(session, categories, config) -> pd.DataFrame:
    # RateLimiter + gather_with_errors
```

- `Article.source`: `"toyokeizai"`, `"investing_jp"`, `"yahoo_jp"`
- feedparser は UTF-8 の日本語フィードをネイティブ対応
- 本文取得: trafilatura は日本語対応済み（既存パターン流用）

---

## Issue 2: JPX・TDnet RSS スクレイパー

### 新規ファイル

| ファイル | 責務 |
|---------|------|
| `src/news_scraper/jpx.py` | JPX 公式 RSS スクレイパー |
| `src/news_scraper/tdnet.py` | TDnet 非公式 RSS（yanoshin API 経由） |
| `tests/news_scraper/unit/test_jpx.py` | |
| `tests/news_scraper/unit/test_tdnet.py` | |
| `tests/news_scraper/property/test_jpx_tdnet_property.py` | |

### 変更ファイル

| ファイル | 変更内容 |
|---------|---------|
| `src/news_scraper/types.py` | JPX/TDnet フィード定数追加 |

### TDnet 固有の設計

TDnet の RSS URL は銘柄コード指定: `https://webapi.yanoshin.jp/webapi/tdnet/list/{codes}.rss`

```python
# tdnet.py — 他のRSSスクレイパーと異なるシグネチャ
TDNET_BASE_URL = "https://webapi.yanoshin.jp/webapi/tdnet/list"

def fetch_disclosure_feed(
    session, codes: list[str], timeout=30
) -> list[Article]:
    """銘柄コード指定で適時開示RSSを取得."""
    codes_str = ",".join(codes)
    url = f"{TDNET_BASE_URL}/{codes_str}.rss"
    # feedparser → Article(source="tdnet", ticker=code)

# デフォルト銘柄コード（TOPIX Core 30 主要銘柄）
TDNET_DEFAULT_CODES: list[str] = [
    "7203", "6758", "9984", "8306", "6861", ...
]
```

- 非公式APIのため安定性に懸念 → リトライ + エラーログで対応
- `Article.ticker` に証券コードを設定

---

## Issue 3: yfinance 日本株プリセット

### 新規ファイル

| ファイル | 責務 |
|---------|------|
| `tests/news_scraper/unit/test_yfinance_jp.py` | |

### 変更ファイル

| ファイル | 変更内容 |
|---------|---------|
| `src/news_scraper/types.py` | `YFINANCE_JP_TICKERS`, `YFINANCE_JP_INDICES` 追加 |
| `src/news_scraper/yfinance.py` | `fetch_jp_stock_news()` 便利関数追加 |

### 追加定数

```python
# types.py
YFINANCE_JP_TICKERS: list[str] = [
    "7203.T",  # トヨタ
    "6758.T",  # ソニー
    "9984.T",  # ソフトバンクG
    "8306.T",  # 三菱UFJ
    "6861.T",  # キーエンス
    "6902.T",  # デンソー
    "9432.T",  # NTT
    "6501.T",  # 日立
    "7741.T",  # HOYA
    "8035.T",  # 東京エレクトロン
    # ... 主要20-30銘柄
]

YFINANCE_JP_INDICES: list[str] = ["^N225", "^TOPX"]
```

### yfinance.py への追加

```python
def fetch_jp_stock_news(
    session, tickers: list[str] | None = None, timeout: int = 30,
) -> list[Article]:
    """日本株ニュースを取得する（YFINANCE_JP_TICKERS デフォルト）."""
    if tickers is None:
        tickers = list(YFINANCE_JP_TICKERS)
    # 既存 fetch_multiple_tickers() を呼び出し
```

---

## Issue 4: J-Quants API クライアント

### 新規ファイル

```
src/market/jquants/
├── __init__.py          # 公開API
├── client.py            # JQuantsClient（メイン実装）
├── session.py           # JQuantsSession（httpx + 認証 + polite delay）
├── types.py             # JQuantsConfig, RetryConfig, FetchOptions
├── constants.py         # BASE_URL, ALLOWED_HOSTS, ENV変数名
├── errors.py            # JQuantsError 階層
├── cache.py             # SQLiteCache（TTL対応、株価/財務キャッシュ）
├── README.md            # モジュールドキュメント
```

テスト:
```
tests/market/jquants/
├── unit/
│   ├── test_client.py
│   ├── test_session.py
│   ├── test_types.py
│   ├── test_constants.py
│   └── test_errors.py
├── property/
└── integration/
    └── test_jquants_integration.py
```

### 参照パターン

- セッション設計: `src/market/bse/session.py`（httpx + UA rotation + SSRF対策 + polite delay）
- エラー階層: `src/market/bse/errors.py`（BseError(MarketError) パターン）
- クライアント設計: `src/market/edinet/client.py`（_request + _handle_response + リトライ）
- キャッシュ: `src/market/cache/cache.py`（SQLiteCache + TTL）

### 設計詳細

```python
# constants.py
BASE_URL: Final[str] = "https://api.jquants.com/v1"
ALLOWED_HOSTS: Final[frozenset[str]] = frozenset({"api.jquants.com"})
JQUANTS_MAIL_ADDRESS_ENV: Final[str] = "JQUANTS_MAIL_ADDRESS"
JQUANTS_PASSWORD_ENV: Final[str] = "JQUANTS_PASSWORD"

# errors.py
class JQuantsError(MarketError): ...      # 基底
class JQuantsAPIError(JQuantsError): ...  # API呼び出し失敗
class JQuantsRateLimitError(JQuantsError): ...  # 429
class JQuantsValidationError(JQuantsError): ... # バリデーション
class JQuantsAuthError(JQuantsError): ...  # 認証失敗

# client.py — 主要メソッド
class JQuantsClient:
    def get_listed_info(self, code: str | None = None) -> pd.DataFrame
    def get_daily_quotes(self, code: str, from_date: str, to_date: str) -> pd.DataFrame
    def get_financial_statements(self, code: str) -> pd.DataFrame
    def get_trading_calendar(self) -> pd.DataFrame
```

- **認証**: email/password → refresh_token → id_token のフロー。session.py でトークンライフサイクル管理
- **依存追加**: `pyproject.toml` に `jquants-api-client-python>=3.0.0`
- **キャッシュ戦略**: 日足 OHLC = TTL 24h、上場銘柄情報 = TTL 7d、財務 = TTL 24h

---

## Issue 5: EDINET 開示 API クライアント

### 新規ファイル

```
src/market/edinet_api/
├── __init__.py          # 公開API
├── client.py            # EdinetApiClient（メイン実装）
├── session.py           # EdinetApiSession（httpx + polite delay）
├── types.py             # EdinetApiConfig, DocumentType enum, DisclosureDocument
├── constants.py         # BASE_URL, ALLOWED_HOSTS, ENV変数名
├── errors.py            # EdinetApiError 階層
├── parsers.py           # XBRL/PDF レスポンスパーサー
├── README.md            # モジュールドキュメント
```

テスト:
```
tests/market/edinet_api/
├── unit/
│   ├── test_client.py
│   ├── test_session.py
│   ├── test_types.py
│   ├── test_constants.py
│   ├── test_errors.py
│   └── test_parsers.py
├── property/
└── integration/
```

### 設計詳細

```python
# constants.py
BASE_URL: Final[str] = "https://api.edinet-fsa.go.jp/api/v2"
DOWNLOAD_BASE_URL: Final[str] = "https://disclosure2dl.edinet-fsa.go.jp/api/v2"
ALLOWED_HOSTS: Final[frozenset[str]] = frozenset({
    "api.edinet-fsa.go.jp",
    "disclosure2dl.edinet-fsa.go.jp",
})
EDINET_FSA_API_KEY_ENV: Final[str] = "EDINET_FSA_API_KEY"

# client.py — 主要メソッド
class EdinetApiClient:
    def search_documents(self, date: str, doc_type: DocumentType | None = None) -> list[DisclosureDocument]
    def download_document(self, doc_id: str, format: str = "xbrl") -> bytes
```

- 既存 `src/market/edinet/`（EDINET DB API）とは**完全に別モジュール**
  - 既存: `https://edinetdb.jp` — 企業財務データ検索API
  - 新規: `https://api.edinet-fsa.go.jp` — 金融庁の開示書類取得API
- 環境変数も分離: `EDINET_FSA_API_KEY`（既存は `EDINET_DB_API_KEY`）
- 無料（APIキー登録のみ）

---

## Issue 6: news_scraper 統合

### 変更ファイル

| ファイル | 変更内容 |
|---------|---------|
| `src/news_scraper/unified.py` | 5つの `_collect_*()` 追加 + source 条件分岐追加 |
| `src/news_scraper/async_unified.py` | 非同期版の同等追加 |
| `src/news_scraper/__init__.py` | 新モジュールのエクスポート追加 |

### unified.py の変更パターン

L31 の import に追加:
```python
from . import cnbc, nasdaq, yfinance, toyokeizai, investing_jp, yahoo_jp, jpx, tdnet
```

L43 の `_DEFAULT_SOURCES` は変更**しない**（既存の "cnbc", "nasdaq" のまま。日本語ソースはオプトイン）。

L194-216 のソース条件分岐に追加（同じ try/except パターン）:
```python
if "toyokeizai" in sources:
    try:
        all_articles.extend(_collect_toyokeizai(config))
    except Exception as e:
        logger.error("Toyokeizai collection failed", error=str(e))

if "investing_jp" in sources:
    ...
if "yahoo_jp" in sources:
    ...
if "jpx" in sources:
    ...
if "tdnet" in sources:
    ...
```

### 使用例

```python
# 日本語ソースのみ
df = collect_financial_news(sources=["toyokeizai", "yahoo_jp", "investing_jp"])

# 米国 + 日本
df = collect_financial_news(sources=["cnbc", "toyokeizai"])

# TDnet（銘柄コード指定）— tdnet_codes パラメータ追加
df = collect_financial_news(sources=["tdnet"], tdnet_codes=["7203", "6758"])
```

---

## Issue 7: market パッケージ統合 + RSS フィード登録

### 変更ファイル

| ファイル | 変更内容 |
|---------|---------|
| `src/market/types.py` | `DataSource` enum に `JQUANTS`, `EDINET_API` 追加 |
| `src/market/__init__.py` | jquants, edinet_api のインポート・エクスポート追加 |
| `data/raw/rss/feeds.json` | 日本語 RSS フィード 5-8件登録 |
| `pyproject.toml` | `jquants-api-client-python>=3.0.0` 依存追加 |

### DataSource enum 追加

```python
# src/market/types.py L51 の後に追加
JQUANTS = "jquants"
EDINET_API = "edinet_api"
```

### feeds.json 登録フィード

カテゴリ `"japan_market"` で以下を登録:
- 東洋経済オンライン RSS
- Yahoo!ニュース 経済/IT
- Investing.com 日本版 株式/為替/経済
- JPX 公式 ニュースリリース

---

## 変更ファイル全体一覧

| ファイル | Wave | 変更種別 |
|---------|------|---------|
| `src/news_scraper/types.py` | 1 | 定数 append |
| `src/news_scraper/yfinance.py` | 1 | 関数 append |
| `src/news_scraper/unified.py` | 3 | import + _collect_* + 条件分岐 |
| `src/news_scraper/async_unified.py` | 3 | 同上（非同期版） |
| `src/news_scraper/__init__.py` | 3 | エクスポート追加 |
| `src/market/types.py` | 3 | DataSource enum 追加 |
| `src/market/__init__.py` | 3 | インポート追加 |
| `data/raw/rss/feeds.json` | 3 | フィード登録 |
| `pyproject.toml` | 2 | 依存追加 |

## 新規ファイル全体一覧

| ファイル | Wave/Issue |
|---------|-----------|
| `src/news_scraper/toyokeizai.py` | 1/1 |
| `src/news_scraper/investing_jp.py` | 1/1 |
| `src/news_scraper/yahoo_jp.py` | 1/1 |
| `src/news_scraper/jpx.py` | 1/2 |
| `src/news_scraper/tdnet.py` | 1/2 |
| `src/market/jquants/` (8ファイル) | 2/4 |
| `src/market/edinet_api/` (8ファイル) | 2/5 |
| テストファイル (約20ファイル) | 各Wave |

---

## 検証方法

### 個別モジュール検証

```python
# RSS スクレイパー
from news_scraper.toyokeizai import fetch_rss_feed
from news_scraper.session import create_session
session = create_session()
articles = fetch_rss_feed(session, "all")
assert len(articles) > 0
assert all(a.source == "toyokeizai" for a in articles)

# J-Quants
from market.jquants import JQuantsClient
with JQuantsClient() as client:
    quotes = client.get_daily_quotes("7203")
    assert len(quotes) > 0

# EDINET
from market.edinet_api import EdinetApiClient
with EdinetApiClient() as client:
    docs = client.search_documents("2026-03-01")
    assert len(docs) > 0
```

### 統合検証

```python
from news_scraper import collect_financial_news
df = collect_financial_news(sources=["toyokeizai", "yahoo_jp", "investing_jp"])
assert len(df) > 0
assert "toyokeizai" in df["source"].unique()
```

### 品質ゲート

```bash
make check-all   # format + lint + typecheck + test
```

---

## 重要な参照ファイル

| 目的 | 参照先 |
|------|--------|
| RSS スクレイパーパターン | `src/news_scraper/cnbc.py` L31-86 |
| フィード定数定義 | `src/news_scraper/types.py` L124-200 |
| 統合関数パターン | `src/news_scraper/unified.py` L46-68, L194-216 |
| 非同期パターン | `src/news_scraper/async_core.py` (RateLimiter, gather_with_errors) |
| Market セッション設計 | `src/market/bse/session.py` |
| Market エラー階層 | `src/market/bse/errors.py` |
| Market クライアント設計 | `src/market/edinet/client.py` |
| Market キャッシュ | `src/market/cache/cache.py` |
| DataSource enum | `src/market/types.py` L18-51 |
