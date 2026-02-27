---
description: 個別銘柄の包括的分析を実行します。株価・財務・SEC Filings・業界データを収集し、クロス検証・深掘り分析・レポート生成までを自動化します。
argument-hint: <TICKER> [--peer-tickers MSFT,GOOGL] [--industry-preset Technology/Semiconductors] [--analysis-period 5y] [--output report|article|memo]
---

# /dr-stock - 個別銘柄ディープリサーチ

個別銘柄の包括的なリサーチを実行するコマンドです。

## 使用例

```bash
# 基本的な使用（ティッカーのみ指定）
/dr-stock AAPL

# ピアグループを明示指定
/dr-stock NVDA --peer-tickers AMD,INTC,AVGO,QCOM --industry-preset Technology/Semiconductors

# note記事形式で出力
/dr-stock MSFT --output article

# 投資メモ形式で出力
/dr-stock GOOGL --output memo

# 分析期間を変更
/dr-stock TSLA --analysis-period 3y
```

## 入力パラメータ

| パラメータ | 必須 | デフォルト | 説明 |
|-----------|------|-----------|------|
| `ticker` | Yes | - | 分析対象のティッカーシンボル（例: AAPL, MSFT） |
| `--peer-tickers` | No | プリセットから自動取得 | ピアグループのティッカー一覧（カンマ区切り） |
| `--industry-preset` | No | ticker から自動判定 | 業界プリセットキー（例: Technology/Semiconductors） |
| `--analysis-period` | No | 5y | 分析期間（1y, 3y, 5y） |
| `--output` | No | report | 出力形式（report, article, memo） |

### 利用可能な業界プリセット

| セクター | サブ業界 |
|---------|---------|
| Technology | Semiconductors, Software_Infrastructure |
| Healthcare | Pharmaceuticals |
| Financials | Banks |
| Consumer_Discretionary | Retail |
| Energy | Oil_Gas |

プリセット設定: `data/config/industry-research-presets.json`

### 出力形式

| 形式 | 説明 | 分量目安 |
|------|------|---------|
| report | 分析レポート形式 | 5-15ページ |
| article | note記事形式 | 2,000-4,000字 |
| memo | 投資メモ形式 | 1ページ |

## 処理フロー

パラメータをパースした後、dr-stock スキルをプリロードし、`dr-stock-lead` エージェントに制御を委譲して Agent Teams ワークフローを実行します。

```
Phase 0: パラメータ解析（コマンド側で実行）
├── ticker（必須）の解析・検証
├── オプションパラメータの解析
├── dr-stock スキルのプリロード
└── dr-stock-lead に委譲

dr-stock-lead（Agent Teams ワークフロー）
├── TeamCreate（dr-stock-team）
├── T0: Setup + [HF0] パラメータ確認（必須）
├── タスク登録（T1-T8）・依存関係設定（addBlockedBy）
├── チームメイト起動・タスク割り当て
├── 実行監視（HF1, HF2）
└── シャットダウン・クリーンアップ（TeamDelete）
```

### 各 Phase の詳細

```
Phase 0: Setup（Lead 自身）
  T0: research-meta.json 生成 + ディレクトリ作成
  [HF0] パラメータ確認（必須）

Phase 1: Data Collection（4並列）
  T1: finance-market-data     株価・財務指標・ピアグループデータ
  T2: finance-sec-filings     10-K/10-Q/8-K/Form4
  T3: finance-web              ニュース・アナリストレポート
  T4: industry-researcher      業界ポジション・競争優位性

Phase 2: Integration + Validation（2並列）
  T5: dr-source-aggregator    raw-data.json 統合
  T6: dr-cross-validator      データ照合 + 信頼度付与
  [HF1] データ品質レポート（任意）

Phase 3: Analysis
  T7: dr-stock-analyzer       包括的銘柄分析（4ピラー）

Phase 4: Output（2並列）
  T8: dr-report-generator     レポート生成 + チャートスクリプト出力
  T9: chart-renderer           チャート出力（Lead が Bash で Python 実行）
  [HF2] 最終出力提示（任意）

Phase 5: Cleanup
  TeamDelete + 完了通知
```

## 実行手順

### Step 1: パラメータ解析

1. **引数のパース**
   - 第1引数を `ticker` として取得（必須）
   - `--peer-tickers`, `--industry-preset`, `--analysis-period`, `--output` をオプションとして取得

2. **ティッカーの検証**
   - ticker が空の場合はエラーを返す

3. **dr-stock スキルのプリロード**
   ```
   Skill: dr-stock
   ```

### Step 2: dr-stock-lead への委譲

パース済みのパラメータを `dr-stock-lead` エージェントに渡し、Agent Teams ワークフローを開始します。

```
Task: dr-stock-lead
Input:
  ticker: {ticker}
  peer_tickers: {peer_tickers}（指定時のみ）
  industry_preset: {industry_preset}（指定時のみ）
  analysis_period: {analysis_period}
  output: {output_format}
```

dr-stock-lead は以下を実行します:

1. **Phase 0: Setup** - research-meta.json の生成とディレクトリ作成
2. **[HF0]** - パラメータ確認（必須、ユーザー承認待ち）
3. **Phase 1: Data Collection** - 4エージェント並列でデータ収集
4. **Phase 2: Integration + Validation** - データ統合とクロス検証
5. **[HF1]** - データ品質レポート（任意）
6. **Phase 3: Analysis** - 4ピラーの包括的銘柄分析
7. **Phase 4: Output** - レポートとチャート生成
8. **[HF2]** - 最終出力提示（任意）
9. **Phase 5: Cleanup** - チームのシャットダウンとクリーンアップ

