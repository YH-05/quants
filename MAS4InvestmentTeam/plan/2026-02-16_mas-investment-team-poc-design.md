# MAS（マルチエージェント投資チーム）PoC 設計プラン

## Context

海外株式運用チームをマルチAIエージェントシステム（MAS）で再現するPoCを構築する。目的は、従来のクオンツオンリーではなく**クオンタメンタル**（定量＋定性）なジャッジメンタル判断を組み込み、投資判断の透明性を高めること。MASの投資判断は人間のファンドマネージャーの参考になることを想定し、全判断を構造化ファイルとして記録する。

### 決定事項（ユーザー回答）

| 項目             | 決定                                                                                      |
| ---------------- | ----------------------------------------------------------------------------------------- |
| ユニバース       | S&P 500                                                                                   |
| アーキテクチャ   | ハイブリッド（バックテストエンジン=Python、投資判断エージェント=Claude Code Agent Teams） |
| バックテスト期間 | 過去10〜20年（2006-01〜現在）、カットオフ前（〜2025-05）はティッカー匿名化。Phase 1で技術検証（直近2年）、Phase 2でフル期間拡張 |
| ポートフォリオ   | 15-30銘柄・集中投資型（最大ウェイト5%、セクター上限25%）                                  |

---

## 1. MASアーキテクチャ

### 1.1 エージェント構成（12エージェント）

```
MAS Investment Team
│
│  Phase 0: POSTMORTEM（失敗パターン分析）
├── [T0] Postmortem Analyst ─── 破綻企業の失敗パターン抽出、生存者バイアス排除
│       ↓ failure_patterns.json
│
│  Phase 1: SCREENING（500銘柄→50-80銘柄）
├── [T1] Universe Screener ──── ファクタースコアベースの定量スクリーニング
│       ↓ candidates.json
│
│  Phase 2: ANALYSIS（4並列 × 候補銘柄バッチ）
├── [T2] Fundamental Analyst ─┐ SEC Filings (10K/10Q/8K) 分析
├── [T3] Valuation Analyst ───┤ DCF・相対バリュエーション
├── [T4] Sentiment Analyst ───┤ Transcript・ニュース・インサイダー取引
└── [T5] Macro/Regime Analyst ┘ 市場レジーム判定、セクターローテーション
│       ↓ stock_analyses/{ticker}.json
│
│  Phase 3: DEBATE（候補銘柄ごとに2ラウンド）
├── [T6] Bull Advocate ────────┐ 投資賛成の論拠提示
└── [T7] Bear Advocate ────────┘ 投資反対の論拠提示
│       ↓ debate_transcripts/{ticker}.json
│
│  Phase 4: DECISION（統合判断）
├── [T8] Fund Manager ─────── ディベート結果の統合、確信度スコア付与
│       ↓ conviction_scores.json
│
│  Phase 5: PORTFOLIO CONSTRUCTION
├── [T9] Risk Manager ────────┐ エクスポージャー制約の検証
└── [T10] Portfolio Constructor┘ 確信度加重の最適化
        ↓ portfolio.json + investment_rationale.json
```

### 1.2 意思決定メカニズム：構造化ディベート

**マネージャー決定型＋構造化ディベート**（AlphaAgents全会一致型とTradingAgentsマネージャー型のハイブリッド）:

1. **Round 1 - Bull Advocate**: 3-5の投資論拠を定量的証拠付きで提示
2. **Round 1 - Bear Advocate**: 3-5の反論（リスク、競争脅威、バリュエーション懸念）
3. **Round 2 - Bull Rebuttal**: Bear の指摘への反論
4. **Round 2 - Bear Rebuttal**: 最終反論
5. **Fund Manager Decision**: 全ディベートを読み、確信度スコア（0-100）とアクション（BUY/PASS）を決定

**全会一致型ではなくマネージャー決定型を採用する理由**:

- 全会一致は安全/凡庸な選択に収束しやすい（リスク回避バイアス）
- コントラリアンなポジションを取る能力を維持
- ディベートログが完全な監査トレースを提供（透明性）
- 実際のファンド運用チーム構造を再現

### 1.3 ハイブリッドアーキテクチャ設計

```
┌─────────────────────────────────────────────────────────┐
│                  Python バックテストエンジン                │
│  src/strategy/backtest/                                   │
│  ├── engine.py          タイムステップ制御                 │
│  ├── pit_data.py        Point-in-Time データ管理          │
│  ├── anonymizer.py      ティッカー匿名化                  │
│  ├── metrics.py         パフォーマンス計算                 │
│  └── reporting.py       レポート生成                      │
│         │                                                 │
│         │ 各リバランス日に呼び出し                          │
│         ↓                                                 │
│  ┌──────────────────────────────────────────────┐        │
│  │     Claude Code Agent Teams                    │        │
│  │     .claude/agents/mas-invest/                 │        │
│  │     ├── mas-invest-lead.md  (オーケストレータ) │        │
│  │     ├── fundamental-analyst.md                 │        │
│  │     ├── valuation-analyst.md                   │        │
│  │     ├── sentiment-analyst.md                   │        │
│  │     ├── macro-analyst.md                       │        │
│  │     ├── bull-advocate.md                       │        │
│  │     ├── bear-advocate.md                       │        │
│  │     ├── fund-manager.md                        │        │
│  │     ├── risk-manager.md                        │        │
│  │     └── portfolio-constructor.md               │        │
│  └──────────────────────────────────────────────┘        │
│         │                                                 │
│         ↓ portfolio.json                                  │
│  バックテストエンジンがリターン計算・集計                     │
└─────────────────────────────────────────────────────────┘
```

### 1.4 既存パッケージの再利用

#### PoC（Phase 1）のデータソース制約

PoCでは以下の2つのデータソースのみを使用する：

1. **SEC Edgar tools** — ファンダメンタルデータ（財務諸表、10-K/10-Q/8K）
2. **yfinance** — 価格データのみ（株価、リターン計算、時価総額）

FREDマクロ指標、yfinanceの財務指標APIなどはPhase 2以降で追加する。

| 既存パッケージ         | 再利用対象                                                     | MASでの用途                                            | PoC対象 |
| ---------------------- | -------------------------------------------------------------- | ------------------------------------------------------ | ------- |
| `market.yfinance`      | `YFinanceFetcher`                                              | **価格データ取得のみ**（株価・リターン計算・時価総額） | ✅       |
| `edgar`                | `EdgarFetcher`, `SectionExtractor`, `BatchFetcher`             | SEC Filings取得・解析（ファンダメンタル分析）          | ✅       |
| MCP `sec-edgar-mcp__*` | SEC EDGAR MCP                                                  | リアルタイムSEC データアクセス                         | ✅       |
| `factor`               | `MomentumFactor`, `Normalizer`                                 | 価格ベースファクター計算（momentum, size）             | ✅       |
| `strategy.risk`        | `RiskCalculator`                                               | Sharpe, Sortino, MDD, VaR, Beta, IR 計算               | ✅       |
| `strategy.portfolio`   | `Portfolio`                                                    | ポートフォリオ表現                                     | ✅       |
| `strategy.rebalance`   | `Rebalancer`                                                   | ドリフト検出・リバランス                               | ✅       |
| `market.fred`          | `FREDFetcher`                                                  | マクロ指標（レジーム判定）                             | Phase 2 |
| `factor`               | `ValueFactor`, `QualityFactor`                                 | SEC Filings由来の財務ファクター計算                    | Phase 2 |
| `analyze.sector`       | セクター分析                                                   | セクターエクスポージャー監視                           | Phase 2 |
| `analyze.statistics`   | 統計分析                                                       | 相関分析・ベータ計算                                   | Phase 2 |

---

## 2. ポートフォリオ構築プロセス

### 2.1 Phase 0: Postmortem（失敗パターン分析）

