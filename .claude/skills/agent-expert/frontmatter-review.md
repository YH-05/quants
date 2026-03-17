# エージェントフロントマターレビューガイド

このドキュメントは、エージェントファイル（`.claude/agents/*.md`）のフロントマターを検証するためのガイドです。

## 公式ドキュメント

**参照**: https://docs.anthropic.com/en/docs/claude-code/sub-agents#supported-frontmatter-fields

## 公式フィールド一覧

Claude Code が認識・処理する公式フィールドは以下のみです：

```yaml
---
name: string              # 必須: エージェント名（kebab-case）
description: string       # 必須: Task tool に表示される説明
tools: string             # オプション: 許可するツールリスト（カンマ区切り）
disallowedTools: string   # オプション: 禁止するツールリスト
model: string             # オプション: inherit | sonnet | haiku | opus
permissionMode: string    # オプション: default | acceptEdits | dontAsk | bypassPermissions | plan
skills: string[]          # オプション: プリロードするスキル配列
hooks: object             # オプション: ライフサイクルフック
---
```

### プロジェクト独自拡張（公式ではないが使用可）

```yaml
color: string             # プロジェクト独自: UI表示用の識別色
category: string          # プロジェクト独自: エージェントの分類
```

## 使用禁止フィールド

以下のフィールドは**使用禁止**です。Claude Code では処理されず、フロントマターを肥大化させるだけです：

| フィールド | 理由 |
|-----------|------|
| `input` | ❌ 非公式。本文に記述すること |
| `output` | ❌ 非公式。本文に記述すること |
| `depends_on` | ❌ 非公式。本文に記述すること |
| `phase` | ❌ 非公式。本文に記述すること |
| `priority` | ❌ 非公式。本文に記述すること |
| `archived` | ❌ 非公式。本文冒頭に注記すること |
| `allowed-tools` | ❌ 非公式。`tools` を使用すること |

---

## フィールド別検証ルール

### 1. `name` フィールド（必須）

**検証項目**:

| チェック項目 | ルール | 例 |
|-------------|--------|-----|
| 必須 | 空でないこと | ✅ `debugger` |
| 形式 | kebab-case | ✅ `quality-checker` ❌ `qualityChecker` |
| ファイル名一致 | `{name}.md` と一致 | `debugger.md` → `name: debugger` |
| 一意性 | 他のエージェントと重複しない | - |

### 2. `description` フィールド（必須）

**検証項目**:

| チェック項目 | ルール | 推奨 |
|-------------|--------|------|
| 必須 | 空でないこと | - |
| 長さ | 1-2文（50-200文字推奨） | 簡潔かつ明確 |
| トリガーキーワード | 使用タイミングを示すキーワードを含む | `〜を実行する` `〜の場合に使用` |
| 具体性 | 何をするエージェントか明確 | ❌ `コードをチェックする` ✅ `コード品質の検証・自動修正を行う` |

**良い例**:
```yaml
description: コード品質の検証・自動修正を行う統合サブエージェント。モードに応じて検証のみ、自動修正、クイックチェックを実行。
```

**悪い例**:
```yaml
description: コードをチェック  # 曖昧すぎる
```

### 3. `tools` フィールド（オプション）

**検証項目**:

| チェック項目 | ルール | 例 |
|-------------|--------|-----|
| 形式 | カンマ区切り文字列 | `tools: Read, Write, Glob, Grep` |
| 有効なツール名 | Claude Code で利用可能なツール | - |
| 最小権限の原則 | 必要なツールのみ指定 | - |

**有効なツール一覧**:

| ツール名 | 説明 |
|----------|------|
| `Read` | ファイル読み込み |
| `Write` | ファイル書き込み |
| `Edit` | ファイル編集 |
| `Glob` | ファイルパターン検索 |
| `Grep` | 内容検索 |
| `Bash` | コマンド実行 |
| `Task` | サブエージェント起動 |
| `WebSearch` | Web検索 |
| `WebFetch` | Webページ取得 |
| `AskUserQuestion` | ユーザーへの質問 |
| `ToolSearch` | ツール検索（旧MCPSearch） |
| `NotebookEdit` | Jupyter Notebook編集 |
| `Skill` | スキル実行 |

