# パフォーマンス最適化パターン集

プロファイリング手法、リトライ・指数バックオフ、メモリ効率化、I/O 最適化を体系化したパターン集です。
既存コードベースの実装例と行番号注釈を含みます。

---

## 1. プロファイリング手法

### 1.1 `@profile` デコレータ — 詳細プロファイリング

cProfile ベースの詳細プロファイリング。関数呼び出しごとの時間・回数を記録します。
ボトルネック特定の第一歩として使用します。

```python
from utils_core.profiling import profile

@profile
def calculate_portfolio_returns(df: pd.DataFrame) -> pd.Series:
    """ポートフォリオリターンを計算する重い処理."""
    returns = df.groupby("symbol")["close"].pct_change()
    weights = df.groupby("symbol")["weight"].first()
    return (returns * weights).groupby(level=0).sum()
```

**オプション付き**:

```python
@profile(sort_by="time", limit=10)
def heavy_computation() -> pd.DataFrame:
    """上位10関数を実行時間順にソートして表示."""
    ...
```

> **参照**: `template/src/template_package/utils/profiling.py` lines 150-223 -- `@profile` デコレータ実装

---

### 1.2 `@timeit` デコレータ — 実行時間計測

cProfile のオーバーヘッドなしで純粋な実行時間のみを計測。
本番コードに埋め込んでも影響が小さいため、定常的な計測に適しています。

```python
from utils_core.profiling import timeit

@timeit
def fetch_market_data(symbols: list[str]) -> pd.DataFrame:
    """市場データ取得の実行時間を計測."""
    ...

@timeit(precision=6)
def precise_calculation() -> float:
    """高精度の時間表示（小数点以下6桁）."""
    ...
```

> **参照**: `template/src/template_package/utils/profiling.py` lines 226-283 -- `@timeit` デコレータ実装

---

### 1.3 `profile_context` — コンテキストマネージャ計測

コードブロック単位で計測。特定の処理区間のみを対象にでき、
改善前後の比較に適しています。

```python
from utils_core.profiling import profile_context

# 基本的な使い方
with profile_context() as prof:
    returns = df.groupby("symbol")["close"].pct_change()

print(f"リターン計算: {prof.elapsed_time:.4f} 秒")

# 無効化（本番環境）
with profile_context(enabled=False) as prof:
    # プロファイリングオーバーヘッドなしで実行
    result = heavy_function()
```

**改善前後の比較パターン**:

```python
# Before: Python ループ
with profile_context(print_stats=False) as prof_before:
    result_loop = calculate_with_loop(df)
print(f"ループ版: {prof_before.elapsed_time:.4f} 秒")

# After: ベクトル演算
with profile_context(print_stats=False) as prof_after:
    result_vec = calculate_with_vectorization(df)
print(f"ベクトル版: {prof_after.elapsed_time:.4f} 秒")
print(f"改善率: {(1 - prof_after.elapsed_time / prof_before.elapsed_time) * 100:.1f}%")
```

> **参照**: `template/src/template_package/utils/profiling.py` lines 67-128 -- `profile_context` 実装

---

### 1.4 `compare_performance` — 複数アプローチの比較

複数の実装を同一条件で計測し、ベースラインとの比率を表示。
最適化手法の選択時に使用します。

```python
from utils_core.profiling import compare_performance

results = compare_performance(
    {
        "loop": lambda: calculate_with_loop(df),
        "vectorized": lambda: calculate_with_vectorization(df),
        "numpy": lambda: calculate_with_numpy(df),
    },
    iterations=100,
    warmup=5,
)
# 出力例:
# Performance Comparison:
# --------------------------------------------------
# numpy                    0.0523 ms (  1.00x)
# vectorized               0.1245 ms (  2.38x)
# loop                     5.2341 ms (100.07x)
```

> **参照**: `template/src/template_package/utils/profiling.py` lines 366-430 -- `compare_performance` 実装

---

### 1.5 プロファイリング手法の選択基準

