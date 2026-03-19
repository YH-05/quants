# クオンツ戦略論文コレクション: ファクター投資

収集日: 2026-03-19
ソース: arXiv / alphaXiv
収集数: 31本

---

## 目次

1. [ファクターモデル基盤 & 資産価格付け](#1-ファクターモデル基盤--資産価格付け)
2. [深層学習 × ファクターモデル](#2-深層学習--ファクターモデル)
3. [アルファマイニング & ファクター発見](#3-アルファマイニング--ファクター発見)
4. [LLM/センチメント × ファクター投資](#4-llmセンチメント--ファクター投資)
5. [マルチファクター・ポートフォリオ構築](#5-マルチファクター・ポートフォリオ構築)
6. [ファクタータイミング & 動的配分](#6-ファクタータイミング--動的配分)
7. [モメンタム & トレンドフォロー](#7-モメンタム--トレンドフォロー)
8. [統計的裁定 & ファクターベース取引](#8-統計的裁定--ファクターベース取引)
9. [サーベイ論文](#9-サーベイ論文)

---

## 1. ファクターモデル基盤 & 資産価格付け

### 1-1. Deep Learning in Asset Pricing

| 項目 | 内容 |
|------|------|
| arXiv ID | [1904.00745](https://arxiv.org/abs/1904.00745) |
| 著者 | Luyang Chen, Markus Pelger, Jason Zhu |
| 所属 | Stanford University |
| 発表 | 2021 (初版 2019) |

**概要**: 深層ニューラルネットワークを用いて個別株リターンの資産価格付けモデルを推定。46の企業特性と178のマクロ経済変数を条件付け情報として使用。年率アウトオブサンプルSharpe比2.6を達成し、線形モデル（1.7）を大幅に上回る。

**キーポイント**:
- GAN的アプローチでSDFを推定
- CRSP全銘柄の1967-2016月次データを使用
- 非線形ファクター構造の重要性を実証

---

### 1-2. Consensus-Bottleneck Asset Pricing Model (CB-APM)

| 項目 | 内容 |
|------|------|
| arXiv ID | [2512.16251](https://arxiv.org/abs/2512.16251) |
| 著者 | (複数著者) |
| 発表 | 2025-12 |

**概要**: 深層学習の予測力と伝統的ファイナンスの構造的透明性を両立するフレームワーク。情報ボトルネックを埋め込み、解釈可能なファクター構造を維持しながら高い予測性能を達成。

**キーポイント**:
- Fama-French 3/5ファクターモデルとの理論的整合性
- コンセンサスメカニズムによる解釈可能性
- 学術研究と実務の両立を目指す設計

---

### 1-3. Deep Learning in Characteristics-Sorted Factor Models

| 項目 | 内容 |
|------|------|
| arXiv ID | [1805.01104](https://arxiv.org/abs/1805.01104) |
| 著者 | Guanhao Feng, Jingyu He, Nicholas G. Polson, Jianeng Xu |
| 所属 | University of Chicago, City University of Hong Kong |
| 発表 | 2023 (初版 2018) |

**概要**: 拡張型深層ファクターモデルを提案。企業特性ソーティングによるファクター構築の従来手法を深層学習で拡張し、クロスセクションの資産価格付けのための潜在ファクターを生成。

**キーポイント**:
- 特性ソートポートフォリオの非線形拡張
- ロング・ショート戦略の改善
- 潜在ファクターの経済的解釈

---

### 1-4. Does Peer-Reviewed Research Help Predict Stock Returns?

| 項目 | 内容 |
|------|------|
| arXiv ID | [2212.10317](https://arxiv.org/abs/2212.10317) |
| 著者 | Andrew Y. Chen, Tom Zimmermann |
| 発表 | 2024 (初版 2022) |

**概要**: 29,000の会計比率からt統計量2.0以上をマイニングした場合と、査読プロセスによるファクター選定の予測力を比較。両手法とも約50%の予測力がアウトオブサンプルで残存。

**キーポイント**:
- ファクターズーの再現性問題に切り込むメタ研究
- データマイニングと査読の比較
- p-hackingの限界を実証

---

### 1-5. Predicting the Distributions of Stock Returns

| 項目 | 内容 |
|------|------|
| arXiv ID | [2408.07497](https://arxiv.org/abs/2408.07497) |
| 著者 | (複数著者) |
| 発表 | 2024-08 |

**概要**: 194の株式特性とマーケット変数を用いて、株式リターンの完全な分布を予測する手法を提案。条件付き分布の学習により、ポートフォリオ最適化やリスク管理に活用可能。

**キーポイント**:
- ポイント予測ではなく分布全体を予測
- 194の企業特性を包括的に使用
- リスク管理への直接適用可能

---

### 1-6. Growing the Efficient Frontier on Panel Trees (P-Trees)

| 項目 | 内容 |
|------|------|
| arXiv ID | [2501.16730](https://arxiv.org/abs/2501.16730) |
| 著者 | (複数著者) |
| 発表 | 2025-01 |

**概要**: パネルデータ向けの新しいツリーベースモデル「P-Trees」を導入。高次元ソーティングを経済的ガイダンスと解釈可能性を持って一般化し、効率的フロンティアを拡張。

**キーポイント**:
- 不均衡パネルデータに対応
- 経済理論によるガイダンス付きソーティング
- Fama-Frenchファクターを上回る性能

---

## 2. 深層学習 × ファクターモデル

### 2-1. Factor Investing with a Deep Multi-Factor Model

| 項目 | 内容 |
|------|------|
| arXiv ID | [2210.12462](https://arxiv.org/abs/2210.12462) |
| 著者 | Zikai Wei, Bo Dai, Dahua Lin |
| 所属 | Shanghai AI Laboratory, CUHK |
| 発表 | 2022-10 |

**概要**: 深層学習ベースのマルチファクターモデルを提案。新しいファクターの発見と特性評価を同時に行い、ベンチマークを上回る超過リターンの達成を目指す。

**キーポイント**:
- End-to-endでファクター構築と銘柄選定
- 伝統的ファクターとの比較分析
- 中国A株・米国株での実証

---

### 2-2. Deep Portfolio Optimization via Distributional Prediction of Residual Factors

| 項目 | 内容 |
|------|------|
| arXiv ID | [2012.07245](https://arxiv.org/abs/2012.07245) |
| 著者 | Kentaro Imajo, Kentaro Minami, Katsuya Ito, Kei Nakagawa |
| 所属 | (日本の研究者チーム) |
| 発表 | 2020-12 |

**概要**: 残差ファクターの分布予測を通じた深層ポートフォリオ最適化。金融市場の非定常性に対処するため、分布予測アプローチを採用。

**キーポイント**:
- 残差リターンの分布予測
- 非定常性への対処
- 日本市場での実証を含む

---

### 2-3. From Factor Models to Deep Learning: ML in Reshaping Empirical Asset Pricing

| 項目 | 内容 |
|------|------|
| arXiv ID | [2403.06779](https://arxiv.org/abs/2403.06779) |
| 著者 | Junyi Ye, Bhaskar Goswami, Jingyi Gu, Ajim Uddin, Guiling Wang |
| 所属 | New Jersey Institute of Technology |
| 発表 | 2024-03 |

**概要**: ファクターモデルから深層学習への進化を包括的にレビュー。伝統的資産価格付けモデルからML/AIベースのアプローチへの移行を体系的に整理。

**キーポイント**:
- CAPM→FF3→FF5→ML/DLの系譜
- 各手法の長所・短所の比較
- 実務適用における課題の議論

---

### 2-4. Machine Learning and Factor-Based Portfolio Optimization

| 項目 | 内容 |
|------|------|
| arXiv ID | [2107.13866](https://arxiv.org/abs/2107.13866) |
| 著者 | Thomas Conlon, John Cotter, Iason Kynigakis |
| 所属 | University College Dublin |
| 発表 | 2021-07 |

**概要**: オートエンコーダ・ニューラルネットワークベースのファクターとポートフォリオ最適化を検討。特性ソートポートフォリオとの関係が弱いことを発見。

**キーポイント**:
- オートエンコーダファクター vs 伝統的ファクター
- ポートフォリオ最適化への統合
- ファクター選択のロバスト性分析

---

## 3. アルファマイニング & ファクター発見

### 3-1. AutoAlpha: Efficient Hierarchical Evolutionary Algorithm for Mining Alpha Factors

| 項目 | 内容 |
|------|------|
| arXiv ID | [2002.08245](https://arxiv.org/abs/2002.08245) |
| 著者 | Tianping Zhang, Yuanqi Li, Yifei Jin, Jian Li |
| 所属 | Tsinghua University |
| 発表 | 2020-04 |

**概要**: 階層的進化アルゴリズムによる効率的なアルファファクターマイニング。マルチファクターモデルの成功はアルファファクターの有効性に大きく依存するという課題に対処。

**キーポイント**:
- 遺伝的プログラミングベースのファクター探索
- 階層的構造による効率化
- 情報係数（IC）による評価

---

### 3-2. AlphaAgent: LLM-Driven Alpha Mining with Regularized Exploration

| 項目 | 内容 |
|------|------|
| arXiv ID | [2502.16789](https://arxiv.org/abs/2502.16789) |
| 著者 | (複数著者) |
| 発表 | 2025-02 |

**概要**: LLMを活用したアルファマイニングフレームワーク。アルファ減衰（alpha decay）に対抗するため、正則化探索メカニズムを導入。独自性強制、複雑性制御、仮説整合の3つのメカニズムを統合。

**キーポイント**:
- LLMによる自律的アルファ探索
- アルファ減衰への対処
- yfinanceベースの実証

---

### 3-3. Alpha-R1: Alpha Screening with LLM Reasoning via Reinforcement Learning

| 項目 | 内容 |
|------|------|
| arXiv ID | [2512.23515](https://arxiv.org/abs/2512.23515) |
| 著者 | (FinStep-AI) |
| 発表 | 2025-12 |

**概要**: 信号減衰とレジームシフトに対処するため、強化学習によるLLM推論でアルファスクリーニングを実行。非定常市場環境での適応的推論を実現。

**キーポイント**:
- RL + LLMのハイブリッドアプローチ
- レジームシフトへの適応
- オープンソース実装あり（GitHub）

---

### 3-4. Navigating the Alpha Jungle: LLM-Powered MCTS for Formulaic Factor Mining

| 項目 | 内容 |
|------|------|
| arXiv ID | [2505.11122](https://arxiv.org/abs/2505.11122) |
| 著者 | (複数著者) |
| 発表 | 2025-05 |

**概要**: モンテカルロ木探索（MCTS）とLLMを組み合わせた数式ベースのアルファファクターマイニング。従来の人間の専門知識に依存するアプローチを自動化。

**キーポイント**:
- MCTS + LLMの組合せ
- 数式ベースのファクター生成
- 探索効率の大幅改善

---

### 3-5. Interpretable Factors of Firm Characteristics

| 項目 | 内容 |
|------|------|
| arXiv ID | [2508.02253](https://arxiv.org/abs/2508.02253) |
| 著者 | Yuxiao Jiao, Guofu Zhou, Wu Zhu, Yingzi Zhu |
| 所属 | Tsinghua University, Washington University in St. Louis |
| 発表 | 2025-08 |

**概要**: 統計的効率性と経済的解釈可能性のバランスを取る新しいファクター構築フレームワーク。全特性を等しく使うのではなく、選択的にファクターを構築。

**キーポイント**:
- 解釈可能性を明示的に追求
- 特性選択メカニズム
- 従来のFF5モデルとの比較

---

## 4. LLM/センチメント × ファクター投資

### 4-1. Exploring the Synergy of Quantitative Factors and Newsflow from LLMs

| 項目 | 内容 |
|------|------|
| arXiv ID | [2510.15691](https://arxiv.org/abs/2510.15691) |
| 著者 | Tian Guo, Emmanuel Hauptmann |
| 発表 | 2025-10 |

**概要**: クオンツファクター（バリュー、クオリティ、グロース等）とLLMによるニュースフロー表現の相乗効果を検証。リターン予測、銘柄選定、ポートフォリオ最適化への応用。

**キーポイント**:
- 伝統的ファクター + LLMニュースの融合
- ファクター間の相補性を実証
- 実践的な投資戦略への適用

---

### 4-2. ChatGPT in Systematic Investing

| 項目 | 内容 |
|------|------|
| arXiv ID | [2510.26228](https://arxiv.org/abs/2510.26228) |
| 著者 | Nikolas Anic, Andrea Barbon, Ralf Seiz, Carlo Zarattini |
| 発表 | 2025-10 |

**概要**: LLMがクロスセクション・モメンタム戦略を改善できるか検証。企業固有ニュースから予測シグナルを抽出し、日次の米国株リターンと組み合わせ。

**キーポイント**:
- ChatGPTのモメンタム戦略への統合
- ニュースベースのシグナル抽出
- リスク調整後リターンの改善

---

### 4-3. Dynamic Asset Pricing: FinBERT Sentiment + Fama-French Five-Factor

| 項目 | 内容 |
|------|------|
| arXiv ID | [2505.01432](https://arxiv.org/abs/2505.01432) |
| 著者 | Chi Zhang |
| 所属 | Tianjin Chengjian University |
| 発表 | 2025-04 |

**概要**: FinBERTによるテキストベースの時変センチメントファクターをFF5モデルに統合。ドメイン特化型の深層学習モデルによるセンチメント定量化。

**キーポイント**:
- FinBERT + FF5の統合モデル
- 時変センチメントファクターの構築
- 伝統モデルのアルファ説明力向上

---

## 5. マルチファクター・ポートフォリオ構築

### 5-1. A Multi-Factor Market-Neutral Investment Strategy for NYSE Equities

| 項目 | 内容 |
|------|------|
| arXiv ID | [2412.12350](https://arxiv.org/abs/2412.12350) |
| 著者 | Georgios M. Gkolemis, Adwin Richie Lee, Amine Roudani |
| 所属 | Columbia University |
| 発表 | 2024-12 |

**概要**: NYSE銘柄を対象としたシステマティック・マーケットニュートラルなマルチファクター投資戦略。市場相関を最小化しながら安定したリターンを目指す。

**キーポイント**:
- マーケットニュートラル設計
- 複数ファクターの統合
- 実運用を意識した制約条件

---

### 5-2. Dynamic Inclusion and Bounded Multi-Factor Tilts for Robust Portfolio Construction

| 項目 | 内容 |
|------|------|
| arXiv ID | [2601.05428](https://arxiv.org/abs/2601.05428) |
| 著者 | Roberto Garrone |
| 発表 | 2026-01 |

**概要**: 推定誤差、非定常性、現実的な取引制約の下でロバストなポートフォリオ構築フレームワーク。動的な資産包含・除外とバウンド付きファクターティルトを組み合わせ。

**キーポイント**:
- 推定誤差に対するロバスト性
- 取引コスト・制約を考慮
- 最新論文（2026年1月）

---

### 5-3. Cross-Market Alpha: Testing Short-Term Trading Factors via Double-Selection LASSO

| 項目 | 内容 |
|------|------|
| arXiv ID | [2601.06499](https://arxiv.org/abs/2601.06499) |
| 著者 | Jin Du, Alexander Walter, Maxim Ulrich |
| 発表 | 2026-01 |

**概要**: クロスマーケット検証が不十分な短期取引ファクターの有効性を検証。中国市場で開発されたファクターの米国市場での再現性をDouble-Selection LASSOで分析。

**キーポイント**:
- クロスマーケット検証の重要性
- 短期トレーディングファクター
- LASSO正則化によるファクター選択

---

## 6. ファクタータイミング & 動的配分

### 6-1. Smart Beta Investing with Feature Saliency Hidden Markov Models

| 項目 | 内容 |
|------|------|
| arXiv ID | [1902.10849](https://arxiv.org/abs/1902.10849) |
| 著者 | Elizabeth Fons, Paula Dawson, Jeffrey Yau, Xiao-jun Zeng, John Keane |
| 所属 | University of Manchester, UC Berkeley, AllianceBernstein |
| 発表 | 2019-02 |

**概要**: 特徴量顕著性Hidden Markov Modelsによる動的資産配分システム。スマートベータ戦略のためのレジームスイッチングフレームワークを提案。

**キーポイント**:
- バリュー、クオリティ、グロース等のファクターETF
- HMMによるレジーム検出
- 動的ファクターローテーション

---

### 6-2. Dynamic Investment Strategies Through Market Classification and Volatility

| 項目 | 内容 |
|------|------|
| arXiv ID | [2504.02841](https://arxiv.org/abs/2504.02841) |
| 著者 | Jinhui Li, Wenjia Xie, Luis Seco |
| 所属 | University of Toronto, Tsinghua University |
| 発表 | 2025-03 |

**概要**: 市場分類とボラティリティに基づく動的投資フレームワーク。従来の静的戦略を上回る、不安定な市場でのポートフォリオ管理手法を提案。

**キーポイント**:
- 4つの従来手法の比較評価
- 機械学習による市場分類
- 動的 vs 静的戦略の実証比較

---

### 6-3. Factor Investing: A Bayesian Hierarchical Approach

| 項目 | 内容 |
|------|------|
| arXiv ID | [1902.01015](https://arxiv.org/abs/1902.01015) |
| 著者 | Guanhao Feng, Jingyu He |
| 発表 | 2020-09 (初版 2019) |

**概要**: リターンの予測可能性を前提としたアセットアロケーション問題。異質な時変係数を用いたベイズ階層（BH）アプローチによるマーケットタイミング手法を導入。

**キーポイント**:
- ベイズ階層モデルによるファクタータイミング
- 時変ファクタープレミアム
- ファクターロードの動的推定

---

### 6-4. Sector Rotation by Factor Model and Fundamental Analysis

| 項目 | 内容 |
|------|------|
| arXiv ID | [2401.00001](https://arxiv.org/abs/2401.00001) |
| 著者 | Runjia Yang, Beining Shi |
| 発表 | 2023-11 |

**概要**: ファクターモデルとファンダメンタル分析を活用したセクターローテーション戦略。体系的なセクター分類と実証分析に基づくアプローチ。

**キーポイント**:
- ファクターモデルベースのセクター評価
- ファンダメンタルメトリクスとの統合
- マクロ環境に応じた動的配分

---

## 7. モメンタム & トレンドフォロー

### 7-1. Two Centuries of Trend Following

| 項目 | 内容 |
|------|------|
| arXiv ID | [1404.3274](https://arxiv.org/abs/1404.3274) |
| 著者 | Y. Lemperiere, C. Deremble, P. Seager, M. Potters, J.P. Bouchaud |
| 発表 | 2014-04 |

**概要**: 4つの資産クラス（コモディティ、通貨、株式指数、債券）にわたり、非常に長い時間スケールでのトレンドフォロー戦略の異常リターンの存在を確立。

**キーポイント**:
- 200年以上のバックテストデータ
- 資産クラス横断の普遍性
- トレンドの持続メカニズムの理論的説明

---

### 7-2. TrendFolios: Momentum and Trend-Following in Multi-Asset Portfolios

| 項目 | 内容 |
|------|------|
| arXiv ID | [2506.09330](https://arxiv.org/abs/2506.09330) |
| 著者 | Joseph Lu, Randall R Rojas, Fiona C. Yeung, Patrick D. Convery |
| 所属 | UCLA, Conscious Capital Advisors |
| 発表 | 2025-06 |

**概要**: 複数資産クラスとリスクファクターにわたるモメンタム・トレンドフォローシグナルを活用したポートフォリオ構築フレームワーク。

**キーポイント**:
- マルチアセット対応
- モメンタム + トレンドフォローの統合
- リスクファクターレベルでのシグナル

---

### 7-3. Winners vs. Losers: Momentum with Intertemporal Choice for ESG Portfolios

| 項目 | 内容 |
|------|------|
| arXiv ID | [2505.24250](https://arxiv.org/abs/2505.24250) |
| 著者 | Ayush Jha, Abootaleb Shirvani, Ali Jaffri, Svetlozar T. Rachev, Frank J. Fabozzi |
| 所属 | Johns Hopkins, Texas Tech, Kean University |
| 発表 | 2025-05 |

**概要**: ESGレジームスイッチングとテールリスク意識報酬・リスクメトリクスを統合した状態依存モメンタムフレームワーク。動的計画法とフィニットホライズン最適化。

**キーポイント**:
- ESG × モメンタムの融合
- テールリスク考慮
- レジームスイッチング

---

## 8. 統計的裁定 & ファクターベース取引

### 8-1. Deep Learning Statistical Arbitrage

| 項目 | 内容 |
|------|------|
| arXiv ID | [2106.04028](https://arxiv.org/abs/2106.04028) |
| 著者 | Jorge Guijarro-Ordonez, Markus Pelger, Greg Zanotti |
| 所属 | Stanford University |
| 発表 | 2022-10 (初版 2021) |

**概要**: 統計的裁定の統一的概念フレームワークとデータ駆動型ソリューション。類似資産間の一時的な価格差異を深層学習で検出し、取引戦略に変換。

**キーポイント**:
- 統計的裁定の統一理論
- オートエンコーダベースのファクター構造
- Stanford発の高品質研究

---

### 8-2. Attention Factors for Statistical Arbitrage

| 項目 | 内容 |
|------|------|
| arXiv ID | [2510.11616](https://arxiv.org/abs/2510.11616) |
| 著者 | Elliot L. Epstein, Rose Wang, Jaewon Choi, Markus Pelger |
| 所属 | Stanford University, Hanwha Life |
| 発表 | 2025-10 |

**概要**: アテンションメカニズムを用いて類似資産の特定、ミスプライシングの検出、取引ポリシーの形成を同時に行うフレームワーク。

**キーポイント**:
- Transformer的アテンションの金融応用
- ファクター構造 + 裁定の統合
- Pelger研究室の最新成果

---

## 9. サーベイ論文

### 9-1. From Deep Learning to LLMs: A Survey of AI in Quantitative Investment

| 項目 | 内容 |
|------|------|
| arXiv ID | [2503.21422](https://arxiv.org/abs/2503.21422) |
| 著者 | Bokai Cao, Saizhuo Wang, Xinyi Lin 他 |
| 所属 | HKUST (Guangzhou), IDEA Research |
| 発表 | 2025-03 |
| 注目度 | 3,645 Visits, 245 Likes |

**概要**: クオンツ投資におけるAIの包括的サーベイ。深層学習からLLMへの進化を体系的にカバー。資産管理における技術駆動型アプローチの全体像を提供。

**キーポイント**:
- 最も引用・閲覧されたサーベイ論文の一つ
- DL→LLMの系譜を網羅
- 実務・学術両面のカバレッジ

---

### 9-2. The Evolution of Reinforcement Learning in Quantitative Finance

| 項目 | 内容 |
|------|------|
| arXiv ID | [2408.10932](https://arxiv.org/abs/2408.10932) |
| 著者 | (複数著者) |
| 発表 | 2024-08 |

**概要**: 過去10年の強化学習の金融応用に関する包括的サーベイ。167本の論文を批判的に評価。ファクター投資、アルゴリズム取引、ポートフォリオ管理等を網羅。

**キーポイント**:
- 167本の論文をレビュー
- RL × ファクター投資のセクション有り
- 実装上の課題を詳細に議論

---

### 9-3. Quant 4.0: Automated, Explainable and Knowledge-driven AI

| 項目 | 内容 |
|------|------|
| arXiv ID | [2301.04020](https://arxiv.org/abs/2301.04020) |
| 著者 | Jian Guo, Saizhuo Wang, Lionel M. Ni, Heung-Yeung Shum |
| 所属 | HKUST (Guangzhou), IDEA Research |
| 発表 | 2022-12 |

**概要**: 次世代クオンツ投資のフレームワーク「Quant 4.0」を提唱。自動化、説明可能性、知識駆動型の3つの柱に基づくビジョン。

**キーポイント**:
- クオンツ投資の進化段階を定義
- AutoML/Explainable AIの適用
- 産学連携の視点

---

## 統計サマリー

| カテゴリ | 本数 |
|---------|------|
| ファクターモデル基盤 | 6 |
| 深層学習 × ファクター | 4 |
| アルファマイニング | 5 |
| LLM/センチメント × ファクター | 3 |
| マルチファクター構築 | 3 |
| ファクタータイミング | 4 |
| モメンタム & トレンドフォロー | 3 |
| 統計的裁定 | 2 |
| サーベイ | 3 |
| **合計** | **31** |

### 発表年分布

| 年 | 本数 |
|----|------|
| 2014-2019 | 5 |
| 2020-2022 | 8 |
| 2023-2024 | 7 |
| 2025-2026 | 11 |

### 所属機関（主要）

- Stanford University (3本)
- Tsinghua University (3本)
- HKUST / IDEA Research (2本)
- Columbia University (2本)
- University of Chicago (1本)
- Shanghai AI Lab / CUHK (2本)
- 日本研究者チーム (1本: Nomura AM系)

---

## 推奨読了順序

### Step 1: 全体像の把握（サーベイ）
1. 9-1: From Deep Learning to LLMs (最も包括的)
2. 2-3: From Factor Models to Deep Learning

### Step 2: 基盤理論
3. 1-1: Deep Learning in Asset Pricing (Pelger, 必読)
4. 1-3: Deep Learning in Characteristics-Sorted Factor Models
5. 1-4: Does Peer-Reviewed Research Help Predict Stock Returns?

### Step 3: 最新のファクター構築手法
6. 3-5: Interpretable Factors
7. 1-6: P-Trees
8. 2-4: ML and Factor-Based Portfolio Optimization

### Step 4: LLM/AIの最前線
9. 3-2: AlphaAgent
10. 3-3: Alpha-R1
11. 4-1: Synergy of Quant Factors and Newsflow

### Step 5: 実践的戦略
12. 5-1: Multi-Factor Market-Neutral Strategy
13. 6-1: Smart Beta with HMM
14. 7-1: Two Centuries of Trend Following
15. 8-1: Deep Learning Statistical Arbitrage
