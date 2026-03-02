# 数値計算テストパターン集

浮動小数点比較（`pytest.approx`, `np.isclose`, rtol/atol）、Hypothesis ストラテジー設計、
エッジケーステストパターンを体系化したパターン集です。
既存コードベースの実装例と行番号注釈を含みます。

---

## tdd-development スキルとの役割分担

| 領域 | tdd-development | quant-computing/testing |
|------|-----------------|------------------------|
| TDD サイクル（Red→Green→Refactor） | **主担当** | 対象外 |
| テスト命名規則（日本語命名） | **主担当** | 対象外 |
| テストファイル配置（unit/property/integration） | **主担当** | 対象外 |
| 三角測量・仮実装→一般化 | **主担当** | 対象外 |
| 浮動小数点比較の許容誤差設計 | 対象外 | **主担当** |
| Hypothesis の数値ストラテジー設計 | 対象外 | **主担当** |
| NaN/inf/empty のエッジケースパターン | 対象外 | **主担当** |
| `assume()` による前提条件フィルタリング | 対象外 | **主担当** |
| プロパティベーステストの「何をテストするか」 | 概要のみ | **詳細パターン集** |

**使い分け**: テストの「進め方・書き方」は `tdd-development`、数値計算固有の「何を・どう検証するか」は本ドキュメントを参照。

---

## 1. rtol/atol 選択基準

### 1.1 相対許容誤差（rtol）vs 絶対許容誤差（atol）

| パラメータ | 判定式 | 推奨場面 |
|-----------|--------|----------|
| `rtol`（相対） | `|a - b| <= rtol * max(|a|, |b|)` | 値のスケールが大きい場合（リターン、リスク指標） |
| `atol`（絶対） | `|a - b| <= atol` | 値がゼロ付近の場合（正規化後の平均、Z-score） |

**選択フロー**:

```
期待値はゼロに近いか？
├── Yes → atol を使用（rtol はゼロ付近で不安定）
│   例: 正規化後の平均 → atol=1e-10
│   例: 定数リターンのモメンタム → atol=1e-10
└── No → rtol を使用（スケールに依存しない比較）
    ├── 数学的に等しいはずの値 → rel_tol=1e-9
    ├── スケーリング比率の検証 → rel_tol=1e-5
    ├── リターン・モメンタム計算 → rel_tol=1e-4
    └── 概算値・統計推定量 → rel=0.01 (1%)
```

### 1.2 許容誤差の設計指針

| 許容誤差 | 用途 | 根拠 |
|----------|------|------|
| `rel_tol=1e-9` | 数学的に等しいはずの値（定数シフトの不変性） | float64 の有効桁数 15-16 桁の範囲 |
| `rel_tol=1e-5` | スケーリング比率の検証（`sigma(kX) = |k| * sigma(X)`） | 累積演算の丸め誤差を許容 |
| `rel_tol=1e-4` | モメンタム・リターン計算 | 入力データの丸めと中間演算の誤差 |
| `rel=0.01` (1%) | 概算値の検証（移動平均、統計量） | 統計量の推定誤差を含む |
| `atol=1e-10` | ゼロに近い値の絶対比較 | 正規化後の平均値がゼロか |
| `atol=1e-15` | ゼロ近傍判定（`_EPSILON` 相当） | IEEE 754 マシンイプシロン × 4.5 |

### 1.3 比較手法と推奨場面

| 手法 | 用途 | 例 |
|------|------|-----|
| `pytest.approx(expected, rel=...)` | 単一スカラー値のテストアサーション | `assert sharpe == pytest.approx(1.5, rel=0.01)` |
| `math.isclose(a, b, rel_tol=...)` | 数学的性質の検証（比率、不変条件） | `assert math.isclose(vol_scaled / vol_base, scale, rel_tol=1e-5)` |
| `np.allclose(a, b, atol=...)` | 配列全体の一括比較 | `assert np.allclose(row_means, 0, atol=1e-10)` |
| `np.isclose(a, b, rtol=...)` | 配列要素ごとのブーリアンマスク | `mask = np.isclose(actual, expected, rtol=1e-4)` |
| `np.testing.assert_allclose(a, b, atol=...)` | 配列比較（失敗時にdiff表示） | `np.testing.assert_allclose(values, 0.0, atol=1e-10)` |

