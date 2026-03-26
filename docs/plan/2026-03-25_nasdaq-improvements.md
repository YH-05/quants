# 議論メモ: NASDAQ データ収集パッケージ改善

**日付**: 2026-03-25
**議論ID**: disc-2026-03-25-nasdaq-improvements
**参加**: ユーザー + AI

## 背景・コンテキスト

market.nasdaq パッケージ（12モジュール、617テスト）の実装状況を確認し、出力パスのハードコード問題とキャッシュ/パーサーのバグを修正した。

## 議論のサマリー

### 1. 実装状況の確認
- Screener, Calendar, Quote, Company, Analyst, Market Movers, ETF Screener の全主要エンドポイント実装済み
- NasdaqClient（同期）+ AsyncNasdaqClient（非同期）+ SQLiteCache + NasdaqSession（curl_cffi ボットブロッキング対策）

### 2. 出力パスの .env 対応
- `DEFAULT_OUTPUT_DIR = "data/raw/nasdaq"` がハードコードされていた
- `DEFAULT_CACHE_DB_PATH` も `Path(__file__)` ベースでハードコードされていた
- `.env` の `DATA_DIR=/Volumes/personal_folder/Quants/data` が無視されていた

### 3. Earnings Calendar ヒストリカルデータ調査
- API は 1日単位で日付指定（日付範囲の一括取得は非対応）
- 取得可能範囲: 2008年〜現在（約18年分）
- 1日あたり 69〜192件（決算シーズンにより変動）
- 2007年以前はデータなし（API が `data` キーを返さない）

### 4. バグ修正

#### バグ1: キャッシュシリアライズエラー（client.py:293）
- **原因**: `_fetch_and_parse()` がパース済み dataclass をキャッシュ保存 → JSON変換失敗
- **原因2**: `use_cache=False` でもキャッシュ書き込みをスキップしない
- **修正**: キャッシュには raw dict（パース前）を保存、ヒット時にパーサー再適用。`use_cache=False` 時は読み書き両方スキップ

#### バグ2: パーサーフィールドマッピング不一致（client_parsers.py:294-306）
- **原因**: パーサーが `epsEstimate`/`epsActual`/`date` を期待 → 実API は `epsForecast`/`eps`/`time`
- **修正**: 正しいキーにマッピング + EarningsRecord に 4フィールド追加（`time`, `no_of_ests`, `last_year_rpt_dt`, `last_year_eps`）

## 決定事項

| ID | 内容 | コンテキスト |
|----|------|------------|
| dec-2026-03-25-001 | NASDAQ出力パスは DATA_DIR 環境変数に従う（ハードコード禁止） | `.env` の `DATA_DIR=/Volumes/personal_folder/Quants/data` が設定済みだが、NASDAQ モジュールが参照していなかった |
| dec-2026-03-25-002 | NasdaqClient のキャッシュはパース前の raw dict を保存する設計 | dataclass の JSON シリアライズ問題を根本解決。キャッシュヒット時にパーサーを再適用して型安全を維持 |
| dec-2026-03-25-003 | Earnings Calendar の取得可能範囲は 2008年〜現在（API制約） | 2007年以前は API が data キーを返さない。18年×252営業日≒4,500回のAPIコールが必要 |

## アクションアイテム

| ID | 内容 | 優先度 | 期限 |
|----|------|--------|------|
| act-2026-03-25-001 | Earnings Calendar ヒストリカル一括取得スクリプトの実装 | 中 | - |
| act-2026-03-25-002 | Neo4j 再起動後にこのセッションの Decision/ActionItem を投入 | 低 | - |

## テスト結果

- DATA_DIR 対応後: 644テスト全パス（65既存 + 4新規 NASDAQ、22既存 + 1新規 cache）
- バグ修正後: 622テスト全パス（13テストファイル更新）
- Ruff format/lint: クリーン
- Pyright: 0 errors, 0 warnings

## 変更ファイル一覧

### DATA_DIR .env 対応
- `src/market/nasdaq/constants.py` - DEFAULT_OUTPUT_DIR → DEFAULT_OUTPUT_SUBDIR
- `src/market/nasdaq/collector.py` - get_data_dir() ベースに変更
- `src/market/cache/cache.py` - DEFAULT_CACHE_DB_PATH を get_data_dir() ベースに
- `tests/market/nasdaq/unit/test_constants.py` - 定数名更新
- `tests/market/nasdaq/unit/test_collector.py` - _resolve_output_dir テスト追加
- `tests/market/unit/cache/test_cache.py` - _resolve_cache_db_path テスト追加

### バグ修正
- `src/market/nasdaq/client.py` - _fetch_and_parse キャッシュ戦略変更
- `src/market/nasdaq/client_types.py` - EarningsRecord 4フィールド追加
- `src/market/nasdaq/client_parsers.py` - parse_earnings_calendar マッピング修正
- `tests/market/nasdaq/unit/test_client_base.py` - キャッシュヒットテスト更新
- `tests/market/nasdaq/unit/test_client_calendar.py` - カレンダーテスト更新
- `tests/market/nasdaq/unit/test_client_parsers_calendar.py` - パーサーテスト更新
- 他10テストファイル - キャッシュ戦略変更に伴う更新
