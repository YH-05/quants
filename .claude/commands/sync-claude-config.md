---
description: .claude/ の設定ファイルを他プロジェクトに同期
---

# Claude Config 同期

`.claude/` 配下の設定ファイルを他プロジェクトに同期します。

**必須**: 以下の手順を実行すること。

## 手順

### ステップ 1: ステータス確認

```bash
python3 .claude/skills/sync-claude-config/sync.py --status
```

### ステップ 2: 差分がある場合、同期を実行

```bash
python3 .claude/skills/sync-claude-config/sync.py
```

### ステップ 3: 結果報告

同期結果をユーザーに報告する。差分がなかった場合はその旨を伝える。

> **スキル参照**: `.claude/skills/sync-claude-config/SKILL.md`
>
> **設定ファイル**: `.claude/sync-config.yaml`
