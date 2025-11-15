# Unified Property Scraper Architecture

**Date:** 2025-11-15  
**Status:** Planning Phase  

---

## 🎯 Objective

Design and implement a unified property scraping system that handles both **for-sale** and **sold** properties efficiently, with proper data storage for DuckDB on GitHub Actions.

---

## 📊 Key Differences Analysis

### For-Sale Properties (`/bostad/`)

**Available Data:**
- ✅ Asking price (utgångspris)
- ✅ Monthly fee (avgift)
- ✅ Living area (boarea)
- ✅ Rooms
- ✅ Floor/elevator info
- ✅ Building year
- ✅ Energy class
- ✅ Association (BRF) info
- ✅ Viewing times
- ✅ Visit statistics
- ✅ Full property description
- ✅ **Coordinates** (from Maps API)
- ❌ ~~Final sold price~~
- ❌ ~~Sold date~~
- ❌ ~~Days on market~~

**URL Pattern:**
```
https://www.hemnet.se/bostad/lagenhet-2rum-slottsstaden-malmo-kommun-ostra-stallmastaregatan-5b-21629409
```

**Unique ID:** `21629409` (numeric, shorter)

---

### Sold Properties (`/salda/`)

**Available Data:**
- ✅ **Final sold price** (slutpris)
- ✅ **Sold date**
- ✅ Asking price (utgångspris)
- ✅ Price development (+/- percentage)
- ✅ Price per m²
- ✅ Monthly fee (avgift)
- ✅ Living area (boarea)
- ✅ Rooms
- ✅ Floor/elevator info
- ✅ Building year
- ✅ Visit count (historical)
- ✅ Full property description
- ✅ **Coordinates** (should be in `__NEXT_DATA__`)
- ❌ ~~Current viewing times~~
- ❌ ~~Live statistics~~

**URL Pattern:**
```
https://www.hemnet.se/salda/lagenhet-3rum-vastra-hamnen-malmo-kommun-stormastgatan-5-6303039936076543572
```

**Unique ID:** `6303039936076543572` (much longer alphanumeric)

---

## 🏗️ Proposed Architecture

### 1. **Two-Phase Approach**

#### Phase 1: Link Collection (Current)
- ✅ Already working for both types
- Collects URLs only
- Lightweight, fast
- Output: CSV with URLs

#### Phase 2: Property Detail Scraping (NEW)
- Takes URLs from Phase 1
- Extracts full property data
- Handles both property types
- Output: Parquet files for DuckDB

---

### 2. **Data Schema Design**

#### Common Base Schema
All properties share these fields:
```python
{
    'property_id': str,          # Extracted from URL
    'property_type': str,        # 'for_sale' or 'sold'
    'url': str,
    'scraped_at': datetime,
    
    # Location
    'address': str,
    'city': str,
    'neighborhood': str,
    'latitude': float,
    'longitude': float,
    
    # Property Details
    'housing_type': str,         # Lägenhet, Villa, etc.
    'ownership_type': str,       # Bostadsrätt, Äganderätt
    'rooms': float,
    'living_area': float,
    'lot_area': float,           # For houses
    'floor': str,
    'has_elevator': bool,
    'has_balcony': bool,
    'building_year': int,
    'energy_class': str,
    
    # Association
    'association_name': str,
    'association_fee': int,
    'operating_cost': int,
    
    # Description
    'description': str,
}
```

#### For-Sale Specific Fields
```python
{
    'asking_price': int,
    'price_per_sqm': float,
    'viewing_times': list,       # JSON array
    'days_on_market': int,       # Calculate from listing date
    'visit_count': int,          # If available
}
```

#### Sold Specific Fields
```python
{
    'asking_price': int,
    'final_price': int,
    'price_change': int,         # final - asking
    'price_change_pct': float,
    'price_per_sqm_final': float,
    'sold_date': date,
    'days_on_market': int,       # If available
    'visit_count': int,          # Historical
}
```

---

### 3. **Storage Strategy**

