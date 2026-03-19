#!/usr/bin/env python3
"""Migrate legacy ``auth-*`` Author nodes to UUID5-based IDs.

Reads existing Author nodes whose ``id`` starts with ``auth-`` from Neo4j,
computes the deterministic UUID5 ID via
:func:`database.id_generator.generate_author_id`, and replaces them
using MERGE + DELETE Cypher statements.

Usage
-----
::

    # Dry-run (default) -- shows planned changes without writing
    uv run python scripts/migrate_author_ids.py

    # Execute migration
    uv run python scripts/migrate_author_ids.py --execute

    # Custom Neo4j URI
    uv run python scripts/migrate_author_ids.py --execute --neo4j-uri bolt://nas:7687
"""

from __future__ import annotations

import argparse
import os
import sys
from typing import Any

from database.id_generator import generate_author_id
from utils_core.logging import get_logger

logger = get_logger(__name__)

# Default Neo4j connection settings
DEFAULT_NEO4J_URI = "bolt://localhost:7687"
DEFAULT_NEO4J_USER = "neo4j"

# Cypher to fetch legacy Author nodes with ``auth-*`` IDs
_FETCH_LEGACY_AUTHORS = """
MATCH (a:Author)
WHERE a.id STARTS WITH 'auth-'
RETURN a.id AS old_id, a.name AS name, a.author_type AS author_type,
       properties(a) AS props
"""

# Migration Cypher without APOC dependency -- copies properties and deletes
# the old node.  DETACH DELETE removes all relationships on the old node.
# AIDEV-NOTE: Relationships are NOT migrated to the new node.  Run this only
# when Author nodes have no critical relationships, or use APOC-based migration.
_MIGRATE_AUTHOR_SIMPLE = """
MATCH (old:Author {id: $old_id})
MERGE (new:Author {id: $new_id})
SET new += $props
SET new.id = $new_id
WITH old, new
OPTIONAL MATCH (old)-[r_out]->()
WITH old, new, collect(r_out) AS outs
OPTIONAL MATCH ()-[r_in]->(old)
WITH old, new, outs, collect(r_in) AS ins
DETACH DELETE old
RETURN new.id AS new_id
"""


def _build_parser() -> argparse.ArgumentParser:
    """Build the CLI argument parser.

    Returns
    -------
    argparse.ArgumentParser
        Configured parser.
    """
    parser = argparse.ArgumentParser(
        description="Migrate legacy auth-* Author node IDs to UUID5.",
    )
    parser.add_argument(
        "--execute",
        action="store_true",
        help="Actually execute the migration. Default is dry-run.",
    )
    parser.add_argument(
        "--neo4j-uri",
        default=DEFAULT_NEO4J_URI,
        help=f"Neo4j bolt URI (default: {DEFAULT_NEO4J_URI}).",
    )
    parser.add_argument(
        "--neo4j-user",
        default=DEFAULT_NEO4J_USER,
        help=f"Neo4j username (default: {DEFAULT_NEO4J_USER}).",
    )
    parser.add_argument(
        "--neo4j-password",
        default=os.environ.get("NEO4J_PASSWORD"),
        help="Neo4j password (or set NEO4J_PASSWORD env var).",
    )
    return parser


