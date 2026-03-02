# DB スキーマ設計パターン集

SQLite vs DuckDB の選択基準、MultiIndex→DB 変換パターン、マイグレーション管理規約、
DuckDB upsert パターン、DuckDB 型マッピングを体系化したパターン集です。
既存コードベースの実装例と行番号注釈を含みます。

---

## 6つのルール

| # | ルール | 要点 |
|---|--------|------|
| 1 | SQLite vs DuckDB の選択基準 | データ量・クエリパターン・ユースケースで判断 |
| 2 | DuckDB 型マッピング | Python/pandas 型と DuckDB 型の対応表 |
| 3 | MultiIndex → DB 変換 | pandas MultiIndex をフラットカラムに変換して保存 |
| 4 | DuckDB upsert パターン | DELETE + INSERT 方式でべき等な更新を実現 |
| 5 | マイグレーション管理規約 | `YYYYMMDD_HHMMSS_description.sql` 形式で管理 |
| 6 | DDL 定義パターン | テーブル定義の辞書管理と一括作成 |

---

## ルール 1: SQLite vs DuckDB の選択基準

### 1.1 選択基準表

| 基準 | SQLite | DuckDB |
|------|--------|--------|
| **データ量** | < 10万行 | > 100万行 |
| **クエリパターン** | CRUD（行単位の読み書き） | OLAP（集計・分析クエリ） |
| **主な用途** | メタデータ、設定、フェッチ履歴 | 時系列データ、財務データ分析 |
| **トランザクション** | ACID 完全対応、行ロック | 読み取り中心、並行書込みに制限あり |
| **Parquet 連携** | 非対応 | `SELECT * FROM 'file.parquet'` で直接読込 |
| **pandas 連携** | `pd.read_sql` / `to_sql` | `conn.execute()` + DataFrame 直接参照 |
| **ファイル拡張子** | `.db` | `.duckdb` |
| **パス規約** | `data/sqlite/{name}.db` | `data/duckdb/{name}.duckdb` |

### 1.2 パス取得パターン

```python
from database.db import get_db_path

# SQLite: メタデータ・設定用
sqlite_path = get_db_path("sqlite", "market")
# → data/sqlite/market.db

# DuckDB: 分析・大規模データ用
duckdb_path = get_db_path("duckdb", "analytics")
# → data/duckdb/analytics.duckdb
```

> **参照**: `src/database/db/connection.py` lines 56-82 -- `get_db_path()` の実装

### 1.3 選択フローチャート

```
データストア選択:
├── レコード数 < 10万 & CRUD 中心
│   ├── メタデータ・設定 → SQLite
│   ├── フェッチ履歴・ログ → SQLite
│   └── マイグレーション管理 → SQLite
├── レコード数 > 100万 & 集計クエリ
│   ├── 時系列データ（株価・指標） → DuckDB
│   ├── 財務データ分析 → DuckDB
│   └── Parquet ファイルの読込 → DuckDB
└── 中間データ・バッチ処理
    └── 一時的な入出力 → Parquet ファイル
```

### 1.4 プロジェクトでの使い分け実例

| パッケージ | DB | 理由 |
|------------|-----|------|
| `database.db.migrations` | SQLite | `schema_migrations` テーブルで適用済みマイグレーション管理 |
| `database.db` の `prices_daily` / `indicators` | SQLite | 日次価格・経済指標の CRUD（初期スキーマ） |
| `market.edinet` | DuckDB | 8テーブルの財務データ分析、集計クエリが中心 |

> **参照**: `src/database/db/migrations/runner.py` lines 14-21 -- SQLite による `schema_migrations` テーブル
> **参照**: `src/market/edinet/storage.py` lines 73-170 -- DuckDB による 8テーブルの DDL 定義

---

## ルール 2: DuckDB 型マッピング

### 2.1 Python/pandas → DuckDB 型対応表

