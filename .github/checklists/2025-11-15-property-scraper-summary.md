# Property Scraper Strategy - Executive Summary

**Date:** 2025-11-15  
**Status:** Planning Complete ✅  

---

## 🎯 The Challenge

You have a working link scraper that collects property URLs. Now you need to scrape the actual property details for:
1. **For-sale properties** (`/bostad/`) - currently listed
2. **Sold properties** (`/salda/`) - historical sales

These property types have different data fields, and we need to store everything efficiently for DuckDB on GitHub Actions.

---

## 💡 The Solution

### Three-Layer Architecture

```
┌─────────────────────────────────────────────────────┐
│  Layer 1: Link Collection (Working ✅)              │
│  Collects URLs only - lightweight & fast            │
│  Output: CSV with property URLs                     │
└─────────────────────────────────────────────────────┘
                         ↓
┌─────────────────────────────────────────────────────┐
│  Layer 2: Property Scraping (To Build)              │
│  Unified scraper for both property types            │
│  Extracts all fields + coordinates                  │
│  Output: Parquet files (batches of 100)             │
└─────────────────────────────────────────────────────┘
                         ↓
┌─────────────────────────────────────────────────────┐
│  Layer 3: DuckDB Storage (To Build)                 │
│  Loads Parquet → DuckDB                             │
│  Queryable SQL database                             │
│  Output: data/processed/hemnet.duckdb               │
└─────────────────────────────────────────────────────┘
```

---

## 📊 Key Differences Between Property Types

### For-Sale Properties
- **Asking price** (utgångspris)
- Viewing times
- Days on market
- Live statistics
- ❌ No final sold price

### Sold Properties  
- Asking price (utgångspris)
- **Final sold price** (slutpris)
- **Price change** (+/- %)
- **Sold date**
- Historical visit count
- ❌ No current viewings

### Common Fields (Both)
- Address, city, coordinates
- Rooms, area, floor
- Building year, energy class
- Association info, monthly fee
- Full description

---

## 🗄️ Storage Strategy: Why Parquet?

### Problem: GitHub Actions + Git Storage
- Weekly: 1,500 properties
- Monthly: 500 properties
- Can't have huge files in Git

### Solution: Parquet + Batching

**What is Parquet?**
- Columnar storage format (like a smart CSV)
- 10-20x smaller than CSV
- Native to DuckDB
- Preserves data types

**Batching Strategy:**
```
data/raw/properties/
├── active/20251115/
│   ├── batch_000.parquet    # 100 properties ≈ 75 KB
│   ├── batch_001.parquet
│   └── metadata.json
└── sold/202511/
    ├── batch_000.parquet
    └── metadata.json
```

**Benefits:**
1. Small files (easy to commit)
2. Resume if interrupted
3. No memory issues
4. Fast queries with DuckDB

**Size Estimates:**
- Per batch: ~75 KB (100 properties)
- Weekly: ~1.1 MB (1,500 properties)
- Annual: ~60 MB total
- **Well within GitHub limits!**

---

## 🏗️ Implementation Plan

### Phase 1: Data Models (1 hour)
Create Pydantic schemas for validation:
- `BaseProperty` - common fields
- `ForSaleProperty` - extends base
- `SoldProperty` - extends base

**Why Pydantic?**
- Automatic validation
- Type checking
- JSON export
- Clear documentation

---

### Phase 2: Unified Scraper (3 hours)
Extend current `property_scraper.py`:

```python
class HemnetPropertyScraper:
    def scrape_property(self, url: str):
        # Detects type from URL (/bostad/ or /salda/)
        property_type = self.detect_type(url)
        
        # Extract common fields (all properties)
        data = self.extract_common(page)
        
        # Extract type-specific fields
        if property_type == 'sold':
            data.update(self.extract_sold(page))
        else:
            data.update(self.extract_for_sale(page))
        
        return data
```

**Key Features:**
- Auto-detects property type
- Handles both `/bostad/` and `/salda/`
- Extracts coordinates (Maps API + fallback)
- Validates with Pydantic
- Retries on failure

---

### Phase 3: Batch Processing (2 hours)
Process properties in batches:

```python
# Read URLs from link collector
urls = load_csv("data/raw/links/active_20251115.csv")

# Scrape in batches of 100
for i in range(0, len(urls), 100):
    batch = scrape_batch(urls[i:i+100])
    save_parquet(batch, f"batch_{i//100:03d}.parquet")
    
    # Commit to Git after each batch
    git_commit(f"Add batch {i//100}")
```