| 手法 | オーバーヘッド | 出力情報 | 推奨場面 |
|------|-------------|---------|---------|
| `@profile` | 高（cProfile） | 関数呼び出し回数・累積時間 | ボトルネック特定 |
| `@timeit` | 低（perf_counter のみ） | 実行時間のみ | 定常計測・ログ出力 |
| `profile_context` | 中（cProfile） | ブロック内の詳細統計 | 改善前後の比較 |
| `compare_performance` | 中 | 複数手法の相対比較 | 最適化手法の選択 |
| `Timer` | 低 | 開始〜停止の時間 | 任意区間の手動計測 |

---

## 2. リトライ・指数バックオフ

### 2.1 RetryConfig — リトライ設定の型定義

リトライ挙動を `dataclass` で型安全に定義。最大試行回数、初期遅延、指数ベース、ジッター有無を制御します。

```python
from dataclasses import dataclass

@dataclass(frozen=True)
class RetryConfig:
    """Configuration for retry behavior.

    Parameters
    ----------
    max_attempts : int
        Maximum number of retry attempts (default: 3)
    initial_delay : float
        Initial delay between retries in seconds (default: 1.0)
    max_delay : float
        Maximum delay between retries in seconds (default: 60.0)
    exponential_base : float
        Base for exponential backoff calculation (default: 2.0)
    jitter : bool
        Whether to add random jitter to delays (default: True)
    """

    max_attempts: int = 3
    initial_delay: float = 1.0
    max_delay: float = 60.0
    exponential_base: float = 2.0
    jitter: bool = True
```

> **参照**: `src/market/yfinance/types.py` lines 63-92 -- `RetryConfig` 定義

---

### 2.2 デフォルトリトライ設定

```python
# Default retry configuration for API calls
DEFAULT_RETRY_CONFIG = RetryConfig(
    max_attempts=3,
    initial_delay=1.0,
    max_delay=30.0,
    exponential_base=2.0,
    jitter=True,
)
```

**設定値の根拠**:

| パラメータ | 値 | 根拠 |
|-----------|-----|------|
| `max_attempts=3` | 3回 | 一時的なネットワークエラーは2-3回で回復する傾向 |
| `initial_delay=1.0` | 1秒 | Yahoo Finance のレート制限に対する最小待機時間 |
| `max_delay=30.0` | 30秒 | ユーザー体感を損なわない上限 |
| `exponential_base=2.0` | 2倍 | 標準的な指数バックオフ（1s → 2s → 4s） |
| `jitter=True` | 有効 | 複数クライアントの同時リトライ衝突（thundering herd）を回避 |

> **参照**: `src/market/yfinance/fetcher.py` lines 46-52 -- `DEFAULT_RETRY_CONFIG` 定義

---

### 2.3 指数バックオフ + ジッター実装パターン

遅延計算の核心部分。`min()` で上限を制限し、ジッターで 0.5x 〜 1.5x の範囲にランダム化します。

```python
import random
import time

for attempt in range(retry_config.max_attempts):
    try:
        return self._do_bulk_fetch(options)

    except Exception as e:
        last_error = e
        logger.warning(
            "Bulk fetch attempt failed",
            attempt=attempt + 1,
            max_attempts=retry_config.max_attempts,
            error=str(e),
            error_type=type(e).__name__,
        )

        if attempt < retry_config.max_attempts - 1:
            # Calculate delay with exponential backoff
            delay = min(
                retry_config.initial_delay
                * (retry_config.exponential_base ** attempt),
                retry_config.max_delay,
            )

            # Add jitter if configured
            if retry_config.jitter:
                delay *= 0.5 + random.random()  # nosec B311 -- ジッター用途（暗号用途ではない）

            logger.debug(
                "Waiting before retry",
                delay_seconds=delay,
                next_attempt=attempt + 2,
            )
            time.sleep(delay)

raise DataFetchError(
    f"Failed to fetch data after {retry_config.max_attempts} attempts",
    symbol=",".join(options.symbols),
    source=self.source.value,
    code=ErrorCode.API_ERROR,
    cause=last_error,
)
```

**遅延シーケンス例（initial_delay=1.0, base=2.0, max_delay=30.0）**:

| 試行 | 計算値 | ジッターなし | ジッターあり（0.5-1.5x） |
|------|--------|-------------|------------------------|
| 1回目 | `1.0 * 2^0` | 1.0秒 | 0.5 〜 1.5秒 |
| 2回目 | `1.0 * 2^1` | 2.0秒 | 1.0 〜 3.0秒 |
| 3回目 | `1.0 * 2^2` | 4.0秒 | 2.0 〜 6.0秒 |
| 4回目 | `min(1.0 * 2^3, 30.0)` | 8.0秒 | 4.0 〜 12.0秒 |
| 5回目 | `min(1.0 * 2^4, 30.0)` | 16.0秒 | 8.0 〜 24.0秒 |

