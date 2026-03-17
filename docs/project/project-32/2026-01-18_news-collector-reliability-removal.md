# /collect-finance-news 信頼性スコア削除 & Issueタイトル日本語化計画

## 概要

`/collect-finance-news` コマンドから以下の変更を行う:
1. 信頼性スコア（reliability score）計算機能の削除
2. Issueタイトルを日本語で作成するよう指示を修正

## 変更対象ファイル

### 1. Pythonコード（信頼性スコア計算ロジック削除）

#### 1.1 `.claude/agents/finance_news_collector/filtering.py`
- **削除**: `calculate_reliability_score()` 関数（行122-209）
- キーワードマッチングと除外ロジックは維持

#### 1.2 `.claude/agents/finance_news_collector/transformation.py`
- **削除**: `from .filtering import calculate_reliability_score` (行8)
- **削除**: `reliability_score = calculate_reliability_score(item, filter_config)` (行52)
- **削除**: Issue bodyから `信頼性スコア` フィールド (行80)

### 2. 共通処理ガイド（信頼性スコア計算セクション削除）

#### 2.1 `.claude/agents/finance_news_collector/common-processing-guide.md`
- **削除**: ステップ2.3「信頼性スコアリング」セクション（行86-151）
- **削除**: Issue作成テンプレートから `信頼性スコア` フィールド（行281-283）
- **削除**: 結果報告の `信頼性: {score}/100` 表示（行391-392）
- **修正**: Issueタイトルを日本語で作成するルールを追加（行267付近）

### 3. コマンド定義

#### 3.1 `.claude/commands/collect-finance-news.md`
- **削除**: フロー説明から「信頼性スコア計算」（行213-214）
- **削除**: サマリー出力から `信頼性: XX/100` 表示（行246-247, 251-252, 256-257）
- **削除**: dry-runモード出力から `信頼性: XX/100`（行288-304）
- **削除**: 設定カスタマイズから `reliability_weight` 説明（行487）

### 4. テーマ別エージェント（5ファイル）

各ファイルに同様の変更を適用:
- `.claude/agents/finance-news-index.md`
- `.claude/agents/finance-news-stock.md`
- `.claude/agents/finance-news-sector.md`
- `.claude/agents/finance-news-macro.md`
- `.claude/agents/finance-news-ai.md`

**各ファイルでの変更**:
- **削除**: フロー説明から「信頼性スコアリング」
- **削除**: Issue作成テンプレートから `信頼性スコア` フィールド
- **削除**: 「信頼性スコア計算例」セクション
- **削除**: 実行ログ例から `信頼性: XX/100` 表示
- **削除**: テーブルから `Reliability Weight` 行
- **修正**: Issueタイトルを日本語で作成するルールを追加

### 5. 設定ファイル

#### 5.1 `data/config/finance-news-themes.json`
- **削除**: 各テーマの `reliability_weight` フィールド（行18, 34, 52, 71, 89）
- **削除**: `common.filtering.min_reliability_score` フィールド（行143）
- **削除**: `common.sources` 配下のTier分類（行113-140）は**保持**（フィルタリングで使用可能性あり）

## 詳細な変更内容

### Issue作成時のタイトルルール変更

**Before**:
```bash
gh issue create --title "[NEWS] {title}" ...
```
（タイトルは元記事のまま、言語不問）

**After**:
```bash
gh issue create --title "[{theme_ja}] {japanese_title}" ...
```

**日本語化ルール**:
1. **タイトル**: 英語記事の場合は日本語に翻訳（要約生成時に同時に翻訳）
2. **プレフィックス**: テーマ名は日本語
   - `[株価指数]`, `[個別銘柄]`, `[セクター]`, `[マクロ経済]`, `[AI]`

### 変更後のIssue作成テンプレート

```bash
gh issue create \
    --repo YH-05/quants \
    --title "[{theme_ja}] {japanese_title}" \
    --body "$(cat <<'EOF'
### 概要

{japanese_summary}

### 情報源URL

{link}

### 公開日

{published_jst}(JST)

### カテゴリ

{category}

### フィード/情報源名

{source}

### 備考・メモ

- テーマ: {theme_name}
- マッチキーワード: {matched_keywords}
EOF
)" \
    --label "news"
```

## 検証方法

1. **構文チェック**: 各markdownファイルの構文確認
2. **Pythonコード**: `filtering.py`, `transformation.py` のインポートエラー確認
3. **dry-runテスト**: `/collect-finance-news --dry-run --limit 5` でエラーなく実行確認
4. **実行テスト**: 1件の記事でIssue作成を確認し、タイトルが日本語であること確認

## 変更ファイル一覧（10ファイル）

| ファイル | 変更種類 |
|---------|---------|
| `.claude/agents/finance_news_collector/filtering.py` | 関数削除 |
| `.claude/agents/finance_news_collector/transformation.py` | インポート・呼び出し削除 |
| `.claude/agents/finance_news_collector/common-processing-guide.md` | セクション削除・ルール追加 |
| `.claude/commands/collect-finance-news.md` | 表示・説明削除 |
| `.claude/agents/finance-news-index.md` | テンプレート・セクション削除 |
| `.claude/agents/finance-news-stock.md` | テンプレート・セクション削除 |
| `.claude/agents/finance-news-sector.md` | テンプレート・セクション削除 |
| `.claude/agents/finance-news-macro.md` | テンプレート・セクション削除 |
| `.claude/agents/finance-news-ai.md` | テンプレート・セクション削除 |
| `data/config/finance-news-themes.json` | フィールド削除 |
