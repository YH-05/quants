# claims.schema.md スキーマ

> 生成タスク: T4 | 生成エージェント: ca-claim-extractor
> 読み込み先: T5_fact_checker（factual_claimsを照合）、T6_pattern_verifier（rule_applicationsを参照）、T7_report_generator（主張一覧とconfidenceを使用）

## JSONスキーマ

```json
{
  "research_id": "CA_eval_20260218-1454_AME",
  "ticker": "AME",
  "company_name": "AMETEK, Inc.",
  "extracted_at": "2026-02-18T15:10:00Z",
  "extractor": "ca-eval-lead (T4直接実行)",
  "kb_applied": {
    "kb1_rules": ["rule01", "rule02", "rule04", "rule06", "rule07", "rule08", "rule10", "rule11"],
    "kb3_references": ["CHD#1", "CHD#7", "ORLY#2", "ORLY#5", "COST#1", "MNST#1"],
    "dogma": "analyst/Competitive_Advantage/analyst_YK/dogma/dogma_v1.0.md"
  },
  "cagr_estimate": {
    "current": "10%（2024年6月面談後）",
    "breakdown": {
      "revenue": "8%（OG4%+M&A4%）",
      "op_leverage": "1%（30bp/年のCore EBIT Margin改善）",
      "buyback": "1%（2014-2023平均）"
    }
  },
  "claims": [
    {
      "claim_id": 1,
      "title": "ニッチ市場特化型スイッチングコスト（ミッションクリティカル×カスタマイズ）",
      "ca_type": "structural",
      "description": "大手企業参入リスクの低いニッチ領域（市場規模USD150~400M）で市場シェア30~50%を確保。Mission Critical且つカスタマイズした財に特化することにより、顧客は一度使用するとスイッチするインセンティブが起きにくい高いスイッチングコストを構造的に有している。",
      "source_text": "ニッチトップ戦略を展開。…ミッションクリティカルな財（High Cost of Failure）、ニッチトップ（市場シェア30~50%）、顧客ニーズに合わせたカスタマイズ製品、などの特徴を持つ事業を有しており、顧客は一度使用するとスイッチするインセンティブが起きにくい。",
      "factual_claims": [
        "ニッチ領域の市場規模はUSD150~400M（USD1bn以上の大規模市場は回避）",
        "各ニッチ領域での市場シェア30~50%",
        "Tier2サプライヤーとして大手（エマソン、GE、Honeywell、Lockheed Martin等）と直接競合しない",
        "ミッションクリティカルな財：規制・安全性・品質基準から正確な計測・分析が求められ、誤りの影響が甚大な領域"
      ],
      "cagr_connected": true,
      "cagr_mechanism": "スイッチングコスト→高い顧客継続率（Churn Rateほぼゼロ）→OG安定（4%/年）→M&A成長の基盤。Vitality Index 29%が新製品での顧客維持を示す。",
      "rule_applications": {
        "rule01_capability_not_result": {
          "result": "PASS",
          "comment": "「スイッチングコスト」「ミッションクリティカル性」「カスタマイズ能力」はいずれも能力・仕組み（名詞）として正しく表現されている。市場シェア30~50%は結果だが、主張の核心はそれを生み出す構造的特性にある。"
        },
        "rule02_noun_attribute": {
          "result": "PASS",
          "comment": "スイッチングコスト、ミッションクリティカル性、カスタマイズ能力—いずれも名詞で表現される属性。"
        },
        "rule04_quantitative_evidence": {
          "result": "PARTIAL",
          "comment": "市場シェア30~50%、市場規模USD150~400Mという定量的裏付けあり。ただし競合他社のChurn Rateや顧客更新率との具体的比較数値は不明。"
        },
        "rule06_structural_vs_complementary": {
          "result": "PASS",
          "comment": "スイッチングコストは事業モデルの核心。ミッションクリティカル性とカスタマイズは補完的要素ではなく構造的要素。"
        },
        "rule07_pure_competitor_differentiation": {
          "result": "PARTIAL",
          "comment": "Tier1企業（エマソン、GE）との差別化は示されているが、同じニッチ領域の純粋競合（他のTier2ニッチプレイヤー）に対する具体的差別化は不明確。"
        },
        "rule08_strategy_not_advantage": {
          "result": "PASS",
          "comment": "「ニッチトップ戦略」という表現があるが、主張の核心は戦略ではなく「スイッチングコスト」という構造的優位性。"
        },
        "rule10_negative_case": {
          "result": "PASS",
          "comment": "USD1bn以上の大規模市場を回避するという明示的な「参入しない」判断がある。"
        },
        "rule11_industry_structure_fit": {
          "result": "PASS",
          "comment": "ニッチ計測・プロセス機器市場は大手企業が参入しにくい構造（市場規模が小さい）であり、AMETEKのTier2ポジションがその構造に合致。"
        }
      },
      "confidence": {
        "ca_score": 70,
        "label": "おおむね納得",
        "reasoning": "スイッチングコストという構造的優位性は実在し、ミッションクリティカル×カスタマイズという裏付けも明確。ただし純粋競合との具体的差別化（ルール7）が不明で、90%には届かない。",
        "kb3_calibration": "CHD#1類似（能力×定量的裏付け部分あり→70%）"
      },
      "cagr_confidence": {
        "score": 70,
        "label": "おおむね納得",
        "reasoning": "スイッチングコスト→低Churn→OG4%→CAGR10%のメカニズムは1-2ステップで直接的。Vitality Index 29%という検証可能指標あり。ただしOG4%の数値根拠（Churn率の定量開示なし）は不完全。"
      }
    }
  ],
  "rule9_gatekeeping": {
    "applied": false,
    "reason": "ファクトチェック（T5）によるcontradicted事実確認後に適用判断。現時点では事実誤認は未検出。"
  },
  "summary": {
    "total_claims": 7,
    "confidence_distribution": {
      "90_very_convinced": 0,
      "70_mostly_convinced": 2,
      "50_somewhat_convinced": 3,
      "30_not_convinced": 2,
      "10_rejected": 0
    },
    "avg_ca_confidence": 50,
    "claims_with_cagr_connection": 6,
    "avg_cagr_confidence": 61,
    "key_strengths": [
      "ニッチ市場×ミッションクリティカル×スイッチングコストは構造的優位性として実在（Claim #1: 70%）",
      "M&A実行能力は定量的裏付け豊富（Claim #2: 70%）",
      "Rule10（ネガティブケース）がClaim #1・#2で機能"
    ],
    "key_weaknesses": [
      "純粋競合（ITW、Roper等）との具体的差別化比較が全体的に不足（ルール7）",
      "Claim #6（Pricing Power）・Claim #7（分散）は結果/戦略に近く独立した優位性として弱い"
    ],
    "poc_skipped": ["rule12_report_type_distinction"]
  }
}
```

