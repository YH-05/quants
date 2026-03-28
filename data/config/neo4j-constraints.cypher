// Neo4j constraints and indices for quants knowledge graph
// KG Schema v2.0 — 14 UNIQUE constraints + 22 indices
// All queries use IF NOT EXISTS for idempotency
//
// Reference: data/config/knowledge-graph-schema.yaml (constraints / indices sections)

// ============================================================
// UNIQUE Constraints (14)
// ============================================================

// --- v1.0 original (9) ---

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

// --- v1.1 addition (1) ---

CREATE CONSTRAINT unique_method_id IF NOT EXISTS
  FOR (m:Method) REQUIRE m.method_id IS UNIQUE;

// --- v2.0 additions (4) ---

CREATE CONSTRAINT unique_anomaly_id IF NOT EXISTS
  FOR (n:Anomaly) REQUIRE n.anomaly_id IS UNIQUE;

CREATE CONSTRAINT unique_evidence_id IF NOT EXISTS
  FOR (n:PerformanceEvidence) REQUIRE n.evidence_id IS UNIQUE;

CREATE CONSTRAINT unique_regime_id IF NOT EXISTS
  FOR (n:MarketRegime) REQUIRE n.regime_id IS UNIQUE;

CREATE CONSTRAINT unique_data_req_id IF NOT EXISTS
  FOR (n:DataRequirement) REQUIRE n.data_req_id IS UNIQUE;

// ============================================================
// Indices (22)
// ============================================================

// --- v1.0 original (13) ---

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

// --- v1.1 addition (1) ---

CREATE INDEX idx_method_method_type IF NOT EXISTS
  FOR (m:Method) ON (m.method_type);

// --- v2.0 additions (8) ---

CREATE INDEX idx_anomaly_type IF NOT EXISTS
  FOR (n:Anomaly) ON (n.anomaly_type);

CREATE INDEX idx_anomaly_persistence IF NOT EXISTS
  FOR (n:Anomaly) ON (n.persistence);

CREATE INDEX idx_perf_metric IF NOT EXISTS
  FOR (n:PerformanceEvidence) ON (n.metric_name);

CREATE INDEX idx_perf_market IF NOT EXISTS
  FOR (n:PerformanceEvidence) ON (n.market);

CREATE INDEX idx_perf_oos IF NOT EXISTS
  FOR (n:PerformanceEvidence) ON (n.is_oos);

CREATE INDEX idx_regime_type IF NOT EXISTS
  FOR (n:MarketRegime) ON (n.regime_type);

CREATE INDEX idx_datareq_type IF NOT EXISTS
  FOR (n:DataRequirement) ON (n.data_type);

CREATE INDEX idx_datareq_avail IF NOT EXISTS
  FOR (n:DataRequirement) ON (n.availability);
