---
description: 週次マーケットレポートを自動生成します（データ収集→ニュース検索→レポート作成→Issue投稿）
argument-hint: [--date YYYY-MM-DD] [--weekly] [--weekly-comment] [--project 15] [--no-search]
---

# /generate-market-report - マーケットレポート生成

週次マーケットレポートを自動生成するコマンドです。

## モード比較

| モード | 説明 | GitHub Project 連携 | Issue 投稿 | 出力形式 |
|--------|------|-------------------|-----------|---------|
| 基本モード | 指定日のレポート生成 | なし | なし | 簡易レポート |
| `--weekly-comment` | 火曜〜火曜の週次コメント | **あり** | **自動** | 3000字以上のコメント |
| `--weekly` | **フル週次レポート（推奨）** | **あり** | **自動** | 5700字以上の詳細レポート |

`--weekly` は `--weekly-comment` の上位互換であり、GitHub Project からのニュース集約機能が追加されています。

**注意**: `--weekly` および `--weekly-comment` モードでは、レポート生成後に自動的に GitHub Issue が作成され、Project #15 に「Weekly Report」ステータスで登録されます。

## 使用例

```bash
# ========== 日付指定（YYYY-MM-DD形式）==========

# 基本的な使用方法（今日を終了日として1週間分のレポート生成）
/generate-market-report

# 特定の日付を終了日としてレポート生成
# 例: 2026-01-20 を終了日とし、2026-01-13 〜 2026-01-20 の1週間分
/generate-market-report --date 2026-01-20

# 過去の期間でレポート生成
# 例: 2026-01-15 を終了日とし、2026-01-08 〜 2026-01-15 の1週間分
/generate-market-report --date 2026-01-15

# ========== 週次レポートモード（推奨） ==========

# フル週次レポート生成（GitHub Project連携 + Issue自動投稿）
/generate-market-report --weekly

# 特定日付でフル週次レポート生成
/generate-market-report --weekly --date 2026-01-20

# 別の GitHub Project を使用
/generate-market-report --weekly --project 20

# GitHub Project のみ使用（追加検索なし）
/generate-market-report --weekly --no-search

# ========== 出力先指定 ==========

# 出力先を指定
/generate-market-report --output articles/market_report_20260119

# ========== 旧: 週次コメントモード（互換性維持） ==========

# 週次コメント生成モード（Issue自動投稿）
/generate-market-report --weekly-comment

# 週次コメント生成（日付指定）
/generate-market-report --weekly-comment --date 2026-01-20
```

## 入力パラメータ

| パラメータ | 必須 | デフォルト | 説明 |
|-----------|------|-----------|------|
| --date | - | 今日の日付 | **レポート終了日（YYYY-MM-DD形式）。この日付から1週間前が開始日となる** |
| --output | - | articles/market_report_{date} または articles/weekly_report/{date} | 出力ディレクトリ |
| --weekly | - | false | **フル週次レポート生成モード（GitHub Project 連携 + Issue 自動投稿、推奨）** |
| --weekly-comment | - | false | 週次コメント生成モード（Issue 自動投稿、旧形式） |
| --project | - | 15 | GitHub Project 番号（--weekly モード時のみ有効） |
| --no-search | - | false | 追加検索を無効化（--weekly モード時のみ有効、GitHub Project のニュースのみ使用） |

### 日付と期間の計算

`--date` で指定した日付が**終了日**となり、**開始日は終了日の7日前**に自動計算されます。

```
例: --date 2026-01-20
  開始日: 2026-01-13
  終了日: 2026-01-20
  期間: 2026-01-13 〜 2026-01-20（7日間）
```

**注意**: `--date` を省略した場合は今日の日付が終了日となります。

## 処理フロー

### 基本モード

```
Phase 1: 初期化
├── 引数解析・出力ディレクトリ作成
├── 必要ツール確認（RSS MCP, Tavily, gh）
└── テンプレート確認

Phase 2: データ収集
├── Pythonスクリプト実行（market_report_data.py）
├── returns.json 読み込み
├── sectors.json 読み込み
└── earnings.json 読み込み

Phase 3: ニュース検索
├── 指数関連ニュース検索
├── MAG7/半導体関連ニュース検索
├── セクター関連ニュース検索
└── 決算関連ニュース検索

Phase 4: レポート生成
├── テンプレート読み込み
├── データ埋め込み
├── ニュースコンテキスト追加
└── Markdownファイル出力

Phase 5: 完了処理
└── 結果サマリー表示
```

### --weekly モード（フル週次レポート）

```
Phase 1: 初期化
├── 対象期間の計算（--date から7日前 〜 --date）
│   └── 例: --date 2026-01-20 → 2026-01-13 〜 2026-01-20
├── 出力ディレクトリ作成
│   └── articles/weekly_report/{YYYY-MM-DD}/
├── 必要ツール確認（gh CLI）
├── テンプレート確認
│   └── template/market_report/weekly_market_report_template.md
└── weekly-report-lead に委譲（Agent Teams ワークフロー）

Phase 2: 市場データ収集（★PerformanceAnalyzer4Agent使用）
├── Pythonスクリプト実行（collect_market_performance.py）
├── data/market/ に出力:
│   ├── indices_us_{YYYYMMDD-HHMM}.json（複数期間: 1D, 1W, MTD, YTD...）
│   ├── indices_global_{YYYYMMDD-HHMM}.json
│   ├── mag7_{YYYYMMDD-HHMM}.json（複数期間 + サマリー）
│   ├── sectors_{YYYYMMDD-HHMM}.json（複数期間 + サマリー）
│   ├── commodities_{YYYYMMDD-HHMM}.json
│   └── all_performance_{YYYYMMDD-HHMM}.json（統合）
└── データ鮮度チェック（日付ズレ警告）

Phase 3: 仮説生成（★新規）
├── market-hypothesis-generator サブエージェント呼び出し
├── パターン検出:
│   ├── 期間間乖離（1D vs 1W, トレンド継続/反転）
│   ├── グループ間比較（MAG7 vs SPX, Growth vs Value）
│   └── セクターローテーション
├── 仮説生成（背景要因の推測）
├── 検索クエリ計画
└── hypotheses_{YYYYMMDD-HHMM}.json に出力

Phase 4: ニュース調査（★仮説ベース検索）
├── GitHub Project から既存ニュース取得
│   └── weekly-report-news-aggregator → news_from_project.json
├── 仮説ベースの追加検索（--no-search でスキップ可能）
│   ├── hypotheses.json の検索クエリを優先度順に実行
│   ├── RSS MCP / Tavily で検索
│   └── 検索結果を仮説IDと紐づけ
└── news_with_context.json に出力（仮説との関連付き）

Phase 5: レポート生成（サブエージェント）
├── weekly-report-writer 呼び出し
├── データ集約（weekly-data-aggregation スキル）
├── コメント生成（weekly-comment-generation スキル）
│   └── 仮説と検索結果を統合してコメント作成
├── テンプレート埋め込み（weekly-template-rendering スキル）
├── 品質検証（weekly-report-validation スキル）
└── 02_edit/weekly_report.md に出力

Phase 6: 品質検証
├── 文字数確認（目標: 3200字以上）
├── セクション別文字数確認
├── データ整合性チェック
└── validation_result.json に結果出力

Phase 7: Issue 投稿（自動実行）
├── weekly-report-publisher 呼び出し
├── GitHub Issue 作成（`--label "report"` 付与）
├── Project #{project} に追加（Status: Weekly Report）
├── 公開日時フィールドを設定
└── Issue URL を出力

Phase 8: 完了処理
└── 結果サマリー表示
```

