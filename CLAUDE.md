---
title: CLAUDE.md
created_at: 2025-12-30
updated_at: 2026-03-07
---

# finance - 金融市場分析・コンテンツ発信支援ライブラリ

**Python 3.12+** | uv | Ruff | pyright | pytest + Hypothesis

金融市場の分析とnote.comでの金融・投資コンテンツ発信を効率化するPythonライブラリ。

## 基本ルール
- 曖昧な表現はせず、可能な限り正確な情報を書く
	- 非推奨: このAPIは制限を受ける可能性がある。
	- 推奨: Github APIは短時間のリクエストを5000件に
- 情報が不足していたり曖昧な状況であったりした場合は、ユーザーにAskUserQeestionsツールを使って詳細を尋ねる
- 自分だけで作業しない。可能な限りサブエージェントに作業を移譲する。適切なサブエージェントがなければ作成を提案する。
- **Bash で `claude` CLI を起動してエージェントをスポーンしてはならない。** サブエージェントの起動は必ず Task tool（`team_name` パラメータ付き）を使用すること。Bash 経由の起動はネストセッション禁止エラー（`CLAUDECODE` 環境変数検出）を引き起こす。
- **コードの動作・出力内容を回答する際は、必ず実装コード（`.py`）を一次情報とすること。** エージェント定義（`.claude/agents/`）やコマンド定義（`.claude/commands/`）は設計意図であり、実装と乖離している場合がある。定義ファイルのみを根拠に回答してはならない。
	- 非推奨: `output-generator.md` の記述から「SEC エビデンスを含む」と回答する
	- 推奨: `output.py` の `_build_rationale()` を読んで実際の出力内容を確認してから回答する

## Python実装時の必須サブエージェント

**Python コードを書く際は、必ず以下のサブエージェントに作業を委譲すること。**

### 目的別サブエージェント一覧

| 目的 | サブエージェント | 説明 |
|------|------------------|------|
| **機能実装** | `feature-implementer` | TDDループ（Red→Green→Refactor）を自動実行。Issue のチェックボックスを更新しながら実装 |
| **テスト作成** | `test-writer` | t-wada流TDDに基づくテスト作成 |
| **単体テスト** | `test-unit-writer` | 関数・クラス単位の単体テスト作成 |
| **プロパティテスト** | `test-property-writer` | Hypothesisを使用した不変条件テスト作成 |
| **統合テスト** | `test-integration-writer` | コンポーネント間連携のテスト作成 |
| **品質チェック** | `quality-checker` | `make check-all` 相当の品質検証・自動修正 |
| **コード整理** | `code-simplifier` | 複雑性削減、可読性・保守性向上 |
| **デバッグ** | `debugger` | 問題特定→根本原因分析→解決策実装 |
| **セキュリティ** | `security-scanner` | OWASP Top 10に基づくセキュリティ監査 |

### 実装フロー例

```
1. 機能実装時
   → feature-implementer（TDDサイクル実行）
   → quality-checker --quick（各サイクル後の品質確認）

2. テスト追加時
   → test-planner（テスト設計）
   → test-unit-writer / test-property-writer（テスト実装）

3. 品質改善時
   → quality-checker --auto-fix（自動修正）
   → code-simplifier（コード整理）

4. バグ修正時
   → debugger（原因特定・修正）
   → quality-checker --validate-only（修正確認）
```

### quality-checker のモード

| モード | 用途 |
|--------|------|
| `--validate-only` | 検証のみ（CI/CD、最終確認） |
| `--auto-fix` | 自動修正（`make check-all` 成功まで繰り返し） |
| `--quick` | フォーマット・リントのみ（TDDサイクル中の高速チェック） |

## 目的別クイックガイド

### コード実装
- コードを書く → `@.claude/rules/coding-standards.md` 参照
- テストを書く → `/write-tests`
- 品質チェック → `make check-all`
- Issue を実装 → `/issue-implement <番号>`

### Git・PR操作
- コミット・PR作成 → `/commit-and-pr`
- PRマージ → `/merge-pr <番号>`
- PRレビュー → `/review-pr`
- コンフリクト分析 → `/analyze-conflicts`

### プロジェクト管理
- Issue作成 → `/issue`
- Issue改善 → `/issue-refine <番号>`
- プロジェクト計画 → `/plan-project`
- 並行開発計画 → `/plan-worktrees <project_number>`
- worktree作成 → `/worktree <branch_name>`

### 金融コンテンツ作成
- ニュース収集 → `/finance-news-workflow`
- AI投資バリューチェーン収集 → `/ai-research-collect`
- トピック提案 → `/finance-suggest-topics`
- 記事フォルダ作成 → `/new-finance-article`
- リサーチ実行 → `/finance-research`
- 個別銘柄分析 → `/dr-stock`
- 業界・セクター分析 → `/dr-industry`
- 競争優位性評価 → `/ca-eval`
- 全工程一括 → `/finance-full`

### 分析・改善
- コード分析 → `/analyze`
- 品質改善 → `/ensure-quality`
- セキュリティ検証 → `/scan`
- デバッグ → `/troubleshoot`

