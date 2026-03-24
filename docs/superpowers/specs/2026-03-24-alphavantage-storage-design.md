# Alpha Vantage Storage Layer 設計書

**Date**: 2026-03-24
**Status**: Draft (rev.2 — レビュー指摘反映)
**Scope**: Alpha Vantage APIデータの永続化層（SQLite）

---

## 1. 概要

Alpha Vantage APIクライアント (`market.alphavantage.client`) が取得したデータを
SQLiteデータベースに永続化するストレージ層を実装する。

既存の TTL キャッシュ（SQLiteCache）は短期的なAPI応答キャッシュであり、
本ストレージ層は**長期的なデータ蓄積と分析クエリ**を目的とする。

### 設計方針

- **SQLite一本**: 外付けSSD・NAS上での保存・操作に対応
- **EdinetStorage / PolymarketStorage パターン踏襲**: DDL-first、INSERT OR REPLACE、dataclass→tuple
- **8テーブル構成**: `av_` プレフィックスで名前空間を分離
- **camelCase → snake_case 変換**: Collector 層で API レスポンスの camelCase を snake_case に統一変換してから Storage に渡す

### スコープ外（将来の拡張）

- 暗号通貨テーブル (`av_crypto_daily`): `client.get_crypto_daily()` に対応するが、初回スコープでは除外。必要時に追加。
- Global Quote スナップショット: リアルタイム価格のスナップショット蓄積。キャッシュで十分な場合が多い。
- Exchange Rate スナップショット: 同上。

---

## 2. ファイル構成

```
src/market/alphavantage/
├── storage_constants.py   # テーブル名定数、DB名、環境変数名
├── models.py              # frozen dataclass（ストレージレコード型）
├── storage.py             # AlphaVantageStorage クラス
└── collector.py           # API→Storage パイプライン（AlphaVantageCollector）
```

---

## 3. テーブル設計

### 3.1 `av_daily_prices` — 日次OHLCV

```sql
CREATE TABLE IF NOT EXISTS av_daily_prices (
    symbol TEXT NOT NULL,
    date TEXT NOT NULL,
    open REAL NOT NULL,
    high REAL NOT NULL,
    low REAL NOT NULL,
    close REAL NOT NULL,
    adjusted_close REAL,
    volume INTEGER NOT NULL,
    fetched_at TEXT NOT NULL,
    PRIMARY KEY (symbol, date)
)
```

- **ソース**: `client.get_daily()`
- **adjusted_close**: `TIME_SERIES_DAILY_ADJUSTED` 使用時に格納。通常の `TIME_SERIES_DAILY` では NULL。
- **備考**: weekly/monthly は別テーブルにしない。日次がメイン用途。
  必要時に `av_weekly_prices`, `av_monthly_prices` を追加。

### 3.2 `av_company_overview` — 企業プロファイル

`parser.py` の `_OVERVIEW_NUMERIC_FIELDS`（32フィールド）+ テキストフィールドを完全に反映。

```sql
CREATE TABLE IF NOT EXISTS av_company_overview (
    symbol TEXT NOT NULL,
    name TEXT,
    description TEXT,
    exchange TEXT,
    currency TEXT,
    country TEXT,
    sector TEXT,
    industry TEXT,
    fiscal_year_end TEXT,
    latest_quarter TEXT,
    -- Numeric fields (from _OVERVIEW_NUMERIC_FIELDS)
    market_capitalization REAL,
    ebitda REAL,
    pe_ratio REAL,
    peg_ratio REAL,
    book_value REAL,
    dividend_per_share REAL,
    dividend_yield REAL,
    eps REAL,
    diluted_eps_ttm REAL,
    week_52_high REAL,
    week_52_low REAL,
    day_50_moving_average REAL,
    day_200_moving_average REAL,
    shares_outstanding REAL,
    revenue_per_share_ttm REAL,
    profit_margin REAL,
    operating_margin_ttm REAL,
    return_on_assets_ttm REAL,
    return_on_equity_ttm REAL,
    revenue_ttm REAL,
    gross_profit_ttm REAL,
    quarterly_earnings_growth_yoy REAL,
    quarterly_revenue_growth_yoy REAL,
    analyst_target_price REAL,
    analyst_rating_strong_buy REAL,
    analyst_rating_buy REAL,
    analyst_rating_hold REAL,
    analyst_rating_sell REAL,
    analyst_rating_strong_sell REAL,
    trailing_pe REAL,
    forward_pe REAL,
    price_to_sales_ratio_ttm REAL,
    price_to_book_ratio REAL,
    ev_to_revenue REAL,
    ev_to_ebitda REAL,
    beta REAL,
    fetched_at TEXT NOT NULL,
    PRIMARY KEY (symbol)
)
```

