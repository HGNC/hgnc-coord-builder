"""Tests for the pseudogene coordinate repository implementation.

Validates that the pseudogene sub-source correctly queries the
PseudogeneOrg ORM model and deduplicates records on porg_id.
"""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from hgnc_coord_builder.domain.models import CoordinateRecord, CoordSource
from hgnc_coord_builder.exceptions import RepositoryError
from hgnc_coord_builder.repositories.genew4_pseudogene_coordinate_repository import (
    Genew4PseudogeneCoordinateRepository,
)
from hgnc_coord_builder.repositories.pseudogene_coordinate_repository import (
    PseudogeneCoordinateRepository,
)


def _make_porg_row(
    porg_id: int = 1,
    chromosome: str = "7",
    strand: str = "+",
    start: int = 100,
    end: int = 200,
) -> MagicMock:
    row = MagicMock()
    row.porg_id = porg_id
    row.chromosome = chromosome
    row.strand = strand
    row.start = start
    row.end = end
    row.class_ = "processed"
    row.link = "ENSG00000012048"
    return row


class TestGenew4PseudogeneCoordinateRepositoryUnit:
    """Unit tests for Genew4PseudogeneCoordinateRepository."""

    def test_inherits_abc(self) -> None:
        assert issubclass(
            Genew4PseudogeneCoordinateRepository, PseudogeneCoordinateRepository
        )

    def test_constructor_stores_session(self) -> None:
        mock_session = MagicMock()
        repo = Genew4PseudogeneCoordinateRepository(session=mock_session)
        assert repo._session is mock_session

    def test_health_check_success(self) -> None:
        mock_session = MagicMock()
        mock_session.execute.return_value = MagicMock(scalar=lambda: 1)
        repo = Genew4PseudogeneCoordinateRepository(session=mock_session)
        assert repo.health_check() is True

    def test_health_check_failure(self) -> None:
        mock_session = MagicMock()
        mock_session.execute.side_effect = Exception("connection lost")
        repo = Genew4PseudogeneCoordinateRepository(session=mock_session)
        assert repo.health_check() is False

    def test_fetch_returns_records(self) -> None:
        mock_session = MagicMock()
        mock_session.execute.return_value = [(_make_porg_row(),)]
        repo = Genew4PseudogeneCoordinateRepository(session=mock_session)
        records = repo.fetch_gene_coordinates()

        assert len(records) == 1
        rec = records[0]
        assert isinstance(rec, CoordinateRecord)
        assert rec.chromosome == "7"
        assert rec.start == 100
        assert rec.end == 200
        assert rec.strand == 1
        assert rec.source == CoordSource.PSEUDOGENE

    def test_fetch_maps_minus_strand(self) -> None:
        mock_session = MagicMock()
        mock_session.execute.return_value = [
            (_make_porg_row(strand="-"),)
        ]
        repo = Genew4PseudogeneCoordinateRepository(session=mock_session)
        records = repo.fetch_gene_coordinates()
        assert records[0].strand == -1

    def test_fetch_skips_missing_strand(self) -> None:
        mock_session = MagicMock()
        mock_session.execute.return_value = [
            (_make_porg_row(strand=None),)
        ]
        repo = Genew4PseudogeneCoordinateRepository(session=mock_session)
        records = repo.fetch_gene_coordinates()
        assert records == []

    def test_fetch_skips_missing_chromosome(self) -> None:
        mock_session = MagicMock()
        mock_session.execute.return_value = [
            (_make_porg_row(chromosome=None),)
        ]
        repo = Genew4PseudogeneCoordinateRepository(session=mock_session)
        records = repo.fetch_gene_coordinates()
        assert records == []

    def test_fetch_skips_missing_start(self) -> None:
        mock_session = MagicMock()
        mock_session.execute.return_value = [
            (_make_porg_row(start=None),)
        ]
        repo = Genew4PseudogeneCoordinateRepository(session=mock_session)
        records = repo.fetch_gene_coordinates()
        assert records == []

    def test_fetch_skips_missing_end(self) -> None:
        mock_session = MagicMock()
        mock_session.execute.return_value = [
            (_make_porg_row(end=None),)
        ]
        repo = Genew4PseudogeneCoordinateRepository(session=mock_session)
        records = repo.fetch_gene_coordinates()
        assert records == []

    def test_fetch_deduplicates_on_porg_id(self) -> None:
        mock_session = MagicMock()
        mock_session.execute.return_value = [
            (_make_porg_row(porg_id=1, start=100),),
            (_make_porg_row(porg_id=1, start=150),),
        ]
        repo = Genew4PseudogeneCoordinateRepository(session=mock_session)
        records = repo.fetch_gene_coordinates()
        assert len(records) == 1
        assert records[0].start == 100

    def test_fetch_keeps_different_porg_ids(self) -> None:
        mock_session = MagicMock()
        mock_session.execute.return_value = [
            (_make_porg_row(porg_id=1),),
            (_make_porg_row(porg_id=2),),
        ]
        repo = Genew4PseudogeneCoordinateRepository(session=mock_session)
        records = repo.fetch_gene_coordinates()
        assert len(records) == 2

    def test_fetch_empty_results(self) -> None:
        mock_session = MagicMock()
        mock_session.execute.return_value = []
        repo = Genew4PseudogeneCoordinateRepository(session=mock_session)
        records = repo.fetch_gene_coordinates()
        assert records == []

    def test_fetch_query_error_raises_repository_error(self) -> None:
        mock_session = MagicMock()
        mock_session.execute.side_effect = Exception("query error")
        repo = Genew4PseudogeneCoordinateRepository(session=mock_session)
        with pytest.raises(RepositoryError, match="Pseudogene"):
            repo.fetch_gene_coordinates()

    def test_fetch_strips_chr_prefix(self) -> None:
        mock_session = MagicMock()
        mock_session.execute.return_value = [
            (_make_porg_row(chromosome="chr7"),)
        ]
        repo = Genew4PseudogeneCoordinateRepository(session=mock_session)
        records = repo.fetch_gene_coordinates()
        assert records[0].chromosome == "7"
