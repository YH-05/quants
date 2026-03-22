# 検索クエリ生成テンプレート

ギャップ分析結果から `embedding_similarity_search` 用の 2-3 文クエリを生成するテンプレート集。

## alphaxiv-search スキル準拠ルール

- クエリは **2-3 文の詳細な記述**（キーワードではない）
- 構造: [研究領域 1 文] + [含めるべき手法/概念 1 文] + [応用文脈 1 文]
- 英語で記述する（alphaxiv は英語論文データベース）

## ギャップ種別ごとのテンプレート

### 1. 孤立 Topic 用

```
テンプレート:
"Research on {topic_name} in quantitative finance and investment management.
Papers covering {topic_name} methods, theoretical foundations, and practical
applications to portfolio management, risk assessment, and algorithmic trading strategies."
```

例:
```
"Research on Spiking Neural Networks for Finance in quantitative finance
and investment management. Papers covering bio-inspired neural computation,
event-driven processing, and applications to high-frequency trading,
time series prediction, and energy-efficient financial model deployment."
```

### 2. 薄い Topic 用

```
テンプレート:
"Recent advances in {topic_name} for financial applications since 2023.
Novel approaches to {topic_name} including {related_method_1}, {related_method_2},
and large language model integration. Empirical evaluations on financial datasets
covering {application_1} and {application_2}."
```

例:
```
"Recent advances in Conformal Prediction for Finance since 2023.
Novel approaches including distribution-free uncertainty quantification,
adaptive conformal intervals, and integration with deep learning models.
Empirical evaluations on financial datasets covering portfolio risk bounds
and trading signal calibration."
```

### 3. 未接続 Method 用

```
テンプレート:
"Academic papers using {method_name} for financial prediction and portfolio optimization.
Studies applying {method_name} to stock market forecasting, asset allocation,
derivatives pricing, and market microstructure analysis.
Benchmark comparisons with traditional quantitative finance approaches."
```

例:
```
"Academic papers using Kolmogorov-Arnold Networks for financial prediction
and portfolio optimization. Studies applying KAN to stock market forecasting,
nonlinear factor modeling, and volatility surface fitting.
Benchmark comparisons with MLP, LSTM, and Transformer architectures."
```

### 4. 時系列ギャップ用

```
テンプレート:
"Machine learning and AI research for quantitative finance published in {year}.
Papers from {year} covering new deep learning architectures, foundation models,
reinforcement learning, and large language models applied to trading,
investment, and risk management. Focus on {specific_topic} if applicable."
```

例:
```
"Machine learning and AI research for quantitative finance published in 2026.
Papers from 2026 covering frontier model applications, agentic AI for trading,
multimodal financial analysis, and real-time market prediction systems.
Focus on LLM-driven portfolio construction and autonomous trading agents."
```

### 5. クロスドメイン用（Long-Tail）

```
テンプレート:
"Intersection of {topic_1} and {topic_2} in quantitative finance and investment.
Research combining {topic_1} techniques with {topic_2} approaches
for novel investment strategies, enhanced market prediction, and risk management.
Cross-disciplinary applications bridging these two domains."
```

例:
```
"Intersection of Graph Neural Networks and Market Regime Detection
in quantitative finance. Research combining GNN-based relationship modeling
with regime-switching approaches for dynamic portfolio allocation,
systemic risk propagation analysis, and adaptive strategy selection."
```

## クエリ修飾パターン

searched_queries と類似度が高い（Jaccard > 0.7）場合に適用する修飾。

### 修飾 A: サブトピック限定

元: "Research on Deep RL for Portfolio Optimization..."
修飾後: "Research on **model-based** Deep RL for Portfolio Optimization, focusing on **world model learning** and **planning-based approaches** for asset allocation..."

### 修飾 B: 応用ドメイン変更

元: "...applied to stock market forecasting..."
修飾後: "...applied to **fixed income markets, credit derivatives**, and **commodity futures** forecasting..."

### 修飾 C: 時期限定

元: "Research on Transformer Architectures for Finance..."
修飾後: "**2025-2026 advances** in Transformer Architectures for Finance, including **state space model hybrids, efficient attention**, and **post-training quantization** for financial deployment..."

### 修飾 D: 対比・比較

元: "Research on GNN for Financial Networks..."
修飾後: "**Comparative studies** of GNN versus **hyperbolic embeddings** and **attention-based** approaches for financial network analysis and **supply chain risk propagation**..."

## クエリ品質チェックリスト

生成したクエリが以下を満たすことを確認:

- [ ] 英語で記述されている
- [ ] 2-3 文で構成されている（1 文や 4 文以上は不可）
- [ ] 具体的な手法名・概念名を含む
- [ ] "quantitative finance" / "investment" / "trading" 等の金融コンテキストを含む
- [ ] 単なるキーワード列挙ではなく、研究領域を描写する文章になっている
- [ ] searched_queries 内の既存クエリと大きく異なる表現になっている
