# market.nasdaq パッケージ拡張計画

## Context

NASDAQ API (`api.nasdaq.com`) は無料・認証不要で30+のエンドポイントを提供するが、現在の `market.nasdaq` パッケージは Stock Screener (`/screener/stocks`) のみ実装済み。日次データ蓄積やユニバース管理、アナリストデータ追跡のため、カレンダー・Market Movers・ETFスクリーナー・アナリスト・需給データ等のエンドポイントを追加する。

既存の `NasdaqSession`（curl_cffi + TLSフィンガープリント偽装）はそのまま再利用可能。

## 設計方針

**AlphaVantage-style 単一クライアント（`NasdaqClient`）を新設**し、既存 `ScreenerCollector` は変更しない。

理由:
- 15+エンドポイントが同一JSONエンベロープ `{"data": {...}, "status": {"rCode": 200}}` を共有
- `_fetch_and_parse()` DRYヘルパーで各メソッドを3-5行に圧縮可能（`AlphaVantageClient._get_cached_or_fetch()` と同パターン）
- 全エンドポイントが既存 `NasdaqSession` を共有
- 既存の `ScreenerCollector` インポートパスに影響なし

**`types.py` / `parser.py` はサブパッケージ化せず、新ファイルを追加する方式**とする。

理由:
- 既存の `types.py`（524行）と `parser.py`（544行）のインポートパスを壊さない
- サブパッケージ化はオーバーエンジニアリング — 追加ファイル数が多くなりすぎる
- ドメイン別に `client_types.py`、`client_parsers.py` を追加すれば十分

## 対象エンドポイント

### Market-wide（銘柄指定不要）
| # | エンドポイント | メソッド名 |
|---|---|---|
| 1 | `/calendar/earnings?date=` | `get_earnings_calendar(date)` |
| 2 | `/calendar/dividends?date=` | `get_dividends_calendar(date)` |
| 3 | `/calendar/splits?date=` | `get_splits_calendar(date)` |
| 4 | `/ipo/calendar?date=` | `get_ipo_calendar(year_month)` |
| 5 | `/marketmovers` | `get_market_movers()` |
| 6 | `/screener/etf?tableonly=true&limit=0` | `get_etf_screener()` |

### Per-symbol（銘柄指定）
| # | エンドポイント | メソッド名 |
|---|---|---|
| 7 | `/analyst/{symbol}/earnings-forecast` | `get_earnings_forecast(symbol)` |
| 8 | `/analyst/{symbol}/ratings` | `get_analyst_ratings(symbol)` |
| 9 | `/analyst/{symbol}/targetprice` | `get_target_price(symbol)` |
| 10 | `/analyst/{symbol}/earnings-date` | `get_earnings_date(symbol)` |
| 11 | `/company/{symbol}/insider-trades` | `get_insider_trades(symbol)` |
| 12 | `/company/{symbol}/institutional-holdings` | `get_institutional_holdings(symbol)` |
| 13 | `/company/{symbol}/financials?frequency=` | `get_financials(symbol, frequency)` |
| 14 | `/quote/{symbol}/short-interest` | `get_short_interest(symbol)` |
| 15 | `/quote/{symbol}/dividends` | `get_dividend_history(symbol)` |

## ファイルレイアウト

```
src/market/nasdaq/
  __init__.py              # 更新: NasdaqClient + 新型を追加
  client.py                # 新規: NasdaqClient（コア）
  client_types.py          # 新規: 新エンドポイント用の型定義
  client_parsers.py        # 新規: 新エンドポイント用のパーサー
  client_cache.py          # 新規: TTL定数 + get_nasdaq_cache()
  constants.py             # 更新: 新URL定数追加
  session.py               # 変更なし
  collector.py             # 変更なし
  parser.py                # 変更なし
  types.py                 # 変更なし
  errors.py                # 変更なし
```

## 実装フェーズ

### Phase 1: 基盤（client.py スケルトン + constants + cache）

**変更ファイル:**
- `src/market/nasdaq/constants.py` — URL定数追加
- `src/market/nasdaq/client_cache.py` — 新規: TTL定数 + `get_nasdaq_cache()`
- `src/market/nasdaq/client_types.py` — 新規: 共通型（空ファイルから開始）
- `src/market/nasdaq/client_parsers.py` — 新規: `unwrap_envelope()` 共通ヘルパー
- `src/market/nasdaq/client.py` — 新規: `NasdaqClient` スケルトン + `_fetch_and_parse()` DRYヘルパー
- `src/market/nasdaq/__init__.py` — `NasdaqClient` をエクスポートに追加

