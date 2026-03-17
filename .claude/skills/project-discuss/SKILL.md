---
name: project-discuss
description: |
  プロジェクトの方向性をユーザーと対話的に議論するスキル。Neo4jグラフDBとドキュメントからコンテキストを復元し、sequential-thinkingで構造化された議論を行い、合意事項をNeo4j+ドキュメントに保存する。
  Use PROACTIVELY when user wants to discuss project direction, brainstorm strategy, review progress, or align on next steps.
allowed-tools: Read, Write, Edit, Bash, Glob, Grep, AskUserQuestion, mcp__neo4j-memory__*, mcp__neo4j-cypher__*, mcp__neo4j-data-modeling__*, mcp__sequential-thinking__*
---

# project-discuss スキル

プロジェクトの方向性についてユーザーと対話的に議論し、合意形成を行うスキル。
Neo4j Memory MCP・Neo4j Cypher MCP・Neo4j Data Modeling MCP を組み合わせ、現状を復元・議論・保存する。

## 使用する MCP サーバー

| MCP サーバー | 用途 |
|-------------|------|
| `mcp__neo4j-memory__*` | エンティティ・リレーション形式で記憶を読み書き |
| `mcp__neo4j-cypher__*` | Cypherクエリで構造化データ（Discussion/Decision/ActionItem）を操作 |
| `mcp__neo4j-data-modeling__*` | ノード・リレーション構造の検証とMermaid可視化 |
| `mcp__sequential-thinking__sequentialthinking` | 議論の構造化・論点整理 |

## 処理フロー

```
Phase 1: コンテキスト復元
    |  neo4j-memory でエンティティ・記憶を検索
    |  neo4j-cypher でプロジェクトノードを取得
    |  docs/plan/ ドキュメント読み込み
    |  sequential-thinking で論点整理
    |
Phase 2: サマリー提示 + 議論
    |  現状サマリーをユーザーに提示
    |  AskUserQuestion で論点ごとに質問（1問ずつ）
    |  各回答を sequential-thinking で分析
    |  必要に応じて Web 調査を挟む
    |
Phase 3: 合意形成 + 保存
    |  neo4j-data-modeling で保存前にノード構造を検証
    |  neo4j-memory に エンティティ/リレーションとして保存
    |  neo4j-cypher で Discussion/Decision/ActionItem ノードを保存
    |  docs/plan/ にメモ保存
    |
Phase 4: アクションアイテム提示
    次のステップを明確化
```

## Phase 1: コンテキスト復元

### 1.1 neo4j-memory でエンティティを検索

まず `mcp__neo4j-memory__search_memories` でプロジェクト関連の記憶を検索する:

```
search_memories("project discussion decision")
search_memories("action item progress")
```

全体俯瞰が必要な場合は `mcp__neo4j-memory__read_graph` でグラフ全体を取得する。

### 1.2 neo4j-cypher でプロジェクトノードを取得

`mcp__neo4j-cypher__read_query` で以下を取得:

```cypher
// プロジェクト関連ノードを取得
MATCH (n)
WHERE n:Project OR n:Discussion OR n:Decision OR n:ActionItem
RETURN labels(n) AS labels, properties(n) AS props
ORDER BY n.created_at DESC
LIMIT 50

// リレーションも取得
MATCH (n)-[r]->(m)
WHERE n:Project OR n:Discussion OR n:Decision
RETURN labels(n) AS from_labels, type(r) AS rel, labels(m) AS to_labels,
       properties(n) AS from_props, properties(m) AS to_props
LIMIT 100
```

### 1.3 ドキュメントの読み込み

`docs/plan/` 配下の関連 Markdown ファイルを読み込む:

```bash
# ファイル一覧取得
Glob docs/plan/*.md

# 最新の議論メモを優先的に読み込み
Glob docs/plan/*discussion*.md
```

### 1.4 sequential-thinking で論点整理

`mcp__sequential-thinking__sequentialthinking` を使い、以下を構造化:

- 現在のプロジェクト状態のサマリー
- これまでの決定事項
- 未解決の論点リスト
- 議論すべきトピックの優先順位

## Phase 2: 議論

