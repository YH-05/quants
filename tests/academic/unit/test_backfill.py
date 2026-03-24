"""academic backfill サブコマンドの単体テスト.

backfill サブコマンドが arXiv ID リストを受け取り、
PaperFetcher で取得 → map_academic_papers で graph-queue JSON 変換 → ファイル出力
する一連の処理を検証する。
"""

from __future__ import annotations

import argparse
import json
from typing import TYPE_CHECKING, Any
from unittest.mock import MagicMock, patch

import pytest

from academic.__main__ import _build_parser, _handle_backfill, main
from academic.types import AuthorInfo, CitationInfo, PaperMetadata

if TYPE_CHECKING:
    from pathlib import Path


def _sample_paper(arxiv_id: str = "2301.00001") -> PaperMetadata:
    """テスト用の PaperMetadata を生成する."""
    return PaperMetadata(
        arxiv_id=arxiv_id,
        title=f"Sample Paper {arxiv_id}",
        authors=(
            AuthorInfo(name="Alice Doe", s2_author_id="a1"),
            AuthorInfo(name="Bob Smith", s2_author_id="a2"),
        ),
        references=(CitationInfo(title="Ref Paper", arxiv_id="2001.00001"),),
        citations=(),
        abstract="Test abstract.",
        s2_paper_id=f"s2-{arxiv_id}",
        published="2023-01-15",
    )


class TestBackfillParserRegistration:
    """backfill サブコマンドのパーサー登録テスト."""

    def test_正常系_backfillサブコマンドが登録されている(self) -> None:
        """backfill サブコマンドがパーサーに登録されていることを確認."""
        parser = _build_parser()
        args = parser.parse_args(["backfill", "--ids-file", "ids.txt"])
        assert args.command == "backfill"

    def test_正常系_ids_fileオプションが解析される(self) -> None:
        """--ids-file オプションが正しく解析されることを確認."""
        parser = _build_parser()
        args = parser.parse_args(["backfill", "--ids-file", "/path/to/ids.txt"])
        assert args.ids_file == "/path/to/ids.txt"

    def test_正常系_output_dirオプションが解析される(self) -> None:
        """--output-dir オプションが正しく解析されることを確認."""
        parser = _build_parser()
        args = parser.parse_args(
            [
                "backfill",
                "--ids-file",
                "ids.txt",
                "--output-dir",
                "/custom/output",
            ]
        )
        assert args.output_dir == "/custom/output"

    def test_正常系_existing_idsオプションが解析される(self) -> None:
        """--existing-ids オプションが正しく解析されることを確認."""
        parser = _build_parser()
        args = parser.parse_args(
            [
                "backfill",
                "--ids-file",
                "ids.txt",
                "--existing-ids",
                "id1",
                "id2",
                "id3",
            ]
        )
        assert args.existing_ids == ["id1", "id2", "id3"]

    def test_正常系_fetchサブコマンドは既存のまま動作する(self) -> None:
        """既存の fetch サブコマンドが影響を受けないことを確認."""
        parser = _build_parser()
        args = parser.parse_args(["fetch", "--arxiv-id", "2301.00001"])
        assert args.command == "fetch"


