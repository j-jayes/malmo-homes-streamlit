from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.backend.database import get_db_connection
from app.backend.models import PropertyStats, Property

app = FastAPI(title="Malmo Homes API")

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],  # Vite default port
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
async def root():
    return {"message": "Malmo Homes API is running"}

@app.get("/health")
async def health_check():
    """Check database connection"""
    try:
        conn = get_db_connection()
        conn.execute("SELECT 1")
        conn.close()
        return {"status": "healthy", "database": "connected"}
    except Exception as e:
        return {"status": "unhealthy", "database": str(e)}

@app.get("/properties", response_model=list[Property])
async def get_properties_endpoint(
    min_price: float = None,
    max_price: float = None,
    min_area: float = None,
    max_area: float = None,
    rooms: float = None,
    limit: int = 1000
):
    """Get properties with optional filters."""
    from app.backend.database import get_properties
    return get_properties(min_price, max_price, min_area, max_area, rooms, limit)

@app.get("/stats", response_model=PropertyStats)
async def get_stats_endpoint():
    """Get dataset statistics."""
    from app.backend.database import get_stats
    return get_stats()
