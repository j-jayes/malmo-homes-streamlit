"""
Analyze district structure across different properties to understand location data patterns.

This script samples properties and extracts their location/district information
to help design robust city/neighborhood extraction logic.

Uses the existing PropertyScraper which has Cloudflare bypass built-in.
"""

import json
from pathlib import Path
import sys

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.scrapers.property_detail_scraper import PropertyScraper
from playwright.sync_api import sync_playwright


def analyze_property_location(url: str, scraper: PropertyScraper) -> dict:
    """
    Extract location data from a single property by scraping.
    
    Args:
        url: Property URL
        scraper: PropertyScraper instance
        
    Returns:
        Dict with location analysis
    """
    try:
        # Scrape the property
        property_model = scraper.scrape_property(url)
        
        if not property_model:
            return None
        
        # Now we need to get the raw Apollo State to analyze districts
        # Re-fetch to get Apollo State
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            context = browser.new_context(
                user_agent='Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36',
                viewport={'width': 1920, 'height': 1080}
            )
            page = context.new_page()
            
            page.goto(url, wait_until='domcontentloaded', timeout=60000)
            page.wait_for_timeout(5000)
            
            # Extract Apollo State
            result = scraper._extract_next_data(page)
            if not result:
                browser.close()
                return None
            
            property_data, apollo_state = result
            
            # Extract location information
            location_info = {
                'url': url,
                'address': property_data.get('streetAddress'),
                'area': property_data.get('area'),
                'locationName': property_data.get('locationName'),
                'districts': [],
                'municipality': None,
                'county': None,
                # Also include what we extracted
                'extracted_city': property_model.city,
                'extracted_neighborhood': property_model.neighborhood
            }
            
            # Get district names by following references
            districts = property_data.get('districts', [])
            for district_ref in districts:
                if isinstance(district_ref, dict) and '__ref' in district_ref:
                    ref_key = district_ref['__ref']
                    if ref_key in apollo_state:
                        district_obj = apollo_state[ref_key]
                        district_name = district_obj.get('fullName')
                        if district_name:
                            location_info['districts'].append(district_name)
            
            # Get municipality
            municipality_ref = property_data.get('municipality', {})
            if isinstance(municipality_ref, dict) and '__ref' in municipality_ref:
                ref_key = municipality_ref['__ref']
                if ref_key in apollo_state:
                    muni_obj = apollo_state[ref_key]
                    location_info['municipality'] = muni_obj.get('fullName')
            
            # Get county
            county_ref = property_data.get('county', {})
            if isinstance(county_ref, dict) and '__ref' in county_ref:
                ref_key = county_ref['__ref']
                if ref_key in apollo_state:
                    county_obj = apollo_state[ref_key]
                    location_info['county'] = county_obj.get('fullName')
            
            browser.close()
            return location_info
            
    except Exception as e:
        print(f'  ❌ Error: {str(e)[:100]}')
        return None


def print_analysis(results: list[dict]):
    """Print formatted analysis of district structures."""
    print('\n' + '=' * 80)
    print('DISTRICT STRUCTURE ANALYSIS')
    print('=' * 80)
    
    for i, result in enumerate(results, 1):
        print(f'\n[Property {i}]')
        print(f'Address: {result["address"]}')
        print(f'Area field: {result["area"]}')
        print(f'LocationName: {result["locationName"]}')
        print(f'Municipality: {result["municipality"]}')
        print(f'County: {result["county"]}')
        print(f'>>> EXTRACTED: City={result["extracted_city"]}, Neighborhood={result["extracted_neighborhood"]}')
        print(f'Districts ({len(result["districts"])}):')
        for j, district in enumerate(result['districts'], 1):
            print(f'  {j}. {district}')
    
    # Summary analysis
    print('\n' + '=' * 80)
    print('SUMMARY PATTERNS')
    print('=' * 80)
    
    district_counts = [len(r['districts']) for r in results]
    print(f'\nDistrict counts: min={min(district_counts)}, max={max(district_counts)}, avg={sum(district_counts)/len(district_counts):.1f}')
    
    # Analyze what appears in districts
    print('\nLocation logic analysis:')
    for i, result in enumerate(results, 1):
        districts = result['districts']
        
        # Find likely city (shortest name without kommun/län/slashes)
        city_candidates = [d for d in districts 
                          if 'kommun' not in d.lower() 
                          and 'län' not in d.lower()
                          and d != result['area']]
        
        if city_candidates:
            # Sort by: no "/" first, then by length
            city_candidates.sort(key=lambda x: ('/' in x, len(x)))
            likely_city = city_candidates[0]
        else:
            likely_city = None
        
        print(f'  Property {i}:')
        print(f'    Neighborhood (area field): {result["area"]}')
        print(f'    Likely city: {likely_city}')
        print(f'    Municipality: {result["municipality"]}')


def save_results(results: list[dict], output_path: Path):
    """Save results to JSON file."""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(results, f, indent=2, ensure_ascii=False)
    print(f'\n✓ Saved results to {output_path}')


def main():
    """Main execution."""
    import argparse
    
    parser = argparse.ArgumentParser(description='Analyze district structure in Hemnet properties')
    parser.add_argument('--sample-size', type=int, default=10, help='Number of properties to analyze')
    parser.add_argument('--output', type=str, default='data/test_results/district_analysis.json', help='Output JSON file')
    
    args = parser.parse_args()
    
    # Read URLs from our test results
    test_results_path = Path('data/test_results/test_results_20251115_215033.json')
    
    if test_results_path.exists():
        print(f'Loading URLs from {test_results_path}')
        with open(test_results_path) as f:
            test_data = json.load(f)
        
        # Get URLs from successful test results
        urls = [item['url'] for item in test_data[:args.sample_size] if item.get('success')]
        print(f'Found {len(urls)} URLs to analyze\n')
    else:
        print('Test results not found, using example URLs')
        urls = [
            'https://www.hemnet.se/salda/lagenhet-2,5rum-folkets-park-malmo-kommun-trelleborgsgatan-8a-8937784767841466942',
            'https://www.hemnet.se/salda/lagenhet-2rum-limhamn-malmo-kommun-vasagatan-16a-4854127945408044649',
        ]
    
    # Create scraper
    scraper = PropertyScraper(headless=True)
    
    # Analyze properties
    results = []
    for i, url in enumerate(urls, 1):
        property_name = url.split('/')[-1][:50]
        print(f'[{i}/{len(urls)}] {property_name}...')
        
        result = analyze_property_location(url, scraper)
        if result:
            results.append(result)
            print(f'  ✓ Extracted location data')
        else:
            print(f'  ❌ Failed to extract data')
    
    if results:
        # Print analysis
        print_analysis(results)
        
        # Save results
        save_results(results, Path(args.output))
    else:
        print('\n❌ No results to analyze')


if __name__ == '__main__':
    main()
