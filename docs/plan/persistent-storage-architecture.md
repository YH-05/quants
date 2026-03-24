# Persistent Storage Architecture Analysis

**Date**: 2026-03-23
**Scope**: Complete exploration of database backends, storage patterns, and persistence mechanisms across the quants codebase

---

## Executive Summary

The project implements a **hybrid persistence architecture** with three distinct layers:

1. **TTL-Based Cache Layer** (SQLiteCache): API response caching with automatic expiration
2. **Domain-Specific Storage Classes**: Persistent table management with DDL and schema validation
3. **File-Based Storage**: JSON serialization for configuration and metadata

Key insight: **No generic "repository" pattern exists**. Instead, each data domain (market.edinet, market.asean_common, rss) implements its own storage class tailored to its specific requirements.

---

## 1. Database Backends Supported

### 1.1 SQLite

**Location**: `src/database/db/sqlite_client.py`

**Purpose**: Transactional, row-oriented database for structured data with ACID guarantees

**Key Features**:
- Context manager-based connection management (`__enter__`, `__exit__`)
- Thread-local connection pools for per-thread isolation
- Row factory for named tuple access
- Methods: `execute()`, `execute_many()`, `execute_script()`, `get_tables()`

**Connection Strategy**:
```python
class SQLiteClient:
    def __init__(self, path: Path):
        self._path = path
        self._thread_local = threading.local()

    def _get_connection(self):
        if not hasattr(self._thread_local, 'connection'):
            self._thread_local.connection = sqlite3.connect(str(self._path))
            self._thread_local.connection.row_factory = sqlite3.Row
        return self._thread_local.connection
```

**Use Cases**:
- Market data cache (TTL-based)
- EDINET disclosure data (companies, financials, ratios, text_blocks)
- Transactional workloads requiring ACID properties

**Database Path Resolution** (`src/database/db/connection.py`):
```python
def get_db_path(db_type: DatabaseType, name: str) -> Path:
    data_dir = get_data_dir()
    if db_type == "sqlite":
        return data_dir / "sqlite" / f"{name}.db"
    return data_dir / "duckdb" / f"{name}.duckdb"
```

Priority for `get_data_dir()`:
1. `DATA_DIR` environment variable (if set and non-empty)
2. Current working directory + `/data` (if exists)
3. Fallback: `PROJECT_ROOT / "data"`

---

### 1.2 DuckDB

**Location**: `src/database/db/duckdb_client.py`

**Purpose**: Columnar OLAP database optimized for analytical queries

**Key Features**:
- DataFrame-native integration (`query_df()`, `store_df()`)
- Parquet query interoperability
- Upsert support via `store_df(if_exists="upsert", key_columns=[...])`
- SQL identifier validation to prevent injection

**Core Methods**:
```python
class DuckDBClient:
    def store_df(
        self,
        df: pd.DataFrame,
        table_name: str,
        if_exists: Literal["append", "replace", "upsert"] = "append",
        key_columns: list[str] | None = None,
    ) -> int:
        """Upsert pattern: DELETE matching rows, then INSERT new rows"""
        if if_exists == "upsert" and key_columns:
            # Delete existing rows matching key_columns
            # INSERT OR REPLACE new rows
```

**Use Cases**:
- ASEAN ticker master data (asean_tickers table)
- Analytical queries joining ticker masters with OHLCV price series
- Schema validation with pandera

---

## 2. Persistent Storage Patterns

### 2.1 Pattern 1: TTL-Based Cache (SQLiteCache)

**Location**: `src/market/cache/cache.py`

**Purpose**: Persistent API response caching with automatic expiration

**Schema**:
```sql
CREATE TABLE cache (
    key TEXT PRIMARY KEY,
    value BLOB NOT NULL,
    value_type TEXT NOT NULL,
    created_at REAL NOT NULL,
    expires_at REAL,
    metadata TEXT
)
```

**Key Operations**:

**Set with TTL**:
```python
def set(self, key: str, value: Any, ttl_seconds: int | None = None) -> None:
    now = time.time()
    expires_at = now + ttl_seconds if ttl_seconds else None

    serialized = self._serialize(value)
    conn = self._get_connection()
    conn.execute(
        "INSERT OR REPLACE INTO cache ...",
        (key, serialized, type(value).__name__, now, expires_at, metadata)
    )
```

