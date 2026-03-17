# タスク 05: fetcher.py に _get_default_presets_path() 関数を追加

- **Issue**: [#2844](https://github.com/YH-05/quants/issues/2844)
- **ステータス**: todo

## 概要

`src/market/fred/fetcher.py` に `_get_default_presets_path()` 関数を追加し、FRED シリーズ設定ファイルのパスをカレントディレクトリから取得できるようにする。

## 対象ファイル

- `src/market/fred/fetcher.py`

## 実装内容

以下の関数を追加:

```python
def _get_default_presets_path() -> Path:
    """Get the default presets path for FRED series.

    Priority:
    1. FRED_SERIES_ID_JSON environment variable
    2. ./data/config/fred_series.json (relative to cwd)
    3. Fallback: __file__ based path (for backward compatibility)
    """
    # 1. 環境変数
    env_path = os.environ.get("FRED_SERIES_ID_JSON")
    if env_path:
        return Path(env_path)

    # 2. カレントディレクトリからの相対パス
    cwd_path = Path.cwd() / "data" / "config" / "fred_series.json"
    if cwd_path.exists():
        return cwd_path

    # 3. フォールバック（後方互換性）
    return Path(__file__).parents[3] / "data" / "config" / "fred_series.json"
```

既存の `DEFAULT_PRESETS_PATH` 定数を非推奨化または削除し、関数呼び出しに置き換える。

## 受け入れ条件

- [ ] `_get_default_presets_path()` 関数が追加されている
- [ ] FRED_SERIES_ID_JSON 環境変数が優先される
- [ ] カレントディレクトリからの相対パスが次に優先される
- [ ] フォールバックとして __file__ ベースのパスが使用される
- [ ] `DEFAULT_PRESETS_PATH` の使用箇所が関数呼び出しに置き換わっている
- [ ] 既存のテストが通過する
- [ ] `make check-all` が成功する

## 依存関係

- depends_on: [#2841](https://github.com/YH-05/quants/issues/2841)
- blocks: [#2845](https://github.com/YH-05/quants/issues/2845)

## 見積もり

30分
