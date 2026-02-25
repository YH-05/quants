# バックテストエンジン設計計画

## Context

金融分析ライブラリ（finance）にはリターン計算・リスク指標・ファクター分析・ポートフォリオ管理の部品が揃っているが、これらを統合してバックテストを実行するエンジンが存在しない。`dev/ca_strategy` の Evaluator は CA Strategy 専用であり、汎用性がない。

**目的**: 既存部品を最大限再利用しつつ、汎用バックテストエンジンを `src/backtest/` に新規作成する。

**設計方針**:
- Vectorized + Event-driven の両モード同時実装
- 全戦略タイプ対応（ファクター、CA Strategy、テクニカル、カスタム）
- PoiT（ルックアヘッドバイアス防止）をフレームワークレベルで強制（zipline 方式）
- **SOLID/DIP**: エンジンはデータソースに依存しない。呼び出し側が `BacktestData` を構築して注入
- 既存パッケージ（strategy, factor, analyze, dev/ca_strategy）との統合（market への依存なし）

---

## 設計の参考にしたライブラリ

| ライブラリ | 採用パターン |
|-----------|-------------|
| **vectorbt** | `Portfolio.from_signals()` — ベクトル化シグナル→ポートフォリオ変換 |
| **bt** | Algo Stack — 宣言的なアルゴリズム合成 `[RunMonthly(), SelectAll(), WeighEqually(), Rebalance()]` |
| **QuantConnect** | 5-Model Framework — Universe → Alpha → Portfolio → Risk → Execution の分離 |
| **zipline** | Pipeline API — ファクター計算 + 1日ラグ強制による PoiT 防止 |
| **QSTrader** | Signal → PositionSizer → RiskManager → Order パイプライン |

**ハイブリッドアプローチ**: 2024-2025年のコンセンサス。Vectorized でパラメータスクリーニング（高速）→ Event-driven で有望候補を精密検証（現実的な執行モデル）。

---

## パッケージ構造

```
src/backtest/
    __init__.py
    py.typed
    README.md
    errors.py                    # PitViolationError, InsufficientDataError 等
    types.py                     # BacktestConfig, Order, Fill, PortfolioSnapshot, BacktestResult

    core/
        __init__.py
        protocols.py             # DataFeed, Signal, WeightScheme, ExecutionModel プロトコル
        clock.py                 # SimulationClock — 時刻の唯一の権限
        universe.py              # Universe 定義とフィルタリング
        calendar.py              # TradingCalendar — 営業日計算

    data/
        __init__.py
        container.py             # BacktestData — 3層データコンテナ（呼び出し側が構築して注入）
        pit_guard.py             # PitGuard — PoiT 強制レイヤー（BacktestData のアクセスを時刻制限）

    signal/
        __init__.py
        base.py                  # SignalBase + SignalRegistry（factor.core.registry パターン）
        factor_signal.py         # FactorSignalAdapter: factor.core.Factor → Signal 変換
        technical_signal.py      # TechnicalSignalAdapter: analyze.technical → Signal 変換
        custom.py                # ユーザー定義シグナルのヘルパー

    strategy/
        __init__.py
        base.py                  # StrategyBase（compute_signals + compute_weights の2ステップ）
        rebalance.py             # RebalanceStrategy — 定期リバランス
        factor_strategy.py       # FactorStrategy — マルチファクター long/short or long-only
        technical_strategy.py    # TechnicalStrategy — テクニカルシグナルベース
        algo_stack.py            # AlgoStack — 宣言的アルゴリズム合成（bt 方式）

    execution/
        __init__.py
        order.py                 # Order, Fill モデル
        broker.py                # SimulatedBroker（スリッページ、手数料モデル）
        position.py              # Position トラッキング
        portfolio_state.py       # PortfolioState — holdings, cash, NAV の日次管理

    engine/
        __init__.py
        vectorized.py            # VectorizedEngine — 高速パラメータスイープ
        event_driven.py          # EventDrivenEngine — バーごとのシミュレーション
        runner.py                # BacktestRunner — 統一エントリーポイント

    evaluation/
        __init__.py
        metrics.py               # strategy.risk.calculator.RiskCalculator のラッパー
        report.py                # BacktestReport（Markdown, JSON, CSV 出力）
        walk_forward.py          # ウォークフォワード分析（ローリングウィンドウ）
        comparison.py            # 複数戦略の比較

    integration/
        __init__.py
        ca_strategy.py           # dev/ca_strategy PortfolioResult → バックテスト可能な戦略に変換
        factor_integration.py    # factor パッケージ Factor → Signal, MultiFactorStrategy
```

