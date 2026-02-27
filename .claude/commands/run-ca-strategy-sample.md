---
description: 任意銘柄のサンプル実行を行うオーケストレーターコマンド。agent_io.py の Python 関数と transcript-claim-extractor/transcript-claim-scorer エージェントを組み合わせた 6 ステップのパイプラインを実行します。
argument-hint: [TICKER]
---

# /run-ca-strategy-sample - CA Strategy サンプル実行

任意銘柄を対象とした CA Strategy end-to-end サンプルパイプラインを実行するコマンドです。`ca-strategy-lead`（Agent Teams 方式）は使わず、コマンドがオーケストレーターとして全体フローを制御します。銘柄ごとに独立した workspace（`workspaces/{TICKER}/`）が作成されるため、複数銘柄を並行して分析可能です。

## ワークフローのロジック

本 PoC は2段階のフレームワークで構成される。

| フェーズ | フレームワーク | 役割 |
|---------|--------------|------|
| **Phase 1: 抽出** | **Hamilton Helmer の 7 Powers** | トランスクリプトから競争優位性を識別・分類する基準。Scale Economies / Network Economies / Counter-Positioning / Switching Costs / Branding / Cornered Resource / Process Power の7類型に基づき主張を抽出する。 |
| **Phase 2: 批判・スコアリング** | **KB1-T / KB2-T / KB3-T + dogma.md** | Phase 1 で抽出された主張の妥当性を批判し、確信度（0.1-0.9）を付与する。ゲートキーパー判定 → KB1-T ルール適用 → KB2-T パターン照合 → KB3-T キャリブレーションの4段階で評価する。 |

7 Powers は「何を優位性とみなすか」の分類軸、KB1〜3 + dogma.md は「その主張はどれだけ信頼できるか」の評価軸として機能する。

## 使用方法

```bash
# DIS をデフォルト銘柄として実行（引数なし）
/run-ca-strategy-sample

# 銘柄を明示指定
/run-ca-strategy-sample DIS
/run-ca-strategy-sample AAPL
/run-ca-strategy-sample COST
```

## パラメータ

| パラメータ | 必須 | デフォルト | 説明 |
|-----------|------|-----------|------|
| `TICKER` | No | DIS | 実行対象のティッカーシンボル |

## 変数定義

| 変数 | 値 |
|------|-----|
| TICKER | DIS（引数で上書き可） |
| workspace | `research/ca_strategy_poc/workspaces/{TICKER}` |
| config_path | `research/ca_strategy_poc/config` |
| transcript_dir | `research/ca_strategy_poc/transcripts` |
| kb_base_dir | `analyst/transcript_eval` |
| dogma_path | `analyst/Competitive_Advantage/analyst_YK/dogma/dogma_v1.0.md` |
| phase1_output_dir | `{workspace}/phase1_output/{TICKER}` |
| phase2_output_dir | `{workspace}/phase2_output/{TICKER}` |
| extraction_input_json | `{workspace}/extraction_input.json` |
| extraction_output_json | `{workspace}/phase1_output/{TICKER}/extraction_output.json` |
| scoring_input_json | `{workspace}/scoring_input.json` |
| scoring_output_json | `{workspace}/scoring_output.json` |
| batch_inputs_dir | `{workspace}/batch_inputs` |

## 処理フロー

```
Step 0: workspace 作成
Step 1: Phase 1 入力準備（Python）
Step 2: Phase 1 エージェント呼び出し（transcript-claim-extractor）
Step 3: Phase 1 出力バリデーション（Python）
Step 4.1: Phase 2 入力準備（prepare_scoring_input）
Step 4.2: バッチ入力生成（prepare_scoring_batches）
Step 4.3: 各バッチに transcript-claim-scorer を並列呼び出し
Step 4.4: バッチ出力を統合（consolidate_scored_claims）
Step 5: Phase 2 出力バリデーション（Python）
```

## 実行手順

### Step 0: パラメータ解析と workspace 作成

1. **引数のパース**
   - 引数が指定されていれば `TICKER` として使用する
   - 引数がなければ `TICKER=DIS` をデフォルト値として使用する

2. **変数の設定**
   ```
   TICKER = <パース結果または DIS>
   workspace = research/ca_strategy_poc/workspaces/{TICKER}
   config_path = research/ca_strategy_poc/config
   transcript_dir = research/ca_strategy_poc/transcripts
   kb_base_dir = analyst/transcript_eval
   phase1_output_dir = {workspace}/phase1_output/{TICKER}
   ```

