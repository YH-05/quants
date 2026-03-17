---
description: graph-queue JSON を Neo4j に投入します（キュー検出 → ノード投入 → リレーション投入 → 完了処理）
argument-hint: [--source <command>] [--dry-run] [--file <path>] [--keep]
---

# /save-to-graph - Neo4j グラフデータ投入

graph-queue JSON ファイルを読み込み、Neo4j にナレッジグラフデータを MERGE ベースで冪等投入します。

## スキル

このコマンドは `save-to-graph` スキルを呼び出します。

- **スキル定義**: `.claude/skills/save-to-graph/SKILL.md`
- **詳細ガイド**: `.claude/skills/save-to-graph/guide.md`

## 使用例

```bash
# 標準実行（.tmp/graph-queue/ 配下の全未処理 JSON を投入）
/save-to-graph

# 特定コマンドソースのみ
/save-to-graph --source dr-stock

# 特定ファイルのみ
/save-to-graph --file .tmp/graph-queue/ca-eval/gq-20260317120000-a1b2.json

# ドライラン（Cypher を表示するが実行しない）
/save-to-graph --dry-run

# 処理済みファイルを削除せず保持
/save-to-graph --keep
```

## パラメータ

| パラメータ | デフォルト | 説明 |
|-----------|-----------|------|
| --source | all | 対象コマンドソース（dr-stock, ca-eval, finance-news-workflow 等） |
| --dry-run | false | Cypher クエリを表示するが実行しない |
| --file | - | 特定の graph-queue JSON ファイルパスを指定（--source と排他） |
| --keep | false | 処理済みファイルを削除せず `.tmp/graph-queue/.processed/` に移動 |

## 前提条件

1. Neo4j が起動中であること（quants-neo4j: bolt://localhost:7690）
2. 初回セットアップ（制約・インデックス作成）が完了していること
3. graph-queue JSON が `.tmp/graph-queue/` に存在すること

初回セットアップの手順は `.claude/skills/save-to-graph/guide.md` を参照してください。

## 処理フロー

```
Phase 1: キュー検出・検証
  +-- Neo4j 接続確認
  +-- 未処理 JSON 検出
  +-- スキーマ検証

Phase 2: ノード投入（MERGE）
  +-- Topic → Entity → FiscalPeriod → Source → Author
  +-- → Fact → Claim → FinancialDataPoint → Insight

Phase 3: リレーション投入（MERGE）
  +-- 3a: ファイル内リレーション
  +-- 3b: クロスファイルリレーション

Phase 4: 完了処理
  +-- ファイル削除 or 移動
  +-- 統計サマリー
```

## 関連コマンド

- **graph-queue 生成**: `/emit-graph-queue --command <cmd> --input <file>`
- **ニュース収集**: `/collect-finance-news`
- **銘柄分析**: `/dr-stock`
- **競争優位性評価**: `/ca-eval`
- **レポート生成**: `/generate-market-report`
