# news

金融ニュースの自動収集・処理・公開パイプラインを提供するパッケージです。

## 概要

このパッケージは、複数のデータソース（RSS、yfinance）からニュース記事を収集し、
本文抽出・AI要約・GitHub Issue作成までの一連のワークフローを自動化します。

**現在のバージョン:** 0.1.0

## 主要機能

- **ニュース収集**: RSSフィード、yfinance APIからの記事取得
- **本文抽出**: Trafilaturaを使用したWebページからの本文抽出
- **AI要約**: Claude APIを使用した構造化日本語要約生成
- **Issue作成**: GitHub Issue作成とProject追加の自動化
- **重複検出**: URL/タイトルベースの重複記事検出

<!-- AUTO-GENERATED: QUICKSTART -->
## クイックスタート

### インストール

```bash
# このリポジトリのパッケージとして利用
uv sync --all-extras
```

### 基本的な使い方

#### パターン1: ワークフロー全体を実行（最も簡単）

```python
import asyncio
from news.orchestrator import NewsWorkflowOrchestrator
from news.config.models import load_config

# 設定ファイルを読み込む
config = load_config("data/config/news-collection-config.yaml")

# オーケストレーターを作成
orchestrator = NewsWorkflowOrchestrator(config=config)

# ワークフロー実行（収集→抽出→要約→公開）
async def main():
    result = await orchestrator.run(
        statuses=["index"],      # 株価指数関連のニュースのみ
        max_articles=10,         # 最大10件まで処理
        dry_run=False,           # 実際にGitHub Issueを作成
    )
    print(f"収集: {result.total_collected}件")
    print(f"公開: {result.total_published}件")

asyncio.run(main())
```

#### パターン2: CLIで実行（推奨）

```bash
# 基本実行（全ステータス対象）
uv run python -m news.scripts.finance_news_workflow

# ドライラン（GitHub Issue作成をスキップして確認）
uv run python -m news.scripts.finance_news_workflow --dry-run

# 特定カテゴリのみ収集
uv run python -m news.scripts.finance_news_workflow --status index,stock

# 記事数を制限（テスト時に便利）
uv run python -m news.scripts.finance_news_workflow --max-articles 5
```

#### パターン3: 個別コンポーネントを使用

```python
from news.collector import Collector, CollectorConfig
from news.sources.yfinance.index import IndexSource
from news.sinks.file import FileSink, WriteMode

# 収集設定
config = CollectorConfig(max_articles_per_source=10)
collector = Collector(config=config)

# ニュースソースを登録（S&P500とダウ平均）
collector.register_source(IndexSource(symbols=["^GSPC", "^DJI"]))

# 出力先を登録（JSONファイル）
collector.register_sink(FileSink(path="output.json", mode=WriteMode.APPEND))

# 収集実行
result = collector.collect()
print(f"収集した記事数: {result.total_articles}")
```

### よくある使い方

#### ユースケース1: 毎日の市場ニュースを自動収集

```bash
# crontab などで定期実行
0 9 * * * cd /path/to/finance && uv run python -m news.scripts.finance_news_workflow --status index,stock --max-articles 20
```

#### ユースケース2: 特定銘柄のニュースを収集

```python
from news.sources.yfinance.stock import StockSource
from news.sinks.file import FileSink, WriteMode

collector = Collector()
collector.register_source(StockSource(symbols=["AAPL", "MSFT", "GOOGL"]))
collector.register_sink(FileSink(path="mag7_news.json", mode=WriteMode.OVERWRITE))
result = collector.collect()
```

#### ユースケース3: 収集したニュースをAI要約

```python
from news.summarizer import Summarizer
from news.models import ExtractedArticle

# 本文抽出済みの記事
article = ExtractedArticle(...)

# AI要約実行
summarizer = Summarizer(config=config)
summarized = await summarizer.summarize(article)

# 4セクションの構造化要約
print(summarized.summary.key_points)      # 要点
print(summarized.summary.market_impact)   # 市場への影響
print(summarized.summary.investment_perspective)  # 投資視点
print(summarized.summary.related_topics)  # 関連トピック
```

