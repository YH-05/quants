# market.bse

ボンベイ証券取引所（BSE India）からの市場データ取得モジュール。

## 概要

BSE India API (`https://api.bseindia.com/BseIndiaAPI/api`) および BSE ウェブサイトから株価・インデックス・コーポレートデータを取得します。httpx ベースの HTTP セッション（`BseSession`）に UA ローテーション、ポライトディレイ、指数バックオフリトライ、SSRF 防止ホストホワイトリストを内蔵。

**取得可能なデータ:**

- **個別銘柄の株価**: リアルタイム気配値・ヒストリカル価格 CSV
- **日次 Bhavcopy**: 全上場銘柄の日次集約データ（株式・デリバティブ・債券）
- **インデックスデータ**: SENSEX・BANKEX・BSE 500 等 12 種の過去データ
- **コーポレートデータ**: 企業概要・決算・開示・コーポレートアクション

## クイックスタート

### 個別銘柄の株価を取得する

```python
from market.bse import QuoteCollector

collector = QuoteCollector()

# スクリップコード "500325" = Reliance Industries
quote = collector.fetch_quote("500325")
print(f"{quote.scrip_name}: {quote.close} 円")
```

### SENSEX の過去データを取得する

```python
from market.bse import IndexCollector, IndexName

collector = IndexCollector()

# デフォルトで直近 365 日分を取得
df = collector.fetch_historical(IndexName.SENSEX)
print(df[["date", "open", "high", "low", "close"]].tail())
```

### 日次 Bhavcopy（全銘柄集約データ）を取得する

```python
import datetime
from market.bse import BhavcopyCollector

collector = BhavcopyCollector()

# 指定日の株式 Bhavcopy を取得
df = collector.fetch_equity(datetime.date(2026, 3, 5))
print(f"上場銘柄数: {len(df)}")
print(df[["scrip_code", "scrip_name", "close"]].head())
```

### 企業情報・決算を取得する

```python
from market.bse import CorporateCollector

collector = CorporateCollector()

# 企業プロフィール
info = collector.get_company_info("500325")
print(f"会社名: {info['company_name']}, 業種: {info['industry']}")

# 財務決算（四半期・通期）
results = collector.get_financial_results("500325")
for r in results:
    print(f"{r.period_ended}: EPS {r.eps}")
```

## 機能別セクション

### QuoteCollector: 個別銘柄の株価取得

BSE API の `getScripHeaderData` エンドポイントから気配値・出来高・売買代金を取得します。

**できること:**

- `fetch_quote(scrip_code)` - 単一銘柄のリアルタイム気配値を `ScripQuote` で取得
- `fetch_historical(scrip_code)` - 銘柄の過去価格 CSV を pandas DataFrame で取得
- `fetch(scrip_code=...)` - `DataCollector` 共通インターフェース（DataFrame 返却）
- `validate(df)` - 取得データの必須カラム検証

```python
from market.bse import QuoteCollector

collector = QuoteCollector()

# ScripQuote データクラスで取得
quote = collector.fetch_quote("500325")
print(quote.scrip_code)   # "500325"
print(quote.scrip_name)   # "RELIANCE INDUSTRIES LTD"
print(quote.open)         # "2450.00"（文字列）
print(quote.close)        # "2470.25"
print(quote.num_shares)   # "5000000"

# ヒストリカル価格（pandas DataFrame）
df = collector.fetch_historical("500325")
print(df.columns.tolist())  # ["scrip_code", "scrip_name", "open", "high", "low", "close", ...]
```

### BhavcopyCollector: 日次全銘柄集約データ取得

BSE が毎営業日終了後に公開する Bhavcopy CSV（全上場銘柄の日次サマリー）を取得します。

**できること:**

- `fetch_equity(date)` - 指定日の株式市場 Bhavcopy を取得
- `fetch_derivative(date)` - 指定日のデリバティブ Bhavcopy を取得
- `fetch_date_range(start, end, bhavcopy_type)` - 期間指定で複数日を一括取得（休場日・祝日はスキップ）
- `fetch(date=...)` - `DataCollector` 共通インターフェース（株式 Bhavcopy）
- `validate(df)` - 取得データの必須カラム検証

