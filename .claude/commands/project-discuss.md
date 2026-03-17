---
description: プロジェクトの方向性を対話的に議論し、合意事項をNeo4j+ドキュメントに保存します
argument-hint: [topic]
---

# /project-discuss - プロジェクト方向性の議論

Neo4j グラフ DB とドキュメントからコンテキストを復元し、ユーザーと対話的に議論を行います。
合意事項は Neo4j（Discussion/Decision/ActionItem ノード）と `docs/plan/` に保存されます。

## スキル

このコマンドは `project-discuss` スキルを呼び出します。

- **スキル定義**: `.claude/skills/project-discuss/SKILL.md`
- **詳細ガイド**: `.claude/skills/project-discuss/guide.md`

## 使用例

```bash
# トピック指定なし（コンテキストから論点を自動提案）
/project-discuss

# トピック指定あり
/project-discuss バックテストエンジンの設計方針

# 前回の議論を再開
/project-discuss 前回の続き
```

## 処理フロー

```
Phase 1: コンテキスト復元
  +-- Neo4j Memory + Cypher でプロジェクト状態を復元
  +-- docs/plan/ からドキュメントを読み込み
  +-- sequential-thinking で論点整理

Phase 2: サマリー提示 + 対話ループ
  +-- 現状サマリーを提示
  +-- AskUserQuestion で1論点ずつ議論
  +-- sequential-thinking で回答分析

Phase 3: 合意形成 + 保存
  +-- Neo4j に Discussion/Decision/ActionItem を MERGE 保存
  +-- docs/plan/ に議論メモを保存

Phase 4: アクションアイテム提示
  +-- 決定事項・アクション・次回トピックを提示
```

## 前提条件

1. Neo4j が起動中であること（quants-neo4j: bolt://localhost:7690）
2. neo4j-memory MCP と neo4j-cypher MCP が利用可能であること

## 保存先

| 保存先 | パス/ノード |
|--------|-----------|
| Neo4j Memory | エンティティ（Discussion, Decision 等） |
| Neo4j Cypher | Discussion / Decision / ActionItem ノード |
| ドキュメント | `docs/plan/YYYY-MM-DD_discussion-{topic}.md` |

## 関連コマンド

- **プロジェクト計画**: `/plan-project`
- **Issue 管理**: `/issue`
- **タスク管理**: `/task`
