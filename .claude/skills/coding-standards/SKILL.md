---
name: coding-standards
description: Python コーディング規約のナレッジベース。型ヒント（PEP 695）、命名規則、NumPy形式Docstring、エラーメッセージ、ロギングの実装パターンを提供。コード実装時にプロアクティブに使用。
allowed-tools: Read
---

# Python コーディング規約スキル

Python 3.12+ のコーディング規約を提供するナレッジベーススキルです。

## 目的

このスキルは以下を提供します：

- **型ヒント**: PEP 695 準拠の最新構文
- **命名規則**: 変数・関数・クラス・定数の命名パターン
- **Docstring**: NumPy 形式の標準テンプレート
- **エラーメッセージ**: 具体的で解決策を示すパターン
- **ロギング**: 構造化ログの実装パターン

## いつ使用するか

### プロアクティブ使用（自動で検討）

以下の状況では、ユーザーが明示的に要求しなくても参照：

1. **Python コード実装時**
   - 新しい関数・クラスの作成
   - 型ヒントの記述
   - エラーハンドリングの実装

2. **コードレビュー時**
   - 命名規則の確認
   - Docstring の形式確認
   - 型ヒントの構文確認

3. **リファクタリング時**
   - コードの可読性向上
   - 型ヒントの最新化（PEP 695 移行）

## クイックリファレンス

### 型ヒント（PEP 695）

```python
# 組み込み型を直接使用
def process_items(items: list[str]) -> dict[str, int]:
    return {item: items.count(item) for item in set(items)}

# ジェネリック関数（PEP 695 新構文）
def first[T](items: list[T]) -> T | None:
    return items[0] if items else None

# ジェネリッククラス
class Stack[T]:
    def __init__(self) -> None:
        self._items: list[T] = []

# ParamSpec（デコレータ用）
def logged[**P, R](func: Callable[P, R]) -> Callable[P, R]:
    def wrapper(*args: P.args, **kwargs: P.kwargs) -> R:
        return func(*args, **kwargs)
    return wrapper

# 境界付き型パラメータ
def unique[T: Hashable](items: list[T]) -> set[T]:
    return set(items)
```

### 命名規則

| 対象 | 規則 | 例 |
|------|------|-----|
| 変数 | snake_case、名詞 | `user_name`, `task_list` |
| Boolean | is_, has_, should_, can_ | `is_valid`, `has_permission` |
| 関数 | snake_case、動詞 | `fetch_data()`, `validate_email()` |
| クラス | PascalCase、名詞 | `TaskManager`, `UserService` |
| 定数 | UPPER_SNAKE | `MAX_RETRY`, `API_BASE_URL` |
| ファイル | snake_case.py | `task_service.py` |
| プライベート | _prefix | `_internal_method()` |

### Docstring（NumPy 形式）

```python
def process_items(
    items: list[dict[str, Any]],
    max_count: int = 100,
) -> list[dict[str, Any]]:
    """Process a list of items with validation.

    Parameters
    ----------
    items : list[dict[str, Any]]
        List of items to process
    max_count : int, default=100
        Maximum number of items

    Returns
    -------
    list[dict[str, Any]]
        Processed items

    Raises
    ------
    ValueError
        If items is empty

    Examples
    --------
    >>> result = process_items([{"id": 1}])
    >>> len(result)
    1
    """
```

### エラーメッセージ

```python
# 具体的な値を含める
raise ValueError(f"Expected positive integer, got {count}")

# 解決策を示す
raise FileNotFoundError(
    f"Config not found at {path}. Create by: python -m {__package__}.init"
)

# コンテキストを保持
raise ProcessingError(f"Failed to process {source}: {e}") from e
```

### ロギング

```python
from utils_core.logging import get_logger

logger = get_logger(__name__)

def process_data(data: list) -> list:
    logger.debug("Processing started", item_count=len(data))
    try:
        result = transform(data)
        logger.info("Processing completed", output_count=len(result))
        return result
    except Exception as e:
        logger.error("Processing failed", error=str(e), exc_info=True)
        raise
```

### アンカーコメント

```python
# AIDEV-NOTE: 実装の意図や背景
# AIDEV-TODO: 未完了タスク
# AIDEV-QUESTION: 確認が必要な疑問点
```

## リソース

このスキルには以下のリソースが含まれています：

### ./guide.md

詳細なコーディング規約ガイド：

- 型ヒントの詳細（dataclass vs TypedDict、Protocol）
- 関数設計（単一責務、パラメータ数）
- エラーハンドリング（カスタム例外、ラッピング）
- 非同期処理（async/await、並列処理）
- セキュリティ（入力検証、機密情報管理）
- パフォーマンス（データ構造選択、メモ化）

### ./examples/type-hints.md

PEP 695 型ヒントの詳細例：