**`constants.py` に追加する定数:**
```python
NASDAQ_API_BASE: Final[str] = "https://api.nasdaq.com/api"
EARNINGS_CALENDAR_URL: Final[str] = f"{NASDAQ_API_BASE}/calendar/earnings"
DIVIDENDS_CALENDAR_URL: Final[str] = f"{NASDAQ_API_BASE}/calendar/dividends"
SPLITS_CALENDAR_URL: Final[str] = f"{NASDAQ_API_BASE}/calendar/splits"
IPO_CALENDAR_URL: Final[str] = f"{NASDAQ_API_BASE}/ipo/calendar"
MARKET_MOVERS_URL: Final[str] = f"{NASDAQ_API_BASE}/marketmovers"
ETF_SCREENER_URL: Final[str] = f"{NASDAQ_API_BASE}/screener/etf"
ANALYST_URL_TEMPLATE: Final[str] = f"{NASDAQ_API_BASE}/analyst/{{symbol}}"
COMPANY_URL_TEMPLATE: Final[str] = f"{NASDAQ_API_BASE}/company/{{symbol}}"
QUOTE_URL_TEMPLATE: Final[str] = f"{NASDAQ_API_BASE}/quote/{{symbol}}"
```

**`client_cache.py` TTL定数:**
```python
CALENDAR_TTL: Final[int] = 86400       # 24h
MARKET_MOVERS_TTL: Final[int] = 300    # 5min
ETF_SCREENER_TTL: Final[int] = 86400   # 24h
ANALYST_TTL: Final[int] = 86400        # 24h
INSIDER_TRADES_TTL: Final[int] = 86400 # 24h
INSTITUTIONAL_TTL: Final[int] = 604800 # 7d
FINANCIALS_TTL: Final[int] = 604800    # 7d
SHORT_INTEREST_TTL: Final[int] = 86400 # 24h
DIVIDEND_HISTORY_TTL: Final[int] = 604800 # 7d
```

**`client.py` コア設計:**
```python
class NasdaqClient:
    def __init__(
        self,
        session: NasdaqSession | None = None,
        config: NasdaqConfig | None = None,
        retry_config: RetryConfig | None = None,
        cache: SQLiteCache | None = None,
    ) -> None: ...

    def _fetch_and_parse[T](
        self,
        url: str,
        params: dict[str, str],
        parser: Callable[[dict[str, Any]], T],
        cache_key: str,
        ttl: int,
        referer: str | None = None,
    ) -> T:
        """DRY helper: cache check → fetch → unwrap envelope → parse → cache store."""

    def _unwrap_envelope(self, raw: dict[str, Any], url: str) -> dict[str, Any]:
        """Extract data from {"data": {...}, "status": {"rCode": 200}}."""

    def _validate_symbol(self, symbol: str) -> None: ...
    def _build_referer(self, path: str) -> str: ...
```

**セッション ALLOWED_HOSTS の確認:**
現在 `ALLOWED_HOSTS = frozenset({"api.nasdaq.com"})` — 全新エンドポイントが `api.nasdaq.com` なので変更不要。

### Phase 2: カレンダーエンドポイント（earnings, dividends, splits, IPO）

**変更ファイル:**
- `src/market/nasdaq/client_types.py` — `EarningsRecord`, `DividendCalendarRecord`, `SplitRecord`, `IpoRecord` 追加
- `src/market/nasdaq/client_parsers.py` — `parse_earnings_calendar()`, `parse_dividends_calendar()`, `parse_splits_calendar()`, `parse_ipo_calendar()` 追加
- `src/market/nasdaq/client.py` — 4メソッド実装

**型定義例（frozen dataclass）:**
```python
@dataclass(frozen=True)
class EarningsRecord:
    symbol: str
    name: str
    market_cap: int | None
    fiscal_quarter_ending: str
    eps_estimate: float | None
    num_estimates: int | None
    last_year_eps: float | None
    report_time: str  # "time-pre-market" | "time-after-hours" | ...
```

**テスト:**
- `tests/market/nasdaq/unit/test_client_calendar.py`
- `tests/market/nasdaq/unit/test_client_parsers_calendar.py`

### Phase 3: Market Movers + ETF スクリーナー

**変更ファイル:**
- `client_types.py` — `MarketMover`, `MoverSection`(enum), `EtfRecord` 追加
- `client_parsers.py` — `parse_market_movers()`, `parse_etf_screener()` 追加
- `client.py` — 2メソッド実装

