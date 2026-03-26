# Market.nasdaq Package Architecture & Extension Patterns

**Status**: COMPLETED EXPLORATION  
**Date**: 2026-03-24  
**Scope**: Full read-only analysis of `/Users/yukihata/Desktop/quants/src/market/nasdaq/`

---

## Executive Summary

The `market.nasdaq` package is a production-grade financial data collector implementing the NASDAQ Stock Screener API. It demonstrates sophisticated patterns for:

- **Bot-blocking countermeasures** (TLS fingerprint impersonation, User-Agent rotation, exponential backoff)
- **Dependency injection** for testability (optional session parameter)
- **Declarative configuration** via frozen dataclasses
- **Type-safe filtering** using string enums
- **Numeric data cleaning** with missing-value handling
- **Security hardening** (SSRF prevention, path traversal validation)

---

## Package Architecture

### Core Components

```
market.nasdaq/
├── __init__.py           # Public API exports (56 lines)
├── collector.py          # ScreenerCollector implementation (531 lines)
├── session.py            # NasdaqSession HTTP client (410 lines)
├── parser.py             # JSON parsing + numeric cleaning (544 lines)
├── constants.py          # Defaults, headers, mappings (205 lines)
├── errors.py             # Exception hierarchy (210 lines)
├── types.py              # Enums, configs, dataclasses (524 lines)
└── README.md             # User documentation (457 lines)
```

### Data Flow

```
External API Call
    ↓
NasdaqSession.get_with_retry()
    ├─ Polite delay (1.0s + 0-0.5s jitter)
    ├─ Random User-Agent rotation (12 browser strings)
    ├─ Host whitelist validation (SSRF prevention)
    ├─ Exponential backoff retry (max 3 attempts)
    └─ Session rotation on rate limit (403/429)
    ↓
JSON Response
    ↓
parse_screener_response()
    ├─ Extract data.table.rows
    ├─ Rename columns (camelCase → snake_case)
    └─ Apply numeric cleaning (price, %, market_cap, volume, IPO year)
    ↓
pd.DataFrame (12 columns, cleaned numeric values)
```

---

## Class Hierarchy & Interfaces

### ScreenerCollector (Main Entry Point)

**Implements**: `DataCollector` ABC  
**Location**: `collector.py` (lines 1-531)

```python
class ScreenerCollector(DataCollector):
    def fetch(self, **kwargs) -> pd.DataFrame:
        """Fetch stock screener data with optional filter"""
        
    def validate(self, df: pd.DataFrame) -> bool:
        """Validate required columns (symbol, name)"""
        
    def fetch_by_category(
        self, 
        category: FilterCategory,
        *,
        base_filter: ScreenerFilter | None = None
    ) -> dict[str, pd.DataFrame]:
        """Bulk fetch across enum members (Exchange, Sector, etc.)"""
        
    def download_csv(
        self,
        filter: ScreenerFilter | None = None,
        *,
        output_dir: str | Path = "data/raw/nasdaq",
        filename: str | None = None
    ) -> Path:
        """Save filtered data to CSV (utf-8-sig encoding)"""
        
    def download_by_category(
        self,
        category: FilterCategory,
        *,
        output_dir: str | Path = "data/raw/nasdaq",
        base_filter: ScreenerFilter | None = None
    ) -> list[Path]:
        """Save category-wise CSVs (pattern: {category}_{value}_{YYYY-MM-DD}.csv)"""
```

**Key Design Patterns**:

1. **Dependency Injection**: Optional `session` parameter in `__init__`
   ```python
   def __init__(self, session: NasdaqSession | None = None):
       self._session = session
       # Allows injection of mock sessions in tests
   ```

2. **Helper Method**: `_get_session() → tuple[NasdaqSession, bool]`
   - Returns `(session, should_close)` flag
   - Enables resource cleanup in `with` blocks

3. **Declarative Field Mapping**: `_CATEGORY_FIELD_MAP`
   ```python
   _CATEGORY_FIELD_MAP: dict[type[FilterCategory], str] = {
       Exchange: "exchange",
       MarketCap: "marketcap",
       Sector: "sector",
       Recommendation: "recommendation",
       Region: "region",
   }
   ```
   - Eliminates if/elif chains
   - Type-safe category → API field mapping

4. **Path Traversal Prevention**: `is_relative_to()` validation
   ```python
   output_path = (Path(output_dir) / filename).resolve()
   if not output_path.is_relative_to(Path(output_dir).resolve()):
       raise ValueError(f"Path traversal detected: {output_path}")
   ```

