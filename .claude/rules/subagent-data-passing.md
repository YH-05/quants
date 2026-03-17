# サブエージェントへのデータ渡しルール

## 概要

サブエージェントにデータを渡す際は、**完全なデータ構造を維持**することが必須です。
データの簡略化や省略は重大な問題を引き起こします。

## 必須ルール

### ルール1: 完全なデータ構造を渡すこと

サブエージェントにデータを渡す際は、取得した元データの全フィールドを含めること。

**禁止例（絶対にやってはいけない）**:
```
1. "記事タイトル" - 簡単な説明
2. "記事タイトル" - 簡単な説明
```

**必須例（正しい形式）**:
```json
{
  "articles": [
    {
      "item_id": "60af4cc3-0a47-4cfb-ae89-ed8872209f5d",
      "title": "記事タイトル",
      "link": "https://example.com/article/123",
      "published": "2026-01-18T22:00:31+00:00",
      "summary": "記事の要約...",
      "content": null,
      "author": null,
      "fetched_at": "2026-01-18T22:40:08.589493+00:00"
    }
  ]
}
```

### ルール2: RSS記事データの必須フィールド

RSS記事をサブエージェントに渡す際、以下のフィールドは**必須**:

| フィールド | 必須 | 説明 |
|-----------|------|------|
| `title` | ✅ | 記事タイトル |
| `link` | ✅ | **元記事のURL（絶対に省略禁止）** |
| `published` | ✅ | 公開日時 |
| `summary` | ✅ | 記事要約 |
| `item_id` | 推奨 | 記事の一意識別子 |
| `fetched_at` | 推奨 | 取得日時 |
| `content` | 任意 | 記事本文（あれば） |
| `author` | 任意 | 著者名（あれば） |

### ルール3: URLは絶対に省略・変更禁止

**最重要**: `link` フィールドは以下の理由で必須です：

1. **GitHub Issue作成時に元記事URLとして使用**
2. **重複チェックのキーとして使用**
3. **トレーサビリティの確保**

URLを省略すると、サブエージェントは以下ができなくなります：
- Issue作成
- 重複チェック
- 記事本文の取得（WebFetch）

### ルール4: JSON形式での受け渡し

データは必ず**JSON形式**で渡すこと。自然言語での説明的な形式は禁止。

**禁止**:
```
以下の記事があります：
- トヨタの決算発表（株式関連）
- 日銀の金利発表（マクロ経済関連）
```

**必須**:
```json
{
  "articles": [...],
  "existing_issues": [...],
  "config": {...}
}
```

### ルール5: 既存Issueデータも完全に渡す

重複チェック用の既存Issueも完全なデータで渡すこと：

```json
{
  "existing_issues": [
    {
      "number": 344,
      "title": "[マクロ経済] 記事タイトル",
      "url": "https://github.com/YH-05/quants/issues/344",
      "createdAt": "2026-01-18T08:22:33Z",
      "body": "Issueの本文..."
    }
  ]
}
```

### ルール6: article-fetcherへのデータ渡し

article-fetcherにはIssue作成に必要な全情報を渡すこと。

**必須**: `articles[]` と `issue_config` の両方を含めること。

```json
{
  "articles": [
    {
      "url": "https://...",
      "title": "...",
      "summary": "...",
      "feed_source": "CNBC - Markets",
      "published": "2026-01-19T12:00:00+00:00"
    }
  ],
  "issue_config": {
    "theme_key": "index",
    "theme_label": "株価指数",
    "status_option_id": "3925acc3",
    "project_id": "PVT_...",
    "project_number": 15,
    "project_owner": "YH-05",
    "repo": "YH-05/quants",
    "status_field_id": "PVTSSF_...",
    "published_date_field_id": "PVTF_..."
  }
}
```

#### articles[] の必須フィールド

| フィールド | 必須 | 説明 |
|-----------|------|------|
| `url` | ✅ | 元記事URL（RSSの`link`フィールド） |
| `title` | ✅ | 記事タイトル |
| `summary` | ✅ | RSS概要（フォールバック用） |
| `feed_source` | ✅ | フィード名 |
| `published` | ✅ | 公開日時（ISO 8601形式） |

#### issue_config の必須フィールド

