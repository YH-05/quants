# research-meta.schema.md スキーマ

> 生成タスク: T0 | 生成エージェント: ca-eval-lead
> 読み込み先: T9_accuracy（research-meta.jsonのtask_resultsとoutputsを参照）

## JSONスキーマ

```json
{
  "research_id": "CA_eval_20260218-1454_AME",
  "type": "ca_eval",
  "ticker": "AME",
  "created_at": "2026-02-18T14:54:00Z",
  "completed_at": "2026-02-18T16:00:00Z",
  "parameters": {
    "ticker": "AME",
    "report_path": "analyst/raw/AME US.md",
    "skip_industry": true
  },
  "status": "completed",
  "workflow": {
    "phase_0": "done",
    "phase_1": "done",
    "phase_2": "done",
    "phase_3": "done",
    "phase_4": "done",
    "phase_5": "done"
  },
  "task_results": {
    "T0_setup": { "status": "completed", "owner": "ca-eval-lead", "output": "00_meta/research-meta.json" },
    "T1_sec_filings": { "status": "completed", "owner": "ca-eval-lead", "output": "01_data_collection/sec-data.json", "note": "SEC EDGAR MCP利用不可のためアナリストレポートから抽出" },
    "T2_report_parser": { "status": "completed", "owner": "ca-eval-lead", "output": "01_data_collection/parsed-report.json" },
    "T3_industry": { "status": "skipped", "owner": "ca-eval-lead", "note": "PoC段階のポリシーによりスキップ（SEC EDGAR以外の外部データソース不使用）" },
    "T4_claim_extractor": { "status": "completed", "owner": "ca-eval-lead", "output": "02_claims/claims.json", "claims_count": 7 },
    "T5_fact_checker": { "status": "completed", "owner": "ca-eval-lead", "output": "03_verification/fact-check.json", "verified": 18, "contradicted": 0, "unverifiable": 1 },
    "T6_pattern_verifier": { "status": "completed", "owner": "ca-eval-lead", "output": "03_verification/pattern-verification.json" },
    "T7_report_generator": { "status": "completed", "owner": "ca-eval-lead", "output": ["04_output/draft-report.md", "04_output/structured.json"] },
    "T8_ai_critique": { "status": "completed", "owner": "ca-eval-lead", "output": ["04_output/critique.json", "04_output/revised-report-{TICKER}.md"], "critical_issues": 2, "minor_issues": 5 },
    "T9_accuracy": { "status": "completed", "owner": "ca-eval-lead", "output": "04_output/accuracy-report.json", "mode": "simplified", "verdict": "pass" }
  },
  "outputs": {
    "final_report": "04_output/revised-report-{TICKER}.md",
    "draft_report": "04_output/draft-report.md",
    "structured_json": "04_output/structured.json",
    "critique": "04_output/critique.json",
    "accuracy": "04_output/accuracy-report.json"
  },
  "summary": {
    "avg_ca_confidence": 50,
    "avg_cagr_confidence": 61,
    "strongest_claims": ["#1 スイッチングコスト（70%）", "#2 M&A実行能力（70%、大型化リスク条件付き）"],
    "kb3_closest_analog": "CHD（平均50%一致）",
    "notable_t8_modification": "Claim #2 CAGR confidence: 大型化リスク顕在化時は50%に低下というアノテーション追加"
  }
}
```

## フィールド説明

