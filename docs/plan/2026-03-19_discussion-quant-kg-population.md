# 議論メモ: クオンツ論文71本のNeo4j投入とスキーマv1.1拡張

**日付**: 2026-03-19
**議論ID**: disc-2026-03-19-quant-kg-population
**参加**: ユーザー + AI

## 背景・コンテキスト

前回の議論 (disc-2026-03-19-quant-kg-barriers) で特定した4障壁に対し、実データ投入を通じて実証・解決を進めた。

- 2レポート: `research/quant_factor_investing_papers.md` (33本) + `research/ai_kg_investment_strategy_research.md` (38本)
- note-finance v2.3 のKG構築手法を参考にスキーマ拡張を設計

## 議論のサマリー

### 投入結果

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

### Method経由のトピック横断パターン（最重要発見）

| ブリッジ手法 | 接続トピック | 論文数 |
|------------|------------|--------|
| GNN | KG投資 ↔ 戦略レプリケート | 7 |
| LLM Alpha Mining | αマイニング ↔ 戦略レプリケート | 4 |
| Autoencoder | DLファクター ↔ 統計的裁定 | 2 |
| Attention | KG投資 ↔ 統計的裁定 | 2 |
| RL | αマイニング ↔ AIエージェント ↔ サーベイ | 3方向 |
| Bayesian | ファクタータイミング ↔ 戦略レプリケート | 2 |

### 知識ギャップ（創発的提案の種）

1. **MAS × KG投資 = 未接続**: 11論文のMASと9論文のKG投資が直接つながっていない → MASでKGを動的構築する戦略が未開拓
2. **GNN × AIエージェント = 未接続**: GNN(7論文)とMAS(11論文)の組合せ論文がない → GNNをエージェントの知覚層に組込む余地
3. **モメンタム → Method未接続**: 3論文あるがMethodノードとの関連付けがゼロ

### スキーマ v1.0 → v1.1 拡張内容

| 変更 | 詳細 |
|------|------|
| **Method ノード追加** | method_id, name, method_type (5 enum: architecture/algorithm/framework/technique/model), description |
| Source.source_type | += paper, code, documentation |
| Topic.category | += quant_method, backtest, algorithm, risk_model |
| Author.author_type | += academic |
| **新リレーション** | USES_METHOD, EXTENDS_METHOD, COMBINED_WITH |
| ノード数 | 9 → 10 |
| リレーション数 | 16 → 19 |

## 決定事項

| ID | 内容 | コンテキスト |
|----|------|------------|
| dec-2026-03-19-004 | KGスキーマv1.0→v1.1拡張完了。Methodノード+enum拡張+3リレーション追加 | 71論文投入で既存スキーマの不足を実証 |
| dec-2026-03-19-005 | Method経由トピック横断パターン発見。MAS×KG投資とGNN×AIエージェントのギャップを創発提案の種として特定 | グラフ分析結果 |

## アクションアイテム

| ID | 内容 | 優先度 | 状態 |
|----|------|--------|------|
| act-2026-03-19-005 | Neo4jグラフから創発的戦略提案クエリ実行（MAS×KG、GNN×MASギャップ活用） | 高 | pending |
| act-2026-03-19-006 | EXTENDS_METHOD/COMBINED_WITHリレーション投入（手法進化チェーン構築） | 中 | pending |
| act-2026-03-19-007 | emit_graph_queue.pyにpaper-collection/web-knowledgeソース追加 | 中 | pending |

## 次回の議論トピック

- 創発的提案クエリの結果レビュー
- 手法進化チェーン（CAPM→FF3→FF5→DL→LLM）の構造化
- 論文の自動収集パイプライン設計（arXiv RSS → LLM抽出 → Neo4j）
