# Phase 6 設計課題整理（CA Strategy パフォーマンス評価）

> 作成日: 2026-02-24
> 目的: Phase 6（StrategyEvaluator）の完全実装に向けて、議論・決定が必要な設計課題を網羅する

---

## 現状の確認

| 項目 | 現状 |
|------|------|
| `evaluator.py` | 実装済みだが `portfolio_returns` / `benchmark_returns` に空 Series を渡している |
| `orchestrator.py:423` | `AIDEV-NOTE: yfinance fetching is out of scope here` と明示 |
| Phase 6 の出力 | `sharpe_ratio=NaN`, `max_drawdown=0.0`, `beta=NaN` が常に返る（評価できていない） |
| `analyst_scores` | 空 dict で渡しているため相関分析も未実施 |

---

## 設計課題一覧

### 課題 A: 評価期間の設定 ✅ 決定済み

| 項目 | 値 |
|------|---|
| ユニバース構築日 | 2015-12-24 |
| ポートフォリオ構築基準日（PoiT） | 2015-09-30 |
| 評価開始 | 2015-10-01 |
| **評価終了** | **2026-02-28（現在）** |
| 評価期間 | 約 10.4 年 |

**目的**: CA スコアの長期予測力検証（競争優位性が株価リターンに反映されるまでの期間を十分にカバー）

**影響**: 8社すべての消失銘柄が評価期間内に収まる → 課題 C（消失企業処理）の設計が重要になる

---

### 課題 B: ベンチマークの選択 ✅ 決定済み

**決定**: **ユニバース内全395銘柄の等ウェイトポートフォリオ**をベンチマークとする

**理由**:
- 外部指数不要・追加データ取得コストなし
- 消失銘柄の処理ルールが CA ポートフォリオと完全同一（比較が公平）
- 「CA スコアによる銘柄選択がユニバース内平均に対して超過リターンを生むか」を直接検証できる
- マーケットキャップウェイトとイコールウェイトの差異ノイズを除去

**ベンチマーク構築**:
- 開始: 2015-12-31 に全395銘柄を均等ウェイト（1/395 ≒ 0.253%）で保有開始
- 消失銘柄の処理: CA ポートフォリオと同一（上場廃止時にウェイト0%→残存銘柄へ比例再配分）
- 配当: Total Return ベース（同上）

---

### 課題 C: 消失企業の取り扱い ✅ 決定済み

**ユニバース内の消失銘柄（8社）**:

| ティッカー | 企業名 | 消失事由 | 消失年月 |
|-----------|-------|---------|---------|
| ALTR | Altera | Intel 買収 | 2015-12 |
| ARM | ARM Holdings | Softbank 買収（市場撤退） | 2016-09 |
| EMC | EMC Corporation | Dell に統合 | 2016-09 |
| MON | Monsanto | Bayer 買収 | 2018-06 |
| CA | CA Technologies | Broadcom 買収 | 2018-11 |
| LIN | Praxair | Linde と合併 | 2018-10 |
| UTX | United Technologies | Raytheon と合併→RTX | 2020-04 |
| S | Sprint | T-Mobile に統合 | 2020-04 |

**決定した取り扱い方針**:
- 上場廃止時点でその銘柄のウェイトを **0%** に設定
- 解放されたウェイト分を、**残存銘柄のウェイト比率を維持しながら** 比例配分で再配分（トータル常に 100%）
- 最終価格は使用するデータソース（Bloomberg / FactSet / yfinance）の最終利用可能価格をそのまま使用

**注意**: データソース上でデータが終了しても、それ自体は企業消失とは判定しない。消失判定は**コーポレートアクション情報**（実際の上場廃止日・買収完了日）に基づく。

**実装要件**:
- コーポレートアクションの日付情報を保持する設定ファイルが必要
- データソースは抽象化し、Bloomberg/FactSet/yfinance を差し替え可能な設計とする

---

### 課題 D: 国際ティッカーの識別子設計 ✅ 決定済み

