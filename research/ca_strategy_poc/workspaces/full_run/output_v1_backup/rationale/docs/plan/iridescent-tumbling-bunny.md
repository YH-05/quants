# Plan: rationale.md Evidence 欠落の修正

## Context

CA Strategy `full_run` パイプラインで生成された29銘柄のポートフォリオ rationale.md のうち、
**12銘柄で Evidence フィールドが空**になっている。

根本原因は3層構造:
1. Phase 1 エクストラクターが **4種類のスキーマ** を出力（A/B/C/D）
2. Phase 2 スコアラーが Schema B/C/D の evidence フィールドを保持しなかった
3. `build_phase2_checkpoint` が空の `claim_lookup={}` を渡し、Phase 1 からの復元が不能

ポートフォリオ構成（銘柄・ウェイト）は evidence と無関係なため変更しない。
LLM 再実行不要。既存データのみで完結する。

---

## Phase 1 スキーマ一覧（確定済み）

| Schema | 件数 | ID | claim | evidence | rule_evaluation |
|--------|------|----|-------|----------|-----------------|
| A | ~51 | `id` ("TICKER-001") | `claim` | `evidence` (str) | dict (完全) |
| B | ~93 | `claim_id` ("TICKER_001") | `claim_text` | `evidence_quotes` (str[]) | なし |
| C | ~170 | `id` ("TICKER-001" or int) | `claim` | `evidence_from_transcript` (str) | dict (confidence 0-100) |
| D | ~26 | `claim_id` ("TICKER-001") | `claim_text` | `evidence_quote` (str, 単数) | なし |

Phase 1 → Phase 2 の ID 対応は12銘柄中10銘柄で完全一致。CPI/DAL は件数差あるが先頭N件のID一致を確認済み。

---

## 実装手順

### Step 1: `_parse_raw_claim` の Schema B/D 対応 (agent_io.py)

**ファイル**: `src/dev/ca_strategy/agent_io.py`

**(a) claim ID フォールバック (L1045)**
```python
# Before:
claim_id = raw.get("id", "unknown")
# After:
claim_id = raw.get("id") or raw.get("claim_id", "unknown")
if isinstance(claim_id, int):
    claim_id = str(claim_id)
```

**(b) rule_evaluation 任意化 (L1047-1055)**
```python
# Before: rule_evaluation が dict でなければ None を返す
# After: なければ top-level confidence からデフォルト構築
rule_eval_raw = raw.get("rule_evaluation")
if not isinstance(rule_eval_raw, dict):
    raw_confidence = raw.get("confidence", 0.5)
    confidence = _normalize_confidence(raw_confidence)
    rule_evaluation = RuleEvaluation(
        applied_rules=[],
        results={},
        confidence=confidence,
        adjustments=[],
    )
else:
    # ... existing parsing logic (変更なし) ...
```

**(c) evidence フォールバック拡張 (L1122-1125)**
```python
# Before:
evidence = raw.get("evidence") or raw.get("evidence_from_transcript", "")
if not evidence:
    evidence = raw.get("claim", "No evidence provided")
# After:
evidence = raw.get("evidence") or raw.get("evidence_from_transcript", "")
if not evidence:
    eq = raw.get("evidence_quotes") or raw.get("evidence_quote")
    if isinstance(eq, list):
        evidence = "; ".join(eq)
    elif isinstance(eq, str):
        evidence = eq
if not evidence:
    evidence = raw.get("claim") or raw.get("claim_text", "No evidence provided")
```

**(d) claim text フォールバック (L1127)**
```python
# Before:
claim_text = raw.get("claim", "")
# After:
claim_text = raw.get("claim", "") or raw.get("claim_text", "")
```

### Step 2: `_parse_raw_scored_claim` のフォールバック拡張 (agent_io.py)

**ファイル**: `src/dev/ca_strategy/agent_io.py`

**(a) claim ID フォールバック (L1185)**
```python
# Before:
claim_id = raw.get("id", "unknown")
# After:
claim_id = raw.get("id") or raw.get("claim_id", "unknown")
if isinstance(claim_id, int):
    claim_id = str(claim_id)
```

**(b) fallback evidence 拡張 (L1242-1243)**
```python
# Before:
fallback_claim = raw.get("claim", "")
fallback_evidence = raw.get("evidence", "")
# After:
fallback_claim = raw.get("claim", "") or raw.get("claim_text", "")
fallback_evidence = raw.get("evidence", "")
if not fallback_evidence:
    fallback_evidence = raw.get("evidence_from_transcript", "")
if not fallback_evidence:
    eq = raw.get("evidence_quotes") or raw.get("evidence_quote")
    if isinstance(eq, list):
        fallback_evidence = "; ".join(eq)
    elif isinstance(eq, str):
        fallback_evidence = eq
```

### Step 3: `build_phase2_checkpoint` に Phase 1 参照を追加 (agent_io.py)

**ファイル**: `src/dev/ca_strategy/agent_io.py`

**(a) 新しいヘルパー関数を追加**
```python
def _build_phase1_evidence_lookup(
    phase1_dirs: list[Path],
) -> dict[str, dict[str, Claim]]:
    """Phase 1 extraction outputs から {ticker: {claim_id: Claim}} を構築."""
```
- `phase1_dirs` の各ディレクトリ下 `*/extraction_output.json` を glob
- 各ファイルを `validate_extraction_output` で Claim リストに変換（Step 1 の修正済み版）
- `{ticker: {claim.id: claim}}` の lookup を構築

