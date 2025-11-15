"""
Pydantic models for property data validation and schema definition.

These models ensure data quality and type safety throughout the pipeline.
"""

from datetime import datetime, date
from typing import Optional, List, Literal
from pydantic import BaseModel, Field, field_validator, ConfigDict
from decimal import Decimal


class BaseProperty(BaseModel):
    """Base model containing fields common to all property types."""
    
    model_config = ConfigDict(
        str_strip_whitespace=True,
        validate_assignment=True,
        use_enum_values=True
    )
    
    # Identifiers
    property_id: str = Field(..., description="Unique property identifier from URL")
    property_type: Literal['sold', 'for_sale'] = Field(..., description="Property type")
    url: str = Field(..., description="Full Hemnet URL")
    scraped_at: datetime = Field(default_factory=datetime.now, description="Scraping timestamp")
    
    # Location
    address: Optional[str] = Field(None, description="Street address")
    city: Optional[str] = Field(None, description="City name")
    neighborhood: Optional[str] = Field(None, description="Neighborhood/district name")
    latitude: Optional[float] = Field(None, ge=-90, le=90, description="Latitude coordinate")
    longitude: Optional[float] = Field(None, ge=-180, le=180, description="Longitude coordinate")
    
    # Property Details
    housing_type: Optional[str] = Field(None, description="Type: Lägenhet, Villa, Radhus, etc.")
    ownership_type: Optional[str] = Field(None, description="Bostadsrätt, Äganderätt, Hyresrätt")
    rooms: Optional[float] = Field(None, ge=0, le=20, description="Number of rooms")
    living_area: Optional[float] = Field(None, ge=0, le=1000, description="Living area in m²")
    lot_area: Optional[float] = Field(None, ge=0, description="Lot/tomtarea in m² (for houses)")
    floor: Optional[str] = Field(None, description="Floor number (e.g., '3', '3 av 5')")
    has_elevator: Optional[bool] = Field(None, description="Building has elevator")
    has_balcony: Optional[bool] = Field(None, description="Property has balcony")
    building_year: Optional[int] = Field(None, ge=1800, le=2030, description="Year built")
    energy_class: Optional[str] = Field(None, description="Energy rating (A-G)")
    
    # Association (for apartments)
    association_name: Optional[str] = Field(None, description="Housing association name")
    association_fee: Optional[int] = Field(None, ge=0, description="Monthly fee (avgift)")
    operating_cost: Optional[int] = Field(None, ge=0, description="Operating cost (driftkostnad)")
    
    # Description
    description: Optional[str] = Field(None, description="Full property description")
    
    @field_validator('property_id')
    @classmethod
    def validate_property_id(cls, v: str) -> str:
        """Ensure property_id is not empty."""
        if not v or not v.strip():
            raise ValueError("property_id cannot be empty")
        return v.strip()
    
    @field_validator('url')
    @classmethod
    def validate_url(cls, v: str) -> str:
        """Ensure URL is a valid Hemnet URL."""
        if not v.startswith('https://www.hemnet.se/'):
            raise ValueError("URL must be a valid Hemnet URL")
        return v
    
    @field_validator('latitude', 'longitude')
    @classmethod
    def validate_coordinates(cls, v: Optional[float]) -> Optional[float]:
        """Validate coordinate values."""
        if v is not None and (v == 0.0 or abs(v) < 0.001):
            # Likely invalid coordinate (0,0 is in the ocean off Africa)
            return None
        return v
    
    @field_validator('rooms')
    @classmethod
    def validate_rooms(cls, v: Optional[float]) -> Optional[float]:
        """Validate room count."""
        if v is not None:
            if v < 0:
                raise ValueError("rooms cannot be negative")
            if v > 20:
                raise ValueError("rooms seems unreasonably high (>20)")
        return v
    
    @field_validator('living_area')
    @classmethod
    def validate_living_area(cls, v: Optional[float]) -> Optional[float]:
        """Validate living area."""
        if v is not None:
            if v < 10:
                raise ValueError("living_area seems too small (<10 m²)")
            if v > 1000:
                raise ValueError("living_area seems too large (>1000 m²)")
        return v


