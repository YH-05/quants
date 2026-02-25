# CrewAI フレームワークと金融マルチエージェントシステム：技術分析レポート

**作成日**: 2026-02-25
**関連ドキュメント**:
- `MAS4InvestmentTeam/plan/2026-02-16_mas-investment-team-poc-design.md`
- `MAS4InvestmentTeam/plan/2026-02-25_analyst-kb-mas-integration.md`
- `MAS4InvestmentTeam/memo/2026-02-25_memo_analyst-kb-mas-integration.md`

---

## 目次

1. [CrewAI の概要と市場ポジション](#1-crewai-の概要と市場ポジション)
2. [技術アーキテクチャの詳細分析](#2-技術アーキテクチャの詳細分析)
3. [金融分野での活用事例の分析](#3-金融分野での活用事例の分析)
4. [CrewAI vs Claude Code Agent Teams の比較](#4-crewai-vs-claude-code-agent-teams-の比較)
5. [MAS4InvestmentTeam への適用と示唆](#5-mas4investmentteam-への適用と示唆)

---

## 1. CrewAI の概要と市場ポジション

### 1.1 プロジェクトの概要

CrewAI は、João Moura が創設した Python ベースのマルチエージェントオーケストレーションフレームワークである。GitHub 上で 44,300 stars を獲得しており（2026年2月時点）、LLM エージェントフレームワークの中でも最大級のコミュニティを擁する。LangChain や AutoGen といった先行プロジェクトとは異なり、CrewAI は**外部フレームワークへの依存を排除したスタンドアロン設計**を採用しており、これが軽量性と柔軟性の源泉となっている。

CrewAI の設計哲学は「AI エージェントに**ロール（役割）**を与え、チームとして協調させる」という直感的なメタファーに基づく。人間の組織に例えると、CEO がプロジェクトを定義し、マネージャーが各メンバーにタスクを割り振り、チームメンバーが専門スキルを活かして協働する構造を、YAML ベースの宣言的な記述で実現する。この「ロールプレイ型」のアプローチは、金融の投資チーム構造（ファンドマネージャー、アナリスト、リスクマネージャー等）との親和性が高い。

### 1.2 資金調達と事業成長

CrewAI は Insight Partners がリードする Series A ラウンドを完了しており、エンタープライズ市場への本格参入の資金的裏付けを得ている。2025年第3四半期の時点で**11億回のエージェンティック自動化**を実行した実績があり、これは同フレームワークが単なるオープンソースプロジェクトではなく、実プロダクション環境で大規模に利用されていることを示す。

さらに、世界中で7桁ドル（$M）規模の契約を複数締結しており、HFS Hot Tech および Gartner Cool Vendor にも選出された。これらの実績は、CrewAI がアカデミックな実験段階を超え、エンタープライズグレードのソリューションとして認知されていることを意味する。

### 1.3 エコシステムと市場ポジション

CrewAI のエコシステムは以下の構成要素で成り立つ：

| コンポーネント | 説明 | GitHub Stars |
|--------------|------|-------------|
| **crewAI** (本体) | コアフレームワーク | 44,300 |
| **crewAI-examples** | 公式サンプル集 | 5,532 |
| **crewAI-tools** | ツール拡張ライブラリ | - |
| **CrewAI-Studio** | No-code GUI | 1,200 |
| **awesome-crewai** | コミュニティプロジェクト集 | - |

マルチエージェントフレームワーク市場における CrewAI の位置付けは、「プロダクション指向の汎用フレームワーク」である。MetaGPT（41k stars）がソフトウェア開発に特化し、FinRobot が金融ドメインに特化しているのに対し、CrewAI はドメインに依存しない汎用的な設計を維持しつつ、エンタープライズ運用に必要な機能（オブザーバビリティ、ガバナンス、デプロイメント）を AOP プラットフォームとして提供する戦略を採っている。

### 1.4 市場コンテキスト：マルチエージェントフレームワークの競争環境

2025-2026年にかけて、マルチエージェントフレームワーク市場は急速に成熟した。以下の主要プレイヤーが存在する：

| フレームワーク | 開発元 | Stars | 特徴 | 金融適性 |
|--------------|--------|-------|------|---------|
| **CrewAI** | CrewAI Inc. | 44.3k | ロールプレイ型、Flows | 高（YAML定義が直感的） |
| **LangGraph** | LangChain | - | ステートグラフ | 高（複雑な状態管理） |
| **AutoGen** | Microsoft | - | エンタープライズ | 中（Microsoftエコシステム依存） |
| **MetaGPT** | DeepWisdom | 41k | ソフトウェア開発向け | 低（ドメイン不一致） |
| **FinRobot** | FinRL | - | 金融特化 | 最高（ドメイン特化） |

CrewAI が市場で際立つ理由は3点ある。第一に、LangChain エコシステムからの**完全な独立性**により、依存関係の複雑さを回避している。第二に、Crews と Flows の**二層構造**により、プロトタイピングからプロダクションまでをカバーする。第三に、AOP プラットフォームによるエンタープライズ機能の提供で、「フレームワーク」から「プラットフォーム」への進化を遂げている。

---

## 2. 技術アーキテクチャの詳細分析

### 2.1 コア概念：Agents, Tasks, Tools, Processes

CrewAI のアーキテクチャは4つのコア概念で構成される。

#### Agents（エージェント）

エージェントは `role`、`goal`、`backstory` の3属性で定義される自律的なユニットである。

```yaml
# agents.yaml
fundamental_analyst:
  role: Senior Fundamental Analyst
  goal: Analyze SEC filings and financial statements to identify companies with sustainable competitive advantages
  backstory: >
    You are a CFA charterholder with 15 years of experience in equity research.
    You specialize in dissecting 10-K and 10-Q filings to evaluate business quality,
    management effectiveness, and long-term earnings power.
```

この3属性の設計は、LLM のプロンプトエンジニアリングにおける「ペルソナ設定」をフレームワークレベルで構造化したものである。`role` はエージェントの専門性を定義し、`goal` は行動の方向性を指定し、`backstory` はコンテキストと推論のフレーミングを提供する。金融領域では、この構造が投資チームの役割分担（アナリスト、リスクマネージャー、ファンドマネージャー等）と自然に対応する。

#### Tasks（タスク）

タスクは `description`、`expected_output`、`agent` の3属性で定義される作業単位である。

```yaml
# tasks.yaml
analyze_10k:
  description: >
    Analyze the most recent 10-K filing for {ticker}.
    Focus on revenue trends, margin profile, competitive moat indicators,
    and management discussion of risks.
  expected_output: >
    A structured JSON with sections: revenue_analysis, margin_analysis,
    moat_assessment (scored 1-10), risk_factors, and overall_quality_score.
  agent: fundamental_analyst
```

`expected_output` の明示的な定義は、LLM の出力を構造化する上で重要な設計判断である。金融分析では、自由形式のテキストよりも構造化された JSON やスコアリング結果が後続処理（ポートフォリオ構築等）に必要なため、この仕様はドメインの要件と合致する。

#### Tools（ツール）

Tools はエージェントが外部システムと対話するためのインターフェースである。CrewAI は独自のツールシステムを持ち、`@tool` デコレータで Python 関数をツールとして登録できる。

```python
from crewai.tools import tool

@tool("SEC Filing Fetcher")
def fetch_sec_filing(ticker: str, filing_type: str = "10-K") -> str:
    """Fetch the most recent SEC filing for a given ticker."""
    # SEC EDGAR API 呼び出し
    ...
```

また、Composio との連携により、200以上の外部サービス（Slack、Google Sheets、Bloomberg 等）との統合が可能である。金融分野では、市場データ API（Yahoo Finance, Bloomberg）、SEC EDGAR、ニュースフィード等との接続が必須であり、この拡張性は重要な利点となる。

#### Processes（プロセス）

Processes はタスクの実行順序と協調パターンを制御する。CrewAI は主に2つのプロセスタイプを提供する：

1. **Sequential（逐次実行）**: タスクが定義順に1つずつ実行される。前のタスクの出力が次のタスクの入力となる。
2. **Hierarchical（階層型）**: マネージャーエージェントがタスクの割り振りと結果の統合を担当する。

```python
from crewai import Crew, Process

crew = Crew(
    agents=[fundamental_analyst, valuation_analyst, fund_manager],
    tasks=[analyze_10k, build_valuation, make_decision],
    process=Process.hierarchical,
    manager_llm="gpt-4"
)
```

Sequential プロセスは分析パイプライン（データ収集 → 分析 → レポート生成）に適し、Hierarchical プロセスは投資判断のように複数の専門家の意見を統合するシナリオに適する。

### 2.2 Crews vs Flows：二層アーキテクチャ

CrewAI の最も重要な技術的差別化は、**Crews** と **Flows** の二層構造にある。

#### Crews：自律協調モード

Crews は CrewAI の基本的な実行単位であり、複数のエージェントが定義されたプロセスに従ってタスクを協調的に実行する。Crews の特徴は以下の通りである：

- **自律性**: エージェントは与えられた役割と目標に基づき、自律的に推論・行動する
- **協調インテリジェンス**: エージェント間でコンテキストが共有され、前のエージェントの出力が後のエージェントの入力となる
- **宣言的定義**: YAML ファイルでエージェントとタスクを定義し、Python コードは最小限

Crews は「探索的な分析」や「定性的な判断」に適しており、投資チームの議論プロセス（Bull/Bear ディベート等）を表現するのに向いている。

#### Flows：イベント駆動制御モード

Flows は 2025年に導入されたエンタープライズ・プロダクション向けアーキテクチャであり、Crews よりも粒度の高い制御を提供する。

```python
from crewai.flow.flow import Flow, listen, start

class InvestmentFlow(Flow):
    @start()
    def collect_market_data(self):
        """市場データの収集"""
        return self.state.market_data

    @listen(collect_market_data)
    def run_fundamental_analysis(self):
        """ファンダメンタル分析 Crew を実行"""
        crew = FundamentalCrew()
        result = crew.kickoff()
        self.state.fundamental_result = result

    @listen(collect_market_data)
    def run_technical_analysis(self):
        """テクニカル分析（単一 LLM コール）"""
        # Crew を使わず、直接 LLM を呼び出す
        ...

    @listen(run_fundamental_analysis, run_technical_analysis)
    def make_investment_decision(self):
        """投資判断の統合"""
        ...
```

Flows の技術的特徴は以下の通りである：

- **イベント駆動アーキテクチャ**: `@listen` デコレータによるイベントリスナーパターン。特定のメソッドの完了をトリガーとして後続処理が発動する
- **粒度の混在**: 同一 Flow 内で Crews（マルチエージェント）と単一 LLM コール（精密制御）を混在させることが可能
- **状態管理**: `self.state` による明示的な状態管理。Crews の暗黙的なコンテキスト共有と異なり、データフローが可視化される
- **並列実行**: 同一イベントを複数のメソッドが listen することで、暗黙的な並列実行が実現する
- **条件分岐**: `@router` デコレータにより、分析結果に基づく動的なルーティングが可能

Flows は Crews を「ネイティブサポート」するため、既存の Crews を Flow のノードとして組み込むことができる。これにより、「ファンダメンタル分析は Crews（複数エージェントの協調）で行い、データ前処理は単一 LLM コールで行い、ポートフォリオ最適化は Python コードで行う」といったハイブリッドなワークフローが構築可能である。

### 2.3 YAML ベースの宣言的定義

CrewAI の設計で注目すべきは、エージェントとタスクの定義を YAML ファイルに分離している点である。これにより以下の利点が得られる：

1. **関心の分離**: エージェントの「何をするか」（YAML）と「どう実行するか」（Python）が分離される
2. **テンプレート変数**: `{topic}` のようなテンプレート変数を使うことで、同一定義を異なるコンテキストで再利用可能
3. **非エンジニアの参加**: YAML は Python コードよりもアクセシブルであり、ドメインエキスパート（金融専門家）がエージェント定義に参加しやすい
4. **バージョン管理**: エージェント定義の変更履歴を Git で追跡可能

```yaml
# agents.yaml - エージェント定義
researcher:
  role: Senior Data Researcher
  goal: Uncover cutting-edge developments in {topic}
  backstory: >
    You're a seasoned researcher with a knack for uncovering the latest
    developments in {topic}. Known for your ability to find the most
    relevant information and present it in a clear and concise manner.

# tasks.yaml - タスク定義
research_task:
  description: >
    Conduct a thorough research about {topic}.
    Make sure you find any interesting and relevant information given
    the current year is 2024.
  expected_output: >
    A list with 10 bullet points of the most relevant information about {topic}.
  agent: researcher
```

この YAML 定義パターンは、当プロジェクト（MAS4InvestmentTeam）の `.claude/agents/` における Markdown ベースのエージェント定義と類似したアプローチである。CrewAI が YAML を選択した理由は、機械可読性と人間可読性のバランスにある。一方、Claude Code Agent Teams が Markdown を選択した理由は、より自然言語に近い記述でエージェントの振る舞いを詳細に指定できる点にある。

### 2.4 CrewAI AOP（Agent Operations Platform）

2025年11月に発表された CrewAI AOP は、フレームワークから**プラットフォーム**への進化を象徴する製品である。

AOP の3つの柱：

1. **オブザーバビリティ（Observability）**: エージェントの推論過程、ツール呼び出し、タスク間のデータフローをリアルタイムで可視化する。金融分野では、投資判断の「なぜそう判断したか」を追跡する監査証跡（Audit Trail）として機能する。

2. **ガバナンス（Governance）**: コンプライアンス要件に準拠したエージェント実行の制御。金融規制（SEC ルール、MiFID II 等）への対応において、エージェントの判断プロセスが規制要件を満たしていることを保証する仕組みとして重要である。

3. **デプロイメント（Deployment）**: 開発環境からプロダクション環境への移行を支援するインフラ。スケーラビリティ、可用性、セキュリティの確保を含む。

AOP は欧州・アジアへの展開を拡大しており、金融規制が厳格な地域でのエンタープライズ採用を支援している。

---

## 3. 金融分野での活用事例の分析

### 3.1 Stock Analysis Platform（CrewAI + Composio）

最も注目される金融活用事例は、CrewAI と Composio を組み合わせたインド株式市場向けの分析プラットフォームである。このシステムは**機関投資家グレード**の分析を目指して構築されている。

#### エージェント構成

| エージェント | 役割 | 分析領域 |
|------------|------|---------|
| **Market Analyst** | 市場動向の把握 | セクターローテーション、市場センチメント、マクロ指標 |
| **Financial Analyst** | 財務データの精査 | 損益計算書、貸借対照表、キャッシュフロー、財務比率 |
| **Investment Advisor** | 投資推奨の生成 | リスク調整リターン、ポートフォリオ適合性、タイミング |

この3エージェント構成は、投資判断に必要な「市場環境」「企業ファンダメンタルズ」「投資判断」の3層を分離したものであり、当プロジェクトの Phase 2（Analysis）→ Phase 4（Decision）の構造と対応する。

#### Dual LLM 戦略

このプラットフォームの技術的に最も興味深い点は、**Dual LLM アーキテクチャ**の採用である：

- **GPT-4（複雑推論）**: 財務分析、競争優位性の評価、投資判断の統合など、深い推論が必要なタスクに使用
- **Groq Llama-3-70B（高速推論）**: データの前処理、テンプレート化された分析、スクリーニング条件の適用など、応答速度が重要なタスクに使用

この設計は、投資分析ワークフローにおけるタスクの異質性を反映している。すべてのタスクに最高性能のモデルを使用する必要はなく、タスクの性質に応じてモデルを使い分けることで、**コスト効率と品質のバランス**を最適化している。

具体的な使い分けの例：

| タスク | 必要な能力 | 適切なモデル | 理由 |
|--------|----------|-------------|------|
| SEC 10-K の要約 | 深い理解・構造化 | GPT-4 | 複雑な財務開示の解釈が必要 |
| 財務比率の計算・分類 | 速度・正確性 | Groq Llama-3-70B | テンプレート的な処理で高速性が重要 |
| 競争優位性の評価 | 推論・判断 | GPT-4 | ビジネスモデルの深い理解が必要 |
| ニュースセンチメント分類 | 速度・スループット | Groq Llama-3-70B | 大量記事の高速処理が必要 |
| 投資判断の統合 | 推論・バランス | GPT-4 | 多面的な情報の統合判断が必要 |

#### リアルタイムデータ処理

Composio との統合により、リアルタイムの市場データフィードを処理できる点も重要である。Composio は 200 以上の外部サービスとの統合を提供し、CrewAI エージェントがAPI経由でリアルタイムデータにアクセスする際のアダプター層として機能する。

### 3.2 金融 MAS における CrewAI の適用パターン

CrewAI を金融分野に適用する際の一般的なパターンを整理する。

#### パターン A：逐次パイプライン型

```
データ収集 → スクリーニング → 分析 → 推奨生成
(Sequential Process)
```

最もシンプルなパターン。各フェーズを1つのタスクとして定義し、Sequential プロセスで実行する。小規模なプロトタイプや概念検証に適している。

#### パターン B：階層型チーム

```
Fund Manager (Manager Agent)
├── Fundamental Analyst (Worker)
├── Technical Analyst (Worker)
├── Macro Analyst (Worker)
└── Risk Manager (Worker)
```

Hierarchical プロセスを使用し、マネージャーエージェント（Fund Manager）がワーカーエージェントにタスクを動的に割り振る。CrewAI の階層型プロセスでは、マネージャーが各ワーカーの出力を評価し、追加情報が必要な場合は再度タスクを割り振ることができる。

#### パターン C：Flows ハイブリッド型

```python
class InvestmentFlow(Flow):
    @start()
    def screen_universe(self):      # Python コード（ファクタースクリーニング）

    @listen(screen_universe)
    def analyze_candidates(self):    # Crew（マルチエージェント分析）

    @listen(analyze_candidates)
    def construct_portfolio(self):   # Python コード（最適化）
```

最も実用的なパターン。定量的な処理（スクリーニング、最適化）は Python コードで行い、定性的な処理（企業分析、投資判断）は Crew で行う。当プロジェクトのハイブリッドアーキテクチャ（Python バックテストエンジン + Agent Teams）と同じ発想である。

### 3.3 CrewAI コミュニティにおける金融プロジェクト

awesome-crewai および crewAI-examples リポジトリには、金融関連のプロジェクトが複数存在する。コミュニティの関心の高さは、金融がマルチエージェントシステムの最も有望な応用領域の1つであることを示している。CrewAI の YAML ベースの定義が「投資チームの役割分担」という金融の慣行と自然に対応することが、コミュニティの金融プロジェクトが多い理由の1つと考えられる。

---

## 4. CrewAI vs Claude Code Agent Teams の比較

### 4.1 アーキテクチャの根本的な違い

CrewAI と Claude Code Agent Teams は、マルチエージェントシステムを実現するための根本的に異なるアプローチを取る。

| 観点 | CrewAI | Claude Code Agent Teams |
|------|--------|------------------------|
| **実行基盤** | 独立した Python プロセス | Claude Code セッション内 |
| **LLM 呼び出し** | API 経由（OpenAI, Anthropic 等） | Subscription 内で完結 |
| **エージェント定義** | YAML（role, goal, backstory） | Markdown（自然言語による詳細指示） |
| **タスク定義** | YAML（description, expected_output） | プロンプト内で直接指定 |
| **ツール** | @tool デコレータ / Composio | MCP ツール |
| **状態管理** | Flows の self.state / Crews の暗黙的共有 | ファイルベース（JSON/Markdown） |
| **プロセス制御** | Sequential / Hierarchical | 直列・並列・条件分岐の柔軟な組み合わせ |

### 4.2 エージェント定義の比較

CrewAI の YAML 定義と Claude Code の Markdown 定義を、同一のエージェント（ファンダメンタルアナリスト）で比較する。

**CrewAI（YAML）:**
```yaml
fundamental_analyst:
  role: Senior Fundamental Analyst
  goal: >
    Analyze SEC filings to identify sustainable competitive advantages
    and assign quality scores
  backstory: >
    You are a CFA charterholder with 15 years of equity research experience.
    You specialize in moat analysis using Morningstar's framework.
```

**Claude Code Agent Teams（Markdown）:**
```markdown
# Fundamental Analyst

## 役割
SEC Filings (10K/10Q/8K) を分析し、企業の競争優位性を評価する。

## スキル参照
- `analyst/kb/dogma.md` - 投資哲学
- `analyst/kb/kb1-rules.md` - 8つの評価ルール
- `analyst/kb/kb2-patterns.md` - 12の却下/高評価パターン

## 入力
- `candidates.json` - スクリーニング通過銘柄リスト
- SEC EDGAR データ（MCP ツール経由）

## 出力
- `stock_analyses/{ticker}.json` - 銘柄別分析結果

## 分析プロセス
1. 直近の 10-K から revenue trends, margin profile を抽出
2. KB1 ルールに基づき競争優位性を評価（8項目チェック）
3. KB2 パターンとの照合で確信度を調整
4. 構造化 JSON として出力
```

この比較から明らかなのは、Markdown 定義の方が**情報量が圧倒的に多い**ことである。CrewAI の YAML は `role`, `goal`, `backstory` の3属性に限定されるが、Claude Code の Markdown は参照すべきナレッジベース、具体的な入出力形式、段階的なプロセス指示を含むことができる。この差は、金融分析のようなドメイン知識が重要な領域で特に顕著となる。

### 4.3 ナレッジ注入メカニズムの比較

当プロジェクトにおける最大の差別化要因は**ナレッジベース（KB）の注入メカニズム**である。

**CrewAI のナレッジ注入:**
- `backstory` でのプロンプト内記述（トークン制限あり）
- RAG（Retrieval-Augmented Generation）による外部知識の検索・注入
- Tool 経由でのドキュメント参照

**Claude Code Agent Teams のナレッジ注入:**
- Skills（`.claude/skills/`）による構造化された知識定義
- エージェント定義内での直接参照（`@analyst/kb/dogma.md`）
- Rules（`.claude/rules/`）による共通ルールの適用

当プロジェクトの4層ナレッジベース（dogma.md → KB1 → KB2 → KB3）は、Claude Code の Skills メカニズムを通じてエージェントに直接注入される。CrewAI で同等の機能を実現するには、RAG パイプラインの構築が必要であり、検索精度や関連性の保証が追加の課題となる。

Skills の利点は以下の通りである：

1. **決定論的な注入**: RAG の確率的な検索と異なり、参照すべきドキュメントが明示的に指定される
2. **構造化された知識**: Markdown の見出し構造が知識の階層を反映する
3. **バージョン管理**: Git による知識の変更履歴追跡
4. **共有と再利用**: 複数エージェント間で同一の KB を参照可能

### 4.4 コスト構造の比較

| コスト要素 | CrewAI | Claude Code Agent Teams |
|-----------|--------|------------------------|
| **LLM 推論** | API 従量課金（$0.01-0.06/1K tokens） | Subscription 内（追加コストなし） |
| **インフラ** | 自前のサーバー or クラウド | 不要（Claude Code が提供） |
| **ツール統合** | Composio 利用料（オプション） | MCP（無料） |
| **運用** | AOP 利用料（エンタープライズ） | 不要 |

当プロジェクトのバックテストでは、500銘柄 x 複数四半期 x 複数フェーズ のエージェント呼び出しが発生する。API 従量課金モデルでは、1回のバックテスト実行で数百ドルのコストが発生し得る。Subscription モデルでは、このコストが固定費に含まれるため、反復的な実験・改善サイクルのコスト障壁が低い。

### 4.5 プロセス制御の柔軟性

CrewAI は Sequential と Hierarchical の2つのプロセスタイプを提供するが、当プロジェクトの PoC 設計における以下のような複雑なパイプラインの直接的な表現には制約がある：

```
Phase 0 (Postmortem) → Phase 1 (Screening) → Phase 2 (4並列 Analysis)
→ Phase 3 (2ラウンド Debate) → Phase 4 (Decision) → Phase 5 (Portfolio)
```

特に、Phase 2 の「4並列分析」と Phase 3 の「銘柄ごとの2ラウンドディベート」を、CrewAI の標準プロセスで表現するには工夫が必要である。Flows を使えば可能だが、追加のボイラープレートコードが必要となる。

Claude Code Agent Teams では、チームメイトの依存関係を直接定義することで、直列・並列・条件分岐を自然に表現できる。

```markdown
## チームメイト
- fundamental_analyst: 並列実行
- valuation_analyst: 並列実行（fundamental_analyst と同時）
- sentiment_analyst: 並列実行
- macro_analyst: 並列実行
- bull_advocate: fundamental_analyst, valuation_analyst, sentiment_analyst, macro_analyst の完了後
- bear_advocate: bull_advocate の完了後（Round 1 の結果を参照）
- fund_manager: bear_advocate の完了後
```

この宣言的な依存関係定義は、CrewAI の Processes よりも直感的であり、DAG（有向非巡回グラフ）ベースのワークフローエンジンに近い表現力を持つ。

### 4.6 デバッグとオブザーバビリティ

CrewAI AOP はエンタープライズグレードのオブザーバビリティを提供するが、これは有償プラットフォームである。一方、Claude Code Agent Teams のデバッグは、エージェントの出力ファイル（JSON/Markdown）を確認することで行う。

当プロジェクトでは、各フェーズの出力が構造化ファイルとして保存されるため（`candidates.json`, `stock_analyses/{ticker}.json`, `debate_transcripts/{ticker}.json` 等）、事後的な分析・デバッグが可能である。ただし、リアルタイムの実行監視という点では CrewAI AOP に劣る。

---

## 5. MAS4InvestmentTeam への適用と示唆

### 5.1 CrewAI の YAML 定義パターンのエージェント設計への参考

CrewAI の `role`, `goal`, `backstory` の3属性モデルは、エージェント設計の**最小限のフレームワーク**として参考になる。当プロジェクトの Markdown 定義は情報量が多い分、構造がエージェントごとにばらつく可能性がある。CrewAI のアプローチから学べるのは、**すべてのエージェント定義に共通するメタデータ構造**を設けることの価値である。

具体的な提案として、各エージェント定義の冒頭に以下のメタデータブロックを標準化することが考えられる：

```markdown
# [エージェント名]

## メタデータ
| 属性 | 値 |
|------|-----|
| Role | ファンダメンタルアナリスト |
| Goal | SEC Filings から持続可能な競争優位性を持つ企業を特定する |
| Phase | Phase 2: Analysis |
| Input | candidates.json |
| Output | stock_analyses/{ticker}.json |
| Skills | dogma.md, KB1, KB2, KB3 |
| LLM Preference | deep_think (複雑推論) |
```

このメタデータブロックは、CrewAI の YAML 定義と同等の構造化情報を提供しつつ、Markdown の柔軟性を維持する。また、将来的にメタデータを機械的にパースして依存関係グラフを自動生成するなど、ツーリングの発展にも対応できる。

### 5.2 Dual LLM 戦略（deep_think + quick_think）の導入

CrewAI の Stock Analysis Platform で採用されている Dual LLM 戦略は、当プロジェクトへの最も即座に適用可能な示唆である。

当プロジェクトの12エージェントを、必要な推論の深さによって分類する：

#### deep_think（深い推論が必要）

| エージェント | 理由 |
|------------|------|
| T2: Fundamental Analyst | 10-K/10-Q の複雑な開示の解釈、競争優位性の評価 |
| T3: Valuation Analyst | DCF モデリング、仮定の妥当性判断 |
| T6: Bull Advocate | 多面的な投資論拠の構築 |
| T7: Bear Advocate | 反論の精密な構築 |
| T8: Fund Manager | 全ディベートの統合と確信度スコアリング |

#### quick_think（速度重視）

| エージェント | 理由 |
|------------|------|
| T0: Postmortem Analyst | パターンマッチング（構造化された失敗パターンの抽出） |
| T1: Universe Screener | ファクタースコアの機械的な計算・ランキング |
| T4: Sentiment Analyst | ニュース・トランスクリプトの分類（ポジティブ/ネガティブ） |
| T5: Macro/Regime Analyst | 経済指標のレジーム判定（テンプレート的処理） |
| T9: Risk Manager | エクスポージャー制約の数値チェック |
| T10: Portfolio Constructor | 最適化計算の実行（主に Python コード） |

Claude Code Agent Teams のコンテキストでは、「Dual LLM」は Claude の異なるモデル（Opus vs Sonnet/Haiku）の使い分けとして実装できる。現在の Claude Code Subscription では同一モデルが使用されるが、将来的にモデル選択が可能になった場合、この分類が直接適用できる。

当面の実装としては、`deep_think` エージェントにはより詳細な Skills と KB を注入し、`quick_think` エージェントにはシンプルなテンプレートベースの指示を与える、というプロンプト設計の差別化で同等の効果を模擬できる。

### 5.3 CrewAI Flows のイベント駆動パターンの Agent Teams への応用

CrewAI Flows の `@listen` / `@router` パターンは、当プロジェクトのハイブリッドアーキテクチャ（Python バックテストエンジン + Agent Teams）に直接的な示唆を与える。

当プロジェクトの PoC 設計では、バックテストエンジン（Python）がタイムステップを制御し、各タイムステップでエージェントを呼び出す構造になっている：

```
Python Engine (タイムステップ制御)
│
├── 四半期ごとに → Agent Teams (MAS Investment Team)
│   ├── Phase 0-5 を実行
│   └── portfolio.json を出力
│
├── portfolio.json を読み込み
├── リバランス実行
└── パフォーマンス記録
```

CrewAI Flows の設計パターンから学べるのは、**Python コードと Agent 呼び出しの境界をイベント駆動で管理する**というアプローチである。具体的には、以下のような設計が考えられる：

```python
# バックテストエンジンにおけるイベント駆動パターン

class BacktestEngine:
    def on_quarter_end(self, date: str, pit_data: dict):
        """四半期末イベント: MAS Investment Team を起動"""
        # Phase 0: Postmortem（Python で失敗パターンを準備）
        failure_patterns = self.prepare_failure_patterns(pit_data)

        # Phase 1: Screening（Python でファクタースクリーニング）
        candidates = self.screen_universe(pit_data)

        # Phase 2-4: Analysis → Debate → Decision（Agent Teams）
        portfolio = self.invoke_agent_teams(candidates, failure_patterns, pit_data)

        # Phase 5: Portfolio Construction（Python で最適化）
        optimized = self.optimize_portfolio(portfolio, pit_data)

        return optimized
```

この設計では、Phase 1（定量スクリーニング）と Phase 5（ポートフォリオ最適化）を Python で実行し、Phase 2-4（定性分析・ディベート・判断）を Agent Teams で実行する。CrewAI Flows が「Crews と単一 LLM コールの混在」を可能にしているように、当プロジェクトでは「Agent Teams と Python コードの混在」を実現する。

さらに、Flows の `@router` パターンは条件分岐に応用できる。たとえば、Phase 2 の分析結果に基づき、確信度が低い銘柄にはより詳細な Phase 3（ディベート3ラウンド）を適用し、確信度が高い銘柄にはディベートを省略する、といった動的なフロー制御が考えられる：

```python
def route_by_conviction(self, analysis_result):
    """分析結果の確信度に基づくルーティング"""
    if analysis_result.preliminary_conviction > 80:
        return "skip_debate"  # 明確なケースはディベート省略
    elif analysis_result.preliminary_conviction < 30:
        return "skip_debate"  # 明確な不採用もディベート省略
    else:
        return "full_debate"  # グレーゾーンのみ詳細ディベート
```

このルーティングにより、500銘柄の全候補に対してフルディベートを実行する非効率を回避し、バックテストの計算コストを削減できる。

### 5.4 CrewAI AOP のオブザーバビリティ・ガバナンス機能の参考

CrewAI AOP のオブザーバビリティ機能は、当プロジェクトの「投資判断の透明性」要件と直接対応する。PoC 設計では全判断を構造化ファイルとして記録する方針だが、AOP の機能から以下の改善を検討すべきである。

#### オブザーバビリティへの示唆

**現状**: 各フェーズの出力ファイル（JSON）が判断の記録として機能。
**改善案**: 以下の追加メタデータを記録する。

```json
{
  "execution_metadata": {
    "timestamp": "2024-03-15T10:30:00Z",
    "phase": "Phase 4: Decision",
    "agent": "T8_FundManager",
    "input_files": [
      "debate_transcripts/AAPL.json",
      "stock_analyses/AAPL.json"
    ],
    "execution_time_seconds": 45,
    "token_usage": {
      "input_tokens": 15000,
      "output_tokens": 3000
    },
    "model_version": "claude-opus-4-6",
    "skills_referenced": ["dogma.md", "KB1", "KB2"]
  },
  "decision": {
    "ticker": "AAPL",
    "action": "BUY",
    "conviction_score": 78,
    "rationale": "..."
  }
}
```

この `execution_metadata` により、「どのエージェントが、どの情報を参照し、どれだけの計算リソースを使って、何を判断したか」が完全にトレーサブルになる。CrewAI AOP のリアルタイム監視機能は当面不要だが、事後分析のための構造化ログは必須である。

#### ガバナンスへの示唆

金融規制の観点から、以下のガバナンス機能を設計段階で組み込むことを提案する：

1. **判断根拠の記録義務**: ファンドマネージャーエージェント（T8）の全判断に、参照した分析結果と重み付けの記録を義務化
2. **リスク制約の事前検証**: ポートフォリオ構築前に、セクター上限（25%）、個別銘柄上限（5%）等の制約をプログラム的に検証
3. **バイアス検出**: KB2 パターン集との照合結果を記録し、確証バイアスや群集心理の影響を定量化
4. **改版履歴**: KB（dogma.md, KB1-3）の変更がバックテスト結果に与える影響を追跡するための、KB バージョンとポートフォリオパフォーマンスの対応記録

### 5.5 当プロジェクトが CrewAI に対して持つ優位性

CrewAI の詳細分析を踏まえ、当プロジェクト（Claude Code Agent Teams ベース）が持つ構造的優位性を整理する。

#### 優位性 1：ナレッジベース注入の精密性

当プロジェクトの4層ナレッジベース（dogma.md → KB1 → KB2 → KB3）は、Skills メカニズムを通じてエージェントに**決定論的に**注入される。CrewAI では同等の機能を実現するには RAG パイプラインの構築が必要であり、検索精度の問題が発生する。

特に重要なのは、KB2（12パターン）の**却下パターン**（A-G）と**高評価パターン**（I-V）が、エージェントの判断基準として明示的に注入される点である。CrewAI の `backstory` にこれらのパターンを全て記述することは、トークン制限の観点から非現実的であり、RAG では関連パターンの検索漏れリスクがある。

Claude Code の Skills は、参照先ファイルの全内容をエージェントのコンテキストに含めるため、パターンの検索漏れが原理的に発生しない。この「漏れのない知識注入」は、投資判断の品質に直結する優位性である。

#### 優位性 2：Subscription 内 LLM 推論

CrewAI は API 従量課金モデルに依存しており、大規模なバックテスト（500銘柄 x 80四半期 x 12エージェント）のコストは膨大になる。Claude Code Subscription 内でのエージェント実行は、この変動費を固定費に変換する。

これは単なるコスト削減ではなく、**実験の自由度**に直結する。API コストを気にせず、KB の微調整 → バックテスト再実行 → 結果比較、というサイクルを高速に回せることは、投資戦略の研究開発において決定的な優位性である。

#### 優位性 3：柔軟な依存関係定義

前述の通り、Agent Teams の依存関係定義は CrewAI の Sequential/Hierarchical プロセスよりも表現力が高い。当プロジェクトのパイプライン（6フェーズ、並列分析、条件付きディベート）を自然に表現できる。

CrewAI Flows を使えば同等の表現力は得られるが、Python コードのボイラープレートが必要になる。Agent Teams では、Markdown の宣言的な依存関係定義だけで同じことが実現でき、エージェント設計者（金融専門家）の負担が小さい。

#### 優位性 4：ファイルベースの状態管理との親和性

当プロジェクトでは、各フェーズの出力を JSON ファイルとして保存し、次のフェーズの入力とする。この設計は以下の利点を持つ：

- **再現性**: 任意のフェーズから再実行可能（中間結果が保存されているため）
- **デバッグ容易性**: 各フェーズの出力を人間が直接確認可能
- **監査証跡**: 全判断プロセスがファイルとして永続化

CrewAI の Crews では、エージェント間のデータ共有が暗黙的であり、中間結果の永続化には追加の実装が必要である。Flows の `self.state` は明示的だが、メモリ上の状態であり、永続化は別途実装が必要である。

#### 優位性 5：既存パッケージとの統合

当プロジェクトは `finance` リポジトリ内の既存パッケージ群（`market`, `edgar`, `factor`, `strategy` 等）と直接統合できる。エージェントが MCP ツール経由でこれらのパッケージの機能を呼び出すことで、市場データ取得、SEC Filings 解析、ファクター計算、ポートフォリオ最適化といった機能をシームレスに利用できる。

CrewAI で同等の統合を実現するには、各パッケージを CrewAI Tool としてラップする追加開発が必要であり、保守コストが増加する。

### 5.6 CrewAI から取り入れるべき設計パターンの要約

以上の分析を踏まえ、CrewAI から当プロジェクトに取り入れるべき設計パターンを優先度順に整理する。

| 優先度 | 設計パターン | 適用箇所 | 期待効果 |
|--------|------------|---------|---------|
| **高** | Dual LLM（deep/quick分類） | 全12エージェントの分類 | バックテスト速度の向上、コスト効率改善 |
| **高** | エージェントメタデータの標準化 | `.claude/agents/` 定義 | 一貫性の確保、ツーリングの発展基盤 |
| **高** | 実行メタデータの記録 | 各フェーズの出力 JSON | オブザーバビリティ向上、デバッグ容易化 |
| **中** | 条件付きルーティング | Phase 2 → Phase 3 の遷移 | 計算コスト削減（確信度によるディベート省略） |
| **中** | ガバナンス制約の事前検証 | Phase 5 前 | 規制準拠の保証 |
| **低** | YAML メタデータのエクスポート | ドキュメント生成 | 外部ツールとの連携 |

---

## 6. まとめ

CrewAI は、マルチエージェントフレームワーク市場において最も成熟したプロダクション指向のプロジェクトの1つである。Crews と Flows の二層構造、YAML ベースの宣言的定義、AOP によるエンタープライズ機能の提供は、MAS の実用化に向けた重要な技術的到達点を示している。

しかし、当プロジェクト（MAS4InvestmentTeam）の文脈では、Claude Code Agent Teams は以下の5つの構造的優位性を持つ：

1. **KB 注入の精密性**: 4層ナレッジベースの決定論的な注入（RAG の確率的検索ではなく Skills の明示的参照）
2. **Subscription 内 LLM**: 変動費の固定費化による実験自由度の向上
3. **柔軟な依存関係**: Markdown 宣言による直列・並列・条件分岐の自然な表現
4. **ファイルベースの状態管理**: 再現性・デバッグ容易性・監査証跡の三位一体
5. **既存パッケージ統合**: MCP ツール経由の `market`, `edgar`, `factor`, `strategy` パッケージへのシームレスなアクセス

一方、CrewAI から積極的に取り入れるべきパターンは以下の3点である：

1. **Dual LLM 戦略**: エージェントをタスクの推論深度で分類し、リソース配分を最適化する
2. **エージェントメタデータの標準化**: YAML の3属性モデルを参考に、Markdown 定義にメタデータブロックを導入する
3. **イベント駆動のフロー制御**: Flows の `@listen` / `@router` パターンを参考に、Python バックテストエンジンと Agent Teams の境界を設計する

これらの知見を MAS4InvestmentTeam の PoC 実装に反映することで、CrewAI の設計知見と Claude Code Agent Teams の構造的優位性を組み合わせた、金融ドメインに最適化されたマルチエージェント投資システムの構築が可能となる。
