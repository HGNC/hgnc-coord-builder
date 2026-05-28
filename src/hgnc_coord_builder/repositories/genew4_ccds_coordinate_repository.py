"""Genew4 implementation of the CCDS coordinate repository.

Queries the genew4 PostgreSQL database for CCDS gene coordinates using
the Ccds ORM model via SQLAlchemy 2.0 select() API. Filters out rows
with non-numeric start/end positions and deduplicates on the composite
key ``ccds_id + ':_:' + chromosome``.
"""

from __future__ import annotations

import logging
from typing import Any

from genew4_orm.models import Ccds
from sqlalchemy import select

from hgnc_coord_builder.domain.models import CoordinateRecord, CoordSource
from hgnc_coord_builder.exceptions import RepositoryError
from hgnc_coord_builder.repositories.ccds_coordinate_repository import (
    CcdsCoordinateRepository,
)

logger = logging.getLogger(__name__)

_DEDUP_SEPARATOR = ":_:"


class Genew4CcdsCoordinateRepository(CcdsCoordinateRepository):
    """CCDS coordinate repository backed by genew4 PostgreSQL via SQLAlchemy.

    Queries the ``ccds`` table for GRCh38 gene coordinates. Filters out
    rows where start or end is '-' or non-numeric. Deduplicates records
    sharing the same ``ccds_id + ':_:' + chromosome`` key, keeping the
    first occurrence.

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
        """Fetch GRCh38 gene coordinates from CCDS data in genew4.

        Queries the ``ccds`` table, filters out rows where start or
        end is '-' or non-numeric, deduplicates on the composite key
        ``ccds_id + ':_:' + chromosome``, and returns normalised
        CoordinateRecord instances sorted by hgnc_id.

        Returns:
            Sorted list of deduplicated coordinate records.

        Raises:
            RepositoryError: On database connectivity or query failure.
        """
        stmt = select(Ccds).order_by(Ccds.hgnc_id)

        try:
            results = self._session.execute(stmt)
        except Exception as exc:
            msg = f"CCDS coordinate query failed: {exc}"
            raise RepositoryError(msg) from exc

        seen_keys: set[str] = set()
        records: list[CoordinateRecord] = []

        for row in results:
            ccds: Ccds = row[0]
            record = self._build_record(ccds)
            if record is None:
                continue

            dedup_key = f"{ccds.ccds_id}{_DEDUP_SEPARATOR}{record.chromosome}"
            if dedup_key in seen_keys:
                continue
            seen_keys.add(dedup_key)
            records.append(record)

        records.sort(key=lambda r: r.hgnc_id)

        logger.info(
            "ccds_coordinates_fetched",
            extra={"record_count": len(records)},
        )
        return records

    def _build_record(self, ccds: Ccds) -> CoordinateRecord | None:
        """Transform a Ccds ORM row into a CoordinateRecord.

        Returns None when required fields are missing or unparseable.

        Args:
            ccds: Ccds ORM row from the query.

        Returns:
            A CoordinateRecord, or None if the row should be skipped.
        """
        if not ccds.hgnc_id:
            return None

        chromosome = self._clean_chromosome(ccds.chromosome)
        if not chromosome:
            return None

        start = self._parse_int(ccds.start)
        if start is None:
            return None

        end = self._parse_int(ccds.end)
        if end is None:
            return None

        strand = self._normalise_strand(ccds.strand)
        if strand is None:
            return None

        return CoordinateRecord(
            hgnc_id=f"HGNC:{ccds.hgnc_id}",
            chromosome=chromosome,
            start=start,
            end=end,
            strand=strand,
            source=CoordSource.CCDS,
        )

    @staticmethod
    def _clean_chromosome(raw: str | None) -> str | None:
        """Normalise a chromosome name by stripping known prefixes.

        Args:
            raw: Raw chromosome string from the ccds table.

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
    def _parse_int(value: str | None) -> int | None:
        """Parse a string value to int, returning None on failure.

        Args:
            value: String representation of an integer.

        Returns:
            Parsed integer, or None if unparseable.
        """
        if not value or value == "-":
            return None
        try:
            return int(value)
        except (ValueError, TypeError):
            return None

    @staticmethod
    def _normalise_strand(raw: str | None) -> int | None:
        """Map CCDS strand string to integer.

        Args:
            raw: Raw strand string ('+' or '-').

        Returns:
            1 for '+', -1 for '-', or None if missing/unrecognised.
        """
        if raw == "+":
            return 1
        if raw == "-":
            return -1
        return None
