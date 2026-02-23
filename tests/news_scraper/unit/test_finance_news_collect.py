"""finance_news_collect.py の単体テスト.

CLI のコマンドライン引数処理、ロギング設定、main() の動作を検証する。
外部収集処理はモックで差し替える。
"""

from __future__ import annotations

import sys
from typing import TYPE_CHECKING
from unittest.mock import MagicMock, call, patch

if TYPE_CHECKING:
    from pathlib import Path

import pandas as pd
import pytest

from news_scraper.finance_news_collect import _build_parser, _configure_logging, main

# ---------------------------------------------------------------------------
# _configure_logging
# ---------------------------------------------------------------------------


class TestConfigureLogging:
    """_configure_logging() の動作を検証する."""

    def test_正常系_verbosity0でWARNINGレベルが設定される(self) -> None:
        """verbosity=0 のとき WARNING レベルが設定される."""
        with (
            patch("news_scraper.finance_news_collect.setup_logging") as mock_setup,
            patch("news_scraper.finance_news_collect.set_log_level") as mock_set,
        ):
            _configure_logging(0)

        mock_setup.assert_called_once()
        mock_set.assert_called_once_with("WARNING")

    def test_正常系_verbosity1でINFOレベルが設定される(self) -> None:
        """verbosity=1 のとき INFO レベルが設定される."""
        with (
            patch("news_scraper.finance_news_collect.setup_logging") as mock_setup,
            patch("news_scraper.finance_news_collect.set_log_level") as mock_set,
        ):
            _configure_logging(1)

        mock_setup.assert_called_once()
        mock_set.assert_called_once_with("INFO")

    def test_正常系_verbosity2でDEBUGレベルが設定される(self) -> None:
        """verbosity=2 のとき DEBUG レベルが設定される."""
        with (
            patch("news_scraper.finance_news_collect.setup_logging") as mock_setup,
            patch("news_scraper.finance_news_collect.set_log_level") as mock_set,
        ):
            _configure_logging(2)

        mock_setup.assert_called_once()
        mock_set.assert_called_once_with("DEBUG")

    def test_正常系_verbosity3以上でDEBUGレベルが設定される(self) -> None:
        """verbosity>=3 のとき DEBUG レベルが設定される."""
        with (
            patch("news_scraper.finance_news_collect.setup_logging"),
            patch("news_scraper.finance_news_collect.set_log_level") as mock_set,
        ):
            _configure_logging(3)

        mock_set.assert_called_once_with("DEBUG")

    def test_正常系_import_loggingが使われない(self) -> None:
        """logging.basicConfig は使用されない（utils_core を使用）."""
        import logging

        with (
            patch("news_scraper.finance_news_collect.setup_logging"),
            patch("news_scraper.finance_news_collect.set_log_level"),
            patch.object(logging, "basicConfig") as mock_basic,
        ):
            _configure_logging(1)

        mock_basic.assert_not_called()


# ---------------------------------------------------------------------------
# _build_parser
# ---------------------------------------------------------------------------


class TestBuildParser:
    """_build_parser() の動作を検証する."""

    def test_正常系_デフォルト値が正しい(self) -> None:
        """デフォルト引数が正しく設定されている."""
        parser = _build_parser()
        args = parser.parse_args([])

        assert args.verbose == 0
        assert args.sources is None
        assert args.cnbc_categories is None
        assert args.nasdaq_categories is None
        assert args.tickers is None
        assert args.delay == 1.0
        assert args.timeout == 30
        assert args.max_concurrency == 5
        assert args.max_concurrency_content == 3
        assert args.impersonate == "chrome131"
        assert args.proxy is None
        assert args.include_content is False
        assert args.fast is False
        assert args.output_dir is None

    def test_正常系_verbose_オプションが積算される(self) -> None:
        """-v は verbosity=1, -vv は verbosity=2."""
        parser = _build_parser()

        args_v = parser.parse_args(["-v"])
        assert args_v.verbose == 1

        args_vv = parser.parse_args(["-vv"])
        assert args_vv.verbose == 2

    def test_正常系_sourcesが複数指定できる(self) -> None:
        """--sources で複数のソースが指定できる."""
        parser = _build_parser()
        args = parser.parse_args(["--sources", "cnbc", "nasdaq"])
        assert args.sources == ["cnbc", "nasdaq"]

    def test_正常系_tickersが複数指定できる(self) -> None:
        """--tickers で複数の銘柄コードが指定できる."""
        parser = _build_parser()
        args = parser.parse_args(["--tickers", "AAPL", "MSFT", "GOOGL"])
        assert args.tickers == ["AAPL", "MSFT", "GOOGL"]

    def test_正常系_include_contentフラグが設定される(self) -> None:
        """--include-content フラグが True になる."""
        parser = _build_parser()
        args = parser.parse_args(["--include-content"])
        assert args.include_content is True

    def test_正常系_fastフラグが設定される(self) -> None:
        """--fast フラグが True になる."""
        parser = _build_parser()
        args = parser.parse_args(["--fast"])
        assert args.fast is True

    def test_正常系_output_dirが設定される(self) -> None:
        """--output-dir オプションが設定される."""
        parser = _build_parser()
        args = parser.parse_args(["--output-dir", "data/news"])
        assert args.output_dir == "data/news"

    def test_異常系_無効なsourceは拒否される(self) -> None:
        """無効なソース名は ArgumentError になる."""
        parser = _build_parser()
        with pytest.raises(SystemExit):
            parser.parse_args(["--sources", "invalid_source"])


