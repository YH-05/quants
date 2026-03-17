# 収集結果サマリーテンプレート

ニュース収集完了時に表示するサマリーフォーマット。

## 全体サマリー

```markdown
================================================================================
            /collect-finance-news 完了
================================================================================

## 収集結果サマリー

| 項目 | 件数 |
|------|------|
| 処理記事数 | {{total_processed}} |
| 期間外スキップ | {{date_filtered}} |
| テーママッチ | {{total_matched}} |
| 重複スキップ | {{total_duplicates}} |
| 新規投稿 | {{total_created}} |
| 投稿失敗 | {{total_failed}} |

## テーマ別統計

| テーマ | 処理 | マッチ | 重複 | 投稿 | 失敗 |
|--------|------|--------|------|------|------|
{{#themes}}
| {{theme_ja}} | {{processed}} | {{matched}} | {{duplicates}} | {{created}} | {{failed}} |
{{/themes}}

## 作成されたIssue

{{#created_issues}}
- [#{{issue_number}}]({{issue_url}}) {{title}}
  - テーマ: {{theme_ja}}
  - 公開日: {{published_date}}
  - ソース: {{feed_source}}
{{/created_issues}}

## エラー・スキップ情報

{{#has_errors}}
### エラー一覧

{{#errors}}
- **{{title}}**: {{error_message}}
  - URL: {{url}}
{{/errors}}
{{/has_errors}}

{{#has_skipped}}
### スキップされた記事

#### 期間外
{{#date_skipped}}
- {{title}} (公開: {{published_date}})
{{/date_skipped}}

#### 重複
{{#duplicates}}
- {{title}} → 既存Issue: #{{existing_issue_number}}
{{/duplicates}}

#### テーマ不一致
{{#theme_mismatch}}
- {{title}} (判定: {{判定結果}})
{{/theme_mismatch}}
{{/has_skipped}}

## 実行パラメータ

- **期間**: {{since}}
- **対象テーマ**: {{themes}}
- **取得上限**: {{limit}}件
- **dry-run**: {{dry_run}}

---

**次回実行**: `/collect-finance-news` または `/collect-finance-news --since 1d`
```

## プレースホルダー一覧

### 統計情報

| プレースホルダー | 説明 | 型 |
|-----------------|------|-----|
| `{{total_processed}}` | 処理した記事総数 | int |
| `{{date_filtered}}` | 期間外でスキップした件数 | int |
| `{{total_matched}}` | テーマにマッチした件数 | int |
| `{{total_duplicates}}` | 重複でスキップした件数 | int |
| `{{total_created}}` | 新規作成したIssue数 | int |
| `{{total_failed}}` | 作成失敗した件数 | int |

### テーマ別統計

| プレースホルダー | 説明 |
|-----------------|------|
| `{{themes}}` | テーマ別統計の配列 |
| `{{theme_ja}}` | テーマ名（日本語） |
| `{{processed}}` | そのテーマで処理した件数 |
| `{{matched}}` | テーマにマッチした件数 |
| `{{duplicates}}` | 重複件数 |
| `{{created}}` | 作成したIssue数 |
| `{{failed}}` | 失敗件数 |

### 作成Issue一覧

| プレースホルダー | 説明 |
|-----------------|------|
| `{{created_issues}}` | 作成したIssueの配列 |
| `{{issue_number}}` | Issue番号 |
| `{{issue_url}}` | IssueのURL |
| `{{title}}` | 記事タイトル |
| `{{published_date}}` | 公開日時 |
| `{{feed_source}}` | フィード名 |

### エラー・スキップ情報

| プレースホルダー | 説明 |
|-----------------|------|
| `{{has_errors}}` | エラーがあるかどうか（boolean） |
| `{{errors}}` | エラー一覧の配列 |
| `{{error_message}}` | エラーメッセージ |
| `{{has_skipped}}` | スキップがあるかどうか（boolean） |
| `{{date_skipped}}` | 期間外でスキップした記事の配列 |
| `{{duplicates}}` | 重複でスキップした記事の配列 |
| `{{existing_issue_number}}` | 重複先のIssue番号 |
| `{{theme_mismatch}}` | テーマ不一致でスキップした記事の配列 |
| `{{判定結果}}` | AI判定の結果 |

### 実行パラメータ

| プレースホルダー | 説明 | デフォルト |
|-----------------|------|-----------|
| `{{since}}` | 期間指定 | `1d` |
| `{{themes}}` | 対象テーマ | `all` |
| `{{limit}}` | 取得上限 | `50` |
| `{{dry_run}}` | dry-runモード | `false` |

