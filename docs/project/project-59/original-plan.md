# ca-strategy: LLM呼び出しをエージェント方式に変更（チャンク並列設計）

## Context

`docs/plan/2026-02-23_ca-strategy-batch-parallel.md` では、Phase 1-2（主張抽出・スコアリング）を Python Orchestrator + Anthropic SDK（ClaimExtractor/ClaimScorer）に委譲する「ハイブリッドアーキテクチャ」を提案していた。

**変更理由**:
1. LLM呼び出しを Python SDK から `transcript-claim-extractor` / `transcript-claim-scorer` エージェント方式（`/run-ca-strategy-sample` と同じ）に変更する
2. チャンク制御は「10銘柄ずつの銘柄チャンクファイルを事前に用意し、各チャンクに独立した `ca-strategy-lead` を並列起動する」方式にする

## 変更後のアーキテクチャ

```
/run-ca-strategy-full コマンド（マスターオーケストレーター）
│
├─ Phase 0: ユニバース分割
│   - universe.json を10銘柄ずつに分割
│   - {workspace}/universe_chunks/chunk_00.json ~ chunk_39.json を生成（40チャンク）
│   - HF0: 銘柄数・チャンク数・コスト見積もり → ユーザー確認
│
├─ Phase 1-2: 並列抽出・スコアリング
│   - 各チャンクファイルに独立した ca-strategy-lead を Task で並列起動
│   - 各 ca-strategy-lead はチャンクの Phase 0-2 を独立実行:
│     ┌──────────────────────────────────────────────────────────┐
│     │  ca-strategy-lead (チャンク単位)                        │
│     │  - Setup: extraction_input.json × 10銘柄を生成          │
│     │  - 10 × Task(transcript-claim-extractor) 並列呼び出し  │
│     │  - validate_extraction_output() × 10                    │
│     │  - prepare_scoring_batches() + Task(scorer) × 10銘柄   │
│     │  - consolidate_scored_claims() × 10                     │
│     │  - チェックポイント保存                                  │
│     └──────────────────────────────────────────────────────────┘
│   - 全チャンク完了を待つ
│   - HF1: 抽出・スコアリング中間品質レポート
│
├─ Phase 3-5: 統合処理（Bash + Python）
│   - agent_io.build_phase2_checkpoint() で全チャンクを統合
│   - uv run python -c "Orchestrator(...).run_from_checkpoint(3)"
│     （集約 → セクター中立化 → ポートフォリオ構築 → 出力生成）
│
└─ HF2: 最終出力提示
```

## 変更ファイル

### Wave 1 (P1): agent_io.py 拡張

**ファイル**: `src/dev/ca_strategy/agent_io.py`

1. **`consolidate_scored_claims()` に `output_path: Path | None = None` パラメータ追加**（後方互換）
   - `None` → 従来どおり `workspace_dir/scoring_output.json`
   - 指定時 → そのパスに書き出し（多銘柄環境で銘柄別パスを指定可能）

2. **`build_phase2_checkpoint(workspace_dirs, tickers, output_path)` 新関数追加**（最重要）
   - 複数の `workspace_dir`（チャンク別）から全銘柄の `scoring_output.json` を読み込み
   - `Orchestrator._load_checkpoint()` が期待する形式（`{ticker: [ScoredClaim.model_dump()]}`）に変換
   - `checkpoints/phase2_scored.json` に書き出し
   - 0件の場合は `ValueError`

3. **`prepare_universe_chunks(universe_path, chunk_size, output_dir)` 新関数追加**
   - `universe.json` を読み込み、`chunk_size`（=10）銘柄ずつに分割
   - `{output_dir}/chunk_{n:02d}.json` ファイルとして書き出し
   - 戻り値: チャンクファイルパスのリスト

4. **`prepare_extraction_input()` に `output_dir: Path | None = None` パラメータ追加**（後方互換）
   - `None` → 従来どおり `workspace_dir/extraction_input.json`
   - 指定時 → `{output_dir}/{TICKER}_extraction_input.json`

