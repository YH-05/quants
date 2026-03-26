# 議論メモ: site-investigator スキル移植

**日付**: 2026-03-24
**議論ID**: disc-2026-03-24-site-investigator-port

## 背景・コンテキスト

note-finance プロジェクトで運用していた site-investigator スキル（Playwright MCP ベースのサイト構造調査）を quants プロジェクトでも使えるようにしたい。

## 実施内容

note-finance から以下の4ファイルを quants に移植:

| ファイル | 説明 |
|---------|------|
| `.claude/skills/site-investigator/SKILL.md` | 5 Phase 調査プロトコル本体 |
| `.claude/skills/site-investigator/references/investigation-checklist.md` | Phase 別チェックリスト |
| `.claude/skills/site-investigator/scripts/generate_site_report.py` | JSON + Markdown レポート生成 |
| `.claude/commands/site-investigator.md` | `/site-investigator` コマンド定義 |

ロギングのインポートパスは `finance.utils.logging_config` → フォールバック `logging` のパターンを維持。

## 決定事項

| ID | 内容 | コンテキスト |
|----|------|------------|
| dec-2026-03-24-001 | site-investigator を quants に移植し `/site-investigator` コマンドとして利用可能にする | スクレイピング前調査の自動化ニーズ |

## アクションアイテム

なし（移植完了済み）

## 使い方

```
/site-investigator https://example.com/blog
```
