# AI投資バリューチェーン Issue作成テンプレート

GitHub Issue作成時のフォーマット定義。投資視点4セクション構成。

## Issueタイトル形式

```
[{{category_label}}] {{japanese_title}}
```

### カテゴリ名プレフィックス

| カテゴリキー | プレフィックス | GitHubラベル | Status |
|------------|--------------|-------------|--------|
| `ai_llm` | `[AI/LLM開発]` | `ai-llm` | Company Release |
| `gpu_chips` | `[GPU・演算チップ]` | `ai-chips` | Company Release |
| `semiconductor_equipment` | `[半導体製造装置]` | `ai-semicon` | Company Release |
| `data_center` | `[データセンター・クラウド]` | `ai-datacenter` | Company Release |
| `networking` | `[ネットワーキング]` | `ai-network` | Company Release |
| `power_energy` | `[電力・エネルギー]` | `ai-power` | Company Release |
| `nuclear_fusion` | `[原子力・核融合]` | `ai-nuclear` | Company Release |
| `physical_ai` | `[フィジカルAI・ロボティクス]` | `ai-robotics` | Company Release |
| `saas` | `[SaaS・AI活用ソフトウェア]` | `ai-saas` | Company Release |
| `ai_infra` | `[AI基盤・MLOps]` | `ai-infra` | Company Release |

### タイトル翻訳ルール

- 英語タイトルは日本語に翻訳
- 企業名・固有名詞は原則そのまま（例: OpenAI, NVIDIA, GPT-5）
- 技術用語は一般的な表記を使用（例: inference -> 推論）
- 製品名はそのまま（例: Blackwell Ultra, Claude 4）

## Issue本文テンプレート

```markdown
## 概要

{{summary_section_概要}}

## 技術的意義

{{summary_section_技術的意義}}

## 市場影響

{{summary_section_市場影響}}

## 投資示唆

{{summary_section_投資示唆}}

---

### メタデータ

| 項目 | 値 |
|------|-----|
| 企業 | {{company_name}} |
| カテゴリ | {{category_label}} |
| 市場影響度 | {{impact_level}} |
| 関連銘柄 | {{tickers}} |
| 情報源URL | {{url}} |
| 公開日 | {{published_date}} |
| 収集日時 | {{collected_at}} |

---

**自動収集**: このIssueは AI Investment Value Chain Tracking ワークフローによって自動作成されました。
```

## フィールド一覧

| フィールド | 説明 | 例 | 必須 |
|-----------|------|-----|------|
| `{{category_label}}` | カテゴリ名（日本語） | `AI/LLM開発` | Yes |
| `{{japanese_title}}` | 記事タイトル（日本語） | `OpenAIがGPT-5を発表` | Yes |
| `{{summary_section_概要}}` | 投資視点の概要セクション | - | Yes |
| `{{summary_section_技術的意義}}` | 技術的意義セクション | - | Yes |
| `{{summary_section_市場影響}}` | 市場影響セクション | - | Yes |
| `{{summary_section_投資示唆}}` | 投資示唆セクション | - | Yes |
| `{{company_name}}` | 企業名 | `OpenAI` | Yes |
| `{{impact_level}}` | 市場影響度 | `high` | Yes |
| `{{tickers}}` | 関連銘柄（カンマ区切り） | `MSFT, GOOGL` | Yes |
| `{{url}}` | 元記事のURL | `https://openai.com/news/...` | Yes |
| `{{published_date}}` | 公開日時 | `2026-02-10` | Yes |
| `{{collected_at}}` | 収集日時（JST形式） | `2026-02-11 10:30(JST)` | Yes |

## 投資視点4セクション要約フォーマット

`{{summary_section_*}}` には以下の構造で要約を記載:

```markdown
### 概要
- [発表内容・主要事実を箇条書きで3-5行]
- [数値データがあれば必ず含める]
- [企業名・製品名を明記]

### 技術的意義
[技術的なブレークスルーの評価]
- 従来技術との比較
- 性能向上の定量的データ（ベンチマーク等）
- 技術的な差別化ポイント
[記事に該当情報がなければ「[記載なし]」]

### 市場影響
[関連銘柄・セクターへの影響分析]
- 直接的な影響を受ける企業・銘柄
- 競合企業への影響
- セクター全体への波及効果
- 短期・中期の株価への影響見通し
[記事に該当情報がなければ「[記載なし]」]

### 投資示唆
[投資家にとっての意味合い]
- 注目すべき投資機会
- リスク要因
- 今後のカタリスト（決算、製品リリース等）
- 推奨するウォッチリスト銘柄
[記事に該当情報がなければ「[記載なし]」]
```

### 各セクションの記載ルール

| セクション | 内容 | 最低文字数 | 記載なしの例 |
|-----------|------|-----------|-------------|
| 概要 | 主要事実、数値データ、企業名 | 200文字 | （常に何か記載できるはず） |
| 技術的意義 | ベンチマーク、性能比較、技術差別化 | 100文字 | 技術詳細の言及がない場合 |
| 市場影響 | 銘柄影響、セクター波及、株価見通し | 100文字 | 市場影響の言及がない場合 |
| 投資示唆 | 投資機会、リスク、カタリスト | 100文字 | 投資視点の言及がない場合 |

### finance-news-workflow の要約との違い

