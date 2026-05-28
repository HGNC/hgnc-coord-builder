"""Postgres engine and session factory for the HGNC coordinate builder.

Creates SQLAlchemy 2.0-style engines and session factories configured for
Cloud Run Job resilience: pool_pre_ping, pool_recycle, and expire_on_commit.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

if TYPE_CHECKING:
    from hgnc_coord_builder.config import Genew4Settings

POOL_PRE_PING = True
POOL_RECYCLE_SECONDS = 3600
POOL_SIZE = 5
MAX_OVERFLOW = 10


def create_genew4_engine(settings: Genew4Settings):
    """Create a SQLAlchemy engine for the genew4 PostgreSQL database.

    Configures connection pooling for Cloud Run Job resilience with
    pool_pre_ping to detect stale connections and pool_recycle to refresh
    connections before Cloud Run maintenance events.

    Args:
        settings: Genew4 database connection settings.

    Returns:
        A SQLAlchemy Engine instance configured for psycopg v3.
    """
    dsn = settings.dsn()
    return create_engine(
        dsn,
        pool_pre_ping=POOL_PRE_PING,
        pool_recycle=POOL_RECYCLE_SECONDS,
        pool_size=POOL_SIZE,
        max_overflow=MAX_OVERFLOW,
    )


def create_session_factory(engine):
    """Create a session factory bound to the given engine.

    Configures sessions with expire_on_commit=False to prevent
    lazy-loading after commit, which is appropriate for batch jobs
    that do not need to re-read committed objects.

    Args:
        engine: A SQLAlchemy Engine instance.

    Returns:
        A callable session factory that produces Session instances.
    """
    return sessionmaker(bind=engine, expire_on_commit=False)
