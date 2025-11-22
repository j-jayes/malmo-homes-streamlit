# Property Detail Runner Checklist

**Date:** 2025-11-22  
**Task:** Plan GitHub Actions runner for property detail scraper  
**Priority:** High  
**Driver:** Stabilize historical backfill by replaying stored link inventory through the unified detail scraper.

---

## 📊 Current Link Inventory Snapshot

- Area-range CSV batches: 10 files (`0-31` → `53-54`) stored under `data/raw/area_ranges/` with **22,655** total sold-property links logged via adaptive scraping (counts per file range from 1,913–2,500).
- Latest raw capture `data/raw/hemnet_links_20251115_201403.csv` contains **159** active listing URLs with timestamps, confirming the link collector’s rolling feed works.
- `progress.json` indicates we stopped after the `53-54 m²` band, so downstream scrapers must support resumable execution and parametrized slices to keep GitHub-hosted minutes under control.

---

## 🎯 Runner Objectives

1. **Deterministic Input Selection**
   - Reuse existing CSV artifacts without editing them in-place.
   - Allow filtering by area-range file name + optional slice (offset, limit) so we can run “spot checks” with 5–20 URLs before scaling.

2. **Batch-Oriented Scraping**
   - Use `src/scrapers/batch_manager.py` to honor resume/metadata semantics, producing parquet batches + failure CSVs.
   - Default batch size 10 for CI-friendly dry runs; configurable via workflow inputs.

3. **Safe Output Handling**
   - Keep scraped parquet + metadata as artifacts (avoid git commits during early testing).
   - Upload JSON summary (counts, success rate, error buckets) to `$GITHUB_STEP_SUMMARY` for quick triage.

4. **Failure Visibility**
   - Preserve playwright logs, batch metadata, and the filtered URL subset as artifacts to reproduce issues locally.
   - Emit non-zero exit on <80% success for the sampled batch to surface schema or anti-bot regressions quickly.

---

## 🛠️ Workflow Specification (draft)

### Trigger + Inputs
- Event: `workflow_dispatch`
- Inputs (all strings/numbers to satisfy the [GitHub Actions workflow-dispatch contract](https://docs.github.com/en/actions/using-workflows/workflow-syntax-for-github-actions#onworkflow_dispatch)):
  - `source_csv` (string, required, default `data/raw/area_ranges/properties_0_31.csv`)
  - `max_records` (number, default `10`) → applied after offset.
  - `offset` (number, default `0`) → skip already processed rows when resuming.
  - `batch_size` (number, default `5`) → forwarded to BatchManager.
  - `headless` (boolean, default `true`).
  - `artifact_prefix` (string, default `property-detail-sample`).

### Job: `scrape-details`
- `runs-on: ubuntu-latest`
- `timeout-minutes: 90`
- Steps (all run inside `.venv` via `uv`):
  1. **Checkout** `actions/checkout@v4` with `fetch-depth: 0`.
  2. **Set up Python** `actions/setup-python@v5` (`3.11`).
  3. **Install uv** using curl bootstrap; add `$HOME/.cargo/bin` to `PATH`.
  4. **Install project deps**: `uv venv && source .venv/bin/activate && uv pip install -e .[scraping]`.
  5. **Install Playwright browsers**: `playwright install chromium --with-deps`.
  6. **Start Xvfb** (identical to sold batch workflow) and export `DISPLAY`.
  7. **Select subset**: run a tiny Python helper that reads `source_csv`, applies offset/limit, and writes `data/tmp/gha_property_subset.csv` (positionally stable, includes headers `url,property_id,area_range,...`).
  8. **Execute batch scrape**:
     ```bash
     uv run python -m src.scrapers.batch_manager_cli \
       --input data/tmp/gha_property_subset.csv \
       --output data/gha_property_batches \
       --batch-size ${{ inputs.batch_size }} \
       --headless ${{ inputs.headless }}
     ```
     (CLI wrapper to author: thin module around `BatchManager.process_all` honoring offset + stop-after `max_records`).
  9. **Summarize results** by parsing `metadata.json` (success/failure counts, average batch size) and `*_failures.csv` if present.
 10. **Upload artifacts** with `actions/upload-artifact@v4` (parquet, metadata, failure CSVs, raw subset CSV, playwright trace/logs if we persist them).
 11. **Post run summary** appended to `$GITHUB_STEP_SUMMARY` (counts, notable errors, artifact links).

### Resiliency Considerations
- Wrap main scraping step with `set -e` + custom trap to upload partial artifacts and exit 1 if success rate < threshold.
- Use `concurrency: property-detail-runner` to prevent overlapping expensive scraping jobs.
- Keep `permissions: contents: read` until we are ready to push data commits.

---

## ✅ Task Checklist

1. [ ] Create lightweight CLI (`src/scrapers/batch_manager_cli.py`) exposing `--input`, `--output`, `--max-records`, `--offset`, `--batch-size`, `--headless` arguments and delegating to `BatchManager`.
2. [ ] Author helper script (`scripts/select_property_subset.py` or inline Python step) that copies filtered rows into `data/tmp/gha_property_subset.csv` with deterministic ordering.
3. [ ] Draft workflow `.github/workflows/property_detail_runner.yml` implementing the spec above.
4. [ ] Add structured logging (JSON or key=value) inside CLI to make GH logs greppable (e.g., `SCRAPE_METRIC total_processed=10 success=9 failed=1`).
5. [ ] Document environment expectations inside `README` (how to invoke workflow via CLI, required secrets if any).
6. [ ] Dry-run locally with `uv run python src/scrapers/batch_manager_cli.py --input data/raw/area_ranges/properties_0_31.csv --max-records 5 --output data/tmp/dry_run` to confirm subset + metadata behavior before shipping workflow.
7. [ ] Configure artifact retention (7 days for smoke tests) and ensure failure CSVs are included for debugging.

---

## 📈 Success Criteria

- Workflow finishes within 45 minutes for ≤25 URLs.
- ≥90% schema validation success on sample batch; failures clearly enumerated.
- Artifacts include parquet, metadata, subset CSV, and failure details.
- `$GITHUB_STEP_SUMMARY` reports: total processed, success rate, top 3 error messages, artifact link.
- CLI + workflow both rely on `.venv` + `uv`, satisfying repository tooling standards.

---

## 🔜 Next Steps

1. Implement CLI + subset helper locally, add tests.
2. Commit workflow + helper scripts.
3. Trigger `gh workflow run property_detail_runner.yml --field source_csv=... --field max_records=5` for a canary batch.
4. Inspect run logs, artifact outputs, and adjust scraper (timeouts, selectors) before scaling to full backlog.

---

_This document will be updated as we execute each checklist item and capture run findings._
