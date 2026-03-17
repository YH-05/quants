---
name: ai-research-workflow
description: AI投資バリューチェーン収集ワークフロー。Python CLI前処理（ティアベーススクレイピング）→AI投資視点要約 + Issue一括作成→結果集約 + スクレイピング統計レポート。10カテゴリ77社対応。
allowed-tools: Read, Bash, Task
---

# AI投資バリューチェーン収集ワークフロー

AIバリューチェーン全体（LLM開発、GPU、データセンター、電力、ロボティクス、SaaS等）の企業ブログ/リリースを自動収集し、投資視点で要約してGitHub Project #44に投稿するワークフロースキル。

## 処理時間目標

| 指標 | 目標 | 根拠 |
|------|------|------|
| 全カテゴリ合計 | 10分以内 | 77社・ティアベース取得のため金融ニュースより長い |
| Phase 1（Python前処理） | 3分以内 | Tier 2スクレイピング含む（ネットワークI/Oあり） |
| Phase 2（Issue一括作成） | 6分以内 | 10カテゴリ並列、各カテゴリ最大10件 |
| Phase 3（結果報告） | 1分以内 | 集約・統計レポート・表示のみ |

## アーキテクチャ

```
/ai-research-collect (このスキル = オーケストレーター)
  |
  +-- Phase 1: Python CLI前処理（3分以内）
  |     +-- prepare_ai_research_session.py
  |           +-- ai-research-companies.json 読み込み（77社定義）
  |           +-- ティアベース取得ルーティング:
  |           |   +-- Tier 1: FeedReader -> RSS対応企業（8社）
  |           |   +-- Tier 2: RobustScraper -> 汎用スクレイピング（64社）
  |           |   +-- Tier 3: CompanyScraperRegistry -> 企業別アダプタ（5社）
  |           +-- ArticleData統一形式に変換
  |           +-- 既存Issue URL抽出（重複チェック用）
  |           +-- 日付フィルタリング -> 重複チェック -> Top-N選択
  |           +-- カテゴリ別JSONファイル出力（.tmp/ai-research-batches/）
  |           +-- スクレイピング統計出力
  |
  +-- Phase 2: ai-research-article-fetcher 並列呼び出し（6分以内）
  |     +-- 投資視点4セクション要約生成（概要/技術的意義/市場影響/投資示唆）
  |     +-- 市場影響度判定（low/medium/high）+ 関連銘柄タグ付け
  |     +-- Issue作成（gh issue create + close）
  |     +-- ラベル付与（ai-research + カテゴリラベル + needs-review）
  |     +-- GitHub Project #44追加 + Category/Status/Date/Impact/Tickers設定
  |     +-- 10カテゴリを1メッセージで並列呼び出し
  |
  +-- Phase 3: 結果集約 + スクレイピング統計レポート（1分以内）
        +-- カテゴリ別統計
        +-- ティア別成功率
        +-- スクレイピング統計サマリー
```

### finance-news-workflow との比較

| 項目 | finance-news-workflow | ai-research-workflow |
|------|----------------------|---------------------|
| 対象 | 金融ニュース（RSSフィード） | AI企業ブログ/リリース（77社） |
| テーマ/カテゴリ | 11テーマ（フィード割当） | 10カテゴリ（企業定義マスタ） |
| 取得方式 | RSS MCP一括 | ティアベース（RSS/汎用/アダプタ） |
| 本文取得 | RSS要約ベース（高速） | スクレイピング済み本文（Python側） |
| 要約視点 | 一般金融4セクション | 投資視点4セクション |
| GitHub Project | #15 | #44 |
| 追加フィールド | なし | Category, Impact Level, Tickers |
| 処理時間目標 | 5分以内 | 10分以内 |

### Python -> AI 役割分担

| Python側（決定論的） | AI側（高度判断） |
|---------------------|-----------------|
| RSS/Webスクレイピング（77社） | タイトル翻訳（英->日） |
| ティア別取得ルーティング | 投資視点4セクション要約生成 |
| 日付フィルタリング | 市場影響度判定（low/medium/high） |
| URLベース重複チェック | 関連銘柄・セクターの特定 |
| Top-N選択（公開日時降順） | Status自動判定 |
| カテゴリ別JSON出力 | Issue本文の文章構成 |
| スクレイピング統計レポート | |
| 構造化ログ出力 | |

## 使用方法

```bash
# 標準実行（デフォルト: 過去7日間、各カテゴリ最新10件）
/ai-research-collect

# オプション付き
/ai-research-collect --days 3 --categories "ai_llm,gpu_chips" --top-n 5

# 特定カテゴリのみ
/ai-research-collect --categories "ai_llm"
```

## Phase 1: Python CLI前処理

### ステップ1.1: 環境確認

```bash
# 企業定義マスタ確認
test -f data/config/ai-research-companies.json

# GitHub CLI 確認
gh auth status
```

### ステップ1.2: Python CLI実行 + カテゴリ別JSON出力