3. **workspace ディレクトリの作成**

   以下の Bash コマンドを実行する:
   ```bash
   mkdir -p research/ca_strategy_poc/workspaces/{TICKER}/phase1_output/{TICKER}
   mkdir -p research/ca_strategy_poc/workspaces/{TICKER}/phase2_output/{TICKER}
   mkdir -p research/ca_strategy_poc/workspaces/{TICKER}/output
   mkdir -p research/ca_strategy_poc/workspaces/{TICKER}/checkpoints
   ```

   **成功判定**: コマンドが終了コード 0 で完了すること。

   **失敗時**: エラーを出力して処理を中断する。

### Step 1: Phase 1 入力準備（Python）

以下の Bash コマンドを実行する:

```bash
uv run python -c "
from pathlib import Path
from dev.ca_strategy.agent_io import prepare_extraction_input

result = prepare_extraction_input(
    config_path=Path('research/ca_strategy_poc/config'),
    transcript_dir=Path('research/ca_strategy_poc/transcripts'),
    kb_base_dir=Path('analyst/transcript_eval'),
    ticker='{TICKER}',
    workspace_dir=Path('research/ca_strategy_poc/workspaces/{TICKER}'),
)
count = len(result['transcript_paths'])
print(f'extraction_input.json generated: {count} transcripts')
if count == 0:
    raise SystemExit('ERROR: No transcripts found for {TICKER}. Check transcript_dir and PoiT cutoff.')
"
```

**成功判定**:
- コマンドが終了コード 0 で完了すること
- 標準出力に `extraction_input.json generated: N transcripts`（N >= 1）が含まれること
- `research/ca_strategy_poc/workspaces/{TICKER}/extraction_input.json` が生成されること

**失敗時**: エラー詳細を出力して処理を中断する。transcript が 0 件の場合は `transcript_dir` と PoiT カットオフ日を確認するよう案内する。

### Step 2: Phase 1 エージェント呼び出し（transcript-claim-extractor）

`Task(transcript-claim-extractor)` を使用して主張抽出を実行する。

```
Task: transcript-claim-extractor
指示:
  以下のパスにある extraction_input.json を読み込み、{TICKER} の決算トランスクリプトから
  競争優位性の主張を抽出して extraction_output.json を書き出してください。

  extraction_input.json パス:
    research/ca_strategy_poc/workspaces/{TICKER}/extraction_input.json

  workspace_dir:
    research/ca_strategy_poc/workspaces/{TICKER}

  出力先:
    research/ca_strategy_poc/workspaces/{TICKER}/phase1_output/{TICKER}/extraction_output.json

  注意:
  - extraction_input.json を最初に Read して ticker・transcript_paths・kb1_dir・kb3_dir・workspace_dir・cutoff_date を取得すること
  - KB1-T・KB3-T・dogma.md・system_prompt・seven_powers_framework を全て Read してから抽出を開始すること
  - PoiT 制約（cutoff_date=2015-09-30）を厳守すること
  - 1銘柄あたり 5-15 件の主張を抽出すること
  - 出力先は {workspace_dir}/phase1_output/{TICKER}/extraction_output.json であること
```

**成功判定**:
- `research/ca_strategy_poc/workspaces/{TICKER}/phase1_output/{TICKER}/extraction_output.json` が生成されること

**失敗時**: エージェントのエラー出力を確認し、KB ファイルの Read 漏れや PoiT 制約違反がないか確認する。

### Step 3: Phase 1 出力バリデーション（Python）

以下の Bash コマンドを実行する:

```bash
uv run python -c "
from pathlib import Path
from dev.ca_strategy.agent_io import validate_extraction_output

output_path = Path('research/ca_strategy_poc/workspaces/{TICKER}/phase1_output/{TICKER}/extraction_output.json')
claims = validate_extraction_output(
    output_path=output_path,
    ticker='{TICKER}',
)
count = len(claims)
print(f'Validated {count} claims')
if count < 5:
    raise SystemExit(f'ERROR: Too few claims ({count}). Expected 5-15. Check extraction_output.json.')
if count > 15:
    print(f'WARNING: More than 15 claims ({count}). Verify extraction quality.')
print('Phase 1 validation: PASS')
"
```