---

## Phase 1: 初期化

### 1.1 引数解析

```bash
# デフォルト値の設定
DATE=$(date +%Y%m%d)
OUTPUT_DIR="articles/market_report_${DATE}"

# 引数が指定されている場合は上書き
# --output: 出力ディレクトリ
# --date: レポート対象日
```

### 1.2 出力ディレクトリ作成

```bash
mkdir -p "${OUTPUT_DIR}/data"
mkdir -p "${OUTPUT_DIR}/02_edit"
```

**ディレクトリ構造**:
```
{OUTPUT_DIR}/
├── data/
│   ├── returns.json        # 騰落率データ
│   ├── sectors.json        # セクター分析
│   ├── earnings.json       # 決算カレンダー
│   └── news_context.json   # ニュース検索結果
└── 02_edit/
    └── report.md           # Markdownレポート
```

### 1.3 必要ツール確認

#### RSS MCP ツール確認（リトライ機能付き）

```
[試行1] キーワード検索でRSS MCPツールを検索
MCPSearch: query="rss", max_results=5

↓ ツールが見つかった場合
成功 → 次へ

↓ ツールが見つからない場合
[待機] 3秒待機
[試行2] 再度検索

↓ それでも見つからない場合
警告表示（RSS検索スキップ）→ 他の検索手段で続行
```

#### Tavily ツール確認

```
MCPSearch: query="tavily", max_results=3

↓ ツールが見つかった場合
成功 → 次へ

↓ 見つからない場合
警告表示（Tavily検索スキップ）→ 他の検索手段で続行
```

#### GitHub CLI 確認

```bash
if ! command -v gh &> /dev/null; then
    echo "警告: GitHub CLI (gh) がインストールされていません"
fi
```

### 1.4 テンプレート確認

```bash
TEMPLATE_FILE="template/market_report/02_edit/first_draft.md"
if [ ! -f "$TEMPLATE_FILE" ]; then
    echo "エラー: テンプレートファイルが見つかりません"
    echo "期待されるパス: $TEMPLATE_FILE"
    exit 1
fi
```

---

## Phase 2: データ収集

### 2.1 Pythonスクリプト実行

```bash
uv run python scripts/market_report_data.py --output "${OUTPUT_DIR}/data"
```

**出力ファイル**:
- `returns.json`: 騰落率データ（主要指数、MAG7、セクターETF、グローバル指数）
- `sectors.json`: セクター分析データ（上位/下位セクター）
- `earnings.json`: 決算カレンダーデータ

**エラーハンドリング**:
```
↓ スクリプト実行成功
成功 → 次へ

↓ スクリプト実行失敗
エラー報告:
  - エラー内容を表示
  - 部分的に成功したファイルがあれば続行
  - 全て失敗した場合は処理中断
```

### 2.2 JSONファイル読み込み

各JSONファイルを読み込み、構造化データとして保持:

```python
# returns.json の構造
{
  "as_of": "2026-01-19",
  "indices": [...],      # 主要指数
  "mag7": [...],         # Magnificent 7
  "sectors": [...],      # セクターETF
  "global": [...]        # グローバル指数
}

# sectors.json の構造
{
  "as_of": "2026-01-19",
  "period": "1W",
  "top_sectors": [...],    # 上位3セクター
  "bottom_sectors": [...]  # 下位3セクター
}

# earnings.json の構造
{
  "generated_at": "2026-01-19",
  "upcoming_earnings": [...]  # 今後2週間の決算予定
}
```

---

## Phase 3: ニュース検索

### 3.1 検索優先順位

1. **RSS MCP**: `mcp__rss__rss_search_items`（33フィード、高速）
2. **Tavily**: `mcp__tavily__tavily-search`（Web全体検索）
3. **Gemini Search**: `/gemini-search` スキル（バックアップ）
4. **Fetch**: `mcp__fetch__fetch`（特定URL取得）

### 3.2 カテゴリ別ニュース検索

#### 指数関連ニュース

```python
keywords = ["S&P 500", "NASDAQ", "Dow Jones", "日経平均", "TOPIX", "株価指数"]
# RSS MCPで検索
# 結果が不足していればTavilyで補完
```

#### MAG7/半導体関連ニュース

```python
keywords = ["Apple", "Microsoft", "Google", "Amazon", "NVIDIA", "Meta", "Tesla", "半導体", "AI"]
# RSS MCPで検索
# 結果が不足していればTavilyで補完
```

#### セクター関連ニュース

```python
# sectors.json の top_sectors, bottom_sectors から動的にキーワード生成
keywords = [sector["name"] for sector in top_sectors + bottom_sectors]
# RSS MCPで検索
# 結果が不足していればTavilyで補完
```

#### 決算関連ニュース

```python
# earnings.json の upcoming_earnings から動的にキーワード生成
keywords = [earning["symbol"] + " 決算" for earning in upcoming_earnings[:5]]
# RSS MCPで検索
# 結果が不足していればTavilyで補完
```

### 3.3 検索結果の保存

```python
# news_context.json の構造
{
  "searched_at": "2026-01-19T10:00:00Z",
  "categories": {
    "indices": [
      {
        "title": "記事タイトル",
        "source": "Bloomberg",
        "url": "https://...",
        "published": "2026-01-18T...",
        "summary": "記事要約"
      }
    ],
    "mag7": [...],
    "sectors": [...],
    "earnings": [...]
  }
}
```

保存先: `${OUTPUT_DIR}/data/news_context.json`

---

## Phase 4: レポート生成

### 4.1 テンプレート読み込み

```bash
cat template/market_report/02_edit/first_draft.md
```

### 4.2 データ埋め込み

テンプレートのプレースホルダーを実データで置換:

#### 主要指数テーブル

```markdown
| 指数 | 終値 | 1D (%) | 1W (%) | MTD (%) | YTD (%) | 1Y (%) |
|------|------|--------|--------|---------|---------|--------|
| S&P 500 | 6,012.45 | +0.25 | +1.50 | +2.30 | +5.20 | +25.30 |
| ... |
```

#### Magnificent 7 テーブル

