---
description: graph-queue JSON を生成します（各種ワークフロー出力 → Neo4j 投入用 JSON 変換）
argument-hint: --command <command> --input <path> [--cleanup]
---

# /emit-graph-queue - graph-queue JSON 生成

各種ワークフローの出力データを graph-queue JSON に変換し、`.tmp/graph-queue/` に出力します。
生成された JSON は `/save-to-graph` で Neo4j に投入できます。

## 引数の解析

ユーザーの入力から以下のパラメータを判定してください:

| パラメータ | 必須 | 説明 |
|-----------|------|------|
| `--command` | ✅ | 対象コマンド（下表参照） |
| `--input` | ✅ | 入力ファイルパス |
| `--cleanup` | - | 7日超の古いキューファイルを削除 |

### 対応コマンド一覧

| コマンド名 | 入力パス例 | 主な生成ノード |
|-----------|-----------|--------------|
| `finance-news-workflow` | `.tmp/news-batches/index_articles.json` | Source, Claim, Topic |
| `ai-research-collect` | `.tmp/ai-research-batches/*.json` | Entity, Source |
| `generate-market-report` | `data/{date}/*.json` | Source, Entity, FinancialDataPoint |
| `dr-stock` | `research/DR_stock_*/03_analysis/stock-analysis.json` | Entity, FinancialDataPoint, FiscalPeriod, Claim, Fact |
| `ca-eval` | `analyst/research/CA_eval_*/02_claims/claims.json` | Claim, Fact, Insight |
| `dr-industry` | `research/DR_industry_*/03_analysis/*.json` | Entity, Claim, Fact |
| `finance-research` | `articles/*/01_research/*.json` | Source, Claim |

## 実行手順

### Step 1: 引数が省略された場合の対話的確認

`--command` または `--input` が未指定の場合、ユーザーに確認してください。

### Step 2: 入力パスの存在確認

```bash
test -f "${INPUT_PATH}" && echo "OK" || echo "ERROR: File not found"
```

### Step 3: emit_graph_queue.py の実行

```bash
uv run python scripts/emit_graph_queue.py \
  --command "${COMMAND}" \
  --input "${INPUT_PATH}"
```

`--cleanup` が指定された場合は末尾に `--cleanup` を追加。

### Step 4: 結果報告

```markdown
## graph-queue 生成完了

| 項目 | 値 |
|------|-----|
| コマンド | ${COMMAND} |
| 入力 | ${INPUT_PATH} |
| 出力 | ${OUTPUT_FILE} |

次のステップ: `/save-to-graph` で Neo4j に投入
```

## 使用例

```bash
# dr-stock: 銘柄分析から graph-queue 生成
/emit-graph-queue --command dr-stock --input research/DR_stock_20260213_MCO/03_analysis/stock-analysis.json

# ca-eval: 競争優位性評価から生成
/emit-graph-queue --command ca-eval --input analyst/research/CA_eval_20260220-0931_MCO/02_claims/claims.json

# finance-news: ニュースバッチから生成
/emit-graph-queue --command finance-news-workflow --input .tmp/news-batches/index_articles.json

# 古いキューファイルを削除しつつ生成
/emit-graph-queue --command dr-stock --input research/DR_stock_20260213_MCO/03_analysis/stock-analysis.json --cleanup
```

## 関連コマンド

- **Neo4j 投入**: `/save-to-graph`（生成済み graph-queue JSON → Neo4j）
- **銘柄分析**: `/dr-stock`（ソースデータ生成）
- **競争優位性評価**: `/ca-eval`（ソースデータ生成）
- **ニュース収集**: `/collect-finance-news`（ソースデータ生成）

## 関連リソース

| リソース | パス |
|---------|------|
| 生成スクリプト | `scripts/emit_graph_queue.py` |
| graph-queue 出力先 | `.tmp/graph-queue/{command}/` |
| save-to-graph スキル | `.claude/skills/save-to-graph/SKILL.md` |
| KG スキーマ定義 | `data/config/knowledge-graph-schema.yaml` |
