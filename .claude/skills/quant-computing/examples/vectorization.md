# ベクトル化パターン集

pandas/NumPy のベクトル演算を活用し、Python ループや `apply()` を排除するパターン集です。
既存コードベースの実装例と行番号注釈を含みます。

---

## 1. ループ → ベクトル演算の変換

### 1.1 日次リターン計算

**Before（Python ループ）**:

```python
# NG: iloc によるループ — O(n) だがオーバーヘッドが大きい
for i in range(1, len(df)):
    df.iloc[i, ret_col] = df.iloc[i]["close"] / df.iloc[i - 1]["close"] - 1
```

**After（ベクトル演算）**:

```python
# OK: pct_change() でワンライナー
df["return"] = df["close"].pct_change()

# 銘柄別にグループ化する場合
df["return"] = df.groupby("symbol")["close"].pct_change()
```

> **参照**: `src/strategy/integration/market_integration.py` line 265 — `close_data.pct_change()`

---

### 1.2 累積リターン計算

**Before（Python ループ）**:

```python
# NG: ループで累積を手動計算
cumulative = [1.0]
for r in daily_returns:
    cumulative.append(cumulative[-1] * (1 + r))
```

**After（ベクトル演算）**:

```python
# OK: cumprod() で累積リターンを一括計算
cumulative = (1 + daily_returns).cumprod()
```

> **参照**: `src/strategy/risk/calculator.py` lines 390-404 — `(1 + self._returns).cumprod()`

---

### 1.3 CAGR（年率複合成長率）計算

**Before（Python ループ）**:

```python
# NG: 行ごとにゼロ除算チェック
cagr_list = []
for start, end in zip(v_start, v_end):
    if start > 0:
        cagr_list.append((end / start) ** (1 / years) - 1)
    else:
        cagr_list.append(float("nan"))
```

**After（`np.where` によるベクトル条件分岐）**:

```python
# OK: np.where で条件分岐をベクトル化
v_start = prices.shift(periods)
v_end = prices

cagr = np.where(
    v_start > 0,
    (v_end / v_start) ** (1 / years) - 1,
    np.nan,
)
```

> **参照**: `src/factor/core/return_calculator.py` lines 422-426 — `np.where(v_start > 0, ...)`

---

### 1.4 ポートフォリオ加重リターン（ブロードキャスティング）

**Before（Python ループ）**:

```python
# NG: 銘柄ごとにループして加重平均を計算
portfolio_returns = pd.Series(0.0, index=returns_df.index)
for ticker, weight in weights.items():
    portfolio_returns += returns_df[ticker].fillna(0.0) * weight
```

**After（DataFrame の要素積 + `sum(axis=1)`）**:

```python
# OK: DataFrame とウェイト DataFrame の要素積 → 行方向に合計
# ブロードキャスティングにより全要素を一括計算
weights_df = pd.DataFrame(weight_rows, index=returns_df.index)
weights_df = weights_df.reindex(columns=returns_df.columns, fill_value=0.0)

portfolio_returns = (returns_df.fillna(0.0) * weights_df).sum(axis=1)
```

> **参照**: `src/dev/ca_strategy/return_calculator.py` lines 565-570 — `(returns_df.fillna(0.0) * weights_df).sum(axis=1)`

---

### 1.5 正規化リターン（Series の除算 + ブロードキャスティング）

**Before（Python ループ）**:

```python
# NG: 各要素を初期値で割る
normalized = []
initial = df_price.iloc[0]
for i in range(len(df_price)):
    normalized.append((df_price.iloc[i] / initial - 1) * 100)
```

**After（ベクトル演算チェーン）**:

```python
# OK: div/sub/mul のメソッドチェーンで一括計算
result = df_price.div(df_price.iloc[0]).sub(1).mul(100).iloc[-1].to_frame()
```

> **参照**: `src/analyze/reporting/market_report_utils.py` line 353 — `.div(df_price.iloc[0]).sub(1).mul(100)`

---

## 2. apply() 回避パターン

### 2.1 Winsorize: `apply()` → `quantile()` + `clip()`

`apply()` は行/列ごとに Python 関数を呼び出すため、大規模データでは遅い。
pandas のビルトインメソッドで代替できるケースが多い。

**apply() を使うケース（DataFrame 列ごとの処理）**:

```python
# DataFrame 全列に同じ処理を適用（列数が少ない場合は許容）
return data.apply(lambda x: self._winsorize_series(x, limits=limits))
```

> **参照**: `src/factor/core/normalizer.py` line 333 — DataFrame の列ごと処理

