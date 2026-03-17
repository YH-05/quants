# 議論メモ: プロジェクト実装状況と方向性の記録

**日付**: 2026-03-17
**議論ID**: disc-2026-03-17-project-status
**参加**: ユーザー + AI

## 背景・コンテキスト

quants プロジェクトの4つの主要プロジェクトについて、実装状況と方向性を Neo4j ナレッジグラフに初回記録する。Neo4j Memory グラフは空の状態からの初期投入。

---

## 1. アナリスト暗黙知形式化プロジェクト

### 概要

アナリスト Y の投資判断における暗黙知を形式知化し、AI で競争優位性を評価できるシステムを構築する。

### 進捗状況

| Stage | 状態 | 内容 |
|-------|------|------|
| Stage 1: 判断軸の抽出・文書化 | **完了** | judgment_patterns.md, dogma_v1.0（検証済み）, KB1/KB2/KB3 |
| Stage 2: Phase 2 評価エンジン | **部分完了** | ca-eval ワークフロー構築、v1.0 バッチ12銘柄実行済み |
| Stage 3: Phase 1 仮説生成改善 | 未着手 | template_ver2.md と Dogma の整合 |
| Stage 4: パイプライン統合 | 未着手 | Phase 1→Phase 2 一気通貫フロー |
| Stage 5: マルチエージェント化 | 未着手 | 弁証法的アーキテクチャ |

### 主要成果物

- **dogma_v1.0.md**: アナリスト検証済み運用版（v0.9 → v1.0、2026-02-26）
- **KB1**: 8 評価ルール（優位性の定義4件 + 裏付けの質4件）
- **KB2**: 12 パターン（却下 A-G + 高評価 I-V）
- **KB3**: 5 Few-shot（CHD, COST, LLY, MNST, ORLY）
- **ca-eval v1.0 バッチ**: AME, ATCOA, CPRT, LLY, LRCX, MCO, MNST, MSFT, NFLX, ORLY, POOL, VRSK

### ca_strategy パッケージ（src/dev/ca_strategy/）

24 Python ファイル実装済み。395銘柄対応のバッチ並列処理基盤:
- `Orchestrator`: Phase 1-5 統括、チェックポイント復帰対応
- `BatchProcessor(max_workers=5)`: 銘柄並列 LLM API 呼び出し
- `CheckpointManager`: クラッシュリカバリ（10銘柄ごと保存）
- `CostTracker`: フェーズ別コスト追跡（推定 ~$40/395銘柄）

### Y の投資哲学（形式知化済み）

- **5段階確信度スケール**: 90%（かなり納得）/ 70%（おおむね納得）/ 50%（まあ納得）/ 30%（あまり納得しない）/ 10%（却下）
- **6却下基準**: 結果の誤帰属、業界共通能力、戦略混同、説明力不足、因果関係混同、事実誤認
- **6上げ要因**: 定量的裏付け、特定競合比較、ネガティブケース、開示データ検証可能性、業界構造合致、能力の具体的説明
- **マルチアナリスト設計**: `analyst/Competitive_Advantage/analyst_{name}/dogma.md` で切替可能

---

## 2. MAS マルチエージェント投資チーム

### 概要

海外株式運用チームをマルチAIエージェントシステム（MAS）で再現。クオンタメンタル（定量+定性）判断の透明性確保。

### 設計決定

| 項目 | 決定 |
|------|------|
| ユニバース | S&P 500 |
| ポートフォリオ | 15-30銘柄、集中投資型（最大5%、セクター上限25%） |
| アーキテクチャ | ハイブリッド（Python バックテストエンジン + Claude Code Agent Teams） |
| 意思決定 | マネージャー決定型 + 構造化ディベート（2ラウンド） |
| バックテスト期間 | 2023-01〜現在、カットオフ前はティッカー匿名化 |

### 12エージェント × 5フェーズ

```
Phase 0: Postmortem Analyst（失敗パターン分析）
Phase 1: Universe Screener（500→50-80銘柄、Python実装）
Phase 2: 4アナリスト並列（Fundamental, Valuation, Sentiment, Macro/Regime）
Phase 3: Bull/Bear Advocate ディベート（2ラウンド）
Phase 4: Fund Manager 統合判断（確信度スコア0-100）
Phase 5: Risk Manager + Portfolio Constructor
```

### 先読みバイアス排除の3層防御

1. **構造的**: PitGuard（BacktestData アクセスの時刻制限）
2. **プロンプト注入**: 各エージェントに時間的制約を強制
3. **ティッカー匿名化**: カットオフ前期間でLLM学習データ汚染を防止

### 実装状況

- 詳細設計完了（`docs/plan/mas-multi-agent-investment-team-poc-plan.md`）
- `.claude/agents/mas-invest/` 未作成
- `src/strategy/backtest/` 未作成
- **前提条件**: 汎用バックテストエンジン（src/backtest/）が必要

