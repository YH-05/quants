---
description: Neo4j KGを学術論文で自動拡充（指定時間まで継続）
argument-hint: <duration> (例: "2h", "90m", "until 15:00")
---

# /kg-enrich-auto

alphaxiv MCP で学術論文を自動検索し、Neo4j KG に継続投入します。
指定した時間まで「ギャップ分析→検索→投入→接続→最適化」サイクルを繰り返します。

## 使用例

```bash
/kg-enrich-auto 2h           # 2時間実行
/kg-enrich-auto 90m          # 90分実行
/kg-enrich-auto until 15:00  # 15:00 JST まで実行
/kg-enrich-auto 15m          # 15分テスト実行
```

## 実行手順

### Step 1: 時刻計算

1. `mcp__time__get_current_time(timezone="Asia/Tokyo")` で現在時刻を取得
2. 引数 `$ARGUMENTS` から END_TIME を計算:

| 引数形式 | 計算方法 |
|---------|---------|
| `2h` / `2 hours` | 現在時刻 + 2 時間 |
| `90m` / `90 minutes` | 現在時刻 + 90 分 |
| `until 15:00` | 本日 15:00 JST |
| `until 2026-03-22T18:00` | 指定の ISO 8601 時刻 |

**引数が省略された場合**: ユーザーに実行時間を確認する。

### Step 2: スキル読み込みと実行

1. `.claude/skills/alphaxiv-search/SKILL.md` を読み込む（検索戦略の前提知識）
2. `.claude/skills/kg-enrich-auto/SKILL.md` を読み込む
3. END_TIME を渡してスキルの全フェーズを実行する

### Step 3: 完了報告

スキルの Final Report をユーザーに表示する。

## 前提条件

- Neo4j が起動していること（quants-neo4j: bolt://localhost:7690）
- alphaxiv MCP サーバーが利用可能であること

## 関連コマンド

| コマンド | 説明 |
|---------|------|
| `/kg-quality-check` | KG 品質チェック（投入後の検証に使用） |
| `/save-to-graph` | graph-queue JSON からの投入（本コマンドとは独立） |

$ARGUMENTS
