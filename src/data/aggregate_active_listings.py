"""Aggregate active (for-sale) property Parquet files into DuckDB.

Unlike sold properties which accumulate over time, active listings are
ephemeral — they disappear once sold.  Each scrape run produces a fresh
snapshot that *replaces* the previous ``active_listings`` table.

After aggregation the script optionally runs batch predictions so that the
frontend can display predicted-vs-asking price comparisons.

Usage::

    python -m src.data.aggregate_active_listings
    python -m src.data.aggregate_active_listings --input data/processed/active_listings --predict
"""

from __future__ import annotations

import argparse
import logging
from datetime import date
from pathlib import Path

import duckdb
import pandas as pd

from src.data.description_archive import DescriptionArchive

logger = logging.getLogger(__name__)

TABLE_NAME = "active_listings"


def aggregate_active_listings(
    input_dir: Path,
    db_path: Path,
) -> int:
    """Replace the ``active_listings`` table with data from *input_dir*.

    Before replacing, descriptions are archived to the persistent
    ``description_archive`` table so they survive across daily runs.

    Returns the number of rows written.
    """
    parquet_files = sorted(input_dir.glob("**/*.parquet"))
    parquet_files = [p for p in parquet_files if "subset" not in p.name]

    if not parquet_files:
        logger.warning("No parquet files found in %s", input_dir)
        return 0

    logger.info("Found %d parquet files in %s", len(parquet_files), input_dir)
    files_str = [str(p) for p in parquet_files]

    archive = DescriptionArchive(db_path)
    archive.upsert_from_parquet(parquet_files)

    conn = duckdb.connect(str(db_path))
    try:
        conn.execute(f"DROP TABLE IF EXISTS {TABLE_NAME}")
        conn.execute(f"""
            CREATE TABLE {TABLE_NAME} AS
            SELECT *
            FROM read_parquet($1)
            QUALIFY ROW_NUMBER() OVER (
                PARTITION BY property_id ORDER BY scraped_at DESC
            ) = 1
        """, [files_str])

        count = conn.execute(f"SELECT COUNT(*) FROM {TABLE_NAME}").fetchone()[0]
        logger.info("Wrote %d rows to %s", count, TABLE_NAME)
        return count
    finally:
        conn.close()


def predict_active_listings(
    db_path: Path,
    model_path: Path,
) -> int:
    """Generate ML predictions for active listings and store in ``active_predictions``."""
    from src.models.prediction_service import PredictionService

    svc = PredictionService.from_artifact(model_path)
    conn = duckdb.connect(str(db_path))

    df = conn.execute(f"""
        SELECT
            property_id, rooms, living_area, association_fee,
            building_year, latitude, longitude, neighborhood,
            housing_type, ownership_type, asking_price
        FROM {TABLE_NAME}
        WHERE living_area IS NOT NULL
          AND rooms IS NOT NULL
          AND latitude IS NOT NULL
          AND longitude IS NOT NULL
    """).df()

    logger.info("Loaded %d active listings for prediction", len(df))
    today = date.today()
    predictions = []

    for _, row in df.iterrows():

        def _safe(val, default=0.0):
            return default if pd.isna(val) else val

        try:
            pred = svc.predict(
                rooms=float(row["rooms"]),
                living_area=float(row["living_area"]),
                association_fee=float(_safe(row.get("association_fee"), 0)),
                building_year=int(_safe(row.get("building_year"), 1970)),
                latitude=float(row["latitude"]),
                longitude=float(row["longitude"]),
                neighborhood=str(_safe(row.get("neighborhood"), "Unknown")),
                housing_type=str(_safe(row.get("housing_type"), "Lägenhet")),
                ownership_type=str(_safe(row.get("ownership_type"), "Bostadsrätt")),
                target_date=today,
            )
            asking = row.get("asking_price")
            diff = None
            diff_pct = None
            if not pd.isna(asking) and pred.predicted_price:
                diff = int(asking) - pred.predicted_price
                diff_pct = round(diff / pred.predicted_price * 100, 1)

            predictions.append({
                "property_id": row["property_id"],
                "predicted_price": pred.predicted_price,
                "confidence_low": pred.confidence_low,
                "confidence_high": pred.confidence_high,
                "predicted_price_per_sqm": pred.predicted_price_per_sqm,
                "price_diff": diff,
                "price_diff_pct": diff_pct,
                "prediction_date": str(today),
            })
        except Exception as exc:
            logger.warning("Prediction failed for %s: %s", row["property_id"], exc)

    pred_df = pd.DataFrame(predictions)
    conn.execute("DROP TABLE IF EXISTS active_predictions")
    conn.execute("CREATE TABLE active_predictions AS SELECT * FROM pred_df")

    count = conn.execute("SELECT COUNT(*) FROM active_predictions").fetchone()[0]
    logger.info("Wrote %d active predictions", count)
    conn.close()
    return count


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Aggregate active listings to DuckDB")
    parser.add_argument(
        "--input", "-i",
        type=Path,
        default=Path("data/processed/active_listings"),
    )
    parser.add_argument(
        "--db", "-d",
        type=Path,
        default=Path("data/database/properties.duckdb"),
    )
    parser.add_argument(
        "--model",
        type=Path,
        default=Path("models/price_model.joblib"),
    )
    parser.add_argument("--predict", action="store_true", help="Run predictions after aggregation")
    parser.add_argument("--log-level", default="INFO")
    args = parser.parse_args(argv)

    logging.basicConfig(
        level=getattr(logging, args.log_level),
        format="%(asctime)s - %(levelname)s - %(message)s",
    )

    if not args.input.exists():
        logger.error("Input directory %s does not exist", args.input)
        return

    args.db.parent.mkdir(parents=True, exist_ok=True)
    count = aggregate_active_listings(args.input, args.db)

    if args.predict and count > 0 and args.model.exists():
        predict_active_listings(args.db, args.model)
    elif args.predict and not args.model.exists():
        logger.warning("Model not found at %s — skipping predictions", args.model)


if __name__ == "__main__":
    main()
