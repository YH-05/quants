# Alpha Vantage Storage Layer 実装計画

## Context

Alpha Vantage APIクライアント（`src/market/alphavantage/`）は API 取得 → パース → TTL キャッシュまで実装済みだが、長期的なデータ蓄積のための永続化層（Storage）が未実装。SQLite ベースの Storage + Collector を追加し、外付けSSD/NAS上での保存・操作に対応する。

設計書: `docs/superpowers/specs/2026-03-24-alphavantage-storage-design.md`

## Wave 依存関係

```
Wave 1 (constants) ──┐
                      ├──→ Wave 3 (storage) ──→ Wave 4 (collector) ──→ Wave 5 (統合)
Wave 2 (models)    ──┘
```

Wave 1・2 は並列実行可能。

---

## Wave 1: storage_constants.py + テスト (~140行)

### 実装ファイル
- `src/market/alphavantage/storage_constants.py`

### パターン参照
- `src/market/polymarket/storage_constants.py` をそのまま踏襲

### 内容
- `AV_DB_PATH_ENV`, `DEFAULT_DB_SUBDIR`, `DEFAULT_DB_NAME`
- 8テーブル名定数（`TABLE_DAILY_PRICES` 等、全て `av_` プレフィックス）
- 各定数に docstring、`__all__` リスト

### テスト
- `tests/market/alphavantage/unit/test_storage_constants.py`
- `av_` プレフィックス検証、定数数=8、`__all__` 網羅性

### 検証
```bash
uv run pytest tests/market/alphavantage/unit/test_storage_constants.py -v
make check-all
```

---

## Wave 2: models.py + テスト (~400行)

### 実装ファイル
- `src/market/alphavantage/models.py`

### パターン参照
- `src/market/edinet/types.py` の frozen dataclass パターン

### 内容
8つの `@dataclass(frozen=True)` レコード型:

| 型 | フィールド数 | 備考 |
|---|---|---|
| `DailyPriceRecord` | 9 | adjusted_close は `float \| None` |
| `CompanyOverviewRecord` | 42 | parser.py の `_OVERVIEW_NUMERIC_FIELDS` 32個 + テキスト9個 + fetched_at |
| `IncomeStatementRecord` | 21 | |
| `BalanceSheetRecord` | 28 | |
| `CashFlowRecord` | 21 | |
| `EarningsRecord` | 9 | annual では reported_date 等が None |
| `EconomicIndicatorRecord` | 6 | interval/maturity は空文字がデフォルト |
| `ForexDailyRecord` | 8 | |

### テスト
- `tests/market/alphavantage/unit/test_models.py`
- frozen 検証、フィールド数チェック、Optional に None 指定可

### 検証
```bash
uv run pytest tests/market/alphavantage/unit/test_models.py -v
make check-all
```

---

## Wave 3: storage.py + テスト (~965行)

### 実装ファイル
- `src/market/alphavantage/storage.py`

### パターン参照
- `src/market/polymarket/storage.py` — `_build_insert_sql` (lru_cache), `_validate_finite`, factory, get_stats
- `src/market/edinet/storage.py` — `_dataclass_to_tuple`, `_migrate_add_missing_columns`, DDL-dataclass 整合性

### 主要コンポーネント

**モジュールレベル:**
- `_TABLE_DDL: dict[str, str]` — 8テーブルの DDL（設計書セクション3）
- `_VALID_TABLE_NAMES: frozenset[str]` — SQL injection 防止
- `_build_insert_sql(table_name, field_names: tuple[str, ...])` — `@lru_cache(maxsize=16)`
- `_dataclass_to_tuple(obj)` — `dataclasses.fields()` ベース
- `_validate_finite(value, name)` — NaN/Inf ガード

**AlphaVantageStorage クラス:**
- `__init__(self, db_path: Path)` → `SQLiteClient` + `ensure_tables()`
- `ensure_tables()` — DDL 実行 + `_migrate_add_missing_columns()`
- 8 upsert メソッド — `INSERT OR REPLACE` + `execute_many()`
- 8 get メソッド — `pd.read_sql_query()` + パラメータ化クエリ
  - `get_company_overview()` のみ `CompanyOverviewRecord | None` 返却（単一レコード）
  - 他は `pd.DataFrame` 返却
- `get_table_names()`, `get_row_count()`, `get_stats()`

**ファクトリ:**
- `_resolve_db_path()` — env var → `get_db_path()` フォールバック
- `get_alphavantage_storage(db_path=None)` — `@lru_cache` なし