- **ソース**: `client.get_company_overview()`
- **INSERT OR REPLACE** で最新データに上書き

### API → DDL カラム名マッピング（company_overview）

| API (camelCase) | DDL (snake_case) |
|---|---|
| `MarketCapitalization` | `market_capitalization` |
| `PERatio` | `pe_ratio` |
| `PEGRatio` | `peg_ratio` |
| `52WeekHigh` | `week_52_high` |
| `52WeekLow` | `week_52_low` |
| `50DayMovingAverage` | `day_50_moving_average` |
| `200DayMovingAverage` | `day_200_moving_average` |
| `OperatingMarginTTM` | `operating_margin_ttm` |
| `DilutedEPSTTM` | `diluted_eps_ttm` |
| `QuarterlyEarningsGrowthYOY` | `quarterly_earnings_growth_yoy` |
| `QuarterlyRevenueGrowthYOY` | `quarterly_revenue_growth_yoy` |
| `AnalystRatingStrongBuy` | `analyst_rating_strong_buy` |
| `TrailingPE` | `trailing_pe` |
| `ForwardPE` | `forward_pe` |
| `PriceToSalesRatioTTM` | `price_to_sales_ratio_ttm` |
| `PriceToBookRatio` | `price_to_book_ratio` |
| `EVToRevenue` | `ev_to_revenue` |
| `EVToEBITDA` | `ev_to_ebitda` |

**変換ルール**: Collector 層に `_camel_to_snake()` ヘルパーを実装。
数字先頭キー（`52WeekHigh`）は特殊マッピング辞書で対応。

### 3.3 `av_income_statements` — 損益計算書

```sql
CREATE TABLE IF NOT EXISTS av_income_statements (
    symbol TEXT NOT NULL,
    fiscal_date_ending TEXT NOT NULL,
    report_type TEXT NOT NULL,
    reported_currency TEXT,
    gross_profit REAL,
    total_revenue REAL,
    cost_of_revenue REAL,
    cost_of_goods_and_services_sold REAL,
    operating_income REAL,
    selling_general_and_administrative REAL,
    research_and_development REAL,
    operating_expenses REAL,
    net_income REAL,
    interest_income REAL,
    interest_expense REAL,
    income_before_tax REAL,
    income_tax_expense REAL,
    ebit REAL,
    ebitda REAL,
    depreciation_and_amortization REAL,
    fetched_at TEXT NOT NULL,
    PRIMARY KEY (symbol, fiscal_date_ending, report_type)
)
```

- **ソース**: `client.get_income_statement(report_type="annualReports"|"quarterlyReports")`
- **report_type**: `"annual"` or `"quarterly"`（Collector 層で `"annualReports"` → `"annual"` に正規化）
- **camelCase → snake_case**: Collector 層の `_camel_to_snake()` で変換

### 3.4 `av_balance_sheets` — 貸借対照表

