# Plan Project 詳細ガイド

## 概要

`/plan-project` はリサーチベースのプロジェクト計画ワークフローです。5つの Phase を通じて、情報収集から GitHub Project 登録までを一貫して実行します。

## ワークフロー全体図

```
Phase 0: 初期化・方向確認
│  ├── 引数パース → タイプ判定
│  ├── セッションディレクトリ作成
│  ├── session-meta.json 書出し
│  └── [HF0] AskUserQuestion: 方向確認
│
Phase 1: リサーチ
│  ├── Task(project-researcher) → research-findings.json
│  └── [HF1] AskUserQuestion: リサーチ結果・ギャップ質問
│           └── user-answers.json 書出し
│
Phase 2: 計画策定
│  ├── Task(project-planner) → implementation-plan.json
│  └── [HF2] AskUserQuestion: 計画承認
│
Phase 3: タスク分解
│  ├── Task(project-decomposer) → task-breakdown.json
│  └── [HF3] AskUserQuestion: タスク確認
│
Phase 4: GitHub Project・Issue 登録
   ├── docs/project/project-{N}/project.md 作成
   ├── gh project create
   ├── gh issue create (各タスク)
   ├── gh project item-add (各Issue)
   ├── project.md に Issue リンク反映
   └── 完了レポート表示
```

## Phase 0: 初期化・方向確認

### 引数パースとタイプ判定

```python
# 判定ロジック（擬似コード）
if args.startswith("@src/"):
    project_type = "package"
elif args.startswith("@docs/plan/"):
    project_type = "from_plan_file"
    source_plan_file = args  # プランファイルパスを記録
elif "--type" in args:
    project_type = args["--type"]  # agent/skill/command/workflow/docs
elif args is None or args is str:
    project_type = "general"
```

**プランファイル対応**:
- 引数が `@docs/plan/*.md` の場合、そのファイルを Phase 4 で `original-plan.md` としてプロジェクトフォルダに移動
- プランファイルからプロジェクト名とタイプを推測（ファイル内容を読み込んで判定）

### セッションディレクトリ

```bash
mkdir -p .tmp/plan-project-{session_id}/
```

`session_id` は `YYYYMMDD-HHMMSS` 形式のタイムスタンプ。

### session-meta.json スキーマ

```json
{
  "session_id": "20260208-143000",
  "created_at": "2026-02-08T14:30:00+09:00",
  "project_type": "agent",
  "project_name": "ニュース分析エージェント",
  "description": "ユーザーの自由記述",
  "arguments": "--type agent \"ニュース分析エージェント\"",
  "source_plan_file": "@docs/plan/2026-02-15_example.md",
  "workflow_status": {
    "phase_0": "completed",
    "phase_1": "pending",
    "phase_2": "pending",
    "phase_3": "pending",
    "phase_4": "pending"
  }
}
```

**新規フィールド**:
- `source_plan_file` (string, optional): 引数で指定されたプランファイルパス。Phase 4 で移動対象となる。

### HF0: 方向確認

AskUserQuestion で以下を確認：

```yaml
questions:
  - question: "プロジェクトタイプは「{detected_type}」で正しいですか？"
    header: "タイプ確認"
    options:
      - label: "{detected_type}（検出結果）"
        description: "自動検出されたタイプで進める"
      - label: "別のタイプを指定"
        description: "手動でタイプを選択"
    multiSelect: false

  - question: "何を作りたいですか？具体的に教えてください。"
    header: "目的"
    options:
      - label: "新規作成"
        description: "ゼロから新しいものを作る"
      - label: "既存の改善"
        description: "既存の仕組みを改善・拡張する"
      - label: "置き換え"
        description: "既存の仕組みを新しいものに置き換える"
    multiSelect: false
```

## Phase 1: リサーチ

### エージェント起動

```
Task(
  subagent_type="project-researcher",
  prompt="""
  以下のセッションディレクトリからメタ情報を読み込み、コードベースを調査してください。

  セッションディレクトリ: {session_dir}

  調査完了後、{session_dir}/research-findings.json に結果を書き出してください。
  """
)
```

### research-findings.json スキーマ

```json
{
  "project_type": "string",
  "explored_paths": [
    {
      "path": "string（探索したディレクトリ）",
      "file_count": "number",
      "relevant_files": [
        {
          "path": "string（完全パス）",
          "relevance": "string（関連性の説明）",
          "key_patterns": ["string"]
        }
      ]
    }
  ],
  "existing_patterns": [
    {
      "pattern": "string（パターン名）",
      "description": "string（説明）",
      "example_files": ["string（ファイルパス）"],
      "applicable": "boolean"
    }
  ],
  "related_issues": [
    {
      "number": "number",
      "title": "string",
      "relevance": "string（直接関連/間接関連/参考）"
    }
  ],
  "information_gaps": [
    {
      "category": "scope|technology|constraint|priority|integration",
      "question": "string（具体的な質問文）",
      "context": "string（なぜ必要か）",
      "options": ["string（選択肢）"]
    }
  ],
  "recommendations": [
    {
      "type": "reuse|adapt|create|avoid",
      "description": "string",
      "source": "string（ファイルパス）"
    }
  ]
}
```

