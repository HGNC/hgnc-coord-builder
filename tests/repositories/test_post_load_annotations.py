"""Tests for post-load cm_mark and cm_note annotations.

Validates that set_default_cm_mark and set_default_cm_note produce
the correct SQL calls matching the Perl CoordMatchGRCh38 Update module.
"""

from __future__ import annotations

from unittest.mock import MagicMock, call, patch

import pytest

from hgnc_coord_builder.repositories.postgres_coord_staging_repository import (
    PostgresCoordStagingRepository,
    PRODUCTION_TABLE,
)


def _make_repo() -> PostgresCoordStagingRepository:
    engine = MagicMock()
    return PostgresCoordStagingRepository(engine=engine)


class TestSetDefaultCmMark:
    """Test set_default_cm_mark SQL execution."""

    def test_executes_three_update_statements(self) -> None:
        repo = _make_repo()
        mock_cursor = MagicMock()
        mock_raw_conn = MagicMock()
        mock_raw_conn.cursor.return_value.__enter__ = MagicMock(return_value=mock_cursor)
        mock_raw_conn.cursor.return_value.__exit__ = MagicMock(return_value=False)
        repo._engine.raw_connection.return_value.__enter__ = MagicMock(
            return_value=mock_raw_conn
        )
        repo._engine.raw_connection.return_value.__exit__ = MagicMock(return_value=False)

        repo.set_default_cm_mark()

        assert mock_cursor.execute.call_count == 3

    def test_first_update_sets_max_for_non_ncbi_non_ccds(self) -> None:
        repo = _make_repo()
        executed_sqls: list[str] = []
        mock_cursor = MagicMock()
        mock_cursor.execute.side_effect = lambda sql, *args: executed_sqls.append(sql.as_string(None)) if hasattr(sql, 'as_string') else None
        mock_raw_conn = MagicMock()
        mock_raw_conn.cursor.return_value.__enter__ = MagicMock(return_value=mock_cursor)
        mock_raw_conn.cursor.return_value.__exit__ = MagicMock(return_value=False)
        repo._engine.raw_connection.return_value.__enter__ = MagicMock(
            return_value=mock_raw_conn
        )
        repo._engine.raw_connection.return_value.__exit__ = MagicMock(return_value=False)

        repo.set_default_cm_mark()

        first_sql = executed_sqls[0]
        assert "cm_mark" in first_sql
        assert "'max'" in first_sql
        assert "'NCBI'" in first_sql
        assert "'CCDS'" in first_sql

    def test_third_update_sets_hidden_for_ccds(self) -> None:
        repo = _make_repo()
        executed_sqls: list[str] = []
        mock_cursor = MagicMock()
        mock_cursor.execute.side_effect = lambda sql, *args: executed_sqls.append(sql.as_string(None)) if hasattr(sql, 'as_string') else None
        mock_raw_conn = MagicMock()
        mock_raw_conn.cursor.return_value.__enter__ = MagicMock(return_value=mock_cursor)
        mock_raw_conn.cursor.return_value.__exit__ = MagicMock(return_value=False)
        repo._engine.raw_connection.return_value.__enter__ = MagicMock(
            return_value=mock_raw_conn
        )
        repo._engine.raw_connection.return_value.__exit__ = MagicMock(return_value=False)

        repo.set_default_cm_mark()

        third_sql = executed_sqls[2]
        assert "'hidden'" in third_sql
        assert "'CCDS'" in third_sql

    def test_commits_after_all_updates(self) -> None:
        repo = _make_repo()
        mock_cursor = MagicMock()
        mock_raw_conn = MagicMock()
        mock_raw_conn.cursor.return_value.__enter__ = MagicMock(return_value=mock_cursor)
        mock_raw_conn.cursor.return_value.__exit__ = MagicMock(return_value=False)
        repo._engine.raw_connection.return_value.__enter__ = MagicMock(
            return_value=mock_raw_conn
        )
        repo._engine.raw_connection.return_value.__exit__ = MagicMock(return_value=False)

        repo.set_default_cm_mark()

        mock_raw_conn.commit.assert_called_once()

    def test_groups_by_coordinate_tuple(self) -> None:
        repo = _make_repo()
        executed_sqls: list[str] = []
        mock_cursor = MagicMock()
        mock_cursor.execute.side_effect = lambda sql, *args: executed_sqls.append(sql.as_string(None)) if hasattr(sql, 'as_string') else None
        mock_raw_conn = MagicMock()
        mock_raw_conn.cursor.return_value.__enter__ = MagicMock(return_value=mock_cursor)
        mock_raw_conn.cursor.return_value.__exit__ = MagicMock(return_value=False)
        repo._engine.raw_connection.return_value.__enter__ = MagicMock(
            return_value=mock_raw_conn
        )
        repo._engine.raw_connection.return_value.__exit__ = MagicMock(return_value=False)

        repo.set_default_cm_mark()

        for sql_text in executed_sqls[:2]:
            assert "cm_source" in sql_text
            assert "cm_start" in sql_text
            assert "cm_end" in sql_text
            assert "cm_strand" in sql_text
            assert "cm_chr" in sql_text
            assert "MAX(oid)" in sql_text


