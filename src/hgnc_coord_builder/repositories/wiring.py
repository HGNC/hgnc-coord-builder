"""Repository factory functions for the hgnc-coord-builder CLI.

Provides factory functions that construct concrete repository instances
from application settings. These are called only by the CLI controller
at runtime. Repository modules are allowed to import DB drivers; this
module lives in the repositories package for that reason.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from hgnc_coord_builder.repositories.genew4_ccds_coordinate_repository import (
    Genew4CcdsCoordinateRepository,
)
from hgnc_coord_builder.repositories.genew4_ncbi_coordinate_repository import (
    Genew4NcbiCoordinateRepository,
)
from hgnc_coord_builder.repositories.genew4_pseudogene_coordinate_repository import (
    Genew4PseudogeneCoordinateRepository,
)
from hgnc_coord_builder.repositories.mysql_ensembl_coordinate_repository import (
    MysqlEnsemblCoordinateRepository,
)
from hgnc_coord_builder.repositories.postgres_coord_staging_repository import (
    PostgresCoordStagingRepository,
)
from hgnc_coord_builder.repositories.psycopg_cytoband_coordinate_repository import (
    PsycopgCytobandCoordinateRepository,
)

if TYPE_CHECKING:
    from hgnc_coord_builder.config import Settings


def build_genew4_engine(settings: Settings) -> create_engine:
    """Build a SQLAlchemy engine for genew4 PostgreSQL.

    Args:
        settings: Application configuration with genew4 connection details.

    Returns:
        A configured SQLAlchemy engine with pool resilience.
    """
    genew4 = settings.genew4
    return create_engine(
        genew4.dsn(),
        pool_pre_ping=True,
        pool_recycle=300,
    )


def build_ensembl_repository(settings: Settings) -> MysqlEnsemblCoordinateRepository:
    """Build the Ensembl coordinate repository from settings.

    Args:
        settings: Application configuration with Ensembl connection details.

    Returns:
        A configured MysqlEnsemblCoordinateRepository.
    """
    from ensembl_orm.session import get_session

    return MysqlEnsemblCoordinateRepository(session=get_session())


def build_ncbi_repository(
    settings: Settings, engine: create_engine
) -> Genew4NcbiCoordinateRepository:
    """Build the NCBI coordinate repository from settings.

    Args:
        settings: Application configuration.
        engine: SQLAlchemy engine connected to genew4.

    Returns:
        A configured Genew4NcbiCoordinateRepository.
    """
    session = Session(engine)
    return Genew4NcbiCoordinateRepository(session=session)


def build_ccds_repository(
    settings: Settings, engine: create_engine
) -> Genew4CcdsCoordinateRepository:
    """Build the CCDS coordinate repository from settings.

    Args:
        settings: Application configuration.
        engine: SQLAlchemy engine connected to genew4.

    Returns:
        A configured Genew4CcdsCoordinateRepository.
    """
    session = Session(engine)
    return Genew4CcdsCoordinateRepository(session=session)


def build_cytoband_repository(
    settings: Settings, engine: create_engine
) -> PsycopgCytobandCoordinateRepository:
    """Build the cytoband coordinate repository from settings.

    Uses a raw psycopg connection for queries since the cytoband table
    has no primary key.

    Args:
        settings: Application configuration.
        engine: SQLAlchemy engine connected to genew4.

    Returns:
        A configured PsycopgCytobandCoordinateRepository.
    """
    raw_conn = engine.raw_connection()
    return PsycopgCytobandCoordinateRepository(connection=raw_conn)


def build_pseudogene_repository(
    settings: Settings, engine: create_engine
) -> Genew4PseudogeneCoordinateRepository:
    """Build the pseudogene coordinate repository from settings.

    Args:
        settings: Application configuration.
        engine: SQLAlchemy engine connected to genew4.

    Returns:
        A configured Genew4PseudogeneCoordinateRepository.
    """
    session = Session(engine)
    return Genew4PseudogeneCoordinateRepository(session=session)


def build_staging_repository(
    settings: Settings, engine: create_engine
) -> PostgresCoordStagingRepository:
    """Build the Postgres staging repository from settings.

    Args:
        settings: Application configuration with genew4 connection details.
        engine: SQLAlchemy engine connected to genew4.

    Returns:
        A configured PostgresCoordStagingRepository.
    """
    return PostgresCoordStagingRepository(engine=engine)