初回のみ実行（キャッシュ可能）:

- 過去5年間に上場廃止・大幅下落した企業の10K/10Qを分析
- 共通の警告サイン（売上急減、コンプライアンス違反、インサイダー大量売却等）をパターン化
- `failure_patterns.json` として保存、Phase 1のフィルタリングに使用

### 2.2 Phase 1: スクリーニング（Universe Screener）

```python
# Pythonで実装（エージェント不要）
# PoC: yfinance価格データ + SEC Filings財務データのみ使用

screening_factors = {
    "momentum": 0.40,   # 12M, 6M リターン → yfinance価格データから計算
    "size": 0.20,       # 時価総額（大型寄り） → yfinance価格データから計算
    "quality": 0.25,    # ROE, 営業利益率 → SEC Filings（10-K/10-Q）から抽出
    "value": 0.15,      # PER → 株価(yfinance) / EPS(SEC Filings) で計算
}

# データソース:
#   - 価格データ: yfinance（株価、時価総額、リターン計算）
#   - 財務データ: SEC EDGAR（10-K/10-Q の財務諸表から ROE, EPS, 営業利益率等）
#   - ※ yfinanceの財務指標API、FREDマクロ指標はPoC外（Phase 2で追加）

# → 複合スコア上位50-80銘柄 + failure_patterns除外
```

### 2.3 Phase 2-3: 分析＋ディベート

**各アナリストの出力フォーマット**:

```json
{
  "ticker": "AAPL",
  "analyst_type": "fundamental",
  "as_of_date": "2025-06-30",
  "thesis_points": [
    {
      "statement": "Services事業の粗利益率が70%超で安定成長",
      "evidence": "10-K Item 7 MD&A: Services revenue grew 14% YoY",
      "data_source": "10-K filed 2025-01-31",
      "strength": "strong"
    }
  ],
  "risk_factors": [...],
  "key_metrics": {"roe": 0.48, "operating_margin": 0.31},
  "confidence": 0.85,
  "data_sources": [{"type": "sec_filing", "filing_date": "2025-01-31", "form": "10-K"}],
  "reasoning_chain": ["Step 1: ...", "Step 2: ..."]
}
```

**ディベートの出力フォーマット**:

```json
{
    "ticker": "AAPL",
    "rounds": [
        {
            "round": 1,
            "bull": "Services事業の高マージン成長がEPS成長を牽引...",
            "bear": "iPhone依存度が依然70%超、中国リスクが高い...",
            "evidence_cited": ["10-K FY2024", "IDC市場シェアレポート"]
        },
        {
            "round": 2,
            "bull": "中国リスクは織り込み済み、インド展開で分散...",
            "bear": "バリュエーション（PER 30x）は成長率に対して割高..."
        }
    ]
}
```

### 2.4 Phase 4: ウェイト決定ロジック

```python
# Fund Managerが確信度スコア >= 60の銘柄をBUYと判断
# ウェイト = 確信度スコアの正規化

# 制約条件:
constraints = {
    "max_single_position": 0.05,   # 最大5%
    "min_single_position": 0.01,   # 最小1%
    "max_sector_exposure": 0.25,   # セクター上限25%
    "sum_weights": 1.0,            # フルインベスト
    "no_short": True,              # ロングオンリー
    "max_positions": 30,           # 最大30銘柄
    "min_positions": 15,           # 最小15銘柄
}

# 最適化: scipy.optimize.minimize（確信度加重 + リスク制約）
```

### 2.5 リバランス戦略

- **頻度**: 四半期ごとにフルパイプライン再実行
- **ドリフト**: `strategy.rebalance.Rebalancer.detect_drift(threshold=0.03)` で3%超のドリフト検出
- **ターンオーバー制約**: 四半期あたり片側30%以下
- **四半期間**: ドリフトベースのリバランスのみ、新規銘柄追加なし

---

## 3. バックテスト・パフォーマンス測定

