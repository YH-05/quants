# データパイプラインパターン集

Raw → Processed → Features 変換フロー、Universe 管理、スキーマ検証、
キャッシュ戦略、欠損値処理、外れ値処理フローを体系化したパターン集です。
既存コードベースの実装例と行番号注釈を含みます。

---

## 7つのルール

| # | ルール | 要点 |
|---|--------|------|
| 1 | Raw → Processed → Features 変換フロー | 取得→検証→変換→保存の4ステップを必ず踏む |
| 2 | Universe 管理 | 投資ユニバースをスキーマ付きで管理し Survivorship bias を防止 |
| 3 | スキーマ検証 | DataFrame の空チェック→必須カラム→型チェックの3段階で検証 |
| 4 | キャッシュ戦略 | DEFAULT（1h, in-memory）vs PERSISTENT（24h, file）の使い分け |
| 5 | 欠損値処理 | セクター中央値→全体中央値→中立値の3段階ルール |
| 6 | 外れ値処理フロー | winsorize → robust z-score → sector-neutral の順序で適用 |
| 7 | リトライとフォールバック | 指数バックオフ+ジッタで外部 API エラーに対応 |

---

## ルール 1: Raw → Processed → Features 変換フロー

### 1.1 3層データモデル

```
Raw（生データ）         → Processed（加工済み）      → Features（特徴量）
━━━━━━━━━━━━━━━━━━━━━   ━━━━━━━━━━━━━━━━━━━━━━━━   ━━━━━━━━━━━━━━━━━━━━
外部API応答そのまま       スキーマ検証済み             分析・モデル入力用
JSON / CSV / HTML        欠損値処理済み               正規化・中立化済み
型未確定                 型変換済み                   ファクタースコア

保存先: data/raw/        保存先: data/processed/      保存先: data/exports/
Parquet / JSON           Parquet                      Parquet / CSV
```

### 1.2 標準パイプライン: 取得→検証→変換→保存

```python
from database.parquet_schema import validate_stock_price_dataframe
from market.cache.cache import SQLiteCache, PERSISTENT_CACHE_CONFIG
from utils_core.logging import get_logger

logger = get_logger(__name__)

class MarketDataPipeline:
    """Standard market data pipeline: fetch -> validate -> transform -> save.

    Parameters
    ----------
    fetcher : YFinanceFetcher
        Data fetcher instance.
    cache : SQLiteCache | None
        Cache instance for intermediate data.
    """

    def __init__(
        self,
        fetcher: YFinanceFetcher,
        cache: SQLiteCache | None = None,
    ) -> None:
        self._fetcher = fetcher
        self._cache = cache
        logger.debug("Pipeline initialized", cache_enabled=cache is not None)

    def run(
        self,
        symbols: list[str],
        start: str,
        end: str,
    ) -> pd.DataFrame:
        """Execute the full pipeline.

        Parameters
        ----------
        symbols : list[str]
            Ticker symbols to fetch.
        start : str
            Start date (YYYY-MM-DD).
        end : str
            End date (YYYY-MM-DD).

        Returns
        -------
        pd.DataFrame
            Validated and transformed data.
        """
        # Step 1: キャッシュチェック
        cached = self._load_cache(symbols, start, end)
        if cached is not None:
            logger.info("Cache hit", symbols=symbols)
            return cached

        # Step 2: Raw データ取得
        raw = self._fetch(symbols, start, end)
        logger.info("Raw data fetched", row_count=len(raw))

        # Step 3: スキーマ検証（ルール 3 参照）
        validate_stock_price_dataframe(raw)

        # Step 4: 変換（欠損値処理、型変換）
        transformed = self._transform(raw)

        # Step 5: キャッシュ保存
        self._save_cache(transformed, symbols, start, end)

        return transformed
```

### 1.3 各ステップの責務

| ステップ | 責務 | 失敗時の対応 |
|----------|------|-------------|
| **取得（Fetch）** | 外部APIからRawデータ取得 | リトライ（ルール 7） |
| **検証（Validate）** | スキーマ準拠を確認 | `ValidationError` 送出 |
| **変換（Transform）** | 型変換、欠損値処理、正規化 | ログ出力+部分結果返却 |
| **保存（Save）** | Parquet/DB に永続化 | リトライ後にエラー送出 |

### 1.4 データ保存先の選択

