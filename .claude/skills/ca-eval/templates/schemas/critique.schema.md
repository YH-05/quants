# critique.schema.md スキーマ

> 生成タスク: T8 | 生成エージェント: ca-eval-lead（T8直接実行）
> 読み込み先: T8後半（revised-report-{TICKER}.md生成時に修正事項を参照）、T9_accuracy（overall_assessmentのKB整合性を参照）

## JSONスキーマ

```json
{
  "research_id": "CA_eval_20260218-1454_AME",
  "ticker": "AME",
  "critique_timestamp": "2026-02-18T15:45:00Z",
  "overall_assessment": {
    "kb_alignment": "moderate",
    "reasoning_quality": "moderate",
    "critical_issues": 2,
    "minor_issues": 5
  },
  "claim_critiques": [
    {
      "claim_id": 1,
      "critique_type": "reasoning_gap",
      "severity": "minor",
      "issue": "「Churn Rateほぼゼロ」という記述をconfidence 70%の支持証拠として使用しているが、これはIR面談の定性コメントであり（「数値は提示されなかったが」との注記あり）、開示データで検証可能な事実ではない。パターンII（直接的CAGR接続）の条件「開示データで検証可能」を満たしておらず、CAGR接続70%は若干楽観的。",
      "kb_reference": "KB2パターンII「開示データで検証可能な場合に最高評価」。KB3 COST顧客粘着力（90%）では「会員更新率・比率が適宜開示されており検証可能」が90%の根拠。",
      "suggested_action": "annotation_only",
      "suggested_value": null,
      "reasoning": "CA confidence 70%は適切。ただし「Churn Rateほぼゼろ」はIRの定性コメントであることをレポートに明記し、CAGR接続70%に「検証可能データが整えば上振れの余地」という注記を追加すべき。confidenceは変更しない。"
    },
    {
      "claim_id": 2,
      "critique_type": "reasoning_gap",
      "severity": "critical",
      "issue": "M&A大型化リスク（2024Q2 CEOの「USD1bn以上の大型案件を買うことになるだろう」というコメント）を「懸念点」として記述しているが、CAGR confidence 70%には一切反映されていない。KB3では「ネガティブケースによる裏付け（ルール10）」を高評価要因としているが、このケースは「従来の不参入判断（ルール10の正方向）」が崩れる「ルール10の逆方向」として機能すべきであり、CAGR接続の確度を下げる要因として明示的に扱うべき。",
      "kb_reference": "KB1ルール10「断念例が能力の証明」。大型化傾向はこの断念能力の喪失を示唆する逆パターン。KB3 CHD#1（70%）では断念例の定量性が明示されていた。",
      "suggested_action": "confidence_adjustment",
      "suggested_value": 60,
      "reasoning": "CAGR confidence を70%から実質的に「70%だが大型化リスクあり」として扱うべき。70%を維持しつつ「大型化リスクが顕在化した場合は50%に低下」という条件付きアノテーションを追加する形が適切。revised-report-{TICKER}.mdで「[⬇️ T8修正]」として明示。"
    },
    {
      "claim_id": 2,
      "critique_type": "kb_misalignment",
      "severity": "minor",
      "issue": "「IRR15%」の達成を選定能力の証拠として使用しているが、実際のIRR達成率（何%の案件がIRR15%を達成したか）のデータが示されていない。KB3 CHD#1では「断念例の具体的記述」が70%の根拠だったが、AMEは基準の存在（IRR15%）のみで達成実績が未確認。",
      "kb_reference": "KB3 CHD#1「人員増強、バリュエーションや収益成長持続性による買収断念例などで補足されており、買収ターゲットの選定能力には納得感あり」。基準の存在と達成実績は別。",
      "suggested_action": "annotation_only",
      "suggested_value": null,
      "reasoning": "CA confidence 70%は引き続き適切。ただし「IRR15%の達成率不明」という限界を明記すべき。"
    },
    {
      "claim_id": 4,
      "critique_type": "reasoning_gap",
      "severity": "minor",
      "issue": "直販→顧客ニーズ→M&Aリスト→クロスセル→OPM改善というループは因果チェーンが4ステップ以上あり、パターンC（因果関係の飛躍）に近い構造。CAGR confidence 50%はこのリスクを適切に反映していない。",
      "kb_reference": "KB2パターンC「3段階以上の推論チェーンで各段階の裏付けがない因果関係を主張するパターン」。KB3 COST思いやり経営CAGR（20%）は従業員満足→顧客サービス→既存店が飛躍とされた。",
      "suggested_action": "annotation_only",
      "suggested_value": null,
      "reasoning": "CAGR confidence 50%は適切。ただし「直販ループの4ステップはパターンCへの警戒が必要」という明示的な批判を追加すべき。"
    },
    {
      "claim_id": 5,
      "critique_type": "kb_misalignment",
      "severity": "minor",
      "issue": "「分散型組織はITWが先行者（80/20戦略で有名なコングロマリット企業）」という事実がアナリストレポート自身に記載されているにもかかわらず、なぜAMEの分散型組織がITWより優れているか（あるいは異なるのか）の議論が欠如している。",
      "kb_reference": "KB3 LLY#6「グローバル医療機関ネットワーク：メガファーマなら誰でも持っている→30%」。アナリストレポート自身が「ITWに類似」と述べている点でルール3が厳密に適用されるべきか要検討。",
      "suggested_action": "annotation_only",
      "suggested_value": null,
      "reasoning": "AMEはITWと類似の分散型組織を持つが、計測機器×ニッチTier2という事業特性に特化している点が差別化。50%は維持するが、「ITW類似」の指摘に対する反論を明記すべき。"
    },
    {
      "claim_id": 6,
      "critique_type": "reasoning_gap",
      "severity": "minor",
      "issue": "スプレッドの縮小トレンド（2021-2022年の100bp→2024年の50bp）が「インフレ正常化に伴う減少」として軽く触れられているが、これが「Pricing Powerの弱体化」なのか「環境変化への正常化」なのかの評価が不十分。",
      "kb_reference": "KB2パターンE「トレンドの方向は正しいか（改善/悪化/横ばい）」の確認要件。",
      "suggested_action": "annotation_only",
      "suggested_value": null,
      "reasoning": "30%は適切。ただしスプレッド縮小（100bp→50bp）の解釈について明記すべき。"
    },
    {
      "claim_id": 1,
      "critique_type": "kb_misalignment",
      "severity": "minor",
      "issue": "KB3 ORLY#2（90%）は「フラグメント市場×規模・密度×ネットワーク」の構造合致が90%の根拠だが、AMEのClaim #1（70%）では市場構造（ニッチ計測機器市場のフラグメント度）の定量的論拠が不足している。",
      "kb_reference": "KB2パターンIV「構造的な市場ポジション：市場構造の分析が明確であること」。KB3 ORLY#2では「出店可能エリアで飽和未到達」というフラグメント度の根拠が明示。",
      "suggested_action": "annotation_only",
      "suggested_value": null,
      "reasoning": "70%は適切。フラグメント度のデータが得られれば90%の可能性があることをレポートに明記し、上振れ条件として記述すべき。"
    }
  ],
  "systematic_issues": [
    {
      "pattern": "純粋競合比較の全面的欠如（ルール7・パターンG）",
      "affected_claims": [1, 2, 3, 4, 5],
      "description": "全7主張中5主張でITW・Roper Technologies・Fortive等との純粋競合比較が欠如。これはAMEのビジネスモデル特性（多数のニッチ領域で異なるプレイヤーと競合）により純粋競合の特定が困難なためと考えられるが、KB3で重視されるルール7が全体的に不満足となっている。",
      "kb_lesson": "KB3 ORLY#1（AZO対比でのDIFM補充頻度→70%）：具体的競合名と比較軸の明示が評価を高める。AMEでは例えばITWとのM&A後ROIC比較（Claim #2）やFortiveとのCapex比較（Claim #3）が有効。"
    },
    {
      "pattern": "ルール10（ネガティブケース）の逆方向リスクへの対処不足",
      "affected_claims": [2],
      "description": "Claim #2では買収断念例（ルール10の正方向）を適切に評価しているが、大型化傾向（ルール10の逆方向：従来の断念能力の喪失）のCAGR confidenceへの反映が不十分。",
      "kb_lesson": "KB3 CHD#1では断念例の存在が70%の根拠。その逆（断念しない傾向の強まり）はCAGR接続の確度を下げる要因として明示的に扱うべき。"
    }
  ]
}
```

