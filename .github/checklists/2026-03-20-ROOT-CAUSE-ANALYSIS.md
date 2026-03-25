# 2026-03-20: Critical Fixes Applied for Git Tracking

## Summary

I've identified and fixed the root cause of why NO NEW DATA has been committed to git since March 12, 2026. The issue is NOT about permissions or .gitignore alone - it's a workflow failure that prevents the git commit step from running.

---

## The Critical Issues Found

### 1. **Azure Storage Account is DISABLED** (PRIMARY ISSUE)
- This causes the "Upload to Azure Blob" step to fail with: `ERROR: The specified account is disabled.`
- The workflow exits with exit code 1, PREVENTING the git commit step from running
- Last successful run: March 11 (Run #9)
- All runs since March 12: FAILURE ❌
- This is a 9-day gap with ZERO new data commits

### 2. **Parquet Files Being Ignored by .gitignore**
- Line 180: `data/processed/*.parquet` ignores ALL processed parquet files
- Even if the workflow reached the git step, the new active listings wouldn't be committed
- Your daily scrapes are saved as parquet files but blocked from git tracking

### 3. **Missing `issues: write` Permission**
- Backfill workflow can't create GitHub issues to report failures
- Less critical but prevents proper failure notifications

---

## Fixes Applied

### Fix 1: Handle Azure Failures Gracefully ✅
**File:** `.github/workflows/collect_active_listings_daily.yml`

Added `continue-on-error: true` to the Azure blob upload step. This allows the workflow to:
1. Attempt Azure upload
2. Fail gracefully if account is disabled
3. **Continue to the git commit step** instead of exiting

### Fix 2: Track Active Listings in Git ✅
**File:** `.gitignore`

Changed from:
```
data/processed/*.parquet  # Blocks all parquet files
```

To:
```
data/processed/*/*.parquet   # Blocks parquet in subdirectories
!data/processed/active_listings/*.parquet  # Explicitly allow active listings
```

This ensures daily snapshots are tracked in git.

### Fix 3: Explicit Git Commit Logic ✅
**File:** `.github/workflows/collect_active_listings_daily.yml`

Replaced the auto-commit action with explicit commands:
```bash
git add -f data/processed/active_listings/links_*.parquet
git add -f data/processed/active_listings/batches_*
git commit -m "data: active listings snapshot..."
git push
```

Using `git add -f` forces adding these files even if .gitignore would normally block them.

### Fix 4: Add Missing Permission ✅
**File:** `.github/workflows/collect_sold_links_backfill.yml`

Added `issues: write` to permissions so the backfill workflow can create failure issues.

---

## Next Steps

1. **Wait for tomorrow's scheduled run** (06:00 UTC)
   - The daily workflow will run with the fixes
   - It will scrape active listings for all of Sweden
   - It will attempt Azure upload (which will fail gracefully)
   - It will commit the data to git and push ✅

2. **Verify the fix works:**
   ```bash
   # Check for new commits
   git log --oneline -5 -- data/processed/active_listings/
   
   # See the parquet files
   ls -la data/processed/active_listings/links_*.parquet
   ```

3. **If you want to test immediately:** (optional)
   ```bash
   gh workflow run collect_active_listings_daily.yml --ref main
   ```

---

## Files Modified

1. **.github/workflows/collect_active_listings_daily.yml**
   - Added `continue-on-error: true` to Azure blob upload
   - Rewrote git commit step with explicit `git add -f` commands

2. **.github/workflows/collect_sold_links_backfill.yml**
   - Added `issues: write` to permissions

3. **.gitignore**
   - Changed parquet ignore pattern
   - Whitelisted `data/processed/active_listings/*.parquet`

4. **.github/checklists/2026-03-20-git-tracking-fix.md**
   - Comprehensive documentation of the issues and fixes

---

## Why This Design is Better

The new design is **resilient to external service failures**:

| OLD DESIGN | NEW DESIGN |
|---|---|
| Scrape → Azure Upload (fail→exit) → Git Commit (never reached) | Scrape → Azure Upload (fail→continue) → Git Commit ✅ |
| High dependency on Azure SLA | Offline-first: git always works |
| Data loss if Azure is down | Graceful degradation |

---

## Expected Outcome

**After the next scheduled run:**
- ✅ New active listings data committed to git every day
- ✅ Git becomes source of truth when Azure is unavailable
- ✅ All 56,000+ property links and new daily snapshots tracked in version control
- ✅ Reports generated with accurate data from Sweden's full housing market

---

## Key Insight

The problem wasn't that you switched FROM Azure TO git. The problem was that the workflow was still TRYING to use Azure and FAILING at that step before it could commit to git. Now the workflow will:
1. Try Azure (nice-to-have)
2. Fall back to git (guaranteed)

This is the correct hybrid approach!