| データ種別 | 保存形式 | 保存先 | 理由 |
|-----------|---------|--------|------|
| 株価 OHLCV | Parquet | `data/raw/yfinance/` | 大量の時系列データ、列指向アクセス |
| FRED 経済指標 | Parquet | `data/raw/fred/indicators/` | 時系列データ、分析クエリ向き |
| RSS フィード | JSON | `data/raw/rss/` | 構造化テキストデータ |
| 中間キャッシュ | SQLite | `data/cache/market_data.db` | TTL 付きキーバリュー |
| 分析結果 | CSV / Parquet | `data/exports/` | エクスポート用 |

---

## ルール 2: Universe 管理

### 2.1 投資ユニバースのスキーマ

投資ユニバースは Pydantic モデルでスキーマを定義し、バリデーション付きで管理する:

```python
from pydantic import BaseModel, ConfigDict, field_validator

class UniverseTicker(BaseModel):
    """A ticker entry in the investment universe.

    Parameters
    ----------
    ticker : str
        Ticker symbol (e.g. "AAPL").
    gics_sector : str
        GICS sector classification (e.g. "Information Technology").
    bloomberg_ticker : str
        Bloomberg ticker identifier (e.g. "AAPL US Equity").
    """

    model_config = ConfigDict(frozen=True)

    ticker: str
    gics_sector: str
    bloomberg_ticker: str = ""


class UniverseConfig(BaseModel):
    """Investment universe configuration.

    Parameters
    ----------
    tickers : list[UniverseTicker]
        List of tickers in the universe. Must not be empty.
    """

    model_config = ConfigDict(frozen=True)

    tickers: list[UniverseTicker]

    @field_validator("tickers")
    @classmethod
    def _tickers_non_empty(
        cls, v: list[UniverseTicker],
    ) -> list[UniverseTicker]:
        if not v:
            msg = "tickers must contain at least one ticker"
            raise ValueError(msg)
        return v
```

> **参照**: `src/dev/ca_strategy/types.py` lines 543-585 -- `UniverseTicker` / `UniverseConfig` の定義

### 2.2 Universe 生成パイプライン

```
Bloomberg Portfolio Data (Excel)
  → _flatten_entries()       # ネスト構造をフラット化
  → _write_universe()        # ticker, gics_sector, bloomberg_ticker を抽出
  → universe.json            # 検証済みユニバース
```

> **参照**: `src/dev/ca_strategy/generate_config.py` lines 120-158 -- `_write_universe()` による Universe 生成

### 2.3 Survivorship Bias 防止

**重要**: ユニバースは分析時点で存在した銘柄を含め、上場廃止・合併銘柄を除外してはならない。

| バイアス | 原因 | 防止策 |
|----------|------|--------|
| Survivorship | 上場廃止銘柄を除外してバックテスト | 分析時点のユニバースを使用 |
| Look-ahead | 将来のユニバース構成を使用 | Point-in-Time 制約（`as_of_date`） |

```python
# NG: 現在のユニバースで過去をバックテスト（Survivorship bias）
current_universe = load_universe("2026-01-01")  # 現在の構成銘柄
backtest(current_universe, start="2020-01-01")  # 2020年の上場廃止銘柄が除外される

# OK: 各時点のユニバースを使用
for rebalance_date in rebalance_dates:
    universe = load_universe(as_of=rebalance_date)  # その時点の構成銘柄
    backtest_period(universe, rebalance_date)
```

### 2.4 コーポレートアクション対応

上場廃止・合併時のウェイト再配分については `backtesting.md` セクション 6 を参照。

---

## ルール 3: スキーマ検証

### 3.1 検証の3段階

```
Step 1: 空チェック
  └─ DataFrame が空 → ValidationError

Step 2: 必須カラムチェック
  └─ カラム欠落 → ValidationError（欠落カラム一覧を含む）

Step 3: 型チェック
  └─ 型不一致 → ValidationError（期待型 vs 実際型を含む）
```

### 3.2 スキーマ定義パターン

```python
import datetime

class StockPriceSchema:
    """株価データスキーマ定義。

    Attributes
    ----------
    fields : dict[str, type]
        カラム名と期待される型のマッピング
    """

    fields: dict[str, type] = {
        "symbol": str,
        "date": datetime.date,
        "open": float,
        "high": float,
        "low": float,
        "close": float,
        "volume": int,
        "adjusted_close": float,
    }
```

> **参照**: `src/database/parquet_schema.py` lines 91-128 -- `StockPriceSchema` の定義

### 3.3 検証関数の実装

