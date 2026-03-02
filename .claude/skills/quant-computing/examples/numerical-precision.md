# 数値精度パターン集

浮動小数点演算の落とし穴と防御策を体系化したパターン集です。
MAD スケールファクター、ゼロ除算防止、浮動小数点比較、dtype 選択基準を含みます。
既存コードベースの実装例と行番号注釈を含みます。

---

## 1. MAD スケールファクター 1.4826

### 1.1 数学的根拠

MAD（Median Absolute Deviation）を標準偏差の推定量として使用する際、正規分布を仮定した場合のスケール変換が必要です。

**定義**:

```
MAD = median(|X_i - median(X)|)
```

正規分布 N(mu, sigma^2) の場合、MAD と標準偏差 sigma の関係は以下の通りです：

```
MAD = sigma * Phi^{-1}(3/4) ≈ sigma * 0.6745
```

ここで `Phi^{-1}(3/4)` は標準正規分布の第3四分位点です。

したがって、MAD から標準偏差を推定するスケールファクターは：

```
1 / Phi^{-1}(3/4) ≈ 1 / 0.6745 ≈ 1.4826
```

**なぜ使うか**: MAD は中央値ベースの統計量であり、外れ値に対してロバスト。
通常の標準偏差が外れ値 1 点で大きく歪むのに対し、MAD はブレークダウンポイント 50% を持つ。

### 1.2 実装パターン

```python
# スケールファクターをモジュール定数として定義
_MAD_SCALE_FACTOR = 1.4826  # Scale factor to convert MAD to standard deviation

def _zscore_series(self, series: pd.Series, *, robust: bool) -> pd.Series:
    if robust:
        center = series.median()
        mad = (series - center).abs().median()
        scale = mad * _MAD_SCALE_FACTOR  # MAD → 標準偏差推定量
    else:
        center = series.mean()
        scale = series.std()

    if abs(scale) < _EPSILON or bool(pd.isna(scale)):
        return pd.Series(np.nan, index=series.index)

    return (series - center) / scale
```

> **参照**: `src/factor/core/normalizer.py` line 24 -- `_MAD_SCALE_FACTOR = 1.4826`
> **参照**: `src/factor/core/normalizer.py` lines 125-131 -- ロバスト Z-score 計算

### 1.3 使用上の注意

| 条件 | 推奨 |
|------|------|
| 正規分布に近いデータ | `_MAD_SCALE_FACTOR` 使用可 |
| 重い裾を持つ分布（金融リターン） | 推定精度は低下するが、ロバスト性が優先される |
| 小サンプル（n < 20） | MAD 自体の推定精度が低いため注意 |

---

## 2. ゼロ除算防止パターン（`_EPSILON`）

### 2.1 基本パターン: 閾値による防御

浮動小数点演算では、数学的にゼロでない値が計算上ゼロに近くなるケースが頻発します。
`_EPSILON` を定義し、閾値未満の値をゼロとみなすことで安全に処理します。

```python
# Threshold for considering standard deviation as effectively zero
# This handles floating-point precision issues
_EPSILON = 1e-15
```

> **参照**: `src/strategy/risk/calculator.py` line 20 -- `_EPSILON = 1e-15`

### 2.2 なぜ 1e-15 か

IEEE 754 倍精度浮動小数点（float64）の**マシンイプシロン**は約 2.22e-16 です。
`1e-15` はマシンイプシロンの約 4.5 倍であり、以下のバランスを取っています：

| 閾値 | 特性 |
|------|------|
| `1e-16`（マシンイプシロン付近） | 丸め誤差で閾値判定が不安定 |
| **`1e-15`（推奨）** | **マシンイプシロンより十分大きく、実用上のゼロ判定に適切** |
| `1e-10` | ウェイト正規化など比較的大きな値の差分チェック向け |
| `1e-6` | 大きすぎ、有意な差を無視してしまうリスク |

### 2.3 パターン: ボラティリティ計算

標準偏差がゼロ（定数リターン）の場合にゼロ除算を防止：

```python
def volatility(self) -> float:
    std = float(self._returns.std())

    # Handle floating-point precision: treat very small std as zero
    if std < _EPSILON:
        logger.debug(
            "Standard deviation below threshold, returning 0",
            daily_std=std,
            threshold=_EPSILON,
        )
        return 0.0

    volatility = std * np.sqrt(self._annualization_factor)
    return float(volatility)
```

> **参照**: `src/strategy/risk/calculator.py` lines 140-149 -- ボラティリティ計算のゼロ防御

### 2.4 パターン: Sharpe レシオ（分子・分母の両方を検査）

分母（標準偏差）がゼロの場合、分子の符号に応じて inf / -inf / nan を返す：