class TestHandleBackfill:
    """_handle_backfill の単体テスト."""

    def test_正常系_IDファイルを読み込んでgraph_queue_JSONを出力する(
        self, tmp_path: Path
    ) -> None:
        """IDs ファイルから arXiv ID を読み込み、graph-queue JSON を出力することを確認."""
        # IDs file
        ids_file = tmp_path / "ids.txt"
        ids_file.write_text("2301.00001\n2301.00002\n")

        output_dir = tmp_path / "output"

        paper1 = _sample_paper("2301.00001")
        paper2 = _sample_paper("2301.00002")

        mock_fetcher = MagicMock()
        mock_fetcher.fetch_papers_batch.return_value = [paper1, paper2]
        mock_fetcher.__enter__ = MagicMock(return_value=mock_fetcher)
        mock_fetcher.__exit__ = MagicMock(return_value=False)

        with patch("academic.fetcher.PaperFetcher", return_value=mock_fetcher):
            args = argparse.Namespace(
                ids_file=str(ids_file),
                output_dir=str(output_dir),
                existing_ids=None,
                existing_ids_file=None,
            )
            result = _handle_backfill(args)

        assert result == 0
        # graph-queue JSON が出力されていること
        output_file = output_dir / "graph-queue.json"
        assert output_file.exists()

        data = json.loads(output_file.read_text(encoding="utf-8"))
        assert data["schema_version"] == "2.1"
        assert len(data["sources"]) == 2
        assert len(data["authors"]) == 2  # Alice, Bob (deduplicated)

    def test_正常系_空行とコメント行がスキップされる(self, tmp_path: Path) -> None:
        """IDs ファイルの空行と # コメント行がスキップされることを確認."""
        ids_file = tmp_path / "ids.txt"
        ids_file.write_text(
            "# This is a comment\n2301.00001\n\n  \n# Another comment\n2301.00002\n"
        )

        output_dir = tmp_path / "output"

        paper1 = _sample_paper("2301.00001")
        paper2 = _sample_paper("2301.00002")

        mock_fetcher = MagicMock()
        mock_fetcher.fetch_papers_batch.return_value = [paper1, paper2]
        mock_fetcher.__enter__ = MagicMock(return_value=mock_fetcher)
        mock_fetcher.__exit__ = MagicMock(return_value=False)

        with patch("academic.fetcher.PaperFetcher", return_value=mock_fetcher):
            args = argparse.Namespace(
                ids_file=str(ids_file),
                output_dir=str(output_dir),
                existing_ids=None,
                existing_ids_file=None,
            )
            result = _handle_backfill(args)

        assert result == 0
        mock_fetcher.fetch_papers_batch.assert_called_once_with(
            ["2301.00001", "2301.00002"]
        )

    def test_正常系_existing_idsがgraph_queueに渡される(self, tmp_path: Path) -> None:
        """--existing-ids で指定した ID が graph-queue の existing_source_ids に渡されることを確認."""
        ids_file = tmp_path / "ids.txt"
        ids_file.write_text("2301.00001\n")

        output_dir = tmp_path / "output"

        paper1 = _sample_paper("2301.00001")

        mock_fetcher = MagicMock()
        mock_fetcher.fetch_papers_batch.return_value = [paper1]
        mock_fetcher.__enter__ = MagicMock(return_value=mock_fetcher)
        mock_fetcher.__exit__ = MagicMock(return_value=False)

        existing_ids = ["existing-id-1", "existing-id-2"]

        with (
            patch("academic.fetcher.PaperFetcher", return_value=mock_fetcher),
            patch("academic.mapper.map_academic_papers") as mock_mapper,
        ):
            mock_mapper.return_value = {
                "schema_version": "2.1",
                "sources": [],
                "authors": [],
                "relations": {
                    "authored_by": [],
                    "cites": [],
                    "coauthored_with": [],
                },
            }
            args = argparse.Namespace(
                ids_file=str(ids_file),
                output_dir=str(output_dir),
                existing_ids=existing_ids,
                existing_ids_file=None,
            )
            _handle_backfill(args)

            # map_academic_papers に existing_source_ids が渡されることを確認
            call_args = mock_mapper.call_args[0][0]
            assert call_args["existing_source_ids"] == existing_ids

    def test_異常系_IDファイルが存在しない場合エラーコード1(self) -> None:
        """存在しない IDs ファイルが指定された場合、エラーコード 1 を返すことを確認."""
        args = argparse.Namespace(
            ids_file="/nonexistent/path/ids.txt",
            output_dir="/tmp/output",
            existing_ids=None,
            existing_ids_file=None,
        )
        result = _handle_backfill(args)
        assert result == 1

    def test_異常系_IDファイルが空の場合エラーコード1(self, tmp_path: Path) -> None:
        """IDs ファイルが空（有効な ID なし）の場合、エラーコード 1 を返すことを確認."""
        ids_file = tmp_path / "empty.txt"
        ids_file.write_text("# comments only\n\n  \n")

        args = argparse.Namespace(
            ids_file=str(ids_file),
            output_dir=str(tmp_path / "output"),
            existing_ids=None,
            existing_ids_file=None,
        )
        result = _handle_backfill(args)
        assert result == 1

    def test_異常系_fetch失敗でエラーコード1(self, tmp_path: Path) -> None:
        """PaperFetcher がエラーを投げた場合、エラーコード 1 を返すことを確認."""
        ids_file = tmp_path / "ids.txt"
        ids_file.write_text("2301.00001\n")

        mock_fetcher = MagicMock()
        mock_fetcher.fetch_papers_batch.side_effect = RuntimeError("API Error")
        mock_fetcher.__enter__ = MagicMock(return_value=mock_fetcher)
        mock_fetcher.__exit__ = MagicMock(return_value=False)

        with patch("academic.fetcher.PaperFetcher", return_value=mock_fetcher):
            args = argparse.Namespace(
                ids_file=str(ids_file),
                output_dir=str(tmp_path / "output"),
                existing_ids=None,
                existing_ids_file=None,
            )
            result = _handle_backfill(args)

        assert result == 1


