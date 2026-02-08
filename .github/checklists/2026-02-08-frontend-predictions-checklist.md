# 2026-02-08 Frontend Predictions Checklist

## Goal
Display sold properties with actual price vs. ML-predicted price on the map and in a "Best Deals" section.

## Architecture
- Pre-computed predictions stored in DuckDB `predictions` table (batch pipeline)
- Backend JOINs `properties` + `predictions` and serves enriched data
- Frontend shows color-coded markers + deal rankings

## Tasks

- [x] Run batch predictions (`scripts/batch_predict.py`)
- [x] Fix NA handling in `scripts/batch_predict.py`
- [x] Re-run batch predictions to fill gaps (22,855 predictions)
- [x] Update `app/backend/database.py` — add `get_properties_with_predictions()`, `get_best_deals()`
- [x] Update `app/backend/models.py` — add `PropertyWithPrediction` response model
- [x] Update `app/backend/main.py` — add `/properties/predicted` and `/deals` endpoints
- [x] Update `app/frontend/src/api/client.ts` — extend types, add API calls
- [x] Update `app/frontend/src/components/Map.tsx` — color-coded CircleMarkers, enriched popups
- [x] Create `app/frontend/src/components/BestDeals.tsx` — deal rankings sidebar
- [x] Update `app/frontend/src/App.tsx` — replace placeholder, wire in predictions
- [x] Update `app/frontend/src/components/StatsPanel.tsx` — add model stats card
- [x] Test end-to-end (backend + frontend)
- [x] Clean up temp files
- [ ] Commit and push