**TDD 順序**:
- Red: `TestBuildPhase2Checkpoint`, `TestPrepareUniverseChunks`, `TestConsolidateScoredClaimsOutputPath` を追加
- Green: 各関数を実装
- Refactor: 後方互換確認（既存テストが全通過すること）

### Wave 2 (P1): ca-strategy-lead.md 変更（チャンク版）

**ファイル**: `.claude/agents/ca-strategy/ca-strategy-lead.md`

**変更の核心**: 1リードが全銘柄を処理 → **1リードが1チャンク（10銘柄）を処理**

- **入力パラメータ追加**: `universe_path` (チャンクファイルのパス、`chunk_00.json` など)、`chunk_workspace_dir`（チャンク別独立ワークスペース）
- **チームメイト構成**: 7チームメイト → **0チームメイト**（Lead 自身がすべて制御）
  - `transcript-claim-extractor` / `transcript-claim-scorer` はスポット Task として都度呼び出し
  - Phase 3-5 は Lead が Bash で実行しない（マスターオーケストレーター側で統合処理）
- **タスク構成**: T1-T7（7タスク） → Lead 自身が処理（Agent Teams 不使用）
- **Phase 1-2 の処理フロー**（`/run-ca-strategy-sample` を10銘柄に拡張）:
  1. `universe_path` からチャンク銘柄リスト（10銘柄）を読み込み
  2. Bash で全銘柄の `extraction_input.json` を生成
  3. 10 × `Task(transcript-claim-extractor)` を並列呼び出し
  4. Bash で `validate_extraction_output()` × 10
  5. Bash で `prepare_scoring_batches()` × 10
  6. 全バッチに `Task(transcript-claim-scorer)` を並列呼び出し
  7. Bash で `consolidate_scored_claims()` × 10
  8. Bash で `validate_scoring_output()` × 10
  9. チェックポイント保存: `{chunk_workspace_dir}/checkpoints/progress.json`
- **Phase 3-5 は実行しない**（マスターが全チャンク統合後に実行）
- `resume_from` パラメータ: 1=全実行, 2=抽出済みチャンクをスキップしてスコアリング再開

**チェックポイント構造**:
```json
// {chunk_workspace_dir}/checkpoints/progress.json
{
  "chunk_id": "chunk_00",
  "tickers": ["AAPL", "MSFT", "..."],
  "extraction_completed": ["AAPL", "MSFT"],
  "scoring_completed": ["AAPL"],
  "failed": []
}
```

### Wave 3 (P2): /run-ca-strategy-full コマンド作成（マスターオーケストレーター）

**新規ファイル**: `.claude/commands/run-ca-strategy-full.md`

**処理フロー**:
1. **ユニバース分割**: `agent_io.prepare_universe_chunks(universe_path, chunk_size=10)` で銘柄チャンクファイルを生成
2. **HF0**: チャンク数・銘柄数・コスト見積もりをユーザーに提示、確認後に実行
3. **並列起動**: 各チャンクファイルに対して `Task(ca-strategy-lead)` を並列呼び出し（同時並列数を管理）
4. **全チャンク完了待ち**
5. **HF1**: 中間品質レポート（抽出・スコアリング結果サマリー）
6. **Phase 3-5 統合**:
   - Bash で `agent_io.build_phase2_checkpoint(chunk_workspace_dirs, all_tickers)` を実行
   - `uv run python -c "Orchestrator(...).run_from_checkpoint(3)"`
7. **HF2**: 最終出力提示

**パラメータ**:
- `--config-path`: 設定ディレクトリ（デフォルト: `research/ca_strategy_poc/config`）
- `--kb-base-dir`: KB ディレクトリ（デフォルト: `analyst/transcript_eval`）
- `--workspace-dir`: 共有ワークスペース（デフォルト: `research/ca_strategy_poc/workspace`）
- `--chunk-size`: チャンクサイズ（デフォルト: 10）
- `--resume-from`: 再開フェーズ（1=全実行, 2=チャンク処理済みをスキップ, 3=Phase3-5のみ）

