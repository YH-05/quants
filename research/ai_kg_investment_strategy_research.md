# AI・ナレッジグラフ・投資戦略に関する学術研究レポート

**作成日**: 2026-03-19
**データソース**: arXiv / alphaXiv（学術論文データベース）
**対象論文数**: 50+本（重複除外後の主要論文 30本を精査）

---

## エグゼクティブサマリー

本レポートは、以下3つのテーマに関する最新の学術研究を体系的に整理したものである。

1. **AI とナレッジグラフ（Neo4j）を活用した投資戦略**
2. **運用会社の戦略レプリケート（複製）**
3. **AI エージェントによる運用チームの構築**

直近2年間（2024-2026）で、特にLLMベースのマルチエージェントシステムと金融ナレッジグラフの融合が急速に進展しており、BlackRock、Oxford、UCLA、Columbia、HKUST等の主要機関から重要な研究が発表されている。

---

## 1. AI とナレッジグラフを活用した投資戦略

### 1.1 概要

金融市場における企業間関係、サプライチェーン、競争構造をグラフとして表現し、投資シグナルの生成やリスク管理に活用する研究が活発化している。LLMの登場により、非構造化テキストからの自動グラフ構築が実現可能になった。

### 1.2 主要論文

#### FinDKG: Dynamic Knowledge Graphs with LLMs for Detecting Global Trends in Financial Markets
- **著者**: Xiaohui Victor Li, Francesco Sanna Passino (Imperial College London)
- **arXiv**: [2407.10909](https://arxiv.org/abs/2407.10909) | 2024年7月 | 1,152 Visits, 75 Likes
- **概要**: LLMを用いて金融ニュースから動的ナレッジグラフ（DKG）を自動構築。KGTransformerアーキテクチャでリンク予測を行い、テーマ投資ポートフォリオを構築。
- **手法**:
  - Wall Street Journalコーパスからエンティティ・関係を抽出
  - 四つ組（ソース、関係、ターゲット、タイムスタンプ）で時系列変化を表現
  - グラフ中心性指標（PageRank、固有ベクトル中心性等）でトレンド検出
  - KGTransformerによるリンク予測で投資対象を特定
- **成果**:
  - FinDKG-AI ポートフォリオ: **年率39.6%、Sharpe比 1.810**（2022/6〜2023/12）
  - 既存AI ETFおよびS&P 500 ETFを大幅にアウトパフォーム
  - MRR、Hits@3,10でベースライン比10%以上の改善
- **投資への示唆**: テーマ投資（AI、ESG等）において、KGベースのエクスポージャー推定が有効

#### CompanyKG: A Large-Scale Heterogeneous Graph for Company Similarity Quantification
- **著者**: Lele Cao et al. (EQT Partners)
- **arXiv**: [2306.10649](https://arxiv.org/abs/2306.10649) | 2024年6月 | 64 Visits
- **概要**: 117万社のノードと15種類の関係性（約5,100万エッジ）を持つ大規模異種グラフデータセット。
- **データソース**: ニュース記事の共起、Webページリンク、Wikipedia参照、特許引用等
- **タスク**: 類似企業予測（SP）、競合企業検索（CR）、類似性ランキング（SR）
- **成果**: GNNベース手法（eGraphMAE）が類似予測で高AUCを達成
- **投資への示唆**: M&A対象スクリーニング、競合分析、市場マッピングに直接応用可能

#### Company Competition Graph
- **著者**: Yanci Zhang et al. (Michigan State, Oxford, Amazon)
- **arXiv**: [2304.00323](https://arxiv.org/abs/2304.00323) | 2023年4月
- **概要**: SEC年次報告書から企業間競争関係を抽出しグラフ化。投資判断の関係性分析を支援。

#### Extracting Alpha from Financial Analyst Networks
- **著者**: Dragos Gorduza et al. (University of Oxford)
- **arXiv**: [2410.20597](https://arxiv.org/abs/2410.20597) | 2024年10月 | 170 Visits, 35 Likes
- **概要**: 金融アナリストのカバレッジネットワークからモメンタムシグナルを抽出。アナリスト間の情報仲介役割に着目。
- **投資への示唆**: セルサイドアナリストネットワークのグラフ分析がアルファ源泉となる可能性

#### GNN関連の追加研究

| 論文 | 著者/機関 | arXiv | 概要 |
|------|-----------|-------|------|
| GrifFinNet | Dai et al. (Jilin Univ.) | [2510.10387](https://arxiv.org/abs/2510.10387) | Graph-Relation統合Transformerで株式リターン予測 |
| Forecasting Equity Correlations | Fanshawe et al. | [2601.04602](https://arxiv.org/abs/2601.04602) | S&P500構成銘柄の相関予測にハイブリッドTransformer-GNN |
| Large-scale Portfolio Optimization using GAT | Korangi et al. (Southampton) | [2407.15532](https://arxiv.org/abs/2407.15532) | Graph Attention Networkでポートフォリオ最適化 |
| Dynamic GNN for Volatility | Kumar et al. (Cardiff) | [2410.16858](https://arxiv.org/abs/2410.16858) | 動的GNNでボラティリティ予測 |
| GNN Review in Finance | Wang et al. (Fudan) | [2111.15367](https://arxiv.org/abs/2111.15367) | 金融GNN応用の包括的サーベイ（381 Visits） |

### 1.3 技術的洞察

```
ナレッジグラフ構築パイプライン:
  非構造化データ（ニュース、SEC filing、決算書）
    → LLMによるエンティティ・関係抽出（ICKG等）
      → 動的KG構築（四つ組: entity, relation, entity, timestamp）
        → グラフ分析（中心性指標、リンク予測）
          → 投資シグナル生成（テーマ投資、モメンタム）
```

**Neo4jとの関連性**: 上記研究のグラフスキーマ（エンティティノード、関係エッジ、時系列プロパティ）はNeo4jの Property Graph モデルと直接対応する。特にFinDKGのDKGアプローチは、Neo4jのTemporal機能と組み合わせることで実装可能。

---

## 2. 運用会社の戦略レプリケート

### 2.1 概要

ヘッジファンドやCTAの運用戦略を機械学習で複製・近似する研究。ファクター分析、ベイジアン手法、LLMによる自動アルファ発見等のアプローチがある。

### 2.2 主要論文

#### Hedge Fund Portfolio Construction Using PolyModel Theory and iTransformer
- **著者**: Siqiao Zhao et al. (Stony Brook, Morgan Stanley, Barclays, Paris 1)
- **arXiv**: [2408.03320](https://arxiv.org/abs/2408.03320) | 2024年8月 | 225 Visits, 20 Likes
- **概要**: PolyModel理論とiTransformerを組み合わせたヘッジファンドポートフォリオ構築。
- **手法**:
  - PolyModel: 各資産を複数のリスクファクターで回帰、スパースデータ問題を解決
  - iTransformer: 時系列予測の最新アーキテクチャ
  - PolyModelの出力（ストレス指標、非線形リスク）をiTransformerの特徴量として使用
- **投資への示唆**: スパースな金融時系列データでの機械学習適用手法として実用的

#### Re-evaluating CTA Replication: A Bayesian Graphical Approach
- **著者**: 著者情報 | **arXiv**: [2507.15876](https://arxiv.org/abs/2507.15876) | 2025年7月
- **概要**: CTAのトレンドフォロー戦略を短期・長期トレンドファクターで分解し、ベイジアングラフィカルモデルで再評価。
- **手法**: ベイジアンネットワークによるファクター間依存関係のモデリング
- **投資への示唆**: CTA戦略のレプリケーションにおいてファクター選択の妥当性を再検証

#### Automate Strategy Finding with LLM in Quant Investment
- **著者**: Zhizhuo Kou et al. (HKUST, Peking University)
- **arXiv**: [2409.06289](https://arxiv.org/abs/2409.06289) | 2024年9月
- **概要**: LLMベースの3段階フレームワークで定量投資戦略を自動発見。
- **手法**:
  1. **アルファファクター抽出**: 金融文献からLLMがファクターを抽出・分類（モメンタム、ファンダメンタル、流動性等）
  2. **マルチエージェント最適化**: リスク考慮型のマルチエージェントシステムでファクター評価
  3. **戦略生成**: 最適なファクター組み合わせから取引戦略を自動生成
- **成果**: 中国・米国市場で既存ベンチマークを上回るパフォーマンス
- **投資への示唆**: 文献ベースのアルファ発見を自動化する画期的アプローチ

#### Fund2Vec: Mutual Funds Similarity using Graph Learning
- **著者**: Vipul Satone et al. (Vanguard)
- **arXiv**: [2106.12987](https://arxiv.org/abs/2106.12987) | 2021年6月
- **概要**: グラフ学習で投資信託の類似性を定量化。ファンド推薦、競合分析、ポートフォリオ分析に応用。
- **投資への示唆**: ファンドスタイル分析とレプリケーション対象の特定に有用

#### 追加の関連研究

| 論文 | 著者/機関 | arXiv | 概要 |
|------|-----------|-------|------|
| E2EAI | Wei et al. (Shanghai AI Lab, CUHK) | [2305.16364](https://arxiv.org/abs/2305.16364) | End-to-Endのファクターベース投資フレームワーク |
| Index Tracking via Learning | Hong et al. (Mirae Asset) | [2209.00780](https://arxiv.org/abs/2209.00780) | 市場感応度学習によるインデックストラッキング |
| PolyModel for Hedge Funds | Zhao et al. (Stevens, Paris 1) | [2412.11019](https://arxiv.org/abs/2412.11019) | PolyModelのヘッジファンド応用詳細版 |
| Learning to Manage Portfolios | ICAIF '25 | [2510.26165](https://arxiv.org/abs/2510.26165) | 単純効用関数を超えたポートフォリオ管理学習 |

### 2.3 技術的洞察

```
戦略レプリケーションの主要アプローチ:

1. ファクター分解型
   運用戦略 → リスクファクター分解 → ファクターエクスポージャー推定 → レプリケーションポートフォリオ

2. LLM自動発見型
   金融文献 → LLMファクター抽出 → マルチエージェント評価 → 自動戦略生成

3. グラフ類似性型
   ファンドポートフォリオ → グラフ埋め込み → 類似ファンド特定 → スタイル複製
```

---

## 3. AI エージェントによる運用チームの構築

### 3.1 概要

LLMベースのマルチエージェントシステムで、実際の投資チーム（アナリスト、トレーダー、リスクマネージャー等）の役割分担をシミュレートする研究が2024年後半から爆発的に増加。2026年2月の最新論文まで含め、最も活発な研究領域。

### 3.2 主要論文

#### TradingAgents: Multi-Agents LLM Financial Trading Framework ⭐
- **著者**: Yijia Xiao et al. (UCLA)
- **arXiv**: [2412.20138](https://arxiv.org/abs/2412.20138) | 2024年12月 | **8,559 Visits, 239 Likes**
- **概要**: 実際のトレーディングファームの組織構造を模倣したマルチエージェントフレームワーク。
- **アーキテクチャ**:
  ```
  ┌─────────────────────────────────────────────┐
  │              Fund Manager（最終決定）           │
  ├─────────────────────────────────────────────┤
  │  Analyst Team          │  Researcher Team      │
  │  ├ Fundamental Analyst  │  ├ Bullish Researcher │
  │  ├ Sentiment Analyst    │  └ Bearish Researcher │
  │  ├ News Analyst         │    （ディベート形式）    │
  │  └ Technical Analyst    │                       │
  ├─────────────────────────────────────────────┤
  │  Trader Agents          │  Risk Management Team │
  │  （売買タイミング決定）    │  （エクスポージャー監視） │
  └─────────────────────────────────────────────┘
  ```
- **特徴**:
  - アナリストチームが市場データを多角的に分析
  - 強気/弱気リサーチャーがディベート形式でリスク・リターンを評価
  - リスク管理チームがリアルタイムでエクスポージャーを監視
  - ファンドマネージャーが最終的な取引を承認・執行
- **成果**: 単一エージェントシステムを大幅に上回るパフォーマンス

#### AlphaAgents: LLM-based Multi-Agents for Equity Portfolio Construction ⭐
- **著者**: Tianjiao Zhao et al. (**BlackRock**)
- **arXiv**: [2508.11152](https://arxiv.org/abs/2508.11152) | 2025年8月 | 851 Visits, 66 Likes
- **概要**: BlackRockによるLLMマルチエージェントの株式ポートフォリオ構築フレームワーク。
- **重要性**: 世界最大の資産運用会社がマルチエージェントAIの実用化研究を発表
- **投資への示唆**: 機関投資家レベルでのAIエージェント活用が現実のものとなりつつある

#### Toward Expert Investment Teams: Multi-Agent LLM System with Fine-Grained Trading Tasks ⭐（最新）
- **著者**: Kunihiro Miyazaki et al. (Oxford, Stefan Zohren)
- **arXiv**: [2602.23330](https://arxiv.org/abs/2602.23330) | **2026年2月** | 223 Visits, 24 Likes
- **概要**: 細粒度のトレーディングタスクを持つマルチエージェントLLMシステム。
- **特徴**: アナリスト・マネージャーの役割を模倣する主流アプローチを超え、各エージェントに精緻なトレーディングタスクを割り当て
- **投資への示唆**: エージェント専門化の粒度が性能に大きく影響することを示す

#### FinCon: Synthesized LLM Multi-Agent System with Conceptual Verbal Reinforcement
- **著者**: Yangyang Yu et al. (Wuhan Univ., Stony Brook, Stevens)
- **arXiv**: [2407.06567](https://arxiv.org/abs/2407.06567) | 2024年7月 | 1,251 Visits, 30 Likes
- **概要**: Manager-Analyst階層構造 + Conceptual Verbal Reinforcement (CVRF) による学習。
- **アーキテクチャ**:
  - **Analyst エージェント**: 各データソース専門の分析担当
  - **Manager エージェント**: アナリストの洞察を統合し取引判断
  - **CVRF**: テキストベースの勾配降下法で投資信念を更新
  - **リスク制御**: エピソード内（リアルタイム）+ エピソード間（学習時）の二重制御
- **成果**: 多様な市場環境で汎化性能を実証

#### HedgeAgents: A Balanced-aware Multi-agent Financial Trading System
- **著者**: Xiangyu Li et al. (South China Univ. of Tech., ByteDance)
- **arXiv**: [2502.13165](https://arxiv.org/abs/2502.13165) | 2025年2月 | 1,028 Visits, 73 Likes
- **概要**: ヘッジ戦略を統合したバランス重視型マルチエージェントトレーディングシステム。
- **特徴**: 既存のLLMベースシステム（FinGPT等）が「頻繁な変動」シナリオで-15%〜-20%の損失を出す問題に対処

#### FinRobot: AI Agent for Equity Research and Valuation
- **著者**: Tianyu Zhou et al. (NTU, Columbia, AI4Finance)
- **arXiv**: [2411.08804](https://arxiv.org/abs/2411.08804) | 2024年11月 | 287 Visits, 14 Likes
- **概要**: セルサイドリサーチを自動化するAIエージェント。株式リサーチレポートとバリュエーション分析を生成。

#### QuantAgents: Multi-agent Financial System via Simulated Trading
- **著者**: Xiangyu Li et al. (South China Univ. of Tech.)
- **arXiv**: [2510.04643](https://arxiv.org/abs/2510.04643) | 2025年10月 | 139 Visits, 12 Likes
- **概要**: シミュレーテッドトレーディングで訓練するマルチエージェント金融システム。プロの金融専門家が広く使用するシミュレーテッドトレーディング技法をAIエージェントに適用。

#### その他の関連マルチエージェント研究

| 論文 | 著者/機関 | arXiv | 概要 |
|------|-----------|-------|------|
| Enhancing Investment Analysis | Han et al. (Tsinghua, Maryland, Columbia) | [2411.04788](https://arxiv.org/abs/2411.04788) | GenAIエージェント協調による投資分析 |
| Agentic AI in Financial Services | Okpala et al. (Discover Financial) | [2502.05439](https://arxiv.org/abs/2502.05439) | 金融サービスでのAgenticクルー（モデリング+MRM） |
| FinVision | Fatemi et al. (UIC) | [2411.08899](https://arxiv.org/abs/2411.08899) | マルチモーダルマルチエージェント株価予測 |
| ContestTrade | Zhao et al. (StepFun) | [2508.00554](https://arxiv.org/abs/2508.00554) | 内部コンテスト機構によるノイズ耐性 |
| TradingGroup | Tian et al. (UNSW) | [2508.17565](https://arxiv.org/abs/2508.17565) | 自己反省とデータ合成による改善 |
| Trade in Minutes | Song et al. (Tongji, Fudan, Microsoft) | [2510.04787](https://arxiv.org/abs/2510.04787) | 合理性駆動型の高速トレーディング |
| R&D-Agent-Quant | HKUST | [2505.15155](https://arxiv.org/abs/2505.15155) | ファクター・モデル同時最適化 |
| FLAG-Trader | HKUST | [2502.11433](https://arxiv.org/abs/2502.11433) | LLM+勾配ベースRL融合トレーダー |
| AI Agents in Financial Markets | Gong | [2603.13942](https://arxiv.org/abs/2603.13942) | **2026年3月**最新サーベイ |

### 3.3 技術的洞察

```
マルチエージェント投資チームの典型的構成:

Level 1: データ収集層
  ├ Market Data Agent（株価、出来高）
  ├ News Agent（ニュース収集・要約）
  ├ Fundamentals Agent（財務データ、SEC filing）
  └ Sentiment Agent（SNS、アナリストレポート）

Level 2: 分析層
  ├ Technical Analyst（テクニカル分析）
  ├ Fundamental Analyst（ファンダメンタル分析）
  ├ Sentiment Analyst（センチメント分析）
  └ Macro Analyst（マクロ経済分析）

Level 3: 意思決定層
  ├ Bullish Researcher（強気論）
  ├ Bearish Researcher（弱気論）
  └ Debate/Consensus mechanism

Level 4: 執行・管理層
  ├ Portfolio Manager（ポートフォリオ構築）
  ├ Risk Manager（リスク管理）
  └ Trader Agent（注文執行）
```

---

## 4. 包括的サーベイ論文

直近の重要なサーベイ論文を参照することで、各領域の全体像を把握できる。

| 論文 | arXiv | 発表 | 規模 | 主要トピック |
|------|-------|------|------|-------------|
| From Deep Learning to LLMs: A Survey of AI in Quant Investment | [2503.21422](https://arxiv.org/abs/2503.21422) | 2025/3 | **3,645 Visits** | DL→LLMの進化、アルファ生成、ポートフォリオ管理 |
| The New Quant: LLMs in Financial Prediction and Trading | [2510.05533](https://arxiv.org/abs/2510.05533) | 2025/10 | 111 Visits | LLMが定量投資を再形成する方法 |
| Quant 4.0: Automated, Explainable, Knowledge-driven AI | [2301.04020](https://arxiv.org/abs/2301.04020) | 2023/1 | 118 Visits | 知識駆動型AIの統合ビジョン |
| A Survey of Financial AI: Architectures, Advances, Challenges | [2411.12747](https://arxiv.org/abs/2411.12747) | 2024/11 | 277 Visits | 金融AIの包括的分類 |
| From Factor Models to Deep Learning | [2403.06779](https://arxiv.org/abs/2403.06779) | 2024/3 | 148 Visits | ファクターモデル→DLの進化 |
| LLM Agent in Financial Trading: A Survey | [2408.06361](https://arxiv.org/abs/2408.06361) | 2024/7 | 1,259 Visits | LLMエージェントのトレーディング応用 |
| Integrating LLMs in Financial Investments | [2507.01990](https://arxiv.org/abs/2507.01990) | 2025/6 | 94 Visits | LLMの投資戦略統合 |
| The Evolution of Alpha: Human Insight and LLM Agents | [2505.14727](https://arxiv.org/abs/2505.14727) | 2025/5 | 86 Visits | アルファ追求の進化史 |

---

## 5. 当プロジェクト（quants）への応用可能性

### 5.1 ナレッジグラフ（Neo4j）との統合

| 研究知見 | quants への適用 | 参照論文 |
|---------|----------------|---------|
| LLMによる動的KG構築 | SEC filing/ニュースからのエンティティ抽出パイプライン強化 | FinDKG |
| 企業間関係グラフ | CompanyKGスキーマのNeo4jへの実装 | CompanyKG |
| テーマ投資シグナル | KGベースのテーマエクスポージャー推定 | FinDKG |
| アナリストネットワーク | セルサイドカバレッジネットワークの構築 | Extracting Alpha |

### 5.2 ca_strategy パッケージの拡張

| 研究知見 | ca_strategy への適用 | 参照論文 |
|---------|---------------------|---------|
| マルチエージェント意思決定 | エージェント間のディベート機構追加 | TradingAgents |
| CVRF学習 | テキストベース投資信念更新の実装 | FinCon |
| ヘッジ統合 | バランス重視型ポートフォリオ構築 | HedgeAgents |
| ファクター自動発見 | LLMによるアルファファクター抽出 | Automate Strategy Finding |

### 5.3 将来のアーキテクチャ方向性

```
現在の quants アーキテクチャ:
  market → analyze → factor → strategy → ca_strategy

提案拡張（研究知見に基づく）:
  market ─┐
  edgar  ─┼→ knowledge_graph (Neo4j) ─→ graph_signals
  news   ─┘                              │
                                          ▼
  ca_strategy ←─── multi_agent_team ←─── signal_aggregator
      │                   │
      ▼                   ▼
  portfolio_output    risk_monitor
```

---

## 6. 研究動向のまとめ

### トレンド分析

1. **2022-2023**: Quant 4.0ビジョン提唱、GNN in Financeサーベイ、CompanyKG公開
2. **2024前半**: FinDKG、FinCon登場、LLMエージェントの金融応用が本格化
3. **2024後半**: TradingAgents（8,500+ Visits）がブレークスルー、マルチエージェント研究が爆発的増加
4. **2025**: BlackRock AlphaAgents、HedgeAgents、QuantAgents等の実用志向研究
5. **2026**: Expert Investment Teams（Oxford）、AI Agents in Financial Marketsサーベイ

### 主要な未解決課題

| 課題 | 説明 | 参照 |
|------|------|------|
| 市場ノイズへの感度 | LLMエージェントがプロンプトに過敏に反応 | ContestTrade |
| 長期パフォーマンス | 短期では有効でも長期で市場に負けるケースあり | LLM Agents Do Not Replicate Human Traders |
| 計算コスト | マルチエージェント実行の高コスト | 複数論文共通 |
| 説明可能性 | AI投資判断の説明・監査 | Quant 4.0 |
| データ品質 | KG構築時のエンティティ解決・関係抽出精度 | FinDKG, CompanyKG |

### 推奨アクション

1. **短期**: FinDKGのアプローチを参考に、Neo4j上でのテーマ投資KG構築をPoC
2. **中期**: TradingAgentsアーキテクチャを参考に、ca_strategyのマルチエージェント化
3. **長期**: Quant 4.0ビジョンに基づく知識駆動型+データ駆動型AIの統合

---

## 参考文献一覧（arXiv ID順）

1. `2106.12987` - Fund2Vec (Vanguard)
2. `2111.15367` - GNN Review in Finance (Fudan)
3. `2207.07183` - Learning Embedded Representation of Stock Correlation (BlackRock)
4. `2301.04020` - Quant 4.0 (HKUST)
5. `2304.00323` - Company Competition Graph (Michigan State, Oxford)
6. `2305.16364` - E2EAI (Shanghai AI Lab)
7. `2306.10649` - CompanyKG (EQT)
8. `2403.06779` - From Factor Models to Deep Learning (NJIT)
9. `2407.06567` - FinCon (Wuhan Univ., Stony Brook)
10. `2407.10909` - FinDKG (Imperial College London)
11. `2407.15532` - Large-scale Portfolio Optimization using GAT (Southampton)
12. `2408.03320` - Hedge Fund Portfolio Construction (Stony Brook, Morgan Stanley)
13. `2408.06361` - LLM Agent in Financial Trading Survey (NYU, Columbia)
14. `2409.06289` - Automate Strategy Finding with LLM (HKUST)
15. `2410.16858` - Dynamic GNN for Volatility (Cardiff)
16. `2410.20597` - Extracting Alpha from Analyst Networks (Oxford)
17. `2411.04788` - Enhancing Investment Analysis (Tsinghua, Columbia)
18. `2411.08804` - FinRobot (NTU, Columbia)
19. `2411.08899` - FinVision (UIC)
20. `2411.12747` - A Survey of Financial AI (Forth AI)
21. `2412.11019` - PolyModel for Hedge Funds (Stevens, Paris 1)
22. `2412.20138` - TradingAgents (UCLA)
23. `2502.05439` - Agentic AI in Financial Services (Discover Financial)
24. `2502.13165` - HedgeAgents (South China UT, ByteDance)
25. `2502.15800` - LLM Agents Do Not Replicate Human Traders
26. `2503.21422` - From Deep Learning to LLMs Survey (HKUST)
27. `2505.14727` - The Evolution of Alpha (George Mason)
28. `2505.15155` - R&D-Agent-Quant (HKUST)
29. `2507.01990` - Integrating LLMs in Financial Investments (Blend360)
30. `2507.15876` - Re-evaluating CTA Replication
31. `2507.21969` - Towards Cognitive Synergy in MAS
32. `2508.00554` - ContestTrade (StepFun)
33. `2508.11152` - AlphaAgents (BlackRock)
34. `2508.17565` - TradingGroup (UNSW)
35. `2510.04643` - QuantAgents (South China UT)
36. `2510.04787` - Trade in Minutes (Tongji, Microsoft)
37. `2510.05533` - The New Quant (Columbia)
38. `2510.10387` - GrifFinNet (Jilin Univ.)
39. `2510.15691` - Quant Factors + LLM Newsflow
40. `2510.26165` - Learning to Manage Portfolios (ICAIF)
41. `2601.04602` - Forecasting Equity Correlations (Hybrid Transformer-GNN)
42. `2602.23330` - Toward Expert Investment Teams (Oxford)
43. `2603.13942` - AI Agents in Financial Markets (2026/3 最新)
