# market.nasdaq

NASDAQ Stock Screener API からの株式スクリーニングデータ取得モジュール。

## 概要

NASDAQ Stock Screener API (`https://api.nasdaq.com/api/screener/stocks`) を通じて、NASDAQ・NYSE・AMEX に上場する全銘柄のスクリーニングデータを取得します。curl_cffi による TLS フィンガープリント偽装とボットブロッキング対策を内蔵。

**取得可能なデータ:**

- **銘柄一覧**: 全上場銘柄のティッカー・社名・株価・時価総額・出来高
- **フィルタリング**: 取引所・時価総額・セクター・アナリスト推奨・地域・国別絞り込み
- **カテゴリ別バルク取得**: 全取引所、全セクターなどカテゴリ単位での一括取得
- **CSV ダウンロード**: utf-8-sig エンコードで CSV ファイルへ保存

## クイックスタート

### 全銘柄の一括取得

```python
from market.nasdaq import ScreenerCollector

collector = ScreenerCollector()
df = collector.fetch()
print(f"銘柄数: {len(df)}")
print(df[["symbol", "name", "market_cap", "sector"]].head())
```

### フィルタリングして取得

```python
from market.nasdaq import ScreenerCollector, ScreenerFilter, Exchange, Sector

collector = ScreenerCollector()

# NASDAQ 上場のテクノロジー銘柄のみ取得
df = collector.fetch(
    filter=ScreenerFilter(
        exchange=Exchange.NASDAQ,
        sector=Sector.TECHNOLOGY,
    )
)
print(f"NASDAQ テクノロジー銘柄数: {len(df)}")
```

### CSV に保存

```python
from market.nasdaq import ScreenerCollector

collector = ScreenerCollector()
path = collector.download_csv(output_dir="data/raw/nasdaq")
print(f"保存先: {path}")
```

## 機能別ガイド

### スクリーニング（全銘柄一括取得）

フィルタなしで全上場銘柄を取得します。`limit=0` が自動的に設定され、全件取得されます。

```python
from market.nasdaq import ScreenerCollector

collector = ScreenerCollector()
df = collector.fetch()

# 取得されるカラム
# symbol, name, last_sale, net_change, pct_change,
# market_cap, country, ipo_year, volume, sector, industry, url
print(df.dtypes)
```

取得後にデータ検証を行う場合:

```python
is_valid = collector.validate(df)
print(f"データ正常: {is_valid}")  # symbol と name カラムの存在・空チェック
```

### フィルタリング（取引所・セクター・時価総額等）

`ScreenerFilter` で複数の条件を組み合わせてフィルタリングできます。

```python
from market.nasdaq import ScreenerCollector, ScreenerFilter
from market.nasdaq import Exchange, MarketCap, Sector, Recommendation, Region, Country

collector = ScreenerCollector()

# 時価総額でフィルタ（メガキャップのみ）
df = collector.fetch(filter=ScreenerFilter(marketcap=MarketCap.MEGA))

# アナリスト推奨でフィルタ
df = collector.fetch(filter=ScreenerFilter(recommendation=Recommendation.STRONG_BUY))

# 地域でフィルタ
df = collector.fetch(filter=ScreenerFilter(region=Region.NORTH_AMERICA))

# 国でフィルタ（Enum または文字列で指定可能）
df = collector.fetch(filter=ScreenerFilter(country=Country.JAPAN))
df = collector.fetch(filter=ScreenerFilter(country="japan"))  # 文字列も可

# 複数条件を組み合わせ
df = collector.fetch(
    filter=ScreenerFilter(
        exchange=Exchange.NYSE,
        marketcap=MarketCap.LARGE,
        sector=Sector.FINANCE,
    )
)
print(f"結果: {len(df)} 件")
```

**フィルタ値一覧:**

| フィルタ | 値 |
|---------|-----|
| `Exchange` | `NASDAQ`, `NYSE`, `AMEX` |
| `MarketCap` | `MEGA`($200B+), `LARGE`($10B-$200B), `MID`($2B-$10B), `SMALL`($300M-$2B), `MICRO`($50M-$300M), `NANO`(<$50M) |
| `Sector` | `TECHNOLOGY`, `HEALTH_CARE`, `FINANCE`, `CONSUMER_DISCRETIONARY`, `CONSUMER_STAPLES`, `INDUSTRIALS`, `ENERGY`, `UTILITIES`, `REAL_ESTATE`, `TELECOMMUNICATIONS`, `BASIC_MATERIALS` |
| `Recommendation` | `STRONG_BUY`, `BUY`, `HOLD`, `SELL`, `STRONG_SELL` |
| `Region` | `NORTH_AMERICA`, `EUROPE`, `ASIA`, `SOUTH_AMERICA`, `AFRICA`, `MIDDLE_EAST`, `AUSTRALIA_AND_SOUTH_PACIFIC`, `CARIBBEAN` |

