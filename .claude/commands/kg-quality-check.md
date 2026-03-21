---
description: quants KG (bolt://localhost:7690) の品質チェックを実行
---

# /kg-quality-check

quants ナレッジグラフのデータ品質を7カテゴリで計測・評価します。

## スキル参照

`.claude/skills/kg-quality-check/SKILL.md` を読み込み、全フェーズを順に実行してください。

## 実行手順

1. **Phase 1**: 7カテゴリの Cypher プローブを `mcp__neo4j-cypher__read_neo4j_cypher` で実行
   - Completeness（完全性）— 14ノードのプロパティ充填率
   - Consistency（一貫性）— ID フォーマット・enum 値・リレーション妥当性
   - Orphan検出（孤立ノード）— 期待リレーションを持たないノード
   - Staleness（鮮度）— 古い draft Insight、未抽出 Source
   - Structural（構造）— 分布分析、ハブ検出
   - Schema Compliance（スキーマ準拠）— ラベル・制約・PascalCase 検証
   - Research Paper Quality（研究論文品質）— 充填率・接続率・パイプライン差分・重複・引用密度

2. **Phase 2**: LLM-as-Judge で Claim/Fact 精度 + 創発的発見ポテンシャルを評価

3. **Phase 3**: 総合スコア（100点満点）と改善提案を含む Markdown レポートを出力

## 注意

- 全ての Cypher は `mcp__neo4j-cypher__read_neo4j_cypher`（読み取り専用）で実行
- `mcp__neo4j-cypher__write_neo4j_cypher` は使用禁止
- データを修正しない（検出と報告のみ）

$ARGUMENTS