| Python 型 | pandas dtype | DuckDB 型 | 用途 |
|-----------|-------------|-----------|------|
| `str` | `object` | `VARCHAR` | テキスト（銘柄コード、名称、カテゴリ） |
| `int` | `int64` | `BIGINT` | 大きな整数（金額、株数、従業員数） |
| `int` | `int32` | `INTEGER` | 小さな整数（ランク、カウント） |
| `float` | `float64` | `DOUBLE` | 浮動小数点（比率、スコア、EPS/BPS） |
| `datetime` | `datetime64[ns]` | `TIMESTAMP` | タイムスタンプ |
| `date` | `object` (date) | `DATE` | 日付のみ |
| `bool` | `bool` | `BOOLEAN` | フラグ |

### 2.2 型選択の実装例

```python
# VARCHAR: テキストデータ
"edinet_code VARCHAR NOT NULL"
"corp_name VARCHAR NOT NULL"
"industry_name VARCHAR NOT NULL"

# BIGINT: 大きな整数（金額系は BIGINT を使用）
"revenue BIGINT NOT NULL"
"total_assets BIGINT NOT NULL"
"shares_outstanding BIGINT NOT NULL"

# DOUBLE: 浮動小数点（比率・スコア）
"roe DOUBLE NOT NULL"
"eps DOUBLE NOT NULL"
"health_score DOUBLE NOT NULL"

# INTEGER: 小さな整数
"rank INTEGER NOT NULL"
"company_count INTEGER NOT NULL"
```

> **参照**: `src/market/edinet/storage.py` lines 84-170 -- DuckDB DDL での型使用例

### 2.3 型選択のガイドライン

| 判断基準 | 推奨型 | 理由 |
|----------|--------|------|
| 金額・株数（大きな整数） | `BIGINT` | `INTEGER` では 21億を超えるとオーバーフロー |
| 財務比率・スコア | `DOUBLE` | 十分な精度と計算性能 |
| テキスト（可変長） | `VARCHAR` | DuckDB は VARCHAR にサイズ制限不要 |
| ランク・カウント（小さな整数） | `INTEGER` | メモリ効率が BIGINT より良い |
| 日付のみ（時刻不要） | `DATE` | SQLite の `DATE` 相当 |
| タイムスタンプ | `TIMESTAMP` | タイムゾーンが必要なら `TIMESTAMPTZ` |

---

## ルール 3: MultiIndex → DB 変換パターン

### 3.1 問題: pandas MultiIndex は DB カラムにならない

pandas の MultiIndex は階層的なインデックスだが、DB テーブルにはフラットなカラムが必要。

```python
# MultiIndex DataFrame（典型的な市場データ）
#              close    volume
# symbol date
# AAPL   2024-01-01  185.0  1000000
#        2024-01-02  186.5  1200000
# MSFT   2024-01-01  375.0   800000
```

### 3.2 変換パターン: `reset_index()` でフラット化

```python
# MultiIndex → フラットカラム
df_flat = df.reset_index()
# symbol       date        close    volume
# AAPL    2024-01-01      185.0   1000000
# AAPL    2024-01-02      186.5   1200000
# MSFT    2024-01-01      375.0    800000

# DuckDB に保存
client.store_df(
    df_flat,
    "prices_daily",
    if_exists="upsert",
    key_columns=["symbol", "date"],
)
```

### 3.3 逆変換: DB → MultiIndex

```python
# DB から読み込み
df = client.query_df("SELECT * FROM prices_daily")

# フラットカラム → MultiIndex
df_multi = df.set_index(["symbol", "date"])
```

### 3.4 複合キーの UNIQUE 制約

MultiIndex のレベルをそのまま複合 UNIQUE 制約に変換する:

```sql
-- MultiIndex: (symbol, date, source) → UNIQUE 制約
CREATE TABLE IF NOT EXISTS prices_daily (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    symbol TEXT NOT NULL,
    date DATE NOT NULL,
    open REAL,
    high REAL,
    low REAL,
    close REAL,
    adj_close REAL,
    volume INTEGER,
    source TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(symbol, date, source)
);
```

> **参照**: `src/database/db/migrations/versions/20250111_000000_initial_schema.sql` lines 19-33 -- `UNIQUE(symbol, date, source)` 制約

