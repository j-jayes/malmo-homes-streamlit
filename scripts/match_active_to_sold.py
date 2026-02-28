"""Match active listings in the description_archive to their final sold property ID.

This script runs periodically to find corresponding sales for properties
whose text was captured while they were active on Hemnet. We match using
address, living_area, and ensuring the sold_date occurs after we first seen it active.

Usage::
    uv run python scripts/match_active_to_sold.py
"""

from __future__ import annotations

import logging
from pathlib import Path

import duckdb

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DB_PATH = PROJECT_ROOT / "data" / "database" / "properties.duckdb"

def match_listings() -> None:
    conn = duckdb.connect(str(DB_PATH))
    try:
        # Check if the tables exist
        tables = [r[0] for r in conn.execute("SHOW TABLES").fetchall()]
        if "description_archive" not in tables or "properties" not in tables:
            logger.error("Required tables missing from database.")
            return

        # Make sure the sold_property_id column exists
        try:
            conn.execute("ALTER TABLE description_archive ADD COLUMN sold_property_id VARCHAR")
        except duckdb.CatalogException:
            pass # Already exists

        # Perform the match
        # We match on address and living_area, and ensure the sold_date is plausible.
        # Since sold_date is VARCHAR (YYYY-MM-DD) in properties, we CAST it.
        # We only update rows that don't already have a sold_property_id.
        
        query = """
            WITH Matches AS (
                SELECT 
                    a.property_id as active_id, 
                    MAX(p.property_id) as new_sold_id
                FROM description_archive a
                JOIN properties p 
                  ON a.address = p.address 
                 AND a.living_area = p.living_area 
                 AND (a.rooms = p.rooms OR (a.rooms IS NULL AND p.rooms IS NULL))
                WHERE a.sold_property_id IS NULL
                  AND CAST(p.sold_date AS DATE) >= a.first_seen
                GROUP BY a.property_id
            )
            UPDATE description_archive
            SET sold_property_id = Matches.new_sold_id
            FROM Matches
            WHERE description_archive.property_id = Matches.active_id;
        """
        
        before_nulls = conn.execute("SELECT COUNT(*) FROM description_archive WHERE sold_property_id IS NULL").fetchone()[0]
        conn.execute(query)
        after_nulls = conn.execute("SELECT COUNT(*) FROM description_archive WHERE sold_property_id IS NULL").fetchone()[0]
        
        new_matches = before_nulls - after_nulls
        
        total_matched = conn.execute("SELECT COUNT(*) FROM description_archive WHERE sold_property_id IS NOT NULL").fetchone()[0]
        total_archive = conn.execute("SELECT COUNT(*) FROM description_archive").fetchone()[0]
        
        logger.info("Matching complete.")
        logger.info(f"New connections made: {new_matches}")
        logger.info(f"Total archive size: {total_archive}")
        logger.info(f"Total joined properties ready for NLP: {total_matched} ({total_matched/max(total_archive, 1)*100:.1f}%)")

    finally:
        conn.close()


if __name__ == "__main__":
    match_listings()