### HF1: リサーチ結果・ギャップ質問

リサーチ結果を提示した上で、information_gaps を AskUserQuestion で質問。

**表示フォーマット**:

```markdown
## リサーチ結果

### 発見したパターン
- {pattern}: {description}（参照: {example_files}）

### 関連する既存 Issue
- #{number}: {title}

### 推奨事項
- {description}（参照: {source}）

---

以下の情報が不足しています。回答をお願いします。
```

AskUserQuestion は最大4問まで。ギャップが5つ以上ある場合は優先度の高い4つを選択し、残りはデフォルト値で進行。

回答は `user-answers.json` に保存：

```json
{
  "answered_at": "2026-02-08T14:35:00+09:00",
  "answers": [
    {
      "gap_category": "scope",
      "question": "質問文",
      "answer": "ユーザーの回答",
      "selected_option": "選択された選択肢"
    }
  ],
  "unanswered_gaps": [
    {
      "category": "priority",
      "question": "質問文",
      "default_value": "デフォルト値"
    }
  ]
}
```

## Phase 2: 計画策定

### エージェント起動

```
Task(
  subagent_type="project-planner",
  prompt="""
  以下のセッションディレクトリから入力データを読み込み、実装計画を策定してください。

  セッションディレクトリ: {session_dir}

  読み込むファイル:
  - session-meta.json
  - research-findings.json
  - user-answers.json

  計画完了後、{session_dir}/implementation-plan.json に結果を書き出してください。
  """
)
```

### implementation-plan.json スキーマ

```json
{
  "project_name": "string",
  "project_type": "string",
  "architecture": {
    "overview": "string",
    "components": [
      {
        "name": "string",
        "type": "agent|skill|command|module|test|doc",
        "description": "string",
        "responsibilities": ["string"],
        "interfaces": ["string"]
      }
    ],
    "data_flow": "string"
  },
  "file_map": [
    {
      "operation": "create|modify|delete",
      "path": "string（完全パス）",
      "description": "string",
      "estimated_size": "string",
      "depends_on": ["string（ファイルパス）"],
      "wave": "number"
    }
  ],
  "risks": [
    {
      "category": "compatibility|complexity|dependency|testing|schedule",
      "description": "string",
      "level": "high|medium|low",
      "mitigation": "string"
    }
  ],
  "implementation_order": [
    {
      "wave": "number",
      "description": "string",
      "files": ["string"]
    }
  ],
  "estimated_total_effort": "string"
}
```

### HF2: 計画承認

完全な計画書を表示し、ユーザーの承認を取得。

**表示フォーマット**:

```markdown
## 実装計画

### アーキテクチャ概要
{overview}

### ファイルマップ

| 操作 | ファイル | 説明 | Wave |
|------|---------|------|------|
| {operation} | {path} | {description} | {wave} |

### リスク評価

| リスク | レベル | 対策 |
|--------|--------|------|
| {description} | {level} | {mitigation} |

### 実装順序
- Wave 1: {description}（{files}）
- Wave 2: {description}（{files}）

### 見積もり: {estimated_total_effort}
```

```yaml
questions:
  - question: "この計画で進めてよいですか？"
    header: "計画承認"
    options:
      - label: "承認"
        description: "この計画で Phase 3（タスク分解）に進む"
      - label: "修正して再計画"
        description: "フィードバックを反映して再計画"
      - label: "中止"
        description: "計画を中止する"
    multiSelect: false
```

「修正して再計画」の場合、ユーザーのフィードバックを受けて Phase 2 を再実行。

## Phase 3: タスク分解

### エージェント起動

```
Task(
  subagent_type="project-decomposer",
  prompt="""
  以下のセッションディレクトリから入力データを読み込み、タスクに分解してください。

  セッションディレクトリ: {session_dir}

  読み込むファイル:
  - session-meta.json
  - research-findings.json
  - user-answers.json
  - implementation-plan.json

  分解完了後、{session_dir}/task-breakdown.json に結果を書き出してください。
  """
)
```

### task-breakdown.json スキーマ