```bash
# 1. セッションファイル作成（ティアベーススクレイピング含む）
uv run python scripts/prepare_ai_research_session.py --days ${days} --top-n ${top_n}

# 2. カテゴリ別JSONファイル作成
python3 << 'EOF'
import json
from pathlib import Path

# 最新のセッションファイルを取得
tmp_dir = Path(".tmp")
session_files = sorted(tmp_dir.glob("ai-research-*.json"), reverse=True)
session_file = session_files[0]
session = json.load(open(session_file))

output_dir = Path(".tmp/ai-research-batches")
output_dir.mkdir(exist_ok=True)

config = session["config"]

for category_key, category_data in session["categories"].items():
    articles = category_data["articles"]
    category_config = category_data["category_config"]
    investment_context = category_data.get("investment_context", {})

    issue_config = {
        "category_key": category_key,
        "category_label": category_config["label"],
        "category_label_gh": category_config["github_label"],
        "status_option_id": category_config.get("default_status_option_id", "2c19ca36"),
        "project_id": config["project_id"],
        "project_number": config["project_number"],
        "project_owner": config["project_owner"],
        "repo": "YH-05/quants",
        "status_field_id": config["status_field_id"],
        "published_date_field_id": config["published_date_field_id"],
        "category_field_id": config["category_field_id"],
        "impact_level_field_id": config["impact_level_field_id"],
        "tickers_field_id": config["tickers_field_id"]
    }

    output_file = output_dir / f"{category_key}.json"
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump({
            "articles": articles,
            "issue_config": issue_config,
            "investment_context": investment_context
        }, f, ensure_ascii=False, indent=2)

    print(f"{category_key}: {len(articles)} articles -> {output_file}")
EOF
```

**出力ファイル形式**（各カテゴリ）:

```json
{
  "articles": [
    {
      "url": "https://openai.com/news/...",
      "title": "Introducing GPT-5",
      "text": "We are excited to announce...",
      "company_key": "openai",
      "company_name": "OpenAI",
      "category": "ai_llm",
      "source_type": "blog",
      "pdf_url": null,
      "published": "2026-02-10T12:00:00+00:00"
    }
  ],
  "issue_config": {
    "category_key": "ai_llm",
    "category_label": "AI/LLM開発",
    "category_label_gh": "ai-llm",
    "status_option_id": "2c19ca36",
    "project_id": "PVT_kwHOBoK6AM4BO4gx",
    "project_number": 44,
    "project_owner": "YH-05",
    "repo": "YH-05/quants",
    "status_field_id": "PVTSSF_lAHOBoK6AM4BO4gxzg9dFiA",
    "published_date_field_id": "PVTF_lAHOBoK6AM4BO4gxzg9dHCA",
    "category_field_id": "PVTSSF_lAHOBoK6AM4BO4gxzg9dHB8",
    "impact_level_field_id": "PVTSSF_lAHOBoK6AM4BO4gxzg9dHCI",
    "tickers_field_id": "PVTF_lAHOBoK6AM4BO4gxzg9dHCE"
  },
  "investment_context": {
    "category_key": "ai_llm",
    "category_label": "AI/LLM開発",
    "focus_areas": ["モデル性能", "API価格", "市場シェア", "提携・投資"],
    "key_tickers": ["MSFT", "GOOGL", "META", "AMZN"]
  }
}
```

## Phase 2: ai-research-article-fetcher 並列呼び出し

### ステップ2.1: 全カテゴリを並列で呼び出し

**重要**: 10カテゴリ全てを**1つのメッセージ内で並列呼び出し**すること。

```python
# 10カテゴリを並列で呼び出し（1メッセージに10個のTask呼び出し）
categories = [
    "ai_llm", "gpu_chips", "semiconductor_equipment",
    "data_center", "networking", "power_energy",
    "nuclear_fusion", "physical_ai", "saas", "ai_infra"
]

# 各カテゴリのJSONファイルを読み込み、ai-research-article-fetcherに渡す
for category in categories:
    json_file = f".tmp/ai-research-batches/{category}.json"
    data = json.load(open(json_file))

    if not data["articles"]:
        # 記事が0件のカテゴリはスキップ
        continue

    Task(
        subagent_type="ai-research-article-fetcher",
        description=f"{category}: {len(data['articles'])}件の記事処理",
        prompt=f"""以下の記事データを投資視点で処理してください。

```json
{json.dumps(data, ensure_ascii=False, indent=2)}
```

処理手順:
1. 各記事の本文（textフィールド）を読み取り
2. タイトルを日本語に翻訳
3. 投資視点4セクション要約を生成（概要/技術的意義/市場影響/投資示唆）
4. 市場影響度を判定（low/medium/high）
5. 関連銘柄をタグ付け
6. Issue作成 + close -> Project追加 -> Category/Status/Date/Impact/Tickers設定

JSON形式で結果を返してください。""",
        run_in_background=True  # バックグラウンド実行
    )
```

### ステップ2.2: 完了待ち

全エージェントの完了を待ち、結果を集約:

```python
# TaskOutputで各エージェントの結果を取得
results = {}
for category in categories:
    result = TaskOutput(task_id=agent_ids[category], block=True, timeout=300000)
    results[category] = parse_result(result)
```

