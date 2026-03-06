# market.factset

FactSet からダウンロード済みの財務・価格データを処理するユーティリティモジュール。
API リアルタイム連携ではなく、FactSet の Excel アドインや Workstation からエクスポートしたファイルを
SQLite / Parquet に変換・蓄積するパイプラインを提供する。

## モジュール構成

```
market/factset/
    factset_downloaded_data_utils.py  # ダウンロード済みデータ用 SQLite 書き込みユーティリティ
    factset_utils.py                  # Excel 整形・コード統合・DB 書き込み・アクティブリターン保存
    price.py                          # FG_PRICE テーブルの読み込み
    README.md                         # このファイル
```

---

## クイックスタート

### 価格データの読み込み

```python
from pathlib import Path
from market.factset.price import load_fg_price

db_path = Path("data/factset.db")

# 全期間・全銘柄
df = load_fg_price(db_path)

# 期間・銘柄を絞り込み
df = load_fg_price(
    db_path,
    start_date="2023-01-01",
    end_date="2024-12-31",
    p_symbol_list=["AAPL-US", "MSFT-US"],
)
# 戻り値: date をインデックスとした DataFrame
# columns: P_SYMBOL, FG_PRICE
```

### ダウンロード済み Excel を SQLite に格納

```python
from pathlib import Path
import pandas as pd
from market.factset.factset_downloaded_data_utils import store_to_database

db_path = Path("data/factset.db")
df = pd.read_csv("factset_export.csv")  # date, P_SYMBOL, variable, value 列を持つ DataFrame

store_to_database(
    df=df,
    db_path=db_path,
    table_name="FF_SALES",
    unique_cols=["date", "P_SYMBOL", "variable"],  # デフォルト値と同じ
)
```

### FactSet Excel を Parquet に変換

```python
from pathlib import Path
from market.factset.factset_utils import format_factset_downloaded_data

file_list = list(Path("downloads/").glob("Financials_*.xlsx"))
output_folder = Path("data/processed/factset/")
output_folder.mkdir(parents=True, exist_ok=True)

format_factset_downloaded_data(
    file_list=file_list,
    output_folder=output_folder,
    split_save_mode=False,  # True で既存ファイルに追記 + 年別分割保存
)
# 出力: Financials_and_Price-compressed-YYYYMMDD_YYYYMMDD.parquet
```

---

## 機能別リファレンス

### price.py - 価格データ読み込み

#### `load_fg_price`

SQLite の `FG_PRICE` テーブルからデータを読み込む。

```python
load_fg_price(
    db_path: Path,
    start_date: str | None = None,   # 例: "2024-01-01"
    end_date: str | None = None,
    p_symbol_list: list[str] | None = None,  # FactSet P_SYMBOL のリスト
) -> pd.DataFrame
```

- 戻り値は `date` インデックス、`P_SYMBOL` / `FG_PRICE` カラムの DataFrame
- フィルタはすべてオプション。省略した場合は全データを返す

---

### factset_downloaded_data_utils.py - SQLite 書き込みユーティリティ

#### `store_to_database`

DataFrame を SQLite テーブルに重複なく追記する。

```python
store_to_database(
    df: pd.DataFrame,
    db_path: Path,
    table_name: str,
    unique_cols: list[str] | None = None,  # デフォルト: ["date", "P_SYMBOL", "variable"]
    verbose: bool = False,
)
```

- テーブルが存在しない場合は自動作成
- `unique_cols` の組み合わせが既存データと重複する行はスキップ
- テーブル名・カラム名に対して SQL インジェクション検証を実施（CWE-89 対策）

#### `delete_table_from_database`

指定テーブルを SQLite から削除する。テーブルが存在しない場合もエラーにならない。

```python
delete_table_from_database(
    db_path: Path,
    table_name: str,
    verbose: bool = False,
)
```

---

### factset_utils.py - Excel 整形・統合ユーティリティ

#### `format_factset_downloaded_data`

FactSet の Excel ファイル（財務データ・価格データ）を縦持ち形式に変換して Parquet 保存する。

```python
format_factset_downloaded_data(
    file_list: list[Path | str],
    output_folder: Path,
    split_save_mode: bool = False,
)
```

- `split_save_mode=True`: 既存の `Financials_and_Price.parquet` に追記し、さらに3年刻みで分割保存
- `split_save_mode=False`: 全期間を1ファイルとして保存（`YYYYMMDD_YYYYMMDD` 形式のファイル名）
- 各シートを `(date, P_SYMBOL, value, variable)` の縦持ち形式に変換

#### `split_and_save_dataframe`

大きな DataFrame を均等に分割して Parquet で保存する。

```python
split_and_save_dataframe(
    df_all: pd.DataFrame,
    n_splits: int,
    base_dir: Path,
    base_filename: str,
    **kwargs,  # pd.to_parquet に渡す引数 (compression="zstd" など)
) -> list[Path]
```

#### `store_to_database`（factset_utils 版）

`factset_downloaded_data_utils` の同名関数の拡張版。重複時の動作（スキップ or 上書き）を選択できる。