```markdown
| 銘柄 | ティッカー | 終値 | 1W (%) | 背景 |
|------|-----------|------|--------|------|
| Apple | AAPL | 245.50 | -2.30 | AI競争激化、幹部退職報道 |
| ... |
```

#### セクター分析テーブル

```markdown
### 上位3セクター
| セクター | 1W (%) | 代表銘柄 | 寄与度 |
|----------|--------|----------|--------|
| IT | +2.50 | AAPL, MSFT | 高 |
| ... |
```

#### 決算発表予定テーブル

```markdown
| 日付 | 銘柄 | ティッカー | EPS予想 | 売上予想 | 着目ポイント |
|------|------|-----------|---------|----------|-------------|
| 01/22 | Apple | AAPL | $2.10 | $119B | AI戦略、Vision Pro販売 |
| ... |
```

### 4.3 ニュースコンテキスト追加

各セクションの「ニュースコンテキスト」部分に、Phase 3で収集したニュースを挿入:

```markdown
**ニュースコンテキスト:**
- [記事タイトル1](URL) - ソース名
- [記事タイトル2](URL) - ソース名
```

### 4.4 Markdownファイル出力

```bash
# 出力先
${OUTPUT_DIR}/02_edit/report.md
```

**日付の置換**:
- `{date}` → `2026年1月19日`
- `{week}` → `第3週`

---

## Phase 5: 完了処理

### 5.1 結果サマリー表示

```markdown
================================================================================
                    /generate-market-report 完了
================================================================================

## 生成されたファイル

| ファイル | パス | サイズ |
|----------|------|--------|
| 騰落率データ | {output}/data/returns.json | 15KB |
| セクター分析 | {output}/data/sectors.json | 8KB |
| 決算カレンダー | {output}/data/earnings.json | 5KB |
| ニュースコンテキスト | {output}/data/news_context.json | 12KB |
| **レポート** | {output}/02_edit/report.md | 25KB |

## データサマリー

### 主要指数
- S&P 500: +1.50% (1W)
- NASDAQ: +2.30% (1W)
- 日経平均: -0.50% (1W)

### 上位セクター
1. IT: +2.50%
2. エネルギー: +1.80%
3. 金融: +1.20%

### 下位セクター
1. ヘルスケア: -2.90%
2. 公益: -2.20%
3. 素材: -1.50%

### 決算予定（今後2週間）
- {count}社の決算発表予定

### ニュース検索結果
- 指数関連: {count}件
- MAG7関連: {count}件
- セクター関連: {count}件
- 決算関連: {count}件

## 次のアクション

1. レポートを確認:
   cat {output}/02_edit/report.md

2. 編集・修正:
   edit {output}/02_edit/report.md

3. 公開準備:
   cp {output}/02_edit/report.md {output}/03_published/{date}_weekly_market_report.md

================================================================================
```

---

## エラーハンドリング

### E001: Pythonスクリプト実行エラー

**発生条件**:
- `scripts/market_report_data.py` が存在しない
- 依存モジュールのインポートエラー
- ネットワークエラー（Yahoo Finance API）

**対処法**:
```
エラー: Pythonスクリプトの実行に失敗しました

確認項目:
1. スクリプトが存在するか確認:
   ls scripts/market_report_data.py

2. 依存関係を確認:
   uv sync --all-extras

3. スクリプトを直接実行してエラー内容を確認:
   uv run python scripts/market_report_data.py --output .tmp/test

4. ネットワーク接続を確認
```

### E002: RSS MCP ツールエラー

**発生条件**:
- RSS MCPサーバーが起動していない
- MCPサーバーの起動が完了していない

**対処法**:
- 3秒待機して再試行（自動）
- 2回失敗した場合は警告を表示し、他の検索手段で続行

### E003: Tavily ツールエラー

**発生条件**:
- Tavily MCPツールが設定されていない
- APIキーが無効

**対処法**:
- 警告を表示し、他の検索手段で続行

### E004: テンプレートエラー

**発生条件**:
- テンプレートファイルが存在しない
- テンプレートの構造が不正

**対処法**:
```
エラー: テンプレートファイルが見つかりません

期待されるパス: template/market_report/02_edit/first_draft.md

対処法:
1. テンプレートディレクトリを確認:
   ls template/market_report/

2. テンプレートを復元:
   git checkout template/market_report/02_edit/first_draft.md
```

### E005: 出力ディレクトリエラー

**発生条件**:
- ディレクトリ作成権限がない
- ディスク容量不足

**対処法**:
```
エラー: 出力ディレクトリを作成できません

対処法:
1. 権限を確認:
   ls -la articles/

2. 手動でディレクトリを作成:
   mkdir -p articles/market_report_{date}/data
   mkdir -p articles/market_report_{date}/02_edit
```

---

# フル週次レポートモード（--weekly）

`--weekly` オプションを指定すると、GitHub Project と連携した詳細な週次マーケットレポート
（3200字以上）を生成します。これは `--weekly-comment` の上位互換モードです。

## --weekly と --weekly-comment の違い

| 項目 | --weekly | --weekly-comment |
|------|----------|-----------------|
| ニュース取得 | GitHub Project + 追加検索 | RSS/Tavily のみ |
| カテゴリ分類 | 6カテゴリ（自動分類） | 3カテゴリ（手動） |
| 目標文字数 | 3200字以上 | 3000字以上 |
| テンプレート | weekly_market_report_template.md | weekly_comment_template.md |
| 品質検証 | あり（スコア評価） | なし |
| サブエージェント | 3つ使用 | ニュース収集のみ |
| 出力ディレクトリ | articles/weekly_report/{date}/ | articles/weekly_comment_{date}/ |

## --weekly 処理フロー詳細

### Phase 1: 初期化

#### 1.1 対象期間の計算

```python
from datetime import date, timedelta

# --date オプションで指定された日付を終了日とする（省略時は今日）
end_date = date.fromisoformat(args.date) if args.date else date.today()

# 開始日は終了日の7日前
start_date = end_date - timedelta(days=7)

# 例: --date 2026-01-20 の場合
# start_date = 2026-01-13
# end_date = 2026-01-20
```

#### 1.2 出力ディレクトリ作成

```bash
# デフォルトパス（--weekly モード）
OUTPUT_DIR="articles/weekly_report/${REPORT_DATE}"

# 構造作成
mkdir -p "${OUTPUT_DIR}/data"
mkdir -p "${OUTPUT_DIR}/02_edit"
mkdir -p "${OUTPUT_DIR}/03_published"
```

**ディレクトリ構造**:
```
articles/weekly_report/{YYYY-MM-DD}/
├── data/
│   ├── indices.json          # 指数パフォーマンス
│   ├── mag7.json             # MAG7 パフォーマンス
│   ├── sectors.json          # セクター分析
│   ├── metadata.json         # 期間・生成情報
│   ├── news_from_project.json # GitHub Project からのニュース
│   ├── news_supplemental.json # 追加検索結果（--no-search がない場合）
│   ├── aggregated_data.json  # 集約データ
│   └── comments.json         # 生成コメント
├── 02_edit/
│   ├── weekly_report.md      # Markdown レポート
│   └── weekly_report.json    # 構造化データ
├── 03_published/
│   └── (公開用に編集後の最終版)
└── validation_result.json    # 品質検証結果
```

