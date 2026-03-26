# Test Patterns Exploration Summary

**Date**: 2026-03-24  
**Scope**: Market package test suite (NASDAQ, FRED, yfinance, general market)  
**Files Analyzed**: 15+ test files, 5+ conftest.py files, template patterns

---

## Executive Summary

The quants project employs a **three-tier testing architecture** (unit/property/integration) with sophisticated mocking and fixture patterns. Test files follow **Japanese naming conventions** with English docstrings, and organize code around **dependency injection**, **protocol testing**, and **property-based validation**.

### Key Characteristics
- **Language**: Japanese test method names + English docstrings
- **Structure**: 3 tiers (unit, property, integration) across packages
- **Fixtures**: Hierarchical composition (config → response → mock objects)
- **Mocking**: `unittest.mock.MagicMock` with `spec` parameter for contracts
- **HTTP Testing**: `curl_cffi` sessions mocked via `patch("market.nasdaq.session.curl_requests")`
- **Property Testing**: Hypothesis with `@given` decorators for robustness validation
- **Exceptions**: Custom hierarchy with inheritance validation and cause chaining

---

## 1. Test Directory Structure

### Market Package Layout
```
tests/
├── conftest.py                          # Root fixtures (OHLCV, MarketDataResult, analysis_result)
├── market/
│   ├── conftest.py                      # Parent-level market package fixtures
│   ├── nasdaq/
│   │   ├── conftest.py                  # NASDAQ-specific fixtures (config, responses, sessions)
│   │   ├── unit/
│   │   │   ├── test_types.py            # Enum/dataclass validation
│   │   │   ├── test_errors.py           # Exception hierarchy
│   │   │   ├── test_session.py          # NasdaqSession HTTP behavior
│   │   │   ├── test_parser.py           # JSON parsing & cleaning functions
│   │   │   └── test_collector.py        # Data collection workflows
│   │   ├── property/
│   │   │   └── test_parser_property.py  # Hypothesis robustness tests
│   │   └── integration/
│   │       └── test_screener_integration.py  # E2E workflows
│   ├── yfinance/
│   │   ├── conftest.py
│   │   └── unit/
│   │       └── test_session.py          # Protocol testing (HttpSessionProtocol)
│   └── fred/                            # Similar structure
├── template/                            # Project template patterns
│   └── tests/
│       ├── conftest.py                  # Template fixture organization
│       ├── unit/
│       ├── property/
│       └── integration/
```

### Convention
- **Mandatory Directory Levels**: All market sub-packages (nasdaq, yfinance, fred) follow identical structure
- **Fixture Inheritance**: Root `conftest.py` → package `conftest.py` → module-level fixtures
- **Autouse Fixtures**: `reset_environment` at root level applies to all tests

---

## 2. Japanese Test Naming Convention

### Pattern
```
test_[Category]_[Description](self) -> None:
    """English docstring describing the test behavior."""
```

### Categories
| Category | Usage | Examples |
|----------|-------|----------|
| `正常系` | Happy path, valid inputs | `test_正常系_有効なデータで処理成功` |
| `異常系` | Error cases, invalid inputs | `test_異常系_不正なサイズでValueError` |
| `エッジケース` | Boundary conditions | `test_エッジケース_空リストで空結果` |
| `パラメトライズ` | Multiple input variations | `test_パラメトライズ_様々なサイズで正しく動作` |

### Example from test_parser.py
```python
def test_正常系_有効な価格文字列をフロートに変換(self) -> None:
    """Valid price strings like '100.50' convert to 100.5."""
    assert clean_price("100.50") == 100.5
```

---

## 3. Fixture Patterns

### Hierarchical Composition: Config → Response → Mock

#### Pattern Flow
```
1. Config Fixture (with test-friendly values: delays=0, timeouts=5)
   ↓
2. Response Fixture (mock API responses as dicts)
   ↓
3. Session Fixture (MagicMock with methods returning responses)
```

### Example: NASDAQ Fixture Stack

