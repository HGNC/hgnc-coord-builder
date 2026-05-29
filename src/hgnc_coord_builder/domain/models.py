"""Coordinate domain models for the HGNC coordinate builder.

Defines the canonical GRCh38 coordinate record schema, source provenance
enum, and metrics container for structured logging and observability.
"""

from __future__ import annotations

import enum

from pydantic import BaseModel, Field, field_validator


class CoordSource(str, enum.Enum):
    """Provenance source for coordinate records.

    Each member corresponds to one of the five sub-sources that feed into
    ``coord_match_grch38``.
    """

    NCBI = "ncbi"
    ENSEMBL = "ensembl"
    CCDS = "ccds"
    CYTOBAND = "cytoband"
    PSEUDOGENE = "pseudogene"


class CoordinateRecord(BaseModel):
    """A GRCh38-compatible coordinate record matching the cm_* DDL schema.

    Field names and types align exactly with the ``coord_match_grch38``
    staging table DDL. Records are sortable by (cm_hgnc_id, cm_chr) for
    deterministic ordering during bulk loads.

    Attributes:
        cm_source: Provenance sub-source name (``NCBI``, ``Ensembl``,
            ``CCDS``, ``Chrom``, ``Pseudogene.org``).
        cm_strand: Strand character (``+``, ``-``, or `` `` for cytoband).
        cm_chr: Chromosome name (e.g. ``7``, ``X``, ``MT``).
        cm_start: 1-based start position on the chromosome.
        cm_end: End position on the chromosome (inclusive).
        cm_source_id: Source-specific identifier for the record.
        cm_eg_id: Entrez Gene ID (integer), or None.
        cm_hgnc_id: Entrez Gene ID used as HGNC link (integer), or None.
        cm_notes: Free-text notes from the source.
        cm_mark: Annotation mark (``max``, ``hidden``, or None).
        cm_mapby: Mapping classification key.
    """

    cm_source: str = Field(min_length=1, description="Provenance sub-source name")
    cm_strand: str = Field(description="Strand character (+, -, or space)")
    cm_chr: str = Field(min_length=1, description="Chromosome name")
    cm_start: int = Field(gt=0, description="1-based start position")
    cm_end: int = Field(gt=0, description="End position")
    cm_source_id: str = Field(min_length=1, description="Source-specific identifier")
    cm_eg_id: int | None = Field(default=None, description="Entrez Gene ID")
    cm_hgnc_id: int | None = Field(default=None, description="HGNC link ID (Entrez Gene ID)")
    cm_notes: str | None = Field(default=None, description="Free-text notes")
    cm_mark: str | None = Field(default=None, description="Annotation mark")
    cm_mapby: str = Field(min_length=1, description="Mapping classification key")

    @field_validator("cm_chr", "cm_source_id", "cm_mapby", mode="before")
    @classmethod
    def trim_required_strings(cls, v: str) -> str:
        return v.strip()

    def __lt__(self, other: CoordinateRecord) -> bool:
        return (self.cm_hgnc_id or 0, self.cm_chr) < (
            other.cm_hgnc_id or 0,
            other.cm_chr,
        )

    def __le__(self, other: CoordinateRecord) -> bool:
        return (self.cm_hgnc_id or 0, self.cm_chr) <= (
            other.cm_hgnc_id or 0,
            other.cm_chr,
        )

    def __gt__(self, other: CoordinateRecord) -> bool:
        return (self.cm_hgnc_id or 0, self.cm_chr) > (
            other.cm_hgnc_id or 0,
            other.cm_chr,
        )

    def __ge__(self, other: CoordinateRecord) -> bool:
        return (self.cm_hgnc_id or 0, self.cm_chr) >= (
            other.cm_hgnc_id or 0,
            other.cm_chr,
        )

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, CoordinateRecord):
            return NotImplemented
        return (
            self.cm_source == other.cm_source
            and self.cm_strand == other.cm_strand
            and self.cm_chr == other.cm_chr
            and self.cm_start == other.cm_start
            and self.cm_end == other.cm_end
            and self.cm_source_id == other.cm_source_id
        )

    def to_dict(self) -> dict[str, str | int]:
        """Convert to a flat dictionary suitable for COPY bulk load.

        Maps None values to empty strings for CSV compatibility with
        the staging table DDL. Returns exactly the 11 cm_* columns.

        Returns:
            Dictionary with all cm_* fields as plain Python types.
        """
        return {
            "cm_source": self.cm_source,
            "cm_strand": self.cm_strand,
            "cm_chr": self.cm_chr,
            "cm_start": self.cm_start,
            "cm_end": self.cm_end,
            "cm_source_id": self.cm_source_id,
            "cm_eg_id": self.cm_eg_id if self.cm_eg_id is not None else "",
            "cm_hgnc_id": self.cm_hgnc_id if self.cm_hgnc_id is not None else "",
            "cm_notes": self.cm_notes if self.cm_notes is not None else "",
            "cm_mark": self.cm_mark if self.cm_mark is not None else "",
            "cm_mapby": self.cm_mapby,
        }


class CoordMetrics(BaseModel):
    """Counters for coordinate builder run metrics.

    Tracks total fetched, merged, and skipped counts across all
    sub-sources for structured JSON logging and observability.

    Attributes:
        total_fetched: Total raw records fetched from all sources.
        total_merged: Total records after merging and deduplication.
        skipped: Records skipped due to errors or missing data.
        by_source: Per-source record counts keyed by source name.
    """

    total_fetched: int = Field(default=0, description="Total raw records fetched")
    total_merged: int = Field(default=0, description="Records after merge/dedup")
    skipped: int = Field(default=0, description="Skipped records")
    by_source: dict[str, int] = Field(default_factory=dict, description="Per-source counts")

    def increment(self, source: CoordSource) -> None:
        """Increment the counter for a given source.

        Args:
            source: The sub-source to increment.
        """
        key = source.value
        self.by_source[key] = self.by_source.get(key, 0) + 1

    def snapshot(self) -> dict[str, int | dict[str, int]]:
        """Return a snapshot of current metrics for logging.

        Returns:
            Dictionary of metric name to value.
        """
        return {
            "total_fetched": self.total_fetched,
            "total_merged": self.total_merged,
            "skipped": self.skipped,
            "by_source": dict(self.by_source),
        }