#### File Structure
```
data/
├── raw/
│   ├── links/
│   │   ├── active_YYYYMMDD.csv          # Link collection Phase 1
│   │   └── sold_YYYYMM.csv
│   └── properties/
│       ├── active/
│       │   └── YYYYMMDD/
│       │       ├── batch_001.parquet    # 100 properties per file
│       │       ├── batch_002.parquet
│       │       └── metadata.json
│       └── sold/
│           └── YYYYMM/
│               ├── batch_001.parquet
│               └── metadata.json
└── processed/
    └── hemnet.duckdb                     # DuckDB database
```

#### Why Parquet + Batches?

1. **Small File Sizes:**
   - Parquet compression: ~10-20x smaller than CSV
   - 100 properties ≈ 50-100 KB per file
   - Easy to commit to Git

2. **GitHub Actions Friendly:**
   - Can scrape in batches (100 at a time)
   - Commit after each batch
   - Interrupted runs are resumable

3. **DuckDB Native:**
   - DuckDB reads Parquet directly
   - Can query across multiple files
   - No need to load everything into memory

4. **Incremental Updates:**
   - Only new batches are added
   - Old data stays untouched
   - Historical tracking is preserved

---

### 4. **Unified Property Scraper Design**

#### Single Scraper Class
```python
class HemnetPropertyScraper:
    """
    Unified scraper for both for-sale and sold properties.
    Automatically detects property type from URL.
    """
    
    def detect_property_type(self, url: str) -> str:
        """Detect if property is for-sale or sold"""
        return 'sold' if '/salda/' in url else 'for_sale'
    
    def scrape_property(self, url: str) -> Dict:
        """
        Main scraping method - handles both types.
        Returns unified schema with type-specific fields.
        """
        property_type = self.detect_property_type(url)
        
        # Common extraction logic
        data = self._extract_common_fields(page)
        
        # Type-specific extraction
        if property_type == 'sold':
            data.update(self._extract_sold_fields(page))
        else:
            data.update(self._extract_for_sale_fields(page))
        
        return data
    
    def scrape_batch(self, urls: List[str], batch_size: int = 100):
        """Scrape properties in batches"""
        for i in range(0, len(urls), batch_size):
            batch = urls[i:i+batch_size]
            properties = []
            
            for url in batch:
                properties.append(self.scrape_property(url))
            
            # Save batch to parquet
            self.save_batch_parquet(properties, batch_num=i//batch_size)
```

---

### 5. **GitHub Actions Workflow**

#### Weekly Active Properties
```yaml
name: Scrape Active Properties

on:
  schedule:
    - cron: '0 0 * * 0'  # Sunday 00:00 UTC
  workflow_dispatch:

jobs:
  scrape:
    runs-on: ubuntu-latest
    steps:
      # 1. Collect links
      - name: Collect property links
        run: python src/scrapers/link_collector.py
      
      # 2. Scrape in batches (100 at a time)
      - name: Scrape properties batch 1
        run: python src/scrapers/property_detail_scraper.py --batch 0-99
      
      # 3. Commit batch
      - name: Commit batch 1
        run: |
          git add data/raw/properties/active/
          git commit -m "Add active properties batch 1"
          git push
      
      # Repeat for all batches...
      
      # 4. Update DuckDB
      - name: Update database
        run: python src/data/update_database.py
```

#### Monthly Sold Properties
```yaml
# Similar structure but for sold properties
# Scrapes last month's sales
# Smaller batches (typically 500 properties/month)
```

---

## 🔧 Implementation Plan

### Step 1: Create Unified Schema ✓
- [x] Analyze differences between property types
- [ ] Define Pydantic models for validation
- [ ] Create type hints for all fields
- [ ] Document schema in README

### Step 2: Enhance Property Scraper
- [ ] Extend `property_scraper.py` to handle both types
- [ ] Add type detection from URL
- [ ] Implement sold-specific extraction
- [ ] Add error handling for missing fields
- [ ] Test on 10 properties of each type

### Step 3: Batch Processing
- [ ] Create batch management system
- [ ] Implement Parquet output
- [ ] Add resume capability (skip already scraped)
- [ ] Create metadata tracking
- [ ] Test batch scraping (100 properties)

### Step 4: DuckDB Integration
- [ ] Design database schema
- [ ] Create table structure
- [ ] Write Parquet → DuckDB loader
- [ ] Add incremental update logic
- [ ] Create query examples