**注意事項**:
- `tools` を指定しない場合、エージェントは全てのツールにアクセス可能
- 制限が必要な場合のみ明示的に指定
- MCP ツールも指定可能（例: `mcp__rss__fetch_feed`）

### 4. `disallowedTools` フィールド（オプション）

特定のツールを禁止する場合に使用します。

```yaml
disallowedTools: Bash, Write  # Bash と Write を禁止
```

### 5. `model` フィールド（オプション）

**検証項目**:

| 有効な値 | 説明 | 用途 |
|---------|------|------|
| `inherit` | 親から継承（デフォルト） | 一般的なタスク |
| `haiku` | 高速・低コスト | 単純なタスク |
| `sonnet` | バランス型 | 標準的なタスク |
| `opus` | 高性能 | 複雑なタスク |

**デフォルト**: `inherit`（指定しない場合）

### 6. `permissionMode` フィールド（オプション）

**有効な値**:

| 値 | 説明 |
|----|------|
| `default` | 通常の権限確認 |
| `acceptEdits` | 編集を自動承認 |
| `dontAsk` | 確認なしで実行 |
| `bypassPermissions` | 全権限をバイパス |
| `plan` | プランモードで実行 |

### 7. `skills` フィールド（オプション）

**検証項目**:

| チェック項目 | ルール | 例 |
|-------------|--------|-----|
| 形式 | YAML配列 | `skills: [skill-name-1, skill-name-2]` |
| 存在確認 | `.claude/skills/{skill-name}/SKILL.md` が存在すること | - |
| 命名規則 | kebab-case | `agent-expert`, `deep-research` |

**検証方法**:

```bash
# skills フィールドの参照先が存在するか確認
for skill in $(grep -A10 '^skills:' "$file" | grep '  - ' | sed 's/  - //'); do
    if [ ! -f ".claude/skills/$skill/SKILL.md" ]; then
        echo "ERROR: skill '$skill' が存在しません"
    fi
done
```

### 8. `hooks` フィールド（オプション）

エージェントのライフサイクルにフックを設定できます。

```yaml
hooks:
  PreToolUse:
    - command: echo "Tool about to be used"
  PostToolUse:
    - command: echo "Tool was used"
  Stop:
    - command: echo "Agent stopping"
```

### 9. `color` フィールド（プロジェクト独自・推奨）

**注意**: これは公式フィールドではありませんが、プロジェクトでの視覚的な識別に有用です。

**検証項目**:

| チェック項目 | ルール | 例 |
|-------------|--------|-----|
| 推奨 | 設定することを推奨 | ✅ `green` |
| 有効な値 | 定義済みの色名 | `green`, `blue`, `purple`, `orange`, `cyan`, `yellow`, `red`, `pink`, `magenta`, `indigo`, `gray` |

**推奨される色の使い分け**:
- `green`: 汎用・ユーティリティ系
- `blue`: 分析・リサーチ系
- `purple`: 作成・生成系
- `orange`: 検証・批評系
- `cyan`: データ処理系
- `yellow`: 管理・オーケストレーション系
- `red`: 重要・警告系
- `pink`: 補助・サポート系

### 10. `category` フィールド（プロジェクト独自・オプション）

**注意**: これは公式フィールドではありません。

**検証項目**:

| チェック項目 | ルール | 例 |
|-------------|--------|-----|
| 形式 | kebab-case | `specialized-domains` |
| 既存カテゴリ | 可能な限り既存のものを使用 | - |

**既存カテゴリ一覧**:
- `specialized-domains`: 汎用的な専門タスク

---

## 検証チェックリスト

### 必須項目

