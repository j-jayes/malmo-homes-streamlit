"""
Integration test for property scraper.

Tests the scraper on real properties (both sold and active listings)
to validate all field extraction and measure performance.
"""

import json
import time
from pathlib import Path
from datetime import datetime
import sys

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.scrapers.property_detail_scraper import PropertyScraper


def test_property(scraper: PropertyScraper, url: str, expected_type: str) -> dict:
    """
    Test scraping a single property.
    
    Args:
        scraper: PropertyScraper instance
        url: Property URL
        expected_type: Expected property type ('sold' or 'for_sale')
        
    Returns:
        Dict with test results
    """
    start_time = time.time()
    
    try:
        result = scraper.scrape_property(url)
        elapsed = time.time() - start_time
        
        if not result:
            return {
                'url': url,
                'success': False,
                'error': 'Scraper returned None',
                'elapsed_seconds': elapsed
            }
        
        # Convert to dict for JSON serialization
        data = result.model_dump()
        
        # Check field completeness
        fields_present = sum(1 for v in data.values() if v is not None)
        total_fields = len(data)
        
        return {
            'url': url,
            'success': True,
            'property_type': result.property_type,
            'expected_type': expected_type,
            'type_match': result.property_type == expected_type,
            'elapsed_seconds': elapsed,
            'fields_present': fields_present,
            'total_fields': total_fields,
            'completeness_pct': (fields_present / total_fields) * 100,
            'data': data
        }
        
    except Exception as e:
        elapsed = time.time() - start_time
        return {
            'url': url,
            'success': False,
            'error': str(e),
            'elapsed_seconds': elapsed
        }


def analyze_results(results: list[dict]) -> dict:
    """Analyze test results and generate statistics."""
    total = len(results)
    successful = sum(1 for r in results if r['success'])
    failed = total - successful
    
    if successful == 0:
        return {
            'total': total,
            'successful': 0,
            'failed': failed,
            'success_rate': 0.0
        }
    
    successful_results = [r for r in results if r['success']]
    
    # Time statistics
    times = [r['elapsed_seconds'] for r in successful_results]
    avg_time = sum(times) / len(times)
    min_time = min(times)
    max_time = max(times)
    
    # Completeness statistics
    completeness = [r['completeness_pct'] for r in successful_results]
    avg_completeness = sum(completeness) / len(completeness)
    
    # Type matching
    type_matches = sum(1 for r in successful_results if r.get('type_match', False))
    
    # Field analysis - count how many properties have each field
    field_counts = {}
    for result in successful_results:
        for field, value in result['data'].items():
            if field not in field_counts:
                field_counts[field] = 0
            if value is not None:
                field_counts[field] += 1
    
    # Calculate field presence percentages
    field_presence = {
        field: (count / successful * 100) 
        for field, count in sorted(field_counts.items(), key=lambda x: x[1], reverse=True)
    }
    
    return {
        'total': total,
        'successful': successful,
        'failed': failed,
        'success_rate': (successful / total) * 100,
        'type_matches': type_matches,
        'type_match_rate': (type_matches / successful) * 100 if successful > 0 else 0,
        'avg_time_seconds': avg_time,
        'min_time_seconds': min_time,
        'max_time_seconds': max_time,
        'total_time_seconds': sum(times),
        'avg_completeness_pct': avg_completeness,
        'field_presence': field_presence
    }


