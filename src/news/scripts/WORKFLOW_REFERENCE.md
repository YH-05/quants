# finance_news_workflow.py - 依存関係と使い方リファレンス

## 概要

`finance_news_workflow.py` は金融ニュース収集パイプラインの CLI エントリポイント。
4 段階のパイプライン（収集 -> 抽出 -> 要約 -> 公開）を順次実行し、
RSS フィードの記事を GitHub Issue として自動投稿する。

---

## 実行方法

```bash
# デフォルト設定で実行
python -m news.scripts.finance_news_workflow

# dry-run（Issue 作成をスキップ）
python -m news.scripts.finance_news_workflow --dry-run

# ステータスでフィルタ（カンマ区切り）
python -m news.scripts.finance_news_workflow --status index,stock

# 処理記事数を制限
python -m news.scripts.finance_news_workflow --max-articles 10

# DEBUG ログを有効化
python -m news.scripts.finance_news_workflow --verbose

# 設定ファイルを指定
python -m news.scripts.finance_news_workflow --config data/config/news-collection-config.yaml
```

### CLI オプション一覧

| オプション | 型 | デフォルト | 説明 |
|-----------|------|-----------|------|
| `--config` | str | `data/config/news-collection-config.yaml` | YAML 設定ファイルパス |
| `--dry-run` | flag | `False` | Issue 作成をスキップ |
| `--status` | str | `None`（全件） | フィルタするステータス（カンマ区切り） |
| `--max-articles` | int | `None`（無制限） | 処理する最大記事数 |
| `--verbose`, `-v` | flag | `False` | コンソールログを DEBUG レベルに設定 |

### 戻り値

- 正常終了: `0`
- 異常終了: `1`（設定ファイル未検出 / ワークフロー例外）

---

## パイプライン全体像

```
finance_news_workflow.py (CLI)
│
├── load_config()           設定ファイル読み込み
│   └── NewsWorkflowConfig  Pydantic モデルへバリデーション
│
└── NewsWorkflowOrchestrator.run()
    │
    ├── [1/4] RSSCollector.collect()
    │   ├── rss-presets.json からフィード定義読み込み
    │   ├── httpx で各フィードを並列取得
    │   ├── FeedParser でパース → FeedItem
    │   ├── CollectedArticle に変換
    │   ├── max_age_hours でフィルタ
    │   └── blocked_domains でフィルタ
    │   出力: list[CollectedArticle]
    │
    ├── ステータスフィルタ適用（--status オプション）
    ├── 記事数制限適用（--max-articles オプション）
    │
    ├── [2/4] TrafilaturaExtractor.extract()（asyncio.Semaphore で並列制御）
    │   ├── trafilatura で本文抽出
    │   ├── 失敗時: Playwright フォールバック（設定有効時）
    │   └── リトライ: 最大 3 回、指数バックオフ（1s, 2s, 4s）
    │   出力: list[ExtractedArticle]  ※ SUCCESS のみ次段階へ
    │
    ├── [3/4] Summarizer.summarize_batch()（バッチ単位で並列）
    │   ├── Claude Agent SDK でプロンプト送信
    │   ├── ストリーミングレスポンス → テキスト収集
    │   └── JSON パース → StructuredSummary（4 セクション）
    │   出力: list[SummarizedArticle]  ※ SUCCESS のみ次段階へ
    │
    └── [4/4] Publisher.publish_batch()
        ├── 重複チェック: 直近 7 日間の Issue URL 照合
        ├── Issue タイトル生成: "[カテゴリ] 記事タイトル"
        ├── Issue ボディ生成: 4 セクション Markdown
        ├── gh issue create → Issue 作成
        ├── gh project item-add → Project 追加
        ├── gh project item-edit → Status / PublishedDate 設定
        └── 出力: list[PublishedArticle]

    → WorkflowResult を構築して JSON 保存
    → print_failure_summary() で失敗詳細を表示
```

---

## 依存関係ツリー

