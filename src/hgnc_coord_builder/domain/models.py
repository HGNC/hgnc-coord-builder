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
    """A GRCh38-compatible coordinate record from a single sub-source.

    Represents a genomic coordinate linked to an HGNC gene. Records are
    normalised on construction: whitespace is trimmed from string fields,
    empty optional strings become None, and strand is validated to be
    1 or -1.

    Records are sortable by (hgnc_id, chromosome) for deterministic
    ordering during bulk loads.

    Attributes:
        hgnc_id: HGNC identifier (e.g. ``HGNC:1100``).
        chromosome: Chromosome name (e.g. ``7``, ``X``, ``MT``).
        start: 1-based start position on the chromosome.
        end: End position on the chromosome (inclusive).
        strand: Strand orientation (1 for forward, -1 for reverse).
        source: Provenance sub-source that produced this record.
        symbol: Optional HGNC gene symbol.
        ensembl_gene_id: Optional Ensembl stable gene ID.
        mapping_type: Optional classification of the coordinate mapping.
    """

    hgnc_id: str = Field(min_length=1, description="HGNC identifier")
    chromosome: str = Field(min_length=1, description="Chromosome name")
    start: int = Field(gt=0, description="1-based start position")
    end: int = Field(gt=0, description="End position")
    strand: int = Field(description="Strand: 1 (forward) or -1 (reverse)")
    source: CoordSource = Field(description="Provenance sub-source")
    symbol: str | None = Field(default=None, description="HGNC gene symbol")
    ensembl_gene_id: str | None = Field(default=None, description="Ensembl stable gene ID")
    mapping_type: str | None = Field(default=None, description="Coordinate mapping type")

    @field_validator("hgnc_id", "chromosome", mode="before")
    @classmethod
    def trim_required_strings(cls, v: str) -> str:
        return v.strip()

    @field_validator("symbol", "ensembl_gene_id", "mapping_type", mode="before")
    @classmethod
    def trim_optional_fields(cls, v: str | None) -> str | None:
        if v is None:
            return None
        return v.strip() or None

    @field_validator("strand")
    @classmethod
    def validate_strand(cls, v: int) -> int:
        if v not in (1, -1):
            msg = f"Strand must be 1 or -1, got {v}"
            raise ValueError(msg)
        return v

    def __lt__(self, other: CoordinateRecord) -> bool:
        return (self.hgnc_id, self.chromosome) < (other.hgnc_id, other.chromosome)

    def __le__(self, other: CoordinateRecord) -> bool:
        return (self.hgnc_id, self.chromosome) <= (other.hgnc_id, other.chromosome)

    def __gt__(self, other: CoordinateRecord) -> bool:
        return (self.hgnc_id, self.chromosome) > (other.hgnc_id, other.chromosome)

    def __ge__(self, other: CoordinateRecord) -> bool:
        return (self.hgnc_id, self.chromosome) >= (other.hgnc_id, other.chromosome)

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, CoordinateRecord):
            return NotImplemented
        return (
            self.hgnc_id == other.hgnc_id
            and self.chromosome == other.chromosome
            and self.start == other.start
            and self.end == other.end
            and self.strand == other.strand
            and self.source == other.source
        )

    def to_dict(self) -> dict[str, str | int | None]:
        """Convert to a flat dictionary suitable for COPY bulk load.

        Returns:
            Dictionary with all fields as plain Python types.
        """
        return {
            "hgnc_id": self.hgnc_id,
            "chromosome": self.chromosome,
            "start": self.start,
            "end": self.end,
            "strand": self.strand,
            "source": self.source.value,
            "symbol": self.symbol,
            "ensembl_gene_id": self.ensembl_gene_id,
            "mapping_type": self.mapping_type,
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