## フィールド説明

| フィールド | 型 | 必須 | 説明 |
|-----------|-----|------|------|
| `research_id` | string | ✅ | ワークフロー固有ID |
| `ticker` | string | ✅ | 銘柄ティッカーシンボル |
| `company_name` | string | ✅ | 企業正式名称 |
| `extracted_at` | string (ISO 8601) | ✅ | 主張抽出実行時刻 |
| `extractor` | string | ✅ | 実行エージェント名 |
| `kb_applied` | object | ✅ | 適用したナレッジベースの参照情報 |
| `kb_applied.kb1_rules` | array[string] | ✅ | 適用したKB1ルールID一覧 |
| `kb_applied.kb3_references` | array[string] | ✅ | 参照したKB3の類似事例一覧（形式: `"{TICKER}#{N}"`） |
| `kb_applied.dogma` | string | ✅ | 参照したdogma.mdファイルパス |
| `cagr_estimate` | object | ✅ | 現時点のCAGR推定値 |
| `cagr_estimate.current` | string | ✅ | CAGR推定値（最新） |
| `cagr_estimate.breakdown` | object | ✅ | CAGR内訳（revenue, op_leverage, buyback 等） |
| `claims` | array[object] | ✅ | 競争優位性主張の一覧（5〜15件） |
| `claims[].claim_id` | integer | ✅ | 主張ID（1から連番） |
| `claims[].title` | string | ✅ | 主張タイトル（50文字以内の簡潔な名称） |
| `claims[].ca_type` | string | ✅ | 競争優位性種別: `"structural"` / `"operational"` / `"financial"` |
| `claims[].description` | string | ✅ | 主張の詳細説明（200文字以内） |
| `claims[].source_text` | string | ✅ | アナリストレポートからの引用テキスト |
| `claims[].factual_claims` | array[string] | ✅ | 事実的主張のリスト（T5でファクトチェックされる対象） |
| `claims[].cagr_connected` | boolean | ✅ | CAGRへの寄与フラグ |
| `claims[].cagr_mechanism` | string | ✅ | 主張からCAGRへの接続メカニズムの説明（`cagr_connected: true` の場合必須） |
| `claims[].rule_applications` | object | ✅ | KB1ルール別の適用結果（オブジェクト形式。旧 `rule_evaluation.results[]` 配列形式は廃止） |
| `claims[].rule_applications.{rule_id}.result` | string | ✅ | ルール適用結果: `"PASS"` / `"PARTIAL"` / `"PARTIAL_PASS"` / `"WARN"` / `"FAIL"` / `"N/A"` |
| `claims[].rule_applications.{rule_id}.comment` | string | ✅ | 適用結果の根拠説明 |
| `claims[].rule_applications.{rule_id}.flag` | string | - | 追加フラグ（`"partially_result"` / `"primarily_result"` 等） |
| `claims[].confidence` | object | ✅ | CA確信度の評価 |
| `claims[].confidence.ca_score` | integer | ✅ | CA確信度スコア（10/30/50/70/90の5段階） |
| `claims[].confidence.label` | string | ✅ | スコアに対応するラベル |
| `claims[].confidence.reasoning` | string | ✅ | スコアの根拠説明（KB3キャリブレーションを含む） |
| `claims[].confidence.kb3_calibration` | string | ✅ | KB3の最も類似した事例とスコアとの比較 |
| `claims[].cagr_confidence` | object | ✅ | CAGR確信度の評価 |
| `claims[].cagr_confidence.score` | integer | ✅ | CAGR確信度スコア（10/30/50/70/90の5段階） |
| `claims[].cagr_confidence.label` | string | ✅ | スコアに対応するラベル |
| `claims[].cagr_confidence.reasoning` | string | ✅ | スコアの根拠説明 |
| `rule9_gatekeeping` | object | ✅ | ルール9（事実誤認即却下）の適用状況 |
| `rule9_gatekeeping.applied` | boolean | ✅ | ルール9を適用したかどうか |
| `rule9_gatekeeping.reason` | string | ✅ | 適用/非適用の理由 |
| `summary` | object | ✅ | 主張抽出結果のサマリー |
| `summary.total_claims` | integer | ✅ | 抽出された主張の総数 |
| `summary.confidence_distribution` | object | ✅ | 確信度スコア別の主張件数 |
| `summary.avg_ca_confidence` | number | ✅ | CA確信度の平均スコア |
| `summary.claims_with_cagr_connection` | integer | ✅ | CAGRと関連する主張の件数 |
| `summary.avg_cagr_confidence` | number | ✅ | CAGR確信度の平均スコア |
| `summary.key_strengths` | array[string] | ✅ | 評価の強みポイント一覧 |
| `summary.key_weaknesses` | array[string] | ✅ | 評価の弱点ポイント一覧 |
| `summary.poc_skipped` | array[string] | - | PoCのためスキップしたルール一覧 |

## バリデーションルール

- `claims[].confidence.ca_score` は 10/30/50/70/90 の5段階のいずれかであること
- `claims[].cagr_confidence.score` は 10/30/50/70/90 の5段階のいずれかであること
- `claims[].rule_applications` はオブジェクト形式で記述すること（旧来の `rule_evaluation.results[]` 配列形式は使用しない）
- `claims[].rule_applications.{rule_id}` のキー形式は `"{rule番号}_{rule名}"` とする（例: `rule01_capability_not_result`）
- `claims[].cagr_connected` が `true` の場合、`claims[].cagr_mechanism` が必須
- `summary.confidence_distribution` のキーは `"{スコア}_{ラベル}"` 形式（例: `"70_mostly_convinced"`）
- `summary.total_claims` は `claims` 配列の実際の要素数と一致すること
- 主張は5件以上15件以下を目安とすること
- `claims` 配列が空（0件）の場合は `processing_error` フィールドを必須とし、その理由（レポート言語不対応、抽出失敗等）を記録すること。`processing_error` が存在する場合でも `ticker`、`report_source`、`extraction_metadata` は必須
