"""Tests for CoordinateRecord model with cm_* DDL schema alignment.

Validates that the CoordinateRecord domain model exposes fields matching
the production coord_match_grch38 staging table DDL columns and that
to_dict() returns exactly the keys required for COPY bulk load.
"""

from __future__ import annotations

import pytest

from hgnc_coord_builder.domain.models import CoordinateRecord

_CM_COLUMNS = {
    "cm_source",
    "cm_strand",
    "cm_chr",
    "cm_start",
    "cm_end",
    "cm_source_id",
    "cm_eg_id",
    "cm_hgnc_id",
    "cm_notes",
    "cm_mark",
    "cm_mapby",
}


class TestCoordinateRecordCmSchema:
    """Tests for CoordinateRecord field alignment with cm_* DDL schema."""

    def test_to_dict_has_exactly_eleven_cm_columns(self) -> None:
        record = CoordinateRecord(
            cm_source="NCBI",
            cm_strand="+",
            cm_chr="7",
            cm_start=100,
            cm_end=200,
            cm_source_id="NM_000492.4",
            cm_eg_id=12345,
            cm_hgnc_id=12345,
            cm_notes="NC_000007.14",
            cm_mark=None,
            cm_mapby="12345",
        )
        result = record.to_dict()
        assert set(result.keys()) == _CM_COLUMNS
        assert len(result) == 11

    def test_to_dict_no_legacy_keys(self) -> None:
        record = CoordinateRecord(
            cm_source="NCBI",
            cm_strand="+",
            cm_chr="7",
            cm_start=100,
            cm_end=200,
            cm_source_id="NM_000492.4",
            cm_eg_id=12345,
            cm_hgnc_id=12345,
            cm_notes="NC_000007.14",
            cm_mark=None,
            cm_mapby="12345",
        )
        result = record.to_dict()
        legacy_keys = {
            "hgnc_id",
            "chromosome",
            "start",
            "end",
            "strand",
            "source",
            "symbol",
            "ensembl_gene_id",
            "mapping_type",
        }
        for key in legacy_keys:
            assert key not in result, f"Legacy key {key!r} found in to_dict()"

    def test_to_dict_cm_source_value(self) -> None:
        record = CoordinateRecord(
            cm_source="NCBI",
            cm_strand="+",
            cm_chr="7",
            cm_start=100,
            cm_end=200,
            cm_source_id="NM_000492.4",
            cm_eg_id=12345,
            cm_hgnc_id=12345,
            cm_notes="NC_000007.14",
            cm_mark=None,
            cm_mapby="12345",
        )
        assert record.to_dict()["cm_source"] == "NCBI"

    def test_to_dict_cm_hgnc_id_is_integer(self) -> None:
        record = CoordinateRecord(
            cm_source="NCBI",
            cm_strand="+",
            cm_chr="7",
            cm_start=100,
            cm_end=200,
            cm_source_id="NM_000492.4",
            cm_eg_id=12345,
            cm_hgnc_id=12345,
            cm_notes="NC_000007.14",
            cm_mark=None,
            cm_mapby="12345",
        )
        assert record.to_dict()["cm_hgnc_id"] == 12345
        assert isinstance(record.to_dict()["cm_hgnc_id"], int)

    def test_to_dict_cm_eg_id_is_integer(self) -> None:
        record = CoordinateRecord(
            cm_source="NCBI",
            cm_strand="+",
            cm_chr="7",
            cm_start=100,
            cm_end=200,
            cm_source_id="NM_000492.4",
            cm_eg_id=12345,
            cm_hgnc_id=12345,
            cm_notes="NC_000007.14",
            cm_mark=None,
            cm_mapby="12345",
        )
        assert record.to_dict()["cm_eg_id"] == 12345
        assert isinstance(record.to_dict()["cm_eg_id"], int)

    def test_to_dict_none_fields_become_empty_string(self) -> None:
        record = CoordinateRecord(
            cm_source="CCDS",
            cm_strand="+",
            cm_chr="7",
            cm_start=100,
            cm_end=200,
            cm_source_id="CCDS1.1",
            cm_eg_id=None,
            cm_hgnc_id=None,
            cm_notes=None,
            cm_mark=None,
            cm_mapby="CCDS1.1",
        )
        result = record.to_dict()
        assert result["cm_eg_id"] == ""
        assert result["cm_hgnc_id"] == ""
        assert result["cm_notes"] == ""
        assert result["cm_mark"] == ""

    def test_cytoband_strand_is_space_character(self) -> None:
        record = CoordinateRecord(
            cm_source="Chrom",
            cm_strand=" ",
            cm_chr="7",
            cm_start=100,
            cm_end=200,
            cm_source_id="7p22",
            cm_eg_id=None,
            cm_hgnc_id=None,
            cm_notes=None,
            cm_mark=None,
            cm_mapby="7p22",
        )
        assert record.to_dict()["cm_strand"] == " "
        assert record.to_dict()["cm_source"] == "Chrom"

    def test_ensembl_notes_format(self) -> None:
        record = CoordinateRecord(
            cm_source="Ensembl",
            cm_strand="+",
            cm_chr="7",
            cm_start=100,
            cm_end=200,
            cm_source_id="ENSG000001",
            cm_eg_id=None,
            cm_hgnc_id=None,
            cm_notes="source => ensembl_havana, status => NULL, desc =>CFTR, biotype => protein_coding",
            cm_mark=None,
            cm_mapby="ENSG000001",
        )
        assert "source =>" in record.to_dict()["cm_notes"]
        assert "biotype =>" in record.to_dict()["cm_notes"]

    def test_pseudogene_source_name(self) -> None:
        record = CoordinateRecord(
            cm_source="Pseudogene.org",
            cm_strand="-",
            cm_chr="1",
            cm_start=500,
            cm_end=600,
            cm_source_id="1",
            cm_eg_id=None,
            cm_hgnc_id=None,
            cm_notes="processed, https://example.com",
            cm_mark=None,
            cm_mapby="1",
        )
        assert record.to_dict()["cm_source"] == "Pseudogene.org"

    def test_ncbi_source_name(self) -> None:
        record = CoordinateRecord(
            cm_source="NCBI",
            cm_strand="+",
            cm_chr="7",
            cm_start=100,
            cm_end=200,
            cm_source_id="NM_000492.4",
            cm_eg_id=12345,
            cm_hgnc_id=12345,
            cm_notes="NC_000007.14",
            cm_mark=None,
            cm_mapby="12345",
        )
        assert record.to_dict()["cm_source"] == "NCBI"

    def test_ccds_source_name(self) -> None:
        record = CoordinateRecord(
            cm_source="CCDS",
            cm_strand="+",
            cm_chr="7",
            cm_start=100,
            cm_end=200,
            cm_source_id="CCDS1.1",
            cm_eg_id=None,
            cm_hgnc_id=None,
            cm_notes="Public",
            cm_mark=None,
            cm_mapby="CCDS1.1",
        )
        assert record.to_dict()["cm_source"] == "CCDS"


