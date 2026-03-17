---
name: deep-research
description: "金融市場・投資テーマ専用のディープリサーチワークフローを実行します。複数ソースからデータ収集→クロス検証→深掘り分析→レポート生成までを自動化します。"
allowed-tools: Read, Write, Glob, Grep, Task, WebSearch, WebFetch, ToolSearch, Bash, AskUserQuestion
---

# Deep Research Skill

金融市場・投資テーマの本格的なリサーチを実行するスキルです。

## 目的

このスキルは以下の場合に使用します：

- **個別銘柄の深掘り分析**: 財務・バリュエーション・カタリストを包括的に分析
- **セクター比較分析**: ローテーション判断、銘柄選定の支援
- **マクロ経済分析**: 経済指標・金融政策の影響を分析
- **テーマ投資分析**: バリューチェーン・投資機会を特定

## いつ使用するか

### 明示的な使用（ユーザー要求）

- `/deep-research` コマンド
- 「銘柄を詳しく分析して」「セクターを比較して」などの直接的な要求
- 「投資リサーチをして」「ディープダイブして」などの要求

### プロアクティブ使用（提案）

以下の状況では、このスキルの使用を提案してください：

1. **投資判断の支援が必要な場合**
    - 「この銘柄買うべき？」→ 分析が必要であることを説明し、/deep-research を提案

2. **市場環境の理解が必要な場合**
    - 「今の経済状況は？」→ マクロ分析を提案

3. **テーマ投資の検討**
    - 「AI関連に投資したい」→ テーマ分析を提案

## リサーチタイプ

### 1. Stock（個別銘柄分析）

```
/deep-research --type stock --ticker AAPL
```

**分析内容**:
- 財務健全性（3-5年トレンド、収益性、キャッシュフロー）
- バリュエーション（絶対・相対、ヒストリカルレンジ）
- ビジネス品質（競争優位性、経営陣、資本配分）
- カタリスト・リスク（イベント、10-Kリスク要因）

**データソース優先度**: SEC EDGAR > market_analysis > Web

### 2. Sector（セクター分析）

```
/deep-research --type sector --sector technology
```

**分析内容**:
- セクター概観（市場規模、主要プレイヤー）
- パフォーマンス比較（バリュエーション、リターン）
- ローテーション分析（モメンタム、サイクル）
- 銘柄選定（リーダー/ラガード、バリュー機会）

**データソース優先度**: market_analysis > SEC EDGAR > Web

### 3. Macro（マクロ経済分析）

```
/deep-research --type macro
```

**分析内容**:
- 経済健全性（GDP、雇用、インフレ）
- 金融政策（Fed政策、金利見通し）
- 市場への影響（アセットクラス、セクター）
- シナリオ分析（ベース/ブル/ベア）

**データソース優先度**: FRED > Web > market_analysis

### 4. Theme（テーマ投資分析）

```
/deep-research --type theme --topic "AI半導体"
```

**分析内容**:
- テーマ定義（構造的ドライバー、TAM、普及曲線）
- バリューチェーン（受益者マッピング）
- 投資機会（ピュアプレイ vs 分散、ETF）
- タイミング（カタリスト、エントリーポイント）

**データソース優先度**: Web > SEC EDGAR > market_analysis

## 深度オプション

| 深度 | スコープ | 用途 |
|------|---------|------|
| quick | 主要指標のみ、1ページサマリー | 素早いスクリーニング |
| standard | 包括的指標、5-10ページレポート | 通常の投資分析 |
| comprehensive | 5年分析、シナリオ分析、15-30ページ | 本格的な投資判断 |

## 出力形式

| 形式 | 説明 | 用途 |
|------|------|------|
| article | note記事形式 | note.com投稿 |
| report | 分析レポート形式 | 本格的な投資分析 |
| memo | 投資メモ形式 | 素早い意思決定 |

## 処理フロー

```
Phase 0: 設定確認
├── パラメータバリデーション
├── 出力フォルダ作成
└── [HF0] リサーチ方針確認

Phase 1: データ収集（並列）
├── SEC EDGAR → 10-K/10-Q/8-K/Form4
├── market_analysis → yfinance/FRED
├── Web検索 → 最新ニュース・分析
└── RSS → ニュースフィード

Phase 2: クロス検証
├── dr-cross-validator → 複数ソース照合
├── dr-confidence-scorer → 信頼度スコア算出
├── dr-bias-detector → バイアス検出
└── [HF1] 中間結果確認

Phase 3: 深掘り分析（タイプ別）
├── Stock: dr-stock-analyzer
├── Sector: dr-sector-analyzer
├── Macro: dr-macro-analyzer
└── Theme: dr-theme-analyzer

Phase 4: 出力生成
├── dr-report-generator → 形式別レポート
├── dr-visualizer → チャート・図表
└── [HF2] 最終確認
```

## 品質管理

### クロス検証

- 複数ソースでデータを照合
- 信頼度Tier（1-3）に基づく重み付け
- 矛盾検出と解決

### 信頼度スコアリング

```
confidence_score = weighted_average(
  source_reliability × 0.4,
  corroboration × 0.3,
  temporal_relevance × 0.2,
  consistency × 0.1
)
```

### バイアス検出

- センチメントバイアス（ブル/ベアの偏り）
- ソース集中バイアス
- 視点バイアス（反対意見の欠如）

## リソース

### ./research-templates/

リサーチタイプ別のテンプレート：
- stock-analysis.md
- sector-analysis.md
- macro-analysis.md
- theme-analysis.md

### ./output-templates/

出力形式別のテンプレート：
- note-article.md
- analysis-report.md
- investment-memo.md

## 使用例

### 個別銘柄分析

```bash
/deep-research --type stock --ticker AAPL --depth standard --output report
```

### セクター分析

```bash
/deep-research --type sector --sector technology --depth comprehensive --output article
```

### マクロ経済分析

```bash
/deep-research --type macro --depth standard --output memo
```

### テーマ投資分析

```bash
/deep-research --type theme --topic "AI半導体" --depth comprehensive --output article
```

## 既存システム連携

### 記事化連携

```
/deep-research → research/{id}/05_output/
                      ↓
/finance-edit --from-research {id}
                      ↓
articles/{article_id}/
```

## ベストプラクティス

1. **適切な深度を選択**: quickは概要把握、comprehensiveは重要な投資判断に
2. **出力形式を目的に合わせる**: note投稿ならarticle、社内分析ならreport
3. **HFポイントでの確認**: 中間結果を確認し、必要に応じて追加データを収集
4. **信頼度スコアを確認**: 低信頼度データには注意

## 注意事項

- 本スキルは情報提供を目的としており、投資助言ではありません
- 生成されたレポートは投資判断の参考情報としてご利用ください
- データの正確性は可能な限り検証していますが、保証はできません
- 最終的な投資判断は自己責任で行ってください

## トラブルシューティング

### データ収集が失敗する

- ネットワーク接続を確認
- SEC EDGAR APIのレート制限に注意
- 代替ソースを試行

### 信頼度スコアが低い

- 追加のデータソースを収集
- 深度をcomprehensiveに変更
- 手動での検証を検討

### レポート生成エラー

- 分析データが十分か確認
- 出力形式を変更して試行