### カテゴリ別バルク取得（fetch_by_category）

Enum カテゴリの全値について一括取得します。リクエスト間に 1 秒のポーライトディレイが自動挿入されます。

```python
from market.nasdaq import ScreenerCollector
from market.nasdaq import Exchange, Sector

collector = ScreenerCollector()

# 全取引所（NASDAQ・NYSE・AMEX）の銘柄を一括取得
results = collector.fetch_by_category(Exchange)
for exchange_name, df in results.items():
    print(f"{exchange_name}: {len(df)} 銘柄")
# nasdaq: 3500 銘柄
# nyse: 2800 銘柄
# amex: 300 銘柄

# 全 11 セクターを一括取得
sector_results = collector.fetch_by_category(Sector)

# ベースフィルタと組み合わせ（NYSE + 全セクター）
from market.nasdaq import ScreenerFilter
base = ScreenerFilter(exchange=Exchange.NYSE)
results = collector.fetch_by_category(Sector, base_filter=base)
```

### CSV ダウンロード（download_csv, download_by_category）

データを CSV ファイルとして保存します。エンコードは Excel での文字化けを防ぐ utf-8-sig を使用。

```python
from market.nasdaq import ScreenerCollector, ScreenerFilter, Exchange
from pathlib import Path

collector = ScreenerCollector()

# 全銘柄を 1 ファイルに保存
path = collector.download_csv(
    output_dir="data/raw/nasdaq",
    filename="all_stocks.csv",
)
print(f"保存先: {path}")

# フィルタ付きで保存
path = collector.download_csv(
    filter=ScreenerFilter(exchange=Exchange.NASDAQ),
    output_dir="data/raw/nasdaq",
    filename="nasdaq_stocks.csv",
)
```

カテゴリ別に複数の CSV を一括保存する場合:

```python
from market.nasdaq import ScreenerCollector
from market.nasdaq import Sector
from pathlib import Path

collector = ScreenerCollector()

# セクター別に CSV を生成（ファイル名: sector_{value}_{YYYY-MM-DD}.csv）
paths = collector.download_by_category(
    Sector,
    output_dir=Path("data/raw/nasdaq"),
)
for path in paths:
    print(path)
# data/raw/nasdaq/sector_technology_2026-03-06.csv
# data/raw/nasdaq/sector_finance_2026-03-06.csv
# ...（全 11 セクター分）
```

## API リファレンス

### コレクタークラス

#### `ScreenerCollector`

NASDAQ Stock Screener API からデータを取得するメインクラス。`DataCollector` ABC を実装。

```python
from market.nasdaq import ScreenerCollector, NasdaqSession

# デフォルト（セッションを内部生成）
collector = ScreenerCollector()

# セッションを注入（テスト・設定カスタマイズ時）
from market.nasdaq import NasdaqConfig, RetryConfig
session = NasdaqSession(
    config=NasdaqConfig(polite_delay=2.0, timeout=60.0),
    retry_config=RetryConfig(max_attempts=5),
)
collector = ScreenerCollector(session=session)
```

| メソッド | 説明 | 戻り値 |
|---------|------|--------|
| `fetch(**kwargs)` | フィルタ付きでスクリーニングデータを取得 | `pd.DataFrame` |
| `validate(df)` | データの正常性を検証（空でないか、必須カラムがあるか） | `bool` |
| `fetch_by_category(category, *, base_filter)` | Enum カテゴリの全値について一括取得 | `dict[str, pd.DataFrame]` |
| `download_csv(filter, *, output_dir, filename)` | データを CSV ファイルに保存 | `Path` |
| `download_by_category(category, *, output_dir, base_filter)` | カテゴリ別に複数 CSV を保存 | `list[Path]` |

**DataFrame カラム:**

