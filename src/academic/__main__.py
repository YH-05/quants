"""academic CLI エントリポイント.

``python -m academic fetch --arxiv-id 2303.09406`` で実行可能にするモジュール。

サブコマンド
-----------
- ``fetch``: arXiv 論文メタデータを取得して JSON 出力
  - ``--arxiv-id``: 単一の arXiv ID を指定
  - ``--arxiv-ids``: 複数の arXiv ID をスペース区切りで指定
- ``backfill``: 既存論文の著者・引用バックフィル
  - ``--ids-file``: arXiv ID リストファイル（1行1ID、# コメント対応）
  - ``--output-dir``: 出力ディレクトリ
  - ``--existing-ids``: 既存 Source ID リスト（CITES フィルタ用）

Examples
--------
>>> # 単一論文
>>> python -m academic fetch --arxiv-id 2303.09406

>>> # 複数論文
>>> python -m academic fetch --arxiv-ids 2303.09406 2401.01234

>>> # バックフィル
>>> python -m academic backfill --ids-file ids.txt --output-dir .tmp/academic

出力先: ``.tmp/academic/papers.json`` (fetch), ``.tmp/academic/graph-queue.json`` (backfill)
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from utils_core.logging import get_logger

logger = get_logger(__name__)

DEFAULT_OUTPUT_DIR = Path(".tmp/academic")
DEFAULT_OUTPUT_FILE = "papers.json"
BACKFILL_OUTPUT_FILE = "graph-queue.json"


def _build_parser() -> argparse.ArgumentParser:
    """Build the argument parser for the academic CLI.

    Returns
    -------
    argparse.ArgumentParser
        Configured parser with ``fetch`` and ``backfill`` subcommands.
    """
    parser = argparse.ArgumentParser(
        prog="python -m academic",
        description="arXiv 論文メタデータ取得 CLI",
    )
    subparsers = parser.add_subparsers(dest="command", help="サブコマンド")

    # --- fetch subcommand ---
    fetch_parser = subparsers.add_parser(
        "fetch",
        help="arXiv 論文メタデータを取得",
    )
    id_group = fetch_parser.add_mutually_exclusive_group(required=True)
    id_group.add_argument(
        "--arxiv-id",
        type=str,
        help="単一の arXiv ID（例: 2303.09406）",
    )
    id_group.add_argument(
        "--arxiv-ids",
        type=str,
        nargs="+",
        help="複数の arXiv ID（スペース区切り）",
    )
    fetch_parser.add_argument(
        "--output-dir",
        type=str,
        default=str(DEFAULT_OUTPUT_DIR),
        help=f"出力ディレクトリ（デフォルト: {DEFAULT_OUTPUT_DIR}）",
    )

    # --- backfill subcommand ---
    backfill_parser = subparsers.add_parser(
        "backfill",
        help="既存論文の著者・引用バックフィル（graph-queue JSON 出力）",
    )
    backfill_parser.add_argument(
        "--ids-file",
        type=str,
        required=True,
        help="arXiv ID リストファイル（1行1ID、# コメント・空行対応）",
    )
    backfill_parser.add_argument(
        "--output-dir",
        type=str,
        default=str(DEFAULT_OUTPUT_DIR),
        help=f"出力ディレクトリ（デフォルト: {DEFAULT_OUTPUT_DIR}）",
    )
    backfill_parser.add_argument(
        "--existing-ids",
        type=str,
        nargs="*",
        default=None,
        help="既存 Source ID リスト（CITES フィルタ用）",
    )
    backfill_parser.add_argument(
        "--existing-ids-file",
        type=str,
        default=None,
        help="既存 Source ID リストファイル（1行1ID、--existing-ids の代替）",
    )

    return parser


def main(argv: list[str] | None = None) -> int:
    """Entry point for the academic CLI.

    Parameters
    ----------
    argv : list[str] | None, optional
        Command-line arguments (default: ``sys.argv[1:]``).

    Returns
    -------
    int
        Exit code (0 for success, 1 for error).
    """
    parser = _build_parser()
    args = parser.parse_args(argv)

    if args.command is None:
        parser.print_help()
        return 1

    if args.command == "fetch":
        return _handle_fetch(args)

    if args.command == "backfill":
        return _handle_backfill(args)

    return 0


def _handle_fetch(args: argparse.Namespace) -> int:
    """Handle the ``fetch`` subcommand.

    Parameters
    ----------
    args : argparse.Namespace
        Parsed arguments with ``arxiv_id`` or ``arxiv_ids``.

    Returns
    -------
    int
        Exit code.
    """
    from .fetcher import PaperFetcher
    from .fetcher import paper_metadata_to_dict as _pm_to_dict

    arxiv_ids: list[str] = []
    if args.arxiv_id:
        arxiv_ids = [args.arxiv_id]
    elif args.arxiv_ids:
        arxiv_ids = args.arxiv_ids

    if not arxiv_ids:
        logger.error("No arXiv IDs specified")
        print("Error: No arXiv IDs specified", file=sys.stderr)
        return 1

    logger.info("Fetching papers", arxiv_ids=arxiv_ids, count=len(arxiv_ids))

    try:
        with PaperFetcher() as fetcher:
            if len(arxiv_ids) == 1:
                papers = [fetcher.fetch_paper(arxiv_ids[0])]
            else:
                papers = fetcher.fetch_papers_batch(arxiv_ids)
    except Exception as exc:
        logger.error("Failed to fetch papers", error=str(exc), exc_info=True)
        print(f"Error: Failed to fetch papers: {exc}", file=sys.stderr)
        return 1

    # Serialize to JSON
    output_data = {
        "papers": [_pm_to_dict(p) for p in papers],
    }

    # Write output
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / DEFAULT_OUTPUT_FILE

    try:
        with output_path.open("w", encoding="utf-8") as f:
            json.dump(output_data, f, ensure_ascii=False, indent=2)
    except OSError as exc:
        logger.error("Failed to write output", path=str(output_path), error=str(exc))
        print(f"Error: Failed to write output: {exc}", file=sys.stderr)
        return 1

    logger.info(
        "Papers fetched and saved",
        count=len(papers),
        output_path=str(output_path),
    )
    print(str(output_path))
    return 0


def _read_arxiv_ids(file_path: str) -> list[str]:
    """arXiv ID リストファイルを読み込む.

    空行と ``#`` で始まるコメント行はスキップする。
    各行の前後の空白はトリムされる。

    Parameters
    ----------
    file_path : str
        arXiv ID リストファイルのパス。

    Returns
    -------
    list[str]
        arXiv ID のリスト。

    Raises
    ------
    FileNotFoundError
        ファイルが存在しない場合。
    """
    ids: list[str] = []
    with Path(file_path).open(encoding="utf-8") as f:
        for line in f:
            stripped = line.strip()
            if not stripped or stripped.startswith("#"):
                continue
            ids.append(stripped)
    return ids


def _handle_backfill(args: argparse.Namespace) -> int:
    """Handle the ``backfill`` subcommand.

    arXiv ID リストファイルを読み込み、PaperFetcher でメタデータを取得し、
    map_academic_papers で graph-queue JSON に変換して出力する。

    Parameters
    ----------
    args : argparse.Namespace
        Parsed arguments with ``ids_file``, ``output_dir``, and
        optional ``existing_ids``.

    Returns
    -------
    int
        Exit code (0 for success, 1 for error).
    """
    from .fetcher import PaperFetcher
    from .fetcher import paper_metadata_to_dict as _pm_to_dict
    from .mapper import map_academic_papers

    # 1. IDs ファイルを読み込む
    try:
        arxiv_ids = _read_arxiv_ids(args.ids_file)
    except FileNotFoundError:
        logger.error("IDs file not found", path=args.ids_file)
        print(f"Error: IDs file not found: {args.ids_file}", file=sys.stderr)
        return 1

    if not arxiv_ids:
        logger.error("No valid arXiv IDs found in file", path=args.ids_file)
        print(
            f"Error: No valid arXiv IDs found in {args.ids_file}",
            file=sys.stderr,
        )
        return 1

    logger.info(
        "Backfill started",
        ids_file=args.ids_file,
        arxiv_id_count=len(arxiv_ids),
    )

    # 2. PaperFetcher でメタデータを取得
    try:
        with PaperFetcher() as fetcher:
            papers = fetcher.fetch_papers_batch(arxiv_ids)
    except Exception as exc:
        logger.error("Failed to fetch papers", error=str(exc), exc_info=True)
        print(f"Error: Failed to fetch papers: {exc}", file=sys.stderr)
        return 1

    logger.info("Papers fetched", fetched_count=len(papers))

    # 3. PaperMetadata -> dict に変換
    paper_dicts = [_pm_to_dict(p) for p in papers]

    # 4. map_academic_papers で graph-queue JSON に変換
    existing_ids: list[str] = args.existing_ids or []
    if args.existing_ids_file:
        existing_ids.extend(_read_arxiv_ids(args.existing_ids_file))
    mapper_input = {
        "papers": paper_dicts,
        "existing_source_ids": existing_ids,
    }
    graph_queue = map_academic_papers(mapper_input)

    # 5. 出力
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / BACKFILL_OUTPUT_FILE

    try:
        with output_path.open("w", encoding="utf-8") as f:
            json.dump(graph_queue, f, ensure_ascii=False, indent=2)
    except OSError as exc:
        logger.error(
            "Failed to write graph-queue output",
            path=str(output_path),
            error=str(exc),
        )
        print(f"Error: Failed to write output: {exc}", file=sys.stderr)
        return 1

    logger.info(
        "Backfill completed",
        output_path=str(output_path),
        source_count=len(graph_queue.get("sources", [])),
        author_count=len(graph_queue.get("authors", [])),
        authored_by_count=len(graph_queue.get("relations", {}).get("authored_by", [])),
        cites_count=len(graph_queue.get("relations", {}).get("cites", [])),
        coauthored_with_count=len(
            graph_queue.get("relations", {}).get("coauthored_with", [])
        ),
    )
    print(str(output_path))
    return 0


if __name__ == "__main__":
    sys.exit(main())