## Phase 3: 結果集約 + スクレイピング統計レポート

### サマリー出力形式

テンプレート: `.claude/skills/ai-research-workflow/templates/summary-template.md` を参照。

カテゴリ別統計に加え、ティア別のスクレイピング成功率レポートを含む。

## パラメータ一覧

| パラメータ | デフォルト | 説明 |
|-----------|-----------|------|
| --days | 7 | 過去何日分の記事を対象とするか |
| --categories | all | 対象カテゴリ（ai_llm,gpu_chips,... / all） |
| --top-n | 10 | 各カテゴリの最大記事数（公開日時の新しい順） |

## カテゴリ一覧

| カテゴリキー | 日本語名 | 対象企業数 | ティア内訳 |
|------------|----------|-----------|-----------|
| ai_llm | AI/LLM開発 | 11社 | RSS:2, 汎用:8, アダプタ:1 |
| gpu_chips | GPU・演算チップ | 10社 | RSS:1, 汎用:7, アダプタ:2 |
| semiconductor_equipment | 半導体製造装置 | 6社 | RSS:0, 汎用:6, アダプタ:0 |
| data_center | データセンター・クラウド | 7社 | RSS:0, 汎用:6, アダプタ:1 |
| networking | ネットワーキング | 2社 | RSS:1, 汎用:1, アダプタ:0 |
| power_energy | 電力・エネルギー | 7社 | RSS:3, 汎用:4, アダプタ:0 |
| nuclear_fusion | 原子力・核融合 | 8社 | RSS:0, 汎用:8, アダプタ:0 |
| physical_ai | フィジカルAI・ロボティクス | 9社 | RSS:1, 汎用:7, アダプタ:1 |
| saas | SaaS・AI活用ソフトウェア | 10社 | RSS:0, 汎用:10, アダプタ:0 |
| ai_infra | AI基盤・MLOps | 7社 | RSS:0, 汎用:7, アダプタ:0 |

## ティアベース・スクレイピング戦略

| ティア | 対象企業数 | 方式 | 特徴 |
|--------|-----------|------|------|
| Tier 1: RSS | 8社 | FeedReader | アダプタ不要、最も安定・高速 |
| Tier 2: 汎用 | 64社 | RobustScraper + trafilatura | UA+レートリミット+429リトライ+3段階フォールバック |
| Tier 3: アダプタ | 5社 | BaseCompanyScraper継承 | SPA/JS-heavy等の特殊サイト専用 |

## 関連リソース

| リソース | パス |
|---------|------|
| Python CLI前処理 | `scripts/prepare_ai_research_session.py` |
| 企業定義マスタ | `data/config/ai-research-companies.json` |
| ai-research-article-fetcher | `.claude/agents/ai-research-article-fetcher.md` |
| RobustScraper | `src/rss/services/company_scrapers/robust_scraper.py` |
| BaseCompanyScraper | `src/rss/services/company_scrapers/base.py` |
| CompanyScraperRegistry | `src/rss/services/company_scrapers/registry.py` |
| GitHub Project #44 | https://github.com/users/YH-05/projects/44 |
| プロジェクト計画 | `docs/project/ai-research-tracking/project.md` |
| フォーク元スキル | `.claude/skills/finance-news-workflow/` |

## エラーハンドリング

| エラー | 対処 |
|--------|------|
| E001: 企業定義マスタエラー | ファイル存在・JSON形式を確認 |
| E002: Python CLI エラー | prepare_ai_research_session.py のログを確認 |
| E003: GitHub CLI エラー | `gh auth login` で認証 |
| E004: ai-research-article-fetcher 失敗 | JSONファイルから手動再実行 |
| E005: スクレイピング失敗（Tier 2） | RobustScraperのログ確認、ドメイン別レートリミット調整 |
| E006: アダプタ失敗（Tier 3） | 企業サイト構造変更の可能性、アダプタ更新が必要 |

## 変更履歴

### 2026-02-11: 初版作成（Issue #3513）

- **finance-news-workflowからフォーク**: 3フェーズアーキテクチャを踏襲
- **ティアベース取得**: RSS(8社) + 汎用(64社) + アダプタ(5社)で77社をカバー
- **投資視点4セクション要約**: 概要/技術的意義/市場影響/投資示唆
- **10カテゴリ対応**: LLM、GPU、半導体装置、DC、ネットワーク、電力、原子力、ロボティクス、SaaS、MLOps
- **GitHub Project #44連携**: Category, Impact Level, Tickers等の追加フィールド対応

## 制約事項

- **GitHub API**: 1時間あたり5000リクエスト
- **スクレイピング**: ドメイン別レートリミット遵守（デフォルト3秒間隔）
- **重複チェック**: Python CLIで事前実行（URLベース）
- **実行頻度**: 週1回を推奨（MVPスコープ）
- **処理時間**: 全カテゴリ10分以内（目標）
- **bot対策**: UA ローテーション（7種）+ 429リトライ（指数バックオフ）
