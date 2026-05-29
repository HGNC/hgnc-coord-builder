"""Tests for CCDS, Cytoband, and Pseudogene repos with cm_* fields.

Validates that each repository outputs CoordinateRecord instances with
cm_* fields matching the Perl sub-source behaviour.
"""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from hgnc_coord_builder.domain.models import CoordinateRecord
from hgnc_coord_builder.exceptions import RepositoryError
from hgnc_coord_builder.repositories.genew4_ccds_coordinate_repository import (
    Genew4CcdsCoordinateRepository,
)
from hgnc_coord_builder.repositories.psycopg_cytoband_coordinate_repository import (
    PsycopgCytobandCoordinateRepository,
)
from hgnc_coord_builder.repositories.genew4_pseudogene_coordinate_repository import (
    Genew4PseudogeneCoordinateRepository,
)


def _make_ccds_row(
    ccds_id: str = "CCDS1.1",
    chromosome: str = "chr7",
    strand: str = "+",
    start: str = "100",
    end: str = "200",
    status: str = "Public",
    hgnc_id: int | None = None,
) -> MagicMock:
    row = MagicMock()
    row.ccds_id = ccds_id
    row.chromosome = chromosome
    row.strand = strand
    row.start = start
    row.end = end
    row.status = status
    row.hgnc_id = hgnc_id
    return row


class TestCcdsCmFields:
    """Tests for CCDS repository outputting cm_* fields matching Perl."""

    def test_cm_source_is_ccds(self) -> None:
        mock_session = MagicMock()
        ccds = _make_ccds_row()
        mock_session.execute.return_value = [(ccds,)]
        repo = Genew4CcdsCoordinateRepository(session=mock_session)
        records = repo.fetch_gene_coordinates()
        assert records[0].cm_source == "CCDS"

    def test_cm_source_id_is_ccds_id(self) -> None:
        mock_session = MagicMock()
        ccds = _make_ccds_row(ccds_id="CCDS1.1")
        mock_session.execute.return_value = [(ccds,)]
        repo = Genew4CcdsCoordinateRepository(session=mock_session)
        records = repo.fetch_gene_coordinates()
        assert records[0].cm_source_id == "CCDS1.1"

    def test_cm_notes_is_status(self) -> None:
        mock_session = MagicMock()
        ccds = _make_ccds_row(status="Public")
        mock_session.execute.return_value = [(ccds,)]
        repo = Genew4CcdsCoordinateRepository(session=mock_session)
        records = repo.fetch_gene_coordinates()
        assert records[0].cm_notes == "Public"

    def test_cm_hgnc_id_is_none(self) -> None:
        mock_session = MagicMock()
        ccds = _make_ccds_row()
        mock_session.execute.return_value = [(ccds,)]
        repo = Genew4CcdsCoordinateRepository(session=mock_session)
        records = repo.fetch_gene_coordinates()
        assert records[0].cm_hgnc_id is None

    def test_cm_eg_id_is_none(self) -> None:
        mock_session = MagicMock()
        ccds = _make_ccds_row()
        mock_session.execute.return_value = [(ccds,)]
        repo = Genew4CcdsCoordinateRepository(session=mock_session)
        records = repo.fetch_gene_coordinates()
        assert records[0].cm_eg_id is None

    def test_cm_mapby_is_ccds_id(self) -> None:
        mock_session = MagicMock()
        ccds = _make_ccds_row(ccds_id="CCDS1.1")
        mock_session.execute.return_value = [(ccds,)]
        repo = Genew4CcdsCoordinateRepository(session=mock_session)
        records = repo.fetch_gene_coordinates()
        assert records[0].cm_mapby == "CCDS1.1"

    def test_cm_strand_plus(self) -> None:
        mock_session = MagicMock()
        ccds = _make_ccds_row(strand="+")
        mock_session.execute.return_value = [(ccds,)]
        repo = Genew4CcdsCoordinateRepository(session=mock_session)
        records = repo.fetch_gene_coordinates()
        assert records[0].cm_strand == "+"

    def test_cm_strand_minus(self) -> None:
        mock_session = MagicMock()
        ccds = _make_ccds_row(strand="-")
        mock_session.execute.return_value = [(ccds,)]
        repo = Genew4CcdsCoordinateRepository(session=mock_session)
        records = repo.fetch_gene_coordinates()
        assert records[0].cm_strand == "-"

    def test_dedup_on_ccds_id_and_chr(self) -> None:
        mock_session = MagicMock()
        ccds1 = _make_ccds_row(ccds_id="CCDS1.1", chromosome="7")
        ccds2 = _make_ccds_row(ccds_id="CCDS1.1", chromosome="7")
        mock_session.execute.return_value = [(ccds1,), (ccds2,)]
        repo = Genew4CcdsCoordinateRepository(session=mock_session)
        records = repo.fetch_gene_coordinates()
        assert len(records) == 1

    def test_filters_out_dash_start(self) -> None:
        mock_session = MagicMock()
        ccds = _make_ccds_row(start="-")
        mock_session.execute.return_value = [(ccds,)]
        repo = Genew4CcdsCoordinateRepository(session=mock_session)
        records = repo.fetch_gene_coordinates()
        assert len(records) == 0

    def test_filters_out_dash_end(self) -> None:
        mock_session = MagicMock()
        ccds = _make_ccds_row(end="-")
        mock_session.execute.return_value = [(ccds,)]
        repo = Genew4CcdsCoordinateRepository(session=mock_session)
        records = repo.fetch_gene_coordinates()
        assert len(records) == 0


