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

### 追加アクション実行結果

| アクション | 結果 |
|----------|------|
| #1: Claim→Entity リンク | ABOUT 177件 + TAGGED 715件作成。140/288 Claims が Entity 接続 |
| #2: edgar.rate_limiter 修正 | RateLimiter を database パッケージに移動、academic import 復旧 |
| #3: 重複Source マージ | 16件統合・削除完了。リレーション移行済み |
| #4: Author/COAUTHORED_WITH 拡充 | academic backfill で S2 API から 433 Author 取得・投入 |

### KG 全体の変化（セッション全体）

| 指標 | セッション開始時 | 最終状態 | 変化 |
|------|-----------------|---------|------|
| Source | 237 | 294 | +57 |
| Author | 312 | 836 | +524 |
| Claim | 189 | 288 | +99 |
| AUTHORED_BY | 354 | 836 | +482 |
| MAKES_CLAIM | 192 | 291 | +99 |
| ABOUT | 0 | 177 | +177 |
| TAGGED | 549 | 1,234 | +685 |
| Consistency enum 違反 | 211件 | ~20件 | -90% |

## 決定事項

| ID | 内容 | コンテキスト |
|----|------|------------|
| dec-2026-03-21-001 | Phase 1.7 Research Paper Quality（15%）を追加 | KG全ノードの93%が論文系Source |
| dec-2026-03-21-002 | Source に abstract, venue を正式追加 | スキーマドリフト解消 |
| dec-2026-03-21-003 | published_date/published → published_at に統一 | 同一意味のプロパティ3種を解消 |
| dec-2026-03-21-004 | Claim.sentiment/claim_type enum を正規化 | Consistency 向上、違反ゼロ達成 |
| dec-2026-03-21-005 | src-* 89件にAuthor展開+Claim抽出を実施 | パイプライン間品質格差の解消 |
| dec-2026-03-21-006 | RateLimiter を database パッケージに移動 | edgartools との名前衝突を解消 |
| dec-2026-03-21-007 | 重複Source 16件を統合（arxiv-* に集約、src-* 削除） | リレーション移行後に削除 |
| dec-2026-03-21-008 | Claim→Entity は著者所属経由（177件）+ TAGGED（715件）で対応 | 市場エンティティノードが不在のため間接リンクで対応 |
| dec-2026-03-21-009 | S2 API の references.externalIds フィールドを追加し CITES 構築を実現 | S2 API がデフォルトで references の externalIds を返さないことが原因 |
| dec-2026-03-21-010 | Method.method_type 38件を既存 enum にマッピング正規化 | benchmark→framework、statistical_model→model 等 |

## アクションアイテム

| ID | 内容 | 優先度 | 状態 |
|----|------|--------|------|
| act-2026-03-21-001 | B7: CITES 再構築（backfill に --existing-ids ファイル対応を追加） | 中 | pending |
| act-2026-03-21-002 | 重複Source 16件のマージ | 中 | **completed** |
| act-2026-03-21-003 | Claim→ABOUT→Entity リレーション構築 | 高 | **completed**（177件） |
| act-2026-03-21-004 | edgar.rate_limiter インポートエラー修正 | 高 | **completed** |
| act-2026-03-21-005 | B7: CITES — S2 API フィールド修正 + 15件構築 | 中 | **completed** |
| act-2026-03-21-006 | 残り148件の Claim に市場エンティティノードを作成してリンク | 中 | pending（構造的制約あり） |
| act-2026-03-21-007 | /kg-quality-check 再実行で改善効果を定量確認 | 高 | **completed**（85点 Rating A 達成） |

### 最終改善アクション（追加実施分）

| アクション | 結果 |
|----------|------|
| 重複Source 73件削除（backfill副作用） | Check E: 75%→100% |
| Method.method_type 38件正規化 | enum 違反 38→0件 |
| CITES 15件構築（S2 API references.externalIds 修正） | 4→19件、Check F: 1.4%→9.3% |

### 最終スコア

**総合: 85/100（Rating A）** — セッション開始時 73点から +12点改善

| カテゴリ | 開始時 | 最終 |
|---------|--------|------|
| Completeness | 87.5% | 87% |
| Consistency | 90% | **99%** |
| Orphan | 64% | **87%** |
| Staleness | 100% | 100% |
| Structural | 40% | **61%** |
| Schema Compliance | 100% | 100% |
| LLM-as-Judge | 63% | 65% |
| Research Paper Quality | 44% | **73%** |

## 次回の議論トピック

- 市場エンティティ（銘柄・指数・セクター等）ノードの設計と投入 → Structural 61%→80%+ に改善可能
- CITES の網羅的構築（残り全論文の S2 参照データ取得）
- Claim→ABOUT→Entity の改善（市場エンティティ追加後に再リンク）

## 関連ファイル

| ファイル | 説明 |
|---------|------|
| `docs/superpowers/specs/2026-03-21-kg-paper-quality-design.md` | 設計書 |
| `docs/superpowers/plans/2026-03-21-kg-paper-quality.md` | 実装計画 |
| `data/config/knowledge-graph-schema.yaml` | スキーマ SSoT |
| `.claude/skills/kg-quality-check/SKILL.md` | 品質チェックスキル |