## フィールド説明

| フィールド | 型 | 必須 | 説明 |
|-----------|-----|------|------|
| `research_id` | string | ✅ | ワークフロー固有ID |
| `ticker` | string | ✅ | 銘柄ティッカーシンボル |
| `critique_timestamp` | string (ISO 8601) | ✅ | 批評実行時刻 |
| `overall_assessment` | object | ✅ | 批評の全体評価 |
| `overall_assessment.kb_alignment` | string | ✅ | KBとの整合性評価: `"high"` / `"moderate"` / `"low"` |
| `overall_assessment.reasoning_quality` | string | ✅ | 推論品質評価: `"high"` / `"moderate"` / `"low"` |
| `overall_assessment.critical_issues` | integer | ✅ | criticalレベルの問題件数 |
| `overall_assessment.minor_issues` | integer | ✅ | minorレベルの問題件数 |
| `claim_critiques` | array[object] | ✅ | 主張別の批評一覧（1つの主張に複数の批評が存在する場合あり） |
| `claim_critiques[].claim_id` | integer | ✅ | 対応する主張ID |
| `claim_critiques[].critique_type` | string | ✅ | 批評種別: `"reasoning_gap"` / `"kb_misalignment"` / `"data_concern"` / `"logic_error"` |
| `claim_critiques[].severity` | string | ✅ | 深刻度: `"critical"` / `"minor"` |
| `claim_critiques[].issue` | string | ✅ | 問題の詳細説明（具体的なテキスト引用を含む） |
| `claim_critiques[].kb_reference` | string | ✅ | 関連するKBのルール・パターン・事例への参照 |
| `claim_critiques[].suggested_action` | string | ✅ | 推奨アクション: `"annotation_only"` / `"confidence_adjustment"` / `"claim_revision"` |
| `claim_critiques[].suggested_value` | integer \| null | ✅ | 推奨する新しい確信度スコア（`confidence_adjustment` 時のみ。非推奨変更の場合は `null`） |
| `claim_critiques[].reasoning` | string | ✅ | 推奨アクションの根拠説明 |
| `systematic_issues` | array[object] | ✅ | 個別主張に限定されない全体的な問題の一覧 |
| `systematic_issues[].pattern` | string | ✅ | 問題パターンの名称 |
| `systematic_issues[].affected_claims` | array[integer] | ✅ | 影響を受ける主張のIDリスト |
| `systematic_issues[].description` | string | ✅ | 問題の詳細説明 |
| `systematic_issues[].kb_lesson` | string | ✅ | KBの教訓と具体的な改善示唆 |

## バリデーションルール

- `claim_critiques[].critique_type` は `"reasoning_gap"` / `"kb_misalignment"` / `"data_concern"` / `"logic_error"` のいずれかであること
- `claim_critiques[].severity` は `"critical"` / `"minor"` のいずれかであること
- `claim_critiques[].suggested_action` が `"confidence_adjustment"` の場合、`suggested_value` は 10/30/50/70/90 の5段階のいずれかであること（`null` は不可）
- `claim_critiques[].suggested_action` が `"annotation_only"` または `"claim_revision"` の場合、`suggested_value` は `null` であること
- `overall_assessment.critical_issues` は `claim_critiques[].severity: "critical"` の件数と一致すること
- `overall_assessment.minor_issues` は `claim_critiques[].severity: "minor"` の件数と一致すること
- `systematic_issues[].affected_claims` の各IDは claims.json に存在する claim_id であること
- `claim_critiques[].kb_reference` には具体的なKBルールID・パターンID・事例IDを含むこと（例: `"KB2パターンII"`, `"KB3 CHD#1"`, `"KB1ルール10"`）
