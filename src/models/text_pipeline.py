"""Text-to-price analysis pipeline.

Trains a model that predicts the "description premium" — the portion of
a property's price that is explained by its ad text rather than its
structural features.

Approach:
    1. Load descriptions + asking prices from the description archive.
    2. Predict asking price from structural features → compute residual.
    3. Fit TF-IDF on descriptions.
    4. Train Ridge regression: TF-IDF → residual.
    5. Rank words by coefficient → "power words" and "discount words".

Usage::

    python -m src.models.text_pipeline --db data/database/properties.duckdb
"""

from __future__ import annotations

import argparse
import logging
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path

import duckdb
import joblib
import numpy as np
import pandas as pd
from sklearn.linear_model import Ridge
from sklearn.model_selection import cross_val_score

from src.features.text_features import TextFeatureExtractor

logger = logging.getLogger(__name__)

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
DEFAULT_DB = PROJECT_ROOT / "data" / "database" / "properties.duckdb"
DEFAULT_PRICE_MODEL = PROJECT_ROOT / "models" / "price_model.joblib"
DEFAULT_OUTPUT = PROJECT_ROOT / "models" / "text_pipeline.joblib"


@dataclass
class PowerWord:
    word: str
    coefficient: float
    frequency: int  # number of documents containing this word

    @property
    def is_premium(self) -> bool:
        return self.coefficient > 0


@dataclass
class TextPipelineResult:
    n_documents: int
    vocabulary_size: int
    r2_cv: float
    mae_cv: float
    power_words: list[PowerWord] = field(default_factory=list)
    discount_words: list[PowerWord] = field(default_factory=list)


