# CA Strategy Phase 6 パフォーマンス指標 算出方法論レポート

## 1. 概要

CA Strategy Phase 6 のポートフォリオ評価で使用されるパフォーマンス指標の算出方法を文書化する。本レポートでは、各指標の数式・実装箇所・検証結果を明示し、標準的な定義との整合性を判定する。

### 対象ソースファイル

| ファイル | 役割 |
|----------|------|
| `src/strategy/risk/calculator.py` | RiskCalculator: Sharpe, Sortino, Max Drawdown, Beta, Information Ratio 等の算出 |
| `src/dev/ca_strategy/evaluator.py` | StrategyEvaluator: RiskCalculator を呼び出しポートフォリオ指標を集約 |
| `src/dev/ca_strategy/return_calculator.py` | PortfolioReturnCalculator: 加重日次リターンの算出 |
| `notebook/ca_strategy_phase6_analysis.py` | Phase 6 分析ノートブック: 拡張指標（Alpha, Calmar, Up/Down Capture 等）の算出 |

### 共通パラメータ

| パラメータ | 値 | 説明 |
|------------|-----|------|
| `annualization_factor` | 252 | 年間営業日数 |
| `risk_free_rate` | 0.02（2%） | 年率リスクフリーレート |

---

## 2. リターン算出

### 2.1 加重日次リターン

**ソース**: `return_calculator.py` L382-449 (`_compute_weighted_returns()`)

**算出式**:

```
portfolio_return_t = Σ(w_i × r_i,t)
```

- `w_i`: 銘柄 i のウェイト（**一定値**）
- `r_i,t`: 銘柄 i の t 日のリターン（前日比 `pct_change`）

**実装の詳細**:

1. 価格データに対して forward-fill を適用し、`pct_change()` で日次リターンを算出
2. 各営業日について、コーポレートアクション（上場廃止・合併等）の有無を確認
3. コーポレートアクション発生時は該当銘柄のウェイトを 0 に設定し、残余ウェイトを比例配分で再分配
4. ウェイト行列とリターン行列の要素積を行方向に合計し、日次ポートフォリオリターンを算出

**重大な問題点**:

レポートでは「2015年末に構築したポートフォリオを10年間リバランスなしで保持」（Buy-and-Hold）と記述しているが、実装コードではウェイトを**毎日一定値（constant weights）**で適用している。これは日次リバランス（Daily Rebalancing）に相当する。

真の Buy-and-Hold では、ウェイトは価格変動に応じてドリフトする。例えば、銘柄 A が値上がりし銘柄 B が値下がりすれば、A のウェイトは増加し B のウェイトは減少する。一定ウェイトの適用はこのドリフトを無視するため、高リターン銘柄の貢献を過大評価する傾向がある。

```
# 実装（日次リバランス）: w_i は全期間で一定
portfolio_return_t = Σ(w_i × r_i,t)    # w_i = const

# 真の Buy-and-Hold: w_i,t は価格変動で変化
w_i,t = w_i,0 × Π(1 + r_i,s) / Σ_j(w_j,0 × Π(1 + r_j,s))    # s = 1..t-1
portfolio_return_t = Σ(w_i,t × r_i,t)
```

**判定**: **CRITICAL** -- 日次リバランスと Buy-and-Hold の不整合。パフォーマンスの過大評価リスクあり。

---

## 3. 各指標の算出方法

### 3.1 Sharpe Ratio

**ソース**: `calculator.py` L161-218 (`sharpe_ratio()`)

**算出式**:

```
daily_rf = rf_annual / 252
excess_return_t = return_t - daily_rf
Sharpe = (mean(excess_return) / std(excess_return)) × √252
```

**実装コード** (L186-209):

```python
daily_rf = self._risk_free_rate / self._annualization_factor
excess_returns = self._returns - daily_rf
mean_excess = float(excess_returns.mean())
std_excess = float(excess_returns.std())          # ddof=1 (pandas default)
sharpe = float((mean_excess / std_excess) * np.sqrt(self._annualization_factor))
```

**注記**:

- 分母に超過リターンの標準偏差（`std(excess_return)`）を使用。Sharpe (1994) の原論文に準拠。
- `pd.Series.std()` はデフォルトで `ddof=1`（不偏標準偏差）を使用。
- ノートブック（L513）では `_p.std()`（トータルリターンの標準偏差）を分母に使用しており、RiskCalculator とは微小な差が生じる。日次リスクフリーレートが小さいため実質的な影響は軽微。

**判定**: ✅ 正確（標準的な実装）

---

