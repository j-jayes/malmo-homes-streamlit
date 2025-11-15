"""
Hemnet Link Collector - Phase 1: Simple Link Collection
Extracts property listing URLs from Hemnet search results
Start simple: single page, then pagination, then smart filtering
"""

import json
import time
import logging
from playwright.sync_api import sync_playwright
from typing import List, Dict, Set
from datetime import datetime
import csv

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')


def extract_property_links_from_page(page) -> List[Dict[str, str]]:
    """
    Extract all property links from the current page.
    Returns list of dicts with URL and any metadata.
    """
    links = []
    
    # Wait for property listings to load
    try:
        page.wait_for_selector('a[href*="/bostad/"]', timeout=10000)
    except:
        logging.warning("Property links not found on page")
        return links
    
    # Find all property listing links
    # Hemnet uses links like /bostad/lagenhet-2rum-...
    property_elements = page.query_selector_all('a[href*="/bostad/"]')
    
    seen_urls = set()
    for element in property_elements:
        try:
            href = element.get_attribute('href')
            if href and href not in seen_urls:
                # Make sure it's a property listing, not other /bostad/ pages
                if '/bostad/' in href and not any(x in href for x in ['/bostader', '/sok', '/filter']):
                    full_url = f"https://www.hemnet.se{href}" if href.startswith('/') else href
                    
                    # Extract property ID from URL if possible
                    property_id = full_url.split('-')[-1] if '-' in full_url else None
                    
                    links.append({
                        'url': full_url,
                        'property_id': property_id,
                        'found_at': datetime.now().isoformat()
                    })
                    seen_urls.add(href)
        except Exception as e:
            logging.debug(f"Error extracting link: {e}")
    
    return links


def get_pagination_info(page) -> Dict:
    """
    Extract pagination information from the page.
    Returns total pages, current page, and total results if available.
    """
    info = {
        'current_page': 1,
        'total_pages': 1,
        'total_results': None
    }
    
    try:
        # Look for pagination elements
        # Hemnet typically shows "Sida X av Y" or similar
        pagination_text = page.inner_text('body')
        
        # Try to find current page number in URL
        current_url = page.url
        if 'page=' in current_url:
            page_param = current_url.split('page=')[1].split('&')[0]
            info['current_page'] = int(page_param)
        
        # Look for total results text
        # Common patterns: "Visar X objekt" or "X träffar"
        if 'objekt' in pagination_text or 'träffar' in pagination_text:
            # This is a rough extraction - might need refinement
            import re
            result_match = re.search(r'(\d+(?:\s?\d+)*)\s*(?:objekt|träffar)', pagination_text)
            if result_match:
                result_str = result_match.group(1).replace(' ', '')
                info['total_results'] = int(result_str)
                logging.info(f"Found {info['total_results']} total results")
        
        # Try to find last page number
        page_links = page.query_selector_all('a[href*="page="]')
        if page_links:
            max_page = 1
            for link in page_links:
                href = link.get_attribute('href')
                if href and 'page=' in href:
                    try:
                        page_num = int(href.split('page=')[1].split('&')[0])
                        max_page = max(max_page, page_num)
                    except:
                        pass
            info['total_pages'] = max_page
            logging.info(f"Found pagination: page {info['current_page']} of {info['total_pages']}")
    
    except Exception as e:
        logging.warning(f"Error extracting pagination info: {e}")
    
    return info


def scrape_search_page(url: str, headless: bool = False) -> Dict:
    """
    Scrape a single Hemnet search results page.
    Returns links and pagination info.
    """
    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=headless,
            args=['--disable-blink-features=AutomationControlled']
        )
        
        context = browser.new_context(
            user_agent='Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36',
            viewport={'width': 1920, 'height': 1080},
            locale='sv-SE'
        )
        
        page = context.new_page()
        
        logging.info(f"Loading search page: {url}")
        
        try:
            page.goto(url, wait_until='domcontentloaded', timeout=60000)
            
            # Check for Cloudflare
            if 'challenge-platform' in page.content():
                logging.warning("⚠️  Cloudflare challenge detected!")
                if not headless:
                    logging.info("Please solve the challenge...")
                    page.wait_for_url(url, timeout=30000)
                else:
                    logging.error("Cannot solve Cloudflare in headless mode")
                    browser.close()
                    return {'links': [], 'pagination': {}, 'error': 'cloudflare'}
            
            # Wait for page to load
            time.sleep(3)
            
            # Extract links
            links = extract_property_links_from_page(page)
            logging.info(f"✓ Found {len(links)} property links")
            
            # Get pagination info
            pagination = get_pagination_info(page)
            
            result = {
                'url': url,
                'links': links,
                'pagination': pagination,
                'scraped_at': datetime.now().isoformat()
            }
            
        except Exception as e:
            logging.error(f"Error scraping page: {e}")
            result = {
                'url': url,
                'links': [],
                'pagination': {},
                'error': str(e)
            }
        
        finally:
            browser.close()
        
        return result


