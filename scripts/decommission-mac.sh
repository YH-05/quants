#!/usr/bin/env bash
#
# decommission-mac.sh - quants の開発環境をこの Mac から撤去する
#
# 使い方:
#   bash scripts/decommission-mac.sh            # dry-run（既定・何も削除しない）
#   bash scripts/decommission-mac.sh --execute  # 実際に削除する
#
# 前提:
#   docs/MIGRATION.md §7 のチェックリストが新PCで全て通っていること。
#
# 触らないもの:
#   - ~/neo4j-data/            4 DB 共有のため（note-finance が使用中）
#   - com.note-finance.*       他プロジェクトの launchd ジョブ
#   - ~/Desktop/Quants_data/   27GB の FNSPID データセット（判断保留）
#   - NAS 上の一切のデータ
#
set -euo pipefail

BACKUP_DIR="${QUANTS_BACKUP_DIR:-/Volumes/personal_folder/quants-migration-2026-09-05}"
REPO_DIR="${QUANTS_REPO_DIR:-$HOME/Desktop/quants}"
ORPHAN_WORKTREE="$HOME/Desktop/.worktrees/Quants"
NEO4J_STARTER="$HOME/.local/bin/start-quants-neo4j.sh"
NEO4J_CONTAINER="${NEO4J_CONTAINER:-neo4j-enterprise}"
LAUNCH_AGENTS="$HOME/Library/LaunchAgents"

EXECUTE=false
[ "${1:-}" = "--execute" ] && EXECUTE=true

