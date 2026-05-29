"""Abstract interface and domain exceptions for coordinate staging promotion.

Defines the staging-table lifecycle contract for ``coord_match_grch38``:
prepare staging table, bulk COPY load, create indexes, validate row counts,
and atomically promote staging to production. All DDL is confined to
concrete implementations of this interface.
"""

from __future__ import annotations

from abc import abstractmethod

from hgnc_coord_builder.exceptions import RepositoryError
from hgnc_coord_builder.repositories.base_repository import Repository


class CoordPromotionError(RepositoryError):
    """Raised when a staging-to-production promotion fails.

    Carries the staging table name for diagnostic context.
    """

    def __init__(self, staging_table: str, message: str = "") -> None:
        self.staging_table = staging_table
        detail = message or f"Promotion failed for staging={staging_table}"
        super().__init__(detail)


class CoordRowCountMismatchError(CoordPromotionError):
    """Raised when staging row count does not match expected count.

    Carries expected and actual row counts alongside staging table context.
    """

    def __init__(self, staging_table: str, expected: int, actual: int) -> None:
        self.expected_count = expected
        self.actual_count = actual
        msg = (
            f"Row count mismatch for {staging_table}: "
            f"expected {expected}, got {actual}"
        )
        super().__init__(staging_table=staging_table, message=msg)


class CoordStagingRepository(Repository):
    """Abstract base class for coord_match_grch38 staging-table lifecycle.

    Defines the contract for preparing staging tables, performing bulk COPY
    loads, creating indexes, validating row counts, and atomically promoting
    staging to production. The staging table naming convention is
    ``coord_match_grch38_update``. Promotion swaps this into the production
    ``coord_match_grch38`` name via ALTER TABLE ... RENAME, updating
    ``table_mod_dates`` atomically.

    Services depend on this abstraction; they never execute SQL or DDL.
    """

    @abstractmethod
    def prepare_staging_table(self) -> str:
        """Drop and recreate the staging table.

        Creates a clean ``coord_match_grch38_update`` staging table,
        destroying any prior staging data. This ensures deterministic
        re-run behavior: every load starts from a known empty state.

        Returns:
            The staging table name (``coord_match_grch38_update``).
        """

    @abstractmethod
    def bulk_copy_coordinates(self, staging_table: str, records: list[dict]) -> int:
        """Bulk-load coordinate records into staging using psycopg v3 COPY.

        Uses COPY for maximum throughput. Accepts an empty record list
        without error (zero-row loads are valid).

        Args:
            staging_table: Name of the staging table to load into.
            records: List of dictionaries representing rows to insert.

        Returns:
            The number of rows loaded (0 for empty input).
        """

    @abstractmethod
    def create_staging_indexes(self, staging_table: str) -> None:
        """Create indexes on the staging table matching production schema.

        Args:
            staging_table: Name of the staging table.
        """

    @abstractmethod
    def validate_row_count(self, staging_table: str, expected: int) -> None:
        """Assert staging table row count matches expected count.

        Raises ``CoordRowCountMismatchError`` if the counts differ.

        Args:
            staging_table: Name of the staging table to validate.
            expected: Expected number of rows in the staging table.

        Raises:
            CoordRowCountMismatchError: If actual count differs from expected.
        """

    @abstractmethod
    def set_default_cm_mark(self) -> None:
        """Apply post-load cm_mark annotations on coord_match_grch38.

        Sets ``cm_mark='hidden'`` for all CCDS rows. For all other sources,
        sets ``cm_mark='max'`` on the row with the highest OID per unique
        coordinate tuple (source, start, end, strand, chr). All other
        non-CCDS rows remain with ``cm_mark=NULL``.
        """

    @abstractmethod
    def set_default_cm_note(self) -> None:
        """Apply post-load cm_note warnings on coord_match_grch38.

        Clears all existing ``cm_notes``. Then sets a warning note on
        rows where the same ``cm_mapby`` value has conflicting start
        or end positions (within the same chromosome).
        """

    @abstractmethod
    def promote_staging_to_production(self, staging_table: str) -> None:
        """Atomically promote the staging table to production.

        Renames ``coord_match_grch38_update`` to ``coord_match_grch38``
        and updates ``table_mod_dates`` within the same transaction. On
        failure, the transaction rolls back and the previous production
        table is preserved.

        Args:
            staging_table: Name of the staging table to promote.

        Raises:
            CoordPromotionError: If the promotion DDL fails.
        """