```python
store_to_database(
    df: pd.DataFrame,
    db_path: Path,
    table_name: str,
    unique_cols: list[str] | None = None,
    verbose: bool = True,
    on_duplicate: str = "skip",  # "skip" または "update"
)
```

#### `store_to_database_batch`

複数テーブルをまとめて SQLite に書き込む。直列（推奨）または並列（WAL モード要）を選択できる。

```python
store_to_database_batch(
    df_dict: dict[str, pd.DataFrame],  # {table_name: DataFrame}
    db_path: Path,
    unique_cols: list[str] | None = None,
    batch_size: int = 10000,
    max_workers: int | None = 1,  # 1 = 直列（ロック回避）
    verbose: bool = True,
) -> dict[str, Any]
```

#### `store_active_returns_batch_serial_write` / `insert_active_returns_optimized_sqlite`

アクティブリターン（銘柄リターン - ベンチマークリターン）をテーブルごとに SQLite へ保存する高速関数。

```python
store_active_returns_batch_serial_write(
    df_active_returns: pd.DataFrame,  # Long 形式。symbol, date, variable, value 列が必要
    return_cols: list[str],           # 処理対象のリターン列名
    db_path: Path,
    benchmark_ticker: str,            # 除外するベンチマークの P_SYMBOL
    batch_size: int = 10000,
    verbose: bool = True,
) -> dict[str, Any]
```

- `store_active_returns_batch_serial_write`: 直列書き込みでロックを完全回避
- `insert_active_returns_optimized_sqlite`: `INSERT OR IGNORE` + `executemany` による高速版

#### `upsert_financial_data`

財務データを UPSERT（挿入または更新）する。SQLite バージョンに応じて方式を自動選択。

```python
upsert_financial_data(
    df: pd.DataFrame,
    conn: sqlite3.Connection,
    table_name: str,
    method: str = "auto",  # "auto" / "upsert"（SQLite 3.24+）/ "delete_insert"
)
```

#### `enable_wal_mode`

SQLite の WAL（Write-Ahead Logging）モードを有効化する。並列書き込み時のパフォーマンス向上に使用。

```python
enable_wal_mode(db_path: Path, verbose: bool = True)
```

#### BPM 連携ユーティリティ（社内データ基盤向け）

| 関数名 | 説明 |
|--------|------|
| `load_bpm_and_export_factset_code_file` | BPM からダウンロードしたインデックス構成銘柄を統合し、FactSet コード取得用 Excel を出力 |
| `unify_factset_code_data` | FactSet からダウンロードした P_SYMBOL / FG_COMPANY_NAME を SEDOL / CUSIP / ISIN / CODE_JP に紐付けて統合 |
| `create_factset_symbol_list_function` | FactSet FQL 埋め込み用のシンボルリスト文字列を生成 |
| `factset_formula` | FactSet GET_FQL_ARRAY 関数の Excel 数式文字列を生成 |
| `implement_factset_formulas` | Universe の財務データ取得用 Excel ファイルを一括生成 |

---

## データ形式

### SQLite テーブルの標準スキーマ

```
date      TEXT    # 例: "2024-01-31"
P_SYMBOL  TEXT    # FactSet 固有の銘柄識別子（例: "AAPL-US"）
variable  TEXT    # データ項目名（例: "FF_SALES", "FG_PRICE"）
value     REAL    # 数値
PRIMARY KEY (date, P_SYMBOL, variable)
```

### Parquet の縦持ち形式

FactSet から Excel でダウンロードしたデータは横持ち（シンボルが列）のため、
`format_factset_downloaded_data` が縦持ち形式に変換する。

```
date        P_SYMBOL   value      variable
2024-01-31  AAPL-US    123456.7   FF_SALES
2024-01-31  MSFT-US    211234.5   FF_SALES
2024-04-30  AAPL-US    135678.9   FF_SALES
```

---

## セキュリティ

テーブル名・カラム名のパラメータ化が SQLite では不可能なため、全関数で `_validate_sql_identifier` による検証を実施している（CWE-89 対策）。

- 使用可能文字: 英字またはアンダースコアで始まり、英数字・アンダースコアのみ（`factset_utils.py` ではハイフン・ドットも許容）
- SQL キーワード（`SELECT`, `DROP` 等）はテーブル名・カラム名として使用不可
- 検証に失敗した場合は `ValueError` を送出

---

## 環境変数

BPM 連携ユーティリティは以下の環境変数を使用する。

| 変数名 | 説明 |
|--------|------|
| `FACTSET_ROOT_DIR` | FactSet ダウンロードデータのルートディレクトリ |
| `FACTSET_FINANCIALS_DIR` | 財務データの出力先ディレクトリ |
| `BPM_DATA_DIR` | BPM データのディレクトリ |
| `BPM_SRC_DIR` | BPM ソースファイルのディレクトリ |
| `SRC_DIR` | ソースコードディレクトリ（YAML マップファイルを含む） |

---

## 関連モジュール

- [market.yfinance](../yfinance/README.md) - Yahoo Finance からのリアルタイム価格取得
- [market.fred](../fred/README.md) - FRED 経済指標データ取得
- [database](../../database/README.md) - SQLite / DuckDB 共通インフラ
