# 議論メモ: Neo4j KG品質改善バックフィル（Phase 2）

**日付**: 2026-03-19
**議論ID**: disc-2026-03-19-kg-quality-backfill
**前回セッション**: disc-2026-03-19-kg-quality-improvement（C+ → B）
**参加**: ユーザー + AI

## 背景・コンテキスト

前回セッションでKG品質をC+→Bに改善した後、ユーザーから「全体的にバックフィルを進めて」との指示を受け、残存する品質問題の系統的な改善を実施した。

## 改善前の状態（Phase 1完了時点）

| 指標 | 値 |
|------|-----|
| 総ノード | 1,180 |
| 総リレーション | 2,975 |
| 密度比 | 2.58 |
| 総合スコア | B+ |

主要問題:
- PerformanceEvidence の33%がMethod未接続（27件orphan）
- Claim の8.5%にsentiment欠損（16件）
- Meta Topic 7件が完全孤立
- Anomaly の50%にtype/persistence欠損
- PerformanceEvidence 7件にbenchmark欠損

## 6フェーズの改善実施

### Phase 1: PerformanceEvidence→Method 接続補完

- evidence_idのパターンマッチ（`perf-{method}-{metric}-{hash}`）
- Claim→Source→Method パスからの候補特定
- Method: Trend Following を新規作成（arxiv-1404.3274用）
- **結果: 27/27件 全て接続完了**

### Phase 2: Meta Topic→Source TAGGED 接続

- Source.category → Meta Topic のマッピング（6カテゴリ）
- category NULL の Source にはtitle/abstractキーワードマッチ
- 細分化Topic → Meta Topic の SUBTOPIC_OF 接続
- **結果: TAGGED +271件、SUBTOPIC_OF +27件、孤立Topic 0件**

### Phase 3: Claim sentiment バックフィル

- claim_type（analysis/benchmark_result/risk_assessment）とcontent内容から推定
- analysis: positive(4)/negative(2)/mixed(2)
- benchmark_result: positive(1)/negative(3)
- risk_assessment: negative(4)
- **結果: 16/16件 全て設定完了**

### Phase 4: PerformanceEvidence value/benchmark 補完

- 数値化可能なもの（ROC-AUC 0.675等）にvalue設定
- 定性的エビデンスに `is_qualitative=true` フラグ追加
- metric_nameパターンからbenchmark推定（Sharpe→market benchmark等）
- **結果: benchmark 7件全て補完、value 1件設定 + 4件分類済**

### Phase 5: Anomaly/Method/MarketRegime 接続強化

- Anomaly 5件の type/persistence 欠損を補完（→全10件完全）
- Method→Anomaly EXPLOITS +8件（Trend Following, LLM earnings等）
- Method→MarketRegime EFFECTIVE_IN +8件（Trend Following→Bull/Bear/High-Vol等）
- 孤立Source 1件も Phase 2 で自動解消

### Phase 6: 最終検証

| 指標 | Before | After | 変化 |
|------|--------|-------|------|
| 総ノード | 1,180 | 1,181 | +1 |
| 総リレーション | 2,975 | 3,290 | **+315 (+10.6%)** |
| 密度比 | 2.58 | 2.81 | **+8.9%** |
| 孤立ノード | 1 | 0 | 完全解消 |
| PE orphan | 27 (33%) | 0 (0%) | 完全解消 |
| Claim sentiment欠損 | 16 (8.5%) | 0 (0%) | 完全解消 |
| 孤立Topic | 7 | 0 | 完全解消 |
| Anomaly type欠損 | 5 (50%) | 0 (0%) | 完全解消 |
| **総合スコア** | **B+** | **A-** | |

## 決定事項

| ID | 内容 | コンテキスト |
|----|------|------------|
| dec-2026-03-19-025 | PE→Method接続はevidence_idパターンマッチ方式 | 命名規則の一貫性を活用 |
| dec-2026-03-19-026 | Meta Topicは二重接続方式（TAGGED + SUBTOPIC_OF） | 情報空間の立体化 |
| dec-2026-03-19-027 | 定性的PEには is_qualitative フラグで分類管理 | 定量/定性の分離クエリを可能に |
| dec-2026-03-19-028 | 残課題はワークフロー依存のため別途対応 | 外部API/実行依存の改善は切り離し |

## アクションアイテム

| ID | 内容 | 優先度 | ステータス |
|----|------|--------|-----------|
| act-2026-03-19-004 | Source日付バックフィル（arXiv/S2 API → 53件） | 中 | pending |
| act-2026-03-19-005 | CITESネットワーク構築（4件→50+件目標） | 中 | pending |
| act-2026-03-19-006 | Method→PE拡充（80件未接続の解消） | 低 | pending |
| act-2026-03-19-007 | FinancialDataPoint/FiscalPeriod投入（dr-stock実行時） | 低 | pending |

## KG品質スコア推移

```
C+ (Phase 0: 初期状態)
 → B  (Phase 1: 孤立解消/Topic統合/confidence付与/パイプライン修正)
 → A- (Phase 2: PE接続/Topic階層/sentiment/Anomaly強化) ← 今回
```

## 次回の議論トピック

- Project #92（arXivパイプライン）によるCITES/published自動投入
- 創発的戦略提案クエリの実行（Anomaly→Method→PE→MarketRegime チェーン活用）
- FinancialDataPoint投入のためのdr-stockワークフロー実行計画
