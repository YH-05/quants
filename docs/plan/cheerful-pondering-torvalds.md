# Neo4j ナレッジグラフ管理システム移植プラン

## Context

note-finance プロジェクトでは neo4j-cypher + neo4j-data-modeling MCP サーバーを使い、ワークフロー出力を構造化ナレッジグラフとして蓄積・活用している。quants プロジェクトにも同等の仕組みを導入し、dr-stock/ca-eval/finance-news 等の7ワークフロー出力を Neo4j に投入可能にする。

**現状**: quants には Neo4j インスタンス（quants-neo4j, bolt://localhost:7690）と neo4j-memory + neo4j-data-modeling MCP が設定済みだが、KG スキーマ・投入パイプラインは未構築。

**ゴール**: ワークフロー出力 → graph-queue JSON → Neo4j 投入の完全なパイプラインを構築する。

---

## quants 用 KG スキーマ設計

note-finance v2.1（12ノード）をベースに、quants の7ワークフローに最適化して9ノードに簡素化。

### ノード（9種）

| ノード | 説明 | 主な投入元 |
|--------|------|-----------|
| **Source** | 情報ソース（ニュース, レポート, SEC Filing） | 全ワークフロー |
| **Entity** | 企業, 指数, セクター, 国, 通貨, コモディティ | dr-stock, dr-industry, ca-eval |
| **Claim** | 主張・意見・予測・推奨 | ca-eval, dr-stock, finance-research |
| **Fact** | 客観的に検証可能な事実 | dr-stock, ca-eval, market-report |
| **FinancialDataPoint** | 構造化数値データ | dr-stock, market-report |
| **FiscalPeriod** | 会計期間 | dr-stock, market-report |
| **Topic** | トピック/テーマタグ | finance-news, ai-research |
| **Author** | 著者・組織 | ca-eval, dr-stock |
| **Insight** | AI生成分析（合成, 矛盾検出, ギャップ） | dr-stock, ca-eval |

### note-finance v2.1 から除外

- **Chunk**: PDF パイプライン不在のため不要
- **Stance**: セルサイドレポート処理がないため不要
- **Question**: 高度機能、将来追加可能

### リレーション（16種）

STATES_FACT, MAKES_CLAIM, ABOUT, RELATES_TO, TAGGED, AUTHORED_BY, SUPPORTED_BY, CONTRADICTS, HAS_DATAPOINT, FOR_PERIOD, NEXT_PERIOD, TREND, DERIVED_FROM, VALIDATES, CHALLENGES, CAUSES

### 名前空間（4区分）

| 名前空間 | 用途 |
|---------|------|
| `kg_v1` | KG スキーマの9ノード |
| `memory` | neo4j-memory MCP（既存、共存） |
| `conversation` | 会話履歴（将来） |
| `archived` | アーカイブ済み |

---

## 実装 Wave

### Wave 1: 基盤構築

**目標**: Neo4j 接続、KG スキーマ定義、ID 生成モジュール、MCP 設定

| # | 作業 | ファイル | 操作 |
|---|------|---------|------|
| 1-1 | neo4j-cypher MCP 追加 | `.mcp.json` | 変更 |
| 1-2 | KG スキーマ定義（SSoT） | `data/config/knowledge-graph-schema.yaml` | 新規 |
| 1-3 | 制約・インデックス DDL | `data/config/neo4j-constraints.cypher` | 新規 |
| 1-4 | 名前空間規約 | `.claude/rules/neo4j-namespace-convention.md` | 新規 |
| 1-5 | ID 生成モジュール | `src/database/id_generator.py` | 新規 |
| 1-6 | スキーマ検証スクリプト | `scripts/validate_neo4j_schema.py` | 新規 |
| 1-7 | ID 生成テスト | `tests/unit/database/test_id_generator.py` | 新規 |

