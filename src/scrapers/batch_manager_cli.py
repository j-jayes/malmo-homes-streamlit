"""Command-line interface for batch property scraping.

Provides a thin wrapper that slices an input CSV, feeds it to the BatchManager,
tracks metadata, and emits scrape metrics for GitHub Actions logs.
"""

from __future__ import annotations

import argparse
import csv
import json
import logging
import sys
from pathlib import Path
from typing import Tuple

from src.scrapers.batch_manager import BatchManager
from src.scrapers.progress_tracker import ProgressTracker

logger = logging.getLogger(__name__)


def _configure_logging(level: str) -> None:
    logging.basicConfig(
        level=getattr(logging, level.upper(), logging.INFO),
        format="%(asctime)s - %(levelname)s - %(message)s",
    )


def slice_csv_subset(
    input_csv: Path,
    subset_path: Path,
    offset: int = 0,
    max_records: int = 0,
    tracker: ProgressTracker | None = None,
) -> Tuple[int, int, int]:
    """Copy a window of rows from ``input_csv`` into ``subset_path``.

    Args:
        input_csv: Source CSV with at least a ``url`` column.
        subset_path: Destination file to write the sliced rows.
        offset: Number of initial rows to skip.
        max_records: Maximum rows to copy after the offset; ``0`` means no limit.

    Returns:
        Tuple of (total_rows_in_source, rows_written_to_subset, rows_skipped_via_tracker).
    """
    input_csv = input_csv.expanduser().resolve()
    subset_path = subset_path.expanduser().resolve()
    subset_path.parent.mkdir(parents=True, exist_ok=True)

    skipped = 0
    written = 0
    total = 0
    cache_skipped = 0
    limit = max_records if max_records and max_records > 0 else None

    with input_csv.open("r", encoding="utf-8", newline="") as src, subset_path.open(
        "w", encoding="utf-8", newline=""
    ) as dst:
        reader = csv.DictReader(src)
        fieldnames = reader.fieldnames or []
        writer = csv.DictWriter(dst, fieldnames=fieldnames)
        writer.writeheader()

        for row in reader:
            total += 1
            if skipped < offset:
                skipped += 1
                continue
            if tracker and tracker.should_skip(row):
                cache_skipped += 1
                continue
            if limit is not None and written >= limit:
                break

            writer.writerow(row)
            written += 1

    logger.info(
        "Sliced %s rows out of %s (offset=%s, max_records=%s) into %s",
        written,
        total,
        offset,
        max_records,
        subset_path,
    )
    if cache_skipped:
        logger.info("Skipped %s rows already present in progress cache", cache_skipped)
    return total, written, cache_skipped


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Batch property detail scraper")
    parser.add_argument("--input", required=True, type=Path, help="Input CSV file with URLs")
    parser.add_argument(
        "--output-dir",
        required=True,
        type=Path,
        help="Directory to store parquet batches and metadata",
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        default=10,
        help="Number of properties per batch (default: 10)",
    )
    parser.add_argument(
        "--offset",
        type=int,
        default=0,
        help="Row offset inside the input CSV before scraping begins",
    )
    parser.add_argument(
        "--max-records",
        type=int,
        default=0,
        help="Maximum number of rows to scrape after offset (0 = all)",
    )
    parser.add_argument(
        "--subset-output",
        type=Path,
        help="Optional path for the intermediate subset CSV"
        " (default: <output-dir>/subset.csv)",
    )
    parser.add_argument(
        "--log-level",
        default="INFO",
        help="Logging level (DEBUG, INFO, WARNING, ERROR)",
    )
    parser.add_argument(
        "--no-resume",
        action="store_true",
        help="Disable resume mode and always start from batch 0",
    )
    parser.add_argument(
        "--show-browser",
        action="store_true",
        help="Run Playwright in headed mode for debugging",
    )
    parser.add_argument(
        "--progress-cache",
        type=Path,
        help="Path to progress cache file (default: <output-dir>/progress_cache.json)",
    )
    parser.add_argument(
        "--skip-processed",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="Skip rows already tracked as processed (default: true)",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    _configure_logging(args.log_level)

    # Resolve paths
    input_csv = args.input.expanduser().resolve()
    if not input_csv.exists():
        parser.error(f"Input CSV not found: {input_csv}")

    output_dir = args.output_dir.expanduser().resolve()
    output_dir.mkdir(parents=True, exist_ok=True)

    subset_path = (
        args.subset_output.expanduser().resolve()
        if args.subset_output
        else output_dir / "subset.csv"
    )

    tracker: ProgressTracker | None = None
    if args.skip_processed:
        cache_path = (
            args.progress_cache.expanduser().resolve()
            if args.progress_cache
            else output_dir / "progress_cache.json"
        )
        tracker = ProgressTracker(cache_path)
        logger.info("Loaded %s processed identifiers from %s", tracker.count, cache_path)

    total_rows, subset_rows, cache_skipped = slice_csv_subset(
        input_csv=input_csv,
        subset_path=subset_path,
        offset=max(args.offset, 0),
        max_records=max(args.max_records, 0),
        tracker=tracker,
    )

    if subset_rows == 0:
        logger.warning(
            "No rows selected for scraping (total_rows=%s, offset=%s, max_records=%s)",
            total_rows,
            args.offset,
            args.max_records,
        )
        return 0

    manager = BatchManager(
        input_file=subset_path,
        output_dir=output_dir,
        batch_size=max(args.batch_size, 1),
        headless=not args.show_browser,
        progress_tracker=tracker,
    )

    try:
        metadata = manager.process_all(
            batch_start=0,
            batch_end=None,
            resume=not args.no_resume,
        )
    finally:
        manager.close()

    metrics = {
        "subset_rows": subset_rows,
        "total_source_rows": total_rows,
        "processed": metadata.get("total_processed", 0),
        "successful": metadata.get("total_successful", 0),
        "failed": metadata.get("total_failed", 0),
        "skipped_from_cache": cache_skipped,
    }
    logger.info("SCRAPE_METRIC %s", json.dumps(metrics))
    success_rate = (
        metadata.get("total_successful", 0)
        / metadata.get("total_processed", 1)
        * 100
        if metadata.get("total_processed", 0)
        else 0.0
    )
    logger.info("Success rate: %.1f%%", success_rate)
    if tracker:
        tracker.save()
    return 0 if metadata.get("total_failed", 0) == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
