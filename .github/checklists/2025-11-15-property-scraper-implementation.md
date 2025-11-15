# Property Scraper Implementation Checklist

**Date:** 2025-11-15  
**Task:** Implement unified property detail scraper  
**Estimated Time:** 9 hours  
**Priority:** High  

---

## 📋 Task Breakdown

### Task 1: Data Models & Schema (1 hour)

#### 1.1 Create Pydantic Models
- [ ] Create `src/models/property_schema.py`
- [ ] Define `BaseProperty` model (common fields)
- [ ] Define `ForSaleProperty` model (inherits Base)
- [ ] Define `SoldProperty` model (inherits Base)
- [ ] Add field validators (price > 0, coords valid, etc.)
- [ ] Add JSON schema export
- [ ] Document all fields with examples

**Files to create:**
- `src/models/__init__.py`
- `src/models/property_schema.py`

**Tests:**
```python
# Valid property passes validation
# Invalid coordinates rejected
# Missing required fields caught
# Type coercion works (str → int)
```

---

### Task 2: Enhanced Property Scraper (3 hours)

#### 2.1 Extend Current Scraper
- [ ] Rename `property_scraper.py` → `property_detail_scraper.py`
- [ ] Add `detect_property_type(url)` method
- [ ] Create `_extract_common_fields(page)` method
- [ ] Create `_extract_sold_fields(page)` method
- [ ] Create `_extract_for_sale_fields(page)` method
- [ ] Update coordinate extraction for sold properties
- [ ] Add retry logic (3 attempts)
- [ ] Add validation using Pydantic models

#### 2.2 Sold Property Extraction
Based on webpage analysis, sold properties have:
```python
{
    'final_price': int,          # "Slutpris 3 095 000 kr"
    'asking_price': int,         # "Utgångspris 2 995 000 kr"
    'price_change': int,         # Calculate: final - asking
    'price_change_pct': float,   # "Prisutveckling +100 000 kr (+3 %)"
    'price_per_sqm': float,      # "45 515 kr/m²"
    'sold_date': date,           # "Såld 15 november 2025"
    'visit_count': int,          # "1138" (from stats)
}
```

Extract from `__NEXT_DATA__`:
```javascript
// Look for sold-specific fields
property.soldPrice
property.askingPrice  
property.soldAt
property.statistics.visits
```

#### 2.3 For-Sale Property Extraction
Already mostly working, ensure:
```python
{
    'asking_price': int,
    'price_per_sqm': float,      # Calculate if not provided
    'viewing_times': list,       # Extract all viewing times
    'days_on_market': int,       # Calculate from listed_at
}
```

**Files to modify:**
- `src/scrapers/property_scraper.py` → `src/scrapers/property_detail_scraper.py`

**Tests:**
- [ ] Test on for-sale property URL
- [ ] Test on sold property URL
- [ ] Test coordinate extraction (both types)
- [ ] Test with Cloudflare challenge
- [ ] Test with missing fields
- [ ] Validate output against schema

---

### Task 3: Batch Processing System (2 hours)

#### 3.1 Create Batch Manager
- [ ] Create `src/utils/batch_manager.py`
- [ ] `BatchManager` class with methods:
  - `create_batch(urls, batch_size=100)`
  - `save_batch_parquet(properties, batch_id)`
  - `load_scraped_ids()` - get already scraped
  - `get_remaining_urls(all_urls)` - resume support
  - `save_metadata(batch_info)` - tracking

#### 3.2 Parquet Output
- [ ] Install `pyarrow` for Parquet support
- [ ] Create `to_parquet()` method in scraper
- [ ] Test compression (snappy vs gzip)
- [ ] Validate schema preservation
- [ ] Test with 100 properties

#### 3.3 Resume Capability
- [ ] Track scraped property IDs in metadata
- [ ] Skip already-scraped URLs
- [ ] Resume from last batch
- [ ] Handle partial batches

**Files to create:**
- `src/utils/__init__.py`
- `src/utils/batch_manager.py`

**Data structure:**
```
data/raw/properties/
├── active/
│   └── 20251115/
│       ├── batch_000.parquet (100 properties)
│       ├── batch_001.parquet
│       ├── metadata.json
│       └── scraped_ids.txt
└── sold/
    └── 202511/
        ├── batch_000.parquet
        └── metadata.json
```

