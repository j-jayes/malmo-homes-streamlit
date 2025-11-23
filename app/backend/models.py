from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime

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
