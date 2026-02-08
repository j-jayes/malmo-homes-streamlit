# 2026-02-08 NLP Text Pipeline — Data Collection Checklist

## Context
Hemnet removes ad descriptions from sold property pages, so descriptions
are only available while a listing is active.  This checklist tracks the
data-collection infrastructure needed before NLP modelling can begin.

## Completed

- [x] **Audit description coverage** — Confirmed all 22,891 sold properties
      have NULL descriptions; active listings have rich text (900–2,000 chars).
- [x] **Create `DescriptionArchive` class** (`src/data/description_archive.py`)
      — Persistent DuckDB table with INSERT-or-IGNORE + `last_seen` update.
- [x] **Integrate into aggregation pipeline** (`src/data/aggregate_active_listings.py`)
      — `upsert_from_parquet()` runs before replacing `active_listings`.
- [x] **Backfill existing data** (`scripts/backfill_description_archive.py`)
      — Seeded archive with 3 test descriptions.
- [x] **Verify idempotency** — Re-running backfill adds 0 new rows.
- [x] **Document NLP roadmap** (`docs/NLP_ROADMAP.md`)
      — Three-phase plan: TF-IDF → SBERT embeddings → SHAP explainability.

## Next Steps (when ~200+ descriptions accumulated)

- [ ] **Run full active listings scrape** — `python scripts/scrape_active_listings.py --predict`
      to collect all ~700 Malmö bostadsrätt descriptions.
- [ ] **Create TF-IDF exploration notebook** — `notebooks/text_analysis_exploration.ipynb`
      with Swedish preprocessing, word frequencies, correlation with asking price.
- [ ] **Build `TextFeatureExtractor` class** — `src/features/text_features.py`
      with TF-IDF pipeline, Swedish stop words, custom domain stop words.
- [ ] **Train residual model** — Predict asking price from structural features,
      compute residual, fit Ridge/Lasso on TF-IDF → residual.
- [ ] **Power words ranking** — Top-N premium/discount words bar chart.
- [ ] **Frontend: Ad Analyzer page** — `POST /analyze-text` endpoint +
      `AdAnalyzer.tsx` component.
