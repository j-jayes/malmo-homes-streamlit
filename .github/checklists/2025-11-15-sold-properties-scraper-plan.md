# Sold Properties Scraper - Strategic Plan

**Date:** 2025-11-15
**Goal:** Collect 56,535 sold property listings from Hemnet with stealth and efficiency
**URL:** https://www.hemnet.se/salda/bostader?item_types[]=bostadsratt&location_ids[]=17989

---

## 🎯 Core Strategy: Time-Based Chunking

### Why This Works
- Sold properties are **time-indexed** (sold date)
- Can filter by sold date ranges to stay under 2,500 limit
- Natural, human-like search pattern
- Easier to resume if interrupted
- Enables incremental updates (only scrape recent sales)

### Filtering Dimensions (Priority Order)
1. **Sold Date** (PRIMARY) - e.g., 2025-11, 2025-10, etc.
2. **Rooms** (SECONDARY) - 1, 2, 3, 4, 5+
3. **Price Range** (TERTIARY) - if still >2,500

---

## 🤖 GitHub Actions Strategy

### Approach: Incremental Monthly Scraping

```yaml
# Run monthly to collect last month's sold properties
schedule: '0 3 1 * *'  # First day of month, 3 AM UTC
```

### Why This Works for Actions
1. **Headless-friendly**: Can use `headless: true` with Playwright
2. **Time-limited**: Each month ≈ 200-500 properties (manageable)
3. **Low detection risk**: Small, periodic scrapes look natural
4. **Resumable**: If it fails, just re-run next month
5. **No rate limit issues**: Few requests per run

---

## 🕵️ Stealth Tactics for GitHub Actions

### 1. Headless Mode with Realistic Settings
```python
browser = playwright.chromium.launch(
    headless=True,
    args=[
        '--disable-blink-features=AutomationControlled',
        '--disable-dev-shm-usage',
        '--no-sandbox',  # Required for GitHub Actions
        '--disable-setuid-sandbox',
        '--disable-web-security',
        '--disable-features=IsolateOrigins,site-per-process'
    ]
)

# Realistic viewport
context = browser.new_context(
    viewport={'width': 1920, 'height': 1080},
    user_agent='Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36...',
    locale='sv-SE',
    timezone_id='Europe/Stockholm'
)
```

### 2. Human-Like Behavior
- Random delays: 3-8 seconds between requests
- Scroll page slowly before extracting data
- Hover over elements occasionally
- Don't scrape at exact intervals (add jitter)

### 3. Session Management
- Solve Cloudflare once, save cookies
- Reuse cookies for subsequent requests
- Cookie expires? Start new session with delay

### 4. Rate Limiting
```python
# Conservative for Actions
MAX_PAGES_PER_RUN = 30  # ~1,500 properties max
DELAY_BETWEEN_PAGES = 5-10 seconds
DELAY_BETWEEN_MONTHS = 60 seconds
```

---

## 📅 Time-Based Scraping Schedule

### Phase 1: Historical Backfill (Manual/Local)
```
2025-11 → ~400 properties
2025-10 → ~500 properties
2025-09 → ~450 properties
...
2020-01 → ~200 properties (older = fewer)
```

**Estimated:** 60 months × 10 pages avg = 600 API requests total
**Duration:** Run locally over 2-3 days with proper delays

### Phase 2: Incremental Updates (GitHub Actions)
```yaml
# Monthly collection of last month's sales
- Runs automatically first of every month
- Collects 200-500 properties
- Takes ~10 minutes per run
- Zero manual intervention
```

---

## 🏗️ Implementation Plan

### Stage 1: Script Development (Local Testing)
- [ ] Create `sold_properties_scraper.py`
- [ ] Test with single month (2025-11)
- [ ] Validate data extraction
- [ ] Test Cloudflare handling in headless mode
- [ ] Implement cookie persistence

### Stage 2: Batch Processing
- [ ] Add month range parameter
- [ ] Implement progress tracking (JSON checkpoint)
- [ ] Add retry logic for failed months
- [ ] Deduplication by property ID
- [ ] Save to CSV/Parquet by month

### Stage 3: GitHub Actions Integration
- [ ] Create `scrape_sold_monthly.yml` workflow
- [ ] Test in Actions environment
- [ ] Verify headless mode works
- [ ] Commit data back to repo
- [ ] Add failure notifications

### Stage 4: Historical Backfill (One-Time)
- [ ] Run locally for 2020-2024 data
- [ ] Upload to repository
- [ ] Document data coverage
- [ ] Validate completeness

---

## 🛡️ Anti-Detection Measures

### Cloudflare in GitHub Actions
```python
# Strategy: Use headed mode for first page only
if is_first_run_of_session:
    # Launch visible browser to solve Cloudflare
    # This works in GitHub Actions with xvfb
    context = browser.new_context(
        ...
        # After challenge, save cookies
    )
else:
    # Reuse saved cookies in headless mode
    context = browser.new_context(
        storage_state='hemnet_session.json'
    )
```