---

## コアクラス設計

### 1. SimulationClock (`core/clock.py`)

バックテスト中の「現在時刻」の唯一の権限。不変オブジェクトで、エンジンだけが `advance()` できる。

```python
class SimulationClock(BaseModel):
    model_config = ConfigDict(frozen=True)

    current_date: date
    start_date: date
    end_date: date
    trading_dates: tuple[date, ...]  # TradingCalendar から事前計算

    def advance(self) -> SimulationClock | None:
        """次の営業日の Clock を返す。終了なら None。"""
```

### 2. BacktestData (`data/container.py`)

**入力データの統一コンテナ**。呼び出し側が構築してエンジンに注入する。エンジンはデータソースの詳細を知らない（SOLID/DIP）。

```python
class BacktestData(BaseModel):
    """3層データコンテナ。

    Layer 1 (必須): close — 終値。全バックテストで必要。
    Layer 2 (任意): series — 任意の時系列データ（OHLV, ファクター値, 経済指標等）
    Layer 3 (任意): metadata — 銘柄ごとの静的属性（セクター, 時価総額等）
    """
    model_config = ConfigDict(frozen=True, arbitrary_types_allowed=True)

    # --- Layer 1: 必須 ---
    close: pd.DataFrame
    """終値。columns=ticker, index=datetime。全バックテストで必須。"""

    # --- Layer 2: 任意の時系列 ---
    series: dict[str, pd.DataFrame] = {}
    """任意の時系列データ。キー例: "open", "high", "low", "volume",
    "momentum_12m", "pb_ratio", "fed_funds_rate" 等。
    各 DataFrame は close と同じ index/columns 構造。"""

    # --- Layer 3: 任意の静的メタデータ ---
    metadata: dict[str, dict[str, Any]] = {}
    """銘柄ごとの静的属性。
    例: {"AAPL": {"sector": "Technology", "market_cap": 3e12}, ...}"""

    # --- オプション ---
    events: pd.DataFrame | None = None
    """コーポレートアクション（配当、分割等）。
    columns: ["ticker", "date", "event_type", "value"]"""

    benchmark: pd.Series | None = None
    """ベンチマーク終値。index=datetime。"""
```

**呼び出し側の構築例**:
```python
import yfinance as yf

# 呼び出し側が自由にデータを取得・加工
prices = yf.download(tickers, start="2015-01-01", end="2025-12-31")

data = BacktestData(
    close=prices["Close"],
    series={
        "open": prices["Open"],
        "high": prices["High"],
        "low": prices["Low"],
        "volume": prices["Volume"],
    },
    metadata={
        "AAPL": {"sector": "Technology", "market_cap": 3.0e12},
        "JPM":  {"sector": "Financials", "market_cap": 6.0e11},
    },
    benchmark=yf.download("SPY")["Close"],
)
```

### 3. PitGuard (`data/pit_guard.py`)

**最重要コンポーネント**。BacktestData へのアクセスを SimulationClock で時刻制限し、PoiT を構造的に強制。

```python
class PitGuard:
    """BacktestData のアクセスを clock.current_date - lag_days で制限。

    Level 1 (構造的): データ要求の end を自動的にクリップ
    Level 2 (計算的): shift(1) による重み適用ラグ
    Level 3 (検証的): 事後の IC 異常検出
    """
    def __init__(self, data: BacktestData, clock: SimulationClock, lag_days: int = 1): ...

    def get_close(self, start: date | None = None) -> pd.DataFrame:
        """close を [start, effective_end] でスライスして返す。"""
        effective_end = self._clock.current_date - timedelta(days=self._lag_days)
        return self._data.close.loc[:effective_end]

    def get_series(self, key: str, start: date | None = None) -> pd.DataFrame:
        """series[key] を PoiT 制限付きで返す。"""
        effective_end = self._clock.current_date - timedelta(days=self._lag_days)
        if key not in self._data.series:
            raise KeyError(f"Series '{key}' not found in BacktestData")
        return self._data.series[key].loc[:effective_end]

    def get_metadata(self) -> dict[str, dict[str, Any]]:
        """metadata は静的なのでそのまま返す。"""
        return self._data.metadata
```