def print_results(results: list[dict], stats: dict):
    """Print formatted test results."""
    print('\n' + '=' * 80)
    print('INTEGRATION TEST RESULTS')
    print('=' * 80)
    
    # Summary
    print(f'\nOverall: {stats["successful"]}/{stats["total"]} successful ({stats["success_rate"]:.1f}%)')
    print(f'Type Detection: {stats["type_matches"]}/{stats["successful"]} correct ({stats["type_match_rate"]:.1f}%)')
    print(f'Average Completeness: {stats["avg_completeness_pct"]:.1f}%')
    print(f'Total Time: {stats["total_time_seconds"]:.1f}s')
    print(f'Average Time: {stats["avg_time_seconds"]:.1f}s (min: {stats["min_time_seconds"]:.1f}s, max: {stats["max_time_seconds"]:.1f}s)')
    
    # Field presence
    print(f'\n{"Field":<30} {"Presence":>10}')
    print('-' * 42)
    for field, pct in stats['field_presence'].items():
        status = '✅' if pct == 100 else '⚠️' if pct >= 80 else '❌'
        print(f'{status} {field:<27} {pct:>6.1f}%')
    
    # Individual results
    print('\n' + '=' * 80)
    print('INDIVIDUAL PROPERTY RESULTS')
    print('=' * 80)
    
    for i, result in enumerate(results, 1):
        url_short = result['url'].split('/')[-1][:50]
        
        if result['success']:
            data = result['data']
            type_marker = '✅' if result.get('type_match', False) else '❌'
            print(f'\n[{i}] {type_marker} {url_short}')
            print(f'    Type: {result["property_type"]} (expected: {result["expected_type"]})')
            print(f'    Time: {result["elapsed_seconds"]:.1f}s')
            print(f'    Completeness: {result["completeness_pct"]:.1f}% ({result["fields_present"]}/{result["total_fields"]} fields)')
            print(f'    Address: {data.get("address")}')
            print(f'    City: {data.get("city")}, Neighborhood: {data.get("neighborhood")}')
            print(f'    Floor: {data.get("floor")}, Building Year: {data.get("building_year")}')
            if result["property_type"] == "sold":
                final_price = data.get("final_price")
                visit_count = data.get("visit_count")
                print(f'    Price: {final_price:,} SEK' if final_price else '    Price: N/A')
                print(f'    Visits: {visit_count}' if visit_count else '    Visits: N/A', end='')
            else:
                asking_price = data.get("asking_price")
                print(f'    Asking Price: {asking_price:,} SEK' if asking_price else '    Asking Price: N/A', end='')
        else:
            print(f'\n[{i}] ❌ {url_short}')
            print(f'    Error: {result["error"]}')
            print(f'    Time: {result["elapsed_seconds"]:.1f}s')


def save_results(results: list[dict], stats: dict, output_dir: Path):
    """Save test results to JSON files."""
    output_dir.mkdir(parents=True, exist_ok=True)
    
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    
    # Save full results
    results_file = output_dir / f'integration_test_{timestamp}.json'
    with open(results_file, 'w', encoding='utf-8') as f:
        json.dump(results, f, indent=2, ensure_ascii=False, default=str)
    
    # Save statistics
    stats_file = output_dir / f'integration_stats_{timestamp}.json'
    with open(stats_file, 'w', encoding='utf-8') as f:
        json.dump(stats, f, indent=2, ensure_ascii=False)
    
    print(f'\n✓ Saved results to {results_file}')
    print(f'✓ Saved statistics to {stats_file}')


