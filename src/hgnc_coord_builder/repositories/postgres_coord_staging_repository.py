"""Postgres implementation of the coord staging repository.

Provides concrete staging-table lifecycle operations for ``coord_match_grch38``
using psycopg v3 COPY for bulk loads, psycopg.sql.Identifier for safe dynamic
identifier composition, and atomic ALTER TABLE ... RENAME for staging-to-
production promotion.

DDL is strictly scoped to the loader exception: DROP/CREATE on the
``coord_match_grch38_update`` staging table and ALTER TABLE ... RENAME
for promotion. All values are parameterized; all identifiers use
psycopg.sql composition.
"""

from __future__ import annotations

import csv
import io
import logging
from typing import Any

from psycopg import sql

from hgnc_coord_builder.repositories.coord_staging_repository import (
    CoordPromotionError,
    CoordRowCountMismatchError,
    CoordStagingRepository,
)

logger = logging.getLogger(__name__)

PRODUCTION_TABLE = "coord_match_grch38"
STAGING_TABLE = "coord_match_grch38_update"


class PostgresCoordStagingRepository(CoordStagingRepository):
    """Postgres-backed coordinate staging repository using psycopg v3.

    Uses COPY for bulk loads, psycopg.sql for safe identifier composition,
    and transactional DDL for atomic staging-to-production promotion.

    Args:
        engine: SQLAlchemy engine configured with psycopg v3 driver.
            Must have pool_pre_ping and pool_recycle configured for
            Cloud Run resilience.
    """

    def __init__(self, engine: Any) -> None:
        self._engine = engine

    def health_check(self) -> bool:
        try:
            with self._engine.connect() as conn:
                conn.execute(sql.SQL("SELECT 1"))
            return True
        except Exception:
            return False

    def prepare_staging_table(self) -> str:
        staging_id = sql.Identifier(STAGING_TABLE)
        prod_id = sql.Identifier(PRODUCTION_TABLE)

        drop_stmt = sql.SQL("DROP TABLE IF EXISTS {table}").format(table=staging_id)
        create_stmt = sql.SQL(
            "CREATE TABLE {table} (LIKE {source} INCLUDING DEFAULTS)"
        ).format(table=staging_id, source=prod_id)

        with self._engine.raw_connection() as raw_conn:
            with raw_conn.cursor() as cur:
                cur.execute(drop_stmt)
                cur.execute(create_stmt)

        logger.info(
            "coord_staging_prepared",
            extra={"staging_table": STAGING_TABLE},
        )
        return STAGING_TABLE

    def bulk_copy_coordinates(self, staging_table: str, records: list[dict]) -> int:
        if not records:
            logger.info(
                "coord_bulk_copy_empty",
                extra={"staging_table": staging_table, "row_count": 0},
            )
            return 0

        columns = list(records[0].keys())
        col_ids = [sql.Identifier(c) for c in columns]
        copy_sql = sql.SQL("COPY {table} ({cols}) FROM STDIN WITH CSV HEADER").format(
            table=sql.Identifier(staging_table),
            cols=sql.SQL(", ").join(col_ids),
        )

        buf = io.StringIO()
        writer = csv.DictWriter(buf, fieldnames=columns)
        writer.writeheader()
        for record in records:
            writer.writerow(record)
        buf.seek(0)

        with self._engine.raw_connection() as raw_conn:
            with raw_conn.cursor() as cur:
                with cur.copy(copy_sql) as copy:
                    copy.write(buf.read())

        count = len(records)
        logger.info(
            "coord_bulk_copy_complete",
            extra={"staging_table": staging_table, "row_count": count},
        )
        return count

    def create_staging_indexes(self, staging_table: str) -> None:
        staging_id = sql.Identifier(staging_table)
        idx_hgnc = sql.Identifier(f"idx_{staging_table}_cm_hgnc_id")
        idx_chr = sql.Identifier(f"idx_{staging_table}_cm_chr")

        create_hgnc_idx = sql.SQL(
            "CREATE INDEX IF NOT EXISTS {idx} ON {table} (cm_hgnc_id)"
        ).format(idx=idx_hgnc, table=staging_id)

        create_chr_idx = sql.SQL(
            "CREATE INDEX IF NOT EXISTS {idx} ON {table} (cm_chr)"
        ).format(idx=idx_chr, table=staging_id)

        with self._engine.raw_connection() as raw_conn:
            with raw_conn.cursor() as cur:
                cur.execute(create_hgnc_idx)
                cur.execute(create_chr_idx)

        logger.info(
            "coord_staging_indexes_created",
            extra={"staging_table": staging_table},
        )

    def validate_row_count(self, staging_table: str, expected: int) -> None:
        count_stmt = sql.SQL("SELECT COUNT(*) FROM {table}").format(
            table=sql.Identifier(staging_table),
        )

        with self._engine.raw_connection() as raw_conn:
            with raw_conn.cursor() as cur:
                cur.execute(count_stmt)
                row = cur.fetchone()

        actual = row[0] if row else 0
        if actual != expected:
            raise CoordRowCountMismatchError(
                staging_table=staging_table,
                expected=expected,
                actual=actual,
            )

        logger.info(
            "coord_row_count_validated",
            extra={"staging_table": staging_table, "expected": expected, "actual": actual},
        )

    def set_default_cm_mark(self) -> None:
        max_non_ncbi_ccds = sql.SQL("""
            UPDATE {table}
            SET cm_mark = 'max'
            WHERE cm_source != 'NCBI'
              AND cm_source != 'CCDS'
              AND oid IN (
                SELECT MAX(oid)
                FROM {table}
                GROUP BY cm_source||' '||cm_start||' '||cm_end||' '||cm_strand||' '||cm_chr
              )
        """).format(table=sql.Identifier(PRODUCTION_TABLE))

        max_ncbi = sql.SQL("""
            UPDATE {table}
            SET cm_mark = 'max'
            WHERE cm_source = 'NCBI'
              AND oid IN (
                SELECT MAX(oid)
                FROM {table}
                GROUP BY cm_source||' '||cm_start||' '||cm_end||' '||cm_strand||' '||cm_chr
              )
        """).format(table=sql.Identifier(PRODUCTION_TABLE))

        hidden_ccds = sql.SQL("""
            UPDATE {table}
            SET cm_mark = 'hidden'
            WHERE cm_source = 'CCDS'
        """).format(table=sql.Identifier(PRODUCTION_TABLE))

        with self._engine.raw_connection() as raw_conn:
            with raw_conn.cursor() as cur:
                cur.execute(max_non_ncbi_ccds)
                cur.execute(max_ncbi)
                cur.execute(hidden_ccds)
            raw_conn.commit()

        logger.info("coord_cm_mark_annotations_applied")

    def set_default_cm_note(self) -> None:
        clear_notes = sql.SQL("""
            UPDATE {table}
            SET cm_notes = NULL
            WHERE cm_notes IS NOT NULL
        """).format(table=sql.Identifier(PRODUCTION_TABLE))

        set_warning = sql.SQL("""
            UPDATE {table}
            SET cm_notes = %s
            WHERE cm_mapby IN (
                SELECT DISTINCT a.cm_mapby
                FROM {table} a, {table} b
                WHERE a.cm_mapby = b.cm_mapby
                  AND (
                    a.cm_start != b.cm_start OR
                    a.cm_end != b.cm_end
                  )
                  AND a.cm_chr = b.cm_chr
              )
        """).format(table=sql.Identifier(PRODUCTION_TABLE))

        warning_text = "\n<br><b>Warning<b>: This ID is associated with multiple coordinates"

        with self._engine.raw_connection() as raw_conn:
            with raw_conn.cursor() as cur:
                cur.execute(clear_notes)
                cur.execute(set_warning, [warning_text])
            raw_conn.commit()

        logger.info("coord_cm_note_annotations_applied")

    def promote_staging_to_production(self, staging_table: str) -> None:
        drop_prod = sql.SQL("DROP TABLE IF EXISTS {table}").format(
            table=sql.Identifier(PRODUCTION_TABLE),
        )
        rename = sql.SQL("ALTER TABLE {staging} RENAME TO {prod}").format(
            staging=sql.Identifier(staging_table),
            prod=sql.Identifier(PRODUCTION_TABLE),
        )
        update_mod_dates = sql.SQL(
            "UPDATE table_mod_dates SET date_modified = NOW() WHERE table_name = %s"
        )

        try:
            with self._engine.raw_connection() as raw_conn:
                with raw_conn.cursor() as cur:
                    cur.execute(drop_prod)
                    cur.execute(rename)
                    cur.execute(update_mod_dates, [PRODUCTION_TABLE])
                raw_conn.commit()

            logger.info(
                "coord_promotion_complete",
                extra={"staging_table": staging_table, "production_table": PRODUCTION_TABLE},
            )
        except Exception as exc:
            raise CoordPromotionError(
                staging_table=staging_table,
            ) from exc
