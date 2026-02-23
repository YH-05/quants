"""CLI エントリポイント.

argparse で引数を受け取り、PipelineConfig を構築して
asyncio.run(run_pipeline(config)) を実行する。

Examples
--------
$ uv run embedding-pipeline --help
$ uv run embedding-pipeline --news-dir data/raw/news --chromadb-path data/chromadb
"""

import argparse
import asyncio
import logging
from pathlib import Path

from .pipeline import run_pipeline
from .types import PipelineConfig

logger = logging.getLogger(__name__)


def build_parser() -> argparse.ArgumentParser:
    """引数パーサを構築する.

    Returns
    -------
    argparse.ArgumentParser
        設定済みの引数パーサ
    """
    parser = argparse.ArgumentParser(
        prog="embedding-pipeline",
        description="ニュース記事のエンベディングパイプラインを実行する",
    )
    parser.add_argument(
        "--news-dir",
        type=Path,
        default=Path("data/raw/news"),
        help="ニュース JSON の格納ディレクトリ (default: data/raw/news)",
    )
    parser.add_argument(
        "--chromadb-path",
        type=Path,
        default=Path("data/chromadb"),
        help="ChromaDB の永続化パス (default: data/chromadb)",
    )
    parser.add_argument(
        "--collection-name",
        default="gemini-embedding-001",
        help="ChromaDB コレクション名 (default: gemini-embedding-001)",
    )
    parser.add_argument(
        "--sources",
        nargs="+",
        default=None,
        help="対象ソースのフィルタリング（スペース区切りで複数指定可）",
    )
    parser.add_argument(
        "--max-concurrent",
        type=int,
        default=3,
        help="最大同時リクエスト数 (default: 3)",
    )
    parser.add_argument(
        "--delay",
        type=float,
        default=1.5,
        help="リクエスト間の待機秒数 (default: 1.5)",
    )
    parser.add_argument(
        "--log-level",
        default="INFO",
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
        help="ログレベル (default: INFO)",
    )
    return parser


def main() -> None:
    """CLI のメインエントリポイント.

    引数を解析して PipelineConfig を構築し、パイプラインを実行する。
    実行統計をログに出力する。
    """
    parser = build_parser()
    args = parser.parse_args()

    logging.basicConfig(
        level=getattr(logging, args.log_level),
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
    )

    config = PipelineConfig(
        news_dir=args.news_dir,
        chromadb_path=args.chromadb_path,
        collection_name=args.collection_name,
        sources=args.sources,
        max_concurrency=args.max_concurrent,
        delay=args.delay,
    )

    logger.info("Starting embedding pipeline")
    logger.info("  news_dir:        %s", config.news_dir)
    logger.info("  chromadb_path:   %s", config.chromadb_path)
    logger.info("  collection_name: %s", config.collection_name)
    logger.info("  sources:         %s", config.sources or "all")
    logger.info("  max_concurrency: %d", config.max_concurrency)
    logger.info("  delay:           %.1f s", config.delay)

    stats = asyncio.run(run_pipeline(config))

    logger.info("Pipeline completed")
    logger.info("  total_json_articles: %d", stats["total_json_articles"])
    logger.info("  already_in_chromadb: %d", stats["already_in_chromadb"])
    logger.info("  new_articles:        %d", stats["new_articles"])
    logger.info("  extraction_success:  %d", stats["extraction_success"])
    logger.info("  extraction_failed:   %d", stats["extraction_failed"])
    logger.info("  stored:              %d", stats["stored"])
