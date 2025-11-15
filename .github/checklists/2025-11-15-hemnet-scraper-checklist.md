# Hemnet Scraper with Playwright - Checklist

**Date:** 2025-11-15
**Goal:** Build a robust scraper for Hemnet property data including coordinates from Google Maps

## Planning Phase
- [x] Create checklist document
- [ ] Research Playwright documentation for network interception
- [ ] Analyze target page structure

## Implementation Phase
- [ ] Install Playwright with uv
- [ ] Install Playwright browsers
- [ ] Create initial scraper script
- [ ] Implement network request interception for Maps API
- [ ] Extract property details (rooms, address, price, etc.)
- [ ] Extract coordinates from Maps API response

## Testing Phase
- [x] Test on example URL: https://www.hemnet.se/bostad/lagenhet-2rum-s-t-knut-malmo-kommun-master-palmsgatan-7d-21641166
- [x] Discovered Cloudflare protection blocking automated access
- [x] Implemented solution using visible browser
- [x] Successfully extracted coordinates: 55.5972023, 13.017004
- [x] Validated coordinates on Google Maps

## Key Findings
1. **Cloudflare Protection**: Hemnet uses Cloudflare bot protection that blocks headless browsers
2. **Data Location**: Property data including coordinates is in `__NEXT_DATA__` JSON embedded in the page
3. **Maps API**: Google Maps is loaded and coordinates are sent via `SingleImageSearch` POST request
4. **GraphQL**: Hemnet uses GraphQL endpoints but they're also protected by Cloudflare
5. **POST Data Pattern**: Coordinates appear as `[null,null,LAT,LNG]` in Maps API requests

## Successful Solution
✅ **Network Interception Approach** (Based on user's Selenium method)
- Intercept Maps API `SingleImageSearch` POST request
- Extract coordinates from POST data using regex: `\[null,null,(\d+\.\d+),(\d+\.\d+)\]`
- Run in visible browser mode to handle Cloudflare challenges
- Fallback to `__NEXT_DATA__` parsing if network interception fails

## Files Created
1. `hemnet_scraper_final.py` - Main working scraper
2. `hemnet_scraper_exploration.py` - Initial exploration
3. `hemnet_scraper_advanced.py` - Async version
4. `hemnet_debug.py` - Debug utilities
5. `HEMNET_SCRAPER_README.md` - Complete documentation

## Test Results
```
2025-11-15 20:03:40,497 - INFO - ✓ Found coordinates in POST data: 55.5972023, 13.017004

✅ SUCCESS! Coordinates extracted successfully!
Google Maps: https://www.google.com/maps?q=55.5972023,13.017004
```

## Key Data Points to Capture
- Street address
- Coordinates (lat, lng)
- Property type
- Number of rooms
- Price
- Property description
- Any other relevant details

## Notes
- Map container class: `Map_container__FhaDJ`
- Need to intercept Maps API requests to get coordinates
- Using Playwright for dynamic content handling
