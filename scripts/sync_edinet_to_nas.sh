#!/bin/bash
# scripts/sync_edinet_to_nas.sh
# edinet ローカル DB を NAS にマージするための Aqua-session 用ラッパー.
#
# 用途
# ----
# launchd 経路では macOS TCC によりNAS書き込みが拒否されるため、本スクリプトは
# GUI/Terminal セッションから実行することで TCC 許可を継承して NAS へ反映する。
#
# 使い方
# ------
#   $ bash scripts/sync_edinet_to_nas.sh
#   $ bash scripts/sync_edinet_to_nas.sh --dry-run
#
# 推奨運用
# --------
# - 週次など定期的に手動で実行（cron は launchd と同様に TCC 制約あり）
# - もしくは Login Items に登録（Aqua-session 起動時に1回マージ）
# - もしくは Calendar.app の Run Script アクションで定期実行
#
# ログ
# ----
#   ~/Library/Logs/quants/edinet-nas-merge.log
#
# 参照
# ----
# - docs/plan/2026-05-27_discussion-edinet-launchd-nas-failure.md
# - scripts/edinet_merge_to_nas.py
# - act-2026-05-27-003

set -uo pipefail

SCRIPT_DIR=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" &>/dev/null && pwd)
REPO_ROOT=$(cd -- "${SCRIPT_DIR}/.." &>/dev/null && pwd)
# ~/Library/Logs は macOS 固有。3OS で動かすため上書き可能にする
LOG_DIR="${QUANTS_LOG_DIR:-${HOME}/Library/Logs/quants}"
LOG_FILE="${LOG_DIR}/edinet-nas-merge.log"
# コンテナ内では NAS_ROOT=/nas が注入される。未設定なら macOS の既定値
MOUNT_POINT="${NAS_ROOT:-/Volumes/personal_folder}"

mkdir -p "${LOG_DIR}"

log() {
  echo "$(date '+%Y-%m-%d %H:%M:%S') $*" | tee -a "${LOG_FILE}"
}

log "=== edinet NAS merge: started ==="
log "repo_root=${REPO_ROOT}"

# 1. NAS マウント確認
if ! mount | grep -q " on ${MOUNT_POINT} "; then
  log "ERROR: NAS not mounted at ${MOUNT_POINT}"
  log "Open Finder > Network and mount '${MOUNT_POINT##*/}', then re-run."
  exit 2
fi

# 2. NAS 書き込み可能性チェック（TCC 許可済みか）
TEST_FILE="${MOUNT_POINT}/.edinet-merge-write-test"
if ! touch "${TEST_FILE}" 2>/dev/null; then
  log "ERROR: NAS not writable from this session (TCC permission missing)"
  log "Hint: System Settings > Privacy & Security > Files & Folders / Network Volumes"
  exit 3
fi
rm -f "${TEST_FILE}"

# 3. uv 経由で Python マージスクリプトを実行
cd "${REPO_ROOT}"
log "running edinet_merge_to_nas.py $*"

# uv は PATH から解決する（ユーザー名のハードコードを排除）
if "${UV_BIN:-uv}" run --no-sync python scripts/edinet_merge_to_nas.py "$@" 2>&1 | tee -a "${LOG_FILE}"; then
  log "=== edinet NAS merge: SUCCESS ==="
  exit 0
else
  rc=${PIPESTATUS[0]}
  log "=== edinet NAS merge: FAILED rc=${rc} ==="
  exit "${rc}"
fi
