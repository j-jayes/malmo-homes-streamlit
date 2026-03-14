"""Unified Hemnet Property Detail Scraper.

Handles both for-sale (/bostad/) and sold (/salda/) properties.
Extracts all fields from __NEXT_DATA__ / Apollo State and validates with Pydantic schemas.

The scraper maintains a persistent browser session to avoid ~1-2s launch overhead per URL.
"""

from __future__ import annotations

import json
import logging
import os
import random
import re
import time
from datetime import date, datetime
from typing import Dict, Optional, Tuple

from playwright.sync_api import Browser, BrowserContext, Page, Playwright, sync_playwright

from src.models.property_schema import BaseProperty, ForSaleProperty, SoldProperty

logger = logging.getLogger(__name__)


def _respectful_sleep(default_min: float = 5.0, default_max: float | None = None) -> None:
    min_seconds = default_min
    max_seconds = default_max if default_max is not None else default_min
    min_override = os.getenv("HEMNET_DETAIL_MIN_DELAY_SECONDS")
    max_override = os.getenv("HEMNET_DETAIL_MAX_DELAY_SECONDS")
    try:
        if min_override is not None:
            min_seconds = max(float(min_override), 0.0)
        if max_override is not None:
            max_seconds = max(float(max_override), 0.0)
    except ValueError:
        logger.warning("Invalid detail delay env vars, falling back to defaults")
    if max_seconds < min_seconds:
        max_seconds = min_seconds
    delay = random.uniform(min_seconds, max_seconds)
    logger.debug("Sleeping %.2fs between property requests", delay)
    time.sleep(delay)