**apply() 不要のケース（Series 単体）**:

```python
# OK: quantile() + clip() でベクトル化
lower_quantile = series.quantile(lower_limit)
upper_quantile = series.quantile(1 - upper_limit)
return series.clip(lower=lower_quantile, upper=upper_quantile)
```

> **参照**: `src/factor/core/normalizer.py` lines 342-345 — `series.clip(lower=..., upper=...)`

**判断基準**:

| 入力 | 推奨 | 理由 |
|------|------|------|
| `pd.Series` | `clip()` / `quantile()` 等のビルトイン | C 実装で高速 |
| `pd.DataFrame`（少数列） | `apply()` 許容 | 列数が少なければオーバーヘッド軽微 |
| `pd.DataFrame`（多数列） | `stack()` → Series 処理 → `unstack()` | apply のループコスト削減 |

---

### 2.2 行単位 apply() → ベクトル演算

**Before（`apply(axis=1)` で行ごとに処理）**:

```python
# NG: 行ごとに Python 関数を呼び出し
df["signal"] = df.apply(
    lambda row: 1 if row["sma_20"] > row["sma_50"] else -1, axis=1
)
```

**After（`np.where` でベクトル化）**:

```python
# OK: 条件分岐を np.where でベクトル化
df["signal"] = np.where(df["sma_20"] > df["sma_50"], 1, -1)
```

**3値以上の分岐には `np.select`**:

```python
conditions = [
    df["sma_20"] > df["sma_50"] * 1.02,  # 強い上昇トレンド
    df["sma_20"] > df["sma_50"],           # 弱い上昇トレンド
    df["sma_20"] < df["sma_50"] * 0.98,   # 強い下降トレンド
]
choices = [2, 1, -2]
df["signal"] = np.select(conditions, choices, default=-1)
```

---

### 2.3 ランク計算: apply() → groupby + rank()

**Before（apply で手動ランキング）**:

```python
# NG: 日付ごとにソートしてランクを付与
def rank_in_group(group):
    return group.rank(ascending=False, method="min").astype(int)

result["rank"] = df.groupby("date")["score"].apply(rank_in_group)
```

**After（`transform` + `rank`）**:

```python
# OK: transform + rank でベクトル化
result["sector_rank"] = (
    result.groupby(["as_of_date", "gics_sector"])["aggregate_score"]
    .rank(ascending=False, method="min")
    .astype(int)
)
```

> **参照**: `src/dev/ca_strategy/neutralizer.py` lines 125-129 — `.rank(ascending=False, method="min")`

---

## 3. groupby + transform パターン

### 3.1 セクター内 Z-score 正規化

グループ内で正規化を行い、元の DataFrame と同じインデックスで結果を返す。

```python
# groupby + transform: 各グループ内でベクトル演算を適用
# 結果は元の DataFrame と同じ行数・インデックスを保持
result[output_column] = data.groupby(group_columns)[value_column].transform(
    normalize_func
)
```

> **参照**: `src/factor/core/normalizer.py` line 439 — `data.groupby(group_columns)[value_column].transform(normalize_func)`

**transform の特徴**:

| メソッド | 出力形状 | 用途 |
|----------|----------|------|
| `transform()` | 入力と同じ行数 | グループ内正規化、フィル |
| `apply()` | グループごとに任意 | 集約＋変形が必要な場合 |
| `agg()` | グループ数の行 | 集約のみ |

---

### 3.2 欠損値のグループ内補完

セクター中央値でファクター値の欠損を補完し、元の行構造を保持する。

```python
# セクター中央値で欠損値を補完
df[factor_list] = df.groupby(["date", "GICS Sector"])[factor_list].transform(
    lambda x: x.fillna(x.median())
)

# セクター内で補完しきれない場合、全体中央値で再補完
df[factor] = df.groupby("date")[factor].transform(
    lambda x: x.fillna(x.median())
)

# それでも残る欠損は中立値で埋める
df[factor] = df[factor].fillna(0.5)
```

> **参照**: `src/market/factset/factset_utils.py` lines 2281-2326 — 3段階の欠損値補完パイプライン

---

### 3.3 グループ内パーセンタイルランク

```python
# 日付×セクター内でパーセンタイルランクを計算
df[pctrank_col] = df.groupby(groupby_cols)[factor_name].transform(
    lambda x: x.rank(pct=True)
)
```

> **参照**: `src/factor/sample/roic_make_data_files_ver2.py` line 647 — `groupby(...)[factor].transform(lambda x: x.rank(pct=True))`

---

