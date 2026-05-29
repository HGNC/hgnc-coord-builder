"""Tests for CoordBuilderService orchestration.

Validates that CoordBuilderService correctly orchestrates all five
sub-source repositories, merges results, and delegates to the staging
repository lifecycle.
"""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from hgnc_coord_builder.domain.models import CoordinateRecord, CoordMetrics
from hgnc_coord_builder.exceptions import RepositoryError
from hgnc_coord_builder.services.coord_builder_service import CoordBuilderService


def _make_record(
    cm_source: str = "NCBI",
    cm_strand: str = "+",
    cm_chr: str = "7",
    cm_start: int = 100,
    cm_end: int = 200,
    cm_source_id: str = "NM_000492.4",
    cm_eg_id: int | None = 12345,
    cm_hgnc_id: int | None = 12345,
    cm_notes: str | None = None,
    cm_mark: str | None = None,
    cm_mapby: str = "12345",
) -> CoordinateRecord:
    return CoordinateRecord(
        cm_source=cm_source,
        cm_strand=cm_strand,
        cm_chr=cm_chr,
        cm_start=cm_start,
        cm_end=cm_end,
        cm_source_id=cm_source_id,
        cm_eg_id=cm_eg_id,
        cm_hgnc_id=cm_hgnc_id,
        cm_notes=cm_notes,
        cm_mark=cm_mark,
        cm_mapby=cm_mapby,
    )


def _make_repos() -> dict:
    ncbi = MagicMock()
    ensembl = MagicMock()
    ccds = MagicMock()
    cytoband = MagicMock()
    pseudogene = MagicMock()
    staging = MagicMock()
    staging.prepare_staging_table.return_value = "coord_match_grch38_update"
    staging.bulk_copy_coordinates.return_value = 0
    return {
        "ncbi": ncbi,
        "ensembl": ensembl,
        "ccds": ccds,
        "cytoband": cytoband,
        "pseudogene": pseudogene,
        "staging": staging,
    }


def _make_service(repos: dict | None = None) -> CoordBuilderService:
    if repos is None:
        repos = _make_repos()
    import logging

    return CoordBuilderService(
        ncbi_repository=repos["ncbi"],
        ensembl_repository=repos["ensembl"],
        ccds_repository=repos["ccds"],
        cytoband_repository=repos["cytoband"],
        pseudogene_repository=repos["pseudogene"],
        staging_repository=repos["staging"],
        logger=logging.getLogger("test"),
    )


