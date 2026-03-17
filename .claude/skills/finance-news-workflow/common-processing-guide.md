# 金融ニュース収集エージェント共通処理ガイド

このガイドは、テーマ別ニュース収集エージェント（finance-news-{theme}）の共通処理を定義します。

## 🚨 最重要: 入力データ検証（Phase 0）

> **参照**: `.claude/rules/subagent-data-passing.md`

サブエージェントが処理を開始する前に、**入力データの完全性を必ず検証**すること。

### 必須フィールドチェック

```python
def validate_article_data(article: dict) -> tuple[bool, str]:
    """記事データの必須フィールドを検証する

    Parameters
    ----------
    article : dict
        検証対象の記事データ

    Returns
    -------
    tuple[bool, str]
        (検証成功, エラーメッセージ)
    """

    required_fields = ["title", "link", "published", "summary"]

    for field in required_fields:
        if field not in article or not article[field]:
            return False, f"必須フィールド '{field}' がありません"

    # URLの形式チェック
    if not article["link"].startswith(("http://", "https://")):
        return False, f"無効なURL形式: {article['link']}"

    return True, ""


def validate_input_data(data: dict) -> tuple[bool, list[str]]:
    """入力データ全体を検証する

    Parameters
    ----------
    data : dict
        プロンプトまたは一時ファイルから受け取ったデータ

    Returns
    -------
    tuple[bool, list[str]]
        (検証成功, エラーメッセージのリスト)
    """

    errors = []

    # 1. rss_items または articles の存在確認
    articles = data.get("rss_items") or data.get("articles") or []
    if not articles:
        errors.append("記事データが空です")
        return False, errors

    # 2. 各記事の必須フィールド検証
    for i, article in enumerate(articles):
        valid, msg = validate_article_data(article)
        if not valid:
            errors.append(f"記事[{i}]: {msg}")

    # 3. 簡略化データの検出（警告）
    if isinstance(articles[0], str):
        errors.append("データが文字列形式です。JSON形式の完全なデータが必要です")

    return len(errors) == 0, errors
```

### 検証失敗時の対応

```python
# Phase 0: 入力データ検証
valid, errors = validate_input_data(input_data)

if not valid:
    # エラー報告して処理中断
    error_report = "\n".join([f"  - {e}" for e in errors])
    print(f"""
## ⛔ 入力データ検証エラー

入力データが不完全なため処理を中断します。

### 検出されたエラー
{error_report}

### 必要なデータ形式

記事データには以下のフィールドが必須です:
- `title`: 記事タイトル
- `link`: 元記事のURL（**絶対に省略禁止**）
- `published`: 公開日時
- `summary`: 記事要約

### 参照
- `.claude/rules/subagent-data-passing.md`
""")
    # 処理を終了
    return
```

### データ形式の例

**正しい形式**:
```json
{
  "rss_items": [
    {
      "item_id": "60af4cc3-0a47-4cfb-ae89-ed8872209f5d",
      "title": "Trump threatens to sue JPMorgan Chase",
      "link": "https://www.cnbc.com/2026/01/17/trump-jpmorgan-chase-debanking.html",
      "published": "2026-01-18T13:47:50+00:00",
      "summary": "President Trump threatened to sue JPMorgan...",
      "content": null,
      "author": null,
      "fetched_at": "2026-01-18T22:40:08.589493+00:00"
    }
  ],
  "existing_issues": [...]
}
```

**禁止される形式**:
```
# ❌ 簡略化されたリスト形式は絶対禁止
1. "Trump threatens JPMorgan" - 銀行関連
2. "BYD is a buy" - EV関連
```

---

## 共通設定

- **Issueテンプレート**: `.github/ISSUE_TEMPLATE/news-article.yml`（YAML形式、GitHub UI用）
- **GitHub Project**: #15 (`PVT_kwHOBoK6AM4BMpw_`)
- **Statusフィールド**: `PVTSSF_lAHOBoK6AM4BMpw_zg739ZE`
- **公開日時フィールド**: `PVTF_lAHOBoK6AM4BMpw_zg8BzrI`（Date型、ソート用）

## 実行制御設定（タイムアウト対策）

設定ソース: `data/config/finance-news-themes.json` → `execution`

| 設定 | デフォルト | 説明 |
|------|-----------|------|
| `batch_size` | 10 | 各テーマの処理記事数上限 |
| `max_articles_per_theme` | 20 | テーマあたりの最大記事数 |
| `concurrency` | 3 | 同時実行するテーマ数（1-6） |
| `timeout_minutes` | 10 | 各テーマのタイムアウト時間（分） |
| `checkpoint_enabled` | true | チェックポイント機能の有効/無効 |
| `checkpoint_dir` | `.tmp/checkpoints` | チェックポイント保存先 |

## 使用ツール

各サブエージェントは以下のツールを使用します：

```yaml
tools:
  - Read              # ファイル読み込み
  - Bash              # gh CLI実行
  - MCPSearch         # MCPツール検索・ロード
  - mcp__rss__fetch_feed   # RSSフィード更新
  - mcp__rss__get_items    # RSS記事取得
```

## Phase 1: 初期化

### ステップ1.1: MCPツールのロード

```python
def load_mcp_tools() -> bool:
    """MCPツールをロードする"""

    try:
        # MCPSearchでRSSツールをロード
        MCPSearch(query="select:mcp__rss__fetch_feed")
        MCPSearch(query="select:mcp__rss__get_items")
        return True
    except Exception as e:
        ログ出力: f"警告: MCPツールのロード失敗: {e}"
        ログ出力: "ローカルフォールバックを使用します"
        return False
```