#### 3.1 Config Fixtures (tests/market/nasdaq/conftest.py)
```python
@pytest.fixture
def sample_nasdaq_config() -> NasdaqConfig:
    """NASDAQ config with zero delays for testing."""
    return NasdaqConfig(
        polite_delay=0.0,           # No real delays in tests
        delay_jitter=0.0,           # Deterministic for reproducibility
        timeout=5.0,                # Short timeout for CI/CD
        max_retries=3,
        backoff_base=2.0,
        user_agents=[...]           # 10-15 real User-Agent strings
    )

@pytest.fixture
def sample_retry_config() -> RetryConfig:
    """Retry configuration with test-friendly timings."""
    return RetryConfig(
        initial_delay=0.1,
        max_delay=1.0,
        exponential_base=2.0,
        jitter_factor=0.0           # Deterministic for verification
    )
```

#### 3.2 Response Fixtures
```python
@pytest.fixture
def mock_curl_response() -> MagicMock:
    """Mock curl_cffi response object."""
    response = MagicMock()
    response.status_code = 200
    response.text = json.dumps({
        "rows": [
            {"symbol": "AAPL", "name": "Apple Inc", "lastSale": "195.32", ...},
            {"symbol": "MSFT", "name": "Microsoft", "lastSale": "423.55", ...},
            # ... more stocks
        ]
    })
    response.json.return_value = json.loads(response.text)
    return response

@pytest.fixture
def sample_screener_api_response() -> dict[str, Any]:
    """Complete NASDAQ screener API response structure."""
    return {
        "rows": [
            {
                "symbol": "AAPL",
                "companyName": "Apple Inc.",
                "marketCap": "2800000000000",
                "volume": "45123456",
                "ipoYear": "1980",
                "lastSale": "195.32",
                "change": "+2.5",
                "percentChange": "+1.30",
            },
            # ... 4 more stocks (MSFT, GOOGL, AMZN, NVDA)
        ],
        "totalCount": 5,
        "activeCount": 5
    }
```

#### 3.3 Session Fixtures
```python
@pytest.fixture
def mock_nasdaq_session(
    mock_curl_response: MagicMock,
    sample_nasdaq_config: NasdaqConfig
) -> MagicMock:
    """Mock NasdaqSession with pre-configured methods."""
    session = MagicMock(spec=NasdaqSession)
    session.config = sample_nasdaq_config
    session.get.return_value = mock_curl_response
    session.get_with_retry.return_value = mock_curl_response
    session.close.return_value = None
    return session
```

### Reusable Utility Fixtures (tests/conftest.py root level)

```python
@pytest.fixture
def sample_ohlcv_data() -> pd.DataFrame:
    """30-day OHLCV data with reproducible random values."""
    np.random.seed(42)
    dates = pd.date_range("2024-01-01", periods=30, freq="D")
    return pd.DataFrame({
        "date": dates,
        "open": np.random.uniform(100, 110, 30),
        "high": np.random.uniform(110, 120, 30),
        "low": np.random.uniform(90, 100, 30),
        "close": np.random.uniform(100, 110, 30),
        "volume": np.random.randint(1000000, 5000000, 30)
    })

@pytest.fixture(autouse=True)
def reset_environment() -> Generator[None, None, None]:
    """Clean TEST_* environment variables between tests."""
    env_backup = {k: v for k, v in os.environ.items() if k.startswith("TEST_")}
    for key in env_backup:
        del os.environ[key]
    yield
    for key in env_backup:
        os.environ[key] = env_backup[key]
```

---

## 4. HTTP Session Mocking Patterns

### 4.1 curl_cffi Session Mocking (NASDAQ)

#### Patching Strategy
```python
from unittest.mock import patch, MagicMock

@patch("market.nasdaq.session.curl_requests")
def test_session_uses_curl_cffi(mock_curl_requests):
    """Verify curl_cffi is used for HTTP requests."""
    mock_curl_requests.Session.return_value = MagicMock()
    session = NasdaqSession(config)
    mock_curl_requests.Session.assert_called_once()
```