#### 1.3 必要ツール確認

```bash
# GitHub CLI 確認（必須）
if ! command -v gh &> /dev/null; then
    echo "エラー: GitHub CLI (gh) がインストールされていません"
    exit 1
fi

# 認証確認
gh auth status || {
    echo "エラー: GitHub CLI が認証されていません"
    echo "対処法: gh auth login を実行"
    exit 1
}
```

### Phase 2: 市場データ収集

```bash
uv run python scripts/collect_weekly_report_data.py \
    --start ${START_DATE} \
    --end ${END_DATE} \
    --output "${OUTPUT_DIR}/data"
```

**出力ファイル**（全7ファイル）:

#### indices.json
```json
{
  "period": {"start": "2026-01-14", "end": "2026-01-21"},
  "indices": [
    {
      "ticker": "^GSPC",
      "name": "S&P 500",
      "weekly_return": 0.025,
      "ytd_return": 0.032,
      "price": null,
      "change": null
    },
    {
      "ticker": "RSP",
      "name": "S&P 500 Equal Weight",
      "weekly_return": 0.018,
      "ytd_return": 0.021,
      "price": null,
      "change": null
    },
    {
      "ticker": "VUG",
      "name": "Vanguard Growth ETF",
      "weekly_return": 0.032,
      "ytd_return": 0.041,
      "price": null,
      "change": null
    },
    {
      "ticker": "VTV",
      "name": "Vanguard Value ETF",
      "weekly_return": 0.012,
      "ytd_return": 0.015,
      "price": null,
      "change": null
    }
  ]
}
```

#### mag7.json
```json
{
  "period": {"start": "2026-01-14", "end": "2026-01-21"},
  "mag7": [
    {
      "ticker": "TSLA",
      "name": "Tesla",
      "weekly_return": 0.037,
      "ytd_return": 0.052,
      "price": null,
      "market_cap": 900000000000
    },
    {
      "ticker": "AMZN",
      "name": "Amazon",
      "weekly_return": 0.028,
      "ytd_return": 0.035,
      "price": null,
      "market_cap": 2200000000000
    },
    {
      "ticker": "MSFT",
      "name": "Microsoft",
      "weekly_return": 0.022,
      "ytd_return": 0.028,
      "price": null,
      "market_cap": 3100000000000
    },
    {
      "ticker": "NVDA",
      "name": "NVIDIA",
      "weekly_return": 0.019,
      "ytd_return": 0.045,
      "price": null,
      "market_cap": 2800000000000
    },
    {
      "ticker": "AAPL",
      "name": "Apple",
      "weekly_return": 0.015,
      "ytd_return": 0.018,
      "price": null,
      "market_cap": 3800000000000
    },
    {
      "ticker": "GOOGL",
      "name": "Alphabet",
      "weekly_return": -0.008,
      "ytd_return": 0.005,
      "price": null,
      "market_cap": 2000000000000
    },
    {
      "ticker": "META",
      "name": "Meta",
      "weekly_return": -0.012,
      "ytd_return": 0.010,
      "price": null,
      "market_cap": 1500000000000
    }
  ],
  "sox": {
    "ticker": "^SOX",
    "name": "Philadelphia Semiconductor",
    "weekly_return": 0.031,
    "ytd_return": 0.042,
    "price": null
  }
}
```

#### sectors.json
```json
{
  "period": {"start": "2026-01-14", "end": "2026-01-21"},
  "top_sectors": [
    {
      "ticker": "XLK",
      "name": "Technology",
      "weekly_return": 0.025,
      "ytd_return": 0.038,
      "weight": null,
      "top_holdings": []
    },
    {
      "ticker": "XLE",
      "name": "Energy",
      "weekly_return": 0.018,
      "ytd_return": 0.022,
      "weight": null,
      "top_holdings": []
    },
    {
      "ticker": "XLF",
      "name": "Financials",
      "weekly_return": 0.012,
      "ytd_return": 0.015,
      "weight": null,
      "top_holdings": []
    }
  ],
  "bottom_sectors": [
    {
      "ticker": "XLV",
      "name": "Healthcare",
      "weekly_return": -0.029,
      "ytd_return": -0.015,
      "weight": null,
      "top_holdings": []
    },
    {
      "ticker": "XLU",
      "name": "Utilities",
      "weekly_return": -0.022,
      "ytd_return": -0.010,
      "weight": null,
      "top_holdings": []
    },
    {
      "ticker": "XLB",
      "name": "Materials",
      "weekly_return": -0.015,
      "ytd_return": -0.008,
      "weight": null,
      "top_holdings": []
    }
  ],
  "all_sectors": [...]
}
```

#### interest_rates.json
```json
{
  "group": "interest_rates",
  "generated_at": "2026-01-22T09:30:00",
  "periods": ["1D", "1W", "1M"],
  "data": {
    "DGS10": {
      "latest": 4.625,
      "changes": {"1D": 0.02, "1W": 0.08, "1M": 0.15}
    },
    "DGS2": {
      "latest": 4.325,
      "changes": {"1D": -0.01, "1W": 0.05, "1M": 0.10}
    },
    "DGS30": {
      "latest": 4.825,
      "changes": {"1D": 0.03, "1W": 0.09, "1M": 0.18}
    }
  },
  "yield_curve": {
    "is_inverted": false,
    "spread_10y_2y": 0.30
  },
  "data_freshness": {
    "newest_date": "2026-01-21",
    "oldest_date": "2026-01-21",
    "has_date_gap": false
  }
}
```

#### currencies.json
```json
{
  "group": "currencies",
  "subgroup": "jpy_crosses",
  "base_currency": "JPY",
  "generated_at": "2026-01-22T09:30:00",
  "periods": ["1D", "1W", "1M"],
  "symbols": {
    "USDJPY=X": {"1D": 0.16, "1W": 0.85, "1M": 2.30},
    "EURJPY=X": {"1D": -0.05, "1W": 0.42, "1M": 1.50},
    "GBPJPY=X": {"1D": 0.10, "1W": 0.65, "1M": 1.80}
  },
  "summary": {
    "strongest_currency": {"symbol": "USDJPY=X", "period": "1M", "return_pct": 2.30},
    "weakest_currency": {"symbol": "EURJPY=X", "period": "1D", "return_pct": -0.05},
    "period_averages": {"1D": 0.07, "1W": 0.64, "1M": 1.87}
  },
  "latest_dates": {
    "USDJPY=X": "2026-01-21",
    "EURJPY=X": "2026-01-21",
    "GBPJPY=X": "2026-01-21"
  },
  "data_freshness": {
    "newest_date": "2026-01-21",
    "oldest_date": "2026-01-21",
    "has_date_gap": false
  }
}
```

