"""Main service for the HGNC coordinate builder.

Wires all five sub-source repositories and CoordBuilderService together.
The CLI constructs this service with concrete repository instances, then
calls run() to execute the workflow.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from hgnc_coord_builder.services.base_service import Service
from hgnc_coord_builder.services.coord_builder_service import CoordBuilderService

if TYPE_CHECKING:
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


class MainService(Service):
    """Orchestrate the HGNC coordinate building workflow.

    Wires all five sub-source repositories and the staging repository
    to CoordBuilderService. The CLI builds this service with concrete
    implementations, then delegates to run().

    Args:
        ncbi_repository: NCBI coordinate reader.
        ensembl_repository: Ensembl coordinate reader.
        ccds_repository: CCDS coordinate reader.
        cytoband_repository: Cytoband coordinate reader.
        pseudogene_repository: Pseudogene coordinate reader.
        staging_repository: Postgres staging writer.
    """

    def __init__(
        self,
        ncbi_repository: NcbiCoordinateRepository,
        ensembl_repository: EnsemblCoordinateRepository,
        ccds_repository: CcdsCoordinateRepository,
        cytoband_repository: CytobandCoordinateRepository,
        pseudogene_repository: PseudogeneCoordinateRepository,
        staging_repository: CoordStagingRepository,
    ) -> None:
        """Initialise with all five sub-source repos and staging repo."""
        self._ncbi_repository = ncbi_repository
        self._ensembl_repository = ensembl_repository
        self._ccds_repository = ccds_repository
        self._cytoband_repository = cytoband_repository
        self._pseudogene_repository = pseudogene_repository
        self._staging_repository = staging_repository

    def run(self) -> None:
        """Execute the coordinate building workflow.

        Creates a CoordBuilderService with the injected repositories
        and delegates the workflow.
        """
        logger = logging.getLogger("hgnc_coord_builder")

        service = CoordBuilderService(
            ncbi_repository=self._ncbi_repository,
            ensembl_repository=self._ensembl_repository,
            ccds_repository=self._ccds_repository,
            cytoband_repository=self._cytoband_repository,
            pseudogene_repository=self._pseudogene_repository,
            staging_repository=self._staging_repository,
            logger=logger,
        )
        service.run()
