# EDINET DB モジュール: 公式API仕様への完全アライメント - 実装プラン

## Context

edinetdb.jp の提供データが大幅に拡充された。公式ドキュメント検証の結果、現行コードと公式APIに重大な差分が存在する:

- **FinancialRecord**: 24フィールド → 55+ フィールド（PL/BS/CF詳細項目追加）
- **RatioRecord**: 13フィールド → 25+ フィールド（成長率、生産性指標等）
- **フィールド名不一致**: `operating_cf` → `cf_operating` 等
- **全フィールドOptional化**: 公式仕様「値が存在する場合のみ返却」
- **型変更**: `fiscal_year: str` → `int`、財務値 `BIGINT` → `DOUBLE`
- **`period_type` 削除**: 公式レスポンスに存在しない

元プラン: `docs/plan/2026-03-06_edinet-api-alignment.md`

---

## Step 0: 実API検証（実装前の必須ステップ）

元プランファイルの curl コマンド7本を実行し、以下を確定する:

| # | 確認対象 | 判定内容 |
|---|---------|---------|
| 1 | `/v1/companies/E02144/financials` | `{"data": [...]}` ラッパーの有無 |
| 2 | financials フィールド名 | `cf_operating` or `operating_cf`、`fiscal_year` の型 |
| 3 | `/v1/companies/E02144/ratios` | `de_ratio`、`split_adjustment_factor` の有無 |
| 4 | `/v1/status` | エンドポイントの存在確認 |
| 5 | `/v1/companies/E02144/earnings` | REST エンドポイントの存在確認 |
| 6 | `/v1/search?q=トヨタ` | レスポンスキー `"results"` or `"data"` |
| 7 | `/v1/companies?per_page=2` | `corp_name` or `name` |

**結果に基づきStep 1以降を微調整する。**

---

## Step 1: types.py — データモデル全面更新

**ファイル**: `src/market/edinet/types.py`

### FinancialRecord (L271-385)

| 変更 | 内容 |
|------|------|
| `fiscal_year` | `str` → `int` |
| `period_type` | 削除 |
| `accounting_standard` | 新規追加 `str \| None = None` |
| 全財務フィールド | `int` (必須) → `float \| None = None` |
| リネーム | `operating_cf`→`cf_operating`, `investing_cf`→`cf_investing`, `financing_cf`→`cf_financing`, `employees`→`num_employees`, `rnd_expense`→`rnd_expenses` |
| 削除 | `equity`, `interest_bearing_debt`, `free_cf`, `shares_outstanding`, `period_type` |
| 追加 (~30) | `cost_of_sales`, `gross_profit`, `sga`, `extraordinary_income/loss`, `profit_before_tax`, `comprehensive_income`, BS詳細(current_assets, ppe, inventories, trade_receivables, cash等), 負債詳細(short_term_loans, long_term_loans等), `diluted_eps`, `per`, `payout_ratio`, `roe_official`, `equity_ratio_official` |

### RatioRecord (L388-470)

| 変更 | 内容 |
|------|------|
| `fiscal_year` | `str` → `int` |
| `period_type` | 削除 |
| 全フィールド | `float` (必須) → `float \| None = None` |
| リネーム | `debt_equity_ratio`→`de_ratio`, `operating_income_growth`→`oi_growth`, `net_income_growth`→`ni_growth` |
| 削除 | `interest_coverage_ratio`, `period_type` |
| 追加 (~12) | `gross_margin`, `sga_ratio`, `rnd_ratio`, `ebitda`, `interest_bearing_debt`, `net_debt`, `fcf`, `eps_growth`, CAGR系(revenue_cagr_3y等), `dividend_yield`, `split_adjustment_factor`, `adjusted_dividend_per_share`, 生産性(revenue_per_employee等) |

### EarningsRecord（条件付き新規追加）

Step 0で `/v1/companies/{code}/earnings` が存在する場合のみ追加。

---

## Step 2: client.py — レスポンスパース更新

**ファイル**: `src/market/edinet/client.py`

### 2a. `_parse_record` ジェネリックヘルパー追加

```python
def _parse_record[T](self, cls: type[T], raw: dict[str, Any]) -> T:
    known = {f.name for f in dataclasses.fields(cls)}
    filtered = {k: v for k, v in raw.items() if k in known}
    return cls(**filtered)
```

