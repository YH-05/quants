# Polymarket データ長期保存 実装計画

## Context

Polymarket APIクライアント（`src/market/polymarket/`）は完成済みだが、データは TTL ベースの SQLiteCache にのみ保存される。分析用途での長期保存ができないため、**SQLite** に永続保存する Storage 層と定期収集用の Collector を実装する。

**なぜ SQLite か**: NAS 上にデータベースを配置する要件があるため。DuckDB はメモリマップドファイルとファイルロックの制約でネットワークストレージとの互換性に問題がある。SQLite はネットワークストレージでも安定して動作する。

**保存対象**: 全16エンドポイントのデータ（イベント、マーケット、価格履歴、約定、OI、注文板スナップショット、リーダーボード、ホルダー）
**DB配置**: `get_db_path("sqlite", "polymarket")` → `DATA_DIR/sqlite/polymarket.db`
**参照実装**: `EdinetStorage`（`src/market/edinet/storage.py`）— SQLite + `INSERT OR REPLACE` パターン

---

## テーブル設計（8テーブル）

| テーブル | PK | 説明 |
|---------|-----|------|
| `pm_events` | `event_id` | イベントメタデータ（SCD） |
| `pm_markets` | `condition_id` | マーケットメタデータ（SCD） |
| `pm_tokens` | `token_id, condition_id` | トークン定義（マーケットの子） |
| `pm_price_history` | `token_id, timestamp, interval` | 価格時系列（append） |
| `pm_trades` | `trade_id` | 約定履歴（append） |
| `pm_oi_snapshots` | `condition_id, snapshot_at` | OI定期スナップショット |
| `pm_orderbook_snapshots` | `asset_id, snapshot_at` | 注文板スナップショット |
| `pm_leaderboard_snapshots` | `snapshot_at, rank` | リーダーボード定期スナップショット |

注: ホルダーデータは `pm_markets` の `holders_json` カラムに JSON 文字列として保持（専用テーブル不要）。

### DDL 概要

```sql
-- pm_events: イベントメタデータ
CREATE TABLE IF NOT EXISTS pm_events (
    event_id TEXT NOT NULL,
    title TEXT NOT NULL,
    slug TEXT NOT NULL,
    description TEXT,
    start_date TEXT,
    end_date TEXT,
    active INTEGER,
    closed INTEGER,
    volume REAL,
    liquidity REAL,
    collected_at TEXT NOT NULL,
    PRIMARY KEY (event_id)
);

-- pm_markets: マーケットメタデータ
CREATE TABLE IF NOT EXISTS pm_markets (
    condition_id TEXT NOT NULL,
    event_id TEXT,
    question TEXT NOT NULL,
    description TEXT,
    end_date_iso TEXT,
    active INTEGER,
    closed INTEGER,
    volume REAL,
    liquidity REAL,
    holders_json TEXT,
    collected_at TEXT NOT NULL,
    PRIMARY KEY (condition_id)
);

-- pm_tokens: トークン定義
CREATE TABLE IF NOT EXISTS pm_tokens (
    token_id TEXT NOT NULL,
    condition_id TEXT NOT NULL,
    outcome TEXT NOT NULL,
    price REAL,
    collected_at TEXT NOT NULL,
    PRIMARY KEY (token_id, condition_id)
);

-- pm_price_history: 価格時系列
CREATE TABLE IF NOT EXISTS pm_price_history (
    token_id TEXT NOT NULL,
    timestamp INTEGER NOT NULL,
    price REAL NOT NULL,
    interval TEXT NOT NULL,
    collected_at TEXT NOT NULL,
    PRIMARY KEY (token_id, timestamp, interval)
);

-- pm_trades: 約定履歴
CREATE TABLE IF NOT EXISTS pm_trades (
    trade_id TEXT NOT NULL,
    condition_id TEXT NOT NULL,
    asset_id TEXT NOT NULL,
    price REAL NOT NULL,
    size REAL NOT NULL,
    side TEXT,
    timestamp TEXT,
    collected_at TEXT NOT NULL,
    PRIMARY KEY (trade_id)
);

-- pm_oi_snapshots: OI スナップショット
CREATE TABLE IF NOT EXISTS pm_oi_snapshots (
    condition_id TEXT NOT NULL,
    snapshot_at TEXT NOT NULL,
    data_json TEXT NOT NULL,
    PRIMARY KEY (condition_id, snapshot_at)
);

-- pm_orderbook_snapshots: 注文板スナップショット
CREATE TABLE IF NOT EXISTS pm_orderbook_snapshots (
    asset_id TEXT NOT NULL,
    snapshot_at TEXT NOT NULL,
    bids_json TEXT NOT NULL,
    asks_json TEXT NOT NULL,
    PRIMARY KEY (asset_id, snapshot_at)
);

-- pm_leaderboard_snapshots: リーダーボード
CREATE TABLE IF NOT EXISTS pm_leaderboard_snapshots (
    snapshot_at TEXT NOT NULL,
    rank INTEGER NOT NULL,
    data_json TEXT NOT NULL,
    PRIMARY KEY (snapshot_at, rank)
);
```

