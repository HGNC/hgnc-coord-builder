"""Tests for the Pseudogene coordinate repository implementation.

Validates that the Pseudogene sub-source correctly queries the
pseudogene_org table and outputs cm_* fields matching the Perl
PseudogeneCoords behaviour.
"""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from hgnc_coord_builder.domain.models import CoordinateRecord
from hgnc_coord_builder.exceptions import RepositoryError
from hgnc_coord_builder.repositories.genew4_pseudogene_coordinate_repository import (
    Genew4PseudogeneCoordinateRepository,
)
from hgnc_coord_builder.repositories.pseudogene_coordinate_repository import (
    PseudogeneCoordinateRepository,
)


def _make_porg(
    porg_id: int = 1,
    chromosome: str = "1",
    strand: str = "+",
    start: int = 500,
    end: int = 600,
) -> MagicMock:
    row = MagicMock()
    row.porg_id = porg_id
    row.chromosome = chromosome
    row.strand = strand
    row.start = start
    row.end = end
    row.porg_class = "processed"
    row.porg_link = "https://example.com"
    return row


class TestGenew4PseudogeneCoordinateRepositoryUnit:
    """Unit tests for Genew4PseudogeneCoordinateRepository."""

    def test_inherits_abc(self) -> None:
        assert issubclass(
            Genew4PseudogeneCoordinateRepository, PseudogeneCoordinateRepository
        )

    def test_fetch_returns_records(self) -> None:
        mock_session = MagicMock()
        porg = _make_porg()
        mock_session.execute.return_value = [(porg,)]
        repo = Genew4PseudogeneCoordinateRepository(session=mock_session)
        records = repo.fetch_gene_coordinates()
        assert len(records) == 1
        assert records[0].cm_source == "Pseudogene.org"

    def test_fetch_maps_minus_strand(self) -> None:
        mock_session = MagicMock()
        porg = _make_porg(strand="-")
        mock_session.execute.return_value = [(porg,)]
        repo = Genew4PseudogeneCoordinateRepository(session=mock_session)
        records = repo.fetch_gene_coordinates()
        assert records[0].cm_strand == "-"

    def test_fetch_defaults_strand_to_minus_when_none(self) -> None:
        mock_session = MagicMock()
        porg = _make_porg(strand=None)
        mock_session.execute.return_value = [(porg,)]
        repo = Genew4PseudogeneCoordinateRepository(session=mock_session)
        records = repo.fetch_gene_coordinates()
        assert records[0].cm_strand == "-"

    def test_fetch_deduplicates_on_porg_id(self) -> None:
        mock_session = MagicMock()
        p1 = _make_porg(porg_id=1)
        p2 = _make_porg(porg_id=1)
        mock_session.execute.return_value = [(p1,), (p2,)]
        repo = Genew4PseudogeneCoordinateRepository(session=mock_session)
        records = repo.fetch_gene_coordinates()
        assert len(records) == 1

    def test_fetch_strips_chr_prefix(self) -> None:
        mock_session = MagicMock()
        porg = _make_porg(chromosome="chr1")
        mock_session.execute.return_value = [(porg,)]
        repo = Genew4PseudogeneCoordinateRepository(session=mock_session)
        records = repo.fetch_gene_coordinates()
        assert records[0].cm_chr == "1"

    def test_fetch_empty_results(self) -> None:
        mock_session = MagicMock()
        mock_session.execute.return_value = []
        repo = Genew4PseudogeneCoordinateRepository(session=mock_session)
        assert repo.fetch_gene_coordinates() == []

    def test_fetch_query_error(self) -> None:
        mock_session = MagicMock()
        mock_session.execute.side_effect = Exception("query error")
        repo = Genew4PseudogeneCoordinateRepository(session=mock_session)
        with pytest.raises(RepositoryError, match="Pseudogene"):
            repo.fetch_gene_coordinates()