### 3.2 Sortino Ratio

**ソース**: `calculator.py` L220-311 (`sortino_ratio()`)、ノートブック L522-525

**算出式（RiskCalculator）**:

```
daily_rf = rf_annual / 252
excess_return = mean(returns) - daily_rf
downside_std = std(returns[returns < 0])           # ddof=1
Sortino = (excess_return / downside_std) × √252
```

**実装コード** (L246-301):

```python
daily_rf = self._risk_free_rate / self._annualization_factor
excess_return = self._returns.mean() - daily_rf
negative_returns = self._returns[self._returns < 0]
downside_std = float(negative_returns.std())       # ddof=1
sortino = float((excess_return / downside_std) * np.sqrt(self._annualization_factor))
```

**算出式（ノートブック）** (L522-525):

```python
_down = _p[_p < 0]
_down_std = float(_down.std() * np.sqrt(_ann)) if len(_down) > 0 else 1
_sortino = float((_p.mean() * _ann - _rf) / _down_std)
```

ノートブックでは年率化された平均リターンと年率化されたダウンサイド偏差を使用。RiskCalculator とは年率化の適用順序が異なるが、数学的には等価。

**Sortino 原論文との差異**:

Sortino & Price (1994) の原論文では、ダウンサイドリスクを MAR（Minimum Acceptable Return）を下回るリターンの **RMS（二乗平均平方根、Root Mean Square）** で定義する:

```
# Sortino 原論文
DD = √(Σ min(r_t - MAR, 0)² / N)

# 本実装（簡略版）
DD = std(returns[returns < 0])
```

原論文の RMS 方式では、MAR を上回る日のリターンも 0 として分母 N に含める。本実装では負のリターンのみをフィルタリングして標準偏差を算出しており、サンプルサイズが異なる。業界では本実装の簡略版も広く使用されている。

**判定**: ⚠️ 簡略版（業界で一般的だが、Sortino 原論文の RMS 方式ではない）

---

### 3.3 Max Drawdown

**ソース**: `calculator.py` L376-415 (`max_drawdown()`)

**算出式**:

```
cumulative_t = Π(1 + return_s)          # s = 1..t
running_max_t = max(cumulative_s)        # s = 1..t
drawdown_t = (cumulative_t - running_max_t) / running_max_t
MDD = min(drawdown_t)
```

**実装コード** (L404-407):

```python
cumulative = (1 + self._returns).cumprod()
running_max = cumulative.cummax()
drawdown = (cumulative - running_max) / running_max
mdd = float(drawdown.min())
```

**注記**:

- 戻り値は負の値（例: -0.15 = -15%）。
- ピーク・トゥ・トラフ方式の標準的な実装。

**判定**: ✅ 正確（標準的なピーク・トゥ・トラフ方式）

---

### 3.4 Beta

**ソース**: `calculator.py` L542-599 (`beta()`)、ノートブック L508-509

**算出式（RiskCalculator）**:

```
Beta = Cov(r_portfolio, r_benchmark) / Var(r_benchmark)
```

**実装コード** (L576-590):

```python
portfolio_aligned, benchmark_aligned = self._align_with_benchmark(benchmark_returns)
covariance = portfolio_aligned.cov(benchmark_aligned)    # ddof=1
benchmark_variance = benchmark_aligned.var()              # ddof=1
beta = float(covariance / benchmark_variance)
```

**算出式（ノートブック）** (L508-509):

```python
_cov = np.cov(_p, _b)                                    # ddof=1 (default)
_beta = float(_cov[0, 1] / _cov[1, 1]) if _cov[1, 1] > 0 else 1.0
```

**注記**:

- 両実装とも `ddof=1`（不偏推定量）を使用。
- RiskCalculator は `_align_with_benchmark()` (L493-540) で共通日付への整列と `dropna()` を実行。
- ノートブックは事前に `_aligned` DataFrame を構築済み。

**判定**: ✅ 正確

---

### 3.5 Information Ratio

**ソース**: `calculator.py` L669-735 (`information_ratio()`)、ノートブック L504-505

**算出式**:

```
active_return_t = r_portfolio,t - r_benchmark,t
IR = (mean(active_return) / std(active_return)) × √252
```

**実装コード（RiskCalculator）** (L707-726):

```python
active_returns = portfolio_aligned - benchmark_aligned
active_mean = float(active_returns.mean())
active_std = float(active_returns.std())                  # ddof=1
ir = (active_mean / active_std) * np.sqrt(self._annualization_factor)
```

**実装コード（ノートブック）** (L504-505):

