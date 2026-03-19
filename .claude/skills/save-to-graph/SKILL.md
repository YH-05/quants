---
name: save-to-graph
description: graph-queue JSON を読み込み、Neo4j にノードとリレーションを MERGE ベースで冪等投入するスキル。4フェーズ構成（キュー検出 → ノード投入 → リレーション投入 → 完了処理）。KG v2.0 スキーマ（14 ノード・27 リレーション）対応。
allowed-tools: Read, Bash, Grep, Glob
---

# save-to-graph スキル

graph-queue JSON ファイルを読み込み、Neo4j にナレッジグラフデータを投入するスキル。
MERGE ベースの Cypher クエリにより冪等性を保証する。

KG v2.0 スキーマでは 14 種のノード（Source, Entity, Claim, Fact, FinancialDataPoint, FiscalPeriod, Topic, Author, Insight, Method, Anomaly, PerformanceEvidence, MarketRegime, DataRequirement）と 27 種のリレーションを投入する。

## アーキテクチャ

```
/save-to-graph (このスキル = オーケストレーター)
  |
  +-- Phase 1: キュー検出・検証
  |     +-- Neo4j 接続確認（neo4j-cypher MCP）
  |     +-- .tmp/graph-queue/ 配下の未処理 JSON を検出
  |     +-- --source / --file によるフィルタリング
  |     +-- JSON スキーマ検証（schema_version '1.0' / '2.0', 必須キー）
  |
  +-- Phase 2: ノード投入（MERGE）
  |     +-- Topic → Entity → FiscalPeriod → Source → Author
  |     +-- → Fact → Claim → FinancialDataPoint → Insight
  |     +-- → Method → Anomaly → PerformanceEvidence → MarketRegime → DataRequirement
  |
  +-- Phase 3a: ファイル内リレーション投入（MERGE）
  |     +-- TAGGED, MAKES_CLAIM, ABOUT, STATES_FACT
  |     +-- HAS_DATAPOINT, FOR_PERIOD, RELATES_TO, SUPPORTED_BY, AUTHORED_BY
  |
  +-- Phase 3b: クロスファイルリレーション（DB既存ノードとの接続）
  |     +-- TAGGED: カテゴリマッチング
  |     +-- ABOUT: コンテンツマッチング
  |
  +-- Phase 4: 完了処理
        +-- 処理済みファイルの削除 or 移動
        +-- 統計サマリー出力
```

## 使用方法

```bash
# 標準実行（全未処理 JSON を投入）
/save-to-graph

# 特定コマンドソースのみ
/save-to-graph --source dr-stock

# 特定ファイルのみ
/save-to-graph --file .tmp/graph-queue/ca-eval/gq-20260317120000-a1b2.json

# ドライラン
/save-to-graph --dry-run

# 処理済みファイルを保持
/save-to-graph --keep
```

## パラメータ

| パラメータ | デフォルト | 説明 |
|-----------|-----------|------|
| --source | all | 対象コマンドソース |
| --dry-run | false | Cypher を表示するが実行しない |
| --skip-cross-link | false | Phase 3b をスキップ |
| --file | - | 特定ファイル指定（--source と排他） |
| --keep | false | 処理済みファイルを保持 |

## 前提条件

1. **Neo4j が起動していること**（quants-neo4j: bolt://localhost:7690）
2. **初回セットアップが完了していること**（制約・インデックス作成）
3. **graph-queue JSON が存在すること**（`scripts/emit_graph_queue.py` で生成）

## Phase 1: キュー検出・検証

### ステップ 1.1: Neo4j 接続確認

neo4j-cypher MCP の `read_query` で接続テスト:
```
RETURN 'connection_ok' AS status
```

### ステップ 1.2: 未処理ファイル検出

`.tmp/graph-queue/` 配下の `gq-*.json` を検出。

### ステップ 1.3: JSON スキーマ検証

必須キー:
```python
required_keys = {
    "schema_version", "queue_id", "created_at", "command_source",
    "sources", "entities", "claims", "facts", "topics",
    "authors", "financial_datapoints", "fiscal_periods", "insights",
    "relations",
}

# v2.0 追加キー（schema_version "1.0" では省略可、"2.0" では必須）
v2_keys = {
    "anomalies", "performance_evidences", "market_regimes", "data_requirements",
}
```