### 3.1 先読みバイアス排除の3層防御

#### 層1: Point-in-Time データ管理（Python）

```python
class PointInTimeDataManager:
    """全データアクセスにカットオフ日を強制する。"""

    def __init__(self, cutoff_date: date):
        self._cutoff = cutoff_date

    # --- PoC対象（Phase 1） ---

    def get_prices(self, tickers, lookback_days=504):
        # cutoff_date 以前の価格データのみ返す（yfinance経由）

    def get_market_cap(self, tickers):
        # cutoff_date 時点の時価総額を返す（yfinance株価 × 発行済株式数）

    def get_sec_filings(self, ticker, form):
        # filing_date（提出日）< cutoff_date のfilingのみ返す
        # ※ reporting_period（報告期間）ではなくfiling_dateでフィルタ
        # PoCでは財務データ（ROE, EPS, 営業利益率等）の唯一のソース

    # --- Phase 2で追加 ---

    # def get_fred(self, series_id):
    #     # cutoff_date 時点で公表済みのデータのみ返す
```

#### 層2: エージェントの時間的制約（プロンプト注入）

各エージェントのシステムプロンプトに以下を注入:

```
TEMPORAL CONSTRAINTS (MANDATORY):
- 現在の日付は {cutoff_date} です。
- この日付以降の情報は一切使用禁止です。
- SEC Filings は filing_date が {cutoff_date} 以前のもののみ参照可能です。
- 将来の株価、業績、イベントに関する知識は使用禁止です。
```

#### 層3: ティッカー匿名化（カットオフ前期間）

LLMの学習データにはカットオフ前の市場結果が含まれるため:

```python
class TickerAnonymizer:
    """LLMの学習データ汚染を防ぐためティッカーを匿名化。"""

    def __init__(self, seed: int = 42):
        self._mapping: dict[str, str] = {}  # AAPL → STOCK_A7X3

    def anonymize(self, ticker: str) -> str:
        """ティッカーをランダムコードに変換。"""

    def anonymize_filing(self, text: str) -> str:
        """Filing テキスト内の企業名・ティッカーを匿名化。"""
        # 企業名、ティッカー、CEOの名前等を汎用的な名前に置換

    def deanonymize(self, code: str) -> str:
        """結果を元のティッカーに復元。"""
```

**期間別の適用**:
| 期間 | PoiTデータ管理 | 時間的制約 | 匿名化 | 備考 |
|------|--------------|----------|--------|------|
| 2006-01〜2025-05（カットオフ前） | ✅ | ✅ | ✅ | LLM学習データに結果が含まれるため匿名化必須 |
| 2025-06〜現在（カットオフ後） | ✅ | ✅ | 不要 | LLMが結果を知らない期間 |

### 3.2 パフォーマンス指標

既存 `strategy.risk.calculator.RiskCalculator` を活用:

| 指標                         | 目標値     | 既存実装                         |
| ---------------------------- | ---------- | -------------------------------- | --- | --- |
| Sharpe Ratio                 | > 0.28     | `RiskCalculator.sharpe_ratio()`  |
| Sortino Ratio                | > 0.20     | `RiskCalculator.sortino_ratio()` |
| Max Drawdown                 | > -15%     | `RiskCalculator.max_drawdown()`  |
| Calmar Ratio                 | > 1.05     | 年率リターン /                   | MDD |     |
| Information Coefficient (IC) | > 0.02     | `factor.analysis.ic.ICAnalyzer`  |
| Rolling Sharpe (12M)         | 安定的に正 | ローリング計算                   |
| Beta                         | 0.8-1.2    | `RiskCalculator` + ベンチマーク  |
| Hit Rate                     | > 50%      | 月次超過リターン勝率             |

### 3.3 ベンチマーク

| ベンチマーク        | ティッカー | 用途                 |
| ------------------- | ---------- | -------------------- |
| S&P 500             | SPY        | プライマリ           |
| S&P 500 等加重      | RSP        | ウェイト効果の分離   |
| Russell 1000 Growth | IWF        | グロースティルト評価 |
| Russell 1000 Value  | IWD        | バリューティルト評価 |

