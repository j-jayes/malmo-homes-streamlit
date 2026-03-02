import duckdb
from pathlib import Path

DB_PATH = Path("data/database/properties.duckdb")


def get_db_connection():
    """Create a read-only connection to the DuckDB database."""
    if not DB_PATH.exists():
        alt_path = Path("../../data/database/properties.duckdb")
        if alt_path.exists():
            return duckdb.connect(str(alt_path), read_only=True)
        raise FileNotFoundError(f"Database not found at {DB_PATH}")
    return duckdb.connect(str(DB_PATH), read_only=True)


def _rows_to_dicts(conn) -> list[dict]:
    columns = [desc[0] for desc in conn.description]
    return [dict(zip(columns, row)) for row in conn.fetchall()]


def get_properties(
    min_price: float = None,
    max_price: float = None,
    min_area: float = None,
    max_area: float = None,
    rooms: float = None,
    limit: int = 1000,
):
    """Query properties with filters."""
    conn = get_db_connection()

    query = """
        SELECT
            property_id, url, address, city,
            COALESCE(final_price, asking_price) as price,
            rooms, living_area as area,
            association_fee as monthly_fee,
            latitude as lat, longitude as lng,
            scraped_at
        FROM properties
        WHERE 1=1
    """
    params = []

    if min_price:
        query += " AND COALESCE(final_price, asking_price) >= ?"
        params.append(min_price)
    if max_price:
        query += " AND COALESCE(final_price, asking_price) <= ?"
        params.append(max_price)
    if min_area:
        query += " AND living_area >= ?"
        params.append(min_area)
    if max_area:
        query += " AND living_area <= ?"
        params.append(max_area)
    if rooms:
        query += " AND rooms >= ?"
        params.append(rooms)

    query += " ORDER BY scraped_at DESC LIMIT ?"
    params.append(limit)

    result = conn.execute(query, params)
    rows = _rows_to_dicts(result)
    conn.close()
    return rows


def get_properties_with_predictions(
    min_price: float = None,
    max_price: float = None,
    min_area: float = None,
    max_area: float = None,
    rooms: float = None,
    neighborhood: str = None,
    limit: int = 1000,
):
    """Query properties joined with pre-computed predictions."""
    conn = get_db_connection()

    query = """
        SELECT
            p.property_id, p.url, p.address, p.city,
            COALESCE(p.final_price, p.asking_price) AS price,
            p.rooms, p.living_area AS area,
            p.association_fee AS monthly_fee,
            p.latitude AS lat, p.longitude AS lng,
            p.neighborhood,
            p.sold_date,
            p.scraped_at,
            pr.predicted_price,
            pr.confidence_low,
            pr.confidence_high,
            pr.predicted_price_per_sqm,
            pr.price_diff,
            pr.price_diff_pct
        FROM properties p
        INNER JOIN predictions pr ON p.property_id = pr.property_id
        WHERE COALESCE(p.final_price, p.asking_price) IS NOT NULL
    """
    params = []

    if min_price:
        query += " AND COALESCE(p.final_price, p.asking_price) >= ?"
        params.append(min_price)
    if max_price:
        query += " AND COALESCE(p.final_price, p.asking_price) <= ?"
        params.append(max_price)
    if min_area:
        query += " AND p.living_area >= ?"
        params.append(min_area)
    if max_area:
        query += " AND p.living_area <= ?"
        params.append(max_area)
    if rooms:
        query += " AND p.rooms >= ?"
        params.append(rooms)
    if neighborhood:
        query += " AND p.neighborhood = ?"
        params.append(neighborhood)

    query += " ORDER BY p.scraped_at DESC LIMIT ?"
    params.append(limit)

    result = conn.execute(query, params)
    rows = _rows_to_dicts(result)
    conn.close()
    return rows


