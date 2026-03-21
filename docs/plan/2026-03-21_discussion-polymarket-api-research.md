# 議論メモ: Polymarket API調査 — クオンツ/AI分析への応用

**日付**: 2026-03-21
**議論ID**: disc-2026-03-21-polymarket-api-research
**参加**: ユーザー + AI

## 背景・コンテキスト

Polymarket（世界最大の予測市場プラットフォーム）のAPIで取得可能なデータを公式ドキュメントに基づいて調査し、クオンツ分析・AI分析への応用可能性を検討した。

## 調査結果サマリー

### APIアーキテクチャ（4つの独立API）

| API | ベースURL | 認証 | 用途 |
|-----|----------|------|------|
| Gamma API | `https://gamma-api.polymarket.com` | 不要 | マーケット/イベント発見、メタデータ、カテゴリ |
| CLOB API | `https://clob.polymarket.com` | 公開エンドポイントは不要 | オーダーブック、価格、ヒストリカルデータ、取引 |
| Data API | `https://data-api.polymarket.com` | 不要 | ポジション、リーダーボード、OI、ホルダー分析 |
| Bridge API | `https://bridge.polymarket.com` | 必要 | 入出金（分析用途では不要） |

レートリミット: 公開エンドポイント約100リクエスト/分、非取引クエリ最大1,000コール/時間。

### 主要エンドポイント

**Gamma API（マーケットディスカバリー）**:
- `GET /events`, `GET /events/{id}` — イベント一覧・詳細
- `GET /markets`, `GET /markets/{id}` — マーケット一覧・詳細（outcomes, outcomePrices=暗示確率, tokenID等）
- `GET /public-search` — 横断検索
- `GET /tags` — カテゴリランキング（POLITICS, SPORTS, CRYPTO, ECONOMICS, TECH等）
- `GET /series`, `GET /sports`, `GET /teams` — メタデータ

**CLOB API（価格・オーダーブック）— 公開メソッド**:
- `getMarket`, `getOrderBook`, `getPrice`, `getMidpoint`, `getSpread` — リアルタイム価格・板
- `getLastTradePrice`, `getMarketTradesEvents` — 約定情報
- `getPricesHistory` — ヒストリカル価格（後述）
- `calculateMarketPrice` — マーケットインパクト推定
- `getTickSize`, `getFeeRateBps`, `getNegRisk` — マーケットパラメータ
- バルク対応: `getOrderBooks`, `getPrices`, `getMidpoints`, `getSpreads` 等

**Data API（分析・ポジション）**:
- `GET /positions?user={address}` — 現在ポジション
- `GET /closed-positions?user={address}` — 決済済みポジション
- `GET /activity?user={address}` — オンチェーン活動
- `GET /value?user={address}` — ポートフォリオ評価額
- `GET /trades` — 完全な取引履歴（Maker + Taker）
- `GET /oi` — オープンインタレスト
- `GET /holders` — マーケットトップホルダー
- `GET /v1/leaderboard` — トレーダーランキング（PNL/VOL、カテゴリ別、1d/7d/30d/all）

**WebSocket**（`wss://ws-subscriptions-clob.polymarket.com/ws/market`）:
- `book` — オーダーブックスナップショット
- `price_change` — 注文追加/キャンセル（price, size, side, best_bid, best_ask）
- `last_trade_price` — 約定（price, side, size, fee_rate_bps）
- `best_bid_ask` — ベストビッド/アスク変更
- `new_market` — 新規マーケット作成
- `market_resolved` — マーケット解決（winning_outcome）

**SDK**: Python (`py-clob-client`), TypeScript (`@polymarket/clob-client`), Rust (`polymarket_client_sdk`)

### ヒストリカルプライスデータ詳細

**エンドポイント**: `GET https://clob.polymarket.com/prices-history`

**レスポンス**: `{ history: [{ t: UNIXタイムスタンプ(uint32), p: 価格=暗示確率(float) }] }`

**`p`（価格）の定義**: オーダーブックのビッド・アスクスプレッドの仲値（midpoint）。スプレッドが$0.10を超える場合は直近約定価格（last trade price）にフォールバック。（出典: Polymarket Help Center）

**パラメータ**:

| パラメータ | 型 | 必須 | 説明 |
|-----------|------|------|------|
| `market` | string | 必須 | トークンID |
| `interval` | string | 任意 | `1h`, `6h`, `1d`, `1w`, `1m`, `max`, `all` |
| `fidelity` | integer | 任意 | データ精度（分単位、デフォルト1分） |
| `startTs` | number | 任意 | 開始UNIXタイムスタンプ |
| `endTs` | number | 任意 | 終了UNIXタイムスタンプ |

**制限事項**: 解決済みマーケットは12時間以上の粒度のみ返却。OHLCV・出来高時系列・OI時系列は直接提供なし。

**不足データの補完**: trades（出来高・VWAP構築）、WebSocket book/price_change（板スナップショット蓄積）、oi（定期ポーリング→OI時系列構築）で補完可能。

### 先物/オプションデータとの比較

