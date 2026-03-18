# 議論メモ: EDINET DB 実装状況レビュー & APIアライメント修正

**日付**: 2026-03-18
**議論ID**: disc-2026-03-18-edinet-api-alignment
**参加**: ユーザー + AI

## 背景・コンテキスト

日本株の EDINET DB 関連モジュールの実装状況をレビューし、API接続確認・dataclassアライメント修正を実施した。

## セッション1: 実装状況レビュー

### 2つのモジュール

| モジュール | API | 用途 | 状態 |
|-----------|-----|------|------|
| `market.edinet` | EDINET DB API (`edinetdb.jp`) | 企業財務データ検索・永続化 | 実装完了 |
| `market.edinet_api` | EDINET 開示 API (`api.edinet-fsa.go.jp`) | 有価証券報告書の検索・DL | 実装完了 |

### market.edinet（EDINET DB API クライアント）

- **コード量**: 4,826行（10ファイル）
- **テスト**: 372テスト、全パス（アライメント修正後）
- **主要コンポーネント**:
  - `EdinetClient` - 10エンドポイント対応
  - `EdinetStorage` - DuckDB 8テーブル管理
  - `EdinetSyncer` - 6フェーズ同期オーケストレーター（チェックポイント再開対応）
  - `DailyRateLimiter` - 日次API制限管理
  - CLI (`sync.py`) - `--initial`/`--daily`/`--resume`/`--status`/`--company`

### DuckDB の状態

- ファイル: `data/duckdb/edinet.duckdb`
- 8テーブル作成済み、**E03006（あいホールディングス）のデータ格納済み**

## セッション2: API接続確認 & アライメント修正

### 実施内容

1. **API接続確認**（2コール）: ステータスOK、3,838社、14エンドポイント
2. **環境変数typo修正**: `.env` の `EDITNET_DB_API` → `EDINET_DB_API_KEY`
3. **Company dataclass修正**: `corp_name`→`name`, `industry_name`→`industry`, `industry_code`/`listing_status` 削除、`name_en`/`name_ja`/`accounting_standard`/`credit_rating`/`credit_score` 追加
4. **edinet_code注入**: financials/ratios/analysis/text-blocks の各メソッドで注入（APIレスポンスに含まれないため）
5. **AnalysisResult再設計**: ネスト構造 `{ai_summary, history}` → フラット構造（最新 history エントリ + ai_summary.text）
6. **TextBlock再設計**: 固定フィールド `{business_overview, risk_factors, management_analysis}` → ペア構造 `{section, text}`
7. **RatioRecord拡張**: `financial_leverage`, `invested_capital` 追加
8. **単一企業同期成功**: E03006 全フェーズ完了（companies=1, financials=14, ratios=14, analyses=1, text_blocks=4）
9. **コミット&プッシュ**: `fix(edinet)` 62c52a0、11ファイル変更

### API側の変更点（実装時に判明）

| 項目 | 旧（コード想定） | 新（実API） |
|------|----------------|------------|
| 企業名フィールド | `corp_name` | `name` |
| 業種フィールド | `industry_name` | `industry` |
| 業種コード | `industry_code`（存在） | 存在しない |
| 上場区分 | `listing_status`（存在） | 存在しない |
| 分析レスポンス | フラット `{health_score, commentary}` | ネスト `{ai_summary, history[]}` |
| テキストレスポンス | `{business_overview, risk_factors, ...}` | `[{section, text}, ...]` |
| エンドポイント数 | 10 | 14（+earnings, calendar, screener, status） |
| ランキング指標 | 20 | 21（+roic） |

## 決定事項

| ID | 内容 | コンテキスト |
|----|------|------------|
| dec-2026-03-18-001 | EDINET DB API Proプラン接続成功 | 3,838社、14エンドポイント、1,000件/日 |
| dec-2026-03-18-002 | APIアライメント修正完了 | Company/AnalysisResult/TextBlock/RatioRecord + DDL + edinet_code注入 |
| dec-2026-03-18-003 | 単一企業同期動作確認完了 | E03006、5 APIコール、全テーブル格納成功 |

## アクションアイテム

| ID | 内容 | 優先度 | 状態 |
|----|------|--------|------|
| act-2026-03-18-001 | DuckDB 全社初回同期実行（`--initial`、約19,000 APIコール、約20日間） | 高 | pending |
| act-2026-03-18-002 | Project 70 残タスク再評価（今回の修正で大部分完了の可能性） | 中 | pending |
| act-2026-03-18-003 | API新エンドポイント対応検討（earnings, calendar, screener, roic） | 低 | pending |

## 関連ファイル

| リソース | パス |
|---------|------|
| EDINET DB モジュール | `src/market/edinet/` |
| EDINET 開示 API モジュール | `src/market/edinet_api/` |
| EDINET DB テスト | `tests/market/unit/edinet/` |
| EDINET API テスト | `tests/market/edinet_api/unit/` |
| DuckDB ファイル | `data/duckdb/edinet.duckdb` |
| API検証結果 | `docs/project/project-70/step0-api-verification.json` |
| APIアライメント計画 | `docs/plan/2026-03-06_edinet-api-alignment.md` |
