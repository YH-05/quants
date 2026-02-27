# structured.schema.md スキーマ

> 生成タスク: T7 | 生成エージェント: ca-report-generator
> 読み込み先: T8_ai_critique（主張一覧と評価結果を参照してレビュー実施）、T9_accuracy（overall_summaryを参照）

## JSONスキーマ

```json
{
  "research_id": "CA_eval_20260218-1454_AME",
  "ticker": "AME",
  "company_name": "AMETEK, Inc.",
  "generated_at": "2026-02-18T15:35:00Z",
  "generator": "ca-eval-lead (T7直接実行)",
  "report_version": "draft_v1",
  "cagr_estimate": {
    "current": "10%",
    "components": {
      "revenue": "8%（OG4%+M&A4%）",
      "op_leverage": "1%（30bp/年のCore EBIT Margin改善）",
      "buyback": "1%（2014-2023平均）"
    },
    "source": "2024年6月IR面談（最新）"
  },
  "claims": [
    {
      "claim_id": 1,
      "title": "ニッチ市場特化型スイッチングコスト（ミッションクリティカル×カスタマイズ）",
      "ca_type": "structural",
      "final_confidence": 70,
      "label": "おおむね納得",
      "cagr_confidence": 70,
      "cagr_label": "おおむね納得",
      "fact_check_status": "verified",
      "rule_summary": {
        "rule01": "PASS（能力・仕組みとして正しく抽出）",
        "rule02": "PASS（名詞属性：スイッチングコスト・カスタマイズ能力）",
        "rule03": "PARTIAL（ニッチTier2内での相対優位は示唆されるが純粋競合比較なし）",
        "rule04": "PARTIAL（市場シェア30~50%・市場規模USD150~400Mの数値あり、競合Churn率比較なし）",
        "rule06": "PASS（構造的要素：スイッチングコストは事業核心）",
        "rule07": "PARTIAL（Tier1との差別化は明確、同ニッチTier2純粋競合との比較なし）",
        "rule08": "PASS（戦略ではなく構造的優位性として記述）",
        "rule09": "N/A（事実誤認なし）",
        "rule10": "PASS（USD1bn以上市場の回避という明示的な不参入判断）",
        "rule11": "PASS（ニッチ計測機器市場の構造×Tier2ポジションの合致、ORLYほどの明確な市場フラグメント分析はなし）",
        "rule12": "SKIP（PoC段階）"
      },
      "patterns_detected": {
        "rejection": [],
        "high_eval": ["III（能力>結果）", "IV（構造的市場ポジション、moderate）"]
      },
      "key_evidence": [
        "市場規模USD150~400M（USD1bn以上は回避）",
        "ニッチ領域シェア30~50%",
        "Tier2ポジション：エマソン・GE・HoneywellへのTier2サプライヤー",
        "Churn Rateほぼゼロ（IR面談確認）",
        "Vitality Index 29%（新製品比率）"
      ],
      "upside_conditions": "ITW・Roper等との具体的スイッチングコスト比較データが得られれば90%に近づける可能性",
      "downside_risks": "ニッチ領域の大型化（USD1bn超買収）によるスイッチングコストの弱体化リスク"
    },
    {
      "claim_id": 6,
      "title": "ニッチトップとしてのPricing Power（価格転嫁力）",
      "ca_type": "structural",
      "final_confidence": 30,
      "label": "あまり納得しない",
      "cagr_confidence": 50,
      "cagr_label": "まあ納得",
      "fact_check_status": "verified",
      "rule_summary": {
        "rule01": "WARN（スプレッド維持は結果の側面が強い）",
        "rule02": "PASS（名詞属性として記述可能）",
        "rule03": "FAIL（ITW等との価格転嫁力比較なし）",
        "rule04": "PARTIAL（スプレッド50~100bpの数値あり、競合比較なし）",
        "rule06": "PARTIAL（Claim #1の派生）",
        "rule07": "FAIL",
        "rule09": "N/A",
        "rule12": "SKIP"
      },
      "patterns_detected": {
        "rejection": ["A（結果を原因と混同、moderate）", "G（純粋競合比較なし、strong）"],
        "high_eval": ["I（定量的裏付け、partial）"]
      },
      "key_evidence": [
        "価格-コストスプレッド通常50~100bp",
        "インフレ5%局面でも100bpスプレッド維持（2021-2022）",
        "2024年スプレッド50bp（正常化に伴う縮小）"
      ],
      "note": "Claim #1（スイッチングコスト）の派生結果として整理が適切。独立した主張としての強度は低い。"
    }
  ],
  "overall_summary": {
    "avg_ca_confidence": 50,
    "avg_cagr_confidence": 61,
    "strongest_claims": [
      {"id": 1, "title": "ニッチ市場特化型スイッチングコスト", "confidence": 70},
      {"id": 2, "title": "規律あるM&A実行能力", "confidence": 70}
    ],
    "weakest_claims": [
      {"id": 6, "title": "Pricing Power（独立主張としては弱い）", "confidence": 30},
      {"id": 7, "title": "ポートフォリオ分散（結果/戦略）", "confidence": 30}
    ],
    "key_insight": "AMETEKの競争優位性の核心はClaim #1（スイッチングコスト）とClaim #2（M&A実行能力）の2本柱。Claim #3-#5はこれらを支える補完的要素。Claim #6-#7は派生結果として整理が適切。",
    "comparison_to_kb3": {
      "closest_analog": "CHD（M&A中心の能力評価。CHD平均50%とAME平均50%が一致）",
      "difference": "AMEはCHDよりM&A規模・体制の定量的裏付けが豊富だが、事業特性上の純粋競合比較が特に困難"
    }
  }
}
```