# ---------------------------------------------------------------------------
# このスクリプトはこれから削除するリポジトリの中にある。
# bash はスクリプトを逐次読み込むため、実行中に自身が消えると壊れる。
# 削除モードのときは /tmp に複製して、そちらから実行し直す。
# ---------------------------------------------------------------------------
SELF="$(cd -P "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)/$(basename "${BASH_SOURCE[0]}")"
REPO_DIR_PHYS="$(cd -P "$REPO_DIR" 2>/dev/null && pwd -P || echo "$REPO_DIR")"
if $EXECUTE && [ -z "${QUANTS_DECOMMISSION_RELAUNCHED:-}" ] && [[ "$SELF" == "$REPO_DIR_PHYS"/* ]]; then
  # mktemp -t で作られるのは拡張子なしのパスなので、ディレクトリ単位で確保して
  # その中に固定名で置く（mktemp のアトミック性を活かすため）
  TMP_SELF="$(mktemp -d)/decommission-mac.sh"
  cp "$SELF" "$TMP_SELF"
  echo "リポジトリ外へ退避して実行し直します: $TMP_SELF"
  QUANTS_DECOMMISSION_RELAUNCHED=1 exec bash "$TMP_SELF" --execute
fi

red()   { printf '\033[31m%s\033[0m\n' "$*"; }
green() { printf '\033[32m%s\033[0m\n' "$*"; }
bold()  { printf '\033[1m%s\033[0m\n' "$*"; }

step() {
  if $EXECUTE; then bold "▶ $*"; else echo "  [dry-run] $*"; fi
}

die() { red "中断: $*"; exit 1; }

echo "============================================================"
if $EXECUTE; then
  bold "quants 撤去スクリプト  [実行モード]"
else
  bold "quants 撤去スクリプト  [dry-run — 何も削除しません]"
  echo "実際に削除するには: bash $(basename "$0") --execute"
fi
echo "============================================================"
echo

# ---------------------------------------------------------------------------
# 事前検証: 削除対象パスの身元確認
#
# REPO_DIR は QUANTS_REPO_DIR で上書きできる。誤って $HOME や $HOME/Desktop を
# 指定すると rm -rf がそれらを消してしまうため、削除に進む前に身元を検証する。
# ${VAR:?} は「空」しか弾けず、「値はあるが想定外のパス」は防げない。
# ---------------------------------------------------------------------------
case "$REPO_DIR" in
  "" | "/" | "$HOME" | "$HOME/" | "$HOME/Desktop" | "$HOME/Desktop/")
    die "REPO_DIR の指定が広すぎます: '$REPO_DIR'" ;;
esac
[ "$(basename "$REPO_DIR")" = "quants" ] \
  || die "REPO_DIR の末尾が 'quants' ではありません: '$REPO_DIR'"
if [ -d "$REPO_DIR" ] && [ ! -d "$REPO_DIR/.git" ]; then
  die "REPO_DIR が git リポジトリではありません: '$REPO_DIR'"
fi

# ---------------------------------------------------------------------------
# 0. 事前検証: NAS のバックアップが揃っているか
# ---------------------------------------------------------------------------
bold "[0/6] バックアップの検証"

[ -d "$BACKUP_DIR" ] || die "バックアップが見つかりません: $BACKUP_DIR（NAS はマウントされていますか）"

REQUIRED=(
  "repo-untracked/market_data.db"
  "repo-untracked/.env"
  "repo-untracked/.mcp.json"
  "repo-untracked/data-sqlite/edinet.db"
  "neo4j/quants.dump"
  "scripts/start-quants-neo4j.sh"
)
missing=0
for f in "${REQUIRED[@]}"; do
  if [ -f "$BACKUP_DIR/$f" ]; then
    printf '  ✅ %s\n' "$f"
  else
    printf '  ❌ %s が無い\n' "$f"; missing=$((missing + 1))
  fi
done
# find はディレクトリが無いと非ゼロ終了する。pipefail 下では代入ごと失敗して
# 下の「不足」分岐に到達できなくなるため || true で吸収する
n_plist=$(find "$BACKUP_DIR/launchd" -name 'com.quants.*.plist' 2>/dev/null | wc -l | tr -d ' ' || true)
if [ "$n_plist" -ge 13 ]; then
  printf '  ✅ launchd plist %s 件\n' "$n_plist"
else
  printf '  ❌ launchd plist が %s 件しかない（13 件必要）\n' "$n_plist"; missing=$((missing + 1))
fi

[ "$missing" -eq 0 ] || die "バックアップが $missing 件不足しています。撤去を中止しました。"
green "  バックアップは揃っています"
echo

# ---------------------------------------------------------------------------
# 1. 未 push のコミットが無いか最終確認
# ---------------------------------------------------------------------------
bold "[1/6] Git の最終確認"
if [ -d "$REPO_DIR/.git" ]; then
  # grep は 0 件マッチで非ゼロ終了する。pipefail 下ではリポジトリがクリーンな
  # ときほど代入が失敗し、この関門を通す前に無言終了してしまうため || true で吸収する
  unpushed=$(git -C "$REPO_DIR" log --branches --not --remotes --oneline 2>/dev/null | wc -l | tr -d ' ' || true)
  dirty=$(git -C "$REPO_DIR" status --porcelain 2>/dev/null | grep -vc '^??' || true)
  stash=$(git -C "$REPO_DIR" stash list 2>/dev/null | wc -l | tr -d ' ' || true)
  printf '  未 push コミット: %s / 未コミット変更: %s / stash: %s\n' "$unpushed" "$dirty" "$stash"
  if [ "$unpushed" != "0" ] || [ "$dirty" != "0" ] || [ "$stash" != "0" ]; then
    die "GitHub に反映されていない作業があります。push してから再実行してください。"
  fi
  green "  全ての作業が GitHub に反映されています"
else
  echo "  リポジトリは既にありません（スキップ）"
fi
echo

# ---------------------------------------------------------------------------
# 2. launchd ジョブの停止と削除（com.quants.* のみ）
# ---------------------------------------------------------------------------
bold "[2/6] launchd ジョブの停止と削除"
found=0
for p in "$LAUNCH_AGENTS"/com.quants.*.plist; do
  [ -e "$p" ] || continue
  found=$((found + 1))
  label="$(basename "$p" .plist)"
  step "unload + 削除: $label"
  if $EXECUTE; then
    if launchctl bootout "gui/$(id -u)/$label" 2>/dev/null \
      || launchctl unload "$p" 2>/dev/null; then
      :
    else
      red "  警告: $label の unload に失敗。plist は削除しますが、"
      red "        ジョブが再起動まで残る可能性があります。"
    fi
    rm -f "$p"
  fi
done
[ "$found" -eq 0 ] && echo "  対象なし（既に削除済み）"
echo "  ※ com.note-finance.* は対象外（他プロジェクトのため残します）"
echo

# ---------------------------------------------------------------------------
# 3. Neo4j の quants データベースのみ削除
# ---------------------------------------------------------------------------
bold "[3/6] Neo4j の quants データベース削除"
if docker info >/dev/null 2>&1 && docker ps --format '{{.Names}}' | grep -qx "$NEO4J_CONTAINER"; then
  # .env が消える前にパスワードを読む
  PW="${NEO4J_PASSWORD:-}"
  if [ -z "$PW" ] && [ -f "$BACKUP_DIR/repo-untracked/.env" ]; then
    PW=$(grep -m1 '^NEO4J_PASSWORD=' "$BACKUP_DIR/repo-untracked/.env" | cut -d= -f2- || true)
  fi
  if [ -z "$PW" ]; then
    red "  NEO4J_PASSWORD を取得できませんでした。手動で drop してください:"
    echo "    docker exec $NEO4J_CONTAINER cypher-shell -u neo4j -p <pw> -d system 'DROP DATABASE quants'"
  else
    step "DROP DATABASE quants（コンテナと note/research/creator は残す）"
    if $EXECUTE; then
      # パスワードは -p 引数ではなく環境変数で渡す（ps 出力に露出させないため）
      docker exec -e NEO4J_PASSWORD="$PW" "$NEO4J_CONTAINER" cypher-shell -u neo4j -d system \
        "DROP DATABASE quants IF EXISTS" 2>&1 | tail -2
      echo "  残っているデータベース:"
      docker exec -e NEO4J_PASSWORD="$PW" "$NEO4J_CONTAINER" cypher-shell -u neo4j -d system \
        "SHOW DATABASES YIELD name" --format plain 2>/dev/null | sed 's/^/    /'
    fi
  fi
else
  echo "  Neo4j コンテナが動いていません。起動してから再実行するか、手動で drop してください。"
fi
echo

# ---------------------------------------------------------------------------
# 3b. quants 専用コンテナとボリューム
#
# neo4j-enterprise は 4 プロジェクト共有なので対象外。
# quants-dev / quants-scheduler と、その名前付きボリュームのみ削除する。
# ---------------------------------------------------------------------------
bold "[3b/6] quants 専用コンテナ・ボリュームの削除"
if docker info >/dev/null 2>&1; then
  for c in quants-dev quants-scheduler; do
    if docker ps -a --format '{{.Names}}' | grep -qx "$c"; then
      step "削除: コンテナ $c"
      $EXECUTE && docker rm -f "$c" >/dev/null 2>&1 || true
    fi
  done
  # compose プロジェクト名 quants の名前付きボリュームを実測で列挙する。
  # 現行定義の venv / claude-config に加え、過去の定義の残骸
  # （quants_neo4j-data など）もここで拾える。
  # neo4j-enterprise の実データは ~/neo4j-data へのバインドマウントであり
  # 名前付きボリュームではないため、この削除では消えない。
  vols=$(docker volume ls --format '{{.Name}}' | grep '^quants_' || true)
  if [ -n "$vols" ]; then
    while IFS= read -r v; do
      [ -n "$v" ] || continue
      used=$(docker ps -a --filter "volume=$v" --format '{{.Names}}' | tr '\n' ' ')
      if [ -n "$used" ]; then
        red "  警告: ボリューム $v は $used が使用中。削除をスキップします"
        continue
      fi
      step "削除: ボリューム $v ($(docker volume inspect "$v" --format '{{.CreatedAt}}' 2>/dev/null))"
      $EXECUTE && docker volume rm "$v" >/dev/null 2>&1 || true
    done <<< "$vols"
  else
    echo "  quants_ 接頭辞のボリュームなし"
  fi
  echo "  ※ neo4j-enterprise コンテナと ~/neo4j-data は対象外（4 プロジェクト共有のため）"
else
  echo "  Docker が動いていません（スキップ）"
fi
echo ""

# ---------------------------------------------------------------------------
# 4. Neo4j 起動スクリプト
# ---------------------------------------------------------------------------
bold "[4/6] Neo4j 起動スクリプトの削除"
if [ -f "$NEO4J_STARTER" ]; then
  step "削除: $NEO4J_STARTER"
  $EXECUTE && rm -f "$NEO4J_STARTER"
else
  echo "  対象なし"
fi
echo

# ---------------------------------------------------------------------------
# 5. 孤立 worktree
# ---------------------------------------------------------------------------
bold "[5/6] 孤立 worktree の削除"
if [ -d "$ORPHAN_WORKTREE" ]; then
  step "削除: $ORPHAN_WORKTREE ($(du -sh "$ORPHAN_WORKTREE" 2>/dev/null | cut -f1))"
  $EXECUTE && rm -rf "${ORPHAN_WORKTREE:?}"
else
  echo "  対象なし"
fi
echo

# ---------------------------------------------------------------------------
# 6. リポジトリ本体
# ---------------------------------------------------------------------------
bold "[6/6] リポジトリの削除"
if [ -d "$REPO_DIR" ]; then
  step "削除: $REPO_DIR ($(du -sh "$REPO_DIR" 2>/dev/null | cut -f1))"
  $EXECUTE && rm -rf "${REPO_DIR:?}"
else
  echo "  対象なし"
fi
echo

echo "============================================================"
if $EXECUTE; then
  green "撤去完了"
  echo
  echo "残したもの（意図的）:"
  echo "  ~/neo4j-data/            4 DB 共有のため"
  echo "  com.note-finance.*       他プロジェクトの launchd ジョブ"
  echo "  ~/Desktop/Quants_data/   27GB / 判断保留"
  echo "  NAS 上の全データ"
else
  bold "dry-run 終了 — 何も削除していません"
  echo "実行するには: bash $(basename "$0") --execute"
fi
echo "============================================================"