## テーマ別サマリー

各テーマエージェントが出力するサマリー形式：

```markdown
## {{theme_name}} ニュース収集完了

### 処理統計
- **処理記事数**: {{processed}}件
- **テーママッチ**: {{matched}}件（AI判断）
- **重複**: {{duplicates}}件
- **新規投稿**: {{created}}件
- **投稿失敗**: {{failed}}件

### 投稿されたニュース

{{#created_issues}}
1. **{{title}}** [#{{issue_number}}]
   - ソース: {{feed_source}}
   - 公開日時: {{published_jst}}
   - AI判定理由: {{判定理由}}
   - URL: https://github.com/YH-05/quants/issues/{{issue_number}}
{{/created_issues}}
```

## dry-runモード出力

`--dry-run` オプション使用時の出力形式：

```markdown
================================================================================
            /collect-finance-news (dry-run) 完了
================================================================================

## dry-run結果

**注意**: 以下は投稿されずにシミュレーションされた結果です。

### 投稿予定のニュース

{{#would_create}}
1. **[{{theme_ja}}] {{japanese_title}}**
   - 元タイトル: {{original_title}}
   - URL: {{url}}
   - ソース: {{feed_source}}
   - 公開日: {{published_date}}
{{/would_create}}

### スキップ予定

- 期間外: {{date_filtered}}件
- 重複: {{total_duplicates}}件
- テーマ不一致: {{theme_mismatch_count}}件

---

**実際に投稿するには**: `/collect-finance-news` を実行してください
```

## エラーサマリー

収集中にエラーが発生した場合の追加出力：

```markdown
## ⚠️ エラーサマリー

### 発生したエラー

| タイプ | 件数 | 詳細 |
|--------|------|------|
| MCP接続エラー | {{mcp_errors}} | RSS MCPへの接続失敗 |
| Issue作成エラー | {{issue_create_errors}} | GitHub API呼び出し失敗 |
| 日時設定エラー | {{date_field_errors}} | Project日時フィールド設定失敗 |
| その他 | {{other_errors}} | - |

### 推奨アクション

{{#has_mcp_errors}}
- MCPサーバーの状態を確認: `.mcp.json` の設定を確認
{{/has_mcp_errors}}

{{#has_rate_limit}}
- GitHub API レート制限: 1時間待機後に再実行
{{/has_rate_limit}}

{{#has_network_errors}}
- ネットワーク接続を確認し、再実行
{{/has_network_errors}}
```

## 出力例

### 正常完了時

```markdown
================================================================================
            /collect-finance-news 完了
================================================================================

## 収集結果サマリー

| 項目 | 件数 |
|------|------|
| 処理記事数 | 45 |
| 期間外スキップ | 12 |
| テーママッチ | 18 |
| 重複スキップ | 5 |
| 新規投稿 | 13 |
| 投稿失敗 | 0 |

## テーマ別統計

| テーマ | 処理 | マッチ | 重複 | 投稿 | 失敗 |
|--------|------|--------|------|------|------|
| 株価指数 | 8 | 4 | 1 | 3 | 0 |
| 個別銘柄 | 10 | 5 | 2 | 3 | 0 |
| セクター | 7 | 2 | 0 | 2 | 0 |
| マクロ経済 | 12 | 4 | 1 | 3 | 0 |
| AI | 5 | 2 | 1 | 1 | 0 |
| 金融 | 3 | 1 | 0 | 1 | 0 |

## 作成されたIssue

- [#345](https://github.com/YH-05/quants/issues/345) S&P 500が最高値を更新、テック株がけん引
  - テーマ: 株価指数
  - 公開日: 2026-01-22 09:30
  - ソース: CNBC - Markets

- [#346](https://github.com/YH-05/quants/issues/346) Fed議長、3月利下げを示唆
  - テーマ: マクロ経済
  - 公開日: 2026-01-22 10:15
  - ソース: CNBC - Economy

...

## 実行パラメータ

- **期間**: 1d
- **対象テーマ**: all
- **取得上限**: 50件
- **dry-run**: false

---

**次回実行**: `/collect-finance-news` または `/collect-finance-news --since 1d`
```

## 参照

- **スキル定義**: `.claude/skills/finance-news-workflow/SKILL.md`
- **Issue作成テンプレート**: `./issue-template.md`
- **共通処理ガイド**: `.claude/agents/finance_news_collector/common-processing-guide.md`
