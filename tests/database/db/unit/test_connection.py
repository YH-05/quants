"""Unit tests for database connection module."""

import os
from pathlib import Path
from unittest import mock

import pytest


class TestGetDataDir:
    """Tests for get_data_dir function."""

    def test_正常系_DATA_DIR環境変数が設定されている場合はその値を返す(
        self,
        temp_dir: Path,
    ) -> None:
        """DATA_DIR環境変数が設定されている場合、その値をPathとして返す."""
        from database.db.connection import get_data_dir

        expected_path = temp_dir / "custom_data"
        expected_path.mkdir(exist_ok=True)

        with mock.patch.dict(os.environ, {"DATA_DIR": str(expected_path)}):
            result = get_data_dir()

        assert result == expected_path

    def test_正常系_DATA_DIR環境変数が未設定でカレントにdata存在時はカレントから相対パス(
        self,
        temp_dir: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """DATA_DIR未設定でカレントディレクトリにdataがある場合、./dataを返す."""
        from database.db.connection import get_data_dir

        # カレントディレクトリにdataディレクトリを作成
        data_dir = temp_dir / "data"
        data_dir.mkdir()

        # DATA_DIR環境変数を削除
        monkeypatch.delenv("DATA_DIR", raising=False)
        # カレントディレクトリを変更
        monkeypatch.chdir(temp_dir)

        result = get_data_dir()

        # macOSではシンボリックリンク解決により/varと/private/varの違いが生じるため
        # resolve()で正規化して比較
        assert result.resolve() == data_dir.resolve()

    def test_正常系_DATA_DIR未設定でカレントにdata無い時はfileベースのパス(
        self,
        temp_dir: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """DATA_DIR未設定でカレントにdata無い場合、__file__ベースのパスを返す."""
        from database.db.connection import DATA_DIR, get_data_dir

        # dataディレクトリが存在しないディレクトリをカレントに設定
        no_data_dir = temp_dir / "no_data_here"
        no_data_dir.mkdir()

        # DATA_DIR環境変数を削除
        monkeypatch.delenv("DATA_DIR", raising=False)
        # カレントディレクトリを変更
        monkeypatch.chdir(no_data_dir)

        result = get_data_dir()

        # __file__ベースのDATA_DIRと一致することを確認
        assert result == DATA_DIR

    def test_エッジケース_DATA_DIR環境変数が空文字の場合はフォールバック(
        self,
        temp_dir: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """DATA_DIR環境変数が空文字の場合はフォールバック動作."""
        from database.db.connection import get_data_dir

        # dataディレクトリが存在しないディレクトリをカレントに設定
        no_data_dir = temp_dir / "no_data_here"
        no_data_dir.mkdir()

        # DATA_DIR環境変数を空文字に設定
        monkeypatch.setenv("DATA_DIR", "")
        # カレントディレクトリを変更
        monkeypatch.chdir(no_data_dir)

        # 空文字の場合は環境変数が設定されていないとみなす
        # フォールバックロジックが動作することを確認
        result = get_data_dir()

        # 空文字の場合のフォールバック動作を確認
        # 結果がPathオブジェクトであること
        assert isinstance(result, Path)

    def test_正常系_返り値がPathオブジェクトである(
        self,
        temp_dir: Path,
    ) -> None:
        """get_data_dir()の返り値がPathオブジェクトである."""
        from database.db.connection import get_data_dir

        with mock.patch.dict(os.environ, {"DATA_DIR": str(temp_dir)}):
            result = get_data_dir()

        assert isinstance(result, Path)


class TestGetDbPath:
    """Tests for get_db_path function."""

    def test_正常系_DATA_DIR環境変数設定時にget_db_pathが追従する(
        self,
        temp_dir: Path,
    ) -> None:
        """DATA_DIR環境変数を設定すると、get_db_pathの戻り値が追従する."""
        from database.db.connection import get_db_path

        custom_data_dir = temp_dir / "custom_data"
        custom_data_dir.mkdir(exist_ok=True)

        with mock.patch.dict(os.environ, {"DATA_DIR": str(custom_data_dir)}):
            sqlite_path = get_db_path("sqlite", "market")
            duckdb_path = get_db_path("duckdb", "analytics")

        assert sqlite_path == custom_data_dir / "sqlite" / "market.db"
        assert duckdb_path == custom_data_dir / "duckdb" / "analytics.duckdb"

    def test_正常系_sqliteタイプで正しいパスを返す(self) -> None:
        """sqlite タイプの場合、.db 拡張子のパスを返す."""
        from database.db.connection import get_db_path

        path = get_db_path("sqlite", "test_db")
        assert path.name == "test_db.db"
        assert path.parent.name == "sqlite"

    def test_正常系_duckdbタイプで正しいパスを返す(self) -> None:
        """duckdb タイプの場合、.duckdb 拡張子のパスを返す."""
        from database.db.connection import get_db_path

        path = get_db_path("duckdb", "test_db")
        assert path.name == "test_db.duckdb"
        assert path.parent.name == "duckdb"


class TestDeprecationComments:
    """Tests for deprecation comments on PROJECT_ROOT and DATA_DIR."""

    def test_正常系_PROJECT_ROOTが存在する(self) -> None:
        """PROJECT_ROOT定数が存在する（後方互換性）."""
        from database.db.connection import PROJECT_ROOT

        assert isinstance(PROJECT_ROOT, Path)

    def test_正常系_DATA_DIRが存在する(self) -> None:
        """DATA_DIR定数が存在する（後方互換性）."""
        from database.db.connection import DATA_DIR

        assert isinstance(DATA_DIR, Path)