def get_best_deals(limit: int = 10):
    """Return properties that sold most below their predicted price (biggest bargains)."""
    conn = get_db_connection()

    query = """
        SELECT
            p.property_id, p.url, p.address, p.city,
            COALESCE(p.final_price, p.asking_price) AS price,
            p.rooms, p.living_area AS area,
            p.association_fee AS monthly_fee,
            p.latitude AS lat, p.longitude AS lng,
            p.neighborhood,
            p.sold_date,
            p.scraped_at,
            pr.predicted_price,
            pr.confidence_low,
            pr.confidence_high,
            pr.predicted_price_per_sqm,
            pr.price_diff,
            pr.price_diff_pct
        FROM properties p
        INNER JOIN predictions pr ON p.property_id = pr.property_id
        WHERE pr.price_diff IS NOT NULL
          AND pr.price_diff_pct < -5
          AND COALESCE(p.final_price, p.asking_price) IS NOT NULL
          AND p.sold_date >= '2024-01-01'
        ORDER BY pr.price_diff_pct ASC
        LIMIT ?
    """
    result = conn.execute(query, [limit])
    rows = _rows_to_dicts(result)
    conn.close()
    return rows


def get_active_listings(
    min_price: float = None,
    max_price: float = None,
    min_area: float = None,
    max_area: float = None,
    rooms: float = None,
    neighborhood: str = None,
    limit: int = 500,
):
    """Query active (for-sale) listings joined with ML predictions."""
    conn = get_db_connection()

    # Check if tables exist
    tables = [r[0] for r in conn.execute("SHOW TABLES").fetchall()]
    if "active_listings" not in tables:
        conn.close()
        return []

    has_predictions = "active_predictions" in tables

    if has_predictions:
        query = """
            SELECT
                a.property_id, a.url, a.address, a.city,
                a.asking_price AS price,
                a.rooms, a.living_area AS area,
                a.association_fee AS monthly_fee,
                a.latitude AS lat, a.longitude AS lng,
                a.neighborhood,
                a.listed_date,
                a.days_on_market,
                a.scraped_at,
                ap.predicted_price,
                ap.confidence_low,
                ap.confidence_high,
                ap.predicted_price_per_sqm,
                ap.price_diff,
                ap.price_diff_pct
            FROM active_listings a
            LEFT JOIN active_predictions ap ON a.property_id = ap.property_id
            WHERE a.asking_price IS NOT NULL
        """
    else:
        query = """
            SELECT
                a.property_id, a.url, a.address, a.city,
                a.asking_price AS price,
                a.rooms, a.living_area AS area,
                a.association_fee AS monthly_fee,
                a.latitude AS lat, a.longitude AS lng,
                a.neighborhood,
                a.listed_date,
                a.days_on_market,
                a.scraped_at,
                NULL AS predicted_price,
                NULL AS confidence_low,
                NULL AS confidence_high,
                NULL AS predicted_price_per_sqm,
                NULL AS price_diff,
                NULL AS price_diff_pct
            FROM active_listings a
            WHERE a.asking_price IS NOT NULL
        """

    params = []
    if min_price:
        query += " AND a.asking_price >= ?"
        params.append(min_price)
    if max_price:
        query += " AND a.asking_price <= ?"
        params.append(max_price)
    if min_area:
        query += " AND a.living_area >= ?"
        params.append(min_area)
    if max_area:
        query += " AND a.living_area <= ?"
        params.append(max_area)
    if rooms:
        query += " AND a.rooms >= ?"
        params.append(rooms)
    if neighborhood:
        query += " AND a.neighborhood = ?"
        params.append(neighborhood)

    query += " ORDER BY a.scraped_at DESC LIMIT ?"
    params.append(limit)

    result = conn.execute(query, params)
    rows = _rows_to_dicts(result)
    conn.close()
    return rows


