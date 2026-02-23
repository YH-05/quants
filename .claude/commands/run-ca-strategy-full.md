---
description: 395銘柄（40チャンク）を3チャンク並列で処理するCA Strategy全体実行コマンド。ユニバース分割→HF0→3並列チャンク起動→完了待ち+リトライ→build_phase2_checkpoint→HF1→Phase3-5→HF2の8ステップパイプラインを実行します。
argument-hint: [--max-parallel N] [--universe-path PATH] [--workspace-dir DIR] [--resume-from-chunk N]
---

# /run-ca-strategy-full - CA Strategy 全体実行

395銘柄（40チャンク）を対象としたCA Strategy end-to-end パイプラインを実行するマスターオーケストレーターコマンドです。`ca-strategy-lead`（チャンク版）を複数並列起動し、指数バックオフリトライ付きのフォールトトレラント処理を提供します。

## ワークフローのロジック

本コマンドは2段階のフレームワークで構成される。

| フェーズ | フレームワーク | 役割 |
|---------|--------------|------|
| **Phase 1-2: 抽出・スコアリング** | **Hamilton Helmer の 7 Powers + KB1-T/KB2-T/KB3-T** | チャンク並列で `ca-strategy-lead` を起動し、トランスクリプトから競争優位性を抽出・スコアリングする。 |
| **Phase 3-5: 集約・構築・出力** | **ScoreAggregator + SectorNeutralizer + PortfolioBuilder** | `Orchestrator.run_from_checkpoint(phase=3)` でスコア集約→セクター中立化→ポートフォリオ構築→出力生成を実行する。 |

## 使用方法

```bash
# デフォルト設定で実行（3チャンク並列）
/run-ca-strategy-full

# 並列度を指定して実行
/run-ca-strategy-full --max-parallel 5

# 特定チャンクから再開
/run-ca-strategy-full --resume-from-chunk 10

# 全パラメータ指定
/run-ca-strategy-full --max-parallel 3 --universe-path research/ca_strategy_poc/config/universe.json --workspace-dir research/ca_strategy_poc/workspaces/full_run
```

## パラメータ

| パラメータ | 必須 | デフォルト | 説明 |
|-----------|------|-----------|------|
| `--max-parallel N` | No | 3 | 並列起動するチャンク数（レートリミット対策） |
| `--universe-path PATH` | No | `research/ca_strategy_poc/config/universe.json` | universe.json のパス |
| `--workspace-dir DIR` | No | `research/ca_strategy_poc/workspaces/full_run` | ワークスペースディレクトリ |
| `--resume-from-chunk N` | No | 0 | チャンク番号 N から再開（0始まり） |

## 変数定義

| 変数 | 値 |
|------|-----|
| MAX_PARALLEL | 3（引数で上書き可） |
| UNIVERSE_PATH | `research/ca_strategy_poc/config/universe.json`（引数で上書き可） |
| WORKSPACE_DIR | `research/ca_strategy_poc/workspaces/full_run`（引数で上書き可） |
| CONFIG_PATH | `research/ca_strategy_poc/config` |
| KB_BASE_DIR | `analyst/transcript_eval` |
| CHUNKS_DIR | `{UNIVERSE_PATH の親ディレクトリ}/chunks` |
| CHUNK_WORKSPACES_DIR | `{WORKSPACE_DIR}/chunk_workspaces` |
| CHECKPOINTS_DIR | `{WORKSPACE_DIR}/checkpoints` |
| RESUME_FROM_CHUNK | 0（引数で上書き可） |

## 処理フロー

```
Step 1: prepare_universe_chunks() でユニバース分割（chunk_00.json ～ chunk_39.json）
Step 2: [HF0] ユニバース分割確認・並列度設定
Step 3: 3チャンク並列 ca-strategy-lead 起動（Task ×3）
Step 4: 完了待ち + 指数バックオフリトライ（30→60→120 秒、最大 3 回）
Step 5: build_phase2_checkpoint(skip_missing=True) でチェックポイント生成
Step 6: [HF1] 失敗サマリー表示（failed_chunks / missing_tickers 確認）
Step 7: Orchestrator.run_from_checkpoint(phase=3) で Phase 3-5 実行
Step 8: [HF2] 完了レポート（portfolio_weights.json/csv）
```

