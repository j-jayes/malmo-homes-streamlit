# Project Components Overview

**Date:** 2025-11-15  
**Status:** Architecture Clarified ✅

---

## 🎯 Two Distinct But Connected Components

This project consists of **two separate workflows** that serve different purposes but work together:

---

## 🏛️ Component 1: Historical Market Database

### Purpose
Build a comprehensive historical dataset to understand the market baseline and train ML models.

### Scope
- **Data:** Sold properties from 2020-present
- **Volume:** ~56,000 properties
- **Frequency:** One-time backfill, then monthly updates
- **Execution:** Run locally or in large GitHub Actions batches

### Data Sources
- URL Pattern: `https://www.hemnet.se/salda/lagenhet-*`
- Time-based filtering (by month)
- Batch size: ~500 properties per month

### Key Fields
```python
{
    'final_price': int,          # What it actually sold for ⭐
    'asking_price': int,         # Original listing price
    'price_change': int,         # final - asking
    'price_change_pct': float,   # Percentage change
    'sold_date': date,           # When it sold ⭐
    'time_on_market': int,       # Days from list to sale
    'address': str,
    'coordinates': (lat, lng),
    'area': float,
    'rooms': float,
    # ... all property details
}
```

### Use Cases
1. **Baseline Analysis:**
   - Historical price trends by neighborhood
   - Seasonal patterns
   - Market cycles

2. **ML Model Training:**
   - Train price prediction models
   - Understand what drives prices
   - Feature importance analysis

3. **Market Context:**
   - "Is this a good price?" comparisons
   - Neighborhood profiling
   - Price per m² benchmarks

### Workflow
```
Month 1 (2020-01):
  Scrape sold properties → 500 properties
  Save to: data/raw/properties/sold/202001/batch_*.parquet
  Load to DuckDB: sold_properties table

Month 2 (2020-02):
  Scrape sold properties → 500 properties
  ... repeat for all months ...

Month 60 (2025-12):
  Scrape sold properties → 500 properties
  TOTAL: ~56,000 properties in database
```

### GitHub Actions Strategy
**Option A: Run Locally (Recommended)**
- Total time: ~10 hours
- No GitHub Actions minutes used
- More control over errors
- Commit final Parquet files to repo

**Option B: GitHub Actions**
- Break into monthly batches
- Each batch: ~10 minutes
- Auto-commit after each month
- Resume capability if interrupted

---

## 🔄 Component 2: Live Market Monitoring

### Purpose
Track currently listed properties to identify underpriced opportunities in real-time.

### Scope
- **Data:** Active listings (currently for sale)
- **Volume:** ~1,500 properties at any given time
- **Frequency:** Weekly updates every Sunday
- **Execution:** Automated GitHub Actions

### Data Sources
- URL Pattern: `https://www.hemnet.se/bostad/lagenhet-*`
- Current market snapshot
- Weekly refresh to catch changes

### Key Fields
```python
{
    'asking_price': int,         # Current asking price ⭐
    'price_changes': list,       # History of price drops ⭐
    'listed_date': date,         # When first listed
    'days_on_market': int,       # How long listed
    'predicted_price': int,      # ML model prediction ⭐
    'underpriced_pct': float,    # % below prediction ⭐
    'address': str,
    'coordinates': (lat, lng),
    'area': float,
    'rooms': float,
    # ... all property details
}
```

### Use Cases
1. **Opportunity Detection:**
   - Properties >10% below predicted value
   - Recent price drops
   - Long time-on-market (motivated sellers)

2. **Price Tracking:**
   - Monitor specific properties
   - Alert on price changes
   - Track listing lifecycle

3. **Market Intelligence:**
   - Current supply levels
   - New listings per week
   - Average days-on-market

### Workflow
```
Week 1 (Sunday):
  Scrape all active listings → 1,500 properties
  Run ML predictions
  Identify underpriced (<10% below prediction)
  Generate opportunity report
  Email alerts for top opportunities

Week 2 (Sunday):
  Scrape all active listings → 1,500 properties
  Compare to Week 1:
    - New listings
    - Price drops
    - Removed listings (maybe sold?)
  Update predictions
  Generate weekly report
```