**Get with Expiration Check**:
```python
def get(self, key: str) -> Any | None:
    row = conn.execute(
        "SELECT value, value_type, expires_at FROM cache WHERE key = ?",
        (key,)
    ).fetchone()

    if row and (row['expires_at'] is None or row['expires_at'] > time.time()):
        return self._deserialize(row['value'], row['value_type'])
    return None
```

**Cleanup**:
```python
def cleanup_expired(self) -> int:
    now = time.time()
    cursor = conn.execute(
        "DELETE FROM cache WHERE expires_at IS NOT NULL AND expires_at <= ?",
        (now,)
    )
    return cursor.rowcount
```

**Serialization Strategy**:
- **Pandas objects** (DataFrame, Series): `pickle` serialization
- **Dict/List**: `json` serialization
- **Fallback**: `str()` conversion

**Thread Safety**: `threading.Lock()` protects cache operations

**TTL Constants** (by domain):
```python
# src/market/jquants/cache.py
JQUANTS_DAILY_TTL = 86400  # 1 day
JQUANTS_WEEKLY_TTL = 604800  # 7 days

# src/market/fred/cache.py
FRED_DAILY_TTL = 86400  # 1 day
```

---

### 2.2 Pattern 2: Domain-Specific Storage Classes

#### 2.2.1 EdinetStorage (SQLite)

**Location**: `src/market/edinet/storage.py`

**Purpose**: Persistent storage for Japanese EDINET disclosure data

**Responsibility**: Manage 6 SQLite tables with DDL initialization and idempotent upserts

**Tables Managed**:

| Table | Primary Key | Purpose |
|-------|-------------|---------|
| `companies` | `edinet_code` | Company master data |
| `financials` | `(edinet_code, fiscal_year, period)` | Financial metrics |
| `ratios` | `(edinet_code, fiscal_year, period)` | Calculated ratios |
| `text_blocks` | `(edinet_code, fiscal_year, period, block_id)` | Disclosure text |
| `industries` | `edinet_code` | Industry classification |
| `industry_details` | `(edinet_code, industry_code)` | Detailed industry mapping |

**Example DDL**:
```python
_COMPANIES_DDL = f"""
    CREATE TABLE IF NOT EXISTS {TABLE_COMPANIES} (
        edinet_code TEXT NOT NULL,
        sec_code TEXT NOT NULL,
        name TEXT NOT NULL,
        industry TEXT NOT NULL,
        name_en TEXT,
        name_ja TEXT,
        accounting_standard TEXT,
        credit_rating TEXT,
        credit_score INTEGER,
        PRIMARY KEY (edinet_code)
    )
"""
```

**Upsert Pattern** (INSERT OR REPLACE):
```python
def upsert_companies(self, companies: list[CompanyRecord]) -> int:
    tuples = [self._dataclass_to_tuple(c) for c in companies]

    sql = f"""
        INSERT OR REPLACE INTO {TABLE_COMPANIES}
        (edinet_code, sec_code, name, ...)
        VALUES (?, ?, ?, ...)
    """

    self._client.execute_many(sql, tuples)
    return len(tuples)
```

**Schema Initialization**:
```python
def ensure_tables(self) -> None:
    """Create all 6 tables if they don't exist"""
    for ddl in [_COMPANIES_DDL, _FINANCIALS_DDL, ...]:
        self._client.execute(ddl)
```

**Migration Support**:
```python
def _migrate_add_missing_columns(self) -> None:
    """Add new columns if table schema evolves"""
    # ALTER TABLE only if column doesn't exist
```

**Key Design Decisions**:
- **Dataclass-to-tuple conversion**: Efficient serialization without ORM overhead
- **INSERT OR REPLACE**: Idempotent upserts (no duplicate key errors)
- **SQLite choice**: Transactional semantics for financial data with ACID guarantees

---

#### 2.2.2 AseanTickerStorage (DuckDB)

**Location**: `src/market/asean_common/storage.py`

**Purpose**: Persistent storage for ASEAN exchange ticker master data

