# Phase 2 スコアリング バッチ分割実装プラン

**作成日**: 2026-02-23
**対象**: CA Strategy パイプライン Phase 2 — 32Kトークン上限回避

---

## Context（背景・問題）

`transcript-claim-scorer` エージェントが15件のScoredClaimを1回のWrite操作で書き出そうとしたところ、出力トークン上限（32,000トークン）を超えてエラーになった。その後エージェントが自己リカバリーしたが、8件しか出力できず7件（DIS_009〜DIS_015）が欠落している。

**根本原因**: 1エージェント呼び出しが全件分の詳細JSON（kb1_evaluations×9 + kb2_patterns×12 × 15件）を一度に生成しようとした。

**ユーザーの方針**: 出力スキーマは変更せず、サブエージェントへの分割移譲でトークン上限を回避する。

---

## 解決方針: バッチ分割（batch_size=5）

1エージェント呼び出し=全15件 → **1エージェント呼び出し=5件** に分割し、3回呼び出す。

```
Before（失敗）:
  transcript-claim-scorer (15件) → scoring_output.json → 32K超過エラー

After（修正後）:
  transcript-claim-scorer batch_1 (DIS_001〜005) → scored_batch_1.json  ┐
  transcript-claim-scorer batch_2 (DIS_006〜010) → scored_batch_2.json  ┤→ Python統合→ scoring_output.json
  transcript-claim-scorer batch_3 (DIS_011〜015) → scored_batch_3.json  ┘
```

**推定トークン削減効果**:
- 修正前: 15件 × 2,500トークン ≒ 37,500トークン → **32K超過**
- 修正後: 5件 × 2,500トークン ≒ 12,500トークン/バッチ → **32K以内**

---

## 変更ファイル一覧

| ファイル | 変更内容 |
|---------|---------|
| `src/dev/ca_strategy/agent_io.py` | 関数2つ追加 |
| `.claude/agents/ca-strategy/transcript-claim-scorer.md` | バッチ対応（`target_claim_ids` フィールド追加） |
| `.claude/commands/run-ca-strategy-sample.md` | Step 4 をバッチ対応に改修 |

---

## 詳細実装計画

### 1. `agent_io.py` — 関数2つ追加

#### 1-A: `prepare_scoring_batches()`

```python
def prepare_scoring_batches(
    workspace_dir: Path,
    kb_base_dir: Path,
    ticker: str,
    batch_size: int = 5,
) -> list[dict[str, Any]]:
    """Phase 1出力からバッチ分割されたscoring_input_batch_{n}.jsonを生成する。

    extraction_output.json から claim_ids を取得し、batch_size ずつ分割。
    各バッチに対して scoring_input_batch_{n}.json を書き出す。

    Returns: バッチ入力 dict のリスト（各バッチのパス・claim_ids 含む）
    """
```

生成ファイル例:
```json
// scoring_input_batch_1.json
{
  "ticker": "DIS",
  "phase1_output_dir": "research/.../phase1_output/DIS",
  "kb1_dir": "analyst/transcript_eval/kb1_rules_transcript",
  "kb2_dir": "analyst/transcript_eval/kb2_patterns_transcript",
  "kb3_dir": "analyst/transcript_eval/kb3_fewshot_transcript",
  "workspace_dir": "research/.../workspace_dis_sample",
  "target_claim_ids": ["DIS_001", "DIS_002", "DIS_003", "DIS_004", "DIS_005"],
  "output_path": "research/.../phase2_output/DIS/scored_batch_1.json",
  "batch_index": 1,
  "batch_total": 3
}
```

#### 1-B: `consolidate_scored_claims()`

```python
def consolidate_scored_claims(
    workspace_dir: Path,
    ticker: str,
) -> Path:
    """phase2_output/{ticker}/scored_batch_*.json を統合し scoring_output.json を生成する。

    Returns: scoring_output.json のパス
    """
```

処理内容:
- `phase2_output/{ticker}/scored_batch_*.json` をファイル名順で全件読み込み
- `scored_claims[]` を統合
- `metadata.scored_count` を再集計
- `{workspace_dir}/scoring_output.json` に書き出す

---

### 2. `transcript-claim-scorer.md` — バッチ対応追加

**追加フィールド** (`scoring_input.json` スキーマ):

| フィールド | 型 | 必須 | 説明 |
|-----------|-----|------|------|
| `target_claim_ids` | `list[str]` | No | スコアリング対象のclaim IDリスト。省略時は全件 |
| `output_path` | `string` | No | 出力ファイルパス。省略時は `{workspace_dir}/scoring_output.json` |
| `batch_index` | `int` | No | バッチ番号（ログ用） |
| `batch_total` | `int` | No | 総バッチ数（ログ用） |

**フロー変更**（Step 3 に追加）:
```
Step 3: Phase 1出力ファイルを Read して主張一覧を取得する
  → target_claim_ids が指定されている場合: 該当する claim のみ処理する
  → 指定がない場合: 全件処理する（後方互換）
```

**Step 6 の出力先変更**:
```
Step 6: output_path に書き出す
  → output_path が指定されている場合: そのパスに書き出す
  → 指定がない場合: {workspace_dir}/scoring_output.json に書き出す（後方互換）
```

