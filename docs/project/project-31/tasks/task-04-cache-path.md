# タスク 04: historical_cache.py の get_default_cache_path() を修正

- **Issue**: [#2843](https://github.com/YH-05/quants/issues/2843)
- **ステータス**: todo

## 概要

`src/market/fred/historical_cache.py` の `get_default_cache_path()` 関数を修正し、カレントディレクトリからの相対パスを優先するようにする。

## 対象ファイル

- `src/market/fred/historical_cache.py`

## 実装内容

既存の `get_default_cache_path()` を以下のように修正:

```python
def get_default_cache_path() -> Path:
    """Get the default cache path for FRED historical data.

    Priority:
    1. FRED_HISTORICAL_CACHE_DIR environment variable
    2. ./data/raw/fred/indicators (relative to cwd)
    3. Fallback: __file__ based path (for backward compatibility)
    """
    load_project_env()

    # 1. 環境変数
    env_path = os.environ.get(FRED_HISTORICAL_CACHE_DIR_ENV)
    if env_path:
        return Path(env_path)

    # 2. カレントディレクトリからの相対パス
    cwd_path = Path.cwd() / "data" / "raw" / "fred" / "indicators"
    if cwd_path.exists() or cwd_path.parent.exists():
        return cwd_path

    # 3. フォールバック（後方互換性）
    return Path(__file__).parents[3] / "data" / "raw" / "fred" / "indicators"
```

また、モジュールレベルの `_DEFAULT_CACHE_PATH` 定数を削除または非推奨化。

## 受け入れ条件

- [ ] `get_default_cache_path()` が修正されている
- [ ] FRED_HISTORICAL_CACHE_DIR 環境変数が優先される
- [ ] カレントディレクトリからの相対パスが次に優先される
- [ ] フォールバックとして __file__ ベースのパスが使用される
- [ ] `_DEFAULT_CACHE_PATH` が削除または非推奨化されている
- [ ] 既存のテストが通過する
- [ ] `make check-all` が成功する

## 依存関係

- depends_on: [#2841](https://github.com/YH-05/quants/issues/2841)
- blocks: [#2845](https://github.com/YH-05/quants/issues/2845)

## 見積もり

30分
