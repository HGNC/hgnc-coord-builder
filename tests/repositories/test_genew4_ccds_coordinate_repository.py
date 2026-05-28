"""Tests for the CCDS coordinate repository implementation.

Validates that the CCDS sub-source correctly queries the Ccds ORM model,
filters out rows with non-numeric start/end positions, and deduplicates
records sharing the same ccds_id + chromosome key.
"""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from hgnc_coord_builder.domain.models import CoordinateRecord, CoordSource
from hgnc_coord_builder.exceptions import RepositoryError
from hgnc_coord_builder.repositories.ccds_coordinate_repository import (
    CcdsCoordinateRepository,
)
from hgnc_coord_builder.repositories.genew4_ccds_coordinate_repository import (
    Genew4CcdsCoordinateRepository,
)


def _make_ccds_row(
    ccds_id: str = "CCDS1",
    chromosome: str = "7",
    strand: str = "+",
    start: str = "100",
    end: str = "200",
    hgnc_id: int = 1100,
    status: str = "Public",
) -> MagicMock:
    row = MagicMock()
    row.ccds_id = ccds_id
    row.chromosome = chromosome
    row.strand = strand
    row.start = start
    row.end = end
    row.hgnc_id = hgnc_id
    row.status = status
    return row


class TestGenew4CcdsCoordinateRepositoryUnit:
    """Unit tests for Genew4CcdsCoordinateRepository."""

    def test_inherits_abc(self) -> None:
        assert issubclass(
            Genew4CcdsCoordinateRepository, CcdsCoordinateRepository
        )

    def test_constructor_stores_session(self) -> None:
        mock_session = MagicMock()
        repo = Genew4CcdsCoordinateRepository(session=mock_session)
        assert repo._session is mock_session

    def test_health_check_success(self) -> None:
        mock_session = MagicMock()
        mock_session.execute.return_value = MagicMock(scalar=lambda: 1)
        repo = Genew4CcdsCoordinateRepository(session=mock_session)
        assert repo.health_check() is True

    def test_health_check_failure(self) -> None:
        mock_session = MagicMock()
        mock_session.execute.side_effect = Exception("connection lost")
        repo = Genew4CcdsCoordinateRepository(session=mock_session)
        assert repo.health_check() is False

    def test_fetch_returns_records(self) -> None:
        mock_session = MagicMock()
        mock_session.execute.return_value = [(_make_ccds_row(),)]
        repo = Genew4CcdsCoordinateRepository(session=mock_session)
        records = repo.fetch_gene_coordinates()

        assert len(records) == 1
        rec = records[0]
        assert isinstance(rec, CoordinateRecord)
        assert rec.hgnc_id == "HGNC:1100"
        assert rec.chromosome == "7"
        assert rec.start == 100
        assert rec.end == 200
        assert rec.strand == 1
        assert rec.source == CoordSource.CCDS

    def test_fetch_maps_minus_strand(self) -> None:
        mock_session = MagicMock()
        mock_session.execute.return_value = [
            (_make_ccds_row(strand="-"),)
        ]
        repo = Genew4CcdsCoordinateRepository(session=mock_session)
        records = repo.fetch_gene_coordinates()
        assert records[0].strand == -1

    def test_fetch_skips_dash_start(self) -> None:
        mock_session = MagicMock()
        mock_session.execute.return_value = [
            (_make_ccds_row(start="-"),)
        ]
        repo = Genew4CcdsCoordinateRepository(session=mock_session)
        records = repo.fetch_gene_coordinates()
        assert records == []

    def test_fetch_skips_dash_end(self) -> None:
        mock_session = MagicMock()
        mock_session.execute.return_value = [
            (_make_ccds_row(end="-"),)
        ]
        repo = Genew4CcdsCoordinateRepository(session=mock_session)
        records = repo.fetch_gene_coordinates()
        assert records == []

    def test_fetch_skips_missing_hgnc_id(self) -> None:
        mock_session = MagicMock()
        mock_session.execute.return_value = [
            (_make_ccds_row(hgnc_id=None),)
        ]
        repo = Genew4CcdsCoordinateRepository(session=mock_session)
        records = repo.fetch_gene_coordinates()
        assert records == []

    def test_fetch_deduplicates_on_ccds_id_chromosome(self) -> None:
        mock_session = MagicMock()
        rows = [
            (_make_ccds_row(ccds_id="CCDS1", chromosome="7", start="100"),),
            (_make_ccds_row(ccds_id="CCDS1", chromosome="7", start="150"),),
        ]
        mock_session.execute.return_value = rows
        repo = Genew4CcdsCoordinateRepository(session=mock_session)
        records = repo.fetch_gene_coordinates()

        assert len(records) == 1
        assert records[0].start == 100

    def test_fetch_keeps_different_chromosomes_same_ccds_id(self) -> None:
        mock_session = MagicMock()
        rows = [
            (_make_ccds_row(ccds_id="CCDS1", chromosome="7"),),
            (_make_ccds_row(ccds_id="CCDS1", chromosome="X"),),
        ]
        mock_session.execute.return_value = rows
        repo = Genew4CcdsCoordinateRepository(session=mock_session)
        records = repo.fetch_gene_coordinates()

        assert len(records) == 2

    def test_fetch_empty_results(self) -> None:
        mock_session = MagicMock()
        mock_session.execute.return_value = []
        repo = Genew4CcdsCoordinateRepository(session=mock_session)
        records = repo.fetch_gene_coordinates()
        assert records == []

    def test_fetch_query_error_raises_repository_error(self) -> None:
        mock_session = MagicMock()
        mock_session.execute.side_effect = Exception("query error")
        repo = Genew4CcdsCoordinateRepository(session=mock_session)
        with pytest.raises(RepositoryError, match="CCDS"):
            repo.fetch_gene_coordinates()

    def test_fetch_uses_select_query(self) -> None:
        mock_session = MagicMock()
        mock_session.execute.return_value = []
        repo = Genew4CcdsCoordinateRepository(session=mock_session)
        repo.fetch_gene_coordinates()
        mock_session.execute.assert_called_once()

    def test_fetch_skips_missing_chromosome(self) -> None:
        mock_session = MagicMock()
        mock_session.execute.return_value = [
            (_make_ccds_row(chromosome=None),)
        ]
        repo = Genew4CcdsCoordinateRepository(session=mock_session)
        records = repo.fetch_gene_coordinates()
        assert records == []

    def test_fetch_skips_missing_strand(self) -> None:
        mock_session = MagicMock()
        mock_session.execute.return_value = [
            (_make_ccds_row(strand=None),)
        ]
        repo = Genew4CcdsCoordinateRepository(session=mock_session)
        records = repo.fetch_gene_coordinates()
        assert records == []

    def test_fetch_strips_chr_prefix_from_chromosome(self) -> None:
        mock_session = MagicMock()
        mock_session.execute.return_value = [
            (_make_ccds_row(chromosome="chr7"),)
        ]
        repo = Genew4CcdsCoordinateRepository(session=mock_session)
        records = repo.fetch_gene_coordinates()
        assert records[0].chromosome == "7"