**Table**:
```sql
CREATE TABLE IF NOT EXISTS asean_tickers (
    ticker VARCHAR NOT NULL,
    name VARCHAR NOT NULL,
    market VARCHAR NOT NULL,
    yfinance_suffix VARCHAR NOT NULL,
    yfinance_ticker VARCHAR NOT NULL,
    sector VARCHAR,
    industry VARCHAR,
    market_cap BIGINT,
    currency VARCHAR,
    is_active BOOLEAN NOT NULL DEFAULT TRUE
)
```

**Primary Key**: Composite `(ticker, market)` via `key_columns` parameter in upsert

**Schema Validation** (pandera):
```python
TICKER_DF_SCHEMA = pa.DataFrameSchema(
    columns={
        "ticker": pa.Column(str, nullable=False),
        "name": pa.Column(str, nullable=False),
        "market": pa.Column(str, nullable=False),
        "yfinance_suffix": pa.Column(str, nullable=False),
        "yfinance_ticker": pa.Column(str, nullable=False),
        "sector": pa.Column(str, nullable=True),
        "industry": pa.Column(str, nullable=True),
        "market_cap": pa.Column("Int64", nullable=True, coerce=True),
        "currency": pa.Column(str, nullable=True),
        "is_active": pa.Column(bool, nullable=False, coerce=True),
    },
    strict=False,
)
```

**Upsert Method**:
```python
def upsert_tickers(self, tickers: list[TickerRecord]) -> int:
    df = self._build_ticker_df(tickers)
    df = TICKER_DF_SCHEMA.validate(df)  # Validate before storage

    self._client.store_df(
        df,
        TABLE_TICKERS,
        if_exists="upsert",
        key_columns=["ticker", "market"],  # Composite key
    )
    return len(tickers)
```

**DataFrame Construction Optimization**:
```python
@staticmethod
def _build_ticker_df(tickers: list[TickerRecord]) -> pd.DataFrame:
    """Resolve enums BEFORE DataFrame construction"""
    rows = []
    for t in tickers:
        d = dataclasses.asdict(t)
        # Resolve AseanMarket enum to string (efficiency: 2 copy stages vs 3)
        d["market"] = d["market"].value if isinstance(d["market"], AseanMarket) else str(d["market"])
        rows.append(d)
    return pd.DataFrame(rows)
```

**DuckDB Choice Rationale**:
1. **Columnar storage**: Analytical joins with OHLCV price series
2. **DataFrame integration**: Zero-copy where possible (vs SQLite serialization)
3. **Parquet interoperability**: Direct query of Parquet OHLCV files
4. **Project convention**: Consistent with `market.edinet` pattern

**Query Methods**:
```python
def get_tickers(self, market: AseanMarket) -> list[TickerRecord]:
    df = self._client.query_df(
        f"SELECT * FROM {TABLE_TICKERS} WHERE market = $1",
        params=[market.value],
    )
    return self._df_to_ticker_records(df)

def lookup_ticker(self, name: str, market: AseanMarket | None = None) -> list[TickerRecord]:
    """Case-insensitive ILIKE search with wildcard escaping"""
    pattern = f"%{self._escape_ilike(name.strip())}%"
    df = self._client.query_df(
        f"SELECT * FROM {TABLE_TICKERS} WHERE name ILIKE $1",
        params=[pattern],
    )
    return self._df_to_ticker_records(df)
```

---

### 2.3 Pattern 3: File-Based Storage (JSON)

**Location**: `src/rss/storage/json_storage.py`

**Purpose**: Persistent storage for RSS feed registry and metadata

**Data Structure**:
```python
@dataclass
class FeedMetadata:
    feed_id: str
    title: str
    url: str
    category: str
    is_active: bool
    last_fetched: datetime | None
    last_updated: datetime | None

@dataclass
class FeedsData:
    feeds: list[FeedMetadata]
    last_sync: datetime
```

**Serialization Strategy**:
```python
def save_feeds(self, feeds_data: FeedsData) -> None:
    """Serialize dataclasses to JSON with enum value conversion"""
    data = dataclasses.asdict(feeds_data)

    # Convert enums to strings
    for feed in data["feeds"]:
        feed["category"] = feed["category"].value  # Enum → str

    with self._lock_manager.lock():
        with open(self._path, "w") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
```