**移植元**:
- ID 生成: `/Users/yukihata/Desktop/note-finance/src/pdf_pipeline/services/id_generator.py`
- スキーマ検証: `/Users/yukihata/Desktop/note-finance/scripts/validate_neo4j_schema.py`
- 名前空間規約: `/Users/yukihata/Desktop/note-finance/.claude/rules/neo4j-namespace-convention.md`

**ID 生成戦略**（決定論的、MERGE で冪等性保証）:
- Source: `UUID5(url)`
- Entity: `UUID5(f"entity:{name}:{entity_type}")`
- Claim: `SHA-256(content)[:32]`
- Fact: `SHA-256(f"fact:{content}")[:32]`
- Topic: `UUID5(f"topic:{name}:{category}")`
- Author: `UUID5(f"author:{name}:{author_type}")`
- FinancialDataPoint: `SHA-256(f"{source_hash}_{metric}_{period}")[:32]`
- FiscalPeriod: `{ticker}_{period_label}`

### Wave 2: graph-queue パイプライン - 軽量ワークフロー

**目標**: emit_graph_queue.py 基盤 + 3 mapper

| # | 作業 | ファイル | 操作 |
|---|------|---------|------|
| 2-1 | graph-queue 基盤 + 3 mapper | `scripts/emit_graph_queue.py` | 新規 |
| 2-2 | mapper テスト | `tests/unit/test_emit_graph_queue.py` | 新規 |

**対応 mapper**:
- `map_finance_news()`: `.tmp/news-batches/{theme}_articles.json` → Source + Claim + TAGGED
- `map_ai_research()`: `.tmp/ai-research-batches/` → Entity + Source
- `map_market_report()`: `data/{date}/` → Source + Claim + Entity + FinancialDataPoint

**出力先**: `.tmp/graph-queue/{command}/gq-{timestamp}-{rand8}.json`

**移植元**: `/Users/yukihata/Desktop/note-finance/scripts/emit_graph_queue.py`（基盤構造、ヘルパー関数）

### Wave 3: graph-queue パイプライン - リッチワークフロー

**目標**: 複雑な構造変換を伴う4 mapper の実装

| # | 作業 | ファイル | 操作 |
|---|------|---------|------|
| 3-1 | 4 mapper 追加 | `scripts/emit_graph_queue.py` | 変更 |
| 3-2 | mapper テスト追加 | `tests/unit/test_emit_graph_queue.py` | 変更 |

**対応 mapper**:
- `map_dr_stock()`: `research/DR_stock_*/` → Entity + FinancialDataPoint + FiscalPeriod + Claim + Fact（**新規実装**、note-finance に同等なし）
- `map_ca_eval()`: `analyst/research/CA_eval_*/` → Claim + Fact + Insight + SUPPORTED_BY
- `map_dr_industry()`: `research/DR_industry_*/` → Entity + Claim + Fact
- `map_finance_research()`: `articles/*/01_research/` → Source + Claim + SUPPORTED_BY

### Wave 4: save-to-graph スキル移植

**目標**: graph-queue JSON → Neo4j 投入パイプラインの完成

| # | 作業 | ファイル | 操作 |
|---|------|---------|------|
| 4-1 | save-to-graph スキル | `.claude/skills/save-to-graph/SKILL.md` | 新規 |
| 4-2 | 詳細ガイド | `.claude/skills/save-to-graph/guide.md` | 新規 |
| 4-3 | emit-graph-queue コマンド | `.claude/commands/emit-graph-queue.md` | 新規 |
| 4-4 | save-to-graph コマンド | `.claude/commands/save-to-graph.md` | 新規 |

**4フェーズ構成**（note-finance から移植）:
1. キュー検出・Neo4j 接続確認・JSON スキーマ検証
2. ノード投入（MERGE）: Topic → Entity → FiscalPeriod → Source → Author → Fact → Claim → FinancialDataPoint → Insight
3. リレーション投入: (a) ファイル内 + (b) クロスファイル
4. 完了処理（ファイル削除/移動、統計サマリー）