```python
def validate_stock_price_dataframe(df: pd.DataFrame) -> bool:
    """株価データフレームを検証する。

    Parameters
    ----------
    df : pd.DataFrame
        検証する DataFrame

    Returns
    -------
    bool
        検証成功時は True

    Raises
    ------
    ValidationError
        DataFrame が空、カラム欠落、型不一致の場合
    """
    # Step 1: 空チェック
    _check_empty_dataframe(df)

    # Step 2: 必須カラムチェック
    required_columns = set(StockPriceSchema.fields.keys())
    missing_columns = _check_missing_columns(df, required_columns)
    if missing_columns:
        raise ValidationError(
            f"Missing required columns: {', '.join(missing_columns)}. "
            f"Expected: {sorted(required_columns)}",
            missing_columns=missing_columns,
        )

    # Step 3: 型チェック
    type_mismatches = _check_type_mismatches(df, StockPriceSchema.fields)
    if type_mismatches:
        mismatch_details = [
            f"{col}: expected {exp.__name__}, got {act.__name__}"
            for col, (exp, act) in type_mismatches.items()
        ]
        raise ValidationError(
            f"Type mismatch in columns: {', '.join(mismatch_details)}",
            type_mismatches=type_mismatches,
        )

    return True
```

> **参照**: `src/database/parquet_schema.py` lines 341-438 -- `validate_stock_price_dataframe()` の完全な実装

### 3.4 検証のタイミング

| タイミング | 目的 | 例 |
|-----------|------|-----|
| **取得直後** | Raw データの整合性確認 | `validate_stock_price_dataframe(raw_df)` |
| **変換後** | Processed データの品質保証 | `validate_stock_price_dataframe(processed_df)` |
| **保存前** | 永続化データの最終確認 | `validate_stock_price_dataframe(final_df)` |

### 3.5 カスタムスキーマの作成

新しいデータ型には同じパターンでスキーマを定義する:

```python
class EconomicIndicatorSchema:
    """経済指標データスキーマ。"""

    fields: dict[str, type] = {
        "series_id": str,
        "date": datetime.date,
        "value": float,
        "unit": str,
    }
```

---

## ルール 4: キャッシュ戦略

### 4.1 2つのキャッシュモード

| モード | TTL | ストレージ | 最大エントリ数 | 用途 |
|--------|-----|-----------|---------------|------|
| **DEFAULT** | 1時間 | インメモリ | 1,000 | 開発・テスト、頻繁に変わるデータ |
| **PERSISTENT** | 24時間 | ファイル（SQLite） | 10,000 | 本番、日次データのキャッシュ |

```python
from market.cache.cache import DEFAULT_CACHE_CONFIG, PERSISTENT_CACHE_CONFIG

# DEFAULT: 開発・テスト向け（インメモリ、1h TTL）
DEFAULT_CACHE_CONFIG = CacheConfig(
    enabled=True,
    ttl_seconds=3600,      # 1 hour
    max_entries=1000,
    db_path=None,          # In-memory
)

# PERSISTENT: 本番向け（ファイルベース、24h TTL）
PERSISTENT_CACHE_CONFIG = CacheConfig(
    enabled=True,
    ttl_seconds=86400,     # 24 hours
    max_entries=10000,
    db_path=str(DEFAULT_CACHE_DB_PATH),
)
```

> **参照**: `src/market/cache/cache.py` lines 34-47 -- `DEFAULT_CACHE_CONFIG` / `PERSISTENT_CACHE_CONFIG` の定義

### 4.2 キャッシュキー生成

キャッシュキーは `symbol:start_date:end_date:interval:source` を SHA-256 ハッシュで生成:

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
    parts = [
        symbol.upper(),
        str(start_date) if start_date else "none",
        str(end_date) if end_date else "none",
        interval,
        source,
    ]
    key_str = ":".join(parts)
    return hashlib.sha256(key_str.encode()).hexdigest()
```

> **参照**: `src/market/cache/cache.py` lines 50-91 -- `generate_cache_key()` の実装

### 4.3 キャッシュ選択フローチャート

```
キャッシュ戦略の選択:
├── データの更新頻度は？
│   ├── リアルタイム / 分足 → キャッシュなし or DEFAULT（1h TTL）
│   ├── 日次（終値） → PERSISTENT（24h TTL）
│   └── 月次 / 四半期 → PERSISTENT（24h TTL）+ 長期キャッシュ検討
├── 環境は？
│   ├── テスト / 開発 → DEFAULT（インメモリ、高速）
│   └── 本番 / バッチ処理 → PERSISTENT（ファイルベース、永続）
└── データサイズは？
    ├── 小（< 1MB） → DEFAULT（インメモリで十分）
    └── 大（> 1MB） → PERSISTENT（ディスク保存でメモリ節約）
