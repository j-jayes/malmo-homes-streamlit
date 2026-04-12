# Malmö Housing Price Predictor

A machine learning application that predicts housing prices in Malmö, Sweden based on property characteristics and location.

## Overview

This application uses a Random Forest model trained on historical housing sales data from Malmö to predict property values. The interactive dashboard allows users to:

- Input property details
- Select property location on a map
- Get a price prediction
- View comparable properties
- Explore market trends and insights

## Features

- **Price Prediction**: Get an estimated market value based on property characteristics
- **Interactive Map**: Select location by clicking on a map
- **Market Insights**: View data on neighborhood price comparisons, price trends, and market factors
- **Validation**: Input constraints ensure values are within reasonable ranges

## Installation

### Prerequisites

- Python 3.8 or higher
- pip (Python package installer)

### Setup

1. Clone this repository:

```
git clone <repository-url>
cd # 🏠 Swedish Housing Market Analyzer

A comprehensive data pipeline and analytics platform for tracking and analyzing housing market trends across Sweden, starting with Malmö.

## 🎯 Project Overview

This project has **two distinct components** that work together:

### 🏛️ Component 1: Historical Market Analysis
**Backfill of sold properties across all housing types** to build a comprehensive historical database:
- Covers all 6 Hemnet housing types: apartments (`bostadsratt`), detached houses (`villa`), townhouses (`radhus`), vacation homes (`fritidshus`), land plots (`tomt`), and farms/estates (`gard`)
- National scope — all of Sweden
- Historical backfill: 2020 onwards (apartments complete; other types in progress)
- Build baseline for price trends and neighborhood analysis
- Train ML models on historical sales data

### 🔄 Component 2: Live Market Monitoring
**Ongoing tracking of active listings across all housing types** to identify opportunities:
- Daily scraping of all active property types listed on Hemnet nationally
- Weekly collection of newly sold links across all 6 housing types
- Track property lifecycle (listed → price changes → sold)
- Identify underpriced properties based on historical trends
- Compare asking prices to predicted fair value

### 🔗 The Connection
**Transition Tracking:** When active properties sell, we:
1. Match sold property to its original listing (by address/ID)
2. Calculate time-on-market (days from listing to sale)
3. Analyze asking price vs final price (negotiation insights)
4. Update our prediction models with fresh data
5. Validate our "underpriced" predictions against outcomes

### Key Features

- 🤖 **Automated Weekly Scraping** via GitHub Actions
- 📊 **DuckDB Database** with Parquet storage for efficient analytics
- 📈 **Historical Price Tracking** with inflation adjustment
- 🗺️ **Interactive Maps** showing property locations and market trends
- 📄 **Automated Reports** (HTML + PDF) published to GitHub Pages
- 🚀 **FastAPI + React** frontend (planned)
- 📱 **Streamlit MVP** for rapid prototyping

## 🏗️ Project Structure

```
malmo-homes-streamlit/
├── .github/
│   ├── workflows/          # CI/CD pipelines
│   └── checklists/        # Development tracking
├── src/
│   ├── scrapers/          # Web scraping modules
│   ├── data/              # Data processing & validation
│   ├── features/          # Feature engineering
│   ├── models/            # ML models (price prediction)
│   └── visualization/     # Plotting utilities
├── data/
│   ├── raw/               # Raw scraped data
│   ├── processed/         # Cleaned & validated data
│   ├── external/          # External datasets (inflation, census)
│   └── database/          # DuckDB database files
├── notebooks/             # Jupyter notebooks for exploration
├── reports/               # Quarto reports (HTML/PDF)
├── app/                   # Web application
│   ├── streamlit_app.py   # Streamlit MVP
│   ├── main.py            # FastAPI backend (planned)
│   ├── pages/             # Multi-page app
│   └── components/        # Reusable UI components
├── tests/                 # Unit tests
├── config/                # Configuration files
├── scripts/               # Standalone scripts
├── models/                # Saved ML models
└── docs/                  # Documentation
```

## 🚀 Quick Start

### Prerequisites

- Python 3.11+
- uv package manager

### Installation

```bash
# Clone the repository
git clone https://github.com/j-jayes/malmo-homes-streamlit.git
cd malmo-homes-streamlit

