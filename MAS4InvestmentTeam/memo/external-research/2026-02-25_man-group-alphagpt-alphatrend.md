# Man Group の AlphaGPT / Alpha Assistant / AlphaTrend — 詳細調査レポート

> 作成日: 2026-02-25
> 対象: Man Group（Man Numeric 部門）の AI/LLM 活用事例
> 目的: MAS4InvestmentTeam プロジェクトへの知見適用

---

## 目次

1. [Man Group の概要と AI 戦略](#1-man-group-の概要と-ai-戦略)
2. [AlphaGPT の3役割モデルの詳細分析](#2-alphagpt-の3役割モデルの詳細分析)
3. [Alpha Assistant から AlphaTrend への進化](#3-alpha-assistant-から-alphatrend-への進化)
4. [DAG ベースのアプローチの技術的評価](#4-dag-ベースのアプローチの技術的評価)
5. [MAS4InvestmentTeam への適用](#5-mas4investmentteam-への適用)
6. [参考文献](#6-参考文献)

---

## 1. Man Group の概要と AI 戦略

### 1.1 企業プロファイル

Man Group は、運用資産残高（AUM）が1,700億ドルを超える世界最大級のヘッジファンドである。1783年にロンドンで設立された同社は、240年以上の歴史を持ちながら、クオンツ運用とシステマティック投資の分野で常に最先端を走り続けてきた。特に、傘下の **Man Numeric** 部門はクオンツ株式運用に特化しており、AI/LLM（大規模言語モデル）の投資プロセスへの統合を業界に先駆けて推進している。

Man Group の運用戦略は、大きく4つの部門に分かれる。**Man AHL**（トレンドフォロー・システマティック戦略）、**Man Numeric**（クオンツ株式）、**Man GLG**（ディスクレショナリー）、そして **Man FRM**（マルチマネージャー）である。このうち Man Numeric が AI/LLM 導入の先鋒として、AlphaGPT、Alpha Assistant、AlphaTrend という3世代のシステムを開発・運用している。

### 1.2 AI 戦略の全体像

Man Group の AI 戦略は、CTO の Gary Collier が Bloomberg Investment Management Summit で公開した内容によると、以下の3つの柱で構成される。

**第1の柱: 専用 generative AI ユニットの設立**

Man Group は、単に既存のチームに AI ツールを導入するのではなく、generative AI に特化した専門組織を社内に設立した。この組織は、LLM のファインチューニング、プロンプトエンジニアリング、そして投資プロセスへの統合アーキテクチャの設計を担当する。重要なのは、この組織がテクノロジー部門と投資部門の橋渡し役として機能している点である。

**第2の柱: 独自 LLM プラットフォームの全社展開**

Man Group は OpenAI や Anthropic の API を単に利用するのではなく、独自の LLM プラットフォームを構築し、全社に展開している。このプラットフォームは、Man Group 固有の投資哲学、リスク管理フレームワーク、そして過去数十年にわたる投資判断のデータベースを LLM に組み込むことを可能にしている。これにより、汎用 LLM では実現できない、Man Group の「投資DNA」を反映したアウトプットが得られる。

**第3の柱: リサーチアイデアからライブシグナルまでのギャップ短縮**

従来のクオンツリサーチでは、投資仮説の着想からバックテスト、実運用シグナルへの変換まで数週間から数ヶ月を要していた。Man Group の AI 戦略は、このパイプラインを大幅に短縮し、「リサーチアイデアの生成 → コード実装 → バックテスト → 評価 → ライブシグナル承認」のサイクルを数時間から数日に圧縮することを目指している。

### 1.3 経営層のコミットメント

CEO の Robyn Grew は「agentic AI is well and truly here（エージェンティック AI は既に現実のものだ）」と明言しており、AI 投資が経営レベルの最優先事項であることを示している。CTO の Gary Collier も「AI agents at Man Group that can and have come up with their own independent alpha-generating ideas（Man Group の AI エージェントは独立したアルファ生成アイデアを実際に生み出している）」と述べ、AI が単なる補助ツールではなく、独立したリサーチパートナーとして機能していることを強調している。

この経営層のコミットメントは、AI への投資が一時的な流行ではなく、Man Group の長期的な競争戦略の中核であることを意味する。同社は過去10年以上にわたって機械学習をトレーディングに応用してきた実績があり、LLM の導入は既存の AI 活用の延長線上にある自然な進化と位置づけられている。

---

## 2. AlphaGPT の3役割モデルの詳細分析

### 2.1 コンセプト: デジタル3人リサーチチーム

AlphaGPT は Man Group の第1世代 LLM ベースアルファ探索システムであり、「デジタル3人リサーチチーム」として設計されている。このチームは24時間365日稼働し、膨大な金融データを秒単位で処理する。人間のリサーチチームが週40時間で行う仮説生成・検証サイクルを、AlphaGPT は数分で何十回も繰り返すことができる。

AlphaGPT の設計思想は、クオンツリサーチの本質的なワークフローを3つの明確な役割に分解し、それぞれを LLM エージェントとして実装するものである。この分解は偶然ではなく、Man Numeric のクオンツリサーチャーが日常的に行っている「仮説を考える → コードで検証する → 結果を評価する」というサイクルを形式化したものである。

### 2.2 Idea Person（アイデア担当）

Idea Person は、投資仮説を2-3秒ごとに生成するエージェントである。このエージェントの役割は、人間のリサーチャーが「ひらめき」として経験する着想プロセスを、体系的かつ高速に実行することにある。

**仮説生成の具体例:**

- 「買い注文が売り注文を上回っている銘柄は、短期的にアウトパフォームするか？」（Order Flow Imbalance）
- 「採用効率（Revenue per Employee の成長率）が高い企業は、翌四半期の業績がポジティブサプライズになりやすいか？」（Operational Efficiency）
- 「10-K の MD&A セクションにおけるセンチメントスコアが前年比で改善した企業は、株価リターンが高いか？」（Textual Analysis）
- 「サプライチェーン上流企業の在庫回転率が改善した場合、下流企業の収益改善を先行予測できるか？」（Supply Chain Propagation）

Idea Person の最大の価値は、人間のリサーチャーが認知バイアスや過去の経験に縛られて検討しない「微妙な関係性」を探索できる点にある。人間は「もっともらしい」仮説に偏りがちだが、LLM は膨大な金融文献、学術論文、市場データのパターンから、直感的には思いつかない仮説を生成できる。

**仮説生成のメカニズム:**

Idea Person は、以下のような情報ソースを組み合わせて仮説を生成する。

1. **アカデミック・ファクター文献**: Fama-French ファクター、AQR のファクター研究、ファクター動物園（Factor Zoo）の500以上のファクターから着想
2. **Man Group 固有の投資哲学**: 過去に成功したシグナルのパターン、Man Numeric の内部リサーチデータベース
3. **代替データの示唆**: 衛星画像、ウェブスクレイピングデータ、テキストマイニングの結果から得られるシグナルの候補
4. **クロスアセットの関係性**: 債券市場、コモディティ市場、為替市場のシグナルが株式リターンに与える影響

重要なのは、Idea Person が生成する仮説が単なるランダムな組み合わせではなく、金融論理的に意味のある構造を持っている点である。LLM は金融知識をトレーニングデータから学習しているため、「ファクターとして検証可能な形式」で仮説を出力できる。

### 2.3 Coder（実装担当）

Coder は、Idea Person が生成した投資仮説をプログラムコードに変換し、バックテストを自動実行するエージェントである。このエージェントの存在が、AlphaGPT を単なる「アイデア生成ツール」から「エンドツーエンドのアルファ探索パイプライン」に昇華させている。

**Coder の実装プロセス:**

1. **仮説のコード化**: Idea Person の自然言語仮説を、バックテスト可能なファクター計算コードに変換する。例えば「買い注文が売り注文を上回る銘柄はアウトパフォームする」という仮説は、`order_imbalance = (buy_volume - sell_volume) / total_volume` というファクター定義に変換される。
2. **内部ライブラリの活用**: Man Group の内部ライブラリ（ファクター計算フレームワーク、バックテストエンジン、データアクセスレイヤー）を使用してコードを生成する。これにより、一貫したデータ処理パイプラインとバックテスト環境が保証される。
3. **バックテストの自動実行**: 生成されたコードを自動的に実行し、Information Coefficient（IC）、リターン分布、ドローダウン特性などの統計量を計算する。

**Coder が解決するボトルネック:**

クオンツリサーチにおいて最大のボトルネックは、仮説からバックテスト可能なコードへの変換である。経験豊富なクオンツリサーチャーでも、1つの仮説を完全にコード化してバックテストするのに数時間から数日を要する。データの前処理、エッジケースの処理、結果の可視化など、本質的でない作業が大量に発生するためである。Coder はこのプロセスを数分に短縮し、リサーチャーが本質的な仕事—仮説の質の評価と改善—に集中できる環境を作り出す。

### 2.4 Evaluator（評価担当）

Evaluator は、Coder が実行したバックテストの結果を評価し、次の仮説生成にフィードバックを提供するエージェントである。このフィードバックループの存在が、AlphaGPT を単なる「仮説の大量生産」ではなく「仮説の品質向上」に導く仕組みとなっている。

**Evaluator の評価基準:**

1. **統計的有意性**: バックテスト結果のt統計量、Sharpe Ratio、IC（Information Coefficient）が統計的に有意か
2. **ロバスト性**: 異なる期間、異なるユニバース、異なるリバランス頻度で結果が安定しているか
3. **経済的合理性**: 統計的に有意であっても、経済的に説明可能なメカニズムがあるか（データマイニングバイアスの排除）
4. **既存シグナルとの相関**: Man Group が既に運用しているシグナルとの相関が低いか（真の増分アルファかの判定）
5. **実装可能性**: 取引コスト、流動性制約、回転率を考慮した上でも収益性があるか

**フィードバックループの重要性:**

Evaluator の評価結果は Idea Person にフィードバックされ、次の仮説生成の方向性を調整する。例えば「モメンタム系のファクターは既に十分に研究されているため、IC が低い」というフィードバックがあれば、Idea Person は代替データや非線形関係に焦点を移す。このフィードバックループにより、AlphaGPT は単調な探索ではなく、適応的で方向性のある探索を実行できる。

### 2.5 3役割モデルの意義

AlphaGPT の3役割モデルは、クオンツリサーチの分業構造を LLM エージェントとして忠実に再現している。この分業が重要である理由は以下の通りである。

**専門性の分離**: 1つの LLM に「アイデア生成・コード実装・評価」の全てを任せると、各タスクの品質が低下する。プロンプトの文脈長にも限界があるため、タスクの分離は出力品質の向上に直結する。

**反復速度の最大化**: 3つのエージェントがパイプラインとして連携することで、1つの仮説の検証サイクルが数分で完了する。人間のリサーチチームが数日かかる作業を、AlphaGPT は1日で数百回実行できる。

**品質管理の組み込み**: Evaluator による品質ゲートが組み込まれているため、無意味な仮説やデータマイニングバイアスのあるシグナルが自動的にフィルタリングされる。

---

## 3. Alpha Assistant から AlphaTrend への進化

### 3.1 Alpha Assistant: 対話型リサーチアシスタント

Alpha Assistant は AlphaGPT の第2世代であり、クオンツリサーチャーの日常的なワークフローを対話的に支援するシステムとして設計された。AlphaGPT が「自律的な探索」を目指したのに対し、Alpha Assistant は「人間との協調」を重視している。

**3フェーズの反復サイクル:**

Alpha Assistant のワークフローは、以下の3フェーズで構成される反復サイクルである。

**Phase 1: Ideation（着想）**

リサーチャーが「どの分析を行うべきか？」を Alpha Assistant と対話的に検討するフェーズ。Alpha Assistant は、リサーチャーの問いかけに対して関連するファクター文献、過去のリサーチ結果、データの利用可能性などの情報を提供し、仮説の精緻化を支援する。

例えば、リサーチャーが「最近の決算カンファレンスコールで、経営陣が "AI" という単語を頻繁に使用する企業のパフォーマンスを調べたい」と入力すると、Alpha Assistant は以下のような応答を返す。

- 類似のテキストマイニング研究の先行事例
- 利用可能なデータソース（トランスクリプトデータベース、NLP ツール）
- 考慮すべき交絡因子（セクター効果、時価総額効果）
- 推奨されるバックテスト設計（期間、ユニバース、リバランス頻度）

**Phase 2: Implementation（実装）**

Alpha Assistant がコードを書き、デバッグするフェーズ。これは Alpha Assistant の運用において **最大のボトルネック** であると同時に、最も価値を発揮する部分でもある。

リサーチャーは自然言語で分析目的を定義するだけでよい。「S&P 500 構成銘柄について、決算トランスクリプトにおける "AI" 言及頻度と翌四半期のリターンの関係をクロスセクション回帰で分析して」という指示を受けると、Alpha Assistant は Man Group の内部ライブラリを使用してコードを生成し、実行する。

重要なのは、このフェーズが対話的であること。Alpha Assistant が生成したコードにバグがあったり、データが想定と異なる形式だったりする場合、リサーチャーと Alpha Assistant が対話しながらデバッグを進める。この対話的なデバッグプロセスが、完全自律型の AlphaGPT との大きな差別化点である。

**Phase 3: Evaluation（評価）**

バックテスト結果の意味を解釈し、次のリサーチ方向を決定するフェーズ。「結果は何を意味するか？」という問いに対し、Alpha Assistant は統計的な解釈、経済的な示唆、そして次のリサーチステップの提案を行う。

リサーチャーは評価結果に基づいて次の Ideation フェーズに戻り、仮説を修正・拡張する。このサイクルが反復されることで、リサーチの品質が段階的に向上する。

### 3.2 Alpha Assistant の限界

Alpha Assistant は対話型であるがゆえに、以下の限界がある。

**再現性の課題**: 対話の流れは毎回異なるため、同じリサーチテーマでも結果が異なる可能性がある。リサーチャーの質問の仕方、対話の順序、中間結果に対するフィードバックの違いが最終結果に影響する。

**スケーラビリティの課題**: 対話型プロセスは本質的に逐次的であり、並列実行が困難である。1人のリサーチャーが Alpha Assistant と対話している間、他のリサーチタスクは待機状態になる。

**監査性の課題**: 対話の履歴を後から追跡して「なぜこの結論に至ったのか」を再構築することは可能だが、構造化されていないため監査コストが高い。規制当局への説明責任を果たすためには、より構造化されたプロセスが必要である。

**依存性管理の課題**: 複数のリサーチタスクが相互に依存している場合（例：ファクター A の結果がファクター B の入力になる場合）、対話型プロセスでは依存関係の管理が困難である。

### 3.3 AlphaTrend: DAG ベースの構造的実行

AlphaTrend は Alpha Assistant の第3世代進化版であり、対話的・反復的なプロセスを **DAG（Directed Acyclic Graph、有向非巡回グラフ）** として事前定義する設計に転換した。これは、Man Group が Alpha Assistant の運用経験から得た教訓を反映した重要なアーキテクチャ変更である。

**DAG としての実行計画:**

AlphaTrend では、リサーチワークフローの全体を実行前に DAG として定義する。各ノードは独立したオペレーション（データ取得、ファクター計算、バックテスト、評価など）を表し、エッジは依存関係（データフロー）を表す。

```
[Data Fetch: Price] ──→ [Factor: Momentum] ──→ [Backtest] ──→ [Evaluate]
                                                    ↑
[Data Fetch: Financials] → [Factor: Quality] ──────┘
                                                    ↑
[Data Fetch: Transcript] → [Factor: Sentiment] ────┘
```

この例では、3つのデータ取得ノードが並列に実行され、それぞれのファクター計算も独立して実行される。バックテストノードは全てのファクター計算が完了した後に実行され、最後に評価ノードが結果を判定する。

**Alpha Assistant との本質的な違い:**

| 特性 | Alpha Assistant | AlphaTrend |
|------|----------------|------------|
| 実行モデル | 対話的・反復的 | DAG 事前定義型 |
| プロセス定義 | 実行中に動的決定 | 実行前に静的定義 |
| 再現性 | 低（対話依存） | 高（同一 DAG = 同一プロセス） |
| 並列性 | 制限的 | 独立ノードの完全並列 |
| 監査性 | 対話履歴の事後解析 | DAG 構造の事前確認 |
| 柔軟性 | 高（任意の方向転換可能） | 中（DAG 再定義が必要） |
| LLM 多様性活用 | 制限的 | 同一ノードの複数実行可能 |

### 3.4 AlphaTrend の4つの利点

**利点1: 透明性（Transparency）**

DAG としてプロセスが可視化されるため、「何が、どの順序で、どのような依存関係で実行されるか」が実行前に明確になる。これは規制環境（MiFID II、SEC 規制）においてモデルの説明責任を果たす上で極めて重要である。監査人は DAG を見るだけで、アルファ生成プロセスの全体像を把握できる。

**利点2: 再現性（Reproducibility）**

同じ DAG を同じデータに対して再実行すれば、（LLM の確率的性質を除いて）同じプロセスが実行される。これにより、「先月のリサーチ結果を再現したい」「異なるデータ期間で同じ分析を実行したい」といった要求に容易に対応できる。Alpha Assistant の対話型プロセスでは、完全な再現は事実上不可能であった。

**利点3: 並列実行（Parallel Execution）**

DAG の独立したノードは同時に実行できる。上記の例では、3つのデータ取得と3つのファクター計算が全て並列に実行される。これにより、逐次実行と比較して大幅な時間短縮が実現される。Man Numeric の規模（数百のファクター候補を日常的に検証）では、この並列性の恩恵は極めて大きい。

**利点4: 多様性（Diversity）**

AlphaTrend の最もユニークな特徴は、LLM の確率的性質を「バグ」ではなく「機能」として活用する点である。同じクエリ（例：「モメンタムファクターのバリエーションを提案して」）を複数回実行すると、LLM は毎回異なる回答を生成する。AlphaTrend はこの性質を意図的に利用し、同一ノードを複数回実行して多様なシグナル提案を生成する。

例えば、「Idea Generation」ノードを10回並列実行すると、10個の異なる投資仮説が得られる。これらを全てバックテストし、最も有望なものを選別することで、単一実行では発見できないシグナルを効率的に探索できる。これは、機械学習におけるアンサンブル手法の哲学と共通する。

---

## 4. DAG ベースのアプローチの技術的評価

### 4.1 DAG の基本概念と金融における意義

DAG（Directed Acyclic Graph、有向非巡回グラフ）は、ノード（頂点）とエッジ（辺）で構成されるグラフ構造であり、エッジに方向性があり（Directed）、循環が存在しない（Acyclic）。この構造は、タスク間の依存関係を自然に表現でき、データパイプラインやワークフローエンジンで広く使用されている（Apache Airflow、Prefect、Dagster など）。

金融リサーチにおいて DAG が特に有用である理由は以下の通りである。

**因果関係の明示化**: 金融データの処理では、「生データ → クリーニング → ファクター計算 → バックテスト → 評価」という明確な因果関係が存在する。DAG はこの因果関係をグラフ構造として形式化し、データの逆流や循環依存を構造的に防止する。

**ルックアヘッドバイアスの防止**: バックテストにおける最大のリスクはルックアヘッドバイアス（将来のデータを過去の判断に使用すること）である。DAG のエッジにタイムスタンプ制約を組み込むことで、各ノードが利用できるデータの時点を厳密に制御できる。

**監査トレースの自動生成**: DAG の各ノードは入力・出力・実行時刻・パラメータを記録するため、完全な監査トレースが自動的に生成される。これは金融規制（SOX法、MiFID II）への準拠において重要である。

### 4.2 AlphaTrend の DAG 設計パターン

AlphaTrend の DAG は、以下の階層構造を持つと推定される。

**Level 1: データ取得レイヤー**
- 価格データ取得ノード
- ファンダメンタルデータ取得ノード
- テキストデータ取得ノード（トランスクリプト、ニュース）
- 代替データ取得ノード
- これらは全て独立しており、完全並列実行が可能

**Level 2: 特徴量計算レイヤー**
- モメンタムファクター計算
- バリューファクター計算
- クオリティファクター計算
- センチメントファクター計算
- 各ノードは Level 1 の対応するデータノードにのみ依存

**Level 3: シグナル合成レイヤー**
- マルチファクターモデルの構築
- 最適ウェイト推定
- Level 2 の全ノードの完了を待って実行

**Level 4: バックテスト・評価レイヤー**
- バックテスト実行
- 統計的有意性検定
- ロバスト性チェック
- Level 3 の完了後に実行

この階層構造により、各レベル内のノードは最大限の並列性を持ち、レベル間の依存関係は明確に定義される。

### 4.3 LLM の確率的性質の戦略的活用

AlphaTrend における最も革新的な技術的要素は、LLM の確率的性質（同じプロンプトに対して異なる応答を生成する特性）を積極的に活用する点である。

**従来の発想**: LLM の非決定性は「問題」であり、temperature=0 や seed の固定で排除すべきもの。

**AlphaTrend の発想**: LLM の非決定性は「特徴」であり、多様な仮説空間を効率的に探索するための手段。

具体的には、以下のような活用パターンが考えられる。

**パターン1: 仮説の多様性確保**
同じ「アイデア生成」ノードを temperature の異なる設定で複数回実行し、保守的な仮説（低 temperature）から大胆な仮説（高 temperature）まで幅広く生成する。

**パターン2: コード生成のロバスト性検証**
同じ仮説に対して複数の「コード生成」ノードを実行し、実装のバリエーションを得る。異なる実装で同じ結論が得られれば、結果の信頼性が高まる。

**パターン3: 評価の多角的視点**
同じバックテスト結果に対して複数の「評価」ノードを実行し、異なる視点からの解釈を集約する。これにより、単一の評価者が見落とすリスクを軽減できる。

### 4.4 技術的課題と解決策

DAG ベースのアプローチには以下の技術的課題がある。

**課題1: DAG 定義の硬直性**

事前定義型の DAG は、実行中に新しい発見に基づいてプロセスを変更することが困難である。Alpha Assistant の対話型プロセスでは可能だった「途中で方向転換する」柔軟性が失われる。

**解決策**: 動的 DAG 拡張メカニズム。特定のノード（例：評価ノード）の出力条件に基づいて、新しいサブ DAG を自動的に追加する仕組みを実装する。例えば、「IC が閾値を超えた場合にのみ、ロバスト性チェックのサブ DAG を起動する」といった条件付き実行が考えられる。

**課題2: LLM コスト管理**

同一ノードを複数回実行する多様性戦略は、LLM の API コストを倍増させる。大規模なファクターリサーチ（数百のファクター候補 × 複数回実行）では、コストが急速に膨らむ。

**解決策**: 二段階スクリーニング。まず軽量なモデル（例：Claude Haiku）で多数の仮説を生成し、有望なものだけを高性能モデル（例：Claude Opus 4.6）で深掘り評価する。

**課題3: 非決定性の管理**

LLM の確率的性質を活用しつつも、最終的な投資判断の再現性を確保する必要がある。

**解決策**: DAG の各ノードで LLM の出力をキャッシュし、再実行時に同じ出力を再利用するオプションを提供する。探索フェーズでは非決定性を活用し、運用フェーズでは出力を固定するという使い分けが有効である。

---

## 5. MAS4InvestmentTeam への適用

### 5.1 アーキテクチャの対応関係

MAS4InvestmentTeam（以下 MAS）と Man Group のシステム群には、明確な構造的対応関係がある。これを体系的に整理する。

**全体パイプラインの対応:**

| MAS のフェーズ | Man Group のシステム | 対応する機能 |
|---------------|---------------------|-------------|
| Phase 0: Postmortem | - | 失敗パターン学習（Man Group には公開情報なし） |
| Phase 1: Screening | AlphaGPT の Idea Person + Coder | ファクターベースのスクリーニング |
| Phase 2: Analysis | Alpha Assistant の Ideation + Implementation | 4並列アナリスト分析 |
| Phase 3: Debate | - | 構造化ディベート（MAS 独自） |
| Phase 4: Decision | AlphaGPT の Evaluator | FM による確信度判断 |
| Phase 5: Portfolio | AlphaTrend のシグナル合成 | ポートフォリオ構築 |

### 5.2 AlphaTrend の DAG パターンと Agent Teams の依存関係グラフ

MAS の Agent Teams アーキテクチャは、AlphaTrend の DAG パターンと驚くほど類似している。両者の構造的対応を詳細に分析する。

**MAS の依存関係グラフ:**

```
[T0 Postmortem] → failure_patterns.json
                         ↓
[T1 Screener] → candidates.json
                         ↓
[T2 Fundamental] ─┐
[T3 Valuation]  ──┤→ stock_analyses/{ticker}.json
[T4 Sentiment]  ──┤
[T5 Macro]      ──┘
                         ↓
[T6 Bull] ─┐→ debate_transcripts/{ticker}.json
[T7 Bear] ─┘
                         ↓
[T8 Fund Manager] → conviction_scores.json
                         ↓
[T9 Risk Manager] ─┐→ portfolio.json
[T10 Constructor] ──┘
```

このグラフは完全な DAG であり、AlphaTrend の設計思想と一致する。特に以下の点が重要である。

**並列実行ポイント**: Phase 2 の4つのアナリストエージェント（T2-T5）は独立しており、AlphaTrend の Level 2（特徴量計算レイヤー）と同様に完全並列実行が可能である。Claude Code の Agent Teams は `teammates` 定義により並列実行をネイティブサポートしているため、AlphaTrend の並列性を自然に実現できる。

**同期ポイント**: Phase 3 のディベートは Phase 2 の全アナリストの出力を必要とするため、ここが同期ポイントとなる。AlphaTrend の Level 3（シグナル合成）と同様の依存関係構造である。

**データフロー**: 各ノード間のデータは JSON ファイルとして受け渡される。AlphaTrend の DAG においてもノード間のデータは構造化された形式で渡されると推定され、この設計は一致している。

**MAS への具体的適用:**

MAS の Agent Teams 定義（`.claude/agents/mas-invest/mas-invest-lead.md`）において、DAG の依存関係を明示的に記述することで、AlphaTrend の透明性・再現性の利点を取り込める。具体的には、各エージェントの入出力スキーマを JSON Schema として定義し、依存関係を `teammates` の実行順序として厳密に制御する。

### 5.3 Idea Person パターンの Phase 1 スクリーニング自動化への応用

現在の MAS Phase 1（Universe Screener）は、固定的なファクターウェイト（momentum: 0.40, size: 0.20, quality: 0.25, value: 0.15）を使用する Python スクリプトとして実装される予定である。AlphaGPT の Idea Person パターンを適用することで、このスクリーニングプロセスを動的かつ適応的にできる。

**適用案1: ファクターウェイトの動的最適化**

Idea Person パターンを応用し、各リバランス時点でのファクターウェイトを LLM に提案させる。例えば、マクロ環境（金利上昇局面、景気後退局面など）に応じて、モメンタムとバリューのウェイトを動的に調整する。

```
[Macro Regime Detection] → regime_label
         ↓
[Factor Weight Proposer (LLM)] → proposed_weights
         ↓
[Backtest Validator] → validated_weights
         ↓
[Screener] → candidates.json
```

**適用案2: 新規ファクターの自動探索**

Idea Person パターンの最も強力な応用は、既存の4ファクターに加えて新しいスクリーニングファクターを LLM に自動提案させることである。例えば、SEC Filings のテキストデータから抽出できる「経営陣の楽観度スコア」や「リスク要因の変化数」といった代替ファクターを LLM が提案し、Coder パターンが自動的にバックテストする。

**適用案3: Failure Pattern の動的更新**

Phase 0 の Postmortem で抽出した failure_patterns.json を、Idea Person パターンで定期的に更新する。新たな倒産・上場廃止事例が発生した際に、LLM が既存パターンとの差異を分析し、パターンリストを拡張する。

### 5.4 LLM の確率的性質を利用した多様なシグナル生成

AlphaTrend の多様性戦略は、MAS の Phase 2（4並列アナリスト分析）に直接適用できる。

**現在の設計**: 4つのアナリストエージェント（Fundamental, Valuation, Sentiment, Macro）がそれぞれ1回ずつ分析を実行する。

**AlphaTrend 適用後の設計**: 各アナリストエージェントを複数回（例：3回）実行し、異なる視点からの分析結果を集約する。

```
[T2 Fundamental × 3回] → 3つのファンダメンタル分析レポート
[T3 Valuation × 3回]  → 3つのバリュエーション分析レポート
[T4 Sentiment × 3回]  → 3つのセンチメント分析レポート
[T5 Macro × 3回]      → 3つのマクロ分析レポート
         ↓
[Analysis Aggregator] → 多角的分析の統合
```

**多様性の価値:**

同じ銘柄の Fundamental 分析を3回実行すると、LLM の temperature 設定や注目するセクションの違いにより、異なる論点が浮かび上がる。例えば、1回目は「収益性の改善」に注目し、2回目は「設備投資の増加リスク」に注目し、3回目は「セグメント別の成長率格差」に注目するかもしれない。

これらを集約することで、1回の分析では見落とされるリスクや機会を捕捉できる。特に、ディベートフェーズ（Phase 3）の質を高めるために、多様な論点の事前収集は極めて有効である。

**コスト管理:**

多回実行のコストを制御するために、以下の二段階戦略を採用する。

1. **Screening 段階**: 軽量モデル（Claude Haiku）で多数の視点を生成
2. **Deep Analysis 段階**: 有望な視点のみを高性能モデル（Claude Sonnet 4/Opus 4.6）で深掘り

### 5.5 Human-in-the-Loop の設計（FM のレビューポイント）

Man Group の一貫したメッセージは「AI as research partner, not replacement（AI は代替ではなくリサーチパートナー）」であり、人間の判断が最終的な投資意思決定に不可欠であるという立場を維持している。数十のシグナルがライブトレードで承認されているが、承認プロセスは **人間の委員会（human committee）** が行っている。

MAS では、Fund Manager（T8）がこの Human-in-the-Loop の役割を担う。AlphaTrend の知見を踏まえて、FM のレビューポイントを以下のように設計すべきである。

**レビューポイント1: Phase 1 後のスクリーニング結果確認**

AlphaTrend の透明性の利点を活かし、スクリーニングのファクタースコアとランキングを FM が確認する。ここでの FM の役割は、定量スコアでは捕捉できない定性的な判断（例：地政学リスク、規制環境の変化）を加味して候補リストを調整することである。

**レビューポイント2: Phase 2 後のアナリスト分析品質確認**

4並列アナリストの分析結果を FM が横断的にレビューし、論理的な矛盾、データの不整合、見落とされたリスクを検出する。AlphaTrend の多回実行で得られた多様な視点を FM が統合する役割。

**レビューポイント3: Phase 3 後のディベート品質確認（最重要）**

Bull/Bear ディベートの質を FM が評価する。具体的には以下を確認する。
- Bull の論拠は定量的証拠に裏付けられているか
- Bear の反論は実質的な反論か、それとも形式的な指摘に留まっているか
- ディベートで議論されなかった重要なリスクはないか
- 両者の論拠の強度バランスは適切か

**レビューポイント4: Phase 5 前のポートフォリオ構成確認**

確信度スコアに基づくポートフォリオ案を FM が最終確認する。セクターエクスポージャー、銘柄集中度、リスクバジェットの配分が投資方針と整合しているかを検証する。

**Human-in-the-Loop の実装方法:**

Claude Code の Agent Teams では、`mas-invest-lead.md`（オーケストレータ）がフェーズ間の遷移を制御する。各レビューポイントで、オーケストレータがレビュー用のサマリーレポートを生成し、FM エージェント（または実際の人間の FM）が承認/差し戻しを判断する構造にする。

```
Phase 2 完了
    ↓
[Review Summary Generator] → phase2_review.json
    ↓
[FM Review Gate] ─── 承認 → Phase 3 へ
                 └── 差し戻し → Phase 2 の特定アナリストを再実行
```

### 5.6 アルファ探索の自動化パイプライン設計

Man Group の AlphaGPT → Alpha Assistant → AlphaTrend の進化を MAS に適用すると、以下の3段階のアルファ探索自動化パイプラインが設計できる。

**Stage 1: 仮説生成パイプライン（AlphaGPT 的）**

```
[Market Data Ingestion]
    ↓
[Factor Hypothesis Generator (LLM)] ── 2-3秒ごとに仮説生成
    ↓
[Hypothesis Filter] ── 既存ファクターとの相関チェック、経済的合理性フィルタ
    ↓
[Code Generator (LLM)] ── Man Group 内部ライブラリに相当する src/ パッケージ群を活用
    ↓
[Backtest Runner] ── strategy.backtest.engine で実行
    ↓
[Evaluator (LLM)] ── IC, Sharpe, Drawdown 等の統計量を評価
    ↓
[Signal Registry] ── 有望シグナルをデータベースに登録
```

このパイプラインは AlphaGPT の Idea Person → Coder → Evaluator ループを MAS の既存インフラ上に再実装したものである。既存の `src/factor/`（ファクター計算）、`src/strategy/`（バックテスト・リスク管理）、`src/market/`（データ取得）パッケージを LLM エージェントが呼び出す形で実装する。

**Stage 2: リサーチ支援パイプライン（Alpha Assistant 的）**

```
[Quant Researcher (Human/FM Agent)]
    ↕ 対話
[Alpha Assistant Agent]
    ↓
[Code Generation & Execution]
    ↓
[Result Interpretation]
    ↓
[Next Hypothesis Suggestion]
```

FM エージェントが Alpha Assistant と対話しながら、Stage 1 で発見された有望シグナルを深掘り分析する。ここでの対話的プロセスは、定量的な発見に定性的な投資判断を加味する重要なステップである。

**Stage 3: 運用パイプライン（AlphaTrend 的）**

```
[DAG: Full Pipeline]
├── Node: Data Fetch (並列)
├── Node: Factor Calculation (並列)
├── Node: Signal Generation (多回実行で多様性確保)
├── Node: Screening (Phase 1)
├── Node: Analysis (Phase 2, 4並列)
├── Node: Debate (Phase 3)
├── Node: FM Decision (Phase 4, Human-in-the-Loop)
└── Node: Portfolio Construction (Phase 5)
```

Stage 3 は、Stage 1 で発見され Stage 2 で検証されたシグナルを、AlphaTrend の DAG パターンに組み込んだ運用パイプラインである。全プロセスが DAG として定義されているため、透明性・再現性・監査性が確保される。

### 5.7 Man Group レベルの運用を Claude Code で実現する方法論

Man Group と MAS4InvestmentTeam では、規模（AUM $170B vs PoC）、インフラ（独自 LLM プラットフォーム vs Claude Code API）、データアクセス（Bloomberg Terminal + 代替データ vs yfinance + SEC EDGAR）に大きな差がある。しかし、**アーキテクチャの設計思想** は同等のものを Claude Code で実現可能である。以下にその方法論を詳述する。

**方法論1: Agent Teams による DAG 実行エンジン**

Claude Code の Agent Teams は、`teammates` 定義と依存関係の記述により、AlphaTrend の DAG パターンを自然に実現できる。

```markdown
# mas-invest-lead.md (Agent Teams Lead)

teammates:
  - postmortem-analyst      # Phase 0
  - universe-screener       # Phase 1
  - fundamental-analyst     # Phase 2 (並列)
  - valuation-analyst       # Phase 2 (並列)
  - sentiment-analyst       # Phase 2 (並列)
  - macro-analyst           # Phase 2 (並列)
  - bull-advocate           # Phase 3
  - bear-advocate           # Phase 3
  - fund-manager            # Phase 4
  - risk-manager            # Phase 5
  - portfolio-constructor   # Phase 5
```

この定義に加えて、Lead エージェントのプロンプトに DAG の依存関係を明示的に記述する。これにより、AlphaTrend の「実行前にオペレーションの順序・依存関係・情報フローを指定する」という設計思想を実現できる。

**方法論2: JSON ファイルによるノード間データフロー**

AlphaTrend の DAG におけるノード間データフローは、MAS では JSON ファイルとして実装される。各エージェントの出力スキーマを厳密に定義し、下流エージェントが期待する入力フォーマットと整合性を保つ。

```
failure_patterns.json     (Phase 0 → Phase 1)
candidates.json           (Phase 1 → Phase 2)
stock_analyses/{ticker}.json  (Phase 2 → Phase 3)
debate_transcripts/{ticker}.json  (Phase 3 → Phase 4)
conviction_scores.json    (Phase 4 → Phase 5)
portfolio.json            (Phase 5 → 出力)
```

このファイルベースのデータフローは、AlphaTrend の DAG ノード間のデータ受け渡しと等価であり、各ファイルが「エッジ」に対応する。

**方法論3: LLM 多回実行による多様性確保**

Claude Code では、同一エージェントを異なるパラメータ（temperature、system prompt のバリエーション）で複数回起動することで、AlphaTrend の多様性戦略を実現できる。

```python
# Phase 2 の Fundamental Analyst を3回実行する例
for variant in ["conservative", "balanced", "aggressive"]:
    result = run_agent(
        agent="fundamental-analyst",
        params={
            "ticker": ticker,
            "analysis_style": variant,
            "focus_areas": get_focus_for_variant(variant),
        }
    )
    analyses.append(result)

# 3つの分析結果を統合
aggregated = aggregate_analyses(analyses)
```

**方法論4: Point-in-Time データ管理によるルックアヘッドバイアス防止**

AlphaTrend の DAG にタイムスタンプ制約を組み込む設計は、MAS の `pit_data.py`（Point-in-Time データ管理）と直接対応する。各ノードが利用できるデータの時点を厳密に制御することで、バックテストの信頼性を確保する。

```python
# 各 Phase のデータアクセスは as_of_date で制約
def get_pit_data(ticker: str, as_of_date: date) -> PITData:
    """as_of_date 時点で利用可能なデータのみを返す"""
    # SEC Filings: filing_date <= as_of_date
    # Price data: date <= as_of_date
    # Transcripts: event_date <= as_of_date
    ...
```

**方法論5: 段階的な実装ロードマップ**

Man Group が AlphaGPT → Alpha Assistant → AlphaTrend と段階的に進化させたように、MAS も段階的な実装が現実的である。

| フェーズ | 期間 | 実装内容 | Man Group 対応 |
|---------|------|---------|----------------|
| PoC Phase 1 | 1-2ヶ月 | 基本パイプライン（固定ファクター） | AlphaGPT の Coder + Evaluator |
| PoC Phase 2 | 2-3ヶ月 | 対話的リサーチ機能追加 | Alpha Assistant |
| PoC Phase 3 | 3-4ヶ月 | DAG 実行エンジン + 多回実行 | AlphaTrend |
| Production | 6ヶ月+ | 自動アルファ探索パイプライン | AlphaGPT + AlphaTrend 統合 |

### 5.8 実装上の推奨事項

Man Group の知見を MAS に適用する際の具体的な推奨事項を以下にまとめる。

**推奨1: DAG 定義の外部化**

Agent Teams の依存関係を Lead エージェントのプロンプトにハードコードするのではなく、YAML/JSON ファイルとして外部化する。これにより、DAG の変更（エージェントの追加・削除、依存関係の変更）がプロンプトの修正なしに行える。

```yaml
# mas_dag_config.yaml
phases:
  - name: postmortem
    agents: [postmortem-analyst]
    depends_on: []
  - name: screening
    agents: [universe-screener]
    depends_on: [postmortem]
  - name: analysis
    agents: [fundamental, valuation, sentiment, macro]
    depends_on: [screening]
    parallel: true
    repeat: 3  # AlphaTrend 多様性戦略
  - name: debate
    agents: [bull-advocate, bear-advocate]
    depends_on: [analysis]
  - name: decision
    agents: [fund-manager]
    depends_on: [debate]
    review_gate: true  # Human-in-the-Loop
  - name: construction
    agents: [risk-manager, portfolio-constructor]
    depends_on: [decision]
```

**推奨2: 評価メトリクスの標準化**

AlphaGPT の Evaluator パターンに倣い、各 Phase の出力品質を定量的に評価するメトリクスを標準化する。

| Phase | メトリクス | 閾値 |
|-------|-----------|------|
| Phase 1 | スクリーニング通過率 | 10-16%（50-80/500） |
| Phase 2 | 分析カバレッジ（言及した thesis point 数） | 3-5 per analyst |
| Phase 3 | ディベート深度（反論の具体性スコア） | 0.7以上 |
| Phase 4 | 確信度スコア分布の分散 | 適度な分散（全銘柄が同スコアは不可） |
| Phase 5 | ポートフォリオ制約充足率 | 100% |

**推奨3: シグナルレジストリの構築**

Man Group が「数十のシグナルがライブトレードで承認済み」と述べているように、MAS でも発見されたシグナル（ファクター）を体系的に管理するレジストリを構築すべきである。

```json
{
  "signal_id": "SIG-001",
  "name": "earnings_call_ai_mention_frequency",
  "hypothesis": "決算カンファレンスコールでAI言及頻度が高い企業はアウトパフォームする",
  "discovered_date": "2026-03-01",
  "backtest_ic": 0.05,
  "sharpe_ratio": 0.8,
  "status": "under_review",
  "discoverer": "idea-person-agent",
  "approved_by": null,
  "live_since": null
}
```

**推奨4: 「リサーチアシスタント」から「リサーチパートナー」への段階的移行**

Man Group の CTO が述べた「AI as research partner」という概念は、MAS の長期ビジョンとして重要である。初期段階では AI をリサーチアシスタント（人間の指示に従う）として位置づけ、段階的にリサーチパートナー（独立した分析・提案を行う）へと移行させる。

- **Phase 1（アシスタント）**: 人間が定義したファクターでスクリーニング、人間がレビュー
- **Phase 2（アドバイザー）**: AI が新ファクターを提案、人間が承認
- **Phase 3（パートナー）**: AI が独立してアルファ探索を実行、人間は最終判断のみ

---

## 6. 参考文献

### 学術論文

1. **Wang, Y., et al. (2023).** "Alpha-GPT: Human-AI Interactive Alpha Mining for Quantitative Investment." *arXiv:2308.00016*. AlphaGPT の基本コンセプトと Human-AI インタラクションフレームワークを提案。

2. **Yuan, Y., Wang, Y., & Guo, J. (2024).** "Alpha-GPT 2.0: Human-in-the-Loop AI for Quantitative Investment." *arXiv:2402.09746*. Alpha-GPT の第2世代として、Human-in-the-Loop の投資プロセスへの統合を深化。

### Man Group 公式情報

3. **Gary Collier, CTO, Man Group.** Bloomberg Investment Management Summit 講演. AlphaGPT、Alpha Assistant、AlphaTrend の3世代システムの概要と実績を公開。

4. **Robyn Grew, CEO, Man Group.** "Agentic AI is well and truly here." AI 戦略の経営レベルでのコミットメントを表明。

### 関連技術

5. **Apache Airflow / Prefect / Dagster**: DAG ベースのワークフローエンジン。AlphaTrend の DAG 実行モデルの技術的基盤。

6. **Claude Code Agent Teams**: Anthropic の Agent Teams フレームワーク。`teammates` 定義による並列エージェント実行と依存関係管理。

---

> **メモ**: 本レポートは公開情報に基づく分析であり、Man Group の内部実装の詳細は推定を含む。MAS4InvestmentTeam への適用提案は、これらの推定に基づく設計案であり、実装にあたっては追加の技術検証が必要である。
