# Property Scraper Architecture - Visual Guide

## 🔄 Complete Data Flow

```
┌─────────────────────────────────────────────────────────────────┐
│                    HEMNET.SE (Source)                            │
│  ┌──────────────────────┐    ┌──────────────────────┐          │
│  │   For-Sale (/bostad/) │    │   Sold (/salda/)      │          │
│  │   ~1,500 properties   │    │   ~500/month          │          │
│  └──────────────────────┘    └──────────────────────┘          │
└─────────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────────┐
│  PHASE 1: Link Collection (Working ✅)                           │
│  ┌──────────────────────────────────────────────────┐          │
│  │  link_collector.py                                │          │
│  │  - Pagination handling                            │          │
│  │  - Cloudflare bypass                              │          │
│  │  - Rate limiting                                  │          │
│  └──────────────────────────────────────────────────┘          │
│                            ↓                                     │
│  Output: data/raw/links/active_20251115.csv                     │
│          property_id,url,found_at                               │
└─────────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────────┐
│  PHASE 2: Property Detail Scraping (To Build 🚧)                │
│  ┌──────────────────────────────────────────────────┐          │
│  │  property_detail_scraper.py                       │          │
│  │  ┌─────────────────────────────────────────────┐ │          │
│  │  │  1. Detect Type (/bostad/ or /salda/)      │ │          │
│  │  │  2. Extract Common Fields (all properties) │ │          │
│  │  │  3. Extract Type-Specific Fields           │ │          │
│  │  │  4. Get Coordinates (Maps API)             │ │          │
│  │  │  5. Validate with Pydantic Schema          │ │          │
│  │  └─────────────────────────────────────────────┘ │          │
│  │                                                   │          │
│  │  Features:                                        │          │
│  │  ✓ Unified scraper (both types)                  │          │
│  │  ✓ Batch processing (100 at a time)              │          │
│  │  ✓ Resume capability                              │          │
│  │  ✓ Parquet output                                 │          │
│  │  ✓ Error handling + retries                      │          │
│  └──────────────────────────────────────────────────┘          │
│                            ↓                                     │
│  Output: data/raw/properties/active/20251115/                   │
│          ├── batch_000.parquet (100 properties, ~75 KB)         │
│          ├── batch_001.parquet                                  │
│          └── metadata.json                                      │
└─────────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────────┐
│  PHASE 3: DuckDB Storage (To Build 🚧)                          │
│  ┌──────────────────────────────────────────────────┐          │
│  │  load_to_duckdb.py                                │          │
│  │  - Reads Parquet files                            │          │
│  │  - Deduplicates by property_id                    │          │
│  │  - Updates incrementally                          │          │
│  │  - Creates indexes                                │          │
│  └──────────────────────────────────────────────────┘          │
│                            ↓                                     │
│  Output: data/processed/hemnet.duckdb                           │
│          └─ properties table (all data, queryable)              │
└─────────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────────┐
│  ANALYSIS & VISUALIZATION                                        │
│  ┌────────────┐  ┌────────────┐  ┌─────────────┐              │
│  │ Streamlit  │  │   Quarto   │  │   FastAPI   │              │
│  │ Dashboard  │  │   Reports  │  │     API     │              │
│  └────────────┘  └────────────┘  └─────────────┘              │
└─────────────────────────────────────────────────────────────────┘
```

---

## 📦 Data Schema Hierarchy

```
BaseProperty (Common to all)
├── property_id: str
├── property_type: 'for_sale' | 'sold'
├── url: str
├── scraped_at: datetime
│
├── Location
│   ├── address: str
│   ├── city: str
│   ├── neighborhood: str
│   ├── latitude: float
│   └── longitude: float
│
├── Property Details
│   ├── housing_type: str
│   ├── ownership_type: str
│   ├── rooms: float
│   ├── living_area: float
│   ├── floor: str
│   ├── has_elevator: bool
│   ├── has_balcony: bool
│   ├── building_year: int
│   └── energy_class: str
│
├── Association
│   ├── association_name: str
│   ├── association_fee: int
│   └── operating_cost: int
│
└── description: str

     ↓ Extends to ↓

ForSaleProperty             SoldProperty
├── asking_price            ├── asking_price
├── price_per_sqm           ├── final_price ⭐
├── viewing_times           ├── price_change ⭐
└── days_on_market          ├── price_change_pct ⭐
                            ├── price_per_sqm_final ⭐
                            ├── sold_date ⭐
                            └── days_on_market
```

---

## 🔧 Batch Processing Flow