> **参照**: `src/market/yfinance/fetcher.py` lines 374-416 -- 指数バックオフ + ジッター実装

---

### 2.4 チャンク処理 + リトライパターン

大量リクエストをチャンクに分割し、各チャンクにリトライを適用。
API のバッチ制限を回避しつつ、障害をチャンク単位に局所化します。

```python
from typing import Final

DEFAULT_CHUNK_SIZE: Final[int] = 50
DEFAULT_MAX_RETRIES: Final[int] = 3
DEFAULT_RETRY_DELAY: Final[float] = 2.0

def get_financial_data_chunked(
    self,
    options: BloombergFetchOptions,
    chunk_size: int = DEFAULT_CHUNK_SIZE,
) -> list[BloombergDataResult]:
    if chunk_size <= 0:
        raise ValueError(f"chunk_size must be positive, got {chunk_size}")

    securities = options.securities
    all_results: list[BloombergDataResult] = []

    for chunk_start in range(0, len(securities), chunk_size):
        chunk = securities[chunk_start : chunk_start + chunk_size]
        chunk_options = BloombergFetchOptions(
            securities=chunk,
            fields=options.fields,
            # ... other options ...
        )

        last_exc: Exception | None = None
        for attempt in range(1, DEFAULT_MAX_RETRIES + 1):
            try:
                chunk_results = self.get_financial_data(chunk_options)
                all_results.extend(chunk_results)
                last_exc = None
                break
            except BloombergDataError as exc:
                last_exc = exc
                logger.warning(
                    "Chunk fetch failed, retrying",
                    chunk_start=chunk_start,
                    attempt=attempt,
                    max_retries=DEFAULT_MAX_RETRIES,
                    error=str(exc),
                )
                if attempt < DEFAULT_MAX_RETRIES:
                    time.sleep(DEFAULT_RETRY_DELAY)

        if last_exc is not None:
            raise last_exc

    return all_results
```

> **参照**: `src/market/bloomberg/fetcher.py` lines 1562-1668 -- チャンク処理 + リトライ
> **参照**: `src/market/bloomberg/constants.py` lines 96-116 -- チャンク・リトライ定数定義

---

### 2.5 ブラウザフィンガープリントローテーション（`news_scraper` 固有）

> **スコープ**: このパターンは `news_scraper` / `market.yfinance` パッケージ固有です。
> クオンツ計算の一般的なリトライとは異なり、Web スクレイピングに特化した戦略です。

リトライ時にセッション情報を変更し、レート制限を回避する戦略。
curl_cffi でブラウザの TLS フィンガープリントを切り替えます。

```python
# Browser impersonation targets for curl_cffi
# AIDEV-NOTE: ブラウザバージョンは curl_cffi のサポート状況に依存。
# 最新のサポート対象は curl_cffi ドキュメントを確認すること。
# また、ブラウザ偽装は対象サイトの利用規約（ToS）に抵触する可能性があるため、
# 使用前に対象サービスの ToS を確認すること。
BROWSER_IMPERSONATE_TARGETS: list[BrowserTypeLiteral] = [
    "chrome",
    "chrome110",
    "chrome120",
    "edge99",
    "safari15_3",
]

# リトライ時にブラウザフィンガープリントをローテーション
if attempt < retry_config.max_attempts - 1:
    delay = min(
        retry_config.initial_delay * (retry_config.exponential_base ** attempt),
        retry_config.max_delay,
    )
    time.sleep(delay)

    # Rotate browser fingerprint on retry
    self._rotate_session()
```

> **参照**: `src/market/yfinance/fetcher.py` lines 37-43 -- ブラウザターゲット定義
> **参照**: `src/market/yfinance/fetcher.py` lines 405-408 -- リトライ時のセッションローテーション

---

## 3. メモリ効率化パターン

### 3.1 キャッシュ設定（TTL 付き）

用途に応じてキャッシュ有効期限を使い分け。短期データはインメモリ、長期データはファイルベースで永続化します。

