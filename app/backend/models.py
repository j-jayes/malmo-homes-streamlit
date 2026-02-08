from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import datetime, date


class PropertyStats(BaseModel):
    total_properties: int
    avg_price: float
    avg_price_per_sqm: float
    predictions_count: int = 0
    model_avg_error_pct: Optional[float] = None
    active_listings_count: int = 0


class Property(BaseModel):
    property_id: str
    url: str
    title: Optional[str] = None
    address: Optional[str] = None
    city: Optional[str] = None
    price: Optional[float] = None
    rooms: Optional[float] = None
    area: Optional[float] = None
    monthly_fee: Optional[float] = None
    lat: Optional[float] = None
    lng: Optional[float] = None
    scraped_at: datetime


class PropertyWithPrediction(BaseModel):
    property_id: str
    url: str
    address: Optional[str] = None
    city: Optional[str] = None
    price: Optional[float] = None
    rooms: Optional[float] = None
    area: Optional[float] = None
    monthly_fee: Optional[float] = None
    lat: Optional[float] = None
    lng: Optional[float] = None
    neighborhood: Optional[str] = None
    sold_date: Optional[str] = None
    scraped_at: Optional[datetime] = None
    predicted_price: Optional[int] = None
    confidence_low: Optional[int] = None
    confidence_high: Optional[int] = None
    predicted_price_per_sqm: Optional[int] = None
    price_diff: Optional[int] = None
    price_diff_pct: Optional[float] = None


class PredictionRequest(BaseModel):
    """Request body for the /predict endpoint."""
    rooms: float = Field(..., ge=1, le=20, description="Number of rooms")
    living_area: float = Field(..., ge=10, le=500, description="Living area in m²")
    association_fee: float = Field(..., ge=0, description="Monthly fee (avgift) in SEK")
    building_year: int = Field(..., ge=1800, le=2030, description="Year built")
    latitude: float = Field(..., ge=55.0, le=56.0, description="Latitude (Malmö range)")
    longitude: float = Field(..., ge=12.5, le=13.5, description="Longitude (Malmö range)")
    neighborhood: str = Field(..., description="Neighborhood name (e.g. 'Västra Hamnen')")
    housing_type: str = Field(default="Lägenhet", description="Housing type")
    ownership_type: str = Field(default="Bostadsrätt", description="Ownership type")
    target_date: Optional[date] = Field(default=None, description="Date to predict price for (default: today)")


class ActiveListing(BaseModel):
    """An active (for-sale) property listing with optional ML prediction."""
    property_id: str
    url: str
    address: Optional[str] = None
    city: Optional[str] = None
    price: Optional[float] = None
    rooms: Optional[float] = None
    area: Optional[float] = None
    monthly_fee: Optional[float] = None
    lat: Optional[float] = None
    lng: Optional[float] = None
    neighborhood: Optional[str] = None
    listed_date: Optional[str] = None
    days_on_market: Optional[int] = None
    scraped_at: Optional[datetime] = None
    predicted_price: Optional[int] = None
    confidence_low: Optional[int] = None
    confidence_high: Optional[int] = None
    predicted_price_per_sqm: Optional[int] = None
    price_diff: Optional[int] = None
    price_diff_pct: Optional[float] = None


class PredictionResponse(BaseModel):
    """Response from the /predict endpoint."""
    predicted_price: int
    confidence_low: int
    confidence_high: int
    predicted_price_per_sqm: Optional[int] = None