```python
_te = float(_active.std() * np.sqrt(_ann))
_ir = float(_active.mean() / _active.std() * np.sqrt(_ann)) if _active.std() > 0 else 0
```

**判定**: ✅ 正確

---

### 3.6 CAPM Alpha (Jensen's Alpha)

**ソース**: ノートブック L510

**算出式**:

```
Alpha = ann_return_portfolio - (rf + Beta × (ann_return_benchmark - rf))
```

**実装コード** (L499-510):

```python
_ann_p = float((1 + _cum_p) ** (1 / _n_yr) - 1)    # CAGR
_ann_b = float((1 + _cum_b) ** (1 / _n_yr) - 1)    # CAGR
_alpha = _ann_p - (_rf + _beta * (_ann_b - _rf))
```

**注記**:

- 年率化リターンは CAGR（幾何平均）で算出。
- 事後的な Jensen's Alpha（ex-post Jensen's Alpha）。

**判定**: ✅ 正確（事後的 Jensen's Alpha）

---

### 3.7 Tracking Error

**ソース**: ノートブック L504

**算出式**:

```
TE = std(active_return) × √252
```

**実装コード** (L504):

```python
_te = float(_active.std() * np.sqrt(_ann))
```

**注記**:

- `pd.Series.std()` はデフォルトで `ddof=1`。
- 日次アクティブリターンの標準偏差を年率化。

**判定**: ✅ 正確

---

### 3.8 Cumulative Return

**ソース**: `evaluator.py` L212

**算出式**:

```
Cumulative Return = Π(1 + r_t) - 1
```

**実装コード** (L212):

```python
cumulative_return = float((1 + portfolio_returns).prod() - 1)
```

**判定**: ✅ 正確

---

### 3.9 Annualized Return (CAGR)

**ソース**: ノートブック L499-500

**算出式**:

```
n_years = len(returns) / 252
CAGR = (1 + Cumulative Return)^(1 / n_years) - 1
```

**実装コード** (L494, L499):

```python
_n_yr = len(_aligned) / _ann
_ann_p = float((1 + _cum_p) ** (1 / _n_yr) - 1)
```

**判定**: ✅ 正確

---

### 3.10 Annualized Volatility

**ソース**: `calculator.py` L117-159 (`volatility()`)

**算出式**:

```
Annualized Volatility = std(daily_returns) × √252
```

**実装コード** (L140-151):

```python
std = float(self._returns.std())          # ddof=1
volatility = std * np.sqrt(self._annualization_factor)
```

**判定**: ✅ 正確

---

### 3.11 Calmar Ratio

**ソース**: ノートブック L528

**算出式**:

```
Calmar Ratio = CAGR / |MDD|
```

**実装コード** (L528):

```python
_calmar = _ann_p / abs(_mdd_p) if _mdd_p != 0 else 0
```

**注記**:

業界標準の Calmar Ratio は直近36ヶ月（trailing 3-year window）の Max Drawdown を使用するが、本実装では全期間（約10年）の MDD を使用している。長期間の MDD は短期間より大きくなる傾向があるため、Calmar Ratio が過小評価される可能性がある。

**判定**: ⚠️ 非標準期間（業界標準は直近36ヶ月のローリングウィンドウ）

---

### 3.12 Up/Down Capture Ratio

**ソース**: ノートブック L530-534

**算出式**:

```
Up Capture   = mean(r_portfolio[r_benchmark > 0]) / mean(r_benchmark[r_benchmark > 0]) × 100
Down Capture = mean(r_portfolio[r_benchmark < 0]) / mean(r_benchmark[r_benchmark < 0]) × 100
```

**実装コード** (L530-534):

```python
_up = _b > 0
_dn = _b < 0
_up_cap = float(_p[_up].mean() / _b[_up].mean() * 100) if _b[_up].mean() != 0 else 0
_dn_cap = float(_p[_dn].mean() / _b[_dn].mean() * 100) if _b[_dn].mean() != 0 else 0
```

**標準的な定義との差異**:

Morningstar 等で採用される標準的な Up/Down Capture Ratio は幾何的（累積的）アプローチを使用する:

```
# 標準的な幾何的アプローチ
Up Capture = ((Π(1 + r_p,t | r_b,t > 0))^(1/n_up) - 1) /
             ((Π(1 + r_b,t | r_b,t > 0))^(1/n_up) - 1) × 100
```

本実装は日次リターンの算術平均比を使用しており、複利効果を反映しない簡略版である。

**判定**: ⚠️ 簡略版（算術的日次平均。標準的な幾何的累積アプローチではない）