## 実行手順

### Step 1: パラメータ解析とユニバース分割

#### 1.1 パラメータのパース

1. `--max-parallel N` が指定されていれば `MAX_PARALLEL=N` として使用する。なければ `MAX_PARALLEL=3` をデフォルト値として使用する。
2. `--universe-path PATH` が指定されていれば `UNIVERSE_PATH=PATH` として使用する。なければ `UNIVERSE_PATH=research/ca_strategy_poc/config/universe.json` をデフォルト値として使用する。
3. `--workspace-dir DIR` が指定されていれば `WORKSPACE_DIR=DIR` として使用する。なければ `WORKSPACE_DIR=research/ca_strategy_poc/workspaces/full_run` をデフォルト値として使用する。
4. `--resume-from-chunk N` が指定されていれば `RESUME_FROM_CHUNK=N` として使用する。なければ `RESUME_FROM_CHUNK=0` をデフォルト値として使用する。

#### 1.2 ワークスペースディレクトリ作成

以下の Bash コマンドを実行する:

```bash
mkdir -p {WORKSPACE_DIR}/chunk_workspaces
mkdir -p {WORKSPACE_DIR}/checkpoints
mkdir -p {WORKSPACE_DIR}/output
```

**成功判定**: コマンドが終了コード 0 で完了すること。

**失敗時**: エラーを出力して処理を中断する。

#### 1.3 ユニバース分割（RESUME_FROM_CHUNK=0 の場合のみ）

`RESUME_FROM_CHUNK=0` の場合、以下の Bash コマンドを実行する:

```bash
uv run python -c "
from pathlib import Path
from dev.ca_strategy.agent_io import prepare_universe_chunks

chunks_dir = Path('{UNIVERSE_PATH}').parent / 'chunks'
chunks_dir.mkdir(parents=True, exist_ok=True)

# universe.json の tickers を chunks_dir に chunk_{n:02d}.json として分割
import json
universe_data = json.loads(Path('{UNIVERSE_PATH}').read_text(encoding='utf-8'))
tickers = universe_data.get('tickers', [])
chunk_size = 10
chunks_dir_path = chunks_dir

# 既存の universe_path を chunks_dir/universe.json にコピーして prepare_universe_chunks に渡す
import shutil
universe_copy = chunks_dir / 'universe.json'
shutil.copy('{UNIVERSE_PATH}', universe_copy)

chunk_paths = prepare_universe_chunks(
    universe_path=universe_copy,
    chunk_size=chunk_size,
)
print(f'chunk_count={len(chunk_paths)}')
for p in chunk_paths:
    print(f'chunk_path={p}')
"
```

**成功判定**:
- コマンドが終了コード 0 で完了すること
- 標準出力に `chunk_count=N`（N >= 1）が含まれること
- `{UNIVERSE_PATH の親ディレクトリ}/chunks/chunk_*.json` が生成されること

**失敗時**: エラー詳細を出力して処理を中断する。`universe.json` の存在と `tickers` フィールドを確認するよう案内する。

`RESUME_FROM_CHUNK>0` の場合: チャンクファイルが既に存在することを確認して、分割ステップをスキップする。

### Step 2: [HF0] ユニバース分割確認・並列度設定

**Human-in-the-loop ゲート HF0**: 処理を開始する前にユーザーに確認を求める。

以下の情報を表示してユーザーの確認を待つ:

```
=== CA Strategy 全体実行 - HF0 確認 ===

実行パラメータ:
- ユニバース: {UNIVERSE_PATH}
- チャンク数: {chunk_count}（{chunk_count × 10} 銘柄）
- 並列度: MAX_PARALLEL={MAX_PARALLEL}
- ワークスペース: {WORKSPACE_DIR}
- 再開チャンク: chunk_{RESUME_FROM_CHUNK:02d} から（0=最初から）

処理スケジュール:
- バッチ数: {ceil(remaining_chunks / MAX_PARALLEL)} バッチ
- 1バッチあたり: {MAX_PARALLEL} チャンク並列
- 推定処理時間: {推定時間}

注意事項:
- Claude Code subscription のレートリミットに対して指数バックオフリトライを実施します
- 失敗チャンクは failed_chunks に記録され、処理継続します
- HF1 で失敗チャンクを確認し、再実行するかどうかを判断できます

続行しますか？ (yes/no)
```

**ユーザーが "yes" または "y" を入力した場合**: Step 3 に進む。
**ユーザーが "no" または "n" を入力した場合**: 処理を中断する。
**その他の入力**: 再確認を求める。

### Step 3: チャンク並列 ca-strategy-lead 起動

全チャンクを `MAX_PARALLEL` 個ずつのバッチに分割して順次処理する。

#### 3.1 バッチ処理ループ

`RESUME_FROM_CHUNK` 以降のチャンクを `MAX_PARALLEL` 個ずつのバッチにグループ化する。

チャンクファイルのリストを取得する:

```bash
uv run python -c "
from pathlib import Path
chunks_dir = Path('{UNIVERSE_PATH}').parent / 'chunks'
chunk_files = sorted(chunks_dir.glob('chunk_*.json'))
for f in chunk_files:
    print(f.name)
"
```

RESUME_FROM_CHUNK 以降のチャンクのみを処理対象とする。

#### 3.2 バッチ内チャンクの並列起動

各バッチで `MAX_PARALLEL` 個のチャンクを **Task ツールで並列起動**する:

```
Task: ca-strategy-lead（バッチ内の各チャンクに対して並列起動）
指示:
  以下のパラメータで {CHUNK_NAME} を処理してください。

  ## パラメータ
  - universe_path: {CHUNKS_DIR}/{CHUNK_NAME}
  - chunk_workspace_dir: {WORKSPACE_DIR}/chunk_workspaces/{CHUNK_NAME_WITHOUT_EXT}
  - config_path: {CONFIG_PATH}
  - kb_base_dir: {KB_BASE_DIR}
  - resume_from: 1

  ## MUST
  - universe_path のチャンクファイルを Read して銘柄リストを取得すること
  - 各銘柄に対して transcript-loader と transcript-claim-extractor を Task スポット呼び出しで実行すること
  - 個別銘柄の失敗を progress.json の failed リストに記録して他銘柄の処理を継続すること
  - 全銘柄の処理完了後に完了サマリーを出力すること
```

**重要**: 同じバッチ内の複数チャンクは**必ず並列に起動**すること（Task ツールを複数同時呼び出し）。

### Step 4: 完了待ち + 指数バックオフリトライ

#### 4.1 チャンク完了確認

各バッチの全 Task 完了後に、チャンクの処理結果を確認する:

- `{WORKSPACE_DIR}/chunk_workspaces/{chunk_name}/checkpoints/progress.json` が存在するか
- `progress.json` の `pending` リストが空か（全銘柄処理完了）
- `pending` が空でない場合は失敗チャンクとして記録する

#### 4.2 失敗チャンクのリトライ（指数バックオフ）

失敗チャンクが存在する場合、以下の手順でリトライを実施する:

| 試行回数 | 待機時間 | 対象 |
|---------|---------|------|
| 1回目 | 30秒待機 | 失敗チャンクのみ再起動 |
| 2回目 | 60秒待機 | 前回失敗チャンクのみ再起動 |
| 3回目 | 120秒待機 | 前回失敗チャンクのみ再起動 |

**待機の実装**:

```bash
# 30秒待機の例
uv run python -c "import time; time.sleep(30); print('waited 30s')"
```

**リトライ時の ca-strategy-lead 起動**:

失敗チャンクを再起動する際は `resume_from=2` を指定して Phase 2 から再開できる:

- Phase 1 出力ファイル（`extraction_output.json`）が存在する場合: `resume_from=2` で Phase 2 から再開
- Phase 1 出力ファイルが存在しない場合: `resume_from=1` で Phase 1 から再実行

**3回のリトライ後も失敗したチャンクは `failed_chunks` リストに記録**し、処理を継続する。

#### 4.3 全バッチ処理完了

全バッチの処理完了後（または最大リトライ数に達した後）、以下の集計を行う:

```python
failed_chunks = []  # 最終的に失敗したチャンクのリスト
all_failed_tickers = []  # 全チャンクの failed ティッカーリスト
all_completed_tickers = []  # 全チャンクの completed ティッカーリスト
```

各チャンクの `progress.json` を確認して集計する:

```bash
uv run python -c "
import json
from pathlib import Path

workspace_dir = Path('{WORKSPACE_DIR}')
chunk_workspaces = sorted(workspace_dir.glob('chunk_workspaces/chunk_*'))

failed_chunks = []
all_failed = []
all_completed = []

for cw in chunk_workspaces:
    progress_path = cw / 'checkpoints' / 'progress.json'
    if not progress_path.exists():
        failed_chunks.append(cw.name)
        continue

    progress = json.loads(progress_path.read_text(encoding='utf-8'))
    chunk_name = progress.get('chunk', cw.name)
    completed = progress.get('completed', [])
    failed = progress.get('failed', [])
    pending = progress.get('pending', [])

    all_completed.extend(completed)
    all_failed.extend(failed)

    if pending:
        failed_chunks.append(chunk_name)
        print(f'INCOMPLETE_CHUNK: {chunk_name}, pending={len(pending)}')

    print(f'CHUNK: {chunk_name}, completed={len(completed)}, failed={len(failed)}, pending={len(pending)}')

print(f'SUMMARY: total_completed={len(all_completed)}, total_failed={len(all_failed)}, failed_chunks={len(failed_chunks)}')
"
```

### Step 5: build_phase2_checkpoint（部分成功対応）

全バッチ処理完了後、以下の Bash コマンドを実行する:

```bash
uv run python -c "
from pathlib import Path
from dev.ca_strategy.agent_io import build_phase2_checkpoint

workspace_dir = Path('{WORKSPACE_DIR}')
checkpoint_path = workspace_dir / 'checkpoints' / 'phase2_scored.json'

# chunk_workspaces 内の全チャンクの phase2_output を統合する
# 各チャンクワークスペースから scoring_output.json を収集して統合

import json
import shutil

# 全チャンクから phase2_output を main workspace にコピー
phase2_merged_dir = workspace_dir / 'phase2_output'
phase2_merged_dir.mkdir(parents=True, exist_ok=True)

chunk_workspaces = sorted(workspace_dir.glob('chunk_workspaces/chunk_*'))
copied_count = 0
for cw in chunk_workspaces:
    cw_phase2 = cw / 'phase2_output'
    if not cw_phase2.exists():
        continue
    for ticker_dir in sorted(cw_phase2.iterdir()):
        if not ticker_dir.is_dir():
            continue
        scoring_output = ticker_dir / 'scoring_output.json'
        if scoring_output.exists():
            dest_dir = phase2_merged_dir / ticker_dir.name
            dest_dir.mkdir(parents=True, exist_ok=True)
            shutil.copy(scoring_output, dest_dir / 'scoring_output.json')
            copied_count += 1

print(f'Copied {copied_count} scoring_output.json files to {phase2_merged_dir}')

# build_phase2_checkpoint でチェックポイントを生成
checkpoint = build_phase2_checkpoint(
    workspace_dir=workspace_dir,
    output_path=checkpoint_path,
    skip_missing=True,
)
print(f'Phase 2 checkpoint built: {len(checkpoint)} tickers')
print(f'Checkpoint path: {checkpoint_path}')
"
```

