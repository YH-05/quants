# note金融コンテンツ発信強化プロジェクト

**GitHub Project**: [#11](https://github.com/users/YH-05/projects/11)
**ステータス**: 完了
**作成日**: 2026-01-14
**完了日**: 2026-01-15

## 概要

noteでの金融市場調査・投資調査コンテンツ発信を強化するための機能追加・ワークフロー改善プロジェクト。

### 背景

現在のfinanceプロジェクトは以下の機能を実装済み：
- market_analysisパッケージ（yfinance/FRED連携、テクニカル分析、可視化）
- 金融記事作成ワークフロー（20エージェント、5カテゴリテンプレート）
- RSSフィード管理

しかし、以下の機能が不足している：
- 米国企業の決算・財務データ分析（SEC EDGAR）
- ニュース・SNSのセンチメント分析
- 市場データ分析の標準化された方針
- マガジン運営の明文化されたガイドライン

## 目標

1. **SEC EDGAR統合** - 米国企業決算分析の自動化
2. **センチメント分析** - マーケット心理の可視化
3. **市場分析方針の標準化** - インデックス、スタイルチルト、セクター、Mag7の定期分析
4. **マガジン運営方針の明文化** - カテゴリ構成、ターゲット読者層、コンテンツガイドライン
5. **ワークフローの簡素化** - エンドツーエンドの統合コマンド

---

## スコープ

### 新規作成ファイル

| ファイル | 説明 | Phase |
|---------|------|-------|
| `.claude/agents/finance-sec-filings.md` | SEC EDGARエージェント | 1 |
| `.claude/agents/finance-sentiment-analyzer.md` | センチメント分析エージェント | 2 |
| `data/schemas/sec-filings.schema.json` | SEC決算スキーマ | 1 |
| `data/schemas/sentiment.schema.json` | センチメントスキーマ | 2 |
| `docs/market-analysis-guidelines.md` | 市場分析ガイドライン | 3 |
| `docs/note-magazine-strategy.md` | マガジン運営戦略 | 4 |
| `.claude/commands/finance-full.md` | 統合コマンド | 5 |

### 修正ファイル

| ファイル | 変更内容 | Phase |
|---------|---------|-------|
| `.claude/commands/finance-research.md` | SEC EDGAR・センチメント統合 | 1, 2 |
| `src/market_analysis/utils/ticker_registry.py` | スタイルファクター追加 | 3 |

---

## 実装計画

### Phase 1: SEC EDGAR統合

**目的**: MCP経由でSEC EDGARデータを金融リサーチに統合

#### 新規エージェント: finance-sec-filings

```
入力: article-meta.json（symbols）
出力: 01_research/sec_filings.json

処理内容:
1. 対象銘柄のCIK（SEC識別子）取得
2. 最新10-K/10-Q取得
3. 財務データ（売上、利益、EPS等）抽出
4. 8-K（重要イベント）確認
5. インサイダー取引（Form 4）サマリー
```

**使用MCPツール**:
- `mcp__sec-edgar-mcp__get_cik_by_ticker`
- `mcp__sec-edgar-mcp__get_financials`
- `mcp__sec-edgar-mcp__get_recent_filings`
- `mcp__sec-edgar-mcp__analyze_8k`
- `mcp__sec-edgar-mcp__get_insider_summary`

---

### Phase 2: センチメント分析

**目的**: 収集したニュース/RSSフィードに感情スコアを付与

#### 新規エージェント: finance-sentiment-analyzer

```
入力: sources.json, raw-data.json
出力: 01_research/sentiment.json

処理内容:
1. 各ソースのテキストを分析
2. ポジティブ/ネガティブ/中立を判定（0-100スコア）
3. 銘柄別センチメント集計
4. 市場全体のセンチメントサマリー
5. Fear & Greed風の総合指標生成
```

**出力形式**:
```json
{
  "overall_sentiment": {
    "score": 65,
    "label": "greed",
    "trend": "improving"
  },
  "by_symbol": {
    "AAPL": { "score": 72, "sources": 15, "trend": "stable" }
  },
  "by_topic": {
    "earnings": { "score": 58, "count": 8 },
    "macro": { "score": 45, "count": 12 }
  }
}
```

---

### Phase 3: 市場データ分析方針

**目的**: 定期レポートで使用する分析テンプレートを標準化

#### 週次マーケットレポートの標準分析項目

1. **主要インデックス動向**
   - S&P 500 / NASDAQ / ダウ / 日経225
   - 週間騰落率、YTDパフォーマンス
   - 50日/200日移動平均との乖離

2. **セクター別パフォーマンス**
   - 11セクターETFの週間リターン比較
   - セクターローテーションの兆候

3. **スタイルファクター分析**
   - グロース vs バリュー（VUG vs VTV）
   - 大型 vs 小型（SPY vs IWM）
   - クオリティーファクター（QUAL）

4. **Magnificent 7動向**
   - 7銘柄の週間パフォーマンス
   - 決算発表スケジュール
   - ニュースハイライト

5. **マクロ経済指標**
   - FRED経済指標の更新
   - 金利動向（10年債利回り）
   - 為替（ドル円、ユーロドル）

#### ticker_registry.py への追加

```python
# スタイルファクター
"STYLE_GROWTH": ["VUG", "IWF", "VONG"],
"STYLE_VALUE": ["VTV", "IWD", "VONV"],
"STYLE_QUALITY": ["QUAL", "SPHQ"],
"STYLE_MOMENTUM": ["MTUM", "PDP"],
"STYLE_LOW_VOL": ["SPLV", "USMV"],

# サイズファクター
"SIZE_LARGE": ["SPY", "IVV", "VOO"],
"SIZE_MID": ["IJH", "VO", "IWR"],
"SIZE_SMALL": ["IWM", "VB", "IJR"],
```

---

### Phase 4: マガジン運営方針

**目的**: noteでのコンテンツ発信戦略を明文化

#### マガジン構成案

| マガジン | 頻度 | 内容 | ターゲット | 価格 |
|---------|------|------|-----------|------|
| 週刊マーケットレポート | 毎週月曜 | 先週の市場サマリー、今週の注目 | 初心者〜中級者 | 無料 |
| 銘柄分析レポート | 月2-4回 | 個別銘柄の詳細分析、決算解説 | 中級者 | 有料/無料混在 |
| 投資戦略・教育 | 月2回 | クオンツ分析、投資手法解説 | 上級者 | 有料 |

#### ターゲット読者層

| レベル | 特徴 | ニーズ | 対応カテゴリ |
|--------|------|--------|-------------|
| 初心者 | 投資未経験〜1年 | 基礎知識、用語解説 | investment_education |
| 中級者 | 投資1-5年 | 市場動向、銘柄選定 | market_report, stock_analysis |
| 上級者 | 投資5年以上 | 戦略検証、定量分析 | quant_analysis, economic_indicators |

#### コンテンツガイドライン

**文字数目安**:
- 市場レポート: 2,000-3,000字
- 銘柄分析: 3,000-5,000字
- 教育コンテンツ: 2,500-4,000字
- クオンツ分析: 4,000-6,000字

**トーン&スタイル**:
- 敬体（です・ます調）
- 専門用語は初出時に解説
- 免責事項は必ず記載

**必須要素**:
- サムネイル画像（1200x630px推奨）
- 目次（3000字以上の場合）
- チャート/図表（最低1つ）
- 参考文献/データソース
- 免責事項

**禁止表現**:
- 「買うべき」「売るべき」
- 「絶対」「必ず」「確実に」
- 「おすすめ銘柄」（投資助言に該当）

---

### Phase 5: ワークフロー簡素化

**目的**: コマンド数を削減し、エンドツーエンドを効率化

#### 新規コマンド: /finance-full

```
使用方法:
/finance-full "トピック名" --category market_report

処理フロー:
1. /new-finance-article でフォルダ作成
2. /finance-research でリサーチ実行
3. [HF] 主要な判定確認（decisions.json）
4. /finance-edit --mode quick で初稿作成
5. [HF] 最終確認

オプション:
--depth: リサーチ深度 (shallow|deep|auto)
--mode: 編集モード (quick|full)
```

---

## GitHub Issues

全Issue完了 (2026-01-15)

| # | タイトル | ラベル | Phase | 依存 | ステータス |
|---|---------|--------|-------|------|----------|
| [#95](https://github.com/YH-05/quants/issues/95) | マガジン運営方針ドキュメント作成 | documentation | 1 | - | Done |
| [#96](https://github.com/YH-05/quants/issues/96) | 市場分析ガイドライン作成 | documentation | 2 | - | Done |
| [#97](https://github.com/YH-05/quants/issues/97) | スタイルファクター用プリセット追加 | enhancement | 3 | #96 | Done |
| [#98](https://github.com/YH-05/quants/issues/98) | SEC EDGARエージェント作成 | enhancement | 1 | #99 | Done |
| [#99](https://github.com/YH-05/quants/issues/99) | SEC決算スキーマ作成 | enhancement | 1 (最優先) | - | Done |
| [#100](https://github.com/YH-05/quants/issues/100) | センチメント分析エージェント作成 | enhancement | 2 | #101 | Done |
| [#101](https://github.com/YH-05/quants/issues/101) | センチメントスキーマ作成 | enhancement | 2 (最優先) | - | Done |
| [#102](https://github.com/YH-05/quants/issues/102) | finance-researchへのSEC/センチメント統合 | enhancement | 2 | #98,#100,#101 | Done |
| [#103](https://github.com/YH-05/quants/issues/103) | /finance-full統合コマンド作成 | enhancement | 5 | #95,#96,#97,#98,#99,#100,#101,#102 | Done |

---

## 実装順序（修正版）

### Phase 1: スキーマとドキュメント基礎
1. **#99 SEC決算スキーマ作成** (最優先) - エージェント実装の仕様書
2. **#95 マガジン運営方針ドキュメント作成** - 並列実行可能
3. **#98 SEC EDGARエージェント作成** - #99 完了後

### Phase 2: センチメントと市場分析
4. **#101 センチメントスキーマ作成** (最優先) - エージェント実装の仕様書
5. **#96 市場分析ガイドライン作成** - 並列実行可能
6. **#100 センチメント分析エージェント作成** - #101 完了後
7. **#102 finance-researchへのSEC/センチメント統合** - #98, #100, #101 完了後

### Phase 3: プリセット追加
8. **#97 スタイルファクター用プリセット追加** - #96 完了後

### Phase 4: 最終統合
9. **#103 /finance-full統合コマンド作成** - 全タスク完了後

**修正理由**:
- スキーマをエージェント実装の前に配置（設計 → 実装の順序）
- ドキュメント作成を Phase 1 に移動（並列実行で早期明確化）
- 依存関係の論理的矛盾を解消

---

## 検証方法

### Phase 1検証（SEC EDGAR）
- Claude CodeでSEC EDGARツールを直接呼び出し
- AAPL の最新10-K取得テスト

### Phase 2検証（センチメント）
- テスト記事でリサーチ実行
- sentiment.json 生成確認

### Phase 3-4検証（ドキュメント）
- 週次レポートを1回手動作成し、ガイドラインの実用性確認
- マガジン戦略に沿った記事分類テスト

### Phase 5検証（統合コマンド）
- `/finance-full "S&P500週間レビュー" --category market_report --depth shallow`
- 全工程の一括実行確認

---

## 参考資料

- 詳細プラン: `~/.claude/plans/effervescent-percolating-wombat.md`
- market_analysis実装: `src/market_analysis/`
- 金融エージェント: `.claude/agents/finance-*.md`
- 記事テンプレート: `template/`