**問題**: `universe.json` は Bloomberg ベースティッカーのみ（取引所コードが失われている）。

```
原始データ: "ADN LN Equity"   → generate_config.py で分割
universe.json: "ADN"           ← LN (= London) が失われ、データ取得に使えない
```

**決定した設計**:

1. **`universe.json` に `bloomberg_ticker` フィールドを追加**
   - 既存の `ticker` フィールド（"ADN"）はトランスクリプトディレクトリ名として維持
   - 追加する `bloomberg_ticker` フィールド（"ADN LN Equity"）をデータ取得用識別子として使用
   - `generate_config.py` を修正し元データの `Bloomberg_Ticker` をそのまま保存

2. **データソース抽象化層（`PriceDataProvider` プロトコル）を先に実装**
   - 具体的なデータソース（yfinance/Bloomberg/FactSet）の実装は後回し
   - インターフェースだけ定義し、Phase 6 はこのプロトコルに依存
   - `bloomberg_ticker` を渡せば日次 Total Return 系列を返す、という契約を定義

**ファイル変更**:
- `src/dev/ca_strategy/types.py`: `UniverseTicker` に `bloomberg_ticker: str` フィールド追加
- `src/dev/ca_strategy/generate_config.py`: `_write_universe()` で `bloomberg_ticker` を保存するよう修正
- `research/ca_strategy_poc/config/universe.json`: 再生成が必要
- `src/dev/ca_strategy/price_provider.py`（新規）: `PriceDataProvider` プロトコル定義

---

### 課題 E: ポートフォリオリターンの計算方式 ✅ 決定済み（一部）

**ポートフォリオ開始日**: **2015-12-31**（ユニバース 2015-12-24 に基づきポートフォリオを保有開始）
- **注意**: PoiT（スコアリング基準日）は 2015-09-30 のまま。データの切り口と保有開始日は別概念。

**リバランス方針**: コーポレートアクション発生時のみ（イベント駆動）
- 通常期間は保有継続（Buy & Hold に相当）
- 上場廃止・買収完了時にウェイトを 0% に設定し、残存銘柄へ比例再配分
- 定期的なウェイト均等化（月次・年次リバランス）は**行わない**

**リターン計算**: **プライスリターン**（配当除く）
- データソースの終値（close price）の日次変化率を使用
- yfinance であれば `Close`（非調整）または `Adj Close`（分割調整済み・配当除く）が対応する

**リバランス**: コーポレートアクション発生時のみ（定期リバランスなし）

---

### 課題 F: データ欠損・フォールバック ✅ 設計確定

- データ取得に失敗した銘柄は警告ログを出力し、ポートフォリオ（およびベンチマーク）から除外
- 除外された銘柄の一覧・理由は出力ファイルに記録
- 消失企業はコーポレートアクション設定ファイルで管理（データ終了≠消失）

---

### 課題 G: アナリストスコアとの相関

Phase 6 PoC では `analyst_scores={}` のまま（相関メトリクスは `None`）。将来拡張の余地として保留。

---

### 課題 H: 実装スコープ ✅ 決定済み

- **PriceDataProvider 抽象層のみ実装**し、具体的なデータソース（yfinance/Bloomberg）は後から差し込む
- Phase 6 として Sharpe, MaxDD, IR, Beta, CumReturn を実際の値で出力
- アナリスト相関は `analyst_scores={}` のまま（Phase 6 PoC 対象外）

---

---

## 実装プラン

### 設計方針サマリー

| 項目 | 決定内容 |
|------|---------|
| 評価期間 | 2015-12-31 〜 2026-02-28（約10.4年） |
| ベンチマーク | ユニバース全395銘柄の等ウェイトポートフォリオ |
| 消失企業処理 | 上場廃止日にウェイト0%→残存比例再配分（コーポレートアクション設定ファイルで管理） |
| リバランス | イベント駆動のみ（上場廃止時のみ） |
| 配当 | **プライスリターン**（配当除く） |
| データソース | 抽象層のみ実装（PriceDataProvider Protocol） |
| アナリスト相関 | analyst_scores={} のまま（Phase 6 PoC 対象外） |

