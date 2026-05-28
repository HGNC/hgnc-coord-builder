"""Tests for CoordBuilderService orchestration.

Validates that CoordBuilderService correctly orchestrates all five
sub-source repositories, merges results, and delegates to the staging
repository lifecycle.
"""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from hgnc_coord_builder.domain.models import CoordinateRecord, CoordMetrics, CoordSource
from hgnc_coord_builder.exceptions import RepositoryError
from hgnc_coord_builder.services.coord_builder_service import CoordBuilderService


def _make_record(
    hgnc_id: str = "HGNC:1100",
    chromosome: str = "7",
    start: int = 100,
    end: int = 200,
    strand: int = 1,
    source: CoordSource = CoordSource.NCBI,
) -> CoordinateRecord:
    return CoordinateRecord(
        hgnc_id=hgnc_id,
        chromosome=chromosome,
        start=start,
        end=end,
        strand=strand,
        source=source,
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
            _make_record(hgnc_id="HGNC:1", source=CoordSource.NCBI),
        ]
        repos["ensembl"].fetch_gene_coordinates.return_value = [
            _make_record(hgnc_id="HGNC:2", source=CoordSource.ENSEMBL),
        ]
        repos["ccds"].fetch_gene_coordinates.return_value = [
            _make_record(hgnc_id="HGNC:3", source=CoordSource.CCDS),
        ]
        repos["cytoband"].fetch_gene_coordinates.return_value = [
            _make_record(hgnc_id="cytoband:7:p22", source=CoordSource.CYTOBAND),
        ]
        repos["pseudogene"].fetch_gene_coordinates.return_value = [
            _make_record(hgnc_id="pseudogene:1", source=CoordSource.PSEUDOGENE),
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
            _make_record(source=CoordSource.NCBI),
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
            _make_record(source=CoordSource.NCBI),
            _make_record(hgnc_id="HGNC:2", source=CoordSource.NCBI),
        ]
        repos["ensembl"].fetch_gene_coordinates.return_value = [
            _make_record(source=CoordSource.ENSEMBL),
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
