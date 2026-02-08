from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.backend.database import get_db_connection
from app.backend.models import PropertyStats, Property, PredictionRequest, PredictionResponse

app = FastAPI(title="Malmo Homes API")

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],  # Vite default port
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Lazy-loaded prediction service (initialised on first /predict call)
_prediction_service = None


def _get_prediction_service():
    global _prediction_service
    if _prediction_service is None:
        from pathlib import Path
        from src.models.prediction_service import PredictionService

        model_path = Path("models/price_model.joblib")
        if not model_path.exists():
            raise FileNotFoundError(
                "Model not found. Run `python scripts/train_model.py` first."
            )
        _prediction_service = PredictionService.from_artifact(model_path)
    return _prediction_service

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

@app.post("/predict", response_model=PredictionResponse)
async def predict_price(request: PredictionRequest):
    """Predict property price given features and an optional target date."""
    from fastapi import HTTPException

    try:
        svc = _get_prediction_service()
    except FileNotFoundError as exc:
        raise HTTPException(status_code=503, detail=str(exc))

    prediction = svc.predict(
        rooms=request.rooms,
        living_area=request.living_area,
        association_fee=request.association_fee,
        building_year=request.building_year,
        latitude=request.latitude,
        longitude=request.longitude,
        neighborhood=request.neighborhood,
        housing_type=request.housing_type,
        ownership_type=request.ownership_type,
        target_date=request.target_date,
    )

    return PredictionResponse(
        predicted_price=prediction.predicted_price,
        confidence_low=prediction.confidence_low,
        confidence_high=prediction.confidence_high,
        predicted_price_per_sqm=prediction.predicted_price_per_sqm,
    )
