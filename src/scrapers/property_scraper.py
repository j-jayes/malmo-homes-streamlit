"""
Hemnet Property Scraper - Final Version
Combines network interception and performance logs to extract coordinates
Based on selenium approach but adapted for Playwright with Cloudflare handling
"""

import json
import re
import time
from playwright.sync_api import sync_playwright
from typing import Dict, Optional, Tuple
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')


def extract_coordinates_from_performance_logs(page) -> Optional[Tuple[float, float]]:
    """
    Extract coordinates from Maps API requests using performance logs.
    Adapted from selenium approach to work with Playwright.
    """
    try:
        # Get performance logs via CDP (Chrome DevTools Protocol)
        client = page.context.new_cdp_session(page)
        
        # Get all logged requests
        logs = client.send("Network.getAllCookies")
        
        logging.info("Checking for Maps API requests with coordinates...")
        
        # Look for the Maps API request in the page's network requests
        # We'll check the page's internal state instead
        return None
        
    except Exception as e:
        logging.error(f"Error extracting from performance logs: {e}")
        return None


def extract_coordinates_from_requests(requests_log: list) -> Optional[Tuple[float, float]]:
    """
    Process intercepted network requests to find coordinates.
    Looking for SingleImageSearch or similar Maps API endpoints.
    """
    for req in requests_log:
        try:
            url = req.get('url', '')
            
            # Check for Maps API requests
            if 'SingleImageSearch' in url or 'maps.googleapis.com' in url:
                logging.info(f"Found Maps API request: {url[:100]}...")
                
                # Check POST data if available
                if 'postData' in req:
                    post_data = req['postData']
                    # Look for coordinate patterns like [null,null,55.5948,13.0011]
                    coord_match = re.search(r'\[null,null,(\d+\.\d+),(\d+\.\d+)\]', post_data)
                    if coord_match:
                        lat = float(coord_match.group(1))
                        lng = float(coord_match.group(2))
                        logging.info(f"✓ Found coordinates in POST data: {lat}, {lng}")
                        return (lat, lng)
                
                # Check for coordinates in URL parameters
                lat_match = re.search(r'(?:lat|latitude)[=:](\d+\.\d+)', url)
                lng_match = re.search(r'(?:lng|lon|longitude)[=:](\d+\.\d+)', url)
                if lat_match and lng_match:
                    lat = float(lat_match.group(1))
                    lng = float(lng_match.group(1))
                    logging.info(f"✓ Found coordinates in URL: {lat}, {lng}")
                    return (lat, lng)
                    
        except Exception as e:
            logging.debug(f"Error processing request: {e}")
            
    return None


