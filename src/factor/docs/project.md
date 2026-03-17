# factor プロジェクト

**GitHub Project**: [#13](https://github.com/users/YH-05/projects/13)
**ステータス**: 完了
**作成日**: 2026-01-15
**完了日**: 2026-01-17

## 概要

カスタムファクター開発のための統合フレームワーク。
ファクターの定義・計算・検証・バックテストを一貫して行い、
投資戦略への連携を可能にする Python ライブラリ。

**主な用途:**
- カスタムファクターの定義（設定ファイル + Python コード）
- ファクター値の計算と正規化
- IC/IR、分位分析、回帰分析による統計的検証
- 過去データでのバックテストとパフォーマンス評価
- strategy パッケージへのシグナル出力

## 主要機能

### ファクター定義（Factor Definition）
- [ ] 設定ファイル（YAML/JSON）ベースのファクター定義
- [ ] Python コードによる複雑なファクター実装
- [ ] ハイブリッドアプローチ（基本は設定、複雑なものはコード）
- [ ] ビルトインファクター（バリュー、モメンタム、クオリティ等）

### データ抽象化（Data Abstraction）
- [ ] 共通データインターフェース（DataProvider）の定義
- [ ] yfinance アダプター
- [ ] FRED アダプター
- [ ] Factset / Bloomberg 等の拡張ポイント
- [ ] market_analysis パッケージとの連携

### ファクター計算（Factor Calculation）
- [ ] クロスセクショナル正規化（z-score、ランク）
- [ ] 時系列変換（変化率、移動平均）
- [ ] 欠損値処理
- [ ] ユニバース管理

### ファクター検証（Factor Validation）
- [ ] IC（Information Coefficient）/ IR（Information Ratio）
- [ ] 分位分析（Quantile Analysis）
- [ ] 回帰分析（Factor Regression）
- [ ] 統計的有意性の検定

### バックテスト（Backtesting）
- [ ] シンプルなファクターポートフォリオ構築
- [ ] リバランス頻度の設定
- [ ] コスト考慮（取引コスト、スリッページ）
- [ ] パフォーマンス指標（シャープレシオ、最大DD等）

### 出力・連携（Output & Integration）
- [ ] レポート生成（Markdown/PDF）
- [ ] チャート可視化（ファクターリターン、IC推移）
- [ ] API形式（DataFrame/JSON）での出力
- [ ] strategy パッケージへのシグナル連携

## 技術的考慮事項

### 技術スタック
- **データ処理**: pandas, numpy
- **統計分析**: scipy, statsmodels
- **可視化**: plotly, matplotlib
- **設定管理**: pydantic（スキーマ検証）
- **永続化**: SQLite（キャッシュ）、Parquet（大規模データ）

### 制約・依存関係
- Python 3.12+
- データソースは抽象インターフェースで分離
- market_analysis との疎結合を維持
- 大規模データ（数千銘柄 × 数年）の効率的処理

### 対象市場
- **日本株式**: 日経225、TOPIX 構成銘柄
- **米国株式**: S&P500、Russell 2000 構成銘柄
- **グローバル**: その他主要市場（拡張可能）

### データソース拡張性
- 抽象インターフェース（DataProvider）により任意のデータソースを接続可能
- 初期実装: yfinance、FRED
- 将来拡張: Factset、Bloomberg、Refinitiv 等

## 成功基準

1. **機能完成度**
   - 基本ファクター（モメンタム、バリュー）が正しく計算される
   - IC/IR の検証結果が妥当な範囲
   - バックテストが正常に動作する

2. **品質基準**
   - テストカバレッジ 80% 以上
   - 型チェック（pyright）エラーなし
   - ドキュメント完備

3. **拡張性**
   - 新しいデータソースを容易に追加可能
   - カスタムファクターを簡単に定義可能
   - strategy パッケージとシームレスに連携

---

## Worktree 並列開発計画

### feature/factor-foundation ブランチ
基盤機能の実装（Wave 1-2）

| Issue | タイトル | 優先度 | 見積もり | ステータス |
|-------|---------|--------|---------|----------|
| [#105](https://github.com/YH-05/quants/issues/105) | T01: 型定義 (types.py) | P0 | 1-2h | ✅ Done |
| [#108](https://github.com/YH-05/quants/issues/108) | T02: エラー型定義 (errors.py) | P0 | 0.5-1h | ✅ Done |
| [#109](https://github.com/YH-05/quants/issues/109) | T03: ロギング設定 | P0 | 0.5h | ✅ Done |
| [#110](https://github.com/YH-05/quants/issues/110) | T04: DataProvider Protocol | P0 | 1h | ✅ Done |
| [#115](https://github.com/YH-05/quants/issues/115) | T05: Cache クラス | P0 | 1-2h | ✅ Done |
| [#116](https://github.com/YH-05/quants/issues/116) | T06: YFinanceProvider | P0 | 2-3h | ✅ Done |

**依存関係**: T01, T02 -> T04 -> T06, T05 -> T06

### feature/factor-core ブランチ
コア機能の実装（Wave 3）

| Issue | タイトル | 優先度 | 見積もり | ステータス |
|-------|---------|--------|---------|----------|
| [#117](https://github.com/YH-05/quants/issues/117) | T07: Factor 基底クラス | P0 | 1-2h | ✅ Done |
| [#122](https://github.com/YH-05/quants/issues/122) | T08: Normalizer クラス | P0 | 1-2h | ✅ Done |

**依存関係**: feature/factor-foundation -> T07 -> T08

### feature/factor-price ブランチ
価格ベースファクターの実装（Wave 4）

| Issue | タイトル | 優先度 | 見積もり | ステータス |
|-------|---------|--------|---------|----------|
| [#123](https://github.com/YH-05/quants/issues/123) | T09: MomentumFactor | P0 | 1h | ✅ Done |
| [#124](https://github.com/YH-05/quants/issues/124) | T10: ReversalFactor | P0 | 0.5h | ✅ Done |
| [#125](https://github.com/YH-05/quants/issues/125) | T11: VolatilityFactor | P0 | 0.5h | ✅ Done |

**依存関係**: feature/factor-core -> T09, T10, T11

### feature/factor-fundamental ブランチ
ファンダメンタルファクターの実装（Wave 4）

| Issue | タイトル | 優先度 | 見積もり | ステータス |
|-------|---------|--------|---------|----------|
| [#126](https://github.com/YH-05/quants/issues/126) | T12: ValueFactor | P0 | 1-1.5h | ✅ Done |
| [#127](https://github.com/YH-05/quants/issues/127) | T13: CompositeValueFactor | P0 | 1h | ✅ Done |
| [#128](https://github.com/YH-05/quants/issues/128) | T14: QualityFactor | P0 | 1-1.5h | ✅ Done |
| [#129](https://github.com/YH-05/quants/issues/129) | T15: CompositeQualityFactor | P0 | 1h | ✅ Done |
| [#130](https://github.com/YH-05/quants/issues/130) | T16: SizeFactor | P0 | 0.5-1h | ✅ Done |

**依存関係**: feature/factor-core -> T12, T14, T16; T08, T12 -> T13; T08, T14 -> T15

### feature/factor-validation ブランチ
検証機能の実装（Wave 5-6）

| Issue | タイトル | 優先度 | 見積もり | ステータス |
|-------|---------|--------|---------|----------|
| [#131](https://github.com/YH-05/quants/issues/131) | T17: ICAnalyzer | P0 | 1-2h | ✅ Done |
| [#132](https://github.com/YH-05/quants/issues/132) | T18: QuantileAnalyzer | P0 | 1-2h | ✅ Done |
| [#133](https://github.com/YH-05/quants/issues/133) | T19: ファクターカテゴリ拡張 | P0 | 1h | ✅ Done |
| [#134](https://github.com/YH-05/quants/issues/134) | T20: パッケージエクスポート | P0 | 0.5h | ✅ Done |
| [#135](https://github.com/YH-05/quants/issues/135) | T21: 統合テスト | P0 | 2-3h | ✅ Done |

**依存関係**: T01 -> T17, T18; 全ファクター -> T19 -> T20 -> T21

---

## 進捗サマリー

| ステータス | 件数 |
|----------|------|
| ✅ Done | 21 |
| 🔄 In Progress | 0 |
| Todo | 0 |
| **合計** | 21 |

**最終更新**: 2026-01-23
**更新内容**: GitHub Project #13 と整合性検証・同期（#135 統合テスト完了、プロジェクト完了）

---

> このファイルは `/new-project @src/factor/docs/project.md` で詳細化されました
