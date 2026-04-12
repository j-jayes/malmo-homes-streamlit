"""Training pipeline for the property price prediction model.

Loads sold-property data from parquet batches, engineers features,
trains a LightGBM regressor with cross-validation, and serialises the
model artifact (model + feature metadata) to disk.
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any

import duckdb
import joblib
import lightgbm as lgb
import numpy as np
import pandas as pd
from sklearn.model_selection import KFold, cross_validate
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OrdinalEncoder

logger = logging.getLogger(__name__)

# Covers both legacy path (property_details/gha_runs) and new path (sold_details)
PARQUET_GLOB = "data/processed/**/batch_*.parquet"

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


@dataclass
class TrainingResult:
    """Holds evaluation metrics and metadata from a training run."""

    mae: float
    mape: float
    r2: float
    n_samples: int
    n_features: int
    feature_names: list[str]
    feature_importances: dict[str, float]
    trained_at: str = field(default_factory=lambda: datetime.now().isoformat())

    def summary(self) -> str:
        return (
            f"R²={self.r2:.3f}  MAE={self.mae:,.0f} SEK  "
            f"MAPE={self.mape:.1f}%  n={self.n_samples}"
        )


class PropertyPriceTrainer:
    """Trains a LightGBM model to predict ``final_price`` of sold properties."""

    def __init__(
        self,
        project_root: Path | None = None,
        n_folds: int = 5,
        random_state: int = 42,
    ) -> None:
        self.project_root = Path(project_root or Path.cwd())
        self.n_folds = n_folds
        self.random_state = random_state
        self._model: lgb.LGBMRegressor | None = None
        self._encoder: OrdinalEncoder | None = None
        self._feature_names: list[str] = []

    def load_data(self) -> pd.DataFrame:
        """Read all scraped parquet batches and return a clean dataframe of sold properties."""
        glob_path = str(self.project_root / PARQUET_GLOB)
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

    def engineer_features(self, df: pd.DataFrame) -> pd.DataFrame:
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

    def _prepare_xy(
        self, df: pd.DataFrame
    ) -> tuple[np.ndarray, np.ndarray, list[str]]:
        """Build feature matrix X and target vector y."""
        df = self.engineer_features(df)

        feature_cols = NUMERIC_FEATURES + CATEGORICAL_FEATURES
        self._feature_names = feature_cols

        X_num = df[NUMERIC_FEATURES].values.astype(np.float64)

        # Ordinal-encode categoricals (LightGBM handles ordered ints natively)
        self._encoder = OrdinalEncoder(
            handle_unknown="use_encoded_value", unknown_value=-1
        )
        X_cat = self._encoder.fit_transform(df[CATEGORICAL_FEATURES])

        X = pd.DataFrame(
            np.hstack([X_num, X_cat]),
            columns=feature_cols,
        )
        y = df[TARGET].values.astype(np.float64)

        return X, y, feature_cols

    def train(self, df: pd.DataFrame | None = None) -> TrainingResult:
        """Run the full training pipeline: load → feature-engineer → CV → fit final model."""
        if df is None:
            df = self.load_data()

        X, y, feature_names = self._prepare_xy(df)
        logger.info(
            "Training on %d samples, %d features", X.shape[0], X.shape[1]
        )

        self._model = lgb.LGBMRegressor(
            n_estimators=1000,
            learning_rate=0.05,
            max_depth=8,
            num_leaves=63,
            min_child_samples=20,
            subsample=0.8,
            colsample_bytree=0.8,
            reg_alpha=0.1,
            reg_lambda=1.0,
            random_state=self.random_state,
            verbose=-1,
        )

        # Cross-validation for evaluation
        cv = KFold(
            n_splits=self.n_folds, shuffle=True, random_state=self.random_state
        )
        scoring = {
            "mae": "neg_mean_absolute_error",
            "mape": "neg_mean_absolute_percentage_error",
            "r2": "r2",
        }
        cv_results = cross_validate(
            self._model, X, y, cv=cv, scoring=scoring, return_train_score=False
        )

        mae = -cv_results["test_mae"].mean()
        mape = -cv_results["test_mape"].mean() * 100
        r2 = cv_results["test_r2"].mean()

        logger.info("CV results — R²=%.3f  MAE=%.0f SEK  MAPE=%.1f%%", r2, mae, mape)

        # Fit final model on all data
        self._model.fit(X, y)

        importances = dict(
            zip(feature_names, self._model.feature_importances_.tolist())
        )

        return TrainingResult(
            mae=mae,
            mape=mape,
            r2=r2,
            n_samples=X.shape[0],
            n_features=X.shape[1],
            feature_names=feature_names,
            feature_importances=importances,
        )

    def save(self, output_dir: Path | None = None) -> Path:
        """Serialise model, encoder, and metadata to disk."""
        if self._model is None:
            raise RuntimeError("No trained model to save — call train() first")

        output_dir = output_dir or self.project_root / "models"
        output_dir.mkdir(parents=True, exist_ok=True)

        artifact: dict[str, Any] = {
            "model": self._model,
            "encoder": self._encoder,
            "feature_names": self._feature_names,
            "numeric_features": NUMERIC_FEATURES,
            "categorical_features": CATEGORICAL_FEATURES,
            "target": TARGET,
        }

        path = output_dir / "price_model.joblib"
        joblib.dump(artifact, path)
        logger.info("Saved model artifact to %s", path)

        # Also write a human-readable metadata sidecar
        meta_path = output_dir / "price_model_meta.json"
        meta_path.write_text(
            json.dumps(
                {
                    "feature_names": self._feature_names,
                    "numeric_features": NUMERIC_FEATURES,
                    "categorical_features": CATEGORICAL_FEATURES,
                    "target": TARGET,
                    "saved_at": datetime.now().isoformat(),
                },
                indent=2,
            )
        )

        return path
