# generate-market-report スクリプト不整合修正計画

## Context

`/generate-market-report --weekly` の Phase 2（市場データ収集）で使用する Python スクリプトが、下流の `wr-data-aggregator` エージェントが期待するデータ形式と不整合を起こしている。具体的には以下の5つの問題がある:

1. **SKILL.md とコマンド定義の矛盾**: SKILL.md は `collect_market_performance.py` を参照、コマンドは `weekly_comment_data.py` を使用
2. **フィールド名の不一致**: スクリプトは `latest_close` を出力、wr-data-aggregator は `price` を期待
3. **フィールドの欠損**: `ytd_return`, `change`, `market_cap`, `weight`, `top_holdings` が未出力
4. **リターン値の単位不統一**: `PerformanceAnalyzer4Agent` はパーセント形式（2.5 = 2.5%）、wr-data-aggregator は小数形式（0.025）を期待
5. **金利・為替・イベントデータの未統合**: `interest_rates.json`, `currencies.json`, `upcoming_events.json` がPhase 2で未生成

## 方針: 新規スクリプト `collect_weekly_report_data.py` の作成

既存の2スクリプトを修正するのではなく、新規スクリプトを作成する。

- `weekly_comment_data.py` → `--weekly-comment` モード専用として温存
- `collect_market_performance.py` → 汎用データ収集用として温存
- **新規** `collect_weekly_report_data.py` → `--weekly` モード専用、wr-data-aggregator 互換出力

**理由**: 既存スクリプトの責務を変えず、`wr-data-aggregator` の期待に完全適合する専用スクリプトを用意する方がリスクが低い。

---

## Step 1: `scripts/collect_weekly_report_data.py` 新規作成

### データソース

| カテゴリ | ソースクラス | メソッド | 取得先 |
|---------|------------|---------|-------|
| indices | `PerformanceAnalyzer` | `get_group_performance_with_prices("indices", "us")` | `analyze.reporting.performance` |
| mag7 | `PerformanceAnalyzer` | `get_group_performance_with_prices("mag7")` | 同上 |
| sectors | `PerformanceAnalyzer` | `get_group_performance_with_prices("sectors")` | 同上 |
| interest_rates | `InterestRateAnalyzer4Agent` | `get_interest_rate_data()` | `analyze.reporting.interest_rate_agent` |
| currencies | `CurrencyAnalyzer4Agent` | `get_currency_performance()` | `analyze.reporting.currency_agent` |
| upcoming_events | `UpcomingEvents4Agent` | `get_upcoming_events()` | `analyze.reporting.upcoming_events_agent` |

名前マッピング: `analyze.config.loader.get_symbol_group()` → `[{"symbol": "AAPL", "name": "Apple"}, ...]`

### アダプター関数

`PerformanceAnalyzer.get_group_performance_with_prices()` → `(returns_df, price_df)` を受け取り変換:

```python
def adapt_to_indices(returns_df, price_df, start_date, end_date) -> dict:
    # returns_df: columns [symbol, period, return_pct] ※ return_pct はパーセント形式
    # price_df: columns [Date, symbol, variable, value]
    # → weekly_return = return_pct["1W"] / 100  (小数形式に変換)
    # → ytd_return = return_pct["YTD"] / 100
    # → price = price_df の各 symbol の最新 Close 値
    # → change = price * (return_pct["1D"] / 100)
```

### 出力ファイル（固定名、タイムスタンプなし）

```
{output_dir}/
├── indices.json          # wr-data-aggregator 互換
├── mag7.json             # wr-data-aggregator 互換
├── sectors.json          # wr-data-aggregator 互換
├── interest_rates.json   # 金利データ（新規追加）
├── currencies.json       # 為替データ（新規追加）
├── upcoming_events.json  # イベントデータ（新規追加）
└── metadata.json         # 期間・生成情報
```

### 出力スキーマ（wr-data-aggregator 互換）

**indices.json**:
```json
{
  "as_of": "2026-01-21",
  "period": {"start": "2026-01-14", "end": "2026-01-21"},
  "indices": [
    {"ticker": "^GSPC", "name": "S&P 500", "weekly_return": 0.025, "ytd_return": 0.032, "price": 6012.45, "change": 15.03}
  ],
  "data_freshness": {"has_date_gap": false, "newest_date": "2026-01-21"}
}
```

**mag7.json**:
```json
{
  "as_of": "2026-01-21",
  "period": {"start": "2026-01-14", "end": "2026-01-21"},
  "mag7": [
    {"ticker": "AAPL", "name": "Apple", "weekly_return": 0.015, "ytd_return": 0.022, "price": 245.50, "change": 1.47}
  ],
  "sox": {"ticker": "^SOX", "name": "Philadelphia Semiconductor Index", "weekly_return": 0.031, "price": 5250.30}
}
```

**sectors.json**:
```json
{
  "as_of": "2026-01-21",
  "period": {"start": "2026-01-14", "end": "2026-01-21"},
  "top_sectors": [{"ticker": "XLK", "name": "Information Technology", "weekly_return": 0.025}],
  "bottom_sectors": [{"ticker": "XLV", "name": "Healthcare", "weekly_return": -0.029}],
  "all_sectors": [...]
}
```

### CLI インターフェース

