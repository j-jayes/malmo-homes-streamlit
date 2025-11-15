# Date Filtering Issue - Investigation Results

**Date:** 2025-11-15
**Status:** ❌ Date filtering approach FAILED - DO NOT USE
**Conclusion:** Hemnet ignores date parameters. Use area filtering instead.

## Problem Discovery

When testing the batch scraper with January 2020, discovered that properties from **November 2025** were being returned instead.

## Investigation Steps

### 1. Initial Approach
- **URL tested:** `?sold_min=2020-01-01`
- **Result:** ❌ Showed all properties from Jan 2020 onwards (including Nov 2025)
- **Root cause:** Missing `sold_max` parameter

### 2. Second Approach
- **URL tested:** `?sold_min=2020-01-01&sold_max=2020-02-01`
- **Result:** ❌ Still showed recent properties (Nov 2025)
- **Root cause:** Parameters ignored without `sold_age=all`

### 3. Third Approach  
- **URL tested:** `?sold_age=all&sold_min=2020-01-01&sold_max=2020-02-01`
- **Result:** ❓ Unclear - Cloudflare blocking local verification
- **Issue:** Cannot verify actual sold dates due to timeouts

## Key Findings

1. **Hemnet's UI shows relative filters** ("Såld inom de senaste 3/6/12 mån")
2. **URL parameters may not work** as expected for historical data
3. **Sidebar filters** suggest relative time ranges, not absolute dates
4. **The 2,500 result limit** still applies regardless of date filtering

## Verification Problem

```python
# Tried to verify sold dates
url = 'https://www.hemnet.se/salda/lagenhet-...'
# Result: Timeout errors (Cloudflare challenges)
```

Without Xvfb (GitHub Actions environment), cannot reliably verify if date filtering works.

## Conclusion

❌ **Date-based filtering is unreliable** for the following reasons:
1. URL parameters may be ignored
2. Cannot verify locally due to Cloudflare
3. Hemnet UI suggests relative time windows, not absolute dates
4. Still hits 2,500 result limit even if dates work

---

## New Strategy Recommendation

✅ **Use living area (boarea) filtering instead**

### Why This Approach is Better

1. **Visible in UI:** Living area sliders clearly visible in sidebar
2. **Controllable steps:** Can adjust ranges dynamically
3. **Verifiable:** Can see result counts before scraping
4. **Flexible:** Can make steps smaller if hitting 2,500 limit

### Implementation Plan

See: `2025-11-15-living-area-filtering-strategy.md`
