# project-discuss 詳細ガイド

## sequential-thinking 活用パターン

### パターン1: コンテキスト復元後の論点整理

```json
{
  "thought": "Neo4jとドキュメントから以下の情報を収集した。\n\n【Neo4j Cypher】\n- Project: quants (status: active)\n- Decision: バックテストエンジン設計方針 (2026-02-25)\n- ActionItem: factor パッケージのテスト追加 (status: pending)\n\n【ドキュメント】\n- backtest-engine-design.md: バックテストエンジン設計\n- ca-strategy-batch-parallel.md: CA Strategy並列実行\n\n【論点の整理】\n1. バックテストエンジンの実装優先度（未決定）\n2. CA Strategy の本番化判断（議論中）\n3. 新規パッケージの優先順位（未決定）\n\n【優先順位】\n2 → 1 → 3 の順で議論するのが効率的。CA Strategyの判断が他の優先度に影響する。",
  "nextThoughtNeeded": true,
  "thoughtNumber": 1,
  "totalThoughts": 3
}
```

### パターン2: ユーザー回答の分析

```json
{
  "thought": "ユーザーの回答: 「CA Strategyはまずバックテスト結果を見てから判断したい」\n\n【分析】\n- バックテストが前提条件 → エンジン設計が先決\n- CA Strategy本番化の判断は保留\n- リソース配分: バックテストエンジン > CA Strategy\n\n【追加で確認すべき点】\n- バックテストの対象期間・ユニバース\n- 既存のvectorbtとの併用 vs 自前実装\n- いつまでにバックテスト結果が欲しいか\n\n【次の質問候補】\n→ バックテストエンジンの実装スコープを具体化する質問が最優先",
  "nextThoughtNeeded": false,
  "thoughtNumber": 1,
  "totalThoughts": 1
}
```

### パターン3: DB保存計画の策定

```json
{
  "thought": "今回の議論結果を保存する計画:\n\n【Discussionノード】\ndisc-2026-03-17-backtest-priority\n- title: バックテストエンジン優先度の議論\n- summary: CA Strategy判断前にバックテスト結果が必要\n\n【Decisionノード】\n1. dec-2026-03-17-001: name='バックテストエンジン最優先実装', content=...\n2. dec-2026-03-17-002: name='CA Strategy本番化判断保留', content=...\n\n【ActionItemノード】\n1. act-2026-03-17-001: name='バックテストMVP実装', description=..., 優先度: 高\n2. act-2026-03-17-002: name='テスト用データ準備', description=..., 優先度: 高\n\n【リレーション】\n- quants -[:HAS_DISCUSSION]-> disc-2026-03-17-backtest-priority\n- disc-... -[:RESULTED_IN]-> dec-2026-03-17-001, dec-2026-03-17-002\n- disc-... -[:PRODUCED]-> act-2026-03-17-001, act-2026-03-17-002",
  "nextThoughtNeeded": false,
  "thoughtNumber": 1,
  "totalThoughts": 1
}
```

## AskUserQuestion の質問設計

### 良い質問の例

```
# 具体的で回答しやすい
"バックテストエンジンの実装について、vectorbt をラップする形と
自前で Zipline ベースで作る形がありますが、どちらが良いと思いますか？
現在の factor パッケージとの統合を考えると自前の方が柔軟性がありますが、
工数は大きくなります。"

# 選択肢を提示
"次の開発スプリントで優先すべきパッケージはどれですか？
1. strategy（ポートフォリオ管理・リバランス）
2. factor（ファクター投資の拡充）
3. バックテストエンジン（新規）"

# 前回の決定を踏まえた深掘り
"前回『バックテスト優先』で合意しましたが、最初のMVPとして
どの戦略をバックテスト対象にしますか？候補:
- CA Strategy（競争優位性ベース）
- モメンタム + クオリティ（factor パッケージ既存）
- セクターローテーション（analyze パッケージ既存）"
```

### 悪い質問の例（避けるべき）

```
# 複数論点を同時に聞いている
"バックテストの設計と CA Strategy の方向性と次のパッケージについて教えてください"

# 抽象的すぎる
"プロジェクトについてどう思いますか？"

# Yes/Noで終わってしまう
"この方向で良いですか？"
```

## Neo4j クエリ集

### コンテキスト復元クエリ

