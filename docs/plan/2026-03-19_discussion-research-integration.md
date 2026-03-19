# 議論メモ: 提案1・2の情報収集完了 — 2エージェント並列リサーチ統合結果

**日付**: 2026-03-19
**議論ID**: disc-2026-03-19-research-integration
**参加**: ユーザー + AI + academic-researcher + web-researcher

## 背景・コンテキスト

Insight 4件（ins-2026-03-19-001~004）の創発的提案のうち、提案1（GNN×MAS）と提案2（KG×LLM Alpha）の実現可能性を検証するため、2つのリサーチエージェントを並列起動。

## リサーチ体制

| エージェント | 検索手段 | フェーズ | 発見数 |
|-------------|---------|---------|--------|
| academic-researcher | tavily (arxiv/alphaxiv) | 12 | 34論文 |
| web-researcher | gemini-search | 12 | 16件 |
| **合計** | | **24** | **50件** |

## KGグラフの成長

| ノード | セッション開始時 | 最終 |
|--------|---------------|------|
| Source | 0 | **113** |
| Method | 0 | **43** |
| Claim | 0 | **69** |
| Insight | 0 | **4** |

## 提案1: GNN-Enhanced Multi-Agent Investment System

### 実現可能性: 高い

**学術的根拠:**
- **Graphs Meet AI Agents** (2506.18019) — GNN×AIエージェント統合の初の体系的サーベイ
- **ChatGPT Informed GNN** (2306.03763) — LLM→動的グラフ→GNN統合（SIGKDD 2023）
- **GNNComm-MARL** (2404.04898) — GNN+MARLアーキテクチャサーベイ
- **GTD** (2510.07799) — グラフ拡散モデルでMAS通信トポロジ動的生成
- **FinMamba** (2502.06707) — Market-Aware Graph + Mambaで線形計算量SOTA
- **THGNN** (2305.08740) — 異種グラフ注意ネットワークで**実運用展開済み**

**実装事例:**
- **HedgeAgents (PyFi)** — 年利70%, WWW 2025, GitHub公開
- **AgenticTrading** — FLAG-Trader含むマルチエージェントエコシステム
- **LED-GNN** — LLM→動的グラフ→GATv2+LSTM

**具体的アーキテクチャ候補: LED-GNN型**
```
ニュース/SEC Filing → LLM(グラフ推論) → 動的企業関係グラフ
                                           ↓
                         GATv2(ノード埋め込み) → LSTM(時系列)
                                           ↓
                         MAS Analyst Team(GNN出力を分析)
                                           ↓
                         Fund Manager(最終投資判断)
```

### 課題
- LLM APIコストとレイテンシの管理
- GNN+MAS+金融の3分野直接統合論文はまだ少ない

---

## 提案2: Autonomous Alpha Discovery via KG + LLM Agents

### 実現可能性: 非常に高い

**学術的根拠:**
- **Agentic-KGR** (2510.09156) — LLM+KG共進化（多ラウンドRL+動的スキーマ拡張）
- **TRACE** (2603.12500) — KGルール誘導多ホップ探索+LLM判定（F1=60.8%）
- **FinCARE** (2510.20221) — KG+LLMで因果発見F1を+366%改善
- **AlphaForge** (2406.18394) — 生成的NNでFactor Zoo生成（AAAI 2025）
- **AlphaSAGE** (2509.25055) — RGCN+GFlowNetで多様なアルファ
- **R&D-Agent** (2505.14738) — Microsoft製自律MLエンジニアリング（MLE-Bench 1位）

**実装事例:**
- **RD-Agent(Q)** — Microsoft, GitHub公開, 5ステージ自律サイクル
- **AlphaAgent** — AST独創性チェック付き, GitHub公開
- **FinDKG + ICKG-v3.2** — OSS動的KG構築
- **Bloomberg/S&P/LSEG** — 全てMCP対応発表（2025年）

**具体的アーキテクチャ候補: 3段パイプライン**
```
Phase 1: 動的KG構築
  FinDKG/ICKG → Neo4j(企業関係・イベント・因果)

Phase 2: 自律的アルファ発見
  AlphaAgent(AST正則化) + RD-Agent(自律R&Dサイクル)
  → KG上のパターン検出 → ファクター候補生成 → バックテスト検証

Phase 3: MAS意思決定
  TradingAgents/FinCon(ディベート型合議) → ポートフォリオ構築
```

### 課題
- KG品質維持（ドリフト対策）
- LLM生成アルファの独創性検証（Alpha Decay防止）
- 3段パイプライン統合時のレイテンシ・整合性

---

## 新規発見Method（25手法、両エージェント合計）

### academic-researcher発見 (13手法)
LLM-based Graph Inference, GAT, Graph Conv LSTM, Reflection-Agent KG, Rule-Guided KG Exploration, Evolutionary Alpha Mining, Hawkes Process on Graphs, LLM-KG Co-evolution, Contrastive Learning for Graphs, Mamba SSM, GFlowNet, Graph Diffusion for Agent Topology, Causal Discovery with KG+LLM

### web-researcher発見 (12手法)
LED-GNN, DisFT-GNN, FLAG-Trader, RD-Agent, AlphaAgent, Evolutionary Alpha Mining, GraphRAG, HedgeAgents, ElliottAgents, ICKG, HIST, MCP

## 決定事項

| ID | 内容 |
|----|------|
| dec-007 | 提案1(GNN×MAS)実現可能性「高」。LED-GNNが具体的アーキテクチャ候補 |
| dec-008 | 提案2(KG×LLM Alpha)実現可能性「非常に高」。OSS部品が揃っている |

## アクションアイテム

| ID | 内容 | 優先度 | 状態 |
|----|------|--------|------|
| act-008 | 提案1・2の実装設計書を作成 | 高 | pending |
| act-009 | bearish論文の意図的収集（Claimバイアス是正） | 中 | pending |
| act-010 | EXTENDS_METHOD/COMBINED_WITHリレーション投入 | 中 | pending |

## 次回の議論トピック

1. 提案1・2のどちらを先に実装するか（リソース配分）
2. 実装設計書の作成（使用OSS、quantsパッケージ統合）
3. OSSリポジトリ（HedgeAgents, RD-Agent, FinDKG）の技術評価