- ジェネリック関数・クラス
- ParamSpec、TypeVarTuple
- 境界付き型パラメータ
- 型エイリアス

### ./examples/docstrings.md

NumPy 形式 Docstring の詳細例：

- 各セクションの書き方
- 複雑な型の記述
- Examples セクションのベストプラクティス

### ./examples/error-messages.md

エラーメッセージパターン集：

- カスタム例外クラス
- エラーチェーン
- ユーザーフレンドリーなメッセージ

### ./examples/naming.md

命名規則の詳細例：

- 変数・関数・クラスの命名パターン
- Boolean 命名
- 略語の扱い

### ./examples/logging.md

ロギング実装パターン：

- 構造化ログ
- ログレベルの使い分け
- コンテキスト情報の付加

## 使用例

### 例1: 新しい関数の実装

**状況**: データ処理関数を新規作成

**処理**:
1. 命名規則を確認（snake_case、動詞で開始）
2. 型ヒントを PEP 695 構文で記述
3. NumPy 形式の Docstring を追加
4. ロギングを実装
5. エラーメッセージを具体的に記述

**期待される出力**:
```python
from utils_core.logging import get_logger

logger = get_logger(__name__)

def fetch_market_data(
    symbols: list[str],
    start_date: datetime,
    end_date: datetime | None = None,
) -> dict[str, DataFrame]:
    """Fetch market data for specified symbols.

    Parameters
    ----------
    symbols : list[str]
        List of ticker symbols
    start_date : datetime
        Start date for data range
    end_date : datetime | None, default=None
        End date (defaults to today)

    Returns
    -------
    dict[str, DataFrame]
        Market data keyed by symbol

    Raises
    ------
    ValueError
        If symbols is empty
    """
    if not symbols:
        raise ValueError("symbols must not be empty")

    logger.info("Fetching market data", symbols=symbols)
    # implementation
```

---

### 例2: ジェネリッククラスの作成

**状況**: 型安全なキャッシュクラスを作成

**処理**:
1. PEP 695 のジェネリック構文を使用
2. 型パラメータに適切な境界を設定

**期待される出力**:
```python
from collections.abc import Hashable

class Cache[K: Hashable, V]:
    """Thread-safe cache with TTL support."""

    def __init__(self, max_size: int = 100) -> None:
        self._data: dict[K, V] = {}
        self._max_size = max_size

    def get(self, key: K) -> V | None:
        return self._data.get(key)

    def set(self, key: K, value: V) -> None:
        self._data[key] = value
```

---

### 例3: カスタム例外の作成

**状況**: ドメイン固有のエラーを定義

**処理**:
1. 基底クラスから継承
2. コンテキスト情報を保持
3. 具体的なメッセージを生成

**期待される出力**:
```python
class MarketDataError(Exception):
    """Base exception for market data operations."""

    def __init__(self, message: str, symbol: str | None = None) -> None:
        super().__init__(message)
        self.symbol = symbol


class SymbolNotFoundError(MarketDataError):
    """Raised when a symbol is not found."""

    def __init__(self, symbol: str) -> None:
        super().__init__(
            f"Symbol not found: {symbol}. Check if it's a valid ticker.",
            symbol=symbol,
        )
```

---

### 例4: 構造化ロギングの実装

**状況**: 処理の追跡可能性を向上

**処理**:
1. get_logger でロガーを取得
2. 適切なログレベルを選択
3. 構造化データをキーワード引数で渡す

**期待される出力**:
```python
from utils_core.logging import get_logger

logger = get_logger(__name__)

async def process_order(order: Order) -> ProcessedOrder:
    logger.info(
        "Order processing started",
        order_id=order.id,
        user_id=order.user_id,
    )

    try:
        result = await execute_order(order)
        logger.info(
            "Order processed successfully",
            order_id=order.id,
            execution_time_ms=result.execution_time,
        )
        return result
    except Exception as e:
        logger.error(
            "Order processing failed",
            order_id=order.id,
            error=str(e),
            exc_info=True,
        )
        raise
```

## 品質基準

### 必須（MUST）

- [ ] 全ての関数・メソッドに型ヒントがある
- [ ] 公開 API に NumPy 形式の Docstring がある
- [ ] 命名規則に従っている
- [ ] エラーメッセージが具体的で解決策を示す
- [ ] 適切なログレベルでロギングされている

### 推奨（SHOULD）

- PEP 695 の新構文を使用（Python 3.12+）
- カスタム例外でコンテキストを保持
- 構造化ログでキーワード引数を使用
- アンカーコメントで意図を説明

## 関連スキル

- **development-guidelines**: 開発プロセス全般
- **tdd-development**: TDD 開発プロセス（後続 Issue で作成予定）

## 参考資料

- `CLAUDE.md`: プロジェクトガイドライン
- `.claude/rules/coding-standards.md`: ルールファイル
- `template/src/template_package/`: 実装テンプレート
