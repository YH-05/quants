# note-quality-check → kg-quality-check 移植計画

## Context

note-finance プロジェクトに実装済みの `note-quality-check` スキル/コマンドを quants プロジェクトに移植する。
note-finance は Discussion/Decision/ActionItem/Research の4ノードに対して品質チェックを行うが、
quants は KG v2.2 スキーマ（14ノード・31リレーション）に適応する必要がある。

**目的**: quants の Neo4j ナレッジグラフのデータ品質を定量的に計測・評価し、
改善ポイントを可視化するスキル/コマンドを整備する。

---

## 作成ファイル

| ファイル | 説明 | 推定行数 |
|---------|------|---------|
| `.claude/skills/kg-quality-check/SKILL.md` | メインスキル定義（全Cypherクエリ・スコアリング・レポートテンプレート） | ~750行 |
| `.claude/commands/kg-quality-check.md` | スラッシュコマンド定義 | ~30行 |

既存ファイルの変更は不要。

---

## 移植元と移植先の差分

| 項目 | note-quality-check（移植元） | kg-quality-check（移植先） |
|------|---------------------------|--------------------------|
| ノード数 | 4（Discussion, Decision, ActionItem, Research） | 14（KG v2.2 全ノード） |
| MCP ツール | `mcp__neo4j-note__note-read_neo4j_cypher` | `mcp__neo4j-cypher__read_neo4j_cypher` |
| Neo4j ポート | 7687 | 7690 |
| DocSync | doc_path ファイル存在確認 | **廃止** → Schema Compliance に置換 |
| LLM-as-Judge | Decision の content/context 整合性 | Claim/Fact 精度 + 創発的発見ポテンシャル |
| ID パターン | 3種（disc-, dec-, act-） | 10種以上 |
| Enum 検証 | 2 enum | 13+ enum |

---

## 7カテゴリ設計

### 重み配分

| # | カテゴリ | 重み | 概要 |
|---|---------|------|------|
| 1 | Completeness（完全性） | 25% | 14ノードのプロパティ充填率（必須/推奨/任意の加重） |
| 2 | Consistency（一貫性） | 20% | ID フォーマット + enum 値 + リレーションタイプ妥当性 |
| 3 | Orphan（孤立ノード） | 15% | 期待リレーションを持たないノードの検出 |
| 4 | Staleness（鮮度） | 10% | 30日以上 draft の Insight、90日以上未抽出の Source |
| 5 | Structural（構造） | 10% | 分布分析（Entity あたり Claim 数、Method-Anomaly カバレッジ等） |
| 6 | Schema Compliance（スキーマ準拠） | 5% | 不明ラベル、PascalCase 違反、UNIQUE 制約存在確認 |
| 7 | LLM-as-Judge | 15% | Claim/Fact 精度（8%）+ 創発的発見ポテンシャル（7%） |

### 1. Completeness（25%）

14ノード全てのプロパティ充填率を計測。スキーマ YAML の `required: true` / `indexed: true` を基に重み付け。

- **必須** (重み 1.0): `required: true` のプロパティ（例: source_id, title, source_type, fetched_at）
- **推奨** (重み 0.7): `indexed: true` だが `required` でないプロパティ（例: url, publisher, ticker, sentiment）
- **任意** (重み 0.3): 上記いずれでもないプロパティ（例: language, aliases, target_price）

各ノードの Cypher クエリ例（Source の場合）:
```cypher
MATCH (s:Source)
RETURN count(s) AS total,
       count(s.source_id) AS has_id, count(s.title) AS has_title,
       count(s.source_type) AS has_source_type, count(s.fetched_at) AS has_fetched_at,
       count(s.url) AS has_url, count(s.publisher) AS has_publisher,
       count(s.published_at) AS has_published_at, count(s.category) AS has_category,
       count(s.command_source) AS has_command_source, count(s.language) AS has_language
```

同様のクエリを残り13ノードにも作成。

### 2. Consistency（20%）

3サブカテゴリ:

**2a. ID フォーマット検証（10種以上）**:
- `method-{slug}`, `anomaly-{slug}`, `regime-{slug}`, `datareq-{slug}`
- `perf-{slug}-{metric}-{hash8}`, `ins-{YYYY-MM-DD}-{seq}`
- `{TICKER}_{period_label}` (FiscalPeriod)
- UUID 形式（Source, Entity, Topic, Author）
- その他（Claim, Fact, FinancialDataPoint）

**2b. Enum 値検証（13 enum）**:
- Source.source_type, Entity.entity_type, Claim.claim_type, Claim.sentiment, Claim.confidence
- Fact.fact_type, Method.method_type, Anomaly.anomaly_type, Anomaly.persistence
- Insight.status, MarketRegime.regime_type, DataRequirement.data_type, DataRequirement.availability

**2c. 異常リレーション検出**:
- STATES_FACT は Source→Fact のみ
- MAKES_CLAIM は Source→Claim のみ
- ABOUT は Claim→Entity のみ
- 不明リレーションタイプの検出（31種以外）

### 3. Orphan（15%）