#### Response Mocking with spec
```python
# Create mock with interface contract
mock_response = MagicMock(spec=["status_code", "text", "json"])
mock_response.status_code = 200
mock_response.text = '{"rows": [...]}'
mock_response.json.return_value = {"rows": [...]}
```

#### Polite Delay Testing
```python
@patch("time.sleep")
@patch("random.uniform")
def test_applies_polite_delay(mock_uniform, mock_sleep, mock_session):
    """Verify delay is applied between requests."""
    mock_uniform.return_value = 0.5
    session.get("https://api.nasdaq.com/api/screener/stocks")
    
    # Verify delay calculation: base_delay (1.0) + jitter (0.5) = 1.5
    mock_sleep.assert_called_with(1.5)
```

### 4.2 User-Agent Rotation Testing

```python
@patch("random.choice")
def test_rotates_user_agents(mock_choice, mock_session):
    """Verify User-Agent header is randomly rotated."""
    test_ua = "Mozilla/5.0 (Test Browser)"
    mock_choice.return_value = test_ua
    
    session.get("https://api.nasdaq.com/api/screener/stocks")
    
    # Verify User-Agent was selected from configured list
    mock_choice.assert_called_once()
    call_args = mock_choice.call_args[0]
    assert all(isinstance(ua, str) for ua in call_args[0])
```

### 4.3 Retry Logic with Exponential Backoff

#### Testing Failure Then Success
```python
@patch("time.sleep")
def test_retries_on_failure_then_succeeds(mock_sleep, mock_session):
    """Verify exponential backoff on transient failures."""
    failure_response = MagicMock(status_code=503)
    success_response = MagicMock(status_code=200)
    
    # Simulate: fail, fail, success
    mock_session.get.side_effect = [failure_response, failure_response, success_response]
    
    result = session.get_with_retry("https://api.nasdaq.com/api/screener/stocks")
    
    # Verify sleep called with exponential backoff: 0.1 → 0.2 → 0.4 (clamped to max_delay)
    assert mock_sleep.call_count == 2
    sleep_calls = [call[0][0] for call in mock_sleep.call_args_list]
    assert sleep_calls == [0.1, 0.2]  # Or similar exponential sequence
```

#### Testing Rate Limit (429)
```python
def test_rate_limit_raises_specific_exception(mock_session):
    """Verify 429 status raises NasdaqRateLimitError with retry_after."""
    rate_limit_response = MagicMock()
    rate_limit_response.status_code = 429
    rate_limit_response.headers = {"Retry-After": "60"}
    
    with pytest.raises(NasdaqRateLimitError) as exc_info:
        session.get_with_retry(url)
    
    assert exc_info.value.retry_after == 60
```

### 4.4 Protocol Testing (yfinance)

```python
def test_http_session_protocol_defines_required_methods(self) -> None:
    """HttpSessionProtocol specifies get, close, raw_session."""
    from market.yfinance.session import HttpSessionProtocol
    import inspect
    
    # Verify methods exist
    assert hasattr(HttpSessionProtocol, "get")
    assert hasattr(HttpSessionProtocol, "close")
    assert hasattr(HttpSessionProtocol, "raw_session")
    
    # Verify signatures
    sig = inspect.signature(HttpSessionProtocol.get)
    assert "url" in sig.parameters
    assert any(p.kind == inspect.Parameter.VAR_KEYWORD for p in sig.parameters.values())

def test_concrete_implementation_satisfies_protocol(self) -> None:
    """Classes with required methods satisfy HttpSessionProtocol."""
    class ConcreteSession:
        def __init__(self) -> None:
            self._session = object()
        
        @property
        def raw_session(self) -> Any:
            return self._session
        
        def get(self, url: str, **kwargs: Any) -> Any:
            return {}
        
        def close(self) -> None:
            pass
    
    # Type checker accepts this as HttpSessionProtocol
    session: HttpSessionProtocol = ConcreteSession()
    result = session.get("https://example.com")
    session.close()
```

---

## 5. Type and Enum Testing Patterns

### 5.1 Enum Validation

