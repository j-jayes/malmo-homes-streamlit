from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.backend.database import get_db_connection
from app.backend.models import (
    PropertyStats,
    Property,
    PropertyWithPrediction,
    ActiveListing,
    PredictionRequest,
    PredictionResponse,
)

app = FastAPI(title="Malmo Homes API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

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
    limit: int = 1000,
):
    from app.backend.database import get_properties

    return get_properties(min_price, max_price, min_area, max_area, rooms, limit)


@app.get("/properties/predicted", response_model=list[PropertyWithPrediction])
async def get_properties_with_predictions_endpoint(
    min_price: float = None,
    max_price: float = None,
    min_area: float = None,
    max_area: float = None,
    rooms: float = None,
    neighborhood: str = None,
    limit: int = 1000,
):
    """Properties enriched with pre-computed price predictions."""
    from app.backend.database import get_properties_with_predictions

    return get_properties_with_predictions(
        min_price, max_price, min_area, max_area, rooms, neighborhood, limit
    )


@app.get("/deals", response_model=list[PropertyWithPrediction])
async def get_best_deals_endpoint(limit: int = 10):
    """Top deals — properties that sold most below their predicted value."""
    from app.backend.database import get_best_deals

    return get_best_deals(limit)


@app.get("/stats", response_model=PropertyStats)
async def get_stats_endpoint():
    from app.backend.database import get_stats

    return get_stats()


@app.get("/active", response_model=list[ActiveListing])
async def get_active_listings_endpoint(
    min_price: float = None,
    max_price: float = None,
    min_area: float = None,
    max_area: float = None,
    rooms: float = None,
    neighborhood: str = None,
    limit: int = 500,
):
    """Active (for-sale) listings with ML price predictions."""
    from app.backend.database import get_active_listings

    return get_active_listings(
        min_price, max_price, min_area, max_area, rooms, neighborhood, limit
    )


@app.post("/predict", response_model=PredictionResponse)
async def predict_price(request: PredictionRequest):
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
