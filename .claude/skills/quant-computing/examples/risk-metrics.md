# リスク指標パターン集

Volatility / Sharpe / Sortino / MDD / VaR / Beta / Treynor / Information Ratio の
数式・コード例と、リスクフリーレートの FRED シリーズ使い分けを体系化したパターン集です。
既存コードベースの実装例と行番号注釈を含みます。

---

## リスクフリーレートの FRED シリーズ使い分け

### DFF vs DGS3MO

| シリーズ | 名称 | 頻度 | 推奨用途 |
|----------|------|------|----------|
| **DFF** | Federal Funds Effective Rate | 日次 | 日次 Sharpe / Sortino 計算（`daily_rf = DFF / 252`） |
| **DGS3MO** | 3-Month Treasury Constant Maturity Rate | 日次 | 年率ベースの比較（Treynor、年率超過リターン） |

### 選択フローチャート

```
リスクフリーレートが必要か？
├── 日次リターンとの比較（Sharpe / Sortino）
│   └── DFF を使用（日次実効 FF レート）
│       └── daily_rf = DFF_rate / 100 / 252
├── 年率ベースの比較（Treynor / 年率超過リターン）
│   └── DGS3MO を使用（3ヶ月 T-Bill）
│       └── annual_rf = DGS3MO_rate / 100
└── バックテスト（期間が長い場合）
    └── DFF を使用し、各日の実際のレートを適用
```

### 日次リスクフリーレートへの変換

```python
# DFF（年率 %）→ 日次リスクフリーレート
daily_rf = self._risk_free_rate / self._annualization_factor
# 例: annual_rf = 0.05 (5%), annualization_factor = 252
# → daily_rf = 0.05 / 252 ≈ 0.000198
```

> **参照**: `src/strategy/risk/calculator.py` line 186 -- `daily_rf = self._risk_free_rate / self._annualization_factor`

---

## ゼロ除算防止パターン（`_EPSILON`）

全リスク指標で共通のゼロ除算防止パターン。詳細は `numerical-precision.md` を参照。

```python
# Threshold for considering standard deviation as effectively zero
# This handles floating-point precision issues
_EPSILON = 1e-15
```

> **参照**: `src/strategy/risk/calculator.py` line 20 -- `_EPSILON = 1e-15`

### 分母がゼロ近傍の場合の戻り値規約

| 分母の状態 | 分子 > EPSILON | 分子 < -EPSILON | |分子| < EPSILON |
|-----------|---------------|----------------|-----------------|
| < EPSILON | `float("inf")` | `float("-inf")` | `float("nan")` |

この規約は Sharpe / Sortino / Treynor / Information Ratio の全てで一貫して適用される。

---

## 1. Volatility（年率化ボラティリティ）

### 数式

```
volatility = std(daily_returns) * sqrt(annualization_factor)
```

- `std()`: 標本標準偏差（pandas のデフォルト: ddof=1）
- `annualization_factor`: 252（日次）、52（週次）、12（月次）

### 実装パターン

```python
def volatility(self) -> float:
    std = float(self._returns.std())

    # Handle floating-point precision: treat very small std as zero
    if std < _EPSILON:
        return 0.0

    volatility = std * np.sqrt(self._annualization_factor)
    return float(volatility)
```

> **参照**: `src/strategy/risk/calculator.py` line 151 -- `volatility = std * np.sqrt(self._annualization_factor)`

### プロパティ

| 性質 | 内容 |
|------|------|
| 非負性 | `volatility >= 0` は常に成立 |
| スケーリング | `sigma(kX) = |k| * sigma(X)` |
| シフト不変 | `sigma(X + c) = sigma(X)` |
| 定数入力 | 全リターンが同一の場合、`volatility = 0.0` |

---

## 2. Sharpe Ratio（シャープレシオ）

### 数式

```
daily_rf = risk_free_rate / annualization_factor
excess_returns = daily_returns - daily_rf
sharpe = (mean(excess_returns) / std(excess_returns)) * sqrt(annualization_factor)
```

### 実装パターン

```python
def sharpe_ratio(self) -> float:
    daily_rf = self._risk_free_rate / self._annualization_factor
    excess_returns = self._returns - daily_rf

    mean_excess = float(excess_returns.mean())
    std_excess = float(excess_returns.std())

    # Handle floating-point precision: treat very small std as zero
    if std_excess < _EPSILON:
        if mean_excess > _EPSILON:
            return float("inf")
        elif mean_excess < -_EPSILON:
            return float("-inf")
        else:
            return float("nan")

    return float((mean_excess / std_excess) * np.sqrt(self._annualization_factor))
```

> **参照**: `src/strategy/risk/calculator.py` lines 186-209 -- Sharpe 比の完全な実装