**File Locking** (concurrent access safety):
```python
class LockManager:
    def __init__(self, lock_file: Path):
        self._lock_file = lock_file

    def lock(self):
        # fcntl.flock() on Unix, msvcrt.locking() on Windows
        return filelock.FileLock(str(self._lock_file), timeout=10)
```

**Graceful Degradation**:
```python
def load_feeds(self) -> FeedsData:
    if not self._path.exists():
        logger.warning("Feed registry not found, returning empty")
        return FeedsData(feeds=[], last_sync=datetime.now())

    with self._lock_manager.lock():
        with open(self._path) as f:
            data = json.load(f)
    return FeedsData(**data)
```

---

## 3. Data Pipeline Patterns

### 3.1 Async Pipeline (news.embedding)

**Location**: `src/embedding/pipeline.py`

**Purpose**: ETL for extracting and storing article content in ChromaDB

**Flow**:
```
read_all_news_json()
    ↓
ChromaDB diff check (skip existing)
    ↓
extract_contents() (WebFetch)
    ↓
store_articles() (ChromaDB)
    ↓
PipelineStats
```

**Result Type**:
```python
@dataclass
class PipelineStats:
    total_json_articles: int
    already_in_chromadb: int
    new_articles: int
    extraction_success: int
    extraction_failed: int
    stored: int
```

**Key Pattern**: Filter before storage
```python
successful = [
    ExtractedArticle(...)
    for article in extraction_results
    if article.status == "success"
]
stored_count = await chromadb.store(successful)
```

---

### 3.2 Sync Pipeline (news.processors)

**Location**: `src/news/processors/pipeline.py`

**Purpose**: Orchestrate Source → Processor → Sink workflows

**Configuration**:
```python
@dataclass
class PipelineConfig:
    continue_on_error: bool = True
    batch_size: int = 10
    max_workers: int = 4
```

**Execution**:
```
fetch_from_sources()
    ↓
_process_articles() (parallel, batched)
    ↓
_output_to_sinks()
    ↓
PipelineResult
```

**Error Handling**:
```python
@dataclass
class StageError:
    stage: Literal["source", "processor", "sink"]
    source_name: str
    error_message: str
    article_url: str | None = None

@dataclass
class PipelineResult:
    success: bool
    total_articles: int
    output_articles: int
    errors: list[StageError]
```

**Fluent API**:
```python
pipeline = (
    Pipeline(config)
    .add_source(YFinanceSource())
    .add_processor(SentimentAnalyzer())
    .add_sink(GitHubIssueSink())
    .run()
)
```

---

## 4. Data Directory Structure

### 4.1 Directory Layout

```
data/
├── sqlite/                    # SQLite databases
│   ├── market_cache.db       # Market data cache (TTL-based)
│   ├── edinet.db             # EDINET disclosure data
│   └── *.db                  # Other SQLite databases
├── duckdb/                    # DuckDB databases
│   ├── asean.duckdb          # ASEAN ticker master
│   ├── market_analytics.duckdb
│   └── *.duckdb              # Other DuckDB databases
├── raw/                       # Unprocessed data
│   ├── yfinance/
│   │   ├── stocks/
│   │   ├── forex/
│   │   └── indices/
│   ├── fred/
│   │   └── indicators/
│   ├── news/                 # Raw news articles (JSON)
│   └── edinet/               # EDINET raw disclosures
├── processed/                # Processed/analyzed data
│   ├── daily/                # Daily updates
│   └── aggregated/           # Time-series aggregations
├── exports/                  # Output data
│   ├── csv/
│   └── json/
├── Transcript/               # Meeting transcripts
├── investment_theme/         # Thematic data
├── macroeconomics/          # Macro indicators
├── market/                   # Market snapshots
└── stock/                    # Stock-specific data
```

### 4.2 Path Resolution Logic

**Priority Order** (in `get_data_dir()`):

1. **Environment Variable** (highest priority)
   ```bash
   export DATA_DIR=/custom/path/data
   ```

