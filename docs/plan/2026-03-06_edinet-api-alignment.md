# EDINET DB モジュール: 公式API仕様への完全アライメント

## Context

edinetdb.jp の提供データが大幅に拡充された。公式ドキュメント（https://edinetdb.jp/developers）を検証した結果、現在のコードベースと公式APIの間に以下の重大な差分が存在する:

1. **財務フィールド**: 現行 24 → 公式 55+ フィールド（PL/BS/CF 詳細項目が大量追加）
2. **比率フィールド**: 現行 13 → 公式 25+ フィールド（成長率、生産性指標等）
3. **フィールド名の不一致**: `operating_cf` → `cf_operating` 等、複数のリネーム
4. **フィールドのオプショナル化**: 公式「値が存在する場合のみレスポンスに含まれる」→ 現行は全フィールド必須
5. **`accounting_standard` フィールド新設**: 会計基準（JP GAAP/IFRS/US GAAP）の識別
6. **株式分割調整**: `split_adjustment_factor`, `adjusted_dividend_per_share` がratiosに追加
7. **`/v1/status` エンドポイント**: 新規（認証不要）
8. **レスポンス形式**: `r.json()["data"]` ラッパーの可能性あり（要実API検証）
9. **MCP `get_earnings`**: TDNet決算短信（REST APIエンドポイントとしては未掲載、MCP toolとして存在）

---

## Step 0: 実API検証（実装前の必須ステップ）

公式ドキュメントのフィールド名とAPIレスポンスの整合性を確認するため、実際にAPIを叩いてサンプルレスポンスを取得する。

```bash
# 1. レスポンス形式の確認（"data" ラッパーの有無）
curl -s -H "X-API-Key: $EDINET_DB_API_KEY" \
  "https://edinetdb.jp/v1/companies/E02144/financials" | python3 -m json.tool | head -30

# 2. financials フィールド名の確認
curl -s -H "X-API-Key: $EDINET_DB_API_KEY" \
  "https://edinetdb.jp/v1/companies/E02144/financials" | python3 -c "
import json, sys
d = json.load(sys.stdin)
# data ラッパーがあるか確認
if isinstance(d, dict) and 'data' in d:
    print('Response wrapped in \"data\" key')
    items = d['data']
else:
    items = d
if items:
    print(f'Fields ({len(items[0])} total):')
    for k, v in sorted(items[0].items()):
        print(f'  {k}: {type(v).__name__} = {v}')
"

# 3. ratios フィールド名の確認
curl -s -H "X-API-Key: $EDINET_DB_API_KEY" \
  "https://edinetdb.jp/v1/companies/E02144/ratios" | python3 -c "
import json, sys
d = json.load(sys.stdin)
items = d.get('data', d) if isinstance(d, dict) else d
if items:
    print(f'Fields ({len(items[0])} total):')
    for k, v in sorted(items[0].items()):
        print(f'  {k}: {type(v).__name__} = {v}')
"

# 4. /v1/status エンドポイントの確認
curl -s "https://edinetdb.jp/v1/status" | python3 -m json.tool

# 5. earnings エンドポイントの確認（REST API として存在するか）
curl -s -H "X-API-Key: $EDINET_DB_API_KEY" \
  "https://edinetdb.jp/v1/companies/E02144/earnings" | python3 -m json.tool | head -30

# 6. search レスポンスのフィールド名確認（"results" → "data" に変わったか）
curl -s -H "X-API-Key: $EDINET_DB_API_KEY" \
  "https://edinetdb.jp/v1/search?q=トヨタ" | python3 -m json.tool | head -20

# 7. companies レスポンスのフィールド名確認
curl -s -H "X-API-Key: $EDINET_DB_API_KEY" \
  "https://edinetdb.jp/v1/companies?per_page=2" | python3 -m json.tool | head -30
```

**Step 0 の結果で以降のプランを微調整する。** 特にフィールド名・レスポンスラッパー・earnings REST有無が確定する。

---

## Step 1: types.py — データモデルの全面更新

### 1a. FinancialRecord の更新

**公式ドキュメントに基づく全フィールド一覧**（すべて `float | None = None`、メタフィールドのみ必須）:

