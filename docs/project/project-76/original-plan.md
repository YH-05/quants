# Alpha Vantage データ収集ライブラリ追加プラン

## Context

market パッケージに Alpha Vantage API のデータ収集サブパッケージを追加する。現在 market パッケージには yfinance, fred, jquants, nasdaq, bse 等 12+ のサブパッケージがあるが、Alpha Vantage は未対応。Alpha Vantage は株式・為替・暗号通貨・経済指標・企業ファンダメンタルズを統一APIで提供しており、既存データソースの補完として有用。

## Alpha Vantage API 仕様

| 項目 | 値 |
|------|-----|
| Base URL | `https://www.alphavantage.co/query` |
| 認証 | `apikey` クエリパラメータ |
| レート制限 (Free) | 25 req/min, 500 req/hour |
| レスポンス形式 | JSON（数値は文字列、キーに番号プレフィックス付き） |
| エラー形式 | HTTP 200 + JSON の `"Error Message"` / `"Note"` / `"Information"` キー |

### 主要エンドポイント

| カテゴリ | function パラメータ | 戻り値 |
|---------|-------------------|--------|
| 時系列 | `TIME_SERIES_DAILY`, `_WEEKLY`, `_MONTHLY`, `_INTRADAY` | OHLCV DataFrame |
| リアルタイム | `GLOBAL_QUOTE` | dict |
| ファンダメンタルズ | `OVERVIEW`, `INCOME_STATEMENT`, `BALANCE_SHEET`, `CASH_FLOW`, `EARNINGS` | dict / DataFrame |
| 為替 | `CURRENCY_EXCHANGE_RATE`, `FX_DAILY`, `FX_WEEKLY`, `FX_MONTHLY` | dict / DataFrame |
| 暗号通貨 | `DIGITAL_CURRENCY_DAILY`, `_WEEKLY`, `_MONTHLY` | DataFrame |
| 経済指標 | `REAL_GDP`, `CPI`, `INFLATION`, `UNEMPLOYMENT`, `TREASURY_YIELD`, `FEDERAL_FUNDS_RATE` 等 | DataFrame |

## ファイル構成

```
src/market/alphavantage/
├── __init__.py          # Public API exports
├── constants.py         # API URL, ホスト許可リスト, 環境変数名, デフォルト値
├── errors.py            # AlphaVantageError 例外階層
├── types.py             # Config dataclass, Enum, FetchOptions
├── rate_limiter.py      # デュアルウィンドウスライディングレートリミッター（新規）
├── session.py           # httpx セッション（レートリミッター統合）
├── parser.py            # レスポンス正規化（AV特有のJSON → DataFrame）
├── cache.py             # TTL 定数 + キャッシュファクトリ
└── client.py            # 高レベル型付きAPIクライアント

tests/market/alphavantage/
├── __init__.py
├── conftest.py          # Config fixture, モックセッション, サンプルAPIレスポンス
├── unit/
│   ├── __init__.py
│   ├── test_constants.py
│   ├── test_errors.py
│   ├── test_types.py
│   ├── test_rate_limiter.py
│   ├── test_session.py
│   ├── test_parser.py
│   ├── test_cache.py
│   └── test_client.py
├── property/
│   ├── __init__.py
│   ├── test_parser_property.py
│   └── test_rate_limiter_property.py
└── integration/
    ├── __init__.py
    └── test_alphavantage_integration.py
```

## 設計詳細

### 1. `constants.py`

参照: `src/market/jquants/constants.py`

```python
BASE_URL: Final[str] = "https://www.alphavantage.co/query"
ALLOWED_HOSTS: Final[frozenset[str]] = frozenset({"www.alphavantage.co"})
ALPHA_VANTAGE_API_KEY_ENV: Final[str] = "ALPHA_VANTAGE_API_KEY"

# レート制限（Free tier）
DEFAULT_REQUESTS_PER_MINUTE: Final[int] = 25
DEFAULT_REQUESTS_PER_HOUR: Final[int] = 500

# HTTP
DEFAULT_TIMEOUT: Final[float] = 30.0
DEFAULT_POLITE_DELAY: Final[float] = 2.5   # 60s / 25 req = 2.4s → 余裕を持って2.5s
DEFAULT_DELAY_JITTER: Final[float] = 0.5

# CWE-209 対策
MAX_RESPONSE_BODY_LOG: Final[int] = 200
```

### 2. `errors.py`

参照: `src/market/jquants/errors.py`（直接 Exception 継承パターン）

