# Bloomberg データ要件メモ — CA Strategy Buy-and-Hold バックテスト

## 概要

現在 yfinance ベースで実行しているバックテストを Bloomberg データに切り替えるために必要なデータ項目・形式・取得方法を整理する。

---

## 1. 必要データ一覧

### 1.1 株価データ（最重要）

| 項目 | Bloomberg Field | 用途 | 現在のソース |
|------|----------------|------|-------------|
| 日次終値 | `PX_LAST` | ポートフォリオリターン算出 | yfinance |
| 出来高 | `PX_VOLUME` | 流動性確認（任意） | — |

**対象銘柄**:
- ポートフォリオ銘柄: 30/60/90銘柄（`portfolio_weights.csv` 参照）
- ユニバース全銘柄: 約390銘柄（`list_portfolio_20151224.json` 参照）
- ベンチマークETF: `TOK`（MSCI Kokusai）、`ACWI`、`URTH`

**期間**: 2015-12-01 ～ 現在（バックテスト開始: 2016-01-04）

**頻度**: 日次（DAILY）

### 1.2 時価総額データ（MCap ベンチマーク用）

| 項目 | Bloomberg Field | 用途 | 現在のソース |
|------|----------------|------|-------------|
| 時価総額（USD） | `CUR_MKT_CAP` | MCap 加重ベンチマーク構築 | `MSCI_Mkt_Cap_USD_MM`（初期値のみ） |

**現在の問題**: 初期時点（2015-12-24）の MCap のみ使用し、その後はドリフト。
Bloomberg では定期スナップショット（四半期）を取得し、`rebalance_schedule` として渡すことで精度向上可能。

**取得頻度: 四半期で十分な理由**

MCap の日次変動は2つの要因に分解される:

```
MCap(t) = 株価(t) × 発行済株式数(t)
```

- **株価変動**: Buy-and-Hold ドリフト式 `w_i(t+1) = w_i(t) × (1+r_i(t)) / Σ[w_j(t) × (1+r_j(t))]` が日次で正確に反映する。追加データ不要。
- **発行済株式数変動**: 自社株買い（年1-3%程度）、増資（年0-1回）、SO行使等。日次の変動はほぼゼロで、四半期で累積誤差を補正すれば十分。

主要インデックスのリバランス頻度も四半期:

| インデックス | リバランス頻度 |
|---|---|
| MSCI Kokusai | 四半期（2月・5月・8月・11月） |
| S&P 500 | 四半期 |
| FTSE 100 | 四半期 |

日次 MCap で日次リバランスすると、実際のインデックスの挙動と乖離し、ベンチマーク比較の意義が薄れる。

**結論**: 四半期末（3月末, 6月末, 9月末, 12月末）のスナップショットを推奨。

### 1.3 コーポレートアクション

| 項目 | Bloomberg Field | 用途 | 現在のソース |
|------|----------------|------|-------------|
| 上場廃止日 | `DELIST_DT` | 消失銘柄の除外日 | 手動 JSON |
| M&A 完了日 | — (News/CA) | 合併・買収による除外 | 手動 JSON |

**現在**: 8件を `corporate_actions.json` に手動登録。
Bloomberg の Corporate Actions データで自動化可能だが、現状の手動管理で十分。

### 1.4 セクター・国情報

| 項目 | Bloomberg Field | 用途 | 現在のソース |
|------|----------------|------|-------------|
| GICS セクター | `GICS_SECTOR_NAME` | セクター中立化 | `list_portfolio_20151224.json` |
| 国 | `COUNTRY_ISO` | US/Non-US 分類 | `list_portfolio_20151224.json` |

**静的データ**: 既にユニバース JSON に含まれているため追加取得不要。

---

## 2. ティッカー形式

### 2.1 パイプライン全体のティッカー体系

パイプライン内部は**ショートティッカー**（`AAPL`, `DIS`, `AVGO`）で統一されている。Bloomberg フルティッカーとの変換は **Bloomberg API 入出力の境界でのみ** 発生する。

