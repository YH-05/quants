# 金融ニュース収集ワークフロー Python化計画

## 概要

現在の `/finance-news-workflow` の問題点（WebFetch不安定、要約品質、処理時間）を解決するため、Python CLIベースの新しいニュース収集ワークフローを実装する。

## 現状の問題点

| 問題 | 原因 | 解決策 |
|------|------|--------|
| 記事本文取得が不安定 | WebFetch/Playwrightのタイムアウト | trafilatura（既存実装）を使用 |
| 要約品質にばらつき | エージェント依存 | Claude Agent SDKで構造化要約 |
| 処理時間が長い | 逐次処理・3段階フォールバック | asyncioで並列処理 |

## アーキテクチャ

```
CLI: uv run python -m news.scripts.rss_collect
         │
         ▼
┌─────────────────────────────────────────────────────────┐
│                   RSSNewsCollector                       │
│                src/news/rss/collector.py                 │
└─────────────────────────────────────────────────────────┘
         │
    ┌────┴────┬────────────┬────────────┐
    ▼         ▼            ▼            ▼
┌────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐
│Fetcher │ │Extractor │ │Summarizer│ │GitHubSink│
│(RSS)   │ │(本文抽出)│ │(AI要約)  │ │(Issue)   │
└────────┘ └──────────┘ └──────────┘ └──────────┘
```

## モジュール構成

```
src/news/
├── rss/                          # 新規: RSS収集サブパッケージ
│   ├── __init__.py
│   ├── collector.py              # メインオーケストレーター
│   ├── fetcher.py                # RSS取得（feedparser）
│   ├── extractor.py              # 本文抽出（trafilatura）
│   ├── summarizer.py             # AI要約（Claude Agent SDK）
│   ├── github_sink.py            # Issue作成（gh CLI）
│   ├── models.py                 # Pydanticモデル
│   └── config.py                 # 設定読み込み
│
├── scripts/
│   └── rss_collect.py            # 新規: CLIエントリーポイント
│
└── (既存ファイルは変更なし)
```

## データモデル

### RSSArticle

```python
class RSSArticle(BaseModel):
    url: HttpUrl
    title: str
    published: datetime | None
    summary: str | None  # RSS要約
    feed_source: str
    theme_key: str

    # 処理中に設定
    body_text: str | None = None
    structured_summary: StructuredSummary | None = None
    status: ProcessingStatus = ProcessingStatus.PENDING
    error_message: str | None = None

    # Issue作成後に設定
    issue_number: int | None = None
    issue_url: str | None = None
```

### StructuredSummary（4セクション構造化要約）

```python
class StructuredSummary(BaseModel):
    overview: str        # 概要: 記事の主旨
    key_points: list[str]  # キーポイント: 重要事実
    market_impact: str   # 市場影響: 投資家への示唆
    related_info: str | None  # 関連情報: 背景
```

## 設定ファイル

`data/config/rss-collection-config.yaml`:

```yaml
version: "1.0"

# テーマ設定への参照
themes_config: "data/config/finance-news-themes.json"

# 要約設定
summarization:
  prompt_template: |
    以下の金融ニュース記事を分析し、日本語で構造化された要約を作成してください。

    ## 記事情報
    **タイトル**: {title}
    **ソース**: {source}
    **公開日**: {published}

    **本文**:
    {body}

    ## 出力形式 (JSON)
    {{
      "overview": "記事の主旨を1-2文で要約",
      "key_points": ["重要なポイント1", "重要なポイント2"],
      "market_impact": "投資家・市場への影響",
      "related_info": "関連する背景情報"
    }}

# 処理設定
processing:
  concurrency: 5      # 並列処理数
  timeout_seconds: 60 # タイムアウト

# GitHub設定
github:
  project_number: 15
  repository: "YH-05/quants"
  duplicate_check: true
  dry_run: false

# フィルタリング
filtering:
  max_age_hours: 168  # 7日
  min_body_length: 200
```

## CLI使用方法

```bash
# 基本実行
uv run python -m news.scripts.rss_collect

# 特定テーマのみ
uv run python -m news.scripts.rss_collect --themes index,stock

# ドライラン（Issue作成なし）
uv run python -m news.scripts.rss_collect --dry-run

# カスタム設定
uv run python -m news.scripts.rss_collect --config path/to/config.yaml

# 記事数制限
uv run python -m news.scripts.rss_collect --max-articles 50
```