# Create virtual environment
uv venv

# Install dependencies
uv pip install -r requirements.txt

# Install Playwright browsers
.venv/bin/playwright install chromium

# Copy environment file
cp .env.example .env
# Edit .env with your configuration
```

### Running the Scraper

```bash
# Collect property links
python src/scrapers/link_collector.py

# Scrape individual properties
python src/scrapers/property_scraper.py
```

## 🧭 Property Detail Runner (2025 refresh)

The refreshed runner splits scraping into discrete stages so we can scale safely via GitHub Actions:

1. **Stage property manifests** – copy immutable CSVs from `data/raw/area_ranges/` (or live feeds) into `data/staging/property_links/`, one manifest per batch, and record the SHA-256 digest + ingestion timestamp (see `.github/checklists/2025-11-22-property-detail-runner-checklist.md`).
2. **Local dry-run** – validate selectors and schema with a tiny subset:

```bash
uv run python -m src.scrapers.batch_manager_cli \
   --input data/staging/property_links/properties_0_31.csv \
   --output-dir data/tmp/property_detail_dry_run \
   --max-records 5 \
   --batch-size 5
```

3. **Dispatch GitHub Actions via GitHub CLI** – once the workflow file lives on `main`, launch a canary run straight from your terminal (customize inputs as needed):

```bash
gh workflow run property_detail_runner.yml \
   --ref main \
   --field source_csv=data/staging/property_links/properties_0_31.csv \
   --field max_records=10 \
   --field offset=0 \
   --field batch_size=5 \
   --field headless=true \
   --field log_level=INFO
```

> 💡 Pass `--git-commit-interval N` to `batch_manager_cli` if you need local dry runs to mimic the GitHub Action’s periodic commits (the cron workflow uses `N=4`).

> ℹ️ GitHub only exposes `workflow_dispatch` triggers that exist on the default branch. Merge the workflow first, then use `--ref` to target feature branches if you need to ship canary code.

### Progress cache & deduplication

- `src/scrapers/progress_tracker.py` persists SHA-256 fingerprints of each scraped property (prefers `property_id`, falls back to URL) in `<output-dir>/progress_cache.json`.
- `batch_manager_cli` loads that cache automatically, skips already-processed rows during subset selection, and records successes from `BatchManager` so reruns remain idempotent.
- Use `--progress-cache /custom/path.json` to override the storage location or `--no-skip-processed` if you intentionally need to re-scrape.
- The cache is written alongside `metadata.json`, so clearing both files resets the run history for a given output directory.

### Staging discipline

- Only staging manifests feed the GitHub runner; raw captures stay untouched for reproducibility.
- After a batch succeeds, move its manifest from `data/staging/property_links/` to `data/archive/staged/` (or annotate it) so the backlog clearly shows what still needs enrichment.
- Downstream modelling jobs always read from `data/processed/property_details/`, never from staging.

### Running the Application

```bash
# Streamlit app
streamlit run app/streamlit_app.py