---

## DataCollector ABC Interface

**Location**: `market/base_collector.py` (209 lines)

```python
class DataCollector(ABC):
    @property
    def name(self) -> str:
        """Returns class name for logging"""
        return self.__class__.__name__
    
    @abstractmethod
    def fetch(**kwargs) -> pd.DataFrame:
        """Fetch raw data from external source"""
    
    @abstractmethod
    def validate(df: pd.DataFrame) -> bool:
        """Validate required columns and data quality"""
    
    def collect(**kwargs) -> pd.DataFrame:
        """Convenience: fetch + validate with logging"""
        # Logs "Starting fetch: ScreenerCollector"
        # Logs "Validation passed: 3500 rows"
        # Raises ValueError if validation fails
```

---

## HTTP Session Management (NasdaqSession)

**Location**: `session.py` (410 lines)

### Bot-Blocking Countermeasures

1. **TLS Fingerprint Impersonation** (curl_cffi)
   ```python
   session = curl_requests.Session(impersonate="chrome")
   # Targets: ["chrome", "chrome110", "chrome120", "edge99", "safari15_3"]
   ```

2. **User-Agent Rotation** (12 real browser strings)
   ```python
   DEFAULT_USER_AGENTS = (
       "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
       # ... 11 more
   )
   ```

3. **Polite Delay**
   ```python
   delay = config.polite_delay + random.uniform(0, config.delay_jitter)
   # Default: 1.0s + 0-0.5s jitter
   time.sleep(delay)
   ```

4. **Exponential Backoff with Session Rotation**
   ```python
   for attempt in range(max_attempts):
       try:
           return self.get(url, params)
       except NasdaqRateLimitError:
           delay = min(
               initial_delay * (exponential_base ** attempt),
               max_delay
           )
           time.sleep(delay)
           self.rotate_session()  # New TLS fingerprint
   ```

5. **SSRF Prevention** (Host Whitelist)
   ```python
   ALLOWED_HOSTS = frozenset({"api.nasdaq.com"})
   
   parsed_host = urlparse(url).netloc
   if parsed_host not in ALLOWED_HOSTS:
       raise ValueError(f"Host '{parsed_host}' not allowed")
   ```

### Configuration Classes

**NasdaqConfig** (frozen dataclass):
```python
@dataclass(frozen=True)
class NasdaqConfig:
    polite_delay: float = 1.0           # 0.0-60.0s range
    delay_jitter: float = 0.5           # 0.0-30.0s range
    impersonate: str = "chrome"         # Browser fingerprint
    timeout: float = 30.0               # 1.0-300.0s range
    user_agents: tuple[str, ...] | None = None
```

**RetryConfig** (frozen dataclass):
```python
@dataclass(frozen=True)
class RetryConfig:
    max_attempts: int = 3               # 1-10 range
    initial_delay: float = 1.0
    max_delay: float = 30.0
    exponential_base: float = 2.0
    jitter: bool = True
```

---

## Type-Safe Filtering System

**Location**: `types.py` (524 lines)

### Filter Enums (String-based for API compatibility)

```python
class Exchange(str, Enum):
    NASDAQ = "nasdaq"
    NYSE = "nyse"
    AMEX = "amex"

class MarketCap(str, Enum):
    MEGA = "megacap"           # > $300B
    LARGE = "largecap"         # $10B - $300B
    MID = "midcap"             # $2B - $10B
    SMALL = "smallcap"         # $300M - $2B
    MICRO = "microcap"         # < $300M
    NANO = "nanocap"           # Nano cap stocks

class Sector(str, Enum):
    # 11 sectors: TECHNOLOGY, HEALTH_CARE, FINANCE, etc.

class Recommendation(str, Enum):
    STRONG_BUY = "strongbuy"
    BUY = "buy"
    HOLD = "hold"
    SELL = "sell"
    STRONG_SELL = "strongsell"

class Region(str, Enum):
    # 8 regions: AFRICA, ASIA, EUROPE, etc.

class Country(str, Enum):
    # Representative subset of 40+
    # Accepts str directly for unlisted countries
```

### ScreenerFilter (Frozen Dataclass)

```python
@dataclass(frozen=True)
class ScreenerFilter:
    exchange: Exchange | None = None
    marketcap: MarketCap | None = None
    sector: Sector | None = None
    recommendation: Recommendation | None = None
    region: Region | None = None
    limit: int | None = 0  # 0 = all records
    
    def to_params(self) -> dict[str, str]:
        """Convert to API query parameters (only non-None fields)"""
        params = {}
        for field, value in asdict(self).items():
            if value is not None:
                if isinstance(value, Enum):
                    params[field] = value.value
                else:
                    params[field] = str(value)
        return params
```

