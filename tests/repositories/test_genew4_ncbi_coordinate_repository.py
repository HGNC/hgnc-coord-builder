"""Tests for the NCBI coordinate repository implementation.

Validates that the NCBI sub-source correctly queries Gene2Refseq and
GeneInfo using mocked SQLAlchemy sessions. Covers join conditions,
filter predicates, chromosome cleanup, strand normalization, and
error handling.
"""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from hgnc_coord_builder.domain.models import CoordinateRecord, CoordSource
from hgnc_coord_builder.exceptions import RepositoryError
from hgnc_coord_builder.repositories.genew4_ncbi_coordinate_repository import (
    Genew4NcbiCoordinateRepository,
)
from hgnc_coord_builder.repositories.ncbi_coordinate_repository import (
    NcbiCoordinateRepository,
)


def _make_g2r_row(
    tax_id: str = "9606",
    eg_id: str = "12345",
    gen_nt_acc_ver: str = "NC_000007.14",
    start: str = "100",
    end: str = "200",
    orientation: str = "+",
    assembly: str = "GRCh38.p14",
    rna_nt_acc_ver: str = "NM_000492.4",
) -> MagicMock:
    row = MagicMock()
    row.g2r_tax_id = tax_id
    row.g2r_eg_id = eg_id
    row.gen_nt_acc_ver = gen_nt_acc_ver
    row.start_pos_gen_acc = start
    row.end_pos_gen_acc = end
    row.orientation = orientation
    row.assembly = assembly
    row.g2r_rna_nt_acc_ver = rna_nt_acc_ver
    return row


def _make_gi_row(
    chrom: str = "7",
    hgnc_id: int = 1100,
) -> MagicMock:
    row = MagicMock()
    row.chromosome = chrom
    row.hgnc_id = hgnc_id
    return row