---

### 3. `run-ca-strategy-sample.md` — Step 4 改修

**現在の Step 4**:
```
Step 4.1: scoring_input.json 生成（Python）
Step 4.2: transcript-claim-scorer を1回呼び出す（全件）
```

**修正後の Step 4**:
```
Step 4.1: scoring_input.json 生成（Python）※既存コマンド変更なし
Step 4.2: バッチ分割入力を生成（Python）
  → prepare_scoring_batches() でバッチ数とバッチ入力ファイルを取得
  → 標準出力にバッチ数とバッチ入力ファイルパス一覧を表示

Step 4.3: 各バッチに対してエージェント呼び出し（並列）
  → バッチ数に応じて transcript-claim-scorer を呼び出す
  → 各バッチの出力: phase2_output/{TICKER}/scored_batch_{n}.json

Step 4.4: バッチ統合（Python）
  → consolidate_scored_claims() を呼び出す
  → scoring_output.json を生成
```

Step 4.2の Bash コマンド例:
```bash
uv run python -c "
from pathlib import Path
from dev.ca_strategy.agent_io import prepare_scoring_batches

batches = prepare_scoring_batches(
    workspace_dir=Path('research/ca_strategy_poc/workspace_dis_sample'),
    kb_base_dir=Path('analyst/transcript_eval'),
    ticker='DIS',
    batch_size=5,
)
print(f'batch_count={len(batches)}')
for b in batches:
    print(f'batch_input={b[\"input_path\"]}')
    print(f'batch_ids={b[\"target_claim_ids\"]}')
"
```

Step 4.3のエージェント呼び出し例（バッチ数が3の場合、並列実行）:
```
Task: transcript-claim-scorer（バッチ1）
指示: scoring_input_batch_1.json を読み込み DIS_001〜DIS_005 のみスコアリングし
     scored_batch_1.json に書き出してください。

Task: transcript-claim-scorer（バッチ2）
指示: scoring_input_batch_2.json を読み込み DIS_006〜DIS_010 のみスコアリングし
     scored_batch_2.json に書き出してください。

Task: transcript-claim-scorer（バッチ3）
指示: scoring_input_batch_3.json を読み込み DIS_011〜DIS_015 のみスコアリングし
     scored_batch_3.json に書き出してください。
```

Step 4.4の Bash コマンド例:
```bash
uv run python -c "
from pathlib import Path
from dev.ca_strategy.agent_io import consolidate_scored_claims

output_path = consolidate_scored_claims(
    workspace_dir=Path('research/ca_strategy_poc/workspace_dis_sample'),
    ticker='DIS',
)
print(f'Consolidated to: {output_path}')
"
```

---

## 出力ディレクトリ構造（修正後）

```
workspace_dis_sample/
├── extraction_input.json
├── scoring_input.json               （既存、変更なし）
├── scoring_input_batch_1.json       （新規: target_claim_ids=[DIS_001..005]）
├── scoring_input_batch_2.json       （新規: target_claim_ids=[DIS_006..010]）
├── scoring_input_batch_3.json       （新規: target_claim_ids=[DIS_011..015]）
├── scoring_output.json              （新規: 統合後の全15件）
├── phase1_output/DIS/
│   └── extraction_output.json
└── phase2_output/DIS/
    ├── scored_batch_1.json          （新規: DIS_001〜005）
    ├── scored_batch_2.json          （新規: DIS_006〜010）
    └── scored_batch_3.json          （新規: DIS_011〜015）
```

---

## リスク評価

| リスク | 影響 | 対策 |
|--------|------|------|
| バッチ数が動的（5件/バッチなら3バッチ、8件なら2バッチ） | 中 | prepare_scoring_batches() が返すリストを使って動的にループ |
| バッチ並列実行でKBファイルを3回読み込む | 低 | 合計読込量は増えるが1回あたりは問題なし |
| scored_batch_*.jsonのソート順が狂う | 低 | consolidate時にbatch_index順でソート |
| 既存の`validate_scoring_output`との互換性 | 低 | 入力は consolidated scoring_output.json で変更なし |

---

## 検証手順

1. 実装後、`/run-ca-strategy-sample` を再実行
2. Step 4.2 でバッチ数=3、claim_ids のリストが出力されることを確認
3. Step 4.3 で scored_batch_1.json, scored_batch_2.json, scored_batch_3.json が生成されることを確認（各ファイル≦32K制限）
4. Step 4.4 で scoring_output.json が生成され、scored_claims の件数=15 であることを確認
5. Step 5 バリデーション: `Validated 15 scored claims` + `Phase 2 validation: PASS` を確認

---

## テスト追加（agent_io.py）

`tests/dev/ca_strategy/unit/test_agent_io.py` に追加:
- `test_正常系_prepare_scoring_batches_5件ずつ3バッチ生成`
- `test_正常系_prepare_scoring_batches_件数がbatch_size未満`
- `test_正常系_consolidate_scored_claims_3バッチを統合`
- `test_異常系_consolidate_scored_claims_バッチファイル不在`
