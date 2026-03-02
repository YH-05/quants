---
name: generate-market-report
description: "週次マーケットレポートを自動生成するスキル。データ収集→ニュース検索→レポート作成の一連のワークフローを提供。/generate-market-report コマンドで使用。"
allowed-tools: Read, Write, Glob, Grep, Bash, Task, WebSearch
---

# Generate Market Report

週次マーケットレポートを自動生成するスキルです。

## 目的

このスキルは以下を提供します：

- **3種類のレポートモード**: 基本レポート、週次コメント（旧形式）、フル週次レポート（推奨）
- **自動データ収集**: yfinance/FRED 経由の市場データ収集
- **ニュース統合**: GitHub Project / RSS / Tavily からのニュース収集と統合
- **品質検証**: 文字数・フォーマット・データ整合性の自動検証

## いつ使用するか

### プロアクティブ使用

- 毎週水曜日の週次レポート作成時
- 市場データの定期収集と分析が必要な場合

### 明示的な使用

- `/generate-market-report` コマンド
- 「週次レポートを作成して」「マーケットレポートを生成して」などの要求

## モード比較

| モード | 説明 | GitHub Project 連携 | Issue 投稿 | 目標文字数 |
|--------|------|-------------------|-----------|-----------|
| 基本モード | 指定日のレポート生成 | なし | なし | - |
| `--weekly-comment` | 火曜〜火曜の週次コメント（旧形式） | **あり** | **自動** | 3000字以上 |
| `--weekly` | **フル週次レポート（推奨）** | **あり** | **自動** | 5700字以上 |

## 処理フロー

### 基本モード

```
Phase 1: 初期化
├── 引数解析・出力ディレクトリ作成
├── 必要ツール確認（RSS MCP, Tavily, gh）
└── テンプレート確認

Phase 2: データ収集
└── Pythonスクリプト実行（market_report_data.py）

Phase 3: ニュース検索
└── カテゴリ別ニュース検索（指数/MAG7/セクター/決算）

Phase 4: レポート生成
└── テンプレート埋め込み → Markdown出力

Phase 5: 完了処理
└── 結果サマリー表示
```

### --weekly モード（推奨）

```
Phase 1: 初期化
├── 対象期間の計算（--date から7日前 〜 --date）
├── 出力ディレクトリ作成
└── 必要ツール確認

Phase 2: 市場データ収集
├── collect_weekly_report_data.py → data/
│   ├── indices.json          # 指数パフォーマンス（S&P500, RSP, VUG, VTV等）
│   ├── mag7.json             # MAG7 + SOX パフォーマンス
│   ├── sectors.json          # セクター分析（上位・下位3セクター）
│   ├── interest_rates.json   # 金利データ
│   ├── currencies.json       # 通貨データ
│   ├── upcoming_events.json  # 今後の主要イベント
│   └── metadata.json         # 収集メタデータ
└── データ鮮度チェック（日付ズレ警告）

Phase 3: 仮説生成（将来計画: 現在は Phase 2 の出力データを直接使用）
├── market-hypothesis-generator サブエージェント
├── パターン検出 → 仮説生成 → 検索クエリ計画
└── hypotheses_{YYYYMMDD-HHMM}.json 出力

Phase 4: ニュース調査（将来計画: 仮説ベース検索は未実装）
├── GitHub Project から既存ニュース取得
├── 仮説ベースの追加検索（--no-search でスキップ可能）
└── news_with_context.json（仮説との関連付き）

Phase 5: レポート生成（サブエージェント）
├── weekly-data-aggregation スキル
├── weekly-comment-generation スキル（仮説+検索結果を統合）
├── weekly-template-rendering スキル
└── weekly-report-validation スキル

Phase 6: 品質検証
└── 文字数・フォーマット・データ整合性チェック

Phase 7: Issue 投稿（自動実行）
└── weekly-report-publisher → GitHub Issue 作成（report ラベル）& Project #15 追加

Phase 8: 完了処理
└── 結果サマリー表示
```

## 入力パラメータ

| パラメータ | デフォルト | 説明 |
|-----------|-----------|------|
| `--date` | 今日 | **レポート終了日（YYYY-MM-DD）。この日付から1週間前が開始日となる** |
| `--output` | articles/market_report_{date} | 出力ディレクトリ |
| `--weekly` | false | フル週次レポート生成（推奨） |
| `--weekly-comment` | false | 週次コメント生成（旧形式） |
| `--project` | 15 | GitHub Project 番号（--weekly時） |
| `--no-search` | false | 追加検索を無効化（--weekly時） |

**注意**: `--weekly` および `--weekly-comment` モードでは、レポート生成後に自動的に GitHub Issue が作成され、`report` ラベルが付与されて Project #15 に「Weekly Report」ステータスで登録されます。

### 日付と期間の計算

`--date` で指定した日付（YYYY-MM-DD形式）が**終了日**となり、**開始日は終了日の7日前**に自動計算されます。

```
例: --date 2026-01-20
  開始日: 2026-01-13
  終了日: 2026-01-20
  期間: 2026-01-13 〜 2026-01-20（7日間）
```

## 出力ディレクトリ構造

### --weekly モード