class TestGenew4NcbiCoordinateRepositoryUnit:
    """Unit tests for Genew4NcbiCoordinateRepository."""

    def test_inherits_abc(self) -> None:
        assert issubclass(
            Genew4NcbiCoordinateRepository, NcbiCoordinateRepository
        )

    def test_constructor_stores_session(self) -> None:
        mock_session = MagicMock()
        repo = Genew4NcbiCoordinateRepository(session=mock_session)
        assert repo._session is mock_session

    def test_health_check_success(self) -> None:
        mock_session = MagicMock()
        mock_session.execute.return_value = MagicMock(scalar=lambda: 1)
        repo = Genew4NcbiCoordinateRepository(session=mock_session)
        assert repo.health_check() is True

    def test_health_check_failure(self) -> None:
        mock_session = MagicMock()
        mock_session.execute.side_effect = Exception("connection lost")
        repo = Genew4NcbiCoordinateRepository(session=mock_session)
        assert repo.health_check() is False

    def test_fetch_returns_records(self) -> None:
        mock_session = MagicMock()
        g2r = _make_g2r_row()
        gi = _make_gi_row()
        mock_session.execute.return_value = [(g2r, gi)]

        repo = Genew4NcbiCoordinateRepository(session=mock_session)
        records = repo.fetch_gene_coordinates()

        assert len(records) == 1
        rec = records[0]
        assert isinstance(rec, CoordinateRecord)
        assert rec.hgnc_id == "HGNC:1100"
        assert rec.chromosome == "7"
        assert rec.start == 100
        assert rec.end == 200
        assert rec.strand == 1
        assert rec.source == CoordSource.NCBI

    def test_fetch_maps_minus_strand(self) -> None:
        mock_session = MagicMock()
        g2r = _make_g2r_row(orientation="-")
        gi = _make_gi_row()
        mock_session.execute.return_value = [(g2r, gi)]

        repo = Genew4NcbiCoordinateRepository(session=mock_session)
        records = repo.fetch_gene_coordinates()

        assert records[0].strand == -1

    def test_fetch_defaults_strand_when_missing(self) -> None:
        mock_session = MagicMock()
        g2r = _make_g2r_row(orientation=None)
        gi = _make_gi_row()
        mock_session.execute.return_value = [(g2r, gi)]

        repo = Genew4NcbiCoordinateRepository(session=mock_session)
        records = repo.fetch_gene_coordinates()

        assert records[0].strand == -1

    def test_fetch_defaults_strand_when_empty(self) -> None:
        mock_session = MagicMock()
        g2r = _make_g2r_row(orientation="")
        gi = _make_gi_row()
        mock_session.execute.return_value = [(g2r, gi)]

        repo = Genew4NcbiCoordinateRepository(session=mock_session)
        records = repo.fetch_gene_coordinates()

        assert records[0].strand == -1

    def test_fetch_strips_chr_prefix_from_chromosome(self) -> None:
        mock_session = MagicMock()
        g2r = _make_g2r_row()
        gi = _make_gi_row(chrom="chr7")
        mock_session.execute.return_value = [(g2r, gi)]

        repo = Genew4NcbiCoordinateRepository(session=mock_session)
        records = repo.fetch_gene_coordinates()

        assert records[0].chromosome == "7"

    def test_fetch_skips_missing_hgnc_id(self) -> None:
        mock_session = MagicMock()
        g2r = _make_g2r_row()
        gi = _make_gi_row(hgnc_id=None)
        mock_session.execute.return_value = [(g2r, gi)]

        repo = Genew4NcbiCoordinateRepository(session=mock_session)
        records = repo.fetch_gene_coordinates()

        assert records == []

    def test_fetch_skips_missing_chromosome(self) -> None:
        mock_session = MagicMock()
        g2r = _make_g2r_row()
        gi = _make_gi_row(chrom=None)
        mock_session.execute.return_value = [(g2r, gi)]

        repo = Genew4NcbiCoordinateRepository(session=mock_session)
        records = repo.fetch_gene_coordinates()

        assert records == []

    def test_fetch_skips_missing_start_position(self) -> None:
        mock_session = MagicMock()
        g2r = _make_g2r_row(start=None)
        gi = _make_gi_row()
        mock_session.execute.return_value = [(g2r, gi)]

        repo = Genew4NcbiCoordinateRepository(session=mock_session)
        records = repo.fetch_gene_coordinates()

        assert records == []

    def test_fetch_skips_missing_end_position(self) -> None:
        mock_session = MagicMock()
        g2r = _make_g2r_row(end=None)
        gi = _make_gi_row()
        mock_session.execute.return_value = [(g2r, gi)]

        repo = Genew4NcbiCoordinateRepository(session=mock_session)
        records = repo.fetch_gene_coordinates()

        assert records == []

    def test_fetch_skips_non_numeric_start(self) -> None:
        mock_session = MagicMock()
        g2r = _make_g2r_row(start="-")
        gi = _make_gi_row()
        mock_session.execute.return_value = [(g2r, gi)]

        repo = Genew4NcbiCoordinateRepository(session=mock_session)
        records = repo.fetch_gene_coordinates()

        assert records == []

    def test_fetch_skips_non_numeric_end(self) -> None:
        mock_session = MagicMock()
        g2r = _make_g2r_row(end="-")
        gi = _make_gi_row()
        mock_session.execute.return_value = [(g2r, gi)]

        repo = Genew4NcbiCoordinateRepository(session=mock_session)
        records = repo.fetch_gene_coordinates()

        assert records == []

    def test_fetch_empty_results(self) -> None:
        mock_session = MagicMock()
        mock_session.execute.return_value = []
        repo = Genew4NcbiCoordinateRepository(session=mock_session)
        records = repo.fetch_gene_coordinates()
        assert records == []

    def test_fetch_query_error_raises_repository_error(self) -> None:
        mock_session = MagicMock()
        mock_session.execute.side_effect = Exception("query error")
        repo = Genew4NcbiCoordinateRepository(session=mock_session)
        with pytest.raises(RepositoryError, match="NCBI"):
            repo.fetch_gene_coordinates()

    def test_fetch_uses_select_query(self) -> None:
        mock_session = MagicMock()
        mock_session.execute.return_value = []
        repo = Genew4NcbiCoordinateRepository(session=mock_session)
        repo.fetch_gene_coordinates()
        mock_session.execute.assert_called_once()

    def test_fetch_multiple_records(self) -> None:
        mock_session = MagicMock()
        rows = [
            (
                _make_g2r_row(eg_id="12345", start="100", end="200"),
                _make_gi_row(chrom="7", hgnc_id=1100),
            ),
            (
                _make_g2r_row(eg_id="67890", start="300", end="400"),
                _make_gi_row(chrom="X", hgnc_id=2200),
            ),
        ]
        mock_session.execute.return_value = rows

        repo = Genew4NcbiCoordinateRepository(session=mock_session)
        records = repo.fetch_gene_coordinates()

        assert len(records) == 2
        assert records[0].hgnc_id == "HGNC:1100"
        assert records[1].hgnc_id == "HGNC:2200"

    def test_fetch_formats_hgnc_id_with_prefix(self) -> None:
        mock_session = MagicMock()
        g2r = _make_g2r_row()
        gi = _make_gi_row(hgnc_id=5)
        mock_session.execute.return_value = [(g2r, gi)]

        repo = Genew4NcbiCoordinateRepository(session=mock_session)
        records = repo.fetch_gene_coordinates()

        assert records[0].hgnc_id == "HGNC:5"

    def test_fetch_handles_x_chromosome(self) -> None:
        mock_session = MagicMock()
        g2r = _make_g2r_row()
        gi = _make_gi_row(chrom="X")
        mock_session.execute.return_value = [(g2r, gi)]

        repo = Genew4NcbiCoordinateRepository(session=mock_session)
        records = repo.fetch_gene_coordinates()

        assert records[0].chromosome == "X"

    def test_fetch_handles_mt_chromosome(self) -> None:
        mock_session = MagicMock()
        g2r = _make_g2r_row()
        gi = _make_gi_row(chrom="MT")
        mock_session.execute.return_value = [(g2r, gi)]

        repo = Genew4NcbiCoordinateRepository(session=mock_session)
        records = repo.fetch_gene_coordinates()

        assert records[0].chromosome == "MT"