### ステップ1.2: 既存Issue取得（重複チェック用）

**重要**: 一時ファイル（`.tmp/news-collection-{timestamp}.json`）から既存Issueを読み込むこと。
オーケストレーターが既に取得済みのデータを使用し、**独自に`gh issue list`を実行しない**。

```python
def load_existing_issues_from_session(session_file: str) -> list[dict]:
    """一時ファイルから既存Issueを読み込む

    Parameters
    ----------
    session_file : str
        オーケストレーターが作成した一時ファイルのパス

    Returns
    -------
    list[dict]
        既存Issueのリスト（number, title, article_url, createdAt）
    """
    with open(session_file) as f:
        session_data = json.load(f)

    return session_data.get("existing_issues", [])
```

#### URLの抽出とキャッシュ

オーケストレーターは既存Issueを取得する際、**各Issue本文から記事URLを抽出してキャッシュ**します。

```bash
gh issue list \
    --repo YH-05/quants \
    --label "news" \
    --state all \
    --limit 500 \
    --json number,title,body,createdAt
```

**URL抽出ロジック（オーケストレーターで実行）**:

```python
import re

def extract_article_url_from_body(body: str) -> str | None:
    """Issue本文から情報源URLを抽出する

    Parameters
    ----------
    body : str
        Issue本文（Markdown）

    Returns
    -------
    str | None
        抽出した記事URL、または None

    Notes
    -----
    Issue本文の「情報源URL【必須】」セクションからURLを抽出する。
    フォーマット:
        ### 情報源URL【必須】
        > ⚠️ このフィールドは必須です...
        https://example.com/article

    URL抽出ルール:
    1. 「情報源URL」セクション以降を対象
    2. https:// または http:// で始まるURLをキャプチャ
    3. 空白・改行で終了
    """

    if not body:
        return None

    # 情報源URLセクション以降を抽出
    url_section_match = re.search(
        r'###\s*情報源URL.*?\n(.*?)(?=\n###|\Z)',
        body,
        re.DOTALL | re.IGNORECASE
    )

    if url_section_match:
        section_text = url_section_match.group(1)
        # URLを抽出（https:// または http:// で始まる）
        url_match = re.search(
            r'(https?://[^\s<>\[\]"\'\)]+)',
            section_text
        )
        if url_match:
            return url_match.group(1).rstrip('.,;:')

    # フォールバック: 本文全体からURLを検索
    url_match = re.search(
        r'(https?://[^\s<>\[\]"\'\)]+)',
        body
    )
    if url_match:
        return url_match.group(1).rstrip('.,;:')

    return None


def prepare_existing_issues_with_urls(raw_issues: list[dict]) -> list[dict]:
    """既存IssueからURLを抽出してキャッシュする

    Parameters
    ----------
    raw_issues : list[dict]
        gh issue list で取得した生のIssueリスト

    Returns
    -------
    list[dict]
        article_url を追加したIssueリスト
    """
    result = []
    for issue in raw_issues:
        article_url = extract_article_url_from_body(issue.get("body", ""))
        result.append({
            "number": issue["number"],
            "title": issue["title"],
            "article_url": article_url,  # 🚨 記事URL（Issueの url ではない）
            "createdAt": issue.get("createdAt"),
        })
    return result
```

### ステップ1.3: 統計カウンタ初期化

```python
# 統計カウンタ（必ず全項目を初期化すること）
stats = {
    "processed": 0,       # 取得した記事総数
    "date_filtered": 0,   # 公開日時フィルタでスキップされた件数
    "matched": 0,         # テーマにマッチした件数
    "excluded": 0,        # 除外キーワードでスキップされた件数
    "duplicates": 0,      # 🚨 重複でスキップされた件数（必須カウント）
    "skipped_no_url": 0,  # URLなしでスキップされた件数
    "created": 0,         # 新規作成したIssue数
    "failed": 0,          # 作成失敗した件数
}

# 重複した記事のリスト（レポート用）
duplicate_articles = []  # [{"title": "...", "url": "...", "existing_issue": 123}, ...]
```

## Phase 2: RSS取得（フィード直接取得）

**重要**: 各サブエージェントは自分の担当フィードから直接記事を取得します。

### ステップ2.1: 担当フィードからの取得

```python
def fetch_assigned_feeds(assigned_feeds: list[dict]) -> list[dict]:
    """担当フィードから記事を取得する

    Parameters
    ----------
    assigned_feeds : list[dict]
        担当フィードのリスト（feed_id, titleを含む）

    Returns
    -------
    list[dict]
        取得した記事のリスト
    """

    all_items = []

    for feed in assigned_feeds:
        feed_id = feed["feed_id"]
        feed_title = feed["title"]

        try:
            # Step 1: フィードを最新化
            mcp__rss__fetch_feed(feed_id=feed_id)

            # Step 2: 記事を取得（24時間以内）
            items = mcp__rss__get_items(
                feed_id=feed_id,
                hours=24,
                limit=50
            )

            # フィード情報を付加
            for item in items:
                item["feed_source"] = feed_title
                item["feed_id"] = feed_id

            all_items.extend(items)
            ログ出力: f"取得完了: {feed_title} ({len(items)}件)"

        except Exception as e:
            ログ出力: f"警告: フィード取得失敗: {feed_title}: {e}"
            # ローカルフォールバックを試行
            local_items = load_from_local(feed_id, feed_title)
            all_items.extend(local_items)

    return all_items
```

### ステップ2.2: ローカルフォールバック

