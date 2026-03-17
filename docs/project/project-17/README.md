# Project 17: marimo Market Dashboard

## 概要

株式市場・マクロ経済データ確認用のインタラクティブダッシュボードを marimo で実装する。

## ステータス

- **フェーズ**: 完了
- **開始日**: 2026-01-17
- **最終更新**: 2026-01-18

## GitHub Issues

| # | タイトル | ラベル | ステータス |
|---|---------|--------|----------|
| [#304](https://github.com/YH-05/quants/issues/304) | marimo app 基本骨格実装 | enhancement | Done |
| [#305](https://github.com/YH-05/quants/issues/305) | Tab 1: パフォーマンス概要実装 | enhancement | Done |
| [#306](https://github.com/YH-05/quants/issues/306) | Tab 2: マクロ指標実装 | enhancement | Done |
| [#307](https://github.com/YH-05/quants/issues/307) | Tab 3: 相関・ベータ分析実装 | enhancement | Done |
| [#308](https://github.com/YH-05/quants/issues/308) | Tab 4: リターン分布実装 | enhancement | Done |
| [#309](https://github.com/YH-05/quants/issues/309) | 統合テスト・動作確認 | test | Done |

## 目標

`notebook_sample/Market-Report2.py` を参考に、既存の `src/market_analysis/` ライブラリを活用したインタラクティブダッシュボードを作成する。

## 機能要件

### Tab 1: パフォーマンス概要
- S&P500 & 主要指数のパフォーマンス
- Magnificent 7 & SOX指数
- セクターETF（XL系）
- 貴金属

### Tab 2: マクロ指標
- 米国金利（10Y, 2Y, FF）
- イールドスプレッド
- VIX & ハイイールドスプレッド

### Tab 3: 相関・ベータ分析
- セクターETFローリングベータ（vs S&P500）
- ドルインデックス vs 貴金属相関
- 相関ヒートマップ

### Tab 4: リターン分布
- 週次リターンヒストグラム
- 統計サマリー

## 技術仕様

### 使用API

| API | 用途 |
|-----|------|
| `MarketData.fetch_stock()` | 株価・指数データ取得 |
| `MarketData.fetch_fred()` | FRED経済指標取得 |
| `MarketData.fetch_commodity()` | 貴金属データ取得 |
| `PRESET_GROUPS` | ティッカーグループ |
| `CorrelationAnalyzer.calculate_rolling_beta()` | ローリングベータ |
| `CorrelationAnalyzer.calculate_rolling_correlation()` | ローリング相関 |

### marimo UI要素

| UI | 用途 |
|----|------|
| `mo.ui.dropdown` | 期間選択（1M, 3M, 6M, 1Y, 2Y, 5Y） |
| `mo.ui.slider` | ローリング窓サイズ |
| `mo.ui.tabs` | セクション切替 |

### FRED シリーズID

| 指標 | シリーズID |
|-----|-----------|
| 10年国債 | DGS10 |
| 2年国債 | DGS2 |
| FF金利 | DFF |
| ハイイールドスプレッド | BAMLH0A0HYM2 |
| 経済不確実性指数 | USEPUINDXD |
| ドルインデックス | DTWEXAFEGS |

## 実装ファイル

```
notebook/
└── market_dashboard.py    # メインダッシュボード
```

## 環境要件

- `FRED_API_KEY` 環境変数（FRED データ取得に必要）
- marimo >= 0.19.2

## 検証方法

```bash
marimo edit notebook/market_dashboard.py
```

## 関連リソース

- GitHub Project: #17
- 参考実装: `notebook_sample/Market-Report2.py`
- 既存API: `src/market_analysis/`
