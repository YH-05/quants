"""academic.mapper のプロパティベーステスト.

Hypothesis を使用して map_academic_papers() の不変条件を検証する。

不変条件
--------
- authored_by.to_id は全て authors.id の部分集合
- cites.to_id は全て existing_source_ids union sources.id の部分集合
- coauthored_with のペアはユニーク
"""

from __future__ import annotations

from typing import Any

from hypothesis import given, settings
from hypothesis import strategies as st

from academic.mapper import map_academic_papers
from database.id_generator import generate_source_id

# ---------------------------------------------------------------------------
# Strategies
# ---------------------------------------------------------------------------

author_name_st = st.text(
    alphabet=st.characters(whitelist_categories=("L", "N", "Z")),
    min_size=1,
    max_size=30,
).filter(lambda s: s.strip() != "")

author_st = st.fixed_dictionaries({"name": author_name_st})

reference_st = st.fixed_dictionaries(
    {
        "title": st.text(min_size=1, max_size=50),
        "arxiv_id": st.one_of(
            st.none(),
            st.from_regex(r"[0-9]{4}\.[0-9]{5}", fullmatch=True),
        ),
        "s2_paper_id": st.none(),
    }
)

paper_st = st.fixed_dictionaries(
    {
        "arxiv_id": st.from_regex(r"[0-9]{4}\.[0-9]{5}", fullmatch=True),
        "title": st.text(min_size=1, max_size=100),
        "authors": st.lists(author_st, min_size=0, max_size=5),
        "references": st.lists(reference_st, min_size=0, max_size=5),
        "citations": st.just([]),
        "abstract": st.text(max_size=200),
        "s2_paper_id": st.none(),
        "published": st.just("2023-01-15"),
        "updated": st.none(),
    }
)


def _make_existing_source_ids(
    papers: list[dict[str, Any]],
) -> list[str]:
    """テスト用に一部の既知 source_id を生成する.

    入力論文の references から arxiv_id を抽出し、
    それらの一部を existing_source_ids として返す。
    """
    ref_arxiv_ids: list[str] = []
    for paper in papers:
        for ref in paper.get("references", []):
            aid = ref.get("arxiv_id")
            if aid:
                ref_arxiv_ids.append(aid)
    # 半分を既知として返す
    half = len(ref_arxiv_ids) // 2
    return [
        generate_source_id(f"https://arxiv.org/abs/{aid}")
        for aid in ref_arxiv_ids[:half]
    ]


# ---------------------------------------------------------------------------
# Property Tests
# ---------------------------------------------------------------------------


class TestMapperProperties:
    """map_academic_papers の不変条件テスト."""

    @given(papers=st.lists(paper_st, min_size=0, max_size=5))
    @settings(max_examples=50, deadline=None)
    def test_プロパティ_authored_byのto_idがauthorsのidに含まれる(
        self,
        papers: list[dict[str, Any]],
    ) -> None:
        """authored_by.to_id が全て authors.id の部分集合であることを確認."""
        data: dict[str, Any] = {
            "papers": papers,
            "existing_source_ids": _make_existing_source_ids(papers),
        }

        result = map_academic_papers(data)

        author_ids = {a["id"] for a in result["authors"]}
        for rel in result["relations"]["authored_by"]:
            assert rel["to_id"] in author_ids, (
                f"authored_by.to_id {rel['to_id']} not in authors"
            )

    @given(papers=st.lists(paper_st, min_size=0, max_size=5))
    @settings(max_examples=50, deadline=None)
    def test_プロパティ_authored_byのfrom_idがsourcesのidに含まれる(
        self,
        papers: list[dict[str, Any]],
    ) -> None:
        """authored_by.from_id が全て sources.id の部分集合であることを確認."""
        data: dict[str, Any] = {
            "papers": papers,
            "existing_source_ids": _make_existing_source_ids(papers),
        }

        result = map_academic_papers(data)

        source_ids = {s["id"] for s in result["sources"]}
        for rel in result["relations"]["authored_by"]:
            assert rel["from_id"] in source_ids, (
                f"authored_by.from_id {rel['from_id']} not in sources"
            )

    @given(papers=st.lists(paper_st, min_size=0, max_size=5))
    @settings(max_examples=50, deadline=None)
    def test_プロパティ_citesのto_idがexisting_source_idsまたはsourcesのidに含まれる(
        self,
        papers: list[dict[str, Any]],
    ) -> None:
        """cites.to_id が existing_source_ids union sources.id の部分集合であることを確認."""
        existing = _make_existing_source_ids(papers)
        data: dict[str, Any] = {
            "papers": papers,
            "existing_source_ids": existing,
        }

        result = map_academic_papers(data)

        allowed_ids = {s["id"] for s in result["sources"]} | set(existing)
        for rel in result["relations"]["cites"]:
            assert rel["to_id"] in allowed_ids, (
                f"cites.to_id {rel['to_id']} not in allowed set"
            )

    @given(papers=st.lists(paper_st, min_size=0, max_size=5))
    @settings(max_examples=50, deadline=None)
    def test_プロパティ_coauthored_withのペアがユニーク(
        self,
        papers: list[dict[str, Any]],
    ) -> None:
        """coauthored_with のペアが全てユニークであることを確認."""
        data: dict[str, Any] = {
            "papers": papers,
            "existing_source_ids": [],
        }

        result = map_academic_papers(data)

        pairs = set()
        for rel in result["relations"]["coauthored_with"]:
            pair = (
                min(rel["from_id"], rel["to_id"]),
                max(rel["from_id"], rel["to_id"]),
            )
            assert pair not in pairs, f"Duplicate coauthored_with pair: {pair}"
            pairs.add(pair)

    @given(papers=st.lists(paper_st, min_size=0, max_size=5))
    @settings(max_examples=50, deadline=None)
    def test_プロパティ_coauthored_withのpaper_countが1以上(
        self,
        papers: list[dict[str, Any]],
    ) -> None:
        """coauthored_with の paper_count が全て 1 以上であることを確認."""
        data: dict[str, Any] = {
            "papers": papers,
            "existing_source_ids": [],
        }

        result = map_academic_papers(data)

        for rel in result["relations"]["coauthored_with"]:
            assert rel["paper_count"] >= 1, f"paper_count < 1: {rel['paper_count']}"

    @given(papers=st.lists(paper_st, min_size=0, max_size=5))
    @settings(max_examples=50, deadline=None)
    def test_プロパティ_coauthored_withのノードIDがauthorsに含まれる(
        self,
        papers: list[dict[str, Any]],
    ) -> None:
        """coauthored_with の from_id/to_id が全て authors.id に含まれることを確認."""
        data: dict[str, Any] = {
            "papers": papers,
            "existing_source_ids": [],
        }

        result = map_academic_papers(data)

        author_ids = {a["id"] for a in result["authors"]}
        for rel in result["relations"]["coauthored_with"]:
            assert rel["from_id"] in author_ids, (
                f"coauthored_with.from_id {rel['from_id']} not in authors"
            )
            assert rel["to_id"] in author_ids, (
                f"coauthored_with.to_id {rel['to_id']} not in authors"
            )
