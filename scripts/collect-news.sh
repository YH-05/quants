#!/bin/bash
# finance-news-workflow 定期実行スクリプト
#
# Usage:
#   ./scripts/collect-news.sh              # デフォルト設定で実行
#   ./scripts/collect-news.sh --days 3     # 過去3日分を対象
#   ./scripts/collect-news.sh --dry-run    # ドライラン
#
# Cron example (毎日朝7時に実行):
#   0 7 * * * /path/to/finance/scripts/collect-news.sh >> /var/log/finance-news.log 2>&1
#
# Launchd example (macOS):
#   See scripts/com.finance.news-collector.plist

set -euo pipefail

# スクリプトのディレクトリからプロジェクトルートを取得
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

# プロジェクトルートに移動
cd "$PROJECT_ROOT"

# ログ出力
echo "[$(date '+%Y-%m-%d %H:%M:%S')] Starting finance news collection..."
echo "[$(date '+%Y-%m-%d %H:%M:%S')] Project root: $PROJECT_ROOT"

# 実行
if command -v uv &> /dev/null; then
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] Using uv..."
    uv run python -m automation.news_collector "$@"
else
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] Using python directly..."
    python -m automation.news_collector "$@"
fi

EXIT_CODE=$?

if [ $EXIT_CODE -eq 0 ]; then
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] News collection completed successfully."
else
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] News collection failed with exit code: $EXIT_CODE"
fi

exit $EXIT_CODE
