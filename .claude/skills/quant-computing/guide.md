# Quantitative Computing 詳細ガイド

このガイドでは、SKILL.md のクイックリファレンスを補完する設計判断基準と詳細パターンを説明します。
全 13 セクション（セクション 1-11: 基盤領域、セクション 12-13: SKILL.md の9領域を補完）。

## 1. 数値精度

### epsilon 閾値の設計

| 閾値 | 用途 | 根拠 |
|------|------|------|
| `1e-15` (`_EPSILON`) | 標準偏差・分散のゼロ近傍判定 | IEEE 754 float64 マシンイプシロン (2.22e-16) の約 4.5 倍 |
| `1e-10` | ウェイト合計の 1.0 乖離判定 | 30 銘柄の累積丸め誤差 O(n * epsilon) を許容 |

```python
_EPSILON = 1e-15  # Threshold for considering standard deviation as effectively zero

# ゼロ除算防止: 分母がゼロ近傍の場合
if std < _EPSILON:
    if mean_excess > _EPSILON:
        return float("inf")
    elif mean_excess < -_EPSILON:
        return float("-inf")
    else:
        return float("nan")
```

> **参照**: `src/strategy/risk/calculator.py` line 20

### 浮動小数点比較の禁止と代替

```python
# NG: 直接比較
if result == 0.0: ...

# OK: epsilon 比較（本番コード）
if abs(result) < _EPSILON: ...

# OK: pytest.approx（テストコード）
assert result == pytest.approx(expected, rel=1e-6)
```

### dtype 選択基準

金融計算では **float64 をデフォルト** とする。float32 は有効桁数 6-7 桁で Sharpe 比の日次平均（1e-4 オーダー）計算に不足する。空の Series は `pd.Series(dtype=float)` で dtype を明示すること。

> **詳細パターン**: `examples/numerical-precision.md`

---

## 2. ベクトル化

### 変換の優先順位

| 優先度 | パターン | 例 |
|--------|----------|-----|
| 1 | ビルトインメソッド | `pct_change()`, `cumprod()`, `clip()` |
| 2 | `np.where` / `np.select` | 条件分岐のベクトル化 |
| 3 | `groupby().transform()` | グループ内正規化・ランク |
| 4 | DataFrame 要素積 + `sum(axis=1)` | ポートフォリオ加重リターン |
| 5 | `apply(axis=0)` | 列数が少ない場合のみ許容 |

### apply() 回避の判断基準

| 入力 | 推奨 | 理由 |
|------|------|------|
| `pd.Series` | `clip()` / `quantile()` 等のビルトイン | C 実装で高速 |
| `pd.DataFrame`（少数列） | `apply()` 許容 | 列数が少なければオーバーヘッド軽微 |
| `pd.DataFrame`（多数列） | `stack()` → Series 処理 → `unstack()` | apply のループコスト削減 |

### パフォーマンス目安（100万行、単一列）

| パターン | 実行時間 |
|----------|---------|
| Python ループ (`for i in range`) | ~5,000ms |
| `apply(axis=1)` | ~3,000ms |
| `groupby().transform()` | ~100ms |
| ベクトル演算 (`pct_change`) | ~10ms |

変換前後で必ず `profile_context` による計測を実施すること。

> **詳細パターン**: `examples/vectorization.md`

---

## 3. 高速化

### ボトルネック判定フロー

```
計測結果のボトルネックは何か？
├── API 呼び出し待ち > 80% → asyncio.gather() + Semaphore
├── ディスク I/O > 50%     → キャッシュ（TTL 付き）/ バッチ挿入
├── 計算処理 > 50%         → ベクトル化 / ProcessPool
└── メモリ使用量が過大     → Parquet 分割 / ジェネレータ
```

**原則**: 推測で最適化しない。`profile_context` / `@profile` で計測してからボトルネックを特定する。

### リトライ設定の標準

```python
DEFAULT_RETRY_CONFIG = RetryConfig(
    max_attempts=3,       # 一時的エラーは 2-3 回で回復
    initial_delay=1.0,    # Yahoo Finance レート制限の最小待機
    max_delay=30.0,       # ユーザー体感を損なわない上限
    exponential_base=2.0, # 1s → 2s → 4s
    jitter=True,          # thundering herd 回避
)
```

### asyncio セマフォの同時実行数

| 対象 | 推奨値 | 根拠 |
|------|--------|------|
| 外部 API（Yahoo Finance 等） | 3-5 | レート制限回避 |
| ニュースサイト | 5-10 | サーバー負荷配慮 |
| ローカルファイル | 10-20 | ファイルディスクリプタ制限 |

> **詳細パターン**: `examples/performance.md`

---

## 4. テスト

### 許容誤差の設計指針

