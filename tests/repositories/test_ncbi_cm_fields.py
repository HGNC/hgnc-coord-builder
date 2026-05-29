"""Tests for NCBI repository aligned with Perl NCBIGeneCoords behavior.

Validates that the NCBI repository queries gene2refseq+gene_info directly
(without HGNC join), truncates chromosomes, defaults strand to '-',
and outputs CoordinateRecord with cm_* fields matching the DDL schema.
"""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from hgnc_coord_builder.domain.models import CoordinateRecord
from hgnc_coord_builder.exceptions import RepositoryError
from hgnc_coord_builder.repositories.genew4_ncbi_coordinate_repository import (
    Genew4NcbiCoordinateRepository,
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
    eg_id: str = "12345",
) -> MagicMock:
    row = MagicMock()
    row.chromosome = chrom
    row.gi_eg_id = eg_id
    return row


class TestNcbiCmFields:
    """Tests for NCBI repository outputting cm_* fields matching Perl."""

    def test_record_has_cm_source_ncbi(self) -> None:
        mock_session = MagicMock()
        g2r = _make_g2r_row()
        gi = _make_gi_row()
        mock_session.execute.return_value = [(g2r, gi)]
        repo = Genew4NcbiCoordinateRepository(session=mock_session)
        records = repo.fetch_gene_coordinates()
        assert records[0].cm_source == "NCBI"

    def test_record_has_cm_strand_from_orientation(self) -> None:
        mock_session = MagicMock()
        g2r = _make_g2r_row(orientation="+")
        gi = _make_gi_row()
        mock_session.execute.return_value = [(g2r, gi)]
        repo = Genew4NcbiCoordinateRepository(session=mock_session)
        records = repo.fetch_gene_coordinates()
        assert records[0].cm_strand == "+"

    def test_record_cm_strand_minus(self) -> None:
        mock_session = MagicMock()
        g2r = _make_g2r_row(orientation="-")
        gi = _make_gi_row()
        mock_session.execute.return_value = [(g2r, gi)]
        repo = Genew4NcbiCoordinateRepository(session=mock_session)
        records = repo.fetch_gene_coordinates()
        assert records[0].cm_strand == "-"

    def test_record_cm_strand_defaults_to_minus_when_missing(self) -> None:
        mock_session = MagicMock()
        g2r = _make_g2r_row(orientation=None)
        gi = _make_gi_row()
        mock_session.execute.return_value = [(g2r, gi)]
        repo = Genew4NcbiCoordinateRepository(session=mock_session)
        records = repo.fetch_gene_coordinates()
        assert records[0].cm_strand == "-"

    def test_record_cm_hgnc_id_is_eg_id_integer(self) -> None:
        mock_session = MagicMock()
        g2r = _make_g2r_row(eg_id="12345")
        gi = _make_gi_row(eg_id="12345")
        mock_session.execute.return_value = [(g2r, gi)]
        repo = Genew4NcbiCoordinateRepository(session=mock_session)
        records = repo.fetch_gene_coordinates()
        assert records[0].cm_hgnc_id == 12345
        assert isinstance(records[0].cm_hgnc_id, int)

    def test_record_cm_eg_id_is_eg_id_integer(self) -> None:
        mock_session = MagicMock()
        g2r = _make_g2r_row(eg_id="12345")
        gi = _make_gi_row(eg_id="12345")
        mock_session.execute.return_value = [(g2r, gi)]
        repo = Genew4NcbiCoordinateRepository(session=mock_session)
        records = repo.fetch_gene_coordinates()
        assert records[0].cm_eg_id == 12345

    def test_record_cm_source_id_is_rna_nt_acc_ver(self) -> None:
        mock_session = MagicMock()
        g2r = _make_g2r_row(rna_nt_acc_ver="NM_000492.4")
        gi = _make_gi_row()
        mock_session.execute.return_value = [(g2r, gi)]
        repo = Genew4NcbiCoordinateRepository(session=mock_session)
        records = repo.fetch_gene_coordinates()
        assert records[0].cm_source_id == "NM_000492.4"

    def test_record_cm_notes_is_gen_nt_acc_ver(self) -> None:
        mock_session = MagicMock()
        g2r = _make_g2r_row(gen_nt_acc_ver="NC_000007.14")
        gi = _make_gi_row()
        mock_session.execute.return_value = [(g2r, gi)]
        repo = Genew4NcbiCoordinateRepository(session=mock_session)
        records = repo.fetch_gene_coordinates()
        assert records[0].cm_notes == "NC_000007.14"

    def test_record_cm_mapby_is_eg_id_string(self) -> None:
        mock_session = MagicMock()
        g2r = _make_g2r_row(eg_id="12345")
        gi = _make_gi_row(eg_id="12345")
        mock_session.execute.return_value = [(g2r, gi)]
        repo = Genew4NcbiCoordinateRepository(session=mock_session)
        records = repo.fetch_gene_coordinates()
        assert records[0].cm_mapby == "12345"

    def test_record_cm_chr_truncates_suffix(self) -> None:
        mock_session = MagicMock()
        g2r = _make_g2r_row()
        gi = _make_gi_row(chrom="7p22")
        mock_session.execute.return_value = [(g2r, gi)]
        repo = Genew4NcbiCoordinateRepository(session=mock_session)
        records = repo.fetch_gene_coordinates()
        assert records[0].cm_chr == "7"

    def test_record_cm_chr_unplaced_unchanged(self) -> None:
        mock_session = MagicMock()
        g2r = _make_g2r_row()
        gi = _make_gi_row(chrom="Un_GL000220v1")
        mock_session.execute.return_value = [(g2r, gi)]
        repo = Genew4NcbiCoordinateRepository(session=mock_session)
        records = repo.fetch_gene_coordinates()
        assert records[0].cm_chr == "Un_GL000220v1"

    def test_record_cm_chr_x(self) -> None:
        mock_session = MagicMock()
        g2r = _make_g2r_row()
        gi = _make_gi_row(chrom="X")
        mock_session.execute.return_value = [(g2r, gi)]
        repo = Genew4NcbiCoordinateRepository(session=mock_session)
        records = repo.fetch_gene_coordinates()
        assert records[0].cm_chr == "X"

    def test_record_cm_chr_y(self) -> None:
        mock_session = MagicMock()
        g2r = _make_g2r_row()
        gi = _make_gi_row(chrom="Y")
        mock_session.execute.return_value = [(g2r, gi)]
        repo = Genew4NcbiCoordinateRepository(session=mock_session)
        records = repo.fetch_gene_coordinates()
        assert records[0].cm_chr == "Y"

    def test_record_cm_chr_mt(self) -> None:
        mock_session = MagicMock()
        g2r = _make_g2r_row()
        gi = _make_gi_row(chrom="MT")
        mock_session.execute.return_value = [(g2r, gi)]
        repo = Genew4NcbiCoordinateRepository(session=mock_session)
        records = repo.fetch_gene_coordinates()
        assert records[0].cm_chr == "MT"

    def test_to_dict_produces_cm_columns(self) -> None:
        mock_session = MagicMock()
        g2r = _make_g2r_row()
        gi = _make_gi_row()
        mock_session.execute.return_value = [(g2r, gi)]
        repo = Genew4NcbiCoordinateRepository(session=mock_session)
        records = repo.fetch_gene_coordinates()
        d = records[0].to_dict()
        expected_keys = {
            "cm_source", "cm_strand", "cm_chr", "cm_start", "cm_end",
            "cm_source_id", "cm_eg_id", "cm_hgnc_id", "cm_notes",
            "cm_mark", "cm_mapby",
        }
        assert set(d.keys()) == expected_keys