**成功判定**:
- コマンドが終了コード 0 で完了すること
- `{WORKSPACE_DIR}/checkpoints/phase2_scored.json` が生成されること
- 標準出力に `Phase 2 checkpoint built: N tickers`（N >= 1）が含まれること

**失敗時**: エラー詳細を出力して処理を中断する。`phase2_output` ディレクトリの存在と `scoring_output.json` ファイルの存在を確認するよう案内する。

### Step 6: [HF1] 失敗サマリー表示

**Human-in-the-loop ゲート HF1**: 失敗チャンクと欠損ティッカーの確認。

以下の情報を表示してユーザーの確認を待つ:

```bash
uv run python -c "
import json
from pathlib import Path

workspace_dir = Path('{WORKSPACE_DIR}')
checkpoint_path = workspace_dir / 'checkpoints' / 'phase2_scored.json'

# チェックポイントの統計
checkpoint = json.loads(checkpoint_path.read_text(encoding='utf-8'))
checkpoint_tickers = list(checkpoint.keys())

# 各チャンクの progress.json を集計
chunk_workspaces = sorted(workspace_dir.glob('chunk_workspaces/chunk_*'))
all_failed = []
all_completed = []
failed_chunks = []

for cw in chunk_workspaces:
    progress_path = cw / 'checkpoints' / 'progress.json'
    if not progress_path.exists():
        failed_chunks.append(cw.name)
        continue

    progress = json.loads(progress_path.read_text(encoding='utf-8'))
    all_completed.extend(progress.get('completed', []))
    all_failed.extend(progress.get('failed', []))
    if progress.get('pending', []):
        failed_chunks.append(progress.get('chunk', cw.name))

print(f'=== HF1 失敗サマリー ===')
print(f'処理完了ティッカー数: {len(all_completed)}')
print(f'処理失敗ティッカー数: {len(all_failed)}')
print(f'チェックポイント登録ティッカー数: {len(checkpoint_tickers)}')
print(f'失敗チャンク数: {len(failed_chunks)}')

if all_failed:
    print(f'失敗ティッカー: {all_failed[:10]}...' if len(all_failed) > 10 else f'失敗ティッカー: {all_failed}')

if failed_chunks:
    print(f'失敗チャンク: {failed_chunks}')
"
```

以下を表示してユーザーの確認を待つ:

```
=== CA Strategy 全体実行 - HF1 確認 ===

Phase 1-2 処理結果:
- 処理完了ティッカー数: {completed_count}
- 処理失敗ティッカー数: {failed_count}
- チェックポイント登録: {checkpoint_ticker_count} ティッカー
- 失敗チャンク: {failed_chunks_list}

欠損ティッカー（skip_missing=True で除外）:
{missing_tickers_list}

Phase 3-5（スコア集約→セクター中立化→ポートフォリオ構築）に進みますか？
失敗チャンクを再実行したい場合は "retry" を入力してください。

続行しますか？ (yes/no/retry)
```

**ユーザーが "yes" または "y" を入力した場合**: Step 7 に進む。
**ユーザーが "no" または "n" を入力した場合**: 処理を中断する。
**ユーザーが "retry" を入力した場合**: 失敗チャンクのみを Step 3 のバッチ処理で再実行する。再実行後、Step 5 から再開する。

### Step 7: Orchestrator.run_from_checkpoint(phase=3)

以下の Bash コマンドを実行する:

```bash
uv run python -c "
from pathlib import Path
from dev.ca_strategy.agent_io import run_phase3_to_5

workspace_dir = Path('{WORKSPACE_DIR}')
config_path = Path('{CONFIG_PATH}')

print('Phase 3-5 開始: スコア集約→セクター中立化→ポートフォリオ構築→出力生成')
run_phase3_to_5(
    workspace_dir=workspace_dir,
    config_path=config_path,
)
print('Phase 3-5 完了')
"
```