### 一覧表示
- 全コマンド一覧 → `/index`

---

## Pythonパッケージ一覧

| パッケージ | 説明 | 主な機能 |
|------------|------|----------|
| `database` | コアインフラパッケージ | SQLite/DuckDB接続、構造化ロギング、日付ユーティリティ |
| `market` | 市場データ取得パッケージ | yfinance連携、FRED連携、Bloomberg連携、キャッシュ機能、業界データ収集（market.industry） |
| `edgar` | SEC Filings抽出パッケージ | edgartoolsラッパー、テキスト・セクション抽出、並列処理、キャッシュ |
| `analyze` | 市場データ分析パッケージ | テクニカル分析、統計分析、セクター分析、可視化 |
| `rss` | RSSフィード管理パッケージ | フィード監視、記事抽出、MCP統合、キーワード検索 |
| `factor` | ファクター投資・分析パッケージ | バリュー/モメンタム/クオリティ/サイズ/マクロファクター |
| `strategy` | 投資戦略パッケージ | リスク計算、ポートフォリオ管理、リバランス分析 |
| `news` | ニュース処理パイプライン | ニュース収集、フィルタリング、GitHub投稿 |
| `news_scraper` | 金融ニューススクレイパー | CNBC/NASDAQ/yfinance RSS・APIスクレイピング、curl_cffi、sync/async対応 |
| `utils_core` | 共通ユーティリティ | ロギング設定 |
| `dev/ca_strategy` | AI駆動の競争優位性ベース投資戦略パッケージ（PoC） | トランスクリプト解析、LLM主張抽出・スコアリング、セクター中立化、ポートフォリオ構築 |

---

## 依存関係

### Pythonパッケージ

- `database` (コア) → `market`, `edgar`, `analyze`, `rss`
- `market` → `analyze`, `factor`, `strategy`
- `edgar` → `analyze`
- `analyze` → `strategy`
- `factor` → `strategy`
- `utils_core` → `dev/ca_strategy`
- `factor` → `dev/ca_strategy`（SectorNeutralizer）
- `news_scraper` (standalone、curl_cffi ベース)

### コマンド → スキル → エージェント

- `/commit-and-pr` → `commit-and-pr` → `quality-checker`, `code-simplifier`
- `/dr-stock` → `dr-stock` → `dr-stock-lead`（Agent Teams）→ 8チームメイト
- `/dr-industry` → `dr-industry` → `dr-industry-lead`（Agent Teams）→ 9チームメイト
- `/finance-research` → `deep-research` → `research-lead`（Agent Teams）→ 12リサーチエージェント
- `/generate-market-report` → `generate-market-report` → `weekly-report-lead`（Agent Teams）→ 6チームメイト
- `/ai-research-collect` → `ai-research-workflow` → `ai-research-article-fetcher`（10カテゴリ並列）
- `/issue-implement <番号>` → `issue-implement-single` → `api-usage-researcher`(条件付き), `test-writer`, `pydantic-model-designer`, `feature-implementer`, `code-simplifier`, `quality-checker`
- `/plan-project` → `plan-project` → `project-researcher`, `project-planner`, `project-decomposer`
- `/write-tests` → `tdd-development` → `test-orchestrator` → `test-lead`（Agent Teams）→ 4テストエージェント
- `/ca-eval` → `ca-eval` → `ca-eval-lead`（Agent Teams）→ 7チームメイト
- `/index` → `index` → `Explore`, `package-readme-updater`
- `ca-strategy-lead`（Agent Teams）→ 7チームメイト

詳細なMermaid図は [README.md](README.md#-依存関係図) を参照。

---

## 規約・詳細参照

| 規約 | パス |
|------|------|
| コーディング規約 | `@.claude/rules/coding-standards.md` |
| テスト戦略 | `@.claude/rules/testing-strategy.md` |
| Git運用 | `@.claude/rules/git-rules.md` |
| 開発プロセス | `@.claude/rules/development-process.md` |
| 共通指示 | `@.claude/rules/common-instructions.md` |
| エビデンスベース | `@.claude/rules/evidence-based.md` |
| サブエージェント | `@.claude/rules/subagent-data-passing.md` |

---

## ディレクトリ構成

```
finance/
├── .claude/          # Claude Code 設定（agents/101個, commands/20個, rules/, skills/52個）
├── src/              # ソースコード（database, market, edgar, analyze, rss, factor, strategy, news, news_scraper, utils_core, dev/ca_strategy）
├── tests/            # テストスイート（{package}/unit/, property/, integration/）
├── data/             # データ層（raw/, processed/, exports/）
├── template/         # 参照テンプレート（読み取り専用）
├── articles/         # 金融記事ワークスペース
├── research/         # ディープリサーチワークスペース
├── docs/             # ドキュメント
├── snippets/         # 再利用可能コンテンツ
└── trash/            # 削除待ちファイル
```

---

## 制約事項

- スキル実装コード（Python）は `.claude/skills/` 内のみ許可
- `template/` は変更・削除禁止
- `trash/` はユーザーが定期的に確認・削除
