"""Collect sold property listing URLs from Hemnet search pages.

Uses an adaptive area-range strategy to stay under Hemnet's 2,500-result
search limit.  The scraper binary-searches for the widest m² band that
returns fewer than 2,400 results, scrapes those pages, then advances to
the next band until the full 0–500 m² range is covered.

Two date-filtering modes are supported (mutually exclusive):

* **Relative** (``--sold-age``): "1m", "3m", "6m", "12m" — Hemnet
  built-in windows, useful for ongoing weekly collection.
* **Absolute** (``--sold-min`` / ``--sold-max``): YYYY-MM-DD boundaries,
  enables month-by-month backfill combined with area partitioning.
  This is the only mode guaranteed to stay under the 2,500 limit at
  national scale for historical data.

Output: per-range CSV files + a consolidated ``sold_properties_all_areas.csv``.

Usage::

    # Ongoing: last month's national sales
    python scripts/collect_sold_links.py --sold-age 1m --headless

    # Backfill: one calendar month, area-partitioned
    python scripts/collect_sold_links.py \\
        --sold-min 2024-03-01 --sold-max 2024-04-01 \\
        --output-dir data/raw/area_ranges_national/202403 \\
        --headless

    # Single city, all time
    python scripts/collect_sold_links.py \\
        --location-id 17989 --headless

    # Consolidate existing range files without scraping
    python scripts/collect_sold_links.py --consolidate-only
"""

import argparse
import json
import logging
import os
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.scrapers.sold_properties_scraper import SoldPropertiesScraper

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


