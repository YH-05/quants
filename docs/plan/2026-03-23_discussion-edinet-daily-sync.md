# 議論メモ: EDINET DBデイリー更新の実行と課題

**日付**: 2026-03-23
**議論ID**: disc-2026-03-23-edinet-daily-sync
**参加**: ユーザー + AI

## 背景・コンテキスト

EDINET DBのデイリー更新を実行。Free plan (100コール/日) の制約下での同期進捗を確認した。

## 実行結果

### コマンド

```bash
source .env && uv run python -m market.edinet.scripts.sync --daily
```

### Phase 結果

| Phase | 結果 | 詳細 |
|-------|------|------|
| companies | OK | 3,839社取得 |
| financials_ratios | 途中停止 | 47/3,839社完了（レートリミット） |
| text_blocks | 未実行 | - |

### DB統計

| テーブル | 行数 |
|---------|------|
| companies | 3,839 |
| financials | 706 |
| ratios | 692 |
| industries | 33 |
| text_blocks | 4 |

### データ保存先

- **実際の保存先**: `/Volumes/personal_folder/Quants/data/sqlite/edinet.db` (NAS)
- `.env` の `DATA_DIR=/Volumes/personal_folder/Quants/data` により解決
- ローカル `data/sqlite/edinet.db` は古いコピー

## 課題

- Free plan (100コール/日, SAFE_MARGIN=5で実質95コール) のため、financials_ratios フェーズは1日約47社ずつ進行
- 全3,839社の完了に約81日必要
- `_rate_limit.json` は flush_interval=100 に達せず未書き出し（同一プロセス内ではカウント正常）

## アクションアイテム

| ID | 内容 | 優先度 | 期限 |
|----|------|--------|------|
| act-2026-03-23-001 | EDINET DB financials_ratios フェーズを --resume で継続実行（毎日約47社ずつ進行） | 中 | - |

## 次回の議論トピック

- 上位プラン (Pro: 1,000コール/日) へのアップグレード検討
- 複数APIキーによるローテーション運用の可否
- デイリー更新の自動化（cron等）