### テスト
- `tests/market/alphavantage/unit/test_storage.py`
- `tests/market/alphavantage/conftest.py` に `av_storage` fixture 追加

主要テストクラス:
- `TestEnsureTables` — 8テーブル作成、冪等性
- `TestUpsertDailyPrices` — upsert、冪等性、PK上書き
- `TestUpsertCompanyOverview` — 全42カラム保存
- `TestUpsertEconomicIndicators` — maturity/interval 区別
- `TestGetMethods` — 日付範囲フィルタ、report_type フィルタ
- `TestMigration` — 不足カラム自動追加
- `TestDDLDataclassAlignment` — DDL ↔ dataclass フィールド名一致（全8テーブル）
- `TestGetAlphaVantageStorage` — ファクトリ、env var オーバーライド

### 検証
```bash
uv run pytest tests/market/alphavantage/unit/test_storage.py -v
make check-all
```

---

## Wave 4: collector.py + テスト (~850行)

### 実装ファイル
- `src/market/alphavantage/collector.py`

### パターン参照
- `src/market/polymarket/collector.py` — DI、エラー収集、collect_all

### 主要コンポーネント

**camelCase → snake_case 変換:**
- `_SPECIAL_KEY_MAP: dict[str, str]` — 数字先頭・略語の特殊マッピング
  - `"52WeekHigh" → "week_52_high"`, `"PERatio" → "pe_ratio"` 等
- `_camel_to_snake(key: str) → str` — 特殊マップ → 正規表現フォールバック

**Parser 出力 → Storage レコード変換:**

| collect メソッド | parser 出力 | 変換 |
|---|---|---|
| `collect_daily` | DF (snake_case) | symbol, fetched_at 追加のみ |
| `collect_company_overview` | dict (PascalCase) | `_SPECIAL_KEY_MAP` + `_camel_to_snake` |
| `collect_income_statements` | DF (camelCase) | `df.rename(columns=_camel_to_snake)` |
| `collect_balance_sheets` | 同上 | 同上 |
| `collect_cash_flows` | 同上 | 同上 |
| `collect_earnings` | tuple[DF, DF] (camelCase) | rename + period_type 追加 |
| `collect_economic_indicators` | DF (snake_case) | indicator, interval, maturity 追加 |
| `collect_forex_daily` | DF (snake_case) | from/to_currency 追加 |

**結果型:**
- `CollectionResult(symbol, table, rows_upserted, success, error_message?)`
- `CollectionSummary(results, total_symbols, successful/failed, total_rows)`

**エラーハンドリング:**
- 各 collect: try/except → `CollectionResult(success=False)` で返却
- `collect_all`: partial success サポート（一部失敗で全体を止めない）

### テスト
- `tests/market/alphavantage/unit/test_collector.py`
- mock client + mock storage で各 collect メソッドをテスト

主要テストクラス:
- `TestCamelToSnake` — 特殊キー変換、汎用変換
- `TestCollectDaily` — 正常系、API エラー、空 DF
- `TestCollectCompanyOverview` — PascalCase 変換
- `TestCollectEconomicIndicators` — 6指標一括、部分エラー
- `TestCollectAll` — 複数銘柄、partial success

### 検証
```bash
uv run pytest tests/market/alphavantage/unit/test_collector.py -v
make check-all
```

---

## Wave 5: __init__.py 更新 + Property/統合テスト (~470行)

### 変更ファイル
- `src/market/alphavantage/__init__.py` — Storage, Collector, models の export 追加

### 新規テストファイル
- `tests/market/alphavantage/property/test_storage_property.py`
  - Hypothesis で upsert 冪等性、PK 制約、ラウンドトリップ検証
- `tests/market/alphavantage/integration/test_storage_integration.py`
  - mock client + 実 DB で collect → get ラウンドトリップ

### 検証
```bash
uv run pytest tests/market/alphavantage/ -v
make check-all
```

---

## 総計

| Wave | ソース | テスト | 計 |
|---|---|---|---|
| 1 | ~80 | ~60 | ~140 |
| 2 | ~250 | ~150 | ~400 |
| 3 | ~500 | ~465 | ~965 |
| 4 | ~450 | ~400 | ~850 |
| 5 | ~20 | ~450 | ~470 |
| **計** | **~1300** | **~1525** | **~2825** |

## 各 Wave の品質チェック

```bash
make format && make lint && make typecheck && make test
```