**成功判定**:
- コマンドが終了コード 0 で完了すること
- 標準出力に `Validated N claims`（5 <= N <= 15）が含まれること
- Pydantic バリデーションが全 Claim に対してパスすること

**失敗時**: 抽出件数が 5 件未満の場合はエラーを出力して処理を中断する。`extraction_output.json` の内容を確認するよう案内する。

### Step 4: Phase 2 バッチスコアリング（transcript-claim-scorer）

#### Step 4.1: Phase 2 入力準備（Python）

以下の Bash コマンドを実行する:

```bash
uv run python -c "
from pathlib import Path
from dev.ca_strategy.agent_io import prepare_scoring_input

result = prepare_scoring_input(
    workspace_dir=Path('research/ca_strategy_poc/workspaces/{TICKER}'),
    kb_base_dir=Path('analyst/transcript_eval'),
    ticker='{TICKER}',
)
print(f'scoring_input.json generated')
print(f'  phase1_output_dir: {result[\"phase1_output_dir\"]}')
print(f'  kb1_dir: {result[\"kb1_dir\"]}')
print(f'  kb2_dir: {result[\"kb2_dir\"]}')
"
```

**成功判定**:
- コマンドが終了コード 0 で完了すること
- `research/ca_strategy_poc/workspaces/{TICKER}/scoring_input.json` が生成されること

#### Step 4.2: バッチ入力生成（Python）

以下の Bash コマンドを実行する:

```bash
uv run python -c "
from pathlib import Path
from dev.ca_strategy.agent_io import prepare_scoring_batches

batches = prepare_scoring_batches(
    workspace_dir=Path('research/ca_strategy_poc/workspaces/{TICKER}'),
    kb_base_dir=Path('analyst/transcript_eval'),
    ticker='{TICKER}',
    batch_size=5,
)
print(f'batch_count={len(batches)}')
for b in batches:
    print(f'batch_input={b[\"input_path\"]}')
"
```

**成功判定**:
- コマンドが終了コード 0 で完了すること
- 標準出力に `batch_count=N`（N >= 1）が含まれること
- `research/ca_strategy_poc/workspaces/{TICKER}/batch_inputs/scoring_input_batch_*.json` が生成されること

**失敗時**: エラー詳細を出力して処理を中断する。`phase1_output/{TICKER}/extraction_output.json` が存在するか確認する。

#### Step 4.3: 各バッチへの transcript-claim-scorer 並列呼び出し

Step 4.2 で生成したバッチ数分だけ `Task(transcript-claim-scorer)` を**並列**に呼び出す。

バッチ 0 を例として示す（バッチ数に応じて動的に繰り返す）:

```
Task: transcript-claim-scorer
指示:
  以下のパスにある scoring_input_batch_0.json を読み込み、
  対象の主張に確信度スコアを付与して scored_batch_0.json を書き出してください。

  scoring_input.json パス:
    research/ca_strategy_poc/workspaces/{TICKER}/batch_inputs/scoring_input_batch_0.json

  workspace_dir:
    research/ca_strategy_poc/workspaces/{TICKER}

  出力先:
    research/ca_strategy_poc/workspaces/{TICKER}/phase2_output/{TICKER}/scored_batch_0.json

  注意:
  - scoring_input_batch_0.json を最初に Read して ticker・phase1_output_dir・kb1_dir・kb2_dir・kb3_dir・workspace_dir・target_claim_ids・output_path・batch_index・batch_total を取得すること
  - KB1-T・KB2-T・KB3-T・dogma.md を全て Read してから評価を開始すること
  - Phase 1 出力ファイル（{phase1_output_dir}/extraction_output.json）を Read して主張一覧を取得すること
  - target_claim_ids に含まれる主張のみをスコアリング対象とすること
  - PoiT 制約（cutoff_date=2015-09-30）を厳守すること
  - 4段階評価（ゲートキーパー→KB1-T→KB2-T→KB3-T）を全対象主張に適用すること
  - 各主張に final_confidence（0.1-0.9 の範囲）を付与すること
  - 出力先は output_path フィールドに指定されたパスであること（scored_batch_0.json）
```

全バッチを並列実行し、各バッチが `phase2_output/{TICKER}/scored_batch_{n}.json` を生成するまで待機する。

**成功判定**:
- 全バッチに対応する `scored_batch_{n}.json` が `phase2_output/{TICKER}/` 配下に生成されること

