# 計画: Difyワークフローの Claude Code 再現・アップグレード

## Context

`analyst/dify/` にDifyワークフロー（KY投資判断・競争優位性評価）が設計されている。これをClaude Codeで再現し、Difyの制約を超える機能拡張を行う。`analyst/design/` フォルダに設計ドキュメントを配置する。

**Difyの制約 → Claude Codeでの解決:**
- KB chunking/RAG → 全KBファイル（25個, ~62KB）を直接読み込み。検索漏れゼロ
- 静的KB4（10-K手動アップロード） → SEC EDGAR MCP toolsでライブ取得。常に最新
- 直列10ノード → Agent Teamsで並列実行（Phase 1: 3並列、Phase 3: 2並列）
- 市場データなし → yfinance/FRED連携
- 手動精度比較 → phase2_KYデータとの自動精度検証

---

## 成果物一覧

### 1. `analyst/design/` フォルダ（設計ドキュメント）

| ファイル | 内容 |
|---------|------|
| `analyst/design/workflow_design.md` | ワークフロー詳細設計書（Dify設計書の Claude Code 版） |
| `analyst/design/dify_comparison.md` | Dify vs Claude Code の比較表・移行ガイド |

### 2. コマンド・スキル

| ファイル | 内容 |
|---------|------|
| `.claude/commands/ca-eval.md` | `/ca-eval TICKER` コマンド定義 |
| `.claude/skills/ca-eval/SKILL.md` | 競争優位性評価スキル定義 |

### 3. エージェント（6個新規、2個既存再利用）

| エージェント | ファイル | 新規/既存 |
|-------------|---------|----------|
| `ca-eval-lead` | `.claude/agents/deep-research/ca-eval-lead.md` | **新規** (Agent Teamsリーダー) |
| `ca-report-parser` | `.claude/agents/ca-report-parser.md` | **新規** |
| `ca-claim-extractor` | `.claude/agents/ca-claim-extractor.md` | **新規** |
| `ca-fact-checker` | `.claude/agents/ca-fact-checker.md` | **新規** |
| `ca-pattern-verifier` | `.claude/agents/ca-pattern-verifier.md` | **新規** |
| `ca-report-generator` | `.claude/agents/ca-report-generator.md` | **新規** (既存 competitive-advantage-critique のロジックを統合) |
| `finance-sec-filings` | `.claude/agents/finance-sec-filings.md` | 既存再利用 |
| `industry-researcher` | `.claude/agents/deep-research/industry-researcher.md` | 既存再利用 |

---

## ワークフロー設計

### 全体構成: 10タスク・5フェーズ

```
/ca-eval ORLY
    |
    Phase 0: Setup (Lead直接実行)
    |-- [T0] research-meta.json作成 + ディレクトリ作成
    |       [HF0] パラメータ確認
    |
    Phase 1: データ収集 (3並列)
    |-- [T1] sec-collector (finance-sec-filings) ----+
    |-- [T2] report-parser (ca-report-parser) -------+ 並列
    |-- [T3] industry (industry-researcher) ---------+
    |
    Phase 2: 主張抽出 + ルール適用 (直列)
    |-- [T4] extractor (ca-claim-extractor)
    |       blockedBy: [T1, T2, T3]
    |
    Phase 3: ファクトチェック + パターン検証 (2並列)
    |-- [T5] fact-checker (ca-fact-checker) ----------+
    |-- [T6] pattern-verifier (ca-pattern-verifier) --+ 並列
    |       blockedBy: [T4]
    |       [HF1] 中間品質レポート
    |
    Phase 4: レポート生成 + 検証 (直列)
    |-- [T7] reporter (ca-report-generator)
    |       blockedBy: [T5, T6]
    |-- [T8] Lead: レポート3層検証
    |-- [T9] Lead: 精度検証 (phase2_KYデータがある場合)
    |       [HF2] 最終出力
    |
    Phase 5: Cleanup (TeamDelete)
```

### research_dir 構造

```
research/CA_eval_{YYYYMMDD}_{TICKER}/
├── 00_meta/
│   └── research-meta.json
├── 01_data_collection/
│   ├── sec-data.json              ← T1 (SEC EDGAR ライブデータ)
│   ├── parsed-report.json         ← T2 (構造化アナリストレポート)
│   └── industry-context.json      ← T3 (業界・競争環境)
├── 02_claims/
│   └── claims.json                ← T4 (主張 + ルール評価)
├── 03_verification/
│   ├── fact-check.json            ← T5 (事実検証)
│   └── pattern-verification.json  ← T6 (パターン照合)
└── 04_output/
    ├── report.md                  ← T7 (評価レポート)
    ├── structured.json            ← T7 (構造化JSON)
    ├── verified-report.md         ← T8 (検証済みレポート)
    ├── verification-results.json  ← T8 (検証詳細)
    └── accuracy-report.json       ← T9 (精度検証、該当銘柄のみ)
```

### 各タスク詳細

**T1 (SEC Filings)**: `finance-sec-filings` 既存エージェント。MCP toolsで10-K/10-Q/8-K/インサイダー取引を取得。**Dify KB4の完全置換**。Fatal=Yes。

**T2 (Report Parser)**: アナリストレポートを構造化。①期初レポートと②四半期レビューを区別（ルール12対応）。セクション・日付の帰属情報を付与。Fatal=Yes。