#### upcoming_events.json
```json
{
  "group": "upcoming_events",
  "generated_at": "2026-01-22T09:30:00+00:00",
  "period": {"start": "2026-01-23", "end": "2026-01-29"},
  "earnings": [
    {
      "ticker": "AAPL",
      "company_name": "Apple Inc.",
      "earnings_date": "2026-01-27",
      "timing": "AMC"
    },
    {
      "ticker": "META",
      "company_name": "Meta Platforms Inc.",
      "earnings_date": "2026-01-28",
      "timing": "AMC"
    }
  ],
  "economic_releases": [
    {
      "name": "FOMC Meeting",
      "release_date": "2026-01-28",
      "importance": "high",
      "description": "Federal Open Market Committee Interest Rate Decision"
    },
    {
      "name": "GDP (Advance)",
      "release_date": "2026-01-29",
      "importance": "high",
      "description": "Q4 2025 GDP Advance Estimate"
    }
  ],
  "summary": {
    "earnings_count": 2,
    "economic_release_count": 2,
    "high_importance_count": 2,
    "busiest_date": "2026-01-28"
  }
}
```

#### metadata.json
```json
{
  "generated_at": "2026-01-22T09:30:00",
  "period": {
    "start": "2026-01-14",
    "end": "2026-01-21",
    "start_jp": "1月14日",
    "end_jp": "1月21日",
    "start_us": "Jan 14",
    "end_us": "Jan 21"
  },
  "mode": "weekly",
  "files": {
    "indices.json": "ok",
    "mag7.json": "ok",
    "sectors.json": "ok",
    "interest_rates.json": "ok",
    "currencies.json": "ok",
    "upcoming_events.json": "ok",
    "metadata.json": "ok"
  }
}
```

### Phase 3: GitHub Project ニュース取得

```python
# weekly-report-news-aggregator サブエージェントを呼び出し
Task(
    subagent_type="weekly-report-news-aggregator",
    description="GitHub Project からニュース取得",
    prompt=f"""
GitHub Project #{project_number} から対象期間のニュースを取得してください。

## 入力パラメータ

start: {START_DATE}
end: {END_DATE}
project_number: {project_number}

## 出力先

{OUTPUT_DIR}/data/news_from_project.json

## 期待される処理

1. gh project item-list {project_number} で Issue を取得
2. 対象期間でフィルタリング（{START_DATE} 〜 {END_DATE}）
3. カテゴリ分類（indices/mag7/sectors/macro/tech/finance）
4. JSON 形式で出力
"""
)
```

**出力形式（news_from_project.json）**:
```json
{
  "period": {"start": "2026-01-14", "end": "2026-01-21"},
  "project_number": 15,
  "generated_at": "2026-01-22T09:35:00Z",
  "total_count": 25,
  "news": [
    {
      "issue_number": 171,
      "title": "Fed signals potential rate pause",
      "category": "macro",
      "url": "https://github.com/YH-05/finance/issues/171",
      "created_at": "2026-01-15T08:30:00Z",
      "summary": "FRBが利上げ停止の可能性を示唆...",
      "original_url": "https://..."
    }
  ],
  "by_category": {
    "indices": [...],
    "mag7": [...],
    "sectors": [...],
    "macro": [...],
    "tech": [...],
    "finance": [],
    "other": []
  },
  "statistics": {
    "indices": 3,
    "mag7": 5,
    "sectors": 4,
    "macro": 8,
    "tech": 3,
    "finance": 2,
    "other": 0
  }
}
```

### Phase 4: 追加ニュース検索

`--no-search` オプションが指定されていない場合、カテゴリ別の件数を確認し、
不足しているカテゴリについて追加検索を実行します。

**判定基準**:
| カテゴリ | 最低件数 | 不足時の対処 |
|---------|---------|-------------|
| indices | 2件 | RSS/Tavily で追加検索 |
| mag7 | 3件 | RSS/Tavily で追加検索 |
| sectors | 2件 | RSS/Tavily で追加検索 |
| macro | 2件 | RSS/Tavily で追加検索 |

```python
# 追加検索が必要な場合
if not no_search:
    for category, min_count in CATEGORY_MIN_COUNTS.items():
        if news_statistics[category] < min_count:
            # RSS MCP で検索
            rss_results = rss_search(CATEGORY_KEYWORDS[category])

            # 不足が続く場合は Tavily で補完
            if len(rss_results) < min_count:
                tavily_results = tavily_search(CATEGORY_KEYWORDS[category])

    # 結果を news_supplemental.json に保存
```

**出力形式（news_supplemental.json）**:
```json
{
  "searched_at": "2026-01-22T09:40:00Z",
  "reason": "カテゴリ別ニュース補完",
  "search_queries": [
    {"category": "sectors", "query": "sector rotation energy healthcare"},
    {"category": "macro", "query": "Federal Reserve interest rate policy"}
  ],
  "results": [
    {
      "category": "sectors",
      "title": "Energy sector leads market rally",
      "source": "RSS Feed",
      "url": "https://...",
      "published": "2026-01-20T14:00:00Z",
      "summary": "エネルギーセクターが市場上昇をリード..."
    }
  ],
  "statistics": {
    "sectors": 2,
    "macro": 1
  }
}
```

### Phase 5: レポート生成（Agent Teams）

Phase 1（初期化）完了後に `weekly-report-lead` エージェントに制御を委譲し、Agent Teams ワークフローでレポートを生成します。

```
weekly-report-lead（Agent Teams ワークフロー）
├── TeamCreate: weekly-report-team を作成
├── TaskCreate: 6タスクを登録（直列依存関係）
│   ├── task-1: wr-news-aggregator（ニュース集約）
│   ├── task-2: wr-data-aggregator（データ集約）← blockedBy: task-1
│   ├── task-3: wr-comment-generator（コメント生成）← blockedBy: task-2
│   ├── task-4: wr-template-renderer（テンプレート埋め込み）← blockedBy: task-3
│   ├── task-5: wr-report-validator（品質検証）← blockedBy: task-4
│   └── task-6: wr-report-publisher（Issue投稿）← blockedBy: task-5
├── 各チームメイトを起動・タスク割り当て
├── 実行監視（SendMessage 受信）
├── 全タスク完了後シャットダウン
└── TeamDelete でクリーンアップ
```

### Phase 6: 品質検証

Phase 5 で生成された `validation_result.json` を確認します。

**検証項目**:
1. **フォーマット検証**: Markdown 構文、テーブル形式
2. **文字数検証**: 合計 3200 字以上、セクション別
3. **データ整合性検証**: 数値の妥当性、日付の整合性
4. **LLM レビュー**: 内容品質（スコア評価）

