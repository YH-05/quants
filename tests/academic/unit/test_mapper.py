"""academic.mapper の単体テスト.

map_academic_papers() の動作を検証する。
Source, Author, AUTHORED_BY, CITES, COAUTHORED_WITH の生成ロジックを
テストする。
"""

from __future__ import annotations

from typing import Any

from academic.mapper import map_academic_papers
from database.id_generator import generate_author_id, generate_source_id


def _make_paper(
    arxiv_id: str = "2301.00001",
    title: str = "Test Paper",
    authors: list[dict[str, Any]] | None = None,
    references: list[dict[str, Any]] | None = None,
    published: str = "2023-01-15",
) -> dict[str, Any]:
    """テスト用の論文 dict を生成するヘルパー."""
    if authors is None:
        authors = [{"name": "Alice Doe"}, {"name": "Bob Smith"}]
    if references is None:
        references = []
    return {
        "arxiv_id": arxiv_id,
        "title": title,
        "authors": authors,
        "references": references,
        "citations": [],
        "abstract": "Test abstract.",
        "s2_paper_id": None,
        "published": published,
        "updated": None,
    }


class TestMapAcademicPapersSources:
    """Source ノード生成のテスト."""

    def test_正常系_単一論文でSourceとAuthorsとAUTHORED_BYが生成される(
        self,
    ) -> None:
        """1論文から Source 1件 + Author 2件 + AUTHORED_BY 2件が生成されることを確認."""
        data: dict[str, Any] = {
            "papers": [_make_paper()],
            "existing_source_ids": [],
        }

        result = map_academic_papers(data)

        assert len(result["sources"]) == 1
        source = result["sources"][0]
        assert source["source_type"] == "paper"
        assert source["publisher"] == "arXiv"
        assert source["arxiv_id"] == "2301.00001"
        assert source["url"] == "https://arxiv.org/abs/2301.00001"
        assert source["title"] == "Test Paper"
        assert source["published"] == "2023-01-15"

        assert len(result["authors"]) == 2
        assert len(result["relations"]["authored_by"]) == 2

    def test_正常系_SourceのIDがgenerate_source_idと一致する(self) -> None:
        """生成された Source ID が generate_source_id(url) と一致することを確認."""
        data: dict[str, Any] = {
            "papers": [_make_paper(arxiv_id="2303.09406")],
            "existing_source_ids": [],
        }

        result = map_academic_papers(data)

        expected_id = generate_source_id("https://arxiv.org/abs/2303.09406")
        assert result["sources"][0]["id"] == expected_id


class TestMapAcademicPapersAuthors:
    """Author ノード生成のテスト."""

    def test_正常系_AuthorのIDがgenerate_author_idと一致する(self) -> None:
        """生成された Author ID が generate_author_id(name, "academic") と一致することを確認."""
        data: dict[str, Any] = {
            "papers": [_make_paper(authors=[{"name": "Alice Doe"}])],
            "existing_source_ids": [],
        }

        result = map_academic_papers(data)

        expected_id = generate_author_id("Alice Doe", "academic")
        assert result["authors"][0]["id"] == expected_id
        assert result["authors"][0]["author_type"] == "academic"

    def test_正常系_共有著者の重複排除(self) -> None:
        """2論文で同一著者が共有される場合、Author ノードが重複しないことを確認."""
        paper1 = _make_paper(
            arxiv_id="2301.00001",
            authors=[{"name": "Alice"}, {"name": "Bob"}],
        )
        paper2 = _make_paper(
            arxiv_id="2301.00002",
            authors=[{"name": "Alice"}, {"name": "Charlie"}],
        )

        data: dict[str, Any] = {
            "papers": [paper1, paper2],
            "existing_source_ids": [],
        }

        result = map_academic_papers(data)

        # Alice は 1 回だけ Author に登場する
        author_names = [a["name"] for a in result["authors"]]
        assert author_names.count("Alice") == 1
        assert len(result["authors"]) == 3  # Alice, Bob, Charlie

    def test_正常系_名前なし著者はスキップされる(self) -> None:
        """name フィールドが空の著者がスキップされることを確認."""
        data: dict[str, Any] = {
            "papers": [_make_paper(authors=[{"name": ""}, {"name": "Bob"}])],
            "existing_source_ids": [],
        }

        result = map_academic_papers(data)

        assert len(result["authors"]) == 1
        assert result["authors"][0]["name"] == "Bob"


