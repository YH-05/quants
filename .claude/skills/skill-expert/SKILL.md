---
name: skill-expert
description: "Create and optimize Claude Code skills. Expertise in skill design, SKILL.md structuring, guide/template creation, and best practices for .claude/skills/ system. Use PROACTIVELY when designing new skills or improving existing ones."
allowed-tools: Read, Write, Glob, Grep, AskUserQuestion, Task
---

# Skill Expert

専門的な Claude Code スキルの設計・最適化を行うスキルです。

## 目的

このスキルは以下を提供します：

- **新規スキルの作成**: ナレッジベースとしてのスキル設計とファイル構造の作成
- **既存スキルの改善**: 品質、明確性、使いやすさの最適化
- **スキルのレビュー**: 品質保証とベストプラクティスへの準拠確認
- **フロントマター検証**: Claude Code 公式仕様への準拠確認

## いつ使用するか

### プロアクティブ使用（自動で使用を検討）

以下の状況では、ユーザーが明示的に要求しなくても使用を検討してください：

1. **スキル設計の議論**
   - 「〜スキルを作りたい」
   - 「〜を共有できるナレッジを作りたい」
   - 新しい専門領域のスキルの必要性が明らか

2. **スキル品質の問題**
   - スキルが期待通りに参照されない
   - スキルの内容が不完全または曖昧
   - フロントマターの設定が不適切

3. **スキルシステムの拡張**
   - 新しいワークフローへのスキル統合
   - エージェントへのスキルプリロード設計
   - 既存スキルの機能拡張

### 明示的な使用（ユーザー要求）

- `/skill-expert` コマンド
- 「スキルを作って」「スキルを改善して」などの直接的な要求

## スキル設計原則

### 1. ナレッジベースの原則

スキルは「知識・手順・テンプレート」を提供し、実際の処理は既存ツールを活用します。

**設計方針**:
```yaml
スキルの役割:
  - ガイドライン提供: 何をどうすべきかの知識
  - テンプレート提供: 標準的な出力形式
  - 手順提供: ステップバイステップのプロセス

実処理:
  - MCP サーバー: ファイルシステム、Git 操作
  - gh CLI: GitHub Issue/PR/Project 操作
  - 組み込みツール: Read, Write, Edit, Glob, Grep
```

### 2. 単一責任の原則

各スキルは**1つの明確なドメイン**に特化すべきです。

**良い例**:
- `coding-standards`: Python コーディング規約
- `tdd-development`: TDD 開発プロセス
- `error-handling`: エラーハンドリングパターン

**悪い例**:
- `general-knowledge`: あらゆる知識を含む
- `everything-guide`: 何でもガイドしようとする

### 3. 構造の一貫性

全スキルは以下の標準構造に従います：

```
.claude/skills/{skill-name}/
├── SKILL.md           # エントリーポイント（必須）
├── guide.md           # 詳細ガイド（オプション）
├── template.md        # 出力テンプレート（オプション）
└── examples/          # 使用例・パターン集（オプション）
```

### 4. プリロード最適化

スキルはエージェントのコンテキストにプリロードされるため、簡潔さが重要です。

**コンテキスト効率化**:
- SKILL.md: クイックリファレンス（概要、要点のみ）
- guide.md: 詳細は必要時のみ Read で参照
- examples/: 具体例は必要時のみ参照

## スキルカテゴリ分類

### repository-management（リポジトリ管理）

リポジトリ構造、ドキュメント、プロジェクト管理に関するスキル。

**例**:
- `index`: CLAUDE.md/README.md の自動更新
- `project-management`: GitHub Project と project.md の管理
- `task-decomposition`: タスク分解と依存関係管理
- `issue-creation`: Issue の作成
- `issue-implementation`: Issue の自動実装
- `issue-refinement`: Issue のブラッシュアップ
- `issue-sync`: Issue コメントからの同期

### coding（コーディング）

コード品質、開発プロセス、エラーハンドリングに関するスキル。

