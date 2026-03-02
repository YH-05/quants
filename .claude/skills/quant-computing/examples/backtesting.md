# バックテスト実装パターン集

バックテストの標準パターンを体系化したパターン集です。
前方参照バイアス防止（`signals.shift(1)` 必須）、取引コストモデル、
ウォークフォワード分割、Buy-and-Hold ドリフト実装を含みます。
既存コードベースの実装例と行番号注釈を含みます。

---

## 最重要ルール: `signals.shift(1)` 必須

**シグナルは必ず 1 日シフトしてからポジションに変換すること。**

当日の終値（close）で計算されたシグナルは、翌営業日の始値（open）で執行される。
`shift(1)` を省略すると、**前方参照バイアス（look-ahead bias）** が発生し、
バックテスト結果が非現実的に良くなる。

```python
# NG: 当日シグナルで当日リターンを取る（前方参照バイアス）
positions = signals  # shift なし
portfolio_returns = (positions * daily_returns).sum(axis=1)

# OK: シグナルを 1 日シフトして翌日リターンを取る
positions = signals.shift(1)  # 必須: 当日 close 計算 → 翌日 open 執行
portfolio_returns = (positions * daily_returns).sum(axis=1)
```

### なぜ `shift(1)` が必要か

| 時点 | 情報 | 執行 |
|------|------|------|
| Day T の close | シグナル計算に使用可能 | 執行不可（市場はすでに閉じている） |
| Day T+1 の open | - | シグナルに基づいて注文執行 |
| Day T+1 の close | - | 日次リターンが確定 |

`shift(1)` を忘れると Day T の close で計算したシグナルを Day T のリターンに適用してしまい、
「未来の株価を知った上で取引している」状態になる。

### 検出パターン

コードレビューで以下を検出した場合は前方参照バイアスの可能性がある:

```python
# 危険: shift なしでリターンに乗算
portfolio_returns = (signals * returns).sum(axis=1)

# 危険: 当日計算のウェイトを当日リターンに適用
daily_return = sum(weight_i * return_i)  # weight が当日 close ベースの場合

# 安全: shift(1) で 1 日遅延
portfolio_returns = (signals.shift(1) * returns).sum(axis=1)
```

---

## 1. ベクトル化バックテストの標準パターン

### 1.1 基本構造: シグナル → ポジション → リターン

```python
import numpy as np
import pandas as pd

def vectorized_backtest(
    prices: pd.DataFrame,
    signals: pd.DataFrame,
    *,
    cost_bps: float = 0.0,
) -> pd.Series:
    """Vectorized backtest with look-ahead bias prevention.

    Parameters
    ----------
    prices : pd.DataFrame
        Daily close prices (index: date, columns: tickers).
    signals : pd.DataFrame
        Trading signals (same shape as prices). Values represent
        target weights (e.g., 0.5 = 50% allocation).
    cost_bps : float
        One-way transaction cost in basis points (e.g., 10.0 = 10bps).

    Returns
    -------
    pd.Series
        Daily portfolio returns.
    """
    # Step 1: 日次リターン計算
    daily_returns = prices.pct_change()

    # Step 2: シグナルを 1 日シフト（最重要ルール）
    positions = signals.shift(1)

    # Step 3: ポートフォリオリターン = ポジション × リターンの行方向合計
    gross_returns = (positions * daily_returns).sum(axis=1)

    # Step 4: 取引コスト控除（オプション）
    if cost_bps > 0:
        turnover = positions.diff().abs().sum(axis=1)
        cost = turnover * (cost_bps / 10_000)
        return gross_returns - cost

    return gross_returns
```

### 1.2 ウェイト正規化付きバックテスト

ウェイトの合計が 1.0 になるよう正規化する。閾値 `1e-10` で浮動小数点誤差を吸収。

```python
def normalize_weights(weights: pd.DataFrame) -> pd.DataFrame:
    """Normalize weights to sum to 1.0 per row.

    Uses threshold 1e-10 to handle floating-point precision.
    """
    row_sums = weights.sum(axis=1)

    # 行ごとの合計が 1e-10 以下の場合はゼロウェイトとして扱う
    valid_mask = row_sums.abs() > 1e-10
    normalized = weights.div(row_sums, axis=0).where(valid_mask, 0.0)

    return normalized
```

> **参照**: `src/dev/ca_strategy/return_calculator.py` lines 500-502 -- ウェイト正規化閾値 `1e-10`

---

## 2. Buy-and-Hold ドリフト

