# Hemnet Property Scraper

A robust Python scraper for extracting property data from Hemnet.se, including coordinates from Google Maps API.

## Features

- ✅ Extracts coordinates from intercepted Maps API requests
- ✅ Handles Cloudflare bot protection
- ✅ Extracts all property details (price, rooms, area, address)
- ✅ Network request interception using Playwright
- ✅ Saves data to JSON format

## Installation

1. Install dependencies using uv:
```bash
uv pip install playwright
```

2. Install Playwright browsers:
```bash
.venv/bin/playwright install chromium
```

## Usage

### Basic Usage

```python
from hemnet_scraper_final import scrape_hemnet_property

url = "https://www.hemnet.se/bostad/lagenhet-2rum-s-t-knut-malmo-kommun-master-palmsgatan-7d-21641166"

# Run with visible browser (recommended for Cloudflare handling)
data = scrape_hemnet_property(url, headless=False)

print(f"Coordinates: {data['coordinates']['lat']}, {data['coordinates']['lng']}")
print(f"Price: {data['price']:,} kr")
```

### Running the Script

```bash
python hemnet_scraper_final.py
```

This will:
1. Open a browser window
2. Load the Hemnet property page
3. If Cloudflare challenge appears, wait for you to solve it
4. Intercept Maps API requests to extract coordinates
5. Extract property details from page data
6. Save results to `hemnet_final_scraped_data.json`

## How It Works

### Coordinate Extraction

The scraper uses **two methods** to extract coordinates:

1. **Primary: Network Interception** (Based on your Selenium approach)
   - Intercepts the Google Maps `SingleImageSearch` API request
   - Extracts coordinates from POST data: `[null,null,55.5972023,13.017004]`
   - This is the most reliable method

2. **Fallback: __NEXT_DATA__ Parsing**
   - Extracts coordinates from Next.js state embedded in the page
   - Used if network interception doesn't capture the request

### Key Components

```python
def extract_coordinates_from_requests(requests_log: list) -> Optional[Tuple[float, float]]:
    """
    Process intercepted network requests to find coordinates.
    Looking for SingleImageSearch or similar Maps API endpoints.
    """
    for req in requests_log:
        if 'SingleImageSearch' in req.get('url', ''):
            if 'postData' in req:
                post_data = req['postData']
                # Pattern: [null,null,55.5972023,13.017004]
                coord_match = re.search(r'\[null,null,(\d+\.\d+),(\d+\.\d+)\]', post_data)
                if coord_match:
                    lat = float(coord_match.group(1))
                    lng = float(coord_match.group(2))
                    return (lat, lng)
```

## Handling Cloudflare Protection

Hemnet uses Cloudflare bot protection. The scraper handles this in two ways:

### Option 1: Visible Browser (Recommended)
```python
data = scrape_hemnet_property(url, headless=False)
```
- Opens a visible browser window
- Allows manual solving of Cloudflare challenge
- Waits up to 30 seconds for challenge to be solved

### Option 2: Advanced (TODO)
For production use, consider:
- **playwright-stealth**: Makes automation less detectable
- **Saved browser sessions**: Save cookies after solving challenge once
- **Residential proxies**: Rotate IP addresses
- **Request delays**: Add random delays between requests

## Data Extracted

The scraper extracts the following data:

```json
{
  "url": "https://www.hemnet.se/bostad/...",
  "title": "Mäster palmsgatan 7D",
  "address": "Mäster palmsgatan 7D",
  "city": "S:t Knut, Malmö kommun",
  "price": 2495000,
  "rooms": 2,
  "area": 53,
  "coordinates": {
    "lat": 55.5972023,
    "lng": 13.017004
  }
}
```

## Success Example

From the test run:
```
2025-11-15 20:03:40,497 - INFO - ✓ Found coordinates in POST data: 55.5972023, 13.017004

✅ SUCCESS! Coordinates extracted successfully!
Google Maps: https://www.google.com/maps?q=55.5972023,13.017004
```

## Technical Details

### Network Interception Approach

The scraper is based on your original Selenium approach but adapted for Playwright:

**Original Selenium Method:**
```python
def extract_coordinates_from_selenium(driver, url):
    logs = driver.get_log("performance")
    for entry in logs:
        log = json.loads(entry["message"])
        if "SingleImageSearch" in request_url:
            coord_match = re.search(r'\[null,null,(\d+\.\d+),(\d+\.\d+)\]', post_data)
```

**Adapted Playwright Method:**
```python
def scrape_hemnet_property(url: str):
    requests_log = []
    
    def handle_request(request):
        if 'SingleImageSearch' in request.url:
            requests_log.append({
                'url': request.url,
                'postData': request.post_data
            })
    
    page.on('request', handle_request)
```

### Why This Approach Works

1. **Maps API Always Loads**: Every Hemnet property page loads Google Maps
2. **Consistent API Call**: The `SingleImageSearch` endpoint is always called with coordinates
3. **POST Data Format**: Coordinates are in a predictable format: `[null,null,LAT,LNG]`
4. **Intercept Before Render**: We catch the request before the map renders

## Files Created

- `hemnet_scraper_final.py` - Main scraper with Cloudflare handling
- `hemnet_scraper_exploration.py` - Initial exploration script
- `hemnet_scraper_advanced.py` - Async version (WIP)
- `hemnet_debug.py` - Debug script for troubleshooting
- `.github/checklists/2025-11-15-hemnet-scraper-checklist.md` - Development checklist

## Troubleshooting

### Cloudflare Challenge Not Solving
- Make sure to run with `headless=False`
- Check your internet connection
- Try using a different browser profile

### No Coordinates Found
- Ensure the page fully loads (default: 5 second wait)
- Check that Maps container exists on the page
- Try increasing the wait time

### Rate Limiting
- Add delays between requests
- Use rotating proxies
- Respect Hemnet's robots.txt

## Future Improvements

- [ ] Add support for playwright-stealth to bypass Cloudflare automatically
- [ ] Implement cookie/session saving to avoid repeated challenges
- [ ] Add bulk scraping with rate limiting
- [ ] Extract additional property features (balcony, parking, etc.)
- [ ] Add error recovery and retry logic
- [ ] Create a simple CLI interface

## License

For educational purposes only. Please respect Hemnet's terms of service and robots.txt.