```sql
CREATE TABLE IF NOT EXISTS av_balance_sheets (
    symbol TEXT NOT NULL,
    fiscal_date_ending TEXT NOT NULL,
    report_type TEXT NOT NULL,
    reported_currency TEXT,
    total_assets REAL,
    total_current_assets REAL,
    cash_and_equivalents REAL,
    cash_and_short_term_investments REAL,
    inventory REAL,
    current_net_receivables REAL,
    total_non_current_assets REAL,
    property_plant_equipment REAL,
    intangible_assets REAL,
    goodwill REAL,
    investments REAL,
    long_term_investments REAL,
    short_term_investments REAL,
    total_liabilities REAL,
    total_current_liabilities REAL,
    current_long_term_debt REAL,
    short_term_debt REAL,
    current_accounts_payable REAL,
    total_non_current_liabilities REAL,
    long_term_debt REAL,
    total_shareholder_equity REAL,
    retained_earnings REAL,
    common_stock REAL,
    common_stock_shares_outstanding REAL,
    fetched_at TEXT NOT NULL,
    PRIMARY KEY (symbol, fiscal_date_ending, report_type)
)
```

- **ソース**: `client.get_balance_sheet(report_type="annualReports"|"quarterlyReports")`

### 3.5 `av_cash_flows` — キャッシュフロー計算書

```sql
CREATE TABLE IF NOT EXISTS av_cash_flows (
    symbol TEXT NOT NULL,
    fiscal_date_ending TEXT NOT NULL,
    report_type TEXT NOT NULL,
    reported_currency TEXT,
    operating_cashflow REAL,
    payments_for_operating_activities REAL,
    change_in_operating_liabilities REAL,
    change_in_operating_assets REAL,
    depreciation_depletion_and_amortization REAL,
    capital_expenditures REAL,
    change_in_receivables REAL,
    change_in_inventory REAL,
    profit_loss REAL,
    cashflow_from_investment REAL,
    cashflow_from_financing REAL,
    dividend_payout REAL,
    proceeds_from_repurchase_of_equity REAL,
    proceeds_from_issuance_of_long_term_debt REAL,
    payments_for_repurchase_of_common_stock REAL,
    change_in_cash_and_equivalents REAL,
    net_income REAL,
    fetched_at TEXT NOT NULL,
    PRIMARY KEY (symbol, fiscal_date_ending, report_type)
)
```

- **ソース**: `client.get_cash_flow(report_type="annualReports"|"quarterlyReports")`

### 3.6 `av_earnings` — 決算EPS

```sql
CREATE TABLE IF NOT EXISTS av_earnings (
    symbol TEXT NOT NULL,
    fiscal_date_ending TEXT NOT NULL,
    period_type TEXT NOT NULL,
    reported_date TEXT,
    reported_eps REAL,
    estimated_eps REAL,
    surprise REAL,
    surprise_percentage REAL,
    fetched_at TEXT NOT NULL,
    PRIMARY KEY (symbol, fiscal_date_ending, period_type)
)
```

- **ソース**: `client.get_earnings()` → `(annual_df, quarterly_df)`
- **period_type**: `"annual"` or `"quarterly"`
- **備考**: annual earnings には `reported_date`, `estimated_eps`, `surprise`, `surprise_percentage` がないため NULL

### 3.7 `av_economic_indicators` — マクロ経済指標

```sql
CREATE TABLE IF NOT EXISTS av_economic_indicators (
    indicator TEXT NOT NULL,
    date TEXT NOT NULL,
    value REAL,
    interval TEXT NOT NULL DEFAULT '',
    maturity TEXT NOT NULL DEFAULT '',
    fetched_at TEXT NOT NULL,
    PRIMARY KEY (indicator, date, interval, maturity)
)
```

- **ソース**: `client.get_real_gdp()`, `get_cpi()`, `get_inflation()`,
  `get_unemployment()`, `get_treasury_yield()`, `get_federal_funds_rate()`
- **indicator 値**: `"REAL_GDP"`, `"CPI"`, `"INFLATION"`, `"UNEMPLOYMENT"`,
  `"TREASURY_YIELD"`, `"FEDERAL_FUNDS_RATE"`