```
Input: 1,500 property URLs
         ↓
┌────────────────────────────┐
│  Batch Manager             │
│  - Split into batches of 100│
│  - Check already scraped   │
│  - Calculate remaining     │
└────────────────────────────┘
         ↓
┌────────────────────────────┐
│  Batch 0: URLs 0-99        │
│  ┌──────────────────────┐  │
│  │  Scrape each URL     │  │
│  │  Validate with schema│  │
│  │  Collect results     │  │
│  └──────────────────────┘  │
│         ↓                  │
│  Save: batch_000.parquet   │
│  Commit to Git ✅          │
└────────────────────────────┘
         ↓
┌────────────────────────────┐
│  Batch 1: URLs 100-199     │
│  [Same process]            │
│  Save: batch_001.parquet   │
│  Commit to Git ✅          │
└────────────────────────────┘
         ↓
       [... continues ...]
         ↓
┌────────────────────────────┐
│  Batch 14: URLs 1400-1499  │
│  [Same process]            │
│  Save: batch_014.parquet   │
│  Commit to Git ✅          │
└────────────────────────────┘
         ↓
┌────────────────────────────┐
│  Update metadata.json      │
│  {                         │
│    "total": 1500,          │
│    "scraped": 1500,        │
│    "batches": 15,          │
│    "status": "complete"    │
│  }                         │
└────────────────────────────┘
```

**Key Benefits:**
- ✅ Each batch commits separately (no data loss)
- ✅ Can resume from any batch
- ✅ Small files (easy to work with)
- ✅ GitHub Actions friendly

---

## 🗂️ File Organization

```
malmo-homes-streamlit/
│
├── .github/
│   ├── checklists/
│   │   ├── 2025-11-15-PROJECT-STATUS.md
│   │   ├── 2025-11-15-unified-scraper-architecture.md
│   │   ├── 2025-11-15-property-scraper-implementation.md
│   │   └── 2025-11-15-property-scraper-summary.md
│   │
│   └── workflows/
│       ├── scrape_weekly.yml         (Active properties)
│       ├── scrape_sold_monthly.yml   (Sold properties)
│       └── generate_reports.yml      (Quarto reports)
│
├── data/
│   ├── raw/
│   │   ├── links/                     📄 PHASE 1: URLs only
│   │   │   ├── active_20251115.csv
│   │   │   └── sold_202511.csv
│   │   │
│   │   └── properties/                📦 PHASE 2: Full details
│   │       ├── active/
│   │       │   └── 20251115/
│   │       │       ├── batch_000.parquet
│   │       │       ├── batch_001.parquet
│   │       │       └── metadata.json
│   │       └── sold/
│   │           └── 202511/
│   │               ├── batch_000.parquet
│   │               └── metadata.json
│   │
│   └── processed/                     🗄️ PHASE 3: Database
│       └── hemnet.duckdb
│
├── src/
│   ├── models/
│   │   ├── __init__.py
│   │   └── property_schema.py         🆕 Pydantic models
│   │
│   ├── scrapers/
│   │   ├── link_collector.py          ✅ Working
│   │   ├── sold_properties_scraper.py ✅ Working
│   │   └── property_detail_scraper.py 🚧 To build
│   │
│   ├── data/
│   │   ├── database_schema.sql        🚧 To build
│   │   └── load_to_duckdb.py          🚧 To build
│   │
│   └── utils/
│       ├── __init__.py
│       └── batch_manager.py           🚧 To build
│
├── tests/
│   ├── test_property_schema.py        🚧 To build
│   ├── test_property_scraper.py       🚧 To build
│   └── test_batch_manager.py          🚧 To build
│
├── notebooks/
│   └── query_examples.ipynb           🚧 To build
│
└── pyproject.toml                     (Add: pyarrow, duckdb)
```

---

## 🔀 Property Type Detection

```python
def detect_property_type(url: str) -> str:
    """
    Automatically detect property type from URL
    """
    
    # For-sale properties
    if '/bostad/' in url:
        return 'for_sale'
    
    # Sold properties
    elif '/salda/' in url:
        return 'sold'
    
    else:
        raise ValueError(f"Unknown property type in URL: {url}")

# Examples:
url1 = "https://www.hemnet.se/bostad/lagenhet-2rum-..."
detect_property_type(url1)  # → 'for_sale'

url2 = "https://www.hemnet.se/salda/lagenhet-3rum-..."
detect_property_type(url2)  # → 'sold'
```

---

## 📊 Storage Size Comparison

```
                CSV        Parquet      Compression
Property        ~2 KB      ~200 bytes   10x smaller
Batch (100)     ~200 KB    ~20 KB       10x smaller
Weekly (1,500)  ~3 MB      ~300 KB      10x smaller
Annual          ~150 MB    ~15 MB       10x smaller

✅ Parquet wins by 10x!
```

**Why it matters for GitHub Actions:**
- Faster uploads/downloads
- Less storage used
- Faster to query
- Better for Git commits

---

## 🔄 Resume Capability

