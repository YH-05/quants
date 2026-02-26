# CA Strategy スコアウェイト算出方法論

**作成日**: 2026-02-26
**対象コード**: `src/dev/ca_strategy/` パッケージ
**パイプライン**: Phase 2（スコア集約）→ Phase 3（セクター中立化）→ Phase 4（ポートフォリオ構築）

---

## 1. 概要

CA Strategy のポートフォリオウェイトは、決算説明会トランスクリプトから抽出された主張（Claim）の確信度スコアを起点に、4段階の変換を経て算出される。

```
Phase 2: ScoredClaim（確信度付き主張）
    ↓  ScoreAggregator
Phase 3a: StockScore（銘柄別集約スコア）
    ↓  SectorNeutralizer
Phase 3b: RankedStock（セクター内ランキング）
    ↓  PortfolioBuilder
Phase 4: PortfolioHolding（最終ウェイト）
```

**重要な設計判断**: セクター中立化（Phase 3b）で算出される Z-score はランキングにのみ使用し、ウェイト計算には元の `aggregate_score` を使用する。

---

## 2. Phase 2: スコア集約（ScoreAggregator）

### 2.1 コード参照

- **ファイル**: `src/dev/ca_strategy/aggregator.py`
- **クラス**: `ScoreAggregator`
- **入力**: `dict[str, list[ScoredClaim]]` — 銘柄別のスコア付き主張リスト
- **出力**: `dict[str, StockScore]` — 銘柄別集約スコア

### 2.2 主張ウェイトの決定

各主張に対し、適用されたルールに基づくウェイトを付与する。複数ルール適用時は最大値を採用。

| ルール | ウェイト | 説明 |
|--------|:-------:|------|
| デフォルト | **1.0** | 構造的ルール非適用 |
| Rule 6（構造的優位性） | **1.5** | 競争優位が構造的である主張 |
| Rule 11（業界構造適合） | **2.0** | 業界構造と合致する主張 |

```python
# aggregator.py L196-220
def _compute_claim_weight(self, claim: ScoredClaim) -> float:
    applied = claim.rule_evaluation.applied_rules
    max_weight = self._default_weight  # 1.0

    for rule in applied:
        if rule == "rule_11":
            max_weight = max(max_weight, self._industry_weight)  # 2.0
        elif rule == "rule_6":
            max_weight = max(max_weight, self._structural_weight)  # 1.5

    return max_weight
```

### 2.3 CAGR接続ブースト

`cagr_connection` タイプの主張には確信度に対して ±10% の調整を適用する。

| 条件 | 調整 |
|------|------|
| `final_confidence ≥ 0.7` | `confidence × 1.10`（+10% ブースト） |
| `final_confidence < 0.7` | `confidence × 0.90`（-10% ペナルティ） |

```python
# aggregator.py L156-161
if claim.claim_type == "cagr_connection":
    if confidence >= 0.7:  # _CAGR_CONFIDENCE_THRESHOLD
        confidence = confidence * (1.0 + 0.10)  # _CAGR_BOOST
    else:
        confidence = confidence * (1.0 - 0.10)
```

### 2.4 集約スコアの算出

加重平均を計算し、[0, 1] にクランプする。

$$
\text{aggregate\_score} = \text{clamp}\left(\frac{\sum_{i} \text{confidence}_i \times w_i}{\sum_{i} w_i},\ 0,\ 1\right)
$$

ここで $w_i$ は主張ウェイト（1.0 / 1.5 / 2.0）、$\text{confidence}_i$ は調整後確信度。

```python
# aggregator.py L148-174
total_weighted_score = 0.0
total_weight = 0.0
for claim in claims:
    weight = self._compute_claim_weight(claim)
    confidence = claim.final_confidence
    # CAGR adjustment (上記参照)
    total_weighted_score += confidence * weight
    total_weight += weight

raw_score = total_weighted_score / total_weight if total_weight > 0 else 0.0
aggregate_score = max(0.0, min(1.0, raw_score))
```

