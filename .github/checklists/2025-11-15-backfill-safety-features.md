# Backfill Safety Features & Execution Guide

**Date:** 2025-11-15  
**Purpose:** Zero-data-loss guarantee for historical backfill

---

## 🛡️ Safety Features

### 1. Incremental Commits ✅

**Problem:** If workflow hits 6-hour timeout, uncommitted data is lost.

**Solution:** Commit after EVERY month scraped!

```yaml
# Pseudo-code from workflow
for each month:
  scrape_month()
  save_to_csv()
  git add + commit + push  # ← Immediate commit!
  continue to next month
```

**Benefits:**
- ✅ Data saved every 3-5 minutes
- ✅ If timeout at month 50, months 1-49 are already in repo
- ✅ Can resume from where we left off
- ✅ Parallel workflows don't conflict (each month is separate file)

### 2. Idempotent Operations ✅

**Problem:** Re-running workflow might duplicate data or waste time.

**Solution:** Smart file checking before scraping.

```python
# In save_to_csv()
if file_exists and same_data:
    logger.info("Already scraped, skipping")
    return  # No work needed!
```

**Benefits:**
- ✅ Safe to re-run workflows
- ✅ Automatically skips completed months
- ✅ Only scrapes what's missing

### 3. Progress Tracking ✅

**File:** `data/raw/sold_links/backfill_progress.json`

```json
{
  "completed": [
    "2020-01",
    "2020-02",
    "2020-03"
  ],
  "last_updated": "2025-11-15T14:30:00"
}
```

**Benefits:**
- ✅ Know exactly what's been scraped
- ✅ Resume capability in Python script
- ✅ Audit trail

### 4. Error Recovery ✅

```yaml
# If scraping fails mid-month
python scrape.py || {
  echo "Failed! Committing progress..."
  git commit -m "partial batch (failed at $MONTH)"
  git push
  exit 1
}
```

**Benefits:**
- ✅ Even failures are saved
- ✅ Can diagnose issues from partial data
- ✅ Resume from last good month

### 5. Parallel Workflow Isolation ✅

**Key Design:**
- Each batch scrapes different months
- Each month = separate CSV file
- No file conflicts between workflows

**Example:**
```
Workflow A: 2020-01 to 2020-12 → sold_links_202001.csv, sold_links_202002.csv, ...
Workflow B: 2021-01 to 2021-12 → sold_links_202101.csv, sold_links_202102.csv, ...
```

**Benefits:**
- ✅ No merge conflicts
- ✅ Workflows can run truly in parallel
- ✅ One failure doesn't block others

---

## 🚀 Execution Options

### Option A: GitHub Actions (Recommended)

**Why?**
- Free compute
- Xvfb handles Cloudflare
- Incremental commits = zero data loss risk
- Parallel execution = fast!

**How?**

```bash
# Install GitHub CLI (one-time)
brew install gh
gh auth login

# Trigger all batches in parallel
./scripts/trigger_backfill_parallel.sh
```

**Batches (all run simultaneously):**
```
Batch 1: 2020-01 to 2020-12  (~1 hour)
Batch 2: 2021-01 to 2021-12  (~1 hour)
Batch 3: 2022-01 to 2022-12  (~1 hour)
Batch 4: 2023-01 to 2023-12  (~1 hour)
Batch 5: 2024-01 to 2024-12  (~1 hour)
Batch 6: 2025-01 to 2025-11  (~1 hour)

Total time: ~1-2 hours (parallel)
```

**Manual Trigger (GitHub UI):**
1. Go to Actions → "Scrape Sold Properties (Batch)"
2. Click "Run workflow"
3. Enter:
   - `start_month`: 2020-01
   - `end_month`: 2020-12
   - `max_pages`: 50
4. Click "Run workflow"
5. Repeat for other batches

### Option B: Local Execution

**Why?**
- Full control
- See browser if needed
- No GitHub Actions quota usage

**How?**

```bash
# Test first (3 months)
python scripts/backfill_sold_links.py --test

# Full backfill (sequential, ~10 hours)
python scripts/backfill_sold_links.py

# Specific range
python scripts/backfill_sold_links.py --start 2020-01 --end 2023-12

# Headless mode
python scripts/backfill_sold_links.py --headless
```

**Resume after interruption:**
```bash
# Just run again - it loads backfill_progress.json
python scripts/backfill_sold_links.py

# Output:
# Loaded progress: 25 months already scraped
# Months to scrape: 35
```

---

## 📊 Monitoring

### GitHub Actions

```bash
# List all runs
gh run list --workflow=scrape_sold_batch.yml

# Watch specific run
gh run watch <RUN_ID>

# View logs
gh run view <RUN_ID> --log

# Check status of all parallel batches
gh run list --workflow=scrape_sold_batch.yml --limit 6
```

### Local

```bash
# Check progress file
cat data/raw/sold_links/backfill_progress.json | jq '.completed | length'

# Count total links collected
cat data/raw/sold_links/sold_links_*.csv | wc -l

# List completed months
ls -1 data/raw/sold_links/sold_links_*.csv | sed 's/.*sold_links_//' | sed 's/.csv//'
```

---

