---
name: quant-computing
description: 金融数値計算・DB設計・データパイプラインのナレッジベース。数値精度、ベクトル化、高速化、テスト、リターン計算標準、リスク指標、バックテスト、DBスキーマ、データパイプラインの9領域を体系化し、新規実装時にプロアクティブに参照。
allowed-tools: Read
---

# Quantitative Computing スキル

金融数値計算・DB設計・データパイプラインに関するナレッジベーススキルです。

## 目的

このスキルは以下の9領域を体系化し、新規実装時の暗黙知を明文化します：

1. **数値精度**: 浮動小数点演算の落とし穴と防御策（epsilon 比較、Decimal、丸め）
2. **ベクトル化**: pandas/NumPy のベクトル演算パターン（ループ排除、groupby + transform）
3. **高速化**: プロファイリング起点のパフォーマンス最適化（I/Oバウンド vs CPUバウンド判定）
4. **テスト**: 数値計算のプロパティベーステストと許容誤差設計（Hypothesis、`pytest.approx`）
5. **リターン計算標準**: simple vs log リターンの使い分け、年率化の複利必須ルール
6. **リスク指標**: Sharpe/Sortino/VaR/最大ドローダウンの計算規約と前提条件
7. **バックテスト**: Point-in-Time 制約、ルックアヘッドバイアス防止、サバイバーシップバイアス対策
8. **DBスキーマ**: SQLite vs DuckDB の選択基準、Parquet スキーマ定義パターン
9. **データパイプライン**: 取得→検証→変換→保存の標準フローとキャッシュ戦略

## いつ使用するか

### プロアクティブ使用（自動で検討）

以下の状況では、ユーザーが明示的に要求しなくても参照：

1. **数値計算コード実装時**
   - リターン・リスク指標の計算
   - 浮動小数点比較を含むロジック
   - pandas/NumPy の集計・変換処理

2. **データパイプライン構築時**
   - 市場データの取得・保存処理
   - Parquet/SQLite/DuckDB のスキーマ設計
   - キャッシュ戦略の決定

3. **バックテスト・ファクター分析実装時**
   - Point-in-Time 制約の適用
   - ポートフォリオリターンの計算
   - セクター中立化・Z-score 正規化

4. **テスト作成時**
   - 数値計算の許容誤差設定
   - プロパティベーステストの不変条件定義
   - 境界値・エッジケースの特定

## クイックリファレンス

### 1. 数値精度

```python
# 浮動小数点比較には epsilon を使用
_EPSILON = 1e-15

if abs(value) < _EPSILON:
    return 0.0  # ゼロとみなす

# pytest での近似比較
assert result == pytest.approx(expected, rel=1e-6)
```

### 2. ベクトル化

```python
# NG: Python ループ
for i in range(len(df)):
    df.iloc[i]["return"] = df.iloc[i]["close"] / df.iloc[i - 1]["close"] - 1

# OK: ベクトル演算
df["return"] = df.groupby("symbol")["close"].pct_change()
```

### 3. 高速化

```python
from finance.utils.profiling import profile_context

with profile_context("リターン計算"):
    returns = df.groupby("symbol")["close"].pct_change()

# I/O バウンド → asyncio / ThreadPool
# CPU バウンド → ベクトル化 / ProcessPool
```

### 4. テスト

```python
from hypothesis import given
from hypothesis import strategies as st

@given(returns=st.lists(st.floats(min_value=-0.5, max_value=0.5, allow_nan=False, allow_infinity=False), min_size=2))
def test_プロパティ_ボラティリティは非負(returns: list[float]) -> None:
    series = pd.Series(returns)
    assert RiskCalculator(series).volatility() >= 0.0
```

### 5. リターン計算標準

```python
# simple リターン: 個別銘柄・短期分析
simple_return = (price_end / price_start) - 1

# log リターン: ポートフォリオ集計・時系列加法性が必要な場合
log_return = np.log(price_end / price_start)

# 年率化は複利必須（単利禁止）
annualized = (1 + cumulative_return) ** (252 / n_days) - 1
```

### 6. リスク指標

