# Plan: quant-computing スキル拡張

## Context

元の計画（`2026-03-02_quant-computing-skill.md`）は数値精度・ベクトル化・高速化・テストの4領域を扱う予定だった。
ヒアリングと既存コード調査の結果、以下のギャップが追加で判明した：

| ギャップ | 現状 | 必要なこと |
|---------|------|-----------|
| DB スキーマ設計 | 実装は散在（database/, market/edinet/）、判断基準なし | SQLite vs DuckDB 使い分け・MultiIndex 格納・マイグレーションパターンを文書化 |
| リターン計算の標準化 | 単純 pct_change() と CAGR 複利が混在、log/simple の使い分け未定義 | いつ log vs simple を使うかの決定ルール |
| リスクフリーレート | `calculator.py` のデフォルトが `0.0`、どの FRED シリーズを使うか未指定 | DFF（日次）/ DGS3MO（年率）の使い分けを明記 |
| バックテスト | メインコードベースにベクトル化バックテストなし | 前方参照バイアス防止を含む標準パターンを提供 |
| データパイプライン | Raw→Processed→Features の変換フロー、Universe 管理、品質チェックが未文書化 | パイプラインパターンと品質チェックルールを文書化 |

**目的**: `quant-computing` スキルをこれらすべてをカバーする包括的ナレッジベースに拡張する。

---

## 作成ファイル構成（元計画から拡張）

```
.claude/skills/quant-computing/
├── SKILL.md                          # 更新：拡張スコープ（9領域）
├── guide.md                          # 更新：DB・パイプライン・リターン標準を追加
└── examples/
    ├── vectorization.md              # 元計画どおり
    ├── numerical-precision.md        # 元計画どおり
    ├── performance.md                # 元計画どおり
    ├── testing.md                    # 元計画どおり
    ├── returns.md                    # NEW: リターン計算標準
    ├── risk-metrics.md               # NEW: リスク指標 + リスクフリーレート
    ├── backtesting.md                # NEW: ベクトル化バックテストパターン
    ├── db-schema.md                  # NEW: SQLite/DuckDB スキーマ設計
    └── data-pipeline.md              # NEW: パイプライン・Universe・品質チェック
```

加えて `CLAUDE.md` のスキル一覧を更新する。

---

## 各ファイルの内容設計

### SKILL.md（200行程度）

frontmatter 更新：
```yaml
---
name: quant-computing
description: |
  クオンツ計算・データ基盤実装のナレッジベース。数値精度・ベクトル化・
  高速化・テスト・リターン計算標準・リスク指標・バックテスト・
  DBスキーマ設計・データパイプラインを提供。
  Python で計算コードまたはDB設計を書く際にプロアクティブに使用。
allowed-tools: Read
---
```

**セクション構成**（元計画の7 → 更新版）：
1. 目的（9つの提供内容）
2. いつ使用するか（数値計算実装 / DB設計 / パイプライン設計時にプロアクティブ）
3. クイックリファレンス（最重要スニペット集、領域別）
4. リソース（全 examples への案内）
5. 使用例（5ケース：リターン計算・Sharpe比・バックテスト・DB設計・パイプライン）
6. 品質基準（MUST/SHOULD チェックリスト）
7. 関連スキル

---

### guide.md（350行程度）

元計画の6セクションを維持しつつ、以下を追加：

| 追加セクション | 内容 |
|--------------|------|
| DB 選択基準 | SQLite（永続・マイグレーション管理・OLTP相当）vs DuckDB（分析・upsert・Parquet連携）の判断表 |
| MultiIndex ↔ DB 変換 | `pd.MultiIndex` (date×symbol) をDB に格納・復元するパターン（UNIQUE制約+インデックス） |
| マイグレーション規約 | `YYYYMMDD_HHMMSS_description.sql` 命名、`schema_migrations` テーブルで管理、後方互換性ルール |
| リターン計算標準 | 単純リターン（ポートフォリオ評価）vs 対数リターン（数学的性質が必要な時）の使い分け表 |
| リスクフリーレート標準 | 日次 Sharpe: DFF（実効フェデラルファンドレート）÷252、年率比較: DGS3MO |

