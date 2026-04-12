"""
Test scraper on a random sample of properties.
Useful for validating scraper behavior and analyzing field extraction rates.
"""

import csv
import json
import random
import logging
from pathlib import Path
from datetime import datetime
from typing import List, Dict
import sys

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.scrapers.property_detail_scraper import PropertyScraper
from src.models.property_schema import SoldProperty, ForSaleProperty

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def read_urls_from_csv(csv_path: Path, sample_size: int = 15) -> List[Dict]:
    """Read URLs from CSV and return random sample."""
    urls = []
    with open(csv_path, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        urls = list(reader)
    
    # Sample randomly
    sample = random.sample(urls, min(sample_size, len(urls)))
    logger.info(f"Selected {len(sample)} random URLs from {len(urls)} total")
    return sample


def analyze_results(results: List[Dict]) -> Dict:
    """Analyze scraping results and compute statistics."""
    total = len(results)
    successful = [r for r in results if r['success']]
    failed = [r for r in results if not r['success']]
    
    stats = {
        'total': total,
        'successful': len(successful),
        'failed': len(failed),
        'success_rate': len(successful) / total * 100 if total > 0 else 0,
        'field_presence': {},
        'property_types': {},
        'errors': {}
    }
    
    # Analyze field presence rates
    if successful:
        # Get all possible fields from first successful property
        sample_prop = successful[0]['data']
        fields = sample_prop.keys()
        
        for field in fields:
            present = sum(1 for r in successful if r['data'].get(field) is not None)
            stats['field_presence'][field] = {
                'count': present,
                'rate': present / len(successful) * 100
            }
        
        # Property type distribution
        for r in successful:
            prop_type = r['data'].get('property_type', 'unknown')
            stats['property_types'][prop_type] = stats['property_types'].get(prop_type, 0) + 1
    
    # Error distribution
    for r in failed:
        error = r.get('error', 'Unknown error')
        stats['errors'][error] = stats['errors'].get(error, 0) + 1
    
    return stats


def print_analysis(stats: Dict):
    """Pretty print analysis results."""
    print("\n" + "="*70)
    print("SCRAPING TEST RESULTS")
    print("="*70)
    
    print(f"\nOverall Statistics:")
    print(f"  Total Properties: {stats['total']}")
    print(f"  Successful: {stats['successful']} ({stats['success_rate']:.1f}%)")
    print(f"  Failed: {stats['failed']}")
    
    if stats['property_types']:
        print(f"\nProperty Type Distribution:")
        for prop_type, count in stats['property_types'].items():
            print(f"  {prop_type}: {count}")
    
    if stats['field_presence']:
        print(f"\nField Presence Rates (successful properties only):")
        
        # Group by presence rate
        always_present = []
        usually_present = []
        sometimes_present = []
        rarely_present = []
        
        for field, data in sorted(stats['field_presence'].items(), key=lambda x: x[1]['rate'], reverse=True):
            rate = data['rate']
            count = data['count']
            total = stats['successful']
            
            if rate == 100:
                always_present.append((field, count, total))
            elif rate >= 80:
                usually_present.append((field, count, total, rate))
            elif rate >= 30:
                sometimes_present.append((field, count, total, rate))
            else:
                rarely_present.append((field, count, total, rate))
        
        if always_present:
            print(f"\n  ✅ Always Present (100%):")
            for field, count, total in always_present:
                print(f"     • {field}: {count}/{total}")
        
        if usually_present:
            print(f"\n  ✓ Usually Present (80-99%):")
            for field, count, total, rate in usually_present:
                print(f"     • {field}: {count}/{total} ({rate:.1f}%)")
        
        if sometimes_present:
            print(f"\n  ⚠ Sometimes Present (30-79%):")
            for field, count, total, rate in sometimes_present:
                print(f"     • {field}: {count}/{total} ({rate:.1f}%)")
        
        if rarely_present:
            print(f"\n  ✗ Rarely Present (<30%):")
            for field, count, total, rate in rarely_present:
                print(f"     • {field}: {count}/{total} ({rate:.1f}%)")
    
    if stats['errors']:
        print(f"\nError Distribution:")
        for error, count in stats['errors'].items():
            print(f"  • {error}: {count}")
    
    print("\n" + "="*70)


def test_scraper_sample(
    input_csv: Path,
    output_dir: Path,
    sample_size: int = 15,
    headless: bool = True
):
    """
    Test scraper on random sample of properties.
    
    Args:
        input_csv: Path to CSV file with URLs
        output_dir: Directory to save results
        sample_size: Number of properties to test
        headless: Whether to run browser in headless mode
    """
    # Create output directory
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Generate timestamp for this run
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    # Read sample URLs
    logger.info(f"Reading URLs from {input_csv}")
    sample_urls = read_urls_from_csv(input_csv, sample_size)
    
    # Initialize scraper
    logger.info("Initializing scraper...")
    scraper = PropertyScraper(headless=headless)
    
    # Scrape properties
    results = []
    logger.info(f"\n{'='*70}")
    logger.info(f"Starting scraping test: {sample_size} properties")
    logger.info(f"{'='*70}\n")
    
    for i, record in enumerate(sample_urls, 1):
        url = record['url']
        property_id = record.get('property_id', 'unknown')
        
        logger.info(f"[{i}/{sample_size}] Testing: {property_id}")
        logger.info(f"  URL: {url}")
        
        try:
            property_data = scraper.scrape_property(url)
            
            if property_data:
                # Convert to dict
                data_dict = property_data.model_dump()
                
                result = {
                    'url': url,
                    'property_id': property_id,
                    'success': True,
                    'data': data_dict,
                    'timestamp': datetime.now().isoformat()
                }
                
                logger.info(f"  ✅ Success")
                logger.info(f"     Address: {property_data.address}")
                logger.info(f"     Type: {property_data.property_type}")
                
                if isinstance(property_data, SoldProperty):
                    logger.info(f"     Final Price: {property_data.final_price:,} SEK" if property_data.final_price else "     Final Price: N/A")
                else:
                    logger.info(f"     Asking Price: {property_data.asking_price:,} SEK" if property_data.asking_price else "     Asking Price: N/A")
            else:
                result = {
                    'url': url,
                    'property_id': property_id,
                    'success': False,
                    'error': 'No data returned',
                    'timestamp': datetime.now().isoformat()
                }
                logger.error(f"  ❌ Failed: No data returned")
        
        except Exception as e:
            result = {
                'url': url,
                'property_id': property_id,
                'success': False,
                'error': str(e),
                'timestamp': datetime.now().isoformat()
            }
            logger.error(f"  ❌ Failed: {e}")
        
        results.append(result)
        logger.info("")
    
    # Save results
    results_file = output_dir / f"test_results_{timestamp}.json"
    with open(results_file, 'w', encoding='utf-8') as f:
        json.dump(results, f, indent=2, ensure_ascii=False, default=str)
    
    logger.info(f"✓ Saved results to {results_file}")
    
    # Analyze results
    stats = analyze_results(results)
    
    # Save statistics
    stats_file = output_dir / f"test_stats_{timestamp}.json"
    with open(stats_file, 'w', encoding='utf-8') as f:
        json.dump(stats, f, indent=2, default=str)
    
    logger.info(f"✓ Saved statistics to {stats_file}")
    
    # Print analysis
    print_analysis(stats)
    
    return results, stats


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Test scraper on random property sample")
    parser.add_argument(
        "--input",
        required=True,
        help="Input CSV file with URLs"
    )
    parser.add_argument(
        "--output",
        default="data/test_results",
        help="Output directory for results (default: data/test_results)"
    )
    parser.add_argument(
        "--sample-size",
        type=int,
        default=15,
        help="Number of properties to test (default: 15)"
    )
    parser.add_argument(
        "--no-headless",
        action="store_true",
        help="Show browser window"
    )
    
    args = parser.parse_args()
    
    test_scraper_sample(
        input_csv=Path(args.input),
        output_dir=Path(args.output),
        sample_size=args.sample_size,
        headless=not args.no_headless
    )
