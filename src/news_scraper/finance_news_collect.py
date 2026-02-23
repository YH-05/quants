"""金融ニュース収集 CLI スクリプト.

複数ソース（CNBC・NASDAQ・yfinance）から金融ニュースを収集する
コマンドラインインターフェース。

使用例
------
# デフォルト設定（CNBC + NASDAQ クオンツ向けカテゴリ）
uv run python -m news_scraper.finance_news_collect

# 詳細ログ（INFO レベル）
uv run python -m news_scraper.finance_news_collect -v

# デバッグログ（DEBUG レベル）
uv run python -m news_scraper.finance_news_collect -vv

# ソース・カテゴリ指定
uv run python -m news_scraper.finance_news_collect \\
    --sources cnbc nasdaq \\
    --cnbc-categories economy earnings technology \\
    --tickers AAPL MSFT GOOGL

# 本文取得 + 出力ディレクトリ指定
uv run python -m news_scraper.finance_news_collect \\
    --include-content \\
    --output-dir data/financial_news

# 高速モード（非同期並列実行）
uv run python -m news_scraper.finance_news_collect --fast
"""

from __future__ import annotations

import argparse
import sys
from typing import TYPE_CHECKING

from utils_core.logging import get_logger, set_log_level, setup_logging

if TYPE_CHECKING:
    from pathlib import Path

from .types import CNBC_QUANT_CATEGORIES, NASDAQ_QUANT_CATEGORIES, ScraperConfig
from .unified import collect_financial_news, collect_financial_news_fast

logger = get_logger(__name__)


def _configure_logging(verbosity: int) -> None:
    """ログレベルを verbosity に応じて設定する.

    Parameters
    ----------
    verbosity : int
        冗長度レベル。0: WARNING, 1: INFO, 2+: DEBUG
    """
    setup_logging()
    if verbosity == 0:
        set_log_level("WARNING")
    elif verbosity == 1:
        set_log_level("INFO")
    elif verbosity >= 2:
        set_log_level("DEBUG")


