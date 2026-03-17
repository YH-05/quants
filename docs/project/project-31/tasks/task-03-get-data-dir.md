# タスク 03: connection.py に get_data_dir() 関数を追加

- **Issue**: [#2842](https://github.com/YH-05/quants/issues/2842)
- **ステータス**: todo

## 概要

`src/database/db/connection.py` に `get_data_dir()` 関数を追加し、データディレクトリのパスを環境変数またはカレントディレクトリから取得できるようにする。

## 対象ファイル

- `src/database/db/connection.py`

## 実装内容

以下の関数を追加:

```python
def get_data_dir() -> Path:
    """Get the data directory path.

    Priority:
    1. DATA_DIR environment variable
    2. ./data (relative to cwd)
    3. Fallback: __file__ based path (for backward compatibility)
    """
    # 1. 環境変数
    env_path = os.environ.get("DATA_DIR")
    if env_path:
        return Path(env_path)

    # 2. カレントディレクトリからの相対パス
    cwd_path = Path.cwd() / "data"
    if cwd_path.exists():
        return cwd_path

    # 3. フォールバック（後方互換性）
    return Path(__file__).parent.parent.parent.parent / "data"
```

既存の定数に非推奨コメントを追加:

```python
# 後方互換性のため定数も残す（非推奨）
PROJECT_ROOT = Path(__file__).parent.parent.parent.parent  # 非推奨
DATA_DIR = PROJECT_ROOT / "data"  # 非推奨
```

## 受け入れ条件

- [ ] `get_data_dir()` 関数が追加されている
- [ ] DATA_DIR 環境変数による明示指定が動作する
- [ ] カレントディレクトリからの相対パスが動作する
- [ ] フォールバックとして __file__ ベースのパスが使用される
- [ ] PROJECT_ROOT、DATA_DIR に非推奨コメントが追加されている
- [ ] 単体テストが追加されている
- [ ] `make check-all` が成功する

## 依存関係

- depends_on: [#2841](https://github.com/YH-05/quants/issues/2841)
- blocks: [#2845](https://github.com/YH-05/quants/issues/2845)

## 見積もり

1時間