**Features:**
- Resume capability (skip already scraped)
- Metadata tracking
- Error handling
- Progress reporting

---

### Phase 4: DuckDB Integration (1 hour)
Load Parquet files into DuckDB:

```sql
-- Create table
CREATE TABLE properties AS 
SELECT * FROM 'data/raw/properties/*/*.parquet';

-- Query examples
SELECT neighborhood, AVG(final_price) 
FROM properties 
WHERE property_type = 'sold'
GROUP BY neighborhood;
```

**Benefits:**
- SQL queries on all data
- Fast aggregations
- Join with other data
- No server needed (embedded)

---

## 📋 Detailed Checklists Created

I've created three documents for you:

### 1. **Architecture Document** 📐
`2025-11-15-unified-scraper-architecture.md`
- Full technical specification
- Data schema design
- Storage strategy
- Risk mitigation
- Design decisions

### 2. **Implementation Checklist** ✅
`2025-11-15-property-scraper-implementation.md`
- Task-by-task breakdown
- 6 implementation sessions
- Testing protocols
- Success criteria
- Time estimates

### 3. **Updated Project Status** 📊
`2025-11-15-PROJECT-STATUS.md`
- Updated next steps
- Current capabilities
- Progress tracking

---

## 🧪 Testing Strategy

### Test Each Component

1. **Schema Validation** (15 min)
   - Valid properties pass
   - Invalid data rejected
   - Type coercion works

2. **Single Property** (30 min)
   - Test for-sale property
   - Test sold property
   - Verify coordinates
   - Check all fields

3. **Batch Processing** (30 min)
   - Scrape 20 properties
   - Check file sizes
   - Verify no duplicates

4. **Resume Logic** (15 min)
   - Interrupt scraping
   - Resume - verify skips done
   - Check metadata

5. **DuckDB Load** (30 min)
   - Load batches to DB
   - Run queries
   - Check data integrity

---

## 📏 Success Metrics

### Data Quality
- ✅ >95% extraction success
- ✅ All coordinates found
- ✅ Zero duplicates
- ✅ Schema validation passes

### Performance  
- ✅ <30s per property
- ✅ <75 KB per batch file
- ✅ Resume works perfectly
- ✅ No Cloudflare blocks

### Reliability
- ✅ Handles interruptions
- ✅ No data loss
- ✅ Automatic retries
- ✅ Clear error messages

---

## 🚀 Next Actions

### Immediate (Today)
1. Review architecture document
2. Validate approach
3. Approve implementation plan
4. Start with Phase 1 (Data Models)

### This Week
1. Complete all 6 implementation sessions
2. Test with 100 real properties
3. Validate data quality
4. Update GitHub Actions workflows

### Next Week
1. Run first full scrape (1,500 properties)
2. Monitor for issues
3. Begin historical backfill planning
4. Create Streamlit dashboard prototype

---

## 💬 Questions to Consider

1. **Batch Size:** Is 100 properties per batch good? (Can adjust to 50 or 200)
2. **Storage:** Keep Parquet files in Git or move older ones to Git LFS?
3. **Backfill:** Run 56k historical properties locally or in batches on Actions?
4. **Coordinates:** Accept properties without coordinates or skip them?

---

## 📚 Documents Created

All planning documents are in `.github/checklists/`:

1. `2025-11-15-unified-scraper-architecture.md` - Full technical spec
2. `2025-11-15-property-scraper-implementation.md` - Detailed checklist
3. `2025-11-15-PROJECT-STATUS.md` - Updated status
4. `2025-11-15-property-scraper-summary.md` - This document

---

## 🎯 The Bottom Line

**What we're building:**
A production-ready property scraper that:
- Handles both for-sale and sold properties
- Saves data efficiently (Parquet format)
- Works on GitHub Actions (small batches)
- Stores in DuckDB (fast queries)
- Resumes after interruptions
- Scales to 100k+ properties

**Time to build:** ~9 hours (6 sessions)  
**Storage needed:** ~60 MB/year  
**Complexity:** Medium  
**Risk:** Low (well-planned)

**Ready to start?** Begin with Session 1: Data Models 🚀

---

**Status:** Planning Complete ✅  
**Next Step:** Create Pydantic schemas  
**Estimated Time:** 1 hour
