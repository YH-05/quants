# 議論メモ: Neo4j品質評価とMemory MCP廃止

**日付**: 2026-03-19
**議論ID**: disc-2026-03-19-neo4j-quality-cleanup
**参加**: ユーザー + AI

## 背景・コンテキスト

Neo4jの現状品質を評価したところ、Memory MCP（neo4j-memory）が作成したノード群がKG v2.1スキーマと完全に孤立しており、データ品質も低いことが判明した。

### 評価時点の状態
- 総ノード数: 741 (19ラベル)
- 総リレーション数: 2,012 (30タイプ)
- Memory ノード: 61件（KGノードとの接続0件）

## 議論のサマリー

### 論点1: Memory MCPの必要性

Memory MCPが保持する61ノード（Decision 21, ActionItem 15, Discussion 11, Project 4, Implementation 3, Schema 1, ラベルなし 6）を調査。

**問題点**:
- KG名前空間との接続が **0件**（完全に孤立した島）
- Decision の 55%、ActionItem の 58% で `name` フィールド欠損
- 用途がファイルメモリ・GitHub Issuesと重複
- `observations` 配列にテキストを詰め込む設計で構造化クエリに不向き

**結論**: Memory MCPを廃止し、知識→KG v2.1、判断→ファイルメモリ、タスク→GitHub Issues に一本化。

### 論点2: Decision/ActionItemのnameフィールド

Memory MCP廃止後、nameフィールドの100%欠損が「問題」として挙がったが、ユーザーの指摘によりnameはMemory MCPの`create_entities`が必須としていたフィールドであり、Cypher直接操作では不要と判明。

**結論**: nameフィールドは不要。decision_id+content、action_id+descriptionで十分。

### 論点3: UNIQUE制約の不足

KG v2.1の14ノード中5ノードのみにUNIQUE制約が設定されていた。

**結論**: 残り9ノードにも制約を追加し、14/14を達成。

## 決定事項

| ID | 内容 | コンテキスト |
|----|------|------------|
| dec-2026-03-19-001 | Memory MCP廃止。61ノード+92リレーション削除、.mcp.json定義削除 | KGと孤立、品質低、用途重複 |
| dec-2026-03-19-002 | project-discussスキルをneo4j-cypher専用に移行 | Memory MCP廃止に伴う移行 |
| dec-2026-03-19-003 | Decision/ActionItemのnameフィールドは不要（Memory MCPの名残） | Cypher直接操作ではID+contentで十分 |
| dec-2026-03-19-004 | KG v2.1全14ノードにUNIQUE制約追加完了 | 品質評価で制約不足を検出 |

## 変更したファイル

| ファイル | 変更内容 |
|---------|---------|
| `.mcp.json` | neo4j-memory サーバー定義を削除 |
| `.claude/skills/project-discuss/SKILL.md` | neo4j-memory依存を全削除、Cypher専用に書き換え |
| `.claude/skills/project-discuss/guide.md` | 同上 |
| `.claude/commands/project-discuss.md` | neo4j-memory前提条件を削除 |
| `.claude/rules/neo4j-namespace-convention.md` | memory名前空間削除、conversation名前空間に統合 |
| `data/config/knowledge-graph-schema.yaml` | memory名前空間削除 |

## Neo4j変更

| 操作 | 内容 |
|------|------|
| DELETE | Memory ノード 61件 + リレーション 92件 |
| CREATE CONSTRAINT | 9件（Source, Entity, Claim, Fact, Topic, Author, Insight, FinancialDataPoint, FiscalPeriod） |

## 廃止後の状態

- ノード数: 625 (16ラベル)
- リレーション数: 1,920 (28タイプ)
- UNIQUE制約: 14/14
- 孤立ノード: 1件（Insight 1件のみ）
- 重複: Author "Hao Chen" 1件のみ（軽微）

## 次回の議論トピック

- Author "Hao Chen" 重複の解消
- FinancialDataPoint / FiscalPeriod へのデータ投入（関連ワークフロー実装時）
- KGデータの充実化（Source 114件からの拡張）
