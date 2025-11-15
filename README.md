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

This project scrapes property listings from Hemnet.se, stores them in a DuckDB database, and provides interactive analytics through a modern web interface. The system tracks both active listings and sold properties, maintaining historical price data with inflation adjustment for accurate market analysis.

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

### Running the Application

```bash
# Streamlit app
streamlit run app/streamlit_app.py

# FastAPI (when implemented)
uvicorn app.main:app --reload
```

## 📊 Data Pipeline

### 1. Data Collection

**Active Listings:**
- Weekly scraping of current property listings
- Smart pagination to handle 2,500+ results per query
- Rate-limited requests (10 req/min)
- Cloudflare handling via visible browser

**Sold Properties:**
- Historical sold property data (different URL structure)
- Final sale prices vs asking prices
- Days on market calculation

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

**Weekly Scraping** (Sunday 00:00 UTC):
```yaml
# .github/workflows/scrape_weekly.yml
- Collect new property links
- Scrape property details
- Update DuckDB database
- Generate reports
- Commit to gh-pages branch
```

**Report Generation** (Sunday 01:00 UTC):
```yaml
# .github/workflows/generate_reports.yml
- Run Quarto reports
- Generate HTML and PDF
- Deploy to GitHub Pages
```

## 🗺️ Coverage

### Current Regions
- ✅ **Malmö** (Location ID: 17989)

### Planned Expansion
- ⏳ Stockholm
- ⏳ Gothenburg
- ⏳ All of Sweden

## 📈 Analytics Features

### Implemented
- Property price distributions
- Price per m² by neighborhood
- Historical price tracking
- Basic market trends

### Planned
- 🔮 Price prediction ML model
- 📊 Market trend forecasting
- 🏘️ Neighborhood profiling
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

1. **Phase 1: Simple Link Collection** ✅
   - Single page scraping
   - Basic pagination
   - CSV export

2. **Phase 2: Smart Filtering Strategy** 🚧
   - Handle 2,500 result limit
   - Hierarchical filter splitting
   - Full coverage of Malmö

3. **Phase 3: Database Integration** ⏳
   - DuckDB schema design
   - Data validation pipeline
   - Historical tracking

4. **Phase 4: Analytics & ML** ⏳
   - Price prediction model
   - Trend analysis
   - Neighborhood profiling

5. **Phase 5: Web Interface** ⏳
   - Streamlit MVP
   - FastAPI + React migration
   - Interactive maps

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
