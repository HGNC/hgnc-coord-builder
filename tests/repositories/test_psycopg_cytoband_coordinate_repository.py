"""Tests for the cytoband coordinate repository implementation.

Validates that the cytoband sub-source correctly queries the cytoband
table via psycopg raw SQL, filters by cb_source='Ensembl', and
deduplicates records on cm_source_id.
"""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from hgnc_coord_builder.domain.models import CoordinateRecord, CoordSource
from hgnc_coord_builder.exceptions import RepositoryError
from hgnc_coord_builder.repositories.cytoband_coordinate_repository import (
    CytobandCoordinateRepository,
)
from hgnc_coord_builder.repositories.psycopg_cytoband_coordinate_repository import (
    PsycopgCytobandCoordinateRepository,
)


def _make_cytoband_row(
    chromosome: str = "7",
    start: int = 100,
    end: int = 200,
    band: str = "p22.1",
    source: str = "Ensembl",
) -> tuple:
    return (source, chromosome, start, end, band)


class TestPsycopgCytobandCoordinateRepositoryUnit:
    """Unit tests for PsycopgCytobandCoordinateRepository."""

    def test_inherits_abc(self) -> None:
        assert issubclass(
            PsycopgCytobandCoordinateRepository, CytobandCoordinateRepository
        )

    def test_constructor_stores_connection(self) -> None:
        mock_conn = MagicMock()
        repo = PsycopgCytobandCoordinateRepository(connection=mock_conn)
        assert repo._connection is mock_conn

    def test_health_check_success(self) -> None:
        mock_conn = MagicMock()
        mock_conn.execute.return_value = MagicMock(fetchone=lambda: (1,))
        repo = PsycopgCytobandCoordinateRepository(connection=mock_conn)
        assert repo.health_check() is True

    def test_health_check_failure(self) -> None:
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_cursor.execute.side_effect = Exception("connection lost")
        mock_conn.cursor.return_value.__enter__ = MagicMock(
            return_value=mock_cursor
        )
        mock_conn.cursor.return_value.__exit__ = MagicMock(return_value=False)
        repo = PsycopgCytobandCoordinateRepository(connection=mock_conn)
        assert repo.health_check() is False

    def test_fetch_returns_records(self) -> None:
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_conn.cursor.return_value.__enter__ = MagicMock(
            return_value=mock_cursor
        )
        mock_conn.cursor.return_value.__exit__ = MagicMock(return_value=False)
        mock_cursor.fetchall.return_value = [
            _make_cytoband_row(chromosome="7", start=100, end=200, band="p22.1"),
        ]

        repo = PsycopgCytobandCoordinateRepository(connection=mock_conn)
        records = repo.fetch_gene_coordinates()

        assert len(records) == 1
        rec = records[0]
        assert isinstance(rec, CoordinateRecord)
        assert rec.chromosome == "7"
        assert rec.start == 100
        assert rec.end == 200
        assert rec.source == CoordSource.CYTOBAND

    def test_fetch_uses_ensembl_filter(self) -> None:
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_conn.cursor.return_value.__enter__ = MagicMock(
            return_value=mock_cursor
        )
        mock_conn.cursor.return_value.__exit__ = MagicMock(return_value=False)
        mock_cursor.fetchall.return_value = []

        repo = PsycopgCytobandCoordinateRepository(connection=mock_conn)
        repo.fetch_gene_coordinates()

        mock_cursor.execute.assert_called_once()
        sql_arg = mock_cursor.execute.call_args[0][0]
        assert "cb_source" in sql_arg
        assert "Ensembl" in str(mock_cursor.execute.call_args)

    def test_fetch_deduplicates_on_source_id(self) -> None:
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_conn.cursor.return_value.__enter__ = MagicMock(
            return_value=mock_cursor
        )
        mock_conn.cursor.return_value.__exit__ = MagicMock(return_value=False)
        mock_cursor.fetchall.return_value = [
            _make_cytoband_row(chromosome="7", band="p22.1"),
            _make_cytoband_row(chromosome="7", band="p22.1"),
        ]

        repo = PsycopgCytobandCoordinateRepository(connection=mock_conn)
        records = repo.fetch_gene_coordinates()

        assert len(records) == 1

    def test_fetch_keeps_different_bands(self) -> None:
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_conn.cursor.return_value.__enter__ = MagicMock(
            return_value=mock_cursor
        )
        mock_conn.cursor.return_value.__exit__ = MagicMock(return_value=False)
        mock_cursor.fetchall.return_value = [
            _make_cytoband_row(chromosome="7", band="p22.1"),
            _make_cytoband_row(chromosome="7", band="p22.2"),
        ]

        repo = PsycopgCytobandCoordinateRepository(connection=mock_conn)
        records = repo.fetch_gene_coordinates()

        assert len(records) == 2

    def test_fetch_empty_results(self) -> None:
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_conn.cursor.return_value.__enter__ = MagicMock(
            return_value=mock_cursor
        )
        mock_conn.cursor.return_value.__exit__ = MagicMock(return_value=False)
        mock_cursor.fetchall.return_value = []

        repo = PsycopgCytobandCoordinateRepository(connection=mock_conn)
        records = repo.fetch_gene_coordinates()
        assert records == []

    def test_fetch_query_error_raises_repository_error(self) -> None:
        mock_conn = MagicMock()
        mock_conn.cursor.side_effect = Exception("connection error")
        repo = PsycopgCytobandCoordinateRepository(connection=mock_conn)
        with pytest.raises(RepositoryError, match="Cytoband"):
            repo.fetch_gene_coordinates()

    def test_fetch_skips_rows_with_null_chromosome(self) -> None:
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_conn.cursor.return_value.__enter__ = MagicMock(
            return_value=mock_cursor
        )
        mock_conn.cursor.return_value.__exit__ = MagicMock(return_value=False)
        mock_cursor.fetchall.return_value = [
            (None, None, 100, 200, "p22.1"),
        ]

        repo = PsycopgCytobandCoordinateRepository(connection=mock_conn)
        records = repo.fetch_gene_coordinates()
        assert records == []

    def test_fetch_strips_chr_prefix(self) -> None:
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_conn.cursor.return_value.__enter__ = MagicMock(
            return_value=mock_cursor
        )
        mock_conn.cursor.return_value.__exit__ = MagicMock(return_value=False)
        mock_cursor.fetchall.return_value = [
            _make_cytoband_row(chromosome="chr7"),
        ]

        repo = PsycopgCytobandCoordinateRepository(connection=mock_conn)
        records = repo.fetch_gene_coordinates()
        assert records[0].chromosome == "7"
