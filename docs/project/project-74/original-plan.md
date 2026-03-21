# Polymarket データ取得パッケージ設計プラン

## Context

Polymarket API調査（`docs/plan/2026-03-21_discussion-polymarket-api-research.md`）の結果、認証不要で暗示確率時系列・オーダーブック・取引履歴等が取得可能と判明。本プランは `src/market/polymarket/` サブモジュールとしてデータ取得ロジックを既存パッケージに統合する設計。

## 設計判断

| 判断 | 選択 | 理由 |
|------|------|------|
| クライアント構成 | 単一 `PolymarketClient` + 単一 `PolymarketSession` | JQuants/EODHDパターン踏襲。3 API（Gamma/CLOB/Data）は同一特性（JSON、認証不要） |
| HTTP ライブラリ | `httpx`（同期） | JQuants/academicと同一。anti-bot不要なのでcurl_cffi不要 |
| レート制限 | JQuants `_polite_delay` パターン（`time.monotonic()`） | float対応（1.5 req/s）。edgar `RateLimiter` はint専用 |
| リトライ | JQuants手動ループ（`get_with_retry`） | tenacity不要でシンプル。429+5xxのみリトライ |
| レスポンス型 | Pydantic V2（`models.py`） | 既存 `schema.py` との名前衝突回避 |
| キャッシュ | 既存 `SQLiteCache` + エンドポイント別TTL | JQuantsパターン踏襲 |
| WebSocket | Phase 2 に延期 | REST APIだけで分析用途は十分 |

## ファイル構成（7ファイル新規作成）

```
src/market/polymarket/
├── __init__.py       # 公開API（PolymarketClient, Config, Errors）
├── constants.py      # API URL, ALLOWED_HOSTS, デフォルト値
├── errors.py         # 例外階層（Exception直接継承、EODHD準拠）
├── types.py          # PolymarketConfig(frozen), RetryConfig, PriceInterval
├── models.py         # Pydantic V2レスポンスモデル
├── session.py        # httpxセッション（polite delay, SSRF防止, リトライ）
└── client.py         # 高レベルAPI（Gamma/CLOB/Data統合、キャッシュ付き）
```

## 実装詳細

### Step 1: `constants.py`

```python
GAMMA_BASE_URL: Final[str] = "https://gamma-api.polymarket.com"
CLOB_BASE_URL: Final[str] = "https://clob.polymarket.com"
DATA_BASE_URL: Final[str] = "https://data-api.polymarket.com"
ALLOWED_HOSTS: Final[frozenset[str]] = frozenset({
    "gamma-api.polymarket.com", "clob.polymarket.com", "data-api.polymarket.com",
})
DEFAULT_TIMEOUT: Final[float] = 30.0
DEFAULT_RATE_LIMIT_PER_SECOND: Final[float] = 1.5  # ~100 req/min、安全マージン込み
```

参照: `src/market/eodhd/constants.py`

### Step 2: `errors.py`

```
PolymarketError (base, Exception直接継承)
├── PolymarketAPIError (url, status_code, response_body)
├── PolymarketRateLimitError (url, retry_after)
├── PolymarketValidationError (field, value)
└── PolymarketNotFoundError (resource_type, resource_id)
```

- AuthError不要（全エンドポイント公開）
- NotFoundError追加（存在しないmarket/event用）
- 参照: `src/market/eodhd/errors.py`（テンプレートとしてほぼ同一構造）

### Step 3: `types.py`

```python
@dataclass(frozen=True)
class PolymarketConfig:
    gamma_base_url: str = GAMMA_BASE_URL
    clob_base_url: str = CLOB_BASE_URL
    data_base_url: str = DATA_BASE_URL
    timeout: float = DEFAULT_TIMEOUT           # 1.0-300.0
    rate_limit_per_second: float = DEFAULT_RATE_LIMIT_PER_SECOND  # > 0

@dataclass(frozen=True)
class RetryConfig:
    max_attempts: int = 3       # 1-10
    base_wait: float = 1.0
    max_wait: float = 30.0

class PriceInterval(str, Enum):
    ONE_HOUR = "1h"
    SIX_HOURS = "6h"
    ONE_DAY = "1d"
    ONE_WEEK = "1w"
    ONE_MONTH = "1m"
    MAX = "max"
    ALL = "all"
```

参照: `src/market/eodhd/types.py`, `src/market/jquants/types.py`

### Step 4: `models.py`（Pydantic V2）

| モデル | 用途 | 主要フィールド |
|--------|------|--------------|
| `PolymarketEvent` | Gamma `/events` | id, slug, title, description, active, closed, markets[] |
| `PolymarketMarket` | Gamma `/markets` | id, question, condition_id, slug, outcomes[], outcome_prices[], volume |
| `PricePoint` | CLOB `/prices-history` | t (Unix timestamp), p (implied probability 0.0-1.0) |
| `OrderBook` | CLOB `/book` | market, asset_id, bids[], asks[] |
| `TradeRecord` | Data `/trades` | id, market, asset_id, side, size, price, timestamp |

- `model_config = {"populate_by_name": True, "extra": "ignore"}` で未知フィールドに耐性
- 参照: `src/market/schema.py`

### Step 5: `session.py`