MCPツールが利用できない場合、ローカルに保存されたRSSデータを使用します。

```python
def load_from_local(feed_id: str, feed_title: str) -> list[dict]:
    """ローカルのRSSデータから記事を取得する

    Parameters
    ----------
    feed_id : str
        フィードID
    feed_title : str
        フィード名（ログ用）

    Returns
    -------
    list[dict]
        取得した記事のリスト
    """

    local_path = f"data/raw/rss/{feed_id}/items.json"

    try:
        with open(local_path) as f:
            data = json.load(f)

        items = data.get("items", [])

        # 24時間以内のアイテムのみフィルタ
        cutoff = datetime.now(timezone.utc) - timedelta(hours=24)
        recent_items = []

        for item in items:
            published = item.get("published")
            if published:
                try:
                    dt = datetime.fromisoformat(published.replace('Z', '+00:00'))
                    if dt >= cutoff:
                        item["feed_source"] = feed_title
                        item["feed_id"] = feed_id
                        recent_items.append(item)
                except ValueError:
                    continue

        ログ出力: f"ローカルから取得: {feed_title} ({len(recent_items)}件)"
        return recent_items

    except FileNotFoundError:
        ログ出力: f"警告: ローカルデータなし: {local_path}"
        return []
    except json.JSONDecodeError as e:
        ログ出力: f"警告: JSONパースエラー: {local_path}: {e}"
        return []
```

## Phase 2.5: 公開日時フィルタリング【必須】

**重要**: `--since`オプションで指定された期間内の記事のみを処理対象とします。

### ステップ2.5.1: --sinceパラメータの解析

```python
def parse_since_param(since: str) -> int:
    """--sinceパラメータを日数に変換

    Parameters
    ----------
    since : str
        期間指定（例: "1d", "3d", "7d"）

    Returns
    -------
    int
        日数

    Examples
    --------
    >>> parse_since_param("1d")
    1
    >>> parse_since_param("3d")
    3
    >>> parse_since_param("7d")
    7
    """

    if since.endswith("d"):
        try:
            return int(since[:-1])
        except ValueError:
            pass

    # デフォルト: 1日
    return 1
```

### ステップ2.5.2: 公開日時によるフィルタリング

```python
from datetime import datetime, timedelta, timezone

def filter_by_published_date(
    items: list[dict],
    since_days: int,
) -> tuple[list[dict], int]:
    """公開日時でフィルタリング

    Parameters
    ----------
    items : list[dict]
        RSS記事リスト
    since_days : int
        現在日時から遡る日数

    Returns
    -------
    tuple[list[dict], int]
        (フィルタリング後の記事リスト, 期間外でスキップされた件数)

    Notes
    -----
    - published フィールドは記事の公開日時（RSSのpubDate）
    - published がない場合は fetched_at で代替判定
    - 両方ない場合は処理対象に含める（除外しない）
    """

    cutoff = datetime.now(timezone.utc) - timedelta(days=since_days)
    filtered = []
    skipped = 0

    for item in items:
        # 公開日時を取得（published → fetched_at の順でフォールバック）
        date_str = item.get("published") or item.get("fetched_at")

        if not date_str:
            # 日時情報がない場合は処理対象に含める
            filtered.append(item)
            continue

        try:
            # ISO 8601形式をパース
            dt = datetime.fromisoformat(date_str.replace('Z', '+00:00'))

            if dt >= cutoff:
                filtered.append(item)
            else:
                skipped += 1
                ログ出力: f"期間外スキップ: {item.get('title', 'タイトルなし')} (公開: {date_str})"

        except ValueError:
            # パース失敗時は処理対象に含める
            filtered.append(item)

    ログ出力: f"公開日時フィルタ: {len(items)}件 → {len(filtered)}件 (過去{since_days}日以内)"
    return filtered, skipped
```

### ステップ2.5.3: フィルタリング実行

各エージェントはRSS取得後、テーマ判定前に以下を実行:

```python
# --since パラメータをパース（デフォルト: 1d）
since_days = parse_since_param(args.get("since", "1d"))

# 公開日時でフィルタリング
items, date_skipped = filter_by_published_date(items, since_days)

# 統計に記録
stats["date_filtered"] = date_skipped
```

## Phase 3: AI判断によるテーマ分類

**重要**: キーワードマッチングは使用しません。**AIが記事の内容を読み取り、テーマに該当するか判断**します。

### ステップ3.1: AI判断によるテーマ判定

各記事について、タイトルと要約（summary）を読み取り、以下の基準でテーマに該当するか判断します。

**テーマ別判定基準**:

| テーマ | 判定基準 |
|--------|----------|
| **Index** | 株価指数（日経平均、TOPIX、S&P500、ダウ、ナスダック等）の動向、市場全体の上昇/下落、ETF関連 |
| **Stock** | 個別企業の決算発表、業績予想、M&A、買収、提携、株式公開、経営陣の変更 |
| **Sector** | 特定業界（銀行、保険、自動車、半導体、ヘルスケア、エネルギー等）の動向、規制変更 |
| **Macro** | 金融政策（金利、量的緩和）、中央銀行（Fed、日銀、ECB）、経済指標（GDP、CPI、雇用統計）、為替 |
| **AI** | AI技術、機械学習、生成AI、AI企業（OpenAI、NVIDIA等）、AI投資、AI規制 |

**判定プロセス**:

```
[1] 記事のタイトルと要約を読む
    ↓
[2] 記事の主題を理解する
    ↓
[3] 上記テーマ判定基準に照らして該当するか判断
    ↓
[4] 該当する場合 → Phase 2.2へ
    該当しない場合 → スキップ
```