```python
@dataclass(frozen=True)
class FinancialRecord:
    # --- メタ（必須） ---
    edinet_code: str
    fiscal_year: int                          # str → int（公式: int）
    accounting_standard: str | None = None    # "JP GAAP" / "IFRS" / "US GAAP"

    # --- PL ---
    revenue: float | None = None
    cost_of_sales: float | None = None
    gross_profit: float | None = None
    sga: float | None = None
    operating_income: float | None = None
    ordinary_income: float | None = None       # JP GAAP only
    extraordinary_income: float | None = None   # JP GAAP only
    extraordinary_loss: float | None = None     # JP GAAP only
    profit_before_tax: float | None = None
    net_income: float | None = None
    comprehensive_income: float | None = None
    depreciation: float | None = None
    rnd_expenses: float | None = None           # renamed from rnd_expense

    # --- BS ---
    total_assets: float | None = None
    current_assets: float | None = None
    noncurrent_assets: float | None = None
    ppe: float | None = None
    intangible_assets: float | None = None
    goodwill: float | None = None
    software: float | None = None
    inventories: float | None = None
    trade_receivables: float | None = None
    cash: float | None = None
    total_liabilities: float | None = None
    current_liabilities: float | None = None
    noncurrent_liabilities: float | None = None  # JP GAAP only
    trade_payables: float | None = None
    short_term_loans: float | None = None         # JP GAAP only
    long_term_loans: float | None = None           # JP GAAP only
    bonds_payable: float | None = None             # JP GAAP only
    ibd_current: float | None = None               # IFRS only
    ibd_noncurrent: float | None = None            # IFRS only
    current_portion_lt_loans: float | None = None  # JP GAAP only
    lease_obligations_cl: float | None = None      # JP GAAP only
    lease_obligations_ncl: float | None = None     # JP GAAP only
    commercial_papers: float | None = None         # JP GAAP only
    lease_liabilities_cl: float | None = None      # IFRS only
    lease_liabilities_ncl: float | None = None     # IFRS only
    net_assets: float | None = None
    retained_earnings: float | None = None
    non_controlling_interests: float | None = None
    shareholders_equity: float | None = None       # JP GAAP only

    # --- CF ---
    cf_operating: float | None = None              # renamed from operating_cf
    cf_investing: float | None = None              # renamed from investing_cf
    cf_financing: float | None = None              # renamed from financing_cf
    capex: float | None = None

    # --- 1株指標 ---
    eps: float | None = None
    diluted_eps: float | None = None
    bps: float | None = None
    dividend_per_share: float | None = None
    per: float | None = None
    payout_ratio: float | None = None

    # --- その他 ---
    roe_official: float | None = None
    equity_ratio_official: float | None = None
    num_employees: int | None = None               # renamed from employees
```

**変更ポイント**:
- `fiscal_year`: `str` → `int`（公式仕様に合わせる）
- 全財務フィールドを `float | None = None` に（API仕様: 値が存在する場合のみ返却）
- フィールド名変更: `operating_cf` → `cf_operating`, `employees` → `num_employees`, `rnd_expense` → `rnd_expenses`
- 削除: `period_type`, `equity`, `interest_bearing_debt`, `free_cf`, `shares_outstanding`（APIレスポンスにない / ratiosに移動）
- 追加: ~30 新フィールド

### 1b. RatioRecord の更新

```python
@dataclass(frozen=True)
class RatioRecord:
    # --- メタ（必須） ---
    edinet_code: str
    fiscal_year: int

    # --- 収益性 ---
    gross_margin: float | None = None
    operating_margin: float | None = None
    net_margin: float | None = None
    sga_ratio: float | None = None
    rnd_ratio: float | None = None
    ebitda: float | None = None

    # --- 資本効率 ---
    roe: float | None = None
    roa: float | None = None
    asset_turnover: float | None = None

    # --- 安全性 ---
    equity_ratio: float | None = None
    current_ratio: float | None = None
    interest_bearing_debt: float | None = None
    de_ratio: float | None = None
    net_debt: float | None = None
    fcf: float | None = None

    # --- 成長性（YoY） ---
    revenue_growth: float | None = None
    oi_growth: float | None = None                 # renamed from operating_income_growth
    ni_growth: float | None = None                 # renamed from net_income_growth
    eps_growth: float | None = None

    # --- 成長性（CAGR） ---
    revenue_cagr_3y: float | None = None
    oi_cagr_3y: float | None = None
    ni_cagr_3y: float | None = None
    eps_cagr_3y: float | None = None

    # --- 株主還元 ---
    dividend_yield: float | None = None

    # --- 分割調整 ---
    split_adjustment_factor: float | None = None
    adjusted_dividend_per_share: float | None = None

    # --- 生産性 ---
    revenue_per_employee: float | None = None
    net_income_per_employee: float | None = None
    capex_to_depreciation: float | None = None
```

**変更ポイント**:
- `period_type` 削除、`debt_equity_ratio` → `de_ratio`、`interest_coverage_ratio` → 削除（公式に無い）
- `operating_income_growth` → `oi_growth`、`net_income_growth` → `ni_growth`
- 全フィールドを `float | None = None` に
- ~15 新フィールド追加

### 1c. Company の確認

Step 0 で `/v1/companies` のレスポンスフィールドを確認し、変更があれば追従。公式コード例では `name` / `sec_code` / `edinet_code` が見える。`corp_name` → `name` のリネームの可能性あり。