class TestMapAcademicPapersAuthoredBy:
    """AUTHORED_BY リレーション生成のテスト."""

    def test_正常系_AUTHORED_BYのfrom_idがSourceでto_idがAuthor(self) -> None:
        """AUTHORED_BY の from_id が Source ID、to_id が Author ID であることを確認."""
        data: dict[str, Any] = {
            "papers": [_make_paper(authors=[{"name": "Alice"}])],
            "existing_source_ids": [],
        }

        result = map_academic_papers(data)

        rel = result["relations"]["authored_by"][0]
        assert rel["from_id"] == result["sources"][0]["id"]
        assert rel["to_id"] == result["authors"][0]["id"]

    def test_正常系_共有著者でもAUTHORED_BYは各論文ごとに生成される(
        self,
    ) -> None:
        """同一著者が2論文に登場する場合、AUTHORED_BY は2件生成されることを確認."""
        paper1 = _make_paper(
            arxiv_id="2301.00001",
            authors=[{"name": "Alice"}],
        )
        paper2 = _make_paper(
            arxiv_id="2301.00002",
            authors=[{"name": "Alice"}],
        )

        data: dict[str, Any] = {
            "papers": [paper1, paper2],
            "existing_source_ids": [],
        }

        result = map_academic_papers(data)

        # Alice の Author ノードは1つだが、AUTHORED_BY は2件
        assert len(result["authors"]) == 1
        assert len(result["relations"]["authored_by"]) == 2


class TestMapAcademicPapersCites:
    """CITES リレーション生成のテスト."""

    def test_正常系_existing_source_idsに含まれる引用先のみCITESが生成される(
        self,
    ) -> None:
        """existing_source_ids に含まれる引用先のみ CITES が生成されることを確認."""
        known_id = generate_source_id("https://arxiv.org/abs/2001.00001")

        paper = _make_paper(
            references=[
                {"title": "Known Ref", "arxiv_id": "2001.00001", "s2_paper_id": None},
                {
                    "title": "Unknown Ref",
                    "arxiv_id": "9999.99999",
                    "s2_paper_id": None,
                },
            ]
        )

        data: dict[str, Any] = {
            "papers": [paper],
            "existing_source_ids": [known_id],
        }

        result = map_academic_papers(data)

        assert len(result["relations"]["cites"]) == 1
        cite = result["relations"]["cites"][0]
        assert cite["to_id"] == known_id

    def test_正常系_バッチ内の論文間CITESも生成される(self) -> None:
        """同一バッチ内の論文への引用も CITES として生成されることを確認."""
        paper1 = _make_paper(
            arxiv_id="2301.00001",
            references=[],
        )
        paper2 = _make_paper(
            arxiv_id="2301.00002",
            references=[
                {
                    "title": "Paper 1",
                    "arxiv_id": "2301.00001",
                    "s2_paper_id": None,
                }
            ],
        )

        data: dict[str, Any] = {
            "papers": [paper1, paper2],
            "existing_source_ids": [],
        }

        result = map_academic_papers(data)

        assert len(result["relations"]["cites"]) == 1
        cite = result["relations"]["cites"][0]
        expected_from = generate_source_id("https://arxiv.org/abs/2301.00002")
        expected_to = generate_source_id("https://arxiv.org/abs/2301.00001")
        assert cite["from_id"] == expected_from
        assert cite["to_id"] == expected_to

    def test_正常系_arxiv_idがない引用はCITES対象外(self) -> None:
        """arxiv_id が None の引用は CITES 生成をスキップすることを確認."""
        paper = _make_paper(
            references=[
                {"title": "No ArXiv ID", "arxiv_id": None, "s2_paper_id": "s2-001"},
            ]
        )

        data: dict[str, Any] = {
            "papers": [paper],
            "existing_source_ids": [],
        }

        result = map_academic_papers(data)

        assert len(result["relations"]["cites"]) == 0

    def test_正常系_existing_source_idsが空だとバッチ内のみCITES(
        self,
    ) -> None:
        """existing_source_ids が空の場合、バッチ内引用のみ CITES が生成されることを確認."""
        paper = _make_paper(
            references=[
                {
                    "title": "Unknown",
                    "arxiv_id": "9999.99999",
                    "s2_paper_id": None,
                },
            ]
        )

        data: dict[str, Any] = {
            "papers": [paper],
            "existing_source_ids": [],
        }

        result = map_academic_papers(data)

        assert len(result["relations"]["cites"]) == 0