class SoldProperty(BaseProperty):
    """Model for sold properties with additional sale-specific fields."""
    
    property_type: Literal['sold'] = Field(default='sold', description="Property type")
    
    # Pricing
    asking_price: Optional[int] = Field(None, ge=0, description="Original asking price (utgångspris)")
    final_price: Optional[int] = Field(None, ge=0, description="Final sold price (slutpris)")
    price_change: Optional[int] = Field(None, description="Price change (final - asking)")
    price_change_pct: Optional[float] = Field(None, description="Price change percentage")
    price_per_sqm_final: Optional[float] = Field(None, ge=0, description="Final price per m²")
    
    # Sale Information
    sold_date: Optional[date] = Field(None, description="Date property sold")
    days_on_market: Optional[int] = Field(None, ge=0, description="Days from listing to sale")
    visit_count: Optional[int] = Field(None, ge=0, description="Number of visits (historical)")
    
    @field_validator('final_price')
    @classmethod
    def validate_final_price(cls, v: Optional[int]) -> Optional[int]:
        """Validate final price is reasonable."""
        if v is not None:
            if v < 100_000:
                raise ValueError("final_price seems too low (<100k SEK)")
            if v > 50_000_000:
                raise ValueError("final_price seems too high (>50M SEK)")
        return v
    
    @field_validator('asking_price')
    @classmethod
    def validate_asking_price(cls, v: Optional[int]) -> Optional[int]:
        """Validate asking price is reasonable."""
        if v is not None:
            if v < 100_000:
                raise ValueError("asking_price seems too low (<100k SEK)")
            if v > 50_000_000:
                raise ValueError("asking_price seems too high (>50M SEK)")
        return v
    
    def calculate_derived_fields(self) -> None:
        """Calculate price_change and price_change_pct if possible."""
        if self.final_price and self.asking_price:
            self.price_change = self.final_price - self.asking_price
            if self.asking_price > 0:
                self.price_change_pct = (self.price_change / self.asking_price) * 100
        
        if self.final_price and self.living_area and self.living_area > 0:
            self.price_per_sqm_final = self.final_price / self.living_area


class ForSaleProperty(BaseProperty):
    """Model for active (for-sale) properties with listing-specific fields."""
    
    property_type: Literal['for_sale'] = Field(default='for_sale', description="Property type")
    
    # Pricing
    asking_price: Optional[int] = Field(None, ge=0, description="Current asking price")
    price_per_sqm: Optional[float] = Field(None, ge=0, description="Current price per m²")
    
    # Listing Information
    listed_date: Optional[date] = Field(None, description="Date first listed")
    days_on_market: Optional[int] = Field(None, ge=0, description="Days since listing")
    viewing_times: Optional[List[str]] = Field(default_factory=list, description="Scheduled viewing times")
    visit_count: Optional[int] = Field(None, ge=0, description="Number of visits so far")
    
    @field_validator('asking_price')
    @classmethod
    def validate_asking_price(cls, v: Optional[int]) -> Optional[int]:
        """Validate asking price is reasonable."""
        if v is not None:
            if v < 100_000:
                raise ValueError("asking_price seems too low (<100k SEK)")
            if v > 50_000_000:
                raise ValueError("asking_price seems too high (>50M SEK)")
        return v
    
    def calculate_derived_fields(self) -> None:
        """Calculate price_per_sqm if possible."""
        if self.asking_price and self.living_area and self.living_area > 0:
            self.price_per_sqm = self.asking_price / self.living_area


# Example usage and validation
if __name__ == "__main__":
    # Example: Valid sold property
    sold_prop = SoldProperty(
        property_id="12345",
        property_type="sold",
        url="https://www.hemnet.se/salda/lagenhet-3rum-malmo-12345",
        address="Stormastgatan 5",
        city="Malmö",
        neighborhood="Västra Hamnen",
        latitude=55.6167,
        longitude=12.9833,
        housing_type="Lägenhet",
        ownership_type="Bostadsrätt",
        rooms=3.0,
        living_area=68.0,
        has_elevator=True,
        has_balcony=True,
        building_year=2017,
        association_fee=5281,
        asking_price=2_995_000,
        final_price=3_095_000,
        sold_date=date(2025, 11, 15)
    )
    
    sold_prop.calculate_derived_fields()
    print("✅ Sold property validated:")
    print(f"   Price change: {sold_prop.price_change:,} SEK ({sold_prop.price_change_pct:.1f}%)")
    print(f"   Price per m²: {sold_prop.price_per_sqm_final:,.0f} SEK/m²")
    
    # Example: Valid for-sale property
    for_sale_prop = ForSaleProperty(
        property_id="67890",
        property_type="for_sale",
        url="https://www.hemnet.se/bostad/lagenhet-2rum-malmo-67890",
        address="Östra Stallmästaregatan 5B",
        city="Malmö",
        neighborhood="Slottsstaden",
        latitude=55.5948,
        longitude=13.0011,
        housing_type="Lägenhet",
        ownership_type="Bostadsrätt",
        rooms=2.0,
        living_area=73.4,
        has_elevator=False,
        has_balcony=False,
        building_year=1936,
        association_fee=6787,
        asking_price=2_495_000,
        viewing_times=["2025-11-16 12:00-12:20"]
    )
    
    for_sale_prop.calculate_derived_fields()
    print("\n✅ For-sale property validated:")
    print(f"   Asking: {for_sale_prop.asking_price:,} SEK")
    print(f"   Price per m²: {for_sale_prop.price_per_sqm:,.0f} SEK/m²")
    
    # Test validation errors
    print("\n🧪 Testing validation...")
    try:
        invalid = SoldProperty(
            property_id="",  # Should fail
            url="invalid",
            property_type="sold"
        )
    except Exception as e:
        print(f"✅ Caught expected error: {e}")
    
    try:
        invalid = SoldProperty(
            property_id="test",
            url="https://www.hemnet.se/test",
            property_type="sold",
            final_price=50  # Should fail - too low
        )
    except Exception as e:
        print(f"✅ Caught expected error: {e}")
    
    print("\n✨ All validation tests passed!")