**検証結果形式（validation_result.json）**:
```json
{
  "status": "PASS",
  "score": 95,
  "grade": "A",
  "checks": {
    "format": {"status": "PASS", "issues": []},
    "character_count": {
      "status": "PASS",
      "total": 3450,
      "target": 3200,
      "by_section": {...}
    },
    "data_integrity": {"status": "PASS", "issues": []},
    "content_quality": {
      "status": "PASS",
      "score": 95,
      "feedback": "..."
    }
  },
  "warnings": [],
  "recommendations": []
}
```

**グレード基準**:
| グレード | スコア | 判定 |
|---------|-------|------|
| A | 90-100 | 優秀 |
| B | 80-89 | 良好 |
| C | 70-79 | 可（警告あり） |
| D | 60-69 | 要改善 |
| F | 0-59 | 不合格 |

### Phase 7: Issue 投稿（自動実行）

レポート生成後、自動的に GitHub Issue として投稿します。

```python
# weekly-report-publisher サブエージェントを呼び出し
Task(
    subagent_type="weekly-report-publisher",
    description="週次レポート Issue 投稿",
    prompt=f"""
週次レポートを GitHub Issue として投稿してください。

## 入力パラメータ

report_dir: {OUTPUT_DIR}
project_number: {project_number}

## 期待される処理（必須）

1. {OUTPUT_DIR}/data/ からデータ読み込み
2. {OUTPUT_DIR}/02_edit/weekly_report.md からレポート読み込み
3. Issue 本文を生成
4. **GitHub Issue を作成（`--label "report"` を必ず付与）**
5. **GitHub Project #{project_number} に追加（`gh project item-add` 実行）**
6. **Status を "Weekly Report" に設定（GraphQL API 実行）**
7. **公開日時フィールドを設定**

## 重要な確認事項

- [ ] Issue に `report` ラベルが付与されているか確認
- [ ] Issue が Project #{project_number} に追加されているか確認
- [ ] Status が "Weekly Report" に設定されているか確認
- [ ] 結果出力に Project 登録情報（Item ID, Status）を含める
"""
)
```

### Phase 8: 完了処理

**成功時の出力**:
```markdown
================================================================================
                    /generate-market-report --weekly 完了
================================================================================

## 生成されたファイル

| ファイル | パス | サイズ |
|----------|------|--------|
| 指数データ | articles/weekly_report/2026-01-22/data/indices.json | 2KB |
| MAG7データ | articles/weekly_report/2026-01-22/data/mag7.json | 3KB |
| セクターデータ | articles/weekly_report/2026-01-22/data/sectors.json | 5KB |
| Project ニュース | articles/weekly_report/2026-01-22/data/news_from_project.json | 15KB |
| 追加検索結果 | articles/weekly_report/2026-01-22/data/news_supplemental.json | 3KB |
| 集約データ | articles/weekly_report/2026-01-22/data/aggregated_data.json | 20KB |
| コメント | articles/weekly_report/2026-01-22/data/comments.json | 12KB |
| **レポート** | **articles/weekly_report/2026-01-22/02_edit/weekly_report.md** | **15KB** |
| 検証結果 | articles/weekly_report/2026-01-22/validation_result.json | 2KB |

## データサマリー

### 対象期間
- **開始日**: 2026-01-14（火）
- **終了日**: 2026-01-21（火）
- **レポート日**: 2026-01-22（水）

### 主要指数
- S&P 500: +2.50%
- 等ウェイト (RSP): +1.80%
- グロース (VUG): +3.20%
- バリュー (VTV): +1.20%

### MAG7 サマリー
- トップ: TSLA +3.70%
- ボトム: META -1.20%

### セクター
- 上位: Technology (+2.50%), Energy (+1.80%), Financials (+1.20%)
- 下位: Healthcare (-2.90%), Utilities (-2.20%), Materials (-1.50%)

### ニュース統計
- GitHub Project: 25件
- 追加検索: 3件
- 合計: 28件

## 品質検証

- **スコア**: 95/100（グレード: A）
- **文字数**: 3,450字（目標: 3,200字）✓
- **ステータス**: PASS ✓

## 投稿された Issue

- **Issue**: #830 - [週次レポート] 2026-01-22 マーケットレポート
- **URL**: https://github.com/YH-05/finance/issues/830
- **Project**: #15 (Finance News Collection)
- **Status**: Weekly Report
- **ラベル**: `report`

## 次のアクション

1. レポートを確認:
   cat articles/weekly_report/2026-01-22/02_edit/weekly_report.md

2. 編集・修正:
   edit articles/weekly_report/2026-01-22/02_edit/weekly_report.md

3. Issue を確認:
   gh issue view 830

================================================================================
```

---

## --weekly モードのエラーハンドリング

### E010: GitHub Project アクセスエラー

**発生条件**:
- Project が存在しない
- アクセス権限がない

**対処法**:
```
エラー: GitHub Project #15 にアクセスできません

確認項目:
1. Project の存在確認:
   gh project list --owner @me

2. Project 番号の確認:
   gh project view 15 --owner @me

3. 別の Project を指定:
   /generate-market-report --weekly --project 20
```

### E011: ニュース取得件数不足

**発生条件**:
- GitHub Project にニュースが少ない
- 対象期間にニュースがない

**対処法**:
```
警告: GitHub Project からのニュースが不足しています

取得件数: 3件（推奨: 10件以上）

対処法:
1. 追加検索を有効化:
   /generate-market-report --weekly  # --no-search なしで実行

2. 期間を拡大（手動でデータ追加）

3. 続行（不足したまま）:
   現在の状態でレポート生成を続行しますか？ [y/N]
```

### E012: レポート生成エラー

**発生条件**:
- weekly-report-writer サブエージェントがエラー
- 必須データの欠損

**対処法**:
```
エラー: レポート生成に失敗しました

フェーズ: Phase 5 (レポート生成)
原因: indices.json が見つかりません

対処法:
1. データ収集を再実行:
   uv run python scripts/weekly_comment_data.py --output {output}/data

2. 手動でデータを配置:
   cp {source}/indices.json {output}/data/
```

### E013: 品質検証失敗

**発生条件**:
- 文字数が目標未達
- データ整合性エラー
- グレードがD以下

**対処法**:
```
警告: 品質検証で問題が検出されました

スコア: 65/100（グレード: D）
ステータス: WARN

問題点:
1. 文字数不足（合計: 2,800字、目標: 3,200字）
2. MAG7 コメントが短い（450字、目標: 800字）

推奨対処:
1. コメントを手動で拡充
2. --publish なしで再実行し、レポートを確認
3. 品質検証をスキップして続行:
   （非推奨: 品質が保証されません）
```

---

# 週次コメントモード（--weekly-comment）【旧形式】

`--weekly-comment` オプションを指定すると、指定日から1週間の期間を対象とした
詳細なマーケットコメント（3000字以上）を生成します。