```python
class TestExchange:
    """Tests for Exchange enum."""
    
    def test_正常系_Exchange継承元はstr(self) -> None:
        """Exchange enum inherits from str for string compatibility."""
        assert issubclass(Exchange, str)
        assert Exchange.NASDAQ == "nasdaq"
        assert isinstance(Exchange.NYSE, str)
    
    def test_正常系_全メンバーが定義されている(self) -> None:
        """All expected exchanges are present."""
        expected = {"NASDAQ", "NYSE", "AMEX"}
        actual = {member.name for member in Exchange}
        assert actual == expected
    
    def test_正常系_メンバー数は3つ(self) -> None:
        """Exchange has exactly 3 members."""
        assert len(Exchange) == 3
```

### 5.2 Frozen Dataclass Validation

```python
from dataclasses import FrozenInstanceError

class TestNasdaqConfig:
    """Tests for frozen NasdaqConfig dataclass."""
    
    def test_異常系_プロパティ修正時にエラー(self) -> None:
        """Frozen dataclass prevents attribute modification."""
        config = NasdaqConfig(polite_delay=1.0, timeout=5.0, ...)
        
        with pytest.raises(FrozenInstanceError):
            config.polite_delay = 2.0
    
    def test_正常系_タイムアウト値の範囲検証(self) -> None:
        """Timeout must be positive value."""
        with pytest.raises(ValueError, match="timeout must be positive"):
            NasdaqConfig(polite_delay=1.0, timeout=-1.0, ...)
```

### 5.3 Type Alias and Filter Testing

```python
class TestScreenerFilter:
    """Tests for ScreenerFilter dataclass."""
    
    def test_正常系_フィルタをパラメータに変換(self) -> None:
        """ScreenerFilter.to_params() converts to query parameters."""
        filter_obj = ScreenerFilter(
            exchange=Exchange.NASDAQ,
            sector=Sector.TECHNOLOGY,
            market_cap=MarketCap.MEGA_CAP
        )
        
        params = filter_obj.to_params()
        
        # All values are strings, None values filtered out
        assert params == {
            "exchange": "nasdaq",
            "sector": "Technology",
            "marketCap": "Mega Cap"
        }
        assert all(isinstance(v, str) for v in params.values())
```

---

## 6. Exception Hierarchy Testing

### 6.1 Exception Architecture

```
NasdaqError (base exception, message: str)
├── NasdaqAPIError (url, status_code, response_body)
├── NasdaqRateLimitError (url, retry_after: int | None)
└── NasdaqParseError (raw_data, field)
```

### 6.2 Hierarchy Validation

```python
class TestExceptionHierarchy:
    """Verify exception inheritance structure."""
    
    def test_正常系_全サブクラスがNasdaqErrorを継承(self) -> None:
        """All exception subclasses inherit from NasdaqError."""
        assert issubclass(NasdaqAPIError, NasdaqError)
        assert issubclass(NasdaqRateLimitError, NasdaqError)
        assert issubclass(NasdaqParseError, NasdaqError)
    
    def test_正常系_NasdaqErrorはExceptionを直接継承(self) -> None:
        """NasdaqError directly inherits from Exception."""
        assert Exception in NasdaqError.__bases__
```

### 6.3 Cause Chaining

```python
def test_正常系_例外チェーンが機能する(self) -> None:
    """Exception cause chain preserves original error context."""
    original = ConnectionError("Connection refused")
    
    try:
        raise NasdaqAPIError(
            "API request failed",
            url="https://api.nasdaq.com",
            status_code=503,
            response_body="Service Unavailable"
        ) from original
    except NasdaqAPIError as e:
        assert e.__cause__ is original
        assert isinstance(e.__cause__, ConnectionError)
```

### 6.4 Optional Attributes

```python
def test_正常系_retry_afterがNoneでも初期化可能(self) -> None:
    """retry_after can be None for unknown retry intervals."""
    error = NasdaqRateLimitError(
        "rate limited",
        url="https://api.nasdaq.com",
        retry_after=None
    )
    assert error.retry_after is None
```

---