```python
# 年率化ボラティリティ
volatility = daily_returns.std() * np.sqrt(252)

# Sharpe（超過リターンの標準偏差で除算）
daily_rf = annual_rf / 252
excess_returns = daily_returns - daily_rf
sharpe = (excess_returns.mean() / excess_returns.std()) * np.sqrt(252)

# Sortino（下方偏差のみ使用、閾値は 0）
downside = daily_returns[daily_returns < 0]
sortino = (daily_returns.mean() - daily_rf) / downside.std() * np.sqrt(252)
```

### 7. バックテスト

```python
# Point-in-Time 制約: as_of_date 以降のデータを使用禁止
scores = scores_df[scores_df["as_of_date"] <= rebalance_date]

# コーポレートアクション対応: 上場廃止銘柄のウェイトを再配分
if ticker in delisted_tickers:
    weights[ticker] = 0.0
    # 残存銘柄に比例配分
```

### 8. DBスキーマ

```python
# SQLite: メタデータ・設定・小規模参照データ
# DuckDB: 大規模時系列データの分析クエリ
# Parquet: 中間データ・バッチ処理の入出力

# Parquet スキーマ定義
class StockPriceSchema:
    COLUMNS = {
        "symbol": str, "date": "datetime64[ns]",
        "open": float, "high": float, "low": float,
        "close": float, "volume": int, "adjusted_close": float,
    }
```

### 9. データパイプライン

```python
# 標準フロー: 取得 → 検証 → 変換 → 保存
raw_data = fetcher.fetch(symbols, start, end)          # 取得
validated = schema.validate(raw_data)                   # 検証
transformed = calculator.calculate_returns(validated)   # 変換
storage.save_parquet(transformed, path)                 # 保存

# キャッシュ: ファイルベース（Parquet）、TTL 付き
```

## リソース

このスキルには以下のリソースが含まれています：

### ./examples/numerical-precision.md

数値精度パターン集：

- epsilon 比較の実装
- Decimal を使うべきケース
- 丸めによる累積誤差の防止

### ./examples/vectorization.md

ベクトル化パターン集：

- ループ → ベクトル演算の変換例
- groupby + transform の活用
- np.where / np.select による条件分岐

### ./examples/performance.md

高速化パターン集：

- I/O バウンド vs CPU バウンドの判定
- asyncio / ThreadPool / ProcessPool の選択
- メモ化・キャッシュの実装

### ./examples/testing.md

数値計算テストパターン集：

- Hypothesis 戦略の設計例
- pytest.approx の使い方
- 境界値テストの設計

### ./examples/returns.md

リターン計算パターン集：

- simple / log リターンの実装
- 年率化（複利）の正しい実装
- マルチピリオドリターンの計算

### ./examples/risk-metrics.md

リスク指標パターン集：

- Sharpe / Sortino / Treynor の計算
- VaR / CVaR の実装
- 最大ドローダウンの計算

### ./examples/backtesting.md

バックテストパターン集：

- Point-in-Time 制約の実装
- ルックアヘッドバイアスの検出
- コーポレートアクション対応

### ./examples/db-schema.md

DBスキーマパターン集：

- SQLite vs DuckDB の選択基準
- Parquet スキーマ定義と検証
- マイグレーション規約

### ./examples/data-pipeline.md

データパイプラインパターン集：

- 取得→検証→変換→保存の標準フロー
- キャッシュ戦略（TTL、無効化）
- エラーリトライとフォールバック

## 使用例

### 例1: リターン計算関数の新規実装

**状況**: ポートフォリオの日次リターンを計算する関数を追加

**参照領域**: リターン計算標準、ベクトル化、数値精度、テスト

```python
_EPSILON = 1e-15

def calculate_portfolio_return(
    weights: dict[str, float],
    daily_returns: pd.DataFrame,
) -> pd.Series:
    """Calculate weighted portfolio daily returns."""
    weight_series = pd.Series(weights)
    if abs(weight_series.sum() - 1.0) > _EPSILON:
        raise ValueError(f"Weights must sum to 1.0, got {weight_series.sum():.6f}")
    return daily_returns[list(weights.keys())].dot(weight_series)
```

---

### 例2: リスク指標のプロパティベーステスト

**状況**: RiskCalculator に Hypothesis テストを追加

**参照領域**: リスク指標、テスト、数値精度

