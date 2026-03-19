"""Tests for scripts/migrate_author_ids.py migration logic."""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

# Add scripts to path for import
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts"))

from migrate_author_ids import compute_migration_plan  # type: ignore[import-not-found]

from database.id_generator import generate_author_id


class TestComputeMigrationPlan:
    """Tests for compute_migration_plan function."""

    def test_正常系_auth_prefixのIDをUUID5に変換(self) -> None:
        legacy_authors: list[dict[str, Any]] = [
            {
                "old_id": "auth-john-smith",
                "name": "John Smith",
                "author_type": "academic",
                "props": {
                    "id": "auth-john-smith",
                    "name": "John Smith",
                    "author_type": "academic",
                },
            },
        ]
        plan = compute_migration_plan(legacy_authors)

        assert len(plan) == 1
        entry = plan[0]
        assert entry["old_id"] == "auth-john-smith"
        expected_new_id = generate_author_id("John Smith", "academic")
        assert entry["new_id"] == expected_new_id
        assert entry["name"] == "John Smith"
        assert entry["author_type"] == "academic"
        # props should not contain 'id' key
        assert "id" not in entry["props"]

    def test_正常系_複数AuthorノードをすべてUUID5に変換(self) -> None:
        legacy_authors: list[dict[str, Any]] = [
            {
                "old_id": "auth-alice",
                "name": "Alice",
                "author_type": "academic",
                "props": {
                    "id": "auth-alice",
                    "name": "Alice",
                    "author_type": "academic",
                },
            },
            {
                "old_id": "auth-bob",
                "name": "Bob",
                "author_type": "sell_side",
                "props": {"id": "auth-bob", "name": "Bob", "author_type": "sell_side"},
            },
        ]
        plan = compute_migration_plan(legacy_authors)

        assert len(plan) == 2
        assert plan[0]["new_id"] == generate_author_id("Alice", "academic")
        assert plan[1]["new_id"] == generate_author_id("Bob", "sell_side")

    def test_正常系_空リストで空プランを返す(self) -> None:
        plan = compute_migration_plan([])
        assert plan == []

    def test_正常系_name欠落のAuthorをスキップ(self) -> None:
        legacy_authors: list[dict[str, Any]] = [
            {
                "old_id": "auth-no-name",
                "name": "",
                "author_type": "academic",
                "props": {"id": "auth-no-name"},
            },
        ]
        plan = compute_migration_plan(legacy_authors)
        assert len(plan) == 0

    def test_正常系_author_type未指定でacademicデフォルト(self) -> None:
        legacy_authors: list[dict[str, Any]] = [
            {
                "old_id": "auth-default-type",
                "name": "Default Author",
                "props": {"id": "auth-default-type", "name": "Default Author"},
            },
        ]
        plan = compute_migration_plan(legacy_authors)

        assert len(plan) == 1
        expected_new_id = generate_author_id("Default Author", "academic")
        assert plan[0]["new_id"] == expected_new_id
        assert plan[0]["author_type"] == "academic"

    def test_正常系_決定論的IDを生成(self) -> None:
        """Same input produces same output (idempotent)."""
        legacy_authors: list[dict[str, Any]] = [
            {
                "old_id": "auth-deterministic",
                "name": "Test Author",
                "author_type": "academic",
                "props": {"id": "auth-deterministic", "name": "Test Author"},
            },
        ]
        plan1 = compute_migration_plan(legacy_authors)
        plan2 = compute_migration_plan(legacy_authors)
        assert plan1[0]["new_id"] == plan2[0]["new_id"]

    def test_正常系_propsからidキーが除去される(self) -> None:
        legacy_authors: list[dict[str, Any]] = [
            {
                "old_id": "auth-prop-cleanup",
                "name": "Prop Author",
                "author_type": "academic",
                "props": {
                    "id": "auth-prop-cleanup",
                    "name": "Prop Author",
                    "author_type": "academic",
                    "affiliation": "MIT",
                },
            },
        ]
        plan = compute_migration_plan(legacy_authors)

        assert len(plan) == 1
        assert "id" not in plan[0]["props"]
        assert plan[0]["props"]["affiliation"] == "MIT"
        assert plan[0]["props"]["name"] == "Prop Author"
