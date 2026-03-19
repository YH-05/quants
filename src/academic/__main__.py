"""academic CLI エントリポイント.

``python -m academic fetch --arxiv-id 2303.09406`` で実行可能にするモジュール。

サブコマンド
-----------
- ``fetch``: arXiv 論文メタデータを取得して JSON 出力
  - ``--arxiv-id``: 単一の arXiv ID を指定
  - ``--arxiv-ids``: 複数の arXiv ID をスペース区切りで指定

Examples
--------
>>> # 単一論文
>>> python -m academic fetch --arxiv-id 2303.09406

>>> # 複数論文
>>> python -m academic fetch --arxiv-ids 2303.09406 2401.01234

出力先: ``.tmp/academic/papers.json``
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

from utils_core.logging import get_logger

logger = get_logger(__name__)

DEFAULT_OUTPUT_DIR = Path(".tmp/academic")
DEFAULT_OUTPUT_FILE = "papers.json"


def _paper_metadata_to_dict(paper: Any) -> dict[str, Any]:
    """PaperMetadata を JSON シリアライズ可能な dict に変換する.

    Parameters
    ----------
    paper : PaperMetadata
        変換する論文メタデータ。

    Returns
    -------
    dict[str, Any]
        シリアライズ可能な辞書。
    """
    return {
        "arxiv_id": paper.arxiv_id,
        "title": paper.title,
        "authors": [
            {
                "name": a.name,
                "s2_author_id": a.s2_author_id,
                "organization": a.organization,
            }
            for a in paper.authors
        ],
        "references": [
            {
                "title": r.title,
                "arxiv_id": r.arxiv_id,
                "s2_paper_id": r.s2_paper_id,
            }
            for r in paper.references
        ],
        "citations": [
            {
                "title": c.title,
                "arxiv_id": c.arxiv_id,
                "s2_paper_id": c.s2_paper_id,
            }
            for c in paper.citations
        ],
        "abstract": paper.abstract,
        "s2_paper_id": paper.s2_paper_id,
        "published": paper.published,
        "updated": paper.updated,
    }


def _build_parser() -> argparse.ArgumentParser:
    """Build the argument parser for the academic CLI.

    Returns
    -------
    argparse.ArgumentParser
        Configured parser with ``fetch`` subcommand.
    """
    parser = argparse.ArgumentParser(
        prog="python -m academic",
        description="arXiv 論文メタデータ取得 CLI",
    )
    subparsers = parser.add_subparsers(dest="command", help="サブコマンド")

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
        "papers": [_paper_metadata_to_dict(p) for p in papers],
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


if __name__ == "__main__":
    sys.exit(main())