```json
{
  "project_name": "string",
  "total_tasks": "number",
  "total_waves": "number",
  "estimated_total_hours": "string",
  "tasks": [
    {
      "id": "string（task-{N}）",
      "title": "string（[Wave{N}] 日本語タイトル）",
      "wave": "number",
      "estimated_hours": "string",
      "depends_on": ["string（task-id）"],
      "blocks": ["string（task-id）"],
      "label": "string（enhancement|documentation|test|refactor）",
      "issue_body": "string（Issue本文、Markdown形式）",
      "files": [
        {
          "operation": "create|modify|delete",
          "path": "string"
        }
      ]
    }
  ],
  "waves": [
    {
      "wave": "number",
      "description": "string",
      "task_ids": ["string"],
      "parallelizable": "boolean"
    }
  ],
  "dependency_graph_mermaid": "string（Mermaid記法）",
  "circular_dependencies": [],
  "summary": {
    "wave_1_tasks": "number",
    "wave_2_tasks": "number",
    "critical_path": ["string（task-id）"]
  }
}
```

### HF3: タスク確認

タスクリストと Mermaid 依存関係図を表示し、確認を取得。

**表示フォーマット**:

```markdown
## タスク分解結果

**合計**: {total_tasks} タスク / {total_waves} Wave / 見積もり {estimated_total_hours}

### Wave 1（並行開発可能）
| # | タイトル | 見積もり | 依存 |
|---|---------|---------|------|
| task-1 | {title} | {hours} | - |

### Wave 2（Wave 1 完了後）
| # | タイトル | 見積もり | 依存 |
|---|---------|---------|------|
| task-4 | {title} | {hours} | task-1 |

### 依存関係図

{dependency_graph_mermaid}

### クリティカルパス
{critical_path の表示}
```

```yaml
questions:
  - question: "このタスク分解で GitHub Issue を作成しますか？"
    header: "タスク確認"
    options:
      - label: "作成する"
        description: "GitHub Project と Issue を作成して登録"
      - label: "修正して再分解"
        description: "フィードバックを反映して再分解"
      - label: "project.md のみ作成"
        description: "GitHub 登録は行わず計画書のみ作成"
    multiSelect: false
```

## Phase 4: GitHub Project・Issue 登録

plan-lead（メインエージェント）が直接実行。

### ステップ 1: project 番号の決定

```bash
ls -d docs/project/project-* | sort -t- -k2 -n | tail -1
# → project-34 → 次は project-35
```

### ステップ 2: GitHub Project 作成

```bash
gh project create --title "{プロジェクト名}" --owner @me --format json
```

### ステップ 2.5: プランファイルの移動

`session-meta.json` の `source_plan_file` が存在する場合、元のプランファイルをプロジェクトフォルダに移動：

```bash
# プロジェクトディレクトリ作成
mkdir -p docs/project/project-{N}/

# プランファイル移動
if [ -n "$SOURCE_PLAN_FILE" ]; then
  # @docs/plan/2026-02-15_example.md → docs/project/project-{N}/original-plan.md
  SOURCE_PATH="${SOURCE_PLAN_FILE#@}"  # @ プレフィックスを削除
  mv "$SOURCE_PATH" "docs/project/project-{N}/original-plan.md"

  echo "プランファイルを移動しました: $SOURCE_PATH → docs/project/project-{N}/original-plan.md"
fi
```

**注意**:
- プランファイルは `original-plan.md` に統一
- 元のファイルは移動（コピーではなく `mv`）されるため、元の場所からは削除される

### ステップ 3: project.md 作成

テンプレート（`templates/project-template.md`）を使用して `docs/project/project-{N}/project.md` を作成。

この時点では Issue リンクは空欄にしておく（ステップ 5 で反映）。

### ステップ 4: Issue 作成と Project 登録

task-breakdown.json の各タスクについて：

```bash
# Issue 作成（gh issue create は --json 非対応のため標準出力からURLを取得）
ISSUE_URL=$(gh issue create \
  --title "{title}" \
  --body "$(cat <<'EOF'
{issue_body}

## 関連
- 計画書: docs/project/project-{N}/project.md
- GitHub Project: [#{project_number}]({project_url})
EOF
)" \
  --label "{label}")

# Project に追加
gh project item-add {project_number} --owner @me --url "$ISSUE_URL"
```

### ステップ 5: project.md に Issue リンクを反映

作成した Issue の番号と URL を project.md のタスク一覧に反映。

### ステップ 6: workflow-status.json 最終更新

```json
{
  "completed_at": "2026-02-08T15:00:00+09:00",
  "workflow_status": {
    "phase_0": "completed",
    "phase_1": "completed",
    "phase_2": "completed",
    "phase_3": "completed",
    "phase_4": "completed"
  },
  "outputs": {
    "project_md": "docs/project/project-35/project.md",
    "original_plan_file": "docs/project/project-35/original-plan.md",
    "github_project_number": 35,
    "github_project_url": "https://github.com/users/YH-05/projects/35",
    "issues_created": [
      {"number": 500, "title": "[Wave1] タスク1", "url": "..."}
    ]
  }
}
```

