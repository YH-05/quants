# リターン計算パターン集

simple vs log リターンの使い分け、年率化の複利必須ルール、CAGR、MTD/YTD、
NaN 伝播ルール、前方参照バイアス防止を体系化したパターン集です。
既存コードベースの実装例と行番号注釈を含みます。

---

## 5つのルール

| # | ルール | 要点 |
|---|--------|------|
| 1 | 単純リターン使用場面 | 個別銘柄の期間リターン、ポートフォリオの加重平均リターン |
| 2 | 累積リターンは複利 | `(1 + r1) * (1 + r2) * ... - 1`、単純加算は禁止 |
| 3 | 年率化は複利必須 | `(1 + cumulative) ** (252/n) - 1`、`return * 252/n` は BAD |
| 4 | 対数リターン使用場面 | 時系列の加法性が必要な場合、連続複利モデル |
| 5 | 前方参照バイアス防止 | `as_of_date` 以降のデータ使用禁止、Point-in-Time 制約 |

---

## ルール 1: 単純リターン（Simple Return）の使用場面

### 1.1 定義

```python
# simple return = (P_end / P_start) - 1
simple_return = (price_end / price_start) - 1
```

### 1.2 使用場面

| 場面 | 理由 |
|------|------|
| 個別銘柄の期間リターン | 直感的で解釈しやすい |
| ポートフォリオの加重平均 | `sum(w_i * r_i)` で正確に算出可能 |
| 短期（日次〜週次）分析 | log との差が微小（< 0.01%） |
| MTD / YTD リターン | 投資家向けレポートの標準形式 |

### 1.3 実装例: 個別銘柄の期間リターン

```python
def calculate_return(prices: pd.Series, period: int | str) -> float | None:
    # ...validation...

    # Calculate return: (current - past) / past
    current_price = clean_prices.iloc[-1]
    past_price = clean_prices.iloc[-(period + 1)]

    if past_price == 0:
        logger.warning("Past price is zero, cannot calculate return")
        return None

    result = (current_price - past_price) / past_price
    return float(result)
```

> **参照**: `src/analyze/returns/returns.py` line 102 -- 単純リターン計算 `(current_price - past_price) / past_price`

### 1.4 実装例: `pct_change()` によるベクトル演算

```python
# groupby + pct_change でシンボル別の期間リターンをベクトル計算
df_regular[f"Return_{period_name}"] = df_regular.groupby(
    level=symbol_column
)[price_column].pct_change(period_month)
```

> **参照**: `src/factor/core/return_calculator.py` lines 166-168 -- `pct_change()` による期間リターン計算

---

## ルール 2: 累積リターンは複利（Compound）

### 2.1 正しい累積リターン計算

```python
# OK: 複利で累積
cumulative_return = (1 + daily_returns).prod() - 1

# OK: 等価な書き方
cumulative_return = np.prod(1 + daily_returns) - 1
```

### 2.2 禁止パターン: 単純加算

```python
# NG: 単純加算は数学的に不正確
cumulative_return = daily_returns.sum()  # 禁止
```

**なぜ禁止か**: 日次リターン +10% と -10% を単純加算すると 0% だが、
実際は `1.10 * 0.90 - 1 = -1%` であり、乖離が複利期間に比例して拡大する。

### 2.3 Buy-and-Hold ポートフォリオでのウェイトドリフト

複利の影響でウェイトが日々変動する。正確なリターン計算にはドリフトの追跡が必要：

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

> **参照**: `src/dev/ca_strategy/return_calculator.py` lines 551-563 -- ドリフト後のウェイト正規化
> **正規化パターンの詳細**: `numerical-precision.md` セクション 3「ウェイト正規化の閾値」を参照

---

## ルール 3: 年率化は複利必須（単利禁止）

### 3.1 正しい年率化公式（複利）

```python
# 複利年率化（正しい）
annualized = (1 + cumulative_return) ** (252 / n_trading_days) - 1

# 月次リターンから年率化（正しい）
annualized = (1 + monthly_return) ** (12 / period_months) - 1
```

### 3.2 複利年率化の実装例

```python
def annualize_return(
    self,
    returns: pd.DataFrame | pd.Series,
    period_months: int,
    *,
    method: Literal["simple", "compound"] = "simple",
) -> pd.DataFrame | pd.Series:
    annualization_factor = 12 / period_months

    if method == "simple":
        return returns * annualization_factor
    else:  # compound
        return (1 + returns) ** annualization_factor - 1
```

> **参照**: `src/factor/core/return_calculator.py` lines 284-287 -- 2つの年率化方式（simple / compound）

### 3.3 BAD パターン（既存コードの既知問題 — 修正予定）

> **WARNING**: 以下は **BAD パターン** です。新規コードで絶対に使用しないでください。