- **interval**: `"quarterly"`, `"monthly"`, `"daily"` 等。interval パラメータのない指標（INFLATION, UNEMPLOYMENT）は空文字
- **maturity**: Treasury Yield の満期（`"10year"`, `"30year"` 等）。他の指標は空文字

### 3.8 `av_forex_daily` — 為替日次OHLC

```sql
CREATE TABLE IF NOT EXISTS av_forex_daily (
    from_currency TEXT NOT NULL,
    to_currency TEXT NOT NULL,
    date TEXT NOT NULL,
    open REAL NOT NULL,
    high REAL NOT NULL,
    low REAL NOT NULL,
    close REAL NOT NULL,
    fetched_at TEXT NOT NULL,
    PRIMARY KEY (from_currency, to_currency, date)
)
```

- **ソース**: `client.get_fx_daily()`

---

## 4. storage_constants.py

```python
from typing import Final

AV_DB_PATH_ENV: Final[str] = "ALPHAVANTAGE_DB_PATH"
DEFAULT_DB_NAME: Final[str] = "alphavantage"

TABLE_DAILY_PRICES: Final[str] = "av_daily_prices"
TABLE_COMPANY_OVERVIEW: Final[str] = "av_company_overview"
TABLE_INCOME_STATEMENTS: Final[str] = "av_income_statements"
TABLE_BALANCE_SHEETS: Final[str] = "av_balance_sheets"
TABLE_CASH_FLOWS: Final[str] = "av_cash_flows"
TABLE_EARNINGS: Final[str] = "av_earnings"
TABLE_ECONOMIC_INDICATORS: Final[str] = "av_economic_indicators"
TABLE_FOREX_DAILY: Final[str] = "av_forex_daily"
```

---

## 5. models.py — ストレージレコード型

frozen dataclass で定義。各テーブルの DDL カラムと 1:1 対応。