```
finance_news_workflow.py
├── news.config.models
│   ├── load_config()              YAML → NewsWorkflowConfig
│   ├── NewsWorkflowConfig         ルート設定モデル
│   ├── yaml                       YAML パーサー
│   └── pydantic                   バリデーション
│
├── news.orchestrator
│   └── NewsWorkflowOrchestrator   パイプライン統合
│       ├── news.collectors.rss.RSSCollector
│       │   ├── news.collectors.base.BaseCollector    抽象基底クラス
│       │   ├── httpx                                 非同期 HTTP クライアント
│       │   ├── rss.core.parser.FeedParser            RSS/Atom パーサー
│       │   │   └── feedparser                        外部ライブラリ
│       │   └── rss.types.{FeedItem, PresetFeed}      RSS 型定義
│       │
│       ├── news.extractors.trafilatura.TrafilaturaExtractor
│       │   ├── news.extractors.base.BaseExtractor    抽象基底クラス
│       │   ├── rss.services.article_extractor.ArticleExtractor
│       │   │   ├── trafilatura                       本文抽出
│       │   │   ├── httpx                             HTTP フォールバック
│       │   │   └── lxml                              HTML パーサー
│       │   └── news.extractors.playwright.PlaywrightExtractor  (optional)
│       │
│       ├── news.summarizer.Summarizer
│       │   ├── claude_agent_sdk                      Claude AI SDK
│       │   └── pydantic.ValidationError              JSON バリデーション
│       │
│       └── news.publisher.Publisher
│           ├── subprocess                            gh CLI 実行
│           └── json                                  レスポンスパース
│
├── news.models
│   ├── CollectedArticle           収集済み記事
│   ├── ExtractedArticle           本文抽出済み記事
│   ├── SummarizedArticle          要約済み記事
│   ├── PublishedArticle           公開済み記事
│   ├── WorkflowResult             ワークフロー結果
│   ├── StructuredSummary          4 セクション構造化要約
│   ├── FailureRecord              失敗記録
│   ├── FeedError                  フィードエラー記録
│   ├── ArticleSource              ソースメタデータ
│   ├── SourceType                 ソース種別 (RSS/YFINANCE/SCRAPE)
│   ├── ExtractionStatus           抽出ステータス
│   ├── SummarizationStatus        要約ステータス
│   └── PublicationStatus          公開ステータス
│
└── utils_core.logging
    ├── get_logger()               構造化ロガー取得
    └── setup_logging()            ログ設定（コンソール + ファイル）
```

---

## データモデル詳細

### パイプライン段階別モデル

各段階の出力モデルは前段階のモデルをネストして保持する。

```
CollectedArticle
├── url: HttpUrl                   元記事 URL
├── title: str                     記事タイトル
├── published: datetime | None     公開日時
├── raw_summary: str | None        RSS の生要約
├── source: ArticleSource          ソース情報
│   ├── source_type: SourceType    RSS / YFINANCE / SCRAPE
│   ├── source_name: str           フィード名 (例: "CNBC Markets")
│   ├── category: str              カテゴリ (例: "market")
│   └── feed_id: str | None        フィード ID
└── collected_at: datetime         収集日時

ExtractedArticle
├── collected: CollectedArticle    元の収集記事
├── body_text: str | None          抽出した本文
├── extraction_status: ExtractionStatus
│   SUCCESS / FAILED / PAYWALL / TIMEOUT
├── extraction_method: str         "trafilatura" / "playwright" / "fallback"
└── error_message: str | None

SummarizedArticle
├── extracted: ExtractedArticle    元の抽出記事
├── summary: StructuredSummary | None
│   ├── overview: str              概要
│   ├── key_points: list[str]      重要ポイント
│   ├── market_impact: str         市場への影響
│   └── related_info: str | None   関連情報
├── summarization_status: SummarizationStatus
│   SUCCESS / FAILED / TIMEOUT / SKIPPED
└── error_message: str | None

PublishedArticle
├── summarized: SummarizedArticle  元の要約記事
├── issue_number: int | None       作成した Issue 番号
├── issue_url: str | None          Issue URL
├── publication_status: PublicationStatus
│   SUCCESS / FAILED / SKIPPED / DUPLICATE
└── error_message: str | None
```

### WorkflowResult

```
WorkflowResult
├── total_collected: int           収集件数
├── total_extracted: int           抽出成功件数
├── total_summarized: int          要約成功件数
├── total_published: int           公開成功件数
├── total_duplicates: int          重複スキップ件数
├── extraction_failures: list[FailureRecord]
├── summarization_failures: list[FailureRecord]
├── publication_failures: list[FailureRecord]
├── started_at: datetime
├── finished_at: datetime
├── elapsed_seconds: float
├── published_articles: list[PublishedArticle]
└── feed_errors: list[FeedError]
```

結果は `data/exports/news-workflow/workflow-result-{timestamp}.json` に保存される。

---

## 設定ファイル構造

設定ファイル: `data/config/news-collection-config.yaml`

