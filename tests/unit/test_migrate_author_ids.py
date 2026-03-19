"""Tests for scripts/migrate_author_ids.py migration logic.

compute_migration_plan() の単体テストと execute_migration() のモックベーステスト。
実 Neo4j には接続しない。
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock

# Add scripts to path for import
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts"))

from migrate_author_ids import (  # type: ignore[import-not-found]
    compute_migration_plan,
    execute_migration,
)

from database.id_generator import generate_author_id


class TestComputeMigrationPlan:
    """compute_migration_plan() の単体テスト."""

    def test_正常系_auth_prefixのIDをUUID5に変換(self) -> None:
        """auth- プレフィックスの ID を UUID5 ベースに変換できることを確認."""
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
        """複数 Author ノードを全て UUID5 ベースに変換できることを確認."""
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
        """空リスト入力で空のプランを返すことを確認."""
        plan = compute_migration_plan([])
        assert plan == []

    def test_正常系_name欠落のAuthorをスキップ(self) -> None:
        """name が空の Author をスキップすることを確認."""
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
        """author_type 未指定時に academic がデフォルトになることを確認."""
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
        """同一入力で同一出力が得られること（冪等性）を確認."""
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
        """props から id キーが除去されることを確認."""
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


class TestExecuteMigration:
    """execute_migration() のモックベーステスト.

    実 Neo4j には接続せず、driver/session をモックして
    Cypher 実行ロジックを検証する。
    """

    def test_正常系_プラン全件が正常に移行される(self) -> None:
        """全エントリが正常に移行され、移行件数が返ることを確認."""
        plan: list[dict[str, Any]] = [
            {
                "old_id": "auth-alice",
                "new_id": "uuid5-alice",
                "name": "Alice",
                "author_type": "academic",
                "props": {"name": "Alice"},
            },
            {
                "old_id": "auth-bob",
                "new_id": "uuid5-bob",
                "name": "Bob",
                "author_type": "academic",
                "props": {"name": "Bob"},
            },
        ]

        mock_record = MagicMock()
        mock_result = MagicMock()
        mock_result.single.return_value = mock_record

        mock_session = MagicMock()
        mock_session.run.return_value = mock_result
        mock_session.__enter__ = MagicMock(return_value=mock_session)
        mock_session.__exit__ = MagicMock(return_value=False)

        mock_driver = MagicMock()
        mock_driver.session.return_value = mock_session

        migrated = execute_migration(mock_driver, plan)

        assert migrated == 2
        assert mock_session.run.call_count == 2

    def test_正常系_空プランで移行件数0を返す(self) -> None:
        """空のプランで移行件数 0 が返ることを確認."""
        mock_session = MagicMock()
        mock_session.__enter__ = MagicMock(return_value=mock_session)
        mock_session.__exit__ = MagicMock(return_value=False)

        mock_driver = MagicMock()
        mock_driver.session.return_value = mock_session

        migrated = execute_migration(mock_driver, [])

        assert migrated == 0
        mock_session.run.assert_not_called()

    def test_異常系_Cypher実行エラーでスキップして次のエントリに進む(self) -> None:
        """1件目がエラーでも2件目は処理されることを確認."""
        plan: list[dict[str, Any]] = [
            {
                "old_id": "auth-fail",
                "new_id": "uuid5-fail",
                "name": "Fail Author",
                "author_type": "academic",
                "props": {"name": "Fail Author"},
            },
            {
                "old_id": "auth-ok",
                "new_id": "uuid5-ok",
                "name": "OK Author",
                "author_type": "academic",
                "props": {"name": "OK Author"},
            },
        ]

        mock_record = MagicMock()
        mock_result_ok = MagicMock()
        mock_result_ok.single.return_value = mock_record

        mock_session = MagicMock()
        mock_session.run.side_effect = [
            RuntimeError("Neo4j error"),
            mock_result_ok,
        ]
        mock_session.__enter__ = MagicMock(return_value=mock_session)
        mock_session.__exit__ = MagicMock(return_value=False)

        mock_driver = MagicMock()
        mock_driver.session.return_value = mock_session

        migrated = execute_migration(mock_driver, plan)

        assert migrated == 1
        assert mock_session.run.call_count == 2

    def test_正常系_session_runにold_idとnew_idが渡される(self) -> None:
        """session.run に正しい old_id, new_id, props パラメータが渡されることを確認."""
        plan: list[dict[str, Any]] = [
            {
                "old_id": "auth-param-test",
                "new_id": "uuid5-param-test",
                "name": "Param Author",
                "author_type": "academic",
                "props": {"name": "Param Author", "affiliation": "MIT"},
            },
        ]

        mock_record = MagicMock()
        mock_result = MagicMock()
        mock_result.single.return_value = mock_record

        mock_session = MagicMock()
        mock_session.run.return_value = mock_result
        mock_session.__enter__ = MagicMock(return_value=mock_session)
        mock_session.__exit__ = MagicMock(return_value=False)

        mock_driver = MagicMock()
        mock_driver.session.return_value = mock_session

        execute_migration(mock_driver, plan)

        call_kwargs = mock_session.run.call_args
        assert call_kwargs.kwargs["old_id"] == "auth-param-test"
        assert call_kwargs.kwargs["new_id"] == "uuid5-param-test"
        assert call_kwargs.kwargs["props"]["affiliation"] == "MIT"

    def test_エッジケース_result_singleがNoneを返す場合は移行カウントされない(
        self,
    ) -> None:
        """session.run().single() が None を返す場合、migrated カウントに含まれないことを確認."""
        plan: list[dict[str, Any]] = [
            {
                "old_id": "auth-no-result",
                "new_id": "uuid5-no-result",
                "name": "No Result Author",
                "author_type": "academic",
                "props": {"name": "No Result Author"},
            },
        ]

        mock_result = MagicMock()
        mock_result.single.return_value = None

        mock_session = MagicMock()
        mock_session.run.return_value = mock_result
        mock_session.__enter__ = MagicMock(return_value=mock_session)
        mock_session.__exit__ = MagicMock(return_value=False)

        mock_driver = MagicMock()
        mock_driver.session.return_value = mock_session

        migrated = execute_migration(mock_driver, plan)

        assert migrated == 0