class TestCoordinateRecordOptionalFields:
    """Tests for optional field handling in CoordinateRecord."""

    def test_cm_eg_id_accepts_none(self) -> None:
        record = CoordinateRecord(
            cm_source="CCDS",
            cm_strand="+",
            cm_chr="7",
            cm_start=100,
            cm_end=200,
            cm_source_id="CCDS1.1",
            cm_eg_id=None,
            cm_hgnc_id=None,
            cm_notes=None,
            cm_mark=None,
            cm_mapby="CCDS1.1",
        )
        assert record.cm_eg_id is None

    def test_cm_hgnc_id_accepts_none(self) -> None:
        record = CoordinateRecord(
            cm_source="Ensembl",
            cm_strand="+",
            cm_chr="7",
            cm_start=100,
            cm_end=200,
            cm_source_id="ENSG000001",
            cm_eg_id=None,
            cm_hgnc_id=None,
            cm_notes=None,
            cm_mark=None,
            cm_mapby="ENSG000001",
        )
        assert record.cm_hgnc_id is None

    def test_cm_notes_accepts_none(self) -> None:
        record = CoordinateRecord(
            cm_source="CCDS",
            cm_strand="+",
            cm_chr="7",
            cm_start=100,
            cm_end=200,
            cm_source_id="CCDS1.1",
            cm_eg_id=None,
            cm_hgnc_id=None,
            cm_notes=None,
            cm_mark=None,
            cm_mapby="CCDS1.1",
        )
        assert record.cm_notes is None

    def test_cm_mark_accepts_none(self) -> None:
        record = CoordinateRecord(
            cm_source="CCDS",
            cm_strand="+",
            cm_chr="7",
            cm_start=100,
            cm_end=200,
            cm_source_id="CCDS1.1",
            cm_eg_id=None,
            cm_hgnc_id=None,
            cm_notes=None,
            cm_mark=None,
            cm_mapby="CCDS1.1",
        )
        assert record.cm_mark is None