---

## 4. 投資判断の記録・透明性

### 4.1 ファイル構造

```
research/mas-invest/{backtest_id}/
├── config.json                         # バックテスト設定
├── failure_patterns.json               # Postmortem結果（Phase 0）
│
├── {rebalance_date}/                   # 各リバランス日
│   ├── 00_screening/
│   │   ├── factor_scores.json          # 全銘柄のファクタースコア
│   │   └── candidates.json             # スクリーニング通過銘柄
│   ├── 01_analysis/
│   │   ├── {ticker}_fundamental.json
│   │   ├── {ticker}_valuation.json
│   │   ├── {ticker}_sentiment.json
│   │   └── {ticker}_macro.json
│   ├── 02_debate/
│   │   ├── {ticker}_debate.json        # ディベート全文
│   │   └── debate_summary.json         # ディベート要約
│   ├── 03_decision/
│   │   ├── conviction_scores.json      # 確信度スコア一覧
│   │   ├── {ticker}_decision_log.json  # 個別判断ログ
│   │   └── fund_manager_commentary.md  # FM所見
│   ├── 04_portfolio/
│   │   ├── portfolio.json              # 最終ポートフォリオ
│   │   ├── risk_report.json            # リスクレポート
│   │   └── rebalance_trades.json       # 売買リスト
│   └── 05_meta/
│       ├── temporal_context.json       # 時間的制約設定
│       ├── anonymizer_mapping.json     # 匿名化マッピング（カットオフ前のみ）
│       └── execution_log.json          # 実行ログ
│
├── performance/
│   ├── backtest_result.json            # パフォーマンス結果
│   ├── monthly_returns.csv             # 月次リターン時系列
│   └── benchmark_comparison.json       # ベンチマーク比較
│
└── reports/
    ├── {rebalance_date}_report.md      # 各期のFMレポート
    └── final_summary.md                # 最終サマリー
```

### 4.2 FMレポートフォーマット

```markdown
# Portfolio Rebalance Report - {date}

## Executive Summary

{fund_manager_commentary}

## Key Changes

| Action | Ticker | 前回ウェイト | 新ウェイト | 確信度 | 主な理由 |
| ------ | ------ | ------------ | ---------- | ------ | -------- |

## Top Conviction Positions (Score >= 80)

### {Ticker}: {Score}/100

**Bull Case**: {ディベートからのサマリー}
**Bear Case**: {ディベートからのサマリー}
**投資理由**: {FM rationale}
**主要リスク**: {認識しているリスク}

## Debate Highlights

{Bull/Bear Advocateの注目すべき論点の対立}

## Risk Dashboard

| 指標 | 現在値 | 目標 | ステータス |
| ---- | ------ | ---- | ---------- |

## Factor Exposure

{セクターティルト、ファクターローディング}
```

---

## 5. 実装ロードマップ

### Phase 1: MVP（4-6週間）

**目標**: ハイブリッドアーキテクチャ（Python + Agent Teams）の技術的実現可能性、MASが生成する投資判断の品質・透明性、およびバックテストによるパフォーマンス参考値の3軸を検証する。チーム・同僚にMASの可能性を共有・デモできる品質の成果物を生成する。

#### PoC 成功基準（3軸）

| 軸 | 成功基準 | 評価方法 |
|----|----------|----------|
| **1. システム実現可能性** | Python→Agent Teams→Python のハイブリッドパイプラインが10〜20年分（40〜80四半期）のバックテストを完走する | 全リバランス日で `portfolio.json` が出力され、パフォーマンス集計が完了する |
| **2. 投資判断品質** | 各銘柄の投資判断に SEC Filings の定量的証拠が紐づいている | `decision_log.json` の `evidence` フィールドが全銘柄で非空 |
| **3. パフォーマンス参考値** | SPY対比で大幅な劣後がない（パフォーマンスは参考値） | Sharpe, Sortino, MDD を算出しベンチマークと並記 |

