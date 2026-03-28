---
name: sync-nas
description: NAS（/Volumes/personal_folder）とローカルの間でファイルを同期するスキル。
  .env, .mcp.json, .claude/settings.json, data/config/ を対象。
  /sync-nas コマンドで呼び出す。
allowed-tools: Bash
---

# NAS同期スキル

NASとローカルの間でファイルを同期します。

## 対象ファイル

| ファイル/ディレクトリ | 説明 |
|--------------------|------|
| `.env` | 環境変数（APIキー等） |
| `.mcp.json` | MCP設定 |
| `.claude/settings.json` | Claude Code プロジェクト設定 |
| `data/config/` | 全設定ファイル |

## 実行手順

1. NASのマウント確認（`/Volumes/personal_folder`）
2. 最終PUSH日時を表示
3. NAS → ローカルへrsync（差分のみ転送）
4. 同期結果を報告

## 実装

```bash
# NAS pull を実行
bash scripts/sync_nas.sh --pull
```

実行後、変更があったファイルを確認してユーザーに報告すること。
NASがマウントされていない場合はその旨を伝え、スキップする。

## 注意事項

- `.claude/settings.local.json` は**同期しない**（マシン固有の設定のため）
- SessionEnd hookでローカル→NASへの自動pushが実行される
- 手動でpullしたい場合は `bash scripts/sync_nas.sh --pull` を実行
- NAS保存先: `/Volumes/personal_folder/Projects/quants/`
