# Simple AI Investment Strategy PoC — 現状レポート

**作成日**: 2026-02-23
**最終更新**: 2026-02-26
**対象プロジェクト**: project-52（実装）/ project-54（エージェント化）

---

## 概要

S&P Capital IQ 決算トランスクリプト（2015年）から競争優位性の主張を抽出し、アナリスト Y の判断軸（KB1-T/KB2-T/KB3-T + dogma.md）でスコアリングして、セクター中立化された投資ポートフォリオを構築する AI 投資戦略 PoC。

- **PoiT カットオフ**: 2015-09-30（ルックアヘッドバイアス防止）
- **ユニバース**: `data/Transcript/list_portfolio_20151224.json` 準拠、**395銘柄**
- **セクター**: 10セクター（Consumer Discretionary 68, Financials 65, Health Care 49 …）
- **トランスクリプト対応**: 320/390銘柄（82.1%）
- **ワークスペース**: `research/ca_strategy_poc/workspaces/full_run/`

---

## パイプライン全体像（6フェーズ）

```
トランスクリプト JSON
    │
    ▼ Phase 0（実装✅ / 実行✅）
  TranscriptParser → per-ticker JSON（TICKER/YYYYMM_earnings_call.json）
    │
    ▼ Phase 1（実装✅ / 実行✅）  331/395銘柄成功、3,112件抽出
  transcript-claim-extractor（Claude Code エージェント）
  → KB1-T（9件）+ KB3-T（5件）を Read → 主張を抽出 → Claim JSON
    │
    ▼ Phase 2（実装✅ / 実行✅）  330銘柄処理、1,861件スコア済み（※後述の残課題あり）
  transcript-claim-scorer（Claude Code エージェント）
  → KB1-T + KB2-T（12件）+ KB3-T + dogma.md を Read → 確信度スコア → ScoredClaim JSON
    │
    ▼ Phase 3（実装✅ / 実行✅）  215銘柄集約
  ScoreAggregator + SectorNeutralizer（Python）
  → セクター内 Z-score → ランキング
    │
    ▼ Phase 4（実装✅ / 実行✅）  32銘柄選定
  PortfolioBuilder（Python）
  → MSCI Kokusai ベンチマーク加重ポートフォリオ
    │
    ▼ Phase 5（実装✅ / 実行✅）
  OutputGenerator（Python）
  → portfolio_weights.json/csv, portfolio_summary.md, 銘柄別 rationale
    │
    ▼ Phase 6（実装✅ / 実行❌）  PriceDataProvider が stub
  StrategyEvaluator（Python）
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
| コマンド（sample） | `.claude/commands/run-ca-strategy-sample.md` | 1 銘柄のサンプル実行オーケストレーター |
| コマンド（full） | `.claude/commands/run-ca-strategy-full.md` | 395銘柄フルパイプライン（40チャンク×3並列） |

**移行理由**: Anthropic API キー不要。Claude Code Subscription の範囲内で LLM 推論を実行。

---

## フルパイプライン実行結果（2026-02-25 完了）

**ワークスペース**: `research/ca_strategy_poc/workspaces/full_run/`

### 実行サマリー

| フェーズ | 状態 | 詳細 |
|---|---|---|
| Phase 0 | ✅ 完了 | 395銘柄の per-ticker JSON 変換済み |
| Phase 1 | ✅ 完了 | 331/395銘柄成功（64失敗）、3,112件の主張抽出 |
| Phase 2 | ✅ 完了 | 330銘柄処理。チェックポイントに統合された有効データは 215銘柄 1,861件（残り115銘柄 910件はスキーマ不整合で未統合、後述） |
| Phase 3 | ✅ 完了 | 215銘柄集約、セクター内 Z-score 正規化 |
| Phase 4 | ✅ 完了 | MSCI Kokusai ベンチマーク加重で32銘柄選定 |
| Phase 5 | ✅ 完了 | JSON/CSV/Markdown/銘柄別 rationale 生成 |
| Phase 6 | ❌ 未実行 | `PriceDataProvider` が stub（`NullPriceDataProvider`） |

**Phase 3-5 完了日時**: `execution_log.json` → `2026-02-25T12:55:29`

### ポートフォリオ結果（32銘柄）

| セクター | ウェイト | 銘柄 |
|---|---|---|
| Health Care | 18.9% | CSL, UTHR, ABBV, ROG, COLOB, ALXN |
| IT | 18.0% | AAPL, SWKS, PAYX, XLNX, FFIV |
| Consumer Staples | 16.3% | CVS, KR, CHD, CL, MO |
| Consumer Disc. | 13.0% | AMZN, CON, FL, LKQ |
| Financials | 13.0% | MHFI, CCI, HNR1, KBC |
| Industrials | 10.3% | CPI, FAST, DHL |
| Energy | 5.5% | ENB, EOG |
| Materials | 2.7% | DD |
| Utilities | 1.3% | PPL |
| Telecom | 0.9% | SCMN |

**Top 5 保有**: AAPL (3.76%, score 0.73), MHFI (3.68%, 0.75), CPI (3.60%, 0.67), SWKS (3.59%, 0.69), PAYX (3.57%, 0.69)

### 出力ファイル

| ファイル | パス |
|---|---|
| ポートフォリオ（JSON） | `output/portfolio_weights.json` |
| ポートフォリオ（CSV） | `output/portfolio_weights.csv` |
| サマリー | `output/portfolio_summary.md` |
| 銘柄別 rationale | `output/rationale/{TICKER}_rationale.md` × 32 |
| Phase 2 チェックポイント | `checkpoints/phase2_scored.json`（2.8MB） |
| 実行ログ | `checkpoints/execution_log.json` |

---

## 残課題 1: Phase 2 スキーマ不整合（115銘柄 910件の未統合データ）

### 何が起きているか

40チャンクの並列処理中に **scorer エージェントのプロンプトが改修され**、出力 JSON のフィールド名が途中で変わった。チェックポイント統合時（`build_phase2_checkpoint`）に新スキーマのフィールド名でバリデーションするため、旧スキーマの出力が弾かれている。

**データ自体は存在する**（各チャンクの `phase2_output/{TICKER}/scoring_output.json` にある）が、フィールド名の違いによりチェックポイントに取り込めていない。

### 具体的なスキーマ差異

| フィールド | 旧スキーマ（13チャンク） | 中間スキーマ（10銘柄） | 新スキーマ（215銘柄） |
|---|---|---|---|
| 確信度 | `confidence` | `final_confidence` ✅ | `final_confidence` ✅ |
| 主張テキスト | `claim_text` | `claim_summary` | `claim` ✅ |
| 主張ID | `claim_id`（`BA_001`） | `claim_id`（`APH-001`） | `id`（`BA-001`） ✅ |
| KB評価 | `kb_rules_applied` (list) | — | `kb1_t_evaluation` (dict) |
| KB2パターン | `kb2_patterns_matched` (list) | `kb2_patterns_applied` (list) | `kb2_t_pattern` (string) |
| **統合結果** | ❌ `final_confidence` なし→除外 | ❌ `claim` なし→除外 | ✅ 統合成功 |

### 影響

| 分類 | 銘柄数 | ドロップされた claim 数 | 原因 |
|---|---|---|---|
| 旧スキーマ | 102 | 854 | `final_confidence` フィールドなし |
| 中間スキーマ | 10 | 56 | `claim` / `claim_text` フィールドなし（`claim_summary` を使用） |
| エラー（非英語） | 3 | 0 | トランスクリプト不在 |
| **合計** | **115** | **910** | |

→ 全スコアリング結果 2,771件のうち **33% がスキーマ不整合で未反映**。

### 修正方針

`build_phase2_checkpoint` 内の `_parse_raw_scored_claim()` にスキーマ互換レイヤーを追加:

1. `confidence` → `final_confidence` へのフォールバック
2. `claim_text` / `claim_summary` → `claim` へのフォールバック
3. `claim_id` → `id` へのフォールバック

修正後に `build_phase2_checkpoint` を再実行すれば、215 → 最大 327 銘柄に拡大し、ポートフォリオの選定母集団が改善される。

---

## 残課題 2: Phase 1 失敗銘柄（64銘柄）

主に非英語圏ティッカー（アジア数値コード `1044`, `6`, `27`, `2328`, `3988` 等、`KBANK`, `SMGR`, `BBRI` 等）。英語トランスクリプトが存在しないため抽出不可。一部米国銘柄（`EXPD`, `JBHT`, `TROW`, `SCHW`, `HPQ` 等）も含まれるが、これらはトランスクリプト未対応。

---

## 残課題 3: Phase 6 未実行

`StrategyEvaluator` は実装済みだが、`PriceDataProvider` が `NullPriceDataProvider`（stub）のまま。`market` パッケージの yfinance 連携を接続すれば、以下が計算可能:

- Sharpe ratio / Max Drawdown / Beta / Information Ratio
- アナリスト Y/AK との Spearman 順位相関
- 2015-12-31 〜 2026-02-28 のバックテスト

---

## 次のアクション

| 優先度 | アクション | 詳細 |
|---|---|---|
| 🔴 高 | スキーマ互換レイヤーの実装 | `_parse_raw_scored_claim()` に旧/中間スキーマのフォールバックを追加。再統合で 215→327銘柄に拡大 |
| 🔴 高 | ポートフォリオ再構築 | 327銘柄ベースで Phase 3-5 を再実行 |
| 🟡 中 | Phase 6 の実行 | `PriceDataProvider` を `market` パッケージに接続し、バックテスト評価を実施 |
| 🟡 中 | 失敗銘柄の再試行 | 米国銘柄（`EXPD`, `JBHT` 等）のトランスクリプト有無を再確認 |
| 🟢 低 | MAS 本格 PoC への拡張 | `MAS4InvestmentTeam/plan/` 参照 |

---

## 関連ファイル

| カテゴリ | パス |
|---|---|
| パッケージ | `src/dev/ca_strategy/` |
| ナレッジベース | `analyst/transcript_eval/`（KB1-T×9, KB2-T×12, KB3-T×5） |
| エージェント定義 | `.claude/agents/ca-strategy/` |
| コマンド（sample） | `.claude/commands/run-ca-strategy-sample.md` |
| コマンド（full） | `.claude/commands/run-ca-strategy-full.md` |
| 設定ファイル | `research/ca_strategy_poc/config/`（universe.json, benchmark_weights.json, chunks/） |
| フル実行ワークスペース | `research/ca_strategy_poc/workspaces/full_run/` |
| DIS サンプル（旧） | `research/ca_strategy_poc/workspace_dis_sample/` |
| プロジェクト計画 | `docs/project/project-52/project.md`, `docs/project/project-54/project.md` |
| MAS 本格 PoC 設計 | `MAS4InvestmentTeam/plan/2026-02-16_mas-investment-team-poc-design.md` |