```yaml
version: "1.0"

# カテゴリ → GitHub Status 名マッピング
status_mapping:
  tech: "ai"
  market: "index"
  finance: "finance"
  stock: "stock"
  sector: "sector"
  macro: "macro"

# GitHub Status 名 → Status ID マッピング
github_status_ids:
  index: "3925acc3"
  stock: "f762022e"
  sector: "48762504"
  macro: "730034a5"
  ai: "6fbb43d0"
  finance: "ac4a91b1"

# RSS フィード設定
rss:
  presets_file: "data/config/rss-presets.json"
  retry:
    max_attempts: 3
    initial_delay_seconds: 2.0
    max_delay_seconds: 30.0
    exponential_base: 2.0
    jitter: true

# 記事本文抽出設定
extraction:
  concurrency: 5               # 同時抽出タスク数
  timeout_seconds: 30           # 抽出タイムアウト
  min_body_length: 200          # 最小本文長
  max_retries: 3                # リトライ回数
  user_agent_rotation:
    enabled: true
    user_agents: [...]          # User-Agent ローテーション
  playwright_fallback:
    enabled: true
    browser: "chromium"
    headless: true
    timeout_seconds: 30

# AI 要約設定
summarization:
  concurrency: 3               # 同時要約タスク数
  timeout_seconds: 60           # 要約タイムアウト
  max_retries: 3
  prompt_template: "..."        # プロンプトテンプレート

# GitHub 設定
github:
  project_number: 15
  project_id: "PVT_..."
  status_field_id: "PVTSSF_..."
  published_date_field_id: "PVTF_..."
  repository: "YH-05/quants"
  duplicate_check_days: 7

# フィルタリング設定
filtering:
  max_age_hours: 168            # 最大記事年齢（7 日）

# 出力設定
output:
  result_dir: "data/exports/news-workflow"

# ドメインブロック
blocked_domains:
  - wsj.com
  - reuters.com
  - ft.com
  - bloomberg.com
  - seekingalpha.com
```

### 設定モデル階層

```
NewsWorkflowConfig (ルート)
├── version: str
├── status_mapping: dict[str, str]
├── github_status_ids: dict[str, str]
├── rss: RssConfig
│   ├── presets_file: str
│   └── retry: RssRetryConfig
│       ├── max_attempts: int (=3)
│       ├── initial_delay_seconds: float (=2.0)
│       ├── max_delay_seconds: float (=30.0)
│       ├── exponential_base: float (=2.0)
│       └── jitter: bool (=True)
├── extraction: ExtractionConfig
│   ├── concurrency: int (=5)
│   ├── timeout_seconds: int (=30)
│   ├── min_body_length: int (=200)
│   ├── max_retries: int (=3)
│   ├── user_agent_rotation: UserAgentRotationConfig
│   │   ├── enabled: bool (=True)
│   │   └── user_agents: list[str]
│   └── playwright_fallback: PlaywrightFallbackConfig
│       ├── enabled: bool (=True)
│       ├── browser: str (="chromium")
│       ├── headless: bool (=True)
│       └── timeout_seconds: int (=30)
├── summarization: SummarizationConfig
│   ├── concurrency: int (=3)
│   ├── timeout_seconds: int (=60)
│   ├── max_retries: int (=3)
│   └── prompt_template: str (必須)
├── github: GitHubConfig
│   ├── project_number: int (必須)
│   ├── project_id: str (必須)
│   ├── status_field_id: str (必須)
│   ├── published_date_field_id: str (必須)
│   ├── repository: str (必須)
│   ├── duplicate_check_days: int (=7)
│   └── dry_run: bool (=False)
├── filtering: FilteringConfig
│   └── max_age_hours: int (=168)
├── output: OutputConfig
│   └── result_dir: str (必須)
└── domain_filtering: DomainFilteringConfig
    ├── enabled: bool (=True)
    ├── log_blocked: bool (=True)
    └── blocked_domains: list[str]
```

---

## 外部依存パッケージ

| パッケージ | 用途 | 使用箇所 |
|-----------|------|---------|
| `httpx` | 非同期 HTTP クライアント | RSSCollector（フィード取得） |
| `feedparser` | RSS/Atom フィードパース | rss.core.parser.FeedParser |
| `trafilatura` | 記事本文抽出 | rss.services.article_extractor |
| `lxml` | HTML パース（フォールバック） | rss.services.article_extractor |
| `pydantic` | データバリデーション | 全モデルクラス |
| `PyYAML` | YAML 設定ファイルパース | news.config.models |
| `claude-agent-sdk` | Claude AI 要約生成 | news.summarizer |
| `playwright` | JS レンダリング（フォールバック） | news.extractors.playwright |

### システム依存

| ツール | 用途 |
|--------|------|
| `gh` CLI | GitHub Issue 作成・Project 操作（Publisher） |

---

## ファイル一覧

### エントリポイント

