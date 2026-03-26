# 議論メモ: NASDAQ API パーサー修正 + 全データ取得

**日付**: 2026-03-25
**議論ID**: disc-2026-03-25-nasdaq-parser-fix

## 背景・コンテキスト

NASDAQ データ取得テストで一部エンドポイントが空データを返す問題を調査。原因はレートリミットではなく、NASDAQ API のレスポンス構造変更とパラメータ仕様変更だった。

## 修正内容

### パーサー構造変更対応 (client_parsers.py)

| パーサー | 旧構造 | 新構造 |
|----------|--------|--------|
| `parse_target_price` | `data.targetPrice.high` (文字列) | `data.consensusOverview.highPriceTarget` (数値) |
| `parse_market_movers` | `data.MostAdvanced.rows` | `data.STOCKS.MostAdvanced.table.rows` |
| `parse_etf_screener` | `data.table.rows` | `data.records.data.rows` |
| `parse_analyst_ratings` | `data.ratings` (リスト) | `data.meanRatingType` + `data.ratingsSummary` |
| `_parse_financial_table_rows` | `headers.values` (リスト) | `headers.value1, value2, ...` (dict) |

### API パラメータ修正 (client.py)

| エンドポイント | 修正 |
|---------------|------|
| `get_dividend_history` | `params={"assetclass": "stocks"}` 追加 |
| `get_financials` | `frequency` を数値マッピング (`annual→1`, `quarterly→2`) |
| `get_etf_screener` | `limit=0` → `limit=99999` |

### エラーハンドリング (client.py)

- `_fetch_and_parse` で空レスポンスボディ (HTTP 404等) のチェック追加
- `AnalystRatings` に `mean_rating`, `summary` フィールド追加

## 決定事項

| ID | 内容 | コンテキスト |
|----|------|------------|
| dec-2026-03-25-005 | 新旧両方のレスポンス構造をサポート、新構造優先+旧構造フォールバック | API変更は予告なく行われるため後方互換性維持が必要 |
| dec-2026-03-25-006 | frequency=1/2, assetclass=stocks, limit=99999 に修正 | 実際のHTTPレスポンス調査で特定 |
| dec-2026-03-25-007 | リクエスト間隔を1.5〜2.0秒に設定 | 0.8秒では47銘柄目以降でレートリミット |

## データ取得結果

### 保存先: `/Volumes/personal_folder/Quants/data/raw/nasdaq/`

| カテゴリ | ファイル数 | サイズ |
|---------|-----------|--------|
| Screener CSV (全銘柄/Exchange/Sector) | 15 | 2.1MB |
| カレンダー系 JSON (earnings/dividends/splits/ipo) | 4 | 40KB |
| マーケット全体 JSON (movers/etf) | 2 | 19KB |
| 個別銘柄 JSON (50銘柄×9種) | 10 | 1.7MB |
| **合計** | **31** | **約3.5MB** |

### 個別銘柄エンドポイント取得率

| エンドポイント | 取得成功 | 備考 |
|---------------|---------|------|
| financials (annual/quarterly) | 50/50 | 修正後100% |
| dividend_history | 50/50 | 修正後100% (配当なし銘柄は0件) |
| short_interest | 16/50 | NASDAQ上場銘柄のみ対応 |
| analyst_ratings | 50/50 | 新フォーマット (meanRatingType) |
| target_price | 50/50 | 新フォーマット (consensusOverview) |
| earnings_date | 50/50 | 正常 |
| insider_trades | 46/50 | 一部レートリミット |
| institutional_holdings | 46/50 | 一部レートリミット |

## アクションアイテム

| ID | 内容 | 優先度 | ステータス |
|----|------|--------|-----------|
| act-2026-03-25-001 | 空レスポンス時のJSONDecodeErrorハンドリング | 中 | **完了** |
| act-2026-03-25-002 | ETF Screenerのページネーション実装 (全4,405件取得) | 低 | pending |

## 次回の議論トピック

- insider_trades / institutional_holdings パーサーの構造変更対応確認
- 定期データ収集の自動化 (cron / scheduler)
- データの DuckDB 格納パイプライン
