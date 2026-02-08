# 2026-02-08 Active Listings Scraper Checklist

## Goal
Scrape currently-for-sale properties on Hemnet (Malmö bostadsrätter) and run predictions against them, so the frontend can show live deals.

## Architecture
Reuse existing infrastructure:
- `link_collector.py` already supports active listings (`/bostader`, `a[href*="/bostad/"]`)
- `property_detail_scraper.py` already handles `ForSaleProperty` via `__NEXT_DATA__`
- `batch_manager.py` + `batch_manager_cli.py` handle batching, progress, git commits

New pieces needed:
- `scripts/scrape_active_listings.py` — orchestrator that: collects links → scrapes details → predicts → stores
- `.github/workflows/scrape_active_listings.yml` — GHA workflow (daily cron)
- `src/data/aggregate_active.py` — aggregates for-sale parquet batches into DuckDB `active_listings` table

## Tasks

- [x] Create `scripts/scrape_active_listings.py` — end-to-end orchestrator
- [x] Create `src/data/aggregate_active_listings.py` — for-sale → DuckDB pipeline + predictions
- [x] Test link collection locally (headless) — 55 links from page 1
- [x] Test detail scraping on active URLs — `ForSaleProperty` fields extracted correctly
- [x] Test full pipeline end-to-end — 3/3 scraped, aggregated, predicted
- [x] Create `.github/workflows/scrape_active_listings.yml` — daily 06:00 UTC
- [x] Update backend: `/active` endpoint + `get_active_listings()` + `ActiveListing` model
- [x] Update frontend: view toggle (Sold / For Sale), `ActiveListingsPanel`, map with active markers
- [x] Commit and push
