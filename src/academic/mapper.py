"""PaperMetadata -> graph-queue JSON マッパー.

PaperMetadata のリストを KG v2.1 graph-queue 形式に変換する。
Source, Author, AUTHORED_BY, CITES, COAUTHORED_WITH ノード・リレーションを生成する。

主な機能
--------
- ``map_academic_papers(data)`` : 論文リストを graph-queue JSON に変換
- Source ノード: ``source_type="paper"``, ``publisher="arXiv"``
- Author ノード: ``author_type="academic"``
- AUTHORED_BY: Source -> Author（各論文の著者全員）
- CITES: existing_source_ids に含まれる引用先のみ
- COAUTHORED_WITH: 同一論文の著者ペア

Examples
--------
>>> from academic.mapper import map_academic_papers
>>> data = {"papers": [], "existing_source_ids": []}
>>> result = map_academic_papers(data)
>>> result["sources"]
[]
"""

from __future__ import annotations

from itertools import combinations
from typing import Any

from database.id_generator import generate_author_id, generate_source_id
from utils_core.logging import get_logger

logger = get_logger(__name__)


def map_academic_papers(data: dict[str, Any]) -> dict[str, Any]:
    """Map academic papers to graph-queue format.

    Input: ``{"papers": [...], "existing_source_ids": [...]}``
    where each paper is a serialized PaperMetadata dict.

    Creates: Source + Author nodes
    Relations: AUTHORED_BY, CITES, COAUTHORED_WITH

    Parameters
    ----------
    data : dict[str, Any]
        Parsed JSON with keys ``papers`` (list of paper dicts) and
        ``existing_source_ids`` (list of known source IDs for CITES
        filtering).

    Returns
    -------
    dict[str, Any]
        Complete graph-queue dict with sources, authors, and relations.
    """
    papers: list[dict[str, Any]] = data.get("papers", [])
    existing_source_ids: list[str] = data.get("existing_source_ids", [])
    existing_set = set(existing_source_ids)

    queue = _empty_academic_queue(data.get("_input_path", ""))

    if not papers:
        logger.warning("No papers found in academic input")
        return queue

    # Track authors for deduplication
    seen_authors: dict[str, str] = {}  # author_key -> author_id

    # Track generated source IDs for CITES self-references
    generated_source_ids: set[str] = set()

    # Track coauthor pairs for COAUTHORED_WITH
    coauthor_pairs: dict[tuple[str, str], _CoauthorInfo] = {}

    for paper in papers:
        arxiv_id = paper.get("arxiv_id", "")
        title = paper.get("title", "")
        published = paper.get("published", "")

        if not arxiv_id:
            logger.warning("Paper missing arxiv_id, skipping", title=title)
            continue

        # Source node
        url = f"https://arxiv.org/abs/{arxiv_id}"
        source_id = generate_source_id(url)
        generated_source_ids.add(source_id)

        queue["sources"].append(
            {
                "id": source_id,
                "url": url,
                "title": title,
                "published": published,
                "source_type": "paper",
                "publisher": "arXiv",
                "arxiv_id": arxiv_id,
            }
        )

        # Authors and AUTHORED_BY
        authors_data: list[dict[str, Any]] = paper.get("authors", [])
        paper_author_ids: list[str] = []

        for author_data in authors_data:
            name = author_data.get("name", "")
            if not name:
                continue

            author_key = f"{name}:academic"
            if author_key not in seen_authors:
                author_id = generate_author_id(name, "academic")
                seen_authors[author_key] = author_id
                queue["authors"].append(
                    {
                        "id": author_id,
                        "name": name,
                        "author_type": "academic",
                    }
                )
            else:
                author_id = seen_authors[author_key]

            paper_author_ids.append(author_id)

            # AUTHORED_BY relation
            queue["relations"]["authored_by"].append(
                {
                    "from_id": source_id,
                    "to_id": author_id,
                }
            )

        # CITES: only references whose source_id is in existing_source_ids
        # or in generated_source_ids (papers within this batch)
        references: list[dict[str, Any]] = paper.get("references", [])
        for ref in references:
            ref_arxiv_id = ref.get("arxiv_id")
            if not ref_arxiv_id:
                continue

            ref_url = f"https://arxiv.org/abs/{ref_arxiv_id}"
            ref_source_id = generate_source_id(ref_url)

            if ref_source_id in existing_set or ref_source_id in generated_source_ids:
                queue["relations"]["cites"].append(
                    {
                        "from_id": source_id,
                        "to_id": ref_source_id,
                    }
                )

        # COAUTHORED_WITH: pairs of authors in this paper
        unique_author_ids = list(dict.fromkeys(paper_author_ids))
        for a_id, b_id in combinations(unique_author_ids, 2):
            pair_key = (min(a_id, b_id), max(a_id, b_id))
            if pair_key not in coauthor_pairs:
                coauthor_pairs[pair_key] = _CoauthorInfo(
                    paper_count=1,
                    first_collaboration=published,
                )
            else:
                coauthor_pairs[pair_key].paper_count += 1

    # Emit COAUTHORED_WITH relations
    for (a_id, b_id), info in coauthor_pairs.items():
        queue["relations"]["coauthored_with"].append(
            {
                "from_id": a_id,
                "to_id": b_id,
                "paper_count": info.paper_count,
                "first_collaboration": info.first_collaboration,
            }
        )

    logger.info(
        "Mapped academic papers",
        paper_count=len(papers),
        source_count=len(queue["sources"]),
        author_count=len(queue["authors"]),
        authored_by_count=len(queue["relations"]["authored_by"]),
        cites_count=len(queue["relations"]["cites"]),
        coauthored_with_count=len(queue["relations"]["coauthored_with"]),
    )
    return queue