**新規フィールド**:
- `outputs.original_plan_file` (string, optional): 移動したプランファイルのパス。`source_plan_file` が指定されていた場合のみ記録。

### ステップ 7: 完了レポート

```markdown
================================================================================
                    プロジェクト計画完了
================================================================================

## プロジェクト情報
- **名前**: {project_name}
- **タイプ**: {project_type}
- **計画書**: docs/project/project-{N}/project.md
- **元プラン**: docs/project/project-{N}/original-plan.md（移動済み）

## GitHub Project
- **番号**: #{project_number}
- **URL**: {project_url}

## 作成した Issue

| Wave | # | タイトル | ラベル |
|------|---|---------|--------|
| 1 | #{number} | {title} | {label} |
| 2 | #{number} | {title} | {label} |

## 依存関係図

{dependency_graph_mermaid}

## リサーチで発見したパターン
- {pattern}: {description}

## 見積もり
- **合計**: {estimated_total_hours}
- **Wave数**: {total_waves}

## 次のステップ
1. 計画書の内容を確認: `docs/project/project-{N}/project.md`
2. 並列開発計画を確認: `/plan-worktrees #{project_number}`
3. タスクを実装: `/issue-implement #{issue_number}`

================================================================================
```

## エラーハンドリング

### GitHub 認証エラー

```
エラー: GitHub 認証が必要です

対処法:
  gh auth login
  gh auth refresh -s project
```

### Phase の中断・再開

workflow-status.json でどの Phase まで完了しているかを追跡。中断後に再開する場合、完了済み Phase はスキップ可能。

```bash
# 中断されたセッションの確認
ls .tmp/plan-project-*/workflow-status.json
```

### エージェント失敗時

各 Phase のエージェントが失敗した場合：

1. エラー内容をユーザーに表示
2. 再実行 or 手動修正の選択肢を提示
3. 手動修正の場合、JSON ファイルを直接編集可能

## タイプ別の挙動差分

### package タイプ

- Phase 1 で `src/` 配下を重点的に探索
- Phase 2 で Python モジュール構造を設計
- 既存の `new-project` パッケージ開発モードのノウハウを活用
- テストファイル（`tests/`）も file_map に含める

### agent タイプ

- Phase 1 で `.claude/agents/` の全エージェントをスキャン
- Phase 2 で frontmatter 構造、スキル参照、入出力を設計
- CLAUDE.md のエージェント一覧テーブル更新を file_map に含める

### skill タイプ

- Phase 1 で `.claude/skills/` の全スキルをスキャン
- Phase 2 で SKILL.md/guide.md/templates/ の構造を設計
- CLAUDE.md のスキル一覧テーブル更新を file_map に含める

### command タイプ

- Phase 1 で `.claude/commands/` の全コマンドをスキャン
- Phase 2 で frontmatter（description, argument-hint）を設計
- CLAUDE.md のコマンド一覧テーブル更新を file_map に含める

### workflow タイプ

- Phase 1 で関連するスキル・エージェント・コマンドを横断的に探索
- Phase 2 で Phase 構造、データフロー、HF ゲートを設計
- 複数のファイルタイプ（skill + agent + command）を統合的に計画

### docs タイプ

- Phase 1 で `docs/` の既存ドキュメント構造を探索
- Phase 2 でセクション構造、クロスリファレンスを設計
- ラベルは `documentation` を使用

### general タイプ

- Phase 0 の HF0 で詳細なヒアリングを実施
- Phase 1 で全ディレクトリを広く探索
- Phase 2 で混合タイプのファイルマップを生成

## サブエージェントデータ渡しルール

**重要**: `.claude/rules/subagent-data-passing.md` に準拠。

- 全データは JSON 形式で一時ファイル経由で受け渡し
- ファイルパスは完全パスで記載（省略禁止）
- 自然言語での説明的な形式は禁止
- セッションディレクトリパスをプロンプトに含めて渡す

## 関連ファイル

| ファイル | 説明 |
|---------|------|
| `.claude/skills/plan-project/SKILL.md` | スキル定義 |
| `.claude/skills/plan-project/templates/project-template.md` | project.md テンプレート |
| `.claude/skills/plan-project/templates/issue-template.md` | Issue 本文テンプレート |
| `.claude/agents/project-researcher.md` | リサーチエージェント |
| `.claude/agents/project-planner.md` | 計画エージェント |
| `.claude/agents/project-decomposer.md` | タスク分解エージェント |
| `.claude/commands/plan-project.md` | コマンド定義 |
| `.claude/rules/subagent-data-passing.md` | データ渡しルール |
| `.claude/skills/task-decomposition/SKILL.md` | タスク分解スキル（参照） |
