# 議論メモ: 2026-03-19 セッション全体サマリー

**日付**: 2026-03-19
**議論ID**: disc-2026-03-19-session-summary
**参加**: ユーザー + AI
**関連Discussion**: disc-2026-03-19-quant-kg-barriers → disc-2026-03-19-quant-kg-population → 本メモ

## 背景・コンテキスト

ユーザーの目的: Web検索・論文検索で収集したクオンツ分析・コード構築情報をNeo4jに保存し、そこから創発的にクオンツ戦略やAI投資調査手法の新規提案をAIに生成させたい。

## セッションの流れ（3段階）

### Stage 1: 障壁分析 (disc-2026-03-19-quant-kg-barriers)

4つの障壁を特定:
1. スキーマにクオンツ手法用ノード型がない
2. KG v1パイプラインが未稼働（Source/Entity等 0件）
3. 収集→構造化パイプラインが欠如
4. enum値不足（Topic.category, Source.source_type）

### Stage 2: 実データ投入 + スキーマ拡張 (disc-2026-03-19-quant-kg-population)

**投入データ**:
- `research/quant_factor_investing_papers.md` (33論文: ファクター投資)
- `research/ai_kg_investment_strategy_research.md` (38論文: AI+KG+エージェント)

**最終グラフ統計**:

| ノード | 件数 |
|--------|------|
| Source (論文) | 71 |
| Claim (発見) | 27 |
| Author (研究者) | 20 |
| Method (手法) **NEW** | 18 |
| Topic (カテゴリ) | 12 |
| Entity (機関) | 10 |
| Fact (定量結果) | 7 |
| リレーション計 | ~170 |

**スキーマ v1.0 → v1.1 拡張**:
- Method ノード追加 (method_type: architecture/algorithm/framework/technique/model)
- Source.source_type += paper, code, documentation
- Topic.category += quant_method, backtest, algorithm, risk_model
- Author.author_type += academic
- 新リレーション: USES_METHOD, EXTENDS_METHOD, COMBINED_WITH
- Neo4j制約・インデックス作成済み

### Stage 3: グラフ分析と発見

**Method経由トピック横断パターン（最重要発見）**:

| ブリッジ手法 | 接続トピック | 論文数 |
|------------|------------|--------|
| GNN | KG投資 ↔ 戦略レプリケート | 7 |
| MAS | AIエージェント中核 | 11 |
| LLM Alpha Mining | αマイニング ↔ 戦略レプリケート | 4 |
| RL | αマイニング ↔ AIエージェント ↔ サーベイ | 3方向 |

**知識ギャップ（創発的提案の種）**:
1. MAS × KG投資 = 未接続 → MASでKGを動的構築する戦略が未開拓
2. GNN × AIエージェント = 未接続 → GNNをエージェント知覚層に組込む余地
3. モメンタム → Method未接続 → 手法の構造化が不足

**note-finance v2.3 調査結果**:
- 12ノード・25+リレーション・4名前空間の成熟スキーマ
- PDFパイプライン（7フェーズ）のKnowledgeExtractorが核心
- 決定論的ID生成（UUID5/SHA-256）で冪等性保証
- authority_level 6段階分類
- 2 DB構成（research-neo4j + article-neo4j）

## 決定事項

| ID | 内容 | コンテキスト |
|----|------|------------|
| dec-001 | KGスキーマにクオンツ知識用ノード型追加が必要 | 既存9ノードは金融市場情報特化 |
| dec-002 | KG v1パイプライン動作確認を先に実施 | KG v1ノード0件 |
| dec-003 | Web検索/論文→graph-queue変換パイプラインの新規構築が必要 | 既存は金融ワークフロー用 |
| dec-004 | **スキーマ v1.0→v1.1 拡張完了** | Method+enum+3リレーション追加 |
| dec-005 | **Method経由トピック横断パターン発見** | MAS×KG, GNN×MASのギャップ特定 |
| dec-006 | **実データ駆動のスキーマ設計が有効** | 「まず入れて確かめる」方針が正解 |

## アクションアイテム

| ID | 内容 | 優先度 | 状態 |
|----|------|--------|------|
| act-001 | ~~パイプライン動作確認~~ | 高 | **completed** (直接Cypher投入で代替) |
| act-002 | ~~スキーマ拡張設計~~ | 高 | **completed** (v1.1完了) |
| act-003 | クオンツ知識収集→構造化エージェント設計 | 中 | pending |
| act-004 | ~~note-finance KG構築手法調査~~ | 高 | **completed** |
| act-005 | **創発的戦略提案クエリ実行** | **高** | pending |
| act-006 | EXTENDS_METHOD/COMBINED_WITH投入（手法進化チェーン） | 中 | pending |
| act-007 | emit_graph_queue.pyにパイプライン自動化追加 | 中 | pending |

## 次回の議論トピック

1. **創発的提案クエリの実行と結果レビュー**（MAS×KG投資、GNN×MASのギャップから新戦略提案）
2. 手法進化チェーン構築（CAPM→FF3→FF5→DL→LLM）
3. 論文の自動収集パイプライン設計（arXiv RSS → LLM抽出 → Neo4j）
4. バックテスト結果の構造化保存設計

## 参考情報

### note-finance v2.3 からの主要知見

| 機能 | quants適用の可否 |
|------|-----------------|
| PDFパイプライン (7フェーズ) | 中期で検討 |
| KnowledgeExtractor (LLM抽出) | 高優先で設計 |
| authority_level 6段階 | v1.2で追加検討 |
| compound key (entity_key等) | v1.2で追加検討 |
| SkillRun observability | 低優先 |