# ---------------------------------------------------------------------------
# main
# ---------------------------------------------------------------------------


def _make_df(count: int = 3, source: str = "cnbc") -> pd.DataFrame:
    """テスト用 DataFrame を生成する."""
    return pd.DataFrame(
        [
            {
                "title": f"Article {i}",
                "url": f"https://example.com/article-{i}",
                "source": source,
            }
            for i in range(count)
        ]
    )


class TestMain:
    """main() の動作を検証する."""

    def test_正常系_デフォルト引数で成功する(
        self, capsys: pytest.CaptureFixture
    ) -> None:
        """引数なしで main() が成功（終了コード 0）を返す."""
        df_mock = _make_df(3)

        with (
            patch("news_scraper.finance_news_collect.setup_logging"),
            patch("news_scraper.finance_news_collect.set_log_level"),
            patch(
                "news_scraper.finance_news_collect.collect_financial_news"
            ) as mock_collect,
        ):
            mock_collect.return_value = df_mock
            result = main([])

        assert result == 0
        captured = capsys.readouterr()
        assert "Collected 3 articles" in captured.out

    def test_正常系_fastモードでasync版が呼ばれる(
        self, capsys: pytest.CaptureFixture
    ) -> None:
        """--fast フラグ時に collect_financial_news_fast が使用される."""
        df_mock = _make_df(5)

        with (
            patch("news_scraper.finance_news_collect.setup_logging"),
            patch("news_scraper.finance_news_collect.set_log_level"),
            patch(
                "news_scraper.finance_news_collect.collect_financial_news_fast"
            ) as mock_fast,
            patch(
                "news_scraper.finance_news_collect.collect_financial_news"
            ) as mock_sync,
        ):
            mock_fast.return_value = df_mock
            result = main(["--fast"])

        assert result == 0
        mock_fast.assert_called_once()
        mock_sync.assert_not_called()

    def test_正常系_verbose_フラグでINFOレベルが設定される(self) -> None:
        """-v フラグで INFO レベルが設定される."""
        df_mock = _make_df(1)

        with (
            patch("news_scraper.finance_news_collect.setup_logging"),
            patch("news_scraper.finance_news_collect.set_log_level") as mock_set,
            patch(
                "news_scraper.finance_news_collect.collect_financial_news"
            ) as mock_collect,
        ):
            mock_collect.return_value = df_mock
            main(["-v"])

        mock_set.assert_called_with("INFO")

    def test_正常系_出力ディレクトリが表示される(
        self, tmp_path: Path, capsys: pytest.CaptureFixture
    ) -> None:
        """--output-dir 指定時に保存先が表示される."""
        df_mock = _make_df(2)

        with (
            patch("news_scraper.finance_news_collect.setup_logging"),
            patch("news_scraper.finance_news_collect.set_log_level"),
            patch(
                "news_scraper.finance_news_collect.collect_financial_news"
            ) as mock_collect,
        ):
            mock_collect.return_value = df_mock
            main(["--output-dir", str(tmp_path)])

        captured = capsys.readouterr()
        assert str(tmp_path) in captured.out

    def test_異常系_例外が発生した場合に終了コード1を返す(
        self, capsys: pytest.CaptureFixture
    ) -> None:
        """収集中に例外が発生した場合、終了コード 1 を返す."""
        with (
            patch("news_scraper.finance_news_collect.setup_logging"),
            patch("news_scraper.finance_news_collect.set_log_level"),
            patch(
                "news_scraper.finance_news_collect.collect_financial_news"
            ) as mock_collect,
        ):
            mock_collect.side_effect = RuntimeError("Collection failed")
            result = main([])

        assert result == 1
        captured = capsys.readouterr()
        assert "Error" in captured.err

    def test_正常系_import_loggingが存在しない(self) -> None:
        """finance_news_collect モジュールに import logging が含まれていないことを確認."""
        import inspect

        import news_scraper.finance_news_collect as cli_module

        source = inspect.getsource(cli_module)
        # `import logging` ステートメントが存在しないことを確認
        assert "import logging" not in source

    def test_正常系_fstringログが残っていない(self) -> None:
        """f-string ログフォーマットが使用されていないことを確認."""
        import inspect

        import news_scraper.finance_news_collect as cli_module

        source = inspect.getsource(cli_module)
        # logger.xxx(f"...") のパターンがないことを確認
        assert 'logger.info(f"' not in source
        assert 'logger.debug(f"' not in source
        assert 'logger.error(f"' not in source
        assert 'logger.warning(f"' not in source