### 2.1 サマリー提示

Phase 1 で整理した現状サマリーをユーザーに提示する。
提示内容:
- プロジェクトの現在地（何が決まっていて、何が未決か）
- 前回までの議論のハイライト
- 今回議論すべき論点の提案

### 2.2 対話ループ

以下のループを繰り返す:

1. **AskUserQuestion** で1つの論点について質問
   - **重要**: 一度に1つの論点のみ質問する（複数論点を同時に聞かない）
   - 質問は具体的で回答しやすい形式にする
2. ユーザーの回答を **sequential-thinking** で分析
   - 回答から得られた示唆
   - 追加で確認すべき点
   - 次に聞くべき論点
3. 必要に応じて **Web 調査**を挟む
   - `mcp__tavily__tavily-search` で市場データ・競合情報等を取得
   - 調査結果をユーザーに共有してから次の質問へ
4. 合意が形成されたら次の論点へ

### 2.3 議論の終了判定

以下のいずれかで議論を終了:
- 全論点について合意が得られた
- ユーザーが「ここまでにしよう」等の終了意思を示した
- 十分なアクションアイテムが出揃った

## Phase 3: 保存

### 3.1 neo4j-data-modeling でノード構造を検証（オプション）

新しいノード型やリレーション型を追加する場合、保存前に `mcp__neo4j-data-modeling__validate_data_model` で構造を検証する。

### 3.2 neo4j-memory にエンティティとして保存

`mcp__neo4j-memory__create_entities` で議論結果をエンティティ保存:

```python
create_entities([
    {
        "name": "Discussion:disc-2026-03-17-market-strategy",
        "entityType": "Discussion",
        "observations": [
            "title: 市場戦略の方向性",
            "date: 2026-03-17",
            "summary: ..."
        ]
    }
])
```

`mcp__neo4j-memory__create_relations` でリレーションを保存:

```python
create_relations([
    {
        "from": "Discussion:disc-2026-03-17-market-strategy",
        "to": "Decision:dec-2026-03-17-001",
        "relationType": "RESULTED_IN"
    }
])
```

### 3.3 neo4j-cypher で構造化ノードを保存

`mcp__neo4j-cypher__write_query` で MERGE ベースで保存。

**Discussion ノード**:
```cypher
MERGE (d:Discussion {discussion_id: $discussion_id})
SET d.title = $title,
    d.date = date($date),
    d.summary = $summary,
    d.created_at = datetime()
```

**Decision ノード**:
```cypher
MERGE (dec:Decision {decision_id: $decision_id})
SET dec.content = $content,
    dec.context = $context,
    dec.decided_at = date($date),
    dec.status = 'active'
```

**ActionItem ノード**:
```cypher
MERGE (a:ActionItem {action_id: $action_id})
SET a.description = $description,
    a.priority = $priority,
    a.status = 'pending',
    a.due_date = CASE WHEN $due_date IS NOT NULL THEN date($due_date) ELSE null END,
    a.created_at = datetime()
```

**リレーション**:
```cypher
// Discussion -> Decision
MATCH (d:Discussion {discussion_id: $discussion_id})
MATCH (dec:Decision {decision_id: $decision_id})
MERGE (d)-[:RESULTED_IN]->(dec)

// Discussion -> ActionItem
MATCH (d:Discussion {discussion_id: $discussion_id})
MATCH (a:ActionItem {action_id: $action_id})
MERGE (d)-[:PRODUCED]->(a)

// Project -> Discussion
MATCH (p:Project {name: $project_name})
MATCH (d:Discussion {discussion_id: $discussion_id})
MERGE (p)-[:HAS_DISCUSSION]->(d)
```

### 3.4 ドキュメントへの保存

`docs/plan/` に日付付きメモを保存:

ファイル名: `YYYY-MM-DD_discussion-{topic-slug}.md`

