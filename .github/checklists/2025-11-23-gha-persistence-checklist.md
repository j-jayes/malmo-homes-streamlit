# 2025-11-23 GHA Persistence Checklist

## Goal
Guard the scheduled scrapers against data loss during cron runs by ensuring default CLI parameters exist for schedule-driven executions and persisting/committing scraped batches before any downstream database work that may fail.

## Tasks
1. **Document failure context**
   - Capture the missing `--min-area` argument error from the sold scraper log.
   - Capture the `git add data/database/properties.duckdb` failure due to `.gitignore`.

2. **Solidify scheduled defaults for area scraper**
   - Determine safe default `min_area`, `max_area`, `initial_step`, `max_pages` for unattended cron usage.
   - Update the workflow to compute fallbacks when `github.event_name == 'schedule'` per GitHub docs on `inputs` context, storing resolved values via `$GITHUB_ENV`.
   - Ensure logging reflects resolved range so debugging cron runs is easier.

3. **Persist scraped detail batches proactively**
   - Move git staging/commit of `$PROCESSED_ROOT` and run index to immediately follow the rsync step so scraped files are pushed before DB aggregation work.
   - Gate DuckDB staging so the workflow skips `.gitignore`d files instead of failing; detect `git check-ignore` and proceed without marking the job failed.
   - Add periodic commits (e.g., commit after every N batches processed based on metadata) so long runs push progress multiple times when `metadata["total_processed"]` crosses thresholds.

4. **Update documentation + status tracker**
   - Summarize the new persistence/commit pattern in README automation notes.
   - Mark this checklist with progress notes as work completes.

## Failure Context
- `scrape_sold_batch.yml` (cron run 2025-11-23 00:00 UTC) exited immediately with `error: the following arguments are required: --min-area`, confirming scheduled events do not supply dispatch inputs.
- `property_detail_runner.yml` (run id 19611359079) completed scraping but failed at `git add data/database/properties.duckdb` because Git reported `The following paths are ignored by one of your .gitignore files`, leaving the cron job marked failed despite the scraped data being present.

## Status Notes
- ✅ Task 1: Added log references from `gh run view` output to internal notes and ensured failure signatures (missing `--min-area`, ignored DuckDB file) are captured in the workflow comments.
- ✅ Task 2: Scheduled defaults resolved via `$GITHUB_ENV` plus console logging in `scrape_sold_batch.yml`.
- ✅ Task 3: Detail runner now writes directly to its timestamped `RUN_DIR` and leverages `batch_manager` auto-commits every 4 batches (configurable via `--git-commit-interval`).
- ✅ Task 4: README automation section updated to describe the new persistence/commit flow; checklist reflects current status.