# FastAPI (when implemented)
uvicorn app.main:app --reload
```

## 📊 Data Pipeline

### Component 1: Historical Backfill (One-Time)

**Sold Properties Scraper:**
- 📅 **Time-based filtering** by month (2020-present)
- 🎯 **Target:** ~56,000 sold properties
- 📦 **Approach:** Monthly batches (~500 properties each)
- 💾 **Storage:** Parquet files → DuckDB
- ⏱️ **Execution:** Run locally or in large GitHub Actions batches
- 🔄 **Status:** One-time operation, then monthly updates only

**Data Extracted:**
- Final sold price & asking price
- Sold date & time on market
- Price change percentage
- Property details (rooms, area, location, etc.)
- Coordinates for mapping

### Component 2: Live Monitoring (Ongoing)

**Active Listings Scraper:**
- 📅 **Daily/Weekly scraping** pipelines
- 🎯 **Target:** Broad country-wide scan collecting ~2,500 active properties daily
- 🔍 **Purpose:** Find underpriced opportunities and store raw property descriptions in the `description_archive`
- 📊 **Compare:** Asking price vs predicted fair value
- 🚨 **Alerts:** Price drops, new listings, anomalies

**Transition Tracking:**
- 🔗 **Match:** Active listing descriptions → Later Sold property IDs
- 📝 **NLP Modelling:** Collect ad-copy to predict price premiums dynamically based on specific descriptive keywords.
- 📈 **Analyze:** Success rate of "underpriced" predictions
- ⏱️ **Calculate:** Time-on-market, negotiation patterns
- 🔄 **Update:** Retrain models with fresh sales data via automated DuckDB jobs

### 1. Data Collection Flow

```
┌──────────────────────────────────────────────────────────┐
│  HISTORICAL (One-Time Backfill)                          │
│  ┌────────────────────────────────────────────────────┐  │
│  │ Sold Properties (2020-2025)                        │  │
│  │ - Monthly scraping in batches                      │  │
│  │ - ~56k total properties                            │  │
│  │ - Final prices + property details                  │  │
│  └────────────────────────────────────────────────────┘  │
│                        ↓                                 │
│           [ DuckDB: sold_properties ]                    │
└──────────────────────────────────────────────────────────┘

┌──────────────────────────────────────────────────────────┐
│  ONGOING (Weekly Updates)                                │
│  ┌────────────────────────────────────────────────────┐  │
│  │ Active Listings (Current)                          │  │
│  │ - Weekly scraping every Sunday                     │  │
│  │ - ~1,500 active properties                         │  │
│  │ - Track asking prices + changes                    │  │
│  └────────────────────────────────────────────────────┘  │
│                        ↓                                 │
│           [ DuckDB: active_properties ]                  │
│                        ↓                                 │
│              [ ML Model Prediction ]                     │
│                        ↓                                 │
│        [ Identify Underpriced Properties ]               │
└──────────────────────────────────────────────────────────┘

┌──────────────────────────────────────────────────────────┐
│  TRANSITION (Weekly Check)                               │
│  ┌────────────────────────────────────────────────────┐  │
│  │ Match: Active → Sold                               │  │
│  │ - Find properties that sold this week              │  │
│  │ - Link to original listing                         │  │
│  │ - Validate predictions                             │  │
│  └────────────────────────────────────────────────────┘  │
│                        ↓                                 │
│         [ DuckDB: property_transitions ]                 │
│                        ↓                                 │
│           [ Update ML Models & Metrics ]                 │
└──────────────────────────────────────────────────────────┘
```

### 2. Data Storage

**DuckDB Database:**
- Main table: `properties` with full property details
- `price_history` for tracking price changes over time
- `neighborhoods` for aggregated area statistics
- Parquet backend for efficient queries

### 3. Data Processing

- Validation pipeline to catch scraping errors
- Deduplication by property ID
- Geocoding fallback for missing coordinates
- Inflation adjustment using SCB data
- Feature engineering for ML models

### 4. Analytics & Reporting

- Weekly Quarto reports (HTML + Typst PDF)
- Interactive dashboards (Streamlit/React)
- Price prediction models (sklearn pipelines)
- Trend analysis and forecasting

## 🔄 Automation

### GitHub Actions Workflows

| Workflow | Schedule | Description |
|---|---|---|
| `collect_active_listings_daily.yml` | Daily 06:00 UTC | Collects all active listings (all housing types) nationally; runs ML predictions |
| `collect_sold_links_weekly.yml` | Sunday 02:00 UTC | Collects newly-sold links (all 6 housing types) across Sweden for the past month |
| `collect_sold_links_backfill.yml` | Every 8h + manual | Historical backfill of sold links; loops housing types × months; resumes via `progress.json` |
| `collect_property_details_scheduled.yml` | 00:30 + 12:30 UTC | Scrapes full property detail pages for all collected links; updates DuckDB |

#### Active listings pipeline (`collect_active_listings_daily.yml`)
- Fetches all current Hemnet listings nationally with no `item_types` filter — all housing types are returned in one pass.
- The detail scraper extracts `housing_type` from each property's page JSON, so every record in the `active_listings` DuckDB table carries its correct type.

#### Sold links collection (weekly + backfill)
Both workflows use `scripts/collect_sold_links.py --housing-type <slug>` which sets `item_types[]=<slug>` in the Hemnet search URL.

**Weekly** (`collect_sold_links_weekly.yml`): loops over all 6 types, each writing to `data/raw/area_ranges_national/{housing_type}/{YYYYMMDD}/`. Results are consolidated into `data/raw/sold_properties_all_areas.csv` with a `housing_type` column.

**Backfill** (`collect_sold_links_backfill.yml`): outer loop over housing types × inner loop over calendar months. Set `housing_type=all` (default) to run all types, or select a single type to resume a specific backfill. Each month is committed independently for resumability. Output: `data/raw/area_ranges_national/{housing_type}/{YYYYMM}/`.

Area partitioning (Hemnet's 2,500-result limit): the adaptive binary-search strategy applies to all housing types. For low-volume types (`tomt`, `gard`) the algorithm finds the full 0–500 m² band is safe and makes a single request; for high-volume types (`bostadsratt`, `villa`) it narrows bands as needed.

#### Property detail scraper (`collect_property_details_scheduled.yml`)
Reads `data/raw/sold_properties_all_areas.csv` (all types), skips already-processed URLs via a SHA-256 fingerprint cache, and extracts all available fields. Type-specific fields (`plot_area`, `monthly_fee`, etc.) are stored as `Optional` columns and are `null` for types that don't carry them.

### Scraper CLI reference

```bash
# Backfill one housing type for one month (area-adaptive)
python scripts/collect_sold_links.py \
  --housing-type villa \
  --sold-min 2024-03-01 --sold-max 2024-04-01 \
  --output-dir data/raw/area_ranges_national/villa/202403 \
  --headless