class TestSetDefaultCmNote:
    """Test set_default_cm_note SQL execution."""

    def test_executes_two_update_statements(self) -> None:
        repo = _make_repo()
        mock_cursor = MagicMock()
        mock_raw_conn = MagicMock()
        mock_raw_conn.cursor.return_value.__enter__ = MagicMock(return_value=mock_cursor)
        mock_raw_conn.cursor.return_value.__exit__ = MagicMock(return_value=False)
        repo._engine.raw_connection.return_value.__enter__ = MagicMock(
            return_value=mock_raw_conn
        )
        repo._engine.raw_connection.return_value.__exit__ = MagicMock(return_value=False)

        repo.set_default_cm_note()

        assert mock_cursor.execute.call_count == 2

    def test_first_update_clears_existing_notes(self) -> None:
        repo = _make_repo()
        executed_sqls: list[str] = []
        executed_params: list = []
        mock_cursor = MagicMock()
        mock_cursor.execute.side_effect = lambda sql, *args: (
            executed_sqls.append(sql.as_string(None)) if hasattr(sql, 'as_string') else None,
            executed_params.append(args),
        )
        mock_raw_conn = MagicMock()
        mock_raw_conn.cursor.return_value.__enter__ = MagicMock(return_value=mock_cursor)
        mock_raw_conn.cursor.return_value.__exit__ = MagicMock(return_value=False)
        repo._engine.raw_connection.return_value.__enter__ = MagicMock(
            return_value=mock_raw_conn
        )
        repo._engine.raw_connection.return_value.__exit__ = MagicMock(return_value=False)

        repo.set_default_cm_note()

        first_sql = executed_sqls[0]
        assert "cm_notes" in first_sql
        assert "NULL" in first_sql

    def test_second_update_sets_warning_for_conflicting_coords(self) -> None:
        repo = _make_repo()
        executed_sqls: list[str] = []
        executed_params: list = []
        mock_cursor = MagicMock()

        def capture(sql, *args):
            if hasattr(sql, 'as_string'):
                executed_sqls.append(sql.as_string(None))
            if args:
                executed_params.append(args[0] if len(args) == 1 else args)

        mock_cursor.execute.side_effect = capture
        mock_raw_conn = MagicMock()
        mock_raw_conn.cursor.return_value.__enter__ = MagicMock(return_value=mock_cursor)
        mock_raw_conn.cursor.return_value.__exit__ = MagicMock(return_value=False)
        repo._engine.raw_connection.return_value.__enter__ = MagicMock(
            return_value=mock_raw_conn
        )
        repo._engine.raw_connection.return_value.__exit__ = MagicMock(return_value=False)

        repo.set_default_cm_note()

        second_sql = executed_sqls[1]
        assert "cm_mapby" in second_sql
        assert "cm_start" in second_sql
        assert "cm_end" in second_sql
        assert "cm_chr" in second_sql
        assert len(executed_params) >= 1
        param = executed_params[0]
        if isinstance(param, (list, tuple)):
            param = param[0]
        assert "Warning" in param
        assert "multiple coordinates" in param

    def test_commits_after_updates(self) -> None:
        repo = _make_repo()
        mock_cursor = MagicMock()
        mock_raw_conn = MagicMock()
        mock_raw_conn.cursor.return_value.__enter__ = MagicMock(return_value=mock_cursor)
        mock_raw_conn.cursor.return_value.__exit__ = MagicMock(return_value=False)
        repo._engine.raw_connection.return_value.__enter__ = MagicMock(
            return_value=mock_raw_conn
        )
        repo._engine.raw_connection.return_value.__exit__ = MagicMock(return_value=False)

        repo.set_default_cm_note()

        mock_raw_conn.commit.assert_called_once()

    def test_warning_text_matches_perl(self) -> None:
        repo = _make_repo()
        captured_params: list = []

        mock_cursor = MagicMock()
        mock_cursor.execute.side_effect = lambda sql, *args: captured_params.append(args)

        mock_raw_conn = MagicMock()
        mock_raw_conn.cursor.return_value.__enter__ = MagicMock(return_value=mock_cursor)
        mock_raw_conn.cursor.return_value.__exit__ = MagicMock(return_value=False)
        repo._engine.raw_connection.return_value.__enter__ = MagicMock(
            return_value=mock_raw_conn
        )
        repo._engine.raw_connection.return_value.__exit__ = MagicMock(return_value=False)

        repo.set_default_cm_note()

        assert len(captured_params) == 2
        warning_param = captured_params[1]
        warning_text = warning_param[0]
        if isinstance(warning_text, (list, tuple)):
            warning_text = warning_text[0]
        assert "Warning" in warning_text
        assert "multiple coordinates" in warning_text
        assert "<br>" in warning_text