**T3 (Industry Context)**: `industry-researcher` 既存エージェント。業界構造・競争環境を収集。dogma.mdの評価基準を適用。Fatal=No（欠損でも続行可能）。

**T4 (Claim Extraction + Rule Application)**: Difyステップ1+2を統合。**KB1（8ルール）+ KB3（5 few-shot）+ dogma.mdを全て直接読み込み**。RAG不要のため検索漏れゼロ。5-15件の主張を抽出し、12ルールを適用。確信度スケール（10/30/50/70/90%）で評価。Fatal=Yes。

**T5 (Fact Check)**: Difyステップ3。claims.jsonの事実主張をSECデータと照合。verified/contradicted/unverifiable を判定。contradicted→ルール9自動適用（確信度10%）。**SEC EDGAR MCPツールで追加検証も可能**。Fatal=No。

**T6 (Pattern Verification)**: Difyステップ4。**KB2（12パターン）を全て直接読み込み**。却下パターンA-G + 高評価パターンI-Vと照合。確信度を調整。Fatal=No。

**T7 (Report Generation)**: Difyステップ5。T4+T5+T6の結果を統合し、Markdownレポート + 構造化JSONを生成。**既存 competitive-advantage-critique エージェントの評価ロジック（Steps 3.1-3.5、スコアリング体系）を統合**。フィードバックテンプレート埋め込み。Fatal=Yes。

**T8 (Report Verification)**: Difyステップ6。Lead直接実行。3層検証（JSON-レポート整合 / KYルール準拠 / パターン一貫性）。

**T9 (Accuracy Scoring)**: **Difyにない新機能**。Lead直接実行。phase2_KYデータとAI出力を比較。平均乖離±10%以内を目標。対象: CHD, COST, LLY, MNST, ORLY。

### 依存関係マトリクス

```
T1: {}                    # Phase 1: 独立
T2: {}                    # Phase 1: 独立
T3: {}                    # Phase 1: 独立
T4: {T1: required, T2: required, T3: optional}  # Phase 2
T5: {T4: required}        # Phase 3: 並列
T6: {T4: required}        # Phase 3: 並列
T7: {T5: optional, T6: optional, T4: required}  # Phase 4
T8: {T7: required}        # Phase 4
T9: {T8: required}        # Phase 4
```

---

## 設計判断

| 判断 | 根拠 |
|------|------|
| Difyステップ1+2をT4に統合 | Claude CodeではKB1+KB3を全て直接読み込み可能。RAG分離の必要なし |
| T5とT6を並列化 | 事実検証（SECデータ）とパターン照合（KB2）は独立した検証軸 |
| competitive-advantage-critique を ca-report-generator に置換 | Agent Teams対応 + 上流検証結果の統合 + Markdown/JSON両出力が必要 |
| T8・T9をLead直接実行 | dr-stock-leadのチャート描画パターンに準拠。軽量な比較タスク |
| KB4をSEC EDGAR MCPに置換 | 常に最新データ、手動アップロード不要、任意の米国上場企業に対応可能 |

---

## 実装手順

### Step 1: ドキュメント作成（`analyst/design/`）
1. `analyst/design/workflow_design.md` — 詳細設計書
2. `analyst/design/dify_comparison.md` — Dify比較表

### Step 2: コマンド・スキル作成
3. `.claude/commands/ca-eval.md`
4. `.claude/skills/ca-eval/SKILL.md`

### Step 3: Leadエージェント作成
5. `.claude/agents/deep-research/ca-eval-lead.md` — dr-stock-lead.mdをテンプレートとして使用

### Step 4: ワーカーエージェント作成
6. `.claude/agents/ca-report-parser.md`
7. `.claude/agents/ca-claim-extractor.md`
8. `.claude/agents/ca-fact-checker.md`
9. `.claude/agents/ca-pattern-verifier.md`
10. `.claude/agents/ca-report-generator.md`

### Step 5: CLAUDE.md 更新
11. コマンド一覧にca-evalを追加
12. エージェント一覧に新規6エージェントを追加

---

## 検証方法

1. `/ca-eval ORLY` で実行し、エラーなく最終出力まで到達することを確認
2. `04_output/structured.json` のJSON構造がDify設計書§6のスキーマに準拠していることを確認
3. `04_output/accuracy-report.json` で、ORLYの平均乖離が±10%以内であることを確認
4. 5銘柄（CHD, COST, LLY, MNST, ORLY）での精度検証を実施

---

## 参照ファイル

| 用途 | パス |
|------|------|
| Leadエージェントのテンプレート | `.claude/agents/deep-research/dr-stock-lead.md` |
| 既存評価エージェント（ロジック移植元） | `.claude/agents/competitive-advantage-critique.md` |
| Dify詳細設計書 | `analyst/memo/dify_workflow_design.md` |
| Dify操作ガイド | `analyst/dify/dify_operation_guide.md` |
| Y版Dogma | `analyst/Competitive_Advantage/analyst_YK/dogma.md` |
| KB1ルール集 | `analyst/dify/kb1_rules/` (8ファイル) |
| KB2パターン集 | `analyst/dify/kb2_patterns/` (12ファイル) |
| KB3 few-shot集 | `analyst/dify/kb3_fewshot/` (5ファイル) |
| Phase 2検証データ | `analyst/phase2_KY/` (5銘柄) |
| SEC Filingsエージェント | `.claude/agents/finance-sec-filings.md` |
| Industry Researcherエージェント | `.claude/agents/deep-research/industry-researcher.md` |
