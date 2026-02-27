---
description: セクター・業界の包括的分析を実行します。市場データ・SEC Filings・業界レポート・専門メディアを収集し、クロス検証・セクター比較分析・レポート生成までを自動化します。
argument-hint: <SECTOR> [--subsector Semiconductors] [--companies NVDA,AMD,INTC] [--sector-etf SMH] [--analysis-period 5y] [--output report|article|memo]
---

# /dr-industry - セクター・業界ディープリサーチ

セクター・業界の包括的なリサーチを実行するコマンドです。

## 使用例

```bash
# 基本的な使用（セクターのみ指定）
/dr-industry Technology

# サブセクターを指定
/dr-industry Technology --subsector Semiconductors

# 企業群を明示指定
/dr-industry Healthcare --subsector Pharmaceuticals --companies JNJ,PFE,MRK,ABBV,LLY,BMY,AZN

# セクター ETF を指定
/dr-industry Technology --subsector Semiconductors --sector-etf SMH

# note記事形式で出力
/dr-industry Energy --output article

# 投資メモ形式で出力
/dr-industry Financials --subsector Banks --output memo

# 分析期間を変更
/dr-industry Technology --analysis-period 3y
```

## 入力パラメータ

| パラメータ | 必須 | デフォルト | 説明 |
|-----------|------|-----------|------|
| `sector` | Yes | - | 分析対象のセクター（例: Technology, Healthcare, Energy） |
| `--subsector` | No | セクター全体 | サブセクター（例: Semiconductors, Pharmaceuticals） |
| `--companies` | No | プリセットから自動取得 | 分析対象企業のティッカー一覧（カンマ区切り） |
| `--sector-etf` | No | セクターから自動判定 | セクター代表 ETF（例: XLK, SMH） |
| `--analysis-period` | No | 5y | 分析期間（1y, 3y, 5y） |
| `--output` | No | report | 出力形式（report, article, memo） |

### 利用可能なセクター

| セクター | 代表 ETF |
|---------|---------|
| Technology | XLK |
| Healthcare | XLV |
| Financials | XLF |
| Consumer_Discretionary | XLY |
| Consumer_Staples | XLP |
| Energy | XLE |
| Industrials | XLI |
| Materials | XLB |
| Utilities | XLU |
| Real_Estate | XLRE |
| Communication_Services | XLC |

### 利用可能なサブセクター

| セクター | サブセクター |
|---------|-------------|
| Technology | Semiconductors, Software_Infrastructure |
| Healthcare | Pharmaceuticals, Biotechnology, Medical_Devices |
| Financials | Banks, Insurance, Capital_Markets |
| Consumer_Discretionary | Retail, E_Commerce, Restaurants |
| Energy | Oil_Gas, Renewable_Energy, Energy_Services |

### 出力形式

| 形式 | 説明 | 分量目安 |
|------|------|---------|
| report | セクター分析レポート形式 | 10-20ページ |
| article | note記事形式 | 2,000-4,000字 |
| memo | 投資メモ形式 | 1ページ |

## 処理フロー

パラメータをパースした後、dr-industry スキルをプリロードし、`dr-industry-lead` エージェントに制御を委譲して Agent Teams ワークフローを実行します。

```
Phase 0: パラメータ解析（コマンド側で実行）
├── sector（必須）の解析・検証
├── オプションパラメータの解析
├── dr-industry スキルのプリロード
└── dr-industry-lead に委譲

dr-industry-lead（Agent Teams ワークフロー）
├── TeamCreate（dr-industry-team）
├── T0: Setup + [HF0] パラメータ確認（必須）
├── タスク登録（T1-T9）・依存関係設定（addBlockedBy）
├── チームメイト起動・タスク割り当て
├── 実行監視（HF1, HF2）
└── シャットダウン・クリーンアップ（TeamDelete）
```

### 各 Phase の詳細

