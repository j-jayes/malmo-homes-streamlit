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


def slice_input_subset(
    input_path: Path,
    subset_path: Path,
    offset: int = 0,
    max_records: int = 0,
    tracker: ProgressTracker | None = None,
) -> Tuple[int, int, int]:
    """Copy a window of rows from ``input_path`` into ``subset_path``.

    Args:
        input_path: Source file (CSV or Parquet) with at least a ``url`` column.
        subset_path: Destination file to write the sliced rows (CSV or Parquet).
        offset: Number of initial rows to skip.
        max_records: Maximum rows to copy after the offset; ``0`` means no limit.

    Returns:
        Tuple of (total_rows_in_source, rows_written_to_subset, rows_skipped_via_tracker).
    """
    input_path = input_path.expanduser().resolve()
    subset_path = subset_path.expanduser().resolve()
    subset_path.parent.mkdir(parents=True, exist_ok=True)

    skipped = 0
    written = 0
    total = 0
    cache_skipped = 0
    limit = max_records if max_records and max_records > 0 else None

    # Read input
    rows = []
    try:
        if input_path.suffix == '.parquet':
            import pandas as pd
            df = pd.read_parquet(input_path)
            rows = df.to_dict('records')
        else:
            with input_path.open("r", encoding="utf-8", newline="") as src:
                reader = csv.DictReader(src)
                rows = list(reader)
    except Exception as e:
        logger.error(f"Error reading input {input_path}: {e}")
        return 0, 0, 0

    total = len(rows)
    output_rows = []

    for i, row in enumerate(rows):
        if skipped < offset:
            skipped += 1
            continue
        row_url = str(row.get("url") or "").strip()
        if not row_url:
            continue
        row["url"] = row_url
        if tracker and tracker.should_skip(row):
            cache_skipped += 1
            continue
        if limit is not None and written >= limit:
            break

        output_rows.append(row)
        written += 1

    # Write output
    if output_rows:
        if subset_path.suffix == '.parquet':
            import pandas as pd
            df = pd.DataFrame(output_rows)
            df.to_parquet(subset_path, index=False)
        else:
            fieldnames = list(output_rows[0].keys())
            with subset_path.open("w", encoding="utf-8", newline="") as dst:
                writer = csv.DictWriter(dst, fieldnames=fieldnames)
                writer.writeheader()
                writer.writerows(output_rows)

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
    parser.add_argument(
        "--git-commit-interval",
        type=int,
        default=0,
        help="Commit scraped batches to git every N batches when running in CI (0 disables)",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    _configure_logging(args.log_level)

    # Resolve paths
    input_path = args.input.expanduser().resolve()
    if not input_path.exists():
        parser.error(f"Input file not found: {input_path}")

    output_dir = args.output_dir.expanduser().resolve()
    output_dir.mkdir(parents=True, exist_ok=True)

    # Default subset path extension matches input if not specified
    default_subset_name = "subset.parquet" if input_path.suffix == '.parquet' else "subset.csv"
    
    subset_path = (
        args.subset_output.expanduser().resolve()
        if args.subset_output
        else output_dir / default_subset_name
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

    total_rows, subset_rows, cache_skipped = slice_input_subset(
        input_path=input_path,
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
        git_commit_interval=max(args.git_commit_interval, 0),
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

    # Nothing left to process — all URLs are already in the progress cache.
    if metadata.get("total_processed", 0) == 0:
        logger.info("No new URLs to process — all source URLs already in progress cache.")
        return 0

    # Tolerate up to 10% failure rate — validation rejects (low prices, etc.)
    # are expected for a small fraction of listings.
    if success_rate >= 90.0:
        return 0
    logger.error("Success rate %.1f%% is below 90%% threshold", success_rate)
    return 1


if __name__ == "__main__":
    sys.exit(main())