**判定例**:

| 記事タイトル | AIの判断 | テーマ |
|------------|---------|--------|
| "S&P 500 hits new record high amid tech rally" | 株価指数の動向について → 該当 | Index |
| "Fed signals rate cut in March meeting" | 金融政策・中央銀行の動向 → 該当 | Macro |
| "Apple reports Q4 earnings beat" | 個別企業の決算発表 → 該当 | Stock |
| "Banks face new capital requirements" | 銀行セクターの規制 → 該当 | Sector |
| "OpenAI launches new model capabilities" | AI企業の動向 → 該当 | AI |
| "Celebrity launches new clothing line" | 金融・経済と無関係 → 非該当 | - |

### ステップ3.2: 除外判断

以下のカテゴリに該当する記事は除外します（金融テーマに関連する場合を除く）:

- **スポーツ**: 試合結果、選手移籍など（ただし、スポーツ関連企業の決算等は対象）
- **エンターテインメント**: 映画、音楽、芸能ニュース
- **政治**: 選挙、内閣関連（ただし、金融政策・規制に関連する場合は対象）
- **一般ニュース**: 事故、災害、犯罪

### ステップ3.3: 重複チェック

> **🚨 重要: 重複チェックは最初に実行すること 🚨**
>
> テーママッチング後ではなく、**RSS取得直後（公開日時フィルタ後）**に重複チェックを行うこと。
> これにより、異なるフィードから取得された同一記事を早期に除外できる。

```python
# 除去対象のトラッキングパラメータ
# プレフィックス型（末尾 "_" で判定）と完全一致型の両方を含む
TRACKING_PARAMS = {
    # プレフィックス型（既存）
    "utm_", "guce_",
    # 完全一致型（既存）
    "ncid", "fbclid", "gclid",
    # 完全一致型（新規追加）
    "ref", "source", "campaign", "si", "mc_cid", "mc_eid",
    "sref", "taid", "mod", "cmpid",
}


def normalize_url(url: str) -> str:
    """URLを正規化して比較しやすくする（強化版）

    Parameters
    ----------
    url : str
        正規化対象のURL

    Returns
    -------
    str
        正規化されたURL

    Notes
    -----
    正規化ルール（比較時のみ適用。保存URLは変更しない）:
    - 末尾のスラッシュを除去
    - ホスト部分の小文字化
    - ``www.`` プレフィックスの除去
    - フラグメント（``#section``）の除去
    - 末尾 ``/index.html`` の除去
    - トラッキングパラメータの除去（TRACKING_PARAMS 参照）

    重要: この関数は重複チェックの比較用です。
    Issue作成時に使用するURLは、RSSオリジナルの link をそのまま使用してください。
    """
    if not url:
        return ""

    import urllib.parse

    # 末尾スラッシュを除去
    url = url.rstrip('/')

    # URLをパース
    parsed = urllib.parse.urlparse(url)

    # ホスト部分: 小文字化 + www. 除去
    netloc = parsed.netloc.lower()
    if netloc.startswith("www."):
        netloc = netloc[4:]

    # フラグメント除去
    parsed = parsed._replace(fragment="")

    # 末尾 /index.html 除去
    path = parsed.path
    if path.endswith("/index.html"):
        path = path[:-len("/index.html")]
    parsed = parsed._replace(path=path)

    # クエリパラメータからトラッキング用を除去
    if parsed.query:
        params = urllib.parse.parse_qs(parsed.query)
        filtered_params = {
            k: v for k, v in params.items()
            if not any(
                k.startswith(prefix) if prefix.endswith("_") else k == prefix
                for prefix in TRACKING_PARAMS
            )
        }
        new_query = urllib.parse.urlencode(filtered_params, doseq=True)
        parsed = parsed._replace(query=new_query)

    # 再構築
    normalized = urllib.parse.urlunparse(parsed._replace(netloc=netloc))

    return normalized


def calculate_title_similarity(title1: str, title2: str) -> float:
    """タイトルの類似度を計算（Jaccard係数）"""

    words1 = set(title1.lower().split())
    words2 = set(title2.lower().split())

    if not words1 or not words2:
        return 0.0

    common = words1.intersection(words2)
    total = words1.union(words2)

    return len(common) / len(total)


def is_duplicate(
    new_item: dict,
    existing_issues: list[dict],
    threshold: float = 0.85
) -> tuple[bool, int | None, str | None]:
    """既存Issueと重複しているかチェック

    Parameters
    ----------
    new_item : dict
        チェック対象の記事（linkフィールド必須）
    existing_issues : list[dict]
        既存のIssueリスト（article_urlフィールドを使用）
    threshold : float
        タイトル類似度の閾値

    Returns
    -------
    tuple[bool, int | None, str | None]
        (重複判定, 既存Issue番号, 重複理由)
        - 重複の場合: (True, issue_number, "URL一致" or "タイトル類似")
        - 重複なしの場合: (False, None, None)

    Notes
    -----
    1. まずURL完全一致をチェック（正規化後）
    2. 次にタイトル類似度をチェック
    3. existing_issuesは article_url フィールドを持つこと
       （オーケストレーターでprepare_existing_issues_with_urls()処理済み）
    """

    new_link = new_item.get('link', '')
    new_title = new_item.get('title', '')
    new_link_normalized = normalize_url(new_link)

    for issue in existing_issues:
        # ★ article_url フィールドを使用（bodyからではなく抽出済み）
        existing_url = issue.get('article_url', '')
        existing_url_normalized = normalize_url(existing_url)

        # URL完全一致（正規化後）
        if new_link_normalized and existing_url_normalized:
            if new_link_normalized == existing_url_normalized:
                return True, issue.get('number'), "URL一致"

        # タイトル類似度チェック
        issue_title = issue.get('title', '')
        similarity = calculate_title_similarity(new_title, issue_title)

        if similarity >= threshold:
            return True, issue.get('number'), f"タイトル類似({similarity:.0%})"

    return False, None, None


def check_duplicates_and_count(
    items: list[dict],
    existing_issues: list[dict],
    stats: dict,
    duplicate_articles: list[dict],
) -> list[dict]:
    """重複チェックを実行し、統計をカウントする

    Parameters
    ----------
    items : list[dict]
        チェック対象の記事リスト
    existing_issues : list[dict]
        既存のIssueリスト
    stats : dict
        統計カウンタ（duplicatesを更新）
    duplicate_articles : list[dict]
        重複記事リスト（追記される）

    Returns
    -------
    list[dict]
        重複を除いた記事リスト
    """

    non_duplicates = []

    for item in items:
        is_dup, issue_number, reason = is_duplicate(item, existing_issues)

        if is_dup:
            stats["duplicates"] += 1
            duplicate_articles.append({
                "title": item.get("title", ""),
                "url": item.get("link", ""),
                "existing_issue": issue_number,
                "reason": reason,
            })
            ログ出力: f"重複スキップ: {item.get('title', '')} → Issue #{issue_number} ({reason})"
        else:
            non_duplicates.append(item)

    return non_duplicates
```