**失敗時**: 失敗したバッチのエージェントエラーを確認し、対応する `scoring_input_batch_{n}.json` の内容と KB ファイルへのパスを確認する。

#### Step 4.4: バッチ出力の統合（Python）

以下の Bash コマンドを実行する:

```bash
uv run python -c "
from pathlib import Path
from dev.ca_strategy.agent_io import consolidate_scored_claims

output_path = consolidate_scored_claims(
    workspace_dir=Path('research/ca_strategy_poc/workspaces/{TICKER}'),
    ticker='{TICKER}',
)
print(f'Consolidated to: {output_path}')
"
```

**成功判定**:
- コマンドが終了コード 0 で完了すること
- `research/ca_strategy_poc/workspaces/{TICKER}/scoring_output.json` が生成されること

**失敗時**: エラー詳細を出力して処理を中断する。`phase2_output/{TICKER}/scored_batch_*.json` が全バッチ分存在するか確認する。

### Step 5: Phase 2 出力バリデーション（Python）

以下の Bash コマンドを実行する:

```bash
uv run python -c "
from pathlib import Path
from dev.ca_strategy.agent_io import validate_extraction_output, validate_scoring_output

# Phase 1 claims を再ロード（ID lookup に使用）
phase1_path = Path('research/ca_strategy_poc/workspaces/{TICKER}/phase1_output/{TICKER}/extraction_output.json')
claims = validate_extraction_output(
    output_path=phase1_path,
    ticker='{TICKER}',
)

# Phase 2 scored claims をバリデーション
scoring_path = Path('research/ca_strategy_poc/workspaces/{TICKER}/scoring_output.json')
scored = validate_scoring_output(
    output_path=scoring_path,
    ticker='{TICKER}',
    original_claims=claims,
)
count = len(scored)
print(f'Validated {count} scored claims')
if count == 0:
    raise SystemExit('ERROR: No valid scored claims. Check scoring_output.json.')

# final_confidence の範囲チェック
out_of_range = [s for s in scored if not (0.1 <= s.final_confidence <= 0.9)]
if out_of_range:
    print(f'WARNING: {len(out_of_range)} claims have final_confidence outside [0.1, 0.9]')
    for c in out_of_range:
        print(f'  id={c.id}, final_confidence={c.final_confidence}')

print('Phase 2 validation: PASS')
print(f'Summary: {count} scored claims, confidence range [{min(s.final_confidence for s in scored):.2f}, {max(s.final_confidence for s in scored):.2f}]')
"
```

**成功判定**:
- コマンドが終了コード 0 で完了すること
- 標準出力に `Validated N scored claims`（N >= 1）が含まれること
- 全 ScoredClaim に `final_confidence`（0.1-0.9 の範囲）が付与されていること
- Pydantic バリデーションが全 ScoredClaim に対してパスすること

**失敗時**: スコア件数が 0 件の場合はエラーを出力して処理を中断する。`scoring_output.json` の内容と Phase 1 の claims との ID 対応を確認するよう案内する。

## 検証基準

| フェーズ | 基準 |
|---------|------|
| Phase 1（主張抽出） | 5-15 件の Claim が抽出されること、Pydantic バリデーション通過 |
| Phase 2（確信度スコアリング） | 全 Claim に `final_confidence`（0.1-0.9）が付与されること、Pydantic バリデーション通過 |

## エラーハンドリング

### Step 0: workspace 作成失敗

```
エラー: workspace ディレクトリの作成に失敗しました

mkdir コマンドのエラー出力を確認し、ディレクトリのパーミッションを確認してください。
```

### Step 1: transcript が 0 件

```
エラー: {TICKER} のトランスクリプトが見つかりません

確認事項:
- transcript_dir が存在するか: research/ca_strategy_poc/transcripts/{TICKER}/
- PoiT カットオフ日（2015-09-30）以前のファイルが存在するか
- ファイル名が {YYYYMM}_earnings_call.json 形式か
```

### Step 2/4.3: エージェント呼び出し失敗

```
エラー: エージェント {エージェント名} が失敗しました

確認事項:
- extraction_input.json / scoring_input_batch_*.json が正しく生成されているか
- KB ファイルへのパスが正しいか（kb_base_dir: analyst/transcript_eval）
- dogma.md のパスが正しいか（analyst/Competitive_Advantage/analyst_YK/dogma/dogma_v1.0.md）
```

