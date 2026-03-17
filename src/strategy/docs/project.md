# strategy プロジェクト

## 概要

ポートフォリオ管理・分析・最適化を行う Python ライブラリ。
個別株、ETF、投資信託を組み合わせたポートフォリオの構成分析、リスク指標計算、
リバランスシミュレーションを提供する。

**主な用途:**
- note記事の分析素材としてポートフォリオ分析結果を活用
- 個人の投資判断支援（ポートフォリオ管理・分析）
- 投資戦略の学習と検証（教育・シミュレーション）

## 主要機能

### 基盤機能（Infrastructure）
- [x] 共通型定義（types.py） [#104](https://github.com/YH-05/quants/issues/104) ✅ Done
- [x] エラー・警告クラス（errors.py） [#106](https://github.com/YH-05/quants/issues/106) ✅ Done
- [x] DataProvider プロトコル [#107](https://github.com/YH-05/quants/issues/107) ✅ Done
- [x] MarketAnalysisProvider [#111](https://github.com/YH-05/quants/issues/111) ✅ Done

### ポートフォリオ管理（Portfolio Management）
- [x] ポートフォリオ構成の定義（ティッカー + 比率） [#112](https://github.com/YH-05/quants/issues/112) ✅ Done
- [x] 資産配分の計算と可視化（円グラフ、棒グラフ） [#121](https://github.com/YH-05/quants/issues/121) ✅ Done
- [x] セクター・資産クラス別の構成分析 [#112](https://github.com/YH-05/quants/issues/112) ✅ Done

### リスク分析（Risk Analysis）
- [x] ボラティリティ（標準偏差） [#113](https://github.com/YH-05/quants/issues/113) ✅ Done
- [x] シャープレシオ [#113](https://github.com/YH-05/quants/issues/113) ✅ Done
- [x] ソルティノレシオ [#113](https://github.com/YH-05/quants/issues/113) ✅ Done
- [x] 最大ドローダウン [#114](https://github.com/YH-05/quants/issues/114) ✅ Done
- [x] VaR（バリューアットリスク） [#114](https://github.com/YH-05/quants/issues/114) ✅ Done
- [x] ベータ値 [#118](https://github.com/YH-05/quants/issues/118) ✅ Done
- [x] トレイナーレシオ [#118](https://github.com/YH-05/quants/issues/118) ✅ Done
- [x] 情報レシオ [#118](https://github.com/YH-05/quants/issues/118) ✅ Done

### リバランス機能（Rebalancing）
- [x] 配分ドリフトの検出と可視化 [#119](https://github.com/YH-05/quants/issues/119) ✅ Done [#121](https://github.com/YH-05/quants/issues/121)
- [ ] リバランスコスト計算（取引コスト、税金影響）
- [ ] リバランスタイミング分析

### 期間設定（Period Configuration）
- [x] プリセット期間（1年、3年、5年） [#104](https://github.com/YH-05/quants/issues/104) ✅ Done
- [x] カスタム期間（開始日・終了日指定） [#104](https://github.com/YH-05/quants/issues/104) ✅ Done

### データ出力（Export）
- [x] pandas DataFrame [#120](https://github.com/YH-05/quants/issues/120) ✅ Done
- [x] JSON/辞書形式（AIエージェント向け） [#120](https://github.com/YH-05/quants/issues/120) ✅ Done
- [x] Plotlyチャート [#121](https://github.com/YH-05/quants/issues/121) ✅ Done
- [x] レポートテキスト（マークダウン） [#120](https://github.com/YH-05/quants/issues/120) ✅ Done
- [x] marimoノートブック連携（出力フォーマッタ） [#120](https://github.com/YH-05/quants/issues/120) ✅ Done
- [x] marimoノートブック連携（可視化） [#121](https://github.com/YH-05/quants/issues/121) ✅ Done

### 将来実装（Future）
- [ ] トレーディング戦略の基盤（戦略インターフェース、シグナル生成）
- [ ] バックテストエンジン
- [ ] 最適化アルゴリズム（平均分散、リスクパリティ、Black-Litterman等）

## 技術的考慮事項

### 技術スタック
- **データ取得**: market_analysis パッケージ（疎結合、インターフェース経由）
- **データ処理**: pandas, numpy
- **可視化**: plotly, marimo
- **数値計算**: scipy（統計計算）

### 制約・依存関係
- Python 3.12+
- market_analysis パッケージとの連携（インターフェース経由）
- yfinance の API レート制限に注意（market_analysis 経由）

### アーキテクチャ方針
- market_analysis との疎結合（DataProvider インターフェース経由）
- 入力形式: ティッカー + 比率のリスト
- 出力形式: 複数フォーマット対応（DataFrame, JSON, Chart, Text）

## 成功基準

1. **機能完成度**
   - ポートフォリオ構成を入力として各種リスク指標が計算できる
   - リバランスシミュレーションが動作する
   - 分析結果を複数形式で出力できる

2. **品質基準**
   - TDD で開発（全機能に Red-Green-Refactor を適用）
   - テストカバレッジ 80% 以上
   - 型チェック（pyright）エラーなし
   - ドキュメント完備

3. **連携性**
   - market_analysis パッケージと疎結合で連携
   - marimo ノートブックから利用可能
   - AIエージェント向け JSON 出力

---

> このファイルは `/new-project @src/strategy/docs/project.md` で詳細化されました