```python
# pytest.approx: 単一値の検証（可読性が高い）
assert returns.iloc[1] == pytest.approx(0.00995, rel=0.01)
```

> **参照**: `tests/analyze/integration/test_market_integration.py` line 223

```python
# math.isclose: 数学的比率の検証
expected_ratio = abs(scale_factor)
actual_ratio = vol_scaled / vol_base
assert math.isclose(actual_ratio, expected_ratio, rel_tol=1e-5)
```

> **参照**: `tests/strategy/property/risk/test_calculator.py` line 111

```python
# np.testing.assert_allclose: 配列全体をゼロと比較（失敗時にdiff表示）
valid_values = result["TEST"].dropna()
np.testing.assert_allclose(np.asarray(valid_values), 0.0, atol=1e-10)
```

> **参照**: `tests/factor/property/price/test_momentum_property.py` line 284

---

## 2. Hypothesis の数値ストラテジー設計

### 2.1 金融データ向けストラテジー一覧

| データ種類 | ストラテジー | 根拠 |
|-----------|------------|------|
| 日次リターン | `st.floats(min_value=-0.5, max_value=0.5, allow_nan=False, allow_infinity=False)` | S&P500 の日次最大変動は約 +-12% |
| 保守的な日次リターン | `st.floats(min_value=-0.1, max_value=0.1, allow_nan=False, allow_infinity=False)` | 統計的性質を安定させる狭い範囲 |
| リスクフリーレート | `st.floats(min_value=0.0, max_value=0.1, allow_nan=False)` | 現実的な年率 0-10% |
| 株価 | `st.floats(min_value=10, max_value=1000, allow_nan=False)` | ペニーストック除外 |
| ポートフォリオウェイト | `st.floats(min_value=0.0, max_value=1.0, allow_nan=False)` | 非負制約 |
| リターンのリストサイズ | `min_size=20, max_size=200` | 統計量の安定性に20件以上が必要 |
| 年率化係数 | `st.integers(min_value=1, max_value=365)` | 日次=252, 週次=52, 月次=12 |
| 信頼水準（VaR） | `st.floats(min_value=0.5, max_value=0.99)` | 50%-99% の現実的な範囲 |

### 2.2 基本パターン: リターンのリスト

```python
from hypothesis import given, settings
from hypothesis import strategies as st

@given(
    returns=st.lists(
        st.floats(min_value=-0.5, max_value=0.5, allow_nan=False, allow_infinity=False),
        min_size=10,
        max_size=500,
    ),
    annualization_factor=st.integers(min_value=1, max_value=365),
)
@settings(max_examples=100)
def test_プロパティ_ボラティリティは常に非負(
    self,
    returns: list[float],
    annualization_factor: int,
) -> None:
    returns_series = pd.Series(returns)
    calculator = RiskCalculator(returns_series, annualization_factor=annualization_factor)

    volatility = calculator.volatility()

    assert volatility >= 0
    assert not math.isnan(volatility)
```

> **参照**: `tests/strategy/property/risk/test_calculator.py` lines 23-61

### 2.3 `allow_nan=False, allow_infinity=False` の必須化

Hypothesis のデフォルトでは `st.floats()` が NaN と Infinity を生成します。
金融データのテストでは、これらをストラテジーレベルで除外し、NaN/inf のテストは専用テストケースで行います。

```python
# NG: NaN/inf が混入して意図しないテスト失敗
st.floats(min_value=-0.5, max_value=0.5)  # NaN, inf が生成される可能性

# OK: 明示的に除外
st.floats(min_value=-0.5, max_value=0.5, allow_nan=False, allow_infinity=False)
```

**理由**:
- NaN が 1 つでも含まれると `pd.Series.std()` が NaN を返し、テストの前提が崩壊する
- NaN/inf の処理は本番コードのエッジケースとして専用テストで検証すべき

