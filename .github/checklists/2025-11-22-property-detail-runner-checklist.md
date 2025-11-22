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

## 🔄 Pipeline Refinement Plan (2025-11-22 review)

- **Stage 1 — Link Capture (`data/raw/area_ranges/` + rolling feeds)**
   - Keep the existing link collectors focused on high-volume acquisition.
   - Immediately copy fresh batches into `data/staging/property_links/` with a manifest that records source CSV, ingestion timestamp, and SHA-256 digest so we can detect drift.
- **Stage 2 — Detail Scrape in Actions**
   - The GitHub Actions runner consumes only staging manifests, keeping raw captures immutable and simplifying retries.
   - Each scrape publishes hashed property IDs to a progress cache so subsequent runs can skip already-enriched listings regardless of staging contents.
- **Stage 3 — Processed Store (`data/processed/property_details/`)**
   - Persist parquet outputs + metadata per batch inside deterministic run directories (e.g., `data/processed/property_details/gha_runs/20251122T2145Z`).
   - Once a batch passes validation, move its manifest entry from staging to `data/archive/staged/` so unprocessed work remains visible.
   - Downstream modelling/analytics jobs read exclusively from processed data, never from staging or raw.
- **Stage 4 — Analytics & Reporting**
   - Feature engineering, ML training, and dashboards rely on the processed store, ensuring reproducibility.
- **Operational guardrails**
   - Workflow inputs reference staging manifests, GH summaries surface metrics, and artifacts carry everything required for local replay.
   - Progress cache + staging separation provide idempotency and a clean audit trail of what remains to scrape.

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

### Repository persistence add-on (2025-11-22 update)

- After successful scraping and validation, the job writes the generated parquet outputs + metadata into `data/processed/property_details/gha_runs/<timestamp>/` before committing.
- Configure `permissions: contents: write` for `scrape-details` and reuse `${{ secrets.GITHUB_TOKEN }}` so the workflow can `git commit` + `git push` without a PAT, following GitHub's [automatic token authentication guidance](https://docs.github.com/en/actions/security-guides/automatic-token-authentication).
- Commit message format: `ci: ingest property details <timestamp> (<source_csv> offset=<offset> max=<max_records>)`.
- Upload artifacts even after committing so we retain zipped copies + logs outside the repo history.

### Resiliency Considerations
- Wrap main scraping step with `set -e` + custom trap to upload partial artifacts and exit 1 if success rate < threshold.
- Use `concurrency: property-detail-runner` to prevent overlapping expensive scraping jobs.
- Keep `permissions: contents: read` until we are ready to push data commits.

## 📂 Repo Storage Strategy (2025-11-22 update)

- **Destination layout** — `data/processed/property_details/gha_runs/<YYYYMMDDTHHMMSSZ>/` containing `batch_*.parquet`, `metadata.json`, `failures.csv`, and the post-run `progress_cache.json` snapshot for auditability.
- **Run index** — maintain `data/processed/property_details/gha_runs/index.jsonl` with one JSON document per workflow invocation recording timestamp, `source_csv`, offsets, `max_records`, success metrics, and artifact URL.
- **Idempotency** — if a folder for the timestamp already exists, append `-retryN` to the directory name rather than overwriting; leverage the hashed progress cache to skip properties already persisted.
- **Git hygiene** — ensure `.gitignore` allows the processed run directories while temporary Playwright traces remain ignored under `data/tmp/`. Only commit curated parquet + metadata artifacts.
- **Automation** — workflow runs `git add data/processed/property_details/gha_runs` + `git add data/processed/property_details/gha_runs/index.jsonl`, commits, and pushes using `${{ secrets.GITHUB_TOKEN }}` scoped with `contents: write`.

## 🚀 Upcoming 100-property Run Plan

- **Inputs** — `source_csv=data/raw/area_ranges/properties_0_31.csv`, `offset=0`, `max_records=100`, `batch_size=10`, `headless=true`.
- **Output expectations** — new folder `data/processed/property_details/gha_runs/20251122T2215Z/` (timestamp captured via `date -u +%Y%m%dT%H%M%SZ`) plus index entry summarizing counts + artifact link.
- **Success guardrail** — workflow fails fast if success rate falls below 90% or more than 5 consecutive failures occur, preventing noisy commits.
- **Monitoring** — `gh run watch <run_id>` tailors logs; step metrics appended to `$GITHUB_STEP_SUMMARY` for asynchronous review.

---

## ✅ Task Checklist

1. [x] Create lightweight CLI (`src/scrapers/batch_manager_cli.py`) exposing `--input`, `--output`, `--max-records`, `--offset`, `--batch-size`, `--headless` arguments and delegating to `BatchManager`.
2. [ ] Author helper script (`scripts/select_property_subset.py` or inline Python step) that copies filtered rows into `data/tmp/gha_property_subset.csv` with deterministic ordering.
3. [x] Draft workflow `.github/workflows/property_detail_runner.yml` implementing the spec above.
4. [ ] Add structured logging (JSON or key=value) inside CLI to make GH logs greppable (e.g., `SCRAPE_METRIC total_processed=10 success=9 failed=1`).
5. [ ] Document environment expectations inside `README` (how to invoke workflow via CLI, required secrets if any).
6. [ ] Dry-run locally with `uv run python src/scrapers/batch_manager_cli.py --input data/raw/area_ranges/properties_0_31.csv --max-records 5 --output data/tmp/dry_run` to confirm subset + metadata behavior before shipping workflow.
7. [ ] Configure artifact retention (7 days for smoke tests) and ensure failure CSVs are included for debugging.
8. [ ] Trigger `property_detail_runner` workflow via `gh` with ≤5 records to validate remote execution path.
9. [ ] Record run findings (success metrics, failures, artifact locations) back into this checklist for traceability.
10. [x] Add hashed progress cache + CLI skip flag so reruns avoid already processed properties.

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

## 📝 Run Log

- 2025-11-22 — `gh workflow run property_detail_runner.yml --ref feature/property-detail-runner ...` failed with `HTTP 404` because GitHub only registers `workflow_dispatch` definitions that live on the default branch. Reference: [Manually running a workflow](https://docs.github.com/en/actions/how-tos/manage-workflow-runs/manually-run-a-workflow). Next step: raise a PR and land the workflow on `main`, then re-trigger the canary run.
- 2025-11-22 — First run on `main` failed mid-job due to missing `pyarrow`; resolved by promoting `pyarrow` to core dependencies and re-installing via `uv pip install -e .[scraping]`.
- 2025-11-22 — Second run reached summary step but crashed with `IndentationError` when writing to `$GITHUB_STEP_SUMMARY`; fixed indentation in `.github/workflows/property_detail_runner.yml` and ready to re-dispatch.
- 2025-11-22 — Third run hit a `SyntaxError` in `progress_tracker.py` (leftover Markdown fence); removed the stray characters so the module imports cleanly before retrying.
- 2025-11-22 — Fourth run (ID `19601674979`) completed successfully for 5 records: 100% success rate, new artifacts archived, validated Playwright/Xvfb stack.