**移植元**: `/Users/yukihata/Desktop/note-finance/.claude/skills/save-to-graph/`

### Wave 5: 統合・ドキュメント

**目標**: 既存ワークフローへの統合フック、ドキュメント整備

| # | 作業 | ファイル | 操作 |
|---|------|---------|------|
| 5-1 | CLAUDE.md にKGコマンド追記 | `CLAUDE.md` | 変更 |
| 5-2 | KG ドキュメント | `docs/knowledge-graph.md` | 新規 |
| 5-3 | dr-stock スキルにフック追加 | `.claude/skills/dr-stock/SKILL.md` | 変更 |
| 5-4 | ca-eval スキルにフック追加 | `.claude/skills/ca-eval/SKILL.md` | 変更 |
| 5-5 | finance-news スキルにフック追加 | `.claude/skills/finance-news-workflow/SKILL.md` | 変更 |
| 5-6 | market-report スキルにフック追加 | `.claude/skills/generate-market-report/SKILL.md` | 変更 |

---

## 依存関係

```
Wave 1 (基盤)
  ├─> Wave 2 (軽量 mapper) ─┐
  └─> Wave 3 (リッチ mapper) ─┤  ← Wave 2/3 は並行可能
                               └─> Wave 4 (save-to-graph)
                                     └─> Wave 5 (統合)
```

## MCP 構成の設計判断

**neo4j-memory は残す**（neo4j-cypher と共存）:
- Memory ノードと KG ノードは名前空間で分離
- neo4j-memory: 軽量な会話メモリ用
- neo4j-cypher: MERGE ベースの構造化 KG 投入用
- neo4j-data-modeling: スキーマ設計・検証用（既存のまま）

## リスクと緩和策

| リスク | 緩和策 |
|--------|--------|
| ワークフロー出力 JSON 構造変更 | mapper を小さく保ち、入力スキーマ変更に追従しやすくする |
| Neo4j CE のマルチラベル MATCH 不可 | CAUSES に `from_label`/`to_label` プロパティで回避 |
| graph-queue JSON 巨大化 | 投入対象を最新5年の年次/四半期に絞り込み |
| neo4j-memory と KG の名前空間衝突 | 規約 + validate_neo4j_schema.py で定期検証 |

## 検証方法

### Wave 1 完了時
```bash
# ID 生成テスト
uv run pytest tests/unit/database/test_id_generator.py -v

# Neo4j 接続確認（neo4j-cypher MCP 経由）
# → read_query で "RETURN 1" が成功すること

# 制約・インデックス投入
# → neo4j-constraints.cypher を実行し、スキーマ検証スクリプトが PASS
python scripts/validate_neo4j_schema.py --schema data/config/knowledge-graph-schema.yaml
```

### Wave 2-3 完了時
```bash
# mapper テスト
uv run pytest tests/unit/test_emit_graph_queue.py -v

# 実データで graph-queue 生成
python scripts/emit_graph_queue.py --command finance-news-workflow --input .tmp/news-batches/index_articles.json
# → .tmp/graph-queue/finance-news-workflow/gq-*.json が生成されること
```

### Wave 4 完了時
```bash
# save-to-graph ドライラン
/save-to-graph --dry-run
# → Cypher クエリが表示され、エラーなし

# 実投入
/save-to-graph --source finance-news-workflow
# → Neo4j Browser (localhost:7477) で Source/Claim ノードが確認可能

# スキーマ検証
python scripts/validate_neo4j_schema.py
# → 全チェック PASS
```

## ファイル一覧（全21ファイル）

| Wave | 新規 | 変更 |
|------|------|------|
| 1 | 6 | 1 |
| 2 | 2 | 0 |
| 3 | 0 | 2 |
| 4 | 4 | 0 |
| 5 | 1 | 5 |
| **合計** | **13** | **8** |