### 2.5 構造的ウェイト比率

構造的ルール（Rule 6, Rule 11）が適用された主張のウェイト合計を全ウェイト合計で割った比率を `structural_weight` として記録する。

$$
\text{structural\_weight} = \frac{\sum_{i \in \text{structural}} w_i}{\sum_{i} w_i}
$$

### 2.6 出力例

| 銘柄 | aggregate_score | claim_count | structural_weight |
|------|:-:|:-:|:-:|
| DIS | 0.7571 | 7 | 0.0 |
| AAPL | 0.7286 | 7 | 0.0 |
| PPL | 0.7933 | 6 | 0.0 |
| CSL | 0.6950 | 10 | 0.0 |

---

## 3. Phase 3: セクター中立化（SectorNeutralizer）

### 3.1 コード参照

- **ファイル**: `src/dev/ca_strategy/neutralizer.py`
- **クラス**: `SectorNeutralizer`
- **依存**: `src/factor/core/normalizer.py` → `Normalizer`
- **入力**: `pd.DataFrame`（ticker, aggregate_score, as_of_date）+ `UniverseConfig`
- **出力**: 入力 DataFrame + `gics_sector`, `sector_zscore`, `sector_rank` カラム

### 3.2 ロバスト Z-score

セクター内（`as_of_date` × `gics_sector` グループ）でロバスト Z-score を算出する。

$$
Z = \frac{x - \tilde{x}}{\text{MAD} \times 1.4826}
$$

| 記号 | 定義 |
|------|------|
| $x$ | 個別銘柄の aggregate_score |
| $\tilde{x}$ | セクター内の中央値 |
| MAD | Median Absolute Deviation: $\text{median}(\|x_i - \tilde{x}\|)$ |
| 1.4826 | MAD → 標準偏差換算係数（正規分布仮定） |

```python
# normalizer.py L125-128
center = series.median()
mad = (series - center).abs().median()
scale = mad * 1.4826  # _MAD_SCALE_FACTOR
```

**最小サンプル数**: 5銘柄未満のセクターは Z-score = NaN（`min_samples=5`）。

### 3.3 セクター内ランキング

Z-score の代わりに、**元の aggregate_score** の降順ランクを `sector_rank` として付与する。

```python
# neutralizer.py L125-129
result["sector_rank"] = (
    result.groupby(["as_of_date", "gics_sector"])["aggregate_score"]
    .rank(ascending=False, method="min")
    .astype(int)
)
```

### 3.4 Z-score の役割

**Z-score はランキング補助情報としてのみ使用**される。Phase 4 のウェイト計算で使用されるのは元の `aggregate_score` であり、Z-score ではない。これにより、セクター間でスコアの相対的な意味が保たれる。

---

## 4. Phase 4: ポートフォリオ構築（PortfolioBuilder）

### 4.1 コード参照

- **ファイル**: `src/dev/ca_strategy/portfolio_builder.py`
- **クラス**: `PortfolioBuilder`
- **入力**: `list[RankedStock]`（Phase 3 出力）+ `list[BenchmarkWeight]`（セクターベンチマーク）
- **出力**: `PortfolioResult`（holdings, sector_allocations, as_of_date）

### 4.2 全体フロー

```
Step 1: セクター別銘柄数の配分（Largest Remainder Method）
Step 2: セクター内 Top-N 銘柄の選択（aggregate_score 降順）
Step 3: セクター内スコア比例ウェイトの算出
Step 4: 全銘柄ウェイトの正規化（合計 = 1.0）
```

### 4.3 Step 1: セクター別銘柄数の配分

#### 4.3.1 初期配分

ベンチマークのセクターウェイトに基づき、ターゲット銘柄数を按分する。

$$
\text{raw\_count}_s = \text{target\_size} \times \text{benchmark\_weight}_s
$$