<!-- END: QUICKSTART -->

<!-- AUTO-GENERATED: STRUCTURE -->
## ディレクトリ構成

```
news/
├── __init__.py              # 公開API定義
├── py.typed                 # PEP 561マーカー
├── models.py                # ワークフローモデル
├── types.py                 # 型定義
├── collector.py             # Collector（統合）
├── orchestrator.py          # ワークフローオーケストレーター
├── summarizer.py            # AI要約（Claude API）
├── publisher.py             # GitHub Issue公開
├── grouper.py               # カテゴリ別記事グルーピング
├── markdown_generator.py    # カテゴリ別Markdown生成・エクスポート
│
├── core/                    # コアコンポーネント
│   ├── article.py           # 統一記事モデル
│   ├── result.py            # 結果・設定モデル
│   ├── sink.py              # Sinkプロトコル
│   ├── source.py            # Sourceプロトコル
│   ├── processor.py         # Processorプロトコル
│   ├── dedup.py             # 重複検出
│   ├── history.py           # 履歴管理
│   └── errors.py            # 例外クラス
│
├── collectors/              # 収集
│   ├── base.py              # BaseCollector
│   └── rss.py               # RSSCollector
│
├── sources/                 # データソース
│   └── yfinance/            # yfinance統合
│       ├── base.py          # 基底クラス
│       ├── index.py         # 株価指数
│       ├── stock.py         # 個別銘柄
│       ├── sector.py        # セクター
│       ├── macro.py         # マクロ経済
│       ├── commodity.py     # 商品
│       └── search.py        # 検索
│
├── extractors/              # 本文抽出
│   ├── base.py              # Extractorプロトコル
│   ├── trafilatura.py       # Trafilatura抽出
│   └── playwright.py        # Playwrightフォールバック
│
├── processors/              # 記事処理
│   ├── classifier.py        # カテゴリ分類
│   ├── summarizer.py        # 要約処理
│   ├── pipeline.py          # パイプライン統合
│   └── agent_base.py        # エージェントベース
│
├── sinks/                   # 出力先
│   ├── file.py              # JSON/CSVファイル
│   └── github.py            # GitHub Issue
│
├── config/                  # 設定管理
│   ├── __init__.py          # 公開API
│   └── models.py            # 設定モデル
│
├── scripts/                 # CLIスクリプト
│   ├── __main__.py          # エントリーポイント
│   ├── collect.py           # 収集コマンド
│   └── finance_news_workflow.py  # ワークフローCLI
│
└── utils/                   # ユーティリティ
    └── logging_config.py    # 構造化ロギング
```

<!-- END: STRUCTURE -->

<!-- AUTO-GENERATED: IMPLEMENTATION -->
## 実装状況

| モジュール | 状態 | ファイル数 | 行数 |
|-----------|------|-----------|------|
| `core/` | ✅ 実装済み | 8 | 1,245 |
| `collectors/` | ✅ 実装済み | 3 | 387 |
| `sources/yfinance/` | ✅ 実装済み | 7 | 1,523 |
| `extractors/` | ✅ 実装済み | 4 | 1,089 |
| `processors/` | ✅ 実装済み | 5 | 892 |
| `sinks/` | ✅ 実装済み | 3 | 678 |
| `config/` | ✅ 実装済み | 2 | 534 |
| `scripts/` | ✅ 実装済み | 4 | 456 |
| `utils/` | ✅ 実装済み | 1 | 89 |
| トップレベル | ✅ 実装済み | 5 | 2,157 |

### 主要コンポーネント

#### コアモデル (`core/`)
- **article.py**: 統一記事モデル（Article, ArticleSource, ContentType）
- **result.py**: 結果・設定モデル（FetchResult, RetryConfig）
- **sink.py / source.py**: プロトコル定義
- **dedup.py**: URL/タイトルベース重複検出
- **history.py**: 履歴管理

