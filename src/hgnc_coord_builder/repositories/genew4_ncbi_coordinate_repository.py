"""Genew4 implementation of the NCBI coordinate repository.

Queries the genew4 PostgreSQL database for NCBI gene coordinates using
Gene2Refseq and GeneInfo ORM models via SQLAlchemy 2.0 select() API.
Joins on (tax_id, eg_id), filters to human GRCh38 assembly, and
normalises strand/chromosome for downstream use.
"""

from __future__ import annotations

import logging
from typing import Any

from genew4_orm.models import Gene2Refseq, GeneInfo
from sqlalchemy import select

from hgnc_coord_builder.domain.models import CoordinateRecord
from hgnc_coord_builder.exceptions import RepositoryError
from hgnc_coord_builder.repositories.ncbi_coordinate_repository import (
    NcbiCoordinateRepository,
)

logger = logging.getLogger(__name__)

_HUMAN_TAX_ID = "9606"
_GRCH38_ASSEMBLY_PATTERN = "%GRCh38%"
_NC_ACCESSION_PREFIX = "NC_%"


class Genew4NcbiCoordinateRepository(NcbiCoordinateRepository):
    """NCBI coordinate repository backed by genew4 PostgreSQL via SQLAlchemy.

    Queries ``gene2refseq`` joined with ``gene_info`` for human GRCh38
    coordinates. Filters to tax_id=9606, assembly containing 'GRCh38',
    and genomic accessions starting with 'NC_'. Strand is normalised
    from '+'/'-' to 1/-1, defaulting to -1 when missing or ambiguous.

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
        """Fetch GRCh38 gene coordinates from NCBI data in genew4.

        Queries ``gene2refseq`` joined with ``gene_info`` on
        (tax_id, eg_id), filtered to human taxonomy, GRCh38 assembly,
        and RefSeq genomic accessions starting with ``NC_``. Returns
        CoordinateRecord instances with cm_* fields matching the
        production staging table DDL.

        Returns:
            List of coordinate records from NCBI gene data.

        Raises:
            RepositoryError: On database connectivity or query failure.
        """
        stmt = (
            select(Gene2Refseq, GeneInfo)
            .join(
                GeneInfo,
                (GeneInfo.gi_tax_id == Gene2Refseq.g2r_tax_id)
                & (GeneInfo.gi_eg_id == Gene2Refseq.g2r_eg_id),
            )
            .where(
                Gene2Refseq.g2r_tax_id == _HUMAN_TAX_ID,
                Gene2Refseq.assembly.like(_GRCH38_ASSEMBLY_PATTERN),
                Gene2Refseq.gen_nt_acc_ver.like(_NC_ACCESSION_PREFIX),
            )
        )

        try:
            results = self._session.execute(stmt)
        except Exception as exc:
            msg = f"NCBI coordinate query failed: {exc}"
            raise RepositoryError(msg) from exc

        records: list[CoordinateRecord] = []
        for row in results:
            g2r: Gene2Refseq = row[0]
            gi: GeneInfo = row[1]

            record = self._build_record(g2r, gi)
            if record is not None:
                records.append(record)

        logger.info(
            "ncbi_coordinates_fetched",
            extra={"record_count": len(records)},
        )
        return records

    def _build_record(
        self, g2r: Gene2Refseq, gi: GeneInfo
    ) -> CoordinateRecord | None:
        """Transform a Gene2Refseq + GeneInfo row into a CoordinateRecord.

        Returns None when required fields are missing or unparseable.
        Maps to cm_* fields matching the Perl NCBIGeneCoords behaviour:
        cm_hgnc_id = eg_id (integer), cm_source = 'NCBI',
        cm_strand defaults to '-' when missing.

        Args:
            g2r: Gene2Refseq ORM row from the join.
            gi: GeneInfo ORM row from the join.

        Returns:
            A CoordinateRecord, or None if the row should be skipped.
        """
        chromosome = self._clean_chromosome(gi.chromosome)
        if not chromosome:
            return None

        start = self._parse_int(g2r.start_pos_gen_acc)
        if start is None:
            return None

        end = self._parse_int(g2r.end_pos_gen_acc)
        if end is None:
            return None

        eg_id = self._parse_int(g2r.g2r_eg_id)
        if eg_id is None:
            return None

        strand = self._normalise_strand(g2r.orientation)

        return CoordinateRecord(
            cm_source="NCBI",
            cm_strand=strand,
            cm_chr=chromosome,
            cm_start=start,
            cm_end=end,
            cm_source_id=g2r.g2r_rna_nt_acc_ver or "",
            cm_eg_id=eg_id,
            cm_hgnc_id=eg_id,
            cm_notes=g2r.gen_nt_acc_ver or "",
            cm_mark=None,
            cm_mapby=str(eg_id),
        )

    @staticmethod
    def _clean_chromosome(raw: str | None) -> str | None:
        """Normalise a chromosome name matching Perl truncation.

        Strips ``chr`` prefix (case-insensitive) and truncates to the
        leading chromosome identifier, matching the Perl regex
        ``s{(^[XYMT\\d]+).*}{$1}``.

        Args:
            raw: Raw chromosome string from gene_info.

        Returns:
            Cleaned chromosome string, or None if input is empty/None.
        """
        if not raw:
            return None
        cleaned = raw.strip()
        if cleaned.lower().startswith("chr"):
            cleaned = cleaned[3:]
        import re as _re

        match = _re.match(r"^([XYMT\d]+)", cleaned)
        if match:
            cleaned = match.group(1)
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
    def _normalise_strand(orientation: str | None) -> str:
        """Map NCBI orientation string to strand character.

        Maps '+' to '+', '-' to '-'. Defaults to '-' for None,
        empty, or unrecognised values, matching Perl behaviour.

        Args:
            orientation: Raw orientation string from gene2refseq.

        Returns:
            '+' for forward strand, '-' for reverse or default.
        """
        if orientation == "+":
            return "+"
        if orientation == "-":
            return "-"
        return "-"
