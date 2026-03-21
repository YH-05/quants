---
name: kg-quality-check
description: |
  quants KG (bolt://localhost:7690) の品質を計測・評価するスキル。
  KG v2.2 スキーマ（14ノード・31リレーション）に対して
  7カテゴリの定量指標を計測し、LLM-as-Judge による精度・発見性チェックを実行する。
  「KG品質」「ナレッジグラフ品質」「グラフ品質チェック」「Neo4j品質」
  と言われたら必ずこのスキルを使うこと。
  Use PROACTIVELY when the user asks about KG quality, graph data quality,
  or after bulk data ingestion (save-to-graph) to verify integrity.
allowed-tools: Read, Write, Bash, Glob, Grep
---

# kg-quality-check

quants KG (bolt://localhost:7690) のデータ品質を計測し、Claude Code が LLM-as-Judge として
Claim/Fact の精度と創発的発見ポテンシャルを評価するスキル。

## 目的

- **定量計測**: 7カテゴリの品質指標を Cypher プローブで計測
- **精度評価**: Claim/Fact のサンプリング精度を Claude Code が評価
- **発見性評価**: グラフ構造から仮説を生成し、発見ポテンシャルを評価
- **レポート生成**: 定量スコア + 問題一覧 + 改善提案を Markdown レポートで出力

## いつ使用するか

### プロアクティブ使用（自動で検討）

1. **KG のデータ品質を確認したい場合**
   - 「KG の品質は？」「ナレッジグラフの状態を確認」
   - 「孤立ノードはある？」「充填率を調べて」

2. **データ投入後の検証**
   - `/save-to-graph` でデータ投入した後
   - スキーマ変更を適用した後

3. **定期的な品質モニタリング**
   - 「Claim の品質はどう？」「enum 値に異常はない？」

### 明示的な使用

- `/kg-quality-check` コマンドで直接実行

## 処理フロー

```
Phase 1: 定量計測（Cypher プローブ）
    |  mcp__neo4j-cypher__read_neo4j_cypher で7カテゴリの指標を計測
    |
Phase 1.7: Research Paper Quality（Cypher プローブ）
    |  論文系 Source の充填率・接続率・パイプライン品質を計測
    |
Phase 2: LLM-as-Judge
    |  Claim/Fact のサンプリング精度評価
    |  4構造プローブ → 仮説構築 → 自己評価
    |
Phase 3: レポート出力
    定量スコア + 問題一覧 + 改善提案をユーザーに提示
```

## Phase 1: 定量計測（7カテゴリ）

全ての Cypher クエリは `mcp__neo4j-cypher__read_neo4j_cypher` を使用する（読み取りのみ）。

### 1.1 Completeness（完全性）— 重み 20%

14ノード全てのプロパティ充填率を計測する。重み分類は `data/config/knowledge-graph-schema.yaml` に基づく。

- **必須** (重み 1.0): `required: true` のプロパティ
- **推奨** (重み 0.7): `indexed: true` だが `required` でないプロパティ
- **任意** (重み 0.3): 上記いずれでもないプロパティ

**Source の充填率**:

```cypher
MATCH (s:Source)
RETURN
    count(s) AS total,
    count(s.source_id) AS has_id,
    count(s.title) AS has_title,
    count(s.source_type) AS has_source_type,
    count(s.fetched_at) AS has_fetched_at,
    count(s.url) AS has_url,
    count(s.publisher) AS has_publisher,
    count(s.published_at) AS has_published_at,
    count(s.language) AS has_language,
    count(s.category) AS has_category,
    count(s.command_source) AS has_command_source
```

| プロパティ | 重要度 |
|-----------|--------|
| source_id, title, source_type, fetched_at | 必須 |
| url, publisher, published_at, category, command_source | 推奨 |
| language | 任意 |

**Entity の充填率**:

```cypher
MATCH (e:Entity)
RETURN
    count(e) AS total,
    count(e.entity_id) AS has_id,
    count(e.name) AS has_name,
    count(e.entity_type) AS has_entity_type,
    count(e.ticker) AS has_ticker,
    count(e.aliases) AS has_aliases,
    count(e.isin) AS has_isin
```

| プロパティ | 重要度 |
|-----------|--------|
| entity_id, name, entity_type | 必須 |
| ticker, isin | 推奨 |
| aliases | 任意 |

**Claim の充填率**:

```cypher
MATCH (c:Claim)
RETURN
    count(c) AS total,
    count(c.claim_id) AS has_id,
    count(c.content) AS has_content,
    count(c.created_at) AS has_created_at,
    count(c.claim_type) AS has_claim_type,
    count(c.sentiment) AS has_sentiment,
    count(c.confidence) AS has_confidence,
    count(c.magnitude) AS has_magnitude,
    count(c.target_price) AS has_target_price,
    count(c.rating) AS has_rating,
    count(c.time_horizon) AS has_time_horizon
```

| プロパティ | 重要度 |
|-----------|--------|
| claim_id, content, created_at | 必須 |
| claim_type, sentiment, confidence | 推奨 |
| magnitude, target_price, rating, time_horizon | 任意 |

**Fact の充填率**:

```cypher
MATCH (f:Fact)
RETURN
    count(f) AS total,
    count(f.fact_id) AS has_id,
    count(f.content) AS has_content,
    count(f.created_at) AS has_created_at,
    count(f.fact_type) AS has_fact_type,
    count(f.as_of_date) AS has_as_of_date
```

| プロパティ | 重要度 |
|-----------|--------|
| fact_id, content, created_at | 必須 |
| fact_type, as_of_date | 推奨 |

**FinancialDataPoint の充填率**:

```cypher
MATCH (dp:FinancialDataPoint)
RETURN
    count(dp) AS total,
    count(dp.datapoint_id) AS has_id,
    count(dp.metric_name) AS has_metric_name,
    count(dp.value) AS has_value,
    count(dp.unit) AS has_unit,
    count(dp.is_estimate) AS has_is_estimate,
    count(dp.created_at) AS has_created_at,
    count(dp.currency) AS has_currency
```

| プロパティ | 重要度 |
|-----------|--------|
| datapoint_id, metric_name, value, unit, is_estimate, created_at | 必須 |
| currency | 任意 |

**FiscalPeriod の充填率**:

```cypher
MATCH (fp:FiscalPeriod)
RETURN
    count(fp) AS total,
    count(fp.period_id) AS has_id,
    count(fp.period_type) AS has_period_type,
    count(fp.period_label) AS has_period_label,
    count(fp.start_date) AS has_start_date,
    count(fp.end_date) AS has_end_date
```

| プロパティ | 重要度 |
|-----------|--------|
| period_id, period_type, period_label | 必須 |
| start_date, end_date | 任意 |

**Topic の充填率**:

```cypher
MATCH (t:Topic)
RETURN
    count(t) AS total,
    count(t.topic_id) AS has_id,
    count(t.name) AS has_name,
    count(t.category) AS has_category,
    count(t.is_meta) AS has_is_meta
```

| プロパティ | 重要度 |
|-----------|--------|
| topic_id, name | 必須 |
| category, is_meta | 推奨 |

**Author の充填率**:

```cypher
MATCH (a:Author)
RETURN
    count(a) AS total,
    count(a.author_id) AS has_id,
    count(a.name) AS has_name,
    count(a.author_type) AS has_author_type,
    count(a.organization) AS has_organization
```

| プロパティ | 重要度 |
|-----------|--------|
| author_id, name, author_type | 必須 |
| organization | 推奨 |

**Insight の充填率**:

```cypher
MATCH (i:Insight)
RETURN
    count(i) AS total,
    count(i.insight_id) AS has_id,
    count(i.insight_type) AS has_insight_type,
    count(i.content) AS has_content,
    count(i.generated_at) AS has_generated_at,
    count(i.status) AS has_status,
    count(i.model) AS has_model
```

| プロパティ | 重要度 |
|-----------|--------|
| insight_id, insight_type, content, generated_at | 必須 |
| status, model | 推奨 |

**Method の充填率**:

```cypher
MATCH (m:Method)
RETURN
    count(m) AS total,
    count(m.method_id) AS has_id,
    count(m.name) AS has_name,
    count(m.method_type) AS has_method_type,
    count(m.description) AS has_description,
    count(m.created_at) AS has_created_at
```

| プロパティ | 重要度 |
|-----------|--------|
| method_id, name, method_type | 必須 |
| description, created_at | 推奨 |

**Anomaly の充填率**:

```cypher
MATCH (a:Anomaly)
RETURN
    count(a) AS total,
    count(a.anomaly_id) AS has_id,
    count(a.name) AS has_name,
    count(a.anomaly_type) AS has_anomaly_type,
    count(a.created_at) AS has_created_at,
    count(a.persistence) AS has_persistence,
    count(a.first_documented_year) AS has_first_documented_year
```

| プロパティ | 重要度 |
|-----------|--------|
| anomaly_id, name, anomaly_type, created_at | 必須 |
| persistence | 推奨 |
| first_documented_year | 任意 |

**PerformanceEvidence の充填率**:

```cypher
MATCH (pe:PerformanceEvidence)
RETURN
    count(pe) AS total,
    count(pe.evidence_id) AS has_id,
    count(pe.metric_name) AS has_metric_name,
    count(pe.value) AS has_value,
    count(pe.created_at) AS has_created_at,
    count(pe.unit) AS has_unit,
    count(pe.market) AS has_market,
    count(pe.is_oos) AS has_is_oos,
    count(pe.benchmark) AS has_benchmark,
    count(pe.benchmark_value) AS has_benchmark_value,
    count(pe.period_start) AS has_period_start,
    count(pe.period_end) AS has_period_end,
    count(pe.sample_size) AS has_sample_size
```

| プロパティ | 重要度 |
|-----------|--------|
| evidence_id, metric_name, value, created_at | 必須 |
| market, is_oos, unit | 推奨 |
| benchmark, benchmark_value, period_start, period_end, sample_size | 任意 |

**MarketRegime の充填率**:

```cypher
MATCH (mr:MarketRegime)
RETURN
    count(mr) AS total,
    count(mr.regime_id) AS has_id,
    count(mr.name) AS has_name,
    count(mr.regime_type) AS has_regime_type,
    count(mr.created_at) AS has_created_at,
    count(mr.description) AS has_description
```

| プロパティ | 重要度 |
|-----------|--------|
| regime_id, name, regime_type, created_at | 必須 |
| description | 推奨 |

**DataRequirement の充填率**:

```cypher
MATCH (dr:DataRequirement)
RETURN
    count(dr) AS total,
    count(dr.data_req_id) AS has_id,
    count(dr.name) AS has_name,
    count(dr.data_type) AS has_data_type,
    count(dr.created_at) AS has_created_at,
    count(dr.availability) AS has_availability,
    count(dr.frequency) AS has_frequency,
    count(dr.min_history) AS has_min_history
```

| プロパティ | 重要度 |
|-----------|--------|
| data_req_id, name, data_type, created_at | 必須 |
| availability, frequency | 推奨 |
| min_history | 任意 |

**スコア算出**:
- 各ノードの加重充填率を計算: Σ(充填率 × 重み) / Σ(重み)
- 全14ノードの平均がカテゴリスコア

---

### 1.2 Consistency（一貫性）— 重み 18%

ID フォーマット、enum 値、リレーションタイプの妥当性を検証する。

#### ID フォーマット検証

```cypher
MATCH (m:Method)
WHERE m.method_id IS NOT NULL AND NOT m.method_id =~ 'method-.+'
RETURN m.method_id AS invalid_id, m.name AS name
```

```cypher
MATCH (a:Anomaly)
WHERE a.anomaly_id IS NOT NULL AND NOT a.anomaly_id =~ 'anomaly-.+'
RETURN a.anomaly_id AS invalid_id, a.name AS name
```

```cypher
MATCH (pe:PerformanceEvidence)
WHERE pe.evidence_id IS NOT NULL AND NOT pe.evidence_id =~ 'perf-.+-.+-[a-f0-9]{8}'
RETURN pe.evidence_id AS invalid_id, pe.metric_name AS metric
```

```cypher
MATCH (mr:MarketRegime)
WHERE mr.regime_id IS NOT NULL AND NOT mr.regime_id =~ 'regime-.+'
RETURN mr.regime_id AS invalid_id, mr.name AS name
```

```cypher
MATCH (dr:DataRequirement)
WHERE dr.data_req_id IS NOT NULL AND NOT dr.data_req_id =~ 'datareq-.+'
RETURN dr.data_req_id AS invalid_id, dr.name AS name
```

```cypher
MATCH (i:Insight)
WHERE i.insight_id IS NOT NULL AND NOT i.insight_id =~ 'ins-\\d{4}-\\d{2}-\\d{2}-.+'
RETURN i.insight_id AS invalid_id, left(i.content, 80) AS content
```

```cypher
MATCH (fp:FiscalPeriod)
WHERE fp.period_id IS NOT NULL AND NOT fp.period_id =~ '[A-Z0-9]+_.+'
RETURN fp.period_id AS invalid_id, fp.period_label AS label
```

#### Enum 値検証

```cypher
MATCH (s:Source)
WHERE s.source_type IS NOT NULL
AND NOT s.source_type IN ['web', 'news', 'report', 'original', 'paper', 'code', 'documentation']
RETURN s.source_id AS id, s.source_type AS invalid_value
```

```cypher
MATCH (e:Entity)
WHERE e.entity_type IS NOT NULL
AND NOT e.entity_type IN ['company', 'index', 'sector', 'indicator', 'currency', 'commodity', 'person', 'organization', 'country', 'instrument']
RETURN e.entity_id AS id, e.entity_type AS invalid_value
```

```cypher
MATCH (c:Claim)
WHERE c.claim_type IS NOT NULL
AND NOT c.claim_type IN ['opinion', 'prediction', 'recommendation', 'analysis', 'assumption', 'guidance', 'risk_assessment', 'policy_stance', 'sector_view', 'forecast']
RETURN c.claim_id AS id, c.claim_type AS invalid_value
```

```cypher
MATCH (c:Claim)
WHERE c.sentiment IS NOT NULL
AND NOT c.sentiment IN ['bullish', 'bearish', 'neutral', 'mixed']
RETURN c.claim_id AS id, c.sentiment AS invalid_value
```

```cypher
MATCH (c:Claim)
WHERE c.confidence IS NOT NULL
AND NOT c.confidence IN ['high', 'medium', 'low']
RETURN c.claim_id AS id, c.confidence AS invalid_value
```

```cypher
MATCH (f:Fact)
WHERE f.fact_type IS NOT NULL
AND NOT f.fact_type IN ['statistic', 'event', 'data_point', 'quote', 'policy_action', 'economic_indicator', 'regulatory', 'corporate_action']
RETURN f.fact_id AS id, f.fact_type AS invalid_value
```

```cypher
MATCH (m:Method)
WHERE m.method_type IS NOT NULL
AND NOT m.method_type IN ['architecture', 'algorithm', 'framework', 'technique', 'model', 'deep-learning', 'graph-construction', 'reasoning', 'stochastic-process', 'representation-learning', 'generative-model', 'causal-inference', 'optimization', 'protocol']
RETURN m.method_id AS id, m.method_type AS invalid_value
```

```cypher
MATCH (a:Anomaly)
WHERE a.anomaly_type IS NOT NULL
AND NOT a.anomaly_type IN ['behavioral', 'structural', 'informational', 'microstructure', 'regulatory']
RETURN a.anomaly_id AS id, a.anomaly_type AS invalid_value
```

```cypher
MATCH (a:Anomaly)
WHERE a.persistence IS NOT NULL
AND NOT a.persistence IN ['persistent', 'decaying', 'debated', 'regime_dependent']
RETURN a.anomaly_id AS id, a.persistence AS invalid_value
```

```cypher
MATCH (i:Insight)
WHERE i.status IS NOT NULL
AND NOT i.status IN ['draft', 'validated', 'invalidated', 'archived']
RETURN i.insight_id AS id, i.status AS invalid_value
```

```cypher
MATCH (mr:MarketRegime)
WHERE mr.regime_type IS NOT NULL
AND NOT mr.regime_type IN ['volatility', 'monetary_policy', 'economic_cycle', 'sentiment', 'liquidity', 'correlation']
RETURN mr.regime_id AS id, mr.regime_type AS invalid_value
```

```cypher
MATCH (dr:DataRequirement)
WHERE dr.data_type IS NOT NULL
AND NOT dr.data_type IN ['price', 'fundamental', 'alternative', 'text', 'graph', 'macro', 'options', 'corporate_action']
RETURN dr.data_req_id AS id, dr.data_type AS invalid_value
```

```cypher
MATCH (dr:DataRequirement)
WHERE dr.availability IS NOT NULL
AND NOT dr.availability IN ['free', 'commercial', 'proprietary', 'mixed']
RETURN dr.data_req_id AS id, dr.availability AS invalid_value
```

#### 異常リレーション検出

```cypher
MATCH (a)-[r:STATES_FACT]->(b)
WHERE NOT (a:Source AND b:Fact)
RETURN labels(a) AS from_labels, type(r) AS rel_type, labels(b) AS to_labels
```

```cypher
MATCH (a)-[r:MAKES_CLAIM]->(b)
WHERE NOT (a:Source AND b:Claim)
RETURN labels(a) AS from_labels, type(r) AS rel_type, labels(b) AS to_labels
```

```cypher
MATCH (a)-[r:ABOUT]->(b)
WHERE NOT (a:Claim AND b:Entity)
RETURN labels(a) AS from_labels, type(r) AS rel_type, labels(b) AS to_labels
```

```cypher
MATCH ()-[r]->()
WHERE NOT type(r) IN [
    'STATES_FACT', 'MAKES_CLAIM', 'ABOUT', 'RELATES_TO', 'TAGGED',
    'AUTHORED_BY', 'SUPPORTED_BY', 'CONTRADICTS', 'HAS_DATAPOINT',
    'FOR_PERIOD', 'NEXT_PERIOD', 'TREND', 'DERIVED_FROM', 'VALIDATES',
    'CHALLENGES', 'USES_METHOD', 'EXTENDS_METHOD', 'COMBINED_WITH',
    'EXPLOITS', 'EVALUATES', 'QUANTIFIED_BY', 'EFFECTIVE_IN',
    'REQUIRES_DATA', 'EXPLAINED_BY', 'MEASURED_IN', 'COMPETES_WITH',
    'CITES', 'COAUTHORED_WITH', 'SUBTOPIC_OF', 'AFFILIATED_WITH', 'CAUSES'
]
RETURN type(r) AS unknown_rel_type, count(*) AS cnt
```

**スコア算出**:
- 不正 ID 率、不正 enum 率、異常リレーション率の逆数の平均
- スコア = 1.0 - (不正率の加重平均)

---

### 1.3 Orphan 検出（孤立ノード）— 重み 13%

リレーションを持たないノードを検出する。

```cypher
MATCH (c:Claim)
WHERE NOT (c)<-[:MAKES_CLAIM]-()
RETURN c.claim_id AS id, left(c.content, 80) AS content
```

```cypher
MATCH (c:Claim)
WHERE NOT (c)-[:ABOUT]->()
RETURN c.claim_id AS id, left(c.content, 80) AS content
```

```cypher
MATCH (f:Fact)
WHERE NOT (f)<-[:STATES_FACT]-()
RETURN f.fact_id AS id, left(f.content, 80) AS content
```

```cypher
MATCH (dp:FinancialDataPoint)
WHERE NOT (dp)<-[:HAS_DATAPOINT]-()
RETURN dp.datapoint_id AS id, dp.metric_name AS metric
```

```cypher
MATCH (dp:FinancialDataPoint)
WHERE NOT (dp)-[:FOR_PERIOD]->()
RETURN dp.datapoint_id AS id, dp.metric_name AS metric
```

```cypher
MATCH (s:Source)
WHERE NOT (s)-[:STATES_FACT]->()
AND NOT (s)-[:MAKES_CLAIM]->()
AND NOT (s)-[:HAS_DATAPOINT]->()
RETURN s.source_id AS id, s.title AS title, s.source_type AS source_type
```

```cypher
MATCH (pe:PerformanceEvidence)
WHERE NOT (pe)-[:EVALUATES]->()
RETURN pe.evidence_id AS id, pe.metric_name AS metric
```

```cypher
MATCH (m:Method)
WHERE NOT (m)<-[:USES_METHOD]-()
RETURN m.method_id AS id, m.name AS name
```

```cypher
MATCH (t:Topic)
WHERE NOT (t)<-[:TAGGED]-()
RETURN t.topic_id AS id, t.name AS name
```

**スコア算出**:
- 孤立率 = 孤立ノード数 / 全対象ノード数
- スコア = 1.0 - 孤立率（0.0 以上にクランプ）

---

### 1.4 Staleness（鮮度）— 重み 8%

古くなったデータを検出する。

**30日以上 draft の Insight**:

```cypher
MATCH (i:Insight)
WHERE i.status = 'draft' AND i.generated_at IS NOT NULL
AND datetime(i.generated_at) < datetime() - duration('P30D')
RETURN i.insight_id AS id, left(i.content, 80) AS content,
       toString(i.generated_at) AS generated_at
```

**90日以上前に取得され未抽出の Source**:

```cypher
MATCH (s:Source)
WHERE s.fetched_at IS NOT NULL
AND datetime(s.fetched_at) < datetime() - duration('P90D')
AND NOT (s)-[:STATES_FACT]->()
AND NOT (s)-[:MAKES_CLAIM]->()
AND NOT (s)-[:HAS_DATAPOINT]->()
RETURN s.source_id AS id, s.title AS title,
       toString(s.fetched_at) AS fetched_at, s.source_type AS source_type
```

**3年以上前の evaluation period を持つ PerformanceEvidence**:

```cypher
MATCH (pe:PerformanceEvidence)
WHERE pe.period_end IS NOT NULL AND pe.period_end < '2023-01'
RETURN pe.evidence_id AS id, pe.metric_name AS metric,
       pe.period_start AS start, pe.period_end AS end_period
```

**スコア算出**:
- stale率 = staleアイテム数 / 該当ステータスのアイテム数
- スコア = 1.0 - stale率

---

### 1.5 Structural（構造）— 重み 9%

グラフ構造の統計を計測する。

**Entity あたりの Claim 数**:

```cypher
MATCH (e:Entity)
OPTIONAL MATCH (e)<-[:ABOUT]-(c:Claim)
WITH e, count(c) AS claim_count
RETURN
    avg(claim_count) AS avg_claims,
    max(claim_count) AS max_claims,
    min(claim_count) AS min_claims,
    percentileCont(claim_count, 0.5) AS median_claims
```

**Topic あたりの Source 数**:

```cypher
MATCH (t:Topic)
OPTIONAL MATCH (t)<-[:TAGGED]-(s:Source)
WITH t, count(s) AS source_count
RETURN
    avg(source_count) AS avg_sources,
    max(source_count) AS max_sources,
    min(source_count) AS min_sources,
    percentileCont(source_count, 0.5) AS median_sources
```

**Method-Anomaly カバレッジ**:

```cypher
MATCH (m:Method)
OPTIONAL MATCH (m)-[:EXPLOITS]->(a:Anomaly)
RETURN
    count(m) AS total_methods,
    count(DISTINCT CASE WHEN a IS NOT NULL THEN m END) AS methods_with_anomaly,
    count(DISTINCT a) AS anomalies_covered
```

**Method あたりの PerformanceEvidence 数**:

```cypher
MATCH (m:Method)
OPTIONAL MATCH (pe:PerformanceEvidence)-[:EVALUATES]->(m)
WITH m, count(pe) AS evidence_count
RETURN
    avg(evidence_count) AS avg_evidence,
    max(evidence_count) AS max_evidence,
    sum(CASE WHEN evidence_count = 0 THEN 1 ELSE 0 END) AS methods_without_evidence
```

**ノードタイプ分布**:

```cypher
MATCH (n)
WHERE NOT 'Memory' IN labels(n)
RETURN labels(n)[0] AS label, count(n) AS cnt
ORDER BY cnt DESC
```

**リレーションタイプ分布**:

```cypher
MATCH ()-[r]->()
RETURN type(r) AS rel_type, count(*) AS cnt
ORDER BY cnt DESC
```

**Top Entity ハブ（最も接続数が多い Entity 上位10）**:

```cypher
MATCH (e:Entity)
OPTIONAL MATCH (e)<-[:ABOUT]-(c:Claim)
OPTIONAL MATCH (e)<-[:RELATES_TO]-(f)
WITH e, count(DISTINCT c) AS claims, count(DISTINCT f) AS facts_dps
RETURN e.name AS entity, e.entity_type AS type,
       claims, facts_dps, claims + facts_dps AS total_connections
ORDER BY total_connections DESC LIMIT 10
```

**スコア算出**:
- 接続 0 の Entity の割合で減点
- 過度に集中（1 Entity に全 Claim の50%以上）がある場合も減点
- PerformanceEvidence がない Method の割合で減点

---

### 1.6 Schema Compliance（スキーマ準拠）— 重み 5%

グラフが `data/config/knowledge-graph-schema.yaml` に準拠しているか検証する。

**不明ノードラベル検出**:

```cypher
CALL db.labels() YIELD label
WHERE NOT label IN [
    'Source', 'Entity', 'Claim', 'Fact', 'FinancialDataPoint', 'FiscalPeriod',
    'Topic', 'Author', 'Insight', 'Method', 'Anomaly', 'PerformanceEvidence',
    'MarketRegime', 'DataRequirement',
    'Discussion', 'Decision', 'ActionItem', 'Project',
    'Memory', 'Archived'
]
RETURN label AS unknown_label
```

**UNIQUE 制約確認**:

```cypher
SHOW CONSTRAINTS
YIELD name, labelsOrTypes, properties, type
WHERE type = 'UNIQUENESS'
RETURN name, labelsOrTypes, properties
```

14制約（Source〜DataRequirement）の存在を確認する。

**PascalCase 違反検出**:

```cypher
CALL db.labels() YIELD label
WHERE label =~ '^[a-z].*'
RETURN label AS pascal_violation
```

**スコア算出**:
- 不明ラベル 0 & 14制約存在 & PascalCase 違反 0 = 100%
- 各違反につき比例減点

---

### 1.7 Research Paper Quality（研究論文品質）— 重み 15%

論文系 Source（`source_type` が `paper` または `report`）に特化した品質チェック。6つのサブチェックで構成される。

#### 内部重み

| チェック | 内部重み |
|---------|---------|
| A. source_type別ブレークダウン | 20% |
| B. スキーマドリフト検出 | 15% |
| C. Author整合性 | 20% |
| D. パイプライン別品質差分 | 20% |
| E. 重複Source検出 | 10% |
| F. 引用ネットワーク密度 | 15% |
| **合計** | **100%** |

#### スコア算出式

全チェックで統一式 `max(0, 1.0 - 問題件数 / 総対象件数)` を基本とする。

- **A**: `0.4 × プロパティ充填率 + 0.6 × 接続率`。充填率 = paper/report の `abstract`, `venue`, `published_at` の加重充填率（重み: 推奨=0.7）。接続率 = AUTHORED_BY/MAKES_CLAIM/USES_METHOD のいずれかを持つ割合。paper と report は件数比例で加重。
- **B**: `max(0, 1.0 - 未定義プロパティ種類数 / 全プロパティ種類数)`。1種類でも未定義があれば減点。
- **C**: `max(0, 1.0 - authors文字列のみの件数 / authors文字列を持つ総件数)`。
- **D**: `max(0, 1.0 - |connected接続率 - unconnected接続率|)`。接続率 = 3リレーション（AUTHORED_BY, MAKES_CLAIM, USES_METHOD）のいずれかを持つ割合。connected = `arxiv-*` + `jsai2026-*`/UUID、unconnected = `src-*`。**注**: このチェックはパイプライン間の**均一性**を計測する。絶対的な接続品質はチェック A がカバーするため、A と D は相補的に機能する。
- **E**: `max(0, 1.0 - 重複URLペア数 / 総Source件数)`。
- **F**: `min(1.0, CITES件数 / 論文件数)`。密度1.0以上は1.0にクランプ。

#### A. source_type別ブレークダウン

**充填率**:

```cypher
MATCH (s:Source)
WHERE s.source_type IN ['paper', 'report']
RETURN s.source_type AS type, count(s) AS total,
       count(s.abstract) AS has_abstract,
       count(s.venue) AS has_venue,
       count(s.published_at) AS has_published_at,
       count(s.fetched_at) AS has_fetched_at
```

**接続率**:

```cypher
MATCH (s:Source)
WHERE s.source_type IN ['paper', 'report']
OPTIONAL MATCH (s)-[:AUTHORED_BY]->(a:Author)
OPTIONAL MATCH (s)-[:MAKES_CLAIM]->(c:Claim)
OPTIONAL MATCH (s)-[:USES_METHOD]->(m:Method)
WITH s, count(DISTINCT a) AS authors, count(DISTINCT c) AS claims, count(DISTINCT m) AS methods
RETURN s.source_type AS type,
       count(s) AS total,
       sum(CASE WHEN authors > 0 THEN 1 ELSE 0 END) AS with_authors,
       sum(CASE WHEN claims > 0 THEN 1 ELSE 0 END) AS with_claims,
       sum(CASE WHEN methods > 0 THEN 1 ELSE 0 END) AS with_methods
```

#### B. スキーマドリフト検出

Source 上の全プロパティキーを収集し、スキーマ定義プロパティリストと比較する。

```cypher
MATCH (s:Source)
WITH s, keys(s) AS props
UNWIND props AS prop
WHERE NOT prop IN [
    'source_id','title','url','source_type','publisher',
    'published_at','fetched_at','language','category',
    'command_source','abstract','venue'
]
RETURN prop AS undeclared_property, count(*) AS cnt
ORDER BY cnt DESC
```

#### C. Author文字列↔リレーション整合性

`authors` 文字列プロパティを持つが AUTHORED_BY リレーションがない Source を検出する。

```cypher
MATCH (s:Source)
WHERE s.source_type IN ['paper', 'report']
AND s.authors IS NOT NULL
AND NOT (s)-[:AUTHORED_BY]->()
RETURN count(s) AS papers_with_string_only,
       collect(s.source_id)[..10] AS sample_ids
```

#### D. パイプライン別品質差分

`src-*` prefix（unconnected）とそれ以外（connected）の接続率を比較する。

```cypher
MATCH (s:Source)
WHERE s.source_type IN ['paper', 'report']
WITH s,
     CASE WHEN s.source_id STARTS WITH 'src-' THEN 'unconnected'
          ELSE 'connected' END AS pipeline
OPTIONAL MATCH (s)-[:AUTHORED_BY]->(a:Author)
OPTIONAL MATCH (s)-[:MAKES_CLAIM]->(c:Claim)
OPTIONAL MATCH (s)-[:USES_METHOD]->(m:Method)
WITH pipeline, s,
     count(DISTINCT a) AS authors,
     count(DISTINCT c) AS claims,
     count(DISTINCT m) AS methods
RETURN pipeline, count(s) AS total,
       sum(CASE WHEN authors > 0 THEN 1 ELSE 0 END) AS with_authors,
       sum(CASE WHEN claims > 0 THEN 1 ELSE 0 END) AS with_claims,
       sum(CASE WHEN methods > 0 THEN 1 ELSE 0 END) AS with_methods
```

#### E. 重複Source検出

同一URLで異なる source_id を持つノードを検出する。

```cypher
MATCH (s:Source)
WHERE s.url IS NOT NULL
WITH s.url AS url, collect(s.source_id) AS ids, count(s) AS cnt
WHERE cnt > 1
RETURN url, ids
```

#### F. 引用ネットワーク密度

論文間の CITES リレーションの密度を計測する。

```cypher
MATCH (s:Source)
WHERE s.source_type IN ['paper', 'report']
WITH count(s) AS paper_count
CALL {
    MATCH ()-[r:CITES]->()
    RETURN count(r) AS cites_count
}
RETURN paper_count, cites_count,
       toFloat(cites_count) / paper_count AS density
```

**スコア算出**:
- 各サブチェックのスコアを算出し、内部重みで加重平均してカテゴリスコアとする

---

## Phase 2: LLM-as-Judge（重み 12%）

Claude Code が直接、Claim/Fact の精度とグラフの創発的発見ポテンシャルを評価する。

### 2.1 Claim/Fact 精度（6.5%）

`mcp__neo4j-cypher__read_neo4j_cypher` で Claim/Fact をサンプリングし、3軸で評価する。

**Claim サンプリング**:

```cypher
MATCH (c:Claim)<-[:MAKES_CLAIM]-(s:Source)
WHERE c.content IS NOT NULL
RETURN c.claim_id AS id, c.content AS content, c.claim_type AS type,
       c.sentiment AS sentiment, c.confidence AS confidence,
       s.title AS source_title, s.url AS source_url
ORDER BY rand() LIMIT 10
```

**Fact サンプリング**:

```cypher
MATCH (f:Fact)<-[:STATES_FACT]-(s:Source)
WHERE f.content IS NOT NULL
RETURN f.fact_id AS id, f.content AS content, f.fact_type AS type,
       toString(f.as_of_date) AS as_of_date,
       s.title AS source_title, s.url AS source_url
ORDER BY rand() LIMIT 10
```

各サンプルを以下の3軸で評価（0.0-1.0）:

| 軸 | 重み | 評価基準 |
|---|---:|---|
| Factual Correctness | 40% | 内容が事実として正確か、具体的な数値・名称を含むか |
| Source Grounding | 30% | Source の URL/title と紐づき、内容が Source と整合するか |
| Temporal Validity | 30% | 時間的に有効な情報か（歴史データ: 高、デイリーニュース: 低） |

**評価の目安**:
- **0.8-1.0**: 具体的で正確、Source と整合、時間的に適切
- **0.5-0.7**: おおむね正確だが、やや曖昧 or Source 情報が不十分
- **0.2-0.4**: 不正確 or Source との不整合あり
- **0.0-0.1**: 無関係 or ノイズデータ

### 2.2 創発的発見ポテンシャル（5.5%）

4つの構造プローブを実行し、仮説を生成して自己評価する。

**Probe A: Cross-Domain Bridge** — 異なる entity_type 間で共有される Fact:

```cypher
MATCH (e1:Entity)<-[:RELATES_TO]-(f:Fact)-[:RELATES_TO]->(e2:Entity)
WHERE e1.entity_type <> e2.entity_type
AND elementId(e1) < elementId(e2)
RETURN e1.name + ' (' + e1.entity_type + ')' AS entity1,
       e2.name + ' (' + e2.entity_type + ')' AS entity2,
       count(DISTINCT f) AS shared_facts,
       collect(DISTINCT f.content)[..2] AS sample_content
ORDER BY shared_facts DESC LIMIT 10
```

**Probe B: Method-Anomaly-Regime Traversal** — AI戦略発見チェーン:

```cypher
MATCH (m:Method)-[:EXPLOITS]->(a:Anomaly)
OPTIONAL MATCH (pe:PerformanceEvidence)-[:EVALUATES]->(m)
OPTIONAL MATCH (m)-[:EFFECTIVE_IN]->(mr:MarketRegime)
RETURN m.name AS method, a.name AS anomaly,
       collect(DISTINCT pe.metric_name + ': ' + toString(pe.value))[..3] AS evidence,
       collect(DISTINCT mr.name)[..3] AS effective_regimes
ORDER BY m.name LIMIT 10
```

**Probe C: Contradicting Claims**:

```cypher
MATCH (c1:Claim)-[:CONTRADICTS]->(c2:Claim)
OPTIONAL MATCH (c1)-[:ABOUT]->(e:Entity)
RETURN c1.claim_id AS claim1_id, left(c1.content, 80) AS claim1,
       c2.claim_id AS claim2_id, left(c2.content, 80) AS claim2,
       collect(DISTINCT e.name)[..3] AS entities
LIMIT 5
```

**Probe D: Multi-Topic Entities** — 複数カテゴリにまたがる Entity:

```cypher
MATCH (e:Entity)<-[:RELATES_TO|ABOUT]-(node)-[:TAGGED]->(t:Topic)
WHERE t.category IS NOT NULL
WITH e, collect(DISTINCT t.category) AS categories, count(DISTINCT t) AS topic_count
WHERE size(categories) >= 2
RETURN e.name AS entity, e.entity_type AS type, categories, topic_count
ORDER BY topic_count DESC LIMIT 10
```

プローブ結果から **3つ以上の仮説** を構築し、以下の4軸で自己評価（0.0-1.0）:

| 軸 | 重み | 評価基準 |
|---|---:|---|
| Cross-Domain Bridging | 30% | グラフがドメインをまたぐインサイトを表面化できるか |
| Hypothesis Novelty | 25% | 生成された仮説が非自明か |
| Evidence Density | 25% | 仮説を裏付ける Fact/Claim/DataPoint が十分あるか |
| Actionability | 20% | 発見がアクショナブルな研究方向につながるか |

---

## Phase 3: レポート出力

以下の Markdown 形式でユーザーに提示する。

```markdown
## KG v2.2 品質チェックレポート

**計測日時**: YYYY-MM-DD HH:MM
**スキーマバージョン**: v2.2
**ノード数**: Source XX / Entity XX / Claim XX / Fact XX / FinancialDataPoint XX / FiscalPeriod XX / Topic XX / Author XX / Insight XX / Method XX / Anomaly XX / PerformanceEvidence XX / MarketRegime XX / DataRequirement XX
**リレーション数**: XX

### 1. Completeness（完全性）スコア: XX%

| ラベル | プロパティ | 充填数/総数 | 充填率 | 重要度 |
|--------|-----------|------------|--------|--------|
| Source | source_id | XX/XX | 100% | 必須 |
| Source | title | XX/XX | XX% | 必須 |
...

### 2. Consistency（一貫性）スコア: XX%

- 不正 ID フォーマット: N件
  - [詳細リスト]
- 不正 enum 値: N件
  - [詳細リスト]
- 異常リレーション: N件
  - [詳細リスト]
- 不明リレーションタイプ: N件

### 3. 孤立ノード スコア: XX%

- Source（未抽出）: N件
- Claim（Source なし）: N件
- Claim（Entity なし）: N件
- Fact（Source なし）: N件
- FinancialDataPoint（Source なし）: N件
- FinancialDataPoint（Period なし）: N件
- PerformanceEvidence（Method なし）: N件
- Method（Source なし）: N件
- Topic（未使用）: N件

### 4. Staleness（鮮度）スコア: XX%

- 30日以上 draft の Insight: N件
  - [ID, content の先頭80文字, generated_at]
- 90日以上未抽出の Source: N件
  - [ID, title, fetched_at]
- 古い PerformanceEvidence: N件
  - [ID, metric, period]

### 5. 構造分析 スコア: XX%

- Entity あたり平均 Claim 数: X.X
- Topic あたり平均 Source 数: X.X
- Method-Anomaly カバレッジ: X/Y Methods, Z Anomalies
- PerformanceEvidence がない Method: N件

| Entity | Type | Claims | Facts/DPs | 合計 |
|--------|------|--------|-----------|------|
| ... | ... | ... | ... | ... |

### 6. Schema Compliance スコア: XX%

- 不明ラベル: N件
- PascalCase 違反: N件
- UNIQUE 制約: X/14 存在

### 7. LLM-as-Judge スコア: XX%

#### Claim/Fact 精度

| ID | Factual | Grounding | Temporal | 総合 | 備考 |
|----|---------|-----------|----------|------|------|
| ... | ... | ... | ... | ... | ... |

平均スコア: X.XX

#### 創発的発見ポテンシャル

| 軸 | スコア |
|----|--------|
| Cross-Domain Bridging | X.X |
| Hypothesis Novelty | X.X |
| Evidence Density | X.X |
| Actionability | X.X |
| 総合 | X.XX |

発見した仮説:
1. [仮説タイトル] - [要約]
2. ...
3. ...

### 8. Research Paper Quality スコア: XX%

#### source_type別充填率
| type | total | abstract | venue | published_at |
|------|-------|----------|-------|-------------|
| paper | XX | XX% | XX% | XX% |
| report | XX | XX% | XX% | XX% |

#### パイプライン別接続率
| pipeline | total | AUTHORED_BY | MAKES_CLAIM | USES_METHOD |
|----------|-------|-------------|-------------|-------------|
| connected | XX | XX% | XX% | XX% |
| unconnected | XX | XX% | XX% | XX% |

#### スキーマドリフト
| プロパティ | 件数 | 対応 |
|-----------|------|------|
| ... | XX | ... |

#### Author整合性
- authors文字列のみ（リレーションなし）: N件

#### 重複Source
- 重複URL: N件

#### 引用ネットワーク密度
- CITES: N件 / 論文 N件 = X.X%

### 総合スコア: XX/100

| カテゴリ | スコア | 重み | 加重スコア |
|---------|--------|------|-----------|
| Completeness | XX% | 20% | XX |
| Consistency | XX% | 18% | XX |
| Orphan | XX% | 13% | XX |
| Staleness | XX% | 8% | XX |
| Structural | XX% | 9% | XX |
| Schema Compliance | XX% | 5% | XX |
| LLM-as-Judge | XX% | 12% | XX |
| Research Paper Quality | XX% | 15% | XX |

Rating: A (85+) / B (70-84) / C (50-69) / D (<50)

### 改善提案

1. [優先度: 高] ...
2. [優先度: 中] ...
3. [優先度: 低] ...
```

## 使用する MCP ツール

| MCP ツール | 用途 |
|-----------|------|
| `mcp__neo4j-cypher__read_neo4j_cypher` | 全ての Cypher クエリ実行（読み取りのみ） |

**注意**: `mcp__neo4j-cypher__write_neo4j_cypher` は一切使用しない。

## 関連ファイル

| ファイル | 説明 |
|---------|------|
| `.claude/commands/kg-quality-check.md` | スラッシュコマンド |
| `data/config/knowledge-graph-schema.yaml` | スキーマ SSoT（enum 値の正規リスト） |
| `.claude/rules/neo4j-namespace-convention.md` | 名前空間・命名規約 |
| `scripts/validate_neo4j_schema.py` | 既存スキーマ検証スクリプト（補完関係） |
| `.claude/skills/save-to-graph/SKILL.md` | グラフ投入スキル |

## MUST / SHOULD / NEVER

### MUST

- Phase 1 の6カテゴリ全ての Cypher プローブを実行すること
- Phase 2 の LLM-as-Judge 評価を Claim/Fact 精度と創発的発見の両方に実施すること
- 全ての Cypher は `mcp__neo4j-cypher__read_neo4j_cypher` で実行すること
- レポートに総合スコア（100点満点）と Rating を算出すること
- 問題が見つかった場合は具体的な改善提案を含めること

### SHOULD

- 各カテゴリでスコアが50%未満の場合は警告マーク付きで報告すること
- 前回レポートが存在する場合は比較を行うこと
- 改善提案に優先度（高/中/低）を付けること
- ノード数が 0 のノードタイプは計測をスキップし、レポートに「データなし」と記載すること

### NEVER

- `mcp__neo4j-cypher__write_neo4j_cypher` を使用してはならない（読み取り専用）
- データを修正してはならない（検出と報告のみ）
- Memory ノードを品質チェック対象に含めてはならない（`WHERE NOT 'Memory' IN labels(n)` で除外）

## 完了条件

- [ ] 6カテゴリの Cypher プローブが全て実行されている
- [ ] LLM-as-Judge による Claim/Fact 精度評価が実施されている
- [ ] 創発的発見ポテンシャル評価が実施されている
- [ ] 総合スコア（100点満点）と Rating が算出されている
- [ ] 問題点と改善提案を含む Markdown レポートがユーザーに提示されている