### Xvfb for Virtual Display (Actions)
```yaml
- name: Setup virtual display
  run: |
    sudo apt-get install -y xvfb
    export DISPLAY=:99
    Xvfb :99 -screen 0 1920x1080x24 > /dev/null 2>&1 &
```

### Alternative: Stealth Plugin
```python
from playwright_stealth import stealth_sync

# Makes Playwright undetectable
page = context.new_page()
stealth_sync(page)
```

---

## 📊 Data Schema

### sold_properties.csv
```csv
property_id,url,address,neighborhood,rooms,sqm,asking_price,sold_price,sold_date,sold_month,price_change,days_on_market,broker,scraped_at
```

### Progress Tracking (sold_scraping_progress.json)
```json
{
  "last_completed_month": "2025-10",
  "months_remaining": ["2025-09", "2025-08", ...],
  "failed_months": [],
  "total_properties_collected": 15420,
  "last_run": "2025-11-15T03:00:00Z"
}
```

---

## 🚀 GitHub Actions Workflow Design

### File: `.github/workflows/scrape_sold_monthly.yml`

```yaml
name: Scrape Sold Properties (Monthly)

on:
  schedule:
    - cron: '0 3 1 * *'  # First of month, 3 AM UTC
  workflow_dispatch:     # Manual trigger
    inputs:
      month:
        description: 'Month to scrape (YYYY-MM)'
        required: true
        default: '2025-11'

jobs:
  scrape-sold:
    runs-on: ubuntu-latest
    timeout-minutes: 30
    
    steps:
      - uses: actions/checkout@v4
      
      - name: Setup Python & Dependencies
        uses: actions/setup-python@v5
        with:
          python-version: '3.11'
      
      - name: Install system dependencies
        run: |
          sudo apt-get update
          sudo apt-get install -y xvfb
      
      - name: Install Playwright
        run: |
          source .venv/bin/activate
          playwright install chromium --with-deps
      
      - name: Start virtual display
        run: |
          export DISPLAY=:99
          Xvfb :99 -screen 0 1920x1080x24 > /dev/null 2>&1 &
      
      - name: Scrape last month's sold properties
        run: |
          source .venv/bin/activate
          python src/scrapers/sold_properties_scraper.py \
            --month $(date -d 'last month' +%Y-%m) \
            --max-pages 30 \
            --output data/raw/sold_properties_$(date -d 'last month' +%Y%m).csv
      
      - name: Commit data
        uses: stefanzweifel/git-auto-commit-action@v5
        with:
          commit_message: "data: add sold properties for $(date -d 'last month' +%Y-%m)"
          file_pattern: 'data/raw/sold_properties_*.csv'
```

---

## ⚠️ Risk Mitigation

### If Cloudflare Blocks in Actions
1. **Fallback 1**: Use BrightData/ScraperAPI proxy
2. **Fallback 2**: Use residential proxy rotation
3. **Fallback 3**: Run locally, push data to repo
4. **Fallback 4**: Use authenticated session (manual login)

### If Rate Limited
1. Reduce pages per run (30 → 10)
2. Increase delays (10s → 30s)
3. Split into weekly runs instead of monthly
4. Use multiple repos/accounts (not recommended)

---

## 📈 Success Metrics

- [ ] Successfully scrape 1 month headlessly in Actions
- [ ] Zero Cloudflare blocks in 5 consecutive runs
- [ ] Data quality >99% (no missing fields)
- [ ] Total runtime <30 minutes per month
- [ ] Zero manual intervention required

---

## 🎯 MVP: Next Steps

1. **Today**: Create `sold_properties_scraper.py`
2. **Test locally**: Scrape November 2025 (headed mode)
3. **Test headless**: Same month, headless with xvfb
4. **Create workflow**: Add to `.github/workflows/`
5. **Test in Actions**: Manual trigger for one month
6. **Schedule**: Enable monthly automation

---

## 💡 Smart Optimizations

### For Large Historical Backfill
```python
# Local script: historical_backfill.py
months = generate_month_range('2020-01', '2024-12')
for month in months:
    scrape_month(month)
    time.sleep(300)  # 5 min between months
    # Saves to: data/raw/sold_properties_YYYYMM.csv
```

### For GitHub Actions (Incremental)
```python
# Auto-determines last month
last_month = (datetime.now() - timedelta(days=30)).strftime('%Y-%m')
scrape_month(last_month)
# Only scrapes ~500 properties per run
```

---

## 🔮 Future Enhancements

1. **Email notifications**: Send summary of properties scraped
2. **Data validation**: Check for anomalies (price outliers)
3. **Automatic retry**: Failed months added to queue
4. **Dashboard**: Real-time scraping status page
5. **API endpoint**: Query sold properties via FastAPI

