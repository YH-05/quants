#!/bin/bash
# quants Neo4j コンテナ自動起動スクリプト
# LaunchAgent (com.quants.neo4j.plist) から呼び出される

COMPOSE_FILE="/Users/yuki/Desktop/quants/docker-compose.yml"
LOG_FILE="/Users/yuki/Desktop/quants/logs/neo4j-autostart.log"

mkdir -p "$(dirname "$LOG_FILE")"

log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $*" >> "$LOG_FILE"
}

log "Neo4j 自動起動スクリプト開始"

# Docker が起動するまで最大 60 秒待機
for i in $(seq 1 30); do
    if /usr/local/bin/docker info >/dev/null 2>&1; then
        log "Docker 起動確認 (試行 ${i}回目)"
        break
    fi
    if [ "$i" -eq 30 ]; then
        log "ERROR: Docker が 60 秒以内に起動しなかった"
        exit 1
    fi
    sleep 2
done

# Neo4j コンテナを起動
log "docker compose up -d neo4j を実行"
/usr/local/bin/docker compose -f "$COMPOSE_FILE" up -d neo4j >> "$LOG_FILE" 2>&1
STATUS=$?

if [ $STATUS -eq 0 ]; then
    log "Neo4j 起動成功"
else
    log "ERROR: Neo4j 起動失敗 (exit code: $STATUS)"
fi

exit $STATUS
