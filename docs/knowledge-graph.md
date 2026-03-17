# Knowledge Graph (Neo4j)

## Overview

quants プロジェクトのナレッジグラフは、金融分析ワークフローの出力を Neo4j に構造化して蓄積するシステムです。

| 項目 | 値 |
|------|-----|
| ノード種別 | 9 |
| リレーション種別 | 16 |
| ネームスペース | 4 |
| スキーマバージョン | KG v1 |

### ネームスペース

| ネームスペース | 説明 |
|---------------|------|
| `market` | 市場データ（銘柄、指数、セクター） |
| `research` | リサーチ出力（分析レポート、主張、ファクト） |
| `news` | ニュース記事・イベント |
| `meta` | メタデータ（ソース、実行記録） |

## Quick Start

### 1. Neo4j セットアップ

```bash
# Docker で Neo4j を起動
docker compose up -d neo4j

# 接続確認
# URL: bolt://localhost:7687
# User: neo4j / Password: 環境変数 NEO4J_PASSWORD
```

### 2. 初期制約の作成

```bash
/save-to-graph --init-constraints
```

初回実行時にユニーク制約とインデックスを自動作成します。

### 3. graph-queue の生成

各ワークフローの出力から graph-queue JSON を生成します:

```bash
/emit-graph-queue --command dr-stock --input research/DR_stock_{date}_{ticker}/03_analysis/stock-analysis.json
```

### 4. Neo4j への投入

```bash
/save-to-graph
```

`save-to-graph` スキルが graph-queue JSON を検出し、ノードとリレーションを MERGE ベースで冪等に投入します。

## Schema Overview

### ノード種別（9 types）

| ノード | ラベル | 主キー | 説明 |
|--------|--------|--------|------|
| 銘柄 | `Ticker` | `symbol` | 米国上場銘柄（AAPL, MSFT 等） |
| セクター | `Sector` | `name` | GICSセクター |
| 指数 | `Index` | `symbol` | 株価指数（SPX, NDX 等） |
| リサーチ | `Research` | `research_id` | 分析レポート（dr-stock, ca-eval 等） |
| 主張 | `Claim` | `claim_id` | CA評価で抽出された主張 |
| ファクト | `Fact` | `fact_id` | ファクトチェック結果 |
| ニュース | `NewsArticle` | `url` | ニュース記事 |
| イベント | `Event` | `event_id` | 市場イベント（決算、経済指標等） |
| ソース | `Source` | `source_id` | データソース（SEC EDGAR, yfinance 等） |

### リレーション種別（16 types）

| リレーション | 起点 | 終点 | 説明 |
|-------------|------|------|------|
| `BELONGS_TO` | Ticker | Sector | 銘柄のセクター所属 |
| `COMPONENT_OF` | Ticker | Index | 指数の構成銘柄 |
| `PEER_OF` | Ticker | Ticker | ピアグループ関係 |
| `ANALYZES` | Research | Ticker | リサーチの分析対象 |
| `PRODUCED_BY` | Research | Source | リサーチのデータソース |
| `CONTAINS_CLAIM` | Research | Claim | リサーチに含まれる主張 |
| `VERIFIED_BY` | Claim | Fact | 主張のファクトチェック |
| `SUPPORTS` | Fact | Claim | ファクトが主張を支持 |
| `CONTRADICTS` | Fact | Claim | ファクトが主張と矛盾 |
| `MENTIONS` | NewsArticle | Ticker | ニュース記事が銘柄に言及 |
| `COVERS` | NewsArticle | Event | ニュースがイベントをカバー |
| `IMPACTS` | Event | Ticker | イベントが銘柄に影響 |
| `IMPACTS_SECTOR` | Event | Sector | イベントがセクターに影響 |
| `REFERENCES` | Research | NewsArticle | リサーチがニュースを参照 |
| `FOLLOWS` | Research | Research | リサーチの時系列関係 |
| `SOURCED_FROM` | Fact | Source | ファクトのデータソース |

## Workflow Integration

各ワークフローが生成するノードとリレーション:

| ワークフロー | コマンド | 生成ノード | 生成リレーション |
|-------------|---------|-----------|----------------|
| 個別銘柄分析 | `/dr-stock` | Ticker, Sector, Research, Source | BELONGS_TO, ANALYZES, PRODUCED_BY, PEER_OF |
| 競争優位性評価 | `/ca-eval` | Research, Claim, Fact, Source | CONTAINS_CLAIM, VERIFIED_BY, SUPPORTS, CONTRADICTS, SOURCED_FROM |
| ニュース収集 | `/finance-news-workflow` | NewsArticle, Ticker, Event | MENTIONS, COVERS, IMPACTS |
| 週次レポート | `/generate-market-report` | Research, Index, Sector, Event | ANALYZES, IMPACTS_SECTOR, REFERENCES |
| 業界分析 | `/dr-industry` | Sector, Ticker, Research | BELONGS_TO, ANALYZES, COMPONENT_OF |

### 投入手順（共通）

```bash
# 1. ワークフロー実行
/dr-stock AAPL

# 2. graph-queue 生成
/emit-graph-queue --command dr-stock --input research/DR_stock_{date}_AAPL/03_analysis/stock-analysis.json

# 3. Neo4j 投入
/save-to-graph --source dr-stock
```

## Architecture

```
┌─────────────────────────────────────────────────────┐
│                   Workflow Layer                     │
│  dr-stock │ ca-eval │ finance-news │ market-report  │
└─────┬───────┬─────────┬───────────┬─────────────────┘
      │       │         │           │
      ▼       ▼         ▼           ▼
┌─────────────────────────────────────────────────────┐
│              emit-graph-queue Skill                  │
│  ワークフロー出力 → graph-queue JSON 変換            │
│  (.tmp/graph-queue/{source}_{timestamp}.json)        │
└──────────────────────┬──────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────┐
│              save-to-graph Skill                     │
│  Phase 1: キュー検出                                 │
│  Phase 2: ノード投入 (MERGE)                         │
│  Phase 3: リレーション投入 (MERGE)                    │
│  Phase 4: 完了処理                                   │
└──────────────────────┬──────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────┐
│                    Neo4j                             │
│  KG v1 Schema: 9 nodes, 16 relations                │
│  MERGE ベース冪等投入                                │
│  4 namespaces: market / research / news / meta       │
└─────────────────────────────────────────────────────┘
```

## 関連リソース

| リソース | パス |
|---------|------|
| emit-graph-queue スキル | `.claude/skills/emit-graph-queue/` |
| save-to-graph スキル | `.claude/skills/save-to-graph/` |
| Neo4j Docker 設定 | `docker-compose.yml` |
