"""Tests for the Cytoband coordinate repository implementation.

Validates that the Cytoband sub-source correctly queries the cytoband
table and outputs cm_* fields matching the Perl ChrCoords behaviour.
"""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from hgnc_coord_builder.domain.models import CoordinateRecord
from hgnc_coord_builder.exceptions import RepositoryError
from hgnc_coord_builder.repositories.psycopg_cytoband_coordinate_repository import (
    PsycopgCytobandCoordinateRepository,
)
from hgnc_coord_builder.repositories.cytoband_coordinate_repository import (
    CytobandCoordinateRepository,
)


def _make_mock_cursor(rows):
    cursor = MagicMock()
    cursor.fetchall.return_value = rows
    return cursor


def _make_mock_conn(rows):
    conn = MagicMock()
    cursor = _make_mock_cursor(rows)
    conn.cursor.return_value.__enter__ = lambda s: cursor
    conn.cursor.return_value.__exit__ = lambda s, *a: None
    return conn


class TestPsycopgCytobandCoordinateRepositoryUnit:
    """Unit tests for PsycopgCytobandCoordinateRepository."""

    def test_inherits_abc(self) -> None:
        assert issubclass(
            PsycopgCytobandCoordinateRepository, CytobandCoordinateRepository
        )

    def test_fetch_returns_records(self) -> None:
        conn = _make_mock_conn([("Ensembl", "7", 100, 200, "p22")])
        repo = PsycopgCytobandCoordinateRepository(connection=conn)
        records = repo.fetch_gene_coordinates()
        assert len(records) == 1
        assert records[0].cm_source == "Chrom"
        assert records[0].cm_strand == " "
        assert records[0].cm_source_id == "7p22"

    def test_fetch_strips_chr_prefix(self) -> None:
        conn = _make_mock_conn([("Ensembl", "chr7", 100, 200, "p22")])
        repo = PsycopgCytobandCoordinateRepository(connection=conn)
        records = repo.fetch_gene_coordinates()
        assert records[0].cm_chr == "7"

    def test_fetch_deduplicates(self) -> None:
        conn = _make_mock_conn([
            ("Ensembl", "7", 100, 200, "p22"),
            ("Ensembl", "7", 100, 200, "p22"),
        ])
        repo = PsycopgCytobandCoordinateRepository(connection=conn)
        records = repo.fetch_gene_coordinates()
        assert len(records) == 1

    def test_fetch_empty_results(self) -> None:
        conn = _make_mock_conn([])
        repo = PsycopgCytobandCoordinateRepository(connection=conn)
        assert repo.fetch_gene_coordinates() == []

    def test_fetch_query_error(self) -> None:
        conn = MagicMock()
        conn.cursor.return_value.__enter__ = lambda s: MagicMock(
            fetchall=MagicMock(side_effect=Exception("db error"))
        )
        conn.cursor.return_value.__exit__ = lambda s, *a: None
        repo = PsycopgCytobandCoordinateRepository(connection=conn)
        with pytest.raises(RepositoryError, match="Cytoband"):
            repo.fetch_gene_coordinates()