| 許容誤差 | 用途 | 根拠 |
|----------|------|------|
| `rel_tol=1e-9` | 数学的に等しいはずの値（シフト不変性） | float64 有効桁数 15-16 桁 |
| `rel_tol=1e-5` | スケーリング比率の検証 | 累積演算の丸め誤差許容 |
| `rel_tol=1e-4` | モメンタム・リターン計算 | 入力データの丸め誤差 |
| `rel=0.01` | 概算値・統計推定量 | 推定誤差を含む |
| `atol=1e-10` | ゼロ近傍の絶対比較 | 正規化後の平均値 |

### Hypothesis ストラテジー設計

金融データの現実的な範囲に制限し、NaN/Infinity はストラテジーレベルで除外する。

```python
# 日次リターン: -50% 〜 +50%（S&P500 日次最大変動は約 +-12%）
st.floats(min_value=-0.5, max_value=0.5, allow_nan=False, allow_infinity=False)

# リスクフリーレート: 0% 〜 10%
st.floats(min_value=0.0, max_value=0.1, allow_nan=False)

# リストサイズ: 統計量の安定性に 20 件以上が必要
min_size=20, max_size=200
```

### assume() の推奨ケース

| 状況 | assume の内容 |
|------|-------------|
| 全値が同一 | `assume(float(series.std()) > _EPSILON)` |
| 負のリターンなし | `assume(any(r < 0 for r in returns))` |
| 微小な変化 | `assume(abs(end - start) > 0.01)` |

### プロパティベーステストの不変条件

| 性質 | 検証対象 | 例 |
|------|----------|-----|
| 非負性 | ボラティリティ | `assert vol >= 0` |
| スケーリング | `sigma(kX) = \|k\| * sigma(X)` | `math.isclose(ratio, abs(k), rel_tol=1e-5)` |
| シフト不変 | `sigma(X + c) = sigma(X)` | `math.isclose(vol_orig, vol_shifted, rel_tol=1e-9)` |
| 範囲制約 | MDD | `assert -1.0 <= mdd <= 0.0` |
| 単調性 | VaR | `assert var_99 <= var_95 + 1e-10` |

> **詳細パターン**: `examples/testing.md`

---

## 5. 並列処理

### I/O バウンド vs CPU バウンドの選択

| ボトルネック | 手法 | 例 |
|------------|------|-----|
| I/O バウンド（ネットワーク） | `asyncio.gather()` + Semaphore | 複数 API の並列呼び出し |
| I/O バウンド（ファイル） | `ThreadPoolExecutor` | ファイル読み書き |
| CPU バウンド（ベクトル化不可） | `ProcessPoolExecutor` | 大規模行列演算 |
| CPU バウンド（ベクトル化可） | pandas/NumPy ベクトル演算 | `groupby().transform()` |

### asyncio.gather() パターン

```python
async def fetch_batch(articles: list[Article], concurrency: int = 5) -> list[Result]:
    semaphore = asyncio.Semaphore(concurrency)

    async def fetch_one(article: Article) -> Result:
        async with semaphore:
            return await self.fetch(article)

    return list(await asyncio.gather(*[fetch_one(a) for a in articles]))
```

`return_exceptions=True` を指定すると、1 つの失敗で全体を止めない。

### チャンク処理パターン

大量リクエストを `chunk_size` 単位に分割し、各チャンクにリトライを適用する。障害をチャンク単位に局所化し、`chunk_size <= 0` は `ValueError` を送出する。

> **詳細パターン**: `examples/performance.md` セクション 2, 4

---

## 6. プロファイリング

### 手法の選択基準

| 手法 | オーバーヘッド | 推奨場面 |
|------|-------------|---------|
| `@profile` | 高（cProfile） | ボトルネック特定 |
| `@timeit` | 低（perf_counter のみ） | 定常計測・ログ出力 |
| `profile_context` | 中 | 改善前後の比較 |
| `compare_performance` | 中 | 複数手法の相対比較 |

### 改善前後の比較パターン

```python
with profile_context(print_stats=False) as prof_before:
    result_loop = calculate_with_loop(df)

with profile_context(print_stats=False) as prof_after:
    result_vec = calculate_with_vectorization(df)

improvement = (1 - prof_after.elapsed_time / prof_before.elapsed_time) * 100
logger.info("改善率", improvement_pct=f"{improvement:.1f}%")
```

> **詳細パターン**: `examples/performance.md` セクション 1

---

## 7. DB 選択基準

### SQLite vs DuckDB 判断表

| 基準 | SQLite | DuckDB |
|------|--------|--------|
| **データ量** | < 10 万行 | > 100 万行 |
| **クエリパターン** | CRUD（行単位の読み書き） | OLAP（集計・分析クエリ） |
| **主な用途** | メタデータ、設定、フェッチ履歴、マイグレーション管理 | 時系列データ分析、財務データ分析 |
| **Parquet 連携** | 非対応 | `SELECT * FROM 'file.parquet'` で直接読込 |
| **トランザクション** | ACID 完全対応、行ロック | 読み取り中心、並行書込みに制限あり |
| **ファイル拡張子** | `.db` | `.duckdb` |
| **パス規約** | `data/sqlite/{name}.db` | `data/duckdb/{name}.duckdb` |

