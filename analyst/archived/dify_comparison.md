# Dify vs Claude Code 比較表・移行ガイド

> 作成日: 2026-02-17
> 関連: [Dify詳細設計書](../memo/dify_workflow_design.md) | [Claude Code ワークフロー設計書](workflow_design.md)

---

## 1. アーキテクチャ比較

| 項目 | Dify | Claude Code |
|------|------|-------------|
| 実行基盤 | Dify Cloud / Self-hosted | Claude Code CLI + Agent Teams |
| ワークフロー構造 | 直列10ノード（LLM×6 + 知識検索×4） | 10タスク・5フェーズ（3並列 + 2並列 + 直列） |
| ナレッジベース | RAG（チャンク分割 + ベクトル検索） | **全ファイル直接読み込み（~62KB、25ファイル）** |
| 10-K/10-Qデータ | KB4（手動アップロード、セクション単位チャンク） | **SEC EDGAR MCPツールでライブ取得** |
| 市場データ | なし | yfinance / FRED 連携 |
| 精度検証 | 手動（Phase 2データと目視比較） | **自動精度検証（phase2_KYデータとの数値比較）** |

## 2. ナレッジベース対応表

### 2.1 KB1: ルール集（8チャンク → 8ファイル直接読み込み）

| Dify | Claude Code |
|------|-------------|
| KB1 チャンク1: ルール1 | `analyst/dify/kb1_rules/rule01_capability_not_result.md` |
| KB1 チャンク2: ルール2 | `analyst/dify/kb1_rules/rule02_noun_attribute.md` |
| KB1 チャンク3: ルール6 | `analyst/dify/kb1_rules/rule06_structural_vs_complementary.md` |
| KB1 チャンク4: ルール8 | `analyst/dify/kb1_rules/rule08_strategy_not_advantage.md` |
| KB1 チャンク5: ルール4 | `analyst/dify/kb1_rules/rule04_quantitative_evidence.md` |
| KB1 チャンク6: ルール7 | `analyst/dify/kb1_rules/rule07_pure_competitor_differentiation.md` |
| KB1 チャンク7: ルール10 | `analyst/dify/kb1_rules/rule10_negative_case.md` |
| KB1 チャンク8: ルール11 | `analyst/dify/kb1_rules/rule11_industry_structure_fit.md` |

**改善点**: RAG検索による取りこぼしゼロ。全8ルールが常にコンテキストに含まれる。

### 2.2 KB2: パターン集（12チャンク → 12ファイル直接読み込み）

| Dify | Claude Code |
|------|-------------|
| KB2 チャンク1-7: 却下パターンA-G | `analyst/dify/kb2_patterns/pattern_A_*.md` 〜 `pattern_G_*.md` |
| KB2 チャンク8-12: 高評価パターンI-V | `analyst/dify/kb2_patterns/pattern_I_*.md` 〜 `pattern_V_*.md` |

**改善点**: 12パターン全てが同時に参照可能。Difyでは Top-K=4 のため最大4パターンしか検索できなかった。

### 2.3 KB3: few-shot集（5チャンク → 5ファイル直接読み込み）

| Dify | Claude Code |
|------|-------------|
| KB3 チャンク1-5: ORLY, COST, MNST, CHD, LLY | `analyst/dify/kb3_fewshot/fewshot_*.md` |

**改善点**: 5銘柄の全評価例が常に参照可能。KYのスコア分布傾向のキャリブレーションが正確に。

### 2.4 KB4: 10-K/10-Q（手動アップロード → SEC EDGAR MCP）

| Dify | Claude Code |
|------|-------------|
| 銘柄ごとにKB作成 | `mcp__sec-edgar-mcp__get_financials` |
| セクション単位でチャンク分割 | `mcp__sec-edgar-mcp__get_filing_sections` |
| 手動アップロード必要 | **ティッカー指定のみで自動取得** |
| 静的データ（更新に再アップロード必要） | **常に最新データ** |
| PoC対象銘柄のみ | **任意の米国上場企業に対応** |

## 3. ワークフローステップ対応表

