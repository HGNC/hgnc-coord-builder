"""CoordBuilder service: multi-source merge and staging orchestration.

Orchestrates the coordinate building workflow: fetch coordinates from
all five sub-source repositories (NCBI, Ensembl, CCDS, Cytoband,
Pseudogene), sort/merge, and push through the staging repository
lifecycle (prepare, COPY, indexes, validate, promote). Optionally
integrates version tracking to skip unchanged runs.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from hgnc_coord_builder.domain.models import CoordinateRecord, CoordMetrics
from hgnc_coord_builder.services.base_service import Service

if TYPE_CHECKING:
    import logging

    from hgnc_coord_builder.repositories.ccds_coordinate_repository import (
        CcdsCoordinateRepository,
    )
    from hgnc_coord_builder.repositories.coord_staging_repository import (
        CoordStagingRepository,
    )
    from hgnc_coord_builder.repositories.cytoband_coordinate_repository import (
        CytobandCoordinateRepository,
    )
    from hgnc_coord_builder.repositories.ensembl_coordinate_repository import (
        EnsemblCoordinateRepository,
    )
    from hgnc_coord_builder.repositories.ncbi_coordinate_repository import (
        NcbiCoordinateRepository,
    )
    from hgnc_coord_builder.repositories.pseudogene_coordinate_repository import (
        PseudogeneCoordinateRepository,
    )

_COORD_TABLE_NAME = "coord_match_grch38"


class CoordBuilderService(Service):
    """Orchestrate the HGNC coordinate building workflow.

    Fetches gene coordinates from all five sub-source repositories,
    merges and sorts them deterministically, and stages them for
    atomic promotion into ``coord_match_grch38``. Optionally checks
    version staleness before running and records the version after
    successful promotion.

    Args:
        ncbi_repository: Abstract NCBI coordinate reader.
        ensembl_repository: Abstract Ensembl coordinate reader.
        ccds_repository: Abstract CCDS coordinate reader.
        cytoband_repository: Abstract cytoband coordinate reader.
        pseudogene_repository: Abstract pseudogene coordinate reader.
        staging_repository: Abstract Postgres staging/promotion writer.
        logger: Logger instance for structured output.
        version_tracker: Optional version tracker for staleness checks.
    """

    def __init__(
        self,
        ncbi_repository: NcbiCoordinateRepository,
        ensembl_repository: EnsemblCoordinateRepository,
        ccds_repository: CcdsCoordinateRepository,
        cytoband_repository: CytobandCoordinateRepository,
        pseudogene_repository: PseudogeneCoordinateRepository,
        staging_repository: CoordStagingRepository,
        logger: logging.Logger,
        version_tracker: object | None = None,
    ) -> None:
        """Initialise with all five sub-source repos and staging repo."""
        self._ncbi_repository = ncbi_repository
        self._ensembl_repository = ensembl_repository
        self._ccds_repository = ccds_repository
        self._cytoband_repository = cytoband_repository
        self._pseudogene_repository = pseudogene_repository
        self._staging_repository = staging_repository
        self._logger = logger
        self._version_tracker = version_tracker

    def run(self) -> CoordMetrics:
        """Execute the coordinate building workflow.

        If a version tracker is configured, checks staleness before
        running. If the version is unchanged, returns early with empty
        metrics. Otherwise fetches coordinates from all five sub-sources,
        merges and sorts them, stages and promotes, then records the
        new version.

        Returns:
            CoordMetrics with counts for observability.

        Raises:
            RepositoryError: If any repository operation fails.
            CoordPromotionError: If staging promotion fails.
        """
        metrics = CoordMetrics()

        if self._should_skip():
            self._logger.info(
                "coord_build_skipped_version_unchanged",
            )
            return metrics

        all_records = self._fetch_all_sources(metrics)
        metrics.total_merged = len(all_records)

        self._stage_and_promote(all_records, metrics)
        self._record_version()

        return metrics

    def _should_skip(self) -> bool:
        """Check version staleness if a tracker is configured.

        Returns:
            True if the run should be skipped due to unchanged version.
        """
        if self._version_tracker is None:
            return False
        return self._version_tracker.should_skip(
            _COORD_TABLE_NAME, ""
        )

    def _record_version(self) -> None:
        """Record the new version after a successful run."""
        if self._version_tracker is None:
            return
        self._version_tracker.record_version(
            _COORD_TABLE_NAME, ""
        )

    def _fetch_all_sources(self, metrics: CoordMetrics) -> list[CoordinateRecord]:
        """Fetch coordinates from all five sub-sources.

        Args:
            metrics: Metrics container to update with fetched counts.

        Returns:
            Merged and sorted list of all coordinate records.
        """
        all_records: list[CoordinateRecord] = []

        sources = [
            ("ncbi", self._ncbi_repository),
            ("ensembl", self._ensembl_repository),
            ("ccds", self._ccds_repository),
            ("cytoband", self._cytoband_repository),
            ("pseudogene", self._pseudogene_repository),
        ]

        for name, repo in sources:
            records = repo.fetch_gene_coordinates()
            metrics.total_fetched += len(records)
            self._logger.info(
                "coordinates_fetched",
                extra={"source": name, "count": len(records)},
            )
            all_records.extend(records)

        return sorted(all_records)

    def _stage_and_promote(
        self, records: list[CoordinateRecord], metrics: CoordMetrics
    ) -> None:
        """Stage records and promote to production.

        Args:
            records: Sorted coordinate records to stage.
            metrics: Metrics container for logging.
        """
        dict_records = [r.to_dict() for r in records]

        staging_table = self._staging_repository.prepare_staging_table()
        self._logger.info(
            "staging_prepared",
            extra={"staging_table": staging_table},
        )

        loaded_count = self._staging_repository.bulk_copy_coordinates(
            staging_table, dict_records
        )
        self._logger.info(
            "bulk_copy_complete",
            extra={"staging_table": staging_table, "loaded": loaded_count},
        )

        self._staging_repository.create_staging_indexes(staging_table)

        self._staging_repository.validate_row_count(staging_table, len(records))

        self._staging_repository.promote_staging_to_production(staging_table)

        self._staging_repository.set_default_cm_mark()
        self._staging_repository.set_default_cm_note()

        self._logger.info(
            "coord_build_complete",
            extra=metrics.snapshot(),
        )