SQLite型マッピング: TEXT（文字列）、REAL（浮動小数点）、INTEGER（整数/ブール）。
日時は ISO 8601 文字列（TEXT）で保存（EdinetStorage と同じ規約）。

---

## ファイル構成

### 新規作成ファイル

```
src/market/polymarket/
    storage_constants.py    # テーブル名定数、DB名
    storage.py              # PolymarketStorage クラス
    collector.py            # PolymarketCollector クラス

tests/market/polymarket/
    conftest.py             # SQLite fixture（tmp_path ベース）
    unit/
        test_storage.py         # Storage 単体テスト
        test_collector.py       # Collector 単体テスト
    property/
        test_storage_property.py  # upsert 冪等性のプロパティテスト
    integration/
        test_storage_integration.py  # 実API → Storage E2E
```

### 変更ファイル

```
src/market/polymarket/__init__.py  # Storage, Collector エクスポート追加
```

---

## クラス設計

### PolymarketStorage

`EdinetStorage`（`src/market/edinet/storage.py`）パターンを踏襲。
`INSERT OR REPLACE` による冪等 upsert、`SQLiteClient` 経由の全DB操作。

```
PolymarketStorage(client: SQLiteClient)
├── ensure_tables()                    # 全8テーブル作成
├── upsert_events(events)             # → pm_events + 子の pm_markets/pm_tokens も連鎖
├── upsert_markets(markets, event_id?) # → pm_markets + pm_tokens
├── upsert_price_history(token_id, prices, interval) # → pm_price_history
├── upsert_trades(trades)             # → pm_trades
├── insert_oi_snapshot(condition_id, data)        # → pm_oi_snapshots
├── insert_orderbook_snapshot(orderbook)          # → pm_orderbook_snapshots
├── insert_leaderboard_snapshot(entries)           # → pm_leaderboard_snapshots
├── upsert_holders(condition_id, holders)         # → pm_markets.holders_json
├── get_events(active_only?)          # クエリ → pd.DataFrame
├── get_markets(event_id?, active_only?)
├── get_tokens(condition_id)
├── get_price_history(token_id, interval?)
├── get_trades(condition_id, limit?)
├── get_oi_snapshots(condition_id)
├── count_records()                   # テーブル別レコード数
└── get_collection_summary()          # 収集状況サマリ
```

**upsert パターン**（EdinetStorage 準拠）:
```python
# _build_insert_sql() でテーブル名+カラム名から SQL 生成
sql = "INSERT OR REPLACE INTO pm_events (event_id, title, ...) VALUES (?, ?, ...)"
# Pydantic model_dump() → tuple 変換 → executemany()
with self._client.connection() as conn:
    conn.executemany(sql, rows)
```

**クエリパターン**:
```python
def get_events(self, active_only: bool = False) -> pd.DataFrame:
    sql = "SELECT * FROM pm_events"
    if active_only:
        sql += " WHERE active = 1"
    rows = self._client.execute(sql)
    return pd.DataFrame([dict(row) for row in rows])
```

**ファクトリ関数**:
```python
def get_polymarket_storage(db_path: Path | None = None) -> PolymarketStorage:
    if db_path is None:
        db_path = get_db_path("sqlite", "polymarket")
    client = SQLiteClient(db_path)
    return PolymarketStorage(client=client)
```

### PolymarketCollector

```
PolymarketCollector(client: PolymarketClient, storage: PolymarketStorage)
├── collect_all()              # 全データ一括収集 → CollectionResult
├── collect_events(limit?)     # イベント + 子マーケット/トークン
├── collect_price_history(token_ids?, interval?) # 価格履歴
├── collect_trades(condition_ids?, limit?)       # 約定
├── collect_open_interest(condition_ids?)        # OI
├── collect_orderbooks(token_ids?)               # 注文板
├── collect_leaderboard(limit?)                  # リーダーボード
└── collect_holders(condition_ids?)              # ホルダー
```

`collect_all()` フロー:
1. `collect_events()` → 全アクティブイベント取得、マーケット/トークンも連鎖保存
2. Storage から全 token_id / condition_id を取得
3. `collect_price_history()` → 各トークンの価格履歴
4. `collect_trades()` → 各マーケットの約定
5. `collect_open_interest()` → 各マーケットの OI
6. `collect_orderbooks()` → 各トークンの注文板スナップショット
7. `collect_leaderboard()` → リーダーボード
8. `collect_holders()` → 各マーケットのホルダー
9. `CollectionResult` を返却