## 7. Parser Testing Patterns

### 7.1 Numeric Cleaning Functions

```python
class TestCleanPrice:
    """Tests for price string cleaning."""
    
    def test_正常系_有効な価格文字列(self) -> None:
        """Valid price strings convert to float."""
        assert clean_price("195.32") == 195.32
        assert clean_price("$100.00") == 100.0
    
    def test_異常系_NAバリエーション(self) -> None:
        """NA, N/A, na, n/a all return None."""
        assert clean_price("N/A") is None
        assert clean_price("NA") is None
        assert clean_price("na") is None
        assert clean_price("n/a") is None
    
    def test_エッジケース_特殊値(self) -> None:
        """inf, -inf, nan strings return None."""
        assert clean_price("inf") is None
        assert clean_price("-inf") is None
        assert clean_price("nan") is None
    
    def test_異常系_不正な形式(self) -> None:
        """Invalid strings raise ValueError or return None."""
        with pytest.raises((ValueError, TypeError)):
            clean_price("not a number")
```

### 7.2 Parser Integration with DataFrames

```python
def test_正常系_スクリーナーレスポンスをパース(self) -> None:
    """parse_screener_response converts API dict to cleaned DataFrame."""
    api_response = sample_screener_api_response  # From fixture
    
    df = parse_screener_response(api_response)
    
    # Verify structure
    assert isinstance(df, pd.DataFrame)
    assert df.shape[0] == 5  # 5 stocks
    assert "symbol" in df.columns
    assert "last_sale" in df.columns  # Snake case from camelCase
    
    # Verify cleaning applied
    assert pd.api.types.is_float_dtype(df["last_sale"])
    assert df["last_sale"].notna().all()  # No NaN from cleaning
```

### 7.3 Error Message Testing

```python
def test_異常系_期待されない応答形式(self) -> None:
    """Unexpected API response format raises NasdaqParseError."""
    bad_response = {"invalid_field": [...]}  # Missing required "rows"
    
    with pytest.raises(NasdaqParseError, match="Expected 'rows' field"):
        parse_screener_response(bad_response)
```

---

## 8. Property-Based Testing with Hypothesis

### 8.1 Robustness Testing Pattern

```python
from hypothesis import given, settings
from hypothesis import strategies as st

class TestCleanPriceProperty:
    """Property-based tests for numeric cleaning robustness."""
    
    @given(value=st.text(max_size=200))
    @settings(max_examples=500, deadline=None)
    def test_プロパティ_任意の文字列でクラッシュしない(self, value: str) -> None:
        """clean_price handles arbitrary text without crashing."""
        try:
            result = clean_price(value)
            # Result is None or float
            assert result is None or isinstance(result, float)
        except (ValueError, TypeError):
            # These exceptions are acceptable
            pass
    
    @given(
        num=st.floats(
            min_value=-1e12,
            max_value=1e12,
            allow_nan=False,
            allow_infinity=False
        )
    )
    @settings(max_examples=1000)
    def test_プロパティ_有効な数値文字列は正しく変換(self, num: float) -> None:
        """Valid numeric strings always convert to correct float."""
        string_value = str(num)
        result = clean_price(string_value)
        assert result == num
```

### 8.2 Invariant Testing

```python
@given(
    items=st.lists(st.integers()),
    chunk_size=st.integers(min_value=1, max_value=100)
)
@settings(max_examples=200)
def test_プロパティ_チャンク化しても全要素保持(
    self,
    items: list[int],
    chunk_size: int
) -> None:
    """Chunking preserves all elements regardless of input size."""
    chunks = chunk_list(items, chunk_size)
    flattened = [item for chunk in chunks for item in chunk]
    
    # Invariant: flattened result equals original
    assert flattened == items
    assert len(flattened) == len(items)
```

---

## 9. Integration Testing Patterns

### 9.1 E2E Workflow Testing