**metadata.json:**
```json
{
  "scrape_date": "2025-11-15",
  "property_type": "active",
  "total_urls": 1500,
  "scraped": 200,
  "batches": 2,
  "last_batch": 1,
  "status": "in_progress",
  "errors": []
}
```

---

### Task 4: CLI & Testing (2 hours)

#### 4.1 Command Line Interface
- [ ] Add argparse to `property_detail_scraper.py`
- [ ] Arguments:
  - `--input`: CSV file with URLs
  - `--batch-start`: Start batch number
  - `--batch-end`: End batch number
  - `--batch-size`: Properties per batch (default: 100)
  - `--output-dir`: Output directory
  - `--headless`: Run headless
  - `--test`: Test mode (10 properties)

#### 4.2 Test Suite
- [ ] Create `tests/test_property_scraper.py`
- [ ] Test URL type detection
- [ ] Test field extraction (mocked HTML)
- [ ] Test batch creation
- [ ] Test Parquet save/load
- [ ] Test resume logic
- [ ] Test error handling

#### 4.3 Integration Test
- [ ] Scrape 10 for-sale properties
- [ ] Scrape 10 sold properties  
- [ ] Validate all have coordinates
- [ ] Check Parquet file size
- [ ] Verify schema compliance
- [ ] Test batch resume

**Test URLs (save these):**
```python
TEST_URLS = {
    'for_sale': [
        'https://www.hemnet.se/bostad/lagenhet-2rum-slottsstaden-malmo-kommun-ostra-stallmastaregatan-5b-21629409',
        # Add 9 more
    ],
    'sold': [
        'https://www.hemnet.se/salda/lagenhet-3rum-vastra-hamnen-malmo-kommun-stormastgatan-5-6303039936076543572',
        # Add 9 more
    ]
}
```

---

### Task 5: DuckDB Integration (1 hour)

#### 5.1 Database Schema
- [ ] Create `src/data/database_schema.sql`
- [ ] Define `properties` table
- [ ] Define indexes (location, price, date)
- [ ] Create views (active, sold, recent)

#### 5.2 Data Loader
- [ ] Create `src/data/load_to_duckdb.py`
- [ ] `load_parquet_batch(file_path)` method
- [ ] `update_database(batch_dir)` method
- [ ] Deduplication logic
- [ ] Incremental update support

#### 5.3 Query Examples
- [ ] Create `notebooks/query_examples.ipynb`
- [ ] Example: Get average price by neighborhood
- [ ] Example: Price trends over time
- [ ] Example: Properties by price range
- [ ] Example: Sold vs asking price analysis

**Files to create:**
- `src/data/database_schema.sql`
- `src/data/load_to_duckdb.py`
- `notebooks/query_examples.ipynb`

---

## 🧪 Testing Protocol

### Test 1: Schema Validation (15 min)
```bash
# Test Pydantic models
pytest tests/test_property_schema.py -v
```

**Expected:**
- All validation tests pass
- Invalid data rejected
- Type coercion works

---

### Test 2: Single Property Scraping (30 min)
```bash
# Test for-sale property
python src/scrapers/property_detail_scraper.py \
  --url "https://www.hemnet.se/bostad/..." \
  --test

# Test sold property
python src/scrapers/property_detail_scraper.py \
  --url "https://www.hemnet.se/salda/..." \
  --test
```

**Expected:**
- ✅ Property type detected correctly
- ✅ All common fields extracted
- ✅ Type-specific fields extracted
- ✅ Coordinates found
- ✅ Schema validation passes
- ✅ Output saved to Parquet

---

### Test 3: Batch Processing (30 min)
```bash
# Create test CSV with 20 URLs (10 each type)
# Run batch scraper
python src/scrapers/property_detail_scraper.py \
  --input data/test_urls.csv \
  --batch-size 10 \
  --output-dir data/test_output \
  --test
```

**Expected:**
- ✅ 2 batch files created
- ✅ Each file has 10 properties
- ✅ File size < 100 KB per batch
- ✅ Metadata.json created
- ✅ No duplicate properties

---

### Test 4: Resume Capability (15 min)
```bash
# Interrupt scraping after first batch
# Run again with same input
python src/scrapers/property_detail_scraper.py \
  --input data/test_urls.csv \
  --batch-size 10 \
  --output-dir data/test_output \
  --resume
```