| フィールド | 必須 | 説明 | 例 |
|-----------|------|------|-----|
| `theme_key` | ✅ | テーマキー | `"index"` |
| `theme_label` | ✅ | テーマ日本語名 | `"株価指数"` |
| `status_option_id` | ✅ | StatusのOption ID | `"3925acc3"` |
| `project_id` | ✅ | Project ID | `"PVT_kwHOBoK6AM4BMpw_"` |
| `project_number` | ✅ | Project番号 | `15` |
| `project_owner` | ✅ | Projectオーナー | `"YH-05"` |
| `repo` | ✅ | リポジトリ | `"YH-05/quants"` |
| `status_field_id` | ✅ | StatusフィールドID | `"PVTSSF_lAHOBoK6AM4BMpw_zg739ZE"` |
| `published_date_field_id` | ✅ | 公開日フィールドID | `"PVTF_lAHOBoK6AM4BMpw_zg8BzrI"` |

#### issue_config の構築方法

テーマエージェントはセッションファイルの `config` とテーマ固有設定を組み合わせて `issue_config` を構築する:

```python
issue_config = {
    "theme_key": "index",                                    # テーマ固有
    "theme_label": "株価指数",                                # テーマ固有
    "status_option_id": "3925acc3",                          # テーマ固有
    "project_id": session_data["config"]["project_id"],      # セッション共通
    "project_number": session_data["config"]["project_number"],  # セッション共通
    "project_owner": session_data["config"]["project_owner"],    # セッション共通
    "repo": "YH-05/quants",                                 # 固定値
    "status_field_id": session_data["config"]["status_field_id"],            # セッション共通
    "published_date_field_id": session_data["config"]["published_date_field_id"],  # セッション共通
}
```

#### article-fetcherの出力形式

article-fetcherは以下の形式で結果を返す:

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
      "reason": "ペイウォール検出"
    }
  ],
  "stats": {
    "total": 5,
    "issue_created": 3,
    "issue_failed": 0,
    "skipped_paywall": 1,
    "skipped_format": 0
  }
}
```

## 違反時の影響

データ省略の実際の影響例：

| 省略したデータ | 発生する問題 |
|--------------|-------------|
| `link` (URL) | Issue作成不可、重複チェック不可 |
| `published` | 日時フィルタリング不可、Project日付フィールド設定不可 |
| `summary` | 適切な日本語要約生成が困難 |
| `existing_issues` | 重複投稿が発生 |
| `issue_config` | article-fetcherがIssue作成・Project追加・Status/Date設定不可 |
| `issue_config.theme_label` | Issueタイトルプレフィックス欠落 |
| `issue_config.project_id` | Project追加・Status/Date設定不可 |

## 正しい実装パターン

### パターン1: 一時ファイル経由

```python
# 1. データを一時ファイルに保存
session_data = {
    "session_id": f"news-collection-{timestamp}",
    "timestamp": datetime.now().isoformat(),
    "rss_items": rss_items,  # 完全なRSSデータ
    "existing_issues": existing_issues,  # 完全なIssueデータ
    "config": config
}
with open(f".tmp/news-collection-{timestamp}.json", "w") as f:
    json.dump(session_data, f, ensure_ascii=False, indent=2)

# 2. サブエージェントに一時ファイルのパスを渡す
Task(
    subagent_type="finance-news-stock",
    prompt=f"一時ファイルを読み込んで処理: .tmp/news-collection-{timestamp}.json"
)
```

### パターン2: プロンプト内でJSON直接渡し

```python
# 完全なデータをJSONとしてプロンプトに含める
Task(
    subagent_type="finance-news-stock",
    prompt=f"""以下のRSSデータを処理してください。

## RSS記事データ（完全版）
```json
{json.dumps(rss_items, ensure_ascii=False, indent=2)}
```

## 既存Issue（重複チェック用）
```json
{json.dumps(existing_issues, ensure_ascii=False, indent=2)}
```
"""
)
```

## チェックリスト

サブエージェント呼び出し前に確認：

- [ ] 全記事に `link` (URL) が含まれているか
- [ ] 全記事に `published` が含まれているか
- [ ] 全記事に `title` と `summary` が含まれているか
- [ ] データはJSON形式で渡しているか
- [ ] 既存Issueも完全なデータで渡しているか
- [ ] 自然言語での説明的な形式になっていないか
- [ ] article-fetcher呼び出し時に `articles[]` と `issue_config` の両方を含めているか
- [ ] `issue_config` に全9フィールドが含まれているか

## 関連ファイル

- コマンド: `.claude/commands/collect-finance-news.md`
- テーマエージェント: `.claude/agents/finance-news-*.md`
- 共通処理ガイド: `.claude/agents/finance_news_collector/common-processing-guide.md`
