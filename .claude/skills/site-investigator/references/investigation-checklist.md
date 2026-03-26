# サイト調査チェックリスト

各 Phase で確認すべき項目の詳細リスト。
SKILL.md の調査プロトコルに沿って、漏れなく調査するためのリファレンス。

## Phase 1: 初回アクセス・概要把握

### 基本情報

- [ ] ページタイトル（`<title>` タグ）
- [ ] ページ種別: 一覧 / 個別記事 / トップ / ランディング / SPA
- [ ] 言語: HTML `lang` 属性、コンテンツの言語
- [ ] レスポンシブ対応: viewport meta の有無

### CMS / フレームワーク検出

以下の痕跡を `browser_evaluate` で確認:

```javascript
return {
  // WordPress
  wordpress: !!document.querySelector('meta[name="generator"][content*="WordPress"]')
    || !!document.querySelector('link[href*="wp-content"]'),
  // Next.js
  nextjs: !!document.getElementById('__next')
    || !!document.querySelector('script[src*="_next"]'),
  // Nuxt.js
  nuxtjs: !!document.getElementById('__nuxt')
    || !!document.querySelector('[data-n-head]'),
  // Gatsby
  gatsby: !!document.getElementById('___gatsby'),
  // Hugo
  hugo: !!document.querySelector('meta[name="generator"][content*="Hugo"]'),
  // Wix
  wix: !!document.querySelector('meta[name="generator"][content*="Wix"]'),
  // Shopify
  shopify: !!document.querySelector('meta[name="shopify"]')
    || !!document.querySelector('link[href*="cdn.shopify.com"]'),
};
```

### 障害物の処理

- [ ] Cookie 同意バナー → 「Accept」「同意」ボタンを `browser_click`
- [ ] ニュースレター登録ポップアップ → 「閉じる」「×」ボタンを `browser_click`
- [ ] 年齢確認ダイアログ → 必要に応じて処理
- [ ] チャットウィジェット → 邪魔なら閉じる

## Phase 2: メタ情報

### RSS フィード検出チェックリスト

- [ ] `<link type="application/rss+xml">` の存在
- [ ] `<link type="application/atom+xml">` の存在
- [ ] `/feed` パスへのアクセス
- [ ] `/rss` パスへのアクセス
- [ ] `/feed.xml` パスへのアクセス
- [ ] `/atom.xml` パスへのアクセス
- [ ] `/blog/feed` パスへのアクセス（ブログがサブパスの場合）

### サイトマップ検出チェックリスト

- [ ] `/sitemap.xml` の存在
- [ ] `/sitemap_index.xml` の存在
- [ ] `/sitemap/` ディレクトリの存在
- [ ] robots.txt 内の `Sitemap:` ディレクティブ
- [ ] サイトマップの形式: XML / テキスト / インデックス

### robots.txt 解析項目

- [ ] `User-agent` ルールの対象
- [ ] `Disallow` ルール一覧
- [ ] `Allow` ルール（例外許可）
- [ ] `Crawl-delay` の値
- [ ] `Sitemap` URL の指定

### meta タグ収集項目

- [ ] `og:title`, `og:description`, `og:image`（OGP）
- [ ] `twitter:card`, `twitter:title`（Twitter Card）
- [ ] `canonical` URL
- [ ] `generator`（CMS 検出用）
- [ ] `robots`（noindex, nofollow）
- [ ] `description`

## Phase 3: 一覧ページ構造

### 繰り返し要素の特定

以下のパターンで繰り返し構造を探す（優先度順）:

1. `<article>` 要素の繰り返し
2. `<li>` 内の記事カード
3. `<div>` のクラス名に `card`, `item`, `post`, `entry` を含む要素
4. `data-*` 属性で統一されたコンテナ

### 各アイテム内の要素

- [ ] タイトル: 通常 `h2` or `h3` 内のリンク
- [ ] URL: タイトルリンクの `href`
- [ ] 日付: `<time>` 要素、`datetime` 属性
- [ ] サムネイル: `<img>` 要素、`src` / `data-src`
- [ ] 著者: `.author`, `[rel="author"]`
- [ ] 概要/抜粋: `.excerpt`, `.summary`, `<p>` 要素
- [ ] カテゴリ: カテゴリリンク、バッジ