def compute_migration_plan(
    legacy_authors: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Compute the ID migration plan for legacy Author nodes.

    For each legacy author, computes the new UUID5-based ID using
    :func:`database.id_generator.generate_author_id`.

    Parameters
    ----------
    legacy_authors : list[dict[str, Any]]
        List of dicts with keys ``old_id``, ``name``, ``author_type``,
        ``props``.

    Returns
    -------
    list[dict[str, Any]]
        Migration plan entries with ``old_id``, ``new_id``, ``name``,
        ``author_type``, ``props``.
    """
    plan: list[dict[str, Any]] = []
    for author in legacy_authors:
        old_id: str = author["old_id"]
        name: str = author.get("name", "")
        author_type: str = author.get("author_type", "academic")

        if not name:
            logger.warning(
                "Skipping author with empty name",
                old_id=old_id,
            )
            continue

        new_id = generate_author_id(name, author_type)

        if old_id == new_id:
            logger.debug(
                "Author already has correct ID, skipping",
                old_id=old_id,
            )
            continue

        props = dict(author.get("props", {}))
        # Remove the old id from props so SET new += $props doesn't overwrite
        props.pop("id", None)

        plan.append(
            {
                "old_id": old_id,
                "new_id": new_id,
                "name": name,
                "author_type": author_type,
                "props": props,
            }
        )
        logger.debug(
            "Planned migration",
            old_id=old_id,
            new_id=new_id,
            name=name,
        )

    return plan


def execute_migration(
    driver: Any,
    plan: list[dict[str, Any]],
    *,
    database: str = "neo4j",
) -> int:
    """Execute the migration plan against Neo4j.

    Parameters
    ----------
    driver : neo4j.Driver
        Neo4j driver instance.
    plan : list[dict[str, Any]]
        Migration plan from :func:`compute_migration_plan`.
    database : str, optional
        Neo4j database name (default ``"neo4j"``).

    Returns
    -------
    int
        Number of nodes successfully migrated.
    """
    migrated = 0
    with driver.session(database=database) as session:
        for entry in plan:
            try:
                result = session.run(
                    _MIGRATE_AUTHOR_SIMPLE,
                    old_id=entry["old_id"],
                    new_id=entry["new_id"],
                    props=entry["props"],
                )
                record = result.single()
                if record:
                    migrated += 1
                    logger.info(
                        "Migrated author",
                        old_id=entry["old_id"],
                        new_id=entry["new_id"],
                        name=entry["name"],
                    )
                else:
                    logger.warning(
                        "Migration returned no result",
                        old_id=entry["old_id"],
                    )
            except Exception as exc:
                logger.error(
                    "Failed to migrate author",
                    old_id=entry["old_id"],
                    error=str(exc),
                    exc_info=True,
                )
    return migrated


def main(argv: list[str] | None = None) -> int:
    """Entry point for the migration CLI.

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

    if not args.neo4j_password:
        logger.error("Neo4j password is required")
        print(
            "Error: Neo4j password is required. "
            "Set --neo4j-password or NEO4J_PASSWORD env var.",
            file=sys.stderr,
        )
        return 1

    try:
        from neo4j import GraphDatabase  # type: ignore[import-untyped]
    except ImportError:
        logger.error("neo4j driver not installed. Install with: uv add neo4j")
        print(
            "Error: neo4j driver not installed. Install with: uv add neo4j",
            file=sys.stderr,
        )
        return 1

    logger.info(
        "Connecting to Neo4j",
        uri=args.neo4j_uri,
        user=args.neo4j_user,
    )

    try:
        driver = GraphDatabase.driver(
            args.neo4j_uri,
            auth=(args.neo4j_user, args.neo4j_password),
        )
        driver.verify_connectivity()
    except Exception as exc:
        logger.error("Failed to connect to Neo4j", error=str(exc))
        print(
            "Error: Failed to connect to Neo4j. See logs for details.",
            file=sys.stderr,
        )
        return 1

    try:
        # Fetch legacy authors
        with driver.session() as session:
            result = session.run(_FETCH_LEGACY_AUTHORS)
            legacy_authors = [dict(record) for record in result]

        logger.info(
            "Found legacy Author nodes",
            count=len(legacy_authors),
        )

        if not legacy_authors:
            print("No legacy auth-* Author nodes found. Nothing to migrate.")
            return 0

        # Compute migration plan
        plan = compute_migration_plan(legacy_authors)
        logger.info("Migration plan computed", planned_count=len(plan))

        # Display plan
        print(f"\nMigration plan: {len(plan)} nodes to migrate\n")
        for entry in plan:
            print(f"  {entry['old_id']} -> {entry['new_id']}  ({entry['name']})")

        if not args.execute:
            print("\nDry-run mode. Use --execute to apply changes.")
            return 0

        # Execute
        print("\nExecuting migration...")
        migrated = execute_migration(driver, plan)
        print(f"\nMigration complete: {migrated}/{len(plan)} nodes migrated.")
        logger.info(
            "Migration finished",
            migrated=migrated,
            total=len(plan),
        )
        return 0

    finally:
        driver.close()


if __name__ == "__main__":
    sys.exit(main())
