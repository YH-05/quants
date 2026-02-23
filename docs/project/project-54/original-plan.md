# CA Strategy パイプライン: LLM処理のエージェント化設計

## Context

ca_strategy パイプラインの Phase 1（主張抽出）と Phase 2（スコアリング）は、現在 `anthropic.Anthropic()` で Python SDK 経由の API 呼び出しを行っている。Claude Code サブスクリプションでは Python SDK からの直接 API 呼び出しが不可能（OAuth 非対応エラー）。

**方針**: 全 LLM 処理を Claude Code サブエージェント（Task tool）に移行。エージェント自身が Claude であり、KB ファイルを読み込んで推論・抽出・スコアリングを直接実行する。API 呼び出しは不要になる。

## アーキテクチャ変更

### Before（API 依存）

```
Python Orchestrator
  → ClaimExtractor._extract_single()
    → call_llm(anthropic.Anthropic(), prompt)   ← API呼び出し
    → JSON parse → Claim[]
  → ClaimScorer._score_single_ticker()
    → call_llm(anthropic.Anthropic(), prompt)   ← API呼び出し
    → JSON parse → ScoredClaim[]
  → Phase 3-5: 純粋 Python
```

### After（エージェント化）

```
Claude Code スキル/コマンド
  → Phase 0: Python (workspace setup)
  → Phase 1: Task(transcript-claim-extractor)    ← エージェントがClaude自身として推論
    → Agent: Read KB + Read transcript → 推論 → Write claims.json
    → Python: Pydantic バリデーション
  → Phase 2: Task(transcript-claim-scorer)       ← エージェントがClaude自身として推論
    → Agent: Read KB + Read claims → 推論 → Write scored.json
    → Python: Pydantic バリデーション
  → Phase 3-5: Python（既存コードそのまま使用）
```

## 変更対象ファイル

### 1. エージェント定義の改修（最重要）

#### `.claude/agents/ca-strategy/transcript-claim-extractor.md`

**変更内容**: Python `ClaimExtractor` クラスへの参照を削除し、エージェント自身が推論する設計に変更。

- 「ClaimExtractor を使用して」→ エージェント自身が KB ファイルを読み、ルールを適用して主張を抽出
- 「Claude API エラー」→ 不要（エージェント自身が Claude）
- 「CostTracker でLLMコスト記録」→ 削除（サブスクリプション利用のためコスト追跡不要）
- system_prompt_transcript.md の内容をエージェントプロンプトに統合
- 出力 JSON スキーマを types.py の Claim モデルに基づいて明示
- 銘柄ごとに 1 回のエージェント呼び出し（複数トランスクリプトをまとめて処理）

**出力フォーマット**（Claim モデル準拠）:

```json
{
  "ticker": "DIS",
  "claims": [
    {
      "id": "DIS-CA-001",
      "claim_type": "competitive_advantage",
      "claim": "主張テキスト",
      "evidence": "証拠テキスト",
      "rule_evaluation": {
        "applied_rules": ["rule_1_t", "rule_2_t"],
        "results": {"rule_1_t": true, "rule_2_t": false},
        "confidence": 0.7,
        "adjustments": ["理由"]
      }
    }
  ]
}
```

#### `.claude/agents/ca-strategy/transcript-claim-scorer.md`

**変更内容**: Python `ClaimScorer` クラスへの参照を削除し、同様にエージェント自身が 4 段階評価を実行する設計に変更。

- KB2-T パターン集（12 ファイル）の参照方法はそのまま
- 4 段階評価フロー（Gatekeeper → KB1 → KB2 → KB3 Calibration）をエージェントプロンプトに明示
- 出力 JSON スキーマを types.py の ScoredClaim モデルに基づいて明示

**出力フォーマット**（ScoredClaim モデル準拠）:

```json
{
  "ticker": "DIS",
  "scored_claims": [
    {
      "id": "DIS-CA-001",
      "claim_type": "competitive_advantage",
      "claim": "主張テキスト",
      "evidence": "証拠テキスト",
      "rule_evaluation": { ... },
      "final_confidence": 0.65,
      "adjustments": [
        {"source": "kb2_pattern_I", "adjustment": 0.1, "reasoning": "理由"}
      ],
      "gatekeeper": {
        "rule9_factual_error": false,
        "rule3_industry_common": false,
        "triggered": false,
        "override_confidence": null
      },
      "kb1_evaluations": [
        {"rule_id": "rule_1_t", "result": true, "reasoning": "理由"}
      ],
      "kb2_patterns": [
        {"pattern_id": "pattern_I", "matched": true, "adjustment": 0.1, "reasoning": "理由"}
      ],
      "overall_reasoning": "4段階評価の総合判断"
    }
  ]
}
```

