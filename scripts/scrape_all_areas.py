"""
Adaptive Area Range Scraper for Hemnet
Automatically iterates through all living area ranges, adapting step size to avoid 2,500 result limit
"""

import argparse
import json
import logging
import sys
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Tuple

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.scrapers.sold_properties_scraper import SoldPropertiesScraper

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class AdaptiveAreaScraper:
    """Scrapes all properties by adaptively partitioning living area ranges"""
    
    RESULT_LIMIT = 2500
    SAFE_LIMIT = 2400  # Stay under limit with margin
    MIN_STEP = 5  # Minimum step size in m²
    MAX_AREA = 500  # Maximum reasonable apartment size
    
    def __init__(self, location_id: str = "17989", headless: bool = True, output_dir: Path = None):
        self.location_id = location_id
        self.scraper = SoldPropertiesScraper(headless=headless, slow_mo=0 if headless else 100)
        self.output_dir = output_dir or Path("data/raw/area_ranges")
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        # Progress tracking
        self.progress_file = self.output_dir / "progress.json"
        self.progress = self._load_progress()
        
    def _load_progress(self) -> Dict:
        """Load scraping progress from file"""
        if self.progress_file.exists():
            with open(self.progress_file, 'r') as f:
                return json.load(f)
        return {
            'completed_ranges': [],
            'total_properties': 0,
            'started_at': datetime.now().isoformat()
        }
    
    def _save_progress(self):
        """Save current progress to file"""
        with open(self.progress_file, 'w') as f:
            json.dump(self.progress, f, indent=2)
    
    def _is_range_completed(self, area_min: int, area_max: int) -> bool:
        """Check if a range has already been scraped"""
        range_key = f"{area_min}-{area_max}"
        return range_key in self.progress['completed_ranges']
    
    def _mark_range_completed(self, area_min: int, area_max: int, property_count: int):
        """Mark a range as completed"""
        range_key = f"{area_min}-{area_max}"
        self.progress['completed_ranges'].append(range_key)
        self.progress['total_properties'] += property_count
        self._save_progress()
    
    def find_optimal_range(self, min_area: int, initial_max: int) -> Tuple[int, int]:
        """
        Find optimal area range that stays under result limit
        Uses binary search to find largest range under SAFE_LIMIT
        """
        
        low = min_area + self.MIN_STEP
        high = min(initial_max, self.MAX_AREA)
        best_max = low
        
        logger.info(f"Finding optimal range starting from {min_area}m²...")
        
        while low <= high:
            mid = (low + high) // 2
            
            # Check result count
            count = self.scraper.get_total_results_count(
                location_id=self.location_id,
                area_min=min_area,
                area_max=mid
            )
            
            logger.info(f"  Testing {min_area}-{mid}m²: {count} results")
            
            if count == 0:
                # No results, we've gone too far
                high = mid - 1
            elif count >= self.SAFE_LIMIT:
                # Too many results, reduce range
                high = mid - 1
            else:
                # Good range, try to expand
                best_max = mid
                low = mid + 1
        
        logger.info(f"✅ Optimal range: {min_area}-{best_max}m² ({count} results)")
        return min_area, best_max
    
    def scrape_range(self, area_min: int, area_max: int, max_pages: int = 50) -> List[Dict]:
        """Scrape a single area range"""
        
        # Check if already completed
        if self._is_range_completed(area_min, area_max):
            logger.info(f"⏭️  Range {area_min}-{area_max}m² already completed, skipping")
            return []
        
        logger.info(f"🔍 Scraping range {area_min}-{area_max}m²")
        
        try:
            properties = self.scraper.scrape_area_range(
                area_min=area_min,
                area_max=area_max,
                location_id=self.location_id,
                max_pages=max_pages
            )
            
            # Save this range's data
            output_file = self.output_dir / f"properties_{area_min}_{area_max}.csv"
            self.scraper.save_to_csv(properties, output_file)
            
            # Mark as completed
            self._mark_range_completed(area_min, area_max, len(properties))
            
            logger.info(f"✅ Completed range {area_min}-{area_max}m²: {len(properties)} properties")
            return properties
            
        except Exception as e:
            logger.error(f"❌ Error scraping range {area_min}-{area_max}m²: {e}")
            raise
    
    def scrape_all(self, initial_step: int = 50, max_pages: int = 50, min_area: int = 0, max_area_limit: int = 500):
        """
        Scrape all properties by adaptively iterating through area ranges
        
        Args:
            initial_step: Initial step size for area ranges (m²)
            max_pages: Maximum pages to scrape per range
            min_area: Starting living area (m²)
            max_area_limit: Maximum living area to scrape up to (m²)
        """
        
        logger.info("🚀 Starting adaptive area scraping")
        logger.info(f"Location ID: {self.location_id}")
        logger.info(f"Output directory: {self.output_dir}")
        logger.info(f"Initial step size: {initial_step}m²")
        logger.info(f"Area range: {min_area}-{max_area_limit}m²")
        
        min_area_current = min_area
        all_properties = []
        
        while min_area_current < max_area_limit:
            # Calculate initial max for this iteration
            initial_max = min_area + initial_step
            
            # Find optimal range
            range_min, range_max = self.find_optimal_range(min_area, initial_max)
            
            # Handle edge case: can't make progress
            if range_max <= range_min:
                logger.warning(f"⚠️ Cannot make progress from {min_area}m². Skipping to next step.")
                min_area += self.MIN_STEP
                continue
            
            # Scrape this range
            properties = self.scrape_range(range_min, range_max, max_pages)
            all_properties.extend(properties)
            
            # Move to next range
            min_area = range_max
            
            # Log overall progress
            logger.info(f"📊 Overall progress: {len(all_properties)} properties collected")
            logger.info(f"📈 Next range starts at {min_area}m²")
        
        logger.info(f"🎉 Scraping completed!")
        logger.info(f"📊 Total unique properties: {len(set(p['property_id'] for p in all_properties))}")
        
        return all_properties
    
    def consolidate_results(self, output_file: Path = None):
        """Consolidate all range CSV files into single file with deduplication"""
        
        output_file = output_file or Path("data/raw/sold_properties_all_areas.csv")
        
        logger.info("📦 Consolidating results from all ranges...")
        
        # Read all CSV files
        all_properties = {}
        csv_files = sorted(self.output_dir.glob("properties_*.csv"))
        
        import csv
        for csv_file in csv_files:
            logger.info(f"  Reading {csv_file.name}")
            with open(csv_file, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    prop_id = row['property_id']
                    # Keep first occurrence (most complete data)
                    if prop_id not in all_properties:
                        all_properties[prop_id] = row
        
        # Write consolidated file
        logger.info(f"✅ Writing {len(all_properties)} unique properties to {output_file}")
        
        properties_list = list(all_properties.values())
        self.scraper.save_to_csv(properties_list, output_file)
        
        logger.info(f"🎉 Consolidation complete!")
        return properties_list


def main():
    parser = argparse.ArgumentParser(
        description='Scrape all sold properties using adaptive area filtering'
    )
    parser.add_argument('--location-id', type=str, default='17989',
                       help='Hemnet location ID (default: 17989 for Malmö)')
    parser.add_argument('--initial-step', type=int, default=50,
                       help='Initial step size in m² (default: 50)')
    parser.add_argument('--max-pages', type=int, default=50,
                       help='Maximum pages per range (default: 50)')
    parser.add_argument('--min-area', type=int, default=0,
                       help='Starting living area in m² (default: 0)')
    parser.add_argument('--max-area', type=int, default=500,
                       help='Ending living area in m² (default: 500)')
    parser.add_argument('--output-dir', type=str,
                       help='Output directory for range files')
    parser.add_argument('--headless', action='store_true',
                       help='Run in headless mode (recommended for production)')
    parser.add_argument('--consolidate-only', action='store_true',
                       help='Only consolidate existing results, do not scrape')
    
    args = parser.parse_args()
    
    # Setup
    output_dir = Path(args.output_dir) if args.output_dir else Path("data/raw/area_ranges")
    
    scraper = AdaptiveAreaScraper(
        location_id=args.location_id,
        headless=args.headless,
        output_dir=output_dir
    )
    
    if args.consolidate_only:
        # Just consolidate existing results
        scraper.consolidate_results()
    else:
        # Run full scrape
        try:
            scraper.scrape_all(
                initial_step=args.initial_step,
                max_pages=args.max_pages,
                min_area=args.min_area,
                max_area_limit=args.max_area
            )
            
            # Consolidate results
            scraper.consolidate_results()
            
        except KeyboardInterrupt:
            logger.info("⏸️  Scraping interrupted by user")
            logger.info("Progress has been saved. Run again to resume.")
        except Exception as e:
            logger.error(f"❌ Scraping failed: {e}")
            raise


if __name__ == "__main__":
    main()
