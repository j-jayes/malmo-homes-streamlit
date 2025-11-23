# 2025-11-23 – Cron Scraping Checklist

## Context
- Want resilient, low-friction automation for historical Hemnet backfill
- Two workflows:
  1. `scrape_sold_batch.yml` – adaptive area link collector that can resume and commits partial progress
  2. `property_detail_runner.yml` – batch detail scraper reading staged CSVs, persists metadata/index
- Constraints from GitHub hosted runners (per docs): max 6h execution per job, workflow run lifetime 35 days, concurrency caps.
- Need cron cadence that chains runs w/ >6h spacing so a fresh runner resumes soon after previous job hits wall.
- Must respect target site: throttle requests (few seconds between) and dedupe so reruns skip completed work.

## Goals
1. Add scheduled triggers for both workflows so they run autonomously.
2. Stagger schedules so link collector leads, detail runner follows ~30m later using CSVs produced by link collector.
3. Ensure deduplication & resume safety: rely on progress caches + gating logic so cron reruns don't re-scrape same rows.
4. Encode polite scraping defaults: env vars for per-request sleep, jitter, and batch-level pauses consumed by scrapers.
5. Document cadence and throttling strategy in repo README.

## Plan
- **Cron windows**
  - Run link collector every 6h starting at :00 UTC (00:00, 06:00, 12:00, 18:00)
  - Run detail runner 30m later (00:30, 06:30, 12:30, 18:30) so new CSVs available and runner limit offset.
- **Workflow updates**
  - `on:` block: add `schedule` array w/ cron strings; keep `workflow_dispatch` for manual overrides.
  - Guarantee `workflow_dispatch` inputs have defaults to ensure scheduled runs pass values (maybe via `inputs.default`? for schedule there isn't `inputs`, so script should read from env). For property runner, scheduled run needs predetermined CSV/batch settings -> set `env` defaults referencing `data/raw/area_ranges/properties_0_31.csv` etc.
  - Add `env` values or CLI flags for `REQUEST_DELAY_SECONDS` etc; propagate to scripts via CLI flags if supported, else set env var consumed by python script; if not supported, extend CLI to read env? Might pass `--sleep-between-runs`? Need inspect script.
  - Insert throttle step (maybe export `SCRAPER_SLEEP_SECONDS`) and ensure CLI uses? Need to review `scripts/scrape_all_areas.py` for argument for `--request-delay`. search.
- **Throttle implementation**
  - For `scripts/scrape_all_areas.py`, check `click` options maybe `--sleep`? We'll search for `request_delay`, `sleep_seconds`. Use `rg`.
  - For detail runner CLI `src/scrapers/batch_manager_cli`, check for options.
  - If existing options missing, we may add CLI support to pass `--request-delay` or `--throttle-seconds`. But user asked to set cron job ensuring waiting a few seconds between requests. Could be already done? Need confirm to avoid editing scrapers? maybe `batch_manager` has `--backoff`? Need review to be sure. We should inspect quickly with `rg 'delay' src/scrapers/batch_manager_cli.py` etc.

- **Dedup**
  - Already dedup via progress caches. Need to mention how schedule respects 6h. Possibly add concurrency group per existing? `property_detail_runner` already has concurrency group. For `scrape_sold_batch` maybe add `concurrency` to avoid overlap; also set `concurrency` to `scrape-sold-batch`. Add `concurrency` for first workflow as well to prevent overlapping when run takes >6h and next triggered.

- **Documentation**
  - README addition? maybe add new section `Automation cadence` in root README describing cron schedule, throttle, dedup/resume. Also mention restful behavior (sleep env). Could mention `progress.json`, `metadata`. Possibly also mention need to use `uv` etc.

- **Testing**
  - After updates, run `yamllint`? Not necessary. Could use `act` but heavy. We'll rely on YAML syntax.

- **Git steps**
  - `git status`, stage, commit message `ci: schedule cron scraping workflows`.

## Tasks
- [ ] Inspect scrapers for throttle flags + dedup env to avoid duplicate scraping. Add CLI flags if missing.
- [ ] Update `scrape_sold_batch.yml` w/ `schedule`, concurrency, env for throttle, fallback inputs.
- [ ] Update `property_detail_runner.yml` w/ `schedule`, default env inputs, throttle env, gating to skip rerun if no new manifest.
- [ ] Document cadence + throttle in README (Automation section) referencing progress caches + env defaults.
- [ ] Run `git status`, review diff, commit & push.
