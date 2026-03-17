# rss プロジェクト

**ステータス**: ✅ 完了（2026-01-15）
**GitHub Project**: [#10](https://github.com/users/YH-05/projects/10)

## 概要

外部RSSフィードを収集・集約し、構造化データとして管理するPythonライブラリ。
金融メディア、経済データソース、個人ブログなど、様々なRSSフィードから情報を取得し、
JSON形式で保存・エクスポートする。

**主な用途:**
- 金融メディア（Bloomberg、Reuters、日経等）のニュースフィード収集
- 経済データソース（FRED、中央銀行等）の統計情報フィード取得
- 個人ブログや専門メディアからの情報収集
- 収集データのAIエージェント向け構造化API提供
- MCPサーバーとしてClaude Codeへの機能提供

## 主要機能

### フィード管理
- [x] RSSフィードの登録・削除・一覧管理 - Issue: [#61](https://github.com/YH-05/quants/issues/61)
- [x] フィードメタデータ（URL、タイトル、カテゴリ、更新頻度等）の管理 - Issue: [#53](https://github.com/YH-05/quants/issues/53)
- [x] フィード取得スケジュール設定 - Issue: [#67](https://github.com/YH-05/quants/issues/67)

### データ取得・パース
- [x] RSS 2.0 / Atom フォーマット対応 - Issue: [#59](https://github.com/YH-05/quants/issues/59)
- [x] HTTP/HTTPS経由でのフィード取得 - Issue: [#60](https://github.com/YH-05/quants/issues/60)
- [x] エラーハンドリング（タイムアウト、404、パースエラー等） - Issue: [#54](https://github.com/YH-05/quants/issues/54)
- [x] 差分取得（既存アイテムとの重複排除） - Issue: [#58](https://github.com/YH-05/quants/issues/58)

### データ保存・管理
- [x] JSON形式でのローカル保存（data/raw/rss/） - Issue: [#56](https://github.com/YH-05/quants/issues/56)
- [x] フィードアイテムの構造化データ管理（タイトル、URL、公開日時、内容等） - Issue: [#63](https://github.com/YH-05/quants/issues/63)
- [x] メタデータ管理（取得日時、フィード情報等） - Issue: [#53](https://github.com/YH-05/quants/issues/53)

### 実行モード
- [x] 手動実行API（Python関数呼び出し） - Issue: [#64](https://github.com/YH-05/quants/issues/64)
- [x] 日次バッチ実行対応（スケジューラー連携） - Issue: [#67](https://github.com/YH-05/quants/issues/67)
- [x] CLIインターフェース - Issue: [#66](https://github.com/YH-05/quants/issues/66)

### MCPサーバー機能
- [x] Claude Code向けMCPサーバー実装 - Issue: [#65](https://github.com/YH-05/quants/issues/65)
- [x] フィード情報取得API（一覧、詳細） - Issue: [#65](https://github.com/YH-05/quants/issues/65)
- [x] アイテム検索・フィルタリングAPI - Issue: [#65](https://github.com/YH-05/quants/issues/65)

## 技術的考慮事項

### 技術スタック
- **HTTPクライアント**: httpx（非同期対応）
- **RSSパーサー**: feedparser
- **データ形式**: JSON（標準ライブラリ）
- **MCPプロトコル**: mcp（Anthropic MCP SDK）
- **スケジューリング**: schedule または APScheduler（オプション）

### 制約・依存関係
- Python 3.12+
- ネットワークアクセスが必要
- 各RSSフィードのレート制限に注意
- feedparser によるパース結果の検証が必要

### データ構造設計
```python
# フィード情報
{
  "feed_id": "unique_id",
  "url": "https://example.com/feed.xml",
  "title": "Example Feed",
  "category": "finance",
  "last_fetched": "2026-01-14T10:00:00Z",
  "fetch_interval": "daily"
}

# フィードアイテム
{
  "item_id": "unique_id",
  "feed_id": "feed_unique_id",
  "title": "Article Title",
  "link": "https://example.com/article",
  "published": "2026-01-14T09:00:00Z",
  "summary": "Article summary...",
  "content": "Full content...",
  "author": "Author Name",
  "fetched_at": "2026-01-14T10:00:00Z"
}
```

## 成功基準

1. **機能完成度**
   - RSS 2.0 / Atom フィードを正常にパースできる
   - 10以上の主要金融メディアのフィードを取得できる
   - 構造化されたJSONデータが保存される
   - MCPサーバーとしてClaude Codeから利用できる

2. **品質基準**
   - テストカバレッジ 80% 以上
   - 型チェック（pyright）エラーなし
   - ドキュメント完備

3. **運用性**
   - 手動実行と日次バッチ実行の両方に対応
   - エラー時の適切なログ出力とリトライ機構
   - AIエージェントから利用可能なAPI提供

4. **柔軟性**
   - Pythonベースで拡張性の高い設計
   - MCPサーバーとしての機能提供
   - 他システムとの連携が容易

---

## GitHub Project #10 Issue一覧

| # | タイトル | ステータス |
|---|---------|----------|
| [#53](https://github.com/YH-05/quants/issues/53) | [T1] 型定義（types.py） | Done |
| [#54](https://github.com/YH-05/quants/issues/54) | [T2] 例外クラス（exceptions.py） | Done |
| [#55](https://github.com/YH-05/quants/issues/55) | [T3] ファイルロック管理（LockManager） | Done |
| [#56](https://github.com/YH-05/quants/issues/56) | [T4] JSON永続化（JSONStorage） | Done |
| [#57](https://github.com/YH-05/quants/issues/57) | [T5] URL・文字列長検証（URLValidator） | Done |
| [#58](https://github.com/YH-05/quants/issues/58) | [T6] 差分検出（DiffDetector） | Done |
| [#59](https://github.com/YH-05/quants/issues/59) | [T7] RSS/Atomパーサー（FeedParser） | Done |
| [#60](https://github.com/YH-05/quants/issues/60) | [T8] HTTP/HTTPSクライアント（HTTPClient） | Done |
| [#61](https://github.com/YH-05/quants/issues/61) | [T9] フィード管理サービス（FeedManager） | Done |
| [#62](https://github.com/YH-05/quants/issues/62) | [T10] フィード取得サービス（FeedFetcher） | Done |
| [#63](https://github.com/YH-05/quants/issues/63) | [T11] アイテム読込サービス（FeedReader） | Done |
| [#64](https://github.com/YH-05/quants/issues/64) | [T12] Python API エクスポート（__init__.py） | Done |
| [#65](https://github.com/YH-05/quants/issues/65) | [T14] MCPサーバー実装 | Done |
| [#66](https://github.com/YH-05/quants/issues/66) | [T15] CLIインターフェース実装 | Done |
| [#67](https://github.com/YH-05/quants/issues/67) | [T16] 日次バッチ実行機能 | Done |
| [#68](https://github.com/YH-05/quants/issues/68) | [T13] ユニットテスト（カバレッジ80%以上） | Done |
| [#69](https://github.com/YH-05/quants/issues/69) | [T17] 統合テスト（フルフロー） | Done |

**17件完了 / 17件中** (2026-01-23)

---

**最終更新**: 2026-01-23
**更新内容**: GitHub Project #10 とステータス同期（全 Issue 完了）

---

> このファイルは `/new-project @src/rss/docs/project.md` で詳細化されました