以下6箇所を置換:
- L260: `Company(**item)` → `self._parse_record(Company, item)`
- L294: `Company(**data)` → `self._parse_record(Company, data)`
- L328: `FinancialRecord(**item)` → `self._parse_record(FinancialRecord, item)`
- L362: `RatioRecord(**item)` → `self._parse_record(RatioRecord, item)`
- L396: `AnalysisResult(**data)` → `self._parse_record(AnalysisResult, data)`
- L444: `TextBlock(**item)` → `self._parse_record(TextBlock, item)`

### 2b. レスポンスアンラップ（Step 0結果次第）

`{"data": [...]}` 形式の場合、`_request()` の戻り値をアンラップ。

### 2c. `search()` レスポンスキー更新（L222）

`data.get("results", [])` → Step 0結果に基づき修正。

### 2d. 新メソッド（条件付き）

- `get_status()` → `GET /v1/status`（認証不要）
- `get_earnings(code, limit=8)` → `GET /v1/companies/{code}/earnings`

### 再利用パターン

- `_RetryableError` + 指数バックオフ + jitter（既存、変更なし）
- `DailyRateLimiter`（既存、変更なし）

---

## Step 3: storage.py — DDL・マイグレーション更新

**ファイル**: `src/market/edinet/storage.py`

### 3a. DDL全面書き換え（L84-130）

- `TABLE_FINANCIALS`: `period_type` 削除、`fiscal_year VARCHAR` → `INTEGER`、全値を `DOUBLE`（nullable）、~30カラム追加
- `TABLE_RATIOS`: 同様の変更、~12カラム追加

### 3b. スキーママイグレーション戦略: DROP + RECREATE

**プロジェクト内にALTER TABLE ADD COLUMNの前例がない** ため、型変更・リネーム・削除を含むこの変更には **バックアップ→DROP→再CREATE→データ復元** 方式を採用。

```python
def _migrate_schema(self) -> None:
    """既存テーブルを新スキーマにマイグレーション。"""
    for table_name, ddl in _TABLE_DDL.items():
        if not self._table_exists(table_name):
            continue
        existing_cols = self._get_column_info(table_name)
        expected_cols = self._parse_ddl_columns(ddl)
        if self._schema_matches(existing_cols, expected_cols):
            continue
        self._migrate_table(table_name, ddl)
```

`_migrate_table` の処理:
1. `CREATE TABLE {name}_backup AS SELECT * FROM {name}`
2. `DROP TABLE {name}`
3. 新DDLで `CREATE TABLE`
4. カラムマッピング（リネーム＋型変換）で `INSERT INTO ... SELECT ...`
5. `DROP TABLE {name}_backup`

カラムリネームマップ:
```python
_COLUMN_RENAMES = {
    "financials": {
        "operating_cf": "cf_operating",
        "investing_cf": "cf_investing",
        "financing_cf": "cf_financing",
        "employees": "num_employees",
        "rnd_expense": "rnd_expenses",
    },
    "ratios": {
        "debt_equity_ratio": "de_ratio",
        "operating_income_growth": "oi_growth",
        "net_income_growth": "ni_growth",
    },
}
```

`fiscal_year` の型変換: `CAST(fiscal_year AS INTEGER)`

### 3c. `ensure_tables()` から `_migrate_schema()` を呼び出し

既存の `CREATE TABLE IF NOT EXISTS` ループの後に実行。

### 3d. upsert key_columns

`financials`/`ratios` のキーは `(edinet_code, fiscal_year)` で変更なし。`period_type` は削除されるがキーには含まれていなかった（確認済み: L257-262）。

---

## Step 4: constants.py — 定数更新

**ファイル**: `src/market/edinet/constants.py`

- `TABLE_EARNINGS` 追加（条件付き）
- `RANKING_METRICS` はStep 0で確認後、必要に応じて更新

---

## Step 5: syncer.py — 同期フロー更新

**ファイル**: `src/market/edinet/syncer.py`

- 既存6フェーズは自動的に新フィールドに対応（client→storageのパススルー）
- `earnings` エンドポイント存在時: `PHASE_EARNINGS` を `PHASE_ORDER` に追加、`_sync_company_earnings()` メソッド追加

---

## Step 6: テスト更新

| ファイル | 変更内容 |
|---------|---------|
| `tests/market/unit/edinet/conftest.py` | Fixture更新（Optional化、fiscal_year=int、新フィールド名） |
| `tests/market/unit/edinet/test_types.py` | Optional defaults=None テスト、fiscal_year int テスト |
| `tests/market/unit/edinet/test_client.py` | `_parse_record` テスト、未知フィールド無視テスト |
| `tests/market/unit/edinet/test_storage.py` | 新DDLテスト、`_migrate_schema` テスト |
| `tests/market/unit/edinet/test_syncer.py` | mock_client fixture更新、Phase数更新（条件付き） |