### 2.1 ドリフトの数式

Buy-and-Hold 戦略では、ポートフォリオウェイトが日々の株価変動によりドリフトする。
銘柄 *i* の Day *t+1* のウェイトは:

```
w_i(t+1) = w_i(t) * (1 + r_i(t)) / sum_j[ w_j(t) * (1 + r_j(t)) ]
```

リバランスを行わない限り、勝者銘柄のウェイトが増加し、
敗者銘柄のウェイトが減少する。

### 2.2 実装パターン: 日次ドリフト追跡

```python
# Drift weights based on today's returns (Buy-and-Hold)
if current_weights:
    day_returns = returns_df.loc[idx_date]
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

> **参照**: `src/dev/ca_strategy/return_calculator.py` lines 550-563 -- Buy-and-Hold ドリフト後のウェイト正規化

### 2.3 ベクトル化されたウェイト付きリターン計算

ドリフト追跡で構築したウェイト行列を使い、最終的なリターンをベクトル化計算する:

```python
# Build weight matrix row-by-row (weights drift via Buy-and-Hold)
weight_rows: list[dict[str, float]] = []

for idx_date in returns_df.index:
    # ... corporate action handling ...
    # ... drift computation ...
    weight_rows.append(dict(current_weights))

# Vectorized computation: build weights DataFrame, align columns,
# element-wise multiply, and sum across tickers per day
weights_df = pd.DataFrame(weight_rows, index=returns_df.index)
weights_df = weights_df.reindex(columns=returns_df.columns, fill_value=0.0)

portfolio_returns = (returns_df.fillna(0.0) * weights_df).sum(axis=1)
```

> **参照**: `src/dev/ca_strategy/return_calculator.py` lines 462-570 -- `_compute_weighted_returns()` の完全な Buy-and-Hold ドリフト実装

### 2.4 定期リバランス（オプション）

Buy-and-Hold の途中で定期的にウェイトをリセットすることも可能:

```python
# Check for periodic rebalance (Bloomberg MCap mode)
if rebalance_dates and trading_date in rebalance_dates:
    rebal_weights = rebalance_dates[trading_date]
    active = set(returns_df.columns) & set(rebal_weights.keys())
    current_weights = {
        t: rebal_weights[t]
        for t in active
        if t in current_weights or t in rebal_weights
    }
    rebal_total = sum(current_weights.values())
    if rebal_total > 0 and abs(rebal_total - 1.0) > 1e-10:
        current_weights = {
            k: v / rebal_total for k, v in current_weights.items()
        }
```

> **参照**: `src/dev/ca_strategy/return_calculator.py` lines 527-545 -- 定期リバランス処理

---

## 3. 取引コストモデル

### 3.1 線形コストモデル（標準）

最もシンプルなモデル。ターンオーバーに比例するコスト:

```python
def apply_linear_cost(
    gross_returns: pd.Series,
    positions: pd.DataFrame,
    cost_bps: float = 10.0,
) -> pd.Series:
    """Apply linear transaction cost based on turnover.

    Parameters
    ----------
    gross_returns : pd.Series
        Portfolio returns before costs.
    positions : pd.DataFrame
        Daily position weights (already shifted by 1 day).
    cost_bps : float
        One-way transaction cost in basis points.
        Typical values: 5-20 bps for liquid US equities.

    Returns
    -------
    pd.Series
        Net returns after transaction costs.
    """
    # Turnover = sum of absolute weight changes
    turnover = positions.diff().abs().sum(axis=1)

    # Cost = turnover * one-way cost rate
    # Note: diff captures both buy and sell, so this is round-trip cost
    cost = turnover * (cost_bps / 10_000)

    return gross_returns - cost
```

### 3.2 コスト水準の目安

| 資産クラス | コスト (bps, 片道) | 備考 |
|-----------|-------------------|------|
| 米国大型株 | 5-10 | S&P 500 構成銘柄 |
| 米国中型株 | 10-20 | Russell Midcap |
| 米国小型株 | 20-50 | Russell 2000 |
| 新興国株式 | 30-100 | 流動性に大きく依存 |
| 国内株式 | 5-15 | TOPIX 100 構成銘柄 |

### 3.3 ターンオーバーの計算

```python
# 日次ターンオーバー: ウェイト変化の絶対値合計
daily_turnover = positions.diff().abs().sum(axis=1)

