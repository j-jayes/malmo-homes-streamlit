import pandas as pd
import numpy as np
from sklearn.ensemble import RandomForestRegressor
from sklearn.model_selection import train_test_split, cross_val_score
from sklearn.preprocessing import StandardScaler, OneHotEncoder
from sklearn.compose import ColumnTransformer
from sklearn.pipeline import Pipeline
from sklearn.impute import SimpleImputer
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
import matplotlib.pyplot as plt
import seaborn as sns
from sklearn.inspection import permutation_importance

# Load the dataset
def load_and_preprocess_data(file_path):
    """Load and preprocess the Malmö housing dataset."""
    df = pd.read_csv(file_path, na_values='NA')
    
    # Handle outliers in final_price
    df = df[df['final_price'] > 100000]  # Remove suspiciously low prices
    df = df[df['final_price'] < 15000000]  # Cap at reasonable upper limit
    
    # Extract neighborhood from location
    df['neighborhood'] = df['location'].apply(lambda x: x.split(',')[0].strip() if isinstance(x, str) else None)
    
    # Clean up year_of_construction
    df['year_of_construction'] = df['year_of_construction'].apply(
        lambda x: x if (pd.notnull(x) and 1800 <= x <= 2024) else np.nan
    )
    
    return df

def prepare_features(df):
    """Prepare features for modeling."""
    # Identify categorical and numerical columns
    categorical_features = ['ownership_form', 'neighborhood']
    numerical_features = [
        'number_of_rooms', 'living_area', 'year_of_construction', 
        'fee', 'floor_number', 'top_floor_number', 'elevator_presence',
        'latitude', 'longitude', 'sale_year'
    ]
    
    # Create preprocessor
    numerical_transformer = Pipeline(steps=[
        ('imputer', SimpleImputer(strategy='median')),
        ('scaler', StandardScaler())
    ])
    
    categorical_transformer = Pipeline(steps=[
        ('imputer', SimpleImputer(strategy='constant', fill_value='missing')),
        ('onehot', OneHotEncoder(handle_unknown='ignore'))
    ])
    
    preprocessor = ColumnTransformer(
        transformers=[
            ('num', numerical_transformer, numerical_features),
            ('cat', categorical_transformer, categorical_features)
        ]
    )
    
    return preprocessor, numerical_features, categorical_features

def build_model(df, preprocessor):
    """Build and evaluate the Random Forest model."""
    X = df.drop(['final_price', 'location', 'operational_cost', 'leasehold_fee', 
                 'housing_association', 'sale_month', 'sale_day', 'balcony'], axis=1)
    y = df['final_price']
    
    # Split data
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)
    
    # Create and train pipeline
    model = Pipeline(steps=[
        ('preprocessor', preprocessor),
        ('regressor', RandomForestRegressor(n_estimators=100, random_state=42, n_jobs=-1))
    ])
    
    # Fit the model
    model.fit(X_train, y_train)
    
    # Evaluate the model
    y_pred = model.predict(X_test)
    mae = mean_absolute_error(y_test, y_pred)
    rmse = np.sqrt(mean_squared_error(y_test, y_pred))
    r2 = r2_score(y_test, y_pred)
    
    print(f"Mean Absolute Error: {mae:.2f} SEK")
    print(f"Root Mean Squared Error: {rmse:.2f} SEK")
    print(f"R² Score: {r2:.4f}")
    
    # Cross-validation score
    cv_scores = cross_val_score(model, X, y, cv=5, scoring='r2')
    print(f"Cross-validation R² scores: {cv_scores}")
    print(f"Mean CV R² score: {cv_scores.mean():.4f}")
    
    return model, X_train, X_test, y_train, y_test

def get_feature_importance(model, X_train, numerical_features, categorical_features):
    """Extract feature importance from the model."""
    # Get feature names after preprocessing
    feature_names = []
    
    # Add numerical feature names
    feature_names.extend(numerical_features)
    
    # Get categorical feature names from the pipeline
    preprocessor = model.named_steps['preprocessor']
    ohe = preprocessor.named_transformers_['cat'].named_steps['onehot']
    categorical_feature_names = ohe.get_feature_names_out(categorical_features).tolist()
    feature_names.extend(categorical_feature_names)
    
    # Extract feature importances
    importances = model.named_steps['regressor'].feature_importances_
    
    # Sort importance values
    indices = np.argsort(importances)[::-1]
    
    # Due to the mismatch in dimensions, we'll just get the top 20 importance values
    top_indices = indices[:min(20, len(importances))]
    top_features = [feature_names[i] if i < len(feature_names) else f"Feature_{i}" for i in top_indices]
    top_importances = [importances[i] for i in top_indices]
    
    importance_df = pd.DataFrame({
        'Feature': top_features,
        'Importance': top_importances
    })
    
    return importance_df

def plot_feature_importance(importance_df):
    """Plot feature importance."""
    plt.figure(figsize=(12, 8))
    sns.barplot(x='Importance', y='Feature', data=importance_df)
    plt.title('Feature Importance for Housing Price Prediction')
    plt.tight_layout()
    plt.savefig('feature_importance.png')
    plt.close()

def analyze_top_neighborhoods(df):
    """Analyze top and bottom neighborhoods by median price."""
    neighborhood_stats = df.groupby('neighborhood')['final_price'].agg(['count', 'median'])
    neighborhood_stats = neighborhood_stats[neighborhood_stats['count'] >= 100]  # Only consider neighborhoods with enough data
    
    top_neighborhoods = neighborhood_stats.sort_values('median', ascending=False).head(10)
    bottom_neighborhoods = neighborhood_stats.sort_values('median').head(10)
    
    return top_neighborhoods, bottom_neighborhoods

def price_prediction_function(model, input_data):
    """Function for predicting prices based on input features."""
    # Convert the input dictionary to a DataFrame
    input_df = pd.DataFrame([input_data])
    
    # Make the prediction
    predicted_price = model.predict(input_df)[0]
    
    return predicted_price

def main():
    """Main function to run the analysis."""
    # Load and prepare data
    df = load_and_preprocess_data('hemnet_properties.csv')
    preprocessor, numerical_features, categorical_features = prepare_features(df)
    
    # Build and evaluate model
    model, X_train, X_test, y_train, y_test = build_model(df, preprocessor)
    
    # Get feature importance
    importance_df = get_feature_importance(model, X_train, numerical_features, categorical_features)
    plot_feature_importance(importance_df)
    
    # Analyze neighborhood data
    top_neighborhoods, bottom_neighborhoods = analyze_top_neighborhoods(df)
    
    return model, df, preprocessor, importance_df, top_neighborhoods, bottom_neighborhoods

if __name__ == "__main__":
    main()