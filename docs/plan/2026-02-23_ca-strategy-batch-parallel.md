# ca-strategy-lead: 395銘柄対応の並列処理+バッチ処理設計

## Context

`ca-strategy-lead`（Agent Teams リーダー）は395銘柄に対して競争優位性評価パイプラインを実行するが、現行設計には以下の問題がある:

1. **T2（transcript-claim-extractor）が全銘柄を1エージェントに割り当て** — コンテキストウィンドウ制限で非現実的
2. **agent_io.py が単一銘柄のみ対応** — `_validate_ticker()` は `^[A-Z]{1,10}$` のみ受付
3. **アーキテクチャ図の矛盾** — 「銘柄並列」と記載するが、タスク設計は1エージェント=全銘柄

一方、**Python レイヤーには既にバッチ処理+並列処理が完成している**:
- `extractor.py`: `BatchProcessor(max_workers=5)` で銘柄並列 LLM API 呼び出し
- `scorer.py`: 同じく `BatchProcessor(max_workers=5)` で並列スコアリング
- `orchestrator.py`: Phase 1→5 の全パイプライン統括、チェックポイント復帰対応
- `batch.py`: `CheckpointManager`（クラッシュリカバリ）、指数バックオフリトライ、部分失敗耐性
- `cost.py`: フェーズ別コスト追跡（推定 ~$40 / 395銘柄）

## 方針: ハイブリッドアーキテクチャ

**Agent Teams を「薄いオーケストレーション層」として維持しつつ、LLM 集約フェーズ（Phase 1-2）の実行は Python `Orchestrator` に完全委譲する。**

```
ca-strategy-lead (Agent Teams リーダー)
│
├─ Phase 0: Setup + HF0（Lead 自身）
│   パラメータ検証、ディレクトリ作成、コスト見積もり → ユーザー確認
│
├─ T1: Python Phase 1-2 実行（Bash）
│   uv run python -c "Orchestrator(...).run_from_checkpoint(1)"
│   → ClaimExtractor.extract_batch() → BatchProcessor(max_workers=5) → 395銘柄 5並列
│   → ClaimScorer.score_batch() → BatchProcessor(max_workers=5) → 同上
│   → checkpoint 自動保存（10銘柄ごと）
│
├─ HF1: 中間品質レポート（Lead がチェックポイントを Read して生成）
│
├─ T2: Python Phase 3-5 実行（Bash）
│   uv run python -c "Orchestrator(...).run_from_checkpoint(3)"
│   → ScoreAggregator + SectorNeutralizer + PortfolioBuilder + OutputGenerator
│
├─ HF2: 最終出力提示
└─ シャットダウン
```

## 変更ファイル

### Wave 1 (P1): 中核変更

#### 1. `src/dev/ca_strategy/extractor.py`
- `extract_batch()` に `checkpoint_dir: Path | None = None` パラメータ追加
- `checkpoint_dir` 指定時は `process_with_checkpoint()` を使用（10銘柄ごとに保存）
- `max_retries` を 1→3 に変更
- 既存の `process()` パスは互換性維持のため残す

#### 2. `src/dev/ca_strategy/scorer.py`
- `score_batch()` に同じ `checkpoint_dir` パラメータ追加
- 同様に `process_with_checkpoint()` 対応

#### 3. `src/dev/ca_strategy/orchestrator.py`
- `_run_phase1_extraction()` と `_run_phase2_scoring()` に `checkpoint_dir` を渡す
- Phase 完了後に失敗率チェック追加（10%超で `RuntimeError`）

#### 4. テスト更新
- `tests/ca_strategy/unit/test_extractor.py` — checkpoint パラメータのテスト追加
- `tests/ca_strategy/unit/test_scorer.py` — 同上
- `tests/ca_strategy/unit/test_orchestrator.py` — 失敗率チェックのテスト追加

### Wave 2 (P1): Agent Teams リーダー変更

#### 5. `.claude/agents/ca-strategy/ca-strategy-lead.md`
- 7チームメイト → 0（Lead 自身が Bash で Python Orchestrator を呼び出す）
- T1-T7 の7タスク → T1-T2 の2タスク
- HF0/HF1/HF2 のヒューマンフィードバックポイントは維持
- 不要になるチームメイトエージェント（transcript-loader, score-aggregator, sector-neutralizer, portfolio-constructor, output-generator）の参照を整理

### Wave 3 (P2): 安全性強化

#### 6. `src/dev/ca_strategy/batch.py`
- `BatchProcessor` に `failure_threshold: float = 0.1` パラメータ追加
- 閾値超過時に `BatchFailureThresholdError` を送出

#### 7. `src/dev/ca_strategy/orchestrator.py`
- コストハードリミット追加（`CostTracker` の total が閾値を超えたら停止+チェックポイント保存）

### Wave 4 (P3): コマンド整備

#### 8. `/run-ca-strategy-full` コマンド作成
- 395銘柄対応の全パイプライン実行コマンド
- 既存の `/run-ca-strategy-sample`（単一銘柄）は維持

## 既存の再利用可能コンポーネント

| コンポーネント | ファイル | 再利用方法 |
|------|------|------|
| `BatchProcessor` | `src/dev/ca_strategy/batch.py:155` | 銘柄並列処理 — 変更不要 |
| `CheckpointManager` | `src/dev/ca_strategy/batch.py:50` | クラッシュリカバリ — 変更不要 |
| `CostTracker` | `src/dev/ca_strategy/cost.py:47` | コスト追跡 — 変更不要 |
| `Orchestrator.run_from_checkpoint()` | `src/dev/ca_strategy/orchestrator.py:183` | Phase 単位再開 — 小修正のみ |
| `ClaimExtractor.extract_batch()` | `src/dev/ca_strategy/extractor.py:176` | 銘柄バッチ抽出 — checkpoint 対応追加 |
| `ClaimScorer.score_batch()` | `src/dev/ca_strategy/scorer.py:162` | 銘柄バッチスコアリング — checkpoint 対応追加 |

## 検証方法

1. **Wave 1 テスト**: `uv run pytest tests/ca_strategy/ -v` — checkpoint 対応のユニットテスト
2. **Wave 2 テスト**: `/run-ca-strategy-sample DIS` で単一銘柄の動作確認（既存フロー維持）
3. **統合テスト**: `Orchestrator.run_full_pipeline()` を小さな universe（5銘柄）で実行し、チェックポイント保存・復帰・コスト追跡を検証
4. **本番テスト**: 395銘柄の全パイプライン実行（推定 2-4時間、$40）

## リスクと緩和策

| リスク | 緩和策 |
|------|------|
| API レートリミット | `max_retries=3` + 指数バックオフ + `process_with_checkpoint()` |
| コスト超過 | `CostTracker.warning_threshold=$50` + ハードリミット追加 |
| 長時間実行（2-4h） | `process_with_checkpoint()` で中断再開可能 |
| 部分失敗 | 失敗率閾値（10%）+ 銘柄単位チェックポイント |
