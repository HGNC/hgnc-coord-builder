"""Tests for Ensembl repository aligned with Perl EnsemblGeneCoords behavior.

Validates that the Ensembl repository queries gene+seq_region only (NO
HGNC ObjectXref join), converts strand integers to +/- strings, constructs
cm_notes with source/desc/biotype, and outputs CoordinateRecord with cm_*
fields matching the DDL schema.
"""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from hgnc_coord_builder.domain.models import CoordinateRecord
from hgnc_coord_builder.exceptions import RepositoryError
from hgnc_coord_builder.repositories.mysql_ensembl_coordinate_repository import (
    MysqlEnsemblCoordinateRepository,
)


def _make_gene_row(
    stable_id: str = "ENSG000001",
    seq_region_start: int = 100,
    seq_region_end: int = 200,
    seq_region_strand: int = 1,
    source: str = "ensembl_havana",
    description: str = "CFTR",
    biotype: str = "protein_coding",
    seq_region_name: str = "7",
    gene_id: int = 1,
    is_current: bool = True,
) -> MagicMock:
    seq_region = MagicMock()
    seq_region.name = seq_region_name

    gene = MagicMock()
    gene.stable_id = stable_id
    gene.seq_region_start = seq_region_start
    gene.seq_region_end = seq_region_end
    gene.seq_region_strand = seq_region_strand
    gene.source = source
    gene.description = description
    gene.biotype = biotype
    gene.seq_region = seq_region
    gene.gene_id = gene_id
    gene.is_current = is_current
    return gene


class TestEnsemblCmFields:
    """Tests for Ensembl repository outputting cm_* fields matching Perl."""

    def test_record_has_cm_source_ensembl(self) -> None:
        mock_session = MagicMock()
        gene = _make_gene_row()
        mock_session.execute.return_value = [(gene, "HGNC:1100")]
        repo = MysqlEnsemblCoordinateRepository(session=mock_session)
        records = repo.fetch_gene_coordinates()
        assert records[0].cm_source == "Ensembl"

    def test_record_cm_strand_plus_from_int_1(self) -> None:
        mock_session = MagicMock()
        gene = _make_gene_row(seq_region_strand=1)
        mock_session.execute.return_value = [(gene, "HGNC:1100")]
        repo = MysqlEnsemblCoordinateRepository(session=mock_session)
        records = repo.fetch_gene_coordinates()
        assert records[0].cm_strand == "+"

    def test_record_cm_strand_minus_from_int_minus_1(self) -> None:
        mock_session = MagicMock()
        gene = _make_gene_row(seq_region_strand=-1)
        mock_session.execute.return_value = [(gene, "HGNC:1100")]
        repo = MysqlEnsemblCoordinateRepository(session=mock_session)
        records = repo.fetch_gene_coordinates()
        assert records[0].cm_strand == "-"

    def test_record_cm_hgnc_id_is_none(self) -> None:
        mock_session = MagicMock()
        gene = _make_gene_row()
        mock_session.execute.return_value = [(gene, "HGNC:1100")]
        repo = MysqlEnsemblCoordinateRepository(session=mock_session)
        records = repo.fetch_gene_coordinates()
        assert records[0].cm_hgnc_id is None

    def test_record_cm_eg_id_is_none(self) -> None:
        mock_session = MagicMock()
        gene = _make_gene_row()
        mock_session.execute.return_value = [(gene, "HGNC:1100")]
        repo = MysqlEnsemblCoordinateRepository(session=mock_session)
        records = repo.fetch_gene_coordinates()
        assert records[0].cm_eg_id is None

    def test_record_cm_source_id_is_stable_id(self) -> None:
        mock_session = MagicMock()
        gene = _make_gene_row(stable_id="ENSG000001")
        mock_session.execute.return_value = [(gene, "HGNC:1100")]
        repo = MysqlEnsemblCoordinateRepository(session=mock_session)
        records = repo.fetch_gene_coordinates()
        assert records[0].cm_source_id == "ENSG000001"

    def test_record_cm_mapby_is_stable_id(self) -> None:
        mock_session = MagicMock()
        gene = _make_gene_row(stable_id="ENSG000001")
        mock_session.execute.return_value = [(gene, "HGNC:1100")]
        repo = MysqlEnsemblCoordinateRepository(session=mock_session)
        records = repo.fetch_gene_coordinates()
        assert records[0].cm_mapby == "ENSG000001"

    def test_record_cm_notes_format(self) -> None:
        mock_session = MagicMock()
        gene = _make_gene_row(
            source="ensembl_havana",
            description="CFTR",
            biotype="protein_coding",
        )
        mock_session.execute.return_value = [(gene, "HGNC:1100")]
        repo = MysqlEnsemblCoordinateRepository(session=mock_session)
        records = repo.fetch_gene_coordinates()
        notes = records[0].cm_notes
        assert "source => ensembl_havana" in notes
        assert "status => NULL" in notes
        assert "desc =>CFTR" in notes
        assert "biotype => protein_coding" in notes

    def test_record_cm_notes_with_hyphen_description(self) -> None:
        mock_session = MagicMock()
        gene = _make_gene_row(description="-")
        mock_session.execute.return_value = [(gene, "HGNC:1100")]
        repo = MysqlEnsemblCoordinateRepository(session=mock_session)
        records = repo.fetch_gene_coordinates()
        assert "desc =>-" in records[0].cm_notes

    def test_record_cm_chr_from_seq_region(self) -> None:
        mock_session = MagicMock()
        gene = _make_gene_row(seq_region_name="7")
        mock_session.execute.return_value = [(gene, "HGNC:1100")]
        repo = MysqlEnsemblCoordinateRepository(session=mock_session)
        records = repo.fetch_gene_coordinates()
        assert records[0].cm_chr == "7"

    def test_record_cm_start_cm_end(self) -> None:
        mock_session = MagicMock()
        gene = _make_gene_row(seq_region_start=100, seq_region_end=200)
        mock_session.execute.return_value = [(gene, "HGNC:1100")]
        repo = MysqlEnsemblCoordinateRepository(session=mock_session)
        records = repo.fetch_gene_coordinates()
        assert records[0].cm_start == 100
        assert records[0].cm_end == 200

    def test_record_cm_mark_is_none(self) -> None:
        mock_session = MagicMock()
        gene = _make_gene_row()
        mock_session.execute.return_value = [(gene, "HGNC:1100")]
        repo = MysqlEnsemblCoordinateRepository(session=mock_session)
        records = repo.fetch_gene_coordinates()
        assert records[0].cm_mark is None

    def test_to_dict_produces_cm_columns(self) -> None:
        mock_session = MagicMock()
        gene = _make_gene_row()
        mock_session.execute.return_value = [(gene, "HGNC:1100")]
        repo = MysqlEnsemblCoordinateRepository(session=mock_session)
        records = repo.fetch_gene_coordinates()
        d = records[0].to_dict()
        expected_keys = {
            "cm_source", "cm_strand", "cm_chr", "cm_start", "cm_end",
            "cm_source_id", "cm_eg_id", "cm_hgnc_id", "cm_notes",
            "cm_mark", "cm_mapby",
        }
        assert set(d.keys()) == expected_keys