# 年率ターンオーバー: 日次ターンオーバーの年間合計
annual_turnover = daily_turnover.sum() / (len(daily_turnover) / 252)
```

---

## 4. ウォークフォワード分割

### 4.1 固定ウィンドウ（Rolling Window）

訓練期間の長さが固定で、時間とともにスライドする:

```python
def rolling_walk_forward(
    data: pd.DataFrame,
    train_months: int = 36,
    test_months: int = 12,
) -> list[tuple[pd.DataFrame, pd.DataFrame]]:
    """Generate rolling walk-forward train/test splits.

    テスト参照: `tests/factor/unit/core/test_walk_forward.py` -- 境界値・空データ・重複日付テスト

    Parameters
    ----------
    data : pd.DataFrame
        Full dataset with DatetimeIndex.
    train_months : int
        Training window length in months.
    test_months : int
        Testing (out-of-sample) window length in months.

    Returns
    -------
    list[tuple[pd.DataFrame, pd.DataFrame]]
        List of (train, test) DataFrame pairs.
    """
    splits: list[tuple[pd.DataFrame, pd.DataFrame]] = []
    dates = data.index.to_series()

    start = dates.iloc[0]
    end = dates.iloc[-1]

    train_start = start
    while True:
        train_end = train_start + pd.DateOffset(months=train_months)
        test_end = train_end + pd.DateOffset(months=test_months)

        if test_end > end:
            break

        train = data[train_start:train_end]  # type: ignore[misc]
        test = data[train_end:test_end]  # type: ignore[misc]

        if len(train) > 0 and len(test) > 0:
            splits.append((train, test))

        # Slide forward by test_months
        train_start = train_start + pd.DateOffset(months=test_months)

    return splits
```

### 4.2 拡張ウィンドウ（Expanding Window）

訓練期間の開始点が固定で、終了点のみが前進する:

```python
def expanding_walk_forward(
    data: pd.DataFrame,
    min_train_months: int = 36,
    test_months: int = 12,
) -> list[tuple[pd.DataFrame, pd.DataFrame]]:
    """Generate expanding walk-forward train/test splits.

    テスト参照: `tests/factor/unit/core/test_walk_forward.py` -- 境界値・空データ・重複日付テスト

    The training window starts from the beginning of the data
    and expands forward. This preserves all historical information.

    Parameters
    ----------
    data : pd.DataFrame
        Full dataset with DatetimeIndex.
    min_train_months : int
        Minimum training window length in months.
    test_months : int
        Testing (out-of-sample) window length in months.

    Returns
    -------
    list[tuple[pd.DataFrame, pd.DataFrame]]
        List of (train, test) DataFrame pairs.
    """
    splits: list[tuple[pd.DataFrame, pd.DataFrame]] = []
    dates = data.index.to_series()

    start = dates.iloc[0]
    end = dates.iloc[-1]

    train_end = start + pd.DateOffset(months=min_train_months)
    while True:
        test_end = train_end + pd.DateOffset(months=test_months)

        if test_end > end:
            break

        train = data[start:train_end]  # type: ignore[misc]
        test = data[train_end:test_end]  # type: ignore[misc]

        if len(train) > 0 and len(test) > 0:
            splits.append((train, test))

        # Expand forward by test_months
        train_end = train_end + pd.DateOffset(months=test_months)

    return splits
```

### 4.3 Rolling vs Expanding の選択基準

| 基準 | Rolling Window | Expanding Window |
|------|---------------|-----------------|
| レジーム変化への適応 | 速い（古いデータを捨てる） | 遅い（全データを保持） |
| 統計的安定性 | データが少ないため不安定 | データが多いため安定 |
| 計算コスト | 一定 | 増加（データ量に比例） |
| **推奨場面** | **市場構造が変化する短期戦略** | **長期ファクター投資** |

### 4.4 選択フローチャート

```
ウォークフォワード分割の選択:
├── 市場構造が頻繁に変化するか？
│   ├── Yes → Rolling Window（古いデータを除外してレジーム適応）
│   └── No → Expanding Window（全データで統計的に安定）
├── 訓練データ量が重要か？
│   ├── Yes（機械学習モデル等） → Expanding Window
│   └── No（シンプルなルールベース） → Rolling Window
└── 計算コストの制約は？
    ├── 厳しい → Rolling Window（一定コスト）
    └── 許容 → Expanding Window