```python
from dataclasses import dataclass

@dataclass(frozen=True)
class CacheConfig:
    enabled: bool = True
    ttl_seconds: int = 3600   # Time-to-live in seconds
    max_entries: int = 1000
    db_path: str | None = None  # None = in-memory

# 短期キャッシュ（デフォルト）: 頻繁に更新されるデータ
DEFAULT_CACHE_CONFIG = CacheConfig(
    enabled=True,
    ttl_seconds=3600,   # 1 hour
    max_entries=1000,
    db_path=None,       # In-memory
)

# 長期キャッシュ: 変更頻度の低い参照データ
PERSISTENT_CACHE_CONFIG = CacheConfig(
    enabled=True,
    ttl_seconds=86400,  # 24 hours
    max_entries=10000,
    db_path=str(DEFAULT_CACHE_DB_PATH),  # File-based
)
```

**TTL 設計指針**:

| データ種別 | TTL | 根拠 |
|-----------|-----|------|
| リアルタイム株価 | 60秒 | 取引時間中は頻繁に変動 |
| 日次 OHLCV | 3600秒（1時間） | 取引終了後は固定 |
| 企業メタデータ | 86400秒（24時間） | 変更頻度が低い |
| セクター分類 | 604800秒（1週間） | 四半期ごとの見直し |

> **参照**: `src/market/cache/cache.py` lines 34-47 -- デフォルト・永続キャッシュ設定
> **参照**: `src/market/cache/types.py` lines 14-61 -- `CacheConfig` 型定義
>
> **セキュリティ注意**: `diskcache` ライブラリは内部で `pickle` を使用します。
> 信頼できないソースのキャッシュファイルを読み込むと任意コード実行のリスクがあります
> （CVE-2025-69872）。キャッシュ DB ファイルのパーミッションを適切に制限してください。

---

### 3.2 バッチ挿入パターン

大量データの DB 書き込みを `batch_size` 単位で分割し、メモリ使用量のピークを抑制します。

```python
def insert_data(
    df: pd.DataFrame,
    table_name: str,
    batch_size: int = 10000,
) -> None:
    """データを batch_size 行ずつ分割して挿入.

    Parameters
    ----------
    df : pd.DataFrame
        挿入するデータ
    table_name : str
        テーブル名
    batch_size : int
        一度に挿入する行数（default: 10000）
    """
    for chunk_start in range(0, len(df), batch_size):
        chunk = df.iloc[chunk_start : chunk_start + batch_size]
        chunk.to_sql(table_name, conn, if_exists="append", index=False)
        logger.debug(
            "Batch inserted",
            chunk_start=chunk_start,
            chunk_size=len(chunk),
            total_rows=len(df),
        )
```

> **参照**: `src/market/factset/factset_utils.py` lines 916-940 -- `batch_size` パラメータ付きバッチ挿入

---

### 3.3 Parquet 分割保存パターン

巨大な DataFrame を N 分割して Parquet ファイルに書き出し、後続処理での部分読み込みを可能にします。

```python
import numpy as np
from pathlib import Path

def save_parquet_splits(
    df: pd.DataFrame,
    output_dir: Path,
    n_splits: int = 4,
    **kwargs,
) -> list[Path]:
    """DataFrame を n_splits 個の Parquet ファイルに分割保存."""
    total_rows = len(df)
    indices = np.linspace(0, total_rows, n_splits + 1, dtype=int)
    paths: list[Path] = []

    for i in range(n_splits):
        df_split = df.iloc[indices[i] : indices[i + 1]]
        file_path = output_dir / f"part_{i:04d}.parquet"
        df_split.to_parquet(file_path, **kwargs)
        paths.append(file_path)

    return paths
```

> **参照**: `src/market/factset/factset_utils.py` lines 109-139 -- Parquet 分割保存

---

### 3.4 キャッシュキー生成パターン

キャッシュの一意キーをハッシュで生成し、メモリ効率の高いルックアップを実現します。

```python
import hashlib

def generate_cache_key(
    symbol: str,
    start_date: datetime | str | None = None,
    end_date: datetime | str | None = None,
    interval: str = "1d",
    source: str = "yfinance",
) -> str:
    """Generate a unique cache key for market data."""
    key_parts = [symbol, str(start_date), str(end_date), interval, source]
    key_string = "|".join(key_parts)
    return hashlib.sha256(key_string.encode()).hexdigest()
```