```
Phase 0: Setup（Lead 自身）
  T0: research-meta.json 生成 + ディレクトリ作成
  [HF0] パラメータ確認（必須）

Phase 1: Data Collection（5並列）
  T1: finance-market-data     セクター ETF + 企業群の株価・財務指標
  T2: finance-sec-filings     企業群の 10-K/10-Q・財務データ（非致命的）
  T3: finance-web（ニュース） セクターニュース・アナリストレポート
  T4: industry-researcher      業界構造・競争環境・バリューチェーン（致命的）
  T5: finance-web（業界メディア）業界専門メディアの最新記事

Phase 2: Integration + Validation（2並列）
  T6: dr-source-aggregator    5ファイル → raw-data.json 統合
  T7: dr-cross-validator      データ照合 + 信頼度付与
  [HF1] データ品質レポート（任意）

Phase 3: Analysis
  T8: dr-sector-analyzer       セクター比較分析（5ピラー）

Phase 4: Output（2並列）
  T9: dr-report-generator     レポート生成 + チャートスクリプト出力
  T10: chart-renderer           チャート出力（Lead が Bash で Python 実行）
  [HF2] 最終出力提示（任意）

Phase 5: Cleanup
  TeamDelete + 完了通知
```

## 実行手順

### Step 1: パラメータ解析

1. **引数のパース**
   - 第1引数を `sector` として取得（必須）
   - `--subsector`, `--companies`, `--sector-etf`, `--analysis-period`, `--output` をオプションとして取得

2. **セクターの検証**
   - sector が空の場合はエラーを返す
   - 利用可能なセクター一覧と照合

3. **dr-industry スキルのプリロード**
   ```
   Skill: dr-industry
   ```

### Step 2: dr-industry-lead への委譲

パース済みのパラメータを `dr-industry-lead` エージェントに渡し、Agent Teams ワークフローを開始します。

```
Task: dr-industry-lead
Input:
  sector: {sector}
  subsector: {subsector}（指定時のみ）
  companies: {companies}（指定時のみ）
  sector_etf: {sector_etf}（指定時のみ）
  analysis_period: {analysis_period}
  output: {output_format}
```

dr-industry-lead は以下を実行します:

1. **Phase 0: Setup** - research-meta.json の生成とディレクトリ作成
2. **[HF0]** - パラメータ確認（必須、ユーザー承認待ち）
3. **Phase 1: Data Collection** - 5エージェント並列でデータ収集
4. **Phase 2: Integration + Validation** - データ統合とクロス検証
5. **[HF1]** - データ品質レポート（任意）
6. **Phase 3: Analysis** - 5ピラーの包括的セクター比較分析
7. **Phase 4: Output** - レポートとチャート生成
8. **[HF2]** - 最終出力提示（任意）
9. **Phase 5: Cleanup** - チームのシャットダウンとクリーンアップ

## 出力ディレクトリ構造

```
research/DR_industry_{YYYYMMDD}_{SECTOR}/
├── 00_meta/
│   └── research-meta.json
├── 01_data_collection/
│   ├── market-data.json        <- T1
│   ├── sec-filings.json        <- T2
│   ├── web-data.json           <- T3
│   ├── industry-data.json      <- T4
│   ├── web-media.json          <- T5
│   └── raw-data.json           <- T6（統合版）
├── 02_validation/
│   └── cross-validation.json   <- T7
├── 03_analysis/
│   └── sector-analysis.json    <- T8
└── 04_output/
    ├── report.md               <- T9
    ├── render_charts.py        <- T9（生成スクリプト）
    └── charts/                 <- T10（生成画像）
        ├── sector_vs_spy.png
        ├── valuation_heatmap.png
        ├── financial_radar.png
        ├── market_share.png
        └── sector_rotation.png
```

## 分析ピラー（5つの分析軸）

| ピラー | 内容 |
|--------|------|
| セクター概況分析 | 市場規模、成長率、セクターローテーション動向、マクロ経済感応度 |
| 競争構造分析 | 市場シェア、参入障壁、バリューチェーン、Porter's Five Forces |
| 企業間比較分析 | 財務指標比較、バリュエーション比較、成長性比較、競争優位性スコアリング |
| カタリスト・リスク分析 | セクター固有リスク、規制動向、技術変化、マクロ影響 |
| 銘柄選定分析 | セクター内トップピック、投資テーマ別推奨、リスクリワード比ランキング |

## 完了報告