```

---

## 5. Point-in-Time（PoiT）制約

### 5.1 基本原則

バックテストでは `as_of_date` 以降のデータを使用してはならない。
これは前方参照バイアスの一種であり、`signals.shift(1)` とは異なるレイヤーの制約。

| バイアス | 原因 | 防止策 |
|----------|------|--------|
| シグナル前方参照 | 当日 close で当日リターンを取る | `signals.shift(1)` |
| データ前方参照 | 未公表の決算データを使用 | `as_of_date <= rebalance_date` |
| サバイバーシップ | 上場廃止銘柄を除外 | コーポレートアクション対応 |

### 5.2 PoiT フィルタリング

```python
from datetime import date

CUTOFF_DATE: date = date(2015, 9, 30)

def filter_by_pit(
    transcripts: list[Transcript],
    cutoff_date: date = CUTOFF_DATE,
) -> list[Transcript]:
    """Filter transcripts to include only those on or before the cutoff date."""
    filtered = [t for t in transcripts if t.metadata.event_date <= cutoff_date]
    return filtered
```

> **参照**: `src/dev/ca_strategy/pit.py` lines 56-82 -- `filter_by_pit()` による PoiT フィルタリング

### 5.3 PoiT コンプライアンス検証

```python
def validate_pit_compliance(
    transcripts: list[Transcript],
    cutoff_date: date = CUTOFF_DATE,
) -> bool:
    """Validate that all transcripts comply with the cutoff date."""
    for transcript in transcripts:
        if transcript.metadata.event_date > cutoff_date:
            logger.warning(
                "PoiT compliance violation detected",
                ticker=transcript.metadata.ticker,
                event_date=transcript.metadata.event_date.isoformat(),
                cutoff_date=cutoff_date.isoformat(),
            )
            return False
    return True
```

> **参照**: `src/dev/ca_strategy/pit.py` lines 112-140 -- PoiT 検証

### 5.4 LLM プロンプトへの PoiT 制約注入

LLM を使った分析でも PoiT 制約を適用する:

```python
def get_pit_prompt_context(cutoff_date: date = CUTOFF_DATE) -> str:
    """Generate temporal constraint text for LLM prompt injection."""
    if not isinstance(cutoff_date, date):
        raise TypeError(f"cutoff_date must be a date, got {type(cutoff_date).__name__}")
    date_str = cutoff_date.isoformat()
    return (
        f"TEMPORAL CONSTRAINTS (MANDATORY):\n"
        f"- The current date is {date_str}.\n"
        f"- You must NOT use any information after {date_str}.\n"
        f"- SEC Filings must have filing_date on or before {date_str}.\n"
        f"- Do NOT use knowledge of future stock prices, earnings, or events.\n"
        f"- All analysis must be based solely on information available as of {date_str}."
    )
```

> **参照**: `src/dev/ca_strategy/pit.py` lines 85-109 -- LLM プロンプト用 PoiT コンテキスト生成

---

## 6. コーポレートアクション対応

### 6.1 上場廃止・合併時のウェイト再配分

上場廃止（delisting）や合併（merger）が発生した銘柄のウェイトを
残存銘柄に比例配分する:

```python
def _redistribute_weights(
    current_weights: dict[str, float],
    removed_tickers: set[str],
) -> dict[str, float]:
    """Redistribute weights from removed tickers proportionally.

    Sets removed tickers' weights to 0 and redistributes their
    combined weight proportionally to remaining tickers so that
    the total weight remains 1.0.
    """
    remaining = {
        k: v for k, v in current_weights.items() if k not in removed_tickers
    }

    if not remaining:
        return {}

    remaining_total = sum(remaining.values())
    if remaining_total == 0:
        return remaining

    # Scale remaining weights to sum to 1.0
    new_weights = {k: v / remaining_total for k, v in remaining.items()}
    return new_weights
```

> **参照**: `src/dev/ca_strategy/return_calculator.py` lines 328-380 -- `_redistribute_weights()` による比例再配分

### 6.2 日次ループ内でのコーポレートアクション適用

```python
for idx_date in returns_df.index:
    trading_date = idx_date.date() if hasattr(idx_date, "date") else idx_date
    removed_on_date: set[str] = set()

    for ticker, action_date in self._corporate_actions.items():
        if ticker in current_weights and trading_date >= action_date:
            removed_on_date.add(ticker)

    if removed_on_date:
        current_weights = self._redistribute_weights(
            current_weights=current_weights,
            removed_tickers=removed_on_date,
        )
```

> **参照**: `src/dev/ca_strategy/return_calculator.py` lines 507-525 -- 日次コーポレートアクション適用

---

## 7. スコア比例ウェイト（Hamilton 法丸め）

### 7.1 セクター内スコア比例ウェイト

銘柄スコアに比例してセクター内ウェイトを配分する:

```python
total_score = sum(s["aggregate_score"] for s in selected)