```python
import datetime
from market.bse import BhavcopyCollector, BhavcopyType

collector = BhavcopyCollector()

# 単日取得
df = collector.fetch_equity(datetime.date(2026, 3, 5))
print(df[["scrip_code", "scrip_name", "open", "high", "low", "close", "trading_date"]])

# 期間一括取得（祝日は自動スキップ）
df_range = collector.fetch_date_range(
    datetime.date(2026, 3, 3),
    datetime.date(2026, 3, 5),
    bhavcopy_type=BhavcopyType.EQUITY,
)
print(f"取得行数: {len(df_range)}")

# デリバティブ Bhavcopy
df_deriv = collector.fetch_derivative(datetime.date(2026, 3, 5))
```

取得される主なカラム: `scrip_code`, `scrip_name`, `scrip_group`, `scrip_type`, `open`, `high`, `low`, `close`, `last`, `prev_close`, `num_trades`, `num_shares`, `net_turnover`, `isin_code`, `trading_date`

### IndexCollector: インデックスデータ取得

BSE Index API から SENSEX・BANKEX 等の過去データを取得します。

**できること:**

- `fetch_historical(index_name, start, end)` - 指定インデックスの過去データを取得（デフォルト直近 365 日）
- `list_indices()` - 取得可能なインデックス名を一覧表示（静的メソッド）
- `fetch(index_name=..., start=..., end=...)` - `DataCollector` 共通インターフェース
- `validate(df)` - 取得データの必須カラム（`date`, `close`）検証

```python
from market.bse import IndexCollector, IndexName
import datetime

collector = IndexCollector()

# 利用可能なインデックス一覧
print(IndexCollector.list_indices())
# ["BANKEX", "BSE 100", "BSE 200", "BSE 500", ...]

# SENSEX の過去 1 年分
df = collector.fetch_historical(IndexName.SENSEX)
print(df[["date", "open", "high", "low", "close", "pe", "pb"]].tail())

# 期間指定
df_range = collector.fetch_historical(
    IndexName.BANKEX,
    start=datetime.date(2025, 1, 1),
    end=datetime.date(2025, 12, 31),
)
```

取得される主なカラム: `date`（datetime64）, `open`, `high`, `low`, `close`, `pe`（PER）, `pb`（PBR）, `yield`

**対応インデックス（12 種）:**

| 列挙値 | インデックス名 |
|--------|--------------|
| `IndexName.SENSEX` | SENSEX（代表指数） |
| `IndexName.SENSEX_50` | SENSEX 50 |
| `IndexName.BSE_100` | BSE 100 |
| `IndexName.BSE_200` | BSE 200 |
| `IndexName.BSE_500` | BSE 500 |
| `IndexName.BSE_MIDCAP` | BSE MIDCAP |
| `IndexName.BSE_SMALLCAP` | BSE SMALLCAP |
| `IndexName.BSE_LARGECAP` | BSE LARGECAP |
| `IndexName.BANKEX` | BANKEX（銀行セクター） |
| `IndexName.BSE_IT` | BSE IT |
| `IndexName.BSE_HEALTHCARE` | BSE HEALTHCARE |
| `IndexName.BSE_AUTO` | BSE AUTO |

### CorporateCollector: 企業情報・財務・コーポレートアクション取得

BSE の複数エンドポイントから企業プロフィール・決算・開示・配当等のコーポレートデータを取得します。`DataCollector` ABC を継承せず、メソッドごとに異なる型を返します。

**できること:**

- `get_company_info(scrip_code)` - 企業概要（会社名・ISIN・業種・時価総額・額面）を辞書で取得
- `get_financial_results(scrip_code)` - 四半期・通期決算を `FinancialResult` リストで取得
- `get_announcements(scrip_code)` - 取引所開示情報を `Announcement` リストで取得
- `get_corporate_actions(scrip_code)` - 配当・株式分割・権利落ち等を `CorporateAction` リストで取得
- `search_scrip(query)` - 銘柄名またはコードで銘柄を検索

```python
from market.bse import CorporateCollector

collector = CorporateCollector()

# 企業プロフィール
info = collector.get_company_info("500325")
# {"scrip_code": "500325", "company_name": "RELIANCE INDUSTRIES LTD",
#  "isin": "INE002A01018", "scrip_group": "A", "industry": "Refineries",
#  "market_cap": "1800000", "face_value": "10.00"}

# 財務決算
results = collector.get_financial_results("500325")
for r in results:
    print(f"{r.period_ended}: 売上 {r.revenue} Cr, 純利益 {r.net_profit} Cr, EPS {r.eps}")

# 取引所開示
announcements = collector.get_announcements("500325")
for a in announcements:
    print(f"[{a.announcement_date}] {a.category}: {a.subject}")

# コーポレートアクション
actions = collector.get_corporate_actions("500325")
for action in actions:
    print(f"権利落ち日 {action.ex_date}: {action.purpose}")

# 銘柄検索
results = collector.search_scrip("RELIANCE")
for r in results:
    print(f"{r['scrip_code']}: {r['scrip_name']}")
```