**システム実現可能性の詳細要件**:

| 要件 | 基準 | 備考 |
|------|------|------|
| パイプライン完走 | 全リバランス日で `portfolio.json` が生成される | エラー発生時はリトライ後にスキップし、スキップ率 < 5% |
| スケーラビリティ | Phase 1（直近2年）で技術検証後、フル期間に拡張可能 | 中間結果キャッシュにより再実行コストを抑制 |
| 匿名化の一貫性 | カットオフ前期間（〜2025-05）で匿名化が正しく動作 | 復元後のティッカーが正確に一致すること |
| 実行時間・コスト | フル期間バックテストが現実的なコスト・時間で完了する | 目安: フル期間で $500-1,500、実行時間 24-72時間 |
| 再実行可能性 | 中間結果キャッシュにより、途中再開・部分再実行が可能 | リバランス日単位でのチェックポイント |

#### PoC 目標アウトプット

| # | アウトプット | 形式 | 想定読者 | 説明 |
|---|-------------|------|----------|------|
| 1 | **ポートフォリオ構築結果** | `portfolio.json` × 40-80期 | 自分・チーム | 各リバランス日の銘柄・ウェイト・確信度スコア |
| 2 | **投資判断ログ** | `{ticker}_decision_log.json` | チーム | 銘柄ごとの投資根拠（Fundamental Analyst の分析 → Fund Manager の判断）。SEC Filings の証拠を紐づけ |
| 3 | **FM（ファンドマネージャー）レポート** | `{date}_report.md` × 40-80期 | チーム | 各リバランス期のポートフォリオ変更理由、確信度上位銘柄のサマリー |
| 4 | **バックテストサマリー** | `backtest_result.json` + `final_summary.md` | チーム | 10〜20年間の累積パフォーマンス、SPY / RSP との比較チャート、年次・ローリング指標 |
| 5 | **システム実行ログ** | `execution_log.json` | 自分 | 各フェーズの実行時間、LLMコール数、エラー率、コスト集計 |

#### PoC で検証しないこと（Phase 2 以降）

- ディベート（Bull/Bear Advocate）の付加価値
- マクロレジーム判定の精度
- ポートフォリオ最適化（確信度加重のみ、リスク最適化なし）
- 汚染検出（Contamination Detection）の網羅性

#### 段階的アプローチ

| ステップ | 期間 | 目的 | リバランス回数 |
|----------|------|------|---------------|
| **Step 1: 技術検証** | 直近2年（2024Q1〜2025Q4） | パイプライン動作確認、エラー検出・修正 | 8回 |
| **Step 2: フル期間実行** | 10〜20年（2006-01〜現在） | バックテスト結果生成、パフォーマンス評価 | 40-80回 |

Step 1 で技術的な問題を解消した後、Step 2 でフル期間に拡張する。Step 2 は中間結果キャッシュを活用し、Step 1 の結果を再利用する。

**スコープ**:

- リバランス: 四半期、10〜20年分（40〜80回）
- エージェント: Universe Screener（Python） + Fundamental Analyst + Fund Manager（ディベートなし）
- 15-20銘柄、確信度加重
- 匿名化あり（カットオフ前、〜2025-05）
- **データソース制約**: SEC Edgar tools（ファンダメンタルデータ）+ yfinance（価格データのみ）
  - yfinanceの財務指標API、FREDマクロ指標はPhase 2で追加

**新規実装**:

| コンポーネント                  | 場所                                  | 概要                             |
| ------------------------------- | ------------------------------------- | -------------------------------- |
| `BacktestEngine`                | `src/strategy/backtest/engine.py`     | タイムステップ制御               |
| `PointInTimeDataManager`        | `src/strategy/backtest/pit_data.py`   | PoiTデータ管理                   |
| `TickerAnonymizer`              | `src/strategy/backtest/anonymizer.py` | ティッカー匿名化                 |
| `BacktestConfig`, `TimeStep` 等 | `src/strategy/backtest/types.py`      | データ型定義                     |
| `BacktestMetrics`               | `src/strategy/backtest/metrics.py`    | パフォーマンス計算               |
| `UniverseScreener`              | `src/strategy/screening/screener.py`  | ファクターベーススクリーニング   |
| `fundamental-analyst.md`        | `.claude/agents/mas-invest/`          | ファンダメンタル分析エージェント |
| `fund-manager.md`               | `.claude/agents/mas-invest/`          | 投資判断エージェント             |
| `mas-invest-lead.md`            | `.claude/agents/mas-invest/`          | オーケストレータ                 |

### Phase 2: フル機能（6-8週間）

**追加**:

- **データソース拡張**: yfinance財務指標API、FREDマクロ指標、ValueFactor/QualityFactor
- Bull/Bear Advocate ディベートシステム（2ラウンド）
- Valuation Analyst, Sentiment Analyst, Macro/Regime Analyst
- Postmortem Analyst（生存者バイアス排除）
- Risk Manager（エクスポージャー制約）
- ポートフォリオ最適化（確信度加重＋リスク制約）
- 完全なディベートログ・FMレポート生成
- 汚染検出（Contamination Detection）
- Phase 1 のフル期間バックテスト結果をベースに、拡張エージェントで再実行

### Phase 3: 拡張（4-6週間）

**追加**:

- MSCI Kokusai / ACWI ex Japan 対応
- Earnings Transcript 分析の強化
- 動的ファクターウェイト調整（レジーム連動）
- Black-Litterman最適化
- Walk-forward最適化
- `/mas-invest-backtest`, `/mas-invest-portfolio` コマンド

---

## 6. 技術的リスクと対策

| リスク                   | 影響                                            | 対策                                                                        |
| ------------------------ | ----------------------------------------------- | --------------------------------------------------------------------------- |
| **LLMコスト**            | フルパイプライン50銘柄×4アナリスト=200コール/回。10-20年で40-80回 | バッチ処理（10銘柄/コール）、中間結果キャッシュ（リバランス日単位）、途中再開可能 |
| **LLMレイテンシ**        | 30-60秒/コール、フル期間で24-72時間             | Phase 2の4エージェント並列（Agent Teams実証済み）、非同期実行、チェックポイント |
| **学習データ汚染**       | カットオフ前（〜2025-05）が期間の大半を占める   | ティッカー匿名化＋汚染検出テスト、カットオフ後を主評価期間                  |
| **SEC Filing解析エラー** | 不完全なファンダメンタル分析・スクリーニング    | MCP `sec-edgar-mcp` をプライマリ、`edgar.extractors` をフォールバック。PoCではSEC Filingsが唯一の財務データソースのため特に重要 |
| **yfinance価格データ欠損** | リターン計算・モメンタムスコアのエラー         | 欠損日の補間、上場廃止銘柄の最終価格保持                                    |
| **生存者バイアス**       | リターンの過大評価                              | Phase 0 Postmortem、上場廃止銘柄をユニバースに含む                          |
| **再現性**               | LLMの非決定性                                   | temperature=0、全エージェント出力をログ、プロンプトのバージョン管理         |

**コスト見積もり**:

- Phase 1 Step 1（技術検証、直近2年）: ~$30-80（8四半期、基本エージェント）
- Phase 1 Step 2（フル期間、10-20年）: ~$500-1,500（40-80四半期、基本エージェント）
- Phase 2 フルバックテスト: ~$2,000-5,000（40-80四半期、フルエージェント+ディベート）
- 対策: SEC FilingsとマーケットデータをSQLiteキャッシュ、LLM分析はリバランス日のみ実行

---

## 7. 新規ファイル構造