class TestCytobandCmFields:
    """Tests for Cytoband repository outputting cm_* fields matching Perl."""

    def test_cm_source_is_chrom(self) -> None:
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_conn.cursor.return_value.__enter__ = lambda s: mock_cursor
        mock_conn.cursor.return_value.__exit__ = lambda s, *a: None
        mock_cursor.fetchall.return_value = [
            ("Ensembl", "7", 100, 200, "p22"),
        ]
        repo = PsycopgCytobandCoordinateRepository(connection=mock_conn)
        records = repo.fetch_gene_coordinates()
        assert records[0].cm_source == "Chrom"

    def test_cm_strand_is_space(self) -> None:
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_conn.cursor.return_value.__enter__ = lambda s: mock_cursor
        mock_conn.cursor.return_value.__exit__ = lambda s, *a: None
        mock_cursor.fetchall.return_value = [
            ("Ensembl", "7", 100, 200, "p22"),
        ]
        repo = PsycopgCytobandCoordinateRepository(connection=mock_conn)
        records = repo.fetch_gene_coordinates()
        assert records[0].cm_strand == " "

    def test_cm_source_id_is_chr_band(self) -> None:
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_conn.cursor.return_value.__enter__ = lambda s: mock_cursor
        mock_conn.cursor.return_value.__exit__ = lambda s, *a: None
        mock_cursor.fetchall.return_value = [
            ("Ensembl", "7", 100, 200, "p22"),
        ]
        repo = PsycopgCytobandCoordinateRepository(connection=mock_conn)
        records = repo.fetch_gene_coordinates()
        assert records[0].cm_source_id == "7p22"

    def test_cm_mapby_is_chr_band(self) -> None:
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_conn.cursor.return_value.__enter__ = lambda s: mock_cursor
        mock_conn.cursor.return_value.__exit__ = lambda s, *a: None
        mock_cursor.fetchall.return_value = [
            ("Ensembl", "7", 100, 200, "p22"),
        ]
        repo = PsycopgCytobandCoordinateRepository(connection=mock_conn)
        records = repo.fetch_gene_coordinates()
        assert records[0].cm_mapby == "7p22"

    def test_cm_hgnc_id_is_none(self) -> None:
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_conn.cursor.return_value.__enter__ = lambda s: mock_cursor
        mock_conn.cursor.return_value.__exit__ = lambda s, *a: None
        mock_cursor.fetchall.return_value = [
            ("Ensembl", "7", 100, 200, "p22"),
        ]
        repo = PsycopgCytobandCoordinateRepository(connection=mock_conn)
        records = repo.fetch_gene_coordinates()
        assert records[0].cm_hgnc_id is None

    def test_cm_eg_id_is_none(self) -> None:
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_conn.cursor.return_value.__enter__ = lambda s: mock_cursor
        mock_conn.cursor.return_value.__exit__ = lambda s, *a: None
        mock_cursor.fetchall.return_value = [
            ("Ensembl", "7", 100, 200, "p22"),
        ]
        repo = PsycopgCytobandCoordinateRepository(connection=mock_conn)
        records = repo.fetch_gene_coordinates()
        assert records[0].cm_eg_id is None

    def test_cm_notes_is_none(self) -> None:
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_conn.cursor.return_value.__enter__ = lambda s: mock_cursor
        mock_conn.cursor.return_value.__exit__ = lambda s, *a: None
        mock_cursor.fetchall.return_value = [
            ("Ensembl", "7", 100, 200, "p22"),
        ]
        repo = PsycopgCytobandCoordinateRepository(connection=mock_conn)
        records = repo.fetch_gene_coordinates()
        assert records[0].cm_notes is None