class TestCoordBuilderServiceOrchestration:
    """Tests for CoordBuilderService multi-source orchestration."""

    def test_fetches_from_all_five_sources(self) -> None:
        repos = _make_repos()
        repos["ncbi"].fetch_gene_coordinates.return_value = []
        repos["ensembl"].fetch_gene_coordinates.return_value = []
        repos["ccds"].fetch_gene_coordinates.return_value = []
        repos["cytoband"].fetch_gene_coordinates.return_value = []
        repos["pseudogene"].fetch_gene_coordinates.return_value = []

        service = _make_service(repos)
        service.run()

        repos["ncbi"].fetch_gene_coordinates.assert_called_once()
        repos["ensembl"].fetch_gene_coordinates.assert_called_once()
        repos["ccds"].fetch_gene_coordinates.assert_called_once()
        repos["cytoband"].fetch_gene_coordinates.assert_called_once()
        repos["pseudogene"].fetch_gene_coordinates.assert_called_once()

    def test_merges_records_from_all_sources(self) -> None:
        repos = _make_repos()
        repos["ncbi"].fetch_gene_coordinates.return_value = [
            _make_record(cm_source="NCBI", cm_hgnc_id=1),
        ]
        repos["ensembl"].fetch_gene_coordinates.return_value = [
            _make_record(cm_source="Ensembl", cm_hgnc_id=2, cm_eg_id=None),
        ]
        repos["ccds"].fetch_gene_coordinates.return_value = [
            _make_record(cm_source="CCDS", cm_hgnc_id=None, cm_eg_id=None),
        ]
        repos["cytoband"].fetch_gene_coordinates.return_value = [
            _make_record(cm_source="Chrom", cm_strand=" ", cm_hgnc_id=None, cm_eg_id=None),
        ]
        repos["pseudogene"].fetch_gene_coordinates.return_value = [
            _make_record(cm_source="Pseudogene.org", cm_hgnc_id=None, cm_eg_id=None),
        ]

        service = _make_service(repos)
        metrics = service.run()

        assert metrics.total_fetched == 5
        assert metrics.total_merged == 5
        repos["staging"].bulk_copy_coordinates.assert_called_once()
        call_args = repos["staging"].bulk_copy_coordinates.call_args
        assert len(call_args[0][1]) == 5

    def test_stages_and_promotes(self) -> None:
        repos = _make_repos()
        repos["ncbi"].fetch_gene_coordinates.return_value = [
            _make_record(cm_source="NCBI"),
        ]

        service = _make_service(repos)
        service.run()

        repos["staging"].prepare_staging_table.assert_called_once()
        repos["staging"].create_staging_indexes.assert_called_once()
        repos["staging"].validate_row_count.assert_called_once()
        repos["staging"].promote_staging_to_production.assert_called_once()

    def test_returns_metrics(self) -> None:
        repos = _make_repos()
        repos["ncbi"].fetch_gene_coordinates.return_value = [
            _make_record(cm_source="NCBI"),
            _make_record(cm_source="NCBI", cm_hgnc_id=2),
        ]
        repos["ensembl"].fetch_gene_coordinates.return_value = [
            _make_record(cm_source="Ensembl", cm_eg_id=None),
        ]

        service = _make_service(repos)
        metrics = service.run()

        assert isinstance(metrics, CoordMetrics)
        assert metrics.total_fetched == 3
        assert metrics.total_merged == 3

    def test_handles_empty_all_sources(self) -> None:
        repos = _make_repos()
        service = _make_service(repos)
        metrics = service.run()

        assert metrics.total_fetched == 0
        assert metrics.total_merged == 0
        repos["staging"].bulk_copy_coordinates.assert_called_once()

    def test_propagates_staging_error(self) -> None:
        repos = _make_repos()
        repos["staging"].prepare_staging_table.side_effect = RepositoryError(
            "staging failed"
        )
        service = _make_service(repos)

        with pytest.raises(RepositoryError, match="staging failed"):
            service.run()

    def test_propagates_source_error(self) -> None:
        repos = _make_repos()
        repos["ncbi"].fetch_gene_coordinates.side_effect = RepositoryError(
            "NCBI query failed"
        )
        service = _make_service(repos)

        with pytest.raises(RepositoryError, match="NCBI"):
            service.run()

    def test_calls_post_load_annotations_after_promotion(self) -> None:
        repos = _make_repos()
        repos["ncbi"].fetch_gene_coordinates.return_value = [
            _make_record(cm_source="NCBI"),
        ]

        service = _make_service(repos)
        service.run()

        repos["staging"].promote_staging_to_production.assert_called_once()
        repos["staging"].set_default_cm_mark.assert_called_once()
        repos["staging"].set_default_cm_note.assert_called_once()

    def test_post_load_called_in_correct_order(self) -> None:
        repos = _make_repos()
        repos["ncbi"].fetch_gene_coordinates.return_value = [
            _make_record(cm_source="NCBI"),
        ]

        call_order: list[str] = []
        repos["staging"].promote_staging_to_production.side_effect = (
            lambda *a, **k: call_order.append("promote")
        )
        repos["staging"].set_default_cm_mark.side_effect = (
            lambda *a, **k: call_order.append("cm_mark")
        )
        repos["staging"].set_default_cm_note.side_effect = (
            lambda *a, **k: call_order.append("cm_note")
        )

        service = _make_service(repos)
        service.run()

        assert call_order == ["promote", "cm_mark", "cm_note"]