**FilterCategory Type Alias**:
```python
FilterCategory = Exchange | MarketCap | Sector | Recommendation | Region
```

---

## JSON Response Parsing & Numeric Cleaning

**Location**: `parser.py` (544 lines)

### Cleaner Factory Pattern

```python
def _create_cleaner[T](
    *,
    converter: Callable[[str], T],
    name: str,
    strip_chars: str = "",
    finite_check: bool = False,
) -> Callable[[str], T | None]:
    """Generate type-safe cleaning function with common pattern"""
    
    def _clean(value: str) -> T | None:
        if _is_missing(value):  # "", "N/A", "NA", "n/a"
            return None
        
        try:
            cleaned = strip_re.sub("", value).strip() if strip_re else value.strip()
            if not cleaned:
                return None
            
            if finite_check:
                float_result = float(cleaned)
                if not math.isfinite(float_result):
                    logger.warning(f"Non-finite {name}")
                    return None
                return converter(str(float_result))
            
            return converter(cleaned)
        except (ValueError, TypeError, OverflowError):
            logger.warning(f"Failed to parse {name}", raw_value=value)
            return None
    
    return _clean
```

### Generated Cleaners

```python
clean_price = _create_cleaner(
    converter=float,
    name="price",
    strip_chars="$,",
    finite_check=True,
)
# "$1,234.56" → 1234.56

clean_percentage = _create_cleaner(
    converter=float,
    name="percentage",
    strip_chars="%,",
    finite_check=True,
)
# "-0.849%" → -0.849 (NOT divided by 100)

clean_market_cap = _create_cleaner(
    converter=_float_to_int,
    name="market cap",
    strip_chars="$,",
    finite_check=True,
)
# "3,435,123,456,789" → 3435123456789

clean_volume = _create_cleaner(
    converter=_float_to_int,
    name="volume",
    strip_chars=",",
    finite_check=True,
)
# "48,123,456" → 48123456

clean_ipo_year = _create_cleaner(
    converter=int,
    name="IPO year",
    strip_chars="",
    finite_check=False,
)
# "1980" → 1980
```

### Response Parsing

```python
def parse_screener_response(response: dict[str, Any]) -> pd.DataFrame:
    """Parse JSON → cleaned DataFrame"""
    
    # Validate structure
    data = response.get("data")
    table = data.get("table")
    rows = table.get("rows")
    
    if not isinstance(rows, list):
        raise NasdaqParseError("Invalid rows key", field="data.table.rows")
    
    # Create DataFrame
    df = pd.DataFrame(rows)
    
    # Rename columns (camelCase → snake_case)
    rename_map = {}
    for col in df.columns:
        mapped = COLUMN_NAME_MAP.get(col)
        rename_map[col] = mapped if mapped else _camel_to_snake(col)
    
    df = df.rename(columns=rename_map)
    
    # Apply numeric cleaning
    for column, cleaner in _COLUMN_CLEANERS.items():
        if column in df.columns:
            df[column] = df[column].apply(
                lambda v, c=cleaner: c(str(v)) if pd.notna(v) else None
            )
    
    return df
```

---

## Exception Hierarchy

**Location**: `errors.py` (210 lines)

```python
NasdaqError (base, direct Exception inheritance)
├── NasdaqAPIError
│   ├── url: str
│   ├── status_code: int
│   └── response_body: str
├── NasdaqRateLimitError
│   ├── url: str | None
│   └── retry_after: int | None
└── NasdaqParseError
    ├── raw_data: str | None
    └── field: str | None
```

**Rate Limit Detection**:
```python
_BLOCKED_STATUS_CODES = frozenset({403, 429})

if response.status_code in _BLOCKED_STATUS_CODES:
    raise NasdaqRateLimitError(
        f"Rate limit detected: HTTP {response.status_code}",
        url=url,
        retry_after=None,
    )
```

---

## Constants & Configuration

**Location**: `constants.py` (205 lines)

