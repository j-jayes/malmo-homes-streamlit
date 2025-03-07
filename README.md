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
cd malmo-housing-price-predictor
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