**成功判定**:
- コマンドが終了コード 0 で完了すること
- `{WORKSPACE_DIR}/output/portfolio_weights.json` が生成されること
- `{WORKSPACE_DIR}/output/portfolio_weights.csv` が生成されること

**失敗時**: エラー詳細を出力して処理を中断する。`phase2_scored.json` の存在と形式（`{ticker: [ScoredClaim]}`）を確認するよう案内する。

### Step 8: [HF2] 完了レポート

**Human-in-the-loop ゲート HF2**: 最終ポートフォリオの確認。

以下の情報を表示してユーザーへ報告する:

```bash
uv run python -c "
import json
from pathlib import Path

workspace_dir = Path('{WORKSPACE_DIR}')
output_dir = workspace_dir / 'output'

# portfolio_weights.json を読み込み
portfolio_path = output_dir / 'portfolio_weights.json'
if portfolio_path.exists():
    portfolio = json.loads(portfolio_path.read_text(encoding='utf-8'))
    holdings = portfolio.get('holdings', [])
    print(f'ポートフォリオ保有銘柄数: {len(holdings)}')
    if holdings:
        print('トップ10銘柄:')
        for h in holdings[:10]:
            ticker = h.get('ticker', 'N/A')
            weight = h.get('weight', 0)
            sector = h.get('sector', 'N/A')
            print(f'  {ticker}: {weight:.2%} ({sector})')
    print(f'出力ファイル:')
    print(f'  JSON: {portfolio_path}')
    csv_path = output_dir / 'portfolio_weights.csv'
    if csv_path.exists():
        print(f'  CSV: {csv_path}')
else:
    print('ERROR: portfolio_weights.json が見つかりません')
"
```

完了報告を以下の形式で表示する:

```markdown
## CA Strategy 全体実行 完了

### 実行パラメータ
- ユニバース: {UNIVERSE_PATH}
- チャンク数: {chunk_count}
- 並列度: {MAX_PARALLEL}
- ワークスペース: {WORKSPACE_DIR}

### Phase 1-2 結果（主張抽出・スコアリング）
- 処理完了ティッカー数: {completed_count}
- 処理失敗ティッカー数: {failed_count}
- チェックポイント登録: {checkpoint_ticker_count} ティッカー

### Phase 3-5 結果（ポートフォリオ構築）
- ポートフォリオ保有銘柄数: {holdings_count}
- トップ銘柄:
  1. {TICKER_1}: {weight_1:.2%} ({sector_1})
  2. {TICKER_2}: {weight_2:.2%} ({sector_2})
  3. {TICKER_3}: {weight_3:.2%} ({sector_3})
  ...

### 生成ファイル
- Phase 2 チェックポイント: {WORKSPACE_DIR}/checkpoints/phase2_scored.json
- ポートフォリオ JSON: {WORKSPACE_DIR}/output/portfolio_weights.json
- ポートフォリオ CSV: {WORKSPACE_DIR}/output/portfolio_weights.csv
- 実行ログ: {WORKSPACE_DIR}/execution_log.json
```

## エラーハンドリング

### Step 1: ユニバース分割失敗

```
エラー: universe.json の分割に失敗しました

確認事項:
- universe.json が存在するか: {UNIVERSE_PATH}
- universe.json に tickers フィールドが存在するか
- chunks ディレクトリへの書き込み権限があるか
```

### Step 3/4: チャンク起動・完了待ちでの失敗

```
警告: チャンク {CHUNK_NAME} の処理が失敗しました

対処:
- 指数バックオフリトライ（30→60→120 秒）を実施
- 3回のリトライ後も失敗した場合は failed_chunks に記録して継続
- HF1 で再実行するかどうかを確認
```

### Step 5: build_phase2_checkpoint 失敗

```
エラー: Phase 2 チェックポイントの生成に失敗しました

確認事項:
- {WORKSPACE_DIR}/phase2_output/ に scoring_output.json ファイルが存在するか
- skip_missing=True を使用しているか（欠損銘柄をスキップ）
- チェックポイントを保存するディスク容量が十分か
```