### 解釈基準

| Sharpe | 解釈 |
|--------|------|
| < 0 | リスクフリーレートを下回るリターン |
| 0 - 1.0 | 標準的 |
| 1.0 - 2.0 | 良好 |
| > 2.0 | 優秀（持続性を要検証） |

---

## 3. Sortino Ratio（ソルティノレシオ）

### 数式

```
daily_rf = risk_free_rate / annualization_factor
excess_return = mean(daily_returns) - daily_rf
downside_returns = daily_returns[daily_returns < 0]
downside_std = std(downside_returns)
sortino = (excess_return / downside_std) * sqrt(annualization_factor)
```

### Sharpe との違い

| 項目 | Sharpe | Sortino |
|------|--------|---------|
| 分母 | 全リターンの標準偏差 | 負のリターンのみの標準偏差（下方偏差） |
| 解釈 | 全体リスクに対するリターン | 下方リスクに対するリターン |
| 適用場面 | 一般的なリスク調整リターン | 上方ボラティリティを「悪い」と見なしたくない場合 |

### 実装パターン

```python
def sortino_ratio(self) -> float:
    daily_rf = self._risk_free_rate / self._annualization_factor
    excess_return = self._returns.mean() - daily_rf

    # Calculate downside deviation
    negative_returns = self._returns[self._returns < 0]

    if len(negative_returns) == 0:
        # No negative returns means zero downside deviation
        if excess_return > _EPSILON:
            return float("inf")
        elif excess_return < -_EPSILON:
            return float("-inf")
        else:
            return float("nan")

    # Single negative return has no standard deviation
    if len(negative_returns) == 1:
        if excess_return > _EPSILON:
            return float("inf")
        elif excess_return < -_EPSILON:
            return float("-inf")
        else:
            return float("nan")

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

    return float(
        (excess_return / downside_std) * np.sqrt(self._annualization_factor)
    )
```

> **参照**: `src/strategy/risk/calculator.py` lines 250-298 -- Sortino 比のエッジケース処理（負リターン 0件/1件/NaN）

### エッジケース一覧

| 条件 | 負リターン数 | downside_std | 結果 |
|------|-------------|-------------|------|
| 全て正のリターン | 0 | - | inf（excess > 0）|
| 負リターン 1 件のみ | 1 | NaN（std 不可） | inf / -inf / nan |
| 全て同じ負のリターン | n >= 2 | 0（< EPSILON）| -inf |
| 通常のデータ | n >= 2 | > EPSILON | 有限値 |

---

## 4. Maximum Drawdown（最大ドローダウン）

### 数式

```
cumulative = (1 + daily_returns).cumprod()
running_max = cumulative.cummax()
drawdown = (cumulative - running_max) / running_max
MDD = min(drawdown)
```

### 実装パターン

```python
def max_drawdown(self) -> float:
    cumulative = (1 + self._returns).cumprod()
    running_max = cumulative.cummax()
    drawdown = (cumulative - running_max) / running_max
    mdd = float(drawdown.min())
    return mdd
```

> **参照**: `src/strategy/risk/calculator.py` lines 404-407 -- MDD の4行実装

### プロパティ

| 性質 | 内容 |
|------|------|
| 範囲 | `-1.0 <= MDD <= 0.0` は常に成立 |
| 全て正のリターン | `MDD = 0.0`（ドローダウンなし）にはならない（初日以外は running_max が追随） |
| 解釈 | -0.20 = ピークから 20% の下落 |

### 解釈基準

| MDD | 解釈 |
|-----|------|
| > -0.10 | 低リスク |
| -0.10 〜 -0.20 | 中程度 |
| -0.20 〜 -0.40 | 高リスク |
| < -0.40 | 極めて高リスク |

---

## 5. Value at Risk（VaR）

### 数式

**Historical VaR**:
```
VaR = percentile(daily_returns, (1 - confidence) * 100)
```

**Parametric VaR**（正規分布仮定）:
```
z_score = norm.ppf(1 - confidence)
VaR = mean(daily_returns) + z_score * std(daily_returns)
```

### 実装パターン

```python
def var(
    self,
    confidence: float = 0.95,
    method: Literal["historical", "parametric"] = "historical",
) -> float:
    if method == "historical":
        var = float(np.percentile(self._returns, (1 - confidence) * 100))
    else:
        z_score = stats.norm.ppf(1 - confidence)
        var = float(self._returns.mean() + z_score * self._returns.std())

    return var
```

> **参照**: `src/strategy/risk/calculator.py` lines 478-482 -- VaR の 2 方式（Historical / Parametric）

### Historical vs Parametric の選択基準