class TestCoordinateRecordValidation:
    """Tests for field validation in CoordinateRecord."""

    def test_cm_start_must_be_positive(self) -> None:
        with pytest.raises(Exception):
            CoordinateRecord(
                cm_source="NCBI",
                cm_strand="+",
                cm_chr="7",
                cm_start=0,
                cm_end=200,
                cm_source_id="NM_000492.4",
                cm_eg_id=12345,
                cm_hgnc_id=12345,
                cm_notes="NC_000007.14",
                cm_mark=None,
                cm_mapby="12345",
            )

    def test_cm_end_must_be_positive(self) -> None:
        with pytest.raises(Exception):
            CoordinateRecord(
                cm_source="NCBI",
                cm_strand="+",
                cm_chr="7",
                cm_start=100,
                cm_end=0,
                cm_source_id="NM_000492.4",
                cm_eg_id=12345,
                cm_hgnc_id=12345,
                cm_notes="NC_000007.14",
                cm_mark=None,
                cm_mapby="12345",
            )

    def test_cm_source_required(self) -> None:
        with pytest.raises(Exception):
            CoordinateRecord(
                cm_source=None,
                cm_strand="+",
                cm_chr="7",
                cm_start=100,
                cm_end=200,
                cm_source_id="NM_000492.4",
                cm_eg_id=12345,
                cm_hgnc_id=12345,
                cm_notes="NC_000007.14",
                cm_mark=None,
                cm_mapby="12345",
            )

    def test_cm_chr_required(self) -> None:
        with pytest.raises(Exception):
            CoordinateRecord(
                cm_source="NCBI",
                cm_strand="+",
                cm_chr=None,
                cm_start=100,
                cm_end=200,
                cm_source_id="NM_000492.4",
                cm_eg_id=12345,
                cm_hgnc_id=12345,
                cm_notes="NC_000007.14",
                cm_mark=None,
                cm_mapby="12345",
            )

    def test_cm_source_id_required(self) -> None:
        with pytest.raises(Exception):
            CoordinateRecord(
                cm_source="NCBI",
                cm_strand="+",
                cm_chr="7",
                cm_start=100,
                cm_end=200,
                cm_source_id=None,
                cm_eg_id=12345,
                cm_hgnc_id=12345,
                cm_notes="NC_000007.14",
                cm_mark=None,
                cm_mapby="12345",
            )

    def test_cm_mapby_required(self) -> None:
        with pytest.raises(Exception):
            CoordinateRecord(
                cm_source="NCBI",
                cm_strand="+",
                cm_chr="7",
                cm_start=100,
                cm_end=200,
                cm_source_id="NM_000492.4",
                cm_eg_id=12345,
                cm_hgnc_id=12345,
                cm_notes="NC_000007.14",
                cm_mark=None,
                cm_mapby=None,
            )


class TestCoordinateRecordSortOrder:
    """Tests for deterministic sort ordering of CoordinateRecord."""

    def test_sorts_by_cm_hgnc_id_then_cm_chr(self) -> None:
        r1 = CoordinateRecord(
            cm_source="NCBI",
            cm_strand="+",
            cm_chr="7",
            cm_start=100,
            cm_end=200,
            cm_source_id="A",
            cm_eg_id=None,
            cm_hgnc_id=1,
            cm_notes=None,
            cm_mark=None,
            cm_mapby="A",
        )
        r2 = CoordinateRecord(
            cm_source="NCBI",
            cm_strand="+",
            cm_chr="1",
            cm_start=100,
            cm_end=200,
            cm_source_id="B",
            cm_eg_id=None,
            cm_hgnc_id=2,
            cm_notes=None,
            cm_mark=None,
            cm_mapby="B",
        )
        r3 = CoordinateRecord(
            cm_source="NCBI",
            cm_strand="+",
            cm_chr="X",
            cm_start=100,
            cm_end=200,
            cm_source_id="C",
            cm_eg_id=None,
            cm_hgnc_id=1,
            cm_notes=None,
            cm_mark=None,
            cm_mapby="C",
        )
        assert sorted([r2, r1, r3]) == [r1, r3, r2]
