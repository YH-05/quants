#!/usr/bin/env bash
# NAS設定ファイル同期スクリプト
# 対象: .env, .mcp.json, .claude/settings.json, data/config/
#
# 使用方法:
#   bash scripts/sync_nas.sh --push   # ローカル → NAS
#   bash scripts/sync_nas.sh --pull   # NAS → ローカル

set -euo pipefail

# --- 設定 ---
NAS_MOUNT="/Volumes/personal_folder"
NAS_SYNC_DIR="${NAS_MOUNT}/Projects/quants"
PROJECT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
LOG_PREFIX="[sync-nas]"

# 同期対象ファイル・ディレクトリ
SYNC_FILES=(
    ".env"
    ".mcp.json"
    ".claude/settings.json"
)
SYNC_DIRS=(
    "data/config"
)

# --- 関数 ---
log() {
    echo "${LOG_PREFIX} $*"
}

check_nas() {
    if [[ ! -d "${NAS_MOUNT}" ]]; then
        log "ERROR: NASがマウントされていません: ${NAS_MOUNT}"
        return 1
    fi
    if [[ ! -d "${NAS_SYNC_DIR}" ]]; then
        log "同期ディレクトリを作成: ${NAS_SYNC_DIR}"
        mkdir -p "${NAS_SYNC_DIR}"
    fi
}

push() {
    log "=== PUSH: ローカル → NAS ==="

    # ファイル同期
    for f in "${SYNC_FILES[@]}"; do
        local src="${PROJECT_DIR}/${f}"
        local dst="${NAS_SYNC_DIR}/$(dirname "${f}")"
        if [[ -f "${src}" ]]; then
            mkdir -p "${dst}"
            rsync -av --checksum "${src}" "${dst}/" && log "  ✓ ${f}"
        else
            log "  - スキップ（存在しない）: ${f}"
        fi
    done

    # ディレクトリ同期
    for d in "${SYNC_DIRS[@]}"; do
        local src="${PROJECT_DIR}/${d}/"
        local dst="${NAS_SYNC_DIR}/${d}/"
        if [[ -d "${PROJECT_DIR}/${d}" ]]; then
            mkdir -p "${dst}"
            rsync -av --checksum --delete "${src}" "${dst}" && log "  ✓ ${d}/"
        else
            log "  - スキップ（存在しない）: ${d}/"
        fi
    done

    # タイムスタンプ記録
    date -u +"%Y-%m-%dT%H:%M:%SZ" > "${NAS_SYNC_DIR}/.last_push"
    log "完了: $(cat "${NAS_SYNC_DIR}/.last_push")"
}

pull() {
    log "=== PULL: NAS → ローカル ==="

    if [[ -f "${NAS_SYNC_DIR}/.last_push" ]]; then
        log "最終PUSH: $(cat "${NAS_SYNC_DIR}/.last_push")"
    fi

    # ファイル同期
    for f in "${SYNC_FILES[@]}"; do
        local src="${NAS_SYNC_DIR}/${f}"
        local dst="${PROJECT_DIR}/$(dirname "${f}")"
        if [[ -f "${src}" ]]; then
            mkdir -p "${dst}"
            rsync -av --checksum "${src}" "${dst}/" && log "  ✓ ${f}"
        else
            log "  - スキップ（NASに存在しない）: ${f}"
        fi
    done

    # ディレクトリ同期
    for d in "${SYNC_DIRS[@]}"; do
        local src="${NAS_SYNC_DIR}/${d}/"
        local dst="${PROJECT_DIR}/${d}/"
        if [[ -d "${NAS_SYNC_DIR}/${d}" ]]; then
            mkdir -p "${dst}"
            rsync -av --checksum --delete "${src}" "${dst}" && log "  ✓ ${d}/"
        else
            log "  - スキップ（NASに存在しない）: ${d}/"
        fi
    done

    log "完了"
}

# --- メイン ---
MODE="${1:-}"
case "${MODE}" in
    --push)
        check_nas && push
        ;;
    --pull)
        check_nas && pull
        ;;
    *)
        echo "使用方法: $0 --push | --pull"
        echo "  --push  ローカル → NAS（SessionEnd時に自動実行）"
        echo "  --pull  NAS → ローカル（他PCから設定を取得）"
        exit 1
        ;;
esac