## フィールド説明

| フィールド | 型 | 必須 | 説明 |
|-----------|-----|------|------|
| `research_id` | string | ✅ | ワークフロー固有ID |
| `ticker` | string | ✅ | 銘柄ティッカーシンボル |
| `company_name` | string | ✅ | 企業正式名称 |
| `generated_at` | string (ISO 8601) | ✅ | 生成時刻 |
| `generator` | string | ✅ | 実行エージェント名 |
| `report_version` | string | ✅ | レポートバージョン: `"draft_v1"` / `"revised_v1"` 等 |
| `cagr_estimate` | object | ✅ | CAGR推定値のサマリー |
| `cagr_estimate.current` | string | ✅ | 最新のCAGR推定値 |
| `cagr_estimate.components` | object | ✅ | CAGR内訳（revenue, op_leverage, buyback 等） |
| `cagr_estimate.source` | string | ✅ | CAGR推定値の出典 |
| `claims` | array[object] | ✅ | 評価済み主張の一覧（claims.jsonの情報をT5・T6の結果で更新したもの） |
| `claims[].claim_id` | integer | ✅ | 主張ID |
| `claims[].title` | string | ✅ | 主張タイトル |
| `claims[].ca_type` | string | ✅ | 競争優位性種別 |
| `claims[].final_confidence` | integer | ✅ | 最終CA確信度スコア（10/30/50/70/90の5段階） |
| `claims[].label` | string | ✅ | CA確信度スコアに対応するラベル |
| `claims[].cagr_confidence` | integer | ✅ | CAGR確信度スコア（10/30/50/70/90の5段階） |
| `claims[].cagr_label` | string | ✅ | CAGR確信度スコアに対応するラベル |
| `claims[].fact_check_status` | string | ✅ | ファクトチェック結果: `"verified"` / `"verified_with_caveat"` / `"unverifiable"` / `"contradicted"` |
| `claims[].rule_summary` | object | ✅ | KB1ルール別の評価サマリー（文字列値）。各キーは `"{rule番号}"` 形式、値は `"{RESULT}（{説明}）"` 形式 |
| `claims[].patterns_detected` | object | ✅ | 検出されたパターンのサマリー |
| `claims[].patterns_detected.rejection` | array[string] | ✅ | 検出された却下パターン（例: `"A（結果を原因と混同、moderate）"`） |
| `claims[].patterns_detected.high_eval` | array[string] | ✅ | 検出された高評価パターン（例: `"III（能力>結果）"`） |
| `claims[].key_evidence` | array[string] | ✅ | 主張を支持する主要な証拠一覧（3〜6件） |
| `claims[].upside_conditions` | string | - | 確信度が向上する条件（`final_confidence` が90未満の場合） |
| `claims[].downside_risks` | string | - | 確信度が低下するリスク |
| `claims[].note` | string | - | 追加の注記（独立性の低い主張等） |
| `overall_summary` | object | ✅ | 評価結果の全体サマリー |
| `overall_summary.avg_ca_confidence` | integer | ✅ | 全主張のCA確信度の平均 |
| `overall_summary.avg_cagr_confidence` | integer | ✅ | 全主張のCAGR確信度の平均 |
| `overall_summary.strongest_claims` | array[object] | ✅ | 最も強い主張一覧（id, title, confidence を含む） |
| `overall_summary.weakest_claims` | array[object] | ✅ | 最も弱い主張一覧（id, title, confidence を含む） |
| `overall_summary.key_insight` | string | ✅ | 評価の核心的洞察（2〜3文） |
| `overall_summary.comparison_to_kb3` | object | ✅ | KB3の類似事例との比較 |
| `overall_summary.comparison_to_kb3.closest_analog` | string | ✅ | 最も類似したKB3事例と根拠 |
| `overall_summary.comparison_to_kb3.difference` | string | ✅ | 類似事例との主要な差異 |

## バリデーションルール

- `claims[].rule_summary` の各値は文字列形式で記述すること（例: `"PASS（能力・仕組みとして正しく抽出）"`）。オブジェクト形式は使用しない
- `claims[].final_confidence` と `claims[].cagr_confidence` は 10/30/50/70/90 の5段階のいずれかであること
- `claims[].fact_check_status` は fact-check.json の `fact_checks[].overall_status` と一致すること
- `overall_summary.strongest_claims` と `overall_summary.weakest_claims` の各オブジェクトは `id` / `title` / `confidence` の3フィールドを含むこと
- `overall_summary.avg_ca_confidence` は `claims[].final_confidence` の平均値と一致すること（小数点以下は切り捨て）
- `report_version` が `"draft_v1"` の場合、T8完了後に `"revised_v1"` に更新されること（revised-report-{TICKER}.mdとは別ファイルだが、バージョン管理は重要）
