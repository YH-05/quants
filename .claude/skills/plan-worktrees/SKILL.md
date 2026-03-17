---
name: plan-worktrees
description: GitHub ProjectのTodo Issueを並列開発用にグルーピング表示。/plan-worktrees コマンドで使用。依存関係を考慮した並列開発計画と、worktree内での連続開発グルーピングを可視化する。
allowed-tools: Read, Bash
---

# Plan Worktrees - Worktree 並列開発計画

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

| 条件 | 説明 | 判定方法 |
|------|------|----------|
| 同一開発タイプ | python / agent / command / skill | ラベルまたはキーワード |
| 順序的依存 | A → B → C のような直列依存 | 依存グラフの解析 |
| 同一対象パッケージ | 同じパッケージ/ディレクトリ | パス解析 |
| コンフリクト無し | 同一ファイルへの競合変更なし | 変更対象推定 |

### 4.5.2 開発タイプの判定

Issue のラベルまたはキーワードから判定：

```python
def detect_dev_type(issue) -> str:
    """開発タイプを判定"""
    labels = [l.lower() for l in issue.get("labels", [])]
    body = issue.get("body", "").lower()

    # ラベル判定（優先）
    if any(l in ["agent", "エージェント"] for l in labels):
        return "agent"
    if any(l in ["command", "コマンド"] for l in labels):
        return "command"
    if any(l in ["skill", "スキル"] for l in labels):
        return "skill"

    # キーワード判定
    if ".claude/agents/" in body:
        return "agent"
    if ".claude/commands/" in body:
        return "command"
    if ".claude/skills/" in body:
        return "skill"

    return "python"
```

### 4.5.3 対象パッケージの特定

Issue 本文から対象パッケージを推定：

```python
def detect_target_package(issue) -> str | None:
    """対象パッケージを推定"""
    body = issue.get("body", "")

    # パッケージパスのパターン
    patterns = [
        r"src/(\w+)/",           # src/finance/, src/market_analysis/
        r"packages/(\w+)/",       # packages/xxx/
        r"\b(finance|market_analysis|rss|factor|strategy|bloomberg)\b"
    ]

    for pattern in patterns:
        match = re.search(pattern, body)
        if match:
            return match.group(1)

    return None
```

### 4.5.4 連続開発チェーンの構築

依存関係が直列の Issue をチェーン化：

```python
def build_sequential_chains(issues, dependencies) -> list[list[int]]:
    """連続開発可能なチェーンを構築"""
    chains = []
    used = set()

    for issue in issues:
        if issue in used:
            continue

        chain = [issue]
        used.add(issue)

        # 同じタイプ・パッケージで、この Issue に依存する Issue を探す
        current = issue
        while True:
            next_issue = find_next_in_chain(current, issues, dependencies, used)
            if next_issue is None:
                break
            chain.append(next_issue)
            used.add(next_issue)
            current = next_issue

        chains.append(chain)

    return chains


def find_next_in_chain(current, issues, dependencies, used):
    """チェーンの次の Issue を探す"""
    for issue in issues:
        if issue in used:
            continue
        deps = dependencies.get(issue, [])
        if deps == [current]:  # 単一依存のみ
            if is_compatible(current, issue):  # 同じタイプ・パッケージ
                return issue
    return None
```

### 4.5.5 グルーピング出力

```markdown
## 🔗 連続開発グループ（同一 worktree で連続実装可能）

### グループ 1: finance パッケージ - Python 開発
| # | タイトル | 依存 |
|---|----------|------|
| #10 | utils モジュール追加 | - |
| #11 | helpers 拡張 | #10 |
| #12 | core 連携 | #11 |

**連続実装コマンド**:
```bash
/issue-implementation 10 11 12
```

**処理フロー**:
```
#10 実装 → コミット → /clear
    ↓
#11 実装 → コミット → /clear
    ↓
#12 実装 → コミット → PR作成
```

---

### グループ 2: agent 開発
| # | タイトル | 依存 |
|---|----------|------|
| #20 | 分析エージェント追加 | - |
| #21 | 連携機能追加 | #20 |

**連続実装コマンド**:
```bash
/issue-implementation 20 21
```
```

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

### 5.2 Wave ごとの Issue 一覧

```markdown
## 🌊 Wave 1（即座に並列開発可能）

以下の Issue は依存関係がなく、同時に worktree を作成して並列開発できます。

| # | タイトル | タイプ | パッケージ | worktree コマンド |
|---|----------|--------|------------|-------------------|
| #10 | utils モジュール追加 | python | finance | `/worktree feature/issue-10` |
| #11 | 分析エージェント追加 | agent | - | `/worktree feature/issue-11` |

**推奨 worktree 作成**:
```bash
# 複数の worktree を作成（別々のターミナルで実行）
/worktree feature/issue-10
/worktree feature/issue-11
```

---

## 🌊 Wave 2（Wave 1 完了後に開発可能）

以下の Issue は Wave 1 の完了を待つ必要があります。

| # | タイトル | 依存 | タイプ | パッケージ |
|---|----------|------|--------|------------|
| #12 | helpers 拡張 | #10 | python | finance |
| #13 | 連携機能追加 | #11 | agent | - |

**依存関係**:
- #12 depends on #10（Wave 1）
- #13 depends on #11（Wave 1）

---

## ⚠️ 未解決の依存関係

以下の Issue は解決できない依存関係があります:

| # | タイトル | 問題 |
|---|----------|------|
| #20 | 機能X | 依存先 #99 が存在しない |
| #21 | 機能Y | 循環依存: #21 → #22 → #21 |
```