### 4. Signal Protocol (`core/protocols.py`)

```python
@runtime_checkable
class Signal(Protocol):
    name: str
    lookback_days: int

    def compute(self, guard: PitGuard, as_of: date) -> pd.Series:
        """PitGuard 経由でデータにアクセスし、シグナルスコアを返す。
        Index=ticker, values=signal score"""

@runtime_checkable
class WeightScheme(Protocol):
    def compute_weights(
        self, scores: pd.Series, current_weights: dict[str, float],
        constraints: PortfolioConstraints | None = None,
    ) -> dict[str, float]: ...
```

> **Note**: `DataFeed` Protocol は削除。全データアクセスは `PitGuard` 経由に統一。

### 5. BacktestConfig (`types.py`)

```python
class BacktestConfig(BaseModel):
    model_config = ConfigDict(frozen=True)

    name: str
    start_date: date
    end_date: date
    initial_capital: float = 1_000_000.0
    rebalance_frequency: Literal["daily", "weekly", "monthly", "quarterly"] = "monthly"
    commission_bps: float = 10.0
    slippage_bps: float = 5.0
    pit_lag_days: int = 1  # zipline 方式の強制ラグ

class BacktestResult(BaseModel):
    model_config = ConfigDict(frozen=True)

    config: BacktestConfig
    daily_nav: list[tuple[date, float]]
    daily_returns: list[tuple[date, float]]
    trades: list[Fill]
    portfolio_snapshots: list[PortfolioSnapshot]
    benchmark_returns: list[tuple[date, float]] | None
```

> **Note**: `universe` と `benchmark_ticker` は `BacktestConfig` から削除。`BacktestData.close.columns` からユニバースを自動取得し、`BacktestData.benchmark` からベンチマークを取得する。データの構造自体が設定を兼ねる。

---

## データフロー

### Event-Driven モード

```
BacktestRunner.run(config, data: BacktestData, strategy, mode="event_driven")
    │
    ├── universe = data.close.columns.tolist()   ← BacktestData から自動取得
    ├── SimulationClock(config.start_date, config.end_date, trading_dates)
    ├── pit_guard = PitGuard(data, clock, lag_days=config.pit_lag_days)
    │
    FOR each trading_date:
    │   ├── clock = clock.advance() → new SimulationClock
    │   ├── pit_guard.update_clock(clock)
    │   ├── close = pit_guard.get_close()
    │   │                    ^^^^^^^^^^^^
    │   │                    PoiT 強制: current_date - lag_days 以降のデータにアクセス不可
    │   ├── signals = strategy.compute_signals(pit_guard, current_date)
    │   │                                      ^^^^^^^^^
    │   │                                      Signal は PitGuard 経由でデータにアクセス
    │   ├── IF rebalance_date:
    │   │       target_weights = strategy.compute_weights(signals, constraints)
    │   │       orders = portfolio_state.generate_orders(target_weights)
    │   │       fills = broker.execute(orders, close_prices)
    │   │       portfolio_state.apply_fills(fills)
    │   ├── portfolio_state.mark_to_market(close_prices)
    │   └── record daily NAV, returns
    │
    └── BacktestResult → Evaluator → BacktestReport
```

### Vectorized モード

```
VectorizedEngine.run(config, data: BacktestData, signal_fn, weight_fn)
    │
    ├── price_matrix = data.close   ← BacktestData から直接取得（全期間）
    ├── signal_matrix = signal_fn(price_matrix)  # ベクトル化計算
    ├── weight_matrix = weight_fn(signal_matrix)
    ├── returns_matrix = price_matrix.pct_change()
    ├── portfolio_returns = (weight_matrix.shift(1) * returns_matrix).sum(axis=1)
    │                        ^^^^^^^^^^^^^^^^ shift(1) で PoiT 強制
    ├── Apply commission/slippage from turnover
    │
    └── BacktestResult (軽量: daily returns のみ, 個別 Fill なし)
```