### プロジェクトでの使い分け実例

| パッケージ | DB | 理由 |
|------------|-----|------|
| `database.db.migrations` | SQLite | `schema_migrations` テーブルで適用済みマイグレーション管理 |
| `database.db` の `prices_daily` | SQLite | 日次価格の CRUD |
| `market.edinet` | DuckDB | 8 テーブルの財務データ分析、集計クエリが中心 |

### DuckDB upsert パターン

DuckDB には `INSERT ... ON CONFLICT` 構文がないため、DELETE + INSERT 方式で冪等な更新を実現する。`key_columns` が空の場合は `ValueError` を送出し、テーブル名・カラム名は `_IDENTIFIER_RE` でバリデーションすること（SQL インジェクション防止）。

> **詳細パターン**: `examples/db-schema.md`

---

## 8. MultiIndex → DB 変換

### 基本パターン

pandas の MultiIndex は DB カラムにならないため、`reset_index()` でフラット化して保存する。

```python
# MultiIndex → フラットカラム
df_flat = df.reset_index()

# DuckDB に upsert
client.store_df(df_flat, "prices_daily", if_exists="upsert", key_columns=["symbol", "date"])

# DB → MultiIndex（復元）
df_multi = client.query_df("SELECT * FROM prices_daily").set_index(["symbol", "date"])
```

### 複合キーの UNIQUE 制約

MultiIndex の各レベルをそのまま複合 UNIQUE 制約に変換する。SQLite は `UNIQUE(symbol, date, source)` 形式、DuckDB は `store_df()` の `key_columns` パラメータで指定する。

> **詳細パターン**: `examples/db-schema.md` セクション 3

---

## 9. マイグレーション規約

### 命名規則

```
YYYYMMDD_HHMMSS_description.sql
```

例: `20250111_000000_initial_schema.sql`

### ガイドライン

| ガイドライン | 説明 |
|-------------|------|
| 1 ファイル 1 操作 | 1 つのマイグレーションで 1 つの変更のみ |
| 冪等性 | `CREATE TABLE IF NOT EXISTS` / `CREATE INDEX IF NOT EXISTS` を使用 |
| ロールバック不要 | 前方のみ。問題があれば新しいマイグレーションで修正 |
| 命名は内容を表す | `add_sector_column` / `create_indicators_table` 等 |

### マイグレーション管理テーブル（SQLite）

```sql
CREATE TABLE IF NOT EXISTS schema_migrations (
    filename TEXT PRIMARY KEY,
    applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

未適用のマイグレーションをファイル名の辞書順で実行し、`schema_migrations` に記録する。

> **詳細パターン**: `examples/db-schema.md` セクション 5

---

## 10. リターン計算標準

### simple vs log リターンの使い分け表

| 用途 | simple | log | 理由 |
|------|--------|-----|------|
| 個別銘柄の期間リターン | 推奨 | - | 直感的で解釈しやすい |
| ポートフォリオの加重平均 | 推奨 | NG | `sum(w_i * r_i)` で正確に算出可能。log は加重平均に使えない |
| 短期（日次〜週次）分析 | 推奨 | - | log との差が微小 (< 0.01%) |
| MTD / YTD レポート | 推奨 | - | 投資家向けレポートの標準形式 |
| 時系列の累積（加法性必要） | - | 推奨 | `log(t0→t2) = log(t0→t1) + log(t1→t2)` |
| 連続複利モデル | - | 推奨 | ブラック・ショールズ等の理論モデル |

### 年率化は複利必須（単利禁止）

```python
# OK: 複利年率化（正しい）
annualized = (1 + cumulative_return) ** (252 / n_trading_days) - 1

# NG: 単利年率化（禁止 — 数学的に不正確）
annualized = cumulative_return * (252 / n_trading_days)  # 禁止
```

**乖離の実例**: 月次 5% リターンの場合、単利年率化は 60.0%、複利年率化は 79.59%（乖離 +19.59pp）。リターンが大きいほど、期間が長いほど乖離が拡大する。

### 累積リターンは複利

```python
# OK: 複利で累積
cumulative_return = (1 + daily_returns).prod() - 1

