# Scraper Pipeline Refactor – 2026-02-08

## Situation

- **56,510 sold property URLs** to scrape from `data/raw/sold_properties_all_areas.csv`
- **22,805 already tracked** in progress cache → **33,705 remaining**
- Last successful scrape: **Dec 4, 2025** — 2+ months of wasted runner time
- **320 runs since Dec 5** (265 cancelled at 2h timeout + 39 failures + 16 success before break) = ~640 wasted runner hours

## Root Causes

### 1. Playwright version mismatch (CRITICAL — scraper is fully broken)
- Workflow installs playwright into `.venv` via `uv pip install`, then runs `playwright install chromium`
- This downloads `chromium_headless_shell-1208` (for playwright 1.58.0)
- But then invokes scraper via `uv run python -m ...` which resolves its OWN environment
- That transient env has an older playwright expecting `chromium_headless_shell-1194`
- **Result**: Every property scrape fails instantly with "Executable doesn't exist"
- **Fix**: Stop mixing `uv pip install` + `uv run`. Use activated venv consistently.

### 2. Timeout too short (120 min vs 360 min available)
- GitHub Actions free tier allows 6 hours per job
- `property_detail_runner.yml` uses `timeout-minutes: 120`
- Even when working (pre-Dec 5), this capped runs at ~1000 properties/run
- With 33K remaining at 7.6s/property average, need ~71 hours total
- At 5.5h effective scraping per 6h run → **~13 runs** to complete
- **Fix**: Increase to `timeout-minutes: 350` (5h50m, safe margin under 6h)

### 3. Cron too frequent for long runs
- Current: `30 0,6,12,18 * * *` (4×/day, every 6h)
- With 350-min runs, the next cron fires while the previous is still running
- Concurrency group prevents parallel runs but wastes a queued slot
- **Fix**: Switch to `30 0,12 * * *` (2×/day, every 12h)

### 4. `batch_manager_cli.py` adds unnecessary complexity
- Duplicates progress tracking that `BatchManager` already does
- Slices input CSV to a subset file → redundant with progress_tracker skip logic
- The CLI was designed for a world where offset-based pagination was the only dedup
- **Fix**: Simplify — remove the CLI wrapper, have the workflow invoke BatchManager directly via a clean entry point

### 5. PropertyScraper launches a new browser per property (!)
- `scrape_property()` calls `sync_playwright()` → `chromium.launch()` → `browser.close()` for EACH URL
- Browser startup is ~1-2s overhead per property
- **Fix**: Reuse browser across batch, only create new pages per property

### 6. `save_failures` writes CSV with wrong fieldnames
- Error: `dict contains fields not in fieldnames: 'scraped_at', 'area_range', 'property_id'`
- The failure CSV writer uses hardcoded `['url', 'error']` but input rows contain extra columns
- **Fix**: Write only `url` and `error` fields to the failure CSV

## Checklist

- [x] Write spec
- [x] Fix Playwright invocation (drop `uv run`, use activated venv)
- [x] Refactor PropertyScraper to reuse browser across batch
- [x] Simplify batch_manager_cli into a clean entry point
- [x] Fix failure CSV field mismatch
- [x] Increase timeout to 350 min in property_detail_runner.yml
- [x] Increase timeout to 350 min in scrape_weekly.yml
- [x] Reduce cron to 2×/day (every 12h)
- [x] Validate with syntax/lint check
- [x] Estimate completion time with new settings

## Completion Estimate (post-fix)

- 33,705 remaining URLs
- ~7.6s/property (proven Dec 4 rate), possibly ~6s with browser reuse
- At 6s: 600 properties/hour → 5.5h run = 3,300/run → **~10 runs (~5 days at 2×/day)**
- At 7.6s: 473 properties/hour → 5.5h run = 2,600/run → **~13 runs (~6.5 days at 2×/day)**