# Collect active listings (all types, national)
python scripts/collect_active_listings.py --predict

# Supported --housing-type values:
#   bostadsratt  villa  radhus  fritidshus  tomt  gard
```

## 🗺️ Coverage

### Housing Types
| Type | Swedish | Backfill status | Active listings |
|------|---------|-----------------|-----------------|
| `bostadsratt` | Bostadsrätt (apartment) | ✅ Complete (2020–2025) | ✅ Daily |
| `villa` | Villa (detached house) | ⏳ In progress | ✅ Daily |
| `radhus` | Radhus (townhouse) | ⏳ In progress | ✅ Daily |
| `fritidshus` | Fritidshus (vacation home) | ⏳ In progress | ✅ Daily |
| `tomt` | Tomt (land/plot) | ⏳ In progress | ✅ Daily |
| `gard` | Gård (farm/estate) | ⏳ In progress | ✅ Daily |

### Geographic scope
- ✅ **All of Sweden** — national scope for all workflows (no location filter by default)
- Location filtering available via `--location-id` for targeted city/region runs

## 📈 Analytics Features

### Implemented
- ✅ Property price distributions
- ✅ Price per m² by neighborhood
- ✅ Historical price tracking
- ✅ Market trends (Inflation adjusted)
- ✅ 🔮 Price prediction ML model (Numerical baseline)
- ✅ 📝 NLP Pipeline for Property text-description modelling
- ✅ 🔔 Automated active listing monitoring and DuckDB integration

### Planned
- 📊 Advanced Market trend forecasting
- 🏘️ Deep Neighborhood profiling
- 🔍 Property comparison tool
- 🔔 Price drop alerts
- ⏱️ Days-on-market analysis
- 💰 Sold vs asking price analysis

## 🛠️ Technology Stack

- **Language:** Python 3.11+
- **Package Manager:** uv
- **Scraping:** Playwright
- **Database:** DuckDB + Parquet
- **Data Processing:** Pandas, Polars
- **ML:** scikit-learn
- **Visualization:** Plotly, Folium
- **Reports:** Quarto (Typst PDF)
- **Frontend (MVP):** Streamlit
- **Frontend (Planned):** FastAPI + React
- **CI/CD:** GitHub Actions
- **Hosting:** GitHub Pages

## 📝 Development

### Project Phases

#### 🏛️ Historical Component

1. **Phase 1A: Link Collection (Sold)** ✅
   - Time-based filtering by month
   - Pagination handling
   - CSV export with property URLs

2. **Phase 1B: Historical Data Scraping** 🚧
   - Unified property scraper (sold + active)
   - Extract all sold property details
   - Batch processing (100 properties at a time)
   - Parquet storage for efficiency

3. **Phase 1C: Historical Database** ⏳
   - Load ~56k sold properties to DuckDB
   - Build price history tables
   - Neighborhood aggregations
   - ML model training dataset

#### 🔄 Live Monitoring Component

4. **Phase 2A: Active Listings Scraping** ⏳
   - Weekly automated collection
   - Track price changes over time
   - Store in separate active_properties table

5. **Phase 2B: Price Prediction** ⏳
   - Train ML model on historical sales
   - Predict fair value for active listings
   - Identify underpriced properties
   - Generate weekly opportunity reports

6. **Phase 2C: Transition Tracking** ⏳
   - Match active → sold properties
   - Calculate time-on-market
   - Validate prediction accuracy
   - Update models with new data

#### 📊 Analytics & Interface

7. **Phase 3A: Analytics Dashboard** ⏳
   - Historical market trends
   - Current market snapshot
   - Underpriced property alerts
   - Prediction accuracy metrics

8. **Phase 3B: Web Interface** ⏳
   - Streamlit MVP (rapid prototyping)
   - FastAPI + React (production)
   - Interactive maps and filters
   - Email/SMS alerts for opportunities

### Testing

```bash
# Run tests
pytest tests/