### GitHub Actions Strategy
**Automated Weekly Workflow:**
```yaml
schedule:
  - cron: '0 0 * * 0'  # Every Sunday at midnight

steps:
  1. Scrape active listings
  2. Load last week's data from DuckDB
  3. Detect changes:
     - New listings
     - Price drops
     - Removed properties
  4. Run ML predictions
  5. Identify opportunities
  6. Generate report
  7. Send alerts (email/Discord/etc.)
  8. Commit data to repo
```

---

## 🔗 Component 3: Transition Tracking

### Purpose
Connect the two components by matching when active properties sell.

### The Challenge
- Active listing has **asking price**
- Sold record has **final price**
- Need to link them to validate predictions

### Matching Strategy
```python
def match_active_to_sold(active_prop, sold_props):
    """
    Match an active listing to its sold record.
    """
    matches = sold_props.filter(
        # Same address (most reliable)
        address == active_prop.address AND
        
        # Similar area (±5% for measurement differences)
        area_diff <= 5% AND
        
        # Sold after it was listed
        sold_date > active_prop.listed_date AND
        
        # Sold within reasonable timeframe (6 months)
        sold_date < active_prop.listed_date + 180 days
    )
    
    return matches.first()  # Should be unique
```

### Tracked Metrics
```python
{
    'property_id': str,
    'listed_date': date,
    'sold_date': date,
    'time_on_market': int,           # Days from list to sale
    'asking_price': int,             # Original asking
    'final_price': int,              # What it sold for
    'price_drop_count': int,         # Times price was reduced
    'negotiation': int,              # final - asking
    'negotiation_pct': float,        # Percentage discount
    'predicted_price': int,          # Our model's prediction
    'prediction_error': int,         # predicted - final
    'was_underpriced': bool,         # Did we flag it?
    'prediction_accuracy': float,    # How close were we?
}
```

### Use Cases

1. **Validation:**
   - How accurate are our predictions?
   - Did "underpriced" properties sell quickly?
   - Were we too conservative/aggressive?

2. **Model Improvement:**
   - Retrain with fresh sales data
   - Identify systematic errors
   - Adjust for market shifts

3. **Market Insights:**
   - Average negotiation rates
   - Effect of time-on-market on final price
   - Seasonal selling patterns

### Workflow
```
Every Sunday (after scraping active listings):
  
  1. Get last week's active properties
  2. Scrape this week's active properties
  3. Find missing properties (possibly sold)
  
  4. Check sold_properties table for matches
  5. If match found:
     - Calculate time-on-market
     - Compare asking vs final price
     - Validate our prediction
     - Update metrics
  
  6. Generate transition report:
     - X properties sold this week
     - Y were flagged as underpriced
     - Z% prediction accuracy
     - Average time-on-market
  
  7. Retrain model if needed (monthly)
```

---

## 📊 Database Schema

### Tables

#### 1. `sold_properties` (Historical)
```sql
CREATE TABLE sold_properties (
    property_id VARCHAR PRIMARY KEY,
    url VARCHAR,
    address VARCHAR,
    neighborhood VARCHAR,
    
    -- Sale Info
    asking_price INTEGER,
    final_price INTEGER,
    sold_date DATE,
    price_change INTEGER,
    price_change_pct FLOAT,
    
    -- Property Details
    rooms FLOAT,
    area FLOAT,
    floor VARCHAR,
    building_year INTEGER,
    
    -- Location
    latitude FLOAT,
    longitude FLOAT,
    
    -- Metadata
    scraped_at TIMESTAMP,
    source_month VARCHAR  -- e.g., "202511"
);
```

#### 2. `active_properties` (Current)
```sql
CREATE TABLE active_properties (
    property_id VARCHAR PRIMARY KEY,
    url VARCHAR,
    address VARCHAR,
    neighborhood VARCHAR,
    
    -- Listing Info
    asking_price INTEGER,
    listed_date DATE,
    days_on_market INTEGER,
    
    -- ML Predictions
    predicted_price INTEGER,
    underpriced_pct FLOAT,
    is_opportunity BOOLEAN,
    
    -- Property Details
    rooms FLOAT,
    area FLOAT,
    floor VARCHAR,
    building_year INTEGER,
    
    -- Location
    latitude FLOAT,
    longitude FLOAT,
    
    -- Tracking
    first_seen DATE,
    last_seen DATE,
    scrape_count INTEGER,
    status VARCHAR  -- 'active', 'removed', 'sold'
);
```

