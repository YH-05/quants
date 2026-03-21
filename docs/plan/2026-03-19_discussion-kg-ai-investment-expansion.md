# 議論メモ: KGのAIエージェント投資情報ギャップ特定と拡充

**日付**: 2026-03-19
**議論ID**: disc-2026-03-19-kg-ai-investment-expansion
**参加**: ユーザー + AI

## 背景・コンテキスト

Neo4jナレッジグラフのAI投資関連データが「AIエージェント運用チーム」「AI・ナレッジグラフ × 投資戦略」の2トピックに偏っており、投資戦略構築の実務的領域（リスク管理、約定最適化、レジーム検知等）がカバーされていなかった。alphaxiv MCPを使って体系的にギャップを特定し拡充した。

## 議論のサマリー

### Phase 1: 初期ギャップ分析と拡充（AIエージェント投資全般）

Neo4jの既存データを分析し、以下6領域のギャップを特定:

| 領域 | 投入論文数 | 代表論文 |
|------|----------|---------|
| Financial Agent Benchmarks & Evaluation | 14 | FinBen, StockBench, FinToolBench, AI-Trader |
| Financial Agent Safety & Alignment | 9 | TradeTrap, FinVault, When AI Agents Collude |
| Multimodal Financial AI | 8 | FinVision, MultiFinBen, MFFMs Survey, FinAudio |
| Financial Foundation Models | 3 | FinGPT, Open-FinLLMs, Alpha-R1 |
| Deep RL for Trading | 4 | FinRL Contests, RL in Quant Finance Survey |
| LLM Alpha Mining & Code Generation | 4 | QuantaAlpha, AlphaEval |

### Phase 2: alphaxiv MCP のコンテキスト爆発問題

`get_paper_content` と `full_text_papers_search` の並列実行でコンテキストウィンドウが圧迫される問題が発生。これを受けて `alphaxiv-search` スキルを設計・作成。

### Phase 3: AI投資戦略構築向け拡充

スキルに従い、残り7領域を `embedding_similarity_search` のみで効率的に検索:

| 領域 | 投入論文数 | 代表論文 |
|------|----------|---------|
| LLM-Driven Portfolio Construction | 8 | MASS, LLM-Enhanced Black-Litterman, Sector Allocation |
| LLM Fundamental Analysis | 6 | Financial Statement Analysis (U Chicago), ECC Analyzer |
| AI Optimal Execution & Microstructure | 5 | RL Optimal Execution (ETH), Regime Adaptive Execution |
| Explainable AI for Finance | 5 | XAI in Finance Survey, Beyond the Black Box (Barclays) |
| AI-Driven Risk Management | 4 | Deep Hedging (JPM), Dynamic CVaR, Tail Risk |
| Market Regime Detection with AI | 4 | Tactical Asset Allocation (UCLA/Oxford), RegimeFolio |
| Signal Combination & Ensemble Methods | 4 | Expert Aggregation (Amundi), Dynamic Weighting |

## 数値サマリー

| ノード | 投入前 → 投入後 | 増加 |
|--------|---------------|------|
| Source | 148 → 237 | +89 |
| Topic | 28 → 41 | +13 |
| Method | 108 → 126 | +18 |
| Claim | 173 → 189 | +16 |
| Entity | 69 → 77 | +8 |

## 決定事項

| ID | 内容 | コンテキスト |
|----|------|------------|
| dec-2026-03-19-001 | alphaxiv MCP使用方針: embedding_similarity_search主力、get_paper_content 1セッション2-3件、agentic_paper_retrieval不使用、並列最大4件。alphaxiv-searchスキルとして永続化 | コンテキスト爆発問題への対策 |
| dec-2026-03-19-002 | AI投資戦略構築に必要な研究領域を15カテゴリで体系化しKGのTopicノードとして構造化 | 既存KGの偏りを是正 |
| dec-2026-03-19-003 | alphaxiv-searchスキルを新規作成（.claude/skills/alphaxiv-search/SKILL.md）。実地テストで有効性確認済み | MCPの効率的利用パターンの組織知化 |

## アクションアイテム

| ID | 内容 | 優先度 | 状態 |
|----|------|--------|------|
| act-2026-03-19-001 | Alternative Data × AI投資の領域をalphaxivで追加リサーチ | 中 | pending |
| act-2026-03-19-002 | 主要論文のClaim/PerformanceEvidence詳細化（get_paper_content） | 中 | pending |
| act-2026-03-19-003 | 四半期ごとのKG情報ギャップ分析を実施 | 低 | pending |

## 新規作成ファイル

| ファイル | 説明 |
|---------|------|
| `.claude/skills/alphaxiv-search/SKILL.md` | alphaxiv MCP効率的検索スキル |

## 発見された重要な知見

1. **GPT-4はトレーディングで最高Sharpe Ratioだが、株価予測はほぼランダム**（FinBen）
2. **LLMトレーディングエージェントは敵対的操作に脆弱**（TradeTrap）
3. **ライブ市場ではバックテスト結果から大幅にパフォーマンス低下**（LiveTradeBench）
4. **精度ベースのベンチマークでは金融エージェントの安全性を評価できない**
5. **マルチモーダル基盤モデルはテキストのみより優れるが支配的アーキテクチャは未確立**
6. **U Chicago Booth: LLMは専門アナリスト水準の財務諸表分析が可能**
7. **UCLA/Oxford: ML レジーム検知で戦術的資産配分が改善（836 visits, 128 likes）**

## 次回の議論トピック

- Alternative Data × AI投資のリサーチ結果レビュー
- 投入済み論文の知見をca_strategyパッケージの設計にどう反映するか
- KGの研究知見からバックテストエンジン設計への示唆の抽出