### Step 5: GitHub Actions Integration
- [ ] Update weekly workflow for batches
- [ ] Update monthly workflow
- [ ] Add batch commit logic
- [ ] Test in Actions environment
- [ ] Add monitoring/alerting

### Step 6: Testing & Validation
- [ ] Unit tests for scraper
- [ ] Integration tests for batches
- [ ] Data quality validation
- [ ] Schema validation tests
- [ ] End-to-end workflow test

---

## 📏 Size Estimates

### For-Sale Properties
- Weekly: ~1,500 properties
- Batches: 15 files × 100 properties
- Size: 15 × 75 KB ≈ 1.1 MB/week
- Annual: ~55 MB

### Sold Properties
- Monthly: ~500 properties
- Batches: 5 files × 100 properties
- Size: 5 × 75 KB ≈ 375 KB/month
- Annual: ~4.5 MB

### Historical Backfill
- Total: ~56,000 properties
- Batches: 560 files
- Size: ~42 MB (highly compressed)
- One-time: Run locally and commit

**Total Storage (Year 1):** ~102 MB  
**GitHub Repo Limit:** 1 GB soft, 5 GB hard  
**✅ Well within limits!**

---

## 🎯 Success Metrics

### Data Quality
- [ ] >95% successful extractions
- [ ] Zero duplicate records
- [ ] All coordinates validated
- [ ] Schema violations = 0

### Performance
- [ ] <30 seconds per property
- [ ] <2 hours per weekly scrape
- [ ] <20 minutes per monthly scrape
- [ ] Zero Cloudflare blocks

### Reliability
- [ ] Automatic retry on failure
- [ ] Resume capability after errors
- [ ] No data loss on interruption
- [ ] Daily automated tests

---

## 🚨 Risk Mitigation

### 1. Cloudflare Protection
**Risk:** Blocks automated scraping  
**Mitigation:**
- Session persistence
- Realistic browser fingerprint
- Rate limiting (5-10s delays)
- Headed mode with Xvfb in Actions

### 2. Schema Changes
**Risk:** Hemnet changes HTML/API structure  
**Mitigation:**
- Flexible extraction with fallbacks
- Schema versioning
- Validation tests
- Alerts on extraction failures

### 3. GitHub Storage Limits
**Risk:** Repository becomes too large  
**Mitigation:**
- Parquet compression
- Monthly archive to Git LFS
- DuckDB as primary storage
- Option to move to external storage

### 4. Rate Limits
**Risk:** IP gets banned  
**Mitigation:**
- Conservative rate limits
- Random delays
- User-agent rotation
- Batch processing with pauses

---

## 📝 Next Actions

1. **Create Schema Models** (1 hour)
   - Pydantic models for validation
   - Type hints
   - Documentation

2. **Extend Property Scraper** (3 hours)
   - Add sold property support
   - Unified extraction
   - Testing suite

3. **Implement Batch System** (2 hours)
   - Parquet output
   - Resume logic
   - Metadata tracking

4. **Test End-to-End** (2 hours)
   - Scrape 100 properties
   - Validate data quality
   - Check file sizes

5. **Update Workflows** (1 hour)
   - Batch processing logic
   - Commit strategy
   - Error handling

**Total Estimated Time:** ~9 hours

---

## 💡 Design Decisions

### ✅ Chosen: Two-Phase Approach
- **Why:** Separation of concerns, resumable, testable
- **Alternative:** Single-phase scraping (too risky, no resume)

### ✅ Chosen: Parquet Format
- **Why:** Small size, DuckDB native, typed schema
- **Alternative:** CSV (10x larger, no types)

### ✅ Chosen: Batch Commits
- **Why:** Resume capability, incremental progress
- **Alternative:** Single commit (loses progress on failure)

### ✅ Chosen: Unified Scraper
- **Why:** Single codebase, easier maintenance
- **Alternative:** Two scrapers (code duplication)

### ✅ Chosen: DuckDB
- **Why:** Embedded, fast, SQL queries, Git-friendly
- **Alternative:** PostgreSQL (needs hosting, overkill)

---

**Status:** Ready to implement! 🚀  
**Priority:** High  
**Complexity:** Medium