### Step 7: Phase 3-5 実行失敗

```
エラー: Orchestrator.run_from_checkpoint(phase=3) が失敗しました

確認事項:
- {WORKSPACE_DIR}/checkpoints/phase2_scored.json が存在するか
- phase2_scored.json の形式が {ticker: [ScoredClaim.model_dump()]} であるか
- config_path にuniverse.json と benchmark_weights.json が存在するか
- Orchestrator が要求する最低限のティッカー数（2以上）が含まれているか
```

## 完了条件

- [ ] Step 1: `prepare_universe_chunks()` でチャンクファイルが生成されている
- [ ] Step 2: HF0 でユーザーが確認済み
- [ ] Step 3: 全チャンクに対して `ca-strategy-lead` を起動済み（`MAX_PARALLEL` 個並列）
- [ ] Step 4: 失敗チャンクへの指数バックオフリトライが完了（最大 3 回）
- [ ] Step 5: `build_phase2_checkpoint(skip_missing=True)` で `phase2_scored.json` が生成されている
- [ ] Step 6: HF1 でユーザーが失敗サマリーを確認済み
- [ ] Step 7: `Orchestrator.run_from_checkpoint(phase=3)` が正常完了
- [ ] Step 8: HF2 で最終ポートフォリオが表示されている
- [ ] `{WORKSPACE_DIR}/output/portfolio_weights.json` が生成されている
- [ ] `{WORKSPACE_DIR}/output/portfolio_weights.csv` が生成されている

## HF ゲート一覧

| ゲート | Step | タイミング | 確認内容 |
|--------|------|-----------|---------|
| HF0 | Step 2 | Phase 1-2 開始前 | チャンク数・並列度・処理スケジュールの確認 |
| HF1 | Step 6 | Phase 3-5 開始前 | 失敗チャンク・欠損銘柄サマリー・再実行判断 |
| HF2 | Step 8 | 処理完了後 | 最終ポートフォリオ内容の確認 |

## 使用エージェント

| エージェント | Step | 説明 |
|-------------|------|------|
| `ca-strategy-lead` | Step 3/4 | チャンク版ワークフローリーダー（10銘柄チャンクを処理） |

## 使用 Python 関数（agent_io.py / orchestrator.py）

| 関数 | Step | 説明 |
|------|------|------|
| `prepare_universe_chunks` | Step 1.3 | universe.json を chunk_{n:02d}.json に分割 |
| `build_phase2_checkpoint` | Step 5 | 全チャンクの phase2 出力を統合して phase2_scored.json を生成 |
| `run_phase3_to_5` | Step 7 | Orchestrator.run_from_checkpoint(phase=3) を呼び出して Phase 3-5 を実行 |

## 関連ファイル

- **ca-strategy-lead**: `.claude/agents/ca-strategy/ca-strategy-lead.md`
- **agent_io.py**: `src/dev/ca_strategy/agent_io.py`
- **orchestrator.py**: `src/dev/ca_strategy/orchestrator.py`
- **universe.json**: `research/ca_strategy_poc/config/universe.json`
- **KB ベースディレクトリ**: `analyst/transcript_eval/`
- **設定ディレクトリ**: `research/ca_strategy_poc/config/`
- **サンプル実装**: `.claude/commands/run-ca-strategy-sample.md`
- **PoC 計画書**: `docs/project/project-59/project.md`

## 注意事項

- 本コマンドは情報提供を目的としており、投資助言ではありません
- PoiT 制約（cutoff_date=2015-09-30）により、カットオフ日以降の情報は使用されません
- デフォルト並列度 3 は Claude Code subscription のレートリミットを考慮した推奨値です
- 失敗チャンクは HF1 ゲートで確認後、手動での再実行も可能です（`--resume-from-chunk N` を使用）
- `build_phase2_checkpoint(skip_missing=True)` により、一部銘柄の欠損があっても処理を継続できます
