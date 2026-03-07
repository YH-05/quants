# etfcom モジュール 404エラー検出・修正計画

## Context

etfcom モジュールの `TickerCollector` を `headless=False` で実行した際、ブラウザ画面に404エラーが表示され、`TargetClosedError` が発生。原因は **HTTP 404レスポンスの未検出** と **サイト構造変更への脆弱性**。他の Collector クラスにも同様の問題が潜在する。

### 根本原因

1. **browser.py**: `page.goto()` の戻り値（`Response`オブジェクト）を無視。404ページでも「成功」として扱い、サイト側JSのリダイレクトで `TargetClosedError` が発生
2. **session.py**: `_BLOCKED_STATUS_CODES` が `{403, 429}` のみ。404は検出対象外でスルー
3. **collectors.py**: ティッカーの大文字/小文字正規化なし（`"spy"` → 404の可能性）
4. **errors.py**: 404専用の例外クラスが存在しない

### 影響範囲

| Collector | URL | 404リスク |
|-----------|-----|-----------|
| TickerCollector | `https://www.etf.com/topics/etf-screener` | サイト改修でURL変更 |
| FundamentalsCollector | `https://www.etf.com/{ticker}` | 無効/小文字ティッカー |
| FundFlowsCollector | `https://www.etf.com/{ticker}#702` | 無効/小文字ティッカー |
| HistoricalFundFlowsCollector | REST API | APIエンドポイント変更（既にステータスチェックあり） |

---

## 修正計画

### Step 1: `ETFComNotFoundError` 追加

**File**: `src/market/etfcom/errors.py`

既存の `ETFComBlockedError` と同じパターンで404専用例外を追加。

```python
class ETFComNotFoundError(ETFComError):
    def __init__(self, message: str, url: str | None, status_code: int = 404) -> None:
        super().__init__(message)
        self.url = url
        self.status_code = status_code
```

更新後の例外階層:
```
ETFComError
├── ETFComScrapingError
├── ETFComTimeoutError
├── ETFComBlockedError (403/429)
├── ETFComNotFoundError (404)  ← NEW
└── ETFComAPIError
```

`__all__` に `"ETFComNotFoundError"` を追加。

### Step 2: browser.py — Playwright 404検出 + TargetClosedError ハンドリング

**File**: `src/market/etfcom/browser.py`

`_navigate()` メソッド（行 271-340）を修正:

1. `page.goto()` の戻り値 `Response` を取得し `response.status == 404` をチェック
2. `TargetClosedError` を明示的にキャッチし `ETFComNotFoundError` でラップ

```python
async def _navigate(self, url: str, wait_until: str = "networkidle") -> Any:
    # ... polite delay, context/page creation (既存コード) ...
    try:
        response = await page.goto(url, timeout=timeout_ms, wait_until=wait_until)

        # NEW: 404検出
        if response is not None and response.status == 404:
            logger.warning("Page returned HTTP 404", url=url, status=response.status)
            await page.close()
            raise ETFComNotFoundError(
                f"Page not found (HTTP 404): {url}", url=url,
            )

        logger.debug("Navigation completed", url=url, wait_until=wait_until,
                      status=response.status if response else None)
        return page

    except (asyncio.TimeoutError, Exception) as e:
        await page.close()
        if isinstance(e, asyncio.TimeoutError):
            raise ETFComTimeoutError(...) from e

        # NEW: TargetClosedError を 404-like として処理
        if type(e).__name__ == "TargetClosedError":
            logger.warning("Target closed during navigation", url=url, error=str(e))
            raise ETFComNotFoundError(
                f"Page closed during navigation (possible 404 redirect): {url}",
                url=url,
            ) from e

        logger.error("Navigation failed", url=url, error=str(e))
        raise
```

**設計判断**: `TargetClosedError` のインポートは行わず `type(e).__name__` で判定。playwright はオプショナル依存のため。

### Step 3: session.py — curl_cffi 404検出

**File**: `src/market/etfcom/session.py`

`_request()` メソッド（行 218-230 の後）に404チェックを追加:

```python
# 既存: ボットブロッキング検出 (403/429)
if response.status_code in _BLOCKED_STATUS_CODES:
    raise ETFComBlockedError(...)

# NEW: 404検出（ブロックではなくリソース不在）
if response.status_code == 404:
    logger.warning("Resource not found", method=method, url=url, status_code=404)
    raise ETFComNotFoundError(
        f"Resource not found (HTTP 404): {url}", url=url,
    )
```

**重要**: 404は `_BLOCKED_STATUS_CODES` に追加しない。ブロック検出とは意味が異なり、リトライ/セッションローテーションは無意味。`_request_with_retry()` は `ETFComBlockedError` のみキャッチするため、404は即座に伝播する（正しい動作）。

### Step 4: collectors.py — ティッカー正規化 + 404グレースフルハンドリング

**File**: `src/market/etfcom/collectors.py`

#### 4a. ティッカー正規化（`.upper()`）

3箇所にティッカー正規化を追加:

- **FundamentalsCollector.fetch()** 行 627-628:
  ```python
  for ticker in tickers:
      ticker = ticker.upper()
      url = PROFILE_URL_TEMPLATE.format(ticker=ticker)
  ```

- **FundFlowsCollector.fetch()** 行 1014-1020:
  ```python
  ticker: str = kwargs.get("ticker", "")
  if not ticker:
      ...
  ticker = ticker.upper()
  url = FUND_FLOWS_URL_TEMPLATE.format(ticker=ticker)
  ```

- **HistoricalFundFlowsCollector.fetch()** 行 1589:
  ```python
  ticker: str = kwargs.get("ticker", "")
  if not ticker:
      ...
  ticker = ticker.upper()
  ```

