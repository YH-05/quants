"""ローカル edinet.db を NAS edinet.db にテーブル単位でマージするスクリプト.

launchd 経由の sync (TCC 制約のためローカルにダウンロード) の結果を
NAS にバックアップ・反映するために使用する。GUI/Terminal セッションから
実行することで macOS TCC の Network Volumes 許可が継承される前提。

Usage
-----
    $ uv run python scripts/edinet_merge_to_nas.py
    $ uv run python scripts/edinet_merge_to_nas.py --dry-run
    $ uv run python scripts/edinet_merge_to_nas.py \
        --source data/sqlite/edinet.db \
        --target "${DATA_DIR}/sqlite/edinet.db"

Notes
-----
- 各テーブルは INSERT OR REPLACE で PK ベースに反映 (差分のみ書き込まれる)
- マージは NAS DB のトランザクション内で実行され、失敗時はロールバック
- _rate_limit.json と _sync_state.json も上書きコピー
- NAS DB ファイルが存在しない場合はローカルをコピーして初期化
- --target の既定値は環境変数 DATA_DIR 配下 (コンテナ内は /nas/Projects/quants/data)

参照
----
- docs/plan/2026-05-27_discussion-edinet-launchd-nas-failure.md
- act-2026-05-27-002, act-2026-05-27-003
"""

from __future__ import annotations

import argparse
import os
import shutil
import sqlite3
import sys
from collections.abc import Iterable
from datetime import UTC, datetime
from pathlib import Path

from utils_core.logging import get_logger

logger = get_logger(__name__)

REPO_ROOT = Path(__file__).resolve().parents[1]

# macOS で NAS をマウントする従来の場所。DATA_DIR 未設定時のみ使う
_FALLBACK_NAS_DATA_DIR = Path("/Volumes/personal_folder/Projects/quants/data")


def _nas_data_dir() -> Path:
    """マージ先 (NAS) のデータルートを解決する.

    Returns
    -------
    Path
        環境変数 ``DATA_DIR`` が設定されていればその値、未設定なら
        ``_FALLBACK_NAS_DATA_DIR``。source と同一パスになるのを避けるため、
        ここではリポジトリ相対にフォールバックしない。
    """
    env_data_dir = os.environ.get("DATA_DIR", "").strip()
    return Path(env_data_dir) if env_data_dir else _FALLBACK_NAS_DATA_DIR


# source は launchd がローカルへダウンロードした DB (リポジトリ内 data/)
DEFAULT_SOURCE_DB = REPO_ROOT / "data" / "sqlite" / "edinet.db"
# target は NAS 上の正本 (DATA_DIR 配下)
DEFAULT_TARGET_DB = _nas_data_dir() / "sqlite" / "edinet.db"

TABLES: tuple[str, ...] = (
    "companies",
    "industries",
    "industry_details",
    "financials",
    "ratios",
    "text_blocks",
)

STATE_FILES: tuple[str, ...] = ("_rate_limit.json", "_sync_state.json")


def _table_columns(conn: sqlite3.Connection, table: str) -> list[str]:
    """テーブルのカラム名一覧を順序通りに取得する."""
    rows = conn.execute(f"PRAGMA table_info({table})").fetchall()
    return [row[1] for row in rows]


def merge_table(
    source: sqlite3.Connection,
    target: sqlite3.Connection,
    table: str,
    *,
    dry_run: bool = False,
) -> tuple[int, int]:
    """source DB の指定テーブルを target DB に INSERT OR REPLACE でマージする.

    Returns
    -------
    tuple[int, int]
        (source_row_count, written_row_count)
        dry_run=True の場合 written_row_count は 0
    """
    cols = _table_columns(source, table)
    if not cols:
        raise ValueError(f"table not found or empty schema: {table}")

    col_list = ", ".join(cols)
    placeholders = ", ".join("?" * len(cols))

    source_rows = source.execute(f"SELECT {col_list} FROM {table}").fetchall()
    source_count = len(source_rows)

    if dry_run or source_count == 0:
        return source_count, 0

    sql = f"INSERT OR REPLACE INTO {table} ({col_list}) VALUES ({placeholders})"
    target.executemany(sql, source_rows)
    return source_count, source_count


def copy_state_files(
    source_dir: Path,
    target_dir: Path,
    *,
    dry_run: bool = False,
) -> list[str]:
    """同期ステートファイル (JSON) を target にコピーする.

    Returns
    -------
    list[str]
        コピーしたファイル名のリスト (dry_run=True なら空)
    """
    copied: list[str] = []
    for name in STATE_FILES:
        src = source_dir / name
        dst = target_dir / name
        if not src.exists():
            logger.warning("state file not found in source", extra={"file": str(src)})
            continue
        if dry_run:
            logger.info(
                "[dry-run] would copy", extra={"src": str(src), "dst": str(dst)}
            )
            continue
        shutil.copy2(src, dst)
        copied.append(name)
    return copied