```python
NASDAQ_SCREENER_URL = "https://api.nasdaq.com/api/screener/stocks"

DEFAULT_USER_AGENTS = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36...",
    # ... 11 more
)

BROWSER_IMPERSONATE_TARGETS = ["chrome", "chrome110", "chrome120", "edge99", "safari15_3"]

DEFAULT_HEADERS = {
    "User-Agent": "[rotation]",
    "Accept": "application/json",
    "Accept-Language": "en-US,en;q=0.9",
    "Accept-Encoding": "gzip, deflate, br",
}

ALLOWED_HOSTS = frozenset({"api.nasdaq.com"})

DEFAULT_OUTPUT_DIR = "data/raw/nasdaq"

COLUMN_NAME_MAP = {
    "symbol": "symbol",
    "name": "name",
    "lastsale": "last_sale",
    "netchange": "net_change",
    "pctchange": "pct_change",
    "marketCap": "market_cap",
    "country": "country",
    "ipoyear": "ipo_year",
    "volume": "volume",
    "sector": "sector",
    "industry": "industry",
    "url": "url",
}
```

---

## Test Coverage & Patterns

**Location**: `tests/market/nasdaq/unit/test_collector.py` (545 lines)

### Test Organization

```
TestScreenerCollectorInit          # Default/injected initialization
TestGetSession                     # Session creation & cleanup
TestFetch                          # fetch() with/without filter, error propagation
TestValidate                       # Empty/valid/malformed DataFrames
TestFetchByCategory                # Category-wise bulk fetch, polite delays
TestDownloadCsv                    # CSV persistence, utf-8-sig BOM
TestDownloadByCategory             # Category-based filename pattern
TestPathTraversalProtection        # SSRF/path traversal validation
TestBuildCategoryFilter            # _CATEGORY_FIELD_MAP coverage
```

### Mock Patterns

```python
def _make_api_response() -> dict[str, Any]:
    """Mock NASDAQ API response structure"""
    return {
        "data": {
            "table": {
                "rows": [
                    {"symbol": "AAPL", "name": "Apple Inc.", ...},
                ]
            }
        }
    }

def _make_mock_session() -> MagicMock:
    """Mock NasdaqSession with get_with_retry response"""
    session = MagicMock()
    session.get_with_retry.return_value = MagicMock(
        json=lambda: _make_api_response()
    )
    return session
```

### Key Test Cases

1. **Polite Delay Verification**: Uses `patch('time.sleep')` to verify `sleep()` calls
2. **Path Traversal**: Tests `ValueError` for `../../../etc/passwd`, `/tmp/evil.csv`
3. **Category Mapping**: Asserts `_CATEGORY_FIELD_MAP` covers all 5 FilterCategory types
4. **CSV Encoding**: Verifies utf-8-sig BOM (bytes `EF BB BF`)
5. **Filename Patterns**: Tests `{category}_{value}_{YYYY-MM-DD}.csv` format

---

## Extension Patterns

### Pattern 1: Add New Enum Filter Category

```python
# In types.py
class IndustryGroup(str, Enum):
    SOFTWARE = "software"
    HARDWARE = "hardware"
    # ...

# In collector.py
_CATEGORY_FIELD_MAP[IndustryGroup] = "industryGroup"
```

### Pattern 2: Add Custom Numeric Cleaner

```python
# In parser.py
clean_earnings = _create_cleaner(
    converter=float,
    name="earnings per share",
    strip_chars="$",
    finite_check=True,
)

_COLUMN_CLEANERS["earnings_per_share"] = clean_earnings
```

### Pattern 3: Create Specialized Collector

```python
# Inherit DataCollector, implement fetch/validate
class NasdaqTrendingCollector(DataCollector):
    def __init__(self, session: NasdaqSession | None = None):
        self._session = session
    
    def fetch(self, **kwargs) -> pd.DataFrame:
        session, should_close = self._get_session()
        try:
            response = session.get_with_retry(
                "https://api.nasdaq.com/api/screener/trending",
                params={"sort": "percentChange"}
            )
            return parse_trending_response(response.json())
        finally:
            if should_close:
                session.close()
    
    def validate(self, df: pd.DataFrame) -> bool:
        return not df.empty and "symbol" in df.columns
```

### Pattern 4: Custom Session Configuration

```python
config = NasdaqConfig(
    polite_delay=2.0,
    delay_jitter=1.0,
    timeout=60.0,
    impersonate="chrome120",
)
session = NasdaqSession(config=config)
collector = ScreenerCollector(session=session)
```

---

## Security & Robustness

### SSRF Prevention
- **Whitelist-based**: Only `api.nasdaq.com` allowed
- **Runtime check**: `urlparse(url).netloc` validation before request