# Run with coverage
pytest --cov=src tests/
```

### Code Quality

```bash
# Format code
black src/ tests/

# Lint
flake8 src/ tests/

# Type check
mypy src/
```

## 📄 Documentation

- [Scraping Guide](docs/scraping_guide.md)
- [API Documentation](docs/api_docs.md)
- [Deployment Guide](docs/deployment_guide.md)
- [Contributing Guidelines](CONTRIBUTING.md)

## 🤝 Contributing

Contributions are welcome! Please read our [Contributing Guidelines](CONTRIBUTING.md) first.

## 📜 License

This project is for educational purposes only. Please respect Hemnet's terms of service and robots.txt.

## 🙏 Acknowledgments

- Hemnet.se for providing property data
- SCB (Statistics Sweden) for inflation data
- Contributors and maintainers

## 📧 Contact

For questions or suggestions, please open an issue on GitHub.

---

**Note:** This project is under active development. Features and structure may change.
```

2. Create a virtual environment (optional but recommended):

```
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. Install required packages:

```
pip install -r requirements.txt
```

### Required Packages

Create a `requirements.txt` file with the following dependencies:

```
pandas
numpy
scikit-learn
streamlit
folium
streamlit-folium
matplotlib
seaborn
joblib
```

## Running the Application

1. Ensure the dataset file `hemnet_properties.csv` is in the project directory
2. Start the Streamlit application:

```
streamlit run app.py
```

3. The application will open in your default web browser at `http://localhost:8501`

## Files

- `app.py`: The main Streamlit application
- `malmo_housing_price_model.py`: Module with model definition and data processing functions
- `hemnet_properties.csv`: Dataset of housing sales (not included in repo - must be provided separately)

## Model Details

The prediction model is a Random Forest Regressor trained on the following features:

- **Location**: Neighborhood, geographic coordinates
- **Property characteristics**: Living area, number of rooms, year of construction
- **Building details**: Floor number, total floors, elevator presence
- **Economic factors**: Monthly fee

## Data Preparation

Before using the application, ensure your dataset file (`hemnet_properties.csv`) is properly formatted with the following columns:

- final_price
- location
- ownership_form
- number_of_rooms
- living_area
- balcony
- year_of_construction
- fee
- operational_cost
- leasehold_fee
- housing_association
- sale_year
- sale_month
- sale_day
- floor_number
- top_floor_number
- elevator_presence
- latitude
- longitude

## Limitations

- The model is based on historical data and may not capture very recent market shifts
- Unique property features (renovations, views, etc.) are not captured


## Roadmap

* Better models; tree-based and neural networks
* Better user interface esp with clicking about
* Make a mapping of coordinates on to neighbourhoods -
