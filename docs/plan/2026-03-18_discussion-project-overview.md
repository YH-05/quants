# 議論メモ: quants プロジェクト全体像の包括的記録

**日付**: 2026-03-18
**議論ID**: disc-2026-03-18-project-overview
**参加**: ユーザー + AI

## 背景・コンテキスト

quants プロジェクトで実装している3つの主要軸（クオンツ系ライブラリ、アナリスト暗黙知プロジェクト、MASファンド運用システム）の全体像を包括的に記録する。

## 1. クオンツ系ライブラリ（quants 本体）

### 全体統計

| 指標 | 値 |
|------|-----|
| ソースファイル | 439 |
| ソースコード行数 | 150,644 |
| テスト数 | 11,103 |
| エージェント | 120 |
| スキル | 63 |
| コマンド | 31 |

### パッケージ別規模

| パッケージ | ファイル数 | 行数 | テスト数 | 主な機能 |
|-----------|----------|------|---------|---------|
| `database` | 13 | 2,771 | 124 | SQLite/DuckDB接続、構造化ロギング、日付ユーティリティ |
| `market` | 108 | 45,621 | 2,690 | yfinance/FRED/Bloomberg/EDINET/J-Quants/BSE連携、キャッシュ |
| `edgar` | 13 | 2,969 | 235 | SEC EDGAR edgartoolsラッパー、テキスト抽出、並列処理 |
| `analyze` | 47 | 17,369 | 844 | テクニカル分析、統計分析、セクター分析、可視化 |
| `rss` | 48 | 12,262 | 2,017 | フィード監視、記事抽出、MCP統合、キーワード検索 |
| `factor` | 45 | 13,638 | 928 | バリュー/モメンタム/クオリティ/サイズ/マクロファクター |
| `strategy` | 23 | 4,750 | 427 | リスク計算、ポートフォリオ管理、リバランス分析 |
| `news` | 51 | 18,687 | 1,511 | ニュース収集、フィルタリング、GitHub投稿パイプライン |
| `news_scraper` | 18 | 7,305 | 391 | CNBC/NASDAQ/yfinance RSS・APIスクレイピング |
| `utils_core` | 7 | 1,400 | 172 | ロギング設定（共通ユーティリティ） |
| `dev/ca_strategy` | 24 | 11,535 | - | AI駆動の競争優位性ベース投資戦略（PoC） |
| `automation` | 4 | 401 | - | ニュース収集自動化、開発タスク自動化 |
| `embedding` | 9 | 1,304 | 100 | ChromaDB連携、テキスト抽出、ベクトル検索 |
| `notebooklm` | 28 | 10,631 | 569 | NotebookLM連携、ブラウザ自動操作、MCP統合 |

### 依存関係

```
database (コア) → market, edgar, analyze, rss
market → analyze, factor, strategy
edgar → analyze
analyze → strategy
factor → strategy, dev/ca_strategy
utils_core → dev/ca_strategy
```

## 2. アナリスト暗黙知プロジェクト

| 項目 | 状態 |
|------|------|
| Stage 1（判断軸の抽出・文書化） | 完了 |
| Stage 2（ca-eval ワークフロー） | 部分完了 |
| Stage 3-5（改善・統合・マルチエージェント化） | 未着手 |

### 主要成果物

- **dogma v1.0**: アナリスト検証済みの投資判断基準
- **KB1**: 8つの評価ルール
- **KB2**: 12の却下/高評価パターン
- **KB3**: 5つの Few-shot 事例
- **ca-eval ワークフロー**: 12銘柄バッチ実行済み（AME, ATCOA, CPRT, LLY, LRCX, MCO, MNST, MSFT, NFLX, ORLY, POOL, VRSK）
- **ca_strategy パッケージ**: 24ファイル11,535行、395銘柄対応バッチ並列処理

### 最優先アクション

- **Out-of-sample 検証**: リスト外+ボーダーライン混合銘柄で AI レポート生成 → Y 評価
- 鏡問題（KB準拠による反論限界）の診断
- FM批判目線 vs AN推奨目線の分離

## 3. MAS ファンド運用システム

| 項目 | 状態 |
|------|------|
| 詳細設計 | 完了 |
| 実装 | 未着手 |
| 前提条件 | バックテストエンジン（src/backtest/）の完成 |

### アーキテクチャ

- **ハイブリッド**: Python バックテストエンジン + Claude Code Agent Teams
- **12エージェント構成**: Postmortem → UniverseScreener → 4アナリスト並列 → Bull/Bear Debate → FundManager → RiskManager + PortfolioConstructor
- **意思決定**: マネージャー決定型 + 構造化ディベート（全会一致型ではない）
- **先読みバイアス排除**: 3層防御（PitGuard構造的 + 時間的制約 + ティッカー匿名化）

### ロードマップ

| Phase | 内容 | コスト見積 |
|-------|------|-----------|
| Phase 1 MVP | 4四半期（2024Q1-Q4）、基本エージェント、ディベートなし | ~$10-30/回 |
| Phase 2 | フル12エージェント + ディベート + Postmortem + 3年バックテスト | ~$200-500/回 |
| Phase 3 | MSCI Kokusai対応、Black-Litterman、Walk-forward最適化 | TBD |

## 決定事項

| ID | 内容 | コンテキスト |
|----|------|------------|
| dec-2026-03-18-005 | quants ライブラリは14パッケージ・150K行・11Kテストで安定稼働 | production レベル |
| dec-2026-03-18-006 | 3プロジェクト依存: バックテスト→MAS前提、暗黙知は独立進行可 | ロードマップ: ①暗黙知OOS→②バックテスト→③MAS |
| dec-2026-03-18-007 | 暗黙知 Stage2部分完了、Out-of-sample検証が最優先 | 鏡問題発見、FM/AN目線分離が課題 |
| dec-2026-03-18-008 | MAS 詳細設計完了、バックテストエンジン待ち | ハイブリッドアーキ、12エージェント、Phase1 ~$10-30/回 |

## プロジェクト間の依存関係図

```
quants-library (基盤)
  ├── ENABLES → quants-analyst-tacit-knowledge (独立進行可)
  ├── ENABLES → quants-backtest-engine (設計完了・実装未着手)
  │                └── REQUIRED_BY → quants-mas-investment-team (設計完了・実装未着手)
  └── ENABLES → quants-edinet-db (実装完了・データ投入待ち)
      └── ENABLES → quants-neo4j-kg (Wave 1部分実装)
```

## Neo4j 保存先

| ノードタイプ | ID / Name |
|-------------|-----------|
| Project | `Project:quants-library` |
| Discussion | `disc-2026-03-18-project-overview` |
| Decision x4 | `dec-2026-03-18-005` 〜 `dec-2026-03-18-008` |
| リレーション | HAS_DISCUSSION, RESULTED_IN, ENABLES, REQUIRED_BY |
