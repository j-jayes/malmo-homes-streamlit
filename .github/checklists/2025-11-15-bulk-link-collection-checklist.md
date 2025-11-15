# Hemnet Bulk Scraper - Link Collection Checklist

**Date:** 2025-11-15
**Goal:** Collect all property listing URLs from Hemnet with smart pagination strategy

## Phase 1: Simple Link Collection (Start Here)
- [x] Create script to scrape listing page: https://www.hemnet.se/bostader?item_types=bostadsratt&expand_locations=10000&location_ids=17989
- [ ] Test: Extract all property links from a single page
- [ ] Test: Identify pagination controls and total number of pages
- [ ] Test: Implement basic pagination loop (respecting rate limits)
- [ ] Test with first 3-5 pages (handle Cloudflare)
- [ ] Save links to CSV with timestamp

**Script created:** `hemnet_link_collector.py`
**Status:** Ready for testing

## Phase 2: Rate Limiting & Politeness
- [ ] Add random delays between requests (2-5 seconds)
- [ ] Implement exponential backoff for errors
- [ ] Respect robots.txt guidelines
- [ ] Add user-agent rotation
- [ ] Log all requests and responses

## Phase 3: Smart Filtering Strategy (Advanced)

### Problem
- Hemnet only shows max 2,500 properties per search (50 pages × 50 per page)
- Total properties may exceed this limit (e.g., 100,000 properties)
- Need to use filters to divide the dataset into smaller chunks

### Available Filters to Combine
- Number of rooms (1, 2, 3, 4, 5+)
- Property type (lägenhet, hus, villa, etc.)
- Price ranges (0-1M, 1-2M, 2-3M, etc.)
- Size ranges (0-40m², 40-60m², 60-80m², etc.)
- Municipality/Area (already filtering by Malmö: 17989)
- Construction year ranges

### Strategy Options

#### Option A: Hierarchical Filtering
```
1. Start with broad filter (e.g., all bostadsrätt in Malmö)
2. If results > 2500:
   - Split by rooms (1, 2, 3, 4, 5+)
3. For each room count, if still > 2500:
   - Split by price ranges
4. For each price range, if still > 2500:
   - Split by size ranges
Continue until all segments < 2500
```

#### Option B: Grid-Based Filtering
```
Create a grid of all filter combinations:
- 5 room types × 10 price ranges × 8 size ranges = 400 queries
- Each query should return < 2500 results
- Check for duplicates across queries
```

#### Option C: Dynamic Adaptive Filtering
```
1. Query with current filters
2. If result count = 2500 (hit limit):
   - Add another filter dimension
   - Split into sub-queries
3. If result count < 2500:
   - Scrape all pages
4. Keep track of filter combinations used
5. Deduplicate final results
```

### Implementation Notes
- [ ] Build filter combination generator
- [ ] Implement duplicate detection (by property ID/URL)
- [ ] Track which filter combinations have been queried
- [ ] Resume capability (save progress to avoid re-scraping)
- [ ] Estimate total queries needed before starting
- [ ] Create coverage report (% of properties captured)

## Phase 4: Data Management
- [ ] Create database/file structure for storing links
- [ ] Implement deduplication logic
- [ ] Add metadata (date collected, filters used, page number)
- [ ] Track scraping progress (which filters completed)
- [ ] Handle interrupted scraping (resume from checkpoint)

## Phase 5: Validation & Quality
- [ ] Verify no duplicate links
- [ ] Check for dead/invalid links
- [ ] Validate link format
- [ ] Compare total count with Hemnet's reported count (if available)
- [ ] Random sample validation (manually check 10-20 links)

## Phase 6: Integration with Property Scraper
- [ ] Read links from CSV/database
- [ ] Scrape each property using `hemnet_scraper_final.py`
- [ ] Add batch processing with checkpoints
- [ ] Error handling and retry logic
- [ ] Final dataset compilation

## Technical Considerations

### URL Structure
Base URL: `https://www.hemnet.se/bostader`

Parameters:
- `item_types` - bostadsratt, villa, etc.
- `location_ids` - 17989 (Malmö)
- `page` - pagination (1-50)
- `rooms_min` - minimum rooms
- `rooms_max` - maximum rooms
- `price_max` - maximum price
- `living_area_min` - minimum m²
- `living_area_max` - maximum m²

### Rate Limiting Strategy
```python
# Conservative approach
requests_per_minute = 10
delay_between_requests = 6  # seconds

# More aggressive (monitor for blocks)
requests_per_minute = 20
delay_between_requests = 3  # seconds
```

### Cloudflare Handling
- Use visible browser for first request to solve challenge
- Save cookies/session
- Reuse session for subsequent requests
- Rotate sessions if rate limited

## Testing Strategy

### Test 1: Single Page
- URL: First page of bostadsrätt in Malmö
- Expected: ~50 property links
- Success criteria: All links extracted correctly

### Test 2: Pagination
- URL: First 3 pages
- Expected: ~150 property links
- Success criteria: No duplicates, correct pagination

### Test 3: Filter Combination
- Test: 2-room apartments in Malmö
- Check if result count < 2500
- If not, test with additional filters

### Test 4: Full Coverage (Small Area)
- Pick a small municipality (< 500 properties)
- Run full scraping with all strategies
- Verify 100% coverage

## Output Files

```
data/
├── links/
│   ├── raw_links_YYYYMMDD_HHMMSS.csv
│   ├── deduplicated_links.csv
│   └── scraping_progress.json
├── properties/
│   ├── property_data_batch_001.json
│   ├── property_data_batch_002.json
│   └── ...
└── logs/
    ├── link_collection.log
    └── property_scraping.log
```

## Success Metrics
- [ ] Collected > 10,000 unique property links
- [ ] Zero duplicate links in final dataset
- [ ] < 1% error rate in link collection
- [ ] Estimated coverage > 95% of available properties
- [ ] No IP blocks or rate limiting issues

## Notes & Ideas

### Smart Filtering Algorithm Pseudocode
```python
def collect_all_links(base_filters):
    queue = [base_filters]
    all_links = set()
    
    while queue:
        filters = queue.pop(0)
        count = get_result_count(filters)
        
        if count <= 2500:
            # Safe to scrape all pages
            links = scrape_all_pages(filters)
            all_links.update(links)
        else:
            # Need to split further
            sub_filters = split_filters(filters)
            queue.extend(sub_filters)
    
    return all_links
```

### Priority Filter Dimensions (by effectiveness)
1. **Rooms** - Good distribution (5-6 categories)
2. **Price** - Can create 10-20 ranges
3. **Size (m²)** - Can create 8-10 ranges
4. **Property age** - Can split by decade
5. **Geographic sub-areas** - Last resort (complex)

### Monitoring Dashboard Ideas
- Real-time count of unique links collected
- Current filter being processed
- Estimated time remaining
- Error rate and retry counts
- Progress bar per filter combination
