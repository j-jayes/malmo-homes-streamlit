"""Batch-predict prices for all properties in DuckDB.

Loads the trained model, reads every property from DuckDB, generates a
predicted price, and writes the results to a ``predictions`` table.  Run
this after ``aggregate_properties.py`` and ``train_model.py``.

Usage::

    python scripts/batch_predict.py
    python scripts/batch_predict.py --db data/database/properties.duckdb
"""

from __future__ import annotations

import argparse
import logging
from datetime import date
from pathlib import Path

import duckdb
import pandas as pd

from src.models.prediction_service import PredictionService

logger = logging.getLogger(__name__)


def batch_predict(
    db_path: Path,
    model_path: Path,
    target_date: date | None = None,
) -> int:
    """Generate predictions for every property in the database.

    Returns the number of rows written to the ``predictions`` table.
    """
    target_date = target_date or date.today()
    svc = PredictionService.from_artifact(model_path)

    conn = duckdb.connect(str(db_path))

    df = conn.execute("""
        SELECT
            property_id,
            property_type,
            rooms,
            living_area,
            association_fee,
            building_year,
            latitude,
            longitude,
            neighborhood,
            housing_type,
            ownership_type,
            asking_price,
            final_price,
            sold_date
        FROM properties
        WHERE living_area IS NOT NULL
          AND rooms IS NOT NULL
          AND latitude IS NOT NULL
          AND longitude IS NOT NULL
    """).df()

    logger.info("Loaded %d properties for prediction", len(df))

    predictions = []
    for _, row in df.iterrows():
        # Use actual sold_date for sold properties, target_date for others
        pred_date = target_date
        if pd.notna(row.get("sold_date")):
            try:
                pred_date = pd.to_datetime(row["sold_date"]).date()
            except Exception:
                pass

        def _safe_float(val, default: float = 0.0) -> float:
            return default if pd.isna(val) else float(val)

        def _safe_int(val, default: int = 1970) -> int:
            return default if pd.isna(val) else int(val)

        def _safe_str(val, default: str = "Unknown") -> str:
            return default if pd.isna(val) else str(val)

        try:
            pred = svc.predict(
                rooms=float(row["rooms"]),
                living_area=float(row["living_area"]),
                association_fee=_safe_float(row.get("association_fee"), 0),
                building_year=_safe_int(row.get("building_year"), 1970),
                latitude=float(row["latitude"]),
                longitude=float(row["longitude"]),
                neighborhood=_safe_str(row.get("neighborhood"), "Unknown"),
                housing_type=_safe_str(row.get("housing_type"), "Lägenhet"),
                ownership_type=_safe_str(row.get("ownership_type"), "Bostadsrätt"),
                target_date=pred_date,
            )
            fp = row.get("final_price")
            ap = row.get("asking_price")
            actual_price = (fp if not pd.isna(fp) else None) or (ap if not pd.isna(ap) else None)
            diff = None
            diff_pct = None
            if actual_price and pred.predicted_price:
                diff = int(actual_price) - pred.predicted_price
                diff_pct = round(diff / pred.predicted_price * 100, 1)

            predictions.append({
                "property_id": row["property_id"],
                "predicted_price": pred.predicted_price,
                "confidence_low": pred.confidence_low,
                "confidence_high": pred.confidence_high,
                "predicted_price_per_sqm": pred.predicted_price_per_sqm,
                "price_diff": diff,
                "price_diff_pct": diff_pct,
                "prediction_date": str(target_date),
            })
        except Exception as exc:
            logger.warning("Prediction failed for %s: %s", row["property_id"], exc)

    pred_df = pd.DataFrame(predictions)
    logger.info("Generated %d predictions", len(pred_df))

    conn.execute("DROP TABLE IF EXISTS predictions")
    conn.execute("CREATE TABLE predictions AS SELECT * FROM pred_df")

    count = conn.execute("SELECT COUNT(*) FROM predictions").fetchone()[0]
    logger.info("Wrote %d rows to predictions table", count)
    conn.close()
    return count


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Batch-predict property prices")
    parser.add_argument(
        "--db",
        type=Path,
        default=Path("data/database/properties.duckdb"),
    )
    parser.add_argument(
        "--model",
        type=Path,
        default=Path("models/price_model.joblib"),
    )
    parser.add_argument("--log-level", default="INFO")
    args = parser.parse_args(argv)

    logging.basicConfig(
        level=getattr(logging, args.log_level),
        format="%(asctime)s - %(levelname)s - %(message)s",
    )
    batch_predict(args.db, args.model)


if __name__ == "__main__":
    main()