- [ ] `name` が設定されている
- [ ] `name` がkebab-caseである
- [ ] `name` がファイル名と一致している
- [ ] `description` が設定されている
- [ ] `description` が具体的で明確である

### 推奨項目

- [ ] `color` が設定されている（プロジェクト独自）
- [ ] `color` が有効な色名である

### オプション項目（設定されている場合）

- [ ] `tools` のツール名が全て有効である
- [ ] `tools` が最小権限の原則に従っている
- [ ] `skills` の参照先スキルが全て存在する
- [ ] `model` が有効な値である（inherit/sonnet/haiku/opus）
- [ ] `permissionMode` が有効な値である

### 禁止項目の確認

- [ ] `input` が使用されていない
- [ ] `output` が使用されていない
- [ ] `depends_on` が使用されていない
- [ ] `phase` が使用されていない
- [ ] `priority` が使用されていない
- [ ] `archived` が使用されていない
- [ ] `allowed-tools` が使用されていない（`tools` を使用）

---

## 自動検証スクリプト例

```bash
#!/bin/bash
# エージェントフロントマター検証スクリプト

agent_file="$1"

if [ ! -f "$agent_file" ]; then
    echo "ERROR: ファイルが存在しません: $agent_file"
    exit 1
fi

errors=0
warnings=0

# name チェック
name=$(grep '^name:' "$agent_file" | sed 's/name: //')
filename=$(basename "$agent_file" .md)

if [ -z "$name" ]; then
    echo "ERROR: name が設定されていません"
    ((errors++))
elif [ "$name" != "$filename" ]; then
    echo "ERROR: name ($name) とファイル名 ($filename) が不一致"
    ((errors++))
fi

# description チェック
description=$(grep '^description:' "$agent_file" | sed 's/description: //')
if [ -z "$description" ]; then
    echo "ERROR: description が設定されていません"
    ((errors++))
elif [ ${#description} -lt 20 ]; then
    echo "WARN: description が短すぎます (${#description}文字)"
    ((warnings++))
fi

# 禁止フィールドのチェック
for field in "input:" "output:" "depends_on:" "phase:" "priority:" "archived:" "allowed-tools:"; do
    if grep -q "^$field" "$agent_file"; then
        echo "ERROR: 禁止フィールド '$field' が使用されています"
        ((errors++))
    fi
done

# skills チェック
if grep -q '^skills:' "$agent_file"; then
    while IFS= read -r skill; do
        skill=$(echo "$skill" | tr -d ' "[],-')
        if [ -n "$skill" ] && [ ! -d ".claude/skills/$skill" ]; then
            echo "ERROR: スキル '$skill' が存在しません"
            ((errors++))
        fi
    done < <(grep -A20 '^skills:' "$agent_file" | grep -E '^\s+-\s+' | sed 's/.*- //')
fi

# 結果サマリー
echo "---"
echo "検証結果: エラー=$errors, 警告=$warnings"
if [ $errors -gt 0 ]; then
    exit 1
fi
```

---

## 正しいフロントマターの例

### 最小構成

```yaml
---
name: code-reviewer
description: コード品質と最適化のレビューを行うサブエージェント
---
```

### 標準構成（推奨）

```yaml
---
name: code-reviewer
description: コード品質と最適化のレビューを行うサブエージェント。新機能開発後やPRレビュー時に使用。
model: inherit
color: blue
skills:
  - coding-standards
---
```

### フル構成

```yaml
---
name: code-reviewer
description: コード品質と最適化のレビューを行うサブエージェント
model: sonnet
color: blue
category: specialized-domains
skills:
  - coding-standards
  - error-handling
tools: Read, Grep, Glob, Bash
permissionMode: default
---
```

---

## 関連ドキュメント

- `guide.md`: エージェント設計の詳細ガイド
- `template.md`: エージェントテンプレート
- `SKILL.md`: agent-expert スキル定義
- **公式ドキュメント**: https://docs.anthropic.com/en/docs/claude-code/sub-agents
