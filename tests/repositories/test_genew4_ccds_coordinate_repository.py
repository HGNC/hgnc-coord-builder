"""Tests for the CCDS coordinate repository implementation.

Validates that the CCDS sub-source correctly queries the ccds table,
deduplicates, and outputs cm_* fields matching the Perl CCDSGeneCoords.
"""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from hgnc_coord_builder.domain.models import CoordinateRecord
from hgnc_coord_builder.exceptions import RepositoryError
from hgnc_coord_builder.repositories.genew4_ccds_coordinate_repository import (
    Genew4CcdsCoordinateRepository,
)
from hgnc_coord_builder.repositories.ccds_coordinate_repository import (
    CcdsCoordinateRepository,
)


def _make_ccds(
    ccds_id: str = "CCDS1.1",
    chromosome: str = "chr7",
    strand: str = "+",
    start: str = "100",
    end: str = "200",
    status: str = "Public",
) -> MagicMock:
    row = MagicMock()
    row.ccds_id = ccds_id
    row.chromosome = chromosome
    row.strand = strand
    row.start = start
    row.end = end
    row.status = status
    return row


class TestGenew4CcdsCoordinateRepositoryUnit:
    """Unit tests for Genew4CcdsCoordinateRepository."""

    def test_inherits_abc(self) -> None:
        assert issubclass(Genew4CcdsCoordinateRepository, CcdsCoordinateRepository)

    def test_fetch_returns_records(self) -> None:
        mock_session = MagicMock()
        ccds = _make_ccds()
        mock_session.execute.return_value = [(ccds,)]
        repo = Genew4CcdsCoordinateRepository(session=mock_session)
        records = repo.fetch_gene_coordinates()
        assert len(records) == 1
        assert records[0].cm_source == "CCDS"

    def test_fetch_maps_minus_strand(self) -> None:
        mock_session = MagicMock()
        ccds = _make_ccds(strand="-")
        mock_session.execute.return_value = [(ccds,)]
        repo = Genew4CcdsCoordinateRepository(session=mock_session)
        records = repo.fetch_gene_coordinates()
        assert records[0].cm_strand == "-"

    def test_fetch_deduplicates_on_ccds_id_chromosome(self) -> None:
        mock_session = MagicMock()
        c1 = _make_ccds(ccds_id="CCDS1", chromosome="7")
        c2 = _make_ccds(ccds_id="CCDS1", chromosome="7")
        mock_session.execute.return_value = [(c1,), (c2,)]
        repo = Genew4CcdsCoordinateRepository(session=mock_session)
        records = repo.fetch_gene_coordinates()
        assert len(records) == 1

    def test_fetch_strips_chr_prefix_from_chromosome(self) -> None:
        mock_session = MagicMock()
        ccds = _make_ccds(chromosome="chr7")
        mock_session.execute.return_value = [(ccds,)]
        repo = Genew4CcdsCoordinateRepository(session=mock_session)
        records = repo.fetch_gene_coordinates()
        assert records[0].cm_chr == "7"

    def test_fetch_skips_dash_start(self) -> None:
        mock_session = MagicMock()
        ccds = _make_ccds(start="-")
        mock_session.execute.return_value = [(ccds,)]
        repo = Genew4CcdsCoordinateRepository(session=mock_session)
        assert repo.fetch_gene_coordinates() == []

    def test_fetch_skips_dash_end(self) -> None:
        mock_session = MagicMock()
        ccds = _make_ccds(end="-")
        mock_session.execute.return_value = [(ccds,)]
        repo = Genew4CcdsCoordinateRepository(session=mock_session)
        assert repo.fetch_gene_coordinates() == []

    def test_fetch_empty_results(self) -> None:
        mock_session = MagicMock()
        mock_session.execute.return_value = []
        repo = Genew4CcdsCoordinateRepository(session=mock_session)
        assert repo.fetch_gene_coordinates() == []

    def test_fetch_query_error_raises_repository_error(self) -> None:
        mock_session = MagicMock()
        mock_session.execute.side_effect = Exception("query error")
        repo = Genew4CcdsCoordinateRepository(session=mock_session)
        with pytest.raises(RepositoryError, match="CCDS"):
            repo.fetch_gene_coordinates()
