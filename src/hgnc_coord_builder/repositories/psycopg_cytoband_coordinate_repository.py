"""Psycopg implementation of the cytoband coordinate repository.

Queries the genew4 PostgreSQL database for cytoband chromosome coordinates
using raw SQL via psycopg v3. The cytoband table has no primary key, so
raw SQL is used instead of ORM models. Filters by ``cb_source='Ensembl'``
and deduplicates on the composite ``chromosome + band`` key.
"""

from __future__ import annotations

import logging
from typing import Any

from hgnc_coord_builder.domain.models import CoordinateRecord, CoordSource
from hgnc_coord_builder.exceptions import RepositoryError
from hgnc_coord_builder.repositories.cytoband_coordinate_repository import (
    CytobandCoordinateRepository,
)

logger = logging.getLogger(__name__)

_CB_SOURCE_ENSEMBL = "Ensembl"
_SELECT_SQL = (
    "SELECT cb_source, cb_chr, cb_start, cb_end, cb_band "
    "FROM cytoband WHERE cb_source = %s"
)


class PsycopgCytobandCoordinateRepository(CytobandCoordinateRepository):
    """Cytoband coordinate repository backed by psycopg v3 raw SQL.

    Queries the ``cytoband`` table filtered by ``cb_source='Ensembl'``
    using parameterised SQL. Deduplicates on the composite key
    ``chromosome + ':_:' + band``. Cytoband records have no strand
    information, so strand defaults to 1.

    Args:
        connection: psycopg v3 connection to the genew4 database.
    """

    def __init__(self, connection: Any) -> None:
        """Initialise with a psycopg connection for genew4."""
        self._connection = connection

    def health_check(self) -> bool:
        """Return True if the underlying data store is reachable."""
        try:
            with self._connection.cursor() as cur:
                cur.execute("SELECT 1")
            return True
        except Exception:
            return False

    def fetch_gene_coordinates(self) -> list[CoordinateRecord]:
        """Fetch chromosome coordinates from cytoband data in genew4.

        Queries the ``cytoband`` table with ``cb_source='Ensembl'``,
        deduplicates on ``chromosome + ':_:' + band``, and returns
        normalised CoordinateRecord instances. Cytoband records have no
        strand information, so strand defaults to 1.

        Returns:
            List of deduplicated coordinate records from cytoband data.

        Raises:
            RepositoryError: On database connectivity or query failure.
        """
        try:
            with self._connection.cursor() as cur:
                cur.execute(_SELECT_SQL, [_CB_SOURCE_ENSEMBL])
                rows = cur.fetchall()
        except Exception as exc:
            msg = f"Cytoband coordinate query failed: {exc}"
            raise RepositoryError(msg) from exc

        seen_keys: set[str] = set()
        records: list[CoordinateRecord] = []

        for row in rows:
            record = self._build_record(row, seen_keys)
            if record is not None:
                records.append(record)

        logger.info(
            "cytoband_coordinates_fetched",
            extra={"record_count": len(records)},
        )
        return records

    def _build_record(
        self, row: tuple, seen_keys: set[str]
    ) -> CoordinateRecord | None:
        """Transform a cytoband SQL row into a CoordinateRecord.

        Returns None when required fields are missing or when the row
        is a duplicate.

        Args:
            row: Tuple of (cb_source, cb_chr, cb_start, cb_end, cb_band).
            seen_keys: Set of deduplication keys already encountered.

        Returns:
            A CoordinateRecord, or None if the row should be skipped.
        """
        _, chromosome_raw, start, end, band = row

        chromosome = self._clean_chromosome(chromosome_raw)
        if not chromosome:
            return None

        if start is None or end is None:
            return None

        band_str = band or ""
        dedup_key = f"{chromosome}:_:{band_str}"
        if dedup_key in seen_keys:
            return None
        seen_keys.add(dedup_key)

        return CoordinateRecord(
            hgnc_id=f"cytoband:{chromosome}:{band_str}",
            chromosome=chromosome,
            start=int(start),
            end=int(end),
            strand=1,
            source=CoordSource.CYTOBAND,
        )

    @staticmethod
    def _clean_chromosome(raw: str | None) -> str | None:
        """Normalise a chromosome name by stripping known prefixes.

        Args:
            raw: Raw chromosome string from the cytoband table.

        Returns:
            Cleaned chromosome string, or None if input is empty/None.
        """
        if not raw:
            return None
        cleaned = raw.strip()
        if cleaned.lower().startswith("chr"):
            cleaned = cleaned[3:]
        return cleaned or None
