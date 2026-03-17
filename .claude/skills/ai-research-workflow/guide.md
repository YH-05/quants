# AI投資バリューチェーン収集ワークフロー詳細ガイド

このガイドは、ai-research-workflow スキルの詳細な処理フローとルールを説明します。

## 目次

1. [ティアベース取得システム](#ティアベース取得システム)
2. [フィルタリングルール](#フィルタリングルール)
3. [重複チェックロジック](#重複チェックロジック)
4. [カテゴリ別処理フロー](#カテゴリ別処理フロー)
5. [投資視点要約生成](#投資視点要約生成)
6. [GitHub Project投稿](#github-project投稿)
7. [スクレイピング統計レポート](#スクレイピング統計レポート)
8. [エラーハンドリング詳細](#エラーハンドリング詳細)

---

## ティアベース取得システム

77社を効率的にカバーするため、3ティアで段階的に処理する。**全企業に個別アダプタを書かない**設計。

### Tier 1: RSS取得（8社）

既存の `src/rss/services/feed_reader.py` を使用。新規コード不要。

**対象企業**: NVIDIA, Microsoft AI, Google DeepMind, Cisco, Bloom Energy, Schneider Electric, nVent Electric, Intuitive Surgical

```python
from rss.services.feed_reader import FeedReader

async def fetch_tier1_articles(company: dict) -> list[ArticleData]:
    """Tier 1: RSSフィードから記事を取得

    Parameters
    ----------
    company : dict
        企業定義（ai-research-companies.jsonの1企業分）

    Returns
    -------
    list[ArticleData]
        取得した記事リスト（ArticleData統一形式）
    """
    reader = FeedReader()
    rss_url = company["urls"]["rss"]
    items = await reader.fetch(rss_url)
    return [to_article_data(item, company) for item in items]
```

### Tier 2: 汎用スクレイパー（64社）

`src/rss/services/company_scrapers/robust_scraper.py` を使用。

**bot対策基盤**:
- 7種UAローテーション（直前UA回避）
- ドメイン別レートリミット（asyncio.Lock排他制御）
- 429リトライ（Retry-After対応、指数バックオフ2->4->8秒）
- 3段階フォールバック: trafilatura -> Playwright -> lxml

```python
from rss.services.company_scrapers.robust_scraper import RobustScraper

async def fetch_tier2_articles(company: dict, scraper: RobustScraper) -> list[ArticleData]:
    """Tier 2: 汎用スクレイパーで記事を取得

    Parameters
    ----------
    company : dict
        企業定義
    scraper : RobustScraper
        共有スクレイパーインスタンス

    Returns
    -------
    list[ArticleData]
        取得した記事リスト
    """
    blog_url = company["urls"]["blog"]
    articles = await scraper.scrape_blog_index(blog_url, max_articles=10)
    return [to_article_data(article, company) for article in articles]
```

### Tier 3: 企業別アダプタ（5社）

`src/rss/services/company_scrapers/adapters/` の個別アダプタを使用。

**対象企業**: Perplexity AI, Cerebras, SambaNova, Lambda Labs, Fanuc

```python
from rss.services.company_scrapers.registry import CompanyScraperRegistry

async def fetch_tier3_articles(company: dict, registry: CompanyScraperRegistry) -> list[ArticleData]:
    """Tier 3: 企業別アダプタで記事を取得

    Parameters
    ----------
    company : dict
        企業定義
    registry : CompanyScraperRegistry
        アダプタレジストリ

    Returns
    -------
    list[ArticleData]
        取得した記事リスト
    """
    adapter = registry.get(company["key"])
    articles = await adapter.scrape_latest(max_articles=10)
    return [to_article_data(article, company) for article in articles]
```

### ティアルーティング

```python
async def fetch_company_articles(
    company: dict,
    scraper: RobustScraper,
    registry: CompanyScraperRegistry,
) -> list[ArticleData]:
    """ティアに基づいて適切な取得方法を選択

    Parameters
    ----------
    company : dict
        企業定義（tierフィールド: 1, 2, or 3）
    scraper : RobustScraper
        Tier 2用スクレイパー
    registry : CompanyScraperRegistry
        Tier 3用レジストリ

    Returns
    -------
    list[ArticleData]
        取得した記事リスト
    """
    tier = company["tier"]

    if tier == 1:
        return await fetch_tier1_articles(company)
    elif tier == 2:
        return await fetch_tier2_articles(company, scraper)
    elif tier == 3:
        return await fetch_tier3_articles(company, registry)
    else:
        logger.warning("Unknown tier", tier=tier, company=company["key"])
        return []
```

---

## フィルタリングルール

### 1. 日数フィルタ（--days）

記事の**公開日時（published）**を基準に、過去N日以内の記事のみを対象とする。

| パラメータ | デフォルト | 説明 |
|-----------|-----------|------|
| `--days` | 7 | 過去何日分の記事を対象とするか |

#### 実装ロジック

```python
from datetime import datetime, timedelta, timezone

def filter_by_published_date(
    items: list[dict],
    days_back: int,
) -> tuple[list[dict], int]:
    """公開日時でフィルタリング

    Parameters
    ----------
    items : list[dict]
        記事リスト
    days_back : int
        現在日時から遡る日数

    Returns
    -------
    tuple[list[dict], int]
        (フィルタリング後の記事リスト, 期間外でスキップされた件数)

    Notes
    -----
    - published がない場合は scraped_at（スクレイピング取得日時）をフォールバック使用
    - どちらもない場合は処理対象に含める（除外しない）
    """
    cutoff = datetime.now(timezone.utc) - timedelta(days=days_back)
    filtered = []
    skipped = 0

    for item in items:
        date_str = item.get("published") or item.get("scraped_at")

        if not date_str:
            filtered.append(item)
            continue

        try:
            dt = datetime.fromisoformat(date_str.replace('Z', '+00:00'))
            if dt >= cutoff:
                filtered.append(item)
            else:
                skipped += 1
        except ValueError:
            filtered.append(item)

    return filtered, skipped
```

### 2. カテゴリフィルタ（--categories）

対象カテゴリを指定して収集範囲を限定する。

| 値 | 説明 |
|----|------|
| `all` | 全10カテゴリを対象（デフォルト） |
| `ai_llm` | AI/LLM開発 |
| `gpu_chips` | GPU・演算チップ |
| `semiconductor_equipment` | 半導体製造装置 |
| `data_center` | データセンター・クラウド |
| `networking` | ネットワーキング |
| `power_energy` | 電力・エネルギー |
| `nuclear_fusion` | 原子力・核融合 |
| `physical_ai` | フィジカルAI・ロボティクス |
| `saas` | SaaS・AI活用ソフトウェア |
| `ai_infra` | AI基盤・MLOps |

#### 複数カテゴリ指定

```bash
# LLMとGPUのみ収集（過去3日間）
/ai-research-collect --days 3 --categories "ai_llm,gpu_chips"

# 電力・原子力のみ
/ai-research-collect --categories "power_energy,nuclear_fusion"
```

### 3. Top-N選択（--top-n）

各カテゴリごとに公開日時の新しい順で上位N件を選択する。

| パラメータ | デフォルト | 説明 |
|-----------|-----------|------|
| `--top-n` | 10 | 各カテゴリの最大記事数 |

```python
def select_top_n(articles: list[dict], n: int) -> list[dict]:
    """公開日時降順で上位N件を選択

    Parameters
    ----------
    articles : list[dict]
        記事リスト
    n : int
        選択する件数

    Returns
    -------
    list[dict]
        上位N件の記事リスト
    """
    sorted_articles = sorted(
        articles,
        key=lambda x: x.get("published", ""),
        reverse=True
    )
    return sorted_articles[:n]
```

---

## 重複チェックロジック

### 1. 既存Issue取得方法

GitHub CLIで指定日数以内に作成されたAI Research Issueを取得する。

```bash
# SINCE_DATE = 現在日時 - days_back（YYYY-MM-DD形式）
gh issue list \
    --repo YH-05/quants \
    --label "ai-research" \
    --state all \
    --search "created:>=${SINCE_DATE}" \
    --json number,title,body,url,createdAt
```

### 2. 重複判定基準

2つの方法で重複を判定する:

#### 方法1: URL完全一致（正規化後）

```python
def normalize_url(url: str) -> str:
    """URLを正規化して比較しやすくする"""
    if not url:
        return ""
    import urllib.parse
    url = url.rstrip('/')
    parsed = urllib.parse.urlparse(url)
    netloc = parsed.netloc.lower()
    if netloc.startswith("www."):
        netloc = netloc[4:]
    parsed = parsed._replace(fragment="", netloc=netloc)
    # トラッキングパラメータ除去
    if parsed.query:
        params = urllib.parse.parse_qs(parsed.query)
        filtered_params = {
            k: v for k, v in params.items()
            if not k.startswith(("utm_", "guce_"))
            and k not in {"ncid", "fbclid", "gclid", "ref", "source", "campaign"}
        }
        new_query = urllib.parse.urlencode(filtered_params, doseq=True)
        parsed = parsed._replace(query=new_query)
    return urllib.parse.urlunparse(parsed)
```

#### 方法2: タイトル類似度（Jaccard係数）

```python
def calculate_title_similarity(title1: str, title2: str) -> float:
    """タイトルの類似度を計算（Jaccard係数）"""
    words1 = set(title1.lower().split())
    words2 = set(title2.lower().split())
    if not words1 or not words2:
        return 0.0
    common = words1.intersection(words2)
    total = words1.union(words2)
    return len(common) / len(total)
```

### 3. 重複判定フロー

```
[1] 新規記事のURLを正規化
    |
[2] URL完全一致チェック
    |-- 一致 -> 重複と判定（スキップ）
    +-- 不一致 -> 次のチェックへ
    |
[3] タイトル類似度チェック（閾値: 0.85）
    |-- 類似度 >= 0.85 -> 重複と判定（スキップ）
    +-- 類似度 < 0.85 -> 新規記事として処理続行
```

---

## カテゴリ別処理フロー

### 全体アーキテクチャ

```
/ai-research-collect
    |
    v
Phase 1: Python CLI前処理
    +-- 企業定義マスタ読み込み（77社）
    +-- ティアベース取得:
    |   +-- Tier 1: RSS (8社) -> FeedReader
    |   +-- Tier 2: 汎用 (64社) -> RobustScraper
    |   +-- Tier 3: アダプタ (5社) -> CompanyScraperRegistry
    +-- ArticleData統一形式に変換
    +-- 既存Issue取得 -> URL抽出（重複チェック用）
    +-- 日付フィルタ -> 重複チェック -> Top-N選択
    +-- カテゴリ別JSON出力（.tmp/ai-research-batches/）
    +-- スクレイピング統計出力（.tmp/ai-research-scrape-stats.json）
    |
    v
Phase 2: AI投資視点要約 + Issue一括作成（10カテゴリ並列）
    |
    +-- [ai_llm] ai-research-article-fetcher
    +-- [gpu_chips] ai-research-article-fetcher
    +-- [semiconductor_equipment] ai-research-article-fetcher
    +-- [data_center] ai-research-article-fetcher
    +-- [networking] ai-research-article-fetcher
    +-- [power_energy] ai-research-article-fetcher
    +-- [nuclear_fusion] ai-research-article-fetcher
    +-- [physical_ai] ai-research-article-fetcher
    +-- [saas] ai-research-article-fetcher
    +-- [ai_infra] ai-research-article-fetcher
    |
    v
Phase 3: 結果集約 + スクレイピング統計レポート
    +-- カテゴリ別投稿数サマリー
    +-- ティア別成功率レポート
    +-- 構造変更検知レポート
```

### Phase 1 の詳細: prepare_ai_research_session.py

```
prepare_ai_research_session.py
    |
    +--[1] 設定ファイル読み込み
    |     +-- data/config/ai-research-companies.json
    |
    +--[2] GitHub CLI 確認
    |     +-- gh auth status
    |
    +--[3] 既存Issue取得（日数ベース）
    |     +-- gh issue list --label "ai-research" --search "created:>=${SINCE_DATE}"
    |     +-- URL抽出 + キャッシュ
    |
    +--[4] カテゴリ別・企業別にデータ収集
    |     +-- Tier 1: FeedReader
    |     +-- Tier 2: RobustScraper（ドメイン別レートリミット遵守）
    |     +-- Tier 3: CompanyScraperRegistry
    |
    +--[5] ArticleData統一形式に変換
    |     +-- url, title, text, company_key, company_name, category
    |     +-- source_type, pdf_url, published
    |
    +--[6] フィルタリング
    |     +-- 日付フィルタ（--days）
    |     +-- 重複チェック（URL + タイトル類似度）
    |     +-- Top-N選択（--top-n、公開日時降順）
    |
    +--[7] カテゴリ別JSON出力
    |     +-- .tmp/ai-research-batches/{category_key}.json
    |
    +--[8] スクレイピング統計出力
          +-- .tmp/ai-research-scrape-stats.json
```

### Phase 2 の詳細: ai-research-article-fetcher

各カテゴリの記事に対して:

```
ai-research-article-fetcher
    |
    +--[1] URL必須検証
    +--[2] 本文最低文字数チェック（100文字未満 -> スキップ）
    +--[3] タイトル翻訳（英語 -> 日本語）
    +--[4] 投資視点4セクション要約生成
    +--[5] 市場影響度判定（low/medium/high）
    +--[6] 関連銘柄タグ付け
    +--[7] Status自動判定
    +--[8] 要約フォーマット検証
    +--[9] Issue作成（gh issue create + close）
    |     +-- --label "ai-research" --label "{category_label_gh}" --label "needs-review"
    +--[10] Project追加（gh project item-add 44）
    +--[11] Category設定（GraphQL API）
    +--[12] Status設定（GraphQL API）
    +--[13] 公開日時設定（GraphQL API）
    +--[14] Impact Level設定（GraphQL API）
    +--[15] Tickers設定（GraphQL API）
```

---

## 投資視点要約生成

### 4セクション構成

finance-news-workflowの一般金融4セクション（概要/背景/市場への影響/今後の見通し）とは異なり、**投資視点**に特化した4セクション構成を使用する。

```markdown
### 概要
- [発表内容・主要事実を箇条書きで3-5行]
- [数値データがあれば必ず含める]
- [企業名・製品名を明記]

### 技術的意義
[技術的なブレークスルーの評価]
- 従来技術との比較
- 性能向上の定量的データ（ベンチマーク等）
- 技術的な差別化ポイント
[記事に該当情報がなければ「[記載なし]」]

### 市場影響
[関連銘柄・セクターへの影響分析]
- 直接的な影響を受ける企業・銘柄
- 競合企業への影響
- セクター全体への波及効果
- 短期・中期の株価への影響見通し
[記事に該当情報がなければ「[記載なし]」]

### 投資示唆
[投資家にとっての意味合い]
- 注目すべき投資機会
- リスク要因
- 今後のカタリスト（決算、製品リリース等）
- 推奨するウォッチリスト銘柄
[記事に該当情報がなければ「[記載なし]」]
```

### カテゴリ別の重点分析項目

| カテゴリ | 重点項目 |
|---------|----------|
| **AI/LLM開発** | モデル性能ベンチマーク、API価格、トレーニングコスト、市場シェア |
| **GPU・演算チップ** | 演算性能、電力効率、供給制約、顧客獲得、競合比較 |
| **半導体製造装置** | プロセスノード、歩留まり、設備投資額、納期、技術ロードマップ |
| **データセンター・クラウド** | 容量拡張、PUE、GPU密度、CapEx、顧客契約 |
| **ネットワーキング** | 帯域幅、レイテンシ、AI最適化、DC向け出荷 |
| **電力・エネルギー** | 発電容量、電力契約、DC向け供給、再エネ比率 |
| **原子力・核融合** | 出力規模、実証進捗、規制認可、DC電力契約 |
| **フィジカルAI・ロボティクス** | 自律度、タスク成功率、製造コスト、量産計画 |
| **SaaS・AI活用ソフト** | ARR、AI機能採用率、ARPU、競合優位性 |
| **AI基盤・MLOps** | プラットフォーム利用者数、収益モデル、OSS貢献度 |

### 要約の品質基準

1. **文字数**: 各セクション100文字以上（概要セクションは200文字以上）
2. **具体性**: 数値・固有名詞・ティッカーシンボルを必ず含める
3. **構造化**: 4セクション構成を厳守
4. **投資視点**: 全セクションを投資家目線で記述
5. **正確性**: 記事に書かれた事実のみ、推測禁止
6. **欠落表示**: 情報がない場合は「[記載なし]」と明記

### 市場影響度判定基準

| レベル | 基準 | 例 |
|--------|------|-----|
| **high** | 新製品発表、大型提携、決算サプライズ、規制変更、大型買収 | GPT-5発表、NVIDIA Blackwellリリース |
| **medium** | 機能アップデート、小規模提携、市場動向、人事異動 | API価格改定、カンファレンス発表 |
| **low** | ブログ投稿、技術解説、カンファレンス参加、マイナーアップデート | 技術ブログ記事、OSSリリース |

### Status自動判定基準

| Status | 判定基準 |
|--------|---------|
| `Company Release` | 新製品発表、サービスリリース、ローンチ |
| `Product Update` | 機能アップデート、バージョンアップ、改善 |
| `Partnership` | 提携、協業、統合、買収 |
| `Earnings Impact` | 決算、収益、売上、財務、価格変更 |
| `Infrastructure` | データセンター、インフラ、設備投資、電力 |

---

## GitHub Project投稿

### 1. Issue作成フォーマット

#### Issueタイトル

```
[{category_label}] {japanese_title}
```

| カテゴリ | 日本語名 | 例 |
|---------|---------|-----|
| ai_llm | AI/LLM開発 | [AI/LLM開発] OpenAIがGPT-5を発表 |
| gpu_chips | GPU・演算チップ | [GPU・演算チップ] NVIDIAがBlackwell Ultra出荷開始 |
| semiconductor_equipment | 半導体製造装置 | [半導体製造装置] TSMCが2nm量産を前倒し |
| data_center | データセンター・クラウド | [データセンター・クラウド] CoreWeaveが新DC建設を発表 |
| networking | ネットワーキング | [ネットワーキング] Aristaが400GbE DCスイッチを発表 |
| power_energy | 電力・エネルギー | [電力・エネルギー] Constellation EnergyがDC向け電力契約 |
| nuclear_fusion | 原子力・核融合 | [原子力・核融合] Okloが先進炉の建設許可を取得 |
| physical_ai | フィジカルAI・ロボティクス | [フィジカルAI・ロボティクス] TeslaがOptimus量産計画を発表 |
| saas | SaaS・AI活用ソフトウェア | [SaaS・AI活用ソフトウェア] PalantirがAI分析プラットフォームを刷新 |
| ai_infra | AI基盤・MLOps | [AI基盤・MLOps] HuggingFaceがモデルHub v2を発表 |

### 2. ラベル設定

```bash
gh issue create \
    --repo YH-05/quants \
    --title "[${category_label}] ${japanese_title}" \
    --body "$body" \
    --label "ai-research" \
    --label "${category_label_gh}" \
    --label "needs-review"
```

**注意**: Issueは `closed` 状態で作成する:

```bash
gh issue close "$issue_number" --repo YH-05/quants
```

### 3. Project #44 追加・フィールド設定

Issue作成後、以下を設定:

1. **Project追加**: `gh project item-add 44 --owner YH-05 --url {issue_url}`
2. **Category設定**: カテゴリに対応するCategoryを設定
3. **Status設定**: 記事内容から自動判定したStatusを設定
4. **公開日時設定**: `YYYY-MM-DD` 形式で日付を設定
5. **Impact Level設定**: 市場影響度（low/medium/high）を設定
6. **Tickers設定**: 関連銘柄ティッカーをカンマ区切りで設定

### 4. Project #44 フィールド一覧

| フィールド名 | フィールドID | 型 | 用途 |
|-------------|-------------|-----|------|
| Status | `PVTSSF_lAHOBoK6AM4BO4gxzg9dFiA` | SingleSelect | 記事種別分類 |
| Category | `PVTSSF_lAHOBoK6AM4BO4gxzg9dHB8` | SingleSelect | カテゴリ分類 |
| Published Date | `PVTF_lAHOBoK6AM4BO4gxzg9dHCA` | Date | ソート用 |
| Impact Level | `PVTSSF_lAHOBoK6AM4BO4gxzg9dHCI` | SingleSelect | 市場影響度 |
| Tickers | `PVTF_lAHOBoK6AM4BO4gxzg9dHCE` | Text | 関連銘柄 |

---

## スクレイピング統計レポート

### スクレイピング統計ファイル

`prepare_ai_research_session.py` が出力するスクレイピング統計:

**パス**: `.tmp/ai-research-scrape-stats.json`

```json
{
  "timestamp": "2026-02-11T10:00:00+09:00",
  "total_companies": 77,
  "tier_stats": {
    "tier1": {"total": 8, "success": 8, "failed": 0, "rate": "100.0%"},
    "tier2": {"total": 64, "success": 58, "failed": 6, "rate": "90.6%"},
    "tier3": {"total": 5, "success": 4, "failed": 1, "rate": "80.0%"}
  },
  "category_stats": {
    "ai_llm": {"companies": 11, "articles_found": 25, "after_filter": 15},
    "gpu_chips": {"companies": 10, "articles_found": 18, "after_filter": 10}
  },
  "failed_companies": [
    {"key": "cerebras", "tier": 3, "error": "AdapterError: ページ構造変更検知"},
    {"key": "sambanova", "tier": 2, "error": "RateLimitError: 429 Too Many Requests"}
  ],
  "structure_changes": [
    {"company_key": "openai", "url": "https://openai.com/news/", "hit_rate": 0.15, "threshold": 0.5}
  ]
}
```

### Phase 3 のスクレイピング統計レポート

Phase 3 の結果報告にスクレイピング統計を含める:

```markdown
## スクレイピング統計

### ティア別成功率

| ティア | 対象企業 | 成功 | 失敗 | 成功率 |
|--------|---------|------|------|--------|
| Tier 1 (RSS) | 8 | 8 | 0 | 100.0% |
| Tier 2 (汎用) | 64 | 58 | 6 | 90.6% |
| Tier 3 (アダプタ) | 5 | 4 | 1 | 80.0% |
| **合計** | **77** | **70** | **7** | **90.9%** |

### 失敗企業一覧

| 企業 | ティア | エラー |
|------|--------|--------|
| Cerebras | Tier 3 | AdapterError: ページ構造変更検知 |
| SambaNova | Tier 2 | RateLimitError: 429 Too Many Requests |

### 構造変更検知

| 企業 | URL | ヒット率 | 閾値 |
|------|-----|---------|------|
| OpenAI | https://openai.com/news/ | 15% | 50% |
```

---

## エラーハンドリング詳細

### E001: 企業定義マスタエラー

**発生条件**:
- `data/config/ai-research-companies.json` が存在しない
- JSON形式が不正

**対処法**:
```python
try:
    with open("data/config/ai-research-companies.json") as f:
        config = json.load(f)
except FileNotFoundError:
    logger.critical("企業定義マスタが見つかりません",
                    path="data/config/ai-research-companies.json")
    raise
except json.JSONDecodeError as e:
    logger.critical("JSON形式が不正です", error=str(e))
    raise
```

### E002: スクレイピングエラー（Tier 2）

**発生条件**:
- bot検知によるブロック（403/429）
- サイト構造変更

**対処法**:
- 自動リトライ（最大3回、指数バックオフ 2->4->8秒）
- Retry-After ヘッダ対応
- 3段階フォールバック（trafilatura -> Playwright -> lxml）
- 構造変更検知（StructureValidator）

### E003: アダプタエラー（Tier 3）

**発生条件**:
- 企業サイトのページ構造変更
- JavaScriptレンダリング失敗

**対処法**:
- エラーログに構造変更の詳細を記録
- 失敗企業はスキップし、他の企業の処理を継続
- 構造変更検知レポートに記録

### E004: GitHub API レート制限

**発生条件**:
- 1時間あたり5000リクエストを超過

**対処法**:
- 1時間待機
- `--categories` で対象カテゴリを限定して再実行

### E005: ai-research-article-fetcher 失敗

**発生条件**:
- 一部のカテゴリエージェントが失敗

**対処法**:
- 成功したカテゴリの結果は有効
- 失敗したカテゴリのみ `--categories` で再実行

```bash
# 失敗したカテゴリのみ再実行
/ai-research-collect --categories "gpu_chips,saas"
```

---

## 参考資料

- **SKILL.md**: `.claude/skills/ai-research-workflow/SKILL.md`
- **Issue作成テンプレート**: `.claude/skills/ai-research-workflow/templates/issue-template.md`
- **サマリーテンプレート**: `.claude/skills/ai-research-workflow/templates/summary-template.md`
- **ai-research-article-fetcher**: `.claude/agents/ai-research-article-fetcher.md`
- **企業定義マスタ**: `data/config/ai-research-companies.json`
- **Python CLI前処理**: `scripts/prepare_ai_research_session.py`
- **RobustScraper**: `src/rss/services/company_scrapers/robust_scraper.py`
- **プロジェクト計画**: `docs/project/ai-research-tracking/project.md`
- **GitHub Project #44**: https://github.com/users/YH-05/projects/44
- **データ渡しルール**: `.claude/rules/subagent-data-passing.md`
