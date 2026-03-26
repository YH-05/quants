# 議論メモ: ETF.com APIデータ取得調査

**日付**: 2026-03-24
**議論ID**: disc-2026-03-24-etfcom-api-investigation
**参加**: ユーザー + AI

## 背景・コンテキスト

日次処理でデータ蓄積できるもののなかにETF.comのデータが含まれているか確認。
`market.etfcom` パッケージは存在するが、`automation/` や cron/trigger には未登録。
実際にデータ取得を試行し、APIの現状を確認した。

## 調査結果

### APIエンドポイント疎通テスト

| エンドポイント | メソッド | ステータス | 備考 |
|--------------|---------|-----------|------|
| `/v2/fund/tickers` | GET | **200 OK** | 5,114 ETF取得成功 |
| `/private/apps/fundflows/tickers` | GET | 404 | 廃止 |
| `/private/apps/fundflows/fund-flows-query` | POST | 404 | 廃止 |
| `/private/apps/fundflows/fund-details` | GET/POST | 404 | 廃止 |
| `/v2/fund/flows` 系（各種パス） | GET/POST | 全て404 | 廃止 |
| `https://www.etf.com/SPY`（HTMLページ） | GET | 200 | JS動的レンダリング、curl_cffiではセレクタヒットせず |

### 取得可能なデータ（/v2/fund/tickers）

- **ETF数**: 5,114銘柄
- **カラム**: `fundId`, `fund`（名称）, `ticker`, `inceptionDate`, `assetClass`, `issuer`
- **アセットクラス分布**: Equity 3,133 / Fixed Income 989 / Alternatives 572 / Asset Allocation 191 / Currency 130 / Commodities 99
- **主要発行体**: BlackRock 477 / First Trust 289 / Invesco 246 / State Street 181 / Vanguard 100

### 取得不可能なデータ

| データ | 理由 |
|--------|------|
| 日次ファンドフロー | REST API全て404（廃止） |
| ファンダメンタルズ | HTMLがJS動的レンダリング、curl_cffiでは取得不可 |
| fund-details | REST API 404（廃止） |

### コード側の問題

- `HistoricalFundFlowsCollector._resolve_fund_id()` が `TICKERS_API_URL`（`/private/apps/fundflows/tickers`）を呼んでおり404。`/v2/fund/tickers` に修正が必要。
- `FundamentalsCollector` / `FundFlowsCollector` はPlaywrightフォールバックを持つが、ブラウザ依存のため日次自動化には不向き。

## 決定事項

| ID | 内容 | コンテキスト |
|----|------|------------|
| dec-2026-03-24-001 | ETF.comティッカーリストAPIは稼働中（5,114 ETF）。ファンドフローAPIは廃止のため現状では日次蓄積不可。 | API疎通テストで確認 |
| dec-2026-03-24-002 | ファンドフローデータが必要な場合、Playwright経由のスクレイピングまたは代替データソース（yfinance等）の検討が必要 | REST API廃止、HTMLはJS動的レンダリング |

## アクションアイテム

| ID | 内容 | 優先度 | ステータス |
|----|------|--------|----------|
| act-2026-03-24-001 | `HistoricalFundFlowsCollector._resolve_fund_id()` のAPI URLを `/v2/fund/tickers` に修正 | 中 | pending |
| act-2026-03-24-002 | ETFファンドフローの代替データソース調査（yfinance, Bloomberg, NASDAQ等） | 高 | pending |
| act-2026-03-24-003 | ETF.comティッカーリスト日次蓄積の自動化検討（週1回更新で十分な可能性） | 低 | pending |

## 参考情報

- `market.etfcom` パッケージ: `src/market/etfcom/`
- REST API ベースURL: `https://api-prod.etf.com`
- 稼働中エンドポイント: `GET /v2/fund/tickers`
- コード内の定数: `src/market/etfcom/constants.py` の `TICKERS_API_URL` が古いURL