| ファイル | 説明 |
|---------|------|
| `src/news/scripts/finance_news_workflow.py` | ワークフロー CLI（本ファイル） |
| `src/news/scripts/collect.py` | yfinance ベースのニュース収集 CLI（別系統） |
| `src/news/scripts/__main__.py` | `python -m news.scripts.collect` 用エントリ |

### コア

| ファイル | 説明 |
|---------|------|
| `src/news/orchestrator.py` | `NewsWorkflowOrchestrator` - 4 段階パイプライン統合 |
| `src/news/models.py` | 全データモデル定義 |
| `src/news/config/models.py` | 全設定モデル + `load_config()` + `ConfigLoader` |

### パイプラインコンポーネント

| ファイル | クラス | 役割 |
|---------|--------|------|
| `src/news/collectors/rss.py` | `RSSCollector` | RSS フィード収集 |
| `src/news/collectors/base.py` | `BaseCollector` | 収集器の抽象基底クラス |
| `src/news/extractors/trafilatura.py` | `TrafilaturaExtractor` | 記事本文抽出 |
| `src/news/extractors/playwright.py` | `PlaywrightExtractor` | JS ページフォールバック |
| `src/news/extractors/base.py` | `BaseExtractor` | 抽出器の抽象基底クラス |
| `src/news/summarizer.py` | `Summarizer` | Claude AI 要約生成 |
| `src/news/publisher.py` | `Publisher` | GitHub Issue 作成 |

### クロスパッケージ依存

| ファイル | 説明 |
|---------|------|
| `src/rss/core/parser.py` | `FeedParser` - feedparser ラッパー |
| `src/rss/services/article_extractor.py` | `ArticleExtractor` - trafilatura ラッパー |
| `src/rss/types.py` | `FeedItem`, `PresetFeed` 型定義 |
| `src/utils_core/logging/__init__.py` | `get_logger()`, `setup_logging()` |

### 設定ファイル

| ファイル | 説明 |
|---------|------|
| `data/config/news-collection-config.yaml` | ワークフロー設定（メイン） |
| `data/config/rss-presets.json` | RSS フィード定義 |

---

## ステータスマッピングの流れ

記事カテゴリから GitHub Project の Status 設定までの変換フロー:

```
記事の category (ArticleSource.category)
    例: "market"
        ↓
status_mapping で変換
    例: "market" → "index"
        ↓
github_status_ids で Status ID に変換
    例: "index" → "3925acc3"
        ↓
gh project item-edit で Status 設定
```

### --status オプションの指定値

`--status` で指定するのは `status_mapping` の**値**側（= `github_status_ids` のキー側）。

| 指定値 | 対象カテゴリ |
|--------|-------------|
| `index` | market 系フィード |
| `stock` | stock 系フィード |
| `sector` | sector 系フィード |
| `macro` | macro 系フィード |
| `ai` | tech 系フィード |
| `finance` | finance 系フィード |

---

## ログ出力

### コンソール出力

- 通常モード: INFO レベル
- `--verbose`: DEBUG レベル

### ファイル出力

- パス: `logs/news-workflow-{YYYY-MM-DD}.log`
- レベル: 常に DEBUG（障害分析用）

---

## 同フォルダの別スクリプト: collect.py

`collect.py` は `finance_news_workflow.py` とは**別系統**のニュース収集スクリプト。

| 項目 | `finance_news_workflow.py` | `collect.py` |
|------|---------------------------|-------------|
| ソース | RSS フィード | yfinance API |
| 出力先 | GitHub Issue + Project | JSON ファイル |
| AI 要約 | あり (Claude) | なし |
| 設定モデル | `NewsWorkflowConfig` | `NewsConfig` |
| 非同期 | `asyncio.run()` | 同期 |
| 実行方法 | `python -m news.scripts.finance_news_workflow` | `python -m news.scripts.collect` |

---

## エラーハンドリング

### 段階別のエラー処理

| 段階 | エラー時の動作 |
|------|--------------|
| 設定読み込み | `FileNotFoundError` / `ValidationError` → 即座に exit 1 |
| RSS 収集 | フィード単位でエラー記録、他フィードは継続 |
| 本文抽出 | 記事単位でリトライ（最大 3 回）、失敗は `FailureRecord` に記録 |
| AI 要約 | 記事単位でリトライ（最大 3 回）、失敗は `FailureRecord` に記録 |
| Issue 公開 | 記事単位でエラー記録、重複は `DUPLICATE` としてスキップ |

### 失敗サマリー表示

ワークフロー完了後、失敗があれば `print_failure_summary()` が詳細を表示（各段階 5 件まで）。