def merge(
    source_db: Path, target_db: Path, *, dry_run: bool = False
) -> dict[str, tuple[int, int]]:
    """source DB を target DB にマージする (テーブル単位 INSERT OR REPLACE).

    Parameters
    ----------
    source_db : Path
        マージ元 SQLite DB ファイルパス
    target_db : Path
        マージ先 SQLite DB ファイルパス
    dry_run : bool
        True の場合は読み込みのみで書き込みは実行しない

    Returns
    -------
    dict[str, tuple[int, int]]
        テーブル名 -> (source 行数, 書き込み行数)

    Raises
    ------
    FileNotFoundError
        source_db が存在しない場合
    """
    if not source_db.exists():
        raise FileNotFoundError(f"source DB not found: {source_db}")

    target_db.parent.mkdir(parents=True, exist_ok=True)

    if not target_db.exists():
        if dry_run:
            logger.info(
                "[dry-run] target DB does not exist; would copy from source",
                extra={"source": str(source_db), "target": str(target_db)},
            )
            return {t: (0, 0) for t in TABLES}
        logger.info(
            "target DB does not exist, initializing by copying source",
            extra={"source": str(source_db), "target": str(target_db)},
        )
        shutil.copy2(source_db, target_db)
        # state files も初期コピー
        copy_state_files(source_db.parent, target_db.parent, dry_run=False)
        return {t: (0, 0) for t in TABLES}

    started = datetime.now(UTC)
    logger.info(
        "merge started",
        extra={
            "source": str(source_db),
            "target": str(target_db),
            "dry_run": dry_run,
        },
    )

    results: dict[str, tuple[int, int]] = {}

    source_conn = sqlite3.connect(f"file:{source_db}?mode=ro", uri=True)
    target_conn = sqlite3.connect(str(target_db))

    try:
        target_conn.execute("BEGIN IMMEDIATE")
        for table in TABLES:
            src_count, written = merge_table(
                source_conn, target_conn, table, dry_run=dry_run
            )
            results[table] = (src_count, written)
            logger.info(
                "table merged",
                extra={"table": table, "source_rows": src_count, "written": written},
            )
        if dry_run:
            target_conn.rollback()
        else:
            target_conn.commit()
    except Exception:
        target_conn.rollback()
        logger.error("merge failed, rolled back", exc_info=True)
        raise
    finally:
        source_conn.close()
        target_conn.close()

    copy_state_files(source_db.parent, target_db.parent, dry_run=dry_run)

    elapsed = (datetime.now(UTC) - started).total_seconds()
    logger.info("merge completed", extra={"elapsed_sec": elapsed, "dry_run": dry_run})

    return results


def _format_summary(results: dict[str, tuple[int, int]]) -> str:
    """マージ結果のサマリー文字列を生成する."""
    lines = ["", "Merge Summary", "=" * 60]
    for table, (src, written) in results.items():
        lines.append(f"  {table:<20} source={src:>8}  written={written:>8}")
    return "\n".join(lines)


def main(argv: Iterable[str] | None = None) -> int:
    """エントリーポイント."""
    parser = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--source",
        type=Path,
        default=DEFAULT_SOURCE_DB,
        help=f"source DB path (default: {DEFAULT_SOURCE_DB})",
    )
    parser.add_argument(
        "--target",
        type=Path,
        default=DEFAULT_TARGET_DB,
        help=f"target DB path (default: {DEFAULT_TARGET_DB})",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="読み込み行数のみ表示し書き込みは行わない",
    )

    args = parser.parse_args(list(argv) if argv is not None else None)

    if not args.target.parent.exists():
        print(
            f"ERROR: target directory not accessible: {args.target.parent}",
            file=sys.stderr,
        )
        print(
            "If target is on a NAS volume, ensure the volume is mounted and "
            "your current process has TCC permission to access it.",
            file=sys.stderr,
        )
        return 2

    try:
        results = merge(args.source, args.target, dry_run=args.dry_run)
    except FileNotFoundError as e:
        print(f"ERROR: {e}", file=sys.stderr)
        return 2
    except Exception as e:
        print(f"ERROR: merge failed: {e}", file=sys.stderr)
        return 1

    print(_format_summary(results))
    if args.dry_run:
        print("\n[dry-run] no changes were written.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