```python
class TestScreenerIntegration:
    """End-to-end screener workflow tests."""
    
    def _make_response(self, data: dict) -> MagicMock:
        """Helper: Create mock response with JSON data."""
        response = MagicMock()
        response.status_code = 200
        response.json.return_value = data
        return response
    
    def test_정상系_fetch_download_workflow(self, mock_session):
        """Complete workflow: fetch → download CSV."""
        # Setup
        api_response = sample_screener_api_response  # From fixture
        mock_session.get_with_retry.return_value = self._make_response(api_response)
        
        # Execute
        collector = ScreenerCollector(session=mock_session)
        csv_path = collector.download_csv("output.csv", exchange=Exchange.NASDAQ)
        
        # Verify
        assert csv_path.exists()
        df = pd.read_csv(csv_path, encoding="utf-8-sig")
        assert len(df) == 5
        assert "AAPL" in df["symbol"].values
```

### 9.2 Security Testing in Integration

```python
def test_異常系_パストラバーサル検出(self, tmp_path):
    """Prevent path traversal attacks in file output."""
    collector = ScreenerCollector()
    
    with pytest.raises(ValueError, match="Path traversal"):
        collector.download_csv("../../../etc/passwd", exchange=Exchange.NASDAQ)
```

---

## 10. Conftest.py Organization

### 10.1 Root Level (tests/conftest.py)

```python
# Session-level setup
def pytest_configure(config):
    """Configure pytest plugins and logging."""
    logging.basicConfig(level=os.getenv("TEST_LOG_LEVEL", "INFO"))

# Reusable fixtures for all tests
@pytest.fixture
def sample_ohlcv_data() -> pd.DataFrame:
    """OHLCV data shared across market tests."""
    ...

@pytest.fixture(autouse=True)
def reset_environment() -> Generator[None, None, None]:
    """Clean environment between test methods."""
    ...

# Conditional plugin loading
def pytest_collection_modifyitems(config, items):
    """Skip Bloomberg tests if blpapi unavailable."""
    try:
        import blpapi
    except ImportError:
        skip = pytest.mark.skip(reason="blpapi not installed")
        for item in items:
            if "bloomberg" in item.nodeid:
                item.add_marker(skip)
```

### 10.2 Package Level (tests/market/nasdaq/conftest.py)

```python
# Package-specific config and response fixtures
@pytest.fixture
def sample_nasdaq_config() -> NasdaqConfig:
    """NASDAQ configuration with test-friendly values."""
    return NasdaqConfig(polite_delay=0.0, ...)

@pytest.fixture
def sample_screener_api_response() -> dict:
    """Mock NASDAQ screener API response."""
    return {"rows": [...], "totalCount": 5, ...}

@pytest.fixture
def mock_nasdaq_session(mock_curl_response) -> MagicMock:
    """Fully mocked NasdaqSession instance."""
    return MagicMock(spec=NasdaqSession)
```

### 10.3 Template Pattern (template/tests/conftest.py)

```python
# Session-level logging setup
def pytest_configure(config):
    """Initialize test logging."""
    logging.basicConfig(
        level=os.getenv("TEST_LOG_LEVEL", "DEBUG"),
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )

# Fixture composition: Config → Instance → Utilities
@pytest.fixture
def example_config() -> ExampleConfig:
    """Reusable configuration for tests."""
    return ExampleConfig(...)

@pytest.fixture
def example_instance(example_config) -> ExampleClass:
    """Instance depending on config (dependency injection)."""
    return ExampleClass(config=example_config)

@pytest.fixture
def sample_data() -> list[dict]:
    """Sample data for parsing/transformation tests."""
    return [{"id": 1, "name": "test"}, ...]

@pytest.fixture
def temp_dir(tmp_path) -> Path:
    """Temporary directory with cleanup."""
    return tmp_path
```

---

## 11. Mock Specification Pattern

### 11.1 spec Parameter for Contract Validation

```python
# Create MagicMock with strict interface contract
mock_session = MagicMock(spec=NasdaqSession)

# Only methods/attributes defined in NasdaqSession are allowed
mock_session.get.return_value = response  # ✓ OK
mock_session.nonexistent_method()         # ✗ AttributeError

# Useful for catching typos and interface mismatches
```