**Polymarketの固有の価値（5点）**:

1. **非金融イベントのカバレッジ**: 政策・規制・テクノロジー・地政学等、先物/オプションで価格付けできないイベントの確率を定量化
2. **確率の直接読み取り**: モデル依存の逆算不要（例: FedWatchが23.3% vs Polymarket 2.4%のケースあり）
3. **情報反映速度**: 先物と同等かそれ以上に速い場合あり、24/7更新
4. **行動バイアスによるアルファ**: ロングショットバイアス、プラットフォーム間裁定、確率制約違反
5. **参加者の多様性**: リテール＋機関の混合→情報源の多様性

**Polymarketの限界（6点）**:

1. 流動性が先物/オプションより桁違いに薄い
2. バイナリ決済のため連続的な価格リスクのヘッジに不向き
3. Greeks・ボラティリティ面等の豊富な派生指標がない
4. 規制環境が未成熟
5. OHLCVの公式提供なし
6. 歴史が浅い（2020年〜）、バックテスト期間が限定的

**結論**: 先物/オプションとは相互補完的。最大価値は「非金融イベントの確率を定量化し、既存ポートフォリオのリスク管理やファクターモデルに組み込むこと」。

### クオンツ/AI分析への応用提案

**クオンツ分析**:
- カリブレーション分析（暗示確率 vs 実現結果）
- マーケットマイクロストラクチャー（流動性、インパクト、ボラティリティ）
- スマートマネー追跡（リーダーボード + ポジション変動）
- 政策予測→株価予測（POLITICS/ECONOMICSマーケット + yfinance相関）
- 地政学リスクインデックス構築

**AI/ML分析**:
- ミスプライシング検出モデル（XGBoost/LightGBM）
- 時系列予測（LSTM/Transformer）
- ニュース→確率変動予測（NLP統合）
- マーケットメイキング強化学習
- ナレッジグラフ統合（PredictionMarket→Entity/Claim/FinancialDataPoint）

## 決定事項

| ID | 内容 | コンテキスト |
|----|------|------------|
| dec-2026-03-21-001 | Polymarket APIは認証不要で公開データ取得可能であり、クオンツ分析基盤への統合価値がある | 4つのAPIすべてで分析用データが認証なしで取得可能。レートリミットも実用的な範囲 |
| dec-2026-03-21-002 | Polymarketの最大の差別化価値は「先物/オプションでは価格付けできない非金融イベント（政策・規制・テクノロジー）の確率を定量化できること」 | 先物/オプションとは相互補完的な関係。既存ポートフォリオのリスクファクターとしての統合が最も価値が高い |

## アクションアイテム

| ID | 内容 | 優先度 | 期限 |
|----|------|--------|------|
| act-2026-03-21-001 | Polymarketデータ収集パッケージの設計検討（market パッケージ内 or 新規パッケージ） | 中 | 未定 |
| act-2026-03-21-002 | ca_strategyへのイベント確率ファクター統合の概念検証（規制イベント確率→AI銘柄リスク調整） | 中 | 未定 |
| act-2026-03-21-003 | FedWatch vs Polymarket裁定分析の実証（prices-history + FRED FF先物データで乖離パターンを分析） | 低 | 未定 |

## 次回の議論トピック

- Polymarketデータ収集パッケージのアーキテクチャ設計（market.polymarket サブモジュール？）
- ca_strategyへの統合方法の詳細（ファクターモデルへの組み込み方）
- KG v2スキーマへの PredictionMarket ノード追加の検討
- レートリミット対策とキャッシュ戦略

## 参考ソース

- [Polymarket公式ドキュメント](https://docs.polymarket.com/)
- [Gamma API Overview](https://docs.polymarket.com/developers/gamma-markets-api/overview)
- [CLOB API Introduction](https://docs.polymarket.com/developers/CLOB/introduction)
- [Price History (Timeseries)](https://docs.polymarket.com/developers/CLOB/timeseries)
- [Public Methods](https://docs.polymarket.com/developers/CLOB/clients/methods-public)
- [WebSocket Market Channel](https://docs.polymarket.com/developers/CLOB/websocket/market-channel)
- [Leaderboard Endpoint](https://docs.polymarket.com/api-reference/core/get-trader-leaderboard-rankings)
- [How Are Prices Calculated?](https://help.polymarket.com/en/articles/13364488-how-are-prices-calculated)
- [Interpreting Prediction Market Prices as Probabilities (NBER)](https://www.nber.org/papers/w12200)
- [Prediction Markets (AEA)](https://www.aeaweb.org/articles?id=10.1257/0895330041371321)
- [Systematic Edges in Prediction Markets (QuantPedia)](https://quantpedia.com/tag/polymarket/)
- [prediction-market-analysis (GitHub)](https://github.com/Jon-Becker/prediction-market-analysis) — 36GiB圧縮の公開データセット
- [py-clob-client (GitHub)](https://github.com/Polymarket/py-clob-client)
- [Fed Reserve FEDS Paper 2026-010](https://www.federalreserve.gov/econres/feds/files/2026010pap.pdf)
