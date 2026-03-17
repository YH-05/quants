# タスク 02: settings.py の load_project_env() を修正

- **Issue**: [#2841](https://github.com/YH-05/quants/issues/2841)
- **ステータス**: todo

## 概要

`src/utils_core/settings.py` の `load_project_env()` 関数を修正し、`_find_env_file()` を使用するようにする。

## 対象ファイル

- `src/utils_core/settings.py`

## 実装内容

既存の `load_project_env()` を以下のように修正:

```python
def load_project_env(*, override: bool = False) -> bool:
    """Load environment variables from .env file.

    Parameters
    ----------
    override : bool
        If True, override existing environment variables.

    Returns
    -------
    bool
        True if .env file was found and loaded.
    """
    env_file = _find_env_file()
    if env_file:
        logger.debug("Loading .env file", path=str(env_file))
        return load_dotenv(dotenv_path=env_file, override=override)

    logger.debug("No .env file found")
    return False
```

また、既存の定数を非推奨化:

```python
# PROJECT_ROOT は非推奨化（後方互換性のため残す）
# WARNING: site-packages環境では正しく動作しない
PROJECT_ROOT: Path = Path(__file__).parent.parent.parent
ENV_FILE_PATH: Path = PROJECT_ROOT / ".env"  # 非推奨
```

## 受け入れ条件

- [ ] `load_project_env()` が `_find_env_file()` を使用している
- [ ] .env が見つかった場合は True を返す
- [ ] .env が見つからない場合は False を返す
- [ ] ログ出力が追加されている
- [ ] PROJECT_ROOT、ENV_FILE_PATH に非推奨コメントが追加されている
- [ ] 既存のテストが通過する
- [ ] `make check-all` が成功する

## 依存関係

- depends_on: [#2840](https://github.com/YH-05/quants/issues/2840)
- blocks: [#2842](https://github.com/YH-05/quants/issues/2842), [#2843](https://github.com/YH-05/quants/issues/2843), [#2844](https://github.com/YH-05/quants/issues/2844)

## 見積もり

30分