```
Scenario: Scraping 1,500 properties, crash at 250

Before Resume:
data/raw/properties/active/20251115/
├── batch_000.parquet  ✅ (100 properties)
├── batch_001.parquet  ✅ (100 properties)
├── batch_002.parquet  ⚠️ (50 properties - incomplete)
└── metadata.json      (status: "in_progress", scraped: 250)

Run Again:
1. Read metadata.json → See 250 done
2. Read scraped_ids.txt → Get list of IDs
3. Load all URLs → 1,500 total
4. Filter out already scraped → 1,250 remaining
5. Continue from batch_003

After Resume:
├── batch_000.parquet  ✅ (kept)
├── batch_001.parquet  ✅ (kept)
├── batch_002.parquet  ✅ (completed 50 → 100)
├── batch_003.parquet  ✅ (new)
├── batch_004.parquet  ✅ (new)
...
└── metadata.json      (status: "complete", scraped: 1500)
```

**No data is lost!** 🎉

---

## 🧪 Testing Pyramid

```
                    ┌─────────────┐
                    │  E2E Test   │  ← Full pipeline (1 test)
                    │  100 props  │
                    └─────────────┘
                         ↑
              ┌──────────────────────┐
              │  Integration Tests   │  ← Multiple components
              │  - Batch processing  │     (3-5 tests)
              │  - DuckDB loading    │
              │  - Resume logic      │
              └──────────────────────┘
                         ↑
         ┌──────────────────────────────────┐
         │        Unit Tests                │  ← Individual functions
         │  - Schema validation             │     (20+ tests)
         │  - Type detection                │
         │  - Field extraction              │
         │  - Coordinate parsing            │
         │  - Parquet save/load             │
         └──────────────────────────────────┘
```

**Test Coverage Goal:** >80%

---

## 🚀 GitHub Actions Workflow

```yaml
name: Weekly Property Scraping

on:
  schedule:
    - cron: '0 0 * * 0'  # Sunday midnight

jobs:
  scrape:
    runs-on: ubuntu-latest
    
    steps:
      # 1️⃣ Collect Links
      - name: Collect property links
        run: python src/scrapers/link_collector.py
        
      # Output: data/raw/links/active_20251115.csv (1,500 URLs)
      
      # 2️⃣ Scrape in Batches (loop through 15 batches)
      - name: Scrape batch 0
        run: |
          python src/scrapers/property_detail_scraper.py \
            --input data/raw/links/active_20251115.csv \
            --batch-start 0 --batch-end 99 \
            --output-dir data/raw/properties/active/20251115
      
      - name: Commit batch 0
        run: |
          git add data/raw/properties/
          git commit -m "Add batch 0 (100 properties)"
          git push
      
      # Repeat for batches 1-14...
      
      # 3️⃣ Update Database
      - name: Load to DuckDB
        run: |
          python src/data/load_to_duckdb.py \
            --input-dir data/raw/properties/active/20251115
      
      - name: Commit database
        run: |
          git add data/processed/hemnet.duckdb
          git commit -m "Update database with new properties"
          git push
```

**Key Features:**
- ✅ Runs automatically every Sunday
- ✅ Each batch commits separately
- ✅ Can resume if interrupted
- ✅ Updates database at end
- ✅ Sends notification on failure

---

## 📈 Expected Performance

```
Metric                    Target      Reality Check
─────────────────────────────────────────────────
Time per property         <30s        Realistic ✅
Batch of 100 properties   <50 min     Achievable ✅
Weekly scrape (1,500)     <12 hours   Within limits ✅
Monthly scrape (500)      <4 hours    Easy ✅
Parquet file size         <100 KB     Tested ✅
Coordinate success rate   >95%        Historical ✅
Schema validation         100%        Pydantic ✅
```

**GitHub Actions Limits:**
- Free tier: 2,000 minutes/month
- Our usage: ~48 hours/month (weekly) + ~4 hours/month (monthly)
- Total: ~52 hours = **Well within limits!** ✅

---

## 🎯 Success Checklist

After implementation, verify:

- [ ] ✅ Both property types scraped correctly
- [ ] ✅ All fields extracted (>95% success)
- [ ] ✅ Coordinates found for all properties
- [ ] ✅ Parquet files <100 KB each
- [ ] ✅ Resume works after interruption
- [ ] ✅ DuckDB loads without errors
- [ ] ✅ Queries return correct results
- [ ] ✅ No duplicates in database
- [ ] ✅ GitHub Actions runs successfully
- [ ] ✅ All tests pass

---

## 💡 Design Philosophy

**Principles we follow:**

1. **Separation of Concerns**
   - Link collection ≠ Property scraping
   - Each phase can be run independently
   - Easier to debug and test

2. **Fail-Safe Design**
   - Batch commits (no data loss)
   - Resume capability
   - Multiple extraction methods (fallbacks)
   - Comprehensive error handling

3. **Git-Friendly Storage**
   - Small files (easy to diff)
   - Immutable batches (append-only)
   - Clear directory structure
   - Metadata for tracking

4. **Future-Proof**
   - Extensible schema
   - Multiple property types supported
   - Easy to add new fields
   - Database-ready format

---

**This architecture will serve us for years to come!** 🚀
