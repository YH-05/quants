# ナレッジマネジメントシステム

**作成日**: 2026-01-22
**ステータス**: 計画中
**GitHub Project**: [#20](https://github.com/users/YH-05/projects/20)

## 背景と目的

### 背景

- **種類**: 新機能の追加
- **課題**: 金融・投資に関するナレッジが分散しており、AIが効率的に参照・活用できる形で管理されていない
- **期間**: 新規プロジェクト

### 目的

金融・投資ナレッジを構造化し、以下を実現する：

1. **知識の構造化**: 情報を体系的に整理・分類
2. **検索性向上**: 必要な情報に素早くアクセス
3. **AIへのコンテキスト提供**: Claudeが知識を参照し推論に活用
4. **知識の蓄積・更新**: 新しい知見を継続的に追加
5. **将来のNeo4j移行**: グラフデータベースへの移行を視野に入れた設計

## スコープ

### 含むもの

- **変更範囲**: 新規追加のみ
- **影響ディレクトリ**:
  - `.claude/` - スキル、エージェント、コマンド
  - `data/` - ナレッジデータファイル
  - `docs/` - プロトコル定義、ドキュメント

### 含まないもの

- Neo4jグラフデータベースの実装（将来フェーズ）
- UI/フロントエンドの実装

## 成果物

| 種類 | 名前 | 説明 |
| ---- | ---- | ---- |
| スキル | `agent-memory` 拡張 | 既存スキルの金融ナレッジ対応強化 |
| データフォーマット | Knowledge Protocol | ナレッジ保存のプロトコル定義 |
| スキル | `knowledge-manager` | ナレッジの登録・検索・更新スキル |
| エージェント | `knowledge-curator` | ナレッジの整理・関連付けエージェント |
| ドキュメント | プロトコル仕様書 | データ構造・メタ情報の定義 |

## 成功基準

- [ ] Claudeが会話中に金融ナレッジを参照できる
- [ ] 会話から新しい知見を簡単に保存できる
- [ ] 知識間の関連付けが表現できる
- [ ] 知識の更新・削除・管理ができる
- [ ] 情報取得日時、ソースURL等のメタ情報が管理できる
- [ ] 情報保管のプロトコルが明確に定義されている
- [ ] Neo4j移行を考慮した設計になっている

## 技術的考慮事項

### 実装アプローチ

**バランス型**: 動作優先と拡張性のバランスを取る

- シンプルなJSON形式でスタート
- Neo4j移行を考慮したスキーマ設計
- MCP Memory との連携を維持

### データ保存形式

**JSONファイル優先**:
- `data/knowledge/` 配下にJSONファイルとして保存
- ファイルベースで透明性確保
- MCP Memory は補助的に活用

### 知識のカテゴリ

1. **金融分析手法**: テクニカル分析、ファンダメンタル分析手法
2. **市場知識**: セクター、銘柄、経済指標の知識
3. **投資戦略**: 戦略パターン、リスク管理手法
4. **カスタム定義**: ユーザーが自由に定義するカテゴリ

### テスト要件

テスト不要（スキル・エージェントのため）

## Knowledge Protocol 設計

### データ構造（Draft）

```json
{
  "id": "uuid",
  "type": "concept|fact|strategy|insight",
  "category": "analysis|market|strategy|custom",
  "title": "知識のタイトル",
  "content": "知識の本文",
  "metadata": {
    "source_url": "情報源URL（あれば）",
    "source_type": "web|paper|conversation|manual",
    "created_at": "ISO8601形式",
    "updated_at": "ISO8601形式",
    "confidence": 0.0-1.0,
    "tags": ["tag1", "tag2"]
  },
  "relations": [
    {
      "type": "relates_to|derived_from|contradicts|supports",
      "target_id": "関連知識のID"
    }
  ]
}
```

### メタ情報の要素

| フィールド | 必須 | 説明 |
|-----------|------|------|
| source_url | No | 情報取得元のURL |
| source_type | Yes | web/paper/conversation/manual |
| created_at | Yes | 知識登録日時 |
| updated_at | Yes | 最終更新日時 |
| confidence | No | 情報の信頼度（0.0-1.0） |
| tags | No | 分類用タグ |

## タスク一覧

### フェーズ1: 基盤構築

- [ ] Knowledge Protocol の仕様策定
  - Issue: [#723](https://github.com/YH-05/quants/issues/723)
  - ステータス: Todo
- [ ] データディレクトリ構造の設計
  - Issue: [#726](https://github.com/YH-05/quants/issues/726)
  - ステータス: Todo

### フェーズ2: コア機能実装

- [ ] `knowledge-manager` スキルの実装
  - Issue: [#730](https://github.com/YH-05/quants/issues/730)
  - ステータス: Todo
  - 機能: 登録、検索、更新、削除
- [ ] `knowledge-curator` エージェントの実装
  - Issue: [#733](https://github.com/YH-05/quants/issues/733)
  - ステータス: Todo
  - 機能: 整理、関連付け、重複検出
- [ ] 既存 `agent-memory` スキルとの統合
  - Issue: [#736](https://github.com/YH-05/quants/issues/736)
  - ステータス: Todo

### フェーズ3: 拡張機能

- [ ] 関連知識の自動提案機能
  - Issue: [#738](https://github.com/YH-05/quants/issues/738)
  - ステータス: Todo
- [ ] 知識のエクスポート機能（Neo4j移行準備）
  - Issue: [#742](https://github.com/YH-05/quants/issues/742)
  - ステータス: Todo

### ドキュメント

- [ ] Knowledge Protocol 仕様書の作成
  - Issue: [#743](https://github.com/YH-05/quants/issues/743)
  - ステータス: Todo
- [ ] 使用ガイドの作成
  - Issue: [#747](https://github.com/YH-05/quants/issues/747)
  - ステータス: Todo

---

**最終更新**: 2026-01-22
