# Simple AI Investment Strategy PoC — 現状レポート

**作成日**: 2026-02-23
**対象プロジェクト**: project-52（実装）/ project-54（エージェント化）

---

## 概要

S&P Capital IQ 決算トランスクリプト（2015年）から競争優位性の主張を抽出し、アナリスト Y の判断軸（KB1-T/KB2-T/KB3-T + dogma.md）でスコアリングして、セクター中立化された投資ポートフォリオを構築する AI 投資戦略 PoC。

- **PoiT カットオフ**: 2015-09-30（ルックアヘッドバイアス防止）
- **ユニバース**: `data/Transcript/list_portfolio_20151224.json` 準拠、**395銘柄**
- **セクター**: 10セクター（Consumer Discretionary 68, Financials 65, Health Care 49 …）
- **トランスクリプト対応**: 320/390銘柄（82.1%）
- **ワークスペース**: `research/ca_strategy_poc/`

---

## パイプライン全体像（5フェーズ）

```
トランスクリプト JSON
    │
    ▼ Phase 0（実装✅ / 実行✅）
  TranscriptParser → per-ticker JSON（TICKER/YYYYMM_earnings_call.json）
    │
    ▼ Phase 1（実装✅ / 実行❌）
  transcript-claim-extractor（Claude Code エージェント）
  → KB1-T（9件）+ KB3-T（5件）を Read → 主張を抽出 → Claim JSON
    │
    ▼ Phase 2（実装✅ / 実行❌）
  transcript-claim-scorer（Claude Code エージェント）
  → KB1-T + KB2-T（12件）+ KB3-T + dogma.md を Read → 確信度スコア → ScoredClaim JSON
    │
    ▼ Phase 3（実装✅ / 実行❌）
  ScoreAggregator + SectorNeutralizer（Python）
  → セクター内 Z-score → ランキング
    │
    ▼ Phase 4（実装✅ / 実行❌）
  PortfolioBuilder（Python）
  → 等ウェイトポートフォリオ（閾値ベース）
    │
    ▼ Phase 5（実装✅ / 実行❌）
  StrategyEvaluator + OutputGenerator（Python）
  → ACWI対比パフォーマンス（Sharpe, MaxDD, Beta, IR）
  → アナリスト Y/AK との Spearman 順位相関
```

---

## プロジェクト完了状況

### project-52: 残作業実装（✅ 完了 2026-02-20）

| コンポーネント | ファイル | 説明 |
|---|---|---|
| TickerConverter | `ticker_converter.py` | Bloomberg→yfinance 変換（395銘柄対応） |
| 評価モデル群 | `types.py`（追加） | PerformanceMetrics, AnalystCorrelation, EvaluationResult 等 |
| generate_config | `generate_config.py` | universe.json / benchmark_weights.json 生成 |
| StrategyEvaluator | `evaluator.py` | 3軸評価（パフォーマンス・アナリスト相関・透明性） |
| build_equal_weight | `portfolio_builder.py`（追加） | 閾値ベース等ウェイトポートフォリオ |
| OutputGenerator 評価 | `output.py`（追加） | evaluation_summary.md / evaluation_results.json |
| Orchestrator 統合 | `orchestrator.py`（追加） | `run_equal_weight_pipeline(thresholds)` |

### project-54: LLM 処理のエージェント化（✅ 完了 2026-02-23）

| コンポーネント | ファイル | 説明 |
|---|---|---|
| agent_io.py | `src/dev/ca_strategy/agent_io.py` | I/O ヘルパー（5関数） |
| extractor 改修 | `.claude/agents/ca-strategy/transcript-claim-extractor.md` | Anthropic SDK → エージェント自身が推論 |
| scorer 改修 | `.claude/agents/ca-strategy/transcript-claim-scorer.md` | 同上 |
| コマンド | `.claude/commands/run-ca-strategy-sample.md` | DIS 1 銘柄のサンプル実行オーケストレーター |

**移行理由**: Anthropic API キー不要。Claude Code Subscription の範囲内で LLM 推論を実行。

---

## 実行状況（DIS サンプル）

**ワークスペース**: `research/ca_strategy_poc/workspace_dis_sample/`

| フェーズ | 状態 | 詳細 |
|---|---|---|
| Phase 0 | ✅ 完了 | `phase1_output/DIS/` に Q1_2014〜Q3_2015 の 7 ファイル存在 |
| Phase 1 | ❌ **0 件** | 全 7 ファイルで Claim 数 = 0（抽出失敗） |
| Phase 2 | ❌ 未実行 | Phase 1 依存 |
| Phase 3〜5 | ❌ 未実行 | Phase 2 依存 |
| ポートフォリオ | ❌ 空 | Total Holdings: 0 |

**チェックポイント**: `checkpoints/phase1_claims.json` = `{"DIS": []}`

> project-54 の成功基準「Phase 1 で 5-15 件の Claim が抽出される」は**未達成**。
> `run-ca-strategy-sample` コマンドを再実行して Phase 1 を成功させることが次の必須ステップ。

---

## 次のアクション

| 優先度 | アクション | コマンド |
|---|---|---|
| 🔴 高 | DIS 1 銘柄で Phase 1 を成功させる（5-15 件の Claim 抽出） | `/run-ca-strategy-sample` |
| 🔴 高 | Phase 2 でScoredClaim に final_confidence（0.1-0.9）が付与されることを確認 | — |
| 🟡 中 | フル 395 銘柄パイプラインの実行（Phase 1〜5 end-to-end） | — |
| 🟡 中 | 等ウェイトポートフォリオ構築 + ACWI 対比評価 | — |
| 🟢 低 | MAS（Multi-Agent System）本格 PoC への拡張（plan/ 参照） | — |

---

## 関連ファイル

| カテゴリ | パス |
|---|---|
| パッケージ | `src/dev/ca_strategy/` |
| ナレッジベース | `analyst/transcript_eval/` （KB1-T×9, KB2-T×12, KB3-T×5） |
| エージェント定義 | `.claude/agents/ca-strategy/` |
| コマンド | `.claude/commands/run-ca-strategy-sample.md` |
| 設定ファイル | `research/ca_strategy_poc/config/` （universe.json, benchmark_weights.json） |
| ワークスペース | `research/ca_strategy_poc/workspace_dis_sample/` |
| プロジェクト計画 | `docs/project/project-52/project.md`, `docs/project/project-54/project.md` |
| MAS 本格 PoC 設計 | `MAS4InvestmentTeam/plan/2026-02-16_mas-investment-team-poc-design.md` |