### 2.4 `assume()` による前提条件フィルタリング

ランダム生成データが前提条件を満たさない場合、`assume()` でスキップします。

```python
from hypothesis import assume

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

    assert math.isclose(calc_original.volatility(), calc_shifted.volatility(), rel_tol=1e-9)
```

> **参照**: `tests/strategy/property/risk/test_calculator.py` lines 122-153

**`assume()` の推奨ケース**:

| 状況 | assume の内容 | 理由 |
|------|--------------|------|
| 全値が同一 | `assume(float(series.std()) > _EPSILON)` | 標準偏差ゼロでは除算不可 |
| 負のリターンなし | `assume(any(r < 0 for r in returns))` | Sortino 比の下方偏差が算出不可 |
| 負のリターンが 1 件 | `assume(negative_count >= 2)` | 1 件では std が NaN |
| 微小な変化 | `assume(abs(end - start) > 0.01)` | モメンタム符号判定が不安定 |
| skip < lookback | `assume(skip_recent < lookback)` | パラメータ制約 |

### 2.5 `@settings(max_examples=N)` の設計指針

| テスト種別 | max_examples | 根拠 |
|-----------|-------------|------|
| 基本的な不変条件（非負性、範囲） | 100 | 十分な範囲をカバー |
| 数学的関係性（スケーリング、不変性） | 50 | 1 テストあたりの計算コストが高い |
| 境界条件 | 50 | 条件が制限的で探索空間が狭い |
| パラメータ制約（正常系） | 100 | パラメータ組み合わせが多い |
| パラメータ制約（異常系） | 50 | 異常値の種類が限定的 |

---

## 3. プロパティベーステストの不変条件パターン

### 3.1 非負性（Non-negativity）

```python
def test_プロパティ_ボラティリティは常に非負(self, returns: list[float]) -> None:
    calculator = RiskCalculator(pd.Series(returns))
    assert calculator.volatility() >= 0
    assert not math.isnan(calculator.volatility())
```

> **参照**: `tests/strategy/property/risk/test_calculator.py` lines 34-61

### 3.2 スケーリング不変条件

`sigma(kX) = |k| * sigma(X)` の関係を検証：

```python
def test_プロパティ_リターンスケールとボラティリティの関係(
    self, base_returns: list[float], scale_factor: float,
) -> None:
    base_series = pd.Series(base_returns)
    scaled_series = base_series * scale_factor

    assume(float(base_series.std()) > _EPSILON)

    vol_base = RiskCalculator(base_series).volatility()
    vol_scaled = RiskCalculator(scaled_series).volatility()

    assume(vol_base > 0)

    expected_ratio = abs(scale_factor)
    actual_ratio = vol_scaled / vol_base
    assert math.isclose(actual_ratio, expected_ratio, rel_tol=1e-5)
```

> **参照**: `tests/strategy/property/risk/test_calculator.py` lines 63-111

### 3.3 シフト不変条件

`sigma(X + c) = sigma(X)` の関係を検証：

```python
def test_プロパティ_定数加算でボラティリティ不変(self, returns: list[float]) -> None:
    original_series = pd.Series(returns)
    assume(float(original_series.std()) > _EPSILON)

    shifted_series = original_series + 0.05
    vol_original = RiskCalculator(original_series).volatility()
    vol_shifted = RiskCalculator(shifted_series).volatility()

    assert math.isclose(vol_original, vol_shifted, rel_tol=1e-9)
```

> **参照**: `tests/strategy/property/risk/test_calculator.py` lines 123-153

### 3.4 範囲制約

値が数学的に定まった範囲内に収まることを検証：

```python
# MDD は -1.0 から 0.0 の範囲
def test_プロパティ_MDDは常に0から負1の範囲(self, returns: list[float]) -> None:
    calculator = RiskCalculator(pd.Series(returns))
    mdd = calculator.max_drawdown()
    assert -1.0 <= mdd <= 0.0
    assert not math.isnan(mdd)

# VaR はリターンの範囲内
def test_プロパティ_VaRはリターン範囲内(self, returns: list[float]) -> None:
    calculator = RiskCalculator(pd.Series(returns))
    var_95 = calculator.var(confidence=0.95, method="historical")
    assert min(returns) <= var_95 <= max(returns)
```

