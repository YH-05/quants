# 議論メモ: KG品質チェック研究論文対応

**日付**: 2026-03-21
**議論ID**: disc-2026-03-21-kg-paper-quality
**参加**: ユーザー + AI

## 背景・コンテキスト

`/kg-quality-check` スキルは KG v2.2 の全体構造品質を網羅的にチェックするが、研究論文データ固有の品質問題に対して6つの盲点が特定された。KG全ノードの93%が論文系Sourceであり、品質チェック強化の優先度が高い。

### 特定された盲点

1. `source_type` 別のブレークダウンがない
2. スキーマドリフト（データにあるがYAML未定義のプロパティ）を検出していない
3. Author文字列↔AUTHORED_BY リレーションの不整合を検出していない
4. パイプライン別（`arxiv-*` vs `src-*`）の品質格差を検出していない
5. 重複Sourceを検出していない
6. 引用ネットワーク密度を計測していない

### データ実態

- 論文系Source: 221件（paper 158 + report 63）
- `arxiv-*`: 98件（接続良好）
- `src-*`: 89件（Topic以外の接続なし）
- `jsai2026-*`/UUID: 34件（arxiv-*と同等品質）

## 議論のサマリー

### 方針決定

1. **A→B 戦略**: スキル改善（検出能力向上）→ データバックフィル（実データ修正）の順序で実行
2. **既存スキル拡張 + スキーマYAML更新**: 新スキル分離ではなく、既存スキルに Phase 1.7 を追加
3. **命名統一**: `published_date` → `published_at` に統一（マイグレーション含む）
4. **全6チェック採用**: source_type別、スキーマドリフト、Author整合性、パイプライン差分、重複検出、引用密度の全てを実装

### Phase A 実行結果（スキル改善）

- `data/config/knowledge-graph-schema.yaml`: Source に `abstract`, `venue` 追加
- `.claude/skills/kg-quality-check/SKILL.md`: Phase 1.7（6サブチェック）追加、重み再配分（8カテゴリ合計100%）
- `.claude/commands/kg-quality-check.md`: 7カテゴリ対応に更新
- 動作確認: Phase 1.7 全チェック実行成功、Research Paper Quality **44%**
- 総合スコア: 78点 → **73点**（盲点の正確な検出による低下）
- コミット: 8件（main ブランチ、037b922〜9dbf82b）

### Phase B 実行結果（データバックフィル）

| タスク | 結果 |
|--------|------|
| B1: `published_date`/`published` → `published_at` | 148件移行 |
| B2: Claim.sentiment 正規化 | 94件修正 → 違反ゼロ |
| B3: Claim.claim_type 正規化 | 57件修正 → 違反ゼロ |
| B4: `src-*` Claim 抽出 | 99 Claims 新規作成（81/89 接続） |
| B5: `src-*` Author 展開 | 141 Author, 165 AUTHORED_BY 作成（84/89 接続） |
| B6: PE ID 正規化 | 47件修正 → 違反ゼロ |
| B7: CITES 再構築 | **未実施**（edgar 依存関係エラー） |

### KG 全体の変化

| 指標 | Before | After |
|------|--------|-------|
| Claim ノード | 189 | 288 |
| Author ノード | 312 | 453 |
| MAKES_CLAIM | 192 | 291 |
| AUTHORED_BY | 354 | 519 |
| Consistency enum 違反 | 211件 | ~20件 |

## 決定事項

| ID | 内容 | コンテキスト |
|----|------|------------|
| dec-2026-03-21-001 | Phase 1.7 Research Paper Quality（15%）を追加 | KG全ノードの93%が論文系Source |
| dec-2026-03-21-002 | Source に abstract, venue を正式追加 | スキーマドリフト解消 |
| dec-2026-03-21-003 | published_date/published → published_at に統一 | 同一意味のプロパティ3種を解消 |
| dec-2026-03-21-004 | Claim.sentiment/claim_type enum を正規化 | Consistency 向上、違反ゼロ達成 |
| dec-2026-03-21-005 | src-* 89件にAuthor展開+Claim抽出を実施 | パイプライン間品質格差の解消 |

## アクションアイテム

| ID | 内容 | 優先度 | 状態 |
|----|------|--------|------|
| act-2026-03-21-001 | B7: CITES 再構築（edgar 依存関係修正後） | 中 | blocked |
| act-2026-03-21-002 | 重複Source 16件のマージ | 中 | pending |
| act-2026-03-21-003 | Claim→ABOUT→Entity リレーション構築（288件が未接続） | 高 | pending |
| act-2026-03-21-004 | edgar.rate_limiter インポートエラー修正（名前衝突） | 高 | pending |

## 次回の議論トピック

- Claim→ABOUT→Entity リレーション構築の自動化パイプライン設計
- edgar パッケージの名前衝突解消（edgartools との分離）
- Phase B 完了後の品質スコア目標達成確認（Research Paper Quality 70%+、総合 85+）

## 関連ファイル

| ファイル | 説明 |
|---------|------|
| `docs/superpowers/specs/2026-03-21-kg-paper-quality-design.md` | 設計書 |
| `docs/superpowers/plans/2026-03-21-kg-paper-quality.md` | 実装計画 |
| `data/config/knowledge-graph-schema.yaml` | スキーマ SSoT |
| `.claude/skills/kg-quality-check/SKILL.md` | 品質チェックスキル |