| Dify ステップ | Claude Code タスク | 改善点 |
|-------------|-------------------|--------|
| 知識検索①(KB4) + LLM①(主張抽出) | **T4: ca-claim-extractor** | KB1+KB3も同時読み込み。RAG不要で全ルール適用 |
| 知識検索②(KB1+KB3) + LLM②(ルール適用) | **T4に統合** | ステップ分離の必要なし（全KB直接読み込み可能） |
| 知識検索③(KB4) + LLM③(ファクトチェック) | **T5: ca-fact-checker** | SEC EDGAR MCPで追加検証も可能 |
| 知識検索④(KB2) + LLM④(検証/JSON) | **T6: ca-pattern-verifier** | 12パターン全て同時参照（Difyは Top-K=4） |
| LLM⑤(レポート生成) | **T7: ca-report-generator** | 上流の全検証結果を統合 |
| 知識検索⑤(KB1+KB2) + LLM⑥(レポート検証) | **T8: Lead直接実行** | 3層検証（JSON整合/ルール準拠/パターン一貫性） |
| *(なし)* | **T1: SEC Filings取得** | **新機能**: KB4の完全置換 |
| *(なし)* | **T2: Report Parser** | アナリストレポートの構造化 |
| *(なし)* | **T3: Industry Research** | **新機能**: 業界・競争環境データ |
| *(なし)* | **T9: 精度検証** | **新機能**: phase2_KYとの自動精度比較 |

## 4. 実行時間比較（推定）

| フェーズ | Dify（直列） | Claude Code（並列） | 改善率 |
|---------|-------------|-------------------|--------|
| データ収集 | N/A（手動前処理） | ~3分（3並列） | - |
| 主張抽出 + ルール適用 | ~2分（2ステップ直列） | ~2分（統合1ステップ） | 同等 |
| ファクトチェック | ~1分 | ~1.5分（SEC MCP追加検証） | やや増加 |
| パターン検証 | ~1分 | 並列（ファクトチェックと同時） | -1分 |
| レポート生成 | ~1分 | ~1.5分（検証結果統合） | やや増加 |
| レポート検証 | ~1分 | ~1分（3層検証） | 同等 |
| 精度検証 | 手動 | ~30秒（自動） | 大幅改善 |
| **合計** | **~6分 + 手動前処理** | **~8分（全自動）** | 手動作業ゼロ |

## 5. 制約の比較

| 制約 | Dify | Claude Code |
|------|------|-------------|
| 対象銘柄 | KB4作成済みの銘柄のみ | **任意の米国上場企業** |
| 10-K更新 | 手動再アップロード | **自動（MCPツールで常に最新）** |
| RAG検索漏れ | Top-K設定に依存（漏れリスクあり） | **ゼロ（全ファイル直接読み込み）** |
| パターン参照数 | Top-K=4（最大4パターン） | **全12パターン同時参照** |
| 並列実行 | 不可（直列のみ） | **Phase 1: 3並列、Phase 3: 2並列** |
| 精度検証 | 手動 | **自動（5銘柄対応）** |
| コスト | Dify Cloud料金 | Claude API料金 |
| デプロイ | Dify Cloud or Self-hosted | ローカルCLI |

## 6. 移行チェックリスト

### 事前準備

- [x] KB1ルール集（8ファイル）が `analyst/dify/kb1_rules/` に存在
- [x] KB2パターン集（12ファイル）が `analyst/dify/kb2_patterns/` に存在
- [x] KB3 few-shot集（5ファイル）が `analyst/dify/kb3_fewshot/` に存在
- [x] dogma.md が `analyst/Competitive_Advantage/analyst_YK/dogma.md` に存在
- [x] Phase 2検証データが `analyst/phase2_KY/` に存在

### Claude Code セットアップ

- [ ] ca-eval-lead エージェント作成
- [ ] 5ワーカーエージェント作成
- [ ] ca-eval スキル作成
- [ ] ca-eval コマンド作成
- [ ] SEC EDGAR MCPサーバー接続確認

### 検証

- [ ] `/ca-eval ORLY` で最終出力まで到達
- [ ] structured.json のスキーマがDify設計書§6に準拠
- [ ] accuracy-report.json でORLYの平均乖離 ±10% 以内
- [ ] 5銘柄（CHD, COST, LLY, MNST, ORLY）での精度検証

## 7. JSON出力スキーマの対応

Dify設計書§6のスキーマをClaude Codeでも踏襲。主要な変更点:

| フィールド | Dify | Claude Code |
|-----------|------|-------------|
| `verification_attempted` | KB4検索結果のみ | **SEC EDGAR MCP取得結果 + KB4** |
| `industry_context` | なし | **industry-researcher出力を追加** |
| `sec_live_data` | なし | **SEC MCPツールで取得した最新データを追加** |
| `accuracy_comparison` | なし | **phase2_KYデータとの乖離分析を追加** |