| フィールド | 型 | 必須 | 説明 |
|-----------|-----|------|------|
| `research_id` | string | ✅ | ワークフロー固有ID。形式: `CA_eval_{YYYYMMDD-HHMM}_{TICKER}` |
| `type` | string | ✅ | 固定値: `"ca_eval"` |
| `ticker` | string | ✅ | 銘柄ティッカーシンボル（大文字） |
| `created_at` | string (ISO 8601) | ✅ | ワークフロー開始時刻 |
| `completed_at` | string (ISO 8601) | ✅ | ワークフロー完了時刻（進行中は `null`） |
| `parameters` | object | ✅ | 入力パラメータ |
| `parameters.ticker` | string | ✅ | 銘柄ティッカー |
| `parameters.report_path` | string | ✅ | アナリストレポートファイルパス |
| `parameters.skip_industry` | boolean | ✅ | T3（業界調査）スキップフラグ |
| `status` | string | ✅ | ワークフロー状態。`"running"` / `"completed"` / `"failed"` |
| `workflow` | object | ✅ | フェーズ別進捗。各値は `"done"` / `"running"` / `"pending"` / `"skipped"` |
| `task_results` | object | ✅ | タスク別実行結果。キーはタスクID（T0_setup〜T9_accuracy） |
| `task_results.{id}.status` | string | ✅ | タスク状態: `"completed"` / `"skipped"` / `"failed"` |
| `task_results.{id}.owner` | string | ✅ | 担当エージェント名 |
| `task_results.{id}.output` | string \| array | ✅ | 出力ファイルパス（単一または配列） |
| `task_results.{id}.note` | string | - | 補足説明（スキップ理由・制限事項等） |
| `task_results.T5_fact_checker.verified` | integer | ✅ | 検証済み事実の件数 |
| `task_results.T5_fact_checker.contradicted` | integer | ✅ | 矛盾が見つかった事実の件数 |
| `task_results.T5_fact_checker.unverifiable` | integer | ✅ | 検証不能な事実の件数 |
| `task_results.T4_claim_extractor.claims_count` | integer | ✅ | 抽出された主張の件数 |
| `task_results.T8_ai_critique.critical_issues` | integer | ✅ | 批評で検出されたcritical issue件数 |
| `task_results.T8_ai_critique.minor_issues` | integer | ✅ | 批評で検出されたminor issue件数 |
| `task_results.T9_accuracy.mode` | string | ✅ | 精度チェックモード: `"simplified"` / `"full"` |
| `task_results.T9_accuracy.verdict` | string | ✅ | 精度チェック結果: `"pass"` / `"fail"` |
| `outputs` | object | ✅ | 最終成果物へのファイルパス |
| `outputs.final_report` | string | ✅ | 最終レポート（revised-report-{TICKER}.md）パス |
| `outputs.draft_report` | string | ✅ | ドラフトレポートパス |
| `outputs.structured_json` | string | ✅ | 構造化JSONパス |
| `outputs.critique` | string | ✅ | 批評JSONパス |
| `outputs.accuracy` | string | ✅ | 精度レポートJSONパス |
| `summary` | object | ✅ | ワークフロー結果サマリー |
| `summary.avg_ca_confidence` | integer | ✅ | 全主張のCA確信度の平均（0-100） |
| `summary.avg_cagr_confidence` | integer | ✅ | 全主張のCAGR確信度の平均（0-100） |
| `summary.strongest_claims` | array[string] | ✅ | 最も強い主張の一覧（タイトルと確信度） |
| `summary.kb3_closest_analog` | string | ✅ | KB3で最も類似した銘柄とその根拠 |
| `summary.notable_t8_modification` | string | - | T8批評で行われた重要な修正内容 |

## バリデーションルール

- `research_id` は `CA_eval_{YYYYMMDD-HHMM}_{TICKER}` の形式に従うこと
- `created_at` / `completed_at` はISO 8601形式（UTC）で記述すること
- `status` が `"completed"` の場合、`completed_at` は必須（nullは不可）
- `task_results` には T0_setup から T9_accuracy の全タスクキーが含まれること（スキップ扱いのタスクは `"skipped"` で記録）
- `outputs` の各フィールドは全て存在すること（T8完了後に `final_report` が確定する）
- `summary.avg_ca_confidence` は `summary.avg_cagr_confidence` との差が通常10〜20ポイント以内であること（大きく乖離する場合は要確認）