---

### examples/returns.md（200行程度）

既存コード（`analyze/returns/returns.py`, `factor/core/return_calculator.py`）から抽出：

```python
# ルール1: ポートフォリオリターンは単純リターン
returns = prices.pct_change(fill_method=None)  # fill_method=None で分割調整ギャップを保持

# ルール2: 累積リターンは複利
cumulative = (1 + returns).cumprod() - 1

# ルール3: 年率化は複利（近似の線形は禁止）
# BAD:  annualized = monthly_return * 12
# GOOD: annualized = (1 + monthly_return) ** 12 - 1

# ルール4: 対数リターンを使う場面（数学的特性が必要）
log_returns = np.log(prices / prices.shift(1))  # 多期間加法可能・正規性仮定

# ルール5: 前方参照バイアス防止（ファクター→リターンのラベル）
forward_returns = returns.shift(-period)  # 必ず shift(-n) でラベル作成
```

- CAGR 計算例（既存 `return_calculator.py` lines 420-425 を引用）
- MTD/YTD 動的期間の計算
- NaN 伝播ルール（最低データ数チェック）

---

### examples/risk-metrics.md（200行程度）

既存コード（`strategy/risk/calculator.py`）から抽出・補足：

```python
# リスクフリーレート：日次 Sharpe 計算
# DFF（FRED）= 実効フェデラルファンドレート、日次値を252で割る
# 年率比較には DGS3MO（3ヶ月Tbill）を使用

# ボラティリティ（既存コード line 151）
vol = returns.std() * np.sqrt(252)  # annualization_factor=252 固定

# Sharpe（既存コード lines 186-209）
daily_rf = risk_free_rate / 252
excess = returns - daily_rf
sharpe = excess.mean() / excess.std() * np.sqrt(252)
# ゼロ除算: std < 1e-15 のとき inf/-inf を返す（既存挙動を踏襲）

# Max Drawdown（既存コード lines 404-407）
cum = (1 + returns).cumprod()
drawdown = (cum - cum.cummax()) / cum.cummax()
mdd = drawdown.min()  # 常に [-1, 0]

# VaR 選択基準
# 履歴 VaR: データ数 > 252（1年分）のとき
# パラメトリック VaR: データ数 < 252 または正規分布仮定が必要なとき
```

---

### examples/backtesting.md（250行程度）

**現状**: メインコードにベクトル化バックテストのループなし → 標準パターンを提供。

```python
# ベクトル化バックテストの標準パターン
# 前方参照バイアス防止: シグナルは当日 close 後に計算、翌日 open で執行
signals = compute_signals(prices)           # t 日の close で計算
positions = signals.shift(1)               # t+1 日の open で執行（必ず shift(1)）
returns = prices.pct_change(fill_method=None)
strategy_returns = (positions * returns).sum(axis=1)  # ポートフォリオリターン

# 取引コスト
turnover = positions.diff().abs().sum(axis=1)
net_returns = strategy_returns - turnover * cost_per_trade

# ウォークフォワード分割（学習・評価期間の分離）
from sklearn.model_selection import TimeSeriesSplit
tscv = TimeSeriesSplit(n_splits=5, gap=21)  # gap=21 で過学習防止
```

- ロングショートポートフォリオのポジション計算
- ポートフォリオウェイトの正規化（ウェイト合計=1）
- 取引コストモデル（一方向コスト）
- `src/dev/ca_strategy/` の TopN 実装を参照例として引用

---

### examples/db-schema.md（250行程度）

既存実装（`database/db/`, `market/edinet/storage.py`）から抽出：

