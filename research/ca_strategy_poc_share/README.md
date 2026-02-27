# CA Strategy PoC — 共有パッケージ

競争優位性（Competitive Advantage）ベース投資戦略のポートフォリオ構築結果と、バックテスト再現に必要なデータ・設定・方法論の一式。

## 概要

| 項目 | 値 |
|------|-----|
| 投資ユニバース | MSCI Kokusai 構成銘柄 395銘柄 |
| スコア取得済み | 330銘柄（2,548件の主張を抽出・スコアリング） |
| 基準日 | 2015-12-24 |
| 価格データ期間 | 2015-12-24 〜 2026-02-27（3,170営業日） |
| 手法 | 決算トランスクリプトから AI（Claude Sonnet 4）で競争優位性の主張を抽出→スコアリング→セクター中立化→ポートフォリオ構築 |
| ポートフォリオ | 30 / 60 / 90 銘柄（セクター中立）+ TopN（中立化なし） |

---

## ディレクトリ構成

```
ca_strategy_poc_share/
│
├── data/                            # 元データ（バックテストの入力）
│   ├── list_portfolio_20151224.json #   銘柄マスタ（408件）
│   └── list_port_and_index_price_2015_2026.csv  # 日次価格（374列×3,170行）
│
├── config/                          # ポートフォリオ構築の設定
│   ├── universe.json                #   投資ユニバース定義（395銘柄）
│   ├── benchmark_weights.json       #   MSCI Kokusai セクターウェイト（10セクター）
│   └── ticker_mapping.json          #   Dead Ticker マッピング（26件）
│
├── scores/                          # 競争優位性スコア
│   └── phase2_scored.json           #   全330銘柄のスコア付き主張（2,548件）
│
├── portfolios/                      # 最終ポートフォリオ
│   ├── size_30/                     #   30銘柄版（実際は32、セクター制約による）
│   ├── size_60/                     #   60銘柄版（実際は61）
│   ├── size_90/                     #   90銘柄版（実際は90）
│   └── topn/                        #   TopN版（セクター中立化なし）
│
└── methodology/                     # 方法論ドキュメント
    ├── score_weight_methodology.md  #   スコア→ウェイト変換の全ロジック
    └── bloomberg_data_requirements.md # Bloomberg データ取得仕様
```

---

## データファイル詳細

### data/list_portfolio_20151224.json — 銘柄マスタ

MSCI Kokusai 構成銘柄の 2015-12-24 時点スナップショット。408エントリ（キーは内部ID）。

```json
{
  "Name": "Apple Inc.",
  "Country": "UNITED STATES",
  "GICS_Sector": "Information Technology",
  "GICS_Industry": "Technology Hardware, Storage & Peripherals",
  "MSCI_Mkt_Cap_USD_MM": 586070.4,
  "Bloomberg_Ticker": "AAPL US Equity",
  "FIGI": "BBG000B9XRY4"
}
```

| フィールド | 用途 |
|-----------|------|
| `Bloomberg_Ticker` | 価格CSVの列名とのマッチングキー |
| `GICS_Sector` | セクター中立化・ベンチマークウェイト算出 |
| `MSCI_Mkt_Cap_USD_MM` | 時価総額加重ベンチマーク構築 |

### data/list_port_and_index_price_2015_2026.csv — 日次価格

Bloomberg Terminal から取得した PX_LAST（分割調整済み、配当未含）。

| 項目 | 値 |
|------|-----|
| 列数 | 374（Date + 約370銘柄 + 3指数） |
| 行数 | 3,170営業日 |
| 期間 | 2015-12-24 〜 2026-02-27 |
| 列名形式 | Bloomberg Ticker（例: `AAPL US Equity`） |
| 欠損値 | 空白（休場・上場廃止等） |

指数列（ベンチマーク比較用）:

| 列名 | 説明 |
|------|------|
| `MXKO INDEX` | MSCI Kokusai（時価総額加重） |
| `MXKOEW INDEX` | MSCI Kokusai（等加重） |
| `MXWDJ INDEX` | MSCI World（参考） |

**注意**: PX_LAST は Price Return のみ。配当再投資を含む Total Return ではない。MXKO INDEX も Price Return のため、ポートフォリオとベンチマークの比較はフェア。

### config/universe.json — 投資ユニバース定義