## API リファレンス

### コレクタークラス

| クラス | 説明 | 継承元 |
|--------|------|--------|
| `QuoteCollector` | 個別銘柄の気配値・ヒストリカル価格を取得 | `DataCollector`, `BseCollectorMixin` |
| `BhavcopyCollector` | 日次 Bhavcopy CSV を取得（株式・デリバティブ・債券） | `DataCollector`, `BseCollectorMixin` |
| `IndexCollector` | BSE インデックスの過去データを取得 | `DataCollector`, `BseCollectorMixin` |
| `CorporateCollector` | 企業情報・決算・開示・コーポレートアクションを取得 | `BseCollectorMixin` |

### BseSession

httpx ベースの HTTP セッション。BSE 特有のボットブロッキング対策を内蔵。

| メソッド | 説明 | 戻り値 |
|---------|------|--------|
| `get(url, params)` | ポライトディレイ・UA ローテーション付き GET | `httpx.Response` |
| `get_with_retry(url, params)` | 指数バックオフリトライ付き GET | `httpx.Response` |
| `download(url)` | バイナリコンテンツ（CSV, ZIP 等）をダウンロード | `bytes` |
| `close()` | セッションを閉じてリソースを解放 | `None` |

**特徴:**

- UA ローテーション（Chrome/Firefox/Safari/Edge × Windows/macOS/Linux の 12 種）
- ポライトディレイ（デフォルト 0.15 秒 + 0〜0.05 秒のジッター、単調時計ベース）
- SSRF 防止（許可ホスト: `api.bseindia.com`, `www.bseindia.com` のみ）
- 429 → `BseRateLimitError`、403/5xx → `BseAPIError` の自動変換
- コンテキストマネージャー対応（`with BseSession() as session:`）

```python
from market.bse import BseSession, BseConfig, RetryConfig

# カスタム設定でセッションを作成
config = BseConfig(polite_delay=0.5, timeout=60.0)
retry_config = RetryConfig(max_attempts=5, initial_delay=2.0)

with BseSession(config=config, retry_config=retry_config) as session:
    response = session.get_with_retry(
        "https://api.bseindia.com/BseIndiaAPI/api/getScripHeaderData",
        params={"scripcode": "500325"},
    )
    print(response.json())
```

### 設定クラス

| クラス | 説明 | 主なフィールド |
|--------|------|--------------|
| `BseConfig` | HTTP 動作設定（遅延・タイムアウト・UA） | `polite_delay=0.15`, `delay_jitter=0.05`, `timeout=30.0`, `user_agents=()` |
| `RetryConfig` | リトライ設定（指数バックオフ） | `max_attempts=3`, `initial_delay=1.0`, `max_delay=30.0`, `exponential_base=2.0`, `jitter=True` |

### データ型（データクラス）

すべて `frozen=True` の不変データクラス。

| 型 | 説明 | 主なフィールド |
|----|------|--------------|
| `ScripQuote` | 銘柄の気配値 | `scrip_code`, `scrip_name`, `scrip_group`, `open`, `high`, `low`, `close`, `last`, `prev_close`, `num_trades`, `num_shares`, `net_turnover` |
| `FinancialResult` | 四半期・通期決算 | `scrip_code`, `scrip_name`, `period_ended`, `revenue`, `net_profit`, `eps` |
| `Announcement` | 取引所開示情報 | `scrip_code`, `scrip_name`, `subject`, `announcement_date`, `category` |
| `CorporateAction` | コーポレートアクション | `scrip_code`, `scrip_name`, `ex_date`, `purpose`, `record_date` |

### 列挙型

| 列挙型 | 値 | 説明 |
|--------|-----|------|
| `BhavcopyType` | `EQUITY`, `DERIVATIVES`, `DEBT` | Bhavcopy の市場区分 |
| `ScripGroup` | `A`, `B`, `T`, `Z`, `X` | 銘柄のグループ分類（A: 大型株、B: 中小型株、T: 当日決済、Z: 非準拠、X: マイクロ） |
| `IndexName` | `SENSEX`, `BANKEX`, 他 10 種 | BSE インデックス名 |

### パーサー関数

数値クリーニングや JSON/CSV パースが必要な場合に直接利用できます。