#### 4b. FundamentalsCollector での404グレースフルハンドリング

行 635-652 の try/except に `ETFComNotFoundError` 専用ハンドリングを追加:

```python
try:
    html = self._get_html(url)
    record = self._parse_profile(html, ticker)
    all_records.append(record)
except ETFComNotFoundError:
    logger.warning("Ticker page not found (404)", ticker=ticker)
    all_records.append({"ticker": ticker})
except Exception as e:
    logger.warning("Failed to fetch fundamentals", ticker=ticker, error=str(e))
    all_records.append({"ticker": ticker})
```

#### 4c. インポート追加

```python
from market.etfcom.errors import ETFComAPIError, ETFComBlockedError, ETFComNotFoundError
```

### Step 5: Re-export 更新

#### `src/market/etfcom/__init__.py`

`ETFComNotFoundError` をインポートと `__all__` に追加。

#### `src/market/errors.py`

- 行 65-70 のインポートに `ETFComNotFoundError` を追加
- docstring の例外階層に `ETFComNotFoundError` を追加
- `__all__` に `"ETFComNotFoundError"` を追加

### Step 6: テスト追加

#### `tests/market/etfcom/unit/test_errors.py`

```python
class TestETFComNotFoundError:
    def test_正常系_属性が正しく設定される(self):
        error = ETFComNotFoundError("Not found", url="https://www.etf.com/XYZ")
        assert error.message == "Not found"
        assert error.url == "https://www.etf.com/XYZ"
        assert error.status_code == 404

    def test_正常系_ETFComErrorを継承している(self):
        assert issubclass(ETFComNotFoundError, ETFComError)
```

#### `tests/market/etfcom/unit/test_browser.py`

```python
class TestNavigate404Detection:
    async def test_異常系_404レスポンスでETFComNotFoundError(self):
        # page.goto() が status=404 の Response を返す場合
    async def test_異常系_TargetClosedErrorでETFComNotFoundError(self):
        # page.goto() が TargetClosedError を raise する場合
    async def test_正常系_200レスポンスでページを返す(self):
        # 回帰テスト
```

#### `tests/market/etfcom/unit/test_session.py`

```python
class TestRequest404Detection:
    def test_異常系_404レスポンスでETFComNotFoundError(self):
        # status_code=404 の Response をモック
    def test_正常系_404はリトライしない(self):
        # get_with_retry() が ETFComNotFoundError を即座に伝播
```

#### `tests/market/etfcom/unit/test_collectors.py`

```python
class TestTickerNormalization:
    def test_正常系_FundamentalsCollectorでティッカーが大文字化(self):
    def test_正常系_FundFlowsCollectorでティッカーが大文字化(self):
    def test_正常系_HistoricalFundFlowsCollectorでティッカーが大文字化(self):
    def test_正常系_404エラー時にminimalレコードが追加される(self):
```

---

## 実装順序

| 順番 | ファイル | 変更内容 | 優先度 |
|------|----------|----------|--------|
| 1 | `errors.py` | `ETFComNotFoundError` 追加 | P0（基盤） |
| 2 | `test_errors.py` | 新エラークラスのテスト | P0 |
| 3 | `session.py` | 404検出を `_request()` に追加 | P0 |
| 4 | `test_session.py` | 404検出テスト | P0 |
| 5 | `browser.py` | レスポンスステータス確認 + TargetClosedError | P0 |
| 6 | `test_browser.py` | 404/TargetClosedError テスト | P0 |
| 7 | `collectors.py` | ティッカー正規化 + 404ハンドリング | P1 |
| 8 | `test_collectors.py` | 正規化 + 404テスト | P1 |
| 9 | `__init__.py` + `market/errors.py` | Re-export 更新 | P1 |
| 10 | ノートブック手動検証 | `notebook/TEST/etfcom_test.ipynb` 再実行 | P2 |

---

## 検証方法

1. **ユニットテスト実行**:
   ```bash
   uv run pytest tests/market/etfcom/unit/ -v
   ```

2. **品質チェック**:
   ```bash
   make check-all
   ```

3. **手動検証（ノートブック）**:
   `notebook/TEST/etfcom_test.ipynb` で `TickerCollector` を実行し、
   - 404の場合: `ETFComNotFoundError` が発生し、URLを含む明確なエラーメッセージが表示されることを確認
   - TargetClosedError ではなく、適切な例外が表示されることを確認

4. **ティッカー正規化の確認**:
   ```python
   collector = FundamentalsCollector()
   df = collector.fetch(tickers=["spy"])  # 小文字入力
   # → URL が https://www.etf.com/SPY に正規化されることをログで確認
   ```

---

## 修正対象ファイル一覧

| ファイル | 種別 |
|----------|------|
| `src/market/etfcom/errors.py` | 修正（クラス追加） |
| `src/market/etfcom/browser.py` | 修正（`_navigate` メソッド） |
| `src/market/etfcom/session.py` | 修正（`_request` メソッド） |
| `src/market/etfcom/collectors.py` | 修正（3箇所の正規化 + 404ハンドリング） |
| `src/market/etfcom/__init__.py` | 修正（re-export追加） |
| `src/market/errors.py` | 修正（re-export追加） |
| `tests/market/etfcom/unit/test_errors.py` | 修正（テスト追加） |
| `tests/market/etfcom/unit/test_browser.py` | 修正（テスト追加） |
| `tests/market/etfcom/unit/test_session.py` | 修正（テスト追加） |
| `tests/market/etfcom/unit/test_collectors.py` | 修正（テスト追加） |