| カラム | 型 | 説明 |
|-------|----|------|
| `symbol` | `str` | ティッカーシンボル（例: `"AAPL"`） |
| `name` | `str` | 銘柄名（例: `"Apple Inc. Common Stock"`） |
| `last_sale` | `float \| None` | 最終売買価格（例: `227.63`） |
| `net_change` | `float \| None` | 値幅（例: `-1.95`） |
| `pct_change` | `float \| None` | 変化率（例: `-0.849`） |
| `market_cap` | `int \| None` | 時価総額（例: `3435123456789`） |
| `country` | `str` | 上場国（例: `"United States"`） |
| `ipo_year` | `int \| None` | IPO 年（例: `1980`） |
| `volume` | `int \| None` | 出来高（例: `48123456`） |
| `sector` | `str` | セクター（例: `"Technology"`） |
| `industry` | `str` | 業種（例: `"Computer Manufacturing"`） |
| `url` | `str` | NASDAQ の銘柄ページ相対パス |

### NasdaqSession

curl_cffi ベースの HTTP セッション。ボットブロッキング対策を内蔵。

```python
from market.nasdaq import NasdaqSession, NasdaqConfig, RetryConfig

session = NasdaqSession(
    config=NasdaqConfig(
        polite_delay=2.0,    # リクエスト間の待機秒数（デフォルト: 1.0）
        delay_jitter=1.0,    # 待機時間のランダム幅（デフォルト: 0.5）
        impersonate="chrome120",  # TLS フィンガープリント（デフォルト: "chrome"）
        timeout=60.0,        # タイムアウト秒数（デフォルト: 30.0）
    ),
    retry_config=RetryConfig(
        max_attempts=5,       # 最大リトライ回数（デフォルト: 3、最大: 10）
        initial_delay=2.0,    # 初回リトライ待機秒数（デフォルト: 1.0）
        max_delay=60.0,       # 最大待機秒数（デフォルト: 30.0）
    ),
)

with session:
    response = session.get_with_retry(
        "https://api.nasdaq.com/api/screener/stocks",
        params={"exchange": "nasdaq", "limit": "0"},
    )
    print(response.status_code)  # 200
```

**特徴:**
- TLS フィンガープリント偽装（Chrome・Edge・Safari 対応）
- User-Agent ローテーション（12 種類）
- HTTP 403/429 の自動検出と指数バックオフリトライ
- リトライ時のセッション（ブラウザ偽装）ローテーション
- SSRF 防止のためのホワイトリスト制限（`api.nasdaq.com` のみ許可）
- コンテキストマネージャー対応

| メソッド | 説明 |
|---------|------|
| `get(url, params)` | ポーライトディレイ・User-Agent ローテーション付き GET |
| `get_with_retry(url, params)` | 指数バックオフリトライ付き GET |
| `rotate_session()` | TLS フィンガープリントを新しいブラウザに切り替え |
| `close()` | セッションを閉じてリソースを解放 |

### ScreenerFilter

フィルタ条件を指定するデータクラス。`None` のフィールドはクエリパラメータから除外されます。

```python
from market.nasdaq import ScreenerFilter, Exchange, Sector

f = ScreenerFilter(exchange=Exchange.NASDAQ, sector=Sector.TECHNOLOGY)
print(f.to_params())
# {'exchange': 'nasdaq', 'sector': 'technology', 'limit': '0'}
```

| フィールド | 型 | デフォルト | 説明 |
|-----------|----|-----------|------|
| `exchange` | `Exchange \| None` | `None` | 取引所フィルタ |
| `marketcap` | `MarketCap \| None` | `None` | 時価総額フィルタ |
| `sector` | `Sector \| None` | `None` | セクターフィルタ |
| `recommendation` | `Recommendation \| None` | `None` | アナリスト推奨フィルタ |
| `region` | `Region \| None` | `None` | 地域フィルタ |
| `country` | `str \| None` | `None` | 国フィルタ（文字列または `Country` Enum） |
| `limit` | `int` | `0` | 取得件数上限（`0` で全件） |

### データ型

#### `StockRecord`

NASDAQ Screener API からの生レスポンス 1 件を表すデータクラス。

```python
from market.nasdaq import StockRecord

record = StockRecord(
    symbol="AAPL",
    name="Apple Inc. Common Stock",
    last_sale="$227.63",
    net_change="-1.95",
    pct_change="-0.849%",
    market_cap="3,435,123,456,789",
    country="United States",
    ipo_year="1980",
    volume="48,123,456",
    sector="Technology",
    industry="Computer Manufacturing",
    url="/market-activity/stocks/aapl",
)
```

#### `FilterCategory`

`fetch_by_category` / `download_by_category` に渡せる Enum 型のエイリアス。

