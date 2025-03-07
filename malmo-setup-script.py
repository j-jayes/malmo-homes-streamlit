"""
Setup script for Malmö Housing Price Predictor
This script prepares the environment and trains the initial model.
"""

import os
import joblib
import pandas as pd
import sys
import subprocess
import argparse

def check_dependencies():
    """Check if all required packages are installed."""
    required_packages = [
        'pandas', 'numpy', 'scikit-learn', 'streamlit', 'folium',
        'streamlit-folium', 'matplotlib', 'seaborn', 'joblib'
    ]
    
    missing_packages = []
    for package in required_packages:
        try:
            __import__(package)
        except ImportError:
            missing_packages.append(package)
    
    if missing_packages:
        print(f"Missing required packages: {', '.join(missing_packages)}")
        install = input("Would you like to install them now? (y/n): ")
        if install.lower() == 'y':
            subprocess.check_call([sys.executable, '-m', 'pip', 'install'] + missing_packages)
            print("Packages installed successfully.")
        else:
            print("Please install the missing packages before continuing.")
            sys.exit(1)

def check_data_file():
    """Check if the data file exists."""
    if not os.path.exists('hemnet_properties.csv'):
        print("ERROR: Data file 'hemnet_properties.csv' not found.")
        print("Please place the data file in the current directory and try again.")
        sys.exit(1)
    else:
        print("Data file found!")

def train_initial_model():
    """Train and save the initial model."""
    try:
        from malmo_housing_price_model import load_and_preprocess_data, prepare_features, build_model, get_feature_importance
        
        print("Loading and preprocessing data...")
        df = load_and_preprocess_data('hemnet_properties.csv')
        
        print("Preparing features...")
        preprocessor, numerical_features, categorical_features = prepare_features(df)
        
        print("Training model (this may take several minutes)...")
        model, X_train, X_test, y_train, y_test = build_model(df, preprocessor)
        
        print("Extracting feature importance...")
        importance_df = get_feature_importance(model, X_train, numerical_features, categorical_features)
        
        print("Saving model and preprocessor...")
        joblib.dump(model, 'housing_price_model.joblib')
        joblib.dump(preprocessor, 'preprocessor.joblib')
        importance_df.to_pickle('feature_importance.pkl')
        
        print("Model trained and saved successfully!")
        return True
    except Exception as e:
        print(f"Error training model: {e}")
        return False

def main():
    """Main function for setup."""
    parser = argparse.ArgumentParser(description='Setup Malmö Housing Price Predictor')
    parser.add_argument('--skip-train', action='store_true', help='Skip model training')
    args = parser.parse_args()
    
    print("Setting up Malmö Housing Price Predictor...")
    
    # Check dependencies
    print("\n1. Checking dependencies...")
    check_dependencies()
    
    # Check for data file
    print("\n2. Checking data file...")
    check_data_file()
    
    # Train initial model
    if not args.skip_train:
        print("\n3. Training initial model...")
        success = train_initial_model()
        if not success:
            print("WARNING: Model training failed. You can still run the app, but it will train the model on first run.")
    else:
        print("\n3. Skipping model training as requested.")
    
    # Final instructions
    print("\nSetup complete! To run the application, use the following command:")
    print("\n    streamlit run app.py\n")
    print("The application will open in your web browser.")

if __name__ == "__main__":
    main()