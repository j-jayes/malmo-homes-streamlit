# Historical Sold Properties Backfill Strategy

**Date:** 2025-11-15  
**Status:** Ready to Execute 🚀  
**Objective:** Collect ~56,000 sold property links since 2020

---

## 🎯 The Problem

Hemnet limits search results to **2,500 properties** (50 pages × 50 results).  
We need to collect **~56,000 sold properties** from 2020 onwards.

**Solution:** Time-based filtering by month! 🎉

---

## 💡 The Clever Strategy

### Phase 1: Link Collection (TODAY) ✅

**Script:** `scripts/backfill_sold_links.py`

**Key Features:**
- ✅ Month-by-month scraping (avoids 2,500 limit)
- ✅ Each month has ~500-1000 properties (well under limit)
- ✅ **Resume capability** if interrupted
- ✅ Progress tracking with ETA
- ✅ Saves links only (fast!)

**How It Works:**
```python
# Loop through each month
for month in ["2020-01", "2020-02", ..., "2025-11"]:
    # Scrape that month's sold properties
    url = f"hemnet.se/salda/bostader?sold_min={month}-01"
    
    # Collect property links
    links = extract_links_from_search_results()
    
    # Save to CSV
    save_to_csv(f"data/raw/sold_links/sold_links_{month}.csv")
    
    # Mark month as complete
    save_progress(month)
```

**Output:**
```
data/raw/sold_links/
├── sold_links_202001.csv  # ~500 links
├── sold_links_202002.csv  # ~600 links
├── sold_links_202003.csv  # ~550 links
├── ...
├── sold_links_202511.csv  # ~100 links
├── backfill_progress.json  # Resume capability
└── backfill_summary.json   # Final statistics
```

### Phase 2: Property Details (TOMORROW) 📅

**Script:** `scripts/scrape_sold_properties.py` (to be created)

**How It Works:**
```python
# Read all collected links
all_links = read_all_link_csvs()  # ~56,000 links

# Scrape each property's details
for link in all_links:
    property_data = scrape_property_details(link)
    save_to_database(property_data)
```

**Why Split Into Two Phases?**
1. **Faster:** Collecting links is quick (just search results)
2. **Safer:** Can resume if interrupted
3. **Cleaner:** Separate concerns (discovery vs extraction)
4. **Efficient:** Property detail scraping is slower, so we know exactly what to scrape

---

## 📊 Estimates

### Link Collection (Phase 1)
- **Months to scrape:** ~60 (Jan 2020 to Nov 2025)
- **Time per month:** ~2-5 minutes
- **Total time:** 2-5 hours (depends on rate limiting)
- **Total links:** ~56,000

### Property Detail Scraping (Phase 2)
- **Properties:** ~56,000
- **Time per property:** ~5-10 seconds
- **Total time:** 80-160 hours (3-7 days)
- **Strategy:** Batch processing with smart rate limiting

---

## 🚀 Execution Plan

### Today: Link Collection

```bash
# Test mode first (3 months)
python scripts/backfill_sold_links.py --test

# If test works, run full backfill
python scripts/backfill_sold_links.py

# Or specify date range
python scripts/backfill_sold_links.py --start 2020-01 --end 2023-12

# Headless mode for server
python scripts/backfill_sold_links.py --headless
```

**Progress Tracking:**
```
MONTH 1/60: 2020-01
✅ Completed 2020-01: 542 links
Progress: 1/60 months (1.7%)
Total links collected: 542
Average time per month: 3.2 minutes
ETA: 3 hours 8 minutes

MONTH 2/60: 2020-02
✅ Completed 2020-02: 498 links
...
```

**Resume Capability:**
```bash
# If interrupted, just run again
python scripts/backfill_sold_links.py

# Output:
# Loaded progress: 25 months already scraped
# Months to scrape: 35
# Ready to scrape 35 months? (y/n):
```

### Tomorrow: Property Details

```bash
# Create new script tomorrow
python scripts/scrape_sold_properties_details.py \
    --input-dir data/raw/sold_links \
    --output data/database/sold_properties.parquet \
    --batch-size 1000 \
    --resume
```

---

## 🛡️ Risk Mitigation

### 1. 2,500 Result Limit ✅ SOLVED
**Solution:** Month-by-month filtering  
**Result:** Each month has <1,000 properties

### 2. Cloudflare Blocking
**Mitigation:**
- Session persistence (cookies saved)
- Human-like delays (5-10s between requests)
- Realistic browser config
- Can run in headed mode if needed

### 3. Long Running Time
**Mitigation:**
- Progress tracking and resume capability
- Can stop/start anytime
- Each month saved independently

### 4. GitHub Actions Limits
**Solution:** Run locally for historical backfill  
**Reason:** 
- 10 hours of scraping = $10 worth of Actions minutes
- Local is free and more reliable

---

## 📁 File Structure After Backfill

```
data/
├── raw/
│   ├── sold_links/                    # Link collection
│   │   ├── sold_links_202001.csv
│   │   ├── sold_links_202002.csv
│   │   ├── ...
│   │   ├── backfill_progress.json
│   │   └── backfill_summary.json
│   │
│   └── sold_properties/                # Property details (tomorrow)
│       ├── batch_0001.parquet
│       ├── batch_0002.parquet
│       └── ...
│
└── database/
    └── malmo_housing.duckdb           # Final database
```

---

## ✅ Checklist

### Today (Link Collection)
- [x] Create `backfill_sold_links.py` script
- [x] Document strategy in checklist
- [ ] Test script with 3 months (`--test` flag)
- [ ] Run full backfill locally
- [ ] Verify all months collected
- [ ] Check summary statistics

### Tomorrow (Property Details)
- [ ] Create `scrape_sold_properties_details.py`
- [ ] Implement batch processing
- [ ] Add resume capability
- [ ] Test on small batch (100 properties)
- [ ] Run full scrape (56k properties)
- [ ] Load into DuckDB database

### Next Week (Analysis)
- [ ] Validate data quality
- [ ] Create historical views
- [ ] Generate initial analytics
- [ ] Train ML models

---

## 🎓 Lessons Learned

### ✅ What Worked Well

1. **Time-based filtering:** Elegant solution to pagination limit
2. **Two-phase approach:** Separates concerns, enables resume
3. **Progress tracking:** Can stop/start without losing work
4. **Session persistence:** Reduces Cloudflare challenges

### 📝 Design Principles

1. **Idempotent:** Can run multiple times safely
2. **Resumable:** Never lose progress
3. **Observable:** Clear progress tracking
4. **Efficient:** Minimize unnecessary work

---

## 📈 Success Metrics

### Link Collection Phase
- ✅ All 60 months scraped successfully
- ✅ ~56,000 unique property links
- ✅ No missing months
- ✅ Average <500 properties per month

### Property Details Phase (Tomorrow)
- ⏳ All 56,000 properties scraped
- ⏳ <1% failure rate
- ⏳ Complete data for all fields
- ⏳ Successfully loaded into DuckDB

---

**Next Steps:**
1. Test the script with 3 months
2. Run full backfill if test passes
3. Tomorrow: Create property detail scraper
4. Load into database and celebrate! 🎉
