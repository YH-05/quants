# 議論メモ: Polymarket 定期データ収集の構築

**日付**: 2026-03-28
**議論ID**: disc-2026-03-28-polymarket-periodic-collection
**参加**: ユーザー + AI

## 背景・コンテキスト

- `src/market/polymarket/` にClient/Storage/Collectorは実装済み（8テーブル、SQLite）
- しかしCLIエントリポイント（`__main__.py`）が存在せず、定期実行の仕組みもなかった
- Polymarket APIは認証不要で読み取り可能、レート制限も余裕あり（CLOB 1,500 req/10s）

## Polymarket API 調査結果

### 利用可能なAPI

| API | ベースURL | 認証 |
|-----|----------|------|
| CLOB API | `https://clob.polymarket.com` | 不要（読み取り） |
| Gamma API | `https://gamma-api.polymarket.com` | 不要 |
| Data API | `https://data-api.polymarket.com` | 不要 |
| WebSocket | `wss://ws-subscriptions-clob.polymarket.com` | 不要 |

### 日時蓄積に適したデータ

| 優先度 | データ | 蓄積理由 |
|--------|--------|---------|
| 高 | 価格時系列 | API提供の過去データはfidelity依存で粒度が落ちる |
| 高 | OIスナップショット | 過去データ取得不可 |
| 高 | オーダーブック | 過去データ取得不可 |
| 高 | ライブボリューム | 過去データ取得不可 |
| 中 | 取引履歴 | 遡及可能だがページネーション制限あり |
| 中 | リーダーボード | ランキング変動の記録 |

## 実施内容

### 1. CLIエントリポイント作成

**ファイル**: `src/market/polymarket/__main__.py`

| コマンド | 動作 |
|---------|------|
| `uv run python -m market.polymarket` | フル収集（active events, 100件） |
| `uv run python -m market.polymarket --status` | DB統計表示 |
| `uv run python -m market.polymarket --event-limit 50` | イベント数指定 |
| `uv run python -m market.polymarket --all-events` | closed含む全イベント |

### 2. launchd 定期実行設定

**ファイル**: `~/Library/LaunchAgents/com.quants.polymarket-collect.plist`

| 設定項目 | 値 |
|---------|-----|
| Label | `com.quants.polymarket-collect` |
| コマンド | `uv run python -m market.polymarket` |
| 実行時刻 | 毎日 0:30, 6:30, 12:30, 18:30（6時間間隔） |
| ログ (stdout) | `/Volumes/personal_folder/Projects/quants/data/logs/polymarket-collect.log` |
| ログ (stderr) | `/Volumes/personal_folder/Projects/quants/data/logs/polymarket-collect-error.log` |

## 決定事項

| ID | 内容 | コンテキスト |
|----|------|------------|
| dec-2026-03-28-003 | Polymarket定期収集をCLI + launchdで構築 | 既存のCollector実装を活用。EDINET同様のパターン |
| dec-2026-03-28-004 | 収集スケジュールは6時間ごと（0:30, 6:30, 12:30, 18:30） | OI/オーダーブック等のスナップショットデータは過去取得不可のため定期ポーリングが必要 |

## アクションアイテム

| ID | 内容 | 優先度 | 期限 | 状態 |
|----|------|--------|------|------|
| act-2026-03-28-003 | `launchctl load` でplistを有効化する | 高 | 2026-03-28 | **完了** |
| act-2026-03-28-004 | NAS上SQLiteアクセス遅延の調査（NFS/SMBロック問題の可能性） | 中 | 随時 | 未着手 |
| act-2026-03-28-005 | 初回手動収集を実行し、データ蓄積を確認する | 高 | 2026-03-28 | 不要（既存データあり） |

## 動作確認結果

- `--status`: 正常動作（ローカルDB / NAS DB 両方）
- `--help`: 正常動作
- plist構文検証: `plutil -lint` OK
- NAS上のDB（`/Volumes/personal_folder/Projects/quants/data/sqlite/polymarket.db`）へのアクセスは遅延あるが動作は正常

### NAS上の既存データ（2026-03-28時点）

| テーブル | レコード数 |
|---------|-----------|
| pm_events | 200 |
| pm_markets | 1,876 |
| pm_tokens | 3,745 |
| pm_price_history | 2,406,199 |
| pm_trades | 700 |
| pm_orderbook_snapshots | 1,702 |
| pm_oi_snapshots | 0 |
| pm_leaderboard_snapshots | 0 |

### launchd 有効化（2026-03-28 完了）

```
$ launchctl load ~/Library/LaunchAgents/com.quants.polymarket-collect.plist
$ launchctl list | grep quants
-  0  com.quants.edinet-sync
-  0  com.quants.polymarket-collect
```

両エージェントがロード済み。Polymarket定期収集は次回 18:30 から自動実行開始。

## 現在の launchd エージェント一覧

| ラベル | スケジュール | 状態 |
|--------|------------|------|
| `com.quants.edinet-sync` | 毎日 8:00 | ロード済み |
| `com.quants.polymarket-collect` | 0:30, 6:30, 12:30, 18:30 | ロード済み |

## 次回の議論トピック

- NAS上SQLiteのパフォーマンス問題（ローカルDBへの切り替え検討）
- WebSocket によるリアルタイム蓄積の検討（より高頻度なデータ取得）
- 蓄積データの分析・可視化パイプライン
- OI / リーダーボードが0件の原因調査（APIエンドポイント変更の可能性）