```

### 4.4 キャッシュ無効化

```python
class SQLiteCache:
    def cleanup_expired(self) -> int:
        """Remove expired cache entries.

        Returns
        -------
        int
            Number of removed entries.
        """
        # TTL 超過エントリを自動削除
        cutoff = datetime.now(UTC) - timedelta(seconds=self._config.ttl_seconds)
        # DELETE FROM cache WHERE created_at < cutoff
```

---

## ルール 5: 欠損値処理

### 5.1 3段階ルール

```
Stage 1: セクター中央値で補完
  └─ groupby(["date", "sector"])[factor].transform(fillna(median))

Stage 2: 全体中央値で補完（Stage 1 で埋まらなかった場合）
  └─ groupby("date")[factor].transform(fillna(median))

Stage 3: 中立値（0.5）で補完（Stage 2 でも埋まらなかった場合）
  └─ factor.fillna(0.5)
```

### 5.2 実装パターン

```python
def fill_missing_by_sector_median(
    df: pd.DataFrame,
    factor_list: list[str],
) -> pd.DataFrame:
    """Fill missing values using 3-stage rule.

    Stage 1: Sector median per date
    Stage 2: Overall median per date
    Stage 3: Neutral value (0.5)
    """
    logger.info(
        "Missing value analysis (before fill)",
        stats={f: int(df[f].isna().sum()) for f in factor_list},
        total_rows=len(df),
    )

    # Stage 1: セクター中央値で補完
    df[factor_list] = df.groupby(["date", "GICS Sector"])[factor_list].transform(
        lambda x: x.fillna(x.median())
    )

    # Stage 2: 全体中央値で補完
    for factor in factor_list:
        if df[factor].isna().sum() > 0:
            df[factor] = df.groupby("date")[factor].transform(
                lambda x: x.fillna(x.median())
            )

            # Stage 3: 中立値で補完
            remaining = df[factor].isna().sum()
            if remaining > 0:
                logger.warning(
                    "Using neutral value 0.5",
                    factor=factor,
                    remaining=int(remaining),
                )
                df[factor] = df[factor].fillna(0.5)

    return df
```

> **参照**: `src/market/factset/factset_utils.py` lines 2260-2347 -- `check_missing_value_and_fill_by_sector_median()` の完全な実装

### 5.3 各ステージの適用理由

| Stage | 手法 | 適用理由 |
|-------|------|---------|
| 1 | セクター中央値 | 同セクター内で類似した特性を持つため、最も精度の高い補完 |
| 2 | 全体中央値 | セクター内に十分なデータがない場合のフォールバック |
| 3 | 中立値（0.5） | 全データが欠損している極端なケースの最終手段 |

### 5.4 欠損値処理の注意事項

| 注意事項 | 説明 |
|----------|------|
| 前方参照禁止 | `fillna(method="ffill")` は PoiT 制約下で未来データを使用する可能性がある |
| 補完前にログ | 補完前後の欠損数をログに記録し、補完の影響を追跡可能にする |
| 中立値の選択 | ファクター値が 0-1 スケールの場合は 0.5、Z-score の場合は 0.0 |
| グループ単位で適用 | 日付ごとにグループ化して補完する（クロスセクション単位） |

---

## ルール 6: 外れ値処理フロー

### 6.1 処理順序: winsorize → robust z-score → sector-neutral

```
Raw Factor Values
  │
  ▼
Step 1: Winsorize（極端値クリッピング）
  │  limits=(0.01, 0.01) → 1st / 99th percentile でクリップ
  │
  ▼
Step 2: Robust Z-score（ロバスト正規化）
  │  median + MAD ベース（外れ値の影響を軽減）
  │
  ▼
Step 3: Sector-Neutral（セクター中立化）
  │  groupby(["date", "sector"]).transform(zscore)
  │
  ▼
