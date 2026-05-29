"""MySQL implementation of the Ensembl coordinate repository.

Queries the Ensembl database for HGNC-mapped gene coordinates using
ensembl-orm models (Gene, SeqRegion, ObjectXref, Xref, ExternalDb)
via SQLAlchemy 2.0 select() API. All query logic is confined to this
repository layer; the service never constructs SQL.
"""

from __future__ import annotations

import logging
from typing import Any

from ensembl_orm.models import Gene
from sqlalchemy import select

from hgnc_coord_builder.domain.models import CoordinateRecord
from hgnc_coord_builder.exceptions import RepositoryError
from hgnc_coord_builder.repositories.ensembl_coordinate_repository import (
    EnsemblCoordinateRepository,
)

logger = logging.getLogger(__name__)


class MysqlEnsemblCoordinateRepository(EnsemblCoordinateRepository):
    """Ensembl coordinate repository backed by mysqlclient via ensembl-orm.

    Queries the Ensembl MySQL ``gene`` table joined with ``seq_region``
    for chromosome names, filtered to HGNC-mapped genes via
    ``object_xref``, ``xref``, and ``external_db`` tables.

    Args:
        session: SQLModel Session connected to the Ensembl database.
    """

    def __init__(self, session: Any) -> None:
        """Initialise with a SQLAlchemy session for Ensembl MySQL."""
        self._session = session

    def health_check(self) -> bool:
        """Return True if the underlying data store is reachable."""
        try:
            from sqlalchemy import text

            self._session.execute(text("SELECT 1"))
            return True
        except Exception:
            return False

    def fetch_gene_coordinates(self) -> list[CoordinateRecord]:
        """Fetch GRCh38 gene coordinates from Ensembl for all genes.

        Queries the Ensembl ``gene`` table joined with ``seq_region``
        for chromosome names. All current genes (``is_current=True``)
        are included. Maps to cm_* fields matching the Perl
        EnsemblGeneCoords behaviour: no HGNC join, strand converted
        to +/- strings, notes with source/desc/biotype format.

        Returns:
            List of coordinate records from Ensembl gene data.

        Raises:
            RepositoryError: On database connectivity or query failure.
        """
        stmt = (
            select(Gene)
            .where(Gene.is_current.is_(True))
            .order_by(Gene.stable_id)
        )

        try:
            results = self._session.execute(stmt)
        except Exception as exc:
            msg = f"Ensembl coordinate query failed: {exc}"
            raise RepositoryError(msg) from exc

        records: list[CoordinateRecord] = []
        for row in results:
            gene: Gene = row[0]

            if not gene.seq_region or not gene.stable_id:
                logger.warning(
                    "skipping_gene_missing_data",
                    extra={"gene_id": gene.gene_id, "stable_id": gene.stable_id},
                )
                continue

            if gene.seq_region_strand not in (1, -1):
                logger.warning(
                    "skipping_gene_invalid_strand",
                    extra={
                        "gene_id": gene.gene_id,
                        "strand": gene.seq_region_strand,
                    },
                )
                continue

            strand = "+" if gene.seq_region_strand == 1 else "-"
            description = gene.description or "-"
            notes = (
                f"source => {gene.source}, status => NULL, "
                f"desc =>{description}, biotype => {gene.biotype}"
            )

            records.append(
                CoordinateRecord(
                    cm_source="Ensembl",
                    cm_strand=strand,
                    cm_chr=gene.seq_region.name,
                    cm_start=gene.seq_region_start,
                    cm_end=gene.seq_region_end,
                    cm_source_id=gene.stable_id,
                    cm_eg_id=None,
                    cm_hgnc_id=None,
                    cm_notes=notes,
                    cm_mark=None,
                    cm_mapby=gene.stable_id,
                )
            )

        logger.info(
            "ensembl_coordinates_fetched",
            extra={"record_count": len(records)},
        )
        return records
