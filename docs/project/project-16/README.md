# Project 16: src_sample Migration

## 概要

`src_sample/`のクオンツ分析スクリプト（約 16,000 行）を、既存の`market_analysis`と`factor`パッケージに適合する形で再実装する。

### GitHub Project

-   **Project Number**: 16
-   **URL**: https://github.com/users/YH-05/projects/16

### 方針

-   **ハイブリッドアプローチ**: 既存設計書と src_sample の両方から良い部分を取り入れる
-   **機能単位の分解**: ファイル単位ではなく、関数・クラス単位で適切なパッケージに配置
-   **既存パターン準拠**: BaseDataFetcher、DataProvider Protocol 等の既存インターフェースに従う

---

## src_sample 詳細分析

### 主要ファイルと機能

| ファイル                       | 行数  | 主要機能                                           | 複雑度 |
| ------------------------------ | ----- | -------------------------------------------------- | ------ |
| `bloomberg_utils.py`           | 2,374 | BlpapiCustom (24 メソッド) - Bloomberg API 連携    | 高     |
| `factset_utils.py`             | 2,131 | 17 関数 + FactorJobArgs - FactSet 連携             | 高     |
| `ROIC_make_data_files_ver2.py` | 2,433 | リターン計算、ランキング、Z-score、ROIC 遷移ラベル | 高     |
| `make_factor.py`               | 365   | OLS 直交化、マクロファクター構築、ローリングベータ | 中     |
| `us_treasury.py`               | 869   | イールドカーブ PCA、符号整列、可視化               | 中     |
| `fred_database_utils.py`       | 277   | FredDataProcessor - UPSERT、差分更新               | 低     |
| `roic_analysis.py`             | 245   | PerformanceAnalyzer - Quantile 分析                | 低     |

### コアアルゴリズム

1. **直交化** (`make_factor.py:22-49`): OLS 残差による多段階ファクター直交化
2. **PCA** (`us_treasury.py:576-659`): イールドカーブ 3 成分分解 + 符号整列
3. **ランキング** (`ROIC_make_data_files_ver2.py:775-1075`): quintile, percentile, z-score
4. **リターン計算** (`ROIC_make_data_files_ver2.py:320-448`): 1M〜5Y、フォワード、アクティブ、年率化
5. **ROIC 遷移ラベル** (`ROIC_make_data_files_ver2.py:1113-1386`): "remain high", "move to high" 等

### 既存パッケージの状態

-   **market_analysis**: 成熟（BaseDataFetcher、types.py 556 行、errors.py 9 種類の例外完備）
-   **factor**: スケルトン（types.py 107 行のみ、core/は空）

---

## ファイル分解マップ

### データ取得 → market_analysis

| src_sample               | 移行先                         | 主要機能                                 |
| ------------------------ | ------------------------------ | ---------------------------------------- |
| `bloomberg_utils.py`     | `core/bloomberg_fetcher.py`    | BloombergFetcher（BaseDataFetcher 継承） |
| `factset_utils.py`       | `core/factset_fetcher.py`      | FactSetFetcher + 構成銘柄ロード          |
| `fred_database_utils.py` | `core/fred_fetcher.py`（拡張） | UPSERT、差分更新機能を追加               |
| `database_utils.py`      | `finance/db/sqlite_client.py`  | 汎用 DB 操作は共通インフラへ             |

### データ加工 → factor

| src_sample                        | 移行先                                   | 主要機能                         |
| --------------------------------- | ---------------------------------------- | -------------------------------- |
| `ROIC_make_data_files_ver2.py`    | 下記に分解                               |                                  |
| ├ リターン計算関数                | `factor/core/return_calculator.py`       | forward return, 複数期間リターン |
| ├ ランキング関数                  | `factor/core/normalizer.py`              | quintile, percentile, zscore     |
| └ ROIC 遷移ラベル                 | `factor/factors/quality/roic_label.py`   | ROIC 遷移分類                    |
| `us_treasury.py`                  | `factor/core/pca.py`                     | PCA 分析、符号整列アルゴリズム   |
| `make_factor.py`                  | 下記に分解                               |                                  |
| ├ orthogonalize()                 | `factor/core/orthogonalization.py`       | 直交化コアアルゴリズム           |
| └ orthogonalize_all_descriptors() | `factor/factors/macro/macro_builder.py`  | マクロファクター構築             |
| `roic_analysis.py`                | `factor/validation/quantile_analyzer.py` | パフォーマンス分析に統合         |