class PropertyScraper:
    """Scraper for individual Hemnet property pages.

    Manages a persistent Playwright browser so that many properties can be
    scraped without paying the browser-launch overhead per URL.

    Usage::

        with PropertyScraper(headless=True) as scraper:
            for url in urls:
                result = scraper.scrape_property(url)
    """

    def __init__(self, headless: bool = True, slow_mo: int = 0) -> None:
        self.headless = headless
        self.slow_mo = slow_mo
        self._playwright: Playwright | None = None
        self._browser: Browser | None = None
        self.requests_log: list[dict] = []

    def _ensure_browser(self) -> Browser:
        if self._browser and self._browser.is_connected():
            return self._browser
        if self._playwright is None:
            self._playwright = sync_playwright().start()
        self._browser = self._playwright.chromium.launch(
            headless=self.headless,
            slow_mo=self.slow_mo,
            args=[
                "--disable-blink-features=AutomationControlled",
                "--no-sandbox",
            ],
        )
        return self._browser

    def _new_context(self) -> BrowserContext:
        browser = self._ensure_browser()
        return browser.new_context(
            user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
            viewport={"width": 1920, "height": 1080},
            locale="sv-SE",
            timezone_id="Europe/Stockholm",
        )

    def close(self) -> None:
        if self._browser:
            try:
                self._browser.close()
            except Exception:
                pass
            self._browser = None
        if self._playwright:
            try:
                self._playwright.stop()
            except Exception:
                pass
            self._playwright = None

    def __enter__(self) -> "PropertyScraper":
        return self

    def __exit__(self, *exc_info: object) -> None:
        self.close()

    @staticmethod
    def detect_property_type(url: str) -> str:
        if "/salda/" in url:
            return "sold"
        if "/bostad/" in url:
            return "for_sale"
        raise ValueError(f"Unknown property type in URL: {url}")

    @staticmethod
    def extract_property_id(url: str) -> str:
        return url.rstrip("/").split("-")[-1]
    
    def _handle_cloudflare(self, page: Page) -> None:
        """Wait for Cloudflare challenge if present."""
        try:
            content = page.content()
            if 'challenge-platform' in content or 'Just a moment' in content:
                logger.warning("⚠️  Cloudflare challenge detected!")
                if not self.headless:
                    logger.info("Waiting for manual challenge resolution...")
                    page.wait_for_load_state("networkidle", timeout=30000)
                    _respectful_sleep()
                    logger.info("✓ Cloudflare challenge passed")
                else:
                    raise Exception("Cloudflare challenge in headless mode - cannot continue")
        except Exception as e:
            logger.debug(f"Cloudflare check: {e}")
    
    def _setup_request_interception(self, page: Page) -> None:
        """Set up network request interception for coordinate extraction."""
        self.requests_log = []
        
        def handle_request(request):
            if 'maps.googleapis.com' in request.url or 'SingleImageSearch' in request.url:
                self.requests_log.append({
                    'url': request.url,
                    'method': request.method,
                    'postData': request.post_data if request.method == 'POST' else None
                })
                logger.debug(f"📍 Intercepted Maps request")
        
        page.on('request', handle_request)
    
    def _extract_coordinates_from_requests(self) -> Optional[Tuple[float, float]]:
        """Extract coordinates from intercepted network requests."""
        for req in self.requests_log:
            try:
                url = req.get('url', '')
                
                # Check POST data for coordinate patterns
                if req.get('postData'):
                    post_data = req['postData']
                    # Pattern: [null,null,55.5948,13.0011]
                    coord_match = re.search(r'\[null,null,(\d+\.\d+),(\d+\.\d+)\]', post_data)
                    if coord_match:
                        lat = float(coord_match.group(1))
                        lng = float(coord_match.group(2))
                        logger.info(f"✓ Found coordinates in Maps API: {lat}, {lng}")
                        return (lat, lng)
                
                # Check URL parameters
                lat_match = re.search(r'(?:lat|latitude)[=:](\d+\.\d+)', url)
                lng_match = re.search(r'(?:lng|lon|longitude)[=:](\d+\.\d+)', url)
                if lat_match and lng_match:
                    lat = float(lat_match.group(1))
                    lng = float(lng_match.group(1))
                    logger.info(f"✓ Found coordinates in URL: {lat}, {lng}")
                    return (lat, lng)
                    
            except Exception as e:
                logger.debug(f"Error processing request: {e}")
        
        return None
    
    def _extract_next_data(self, page: Page) -> Optional[tuple[Dict, Dict]]:
        """Extract __NEXT_DATA__ JSON from page. Returns (property_data, apollo_state)."""
        try:
            html = page.content()
            if '__NEXT_DATA__' not in html:
                # Detect Hemnet 404 pages (removed / expired listings)
                title = page.title()
                if 'hittades inte' in title.lower() or 'not found' in title.lower() or '404' in title:
                    logger.warning("Listing removed from Hemnet (404): %s", title)
                else:
                    logger.warning("__NEXT_DATA__ not found in page (title: %s)", title)
                return None
            
            match = re.search(
                r'<script id="__NEXT_DATA__" type="application/json">(.+?)</script>',
                html,
                re.DOTALL
            )
            
            if match:
                next_data = json.loads(match.group(1))
                props = next_data.get('props', {})
                page_props = props.get('pageProps', {})
                
                # Try to find property data in Apollo State (GraphQL cache)
                apollo_state = page_props.get('__APOLLO_STATE__', {})
                if apollo_state:
                    # Find the Property/Listing object
                    # Keys can be: Property:12345, ActivePropertyListing:12345, SoldPropertyListing:12345
                    for key, value in apollo_state.items():
                        if isinstance(value, dict):
                            typename = value.get('__typename')
                            if typename in ['Property', 'ActivePropertyListing', 'SoldPropertyListing', 'Listing']:
                                logger.info(f"✓ Found property data in Apollo State ({typename})")
                                return value, apollo_state
                
                # Fallback: try direct property field (older format)
                property_data = page_props.get('property', {})
                if property_data:
                    logger.info("✓ Found property data in pageProps")
                    return property_data, {}
                
                logger.warning("No property data found in __NEXT_DATA__")
                return None
        except Exception as e:
            logger.error(f"Error extracting __NEXT_DATA__: {e}")
            return None
    
    def _extract_value(self, data: any, apollo_state: Dict = None) -> any:
        """
        Extract actual value from Apollo State objects.
        Apollo State often wraps values in objects like:
        {'__typename': 'Money', 'amount': 6787, 'formatted': '6\xa0787\xa0kr'}
        {'__typename': 'HousingForm', 'primaryGroup': 'APARTMENTS', 'code': 'APARTMENT'}
        
        Also handles Apollo references like {'__ref': 'Location:123'}
        """
        if not isinstance(data, dict):
            return data
        
        # Follow Apollo State references
        if '__ref' in data and apollo_state:
            ref_key = data['__ref']
            if ref_key in apollo_state:
                data = apollo_state[ref_key]
        
        # Money object
        if data.get('__typename') == 'Money':
            return data.get('amount')
        
        # Housing form
        if data.get('__typename') == 'HousingForm':
            # Return Swedish name or code
            return data.get('name') or data.get('code', '').title()
        
        # Tenure
        if data.get('__typename') == 'Tenure':
            return data.get('name') or data.get('code', '').replace('_', ' ').title()
        
        # Location reference
        if data.get('__typename') == 'Location':
            return data.get('fullName') or data.get('name')
        
        # Coordinate
        if data.get('__typename') == 'Coordinate':
            return data  # Return the whole dict, will be extracted separately
        
        # Generic fallback: look for common value fields
        for key in ['value', 'amount', 'name', 'code', 'label']:
            if key in data:
                return data[key]
        
        return data
    
    def _extract_common_fields(self, next_data: Dict, coords: Optional[Tuple[float, float]], apollo_state: Dict = None) -> Dict:
        """Extract fields common to all property types."""
        data = {}
        
        # Basic info - handle both direct and Apollo State formats
        data['address'] = next_data.get('streetAddress') or next_data.get('street')
        
        # Coordinates - prefer from Maps API
        if coords:
            data['latitude'], data['longitude'] = coords
        else:
            # Try Apollo State coordinate field
            location = next_data.get('location', {})
            coord_data = location.get('coordinate') or next_data.get('coordinate', {})
            data['latitude'] = coord_data.get('latitude')
            data['longitude'] = coord_data.get('longitude')
        
        # City and neighborhood - Apollo State structure
        # neighborhood is in 'area' field
        data['neighborhood'] = next_data.get('area')
        
        # City - look in districts for the city (without "kommun" suffix)
        # Districts are ordered from specific to general, e.g.:
        # [Möllevången, Malmö Centrum/Hamnen, Malmö, Folkets Park]
        # We want "Malmö" - the simplest non-neighborhood name
        districts = next_data.get('districts', [])
        if districts and apollo_state:
            city_candidates = []
            for district_ref in districts:
                district = self._extract_value(district_ref, apollo_state)
                if isinstance(district, str):
                    # Skip if it has "kommun" or "län" in it, those are not cities
                    if 'kommun' not in district.lower() and 'län' not in district.lower():
                        # Also check it's not the same as neighborhood
                        if district != data.get('neighborhood'):
                            city_candidates.append(district)
            
            # Prefer the shortest name (likely the city, not sub-districts)
            # Also prefer names without "/" (like "Malmö Centrum/Hamnen")
            if city_candidates:
                # Sort by: no "/" first, then by length
                city_candidates.sort(key=lambda x: ('/' in x, len(x)))
                data['city'] = city_candidates[0]
        
        # Fallback: try to parse from locationName or municipality
        if not data.get('city'):
            location_name = next_data.get('locationName', '')
            if ', ' in location_name:
                # Format is "Neighborhood, City kommun"
                parts = location_name.split(', ')
                if len(parts) >= 2:
                    city_part = parts[1].replace(' kommun', '').strip()
                    data['city'] = city_part
        
        # Property details - Apollo State uses snake_case sometimes
        housing = (next_data.get('housingForm') or 
                  next_data.get('housing_form') or 
                  next_data.get('propertyType'))
        data['housing_type'] = self._extract_value(housing)
        
        tenure = (next_data.get('tenureForm') or 
                 next_data.get('tenure') or
                 next_data.get('ownershipType'))
        data['ownership_type'] = self._extract_value(tenure)
        
        data['rooms'] = (next_data.get('numberOfRooms') or 
                        next_data.get('rooms') or
                        next_data.get('roomCount'))
        living_area = (next_data.get('livingArea') or 
                      next_data.get('living_area'))
        if isinstance(living_area, (int, float)):
            data['living_area'] = living_area
        elif living_area is not None:
            try:
                data['living_area'] = float(living_area)
            except (ValueError, TypeError):
                logger.debug(f"Could not convert living_area to float: {living_area}")
                data['living_area'] = None
        data['lot_area'] = (next_data.get('landArea') or 
                          next_data.get('plotArea') or
                          next_data.get('lot_area'))
        
        # Floor info - check both raw and formatted versions
        floor = next_data.get('floor') or next_data.get('formattedFloor')
        if floor is not None:
            data['floor'] = str(floor)
        
        data['has_elevator'] = next_data.get('elevator', False) or next_data.get('hasElevator', False)
        data['has_balcony'] = next_data.get('balcony', False) or next_data.get('hasBalcony', False)
        building_year = (next_data.get('constructionYear') or 
                        next_data.get('buildYear') or
                        next_data.get('yearBuilt') or
                        next_data.get('legacyConstructionYear'))
        if isinstance(building_year, int):
            data['building_year'] = building_year
        elif building_year is not None:
            try:
                data['building_year'] = int(building_year)
            except (ValueError, TypeError):
                logger.debug(f"Could not convert building_year to int: {building_year}")
                data['building_year'] = None
        data['energy_class'] = next_data.get('energyClass') or next_data.get('energyRating')
        
        # Association info
        assoc = next_data.get('housingAssociation') or next_data.get('association')
        data['association_name'] = self._extract_value(assoc)
        
        fee = next_data.get('fee') or next_data.get('monthlyFee') or next_data.get('avgift')
        data['association_fee'] = self._extract_value(fee)
        
        op_cost = next_data.get('operatingCost') or next_data.get('driftskostnad')
        data['operating_cost'] = self._extract_value(op_cost)
        
        # Description
        data['description'] = next_data.get('description')
        
        return data
    
    def _extract_sold_fields(self, property_data: dict) -> dict:
        """Extract sold-specific fields."""
        fields = {}
        
        # Asking price (what it was listed for)
        asking_price_data = property_data.get('askingPrice') or property_data.get('listing', {}).get('price')
        fields['asking_price'] = self._extract_value(asking_price_data)
        
        # Final sold price
        final_price_data = property_data.get('soldPrice') or property_data.get('finalPrice') or property_data.get('sellingPrice')
        fields['final_price'] = self._extract_value(final_price_data)
        
        # Calculate price change
        if fields.get('asking_price') and fields.get('final_price'):
            fields['price_change'] = fields['final_price'] - fields['asking_price']
        
        # Sold date - try multiple field names and formats
        sold_date = property_data.get('soldAt') or property_data.get('soldDate') or property_data.get('saleDate')
        if sold_date:
            try:
                # Handle both timestamp (seconds) and ISO string
                if isinstance(sold_date, (int, float)):
                    # Unix timestamp (already in seconds)
                    fields['sold_date'] = datetime.fromtimestamp(sold_date).date()
                elif isinstance(sold_date, str):
                    # Try parsing as float first (for string numbers)
                    try:
                        timestamp = float(sold_date)
                        fields['sold_date'] = datetime.fromtimestamp(timestamp).date()
                    except ValueError:
                        # If not a number, try ISO format
                        fields['sold_date'] = datetime.fromisoformat(sold_date.replace('Z', '+00:00')).date()
            except Exception as e:
                logger.warning(f"Could not parse sold_date: {sold_date} - {e}")
        
        # Statistics - check both nested and top-level
        stats = property_data.get('statistics', {})
        fields['visit_count'] = (property_data.get('timesViewed') or 
                                stats.get('visitsTotal') or 
                                stats.get('visits'))
        fields['days_on_market'] = property_data.get('daysOnMarket')
        
        return fields
    
    def _extract_for_sale_fields(self, next_data: Dict) -> Dict:
        """Extract for-sale specific fields."""
        data = {}
        
        # Pricing - handle Money objects
        asking = next_data.get('askingPrice') or next_data.get('price', {}).get('asking')
        data['asking_price'] = self._extract_value(asking)
        
        # Listing info
        published_at = next_data.get('publishedAt') or next_data.get('listedAt')
        if published_at:
            try:
                # Handle both timestamp (seconds) and ISO string
                if isinstance(published_at, (int, float)):
                    # Unix timestamp (already in seconds)
                    data['listed_date'] = datetime.fromtimestamp(published_at).date()
                elif isinstance(published_at, str):
                    # Try parsing as float first (for string numbers)
                    try:
                        timestamp = float(published_at)
                        data['listed_date'] = datetime.fromtimestamp(timestamp).date()
                    except ValueError:
                        # If not a number, try ISO format
                        data['listed_date'] = datetime.fromisoformat(published_at.replace('Z', '+00:00')).date()
            except Exception as e:
                logger.warning(f"Could not parse listed_date: {published_at} - {e}")
        
        # Days on market (calculate if we have listed_date)
        if data.get('listed_date'):
            data['days_on_market'] = (date.today() - data['listed_date']).days
        
        # Viewing times
        viewings = next_data.get('viewings', [])
        data['viewing_times'] = [v.get('formattedTime') or v.get('time') for v in viewings if v.get('formattedTime') or v.get('time')]
        
        # Statistics
        stats = next_data.get('statistics', {})
        data['visit_count'] = stats.get('visitsTotal') or stats.get('visits')
        
        return data
    
    def scrape_property(self, url: str) -> Optional[BaseProperty]:
        """Scrape a single property page and return a validated Pydantic model."""
        property_type = self.detect_property_type(url)
        property_id = self.extract_property_id(url)

        context = self._new_context()
        page = context.new_page()
        self._setup_request_interception(page)

        try:
            page.goto(url, wait_until="domcontentloaded", timeout=60000)
            self._handle_cloudflare(page)
            page.wait_for_timeout(5000)

            coords = self._extract_coordinates_from_requests()
            result = self._extract_next_data(page)
            if not result:
                logger.error("Failed to extract property data from %s", url)
                return None

            next_data, apollo_state = result
            data = self._extract_common_fields(next_data, coords, apollo_state)
            data["property_id"] = property_id
            data["property_type"] = property_type
            data["url"] = url
            data["scraped_at"] = datetime.now()

            if property_type == "sold":
                data.update(self._extract_sold_fields(next_data))
                model = SoldProperty(**data)
            else:
                data.update(self._extract_for_sale_fields(next_data))
                model = ForSaleProperty(**data)

            model.calculate_derived_fields()
            return model

        except Exception as exc:
            logger.error("Error scraping %s: %s", url, exc, exc_info=True)
            return None
        finally:
            page.close()
            context.close()