```
[Bloomberg API]                [パイプライン内部]
AAPL US Equity  ──split()[0]──→  AAPL
SAP GY Equity   ──split()[0]──→  SAP
ENB CN Equity   ──split()[0]──→  ENB
```

各コンポーネントのティッカー形式:

| コンポーネント | 形式 | 例 | 変換要否 |
|---|---|---|---|
| `list_portfolio_20151224.json` | Bloomberg フル | `AAPL US Equity` | API 入力にそのまま使用 |
| `portfolio_weights.csv` | ショート | `AAPL` | 変換不要 |
| `corporate_actions.json` | ショート | `ALTR` | 変換不要 |
| Parquet 列名 | ショート | `AAPL` | 変換不要 |
| `return_calculator.py` | ショート | weights の key | 変換不要 |
| `run_buyhold_backtest.py` | ショート | weights の key | 変換不要 |

### 2.2 Bloomberg データ取得時の変換

**変換が必要なのは1箇所だけ**: Bloomberg API から取得した結果を Parquet に保存する際に、列名をショートティッカーにする。

```python
# Bloomberg API 呼び出し（フルティッカーで入力）
options = BloombergFetchOptions(
    securities=["AAPL US Equity", "SAP GY Equity", "ENB CN Equity"],
    fields=["PX_LAST"],
)
results = fetcher.get_historical_data(options)

# Parquet 保存（ショートティッカーに変換）
prices = {}
for result in results:
    short_ticker = result.security.split()[0]  # "AAPL US Equity" → "AAPL"
    prices[short_ticker] = result.data["PX_LAST"]

pd.DataFrame(prices).to_parquet("ca_portfolio_close_prices.parquet")
```

**パイプライン内部のコードは一切変更不要**。現在 yfinance 用に存在する `ticker_converter.py`（Bloomberg `GY` → yfinance `.DE` 等のサフィックス変換）も不要になる。

### 2.3 注意事項

消失銘柄の Bloomberg Ticker は期限切れの場合がある:
- `ALTR US Equity` → Intel 買収済み（2015-12）
- `EMC US Equity` → Dell 統合済み（2016-09）
- これらは `corporate_actions.json` で管理済みのため、株価取得失敗は想定内

---

## 3. ファイル形式・テーブル形状

### 3.1 株価データ（Parquet）

**ファイル**: `data/raw/bloomberg/stocks/ca_portfolio_close_prices.parquet`（等）

```
Shape: (日数, 銘柄数)   例: (2551, 32)
Index: DatetimeIndex     例: 2016-01-04 ~ 2026-02-25
Columns: ティッカー名    例: ['AAPL', 'MSFT', 'AVGO', ...]
Values: float64 終値     例: 94.92, 16.41, 31.85, ...
```

**現在と同一形状**。列名は Bloomberg Ticker のショート部分（`AAPL US Equity` → `AAPL`）。

```python
# 例: 30銘柄ポートフォリオの株価テーブル
#              AAPL      MSFT      AVGO  ...
# 2016-01-04  94.92   162.41    31.85  ...
# 2016-01-05  93.00   160.53    31.69  ...
# ...
```

**ファイル一覧**:

| ファイル | 内容 | 推定サイズ |
|---------|------|-----------|
| `ca_portfolio_close_prices.parquet` | 30銘柄 × ~2550日 | ~0.4MB |
| `ca_portfolio_60_close_prices.parquet` | 60銘柄 × ~2550日 | ~0.7MB |
| `ca_portfolio_90_close_prices.parquet` | 90銘柄 × ~2550日 | ~1.1MB |
| `universe_benchmark_close_prices.parquet` | 全銘柄 × ~2550日 | ~5MB |
| `msci_benchmark_close_prices.parquet` | ETF 3本 × ~2550日 | ~0.1MB |

### 3.2 時価総額スナップショット（JSON）— 新規

**ファイル**: `data/raw/bloomberg/mcap/mcap_snapshots.json`

