# 議論メモ: NASDAQ データ取得テスト

**日付**: 2026-03-25
**議論ID**: disc-2026-03-25-nasdaq-data-test

## 背景・コンテキスト

DATA_DIR 統一リファクタリング後の動作確認として、NASDAQ パッケージの ScreenerCollector と NasdaqClient の両方をテスト。

## テスト結果

### ScreenerCollector (Stock Screener API)

| テスト | 結果 |
|--------|------|
| 全銘柄取得 | 7,086 銘柄取得成功 |
| フィルタ (NASDAQ + Technology) | 605 銘柄取得成功 |
| バリデーション | True |
| 出力先パス | `/Volumes/personal_folder/Quants/data/raw/nasdaq` (DATA_DIR 反映済み) |

### NasdaqClient (個別エンドポイント)

| エンドポイント | 結果 | 備考 |
|---------------|------|------|
| Earnings Calendar | 80件 | 正常動作 |
| Short Interest (AAPL) | 25件 | 正常動作 |
| Analyst Ratings (AAPL) | 空 | レートリミット or 時間帯の問題 |
| Target Price (AAPL) | 空 | 同上 |
| Market Movers | 空 | 市場時間外のため期待通り |
| ETF Screener | 空 | レートリミットの可能性 |
| Earnings Forecast (AAPL) | JSONDecodeError | API が空 body を返却 |

## 決定事項

| ID | 内容 | コンテキスト |
|----|------|------------|
| dec-2026-03-25-004 | ScreenerCollector は本番利用可能。NasdaqClient の Earnings Calendar・Short Interest も安定動作。Analyst系はレートリミット耐性の改善が必要 | DATA_DIR 統一リファクタリング後の動作確認 |

## アクションアイテム

| ID | 内容 | 優先度 | ステータス |
|----|------|--------|-----------|
| act-2026-03-25-001 | NasdaqClient._fetch_and_parse() で空レスポンス時の JSONDecodeError をキャッチし、空結果を返すよう改善 | 中 | pending |

## 次回の議論トピック

- Analyst 系エンドポイントのレートリミット対策（リトライ間隔の調整）
- Market Movers の市場時間内テスト
- CSV ダウンロード機能 (`download_by_category`) の DATA_DIR 反映テスト
