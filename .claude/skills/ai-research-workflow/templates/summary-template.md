# AI投資バリューチェーン収集結果サマリーテンプレート

収集完了時に表示するサマリーフォーマット。カテゴリ別統計 + スクレイピング統計レポート。

## 全体サマリー

```markdown
================================================================================
            /ai-research-collect 完了
================================================================================

## 収集結果サマリー

| 項目 | 件数 |
|------|------|
| 対象企業数 | {{total_companies}} |
| スクレイピング成功企業 | {{scrape_success}} |
| スクレイピング失敗企業 | {{scrape_failed}} |
| 取得記事数 | {{total_articles}} |
| 期間外スキップ | {{date_filtered}} |
| 重複スキップ | {{total_duplicates}} |
| 投稿対象 | {{total_eligible}} |
| Issue作成成功 | {{total_created}} |
| Issue作成失敗 | {{total_failed}} |

## カテゴリ別統計

| カテゴリ | 企業数 | 取得記事 | 重複 | 投稿 | 失敗 | Impact H/M/L |
|---------|--------|---------|------|------|------|-------------|
{{#categories}}
| {{category_label}} | {{companies}} | {{articles}} | {{duplicates}} | {{created}} | {{failed}} | {{impact_high}}/{{impact_medium}}/{{impact_low}} |
{{/categories}}

## ティア別スクレイピング統計

| ティア | 対象企業 | 成功 | 失敗 | 成功率 |
|--------|---------|------|------|--------|
| Tier 1 (RSS) | {{tier1_total}} | {{tier1_success}} | {{tier1_failed}} | {{tier1_rate}} |
| Tier 2 (汎用) | {{tier2_total}} | {{tier2_success}} | {{tier2_failed}} | {{tier2_rate}} |
| Tier 3 (アダプタ) | {{tier3_total}} | {{tier3_success}} | {{tier3_failed}} | {{tier3_rate}} |
| **合計** | **{{total_companies}}** | **{{scrape_success}}** | **{{scrape_failed}}** | **{{overall_rate}}** |

{{#has_failed_companies}}
## スクレイピング失敗企業

| 企業 | ティア | カテゴリ | エラー |
|------|--------|---------|--------|
{{#failed_companies}}
| {{company_name}} | Tier {{tier}} | {{category_label}} | {{error}} |
{{/failed_companies}}
{{/has_failed_companies}}

{{#has_structure_changes}}
## 構造変更検知

| 企業 | URL | ヒット率 | 閾値 | 推奨アクション |
|------|-----|---------|------|--------------|
{{#structure_changes}}
| {{company_name}} | {{url}} | {{hit_rate}} | {{threshold}} | {{action}} |
{{/structure_changes}}
{{/has_structure_changes}}

## 作成されたIssue

{{#created_issues}}
- [#{{issue_number}}]({{issue_url}}) {{title}}
  - カテゴリ: {{category_label}}
  - 企業: {{company_name}}
  - 影響度: {{impact_level}}
  - 関連銘柄: {{tickers}}
  - 公開日: {{published_date}}
{{/created_issues}}

{{#has_errors}}
## エラー・スキップ情報

### エラー一覧

{{#errors}}
- **{{title}}**: {{error_message}}
  - URL: {{url}}
  - 企業: {{company_name}}
{{/errors}}
{{/has_errors}}

{{#has_skipped}}
### スキップされた記事

#### 期間外
{{#date_skipped}}
- {{title}} ({{company_name}}, 公開: {{published_date}})
{{/date_skipped}}

#### 重複
{{#duplicates}}
- {{title}} -> 既存Issue: #{{existing_issue_number}}
{{/duplicates}}

#### 本文不十分
{{#text_insufficient}}
- {{title}} ({{company_name}}, {{text_length}}文字)
{{/text_insufficient}}
{{/has_skipped}}

## 実行パラメータ

- **期間**: 過去{{days}}日間
- **対象カテゴリ**: {{categories}}
- **取得上限**: {{top_n}}件/カテゴリ
- **実行時刻**: {{timestamp}}
- **セッションファイル**: {{session_file}}

---

**次回実行**: `/ai-research-collect` または `/ai-research-collect --days 3 --categories "ai_llm,gpu_chips"`
```

## プレースホルダー一覧

### 全体統計

| プレースホルダー | 説明 | 型 |
|-----------------|------|-----|
| `{{total_companies}}` | 対象企業総数 | int |
| `{{scrape_success}}` | スクレイピング成功企業数 | int |
| `{{scrape_failed}}` | スクレイピング失敗企業数 | int |
| `{{total_articles}}` | 取得した記事総数 | int |
| `{{date_filtered}}` | 期間外でスキップした件数 | int |
| `{{total_duplicates}}` | 重複でスキップした件数 | int |
| `{{total_eligible}}` | 投稿対象記事数 | int |
| `{{total_created}}` | 新規作成したIssue数 | int |
| `{{total_failed}}` | 作成失敗した件数 | int |