| 関数 | 説明 | 入力 | 出力 |
|------|------|------|------|
| `parse_quote_response(raw)` | 気配値 JSON をパース | `dict` | `ScripQuote` |
| `parse_bhavcopy_csv(content)` | Bhavcopy CSV をパース | `str\|bytes` | `pd.DataFrame` |
| `parse_historical_csv(content)` | ヒストリカル CSV をパース | `str\|bytes` | `pd.DataFrame` |
| `parse_index_data(raw)` | インデックス JSON をパース | `list[dict]` | `pd.DataFrame` |
| `parse_company_info(raw)` | 企業情報 JSON をパース | `dict` | `dict[str, str\|None]` |
| `parse_financial_results(raw)` | 決算 JSON をパース | `list[dict]` | `list[FinancialResult]` |
| `parse_announcements(raw)` | 開示 JSON をパース | `list[dict]` | `list[Announcement]` |
| `parse_corporate_actions(raw)` | コーポレートアクション JSON をパース | `list[dict]` | `list[CorporateAction]` |
| `clean_price(value)` | BSE 価格文字列を `float` に変換 | `str` | `float\|None` |
| `clean_volume(value)` | 出来高文字列を `int` に変換 | `str` | `int\|None` |
| `clean_indian_number(value)` | インド表記（ラク・クロール）を `float` に変換 | `str` | `float\|None` |

### 例外クラス

| 例外 | 継承元 | 発生条件 | 追加属性 |
|------|--------|---------|---------|
| `BseError` | `Exception` | すべての BSE 操作の基底例外 | `message` |
| `BseAPIError` | `BseError` | HTTP 403/5xx エラー | `url`, `status_code`, `response_body` |
| `BseRateLimitError` | `BseError` | HTTP 429 レートリミット超過 | `url`, `retry_after` |
| `BseParseError` | `BseError` | JSON/CSV パース失敗 | `raw_data`, `field` |
| `BseValidationError` | `BseError` | データバリデーション失敗 | `field`, `value` |

```python
from market.bse import QuoteCollector, BseError, BseRateLimitError, BseAPIError

collector = QuoteCollector()

try:
    quote = collector.fetch_quote("500325")
except BseRateLimitError as e:
    print(f"レートリミット超過: {e.message}, 推奨待機時間: {e.retry_after}秒")
except BseAPIError as e:
    print(f"API エラー: HTTP {e.status_code} - {e.url}")
except BseError as e:
    print(f"BSE エラー: {e.message}")
```

## モジュール構成

```
market/bse/
├── __init__.py          # パッケージエクスポート（全パブリック API）
├── constants.py         # API URL・ホストホワイトリスト・デフォルト設定・カラムマップ
├── errors.py            # 例外クラス（BseError 階層）
├── parsers.py           # JSON/CSV パーサーと数値クリーニング関数
├── session.py           # BseSession（httpx ベース HTTP セッション）
├── types.py             # 設定・列挙型・データクラス定義
├── collectors/
│   ├── __init__.py      # コレクターパッケージ
│   ├── _base.py         # BseCollectorMixin（共通セッション管理）
│   ├── bhavcopy.py      # BhavcopyCollector
│   ├── corporate.py     # CorporateCollector
│   ├── index.py         # IndexCollector
│   └── quote.py         # QuoteCollector
└── README.md            # このファイル
```

## トラブルシューティング

### レートリミット（HTTP 429）

BSE API がリクエストを制限した場合、`BseRateLimitError` が発生します。`RetryConfig` でリトライ戦略を調整してください。

```python
from market.bse import BseSession, RetryConfig

retry_config = RetryConfig(max_attempts=5, initial_delay=2.0, max_delay=60.0)
with BseSession(retry_config=retry_config) as session:
    ...
```

### アクセス拒否（HTTP 403）

BSE が UA やリクエストパターンを検知した可能性があります。`BseConfig` でディレイを長めに設定してください。

```python
from market.bse import BseConfig

config = BseConfig(polite_delay=1.0, delay_jitter=0.5)
```

### 祝日・休場日の Bhavcopy

`BhavcopyCollector.fetch_date_range()` は取得失敗日（休場日）を自動スキップします。単日取得（`fetch_equity()`）の場合は `BseAPIError` が発生するため、例外処理が必要です。

## 関連モジュール

- [market.yfinance](../yfinance/README.md) - Yahoo Finance からの株価取得
- [market.fred](../fred/README.md) - FRED 経済指標データ取得
- [market.nasdaq](../nasdaq/README.md) - NASDAQ データ取得（類似アーキテクチャ）
- [market.cache](../cache/README.md) - API レスポンスのキャッシュ機能