2. **Current Working Directory**
   ```python
   if Path.cwd() / "data" exists:
       return Path.cwd() / "data"
   ```

3. **Fallback** (lowest priority)
   ```python
   PROJECT_ROOT / "data"
   ```

**Rationale**: Allows flexibility for development (local `./data`), deployment (env var), and migration (fallback)

---

## 5. Schema Design Patterns

### 5.1 DDL-First Approach

**Pattern**: Define complete schema in `CREATE TABLE IF NOT EXISTS` statements

**Benefits**:
- Schema documentation in code
- Version control tracking
- Migration support via `ALTER TABLE`

**Example**:
```python
_TABLE_DDL: str = f"""
    CREATE TABLE IF NOT EXISTS {TABLE_TICKERS} (
        ticker VARCHAR NOT NULL,
        name VARCHAR NOT NULL,
        market VARCHAR NOT NULL,
        yfinance_suffix VARCHAR NOT NULL,
        yfinance_ticker VARCHAR NOT NULL,
        sector VARCHAR,
        industry VARCHAR,
        market_cap BIGINT,
        currency VARCHAR,
        is_active BOOLEAN NOT NULL DEFAULT TRUE
    )
"""
```

### 5.2 Validation Layers

#### SQLite (EdinetStorage)
- **Approach**: Python type checking in dataclass definitions
- **Mechanism**: Accept `dataclass` instances, convert to tuples for INSERT

#### DuckDB (AseanTickerStorage)
- **Approach**: Pandera DataFrame schema validation
- **Mechanism**: Validate DataFrame before `store_df()` call
- **Features**: Type coercion, nullable checking, strict mode disabled for extensibility

#### Parquet (database/parquet_schema.py)
- **Approach**: Schema class with field definitions
- **Mechanism**: Type checking helpers (`_is_numeric_compatible()`, etc.)
- **Structure**:
  ```python
  class StockPriceSchema:
      fields = {
          "symbol": str,
          "date": datetime.date,
          "open": float,
          "high": float,
          "low": float,
          "close": float,
          "adjusted_close": float,
          "volume": int,
      }
  ```

---

## 6. Upsert Patterns

### 6.1 SQLite: INSERT OR REPLACE

```python
# EdinetStorage pattern
sql = f"""
    INSERT OR REPLACE INTO {TABLE_COMPANIES}
    (edinet_code, sec_code, name, industry, ...)
    VALUES (?, ?, ?, ?, ...)
"""
self._client.execute_many(sql, tuples)
```

**Characteristics**:
- Composite keys defined via `PRIMARY KEY` constraint
- Atomic: Replaces entire row if key matches
- Simple: No explicit DELETE + INSERT steps

### 6.2 DuckDB: DELETE + INSERT (via store_df)

```python
# AseanTickerStorage pattern
self._client.store_df(
    df,
    TABLE_TICKERS,
    if_exists="upsert",
    key_columns=["ticker", "market"],
)
```

**DuckDBClient Implementation**:
```python
def store_df(self, df, table_name, if_exists="upsert", key_columns=None):
    if if_exists == "upsert" and key_columns:
        # Step 1: DELETE matching rows
        where_clause = " AND ".join([f"{col} = ${{col}}" for col in key_columns])
        self.execute(f"DELETE FROM {table_name} WHERE {where_clause}", ...)

        # Step 2: INSERT new rows
        self.execute(f"INSERT INTO {table_name} SELECT * FROM temp_df", ...)
```

**Characteristics**:
- Explicit control: Separate DELETE + INSERT steps
- DataFrame-native: Leverages DuckDB's columnar efficiency
- Key columns specified as parameter (flexible composite keys)

---

## 7. No Generic Repository Pattern

### 7.1 Why Not?

The project deliberately avoids a generic ORM/Repository pattern:

1. **Heterogeneous Storage**: Different domains use different backends (SQLite vs DuckDB)
2. **Schema Variation**: Each domain has unique primary keys and validation logic
3. **Operational Differences**: TTL-based cache ≠ EDINET ledger ≠ ASEAN ticker master
4. **Performance Tradeoffs**: Columnar (DuckDB) vs Row-oriented (SQLite)