```cypher
// プロジェクト全体の状態を取得
MATCH (p:Project)-[r]->(n)
RETURN p.name AS project, type(r) AS relation, labels(n) AS node_type,
       properties(n) AS details
ORDER BY CASE type(r)
  WHEN 'HAS_DISCUSSION' THEN 1
  WHEN 'RESULTED_IN' THEN 2
  WHEN 'PRODUCED' THEN 3
  ELSE 4
END

// 最近の議論を取得
MATCH (d:Discussion)
OPTIONAL MATCH (d)-[:RESULTED_IN]->(dec:Decision)
OPTIONAL MATCH (d)-[:PRODUCED]->(a:ActionItem)
RETURN d, collect(DISTINCT dec) AS decisions, collect(DISTINCT a) AS actions
ORDER BY d.date DESC
LIMIT 10

// 未完了のアクションアイテムを取得
MATCH (a:ActionItem {status: 'pending'})
OPTIONAL MATCH (d:Discussion)-[:PRODUCED]->(a)
RETURN a.description, a.priority, a.due_date, d.title AS from_discussion
ORDER BY
  CASE a.priority WHEN 'high' THEN 1 WHEN 'medium' THEN 2 ELSE 3 END
```

### 保存クエリ

```cypher
// Project ノードの確認/作成
MERGE (p:Project {name: $project_name})
SET p.updated_at = datetime()

// Discussion ノードの保存
MERGE (d:Discussion {discussion_id: $discussion_id})
SET d.title = $title,
    d.date = date($date),
    d.summary = $summary,
    d.topics = $topics,
    d.created_at = datetime()

// Decision ノードの保存
MERGE (dec:Decision {decision_id: $decision_id})
SET dec.content = $content,
    dec.context = $context,
    dec.decided_at = date($date),
    dec.status = 'active',
    dec.created_at = datetime()

// ActionItem ノードの保存
MERGE (a:ActionItem {action_id: $action_id})
SET a.description = $description,
    a.priority = $priority,
    a.status = 'pending',
    a.due_date = CASE WHEN $due_date IS NOT NULL THEN date($due_date) ELSE null END,
    a.created_at = datetime()

// ActionItem のステータス更新
MATCH (a:ActionItem {action_id: $action_id})
SET a.status = $new_status,
    a.completed_at = CASE WHEN $new_status = 'completed' THEN datetime() ELSE null END
```

## ドキュメント保存テンプレート

### 議論メモテンプレート

```markdown
# 議論メモ: {トピック}

**日付**: YYYY-MM-DD
**議論ID**: disc-YYYY-MM-DD-{topic-slug}
**参加**: ユーザー + AI

## 背景・コンテキスト

{議論の背景。前回の議論からの続きであればその旨を記載}

## 議論のサマリー

### 論点1: {論点}

{議論の内容}

**結論**: {合意事項}

### 論点2: {論点}

{議論の内容}

**結論**: {合意事項}

## 決定事項

| ID | 内容 | コンテキスト |
|----|------|------------|
| dec-YYYY-MM-DD-001 | {決定事項1} | {決定の背景} |
| dec-YYYY-MM-DD-002 | {決定事項2} | {決定の背景} |

## アクションアイテム

| ID | 内容 | 優先度 | 期限 |
|----|------|--------|------|
| act-YYYY-MM-DD-001 | {アクション1} | 高 | YYYY-MM-DD |
| act-YYYY-MM-DD-002 | {アクション2} | 中 | - |

## 次回の議論トピック

- {次回議論すべきこと1}
- {次回議論すべきこと2}

## 参考情報

### Web調査結果

{Web調査で得た情報があれば記載}

### 関連ドキュメント

- {関連する既存ドキュメントへのリンク}
```

## エラーハンドリング

| エラー | 対処 |
|--------|------|
| Neo4j 接続失敗 | ドキュメントのみでコンテキスト復元を行い、Neo4j保存はスキップ。ユーザーに通知する |
| docs/plan/ にディスカッションメモなし | 初回議論として扱い、プロジェクトの概要から聞き始める |
| sequential-thinking が利用不可 | スキル内で直接分析を行う（品質は落ちるが続行可能） |
| Web 調査が失敗 | 調査なしで議論を継続。ユーザーに調査失敗を通知 |

## 議論の再開パターン

前回の議論を引き継ぐ場合:

1. Neo4j から最新の Discussion ノードを取得
2. 関連する Decision と ActionItem を復元
3. ActionItem のステータスを確認（完了/未完了）
4. 未完了アイテムの進捗確認から議論を開始
5. 新しい論点があれば追加
