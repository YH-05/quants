# save-to-graph 詳細ガイド

## 初回セットアップ

### 前提: Neo4j 接続

quants プロジェクトでは `quants-neo4j` (bolt://localhost:7690) を使用。

```bash
# 環境変数設定
export NEO4J_URI="bolt://localhost:7690"
export NEO4J_USER="neo4j"
export NEO4J_PASSWORD="quants2026"

# 接続テスト（neo4j-cypher MCP 経由）
# read_query: "RETURN 'connection_ok' AS status"
```

### UNIQUE 制約の作成（9個）

`data/config/neo4j-constraints.cypher` の全クエリを実行:

```cypher
CREATE CONSTRAINT unique_source_id IF NOT EXISTS
  FOR (s:Source) REQUIRE s.source_id IS UNIQUE;

CREATE CONSTRAINT unique_entity_id IF NOT EXISTS
  FOR (e:Entity) REQUIRE e.entity_id IS UNIQUE;

CREATE CONSTRAINT unique_claim_id IF NOT EXISTS
  FOR (c:Claim) REQUIRE c.claim_id IS UNIQUE;

CREATE CONSTRAINT unique_fact_id IF NOT EXISTS
  FOR (f:Fact) REQUIRE f.fact_id IS UNIQUE;

CREATE CONSTRAINT unique_datapoint_id IF NOT EXISTS
  FOR (dp:FinancialDataPoint) REQUIRE dp.datapoint_id IS UNIQUE;

CREATE CONSTRAINT unique_period_id IF NOT EXISTS
  FOR (fp:FiscalPeriod) REQUIRE fp.period_id IS UNIQUE;

CREATE CONSTRAINT unique_topic_id IF NOT EXISTS
  FOR (t:Topic) REQUIRE t.topic_id IS UNIQUE;

CREATE CONSTRAINT unique_author_id IF NOT EXISTS
  FOR (a:Author) REQUIRE a.author_id IS UNIQUE;

CREATE CONSTRAINT unique_insight_id IF NOT EXISTS
  FOR (i:Insight) REQUIRE i.insight_id IS UNIQUE;
```

### インデックスの作成（13個）

```cypher
CREATE INDEX idx_fact_fact_type IF NOT EXISTS FOR (f:Fact) ON (f.fact_type);
CREATE INDEX idx_fact_as_of_date IF NOT EXISTS FOR (f:Fact) ON (f.as_of_date);
CREATE INDEX idx_claim_claim_type IF NOT EXISTS FOR (c:Claim) ON (c.claim_type);
CREATE INDEX idx_claim_sentiment IF NOT EXISTS FOR (c:Claim) ON (c.sentiment);
CREATE INDEX idx_entity_entity_type IF NOT EXISTS FOR (e:Entity) ON (e.entity_type);
CREATE INDEX idx_entity_ticker IF NOT EXISTS FOR (e:Entity) ON (e.ticker);
CREATE INDEX idx_datapoint_metric_name IF NOT EXISTS FOR (dp:FinancialDataPoint) ON (dp.metric_name);
CREATE INDEX idx_datapoint_is_estimate IF NOT EXISTS FOR (dp:FinancialDataPoint) ON (dp.is_estimate);
CREATE INDEX idx_period_period_label IF NOT EXISTS FOR (fp:FiscalPeriod) ON (fp.period_label);
CREATE INDEX idx_insight_insight_type IF NOT EXISTS FOR (i:Insight) ON (i.insight_type);
CREATE INDEX idx_insight_status IF NOT EXISTS FOR (i:Insight) ON (i.status);
CREATE INDEX idx_source_source_type IF NOT EXISTS FOR (s:Source) ON (s.source_type);
CREATE INDEX idx_source_command_source IF NOT EXISTS FOR (s:Source) ON (s.command_source);
```

## graph-queue フォーマット仕様

### 最小構造

```json
{
  "schema_version": "2.2",
  "queue_id": "gq-20260317120000-a1b2c3d4",
  "created_at": "2026-03-17T12:00:00+00:00",
  "command_source": "dr-stock",
  "input_path": "research/DR_stock_20260213_MCO/03_analysis/stock-analysis.json",
  "sources": [],
  "entities": [],
  "claims": [],
  "facts": [],
  "topics": [],
  "authors": [],
  "financial_datapoints": [],
  "fiscal_periods": [],
  "insights": [],
  "relations": {
    "tagged": [],
    "makes_claim": [],
    "states_fact": [],
    "about": [],
    "relates_to": [],
    "has_datapoint": [],
    "for_period": [],
    "supported_by": [],
    "authored_by": [],
    "cites": [],
    "coauthored_with": [],
    "subtopic_of": [],
    "affiliated_with": []
  }
}
```

### ノード配列のフォーマット

各ノードは `id` フィールドを必須とし、MCP の `write_query` のパラメータとして渡される:

```json
{
  "sources": [
    {
      "id": "uuid5-based-id",
      "url": "https://...",
      "title": "...",
      "source_type": "news_article",
      "published": "2026-03-17T10:00:00Z"
    }
  ]
}
```

### リレーション配列のフォーマット

```json
{
  "relations": {
    "makes_claim": [
      {"from_id": "source-uuid", "to_id": "claim-sha256-hash"}
    ]
  }
}
```

## ID 生成戦略

| ノード | ID 生成方法 | 例 |
|--------|-----------|-----|
| Source | UUID5(url) | `a1b2c3d4-...` |
| Entity | UUID5(f"entity:{name}:{type}") | `e5f6g7h8-...` |
| Claim | SHA-256(content)[:32] | `a1b2c3d4e5f6...` |
| Fact | SHA-256(f"fact:{content}")[:32] | `f1f2f3f4f5f6...` |
| Topic | UUID5(f"topic:{name}:{category}") | `t1t2t3t4-...` |
| Author | UUID5(f"author:{name}:{type}") | `a1a2a3a4-...` |
| FinancialDataPoint | SHA-256(f"{hash}:{metric}:{period}")[:32] | `d1d2d3d4...` |
| FiscalPeriod | `{ticker}_{period_label}` | `AAPL_FY2025` |
| Insight | `ins-{date}-{seq:04d}` | `ins-2026-03-17-0001` |

## Cypher テンプレート

### ノード投入

neo4j-cypher MCP の `write_query` を使用。各ノードは個別の MERGE クエリで投入:

```
# Topic
write_query: "MERGE (t:Topic {topic_id: $id}) SET t.name = $name, t.category = $category"
params: {"id": "...", "name": "...", "category": "..."}

# Entity
write_query: "MERGE (e:Entity {entity_id: $id}) SET e.name = $name, e.entity_type = $entity_type, e.ticker = $ticker"
params: {"id": "...", "name": "...", "entity_type": "...", "ticker": "..."}
```

### リレーション投入

```
# TAGGED
write_query: "MATCH (s:Source {source_id: $from_id}) MATCH (t:Topic {topic_id: $to_id}) MERGE (s)-[:TAGGED]->(t)"
params: {"from_id": "...", "to_id": "..."}

# MAKES_CLAIM
write_query: "MATCH (s:Source {source_id: $from_id}) MATCH (c:Claim {claim_id: $to_id}) MERGE (s)-[:MAKES_CLAIM]->(c)"
params: {"from_id": "...", "to_id": "..."}
```

## ノードプロパティの ID フィールドマッピング

graph-queue JSON の `id` フィールドは、Neo4j ノードの固有 ID プロパティにマッピングされる:

| ノード | graph-queue `id` | Neo4j プロパティ |
|--------|-----------------|-----------------|
| Source | id | source_id |
| Entity | id | entity_id |
| Claim | id | claim_id |
| Fact | id | fact_id |
| FinancialDataPoint | id | datapoint_id |
| FiscalPeriod | id | period_id |
| Topic | id | topic_id |
| Author | id | author_id |
| Insight | id | insight_id |

## 検証コマンド

```bash
# 投入後のノード数確認
# neo4j-cypher read_query: "MATCH (n) RETURN labels(n)[0] AS label, count(*) AS cnt ORDER BY label"

# スキーマ検証
python scripts/validate_neo4j_schema.py --neo4j-password quants2026
```