```python
@dataclass(frozen=True)
class DailyPriceRecord:
    symbol: str
    date: str
    open: float
    high: float
    low: float
    close: float
    adjusted_close: float | None
    volume: int
    fetched_at: str

@dataclass(frozen=True)
class CompanyOverviewRecord:
    symbol: str
    name: str | None
    description: str | None
    exchange: str | None
    currency: str | None
    country: str | None
    sector: str | None
    industry: str | None
    fiscal_year_end: str | None
    latest_quarter: str | None
    market_capitalization: float | None
    ebitda: float | None
    pe_ratio: float | None
    peg_ratio: float | None
    book_value: float | None
    dividend_per_share: float | None
    dividend_yield: float | None
    eps: float | None
    diluted_eps_ttm: float | None
    week_52_high: float | None
    week_52_low: float | None
    day_50_moving_average: float | None
    day_200_moving_average: float | None
    shares_outstanding: float | None
    revenue_per_share_ttm: float | None
    profit_margin: float | None
    operating_margin_ttm: float | None
    return_on_assets_ttm: float | None
    return_on_equity_ttm: float | None
    revenue_ttm: float | None
    gross_profit_ttm: float | None
    quarterly_earnings_growth_yoy: float | None
    quarterly_revenue_growth_yoy: float | None
    analyst_target_price: float | None
    analyst_rating_strong_buy: float | None
    analyst_rating_buy: float | None
    analyst_rating_hold: float | None
    analyst_rating_sell: float | None
    analyst_rating_strong_sell: float | None
    trailing_pe: float | None
    forward_pe: float | None
    price_to_sales_ratio_ttm: float | None
    price_to_book_ratio: float | None
    ev_to_revenue: float | None
    ev_to_ebitda: float | None
    beta: float | None
    fetched_at: str

@dataclass(frozen=True)
class IncomeStatementRecord:
    symbol: str
    fiscal_date_ending: str
    report_type: str
    reported_currency: str | None
    gross_profit: float | None
    total_revenue: float | None
    cost_of_revenue: float | None
    cost_of_goods_and_services_sold: float | None
    operating_income: float | None
    selling_general_and_administrative: float | None
    research_and_development: float | None
    operating_expenses: float | None
    net_income: float | None
    interest_income: float | None
    interest_expense: float | None
    income_before_tax: float | None
    income_tax_expense: float | None
    ebit: float | None
    ebitda: float | None
    depreciation_and_amortization: float | None
    fetched_at: str

@dataclass(frozen=True)
class BalanceSheetRecord:
    symbol: str
    fiscal_date_ending: str
    report_type: str
    reported_currency: str | None
    total_assets: float | None
    total_current_assets: float | None
    cash_and_equivalents: float | None
    cash_and_short_term_investments: float | None
    inventory: float | None
    current_net_receivables: float | None
    total_non_current_assets: float | None
    property_plant_equipment: float | None
    intangible_assets: float | None
    goodwill: float | None
    investments: float | None
    long_term_investments: float | None
    short_term_investments: float | None
    total_liabilities: float | None
    total_current_liabilities: float | None
    current_long_term_debt: float | None
    short_term_debt: float | None
    current_accounts_payable: float | None
    total_non_current_liabilities: float | None
    long_term_debt: float | None
    total_shareholder_equity: float | None
    retained_earnings: float | None
    common_stock: float | None
    common_stock_shares_outstanding: float | None
    fetched_at: str

@dataclass(frozen=True)
class CashFlowRecord:
    symbol: str
    fiscal_date_ending: str
    report_type: str
    reported_currency: str | None
    operating_cashflow: float | None
    payments_for_operating_activities: float | None
    change_in_operating_liabilities: float | None
    change_in_operating_assets: float | None
    depreciation_depletion_and_amortization: float | None
    capital_expenditures: float | None
    change_in_receivables: float | None
    change_in_inventory: float | None
    profit_loss: float | None
    cashflow_from_investment: float | None
    cashflow_from_financing: float | None
    dividend_payout: float | None
    proceeds_from_repurchase_of_equity: float | None
    proceeds_from_issuance_of_long_term_debt: float | None
    payments_for_repurchase_of_common_stock: float | None
    change_in_cash_and_equivalents: float | None
    net_income: float | None
    fetched_at: str

@dataclass(frozen=True)
class EarningsRecord:
    symbol: str
    fiscal_date_ending: str
    period_type: str
    reported_date: str | None
    reported_eps: float | None
    estimated_eps: float | None
    surprise: float | None
    surprise_percentage: float | None
    fetched_at: str

@dataclass(frozen=True)
class EconomicIndicatorRecord:
    indicator: str
    date: str
    value: float | None
    interval: str
    maturity: str
    fetched_at: str

@dataclass(frozen=True)
class ForexDailyRecord:
    from_currency: str
    to_currency: str
    date: str
    open: float
    high: float
    low: float
    close: float
    fetched_at: str
```

---

## 6. storage.py — AlphaVantageStorage

PolymarketStorage パターンに従い:

### コンストラクタ

```python
def __init__(self, db_path: Path | None = None) -> None:
    path = db_path or _resolve_db_path()
    self._client = SQLiteClient(path)
    self.ensure_tables()
```

### ファクトリ関数

```python
def get_alphavantage_storage(db_path: Path | None = None) -> AlphaVantageStorage:
    """AlphaVantageStorage インスタンスを生成する。

    lru_cache は使用しない（テスト時のグローバル状態共有を回避）。
    PolymarketStorage の get_polymarket_storage() パターンに合わせる。
    """
    return AlphaVantageStorage(db_path=db_path)
```

### DDL 管理

```python
_TABLE_DDL: dict[str, str] = {
    TABLE_DAILY_PRICES: "CREATE TABLE IF NOT EXISTS ...",
    TABLE_COMPANY_OVERVIEW: "CREATE TABLE IF NOT EXISTS ...",
    # ... 8テーブル分
}
```

### メソッド一覧

