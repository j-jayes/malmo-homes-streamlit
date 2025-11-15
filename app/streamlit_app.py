import streamlit as st
import pandas as pd
import numpy as np
import pickle
import folium
from streamlit_folium import folium_static
from folium.plugins import Draw
import matplotlib.pyplot as plt
import seaborn as sns
import os
import joblib
from malmo_housing_price_model import load_and_preprocess_data, prepare_features, build_model, get_feature_importance

# Set page configuration
st.set_page_config(
    page_title="Malmö Housing Price Predictor",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Cache data loading to improve performance
@st.cache_data
def load_data():
    """Load and preprocess the dataset."""
    df = load_and_preprocess_data('hemnet_properties.csv')
    return df

@st.cache_resource
def load_or_train_model(df):
    """Load a saved model or train a new one if not available."""
    model_path = 'housing_price_model.joblib'
    
    if os.path.exists(model_path):
        model = joblib.load(model_path)
        preprocessor = joblib.load('preprocessor.joblib')
        importance_df = pd.read_pickle('feature_importance.pkl')
    else:
        preprocessor, numerical_features, categorical_features = prepare_features(df)
        model, X_train, X_test, y_train, y_test = build_model(df, preprocessor)
        importance_df = get_feature_importance(model, X_train, numerical_features, categorical_features)
        
        # Save the model and preprocessor
        joblib.dump(model, model_path)
        joblib.dump(preprocessor, 'preprocessor.joblib')
        importance_df.to_pickle('feature_importance.pkl')
    
    return model, preprocessor, importance_df

def get_data_ranges(df):
    """Extract min/max values and unique values for all features."""
    data_ranges = {
        'number_of_rooms': {
            'min': df['number_of_rooms'].min(),
            'max': df['number_of_rooms'].max(),
            'type': 'numeric'
        },
        'living_area': {
            'min': df['living_area'].min(),
            'max': df['living_area'].max(),
            'type': 'numeric'
        },
        'year_of_construction': {
            'min': df[df['year_of_construction'] >= 1800]['year_of_construction'].min(),
            'max': df['year_of_construction'].max(),
            'type': 'numeric'
        },
        'fee': {
            'min': df['fee'].min(),
            'max': df['fee'].max(),
            'type': 'numeric'
        },
        'floor_number': {
            'min': df['floor_number'].min(),
            'max': df['floor_number'].max(),
            'type': 'numeric'
        },
        'top_floor_number': {
            'min': df['top_floor_number'].min(),
            'max': df['top_floor_number'].max(),
            'type': 'numeric'
        },
        'elevator_presence': {
            'options': [0, 1],
            'type': 'categorical'
        },
        'ownership_form': {
            'options': sorted(df['ownership_form'].unique()),
            'type': 'categorical'
        },
        'neighborhood': {
            'options': sorted(df['neighborhood'].unique()),
            'type': 'categorical'
        },
        'latitude': {
            'min': df['latitude'].min(),
            'max': df['latitude'].max(),
            'type': 'numeric'
        },
        'longitude': {
            'min': df['longitude'].min(),
            'max': df['longitude'].max(),
            'type': 'numeric'
        }
    }
    return data_ranges

def predict_price(model, input_data, df, preprocessor):
    """Generate a price prediction based on user inputs."""
    # Create a dataframe with the input data
    input_df = pd.DataFrame([input_data])
    
    # Add the neighborhood column from location
    input_df['neighborhood'] = input_data.get('neighborhood')
    
    # Make prediction
    try:
        prediction = model.predict(input_df)[0]
        return round(prediction, -3)  # Round to nearest thousand
    except Exception as e:
        st.error(f"Prediction error: {e}")
        return None

def create_folium_map(df, latitude=None, longitude=None):
    """Create a Folium map centered on Malmö with a marker at the specified coordinates."""
    # Determine center coordinates (default to center of Malmö)
    if latitude and longitude:
        center = [latitude, longitude]
    else:
        center = [55.605, 13.002]  # Center of Malmö
    
    # Create the map
    m = folium.Map(location=center, zoom_start=12)
    
    # Add a popup to show users how to select location
    folium.Popup(
        "Click on the map to select your property's location",
        max_width=200
    ).add_to(folium.Marker(
        location=center,
        icon=folium.Icon(color="blue", icon="info-sign")
    ).add_to(m))
    
    # Add a marker if coordinates are provided
    if latitude and longitude:
        folium.Marker(
            location=[latitude, longitude],
            popup="Selected Location",
            icon=folium.Icon(color="red", icon="home")
        ).add_to(m)
    
    # Add a heatmap or plot of previous sales (limited to improve performance)
    sample = df.sample(min(500, len(df)))
    for _, row in sample.iterrows():
        folium.CircleMarker(
            location=[row['latitude'], row['longitude']],
            radius=2,
            color='blue',
            fill=True,
            fill_color='blue',
            fill_opacity=0.1
        ).add_to(m)
    
    # Add click event handling JavaScript
    m.add_child(folium.Element("""
    <script>
    // Add click event listener to the map
    document.addEventListener('DOMContentLoaded', function() {
        setTimeout(function() {
            var map = document.querySelector('.folium-map');
            if (map) {
                map._leaflet_map.on('click', function(e) {
                    // Create or update hidden form with the clicked coordinates
                    var lat = e.latlng.lat.toFixed(6);
                    var lng = e.latlng.lng.toFixed(6);
                    
                    // Update the latitude and longitude input fields
                    var latInput = window.parent.document.querySelector('input[aria-label="Latitude"]');
                    var lngInput = window.parent.document.querySelector('input[aria-label="Longitude"]');
                    
                    if (latInput && lngInput) {
                        // Set values
                        latInput.value = lat;
                        lngInput.value = lng;
                        
                        // Trigger change events
                        var event = new Event('input', { bubbles: true });
                        latInput.dispatchEvent(event);
                        lngInput.dispatchEvent(event);
                        
                        // Submit to update the map
                        setTimeout(function() {
                            var buttons = window.parent.document.querySelectorAll('button[kind="primaryFormSubmit"]');
                            if (buttons.length > 0) {
                                buttons[0].click();
                            }
                        }, 100);
                    }
                });
            }
        }, 1000); // Wait for the map to be fully loaded
    });
    </script>
    """))
    
    return m

def plot_feature_importance(importance_df):
    """Plot feature importance."""
    fig, ax = plt.subplots(figsize=(10, 6))
    sns.barplot(x='Importance', y='Feature', data=importance_df.head(10), ax=ax)
    ax.set_title('Top 10 Features Influencing Housing Prices')
    ax.set_xlabel('Relative Importance')
    st.pyplot(fig)

def plot_neighborhood_price_comparison(df):
    """Plot comparison of median prices by neighborhood."""
    # Get neighborhood stats
    neighborhood_stats = df.groupby('neighborhood')['final_price'].agg(['count', 'median'])
    neighborhood_stats = neighborhood_stats[neighborhood_stats['count'] >= 100]  # Only neighborhoods with enough data
    
    # Get top and bottom 10 neighborhoods by price
    top_neighborhoods = neighborhood_stats.sort_values('median', ascending=False).head(10)
    bottom_neighborhoods = neighborhood_stats.sort_values('median').head(10)
    
    # Create plots
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(16, 8))
    
    # Plot top neighborhoods
    sns.barplot(x='median', y=top_neighborhoods.index, data=top_neighborhoods.reset_index(), ax=ax1)
    ax1.set_title('Top 10 Most Expensive Neighborhoods')
    ax1.set_xlabel('Median Price (SEK)')
    
    # Plot bottom neighborhoods
    sns.barplot(x='median', y=bottom_neighborhoods.index, data=bottom_neighborhoods.reset_index(), ax=ax2)
    ax2.set_title('Top 10 Least Expensive Neighborhoods')
    ax2.set_xlabel('Median Price (SEK)')
    
    fig.tight_layout()
    return fig