**例**: target_size = 30, Information Technology のベンチマーク比率 = 18.6%

$$
\text{raw\_count}_{IT} = 30 \times 0.186 = 5.58
$$

#### 4.3.2 最大剰余法（Hamilton's Method）

端数を丸めるために**最大剰余法**（Largest Remainder Method）を使用する。これは比例代表制の議席配分で使用されるアルゴリズムで、端数の合計が正確にターゲット銘柄数と一致することを保証する。

**アルゴリズム**:

1. 各セクターの raw_count を切り捨て → `floor`
2. 剰余（remainder）= raw_count − floor を計算
3. 全セクターの floor の合計を計算
4. 不足分（deficit）= target_size − floor の合計
5. 剰余が大きい順に1銘柄ずつ追加（deficit 回）

```python
# portfolio_builder.py L252-290
total = round(sum(raw.values()))
floors = {k: math.floor(v) for k, v in raw.items()}
remainders = {k: v - math.floor(v) for k, v in raw.items()}

current_total = sum(floors.values())
deficit = total - current_total

sorted_sectors = sorted(
    remainders.keys(),
    key=lambda k: remainders[k],
    reverse=True,
)
for i in range(min(deficit, len(sorted_sectors))):
    floors[sorted_sectors[i]] += 1
```

#### 4.3.3 制約

- **最小銘柄数**: 候補が1銘柄以上あるセクターは最低1銘柄を選択
- **上限**: セクター内の候補銘柄数を超えない

```python
# portfolio_builder.py L243-248
counts[sector] = max(
    1,              # _MIN_STOCKS_PER_SECTOR
    min(counts[sector], available),
)
```

#### 4.3.4 30-stock ポートフォリオの配分例

| セクター | ベンチマーク比率 | raw_count | 最終配分 |
|---------|:-:|:-:|:-:|
| Consumer Discretionary | 13.0% | 3.90 | **4** |
| Consumer Staples | 16.3% | 4.89 | **5** |
| Energy | 5.5% | 1.65 | **2** |
| Financials | 9.9% | 2.97 | **4** |
| Health Care | 19.1% | 5.73 | **6** |
| Industrials | 10.2% | 3.06 | **3** |
| Information Technology | 18.6% | 5.58 | **5** |
| Materials | 2.7% | 0.81 | **1** |
| Telecommunication Services | 0.9% | 0.27 | **1** |
| Utilities | 1.3% | 0.39 | **1** |
| **合計** | **97.5%** | — | **32** |

※ 実際の30-stock出力は33銘柄。ベンチマーク合計が100%未満のため、最小銘柄数制約が効き、実際のtarget_sizeを若干超過する場合がある。

### 4.4 Step 2: セクター内 Top-N 銘柄選択

各セクター内で `aggregate_score` の降順にソートし、Step 1 で決定した銘柄数分だけ選択する。

```python
# portfolio_builder.py L143-148, L164-165
for sector in stocks_by_sector:
    stocks_by_sector[sector].sort(
        key=lambda s: s["aggregate_score"],
        reverse=True,
    )
# ...
selected = available[:count]
```

**注意**: ランキングの基準は `sector_rank`（Z-score ベース）ではなく `aggregate_score` の降順ソートである。実質的には同じ順序になるが、Z-score が NaN のセクター（5銘柄未満）でも問題なく動作する。

### 4.5 Step 3: セクター内スコア比例ウェイト

セクター内の各銘柄に、セクターベンチマークウェイトをスコア比例で配分する。

$$
w_i = \frac{s_i}{\sum_{j \in \text{sector}} s_j} \times W_{\text{sector}}
$$

| 記号 | 定義 |
|------|------|
| $s_i$ | 銘柄 $i$ の aggregate_score |
| $\sum_j s_j$ | セクター内全選択銘柄のスコア合計 |
| $W_{\text{sector}}$ | ベンチマークのセクターウェイト |

