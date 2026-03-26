# 議論メモ: ハードコードデータパス → .env DATA_DIR ベース統一リファクタリング

**日付**: 2026-03-25
**議論ID**: disc-2026-03-25-data-dir-env-migration

## 背景・コンテキスト

各パッケージが `Path("data/raw/xxx/")` のようにデータ保存先をハードコードしており、`.env` の `DATA_DIR` 環境変数が反映されなかった。NASDAQ パッケージのみ先行して `get_data_dir()` + `DEFAULT_OUTPUT_SUBDIR` パターンを導入済みだった。

## 決定事項

| ID | 内容 | コンテキスト |
|----|------|------------|
| dec-2026-03-25-001 | `get_data_dir()` を全パッケージのデータパス解決の唯一のエントリポイントとする | `__file__` ベースや `Path("data/...")` のハードコードを廃止 |
| dec-2026-03-25-002 | constants ファイルでは `DEFAULT_OUTPUT_SUBDIR`（DATA_DIR 相対パス）を定数として定義し、使用箇所で `get_data_dir() / DEFAULT_OUTPUT_SUBDIR` として組み立てる | 定数ファイルにランタイム依存を持ち込まない |
| dec-2026-03-25-003 | fred モジュールのパス解決を 3段階 → 2段階に簡素化 | `get_data_dir()` が内部で CWD 解決を行うため冗長だった |

## 変更ファイル一覧

### ASEAN 7取引所 constants + テスト（14ファイル）
- `DEFAULT_OUTPUT_DIR = "data/raw/xxx/"` → `DEFAULT_OUTPUT_SUBDIR = "raw/xxx"`
- idx, sgx, set_exchange, hose, pse, bse, bursa

### edinet_api / etfcom（4ファイル）
- `DEFAULT_OUTPUT_DIR` → `DEFAULT_OUTPUT_SUBDIR`
- `DEFAULT_TICKER_CACHE_DIR` → `DEFAULT_TICKER_CACHE_SUBDIR`

### industry モジュール（6ファイル）
- collector, config, bls, census, consulting, investment_bank で `get_data_dir()` を使用

### edgar / academic（2ファイル）
- `DEFAULT_CACHE_DIR`, `ACADEMIC_CACHE_DB_PATH` を `get_data_dir()` ベースに

### fred（2ファイル）
- `__file__` ベースのフォールバックを `get_data_dir()` に統一
- 3段階 → 2段階優先度に簡素化

### embedding / news / schema（4ファイル）
- dataclass / Pydantic Field のデフォルト値を `get_data_dir()` ベースに

## テスト結果

- 2450 passed, 1 failed（既存の FRED API キーテスト問題、変更とは無関係）
- pyright: 0 errors
- ruff: All checks passed

## パターンリファレンス

### constants ファイル（型注釈のみ）
```python
DEFAULT_OUTPUT_SUBDIR: Final[str] = "raw/nasdaq"
```

### collector / config ファイル（ランタイム使用）
```python
from database.db.connection import get_data_dir
DEFAULT_CACHE_DIR: Path = get_data_dir() / "raw" / "industry_reports" / "bls"
```

### 使用箇所
```python
output_dir = get_data_dir() / DEFAULT_OUTPUT_SUBDIR
```