# NG: 単純加算は禁止（+10% と -10% は 0% ではなく -1%）
cumulative_return = daily_returns.sum()  # 禁止
```

> **詳細パターン**: `examples/returns.md`

---

## 11. リスクフリーレート標準

### DFF vs DGS3MO 使い分け

| FRED シリーズ | 名称 | 推奨用途 |
|-------------|------|----------|
| **DFF** | Federal Funds Effective Rate | 日次 Sharpe / Sortino 計算（`daily_rf = DFF / 252`） |
| **DGS3MO** | 3-Month Treasury Constant Maturity Rate | 年率ベースの比較（Treynor、年率超過リターン） |

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

### リスク指標の分類

| 指標 | リスクフリーレート | ベンチマーク | FRED シリーズ |
|------|------------------|-------------|-------------|
| Volatility | 不要 | 不要 | - |
| Sharpe | 必要 | 不要 | DFF |
| Sortino | 必要 | 不要 | DFF |
| MDD | 不要 | 不要 | - |
| VaR | 不要 | 不要 | - |
| Beta | 不要 | 必要 | - |
| Treynor | 必要 | 必要 | DGS3MO |
| Information Ratio | 不要 | 必要 | - |

### ゼロ除算防止の統一規約

全リスク指標で `_EPSILON = 1e-15` を適用し、分母がゼロ近傍の場合の戻り値は以下の規約に従う:

| 分母の状態 | 分子 > EPSILON | 分子 < -EPSILON | \|分子\| < EPSILON |
|-----------|---------------|----------------|-----------------|
| < EPSILON | `float("inf")` | `float("-inf")` | `float("nan")` |

この規約は Sharpe / Sortino / Treynor / Information Ratio の全てで一貫して適用される。

> **詳細パターン**: `examples/risk-metrics.md`

---

## 12. バックテスト

### 最重要ルール: `signals.shift(1)` 必須

当日 close で計算したシグナルは翌営業日の open で執行される。`shift(1)` を省略すると**前方参照バイアス**が発生する。

```python
# NG: 前方参照バイアス
positions = signals
portfolio_returns = (positions * daily_returns).sum(axis=1)

# OK: 1日シフトで翌日執行
positions = signals.shift(1)
portfolio_returns = (positions * daily_returns).sum(axis=1)
```

### 3種のバイアス防止策

| バイアス | 原因 | 防止策 |
|----------|------|--------|
| シグナル前方参照 | 当日 close で当日リターンを取る | `signals.shift(1)` |
| データ前方参照 | 未公表の決算データを使用 | `as_of_date <= rebalance_date`（PoiT 制約） |
| サバイバーシップ | 上場廃止銘柄を除外 | コーポレートアクション対応（ウェイト再配分） |

### ウォークフォワード分割の選択

| 基準 | Rolling Window | Expanding Window |
|------|---------------|-----------------|
| レジーム変化への適応 | 速い（古いデータを捨てる） | 遅い（全データを保持） |
| 統計的安定性 | 不安定（データが少ない） | 安定（データが多い） |
| **推奨場面** | **短期戦略、市場構造が変化** | **長期ファクター投資** |

### 取引コストの標準値

| 資産クラス | コスト (bps, 片道) |
|-----------|-------------------|
| 米国大型株 | 5-10 |
| 米国中型株 | 10-20 |
| 米国小型株 | 20-50 |

> **詳細パターン**: `examples/backtesting.md`

---

## 13. データパイプライン

### 3層データモデル

```
Raw（生データ）         → Processed（加工済み）      → Features（特徴量）
外部API応答そのまま       スキーマ検証済み             分析・モデル入力用
保存先: data/raw/        保存先: data/processed/      保存先: data/exports/
```

### 標準パイプライン: 取得→検証→変換→保存

| ステップ | 責務 | 失敗時の対応 |
|----------|------|-------------|
| **取得（Fetch）** | 外部APIからRawデータ取得 | リトライ（指数バックオフ） |
| **検証（Validate）** | スキーマ準拠を確認 | `ValidationError` 送出 |
| **変換（Transform）** | 型変換、欠損値処理、正規化 | ログ出力+部分結果返却 |
| **保存（Save）** | Parquet/DB に永続化 | リトライ後にエラー送出 |

### スキーマ検証の3段階

```
Step 1: 空チェック → Step 2: 必須カラムチェック → Step 3: 型チェック
```

各ステップで失敗時は `ValidationError` を送出し、欠落カラム名や型不一致の詳細を含める。

### 欠損値処理の3段階ルール

| Stage | 手法 | 適用理由 |
|-------|------|---------|
| 1 | セクター中央値 | 同セクター内で類似した特性を持つため最も精度が高い |
| 2 | 全体中央値 | セクター内に十分なデータがない場合のフォールバック |
| 3 | 中立値（0.5 or 0.0） | 全データが欠損している極端なケースの最終手段 |

### 外れ値処理の順序

```
winsorize（1st/99th パーセンタイル）→ robust z-score（MAD ベース）→ sector-neutral
```

この順序は必須。winsorize で極端値をクリップしてから正規化することで、外れ値の影響を段階的に除去する。

> **詳細パターン**: `examples/data-pipeline.md`
