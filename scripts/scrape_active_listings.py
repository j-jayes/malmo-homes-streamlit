"""End-to-end orchestrator for scraping active (for-sale) listings.

1. Collect property links from Hemnet search pages.
2. Scrape detail pages for each link.
3. Aggregate Parquet output into the DuckDB ``active_listings`` table.
4. Optionally generate ML predictions.

Designed to run both locally and inside GitHub Actions.

Usage::

    # Quick local test (5 links, 1 page)
    python scripts/scrape_active_listings.py --max-pages 1 --max-records 5

    # Full run with predictions
    python scripts/scrape_active_listings.py --predict

    # CI mode (longer delays, git commits)
    python scripts/scrape_active_listings.py --predict --git-commit-interval 20
"""

from __future__ import annotations

import argparse
import logging
import sys
from datetime import datetime
from pathlib import Path

logger = logging.getLogger(__name__)

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_LOCATION_ID = ""  # Empty = all of Sweden
DEFAULT_DB = PROJECT_ROOT / "data" / "database" / "properties.duckdb"
DEFAULT_MODEL = PROJECT_ROOT / "models" / "price_model.joblib"


def _configure_logging(level: str) -> None:
    logging.basicConfig(
        level=getattr(logging, level.upper(), logging.INFO),
        format="%(asctime)s - %(levelname)s - %(message)s",
    )


def collect_links(
    location_id: str,
    max_pages: int,
    output_path: Path,
    headless: bool,
) -> int:
    """Collect active listing URLs from Hemnet search pages.

    Returns the number of unique links saved.
    """
    from src.scrapers.link_collector import scrape_multiple_pages, save_links_to_parquet

    base_url = "https://www.hemnet.se/bostader?item_types=bostadsratt"
    if location_id:
        base_url += f"&expand_locations=10000&location_ids={location_id}"
    scope = location_id or "all-Sweden"
    logger.info("Collecting active listing links (scope=%s, max_pages=%s)", scope, max_pages)
    results = scrape_multiple_pages(base_url, max_pages=max_pages, headless=headless)

    total_links = sum(len(r.get("links", [])) for r in results)
    if total_links == 0:
        logger.warning("No links collected")
        return 0

    output_path.parent.mkdir(parents=True, exist_ok=True)
    save_links_to_parquet(results, str(output_path))
    logger.info("Saved %d links to %s", total_links, output_path)
    return total_links


def scrape_details(
    input_path: Path,
    output_dir: Path,
    batch_size: int,
    max_records: int,
    headless: bool,
    git_commit_interval: int,
) -> dict:
    """Scrape property details using the existing batch CLI.

    Calls ``batch_manager_cli.main`` directly with an explicit argv list so
    that the host script's ``sys.argv`` does not bleed through.
    """
    from src.scrapers.batch_manager_cli import main as batch_cli_main

    argv: list[str] = [
        "--input", str(input_path),
        "--output-dir", str(output_dir),
        "--batch-size", str(batch_size),
        "--no-resume",
        "--no-skip-processed",
    ]
    if max_records > 0:
        argv += ["--max-records", str(max_records)]
    if not headless:
        argv.append("--show-browser")
    if git_commit_interval > 0:
        argv += ["--git-commit-interval", str(git_commit_interval)]

    logger.info("Running batch scraper with argv: %s", argv)
    exit_code = batch_cli_main(argv)
    return {"exit_code": exit_code}


def aggregate_and_predict(
    input_dir: Path,
    db_path: Path,
    model_path: Path,
    predict: bool,
) -> dict:
    """Aggregate parquet files to DuckDB and optionally run predictions."""
    from src.data.aggregate_active_listings import (
        aggregate_active_listings,
        predict_active_listings,
    )

    count = aggregate_active_listings(input_dir, db_path)
    pred_count = 0
    if predict and count > 0 and model_path.exists():
        pred_count = predict_active_listings(db_path, model_path)
    return {"listings": count, "predictions": pred_count}


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Scrape active Hemnet listings end-to-end",
    )
    parser.add_argument("--location-id", default=DEFAULT_LOCATION_ID, help="Hemnet location ID (empty=all Sweden)")
    parser.add_argument("--max-pages", type=int, default=50, help="Search result pages to crawl (Hemnet max=50)")
    parser.add_argument("--max-records", type=int, default=0, help="Max detail pages to scrape (0=all)")
    parser.add_argument("--batch-size", type=int, default=10)
    parser.add_argument("--output-dir", type=Path, default=Path("data/processed/active_listings"))
    parser.add_argument("--db", type=Path, default=DEFAULT_DB)
    parser.add_argument("--model", type=Path, default=DEFAULT_MODEL)
    parser.add_argument("--predict", action="store_true", help="Run ML predictions after aggregation")
    parser.add_argument("--headless", action="store_true", default=True)
    parser.add_argument("--show-browser", action="store_true")
    parser.add_argument("--git-commit-interval", type=int, default=0)
    parser.add_argument("--log-level", default="INFO")
    parser.add_argument(
        "--skip-collect",
        action="store_true",
        help="Skip link collection (reuse existing links file)",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    _configure_logging(args.log_level)

    headless = args.headless and not args.show_browser
    output_dir = args.output_dir.expanduser().resolve()
    output_dir.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d")
    links_path = output_dir / f"links_{timestamp}.parquet"
    batches_dir = output_dir / f"batches_{timestamp}"

    # Step 1: Collect links
    if not args.skip_collect:
        n_links = collect_links(args.location_id, args.max_pages, links_path, headless)
        if n_links == 0:
            logger.error("No links collected — aborting")
            return 1
    else:
        if not links_path.exists():
            logger.error("Links file not found: %s", links_path)
            return 1
        logger.info("Skipping link collection — using %s", links_path)

    # Step 2: Scrape details
    result = scrape_details(
        input_path=links_path,
        output_dir=batches_dir,
        batch_size=args.batch_size,
        max_records=args.max_records,
        headless=headless,
        git_commit_interval=args.git_commit_interval,
    )
    if result["exit_code"] != 0:
        logger.warning("Scraper exited with code %s (below 90%% success rate)", result["exit_code"])

    # Step 3: Aggregate + predict
    agg = aggregate_and_predict(batches_dir, args.db, args.model, args.predict)
    logger.info(
        "Pipeline complete: %d listings, %d predictions",
        agg["listings"],
        agg["predictions"],
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