### 1d. EarningsRecord 新規追加（条件付き）

Step 0 で `/v1/companies/{code}/earnings` REST エンドポイントが存在することが確認できた場合のみ追加。

---

## Step 2: client.py — レスポンスパース更新

### 2a. レスポンスアンラッピング

公式コード例 `r.json()["data"]` が示すように、レスポンスが `{"data": [...]}` 形式になっている可能性。Step 0 の結果に基づき、`_request()` または各メソッドでアンラップ処理を追加。

```python
# _request() の戻り値を変えるか、各メソッドで対応
def _unwrap_response(self, data: Any) -> Any:
    """Unwrap {"data": ...} response envelope if present."""
    if isinstance(data, dict) and "data" in data:
        return data["data"]
    return data
```

### 2b. データクラス生成の堅牢化

APIが返すフィールドとdataclassのフィールドの差異を吸収:

```python
def _parse_record[T](self, cls: type[T], raw: dict[str, Any]) -> T:
    """Create a dataclass instance, ignoring unknown fields."""
    known = {f.name for f in dataclasses.fields(cls)}
    filtered = {k: v for k, v in raw.items() if k in known}
    return cls(**filtered)
```

各メソッドで `FinancialRecord(**item)` → `self._parse_record(FinancialRecord, item)` に変更。

### 2c. 新メソッド追加

| メソッド | エンドポイント | 説明 |
|---------|-------------|------|
| `get_status()` | `GET /v1/status` | APIステータス確認（認証不要） |
| `get_earnings(code, limit=8)` | `GET /v1/companies/{code}/earnings` | TDNet決算短信（Step 0で確認後） |

### 2d. search() のレスポンスキー更新

`data.get("results", [])` → `data.get("data", data.get("results", []))` のフォールバック、またはStep 0結果に基づき修正。

---

## Step 3: storage.py — DDL・upsert更新

### 3a. DDL更新

`_TABLE_DDL` のfinancials, ratios テーブルを全面書き換え。全フィールドを `DOUBLE`（nullable）に。

```sql
CREATE TABLE IF NOT EXISTS financials (
    edinet_code VARCHAR NOT NULL,
    fiscal_year INTEGER NOT NULL,
    accounting_standard VARCHAR,
    revenue DOUBLE,
    cost_of_sales DOUBLE,
    gross_profit DOUBLE,
    -- ... 全フィールド（NOT NULL なし）
)
```

### 3b. スキーママイグレーション

既存テーブルとの互換性のため `_migrate_schema()` メソッドを追加:

```python
def _migrate_schema(self) -> None:
    """Add missing columns to existing tables via ALTER TABLE."""
    for table_name, ddl in _TABLE_DDL.items():
        # DDLからカラム定義を抽出
        # 既存テーブルのカラムと比較
        # 不足カラムを ALTER TABLE ADD COLUMN で追加
```

DuckDB は `ALTER TABLE ... ADD COLUMN` をサポートしている。`ensure_tables()` から呼び出す。

### 3c. upsert key_columns

| テーブル | 現行キー | 新キー |
|---------|---------|-------|
| financials | `(edinet_code, fiscal_year)` | `(edinet_code, fiscal_year)` — 変更なし |
| ratios | `(edinet_code, fiscal_year)` | `(edinet_code, fiscal_year)` — 変更なし |

`period_type` が financials/ratios から削除されるため、キーは2列のまま。

### 3d. earnings テーブル追加（条件付き）

Step 0 で確認後、`TABLE_EARNINGS` と対応DDL/upsert/queryメソッドを追加。

---

## Step 4: constants.py — 定数更新

| 変更 | 内容 |
|------|------|
| `TABLE_EARNINGS` 追加 | `"earnings"`（条件付き） |
| `RANKING_METRICS` 確認 | 現行20指標が最新と一致するか Step 0 で確認 |

---

## Step 5: syncer.py — 同期フロー更新

### 5a. Phase 構成

現行6フェーズは維持。earnings エンドポイントが存在する場合は Phase 7 を追加:

| Phase | 説明 | 変更 |
|-------|------|------|
| 1. companies | 企業一覧 | 変更なし |
| 2. industries | 業種マスタ | 変更なし |
| 3. rankings | ランキング | 変更なし |
| 4. company_details | 企業詳細 | 変更なし |
| 5. financials_ratios | 財務+比率 | 新フィールド対応（自動） |
| 6. analysis_text | AI分析+テキスト | 変更なし |
| 7. earnings（新規） | 決算短信 | 条件付き追加 |

### 5b. sync_company() 更新

earnings が利用可能な場合、`_sync_company_earnings()` を追加。

---

## Step 6: テスト更新