```python
def sharpe_ratio(self) -> float:
    daily_rf = self._risk_free_rate / self._annualization_factor
    excess_returns = self._returns - daily_rf

    mean_excess = float(excess_returns.mean())
    std_excess = float(excess_returns.std())

    # Handle floating-point precision: treat very small std as zero
    if std_excess < _EPSILON:
        # Zero standard deviation means infinite Sharpe if positive return
        if mean_excess > _EPSILON:
            return float("inf")
        elif mean_excess < -_EPSILON:
            return float("-inf")
        else:
            return float("nan")

    return float((mean_excess / std_excess) * np.sqrt(self._annualization_factor))
```

> **参照**: `src/strategy/risk/calculator.py` lines 193-209 -- Sharpe レシオのゼロ除算防御

### 2.5 パターン: NaN との複合チェック

`math.isnan()` と `_EPSILON` チェックを組み合わせて、NaN とゼロ近傍の両方を防御：

```python
downside_std = float(negative_returns.std())

# Handle floating-point precision: treat very small std as zero
# Also handle NaN case
if math.isnan(downside_std) or downside_std < _EPSILON:
    if excess_return > _EPSILON:
        return float("inf")
    elif excess_return < -_EPSILON:
        return float("-inf")
    else:
        return float("nan")
```

> **参照**: `src/strategy/risk/calculator.py` lines 284-298 -- Sortino レシオの NaN + ゼロ複合防御

### 2.6 パターン: ベータ計算（分散がゼロ）

ベンチマークの分散がゼロ（ベンチマークが定数）の場合のベータ計算：

```python
def beta(self, benchmark_returns: pd.Series) -> float:
    covariance = portfolio_aligned.cov(benchmark_aligned)
    benchmark_variance = benchmark_aligned.var()

    if benchmark_variance < _EPSILON:
        logger.warning(
            "Benchmark variance is effectively zero, returning NaN",
            benchmark_variance=benchmark_variance,
        )
        return float("nan")

    return float(covariance / benchmark_variance)
```

> **参照**: `src/strategy/risk/calculator.py` lines 583-588 -- ベータ計算のゼロ分散防御

### 2.7 パターン: ゼロスケール検出（MAD = 0）

データが全て同じ値の場合、MAD もスケールもゼロになる：

```python
# AIDEV-NOTE: ソースコード (normalizer.py) は `scale == 0` だが、
# epsilon 比較が本来望ましい（浮動小数点の直接比較を避ける原則）
if abs(scale) < _EPSILON or bool(pd.isna(scale)):
    logger.warning(
        "Zero or NaN scale in zscore calculation",
        robust=robust,
        center=center,
        scale=scale,
    )
    return pd.Series(np.nan, index=series.index)
```

> **参照**: `src/factor/core/normalizer.py` lines 133-140 -- ゼロスケール検出

---

## 3. ウェイト正規化の閾値

### 3.1 なぜ `1e-10` か

ポートフォリオウェイトの合計が 1.0 であるべき場合の「ずれ」の検出には、
`_EPSILON`（1e-15）より大きい `1e-10` を閾値として使用します。

| 閾値 | 用途 |
|------|------|
| `1e-15` | 標準偏差・分散のゼロ近傍判定（演算結果の精度限界） |
| **`1e-10`** | **ウェイト合計の 1.0 からの乖離判定（累積的な丸め誤差の許容）** |

ウェイト正規化では、複数の浮動小数点数を合計するため、1e-15 では厳しすぎます。
30 銘柄のウェイトを合計した場合、累積丸め誤差は O(n * epsilon) で 1e-14 程度に達しうるため、
余裕を持って `1e-10` を閾値とします。

### 3.2 実装パターン

```python
# Normalize if needed (tickers might have been dropped)
total = sum(current_weights.values())
if total > 0 and abs(total - 1.0) > 1e-10:
    current_weights = {k: v / total for k, v in current_weights.items()}
```

> **参照**: `src/dev/ca_strategy/return_calculator.py` lines 500-502 -- ウェイト正規化

### 3.3 リバランス時のウェイト正規化

```python
rebal_total = sum(current_weights.values())
if rebal_total > 0 and abs(rebal_total - 1.0) > 1e-10:
    current_weights = {
        k: v / rebal_total for k, v in current_weights.items()
    }
```

> **参照**: `src/dev/ca_strategy/return_calculator.py` lines 536-540 -- リバランス時のウェイト正規化

### 3.4 ドリフト後のウェイト正規化

Buy-and-Hold 戦略ではウェイトが日々ドリフトするため、毎日再正規化が必要：

```python
# Drift weights based on today's returns (Buy-and-Hold)
new_values: dict[str, float] = {}
for t, w in current_weights.items():
    ret = day_returns.get(t, 0.0)
    if pd.isna(ret):
        ret = 0.0
    new_values[t] = w * (1.0 + ret)
drift_total = sum(new_values.values())
if drift_total > 0:
    current_weights = {
        t: v / drift_total for t, v in new_values.items()
    }
```