class _CoauthorInfo:
    """Internal tracker for coauthor pair metadata."""

    __slots__ = ("first_collaboration", "paper_count")

    def __init__(self, paper_count: int, first_collaboration: str) -> None:
        self.paper_count = paper_count
        self.first_collaboration = first_collaboration


def _empty_academic_queue(input_path: str) -> dict[str, Any]:
    """Create an empty graph-queue structure for academic papers.

    This is a minimal queue structure containing only the node/relation
    types used by the academic mapper.

    Parameters
    ----------
    input_path : str
        Path to the input file for traceability.

    Returns
    -------
    dict[str, Any]
        Empty academic graph-queue dict.
    """
    # Import here to avoid circular dependency at module level
    import secrets
    from datetime import datetime, timezone

    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S")
    rand8 = secrets.token_hex(4)
    queue_id = f"gq-{timestamp}-{rand8}"

    now = datetime.now(timezone.utc)

    return {
        "schema_version": "2.1",
        "queue_id": queue_id,
        "created_at": now.isoformat(),
        "command_source": "academic-fetch",
        "input_path": input_path,
        "sources": [],
        "entities": [],
        "claims": [],
        "facts": [],
        "topics": [],
        "authors": [],
        "financial_datapoints": [],
        "fiscal_periods": [],
        "insights": [],
        "anomalies": [],
        "performance_evidences": [],
        "market_regimes": [],
        "data_requirements": [],
        "relations": {
            "tagged": [],
            "makes_claim": [],
            "states_fact": [],
            "about": [],
            "relates_to": [],
            "has_datapoint": [],
            "for_period": [],
            "supported_by": [],
            "authored_by": [],
            "exploits": [],
            "evaluates": [],
            "quantified_by": [],
            "effective_in": [],
            "requires_data": [],
            "explained_by": [],
            "measured_in": [],
            "competes_with": [],
            "extends_method": [],
            "combined_with": [],
            "uses_method": [],
            "cites": [],
            "coauthored_with": [],
        },
    }


__all__ = ["map_academic_papers"]