class TestMapAcademicPapersCoauthoredWith:
    """COAUTHORED_WITH リレーション生成のテスト."""

    def test_正常系_2著者で1ペアのCOAUTHORED_WITHが生成される(self) -> None:
        """2著者の論文から 1 ペアの COAUTHORED_WITH が生成されることを確認."""
        data: dict[str, Any] = {
            "papers": [
                _make_paper(authors=[{"name": "Alice"}, {"name": "Bob"}]),
            ],
            "existing_source_ids": [],
        }

        result = map_academic_papers(data)

        assert len(result["relations"]["coauthored_with"]) == 1
        coauth = result["relations"]["coauthored_with"][0]
        assert coauth["paper_count"] == 1
        assert "first_collaboration" in coauth

    def test_正常系_3著者で3ペアのCOAUTHORED_WITHが生成される(self) -> None:
        """3著者の論文から C(3,2)=3 ペアの COAUTHORED_WITH が生成されることを確認."""
        data: dict[str, Any] = {
            "papers": [
                _make_paper(
                    authors=[
                        {"name": "Alice"},
                        {"name": "Bob"},
                        {"name": "Charlie"},
                    ]
                ),
            ],
            "existing_source_ids": [],
        }

        result = map_academic_papers(data)

        assert len(result["relations"]["coauthored_with"]) == 3

    def test_正常系_複数論文で同一ペアのpaper_countが加算される(self) -> None:
        """同一著者ペアが複数論文で共著の場合、paper_count が加算されることを確認."""
        paper1 = _make_paper(
            arxiv_id="2301.00001",
            authors=[{"name": "Alice"}, {"name": "Bob"}],
            published="2023-01-01",
        )
        paper2 = _make_paper(
            arxiv_id="2301.00002",
            authors=[{"name": "Alice"}, {"name": "Bob"}],
            published="2023-06-01",
        )

        data: dict[str, Any] = {
            "papers": [paper1, paper2],
            "existing_source_ids": [],
        }

        result = map_academic_papers(data)

        assert len(result["relations"]["coauthored_with"]) == 1
        coauth = result["relations"]["coauthored_with"][0]
        assert coauth["paper_count"] == 2
        assert coauth["first_collaboration"] == "2023-01-01"

    def test_正常系_単独著者ではCOAUTHORED_WITHは生成されない(self) -> None:
        """1著者の論文では COAUTHORED_WITH が生成されないことを確認."""
        data: dict[str, Any] = {
            "papers": [_make_paper(authors=[{"name": "Alice"}])],
            "existing_source_ids": [],
        }

        result = map_academic_papers(data)

        assert len(result["relations"]["coauthored_with"]) == 0


class TestMapAcademicPapersEdgeCases:
    """エッジケースのテスト."""

    def test_エッジケース_空リストで空キューが返される(self) -> None:
        """空の papers リストで空のキューが返されることを確認."""
        data: dict[str, Any] = {
            "papers": [],
            "existing_source_ids": [],
        }

        result = map_academic_papers(data)

        assert result["sources"] == []
        assert result["authors"] == []
        assert result["relations"]["authored_by"] == []
        assert result["relations"]["cites"] == []
        assert result["relations"]["coauthored_with"] == []

    def test_エッジケース_papersキーが存在しない場合も空キュー(self) -> None:
        """papers キーが存在しない場合も空のキューが返されることを確認."""
        data: dict[str, Any] = {}

        result = map_academic_papers(data)

        assert result["sources"] == []

    def test_エッジケース_arxiv_idがない論文はスキップされる(self) -> None:
        """arxiv_id が空の論文がスキップされることを確認."""
        paper = _make_paper(arxiv_id="")

        data: dict[str, Any] = {
            "papers": [paper],
            "existing_source_ids": [],
        }

        result = map_academic_papers(data)

        assert len(result["sources"]) == 0

    def test_冪等性_同一入力で同一出力(self) -> None:
        """同一入力に対して同一出力が返されることを確認（冪等性）."""
        paper = _make_paper()
        data: dict[str, Any] = {
            "papers": [paper],
            "existing_source_ids": [],
        }

        result1 = map_academic_papers(data)
        result2 = map_academic_papers(data)

        # queue_id と created_at はランダム/時刻なので除外して比較
        for key in ("queue_id", "created_at"):
            result1.pop(key, None)
            result2.pop(key, None)

        assert result1 == result2

    def test_正常系_schema_versionが2_1(self) -> None:
        """schema_version が '2.1' であることを確認."""
        data: dict[str, Any] = {
            "papers": [],
            "existing_source_ids": [],
        }

        result = map_academic_papers(data)

        assert result["schema_version"] == "2.1"

    def test_正常系_command_sourceがacademic_fetch(self) -> None:
        """command_source が 'academic-fetch' であることを確認."""
        data: dict[str, Any] = {
            "papers": [],
            "existing_source_ids": [],
        }

        result = map_academic_papers(data)

        assert result["command_source"] == "academic-fetch"
