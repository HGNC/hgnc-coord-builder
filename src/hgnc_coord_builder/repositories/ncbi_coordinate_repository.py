"""Abstract interface for reading NCBI gene coordinates from genew4.

Defines the contract for NCBI-side coordinate extraction used by the
coord-builder service. Implementations query the ``gene2refseq`` and
``gene_info`` tables for GRCh38 gene coordinates linked to HGNC
identifiers via the hgnc_id field.
"""

from __future__ import annotations

from abc import abstractmethod
from typing import TYPE_CHECKING

from hgnc_coord_builder.repositories.base_repository import Repository

if TYPE_CHECKING:
    from hgnc_coord_builder.domain.models import CoordinateRecord


class NcbiCoordinateRepository(Repository):
    """Abstract base class for NCBI gene coordinate extraction.

    Implementations query the genew4 PostgreSQL database for NCBI
    gene coordinates using the Gene2Refseq and GeneInfo ORM models
    and return normalised CoordinateRecord instances.

    All query logic is confined to the repository layer. The service
    layer depends on this abstraction and never constructs SQL.
    """

    @abstractmethod
    def fetch_gene_coordinates(self) -> list[CoordinateRecord]:
        """Fetch GRCh38 gene coordinates from NCBI data in genew4.

        Queries ``gene2refseq`` joined with ``gene_info``, filtered to
        human taxonomy (tax_id=9606), GRCh38 assembly, and RefSeq
        genomic accessions starting with ``NC_``. Results are returned
        as normalised CoordinateRecord instances sorted by hgnc_id.

        Returns:
            List of coordinate records from NCBI gene data.

        Raises:
            RepositoryError: On database connectivity or query failure.
        """