### 3.5 DuckDB での複合キーによる upsert

```python
# MultiIndex の各レベルを key_columns に指定
client.store_df(
    df_flat,
    "financials",
    if_exists="upsert",
    key_columns=["edinet_code", "fiscal_year"],  # 複合キー
)
```

> **参照**: `src/market/edinet/storage.py` lines 257-261 -- 複合キー `["edinet_code", "fiscal_year"]` による upsert

---

## ルール 4: DuckDB upsert パターン

### 4.1 upsert の仕組み: DELETE + INSERT

DuckDB には `INSERT ... ON CONFLICT` 構文がないため、DELETE + INSERT 方式でべき等な更新を実現する。

```python
# AIDEV-NOTE: table_name, key_columns はバリデーション済みの内部値を使用すること。
# ユーザー入力を直接 f-string に渡すと SQL インジェクション（CWE-89）のリスクがある。
# 実装では validate_identifier() を呼び出してからこのパターンを適用する。

# Step 1: キーが一致する既存行を削除
key_cond = " AND ".join(f"existing.{c} = new.{c}" for c in key_columns)
conn.execute(f"""
    DELETE FROM {table_name} existing
    WHERE EXISTS (
        SELECT 1 FROM df new
        WHERE {key_cond}
    )
""")

# Step 2: 新しい行を全て挿入
conn.execute(f"INSERT INTO {table_name} SELECT * FROM df")
```

> **参照**: `src/database/db/duckdb_client.py` lines 279-292 -- DuckDB upsert パターンの実装

### 4.2 `store_df()` の 3つのモード

| モード | 動作 | 用途 |
|--------|------|------|
| `replace` | `CREATE OR REPLACE TABLE` | テーブル全体を最新データで置換 |
| `append` | `INSERT INTO ... SELECT *` | 既存データに追記（重複チェックなし） |
| `upsert` | DELETE + INSERT（キーベース） | べき等な更新（推奨） |

### 4.3 upsert の使用例

```python
from database.db import DuckDBClient, get_db_path

client = DuckDBClient(get_db_path("duckdb", "analytics"))

# 単一キーの upsert（企業マスタ）
client.store_df(
    df,
    "companies",
    if_exists="upsert",
    key_columns=["edinet_code"],
)

# 複合キーの upsert（財務データ）
client.store_df(
    df,
    "financials",
    if_exists="upsert",
    key_columns=["edinet_code", "fiscal_year"],
)

# 複合キーの upsert（株価データ）
client.store_df(
    df,
    "prices",
    if_exists="upsert",
    key_columns=["date", "ticker"],
)
```

> **参照**: `src/database/db/duckdb_client.py` lines 224-226 -- `store_df()` のシグネチャと使用例
> **参照**: `src/market/edinet/storage.py` lines 237-243 -- 単一キー upsert（`["edinet_code"]`）
> **参照**: `src/market/edinet/storage.py` lines 257-261 -- 複合キー upsert（`["edinet_code", "fiscal_year"]`）

### 4.4 upsert 使用時の必須バリデーション

```python
# key_columns が空の場合は ValueError
if if_exists == "upsert" and not key_columns:
    raise ValueError(
        "key_columns must be provided and non-empty for if_exists='upsert'"
    )

# SQL 識別子のバリデーション（SQLインジェクション防止）
_IDENTIFIER_RE = re.compile(r"^[a-zA-Z_][a-zA-Z0-9_]*$")

def _validate_identifier(name: str) -> None:
    if not _IDENTIFIER_RE.match(name):
        raise ValueError(
            f"Invalid identifier: {name!r}. Must match ^[a-zA-Z_][a-zA-Z0-9_]*$"
        )
```

> **参照**: `src/database/db/duckdb_client.py` lines 14-15 -- 識別子バリデーション正規表現
> **参照**: `src/database/db/duckdb_client.py` lines 234-237 -- upsert 時の key_columns 必須チェック

### 4.5 テーブル自動作成

