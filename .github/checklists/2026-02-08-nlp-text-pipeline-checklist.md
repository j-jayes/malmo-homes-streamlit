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

- [x] **Update scraper for all Sweden** — Empty location_id for country-wide scraping,
      GHA timeout set to 350 min (5h50m), max_pages=50 (Hemnet cap of 2,500 listings).
- [x] **Build `TextFeatureExtractor` class** — `src/features/text_features.py`
      with TF-IDF pipeline, Swedish stop words, custom domain stop words,
      agent boilerplate stripping.
- [x] **Build `TextPricePipeline` class** — `src/models/text_pipeline.py`
      with residual computation, Ridge regression, power-word ranking.
- [x] **Expand description archive schema** — Added city, lat, lng, building_year,
      association_fee, housing_type, ownership_type for accurate residual computation.
- [x] **Run 200 active listings scrape** — 195/200 successful (97.5%) across
      83 cities, 146 neighborhoods. Lat range 55.4°–63.8°N (all Sweden).
- [x] **Train text pipeline** — R²=0.044 on 193 docs (expected with all-Sweden mix).
      Premium words: toppläge, fönsterpartier, gäst wc, låg belåning.
      Discount words: lantlig, bara flytta, campus, renoverade.
- [ ] **Power words ranking** — Top-N premium/discount words bar chart.
- [ ] **Frontend: Ad Analyzer page** — `POST /analyze-text` endpoint +
      `AdAnalyzer.tsx` component.