> **参照**: `tests/strategy/property/risk/test_calculator.py` lines 588-609, 753-774

### 3.5 単調性

信頼水準が高いほど VaR が厳しくなる（より負の値になる）:

```python
def test_プロパティ_VaR99はVaR95以下(self, returns: list[float]) -> None:
    calculator = RiskCalculator(pd.Series(returns))
    var_95 = calculator.var(confidence=0.95, method="historical")
    var_99 = calculator.var(confidence=0.99, method="historical")

    # 99% VaR は 95% VaR 以下（許容誤差付き）
    assert var_99 <= var_95 + 1e-10
```

> **参照**: `tests/strategy/property/risk/test_calculator.py` lines 718-741

### 3.6 符号の一貫性

入力データの方向と出力の符号が一致することを検証：

```python
# 全て正のリターン → 正の Sharpe
def test_プロパティ_正のリターンで正のシャープレシオ(self, returns: list[float]) -> None:
    calculator = RiskCalculator(pd.Series(returns), risk_free_rate=0.0)
    sharpe = calculator.sharpe_ratio()
    if not math.isinf(sharpe):
        assert sharpe > 0

# 全て負のリターン → 負の Sharpe
def test_プロパティ_負のリターンで負のシャープレシオ(self, returns: list[float]) -> None:
    calculator = RiskCalculator(pd.Series(returns), risk_free_rate=0.0)
    sharpe = calculator.sharpe_ratio()
    if not math.isinf(sharpe):
        assert sharpe < 0
```

> **参照**: `tests/strategy/property/risk/test_calculator.py` lines 198-256

---

## 4. エッジケーステストパターン

### 4.1 NaN の処理

NaN を含むデータに対する計算関数のテスト。Hypothesis ではなく、確定的なテストケースで検証します。

```python
class TestEdgeCaseNaN:
    """NaN を含むデータのテスト."""

    def test_エッジケース_NaN含む時系列でリターン計算(self) -> None:
        """NaN が含まれる場合、対応する位置のリターンも NaN になる."""
        prices = pd.Series([100.0, 105.0, float("nan"), 110.0, 115.0])
        returns = prices.pct_change()

        assert pd.isna(returns.iloc[2])  # NaN 位置のリターンは NaN
        assert pd.isna(returns.iloc[3])  # NaN 直後のリターンも NaN（分母が NaN）

    def test_エッジケース_全NaN入力でボラティリティ(self) -> None:
        """全て NaN の入力でボラティリティが NaN を返す."""
        nan_series = pd.Series([float("nan")] * 10)
        calculator = RiskCalculator(nan_series)
        vol = calculator.volatility()

        # pd.Series([NaN]*10).std() → NaN → NaN < _EPSILON は False → NaN * sqrt(252) = NaN
        assert math.isnan(vol)

    def test_エッジケース_一部NaN入力で統計量は有効値のみで計算(self) -> None:
        """NaN を含む Series の std() は NaN を除外して計算される."""
        series = pd.Series([0.01, 0.02, float("nan"), -0.01, 0.03])
        std = float(series.std())

        assert not math.isnan(std)
        assert std > 0
```

### 4.2 Infinity の処理