```markdown
# 議論メモ: {トピック}

**日付**: YYYY-MM-DD
**議論ID**: disc-YYYY-MM-DD-{topic-slug}
**参加**: ユーザー + AI

## 背景・コンテキスト

{議論の背景}

## 議論のサマリー

{主要な論点と議論の流れ}

## 決定事項

| ID | 内容 | コンテキスト |
|----|------|------------|
| dec-YYYY-MM-DD-001 | {決定事項1} | {決定の背景} |

## アクションアイテム

| ID | 内容 | 優先度 | 期限 |
|----|------|--------|------|
| act-YYYY-MM-DD-001 | {アクション1} | 高 | YYYY-MM-DD |

## 次回の議論トピック

- {次回議論すべきこと}

## 参考情報

- {Web調査で得た情報等}
```

## Phase 4: アクションアイテム提示

議論の締めくくりとして以下を提示:

1. **決定事項の一覧**: 今回合意した内容
2. **アクションアイテム**: 優先度付きのタスクリスト
3. **次回の議論トピック**: 未解決の論点や次に議論すべきこと
4. **保存先**: Neo4j ノード ID とドキュメントパス

## sequential-thinking の活用方針

以下の場面で **必ず** `mcp__sequential-thinking__sequentialthinking` を使用する:

| 場面 | 用途 |
|------|------|
| Phase 1 完了時 | 収集データの整理、論点の優先順位付け |
| ユーザー回答の分析時 | 回答の示唆分析、次の質問の設計 |
| Web 調査結果の統合時 | 調査結果と議論の関連付け |
| Phase 3 開始前 | DB 保存計画の策定（ノード/リレーション設計） |
| 合意形成時 | 決定事項とアクションアイテムの構造化 |

## Neo4j ノード ID の生成規則

冪等性を保証するため、ID は決定論的に生成する:

| ノード | ID 形式 | 例 |
|--------|---------|-----|
| Discussion | `disc-{YYYY-MM-DD}-{topic-slug}` | `disc-2026-03-17-market-strategy` |
| Decision | `dec-{YYYY-MM-DD}-{sequential}` | `dec-2026-03-17-001` |
| ActionItem | `act-{YYYY-MM-DD}-{sequential}` | `act-2026-03-17-001` |

## MUST / SHOULD / NEVER

### MUST

- sequential-thinking を可能な限り使い、議論を構造化する
- AskUserQuestion で一度に1つの論点のみ質問する
- Phase 1 では neo4j-memory と neo4j-cypher の両方を参照する
- Phase 3 の保存は neo4j-memory（エンティティ） + neo4j-cypher（構造化ノード）の両方に行う
- Neo4j への保存は MERGE ベースで冪等に行う
- ドキュメント保存時はファイル名に日付を含める

### SHOULD

- 新しいノード型を追加する場合は neo4j-data-modeling で事前検証する
- グラフ構造の変更時は get_mermaid_config_str で可視化して確認する
- Web 調査結果はユーザーに共有してから次の質問に進む
- 既存の Decision ノードとの整合性を確認する

### NEVER

- 複数の論点を一度に質問する
- Neo4j への保存で CREATE を使う（MERGE を使うこと）
- コンテキスト復元をスキップして議論を開始する

## 完了条件

- [ ] Phase 1 で neo4j-memory + neo4j-cypher + ドキュメントからコンテキストが復元されている
- [ ] 少なくとも1つの論点について合意が形成されている
- [ ] 決定事項が neo4j-memory にエンティティとして保存されている
- [ ] 決定事項が neo4j-cypher で Discussion/Decision ノードとして保存されている
- [ ] アクションアイテムが ActionItem ノードとして保存されている
- [ ] `docs/plan/` に議論メモが保存されている
- [ ] アクションアイテムと次回議論トピックが提示されている

## 関連リソース

| リソース | パス |
|---------|------|
| 詳細ガイド | `.claude/skills/project-discuss/guide.md` |
| プランドキュメント | `docs/plan/` |
| Neo4j Memory MCP | `mcp__neo4j-memory__*` |
| Neo4j Cypher MCP | `mcp__neo4j-cypher__*` |
| Neo4j Data Modeling MCP | `mcp__neo4j-data-modeling__*` |
| KG スキーマ定義 | `data/config/knowledge-graph-schema.yaml` |
| 名前空間規約 | `.claude/rules/neo4j-namespace-convention.md` |