## Phase 4: バッチ投稿（article-fetcherに委譲）

> **🚨 コンテキスト効率化のため、Issue作成を含む全処理をサブエージェントに委譲します 🚨**
>
> 記事本文の取得、日本語要約の生成、Issue作成、Project追加、Status/Date設定は
> すべて `news-article-fetcher` サブエージェント（Sonnet）が担当します。
> テーマエージェントはフィルタリング済み記事をバッチ分割して委譲するのみです。

### Phase 4 処理フロー概要

```
Phase 4: バッチ投稿（article-fetcherに委譲）
├── URL必須バリデーション
├── 5件ずつバッチ分割（公開日時の新しい順）
└── 各バッチ → news-article-fetcher（Sonnet）
    ├── ペイウォール/JS事前チェック（article_content_checker.py）
    ├── チェック通過 → WebFetch → 要約生成
    ├── チェック不通過 → スキップ（stats記録）
    ├── Issue作成 + close（.github/ISSUE_TEMPLATE/news-article.yml 準拠）
    ├── Project追加
    ├── Status設定
    └── 公開日時設定
```

### ステップ4.1: URL必須バリデーション【投稿前チェック】

> **🚨 Issue作成前に必ず実行すること 🚨**
>
> URLが存在しない記事は**絶対にIssue作成してはいけません**。
> バッチ分割前にURLなし記事を除外すること。

```python
def validate_url_for_issue(item: dict) -> tuple[bool, str | None]:
    """Issue作成前にURLの存在を検証する

    Parameters
    ----------
    item : dict
        RSSから取得した記事アイテム

    Returns
    -------
    tuple[bool, str | None]
        (検証成功, エラーメッセージ)

    Notes
    -----
    - URLがない記事はIssue作成しない
    - 空文字列もURLなしとして扱う
    """

    url = item.get("link", "").strip()

    if not url:
        return False, f"URLなし: {item.get('title', '不明')}"

    if not url.startswith(("http://", "https://")):
        return False, f"無効なURL形式: {url}"

    return True, None


# 使用例: バッチ分割前のフィルタリング
valid_items = []
for item in filtered_items:
    valid, error = validate_url_for_issue(item)
    if not valid:
        ログ出力: f"スキップ（URL必須違反）: {error}"
        stats["skipped_no_url"] += 1
        continue
    valid_items.append(item)
```

### ステップ4.2: バッチ処理

コンテキスト使用量を削減するため、記事を5件ずつ `news-article-fetcher` に委譲します。

| パラメータ | 値 |
|-----------|-----|
| バッチサイズ | 5件 |
| 処理順序 | 公開日時の新しい順 |
| 委譲先 | news-article-fetcher（Sonnet） |
| 委譲範囲 | ペイウォールチェック + WebFetch + 要約生成 + Issue作成 + Project追加 + Status/Date設定 |

#### バッチ処理フロー

```python
BATCH_SIZE = 5

# 公開日時の新しい順にソート
sorted_items = sorted(valid_items, key=lambda x: x.get("published", ""), reverse=True)

all_created = []
all_skipped = []

for i in range(0, len(sorted_items), BATCH_SIZE):
    batch = sorted_items[i:i + BATCH_SIZE]
    batch_num = (i // BATCH_SIZE) + 1
    ログ出力: f"バッチ {batch_num} 処理中... ({len(batch)}件)"

    # article-fetcher に委譲
    result = Task(
        subagent_type="news-article-fetcher",
        description=f"バッチ{batch_num}: 記事取得・要約・Issue作成",
        prompt=f"""以下の記事を処理してください。

入力:
{json.dumps({
    "articles": [
        {
            "url": item["link"],
            "title": item["title"],
            "summary": item.get("summary", ""),
            "feed_source": item.get("feed_source", ""),
            "published": item.get("published", "")
        }
        for item in batch
    ],
    "issue_config": issue_config  # build_issue_config() で構築済み
}, ensure_ascii=False, indent=2)}
""")

    # 結果集約
    all_created.extend(result.get("created_issues", []))
    all_skipped.extend(result.get("skipped", []))
    stats["created"] += result["stats"]["issue_created"]
    stats["failed"] += result["stats"]["issue_failed"]
```

