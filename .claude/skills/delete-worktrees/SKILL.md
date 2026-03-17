---
name: delete-worktrees
description: "複数のworktreeとブランチを一括削除するスキル。/delete-worktrees コマンドで使用。開発完了後、複数のworktreeを効率的にクリーンアップする。"
allowed-tools: Read, Bash, Task
---

# Delete Worktrees - 複数Worktree一括削除

複数の worktree とブランチを一括で削除します。

**目的**: 開発完了後、複数の worktree を効率的にクリーンアップ

## 使用例

```bash
# ブランチ名を指定して一括削除
/delete-worktrees feature/issue-64 feature/issue-67

# 3つ以上も可能
/delete-worktrees feature/issue-64 feature/issue-65 feature/issue-66
```

---

## ステップ 0: 引数解析と事前検証

1. 引数からブランチ名のリストを取得（スペース区切り）
2. **引数がない場合**: 現在のworktree一覧を表示してエラー

```bash
git worktree list
```

3. 各ブランチ名について worktree が存在するか確認
4. 存在しないブランチは警告を表示してリストから除外

---

## ステップ 1: Task ツールで並列削除

**重要**: 単一のメッセージで複数の Task ツール呼び出しを並列実行する。

各ブランチに対して Task ツールを **同時に** 呼び出す:

```
Task(
  subagent_type: "general-purpose",
  description: "worktree cleanup: feature/issue-64",
  prompt: "/worktree-done feature/issue-64 を実行してください。"
)

Task(
  subagent_type: "general-purpose",
  description: "worktree cleanup: feature/issue-67",
  prompt: "/worktree-done feature/issue-67 を実行してください。"
)
```

### 並列実行の要件

- **必須**: 全ての Task 呼び出しを単一のメッセージで送信すること
- 各 Task は独立して `/worktree-done` スキルを実行
- 全ての Task 完了を待機

---

## ステップ 2: 結果サマリー

```
================================================================================
✅ Worktree 一括削除完了
================================================================================

削除数: X 件

| ブランチ | 状態 | 結果 |
|----------|------|------|
| feature/issue-64 | 成功 | worktree, ローカル, リモート削除済み |
| feature/issue-67 | 成功 | worktree, ローカル, リモート削除済み |

## 次のステップ

- 新しい開発を開始: /worktree <feature-name>
- 並列開発計画: /plan-worktrees <project-number>
- メインリポジトリに移動: cd <main-repo-path>

================================================================================
```

---

## エラーハンドリング

| ケース | 対処 |
|--------|------|
| 引数未指定 | エラーメッセージと現在のworktree一覧を表示 |
| worktreeが見つからない | 警告を表示し、次のブランチへ継続 |
| PRが未マージ | `/worktree-done` のエラー処理に従う（スキップまたは中断） |
| 削除失敗 | エラーを表示し、残りのブランチは継続 |

### エラー時の継続判断

各ブランチの削除は独立した Task で並列実行されるため、1つのブランチで失敗しても他は影響を受けません。

結果サマリーで各ブランチの成功/失敗を確認してください。

---

## 注意事項

1. **必ず Task ツールで /worktree-done を実行**: `git worktree remove` を直接使用しない
2. **並列実行**: 全ての Task を単一のメッセージで呼び出して並列削除
3. **PRのマージ確認**: 各 `/worktree-done` がブランチのマージ状態を確認
4. **エラー時も継続**: 1つの worktree 削除に失敗しても、他は継続
5. **mainブランチは削除不可**: `/worktree-done` が検証するため安全

---

## 完了前の確認事項

削除前に以下を確認することを推奨:

1. **PRのマージ状態**: 全てのPRがマージされているか
2. **未コミット変更**: worktreeに未保存の作業がないか
3. **関連Issue**: GitHub Projectで「Done」に移動されるか

---

## 関連コマンド

| コマンド | 説明 |
|----------|------|
| `/plan-worktrees` | 並列開発計画の作成（Wave グルーピング） |
| `/create-worktrees` | 複数の worktree を一括作成 |
| `/worktree-done` | 単一の worktree をクリーンアップ |
| `/worktree` | 単一の worktree を作成 |

---

## ワークフロー例

```bash
# 1. 並列開発計画
/plan-worktrees 1

# 2. Wave 1 のworktreeを一括作成
/create-worktrees 64 67 68

# 開発作業...
# PRマージ...

# 3. 完了したworktreeを一括削除
/delete-worktrees feature/issue-64 feature/issue-67 feature/issue-68
```

---

## 完了条件

- 全ての指定ブランチに対して Task ツールで `/worktree-done` が並列実行されている
- 全ての Task が完了している
- 各ブランチの処理結果（成功/失敗）が記録されている
- 結果サマリーが表示されている
- 次のステップが案内されている