```
AlphaVantageError (base)
├── AlphaVantageAPIError (url, status_code, response_body)
├── AlphaVantageRateLimitError (url, retry_after)
├── AlphaVantageValidationError (field, value)
├── AlphaVantageParseError (raw_data, field)
└── AlphaVantageAuthError (message のみ)
```

- `AlphaVantageParseError`: AV のレスポンス構造が不安定なため、nasdaq の `NasdaqParseError` と同様に追加
- `AlphaVantageAuthError`: AV は無効なAPIキーで HTTP 200 + `"Error Message"` を返すため必要

### 3. `types.py`

参照: `src/market/jquants/types.py`

**Enum（`str, Enum` パターン）**:

| Enum | 値 |
|------|-----|
| `OutputSize` | `COMPACT` ("compact"), `FULL` ("full") |
| `Interval` | `ONE_MIN` ("1min") ～ `SIXTY_MIN` ("60min") |
| `TimeSeriesFunction` | `DAILY`, `DAILY_ADJUSTED`, `WEEKLY`, `MONTHLY`, `INTRADAY` 等 |
| `FundamentalFunction` | `OVERVIEW`, `INCOME_STATEMENT`, `BALANCE_SHEET`, `CASH_FLOW`, `EARNINGS` |
| `ForexFunction` | `EXCHANGE_RATE`, `FX_DAILY`, `FX_WEEKLY`, `FX_MONTHLY` |
| `CryptoFunction` | `DAILY`, `WEEKLY`, `MONTHLY` |
| `EconomicIndicator` | `REAL_GDP`, `CPI`, `INFLATION`, `UNEMPLOYMENT`, `TREASURY_YIELD`, `FEDERAL_FUNDS_RATE` 等 |

**Config dataclass（frozen=True）**:

```python
@dataclass(frozen=True)
class AlphaVantageConfig:
    api_key: str = field(default="", repr=False)  # env var フォールバック
    timeout: float = DEFAULT_TIMEOUT               # 1.0-300.0
    polite_delay: float = DEFAULT_POLITE_DELAY     # 0.0-60.0
    delay_jitter: float = DEFAULT_DELAY_JITTER     # 0.0-30.0
    requests_per_minute: int = DEFAULT_REQUESTS_PER_MINUTE  # Premium 対応
    requests_per_hour: int = DEFAULT_REQUESTS_PER_HOUR

@dataclass(frozen=True)
class RetryConfig:  # jquants と同一パターン
    max_attempts: int = 3
    exponential_base: float = 2.0
    max_delay: float = 30.0
    initial_delay: float = 1.0
    jitter: bool = True

@dataclass(frozen=True)
class FetchOptions:
    use_cache: bool = True
    force_refresh: bool = False
```

### 4. `rate_limiter.py`（新規モジュール）

既存パッケージにない新機能。AV のデュアルウィンドウ制限（25/min + 500/hour）に対応。

```python
class DualWindowRateLimiter:
    """スレッドセーフなスライディングウィンドウレートリミッター。

    time.monotonic() ベースの deque でリクエストタイムスタンプを追跡。
    acquire() で両ウィンドウをチェックし、必要なら sleep。
    """
    def __init__(self, requests_per_minute: int = 25, requests_per_hour: int = 500)
    def acquire(self) -> float          # ブロッキング、待機時間を返す
    def _purge_old(self, now: float)    # 1時間超のタイムスタンプを削除
    @property
    def available_minute(self) -> int   # 残りリクエスト数（分）
    @property
    def available_hour(self) -> int     # 残りリクエスト数（時）
```

- `threading.Lock()` でスレッドセーフ
- `collections.deque` で O(1) append、O(n) purge（n ≤ 500）
- Premium ティアユーザーはコンストラクタで上限変更可能

### 5. `session.py`

参照: `src/market/jquants/session.py`（httpx, polite delay, SSRF 防止, リトライ）

```python
class AlphaVantageSession:
    def __init__(self, config, retry_config)
    def get(self, params: dict[str, str]) -> httpx.Response
    def get_with_retry(self, params: dict[str, str]) -> httpx.Response
    def _handle_response(self, response: httpx.Response) -> None  # AV特有のエラー検出
    def _resolve_api_key(self) -> str
    # Context manager: __enter__, __exit__, close()
```