---

### 3.13 Win Rate

**ソース**: ノートブック L537

**算出式**:

```
Win Rate = count(active_return > 0) / count(active_return)
```

**実装コード** (L537):

```python
_win = float((_active > 0).mean())
```

**注記**:

- `pd.Series.mean()` は boolean Series に対して True の割合を返す。
- アクティブリターンがベンチマークを上回った日の割合。

**判定**: ✅ 正確

---

## 4. サマリーテーブル

| 指標 | 算出式 | ソースファイル | 行番号 | 判定 | 備考 |
|------|--------|---------------|--------|------|------|
| Sharpe Ratio | `(mean(excess_ret) / std(excess_ret)) × √252` | `calculator.py` | L161-218 | ✅ 正確 | 超過リターンの std を使用（Sharpe 原論文準拠） |
| Sortino Ratio | `(mean_excess / std(negative_ret)) × √252` | `calculator.py` | L220-311 | ⚠️ 簡略版 | 業界で一般的だが Sortino 原論文の RMS 方式ではない |
| Max Drawdown | `min((cumulative - running_max) / running_max)` | `calculator.py` | L376-415 | ✅ 正確 | 標準的なピーク・トゥ・トラフ |
| Beta | `Cov(r_p, r_b) / Var(r_b)` | `calculator.py` | L542-599 | ✅ 正確 | ddof=1、日付整列済み |
| Information Ratio | `(mean(active_ret) / std(active_ret)) × √252` | `calculator.py` | L669-735 | ✅ 正確 | 標準的な実装 |
| CAPM Alpha | `CAGR_p - (rf + Beta × (CAGR_b - rf))` | ノートブック | L510 | ✅ 正確 | 事後的 Jensen's Alpha |
| Tracking Error | `std(active_ret) × √252` | ノートブック | L504 | ✅ 正確 | 標準的な実装 |
| Cumulative Return | `Π(1 + r_t) - 1` | `evaluator.py` | L212 | ✅ 正確 | 標準的な実装 |
| Annualized Return (CAGR) | `(1 + cum_ret)^(1/n_years) - 1` | ノートブック | L499-500 | ✅ 正確 | 幾何平均年率化 |
| Annualized Volatility | `std(daily_ret) × √252` | `calculator.py` | L117-159 | ✅ 正確 | ddof=1 |
| Calmar Ratio | `CAGR / |MDD|` | ノートブック | L528 | ⚠️ 非標準 | 全期間 MDD を使用（標準は直近36ヶ月） |
| Up/Down Capture Ratio | `mean(r_p[condition]) / mean(r_b[condition]) × 100` | ノートブック | L530-534 | ⚠️ 簡略版 | 算術平均（標準は幾何的累積アプローチ） |
| Win Rate | `count(active_ret > 0) / count(active_ret)` | ノートブック | L537 | ✅ 正確 | 標準的な実装 |

---

## 5. 重大な問題点

### 5.1 [CRITICAL] 日次リバランス vs Buy-and-Hold の不整合

**影響度**: 重大

**概要**: レポートの前提（Buy-and-Hold）と実装（日次リバランス）が不整合。

**詳細**:

`return_calculator.py` の `_compute_weighted_returns()` (L382-449) は、コーポレートアクションがない限り全期間で一定のウェイトを適用する。これは各営業日の期初にウェイトを初期値にリセットする日次リバランスと等価である。

一方、パフォーマンス分析レポートでは「2015年末に構築したポートフォリオを10年間リバランスなしで保持」と記述しており、Buy-and-Hold 戦略を前提としている。

**パフォーマンスへの影響**:

- 日次リバランスは「ウィナーを売ってルーザーを買う」逆張り効果を内包する
- モメンタムが強い期間では Buy-and-Hold がアウトパフォームする傾向
- ミーンリバージョンが強い期間では日次リバランスがアウトパフォームする傾向
- 一般に、10年間のような長期間では両者の差が大きくなる

### 5.2 [MINOR] Sortino Ratio の簡略化

**影響度**: 軽微

**概要**: Sortino & Price (1994) の原論文で定義された RMS ベースのダウンサイドデビエーションではなく、負のリターンの標準偏差を使用。

**差異の本質**: 原論文の RMS では全日数（MAR を上回る日も 0 として含む）を分母に使用するが、本実装では負のリターンの日数のみを分母に使用。これにより、本実装のダウンサイドデビエーションは原論文の値より大きくなり、Sortino Ratio は過小評価される傾向がある。

### 5.3 [MINOR] Calmar Ratio の非標準期間