def main():
    """Main execution."""
    import argparse
    
    parser = argparse.ArgumentParser(description='Integration test for property scraper')
    parser.add_argument('--output-dir', type=str, default='data/test_results', help='Output directory')
    parser.add_argument('--sold-count', type=int, default=10, help='Number of sold properties to test')
    parser.add_argument('--active-count', type=int, default=10, help='Number of active properties to test')
    
    args = parser.parse_args()
    
    # Test URLs - mix of Malmö and other locations
    sold_urls = [
        # Malmö properties
        'https://www.hemnet.se/salda/lagenhet-2,5rum-folkets-park-malmo-kommun-trelleborgsgatan-8a-8937784767841466942',
        'https://www.hemnet.se/salda/lagenhet-2rum-limhamn-malmo-kommun-vasagatan-16a-4854127945408044649',
        'https://www.hemnet.se/salda/lagenhet-3rum-hogaholm-malmo-kommun-balladgatan-49-4637183799182047208',
        'https://www.hemnet.se/salda/lagenhet-2rum-rorsjostaden-malmo-kommun-lojtnantsgatan-12b-9156284561016495254',
        'https://www.hemnet.se/salda/lagenhet-1rum-folkets-park-malmo-kommun-kristianstadsgatan-25a-5454721957521815189',
        'https://www.hemnet.se/salda/lagenhet-2rum-rosengard-malmo-kommun-gitarrvagen-31-7863437734664651166',
        'https://www.hemnet.se/salda/lagenhet-2rum-kirseberg-malmo-kommun-fersens-vag-28-5726413193012837084',
        'https://www.hemnet.se/salda/lagenhet-2rum-vastra-hamnen-malmo-kommun-fredrikshamnsleden-61-3877950736862302868',
        # Hörby properties (smaller town)
        'https://www.hemnet.se/salda/lagenhet-2rum-centralt-horby-kommun-nygatan-49a-6408029372512178039',
        'https://www.hemnet.se/salda/lagenhet-5rum-horby-horby-kommun-johannagatan-38b-7608095938618044583',
    ][:args.sold_count]
    
    active_urls = [
        # Active listings - these will need to be current URLs
        'https://www.hemnet.se/bostad/lagenhet-2rum-slottsstaden-malmo-kommun-ostra-stallmastaregatan-5b-21629409',
        'https://www.hemnet.se/bostad/lagenhet-3rum-vastra-hamnen-malmo-kommun-varvsgatan-45-21684049',
        'https://www.hemnet.se/bostad/lagenhet-2rum-rosengard-malmo-kommun-persborg-21-21597921',
        'https://www.hemnet.se/bostad/lagenhet-1rum-mollevangen-malmo-kommun-kulladalsgatan-14-21681401',
        'https://www.hemnet.se/bostad/lagenhet-2rum-limhamn-malmo-kommun-kalkbrottsgatan-7-21665977',
        'https://www.hemnet.se/bostad/lagenhet-2rum-sodra-innerstaden-malmo-kommun-carl-gustafs-vag-42-21683821',
        'https://www.hemnet.se/bostad/lagenhet-3rum-kirseberg-malmo-kommun-kaptensgatan-10-21668633',
        'https://www.hemnet.se/bostad/lagenhet-4rum-oxie-malmo-kommun-storgatan-34-21643329',
        'https://www.hemnet.se/bostad/lagenhet-2rum-centrum-malmo-kommun-sodra-forstadsgatan-78-21667025',
        'https://www.hemnet.se/bostad/lagenhet-3rum-mollevangen-malmo-kommun-nobelstigen-15-21641185',
    ][:args.active_count]
    
    print('=' * 80)
    print('PROPERTY SCRAPER INTEGRATION TEST')
    print('=' * 80)
    print(f'\nTesting {len(sold_urls)} sold + {len(active_urls)} active = {len(sold_urls) + len(active_urls)} total properties')
    
    # Create scraper
    scraper = PropertyScraper(headless=True)
    
    # Test sold properties
    print('\n' + '-' * 80)
    print('Testing SOLD properties...')
    print('-' * 80)
    
    sold_results = []
    for i, url in enumerate(sold_urls, 1):
        print(f'\n[{i}/{len(sold_urls)}] {url.split("/")[-1][:60]}...')
        result = test_property(scraper, url, 'sold')
        sold_results.append(result)
        if result['success']:
            print(f'  ✅ Success in {result["elapsed_seconds"]:.1f}s')
        else:
            print(f'  ❌ Failed: {result["error"]}')
    
    # Test active properties
    print('\n' + '-' * 80)
    print('Testing ACTIVE properties...')
    print('-' * 80)
    
    active_results = []
    for i, url in enumerate(active_urls, 1):
        print(f'\n[{i}/{len(active_urls)}] {url.split("/")[-1][:60]}...')
        result = test_property(scraper, url, 'for_sale')
        active_results.append(result)
        if result['success']:
            print(f'  ✅ Success in {result["elapsed_seconds"]:.1f}s')
        else:
            print(f'  ❌ Failed: {result["error"]}')
    
    # Combine results
    all_results = sold_results + active_results
    
    # Analyze
    stats = analyze_results(all_results)
    
    # Print results
    print_results(all_results, stats)
    
    # Save results
    save_results(all_results, stats, Path(args.output_dir))
    
    # Return exit code based on success rate
    if stats['success_rate'] >= 95:
        print('\n✅ Integration test PASSED (≥95% success rate)')
        return 0
    elif stats['success_rate'] >= 80:
        print('\n⚠️ Integration test PARTIAL (80-95% success rate)')
        return 0
    else:
        print('\n❌ Integration test FAILED (<80% success rate)')
        return 1


if __name__ == '__main__':
    sys.exit(main())
