# タスク 01: settings.py に _find_env_file() 関数を追加

- **Issue**: [#2840](https://github.com/YH-05/quants/issues/2840)
- **ステータス**: todo

## 概要

`src/utils_core/settings.py` に `.env` ファイルを探索する `_find_env_file()` 関数を追加する。

## 対象ファイル

- `src/utils_core/settings.py`

## 実装内容

以下の関数を追加:

```python
def _find_env_file() -> Path | None:
    """Find .env file in order of priority.

    Search order:
    1. DOTENV_PATH environment variable
    2. Current working directory
    3. Parent directories (up to 5 levels)
    """
    # 1. 環境変数で明示的に指定されたパス
    env_path = os.environ.get("DOTENV_PATH")
    if env_path:
        path = Path(env_path)
        if path.exists():
            return path

    # 2. カレントディレクトリ
    cwd_env = Path.cwd() / ".env"
    if cwd_env.exists():
        return cwd_env

    # 3. 親ディレクトリを遡って探索（最大5レベル）
    current = Path.cwd()
    for _ in range(5):
        env_file = current / ".env"
        if env_file.exists():
            return env_file
        parent = current.parent
        if parent == current:
            break
        current = parent

    return None
```

## 受け入れ条件

- [ ] `_find_env_file()` 関数が追加されている
- [ ] DOTENV_PATH 環境変数による明示指定が動作する
- [ ] カレントディレクトリの .env が検出される
- [ ] 親ディレクトリの .env が検出される（最大5レベル）
- [ ] .env が見つからない場合は None を返す
- [ ] 単体テストが追加されている
- [ ] `make check-all` が成功する

## 依存関係

- depends_on: なし（最初のタスク）
- blocks: [#2841](https://github.com/YH-05/quants/issues/2841)

## 見積もり

1時間
