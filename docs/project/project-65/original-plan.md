# BSE（ボンベイ証券取引所）データ取得モジュール設計

## Context

インド株式市場（BSE）のデータを `src/market/bse/` として追加する。BSE は公式の公開 REST API を提供していないが、`bseindia.com` のウェブサイト内部 API（JSON/CSV）が事実上のデータソースとして利用可能。BseIndiaApi 等の既存ライブラリを参考に、独自の BSE クライアントライブラリを構築する。

**取得対象データ:**
- ヒストリカル株価（OHLCV）
- Bhavcopy（日次全銘柄集約データ）
- 企業情報・財務データ（決算、財務諸表）
- 企業開示情報（アナウンスメント、コーポレートアクション）
- インデックスデータ（SENSEX 等）

---

## API エンドポイント

ベース URL: `https://api.bseindia.com/BseIndiaAPI/api`

| カテゴリ | エンドポイント | 用途 |
|---------|-------------|------|
| 株価 | `/getScripHeaderData/w` | リアルタイム OHLC |
| 株価 | `/StockPriceCSVDownload/w` | ヒストリカル CSV |
| 株価 | `/StockReachGraph/w` | 12ヶ月価格・出来高 |
| 株価 | `/HighLow/w` | 52 週高値安値 |
| Bhavcopy | `/download/BhavCopy/Equity/BhavCopy_BSE_CM_0_0_0_{YYYYMMDD}_F_0000.CSV` | 日次集約 |
| 企業情報 | `/ComHeadernew/w` | メタ情報 |
| 企業情報 | `/TabResults_PAR/w` | 決算スナップショット |
| 企業情報 | `/AnnSubCategoryGetData/w` | アナウンスメント |
| 企業情報 | `/DefaultData/w` | コーポレートアクション |
| 企業情報 | `/Corpforthresults/w` | 決算カレンダー |
| インデックス | `/IndexArchDailyAll/w` | 全指数日次 |
| インデックス | `/ProduceCSVForDate/w` | 指数ヒストリカル CSV |
| 銘柄検索 | `/PeerSmartSearch/w` | シンボル検索（HTML） |
| 市場 | `/MktRGainerLoserData/w` | 値上がり・値下がり |
| 市場 | `/advanceDecline/w` | 上昇下降銘柄数 |

**認証:** 不要（User-Agent + Referer ヘッダー必須）
**レート制限:** lookup 系 15 RPS、その他 8 RPS

---

## モジュール構成

```
src/market/bse/
├── __init__.py              # 公開 API エクスポート
├── constants.py             # URL, ヘッダー, カラムマップ, レート制限値
├── errors.py                # BseError 階層（MarketError ではなく Exception 継承）
├── types.py                 # BseConfig, RetryConfig, enum, データレコード
├── session.py               # BseSession（httpx, スロットル, リトライ）
├── parsers.py               # エンドポイント別レスポンスパーサー
└── collectors/
    ├── __init__.py           # コレクター再エクスポート
    ├── quote.py              # QuoteCollector（DataCollector ABC）
    ├── bhavcopy.py           # BhavcopyCollector（DataCollector ABC）
    ├── corporate.py          # CorporateCollector（企業情報・開示）
    └── index.py              # IndexCollector（DataCollector ABC）
```

---

## クラス設計

### BseSession (`session.py`)

httpx ベースの HTTP セッション。NASDAQ の `NasdaqSession` パターン参考。

- `get(url, params)` - 単一リクエスト（ポライトディレイ付き）
- `get_with_retry(url, params)` - 指数バックオフリトライ
- `download(url)` - CSV/バイナリダウンロード
- コンテキストマネージャー対応
- SSRF 防止（ALLOWED_HOSTS ホワイトリスト）
- User-Agent ローテーション

### QuoteCollector (`collectors/quote.py`)

`DataCollector` ABC 準拠。株価データ取得。

- `fetch(**kwargs) -> pd.DataFrame` - ヒストリカル OHLCV
- `validate(df) -> bool` - 必須カラム検証
- `fetch_quote(scrip_code) -> ScripQuote` - リアルタイム引用
- `fetch_historical(scrip_code, start, end) -> pd.DataFrame`

### BhavcopyCollector (`collectors/bhavcopy.py`)

`DataCollector` ABC 準拠。日次一括データ。

- `fetch(**kwargs) -> pd.DataFrame` - 指定日の Bhavcopy
- `validate(df) -> bool`
- `fetch_equity(date) -> pd.DataFrame`
- `fetch_derivative(date) -> pd.DataFrame`
- `fetch_date_range(start, end) -> pd.DataFrame`

### CorporateCollector (`collectors/corporate.py`)

企業情報・開示（非 ABC、異種型を返すため）。

- `get_company_info(scrip_code) -> dict`
- `get_financial_results(scrip_code) -> list[FinancialResult]`
- `get_announcements(scrip_code, ...) -> list[Announcement]`
- `get_corporate_actions(scrip_code) -> list[CorporateAction]`
- `search_scrip(query) -> list[dict]`