## 出力ディレクトリ構造

```
research/DR_stock_{YYYYMMDD}_{TICKER}/
├── 00_meta/
│   └── research-meta.json
├── 01_data_collection/
│   ├── market-data.json        <- T1
│   ├── sec-filings.json        <- T2
│   ├── web-data.json           <- T3
│   ├── industry-data.json      <- T4
│   └── raw-data.json           <- T5（統合版）
├── 02_validation/
│   └── cross-validation.json   <- T6
├── 03_analysis/
│   └── stock-analysis.json     <- T7
└── 04_output/
    ├── report.md               <- T8
    ├── render_charts.py        <- T8（生成スクリプト）
    └── charts/                 <- T9（生成画像）
        ├── price_chart.png
        ├── peer_comparison.png
        ├── financial_trend.png
        ├── valuation_heatmap.png
        └── sector_performance.png
```

## 分析ピラー（4つの分析軸）

| ピラー | 内容 |
|--------|------|
| 財務健全性分析 | 売上CAGR、利益率、ROE/ROIC、D/E、FCF、5年トレンド |
| バリュエーション分析 | DCF簡易試算、P/E・EV/EBITDA等のピア比較、ヒストリカルレンジ |
| ビジネス品質分析 | 競争優位性、経営陣評価、資本配分、dogma.mdフレームワーク |
| カタリスト・リスク分析 | イベントカレンダー、リスクマトリックス、ブル/ベース/ベアの3シナリオ |

## 完了報告

```markdown
## リサーチ完了

### 銘柄情報
- **ティッカー**: {ticker}
- **リサーチID**: {research_id}

### 収集結果
- 市場データ（T1）: {market_data_status}
- SEC Filings（T2）: {sec_status}
- Web検索（T3）: {web_status}
- 業界分析（T4）: {industry_status}

### 分析結果
- 投資品質: {investment_quality}
- バリュエーション: {valuation_assessment}
- リスクプロファイル: {risk_profile}

### 生成ファイル
- `research/{research_id}/04_output/report.md`
- `research/{research_id}/04_output/charts/`（5チャート）

### 次のステップ
**記事化**: `/finance-edit --from-research {research_id}`
```

## エラーハンドリング

### ティッカーが指定されていない

```
エラー: ティッカーシンボルが必要です

使用法: /dr-stock <TICKER> [オプション]

例:
  /dr-stock AAPL
  /dr-stock NVDA --peer-tickers AMD,INTC,AVGO,QCOM
```

### 致命的タスクの失敗

致命的タスク（T1: market-data, T2: sec-filings, T5: aggregator, T7: analyzer, T8: reporter）が失敗した場合、ワークフローは中断されます。

```
エラー: 致命的タスクが失敗しました

失敗タスク: T1 (市場データ)
原因: yfinance データ取得失敗 - ticker not found

対処法:
- ティッカーシンボルが正しいか確認してください
- ネットワーク接続を確認してください
```

### 非致命的タスクの失敗

非致命的タスク（T3: web-search, T4: industry, T6: validator, T9: chart-renderer）が失敗した場合、警告付きで続行します。

```
警告: 一部の処理が失敗しました

失敗した処理:
- T3 (Web検索): ネットワークエラー

成功した処理で続行します。レポートは部分データに基づいて生成されます。
```

## 関連コマンド・エージェント

### 関連コマンド

| コマンド | 説明 |
|----------|------|
| `/finance-research` | 金融記事のリサーチワークフロー |
| `/finance-edit` | 金融記事の編集ワークフロー |
| `/generate-market-report` | 週次マーケットレポート生成 |

### 使用エージェント

| エージェント | Phase | 説明 |
|-------------|-------|------|
| `dr-stock-lead` | - | リーダー（Agent Teams ワークフロー制御） |
| `finance-market-data` | 1 | 市場データ取得 |
| `finance-sec-filings` | 1 | SEC Filings 取得 |
| `finance-web` | 1 | Web 検索 |
| `industry-researcher` | 1 | 業界リサーチ |
| `dr-source-aggregator` | 2 | ソース統合 |
| `dr-cross-validator` | 2 | クロス検証 + 信頼度スコアリング |
| `dr-stock-analyzer` | 3 | 包括的銘柄分析（4ピラー） |
| `dr-report-generator` | 4 | レポート生成 |

### 関連ファイル

- **スキル定義**: `.claude/skills/dr-stock/SKILL.md`
- **リーダーエージェント**: `.claude/agents/deep-research/dr-stock-lead.md`
- **プリセット設定**: `data/config/industry-research-presets.json`
- **競争優位性フレームワーク**: `analyst/Competitive_Advantage/analyst_YK/dogma/dogma_v1.0.md`
- **設計書**: `docs/project/research-restructure/dr-stock-lead-design.md`

## 注意事項

- 本コマンドは情報提供を目的としており、投資助言ではありません
- 生成されたレポートは投資判断の参考情報としてご利用ください
- データの正確性は可能な限り検証していますが、保証はできません
- 最終的な投資判断は自己責任で行ってください
- 深度モードはありません。常にフルパイプラインを実行します
