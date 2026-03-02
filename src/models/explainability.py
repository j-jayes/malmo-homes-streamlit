"""SHAP-based explainability engine and natural-language narrative generator.

Provides per-property explanations of predicted prices by attributing the
prediction to individual features using SHAP TreeExplainer, and optionally
enriching the explanation with text-based signals from the TextPricePipeline.

Usage::

    explainer = SHAPExplainer("models/price_model.joblib")
    shap_features = explainer.explain(X_row)

    gen = NarrativeGenerator()
    narrative = gen.generate(
        shap_features=shap_features,
        asking_price=2_950_000,
        predicted_price=3_350_000,
        neighborhood="Husie",
        text_analysis={"predicted_premium": 45_000, "word_impacts": [...]},
    )
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Optional

import joblib
import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)

# Human-readable labels for model feature names
_FEATURE_LABELS: dict[str, str] = {
    "rooms": "number of rooms",
    "living_area": "floor area",
    "association_fee": "monthly fee",
    "building_year": "year built",
    "latitude": "north-south location",
    "longitude": "east-west location",
    "sale_year": "sale year",
    "sale_month": "sale month",
    "neighborhood": "neighborhood",
    "housing_type": "housing type",
    "ownership_type": "ownership type",
}


class SHAPExplainer:
    """Wraps a trained LightGBM model with a SHAP TreeExplainer.

    Loads the same artifact format produced by ``PropertyPriceTrainer.save()``.
    The feature construction mirrors ``PredictionService._prepare_row()`` so that
    SHAP values are attributed to the same feature space the model was trained on.
    """

    def __init__(self, model_path: str | Path) -> None:
        import shap

        path = Path(model_path)
        if not path.exists():
            raise FileNotFoundError(f"Model artifact not found: {path}")

        artifact = joblib.load(path)
        self._model = artifact["model"]
        self._encoder = artifact["encoder"]
        self._numeric_features: list[str] = artifact["numeric_features"]
        self._categorical_features: list[str] = artifact["categorical_features"]
        self._feature_names: list[str] = artifact["feature_names"]

        self._explainer = shap.TreeExplainer(self._model)
        logger.info("SHAPExplainer loaded from %s", path)

    def _build_row(
        self,
        rooms: float,
        living_area: float,
        association_fee: float,
        building_year: int,
        latitude: float,
        longitude: float,
        neighborhood: str,
        housing_type: str,
        ownership_type: str,
        sale_year: int,
        sale_month: int,
    ) -> pd.DataFrame:
        """Build the feature DataFrame in exactly the same way as PredictionService."""
        from datetime import date

        num_row = dict(
            zip(
                self._numeric_features,
                [
                    float(rooms),
                    float(living_area),
                    float(association_fee),
                    float(building_year),
                    float(latitude),
                    float(longitude),
                    float(sale_year),
                    float(sale_month),
                ],
            )
        )

        cat_df = pd.DataFrame(
            [[neighborhood, housing_type, ownership_type]],
            columns=self._categorical_features,
        )
        cat_encoded = self._encoder.transform(cat_df)
        cat_row = dict(zip(self._categorical_features, cat_encoded[0]))

        return pd.DataFrame([{**num_row, **cat_row}])

    def explain(
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
        sale_year: int | None = None,
        sale_month: int | None = None,
    ) -> list[dict]:
        """Return per-feature SHAP attributions sorted by absolute impact.

        Each item in the returned list is a dict with keys:
          feature, display_name, value, shap_value
        """
        from datetime import date

        today = date.today()
        sale_year = sale_year or today.year
        sale_month = sale_month or today.month

        X = self._build_row(
            rooms=rooms,
            living_area=living_area,
            association_fee=association_fee,
            building_year=building_year,
            latitude=latitude,
            longitude=longitude,
            neighborhood=neighborhood,
            housing_type=housing_type,
            ownership_type=ownership_type,
            sale_year=sale_year,
            sale_month=sale_month,
        )

        shap_values = self._explainer.shap_values(X)
        # shap_values may be 2-D (n_rows=1, n_features)
        row_shap = np.asarray(shap_values).flatten()

        results = []
        for i, name in enumerate(self._feature_names):
            if i < len(row_shap):
                results.append(
                    {
                        "feature": name,
                        "display_name": _FEATURE_LABELS.get(name, name),
                        "value": float(X.iloc[0][name]),
                        "shap_value": float(row_shap[i]),
                    }
                )

        return sorted(results, key=lambda x: abs(x["shap_value"]), reverse=True)


class NarrativeGenerator:
    """Converts SHAP feature attributions into a human-readable price narrative.

    Designed for the Swedish housing market where the asking price (utgångspris)
    is a strategic anchor and the final sale price is what matters.

    Gap classification thresholds (asking vs predicted):
      - asking < predicted - 5%  → property may sell above asking (typical gap)
      - asking within ±5%        → priced close to model estimate
      - asking > predicted + 5%  → listed above model estimate
    """

    def generate(
        self,
        shap_features: list[dict],
        asking_price: float,
        predicted_price: int,
        neighborhood: str = "",
        text_analysis: Optional[dict] = None,
    ) -> str:
        """Generate a narrative explanation string.

        Args:
            shap_features: Output of SHAPExplainer.explain()
            asking_price:  The current listing price (utgångspris)
            predicted_price: Model's estimate of the final sold price
            neighborhood:  Neighborhood name for localised phrasing
            text_analysis: Optional output of TextPricePipeline.analyze_description()
        """
        gap = asking_price - predicted_price
        gap_pct = gap / predicted_price * 100

        # --- Sentence 1: Price gap assessment ---
        asking_fmt = _fmt_kr(asking_price)
        pred_fmt = _fmt_kr(predicted_price)

        if gap_pct < -15:
            gap_sentence = (
                f"Listed at {asking_fmt} — our model estimates a final sale price of "
                f"{pred_fmt} ({abs(gap_pct):.0f}% above asking). "
                f"This property appears to be listed below its market value"
                + (f" for {neighborhood}" if neighborhood else "")
                + "."
            )
        elif gap_pct < -5:
            gap_sentence = (
                f"Listed at {asking_fmt} — our model estimates a final sale price of "
                f"{pred_fmt} ({abs(gap_pct):.0f}% above asking). "
                f"Expect competitive bidding"
                + (f" in {neighborhood}" if neighborhood else "")
                + "."
            )
        elif gap_pct <= 5:
            gap_sentence = (
                f"Listed at {asking_fmt}, close to our model estimate of {pred_fmt} "
                f"({abs(gap_pct):.0f}% {'above' if gap_pct > 0 else 'below'} asking). "
                "The final sale price is likely to land near the asking price."
            )
        else:
            gap_sentence = (
                f"Listed at {asking_fmt} — our model estimates {pred_fmt}, "
                f"which is {abs(gap_pct):.0f}% below the asking price. "
                "This property may be priced above current market expectations."
            )

        # --- Sentence 2: Top structural drivers ---
        positives = [f for f in shap_features if f["shap_value"] > 0][:3]
        negatives = [f for f in shap_features if f["shap_value"] < 0][:3]

        driver_parts = []
        if positives:
            pos_str = ", ".join(
                f"{f['display_name']} (+{_fmt_kr(f['shap_value'])})"
                for f in positives
            )
            driver_parts.append(f"Key value drivers: {pos_str}.")
        if negatives:
            neg_str = ", ".join(
                f"{f['display_name']} ({_fmt_kr(f['shap_value'])})"
                for f in negatives
            )
            driver_parts.append(f"Tempering factors: {neg_str}.")

        structural_sentence = " ".join(driver_parts)

        # --- Sentence 3: Text-based signals (optional) ---
        text_sentence = ""
        if text_analysis:
            premium = text_analysis.get("predicted_premium", 0)
            word_impacts = text_analysis.get("word_impacts", [])
            if abs(premium) > 10_000 and word_impacts:
                top_words = [
                    w["word"]
                    for w in sorted(word_impacts, key=lambda x: abs(x["impact"]), reverse=True)
                    if abs(w["impact"]) > 5_000
                ][:4]
                if top_words:
                    direction = "adds" if premium > 0 else "reduces"
                    words_str = ", ".join(f"'{w}'" for w in top_words)
                    text_sentence = (
                        f"The ad description {direction} approximately "
                        f"{_fmt_kr(abs(premium))} to the estimated value, "
                        f"driven by: {words_str}."
                    )

        parts = [gap_sentence]
        if structural_sentence:
            parts.append(structural_sentence)
        if text_sentence:
            parts.append(text_sentence)

        return "\n\n".join(parts)


def _fmt_kr(value: float) -> str:
    """Format a SEK value as a human-readable string."""
    abs_val = abs(value)
    sign = "-" if value < 0 else ""
    if abs_val >= 1_000_000:
        return f"{sign}{abs_val / 1_000_000:.2f}M kr".replace(".00", "").replace(
            ".50", ".5"
        )
    if abs_val >= 1_000:
        rounded = round(abs_val / 1_000) * 1_000
        return f"{sign}{rounded:,.0f} kr".replace(",", "\u202f")
    return f"{sign}{abs_val:.0f} kr"