**ワークスペース構造**:
```
{workspace}/
├── universe_chunks/
│   ├── chunk_00.json     (10銘柄)
│   ├── chunk_01.json     (10銘柄)
│   └── ...               (40チャンク)
├── chunk_workspaces/
│   ├── chunk_00/         (ca-strategy-lead #1 の独立ワークスペース)
│   │   ├── extraction_inputs/
│   │   ├── phase1_output/
│   │   ├── phase2_output/
│   │   └── checkpoints/
│   ├── chunk_01/         (ca-strategy-lead #2 の独立ワークスペース)
│   └── ...
└── checkpoints/
    └── phase2_scored.json  (Phase 3-5 用統合チェックポイント)
```

### Wave 4 (P3): テスト追加

**変更ファイル**: `tests/dev/ca_strategy/unit/test_agent_io.py`

追加テストクラス:
- `TestBuildPhase2Checkpoint` (3ケース: 正常・一部欠損・全欠損)
- `TestPrepareUniverseChunks` (3ケース: 正常・端数銘柄・空)
- `TestConsolidateScoredClaimsOutputPath` (2ケース: 指定・未指定)

**新規ファイル**: `tests/dev/ca_strategy/integration/test_agent_io_batch.py`

- 3銘柄 × 2チャンクの小規模 universe で `build_phase2_checkpoint()` → `Orchestrator.run_from_checkpoint(3)` まで通る統合テスト

## 旧計画との差分

### 廃止する変更（旧計画 Wave 1, Wave 3 の Python 側変更）

| 旧計画の変更 | 廃止理由 |
|-------------|---------|
| `extractor.py`: `extract_batch()` に `checkpoint_dir` 追加 | エージェント方式では `ClaimExtractor` を直接呼ばない |
| `scorer.py`: `score_batch()` に `checkpoint_dir` 追加 | 同上 |
| `orchestrator.py`: Phase 1-2 への `checkpoint_dir` 渡し | Phase 1-2 は Orchestrator 経由でなくなる |
| `batch.py`: `failure_threshold` パラメータ追加 | BatchProcessor を Phase 1-2 で使わないため |

### 維持/変更する変更

| 旧計画の変更 | 対応方針 |
|-------------|---------|
| `ca-strategy-lead.md` の変更 | 旧計画の「7→0チームメイト化」を維持、ただし「全銘柄」→「10銘柄チャンク単位」に変更 |
| `/run-ca-strategy-full` コマンド作成 | 役割がマスターオーケストレーターに拡大 |

## 再利用する既存コンポーネント

| コンポーネント | ファイル | 再利用方法 |
|------|------|------|
| `prepare_extraction_input()` | `src/dev/ca_strategy/agent_io.py` | Lead が銘柄ごとに呼ぶ（`output_dir` パラメータ追加で再利用） |
| `validate_extraction_output()` | `src/dev/ca_strategy/agent_io.py` | 変更なし |
| `prepare_scoring_batches()` | `src/dev/ca_strategy/agent_io.py` | 変更なし |
| `consolidate_scored_claims()` | `src/dev/ca_strategy/agent_io.py` | `output_path` パラメータ追加で再利用 |
| `Orchestrator.run_from_checkpoint(3)` | `src/dev/ca_strategy/orchestrator.py` | Phase 3-5 を Bash で呼び出し（変更なし） |
| `transcript-claim-extractor` エージェント | `.claude/agents/ca-strategy/transcript-claim-extractor.md` | スポット Task として都度呼び出し（変更なし） |
| `transcript-claim-scorer` エージェント | `.claude/agents/ca-strategy/transcript-claim-scorer.md` | 同上 |

## 検証方法

1. **Wave 1 テスト**: `uv run pytest tests/dev/ca_strategy/ -v` — 新関数のユニットテスト（後方互換含む）
2. **Wave 2 テスト**: `/run-ca-strategy-sample DIS` で単一銘柄の動作確認（既存フロー維持）
3. **統合テスト**: `build_phase2_checkpoint()` → `Orchestrator.run_from_checkpoint(3)` を3銘柄 × 2チャンクで確認
4. **小規模 E2E テスト**: `/run-ca-strategy-full` を20銘柄（2チャンク）の小規模 universe で実行し、チャンク並列動作・Phase 3-5 統合・ポートフォリオ生成を確認