```python
# portfolio_builder.py L314-322
total_score = sum(s["aggregate_score"] for s in selected)
for stock in selected:
    score = stock["aggregate_score"]
    if total_score > 0:
        intra_weight = (score / total_score) * sector_weight
    else:
        intra_weight = sector_weight / len(selected)  # フォールバック: 等ウェイト
```

#### 具体例: Consumer Discretionary セクター（30-stock）

ベンチマーク比率 = 13.0%、選択銘柄4銘柄:

| 銘柄 | score | score / Σscores | × sector_weight | 正規化前 weight |
|------|:-----:|:------:|:------:|:------:|
| DIS | 0.7571 | 26.8% | × 0.130 | 0.03490 |
| ORLY | 0.7129 | 25.3% | × 0.130 | 0.03285 |
| AMZN | 0.7000 | 24.8% | × 0.130 | 0.03229 |
| ITV | 0.6525 | 23.1% | × 0.130 | 0.03008 |
| **合計** | **2.8225** | **100%** | | **0.13012** |

スコアレンジ（0.6525〜0.7571）が狭いため、セクター内ウェイト差は小さい（最大 3.49% vs 最小 3.01%）。

### 4.6 Step 4: 全体正規化

全セクターの正規化前ウェイトの合計が 1.0 にならない場合（ベンチマーク比率の合計 ≠ 100%、候補銘柄不足等）、全銘柄のウェイトを比例的にスケーリングして合計 1.0 に正規化する。

$$
w_i^{\text{final}} = \frac{w_i^{\text{raw}}}{\sum_{j} w_j^{\text{raw}}}
$$

```python
# portfolio_builder.py L337-369
total = sum(h.weight for h in holdings)
return [
    PortfolioHolding(
        ticker=h.ticker,
        weight=h.weight / total,
        ...
    )
    for h in holdings
]
```

---

## 5. 実データでの検証

### 5.1 30-stock ポートフォリオ

**実際の出力**: `research/ca_strategy_poc/workspaces/full_run/output/portfolio_weights.csv`

| セクター | 銘柄数 | 合計ウェイト | 最大ウェイト銘柄 | 最小ウェイト銘柄 |
|---------|:------:|:----------:|:-:|:-:|
| Information Technology | 5 | 18.0% | AMS (3.70%) | SWKS (3.51%) |
| Health Care | 6 | 18.9% | CSL (3.25%) | ABBV (3.11%) |
| Consumer Staples | 5 | 16.3% | CCEP (3.41%) | CHD/CL (3.21%) |
| Consumer Discretionary | 4 | 13.0% | DIS (3.50%) | ITV (3.01%) |
| Financials | 4 | 13.0% | MHFI (3.58%) | HNR1 (3.02%) |
| Industrials | 3 | 10.2% | CPI (3.52%) | COL (3.37%) |
| Energy | 2 | 5.5% | ENB (2.82%) | SLB (2.71%) |
| Materials | 1 | 2.7% | DD (2.73%) | — |
| Utilities | 1 | 1.3% | PPL (1.27%) | — |
| Telecom Services | 1 | 0.9% | SCMN (0.92%) | — |
| **合計** | **32** | **100.0%** | | |

### 5.2 スコアウェイト vs 等ウェイトの差異

セクター内のスコアレンジが狭い（典型的に 0.60〜0.80）ため、スコア比例と等ウェイトの差は小さい。

**Consumer Discretionary セクター（30-stock）の例**:

| 銘柄 | スコア比例 | 等ウェイト（セクター内） | 差 |
|------|:-:|:-:|:-:|
| DIS | 3.50% | 3.25% | +0.25pp |
| ORLY | 3.29% | 3.25% | +0.04pp |
| AMZN | 3.23% | 3.25% | -0.02pp |
| ITV | 3.01% | 3.25% | -0.24pp |

最大差はわずか ±0.25pp。

### 5.3 ポートフォリオサイズ別比較