Normalized Factor Values
```

### 6.2 Step 1: Winsorize

極端値を指定パーセンタイルでクリッピングする:

```python
def winsorize(
    data: pd.Series | pd.DataFrame,
    *,
    limits: tuple[float, float] = (0.01, 0.01),
) -> pd.Series | pd.DataFrame:
    """Winsorize data by clipping extreme values.

    Parameters
    ----------
    data : pd.Series | pd.DataFrame
        Input data to winsorize.
    limits : tuple[float, float], default=(0.01, 0.01)
        Lower and upper percentile limits for clipping.
        (0.01, 0.01) means clip at 1st and 99th percentiles.

    Raises
    ------
    ValidationError
        If limits are not valid percentiles (0-0.5).
    """
    lower_limit, upper_limit = limits

    if not (0 <= lower_limit <= 0.5 and 0 <= upper_limit <= 0.5):
        raise ValidationError(
            f"limits must be in range [0, 0.5], got ({lower_limit}, {upper_limit})"
        )

    lower_quantile = data.quantile(lower_limit)
    upper_quantile = data.quantile(1 - upper_limit)
    return data.clip(lower=lower_quantile, upper=upper_quantile)
```

> **参照**: `src/factor/core/normalizer.py` lines 284-345 -- `winsorize()` の実装

### 6.3 Step 2: Robust Z-score

median と MAD（Median Absolute Deviation）を使用した外れ値に頑健な正規化:

```python
_MAD_SCALE_FACTOR = 1.4826  # MAD → 標準偏差変換係数

def _zscore_series(series: pd.Series, *, robust: bool = True) -> pd.Series:
    """Calculate Z-score for a single series.

    robust=True の場合:
      center = median
      scale  = MAD * 1.4826（正規分布との整合性のため）

    robust=False の場合:
      center = mean
      scale  = std
    """
    if robust:
        center = series.median()
        mad = (series - center).abs().median()
        scale = mad * _MAD_SCALE_FACTOR
    else:
        center = series.mean()
        scale = series.std()

    if scale == 0 or bool(pd.isna(scale)):
        return pd.Series(np.nan, index=series.index)

    return (series - center) / scale
```

> **参照**: `src/factor/core/normalizer.py` lines 113-149 -- `_zscore_series()` の実装
> **参照**: `src/factor/core/normalizer.py` line 24 -- `_MAD_SCALE_FACTOR = 1.4826`

### 6.4 Step 3: Sector-Neutral（セクター中立化）

セクター内で Z-score を計算し、セクター間の水準差を除去:

```python
def normalize_by_group(
    data: pd.DataFrame,
    value_column: str,
    group_columns: list[str],
    *,
    method: str = "zscore",
) -> pd.DataFrame:
    """Normalize data within groups (sector-neutral normalization).

    Parameters
    ----------
    data : pd.DataFrame
        Input DataFrame.
    value_column : str
        Column to normalize.
    group_columns : list[str]
        Columns to group by (e.g. ["date", "sector"]).
    method : str
        "zscore" | "percentile_rank" | "quintile_rank" | "winsorize"
    """
    output_column = f"{value_column}_{method}"
    result = data.copy()
    result[output_column] = data.groupby(group_columns)[value_column].transform(
        normalize_func  # method に応じた正規化関数
    )
    return result
```

> **参照**: `src/factor/core/normalizer.py` lines 347-450 -- `normalize_by_group()` の完全な実装

### 6.5 外れ値処理の適用例

```python
from factor.core.normalizer import Normalizer

normalizer = Normalizer(min_samples=5)

# Step 1: Winsorize（1st / 99th パーセンタイルでクリップ）
winsorized = normalizer.winsorize(raw_factor, limits=(0.01, 0.01))

# Step 2: Robust Z-score
zscored = normalizer.zscore(winsorized, robust=True)

# Step 3: Sector-neutral normalization
sector_neutral = normalizer.normalize_by_group(
    df,
    value_column="factor_value",
    group_columns=["date", "sector"],
    method="zscore",
    robust=True,
)
```

### 6.6 正規化手法の選択

| 手法 | 用途 | 頑健性 |
|------|------|--------|
| `zscore` (robust=True) | ファクター分析のデフォルト | 外れ値に頑健（MAD ベース） |
| `zscore` (robust=False) | 正規分布に近いデータ | 外れ値に敏感（mean/std） |
| `percentile_rank` | 順位ベースの比較 | 分布に依存しない |
| `quintile_rank` | 5分位分類 | カテゴリ分析向け |
| `winsorize` | 前処理（他の手法と組み合わせ） | クリッピングのみ |

---

## ルール 7: リトライとフォールバック

外部 API 呼び出しのリトライ・指数バックオフ・ブラウザローテーションの詳細パターンは
**`performance.md` セクション 2** を参照してください。

ここではデータパイプライン固有の適用ガイドラインのみ記載します。

### 7.1 パイプラインでのリトライ適用箇所

| ステップ | リトライ | 根拠 |
|----------|---------|------|
| **取得（Fetch）** | 必須 | ネットワーク障害・レート制限は一時的 |
| **検証（Validate）** | 不要 | 入力データの問題であり、リトライで解決しない |
| **変換（Transform）** | 不要 | 計算処理でありリトライ不要 |
| **保存（Save）** | 条件付き | ディスク I/O 障害時のみリトライ |

### 7.2 パイプライン統合例

```python
from market.yfinance.fetcher import YFinanceFetcher
from market.yfinance.types import RetryConfig