```json
{
  "snapshots": {
    "2016-03-31": {
      "AAPL": 586200.0,
      "MSFT": 438100.0,
      "AVGO": 52300.0
    },
    "2016-06-30": {
      "AAPL": 521500.0,
      "MSFT": 410200.0,
      "AVGO": 61200.0
    }
  },
  "unit": "USD_MM",
  "frequency": "quarterly"
}
```

**用途**: `return_calculator.py` の `calculate_mcap_benchmark_returns()` に `rebalance_schedule` として渡す。

```python
# rebalance_schedule の構築
rebalance_schedule: dict[date, dict[str, float]] = {}
for date_str, mcap_dict in snapshots["snapshots"].items():
    total = sum(mcap_dict.values())
    weights = {t: v / total for t, v in mcap_dict.items()}
    rebalance_schedule[date.fromisoformat(date_str)] = weights
```

### 3.3 コーポレートアクション（JSON）— 既存

**ファイル**: `research/ca_strategy_poc/config/corporate_actions.json`（変更不要）

```json
{
  "corporate_actions": [
    {
      "ticker": "ALTR",
      "company_name": "Altera Corporation",
      "action_date": "2015-12-31",
      "action_type": "delisting",
      "reason": "Acquired by Intel Corporation"
    }
  ]
}
```

---

## 4. Bloomberg API 取得コード例

### 4.1 株価取得

```python
from market.bloomberg import BloombergFetcher, BloombergFetchOptions

fetcher = BloombergFetcher()

# ポートフォリオ銘柄の株価取得
options = BloombergFetchOptions(
    securities=["AAPL US Equity", "MSFT US Equity", "AVGO US Equity"],
    fields=["PX_LAST"],
    start_date="2016-01-01",
    end_date="2026-02-28",
    periodicity=Periodicity.DAILY,
)
results = fetcher.get_historical_data(options)

# DataFrame に変換 → Parquet 保存
prices = {}
for result in results:
    short_ticker = result.security.split()[0]  # "AAPL US Equity" → "AAPL"
    prices[short_ticker] = result.data["PX_LAST"]

df = pd.DataFrame(prices)
df.to_parquet("data/raw/bloomberg/stocks/ca_portfolio_close_prices.parquet")
```

### 4.2 時価総額スナップショット取得

```python
# 四半期末の時価総額を取得
snapshot_dates = [
    "2016-03-31", "2016-06-30", "2016-09-30", "2016-12-31",
    "2017-03-31", "2017-06-30", # ... 省略 ... "2025-12-31",
]

snapshots = {}
for snap_date in snapshot_dates:
    options = BloombergFetchOptions(
        securities=universe_tickers,  # 全390銘柄
        fields=["CUR_MKT_CAP"],
        start_date=snap_date,
        end_date=snap_date,
    )
    results = fetcher.get_historical_data(options)
    mcap = {}
    for result in results:
        short = result.security.split()[0]
        if not result.is_empty:
            mcap[short] = float(result.data["CUR_MKT_CAP"].iloc[-1])
    snapshots[snap_date] = mcap
```

---

## 5. 現在のデータフローとの比較

```
=== 現在（yfinance）===
list_portfolio_20151224.json
  → Bloomberg_Ticker → yfinance suffix変換（.L, .PA, .DE 等）
  → yfinance API → Parquet キャッシュ
  → run_buyhold_backtest.py

=== Bloomberg 移行後 ===
list_portfolio_20151224.json
  → Bloomberg_Ticker をそのまま使用
  → Bloomberg BLPAPI → Parquet キャッシュ
  → run_buyhold_backtest.py（load_* 関数のパス変更のみ）
```

### 5.1 コード変更箇所（最小限）

| ファイル | 変更内容 |
|---------|---------|
| `run_buyhold_backtest.py` | `DATA_DIR` パスを `bloomberg/stocks/` に変更 |
| `run_buyhold_backtest.py` | `load_universe_mcap_weights()` を MCap スナップショット対応に拡張 |
| `run_buyhold_backtest.py` | MCap ベンチマークに `rebalance_schedule` を渡す |
| `run_buyhold_backtest.py` | ティッカーマッピング（`.L`, `.PA` 等のサフィックス処理）を削除 |

