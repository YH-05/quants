# 議論メモ: EDINET DB sync 429エラー修正

**日付**: 2026-03-18
**議論ID**: disc-2026-03-18-edinet-sync-fix
**参加**: ユーザー + AI

## 背景・コンテキスト

`uv run python -m market.edinet.scripts.sync --resume` が `company_details` フェーズで `[FAIL]` となり、エラー詳細も表示されない問題が発生。

## 調査の流れ

1. **初期調査**: DEBUG ログでも詳細が出ず、直接 Python で例外を捕捉 → `EdinetRateLimitError: API rate limit exceeded: HTTP 429`
2. **仮説1 (一時的429)**: 429 をリトライ対象に変更（5xx と同様のバックオフ） → リトライしても 429 が継続
3. **仮説2 (バックオフ不足)**: `_RATE_LIMIT_MIN_BACKOFF = 30s` を導入 → 30秒×2回待っても 429
4. **根本原因特定**: API レスポンスヘッダーを直接確認
   - `x-ratelimit-limit: 100` (Free プラン)
   - `x-ratelimit-remaining: 0`
   - `x-ratelimit-reset: 2026-03-18`
   - コードは `DAILY_RATE_LIMIT=1000` (Pro プラン前提) だった

## 修正内容

| ファイル | 変更内容 |
|---------|---------|
| `src/market/edinet/constants.py` | `DAILY_RATE_LIMIT`: 1000→100, `SAFE_MARGIN`: 50→5 |
| `src/market/edinet/client.py` | 429 で API ヘッダー (`x-ratelimit-*`) を読み取り、リセット日時付き `EdinetRateLimitError` を即座に発生（リトライ不要） |
| `src/market/edinet/errors.py` | `EdinetRateLimitError` に `reset_date` フィールド追加 |
| `src/market/edinet/syncer.py` | rate limit 停止時にリセット日時を `errors` と `stopped_reason` に含める |
| `src/market/edinet/scripts/sync.py` | `--resume` で `errors` と `stopped_reason` を表示 |
| `tests/market/unit/edinet/test_constants.py` | 定数値テスト更新 |
| `tests/market/unit/edinet/test_rate_limiter.py` | 定数値テスト更新 |

## 決定事項

| ID | 内容 | コンテキスト |
|----|------|------------|
| dec-2026-03-18-001 | DAILY_RATE_LIMIT を 1000→100、SAFE_MARGIN を 50→5 に修正 | API ヘッダー `x-ratelimit-limit: 100` で Free プラン確認 |
| dec-2026-03-18-002 | HTTP 429 は即座に EdinetRateLimitError（リトライしない）。ヘッダーからリセット情報取得 | 日次上限はリトライしても無駄 |
| dec-2026-03-18-003 | 全データ同期: Free プラン 約200日、Pro プラン 約20日 | Phase 4: 40日, Phase 5: 81日, Phase 6: 81日 |

## DB 保存状況 (2026-03-18 時点)

| テーブル | 行数 | フェーズ | 状態 |
|---------|------|---------|------|
| companies | 3,838 | Phase 1 | 完了 |
| industries | 33 | Phase 2 | 完了 |
| industry_details | 32 | Phase 2 | 完了 |
| rankings | 2,000 | Phase 3 | 完了 (20メトリック×100社) |
| financials | 14 | Phase 5 | 未到達 (1社分のみ) |
| ratios | 14 | Phase 5 | 未到達 (1社分のみ) |
| analyses | 1 | Phase 6 | 未到達 |
| text_blocks | 4 | Phase 6 | 未到達 |

**現在地**: Phase 4 (`company_details`) — 11/3,838社 処理済み

## アクションアイテム

| ID | 内容 | 優先度 | 状態 |
|----|------|--------|------|
| act-2026-03-18-001 | EDINET DB Pro プランへのアップグレード検討 | medium | pending |
| act-2026-03-18-002 | 深夜0時(JST)リセット後に `--resume` で継続実行 | high | pending |

## EDINET DB API プラン比較

| プラン | 日次上限 | 月次上限 | 全同期所要日数 |
|--------|---------|---------|--------------|
| Free | 100 | 3,000 | 約200日 |
| Pro | 1,000 | 30,000 | 約20日 |
| Business | 10,000 | ? | 約2日 |

## 次回の議論トピック

- Pro プランのコスト対効果
- 同期の優先順位付け（全社ではなく必要な銘柄のみ先に同期するオプション）
- cron による自動日次 resume 実行の検討