# パイプラインのフェッチャーにリトライ設定を渡す
fetcher = YFinanceFetcher(
    retry_config=RetryConfig(
        max_attempts=3,
        initial_delay=1.0,
        max_delay=30.0,
        jitter=True,
    ),
)
```

> **詳細**: `performance.md` セクション 2（RetryConfig 定義、指数バックオフ実装、チャンク+リトライ、ブラウザローテーション）

---

## 統合パターン: 完全なデータパイプライン

### E2E パイプラインの実装例

```python
from database.parquet_schema import validate_stock_price_dataframe
from factor.core.normalizer import Normalizer
from market.cache.cache import SQLiteCache, PERSISTENT_CACHE_CONFIG
from market.yfinance.fetcher import YFinanceFetcher, DEFAULT_RETRY_CONFIG
from utils_core.logging import get_logger

logger = get_logger(__name__)

class FactorDataPipeline:
    """End-to-end factor data pipeline.

    Raw → Validated → Missing-filled → Winsorized → Z-scored → Sector-neutral
    """

    def __init__(self) -> None:
        self._fetcher = YFinanceFetcher(
            cache_config=PERSISTENT_CACHE_CONFIG,
            retry_config=DEFAULT_RETRY_CONFIG,
        )
        self._normalizer = Normalizer(min_samples=5)

    def run(
        self,
        universe: UniverseConfig,
        start: str,
        end: str,
        factor_columns: list[str],
    ) -> pd.DataFrame:
        """Execute full pipeline.

        Parameters
        ----------
        universe : UniverseConfig
            Investment universe configuration.
        start : str
            Start date (YYYY-MM-DD).
        end : str
            End date (YYYY-MM-DD).
        factor_columns : list[str]
            Factor columns to process.

        Returns
        -------
        pd.DataFrame
            Processed factor data with sector-neutral scores.
        """
        symbols = [t.ticker for t in universe.tickers]

        # Phase 1: Raw データ取得
        raw = self._fetch_raw(symbols, start, end)
        logger.info("Phase 1 complete: Raw data fetched", rows=len(raw))

        # Phase 2: スキーマ検証
        validate_stock_price_dataframe(raw)
        logger.info("Phase 2 complete: Schema validated")

        # Phase 3: 欠損値処理（3段階ルール）
        filled = fill_missing_by_sector_median(raw, factor_columns)
        logger.info("Phase 3 complete: Missing values filled")

        # Phase 4: 外れ値処理（winsorize → robust z-score）
        for col in factor_columns:
            filled[col] = self._normalizer.winsorize(
                filled[col], limits=(0.01, 0.01)
            )
        logger.info("Phase 4 complete: Outliers winsorized")

        # Phase 5: セクター中立化
        for col in factor_columns:
            filled = self._normalizer.normalize_by_group(
                filled,
                value_column=col,
                group_columns=["date", "sector"],
                method="zscore",
                robust=True,
            )
        logger.info("Phase 5 complete: Sector-neutral normalization")

        return filled
```

---

## まとめ: データパイプラインチェックリスト

実装時に以下を確認:

- [ ] Raw → Processed → Features の3層構造に従っているか
- [ ] 取得→検証→変換→保存の4ステップを省略していないか
- [ ] 投資ユニバースに Survivorship bias 防止策があるか
- [ ] スキーマ検証（空チェック→カラム→型）を取得直後に実行しているか
- [ ] キャッシュ戦略が用途に適切か（DEFAULT vs PERSISTENT）
- [ ] 欠損値処理が3段階ルール（セクター中央値→全体中央値→中立値）に従っているか
- [ ] 外れ値処理が正しい順序（winsorize → robust z-score → sector-neutral）で適用されているか
- [ ] 外部 API 呼び出しにリトライ設定（指数バックオフ+ジッタ）があるか
- [ ] 各ステップでログを出力しているか（処理前後の行数・欠損数）