| ポートフォリオ | 銘柄数 | ウェイト最大 | ウェイト最小 | ウェイト標準偏差 |
|:-:|:-:|:-:|:-:|:-:|
| 30-stock | 32 | PPL (3.70%) | SCMN (0.92%) | 0.80% |
| 60-stock | 62 | ENB (1.94%) | SCMN (0.92%) | 0.22% |
| 90-stock | 91 | DD (1.38%) | SCMN (0.92%) | 0.12% |

銘柄数が増えると、個別銘柄のウェイト差が縮小し、より等ウェイトに近づく。

---

## 6. 等ウェイトポートフォリオ（代替方式）

### 6.1 コード参照

`PortfolioBuilder.build_equal_weight()` (L409-492)

### 6.2 アルゴリズム

1. `aggregate_score > threshold` の全銘柄を選択
2. 各銘柄に `1/N` の等ウェイトを付与
3. ベンチマークセクター制約は**適用しない**

```python
# portfolio_builder.py L446-460
selected = [s for s in ranked if s["aggregate_score"] > threshold]
n = len(selected)
equal_weight = 1.0 / n
```

### 6.3 スコアウェイトとの主な違い

| 観点 | スコアウェイト | 等ウェイト |
|------|:-:|:-:|
| セクター制約 | ベンチマーク追従 | なし |
| 銘柄内ウェイト | スコア比例 | 均等 |
| 銘柄数決定 | target_size（30/60/90） | threshold 超過全銘柄 |
| リバランス含意 | セクター配分維持 | 純粋な 1/N |

---

## 7. 設計上の特徴と留意点

### 7.1 スコアレンジの影響

現在のスコアリングでは aggregate_score が 0.55〜0.80 の狭い範囲に集中しているため、スコア比例ウェイトと等ウェイトの差が小さい。スコアリングの分散が大きくなれば、スコア比例ウェイトの効果が増す。

### 7.2 セクター中立化の非対称性

Z-score はランキングに使用されるが、ウェイト計算には影響しない。仮にセクター A のスコア分布が高く（全銘柄 0.8+）、セクター B が低い（全銘柄 0.5+）場合でも、ベンチマークウェイトに従いセクター配分は同一となる。

### 7.3 最大剰余法の特性

- **利点**: 合計がターゲット銘柄数に正確に一致
- **欠点**: Alabama Paradox（ターゲット銘柄数の増加でセクター割当が減る可能性）が理論的に存在するが、実用上は問題にならない

### 7.4 定数ウェイトの含意

Phase 6 のリターン計算（`return_calculator.py`）では定数ウェイトを使用しており、これは**日次リバランス**と等価である。実際の運用では日次リバランスのトランザクションコストが発生するが、バックテストではこれを考慮していない。

---

## 8. 関連ファイル

| ファイル | 説明 |
|---------|------|
| `src/dev/ca_strategy/aggregator.py` | Phase 2: スコア集約（ScoreAggregator） |
| `src/dev/ca_strategy/neutralizer.py` | Phase 3: セクター中立化（SectorNeutralizer） |
| `src/factor/core/normalizer.py` | ロバスト Z-score 実装（Normalizer） |
| `src/dev/ca_strategy/portfolio_builder.py` | Phase 4: ポートフォリオ構築（PortfolioBuilder） |
| `src/dev/ca_strategy/types.py` | 全データモデル定義 |
| `research/ca_strategy_poc/reports/calculation_methodology.md` | パフォーマンス指標の計算方法論 |
| `research/ca_strategy_poc/reports/performance_analysis_report.md` | パフォーマンス分析レポート |
| `research/ca_strategy_poc/workspaces/full_run/output/portfolio_weights.csv` | 30-stock 実出力 |
| `research/ca_strategy_poc/workspaces/full_run/output/portfolio_weights_60.csv` | 60-stock 実出力 |
| `research/ca_strategy_poc/workspaces/full_run/output/portfolio_weights_90.csv` | 90-stock 実出力 |