class TextPricePipeline:
    """End-to-end pipeline: descriptions → power-word rankings."""

    def __init__(
        self,
        extractor: TextFeatureExtractor | None = None,
        ridge_alpha: float = 10.0,
    ) -> None:
        self._extractor = extractor or TextFeatureExtractor()
        self._ridge = Ridge(alpha=ridge_alpha)
        self._is_fitted = False

    def load_data(self, db_path: Path) -> pd.DataFrame:
        """Load descriptions with structured features from description_archive."""
        conn = duckdb.connect(str(db_path), read_only=True)
        try:
            df = conn.execute("""
                SELECT
                    a.property_id,
                    a.description,
                    a.asking_price,
                    a.living_area,
                    a.rooms,
                    a.neighborhood,
                    a.city,
                    a.latitude,
                    a.longitude,
                    a.building_year,
                    a.association_fee,
                    a.housing_type,
                    a.ownership_type,
                    a.address
                FROM description_archive a
                WHERE a.description IS NOT NULL
                  AND LENGTH(TRIM(a.description)) > 50
                  AND a.asking_price IS NOT NULL
                  AND a.asking_price > 0
                  AND a.living_area IS NOT NULL
                  AND a.living_area > 0
            """).df()
            logger.info("Loaded %d descriptions with asking prices", len(df))
            return df
        finally:
            conn.close()

    def compute_residuals(
        self, df: pd.DataFrame, price_model_path: Path
    ) -> np.ndarray:
        """Predict asking price from structural features and return residuals.

        Residual = actual_asking_price − predicted_asking_price.
        Positive residual → agent priced above model expectation.
        """
        from src.models.prediction_service import PredictionService

        svc = PredictionService.from_artifact(price_model_path)
        predictions = []
        today = date.today()

        for _, row in df.iterrows():
            try:
                pred = svc.predict(
                    rooms=float(row["rooms"]) if pd.notna(row["rooms"]) else 2.0,
                    living_area=float(row["living_area"]),
                    association_fee=int(row["association_fee"]) if pd.notna(row.get("association_fee")) else 0,
                    building_year=int(row["building_year"]) if pd.notna(row.get("building_year")) else 1970,
                    latitude=float(row["latitude"]) if pd.notna(row.get("latitude")) else 0.0,
                    longitude=float(row["longitude"]) if pd.notna(row.get("longitude")) else 0.0,
                    neighborhood=str(row.get("neighborhood", "Unknown")),
                    housing_type=str(row.get("housing_type", "Lägenhet")),
                    ownership_type=str(row.get("ownership_type", "Bostadsrätt")),
                    target_date=today,
                )
                predictions.append(pred.predicted_price)
            except Exception:
                predictions.append(np.nan)

        predicted = np.array(predictions, dtype=float)
        actual = df["asking_price"].values.astype(float)
        residuals = actual - predicted
        n_valid = int(np.sum(~np.isnan(residuals)))
        logger.info(
            "Residual stats (n=%d): mean=%.0f, std=%.0f, median=%.0f",
            n_valid,
            np.nanmean(residuals),
            np.nanstd(residuals),
            np.nanmedian(residuals),
        )
        return residuals

    def fit(
        self,
        descriptions: list[str],
        residuals: np.ndarray,
    ) -> TextPipelineResult:
        """Fit TF-IDF + Ridge on descriptions → residuals."""
        tfidf = self._extractor.fit_transform(descriptions)

        mask = ~np.isnan(residuals)
        tfidf_clean = tfidf[mask]
        y_clean = residuals[mask]

        scores_r2 = cross_val_score(
            self._ridge, tfidf_clean, y_clean, cv=5, scoring="r2"
        )
        scores_mae = cross_val_score(
            self._ridge, tfidf_clean, y_clean, cv=5, scoring="neg_mean_absolute_error"
        )

        self._ridge.fit(tfidf_clean, y_clean)
        self._is_fitted = True

        r2_cv = float(np.mean(scores_r2))
        mae_cv = float(-np.mean(scores_mae))
        logger.info("Ridge CV: R²=%.4f, MAE=%.0f SEK", r2_cv, mae_cv)

        power_words, discount_words = self._rank_words(tfidf_clean)

        return TextPipelineResult(
            n_documents=int(mask.sum()),
            vocabulary_size=self._extractor.vocabulary_size,
            r2_cv=r2_cv,
            mae_cv=mae_cv,
            power_words=power_words,
            discount_words=discount_words,
        )

    def _rank_words(
        self, tfidf_matrix, top_n: int = 30
    ) -> tuple[list[PowerWord], list[PowerWord]]:
        """Rank features by Ridge coefficient magnitude."""
        coefs = self._ridge.coef_
        names = self._extractor.feature_names
        doc_freq = np.asarray((tfidf_matrix > 0).sum(axis=0)).flatten()

        idx_sorted = np.argsort(coefs)
        premium_idx = idx_sorted[-top_n:][::-1]
        discount_idx = idx_sorted[:top_n]

        power = [
            PowerWord(names[i], float(coefs[i]), int(doc_freq[i]))
            for i in premium_idx
            if coefs[i] > 0
        ]
        discount = [
            PowerWord(names[i], float(coefs[i]), int(doc_freq[i]))
            for i in discount_idx
            if coefs[i] < 0
        ]
        return power, discount

    def predict_premium(self, description: str) -> float:
        """Predict the text-based price premium for a single description."""
        if not self._is_fitted:
            raise RuntimeError("Pipeline not fitted")
        vec = self._extractor.transform([description])
        return float(self._ridge.predict(vec)[0])

    def analyze_description(
        self, description: str, top_n: int = 15
    ) -> dict:
        """Full analysis of a single description text."""
        premium = self.predict_premium(description)
        top_features = self._extractor.top_features_for_document(description, n=top_n)

        coef_map = dict(
            zip(self._extractor.feature_names, self._ridge.coef_)
        )
        word_impacts = []
        for word, tfidf_score in top_features:
            coef = coef_map.get(word, 0.0)
            word_impacts.append({
                "word": word,
                "tfidf_score": round(tfidf_score, 4),
                "coefficient": round(coef, 0),
                "impact": round(tfidf_score * coef, 0),
            })
        word_impacts.sort(key=lambda x: abs(x["impact"]), reverse=True)

        return {
            "predicted_premium": round(premium, 0),
            "word_impacts": word_impacts,
        }

    def save(self, path: Path | str) -> None:
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        joblib.dump(
            {
                "extractor": self._extractor,
                "ridge": self._ridge,
            },
            path,
        )
        logger.info("Saved TextPricePipeline to %s", path)

    @classmethod
    def load(cls, path: Path | str) -> "TextPricePipeline":
        data = joblib.load(path)
        obj = cls.__new__(cls)
        obj._extractor = data["extractor"]
        obj._ridge = data["ridge"]
        obj._is_fitted = True
        logger.info("Loaded TextPricePipeline from %s", path)
        return obj


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Train text-to-price pipeline")
    parser.add_argument("--db", type=Path, default=DEFAULT_DB)
    parser.add_argument("--price-model", type=Path, default=DEFAULT_PRICE_MODEL)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--alpha", type=float, default=10.0, help="Ridge alpha")
    parser.add_argument("--log-level", default="INFO")
    args = parser.parse_args(argv)

    logging.basicConfig(
        level=getattr(logging, args.log_level),
        format="%(asctime)s - %(levelname)s - %(message)s",
    )

    pipeline = TextPricePipeline(ridge_alpha=args.alpha)
    df = pipeline.load_data(args.db)

    if len(df) < 20:
        logger.warning(
            "Only %d descriptions — need at least 20 for meaningful analysis. "
            "Run more active listing scrapes first.",
            len(df),
        )
        return

    if args.price_model.exists():
        residuals = pipeline.compute_residuals(df, args.price_model)
    else:
        logger.warning("No price model found — using raw asking_price as target")
        residuals = df["asking_price"].values.astype(float)

    result = pipeline.fit(df["description"].tolist(), residuals)

    logger.info("=" * 60)
    logger.info("Text Pipeline Results")
    logger.info("=" * 60)
    logger.info("Documents: %d", result.n_documents)
    logger.info("Vocabulary: %d features", result.vocabulary_size)
    logger.info("CV R²: %.4f", result.r2_cv)
    logger.info("CV MAE: %.0f SEK", result.mae_cv)
    logger.info("")
    logger.info("Top premium words:")
    for pw in result.power_words[:15]:
        logger.info("  +%.0f SEK  %-25s (in %d docs)", pw.coefficient, pw.word, pw.frequency)
    logger.info("")
    logger.info("Top discount words:")
    for dw in result.discount_words[:15]:
        logger.info("  %.0f SEK  %-25s (in %d docs)", dw.coefficient, dw.word, dw.frequency)

    pipeline.save(args.output)


if __name__ == "__main__":
    main()