---

## 既存パッケージ再利用マップ

| backtest コンポーネント | 再利用する既存コード | ファイルパス |
|---|---|---|
| リスク指標 | `strategy.risk.calculator.RiskCalculator` | `src/strategy/risk/calculator.py` |
| ポートフォリオ | `strategy.portfolio.Portfolio, Holding` | `src/strategy/portfolio.py` |
| ドリフト検出 | `strategy.rebalance.types.DriftResult` | `src/strategy/rebalance/types.py` |
| ファクター計算 | `factor.core.base.Factor` | `src/factor/core/base.py` |
| ファクター登録 | `factor.core.registry.FactorRegistry` | `src/factor/core/registry.py` |
| IC/IR 分析 | `factor.validation.ic_analyzer.ICAnalyzer` | `src/factor/validation/ic_analyzer.py` |
| 分位分析 | `factor.validation.quantile_analyzer` | `src/factor/validation/quantile_analyzer.py` |
| フォワードリターン | `factor.core.return_calculator.ReturnCalculator` | `src/factor/core/return_calculator.py` |
| PoiT パターン | `dev/ca_strategy/pit.py` | `src/dev/ca_strategy/pit.py` |
| チェックポイント | `dev/ca_strategy/batch.CheckpointManager` | `src/dev/ca_strategy/batch.py` |
| ポートフォリオ構築 | `dev/ca_strategy/portfolio_builder.PortfolioBuilder` | `src/dev/ca_strategy/portfolio_builder.py` |
| コーポレートアクション | `dev/ca_strategy/return_calculator` | `src/dev/ca_strategy/return_calculator.py` |
| 構造化ロギング | `utils_core.logging.get_logger` | `src/utils_core/logging/config.py` |
| テクニカル指標 | `analyze.technical.indicators.TechnicalIndicators` | `src/analyze/technical/indicators.py` |

> **Note**: `market.yfinance`, `market.fred`, `market.cache` は backtest パッケージの依存から除外。
> データ取得は呼び出し側の責務。backtest エンジンは `BacktestData` コンテナのみを受け取る。

---

## PoiT 強制の3層設計

| 層 | 場所 | メカニズム |
|---|---|---|
| **Level 1: 構造的** | `PitGuard` | `BacktestData` へのアクセスを `current_date - lag_days` でキャップ。Signal は `PitGuard` 経由でのみデータにアクセス可能 |
| **Level 2: 計算的** | Engine 内 | Vectorized: `weight_matrix.shift(1)` / Event-driven: シグナルは t-1 のデータで計算、t で適用 |
| **Level 3: 検証的** | `evaluation/metrics.py` | IC > 0.05 のとき PoiT バイアス警告。ウォークフォワード検証で OOS パフォーマンス確認 |

---

## 実装フェーズ

### Phase 1: 基盤（Core + Data + Types）

**ファイル**: `types.py`, `errors.py`, `core/protocols.py`, `core/clock.py`, `core/universe.py`, `core/calendar.py`, `data/container.py`, `data/pit_guard.py`

- BacktestData 3層コンテナ（`data/container.py`）
- 全 Pydantic モデルと Protocol を定義
- SimulationClock + TradingCalendar（営業日計算）
- PitGuard（BacktestData への時刻制限アクセス）
- PoiT エッジケースの Property テスト

### Phase 2: 実行レイヤー

**ファイル**: `execution/order.py`, `execution/broker.py`, `execution/position.py`, `execution/portfolio_state.py`

- Order/Fill モデル
- SimulatedBroker（スリッページ、手数料）
- PositionTracker, PortfolioState
- コーポレートアクション処理（`dev/ca_strategy/return_calculator.py` パターン再利用）

### Phase 3: シグナル & 戦略

**ファイル**: `signal/base.py`, `signal/factor_signal.py`, `signal/technical_signal.py`, `signal/custom.py`, `strategy/base.py`, `strategy/rebalance.py`, `strategy/factor_strategy.py`, `strategy/technical_strategy.py`, `strategy/algo_stack.py`