```python
class TestEdgeCaseInfinity:
    """Infinity を含むデータのテスト."""

    def test_エッジケース_ゼロ除算でinfリターン(self) -> None:
        """価格がゼロの場合、リターンが inf になることを検証."""
        prices = pd.Series([100.0, 0.0, 50.0])
        returns = prices.pct_change()

        assert math.isinf(returns.iloc[2])  # 0 → 50 は inf

    def test_エッジケース_Sharpe比のinf出力(self) -> None:
        """標準偏差ゼロで正のリターンの場合、inf を返す."""
        constant_positive = pd.Series([0.01] * 20)
        calculator = RiskCalculator(constant_positive, risk_free_rate=0.0)
        sharpe = calculator.sharpe_ratio()

        assert math.isinf(sharpe) and sharpe > 0

    def test_エッジケース_Sortino比のinf出力(self) -> None:
        """全て正のリターンで下方偏差ゼロの場合、inf を返す."""
        positive_returns = pd.Series([0.01, 0.02, 0.03, 0.01, 0.02] * 4)
        calculator = RiskCalculator(positive_returns, risk_free_rate=0.0)
        sortino = calculator.sortino_ratio()

        assert math.isinf(sortino) and sortino > 0
```

> **参照**: `src/strategy/risk/calculator.py` lines 193-209 -- Sharpe レシオの inf 出力
> **参照**: `src/strategy/risk/calculator.py` lines 250-298 -- Sortino レシオのエッジケース処理

### 4.3 空データ・不十分なデータ

```python
class TestEdgeCaseEmpty:
    """空・不十分なデータのテスト."""

    def test_エッジケース_空のSeriesでNoneまたはデフォルト値(self) -> None:
        """空の Series が渡された場合の挙動を検証."""
        empty = pd.Series([], dtype=float)

        # 実装によって例外 or デフォルト値を返す
        # 明示的に dtype=float を指定すること
        assert len(empty) == 0

    def test_エッジケース_1要素のSeriesでリターンNone(self) -> None:
        """1 要素しかない場合、リターンが計算できないことを検証."""
        single = pd.Series([100.0])
        returns = single.pct_change()

        assert len(returns) == 1
        assert pd.isna(returns.iloc[0])

    def test_エッジケース_最低データ数に満たない場合(self) -> None:
        """最低サンプル数未満のデータで適切にハンドリングされることを検証."""
        # min_samples=5 のとき、4件では処理をスキップまたはエラー
        short_series = pd.Series([0.01, -0.01, 0.02, -0.02])

        # Normalizer の例: min_samples 未満は NaN を返す
        from factor.core.normalizer import Normalizer
        normalizer = Normalizer(min_samples=5)
        result = normalizer.zscore(short_series)

        assert result.isna().all()
```

> **参照**: `src/factor/core/normalizer.py` line 46 -- `min_samples: int = 5`
> **参照**: `src/analyze/returns/returns.py` lines 86-92 -- 最低データ数検証

### 4.4 定数データ（分散ゼロ）

```python
class TestEdgeCaseConstant:
    """全値が同一（分散ゼロ）のテスト."""

    def test_エッジケース_定数リターンでボラティリティゼロ(self) -> None:
        """全て同じリターンではボラティリティがゼロ."""
        constant = pd.Series([0.01] * 50)
        calculator = RiskCalculator(constant)

        assert calculator.volatility() == 0.0

    def test_エッジケース_定数リターンでSharpeはinf_or_nan(self) -> None:
        """分散ゼロで Sharpe は inf（正）/ -inf（負）/ nan（ゼロ）."""
        positive_constant = pd.Series([0.01] * 50)
        calc = RiskCalculator(positive_constant, risk_free_rate=0.0)
        assert math.isinf(calc.sharpe_ratio()) and calc.sharpe_ratio() > 0

        zero_constant = pd.Series([0.0] * 50)
        calc_zero = RiskCalculator(zero_constant, risk_free_rate=0.0)
        assert math.isnan(calc_zero.sharpe_ratio())

    def test_エッジケース_全同一値でZスコアはNaN(self) -> None:
        """全て同じ値の場合、Z-score は NaN を返す."""
        constant = pd.Series([100.0] * 10)
        # scale = 0 → NaN を返す（ゼロ除算防止）
        zscore = (constant - constant.mean()) / constant.std()

        assert zscore.isna().all()  # std = 0 → NaN
```

> **参照**: `src/factor/core/normalizer.py` lines 133-140 -- ゼロスケール検出

### 4.5 Sortino レシオ固有のエッジケース