#### バッチ間の状態管理

- 各バッチの結果（`created_issues`, `skipped`）はテーマエージェント側で集約
- 統計カウンタ（`stats`）は全バッチで共有・累積
- バッチ失敗時も次のバッチは継続
- 重複チェックはテーマエージェント側（バッチ分割前の Phase 3）で完了済み

### ステップ4.3: article-fetcher 入力仕様

#### articles[] の必須フィールド

| フィールド | 必須 | 説明 |
|-----------|------|------|
| `url` | Yes | 元記事URL（RSSのlinkフィールド） |
| `title` | Yes | 記事タイトル |
| `summary` | Yes | RSS概要（フォールバック用） |
| `feed_source` | Yes | フィード名 |
| `published` | Yes | 公開日時（ISO 8601） |

#### issue_config の必須フィールド

| フィールド | 説明 | 例 |
|-----------|------|-----|
| `theme_key` | テーマキー | `"index"` |
| `theme_label` | テーマ日本語名 | `"株価指数"` |
| `status_option_id` | StatusのOption ID | `"3925acc3"` |
| `project_id` | Project ID | `"PVT_kwHOBoK6AM4BMpw_"` |
| `project_number` | Project番号 | `15` |
| `project_owner` | Projectオーナー | `"YH-05"` |
| `repo` | リポジトリ | `"YH-05/quants"` |
| `status_field_id` | StatusフィールドID | `"PVTSSF_lAHOBoK6AM4BMpw_zg739ZE"` |
| `published_date_field_id` | 公開日フィールドID | `"PVTF_lAHOBoK6AM4BMpw_zg8BzrI"` |

#### issue_config の構築パターン

テーマエージェントはセッションファイルの `config` とテーマ固有設定を組み合わせて `issue_config` を構築します。

```python
def build_issue_config(
    session_data: dict,
    theme_key: str,
    theme_label: str,
    status_option_id: str,
) -> dict:
    """セッションデータからissue_configを構築する

    Parameters
    ----------
    session_data : dict
        オーケストレーターが作成したセッションファイルのデータ
    theme_key : str
        テーマキー（例: "index", "stock", "macro"）
    theme_label : str
        テーマ日本語名（例: "株価指数", "個別銘柄", "マクロ経済"）
    status_option_id : str
        GitHub ProjectのStatusフィールドのOption ID

    Returns
    -------
    dict
        article-fetcherに渡すissue_config
    """

    config = session_data["config"]
    return {
        "theme_key": theme_key,
        "theme_label": theme_label,
        "status_option_id": status_option_id,
        "project_id": config["project_id"],
        "project_number": config["project_number"],
        "project_owner": config["project_owner"],
        "repo": "YH-05/quants",
        "status_field_id": config["status_field_id"],
        "published_date_field_id": config["published_date_field_id"],
    }
```

**使用例**:

```python
# テーマエージェント内での使用
issue_config = build_issue_config(
    session_data=session_data,
    theme_key="index",
    theme_label="株価指数",
    status_option_id="3925acc3",
)
```

### ステップ4.4: article-fetcher の戻り値

article-fetcher は各バッチ処理後、以下のJSON形式で結果を返却します。

```json
{
  "created_issues": [
    {
      "issue_number": 200,
      "issue_url": "https://github.com/YH-05/quants/issues/200",
      "title": "[株価指数] S&P500が過去最高値を更新",
      "article_url": "https://www.cnbc.com/...",
      "published_date": "2026-01-19"
    }
  ],
  "skipped": [
    {
      "url": "https://...",
      "title": "...",
      "reason": "ペイウォール検出 (Tier 3: 'subscribe to continue' 検出, 本文320文字)"
    }
  ],
  "stats": {
    "total": 5,
    "content_check_passed": 4,
    "content_check_failed": 1,
    "fetch_success": 3,
    "fetch_failed": 1,
    "issue_created": 3,
    "issue_failed": 0,
    "skipped_paywall": 1,
    "skipped_format": 0
  }
}
```

> **🚨 URL設定の重要ルール 🚨**: `created_issues[].article_url` は
> RSSオリジナルのlinkをそのまま保持しています。WebFetchでリダイレクトが
> 発生しても、Issue記載のURLはこの値を使用してください。

### ステップ4.5: 要約フォーマット（4セクション構成）

article-fetcher が生成する要約は以下のフォーマットに従います:

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

**重要ルール**:
- 各セクションについて、**記事内に該当する情報がなければ「[記載なし]」と記述**する
- 情報を推測・創作してはいけない
- 記事に明示的に書かれている内容のみを記載する

| セクション | 内容 | 記載なしの例 |
|-----------|------|-------------|
| 概要 | 主要事実、数値データ | （常に何か記載できるはず） |
| 背景 | 経緯、原因、これまでの流れ | 速報で背景説明がない場合 |
| 市場への影響 | 株価・為替・債券への影響 | 影響の言及がない場合 |
| 今後の見通し | 予想、アナリスト見解 | 将来予測の言及がない場合 |

### ステップ4.6: article-fetcher の詳細仕様

サブエージェントの詳細な実装については以下を参照:
`.claude/agents/news-article-fetcher.md`