### Step 3: Phase 1 バリデーション失敗（件数不足）

```
エラー: 抽出された Claim が少なすぎます（N 件）

確認事項:
- extraction_output.json の内容を確認してください
- KB1-T ルールと KB3-T few-shot が正しく読み込まれているか
- トランスクリプトに競争優位性に関する発言が含まれているか
```

### Step 5: Phase 2 バリデーション失敗

```
エラー: スコアリングされた Claim が 0 件です

確認事項:
- scoring_output.json の内容を確認してください
- Phase 1 の extraction_output.json との claim ID 対応を確認してください
- final_confidence フィールドが正しく設定されているか
```

## 完了報告

全 Step が成功した場合、以下の形式で報告します:

```markdown
## CA Strategy サンプル実行 完了

### 実行パラメータ
- TICKER: {TICKER}
- workspace: research/ca_strategy_poc/workspaces/{TICKER}

### Phase 1 結果（主張抽出）
- 抽出 Claim 数: N 件
- バリデーション: PASS

### Phase 2 結果（確信度スコアリング）
- バッチ数: N バッチ（batch_size=5）
- スコアリング済み Claim 数: N 件
- final_confidence 範囲: [min, max]
- バリデーション: PASS

### 生成ファイル
- extraction_input.json: research/ca_strategy_poc/workspaces/{TICKER}/extraction_input.json
- extraction_output.json: research/ca_strategy_poc/workspaces/{TICKER}/phase1_output/{TICKER}/extraction_output.json
- scoring_input.json: research/ca_strategy_poc/workspaces/{TICKER}/scoring_input.json
- scoring_input_batch_*.json: research/ca_strategy_poc/workspaces/{TICKER}/batch_inputs/
- scored_batch_*.json: research/ca_strategy_poc/workspaces/{TICKER}/phase2_output/{TICKER}/
- scoring_output.json: research/ca_strategy_poc/workspaces/{TICKER}/scoring_output.json
```

## 使用エージェント

| エージェント | Step | 説明 |
|-------------|------|------|
| `transcript-claim-extractor` | Step 2 | KB1-T/KB3-T+dogma.mdで主張を抽出し extraction_output.json を生成 |
| `transcript-claim-scorer` | Step 4.3（各バッチ） | KB1-T/KB2-T/KB3-T+dogma.mdで4段階評価を実行し scored_batch_{n}.json を生成 |

## 使用 Python 関数（agent_io.py）

| 関数 | Step | 説明 |
|------|------|------|
| `prepare_extraction_input` | Step 1 | トランスクリプトロード・KB パス構築・extraction_input.json 生成 |
| `validate_extraction_output` | Step 3 | extraction_output.json の Pydantic バリデーション |
| `prepare_scoring_input` | Step 4.1 | Phase 1 出力パス・KB パス構築・scoring_input.json 生成 |
| `prepare_scoring_batches` | Step 4.2 | claim ID のバッチ分割・scoring_input_batch_{n}.json 生成 |
| `consolidate_scored_claims` | Step 4.4 | scored_batch_{n}.json を統合して scoring_output.json を生成 |
| `validate_scoring_output` | Step 5 | scoring_output.json の Pydantic バリデーション |

## 関連ファイル

- **agent_io.py**: `src/dev/ca_strategy/agent_io.py`
- **transcript-claim-extractor**: `.claude/agents/ca-strategy/transcript-claim-extractor.md`
- **transcript-claim-scorer**: `.claude/agents/ca-strategy/transcript-claim-scorer.md`
- **dogma.md**: `analyst/Competitive_Advantage/analyst_YK/dogma/dogma_v1.0.md`
- **KB ベースディレクトリ**: `analyst/transcript_eval/`
- **トランスクリプトディレクトリ**: `research/ca_strategy_poc/transcripts/`
- **設定ディレクトリ**: `research/ca_strategy_poc/config/`

## 注意事項

- 本コマンドは情報提供を目的としており、投資助言ではありません
- PoiT 制約（cutoff_date=2015-09-30）により、カットオフ日以降の情報は使用されません
- `ca-strategy-lead`（Agent Teams 方式）は使用しません。コマンド自身がオーケストレーターとして機能します
- Phase 3-5（スコア集計・セクター中立化・ポートフォリオ構築）は本コマンドの対象外です