def plot_price_trends(df):
    """Plot price trends over time."""
    # Aggregate by year
    yearly_prices = df.groupby('sale_year')['final_price'].agg(['median', 'mean', 'count']).reset_index()
    
    fig, ax = plt.subplots(figsize=(10, 6))
    sns.lineplot(x='sale_year', y='median', data=yearly_prices, marker='o', label='Median Price', ax=ax)
    sns.lineplot(x='sale_year', y='mean', data=yearly_prices, marker='x', label='Mean Price', ax=ax)
    
    ax.set_title('Housing Price Trends in Malmö (2013-2024)')
    ax.set_xlabel('Year')
    ax.set_ylabel('Price (SEK)')
    ax.set_xticks(yearly_prices['sale_year'])
    ax.grid(True, linestyle='--', alpha=0.7)
    
    # Add annotations for the number of sales
    for i, row in yearly_prices.iterrows():
        ax.annotate(f"{row['count']} sales", 
                    xy=(row['sale_year'], row['median']), 
                    xytext=(0, 10),
                    textcoords='offset points',
                    ha='center',
                    fontsize=8)
    
    return fig

def main():
    """Main function for the Streamlit app."""
    st.title("Malmö Housing Price Predictor")
    
    # Load data and model
    with st.spinner("Loading data and model..."):
        df = load_data()
        model, preprocessor, importance_df = load_or_train_model(df)
        data_ranges = get_data_ranges(df)
    
    # Create tabs for different sections
    tab1, tab2, tab3 = st.tabs(["Price Prediction", "Market Insights", "About"])
    
    # Tab 1: Price Prediction
    with tab1:
        st.header("Estimate Your Property's Value")
        st.write("Enter your property details below to get an estimated market value.")
        
        # Create columns for layout
        col1, col2 = st.columns(2)
        
        # Initialize input data dictionary
        input_data = {
            'sale_year': 2024  # Set current year as default
        }
        
        # Property details inputs
        with col1:
            st.subheader("Property Details")
            
            # Ownership form
            input_data['ownership_form'] = st.selectbox(
                "Ownership Form",
                options=data_ranges['ownership_form']['options'],
                index=0
            )
            
            # Neighborhood selection
            input_data['neighborhood'] = st.selectbox(
                "Neighborhood",
                options=data_ranges['neighborhood']['options'],
                index=data_ranges['neighborhood']['options'].index('Västra Hamnen') if 'Västra Hamnen' in data_ranges['neighborhood']['options'] else 0
            )
            
            # Living area
            input_data['living_area'] = st.slider(
                "Living Area (sqm)",
                min_value=int(data_ranges['living_area']['min']),
                max_value=int(data_ranges['living_area']['max']),
                value=70
            )
            
            # Number of rooms
            input_data['number_of_rooms'] = st.slider(
                "Number of Rooms",
                min_value=float(data_ranges['number_of_rooms']['min']),
                max_value=float(data_ranges['number_of_rooms']['max']),
                value=2.0,
                step=0.5
            )
            
            # Year of construction
            input_data['year_of_construction'] = st.slider(
                "Year of Construction",
                min_value=int(data_ranges['year_of_construction']['min']),
                max_value=int(data_ranges['year_of_construction']['max']),
                value=1980
            )
            
            # Monthly fee
            input_data['fee'] = st.slider(
                "Monthly Fee (SEK)",
                min_value=int(data_ranges['fee']['min']),
                max_value=int(data_ranges['fee']['max']),
                value=3500
            )
            
            # Floor details
            col1a, col1b = st.columns(2)
            
            with col1a:
                input_data['floor_number'] = st.number_input(
                    "Floor Number",
                    min_value=int(data_ranges['floor_number']['min']),
                    max_value=int(data_ranges['floor_number']['max']),
                    value=2
                )
            
            with col1b:
                input_data['top_floor_number'] = st.number_input(
                    "Total Floors in Building",
                    min_value=int(data_ranges['top_floor_number']['min']),
                    max_value=int(data_ranges['top_floor_number']['max']),
                    value=5
                )
            
            # Elevator presence
            input_data['elevator_presence'] = st.radio(
                "Elevator",
                options=[0, 1],
                format_func={0: "No", 1: "Yes"}.get,
                horizontal=True,
                index=1
            )
        
        # Map for location selection
        with col2:
            st.subheader("Property Location")
            st.write("Click on the map to select your property's location, or enter coordinates directly.")
            
            # Coordinates input
            col2a, col2b = st.columns(2)
            
            with col2a:
                latitude = st.number_input(
                    "Latitude",
                    min_value=float(data_ranges['latitude']['min']),
                    max_value=float(data_ranges['latitude']['max']),
                    value=55.605,
                    format="%.6f"
                )
            
            with col2b:
                longitude = st.number_input(
                    "Longitude",
                    min_value=float(data_ranges['longitude']['min']),
                    max_value=float(data_ranges['longitude']['max']),
                    value=13.002,
                    format="%.6f"
                )
            
            # Create map
            map_container = st.container()
            with map_container:
                m = create_folium_map(df, latitude, longitude)
                folium_static(m, width=500, height=400)
                st.info("Click on the map to select a location. After clicking, the coordinates will update when you change other inputs.")
            
            input_data['latitude'] = latitude
            input_data['longitude'] = longitude
        
        # Predict button
        if st.button("Predict Price", type="primary"):
            with st.spinner("Calculating price..."):
                predicted_price = predict_price(model, input_data, df, preprocessor)
                
                if predicted_price:
                    # Display prediction
                    st.success(f"Estimated Property Value: **{predicted_price:,.0f} SEK**")
                    
                    # Show price per sqm
                    price_per_sqm = predicted_price / input_data['living_area']
                    st.info(f"Price per square meter: **{price_per_sqm:,.0f} SEK/sqm**")
                    
                    # Comparable properties
                    st.subheader("Comparable Properties")
                    
                    # Find similar properties
                    similar_properties = df[
                        (df['neighborhood'] == input_data['neighborhood']) &
                        (df['number_of_rooms'] == input_data['number_of_rooms']) &
                        (abs(df['living_area'] - input_data['living_area']) <= 10)
                    ].sort_values('sale_year', ascending=False).head(5)
                    
                    if len(similar_properties) > 0:
                        # Display similar properties
                        similar_table = similar_properties[['final_price', 'living_area', 'sale_year', 'fee']].copy()
                        similar_table['price_per_sqm'] = similar_table['final_price'] / similar_table['living_area']
                        similar_table.columns = ['Price (SEK)', 'Area (sqm)', 'Year Sold', 'Fee (SEK)', 'SEK/sqm']
                        st.dataframe(similar_table)
                    else:
                        st.write("No similar properties found in the dataset.")
    
    # Tab 2: Market Insights
    with tab2:
        st.header("Malmö Housing Market Insights")
        
        # Feature importance
        st.subheader("Price Determinants")
        st.write("These are the features that most influence property prices in Malmö:")
        plot_feature_importance(importance_df)
        
        # Neighborhood comparison
        st.subheader("Neighborhood Price Comparison")
        fig = plot_neighborhood_price_comparison(df)
        st.pyplot(fig)
        
        # Price trends
        st.subheader("Price Trends (2013-2024)")
        trend_fig = plot_price_trends(df)
        st.pyplot(trend_fig)
        
        # Price distribution by property type
        st.subheader("Price Distribution by Property Type")
        fig, ax = plt.subplots(figsize=(10, 6))
        sns.boxplot(x='ownership_form', y='final_price', data=df, ax=ax)
        ax.set_title('Price Distribution by Ownership Type')
        ax.set_xlabel('Ownership Type')
        ax.set_ylabel('Price (SEK)')
        plt.xticks(rotation=45)
        st.pyplot(fig)
        
        # Living area vs. price
        st.subheader("Relationship: Living Area vs. Price")
        fig, ax = plt.subplots(figsize=(10, 6))
        sns.scatterplot(x='living_area', y='final_price', hue='number_of_rooms', 
                        data=df.sample(min(5000, len(df))), alpha=0.6, ax=ax)
        ax.set_title('Living Area vs. Price (colored by number of rooms)')
        ax.set_xlabel('Living Area (sqm)')
        ax.set_ylabel('Price (SEK)')
        st.pyplot(fig)
    
    # Tab 3: About
    with tab3:
        st.header("About This App")
        st.write("""
        This app uses machine learning to predict housing prices in Malmö, Sweden. The prediction model is based on a dataset of over 44,000 property sales in Malmö from 2013 to 2024.
        
        ### How It Works
        
        The app uses a Random Forest model trained on historical sales data. The model takes into account various factors like:
        
        - Location (neighborhood and coordinates)
        - Property characteristics (size, number of rooms, year built)
        - Building features (floor number, elevator presence)
        - Economic factors (monthly fees)
        
        ### Data Source
        
        The data was collected from Hemnet, a Swedish property listing service. The dataset includes apartments and houses sold in Malmö between 2013 and 2024.
        
        ### Limitations
        
        - The model is based on historical data and may not capture recent market shifts
        - Unique property features (renovations, views, etc.) are not captured
        - Predictions are estimates and should not replace professional appraisals
        """)
        
        st.info("This app is for educational purposes only and should not be used as the sole basis for property valuation decisions.")

if __name__ == "__main__":
    main()