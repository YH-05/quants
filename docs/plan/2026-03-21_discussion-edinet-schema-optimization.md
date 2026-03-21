# 議論メモ: EDINET DB スキーマ最適化 — 全工程

**日付**: 2026-03-21
**議論ID**: disc-2026-03-21-edinet-schema-optimization
**参加**: ユーザー + AI

## 背景・コンテキスト

EDINET DB の構造レビューから始まり、スキーマ最適化 → DB移行 → cron自動化準備まで一気通貫で実施。

## 実施内容サマリー

### Phase 1: スキーマレビュー・最適化
1. 8テーブル構造をレビュー、パネルデータ慣例に従わないテーブルを特定
2. rankings テーブル: 全20メトリクスが financials + ratios + companies から再現可能 → **削除**
3. analyses テーブル: 固有情報はAI生成テキスト2列のみ、Claude Codeで代替可能 → **削除**
4. text_blocks: fiscal_year なし → **PK に fiscal_year 追加** `(edinet_code, fiscal_year, section)`

### Phase 2: コード変更
- constants.py: TABLE_RANKINGS, TABLE_ANALYSES, RANKING_METRICS 削除
- types.py: AnalysisResult, RankingEntry 削除、TextBlock に fiscal_year 追加
- storage.py: 対応するDDL, upsert, query 削除、text_blocks PK変更
- client.py: get_analysis, get_ranking 削除、get_text_blocks に year 必須化
- syncer.py: Phase 3(rankings) 削除、Phase 6 → text_blocks のみ、--daily に text_blocks 追加
- __init__.py: 削除済みシンボルの re-export 除去
- テスト: 6ファイル更新、302テスト全パス

### Phase 3: DuckDB → SQLite 移行
- NAS (SMB) 上で DuckDB はファイルロック非対応 → SQLite に移行
- storage.py 全面書き換え（SQLiteClient, INSERT OR REPLACE, pd.read_sql_query）
- 既存DuckDBデータをSQLiteに移行（6テーブル全量）
- NAS上で直接読み書き可能を確認

### Phase 4: 日次同期実行
- 日次同期: companies +1, financials/ratios +650行（47社分）
- --resume: +2社（レートリミットで停止）
- 現在: 51/3,839社の financials/ratios 取得済み

### Phase 5: Mac Mini cron 準備（途中）
- Mac Mini (yukimac-mini) はオンライン、Tailscale接続可能
- SSH公開鍵認証: 動作せず（xattr/provenance問題）→ Mac Mini 直接操作に切替
- quants リポジトリ: Mac Mini に EXISTS
- uv/Python 3.12: インストール済み
- **未完了**: NASマウント、EDINET_DB_API_KEY設定、git pull、cron登録

## 決定事項

| ID | 内容 | ステータス |
|----|------|-----------|
| dec-001 | rankings テーブルを削除 | **実装済み** |
| dec-002 | analyses テーブルを削除 | **実装済み** |
| dec-003 | レートリミット定数はFree plan値(100)を維持 | active |
| dec-004 | text_blocks に fiscal_year を追加しPK変更 | **実装済み** |
| dec-005 | DuckDB → SQLite に移行 | **実装済み** |
| dec-006 | 定期データ取得は Mac Mini で行う | active |
| dec-007 | --daily に text_blocks フェーズを追加 | **実装済み** |

## テーブル構造（最終形）

| テーブル | 行数 | PK | DB |
|---------|------|-----|-----|
| companies | 3,839 | `edinet_code` | SQLite |
| financials | 706 | `(edinet_code, fiscal_year)` | SQLite |
| ratios | 692 | `(edinet_code, fiscal_year)` | SQLite |
| text_blocks | 4 | `(edinet_code, fiscal_year, section)` | SQLite |
| industries | 33 | `slug` | SQLite |
| industry_details | 32 | `slug` | SQLite |

## API コール構造（最終形）

### --initial（5フェーズ）
| フェーズ | コール数 |
|---------|---------|
| companies | 1 |
| industries | 34 |
| company_details | 3,839 |
| financials_ratios | 7,678 |
| text_blocks | 3,839 |
| **合計** | **15,391** (約162日) |

### --daily（3フェーズ）
| フェーズ | コール数 |
|---------|---------|
| companies | 1 |
| financials_ratios | 2/社 |
| text_blocks | 1/社 |
| **1日** | **約31社** (95コール/日) |

## 関連ファイル

| リソース | パス |
|---------|------|
| EDINET DB モジュール | `src/market/edinet/` |
| テスト | `tests/market/unit/edinet/` |
| SQLite DB | `data/sqlite/edinet.db` (NAS symlink) |
| メモリ（レートリミット方針） | `.claude/projects/.../memory/project_edinet_rate_limit.md` |
| 前回の議論メモ | `docs/plan/2026-03-18_discussion-edinet-db-status.md` |
