from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import datetime, date

class PropertyStats(BaseModel):
    total_properties: int
    avg_price: float
    avg_price_per_sqm: float

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


class PredictionResponse(BaseModel):
    """Response from the /predict endpoint."""
    predicted_price: int
    confidence_low: int
    confidence_high: int
    predicted_price_per_sqm: Optional[int] = None
