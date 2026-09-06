#!/usr/bin/env bash
#
# scheduler サービスの起動前チェック
#
# NAS が未マウントのままでも Docker はバインド元を空ディレクトリとして
# 作ってしまうため、コンテナからは「NAS があるように見えて中身が空」という
# 状態になりうる。その状態で定期ジョブを走らせるとローカルの空ディレクトリに
# 書き込み続けることになるので、起動前に実データの存在を確認して止める。
#
set -euo pipefail

CRONTAB="${QUANTS_CRONTAB:-/app/docker/crontab}"
NAS_SENTINEL="${QUANTS_NAS_SENTINEL:-/nas/Projects/quants/data}"

fail() {
  echo "[scheduler] 起動中止: $*" >&2
  exit 1
}

echo "[scheduler] 起動前チェックを開始"
echo "[scheduler] TZ=${TZ:-（未設定・UTC）}  現在時刻: $(date '+%Y-%m-%d %H:%M:%S %Z')"

# --- 1. NAS が本当にマウントされているか -------------------------------------
[ -d /nas ] || fail "/nas がマウントされていません。.env の NAS_ROOT を確認してください"
[ -d "$NAS_SENTINEL" ] \
  || fail "$NAS_SENTINEL が見つかりません。NAS_ROOT の指す先が NAS 本体か確認してください（空ディレクトリが作られている可能性があります）"

if [ -z "$(ls -A "$NAS_SENTINEL" 2>/dev/null)" ]; then
  fail "$NAS_SENTINEL が空です。NAS が未マウントの疑いがあります"
fi
echo "[scheduler] ✅ NAS を確認: $NAS_SENTINEL"

# --- 2. crontab の存在 --------------------------------------------------------
[ -f "$CRONTAB" ] || fail "crontab が見つかりません: $CRONTAB"
n_jobs=$(grep -cE '^[0-9*]' "$CRONTAB" || true)
echo "[scheduler] ✅ crontab を確認: $CRONTAB（$n_jobs ジョブ）"

# --- 3. Docker API（Neo4j バックアップジョブが docker exec を使う）------------
if docker info >/dev/null 2>&1; then
  echo "[scheduler] ✅ Docker API に接続できます"
  if docker ps --format '{{.Names}}' | grep -qx "${NEO4J_CONTAINER:-neo4j-enterprise}"; then
    echo "[scheduler] ✅ Neo4j コンテナを確認"
  else
    echo "[scheduler] ⚠️  Neo4j コンテナが見つかりません。Neo4j バックアップジョブは失敗します" >&2
  fi
else
  echo "[scheduler] ⚠️  Docker API に接続できません。Neo4j バックアップの 2 ジョブは失敗します" >&2
  echo "[scheduler]     Windows では .env に DOCKER_SOCKET=//./pipe/docker_engine が必要です" >&2
fi

# --- 4. ログ出力先 ------------------------------------------------------------
mkdir -p "$(dirname "${NEO4J_SYNC_LOG:-/app/logs/neo4j-sync.log}")"

echo "[scheduler] チェック完了。supercronic を起動します"

# 絶対パスで起動すること。supercronic は PID 1 で動くときプロセス回収のために
# 自身を再実行するが、その際 os.Args[0] を PATH 解決せずに exec するため、
# `exec supercronic ...` だと "Failed to fork exec: no such file or directory"
# で即座に落ちて再起動ループになる。
exec /usr/local/bin/supercronic -passthrough-logs "$CRONTAB"