テーブルが存在しない場合、`store_df()` は `CREATE TABLE AS SELECT * FROM df` で自動作成する。
明示的な DDL 定義がなくても、DataFrame のスキーマから自動推論される。

```python
# テーブルが存在しない場合: 自動作成
if not table_exists:
    conn.execute(f"CREATE TABLE {table_name} AS SELECT * FROM df")
```

> **参照**: `src/database/db/duckdb_client.py` lines 251-258 -- テーブル不在時の自動作成

---

## ルール 5: マイグレーション管理規約

### 5.1 命名規則

```
YYYYMMDD_HHMMSS_description.sql
```

| 要素 | 形式 | 例 |
|------|------|-----|
| 日付 | `YYYYMMDD` | `20250111` |
| 時刻 | `HHMMSS` | `000000` |
| 説明 | `snake_case` | `initial_schema` |

### 5.2 マイグレーションファイルの配置

```
src/database/db/migrations/
├── runner.py           # マイグレーション実行エンジン
└── versions/           # マイグレーションファイル（時系列順）
    └── 20250111_000000_initial_schema.sql
```

### 5.3 マイグレーション管理テーブル（SQLite）

```sql
-- schema_migrations: 適用済みマイグレーションを追跡
CREATE TABLE IF NOT EXISTS schema_migrations (
    filename TEXT PRIMARY KEY,
    applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

> **参照**: `src/database/db/migrations/runner.py` lines 14-21 -- `schema_migrations` テーブルの作成

### 5.4 マイグレーション実行フロー

```python
# 1. 適用済みマイグレーションを取得
applied = _get_applied_migrations(conn)
# → {"20250111_000000_initial_schema.sql"}

# 2. 未適用のマイグレーションをファイル名順で実行
for migration_file in sorted(MIGRATIONS_DIR.glob("*.sql")):
    if migration_file.name not in applied:
        sql = migration_file.read_text()
        conn.executescript(sql)
        conn.execute(
            "INSERT INTO schema_migrations (filename) VALUES (?)",
            (migration_file.name,),
        )
```

### 5.5 マイグレーション作成のガイドライン

| ガイドライン | 説明 |
|-------------|------|
| 1ファイル1操作 | 1つのマイグレーションで1つの変更のみ |
| べき等性 | `CREATE TABLE IF NOT EXISTS` / `CREATE INDEX IF NOT EXISTS` を使用 |
| ロールバック不要 | 前方のみ。問題があれば新しいマイグレーションで修正 |
| 命名は内容を表す | `add_sector_column` / `create_indicators_table` 等 |

### 5.6 SQLite DDL パターン: インデックス定義

```sql
-- 単一カラムインデックス
CREATE INDEX IF NOT EXISTS idx_assets_symbol ON assets(symbol);
CREATE INDEX IF NOT EXISTS idx_assets_type ON assets(asset_type);

-- 複合カラムインデックス（頻繁な WHERE 条件に対応）
CREATE INDEX IF NOT EXISTS idx_prices_symbol_date ON prices_daily(symbol, date);
```

> **参照**: `src/database/db/migrations/versions/20250111_000000_initial_schema.sql` lines 61-73 -- インデックス定義例

---

## ルール 6: DDL 定義パターン（DuckDB）

### 6.1 辞書管理パターン

テーブル DDL を Python 辞書で一元管理し、`ensure_tables()` で一括作成する。

```python
# テーブル名を定数として定義
TABLE_COMPANIES = "companies"
TABLE_FINANCIALS = "financials"
TABLE_RATIOS = "ratios"

