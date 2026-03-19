"""_handle_fetch() サブコマンドの単体テスト.

fetch サブコマンドが arXiv ID を受け取り、PaperFetcher で取得して
JSON ファイルに出力する処理を検証する。
モックベースで実 API に接続しない。
"""

from __future__ import annotations

import argparse
import json
from typing import TYPE_CHECKING, Any
from unittest.mock import MagicMock, patch

import pytest

from academic.__main__ import _handle_fetch, main
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


class TestHandleFetch:
    """_handle_fetch() の単体テスト."""

    def test_正常系_単一IDで論文を取得してJSONを出力する(self, tmp_path: Path) -> None:
        """単一の arXiv ID で論文を取得し、JSON ファイルに出力することを確認."""
        output_dir = tmp_path / "output"

        paper = _sample_paper("2301.00001")

        mock_fetcher = MagicMock()
        mock_fetcher.fetch_paper.return_value = paper
        mock_fetcher.__enter__ = MagicMock(return_value=mock_fetcher)
        mock_fetcher.__exit__ = MagicMock(return_value=False)

        with patch("academic.fetcher.PaperFetcher", return_value=mock_fetcher):
            args = argparse.Namespace(
                arxiv_id="2301.00001",
                arxiv_ids=None,
                output_dir=str(output_dir),
            )
            result = _handle_fetch(args)

        assert result == 0
        output_file = output_dir / "papers.json"
        assert output_file.exists()

        data = json.loads(output_file.read_text(encoding="utf-8"))
        assert len(data["papers"]) == 1
        assert data["papers"][0]["arxiv_id"] == "2301.00001"
        assert data["papers"][0]["title"] == "Sample Paper 2301.00001"

    def test_正常系_複数IDでバッチ取得してJSONを出力する(self, tmp_path: Path) -> None:
        """複数の arXiv ID でバッチ取得し、JSON ファイルに出力することを確認."""
        output_dir = tmp_path / "output"

        paper1 = _sample_paper("2301.00001")
        paper2 = _sample_paper("2301.00002")

        mock_fetcher = MagicMock()
        mock_fetcher.fetch_papers_batch.return_value = [paper1, paper2]
        mock_fetcher.__enter__ = MagicMock(return_value=mock_fetcher)
        mock_fetcher.__exit__ = MagicMock(return_value=False)

        with patch("academic.fetcher.PaperFetcher", return_value=mock_fetcher):
            args = argparse.Namespace(
                arxiv_id=None,
                arxiv_ids=["2301.00001", "2301.00002"],
                output_dir=str(output_dir),
            )
            result = _handle_fetch(args)

        assert result == 0
        output_file = output_dir / "papers.json"
        assert output_file.exists()

        data = json.loads(output_file.read_text(encoding="utf-8"))
        assert len(data["papers"]) == 2
        assert data["papers"][0]["arxiv_id"] == "2301.00001"
        assert data["papers"][1]["arxiv_id"] == "2301.00002"

    def test_異常系_IDなしでエラーコード1を返す(self, tmp_path: Path) -> None:
        """arXiv ID が指定されていない場合、エラーコード 1 を返すことを確認."""
        args = argparse.Namespace(
            arxiv_id=None,
            arxiv_ids=None,
            output_dir=str(tmp_path / "output"),
        )
        result = _handle_fetch(args)
        assert result == 1

    def test_異常系_fetch失敗でエラーコード1を返す(self, tmp_path: Path) -> None:
        """PaperFetcher がエラーを投げた場合、エラーコード 1 を返すことを確認."""
        mock_fetcher = MagicMock()
        mock_fetcher.fetch_paper.side_effect = RuntimeError("API Error")
        mock_fetcher.__enter__ = MagicMock(return_value=mock_fetcher)
        mock_fetcher.__exit__ = MagicMock(return_value=False)

        with patch("academic.fetcher.PaperFetcher", return_value=mock_fetcher):
            args = argparse.Namespace(
                arxiv_id="2301.00001",
                arxiv_ids=None,
                output_dir=str(tmp_path / "output"),
            )
            result = _handle_fetch(args)

        assert result == 1

    def test_正常系_出力JSONに著者と引用情報が含まれる(self, tmp_path: Path) -> None:
        """出力された JSON に著者・引用情報が含まれることを確認."""
        output_dir = tmp_path / "output"

        paper = _sample_paper("2301.00001")

        mock_fetcher = MagicMock()
        mock_fetcher.fetch_paper.return_value = paper
        mock_fetcher.__enter__ = MagicMock(return_value=mock_fetcher)
        mock_fetcher.__exit__ = MagicMock(return_value=False)

        with patch("academic.fetcher.PaperFetcher", return_value=mock_fetcher):
            args = argparse.Namespace(
                arxiv_id="2301.00001",
                arxiv_ids=None,
                output_dir=str(output_dir),
            )
            _handle_fetch(args)

        output_file = output_dir / "papers.json"
        data = json.loads(output_file.read_text(encoding="utf-8"))

        paper_data = data["papers"][0]
        assert len(paper_data["authors"]) == 2
        assert paper_data["authors"][0]["name"] == "Alice Doe"
        assert len(paper_data["references"]) == 1
        assert paper_data["references"][0]["title"] == "Ref Paper"


class TestMainFetchIntegration:
    """main() 経由の fetch サブコマンド統合テスト."""

    def test_正常系_main経由で単一fetchが実行される(self, tmp_path: Path) -> None:
        """main() 経由で fetch --arxiv-id が正しく実行されることを確認."""
        output_dir = tmp_path / "output"

        paper = _sample_paper("2301.00001")

        mock_fetcher = MagicMock()
        mock_fetcher.fetch_paper.return_value = paper
        mock_fetcher.__enter__ = MagicMock(return_value=mock_fetcher)
        mock_fetcher.__exit__ = MagicMock(return_value=False)

        with patch("academic.fetcher.PaperFetcher", return_value=mock_fetcher):
            result = main(
                [
                    "fetch",
                    "--arxiv-id",
                    "2301.00001",
                    "--output-dir",
                    str(output_dir),
                ]
            )

        assert result == 0
        output_file = output_dir / "papers.json"
        assert output_file.exists()

    def test_正常系_main経由で複数fetchが実行される(self, tmp_path: Path) -> None:
        """main() 経由で fetch --arxiv-ids が正しく実行されることを確認."""
        output_dir = tmp_path / "output"

        paper1 = _sample_paper("2301.00001")
        paper2 = _sample_paper("2301.00002")

        mock_fetcher = MagicMock()
        mock_fetcher.fetch_papers_batch.return_value = [paper1, paper2]
        mock_fetcher.__enter__ = MagicMock(return_value=mock_fetcher)
        mock_fetcher.__exit__ = MagicMock(return_value=False)

        with patch("academic.fetcher.PaperFetcher", return_value=mock_fetcher):
            result = main(
                [
                    "fetch",
                    "--arxiv-ids",
                    "2301.00001",
                    "2301.00002",
                    "--output-dir",
                    str(output_dir),
                ]
            )

        assert result == 0
        output_file = output_dir / "papers.json"
        data = json.loads(output_file.read_text(encoding="utf-8"))
        assert len(data["papers"]) == 2