### 11.2 Side Effect for State Sequences

```python
# Simulate sequence: fail, fail, success
mock_response.side_effect = [
    ConnectionError("Network error"),
    TimeoutError("Request timeout"),
    MagicMock(status_code=200, json=lambda: {"rows": [...]})
]

# Each call consumes next item from list
result1 = get()  # Raises ConnectionError
result2 = get()  # Raises TimeoutError
result3 = get()  # Returns success response
```

---

## 12. Key Insights and Best Practices

### 12.1 Organizational Principles

1. **Hierarchical Fixtures**: Config → Response → Mock objects
   - Reduces duplication and keeps test setup maintainable
   - Enables composition of simpler fixtures into complex ones

2. **Dependency Injection in Tests**
   - Pass mocks via function parameters (fixture injection)
   - Tests don't rely on global state or hard-coded values
   - Easy to swap implementations (testing vs. real)

3. **Three-Tier Architecture**
   - **Unit**: Single function/method isolation (MagicMock everything external)
   - **Property**: Robustness validation (arbitrary inputs never crash)
   - **Integration**: E2E workflows (real module composition with fixture mocks)

### 12.2 Naming and Documentation

- **Japanese test method names** (`test_正常系_`) improve readability for team
- **English docstrings** provide self-documenting test intent
- **Descriptive parameter names** (e.g., `sample_nasdaq_config` vs. `config`) aid clarity

### 12.3 Mocking Best Practices

1. **Use `spec` parameter** to validate mock interface against contract
2. **Mock at boundary** (e.g., `patch("market.nasdaq.session.curl_requests")`)
3. **Return real objects** from mocks when behavior is complex (e.g., pandas DataFrames)
4. **Verify mock calls** with `assert_called_once()`, `assert_called_with()` to catch integration issues
5. **Use `side_effect` for sequences** when testing retry logic or state transitions

### 12.4 Test Data Patterns

- **Reusable fixtures**: Define once in conftest.py, use in all tests
- **Minimal test data**: Include only fields required by test
- **Seeded randomness**: `np.random.seed(42)` ensures reproducible test data
- **Realistic test data**: 5 NASDAQ stocks (AAPL, MSFT, GOOGL, AMZN, NVDA) with real price formats

### 12.5 Error Testing Patterns

```python
# Generic exception testing
with pytest.raises(ValueError):
    invalid_function()

# Specific message matching
with pytest.raises(ValueError, match="must be positive"):
    function_with_constraint(-5)

# Exception context (cause chain)
with pytest.raises(NasdaqAPIError) as exc_info:
    api_call()
assert isinstance(exc_info.value.__cause__, ConnectionError)
```

---

## 13. Summary Checklist for New Tests

When adding tests to market packages:

- [ ] Create test class with Japanese method names
- [ ] Add English docstring to each test method
- [ ] Follow 正常系/異常系/エッジケース/パラメトライズ categories
- [ ] Define fixtures in conftest.py (Config → Response → Mock)
- [ ] Use `MagicMock(spec=RealClass)` for interface validation
- [ ] Patch at module boundary (e.g., `patch("market.nasdaq.session.curl_requests")`)
- [ ] Test exception hierarchy with `issubclass()` and `isinstance()`
- [ ] Add property-based tests with Hypothesis for robustness
- [ ] Include integration tests for E2E workflows
- [ ] Run `make test-cov` to verify coverage targets (80%+ unit, 60%+ integration)
- [ ] Verify tests run with `make test` before commit

---

## References

- **Fixture Examples**: `tests/market/nasdaq/conftest.py` (lines 1-100)
- **Unit Test Examples**: `tests/market/nasdaq/unit/test_session.py` (621 lines)
- **Property Tests**: `tests/market/nasdaq/property/test_parser_property.py`
- **Integration Tests**: `tests/market/nasdaq/integration/test_screener_integration.py`
- **Template Patterns**: `template/tests/conftest.py` (103 lines)
- **Exception Tests**: `tests/market/nasdaq/unit/test_errors.py` (419 lines)