**(b) `build_phase2_checkpoint` に `phase1_dirs` パラメータ追加 (L691)**
```python
def build_phase2_checkpoint(
    workspace_dir: Path,
    output_path: Path,
    skip_missing: bool = False,
    phase1_dirs: list[Path] | None = None,  # NEW: 後方互換、デフォルト None
) -> dict[str, list[dict[str, Any]]]:
```

**(c) L803 の修正**
```python
# Before:
parsed = _parse_raw_scored_claim(raw, {}, ticker)
# After:
ticker_lookup = phase1_lookup.get(ticker, {})
parsed = _parse_raw_scored_claim(raw, ticker_lookup, ticker)
```

### Step 4: テスト追加

**ファイル**: `tests/dev/ca_strategy/unit/test_agent_io.py`

追加するテストケース:

| テスト | 対象関数 | 内容 |
|--------|----------|------|
| `test_正常系_SchemaB形式のclaim_idとevidence_quotesをパースできる` | `validate_extraction_output` | Schema B 入力（`claim_id`, `claim_text`, `evidence_quotes`） |
| `test_正常系_SchemaC形式のevidence_from_transcriptをパースできる` | `validate_extraction_output` | Schema C 入力（`evidence_from_transcript`, confidence=50） |
| `test_正常系_SchemaD形式のevidence_quoteをパースできる` | `validate_extraction_output` | Schema D 入力（`evidence_quote` 単数） |
| `test_正常系_rule_evaluationがない場合デフォルトで構築する` | `validate_extraction_output` | Schema B/D（rule_evaluation なし） |
| `test_正常系_claim_idフォールバックでidが取得できる` | `validate_extraction_output` | `claim_id` のみ |
| `test_正常系_phase1_dirsで渡したPhase1データからevidenceが復元される` | `build_phase2_checkpoint` | phase1_dirs パラメータの動作確認 |
| `test_正常系_phase1_dirsがNoneのとき既存動作と同一` | `build_phase2_checkpoint` | 後方互換性確認 |

### Step 5: `phase2_scored.json` の再ビルドと rationale 再生成

修正済みコードで以下を実行:

```python
from pathlib import Path
from dev.ca_strategy.agent_io import build_phase2_checkpoint

workspace = Path("research/ca_strategy_poc/workspaces/full_run")

# chunk_workspaces の phase1_output ディレクトリを収集
phase1_dirs = sorted(workspace.glob("chunk_workspaces/chunk_*/phase1_output"))

# phase2_scored.json を再ビルド（Phase 1 evidence 付き）
build_phase2_checkpoint(
    workspace_dir=workspace,
    output_path=workspace / "checkpoints" / "phase2_scored.json",
    skip_missing=True,
    phase1_dirs=phase1_dirs,
)
```

続けて rationale を再生成:
```python
from dev.ca_strategy.agent_io import run_phase3_to_5

# Phase 3-5 再実行（phase2_scored.json から）
run_phase3_to_5(
    workspace_dir=workspace,
    config_path=Path("research/ca_strategy_poc/config"),
)
```

> **注**: `run_phase3_to_5` は `Orchestrator.run_from_checkpoint(phase=3)` を呼ぶ。
> Phase 3 (aggregation) は `final_confidence` のみ使用するため、evidence の変更で
> ポートフォリオ構成は変わらない。

---

## 修正ファイル一覧

| ファイル | 修正内容 |
|----------|----------|
| `src/dev/ca_strategy/agent_io.py` | `_parse_raw_claim`, `_parse_raw_scored_claim`, `build_phase2_checkpoint`, 新規ヘルパー |
| `tests/dev/ca_strategy/unit/test_agent_io.py` | Schema B/C/D テストケース追加、`phase1_dirs` テスト追加 |

**変更しないファイル**: `output.py`, `aggregator.py`, `types.py`, `portfolio_builder.py`

---

## 検証方法

### 1. テスト
```bash
uv run pytest tests/dev/ca_strategy/unit/test_agent_io.py -v
```

### 2. Evidence 補完の確認
```bash
# 再ビルド後の phase2_scored.json で空 evidence がないことを確認
python3 -c "
import json
with open('research/ca_strategy_poc/workspaces/full_run/checkpoints/phase2_scored.json') as f:
    data = json.load(f)
empty = [(t, sum(1 for c in cs if not c.get('evidence',''))) for t, cs in data.items()]
print([t for t, e in empty if e > 0])  # 空のリストであること
"
```

### 3. ポートフォリオ不変の確認
```bash
# 再生成前に portfolio_weights.json をバックアップ
cp output/portfolio_weights.json output/portfolio_weights.json.bak
# 再生成後に diff
diff output/portfolio_weights.json output/portfolio_weights.json.bak
# → 差分なし
```

### 4. Rationale Evidence 確認
```bash
# 全 rationale で Evidence が非空であること
grep -c "^\- \*\*Evidence\*\*:$" output/rationale/*.md
# → 全ファイル 0
```

### 5. 既存テスト回帰
```bash
make check-all
```

---

## リスクと対策

| リスク | 可能性 | 対策 |
|--------|--------|------|
| `_parse_raw_claim` の Schema B/D 受入でClaim件数が増加 | 想定通り | デフォルト confidence=0.5 は保守的。Phase 1 checkpoint は今回使わない |
| CPI/DAL の ID 件数不一致で一部 evidence が復元不能 | 低 | P2 側のID (1,2,...7) は P1 の先頭7件に対応（確認済み） |
| `run_phase3_to_5` でポートフォリオ構成変更 | なし | evidence は score に無関係。念のため diff で確認 |
| `build_phase2_checkpoint` の API 変更で呼出元に影響 | なし | `phase1_dirs` はデフォルト `None`（後方互換） |
