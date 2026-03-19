# v2 ノード自動抽出プロンプトテンプレート

論文・レポートをKGに投入する際、v1ノード（Source, Claim, Method等）と同時にv2ノード（Anomaly, PerformanceEvidence, MarketRegime, DataRequirement）を抽出するためのプロンプト。

## 使用タイミング

- `emit_graph_queue.py` のマッパー内でLLM抽出を行う場合
- 手動で論文をKGに投入する際のガイド
- graph-queue JSONを手書きする際の参照

## 抽出プロンプト

以下のプロンプトを論文/レポートの要約・主張と共に使用する。

---

### System Prompt

```
あなたはクオンツ投資のナレッジグラフ構築エキスパートです。
論文・レポートから以下の4種類のv2ノードを構造化抽出してください。
既存ノードとの重複を避けるため、既知のID一覧を参照してください。
```

### User Prompt Template

```
以下の論文情報からv2ナレッジグラフノードを抽出してください。

## 論文情報
タイトル: {title}
著者: {authors}
手法: {method_names} (既存method_id: {method_ids})
主張: {claims_content}

## 抽出対象

### 1. Anomaly（この手法が攻略する市場の非効率性）
既存Anomaly一覧: {existing_anomaly_ids}
- 新規の場合のみ追加。既存に該当する場合はIDを返す
- anomaly_type: behavioral|structural|informational|microstructure|regulatory
- persistence: persistent|decaying|debated|regime_dependent

### 2. PerformanceEvidence（定量的な成果証拠）
主張内の数値データを構造化:
- metric_name: sharpe_ratio|annual_return|cumulative_return|accuracy|f1_score|annual_excess_return|max_drawdown
- value: 数値（%の場合はそのまま）
- benchmark: 比較対象
- market: US|China|Europe|Japan|Global|N/A
- is_oos: true|false

### 3. MarketRegime（この成果が測定された/有効な市場環境）
既存MarketRegime一覧: {existing_regime_ids}
- 新規の場合のみ追加
- regime_type: volatility|monetary_policy|economic_cycle|sentiment|liquidity|correlation

### 4. DataRequirement（この手法に必要なデータ）
既存DataRequirement一覧: {existing_datareq_ids}
- 新規の場合のみ追加
- data_type: price|fundamental|alternative|text|graph|macro|options|corporate_action
- criticality: essential|recommended|optional

## 出力形式（JSON）
```json
{
  "anomalies": [
    {"id": "anomaly-{slug}", "name": "...", "anomaly_type": "...", "persistence": "...", "is_new": true}
  ],
  "performance_evidences": [
    {"id": "perf-{method}-{metric}-{hash8}", "metric_name": "...", "value": ..., "unit": "...", "benchmark": "...", "market": "...", "is_oos": true}
  ],
  "market_regimes": [
    {"id": "regime-{slug}", "name": "...", "regime_type": "...", "is_new": true}
  ],
  "data_requirements": [
    {"id": "datareq-{slug}", "name": "...", "data_type": "...", "criticality": "...", "is_new": true}
  ],
  "relations": {
    "exploits": [{"from_id": "method-...", "to_id": "anomaly-...", "mechanism": "...", "effectiveness": "proven|promising|theoretical"}],
    "evaluates": [{"from_id": "perf-...", "to_id": "method-..."}],
    "quantified_by": [{"from_id": "clm-...", "to_id": "perf-..."}],
    "requires_data": [{"from_id": "method-...", "to_id": "datareq-...", "criticality": "essential|recommended"}],
    "effective_in": [{"from_id": "method-...", "to_id": "regime-..."}],
    "measured_in": [{"from_id": "perf-...", "to_id": "regime-..."}],
    "explained_by": [{"from_id": "anomaly-...", "to_id": "clm-...", "explanation_type": "persistence|decay|boundary_condition"}]
  }
}
```
```

## 既存ノードID一覧の取得クエリ

投入前に以下のCypherで既存IDを取得し、プロンプトに注入する:

```cypher
// 既存 Anomaly
MATCH (a:Anomaly) RETURN a.anomaly_id, a.name ORDER BY a.name

// 既存 MarketRegime
MATCH (r:MarketRegime) RETURN r.regime_id, r.name ORDER BY r.name

// 既存 DataRequirement
MATCH (d:DataRequirement) RETURN d.data_req_id, d.name ORDER BY d.name

// 既存 Method
MATCH (m:Method) RETURN m.method_id, m.name ORDER BY m.name
```

## 品質チェックリスト

v2ノード抽出後に確認:

- [ ] PerformanceEvidence の value が原文の数値と一致するか
- [ ] is_oos フラグが正しいか（in-sample結果をOOSと誤記していないか）
- [ ] Anomaly が既存ノードと重複していないか
- [ ] DataRequirement の criticality が適切か（essential = なければ手法が機能しない）
- [ ] EXPLOITS の mechanism が「なぜこの手法がこのアノマリーを攻略するか」を説明しているか
