# NASDAQ API エンドポイント調査

**日付**: 2026-03-24
**議論ID**: disc-2026-03-24-nasdaq-api-endpoints

## 概要

NASDAQ API (`api.nasdaq.com`) の全エンドポイントを調査。Stock Screener 以外に、無料・認証不要で多数のデータが取得可能。既存の `NasdaqSession`（curl_cffi + TLS フィンガープリント偽装）がそのまま利用可能。

## 実装済み

- `/screener/stocks` — `market.nasdaq.ScreenerCollector`

## 未実装エンドポイント一覧

### 1. Quote（銘柄単位）

| エンドポイント | データ | assetclass対応 |
|---|---|---|
| `/quote/{symbol}/info` | リアルタイム株価、出来高、マーケット状態 | stocks, etf, index, crypto 等 |
| `/quote/{symbol}/summary` | セクター、52週高安、時価総額、P/E、配当利回り | 同上 |
| `/quote/{symbol}/historical?fromdate=&todate=&limit=` | OHLCV日次データ | 同上 |
| `/quote/{symbol}/chart?charttype=rs` | 分足イントラデイ | 同上 |
| `/quote/{symbol}/dividends` | 配当支払い履歴 | stocks |
| `/quote/{symbol}/eps` | EPS履歴（予想 vs 実績） | stocks |
| `/quote/{symbol}/short-interest` | 空売り残高、カバー日数（隔月） | stocks |
| `/quote/{symbol}/option-chain` | オプションチェーン（コール/プット、OI） | stocks |
| `/quote/{symbol}/extended-trading?markettype=pre|post` | プレ/アフターマーケット | stocks |
| `/quote/{symbol}/realtime-trades` | リアルタイム約定データ | stocks |
| `/quote/watchlist?symbol=SYM1|assetclass` | バッチクオート（複数銘柄一括） | 複合 |
| `/quote/indices` | 全NASDAQ指数一覧 + 最新値 | index |

### 2. Company（銘柄単位）

| エンドポイント | データ |
|---|---|
| `/company/{symbol}/company-profile` | 企業概要、セクター、住所、URL |
| `/company/{symbol}/financials?frequency=1or2` | PL/BS/CF/財務比率（年次/四半期） |
| `/company/{symbol}/earnings-surprise` | EPS実績 vs コンセンサス |
| `/company/{symbol}/revenue?limit=` | 四半期売上・EPS推移 |
| `/company/{symbol}/insider-trades?limit=&type=ALL|buys|sells` | インサイダー売買（氏名、役職、株数、金額） |
| `/company/{symbol}/institutional-holdings?limit=&type=TOTAL|NEW|INCREASED|DECREASED|SOLDOUT` | 機関投資家保有（上位ホルダー、増減） |
| `/company/{symbol}/sec-filings?limit=` | 10-K, 10-Q, 8-K等（ダウンロードURL付き） |
| `/company/{symbol}/holdings?assetclass=stocks` | この銘柄を保有するETF一覧 |

### 3. Analyst（銘柄単位）

| エンドポイント | データ |
|---|---|
| `/analyst/{symbol}/earnings-forecast` | コンセンサスEPS予想（四半期/年次）、アナリスト数、修正回数 |
| `/analyst/{symbol}/ratings` | Buy/Hold/Sell分布、アップグレード/ダウングレード |
| `/analyst/{symbol}/targetprice` | コンセンサス目標株価（高/安/平均）、買い/売り/ホールド数 |
| `/analyst/{symbol}/peg-ratio` | PEG比率、成長率 |
| `/analyst/{symbol}/estimate-momentum` | 推定値修正モメンタム |
| `/analyst/{symbol}/earnings-date` | 次回決算日 |

### 4. Calendar（マーケット全体）

| エンドポイント | データ |
|---|---|
| `/calendar/earnings?date=YYYY-MM-DD` | 当日の全決算企業（EPS予想、前年EPS、時価総額） |
| `/calendar/dividends?date=YYYY-MM-DD` | 当日の権利落ち銘柄 |
| `/calendar/splits?date=YYYY-MM-DD` | 当日の株式分割 |
| `/calendar/economicevents?date=YYYY-MM-DD` | 経済イベント（不安定） |

### 5. IPO

| エンドポイント | データ |
|---|---|
| `/ipo/calendar?date=YYYY-MM` | IPOカレンダー（priced/filed/upcoming/withdrawn） |

### 6. Screener（マーケット全体）

| エンドポイント | データ |
|---|---|
| `/screener/etf?tableonly=true&limit=0` | ETFスクリーナー（~4,400本） |
| `/screener/mutualfunds?tableonly=true&limit=0` | 投資信託スクリーナー |
| `/screener/index?tableonly=true&limit=0` | インデックスセキュリティ |

### 7. Market

| エンドポイント | データ |
|---|---|
| `/marketmovers` | 値上がり/値下がり/出来高ランキング（株式/ETF/投信） |
| `/market-info` | マーケット開閉状態、取引時間 |

### 8. News

| エンドポイント | データ |
|---|---|
| `www.nasdaq.com/api/news/topic/articlebysymbol?q={symbol}|STOCKS` | 銘柄ニュース（注: www.nasdaq.com ドメイン） |

### 9. Charting (charting.nasdaq.com)

| エンドポイント | データ |
|---|---|
| `charting.nasdaq.com/data/charting/historical?symbol=&date=start~end` | 日足OHLC（curl_cffi必須） |
| `charting.nasdaq.com/data/charting/intraday?symbol=&mostRecent=` | 分足データ（curl_cffi必須） |

## 共通仕様

- **認証**: 不要（全エンドポイント無料）
- **レスポンス形式**: `{"data": {...}, "message": null, "status": {"rCode": 200, ...}}`
- **User-Agent**: 必須（空だと拒否）
- **ボット対策**: Akamai — 既存 NasdaqSession で対応済み
- **assetclass パラメータ**: `stocks`, `etf`, `index`, `mutualfunds`, `crypto`, `commodities`, `currencies`, `fixedincome`, `futures`

## 決定事項

| ID | 内容 | コンテキスト |
|----|------|------------|
| dec-2026-03-24-001 | NASDAQ APIは無料・認証不要で9カテゴリ30+エンドポイントを提供 | 既存NasdaqSessionがそのまま利用可能 |
| dec-2026-03-24-002 | 日次蓄積優先度トップ5を特定 | カレンダー系 > スクリーナー > 銘柄単位データ |

## アクションアイテム

| ID | 内容 | 優先度 | 状態 |
|----|------|--------|------|
| act-2026-03-24-001 | 決算カレンダー (`/calendar/earnings`) の実装 | 高 | pending |
| act-2026-03-24-002 | Market Movers (`/marketmovers`) の実装 | 高 | pending |
| act-2026-03-24-003 | ETFスクリーナー (`/screener/etf`) の実装 | 高 | pending |
| act-2026-03-24-004 | アナリストデータ (`/analyst/{symbol}/*`) の実装 | 中 | pending |
| act-2026-03-24-005 | インサイダー/機関投資家データの実装 | 中 | pending |

## 参考情報

- [stonkBot NASDAQ_API_DOC.md](https://github.com/steveman1123/stonkBot/blob/master/NASDAQ_API_DOC.md) — コミュニティによる最も包括的なドキュメント
- [evgenyzorin/Financials nasdaq-api-v3.0.2.ipynb](https://github.com/evgenyzorin/Financials/blob/main/nasdaq-api-v3.0.2.ipynb) — 13エンドポイントの動作確認済みNotebook
