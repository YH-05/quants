---
description: GitHub Projectを参照し、Todoの Issue を並列開発用にグルーピング表示。連続開発グループも提案。
skill-preload: plan-worktrees
---

# /plan-worktrees - Worktree 並列開発計画

> **スキル参照**: `.claude/skills/plan-worktrees/SKILL.md`

GitHub Project の Todo 状態の Issue を分析し、worktree による並列開発のためのグルーピングを提案します。
また、同一 worktree 内で `/issue-implementation` の複数 Issue 連続実装が可能なグループも提案します。

**目的**:
- 依存関係を考慮した並列開発計画の可視化
- worktree 内での連続開発グループの提案

**出力形式**:
- REPL出力: アスキーアート・テーブル形式（mermaid禁止）
- ファイル出力: mermaid使用可

## コマンド構文

```bash
# GitHub Project 番号を指定
/plan-worktrees <project_number>

# 例
/plan-worktrees 1
/plan-worktrees 3
```

---

## ステップ 0: 引数解析

1. 引数から GitHub Project 番号を取得
2. **引数がない場合**: AskUserQuestion でヒアリング

```yaml
questions:
  - question: "対象の GitHub Project 番号を入力してください"
    header: "Project番号"
    options:
      - label: "プロジェクト一覧を表示"
        description: "gh project list で一覧を確認"
      - label: "番号を直接入力"
        description: "プロジェクト番号を入力"
```

**プロジェクト一覧の表示**:

```bash
gh project list --owner "@me" --format json
```

---

## ステップ 1: プロジェクト情報の取得

### 1.1 認証確認

```bash
gh auth status
```

**認証スコープ不足の場合**:

```
エラー: GitHub Project へのアクセス権限がありません。

解決方法:
gh auth refresh -s project
```

### 1.2 プロジェクト Item の取得

```bash
gh project item-list <project_number> --owner "@me" --format json --limit 100
```

### 1.3 プロジェクトフィールドの取得

```bash
gh project field-list <project_number> --owner "@me" --format json
```

**プロジェクトが存在しない場合**:

```
エラー: Project #<number> が見つかりません。

解決方法:
gh project list --owner "@me" でプロジェクト一覧を確認してください。
```

---

## ステップ 2: Todo Issue のフィルタリング

取得したアイテムから以下の条件でフィルタリング:

1. **status が "Todo"** のアイテムのみ抽出
2. **type が "Issue"** のアイテムのみ（Draft は除外）
3. 各アイテムから以下の情報を抽出:
   - `number`: Issue 番号
   - `title`: タイトル
   - `labels`: ラベル配列
   - `body`: 本文（依存関係解析用）
   - `url`: Issue URL
   - `repository`: リポジトリ名

**Todo Issue がない場合**:

```
Project #<number> に Todo 状態の Issue がありません。

現在のステータス:
- In Progress: X 件
- Done: Y 件

次のステップ:
- 新しい Issue を作成して Project に追加
- In Progress の Issue を確認
```

---

## ステップ 3: 依存関係の解析

各 Issue の body から依存関係を抽出:

### 3.1 依存関係パターンの検出

以下のパターンを検索:

```markdown
## 依存タスク
- [ ] #<number>
- [x] #<number>

depends on #<number>
depends_on: #<number>
blocked by #<number>
requires #<number>
```

### 3.2 依存グラフの構築

```python
# 依存関係グラフ（概念）
dependencies = {
    12: [9, 10, 11],  # Issue #12 は #9, #10, #11 に依存
    15: [12],         # Issue #15 は #12 に依存
    10: [],           # Issue #10 は依存なし
}
```

### 3.3 循環依存の検出

循環依存がある場合は警告:

```
警告: 循環依存を検出しました

#10 → #12 → #15 → #10

解決方法:
Issue の依存関係を見直してください。
```

---

## ステップ 4: Wave グルーピング

依存関係に基づいて Issue を「Wave（波）」にグルーピング:

### 4.1 Wave の定義

| Wave | 条件 | 並列開発 |
|------|------|----------|
| Wave 1 | 依存関係なし、または全ての依存が Done | 即座に並列開発可能 |
| Wave 2 | Wave 1 の Issue に依存 | Wave 1 完了後に開発可能 |
| Wave 3 | Wave 2 の Issue に依存 | Wave 2 完了後に開発可能 |
| ... | ... | ... |

### 4.2 グルーピングアルゴリズム