### スコープ外（後回し）

-   `weekly_report_generator.py` - レポート生成
-   `weekly_insights.py` - インサイト生成
-   `google_drive_utils.py` - 外部サービス連携
-   `etf_dot_com.py` - Web スクレイピング
-   `edgar_utils.py` - SEC EDGAR（30 行のスタブのみ）

---

## 新規ディレクトリ構造

### market_analysis 追加分

```
src/market_analysis/
├── core/
│   ├── bloomberg_fetcher.py    # NEW
│   ├── factset_fetcher.py      # NEW
│   └── mock_fetchers.py        # NEW (テスト用)
└── types.py                    # 拡張: DataSource, IdentifierType
```

### factor 追加分

```
src/factor/
├── core/
│   ├── normalizer.py           # NEW (zscore, rank, winsorize)
│   ├── return_calculator.py    # NEW (リターン計算)
│   ├── orthogonalization.py    # NEW (直交化)
│   └── pca.py                  # NEW (PCA分析)
├── factors/
│   ├── quality/
│   │   ├── roic.py             # NEW (ROICファクター)
│   │   └── roic_label.py       # NEW (ROIC遷移ラベル)
│   └── macro/
│       ├── base.py             # NEW (BaseMacroFactor)
│       ├── interest_rate.py    # NEW (Level, Slope, Curvature)
│       ├── flight_to_quality.py # NEW
│       ├── inflation.py        # NEW
│       └── macro_builder.py    # NEW (統合ビルダー)
├── validation/
│   ├── ic_analyzer.py          # NEW
│   └── quantile_analyzer.py    # NEW
├── types.py                    # 拡張: FactorConfig, FactorResult等
├── errors.py                   # NEW
└── enums.py                    # NEW
```

---

## Wave 別実装計画（修正版）

### Wave 0: 基盤整備（1 日）- Issue: [#256](https://github.com/YH-05/quants/issues/256)

**優先度**: P0 (high) - 全 Wave の前提条件

**実装ファイル**:

```
src/factor/
├── types.py          # 拡張: FactorConfig, FactorResult, OrthogonalizationResult
├── errors.py         # NEW: FactorError, InsufficientDataError等
└── enums.py          # NEW: FactorCategory, NormalizationMethod

src/market_analysis/types.py  # 拡張: DataSource (BLOOMBERG, FACTSET追加)
```

**検証**: `make typecheck` 成功

---

### Wave 1-3: コアアルゴリズム（7 日）- Issue: [#257](https://github.com/YH-05/quants/issues/257)

**優先度**: P0 (high) - Wave 4-6 の前提条件
**依存**: Wave 0

#### Wave 1: 正規化アルゴリズム（2 日）

| タスク                       | ファイル                    | 元ソース                             |
| ---------------------------- | --------------------------- | ------------------------------------ |
| Normalizer.zscore()          | `factor/core/normalizer.py` | ROIC_make_data_files_ver2.py:775-850 |
| Normalizer.percentile_rank() | 同上                        | 同上:850-900                         |
| Normalizer.quintile_rank()   | 同上                        | 同上:900-950                         |
| Normalizer.winsorize()       | 同上                        | 同上:950-1000                        |
| normalize_by_group()         | 同上                        | 同上:1000-1075                       |

#### Wave 2: リターン計算（2 日）

| タスク                      | ファイル                           | 元ソース                             |
| --------------------------- | ---------------------------------- | ------------------------------------ |
| calculate_returns()         | `factor/core/return_calculator.py` | ROIC_make_data_files_ver2.py:320-380 |
| calculate_forward_returns() | 同上                               | 同上:380-420                         |
| annualize_return()          | 同上                               | 同上:420-448                         |
| calculate_active_return()   | 同上                               | calculate_performance_metrics.py     |

#### Wave 3: 直交化・PCA（3 日）

