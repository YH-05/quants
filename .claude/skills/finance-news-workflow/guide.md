# 金融ニュース収集ワークフロー詳細ガイド

このガイドは、finance-news-workflow スキルの詳細な処理フローとルールを説明します。

## 目次

1. [フィルタリングルール](#フィルタリングルール)
2. [重複チェックロジック](#重複チェックロジック)
3. [テーマ別処理フロー](#テーマ別処理フロー)
4. [GitHub Project投稿](#github-project投稿)
5. [エラーハンドリング詳細](#エラーハンドリング詳細)

---

## フィルタリングルール

### 1. 日数フィルタ（--days）

記事の**公開日時（published）**を基準に、過去N日以内の記事のみを対象とします。

#### パラメータ

| パラメータ | デフォルト | 説明 |
|-----------|-----------|------|
| `--days` | 7 | 過去何日分のニュースを対象とするか |

#### 例（現在が2026-01-24の場合）

| 値 | 対象範囲 |
|-----|------|
| `--days 1` | 2026-01-23 00:00 以降の記事 |
| `--days 3` | 2026-01-21 00:00 以降の記事 |
| `--days 7` | 2026-01-17 00:00 以降の記事（デフォルト） |

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
        RSS記事リスト
    days_back : int
        現在日時から遡る日数（デフォルト: 7）

    Returns
    -------
    tuple[list[dict], int]
        (フィルタリング後の記事リスト, 期間外でスキップされた件数)

    Notes
    -----
    - RSS MCPサーバーは各種フィード形式の日時を `published` に正規化:
      - RSS 2.0: pubDate → published
      - Atom: published, updated → published
    - published がない場合は fetched_at（取得日時）をフォールバック使用
    - どちらもない場合のみ除外
    """
    cutoff = datetime.now(timezone.utc) - timedelta(days=days_back)
    filtered = []
    skipped = 0

    for item in items:
        # published を優先、なければ fetched_at をフォールバック
        date_str = item.get("published") or item.get("fetched_at")

        if not date_str:
            # どちらもない記事は除外
            skipped += 1
            continue

        try:
            dt = datetime.fromisoformat(date_str.replace('Z', '+00:00'))
            if dt >= cutoff:
                filtered.append(item)
            else:
                skipped += 1
        except ValueError:
            # パース失敗時は除外
            skipped += 1

    return filtered, skipped
```

#### 処理フロー

```
[1] --days パラメータを取得（デフォルト: 7）
    ↓
[2] カットオフ日時を計算（現在日時 - days_back）
    ↓
[3] 各記事をチェック
    │
    ├─ published が存在する場合 → published を使用
    │
    ├─ published がない & fetched_at がある場合 → fetched_at を使用
    │
    └─ どちらもない場合 → スキップ
    ↓
[4] 日時をカットオフと比較
    │
    ├─ カットオフ日時以降 → フィルタリング後リストに追加
    │
    └─ カットオフ日時より前 → スキップ
    ↓
[5] 統計に記録（date_filtered = スキップ件数）
```

**日時フィールドの正規化**:

RSS MCPサーバー（`src/rss/core/parser.py`）は各種フィード形式を自動的に正規化します：

| フィード形式 | 元のフィールド | 正規化先 |
|-------------|---------------|---------|
| RSS 2.0 | `pubDate` | `published` |
| Atom | `published` | `published` |
| Atom | `updated`（publishedがない場合） | `published` |

フィード自体に日時がない場合は `published` が `None` になるため、`fetched_at`（取得日時）をフォールバックとして使用します。

---

### 2. テーマフィルタ（--themes）

対象テーマを指定して収集範囲を限定します。

#### パラメータ値

| 値 | 説明 |
|----|------|
| `all` | 全テーマを対象（デフォルト） |
| `index` | 株価指数（日経平均、S&P500等） |
| `stock` | 個別銘柄（決算、M&A等） |
| `sector` | セクター（業界動向） |
| `macro` | マクロ経済（金融政策、経済指標） |
| `ai` | AI（技術、企業、投資） |
| `finance` | 金融（財務、資金調達） |

#### 複数テーマ指定

カンマ区切りで複数テーマを指定可能:

```bash
# Index と Macro のみ収集（過去3日間）
/finance-news-workflow --days 3 --themes "index,macro"

# AI と Stock のみ収集
/finance-news-workflow --themes "ai,stock"
```

#### 実装ロジック

```python
def parse_themes_param(themes: str) -> list[str]:
    """--themesパラメータをテーマリストに変換

    Parameters
    ----------
    themes : str
        テーマ指定（例: "all", "index,macro"）

    Returns
    -------
    list[str]
        対象テーマのリスト
    """
    all_themes = ["index", "stock", "sector", "macro", "ai", "finance"]

    if themes == "all":
        return all_themes

    return [t.strip() for t in themes.split(",") if t.strip() in all_themes]
```

---

### 3. テーマ判定（AI判断）

**重要**: キーワードマッチングは使用しません。AIが記事の内容を読み取り、テーマに該当するか判断します。

#### テーマ別判定基準

| テーマ | 判定基準 |
|--------|----------|
| **Index** | 株価指数（日経平均、TOPIX、S&P500、ダウ、ナスダック等）の動向、市場全体の上昇/下落、ETF関連 |
| **Stock** | 個別企業の決算発表、業績予想、M&A、買収、提携、株式公開、経営陣の変更 |
| **Sector** | 特定業界（銀行、保険、自動車、半導体、ヘルスケア、エネルギー等）の動向、規制変更 |
| **Macro** | 金融政策（金利、量的緩和）、中央銀行（Fed、日銀、ECB）、経済指標（GDP、CPI、雇用統計）、為替 |
| **AI** | AI技術、機械学習、生成AI、AI企業（OpenAI、NVIDIA等）、AI投資、AI規制 |
| **Finance** | 企業財務、資金調達（IPO、増資、社債）、株主還元（配当、自社株買い）、金融商品 |

#### 判定プロセス

```
[1] 記事のタイトルと要約（summary）を読む
    ↓
[2] 記事の主題を理解する
    ↓
[3] テーマ判定基準に照らして該当するか判断
    ↓
[4] 該当する場合 → 処理続行
    該当しない場合 → スキップ
```

#### 判定例

| 記事タイトル | AIの判断 | テーマ |
|------------|---------|--------|
| "S&P 500 hits new record high amid tech rally" | 株価指数の動向 → 該当 | Index |
| "Fed signals rate cut in March meeting" | 金融政策・中央銀行 → 該当 | Macro |
| "Apple reports Q4 earnings beat" | 個別企業の決算 → 該当 | Stock |
| "Banks face new capital requirements" | 銀行セクターの規制 → 該当 | Sector |
| "OpenAI launches new model capabilities" | AI企業の動向 → 該当 | AI |
| "Celebrity launches new clothing line" | 金融・経済と無関係 → 非該当 | - |

---

### 5. 除外カテゴリ

以下のカテゴリに該当する記事は除外します（金融テーマに関連する場合を除く）:

| カテゴリ | 説明 | 例外 |
|---------|------|------|
| **スポーツ** | 試合結果、選手移籍など | スポーツ関連企業の決算等は対象 |
| **エンターテインメント** | 映画、音楽、芸能ニュース | - |
| **政治** | 選挙、内閣関連 | 金融政策・規制に関連する場合は対象 |
| **一般ニュース** | 事故、災害、犯罪 | - |

---

## 重複チェックロジック

### 1. 既存Issue取得方法

GitHub CLIで指定日数以内に作成されたニュースIssueを取得します。

```bash
# SINCE_DATE = 現在日時 - days_back（YYYY-MM-DD形式）
gh issue list \
    --repo YH-05/quants \
    --label "news" \
    --state all \
    --search "created:>=${SINCE_DATE}" \
    --json number,title,body,url,createdAt
```

#### 日数ベースのフィルタリング

| --days | SINCE_DATE（2026-01-24の場合） | 対象範囲 |
|--------|-------------------------------|---------|
| 1 | 2026-01-23 | 直近1日間 |
| 3 | 2026-01-21 | 直近3日間 |
| 7 | 2026-01-17 | 直近7日間（デフォルト） |

#### 取得データ構造

```json
{
  "existing_issues": [
    {
      "number": 344,
      "title": "[マクロ経済] 日銀、政策金利を据え置き",
      "url": "https://github.com/YH-05/quants/issues/344",
      "body": "## 概要\n...\n## 情報源\nhttps://example.com/article/123",
      "createdAt": "2026-01-21T08:22:33Z"
    }
  ]
}
```

### 2. 重複判定基準

2つの方法で重複を判定します:

#### 方法1: URL完全一致

```python
def is_url_duplicate(new_url: str, existing_issues: list[dict]) -> bool:
    """URLの完全一致で重複チェック

    Parameters
    ----------
    new_url : str
        新規記事のURL
    existing_issues : list[dict]
        既存Issueのリスト

    Returns
    -------
    bool
        重複している場合True
    """
    for issue in existing_issues:
        body = issue.get("body", "")
        if new_url and new_url in body:
            return True
    return False
```

#### 方法2: タイトル類似度（Jaccard係数）

```python
def calculate_title_similarity(title1: str, title2: str) -> float:
    """タイトルの類似度を計算（Jaccard係数）

    Parameters
    ----------
    title1 : str
        タイトル1
    title2 : str
        タイトル2

    Returns
    -------
    float
        類似度（0.0〜1.0）

    Notes
    -----
    Jaccard係数 = |A ∩ B| / |A ∪ B|
    単語の共通率で類似度を算出
    """
    words1 = set(title1.lower().split())
    words2 = set(title2.lower().split())

    if not words1 or not words2:
        return 0.0

    common = words1.intersection(words2)
    total = words1.union(words2)

    return len(common) / len(total)


def is_title_duplicate(
    new_title: str,
    existing_issues: list[dict],
    threshold: float = 0.85,
) -> bool:
    """タイトル類似度で重複チェック

    Parameters
    ----------
    new_title : str
        新規記事のタイトル
    existing_issues : list[dict]
        既存Issueのリスト
    threshold : float
        類似度閾値（デフォルト: 0.85）

    Returns
    -------
    bool
        重複している場合True
    """
    for issue in existing_issues:
        issue_title = issue.get("title", "")
        similarity = calculate_title_similarity(new_title, issue_title)
        if similarity >= threshold:
            return True
    return False
```

### 3. 重複判定フロー

```
[1] 新規記事のURLを取得
    ↓
[2] URL完全一致チェック
    │
    ├─ 一致 → 重複と判定（スキップ）
    │
    └─ 不一致 → 次のチェックへ
    ↓
[3] タイトル類似度チェック（閾値: 0.85）
    │
    ├─ 類似度 >= 0.85 → 重複と判定（スキップ）
    │
    └─ 類似度 < 0.85 → 新規記事として処理続行
```

### 4. 統合された重複チェック関数

```python
def is_duplicate(
    new_item: dict,
    existing_issues: list[dict],
    threshold: float = 0.85,
) -> bool:
    """既存Issueと重複しているかチェック

    Parameters
    ----------
    new_item : dict
        新規記事データ
    existing_issues : list[dict]
        既存Issueのリスト
    threshold : float
        タイトル類似度閾値（デフォルト: 0.85）

    Returns
    -------
    bool
        重複している場合True
    """
    new_link = new_item.get("link", "")
    new_title = new_item.get("title", "")

    for issue in existing_issues:
        # URL完全一致
        body = issue.get("body", "")
        if new_link and new_link in body:
            return True

        # タイトル類似度チェック
        issue_title = issue.get("title", "")
        similarity = calculate_title_similarity(new_title, issue_title)
        if similarity >= threshold:
            return True

    return False
```

---

## テーマ別処理フロー

### 1. 全体アーキテクチャ

```
┌─────────────────────────────────────────────────────────────────┐
│                    /collect-finance-news                        │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                   Phase 1: 初期化                                │
│  ├── テーマ設定ファイル確認                                      │
│  ├── RSS MCP ツール確認（リトライ付き）                          │
│  └── GitHub CLI 確認                                             │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│               Phase 2: データ準備（オーケストレーター）           │
│  finance-news-orchestrator エージェント起動                      │
│  ├── 既存Issue取得（gh issue list）                              │
│  └── 一時ファイル保存（.tmp/news-collection-{timestamp}.json）   │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                Phase 3: テーマ別収集（並列）                      │
│                                                                  │
│  ┌──────────────┐ ┌──────────────┐ ┌──────────────┐             │
│  │ finance-news │ │ finance-news │ │ finance-news │             │
│  │    -index    │ │    -stock    │ │   -sector    │             │
│  └──────────────┘ └──────────────┘ └──────────────┘             │
│                                                                  │
│  ┌──────────────┐ ┌──────────────┐ ┌──────────────┐             │
│  │ finance-news │ │ finance-news │ │ finance-news │             │
│  │    -macro    │ │     -ai      │ │   -finance   │             │
│  └──────────────┘ └──────────────┘ └──────────────┘             │
│                                                                  │
│  各エージェントが並列実行:                                        │
│  ├── 担当フィードからRSS取得                                     │
│  ├── 公開日時フィルタリング                                      │
│  ├── AI判断によるテーマ分類                                      │
│  ├── 重複チェック                                                │
│  ├── Issue作成                                                   │
│  ├── Project追加                                                 │
│  └── Status・公開日時設定                                        │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                   Phase 4: 結果報告                              │
│  └── テーマ別投稿数サマリー表示                                  │
└─────────────────────────────────────────────────────────────────┘
```

### 2. オーケストレーターの処理フロー

```
finance-news-orchestrator
    │
    ├─[1] 設定ファイル読み込み
    │     └─ data/config/finance-news-themes.json
    │
    ├─[2] GitHub CLI 確認
    │     ├─ gh コマンド存在確認
    │     └─ gh auth status で認証確認
    │
    ├─[3] 既存Issue取得（日数ベース）
    │     └─ gh issue list --label "news" --search "created:>=${SINCE_DATE}"
    │
    ├─[4] タイムスタンプ生成
    │     └─ YYYYMMDD-HHMMSS形式
    │
    ├─[5] 一時ファイル保存
    │     └─ .tmp/news-collection-{timestamp}.json
    │
    └─[6] 完了報告
          └─ セッションID、既存Issue数、フィード割り当てを報告
```

### 3. テーマ別エージェントの処理フロー

各テーマ別エージェント（finance-news-{theme}）は以下のフローを実行:

```
finance-news-{theme}
    │
    ├─[Phase 0] 入力データ検証
    │     ├─ 必須フィールド確認（title, link, published, summary）
    │     └─ 検証失敗時 → エラー報告して中断
    │
    ├─[Phase 1] 初期化
    │     ├─ MCPツールのロード（mcp__rss__fetch_feed, mcp__rss__get_items）
    │     ├─ 既存Issue取得（重複チェック用）
    │     └─ 統計カウンタ初期化
    │
    ├─[Phase 2] RSS取得
    │     ├─ 担当フィードからRSS取得
    │     └─ ローカルフォールバック（MCP失敗時）
    │
    ├─[Phase 2.5] 公開日時フィルタリング
    │     └─ --days パラメータによるフィルタ（published がない記事は除外）
    │
    ├─[Phase 3] AI判断によるテーマ分類
    │     ├─ タイトル・要約からテーマ判定
    │     ├─ 除外カテゴリチェック
    │     └─ 重複チェック
    │
    ├─[Phase 4] GitHub投稿
    │     ├─ [4.0] 記事本文取得・要約生成（news-article-fetcher サブエージェント）
    │     ├─ [4.1] 日時フォーマット変換
    │     ├─ [4.2] Issue作成（closed状態）
    │     ├─ [4.3] Project追加
    │     ├─ [4.4] Status設定
    │     └─ [4.5] 公開日時設定【必須】
    │
    └─[Phase 5] 結果報告
          └─ 統計サマリー出力
```

### 4. テーマ別フィード割り当て

| テーマ | エージェント | 担当フィード数 | 主なソース |
|--------|-------------|---------------|-----------|
| Index | finance-news-index | 5 | CNBC Markets, MarketWatch, NASDAQ |
| Stock | finance-news-stock | 5 | CNBC Earnings, Seeking Alpha, NASDAQ |
| Sector | finance-news-sector | 7 | CNBC (Health, Real Estate, Autos, Energy, Media, Retail, Travel) |
| Macro | finance-news-macro | 9 | CNBC Economy, Fed Press, IMF, Trading Economics |
| AI | finance-news-ai | 9 | CNBC Tech, Hacker News, TechCrunch, Ars Technica, NASDAQ AI |
| Finance | finance-news-finance | 7 | CNBC Finance, Yahoo Finance, FT, NASDAQ |

### 5. 並列実行パターン（並列度制御付き）

```python
# 並列度を設定から取得（デフォルト: 3）
concurrency = config.get("execution", {}).get("concurrency", 3)

# 対象テーマの決定
target_themes = parse_themes_param(args.themes)

# concurrency 件ずつバッチ実行（タイムアウト対策）
for i in range(0, len(target_themes), concurrency):
    batch_themes = target_themes[i:i + concurrency]

    # バッチ内は並列起動
    tasks = []
    for theme in batch_themes:
        task = Task(
            subagent_type=f"finance-news-{theme}",
            description=f"{theme}テーマのニュース収集",
            prompt=f"""一時ファイルを読み込んで{theme}テーマのニュースを処理してください。

## パラメータ
- --days: {args.days}
- --dry-run: {args.dry_run}
- --batch-size: {args.batch_size}
- --timeout: {args.timeout}

## 一時ファイル
{temp_file_path}

## 実行制御
- 記事数上限: {config.get("execution", {}).get("max_articles_per_theme", 20)}件
- タイムアウト: {config.get("execution", {}).get("timeout_minutes", 10)}分
""",
            run_in_background=True
        )
        tasks.append(task)

    # バッチ内タスクの完了を待機
    for task in tasks:
        result = TaskOutput(task_id=task.id)
        # 結果を集約
        # チェックポイント保存
```

### 6. チェックポイント再開パターン

```python
# --resume オプション指定時
if args.resume:
    # 最新のチェックポイントを検索
    checkpoint_dir = Path(config.get("execution", {}).get("checkpoint_dir", ".tmp/checkpoints"))
    checkpoints = sorted(checkpoint_dir.glob("news-collection-*.json"), reverse=True)

    if checkpoints:
        with open(checkpoints[0]) as f:
            checkpoint = json.load(f)

        # 再開対象テーマを特定
        themes_to_resume = []
        for theme, status in checkpoint["themes"].items():
            if status["status"] in ["pending", "in_progress"]:
                themes_to_resume.append({
                    "theme": theme,
                    "start_index": status.get("last_processed_index", 0),
                    "pending_articles": checkpoint.get("pending_articles", {}).get(theme, [])
                })

        # 再開処理を実行
        for resume_info in themes_to_resume:
            # ...
```

---

## GitHub Project投稿

### 1. Issue作成フォーマット

#### Issueタイトル

```
[{theme_ja}] {japanese_title}
```

| テーマ | 日本語名 | 例 |
|--------|---------|-----|
| Index | 株価指数 | [株価指数] S&P500が史上最高値を更新 |
| Stock | 個別銘柄 | [個別銘柄] アップル、Q4決算で予想を上回る |
| Sector | セクター | [セクター] 銀行セクターに新規制導入 |
| Macro | マクロ経済 | [マクロ経済] FRBが3月利下げを示唆 |
| AI | AI | [AI] OpenAIが新モデルを発表 |
| Finance | 金融 | [金融] テスラが50億ドルの株式公開を発表 |

#### Issue本文（テンプレート）

テンプレート: `.github/ISSUE_TEMPLATE/news-article.yml`（GitHub UI用）

**プログラムによるIssue作成**: HEREDOCで直接ボディを生成（`.claude/skills/finance-news-workflow/templates/issue-template.md` 参照）

```markdown
## 概要

{{summary}}

## 情報源

{{url}}

## 詳細情報

| 項目 | 内容 |
|------|------|
| 公開日時 | {{published_date}} |
| 収集日時 | {{collected_at}} |
| カテゴリ | {{category}} |
| ソース | {{feed_source}} |

## 備考

{{notes}}
```

#### 日本語要約フォーマット（4セクション構成）

```markdown
### 概要
- [主要事実を箇条書きで3行程度]
- [数値データがあれば含める]
- [関連企業があれば含める]

### 背景
[この出来事の背景・経緯を記載。記事に記載がなければ「[記載なし]」]

### 市場への影響
[株式・為替・債券等への影響を記載。記事に記載がなければ「[記載なし]」]

### 今後の見通し
[今後予想される展開・注目点を記載。記事に記載がなければ「[記載なし]」]
```

### 2. ラベル設定

```bash
gh issue create \
    --repo YH-05/quants \
    --title "[{theme_ja}] {japanese_title}" \
    --body "$body" \
    --label "news"
```

**注意**: Issueは `closed` 状態で作成します:

```bash
# Issue作成後にcloseする
gh issue close "$issue_number" --repo YH-05/quants
```

### 3. Project追加方法

#### ステップ1: Projectに追加

```bash
gh project item-add 15 \
    --owner YH-05 \
    --url {issue_url}
```

#### ステップ2: Issue Node ID取得

```bash
gh api graphql -f query='
query {
  repository(owner: "YH-05", name: "finance") {
    issue(number: {issue_number}) {
      id
    }
  }
}'
```

#### ステップ3: Project Item ID取得

```bash
gh api graphql -f query='
query {
  node(id: "{issue_node_id}") {
    ... on Issue {
      projectItems(first: 10) {
        nodes {
          id
          project {
            number
          }
        }
      }
    }
  }
}'
```

#### ステップ4: Status設定

```bash
gh api graphql -f query='
mutation {
  updateProjectV2ItemFieldValue(
    input: {
      projectId: "PVT_kwHOBoK6AM4BMpw_"
      itemId: "{project_item_id}"
      fieldId: "PVTSSF_lAHOBoK6AM4BMpw_zg739ZE"
      value: {
        singleSelectOptionId: "{status_option_id}"
      }
    }
  ) {
    projectV2Item {
      id
    }
  }
}'
```

#### ステップ5: 公開日時設定【必須】

```bash
gh api graphql -f query='
mutation {
  updateProjectV2ItemFieldValue(
    input: {
      projectId: "PVT_kwHOBoK6AM4BMpw_"
      itemId: "{project_item_id}"
      fieldId: "PVTF_lAHOBoK6AM4BMpw_zg8BzrI"
      value: {
        date: "{published_iso}"
      }
    }
  ) {
    projectV2Item {
      id
    }
  }
}'
```

**日付形式**: `YYYY-MM-DD`（例: `2026-01-22`）

### 4. テーマ別Status ID一覧

| テーマ | Status名 | Option ID |
|--------|----------|-----------|
| index | Index | `3925acc3` |
| stock | Stock | `f762022e` |
| sector | Sector | `48762504` |
| macro | Macro Economics | `730034a5` |
| ai | AI | `6fbb43d0` |
| finance | Finance | `ac4a91b1` |

### 5. GitHub Projectフィールド一覧

| フィールド名 | フィールドID | 型 | 用途 |
|-------------|-------------|-----|------|
| Status | `PVTSSF_lAHOBoK6AM4BMpw_zg739ZE` | SingleSelect | テーマ分類 |
| 公開日時 | `PVTF_lAHOBoK6AM4BMpw_zg8BzrI` | Date | ソート用 |

---

## エラーハンドリング詳細

### E001: テーマ設定ファイルエラー

**発生条件**:
- `data/config/finance-news-themes.json` が存在しない
- JSON形式が不正

**対処法**:

```python
try:
    with open("data/config/finance-news-themes.json") as f:
        config = json.load(f)
except FileNotFoundError:
    print("エラー: テーマ設定ファイルが見つかりません")
    print("期待されるパス: data/config/finance-news-themes.json")
    raise
except json.JSONDecodeError as e:
    print(f"エラー: JSON形式が不正です - {e}")
    raise
```

### E002: RSS MCP ツールエラー

**発生条件**:
- RSS MCPサーバーが起動していない
- MCPサーバーの起動が完了していない

**自動対処（リトライロジック）**:

```
[試行1] MCPSearch: query="rss", max_results=5
    ↓
ツールが見つからない場合
    ↓
[待機] 3秒待機
    ↓
[試行2] MCPSearch: query="rss", max_results=5
    ↓
それでも見つからない場合
    ↓
エラー報告 → 処理中断
```

### E003: GitHub CLI エラー

**発生条件**:
- `gh` コマンドがインストールされていない
- GitHub認証が切れている

**確認コマンド**:

```bash
# コマンド存在確認
command -v gh

# 認証確認
gh auth status
```

### E004: ネットワークエラー

**発生条件**:
- RSS フィードへの接続失敗
- GitHub API への接続失敗

**対処法**:
- 自動リトライ（最大3回、指数バックオフ）
- ローカルフォールバック

### E005: GitHub API レート制限

**発生条件**:
- 1時間あたり5000リクエストを超過

**対処法**:
- 1時間待機
- `--days` を減らして対象期間を短縮

### E006: 並列実行エラー

**発生条件**:
- 一部のテーマエージェントが失敗

**対処法**:
- 成功したテーマの結果は有効
- 失敗したテーマのみ `--themes` で再実行

```bash
# 失敗したテーマのみ再実行
/collect-finance-news --themes "stock,ai"
```

---

## 参考資料

- **SKILL.md**: `.claude/skills/finance-news-workflow/SKILL.md`
- **コマンド**: `.claude/commands/collect-finance-news.md`
- **オーケストレーター**: `.claude/agents/finance-news-orchestrator.md`
- **共通処理ガイド**: `.claude/agents/finance_news_collector/common-processing-guide.md`
- **テーマ設定**: `data/config/finance-news-themes.json`
- **GitHub Project**: https://github.com/users/YH-05/projects/15
- **データ渡しルール**: `.claude/rules/subagent-data-passing.md`