```
src/strategy/
├── backtest/                     # 新規パッケージ
│   ├── __init__.py
│   ├── types.py                  # BacktestConfig, TimeStep, ConvictionScore, DecisionLog
│   ├── engine.py                 # BacktestEngine（タイムステップ制御）
│   ├── pit_data.py               # PointInTimeDataManager
│   ├── anonymizer.py             # TickerAnonymizer
│   ├── metrics.py                # IC計算、ローリング指標、ベンチマーク比較
│   ├── debate.py                 # DebateProtocol（Phase 2）
│   ├── postmortem.py             # PostmortemAnalyzer（Phase 2）
│   ├── contamination.py          # ContaminationDetector（Phase 2）
│   └── reporting.py              # FMレポート生成
├── screening/                    # 新規パッケージ
│   ├── __init__.py
│   └── screener.py               # UniverseScreener（ファクターベース）
└── optimization/                 # 新規パッケージ（Phase 2）
    ├── __init__.py
    └── optimizer.py              # ConvictionWeightedOptimizer

.claude/agents/mas-invest/        # 新規エージェント群
├── mas-invest-lead.md            # オーケストレータ（dr-stock-leadパターン踏襲）
├── fundamental-analyst.md        # SEC Filings分析
├── valuation-analyst.md          # DCF・相対バリュエーション（Phase 2）
├── sentiment-analyst.md          # Transcript・ニュース分析（Phase 2）
├── macro-analyst.md              # レジーム判定（Phase 2）
├── bull-advocate.md              # ディベート：賛成側（Phase 2）
├── bear-advocate.md              # ディベート：反対側（Phase 2）
├── fund-manager.md               # 最終判断
├── risk-manager.md               # リスク制約（Phase 2）
├── portfolio-constructor.md      # ウェイト最適化（Phase 2）
└── postmortem-analyst.md         # 失敗パターン分析（Phase 2）

.claude/skills/mas-invest/        # 新規スキル
├── SKILL.md
└── templates/
    ├── decision-log.json
    ├── debate-transcript.json
    └── portfolio-report.md

.claude/commands/
├── mas-invest-backtest.md        # /mas-invest-backtest コマンド（Phase 3）
└── mas-invest-portfolio.md       # /mas-invest-portfolio コマンド（Phase 3）
```

---

## 8. 主要な再利用ファイル

| ファイル                                        | 用途                                     |
| ----------------------------------------------- | ---------------------------------------- |
| `src/strategy/risk/calculator.py`               | Sharpe, Sortino, MDD, Beta, IR 計算      |
| `src/factor/core/base.py`                       | Factor抽象基底クラス（スクリーニング用） |
| `src/factor/core/normalizer.py`                 | ファクタースコア正規化（Z-score）        |
| `src/factor/analysis/ic.py`                     | Information Coefficient 計算             |
| `src/edgar/batch.py`                            | 並列SEC Filing取得パターン               |
| `src/edgar/extractors/section_extractor.py`     | 10-K セクション抽出                      |
| `src/market/yfinance/fetcher.py`                | 株価・財務データ取得                     |
| `src/market/fred/fetcher.py`                    | マクロ指標取得                           |
| `.claude/agents/deep-research/dr-stock-lead.md` | Agent Teamsオーケストレーションパターン  |

---

## 9. 検証方法

### Phase 1 MVP の検証

1. **単体テスト**: `PointInTimeDataManager`, `TickerAnonymizer`, `UniverseScreener` のユニットテスト
2. **統合テスト**: 1銘柄について Phase 2（分析）→ Phase 4（判断）のend-to-end実行
3. **バックテスト実行**: 2024年4四半期分のバックテストを実行し、`BacktestResult` を生成
4. **パフォーマンス確認**: Sharpe, Sortino, MDD をSPYベンチマークと比較
5. **透明性確認**: 各銘柄の `decision_log.json` に投資根拠が構造化されていること
6. **バイアス確認**: カットオフ前期間で匿名化が正しく動作していること（ティッカーがログに漏れていないこと）