### IndexCollector (`collectors/index.py`)

`DataCollector` ABC 準拠。インデックスデータ。

- `fetch(**kwargs) -> pd.DataFrame`
- `validate(df) -> bool`
- `list_indices() -> list[str]`
- `fetch_historical(index_name, start, end) -> pd.DataFrame`

---

## エラー階層

```
BseError(Exception)
├── BseAPIError          # HTTP 4xx/5xx（url, status_code, response_body）
├── BseRateLimitError    # HTTP 429（url, retry_after）
├── BseParseError        # レスポンスパース失敗（raw_data, field）
└── BseValidationError   # 入力検証エラー（field, value）
```

**変更対象の既存ファイル:**
- `src/market/errors.py` - BSE エラーのインポート・再エクスポート追加
- `src/market/types.py` - `DataSource.BSE = "bse"` 追加

---

## 実装フェーズ

### Phase 1: Foundation（基盤）

| ファイル | 内容 |
|---------|------|
| `bse/__init__.py` | プレースホルダー |
| `bse/constants.py` | URL, ヘッダー, レート制限値 |
| `bse/errors.py` | エラー階層 4 クラス |
| `bse/types.py` | BseConfig, RetryConfig, BhavcopyType, ScripGroup enum |
| `bse/session.py` | BseSession（httpx + スロットル + リトライ） |
| `market/errors.py` | BSE エラー再エクスポート追加 |
| `market/types.py` | `DataSource.BSE` 追加 |

### Phase 2: Quote & Historical（株価データ）

| ファイル | 内容 |
|---------|------|
| `bse/parsers.py` | `parse_quote_response`, `parse_historical_csv` |
| `bse/collectors/quote.py` | QuoteCollector |

### Phase 3: Bhavcopy（日次一括データ）

| ファイル | 内容 |
|---------|------|
| `bse/parsers.py` | `parse_bhavcopy_csv` 追加 |
| `bse/collectors/bhavcopy.py` | BhavcopyCollector |

### Phase 4: Index（インデックス）

| ファイル | 内容 |
|---------|------|
| `bse/parsers.py` | `parse_index_data` 追加 |
| `bse/collectors/index.py` | IndexCollector |
| `bse/types.py` | IndexName enum 拡張 |

### Phase 5: Corporate（企業情報・開示）

| ファイル | 内容 |
|---------|------|
| `bse/parsers.py` | corporate 系パーサー追加 |
| `bse/collectors/corporate.py` | CorporateCollector |
| `bse/types.py` | FinancialResult, Announcement, CorporateAction データクラス |

### Phase 6: Integration（統合・最適化）

| ファイル | 内容 |
|---------|------|
| `bse/__init__.py` | 公開 API 完成 |
| `market/__init__.py` | BSE インポート追加 |
| キャッシュ統合 | SQLiteCache 利用 |
| 統合テスト | 実 API テスト（`@pytest.mark.integration`） |

---

## 参照すべき既存ファイル

| 参照先 | 用途 |
|--------|------|
| `src/market/base_collector.py` | DataCollector ABC インターフェース |
| `src/market/nasdaq/session.py` | セッション設計（ポライトディレイ、リトライ、SSRF 防止） |
| `src/market/nasdaq/collector.py` | DataCollector ABC 準拠パターン、DI |
| `src/market/edinet/client.py` | httpx ベースクライアント、レートリミッター |
| `src/market/errors.py` | エラー階層の統合ポイント |
| `src/market/types.py` | DataSource enum、MarketDataResult |
| `src/market/cache/cache.py` | SQLiteCache 再利用 |

---

## テスト構成

```
tests/market/bse/
├── conftest.py              # 共有フィクスチャ（モックレスポンス、サンプル CSV）
├── unit/
│   ├── test_constants.py
│   ├── test_errors.py
│   ├── test_types.py
│   ├── test_session.py      # httpx モック
│   ├── test_parsers.py      # 各パーサーの正常・異常・エッジケース
│   ├── test_quote.py
│   ├── test_bhavcopy.py
│   ├── test_index.py
│   └── test_corporate.py
├── property/
│   └── test_parsers_property.py  # Hypothesis: 数値クリーニング、CSV ラウンドトリップ
└── integration/
    └── test_bse_integration.py   # 実 API（pytest.mark.integration）
```

## 検証方法

1. `make check-all` で全品質チェック通過
2. Phase 1 完了後: `BseSession` の単体テスト（モック httpx でリトライ・スロットル検証）
3. Phase 2 完了後: サンプル scrip_code（例: 500209 = Infosys）でヒストリカルデータ取得確認
4. Phase 3 完了後: 直近営業日の Bhavcopy CSV ダウンロード・パース確認
5. Phase 5 完了後: Infosys の決算・アナウンスメント取得確認
6. 統合テスト: `uv run pytest tests/market/bse/integration/ -v -m integration`