```python
# WARNING: BAD PATTERN — DO NOT COPY
# BAD: 単利年率化（数学的に不正確）
annualization_factor = 12 / period_month
df_regular[f"Return_{period_name}_annualized"] = (
    df_regular[f"Return_{period_name}"] * annualization_factor  # 単純乗算 = 単利
)
df_regular[f"Forward_Return_{period_name}_annualized"] = (
    df_regular[f"Forward_Return_{period_name}"] * annualization_factor  # 単純乗算 = 単利
)
```

> **参照**: `src/factor/core/return_calculator.py` lines 177-183 -- BAD パターン（simple 年率化）
>
> **警告**: この実装は `return * (12 / period_month)` という単利年率化を使用しています。
> 正しくは `(1 + return) ** (12 / period_month) - 1` の複利年率化を使用すべきです。
> **修正は別 Issue で対応予定です。**

### 3.4 単利 vs 複利の乖離

| 月次リターン | 単利年率化（BAD） | 複利年率化（正しい） | 乖離 |
|-------------|-------------------|---------------------|------|
| 1% | 12.0% | 12.68% | +0.68pp |
| 3% | 36.0% | 42.58% | +6.58pp |
| 5% | 60.0% | 79.59% | +19.59pp |
| -5% | -60.0% | -46.01% | +13.99pp |

リターンが大きいほど、また期間が長いほど乖離が拡大する。
特に負のリターンでは単利が過大評価（より悪く見せる）するため注意。

---

## ルール 4: 対数リターン（Log Return）の使用場面

### 4.1 定義

```python
# log return = ln(P_end / P_start)
log_return = np.log(price_end / price_start)
```

### 4.2 使用場面

| 場面 | 理由 |
|------|------|
| 時系列の加法性が必要 | `log_return(t0→t2) = log_return(t0→t1) + log_return(t1→t2)` |
| 連続複利モデル | ブラック・ショールズ等の理論モデル |
| 統計的性質が望ましい | 正規分布に近い分布特性（対数正規仮定） |
| クロスセクション集計しない | log リターンは銘柄間の加重平均に不適 |

### 4.3 simple vs log の変換

```python
# simple → log
log_return = np.log(1 + simple_return)

# log → simple
simple_return = np.exp(log_return) - 1
```

### 4.4 注意: log リターンはポートフォリオの加重平均に使えない

```python
# NG: log リターンの加重平均はポートフォリオリターンにならない
portfolio_return = sum(w_i * log_r_i)  # 数学的に不正確

# OK: simple リターンの加重平均を使う
portfolio_return = sum(w_i * simple_r_i)
```

### 4.5 選択フローチャート

```
リターン計算の目的は？
├── ポートフォリオの加重平均リターン → simple
├── 個別銘柄の期間リターン → simple
├── 時系列の累積リターン（加法性が必要） → log
├── 統計モデル（ブラック・ショールズ等） → log
└── MTD / YTD レポート → simple
```

---

## ルール 5: 前方参照バイアス（Look-Ahead Bias）防止

### 5.1 基本原則

リターン計算では以下の2つの前方参照を防止する:

| バイアス | 原因 | 防止策 |
|----------|------|--------|
| シグナル前方参照 | 当日 close で当日リターンを取る | `signals.shift(1)` |
| データ前方参照 | 未公表の決算データを使用 | `as_of_date <= rebalance_date` |

```python
# 決算データは公表日以降のみ使用可能
scores = scores_df[scores_df["as_of_date"] <= rebalance_date]
```

### 5.2 フォワードリターンの使用制限

フォワードリターンはバックテストの**評価指標としてのみ**使用可能。シグナルへの使用は禁止。

```python
# Forward returns: バックテスト評価用（シグナルに使用禁止）
df_regular[f"Forward_Return_{period_name}"] = df_regular.groupby(
    level=symbol_column
)[f"Return_{period_name}"].shift(-period_month)
```

> **参照**: `src/factor/core/return_calculator.py` lines 171-173 -- フォワードリターン計算

### 5.3 PoiT 制約の詳細パターン

Point-in-Time フィルタリング、コンプライアンス検証、LLM プロンプトへの制約注入の
詳細な実装パターンは **`backtesting.md` セクション 5** を参照。

---

## CAGR（Compound Annual Growth Rate）

### 定義

```
CAGR = (V_end / V_start) ^ (1 / years) - 1
```

### 実装パターン: ローリング CAGR

```python
def calculate_cagr(
    self,
    prices: pd.Series,
    years: int,
) -> pd.Series:
    if years <= 0:
        raise ValidationError(
            f"years must be positive, got {years}",
            field="years",
            value=years,
        )

    if prices.empty:
        return pd.Series(dtype=float)

    # Period T = years * 12 months
    periods = years * 12

    # Start value (lagged)
    v_start = prices.shift(periods)

    # End value (current)
    v_end = prices

    # CAGR = (v_end / v_start)^(1/years) - 1
    # Handle zero/negative values
    cagr = np.where(
        v_start > 0,
        (v_end / v_start) ** (1 / years) - 1,
        np.nan,
    )

    return pd.Series(cagr, index=prices.index)
```