def _make_porg_row(
    porg_id: int = 1,
    chromosome: str = "1",
    strand: str = "+",
    start: int = 500,
    end: int = 600,
    porg_class: str = "processed",
    porg_link: str = "https://example.com",
) -> MagicMock:
    row = MagicMock()
    row.porg_id = porg_id
    row.chromosome = chromosome
    row.strand = strand
    row.start = start
    row.end = end
    row.porg_class = porg_class
    row.porg_link = porg_link
    return row


class TestPseudogeneCmFields:
    """Tests for Pseudogene repository outputting cm_* fields matching Perl."""

    def test_cm_source_is_pseudogene_dot_org(self) -> None:
        mock_session = MagicMock()
        porg = _make_porg_row()
        mock_session.execute.return_value = [(porg,)]
        repo = Genew4PseudogeneCoordinateRepository(session=mock_session)
        records = repo.fetch_gene_coordinates()
        assert records[0].cm_source == "Pseudogene.org"

    def test_cm_source_id_is_porg_id_string(self) -> None:
        mock_session = MagicMock()
        porg = _make_porg_row(porg_id=42)
        mock_session.execute.return_value = [(porg,)]
        repo = Genew4PseudogeneCoordinateRepository(session=mock_session)
        records = repo.fetch_gene_coordinates()
        assert records[0].cm_source_id == "42"

    def test_cm_notes_is_class_comma_link(self) -> None:
        mock_session = MagicMock()
        porg = _make_porg_row(porg_class="processed", porg_link="https://example.com")
        mock_session.execute.return_value = [(porg,)]
        repo = Genew4PseudogeneCoordinateRepository(session=mock_session)
        records = repo.fetch_gene_coordinates()
        assert records[0].cm_notes == "processed, https://example.com"

    def test_cm_notes_empty_class(self) -> None:
        mock_session = MagicMock()
        porg = _make_porg_row(porg_class=None, porg_link="https://example.com")
        mock_session.execute.return_value = [(porg,)]
        repo = Genew4PseudogeneCoordinateRepository(session=mock_session)
        records = repo.fetch_gene_coordinates()
        assert records[0].cm_notes == ", https://example.com"

    def test_cm_notes_empty_link(self) -> None:
        mock_session = MagicMock()
        porg = _make_porg_row(porg_class="processed", porg_link=None)
        mock_session.execute.return_value = [(porg,)]
        repo = Genew4PseudogeneCoordinateRepository(session=mock_session)
        records = repo.fetch_gene_coordinates()
        assert records[0].cm_notes == "processed, "

    def test_cm_mapby_is_porg_id_string(self) -> None:
        mock_session = MagicMock()
        porg = _make_porg_row(porg_id=42)
        mock_session.execute.return_value = [(porg,)]
        repo = Genew4PseudogeneCoordinateRepository(session=mock_session)
        records = repo.fetch_gene_coordinates()
        assert records[0].cm_mapby == "42"

    def test_cm_hgnc_id_is_none(self) -> None:
        mock_session = MagicMock()
        porg = _make_porg_row()
        mock_session.execute.return_value = [(porg,)]
        repo = Genew4PseudogeneCoordinateRepository(session=mock_session)
        records = repo.fetch_gene_coordinates()
        assert records[0].cm_hgnc_id is None

    def test_cm_eg_id_is_none(self) -> None:
        mock_session = MagicMock()
        porg = _make_porg_row()
        mock_session.execute.return_value = [(porg,)]
        repo = Genew4PseudogeneCoordinateRepository(session=mock_session)
        records = repo.fetch_gene_coordinates()
        assert records[0].cm_eg_id is None

    def test_cm_strand_defaults_to_minus_when_none(self) -> None:
        mock_session = MagicMock()
        porg = _make_porg_row(strand=None)
        mock_session.execute.return_value = [(porg,)]
        repo = Genew4PseudogeneCoordinateRepository(session=mock_session)
        records = repo.fetch_gene_coordinates()
        assert records[0].cm_strand == "-"
