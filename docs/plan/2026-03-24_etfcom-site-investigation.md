# 議論メモ: ETF.com サイト再調査 — 全API発見・パッケージ書き直し方針決定

**日付**: 2026-03-24
**議論ID**: disc-2026-03-24-etfcom-site-investigation
**参加**: ユーザー + AI
**前回の議論**: disc-2026-03-24-etfcom-api-investigation

## 背景・コンテキスト

前回の調査では「ファンドフローAPIは廃止済み（全て404）、日次蓄積不可」と結論。
しかし site-investigator スキル（Playwright MCP）でブラウザのネットワークリクエストを監視したところ、
実際にはブラウザが **新しい API パス** `/v2/fund/fund-details` を叩いていることが判明。
前回叩いた `/private/apps/fundflows/*` は旧パスであり、API は `/v2/` に移行済みだった。

## 調査結果

### サイト技術スタック

- **CMS**: Drupal 11.1.8
- **フロントエンド**: React ウィジェット埋め込み（Highcharts, TradingView）
- **データプロバイダー**: FactSet
- **CDN/保護**: Cloudflare（JavaScript チャレンジ）
- **RSS**: `https://www.etf.com/feeds`（ニュース記事用）

### 発見した API エンドポイント

#### POST /v2/fund/fund-details（18クエリ）

| # | クエリ名 | データ内容 | 更新頻度 |
|---|---------|-----------|---------|
| 1 | `fundFlowsData` | 日次NAV, ファンドフロー, AUM, プレミアム/ディスカウント, シェア数 | 日次 |
| 2 | `topHoldings` | 保有銘柄（トップ10+全件）、各ウェイト | 週次 |
| 3 | `fundPortfolioData` | P/E, P/B, 配当利回り, 時価総額加重平均 | 週次 |
| 4 | `sectorIndustryBreakdown` | セクター配分 | 週次 |
| 5 | `regions` | 地域配分 | 月次 |
| 6 | `countries` | 国別配分 | 月次 |
| 7 | `economicDevelopment` | 経済発展度分類 | 月次 |
| 8 | `fundIntraData` | 日中価格データ | 日次 |
| 9 | `compareTicker` | 競合ETF比較 | 月次 |
| 10 | `fundSpreadChart` | スプレッドチャート | 週次 |
| 11 | `fundPremiumChart` | プレミアム/ディスカウントチャート | 週次 |
| 12 | `fundTradabilityData` | 出来高, スプレッド, 流動性指標 | 週次 |
| 13 | `fundTradabilitySummary` | クリエーションユニット, 流動性 | 月次 |
| 14 | `fundPortfolioManData` | 経費率, トラッキング差異 | 月次 |
| 15 | `fundTaxExposuresData` | 税金関連 | 月次 |
| 16 | `fundStructureData` | 法的構造, デリバティブ使用, 証券貸借 | 月次 |
| 17 | `fundRankingsData` | ETF.com ランキング（効率性/流動性/適合性） | 月次 |
| 18 | `fundPerformanceStatsData` | パフォーマンス統計, R², グレード | 月次 |

#### GET エンドポイント

| エンドポイント | データ内容 |
|--------------|-----------|
| `/v2/fund/tickers` | 5,114 ETF のティッカー・fund_id マッピング |
| `/v2/quotes/delayedquotes?tickers=SPY` | 遅延リアルタイムクォート（OHLC, Bid/Ask） |
| `/v2/fund/charts?dataPoint=splitPrice&interval=MAX&ticker=SPY` | 価格チャート |
| `/v2/fund/performance/{fund_id}` | パフォーマンスリターン（1M/3M/YTD/1Y/3Y/5Y） |

#### 認証の仕組み

```
GET https://www.etf.com/api/v1/api-details
→ {
    apiBaseUrl: "https://api-prod.etf.com",
    fundApiKey: "0QE2aa6trh...", (256文字)
    toolsApiKey: "eyJhbG...",    (JWT)
    oauthToken: "eyJhbG...",     (JWT, 24h有効)
    realTimeApiUrl: "https://real-time-prod.etf.com/graphql",
    graphQLApiUrl: "https://data.etf.com"
  }
```

#### Cloudflare バイパス

```python
import curl_cffi.requests as requests
session = requests.Session(impersonate='chrome')
session.get('https://www.etf.com/')       # Cloudflare クッキー取得
session.get('https://www.etf.com/api/v1/api-details')  # API Key 取得
session.post('https://api-prod.etf.com/v2/fund/fund-details', json={...})  # データ取得
```

### fundFlowsData レスポンス例

```json
{
  "name": "funddetails",
  "ticker": "SPY",
  "data": {
    "fundFlowsData": {
      "data": [
        {
          "navDate": "2024-04-03",
          "nav": 519.255414,
          "navChange": 0.588794,
          "navChangePercent": 0.113521,
          "premiumDiscount": -0.204586,
          "fundFlows": -311199972,
          "sharesOutstanding": 1015882116,
          "aum": 526904143424.17
        }
      ]
    }
  }
}
```

## 決定事項

| ID | 内容 | コンテキスト |
|----|------|------------|
| dec-2026-03-24-003 | /v2/fund/fund-details POST API は18種類のクエリで完全動作中。旧パス /private/ は廃止済み。 | Playwright ネットワーク監視 + curl_cffi 検証 |
| dec-2026-03-24-004 | market.etfcom パッケージは既存コレクター廃止→APIクライアントベースで全面書き直し | ユーザー選択: APIクライアント書き直し |
| dec-2026-03-24-005 | 全18種類を段階的に実装。蓄積頻度は日次(フロー)+週次(Holdings)+月次(メタデータ)の階層化 | ユーザー選択: 全データ網羅 + 階層化蓄積 |

## アクションアイテム

| ID | 内容 | 優先度 | ステータス |
|----|------|--------|----------|
| act-2026-03-24-004 | ETFComClient クラス設計・実装（/v2/fund/fund-details API ベース） | 高 | pending |
| act-2026-03-24-005 | types.py を API レスポンス構造に合わせて再設計 | 高 | pending |
| act-2026-03-24-006 | SQLite ストレージ設計 — 日次/週次/月次テーブル | 高 | pending |
| act-2026-03-24-007 | automation/ への蓄積タスク組み込み | 中 | pending |
| act-2026-03-24-008 | GraphQL エンドポイント（real-time, data.etf.com）の追加調査 | 低 | pending |

## 前回の ActionItem 更新

| ID | 更新内容 |
|----|---------|
| act-2026-03-24-001 | 解消 — URL修正ではなく全面書き直しに方針変更 |
| act-2026-03-24-002 | 解消 — ETF.com API 自体が動作することが判明、代替データソース不要 |
| act-2026-03-24-003 | 吸収 — act-2026-03-24-007 に統合 |

## 次回の議論トピック

- ETFComClient のクラス設計（メソッド構成、エラーハンドリング）
- SQLite テーブルスキーマの詳細設計
- レート制限の実測値確認
- GraphQL エンドポイントの調査結果

## 参考情報

- サイト調査レポート（JSON）: `.tmp/site-reports/etf.com/report.json`
- スクリーンショット: `.tmp/site-reports/etf.com/screenshots/`
- 既存パッケージ: `src/market/etfcom/`
- 前回の議論メモ: `docs/plan/2026-03-24_etfcom-api-investigation.md`
