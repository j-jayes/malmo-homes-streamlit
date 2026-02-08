# NLP Text Analysis Roadmap

## Motivation

Hemnet property listings include rich Swedish ad text written by estate
agents.  We hypothesise that specific word choices and phrasing
correlate with higher (or lower) sale prices — even after controlling for
structural features like living area, rooms, and location.

If we can quantify the "description premium" we can:

1. Surface **power words** that are associated with above-predicted prices.
2. Build an **ad-writing assistant** that suggests improvements to listing
   descriptions.
3. Add a **text feature** to the price model that may improve accuracy.

## Critical Data Constraint

Hemnet **removes ad descriptions from sold property pages**.  The
`SoldPropertyListing` Apollo State object does not include a
`description` field, so the ~23 k sold properties in our database have
`NULL` descriptions.

Active (for-sale) listings **do** include descriptions — typically
900–2 000 characters of rich Swedish real estate language.

### Implication

We cannot simply train on `(description, final_price)` pairs today.
Instead, we need a two-step approach:

| Step | What | When |
|------|------|------|
| **Accumulate** | Archive descriptions from daily active-listing scrapes into a persistent `description_archive` table. | Now (implemented) |
| **Match** | When a property sells, join its archived description to its final sale price via `property_id`. | After weeks/months of accumulation |
| **Train** | Use matched `(description, final_price)` pairs for supervised NLP modelling. | When ≥ 200–500 matched pairs exist |

In the interim, we can use `(description, asking_price)` pairs from active
listings for exploratory TF-IDF analysis.

---

## Phase 1 — TF-IDF + Bag of Words (exploratory)

**Goal:** Identify individual words and bi-grams correlated with
asking-price residuals (actual price minus model-predicted price).

### Approach

1. Load descriptions from `description_archive`.
2. Predict asking price from structural features using the existing
   LightGBM model → compute residual per listing.
3. Preprocess text:
   - Lowercase, strip HTML tags.
   - Remove Swedish stop words (NLTK `swedish` list + custom real-estate
     stop words like *rum*, *kvm*, *bostadsrätt*).
4. Fit `TfidfVectorizer(max_features=2000, ngram_range=(1,2), sublinear_tf=True)`.
5. Train a Ridge / Lasso regression: TF-IDF matrix → residual.
6. Rank features by coefficient magnitude → **"power words"** and
   **"discount words"**.

### Deliverables

- `notebooks/text_analysis_exploration.ipynb` — interactive exploration.
- `src/features/text_features.py` — reusable TF-IDF preprocessing class.
- Power-word ranking table + bar chart for the frontend.

### Requirements

- Already installed: `scikit-learn`, `pandas`.
- New: `nltk` (for Swedish stop words).

---

## Phase 2 — Swedish Sentence Embeddings

**Goal:** Replace hand-crafted TF-IDF features with dense embeddings
that capture semantic meaning.

### Model Choice

| Model | Dimensions | Language | License |
|-------|-----------|----------|---------|
| `KBLab/sentence-bert-swedish-cased` | 768 | Swedish | Apache-2.0 |

This is a Swedish SBERT model trained by the Royal Library of Sweden
(KB) and is the standard choice for Swedish semantic similarity.

### Approach

1. Encode each description → 768-d vector using SBERT.
2. Optionally reduce to 50–100 dims with PCA/UMAP.
3. Concatenate embedding features with structural features.
4. Train LightGBM on the combined feature set.
5. Compare R² / MAE to the structure-only model.

### Literature Context

Academic studies (Nowak & Smith 2017, Sirmans et al. 2005, Beracha &
Wintoki 2013) have found a **2–8 % improvement** in price prediction
accuracy when text features are added to hedonic models.

### Requirements

- `sentence-transformers` (~500 MB model download).
- `torch` (CPU inference is sufficient).

---

## Phase 3 — SHAP Text Explainability + Frontend

**Goal:** Per-word attribution so users can see *which words* in their
ad increase or decrease the predicted price.

### Approach

1. Use `shap.Explainer` with a text masker on the trained model.
2. For each word in the description, compute the marginal SHAP value.
3. Render highlighted text in the frontend: green for positive,
   red for negative impact.

### Frontend Features

- **Ad Analyzer page:** User pastes their listing description →
  backend tokenises → SHAP attribution → highlighted text returned.
- **Power Words panel:** Top-N words ranked by average SHAP value
  across the corpus, shown as a horizontal bar chart.
- **Suggestions:** If a listing description is missing high-value
  words, suggest adding them.

### Requirements

- `shap>=0.43`.
- New FastAPI endpoint: `POST /analyze-text`.
- New React component: `AdAnalyzer.tsx`.

---

## Data Collection Status

| Metric | Value |
|--------|-------|
| Descriptions archived | 3 (test run) |
| Avg. description length | 1 462 chars |
| Neighborhoods covered | 3 |
| Matched to sold properties | 0 |
| Estimated full Malmö scrape | ~700 listings |
| Days to first matched pairs | ~30–90 |

The daily GitHub Actions workflow (`scrape_active_listings.yml`) runs
at 06:00 UTC and now automatically archives descriptions via the
`DescriptionArchive` integration in `aggregate_active_listings.py`.

---

## Architecture

```
┌───────────────────┐     ┌──────────────────────┐
│  Hemnet active    │────▶│  scrape_active_      │
│  listing pages    │     │  listings.py          │
└───────────────────┘     └──────────┬───────────┘
                                     │ Parquet files
                                     ▼
                          ┌──────────────────────┐
                          │  aggregate_active_    │
                          │  listings.py          │
                          └──────┬───────┬───────┘
                                 │       │
                    ┌────────────┘       └────────────┐
                    ▼                                  ▼
          ┌─────────────────┐              ┌─────────────────────┐
          │ active_listings │              │ description_archive │
          │ (replaced daily)│              │ (accumulates)       │
          └─────────────────┘              └──────────┬──────────┘
                                                      │
                                           JOIN on property_id
                                                      │
                                                      ▼
                                           ┌──────────────────┐
                                           │ properties       │
                                           │ (sold, with      │
                                           │  final_price)    │
                                           └──────────────────┘
```

## File Inventory

| File | Purpose |
|------|---------|
| `src/data/description_archive.py` | `DescriptionArchive` class — persistent DuckDB upsert logic |
| `src/data/aggregate_active_listings.py` | Calls `DescriptionArchive.upsert_from_parquet()` before replacing `active_listings` |
| `scripts/backfill_description_archive.py` | One-time backfill from existing Parquet files |
| `docs/NLP_ROADMAP.md` | This document |
