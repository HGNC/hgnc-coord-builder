"""CLI entrypoint for the HGNC coordinate builder batch job."""

from __future__ import annotations

import sys

from hgnc_coord_builder.config import Settings
from hgnc_coord_builder.exceptions import ConfigError, ServiceError
from hgnc_coord_builder.logging_config import configure_logging
from hgnc_coord_builder.services.main_service import MainService


def main(argv: list[str] | None = None) -> int:
    """Run the HGNC coordinate builder batch job.

    This function is the controller for the batch job. It handles
    configuration loading, logging setup, service wiring, and
    exit-code mapping. It MUST NOT contain business logic.

    Args:
        argv: Command-line arguments. Defaults to ``sys.argv[1:]``.

    Returns:
        Exit code: 0 for success, 1 for unexpected error,
        2 for configuration error, 3 for domain error.
    """
    argv = argv or sys.argv[1:]
    configure_logging()

    try:
        settings = Settings()
    except ConfigError:
        return 2
    except Exception:
        return 2

    try:
        from hgnc_coord_builder.repositories.wiring import (
            build_ccds_repository,
            build_cytoband_repository,
            build_ensembl_repository,
            build_genew4_engine,
            build_ncbi_repository,
            build_pseudogene_repository,
            build_staging_repository,
        )

        engine = build_genew4_engine(settings)
        service = MainService(
            ncbi_repository=build_ncbi_repository(settings, engine),
            ensembl_repository=build_ensembl_repository(settings),
            ccds_repository=build_ccds_repository(settings, engine),
            cytoband_repository=build_cytoband_repository(settings, engine),
            pseudogene_repository=build_pseudogene_repository(settings, engine),
            staging_repository=build_staging_repository(settings, engine),
        )
        service.run()
    except ConfigError:
        return 2
    except ServiceError:
        return 3
    except Exception:
        return 1
    return 0
