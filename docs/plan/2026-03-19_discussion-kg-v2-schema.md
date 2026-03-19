# 議論メモ: KG v2.0スキーマ設計 — AI駆動クオンツ戦略創発

**日付**: 2026-03-19
**議論ID**: disc-2026-03-19-kg-v2-schema
**参加**: ユーザー + AI

## 背景・コンテキスト

Neo4jグラフデータベースの現行構造（KG v1.1）が、AIによるクオンツ投資戦略の創発的開発・提案・発見の障壁になっているか分析を実施。

### 判明した障壁

1. **Claim/Method間の接続がゼロ** — 69 Claimの平均次数1.01、Method間リレーション0件
2. **FinancialDataPoint/FiscalPeriodのデータがゼロ** — スキーマ定義のみ
3. **ca_strategyパイプラインとKGが完全分離** — grep "neo4j" で0件
4. **スキーマ定義済みリレーション（CONTRADICTS等）のデータ不在**
5. **Strategy/Signal/Factor/Backtest等の投資戦略ノード不在**
6. **フィードバックループの構造的不在**
7. **収集バイアス（89% bullish）**

## 議論のサマリー

### Phase 1: 空リレーション投入

既存113 Source・69 Claim・43 Methodの内容を分析し、v1.1スキーマの空リレーションを投入:

| リレーション | 件数 | 内容 |
|---|---|---|
| EXTENDS_METHOD | 18 | GNN系6件、Dynamic KG系5件、LLM Alpha Mining/MAS/RL系7件 |
| COMBINED_WITH | 12 | GNN×RL、Dynamic KG×Causal Discovery等 |
| SUPPORTED_BY | 9 | Fact→Claim 4件、Claim→Claim 5件 |
| CONTRADICTS | 4 | Autoencoder有効性、OOS予測力、MASリスク、企業グラフ有効性 |

### Phase 2: v2.0スキーマ設計

AI戦略創発に必要な推論パス `Anomaly → Method → PerformanceEvidence → MarketRegime` を実現するため、4つの新ノードと8つの新リレーションを設計・実装。

**新ノード (4)**:
- **Anomaly** — 手法が攻略する市場の非効率性（behavioral/structural/informational/microstructure/regulatory）
- **PerformanceEvidence** — Claimから構造化抽出した定量成果（Sharpe/Return/Accuracy等）
- **MarketRegime** — 戦略有効性の条件となる市場環境（volatility/monetary_policy/economic_cycle等）
- **DataRequirement** — 手法に必要なデータ種別（price/fundamental/text/graph等）

**新リレーション (8)**:
EXPLOITS, EVALUATES, QUANTIFIED_BY, EFFECTIVE_IN, REQUIRES_DATA, EXPLAINED_BY, MEASURED_IN, COMPETES_WITH

### Phase 3: シードデータ投入・検証

シードデータ: Anomaly 6件、PerformanceEvidence 9件、MarketRegime 6件、DataRequirement 8件

**検証クエリ3種で推論パス動作確認済み**:

1. `Anomaly ← EXPLOITS ← Method ← EVALUATES ← PerformanceEvidence` — アノマリー別手法成果比較
2. `Method → REQUIRES_DATA → DataRequirement(free)` — 無料データ実装可能手法の発見
3. **未組合Method対の自動発見** — 共通Anomalyを攻略するが COMBINED_WITH がない対:
   - KGTransformer × GNN (Corporate Network Effect)
   - MAS × LLM Alpha Mining (Information Asymmetry)
   - MAS × Dynamic KG (Information Asymmetry)
   - LLM Alpha Mining × Dynamic KG (Information Asymmetry)
   - Autoencoder × Attention (Mean Reversion)

## 決定事項

| ID | 内容 | コンテキスト |
|----|------|------------|
| dec-2026-03-19-001 | KG v1.1→v2.0スキーマ拡張（14ノード27リレーション） | AI戦略創発のための推論チェーン構築 |
| dec-2026-03-19-002 | 空リレーション投入完了（43件） | スキーマ定義済みだがデータゼロだった |
| dec-2026-03-19-003 | ca_strategy結果はまだKGに投入しない | オペレーショナルデータとナレッジを分離 |
| dec-2026-03-19-004 | v2シードデータ投入（29ノード+64リレーション） | 推論パス検証成功 |
| dec-2026-03-19-005 | 推論パス3種の検証完了 | 未発見ハイブリッド戦略5件を自動発見 |

## アクションアイテム

| ID | 内容 | 優先度 | ステータス |
|----|------|--------|----------|
| act-2026-03-19-001 | emit_graph_queue.py のv2対応（新ノードマッパー追加） | 高 | pending |
| act-2026-03-19-002 | save-to-graph スキルのv2対応 | 高 | pending |
| act-2026-03-19-003 | 既存69 ClaimからPerformanceEvidenceの網羅的抽出 | 中 | pending |
| act-2026-03-19-004 | DataRequirement→Method接続の拡充（残り約半数） | 中 | pending |
| act-2026-03-19-005 | 新規論文投入時のv2ノード同時生成プロンプト設計 | 中 | pending |

## 変更ファイル

| ファイル | 変更内容 |
|---------|---------|
| `data/config/knowledge-graph-schema.yaml` | v1.1→v2.0（14ノード、27リレーション） |
| `data/config/neo4j-constraints.cypher` | 14 constraint + 22 index |
| `.claude/rules/neo4j-namespace-convention.md` | kg_v1ラベル一覧にv2ノード追加 |

## v2.0 スキーマ全体像

```
Source ──USES_METHOD──→ Method ──EXPLOITS──→ Anomaly
  │                       │  │                  ↑
  │──MAKES_CLAIM──→ Claim │  ├──EXTENDS_METHOD  │──EXPLAINED_BY──→ Claim
  │                   │   │  ├──COMBINED_WITH
  │──STATES_FACT──→ Fact  │  ├──COMPETES_WITH
  │                       │  │
  │──TAGGED──→ Topic      │  ├──EFFECTIVE_IN──→ MarketRegime
  │──AUTHORED_BY──→ Author│  │                      ↑
                          │  └──REQUIRES_DATA──→ DataRequirement
                          │
  Claim ──QUANTIFIED_BY──→ PerformanceEvidence ──EVALUATES──→ Method
     │                           │
     ├──SUPPORTED_BY──→ Fact     └──MEASURED_IN──→ MarketRegime
     ├──CONTRADICTS──→ Claim
     └──ABOUT──→ Entity
```

## 次回の議論トピック

- v2ノードの自動生成パイプライン設計（emit_graph_queue.py拡張方針）
- PerformanceEvidenceの網羅的抽出（LLMバッチ処理 vs 手動キュレーション）
- ca_strategy→KG統合のロードマップ（いつ、どのフェーズから接続するか）
