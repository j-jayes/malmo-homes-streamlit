# Data Pipeline Conventions

This document defines the naming and structural conventions for all pipeline
scripts and GitHub Actions workflows in this project.  Following these
conventions makes the end-to-end data flow immediately readable from file names
alone.

---

## Naming Scheme

### `scripts/` — pipeline entry points

Primary scripts follow the pattern:

```
{verb}_{subject}[_{qualifier}].py
```

| Verb | Meaning |
|---|---|
| `collect` | Scrape raw data from an external source |
| `process` | Transform / aggregate raw data |
| `train`   | Fit a machine-learning model |
| `match`   | Link records across tables |
| `backfill`| Historical one-off data recovery (local use) |

Examples:

| File | Role |
|---|---|
| `collect_sold_links.py` | Scrape sold-property search pages → URL list (area-adaptive) |
| `collect_active_listings.py` | Scrape active (for-sale) listings end-to-end |
| `train_model.py` | Train the LightGBM price model |
| `train_text_pipeline.py` | Train the TF-IDF Ridge text-price pipeline |
| `match_active_to_sold.py` | Link description_archive rows to sold property IDs |
| `batch_predict.py` | Batch ML predictions on sold properties |
| `backfill_sold_links.py` | Local month-by-month backfill for single-city scope |
| `backfill_description_archive.py` | Re-populate description archive from parquet files |

Scripts prefixed with `_` (e.g. `_test_active_links.py`) or in a separate
`tests/` directory are development / debugging tools and are **not** part of
the production pipeline.

---

### `.github/workflows/` — CI/CD automation

Workflow files follow the pattern:

```
{verb}_{subject}_{frequency|qualifier}.yml
```

| Qualifier | Meaning |
|---|---|
| `_daily`     | Runs on a daily cron schedule |
| `_weekly`    | Runs on a weekly cron schedule |
| `_scheduled` | Runs on a sub-daily schedule (e.g. twice daily) |
| `_backfill`  | Manual dispatch for historical data recovery |

Production workflows:

| File | Trigger | Role |
|---|---|---|
| `collect_active_listings_daily.yml` | Daily 06:00 UTC | Links + details + predictions for active listings |
| `collect_sold_links_weekly.yml` | Weekly Sunday 02:00 UTC | Collect URLs for recently sold properties (area-adaptive) |
| `collect_sold_links_backfill.yml` | Manual dispatch | Historical month × area national backfill |
| `collect_property_details_scheduled.yml` | Twice daily 00:30 + 12:30 UTC | Scrape detail pages for sold property URLs |
| `deploy_app.yml` | Push to main | Build + deploy the web app |
| `generate_reports.yml` | Manual | Generate analysis reports |
| `tests.yml` | Pull request | Run the test suite |

---

## Data Pipeline Flow

```
Hemnet search pages (sold)
        │
        ▼
collect_sold_links_weekly.yml          — ongoing, area-adaptive, sold_age=1m
collect_sold_links_backfill.yml        — historical, month × area partitioning
        │
        │  data/raw/sold_properties_all_areas.csv
        ▼
collect_property_details_scheduled.yml — twice daily, reads master CSV
        │
        │  data/processed/property_details/gha_runs/
        ▼
src/data/aggregate_properties.py       — merges parquet → DuckDB `properties` table
        │
        ▼
train_model.py  →  models/price_model.joblib


Hemnet active listings
        │
        ▼
collect_active_listings_daily.yml      — links + details + predictions + archive
        │
        ├──► DuckDB `active_listings` table
        ├──► DuckDB `active_predictions` table
        └──► DuckDB `description_archive` table
                    │
                    ▼
          match_active_to_sold.py       — links descriptions to final sale prices
                    │
                    ▼
          train_text_pipeline.py        — trains NLP model once ≥50 matched pairs exist
```

---

## The 2,500-Result Limit

Hemnet's search API returns at most 2,500 results per query.  The project
handles this through **two-dimensional partitioning** when operating at
national scope:

### Ongoing weekly collection (`collect_sold_links_weekly.yml`)

Uses `--sold-age 1m` (last month).  At national scale, roughly 7,000–10,000
apartments sell per month.  Area-band partitioning alone (binary search on m²)
is sufficient — even popular sizes never exceed ~200 results per 1 m² band per
month.

### Historical backfill (`collect_sold_links_backfill.yml`)

For all-time historical data, area-only partitioning can overflow at popular
sizes (55–75 m²).  The backfill workflow combines **month window + area band**:

```
For each month M:
    For each area band [a, a+step] where count(M, a, a+step) < 2,400:
        scrape links
```

This is mathematically guaranteed to stay under the limit at any scope.  The
implementation passes `--sold-min YYYY-MM-01 --sold-max NEXT-MM-01` to
`collect_sold_links.py`, which in turn builds the Hemnet URL:

```
?item_types[]=bostadsratt
&sold_age=all&sold_min=YYYY-MM-01&sold_max=NEXT-MM-01
&living_area_min=A&living_area_max=B
&location_ids[]=ID          (optional)
```

### Resume capability

Both workflows support resuming after a timeout or failure:

- **Weekly**: each run uses a dated output directory
  (`data/raw/area_ranges_national/YYYYMMDD/`) with its own `progress.json`.
  Completed m² ranges are skipped on re-run.
- **Backfill**: each month gets its own directory
  (`data/raw/area_ranges_national/YYYYMM/`) and is committed independently.
  Re-triggering the workflow with the same date range skips already-completed
  months.

---

## `src/` — internal library modules

Modules under `src/` are not renamed by this convention; they are internal
APIs imported by the pipeline scripts.

```
src/
  scrapers/
    sold_properties_scraper.py  ← URL building + Playwright scraping for sold listings
    link_collector.py           ← search-page link extraction for active listings
    batch_manager.py            ← batch orchestration logic
    batch_manager_cli.py        ← CLI wrapper for batch_manager (invoked via -m)
    property_detail_scraper.py  ← individual property page parsing
    progress_tracker.py         ← SHA-256 fingerprint cache for deduplication
  models/
    prediction_service.py       ← LightGBM inference
    explainability.py           ← SHAP + narrative generator
    text_pipeline.py            ← TF-IDF Ridge text model
  data/
    aggregate_properties.py     ← parquet → DuckDB (sold)
    aggregate_active_listings.py← parquet → DuckDB (active) + predictions
    description_archive.py      ← persistent description store
```

---

## Adding a New Pipeline Step

1. Name the script `{verb}_{subject}.py` in `scripts/`.
2. Add a docstring explaining inputs, outputs, and CLI usage.
3. If it runs in CI, add a workflow `{verb}_{subject}_{frequency}.yml` in
   `.github/workflows/` following the pattern above.
4. Update this document and the pipeline flow diagram.
