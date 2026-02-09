"""Persistent archive for property descriptions.

Hemnet removes ad descriptions from sold property pages, so descriptions
are only available while a listing is active.  This module maintains a
``description_archive`` table in DuckDB that accumulates descriptions
across daily scrape runs, preserving them even after the listing sells.

The archive is keyed on ``property_id`` (INSERT-or-IGNORE semantics) so
that re-scraping the same listing does not create duplicates but *does*
update the ``last_seen_date``.

Over time, archived descriptions can be joined to the ``properties``
table (sold listings) via ``property_id`` to train NLP models that
relate ad text to final sale price.
"""

from __future__ import annotations

import logging
from datetime import date
from pathlib import Path

import duckdb

logger = logging.getLogger(__name__)

TABLE = "description_archive"

_DDL = f"""
CREATE TABLE IF NOT EXISTS {TABLE} (
    property_id      VARCHAR PRIMARY KEY,
    url              VARCHAR,
    address          VARCHAR,
    city             VARCHAR,
    neighborhood     VARCHAR,
    latitude         DOUBLE,
    longitude        DOUBLE,
    asking_price     BIGINT,
    living_area      DOUBLE,
    rooms            DOUBLE,
    building_year    INTEGER,
    association_fee  INTEGER,
    housing_type     VARCHAR,
    ownership_type   VARCHAR,
    description      VARCHAR NOT NULL,
    first_seen       DATE NOT NULL,
    last_seen        DATE NOT NULL,
    scraped_at       VARCHAR
);
"""


class DescriptionArchive:
    """Manages the persistent description archive in DuckDB."""

    def __init__(self, db_path: Path) -> None:
        self._db_path = db_path

    def _connect(self) -> duckdb.DuckDBPyConnection:
        return duckdb.connect(str(self._db_path))

    def ensure_table(self) -> None:
        conn = self._connect()
        try:
            conn.execute(_DDL)
        finally:
            conn.close()

    def upsert_from_parquet(self, parquet_paths: list[Path]) -> int:
        """Insert new descriptions and update ``last_seen`` for existing ones.

        Returns the number of *new* descriptions added.
        """
        if not parquet_paths:
            return 0

        self.ensure_table()
        files = [str(p) for p in parquet_paths]
        today = date.today().isoformat()

        conn = self._connect()
        try:
            before = conn.execute(f"SELECT COUNT(*) FROM {TABLE}").fetchone()[0]

            conn.execute(f"""
                INSERT INTO {TABLE}
                SELECT
                    property_id,
                    url,
                    address,
                    city,
                    neighborhood,
                    latitude,
                    longitude,
                    asking_price,
                    living_area,
                    rooms,
                    building_year,
                    association_fee,
                    housing_type,
                    ownership_type,
                    description,
                    '{today}'::DATE AS first_seen,
                    '{today}'::DATE AS last_seen,
                    scraped_at
                FROM read_parquet($1)
                WHERE description IS NOT NULL
                  AND LENGTH(TRIM(description)) > 0
                ON CONFLICT (property_id) DO UPDATE
                SET last_seen = '{today}'::DATE
            """, [files])

            after = conn.execute(f"SELECT COUNT(*) FROM {TABLE}").fetchone()[0]
            new_count = after - before
            logger.info(
                "Description archive: %d new, %d total (%d parquet files ingested)",
                new_count, after, len(files),
            )
            return new_count
        finally:
            conn.close()

    def upsert_from_active_table(self) -> int:
        """Archive descriptions directly from the ``active_listings`` table.

        Useful as a fallback when raw Parquet files are unavailable.
        """
        self.ensure_table()
        today = date.today().isoformat()

        conn = self._connect()
        try:
            before = conn.execute(f"SELECT COUNT(*) FROM {TABLE}").fetchone()[0]

            conn.execute(f"""
                INSERT INTO {TABLE}
                SELECT
                    property_id,
                    url,
                    address,
                    city,
                    neighborhood,
                    latitude,
                    longitude,
                    asking_price,
                    living_area,
                    rooms,
                    building_year,
                    association_fee,
                    housing_type,
                    ownership_type,
                    description,
                    '{today}'::DATE AS first_seen,
                    '{today}'::DATE AS last_seen,
                    scraped_at
                FROM active_listings
                WHERE description IS NOT NULL
                  AND LENGTH(TRIM(description)) > 0
                ON CONFLICT (property_id) DO UPDATE
                SET last_seen = '{today}'::DATE
            """)

            after = conn.execute(f"SELECT COUNT(*) FROM {TABLE}").fetchone()[0]
            new_count = after - before
            logger.info(
                "Description archive (from active_listings table): %d new, %d total",
                new_count, after,
            )
            return new_count
        finally:
            conn.close()

    def stats(self) -> dict:
        """Return summary statistics about the archive."""
        self.ensure_table()
        conn = self._connect()
        try:
            row = conn.execute(f"""
                SELECT
                    COUNT(*)                           AS total,
                    COUNT(DISTINCT neighborhood)       AS neighborhoods,
                    AVG(LENGTH(description))           AS avg_desc_length,
                    MIN(first_seen)                    AS earliest,
                    MAX(last_seen)                     AS latest
                FROM {TABLE}
            """).fetchone()
            return {
                "total_descriptions": row[0],
                "neighborhoods": row[1],
                "avg_description_length": round(row[2], 0) if row[2] else 0,
                "earliest_date": str(row[3]) if row[3] else None,
                "latest_date": str(row[4]) if row[4] else None,
            }
        finally:
            conn.close()

    def matched_to_sold(self) -> int:
        """Count how many archived descriptions can be joined to sold properties."""
        self.ensure_table()
        conn = self._connect()
        try:
            tables = [r[0] for r in conn.execute("SHOW TABLES").fetchall()]
            if "properties" not in tables:
                return 0
            row = conn.execute(f"""
                SELECT COUNT(*)
                FROM {TABLE} a
                JOIN properties p ON a.property_id = p.property_id
            """).fetchone()
            return row[0]
        finally:
            conn.close()
