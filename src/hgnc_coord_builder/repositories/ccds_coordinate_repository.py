"""Abstract interface for reading CCDS gene coordinates from genew4.

Defines the contract for CCDS-side coordinate extraction used by the
coord-builder service. Implementations query the ``ccds`` table for
GRCh38 gene coordinates filtered to rows with valid numeric start/end
positions, and deduplicated on ``ccds_id + chromosome``.
"""

from __future__ import annotations

from abc import abstractmethod
from typing import TYPE_CHECKING

from hgnc_coord_builder.repositories.base_repository import Repository

if TYPE_CHECKING:
    from hgnc_coord_builder.domain.models import CoordinateRecord


class CcdsCoordinateRepository(Repository):
    """Abstract base class for CCDS gene coordinate extraction.

    Implementations query the genew4 PostgreSQL database for CCDS
    gene coordinates using the Ccds ORM model, filter out rows with
    non-numeric start/end positions, and deduplicate records sharing
    the same ``ccds_id + chromosome`` key.

    All query logic is confined to the repository layer. The service
    layer depends on this abstraction and never constructs SQL.
    """

    @abstractmethod
    def fetch_gene_coordinates(self) -> list[CoordinateRecord]:
        """Fetch GRCh38 gene coordinates from CCDS data in genew4.

        Queries the ``ccds`` table, filters out rows where start or
        end is '-' or otherwise non-numeric, deduplicates on the
        composite key ``ccds_id + ':_:' + chromosome``, and returns
        normalised CoordinateRecord instances sorted by hgnc_id.

        Returns:
            List of deduplicated coordinate records from CCDS data.

        Raises:
            RepositoryError: On database connectivity or query failure.
        """
