---
name: site-investigator
description: >
  新しいサイトのスクレイピング前調査スキル。Playwright MCP でサイトにアクセスし、
  ページ構造・セレクタ・ページネーション・RSS/サイトマップ・動的挙動を自動解析して
  JSON + Markdown レポートを生成する。
  「サイト調査」「サイト構造を調べて」「スクレイピング前に構造を確認」「このURLの構造を解析」
  「セレクタを特定して」「ページネーションの仕組みを調べて」「RSSがあるか確認」
  と言われたら必ずこのスキルを使うこと。
  新しいサイトへのスクレイピング実装を始める前にプロアクティブに使用すること。
---

# site-investigator スキル

Playwright MCP を使って未知のサイトを体系的に調査し、スクレイピングに必要な
構造情報をまとめるスキル。Claude 自身がアクセシビリティツリーを読んで構造を判断する
（browser-use と同等のアプローチを追加コストなしで実現）。

## 前提条件

- Playwright MCP が Claude Code に設定済みであること
- ブラウザがインストール済みであること（`playwright install chromium`）

## 使い方

```
/site-investigator https://example.com/blog
```

引数としてサイトの URL を受け取り、5 Phase の調査を実行する。

## 調査プロトコル（5 Phase）

各 Phase を順番に実行する。Phase 間で得た情報を蓄積しながら進める。
詳細なチェック項目は `references/investigation-checklist.md` を参照。

### Phase 1: 初回アクセス・概要把握

**目的**: サイトの第一印象を掴み、基本情報を収集する。

1. `browser_navigate` で対象 URL にアクセス
2. `browser_take_screenshot` でスクリーンショットを保存
3. `browser_snapshot` でアクセシビリティツリーを取得
4. 以下を判定:
   - ページ種別（一覧 / 単体記事 / トップページ / SPA）
   - 言語（日本語 / 英語 / 他）
   - CMS/フレームワーク推定（WordPress, Next.js, etc.）
5. Cookie 同意バナーやポップアップがあれば `browser_click` で閉じる

**判定ロジック**: アクセシビリティツリーで `article` 要素の繰り返しがあれば一覧ページ、
単一の長い `article` なら個別記事ページ、と判断する。

### Phase 2: メタ情報の収集

**目的**: スクレイピングの最適手段（RSS / サイトマップ / 直接）を判断する材料を集める。

1. **RSS フィード検出**:
   ```javascript
   // browser_evaluate で実行
   const feeds = document.querySelectorAll('link[type="application/rss+xml"], link[type="application/atom+xml"]');
   return Array.from(feeds).map(f => ({ href: f.href, title: f.title }));
   ```
   - 見つからない場合、`/feed`, `/rss`, `/feed.xml`, `/atom.xml` に `browser_navigate` してみる

2. **サイトマップ検出**:
   - `browser_navigate` で `/sitemap.xml` にアクセス
   - 404 なら `/sitemap_index.xml`, `/sitemap/` も試す

3. **robots.txt 確認**:
   - `browser_navigate` で `/robots.txt` にアクセス
   - Disallow ルール、Crawl-delay、Sitemap 指定を読み取る

4. **meta タグ収集**:
   ```javascript
   // browser_evaluate で実行
   const metas = document.querySelectorAll('meta');
   return Array.from(metas).map(m => ({
     name: m.name || m.getAttribute('property'),
     content: m.content
   }));
   ```

### Phase 3: 一覧ページの構造解析

**目的**: 記事一覧のセレクタとページネーション方式を特定する。

Phase 1 で一覧ページと判定された場合（または一覧ページに遷移して）実行。

1. `browser_snapshot` のアクセシビリティツリーから繰り返し構造を発見:
   - 同一構造の `article`, `li`, `div` が並んでいるパターンを探す
   - 各アイテム内のタイトル（リンク）、日付、サムネイル、著者を特定

2. セレクタの検証:
   ```javascript
   // browser_evaluate で候補セレクタの要素数を確認
   return document.querySelectorAll('article.post-card').length;
   ```

3. ページネーション方式の特定:
   - アクセシビリティツリーで `navigation` や `pagination` を含む要素を探す
   - 方式を判定:
     - **numbered**: `?page=2` や `/page/2/` 形式のリンク
     - **next/prev**: 「次へ」「前へ」ボタン
     - **infinite scroll**: スクロールイベントで追加読み込み
     - **load more**: 「もっと見る」ボタン
   - infinite scroll の検出:
     ```javascript
     // browser_evaluate で IntersectionObserver やスクロールリスナーを確認
     return {
       hasIntersectionObserver: typeof IntersectionObserver !== 'undefined',
       scrollListeners: getEventListeners ? getEventListeners(window).scroll?.length : 'unknown'
     };
     ```

4. URL パターンの分析:
   - 記事リンクの href から URL パターンを抽出
   - 例: `/blog/{slug}`, `/articles/{id}`, `/{year}/{month}/{slug}`

### Phase 4: 個別コンテンツページの構造解析

**目的**: 記事ページの各要素のセレクタを特定する。

1. Phase 3 で見つけた記事リンクの 1 つを `browser_click` でクリック
2. `browser_snapshot` で記事ページの構造を取得
3. 以下の要素を特定:
   - **タイトル**: 通常 `h1` 要素
   - **本文**: `article`, `div.content`, `div.entry-content` 等のコンテナ
   - **公開日**: `time` 要素、`datetime` 属性
   - **著者**: `a[rel="author"]`, `.author` 等
   - **カテゴリ/タグ**: カテゴリリンク、タグクラウド
   - **関連記事**: 記事下部のリンクリスト
   - **コメント欄**: 有無の確認