| タスク                                 | ファイル                           | 元ソース               |
| -------------------------------------- | ---------------------------------- | ---------------------- |
| Orthogonalizer.orthogonalize()         | `factor/core/orthogonalization.py` | make_factor.py:22-49   |
| Orthogonalizer.orthogonalize_cascade() | 同上                               | make_factor.py:53-109  |
| YieldCurvePCA.fit_transform()          | `factor/core/pca.py`               | us_treasury.py:576-620 |
| YieldCurvePCA.align_signs()            | 同上                               | us_treasury.py:620-659 |

---

### Wave 4: マクロファクター（3 日）- Issue: [#260](https://github.com/YH-05/quants/issues/260)

**優先度**: P1 (medium) - Wave 5 と並列実行可能
**依存**: Wave 1-3

| タスク                                 | ファイル                                    | 元ソース                        |
| -------------------------------------- | ------------------------------------------- | ------------------------------- |
| BaseMacroFactor                        | `factor/factors/macro/base.py`              | -                               |
| InterestRateFactor                     | `factor/factors/macro/interest_rate.py`     | make_factor.py + us_treasury.py |
| FlightToQualityFactor                  | `factor/factors/macro/flight_to_quality.py` | make_factor.py:164-173          |
| InflationFactor                        | `factor/factors/macro/inflation.py`         | make_factor.py:175-181          |
| MacroFactorBuilder.build_all_factors() | `factor/factors/macro/macro_builder.py`     | make_factor.py:113-195          |

**出力**: Factor_Market, Factor_Level, Factor_Slope, Factor_Curvature, Factor_FtoQ, Factor_Inflation

---

### Wave 5: データフェッチャー（4 日）- Issue: [#258](https://github.com/YH-05/quants/issues/258)

**優先度**: P1 (medium) - Wave 4 と並列実行可能
**依存**: Wave 0

| タスク               | ファイル                                    | 元ソース           |
| -------------------- | ------------------------------------------- | ------------------ |
| BloombergFetcher     | `market_analysis/core/bloomberg_fetcher.py` | bloomberg_utils.py |
| FactSetFetcher       | `market_analysis/core/factset_fetcher.py`   | factset_utils.py   |
| MockBloombergFetcher | `market_analysis/core/mock_fetchers.py`     | -                  |
| MockFactSetFetcher   | 同上                                        | -                  |

**リスク対策**: 環境変数 `BLOOMBERG_AVAILABLE`/`FACTSET_AVAILABLE` でテスト分岐

---

### Wave 6: ROIC・品質ファクター（3 日）- Issue: [#259](https://github.com/YH-05/quants/issues/259)

**優先度**: P1 (medium)
**依存**: Wave 1-3

| タスク                                   | ファイル                               | 元ソース                     |
| ---------------------------------------- | -------------------------------------- | ---------------------------- |
| ROICFactor.calculate_ranks()             | `factor/factors/quality/roic.py`       | ROIC_make_data_files_ver2.py |
| ROICFactor.add_shifted_values()          | 同上                                   | 同上:1000-1112               |
| ROICTransitionLabeler.label_transition() | `factor/factors/quality/roic_label.py` | 同上:1113-1386               |

**ROIC 遷移ラベル**: "remain high", "remain low", "move to high", "drop to low", "others"

---

### Wave 7: 検証・分析ツール（2 日）- Issue: [#261](https://github.com/YH-05/quants/issues/261)

**優先度**: P2 (low)
**依存**: Wave 4, 6

| タスク                                     | ファイル                                 | 元ソース                |
| ------------------------------------------ | ---------------------------------------- | ----------------------- |
| ICAnalyzer.calculate_ic()                  | `factor/validation/ic_analyzer.py`       | 設計書                  |
| QuantileAnalyzer.analyze_by_quantile()     | `factor/validation/quantile_analyzer.py` | roic_analysis.py:17-245 |
| QuantileAnalyzer.calculate_spread_return() | 同上                                     | 同上                    |

---

### Wave 8: 統合・回帰テスト（3 日）- Issue: [#262](https://github.com/YH-05/quants/issues/262)

**優先度**: P2 (low)
**依存**: Wave 1-7

**テスト構成**:

```
tests/factor/
├── integration/
│   ├── test_macro_factor_pipeline.py
│   ├── test_roic_pipeline.py
│   └── test_end_to_end.py
└── regression/
    ├── test_normalizer_regression.py
    ├── test_orthogonalization_regression.py
    └── fixtures/
        ├── expected_orthogonalized.parquet
        └── expected_pca_scores.parquet
```

