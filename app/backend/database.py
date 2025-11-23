import duckdb
from pathlib import Path
import os

# Define database path relative to project root
# Assuming running from project root
DB_PATH = Path("data/database/properties.duckdb")

def get_db_connection():
    """Create a connection to the DuckDB database."""
    if not DB_PATH.exists():
        # Fallback for development if running from app/backend
        alt_path = Path("../../data/database/properties.duckdb")
        if alt_path.exists():
            return duckdb.connect(str(alt_path), read_only=True)
        raise FileNotFoundError(f"Database not found at {DB_PATH}")
    
    return duckdb.connect(str(DB_PATH), read_only=True)

def get_properties(
    min_price: float = None,
    max_price: float = None,
    min_area: float = None,
    max_area: float = None,
    rooms: float = None,
    limit: int = 1000
):
    """Query properties with filters."""
    conn = get_db_connection()
    
    query = """
        SELECT 
            property_id, 
            url, 
            address, 
            city, 
            COALESCE(final_price, asking_price) as price,
            rooms, 
            living_area as area, 
            association_fee as monthly_fee, 
            latitude as lat, 
            longitude as lng,
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
    
    # Execute and fetch as dicts
    result = conn.execute(query, params).fetchall()
    columns = [desc[0] for desc in conn.description]
    
    properties = []
    for row in result:
        properties.append(dict(zip(columns, row)))
        
    conn.close()
    return properties

def get_stats():
    """Get basic statistics about the dataset."""
    conn = get_db_connection()
    
    query = """
        SELECT 
            COUNT(*) as total_properties,
            AVG(COALESCE(final_price, asking_price)) as avg_price,
            AVG(COALESCE(final_price, asking_price) / NULLIF(living_area, 0)) as avg_price_per_sqm
        FROM properties
        WHERE COALESCE(final_price, asking_price) IS NOT NULL AND living_area IS NOT NULL
    """
    
    result = conn.execute(query).fetchone()
    conn.close()
    
    return {
        "total_properties": result[0],
        "avg_price": result[1] or 0,
        "avg_price_per_sqm": result[2] or 0
    }