```
articles/weekly_report/{YYYY-MM-DD}/
├── data/
│   ├── indices.json          # 指数パフォーマンス
│   ├── mag7.json             # MAG7 パフォーマンス
│   ├── sectors.json          # セクター分析
│   ├── news_from_project.json # GitHub Project からのニュース
│   ├── news_supplemental.json # 追加検索結果
│   ├── aggregated_data.json  # 集約データ
│   └── comments.json         # 生成コメント
├── 02_edit/
│   └── weekly_report.md      # Markdown レポート
└── validation_result.json    # 品質検証結果
```

## 使用例

### 例1: フル週次レポート生成 & Issue投稿

**状況**: 毎週水曜日に週次レポートを作成したい

**コマンド**:
```bash
/generate-market-report
```

**処理**:
1. 対象期間を自動計算（前週火曜〜当週火曜）
2. 市場データを収集
3. GitHub Project #15 からニュースを取得
4. 不足カテゴリを追加検索で補完
5. 3200字以上のレポートを生成
6. 品質検証を実行
7. **GitHub Issue を作成（`report` ラベル付与）し Project #15 に追加**

---

### 例2: GitHub Project のみ使用

**状況**: 追加検索なしでレポートを作成したい

**コマンド**:
```bash
/generate-market-report --weekly --no-search
```

**処理**:
1. GitHub Project からのニュースのみ使用
2. 追加検索をスキップ
3. レポートを生成
4. GitHub Issue を作成し Project #15 に追加

---

### 例3: 特定日付でレポート生成

**状況**: 特定の日付を終了日として1週間分のレポートを作成したい

**コマンド**:
```bash
/generate-market-report --date 2026-01-20
```

**処理**:
1. 2026-01-20 を終了日として設定
2. 開始日を 2026-01-13（7日前）に自動計算
3. 2026-01-13 〜 2026-01-20 の期間でレポートを生成

## 関連リソース

### サブエージェント（--weekly モード用）

| エージェント | 説明 | 使用モード |
|-------------|------|-----------|
| `weekly-report-lead` | リーダーエージェント（ワークフロー制御） | --weekly |
| `wr-news-aggregator` | GitHub Project からニュース集約 | --weekly |
| `wr-data-aggregator` | 入力データの統合・正規化 | --weekly |
| `wr-comment-generator` | セクション別コメント生成 | --weekly |
| `wr-template-renderer` | テンプレートへのデータ埋め込み | --weekly |
| `wr-report-validator` | レポート品質検証 | --weekly |
| `wr-report-publisher` | GitHub Issue 作成 & Project 追加 | --weekly |
| `weekly-comment-indices-fetcher` | 指数ニュース収集 | --weekly-comment |
| `weekly-comment-mag7-fetcher` | MAG7 ニュース収集 | --weekly-comment |
| `weekly-comment-sectors-fetcher` | セクターニュース収集 | --weekly-comment |

### テンプレート

| テンプレート | 用途 |
|-------------|------|
| `template/market_report/weekly_market_report_template.md` | --weekly モード用 |
| `template/market_report/weekly_comment_template.md` | --weekly-comment モード用 |
| `template/market_report/02_edit/first_draft.md` | 基本モード用 |

### Python スクリプト

| スクリプト | 用途 |
|-----------|------|
| `scripts/market_report_data.py` | 基本モード用データ収集 |
| `scripts/collect_weekly_report_data.py` | `--weekly` モード用データ収集（固定名7ファイル出力） |
| `scripts/weekly_comment_data.py` | `--weekly-comment` モード専用データ収集 |

## エラーハンドリング

### E001: Python スクリプト実行エラー

**原因**: スクリプトが存在しない、依存関係不足、ネットワークエラー

**対処法**:
```bash
# 依存関係を確認
uv sync --all-extras

# スクリプトを直接実行してエラー確認
uv run python scripts/weekly_comment_data.py --output .tmp/test
```

### E010: GitHub Project アクセスエラー

**原因**: Project が存在しない、アクセス権限がない

**対処法**:
```bash
# Project の存在確認
gh project list --owner @me

# 別の Project を指定
/generate-market-report --weekly --project 20
```

### E013: 品質検証失敗

**原因**: 文字数不足、データ整合性エラー

**対処法**:
- コメントを手動で拡充
- 生成されたレポートファイル（02_edit/weekly_report.md）を手動で編集

## 品質基準

### 必須（MUST）

- [ ] 対象期間が正しく計算されている
- [ ] 必須データファイル（indices/mag7/sectors.json）が生成されている
- [ ] --weekly モードで 3200 字以上のレポートが生成される
- [ ] 品質検証結果がファイルに出力される

### 推奨（SHOULD）

- ニュースカテゴリが最低件数を満たしている
- グレード B 以上の品質スコア
- 全セクションにコメントが含まれている

## 完了条件

- [ ] 出力ディレクトリにレポートファイルが生成されている
- [ ] 品質検証が PASS または WARN で完了している
- [ ] **GitHub Issue が作成されている（`report` ラベル付き）**
- [ ] **Issue が Project #15 に追加されている（Status: Weekly Report）**
- [ ] 結果サマリーが表示されている

## 関連コマンド

- `/finance-news-workflow`: ニュース収集
- `/new-finance-article`: 記事フォルダ作成
- `/finance-research`: リサーチ実行