#### 3. `price_changes` (History)
```sql
CREATE TABLE price_changes (
    id INTEGER PRIMARY KEY,
    property_id VARCHAR,
    changed_date DATE,
    old_price INTEGER,
    new_price INTEGER,
    price_drop INTEGER,
    price_drop_pct FLOAT,
    
    FOREIGN KEY (property_id) REFERENCES active_properties(property_id)
);
```

#### 4. `property_transitions` (Linkage)
```sql
CREATE TABLE property_transitions (
    id INTEGER PRIMARY KEY,
    active_property_id VARCHAR,
    sold_property_id VARCHAR,
    
    -- Timeline
    listed_date DATE,
    sold_date DATE,
    time_on_market INTEGER,
    
    -- Pricing
    asking_price INTEGER,
    final_price INTEGER,
    negotiation INTEGER,
    negotiation_pct FLOAT,
    
    -- Predictions
    predicted_price INTEGER,
    prediction_error INTEGER,
    prediction_accuracy FLOAT,
    was_flagged_underpriced BOOLEAN,
    
    -- Match Quality
    match_confidence FLOAT,
    match_method VARCHAR,
    
    FOREIGN KEY (active_property_id) REFERENCES active_properties(property_id),
    FOREIGN KEY (sold_property_id) REFERENCES sold_properties(property_id)
);
```

---

## 🔄 Data Flow

### Initial Setup (One-Time)
```
1. Historical Backfill
   ├─ Scrape sold properties (2020-2025)
   ├─ Load to DuckDB: sold_properties table
   └─ Train ML model on historical data
```

### Weekly Cycle (Ongoing)
```
2. Sunday 00:00 UTC
   ├─ Scrape active listings
   ├─ Compare to last week
   ├─ Detect changes (new, removed, price drops)
   └─ Update active_properties table

3. Sunday 00:30 UTC
   ├─ Run ML predictions
   ├─ Identify underpriced properties
   └─ Generate opportunity report

4. Sunday 01:00 UTC
   ├─ Match removed properties to sold
   ├─ Update property_transitions table
   ├─ Calculate prediction accuracy
   └─ Generate performance report

5. Sunday 01:30 UTC
   ├─ Send email alerts
   ├─ Update dashboard
   └─ Commit data to repo
```

### Monthly Updates
```
6. First Sunday of Month
   ├─ Scrape last month's sold properties
   ├─ Add to sold_properties table
   ├─ Retrain ML model with fresh data
   └─ Update prediction accuracy metrics
```

---

## 🎯 Success Metrics

### Historical Component
- ✅ 56,000 properties scraped
- ✅ Complete coverage (2020-present)
- ✅ <5% missing data
- ✅ All coordinates found

### Live Monitoring
- ✅ Weekly scraping runs reliably
- ✅ <10% properties missed
- ✅ Price changes detected within 7 days
- ✅ Opportunities identified and alerted

### Transition Tracking
- ✅ >80% of sold properties matched
- ✅ Time-on-market calculated accurately
- ✅ Prediction accuracy >70% (±10%)
- ✅ Model improves over time

---

## 💡 Key Insights

### Why Two Components?
1. **Different Data Sources:**
   - Sold: `/salda/` URLs (historical)
   - Active: `/bostad/` URLs (current)

2. **Different Update Frequencies:**
   - Sold: Monthly (new sales data)
   - Active: Weekly (market changes fast)

3. **Different Use Cases:**
   - Sold: Training & benchmarking
   - Active: Opportunity detection

### Why Connect Them?
- **Validation:** Did our predictions work?
- **Learning:** Feed outcomes back to model
- **Insights:** Market dynamics over time

---

## 📅 Implementation Priority

### Phase 1: Foundation (Weeks 1-2)
1. Build unified property scraper
2. Historical backfill (56k sold)
3. Set up DuckDB schema

### Phase 2: Monitoring (Weeks 3-4)
1. Active listings workflow
2. ML model training
3. Opportunity detection

### Phase 3: Connection (Week 5)
1. Transition tracking
2. Prediction validation
3. Model retraining pipeline

### Phase 4: Polish (Week 6+)
1. Dashboard
2. Alerts
3. Reports

---

**This architecture separates concerns while enabling powerful insights!** 🚀