```python
# SQLite 選択基準: 永続データ、マイグレーション管理が必要、OLTP相当
# DuckDB 選択基準: 分析クエリ、Parquetとの連携、upsert パターン、一時DB

# 時系列×銘柄の SQLite スキーマ（既存 initial_schema.sql を参照）
CREATE TABLE prices_daily (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    symbol TEXT NOT NULL REFERENCES assets(symbol),
    date  DATE  NOT NULL,
    close REAL,
    adj_close REAL,
    UNIQUE(symbol, date, source)  -- MultiIndex 制約
);
CREATE INDEX idx_prices_symbol_date ON prices_daily(symbol, date);

# DuckDB upsert パターン（既存 storage.py を参照）
client.store_df(
    df, "financials",
    if_exists="upsert",
    key_columns=["edinet_code", "fiscal_year"]
)

# MultiIndex DataFrame → DB 変換
# stack() → 長形式 → 格納
long_df = df.stack(level="symbol").reset_index()  # (date, symbol, value) 形式
# DB からの復元: pivot_table(index="date", columns="symbol", values="close")
```

- マイグレーションファイル命名規則（`YYYYMMDD_HHMMSS_description.sql`）
- `schema_migrations` テーブルによるバージョン管理
- DuckDB の型マッピング（Python ↔ DuckDB: VARCHAR/DOUBLE/BIGINT）

---

### examples/data-pipeline.md（250行程度）

既存実装（`market/yfinance/fetcher.py`, `market/cache/cache.py`, `database/parquet_schema.py`）から抽出：

```python
# Universe 定義（既存 ca_strategy/types.py を参照）
class UniverseTicker(BaseModel):
    ticker: NonEmptyStr
    gics_sector: NonEmptyStr

# 欠損値ルール
# 1. pct_change に fill_method=None（分割ギャップを保持）
# 2. ファクター計算前に dropna()（既存 pca.py, orthogonalization.py）
# 3. 最低データ数チェック（既存 returns.py lines 86-92）

# スキーマ検証（既存 parquet_schema.py）
validate_stock_price_dataframe(df)  # 必須: symbol, date, OHLCV

# Parquet メタデータ管理（既存パターン）
meta = {
    "symbol": "AAPL",
    "fetched_at": datetime.now().isoformat(),
    "row_count": len(df),
    "date_range": {"first": str(df.index.min()), "last": str(df.index.max())}
}
```

- per-ticker Parquet パターン（ファイル構造、メタデータ JSON）
- SQLite TTL キャッシュの使い方（1h デフォルト、24h 永続）
- Survivorship bias 防止：Universe JSON スナップショット
- 外れ値処理フロー（winsorize → robust z-score → sector-neutral）

---

## CLAUDE.md 更新内容

`スキル一覧 > コーディング・開発` テーブルに追加：

```markdown
| `quant-computing` | クオンツ計算・データ基盤ベストプラクティス（数値精度・ベクトル化・高速化・テスト・リターン標準・リスク指標・バックテスト・DBスキーマ・パイプライン） | プロアクティブ |
```

`Python実装時の必須サブエージェント` セクションのコード実装ルールに追記：
- クオンツ計算・DB設計・データパイプラインを書く際は `@.claude/skills/quant-computing/SKILL.md` を参照

---

## 実装方針

- 実装は `skill-creator` サブエージェントに委譲（`skill-expert` スキル参照）
- 各 examples ファイルは既存コードのパス・行番号を注釈として明記（「実装との乖離防止」）
- `coding-standards` スキルとの重複は避ける（一般規約はそちら参照）
- スキルはプロアクティブ使用前提：クイックリファレンスを簡潔に保つ

---

## 検証方法

1. ファイル存在確認（9ファイル）
2. frontmatter の `name: quant-computing` / `allowed-tools: Read` を確認
3. 既存コードとの整合性
   - `strategy/risk/calculator.py` のリスクフリーレートデフォルト `0.0` と risk-metrics.md の説明が一致
   - `factor/core/normalizer.py` の MAD スケール `1.4826` が numerical-precision.md に記載
   - `database/db/migrations/runner.py` のマイグレーション方式が db-schema.md と一致
4. CLAUDE.md のリンクが正しく更新されていること
