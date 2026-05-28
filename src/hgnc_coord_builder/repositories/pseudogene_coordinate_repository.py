"""Abstract interface for reading pseudogene coordinates from genew4.

Defines the contract for pseudogene coordinate extraction used by the
coord-builder service. Implementations query the ``pseudogene_org`` table
and deduplicate on ``cm_source_id``.
"""

from __future__ import annotations

from abc import abstractmethod
from typing import TYPE_CHECKING

from hgnc_coord_builder.repositories.base_repository import Repository

if TYPE_CHECKING:
    from hgnc_coord_builder.domain.models import CoordinateRecord


class PseudogeneCoordinateRepository(Repository):
    """Abstract base class for pseudogene coordinate extraction.

    Implementations query the genew4 PostgreSQL database for pseudogene
    coordinates using the PseudogeneOrg ORM model and deduplicate
    records sharing the same ``cm_source_id``.

    All query logic is confined to the repository layer. The service
    layer depends on this abstraction and never constructs SQL.
    """

    @abstractmethod
    def fetch_gene_coordinates(self) -> list[CoordinateRecord]:
        """Fetch pseudogene coordinates from genew4.

        Queries the ``pseudogene_org`` table, deduplicates on
        ``cm_source_id`` (porg_id), and returns normalised
        CoordinateRecord instances sorted by hgnc_id.

        Returns:
            List of deduplicated coordinate records from pseudogene data.

        Raises:
            RepositoryError: On database connectivity or query failure.
        """