期待される接続を持たないノード:
- Claim: `MAKES_CLAIM` なし（Source 未接続）、`ABOUT` なし（Entity 未接続）
- Fact: `STATES_FACT` なし
- FinancialDataPoint: `HAS_DATAPOINT` なし、`FOR_PERIOD` なし
- Source: `STATES_FACT` も `MAKES_CLAIM` も `HAS_DATAPOINT` もなし（未抽出）
- PerformanceEvidence: `EVALUATES` なし
- Method: `USES_METHOD` なし
- Topic: `TAGGED` なし（未使用）

### 4. Staleness（10%）

- 30日以上 `draft` のままの Insight
- 90日以上前に取得され、Claim/Fact/DataPoint が未抽出の Source
- 3年以上前の evaluation period を持つ PerformanceEvidence

### 5. Structural（10%）

- Entity あたり Claim 数の分布（avg/max/min/median）
- Topic あたり Source 数の分布
- Method-Anomaly カバレッジ（EXPLOITS 接続率）
- Method あたり PerformanceEvidence 数
- ノードタイプ分布、リレーションタイプ分布
- Top Entity ハブ（最も接続数が多い Entity 上位10）

### 6. Schema Compliance（5%）

- 不明ノードラベル検出（KG v2.2 + conversation + archived 名前空間以外）
- PascalCase 違反検出
- UNIQUE 制約存在確認（14制約）
- 既存の `scripts/validate_neo4j_schema.py` と補完関係（重複なし）

### 7. LLM-as-Judge（15%）

**7a. Claim/Fact 精度（8%）**:
- ランダム10 Claim + 10 Fact をサンプリング
- 3軸評価: Factual Correctness (40%) / Source Grounding (30%) / Temporal Validity (30%)

**7b. 創発的発見ポテンシャル（7%）**:
- 4構造プローブ実行:
  - A: Cross-Domain Bridge（異なる entity_type の Entity 間で共有 Fact）
  - B: Method-Anomaly-Regime Traversal（AI戦略発見チェーン）
  - C: Contradicting Claims（矛盾する主張）
  - D: Multi-Topic Entities（複数カテゴリにまたがる Entity）
- 3+ 仮説を構築し、4軸で自己評価

---

## 処理フロー

```
Phase 1: 定量計測（Cypher プローブ）
    |  mcp__neo4j-cypher__read_neo4j_cypher で6カテゴリの指標を計測
    |  推定 40+ クエリ、2-3分
    |
Phase 2: LLM-as-Judge
    |  Claim/Fact のサンプリング精度評価
    |  4構造プローブ → 仮説構築 → 自己評価
    |
Phase 3: レポート出力
    Markdown レポートを画面出力
    総合スコア（100点満点）+ Rating (A/B/C/D)
    問題一覧 + 改善提案（優先度: 高/中/低）
```

---

## 参照ファイル

| ファイル | 用途 |
|---------|------|
| `/users/yukihata/desktop/note-finance/.claude/skills/note-quality-check/SKILL.md` | 移植元テンプレート（構造・Phase・MUST/SHOULD/NEVER セクション） |
| `/users/yukihata/desktop/note-finance/.claude/commands/note-quality-check.md` | 移植元コマンド |
| `data/config/knowledge-graph-schema.yaml` | スキーマ SSoT（全プロパティ・enum・リレーション定義） |
| `.claude/rules/neo4j-namespace-convention.md` | 名前空間・命名規約 |
| `scripts/validate_neo4j_schema.py` | 既存スキーマ検証（Schema Compliance カテゴリの補完） |
| `.claude/skills/save-to-graph/SKILL.md` | グラフ投入スキル（品質チェックの対象パイプライン） |

---

## MUST / SHOULD / NEVER

### MUST
- 全 Cypher は `mcp__neo4j-cypher__read_neo4j_cypher` で実行（読み取り専用）
- 7カテゴリ全てのプローブを実行
- 総合スコア（100点満点）を算出
- 問題発見時は具体的な改善提案を含める

### SHOULD
- スコアが50%未満のカテゴリは警告マーク付き
- 前回レポートが存在する場合は比較
- 改善提案に優先度（高/中/低）を付与

### NEVER
- `mcp__neo4j-cypher__write_neo4j_cypher` を使用しない
- データを修正しない（検出と報告のみ）

---

## 検証方法

1. `/kg-quality-check` コマンドを実行
2. 7カテゴリ全てのスコアが出力されることを確認
3. 総合スコア（100点満点）と Rating が表示されることを確認
4. 改善提案が含まれることを確認
5. 既知の問題（例: 孤立ノード）が正しく検出されることを確認

---

## 実装手順

1. `.claude/skills/kg-quality-check/SKILL.md` を作成
   - note-quality-check の構造をベースに、14ノード・31リレーション用の全 Cypher クエリを記述
   - スコアリングロジック、レポートテンプレートを含める
2. `.claude/commands/kg-quality-check.md` を作成
   - スキル参照 + 実行手順 + 注意事項
3. 動作確認: `/kg-quality-check` を実行してレポート出力を検証