| テストファイル | 変更内容 |
|-------------|---------|
| `test_types.py` | 新データクラスの生成テスト、オプショナルフィールドのデフォルトNoneテスト |
| `test_client.py` | `_parse_record` テスト、未知フィールド無視テスト、新メソッドテスト |
| `test_storage.py` | 新DDLテスト、マイグレーションテスト、新upsertテスト |
| `test_syncer.py` | Phase数の更新、新Phaseテスト（条件付き） |
| `conftest.py` | サンプルデータ fixtures 更新（新フィールド対応） |

---

## Step 7: README.md 更新

- フィールド一覧テーブルを公式仕様に合わせて全面更新
- 使用例を更新（新フィールド名、オプショナルフィールドの扱い）
- earnings セクション追加（条件付き）
- データカバレッジセクション追加（会計基準別の取得率情報）

---

## Step 8: __init__.py 更新

新しいエクスポートを追加（`EarningsRecord` 等、条件付き）。

---

## 修正ファイル一覧

| ファイル | 変更規模 | 内容 |
|---------|---------|------|
| `src/market/edinet/types.py` | **大** | FinancialRecord/RatioRecord 全面更新、EarningsRecord 追加 |
| `src/market/edinet/client.py` | **大** | _parse_record 追加、レスポンスアンラップ、新メソッド |
| `src/market/edinet/storage.py` | **大** | DDL全面更新、_migrate_schema 追加、新テーブル |
| `src/market/edinet/constants.py` | 小 | TABLE_EARNINGS 追加 |
| `src/market/edinet/syncer.py` | 中 | earnings Phase 追加（条件付き） |
| `src/market/edinet/__init__.py` | 小 | エクスポート更新 |
| `src/market/edinet/scripts/sync.py` | 小 | docstring 更新 |
| `src/market/edinet/README.md` | **大** | 全面更新 |
| `tests/market/unit/edinet/test_types.py` | 大 | 新フィールドテスト |
| `tests/market/unit/edinet/test_client.py` | 大 | パース堅牢化テスト |
| `tests/market/unit/edinet/test_storage.py` | 大 | DDL・マイグレーションテスト |
| `tests/market/unit/edinet/test_syncer.py` | 中 | Phase数更新 |
| `tests/market/unit/edinet/conftest.py` | 中 | fixtures 更新 |

---

## 再利用する既存パターン

| パターン | ファイルパス | 用途 |
|---------|-----------|------|
| `DuckDBClient.store_df(if_exists="upsert")` | `src/database/db/duckdb_client.py` | upsert 処理 |
| `get_db_path()` | `src/database/db/connection.py` | DB パス解決 |
| `get_logger()` | `src/utils_core/logging.py` | 構造化ロギング |
| frozen dataclass パターン | `src/market/edinet/types.py` | イミュータブルデータクラス |
| `_RetryableError` + backoff | `src/market/edinet/client.py` | リトライロジック |
| `DailyRateLimiter` | `src/market/edinet/rate_limiter.py` | レート制限管理 |
| `_TABLE_DDL` + `ensure_tables()` | `src/market/edinet/storage.py` | テーブル管理パターン |

---

## 検証手順

### 1. API検証（Step 0）
```bash
# 上記 curl コマンドでサンプルレスポンスを取得・確認
```

### 2. 単体テスト
```bash
uv run pytest tests/market/unit/edinet/ -v
```

### 3. 品質チェック
```bash
make check-all  # format, lint, typecheck, test
```

### 4. 統合テスト（要APIキー）
```bash
EDINET_DB_API_KEY=xxx uv run pytest tests/market/integration/edinet/ -v
```

### 5. 動作確認
```python
from market.edinet import EdinetClient, EdinetConfig
config = EdinetConfig(api_key="xxx")
with EdinetClient(config=config) as client:
    # 財務データ取得（新フィールド確認）
    records = client.get_financials("E02144")
    r = records[0]
    print(f"accounting_standard: {r.accounting_standard}")
    print(f"gross_profit: {r.gross_profit}")
    print(f"cf_operating: {r.cf_operating}")

    # 比率（分割調整確認）
    ratios = client.get_ratios("E02144")
    print(f"split_adjustment_factor: {ratios[0].split_adjustment_factor}")
    print(f"ebitda: {ratios[0].ebitda}")
```

---

## 実装順序

1. **Step 0**: API実検証 → フィールド名・レスポンス形式確定
2. **Step 1**: types.py 更新（データモデル）
3. **Step 2**: client.py 更新（パース・新メソッド）
4. **Step 3**: storage.py 更新（DDL・マイグレーション）
5. **Step 4-5**: constants.py / syncer.py 更新
6. **Step 6**: テスト更新・実行
7. **Step 7-8**: README.md / __init__.py 更新
8. `make check-all` で全品質チェック通過を確認