```python
from market.nasdaq import FilterCategory
from market.nasdaq import Exchange, MarketCap, Sector, Recommendation, Region

categories: list[FilterCategory] = [Exchange, MarketCap, Sector, Recommendation, Region]
```

### 設定クラス

#### `NasdaqConfig`

HTTP 動作設定。すべてのフィールドは検証付き（範囲外の値は `ValueError`）。

| フィールド | デフォルト | 有効範囲 | 説明 |
|-----------|-----------|---------|------|
| `polite_delay` | `1.0` | 0.0〜60.0 秒 | リクエスト間の最小待機時間 |
| `delay_jitter` | `0.5` | 0.0〜30.0 秒 | 待機時間に加えるランダム幅 |
| `impersonate` | `"chrome"` | - | TLS フィンガープリントのターゲット |
| `timeout` | `30.0` | 1.0〜300.0 秒 | HTTP タイムアウト |
| `user_agents` | `()` | - | User-Agent リスト（空の場合はデフォルトを使用） |

#### `RetryConfig`

指数バックオフのリトライ設定。

| フィールド | デフォルト | 有効範囲 | 説明 |
|-----------|-----------|---------|------|
| `max_attempts` | `3` | 1〜10 | 最大リトライ回数 |
| `initial_delay` | `1.0` | - | 初回リトライ待機秒数 |
| `max_delay` | `30.0` | - | 最大待機秒数 |
| `exponential_base` | `2.0` | - | 指数バックオフの底 |
| `jitter` | `True` | - | ランダムジッター付加 |

### 例外クラス

| 例外 | 説明 | 主な属性 |
|------|------|---------|
| `NasdaqError` | 全 NASDAQ 例外の基底クラス | `message` |
| `NasdaqAPIError` | API が 4xx/5xx を返したとき | `url`, `status_code`, `response_body` |
| `NasdaqRateLimitError` | HTTP 403/429 でレート制限検出時 | `url`, `retry_after` |
| `NasdaqParseError` | JSON レスポンスのパース失敗時 | `raw_data`, `field` |

```python
from market.nasdaq import (
    ScreenerCollector,
    NasdaqError,
    NasdaqRateLimitError,
    NasdaqAPIError,
    NasdaqParseError,
)

collector = ScreenerCollector()
try:
    df = collector.fetch()
except NasdaqRateLimitError as e:
    print(f"レート制限: {e.message}, retry_after={e.retry_after}")
except NasdaqAPIError as e:
    print(f"API エラー: HTTP {e.status_code} - {e.message}")
except NasdaqParseError as e:
    print(f"パースエラー: フィールド={e.field}")
except NasdaqError as e:
    print(f"NASDAQ エラー: {e.message}")
```

## トラブルシューティング

### レート制限（HTTP 403/429）

```
NasdaqRateLimitError: Rate limit detected: HTTP 429
```

**解決策:**
- `NasdaqConfig` で `polite_delay` を長く設定する（例: `polite_delay=3.0`）
- `RetryConfig` で `max_attempts` を増やす
- リクエスト頻度を下げる

```python
from market.nasdaq import ScreenerCollector, NasdaqSession, NasdaqConfig, RetryConfig

session = NasdaqSession(
    config=NasdaqConfig(polite_delay=3.0, delay_jitter=1.0),
    retry_config=RetryConfig(max_attempts=5, initial_delay=2.0),
)
collector = ScreenerCollector(session=session)
```

### パースエラー

```
NasdaqParseError: Missing or invalid 'data.table.rows' key in response
```

**解決策:**
- NASDAQ API のレスポンス形式が変わっている可能性があります
- `NasdaqSession.get_with_retry()` を使って生レスポンスを確認する

## モジュール構成

```
market/nasdaq/
├── __init__.py      # パッケージエクスポート
├── collector.py     # ScreenerCollector（DataCollector ABC 実装）
├── session.py       # NasdaqSession（HTTP セッション）
├── types.py         # フィルタ Enum・設定・データ型定義
├── errors.py        # 例外クラス
├── parser.py        # JSON パーサー・数値クリーナー
├── constants.py     # API URL・ヘッダー・デフォルト値
└── README.md        # このファイル
```

## 関連モジュール

- [market.etfcom](../etfcom/README.md) - ETF.com からの ETF データ取得
- [market.yfinance](../yfinance/README.md) - Yahoo Finance データ取得
- [market.cache](../cache/README.md) - キャッシュ機能