> **参照**: `src/dev/ca_strategy/return_calculator.py` lines 551-563 -- ドリフト後の正規化

---

## 4. 浮動小数点比較の推奨手法

### 4.1 直接比較の禁止

浮動小数点数に `==` を使用してはいけない：

```python
# NG: 浮動小数点の直接比較
if result == 0.0:  # 丸め誤差で false になる可能性
    ...

if total == 1.0:  # 累積誤差で false になる可能性
    ...

# OK: epsilon 比較
if abs(result) < _EPSILON:
    ...

if abs(total - 1.0) < 1e-10:
    ...
```

### 4.2 テストでの比較手法

#### pytest.approx（推奨: 単一値・Series の比較）

```python
# 相対許容誤差（デフォルト 1e-6）
assert returns.iloc[1] == pytest.approx(0.00995, rel=0.01)

# 絶対許容誤差
assert stats.mean == pytest.approx(102.5, rel=0.01)
```

> **参照**: `tests/analyze/integration/test_market_integration.py` line 223 -- `pytest.approx`
> **参照**: `tests/analyze/unit/technical/test_technical.py` line 86 -- `pytest.approx`

#### math.isclose（推奨: 比率の比較）

```python
# 相対許容誤差でボラティリティ比率を検証
expected_ratio = abs(scale_factor)
actual_ratio = vol_scaled / vol_base
assert math.isclose(actual_ratio, expected_ratio, rel_tol=1e-5)

# 定数シフトでの不変性検証
assert math.isclose(vol_original, vol_shifted, rel_tol=1e-9)
```

> **参照**: `tests/strategy/property/risk/test_calculator.py` line 111 -- `math.isclose`
> **参照**: `tests/strategy/property/risk/test_calculator.py` line 153 -- `math.isclose`

#### np.allclose / np.isclose（推奨: 配列の比較）

```python
# 行平均がゼロであること（Z-score 後）
assert np.allclose(row_means, 0, atol=1e-10)

# 単一値の比較
assert np.isclose(actual_momentum, expected_momentum, rtol=1e-4)
```

> **参照**: `src/factor/docs/development-guidelines.md` line 890 -- `np.allclose`
> **参照**: `src/factor/docs/development-guidelines.md` line 1052 -- `np.isclose`

### 4.3 比較手法の選択基準

| 手法 | 用途 | 推奨場面 |
|------|------|----------|
| `abs(x) < _EPSILON` | ゼロ近傍判定 | 本番コード、ゼロ除算防止 |
| `abs(x - y) < threshold` | 差分ベースの比較 | 本番コード、ウェイト合計の検証 |
| `pytest.approx(expected, rel=...)` | テストアサーション | 単一値の検証、可読性重視 |
| `math.isclose(a, b, rel_tol=...)` | テストアサーション | 比率や数学的性質の検証 |
| `np.allclose(a, b, atol=...)` | テストアサーション | 配列全体の検証 |
| `np.isclose(a, b, rtol=...)` | テストアサーション | 配列要素ごとの検証 |

### 4.4 許容誤差の設計指針

| 許容誤差 | 用途 | 根拠 |
|----------|------|------|
| `rel_tol=1e-9` | 数学的に等しいはずの値（定数シフトの不変性） | float64 の有効桁数 15-16 桁の範囲 |
| `rel_tol=1e-5` | スケーリング比率の検証 | 累積演算の丸め誤差を許容 |
| `rel_tol=1e-4` | モメンタム・リターン計算 | 入力データの丸めと中間演算の誤差 |
| `rel=0.01` (1%) | 概算値の検証 | 統計量の推定誤差を含む |
| `atol=1e-10` | ゼロに近い値の絶対比較 | 正規化後の平均値がゼロか |

---

## 5. dtype 選択基準

### 5.1 float64（デフォルト）

金融計算では **float64 を標準** とする。pandas の `pd.Series(dtype=float)` は float64 です。

```python
# 空の Series を作成する場合は dtype=float を明示
result["sector_zscore"] = pd.Series(dtype=float)
result["sector_rank"] = pd.Series(dtype=float)
```

> **参照**: `src/dev/ca_strategy/neutralizer.py` lines 106-107 -- `pd.Series(dtype=float)`

```python
# 空のリターン Series を返す場合
return pd.Series([], dtype=float)
```

> **参照**: `src/dev/ca_strategy/return_calculator.py` line 123 -- `pd.Series([], dtype=float)`

### 5.2 dtype 選択フローチャート

```
金融計算で使用する値か？
├── Yes: 通貨金額（USD cents 精度が必要）か？
│   ├── Yes → Decimal（銀行・決済系、本プロジェクトでは未使用）
│   └── No: リターン・リスク指標・スコアか？
│       └── Yes → float64（デフォルト）
└── No: 整数カウント・ID・ランクか？
    ├── Yes → int64
    └── No: ブーリアンフラグか？
        ├── Yes → bool
        └── No: カテゴリ・ラベルか？
            └── Yes → str / category
```