JQuants `session.py` をベースに認証部分を除去した簡素版。

```python
class PolymarketSession:
    def __init__(self, config, retry_config): ...

    def get(self, url, params) -> httpx.Response:
        # 1. _validate_url() — SSRF防止
        # 2. _polite_delay() — monotonic clock ベース
        # 3. _client.get()
        # 4. _handle_response() — 429/404/4xx/5xx分岐

    def get_with_retry(self, url, params) -> httpx.Response:
        # JQuants get_with_retry 手動ループ（lines 198-272）準拠
        # 429 + 5xx のみリトライ、4xx は即座にraise

    def close(self): ...
    def __enter__(self): ...
    def __exit__(self): ...
```

参照: `src/market/jquants/session.py:62-272`

### Step 6: `client.py`

```python
class PolymarketClient:
    def __init__(self, config, retry_config, cache): ...

    # --- Gamma API ---
    def get_events(*, active, closed, limit, offset) -> list[PolymarketEvent]
    def get_event(event_id) -> PolymarketEvent
    def get_markets(*, active, closed, limit, offset) -> list[PolymarketMarket]
    def get_market(condition_id) -> PolymarketMarket

    # --- CLOB API ---
    def get_prices_history(token_id, *, interval, fidelity, start_ts, end_ts) -> MarketDataResult
    def get_midpoint(token_id) -> float
    def get_spread(token_id) -> dict[str, float]
    def get_orderbook(token_id) -> OrderBook

    # --- Data API ---
    def get_open_interest(condition_id) -> dict[str, float]
    def get_trades(condition_id, *, limit) -> list[TradeRecord]
    def get_leaderboard(*, category, time_period, limit) -> list[dict]
    def get_holders(condition_id) -> list[dict]
```

**`get_prices_history` の戻り値**: `MarketDataResult(symbol=token_id, data=DataFrame["timestamp","probability"], source=DataSource.POLYMARKET)`

**キャッシュ TTL**:

| エンドポイント | TTL | 理由 |
|--------------|-----|------|
| events/markets メタデータ | 1時間 | 変更頻度低 |
| アクティブ市場の prices-history | 60秒 | 頻繁に更新 |
| 解決済み市場の prices-history | 30日 | 不変 |
| orderbook | 30秒 | 高頻度変動 |
| OI / trades | 5分 | 中頻度 |
| leaderboard | 1時間 | 変更頻度低 |

参照: `src/market/jquants/client.py`

### Step 7: `__init__.py`

`PolymarketClient`, `PolymarketConfig`, `RetryConfig`, `FetchOptions` + 全エラークラスをexport。

## 既存ファイル変更（3ファイル）

| ファイル | 変更内容 |
|---------|---------|
| `src/market/types.py:75` | `POLYMARKET = "polymarket"` を `DataSource` enum に追加 |
| `src/market/errors.py` | Polymarketエラーをre-export + `ErrorCode` に4エントリ追加 |
| `src/market/__init__.py` | Polymarket exports を追加（`PolymarketClient`, `PolymarketConfig`, エラー群） |

## テスト構成

```
tests/market/polymarket/
├── unit/
│   ├── test_constants.py     # URL値、ALLOWED_HOSTS
│   ├── test_errors.py        # 例外階層、属性
│   ├── test_types.py         # Config検証（frozen、デフォルト、範囲）
│   ├── test_models.py        # Pydanticモデルバリデーション
│   ├── test_session.py       # SSRF防止、レート制限、エラーハンドリング（httpxモック）
│   └── test_client.py        # クライアントメソッド（セッションモック）
├── property/
│   └── test_types_property.py  # Hypothesis: Config境界値
└── integration/
    └── test_polymarket_integration.py  # ライブAPI疎通テスト（@pytest.mark.integration）
```

テスト命名: `test_正常系_*`, `test_異常系_*`, `test_エッジケース_*`

## 実装順序

1. `constants.py` → `errors.py` → `types.py` （依存なし、並行可能）
2. `models.py` （pydanticのみ依存）
3. `session.py` （constants, errors, types に依存）
4. `client.py` （全ファイルに依存）
5. `__init__.py`
6. 既存ファイル変更（`types.py`, `errors.py`, `__init__.py`）
7. テスト作成

## 検証方法

```bash
# 1. 品質チェック
make check-all

# 2. 単体テスト
uv run pytest tests/market/polymarket/unit/ -v

# 3. プロパティテスト
uv run pytest tests/market/polymarket/property/ -v

# 4. 統合テスト（ライブAPI疎通）
uv run pytest tests/market/polymarket/integration/ -v -m integration

# 5. 手動疎通確認
python -c "
from market.polymarket import PolymarketClient
with PolymarketClient() as client:
    events = client.get_events(limit=3)
    print(f'Events: {len(events)}')
    if events and events[0].markets:
        m = events[0].markets[0]
        print(f'Market: {m.question}')
        print(f'Outcomes: {m.outcomes} -> {m.outcome_prices}')
"
```

## Phase 2（延期事項）

- WebSocket ストリーム（`ws.py`）: book, price_change, last_trade_price, best_bid_ask, new_market, market_resolved
- `websockets` or `httpx-ws` 依存追加が必要