class AdaptiveAreaScraper:
    """Scrape all sold properties by adaptively partitioning living-area ranges."""

    RESULT_LIMIT = 2500
    SAFE_LIMIT = 2400  # Stay under the hard limit with a small margin
    MIN_STEP = 1       # Minimum step size in m²
    MAX_AREA = 500     # Maximum reasonable apartment size to consider

    def __init__(
        self,
        location_id: str = "17989",
        headless: bool = True,
        output_dir: Optional[Path] = None,
        sold_age: Optional[str] = None,
        sold_min: Optional[str] = None,
        sold_max: Optional[str] = None,
    ) -> None:
        self.location_id = location_id
        self.sold_age = sold_age
        self.sold_min = sold_min
        self.sold_max = sold_max
        self.scraper = SoldPropertiesScraper(headless=headless, slow_mo=0 if headless else 100)
        self.output_dir = output_dir or Path("data/raw/area_ranges")
        self.output_dir.mkdir(parents=True, exist_ok=True)

        self.progress_file = self.output_dir / "progress.json"
        self.progress = self._load_progress()

    # ------------------------------------------------------------------ #
    #  Progress tracking                                                   #
    # ------------------------------------------------------------------ #

    def _load_progress(self) -> Dict:
        if self.progress_file.exists():
            try:
                with open(self.progress_file) as f:
                    return json.load(f)
            except (json.JSONDecodeError, IOError) as exc:
                logger.warning("Progress file unreadable (%s); starting fresh.", exc)
        return {
            "completed_ranges": [],
            "total_properties": 0,
            "started_at": datetime.now().isoformat(),
        }

    def _save_progress(self) -> None:
        tmp = self.progress_file.with_suffix(".json.tmp")
        with open(tmp, "w") as f:
            json.dump(self.progress, f, indent=2)
        os.replace(tmp, self.progress_file)

    def _is_range_completed(self, area_min: int, area_max: int) -> bool:
        return f"{area_min}-{area_max}" in self.progress["completed_ranges"]

    def _mark_range_completed(self, area_min: int, area_max: int, count: int) -> None:
        self.progress["completed_ranges"].append(f"{area_min}-{area_max}")
        self.progress["total_properties"] += count
        self._save_progress()

    def _git_commit_progress(self, area_min: int, area_max: int) -> None:
        """Commit scraped data to git (CI only)."""
        if not os.environ.get("CI"):
            return
        try:
            logger.info("Committing progress for range %d-%dm²…", area_min, area_max)
            subprocess.run(
                ["git", "add", str(self.output_dir / "*.csv"), str(self.output_dir / "*.json")],
                check=False, capture_output=True,
            )
            result = subprocess.run(
                ["git", "diff", "--staged", "--quiet"], capture_output=True
            )
            if result.returncode != 0:
                subprocess.run(
                    ["git", "commit", "-m", f"data: scraped area range {area_min}-{area_max}m²"],
                    check=True, capture_output=True,
                )
                subprocess.run(["git", "push"], check=True, capture_output=True)
                logger.info("Committed and pushed range %d-%dm².", area_min, area_max)
        except subprocess.CalledProcessError as exc:
            logger.warning("Git commit/push failed: %s. Continuing.", exc)

    # ------------------------------------------------------------------ #
    #  Adaptive binary search                                              #
    # ------------------------------------------------------------------ #

    def find_optimal_range(self, min_area: int, initial_max: int) -> Tuple[int, int]:
        """Return the largest m² range starting at *min_area* under SAFE_LIMIT."""
        logger.info("Finding optimal range from %dm²…", min_area)

        initial_count = self.scraper.get_total_results_count(
            location_id=self.location_id,
            area_min=min_area,
            area_max=min(initial_max, self.MAX_AREA),
            sold_age=self.sold_age,
            sold_min=self.sold_min,
            sold_max=self.sold_max,
        )
        logger.info(
            "  Initial range %d-%dm²: %d results",
            min_area, min(initial_max, self.MAX_AREA), initial_count,
        )

        if initial_count == 0:
            return min_area, min_area + self.MIN_STEP

        if initial_count < self.SAFE_LIMIT:
            return min_area, min(initial_max, self.MAX_AREA)

        # Binary search for the largest safe band
        logger.info("  Over limit (%d >= %d); binary-searching…", initial_count, self.SAFE_LIMIT)
        low = min_area + self.MIN_STEP
        high = min(initial_max, self.MAX_AREA)
        best_max = low
        best_count = 0

        while low <= high:
            mid = (low + high) // 2
            count = self.scraper.get_total_results_count(
                location_id=self.location_id,
                area_min=min_area,
                area_max=mid,
                sold_age=self.sold_age,
                sold_min=self.sold_min,
                sold_max=self.sold_max,
            )
            logger.info("  Testing %d-%dm²: %d results", min_area, mid, count)

            if count == 0 or count >= self.SAFE_LIMIT:
                high = mid - 1
            else:
                best_max = mid
                best_count = count
                low = mid + 1

        logger.info("Optimal range: %d-%dm² (%d results)", min_area, best_max, best_count)
        return min_area, best_max

    # ------------------------------------------------------------------ #
    #  Scraping                                                            #
    # ------------------------------------------------------------------ #

    def scrape_range(self, area_min: int, area_max: int, max_pages: int = 50) -> List[Dict]:
        if self._is_range_completed(area_min, area_max):
            logger.info("Range %d-%dm² already done; skipping.", area_min, area_max)
            return []

        logger.info("Scraping range %d-%dm²", area_min, area_max)
        try:
            properties = self.scraper.scrape_area_range(
                area_min=area_min,
                area_max=area_max,
                location_id=self.location_id,
                max_pages=max_pages,
                sold_age=self.sold_age,
                sold_min=self.sold_min,
                sold_max=self.sold_max,
            )
            output_file = self.output_dir / f"properties_{area_min}_{area_max}.csv"
            self.scraper.save_to_csv(properties, output_file)
            self._mark_range_completed(area_min, area_max, len(properties))
            self._git_commit_progress(area_min, area_max)
            logger.info("Completed %d-%dm²: %d properties.", area_min, area_max, len(properties))
            return properties
        except Exception as exc:
            logger.error("Error scraping %d-%dm²: %s", area_min, area_max, exc)
            raise

    def scrape_all(
        self,
        initial_step: int = 50,
        max_pages: int = 50,
        min_area: int = 0,
        max_area_limit: int = 500,
    ) -> List[Dict]:
        """Iterate through all area bands up to *max_area_limit*."""
        logger.info(
            "Starting adaptive area scraping (location=%s, sold_age=%s, "
            "sold_min=%s, sold_max=%s, step=%dm², range=%d-%dm²)",
            self.location_id or "national",
            self.sold_age, self.sold_min, self.sold_max,
            initial_step, min_area, max_area_limit,
        )

        current = min_area
        all_properties: List[Dict] = []

        # Map completed ranges for fast skipping
        completed = {}
        for r_str in self.progress.get("completed_ranges", []):
            try:
                c_min, c_max = map(int, r_str.split("-"))
                completed[c_min] = c_max
            except ValueError:
                continue

        while current < max_area_limit:
            if current in completed:
                logger.info(
                    "Range starting at %dm² already completed (ends at %dm²). Skipping.",
                    current, completed[current]
                )
                current = completed[current]
                continue

            range_min, range_max = self.find_optimal_range(current, current + initial_step)

            if range_max <= range_min:
                logger.warning(
                    "Cannot advance from %dm² (even 1m² band overflows). "
                    "Consider combining with a tighter date window (--sold-min/--sold-max). "
                    "Skipping this band.",
                    current,
                )
                current += self.MIN_STEP
                continue

            props = self.scrape_range(range_min, range_max, max_pages)
            all_properties.extend(props)
            current = range_max

            logger.info(
                "Progress: %d properties collected; next band starts at %dm²",
                len(all_properties), current,
            )

        logger.info(
            "Scraping complete. %d unique properties collected.",
            len(set(p["property_id"] for p in all_properties)),
        )
        return all_properties

    # ------------------------------------------------------------------ #
    #  Consolidation                                                       #
    # ------------------------------------------------------------------ #

    def consolidate_results(self, output_file: Optional[Path] = None) -> List[Dict]:
        """Merge all per-range CSV files into a single deduplicated master file.

        Also appends new links to the existing master file so incremental
        runs accumulate over time without duplicates.
        """
        import csv

        output_file = output_file or Path("data/raw/sold_properties_all_areas.csv")
        logger.info("Consolidating results…")

        # Read all per-range CSV files (including any subdirectories)
        all_properties: Dict[str, Dict] = {}
        for csv_file in sorted(self.output_dir.rglob("properties_*.csv")):
            logger.info("  Reading %s", csv_file.name)
            with open(csv_file, encoding="utf-8") as f:
                for row in csv.DictReader(f):
                    pid = row["property_id"]
                    if pid not in all_properties:
                        all_properties[pid] = row

        # Merge with existing master file (deduplication)
        if output_file.exists():
            with open(output_file, encoding="utf-8") as f:
                for row in csv.DictReader(f):
                    pid = row["property_id"]
                    if pid not in all_properties:
                        all_properties[pid] = row

        logger.info("Writing %d unique properties to %s", len(all_properties), output_file)
        props_list = list(all_properties.values())
        self.scraper.save_to_csv(props_list, output_file)
        return props_list


