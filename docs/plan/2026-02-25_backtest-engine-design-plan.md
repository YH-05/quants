# バックテストエンジン設計計画

> **正式な設計文書**: [`docs/plan/2026-02-25_backtest-engine-design.md`](./2026-02-25_backtest-engine-design.md)
>
> このファイルは Plan mode 用のエントリーポイントです。全設計内容は上記ファイルに記載済みです。

## Context

金融分析ライブラリ（finance）にはリターン計算・リスク指標・ファクター分析・ポートフォリオ管理の部品が揃っているが、これらを統合してバックテストを実行するエンジンが存在しない。`dev/ca_strategy` の Evaluator は CA Strategy 専用であり、汎用性がない。

**目的**: 既存部品を最大限再利用しつつ、汎用バックテストエンジンを `src/backtest/` に新規作成する。

## 設計方針サマリー

- **Vectorized + Event-driven** の両モード同時実装
- **全戦略タイプ対応**（ファクター、CA Strategy、テクニカル、カスタム）
- **PoiT 強制**（ルックアヘッドバイアス防止）をフレームワークレベルで強制（zipline 方式）
- **SOLID/DIP**: エンジンはデータソースに依存しない。呼び出し側が `BacktestData` を構築して注入
- 既存パッケージ（strategy, factor, analyze, dev/ca_strategy）との統合（**market への依存なし**）

## 主要設計決定

### 1. BacktestData 3層コンテナ (`data/container.py`)

呼び出し側が構築してエンジンに注入するデータコンテナ。

| Layer | 必須/任意 | 内容 | 例 |
|-------|----------|------|-----|
| **Layer 1** | **必須** | `close: pd.DataFrame` — 終値 | 全バックテストで必要 |
| **Layer 2** | 任意 | `series: dict[str, pd.DataFrame]` — 時系列データ | OHLV, ファクター値, 経済指標 |
| **Layer 3** | 任意 | `metadata: dict[str, dict[str, Any]]` — 静的属性 | セクター, 時価総額 |
| オプション | 任意 | `events`, `benchmark` | 配当・分割、ベンチマーク終値 |

### 2. PitGuard (`data/pit_guard.py`)

BacktestData へのアクセスを SimulationClock で時刻制限。Signal は PitGuard 経由でのみデータにアクセス可能。DataFeed Protocol は廃止。

### 3. market パッケージへの非依存 (SOLID/DIP)

- エンジンは `BacktestData` コンテナのみを受け取る
- データ取得（yfinance, FRED, Bloomberg 等）は呼び出し側の責務
- `data/feed.py`, `data/cache_adapter.py` は不要（削除済み）

## パッケージ構造

```
src/backtest/
    __init__.py, py.typed, README.md, errors.py, types.py
    core/       → protocols.py, clock.py, universe.py, calendar.py
    data/       → container.py (BacktestData), pit_guard.py (PitGuard)
    signal/     → base.py, factor_signal.py, technical_signal.py, custom.py
    strategy/   → base.py, rebalance.py, factor_strategy.py, technical_strategy.py, algo_stack.py
    execution/  → order.py, broker.py, position.py, portfolio_state.py
    engine/     → vectorized.py, event_driven.py, runner.py
    evaluation/ → metrics.py, report.py, walk_forward.py, comparison.py
    integration/→ ca_strategy.py, factor_integration.py
```

## 依存関係

```
backtest (new)
    ├── utils_core          (logging)
    ├── strategy            (RiskCalculator, Portfolio, Holding, DriftResult)
    ├── factor              (Factor, FactorRegistry, ICAnalyzer, QuantileAnalyzer)
    └── (optional) dev/ca_strategy  (統合アダプターのみ)

※ market パッケージへの依存なし
```

## 実装フェーズ (6段階)

1. **Phase 1**: 基盤 — BacktestData, PitGuard, SimulationClock, Protocols, Types
2. **Phase 2**: 実行レイヤー — Order/Fill, SimulatedBroker, PortfolioState
3. **Phase 3**: シグナル & 戦略 — Signal, FactorSignalAdapter, TechnicalSignalAdapter, AlgoStack
4. **Phase 4**: エンジン — VectorizedEngine, EventDrivenEngine, BacktestRunner
5. **Phase 5**: 評価 & レポーティング — Metrics, Report, WalkForward, Comparison
6. **Phase 6**: 統合アダプター — CA Strategy, Factor Integration

## 検証方法

1. `make test` — 全テスト通過
2. PitGuard Property テスト — Hypothesis で未来データ非返却を証明
3. BacktestData Property テスト — series の index/columns 整合性
4. E2E 統合テスト — BacktestData 構築 → バックテスト → レポート生成
5. `make check-all` — format, lint, typecheck, test
6. サニティチェック — equal-weight でベンチマーク近似を確認
7. PoiT 検証 — 未来データアクセスのブロック確認
8. SOLID 検証 — backtest の import に market が含まれないことを確認

## 詳細

全設計詳細（コアクラス設計、データフロー図、再利用マップ、使用例、テスト構造等）は [`docs/plan/2026-02-25_backtest-engine-design.md`](./2026-02-25_backtest-engine-design.md) を参照。