```python
class TestEdgeCaseSortino:
    """Sortino レシオ固有のエッジケース."""

    def test_エッジケース_負のリターンなしでinf(self) -> None:
        """負のリターンが 0 件の場合、下方偏差がゼロで inf."""
        all_positive = pd.Series([0.01, 0.02, 0.03, 0.01, 0.02] * 4)
        calculator = RiskCalculator(all_positive, risk_free_rate=0.0)
        sortino = calculator.sortino_ratio()

        assert math.isinf(sortino) and sortino > 0

    def test_エッジケース_負のリターン1件でinf(self) -> None:
        """負のリターンが 1 件だけの場合、len(negative)==1 の専用分岐で inf."""
        one_negative = pd.Series(
            [0.01, 0.02, 0.03, 0.01, 0.02, 0.01, 0.03, 0.02, 0.01, 0.03,
             0.02, 0.01, 0.03, 0.01, 0.02, 0.03, 0.01, 0.02, -0.01, 0.03]
        )
        calculator = RiskCalculator(one_negative, risk_free_rate=0.0)
        sortino = calculator.sortino_ratio()

        # 負のリターン1件 → len(negative_returns)==1 専用分岐 → excess > 0 → inf
        assert math.isinf(sortino) and sortino > 0

    def test_エッジケース_全て同じ負のリターンでSortino(self) -> None:
        """全て同じ負のリターンの場合、下方偏差ゼロで -inf."""
        same_negative = pd.Series([-0.01] * 20)
        calculator = RiskCalculator(same_negative, risk_free_rate=0.0)
        sortino = calculator.sortino_ratio()

        # 全て同じ負 → std = 0 → mean < 0 → -inf
        assert math.isinf(sortino) and sortino < 0
```

> **参照**: `src/strategy/risk/calculator.py` lines 250-298 -- Sortino のエッジケース処理

---

## 5. テスト設計チェックリスト

数値計算関数のテストを書く前に確認:

### 5.1 基本チェック

- [ ] 浮動小数点比較に `==` を直接使用していないか → `pytest.approx` / `math.isclose` / `np.allclose`
- [ ] rtol/atol の選択根拠を明確にしているか（セクション 1.2 参照）
- [ ] Hypothesis ストラテジーに `allow_nan=False, allow_infinity=False` を指定しているか
- [ ] `assume()` で無効な入力（std ≈ 0、データ不足）を除外しているか

### 5.2 エッジケース網羅

- [ ] NaN を含む入力のテストがあるか
- [ ] Infinity を生成する条件のテストがあるか
- [ ] 空データ / 1 要素データのテストがあるか
- [ ] 全値同一（分散ゼロ）のテストがあるか
- [ ] 最低サンプル数未満のテストがあるか

### 5.3 プロパティベーステスト

- [ ] 非負性の不変条件をテストしているか
- [ ] スケーリング・シフト不変条件をテストしているか
- [ ] 出力の範囲制約をテストしているか
- [ ] 単調性（例: VaR99 <= VaR95）をテストしているか
- [ ] 符号の一貫性をテストしているか

---

## まとめ: 数値計算テスト設計フロー

```
1. テスト対象の数学的性質を特定
   ├── 非負性、範囲制約、単調性
   ├── スケーリング/シフト不変条件
   └── 符号の一貫性

2. Hypothesis ストラテジーを設計
   ├── データ範囲: 金融データの現実的な範囲に制限（セクション 2.1 参照）
   ├── allow_nan=False, allow_infinity=False
   ├── assume() で前提条件をフィルタリング
   └── max_examples をテスト種別に応じて設定

3. 許容誤差を決定
   ├── ゼロ付近 → atol（1e-10 〜 1e-15）
   ├── スケール依存 → rtol（1e-9 〜 1e-4）
   └── 根拠をコメントに記載

4. エッジケースを網羅
   ├── NaN / Infinity / 空データ
   ├── 全値同一（分散ゼロ）
   ├── 最低サンプル数未満
   └── 関数固有のエッジケース（Sortino の負のリターン 0-1 件）
```