> **注意**: `--weekly-comment` は互換性のために維持されています。
> 新規利用では `--weekly` オプションの使用を推奨します。

## 週次コメント処理フロー

```
/generate-market-report --weekly-comment
    │
    ├── Phase 1: 初期化
    │   ├── 対象期間の計算（--date から7日前 〜 --date）
    │   │   └── 例: --date 2026-01-20 → 2026-01-13 〜 2026-01-20
    │   └── 出力ディレクトリ作成
    │       └── articles/weekly_comment_{YYYYMMDD}/
    │
    ├── Phase 2: データ収集
    │   ├── Pythonスクリプト実行（weekly_comment_data.py）
    │   ├── indices.json: S&P500, RSP, VUG, VTV
    │   ├── mag7.json: MAG7 + SOX
    │   └── sectors.json: 上位・下位3セクター
    │
    ├── Phase 3: ニュース収集（3サブエージェント並列）
    │   ├── weekly-comment-indices-fetcher（指数背景）
    │   ├── weekly-comment-mag7-fetcher（MAG7背景）
    │   └── weekly-comment-sectors-fetcher（セクター背景）
    │
    ├── Phase 4: コメント生成（3000字以上）
    │   ├── テンプレート読み込み
    │   │   └── template/market_report/weekly_comment_template.md
    │   ├── データ埋め込み
    │   ├── ニュースコンテキスト統合
    │   └── Markdownファイル出力
    │
    ├── Phase 5: 出力
    │   └── articles/weekly_comment_{date}/02_edit/weekly_comment.md
    │
    └── Phase 6: Issue 投稿（自動実行）
        ├── weekly-report-publisher サブエージェント呼び出し
        ├── GitHub Issue 作成（`--label "report"` 付与）
        ├── GitHub Project #15 に追加（Status: Weekly Report）
        └── 公開日時フィールドを設定
```

## 週次コメント出力ディレクトリ構造

```
articles/weekly_comment_{YYYYMMDD}/
├── data/
│   ├── indices.json        # 指数騰落率（S&P500, RSP, VUG, VTV）
│   ├── mag7.json           # MAG7 + SOX騰落率
│   ├── sectors.json        # セクター分析（上位・下位3）
│   ├── metadata.json       # 期間情報
│   └── news_context.json   # ニュース検索結果
└── 02_edit/
    └── weekly_comment.md   # 週次コメント（3000字以上）
```

## 週次コメント Phase 1: 初期化（詳細）

### 1.1 対象期間の計算

```python
from datetime import date, timedelta

# --date オプションで指定された日付を終了日とする（省略時は今日）
end_date = date.fromisoformat(args.date) if args.date else date.today()

# 開始日は終了日の7日前
start_date = end_date - timedelta(days=7)

# 例: --date 2026-01-20 の場合
# start_date = 2026-01-13
# end_date = 2026-01-20
```

### 1.2 出力ディレクトリ作成

```bash
# デフォルトパス
OUTPUT_DIR="articles/weekly_comment_${REPORT_DATE}"

# 構造作成
mkdir -p "${OUTPUT_DIR}/data"
mkdir -p "${OUTPUT_DIR}/02_edit"
```

## 週次コメント Phase 2: データ収集（詳細）

### 2.1 Pythonスクリプト実行

```bash
uv run python scripts/weekly_comment_data.py \
    --start ${START_DATE} \
    --end ${END_DATE} \
    --output "${OUTPUT_DIR}/data"
```

### 2.2 出力データ形式

#### indices.json
```json
{
  "as_of": "2026-01-21",
  "period": {"start": "2026-01-14", "end": "2026-01-21"},
  "indices": [
    {"ticker": "^GSPC", "name": "S&P 500", "weekly_return": 0.025},
    {"ticker": "RSP", "name": "S&P 500 Equal Weight", "weekly_return": 0.018},
    {"ticker": "VUG", "name": "Vanguard Growth ETF", "weekly_return": 0.032},
    {"ticker": "VTV", "name": "Vanguard Value ETF", "weekly_return": 0.012}
  ]
}
```

#### mag7.json
```json
{
  "as_of": "2026-01-21",
  "period": {"start": "2026-01-14", "end": "2026-01-21"},
  "mag7": [
    {"ticker": "TSLA", "name": "Tesla", "weekly_return": 0.037},
    ...
  ],
  "sox": {"ticker": "^SOX", "name": "SOX Index", "weekly_return": 0.031}
}
```

#### sectors.json
```json
{
  "as_of": "2026-01-21",
  "period": {"start": "2026-01-14", "end": "2026-01-21"},
  "top_sectors": [...],
  "bottom_sectors": [...],
  "all_sectors": [...]
}
```

## 週次コメント Phase 3: ニュース収集（詳細）

### 3.1 サブエージェント並列実行

3つのサブエージェントを**並列**で実行:

```python
# 並列実行（Task tool を複数同時呼び出し）
Task(
    subagent_type="weekly-comment-indices-fetcher",
    description="指数ニュース収集",
    prompt="...",
    run_in_background=True
)

Task(
    subagent_type="weekly-comment-mag7-fetcher",
    description="MAG7ニュース収集",
    prompt="...",
    run_in_background=True
)

Task(
    subagent_type="weekly-comment-sectors-fetcher",
    description="セクターニュース収集",
    prompt="...",
    run_in_background=True
)
```

### 3.2 各サブエージェントへの入力

```json
{
  "period": {"start": "2026-01-14", "end": "2026-01-21"},
  "data_file": "articles/weekly_comment_20260122/data/indices.json"
}
```

### 3.3 ニュースコンテキスト統合

```json
// news_context.json
{
  "generated_at": "2026-01-22T09:00:00+09:00",
  "indices": {
    "market_sentiment": "bullish",
    "key_drivers": [...],
    "commentary_draft": "..."
  },
  "mag7": {
    "mag7_analysis": [...],
    "sox_analysis": {...},
    "commentary_draft": "..."
  },
  "sectors": {
    "top_sectors_analysis": [...],
    "bottom_sectors_analysis": [...],
    "commentary_draft": {...}
  }
}
```

## 週次コメント Phase 4: コメント生成（詳細）

### 4.1 テンプレート読み込み

```bash
TEMPLATE="template/market_report/weekly_comment_template.md"
```

### 4.2 プレースホルダー置換

| プレースホルダー | 値の例 |
|-----------------|--------|
| `{report_date_formatted}` | `2026/1/22(Wed)` |
| `{end_date_formatted}` | `1/21` |
| `{spx_return}` | `+2.50%` |
| `{rsp_return}` | `+1.80%` |
| `{vug_return}` | `+3.20%` |
| `{vtv_return}` | `+1.20%` |
| `{indices_comment}` | サブエージェント生成テキスト |
| `{mag7_table}` | MAG7テーブル（Markdown形式） |
| `{mag7_comment}` | サブエージェント生成テキスト |
| `{top_sectors_table}` | 上位セクターテーブル |
| `{top_sectors_comment}` | サブエージェント生成テキスト |
| `{bottom_sectors_table}` | 下位セクターテーブル |
| `{bottom_sectors_comment}` | サブエージェント生成テキスト |