### 5.2 変更不要の箇所

- `return_calculator.py` — `rebalance_schedule` は既に実装済み
- `compute_metrics()` — データソースに依存しない
- `corporate_actions.json` — そのまま使用
- DGS10 リスクフリーレート — FRED から取得（Bloomberg 不要）

---

## 6. 非US銘柄の改善点

### 6.1 現在の問題

yfinance では一部の非US銘柄が取得できない（60銘柄で17欠落、90銘柄で26欠落）:

| 銘柄 | 理由 | Bloomberg 対応 |
|------|------|---------------|
| `BAYN` | バイエル（ドイツ）| `BAYN GY Equity` ✅ |
| `NESN` | ネスレ（スイス）| `NESN VX Equity` ✅ |
| `NOVN` | ノバルティス（スイス）| `NOVN VX Equity` ✅ |
| `SCMN` | スウォッチ（スイス）| `SCMN VX Equity` ✅ |
| `COLOB` | コロプラスト（デンマーク）| `COLOB DC Equity` ✅ |
| `HNR1` | ハノーバー（ドイツ）| `HNR1 GY Equity` ✅ |
| `KBC` | KBC（ベルギー）| `KBC BB Equity` ✅ |
| `ITV` | ITV（英国）| `ITV LN Equity` ✅ |
| `SHP` | シャイア（英国・買収済）| `SHP LN Equity` ✅ |
| `ITUB4` | イタウ（ブラジル）| `ITUB4 BZ Equity` ✅ |
| `005930` | サムスン（韓国）| `005930 KS Equity` ✅ |

**Bloomberg で全銘柄のデータ取得が可能** → 欠落率 0% が実現可能。

### 6.2 期待される改善

| ポートフォリオ | 現在の欠落 | Bloomberg後の欠落 | 影響 |
|--------------|-----------|-----------------|------|
| 30銘柄 | 0 | 0 | — |
| 60銘柄 | 17 (28%) | 0 | 重みの再配分が不要に |
| 90銘柄 | 26 (29%) | 0 | 重みの再配分が不要に |

---

## 7. 優先度

| 優先度 | データ | 理由 |
|--------|--------|------|
| **P0** | 全銘柄の日次終値 (`PX_LAST`) | バックテストの基盤、非US銘柄カバレッジ改善 |
| **P1** | MCap 四半期スナップショット (`CUR_MKT_CAP`) | MCap ベンチマークの精度向上 |
| **P2** | ベンチマーク ETF 終値 (`PX_LAST`) | TOK/ACWI/URTH は yfinance でも取得可能 |
| **P3** | コーポレートアクション自動化 | 現状の手動管理で十分 |

---

## 8. チェックリスト

Bloomberg データ準備時の確認事項:

- [ ] 全銘柄の Bloomberg Ticker が `list_portfolio_20151224.json` に含まれているか
- [ ] 日次終値の期間: 2015-12-01 ～ 現在をカバーしているか
- [ ] Parquet ファイルの形状: `(日数, 銘柄数)`, DatetimeIndex, 列名=ショートティッカー
- [ ] 消失銘柄（ALTR, EMC, MON 等）の株価は消失日前までのデータがあるか
- [ ] MCap スナップショットの四半期末日付が正しいか
- [ ] 非US銘柄の通貨: `PX_LAST` が USD 建てか現地通貨建てか確認

### 8.1 通貨の注意

yfinance は各銘柄の上場市場通貨で返す。Bloomberg も同様。
現在の実装は**現地通貨ベースのリターン**を使用しており、為替効果を含まない。

Bloomberg で USD 建てに統一する場合は以下のいずれか:
- (A) `PX_LAST` + Override `CRNCY=USD` → USD 建て取得
- (B) 現地通貨建て株価 + 為替レート → 手動換算

**推奨**: 現在と同じく現地通貨建て（変更コスト最小）。
USD 建て分析は別途追加機能として検討。