```python
@given(returns=st.lists(st.floats(min_value=-0.3, max_value=0.3, allow_nan=False), min_size=20))
def test_プロパティ_ボラティリティは常に非負(self, returns: list[float]) -> None:
    calc = RiskCalculator(pd.Series(returns), risk_free_rate=0.02)
    assert calc.volatility() >= 0.0
```

---

### 例3: Point-in-Time 制約付きバックテスト

**状況**: CA Strategy パイプラインで銘柄スコアを集約

**参照領域**: バックテスト

```python
def aggregate_scores(scores_df: pd.DataFrame, rebalance_date: date) -> pd.DataFrame:
    """Aggregate stock scores with Point-in-Time constraint."""
    pit_scores = scores_df[scores_df["as_of_date"] <= rebalance_date]
    return pit_scores.sort_values("as_of_date").groupby("ticker").last()
```

---

### 例4: DuckDB vs SQLite の選択判断

**状況**: 新しいデータストアの選択

**参照領域**: DBスキーマ

| 条件 | SQLite | DuckDB |
|------|--------|--------|
| レコード数 < 10万 / CRUD 中心 / メタデータ | 推奨 | - |
| レコード数 > 100万 / 集計クエリ / 時系列分析 / Parquet 読込 | - | 推奨 |

---

### 例5: データパイプラインの標準実装

**状況**: 新しい市場データフェッチャーを追加

**参照領域**: データパイプライン

```python
class MarketDataPipeline:
    """Standard market data pipeline: fetch -> validate -> transform -> save."""

    def run(self, symbols: list[str], start: str, end: str) -> pd.DataFrame:
        cached = self._load_cache(symbols, start, end)
        if cached is not None:
            return cached
        raw = self._fetch(symbols, start, end)
        validate_stock_price_dataframe(raw)
        transformed = self._transform(raw)
        self._save_cache(transformed, symbols, start, end)
        return transformed
```

## 品質基準

### 必須（MUST）

- [ ] 浮動小数点比較に `==` を直接使用しない（epsilon 比較または `pytest.approx` を使用）
- [ ] リターンの年率化に単利公式 `return * 252/n` を使用しない（複利公式を使用）
- [ ] バックテストで未来データを参照しない（Point-in-Time 制約を適用）
- [ ] pandas/NumPy の集計処理で Python ループを使用しない（ベクトル演算を使用）
- [ ] 数値計算関数に対してプロパティベーステスト（Hypothesis）を作成する
- [ ] リスク指標の計算でゼロ除算を防御する（epsilon チェック）
- [ ] データパイプラインで取得データを保存前に検証する（スキーマ検証）
- [ ] DB 選択時にデータ量とクエリパターンに基づいて SQLite/DuckDB を判断する

### 推奨（SHOULD）

- リターン計算で simple/log の選択理由をコメントまたは Docstring に記載
- リスク指標の前提条件（年率化係数、リスクフリーレート）を明示
- パフォーマンス改善前にプロファイリング結果を測定
- Parquet スキーマを `database.parquet_schema` で定義・検証
- キャッシュに TTL を設定し、古いデータの自動無効化を実装
- バックテストでサバイバーシップバイアス対策を実装
- ベクトル演算の変換前後で計測結果を記録

## 関連スキル

- **coding-standards**: Python コーディング規約（型ヒント、命名規則、Docstring）
- **tdd-development**: TDD 開発プロセス（Red-Green-Refactor サイクル）
- **error-handling**: エラーハンドリングパターン（Simple/Rich パターン選択）
- **ensure-quality**: コード品質の自動改善（`make check-all` 相当）

## 参考資料

- `src/strategy/risk/calculator.py`: リスク指標計算の実装例
- `src/factor/core/return_calculator.py`: リターン計算の実装例
- `src/dev/ca_strategy/neutralizer.py`: セクター中立化の実装例
- `src/dev/ca_strategy/return_calculator.py`: ポートフォリオリターン計算（PoiT 対応）
- `src/database/parquet_schema.py`: Parquet スキーマ定義パターン
- `src/database/db/duckdb_client.py`: DuckDB 接続パターン
- `src/database/db/sqlite_client.py`: SQLite 接続パターン
- `template/src/template_package/utils/profiling.py`: プロファイリングユーティリティ