| メソッド | 入力 | 出力 |
|---|---|---|
| `ensure_tables()` | — | `None` |
| `upsert_daily_prices(records)` | `list[DailyPriceRecord]` | `int` (行数) |
| `upsert_company_overview(record)` | `CompanyOverviewRecord` | `int` |
| `upsert_income_statements(records)` | `list[IncomeStatementRecord]` | `int` |
| `upsert_balance_sheets(records)` | `list[BalanceSheetRecord]` | `int` |
| `upsert_cash_flows(records)` | `list[CashFlowRecord]` | `int` |
| `upsert_earnings(records)` | `list[EarningsRecord]` | `int` |
| `upsert_economic_indicators(records)` | `list[EconomicIndicatorRecord]` | `int` |
| `upsert_forex_daily(records)` | `list[ForexDailyRecord]` | `int` |
| `get_daily_prices(symbol, start_date?, end_date?)` | `str`, `str?`, `str?` | `pd.DataFrame` |
| `get_company_overview(symbol)` | `str` | `CompanyOverviewRecord \| None` |
| `get_income_statements(symbol, report_type?)` | `str`, `str?` | `pd.DataFrame` |
| `get_balance_sheets(symbol, report_type?)` | `str`, `str?` | `pd.DataFrame` |
| `get_cash_flows(symbol, report_type?)` | `str`, `str?` | `pd.DataFrame` |
| `get_earnings(symbol, period_type?)` | `str`, `str?` | `pd.DataFrame` |
| `get_economic_indicator(indicator, interval?, maturity?)` | `str`, `str?`, `str?` | `pd.DataFrame` |
| `get_forex_daily(from_c, to_c, start_date?, end_date?)` | `str`, `str`, `str?`, `str?` | `pd.DataFrame` |
| `get_table_names()` | — | `list[str]` |
| `get_row_count(table_name)` | `str` | `int` |

### マイグレーション

EdinetStorage の `_migrate_add_missing_columns()` パターンを踏襲。
Alpha Vantage API がフィールドを追加した場合に `ALTER TABLE ADD COLUMN` で対応。

```python
def _migrate_if_needed(self) -> None:
    """Add new columns if table schema evolves."""
    # ALTER TABLE only if column doesn't exist
```

---

## 7. collector.py — AlphaVantageCollector

API取得 → camelCase→snake_case 変換 → dataclass 生成 → Storage upsert のパイプライン。

### camelCase → snake_case 変換戦略

```python
# 特殊マッピング辞書（数字先頭や略語）
_SPECIAL_KEY_MAP: dict[str, str] = {
    "52WeekHigh": "week_52_high",
    "52WeekLow": "week_52_low",
    "50DayMovingAverage": "day_50_moving_average",
    "200DayMovingAverage": "day_200_moving_average",
    "MarketCapitalization": "market_capitalization",
    "PERatio": "pe_ratio",
    "PEGRatio": "peg_ratio",
    "EPS": "eps",
    "EBITDA": "ebitda",
    # ... 完全なマッピング
}

def _camel_to_snake(key: str) -> str:
    """camelCase/PascalCase キーを snake_case に変換。
    特殊キーは辞書で対応。汎用キーは正規表現で変換。
    """
    if key in _SPECIAL_KEY_MAP:
        return _SPECIAL_KEY_MAP[key]
    # 汎用変換: fiscalDateEnding → fiscal_date_ending
    s = re.sub(r"([A-Z]+)([A-Z][a-z])", r"\1_\2", key)
    s = re.sub(r"([a-z\d])([A-Z])", r"\1_\2", s)
    return s.lower()
```

### クラス定義