**例**:
- `coding-standards`: Python コーディング規約
- `tdd-development`: TDD 開発プロセス
- `error-handling`: エラーハンドリングパターン

### meta（メタスキル）

スキル・エージェント・ワークフロー自体の設計に関するスキル。

**例**:
- `skill-expert`: スキル設計・管理（このスキル）
- `agent-expert`: エージェント設計・管理
- `workflow-expert`: ワークフロー設計・管理

### domain-specific（ドメイン固有）

特定のドメイン（金融、データ分析等）に特化したスキル。

**例**:
- `yfinance-best-practices`: yfinance 使用のベストプラクティス
- `market-analysis`: 市場分析手法
- `sec-edgar`: SEC EDGAR データ取得

## 活用ツールの使用方法

スキルは基本的に既存ツールを活用し、Python スクリプトの実装は最小限に抑えます。

### MCP サーバー（ファイルシステム）

```bash
# ディレクトリツリー取得
mcp__filesystem__directory_tree(
  path=".",
  excludePatterns=["node_modules", ".git", "__pycache__"]
)

# ファイル検索
mcp__filesystem__search_files(
  path=".",
  pattern="**/*.md"
)

# ディレクトリ一覧
mcp__filesystem__list_directory(path=".")
```

### MCP サーバー（Git）

```bash
# ステータス確認
mcp__git__git_status(repo_path=".")

# 差分確認
mcp__git__git_diff(repo_path=".")

# ブランチ作成
mcp__git__git_create_branch(repo_path=".", branch_name="feature/xxx")
```

### gh CLI（GitHub 操作）

```bash
# Issue 一覧
gh issue list --json number,title,state,labels

# Issue 作成
gh issue create --title "タイトル" --body "本文"

# Project Item 一覧
gh project item-list <project_number> --format json

# Project Item 追加
gh project item-add <project_number> --owner @me --url <issue_url>

# PR 作成
gh pr create --title "タイトル" --body "本文"
```

### 組み込みツール

| ツール | 用途 |
|--------|------|
| Read | ファイル読み取り |
| Write | ファイル書き込み（新規作成） |
| Edit | ファイル編集（既存ファイルの部分変更） |
| Glob | パターンマッチング（ファイル検索） |
| Grep | 正規表現検索（内容検索） |

### コード品質ツール

```bash
# フォーマット
make format

# リント
make lint

# 型チェック
make typecheck

# テスト
make test

# 全チェック
make check-all
```

## プロセス

### 1. 要件の分析

スキル作成前に以下を明確化します：

```bash
# 既存のスキルを確認
ls -la .claude/skills/

# 類似スキルの内容を確認
cat .claude/skills/similar-skill/SKILL.md
```

- **ドメイン境界**: スキルの専門領域と提供範囲
- **プリロード先**: どのエージェントにプリロードされるか
- **リソース構成**: guide.md, template.md, examples/ の必要性

### 2. スキル設計

AskUserQuestion ツールを使用して、以下を確認：

- スキルの名前（kebab-case）
- 提供する知識・ガイドライン
- 想定されるプリロード先エージェント
- 必要なリソースファイル

### 3. スキルの実装

標準的なスキル構造：

```markdown
---
name: skill-name
description: Short description for the Skill tool
allowed-tools: Read, Write
---

# Skill Purpose and Context

## 目的

[スキルが提供する価値]

## いつ使用するか

[トリガー条件]

## プロセス

1. Step one
2. Step two
   ...

## リソース

### ./guide.md

[ガイドの内容説明]

### ./template.md

[テンプレートの内容説明]

## 使用例

[3-4 realistic usage examples]

## 品質基準

[MUST/SHOULD criteria]
```

## フロントマター仕様

スキルの SKILL.md ファイルのフロントマターは以下の仕様に従う必要があります。

### 必須フィールド