4. ペイウォール/ログイン壁の検出:
   - 本文が途中で切れている、「続きを読むにはログイン」等のテキスト
   - `browser_snapshot` で `dialog`, `modal` 要素の存在

5. セレクタの検証:
   ```javascript
   // browser_evaluate で本文テキストが取得できるか確認
   const body = document.querySelector('div.entry-content');
   return body ? body.textContent.substring(0, 200) : null;
   ```

### Phase 5: 動的挙動の検出

**目的**: JavaScript 依存度と API エンドポイントを把握する。

1. **SPA / CSR 判定**:
   ```javascript
   // browser_evaluate で判定
   return {
     // React/Vue/Angular の痕跡
     hasReact: !!document.querySelector('[data-reactroot], #__next'),
     hasVue: !!document.querySelector('[data-v-], #__nuxt'),
     hasAngular: !!document.querySelector('[ng-version], [_nghost]'),
     // JS無効時に本文が空になるか
     bodyTextLength: document.body.innerText.length
   };
   ```

2. **API エンドポイントの発見**:
   - `browser_network_requests` で XHR/fetch リクエストを監視
   - JSON レスポンスを返す API があれば、直接 API を叩く方がスクレイピングより効率的

3. **lazy load 検出**:
   ```javascript
   return {
     lazyImages: document.querySelectorAll('img[loading="lazy"], img[data-src]').length,
     totalImages: document.querySelectorAll('img').length
   };
   ```

4. **レート制限の確認**:
   - `browser_network_requests` のレスポンスヘッダーから `X-RateLimit-*`, `Retry-After` を確認

## レポート生成

全 Phase 完了後、調査結果を JSON にまとめてレポート生成スクリプトを実行する。

### 手順

1. 調査結果を `.tmp/site-investigation-{domain}-{timestamp}.json` に保存
2. レポート生成:
   ```bash
   uv run python .claude/skills/site-investigator/scripts/generate_site_report.py \
     --input .tmp/site-investigation-{domain}-{timestamp}.json \
     --output-dir .tmp/site-reports/{domain}/
   ```
3. 出力:
   - `.tmp/site-reports/{domain}/report.json` — 構造化データ（後続スクリプト用）
   - `.tmp/site-reports/{domain}/report.md` — 人間が読むレポート
   - `.tmp/site-reports/{domain}/screenshots/` — スクリーンショット

### 入力 JSON スキーマ

調査結果は以下の構造で保存する:

```json
{
  "url": "https://example.com/blog",
  "investigated_at": "2026-03-21T10:00:00+09:00",
  "site_overview": {
    "type": "blog | news | ecommerce | portfolio | other",
    "technology": "WordPress | Next.js | Hugo | unknown",
    "language": "ja | en | ...",
    "has_rss": true,
    "rss_urls": ["https://example.com/feed"],
    "has_sitemap": true,
    "sitemap_url": "https://example.com/sitemap.xml",
    "robots_txt": {
      "exists": true,
      "disallow_rules": ["/wp-admin/"],
      "crawl_delay": null
    },
    "requires_login": false,
    "has_paywall": false
  },
  "list_page": {
    "url": "https://example.com/blog",
    "selectors": {
      "article_container": "article.post-card",
      "title": "article.post-card h2 a",
      "link": "article.post-card h2 a",
      "date": "article.post-card time",
      "author": "article.post-card .author",
      "thumbnail": "article.post-card img",
      "summary": "article.post-card .excerpt"
    },
    "items_per_page": 10,
    "pagination": {
      "type": "numbered | next_prev | infinite_scroll | load_more | none",
      "next_selector": "a.next",
      "url_pattern": "?page={n}"
    },
    "url_pattern": "/blog/{slug}"
  },
  "article_page": {
    "sample_url": "https://example.com/blog/sample-post",
    "selectors": {
      "title": "h1.entry-title",
      "body": "div.entry-content",
      "date": "time.published",
      "author": "span.author-name",
      "category": "a[rel='category']",
      "tags": "a[rel='tag']",
      "related_articles": ".related-posts a",
      "comments": "#comments"
    }
  },
  "dynamic_behavior": {
    "is_spa": false,
    "framework": null,
    "has_infinite_scroll": false,
    "has_lazy_load": true,
    "api_endpoints": [],
    "requires_js_rendering": false
  },
  "recommendations": {
    "best_approach": "rss | sitemap | direct_scraping | api",
    "fallback_approach": "sitemap | direct_scraping",
    "rate_limit_suggestion": "1 req/sec",
    "notes": ["特記事項"]
  }
}
```

## エラーハンドリング

| 状況 | 対応 |
|------|------|
| サイト到達不可 | エラー報告して終了 |
| Cookie 同意で操作困難 | スクリーンショット撮影 → 手動対応を提案 |
| ログイン必須 | Phase 1 でその旨を報告、認証情報の提供を求める |
| SPA で snapshot が薄い | `browser_evaluate` で DOM を直接読む |
| タイムアウト | 30秒待って再試行、3回失敗で報告 |

## 注意事項

- robots.txt の Disallow ルールを尊重すること
- 短時間に大量のリクエストを送らないこと（Phase 全体で 10-20 リクエスト程度）
- 個人情報やログイン情報をレポートに含めないこと
- スクリーンショットは調査目的のみに使用すること
