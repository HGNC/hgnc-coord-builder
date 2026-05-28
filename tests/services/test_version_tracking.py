"""Tests for VersionTracker integration in CoordBuilderService.

Validates that the service correctly checks version staleness before
running and records the version after successful promotion.
"""

from __future__ import annotations

import logging
from unittest.mock import MagicMock

import pytest

from hgnc_coord_builder.domain.models import CoordinateRecord, CoordSource
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
    repos = {}
    for name in ("ncbi", "ensembl", "ccds", "cytoband", "pseudogene"):
        repo = MagicMock()
        repo.fetch_gene_coordinates.return_value = []
        repos[name] = repo
    staging = MagicMock()
    staging.prepare_staging_table.return_value = "coord_match_grch38_update"
    staging.bulk_copy_coordinates.return_value = 0
    repos["staging"] = staging
    return repos


def _make_service(
    repos: dict | None = None,
    version_tracker: MagicMock | None = None,
) -> CoordBuilderService:
    if repos is None:
        repos = _make_repos()
    return CoordBuilderService(
        ncbi_repository=repos["ncbi"],
        ensembl_repository=repos["ensembl"],
        ccds_repository=repos["ccds"],
        cytoband_repository=repos["cytoband"],
        pseudogene_repository=repos["pseudogene"],
        staging_repository=repos["staging"],
        logger=logging.getLogger("test"),
        version_tracker=version_tracker,
    )


class TestCoordBuilderVersionTracking:
    """Tests for VersionTracker integration."""

    def test_skips_run_when_version_unchanged(self) -> None:
        tracker = MagicMock()
        tracker.should_skip.return_value = True

        repos = _make_repos()
        service = _make_service(repos=repos, version_tracker=tracker)
        metrics = service.run()

        repos["ncbi"].fetch_gene_coordinates.assert_not_called()
        repos["staging"].prepare_staging_table.assert_not_called()
        assert metrics.total_fetched == 0

    def test_runs_when_version_changed(self) -> None:
        tracker = MagicMock()
        tracker.should_skip.return_value = False

        repos = _make_repos()
        service = _make_service(repos=repos, version_tracker=tracker)
        service.run()

        repos["ncbi"].fetch_gene_coordinates.assert_called_once()
        repos["staging"].prepare_staging_table.assert_called_once()

    def test_runs_without_version_tracker(self) -> None:
        repos = _make_repos()
        service = _make_service(repos=repos, version_tracker=None)
        service.run()

        repos["ncbi"].fetch_gene_coordinates.assert_called_once()

    def test_records_version_after_success(self) -> None:
        tracker = MagicMock()
        tracker.should_skip.return_value = False

        repos = _make_repos()
        service = _make_service(repos=repos, version_tracker=tracker)
        service.run()

        tracker.record_version.assert_called_once()

    def test_does_not_record_version_on_skip(self) -> None:
        tracker = MagicMock()
        tracker.should_skip.return_value = True

        repos = _make_repos()
        service = _make_service(repos=repos, version_tracker=tracker)
        service.run()

        tracker.record_version.assert_not_called()

    def test_does_not_record_version_on_staging_error(self) -> None:
        tracker = MagicMock()
        tracker.should_skip.return_value = False

        repos = _make_repos()
        repos["staging"].prepare_staging_table.side_effect = RepositoryError(
            "staging failed"
        )
        service = _make_service(repos=repos, version_tracker=tracker)

        with pytest.raises(RepositoryError):
            service.run()

        tracker.record_version.assert_not_called()
