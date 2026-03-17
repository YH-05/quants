// Neo4j constraints and indices for quants knowledge graph
// KG Schema v1 — 9 UNIQUE constraints + 13 indices
// All queries use IF NOT EXISTS for idempotency
//
// Reference: data/config/knowledge-graph-schema.yaml (constraints / indices sections)

// ============================================================
// UNIQUE Constraints (9)
// ============================================================

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

// ============================================================
// Indices (13)
// ============================================================

CREATE INDEX idx_fact_fact_type IF NOT EXISTS
  FOR (f:Fact) ON (f.fact_type);

CREATE INDEX idx_fact_as_of_date IF NOT EXISTS
  FOR (f:Fact) ON (f.as_of_date);

CREATE INDEX idx_claim_claim_type IF NOT EXISTS
  FOR (c:Claim) ON (c.claim_type);

CREATE INDEX idx_claim_sentiment IF NOT EXISTS
  FOR (c:Claim) ON (c.sentiment);

CREATE INDEX idx_entity_entity_type IF NOT EXISTS
  FOR (e:Entity) ON (e.entity_type);

CREATE INDEX idx_entity_ticker IF NOT EXISTS
  FOR (e:Entity) ON (e.ticker);

CREATE INDEX idx_datapoint_metric_name IF NOT EXISTS
  FOR (dp:FinancialDataPoint) ON (dp.metric_name);

CREATE INDEX idx_datapoint_is_estimate IF NOT EXISTS
  FOR (dp:FinancialDataPoint) ON (dp.is_estimate);

CREATE INDEX idx_period_period_label IF NOT EXISTS
  FOR (fp:FiscalPeriod) ON (fp.period_label);

CREATE INDEX idx_insight_insight_type IF NOT EXISTS
  FOR (i:Insight) ON (i.insight_type);

CREATE INDEX idx_insight_status IF NOT EXISTS
  FOR (i:Insight) ON (i.status);

CREATE INDEX idx_source_source_type IF NOT EXISTS
  FOR (s:Source) ON (s.source_type);

CREATE INDEX idx_source_command_source IF NOT EXISTS
  FOR (s:Source) ON (s.command_source);