> **参照**: `src/factor/core/return_calculator.py` lines 367-428 -- CAGR 計算の完全な実装

### CAGR の注意点

| 注意点 | 対策 |
|--------|------|
| 開始値がゼロまたは負 | `np.nan` を返す（ゼロ除算防止） |
| データ不足（期間 < years） | `shift(periods)` が NaN を返すため自然にハンドリング |
| 月次前提 | `periods = years * 12` は月次データが前提。日次の場合は `years * 252` |

### CAGR の使用例

```python
calculator = ReturnCalculator()

# 3年 CAGR（月次データ）
cagr_3y = calculator.calculate_cagr(monthly_prices, years=3)

# 5年 CAGR（月次データ）
cagr_5y = calculator.calculate_cagr(monthly_prices, years=5)
```

---

## MTD / YTD リターン

### MTD（Month-to-Date）

月初の最初のデータポイントから現在値までの simple リターン：

```python
def _calculate_mtd_return(prices: pd.Series) -> float | None:
    current_date = prices.index[-1]
    current_month = current_date.month
    current_year = current_date.year

    # Find the first price of the current month
    month_start_mask = (prices.index.month == current_month) & (
        prices.index.year == current_year
    )
    month_prices = prices[month_start_mask]

    if month_prices.empty or len(month_prices) < 1:
        return None

    month_start_price = month_prices.iloc[0]
    current_price = prices.iloc[-1]

    if month_start_price == 0:
        return None

    return float((current_price - month_start_price) / month_start_price)
```

> **参照**: `src/analyze/returns/returns.py` lines 120-160 -- MTD リターン計算

### YTD（Year-to-Date）

年初の最初のデータポイントから現在値までの simple リターン：

```python
def _calculate_ytd_return(prices: pd.Series) -> float | None:
    current_date = prices.index[-1]
    current_year = current_date.year

    year_start_mask = prices.index.year == current_year
    year_prices = prices[year_start_mask]

    if year_prices.empty or len(year_prices) < 1:
        return None

    year_start_price = year_prices.iloc[0]
    current_price = prices.iloc[-1]

    if year_start_price == 0:
        return None

    return float((current_price - year_start_price) / year_start_price)
```

> **参照**: `src/analyze/returns/returns.py` lines 163-200 -- YTD リターン計算

---

## NaN 伝播ルール

### 基本原則

NaN を含む価格データに対するリターン計算では、NaN が結果に伝播する。

```python
prices = pd.Series([100.0, 105.0, float("nan"), 110.0, 115.0])
returns = prices.pct_change()

# returns:
# 0      NaN      # 最初の要素は常に NaN（前日なし）
# 1     0.05      # 105 / 100 - 1
# 2      NaN      # NaN 価格のリターンは NaN
# 3      NaN      # NaN 直後のリターンも NaN（分母が NaN）
# 4    0.0455     # 115 / 110 - 1
```

### NaN ハンドリングパターン

| パターン | 処理 | 用途 |
|----------|------|------|
| `dropna()` で事前除去 | NaN を含む行を除外して計算 | 期間リターン計算（`calculate_return`） |
| NaN 伝播を許容 | NaN をそのまま伝播させる | 時系列の連続性を保持する場合 |
| `fillna(0.0)` で補完 | NaN を 0 リターンに置換 | ポートフォリオリターン（欠損 = リターンなし） |

### 最低データ数の検証

```python
# Check if we have enough data
if len(clean_prices) <= period:
    logger.debug(
        "Insufficient data for period",
        period=period,
        data_length=len(clean_prices),
    )
    return None
```

> **参照**: `src/analyze/returns/returns.py` lines 86-92 -- 最低データ数検証

---

## まとめ: リターン計算チェックリスト

実装時に以下を確認:

- [ ] 年率化に単利公式 `return * (252/n)` を使用していないか → 複利 `(1 + return) ** (252/n) - 1` を使用
- [ ] 累積リターンを `sum()` で計算していないか → `prod(1 + r) - 1` を使用
- [ ] ポートフォリオの加重平均に log リターンを使用していないか → simple リターンを使用
- [ ] フォワードリターンをシグナルとして使用していないか → バックテスト評価用のみ
- [ ] Point-in-Time 制約を適用しているか → `as_of_date <= rebalance_date`
- [ ] CAGR 計算で開始値がゼロの場合を防御しているか → `np.nan` を返す
- [ ] NaN を含む価格データの伝播ルールを理解しているか → `dropna()` or 許容
- [ ] 最低データ数の検証を実装しているか → データ不足時は `None` を返す
- [ ] simple vs log の選択理由をコメントまたは Docstring に記載しているか