holdings: list[PortfolioHolding] = []
for stock in selected:
    score = stock["aggregate_score"]
    if total_score > 0:
        intra_weight = (score / total_score) * sector_weight
    else:
        intra_weight = sector_weight / len(selected)

    holdings.append(
        PortfolioHolding(
            ticker=stock["ticker"],
            weight=intra_weight,
            sector=sector,
            score=score,
            rationale_summary=f"Sector rank {stock['sector_rank']}, "
            f"score {score:.2f}",
        )
    )
```

> **参照**: `src/dev/ca_strategy/portfolio_builder.py` lines 314-335 -- スコア比例ウェイト配分

### 7.2 Hamilton 法（最大剰余法）による整数丸め

セクター別の銘柄数を比例配分し、端数を Hamilton 法で整数に丸める:

```python
import math

def largest_remainder_round(raw: dict[str, float]) -> dict[str, int]:
    """Round fractional counts preserving the total.

    Uses the largest-remainder method (Hamilton's method) to
    distribute integer counts proportionally.
    """
    if not raw:
        return {}

    total = round(sum(raw.values()))
    floors = {k: math.floor(v) for k, v in raw.items()}
    remainders = {k: v - math.floor(v) for k, v in raw.items()}

    current_total = sum(floors.values())
    deficit = total - current_total

    # Distribute remaining slots to sectors with largest remainders
    sorted_sectors = sorted(
        remainders.keys(),
        key=lambda k: remainders[k],
        reverse=True,
    )
    for i in range(min(deficit, len(sorted_sectors))):
        floors[sorted_sectors[i]] += 1

    return floors
```

> **参照**: `src/dev/ca_strategy/portfolio_builder.py` lines 252-290 -- Hamilton 法丸め（`_largest_remainder_round`）

---

## 8. 累積リターンとパフォーマンス評価

### 8.1 累積リターンの計算

```python
# 日次リターンから累積リターンを計算
cumulative = (1 + daily_returns).cumprod()

# 初日を 1.0 に正規化
cumulative = cumulative / cumulative.iloc[0]
```

### 8.2 パフォーマンス指標の算出

バックテスト結果の評価には `risk-metrics.md` のリスク指標を使用する:

```python
from strategy.risk.calculator import RiskCalculator

calc = RiskCalculator(
    returns=portfolio_returns,
    risk_free_rate=0.05,
    annualization_factor=252,
)

# 年率リターン（複利）
annualized_return = (1 + portfolio_returns).prod() ** (252 / len(portfolio_returns)) - 1

# リスク指標
sharpe = calc.sharpe_ratio()
sortino = calc.sortino_ratio()
mdd = calc.max_drawdown()
volatility = calc.volatility()
```

> **参照**: `src/strategy/risk/calculator.py` -- RiskCalculator の全リスク指標

### 8.3 ベンチマーク比較

```python
# Equal-weight benchmark
n = len(returns_df.columns)
equal_weight = 1.0 / n
benchmark_weights = {ticker: equal_weight for ticker in returns_df.columns}

benchmark_returns = calc.calculate_benchmark_returns(
    tickers=list(benchmark_weights.keys()),
    start=start_date,
    end=end_date,
)

# Active return
active_returns = portfolio_returns - benchmark_returns

# Information Ratio
ir = calc.information_ratio(benchmark_returns)
```

> **参照**: `src/dev/ca_strategy/return_calculator.py` lines 146-205 -- `calculate_benchmark_returns()` による等ウェイトベンチマーク

---

## まとめ: バックテストチェックリスト

実装時に以下を確認:

- [ ] `signals.shift(1)` を適用しているか（最重要: 前方参照バイアス防止）
- [ ] Point-in-Time 制約を適用しているか（`as_of_date <= rebalance_date`）
- [ ] コーポレートアクション（上場廃止・合併）を処理しているか
- [ ] ウェイトの合計が 1.0 に正規化されているか（閾値 `1e-10`）
- [ ] Buy-and-Hold ドリフトを正しく追跡しているか
- [ ] 取引コストを考慮しているか（コスト控除後のリターンで評価）
- [ ] ウォークフォワード分割でアウトオブサンプル評価を行っているか
- [ ] 累積リターンの計算に複利（`cumprod`）を使用しているか（`sum` は禁止）
- [ ] LLM 分析にも PoiT 制約をプロンプトに注入しているか