銘柄マスタから生成した395銘柄のリスト。ポートフォリオ構築パイプラインの入力。

```json
{
  "_metadata": {
    "total_count": 395,
    "sector_counts": { "Consumer Discretionary": 68, ... }
  },
  "tickers": [
    {
      "ticker": "AAPL",
      "bloomberg_ticker": "AAPL US Equity",
      "company_name": "Apple Inc.",
      "gics_sector": "Information Technology",
      "country": "UNITED STATES"
    }
  ]
}
```

`ticker` フィールドが `scores/phase2_scored.json` および `portfolios/*/portfolio_weights.csv` のキーと対応する。

### config/benchmark_weights.json — セクターウェイト

MSCI Kokusai のセクター配分を、銘柄マスタの `MSCI_Mkt_Cap_USD_MM` 集計で近似。

```json
{
  "weights": {
    "Consumer Discretionary": 0.1303,
    "Consumer Staples": 0.1631,
    "Energy": 0.0553,
    "Financials": 0.1299,
    "Health Care": 0.1893,
    "Industrials": 0.1030,
    "Information Technology": 0.1798,
    "Materials": 0.0273,
    "Telecommunication Services": 0.0092,
    "Utilities": 0.0127
  }
}
```

セクター中立化ポートフォリオ（size_30/60/90）は、このウェイトに一致するようセクター配分を制約する。

### config/ticker_mapping.json — Dead Ticker マッピング

M&A・社名変更等で Bloomberg Ticker が変わった銘柄のマッピング（26件）。

```json
{
  "1715651D": { "ticker": "DD", "company_name": "EIDP, Inc.", "note": "DuPont歴史的ティッカー" },
  "1373183D": { "ticker": "AVGO", "company_name": "Broadcom Inc.", "note": "Avago Technologies→Broadcom" }
}
```

価格CSVの列名（例: `1373183D US Equity`）を現在のティッカー（`AVGO`）に変換する際に使用。

---

## スコアデータ

### scores/phase2_scored.json — 競争優位性スコア

全330銘柄の AI 評価済み主張データ。辞書形式（キー: ティッカー、値: 主張リスト）。

| 統計 | 値 |
|------|-----|
| 銘柄数 | 330 |
| 主張総数 | 2,548 |
| 銘柄あたり主張数 | 0〜16件（平均7.7件） |
| スコア範囲 | 0.100 〜 0.900 |
| スコア平均 | 0.528 |

各主張の構造:

| フィールド | 型 | 説明 |
|-----------|-----|------|
| `id` | string | 主張ID |
| `claim` | string | 主張テキスト（日本語） |
| `claim_type` | string | `competitive_advantage` 等 |
| `evidence` | string | トランスクリプトからの引用 |
| `final_confidence` | float | 最終確信度スコア（0.0〜1.0） |
| `rule_evaluation` | object | 適用ルールと評価詳細 |
| `kb1_evaluations` | object | KB1（12ルール）の個別評価 |
| `kb2_patterns` | object | KB2（却下 A-G / 高評価 I-V パターン）との照合 |
| `overall_reasoning` | string | 総合判定の推論プロセス |

---

## ポートフォリオデータ

### portfolios/size_{30,60,90}/ — セクター中立化ポートフォリオ

各サイズ共通で以下のファイルを含む:

| ファイル | 形式 | 内容 |
|----------|------|------|
| `portfolio_weights.csv` | CSV | `ticker,weight,sector,score,rationale_summary` |
| `portfolio_weights.json` | JSON | `as_of_date`, `holdings`, `sector_allocation`, `data_sources` |
| `portfolio_summary.md` | Markdown | セクター配分表 + 全銘柄ウェイト一覧 |
| `portfolio_analysis_report.md` | Markdown | 詳細分析（スコア分布、セクター特性、HHI等） |
| `rationale/<TICKER>_rationale.md` | Markdown | 銘柄別の選定根拠（スコア、主張一覧、競争優位性の評価） |

**バックテスト再現時の参照フロー**:
1. `portfolio_weights.csv` の `ticker` 列を取得
2. `config/ticker_mapping.json` で Dead Ticker を Bloomberg Ticker に変換
3. `data/list_port_and_index_price_2015_2026.csv` から該当列の日次価格を取得
4. `weight` 列で加重リターンを算出

