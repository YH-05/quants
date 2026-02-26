# CA-Eval 全12銘柄バッチ実行計画（dogma v1.0対応）

## Context

dogma.md を v0.9 → v1.0 に更新し、KB1/KB2/KB3 も同期修正済み。主な変更:
- 「定量はWANT、説明力がMUST」への哲学転換
- 因果関係パターンC/D/Fの再定義
- CAGR掛け算原則の追加
- ブランド評価フレームワーク（タイプ5/6追加）

これらの変更を反映した ca-eval を全12銘柄に対して実行し、アナリストYへのフィードバック用レポートを生成する。

## 対象銘柄（12銘柄）

### 既存評価あり（9銘柄）— v1.0で再実行
| # | ティッカー | 市場 | 既存結果 |
|---|-----------|------|---------|
| 1 | AME US | 米国 | `CA_eval_20260220-0845_AME` |
| 2 | ATCOA SS | **スウェーデン** | `CA_eval_20260220-0845_ATCOA` |
| 3 | CPRT US | 米国 | `CA_eval_20260220-0932_CPRT` |
| 4 | LLY US | 米国 | `CA_eval_20260220-1411_LLY` |
| 5 | MCO US | 米国 | `CA_eval_20260220-0931_MCO` |
| 6 | MSFT US | 米国 | `CA_eval_20260220-1411_MSFT` |
| 7 | NFLX | 米国 | `CA_eval_20260220-0931_NFLX` |
| 8 | POOL | 米国 | `CA_eval_20260220-1411_POOL` |
| 9 | VRSK | 米国 | `CA_eval_20260220-1411_VRSK` |

### 未評価（3銘柄）— 新規実行
| # | ティッカー | 市場 | レポート |
|---|-----------|------|---------|
| 10 | LRCS US | 米国 | `analyst/raw/LRCS US.md` |
| 11 | MNST US | 米国 | `analyst/raw/MNST US.md` |
| 12 | ORLY | 米国 | `analyst/raw/ORLY.md` |

> MNST, ORLY は Phase 2 検証データ（`analyst/phase2_KY/`）があるため、T9精度検証がフルモードで実行される。

## 再実行の理由

dogma v1.0 の変更は評価哲学の根幹に影響する:
- パターンD「説明力不足」の再定義により、定性的主張の評価基準が変化
- パターンC「因果関係の混同・拡大解釈」の拡張により、検出範囲が変化
- rule04「説明力がMUST」により、確信度スケールの判定基準が変化

全9銘柄を v1.0 KB で再実行し、アナリストYに一貫した基準での評価セットを提出する。

## 非US銘柄の対応（ATCOA SS）

### 現状
前回実行時、T1（SEC Filings収集）は `data_source: "analyst_report_extracted"` にフォールバック済み。アナリストレポートからの参照値のみで sec-data.json を構成。

### 改善案: IR資料からのデータ補強

Atlas Copco IR ページ（https://www.atlascopcogroup.com/en/investor-relations）から以下を事前取得し、sec-data.json を手動で補強:

| データ | ソース | SEC相当 |
|--------|--------|---------|
| Annual Report 2024 (英語PDF) | IR > Reports | 10-K |
| Q2 2025 Interim Report | IR > Reports | 10-Q |
| Segment breakdown (4事業) | Annual Report内 | Segment Data |
| Key financial metrics | IR > Key Figures | Company Facts |

### 実装手順
1. ブラウザ（playwright or manual）でAtlas Copco IR資料を取得
2. 財務データを sec-data.json のスキーマに合わせて手動補強
3. `data_source: "ir_filing_extracted"`, `data_limitations` を更新
4. 補強済み sec-data.json を `01_data_collection/` に配置した状態で ca-eval を実行（T1はスキップ or 既存ファイルを使用）

## 実行計画

### Phase 1: ATCOA IR資料の事前準備

1. Atlas Copco IR ページから Annual Report 2024 と Q2 2025 Interim Report の情報を取得
2. 既存の `CA_eval_20260220-0845_ATCOA/01_data_collection/sec-data.json` をベースに補強
3. 補強版 sec-data.json を `analyst/Competitive_Advantage/ATCOA_SS/sec-data-enriched.json` として保存（再利用可能に）

### Phase 2: ca-eval バッチ実行（3 Wave）

並列度は2（同時に2銘柄を `/ca-eval` で実行）。

**Wave 1: Phase 2検証データあり銘柄（精度検証フルモード）**
- Run 1: MNST, ORLY（新規、Phase 2データあり）
- Run 2: LLY（再実行、Phase 2データあり）

**Wave 2: 主要US銘柄**
- Run 3: AME, CPRT
- Run 4: MCO, NFLX
- Run 5: MSFT, POOL

**Wave 3: 残り**
- Run 6: VRSK, LRCS（新規）
- Run 7: ATCOA（補強sec-data使用）

### Phase 3: 結果パッケージング

1. 全12銘柄の `revised-report.md` を `analyst/Competitive_Advantage/ca-eval-v1.0-batch/` に集約
2. 銘柄別サマリー一覧表（ティッカー/主張数/平均確信度/v0.9からの変化点）を作成
3. v1.0変更の影響分析メモ（どの変更がどの銘柄の評価に影響したか）

## 重要ファイル

| ファイル | 用途 |
|---------|------|
| `analyst/Competitive_Advantage/analyst_YK/dogma.md` | v1.0 dogma（全評価の基盤） |
| `analyst/Competitive_Advantage/analyst_YK/kb1_rules/*.md` | 8ルール |
| `analyst/Competitive_Advantage/analyst_YK/kb2_patterns/*.md` | 12パターン（C/D/F更新済み） |
| `analyst/Competitive_Advantage/analyst_YK/kb3_fewshot/*.md` | 5 few-shot例 |
| `.claude/skills/ca-eval/SKILL.md` | ワークフロー定義 |
| `.claude/agents/deep-research/ca-eval-lead.md` | Agent Teamsリーダー |
| `analyst/phase2_KY/` | CHD/COST/LLY/MNST/ORLY の検証データ |

## 検証方法

1. **各銘柄**: `04_output/revised-report.md` と `structured.json` の存在確認
2. **Phase 2対象銘柄**: `accuracy-report.json` の平均乖離 ≤ 15% を確認
3. **ATCOA**: sec-data.json が `ir_filing_extracted` ソースで補強されていることを確認
4. **v1.0一貫性**: 全レポートで dogma v1.0 の用語（「説明力がMUST」等）が正しく反映されていることを目視確認

## アナリストY提出物

1. 12銘柄の `revised-report.md`（最終版レポート）
2. 銘柄別サマリー一覧（一覧性のある比較表）
3. dogma v1.0 変更影響メモ
4. フィードバック依頼事項:
   - 各銘柄の確信度は妥当か
   - v1.0変更により改善された評価 / 悪化した評価はあるか
   - ATCOA（非US）のデータ品質は十分か
