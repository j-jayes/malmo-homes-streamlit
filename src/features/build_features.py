"""Data loading and feature engineering logic.

Prepares raw scraped data into training-ready feature matrices.
"""

from __future__ import annotations

import logging
from pathlib import Path

import duckdb
import numpy as np
import pandas as pd
from sklearn.preprocessing import OrdinalEncoder

logger = logging.getLogger(__name__)

PARQUET_GLOB = "data/processed/property_details/gha_runs/*/batch_*.parquet"

NUMERIC_FEATURES = [
    "rooms",
    "living_area",
    "association_fee",
    "building_year",
    "latitude",
    "longitude",
    "sale_year",
    "sale_month",
]

CATEGORICAL_FEATURES = [
    "neighborhood",
    "housing_type",
    "ownership_type",
]

TARGET = "final_price"


def load_data(project_root: Path | str | None = None) -> pd.DataFrame:
    """Read all scraped parquet batches and return a clean dataframe of sold properties."""
    project_root = Path(project_root or Path.cwd())
    glob_path = str(project_root / PARQUET_GLOB)
    conn = duckdb.connect(":memory:")
    df = conn.execute(
        f"""
        SELECT *
        FROM read_parquet('{glob_path}', union_by_name=true)
        WHERE property_type = 'sold'
          AND final_price IS NOT NULL
          AND living_area IS NOT NULL
          AND rooms IS NOT NULL
          AND sold_date IS NOT NULL
        """
    ).df()
    conn.close()
    logger.info("Loaded %d sold properties from parquet batches", len(df))
    return df


def engineer_features(df: pd.DataFrame) -> pd.DataFrame:
    """Derive temporal and spatial features from raw columns."""
    df = df.copy()

    # Parse sold_date → year and month
    sold = pd.to_datetime(df["sold_date"], errors="coerce")
    df["sale_year"] = sold.dt.year
    df["sale_month"] = sold.dt.month

    # Fill missing numerics with median
    for col in NUMERIC_FEATURES:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")
            df[col] = df[col].fillna(df[col].median())

    # Fill missing categoricals with "Unknown"
    for col in CATEGORICAL_FEATURES:
        if col in df.columns:
            df[col] = df[col].fillna("Unknown").astype(str)

    return df


def prepare_xy(
    df: pd.DataFrame,
) -> tuple[pd.DataFrame, pd.Series, OrdinalEncoder, list[str]]:
    """Build feature matrix X, target vector y, and the fitted ordinal encoder.
    
    Returns:
        X (pd.DataFrame): Engineered features ready for model input.
        y (pd.Series): Target values.
        encoder (OrdinalEncoder): Fitted encoder for categorical features.
        feature_cols (list[str]): List of column names used in X.
    """
    df = engineer_features(df)

    feature_cols = NUMERIC_FEATURES + CATEGORICAL_FEATURES

    X_num = df[NUMERIC_FEATURES].values.astype(np.float64)

    # Ordinal-encode categoricals
    encoder = OrdinalEncoder(handle_unknown="use_encoded_value", unknown_value=-1)
    X_cat = encoder.fit_transform(df[CATEGORICAL_FEATURES])

    X = pd.DataFrame(
        np.hstack([X_num, X_cat]),
        columns=feature_cols,
    )
    y = df[TARGET].astype(np.float64)

    return X, y, encoder, feature_cols
