# Hemnet Scraping: Living Area Filtering Solution

## ✅ Primary Approach

**This is the ONLY working approach for comprehensive link collection.**

### Why This is Required:
- ❌ Date filtering (`sold_min`/`sold_max`) **DOES NOT WORK** on Hemnet
- ❌ Hemnet ignores date URL parameters and returns all properties
- ✅ Living area filtering (`living_area_min`/`living_area_max`) **WORKS RELIABLY**
- ✅ Verified: URL parameters match actual results
- ✅ Handles 2,500 result limit via adaptive partitioning

### Use This For:
- ✅ One-time historical backfill (all ~38k properties)
- ✅ Ongoing monthly updates (just scrape all, deduplicate)
- ✅ Guaranteed complete coverage

---

## Quick Start

### Check result count for a range
```bash
python src/scrapers/sold_properties_scraper.py \
  --area-min 150 --area-max 200 \
  --check-count --headless
```

### Scrape a specific range
```bash
python src/scrapers/sold_properties_scraper.py \
  --area-min 150 --area-max 200 \
  --headless
```

### Scrape all properties automatically
```bash
# Full scrape with adaptive step sizing
python scripts/scrape_all_areas.py --headless

# Resume after interruption
python scripts/scrape_all_areas.py --headless

# Just consolidate existing results
python scripts/scrape_all_areas.py --consolidate-only
```

## Problem Solved

**Original Issue:** Hemnet limits search results to 2,500 properties. Date filtering was unreliable.

**Solution:** Partition dataset by living area (boarea) ranges with adaptive step sizing.

## Key Features

- ✅ **Adaptive partitioning:** Automatically splits ranges that exceed 2,500 results
- ✅ **Resume capability:** Saves progress, can continue after interruption
- ✅ **Deduplication:** Handles overlapping properties across ranges
- ✅ **Session management:** Reuses browser cookies to avoid Cloudflare challenges
- ✅ **Verifiable counts:** Can check result count before scraping

## Architecture

```
┌─────────────────────────────────────────────────────────┐
│ AdaptiveAreaScraper (scripts/scrape_all_areas.py)      │
│                                                         │
│  ┌────────────────────────────────────────┐            │
│  │ 1. Find optimal range (binary search)  │            │
│  │    - Check result count                │            │
│  │    - Split if ≥ 2,400                  │            │
│  └────────────────┬───────────────────────┘            │
│                   ↓                                     │
│  ┌────────────────────────────────────────┐            │
│  │ 2. Scrape range                        │            │
│  │    (SoldPropertiesScraper)             │            │
│  └────────────────┬───────────────────────┘            │
│                   ↓                                     │
│  ┌────────────────────────────────────────┐            │
│  │ 3. Save to CSV                         │            │
│  │    properties_MIN_MAX.csv              │            │
│  └────────────────┬───────────────────────┘            │
│                   ↓                                     │
│  ┌────────────────────────────────────────┐            │
│  │ 4. Update progress.json                │            │
│  └────────────────┬───────────────────────┘            │
│                   ↓                                     │
│  ┌────────────────────────────────────────┐            │
│  │ 5. Move to next range                  │            │
│  └────────────────────────────────────────┘            │
└─────────────────────────────────────────────────────────┘
```

## Files Modified/Created

### Modified
- `src/scrapers/sold_properties_scraper.py`
  - Added `scrape_area_range()` method
  - Added `get_total_results_count()` method
  - Updated CLI to support `--area-min`, `--area-max`, `--check-count`
  - Made `save_to_csv()` flexible for different field sets

### Created
- `scripts/scrape_all_areas.py` - Adaptive scraper with resume capability
- `docs/LIVING_AREA_FILTERING.md` - Full documentation
- `.github/checklists/2025-11-15-area-filtering-implementation.md` - Implementation tracker

## Expected Runtime

For Malmö kommun (~38,000 properties):
- **Result count checks:** ~15-20 API calls (fast, <5 min)
- **Scraping:** ~10-15 ranges × 50 pages = ~12-18 hours
  - With Cloudflare handling: ~1-2 min per page
  - Total: 500-750 pages to scrape

## Optimization Tips

1. **Use headless mode:** Faster, less resource intensive
   ```bash
   python scripts/scrape_all_areas.py --headless
   ```

2. **Run in tmux/screen:** For long-running scrapes
   ```bash
   tmux new -s hemnet-scrape
   python scripts/scrape_all_areas.py --headless
   # Detach: Ctrl+B, then D
   ```

3. **Monitor progress:**
   ```bash
   cat data/raw/area_ranges/progress.json
   ```

4. **Check scraped so far:**
   ```bash
   wc -l data/raw/area_ranges/properties_*.csv
   ```

## Troubleshooting

### "Cloudflare challenge detected"
- **Solution:** Handled automatically. Session saved for reuse.

### "Timeout exceeded"
- **Likely cause:** Network issue or Cloudflare challenge
- **Solution:** Script will continue. Session management handles this.

### "Result count is 0"
- **Likely cause:** Range has no properties
- **Solution:** Script automatically skips and moves to next range

### Script interrupted
- **Solution:** Just run again - progress is saved:
  ```bash
  python scripts/scrape_all_areas.py --headless
  ```

## Data Output

### Individual Range Files
```
data/raw/area_ranges/
  properties_0_50.csv
  properties_50_75.csv
  properties_75_100.csv
  ...
  progress.json
```

### Consolidated Output
```
data/raw/sold_properties_all_areas.csv
```

### CSV Format
```csv
property_id,url,area_range,scraped_at
2142088725610863032,https://www.hemnet.se/salda/lagenhet-...,150-200m²,2025-11-15T23:04:01.245882
```

## Next Steps

1. **Run full scrape:**
   ```bash
   python scripts/scrape_all_areas.py --headless
   ```

2. **Validate results:**
   ```bash
   # Check total unique properties
   python -c "import pandas as pd; df = pd.read_csv('data/raw/sold_properties_all_areas.csv'); print(f'Total: {len(df)}, Unique: {df.property_id.nunique()}')"
   ```

3. **Update GitHub Actions:**
   - Add workflow to run scraper monthly
   - Store results as artifacts

4. **Detail scraping:**
   - Use property URLs to scrape full details
   - Use existing `PropertyDetailScraper`

## References

- Original issue: `.github/checklists/2025-11-15-date-filtering-issue.md`
- Strategy doc: `.github/checklists/2025-11-15-living-area-filtering-strategy.md`
- Full docs: `docs/LIVING_AREA_FILTERING.md`