```python
@dataclass(frozen=True)
class CollectionResult:
    events_collected: int
    markets_collected: int
    price_points_collected: int
    trades_collected: int
    oi_snapshots_collected: int
    orderbook_snapshots_collected: int
    leaderboard_entries_collected: int
    holders_collected: int
    errors: list[str]
    duration_seconds: float
```

---

## 再利用する既存コード

| コンポーネント | パス | 用途 |
|--------------|------|------|
| `SQLiteClient` | `src/database/db/sqlite_client.py` | `execute()`, `connection()` コンテキストマネージャ |
| `get_db_path("sqlite", ...)` | `src/database/db/connection.py` | DB パス解決（DATA_DIR 尊重） |
| `EdinetStorage` | `src/market/edinet/storage.py` | **主参照**: SQLite DDL + `INSERT OR REPLACE` + upsert パターン |
| `_build_insert_sql()` | `src/market/edinet/storage.py:230` | INSERT OR REPLACE SQL 生成ヘルパー |
| `_dataclass_to_tuple()` | `src/market/edinet/storage.py:214` | dataclass → tuple 変換 |
| `_parse_ddl_columns()` | `src/market/edinet/storage.py:183` | DDL からカラム名抽出（スキーマ検証用） |
| `PolymarketClient` | `src/market/polymarket/client.py` | 16メソッドのデータ取得元 |
| Pydantic モデル | `src/market/polymarket/models.py` | `model_dump()` で dict 変換 |
| `get_logger()` | `src/utils_core/logging.py` | 構造化ロギング |

---

## 実装フェーズ（TDD）

### Phase 1: 基盤（storage_constants.py + storage.py スキャフォルド）
- `storage_constants.py`: テーブル名定数（`pm_` プレフィクス）、DB名
- `conftest.py`: tmp_path SQLite fixture
- テスト: `test_正常系_全テーブルが作成される`
- 実装: `__init__()`, `ensure_tables()`, DDL 定義（`_TABLE_DDL` dict）

### Phase 2: Events / Markets / Tokens upsert
- テスト: upsert 成功、空リスト、冪等性（重複上書き）
- 実装: `upsert_events()`, `upsert_markets()` + トークン抽出
- `make check-all`

### Phase 3: Price History upsert
- テスト: upsert 成功、重複タイムスタンプ上書き、空リスト
- 実装: `upsert_price_history()`
- `make check-all`

### Phase 4: Trades + OI + Orderbook + Leaderboard + Holders
- テスト + 実装: 各 insert/upsert メソッド
- `make check-all`

### Phase 5: Query メソッド + 統計
- テスト + 実装: 全 `get_*()` → pd.DataFrame 返却、`count_records()`, `get_collection_summary()`

### Phase 6: Collector
- テスト: Client をモックし Storage への保存を検証
- 実装: `PolymarketCollector` 全メソッド + `CollectionResult`

### Phase 7: Property テスト + Integration テスト
- upsert 冪等性のプロパティテスト
- `@pytest.mark.integration` 付き E2E テスト

### Phase 8: エクスポート + 仕上げ
- `__init__.py` 更新（`PolymarketStorage`, `PolymarketCollector`, `CollectionResult` エクスポート）
- `make check-all` 最終確認

---

## 検証方法

```bash
# 1. 全品質チェック
make check-all

# 2. Polymarket テストのみ実行
uv run pytest tests/market/polymarket/ -v

# 3. 統合テスト（実API接続）
uv run pytest tests/market/polymarket/integration/ -v -m integration

# 4. 手動動作確認（Python REPL）
python -c "
from market.polymarket.storage import get_polymarket_storage
from market.polymarket.client import PolymarketClient
from market.polymarket.collector import PolymarketCollector

storage = get_polymarket_storage()
client = PolymarketClient()
collector = PolymarketCollector(client=client, storage=storage)
result = collector.collect_events(limit=5)
print(f'Collected {result} events')
print(storage.count_records())
"
```

---

## 注意点

- **NAS互換性**: SQLite の WAL モード は NAS で問題を起こす可能性があるため、デフォルトの DELETE ジャーナルモードを使用
- **トークン抽出**: `PolymarketMarket.tokens` は `list[dict[str, Any]]` で構造が可変。`token_id` と `outcome` の存在を安全にチェック
- **Event-Market 関係**: イベント経由取得時は `event_id` が分かるが、マーケット単体取得時は nullable
- **レート制限**: Collector は既存の `PolymarketSession`（1.5 req/s）に従う。全データ収集は時間がかかるため進捗ログを出力
- **OI / 注文板 / リーダーボード**: スキーマが可変なため JSON 文字列で保持
- **`_build_insert_sql` の共通化**: EdinetStorage のヘルパーを直接インポートするか、polymarket 内にコピーするか → EdinetStorage のものは private 関数のため、polymarket 内に同等のヘルパーを実装