各サイズの銘柄数:

| ポートフォリオ | 目標 | 実際の銘柄数 | rationale ファイル数 |
|---------------|------|-------------|-------------------|
| size_30 | 30 | 32 | 32 |
| size_60 | 60 | 61 | 61 |
| size_90 | 90 | 90 | 90 |

### portfolios/topn/ — セクター中立化なしポートフォリオ

スコア上位N銘柄を純粋に選定（セクター制約なし）。

| ファイル | ウェイト方式 | 列 |
|----------|------------|-----|
| `top30_score_weighted.csv` | スコア比例 | `ticker,weight,score,claim_count,structural_weight` |
| `top30_equal_weighted.csv` | 等ウェイト | 同上 |
| `top60_*.csv` | 同上 | 同上 |
| `top90_*.csv` | 同上 | 同上 |

---

## ティッカー変換ガイド

ポートフォリオの `ticker`（例: `AVGO`）から価格CSVの列名（例: `1373183D US Equity`）を引くには:

1. `config/universe.json` の `tickers[]` で `ticker` → `bloomberg_ticker` を検索
2. 見つからない場合、`config/ticker_mapping.json` で Dead Ticker の `bloomberg_ticker` を確認
3. 価格CSVの列名は `bloomberg_ticker` と一致する

該当する Dead Ticker の例:

| ポートフォリオ上の ticker | 価格CSV列名 | 理由 |
|--------------------------|-------------|------|
| `AVGO` | `1373183D US Equity` | Avago Technologies → Broadcom |
| `CCEP` | `9876641D US Equity` | Coca-Cola Enterprises → Europacific Partners |
| `DD` | `1715651D US Equity` | DuPont 歴史的ティッカー |

---

## 方法論

### methodology/score_weight_methodology.md

スコアからポートフォリオウェイトへの4段階変換を記述:

```
Phase 2: ScoredClaim（確信度付き主張）
    ↓  ScoreAggregator（ルール別重み付き加重平均）
Phase 3a: StockScore（銘柄別集約スコア）
    ↓  SectorNeutralizer（セクター内 Z-score → ランキング）
Phase 3b: RankedStock
    ↓  PortfolioBuilder（ベンチマークウェイト × セクター内スコア比例配分）
Phase 4: PortfolioHolding（最終ウェイト）
```

### methodology/bloomberg_data_requirements.md

Bloomberg Terminal からのデータ取得仕様（フィールド名、対象銘柄、期間、頻度）。

---

## バックテスト再現手順

### Step 1: データの準備

- `data/list_port_and_index_price_2015_2026.csv` を読み込む
- 1行目が Bloomberg Ticker 列名、2行目以降が日次価格
- `Date` 列を日付型に変換

### Step 2: ポートフォリオウェイトの取得

- `portfolios/size_30/portfolio_weights.csv` 等から `ticker` と `weight` を取得
- `weight` の合計は 1.0

### Step 3: ティッカー→価格列の名前解決

- `config/universe.json` で `ticker` → `bloomberg_ticker` を変換
- Dead Ticker は `config/ticker_mapping.json` を参照
- 変換後の `bloomberg_ticker` が価格CSVの列名と一致

### Step 4: 日次リターンの算出

```
daily_return[t] = price[t] / price[t-1] - 1
portfolio_return[t] = Σ (weight[i] × daily_return[i][t])
```

- Buy-and-Hold（ドリフトウェイト）の場合、初期ウェイトのみ使用し日次でリバランスしない
- ベンチマーク: `MXKO INDEX` 列の日次リターン

### Step 5: ベンチマーク比較

- 価格CSVの `MXKO INDEX`（時価総額加重）、`MXKOEW INDEX`（等加重）と比較
- 累積リターン、Sharpe Ratio、最大ドローダウン等を算出

---

## クロスチェック観点

- [ ] `scores/phase2_scored.json` のスコア集約ロジック（加重平均）の妥当性
- [ ] セクター中立化によるウェイト配分の正確性（ベンチマークウェイトとの一致）
- [ ] 個別銘柄のスコアと `rationale/` の主張内容の整合性
- [ ] TopN版（セクター中立化なし）とセクター中立版の銘柄差異と要因
- [ ] Dead Ticker マッピングの正確性（価格CSVとの照合）
