# finance_news_workflow の信頼性向上（RSS UA / Summarizer 空レスポンス / 重複チェック前倒し）

## 問題概要

`finance_news_workflow.py` のフェーズ 1（RSS 収集）で、Yahoo Finance が `429 Too Many Requests`、Nasdaq 系フィードが接続拒否（空エラー）を返す。

### 発生エラー

```
[error] Feed collection failed [news.collectors.rss]
  error="Client error '429 Too Many Requests' ..."
  feed_name='Yahoo Finance'
  feed_url=https://finance.yahoo.com/news/rssindex

[error] Feed collection failed [news.collectors.rss]
  error=
  feed_name='Nasdaq Stock News'
  feed_url='https://www.nasdaq.com/feed/rssoutbound?category=stocks'

[error] Feed collection failed [news.collectors.rss]
  error=
  feed_name='Nasdaq ETFs'
  feed_url='https://www.nasdaq.com/feed/rssoutbound?category=etfs'

[error] Feed collection failed [news.collectors.rss]
  error=
  feed_name='Nasdaq Markets'
  feed_url='https://www.nasdaq.com/feed/rssoutbound?category=markets'
```

### 根本原因

`RSSCollector` が `httpx.AsyncClient` を User-Agent ヘッダーなしで生成している。

```python
# src/news/collectors/rss.py:155
async with httpx.AsyncClient(timeout=30.0) as client:
```

httpx のデフォルト User-Agent は `python-httpx/0.x.x` であり、Yahoo Finance・Nasdaq はこれをボットと判定してリクエストを拒否する。

### 現状の UA 設定状況

| フェーズ | コンポーネント | UA 設定 | 状態 |
|---------|---------------|---------|------|
| 1. 収集 | `RSSCollector` | **なし** | httpx デフォルト (`python-httpx/...`) |
| 2. 抽出 | `TrafilaturaExtractor` | **あり** | `config.extraction.user_agent_rotation` を使用 |
| 3. 要約 | `Summarizer` | N/A | Claude API のため不要 |
| 4. 公開 | `Publisher` | N/A | gh CLI のため不要 |

フェーズ 2 では `extraction.user_agent_rotation` が正しく参照されブラウザ UA が使用されるが、フェーズ 1 では完全に未設定。

### ワークフローへの影響

フェーズ 1 のフィードエラーはフィード単位で `except` → `continue` されるため（`src/news/collectors/rss.py:169`）、ワークフロー自体は**停止せず続行する**。ただし以下の問題が発生する。

#### 1. 4フィード分の記事がサイレントに欠落する

該当フィードの記事がフェーズ 2 以降に一切渡らず、GitHub Issue として公開されない。

| フィード | カテゴリ | 失われる記事 |
|---------|---------|-------------|
| Yahoo Finance | market | Yahoo Finance 発のニュース全件 |
| Nasdaq Stock News | stock | Nasdaq 個別株ニュース全件 |
| Nasdaq ETFs | etfs | Nasdaq ETF ニュース全件 |
| Nasdaq Markets | market | Nasdaq 市場ニュース全件 |

#### 2. 欠落がコンソール出力に表示されない

`print_failure_summary()` は抽出・要約・公開の失敗のみを表示する。フィードエラーは `WorkflowResult.feed_errors` に記録されるが、最終サマリーには含まれない。欠落に気付くには実行時のログ出力（`[error] Feed collection failed`）を確認するか、`feed_errors` フィールドの件数を見る必要がある。

#### 3. 成功フィードへの影響はなし

残りの成功したフィード（504件）はフェーズ 2 → 3 → 4 と正常に処理され、Issue 作成まで完了する。

---

## 変更対象ファイル

| ファイル | 変更内容 |
|----------|----------|
| `src/news/config/models.py` | `RssConfig` に `user_agent_rotation` フィールド追加 |
| `src/news/collectors/rss.py` | `httpx.AsyncClient` に UA ヘッダーを設定 |
| `data/config/news-collection-config.yaml` | `rss` セクションに `user_agent_rotation` 設定追加 |
| `tests/news/unit/collectors/test_rss.py` | UA ヘッダー送信のテスト追加 |

---

## 修正方針

既存の `UserAgentRotationConfig` モデルと `extraction.user_agent_rotation` の設計パターンを `RssConfig` にも適用する。フェーズ 2 で実績のある仕組みをそのまま再利用し、設定ファイルでは同じ UA リストを `rss` セクション内にも配置する。

### 方針選定の理由

| 案 | 内容 | 採否 | 理由 |
|----|------|------|------|
| A. `RssConfig` に専用 UA 設定を追加 | `rss.user_agent_rotation` | **採用** | フェーズごとに独立して設定可能。既存の `extraction` 設定に影響なし |
| B. `extraction.user_agent_rotation` を共有参照 | オーケストレータが `extraction` の UA を `RSSCollector` に注入 | 不採用 | 設定の責務が混在する。RSS 収集と本文抽出は独立した関心事 |
| C. トップレベルに共通 UA 設定を新設 | `user_agent_rotation` をルートに配置 | 不採用 | 既存設定ファイルの構造変更が大きい。後方互換性の問題 |

---

## 修正内容

### 1. `src/news/config/models.py` — `RssConfig` にフィールド追加

