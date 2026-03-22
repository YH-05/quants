# 議論メモ: KG品質チェック（論文大量投入後）

**日付**: 2026-03-21
**議論ID**: disc-2026-03-21-kg-quality-check
**参加**: ユーザー + AI（Claude Opus 4.6）

## 背景・コンテキスト

701論文（+581新規）を投入した後のKG品質チェック。総合68/100（Rating C）。

## 品質チェック結果サマリー

| カテゴリ | スコア | 重み | 加重スコア |
|---------|--------|------|-----------|
| Completeness | 72% | 20% | 14.4 |
| Consistency | 92% | 18% | 16.6 |
| Orphan | 95% | 13% | 12.4 |
| Staleness | 85% | 8% | 6.8 |
| Structural | 70% | 9% | 6.3 |
| Schema Compliance | 90% | 5% | 4.5 |
| LLM-as-Judge | 75% | 12% | 9.0 |
| Research Paper Quality | **55%** | 15% | **8.3** |
| **総合** | | | **68.2 (C)** |

### 最大の品質課題

**パイプライン別接続率の格差**:
- connected（arxiv-*等 132件）: AUTHORED_BY 73%, MAKES_CLAIM 74%, USES_METHOD 77%
- unconnected（src-* 632件）: AUTHORED_BY 12%, MAKES_CLAIM 11%, USES_METHOD **2%**

→ 今回投入した632件のsrc-*論文はメタデータ（title, abstract, url, authors文字列）のみで、構造化リレーション（Claim, Method, Author）がほぼ未抽出。

### その他の課題
- 重複Source: 10+件（arxiv-*とsrc-*が同一URLで共存）
- Topic.topic_id: 新規100 Topicに未設定
- CITES密度: 2.5%（非常に低い）
- スキーマ外リレーション: 6種47件

## 決定事項

| ID | 内容 | コンテキスト |
|----|------|------------|
| dec-2026-03-21-003 | src-*論文のClaim/Method/Author抽出パイプライン構築が最優先 | 632件中接続率10%以下 |
| dec-2026-03-21-004 | arxiv-*とsrc-*の重複Source統合が必要 | 10+件の重複URL検出 |

## アクションアイテム

| ID | 内容 | 優先度 | ステータス |
|----|------|--------|-----------|
| act-2026-03-21-001 | KG品質チェック実施 | 高 | **完了** |
| act-2026-03-21-002 | Topic間RELATED_TOリレーション構築 | 中 | pending |
| act-2026-03-21-003 | 主要論文の詳細Claim/Method抽出 | 中 | pending |
| act-2026-03-21-004 | 重複Source統合（arxiv-*/src-*） | 高 | pending |
| act-2026-03-21-005 | src-*論文の段階的Claim/Method抽出パイプライン | 高 | pending |
| act-2026-03-21-006 | Topic.topic_id一括付与 | 中 | pending |

## 次回の議論トピック

1. src-*論文のClaim/Method抽出優先順位（visits順 or Topic重要度順）
2. 重複Source統合の実行計画
3. Rating B（70+）到達のための改善ロードマップ
4. Topic階層構造の最適化