```python
class AlphaVantageCollector:
    def __init__(
        self,
        client: AlphaVantageClient | None = None,
        storage: AlphaVantageStorage | None = None,
    ) -> None:
        self._client = client or AlphaVantageClient()
        self._storage = storage or get_alphavantage_storage()

    def collect_daily(self, symbol: str, outputsize: OutputSize = OutputSize.COMPACT) -> CollectionResult:
        """日次OHLCVを取得して保存"""

    def collect_company_overview(self, symbol: str) -> CollectionResult:
        """企業プロファイルを取得して保存"""

    def collect_income_statements(self, symbol: str) -> CollectionResult:
        """損益計算書（annual + quarterly）を取得して保存"""

    def collect_balance_sheets(self, symbol: str) -> CollectionResult:
        """貸借対照表（annual + quarterly）を取得して保存"""

    def collect_cash_flows(self, symbol: str) -> CollectionResult:
        """キャッシュフロー（annual + quarterly）を取得して保存"""

    def collect_earnings(self, symbol: str) -> CollectionResult:
        """決算EPS（annual + quarterly）を取得して保存"""

    def collect_economic_indicators(self) -> list[CollectionResult]:
        """全マクロ指標を一括取得して保存（6種）"""

    def collect_forex_daily(self, from_currency: str, to_currency: str) -> CollectionResult:
        """為替日次データを取得して保存"""

    def collect_all(self, symbols: list[str]) -> CollectionSummary:
        """複数銘柄のデータを一括収集"""
```

### 結果型

```python
@dataclass(frozen=True)
class CollectionResult:
    symbol: str
    table: str
    rows_upserted: int
    success: bool
    error_message: str | None = None

@dataclass(frozen=True)
class CollectionSummary:
    results: list[CollectionResult]
    total_symbols: int
    successful_symbols: int
    failed_symbols: int
    total_rows_upserted: int
```

### エラーハンドリング

- API エラー（レート制限、認証等）: `CollectionResult(success=False, error_message=...)` で返却、処理を継続
- パースエラー: 同上
- DB エラー: ログ出力 + `CollectionResult(success=False)` で返却
- `collect_all()` は partial success をサポート（一部銘柄の失敗で全体を止めない）

---

## 8. テスト計画

| テストファイル | 対象 | 種別 |
|---|---|---|
| `tests/market/alphavantage/unit/test_storage_constants.py` | 定数の値・型・プレフィックス | unit |
| `tests/market/alphavantage/unit/test_models.py` | dataclass 生成・frozen・フィールド数 | unit |
| `tests/market/alphavantage/unit/test_storage.py` | DDL実行、upsert、get、マイグレーション | unit |
| `tests/market/alphavantage/unit/test_collector.py` | パイプライン、camelCase変換、エラーハンドリング | unit |
| `tests/market/alphavantage/property/test_storage_property.py` | upsert冪等性、PK制約、NaN/None処理 | property |
| `tests/market/alphavantage/integration/test_storage_integration.py` | 実DB操作、collect→get ラウンドトリップ | integration |

### 主要テストケース

- `test_正常系_upsert冪等性でレコード数が変わらない`
- `test_正常系_同一PKで最新データに上書きされる`
- `test_正常系_get_daily_pricesで日付範囲フィルタが機能する`
- `test_正常系_company_overviewの全42カラムが保存される`
- `test_正常系_economic_indicatorのmaturityが区別される`
- `test_異常系_NaN値がNoneに変換される`
- `test_異常系_API失敗でCollectionResult_successがFalse`
- `test_エッジケース_空のDataFrameで0行upsert`
- `test_プロパティ_任意のシンボルでupsert→getラウンドトリップ`

---

## 9. 既存コードへの影響

- `__init__.py`: `AlphaVantageStorage`, `AlphaVantageCollector`, `get_alphavantage_storage` を追加
- `client.py`: 変更なし（Collector が client を使う）
- 他パッケージへの影響なし

---

## 10. 実装順序（Wave分割）

| Wave | ファイル | 内容 |
|---|---|---|
| 1 | `storage_constants.py` + テスト | テーブル名定数、DB設定 |
| 2 | `models.py` + テスト | 8つの frozen dataclass |
| 3 | `storage.py` + テスト | DDL + ensure_tables + upsert + get |
| 4 | `collector.py` + テスト | camelCase変換 + API→Storage パイプライン |
| 5 | `__init__.py` 更新 + 統合テスト | 公開API追加 + ラウンドトリップテスト |
