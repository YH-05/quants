---
description: NAS ↔ ローカル間でファイルを同期（.env, .mcp.json, .claude/settings.json, data/config/）
---

# NAS同期

NAS（`/Volumes/personal_folder/Projects/quants/`）と
ローカルの間でファイルを同期します。

**必須**: Skillツールを使用して `sync-nas` スキルを実行すること。

```
Skill(skill: "sync-nas")
```

> **スキル参照**: `.claude/skills/sync-nas/SKILL.md`

## pull（手動・他PCからの取り込み）

NAS → ローカルへ同期（他PCで更新した設定を取り込む場合）:
```bash
bash scripts/sync_nas.sh --pull
```

## push（SessionEnd hookで自動実行）

ローカル → NAS へ同期（セッション終了時に自動実行）:
```bash
bash scripts/sync_nas.sh --push
```