### カテゴリ別統計

| プレースホルダー | 説明 |
|-----------------|------|
| `{{categories}}` | カテゴリ別統計の配列 |
| `{{category_label}}` | カテゴリ名（日本語） |
| `{{companies}}` | そのカテゴリの企業数 |
| `{{articles}}` | 取得した記事数 |
| `{{duplicates}}` | 重複件数 |
| `{{created}}` | 作成したIssue数 |
| `{{failed}}` | 失敗件数 |
| `{{impact_high}}` | Impact Levelがhighの件数 |
| `{{impact_medium}}` | Impact Levelがmediumの件数 |
| `{{impact_low}}` | Impact Levelがlowの件数 |

### ティア別スクレイピング統計

| プレースホルダー | 説明 |
|-----------------|------|
| `{{tier1_total}}` | Tier 1対象企業数 |
| `{{tier1_success}}` | Tier 1成功企業数 |
| `{{tier1_failed}}` | Tier 1失敗企業数 |
| `{{tier1_rate}}` | Tier 1成功率（例: 100.0%） |
| `{{tier2_total}}` | Tier 2対象企業数 |
| `{{tier2_success}}` | Tier 2成功企業数 |
| `{{tier2_failed}}` | Tier 2失敗企業数 |
| `{{tier2_rate}}` | Tier 2成功率 |
| `{{tier3_total}}` | Tier 3対象企業数 |
| `{{tier3_success}}` | Tier 3成功企業数 |
| `{{tier3_failed}}` | Tier 3失敗企業数 |
| `{{tier3_rate}}` | Tier 3成功率 |
| `{{overall_rate}}` | 全体成功率 |

### 失敗企業

| プレースホルダー | 説明 |
|-----------------|------|
| `{{has_failed_companies}}` | 失敗企業があるかどうか（boolean） |
| `{{failed_companies}}` | 失敗企業の配列 |
| `{{company_name}}` | 企業名 |
| `{{tier}}` | ティア番号（1/2/3） |
| `{{error}}` | エラーメッセージ |

### 構造変更検知

| プレースホルダー | 説明 |
|-----------------|------|
| `{{has_structure_changes}}` | 構造変更があるかどうか（boolean） |
| `{{structure_changes}}` | 構造変更の配列 |
| `{{url}}` | 対象URL |
| `{{hit_rate}}` | セレクタヒット率（例: 15%） |
| `{{threshold}}` | 閾値（例: 50%） |
| `{{action}}` | 推奨アクション |

### 作成Issue一覧

| プレースホルダー | 説明 |
|-----------------|------|
| `{{created_issues}}` | 作成したIssueの配列 |
| `{{issue_number}}` | Issue番号 |
| `{{issue_url}}` | IssueのURL |
| `{{title}}` | Issueタイトル |
| `{{company_name}}` | 企業名 |
| `{{impact_level}}` | 市場影響度（high/medium/low） |
| `{{tickers}}` | 関連銘柄（カンマ区切り） |
| `{{published_date}}` | 公開日時 |

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
| `{{text_insufficient}}` | 本文不十分でスキップした記事の配列 |
| `{{text_length}}` | 本文の文字数 |

### 実行パラメータ

| プレースホルダー | 説明 | デフォルト |
|-----------------|------|-----------|
| `{{days}}` | 期間指定（日数） | `7` |
| `{{categories}}` | 対象カテゴリ | `all` |
| `{{top_n}}` | 取得上限 | `10` |
| `{{timestamp}}` | 実行日時 | - |
| `{{session_file}}` | セッションファイルパス | - |

## カテゴリ別サマリー

各カテゴリの ai-research-article-fetcher が出力するサマリー形式:

```markdown
## {{category_label}} AI投資バリューチェーン収集完了

### 処理統計

| 項目 | 件数 |
|------|------|
| 処理記事数 | {{total}} |
| Issue作成成功 | {{issue_created}} |
| Issue作成失敗 | {{issue_failed}} |
| スキップ | {{skipped}} |
| Impact High | {{impact_high}} |
| Impact Medium | {{impact_medium}} |
| Impact Low | {{impact_low}} |

### 投稿されたニュース

{{#created_issues}}
1. **{{title}}** [#{{issue_number}}]
   - 企業: {{company_name}}
   - 影響度: {{impact_level}}
   - 関連銘柄: {{tickers}}
   - Status: {{status}}
   - URL: {{issue_url}}
{{/created_issues}}
```

## エラーサマリー

収集中にエラーが発生した場合の追加出力:

```markdown
## エラーサマリー

### 発生したエラー

| タイプ | 件数 | 詳細 |
|--------|------|------|
| スクレイピングエラー | {{scrape_errors}} | RobustScraper/アダプタの失敗 |
| bot検知ブロック | {{bot_detection_errors}} | 403/429によるブロック |
| Issue作成エラー | {{issue_create_errors}} | GitHub API呼び出し失敗 |
| フィールド設定エラー | {{field_set_errors}} | Category/Status/Date/Impact/Tickers設定失敗 |
| その他 | {{other_errors}} | - |

### 推奨アクション

{{#has_scrape_errors}}
- スクレイピング失敗: RobustScraperのログを確認し、ドメイン別レートリミットを調整
{{/has_scrape_errors}}

{{#has_bot_detection}}
- bot検知: UAローテーション設定を確認、レートリミット間隔を拡大
{{/has_bot_detection}}

{{#has_rate_limit}}
- GitHub API レート制限: 1時間待機後に再実行
{{/has_rate_limit}}

{{#has_structure_changes}}
- 構造変更検知: 該当企業のアダプタまたはセレクタ設定を更新
{{/has_structure_changes}}
```

## 出力例

### 正常完了時

```markdown
================================================================================
            /ai-research-collect 完了
================================================================================

## 収集結果サマリー

| 項目 | 件数 |
|------|------|
| 対象企業数 | 77 |
| スクレイピング成功企業 | 70 |
| スクレイピング失敗企業 | 7 |
| 取得記事数 | 142 |
| 期間外スキップ | 35 |
| 重複スキップ | 12 |
| 投稿対象 | 95 |
| Issue作成成功 | 82 |
| Issue作成失敗 | 3 |

## カテゴリ別統計

| カテゴリ | 企業数 | 取得記事 | 重複 | 投稿 | 失敗 | Impact H/M/L |
|---------|--------|---------|------|------|------|-------------|
| AI/LLM開発 | 11 | 22 | 3 | 15 | 0 | 2/8/5 |
| GPU・演算チップ | 10 | 18 | 2 | 12 | 1 | 3/5/4 |
| 半導体製造装置 | 6 | 8 | 0 | 6 | 0 | 1/3/2 |
| データセンター・クラウド | 7 | 14 | 1 | 10 | 0 | 2/5/3 |
| ネットワーキング | 2 | 4 | 0 | 3 | 0 | 0/2/1 |
| 電力・エネルギー | 7 | 12 | 2 | 8 | 1 | 1/4/3 |
| 原子力・核融合 | 8 | 10 | 1 | 7 | 0 | 2/3/2 |
| フィジカルAI・ロボティクス | 9 | 16 | 1 | 9 | 0 | 1/5/3 |
| SaaS・AI活用ソフトウェア | 10 | 20 | 1 | 7 | 1 | 1/3/3 |
| AI基盤・MLOps | 7 | 18 | 1 | 5 | 0 | 0/3/2 |

## ティア別スクレイピング統計

| ティア | 対象企業 | 成功 | 失敗 | 成功率 |
|--------|---------|------|------|--------|
| Tier 1 (RSS) | 8 | 8 | 0 | 100.0% |
| Tier 2 (汎用) | 64 | 58 | 6 | 90.6% |
| Tier 3 (アダプタ) | 5 | 4 | 1 | 80.0% |
| **合計** | **77** | **70** | **7** | **90.9%** |

## 作成されたIssue

- [#3600](https://github.com/YH-05/quants/issues/3600) [AI/LLM開発] OpenAIがGPT-5を発表、推論性能が3倍向上
  - カテゴリ: AI/LLM開発
  - 企業: OpenAI
  - 影響度: high
  - 関連銘柄: MSFT
  - 公開日: 2026-02-10

- [#3601](https://github.com/YH-05/quants/issues/3601) [GPU・演算チップ] NVIDIAがBlackwell Ultra量産を前倒し
  - カテゴリ: GPU・演算チップ
  - 企業: NVIDIA
  - 影響度: high
  - 関連銘柄: NVDA
  - 公開日: 2026-02-09

...

## 実行パラメータ

- **期間**: 過去7日間
- **対象カテゴリ**: all
- **取得上限**: 10件/カテゴリ
- **実行時刻**: 2026-02-11 10:00(JST)
- **セッションファイル**: .tmp/ai-research-20260211-100000.json

---

**次回実行**: `/ai-research-collect` または `/ai-research-collect --days 3 --categories "ai_llm,gpu_chips"`
```

## 参照

- **スキル定義**: `.claude/skills/ai-research-workflow/SKILL.md`
- **Issue作成テンプレート**: `./issue-template.md`
- **詳細ガイド**: `.claude/skills/ai-research-workflow/guide.md`
- **ai-research-article-fetcher**: `.claude/agents/ai-research-article-fetcher.md`