- Signal ベースクラス + SignalRegistry（`factor.core.registry` パターン）
- FactorSignalAdapter（factor → Signal 変換）
- TechnicalSignalAdapter（analyze.technical → Signal 変換）
- RebalanceStrategy, FactorStrategy, TechnicalStrategy
- AlgoStack（bt 方式の宣言的合成）
- 組み込みシグナル: Momentum, MeanReversion, EqualWeight

### Phase 4: エンジン

**ファイル**: `engine/vectorized.py`, `engine/event_driven.py`, `engine/runner.py`

- VectorizedEngine（パラメータスイープ対応）
- EventDrivenEngine（バーごとシミュレーション）
- BacktestRunner（統一エントリーポイント）
- CheckpointManager 再利用（長時間パラメータスイープ向け）

### Phase 5: 評価 & レポーティング

**ファイル**: `evaluation/metrics.py`, `evaluation/report.py`, `evaluation/walk_forward.py`, `evaluation/comparison.py`

- `RiskCalculator` ラッパー（Sharpe, Sortino, Max DD, VaR, Beta, IR, Treynor）
- `ICAnalyzer` 統合（シグナル品質評価）
- BacktestReport（Markdown / JSON / CSV 出力）
- ウォークフォワード分析（ローリングウィンドウ OOS 検証）
- 複数戦略比較

### Phase 6: 統合アダプター

**ファイル**: `integration/ca_strategy.py`, `integration/factor_integration.py`

- CA Strategy アダプター: PortfolioResult → バックテスト可能な戦略
- Factor 統合: Factor → Signal, MultiFactorStrategy
- ウォークフォワードによる CA Strategy 評価

---

## テスト構造

```
tests/backtest/
    conftest.py              # サンプル BacktestData フィクスチャ、テスト用データ生成ヘルパー
    unit/
        test_types.py
        test_backtest_data.py     # BacktestData 3層コンテナのバリデーション
        test_clock.py
        test_pit_guard.py
        test_broker.py
        test_portfolio_state.py
        test_signal_base.py
        test_factor_signal.py
        test_technical_signal.py
        test_rebalance_strategy.py
        test_vectorized_engine.py
        test_event_driven_engine.py
        test_metrics.py
        test_walk_forward.py
    property/
        test_pit_guard_properties.py        # PoiT: いかなる入力でも未来データ非返却
        test_backtest_data_properties.py    # BacktestData: series の index/columns 整合性
        test_portfolio_state_properties.py  # NAV >= 0, weights sum <= 1.0
    integration/
        test_factor_integration.py
        test_ca_strategy_adapter.py
        test_full_pipeline.py
```

**Critical Property Test**:
```python
@given(
    current_date=st.dates(min_value=date(2010,1,1), max_value=date(2025,12,31)),
    request_end=st.dates(min_value=date(2010,1,1), max_value=date(2026,12,31)),
    lag_days=st.integers(min_value=0, max_value=5),
)
def test_pit_guard_never_returns_future_data(current_date, request_end, lag_days):
    """PitGuardedFeed は current_date - lag_days より後のデータを絶対に返さない"""
```

---

## 依存関係

```
backtest (new)
    ├── utils_core          (logging)
    ├── strategy            (RiskCalculator, Portfolio, Holding, DriftResult)
    ├── factor              (Factor, FactorRegistry, ICAnalyzer, QuantileAnalyzer)
    └── (optional) dev/ca_strategy  (統合アダプターのみ)

※ market パッケージへの依存なし（SOLID/DIP）
※ データ取得・加工は呼び出し側の責務
```

`pyproject.toml` に `src/backtest` をパッケージとして追加が必要。

---

## 使用例

### モメンタム戦略のバックテスト

