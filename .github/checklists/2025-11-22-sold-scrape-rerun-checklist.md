# Sold Properties Scrape Rerun Checklist

**Date:** 2025-11-22  \
**Task:** Resume adaptive area-range scraping for sold listings via GitHub Actions  \
**Priority:** Critical  \
**Driver:** Finish Malmö historical sold-property link inventory up to 500 m² while keeping runs resumable and observable.

---

## 🧭 Situation Snapshot

- Workflow: `.github/workflows/scrape_sold_batch.yml` (adaptive area partitioning with resumable progress + git commits).
- Latest local artifacts under `data/raw/area_ranges/` cover **10 ranges (0–54 m²)** totaling **22,655 links** per `progress.json`.
- Most recent GH run reportedly exhausted the 6h window; need to confirm scope, final logs, and whether commits/pushes landed.
- Remaining area coverage: roughly **54–500 m²**, likely >40 bins even with adaptive steps; expect multiple workflow invocations.

---

## 🎯 Objectives

1. **Audit last run** — Inspect GH Actions history (duration, completion state, committed ranges) using `gh run` commands.
2. **Validate resume point** — Cross-check `progress.json`, committed CSVs, and GH logs to ensure the next invocation should start at ≥54 m².
3. **Relaunch workflow** — Trigger `scrape_sold_batch.yml` from CLI with adjusted `min_area`, `max_area`, and `initial_step` to continue scraping without rework.
4. **Document findings** — Capture observations (bottlenecks, safe guards, next follow-ups) directly in this checklist for future operators.

---

## 🔄 Action Plan

1. _Run diagnostics_
   - `gh run list --workflow scrape_sold_batch.yml --limit 5` to identify the 6h execution (elapsed, conclusion).
   - `gh run view <run-id> --log` to skim critical sections (scraper output, commit summaries, failure cause if any).
2. _Correlate progress_
   - Compare GH log statements with `data/raw/area_ranges/progress.json` + CSV timestamps to ensure local repo reflects the latest scraped ranges.
3. _Decide resume parameters_
   - Choose `min_area` = 54 (next unprocessed) and tune `initial_step` (likely 3–5) so dense ranges stay under result limit.
   - Keep `max_pages` at 50, `max_area` up to 500, and rely on adaptive splitting for the remainder of the spectrum.
4. _Trigger rerun_
   - Execute `gh workflow run scrape_sold_batch.yml --field min_area=54 --field max_area=500 --field initial_step=50 --field max_pages=50` (adjust once diagnostics confirm needs).
   - Use `gh run watch <new-run-id>` for realtime monitoring until the job stabilizes.
5. _Update checklist_
   - Log run IDs, success/failure notes, and follow-up tasks (e.g., if we need smaller initial steps or additional guards).

---

## 🧪 Diagnostics Log (2025-11-22)

- `gh run list --workflow scrape_sold_batch.yml --limit 5` shows run `19409988609` (started `2025-11-16T18:19Z`) cancelled after **5h50m**, plus two short-lived cancelled attempts and one 3m success (likely smoke test).
- `gh run view 19409988609 --log` confirms the job completed area band `53-54 m²` (2,500 links, committed/pushed) and started `54-55 m²` (2,429 hits → 49 pages) before the workflow was cancelled while uploading artifacts.
- Logs show repeat `Page.wait_for_selector` timeouts per page yet each retry still captures 50 results, suggesting Cloudflare jitter rather than fatal errors. Runtime dominated by 50-page loops per dense range.
- Artifacts (id `4583239895`) captured 11 CSV/JSON outputs, validating automatic checkpointing even on cancellation.

## 🧮 Approach Assessment

- The adaptive range finder correctly narrows dense segments to 1 m² slices but currently accepts ranges slightly above the `SAFE_LIMIT` (e.g., 54–55 m² → 2,429 results) which still forces nearly 50 pages and ~6h runtime. Consider tightening `SAFE_LIMIT` heuristics or capping `max_pages` for ultra-dense bins to avoid timeouts.
- Progress tracking + git commits behaved as intended: after each finished range we write CSV + JSON to `data/raw/area_ranges/` and push, keeping state resumable; `progress.json` aligns with run logs (next start `54 m²`).
- Headless Playwright continues to function but repeated `wait_for_selector` warnings slow each page; adding exponential backoff or enabling `page.wait_for_timeout` between navigations might keep each iteration under 10s and reduce total runtime.
- Given the remaining 54–500 m² span, we should split execution into multiple workflow runs (e.g., 54–80, 80–120, 120–500) instead of one marathon job to stay within GH's 6h limit.

## 📌 Next Actions (Nov 22)

1. Launch `scrape_sold_batch.yml` with `min_area=54`, `max_area=120`, `initial_step=25`, `max_pages=50` to finish the high-density condo range without touching larger apartments yet.
2. Monitor via `gh run watch <id>` for the first 15 minutes; if page loops still take ~45s, bail and rerun with even smaller `max_area` bands (e.g., 10 m² increments) to prevent timeouts.
3. After completion, update this checklist with the new run ID, duration, and whether additional runs are needed for 120–500 m².

---

## ✅ Checklist

- [x] Capture GH Actions history + notes (run IDs, outcomes, duration).
- [x] Verify local progress artifacts align with GH reports (no missing CSVs).
- [x] Launch resumed workflow with appropriate parameters.
- [ ] Monitor run to confirm it progresses past prior stopping point.
- [ ] Record outcomes + next actions here (e.g., if another run is queued, or if the scrape completes up to 500 m²).

---

## 📝 Run Log

- 2025-11-22 22:28 UTC — Triggered `scrape_sold_batch.yml` via `gh workflow run` with `min_area=54`, `max_area=120`, `initial_step=25`, `max_pages=50`. Run ID `19602107194` currently `in_progress`; expect completion <6h given narrower span. Will monitor with `gh run watch 19602107194`.

---

_This checklist will be updated throughout the rerun process so future maintainers know exactly what was done and why._
