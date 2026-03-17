# 週次レポート Issue テンプレート

GitHub Project #15 に週次レポートを投稿するための Issue テンプレート。

## Issue タイトル形式

```
[週次レポート] {YYYY-MM-DD} マーケットレポート
```

### タイトル例

- `[週次レポート] 2026-01-22 マーケットレポート`
- `[週次レポート] 2026-01-15 マーケットレポート`

## Issue 本文テンプレート

```markdown
## 週次マーケットレポート {{report_date}}

**対象期間**: {{start_date}} 〜 {{end_date}}

### 今週のハイライト

{{highlights}}

### 主要指数サマリー

| 指数 | 週間リターン |
|------|-------------|
| S&P 500 | {{spx_return}} |
| 等ウェイト (RSP) | {{rsp_return}} |
| グロース (VUG) | {{vug_return}} |
| バリュー (VTV) | {{vtv_return}} |

### MAG7 サマリー

{{mag7_summary}}

### セクター概況

**上位セクター**: {{top_sectors}}
**下位セクター**: {{bottom_sectors}}

### 詳細レポート

📄 [Markdownレポート]({{report_path}})

---

**生成日時**: {{generated_at}}
**自動生成**: このIssueは `/generate-market-report --weekly-comment` コマンドによって作成されました。
```

## プレースホルダー一覧

| プレースホルダー | 説明 | 例 | 必須 |
|-----------------|------|-----|------|
| `{{report_date}}` | レポート日付 | `2026-01-22` | ✅ |
| `{{start_date}}` | 対象期間開始日 | `2026-01-14` | ✅ |
| `{{end_date}}` | 対象期間終了日 | `2026-01-21` | ✅ |
| `{{highlights}}` | 今週のハイライト（箇条書き） | - S&P 500が2.5%上昇... | ✅ |
| `{{spx_return}}` | S&P 500 週間リターン | `+2.50%` | ✅ |
| `{{rsp_return}}` | RSP 週間リターン | `+1.80%` | ✅ |
| `{{vug_return}}` | VUG 週間リターン | `+3.20%` | ✅ |
| `{{vtv_return}}` | VTV 週間リターン | `+1.20%` | ✅ |
| `{{mag7_summary}}` | MAG7のサマリー（1〜2行） | TSLAが+3.70%でトップ | ✅ |
| `{{top_sectors}}` | 上位3セクター | IT, エネルギー, 金融 | ✅ |
| `{{bottom_sectors}}` | 下位3セクター | ヘルスケア, 公益, 素材 | ✅ |
| `{{report_path}}` | 詳細レポートへのパス | articles/weekly_comment_20260122/02_edit/weekly_comment.md | ✅ |
| `{{generated_at}}` | 生成日時（JST） | `2026-01-22 09:30 (JST)` | ✅ |

## ラベル設定

### 必須ラベル

- `report`: 週次レポート Issue に付与

### オプションラベル

| ラベル | 条件 |
|--------|------|
| `bullish` | 市場センチメントが強気の場合 |
| `bearish` | 市場センチメントが弱気の場合 |

## GitHub Project #15 設定

Issue 作成後、以下を設定：

1. **Project追加**: `gh project item-add 15 --owner YH-05 --url {issue_url}`
2. **Status設定**: `Weekly Report` を設定
3. **公開日時設定**: レポート日付を設定

### Status Option ID

| ステータス | Option ID |
|-----------|-----------|
| Weekly Report | `d5257bbb` |

### Project Field ID

| フィールド | Field ID |
|-----------|----------|
| Status | `PVTSSF_lAHOBoK6AM4BMpw_zg739ZE` |
| 公開日時 | `PVTF_lAHOBoK6AM4BMpw_zg8BzrI` |

## Issue 作成手順