### Path Traversal Prevention
- **is_relative_to()**: Output path must be relative to output_dir
- **resolve()**: Both paths converted to absolute before comparison
- **CWE-22**: Documented in docstring

### Rate Limit Handling
- **Detection**: HTTP 403/429 → `NasdaqRateLimitError`
- **Backoff**: Exponential with optional jitter
- **Session Rotation**: New TLS fingerprint on retry
- **Fail-fast**: Immediate error propagation from `fetch_by_category()`

### Numeric Data Validation
- **Finiteness check**: Rejects inf/-inf/nan values
- **Type safety**: Explicit converters (float/int) prevent silent errors
- **Missing value handling**: Empty strings, "N/A" normalized to None

---

## Public API Surface

**Location**: `__init__.py` (56 lines)

```python
# Collectors
ScreenerCollector

# HTTP Session
NasdaqSession

# Filters & Configuration
ScreenerFilter
Exchange, MarketCap, Sector, Recommendation, Region, Country

# Configuration Classes
NasdaqConfig
RetryConfig

# Exception Hierarchy
NasdaqError
NasdaqAPIError
NasdaqRateLimitError
NasdaqParseError
```

---

## DataFrame Output Schema

**Columns** (12 total):
```
symbol          : str       # Stock ticker
name            : str       # Company name
last_sale       : float     # Current price
net_change      : float     # Absolute change
pct_change      : float     # Percentage change (not divided by 100)
market_cap      : int       # Market capitalization
country         : str       # Company country
ipo_year        : int       # IPO year
volume          : int       # Trading volume
sector          : str       # Sector classification
industry        : str       # Industry classification
url             : str       # NASDAQ profile URL
```

---

## Dependencies & Integrations

**External Dependencies**:
- `curl_cffi`: TLS fingerprint impersonation
- `pandas`: DataFrame operations
- `requests` (from curl_cffi): HTTP response handling

**Internal Dependencies**:
- `market.base_collector`: DataCollector ABC
- `market.errors`: Shared error base classes
- `utils_core.logging`: Structured logging

**Related Collectors** (Same Package):
- `market.yfinance`: Yahoo Finance data
- `market.fred`: Federal Reserve Economic Data
- `market.etfcom`: ETF.com scraper
- `market.edinet`: Japanese financial disclosures
- `market.eodhd`: Global financial data

---

## Key Design Decisions

| Decision | Rationale |
|----------|-----------|
| **Frozen dataclasses** | Immutability ensures config cannot be accidentally mutated |
| **String Enums** | Direct API value compatibility without conversion layer |
| **Dependency injection** | Session parameter enables mock injection for testing |
| **Polite delays** | Respect API rate limits; reduce bot detection risk |
| **TLS fingerprint rotation** | Impersonate real browsers; avoid blocking |
| **Path traversal validation** | Prevent arbitrary file writes when output_dir is user-provided |
| **Numeric cleaning factory** | DRY principle; consistent error handling across 5+ numeric types |
| **Missing value normalization** | Unified handling of empty strings, "N/A", "NA", "n/a" |
| **Category field mapping** | Type-safe declarative dispatch vs if/elif chains |
| **utf-8-sig encoding** | Excel compatibility (BOM prevents corruption) |

---

## Known Limitations & Caveats

1. **Single-threaded**: No async support; suitable for batch operations
2. **Rate limit**: Free plan limited to ~100 requests/min; exponential backoff helps but not guaranteed
3. **Data freshness**: Real-time data 15+ min delayed (stock market standard)
4. **Exchange coverage**: NASDAQ, NYSE, AMEX only (no international exchanges)
5. **Market hours**: Data only updated during US market hours
6. **Column subset**: Only 12 columns returned; full NASDAQ profile has more data
7. **Numeric precision**: Float/int conversions may lose precision for very large numbers

---

## Recommended Next Steps

1. **Add new data source**: Follow `ScreenerCollector` pattern for API integration
2. **Extend filter system**: Add new `FilterCategory` enums for additional API parameters
3. **Enhance numeric cleaning**: Add domain-specific cleaners (P/E ratio, dividend yield, etc.)
4. **Async support**: Refactor `NasdaqSession` to use `httpx.AsyncClient` for concurrent requests
5. **Caching layer**: Add local SQLite cache to reduce API calls during development
6. **Alternative session backends**: Support `aiohttp`, `requests`, `httpx` alongside `curl_cffi`

---

**End of Plan**

All files referenced in this plan are verified to exist in the repository as of 2026-03-24.