| 項目 | finance-news-workflow | ai-research-workflow |
|------|----------------------|---------------------|
| セクション数 | 4 | 4 |
| セクション1 | 概要 | 概要 |
| セクション2 | **背景** | **技術的意義** |
| セクション3 | **市場への影響** | **市場影響** |
| セクション4 | **今後の見通し** | **投資示唆** |
| 視点 | 一般金融ニュース | **投資家向けAIバリューチェーン** |
| 詳細度 | 3行箇条書き | **3-5行箇条書き + 分析** |

## ラベル設定

### 必須ラベル

- `ai-research`: 全AI Research Issueに付与
- `{category_label_gh}`: カテゴリラベル（例: `ai-llm`, `ai-chips`）
- `needs-review`: 自動収集記事のレビュー待ち

### カテゴリラベル一覧

| カテゴリキー | GitHubラベル | カラー | 説明 |
|------------|-------------|--------|------|
| `ai_llm` | `ai-llm` | `#7057ff` | AI/LLM開発 |
| `gpu_chips` | `ai-chips` | `#7057ff` | GPU・演算チップ |
| `semiconductor_equipment` | `ai-semicon` | `#7057ff` | 半導体製造装置 |
| `data_center` | `ai-datacenter` | `#7057ff` | データセンター・クラウド |
| `networking` | `ai-network` | `#7057ff` | ネットワーキング |
| `power_energy` | `ai-power` | `#7057ff` | 電力・エネルギー |
| `nuclear_fusion` | `ai-nuclear` | `#7057ff` | 原子力・核融合 |
| `physical_ai` | `ai-robotics` | `#7057ff` | フィジカルAI・ロボティクス |
| `saas` | `ai-saas` | `#7057ff` | SaaS・AI活用ソフトウェア |
| `ai_infra` | `ai-infra` | `#7057ff` | AI基盤・MLOps |

## URL設定の重要ルール

> **絶対に守ること**: `{{url}}`には**スクレイピングで取得したオリジナルのURL**をそのまま使用すること。
>
> - 正しい: 元記事のURLをそのまま使用
> - 間違い: WebFetchのリダイレクト先URL
> - 間違い: URLを推測・生成する
> - 間違い: URLを短縮・変換する

## Issue作成手順

```bash
# Step 1: 収集日時を取得
collected_at=$(TZ=Asia/Tokyo date '+%Y-%m-%d %H:%M')

# Step 2: Issueボディを直接生成（HEREDOCを使用）
body=$(cat <<EOF
## 概要

${summary_概要}

## 技術的意義

${summary_技術的意義}

## 市場影響

${summary_市場影響}

## 投資示唆

${summary_投資示唆}

---

### メタデータ

| 項目 | 値 |
|------|-----|
| 企業 | ${company_name} |
| カテゴリ | ${category_label} |
| 市場影響度 | ${impact_level} |
| 関連銘柄 | ${tickers} |
| 情報源URL | ${url} |
| 公開日 | ${published_date} |
| 収集日時 | ${collected_at}(JST) |

---

**自動収集**: このIssueは AI Investment Value Chain Tracking ワークフローによって自動作成されました。
EOF
)

# Step 3: Issue作成
issue_url=$(gh issue create \
    --repo YH-05/quants \
    --title "[${category_label}] ${japanese_title}" \
    --body "$body" \
    --label "ai-research" \
    --label "${category_label_gh}" \
    --label "needs-review")

# Step 4: Issue番号を抽出
issue_number=$(echo "$issue_url" | grep -oE '[0-9]+$')

# Step 5: Issueをclose
gh issue close "$issue_number" --repo YH-05/quants
```

## GitHub Project #44 設定

Issue作成後、以下を設定:

1. **Project追加**: `gh project item-add 44 --owner YH-05 --url {issue_url}`
2. **Category設定**: カテゴリに対応するCategory Option IDを設定
3. **Status設定**: 記事内容から自動判定したStatusを設定
4. **公開日時設定**: `YYYY-MM-DD` 形式で日付を設定
5. **Impact Level設定**: 市場影響度（low/medium/high）のOption IDを設定
6. **Tickers設定**: 関連銘柄をカンマ区切りテキストで設定

### Category Option ID一覧

| カテゴリラベル | Category Option ID |
|--------------|-------------------|
| `ai-llm` | `4b866888` |
| `ai-chips` | `46180b94` |
| `ai-semicon` | `c1e94c08` |
| `ai-datacenter` | `e1805e96` |
| `ai-network` | `90d413a5` |
| `ai-power` | `3afd6a01` |
| `ai-nuclear` | `b8c20582` |
| `ai-robotics` | `8c1c9e55` |
| `ai-saas` | `b65c392e` |
| `ai-infra` | `bf8cc297` |

### Status Option ID一覧

| Status | Option ID |
|--------|-----------|
| `Company Release` | `2c19ca36` |
| `Product Update` | `9dc533cc` |
| `Partnership` | `026e3e40` |
| `Earnings Impact` | `91a91f6b` |
| `Infrastructure` | `299507d2` |

### Impact Level Option ID一覧

| Impact Level | Option ID |
|-------------|-----------|
| `low` | `57bf5301` |
| `medium` | `c52c8ef0` |
| `high` | `8785a2d1` |

## 参照

- **スキル定義**: `.claude/skills/ai-research-workflow/SKILL.md`
- **詳細ガイド**: `.claude/skills/ai-research-workflow/guide.md`
- **サマリーテンプレート**: `./summary-template.md`
- **ai-research-article-fetcher**: `.claude/agents/ai-research-article-fetcher.md`
- **企業定義マスタ**: `data/config/ai-research-companies.json`