**AV 固有の注意点**:
- API キーは `params["apikey"]` として注入（ヘッダーではない）
- `_handle_response` で HTTP 200 のボディを解析し、`"Error Message"`, `"Note"`, `"Information"` キーを検出
  - `"Note"` → `AlphaVantageRateLimitError`
  - `"Error Message"` → `AlphaVantageAPIError` または `AlphaVantageAuthError`
  - `"Information"` → `AlphaVantageAuthError`（プレミアムエンドポイント）
- レートリミッター `acquire()` → polite delay → リクエスト実行の順序

### 6. `parser.py`

参照: `src/market/nasdaq/parser.py`（cleaner factory, DataFrame 正規化）

**AV レスポンスの特徴**:
- 時系列キーがエンドポイントごとに異なる（`"Time Series (Daily)"`, `"Weekly Time Series"`, `"Time Series FX (Daily)"` 等）
- カラムキーに番号プレフィックス（`"1. open"`, `"2. high"` 等）
- 全値が文字列（`"150.2300"`）
- ファンダメンタルズは `"annualReports"` / `"quarterlyReports"` 配列
- 経済指標は `"data"` 配列（`{"date": "...", "value": "..."}`）

**主要関数**:

| 関数 | 入力 | 出力 |
|------|------|------|
| `parse_time_series(data)` | 任意の時系列レスポンス | `pd.DataFrame`（DatetimeIndex, float カラム） |
| `parse_global_quote(data)` | GLOBAL_QUOTE レスポンス | `dict[str, Any]` |
| `parse_company_overview(data)` | OVERVIEW レスポンス | `dict[str, Any]` |
| `parse_financial_statements(data, report_type)` | 財務諸表レスポンス | `pd.DataFrame` |
| `parse_earnings(data)` | EARNINGS レスポンス | `pd.DataFrame` |
| `parse_economic_indicator(data)` | 経済指標レスポンス | `pd.DataFrame` |
| `parse_forex_rate(data)` | CURRENCY_EXCHANGE_RATE レスポンス | `dict[str, Any]` |

**内部ヘルパー**:
- `_detect_time_series_key(data)`: トップレベルキーから時系列データキーを検出
- `_normalize_ohlcv_columns(raw_key)`: `"1. open"` → `"open"` への正規化（regex `r"^\d+\.\s*"`）
- `_clean_numeric(value)`: 文字列 → float 変換（`"None"`, `"-"`, 空文字列対応）

### 7. `cache.py`

参照: `src/market/jquants/cache.py`

```python
TIME_SERIES_DAILY_TTL: Final[int] = 86400       # 24時間
TIME_SERIES_INTRADAY_TTL: Final[int] = 3600     # 1時間
FUNDAMENTALS_TTL: Final[int] = 604800           # 7日
ECONOMIC_INDICATOR_TTL: Final[int] = 86400      # 24時間
FOREX_TTL: Final[int] = 86400                   # 24時間
CRYPTO_TTL: Final[int] = 86400                  # 24時間
GLOBAL_QUOTE_TTL: Final[int] = 300              # 5分
COMPANY_OVERVIEW_TTL: Final[int] = 604800       # 7日

def get_alphavantage_cache() -> SQLiteCache:
    return create_persistent_cache(ttl_seconds=TIME_SERIES_DAILY_TTL, max_entries=10000)
```

### 8. `client.py`

参照: `src/market/jquants/client.py`

```python
class AlphaVantageClient:
    def __init__(self, config, retry_config, cache)

    # === 時系列 ===
    def get_daily(self, symbol, outputsize=OutputSize.COMPACT, options=None) -> pd.DataFrame
    def get_weekly(self, symbol, ...) -> pd.DataFrame
    def get_monthly(self, symbol, ...) -> pd.DataFrame
    def get_intraday(self, symbol, interval, outputsize, options) -> pd.DataFrame

    # === リアルタイム ===
    def get_global_quote(self, symbol, options) -> dict[str, Any]

    # === ファンダメンタルズ ===
    def get_company_overview(self, symbol, options) -> dict[str, Any]
    def get_income_statement(self, symbol, options) -> pd.DataFrame
    def get_balance_sheet(self, symbol, options) -> pd.DataFrame
    def get_cash_flow(self, symbol, options) -> pd.DataFrame
    def get_earnings(self, symbol, options) -> pd.DataFrame

    # === 為替 ===
    def get_exchange_rate(self, from_currency, to_currency) -> dict[str, Any]
    def get_fx_daily(self, from_symbol, to_symbol, outputsize, options) -> pd.DataFrame

    # === 暗号通貨 ===
    def get_crypto_daily(self, symbol, market="USD", options) -> pd.DataFrame

    # === 経済指標 ===
    def get_real_gdp(self, interval="annual", options) -> pd.DataFrame
    def get_cpi(self, interval="monthly", options) -> pd.DataFrame
    def get_inflation(self, options) -> pd.DataFrame
    def get_unemployment(self, options) -> pd.DataFrame
    def get_treasury_yield(self, interval="monthly", maturity="10year", options) -> pd.DataFrame
    def get_federal_funds_rate(self, interval="monthly", options) -> pd.DataFrame

    # === 内部 ===
    def _request(self, params) -> dict[str, Any]
    def _validate_symbol(self, symbol) -> None      # 1-10文字、英数字+ドット
    def _get_cached_or_fetch(self, cache_key, params, parser, ttl, options, **kwargs)
    # Context manager: __enter__, __exit__, close()
```