# DDL を辞書で一元管理
_TABLE_DDL: dict[str, str] = {
    TABLE_COMPANIES: f"""
        CREATE TABLE IF NOT EXISTS {TABLE_COMPANIES} (
            edinet_code VARCHAR NOT NULL,
            sec_code VARCHAR NOT NULL,
            corp_name VARCHAR NOT NULL,
            industry_code VARCHAR NOT NULL,
            industry_name VARCHAR NOT NULL,
            listing_status VARCHAR NOT NULL
        )
    """,
    TABLE_FINANCIALS: f"""
        CREATE TABLE IF NOT EXISTS {TABLE_FINANCIALS} (
            edinet_code VARCHAR NOT NULL,
            fiscal_year VARCHAR NOT NULL,
            period_type VARCHAR NOT NULL,
            revenue BIGINT NOT NULL,
            operating_income BIGINT NOT NULL,
            -- 他のカラムは参照先を参照
        )
    """,
}
```

> **参照**: `src/market/edinet/storage.py` lines 73-170 -- 8テーブルの完全な DDL 辞書定義（全カラム含む）

### 6.2 一括テーブル作成

```python
class EdinetStorage:
    def ensure_tables(self) -> None:
        """Create all tables if they do not already exist."""
        for table_name, ddl in _TABLE_DDL.items():
            self._client.execute(ddl)
            logger.debug("Table ensured", table_name=table_name)
        logger.info(
            "All tables ensured",
            table_count=len(_TABLE_DDL),
        )
```

> **参照**: `src/market/edinet/storage.py` lines 206-219 -- `ensure_tables()` による一括作成

### 6.3 Dataclass → DataFrame → DuckDB の変換フロー

```python
# 1. Dataclass リストを DataFrame に変換
df = pd.DataFrame([dataclasses.asdict(c) for c in companies])

# 2. DataFrame を DuckDB に upsert
self._client.store_df(
    df,
    TABLE_COMPANIES,
    if_exists="upsert",
    key_columns=["edinet_code"],
)
```

> **参照**: `src/market/edinet/storage.py` lines 236-242 -- Dataclass → DataFrame → upsert の流れ

### 6.4 SQLite DDL パターン: FOREIGN KEY と UNIQUE

```sql
-- UNIQUE 制約 + FOREIGN KEY
CREATE TABLE IF NOT EXISTS prices_daily (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    symbol TEXT NOT NULL,
    date DATE NOT NULL,
    open REAL,
    high REAL,
    low REAL,
    close REAL,
    adj_close REAL,
    volume INTEGER,
    source TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(symbol, date, source),
    FOREIGN KEY (symbol) REFERENCES assets(symbol)
);
```

> **参照**: `src/database/db/migrations/versions/20250111_000000_initial_schema.sql` lines 19-33 -- UNIQUE 制約と FOREIGN KEY の組み合わせ

### 6.5 DuckDB vs SQLite DDL の違い

| 機能 | SQLite | DuckDB |
|------|--------|--------|
| 自動インクリメント | `INTEGER PRIMARY KEY AUTOINCREMENT` | `INTEGER PRIMARY KEY`（自動） |
| テキスト型 | `TEXT` | `VARCHAR` |
| 浮動小数点 | `REAL` | `DOUBLE` |
| 整数 | `INTEGER` | `INTEGER` / `BIGINT` |
| FOREIGN KEY | サポート（`PRAGMA foreign_keys = ON` が必要） | サポート |
| `CREATE OR REPLACE` | 非サポート | サポート |
| `IF NOT EXISTS` | サポート | サポート |

---

## まとめ: DB スキーマ設計チェックリスト

実装時に以下を確認:

- [ ] データ量とクエリパターンに基づいて SQLite / DuckDB を選択しているか
- [ ] DuckDB テーブルの型は適切か（金額 → `BIGINT`、比率 → `DOUBLE`、テキスト → `VARCHAR`）
- [ ] MultiIndex は `reset_index()` でフラット化してから保存しているか
- [ ] upsert 時に適切な `key_columns` を指定しているか
- [ ] upsert のキーカラムが SQL 識別子として有効か（`^[a-zA-Z_][a-zA-Z0-9_]*$`）
- [ ] マイグレーションファイル名が `YYYYMMDD_HHMMSS_description.sql` 形式か
- [ ] DDL に `CREATE TABLE IF NOT EXISTS` を使用しているか（べき等性）
- [ ] テーブル名を定数として定義し、DDL 辞書で一元管理しているか
- [ ] 頻繁にクエリされるカラムにインデックスを作成しているか
