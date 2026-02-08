"""Backfill the description archive from existing active listing Parquet files.

One-time script to seed the ``description_archive`` table with any
descriptions already captured in the ``data/processed/active_listings``
directory.

Usage::

    python scripts/backfill_description_archive.py
"""

from __future__ import annotations

import logging
from pathlib import Path

from src.data.description_archive import DescriptionArchive

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DB_PATH = PROJECT_ROOT / "data" / "database" / "properties.duckdb"
ACTIVE_DIR = PROJECT_ROOT / "data" / "processed" / "active_listings"


def main() -> None:
    parquet_files = sorted(ACTIVE_DIR.glob("**/batch_*.parquet"))
    logger.info("Found %d batch parquet files to backfill from", len(parquet_files))

    if not parquet_files:
        logger.warning("No batch parquet files found in %s", ACTIVE_DIR)
        return

    archive = DescriptionArchive(DB_PATH)
    new = archive.upsert_from_parquet(parquet_files)
    stats = archive.stats()
    matched = archive.matched_to_sold()

    logger.info("Backfill complete:")
    logger.info("  New descriptions added: %d", new)
    logger.info("  Total in archive: %d", stats["total_descriptions"])
    logger.info("  Neighborhoods: %d", stats["neighborhoods"])
    logger.info("  Avg description length: %.0f chars", stats["avg_description_length"])
    logger.info("  Matched to sold properties: %d", matched)


if __name__ == "__main__":
    main()
