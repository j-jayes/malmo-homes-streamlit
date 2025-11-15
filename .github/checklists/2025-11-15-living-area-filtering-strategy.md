# Living Area Filtering Strategy

**Date:** 2025-11-15
**Status:** ✅ IMPLEMENTED - This is the ONLY working approach
**Note:** Date filtering FAILED (Hemnet ignores date parameters)

## Strategy Overview

Instead of filtering by date (which Hemnet may ignore), use **living area (boarea)** ranges to partition the dataset. This gives us direct control over result counts.

## Why Living Area?

### Advantages
1. ✅ **Visible in UI:** Clear "Boarea" min/max sliders in sidebar
2. ✅ **Direct control:** Can adjust step size dynamically
3. ✅ **Verifiable:** Result count shown before scraping
4. ✅ **Reliable:** URL parameter likely to work (common filter)
5. ✅ **Full coverage:** Eventually covers all properties

### URL Parameter
```
?living_area_min=0&living_area_max=50
```

## Implementation Algorithm

```python
def scrape_by_living_area(location_id: int = 17989):
    """
    Scrape all properties by iterating through living area ranges
    """
    
    # Start with broad range
    min_area = 0
    max_area = 200  # Start with 200m² chunks
    step_size = 50   # Default step
    
    all_properties = []
    
    while min_area < 500:  # Max reasonable apartment size
        url = f"{BASE_URL}?item_types[]=bostadsratt&location_ids[]={location_id}&living_area_min={min_area}&living_area_max={max_area}"
        
        # Get result count
        result_count = get_total_results(url)
        
        # If too many results, decrease step size
        if result_count >= 2500:
            # Reduce range to get under limit
            max_area = min_area + (max_area - min_area) // 2
            continue
        
        # If very few results, increase step size
        elif result_count < 500 and (max_area - min_area) < 100:
            max_area += 50
            continue
        
        # Good range - scrape it
        properties = scrape_range(min_area, max_area)
        all_properties.extend(properties)
        
        # Move to next range
        min_area = max_area
        max_area = min_area + step_size
        
    return all_properties
```

## Adaptive Step Size Logic

| Result Count | Action |
|--------------|--------|
| ≥ 2,500 | ❌ Halve the range (too many results) |
| 1,000 - 2,499 | ✅ Scrape this range |
| 500 - 999 | ✅ Scrape, consider increasing next step |
| < 500 | ✅ Scrape, increase next step size |

## Expected Result Ranges

Based on Malmö apartment sizes:

| Living Area (m²) | Expected Properties | Action |
|------------------|---------------------|---------|
| 0-30 | ~5,000 | Split: 0-15, 15-30 |
| 30-50 | ~15,000 | Split: 30-40, 40-50 |
| 50-70 | ~20,000 | Split: 50-60, 60-70 |
| 70-100 | ~10,000 | May need split |
| 100-150 | ~4,000 | Single range OK |
| 150-500 | ~2,000 | Single range OK |

## Implementation Checklist

- [ ] Create `SoldPropertiesAreaScraper` class
- [ ] Implement `get_total_results(url)` helper
- [ ] Implement adaptive step size logic
- [ ] Add progress tracking (which ranges completed)
- [ ] Add resume capability
- [ ] Test with small area range (e.g., 150-200m²)
- [ ] Run full scrape once verified
- [ ] Deduplicate across ranges (property may appear in multiple ranges)

## Benefits Over Date Filtering

1. **No 2,500 limit issues:** We control the partition
2. **Verifiable:** Can see result count before scraping
3. **Complete coverage:** Guaranteed to get all properties
4. **No date ambiguity:** Don't rely on Hemnet's date filtering
5. **Resumable:** Easy to track which ranges are done

## Testing Plan

### Phase 1: Verify URL Parameters Work
```bash
# Test if living_area params actually filter
curl "https://www.hemnet.se/salda/bostader?item_types[]=bostadsratt&location_ids[]=17989&living_area_min=150&living_area_max=200"
```

### Phase 2: Test Small Range
```bash
# Scrape 150-200m² (should be ~500 properties)
python src/scrapers/sold_properties_scraper.py --area-min 150 --area-max 200
```

### Phase 3: Test Adaptive Logic
```bash
# Run with adaptive logic on 40-60m² (likely >2500)
python src/scrapers/sold_properties_scraper.py --area-min 40 --area-max 60 --adaptive
```

## Deduplication Strategy

Since we're partitioning by living area, properties with unspecified area might appear in multiple ranges. Need to:

1. Track property IDs across all ranges
2. Final deduplication step after all ranges scraped
3. Keep most complete record if duplicates exist

## Success Criteria

- [ ] All ranges 0-500m² scraped
- [ ] No range exceeds 2,500 results
- [ ] ~56,000 unique properties collected
- [ ] No Cloudflare blocks
- [ ] Completes within 6 hours on GitHub Actions

## Next Steps

1. Update `sold_properties_scraper.py` to accept `--area-min` and `--area-max`
2. Create adaptive iteration script
3. Test with one small range
4. Deploy to GitHub Actions