### 2. Python コード変更

#### `src/dev/ca_strategy/agent_io.py`（新規作成）

エージェントパイプライン用の入出力ヘルパーモジュール。

```python
"""Agent-based pipeline I/O helpers.

Provides functions for:
1. Preparing input files for subagent extraction/scoring
2. Validating subagent JSON output against Pydantic models
3. Running Phase 3-5 from validated agent output
"""

# 主要関数:
def prepare_extraction_input(config_path, workspace_dir, kb_base_dir, ticker) -> dict:
    """Phase 1 エージェント用の入力情報を準備"""

def validate_extraction_output(output_path, ticker) -> list[Claim]:
    """Phase 1 エージェント出力を Pydantic Claim モデルで検証"""

def prepare_scoring_input(workspace_dir, kb_base_dir, ticker) -> dict:
    """Phase 2 エージェント用の入力情報を準備"""

def validate_scoring_output(output_path, ticker) -> list[ScoredClaim]:
    """Phase 2 エージェント出力を Pydantic ScoredClaim モデルで検証"""

def run_phase3_to_5(workspace_dir, config_path) -> None:
    """Phase 3-5 を既存 Python コードで実行"""
```

#### `src/dev/ca_strategy/extractor.py`（変更なし or 最小変更）

既存の `ClaimExtractor` クラスは API ベースの実行パスとして保持。新規 `agent_io.py` が出力バリデーション用に `_parse_single_claim()` のロジックを再利用する。

#### `src/dev/ca_strategy/scorer.py`（変更なし or 最小変更）

同上。既存コードは保持し、`agent_io.py` からバリデーションロジックを参照。

### 3. 不要コードの整理（Phase 2 以降で実施）

- `_llm_utils.py` から `call_llm()`, `extract_text_from_response()` の `anthropic` 依存部分
- `extractor.py`, `scorer.py` の `import anthropic` と `client` パラメータ
- `orchestrator.py` から API ベースの Phase 1/2 実行パス

→ まずは DIS サンプルでエージェントベースの動作を確認してから整理する。

## 実行フロー（DIS サンプル）

```
Step 1: Python で workspace 準備
  $ uv run python -c "from dev.ca_strategy.agent_io import prepare_extraction_input; ..."

Step 2: Task(transcript-claim-extractor) で DIS の主張抽出
  → Agent reads: KB1-T(9), KB3-T(5), dogma.md, system_prompt, DIS transcripts(7)
  → Agent writes: workspace_dis_sample/phase1/DIS_claims.json

Step 3: Python で Phase 1 出力を検証
  $ uv run python -c "from dev.ca_strategy.agent_io import validate_extraction_output; ..."

Step 4: Task(transcript-claim-scorer) で DIS のスコアリング
  → Agent reads: KB1-T(9), KB2-T(12), KB3-T(5), dogma.md, DIS claims
  → Agent writes: workspace_dis_sample/phase2/DIS_scored.json

Step 5: Python で Phase 2 出力を検証
  $ uv run python -c "from dev.ca_strategy.agent_io import validate_scoring_output; ..."

Step 6: Python で Phase 3-5 実行
  $ uv run python -c "from dev.ca_strategy.agent_io import run_phase3_to_5; ..."
```

## 検証方法

1. **Phase 1 出力**: DIS で 5-15 件の Claim が JSON 出力され、Pydantic バリデーション通過
2. **Phase 2 出力**: 各 Claim に final_confidence (0.1-0.9) が付与され、ScoredClaim バリデーション通過
3. **Phase 3-5 出力**: portfolio_weights.json, portfolio_summary.md が生成される
4. **API 非依存**: `ANTHROPIC_API_KEY` 未設定でも全フェーズが完了する

## 作業順序

1. `agent_io.py` 新規作成（入力準備 + 出力バリデーション + Phase 3-5 ランナー）
2. `transcript-claim-extractor.md` 改修（Python クラス参照削除、推論指示追加、JSON スキーマ明示）
3. `transcript-claim-scorer.md` 改修（同上）
4. DIS サンプル実行テスト
5. （成功後）不要な API 依存コードの整理