### 3.4 グループ内 Z-score 正規化

```python
# 日付ごとの Z-score
df[zscore_col] = df.groupby(groupby_cols)[factor_name].transform(
    lambda x: (x - x.mean()) / x.std()
)

# セクター内 Z-score（セクター中立化）
df[factor_list] = df.groupby(["date", "GICS Sector"])[factor_list].transform(
    lambda x: (x - x.mean()) / x.std()
)
```

> **参照**: `src/factor/sample/roic_make_data_files_ver2.py` lines 869-873 — groupby + Z-score transform
> **参照**: `src/market/factset/factset_utils.py` line 2281 — セクター内 transform

---

### 3.5 Quintile 分類（groupby + transform + qcut）

```python
# 日付ごとに五分位に分類
def _calculate_quintile(group: pd.Series) -> pd.Series:
    try:
        return pd.qcut(group, q=5, labels=[1, 2, 3, 4, 5]).astype(float)
    except ValueError:
        return pd.Series(np.nan, index=group.index)

result[rank_column] = df.groupby(date_column)[roic_column].transform(
    _calculate_quintile
)
```

> **参照**: `src/factor/factors/quality/roic.py` lines 148-166 — `groupby(date_column)[roic_column].transform(_calculate_quintile)`

---

## 4. ブロードキャスティング活用

### 4.1 Series の map によるカテゴリマッピング

辞書マッピングで新しい列を効率的に生成する。

```python
# ticker → sector のマッピングをベクトル化
sector_map = {t.ticker: t.gics_sector for t in universe.tickers}
result["gics_sector"] = result["ticker"].map(sector_map)
```

> **参照**: `src/dev/ca_strategy/neutralizer.py` line 92 — `result["ticker"].map(sector_map)`

---

### 4.2 DataFrame 同士の要素積（ブロードキャスティング）

```python
# ウェイト DataFrame × リターン DataFrame → 行方向に合計
# 列名が一致していれば自動的にアライメントされる
weights_df = weights_df.reindex(columns=returns_df.columns, fill_value=0.0)
portfolio_returns = (returns_df.fillna(0.0) * weights_df).sum(axis=1)
```

> **参照**: `src/dev/ca_strategy/return_calculator.py` lines 567-570

---

### 4.3 ウェイト再配分（辞書内包 + 合計値による正規化）

```python
# ウェイト合計が 1.0 になるよう正規化
total = sum(current_weights.values())
if total > 0 and abs(total - 1.0) > 1e-10:
    current_weights = {k: v / total for k, v in current_weights.items()}
```

> **参照**: `src/dev/ca_strategy/return_calculator.py` lines 500-502 — ウェイト正規化
> **正規化パターンの詳細**: `numerical-precision.md` セクション 3「ウェイト正規化の閾値」を参照

---

## 5. パフォーマンス比較の目安

> **注意**: 以下の数値は参考値です（Python 3.12, pandas 2.x, Apple M2, 単一列処理）。
> 実際の計測には必ず `profile_context` を使用してください。

| パターン | 1万行 | 100万行 | 備考 |
|----------|-------|---------|------|
| Python ループ (`for i in range`) | ~50ms | ~5,000ms | 最も遅い |
| `apply(axis=1)` | ~30ms | ~3,000ms | 行ごとに Python 呼び出し |
| `apply(axis=0)` | ~5ms | ~500ms | 列ごと（列数依存） |
| `groupby().transform()` | ~3ms | ~100ms | C 実装の集約 |
| ベクトル演算 (`pct_change`, `clip`) | ~1ms | ~10ms | 最速、C/Cython 実装 |
| `np.where` / `np.select` | ~1ms | ~10ms | NumPy の条件分岐 |

```python
from utils_core.profiling import profile_context

with profile_context("ベクトル化版リターン計算"):
    returns = df.groupby("symbol")["close"].pct_change()
```

> **参照**: `template/src/template_package/utils/profiling.py` — プロファイリングユーティリティ

---

## まとめ: 変換チェックリスト

実装時に以下を確認:

- [ ] `for i in range(len(df))` / `iterrows()` → `pct_change()` / `cumsum()` / `cumprod()`
- [ ] `apply(axis=1)` の条件分岐 → `np.where()` / `np.select()`
- [ ] グループ内の正規化・ランク → `groupby().transform()`
- [ ] 辞書マッピング → `Series.map(dict)`
- [ ] DataFrame 間の演算 → 要素積 + `sum(axis=1)` / `dot()`
- [ ] 変換前後で `profile_context` による計測を実施