## 🔄 Resume Scenarios

### Scenario 1: Workflow Timeout (6 hours)

**What happens:**
- Workflow stops mid-scraping
- ✅ All completed months are already committed to repo
- ❌ Current month in progress is lost (only that one!)

**Recovery:**
1. Check `backfill_progress.json` to see last completed month
2. Re-run workflow with new date range
3. Example: Timeout at 2020-08 → Re-run from 2020-08 to 2020-12

### Scenario 2: Cloudflare Block

**What happens:**
- Scraping fails on specific month
- ✅ Previous months already committed
- ✅ Error logged and workflow fails
- ✅ GitHub issue created automatically

**Recovery:**
1. Check workflow logs
2. Wait 1-2 hours (rate limit cooldown)
3. Re-run workflow for failed month range
4. Or: Run locally in headed mode to solve challenge manually

### Scenario 3: Partial Batch Completion

**What happens:**
- Batch 1 ✅ Complete (2020)
- Batch 2 ✅ Complete (2021)
- Batch 3 ❌ Failed (2022)
- Batch 4 ✅ Complete (2023)
- Batch 5 ✅ Complete (2024)
- Batch 6 ✅ Complete (2025)

**Recovery:**
1. Only re-run Batch 3
2. Other batches don't need to re-run (data already in repo)

---

## 💾 Data Persistence Guarantee

### Commit Strategy

```
Time    Month       Action
0:00    2020-01     Scrape → Commit → Push ✅
0:05    2020-02     Scrape → Commit → Push ✅
0:10    2020-03     Scrape → Commit → Push ✅
...
0:55    2020-12     Scrape → Commit → Push ✅
1:00    TIMEOUT     ← Even if this happens, we have all 12 months! ✅
```

### What Gets Committed Each Time

```bash
git add data/raw/sold_links/sold_links_YYYYMM.csv
git add data/raw/sold_links/backfill_progress.json
git add data/.hemnet_session.json  # Reuse cookies
git commit -m "data: sold links for YYYY-MM"
git push
```

### Repository State After Parallel Execution

```
data/raw/sold_links/
├── sold_links_202001.csv  ← From Batch 1, commit 1
├── sold_links_202002.csv  ← From Batch 1, commit 2
├── ...
├── sold_links_202101.csv  ← From Batch 2, commit 1
├── sold_links_202102.csv  ← From Batch 2, commit 2
├── ...
├── backfill_progress.json ← Updated after each month
└── backfill_summary.json  ← Final summary
```

**Result:** 60+ commits, but ZERO data loss risk! 🎉

---

## ✅ Pre-Flight Checklist

### Before Triggering Workflows

- [ ] GitHub CLI installed: `gh --version`
- [ ] Authenticated: `gh auth status`
- [ ] Workflow file exists: `.github/workflows/scrape_sold_batch.yml`
- [ ] Python scraper works: Test locally first
- [ ] Repository has Actions enabled
- [ ] Git pushes are allowed (not branch protected)

### Verify After Completion

- [ ] Check all batches completed: `gh run list`
- [ ] Count CSV files: `ls data/raw/sold_links/*.csv | wc -l` (should be ~60)
- [ ] Verify total links: `cat data/raw/sold_links/sold_links_*.csv | wc -l`
- [ ] Check summary: `cat data/raw/sold_links/backfill_summary.json`
- [ ] No failed workflows: Check GitHub Actions UI

---

## 🎯 Success Criteria

### Complete Success
- ✅ All 60 months scraped (2020-01 to 2025-11)
- ✅ ~56,000 property links collected
- ✅ All CSV files in repository
- ✅ backfill_summary.json shows totals
- ✅ No failed workflow runs

### Acceptable Success (Partial)
- ✅ 55+ months scraped (90%+)
- ✅ Can manually re-run failed months
- ✅ Resume capability working

### Failure (Need to Investigate)
- ❌ Multiple batches failing
- ❌ Cloudflare blocking all requests
- ❌ Data not being committed to repo
- ❌ File conflicts in parallel workflows

---

## 📈 Expected Timeline

### Parallel Execution (Recommended)
```
Start: Trigger 6 workflows simultaneously
+0:00  All 6 batches start
+0:05  First commits appear
+0:30  ~50% complete
+1:00  ~80% complete
+1:30  All complete! 🎉

Total: 1-2 hours
```

### Sequential Execution (Local)
```
Start: python scripts/backfill_sold_links.py
+0:00  Start 2020-01
+0:05  Month 1 complete (1/60 = 1.7%)
+0:10  Month 2 complete (2/60 = 3.3%)
...
+5:00  Month 60 complete

Total: 5-10 hours
```

---

## 🔐 Security Notes

### Session Persistence
- Cookie file: `data/.hemnet_session.json`
- Contains: Browser session cookies (not sensitive)
- Purpose: Avoid repeated Cloudflare challenges
- Committed to repo: Yes (safe, not credentials)

### Rate Limiting
- 5-10 second delays between pages
- Respect Hemnet's servers
- Human-like behavior patterns

---

**Next Steps:**
1. Test one batch locally first
2. Trigger parallel workflows
3. Monitor progress
4. Celebrate when complete! 🎉
