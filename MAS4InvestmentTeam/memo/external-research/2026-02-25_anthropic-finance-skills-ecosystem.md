# Anthropic 公式 Finance Skills と Claude Code エコシステムの詳細調査レポート

**作成日**: 2026-02-25
**対象**: MAS4InvestmentTeam プロジェクトへの適用検討

---

## 目次

1. [Anthropic の金融向け戦略](#1-anthropic-の金融向け戦略)
2. [Agent Skills フレームワークの技術的分析](#2-agent-skills-フレームワークの技術的分析)
3. [公開 Finance Skills の評価](#3-公開-finance-skills-の評価)
4. [Claude Code エコシステム全体の分析](#4-claude-code-エコシステム全体の分析)
5. [MAS4InvestmentTeam への適用](#5-mas4investmentteam-への適用)

---

## 1. Anthropic の金融向け戦略

### 1.1 「Advancing Claude for Financial Services」の全体像

2025年10月、Anthropic は金融サービス向けの包括的な取り組みとして「Advancing Claude for Financial Services」を発表した。この発表は、LLM の汎用的な応用から金融ドメインへの垂直統合へと舵を切る転換点であり、以下の3つの柱で構成されている。

**第一の柱: Claude for Excel アドイン**

金融業界の実務者が最も多く利用するツールは依然として Excel である。Claude for Excel は、スプレッドシート内で直接 Claude を呼び出し、セル内のデータに対して自然言語で分析・変換・要約を実行できるアドインである。これにより、投資銀行のアナリストがバリュエーションモデルを構築する際、従来は VBA マクロや手動計算に依存していたプロセスを、Claude への自然言語指示で代替できるようになった。

特に注目すべきは、Excel アドインが単なるチャットボットではなく、セルの参照・数式の理解・テーブル構造の認識を備えている点である。DCF モデルの前提条件変更が下流の全セルに波及する構造を理解し、「WACC を50bp引き上げた場合のフェアバリューの変化」といった what-if 分析を即座に実行できる。

**第二の柱: リアルタイム市場データ・ポートフォリオ分析コネクタ**

コネクタは Bloomberg、Refinitiv（現 LSEG）、FactSet などの主要データプロバイダーと Claude を接続するインターフェース層である。これにより、Claude はリアルタイムの株価・債券利回り・為替レート・デリバティブ価格にアクセスし、プロンプトベースでポートフォリオのリスク分析やエクスポージャー計算を実行できる。

この設計は MCP（Model Context Protocol）の思想と一貫している。データソースへの接続を標準化し、エージェントが必要に応じて動的にデータを取得する構造を実現している。

**第三の柱: 6つの Finance Agent Skills**

Anthropic が公式に提供する金融特化型の Agent Skills は以下の6つである。

1. **DCF（Discounted Cash Flow）モデル構築**: 企業の将来キャッシュフローを予測し、適切な割引率で現在価値を算出する完全なモデルを構築するスキル。WACC の算出、Terminal Value の設定、感応度分析を含む。
2. **カバレッジレポート開始（Initiating Coverage）**: 機関投資家向けの包括的なカバレッジ開始レポートを生成するスキル。業界概観、競争ポジション、財務分析、バリュエーション、投資リスクの各セクションを体系的にカバーする。
3. **ポートフォリオ分析**: 既存ポートフォリオの属性分析（セクター配分、ファクターエクスポージャー、リスク寄与度）を実行するスキル。
4. **リスクアセスメント**: 個別銘柄・ポートフォリオレベルでのリスク要因を特定・定量化するスキル。
5. **財務諸表分析**: 10-K/10-Q の財務諸表から主要指標を抽出・解釈し、トレンド分析と同業他社比較を行うスキル。
6. **規制コンプライアンス分析**: 金融規制（Dodd-Frank、Basel III、MiFID II 等）の要件に対するコンプライアンス状況を評価するスキル。

### 1.2 Vals AI Finance Agent Benchmark

Anthropic は金融タスクの評価基盤として Vals AI Finance Agent Benchmark を活用している。このベンチマークは金融業界の実務タスク（財務モデリング、リスク評価、レポート作成、データ分析）を網羅しており、2025年時点で Sonnet 4.5 が 55.3% の精度を達成しトップとなった。

この数値は一見低く見えるが、ベンチマークの難度を考慮する必要がある。財務モデリングでは数値の正確性が厳密に評価され、1セントの誤差でも不正解となる。また、レポート作成では機関投資家が期待するフォーマット・深度・一貫性が評価基準となる。55.3% は、金融の実務経験2-3年のジュニアアナリストに匹敵する水準と解釈できる。

注目すべきは、このスコアが Agent Skills の適用なしの「素」の状態での結果である点だ。Agent Skills を適用することで、ドメイン知識の注入によりスコアの大幅な向上が見込まれる。これは当プロジェクトの dogma.md + KB1/KB2/KB3 による知識注入アプローチと同じ思想であり、Anthropic が公式にこの方向性を支持していることを意味する。

### 1.3 金融業界における Claude の採用動向

Anthropic の金融向け取り組みの背景には、大手金融機関による Claude の採用拡大がある。Goldman Sachs、Morgan Stanley、Citadel などがリサーチ業務に Claude を試験導入しており、特にアナリストレポートの初稿作成、財務モデルのレビュー、規制変更のインパクト分析において生産性の向上が報告されている。

この動向は MAS4InvestmentTeam プロジェクトにとって追い風である。Anthropic が金融ドメインに注力することで、モデル自体の金融タスク性能が継続的に向上し、我々の MAS エージェント群の判断品質も連動して改善される。

---

## 2. Agent Skills フレームワークの技術的分析

### 2.1 SKILL.md の構造と設計哲学

Claude Code の Agent Skills は、`.claude/skills/` ディレクトリに配置される SKILL.md ファイルを中心とした宣言的な知識注入フレームワークである。その構造は以下の通りである。

```
.claude/skills/{skill_name}/
├── SKILL.md          # スキル定義（description + instruction）
├── guide.md          # 詳細ガイド（オプション）
├── templates/        # テンプレート（オプション）
└── examples/         # 例示（オプション）
```

SKILL.md は2つのセクションで構成される。

**description セクション**: スキルの目的と適用条件を自然言語で記述する。Claude Code はこの記述を読み取り、ユーザーのタスクに適合するスキルを自動的に選択する。例えば、「DCFモデルを構築して」というリクエストに対して、description に「Discounted Cash Flow モデルの構築」と記載されたスキルが自動的にコンテキストにロードされる。

**instruction セクション**: スキルの実行手順、使用するツール、出力フォーマット、制約条件を記述する。これはシステムプロンプトの一部として Claude のコンテキストに注入され、タスク実行を誘導する。

この設計哲学は「宣言的知識注入」と呼べるものであり、手続き型のプログラミングではなく、「何を知っているべきか」「どのような判断基準で行動すべきか」を自然言語で定義する。

### 2.2 Skills vs MCP vs Agents の技術的関係

Claude Code のエコシステムは3つの主要コンポーネントで構成されており、それぞれが異なる関心事を担当する。David Cramer の分析に基づき、この3者の関係を整理する。

**Skills（知識層）**:
- 役割: ドメイン知識、手順、判断基準の注入
- 実装: SKILL.md ファイル（マークダウン）
- ロード方法: Claude Code がコンテキストとして自動認識
- 特徴: セットアップ不要、宣言的、人間が読める
- 限界: 外部データへのアクセス不可、実行能力なし

**MCP（ツール層）**:
- 役割: 外部ツール・データソースへの標準接続
- 実装: JSON-RPC ベースのサーバー
- ロード方法: `claude_desktop_config.json` または `.mcp.json` で設定
- 特徴: 構造化された I/O、スキーマ定義、バリデーション
- 限界: セットアップが必要、サーバーの起動・管理が必要

**Agents（実行層）**:
- 役割: コンテキスト分離された実行単位
- 実装: `.claude/agents/` のマークダウンファイル
- ロード方法: Task tool で起動（fork モード）
- 特徴: コンテキスト分離、並列実行可能、Agent Teams
- 限界: 各エージェントのコンテキストウィンドウに制約

3者の関係を図示すると以下のようになる。

```
┌─────────────────────────────────────────────┐
│                 Agent (実行層)                │
│                                             │
│  ┌──────────────┐    ┌──────────────┐       │
│  │   Skills     │    │   MCP        │       │
│  │  (知識層)    │    │  (ツール層)   │       │
│  │              │    │              │       │
│  │ SKILL.md     │    │ sec-edgar    │       │
│  │ guide.md     │    │ rss-reader   │       │
│  │ templates/   │    │ fetch        │       │
│  └──────────────┘    └──────────────┘       │
│                                             │
│  Agent は Skills から「何を知っているか」を、   │
│  MCP から「何ができるか」を受け取り、          │
│  タスクを実行する。                           │
└─────────────────────────────────────────────┘
```

### 2.3 Skills の技術的優位性

MCP と比較した Skills の優位性は以下の4点に集約される。

1. **ゼロセットアップ**: マークダウンファイルを配置するだけで機能する。MCP はサーバーの設定・起動・認証管理が必要。
2. **バージョン管理との親和性**: SKILL.md は Git で管理でき、変更履歴の追跡・レビュー・ロールバックが容易。MCP サーバーのバージョン管理はコードレベルで行う必要がある。
3. **人間可読性**: Skills の定義は自然言語で記述されるため、ドメインエキスパート（非エンジニア）がレビュー・修正できる。これは金融ドメインにおいて極めて重要な特性であり、ポートフォリオマネージャーやアナリストが直接 Skills の内容を検証できる。
4. **コンテキスト効率**: Skills はコンテキストウィンドウの一部として直接注入されるため、MCP のような外部呼び出しのオーバーヘッドがない。

### 2.4 将来の方向性: MCP が Skills を expose する可能性

David Cramer の分析では、将来的に MCP サーバーが Skills を expose する可能性が示唆されている。これは以下のシナリオを意味する。

```
現在:
  Skills = ローカルの .claude/skills/ に配置

将来:
  MCP Server → Skills を標準プロトコルで配信
  → 組織全体で Skills を共有
  → Skills のバージョン管理を中央集権化
  → アクセス制御・監査ログの追加
```

この方向性は、当プロジェクトの dogma.md + KB システムにとって重要な示唆を持つ。現在はローカルファイルとして管理している KB を、将来的には MCP サーバー経由で配信し、複数の MAS インスタンスや異なるプロジェクト間で共有できる可能性がある。

### 2.5 Skills のアンチパターン

Skills フレームワークの設計意図を逸脱した使い方として、以下のアンチパターンが知られている。

1. **過剰注入**: 全スキルを全エージェントに注入する。コンテキストウィンドウを圧迫し、注意力の分散を招く。
2. **手続き型記述**: SKILL.md にステップバイステップの手順を過度に詳細化する。Claude の柔軟な推論能力を制限してしまう。
3. **データの直接埋め込み**: 大量のデータを SKILL.md に直接含める。Skills は「知識」であり「データ」ではない。データは MCP 経由で取得すべき。
4. **スキル間の暗黙的依存**: スキル A がスキル B の存在を前提とするが、その依存関係が明示されない。

これらは当プロジェクトの52スキル・100エージェントの規模では特に注意が必要であり、KB の注入設計（アナリスト KB-MAS 統合設計書 §4.2 の「B+C ハイブリッド」方針）はアンチパターン1を明確に回避している。

---

## 3. 公開 Finance Skills の評価

### 3.1 VoltAgent/awesome-agent-skills（6,532 stars）

VoltAgent が管理する awesome-agent-skills は、Claude Code の Agent Skills コレクションとしては最大規模のリポジトリである。300を超えるスキルが登録されており、公式開発チームとコミュニティの両方から寄稿されている。

**金融関連スキルの概要**:
- DCF モデル構築（Anthropic 公式スキルのコミュニティ拡張版）
- 財務諸表分析（マルチ期間比較、同業比較機能付き）
- リスク評価（VaR、CVaR、ストレステスト）
- レポート生成（機関投資家向けフォーマット）

**評価**:
このコレクションの価値は「スキルの雛形」として活用できる点にある。各スキルの SKILL.md を読むことで、効果的なスキル設計のパターンを学ぶことができる。ただし、汎用的に設計されているため、特定の投資哲学や判断基準を反映したカスタマイズが必須である。当プロジェクトの dogma.md のような投資哲学の注入はコミュニティスキルには含まれておらず、これは当プロジェクトの差別化ポイントでもある。

### 3.2 quant-sentiment-ai/claude-equity-research（290 stars）

claude-equity-research は、機関投資家レベルのエクイティリサーチワークフローを Claude Code の Skills として実装したプロジェクトである。

**主要な特徴**:
1. **Goldman Sachs スタイルのフォーマット**: セルサイドの機関投資家レポートのフォーマットを忠実に再現するスキル。Investment Thesis、Industry Overview、Financial Analysis、Valuation、Risk Assessment の各セクションが定義されている。
2. **包括的なリスク評価フレームワーク**: 定量リスク（ベータ、ボラティリティ、VaR）と定性リスク（競争環境、規制リスク、ESG リスク）を統合的に評価するスキル。
3. **マルチステップ分析パイプライン**: データ収集 → 財務分析 → バリュエーション → リスク評価 → レポート生成 の各段階をスキルとして定義し、Agent Teams で連携させるパターン。

**当プロジェクトとの比較**:

| 項目 | claude-equity-research | 当プロジェクト |
|------|----------------------|--------------|
| 分析フレームワーク | セルサイドレポート再現 | バイサイド投資チーム再現 |
| 投資哲学の注入 | なし（汎用） | dogma.md + KB1/KB2/KB3 |
| 判断基準 | 一般的な財務指標 | 競争優位性ベースの8ルール |
| 意思決定メカニズム | 単一エージェント | マルチエージェント・ディベート |
| 出力 | セルサイドレポート | 投資判断ログ + ポートフォリオ |

**適用可能な要素**:
claude-equity-research の Initiating Coverage スキルのフォーマット定義は、当プロジェクトの Fundamental Analyst の出力テンプレートに応用できる。特に、Investment Thesis の構造化（Key Drivers、Risk Factors、Catalyst Events）は、MAS の `thesis_points` フォーマットと互換性が高い。

### 3.3 K-Dense-AI/claude-scientific-skills（8,241 stars）

claude-scientific-skills は、140のスキル、28の科学データベース、55の Python パッケージをカバーする大規模な科学計算スキルコレクションである。直接の金融スキルではないが、クオンツファイナンスに応用可能な統計分析・時系列モデリング・最適化のスキルが豊富に含まれている。

**クオンツファイナンスへの応用可能スキル**:

1. **統計分析スキル群**:
   - 回帰分析（線形、ロジスティック、正則化）
   - 時系列分析（ARIMA、GARCH、状態空間モデル）
   - ベイズ推論（事前分布の設定、MCMC）
   - これらは Phase 1 のスクリーニングにおけるファクター分析や、Phase 2 のバリュエーション分析に直接活用できる。

2. **最適化スキル群**:
   - 凸最適化（ポートフォリオ最適化の基盤）
   - 制約付き最適化（セクター上限、ポジション制約）
   - ブラックリターマン最適化（Phase 3 で導入予定）

3. **データ可視化スキル群**:
   - 時系列プロット（パフォーマンスチャート）
   - ヒートマップ（相関行列、ファクターエクスポージャー）
   - インタラクティブダッシュボード

**評価**:
K-Dense の強みは、各スキルが Python パッケージとの連携を前提として設計されている点にある。例えば、時系列分析スキルは `statsmodels` や `scipy` の具体的な API 呼び出しパターンを instruction に含んでおり、Claude が正確なコードを生成する確率が高い。当プロジェクトの `factor` パッケージや `strategy.risk` パッケージとの連携において、K-Dense のパターンを参考にしたスキル設計が有効である。

### 3.4 MCP Market での Agent Skills ランキング

2026年2月時点の MCP Market では、以下のスキルがトップランキングを占めている。

1. **Ralph Wiggum Autonomous Coding Loop**: 自律的なコーディングループを実装するスキル。テスト駆動の反復改善を自動化する。
2. **Professional Code Review**: プロフェッショナルなコードレビューを実行するスキル。
3. **Multi-Agent Coordination**: 複数エージェントの協調を管理するスキル。
4. **Resilient Multi-Model Planning**: 複数モデルを活用した計画立案スキル。
5. **Multi-Artifact Session Isolation**: セッション内の成果物を分離管理するスキル。

注目すべきは、上位スキルが金融特化ではなく「メタスキル」（他のスキルやエージェントの管理・協調に関するスキル）であることだ。これは、Skills エコシステムがまだ成熟途上であり、ドメイン特化型スキルの需要が十分に顕在化していないことを示唆している。逆に言えば、金融ドメインに特化した高品質なスキルセットは差別化要因となり得る。

---

## 4. Claude Code エコシステム全体の分析

### 4.1 Subagents（サブエージェント）の技術的構造

Claude Code のサブエージェントは `.claude/agents/` ディレクトリにマークダウン形式で定義される。各エージェントは以下の要素で構成される。

```markdown
# エージェント名

## Role（役割）
エージェントの責務と期待される振る舞いを定義。

## Context（コンテキスト）
参照すべきファイル、データ、他のエージェントの出力。

## Instructions（指示）
タスク実行の手順、制約、出力フォーマット。

## Output（出力）
生成すべきファイル、データ構造、レポートの仕様。
```

エージェントは Task tool を通じて起動され、`fork` モードでコンテキストが分離される。これにより、各エージェントは独立したコンテキストウィンドウ内で動作し、他のエージェントの状態に影響されない。

当プロジェクトでは100のエージェントが定義されており、金融リサーチ、コード品質、PR レビュー、ニュース収集など多岐にわたる。特に `ca-strategy/` 配下の8エージェント（transcript-loader、transcript-claim-extractor、transcript-claim-scorer、score-aggregator、sector-neutralizer、portfolio-constructor、output-generator）は、MAS4InvestmentTeam のエージェント設計の直接的な先行事例である。

### 4.2 Agent Teams による協調パターン

Agent Teams は、複数のエージェントを一つの lead エージェントが統括するパターンである。当プロジェクトでは以下の Agent Teams が稼働している。

| Agent Teams | Lead | チームメイト数 | フェーズ構成 |
|-------------|------|-------------|------------|
| dr-stock | dr-stock-lead | 8 | 5フェーズ |
| dr-industry | dr-industry-lead | 9 | 5フェーズ |
| finance-research | research-lead | 12 | 5フェーズ |
| weekly-report | weekly-report-lead | 6 | 直列制御 |
| ca-eval | ca-eval-lead | 7 | 5フェーズ |
| ca-strategy | ca-strategy-lead | 7 | 5フェーズ |
| test | test-lead | 4 | 依存グラフ |

これらの実績は、MAS Investment Team の Agent Teams 設計に直接活用できる。特に dr-stock-lead の5フェーズ制御パターン（データ収集 → 統合 → クロス検証 → 深掘り分析 → レポート生成）は、MAS の5フェーズ（Screening → Analysis → Debate → Decision → Portfolio Construction）と構造的に類似している。

### 4.3 MCP 統合の実績

当プロジェクトでは以下の MCP サーバーが統合されている。

- **sec-edgar-mcp**: SEC EDGAR からの企業情報、財務データ、Filing コンテンツの取得。Fundamental Analyst の主要データソース。
- **RSS MCP**: RSS フィードの監視・記事取得。ニュース収集ワークフローの基盤。
- **fetch MCP**: 任意の URL からのコンテンツ取得。
- **time MCP**: 現在時刻の取得（タイムゾーン対応）。
- **reddit MCP**: Reddit の投稿・コメント取得。

MCP の活用実績は、MAS エージェントがリアルタイムのデータにアクセスする際のパターンを提供している。特に sec-edgar-mcp は、Fundamental Analyst が SEC Filings にアクセスする際の主要チャネルとなり、CA Evaluator が fact-checking を行う際にも不可欠である。

### 4.4 エコシステムの成熟度評価

Claude Code エコシステム全体の成熟度を、当プロジェクトの利用経験に基づいて評価する。

| コンポーネント | 成熟度 | 強み | 課題 |
|-------------|--------|------|------|
| Skills | 高 | 宣言的、バージョン管理容易 | 大規模スキル間の依存管理が手動 |
| Agents | 高 | コンテキスト分離、Agent Teams | コンテキストウィンドウ制約 |
| MCP | 中-高 | 標準プロトコル、拡張性 | セットアップの複雑さ、エラーハンドリング |
| Task tool | 高 | シンプルな API、fork モード | 大量データの受け渡しに制約 |
| Agent Teams | 中 | 並列実行、フェーズ制御 | デバッグの困難さ、ログの追跡性 |

全体として、Claude Code エコシステムは金融ドメインのマルチエージェントシステム構築に十分な基盤を提供しているが、大規模なエージェント間協調のデバッグ・モニタリング・コスト管理において改善の余地がある。

---

## 5. MAS4InvestmentTeam への適用

### 5.1 Anthropic 公式 DCF/Coverage Skills の MAS への統合

Anthropic の公式 Finance Agent Skills のうち、DCF モデル構築とカバレッジレポート開始の2つのスキルは、MAS の Phase 2（Analysis）に直接統合可能である。

**DCF スキル → Valuation Analyst への統合**:

```
現在の設計（MAS PoC 設計書 §1.1）:
  [T3] Valuation Analyst → DCF・相対バリュエーション

統合後:
  [T3] Valuation Analyst
    ├── Skills: anthropic-dcf-skill（公式 DCF スキル）
    ├── Skills: valuation-standards（当プロジェクト独自の基準）
    ├── MCP: sec-edgar-mcp（財務データ取得）
    └── Output: {ticker}_valuation.json
```

公式 DCF スキルは WACC 算出・Terminal Value 設定・感応度分析のテンプレートを提供するが、当プロジェクト独自の要件として以下のカスタマイズが必要である。

1. **PoiT（Point-in-Time）制約の注入**: DCF モデルの前提条件に使用できるデータを `cutoff_date` 以前に制限する。公式スキルはリアルタイム分析を前提としているため、バックテスト用の時間的制約を追加する必要がある。
2. **匿名化対応**: カットオフ前期間では企業名・ティッカーが匿名化されるため、DCF スキルの出力からも企業固有の情報を除去する必要がある。
3. **確信度スコアとの連携**: DCF の算出結果を Fund Manager の確信度スコア（0-100）に反映するためのマッピングロジックを追加する。

**Coverage スキル → Fundamental Analyst への統合**:

Initiating Coverage スキルの構造化されたセクション定義（Industry Overview、Competitive Position、Financial Analysis）は、Fundamental Analyst の `thesis_points` 生成の品質向上に寄与する。具体的には、Coverage スキルの「Competitive Position」セクションのテンプレートを、当プロジェクトの KB1（8ルール）で強化する。

```markdown
# Fundamental Analyst SKILL.md（統合案）

## description
SEC Filings（10-K/10-Q）を分析し、企業のファンダメンタルズを評価する。
Anthropic Coverage スキルのセクション構造を基盤に、
当プロジェクト独自の競争優位性評価基準（dogma + KB1）を適用する。

## instruction
### Step 1: データ収集
- sec-edgar-mcp を使用し、直近の 10-K/10-Q を取得
- filing_date < cutoff_date の制約を厳守

### Step 2: 財務分析（Coverage スキルベース）
- Revenue growth, Margin trends, Cash flow analysis
- Peer comparison（同業他社比較）

### Step 3: 競争優位性評価（KB1 ベース）
- dogma.md の要約（~2KB）を参照し、以下の基準で評価:
  - rule01: 能力 vs 結果の区別
  - rule02: 名詞属性としての競争優位性
  - rule04: 定量的裏付けの有無
  ...
```

### 5.2 claude-equity-research パターンの Fundamental Analyst への応用

claude-equity-research の Goldman Sachs スタイルフォーマットは、Fundamental Analyst の出力品質を機関投資家レベルに引き上げるためのテンプレートとして活用できる。

**応用ポイント1: Investment Thesis の構造化**

claude-equity-research では Investment Thesis を以下の構造で定義している。

```json
{
  "investment_thesis": {
    "core_thesis": "一文要約",
    "key_drivers": ["成長ドライバー1", "成長ドライバー2"],
    "risk_factors": ["リスク1", "リスク2"],
    "catalyst_events": ["カタリスト1", "カタリスト2"],
    "target_price": {"base": 150, "bull": 180, "bear": 120}
  }
}
```

この構造を MAS の `thesis_points` フォーマットと統合する。

```json
{
  "thesis_points": [
    {
      "statement": "Services事業の粗利益率が70%超で安定成長",
      "evidence": "10-K Item 7 MD&A: Services revenue grew 14% YoY",
      "data_source": "10-K filed 2025-01-31",
      "strength": "strong",
      "category": "key_driver",
      "ca_relevance": "rule02_noun_attribute"
    }
  ]
}
```

`category` フィールド（key_driver / risk_factor / catalyst）と `ca_relevance` フィールド（KB1 ルールへの紐づけ）を追加することで、claude-equity-research の構造と当プロジェクトの KB システムを橋渡しする。

**応用ポイント2: リスク評価の体系化**

claude-equity-research のリスク評価フレームワーク（定量リスク + 定性リスクの統合）は、Bear Advocate のディベート論拠構築に応用できる。特に、ESG リスクの評価テンプレートは、KB2 の却下パターン A-G には含まれていない視点であり、MAS の評価対象を拡充する。

### 5.3 K-Dense 統計スキルの Phase 1 スクリーニングへの活用

Phase 1（Universe Screener）は Python で実装される定量スクリーニングであり、ファクタースコアの計算と複合スコアによるランキングを行う。K-Dense の統計スキル群は、このプロセスの品質向上に以下の形で寄与する。

**ファクター計算の精緻化**:

現在の設計ではモメンタム、サイズ、クオリティ、バリューの4ファクターを固定ウェイトで合成している。K-Dense の時系列分析スキルを活用し、以下の改善を導入できる。

1. **動的ウェイト調整**: ARIMA/GARCH モデルによるボラティリティレジームの推定に基づき、ファクターウェイトを動的に調整する。高ボラティリティ環境ではクオリティファクターのウェイトを増加させ、低ボラティリティ環境ではモメンタムファクターを増加させる。
2. **異常値検出**: 統計的異常値検出スキルを用いて、ファクタースコアの外れ値（データエラーやコーポレートアクションの影響）を自動検出・処理する。
3. **相関分析**: ファクター間の相関行列を定期的に計算し、多重共線性の問題を検出する。相関が閾値を超えた場合、ファクターの直交化または代替ファクターへの切替を推奨する。

**スクリーニング結果の検証**:

K-Dense のベイズ推論スキルを活用し、スクリーニング結果の信頼性を検証する。具体的には、各ファクタースコアに対する事後分布を推定し、スコアの不確実性が高い銘柄にはフラグを立てる。これにより、Phase 2 のアナリストエージェントがどの銘柄に特に注意を払うべきかのガイダンスを提供できる。

### 5.4 Agent Teams と Skills の組み合わせ最適化

MAS4InvestmentTeam のアーキテクチャにおいて、Agent Teams と Skills の最適な組み合わせ方を設計する。

**現在の設計（MAS PoC 設計書 §1.1）のエージェント・スキルマッピング**:

```
mas-invest-lead (Agent Teams Lead)
│
├── Phase 1: Universe Screener (Python、スキル不要)
│
├── Phase 2: Analysis
│   ├── fundamental-analyst
│   │   ├── Skills: fundamental-analysis（財務分析手順）
│   │   ├── Skills: dogma-summary（競争優位性の判断基準 ~2KB）
│   │   └── MCP: sec-edgar-mcp
│   │
│   ├── valuation-analyst
│   │   ├── Skills: anthropic-dcf-skill（公式 DCF スキル）
│   │   ├── Skills: relative-valuation（相対バリュエーション）
│   │   └── MCP: sec-edgar-mcp
│   │
│   ├── sentiment-analyst
│   │   ├── Skills: transcript-analysis（KB1-T 要約 ~3KB）
│   │   └── MCP: sec-edgar-mcp, rss-mcp
│   │
│   └── macro-analyst
│       ├── Skills: regime-detection（レジーム判定手順）
│       └── MCP: fred-mcp（Phase 2 追加）
│
├── Phase 2.5: CA Evaluation（新設）
│   └── ca-evaluator
│       ├── Skills: ca-eval-full（dogma + KB1 + KB2 + KB3 全量 ~62KB）
│       └── Input: Phase 2 全 Analyst の thesis_points
│
├── Phase 3: Debate
│   ├── bull-advocate
│   │   ├── Skills: bull-patterns（KB2 高評価パターン I-V ~5KB）
│   │   └── Input: CA Evaluator の出力
│   │
│   └── bear-advocate
│       ├── Skills: bear-patterns（KB2 却下パターン A-G ~5KB）
│       └── Input: CA Evaluator の出力
│
├── Phase 4: Decision
│   └── fund-manager
│       ├── Skills: conviction-scoring（dogma 確信度スケール ~2KB）
│       ├── Skills: fm-reporting（FM レポートテンプレート）
│       └── Input: 全 Phase の出力
│
└── Phase 5: Portfolio Construction
    ├── risk-manager (Python + Skills: risk-constraints)
    └── portfolio-constructor (Python + Skills: optimization-params)
```

**最適化のポイント**:

1. **スキルサイズの階層化**: 全量スキル（~62KB）は CA Evaluator のみに集中させ、他のエージェントには役割に応じた要約版（2-5KB）を提供する。これはアナリスト KB-MAS 統合設計書 §4.2 の「B+C ハイブリッド」方針と一致する。

2. **スキルのバージョン管理**: バックテスト期間中はスキル（KB）のバージョンを固定し、先読みバイアスを防止する。`config.json` にスキルバージョンを記録し、再現性を確保する。

3. **スキルの段階的ロード**: Phase 1（Python）ではスキルは不要。Phase 2 で各アナリスト用の特化スキルをロード。Phase 2.5 で KB 全量をロード。Phase 3-4 でディベート・判断用スキルをロード。この段階的ロードにより、コンテキストウィンドウの効率的な利用を実現する。

### 5.5 MAS 専用 Skills の設計指針

MAS4InvestmentTeam 専用の Skills セットを設計する際の指針を、Anthropic 公式スキル・コミュニティスキル・当プロジェクトの既存スキルの知見に基づいて定める。

**指針1: 投資哲学のスキル化**

dogma.md の投資哲学を、エージェントの役割に応じた複数のスキルファイルに分割する。

```
.claude/skills/mas-invest/
├── SKILL.md                    # MAS 全体概要
├── dogma-core/
│   ├── SKILL.md                # dogma の5原則（全エージェント共通 ~3KB）
│   └── confidence-scale.md     # 確信度スケール（FM 専用 ~1KB）
├── kb1-rules/
│   ├── SKILL.md                # 8ルールの要約版（Analyst 用 ~2KB）
│   └── full-rules.md           # 8ルールの全文（CA Evaluator 用 ~15KB）
├── kb2-patterns/
│   ├── SKILL.md                # パターン概要（全エージェント共通 ~2KB）
│   ├── bull-patterns.md        # 高評価パターン I-V（Bull 用 ~5KB）
│   └── bear-patterns.md        # 却下パターン A-G（Bear 用 ~5KB）
├── kb3-examples/
│   └── SKILL.md                # 5社34件の判断例（CA Evaluator 用 ~15KB）
└── templates/
    ├── thesis-point.json       # thesis_points の出力テンプレート
    ├── decision-log.json       # decision_log.json のテンプレート
    ├── debate-transcript.json  # ディベートの出力テンプレート
    └── fm-report.md            # FM レポートのテンプレート
```

**指針2: PoiT（Point-in-Time）制約のスキル化**

バックテストにおける時間的制約を、専用のスキルとして定義する。これにより、全エージェントが同一の時間的制約を認識し、先読みバイアスを構造的に排除する。

```markdown
# .claude/skills/mas-invest/temporal-constraints/SKILL.md

## description
MAS バックテストにおける時間的制約（Point-in-Time）を定義する。
全エージェントはこのスキルを参照し、cutoff_date 以降の情報を
使用してはならない。

## instruction
1. cutoff_date は `temporal_context.json` から読み取る
2. SEC Filings は filing_date < cutoff_date のもののみ使用可能
3. 価格データは cutoff_date 以前のもののみ使用可能
4. 将来の株価、業績、イベントに関する推論は禁止
5. カットオフ前期間では企業名・ティッカーは匿名化されている
```

**指針3: エージェント間データフローのスキル化**

MAS のエージェント間で受け渡されるデータのスキーマを、スキルとして定義する。これにより、`subagent-data-passing.md` のルールをスキルレベルで強制できる。

```markdown
# .claude/skills/mas-invest/data-flow/SKILL.md

## description
MAS エージェント間のデータフローの定義。
各エージェントは入力・出力のスキーマを厳守すること。

## instruction
### Phase 2 → Phase 2.5（Analyst → CA Evaluator）
入力スキーマ: thesis_points[] + risk_factors[] + key_metrics{}
必須フィールド: statement, evidence, data_source, strength

### Phase 2.5 → Phase 3（CA Evaluator → Bull/Bear）
入力スキーマ: ca_claims[] + overall_ca_score + warnings[]
必須フィールド: claim, ca_confidence, rules_applied

### Phase 3 → Phase 4（Debate → Fund Manager）
入力スキーマ: debate_rounds[] + ca_evaluation{}
必須フィールド: round, bull, bear, evidence_cited
```

**指針4: 既存 CA-Eval 実績のスキル化**

CA-Eval で12社の評価実績がある。この実績データをスキルとして形式化し、CA Evaluator の判断品質を向上させる。

```markdown
# .claude/skills/mas-invest/ca-eval-learnings/SKILL.md

## description
CA-Eval の12社評価実績から得られた判断パターンの要約。
CA Evaluator はこのスキルを参照し、過去の評価結果と
一貫した判断を行うこと。

## instruction
### よくある判断ミスのパターン
1. 高シェアを競争優位性と誤認する（rule01 違反率: 40%）
2. 定性的な主張に高い確信度を付与する（rule04 違反率: 35%）
3. 業界全体の特性を個社の優位性と混同する（rule07 違反率: 25%）

### 確信度の分布ガイドライン
- 90% は極めてまれ（6%）。構造的優位性 + CAGR接続 + 定量的裏付けの全てが揃う場合のみ
- 50% が最頻値（35%）。方向性は正しいが裏付けが不十分
- 30% 以下は積極的に付与すべき（飛躍的解釈には厳しく）
```

### 5.6 エコシステムの将来方向への準備

Skills 経由の MCP expose が実現した場合に備え、以下の準備を進めておく。

**準備1: KB のモジュール化**

現在の dogma.md + KB1/KB2/KB3 は大きなマークダウンファイルとして管理されている。将来の MCP 配信に備え、各 KB コンポーネントを独立したモジュールとして構造化する。

```
analyst/Competitive_Advantage/analyst_YK/
├── dogma/
│   ├── v1.0/
│   │   └── dogma.md          # バージョン管理
│   └── latest -> v1.0/
├── kb1/
│   ├── v1.0/
│   │   ├── rules.md          # 8ルール定義
│   │   └── schema.json       # ルールのスキーマ定義
│   └── latest -> v1.0/
├── kb2/
│   ├── v1.0/
│   │   ├── patterns.md       # 12パターン定義
│   │   └── schema.json
│   └── latest -> v1.0/
└── kb3/
    ├── v1.0/
    │   ├── examples.md        # 5社34件
    │   └── schema.json
    └── latest -> v1.0/
```

**準備2: Skills のスキーマ定義**

将来的に MCP サーバーが Skills を配信する際、スキルの入出力スキーマが標準化される可能性がある。先行して、各スキルの入出力を JSON Schema で定義しておく。

```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "title": "CA Evaluator Skill Input",
  "type": "object",
  "required": ["thesis_points", "cutoff_date"],
  "properties": {
    "thesis_points": {
      "type": "array",
      "items": {
        "type": "object",
        "required": ["statement", "evidence", "data_source"],
        "properties": {
          "statement": {"type": "string"},
          "evidence": {"type": "string"},
          "data_source": {"type": "string"},
          "strength": {"enum": ["strong", "moderate", "weak"]}
        }
      }
    },
    "cutoff_date": {"type": "string", "format": "date"}
  }
}
```

**準備3: スキルの品質メトリクス導入**

各スキルの有効性を定量的に評価するメトリクスを導入する。

| メトリクス | 計算方法 | 目標値 |
|-----------|---------|--------|
| 整合性スコア | CA Evaluator の出力と Y の Phase 2 スコアの相関 | r > 0.7 |
| ルール適用率 | 8ルール中、実際に適用された割合 | > 80% |
| 警鐘精度 | CA Evaluator の警鐘が Y の実際の判断と一致する割合 | > 60% |
| コンテキスト効率 | スキルサイズ / 判断品質向上幅 | 最小化 |

### 5.7 統合ロードマップ（エコシステム視点）

MAS4InvestmentTeam への Anthropic Finance Skills エコシステムの統合を、段階的に進めるロードマップを以下に示す。

```
Phase A: 基盤整備（Stage 2 と並行）
├── MAS 専用 Skills ディレクトリ構造の作成
├── dogma-core スキルの作成（5原則の要約版）
├── temporal-constraints スキルの作成
├── data-flow スキルの作成
└── テンプレートの整備（thesis-point.json 等）

Phase B: Analyst スキル統合（Stage 3 と並行）
├── Anthropic DCF スキルのカスタマイズ → Valuation Analyst
├── claude-equity-research の Coverage パターン → Fundamental Analyst
├── KB1 要約スキルの作成 → Fundamental Analyst
├── CA Evaluator 用 KB 全量スキルの作成
└── 1銘柄 end-to-end テスト

Phase C: ディベート・判断スキル統合（Stage 4 と並行）
├── KB2 Bull/Bear パターンスキルの作成
├── conviction-scoring スキルの作成（dogma 確信度スケール）
├── FM レポートテンプレートスキルの作成
└── K-Dense 統計スキルの Phase 1 スクリーニングへの導入

Phase D: 最適化と拡張（Stage 5 と並行）
├── スキルの品質メトリクス導入と測定
├── KB のモジュール化とバージョン管理
├── MCP expose 準備（スキーマ定義）
├── KB3 の拡張（10-12社への拡大）
└── Y のフィードバックループによるスキル更新
```

### 5.8 差別化要因の整理

当プロジェクトが Anthropic 公式スキルやコミュニティスキルと比較して持つ差別化要因を整理する。

| 観点 | 公式/コミュニティ | 当プロジェクト（MAS4InvestmentTeam） |
|------|-----------------|--------------------------------------|
| **投資哲学** | 汎用的・中立的 | dogma.md に明示的な投資哲学を定義 |
| **判断基準** | 一般的な財務指標 | KB1 の8ルールによる構造的な判断基準 |
| **パターン認識** | なし | KB2 の12パターン（却下7 + 高評価5） |
| **暗黙知の形式化** | なし | KB3 の5社34件の判断例 |
| **意思決定メカニズム** | 単一エージェント | 12エージェントの構造化ディベート |
| **透明性** | レポート出力 | 全判断のJSON構造化ログ |
| **バイアス排除** | なし | PoiT + ティッカー匿名化の3層防御 |
| **確信度の校正** | なし | Y の判断パターンに基づく確信度分布 |

これらの差別化要因は、Anthropic のエコシステムが提供する基盤の上に構築されるものであり、「公式スキルの強化版」として位置づけられる。公式スキルが「金融の汎用的な分析能力」を提供するのに対し、当プロジェクトのスキルは「特定の投資哲学に基づく判断能力」を提供する。

---

## 総括

Anthropic の Finance Agent Skills エコシステムは、MAS4InvestmentTeam プロジェクトにとって3つの意味で重要である。

1. **基盤の提供**: DCF、Coverage、ポートフォリオ分析などの汎用スキルが、MAS の各エージェントのベースラインスキルとして利用可能。ゼロから構築する必要がなくなる。

2. **設計パターンの参照**: Skills、MCP、Agents の3層アーキテクチャは、当プロジェクトの KB 統合設計（dogma → Skills、SEC EDGAR → MCP、12エージェント → Agent Teams）と一致する。Anthropic 公式のベストプラクティスに沿った設計であることが確認できた。

3. **将来方向の整合**: MCP 経由の Skills 配信、スキーマの標準化、品質メトリクスの導入など、エコシステムの進化方向は当プロジェクトの拡張計画と整合している。先行して準備を進めることで、エコシステムの進化を即座に取り込める体制を構築できる。

当プロジェクトの52スキル・100エージェント・dogma+KB システムは、Anthropic が「Advancing Claude for Financial Services」で提示した方向性を先取りしたものであり、エコシステムの成熟に伴いその価値がさらに増大する構造にある。

---

## 参考リソース

| リソース | URL / パス | 備考 |
|---------|-----------|------|
| Anthropic Finance Skills 発表 | anthropic.com/research/advancing-claude-financial-services | 2025年10月 |
| Vals AI Finance Benchmark | vals.ai/benchmarks/finance | Sonnet 4.5: 55.3% |
| VoltAgent/awesome-agent-skills | github.com/VoltAgent/awesome-agent-skills | 6,532 stars |
| claude-equity-research | github.com/quant-sentiment-ai/claude-equity-research | 290 stars |
| K-Dense-AI/claude-scientific-skills | github.com/K-Dense-AI/claude-scientific-skills | 8,241 stars |
| MAS PoC 設計書 | MAS4InvestmentTeam/plan/2026-02-16_mas-investment-team-poc-design.md | |
| アナリスト KB-MAS 統合設計 | MAS4InvestmentTeam/plan/2026-02-25_analyst-kb-mas-integration.md | |
| David Cramer Skills vs MCP 分析 | david-cramer.com/blog/skills-vs-mcp | 2025年 |