def get_stats():
    """Get basic statistics including prediction model coverage."""
    conn = get_db_connection()

    result = conn.execute("""
        SELECT
            COUNT(*) as total_properties,
            AVG(COALESCE(final_price, asking_price)) as avg_price,
            AVG(COALESCE(final_price, asking_price) / NULLIF(living_area, 0)) as avg_price_per_sqm
        FROM properties
        WHERE COALESCE(final_price, asking_price) IS NOT NULL
          AND living_area IS NOT NULL
    """).fetchone()

    pred_result = conn.execute("""
        SELECT
            COUNT(*) as predictions_count,
            AVG(ABS(price_diff_pct)) as avg_abs_error_pct
        FROM predictions
        WHERE price_diff_pct IS NOT NULL
    """).fetchone()

    active_count = 0
    try:
        active_count = conn.execute("SELECT COUNT(*) FROM active_listings").fetchone()[0]
    except Exception:
        pass

    conn.close()

    return {
        "total_properties": result[0],
        "avg_price": result[1] or 0,
        "avg_price_per_sqm": result[2] or 0,
        "predictions_count": pred_result[0] if pred_result else 0,
        "model_avg_error_pct": round(pred_result[1], 1) if pred_result and pred_result[1] else None,
        "active_listings_count": active_count,
    }


def get_explanation(property_id: str) -> dict | None:
    """Retrieve pre-computed SHAP explanation and narrative for a property."""
    import json

    conn = get_db_connection()
    tables = [r[0] for r in conn.execute("SHOW TABLES").fetchall()]
    if "active_explanations" not in tables:
        conn.close()
        return None

    has_predictions = "active_predictions" in tables
    has_listings = "active_listings" in tables

    if has_predictions and has_listings:
        query = """
            SELECT
                ae.property_id,
                ae.narrative,
                ae.shap_json,
                ae.text_premium,
                ae.word_impacts_json,
                ap.predicted_price,
                al.asking_price,
                ap.price_diff_pct
            FROM active_explanations ae
            LEFT JOIN active_predictions ap ON ae.property_id = ap.property_id
            LEFT JOIN active_listings al ON ae.property_id = al.property_id
            WHERE ae.property_id = ?
        """
    else:
        query = """
            SELECT
                ae.property_id,
                ae.narrative,
                ae.shap_json,
                ae.text_premium,
                ae.word_impacts_json,
                NULL AS predicted_price,
                NULL AS asking_price,
                NULL AS price_diff_pct
            FROM active_explanations ae
            WHERE ae.property_id = ?
        """

    result = conn.execute(query, [property_id])
    rows = _rows_to_dicts(result)
    conn.close()

    if not rows:
        return None

    row = rows[0]

    shap_features = []
    if row.get("shap_json"):
        try:
            shap_features = json.loads(row["shap_json"])
        except (json.JSONDecodeError, TypeError):
            pass

    word_impacts = []
    if row.get("word_impacts_json"):
        try:
            word_impacts = json.loads(row["word_impacts_json"])
        except (json.JSONDecodeError, TypeError):
            pass

    return {
        "property_id": row["property_id"],
        "narrative": row.get("narrative") or "",
        "predicted_price": row.get("predicted_price"),
        "asking_price": row.get("asking_price"),
        "price_diff_pct": row.get("price_diff_pct"),
        "shap_features": shap_features,
        "text_premium": row.get("text_premium"),
        "word_impacts": word_impacts,
    }


def get_neighborhood_stats() -> list[dict]:
    """Neighbourhood median price/m² and days-on-market, qualifying >= 10 sales."""
    conn = get_db_connection()
    result = conn.execute("""
        SELECT
            neighborhood,
            MEDIAN(final_price / living_area) AS median_price_per_sqm,
            MEDIAN(final_price)               AS median_price,
            COUNT(*)                          AS count,
            MEDIAN(days_on_market)            AS avg_days_on_market
        FROM properties
        WHERE neighborhood IS NOT NULL
          AND living_area > 0
          AND final_price > 0
        GROUP BY neighborhood
        HAVING COUNT(*) >= 10
        ORDER BY median_price_per_sqm DESC
    """)
    rows = _rows_to_dicts(result)
    conn.close()
    return rows