## Phase 2: ノード投入（MERGE）

投入順序は依存関係に基づく:
**Topic → Entity → FiscalPeriod → Source → Author → Fact → Claim → FinancialDataPoint → Insight → Method → Anomaly → PerformanceEvidence → MarketRegime → DataRequirement**

### Topic ノード MERGE
```cypher
MERGE (t:Topic {topic_id: $topic_id})
SET t.name = $name, t.category = $category
```

### Entity ノード MERGE
```cypher
MERGE (e:Entity {entity_id: $entity_id})
SET e.name = $name, e.entity_type = $entity_type, e.ticker = $ticker
```

### FiscalPeriod ノード MERGE
```cypher
MERGE (fp:FiscalPeriod {period_id: $period_id})
SET fp.period_type = $period_type, fp.period_label = $period_label
```

### Source ノード MERGE
```cypher
MERGE (s:Source {source_id: $source_id})
SET s.url = $url, s.title = $title, s.source_type = $source_type,
    s.command_source = $command_source
```

### Author ノード MERGE
```cypher
MERGE (a:Author {author_id: $author_id})
SET a.name = $name, a.author_type = $author_type
```

### Fact ノード MERGE
```cypher
MERGE (f:Fact {fact_id: $fact_id})
SET f.content = $content, f.fact_type = $fact_type,
    f.created_at = datetime($created_at)
```

### Claim ノード MERGE
```cypher
MERGE (c:Claim {claim_id: $claim_id})
SET c.content = $content, c.claim_type = $claim_type,
    c.sentiment = $sentiment, c.created_at = datetime($created_at)
```

### FinancialDataPoint ノード MERGE
```cypher
MERGE (dp:FinancialDataPoint {datapoint_id: $datapoint_id})
SET dp.metric_name = $metric_name, dp.value = $value,
    dp.unit = $unit, dp.is_estimate = $is_estimate
```

### Insight ノード MERGE
```cypher
MERGE (i:Insight {insight_id: $insight_id})
SET i.content = $content, i.insight_type = $insight_type,
    i.generated_at = datetime($generated_at)
```

### Method ノード MERGE
```cypher
MERGE (m:Method {method_id: $method_id})
SET m.name = $name, m.method_type = $method_type, m.description = $description
```

### Anomaly ノード MERGE
```cypher
MERGE (a:Anomaly {anomaly_id: $anomaly_id})
SET a.name = $name, a.anomaly_type = $anomaly_type,
    a.persistence = $persistence, a.created_at = datetime()
```

### PerformanceEvidence ノード MERGE
```cypher
MERGE (pe:PerformanceEvidence {evidence_id: $evidence_id})
SET pe.metric_name = $metric_name, pe.value = $value,
    pe.unit = $unit, pe.benchmark = $benchmark, pe.market = $market,
    pe.is_oos = $is_oos, pe.created_at = datetime()
```

### MarketRegime ノード MERGE
```cypher
MERGE (mr:MarketRegime {regime_id: $regime_id})
SET mr.name = $name, mr.regime_type = $regime_type,
    mr.description = $description, mr.created_at = datetime()
```

### DataRequirement ノード MERGE
```cypher
MERGE (dr:DataRequirement {data_req_id: $data_req_id})
SET dr.name = $name, dr.data_type = $data_type,
    dr.frequency = $frequency, dr.availability = $availability,
    dr.created_at = datetime()
```

## Phase 3a: ファイル内リレーション投入

graph-queue JSON の `relations` オブジェクトから各リレーションを MERGE:

- `tagged[]` → `TAGGED` (Source → Topic)
- `makes_claim[]` → `MAKES_CLAIM` (Source → Claim)
- `about[]` → `ABOUT` (Claim → Entity)
- `states_fact[]` → `STATES_FACT` (Source → Fact)
- `has_datapoint[]` → `HAS_DATAPOINT` (Entity → FinancialDataPoint)
- `for_period[]` → `FOR_PERIOD` (FinancialDataPoint → FiscalPeriod)
- `relates_to[]` → `RELATES_TO` (Fact → Entity)
- `supported_by[]` → `SUPPORTED_BY` (Claim → Fact)
- `authored_by[]` → `AUTHORED_BY` (Source → Author)
- `uses_method[]` → `USES_METHOD` (Source → Method)
- `exploits[]` → `EXPLOITS` (Method → Anomaly)
- `evaluates[]` → `EVALUATES` (PerformanceEvidence → Method)
- `quantified_by[]` → `QUANTIFIED_BY` (Claim → PerformanceEvidence)
- `effective_in[]` → `EFFECTIVE_IN` (Method → MarketRegime)
- `requires_data[]` → `REQUIRES_DATA` (Method → DataRequirement)
- `explained_by[]` → `EXPLAINED_BY` (Anomaly → Claim)
- `measured_in[]` → `MEASURED_IN` (PerformanceEvidence → MarketRegime)
- `extends_method[]` → `EXTENDS_METHOD` (Method → Method)
- `combined_with[]` → `COMBINED_WITH` (Method → Method)
- `competes_with[]` → `COMPETES_WITH` (Method → Method)
- `contradicts[]` → `CONTRADICTS` (Claim → Claim)

## Phase 3b: クロスファイルリレーション

### TAGGED カテゴリマッチング
```cypher
UNWIND $source_ids AS sid
MATCH (s:Source {source_id: sid})
MATCH (t:Topic {category: s.category})
MERGE (s)-[:TAGGED]->(t)
```

### ABOUT コンテンツマッチング
```cypher
UNWIND $claim_ids AS cid
MATCH (c:Claim {claim_id: cid})
MATCH (e:Entity)
WHERE size(e.name) >= 2 AND c.content CONTAINS e.name
MERGE (c)-[:ABOUT]->(e)
```

## Phase 4: 完了処理

| モード | 動作 |
|--------|------|
| デフォルト | 処理済み JSON を削除 |
| `--keep` | `.tmp/graph-queue/.processed/` に移動 |

## 冪等性の保証

1. **ノード投入**: MERGE はノード存在時に更新、不在時に作成
2. **リレーション投入**: MERGE はリレーション存在時に何もしない
3. **ID の決定論性**: 全 ID は入力データから決定論的に生成（UUID5 / SHA-256）

## エラーハンドリング

| エラー | 対処 |
|--------|------|
| E001: Neo4j 接続失敗 | NEO4J_URI=bolt://localhost:7690, NEO4J_PASSWORD 確認 |
| E002: graph-queue 未検出 | `scripts/emit_graph_queue.py` で JSON 生成 |
| E003: JSON 検証エラー | schema_version と必須キーを確認 |
| E004: Cypher 実行エラー | 制約・インデックス未作成の場合は初回セットアップ実行 |

## 環境変数

| 変数名 | デフォルト | 説明 |
|--------|-----------|------|
| NEO4J_URI | bolt://localhost:7690 | Neo4j Bolt URI |
| NEO4J_USER | neo4j | Neo4j ユーザー名 |
| NEO4J_PASSWORD | (必須) | Neo4j パスワード |

## 対応コマンドソース

| コマンドソース | 主な生成ノード |
|--------------|--------------|
| finance-news-workflow | Source, Claim, Topic |
| ai-research-collect | Entity, Source |
| generate-market-report | Source, Entity, FinancialDataPoint |
| dr-stock | Entity, FinancialDataPoint, FiscalPeriod, Claim, Fact |
| ca-eval | Claim, Fact, Insight |
| dr-industry | Entity, Claim, Fact |
| finance-research | Source, Claim |
| pdf-to-knowledge | Source, Entity, Claim, Fact, Method, Anomaly, PerformanceEvidence, MarketRegime, DataRequirement |

## 関連リソース

| リソース | パス |
|---------|------|
| 詳細ガイド | `.claude/skills/save-to-graph/guide.md` |
| スラッシュコマンド | `.claude/commands/save-to-graph.md` |
| graph-queue 生成スクリプト | `scripts/emit_graph_queue.py` |
| KG スキーマ定義 | `data/config/knowledge-graph-schema.yaml` |
| 制約・インデックス | `data/config/neo4j-constraints.cypher` |
| 名前空間規約 | `.claude/rules/neo4j-namespace-convention.md` |