| 基準 | Historical | Parametric |
|------|-----------|------------|
| 分布仮定 | 不要（ノンパラメトリック） | 正規分布を仮定 |
| 裾リスク | ファットテールを自然に捕捉 | 過小評価の傾向（正規分布は thin tail） |
| データ量 | 多い方が精度向上（250日以上推奨） | 少ないデータでも計算可能 |
| 計算コスト | O(n log n)（ソート） | O(n)（平均・標準偏差のみ） |
| 極端なイベント | 観測範囲内の損失のみ | 観測範囲外の損失も推定可能 |
| **推奨場面** | **通常のリスク管理（デフォルト）** | **データ不足時、理論的な上限推定** |

### 選択フローチャート

```
VaR の計算方法は？
├── データが 250 日以上あるか？
│   ├── Yes → Historical（デフォルト、ファットテール対応）
│   └── No → Parametric（少データでも安定）
├── 正規分布から大きく乖離するか？（尖度 > 3）
│   ├── Yes → Historical（正規仮定が不適切）
│   └── No → どちらでも可
└── テールリスクを重視するか？
    ├── Yes → Historical + CVaR の併用
    └── No → Parametric で十分
```

### プロパティ

| 性質 | 内容 |
|------|------|
| 単調性 | `VaR(99%) <= VaR(95%)`（高信頼水準ほど損失が大きい） |
| 範囲（Historical） | `min(returns) <= VaR <= max(returns)` |
| 符号 | 通常は負の値（損失を表す） |

---

## 6. Beta（ベータ）

### 数式

```
beta = cov(portfolio_returns, benchmark_returns) / var(benchmark_returns)
```

### 実装パターン

```python
def beta(self, benchmark_returns: pd.Series) -> float:
    portfolio_aligned, benchmark_aligned = self._align_with_benchmark(
        benchmark_returns
    )

    covariance = portfolio_aligned.cov(benchmark_aligned)
    benchmark_variance = benchmark_aligned.var()

    if benchmark_variance < _EPSILON:
        return float("nan")

    return float(covariance / benchmark_variance)
```

> **参照**: `src/strategy/risk/calculator.py` lines 576-599 -- Beta 計算（日付アライメント + ゼロ分散防御）

### 日付アライメント

ポートフォリオとベンチマークの日付が異なる場合、共通する日付のみで計算する:

```python
def _align_with_benchmark(
    self,
    benchmark_returns: pd.Series,
) -> tuple[pd.Series, pd.Series]:
    aligned = pd.DataFrame(
        {
            "portfolio": self._returns,
            "benchmark": benchmark_returns,
        }
    ).dropna()

    if len(aligned) == 0:
        raise ValueError(
            "No common or overlapping dates between portfolio and benchmark returns"
        )

    return pd.Series(aligned["portfolio"]), pd.Series(aligned["benchmark"])
```

> **参照**: `src/strategy/risk/calculator.py` lines 493-540 -- `_align_with_benchmark()` による日付アライメント

### 解釈基準

| Beta | 解釈 |
|------|------|
| < 0 | 市場と逆方向に動く（ヘッジ資産） |
| 0 | 市場と無相関 |
| 0 - 1.0 | 市場より低ボラティリティ（ディフェンシブ） |
| 1.0 | 市場と同じボラティリティ |
| > 1.0 | 市場より高ボラティリティ（アグレッシブ） |

---

## 7. Treynor Ratio（トレイナーレシオ）

### 数式

```
annualized_return = mean(daily_returns) * annualization_factor
treynor = (annualized_return - risk_free_rate) / beta
```

### Sharpe との違い

| 項目 | Sharpe | Treynor |
|------|--------|---------|
| 分母 | トータルリスク（標準偏差） | システマティックリスク（ベータ） |
| 適用場面 | 単一ポートフォリオの評価 | 分散投資されたポートフォリオの比較 |
| ベンチマーク | 不要 | 必要 |

### 実装パターン

```python
def treynor_ratio(self, benchmark_returns: pd.Series) -> float:
    beta = self.beta(benchmark_returns)

    if math.isnan(beta):
        return float("nan")

    if abs(beta) < _EPSILON:
        annualized_return = float(self._returns.mean()) * self._annualization_factor
        excess_return = annualized_return - self._risk_free_rate

        if excess_return > _EPSILON:
            return float("inf")
        elif excess_return < -_EPSILON:
            return float("-inf")
        else:
            return float("nan")

    annualized_return = float(self._returns.mean()) * self._annualization_factor
    treynor = (annualized_return - self._risk_free_rate) / beta
    return float(treynor)
```

> **参照**: `src/strategy/risk/calculator.py` lines 601-667 -- Treynor 比（Beta NaN / Beta ゼロのエッジケース処理）

### エッジケース