### ロードマップ

| Phase | スコープ | コスト見積 |
|-------|---------|-----------|
| Phase 1 MVP | 4四半期（2024Q1-Q4）、基本エージェント、ディベートなし | ~$10-30/回 |
| Phase 2 フル | 12エージェント + ディベート + 3年バックテスト | ~$200-500/回 |
| Phase 3 拡張 | MSCI Kokusai、Black-Litterman、Walk-forward | TBD |

---

## 3. 汎用バックテストエンジン

### 概要

既存部品を最大限再利用した汎用バックテストエンジンを `src/backtest/` に新規作成。MAS の前提条件。

### 設計方針

- **Vectorized + Event-driven** 両モード同時実装
- **SOLID/DIP**: market パッケージに非依存。BacktestData 3層コンテナで呼び出し側がデータ注入
- **PitGuard**: PoiT（ルックアヘッドバイアス防止）をフレームワークレベルで構造的に強制
- 参考: vectorbt, bt, QuantConnect, zipline, QSTrader

### 6フェーズ実装計画

1. 基盤（BacktestData, PitGuard, SimulationClock, Protocols）
2. 実行レイヤー（Order/Fill, SimulatedBroker, PortfolioState）
3. シグナル & 戦略（Signal, FactorSignalAdapter, AlgoStack）
4. エンジン（VectorizedEngine, EventDrivenEngine, BacktestRunner）
5. 評価（Metrics, Report, WalkForward, Comparison）
6. 統合アダプター（CA Strategy, Factor Integration）

### 実装状況

- 詳細設計完了（`docs/plan/2026-02-25_backtest-engine-design.md`）
- 実装未着手（`src/backtest/` 未作成）

---

## 4. Neo4j ナレッジグラフ管理

### 概要

ワークフロー出力を構造化ナレッジグラフとして Neo4j に蓄積・活用。

### 実装状況

| Wave | 状態 | 内容 |
|------|------|------|
| Wave 1: 基盤構築 | **一部実装** | id_generator.py, schema.yaml, constraints.cypher, 名前空間規約 |
| Wave 2: 軽量 mapper | 未実装 | finance-news, ai-research, market-report |
| Wave 3: リッチ mapper | 未実装 | dr-stock, ca-eval, dr-industry, finance-research |
| Wave 4: save-to-graph | 未実装 | graph-queue JSON → Neo4j 投入パイプライン |
| Wave 5: 統合・ドキュメント | 未実装 | 既存ワークフローへのフック統合 |

---

## 決定事項

| ID | 内容 | コンテキスト |
|----|------|------------|
| dec-2026-03-17-001 | dogma v1.0 検証済み。KB1/KB2/KB3 構造化完了。ca-eval v1.0 バッチ12銘柄実行済み | アナリスト暗黙知形式化 Stage 2 |
| dec-2026-03-17-002 | MAS はハイブリッドアーキテクチャ + マネージャー決定型ディベート | 全会一致型は凡庸に収束するため |
| dec-2026-03-17-003 | MAS は汎用バックテストエンジンを前提。SOLID/DIP + PitGuard | zipline 方式の PoiT 強制 |
| dec-2026-03-17-004 | ca_strategy は Agent Teams を薄いオーケストレーション層に。Python Orchestrator に委譲 | BatchProcessor/CheckpointManager 完成済み |
| dec-2026-03-17-005 | ca-eval v1.0 結果を Y にレビュー依頼。In-sample 検証も並行実施 | 目標: 平均乖離 ±10% 以内 |

## アクションアイテム

| ID | 内容 | 優先度 | 状態 |
|----|------|--------|------|
| act-2026-03-17-001 | バックテストエンジン（src/backtest/）実装開始 | 高 | pending |
| act-2026-03-17-002 | MAS エージェント群作成 | 中 | pending |
| act-2026-03-17-003 | ca-eval In-sample 検証 | 高 | pending |
| act-2026-03-17-004 | ca-eval v1.0 結果を Y にレビュー依頼 | 高 | pending |
| act-2026-03-17-005 | Phase 1 仮説生成改善 | 中 | pending |
| act-2026-03-17-006 | Neo4j KG Wave 2-5 実装継続 | 低 | pending |

## プロジェクト間依存関係

```
analyst-tacit-knowledge ──FEEDS_INTO──→ mas-investment-team
backtest-engine ─────────ENABLES──────→ mas-investment-team
neo4j-kg（独立、全プロジェクトの出力を蓄積）
```

## 次回の議論トピック

- バックテストエンジン実装の優先順位（Phase 1 のどのコンポーネントから着手するか）
- ca-eval In-sample 検証結果に基づく Dogma 改善方針
- MAS Phase 1 MVP のスコープ最終確定
