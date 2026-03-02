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
            FROM read_parquet($1, union_by_name = true)
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


def compute_explanations(
    db_path: Path,
    model_path: Path,
    text_model_path: Path | None = None,
) -> int:
    """Generate SHAP explanations and narratives for active listings.

    Writes results to the ``active_explanations`` table with columns:
    property_id, narrative, shap_json, text_premium, word_impacts_json, explained_at

    Returns the number of rows written.
    """
    import json

    from src.models.explainability import NarrativeGenerator, SHAPExplainer

    try:
        explainer = SHAPExplainer(model_path)
    except FileNotFoundError:
        logger.warning("Price model not found at %s — skipping explanations", model_path)
        return 0

    text_pipeline = None
    if text_model_path and text_model_path.exists():
        try:
            from src.models.text_pipeline import TextPricePipeline

            text_pipeline = TextPricePipeline.load(text_model_path)
            logger.info("Loaded text pipeline from %s", text_model_path)
        except Exception as exc:
            logger.warning("Could not load text pipeline: %s", exc)

    conn = duckdb.connect(str(db_path))
    tables = [r[0] for r in conn.execute("SHOW TABLES").fetchall()]
    if TABLE_NAME not in tables:
        conn.close()
        logger.warning("Table %s not found — run aggregate first", TABLE_NAME)
        return 0

    has_archive = "description_archive" in tables
    has_predictions = "active_predictions" in tables

    if has_archive and has_predictions:
        query = f"""
            SELECT
                a.property_id, a.asking_price,
                a.rooms, a.living_area, a.association_fee,
                a.building_year, a.latitude, a.longitude,
                a.neighborhood, a.housing_type, a.ownership_type,
                d.description,
                ap.predicted_price, ap.price_diff_pct
            FROM {TABLE_NAME} a
            LEFT JOIN active_predictions ap ON a.property_id = ap.property_id
            LEFT JOIN description_archive d ON a.property_id = d.property_id
            WHERE a.living_area IS NOT NULL
              AND a.rooms IS NOT NULL
              AND a.latitude IS NOT NULL
              AND a.longitude IS NOT NULL
        """
    elif has_predictions:
        query = f"""
            SELECT
                a.property_id, a.asking_price,
                a.rooms, a.living_area, a.association_fee,
                a.building_year, a.latitude, a.longitude,
                a.neighborhood, a.housing_type, a.ownership_type,
                NULL as description,
                ap.predicted_price, ap.price_diff_pct
            FROM {TABLE_NAME} a
            LEFT JOIN active_predictions ap ON a.property_id = ap.property_id
            WHERE a.living_area IS NOT NULL
              AND a.rooms IS NOT NULL
              AND a.latitude IS NOT NULL
              AND a.longitude IS NOT NULL
        """
    else:
        query = f"""
            SELECT
                a.property_id, a.asking_price,
                a.rooms, a.living_area, a.association_fee,
                a.building_year, a.latitude, a.longitude,
                a.neighborhood, a.housing_type, a.ownership_type,
                NULL as description,
                NULL as predicted_price, NULL as price_diff_pct
            FROM {TABLE_NAME} a
            WHERE a.living_area IS NOT NULL
              AND a.rooms IS NOT NULL
              AND a.latitude IS NOT NULL
              AND a.longitude IS NOT NULL
        """

    df = conn.execute(query).df()
    conn.close()

    logger.info("Computing explanations for %d active listings", len(df))
    gen = NarrativeGenerator()
    from datetime import date
    today = str(date.today())
    rows = []

    for _, row in df.iterrows():

        def _safe(val, default=0.0):
            return default if pd.isna(val) else val

        try:
            shap_features = explainer.explain(
                rooms=float(row["rooms"]),
                living_area=float(row["living_area"]),
                association_fee=float(_safe(row.get("association_fee"), 0)),
                building_year=int(_safe(row.get("building_year"), 1970)),
                latitude=float(row["latitude"]),
                longitude=float(row["longitude"]),
                neighborhood=str(_safe(row.get("neighborhood"), "Unknown")),
                housing_type=str(_safe(row.get("housing_type"), "Lägenhet")),
                ownership_type=str(_safe(row.get("ownership_type"), "Bostadsrätt")),
            )

            text_analysis = None
            description = row.get("description")
            if text_pipeline and description and not pd.isna(description):
                try:
                    text_analysis = text_pipeline.analyze_description(str(description))
                except Exception as exc:
                    logger.debug("Text analysis failed for %s: %s", row["property_id"], exc)

            asking = _safe(row.get("asking_price"), 0)
            predicted = _safe(row.get("predicted_price"), 0)
            neighborhood = str(_safe(row.get("neighborhood"), ""))

            narrative = ""
            if asking > 0 and predicted > 0:
                narrative = gen.generate(
                    shap_features=shap_features,
                    asking_price=float(asking),
                    predicted_price=int(predicted),
                    neighborhood=neighborhood,
                    text_analysis=text_analysis,
                )

            text_premium = None
            word_impacts_json = None
            if text_analysis:
                text_premium = text_analysis.get("predicted_premium")
                word_impacts = text_analysis.get("word_impacts", [])
                if word_impacts:
                    word_impacts_json = json.dumps(word_impacts)

            rows.append(
                {
                    "property_id": row["property_id"],
                    "narrative": narrative,
                    "shap_json": json.dumps(shap_features),
                    "text_premium": text_premium,
                    "word_impacts_json": word_impacts_json,
                    "explained_at": today,
                }
            )
        except Exception as exc:
            logger.warning("Explanation failed for %s: %s", row["property_id"], exc)

    if not rows:
        logger.info("No explanations generated")
        return 0

    explanations_df = pd.DataFrame(rows)
    conn = duckdb.connect(str(db_path))
    conn.execute("DROP TABLE IF EXISTS active_explanations")
    conn.execute("CREATE TABLE active_explanations AS SELECT * FROM explanations_df")
    count = conn.execute("SELECT COUNT(*) FROM active_explanations").fetchone()[0]
    conn.close()
    logger.info("Wrote %d explanations to active_explanations", count)
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
    parser.add_argument(
        "--text-model",
        type=Path,
        default=Path("models/text_pipeline.joblib"),
    )
    parser.add_argument("--predict", action="store_true", help="Run predictions after aggregation")
    parser.add_argument("--explain", action="store_true", help="Run SHAP explanations after predictions")
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

    if args.explain and count > 0 and args.model.exists():
        text_model = args.text_model if args.text_model.exists() else None
        compute_explanations(args.db, args.model, text_model)
    elif args.explain and not args.model.exists():
        logger.warning("Model not found at %s — skipping explanations", args.model)


if __name__ == "__main__":
    main()