| 条件 | Beta | 結果 |
|------|------|------|
| ベンチマーク分散ゼロ | NaN | NaN |
| Beta ≈ 0 + 正の超過リターン | < EPSILON | inf |
| Beta ≈ 0 + 負の超過リターン | < EPSILON | -inf |

---

## 8. Information Ratio（インフォメーションレシオ）

### 数式

```
active_returns = portfolio_returns - benchmark_returns
tracking_error = std(active_returns)
IR = (mean(active_returns) / tracking_error) * sqrt(annualization_factor)
```

### 実装パターン

```python
def information_ratio(self, benchmark_returns: pd.Series) -> float:
    portfolio_aligned, benchmark_aligned = self._align_with_benchmark(
        benchmark_returns
    )

    active_returns = portfolio_aligned - benchmark_aligned
    active_mean = float(active_returns.mean())
    active_std = float(active_returns.std())

    if active_std < _EPSILON:
        if active_mean > _EPSILON:
            return float("inf")
        elif active_mean < -_EPSILON:
            return float("-inf")
        else:
            return float("nan")

    ir = (active_mean / active_std) * np.sqrt(self._annualization_factor)
    return float(ir)
```

> **参照**: `src/strategy/risk/calculator.py` lines 669-735 -- Information Ratio（トラッキングエラーゼロのエッジケース処理）

### Sharpe との関係

| 項目 | Sharpe | Information Ratio |
|------|--------|-------------------|
| 基準 | リスクフリーレート | ベンチマークリターン |
| 分母 | ポートフォリオのボラティリティ | トラッキングエラー |
| 用途 | 絶対リターンの評価 | アクティブ運用の評価 |

### 解釈基準

| IR | 解釈 |
|----|------|
| < 0 | ベンチマークをアンダーパフォーム |
| 0 - 0.5 | 平凡なアクティブ運用 |
| 0.5 - 1.0 | 良好なアクティブ運用 |
| > 1.0 | 優秀なアクティブ運用 |

---

## リスク指標の分類と選択

### 用途別マトリクス

| 指標 | 絶対リスク | 相対リスク | ベンチマーク必要 | リスクフリーレート必要 |
|------|-----------|-----------|----------------|---------------------|
| Volatility | Yes | - | No | No |
| Sharpe | - | Yes | No | Yes (DFF) |
| Sortino | - | Yes | No | Yes (DFF) |
| MDD | Yes | - | No | No |
| VaR | Yes | - | No | No |
| Beta | - | Yes | Yes | No |
| Treynor | - | Yes | Yes | Yes (DGS3MO) |
| IR | - | Yes | Yes | No |

### 選択フローチャート

```
リスク評価の目的は？
├── 絶対リスクの把握
│   ├── ボラティリティ → Volatility
│   ├── 最悪ケースの損失 → MDD
│   └── 確率的な損失見積 → VaR
├── リスク調整リターンの評価
│   ├── ベンチマークなし
│   │   ├── 上下のリスクを同等に扱う → Sharpe
│   │   └── 下方リスクのみ重視 → Sortino
│   └── ベンチマークあり
│       ├── システマティックリスクに対する評価 → Treynor
│       └── アクティブ運用の評価 → IR
└── 市場感応度の把握 → Beta
```

---

## RiskCalculator の初期化

### コンストラクタ

```python
calc = RiskCalculator(
    returns=daily_returns,       # pd.Series of daily returns
    risk_free_rate=0.05,         # Annual risk-free rate (5%)
    annualization_factor=252,    # 252 for daily, 52 for weekly, 12 for monthly
)
```

> **参照**: `src/strategy/risk/calculator.py` line 67 -- `risk_free_rate: float = 0.0`

### 入力検証

| 条件 | 例外 |
|------|------|
| `len(returns) == 0` | `ValueError("returns must not be empty")` |
| `annualization_factor <= 0` | `ValueError("annualization_factor must be positive, got ...")` |

---

## まとめ: リスク指標チェックリスト

実装時に以下を確認:

- [ ] `_EPSILON = 1e-15` によるゼロ除算防止を全指標で適用しているか
- [ ] 分母ゼロ時の戻り値（inf / -inf / nan）が規約に従っているか
- [ ] リスクフリーレートの FRED シリーズを適切に選択しているか（日次: DFF、年率: DGS3MO）
- [ ] `daily_rf = annual_rf / annualization_factor` で日次変換しているか
- [ ] ベンチマーク必要な指標（Beta / Treynor / IR）で日付アライメントを行っているか
- [ ] VaR の method に応じて Historical / Parametric を正しく選択しているか
- [ ] Sortino 比で負リターン 0件 / 1件のエッジケースを処理しているか
- [ ] NaN と EPSILON の複合チェック（`math.isnan(x) or x < _EPSILON`）を行っているか