def get_room_stats() -> list[dict]:
    """Median price and price/m² grouped by room count (1–6)."""
    conn = get_db_connection()
    result = conn.execute("""
        SELECT
            CAST(rooms AS INT) AS rooms,
            MEDIAN(final_price)               AS median_price,
            MEDIAN(final_price / living_area) AS median_price_per_sqm,
            MEDIAN(living_area)               AS avg_area,
            COUNT(*) AS count
        FROM properties
        WHERE rooms BETWEEN 1 AND 6
          AND final_price > 0
          AND living_area > 0
          AND rooms IS NOT NULL
        GROUP BY CAST(rooms AS INT)
        ORDER BY rooms
    """)
    rows = _rows_to_dicts(result)
    conn.close()
    return rows


def get_price_trend() -> list[dict]:
    """Monthly median price over the last 24 months."""
    conn = get_db_connection()
    result = conn.execute("""
        SELECT
            LEFT(sold_date, 7)   AS month,
            MEDIAN(final_price)  AS median_price,
            COUNT(*)             AS count
        FROM properties
        WHERE sold_date IS NOT NULL
          AND sold_date >= '2024-01-01'
          AND final_price > 0
        GROUP BY LEFT(sold_date, 7)
        ORDER BY month
    """)
    rows = _rows_to_dicts(result)
    conn.close()
    return rows


def get_building_decade_stats() -> list[dict]:
    """Median price/m² grouped by building decade."""
    conn = get_db_connection()
    result = conn.execute("""
        SELECT
            CONCAT(CAST((CAST(building_year AS INT) / 10) * 10 AS VARCHAR), 's') AS decade,
            (CAST(building_year AS INT) / 10) * 10                               AS decade_start,
            MEDIAN(final_price / living_area)                                     AS median_price_per_sqm,
            COUNT(*) AS count
        FROM properties
        WHERE building_year IS NOT NULL
          AND CAST(building_year AS INT) BETWEEN 1900 AND 2024
          AND living_area > 0
          AND final_price > 0
        GROUP BY decade, decade_start
        HAVING COUNT(*) >= 5
        ORDER BY decade_start
    """)
    rows = _rows_to_dicts(result)
    conn.close()
    return rows


def get_fee_analysis() -> list[dict]:
    """Median price bucketed by fee, split into small (<60m²) vs large (≥80m²) apartments."""
    conn = get_db_connection()
    result = conn.execute("""
        SELECT
            ROUND(association_fee / 500.0) * 500          AS fee_bucket,
            MEDIAN(final_price)                            AS price,
            CASE
                WHEN living_area < 60 THEN 'Small (<60m²)'
                ELSE 'Large (≥80m²)'
            END                                            AS area_group,
            COUNT(*) AS count
        FROM properties
        WHERE association_fee > 0
          AND association_fee <= 8000
          AND final_price > 0
          AND (living_area < 60 OR living_area >= 80)
        GROUP BY fee_bucket, area_group
        HAVING COUNT(*) >= 3
        ORDER BY area_group, fee_bucket
    """)
    rows = _rows_to_dicts(result)
    conn.close()
    return rows


def get_nlp_training_data(limit: int = 5000):
    """Retrieve text descriptions paired with final sale prices for NLP modeling."""
    conn = get_db_connection()
    
    # Check if necessary tables exist
    tables = [r[0] for r in conn.execute("SHOW TABLES").fetchall()]
    if "description_archive" not in tables or "properties" not in tables:
        conn.close()
        return []

    # Get description, original asking price, and final sold price for computing differences
    query = """
        SELECT
            d.property_id as active_id,
            p.property_id as sold_id,
            d.description,
            d.city,
            d.neighborhood,
            d.rooms,
            d.living_area as area,
            d.asking_price,
            p.final_price,
            p.price_change,
            p.price_change_pct,
            p.sold_date,
            p.days_on_market
        FROM description_archive d
        JOIN properties p ON d.sold_property_id = p.property_id
        WHERE d.description IS NOT NULL
          AND p.final_price IS NOT NULL
    """
    
    query += " ORDER BY p.sold_date DESC LIMIT ?"
    
    try:
        result = conn.execute(query, [limit])
        rows = _rows_to_dicts(result)
        return rows
    except Exception as e:
        print(f"Error executing NLP query: {e}")
        return []
    finally:
        conn.close()