**回帰テスト手順**:

1. src_sample で出力生成（1 回のみ）
2. Parquet 形式で fixtures/に保存
3. 新実装と比較（許容誤差: 1e-10）

---

## 依存関係グラフ

```
Wave 0 (型定義)
    ↓
Wave 1 (正規化) ───────────────────────┐
    ↓                                   │
Wave 2 (リターン計算)                    │
    ↓                                   │
Wave 3 (直交化・PCA)                    │
    ↓                                   │
Wave 4 (マクロファクター) ←─────────────┤
    ↓                    並列可能        │
Wave 5 (フェッチャー) ←─────────────────┤
    ↓                                   │
Wave 6 (ROIC・品質) ←───────────────────┘
    ↓
Wave 7 (検証ツール)
    ↓
Wave 8 (統合テスト)
```

**並列実行可能**:

-   Wave 4 と Wave 5（マクロファクターとフェッチャーは独立）
-   Wave 4 と Wave 6（マクロファクターと ROIC ファクターは独立）

---

## 検証計画

### 単体テスト

```bash
# 各Waveの完了後に実行
make check-all
```

### 回帰テスト

```python
# 元のsrc_sampleスクリプトの出力と比較
def test_orthogonalization_matches_original():
    """make_factor.pyのorthogonalize()と同一出力を確認"""

def test_pca_matches_original():
    """us_treasury.pyのPCA結果と同一出力を確認"""
```

### 統合テスト（環境依存）

```bash
# Bloomberg環境がある場合
BLOOMBERG_AVAILABLE=true pytest tests/market_analysis/integration/ -v
```

---

## リスクと緩和策

| リスク                     | 緩和策                               |
| -------------------------- | ------------------------------------ |
| Bloomberg/FactSet 環境不在 | モックフェッチャー + 環境変数分岐    |
| 大規模データ性能           | チャンク処理オプション + Polars 検討 |
| 既存 API への破壊的変更    | DataSource enum 拡張は後方互換       |
| src_sample のパス問題      | 相対インポート → 絶対パス変換        |

---

## 想定工数

| Wave     | 内容                                             | 見積もり  |
| -------- | ------------------------------------------------ | --------- |
| Wave 0   | 型定義・エラー定義                               | 1 日      |
| Wave 1-3 | コアアルゴリズム（正規化、リターン、直交化/PCA） | 7 日      |
| Wave 4   | マクロファクター                                 | 3 日      |
| Wave 5   | データフェッチャー                               | 4 日      |
| Wave 6   | ROIC・品質ファクター                             | 3 日      |
| Wave 7   | 検証・分析ツール                                 | 2 日      |
| Wave 8   | 統合・回帰テスト                                 | 3 日      |
| **合計** |                                                  | **23 日** |

---

## 進捗状況

| Wave     | Issue                                               | 優先度 | ステータス | 開始日     | 完了日     |
| -------- | --------------------------------------------------- | ------ | ---------- | ---------- | ---------- |
| Wave 0   | [#256](https://github.com/YH-05/quants/issues/256) | P0     | Done       | 2026-01-16 | 2026-01-16 |
| Wave 1-3 | [#257](https://github.com/YH-05/quants/issues/257) | P0     | Done       | 2026-01-16 | 2026-01-16 |
| Wave 4   | [#260](https://github.com/YH-05/quants/issues/260) | P1     | Done       | 2026-01-17 | 2026-01-17 |
| Wave 5   | [#258](https://github.com/YH-05/quants/issues/258) | P1     | Done       | 2026-01-16 | 2026-01-16 |
| Wave 6   | [#259](https://github.com/YH-05/quants/issues/259) | P1     | Done       | 2026-01-16 | 2026-01-16 |
| Wave 7   | [#261](https://github.com/YH-05/quants/issues/261) | P2     | -          | -          | -          |
| Wave 8   | [#262](https://github.com/YH-05/quants/issues/262) | P2     | Todo       | -          | -          |

**進捗サマリー**: 5/7 Wave 完了（Wave 7 は Issue 未作成、Wave 8 のみ残）
