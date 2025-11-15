"""
Historical Sold Properties Link Collector
==========================================

Clever backfill strategy to collect all sold property links since 2020.

Strategy:
- Scrape month-by-month (avoids 2,500 result limit)
- Each month typically has <500 properties (well under limit)
- Collect only links first (fast!)
- Tomorrow: scrape full details from collected links
- Resume capability if interrupted
- Progress tracking with ETA

Execution Time Estimate:
- ~60 months × 10 minutes = ~10 hours total
- Or run overnight and wake up to complete dataset!
"""

import argparse
import csv
import json
import logging
import sys
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Dict

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.scrapers.sold_properties_scraper import SoldPropertiesScraper


# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class HistoricalLinkCollector:
    """Collect sold property links across multiple months"""
    
    def __init__(
        self,
        start_year: int = 2020,
        start_month: int = 1,
        end_year: int = None,
        end_month: int = None,
        location_id: str = "17989",
        output_dir: Path = None,
        headless: bool = False
    ):
        self.start_year = start_year
        self.start_month = start_month
        
        # Default to current month if not specified
        if end_year is None or end_month is None:
            now = datetime.now()
            self.end_year = now.year
            self.end_month = now.month
        else:
            self.end_year = end_year
            self.end_month = end_month
        
        self.location_id = location_id
        self.output_dir = output_dir or Path("data/raw/sold_links")
        self.headless = headless
        
        # Create output directory
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        # Progress file
        self.progress_file = self.output_dir / "backfill_progress.json"
        self.completed_months = self._load_progress()
        
    def _load_progress(self) -> set:
        """Load previously completed months"""
        if self.progress_file.exists():
            with open(self.progress_file, 'r') as f:
                data = json.load(f)
                logger.info(f"Loaded progress: {len(data['completed'])} months already scraped")
                return set(data['completed'])
        return set()
    
    def _save_progress(self, month_str: str):
        """Save progress after each month"""
        self.completed_months.add(month_str)
        
        with open(self.progress_file, 'w') as f:
            json.dump({
                'completed': sorted(list(self.completed_months)),
                'last_updated': datetime.now().isoformat()
            }, f, indent=2)
    
    def _generate_months(self) -> List[tuple]:
        """Generate list of (year, month) tuples to scrape"""
        months = []
        current = datetime(self.start_year, self.start_month, 1)
        end = datetime(self.end_year, self.end_month, 1)
        
        while current <= end:
            month_str = f"{current.year}-{current.month:02d}"
            if month_str not in self.completed_months:
                months.append((current.year, current.month))
            current += timedelta(days=32)
            current = current.replace(day=1)
        
        return months
    
    def collect_all(self, max_pages_per_month: int = 50) -> Dict:
        """
        Collect links for all months
        
        Returns summary statistics
        """
        months = self._generate_months()
        
        logger.info("="*80)
        logger.info("HISTORICAL SOLD PROPERTIES LINK COLLECTION")
        logger.info("="*80)
        logger.info(f"Period: {self.start_year}-{self.start_month:02d} to {self.end_year}-{self.end_month:02d}")
        logger.info(f"Months to scrape: {len(months)}")
        logger.info(f"Already completed: {len(self.completed_months)}")
        logger.info(f"Output directory: {self.output_dir}")
        logger.info(f"Headless mode: {self.headless}")
        logger.info("="*80)
        
        if not months:
            logger.info("✅ All months already scraped! Nothing to do.")
            return self._generate_summary()
        
        # Ask for confirmation
        if not self.headless:
            response = input(f"\nReady to scrape {len(months)} months? (y/n): ")
            if response.lower() != 'y':
                logger.info("Cancelled by user")
                return {}
        
        # Statistics
        total_links = 0
        total_pages = 0
        failed_months = []
        
        start_time = datetime.now()
        
        # Scrape each month
        for i, (year, month) in enumerate(months, 1):
            month_str = f"{year}-{month:02d}"
            
            logger.info("\n" + "="*80)
            logger.info(f"MONTH {i}/{len(months)}: {month_str}")
            logger.info("="*80)
            
            try:
                # Create scraper
                scraper = SoldPropertiesScraper(
                    headless=self.headless,
                    slow_mo=100 if not self.headless else 0
                )
                
                # Scrape month
                properties = scraper.scrape_month(
                    year=year,
                    month=month,
                    location_id=self.location_id,
                    max_pages=max_pages_per_month
                )
                
                # Save to CSV
                output_file = self.output_dir / f"sold_links_{year}{month:02d}.csv"
                scraper.save_to_csv(properties, output_file)
                
                # Update statistics
                total_links += len(properties)
                
                # Mark as complete
                self._save_progress(month_str)
                
                # Calculate ETA
                elapsed = (datetime.now() - start_time).total_seconds()
                avg_time_per_month = elapsed / i
                remaining_months = len(months) - i
                eta_seconds = remaining_months * avg_time_per_month
                eta = timedelta(seconds=int(eta_seconds))
                
                logger.info(f"✅ Completed {month_str}: {len(properties)} links")
                logger.info(f"Progress: {i}/{len(months)} months ({i/len(months)*100:.1f}%)")
                logger.info(f"Total links collected: {total_links}")
                logger.info(f"Average time per month: {avg_time_per_month/60:.1f} minutes")
                logger.info(f"ETA: {eta}")
                
            except Exception as e:
                logger.error(f"❌ Failed to scrape {month_str}: {e}")
                failed_months.append((month_str, str(e)))
                continue
        
        # Final summary
        elapsed_total = datetime.now() - start_time
        
        logger.info("\n" + "="*80)
        logger.info("BACKFILL COMPLETE!")
        logger.info("="*80)
        logger.info(f"Total months scraped: {len(months) - len(failed_months)}/{len(months)}")
        logger.info(f"Total links collected: {total_links}")
        logger.info(f"Total time: {elapsed_total}")
        logger.info(f"Average time per month: {elapsed_total.total_seconds()/len(months)/60:.1f} minutes")
        
        if failed_months:
            logger.warning(f"\n⚠️  {len(failed_months)} months failed:")
            for month_str, error in failed_months:
                logger.warning(f"  - {month_str}: {error}")
        
        return self._generate_summary()
    
    def _generate_summary(self) -> Dict:
        """Generate summary of collected links"""
        csv_files = sorted(self.output_dir.glob("sold_links_*.csv"))
        
        total_links = 0
        months_data = []
        
        for csv_file in csv_files:
            with open(csv_file, 'r') as f:
                reader = csv.DictReader(f)
                count = sum(1 for _ in reader)
                total_links += count
                
                # Extract month from filename
                month_str = csv_file.stem.replace('sold_links_', '')
                months_data.append({
                    'month': month_str,
                    'count': count,
                    'file': str(csv_file)
                })
        
        summary = {
            'total_months': len(csv_files),
            'total_links': total_links,
            'months': months_data,
            'output_dir': str(self.output_dir)
        }
        
        # Save summary
        summary_file = self.output_dir / "backfill_summary.json"
        with open(summary_file, 'w') as f:
            json.dump(summary, f, indent=2)
        
        logger.info(f"\n📊 Summary saved to: {summary_file}")
        
        return summary