```python
import yfinance as yf
from backtest import BacktestRunner, BacktestConfig
from backtest.data import BacktestData
from backtest.signal import MomentumSignal
from backtest.strategy import RebalanceStrategy

# --- 呼び出し側がデータを準備 ---
tickers = ["AAPL", "MSFT", "GOOGL", "AMZN", "META", ...]
prices = yf.download(tickers + ["SPY"], start="2014-01-01", end="2025-12-31")

data = BacktestData(
    close=prices["Close"][tickers],
    series={"volume": prices["Volume"][tickers]},
    metadata={t: {"sector": get_sector(t)} for t in tickers},
    benchmark=prices["Close"]["SPY"],
)

# --- バックテスト実行 ---
config = BacktestConfig(
    name="momentum_12m",
    start_date=date(2015, 1, 1),
    end_date=date(2025, 12, 31),
    rebalance_frequency="monthly",
)

signal = MomentumSignal(lookback=252, skip_recent=21)
strategy = RebalanceStrategy(signal=signal, top_n=30)

runner = BacktestRunner()
result = runner.run(config, data, strategy, mode="event_driven")
report = runner.evaluate(result)
report.to_markdown("output/momentum_report.md")
```

### パラメータスイープ（Vectorized）

```python
from backtest.engine import VectorizedEngine

engine = VectorizedEngine()
results = engine.parameter_sweep(
    config=config,
    data=data,
    signal_cls=MomentumSignal,
    param_grid={"lookback": [63, 126, 252], "skip_recent": [0, 21]},
)
```

### CA Strategy 評価

```python
from backtest.integration import CAStrategyBacktestAdapter

adapter = CAStrategyBacktestAdapter()
strategy = adapter.from_portfolio_result(portfolio, formation_date=date(2015, 12, 31))
result = runner.run(config, data, strategy, mode="event_driven")
```

### ファクター戦略（series レイヤー活用）

```python
from factor.implementations import PBRatioFactor

# 呼び出し側がファクター値を事前計算して series に注入
pb_values = compute_pb_ratio(tickers, "2014-01-01", "2025-12-31")

data = BacktestData(
    close=prices["Close"][tickers],
    series={
        "pb_ratio": pb_values,           # Layer 2: ファクター値
        "fed_funds_rate": fred_data,     # Layer 2: 経済指標
    },
    metadata={
        "AAPL": {"sector": "Technology", "market_cap": 3e12},
        "JPM":  {"sector": "Financials", "market_cap": 6e11},
    },
)
```

---

## 設計トレードオフ

| 決定 | 理由 |
|------|------|
| Vectorized + Event-driven 両方実装 | 型・評価レイヤーを共有し、エンジン部分だけ分離。コード重複は最小限 |
| SimulationClock を frozen Pydantic | エンジンだけが時間を進行できる。PoiT の推論が容易に |
| PitGuard は BacktestData のラッパー | Signal は PitGuard 経由でのみデータにアクセス。PoiT が構造的に強制される |
| **market パッケージに依存しない (SOLID/DIP)** | エンジンは `BacktestData` コンテナのみを受け取る。データ取得・加工は呼び出し側の責務。yfinance/FRED/Bloomberg 等の具象実装と疎結合になり、テストも容易 |
| **BacktestData 3層コンテナ** | Layer 1 (close) は全戦略共通。Layer 2 (series) でファクター値・経済指標等を柔軟に追加。Layer 3 (metadata) でセクター・時価総額等の静的属性を格納。戦略タイプに依存しない汎用設計 |
| `src/backtest/` に配置（`src/dev/` ではない） | strategy, factor と同列の汎用パッケージとして長期的に育てる |
| RiskCalculator を再実装せず委譲 | DRY 原則。strategy パッケージとの結合は許容範囲 |

---

## 検証方法

1. **ユニットテスト**: `make test` で全テスト通過
2. **Property テスト**: PitGuard が任意入力で未来データを返さないことを Hypothesis で証明
3. **Property テスト**: BacktestData の series が close と同じ index/columns 構造であることを検証
4. **統合テスト**: サンプル BacktestData 構築 → バックテスト実行 → レポート生成の E2E
5. **品質チェック**: `make check-all`（format, lint, typecheck, test）
6. **サニティチェック**: 既知の戦略（equal-weight SPY 構成銘柄）でベンチマークに近いリターンを確認
7. **PoiT 検証**: 意図的に未来データアクセスを試みて PitGuard が正しくブロックすることを確認
8. **SOLID 検証**: backtest パッケージの import に market が含まれないことを確認