| フィールド | 必須 | 説明 |
|-----------|------|------|
| `name` | ✓ | スキル名（ディレクトリ名と一致、kebab-case） |
| `description` | ✓ | スキルの説明（1行、改行禁止） |
| `allowed-tools` | - | 使用を許可するツール（省略可） |

### description の書き方

**重要**: `description` は**改行を含めない1行の文字列**で記述すること。

```yaml
# ✓ 正しい例（1行）
description: 新しいworktreeとブランチを作成して開発を開始。/worktree コマンドで使用。

# ✗ 誤った例（改行あり）
description: 新しいworktreeとブランチを作成するスキル。
/worktree コマンドで使用。
```

**理由**:
- 改行を含むと YAML パースエラーの原因になる
- 複数行の場合は `|` ブロックスカラーが必要だが、description には不適切
- Skill ツールの description 表示で見切れる

**description のベストプラクティス**:
- 100文字以内を目安
- 「〜するスキル」ではなく「〜する」で終わる動詞形
- コマンド名を含める（例: `/worktree コマンドで使用`）
- トリガーキーワードを含める

### allowed-tools の設定

必要最小限のツールのみを指定：

```yaml
# 読み取りのみ
allowed-tools: Read

# 読み書き
allowed-tools: Read, Write, Edit

# GitHub 操作を含む
allowed-tools: Read, Write, Bash, Task
```

### 4. テストとバリデーション

作成後の確認項目：

- [ ] フロントマターが正しく設定されている
- [ ] name がディレクトリ名と一致
- [ ] description が1行で改行を含まない
- [ ] description が簡潔で目的を説明
- [ ] allowed-tools が最小限に設定
- [ ] 実用的な例が3個以上含まれている
- [ ] リソースファイルが正しく参照されている

### 5. 既存スキルのブラッシュアップ

既存スキルを改善する際は、AskUserQuestion ツールで情報収集します：

**確認項目**:
- 現状の問題点
- 使用頻度と重要度
- 期待する改善点
- 具体的なユースケース
- 成功基準

## リソース

このスキルには以下のリソースが含まれています（後続 Issue で作成予定）：

### ./guide.md

スキル設計の詳細ガイド：

- スキル構造（SKILL.md + guide.md + examples/）の説明
- プロンプトエンジニアリングガイド
- スキルフロントマター検証ルール

### ./template.md

標準的なスキルテンプレート：

- スキル用フロントマター構造
- スキルセクション構成
- コメント付きガイド

### ../agent-expert/frontmatter-review.md

フロントマターレビューガイド（agent-expert と共有）：

- スキルフロントマター検証ルール
- allowed-tools の検証
- description の品質基準

## 使用例

### 例1: 新規スキルの作成

**状況**: コーディング規約を共有するスキルを作成したい

**処理**:
1. 要件を明確化（AskUserQuestion 使用）
2. 既存スキルを調査
3. SKILL.md を作成
4. guide.md, template.md を作成（必要に応じて）
5. バリデーション実行

**期待される出力**:
```
.claude/skills/coding-standards/
├── SKILL.md
├── guide.md
└── examples/
    ├── type-hints.md
    ├── docstrings.md
    └── naming.md
```

---

### 例2: 既存スキルの改善

**状況**: project-management スキルの description が曖昧

**処理**:
1. 現在の SKILL.md を読み込み
2. AskUserQuestion で改善ポイントを収集
3. description を具体的なトリガーキーワードで更新
4. 使用例を追加
5. バリデーション実行

**期待される出力**:
```markdown
# 改善前
description: プロジェクト管理

# 改善後
description: |
  GitHub Project と project.md の作成・管理・同期を行うスキル。
  /new-project, /project-refine コマンドで使用。
```

---

### 例3: スキルフロントマターの検証

**状況**: 新しく作成したスキルの品質を検証したい

**処理**:
1. SKILL.md を読み込み
2. フロントマター検証チェックリストを実行
3. 問題点をレポート
4. 修正提案を提示

