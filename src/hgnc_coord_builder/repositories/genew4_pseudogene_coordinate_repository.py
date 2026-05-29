"""Genew4 implementation of the pseudogene coordinate repository.

Queries the genew4 PostgreSQL database for pseudogene coordinates using
the PseudogeneOrg ORM model via SQLAlchemy 2.0 select() API. Deduplicates
records on ``porg_id``.
"""

from __future__ import annotations

import logging
from typing import Any

from genew4_orm.models import PseudogeneOrg
from sqlalchemy import select

from hgnc_coord_builder.domain.models import CoordinateRecord
from hgnc_coord_builder.exceptions import RepositoryError
from hgnc_coord_builder.repositories.pseudogene_coordinate_repository import (
    PseudogeneCoordinateRepository,
)

logger = logging.getLogger(__name__)


class Genew4PseudogeneCoordinateRepository(PseudogeneCoordinateRepository):
    """Pseudogene coordinate repository backed by genew4 PostgreSQL.

    Queries the ``pseudogene_org`` table for pseudogene coordinates,
    deduplicates on ``porg_id``, and returns normalised CoordinateRecord
    instances.

    Args:
        session: SQLModel Session connected to the genew4 database.
    """

    def __init__(self, session: Any) -> None:
        """Initialise with a SQLAlchemy session for genew4."""
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
        """Fetch pseudogene coordinates from genew4.

        Queries the ``pseudogene_org`` table, deduplicates on
        ``porg_id``, and returns normalised CoordinateRecord instances.

        Returns:
            List of deduplicated coordinate records.

        Raises:
            RepositoryError: On database connectivity or query failure.
        """
        stmt = select(PseudogeneOrg).order_by(PseudogeneOrg.porg_id)

        try:
            results = self._session.execute(stmt)
        except Exception as exc:
            msg = f"Pseudogene coordinate query failed: {exc}"
            raise RepositoryError(msg) from exc

        seen_ids: set[int] = set()
        records: list[CoordinateRecord] = []

        for row in results:
            porg: PseudogeneOrg = row[0]

            if porg.porg_id is None or porg.porg_id in seen_ids:
                continue
            seen_ids.add(porg.porg_id)

            record = self._build_record(porg)
            if record is not None:
                records.append(record)

        logger.info(
            "pseudogene_coordinates_fetched",
            extra={"record_count": len(records)},
        )
        return records

    def _build_record(self, porg: PseudogeneOrg) -> CoordinateRecord | None:
        """Transform a PseudogeneOrg ORM row into a CoordinateRecord.

        Maps to cm_* fields matching the Perl PseudogeneCoords behaviour:
        cm_source='Pseudogene.org', cm_notes=class||', '||link,
        strand defaults to '-' if missing.

        Args:
            porg: PseudogeneOrg ORM row from the query.

        Returns:
            A CoordinateRecord, or None if the row should be skipped.
        """
        chromosome = self._clean_chromosome(porg.chromosome)
        if not chromosome:
            return None

        if porg.start is None or porg.end is None:
            return None

        strand = self._normalise_strand(porg.strand)
        if strand is None:
            strand = "-"

        porg_class = porg.porg_class or ""
        porg_link = porg.porg_link or ""
        notes = f"{porg_class}, {porg_link}"

        return CoordinateRecord(
            cm_source="Pseudogene.org",
            cm_strand=strand,
            cm_chr=chromosome,
            cm_start=int(porg.start),
            cm_end=int(porg.end),
            cm_source_id=str(porg.porg_id),
            cm_eg_id=None,
            cm_hgnc_id=None,
            cm_notes=notes,
            cm_mark=None,
            cm_mapby=str(porg.porg_id),
        )

    @staticmethod
    def _clean_chromosome(raw: str | None) -> str | None:
        """Normalise a chromosome name by stripping known prefixes.

        Args:
            raw: Raw chromosome string from the pseudogene_org table.

        Returns:
            Cleaned chromosome string, or None if input is empty/None.
        """
        if not raw:
            return None
        cleaned = raw.strip()
        if cleaned.lower().startswith("chr"):
            cleaned = cleaned[3:]
        return cleaned or None

    @staticmethod
    def _normalise_strand(raw: str | None) -> str | None:
        """Map strand string to string.

        Args:
            raw: Raw strand string ('+' or '-').

        Returns:
            '+' or '-', or None if missing/unrecognised.
        """
        if raw == "+":
            return "+"
        if raw == "-":
            return "-"
        return None
