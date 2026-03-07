---
name: sync-claude-config
description: .claude/ 配下の設定ファイル（スキル、エージェント、コマンド、ルール）を他プロジェクトに同期するスキル。PostToolUse hook により Write/Edit 時に自動実行。/sync-claude-config コマンドで手動実行も可能。
allowed-tools: Read, Bash
---

# Sync Claude Config

`.claude/` 配下の設定ファイルをプロジェクト間で同期する。

## 設定ファイル

`.claude/sync-config.yaml` で同期対象と同期先を定義:

- **targets**: 同期先プロジェクト（名前、GitHub URL、ローカルパス）
- **sync**: カテゴリ別の同期ルール
  - `"*"` で全アイテム同期、リスト形式で個別指定
  - `{category}_exclude` で glob パターン除外

## 使用方法

### 手動同期

```bash
# 差分確認
python3 .claude/skills/sync-claude-config/sync.py --dry-run

# 同期実行
python3 .claude/skills/sync-claude-config/sync.py

# ステータス確認
python3 .claude/skills/sync-claude-config/sync.py --status

# 同期対象一覧
python3 .claude/skills/sync-claude-config/sync.py --list
```

### 自動同期

`.claude/settings.json` の PostToolUse hook により、Write/Edit 実行後に自動で差分同期される。

## 実行手順（/sync-claude-config コマンド）

1. ステータス確認:
   ```bash
   python3 .claude/skills/sync-claude-config/sync.py --status
   ```

2. 差分がある場合、同期実行:
   ```bash
   python3 .claude/skills/sync-claude-config/sync.py
   ```

3. 結果をユーザーに報告