### ページネーション方式

| 方式 | 検出方法 |
|------|----------|
| Numbered | `?page=`, `/page/N/` 形式のリンク、数字付きナビゲーション |
| Next/Prev | 「次へ」「Next」「→」ボタン、`rel="next"` リンク |
| Infinite Scroll | スクロールイベントリスナー、IntersectionObserver |
| Load More | 「もっと見る」「Load More」ボタン |
| None | 1 ページに全件表示 |

### セレクタ検証スクリプト

```javascript
// browser_evaluate で実行: 候補セレクタの妥当性検証
function validateSelectors(selectors) {
  const results = {};
  for (const [name, selector] of Object.entries(selectors)) {
    const elements = document.querySelectorAll(selector);
    results[name] = {
      count: elements.length,
      sample: elements[0] ? elements[0].textContent.trim().substring(0, 100) : null,
    };
  }
  return results;
}

return validateSelectors({
  article: 'article.post-card',
  title: 'article.post-card h2 a',
  date: 'article.post-card time',
});
```

## Phase 4: 個別コンテンツページ

### 必須要素

- [ ] タイトル: `h1` 要素（通常 1 つだけ）
- [ ] 本文コンテナ: 最大のテキストブロックを含む要素
- [ ] 公開日: `<time>` 要素、`datetime` 属性付き
- [ ] 著者名: リンクまたはテキスト

### オプション要素

- [ ] 更新日: 公開日とは別の日付
- [ ] カテゴリ: リンク形式のカテゴリ名
- [ ] タグ: タグクラウドまたはリスト
- [ ] アイキャッチ画像: 記事上部の大きな画像
- [ ] 関連記事: 記事下部のリンクリスト
- [ ] コメント欄: コメントセクションの有無
- [ ] SNS シェアボタン: シェア UI の有無
- [ ] 目次: ページ内リンクの目次

### ペイウォール/ログイン壁検出

```javascript
// browser_evaluate で確認
return {
  // ペイウォール関連要素
  paywallOverlay: !!document.querySelector(
    '[class*="paywall"], [class*="subscribe"], [id*="paywall"]'
  ),
  // ログインモーダル
  loginModal: !!document.querySelector(
    '[class*="login-modal"], [class*="signin"], [class*="auth-wall"]'
  ),
  // 「続きを読む」系
  readMore: !!document.querySelector(
    '[class*="read-more-gate"], [class*="premium-content"]'
  ),
  // 本文の文字数（少なすぎれば切断の疑い）
  bodyLength: document.querySelector('article')?.textContent?.length || 0,
};
```

## Phase 5: 動的挙動

### SPA フレームワーク検出

- [ ] React: `[data-reactroot]`, `#__next`, `._reactRootContainer`
- [ ] Vue: `[data-v-]`, `#__nuxt`, `.__vue_root`
- [ ] Angular: `[ng-version]`, `[_nghost]`
- [ ] Svelte: `[class*="svelte-"]`

### API エンドポイント発見

`browser_network_requests` で以下のパターンを監視:

- `/api/` パスへの XHR/fetch
- JSON レスポンス（`Content-Type: application/json`）
- GraphQL エンドポイント（`/graphql`）
- REST API パターン（`/v1/`, `/v2/`）

API が見つかった場合、直接 API を叩く方が効率的なことが多い。
URL パターン、必要なヘッダー、レスポンス構造を記録する。

### lazy load パターン

- [ ] `<img loading="lazy">`: ネイティブ lazy load
- [ ] `<img data-src="...">`: カスタム lazy load（スクロール時に `src` にコピー）
- [ ] `<img class="lazyload">`: lazysizes 等のライブラリ
- [ ] `background-image` の遅延読み込み

### パフォーマンス情報

```javascript
// browser_evaluate で収集
const perf = performance.getEntriesByType('navigation')[0];
return {
  protocol: perf.nextHopProtocol, // h2, h3, http/1.1
  domContentLoaded: Math.round(perf.domContentLoadedEventEnd),
  loadComplete: Math.round(perf.loadEventEnd),
  transferSize: Math.round(perf.transferSize / 1024) + 'KB',
};
```