class TestMainBackfillIntegration:
    """main() 経由の backfill サブコマンド統合テスト."""

    def test_正常系_main経由でbackfillが実行される(self, tmp_path: Path) -> None:
        """main() 経由で backfill サブコマンドが正しく実行されることを確認."""
        ids_file = tmp_path / "ids.txt"
        ids_file.write_text("2301.00001\n")

        output_dir = tmp_path / "output"

        paper1 = _sample_paper("2301.00001")

        mock_fetcher = MagicMock()
        mock_fetcher.fetch_papers_batch.return_value = [paper1]
        mock_fetcher.__enter__ = MagicMock(return_value=mock_fetcher)
        mock_fetcher.__exit__ = MagicMock(return_value=False)

        with patch("academic.fetcher.PaperFetcher", return_value=mock_fetcher):
            result = main(
                [
                    "backfill",
                    "--ids-file",
                    str(ids_file),
                    "--output-dir",
                    str(output_dir),
                ]
            )

        assert result == 0

    def test_正常系_出力JSONにAUTHORED_BYリレーションが含まれる(
        self, tmp_path: Path
    ) -> None:
        """出力された graph-queue JSON に AUTHORED_BY リレーションが含まれることを確認."""
        ids_file = tmp_path / "ids.txt"
        ids_file.write_text("2301.00001\n")

        output_dir = tmp_path / "output"

        paper1 = _sample_paper("2301.00001")

        mock_fetcher = MagicMock()
        mock_fetcher.fetch_papers_batch.return_value = [paper1]
        mock_fetcher.__enter__ = MagicMock(return_value=mock_fetcher)
        mock_fetcher.__exit__ = MagicMock(return_value=False)

        with patch("academic.fetcher.PaperFetcher", return_value=mock_fetcher):
            main(
                [
                    "backfill",
                    "--ids-file",
                    str(ids_file),
                    "--output-dir",
                    str(output_dir),
                ]
            )

        output_file = output_dir / "graph-queue.json"
        data = json.loads(output_file.read_text(encoding="utf-8"))

        # AUTHORED_BY リレーションが存在する
        assert len(data["relations"]["authored_by"]) == 2  # Alice, Bob

    def test_正常系_出力JSONにCOAUTHORED_WITHリレーションが含まれる(
        self, tmp_path: Path
    ) -> None:
        """出力された graph-queue JSON に COAUTHORED_WITH リレーションが含まれることを確認."""
        ids_file = tmp_path / "ids.txt"
        ids_file.write_text("2301.00001\n")

        output_dir = tmp_path / "output"

        paper1 = _sample_paper("2301.00001")

        mock_fetcher = MagicMock()
        mock_fetcher.fetch_papers_batch.return_value = [paper1]
        mock_fetcher.__enter__ = MagicMock(return_value=mock_fetcher)
        mock_fetcher.__exit__ = MagicMock(return_value=False)

        with patch("academic.fetcher.PaperFetcher", return_value=mock_fetcher):
            main(
                [
                    "backfill",
                    "--ids-file",
                    str(ids_file),
                    "--output-dir",
                    str(output_dir),
                ]
            )

        output_file = output_dir / "graph-queue.json"
        data = json.loads(output_file.read_text(encoding="utf-8"))

        # 2著者 → 1ペアの COAUTHORED_WITH
        assert len(data["relations"]["coauthored_with"]) == 1