```python
# 概念的なアルゴリズム
def assign_waves(issues, dependencies, done_issues):
    waves = {}
    remaining = set(issues)
    current_wave = 1

    while remaining:
        # このWaveで開発可能なIssue
        ready = []
        for issue in remaining:
            deps = dependencies.get(issue, [])
            # 依存がDoneまたは前のWaveに含まれていれば開発可能
            if all(d in done_issues or d in assigned for d in deps):
                ready.append(issue)

        if not ready:
            # 残りは循環依存または未解決の依存あり
            waves["unresolved"] = list(remaining)
            break

        waves[current_wave] = ready
        assigned.update(ready)
        remaining -= set(ready)
        current_wave += 1

    return waves
```

### 4.3 サブグルーピング（Wave 内）

同じ Wave 内でさらにグルーピング:

1. **ラベルベース**: `type:*`, `phase:*` でグルーピング
2. **優先度ソート**: `priority:high` → `priority:medium` → `priority:low`
3. **リポジトリベース**: 異なるリポジトリの Issue は自然に並列開発可能

---

## ステップ 4.5: 連続開発グルーピング（NEW）

同一 worktree 内で `/issue-implementation` の複数 Issue 連続実装が可能なグループを判定します。

### 4.5.1 連続開発可能条件

以下の **全て** を満たす Issue は同一 worktree で連続開発できます：

| 条件 | 説明 |
|------|------|
| 同一開発タイプ | python / agent / command / skill |
| 順序的依存 | A → B → C のような直列依存 |
| 同一対象パッケージ | 同じパッケージ/ディレクトリ |

### 4.5.2 開発タイプの判定

Issue のラベルまたはキーワードから判定：

- ラベルに `agent`/`command`/`skill` を含む → 該当タイプ
- 本文に `.claude/agents/` 等のパスを含む → 該当タイプ
- 上記以外 → `python`

### 4.5.3 対象パッケージの特定

Issue 本文から `src/<package>/` や `packages/<package>/` のパターンを検出。

### 4.5.4 連続開発チェーンの構築

依存関係が直列（A → B → C）の Issue をチェーン化し、`/issue-implementation A B C` の形式で提案。

---

## ステップ 5: 結果表示

### 5.1 サマリー表示

```
================================================================================
📋 Worktree 並列開発計画
================================================================================

Project: #<number>
リポジトリ: <repository>
Todo Issue: X 件
Wave 数: Y

================================================================================
```

### 5.2 Wave ごとの Issue 一覧（タイプ・パッケージ情報付き）

```markdown
## 🌊 Wave 1（即座に並列開発可能）

| # | タイトル | タイプ | パッケージ | 優先度 |
|---|----------|--------|------------|--------|
| #10 | utils モジュール追加 | python | finance | high |
| #11 | 分析エージェント追加 | agent | - | high |

## 🌊 Wave 2（Wave 1 完了後）

| # | タイトル | 依存 | タイプ | パッケージ |
|---|----------|------|--------|------------|
| #12 | helpers 拡張 | #10 | python | finance |
| #13 | 連携機能追加 | #11 | agent | - |
```

### 5.3 連続開発グループの表示（NEW）

Wave を跨いで連続開発可能なグループを表示します。

```markdown
## 🔗 連続開発グループ（推奨）

### グループ 1: finance パッケージ - Python 開発
| # | タイトル | Wave | 依存 |
|---|----------|------|------|
| #10 | utils モジュール追加 | 1 | - |
| #12 | helpers 拡張 | 2 | #10 |

**連続実装コマンド**:
```bash
/worktree feature/finance-utils
/issue-implementation 10 12
```

### グループ 2: agent 開発
| # | タイトル | Wave | 依存 |
|---|----------|------|------|
| #11 | 分析エージェント追加 | 1 | - |
| #13 | 連携機能追加 | 2 | #11 |

**連続実装コマンド**:
```bash
/worktree feature/analysis-agent
/issue-implementation 11 13
```

### 単独開発 Issue
| # | タイトル | Wave | 理由 |
|---|----------|------|------|
| #16 | CI設定追加 | 1 | 依存なしの独立タスク |
```

### 5.4 推奨開発フロー

```markdown
## 📝 推奨開発フロー

### 連続開発グループを活用（最効率）

```bash
# ターミナル 1: グループ 1
/worktree feature/finance-utils
/issue-implementation 10 12   # 連続実装 → 1 PR

# ターミナル 2: グループ 2
/worktree feature/analysis-agent
/issue-implementation 11 13   # 連続実装 → 1 PR
```

**メリット**:
- Wave を待たずに連続開発
- コンテキストスイッチを最小化
- 関連 Issue が 1 つの PR にまとまる
```

---

## ステップ 6: 追加情報（オプション）