### 7.2 Instead: Domain-Specific Classes

Each storage class encapsulates:
- **DDL definitions** (schema)
- **Upsert logic** (idempotent writes)
- **Query methods** (domain-specific filtering)
- **Validation** (pandera, type checking)
- **Serialization** (dataclass → tuple/DataFrame)

**Benefits**:
- Explicit control over schema and performance
- Clear separation of concerns
- Testability (mock storage classes easily)
- Extensibility (add new tables without framework changes)

---

## 8. Serialization Strategies

### 8.1 Dataclass → Tuple (SQLite)

```python
def _dataclass_to_tuple(self, obj: Any) -> tuple:
    """Convert dataclass to tuple for INSERT"""
    if dataclasses.is_dataclass(obj):
        return tuple(obj.__dict__.values())
    raise TypeError(f"Expected dataclass, got {type(obj)}")
```

**Efficiency**: O(1) conversion, minimal memory overhead

### 8.2 Dataclass → DataFrame (DuckDB)

```python
def _build_ticker_df(tickers: list[TickerRecord]) -> pd.DataFrame:
    rows = []
    for t in tickers:
        d = dataclasses.asdict(t)
        # Resolve enums before DataFrame construction
        d["market"] = d["market"].value if isinstance(d["market"], AseanMarket) else str(d["market"])
        rows.append(d)
    return pd.DataFrame(rows)
```

**Optimization**: Resolve enums before DataFrame construction (2 memory copies vs 3)

### 8.3 Dataclass → JSON (RSS Storage)

```python
data = dataclasses.asdict(feeds_data)
# Convert enums to strings for JSON compatibility
for feed in data["feeds"]:
    feed["category"] = feed["category"].value
json.dump(data, f, ensure_ascii=False, indent=2)
```

### 8.4 Cache Serialization Strategy

```python
def _serialize(self, value: Any) -> bytes:
    if isinstance(value, (pd.DataFrame, pd.Series)):
        return pickle.dumps(value)
    elif isinstance(value, (dict, list)):
        return json.dumps(value).encode('utf-8')
    else:
        return str(value).encode('utf-8')

def _deserialize(self, data: bytes, value_type: str) -> Any:
    if value_type in ("DataFrame", "Series"):
        return pickle.loads(data)
    elif value_type in ("dict", "list"):
        return json.loads(data.decode('utf-8'))
    else:
        return data.decode('utf-8')
```

**Rationale**:
- **Pickle**: Best for pandas objects (zero-copy in many cases)
- **JSON**: Human-readable, interoperable with other languages
- **String**: Fallback for scalar values

---

## 9. Type Definitions and Constants

### 9.1 Core Types (src/market/types.py)

```python
@dataclass
class MarketDataResult:
    symbol: str
    data: pd.DataFrame  # OHLCV data
    source: DataSource
    fetched_at: datetime
    from_cache: bool = False
    metadata: dict[str, Any] = field(default_factory=dict)

    @property
    def is_empty(self) -> bool:
        return self.data.empty

    @property
    def row_count(self) -> int:
        return len(self.data)

class DataSource(str, Enum):
    YFINANCE = "yfinance"
    FRED = "fred"
    LOCAL = "local"
    EDINET_DB = "edinet_db"
    EDINET_API = "edinet_api"
    JQUANTS = "jquants"
    # ... 10+ other sources
```

### 9.2 Database Types (src/database/types.py)

```python
DatabaseType = Literal["sqlite", "duckdb"]

@dataclass
class ConversionResult:
    success: bool
    input_path: Path
    output_path: Path
    rows_converted: int
    columns: list[str]
    error_message: str | None = None
    type_mappings: dict[str, str] = field(default_factory=dict)

    @staticmethod
    def create_success(...) -> ConversionResult:
        return ConversionResult(success=True, ...)

    @staticmethod
    def create_failure(...) -> ConversionResult:
        return ConversionResult(success=False, ...)
```

---

## 10. Key Design Principles

### 10.1 Separation of Concerns

| Layer | Responsibility |
|-------|-----------------|
| **Cache (SQLiteCache)** | API response persistence with TTL |
| **Storage (Domain classes)** | Persistent table management |
| **Pipeline** | ETL orchestration and transformation |
| **Client (DuckDBClient, SQLiteClient)** | Low-level DB operations |