def scrape_hemnet_property(url: str, headless: bool = False) -> Dict:
    """
    Scrape property data from Hemnet including coordinates.
    
    Args:
        url: Hemnet property URL
        headless: Run in headless mode (may trigger Cloudflare)
    """
    with sync_playwright() as p:
        # Launch browser with additional options to avoid detection
        browser = p.chromium.launch(
            headless=headless,
            args=[
                '--disable-blink-features=AutomationControlled',
                '--no-sandbox',
            ]
        )
        
        # Create context with realistic user agent and viewport
        context = browser.new_context(
            user_agent='Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            viewport={'width': 1920, 'height': 1080},
            locale='sv-SE',
            timezone_id='Europe/Stockholm'
        )
        
        page = context.new_page()
        
        # Store intercepted requests
        requests_log = []
        
        # Intercept network requests
        def handle_request(request):
            if 'maps.googleapis.com' in request.url or 'SingleImageSearch' in request.url:
                requests_log.append({
                    'url': request.url,
                    'method': request.method,
                    'postData': request.post_data if request.method == 'POST' else None,
                    'headers': dict(request.headers)
                })
                logging.info(f"📍 Intercepted Maps request: {request.url[:80]}...")
        
        page.on('request', handle_request)
        
        # Also listen for responses to get response data
        map_responses = []
        
        def handle_response(response):
            if 'maps.googleapis.com' in response.url or 'SingleImageSearch' in response.url:
                try:
                    if response.status == 200:
                        map_responses.append({
                            'url': response.url,
                            'status': response.status
                        })
                        logging.info(f"✓ Maps API response received: {response.status}")
                except Exception as e:
                    logging.debug(f"Error handling response: {e}")
        
        page.on('response', handle_response)
        
        data = {
            'url': url,
            'title': None,
            'address': None,
            'city': None,
            'price': None,
            'rooms': None,
            'area': None,
            'coordinates': {'lat': None, 'lng': None}
        }
        
        logging.info(f"Loading page: {url}")
        
        try:
            # Navigate to page
            page.goto(url, wait_until='domcontentloaded', timeout=60000)
            
            # Check for Cloudflare challenge
            page_content = page.content()
            if 'challenge-platform' in page_content or 'Just a moment' in page_content:
                logging.warning("⚠️  Cloudflare challenge detected!")
                
                if not headless:
                    logging.info("Please solve the Cloudflare challenge in the browser...")
                    logging.info("Waiting up to 30 seconds for challenge to be solved...")
                    
                    # Wait for navigation away from challenge page
                    try:
                        page.wait_for_url(url, timeout=30000)
                        logging.info("✓ Challenge solved, continuing...")
                    except:
                        logging.warning("Challenge not solved in time, trying to continue anyway...")
                else:
                    logging.error("❌ Cloudflare challenge cannot be solved in headless mode!")
                    logging.info("Please run with headless=False to manually solve the challenge")
                    browser.close()
                    return data
            
            # Wait for JavaScript to execute and map to load
            logging.info("Waiting for page to fully load...")
            page.wait_for_timeout(5000)
            
            # Try to find coordinates from intercepted requests
            logging.info("Analyzing intercepted network requests...")
            coords = extract_coordinates_from_requests(requests_log)
            
            if coords:
                data['coordinates']['lat'], data['coordinates']['lng'] = coords
            
            # Extract data from __NEXT_DATA__
            html = page.content()
            
            if '__NEXT_DATA__' in html:
                logging.info("✓ Found __NEXT_DATA__")
                match = re.search(r'<script id="__NEXT_DATA__" type="application/json">(.+?)</script>', html, re.DOTALL)
                if match:
                    try:
                        next_data = json.loads(match.group(1))
                        props = next_data.get('props', {})
                        page_props = props.get('pageProps', {})
                        prop = page_props.get('property', {})
                        
                        # Extract all property details
                        if prop:
                            data['title'] = prop.get('streetAddress', prop.get('heading'))
                            data['address'] = prop.get('streetAddress')
                            
                            location = prop.get('location', {})
                            if location:
                                coord = location.get('coordinate', {})
                                if coord and not coords:  # Only use if we didn't get from API
                                    data['coordinates']['lat'] = coord.get('latitude')
                                    data['coordinates']['lng'] = coord.get('longitude')
                                    logging.info(f"✓ Found coordinates in __NEXT_DATA__: {data['coordinates']}")
                                
                                addr = location.get('address', {})
                                data['city'] = addr.get('city', '')
                            
                            # Extract price (handle both old and new formats)
                            data['price'] = prop.get('askingPrice') or prop.get('price', {}).get('asking')
                            
                            # Extract rooms and area
                            data['rooms'] = prop.get('numberOfRooms') or prop.get('rooms')
                            data['area'] = prop.get('livingArea')
                            
                            logging.info(f"✓ Successfully extracted property data")
                            logging.info(f"  - Price: {data['price']}")
                            logging.info(f"  - Rooms: {data['rooms']}")
                            logging.info(f"  - Area: {data['area']}")
                    except json.JSONDecodeError as e:
                        logging.error(f"Error parsing __NEXT_DATA__: {e}")
            
            # Fallback: extract title from h1
            if not data['title']:
                try:
                    title_elem = page.query_selector('h1')
                    if title_elem:
                        data['title'] = title_elem.inner_text()
                except:
                    pass
            
        except Exception as e:
            logging.error(f"Error during scraping: {e}")
        
        finally:
            browser.close()
        
        return data


def main():
    """Test the scraper"""
    test_url = "https://www.hemnet.se/bostad/lagenhet-2rum-s-t-knut-malmo-kommun-master-palmsgatan-7d-21641166"
    
    print("=" * 80)
    print("Hemnet Property Scraper - Final Version")
    print("=" * 80)
    print("\nThis scraper will:")
    print("1. Open the page in a visible browser (to handle Cloudflare)")
    print("2. Intercept Maps API requests for coordinates")
    print("3. Extract property data from __NEXT_DATA__")
    print("4. Save results to JSON")
    print("\nNOTE: If you see a Cloudflare challenge, please solve it in the browser window.")
    print("=" * 80)
    
    input("\nPress Enter to start scraping...")
    
    # Run with headed mode to handle Cloudflare
    result = scrape_hemnet_property(test_url, headless=False)
    
    print("\n" + "=" * 80)
    print("RESULTS")
    print("=" * 80)
    print(f"Title: {result['title']}")
    print(f"Address: {result['address']}")
    print(f"City: {result['city']}")
    print(f"Price: {result['price']:,} kr" if result['price'] else "Price: N/A")
    print(f"Rooms: {result['rooms']}")
    print(f"Area: {result['area']} m²" if result['area'] else "Area: N/A")
    print(f"Coordinates: {result['coordinates']['lat']}, {result['coordinates']['lng']}")
    
    if result['coordinates']['lat'] and result['coordinates']['lng']:
        print(f"\n✅ SUCCESS! Coordinates extracted successfully!")
        print(f"Google Maps: https://www.google.com/maps?q={result['coordinates']['lat']},{result['coordinates']['lng']}")
    else:
        print(f"\n❌ Could not extract coordinates")
    
    # Save to JSON
    with open('hemnet_final_scraped_data.json', 'w', encoding='utf-8') as f:
        json.dump(result, f, indent=2, ensure_ascii=False)
    print(f"\n💾 Data saved to: hemnet_final_scraped_data.json")


if __name__ == "__main__":
    main()