### 6.1 ラベル別サマリー

```markdown
## 📊 ラベル別サマリー

| ラベル | Issue 数 | Wave 分布 |
|--------|----------|-----------|
| priority:high | 3 | Wave 1: 2, Wave 2: 1 |
| priority:medium | 5 | Wave 1: 1, Wave 2: 3, Wave 3: 1 |
| type:feature | 4 | Wave 1: 2, Wave 2: 2 |
| type:test | 2 | Wave 2: 2 |
```

### 6.2 クリティカルパス

```markdown
## 🛤️ クリティカルパス

最も長い依存チェーン:

#10 → #12 → #15 → #18（4 ステップ）

このパスの Issue を優先的に完了させることで、全体のリードタイムを短縮できます。
```

---

## エラーハンドリング

| ケース | 対処 |
|--------|------|
| 引数未指定 | プロジェクト番号のヒアリング |
| プロジェクトが存在しない | エラーメッセージとプロジェクト一覧表示 |
| 認証スコープ不足 | `gh auth refresh -s project` を案内 |
| Todo Issue なし | ステータス別件数を表示 |
| 循環依存 | 警告と該当 Issue を表示 |
| 存在しない Issue への依存 | 警告と該当 Issue を表示 |

---

## 出力例

```
================================================================================
📋 Worktree 並列開発計画
================================================================================

Project: #1
リポジトリ: YH-05/quants
Todo Issue: 5 件
Wave 数: 2
連続開発グループ: 2 グループ

================================================================================

## 🌊 Wave 1（即座に並列開発可能）- 3 件

| # | タイトル | タイプ | パッケージ | 優先度 |
|---|----------|--------|------------|--------|
| #10 | utils モジュール追加 | python | finance | high |
| #11 | 分析エージェント追加 | agent | - | high |
| #16 | CI設定追加 | python | - | medium |

## 🌊 Wave 2（Wave 1 完了後）- 2 件

| # | タイトル | 依存 | タイプ | パッケージ |
|---|----------|------|--------|------------|
| #12 | helpers 拡張 | #10 | python | finance |
| #13 | 連携機能追加 | #11 | agent | - |

================================================================================

## 🔗 連続開発グループ（推奨）

### グループ 1: finance パッケージ - Python 開発
| # | タイトル | Wave | 依存 |
|---|----------|------|------|
| #10 | utils モジュール追加 | 1 | - |
| #12 | helpers 拡張 | 2 | #10 |

```bash
/worktree feature/finance-utils
/issue-implementation 10 12
```

### グループ 2: agent 開発
| # | タイトル | Wave | 依存 |
|---|----------|------|------|
| #11 | 分析エージェント追加 | 1 | - |
| #13 | 連携機能追加 | 2 | #11 |

```bash
/worktree feature/analysis-agent
/issue-implementation 11 13
```

### 単独開発 Issue
| # | タイトル | Wave |
|---|----------|------|
| #16 | CI設定追加 | 1 |

```bash
/worktree feature/ci-setup
/issue-implementation 16
```

================================================================================

## 📝 推奨開発フロー

### 連続開発グループを活用（最効率）

```bash
# ターミナル 1: グループ 1（2 Issue → 1 PR）
/worktree feature/finance-utils
/issue-implementation 10 12

# ターミナル 2: グループ 2（2 Issue → 1 PR）
/worktree feature/analysis-agent
/issue-implementation 11 13

# ターミナル 3: 単独 Issue
/worktree feature/ci-setup
/issue-implementation 16
```

### 完了後
```bash
/worktree-done <branch-name>
```
================================================================================
```

---

## 関連コマンド

| コマンド | 説明 |
|----------|------|
| `/worktree` | 新しい worktree を作成 |
| `/create-worktrees` | 複数 worktree を一括作成 |
| `/worktree-done` | worktree の完了とクリーンアップ |
| `/issue-implementation` | Issue 実装（複数 Issue 連続実装対応） |
| `/commit-and-pr` | コミットと PR 作成 |

---

## 完了条件

このワークフローは、以下の全ての条件を満たした時点で完了:

- ステップ 0: 引数が正しく解析されている
- ステップ 1: プロジェクト情報が取得できている
- ステップ 2: Todo Issue がフィルタリングされている
- ステップ 3: 依存関係が解析されている
- ステップ 4: Wave グルーピングが完了している
- ステップ 4.5: 連続開発グループが判定されている（NEW）
  - 各 Issue の開発タイプが判定されている
  - 直列依存の Issue がチェーン化されている
  - `/issue-implementation` に渡す引数が明示されている
- ステップ 5: 結果が表示されている