### 5.3 float64 vs float32

| 項目 | float64 | float32 |
|------|---------|---------|
| 有効桁数 | 15-16 桁 | 6-7 桁 |
| マシンイプシロン | 2.22e-16 | 1.19e-7 |
| メモリ | 8 bytes | 4 bytes |
| 推奨用途 | **金融計算全般（標準）** | 大規模 ML 推論（本プロジェクトでは不使用） |

**float32 を使わない理由**:
- Sharpe レシオ計算で日次リターンの平均（1e-4 オーダー）を標準偏差（1e-2 オーダー）で割る際、float32 では有効桁数が不足
- ウェイト合計の 1.0 からの乖離チェック（1e-10）が float32 の精度限界（1e-7）を下回る
- pandas のデフォルトが float64 であり、混在させるとキャスト時に性能劣化

---

## 6. プロパティベーステストにおける数値精度

### 6.1 assume() による前提条件のフィルタリング

Hypothesis テストでは、ゼロ近傍の入力を `assume()` で除外：

```python
from hypothesis import assume, given, settings
from hypothesis import strategies as st

@given(
    returns=st.lists(
        st.floats(min_value=-0.1, max_value=0.1, allow_nan=False, allow_infinity=False),
        min_size=20, max_size=100,
    ),
)
@settings(max_examples=50)
def test_プロパティ_定数加算でボラティリティ不変(self, returns: list[float]) -> None:
    original_series = pd.Series(returns)

    # 標準偏差が実質的にゼロでない場合のみテスト
    assume(float(original_series.std()) > _EPSILON)

    shifted_series = original_series + 0.05
    calc_original = RiskCalculator(original_series)
    calc_shifted = RiskCalculator(shifted_series)

    # 浮動小数点精度の問題を考慮して相対許容誤差を緩和
    assert math.isclose(
        calc_original.volatility(), calc_shifted.volatility(), rel_tol=1e-9
    )
```

> **参照**: `tests/strategy/property/risk/test_calculator.py` lines 122-153 -- `assume()` による前提条件フィルタリング

### 6.2 strategies の範囲制限

金融データの現実的な範囲に制限してテストの有効性を向上：

```python
# 日次リターンの現実的な範囲（-10% 〜 +10%）
returns=st.lists(
    st.floats(min_value=-0.1, max_value=0.1, allow_nan=False, allow_infinity=False),
    min_size=20,
    max_size=200,
)

# リスクフリーレート（0% 〜 10%）
risk_free_rate=st.floats(min_value=0.0, max_value=0.1, allow_nan=False)
```

> **参照**: `tests/strategy/property/risk/test_calculator.py` lines 159-168 -- strategies の範囲設計

---

## 7. 閾値定数の命名・配置規約

### 7.1 命名規約

| パターン | 命名 | 例 |
|----------|------|-----|
| ゼロ近傍閾値 | `_EPSILON` | `_EPSILON = 1e-15` |
| スケールファクター | `_XXX_SCALE_FACTOR` | `_MAD_SCALE_FACTOR = 1.4826` |
| ウェイト閾値 | インライン定数 | `abs(total - 1.0) > 1e-10` |

### 7.2 配置規約

```python
# モジュール先頭（import の後、クラス定義の前）に配置
import numpy as np
import pandas as pd

# Constants
_EPSILON = 1e-15
_MAD_SCALE_FACTOR = 1.4826

class Calculator:
    ...
```

### 7.3 コメント規約

閾値定数には **用途と根拠** をコメントで記載：

```python
# Threshold for considering standard deviation as effectively zero
# This handles floating-point precision issues
_EPSILON = 1e-15

# Scale factor to convert MAD to standard deviation
_MAD_SCALE_FACTOR = 1.4826
```

---

## まとめ: 数値精度チェックリスト

実装時に以下を確認:

- [ ] 浮動小数点比較に `==` を直接使用していないか
- [ ] 除算の分母に `_EPSILON` チェックを入れているか
- [ ] `pd.isna()` / `math.isnan()` と `_EPSILON` の複合チェックを行っているか
- [ ] ウェイト正規化の閾値は `1e-10` 以上を使用しているか
- [ ] テストでは `pytest.approx` / `math.isclose` / `np.allclose` を使用しているか
- [ ] 許容誤差の値に根拠があるか（マシンイプシロン、累積誤差、推定誤差）
- [ ] 空の Series/DataFrame は `dtype=float` を明示しているか
- [ ] 閾値定数はモジュール先頭に配置し、コメントで根拠を記載しているか
- [ ] Hypothesis テストで `assume()` によりゼロ近傍の入力を除外しているか