---

## Step 7-8: README.md + __init__.py 更新

- `src/market/edinet/README.md`: フィールド一覧テーブル全面更新
- `src/market/edinet/__init__.py`: `EarningsRecord` エクスポート追加（条件付き）
- `src/market/edinet/scripts/sync.py`: docstring更新

---

## PR分割戦略（4PR）

```
PR 1: types.py + client.py + テスト
  branch: feature/edinet-api-types-client
  ├── types.py (FinancialRecord/RatioRecord全面更新)
  ├── client.py (_parse_record, _unwrap_response)
  ├── conftest.py (fixture更新)
  ├── test_types.py
  └── test_client.py
    ↓
PR 2: storage.py + constants.py + テスト
  branch: feature/edinet-api-storage-migration
  ├── storage.py (DDL書き換え, _migrate_schema)
  ├── constants.py
  └── test_storage.py
    ↓
PR 3: syncer.py + 新エンドポイント + テスト
  branch: feature/edinet-api-syncer
  ├── syncer.py (earnings Phase, 条件付き)
  ├── client.py (get_status, get_earnings)
  ├── __init__.py
  └── test_syncer.py
    ↓
PR 4: ドキュメント + 統合テスト
  branch: docs/edinet-api-alignment
  ├── README.md
  ├── scripts/sync.py (docstring)
  └── test_client_integration.py
```

---

## リスクと対策

| リスク | 深刻度 | 対策 |
|--------|--------|------|
| スキーママイグレーションでデータ損失 | Critical | backup テーブル作成 → try/except で復元 → 失敗時も再sync可能 |
| store_df カラム不一致 | High | `dataclasses.asdict()` が新スキーマと一致することをテストで保証 |
| 実APIフィールド名がドキュメントと異なる | High | Step 0 で必ず検証 → `_parse_record` が未知フィールドを無視 |
| fiscal_year型変更で既存クエリ破損 | Medium | マイグレーションで `CAST(VARCHAR AS INTEGER)` → パラメータ化クエリで型安全 |
| 外部消費者への破壊的変更 | Medium | Grep確認済み: EDINETモジュールは `src/market/edinet/` 内で完結 |

---

## 修正ファイル一覧

| ファイル | 変更規模 |
|---------|---------|
| `src/market/edinet/types.py` | **大** |
| `src/market/edinet/client.py` | **大** |
| `src/market/edinet/storage.py` | **大** |
| `src/market/edinet/constants.py` | 小 |
| `src/market/edinet/syncer.py` | 中 |
| `src/market/edinet/__init__.py` | 小 |
| `src/market/edinet/scripts/sync.py` | 小 |
| `src/market/edinet/README.md` | **大** |
| `tests/market/unit/edinet/conftest.py` | 中 |
| `tests/market/unit/edinet/test_types.py` | 大 |
| `tests/market/unit/edinet/test_client.py` | 大 |
| `tests/market/unit/edinet/test_storage.py` | 大 |
| `tests/market/unit/edinet/test_syncer.py` | 中 |

---

## 再利用する既存パターン

| パターン | ファイル |
|---------|---------|
| `DuckDBClient.store_df(if_exists="upsert")` | `src/database/db/duckdb_client.py` |
| frozen dataclass パターン | `src/market/edinet/types.py` |
| `_RetryableError` + backoff | `src/market/edinet/client.py` |
| `DailyRateLimiter` | `src/market/edinet/rate_limiter.py` |
| `_TABLE_DDL` + `ensure_tables()` | `src/market/edinet/storage.py` |
| チェックポイント + resume | `src/market/edinet/syncer.py` |

---

## 検証手順

```bash
# 1. Step 0: API実検証
# 元プランファイルの curl コマンド7本を実行

# 2. 各PR: 単体テスト
uv run pytest tests/market/unit/edinet/ -v

# 3. 各PR: 品質チェック
make check-all

# 4. PR 2後: マイグレーション検証（既存DBファイルがある場合）
# EdinetStorage初期化時にensure_tables→_migrate_schemaが自動実行

# 5. 全PR後: 統合テスト
EDINET_DB_API_KEY=xxx uv run pytest tests/market/integration/edinet/ -v

# 6. 動作確認
# 新フィールド名・Optional・fiscal_year=intの確認
```