**テスト:**
- `tests/market/nasdaq/unit/test_client_movers.py`
- `tests/market/nasdaq/unit/test_client_etf.py`

### Phase 4: アナリストデータ（forecast, ratings, targetprice, earnings-date）

**変更ファイル:**
- `client_types.py` — `EarningsForecast`, `AnalystRatings`, `TargetPrice`, `EarningsDate` 追加
- `client_parsers.py` — 4パーサー追加
- `client.py` — 4メソッド + `get_analyst_summary(symbol)` 便利メソッド

**テスト:**
- `tests/market/nasdaq/unit/test_client_analyst.py`

### Phase 5: 企業データ（insider-trades, institutional-holdings, financials）

**変更ファイル:**
- `client_types.py` — `InsiderTrade`, `InstitutionalHolding`, `FinancialStatement` 追加
- `client_parsers.py` — 3パーサー追加
- `client.py` — 3メソッド

**テスト:**
- `tests/market/nasdaq/unit/test_client_company.py`

### Phase 6: クオートデータ（short-interest, dividends）

**変更ファイル:**
- `client_types.py` — `ShortInterestRecord`, `DividendRecord` 追加
- `client_parsers.py` — 2パーサー追加
- `client.py` — 2メソッド

**テスト:**
- `tests/market/nasdaq/unit/test_client_quote.py`

### Phase 7: バッチ処理 + __init__.py + README

**変更ファイル:**
- `client.py` — `fetch_for_symbols(symbols, method_name)` バッチヘルパー
- `__init__.py` — 全新型のエクスポート追加
- `README.md` — 新エンドポイントのドキュメント

## 再利用する既存コード

| 既存コード | パス | 用途 |
|---|---|---|
| `NasdaqSession` | `src/market/nasdaq/session.py` | HTTP セッション（そのまま再利用） |
| `NasdaqConfig`, `RetryConfig` | `src/market/nasdaq/types.py` | セッション設定 |
| `NasdaqError` hierarchy | `src/market/nasdaq/errors.py` | エラー処理 |
| `_is_missing`, `_create_cleaner` | `src/market/nasdaq/parser.py` | 数値クリーニング |
| `clean_price`, `clean_percentage`, `clean_market_cap`, `clean_volume` | `src/market/nasdaq/parser.py` | クリーナー関数 |
| `ALLOWED_HOSTS`, `DEFAULT_HEADERS`, `DEFAULT_USER_AGENTS` | `src/market/nasdaq/constants.py` | セッション定数 |
| `SQLiteCache`, `generate_cache_key` | `src/market/cache/cache.py` | キャッシュ |
| `DataCollector` ABC | `src/market/base_collector.py` | 参照のみ（NasdaqClient はABC不使用） |
| `AlphaVantageClient._get_cached_or_fetch()` | `src/market/alphavantage/client.py:979` | DRYヘルパーのパターン参照 |

## リスク

| リスク | 対策 |
|---|---|
| ボットブロッキング | 既存 NasdaqSession が対応済み。新エンドポイントで 403 が頻発する場合は `polite_delay` を引き上げ |
| APIレスポンス形式変更 | 各パーサーで防御的パース（KeyError → NasdaqParseError、空データ → 空DataFrame） |
| Per-symbol バッチのレート制限 | NasdaqSession の polite_delay (1s+jitter) が自動適用。連続 403 で early termination |
| Referer 検証 | `_build_referer()` でエンドポイント別に適切な Referer を設定。session.get() の headers オーバーライド機構を利用 |

## 検証方法

### 各フェーズ完了時
```bash
# 型チェック + リント + テスト
make check-all

# 新規テストのみ実行
uv run pytest tests/market/nasdaq/unit/test_client*.py -v
```

### Phase 2 以降の統合テスト（手動）
```python
from market.nasdaq import NasdaqClient

with NasdaqClient() as client:
    # Phase 2: カレンダー
    df = client.get_earnings_calendar()  # 当日
    print(f"決算企業数: {len(df)}")

    # Phase 3: Market Movers
    movers = client.get_market_movers()
    print(f"値上がり銘柄: {len(movers['most_advanced'])}")

    # Phase 4: アナリスト
    target = client.get_target_price("AAPL")
    print(f"AAPL目標株価: {target}")
```

### 最終検証
```bash
make check-all  # 全チェック通過を確認
```