```markdown
## リサーチ完了

### セクター情報
- **セクター**: {sector}
- **サブセクター**: {subsector}
- **リサーチID**: {research_id}

### 収集結果
- 市場データ（T1）: {market_data_status}
- SEC Filings（T2）: {sec_status}
- Web ニュース（T3）: {web_status}
- 業界分析（T4）: {industry_status}
- 業界メディア（T5）: {media_status}

### 分析結果
- セクター評価: {sector_assessment}
- トップピック: {top_picks}
- リスクプロファイル: {risk_profile}

### 生成ファイル
- `research/{research_id}/04_output/report.md`
- `research/{research_id}/04_output/charts/`（5チャート）

### 次のステップ
**記事化**: `/finance-edit --from-research {research_id}`
**個別銘柄深掘り**: `/dr-stock {top_pick_ticker}`
```

## エラーハンドリング

### セクターが指定されていない

```
エラー: セクター名が必要です

使用法: /dr-industry <SECTOR> [オプション]

例:
  /dr-industry Technology
  /dr-industry Technology --subsector Semiconductors
  /dr-industry Healthcare --companies JNJ,PFE,MRK,ABBV,LLY
```

### 無効なセクター名

```
エラー: 無効なセクター名です

指定されたセクター: "{sector}"

利用可能なセクター:
  Technology, Healthcare, Financials, Consumer_Discretionary, Consumer_Staples,
  Energy, Industrials, Materials, Utilities, Real_Estate, Communication_Services

利用可能なセクターは data/config/industry-research-presets.json を参照してください。
```

### 致命的タスクの失敗

致命的タスク（T1: market-data, T4: industry-researcher, T6: aggregator, T8: analyzer, T9: reporter）が失敗した場合、ワークフローは中断されます。

```
エラー: 致命的タスクが失敗しました

失敗タスク: T4 (業界分析)
原因: industry-researcher 実行失敗 - プリセットが見つかりません

対処法:
- セクター名が正しいか確認してください
- data/config/industry-research-presets.json にセクターが登録されているか確認してください
- 未登録セクターの場合は --companies で企業を手動指定してください
```

### 非致命的タスクの失敗

非致命的タスク（T2: sec-filings, T3: web-news, T5: web-media, T7: validator, T10: chart-renderer）が失敗した場合、警告付きで続行します。

```
警告: 一部の処理が失敗しました

失敗した処理:
- T2 (SEC Filings): SEC EDGAR 取得失敗
- T5 (業界メディア): ネットワークエラー

成功した処理で続行します。レポートは部分データに基づいて生成されます。
```

## 関連コマンド・エージェント

### 関連コマンド

| コマンド | 説明 |
|----------|------|
| `/dr-stock` | 個別銘柄の包括的分析 |
| `/finance-research` | 金融記事のリサーチワークフロー |
| `/finance-edit` | 金融記事の編集ワークフロー |
| `/generate-market-report` | 週次マーケットレポート生成 |

### 使用エージェント

| エージェント | Phase | 説明 |
|-------------|-------|------|
| `dr-industry-lead` | - | リーダー（Agent Teams ワークフロー制御） |
| `finance-market-data` | 1 | 市場データ取得 |
| `finance-sec-filings` | 1 | SEC Filings 取得 |
| `finance-web` | 1 | Web 検索（ニュース + 業界メディアの2インスタンス） |
| `industry-researcher` | 1 | 業界リサーチ |
| `dr-source-aggregator` | 2 | ソース統合 |
| `dr-cross-validator` | 2 | クロス検証 + 信頼度スコアリング |
| `dr-sector-analyzer` | 3 | セクター比較分析（5ピラー） |
| `dr-report-generator` | 4 | レポート生成 |

### 関連ファイル

- **スキル定義**: `.claude/skills/dr-industry/SKILL.md`
- **リーダーエージェント**: `.claude/agents/deep-research/dr-industry-lead.md`
- **プリセット設定**: `data/config/industry-research-presets.json`
- **競争優位性フレームワーク**: `analyst/Competitive_Advantage/analyst_YK/dogma/dogma_v1.0.md`

## 注意事項

- 本コマンドは情報提供を目的としており、投資助言ではありません
- 生成されたレポートは投資判断の参考情報としてご利用ください
- データの正確性は可能な限り検証していますが、保証はできません
- 最終的な投資判断は自己責任で行ってください
- 深度モードはありません。常にフルパイプラインを実行します
- 業界分析では industry-researcher（T4）が致命的依存です。プリセット設定が必須です