def scrape_multiple_pages(base_url: str, max_pages: int = 3, delay: int = 5, headless: bool = False) -> List[Dict]:
    """
    Scrape multiple pages of search results.
    Adds page parameter to URL and respects rate limits.
    """
    all_results = []
    
    for page_num in range(1, max_pages + 1):
        # Add page parameter to URL
        if 'page=' in base_url:
            # Replace existing page parameter
            url = base_url.replace(f'page={page_num-1}', f'page={page_num}')
        else:
            # Add page parameter
            separator = '&' if '?' in base_url else '?'
            url = f"{base_url}{separator}page={page_num}"
        
        logging.info(f"\n{'='*80}")
        logging.info(f"Scraping page {page_num}/{max_pages}")
        logging.info(f"{'='*80}")
        
        result = scrape_search_page(url, headless=headless)
        all_results.append(result)
        
        if 'error' in result:
            logging.error(f"Error on page {page_num}, stopping")
            break
        
        # Rate limiting - be polite!
        if page_num < max_pages:
            logging.info(f"Waiting {delay} seconds before next request...")
            time.sleep(delay)
    
    return all_results


def save_links_to_csv(results: List[Dict], filename: str = None):
    """Save collected links to CSV file."""
    if filename is None:
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f'hemnet_links_{timestamp}.csv'
    
    # Flatten all links from all pages
    all_links = []
    for result in results:
        for link in result.get('links', []):
            all_links.append(link)
    
    # Deduplicate by URL
    seen = set()
    unique_links = []
    for link in all_links:
        if link['url'] not in seen:
            seen.add(link['url'])
            unique_links.append(link)
    
    # Save to CSV
    with open(filename, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=['url', 'property_id', 'found_at'])
        writer.writeheader()
        writer.writerows(unique_links)
    
    logging.info(f"\n✓ Saved {len(unique_links)} unique links to {filename}")
    return filename


def main():
    """Test the link collector"""
    
    # Start with the provided URL
    base_url = "https://www.hemnet.se/bostader?item_types=bostadsratt&expand_locations=10000&location_ids=17989"
    
    print("=" * 80)
    print("Hemnet Link Collector - Phase 1")
    print("=" * 80)
    print("\nThis script will:")
    print("1. Load the Hemnet search page")
    print("2. Extract all property listing links")
    print("3. Get pagination information")
    print("4. Optionally scrape multiple pages")
    print("\nNOTE: Running in visible browser mode to handle Cloudflare")
    print("=" * 80)
    
    # Test 1: Single page
    print("\n[TEST 1] Scraping single page...")
    input("Press Enter to continue...")
    
    result = scrape_search_page(base_url, headless=False)
    
    print(f"\nResults:")
    print(f"  Links found: {len(result['links'])}")
    print(f"  Current page: {result['pagination'].get('current_page')}")
    print(f"  Total pages: {result['pagination'].get('total_pages')}")
    print(f"  Total results: {result['pagination'].get('total_results')}")
    
    if result['links']:
        print(f"\nFirst 3 links:")
        for link in result['links'][:3]:
            print(f"  - {link['url']}")
    
    # Test 2: Multiple pages (optional)
    print("\n" + "=" * 80)
    response = input("\nDo you want to scrape multiple pages? (y/n): ")
    
    if response.lower() == 'y':
        num_pages = int(input("How many pages to scrape? (1-50): "))
        delay = int(input("Delay between requests in seconds? (3-10): "))
        
        print(f"\n[TEST 2] Scraping {num_pages} pages with {delay}s delay...")
        
        results = scrape_multiple_pages(base_url, max_pages=num_pages, delay=delay, headless=False)
        
        # Save to CSV
        filename = save_links_to_csv(results)
        
        # Summary
        total_links = sum(len(r.get('links', [])) for r in results)
        print(f"\n{'='*80}")
        print("SUMMARY")
        print(f"{'='*80}")
        print(f"Pages scraped: {len(results)}")
        print(f"Total links found: {total_links}")
        print(f"Saved to: {filename}")
    
    print("\n✓ Done!")


if __name__ == "__main__":
    main()