### 4.3 出力文字数目標

| セクション | 最低文字数 |
|-----------|-----------|
| 指数コメント | 500字 |
| MAG7コメント | 800字 |
| 上位セクターコメント | 400字 |
| 下位セクターコメント | 400字 |
| 今後の材料 | 200字 |
| **合計** | **3000字以上** |

## 週次コメント出力例

```markdown
# 2026/1/22(Wed) Weekly Comment

## Indices (AS OF 1/21)

| 指数 | 週間リターン |
|------|-------------|
| S&P 500 | +2.50% |
| 等ウェイト (RSP) | +1.80% |
| グロース (VUG) | +3.20% |
| バリュー (VTV) | +1.20% |

外株です。S&P500指数は週間+2.50%上昇しました。市場全体は...
（500字以上のコメント）

## Magnificent 7

| 銘柄 | 週間リターン |
|------|-------------|
| Tesla | +3.70% |
| NVIDIA | +1.90% |
...

MAG7では、TSLAが+3.70%で週間トップパフォーマーとなりました...
（800字以上のコメント）

## セクター別パフォーマンス

### 上位3セクター
（400字以上のコメント）

### 下位3セクター
（400字以上のコメント）

## 今後の材料
（200字以上のコメント）
```

---

## 制約事項

1. **データソース**: Yahoo Finance APIの制限により、リアルタイムデータではなく前日終値ベース
2. **ニュース検索**: RSS MCP は登録済みフィード（33件）のみ検索可能
3. **決算データ**: earnings.json は今後2週間分の主要企業のみ
4. **レポート言語**: 日本語での出力を前提
5. **レポート期間**: 指定日（または今日）から7日前までの1週間

---

## 関連リソース

- **Pythonスクリプト**: `scripts/market_report_data.py`
- **週次コメントスクリプト**: `scripts/weekly_comment_data.py`
- **テンプレート**: `template/market_report/02_edit/first_draft.md`
- **週次コメントテンプレート**: `template/market_report/weekly_comment_template.md`
- **サンプルレポート**: `template/market_report/sample/20251210_weekly_comment.md`
- **データスキーマ**: `data/schemas/`
- **日付ユーティリティ**: `src/market_analysis/utils/date_utils.py`

## 週次コメント用サブエージェント

- **指数ニュース収集**: `.claude/agents/weekly-comment-indices-fetcher.md`
- **MAG7ニュース収集**: `.claude/agents/weekly-comment-mag7-fetcher.md`
- **セクターニュース収集**: `.claude/agents/weekly-comment-sectors-fetcher.md`
- **Issue 投稿**: `.claude/agents/weekly-report-publisher.md`

---

## Phase 6: Issue 投稿（自動実行）

週次レポート生成後、自動的に GitHub Issue として投稿します。

### 6.1 サブエージェント呼び出し

```python
# weekly-report-publisher サブエージェントを呼び出し
Task(
    subagent_type="weekly-report-publisher",
    description="週次レポート Issue 投稿",
    prompt=f"""
週次レポートを GitHub Issue として投稿してください。

## 入力パラメータ

report_dir: {OUTPUT_DIR}
project_number: 15

## 期待される処理（必須）

1. {OUTPUT_DIR}/data/ からデータ読み込み
2. {OUTPUT_DIR}/02_edit/weekly_comment.md からレポート読み込み
3. Issue 本文を生成
4. **GitHub Issue を作成（`--label "report"` を必ず付与）**
5. **GitHub Project #15 に追加（`gh project item-add` 実行）**
6. **Status を "Weekly Report" に設定（GraphQL API 実行）**
7. **公開日時フィールドを設定**

## 重要な確認事項

- [ ] Issue に `report` ラベルが付与されているか確認
- [ ] Issue が Project #15 に追加されているか確認
- [ ] Status が "Weekly Report" に設定されているか確認
- [ ] 結果出力に Project 登録情報（Item ID, Status）を含める
"""
)
```

### 6.2 完了時の出力

```markdown
================================================================================
                    /generate-market-report --weekly-comment 完了
================================================================================

## 生成されたレポート

- **レポートファイル**: {output}/02_edit/weekly_comment.md
- **文字数**: 3,200字

## 投稿された Issue

- **Issue**: #825 - [週次レポート] 2026-01-22 マーケットレポート
- **URL**: https://github.com/YH-05/finance/issues/825
- **Project**: #15 (Finance News Collection)
- **Status**: Weekly Report
- **ラベル**: `report`

## 次のステップ

1. レポートを確認:
   cat {output}/02_edit/weekly_comment.md

2. Issue を確認:
   gh issue view 825

================================================================================
```

## 関連コマンド

- **ニュース収集**: `/collect-finance-news`
- **記事作成**: `/new-finance-article`
- **リサーチ実行**: `/finance-research`

---

---

## 関連リソース

### Pythonスクリプト
- **市場データ収集**: `scripts/market_report_data.py`
- **週次コメントデータ**: `scripts/weekly_comment_data.py`
- **日付ユーティリティ**: `src/market_analysis/utils/date_utils.py`

### テンプレート
- **フル週次レポート（--weekly）**: `template/market_report/weekly_market_report_template.md`
- **週次コメント（--weekly-comment）**: `template/market_report/weekly_comment_template.md`
- **基本レポート**: `template/market_report/02_edit/first_draft.md`
- **サンプルレポート**: `template/market_report/sample/`

### サブエージェント（--weekly モード用）

| エージェント | 説明 | タスク |
|-------------|------|--------|
| `weekly-report-lead` | リーダーエージェント（ワークフロー制御） | - |
| `wr-news-aggregator` | GitHub Project からニュース集約 | task-1 |
| `wr-data-aggregator` | 入力データの統合・正規化 | task-2 |
| `wr-comment-generator` | セクション別コメント生成（5700字以上） | task-3 |
| `wr-template-renderer` | テンプレートへのデータ埋め込み | task-4 |
| `wr-report-validator` | レポート品質検証 | task-5 |
| `wr-report-publisher` | GitHub Issue 作成 & Project 追加 | task-6 |

#### --weekly-comment モード用（互換性維持）
| エージェント | 説明 |
|-------------|------|
| `weekly-comment-indices-fetcher` | 指数ニュース収集 |
| `weekly-comment-mag7-fetcher` | MAG7 ニュース収集 |
| `weekly-comment-sectors-fetcher` | セクターニュース収集 |

### GitHub Project
- **Finance News Collection**: [Project #15](https://github.com/users/YH-05/projects/15)

### データスキーマ
- **スキーマ定義**: `data/schemas/`