> **参照**: `src/market/cache/cache.py` lines 50-80 -- `generate_cache_key` 実装

---

### 3.5 インメモリキャッシュ + ファイルキャッシュの2階層パターン

高速なインメモリキャッシュと永続的なファイルキャッシュの2階層構成。
ヒット率を最大化しながら、プロセス再起動後もキャッシュを維持します。

```python
class FundIdResolver:
    """2階層キャッシュでファンドIDを解決.

    Tier 1: インメモリキャッシュ（最速、セッション中に構築）
    Tier 2: ファイルキャッシュ（JSON ファイル、プロセス再起動後も有効）
    Tier 3: API 呼び出し（キャッシュミス時のフォールバック）
    """

    def resolve(self, ticker: str) -> str | None:
        # Tier 1: インメモリキャッシュ
        if ticker in self._memory_cache:
            logger.debug("Fund ID resolved from in-memory cache", ticker=ticker)
            return self._memory_cache[ticker]

        # Tier 2: ファイルキャッシュ
        file_result = self._load_from_file_cache(ticker)
        if file_result is not None:
            # インメモリキャッシュに昇格
            self._memory_cache[ticker] = file_result
            return file_result

        # Tier 3: API 呼び出し（フォールバック）
        api_result = self._fetch_from_api(ticker)
        if api_result is not None:
            self._memory_cache[ticker] = api_result
            self._save_to_file_cache(ticker, api_result)
        return api_result
```

> **参照**: `src/market/etfcom/collectors.py` lines 1695-1731 -- 2階層キャッシュパターン

---

## 4. I/O 最適化パターン

### 4.1 I/O バウンド vs CPU バウンドの判定

最適化戦略はボトルネックの種類で決まります。
プロファイリングで判定してから最適化に着手すること。

```
処理のボトルネックは何か？
├── ネットワーク / ディスク待ち（I/O バウンド）
│   ├── 複数の独立した API 呼び出し → asyncio.gather()
│   ├── ファイル読み書き → ThreadPoolExecutor
│   └── DB クエリ → コネクションプール
│
└── 計算処理（CPU バウンド）
    ├── pandas/NumPy 演算 → ベクトル化（examples/vectorization.md 参照）
    ├── 大規模行列演算 → ProcessPoolExecutor
    └── ループ不可避 → Cython / Numba（本プロジェクトでは未使用）
```

---

### 4.2 asyncio.gather() — 並列 I/O パターン

複数の独立した I/O 操作を並列実行。セマフォで同時実行数を制限し、
対象サーバーへの負荷を制御します。

```python
import asyncio

async def extract_batch(
    self,
    articles: list[CollectedArticle],
    concurrency: int = 5,
) -> list[ExtractedArticle]:
    """Extract body text from multiple articles in parallel.

    Uses asyncio.Semaphore to limit concurrent extractions.
    """
    semaphore = asyncio.Semaphore(concurrency)

    async def extract_with_semaphore(article: CollectedArticle) -> ExtractedArticle:
        async with semaphore:
            return await self.extract(article)

    tasks = [extract_with_semaphore(article) for article in articles]
    return list(await asyncio.gather(*tasks))
```

**セマフォの同時実行数設計**:

| 対象 | 推奨値 | 根拠 |
|------|--------|------|
| 外部 API（Yahoo Finance 等） | 3-5 | レート制限回避 |
| ニュースサイト | 5-10 | サーバー負荷配慮 |
| ローカルファイル | 10-20 | OS のファイルディスクリプタ制限 |
| 内部 API | 20-50 | ネットワーク帯域が許す限り |

> **参照**: `src/news/extractors/base.py` lines 136-180 -- `extract_batch` の asyncio.gather + セマフォ実装

---

### 4.3 asyncio.gather() — 複数データソース並列収集

異なるデータソースから同時にデータを収集し、結果を統合します。

