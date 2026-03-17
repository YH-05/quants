# Neo4j 名前空間・命名規約

## 統一ルール

**全ノードラベルは PascalCase で統一する。**

snake_case ラベル（`content_theme`, `decision` 等）は禁止。
Memory MCP の `create_entities` 呼び出し時、`entityType` / `type` は必ず PascalCase で指定すること。

## 名前空間分類

| 名前空間 | ラベル | 用途 |
|---------|--------|------|
| kg_v1 | Source, Entity, Claim, Fact, FinancialDataPoint, FiscalPeriod, Topic, Author, Insight | KG v1 スキーマ（9ノード） |
| memory | Memory (root) + サブラベル | MCP Memory |
| conversation | ConversationSession, ConversationTopic, Project | 会話履歴（将来） |
| archived | Archived | アーカイブ済みレガシーノード |

## Memory 許可サブラベル一覧

`Memory` ノードに付与できるサブラベルは以下のみ:

| サブラベル | 説明 |
|-----------|------|
| Decision | 設計・技術的判断 |
| ContentTheme | コンテンツテーマ |
| Theme | テーマ（副業・記事テーマ等） |
| Implementation | 実装案・設計案 |
| Phase | プロジェクトフェーズ |
| Strategy | 戦略・方針 |
| CaseStudy | 事例研究 |
| Architecture | アーキテクチャ設計 |
| Schema | スキーマ定義 |
| Status | 現状・ステータス |
| BusinessModel | ビジネスモデル |
| Workflow | ワークフロー |
| Research | リサーチ結果 |
| Todo | 未決定事項・タスク |
| Discussion | 議論・検討事項 |

## クエリガイドライン

### KG v1 専用クエリ（Memory を除外）

```cypher
MATCH (n:Entity)
WHERE NOT 'Memory' IN labels(n)
RETURN n
```

### Memory 専用クエリ

```cypher
MATCH (m:Memory)
RETURN m, labels(m) AS types
```

### 名前空間横断クエリ（非推奨）

KG v1 ノードと Memory ノードを同一クエリで混在させることは避ける。
必要な場合は `labels(n)` で明示的にフィルタすること。

## Memory MCP 呼び出し時の注意

```json
// 正しい（PascalCase）
{
  "entityType": "Decision",
  "name": "KGスキーマ設計の決定"
}

// 誤り（snake_case）— 禁止
{
  "entityType": "decision",
  "name": "KGスキーマ設計の決定"
}
```

## 違反の検出

スキーマ検証スクリプトで自動検出:

```bash
python scripts/validate_neo4j_schema.py
```