**article-fetcher 内部での処理（各記事に対して）**:
1. ペイウォール/JS事前チェック（`article_content_checker.py` 呼び出し）
2. チェック通過時: WebFetchで本文取得
3. 4セクション構成の日本語要約を生成
4. 英語タイトルを日本語に翻訳
5. Issue作成（`gh issue create` + close）-- `.github/ISSUE_TEMPLATE/news-article.yml` 準拠
6. Project追加（`gh project item-add`）
7. Status設定（GraphQL API）
8. 公開日時設定（GraphQL API）
9. チェック不通過時: `skipped` に記録しスキップ

> **重要な変更**: WebFetch失敗時のフォールバック要約生成（RSS summaryベース）は**廃止**。
> 本文が取得できない記事の要約は品質が担保できないため、Issue作成をスキップする。

## Phase 5: 結果報告

### 統計サマリー出力フォーマット【必須】

> **🚨 重複件数の出力は必須です 🚨**
>
> 処理統計には必ず「重複」の件数を含めてください。
> これにより、オーケストレーターが全テーマの重複件数を集計できます。

```markdown
## {theme_name} ニュース収集完了

### 処理統計

| 項目 | 件数 |
|------|------|
| 処理記事数 | {stats["processed"]} |
| 公開日時フィルタ除外 | {stats["date_filtered"]} |
| テーママッチ | {stats["matched"]} |
| **重複スキップ** | **{stats["duplicates"]}** |
| URLなしスキップ | {stats["skipped_no_url"]} |
| 新規投稿 | {stats["created"]} |
| 投稿失敗 | {stats["failed"]} |

### 投稿されたニュース

| Issue # | タイトル | 公開日 |
|---------|----------|--------|
{{#created_issues}}
| #{{issue_number}} | {{title}} | {{published_date}} |
{{/created_issues}}

{{#has_duplicates}}
### 重複でスキップされた記事

| 記事タイトル | 重複先 | 理由 |
|-------------|--------|------|
{{#duplicate_articles}}
| {{title}} | #{{existing_issue}} | {{reason}} |
{{/duplicate_articles}}
{{/has_duplicates}}
```

### 結果報告の実装例

```python
def generate_result_report(
    theme_name: str,
    stats: dict,
    created_issues: list[dict],
    duplicate_articles: list[dict],
) -> str:
    """結果レポートを生成する

    Parameters
    ----------
    theme_name : str
        テーマ名（日本語）
    stats : dict
        統計カウンタ
    created_issues : list[dict]
        作成したIssueのリスト
    duplicate_articles : list[dict]
        重複でスキップした記事のリスト

    Returns
    -------
    str
        Markdown形式のレポート
    """

    report = f"""## {theme_name} ニュース収集完了

### 処理統計

| 項目 | 件数 |
|------|------|
| 処理記事数 | {stats["processed"]} |
| 公開日時フィルタ除外 | {stats["date_filtered"]} |
| テーママッチ | {stats["matched"]} |
| **重複スキップ** | **{stats["duplicates"]}** |
| URLなしスキップ | {stats["skipped_no_url"]} |
| 新規投稿 | {stats["created"]} |
| 投稿失敗 | {stats["failed"]} |

### 投稿されたニュース

| Issue # | タイトル | 公開日 |
|---------|----------|--------|
"""

    for issue in created_issues:
        report += f"| #{issue['number']} | {issue['title']} | {issue['published_date']} |\n"

    # 重複記事の詳細（オプション）
    if duplicate_articles:
        report += f"""
### 重複でスキップされた記事（{len(duplicate_articles)}件）

| 記事タイトル | 重複先 | 理由 |
|-------------|--------|------|
"""
        for dup in duplicate_articles:
            report += f"| {dup['title'][:50]}... | #{dup['existing_issue']} | {dup['reason']} |\n"

    return report
```

## テーマ別Status ID一覧

| テーマ | Status名 | Option ID |
|--------|----------|-----------|
| index | Index | `3925acc3` |
| stock | Stock | `f762022e` |
| sector | Sector | `48762504` |
| macro | Macro Economics | `730034a5` |
| ai | AI | `6fbb43d0` |
| finance | Finance | `ac4a91b1` |

## GitHub Projectフィールド一覧

| フィールド名 | フィールドID | 型 | 用途 |
|-------------|-------------|-----|------|
| Status | `PVTSSF_lAHOBoK6AM4BMpw_zg739ZE` | SingleSelect | テーマ分類 |
| 公開日時 | `PVTF_lAHOBoK6AM4BMpw_zg8BzrI` | Date | ソート用 |

## 共通エラーハンドリング

### E001: MCPツール接続エラー

```python
def handle_mcp_error(feed_id: str, feed_title: str, error: Exception) -> list[dict]:
    """MCPツール接続失敗時のフォールバック処理

    Parameters
    ----------
    feed_id : str
        フィードID
    feed_title : str
        フィード名（ログ用）
    error : Exception
        発生したエラー

    Returns
    -------
    list[dict]
        ローカルから取得した記事（取得できない場合は空リスト）
    """

    ログ出力: f"警告: MCPツール接続失敗: {feed_title}"
    ログ出力: f"エラー詳細: {error}"
    ログ出力: "ローカルフォールバックを試行します"

    # ローカルデータから取得を試みる
    return load_from_local(feed_id, feed_title)
```

### E002: Issue作成エラー

```python
try:
    result = subprocess.run(
        ["gh", "issue", "create", ...],
        capture_output=True,
        text=True,
        check=True
    )
except subprocess.CalledProcessError as e:
    ログ出力: f"警告: Issue作成失敗: {item['title']}"
    ログ出力: f"エラー詳細: {e.stderr}"

    if "rate limit" in str(e.stderr).lower():
        ログ出力: "GitHub API レート制限に達しました。1時間待機してください。"

    failed += 1
    continue
```