### アーキテクチャ

```
Orchestrator
├── Phase 1-5（変更なし）
└── Phase 6（新実装）
    ├── PortfolioReturnCalculator (NEW)
    │   ├── PriceDataProvider Protocol (NEW) ← 具体実装は後から差し込み
    │   └── corporate_actions.json (NEW data file)
    └── StrategyEvaluator (既存・API 変更なし)
```

### 新規定数（pit.py に追加）

```python
CUTOFF_DATE: date = date(2015, 9, 30)       # PoiT（CA スコアリング基準日）← 既存
PORTFOLIO_DATE: date = date(2015, 12, 31)   # ポートフォリオ保有開始日（新規）
EVALUATION_END_DATE: date = date(2026, 2, 28)  # 評価終了日（新規）
```

### リターン計算アルゴリズム

CA ポートフォリオ・ベンチマーク共通:
1. 初期ウェイト辞書 `{ticker: weight}` を設定（開始日 PORTFOLIO_DATE）
2. 各営業日 T について:
   - `corporate_actions.json` を確認 → 本日上場廃止の銘柄があればウェイトを 0 に設定し、解放分を残存銘柄へ比例再配分
   - 日次リターン = `Σ(weight[t] × daily_return[t])` で加重平均
3. `pd.Series`（日次リターン系列）を返す

### 変更ファイル一覧

#### 新規作成

| ファイル | 内容 |
|---------|------|
| `src/dev/ca_strategy/price_provider.py` | `PriceDataProvider` Protocol 定義（`fetch(tickers, start, end) -> dict[str, pd.Series]`） |
| `src/dev/ca_strategy/return_calculator.py` | `PortfolioReturnCalculator`（上記アルゴリズム実装） |
| `research/ca_strategy_poc/config/corporate_actions.json` | 8社のコーポレートアクション情報（ticker, action_date, action_type） |

#### 修正

| ファイル | 変更内容 |
|---------|---------|
| `src/dev/ca_strategy/pit.py` | `PORTFOLIO_DATE`・`EVALUATION_END_DATE` 定数を追加 |
| `src/dev/ca_strategy/types.py` | `UniverseTicker` に `bloomberg_ticker: str` フィールドを追加 |
| `src/dev/ca_strategy/generate_config.py` | `_write_universe()` で `bloomberg_ticker` を保存するよう修正 |
| `src/dev/ca_strategy/orchestrator.py` | Phase 6 で `PortfolioReturnCalculator` を呼び出し、実際のリターン系列を `StrategyEvaluator` に渡す。`as_of_date=CUTOFF_DATE` → `as_of_date=PORTFOLIO_DATE` に修正 |
| `research/ca_strategy_poc/config/universe.json` | `generate_config.py` 修正後に再生成 |

### 出力ファイルの追加

`OutputGenerator` は既存の `evaluation` optional パラメータをすでに処理しているため変更不要。Phase 6 の実値が入ることで以下が有効化:
- `evaluation_summary.json`: Sharpe, MaxDD, IR, Beta, CumReturn の実値
- `evaluation_results.json`: 閾値別評価結果

### 検証方法

```bash
# 1. generate_config を再実行して universe.json に bloomberg_ticker を追加
uv run python -m dev.ca_strategy.generate_config \
  --source data/Transcript/list_portfolio_20151224.json \
  --output-dir research/ca_strategy_poc/config

# 2. Orchestrator の run_equal_weight_pipeline() を実行
#    （Phase 6 が実値を返すことを確認）

# 3. 出力確認
cat research/ca_strategy_poc/workspaces/*/output/threshold_0.50/evaluation_summary.json
# → sharpe_ratio が NaN でないこと
# → benchmark_cumulative_return と portfolio_cumulative_return が出力されること

# 4. テスト
uv run pytest tests/dev/ca_strategy/ -v -k "phase6 or return_calculator or price_provider"
```