```python
class RssConfig(BaseModel):
    presets_file: str = Field(
        ...,
        description="Path to the RSS presets JSON file",
    )
    retry: RssRetryConfig = Field(
        default_factory=RssRetryConfig,
        description="Retry configuration for feed collection",
    )
    # ---- 追加 ----
    user_agent_rotation: UserAgentRotationConfig = Field(
        default_factory=UserAgentRotationConfig,
        description="User-Agent rotation configuration for RSS feed fetching",
    )
```

`UserAgentRotationConfig` は既存モデル（`src/news/config/models.py:554`）をそのまま再利用する。新規モデル定義は不要。

### 2. `src/news/collectors/rss.py` — UA ヘッダーの設定

#### 2.1 `__init__` に UA 設定参照を追加

```python
def __init__(self, config: NewsWorkflowConfig) -> None:
    self._config = config
    self._parser = FeedParser()
    self._domain_filter = config.domain_filtering
    self._feed_errors: list[FeedError] = []
    # ---- 追加 ----
    self._ua_config = config.rss.user_agent_rotation
```

#### 2.2 `collect()` の `httpx.AsyncClient` にヘッダーを設定

**変更前**（155行目）:
```python
async with httpx.AsyncClient(timeout=30.0) as client:
```

**変更後**:
```python
headers = self._build_headers()
async with httpx.AsyncClient(timeout=30.0, headers=headers) as client:
```

#### 2.3 `_build_headers()` メソッドを新規追加

```python
def _build_headers(self) -> dict[str, str]:
    """Build HTTP headers with User-Agent for RSS feed requests.

    Returns
    -------
    dict[str, str]
        HTTP headers dictionary. If UA rotation is enabled,
        includes a randomly selected browser User-Agent.
    """
    headers: dict[str, str] = {
        "Accept": "application/rss+xml, application/xml, text/xml, */*",
    }

    if self._ua_config:
        ua = self._ua_config.get_random_user_agent()
        if ua:
            headers["User-Agent"] = ua
            logger.debug(
                "Using custom User-Agent for RSS collection",
                user_agent=ua[:50] + "..." if len(ua) > 50 else ua,
            )

    return headers
```

**設計上のポイント**:
- `Accept` ヘッダーも追加する。RSS/XML を明示的に受け入れることで、サーバーが適切な Content-Type で応答しやすくなる
- UA はクライアント生成時（全フィード共通）に 1 回設定する。フィードごとのローテーションは不要（短時間での同一 IP からの異なる UA はかえって不審と判定される可能性がある）

### 3. `data/config/news-collection-config.yaml` — 設定追加

```yaml
rss:
  presets_file: "data/config/rss-presets.json"

  # User-Agent ローテーション（ボット検出回避）
  user_agent_rotation:
    enabled: true
    user_agents:
      # Chrome (Windows)
      - "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
      # Chrome (macOS)
      - "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
      # Firefox (Windows)
      - "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0"
      # Safari (macOS)
      - "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.2 Safari/605.1.15"
      # Chrome (Linux)
      - "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
```

`extraction.user_agent_rotation.user_agents` と同じリストを使用する。設定ファイル上は重複するが、フェーズ間の設定独立性を優先する。

### 4. テスト追加

`tests/news/unit/collectors/test_rss.py` に以下のテストケースを追加:

| テスト名 | 検証内容 |
|---------|---------|
| `test_正常系_ブラウザUAでリクエストを送信` | httpx リクエストに UA ヘッダーが含まれることを検証 |
| `test_正常系_UA無効時はデフォルトUAで送信` | `enabled: false` 時に UA ヘッダーが設定されないことを検証 |
| `test_正常系_AcceptヘッダーにRSS形式が含まれる` | Accept ヘッダーに `application/rss+xml` が含まれることを検証 |

**テスト方法**: 既存テストと一貫して `patch("httpx.AsyncClient")` を使用し、コンストラクタに渡された `headers` 引数を検証する。

```python
# 検証例
mock_client_class.assert_called_once_with(
    timeout=30.0,
    headers={
        "Accept": "application/rss+xml, application/xml, text/xml, */*",
        "User-Agent": ANY,  # ランダム選択のため ANY で検証
    },
)
```

---

## 実装チェックリスト