### 10.2 Idempotency

All write operations are idempotent:
- **SQLite**: `INSERT OR REPLACE` replaces on PK match
- **DuckDB**: Explicit `DELETE` + `INSERT` with key_columns
- **Cache**: `INSERT OR REPLACE` updates on key match

### 10.3 Validation First

```python
# Validate BEFORE persisting
df = TICKER_DF_SCHEMA.validate(df)  # Can raise SchemaError
self._client.store_df(df, table_name, ...)
```

### 10.4 Explicit Over Implicit

- Upsert is explicit (not automatic)
- Key columns specified as parameters (not implicit from schema)
- Serialization strategy chosen per-domain (not framework-driven)

---

## 11. Implementation Checklist

When adding persistent storage for a new data domain:

- [ ] **Choose database backend**
  - SQLite: Transactional, ACID, row-oriented (default)
  - DuckDB: Analytical, columnar, DataFrame-native
  - JSON: Simple, configuration/metadata only

- [ ] **Define DDL** (CREATE TABLE IF NOT EXISTS)
  - Specify column types explicitly
  - Define PRIMARY KEY for upsert operations
  - Add comments for column semantics

- [ ] **Implement Storage Class**
  - `__init__(self, client)` - accepts DuckDBClient or SQLiteClient
  - `ensure_tables()` - schema initialization
  - `upsert_*()` - idempotent write methods
  - `get_*()` - query methods

- [ ] **Add Schema Validation**
  - pandera (DuckDB) or type checking (SQLite)
  - Validate before `store_df()` or `execute_many()`
  - Handle nullable fields and type coercion

- [ ] **Implement Serialization**
  - Dataclass → tuple/DataFrame conversion
  - Handle enum resolution
  - Support round-trip deserialization

- [ ] **Add Query Methods**
  - Support filtering by domain-specific keys
  - Implement search/lookup with appropriate indexes
  - Return domain objects (dataclass instances)

- [ ] **Consider Caching**
  - Use SQLiteCache for frequently accessed data
  - Set appropriate TTL values per source
  - Implement cleanup_expired() triggers

- [ ] **Document Schema**
  - Include table purpose in comments
  - Document primary key semantics
  - List expected data sources

---

## 12. References

### Core Database Infrastructure
- `src/database/db/connection.py` - Path resolution, directory initialization
- `src/database/db/duckdb_client.py` - DuckDB client with DataFrame I/O
- `src/database/db/sqlite_client.py` - SQLite client with context managers

### Persistent Storage Implementations
- `src/market/cache/cache.py` - TTL-based cache with serialization
- `src/market/edinet/storage.py` - EDINET disclosure storage (SQLite)
- `src/market/asean_common/storage.py` - ASEAN ticker storage (DuckDB)
- `src/rss/storage/json_storage.py` - RSS feed metadata storage

### Pipeline Patterns
- `src/embedding/pipeline.py` - Async ETL pipeline
- `src/news/processors/pipeline.py` - Sync pipeline orchestration

### Type Definitions
- `src/market/types.py` - MarketDataResult, DataSource enum
- `src/database/types.py` - DatabaseType, ConversionResult
- `src/database/parquet_schema.py` - Parquet schema definitions

---

## 13. Summary Table

| Pattern | Backend | Use Case | Key Feature |
|---------|---------|----------|------------|
| **TTL Cache** | SQLite | API response caching | Automatic expiration |
| **EDINET Storage** | SQLite | Disclosure data | INSERT OR REPLACE upsert |
| **ASEAN Ticker** | DuckDB | Master data + analytics | DataFrame validation |
| **RSS Metadata** | JSON | Feed registry | File-based with locking |
| **Async Pipeline** | Mixed | Content extraction | ChromaDB integration |
| **Sync Pipeline** | Mixed | ETL orchestration | Batch processing |

---

**End of Architecture Analysis**

This document synthesizes findings from comprehensive exploration of 15+ implementation files across the quants codebase. It provides a complete reference for understanding persistent storage decisions, patterns, and best practices used throughout the project.