```python
async def async_collect_financial_news(
    symbols: list[str],
) -> pd.DataFrame:
    """CNBC・NASDAQ・yfinance の複数ソースを asyncio.gather() で並列実行."""

    async def _async_collect_yfinance_ticker() -> pd.DataFrame:
        # yfinance ticker ニュース取得
        ...

    async def _async_collect_yfinance_search() -> pd.DataFrame:
        # yfinance 検索ニュース取得
        ...

    # 全ソースを並列実行
    results = await asyncio.gather(
        _async_collect_cnbc(),
        _async_collect_nasdaq(),
        _async_collect_yfinance_ticker(),
        _async_collect_yfinance_search(),
        return_exceptions=True,  # 1つの失敗で全体を止めない
    )

    # 成功した結果のみ統合
    dfs = [r for r in results if isinstance(r, pd.DataFrame)]
    return pd.concat(dfs, ignore_index=True) if dfs else pd.DataFrame()
```

> **参照**: `src/news_scraper/async_unified.py` lines 45-177 -- 複数ソース並列収集

---

### 4.4 チャンク処理パターン

大量データを固定サイズのチャンクに分割して処理。
メモリ使用量を制御しながら、部分的な失敗をチャンク単位に局所化します。

```python
from typing import Final

DEFAULT_CHUNK_SIZE: Final[int] = 50

def process_chunked(
    securities: list[str],
    chunk_size: int = DEFAULT_CHUNK_SIZE,
) -> list[Result]:
    """証券リストをチャンク分割して処理."""
    if chunk_size <= 0:
        raise ValueError(f"chunk_size must be positive, got {chunk_size}")

    all_results: list[Result] = []

    for chunk_start in range(0, len(securities), chunk_size):
        chunk = securities[chunk_start : chunk_start + chunk_size]
        logger.info(
            "Processing chunk",
            chunk_start=chunk_start,
            chunk_size=len(chunk),
            total=len(securities),
        )
        results = process_single_chunk(chunk)
        all_results.extend(results)

    return all_results
```

> **参照**: `src/market/bloomberg/fetcher.py` lines 1605-1619 -- チャンク分割処理
> **参照**: `src/market/bloomberg/constants.py` lines 96-102 -- `DEFAULT_CHUNK_SIZE = 50` 定義

---

## 5. ボトルネック判定フロー

### 5.1 最適化の前にプロファイリング

**推測で最適化しない。必ず計測結果に基づいて判断する。**

```
1. profile_context で全体の実行時間を計測
2. @profile で関数呼び出しの内訳を確認
3. ボトルネック関数を特定
4. I/O バウンド or CPU バウンドを判定
5. 適切な最適化パターンを適用
6. 改善後に再計測して効果を確認
```

### 5.2 最適化判断フロー

```
計測結果のボトルネックは何か？
│
├── API 呼び出し待ち > 80%
│   ├── 独立したリクエスト → asyncio.gather()
│   ├── 依存リクエスト → リトライ + 指数バックオフ
│   └── 大量リクエスト → チャンク分割 + リトライ
│
├── ディスク I/O > 50%
│   ├── 読み込み → キャッシュ（TTL 付き）
│   ├── 書き込み → バッチ挿入
│   └── 大規模ファイル → Parquet 分割
│
├── 計算処理 > 50%
│   ├── pandas/NumPy → ベクトル化（vectorization.md 参照）
│   ├── ループ不可避 → ProcessPoolExecutor
│   └── メモリ圧迫 → チャンク処理 + ジェネレータ
│
└── メモリ使用量が過大
    ├── DataFrame 全体をメモリに保持 → Parquet 分割読み込み
    ├── キャッシュ肥大化 → TTL + max_entries 制限
    └── 大量オブジェクト → ジェネレータ / イテレータ
```

---

## まとめ: パフォーマンス最適化チェックリスト

実装時に以下を確認:

- [ ] 最適化の前に `profile_context` / `@profile` で計測を行ったか
- [ ] I/O バウンド / CPU バウンドのどちらかを判定したか
- [ ] リトライ設定に `RetryConfig`（指数バックオフ + ジッター）を使用しているか
- [ ] 大量 API リクエストをチャンク分割しているか
- [ ] キャッシュに TTL と `max_entries` 上限を設定しているか
- [ ] 並列 I/O に `asyncio.Semaphore` で同時実行数を制限しているか
- [ ] 大量データの DB 挿入に `batch_size` を指定しているか
- [ ] 改善前後で計測結果を比較し、改善率を記録しているか