### 5.3 連続開発グループの表示（NEW）

Wave を跨いで連続開発可能なグループを表示します。

```markdown
## 🔗 連続開発グループ

同一 worktree 内で `/issue-implementation` の複数 Issue 連続実装が可能なグループです。

### グループ 1: finance パッケージ - Python 開発
**Wave 1 → Wave 2 を連続開発**

| # | タイトル | Wave | 依存 |
|---|----------|------|------|
| #10 | utils モジュール追加 | 1 | - |
| #12 | helpers 拡張 | 2 | #10 |

**連続実装コマンド**:
```bash
# worktree を作成
/worktree feature/finance-utils

# 連続実装（推奨）
/issue-implementation 10 12
```

**処理フロー**:
```
#10 実装 → コミット → /clear → #12 実装 → コミット → PR作成
```

---

### グループ 2: agent 開発
**Wave 1 → Wave 2 を連続開発**

| # | タイトル | Wave | 依存 |
|---|----------|------|------|
| #11 | 分析エージェント追加 | 1 | - |
| #13 | 連携機能追加 | 2 | #11 |

**連続実装コマンド**:
```bash
# worktree を作成
/worktree feature/analysis-agent

# 連続実装（推奨）
/issue-implementation 11 13
```

---

### 単独開発 Issue

以下の Issue は連続開発グループに含まれず、単独で実装します。

| # | タイトル | 理由 |
|---|----------|------|
| #15 | ドキュメント更新 | 複数依存あり（#10, #11）、タイプ混在 |
| #16 | CI設定追加 | 依存なしの独立タスク |
```

### 5.4 推奨開発フロー

```markdown
## 📝 推奨開発フロー

### Phase 1: 連続開発グループを活用

連続開発グループがある場合、同一 worktree で複数 Issue を連続実装できます。

```bash
# 開発者A: グループ1（finance パッケージ）
/worktree feature/finance-utils
/issue-implementation 10 12   # 連続実装

# 開発者B: グループ2（agent 開発）
/worktree feature/analysis-agent
/issue-implementation 11 13   # 連続実装
```

**メリット**:
- Wave 1 → Wave 2 を待たずに連続開発
- コンテキストスイッチを最小化
- 関連 Issue が 1 つの PR にまとまる

### Phase 2: 残りの Issue を並列開発

連続開発グループに含まれない Issue は従来通り並列開発。

```bash
# 単独 Issue
/worktree docs/issue-15
/issue-implementation 15

/worktree feature/issue-16
/issue-implementation 16
```

### 単独開発の場合

一人で開発する場合の推奨フロー:

1. **連続開発グループを優先**: 1 worktree で複数 Issue を実装
2. **レビュー待ち時**: 別 worktree で次のグループに着手
3. **独立 Issue は後回し**: グループ化できない Issue は最後に
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
| 開発タイプ不明 | ラベル・キーワード両方で判定不可の場合は `python` とみなす |
| パッケージ特定不可 | 連続開発グループから除外、単独開発として表示 |

---

## 出力例

```
================================================================================
📋 Worktree 並列開発計画
================================================================================

Project: #1
リポジトリ: YH-05/quants
Todo Issue: 6 件
Wave 数: 3
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

## 🌊 Wave 3（Wave 2 完了後）- 1 件

| # | タイトル | 依存 | タイプ | パッケージ |
|---|----------|------|--------|------------|
| #14 | core 連携 | #12 | python | finance |

================================================================================

## 🔗 連続開発グループ（推奨）

### グループ 1: finance パッケージ - Python 開発
| # | タイトル | Wave | 依存 |
|---|----------|------|------|
| #10 | utils モジュール追加 | 1 | - |
| #12 | helpers 拡張 | 2 | #10 |
| #14 | core 連携 | 3 | #12 |

```bash
/worktree feature/finance-utils
/issue-implementation 10 12 14
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
| # | タイトル | Wave | 理由 |
|---|----------|------|------|
| #16 | CI設定追加 | 1 | 依存なしの独立タスク |

```bash
/worktree feature/ci-setup
/issue-implementation 16
```

================================================================================

## 📝 推奨開発フロー

### 連続開発グループを活用（最効率）

```bash
# ターミナル 1: グループ 1
/worktree feature/finance-utils
/issue-implementation 10 12 14   # 3 Issue を連続実装 → 1 PR

# ターミナル 2: グループ 2
/worktree feature/analysis-agent
/issue-implementation 11 13      # 2 Issue を連続実装 → 1 PR

# ターミナル 3: 単独 Issue
/worktree feature/ci-setup
/issue-implementation 16
```

### 完了後のクリーンアップ

```bash
/worktree-done feature/finance-utils
/worktree-done feature/analysis-agent
/worktree-done feature/ci-setup
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
  - 各 Issue の開発タイプ（python/agent/command/skill）が判定されている
  - 対象パッケージが特定されている（可能な場合）
  - 直列依存の Issue がチェーン化されている
  - `/issue-implementation` に渡す引数が明示されている
- ステップ 5: 結果が表示されている
  - Wave ごとの Issue 一覧に開発タイプ・パッケージが含まれている
  - 連続開発グループと実行コマンドが表示されている
