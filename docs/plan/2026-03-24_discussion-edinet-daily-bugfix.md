# 議論メモ: EDINET DB デイリー更新実行とバグ修正

**日付**: 2026-03-24
**議論ID**: disc-2026-03-24-edinet-daily-bugfix
**参加**: ユーザー + AI

## 背景・コンテキスト

EDINET DB のデイリー更新を実行。Free plan (100コール/日) 制約下で同期を継続中（前日時点: 47/3,839社完了）。

## 議論のサマリー

### 発見した問題

1. **`--daily` が `completed_codes` をリセット**: `run_daily()` が毎回 `completed_codes` を空にリセットするため、既に完了した47社を再処理。APIクォータ（95コール/日）を丸ごと消費し、初回同期が永遠に完了しない状態だった。
2. **レートリミッター状態の未永続化**: `DailyRateLimiter` の `flush_interval=100` に達する前にレートリミット（95コール）に達するため、`_rate_limit.json` が書き出されなかった。次回起動時にカウント0から再開。

### 実行結果

| コマンド | 結果 |
|---------|------|
| `--daily` | companies OK, financials_ratios FAIL（既存47社を再処理してクォータ消費） |
| `--resume` | +2社（49/3,839社）でAPIサーバー側レートリミット到達 |

### DB統計（修正前）

| テーブル | 行数 |
|---------|------|
| companies | 3,839 |
| financials | 706 |
| ratios | 692 |
| industries | 33 |
| industry_details | 32 |
| text_blocks | 4 |

## 決定事項

| ID | 内容 | コンテキスト |
|----|------|------------|
| dec-2026-03-24-001 | `run_daily()` は初回同期未完了時（`current_phase != complete`）に `resume()` へフォールバックする仕様に変更 | completed_codes を引き継ぎ、APIクォータの無駄消費を防止 |
| dec-2026-03-24-002 | `_run_phase()` 終了時と `sync_company()` 終了時に `rate_limiter.flush()` を呼び出す | `_rate_limit.json` が確実に書き出され、次回起動時に正しいカウントを引き継ぐ |

## 実装内容

### 変更ファイル

| ファイル | 変更内容 |
|---------|---------|
| `src/market/edinet/syncer.py` | `run_daily()` にガード条件追加、`_run_phase()` と `sync_company()` に flush() 追加 |
| `tests/market/unit/edinet/test_syncer.py` | 4テスト追加（フォールバック2件 + flush2件）、既存テスト修正 |

### テスト結果

- 全32テスト通過（既存28 + 新規4）
- `make check-all` 相当の品質チェック通過

## アクションアイテム

| ID | 内容 | 優先度 | 期限 |
|----|------|--------|------|
| act-2026-03-24-001 | EDINET DB financials_ratios を毎日 `--daily` で継続実行（49/3,839社、残り約80日） | 中 | - |
| act-2026-03-24-002 | syncer.py バグ修正のコミットとPR作成 | 高 | 2026-03-24 |

## 次回の議論トピック

- cron による自動化（NAS 上で毎日深夜に `--daily` を実行）
- Pro プラン（1,000コール/日）へのアップグレード検討（残り80日を8日に短縮可能）
- Project 70（edinet-api-alignment）Step 1-8 の着手時期

## 実行コマンド（明日以降）

```bash
source .env && uv run python -m market.edinet.scripts.sync --daily
```