#### データ収集 (`collectors/`, `sources/`)
- **collectors/rss.py**: RSSフィード収集
- **sources/yfinance/**: yfinance統合（6種類のソース）
  - index, stock, sector, macro, commodity, search

#### 本文抽出 (`extractors/`)
- **trafilatura.py**: Trafilatura本文抽出
- **playwright.py**: Playwrightフォールバック（JS実行後DOM取得）

#### 出力 (`sinks/`)
- **file.py**: JSON/CSV出力
- **github.py**: GitHub Issue作成・Project追加

#### ワークフロー統合
- **orchestrator.py**: 完全ワークフロー統合（per_category: 収集→抽出→要約→グループ化→エクスポート→公開、per_article: 収集→抽出→要約→公開）
- **summarizer.py**: Claude AI要約
- **publisher.py**: GitHub Issue/Project管理（記事別・カテゴリ別の両方に対応）
- **grouper.py**: カテゴリ別記事グルーピング（ステータスマッピングに基づく分類）
- **markdown_generator.py**: カテゴリ別Markdownファイル生成・エクスポート

<!-- END: IMPLEMENTATION -->

<!-- AUTO-GENERATED: API -->
## 公開API

### クイックスタート（初めての方向け）

パッケージの最も基本的な使い方:

```python
from news.orchestrator import NewsWorkflowOrchestrator
from news.config.models import load_config

# 設定を読み込む
config = load_config("data/config/news-collection-config.yaml")

# ワークフロー実行（収集→抽出→要約→公開の全工程）
orchestrator = NewsWorkflowOrchestrator(config=config)
result = await orchestrator.run()
print(f"収集: {result.total_collected}件, 公開: {result.total_published}件")
```

---

### 主要クラス

#### `NewsWorkflowOrchestrator`

**説明**: ニュース収集の全工程（収集→本文抽出→AI要約→GitHub Issue公開）を統合実行するオーケストレーター

**基本的な使い方**:

```python
from news.orchestrator import NewsWorkflowOrchestrator
from news.config.models import load_config

# 設定ファイルから初期化
config = load_config("data/config/news-collection-config.yaml")
orchestrator = NewsWorkflowOrchestrator(config=config)

# ワークフロー実行
result = await orchestrator.run(
    statuses=["index", "stock"],  # 対象カテゴリ
    max_articles=10,              # 最大処理数
    dry_run=False,                # 実行モード
)
```

**主なメソッド**:

| メソッド | 説明 | 戻り値 |
|---------|------|--------|
| `run(statuses, max_articles, dry_run, export_only)` | ワークフロー全体を実行 | `WorkflowResult` |

**`run()` パラメータ**:

| パラメータ | 型 | 説明 | デフォルト |
|-----------|-----|------|-----------|
| `statuses` | `list[str] \| None` | フィルタ対象ステータス | `None`（全て） |
| `max_articles` | `int \| None` | 最大処理記事数 | `None`（無制限） |
| `dry_run` | `bool` | Issue作成をスキップ | `False` |
| `export_only` | `bool` | Markdownエクスポートのみ（per_category時） | `False` |

---

#### `Collector`

**説明**: 複数のニュースソースから記事を収集し、複数の出力先に書き込むコレクター

**基本的な使い方**:

```python
from news.collector import Collector, CollectorConfig
from news.sources.yfinance.index import IndexSource
from news.sinks.file import FileSink, WriteMode

# 初期化
config = CollectorConfig(max_articles_per_source=10)
collector = Collector(config=config)

# ソース・シンクを登録
collector.register_source(IndexSource(symbols=["^GSPC", "^DJI"]))
collector.register_sink(FileSink(path="output.json", mode=WriteMode.APPEND))

# 収集実行
result = collector.collect()
```

**主なメソッド**:

| メソッド | 説明 | 戻り値 |
|---------|------|--------|
| `register_source(source)` | ニュースソースを登録 | `None` |
| `register_sink(sink)` | 出力先を登録 | `None` |
| `collect()` | 収集を実行 | `FetchResult` |

---

#### `Summarizer`

**説明**: 記事本文をClaude APIで構造化日本語要約（要点・市場影響・投資視点・関連トピック）に変換

**基本的な使い方**:

```python
from news.summarizer import Summarizer
from news.config.models import load_config

# 設定から初期化
config = load_config("data/config/news-collection-config.yaml")
summarizer = Summarizer(config=config)

# 要約実行（ExtractedArticleを入力）
summarized = await summarizer.summarize(extracted_article)

# 4セクション構造化要約にアクセス
print(summarized.summary.key_points)      # 要点
print(summarized.summary.market_impact)   # 市場への影響
```

**主なメソッド**:

| メソッド | 説明 | 戻り値 |
|---------|------|--------|
| `summarize(article)` | 記事を要約 | `SummarizedArticle` |
| `summarize_batch(articles, concurrency)` | 複数記事を並列要約 | `list[SummarizedArticle]` |

---

#### `Publisher`

**説明**: 要約済み記事をGitHub Issueとして作成し、Projectに追加

**基本的な使い方**:

```python
from news.publisher import Publisher
from news.config.models import load_config

# 設定から初期化
config = load_config("data/config/news-collection-config.yaml")
publisher = Publisher(config=config)

# GitHub Issue作成
published = await publisher.publish(summarized_article)
print(f"Issue作成: {published.github_issue_url}")
```

**主なメソッド**:

| メソッド | 説明 | 戻り値 |
|---------|------|--------|
| `publish(article)` | Issue作成・Project追加 | `PublishedArticle` |
| `publish_batch(articles, concurrency)` | 複数記事を並列公開 | `list[PublishedArticle]` |

---

### データソース

#### yfinanceソース

```python
from news.sources.yfinance import (
    IndexSource,      # 株価指数ニュース
    StockSource,      # 個別銘柄ニュース
    SectorSource,     # セクターニュース
    MacroSource,      # マクロ経済ニュース
    CommoditySource,  # 商品ニュース
    SearchSource,     # キーワード検索ニュース
)

# 株価指数ニュース取得
source = IndexSource(symbols=["^GSPC", "^DJI", "^IXIC"])
result = source.fetch()
```

#### RSSコレクター

```python
from news.collectors.rss import RSSCollector

collector = RSSCollector()
articles = await collector.collect_from_feeds(
    feed_urls=["https://www.cnbc.com/id/100003114/device/rss/rss.html"]
)
```

---

### コアモデル

ニュース記事の統一データ構造:

```python
from news import (
    Article,         # 統一記事モデル
    ArticleSource,   # ソース種別（YFINANCE_TICKER, YFINANCE_SEARCH, RSS, SCRAPER）
    ContentType,     # コンテンツ種別（ARTICLE, VIDEO, PRESS_RELEASE, UNKNOWN）
    FetchResult,     # 収集結果
    RetryConfig,     # リトライ設定
)
```

---

### 出力先（Sink）

```python
from news.sinks import (
    FileSink,        # JSON/CSVファイル出力
    WriteMode,       # 書き込みモード（OVERWRITE, APPEND）
    GitHubSink,      # GitHub Issue出力
)

# JSON出力
sink = FileSink(path="output.json", mode=WriteMode.APPEND)
sink.write([article1, article2])
```

---

### ワークフローモデル

処理フェーズごとのモデル:

```python
from news.models import (
    CollectedArticle,        # 収集済み記事
    ExtractedArticle,        # 本文抽出済み記事
    SummarizedArticle,       # 要約済み記事
    PublishedArticle,        # 公開済み記事（per_article形式）
    CategoryGroup,           # カテゴリ別グループ（per_category形式）
    CategoryPublishResult,   # カテゴリ別公開結果（per_category形式）
    WorkflowResult,          # ワークフロー全体結果
    StructuredSummary,       # 構造化要約（4セクション）
    StageMetrics,            # ステージ別処理時間
    DomainExtractionRate,    # ドメイン別抽出成功率
)
```

---

### 設定管理

```python
from news.config.models import (
    load_config,             # YAML設定ファイル読み込み
    NewsWorkflowConfig,      # ワークフロー設定
)

# 設定読み込み
config = load_config("data/config/news-collection-config.yaml")
```

---

### ユーティリティ

```python
from news import get_logger

# 構造化ロギング
logger = get_logger(__name__)
logger.info("記事収集開始", article_count=10)
```

<!-- END: API -->

<!-- AUTO-GENERATED: STATS -->
## モジュール統計

| 項目 | 値 |
|------|-----|
| Pythonファイル数 | 47 |
| 総行数（実装コード） | 16,150 |
| モジュール数 | 10 |
| テストファイル数 | 40 |
| テストカバレッジ | N/A |

### パッケージ構成

- **コアコンポーネント**: 8モジュール（記事モデル、プロトコル定義、重複検出）
- **データ収集**: 10モジュール（RSS、yfinance統合）
- **本文抽出**: 3モジュール（Trafilatura、Playwrightフォールバック）
- **出力先**: 2モジュール（JSON/CSV、GitHub Issue）
- **ワークフロー統合**: 5モジュール（オーケストレーター、要約、公開）
- **設定管理**: 2モジュール（YAML設定読み込み）
- **CLI**: 3モジュール（収集コマンド、ワークフローCLI）

<!-- END: STATS -->

## 詳細な使用例

### CLI実行

#### 基本的な使い方

```bash
# 最もシンプルな実行（全カテゴリ対象）
uv run python -m news.scripts.finance_news_workflow

# ドライラン（GitHub Issue作成をスキップして確認）
uv run python -m news.scripts.finance_news_workflow --dry-run

# 特定カテゴリのみ収集
uv run python -m news.scripts.finance_news_workflow --status index,stock

# 記事数を制限（テスト時に便利）
uv run python -m news.scripts.finance_news_workflow --max-articles 10

# 詳細ログ出力
uv run python -m news.scripts.finance_news_workflow --verbose

# 設定ファイル指定
uv run python -m news.scripts.finance_news_workflow \
    --config data/config/news-collection-config.yaml
```

#### CLIオプション一覧

| オプション | 説明 | デフォルト |
|-----------|------|-----------|
| `--config` | 設定ファイルパス | `data/config/news-collection-config.yaml` |
| `--dry-run` | Issue作成をスキップ | False |
| `--status` | フィルタ対象ステータス（カンマ区切り） | 全て |
| `--max-articles` | 処理する最大記事数 | 無制限 |
| `--verbose`, `-v` | DEBUGレベルログ出力 | False |

#### 出力先

- **コンソール**: 処理結果サマリー（収集数、抽出数、要約数、公開数、重複数、経過時間）
- **ログファイル**: `logs/news-workflow-{日付}.log`
- **結果JSON**: `data/exports/news-workflow/workflow-result-{timestamp}.json`
- **GitHub**: Project #15 にIssueとして投稿

---

### プログラムから使用

#### パターン1: 完全ワークフロー実行

```python
import asyncio
from news.orchestrator import NewsWorkflowOrchestrator
from news.config.models import load_config

async def main():
    # 設定ロード
    config = load_config("data/config/news-collection-config.yaml")

    # オーケストレーター作成
    orchestrator = NewsWorkflowOrchestrator(config=config)

    # ワークフロー実行（収集→抽出→要約→公開）
    result = await orchestrator.run(
        statuses=["index"],      # 株価指数関連のみ
        max_articles=10,         # 最大10件
        dry_run=False,           # 実際にIssue作成
    )

    # 結果確認
    print(f"収集: {result.total_collected}件")
    print(f"本文抽出成功: {result.total_extracted}件")
    print(f"AI要約成功: {result.total_summarized}件")
    print(f"GitHub Issue公開: {result.total_published}件")
    print(f"重複スキップ: {result.total_duplicates}件")

asyncio.run(main())
```

#### パターン2: 個別コンポーネント組み合わせ

```python
from news.collector import Collector, CollectorConfig
from news.sources.yfinance.index import IndexSource
from news.sources.yfinance.stock import StockSource
from news.sinks.file import FileSink, WriteMode

# コレクター初期化
config = CollectorConfig(
    max_articles_per_source=10,
    continue_on_source_error=True,
)
collector = Collector(config=config)

# 複数ソースを登録
collector.register_source(IndexSource(symbols=["^GSPC", "^DJI"]))
collector.register_source(StockSource(symbols=["AAPL", "MSFT", "GOOGL"]))

# 複数出力先を登録
collector.register_sink(FileSink(path="market_news.json", mode=WriteMode.OVERWRITE))
collector.register_sink(FileSink(path="archive/news.jsonl", mode=WriteMode.APPEND))

# 収集実行
result = collector.collect()
print(f"収集成功: {result.total_articles}件")
print(f"エラー: {len(result.errors)}件")
```

#### パターン3: AI要約のみ実行

```python
from news.summarizer import Summarizer
from news.models import ExtractedArticle
from news.config.models import load_config

async def summarize_article():
    # 設定読み込み
    config = load_config("data/config/news-collection-config.yaml")

    # 本文抽出済みの記事（既存データから）
    article = ExtractedArticle(
        url="https://example.com/article",
        title="記事タイトル",
        body="記事本文...",
        status="index",
        # ... その他のフィールド
    )

    # AI要約実行
    summarizer = Summarizer(config=config)
    summarized = await summarizer.summarize(article)

    # 4セクション構造化要約を取得
    print("【要点】")
    print(summarized.summary.key_points)

    print("\n【市場への影響】")
    print(summarized.summary.market_impact)

    print("\n【投資視点】")
    print(summarized.summary.investment_perspective)

    print("\n【関連トピック】")
    print(summarized.summary.related_topics)

asyncio.run(summarize_article())
```

#### パターン4: バッチ処理（並列実行）

```python
from news.summarizer import Summarizer
from news.config.models import load_config

async def batch_summarize():
    config = load_config("data/config/news-collection-config.yaml")
    summarizer = Summarizer(config=config)

    # 複数記事を並列要約（並列度3）
    articles = [...]  # ExtractedArticleのリスト
    summarized_list = await summarizer.summarize_batch(
        articles=articles,
        concurrency=3,  # 同時実行数
    )

    print(f"要約完了: {len(summarized_list)}件")

asyncio.run(batch_summarize())
```

## ワークフローパイプライン

2つの公開形式に対応しています。

### per_category 形式（デフォルト・推奨）

カテゴリ別にグループ化し、1つのGitHub Issueにまとめて公開します。

```
┌──────────────┐    ┌──────────────┐    ┌──────────────┐
│  Collector   │ -> │  Extractor   │ -> │  Summarizer  │
│  (RSS収集)   │    │  (本文抽出)  │    │  (AI要約)    │
└──────────────┘    └──────────────┘    └──────────────┘
     |                    |                    |
     v                    v                    v
 CollectedArticle   ExtractedArticle   SummarizedArticle
                                             |
                    ┌────────────────────────┘
                    v
            ┌──────────────┐    ┌──────────────┐    ┌──────────────┐
            │   Grouper    │ -> │   Exporter   │ -> │  Publisher   │
            │ (カテゴリ分類)│    │ (Markdown出力)│    │ (Issue作成)  │
            └──────────────┘    └──────────────┘    └──────────────┘
                    |                    |                    |
                    v                    v                    v
             CategoryGroup        Markdownファイル    CategoryPublishResult
```

**ステージ構成**: 収集 -> 抽出 -> 要約 -> グループ化 -> エクスポート -> 公開（6ステージ）

### per_article 形式（レガシー）

記事単位で個別にGitHub Issueを作成します。

```
┌──────────────┐    ┌──────────────┐    ┌──────────────┐    ┌──────────────┐
│  Collector   │ -> │  Extractor   │ -> │  Summarizer  │ -> │  Publisher   │
│  (RSS収集)   │    │  (本文抽出)  │    │  (AI要約)    │    │  (Issue作成) │
└──────────────┘    └──────────────┘    └──────────────┘    └──────────────┘
     |                    |                    |                    |
     v                    v                    v                    v
 CollectedArticle   ExtractedArticle   SummarizedArticle   PublishedArticle
```

**ステージ構成**: 収集 -> 抽出 -> 要約 -> 公開（4ステージ）

### 公開形式の選択

```yaml
# data/config/news-collection-config.yaml
publishing:
  format: "per_category"   # "per_category"（推奨）または "per_article"
  export_markdown: true     # Markdownファイルのエクスポート（per_categoryのみ）
  export_dir: "data/exports/news-workflow"  # エクスポート先ディレクトリ
```

### 実行モード

| モード | 説明 | 対象形式 |
|--------|------|----------|
| 通常 | 全パイプラインを実行しIssueを作成 | 両方 |
| `dry_run=True` | Issue作成をスキップ（確認用） | 両方 |
| `export_only=True` | Markdownエクスポートのみ、Issue作成なし | per_category |

### カテゴリラベル設定

per_category形式で使用するカテゴリの日本語ラベルを設定できます。

```yaml
# data/config/news-collection-config.yaml
category_labels:
  index: "株価指数"    # デフォルト
  stock: "個別銘柄"
  sector: "セクター"
  macro: "マクロ経済"
  ai: "AI関連"
  finance: "金融"
```

### ステータスマッピング

RSS記事のカテゴリからGitHub Projectのステータスに変換するマッピング:

```yaml
# data/config/news-collection-config.yaml
status_mapping:
  market: "index"     # market カテゴリ -> index ステータス
  tech: "ai"          # tech カテゴリ -> ai ステータス
  finance: "finance"
  sector: "sector"
```

## 設定ファイル

`data/config/news-collection-config.yaml`:

```yaml
feeds:
  - name: "CNBC Markets"
    url: "https://www.cnbc.com/id/100003114/device/rss/rss.html"
    category: "index"

filtering:
  max_age_hours: 72

extraction:
  min_body_length: 100
  max_retries: 3
  timeout_seconds: 30
  concurrency: 5

summarization:
  concurrency: 3
  prompt_template: |
    以下のニュース記事を日本語で要約してください。
    ...

github:
  repo: "YH-05/quants"
  project_id: "PVT_xxx"
  project_number: 15
```

## 信頼性向上機能 (Phase 10)

Phase 10で追加された信頼性向上機能により、ニュース収集の成功率が大幅に向上しました。

### ドメインブロックリスト

ペイウォールやボット検出を行うサイトを自動的にスキップ:

```yaml
# data/config/news-collection-config.yaml
blocked_domains:
  - seekingalpha.com  # ボット検出
  - wsj.com           # ペイウォール
  - reuters.com       # ペイウォール
  - ft.com            # ペイウォール
  - bloomberg.com     # ペイウォール
```

### User-Agentローテーション

複数のUser-Agentをランダムに使用してボット検出を回避:

```yaml
extraction:
  user_agent_rotation:
    enabled: true
    user_agents:
      - "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36..."
      - "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)..."
```

### Playwrightフォールバック

trafilatura失敗時にPlaywrightでJS実行後のDOMから再取得:

```yaml
extraction:
  playwright_fallback:
    enabled: true
    browser: chromium  # chromium, firefox, webkit
    headless: true
    timeout_seconds: 30
```

### ログ出力

障害分析のための詳細なログ機能:

- **コンソール**: INFO（`--verbose` でDEBUG）
- **ファイル**: 常にDEBUG（詳細な障害分析用）
- **出力先**: `logs/news-workflow-{date}.log`

### 結果JSON保存

ワークフロー実行結果は常にJSON形式で保存されます（処理対象の記事がない場合も含む）:

- **出力先**: `data/exports/news-workflow/workflow-result-{timestamp}.json`

## 依存関係

### パッケージ依存

- `rss` パッケージ: RSSフィード処理
- `database` パッケージ: ロギング設定

### 外部ライブラリ

- `pydantic`: データバリデーション
- `trafilatura`: 本文抽出
- `anthropic`: Claude API
- `httpx`: HTTP クライアント
- `playwright`: Playwrightフォールバック（オプション）

## 関連ドキュメント

- `data/config/news-collection-config.yaml` - 設定例
- `docs/project/project-29/` - 実装仕様
- `docs/project/project-27/` - Phase 10 ワークフロー信頼性向上計画
- `.claude/skills/finance-news-workflow/` - ワークフロースキル
