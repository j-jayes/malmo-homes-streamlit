"""
Hemnet Sold Properties Scraper
Collects historical sold property data using time-based filtering
"""

import argparse
import csv
import json
import logging
import random
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Dict, Optional

from playwright.sync_api import sync_playwright, Page, BrowserContext


# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class SoldPropertiesScraper:
    """Scraper for Hemnet sold properties with stealth features"""
    
    BASE_URL = "https://www.hemnet.se/salda/bostader"
    SESSION_FILE = "data/.hemnet_session.json"
    
    def __init__(self, headless: bool = False, slow_mo: int = 100):
        self.headless = headless
        self.slow_mo = slow_mo
        self.session_cookies = None
        
    def _setup_browser_context(self, browser) -> BrowserContext:
        """Create browser context with stealth settings"""
        
        # Try to load existing session
        session_path = Path(self.SESSION_FILE)
        storage_state = None
        if session_path.exists():
            logger.info("Loading existing session...")
            storage_state = self.SESSION_FILE
        
        context = browser.new_context(
            viewport={'width': 1920, 'height': 1080},
            user_agent='Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            locale='sv-SE',
            timezone_id='Europe/Stockholm',
            storage_state=storage_state
        )
        
        return context
    
    def _human_like_delay(self, min_seconds: float = 3, max_seconds: float = 8):
        """Add random human-like delay"""
        delay = random.uniform(min_seconds, max_seconds)
        logger.debug(f"Waiting {delay:.2f} seconds...")
        time.sleep(delay)
    
    def _scroll_page_slowly(self, page: Page):
        """Scroll page like a human to trigger lazy loading"""
        page.evaluate("""
            async () => {
                await new Promise((resolve) => {
                    let totalHeight = 0;
                    const distance = 100;
                    const timer = setInterval(() => {
                        const scrollHeight = document.body.scrollHeight;
                        window.scrollBy(0, distance);
                        totalHeight += distance;
                        
                        if(totalHeight >= scrollHeight){
                            clearInterval(timer);
                            resolve();
                        }
                    }, 100);
                });
            }
        """)
        time.sleep(2)
    
    def _handle_cloudflare_if_needed(self, page: Page):
        """Wait for Cloudflare challenge if present"""
        try:
            # Check for Cloudflare challenge
            if "Checking your browser" in page.content() or "cf-browser-verification" in page.content():
                logger.warning("Cloudflare challenge detected, waiting...")
                page.wait_for_load_state("networkidle", timeout=30000)
                time.sleep(5)
                logger.info("Cloudflare challenge passed")
        except Exception as e:
            logger.debug(f"No Cloudflare challenge: {e}")
    
    def extract_property_links(self, page: Page) -> List[str]:
        """Extract property links from search results page"""
        
        # Wait for property listings to load - use more specific selector
        try:
            # Wait for results container
            page.wait_for_selector('div[data-testid="search-results"]', timeout=15000)
            time.sleep(2)  # Let all properties load
        except Exception as e:
            logger.warning(f"Search results container not found: {e}")
            # Continue anyway, might still find links
        
        # Extract all property links
        links = page.evaluate("""
            () => {
                // Try multiple selectors to find property links
                let propertyLinks = [];
                
                // Method 1: Look for property cards with specific href pattern
                const cardLinks = Array.from(document.querySelectorAll('a[href*="/salda/lagenhet-"]'));
                propertyLinks.push(...cardLinks.map(a => a.href));
                
                // Method 2: Look within result items
                const resultItems = document.querySelectorAll('[data-testid*="result"], .sold-property-listing, .js-link-item');
                resultItems.forEach(item => {
                    const link = item.querySelector('a[href*="/salda/"]');
                    if (link && link.href.includes('/salda/lagenhet-')) {
                        propertyLinks.push(link.href);
                    }
                });
                
                // Deduplicate and filter
                return [...new Set(propertyLinks)]
                    .filter(href => href.includes('/salda/lagenhet-'))
                    .filter(href => !href.includes('#'));
            }
        """)
        
        logger.info(f"Found {len(links)} property links on page")
        return links
    
    def get_total_results(self, page: Page) -> int:
        """Extract total number of results from page"""
        try:
            text = page.locator('text=/Visar .* av/').first.inner_text()
            # Extract number after "av" - handle both "625" and "625 " formats
            total_str = text.split('av')[1].strip().replace(' ', '').replace('\xa0', '')
            total = int(total_str)
            return total
        except Exception as e:
            logger.debug(f"Could not extract total results: {e}")
            return 0
    
    def get_total_results_count(self, location_id: str, area_min: int, area_max: int) -> int:
        """Get result count for an area range without scraping full pages"""
        
        with sync_playwright() as p:
            browser = p.chromium.launch(
                headless=True,
                args=['--disable-blink-features=AutomationControlled']
            )
            
            try:
                context = self._setup_browser_context(browser)
                page = context.new_page()
                
                url = f"{self.BASE_URL}?item_types[]=bostadsratt&location_ids[]={location_id}&living_area_min={area_min}&living_area_max={area_max}"
                
                logger.info(f"Checking result count for area {area_min}-{area_max}m²")
                page.goto(url, wait_until="domcontentloaded", timeout=30000)
                
                self._handle_cloudflare_if_needed(page)
                time.sleep(2)  # Let page fully load
                
                total = self.get_total_results(page)
                logger.info(f"Found {total} results for area {area_min}-{area_max}m²")
                
                return total
                
            except Exception as e:
                logger.error(f"Error getting result count: {e}")
                return 0
            finally:
                browser.close()
    
    def scrape_area_range(
        self,
        area_min: int,
        area_max: int,
        location_id: str = "17989",
        max_pages: int = 50
    ) -> List[Dict]:
        """Scrape sold properties within a specific living area range
        
        Args:
            area_min: Minimum living area in m²
            area_max: Maximum living area in m²
            location_id: Hemnet location ID (default: Malmö)
            max_pages: Maximum pages to scrape
        
        Returns:
            List of property data dictionaries
        """
        
        properties = []
        area_str = f"{area_min}-{area_max}m²"
        logger.info(f"Starting scrape for area range {area_str}")
        
        with sync_playwright() as p:
            browser = p.chromium.launch(
                headless=self.headless,
                slow_mo=self.slow_mo,
                args=[
                    '--disable-blink-features=AutomationControlled',
                    '--disable-dev-shm-usage',
                    '--no-sandbox',
                    '--disable-setuid-sandbox',
                ]
            )
            
            try:
                context = self._setup_browser_context(browser)
                page = context.new_page()
                
                # Build URL with living area filter
                url = f"{self.BASE_URL}?item_types[]=bostadsratt&location_ids[]={location_id}&living_area_min={area_min}&living_area_max={area_max}"
                
                logger.info(f"Navigating to: {url}")
                page.goto(url, wait_until="domcontentloaded", timeout=30000)
                
                # Handle Cloudflare
                self._handle_cloudflare_if_needed(page)
                
                # Get total results
                total_results = self.get_total_results(page)
                logger.info(f"Total results for {area_str}: {total_results}")
                
                if total_results >= 2500:
                    logger.warning(f"⚠️ Result count ({total_results}) exceeds 2,500 limit! Consider splitting this range.")
                
                # Save session cookies after first successful page load
                if not Path(self.SESSION_FILE).exists():
                    Path(self.SESSION_FILE).parent.mkdir(parents=True, exist_ok=True)
                    context.storage_state(path=self.SESSION_FILE)
                    logger.info("Session saved for future use")
                
                # Calculate pages to scrape
                total_pages = min((total_results + 49) // 50, max_pages)
                logger.info(f"Will scrape {total_pages} pages")
                
                all_links = []
                
                # Scrape each page
                for page_num in range(1, total_pages + 1):
                    logger.info(f"Scraping page {page_num}/{total_pages}")
                    
                    if page_num > 1:
                        page_url = f"{url}&page={page_num}"
                        self._human_like_delay(5, 10)
                        page.goto(page_url, wait_until="domcontentloaded", timeout=30000)
                    
                    # Scroll to load all content
                    self._scroll_page_slowly(page)
                    
                    # Extract links
                    links = self.extract_property_links(page)
                    all_links.extend(links)
                    
                    logger.info(f"Total unique links so far: {len(set(all_links))}")
                
                # Deduplicate
                unique_links = list(set(all_links))
                logger.info(f"Collected {len(unique_links)} unique property links for {area_str}")
                
                # Convert to property data format
                properties = [{
                    'property_id': link.split('-')[-1],
                    'url': link,
                    'area_range': area_str,
                    'scraped_at': datetime.now().isoformat()
                } for link in unique_links]
                
            except Exception as e:
                logger.error(f"Error scraping area range {area_str}: {e}")
                raise
            
            finally:
                browser.close()
        
        return properties
    
    def scrape_month(
        self,
        year: int,
        month: int,
        location_id: str = "17989",
        max_pages: int = 50
    ) -> List[Dict]:
        """
        Scrape sold properties for a specific month
        
        Args:
            year: Year to scrape
            month: Month to scrape (1-12)
            location_id: Hemnet location ID (default: Malmö)
            max_pages: Maximum pages to scrape
        
        Returns:
            List of property data dictionaries
        """
        
        properties = []
        month_str = f"{year}-{month:02d}"
        logger.info(f"Starting scrape for {month_str}")
        
        with sync_playwright() as p:
            # Launch browser
            browser = p.chromium.launch(
                headless=self.headless,
                slow_mo=self.slow_mo,
                args=[
                    '--disable-blink-features=AutomationControlled',
                    '--disable-dev-shm-usage',
                    '--no-sandbox',
                    '--disable-setuid-sandbox',
                ]
            )
            
            try:
                context = self._setup_browser_context(browser)
                page = context.new_page()
                
                # Calculate the last day of the month for sold_max
                if month == 12:
                    next_month_year = year + 1
                    next_month = 1
                else:
                    next_month_year = year
                    next_month = month + 1
                
                sold_min = f"{year}-{month:02d}-01"
                sold_max = f"{next_month_year}-{next_month:02d}-01"
                
                # Build URL with date filter - MUST include sold_age=all to enable date filtering
                url = f"{self.BASE_URL}?item_types[]=bostadsratt&location_ids[]={location_id}&sold_age=all&sold_min={sold_min}&sold_max={sold_max}"
                
                logger.info(f"Navigating to: {url}")
                page.goto(url, wait_until="domcontentloaded", timeout=30000)
                
                # Handle Cloudflare
                self._handle_cloudflare_if_needed(page)
                
                # Get total results
                total_results = self.get_total_results(page)
                logger.info(f"Total results for {month_str}: {total_results}")
                
                # Save session cookies after first successful page load
                if not Path(self.SESSION_FILE).exists():
                    Path(self.SESSION_FILE).parent.mkdir(parents=True, exist_ok=True)
                    context.storage_state(path=self.SESSION_FILE)
                    logger.info("Session saved for future use")
                
                # Calculate pages to scrape
                total_pages = min((total_results + 49) // 50, max_pages)
                logger.info(f"Will scrape {total_pages} pages")
                
                all_links = []
                
                # Scrape each page
                for page_num in range(1, total_pages + 1):
                    logger.info(f"Scraping page {page_num}/{total_pages}")
                    
                    if page_num > 1:
                        page_url = f"{url}&page={page_num}"
                        self._human_like_delay(5, 10)  # Longer delay between pages
                        page.goto(page_url, wait_until="domcontentloaded", timeout=30000)
                    
                    # Scroll to load all content
                    self._scroll_page_slowly(page)
                    
                    # Extract links
                    links = self.extract_property_links(page)
                    all_links.extend(links)
                    
                    logger.info(f"Total unique links so far: {len(set(all_links))}")
                
                # Deduplicate
                unique_links = list(set(all_links))
                logger.info(f"Collected {len(unique_links)} unique property links for {month_str}")
                
                # Convert to property data format
                properties = [{
                    'property_id': link.split('-')[-1],
                    'url': link,
                    'sold_month': month_str,
                    'scraped_at': datetime.now().isoformat()
                } for link in unique_links]
                
            except Exception as e:
                logger.error(f"Error scraping month {month_str}: {e}")
                raise
            
            finally:
                browser.close()
        
        return properties
    
    def save_to_csv(self, properties: List[Dict], output_path: Path):
        """Save properties to CSV file"""
        
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Check if file exists and has same data (idempotent)
        if output_path.exists():
            # Read existing data
            existing_ids = set()
            with open(output_path, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                existing_ids = {row['property_id'] for row in reader}
            
            # Check if we have the same data
            new_ids = {prop['property_id'] for prop in properties}
            if existing_ids == new_ids:
                logger.info(f"File {output_path} already exists with same data, skipping")
                return
            
            logger.info(f"Updating existing file {output_path}")
        
        # Determine fieldnames based on what's in the data
        if properties:
            # Use all fields present in first property
            fieldnames = list(properties[0].keys())
        else:
            # Default fieldnames
            fieldnames = ['property_id', 'url', 'sold_month', 'scraped_at']
        
        with open(output_path, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(properties)
        
        logger.info(f"Saved {len(properties)} properties to {output_path}")


def parse_month(month_str: str) -> tuple[int, int]:
    """Parse month string (YYYY-MM) into year and month"""
    year, month = map(int, month_str.split('-'))
    return year, month


def main():
    parser = argparse.ArgumentParser(description='Scrape sold properties from Hemnet')
    
    # Mode selection
    mode_group = parser.add_mutually_exclusive_group()
    mode_group.add_argument('--month', type=str, 
                           help='Month to scrape (YYYY-MM), defaults to last month')
    mode_group.add_argument('--area-min', type=int,
                           help='Minimum living area in m² (use with --area-max)')
    
    # Common arguments
    parser.add_argument('--area-max', type=int,
                       help='Maximum living area in m² (requires --area-min)')
    parser.add_argument('--location-id', type=str, default='17989',
                       help='Hemnet location ID (default: 17989 for Malmö)')
    parser.add_argument('--max-pages', type=int, default=30,
                       help='Maximum pages to scrape (default: 30)')
    parser.add_argument('--output', type=str,
                       help='Output CSV file path')
    parser.add_argument('--headless', action='store_true',
                       help='Run in headless mode')
    parser.add_argument('--test', action='store_true',
                       help='Test mode: scrape only 2 pages')
    parser.add_argument('--check-count', action='store_true',
                       help='Only check result count, do not scrape')
    
    args = parser.parse_args()
    
    # Validate area arguments
    if args.area_min is not None and args.area_max is None:
        parser.error('--area-max is required when using --area-min')
    if args.area_max is not None and args.area_min is None:
        parser.error('--area-min is required when using --area-max')
    
    # Test mode: limit to 2 pages
    max_pages = 2 if args.test else args.max_pages
    
    # Create scraper
    scraper = SoldPropertiesScraper(
        headless=args.headless,
        slow_mo=100 if not args.headless else 0
    )
    
    # Mode: Area filtering
    if args.area_min is not None:
        area_min = args.area_min
        area_max = args.area_max
        
        # Check count only mode
        if args.check_count:
            count = scraper.get_total_results_count(
                location_id=args.location_id,
                area_min=area_min,
                area_max=area_max
            )
            logger.info(f"✅ Result count for {area_min}-{area_max}m²: {count}")
            if count >= 2500:
                logger.warning("⚠️ This range will hit the 2,500 result limit!")
            return
        
        # Determine output path
        if args.output:
            output_path = Path(args.output)
        else:
            output_path = Path(f"data/raw/sold_properties_area_{area_min}_{area_max}.csv")
        
        logger.info(f"Configuration:")
        logger.info(f"  Area range: {area_min}-{area_max}m²")
        logger.info(f"  Location ID: {args.location_id}")
        logger.info(f"  Max pages: {max_pages}")
        logger.info(f"  Headless: {args.headless}")
        logger.info(f"  Output: {output_path}")
        
        try:
            properties = scraper.scrape_area_range(
                area_min=area_min,
                area_max=area_max,
                location_id=args.location_id,
                max_pages=max_pages
            )
            
            scraper.save_to_csv(properties, output_path)
            
            logger.info("✅ Scraping completed successfully!")
            logger.info(f"📊 Collected {len(properties)} properties")
            
        except Exception as e:
            logger.error(f"❌ Scraping failed: {e}")
            raise
    
    # Mode: Month filtering (original behavior)
    else:
        # Determine month to scrape
        if args.month:
            year, month = parse_month(args.month)
        else:
            # Default to last month
            last_month = datetime.now() - timedelta(days=30)
            year, month = last_month.year, last_month.month
        
        # Determine output path
        if args.output:
            output_path = Path(args.output)
        else:
            output_path = Path(f"data/raw/sold_links/sold_links_{year}{month:02d}.csv")
        
        logger.info(f"Configuration:")
        logger.info(f"  Month: {year}-{month:02d}")
        logger.info(f"  Location ID: {args.location_id}")
        logger.info(f"  Max pages: {max_pages}")
        logger.info(f"  Headless: {args.headless}")
        logger.info(f"  Output: {output_path}")
        
        try:
            properties = scraper.scrape_month(
                year=year,
                month=month,
                location_id=args.location_id,
                max_pages=max_pages
            )
            
            scraper.save_to_csv(properties, output_path)
            
            logger.info("✅ Scraping completed successfully!")
            logger.info(f"📊 Collected {len(properties)} properties")
            
        except Exception as e:
            logger.error(f"❌ Scraping failed: {e}")
            raise


if __name__ == "__main__":
    main()