def _build_parser() -> argparse.ArgumentParser:
    """CLI 引数パーサーを構築する.

    Returns
    -------
    argparse.ArgumentParser
        設定済みのパーサー
    """
    parser = argparse.ArgumentParser(
        prog="finance_news_collect",
        description="金融ニュースを複数ソースから収集する",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
例:
  # デフォルト設定
  python -m news_scraper.finance_news_collect

  # CNBC のみ・特定カテゴリ
  python -m news_scraper.finance_news_collect \\
      --sources cnbc \\
      --cnbc-categories economy earnings

  # 銘柄指定 + 出力ディレクトリ
  python -m news_scraper.finance_news_collect \\
      --tickers AAPL MSFT GOOGL \\
      --output-dir data/news

  # 高速モード（非同期並列）+ 本文取得
  python -m news_scraper.finance_news_collect --fast --include-content -vv
""",
    )

    # ログ制御
    parser.add_argument(
        "-v",
        "--verbose",
        action="count",
        default=0,
        help="ログの詳細度を上げる（-v: INFO, -vv: DEBUG）",
    )

    # ソース設定
    parser.add_argument(
        "--sources",
        nargs="+",
        choices=["cnbc", "nasdaq", "yfinance_ticker", "yfinance_search"],
        default=None,
        metavar="SOURCE",
        help=(
            "収集するソース（デフォルト: cnbc nasdaq）。"
            "有効な値: cnbc, nasdaq, yfinance_ticker, yfinance_search"
        ),
    )

    # CNBC カテゴリ
    parser.add_argument(
        "--cnbc-categories",
        nargs="+",
        default=None,
        metavar="CATEGORY",
        help=(f"CNBC の収集カテゴリ（デフォルト: {' '.join(CNBC_QUANT_CATEGORIES)}）"),
    )

    # NASDAQ カテゴリ
    parser.add_argument(
        "--nasdaq-categories",
        nargs="+",
        default=None,
        metavar="CATEGORY",
        help=(
            f"NASDAQ の収集カテゴリ（デフォルト: {' '.join(NASDAQ_QUANT_CATEGORIES)}）"
        ),
    )

    # 銘柄コード
    parser.add_argument(
        "--tickers",
        nargs="+",
        default=None,
        metavar="TICKER",
        help="収集する銘柄コード（例: AAPL MSFT GOOGL）",
    )

    # スクレイパー設定
    parser.add_argument(
        "--delay",
        type=float,
        default=1.0,
        help="リクエスト間隔（秒、デフォルト: 1.0）",
    )

    parser.add_argument(
        "--timeout",
        type=int,
        default=30,
        help="タイムアウト秒数（デフォルト: 30）",
    )

    parser.add_argument(
        "--max-concurrency",
        type=int,
        default=5,
        help="RSS/API の最大同時リクエスト数（デフォルト: 5）",
    )

    parser.add_argument(
        "--max-concurrency-content",
        type=int,
        default=3,
        help="本文取得の最大同時リクエスト数（デフォルト: 3）",
    )

    parser.add_argument(
        "--impersonate",
        choices=["chrome", "chrome131", "safari", "firefox"],
        default="chrome131",
        help="偽装するブラウザ（デフォルト: chrome131）",
    )

    parser.add_argument(
        "--proxy",
        default=None,
        help="プロキシ URL（例: http://user:pass@host:port）",
    )

    # 収集オプション
    parser.add_argument(
        "--include-content",
        action="store_true",
        help="記事本文を取得する（時間がかかる）",
    )

    parser.add_argument(
        "--fast",
        action="store_true",
        help="非同期並列モードで収集する（collect_financial_news_fast を使用）",
    )

    # 出力設定
    parser.add_argument(
        "--output-dir",
        default=None,
        metavar="DIR",
        help="出力ディレクトリ（指定時は JSON + Parquet で保存）",
    )

    return parser


def main(argv: list[str] | None = None) -> int:
    """CLI エントリーポイント.

    Parameters
    ----------
    argv : list[str] | None
        コマンドライン引数。None の場合は sys.argv[1:] を使用。

    Returns
    -------
    int
        終了コード（0: 成功, 1: エラー）

    Examples
    --------
    >>> import sys
    >>> sys.exit(main(["--sources", "cnbc", "-v"]))
    """
    parser = _build_parser()
    args = parser.parse_args(argv)

    # ログ設定（logging.basicConfig の代わりに setup_logging を使用）
    _configure_logging(args.verbose)

    logger.info("Starting finance news collect CLI", args=vars(args))

    # ScraperConfig を構築
    config = ScraperConfig(
        impersonate=args.impersonate,
        proxy=args.proxy,
        delay=args.delay,
        timeout=args.timeout,
        include_content=args.include_content,
        max_concurrency=args.max_concurrency,
        max_concurrency_content=args.max_concurrency_content,
    )

    output_dir: str | Path | None = args.output_dir

    try:
        if args.fast:
            # 非同期並列モード
            logger.info("Using fast (async) collection mode")
            df = collect_financial_news_fast(
                sources=args.sources,
                cnbc_categories=args.cnbc_categories,
                nasdaq_categories=args.nasdaq_categories,
                tickers=args.tickers,
                config=config,
                output_dir=output_dir,
            )
        else:
            # 同期モード
            logger.info("Using sync collection mode")
            df = collect_financial_news(
                sources=args.sources,
                cnbc_categories=args.cnbc_categories,
                nasdaq_categories=args.nasdaq_categories,
                tickers=args.tickers,
                config=config,
                output_dir=output_dir,
            )

        print(f"Collected {len(df)} articles")

        if not df.empty:
            # サマリー表示
            if "source" in df.columns:
                source_counts = df["source"].value_counts()
                for src, count in source_counts.items():
                    print(f"  {src}: {count} articles")

            if output_dir:
                print(f"Saved to: {output_dir}")

        logger.info("CLI finished successfully", article_count=len(df))
        return 0

    except KeyboardInterrupt:
        logger.info("Collection interrupted by user")
        print("\nInterrupted by user.")
        return 130

    except Exception as e:
        logger.error("CLI failed", error=str(e), exc_info=True)
        print(f"Error: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
