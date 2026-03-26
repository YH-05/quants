---
description: NAS → ローカルへ設定ファイルを同期（.env, .mcp.json, .claude/settings.json, data/config/）
---

# 設定ファイル同期（Pull）

NAS（`/Volumes/personal_folder/Projects/quants/`）から
ローカルへ設定ファイルを同期します。他PCで更新された設定を取り込むときに使用。

**必須**: Skillツールを使用して `config-sync` スキルを実行すること。

```
Skill(skill: "config-sync")
```

> **スキル参照**: `.claude/skills/config-sync/SKILL.md`

## 逆方向（push）について

SessionEnd時に自動でNASへpushされます。
手動でpushしたい場合は以下を実行:
```bash
bash scripts/sync_nas.sh --push
```