## データフロー

```
1. RSS Feeds (finance-news-themes.json)
   │ feedparser.parse()
   ▼
2. FeedItem[] (title, link, summary, published)
   │ filter by max_age_hours
   ▼
3. RSSArticle[] (status: PENDING)
   │ trafilatura.extract() [並列: semaphore=5]
   ▼
4. RSSArticle[] (status: EXTRACTED, body_text設定済み)
   │ claude_agent_sdk.query() [並列: semaphore=3]
   ▼
5. RSSArticle[] (status: SUMMARIZED, structured_summary設定済み)
   │ duplicate check (gh issue list)
   ▼
6. RSSArticle[] (重複スキップ済み)
   │ gh issue create
   ▼
7. RSSArticle[] (status: POSTED, issue_number/url設定済み)
   │ gh project item-add + field updates
   ▼
8. CollectionResult (統計情報)
```

## 再利用する既存コード

| コンポーネント | ファイル | 用途 |
|----------------|----------|------|
| FeedParser | `src/rss/core/parser.py` | feedparser統合 |
| ArticleExtractor | `src/rss/services/article_extractor.py` | trafilatura統合 |
| AgentProcessor | `src/news/processors/agent_base.py` | Claude Agent SDK基底クラス |
| GitHubSink | `src/news/sinks/github.py` | Issue作成パターン |
| テスト関数 | `notebook/claude-agent-test.ipynb` | extract_body, summarize_content |

## 実装タスク

### Phase 1: モデルと設定
- [ ] `src/news/rss/__init__.py` 作成
- [ ] `src/news/rss/models.py` 作成（Pydanticモデル）
- [ ] `src/news/rss/config.py` 作成（設定読み込み）
- [ ] `data/config/rss-collection-config.yaml` 作成
- [ ] 単体テスト作成

### Phase 2: RSS取得
- [ ] `src/news/rss/fetcher.py` 作成
- [ ] `rss.core.parser.FeedParser` との統合
- [ ] 日時フィルタリング実装
- [ ] 単体テスト作成

### Phase 3: 本文抽出
- [ ] `src/news/rss/extractor.py` 作成
- [ ] `rss.services.article_extractor.ArticleExtractor` のラッパー
- [ ] セマフォベース並列処理
- [ ] 単体テスト作成

### Phase 4: AI要約
- [ ] `src/news/rss/summarizer.py` 作成
- [ ] Claude Agent SDK統合
- [ ] JSON出力パース・バリデーション
- [ ] リトライロジック
- [ ] 単体テスト作成

### Phase 5: GitHub Sink
- [ ] `src/news/rss/github_sink.py` 作成
- [ ] Issue本文生成（4セクション構造）
- [ ] Project フィールド更新
- [ ] 重複チェック
- [ ] 単体テスト作成

### Phase 6: オーケストレーター
- [ ] `src/news/rss/collector.py` 作成
- [ ] 全コンポーネント統合
- [ ] 進捗ログ
- [ ] 統合テスト作成

### Phase 7: CLI
- [ ] `src/news/scripts/rss_collect.py` 作成
- [ ] 引数パース
- [ ] ログ設定
- [ ] CLIテスト作成

### Phase 8: ドキュメント
- [ ] `src/news/README.md` 更新
- [ ] CLAUDE.md 更新（新コマンド追加）

## 主要ファイル

| ファイル | 説明 |
|----------|------|
| `src/rss/services/article_extractor.py` | trafilatura統合（再利用） |
| `src/news/processors/agent_base.py` | Claude Agent SDKパターン |
| `src/news/sinks/github.py` | GitHub Issue作成パターン |
| `data/config/finance-news-themes.json` | テーマ・フィード設定 |
| `notebook/claude-agent-test.ipynb` | Claude Agent SDK使用例 |

## 検証方法

1. **ドライラン**: `--dry-run` でIssue作成なしで全フロー確認
2. **単体テスト**: 各モジュールのテスト実行 `make test`
3. **統合テスト**: 特定テーマ1つで実際にIssue作成まで確認
4. **全テーマテスト**: 全テーマで実行し、処理時間・成功率を確認