def main():
    parser = argparse.ArgumentParser(
        description='Collect sold property links for historical backfill',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Scrape all months since 2020
  python scripts/backfill_sold_links.py
  
  # Scrape specific date range
  python scripts/backfill_sold_links.py --start 2023-01 --end 2024-12
  
  # Resume interrupted scrape (uses progress file)
  python scripts/backfill_sold_links.py
  
  # Test mode: scrape just 3 months
  python scripts/backfill_sold_links.py --test
  
  # Headless mode for server
  python scripts/backfill_sold_links.py --headless
        """
    )
    
    parser.add_argument(
        '--start',
        type=str,
        default='2020-01',
        help='Start month (YYYY-MM), default: 2020-01'
    )
    
    parser.add_argument(
        '--end',
        type=str,
        default=None,
        help='End month (YYYY-MM), default: current month'
    )
    
    parser.add_argument(
        '--location-id',
        type=str,
        default='17989',
        help='Hemnet location ID (default: 17989 for Malmö)'
    )
    
    parser.add_argument(
        '--output-dir',
        type=str,
        default='data/raw/sold_links',
        help='Output directory for link CSVs'
    )
    
    parser.add_argument(
        '--max-pages',
        type=int,
        default=50,
        help='Max pages per month (default: 50)'
    )
    
    parser.add_argument(
        '--headless',
        action='store_true',
        help='Run in headless mode'
    )
    
    parser.add_argument(
        '--test',
        action='store_true',
        help='Test mode: scrape only 3 months'
    )
    
    args = parser.parse_args()
    
    # Parse start date
    start_year, start_month = map(int, args.start.split('-'))
    
    # Parse end date
    if args.end:
        end_year, end_month = map(int, args.end.split('-'))
    else:
        now = datetime.now()
        end_year, end_month = now.year, now.month
    
    # Test mode: only 3 months
    if args.test:
        logger.info("🧪 TEST MODE: Scraping only 3 months")
        end_year = start_year
        end_month = min(start_month + 2, 12)
    
    # Create collector
    collector = HistoricalLinkCollector(
        start_year=start_year,
        start_month=start_month,
        end_year=end_year,
        end_month=end_month,
        location_id=args.location_id,
        output_dir=Path(args.output_dir),
        headless=args.headless
    )
    
    # Run collection
    try:
        summary = collector.collect_all(max_pages_per_month=args.max_pages)
        
        if summary:
            logger.info("\n" + "="*80)
            logger.info("📊 FINAL SUMMARY")
            logger.info("="*80)
            logger.info(f"Total months: {summary['total_months']}")
            logger.info(f"Total links: {summary['total_links']}")
            logger.info(f"Output: {summary['output_dir']}")
            logger.info("\n✅ Ready to scrape full property details tomorrow!")
        
    except KeyboardInterrupt:
        logger.warning("\n⚠️  Interrupted by user")
        logger.info("Progress saved! Run again to resume.")
    except Exception as e:
        logger.error(f"❌ Error: {e}")
        raise


if __name__ == "__main__":
    main()
