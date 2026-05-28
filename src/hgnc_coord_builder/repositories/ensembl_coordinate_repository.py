"""Abstract interface for reading gene coordinates from Ensembl MySQL.

Defines the contract for Ensembl-side coordinate extraction used by the
coord-builder service. Implementations use ensembl-orm/mysqlclient to
query the ``gene`` and ``seq_region`` tables for GRCh38 gene coordinates
linked to HGNC identifiers via the xref/object_xref tables.
"""

from __future__ import annotations

from abc import abstractmethod

from hgnc_coord_builder.domain.models import CoordinateRecord
from hgnc_coord_builder.repositories.base_repository import Repository


class EnsemblCoordinateRepository(Repository):
    """Abstract base class for Ensembl gene coordinate extraction.

    Implementations query the Ensembl MySQL database for gene coordinates
    using ensembl-orm models (Gene, SeqRegion, Xref, ObjectXref) and
    return normalised CoordinateRecord instances.

    All query logic is confined to the repository layer. The service
    layer depends on this abstraction and never constructs SQL.
    """

    @abstractmethod
    def fetch_gene_coordinates(self) -> list[CoordinateRecord]:
        """Fetch GRCh38 gene coordinates from Ensembl.

        Queries the Ensembl ``gene`` table joined with ``seq_region``
        for chromosome names, filtered to HGNC-mapped genes via
        ``object_xref`` and ``xref``. Results are returned as
        normalised CoordinateRecord instances sorted by hgnc_id.

        Returns:
            List of coordinate records from Ensembl gene data.

        Raises:
            RepositoryError: On database connectivity or query failure.
        """