### E003: 公開日時設定エラー

```python
try:
    result = subprocess.run(
        ["gh", "api", "graphql", "-f", f"query={mutation}"],
        capture_output=True,
        text=True,
        check=True
    )
except subprocess.CalledProcessError as e:
    ログ出力: f"警告: 公開日時設定失敗: Issue #{issue_number}"
    ログ出力: f"エラー詳細: {e.stderr}"
    ログ出力: "Issue作成は成功しています。手動で公開日時を設定してください。"
    continue
```

## チェックポイント機能（タイムアウト対策）

### 概要

バックグラウンドエージェントがタイムアウトで中途停止した場合に、処理を再開できるようにするための機能。

### チェックポイントファイル形式

**保存先**: `.tmp/checkpoints/news-collection-{timestamp}.json`

```json
{
  "checkpoint_id": "news-collection-20260129-143000",
  "created_at": "2026-01-29T14:30:00+09:00",
  "updated_at": "2026-01-29T14:35:00+09:00",
  "status": "in_progress",
  "config": {
    "days_back": 7,
    "batch_size": 10,
    "concurrency": 3,
    "timeout_minutes": 10
  },
  "themes": {
    "index": {
      "status": "completed",
      "started_at": "2026-01-29T14:30:05+09:00",
      "completed_at": "2026-01-29T14:32:00+09:00",
      "articles_processed": 8,
      "issues_created": 5,
      "issues_skipped": 3,
      "last_processed_index": 8
    },
    "stock": {
      "status": "in_progress",
      "started_at": "2026-01-29T14:32:05+09:00",
      "completed_at": null,
      "articles_processed": 3,
      "issues_created": 2,
      "issues_skipped": 1,
      "last_processed_index": 3
    },
    "sector": {
      "status": "pending",
      "started_at": null,
      "completed_at": null,
      "articles_processed": 0,
      "issues_created": 0,
      "issues_skipped": 0,
      "last_processed_index": 0
    }
  },
  "pending_articles": {
    "stock": [
      {
        "url": "https://...",
        "title": "...",
        "published": "..."
      }
    ]
  }
}
```

### チェックポイント保存タイミング

| イベント | 保存内容 |
|---------|---------|
| テーマ開始時 | `themes[theme].status = "in_progress"`, `started_at` |
| 記事処理後（5件ごと） | `articles_processed`, `last_processed_index` |
| テーマ完了時 | `themes[theme].status = "completed"`, `completed_at` |
| エラー発生時 | `themes[theme].status = "failed"`, エラー詳細 |

### 再開時の処理フロー

```
[1] チェックポイントファイルの検索
    └─ .tmp/checkpoints/ から最新のファイルを取得

[2] 再開可能か判定
    ├─ status == "completed" → 既に完了、スキップ
    ├─ status == "failed" → エラー表示、手動対応要求
    └─ status == "in_progress" → 再開処理へ

[3] 再開対象テーマの特定
    ├─ status == "in_progress" → last_processed_index から再開
    └─ status == "pending" → 最初から開始

[4] pending_articles からデータ復元
    └─ 未処理記事をロードして処理続行
```

### 再開オプション

```bash
# 前回のチェックポイントから再開
/finance-news-workflow --resume

# 特定のチェックポイントから再開
/finance-news-workflow --resume --checkpoint-id "news-collection-20260129-143000"

# 失敗したテーマのみ再実行
/finance-news-workflow --themes "stock,sector" --resume
```

### バッチサイズ制限

タイムアウトを防ぐため、各テーマの処理記事数を制限:

```python
# 設定から取得
batch_size = config.get("execution", {}).get("batch_size", 10)
max_articles = config.get("execution", {}).get("max_articles_per_theme", 20)

# 記事リストを制限
articles = sorted(articles, key=lambda x: x["published"], reverse=True)
articles = articles[:max_articles]

# バッチ分割して処理
for i in range(0, len(articles), batch_size):
    batch = articles[i:i + batch_size]
    # チェックポイント保存
    save_checkpoint(checkpoint_id, theme, i + len(batch))
    # バッチ処理
    process_batch(batch)
```

### 並列度制御

同時実行するテーマ数を制限してリソース消費を抑制:

```python
# 設定から取得
concurrency = config.get("execution", {}).get("concurrency", 3)

# テーマをグループに分割
all_themes = ["index", "stock", "sector", "macro_cnbc", "macro_other",
              "ai_cnbc", "ai_nasdaq", "ai_tech",
              "finance_cnbc", "finance_nasdaq", "finance_other"]

# concurrency 件ずつ並列実行
for i in range(0, len(all_themes), concurrency):
    batch_themes = all_themes[i:i + concurrency]
    # 並列実行（Task tool with run_in_background=True）
    tasks = [
        Task(
            subagent_type=f"finance-news-{theme}",
            run_in_background=True,
            ...
        )
        for theme in batch_themes
    ]
    # 完了待ち
    for task in tasks:
        result = TaskOutput(task_id=task.id)
```

## 参考資料

- **Issueテンプレート**: `.github/ISSUE_TEMPLATE/news-article.yml`（YAML形式、GitHub UI用）
- **オーケストレーター**: `.claude/agents/finance-news-orchestrator.md`
- **コマンド**: `.claude/commands/collect-finance-news.md`
- **GitHub Project**: https://github.com/users/YH-05/projects/15