# --------------------------------------------------------------------------- #
#  CLI                                                                         #
# --------------------------------------------------------------------------- #

def main() -> None:
    parser = argparse.ArgumentParser(
        description="Collect sold property URLs using adaptive area-range partitioning.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument("--location-id", default="",
                        help="Hemnet location ID (default: '' = all Sweden)")
    parser.add_argument("--initial-step", type=int, default=50,
                        help="Initial m² step size (default: 50)")
    parser.add_argument("--max-pages", type=int, default=50,
                        help="Max search-result pages per range (default: 50)")
    parser.add_argument("--min-area", type=int, default=0,
                        help="Starting living area in m² (default: 0)")
    parser.add_argument("--max-area", type=int, default=500,
                        help="Ending living area in m² (default: 500)")
    parser.add_argument("--output-dir", type=str,
                        help="Directory for per-range CSV files")
    parser.add_argument("--headless", action="store_true",
                        help="Run browser headlessly (required for CI)")
    parser.add_argument("--consolidate-only", action="store_true",
                        help="Skip scraping; only consolidate existing CSV files")

    # Date-filtering (mutually exclusive)
    date_group = parser.add_mutually_exclusive_group()
    date_group.add_argument("--sold-age", type=str,
                            help='Relative sold-age window: "1m", "3m", "6m", "12m"')
    date_group.add_argument("--sold-min", type=str,
                            help="Absolute sold-from date (YYYY-MM-DD). Requires --sold-max.")

    parser.add_argument("--sold-max", type=str,
                        help="Absolute sold-to date exclusive (YYYY-MM-DD). Requires --sold-min.")

    args = parser.parse_args()

    if args.sold_min and not args.sold_max:
        parser.error("--sold-max is required when using --sold-min")
    if args.sold_max and not args.sold_min:
        parser.error("--sold-min is required when using --sold-max")

    output_dir = Path(args.output_dir) if args.output_dir else Path("data/raw/area_ranges")

    scraper = AdaptiveAreaScraper(
        location_id=args.location_id,
        headless=args.headless,
        output_dir=output_dir,
        sold_age=args.sold_age,
        sold_min=args.sold_min,
        sold_max=args.sold_max,
    )

    if args.consolidate_only:
        scraper.consolidate_results()
        return

    try:
        scraper.scrape_all(
            initial_step=args.initial_step,
            max_pages=args.max_pages,
            min_area=args.min_area,
            max_area_limit=args.max_area,
        )
        scraper.consolidate_results()
    except KeyboardInterrupt:
        logger.info("Interrupted. Progress saved; re-run to resume.")
    except Exception as exc:
        logger.error("Scraping failed: %s", exc)
        raise


if __name__ == "__main__":
    main()
