# 議論メモ: Polymarket 初回データ収集完了・DB蓄積状況

**日付**: 2026-03-23
**議論ID**: disc-2026-03-23-polymarket-data-collection
**参加**: ユーザー + AI

## 背景・コンテキスト

2026-03-21 に market.polymarket パッケージ（PR #3818）をマージ後、PolymarketStorage + Collector を実装（PR #3831）し、Gamma/Data API互換性修正（commit 856bdb4）を経て、初回データ収集を実施した。

関連する過去の議論:
- disc-2026-03-21-polymarket-api-research: API調査・応用提案
- disc-2026-03-21-polymarket-merge: パッケージマージ完了

## DB蓄積状況

**ファイル**: `data/sqlite/polymarket.db` (578 MB)
**データ取得日**: 2026-03-23

### テーブル別レコード数

| テーブル | 行数 | 説明 |
|----------|-----:|------|
| `pm_events` | 200 | 予測イベント（Active: 200, Closed: 100） |
| `pm_markets` | 1,876 | 個別マーケット（Active: 1,202, Closed: 369） |
| `pm_tokens` | 3,745 | トークン（Yes: 1,846, No: 1,846, 他53） |
| `pm_price_history` | 2,406,199 | 価格時系列（interval=`1d` のみ、1,680トークン分） |
| `pm_trades` | 700 | 取引記録（2026-03-23 07:52〜09:22 UTC） |
| `pm_orderbook_snapshots` | 1,702 | オーダーブックスナップショット（07:54〜10:27 UTC） |
| `pm_oi_snapshots` | 0 | OIスナップショット（未収集） |
| `pm_leaderboard_snapshots` | 0 | リーダーボード（未収集） |

**合計**: 約 2,414,422 行

### 主要イベント（出来高上位）

| イベント | 出来高 | 流動性 | 状態 |
|---------|-------:|-------:|------|
| Democratic Presidential Nominee 2028 | 896M | 44.3M | Active |
| SCOTUS accepts sports event contract case | 929K | 13K | Active |
| Mike Johnson out as Speaker | 91K | 15K | Active |

### 主要マーケット（出来高上位）

| マーケット | 出来高 | 流動性 |
|-----------|-------:|-------:|
| Chris Murphy win Dem nomination? | 9.9M | 864K |
| Dallas Mavericks win 2026 NBA Finals? | 9.8M | 288K |
| Miami Heat win 2026 NBA Finals? | 9.8M | 301K |
| Devin Booker win 2025-26 NBA MVP? | 9.8M | 142K |
| Phoenix Suns win 2026 NBA Finals? | 9.8M | 641K |
| Will Claude 5 be released by March 31, 2026? | 977K | 44K |

### 所見

1. **価格履歴が圧倒的**: 240万行がDB容量（578MB）の大部分を占める
2. **日次 interval のみ**: `1d` のみ収集済み。`1h`/`6h`/`1w`/`1m` は未収集
3. **未収集テーブル**: `pm_oi_snapshots`（建玉）と `pm_leaderboard_snapshots` は0件
4. **政治・スポーツが中心**: 2028年米大統領選、NBA/NHL、EU政治が出来高上位
5. **取引・板データは短期間**: trades/orderbookは本日数時間分のみ

## 決定事項

| ID | 内容 | コンテキスト |
|----|------|------------|
| dec-2026-03-23-001 | PolymarketStorage(8テーブルSQLite) + Collector 実装完了、初回データ収集成功（578MB, 240万行） | PR #3831 + commit 856bdb4。200イベント・1,876マーケット・240万価格ポイント蓄積 |
| dec-2026-03-23-002 | 価格履歴は1d intervalのみ。OI・リーダーボードは未収集 | 段階的にinterval追加・未収集テーブルの定期収集を実装予定 |

## アクションアイテム

| ID | 内容 | 優先度 | 期限 |
|----|------|--------|------|
| act-2026-03-23-001 | pm_oi_snapshots（建玉）の定期収集を実装 | 中 | 未定 |
| act-2026-03-23-002 | pm_leaderboard_snapshots の定期収集を実装 | 低 | 未定 |
| act-2026-03-23-003 | 定期収集スケジュール（cron/launchd）をMac Miniで設定 | 中 | 未定 |
| act-2026-03-23-004 | 分析パイプラインへの統合検討（カリブレーション、スマートマネー追跡等） | 中 | 未定 |

## 次回の議論トピック

- 定期収集の頻度設計（OI: 日次？, リーダーボード: 週次？, 板: リアルタイム？）
- 他 interval（1h, 6h）の追加収集の費用対効果
- ca_strategy への予測市場確率ファクター統合（act-2026-03-21-002 の続き）
- EDINET DB定期収集と同じ Mac Mini cron パターンでの運用設計

## 参考情報

- ストレージ実装: `src/market/polymarket/storage.py`
- コレクター実装: `src/market/polymarket/collector.py`
- モデル定義: `src/market/polymarket/models.py`
- 定数定義: `src/market/polymarket/storage_constants.py`
- 関連PR: #3818 (パッケージ実装), #3831 (Storage + Collector)
- 関連commit: 856bdb4 (Gamma/Data API互換性修正)