- `_get_cached_or_fetch`: キャッシュチェック→フェッチ→パース→保存の DRY ヘルパー（jquants では各メソッドにインラインだったものを抽象化）
- シンボル検証は `.` を許可（例: `BRK.B`）

### 9. `__init__.py`

参照: `src/market/jquants/__init__.py`

全公開クラス・Enum・エラーを re-export + `__all__` 定義。

## 実装順序

TDD で各フェーズごとにテスト→実装→リファクタリングを実行。

| Phase | ファイル | 依存先 | 複雑度 |
|-------|---------|--------|--------|
| 1 | `constants.py` + `test_constants.py` | なし | Low |
| 2 | `errors.py` + `test_errors.py` | なし | Low |
| 3 | `types.py` + `test_types.py` | constants | Medium |
| 4 | `rate_limiter.py` + `test_rate_limiter.py` + `test_rate_limiter_property.py` | stdlib のみ | **High** |
| 5 | `session.py` + `test_session.py` | constants, errors, types, rate_limiter | Medium |
| 6 | `parser.py` + `test_parser.py` + `test_parser_property.py` | errors | **High** |
| 7 | `cache.py` + `test_cache.py` | market.cache.cache | Low |
| 8 | `client.py` + `test_client.py` | 全上記 | **High** |
| 9 | `__init__.py` | 全上記 | Low |
| 10 | `conftest.py` + 統合テスト | 全上記 | Medium |

## 参照ファイル（実装時に必ず確認）

| パターン | 参照先 |
|---------|--------|
| セッション | `src/market/jquants/session.py` |
| クライアント | `src/market/jquants/client.py` |
| エラー階層 | `src/market/jquants/errors.py` |
| 型定義 | `src/market/jquants/types.py` |
| キャッシュ | `src/market/jquants/cache.py` |
| パーサー | `src/market/nasdaq/parser.py` |
| `__init__.py` | `src/market/jquants/__init__.py` |
| テスト fixture | `tests/market/nasdaq/conftest.py` |
| テンプレート | `template/src/template_package/` |

## 新規依存パッケージ

**なし**。`httpx` は既に依存関係に含まれている。外部の `alpha_vantage` PyPI パッケージは使用せず、コードベースの一貫性のために自前クライアントを構築する。

## 検証方法

### 自動テスト

```bash
# 全テスト（unit + property）
uv run pytest tests/market/alphavantage/ -v

# 統合テスト（要 API キー）
ALPHA_VANTAGE_API_KEY=xxx uv run pytest tests/market/alphavantage/integration/ -v -m integration

# 品質チェック
make check-all
```

### 手動検証

```python
from market.alphavantage import AlphaVantageClient, AlphaVantageConfig

config = AlphaVantageConfig(api_key="YOUR_KEY")
with AlphaVantageClient(config=config) as client:
    # 時系列
    df = client.get_daily("AAPL")
    assert not df.empty
    assert set(df.columns) >= {"open", "high", "low", "close", "volume"}

    # ファンダメンタルズ
    overview = client.get_company_overview("AAPL")
    assert "MarketCapitalization" in overview

    # 経済指標
    gdp = client.get_real_gdp()
    assert not gdp.empty
```

### レートリミッター検証

```python
from market.alphavantage.rate_limiter import DualWindowRateLimiter

limiter = DualWindowRateLimiter(requests_per_minute=5, requests_per_hour=100)
for i in range(6):
    wait = limiter.acquire()
    print(f"Request {i+1}: waited {wait:.2f}s, remaining={limiter.available_minute}/min")
# 6回目で ~12s の待機が発生することを確認
```
