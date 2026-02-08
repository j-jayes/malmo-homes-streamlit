"""Prediction service for property price inference.

Loads a trained model artifact and provides a clean interface for
predicting the price of a property given its features and a target date.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Optional

import joblib
import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)


@dataclass
class PricePrediction:
    """Result of a single price prediction."""

    predicted_price: int
    confidence_low: int
    confidence_high: int
    predicted_price_per_sqm: Optional[int] = None


class PredictionService:
    """Loads a trained model and serves price predictions.

    Usage::

        svc = PredictionService.from_artifact("models/price_model.joblib")
        pred = svc.predict(
            rooms=3,
            living_area=68.0,
            association_fee=5200,
            building_year=2017,
            latitude=55.61,
            longitude=12.98,
            neighborhood="Västra Hamnen",
            housing_type="Lägenhet",
            ownership_type="Bostadsrätt",
            target_date=date(2026, 3, 1),
        )
    """

    _CONFIDENCE_SPREAD = 0.10  # ±10% for confidence interval

    def __init__(
        self,
        model,
        encoder,
        feature_names: list[str],
        numeric_features: list[str],
        categorical_features: list[str],
    ) -> None:
        self._model = model
        self._encoder = encoder
        self._feature_names = feature_names
        self._numeric_features = numeric_features
        self._categorical_features = categorical_features

    @classmethod
    def from_artifact(cls, path: str | Path) -> "PredictionService":
        """Load from a joblib artifact produced by ``PropertyPriceTrainer.save()``."""
        path = Path(path)
        if not path.exists():
            raise FileNotFoundError(f"Model artifact not found: {path}")

        artifact = joblib.load(path)
        logger.info("Loaded model artifact from %s", path)

        return cls(
            model=artifact["model"],
            encoder=artifact["encoder"],
            feature_names=artifact["feature_names"],
            numeric_features=artifact["numeric_features"],
            categorical_features=artifact["categorical_features"],
        )

    def predict(
        self,
        rooms: float,
        living_area: float,
        association_fee: float,
        building_year: int,
        latitude: float,
        longitude: float,
        neighborhood: str,
        housing_type: str = "Lägenhet",
        ownership_type: str = "Bostadsrätt",
        target_date: date | None = None,
    ) -> PricePrediction:
        """Predict the price for a property on a given date."""
        target_date = target_date or date.today()

        num_row = {
            k: v
            for k, v in zip(
                self._numeric_features,
                [
                    rooms, living_area, association_fee,
                    float(building_year), latitude, longitude,
                    float(target_date.year), float(target_date.month),
                ],
            )
        }

        cat_df = pd.DataFrame(
            [[neighborhood, housing_type, ownership_type]],
            columns=self._categorical_features,
        )
        cat_encoded = self._encoder.transform(cat_df)
        cat_row = {
            k: v for k, v in zip(self._categorical_features, cat_encoded[0])
        }

        X = pd.DataFrame([{**num_row, **cat_row}])
        raw_pred = self._model.predict(X)[0]
        predicted = int(round(raw_pred, -3))  # Round to nearest 1000

        spread = self._CONFIDENCE_SPREAD
        low = int(round(predicted * (1 - spread), -3))
        high = int(round(predicted * (1 + spread), -3))

        price_per_sqm = int(round(predicted / living_area)) if living_area > 0 else None

        return PricePrediction(
            predicted_price=predicted,
            confidence_low=low,
            confidence_high=high,
            predicted_price_per_sqm=price_per_sqm,
        )