- [ ] `src/news/config/models.py`: `RssConfig` に `user_agent_rotation: UserAgentRotationConfig` フィールド追加 → [#3075](https://github.com/YH-05/quants/issues/3075)
- [ ] `src/news/collectors/rss.py`: `__init__` に `self._ua_config` 追加 → [#3076](https://github.com/YH-05/quants/issues/3076)
- [ ] `src/news/collectors/rss.py`: `_build_headers()` メソッド追加 → [#3076](https://github.com/YH-05/quants/issues/3076)
- [ ] `src/news/collectors/rss.py`: `httpx.AsyncClient` に `headers` 引数追加 → [#3076](https://github.com/YH-05/quants/issues/3076)
- [ ] `data/config/news-collection-config.yaml`: `rss.user_agent_rotation` セクション追加 → [#3077](https://github.com/YH-05/quants/issues/3077)
- [ ] `tests/news/unit/collectors/test_rss.py`: UA ヘッダー検証テスト追加 → [#3078](https://github.com/YH-05/quants/issues/3078)
- [ ] `make check-all` が成功することを確認
- [ ] Yahoo Finance フィード（`https://finance.yahoo.com/news/rssindex`）で 429 が解消されることを確認
- [ ] Nasdaq フィード（3 件）で接続拒否が解消されることを確認

---

## 補足: フィードごとの UA ローテーションを行わない理由

フィードごとに異なる UA を設定する方式（`_fetch_feed` 内でリクエストごとにローテーション）も検討したが、以下の理由で不採用とした:

1. **フィンガープリンティング対策**: 同一 IP から短時間で異なる UA が送信されると、逆にボット判定されるリスクが上がる
2. **httpx の設計**: `AsyncClient` はセッション単位でヘッダーを保持する設計であり、リクエストごとの上書きはコードの複雑性が増す
3. **実用上の十分性**: 実行ごとにランダムな 1 つの UA を使用すれば、ボット検出は十分に回避できる

ワークフローの実行間隔（通常 1 日 1 回以上）を考慮すると、セッション単位のローテーションで十分。

---

## 追加改善: 重複チェックのフェーズ前倒し

### 現状の問題

現在のパイプラインでは、重複チェックはフェーズ 4（`Publisher.publish_batch`）内で実行される。つまり、重複記事に対してもフェーズ 2（本文抽出）とフェーズ 3（AI 要約）が実行され、リソースが無駄に消費される。

```
【現状の処理順序】 src/news/orchestrator.py:186-269

収集(504件)
  → ステータスフィルタ / 記事数制限
  → 抽出（504件全てに HTTP リクエスト + trafilatura 処理）
  → 要約（抽出成功分全てに Claude API 呼出）
  → 重複チェック + 公開（ここで初めて重複を除外）
```

重複チェックに使う URL は `CollectedArticle.url` としてフェーズ 1 完了時点で確定しているため、後続フェーズに渡す前に除外できる。

### 改善案

重複チェックをフェーズ 1 直後（フェーズ 2 の前）に移動する。

```
【改善後の処理順序】

収集(504件)
  → ステータスフィルタ / 記事数制限
  → 重複チェック（既存 Issue の URL と照合、重複を除外）
  → 抽出（新規記事のみ）
  → 要約（新規記事のみ）
  → 公開（重複チェック済みのためスキップなし）
```

### 節約できるコスト

重複記事 1 件あたり、以下の処理をスキップできる:

| フェーズ | 1 件あたりのコスト | 節約 |
|---------|-------------------|------|
| 2. 抽出 | HTTP リクエスト 1〜4 回（リトライ含む）+ trafilatura | 節約可 |
| 3. 要約 | Claude API 呼出 1 回（最大 60s × リトライ 3 回） | **最も効果大** |

フェーズ 3 の Claude API 呼出が処理時間・コストともに最も大きいため、ここを削減する効果が高い。

### 変更対象ファイル

| ファイル | 変更内容 |
|----------|----------|
| `src/news/orchestrator.py` | フェーズ 1 後に重複チェックステップを追加 |
| `src/news/publisher.py` | `_get_existing_issues()` と `_is_duplicate()` を外部から呼び出し可能にする |
| `src/news/publisher.py` | `_get_existing_issues()` を `asyncio.create_subprocess_exec` で非同期化 |
| `src/news/publisher.py` | `--limit 500` 制限を撤廃し、対象期間の全 Issue を取得（ページネーション対応） |
| `src/news/models.py` | `WorkflowResult` に `total_early_duplicates` フィールド追加 |
| `tests/news/unit/test_orchestrator.py` | 重複チェック前倒しの検証テスト追加（新規作成） |

### 修正内容

#### 1. `src/news/publisher.py` — 重複チェックメソッドの公開 + 非同期化 + ページネーション

`_get_existing_issues()` を外部から呼び出せるよう公開メソッド化する。`_is_duplicate()` も URL ベースの判定を `CollectedArticle` で使えるよう汎用化する。

##### 1.1 非同期化: `subprocess.run` → `asyncio.create_subprocess_exec`

現在の `_get_existing_issues()` は `subprocess.run`（同期呼出）を使用しており、`async` コンテキストでイベントループをブロックする。`asyncio.create_subprocess_exec` に置き換えて完全な非同期化を行う。

```python
async def _get_existing_issues(self, days: int = 7) -> set[str]:
    since_date = datetime.now(timezone.utc) - timedelta(days=days)

    proc = await asyncio.create_subprocess_exec(
        "gh", "issue", "list",
        "--repo", self._repo,
        "--state", "all",
        "--limit", "1000",  # ページあたりの取得件数
        "--json", "body,createdAt",
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    stdout, stderr = await proc.communicate()

    if proc.returncode != 0:
        logger.error("Failed to fetch issues", stderr=stderr.decode())
        return set()

    issues = json.loads(stdout.decode())
    # ... URL 抽出処理（既存ロジック）
```

##### 1.2 ページネーション: `--limit 500` 制限の撤廃

`gh issue list` の `--limit` を十分大きな値にするか、`--paginate` オプションと `gh api` を使用して対象期間の全 Issue を取得する。

```python
# gh api を使用したページネーション対応
proc = await asyncio.create_subprocess_exec(
    "gh", "api",
    "--paginate",
    f"/repos/{self._repo}/issues",
    "--jq", ".[].body",
    "-q", f".[] | select(.created_at >= \"{since_date.isoformat()}\")",
    stdout=asyncio.subprocess.PIPE,
    stderr=asyncio.subprocess.PIPE,
)
```

**注意**: 具体的なページネーション実装は `gh issue list --limit` の上限引き上げか `gh api --paginate` のいずれかを実装時に選定する。

##### 1.3 公開メソッドの追加

```python
async def get_existing_urls(self, days: int | None = None) -> set[str]:
    """直近N日の既存 Issue から記事 URL を取得する。

    Parameters
    ----------
    days : int | None, optional
        取得対象期間。None の場合は config の duplicate_check_days を使用。

    Returns
    -------
    set[str]
        既存 Issue に含まれる記事 URL のセット。
    """
    check_days = days or self._config.duplicate_check_days
    return await self._get_existing_issues(days=check_days)
```

```python
# URL ベースの重複判定（CollectedArticle 用）
def is_duplicate_url(self, url: str, existing_urls: set[str]) -> bool:
    """URL が既存 Issue に含まれるか判定する。"""
    return url in existing_urls
```

#### 2. `src/news/orchestrator.py` — フェーズ 1 後に重複チェックを挿入

`run()` メソッドのフェーズ 1（収集）直後、フェーズ 2（抽出）の前に重複チェックステップを追加する。

**変更箇所**: `run()` メソッド内、ステータスフィルタ/記事数制限の後（202行目付近）

```python
# Apply max_articles limit
if max_articles and len(collected) > max_articles:
    collected = collected[:max_articles]
    print(f"  記事数制限適用: {len(collected)}件")

# ---- 追加: 重複チェック（フェーズ2の前に実行） ----
existing_urls = await self._publisher.get_existing_urls()
before_dedup = len(collected)
collected = [
    a for a in collected
    if not self._publisher.is_duplicate_url(str(a.url), existing_urls)
]
dedup_count = before_dedup - len(collected)
if dedup_count > 0:
    print(f"  重複除外: {before_dedup} -> {len(collected)}件 (重複: {dedup_count}件)")

if not collected:
    print("  -> 処理対象の記事がありません")
    # ... 既存の早期リターン処理
```

#### 3. `Publisher.publish_batch()` — 重複チェックの二重実行を防止

重複チェックがフェーズ 1 後で完了しているため、`publish_batch()` 内の重複チェックは冗長になる。ただし安全策として残し、ログレベルを下げる。

```python
# publish_batch() 内の既存重複チェック（変更なし、安全策として維持）
if self._is_duplicate(article, existing_urls):
    duplicate_count += 1
    logger.debug(  # info → debug に変更（通常到達しないため）
        "Duplicate detected in publish_batch (safety check)",
        article_url=str(article.extracted.collected.url),
    )
    # ... 既存の DUPLICATE 処理
```

### WorkflowResult への影響

重複チェックの前倒しにより `total_duplicates` の計上位置が変わる。現状は `PublishedArticle` の `DUPLICATE` ステータスから計上しているが、改善後はフェーズ 1 の段階で除外されるため `published` リストに含まれなくなる。

**対応方法**: `WorkflowResult` モデルに `total_early_duplicates` フィールドを新設し、`_build_result()` で受け取って設定する。既存の `total_duplicates`（フェーズ 4 での重複検出）とは分離する。

##### `src/news/models.py` — `WorkflowResult` にフィールド追加

```python
class WorkflowResult(BaseModel):
    # ... 既存フィールド ...
    total_duplicates: int  # フェーズ 4 での重複検出数（安全策として残存）
    # ---- 追加 ----
    total_early_duplicates: int = Field(
        default=0,
        description="Number of articles excluded by early duplicate check (before extraction)",
    )
```

##### `src/news/orchestrator.py` — `_build_result()` のシグネチャ変更

```python
def _build_result(
    self,
    collected: list[CollectedArticle],
    extracted: list[ExtractedArticle],
    summarized: list[SummarizedArticle],
    published: list[PublishedArticle],
    started_at: datetime,
    finished_at: datetime,
    early_duplicates: int = 0,  # 追加
) -> WorkflowResult:
    # ... 既存の集計ロジック ...
    return WorkflowResult(
        # ... 既存フィールド ...
        total_early_duplicates=early_duplicates,
    )
```

##### `run()` 内での呼び出し

```python
result = self._build_result(
    collected=collected,
    extracted=extracted,
    summarized=summarized,
    published=published,
    started_at=started_at,
    finished_at=finished_at,
    early_duplicates=dedup_count,
)
```

##### 最終サマリーの表示更新

```python
if result.total_early_duplicates > 0:
    print(f"  重複除外（早期）: {result.total_early_duplicates}件")
if result.total_duplicates > 0:
    print(f"  重複（公開時）: {result.total_duplicates}件")
```

### テスト追加

| テスト名 | 検証内容 |
|---------|---------|
| `test_正常系_重複記事がフェーズ2前に除外される` | 既存 URL と一致する記事が抽出対象から除外されることを検証 |
| `test_正常系_重複除外後に記事が0件で早期リターン` | 全記事が重複の場合に空の `WorkflowResult` が返ることを検証 |
| `test_正常系_重複件数がWorkflowResultに反映される` | `total_early_duplicates` に前倒しチェックの除外数が含まれることを検証 |

### 実装チェックリスト

- [ ] `src/news/publisher.py`: `_get_existing_issues()` を `asyncio.create_subprocess_exec` で非同期化 → [#3079](https://github.com/YH-05/quants/issues/3079)
- [ ] `src/news/publisher.py`: `--limit 500` 制限を撤廃し、対象期間の全 Issue を取得（ページネーション対応） → [#3079](https://github.com/YH-05/quants/issues/3079)
- [ ] `src/news/publisher.py`: `get_existing_urls()` 公開メソッド追加 → [#3079](https://github.com/YH-05/quants/issues/3079)
- [ ] `src/news/publisher.py`: `is_duplicate_url()` 公開メソッド追加 → [#3079](https://github.com/YH-05/quants/issues/3079)
- [ ] `src/news/models.py`: `WorkflowResult` に `total_early_duplicates` フィールド追加 → [#3080](https://github.com/YH-05/quants/issues/3080)
- [ ] `src/news/orchestrator.py`: フェーズ 1 後に重複チェックステップを挿入 → [#3081](https://github.com/YH-05/quants/issues/3081)
- [ ] `src/news/orchestrator.py`: `_build_result()` に `early_duplicates` パラメータ追加 → [#3081](https://github.com/YH-05/quants/issues/3081)
- [ ] `src/news/orchestrator.py`: 最終サマリーに早期重複除外件数を表示 → [#3081](https://github.com/YH-05/quants/issues/3081)
- [ ] `src/news/publisher.py`: `publish_batch()` 内の重複チェックログレベルを `debug` に変更 → [#3079](https://github.com/YH-05/quants/issues/3079)
- [ ] `tests/news/unit/test_orchestrator.py`: 重複チェック前倒しのテスト追加（新規作成） → [#3082](https://github.com/YH-05/quants/issues/3082)
- [ ] `make check-all` が成功することを確認

---

## 追加改善: Summarizer の空レスポンスによる JSON パースエラー修正

### 問題概要

`finance_news_workflow.py` のフェーズ 3（AI 要約）で、Claude Agent SDK からの空レスポンスにより JSON パースエラーが頻発する。

### 発生エラー

```
[error    ] Parse/validation error         [news.summarizer]
  article_url=https://www.cnbc.com/2026/02/03/gold-and-silver-rebound-after-historic-wipeout-as-analysts-say-thematic-drivers-stay-intact-.html
  error='JSON parse error: Expecting value: line 1 column 1 (char 0)'
  module=summarizer

  ERROR[130/240] Gold and silver rebound, pulling global ... - JSON parse error: Expecting value: line 1 column 1 (char 0)

[error    ] Summarization failed           [news.orchestrator]
  error='JSON parse error: Expecting value: line 1 column 1 (char 0)'
  module=orchestrator
  url=https://www.cnbc.com/2026/02/03/gold-and-silver-rebound-after-historic-wipeout-as-analysts-say-thematic-drivers-stay-intact-.html

  ERROR[131/240] From PopMart to JD.com: Britain and Chin... - JSON parse error: Expecting value: line 1 column 1 (char 0)
```

`Expecting value: line 1 column 1 (char 0)` は `json.loads("")`（空文字列のパース）で発生する固有のエラーメッセージ。

### 根本原因

3つの原因が重なって発生している。

#### 原因 1: Claude API のレート制限（最も可能性が高い）

`claude-agent-sdk` の `AssistantMessage` には `error` フィールドがある。

```python
# .venv/lib/python3.12/site-packages/claude_agent_sdk/types.py
@dataclass
class AssistantMessage:
    content: list[ContentBlock]
    model: str
    error: AssistantMessageError | None = None  # "rate_limit", "authentication_failed" 等
```

レート制限時、SDK は `error="rate_limit"` が設定された `AssistantMessage` を返すが、`content` に `TextBlock` が含まれない。エラーログで `[130/240]`, `[131/240]` と **連続して失敗** していることから、240記事の大量処理中に API レート制限に到達していると推定される。

#### 原因 2: `_call_claude_sdk()` が `AssistantMessage.error` をチェックしていない

```python
# src/news/summarizer.py:380-393
response_parts: list[str] = []
async for message in query(prompt=prompt, options=options):
    if isinstance(message, AssistantMessage):
        for block in message.content:
            if isinstance(block, TextBlock):
                response_parts.append(block.text)

result = "".join(response_parts)  # ← レート制限時は空文字列 "" になる
return result
```

`query()` は5種類のメッセージを yield するが、コードは `AssistantMessage` 内の `TextBlock` のみを収集している。

```
query() が yield するメッセージ型:
├── UserMessage         ← 無視
├── AssistantMessage    ← ここだけ見ている
│   ├── content:
│   │   ├── TextBlock       ← これだけ拾っている
│   │   ├── ThinkingBlock   ← 無視
│   │   ├── ToolUseBlock    ← 無視
│   │   └── ToolResultBlock ← 無視
│   └── error: "rate_limit" | ... ← チェックしていない
├── SystemMessage       ← 無視
├── ResultMessage       ← 無視（is_error, result フィールドあり）
└── StreamEvent         ← 無視
```

レート制限やその他のエラーで `TextBlock` が含まれない場合、`response_parts` は空のまま `""` を返す。

#### 原因 3: `_parse_response()` に空文字列チェックがない

```python
# src/news/summarizer.py:436-448
json_match = re.search(r"```json\s*(.*?)\s*```", response_text, re.DOTALL)
if json_match:
    json_str = json_match.group(1)
else:
    json_str = response_text.strip()  # "" → ""

data = json.loads(json_str)  # json.loads("") → JSONDecodeError
```

空文字列の早期検出がないため、`json.loads("")` まで到達して `JSONDecodeError` が発生する。

### エラーフロー

```
Claude API → レート制限 → AssistantMessage(error="rate_limit", content=[])
→ _call_claude_sdk(): TextBlock なし → response_parts=[] → return ""
→ _parse_response(""): json.loads("") → JSONDecodeError
→ ValueError("JSON parse error: Expecting value: line 1 column 1 (char 0)")
→ summarize() の except ValueError → リトライなしで即 FAILED
```

### 現在のリトライ判定の問題

```python
# src/news/summarizer.py:175-256（簡略化）
for attempt in range(self._max_retries):
    try:
        response_text = await self._call_claude_sdk(prompt)
        summary = self._parse_response(response_text)
        return SummarizedArticle(status=SUCCESS)

    except ValueError as e:
        # JSON parse error or Pydantic validation error - don't retry  ← ★問題
        return SummarizedArticle(status=FAILED)  # 即座に失敗

    except asyncio.TimeoutError:
        # タイムアウト → リトライする
        ...

    except Exception as e:
        # ProcessError, CLIConnectionError 等 → リトライする
        ...
```

空レスポンス起因の `ValueError` は **一時的なエラー**（レート制限等）が原因の可能性が高いのに、`ValueError` を「パースエラー = 永続的エラー」と判定してリトライしていない。タイムアウトや `ProcessError` はリトライするのに、空レスポンスはリトライしないという非対称性がある。

### `ResultMessage` の未活用

`query()` は最後に `ResultMessage` を yield する。

```python
# claude-agent-sdk types
@dataclass
class ResultMessage:
    is_error: bool      # クエリ全体が失敗したか
    result: str | None  # 最終結果テキスト
    duration_ms: int
    total_cost_usd: float | None
    ...
```

現在のコードはこれを完全に無視している。`is_error=True` でも検知できず、`result` に実際のテキストが入っていても取得しない。

### ワークフローへの影響

240記事中の要約失敗は `WorkflowResult.summarization_failures` に記録されるが、失敗した記事はフェーズ 4（公開）に進まない。レート制限が原因の場合、リトライすれば成功する可能性が高いにもかかわらず、即座に失敗扱いとなり記事が欠落する。

---

### 変更対象ファイル

| ファイル | 変更内容 |
|----------|----------|
| `src/news/summarizer.py` | 空レスポンス検出、`AssistantMessage.error` チェック、リトライ判定改善 |
| `src/news/summarizer.py` | `ResultMessage` のインポート追加 |
| `tests/news/unit/summarizers/test_summarizer.py` | 空レスポンス・レート制限エラーのテスト追加 |

---

### 修正方針

空レスポンスの原因を正確に識別し、一時的なエラー（レート制限等）はリトライ対象にする。永続的なパースエラー（不正な JSON 形式）とは区別する。

#### 方針選定の理由

| 案 | 内容 | 採否 | 理由 |
|----|------|------|------|
| A. 空レスポンスをリトライ対象にする | `ValueError` を細分化し、空レスポンス起因はリトライ | **採用** | 一時的エラーの回復率が向上。既存のリトライ基盤を活用 |
| B. `ResultMessage` を正式に活用する | `is_error`/`result` を参照 | **採用** | エラー原因の正確な特定が可能。追加情報でデバッグ向上 |
| C. 並列数を下げる | `concurrency: 3` → `1` | 不採用 | 処理時間が 3 倍に増加。根本解決ではない |
| D. レート制限時の長時間バックオフ | 空レスポンス検出時に 30s 待機 | **部分採用** | レート制限回復には有効だが、他の一時的エラーには過剰 |

---

### 修正内容

#### 1. `src/news/summarizer.py` — 空レスポンス専用例外の新設

```python
class EmptyResponseError(Exception):
    """Claude Agent SDK が空レスポンスを返した場合の例外。

    レート制限やAPIエラーなど一時的な原因で発生するため、
    リトライ対象として扱う。

    Parameters
    ----------
    reason : str
        空レスポンスの推定原因。
    """

    def __init__(self, reason: str = "unknown") -> None:
        self.reason = reason
        super().__init__(f"Empty response from Claude SDK (reason: {reason})")
```

#### 2. `src/news/summarizer.py` — `ResultMessage` のインポート追加

現在のインポート（`AssistantMessage`, `TextBlock` のみ）に `ResultMessage` を追加する。

```python
from claude_agent_sdk.types import AssistantMessage, ResultMessage, TextBlock
```

#### 3. `src/news/summarizer.py` — `_call_claude_sdk()` の改善

**変更前**（380-393行目）:
```python
response_parts: list[str] = []
async for message in query(prompt=prompt, options=options):
    if isinstance(message, AssistantMessage):
        for block in message.content:
            if isinstance(block, TextBlock):
                response_parts.append(block.text)

result = "".join(response_parts)
return result
```

**変更後**:
```python
response_parts: list[str] = []
assistant_error: str | None = None
result_message: ResultMessage | None = None

async for message in query(prompt=prompt, options=options):
    if isinstance(message, AssistantMessage):
        # AssistantMessage.error のチェック
        if message.error is not None:
            assistant_error = str(message.error)
            logger.warning(
                "AssistantMessage contains error",
                error=assistant_error,
            )
        for block in message.content:
            if isinstance(block, TextBlock):
                response_parts.append(block.text)
    elif isinstance(message, ResultMessage):
        result_message = message

result = "".join(response_parts)

# ResultMessage のエラーチェック
if result_message and result_message.is_error:
    logger.warning(
        "ResultMessage indicates error",
        is_error=result_message.is_error,
        result=result_message.result[:100] if result_message.result else None,
    )

# 空レスポンスの検出と原因特定
if not result.strip():
    if assistant_error:
        raise EmptyResponseError(reason=assistant_error)
    elif result_message and result_message.is_error:
        raise EmptyResponseError(reason="result_message_error")
    else:
        raise EmptyResponseError(reason="no_text_block")

return result
```

**設計上のポイント**:
- `AssistantMessage.error` を明示的にチェックし、レート制限等を検出する
- `ResultMessage` からクエリ全体の成否を確認する
- 空レスポンスの原因を `EmptyResponseError.reason` に記録し、ログで追跡可能にする
- `EmptyResponseError` は `ValueError` とは異なる例外型のため、リトライ判定で区別できる

#### 4. `src/news/summarizer.py` — `_parse_response()` に空文字列の早期チェック追加

**変更前**（436行目付近）:
```python
json_match = re.search(r"```json\s*(.*?)\s*```", response_text, re.DOTALL)
```

**変更後**:
```python
if not response_text.strip():
    raise ValueError("Empty response text (should have been caught by _call_claude_sdk)")

json_match = re.search(r"```json\s*(.*?)\s*```", response_text, re.DOTALL)
```

防御的チェック。通常は `_call_claude_sdk()` で `EmptyResponseError` が送出されるが、万が一到達した場合の安全策。

#### 5. `src/news/summarizer.py` — `summarize()` のリトライ判定改善

**変更前**（197-210行目）:
```python
except ValueError as e:
    # JSON parse error or Pydantic validation error - don't retry
    error_message = str(e)
    logger.error("Parse/validation error", ...)
    return SummarizedArticle(status=FAILED)
```

**変更後**:
```python
except EmptyResponseError as e:
    # 空レスポンス（レート制限等） → リトライする
    last_error = e
    logger.warning(
        "Empty response from Claude SDK",
        article_url=str(article.collected.url),
        reason=e.reason,
        attempt=attempt + 1,
        max_retries=self._max_retries,
    )
    # レート制限の場合は長めのバックオフ
    if e.reason == "rate_limit" and attempt < self._max_retries - 1:
        backoff = 2 ** (attempt + 2)  # 4s, 8s, 16s
        logger.info("Rate limit detected, extended backoff", backoff_seconds=backoff)
        await asyncio.sleep(backoff)
        continue

except ValueError as e:
    # 不正な JSON 形式 → リトライしない（永続的エラー）
    error_message = str(e)
    logger.error("Parse/validation error", ...)
    return SummarizedArticle(status=FAILED)
```

**設計上のポイント**:
- `EmptyResponseError` は `ValueError` の前に `except` する（Python の例外マッチング順序）
- `EmptyResponseError` は既存のリトライループ（`for attempt in range(self._max_retries)`）で再試行する
- レート制限時は通常より長いバックオフ（4s, 8s, 16s）を適用する
- 不正な JSON 形式（`ValueError`）は従来通りリトライしない

#### 6. バックオフ戦略の整理

| 例外 | リトライ | バックオフ | 理由 |
|------|---------|-----------|------|
| `EmptyResponseError(reason="rate_limit")` | する | 4s, 8s, 16s（強化） | レート制限の回復に時間が必要 |
| `EmptyResponseError(reason=その他)` | する | 1s, 2s, 4s（通常） | 一時的なエラーの可能性 |
| `ValueError` | しない | — | 不正な JSON 形式は再試行しても変わらない |
| `asyncio.TimeoutError` | する | 1s, 2s, 4s（通常） | ネットワーク一時障害 |
| `ProcessError` 等 | する | 1s, 2s, 4s（通常） | CLI プロセスの一時障害 |
| `RuntimeError`（SDK未インストール） | しない | — | 永続的エラー |

**注意: バックオフと `asyncio.timeout` の関係**

`summarize()` メソッドでは `asyncio.timeout(self._timeout_seconds)` が `_call_claude_sdk()` 呼出を囲んでいる。レート制限時のバックオフ `await asyncio.sleep(backoff)` は `except EmptyResponseError` ブロック内で実行されるため、`asyncio.timeout` のスコープ外となり競合しない。

```
for attempt in range(self._max_retries):
    try:
        async with asyncio.timeout(self._timeout_seconds):  # ← timeout のスコープ
            response_text = await self._call_claude_sdk(prompt)  # EmptyResponseError はここで発生
        summary = self._parse_response(response_text)
        ...
    except EmptyResponseError as e:
        await asyncio.sleep(backoff)  # ← timeout の外側で実行（競合なし）
```

---

### テスト追加

`tests/news/unit/summarizers/test_summarizer.py` に以下のテストケースを追加:

| テスト名 | 検証内容 |
|---------|---------|
| `test_異常系_空レスポンスでEmptyResponseError送出` | `_call_claude_sdk` が空文字列を返す場合に `EmptyResponseError` が送出されることを検証 |
| `test_異常系_AssistantMessageエラーでEmptyResponseError送出` | `AssistantMessage.error="rate_limit"` 時に `EmptyResponseError(reason="rate_limit")` が送出されることを検証 |
| `test_異常系_空レスポンスはリトライされる` | `EmptyResponseError` 発生時にリトライループが継続することを検証（2回目で成功するケース） |
| `test_異常系_レート制限時の強化バックオフ` | `reason="rate_limit"` 時のバックオフが 4s, 8s, 16s であることを検証 |
| `test_異常系_不正JSONはリトライされない` | `ValueError`（不正な JSON 形式）発生時に即座に FAILED が返ることを検証（従来動作の維持） |
| `test_異常系_ResultMessageエラーで空レスポンス検出` | `ResultMessage(is_error=True)` かつ TextBlock なしの場合にエラーが検出されることを検証 |

---

### 実装チェックリスト

- [ ] `src/news/summarizer.py`: `ResultMessage` のインポート追加 → [#3083](https://github.com/YH-05/quants/issues/3083)
- [ ] `src/news/summarizer.py`: `EmptyResponseError` 例外クラス追加 → [#3083](https://github.com/YH-05/quants/issues/3083)
- [ ] `src/news/summarizer.py`: `_call_claude_sdk()` に `AssistantMessage.error` チェック追加 → [#3084](https://github.com/YH-05/quants/issues/3084)
- [ ] `src/news/summarizer.py`: `_call_claude_sdk()` に `ResultMessage` チェック追加 → [#3084](https://github.com/YH-05/quants/issues/3084)
- [ ] `src/news/summarizer.py`: `_call_claude_sdk()` に空レスポンス検出と `EmptyResponseError` 送出追加 → [#3084](https://github.com/YH-05/quants/issues/3084)
- [ ] `src/news/summarizer.py`: `_parse_response()` に空文字列の早期チェック追加 → [#3085](https://github.com/YH-05/quants/issues/3085)
- [ ] `src/news/summarizer.py`: `summarize()` に `EmptyResponseError` の `except` ブロック追加（`ValueError` の前に配置） → [#3086](https://github.com/YH-05/quants/issues/3086)
- [ ] `src/news/summarizer.py`: レート制限時の強化バックオフ（4s, 8s, 16s）追加 → [#3086](https://github.com/YH-05/quants/issues/3086)
- [ ] `tests/news/unit/summarizers/test_summarizer.py`: 空レスポンス・レート制限・リトライのテスト追加 → [#3087](https://github.com/YH-05/quants/issues/3087)
- [ ] `make check-all` が成功することを確認

---

### 補足: `ResultMessage.result` を要約テキストとして使用しない理由

`ResultMessage.result` には最終結果テキストが含まれる場合がある。これを `AssistantMessage` の代わりに使用する案も検討したが、以下の理由で不採用とした:

1. **フォーマットの保証がない**: `ResultMessage.result` はプレーンテキストであり、JSON 形式が保証されない
2. **ストリーミングとの整合性**: `AssistantMessage` のストリーミング受信が正常なパスであり、`ResultMessage` はメタデータ取得が主目的
3. **エラー検出の信頼性**: `ResultMessage.is_error` はクエリ全体の成否を示すフラグとして使用する方が適切

`ResultMessage` はエラー検出とコスト・時間のログ出力のみに使用する。

---

## 追加改善: フィードエラーの最終サマリー表示

### 問題概要

フィードエラー（`WorkflowResult.feed_errors`）は記録されるが、最終サマリー（`orchestrator.py:286-298`）には含まれていない。ユーザーがフィード収集の失敗に気付くにはログ出力を確認する必要がある。

### 変更対象ファイル

| ファイル | 変更内容 |
|----------|----------|
| `src/news/orchestrator.py` | 最終サマリーにフィードエラー件数を表示 |

### 修正内容

`run()` メソッドの最終サマリー表示（`orchestrator.py:286-298`）に `feed_errors` の件数を追加する。

```python
# Final summary
print(f"\n{'=' * 60}")
print("ワークフロー完了")
print(f"{'=' * 60}")
print(f"  収集: {result.total_collected}件")
# ---- 追加 ----
if result.feed_errors:
    print(f"  フィードエラー: {len(result.feed_errors)}件")
# ---- ここまで ----
if result.total_early_duplicates > 0:
    print(f"  重複除外（早期）: {result.total_early_duplicates}件")
print(f"  抽出: {result.total_extracted}件")
print(f"  要約: {result.total_summarized}件")
print(f"  公開: {result.total_published}件")
if result.total_duplicates > 0:
    print(f"  重複（公開時）: {result.total_duplicates}件")
print(f"  処理時間: {elapsed:.1f}秒")
```

### 実装チェックリスト

- [ ] `src/news/orchestrator.py`: 最終サマリーにフィードエラー件数の表示を追加 → [#3088](https://github.com/YH-05/quants/issues/3088)
- [ ] `src/news/orchestrator.py`: `_build_result()` で `feed_errors` が正しく `WorkflowResult` に設定されていることを確認 → [#3088](https://github.com/YH-05/quants/issues/3088)
