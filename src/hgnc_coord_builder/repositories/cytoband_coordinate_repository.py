"""Abstract interface for reading cytoband chromosome coordinates from genew4.

Defines the contract for cytoband/UCSC chromosome coordinate extraction
used by the coord-builder service. Implementations use raw SQL via psycopg
to query the ``cytoband`` table filtered by ``cb_source='Ensembl'`` and
deduplicated on ``cm_source_id``.
"""

from __future__ import annotations

from abc import abstractmethod
from typing import TYPE_CHECKING

from hgnc_coord_builder.repositories.base_repository import Repository

if TYPE_CHECKING:
    from hgnc_coord_builder.domain.models import CoordinateRecord


class CytobandCoordinateRepository(Repository):
    """Abstract base class for cytoband chromosome coordinate extraction.

    Implementations query the genew4 PostgreSQL database for cytoband
    chromosome coordinates using raw SQL via psycopg, filtered to
    ``cb_source='Ensembl'``, and deduplicated on the composite
    ``cm_source_id`` key.

    The cytoband table has no primary key, so raw SQL is used instead
    of ORM models.
    """

    @abstractmethod
    def fetch_gene_coordinates(self) -> list[CoordinateRecord]:
        """Fetch chromosome coordinates from cytoband data in genew4.

        Queries the ``cytoband`` table with ``cb_source='Ensembl'``,
        deduplicates on ``cm_source_id`` (chromosome + band), and
        returns normalised CoordinateRecord instances. Cytoband records
        use strand value 1 as a default (cytogenetic bands have no
        strand).

        Returns:
            List of deduplicated coordinate records from cytoband data.

        Raises:
            RepositoryError: On database connectivity or query failure.
        """
