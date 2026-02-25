# Python Backtesting Library Architecture Research (2024-2025)

**Date**: 2026-02-25
**Purpose**: 主要なPythonバックテストライブラリのアーキテクチャ、設計パターン、コア抽象化の包括的リサーチ

---

## 1. 総合比較表

| 項目 | vectorbt | backtrader | zipline-reloaded | bt | QuantConnect/LEAN | QSTrader |
|------|----------|------------|------------------|----|-------------------|----------|
| **パラダイム** | Vectorized | Event-driven | Event-driven | Declarative/Tree | Event-driven (Framework) | Event-driven (Schedule) |
| **言語** | Python (NumPy/Numba) | Python | Python (Cython) | Python (NumPy/ffn) | C# + Python (Python.NET) | Python |
| **Strategy定義** | Functional (配列操作) | Class-based (継承) | Function-based (initialize/handle_data) | Declarative (Algoスタック) | Class-based (5モデル分離) | Class-based (Signal/Portfolio分離) |
| **実行速度** | 最速 (Numba JIT) | 中速 | 低速 (per-bar Python) | 中速 | 高速 (C#エンジン) | 中速 |
| **ライブ取引** | 限定的 (PRO版) | 対応 (IB等) | 限定的 (StrateQueue経由) | 非対応 | 完全対応 (クラウド) | 対応 (QuantStart) |
| **資産クラス** | 汎用 | 汎用 | 株式中心 | 株式/ETF | マルチアセット | 株式/ETF |
| **最適化** | ネイティブ (ベクトル化) | optstrategy | 限定的 | 限定的 | クラウド最適化 | 限定的 |
| **コミュニティ** | 活発 (PRO有料) | 大規模 (更新停滞) | 中規模 (zipline-reloaded) | 小規模 | 最大級 (商用) | 小規模 (教育的) |
| **GitHub Stars** | ~4.3k | ~14k | ~17k (本家) / ~1.2k (reloaded) | ~2.2k | ~10k | ~2.7k |
| **メンテナンス状況 (2025)** | 活発 (PRO中心) | 停滞 (1.9.78) | 活発 (3.1.1) | 低活性 | 活発 (商用) | 低活性 |
| **ML/LLM統合** | 容易 (配列ベース) | 困難 (イベント構造) | 中程度 (Pipeline) | 困難 | 中程度 (研究環境) | 困難 |

---

## 2. 各ライブラリの詳細アーキテクチャ

### 2.1 vectorbt (vectorbt / vectorbt-pro)

#### 設計思想
- **Vectorized Backtesting**: 戦略のインスタンスをベクトル化された形式で表現し、複数の戦略インスタンスを単一の多次元配列にパックして同時処理
- **Numba JIT**: NumPy/pandas上に構築され、Numbaで加速
- **Lego-brick構成**: 各コンポーネントが独立して組み合わせ可能

#### コア抽象化

```
Data Layer (YFData, BinanceData, CCXTData)
    ↓
IndicatorFactory → Indicators (MA, BBANDS, RSI)
    ↓
SignalFactory → Signal Generators
    ↓
Portfolio Engine (from_signals / from_orders / from_order_func)
    ↓
Records (Orders, Trades, Positions, Drawdowns)
    ↓
Stats & Visualization
```

**Portfolio クラス** (中核):
- `Portfolio.from_signals(close, entries, exits)`: シグナルベースのシミュレーション。エントリー/イグジットのブール配列から自動的にオーダーを生成
- `Portfolio.from_orders(close, size, direction)`: オーダーベースのシミュレーション。サイズと方向を配列で指定
- `Portfolio.from_order_func(close, order_func_nb)`: Numbaコンパイルされたカスタムオーダー関数。最も柔軟（`flexible=True`でバーごとに複数オーダー可能）

**ArrayWrapper**: pandas DataFrameとvectorbtの最適化された配列操作のブリッジ

**MappedArray / Records**: イベントデータ（取引、注文、ポジション）を構造化NumPy配列で効率管理

#### データフロー
1. データソース → DataUpdater → pandas DataFrame (OHLCV)
2. DataFrame → Indicators (ベクトル化計算)
3. Indicators → Signals (ブール配列)
4. Signals → Portfolio.from_signals() (Numbaコンパイル済みシミュレーション関数)
5. シミュレーション関数がrow-by-row (時間次元), column-by-column (資産次元) で走査
6. Results → Records (Orders, Trades, Positions, Drawdowns)
7. Records → Stats / Visualization

#### 強み
- パラメータの全組み合わせを一括シミュレーション可能（ブロードキャスティング）
- 数千の戦略バリエーションを数秒で評価
- NumPy/pandasとの完全互換
- ML/LLMとの統合が容易（配列入出力）

#### 弱み
- ルックアヘッドバイアスの防止はユーザー責任（フレームワークレベルでの強制なし）
- リアルな注文執行シミュレーション（スリッページ、部分約定）が限定的（open source版）
- イベント駆動型と比較してライブ取引への移行が困難
- PRO版は有料（$20/月）

#### vectorbt PRO vs Open Source
- PRO: 次世代エンジン。ティックレベル解像度、スリッページモデル（Binance実約定と0.3%以内の精度）、高度な機能
- Open Source: 基本機能は無料、コミュニティ駆動

---

### 2.2 backtrader

#### 設計思想
- **Event-driven**: Cerebro（脳）がイベントループを駆動
- **MetaClass Architecture**: Pythonのメタクラスシステムを活用した宣言的フレームワーク
- **トレーダーの視点**: 現実のトレーダーの思考プロセスに近い設計

#### コア抽象化

```
Cerebro (Engine)
├── DataFeed (Lines-based OHLCV)
│   └── Lines / LineBuffer (MetaBase metaclass)
├── Strategy (ユーザー定義)
│   ├── __init__() → Indicator宣言
│   ├── prenext() → minimum period未到達時
│   ├── next() → メインロジック
│   ├── notify_order() → 注文通知
│   └── notify_trade() → 取引通知
├── Broker (注文執行・口座管理)
│   ├── CommissionInfo
│   └── Sizer (ポジションサイズ)
├── Observer (リアルタイム観測)
├── Analyzer (パフォーマンス分析)
└── Writer (結果出力)
```

**Lines / MetaBase システム** (最も特徴的):
- `MetaDataBase.__call__()` が `Lines.__init__()` を呼び出し、各ラインに対して `LineBuffer` を生成
- データフィードのカラム（Open, High, Low, Close, Volume, DateTime）がそれぞれ `LineBuffer` として管理
- クラス定義時（インスタンス化前）に初期化が行われるメタクラスパターン
- `lines = ('pe',)` のようなタプルで宣言的にライン定義

**Strategy クラス**:
- `__init__`: インジケーター宣言（minimum period自動計算）
- `prenext`: minimum period未満のバーで呼ばれる
- `next`: メインの取引ロジック（1バーごとに呼ばれる）
- `notify_order(order)`: 注文ステータス変更時に呼ばれる
- `notify_trade(trade)`: 取引の開始/更新/クローズ時に呼ばれる
- `notify_cashvalue(cash, value)`: 現金残高/ポートフォリオ価値変更時

**Order/Position/Broker**:
- `Order`: 作成/実行データと注文タイプを保持。ユーザーへの通知手段
- `Position`: サイズと価格を追跡・更新。注文発行の判断材料
- `Broker`: BackBroker（バックテスト用ブローカー）が注文の受理・実行を管理
- `Sizer`: `_getsizing()` メソッドでCommissionInfo、利用可能現金、データを受けてポジションサイズを決定

**最適化パターン**:
```python
cerebro.optstrategy(MyStrategy, myparam1=range(10, 20))
```
同じStrategyクラスを異なるパラメータで複数回インスタンス化

#### データフロー
1. DataFeed → Cerebro.adddata() で登録
2. Cerebro.run() → イベントループ開始
3. 各バーで: DataFeed → Strategy.next() → buy()/sell() → Broker
4. Broker → Order作成 → 次のバーで執行
5. 執行結果 → Strategy.notify_order() / notify_trade()
6. Analyzer → 最終統計

#### 強み
- 豊富なドキュメントと大規模コミュニティ
- ライブ取引への移行が容易（同じStrategy使用可）
- IB, Oanda等のブローカー統合
- 柔軟なCommission/Sizer/Analyzer拡張
- 最も直感的なイベント通知システム

#### 弱み
- メンテナンス停滞（最終大規模更新は数年前）
- メタクラスシステムの学習曲線が急峻
- 大量資産の同時バックテストで性能低下
- ML統合が構造的に困難（イベント駆動×反復構造）
- Python 3.12+での互換性問題報告あり

---

### 2.3 zipline (zipline-reloaded)

#### 設計思想
- **Institutional-grade**: Quantopian社が実運用で使用した設計
- **Look-ahead bias防止**: フレームワークレベルでのPoint-in-Time (PIT) データ管理
- **Pipeline API**: 大量銘柄のファクター計算を効率的に処理

#### コア抽象化

```
TradingAlgorithm (中央コーディネーター)
├── initialize(context) → 初期設定
├── handle_data(context, data) → バーごとのロジック
├── before_trading_start(context, data) → 取引開始前処理
└── schedule_function(func, date_rule, time_rule) → スケジューリング

Pipeline API
├── Pipeline → ファクター計算グラフ
│   ├── Factor (数値出力)
│   │   ├── Built-in: AverageDollarVolume, VWAP等
│   │   └── CustomFactor (inputs, window_length, compute())
│   ├── Filter (ブール出力)
│   └── Classifier (カテゴリ出力)
└── BoundColumn (USEquityPricing.close等)

Data Management
├── DataBundle → OHLCV + Adjustments (splits/dividends)
├── BarData → PIT current/historical data
├── TradingCalendar → 取引所営業時間
└── AssetFinder → 銘柄マスタ管理
```

**TradingAlgorithm クラス** (中核):
- `initialize(context)`: シミュレーション開始時に1回呼ばれる。状態は `context` 辞書に保持
- `handle_data(context, data)`: 取引頻度ごとに呼ばれる（日次/分次）
- `schedule_function()`: 任意タイミングでの関数スケジューリング（`date_rules.every_day()`, `time_rules.market_open(minutes=30)`等）

**Pipeline API** (最も特徴的):
- `CustomFactor`: `inputs` (BoundColumnのイテラブル), `window_length` (過去何バーを使うか), `compute(today, assets, out, *inputs)` を定義
- ファクターは年単位でバルク計算されるが、**プラットフォームが必要な値を必要な時にだけ渡す**（ルックアヘッドバイアス防止）
- Pipeline出力 = 「各日の取引開始時に、前日のデータに基づいて知り得た情報」（1日ラグの自動適用）
- メモリ効率: 中間結果を不要になった時点で破棄

**Look-ahead bias防止メカニズム**:
1. **Point-in-Time data**: BarDataがPITデータのみ提供
2. **Pipeline 1-day lag**: ファクター値は前日データに基づく
3. **Data Bundles**: splits/dividendsのon-the-fly調整
4. **TradingCalendar**: 取引所ごとの営業時間を正確に反映

#### データフロー
1. DataBundle → AssetFinder + AdjustedArray
2. TradingCalendar → シミュレーション時間軸決定
3. 各バーで: BarData (PIT) → handle_data() / Pipeline → order()
4. Pipeline: CustomFactor.compute() → Factor values → Filter → 銘柄選定
5. Order → Blotter → Slippage/Commission → Fill
6. Fill → Portfolio → Performance

#### 強み
- フレームワークレベルのルックアヘッドバイアス防止（最も堅牢）
- Pipeline APIによる大量銘柄の効率的ファクター計算
- TradingCalendar（世界中の取引所対応）
- splits/dividends自動調整
- 学術・制度投資家向けの信頼性
- scikit-learn等ML統合が比較的容易

#### 弱み
- インストールが困難（Python 3.5-3.6設計。2025年でもワークアラウンド必要）
- 実行速度が遅い（per-bar Python実行）
- 株式中心（FX, Crypto等のサポートが弱い）
- ライブ取引は外部フレームワーク（StrateQueue等）が必要
- 大量資産×分足データでバックテストに数時間

---

### 2.4 bt (pmorissette/bt)

#### 設計思想
- **Strategy Tree**: ツリー構造による戦略のモジュール化・再利用
- **Algo Stack**: アルゴリズムをスタックとして宣言的に積み重ね
- **ffn統合**: ffn (Financial Functions for Python) ライブラリとの緊密な統合

#### コア抽象化

```
Tree Hierarchy
├── Node (基本ビルディングブロック、価格追跡とヒエラルキー管理)
│   ├── StrategyBase (戦略コンテナ)
│   │   └── Strategy (AlgoStackを持つ)
│   └── SecurityBase (証券タイプ)
│       ├── Security (基本証券)
│       ├── FixedIncomeSecurity (債券)
│       ├── HedgeSecurity (ヘッジ用)
│       └── CouponPayingSecurity (利払い証券)

Algo System
├── Algo (基底クラス、__call__メソッドでtargetを受け取る)
├── AlgoStack (Algo のリスト、順次実行)
│   ├── Timing Algos: RunMonthly, RunWeekly, RunDaily
│   ├── Selection Algos: SelectAll, SelectWhere, SelectN
│   ├── Weighting Algos: WeighEqually, WeighInvVol, WeighMeanVar
│   └── Execution Algos: Rebalance, Or, Limit
└── Strategy = Tree Node + AlgoStack

Backtest & Result
├── Backtest(strategy, data) → シミュレーション実行単位
├── bt.run(backtest1, backtest2, ...) → 複数バックテスト同時実行
└── Result → ffn.GroupStats のラッパー
```

**宣言的戦略定義**:
```python
strategy = bt.Strategy('monthly_equal', [
    bt.algos.RunMonthly(),       # いつ: 月次リバランス
    bt.algos.SelectAll(),         # 何を: 全銘柄
    bt.algos.WeighEqually(),      # どう配分: 均等加重
    bt.algos.Rebalance()          # 実行: リバランス
])
```

**ツリー構造**:
- 各Node（戦略/証券）が独自のprice indexを持つ
- Algoがnode.allocateを通じてサブノードに資金配分
- 親戦略が子戦略を含む入れ子構造が可能
- SecurityBaseの特殊型（FixedIncomeSecurity, HedgeSecurity, CouponPayingSecurity）が固定収入・クーポン支払の独自評価・キャッシュフロー処理を実装

**Algo間の通信**: `temp` 辞書を通じてキー・バリューを受け渡し
- `WeighEqually` は `temp['weights']` をセット、`temp['selected']` を参照
- `SelectWhere` は `temp['selected']` をセット

#### データフロー
1. pandas DataFrame (OHLCV) → Backtest(strategy, data)
2. bt.run() → シミュレーション開始
3. 各バー: AlgoStack順次実行 → temp辞書でデータ受け渡し
4. Timing Algo (RunMonthly) → True/False でゲート
5. Selection Algo → selected銘柄をtemp['selected']に
6. Weighting Algo → weightsをtemp['weights']に
7. Rebalance Algo → node.allocate()で実際の売買
8. Result → ffn.GroupStats統計

#### 強み
- 最も宣言的で読みやすい戦略定義
- Algoの再利用・組み合わせが容易
- 複数バックテストの同時実行・比較が得意
- FixedIncome等の特殊資産サポート
- ffnの豊富な統計・可視化機能

#### 弱み
- ライブ取引非対応
- コミュニティが小規模で情報が少ない
- 高頻度戦略には不向き
- カスタムAlgo作成の学習曲線
- メンテナンス活性度が低い

---

### 2.5 QuantConnect / LEAN

#### 設計思想
- **Algorithm Framework**: 5つのモデル（Universe, Alpha, Portfolio, Risk, Execution）の明確な分離
- **Cloud-native**: クラウドでの大規模バックテスト・ライブ取引
- **Multi-language**: C#エンジン上でPython/C# Algorithm作成可能（Python.NET経由）

#### コア抽象化（Algorithm Framework）

```
QCAlgorithm (中央アルゴリズムクラス)
│
├── 1. Universe Selection Model
│   └── 資産選定 → OnSecuritiesChanged()イベント
│
├── 2. Alpha Model (extends AlphaModel)
│   ├── Update(algorithm, Slice) → Insight[]
│   └── OnSecuritiesChanged(algorithm, SecurityChanges)
│   │
│   ↓ Insight objects (Symbol, Direction, Magnitude, Confidence, Period, Weight)
│
├── 3. Portfolio Construction Model
│   ├── CreateTargets(algorithm, Insight[]) → PortfolioTarget[]
│   └── Built-in: EqualWeighting, MeanVariance, BlackLitterman
│   │
│   ↓ PortfolioTarget objects (Symbol, Quantity)
│
├── 4. Risk Management Model (extends RiskManagementModel)
│   ├── ManageRisk(algorithm, PortfolioTarget[]) → PortfolioTarget[]
│   └── Built-in: MaxDrawdownPercentPortfolio, MaxSectorExposure, TrailingStop
│   │
│   ↓ Risk-adjusted PortfolioTarget objects
│
└── 5. Execution Model (extends ExecutionModel)
    ├── Execute(algorithm, PortfolioTarget[]) → 実際の注文
    └── Built-in: ImmediateExecution, VWAP, StandardDeviation
```

**Insight オブジェクト** (Alpha → Portfolio間の通信):
- Symbol: 対象銘柄
- Type: Price / Volatility
- Direction: Up / Down / Flat
- Period: 予測期間
- Magnitude: 予測変動幅
- Confidence: 確信度
- Weight: アルファモデル間の重み

**データフロー**:
```
Slice (market data) → Universe Selection → filtered Securities
    ↓
Alpha Model.Update(Slice) → Insight[]
    ↓
Portfolio Construction.CreateTargets(Insight[]) → PortfolioTarget[]
    ↓
Risk Management.ManageRisk(PortfolioTarget[]) → adjusted PortfolioTarget[]
    ↓
Execution Model.Execute(adjusted PortfolioTarget[]) → Orders
```

**Hybrid Algorithm**: Framework APIとClassic API（直接order()呼び出し）の混合も可能

#### 強み
- 最も洗練されたモデル分離（5モデルの完全独立交換）
- 商用レベルの信頼性とデータ品質
- マルチアセット（株式, FX, Crypto, Options, Futures）
- 豊富なデータソース（無料で利用可能）
- クラウドスケーリング
- ライブ取引への直接移行
- 大規模コミュニティとドキュメント

#### 弱み
- C#エンジンのためPython側のデバッグが困難
- Python.NET経由のオーバーヘッド
- プラットフォーム依存（オンプレミスはLEAN CLI経由だが制限あり）
- 学習曲線が急峻（5モデルのインターフェース理解が必要）
- オープンソース版と商用版の機能差

---

### 2.6 QSTrader

#### 設計思想
- **Schedule-driven Event Architecture**: イベント駆動型だが、スケジュールベースのリバランスを中心に設計
- **Signal/Portfolio分離**: シグナル生成とポートフォリオ構築の明確な責務分離
- **教育的設計**: バックテストシステムの構造を学ぶための透明性の高い設計

#### コア抽象化

```
BacktestTradingSession (全体オーケストレーション)
│
├── SimulationEngine (時間ベースイベント生成)
│
├── DataHandler (価格データ提供)
│
├── QuantTradingSystem (戦略ロジック統合)
│   ├── Alpha Model (シグナル生成)
│   ├── Risk Model (リスク管理)
│   ├── Portfolio Construction (ポートフォリオ構築)
│   └── Order Execution (注文執行)
│
├── SimulatedBroker (ブローカーシミュレーション)
│   ├── Fee Models
│   └── Fill Models
│
├── PortfolioHandler
│   ├── on_signal(SignalEvent) → PositionSizer → RiskManager → OrderEvent
│   └── on_fill(FillEvent) → Portfolio更新
│
└── Event Queue (コンポーネント間通信)
    ├── SignalEvent
    ├── OrderEvent
    └── FillEvent
```

**PortfolioHandler** (中核):
- `on_signal(SignalEvent)`: SignalEventを受信 → PositionSizerでサイズ決定 → RiskManagerで検証/修正/除去 → OrderEvent生成
- `on_fill(FillEvent)`: FillEventを受信 → Portfolio（ポジション・残高）を更新

**イベントフロー**:
```
SimulationEngine → Time Event
    ↓
DataHandler → Market Data
    ↓
QuantTradingSystem.Alpha → SignalEvent → Event Queue
    ↓
PortfolioHandler.on_signal() → PositionSizer → RiskManager → OrderEvent → Event Queue
    ↓
SimulatedBroker → FillEvent → Event Queue
    ↓
PortfolioHandler.on_fill() → Portfolio更新
```

#### 強み
- 最も教育的で構造が透明（アーキテクチャ学習に最適）
- Signal → PositionSizer → RiskManager → Order の明確なパイプライン
- イベントキューベースのため、バックテスト→ライブ取引の移行が概念的に容易
- 機関投資家的な設計思想（スケジュールベースリバランス）

#### 弱み
- 小規模コミュニティで情報が限定的
- メンテナンスが低活性
- 高頻度戦略には不向き
- 資産クラスが株式/ETFに限定的
- ドキュメントが不完全

---

## 3. 設計パターン分析

### 3.1 Strategy定義パターンの比較

| パターン | ライブラリ | 例 |
|----------|-----------|-----|
| **Class継承 (Event)** | backtrader, QSTrader | `class MyStrategy(bt.Strategy): def next(): ...` |
| **関数ベース** | zipline | `def initialize(ctx): ... / def handle_data(ctx, data): ...` |
| **宣言的 (Algo Stack)** | bt | `Strategy('s', [RunMonthly(), SelectAll(), WeighEqually(), Rebalance()])` |
| **配列操作 (Vectorized)** | vectorbt | `Portfolio.from_signals(close, entries=cross_above, exits=cross_below)` |
| **5-Model Framework** | QuantConnect | `AlphaModel → PortfolioModel → RiskModel → ExecutionModel` |

### 3.2 データフローパターン

**Vectorized (vectorbt)**:
```
全時系列データ → 配列演算 → シグナル配列 → Portfolio一括シミュレーション
```
- 全データが一度にメモリに載る
- ルックアヘッドバイアスはユーザー責任

**Event-driven (backtrader, zipline, QSTrader)**:
```
DataFeed → 1バー → Strategy.next() → Order → Broker → Fill → 次のバー
```
- 構造的にルックアヘッドバイアスを防止（ziplineが最強）
- ライブ取引への移行が自然

**Declarative (bt)**:
```
Data → Algo1(timing) → Algo2(selection) → Algo3(weighting) → Algo4(execution)
```
- パイプラインのような直線的フロー
- temp辞書でステート管理

**Framework (QuantConnect)**:
```
Universe → Alpha(Insight) → Portfolio(Target) → Risk(adjusted Target) → Execution(Order)
```
- 各ステージが独立交換可能
- 最も分離された設計

### 3.3 ルックアヘッドバイアス防止メカニズム

| レベル | ライブラリ | メカニズム |
|--------|-----------|-----------|
| **フレームワーク強制** | zipline | Pipeline 1-day lag, PIT BarData, TradingCalendar |
| **構造的防止** | backtrader, QSTrader | イベント駆動（過去データのみアクセス可能） |
| **モデル分離** | QuantConnect | Universe → Alpha → Portfolio の一方向フロー |
| **ユーザー責任** | vectorbt, bt | フレームワークレベルの防止なし |

---

## 4. Vectorized vs Event-driven: 詳細比較

### Vectorized Backtesting

**動作原理**: 全ヒストリカルデータを配列として一括処理。シグナル計算はNumPy/pandasのベクトル演算。ポートフォリオシミュレーションは時系列全体を一度に処理。

**性能特性**:
- 100倍以上高速（数千戦略を数秒）
- メモリ使用量は大きいが、NumPyの効率的メモリ管理
- パラメータ最適化に最適

**リスク**:
- **ルックアヘッドバイアス**: 全データが一度に利用可能なため、意図せず将来データを使用するリスク
- **リアリスティック実行**: スリッページ、部分約定、bid-askスプレッドのモデリングが困難
- **日中リスク管理**: ストップロス等の動的リスク管理が困難

### Event-driven Backtesting

**動作原理**: マーケットイベント（新しいバー、ティック）をシーケンシャルに処理。各タイムステップで戦略ロジックが呼ばれ、注文を発行。

**性能特性**:
- 遅い（per-bar Python実行）
- メモリ効率は良い（ストリーミング処理可能）
- ライブ取引と同一コードベース

**利点**:
- **構造的バイアス防止**: 設計上、将来データにアクセス不可
- **リアルな実行モデル**: ティックレベル更新、部分約定、動的リスク管理
- **ライブ移行**: コンポーネント交換だけでライブ取引に移行可能

### ハイブリッドアプローチ（2024-2025のベストプラクティス）

多くのクオンツチームが採用するアプローチ:
1. **Vectorized** で候補戦略をスクリーニング（高速パラメータ探索）
2. **Event-driven** で有望な戦略を最終検証（リアリスティックシミュレーション）
3. **ライブデプロイ** はイベント駆動フレームワーク上で実行

---

## 5. ベストプラクティスとピットフォール（2024-2025）

### 5.1 設計ベストプラクティス

1. **Point-in-Time (PIT) データ管理**: 全データアクセスをPITに制限するレイヤーを設ける
2. **モジュラー設計**: Strategy, Signal, Portfolio, Risk, Execution の各レイヤーを明確に分離
3. **In-sample / Out-of-sample分割**: パラメータ推定 (IS) と性能評価 (OOS) を分離
4. **Deflated Sharpe Ratio**: 複数テストのバイアスを調整したSharpe Ratio
5. **Paper Trading (Forward Test)**: ライブ前のリアルタイム検証

### 5.2 共通ピットフォール

| バイアス | 影響 | 防止策 |
|----------|------|--------|
| **Look-ahead bias** | 過度に楽観的なパフォーマンス | PIT制約、Pipeline 1-day lag、イベント駆動設計 |
| **Survivorship bias** | 年間リターンを1-4%過大評価、Sharpe Ratioを最大0.5ポイント膨張 | 上場廃止銘柄を含むデータセット使用 |
| **Overfitting** | ヒストリカルノイズへの過剰適合、OOS性能の劇的低下 | IS/OOS分割、Walk-forward analysis、Deflated Sharpe Ratio |
| **Transaction cost bias** | 取引コスト未考慮でリターン過大 | リアルなスリッページ・手数料モデル |
| **Data mining bias** | 大量のバリエーションテストで偶然の高パフォーマンスを「発見」 | Minimum Backtest Length、Probabilistic Sharpe Ratio |

### 5.3 2024-2025のトレンド

1. **Hybrid Vectorized + Event-driven**: スクリーニングは高速ベクトル化、検証はイベント駆動
2. **ML/LLM統合**: LLMによるファンダメンタル情報の構造化、ML予測モデルのバックテスト統合
3. **Rust/C++高速化**: RustyBT (zipline-reloaded拡張)、NautilusTrader (Rust/Cython)
4. **クラウドネイティブ**: QuantConnect, StrateQueue等の分散バックテスト
5. **Forward-only Backtesting**: LLMの時系列予測能力評価のための「Temporal Contamination」フリー・フレームワーク

---

## 6. finance プロジェクトへの示唆

### 既存のCA Strategy パイプラインとの対比

現在のfinanceプロジェクトの `dev/ca_strategy` は以下の構造:
```
transcript-loader → claim-extractor → claim-scorer → score-aggregator → sector-neutralizer → portfolio-constructor → output-generator
```

これはQuantConnect/LEANのAlgorithm Frameworkに最も近い設計思想:
- claim-extractor/scorer = **Alpha Model** (Insight生成)
- score-aggregator/sector-neutralizer = **Portfolio Construction Model** (Target生成)
- portfolio-constructor = **Risk Management + Execution** (セクター中立化 + ポートフォリオ構築)

### モジュラー設計で参考にすべきパターン

| パターン | 参考ライブラリ | 適用先 |
|----------|---------------|--------|
| **Pipeline Factor API** | zipline | ファクター計算レイヤー（market/analyze拡張） |
| **Insight/PortfolioTarget** | QuantConnect | Alpha → Portfolio → Riskの標準データ構造 |
| **Algo Stack** | bt | 宣言的戦略構成（strategy拡張） |
| **Records/MappedArray** | vectorbt | 取引記録の効率的管理 |
| **Event Queue** | QSTrader | コンポーネント間の疎結合通信 |
| **TradingCalendar** | zipline | 取引所営業時間管理 |

### 推奨アーキテクチャ方針

1. **Vectorized-first, Event-driven-validation**: スクリーニング/リサーチはベクトル化、最終検証はイベント駆動
2. **PIT制約の強制**: ziplineのPipeline 1-day lag相当の仕組みをデータアクセスレイヤーに組み込む
3. **5-Model分離の採用**: QuantConnectのAlpha/Portfolio/Risk/Execution分離をPythonic に実装
4. **ffn統合**: btが採用しているffnの統計・可視化機能を結果評価に活用
5. **Insight-likeデータ構造**: 戦略シグナルを統一的なInsightオブジェクト（Symbol, Direction, Confidence, Period）で表現

---

## Sources

### vectorbt
- [GitHub - polakowo/vectorbt](https://github.com/polakowo/vectorbt)
- [VectorBT Documentation](https://vectorbt.dev/)
- [VectorBT PRO](https://vectorbt.pro/)
- [VectorBT PRO Fundamentals](https://vectorbt.pro/documentation/fundamentals/)
- [vectorbt Portfolio API](https://vectorbt.dev/api/portfolio/base/)
- [polakowo/vectorbt - DeepWiki](https://deepwiki.com/polakowo/vectorbt/1-overview)
- [VectorBT Introductory Guide - AlgoTrading101](https://algotrading101.com/learn/vectorbt-guide/)
- [From Backtest to Live with VectorBT in 2025](https://medium.com/@samuel.tinnerholm/from-backtest-to-live-going-live-with-vectorbt-in-2025-step-by-step-guide-681ff5e3376e)

### backtrader
- [Cerebro - Backtrader](https://www.backtrader.com/docu/cerebro/)
- [Strategy - Backtrader](https://www.backtrader.com/docu/strategy/)
- [Platform Concepts - Backtrader](https://www.backtrader.com/docu/concepts/)
- [Orders - Backtrader](https://www.backtrader.com/docu/order/)
- [Position - Backtrader](https://www.backtrader.com/docu/position/)
- [Sizers - Backtrader](https://www.backtrader.com/docu/sizers/sizers/)
- [Data Feed Development - Backtrader](https://www.backtrader.com/docu/datafeed-develop-general/datafeed-develop-general/)
- [GitHub - mementum/backtrader](https://github.com/mementum/backtrader)
- [Backtrader Guide - AlgoTrading101](https://algotrading101.com/learn/backtrader-for-backtesting/)

### zipline-reloaded
- [Zipline Documentation](https://zipline.ml4trading.io/)
- [GitHub - stefan-jansen/zipline-reloaded](https://github.com/stefan-jansen/zipline-reloaded)
- [zipline-reloaded - DeepWiki](https://deepwiki.com/stefan-jansen/zipline-reloaded)
- [Zipline Pipeline Workflow](https://mw96.medium.com/zipline-pipeline-6723632824)
- [Zipline API Reference](https://zipline.ml4trading.io/api-reference.html)
- [Zipline ML4Trading - Pipeline](https://stefan-jansen.github.io/machine-learning-for-trading/08_ml4t_workflow/04_ml4t_workflow_with_zipline/)

### bt
- [bt Documentation](https://pmorissette.github.io/bt/)
- [GitHub - pmorissette/bt](https://github.com/pmorissette/bt)
- [bt Algorithms Documentation](https://pmorissette.github.io/bt/algos.html)
- [Flexible Backtesting with BT - Medium](https://medium.com/@richardhwlin/flexible-backtesting-with-bt-7295c0dde5dd)
- [Advanced Backtesting with BT - Medium](https://medium.com/@richardhwlin/advanced-backtesting-with-bt-635ed441cb60)

### QuantConnect / LEAN
- [Algorithm Framework Overview](https://www.quantconnect.com/docs/v2/writing-algorithms/algorithm-framework/overview)
- [Portfolio Construction Key Concepts](https://www.quantconnect.com/docs/v2/writing-algorithms/algorithm-framework/portfolio-construction/key-concepts)
- [Risk Management](https://www.quantconnect.com/docs/v2/writing-algorithms/algorithm-framework/risk-management/key-concepts)
- [Execution Key Concepts](https://www.quantconnect.com/docs/v2/writing-algorithms/algorithm-framework/execution/key-concepts)
- [Algorithm Engine](https://www.quantconnect.com/docs/v2/writing-algorithms/key-concepts/algorithm-engine)
- [LEAN.io](https://www.lean.io/)
- [GitHub - QuantConnect/Lean](https://github.com/QuantConnect/Lean)

### QSTrader
- [GitHub - mhallsmoore/qstrader](https://github.com/mhallsmoore/qstrader)
- [mhallsmoore/qstrader - DeepWiki](https://deepwiki.com/mhallsmoore/qstrader)
- [QuantStart - Portfolio Handler](https://www.quantstart.com/articles/Advanced-Trading-Infrastructure-Portfolio-Handler-Class/)
- [QSTrader Major Update](https://www.quantstart.com/articles/qstrader-a-major-update-on-our-progress/)
- [Event-Driven Backtesting - QuantStart](https://www.quantstart.com/articles/Event-Driven-Backtesting-with-Python-Part-V/)

### 比較・ベストプラクティス
- [Battle-Tested Backtesters Comparison](https://medium.com/@trading.dude/battle-tested-backtesters-comparing-vectorbt-zipline-and-backtrader-for-financial-strategy-dee33d33a9e0)
- [Backtrader vs NautilusTrader vs VectorBT vs Zipline - autotradelab](https://autotradelab.com/blog/backtrader-vs-nautilusttrader-vs-vectorbt-vs-zipline-reloaded)
- [Python Backtesting Frameworks - PipeKit](https://pipekit.io/blog/python-backtesting-frameworks-six-options-to-consider)
- [Vectorized vs Event-driven Backtesting - IBKR](https://www.interactivebrokers.com/campus/ibkr-quant-news/a-practical-breakdown-of-vector-based-vs-event-based-backtesting/)
- [Vectorized vs Event Driven - MarketCalls](https://www.marketcalls.in/system-trading/comparision-of-event-driven-backtesting-vs-vectorized-backtesting.html)
- [Backtesting Frameworks - QuantStart](https://www.quantstart.com/articles/backtesting-systematic-trading-strategies-in-python-considerations-and-open-source-frameworks/)
- [Common Pitfalls in Backtesting](https://medium.com/funny-ai-quant/ai-algorithmic-trading-common-pitfalls-in-backtesting-a-comprehensive-guide-for-algorithmic-ce97e1b1f7f7)
- [Seven Sins of Quantitative Investing](https://bookdown.org/palomar/portfoliooptimizationbook/8.2-seven-sins.html)
- [Survivorship Bias Explained - LuxAlgo](https://www.luxalgo.com/blog/survivorship-bias-in-backtesting-explained/)