**期待される出力**:
```yaml
検証結果:
  name: ✓ ディレクトリ名と一致
  description: ✗ トリガーキーワードが不足
  allowed-tools: ✓ 最小限に設定

推奨修正:
  description: 「〜の場合に使用」を追加
```

---

### 例4: エージェントへのスキルプリロード設計

**状況**: feature-implementer エージェントにスキルをプリロードしたい

**処理**:
1. feature-implementer エージェントの責任範囲を確認
2. 関連するスキルを特定
3. フロントマターに skills: フィールドを追加
4. スキルの依存関係を検証

**期待される出力**:
```yaml
---
name: feature-implementer
skills:
  - coding-standards
  - tdd-development
  - error-handling
---
```

## 品質基準

このスキルの成果物は以下の品質基準を満たす必要があります：

### 必須（MUST）

- [ ] フロントマターの name がディレクトリ名と一致
- [ ] description が簡潔でトリガーキーワードを含む
- [ ] allowed-tools が必要最小限に設定
- [ ] 実用的な使用例が3つ以上含まれている
- [ ] リソースファイル（guide.md 等）が SKILL.md で参照されている

### 推奨（SHOULD）

- プロセスがステップバイステップで説明されている
- 品質基準（MUST/SHOULD）が定義されている
- エラーハンドリングが含まれている
- 関連スキルへの参照がある

## 出力フォーマット

### スキル作成時

```
================================================================================
                    スキル作成完了
================================================================================

## 作成したスキル
- 名前: {skill_name}
- 配置先: .claude/skills/{skill_name}/

## ファイル構成
- SKILL.md: ✓ 作成
- guide.md: ✓ 作成 / - 不要
- template.md: ✓ 作成 / - 不要
- examples/: ✓ 作成 / - 不要

## 検証結果
| 項目 | 状態 |
|------|------|
| フロントマター | ✓ |
| 使用例 | ✓ ({n}個) |
| 品質基準 | ✓ |

================================================================================
```

### フロントマター検証時

```yaml
検証結果:
  name:
    value: "{actual_value}"
    status: "✓ / ✗"
    issue: "{問題点があれば}"
  description:
    value: "{actual_value}"
    status: "✓ / ✗"
    issue: "{問題点があれば}"
  allowed-tools:
    value: "{actual_value}"
    status: "✓ / ✗"
    issue: "{問題点があれば}"

総合判定: PASS / FAIL
推奨修正: [{修正内容}]
```

## エラーハンドリング

### スキルが参照されない

**原因**:
1. description にトリガーキーワードがない
2. skills: フィールドでの参照漏れ

**対処法**:
- description を見直し、明確なトリガーワードを追加
- 関連エージェントの skills: フィールドを確認

### リソースファイルが見つからない

**原因**:
1. guide.md/template.md が存在しない
2. パスの指定ミス

**対処法**:
- リソースファイルの存在を確認
- SKILL.md での参照パスを修正

### フロントマター検証エラー

**原因**:
1. YAML 構文エラー
2. 必須フィールドの欠落

**対処法**:
- YAML 構文を修正
- 必須フィールド（name, description）を追加

## 完了条件

このスキルは以下の条件を満たした場合に完了とする：

- [ ] スキルディレクトリが作成されている
- [ ] SKILL.md が作成され、フロントマターが正しい
- [ ] 必要なリソースファイルが作成されている
- [ ] フロントマター検証がパスしている
- [ ] 使用例が3つ以上含まれている

## 関連スキル

- **agent-expert**: エージェント設計・管理（スキルプリロード設計で連携）
- **workflow-expert**: ワークフロー設計・管理（スキル連携パターンで連携）

## 参考資料

- `CLAUDE.md`: プロジェクト全体のガイドライン
- `template/skill/SKILL.md`: スキルテンプレート
- `.claude/skills/agent-expert/`: 参考実装（類似構造）
- `docs/plan/2026-01-21_System-Update-Implementation.md`: システム更新計画書
