# note執筆ワークフロー包括的技術レポート

**作成日**: 2026-01-19
**対象プロジェクト**: GitHub Project #11 - note金融コンテンツ発信強化
**文書バージョン**: 1.0

---

## 目次

1. [概要](#1-概要)
2. [ワークフロー全体構成](#2-ワークフロー全体構成)
3. [コマンド詳細仕様](#3-コマンド詳細仕様)
4. [エージェント詳細仕様](#4-エージェント詳細仕様)
5. [テンプレート構造](#5-テンプレート構造)
6. [JSONスキーマ定義](#6-jsonスキーマ定義)
7. [データフロー](#7-データフロー)
8. [品質管理システム](#8-品質管理システム)
9. [エラーハンドリング](#9-エラーハンドリング)
10. [並列実行戦略](#10-並列実行戦略)
11. [ヒューマンフィードバック](#11-ヒューマンフィードバック)
12. [ニュース収集システム](#12-ニュース収集システム)
13. [付録](#13-付録)

---

## 1. 概要

### 1.1 システム目的

金融市場の分析からnote.comでの記事公開までを自動化するエンドツーエンドワークフロー。トピック提案、データ収集、分析、執筆、批評、修正の全工程を28のエージェントと6つの統合コマンドで実現する。

### 1.2 主要コンポーネント

| コンポーネント | 数量 | 説明 |
|--------------|------|------|
| 統合コマンド | 6 | ワークフローのエントリーポイント |
| エージェント | 28 | 専門化された処理ユニット |
| テンプレート | 5 | カテゴリ別記事テンプレート |
| JSONスキーマ | 14 | データ構造定義 |

### 1.3 対応記事カテゴリ

| カテゴリ | 対象読者 | 文字数目安 | 用途 |
|---------|---------|-----------|------|
| market_report | intermediate | 3000-5000 | 市場レポート・相場解説 |
| stock_analysis | intermediate | 4000-6000 | 個別銘柄・企業分析 |
| economic_indicators | intermediate | 2500-4000 | 経済指標・マクロ分析 |
| investment_education | beginner | 3000-5000 | 投資教育・基礎知識 |
| quant_analysis | advanced | 4000-6000 | クオンツ分析・戦略検証 |

---

## 2. ワークフロー全体構成

### 2.1 コマンド階層

```
/finance-full（全工程一括実行）
├── /new-finance-article（フォルダ作成）
├── /finance-research（リサーチ）
└── /finance-edit（執筆/批評）

/finance-suggest-topics（トピック提案）
/collect-finance-news（ニュース収集→GitHub Issues）
```

### 2.2 処理フェーズ

```
Phase 0: トピック提案
    ↓
Phase 1: クエリ生成
    ↓
Phase 2: データ収集（並列4エージェント）
    ↓
Phase 3: データ処理
    ↓
Phase 4: 分析・検証（並列5エージェント）
    ↓
Phase 5: 可視化
    ↓
Phase 6: 初稿生成
    ↓
Phase 7: 批評（並列5エージェント）
    ↓
Phase 8: 修正・公開
```

### 2.3 エージェント分類

| 層 | エージェント数 | 役割 |
|----|--------------|------|
| データ収集層 | 4 | クエリ生成、市場データ、Web、Wikipedia |
| データ処理層 | 3 | ソース整理、主張抽出、センチメント |
| 分析層 | 5 | 信頼度評価、ファクトチェック、採用判定、テクニカル、経済 |
| 執筆層 | 2 | 初稿生成、可視化 |
| 批評層 | 5 | 事実、コンプライアンス、構成、データ、読みやすさ |
| 修正層 | 1 | 批評反映修正 |
| トピック層 | 1 | トピック提案 |
| ニュース層 | 7 | オーケストレーター + 5テーマ別 |

---

## 3. コマンド詳細仕様

### 3.1 /new-finance-article

**目的**: 記事フォルダとテンプレートの初期化

#### パラメータ

| パラメータ | 必須 | デフォルト | 型 | 説明 |
|-----------|------|-----------|-----|------|
| トピック名 | ○ | - | string | 記事のテーマ |

#### 処理フロー

**Phase 1: 記事情報収集**
1. トピック名入力（なければユーザー確認）
2. カテゴリ選択（5種類から対話選択）
3. 英語テーマ名生成（ケバブケース）
4. シンボル/指標入力（カテゴリ別）
5. 分析期間入力

**Phase 2: article_id 生成と重複確認**
1. `articles/{category}_*` をスキャン → 最大通番 + 1
2. 形式: `{category}_{seq:03d}_{theme_name_en}`
3. 重複チェック

**Phase 3: フォルダ構造作成**
```bash
mkdir -p articles/{article_id}
cp -r template/{category}/* articles/{article_id}/
```

**Phase 4: メタデータ初期化**
1. `article-meta.json` 生成
2. 7つの空JSONファイルの `article_id` フィールド更新
3. `human_feedback` フィールド初期化

**Phase 5: 完了報告**

#### 出力ファイル

```
articles/{article_id}/
├── article-meta.json
├── 01_research/
│   ├── queries.json
│   ├── raw-data.json
│   ├── sources.json
│   ├── claims.json
│   ├── analysis.json
│   ├── fact-checks.json
│   ├── decisions.json
│   └── market_data/
│       └── data.json
├── 02_edit/
│   ├── first_draft.md
│   ├── critic.json
│   ├── critic.md
│   └── revised_draft.md
└── 03_published/
```

#### カテゴリ別デフォルト設定

| カテゴリ | target_audience | 主な入力 |
|---------|-----------------|----------|
| market_report | intermediate | symbols, date_range |
| stock_analysis | intermediate | symbols, date_range |
| economic_indicators | intermediate | fred_series, date_range |
| investment_education | beginner | topics |
| quant_analysis | advanced | symbols, date_range, backtest_config |

---

### 3.2 /finance-research

**目的**: リサーチワークフローの実行

#### パラメータ

| パラメータ | 必須 | デフォルト | 型 | 説明 |
|-----------|------|-----------|-----|------|
| --article | ○ | - | string | 記事ID |
| --depth | - | auto | enum | shallow/auto/deep |
| --parallel | - | true | bool | 並列処理 |
| --force | - | false | bool | 強制再実行 |

#### 深度オプション

| 深度 | 説明 |
|------|------|
| shallow | 基本情報のみ、クエリ数制限 |
| auto | claims-analyzer の判定で自動調整（推奨） |
| deep | 詳細調査、追加クエリ、複数検証 |

#### 処理フロー

**Phase 1: クエリ生成**
- article-meta.json 確認
- finance-query-generator 実行 → queries.json

**Phase 2: データ収集（並列4エージェント）**
```
Task 1: finance-market-data → market_data/data.json
Task 2: finance-web → raw-data.json (web_search)
Task 3: finance-wiki → raw-data.json (wikipedia)
Task 4: finance-sec-filings → raw-data.json (sec_filings)
```

**Phase 3: データ処理**
- finance-source → sources.json
- finance-claims → claims.json

**Phase 3.5: センチメント分析**
- finance-sentiment-analyzer → sentiment_analysis.json

**Phase 4: 分析・検証（並列）**
```
Task 1: finance-claims-analyzer → analysis.json
Task 2: finance-fact-checker → fact-checks.json
Task 3: finance-decisions → decisions.json
```

**Phase 5: 可視化**
- finance-visualize → visualize/

#### 呼び出すエージェント（12個）

1. finance-query-generator
2. finance-market-data
3. finance-web
4. finance-wiki
5. finance-sec-filings
6. finance-source
7. finance-claims
8. finance-sentiment-analyzer
9. finance-claims-analyzer
10. finance-fact-checker
11. finance-decisions
12. finance-visualize

#### 出力ファイル

- queries.json
- raw-data.json
- market_data/data.json
- sources.json
- claims.json
- sentiment_analysis.json
- analysis.json
- fact-checks.json
- decisions.json
- visualize/

---

### 3.3 /finance-edit

**目的**: 記事執筆・批評・修正ワークフロー

#### パラメータ

| パラメータ | 必須 | デフォルト | 型 | 説明 |
|-----------|------|-----------|-----|------|
| --article | ○ | - | string | 記事ID |
| --mode | - | full | enum | quick/full |
| --skip-draft | - | false | bool | 初稿作成スキップ |

#### 編集モード

| モード | 批評エージェント | 用途 |
|--------|-----------------|------|
| quick | fact, compliance | 速報記事、簡潔な記事 |
| full | fact, compliance, structure, data_accuracy, readability | 詳細記事、高品質 |

#### 処理フロー

**Step 1: 初稿作成**
1. リサーチ完了確認
2. finance-article-writer 実行 → first_draft.md
3. [HF5] 初稿レビュー（推奨）

**Step 2: 批評（並列実行）**

quick モード:
```
Task 1: finance-critic-fact
Task 2: finance-critic-compliance
```

full モード:
```
Task 1: finance-critic-fact
Task 2: finance-critic-compliance
Task 3: finance-critic-structure
Task 4: finance-critic-data
Task 5: finance-critic-readability
```

結果統合 → critic.json + critic.md

**Step 3: 修正**
1. finance-reviser 実行 → revised_draft.md
2. [HF6] 最終確認（必須）
3. status = "ready_for_publish"

#### 呼び出すエージェント（7個）

1. finance-article-writer
2. finance-critic-fact
3. finance-critic-compliance
4. finance-critic-structure (fullモード時)
5. finance-critic-data (fullモード時)
6. finance-critic-readability (fullモード時)
7. finance-reviser

---

### 3.4 /finance-full

**目的**: 全工程一括実行

#### パラメータ

| パラメータ | 必須 | デフォルト | 型 | 説明 |
|-----------|------|-----------|-----|------|
| トピック名 | ○ | - | string | 記事のテーマ |
| --category | - | 対話選択 | enum | カテゴリ |
| --depth | - | auto | enum | shallow/auto/deep |
| --mode | - | quick | enum | quick/full |
| --skip-hf | - | false | bool | HFスキップ（非推奨） |

#### 処理フロー

```
Phase 1: 記事フォルダ作成
├── /new-finance-article 全機能実行
└── [HF1] トピック承認

Phase 2: リサーチ実行
├── /finance-research --article {article_id} --depth {depth}
└── [HF3] 主張採用確認

Phase 3: 記事執筆
├── /finance-edit --article {article_id} --mode {mode}
├── [HF5] 初稿レビュー
└── [HF6] 最終確認
```

#### カテゴリ別推奨設定

| カテゴリ | 推奨depth | 推奨mode | 理由 |
|---------|-----------|----------|------|
| market_report | auto | quick | 定期市場レポート、速報性重視 |
| stock_analysis | deep | full | 詳細企業分析、品質重視 |
| economic_indicators | deep | full | マクロ経済分析、正確性重視 |
| investment_education | deep | full | 教育コンテンツ、読みやすさ重視 |
| quant_analysis | deep | full | 数値分析、データ正確性重視 |

#### 実行時間目安

- shallow + quick: 約5-10分
- auto + quick: 約10-20分
- deep + full: 約20-40分

---

### 3.5 /finance-suggest-topics

**目的**: トピック提案とスコアリング

#### パラメータ

| パラメータ | 必須 | デフォルト | 型 | 説明 |
|-----------|------|-----------|-----|------|
| カテゴリ | - | 全カテゴリ | enum | 特定カテゴリに限定 |
| --count | - | 5 | integer | 提案数 |

#### 処理フロー

**Phase 1: 既存記事確認**
- articles/ スキャン
- カテゴリ分布集計

**Phase 2: トピック提案生成**
- finance-topic-suggester エージェント実行

**Phase 3: 結果整形・表示**

#### スコア評価基準（各1-10点、合計50点）

| 基準 | 高スコア（8-10） | 中スコア（5-7） | 低スコア（1-4） |
|------|-----------------|----------------|----------------|
| timeliness | 今週のイベント | 今月のイベント | 時事性なし |
| information | データ豊富、複数ソース | 十分なデータ | データ不足 |
| reader_interest | SNS話題、検索需要高 | 一定の関心 | ニッチ |
| feasibility | 3000-5000字で完結 | 調整必要 | 大幅調整必要 |
| uniqueness | 独自視点あり | 標準的 | 類似記事多数 |

#### 出力フォーマット

```json
{
  "rank": 1,
  "topic": "トピック名",
  "category": "カテゴリ",
  "suggested_symbols": ["AAPL", "^GSPC"],
  "scores": {
    "timeliness": 9,
    "information_availability": 8,
    "reader_interest": 8,
    "feasibility": 9,
    "uniqueness": 7,
    "total": 41
  },
  "rationale": "提案理由",
  "key_points": ["ポイント1", "ポイント2"]
}
```

---

### 3.6 /collect-finance-news

**目的**: RSSニュース収集とGitHub Issues投稿

#### パラメータ

| パラメータ | 必須 | デフォルト | 型 | 説明 |
|-----------|------|-----------|-----|------|
| --project | - | 15 | integer | GitHub Project番号 |
| --limit | - | 50 | integer | 取得記事数上限 |
| --themes | - | all | string | 対象テーマ |
| --dry-run | - | false | bool | 投稿せず確認のみ |

#### テーマ別Status設定

| テーマ | GitHub Status | Status ID |
|--------|---------------|-----------|
| Index | Status=Index | f75ad846 |
| Stock | Status=Stock | 47fc9ee4 |
| Sector | Status=Sector | 98236657 |
| Macro | Status=Macro Economics | c40731f6 |
| AI | Status=AI | 17189c86 |

#### 処理フロー

**Phase 1: 初期化**
1. テーマ設定ファイル確認
2. RSS MCP ツール確認（リトライロジック付き）
3. GitHub CLI 確認

**Phase 2: データ準備**
- finance-news-orchestrator エージェント実行
- 一時ファイル保存

**Phase 3: テーマ別収集（並列5エージェント）**
```
Task 1: finance-news-index
Task 2: finance-news-stock
Task 3: finance-news-sector
Task 4: finance-news-macro
Task 5: finance-news-ai
```

**Phase 4: 結果報告**

---

## 4. エージェント詳細仕様

### 4.1 finance-query-generator

**役割**: 金融トピックから検索クエリを生成

#### 入力パラメータ

```json
{
  "article_id": "記事ID",
  "topic": "トピック名",
  "category": "market_report | stock_analysis | economic_indicators | investment_education | quant_analysis",
  "symbols": ["AAPL", "^GSPC"],
  "fred_series": ["GDP", "CPIAUCSL"],
  "date_range": {
    "start": "2025-01-01",
    "end": "2025-01-11"
  }
}
```

#### 出力スキーマ（queries.json）

```json
{
  "article_id": "string",
  "topic": "string",
  "category": "string",
  "generated_at": "ISO8601",
  "queries": {
    "wikipedia": [
      {
        "query_id": "Q001",
        "query": "検索クエリ",
        "lang": "ja | en",
        "purpose": "main | related | background"
      }
    ],
    "web_search": [
      {
        "query_id": "Q010",
        "query": "検索クエリ",
        "lang": "ja | en",
        "focus": "basic | detail | recent | news | analysis"
      }
    ],
    "financial_data": {
      "symbols": ["AAPL", "^GSPC"],
      "fred_series": ["GDP", "CPIAUCSL"],
      "date_range": {
        "start": "2024-01-01",
        "end": "2025-01-10"
      }
    }
  }
}
```

#### カテゴリ別キーワード戦略

| カテゴリ | 日本語キーワード | 英語キーワード |
|---------|-----------------|----------------|
| market_report | 市場動向, 株価, 為替, 週間レビュー | market analysis, stock market, forex |
| stock_analysis | 決算, 業績, 株価分析, 目標株価 | earnings, financials, price target |
| economic_indicators | 経済指標, GDP, 雇用統計, インフレ | economic data, GDP, employment |
| investment_education | 投資入門, 資産形成, リスク管理 | investing basics, portfolio |
| quant_analysis | クオンツ, バックテスト, シャープレシオ | quantitative, backtest, Sharpe ratio |

#### エラーコード

| コード | 説明 |
|--------|------|
| E001 | 入力パラメータエラー（article_id, topic, categoryが未指定） |
| E006 | 出力ディレクトリ存在エラー |

---

### 4.2 finance-market-data

**役割**: YFinance/FREDデータ取得

#### 出力スキーマ（market_data/data.json）

```json
{
  "article_id": "string",
  "fetched_at": "ISO8601",
  "status": "success | partial | failed",
  "symbols": {
    "AAPL": {
      "source": "yfinance",
      "from_cache": false,
      "rows": 252,
      "date_range": ["2024-01-02", "2025-01-10"],
      "latest": {
        "date": "2025-01-10",
        "close": 225.50,
        "volume": 45000000
      },
      "summary": {
        "52w_high": 250.00,
        "52w_low": 180.00,
        "avg_volume": 50000000
      }
    }
  },
  "economic": {
    "GDP": {
      "source": "fred",
      "rows": 12,
      "latest": {
        "date": "2024-09-30",
        "value": 27000
      }
    }
  }
}
```

#### シンボルタイプ

| タイプ | 例 | 説明 |
|--------|-----|------|
| 個別株 | AAPL, MSFT | 米国個別株 |
| 指数 | ^GSPC, ^IXIC | 指数（^プレフィックス） |
| 為替 | USDJPY=X | 為替ペア（=Xサフィックス） |
| コモディティ | GC=F | 先物（=Fサフィックス） |
| FRED | GDP, CPIAUCSL | 経済指標 |

#### エラーコード

| コード | 説明 |
|--------|------|
| E001 | 入力パラメータエラー |
| E002 | データ取得エラー（ネットワーク、無効シンボル） |
| E003 | FRED API キーエラー |

---

### 4.3 finance-web

**役割**: Web検索で金融情報を収集

#### 推奨ソース（信頼度別）

| 信頼度 | ソース |
|--------|--------|
| high | Bloomberg, Reuters, WSJ, Financial Times, CNBC, Yahoo Finance, SEC EDGAR |
| medium | MarketWatch, Investopedia, Morningstar, 企業IR |
| low | 個人ブログ, SNS, 掲示板 |

#### 出力スキーマ（raw-data.json > web_search）

```json
[
  {
    "source_id": "W001",
    "query_id": "Q010",
    "url": "https://...",
    "title": "記事タイトル",
    "snippet": "概要テキスト",
    "source_name": "Bloomberg",
    "published_date": "2025-01-10",
    "reliability": "high | medium | low",
    "relevance": "high | medium | low"
  }
]
```

#### 処理特性

- 並列実行最大8クエリ同時
- 重複URL除去
- 信頼度でソート

---

### 4.4 finance-wiki

**役割**: Wikipedia から金融背景情報を収集

#### MCPツール使用

- `mcp__wikipedia__search_wikipedia`: キーワード検索
- `mcp__wikipedia__get_article`: 記事全文取得
- `mcp__wikipedia__get_summary`: 要約取得
- `mcp__wikipedia__extract_key_facts`: 重要事実抽出
- `mcp__wikipedia__get_related_topics`: 関連トピック取得

#### 出力スキーマ（raw-data.json > wikipedia）

```json
[
  {
    "source_id": "WK001",
    "query_id": "Q001",
    "title": "記事タイトル",
    "lang": "ja | en",
    "url": "https://...",
    "summary": "要約テキスト",
    "key_facts": [
      {
        "fact": "事実の内容",
        "type": "definition | history | statistic | event"
      }
    ],
    "reliability": "high"
  }
]
```

---

### 4.5 finance-source

**役割**: raw-data.json から情報源を整理し sources.json 生成

#### 信頼度判定基準（金融向け）

| 信頼度 | ソースタイプ |
|--------|------------|
| high | SEC EDGAR, FRED, 取引所公式, Bloomberg, Reuters, 企業IR |
| medium | Yahoo Finance, Seeking Alpha, MarketWatch, Wikipedia |
| low | 個人ブログ, SNS, 掲示板, 不明 |

#### ソースタイプ分類

- official: 公式発表（企業IR、政府機関）
- news: ニュース記事
- analysis: アナリストレポート、分析記事
- data: データソース（FRED、Yahoo Finance）
- reference: 参考情報（Wikipedia、解説記事）
- opinion: 意見・見解

#### 出力スキーマ（sources.json）

```json
{
  "article_id": "string",
  "generated_at": "ISO8601",
  "sources": [
    {
      "source_id": "S001",
      "original_id": "W001 | WK001 | MD001",
      "type": "official | news | analysis | data | reference | opinion",
      "title": "ソースタイトル",
      "url": "https://...",
      "source_name": "Bloomberg",
      "reliability": "high | medium | low",
      "relevance": "high | medium | low",
      "key_data": [
        {
          "label": "データラベル",
          "value": "データ値",
          "unit": "単位"
        }
      ]
    }
  ],
  "statistics": {
    "total_sources": 15,
    "by_reliability": { "high": 5, "medium": 8, "low": 2 },
    "by_type": { "official": 3, "news": 5, "analysis": 4 }
  }
}
```

---

### 4.6 finance-claims

**役割**: sources.json から金融関連の主張・事実を抽出

#### 主張タイプ分類

| タイプ | 説明 | 例 |
|--------|------|-----|
| fact | 検証可能な事実 | 株価が$225で終了した |
| statistic | 統計データ | 前年比+15%の増収 |
| forecast | 将来予測 | 来期のEPSは$3.50と予想 |
| analysis | 分析結果 | RSIが70を超えて過熱感 |
| opinion | 意見・見解 | 割高と判断する |
| quote | 引用 | CEOは「成長を継続」と発言 |
| event | イベント情報 | 1月29日にFOMC開催 |

#### 重要度判定

| 重要度 | 基準 |
|--------|------|
| high | 記事の核心、投資判断に直結 |
| medium | 補足情報、背景説明 |
| low | 参考情報、詳細データ |

#### 出力スキーマ（claims.json）

```json
{
  "article_id": "string",
  "generated_at": "ISO8601",
  "claims": [
    {
      "claim_id": "C001",
      "source_ids": ["S001", "S003"],
      "type": "fact | statistic | forecast | analysis | opinion | quote | event",
      "importance": "high | medium | low",
      "content": "主張の内容",
      "data": {
        "value": 225.50,
        "unit": "USD",
        "date": "2025-01-10",
        "comparison": {
          "type": "yoy | mom | qoq | prev_close",
          "change": 15.5,
          "unit": "%"
        }
      },
      "confidence": "high | medium | low",
      "temporal": "past | present | future"
    }
  ],
  "statistics": {
    "total_claims": 25,
    "by_type": { "fact": 10, "statistic": 8, "forecast": 3 },
    "by_importance": { "high": 5, "medium": 12, "low": 8 }
  }
}
```

---

### 4.7 finance-sentiment-analyzer

**役割**: ニュース・ソースのセンチメント分析

#### スコアリング基準（0-100、50:中立）

| スコア範囲 | ラベル |
|-----------|--------|
| 0-20 | extreme_fear |
| 21-40 | fear |
| 41-60 | neutral |
| 61-80 | greed |
| 81-100 | extreme_greed |

#### 出力スキーマ（sentiment.json）

```json
{
  "overall_sentiment": {
    "score": 65,
    "label": "greed",
    "trend": "improving | declining | stable"
  },
  "by_symbol": [
    {
      "symbol": "AAPL",
      "score": 72,
      "label": "greed",
      "mentions": 15,
      "key_points": ["iPhone売上が予想を上回る"]
    }
  ],
  "by_topic": [
    {
      "topic": "earnings | macro | geopolitical | monetary_policy",
      "score": 58,
      "label": "neutral",
      "mentions": 8
    }
  ],
  "confidence": "high | medium | low"
}
```

---

### 4.8 finance-claims-analyzer

**役割**: claims.json の情報ギャップを検出

#### カバレッジ分析（必須トピック）

**market_report**: 主要指数の動き, イベント影響, セクター別動向, 来週の注目点

**stock_analysis**: 最新決算情報, 株価動向, バリュエーション, リスク要因, 競合比較

**economic_indicators**: 指標実績値, 市場予想比較, 市場への影響, 政策への示唆

**investment_education**: 用語定義, 実践的方法, リスク説明, 具体例

**quant_analysis**: 戦略ロジック, バックテスト結果, パフォーマンス指標, リスク分析

#### 情報ギャップタイプ

| タイプ | 説明 |
|--------|------|
| missing_info | 欠落している重要情報 |
| contradiction | ソース間の矛盾 |
| ambiguity | 不明確な情報 |
| unverified | 未確認の情報 |

#### 出力スキーマ（analysis.json）

```json
{
  "article_id": "string",
  "coverage": {
    "required_topics": [
      {
        "topic": "トピック名",
        "status": "covered | partial | missing",
        "claims_count": 5,
        "quality": "high | medium | low"
      }
    ],
    "coverage_score": 85
  },
  "gaps": [
    {
      "gap_id": "G001",
      "type": "missing_info | contradiction | ambiguity | unverified",
      "description": "ギャップ説明",
      "importance": "high | medium | low",
      "suggested_action": "追加調査提案",
      "suggested_queries": ["追加クエリ1"]
    }
  ],
  "recommendations": {
    "additional_research_needed": true,
    "priority_gaps": ["G001", "G002"],
    "ready_for_writing": false
  }
}
```

---

### 4.9 finance-fact-checker

**役割**: claims.json の各主張を検証

#### 検証ステータス

| ステータス | 基準 |
|-----------|------|
| verified | 2件以上の信頼できるソースで確認、矛盾なし |
| disputed | ソース間で矛盾あり |
| unverifiable | 検証手段なし、将来予測、単一ソースのみ |
| speculation | 推測・仮説、アナリスト意見 |

#### 許容誤差

| データタイプ | 許容誤差 |
|-------------|---------|
| 株価 | ±0.01 |
| 変動率 | ±0.1% |
| 大きな数値 | ±1% |
| 経済指標 | ±0.1 |

#### 出力スキーマ（fact-checks.json）

```json
{
  "article_id": "string",
  "checks": [
    {
      "check_id": "FC001",
      "claim_id": "C001",
      "claim_content": "主張内容",
      "verification_status": "verified | disputed | unverifiable | speculation",
      "confidence": "high | medium | low",
      "verification_details": {
        "method": "検証方法説明",
        "sources_checked": ["S001", "S003"],
        "data_match": true,
        "discrepancies": []
      }
    }
  ],
  "summary": {
    "total_claims": 25,
    "verified": 18,
    "disputed": 2,
    "unverifiable": 3,
    "speculation": 2,
    "verification_rate": 72
  }
}
```

---

### 4.10 finance-decisions

**役割**: claims.json と fact-checks.json を基に採用可否を判定

#### 判定基準

**accept（採用）**
- verified かつ high/medium 信頼度
- 重要度が high または medium
- テーマに直接関連

**reject（不採用）**
- disputed かつ解決不能
- 信頼度 low かつ単一ソース
- テーマと無関係

**hold（保留）**
- unverifiable だが重要
- 追加検証が必要
- speculation だが参考として有用

#### usage_guidance 生成

| フィールド | 説明 |
|-----------|------|
| can_state_as_fact | true: 断定的に記述可能 |
| requires_hedging | true: ヘッジ表現が必要 |
| hedging_phrase | 推奨される表現 |
| requires_source_citation | true: 出典記載が必須 |
| temporal_label | past / present / future |

#### hedging_phrase の例

| 信頼度 | 表現 |
|--------|------|
| verified + high | 〜である |
| verified + medium | 〜とされている、〜と報告されている |
| disputed | 〜という見方と〜という見方がある |
| speculation | 〜の可能性がある、〜と予想されている |

#### 出力スキーマ（decisions.json）

```json
{
  "article_id": "string",
  "decisions": [
    {
      "decision_id": "D001",
      "claim_id": "C001",
      "check_id": "FC001",
      "decision": "accept | reject | hold",
      "reason": "判定理由",
      "usage_guidance": {
        "can_state_as_fact": true,
        "requires_hedging": false,
        "hedging_phrase": null,
        "requires_source_citation": true,
        "temporal_label": "past"
      },
      "priority": "high | medium | low"
    }
  ],
  "summary": {
    "total_claims": 25,
    "accepted": 18,
    "rejected": 4,
    "held": 3,
    "acceptance_rate": 72
  },
  "content_guidance": {
    "key_facts": ["D001", "D005"],
    "supporting_facts": ["D002", "D003"],
    "background_info": ["D010"],
    "speculative_content": ["D015"]
  }
}
```

---

### 4.11 finance-technical-analysis

**役割**: テクニカル指標を計算・分析

#### 計算指標

| カテゴリ | 指標 | パラメータ |
|---------|------|-----------|
| トレンド | SMA | 20, 50, 200日 |
| | EMA | 12, 26日 |
| | MACD | (12, 26, 9) |
| | ADX | 14日 |
| モメンタム | RSI | 14日 |
| | Stochastic | (14, 3) |
| | Williams %R | 14日 |
| ボラティリティ | Bollinger Bands | (20, 2) |
| | ATR | 14日 |
| 出来高 | OBV | - |
| | Volume SMA | 20日 |

#### 判定基準

**トレンド判定**
| 条件 | 判定 |
|------|------|
| 価格 > SMA200, SMA50 > SMA200 | bullish |
| 価格 < SMA200, SMA50 < SMA200 | bearish |
| その他 | neutral |

**RSI判定**
| 値 | 判定 |
|----|------|
| > 70 | overbought |
| < 30 | oversold |
| 30-70 | neutral |

**総合シグナル**
| 条件 | シグナル |
|------|---------|
| トレンド bullish + RSI neutral/oversold + MACD bullish | buy |
| トレンド bearish + RSI neutral/overbought + MACD bearish | sell |
| その他 | hold |

---

### 4.12 finance-economic-analysis

**役割**: FRED経済指標データを分析

#### 分析対象指標

| カテゴリ | 指標 | 説明 |
|---------|------|------|
| 成長 | GDP, GDPC1 | 国内総生産 |
| インフレ | CPIAUCSL, CPILFESL, PCEPI | 物価指数 |
| 雇用 | UNRATE, PAYEMS, ICSA | 失業率・雇用 |
| 金利 | FEDFUNDS, DGS10, DGS2 | 政策金利・国債 |
| 住宅 | HOUST, CSUSHPISA | 住宅市場 |
| 消費者 | UMCSENT, RSAFS | 消費者信頼感 |

#### 評価基準

**経済成長評価（GDP成長率 QoQ年率）**
| 成長率 | 評価 |
|--------|------|
| > 2.5% | expanding |
| 0-2.5% | stagnant |
| < 0% | contracting |

**インフレ評価（CPI前年比）**
| CPI | 評価 |
|-----|------|
| > 3.0% | above_target |
| 1.5-3.0% | at_target |
| < 1.5% | below_target |

**雇用評価（失業率）**
| 失業率 | 評価 |
|--------|------|
| < 4.0% | strong |
| 4.0-5.0% | moderate |
| > 5.0% | weak |

---

### 4.13 finance-article-writer

**役割**: リサーチ結果から記事初稿を生成

#### 信頼度別表現ルール

| 検証ステータス | 信頼度 | 表現例 |
|--------------|--------|--------|
| verified | high | 〜である、〜となった |
| verified | medium | 〜とされている、〜と報告されている |
| disputed | - | 〜という見方と〜という見方がある |
| speculation | - | 〜の可能性がある、〜と予想されている |

#### 禁止表現

- 「絶対に」「必ず」「間違いなく」
- 「買うべき」「売るべき」
- 「推奨」「お勧め」
- 過度に断定的な将来予測

#### 必須要素

全カテゴリ:
1. 冒頭の免責事項（snippets/not-advice.md）
2. 末尾のデータソース列挙
3. 末尾のリスク開示（snippets/investment-risk.md）

#### カテゴリ別テンプレート構成

**market_report（3000-5000字）**
```
- 市場サマリー（300-500字）
- 株式市場（米国/日本）
- 為替市場
- 経済指標
- 来週の注目イベント
```

**stock_analysis（4000-6000字）**
```
- エグゼクティブサマリー（200-300字）
- 企業概要
- 財務分析（業績推移、バリュエーション）
- テクニカル分析
- リスク要因
- まとめ
```

**economic_indicators（2500-4000字）**
```
- 概要（200-300字）
- 指標の解説（定義、算出方法、重要性）
- 過去の推移
- 今回の発表内容（データ表）
- 市場への影響
- 今後の見通し
```

---

### 4.14 finance-visualize

**役割**: リサーチ結果を可視化

#### 出力ファイル

- `visualize/summary.md` - リサーチ概要
- `visualize/charts/` - Mermaid形式チャート
- `visualize/tables/` - マークダウン表

#### チャート生成（Mermaid）

- 折れ線: 価格推移
- 棒グラフ: セクター別パフォーマンス
- 時系列: 経済指標トレンド
- フロー図: 因果関係

---

### 4.15 finance-critic-fact

**役割**: 記事の事実正確性を検証

#### 検証対象

- 数値データ（株価、決算、経済指標等）
- 日付情報
- 事実記述
- 出典の正確性

#### スコアリング

```
score = 100 - (high_issues × 10 + medium_issues × 5 + low_issues × 2)
```

#### 出力スキーマ（critic.json > fact）

```json
{
  "critic_type": "fact",
  "score": 85,
  "issues": [
    {
      "issue_id": "F001",
      "severity": "high | medium | low",
      "location": {
        "section": "セクション名",
        "line": "該当行テキスト"
      },
      "issue": "問題説明",
      "original": "記事の記述",
      "correct": "正しい記述",
      "source": "S001",
      "suggestion": "修正提案"
    }
  ],
  "verified_facts": 45,
  "issues_found": 3,
  "verification_rate": 93.3
}
```

---

### 4.16 finance-critic-compliance

**役割**: コンプライアンス・金融規制チェック

#### チェック項目

1. **投資助言規制**
   - 特定銘柄の売買推奨がないか
   - 「買うべき」「売るべき」等の表現がないか

2. **免責事項**
   - 投資リスク警告の有無
   - 投資助言ではない旨の記載

3. **表現の適切性**
   - 「絶対」「必ず」等の禁止表現
   - リターンの保証を示唆する表現

4. **情報の公正性**
   - メリット・デメリットの両面提示
   - リスク開示の適切さ

5. **データソースの明示**

#### 禁止表現チェック

```
「買うべき」「売るべき」
「絶対に上がる/下がる」
「必ず儲かる」
「おすすめ銘柄」
「今が買い時/売り時」
```

#### 必須免責事項

冒頭:
```
本記事は情報提供を目的としており、
特定の金融商品の売買を推奨するものではありません。
```

末尾:
```
投資には元本割れリスクがあります。
投資に関する最終決定は、ご自身の判断と責任において行ってください。
```

#### ステータス判定

| ステータス | 条件 |
|-----------|------|
| fail | critical な問題が1件以上 |
| warning | high な問題が1件以上、または必須免責欠落 |
| pass | その他 |

#### スコアリング

```
score = 100 - (critical × 30 + high × 15 + medium × 5 + low × 2)
critical がある場合: score 最大70
```

**重要**: status が fail の場合、記事は修正が完了するまで公開不可

---

### 4.17 finance-critic-structure

**役割**: 文章構成を評価

#### 評価項目

1. **導入部**（20%）- フックの効果、問題提起の明確さ
2. **論理展開**（25%）- 段階的説明、セクション間の遷移
3. **セクション構成**（25%）- 見出しの明確さ、階層構造
4. **結論**（15%）- 要約の的確さ、読者への示唆
5. **読みやすさ**（15%）- 文の長さ、段落の長さ

---

### 4.18 finance-critic-data

**役割**: データ・数値の正確性を検証

#### 検証対象

- 株価: 終値, 始値, 高値, 安値, 出来高
- 変動率: 日次, 週次/月次/年次リターン
- 決算: 売上高, 営業利益, 純利益, EPS
- バリュエーション: P/E, P/B, PEG, 配当利回り
- 経済指標: GDP, CPI, 失業率, 金利

#### スコアリング

```
score = (correct / total) × 100 - (high_issues × 5)
```

---

### 4.19 finance-critic-readability

**役割**: 読みやすさと訴求力を評価

#### ターゲット読者別の評価基準

**beginner（初心者）**
- 専門用語には必ず説明を付ける
- 前提知識を仮定しない
- 具体例を多用
- 短く、シンプルに

**intermediate（中級者）**
- 基本用語は説明不要
- 分析の根拠を明示
- 丁寧なデータ解釈

**advanced（上級者）**
- 専門用語をそのまま使用可
- 詳細なデータ分析
- 簡潔な表現

#### note.com 読者特性

- デバイス: スマホ中心（70%以上）
- タイミング: 隙間時間
- 判断時間: 最初の数行で決定
- 段落長: スマホで3-4行が目安

---

### 4.20 finance-reviser

**役割**: 批評結果を反映して記事を修正

#### 修正優先順位

1. **最優先**: compliance の critical/high 問題
2. **高優先**: fact の high 問題
3. **高優先**: data_accuracy の high 問題
4. **中優先**: structure の high/medium 問題
5. **中優先**: readability の high/medium 問題
6. **低優先**: その他の low 問題

#### compliance 問題の修正方針

| 元の表現 | 修正後 |
|---------|--------|
| 買うべき | 注目に値する |
| 売るべき | リスクを考慮する必要がある |
| 絶対に〜 | 〜の可能性が高い |
| 必ず儲かる | リターンが期待できる可能性がある |

#### 品質チェック

- [ ] compliance の critical/high 問題がすべて解決
- [ ] 必須免責事項がすべて含まれている
- [ ] 数値データが正確
- [ ] 文章の一貫性が保たれている

---

### 4.21 finance-topic-suggester

**役割**: トピック提案とスコアリング

#### 評価基準（各1-10点、合計50点）

| 基準 | 説明 |
|------|------|
| timeliness | 時事性・話題性 |
| information_availability | 情報入手性 |
| reader_interest | 読者関心度 |
| feasibility | 執筆実現性 |
| uniqueness | 独自性 |

#### 避けるべきトピック

- 極めて専門的で一般読者に理解困難
- 信頼できる情報源が3つ未満
- 最近の既存記事と大きく重複
- センシティブすぎる予測

---

## 5. テンプレート構造

### 5.1 共通フォルダ構成

```
template/{category}/
├── article-meta.json
├── 01_research/
│   ├── analysis.json
│   ├── claims.json
│   ├── decisions.json
│   ├── fact-checks.json
│   ├── queries.json
│   ├── raw-data.json
│   ├── sources.json
│   └── market_data/
│       └── data.json
├── 02_edit/
│   ├── critic.json
│   ├── critic.md
│   ├── first_draft.md
│   └── revised_draft.md
└── 03_published/
    └── YYYYMMDD_article-title-en.md
```

### 5.2 カテゴリ別の違い

| カテゴリ | target_audience | 特別フィールド | processing |
|---------|-----------------|---------------|-----------|
| market_report | intermediate | date_range | technical_analysis, economic_analysis |
| stock_analysis | intermediate | date_range | technical_analysis, fundamental_analysis |
| economic_indicators | intermediate | date_range | economic_analysis のみ |
| investment_education | beginner | date_range なし | web_search, wiki_search のみ |
| quant_analysis | advanced | backtest_config | technical_analysis, backtest |

### 5.3 first_draft.md テンプレート（market_report例）

```markdown
---
title:
article_id:
category: market_report
symbols: []
period:
status: draft
---

> **免責事項**: 本記事は情報提供を目的としており、投資助言ではありません。

# 今週の市場サマリー
[300-500字: 主要指標の動き、重要イベント]

# 株式市場
## 米国市場
[S&P 500, NASDAQ, DOW の分析]

## 日本市場
[日経平均、TOPIX の分析]

# 為替市場
[USD/JPY, EUR/USD 等]

# 経済指標
[発表された重要指標]

# 来週の注目イベント
[経済カレンダー]

## 参考データソース
{自動生成: Yahoo Finance, FRED等}

## リスク開示
投資には元本割れリスクがあります...
```

---

## 6. JSONスキーマ定義

### 6.1 article-meta.schema.json

**必須フィールド**: article_id, topic, category, status, created_at, updated_at, workflow

**workflow セクション**:
```json
{
  "workflow": {
    "data_collection": {
      "market_data": "pending | done | in_progress | skipped",
      "web_search": "pending | done | in_progress | skipped",
      "wiki_search": "pending | done | in_progress | skipped"
    },
    "processing": {
      "sources": "pending | done",
      "claims": "pending | done",
      "technical_analysis": "pending | done",
      "fundamental_analysis": "pending | done",
      "economic_analysis": "pending | done",
      "backtest": "pending | done"
    },
    "research": {
      "analysis": "pending | done",
      "fact_checks": "pending | done",
      "decisions": "pending | done",
      "visualize": "pending | done"
    },
    "writing": {
      "first_draft": "pending | done",
      "critics": "pending | done",
      "revised_draft": "pending | done"
    },
    "publishing": {
      "final_review": "pending | done",
      "published": "pending | done"
    }
  }
}
```

### 6.2 common-enums.json

```json
{
  "reliability": ["high", "medium", "low"],
  "priority": ["high", "medium", "low"],
  "confidence": ["high", "medium", "low"],
  "decision": ["accept", "reject", "hold"],
  "claim_role": ["main", "supporting", "background"],
  "verification_status": ["verified", "disputed", "unverifiable", "speculation"],
  "issue_type": ["missing_info", "contradiction", "ambiguity", "unverified"],
  "source_type": ["web", "book", "video", "news", "academic", "other"],
  "workflow_status": ["pending", "done", "in_progress", "skipped"]
}
```

### 6.3 その他スキーマ一覧

| スキーマ | 説明 |
|---------|------|
| claims.schema.json | 主張リスト |
| fact-checks.schema.json | ファクトチェック結果 |
| analysis.schema.json | 論点整理・2段階リサーチ制御 |
| sources.schema.json | 情報源リスト |
| raw-data.schema.json | 生データ・並列実行メタ |
| decisions.schema.json | 採用判断 |
| critic.schema.json | 批評結果 |
| queries.schema.json | クエリ定義 |
| sentiment.schema.json | センチメント分析 |
| sec-filings.schema.json | SEC書類 |

---

## 7. データフロー

### 7.1 全体フロー図

```
Phase 0: finance-topic-suggester
         ↓ (topics提案)

Phase 1: finance-query-generator
         ↓ (queries.json)

Phase 2: ├─ finance-market-data (data.json)
         ├─ finance-web (→raw-data.json)
         ├─ finance-wiki (→raw-data.json)
         └─ finance-sentiment-analyzer (→sentiment.json)

Phase 3: finance-source
         ↓ (sources.json + tags更新)

Phase 4: ├─ finance-claims (→claims.json)
         ├─ finance-claims-analyzer (→analysis.json)
         ├─ finance-fact-checker (→fact-checks.json)
         ├─ finance-decisions (→decisions.json)
         ├─ finance-technical-analysis (→technical_analysis.json)
         └─ finance-economic-analysis (→economic_analysis.json)

Phase 5: finance-visualize
         ↓ (summary.md + charts/ + tables/)

Phase 6: finance-article-writer
         ↓ (first_draft.md)

Phase 7: ├─ finance-critic-fact (→critic.json:fact)
         ├─ finance-critic-compliance (→critic.json:compliance)
         ├─ finance-critic-structure (→critic.json:structure)
         ├─ finance-critic-data (→critic.json:data_accuracy)
         └─ finance-critic-readability (→critic.json:readability)

Phase 8: finance-reviser
         ↓ (revised_draft.md)
```

### 7.2 入出力ファイルマトリックス

| ファイル | 生成元 | 使用元 | フェーズ |
|---------|--------|--------|---------|
| queries.json | query-generator | web, wiki | 1 → 2 |
| data.json | market-data | technical, economic, critic-data | 2 → 4,7 |
| raw-data.json | web, wiki | source, sentiment | 2 → 3,2 |
| sources.json | source | claims, critic-fact | 3 → 4,7 |
| claims.json | claims | analyzer, checker, decisions, visualize | 4 → 4,4,4,5 |
| fact-checks.json | fact-checker | decisions, critic-fact | 4 → 4,7 |
| decisions.json | decisions | article-writer, visualize | 4 → 6,5 |
| first_draft.md | article-writer | critic-* (all) | 6 → 7 |
| critic.json | critic-* (all) | reviser | 7 → 8 |
| revised_draft.md | reviser | (公開) | 8 |

---

## 8. 品質管理システム

### 8.1 多層検証

| エージェント | 確認項目 |
|-------------|---------|
| fact-checker | ファクト検証 |
| critic-fact | 事実正確性（最終確認） |
| critic-data | 数値照合 |
| critic-compliance | 規制遵守（最重要） |
| critic-structure | 構成適切性 |
| critic-readability | ユーザー体験 |

### 8.2 ゲートメカニズム

- **compliance fail** → reviser 実行前にストップ
- **fact high issues > 3** → 追加検証要求
- **readability score < 60** → 改稿推奨

### 8.3 スコアリング体系

| エージェント | スコア計算式 | 合格ライン |
|------------|----------|----------|
| fact-checker | 検証率% | 70%以上 |
| critic-compliance | 100 - (c×30 + h×15 + ...) | pass (max 70 if critical) |
| critic-data | (correct/total) × 100 | 95%以上 |
| critic-structure | 5カテゴリ加重平均 | 70以上 |
| critic-readability | 5カテゴリ加重平均 | 60以上 |

### 8.4 記事公開条件

- compliance status: pass
- fact score: ≥80
- data_accuracy score: ≥85

---

## 9. エラーハンドリング

### 9.1 エラーコード一覧

| コード | 説明 | 発生元 |
|--------|------|--------|
| E001 | 入力パラメータエラー | query-generator, market-data |
| E002 | ファイル存在エラー | ほぼ全エージェント |
| E003 | API キーエラー | market-data (FRED) |
| E004 | 検索・通信エラー | web, wiki |
| E005 | GitHub API レート制限 | news-collector |
| E006 | 出力ディレクトリ存在エラー | query-generator |

### 9.2 エラー時の処理方針

| エラー | 対処 |
|--------|------|
| E001/E002 | 前提条件となるエージェント実行を促す |
| E003 | 環境変数設定を促す |
| E004 | リトライまたはクエリ調整を提案 |
| E005 | 1時間待機または --limit 削減 |
| E006 | /new-finance-article で記事フォルダ作成を促す |

### 9.3 リトライロジック

**RSS MCP ツール（E002専用）**
```
1回目: mcp__rss__* 検索
↓ 見つからない場合
3秒待機（MCPサーバー起動完了を待つ）
↓
2回目: 再検索
↓ 見つからない場合
エラー報告 → .mcp.json確認を促す
```

---

## 10. 並列実行戦略

### 10.1 並列実行可能グループ

**Phase 2: データ収集（4並列）**
- finance-market-data
- finance-web
- finance-wiki
- finance-sec-filings

**Phase 4: 分析（5並列）**
- finance-claims-analyzer
- finance-fact-checker
- finance-decisions
- finance-technical-analysis
- finance-economic-analysis

**Phase 7: 批評（5並列）**
- finance-critic-fact
- finance-critic-compliance
- finance-critic-structure
- finance-critic-data
- finance-critic-readability

### 10.2 推定実行時間

| エージェント | 推定時間 |
|-------------|---------|
| query-generator | 1-2秒 |
| web | 10-15秒 |
| wiki | 5-8秒 |
| market-data | 3-5秒 |
| source | 2-3秒 |
| claims | 3-5秒 |
| fact-checker | 5-8秒 |
| decisions | 2-3秒 |
| article-writer | 10-15秒 |
| critics (各) | 5-10秒 |
| reviser | 10-15秒 |

**合計**:
- 逐次実行時: 約120秒
- 最適化時（並列）: 約50秒

---

## 11. ヒューマンフィードバック

### 11.1 フィードバックポイント一覧

| ポイント | タイミング | 目的 | スキップ可能 | 関連コマンド |
|---------|-----------|------|------------|------------|
| HF1 | フォルダ作成後 | トピック承認 | yes | new-finance-article, finance-full |
| HF2 | データ収集後 | データ確認 | yes | finance-research |
| HF3 | 分析完了後 | 主張採用確認 | yes | finance-research, finance-full |
| HF4 | 可視化完了後 | チャート確認 | yes | finance-research |
| HF5 | 初稿作成後 | 初稿レビュー | yes | finance-edit, finance-full |
| HF6 | 修正版完成後 | 最終確認 | yes（非推奨） | finance-edit, finance-full |

### 11.2 各フィードバックの詳細

**HF1: トピック承認**
- 表示: article-meta.json の基本情報
- 操作: 承認 / 修正 / キャンセル

**HF3: 主張採用確認**
- 表示: decisions.json の内容
- 操作: accept/reject/hold の変更可

**HF5: 初稿レビュー**
- 表示: first_draft.md
- 操作: 編集可、承認で次へ

**HF6: 最終確認**
- 表示: revised_draft.md + 修正サマリー
- 操作: 承認 / 追加修正要求

---

## 12. ニュース収集システム

### 12.1 アーキテクチャ

```
Layer 1: Orchestrator
├── 既存Issue取得 (gh issue list)
├── セッション情報生成
└── 一時ファイル作成

Layer 2: テーマ別エージェント × 5 (並列)
├── finance-news-index      [Index]
├── finance-news-stock      [Stock]
├── finance-news-sector     [Sector]
├── finance-news-macro      [Macro Economics]
└── finance-news-ai         [AI]

Layer 3: フィード取得 & フィルタリング
├── RSS取得 (mcp__rss__fetch_feed)
├── AIベースのテーマ判定
├── 重複チェック
└── Issue作成 & GitHub投稿
```

### 12.2 テーマ別フィード数

| テーマ | フィード数 | Status ID |
|--------|----------|-----------|
| Index | 2 | f75ad846 |
| Stock | 2 | 47fc9ee4 |
| Sector | 6 | 98236657 |
| Macro | 9 | c40731f6 |
| AI | 5 | 17189c86 |
| **合計** | **24** | - |

### 12.3 フィルタリングルール

#### AI判定による分類

**Index（株価指数）**
- 株価指数の動向（日経平均, TOPIX, S&P500, ダウ, ナスダック）
- 市場全体の上昇/下落
- ETF関連

**Stock（個別銘柄）**
- 個別企業の決算発表
- 業績予想、M&A、買収、提携

**Sector（セクター分析）**
- 特定業界の動向
- 業界規制の変更

**Macro（マクロ経済）**
- 金融政策（金利, 量的緩和）
- 中央銀行の決定
- 経済指標

**AI（AI技術）**
- AI技術, 機械学習
- 生成AI, LLM
- AI企業の動向

#### 除外判定

- スポーツ（試合結果、選手移籍）
- エンターテインメント（映画、音楽、芸能）
- 政治（選挙、内閣関連 ※金融政策に関連する場合は対象）
- 一般ニュース（事故、災害、犯罪）

#### 重複チェック

1. **URL完全一致**: 新規記事URLが既存Issueに含まれているか
2. **タイトル類似度**: Jaccard係数 ≥ 0.85 で重複と判定

### 12.4 GitHub Projects連携

**メタデータ**
- Project ID: PVT_kwHOBoK6AM4BMpw_
- StatusフィールドID: PVTSSF_lAHOBoK6AM4BMpw_zg739ZE
- 公開日時フィールドID: PVTF_lAHOBoK6AM4BMpw_zg8BzrI

**Issue作成フロー**

```bash
# Step 1: テンプレート読み込み + プレースホルダー置換
template=$(cat .github/ISSUE_TEMPLATE/news-article.md | tail -n +7)

# Step 2: Issue作成
issue_url=$(gh issue create --repo YH-05/quants \
  --title "[テーマ] {日本語タイトル}" \
  --body "$body" --label "news")

# Step 3: Project追加
gh project item-add 15 --owner YH-05 --url $issue_url

# Step 4: Status設定（GraphQL）
gh api graphql -f query='mutation { updateProjectV2ItemFieldValue(...) }'

# Step 5: 公開日時設定（GraphQL）【必須】
gh api graphql -f query='mutation { updateProjectV2ItemFieldValue(...) }'
```

### 12.5 Issueテンプレート

```markdown
### 概要
{{summary}}

### 情報源URL
{{url}}

### 公開日
{{published_date}}

### 収集日時
{{collected_at}}

### 信頼性スコア
{{credibility}}

### カテゴリ
{{category}}

### フィード/情報源名
{{feed_source}}

### 優先度
{{priority}}

### 備考・メモ
{{notes}}
```

---

## 13. 付録

### 13.1 エージェント一覧（28個）

| # | エージェント | フェーズ | 役割 |
|---|-------------|---------|------|
| 1 | finance-query-generator | 1 | クエリ生成 |
| 2 | finance-market-data | 2 | 市場データ取得 |
| 3 | finance-web | 2 | Web検索 |
| 4 | finance-wiki | 2 | Wikipedia検索 |
| 5 | finance-sec-filings | 2 | SEC書類取得 |
| 6 | finance-source | 3 | ソース整理 |
| 7 | finance-claims | 4 | 主張抽出 |
| 8 | finance-sentiment-analyzer | 2 | センチメント分析 |
| 9 | finance-claims-analyzer | 4 | 情報ギャップ検出 |
| 10 | finance-fact-checker | 4 | ファクトチェック |
| 11 | finance-decisions | 4 | 採用判定 |
| 12 | finance-technical-analysis | 4 | テクニカル分析 |
| 13 | finance-economic-analysis | 4 | 経済分析 |
| 14 | finance-visualize | 5 | 可視化 |
| 15 | finance-article-writer | 6 | 初稿生成 |
| 16 | finance-critic-fact | 7 | 事実正確性批評 |
| 17 | finance-critic-compliance | 7 | コンプライアンス批評 |
| 18 | finance-critic-structure | 7 | 構成批評 |
| 19 | finance-critic-data | 7 | データ正確性批評 |
| 20 | finance-critic-readability | 7 | 読みやすさ批評 |
| 21 | finance-reviser | 8 | 修正 |
| 22 | finance-topic-suggester | 0 | トピック提案 |
| 23 | finance-news-orchestrator | - | ニュース収集制御 |
| 24 | finance-news-index | - | 株価指数ニュース |
| 25 | finance-news-stock | - | 個別銘柄ニュース |
| 26 | finance-news-sector | - | セクターニュース |
| 27 | finance-news-macro | - | マクロ経済ニュース |
| 28 | finance-news-ai | - | AIニュース |

### 13.2 コマンド一覧（6個）

| コマンド | 目的 | 呼び出すエージェント数 |
|---------|------|---------------------|
| /new-finance-article | フォルダ作成 | 0 |
| /finance-research | リサーチ | 12 |
| /finance-edit | 執筆・批評 | 7 |
| /finance-full | 全工程一括 | 19 |
| /finance-suggest-topics | トピック提案 | 1 |
| /collect-finance-news | ニュース収集 | 6 |

### 13.3 出力ファイル一覧

**01_research/**
- queries.json
- raw-data.json
- sources.json
- claims.json
- sentiment_analysis.json
- analysis.json
- fact-checks.json
- decisions.json
- market_data/data.json
- visualize/

**02_edit/**
- first_draft.md
- critic.json
- critic.md
- revised_draft.md

**03_published/**
- YYYYMMDD_article-title-en.md

### 13.4 スニペット一覧

| スニペット | 用途 | 配置位置 |
|-----------|------|---------|
| snippets/not-advice.md | 投資助言ではない旨 | 冒頭 |
| snippets/investment-risk.md | 投資リスク警告 | 末尾 |
| snippets/data-source.md | データソース記載 | 末尾 |
| snippets/disclaimer.md | 免責事項 | 冒頭/末尾 |

### 13.5 環境変数

| 変数名 | 説明 | 必須 |
|--------|------|------|
| FRED_API_KEY | FRED API キー | finance-market-data使用時 |
| GITHUB_TOKEN | GitHub トークン | ニュース収集時 |

---

## 更新履歴

| バージョン | 日付 | 変更内容 |
|-----------|------|---------|
| 1.0 | 2026-01-19 | 初版作成 |

---

**文書終了**
