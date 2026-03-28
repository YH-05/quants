# 議論メモ: EDINET launchd 自動化 & NASパス移行

**日付**: 2026-03-28
**議論ID**: disc-2026-03-28-edinet-launchd-nas-migration
**参加**: ユーザー + AI

## 背景・コンテキスト

前回（2026-03-24）の課題:
- EDINET DB 初期同期が49/3,839社で継続中
- cron/launchd による自動化が未完了
- NASパスが `/Volumes/personal_folder/Quants/data` のまま（旧パス）

## 実施内容

### 1. EDINET daily sync 実行（`--resume`）

| 項目 | 実行前 | 実行後 |
|------|--------|--------|
| 完了社数 | 49社 | 96社 (+47社) |
| API コール | 550 | 645 (上限到達) |
| financials | 706行 | 1,366行 (+660) |
| ratios | 692行 | 1,352行 (+660) |
| 残APIコール | 95 | 0 |

### 2. launchd による自動実行設定

| 設定項目 | 値 |
|---------|-----|
| plist | `~/Library/LaunchAgents/com.quants.edinet-sync.plist` |
| Label | `com.quants.edinet-sync` |
| コマンド | `uv run python -m market.edinet.scripts.sync --daily` |
| 実行時刻 | 毎日 8:00 |
| ログ (stdout) | `/Volumes/personal_folder/Projects/quants/data/logs/edinet-sync.log` |
| ログ (stderr) | `/Volumes/personal_folder/Projects/quants/data/logs/edinet-sync-error.log` |

`run_daily()` は初期同期未完了時に自動で `resume()` にフォールバックする仕様のため、`--daily` のみで初期同期継続とデイリー更新の両方に対応。

### 3. NASパス移行

| 項目 | 旧パス | 新パス |
|------|--------|--------|
| データルート | `/Volumes/personal_folder/Quants/data/` | `/Volumes/personal_folder/Projects/quants/data/` |
| データサイズ | 861MB | 861MB (rsync 転送済み) |

**更新ファイル:**

| ファイル | 変更内容 |
|---------|---------|
| `.env` | `DATA_DIR`, `FRED_HISTORICAL_CACHE_DIR` を新パスに更新 |
| `~/Library/LaunchAgents/com.quants.edinet-sync.plist` | ログパスを新パスに更新 |

## 決定事項

| ID | 内容 | コンテキスト |
|----|------|------------|
| dec-2026-03-28-001 | launchd で毎日 8:00 に EDINET daily sync を自動実行 | 手動実行の手間を排除。初期同期完了後もデイリー更新として継続動作 |
| dec-2026-03-28-002 | quants データ保存先を `/Volumes/personal_folder/Projects/quants/data` に統一 | `personal_folder` 直下の `Quants/` から `Projects/quants/` に整理 |

## アクションアイテム

| ID | 内容 | 優先度 | 期限 |
|----|------|--------|------|
| act-2026-03-28-001 | 旧 `/Volumes/personal_folder/Quants/` を確認後に削除（`rm -rf`） | 低 | 随時 |
| act-2026-03-28-002 | EDINET 初期同期の継続（96/3,839社、毎日 8:00 自動実行で進行中） | 中 | 完了まで自動 |

## 現在の同期状況

- **完了**: 96/3,839社（financials_ratios フェーズ）
- **残り**: 約3,743社
- **1日あたりの進捗**: ~47社（645コール/日上限）
- **完了見込み**: 約80日後（自動実行継続中）

## 次回の議論トピック

- Pro プラン（1,000コール/日）へのアップグレード検討（残り80日を約50日に短縮可能）
- 複数 API キー（`.env` に3キーあり）のローテーション検討
- Project 70（edinet-api-alignment）Step 1-8 の着手時期
