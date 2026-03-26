---
allowed-tools: mcp__playwright__browser_navigate, mcp__playwright__browser_snapshot, mcp__playwright__browser_take_screenshot, mcp__playwright__browser_click, mcp__playwright__browser_evaluate, mcp__playwright__browser_network_requests, mcp__playwright__browser_handle_dialog, mcp__playwright__browser_close, Bash, Read, Write, Glob, Grep
---

# /site-investigator

対象 URL のサイト構造を Playwright MCP で調査し、スクレイピングに必要な情報をレポートする。

## 引数

$ARGUMENTS — 調査対象の URL（例: `https://example.com/blog`）

## 実行手順

1. `.claude/skills/site-investigator/SKILL.md` を読み込み、5 Phase の調査プロトコルに従って実行する
2. 調査結果を `.tmp/site-investigation-{domain}-{timestamp}.json` に保存する
3. レポート生成スクリプトを実行する:
   ```bash
   uv run python .claude/skills/site-investigator/scripts/generate_site_report.py \
     --input .tmp/site-investigation-{domain}-{timestamp}.json \
     --output-dir .tmp/site-reports/{domain}/
   ```
4. 生成されたレポート（`.tmp/site-reports/{domain}/report.md`）を読み込んで結果を報告する

## 注意事項

- robots.txt の Disallow ルールを尊重すること
- 調査全体で 10-20 リクエスト程度に抑えること
- 個人情報やログイン情報をレポートに含めないこと