**Expected:**
- ✅ First batch skipped
- ✅ Second batch scraped
- ✅ Metadata updated
- ✅ No duplicates

---

### Test 5: DuckDB Integration (30 min)
```bash
# Load test batches into DuckDB
python src/data/load_to_duckdb.py \
  --input-dir data/test_output \
  --database data/test.duckdb
```

**Expected:**
- ✅ All 20 properties loaded
- ✅ No duplicates
- ✅ Schema matches
- ✅ Queries work

---

## 📦 Dependencies to Add

Update `pyproject.toml`:
```toml
[project]
dependencies = [
    "playwright>=1.40.0",
    "pydantic>=2.5.0",
    "pyarrow>=14.0.0",      # Parquet support
    "duckdb>=0.9.0",        # Database
    "pandas>=2.1.0",        # Data manipulation
    "python-dateutil>=2.8.2",
]

[project.optional-dependencies]
dev = [
    "pytest>=7.4.0",
    "pytest-cov>=4.1.0",
    "black>=23.0.0",
    "ruff>=0.1.0",
]
```

Install:
```bash
uv pip install pyarrow duckdb pandas python-dateutil
```

---

## 📊 Success Criteria

### Code Quality
- [ ] All tests pass (100% pass rate)
- [ ] Type hints on all functions
- [ ] Docstrings on all public methods
- [ ] No hardcoded values (use config)
- [ ] Error handling throughout

### Data Quality
- [ ] >95% extraction success rate
- [ ] All properties have coordinates
- [ ] No duplicate records
- [ ] Schema validation passes
- [ ] Price data reasonable (>0, <50M SEK)

### Performance
- [ ] <30s per property average
- [ ] <50 KB per batch file
- [ ] Resume works correctly
- [ ] No memory leaks

### Documentation
- [ ] README updated with usage examples
- [ ] Schema documented
- [ ] CLI help text complete
- [ ] Query examples provided

---

## 🚀 Execution Plan

### Session 1: Data Models (1 hour)
1. Create `src/models/property_schema.py`
2. Define Pydantic models
3. Write validation tests
4. Test and validate

**Deliverable:** Working schema with tests

---

### Session 2: Scraper Extension (1.5 hours)
1. Extend `property_scraper.py`
2. Add type detection
3. Implement sold property extraction
4. Test on sample URLs

**Deliverable:** Scraper handles both types

---

### Session 3: Batch System (1.5 hours)
1. Create `batch_manager.py`
2. Implement Parquet output
3. Add resume logic
4. Test with 20 properties

**Deliverable:** Working batch system

---

### Session 4: CLI & Integration (1 hour)
1. Add argparse CLI
2. Write integration tests
3. Test end-to-end flow
4. Fix any issues

**Deliverable:** Complete scraper with CLI

---

### Session 5: DuckDB & Docs (1 hour)
1. Create database schema
2. Write data loader
3. Test database integration
4. Update documentation

**Deliverable:** Full pipeline working

---

### Session 6: Real-World Test (1 hour)
1. Scrape 100 real properties
2. Validate data quality
3. Check file sizes
4. Performance profiling
5. Fix any issues

**Deliverable:** Production-ready scraper

---

## 📝 Notes & Decisions

### Parquet vs CSV
**Chosen:** Parquet
- 10-20x smaller file size
- Type preservation
- Fast loading
- DuckDB native

### Batch Size
**Chosen:** 100 properties per batch
- ~50-75 KB per file
- Good balance for resume
- Easy to commit to Git

### Resume Strategy
**Chosen:** Track scraped IDs in metadata
- Simple text file
- Fast lookup
- No database needed

### Coordinate Extraction
**Approach:** Try both methods
1. Network interception (primary)
2. `__NEXT_DATA__` (fallback)
3. Geocoding API (last resort)

---

## ⚠️ Known Risks

### Risk 1: Sold Properties Have Different Structure
**Mitigation:** Test thoroughly on multiple sold properties, have flexible extraction with fallbacks

### Risk 2: Parquet Files Too Large
**Mitigation:** Adjust batch size, test compression options

### Risk 3: Coordinates Missing on Sold
**Mitigation:** Multiple extraction methods, fallback to geocoding

### Risk 4: GitHub Actions Timeout
**Mitigation:** Process in smaller batches, add resume capability

---

**Status:** Ready to implement  
**Next:** Start with Session 1 (Data Models)  
**Time Tracking:** Update after each session