**影響度**: 軽微

**概要**: 業界標準の直近36ヶ月ローリングウィンドウではなく、全期間（約10年）の MDD を使用。

**差異の本質**: 長期間ほど大きなドローダウンが観測される確率が高く、全期間 MDD は36ヶ月 MDD より大きくなる傾向がある。結果として Calmar Ratio が過小評価される。

### 5.4 [MINOR] Up/Down Capture Ratio の算術的アプローチ

**影響度**: 軽微

**概要**: Morningstar 等で採用される幾何的（累積的）アプローチではなく、日次リターンの算術平均比を使用。

**差異の本質**: 算術平均は複利効果を無視するため、特に上昇・下落が大きい期間で幾何的アプローチとの乖離が大きくなる。

---

## 6. 推奨事項

### 6.1 真の Buy-and-Hold 実装（優先度: 高）

ウェイトが価格変動に応じてドリフトする Buy-and-Hold リターン算出を実装する。

```python
def _compute_buyandhold_returns(
    self,
    prices_df: pd.DataFrame,
    initial_weights: dict[str, float],
) -> pd.Series:
    """Buy-and-Hold: ウェイトが価格変動でドリフトする."""
    # 初期投資額を配分
    initial_values = {t: w for t, w in initial_weights.items()}
    # 各銘柄の価値を価格比で追跡
    value_df = prices_df / prices_df.iloc[0] * pd.Series(initial_values)
    # ポートフォリオ価値 = 各銘柄価値の合計
    portfolio_value = value_df.sum(axis=1)
    # 日次リターン
    return portfolio_value.pct_change().dropna()
```

既存の日次リバランス版と並行して結果を比較し、レポートの前提と整合する方を採用すること。

### 6.2 Sortino Ratio の RMS ベース実装（優先度: 低）

オプションとして RMS ベースの Sortino 計算を追加する。

```python
def sortino_ratio_rms(returns: pd.Series, mar: float = 0.0) -> float:
    """Sortino 原論文の RMS ベース."""
    diff = returns - mar
    downside = np.minimum(diff, 0)
    dd = np.sqrt((downside ** 2).mean())  # RMS: 全日数で割る
    excess = returns.mean() - mar
    return (excess / dd) * np.sqrt(252) if dd > 0 else float('inf')
```

### 6.3 Calmar Ratio の trailing 36ヶ月オプション（優先度: 低）

直近36ヶ月ウィンドウの MDD を使用する Calmar Ratio の算出オプションを追加する。

```python
def calmar_ratio_trailing(returns: pd.Series, window: int = 756) -> float:
    """直近 window 日（デフォルト: 756 = 36ヶ月 × 21日）."""
    trailing = returns.iloc[-window:]
    cum = (1 + trailing).cumprod()
    mdd = float((cum / cum.cummax() - 1).min())
    cagr = float((1 + (1 + trailing).prod() - 1) ** (252 / window) - 1)
    return cagr / abs(mdd) if mdd != 0 else 0.0
```

### 6.4 Up/Down Capture Ratio の幾何的アプローチ（優先度: 低）

幾何的（累積的）な Capture Ratio 算出オプションを追加する。

```python
def capture_ratio_geometric(
    portfolio: pd.Series, benchmark: pd.Series, up: bool = True
) -> float:
    """幾何的 Up/Down Capture Ratio."""
    mask = benchmark > 0 if up else benchmark < 0
    p_cum = float((1 + portfolio[mask]).prod())
    b_cum = float((1 + benchmark[mask]).prod())
    n = mask.sum()
    if n == 0 or b_cum == 0:
        return 0.0
    return float((p_cum ** (1 / n) - 1) / (b_cum ** (1 / n) - 1) * 100)
```

---

## 7. ノートブックと RiskCalculator の実装差異

Phase 6 分析ノートブックと `RiskCalculator` の間で以下の軽微な差異が確認された。

| 指標 | RiskCalculator | ノートブック | 影響 |
|------|----------------|-------------|------|
| Sharpe Ratio 分母 | `std(excess_returns)` (L190) | `std(total_returns)` (L513) | 軽微（日次 rf が小さいため差は微小） |
| Sortino 年率化順序 | 日次ベースで比率算出後に `×√252` (L300-301) | 年率化後の値で比率算出 (L525) | なし（数学的に等価） |
| Beta 実装 | `pd.Series.cov/var` (L580-581) | `np.cov` 行列 (L508-509) | なし（同一の ddof=1） |

---

*本レポートは 2026-02-26 時点のソースコードに基づく。*