```bash
uv run python scripts/collect_weekly_report_data.py \
    --start 2026-01-14 \
    --end 2026-01-21 \
    --output articles/weekly_report/2026-01-21/data
```

引数は `weekly_comment_data.py` と互換（`--start`, `--end`, `--date`, `--output`）。

### 主要関数

```python
# アダプター（PerformanceAnalyzer → wr-data-aggregator 互換形式）
def adapt_to_indices(returns_df, price_df, name_map, start_date, end_date) -> dict
def adapt_to_mag7(returns_df, price_df, name_map, start_date, end_date) -> dict
def adapt_to_sectors(returns_df, price_df, name_map, start_date, end_date) -> dict

# 金利・為替・イベント（4Agent の to_dict() をそのまま利用可能）
def collect_interest_rates(output_dir) -> dict | None
def collect_currencies(output_dir) -> dict | None
def collect_upcoming_events(output_dir) -> dict | None

# オーケストレーション
def collect_all_data(output_dir, start_date, end_date) -> dict[str, bool]

# CLI
def create_parser() -> ArgumentParser
def main() -> int
```

### 重要な変換ルール

| 変換 | 説明 |
|------|------|
| `return_pct / 100` | パーセント → 小数（例: 2.5 → 0.025） |
| `latest_close` → `price` | フィールド名変更 |
| `price * (1D_return / 100)` | `change`の算出 |
| `get_symbol_group()` | ticker → name マッピング |
| MAG7 ソート | `weekly_return` 降順 |
| Sector Top/Bottom | `weekly_return` 降順でスライス |

### 参照すべき既存コード

| ファイル | 参照箇所 |
|---------|---------|
| `src/analyze/reporting/performance.py:325-374` | `get_group_performance_with_prices()` の戻り値構造 |
| `src/analyze/reporting/performance_agent.py:93-187` | `_convert_to_result()` のアダプターパターン |
| `src/analyze/config/loader.py:102-126` | `get_symbol_group()` による名前マッピング |
| `scripts/weekly_comment_data.py` | CLI構造・エラーハンドリングのパターン |

---

## Step 2: テスト作成

`tests/scripts/unit/test_collect_weekly_report_data.py`

- `TestAdaptToIndices`: returns_df + price_df をモックし、出力スキーマを検証
- `TestAdaptToMag7`: MAG7 + SOX のアダプター検証
- `TestAdaptToSectors`: Top/Bottom ソートの検証
- `TestReturnConversion`: パーセント→小数変換の正確性
- `TestCreateParser`: CLI 引数パース

---

## Step 3: コマンド定義の更新

**ファイル**: `.claude/commands/generate-market-report.md`

**変更箇所**: Phase 2（714行目付近）

```diff
- uv run python scripts/weekly_comment_data.py \
+ uv run python scripts/collect_weekly_report_data.py \
      --start ${START_DATE} \
      --end ${END_DATE} \
      --output "${OUTPUT_DIR}/data"
```

Phase 2 の出力ファイル例（722-770行目）に以下を追加:
- `interest_rates.json`, `currencies.json`, `upcoming_events.json`
- 各フィールドの `ytd_return`, `change` を追記

---

## Step 4: SKILL.md の更新

**ファイル**: `.claude/skills/generate-market-report/SKILL.md`

Phase 2 の記述をコマンド定義と一致させる:

```
Phase 2: 市場データ収集
├── collect_weekly_report_data.py → {output_dir}/data/
│   ├── indices.json（weekly_return, ytd_return, price, change）
│   ├── mag7.json（weekly_return, ytd_return, price）
│   ├── sectors.json（top_sectors, bottom_sectors, all_sectors）
│   ├── interest_rates.json（金利・イールドカーブ）
│   ├── currencies.json（為替パフォーマンス）
│   ├── upcoming_events.json（決算・経済指標）
│   └── metadata.json（期間・生成情報）
└── データ鮮度チェック（日付ズレ警告）
```

Python スクリプトセクションも更新:
```
| scripts/collect_weekly_report_data.py | --weekly モード用データ収集 |
```

Phase 3（仮説生成）と Phase 4（news_with_context.json）の記述は「将来計画」として注記を追加。

---

## Step 5: wr-data-aggregator.md の更新（任意）

入力ファイル一覧に `interest_rates.json`, `currencies.json`, `upcoming_events.json` を追加。
これにより `aggregated_data.json` の `interest_rates` / `forex` セクションがデフォルト値ではなく実データで埋まる。

---

## 検証方法

### 1. スクリプト単体実行
```bash
uv run python scripts/collect_weekly_report_data.py \
    --start 2026-02-23 --end 2026-03-02 \
    --output .tmp/test-weekly-report/data
```
→ `indices.json`, `mag7.json`, `sectors.json` 等が生成されることを確認

### 2. テスト実行
```bash
uv run pytest tests/scripts/unit/test_collect_weekly_report_data.py -v
```

### 3. wr-data-aggregator との結合確認
生成された JSON を `wr-data-aggregator` の期待スキーマと目視比較:
- `indices.json` に `weekly_return`（小数形式）, `ytd_return`, `price`, `change` が存在
- `mag7.json` に `mag7` 配列 + `sox` オブジェクト
- `sectors.json` に `top_sectors`, `bottom_sectors`, `all_sectors`

### 4. 品質チェック
```bash
make check-all
```