```bash
# Step 1: 変数の準備
REPORT_DATE="2026-01-22"
START_DATE="2026-01-14"
END_DATE="2026-01-21"
GENERATED_AT=$(TZ=Asia/Tokyo date '+%Y-%m-%d %H:%M (JST)')

# Step 2: Issue本文を生成（プレースホルダーを置換）
body="## 週次マーケットレポート ${REPORT_DATE}

**対象期間**: ${START_DATE} 〜 ${END_DATE}

### 今週のハイライト

${highlights}

### 主要指数サマリー

| 指数 | 週間リターン |
|------|-------------|
| S&P 500 | ${spx_return} |
| 等ウェイト (RSP) | ${rsp_return} |
| グロース (VUG) | ${vug_return} |
| バリュー (VTV) | ${vtv_return} |

### MAG7 サマリー

${mag7_summary}

### セクター概況

**上位セクター**: ${top_sectors}
**下位セクター**: ${bottom_sectors}

### 詳細レポート

📄 [Markdownレポート](${report_path})

---

**生成日時**: ${GENERATED_AT}
**自動生成**: このIssueは \`/generate-market-report --weekly-comment\` コマンドによって作成されました。
"

# Step 3: Issue作成
issue_url=$(gh issue create \
    --repo YH-05/quants \
    --title "[週次レポート] ${REPORT_DATE} マーケットレポート" \
    --body "$body" \
    --label "report")

# Step 4: Issue番号を抽出
issue_number=$(echo "$issue_url" | grep -oE '[0-9]+$')

# Step 5: GitHub Project に追加
gh project item-add 15 --owner YH-05 --url "$issue_url"

# Step 6: Status を Weekly Report に設定
# (GraphQL APIを使用)

# Step 7: Issueをclose（レポート完成後）
# gh issue close "$issue_number" --repo YH-05/quants
```

## ハイライトの生成ガイドライン

`{{highlights}}` には以下の形式で3〜5個のポイントを箇条書きで記載：

```markdown
- S&P 500が週間+2.50%上昇、年初来高値を更新
- テクノロジーセクターがグロース株をけん引
- TSLAが+3.70%で週間MAG7トップパフォーマー
- Fed議長発言で利下げ期待が後退
- 決算シーズン本格化、主要企業の業績に注目
```

### ハイライト選定基準

1. **主要指数の動き**: S&P 500, NASDAQ の週間パフォーマンス
2. **セクターローテーション**: 上昇・下落の顕著なセクター
3. **個別銘柄**: MAG7 の注目すべき動き
4. **マクロ要因**: Fed, 経済指標, 地政学リスク
5. **今後の注目点**: 決算発表、経済指標発表など

## RSSニューステンプレートとの整合性

### 共通点

| 項目 | RSSニュース | 週次レポート |
|------|------------|--------------|
| プレースホルダー形式 | `{{name}}` | `{{name}}` |
| 日時形式 | JST表示 | JST表示 |
| GitHub Project | #15 | #15 |
| 自動生成表記 | あり | あり |

### 相違点

| 項目 | RSSニュース | 週次レポート |
|------|------------|--------------|
| タイトルプレフィックス | `[テーマ名]` | `[週次レポート]` |
| Status | テーマ別 | `Weekly Report` |
| 内容 | 単一記事の要約 | 週間サマリー |
| リンク | 情報源URL | レポートファイルパス |

## 出力例

### Issue タイトル

```
[週次レポート] 2026-01-22 マーケットレポート
```

### Issue 本文

```markdown
## 週次マーケットレポート 2026-01-22

**対象期間**: 2026-01-14 〜 2026-01-21

### 今週のハイライト

- S&P 500が週間+2.50%上昇、年初来高値を更新
- テクノロジーセクターがグロース株をけん引
- TSLAが+3.70%で週間MAG7トップパフォーマー
- Fed議長発言で利下げ期待がやや後退
- 来週から決算シーズン本格化

### 主要指数サマリー

| 指数 | 週間リターン |
|------|-------------|
| S&P 500 | +2.50% |
| 等ウェイト (RSP) | +1.80% |
| グロース (VUG) | +3.20% |
| バリュー (VTV) | +1.20% |

### MAG7 サマリー

TSLAが+3.70%でトップ、NVDAは+1.90%。META, GOOGLが週間マイナス。

### セクター概況

**上位セクター**: IT, エネルギー, 金融
**下位セクター**: ヘルスケア, 公益, 素材

### 詳細レポート

📄 [Markdownレポート](articles/weekly_comment_20260122/02_edit/weekly_comment.md)

---

**生成日時**: 2026-01-22 09:30 (JST)
**自動生成**: このIssueは `/generate-market-report --weekly-comment` コマンドによって作成されました。
```

## 参照

- **RSSニューステンプレート**: `.claude/skills/finance-news-workflow/templates/issue-template.md`
- **週次コメントコマンド**: `.claude/commands/generate-market-report.md`
- **GitHub Project #15**: https://github.com/users/YH-05/projects/15
