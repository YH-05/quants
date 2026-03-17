# ニュース記事と開発 Issue 区別機能 - 実装メモ

**作業開始日**: 2026-01-15
**最終更新**: 2026-01-15
**ステータス**: Phase 2 完了、Phase 3（コミット・テスト）未実施

---

## 📋 プロジェクト概要

### 目的

GitHub Project 15 (Finance News Collection) で収集した金融ニュース記事と、一般的な開発用 Issue を明確に区別する。

### 背景

`/collect-finance-news` コマンドで自動収集されるニュース記事が開発タスクと混在し、管理が煩雑になっていた。

### アプローチ

3 層の区別戦略を採用：

1. **news ラベル** - フィルタリング可能
2. **Project 分離** - Project 15 をニュース専用に
3. **[NEWS] プレフィックス** - 視覚的識別
4. **Issue テンプレート** - 統一フォーマット

---

## ✅ Phase 1: 基盤整備（完了）

**完了日**: 2026-01-15

### 実施内容

#### 1. news ラベル作成

```bash
gh label create "news" \
  --description "金融ニュース記事（記事化候補）" \
  --color "FFA500"
```

**結果**:

-   ラベル名: `news`
-   色: オレンジ (#FFA500)
-   説明: 金融ニュース記事（記事化候補）

#### 2. Issue テンプレート作成

**ファイル**: `.github/ISSUE_TEMPLATE/news-article.md`

**特徴**:

-   自動的に `news` ラベルを付与
-   自動的に Project 15 に追加
-   タイトルに `[NEWS]` プレフィックス
-   必須フィールド: 概要、URL、信頼性スコア、カテゴリ
-   オプションフィールド: 公開日、フィード名、優先度、備考

#### 3. 既存ニュース記事へのラベル付与

```bash
for issue in 171 172 173 174 175; do
  gh issue edit $issue --add-label "news"
done
```

**対象**: Issue #171-175（5 件）

#### 4. Project 15 への移動

```bash
for issue in 171 172 173 174 175; do
  gh project item-add 15 --owner YH-05 \
    --url "https://github.com/YH-05/quants/issues/${issue}"
done
```

**結果**: 5 件のニュース記事が Project 15 に追加

#### 5. ニュース記事の再オープン

```bash
for issue in 171 172 173 174 175; do
  gh issue reopen $issue
done
```

**理由**: Project 15 で管理可能な状態にするため

---

## ✅ Phase 2: 自動化実装（完了）

**完了日**: 2026-01-15

### 実施内容

#### 1. 既存ニュース記事のタイトル更新

```bash
gh issue edit 171 --title "[NEWS] Your wealth and investments are on the line if Trump torpedoes the Fed's independence"
gh issue edit 172 --title "[NEWS] Global Central Bankers Line Up to Support Fed Chair. Markets, Not So Much."
gh issue edit 173 --title "[NEWS] US, Denmark and Greenland to form Arctic working group after tense talks"
gh issue edit 174 --title "[NEWS] Sadiq Khan to warn AI could cause 'mass unemployment' in London"
gh issue edit 175 --title "[NEWS] Rachel Reeves signals expansion of pubs tax U-turn to other businesses"
```

**結果**: 全 5 件に `[NEWS]` プレフィックス付与

#### 2. finance-news-collector エージェント修正

**ファイル**: `.claude/agents/finance-news-collector.md`

**変更箇所**:

-   行 270: Issue 作成時のタイトルに `[NEWS]` プレフィックスを自動追加
    ```bash
    --title "[NEWS] {news_title}"
    ```
-   行 292: `news` ラベルの自動付与（既存）
-   行 293: Project 15 への自動追加（既存から変更なし）

#### 3. collect-finance-news コマンド修正

**ファイル**: `.claude/commands/collect-finance-news.md`

**変更内容**:
| 項目 | 変更前 | 変更後 |
|------|--------|--------|
| デフォルト Project | 14 | 15 |
| Project 名称 | Finance News Tracker | Finance News Collection |
| Project URL | projects/14 | projects/15 |
| Issue 確認コマンド | `gh issue list --project "..."` | `gh issue list --label "news"` |

#### 4. finance-news-collection スキル修正

**ファイル**: `.claude/skills/finance-news-collection/SKILL.md`

**変更箇所**:

-   行 435: GitHub Project 参照を Project 14 → Project 15 に更新

#### 5. Issue テンプレート（再掲）

**ファイル**: `.github/ISSUE_TEMPLATE/news-article.md`

**YAML 設定**:

```yaml
title: "[NEWS] "
labels: ["news"]
projects: ["YH-05/15"]
```

---

## 📊 実装結果の検証

### ニュース記事の状態（2026-01-15 時点）

| Issue | タイトル                              | ラベル | Project | 状態 |
| ----- | ------------------------------------- | ------ | ------- | ---- |
| #171  | [NEWS] Your wealth and investments... | news   | 15      | OPEN |
| #172  | [NEWS] Global Central Bankers...      | news   | 15      | OPEN |
| #173  | [NEWS] US, Denmark and Greenland...   | news   | 15      | OPEN |
| #174  | [NEWS] Sadiq Khan to warn AI...       | news   | 15      | OPEN |
| #175  | [NEWS] Rachel Reeves signals...       | news   | 15      | OPEN |

**検証結果**:

-   ✅ 全 5 件に `[NEWS]` プレフィックス付与
-   ✅ 全 5 件に `news` ラベル付与
-   ✅ 全 5 件が Project 15 に登録
-   ✅ 全 5 件が OPEN 状態

### 区別戦略の実装状況

| 戦略                 | 実装状況 | 詳細                           |
| -------------------- | -------- | ------------------------------ |
| news ラベル          | ✅ 完了  | 既存 5 件 + 自動付与設定完了   |
| Project 分離         | ✅ 完了  | Project 15 に全件移動          |
| [NEWS]プレフィックス | ✅ 完了  | 既存 5 件 + 自動付与設定完了   |
| Issue テンプレート   | ✅ 完了  | news-article.md 作成完了      |
| 自動化設定           | ✅ 完了  | エージェント・コマンド修正完了 |

---

## 📝 変更ファイル一覧

### 修正ファイル

```
M  .claude/agents/finance-news-collector.md
   - 行270: タイトルに [NEWS] プレフィックス自動付与

M  .claude/commands/collect-finance-news.md
   - デフォルトProject: 14 → 15
   - 全Project参照を15に更新
   - Issue確認コマンド変更

M  .claude/skills/finance-news-collection/SKILL.md
   - 行435: Project 14 → 15 参照更新
```

### 新規ファイル

```
?? .github/ISSUE_TEMPLATE/news-article.md
   - 金融ニュース記事専用テンプレート
   - 自動ラベル・Project・プレフィックス設定
```

### git ステータス

```bash
# 2026-01-15時点
M .claude/agents/finance-news-collector.md
M .claude/commands/collect-finance-news.md
M .claude/settings.json
M .claude/skills/finance-news-collection/SKILL.md
?? .claude/sounds/
?? .github/ISSUE_TEMPLATE/news-article.md
```

**ステータス**: 全ての変更は `git add` 未実行、コミット未実施

---

## 🔄 未完了タスク（Phase 3）

### 優先度: 高

#### 1. 変更をコミット

```bash
git add .claude/agents/finance-news-collector.md \
        .claude/commands/collect-finance-news.md \
        .claude/skills/finance-news-collection/SKILL.md \
        .github/ISSUE_TEMPLATE/news-article.md

git commit -m "feat: ニュース記事と開発Issue区別機能を実装

- newsラベルを作成
- [NEWS]プレフィックスを自動付与
- Project 15 (Finance News Collection)に投稿先を変更
- 金融ニュース記事専用Issueテンプレート追加
- 既存ニュース記事(#171-175)を更新・移行"
```

#### 2. dry-run モードで動作確認

```bash
/collect-finance-news --dry-run --limit 5
```

**確認ポイント**:

-   フィルタリング処理が正常に動作
-   投稿候補の表示形式
-   エラーが発生しないこと

#### 3. 実際のニュース収集テスト

```bash
/collect-finance-news --limit 3
```

**確認ポイント**:

-   Issue 作成時に `[NEWS]` プレフィックスが付与される
-   `news` ラベルが自動付与される
-   Project 15 に自動追加される
-   カスタムフィールドが設定される（手動設定の場合は後で）

### 優先度: 中

#### 4. Project 15 カスタムフィールドの設定

**対象フィールド**:

-   カテゴリ（米国株/日本株/セクター/テーマ/マクロ/その他）
-   優先度（High/Medium/Low）
-   記事化状態（未着手/執筆中/完了）
-   情報源（フィード名）
-   収集日時

**設定方法**:

-   手動: Web UI から各 Issue のカスタムフィールドを設定
-   自動: エージェントにフィールド設定機能を追加（将来的に）

#### 5. Project 14 のクリーンアップ（オプション）

-   Project 14 に残っているニュース記事関連のアイテムを整理
-   必要に応じて Project 14 の説明を更新
-   開発タスク専用であることを明確化

---

## 🎯 実装された区別戦略の詳細

### 戦略 1: news ラベル

**実装**:

-   ラベル名: `news`
-   色: #FFA500（オレンジ）
-   自動付与: Issue テンプレート + エージェント

**使用方法**:

```bash
# ニュース記事のみ表示
gh issue list --label "news"

# 開発Issueのみ表示（ニュースを除外）
gh issue list --label "!news"
```

### 戦略 2: Project 分離

**実装**:

-   **Project 15**: Finance News Collection（ニュース専用）

    -   URL: https://github.com/users/YH-05/projects/15
    -   カスタムフィールド: カテゴリ、優先度、記事化状態、情報源、収集日時

-   **Project 14, その他**: 開発タスク専用
    -   Finance News Tracker は開発完了済み

**メリット**:

-   ニュースと開発タスクを完全に分離
-   カテゴリ別の視覚的整理
-   記事化の進捗管理

### 戦略 3: [NEWS] プレフィックス

**実装**:

-   Issue 作成時に自動付与: `[NEWS] {タイトル}`
-   既存 5 件にも手動付与済み

**メリット**:

-   Issue 一覧で一目で判別可能
-   通知でも区別しやすい
-   検索でも容易に識別

### 戦略 4: Issue テンプレート

**ファイル**: `.github/ISSUE_TEMPLATE/news-article.md`

**フィールド**:

-   概要（必須）
-   情報源 URL（必須）
-   公開日
-   信頼性スコア（必須）
-   カテゴリ（必須）
-   フィード/情報源名
-   優先度
-   備考・メモ

**自動設定**:

-   タイトル: `[NEWS] ` プレフィックス
-   ラベル: `news` 自動付与
-   Project: 15 に自動追加

---

## 🔍 トラブルシューティング

### Issue 作成時のエラー

#### E001: news ラベルが付与されない

**原因**: テンプレート設定の不備

**確認**:

```bash
cat .github/ISSUE_TEMPLATE/news-article.md | grep labels
```

**対処**:

```yaml
labels: ["news"] # この行があることを確認
```

#### E002: Project 15 に追加されない

**原因**: projects 設定の不備

**確認**:

```bash
cat .github/ISSUE_TEMPLATE/news-article.md | grep projects
```

**対処**:

```yaml
projects: ["YH-05/15"] # この行があることを確認
```

#### E003: [NEWS] プレフィックスが付与されない

**原因**: エージェントの設定ミス

**確認**:

```bash
grep "\\[NEWS\\]" .claude/agents/finance-news-collector.md
```

**対処**:

```bash
# 行270付近を確認
--title "[NEWS] {news_title}"  # この形式であることを確認
```

### /collect-finance-news コマンドのエラー

#### E004: Project 14 に投稿される

**原因**: コマンド設定の未更新

**確認**:

```bash
grep "project.*14" .claude/commands/collect-finance-news.md
```

**対処**: 全ての Project 14 参照を 15 に変更

#### E005: dry-run モードで動作しない

**原因**: エージェント実装の問題

**確認**: エージェントログを確認

**対処**: `.claude/agents/finance-news-collector.md` のエラーハンドリングセクション参照

---

## 📚 関連リソース

### GitHub Projects

-   **Project 15**: Finance News Collection

    -   URL: https://github.com/users/YH-05/projects/15
    -   ID: `PVT_kwHOBoK6AM4BMpw_`
    -   用途: 金融ニュース収集管理専用

-   **Project 14**: Finance News Tracker
    -   URL: https://github.com/users/YH-05/projects/14
    -   状態: 開発完了、In Progress なし
    -   用途: 旧ニュース管理（現在は非推奨）

### Project 15 カスタムフィールド ID

```
Status: PVTSSF_lAHOBoK6AM4BMpw_zg739ZE
カテゴリ: PVTSSF_lAHOBoK6AM4BMpw_zg739b4
優先度: PVTSSF_lAHOBoK6AM4BMpw_zg739eA
記事化状態: PVTSSF_lAHOBoK6AM4BMpw_zg739eI
情報源: PVTF_lAHOBoK6AM4BMpw_zg739d8
収集日時: PVTF_lAHOBoK6AM4BMpw_zg739d0
```

### 関連ファイル

-   エージェント: `.claude/agents/finance-news-collector.md`
-   コマンド: `.claude/commands/collect-finance-news.md`
-   スキル: `.claude/skills/finance-news-collection/SKILL.md`
-   テンプレート: `.github/ISSUE_TEMPLATE/news-article.md`
-   フィルター設定: `data/config/finance-news-filter.json`

### 関連ドキュメント

-   プロジェクト計画書: `docs/project/financial-news-rss-collector.md`
-   フィルタリング基準: `docs/finance-news-filtering-criteria.md`
-   使用方法ガイド: `docs/finance-news-collection-guide.md`

---

## 🚀 次回作業再開時のチェックリスト

### 1. 状況確認

```bash
# git ステータス確認
git status

# 変更ファイルの確認
git diff .claude/agents/finance-news-collector.md
git diff .claude/commands/collect-finance-news.md

# Project 15 の確認
gh project item-list 15 --owner YH-05 --format json | jq '.totalCount'

# news ラベル付きIssueの確認
gh issue list --label "news" --state all
```

### 2. コミット実行

```bash
git add .claude/agents/finance-news-collector.md \
        .claude/commands/collect-finance-news.md \
        .claude/skills/finance-news-collection/SKILL.md \
        .github/ISSUE_TEMPLATE/news-article.md

git commit -m "feat: ニュース記事と開発Issue区別機能を実装

- newsラベルを作成
- [NEWS]プレフィックスを自動付与
- Project 15 (Finance News Collection)に投稿先を変更
- 金融ニュース記事専用Issueテンプレート追加
- 既存ニュース記事(#171-175)を更新・移行"
```

### 3. 動作確認

```bash
# dry-run テスト
/collect-finance-news --dry-run --limit 5

# 実際の収集テスト（少量）
/collect-finance-news --limit 3
```

### 4. 検証ポイント

-   [ ] Issue 作成時に `[NEWS]` プレフィックスが付与される
-   [ ] `news` ラベルが自動付与される
-   [ ] Project 15 に自動追加される
-   [ ] Issue 一覧で視覚的に区別できる
-   [ ] `gh issue list --label "news"` でフィルタリング可能

### 5. カスタムフィールド設定（オプション）

-   [ ] 既存ニュース記事（#171-175）のカテゴリを設定
-   [ ] 優先度を設定
-   [ ] 記事化状態を「未着手」に設定

---

## 📝 メモ・備考

### 実装時の気づき

1. Issue テンプレートの `projects` 設定は `YH-05/15` という形式で指定
2. エージェントの行番号は変更される可能性があるため、検索で確認推奨
3. Project のカスタムフィールド設定は gh CLI でも可能だが Web UI が簡単

### 今後の改善案

1. カスタムフィールドの自動設定機能をエージェントに追加
2. RSS フィードのカテゴリと Project 15 のカテゴリフィールドを自動マッピング
3. 信頼性スコアに基づいた優先度の自動設定
4. 重複検出の精度向上（タイトル類似度の閾値調整）

### 参考コマンド

```bash
# ニュース記事のみ表示
gh issue list --label "news"

# Project 15 の内容確認
gh project view 15 --owner YH-05

# 特定Issueの詳細確認
gh issue view 171

# Project 15 のフィールド一覧
gh project field-list 15 --owner YH-05
```

---

**最終更新**: 2026-01-15
**次回アクション**: Phase 3（コミット・テスト）の実施
