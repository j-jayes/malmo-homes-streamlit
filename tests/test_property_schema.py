"""Tests for property data models."""

import pytest
from datetime import date, datetime
from pydantic import ValidationError
from src.models.property_schema import BaseProperty, SoldProperty, ForSaleProperty


class TestBaseProperty:
    """Test BaseProperty validation."""
    
    def test_valid_property(self):
        """Test creating a valid base property."""
        data = {
            "property_id": "12345",
            "property_type": "for_sale",
            "url": "https://www.hemnet.se/bostad/test",
            "address": "Test Street 1",
            "latitude": 55.6,
            "longitude": 13.0,
            "housing_type": "Lägenhet",
            "ownership_type": "Bostadsrätt",
            "rooms": 2.0,
            "living_area": 75.0,
            "association_fee": 5000,
        }
        
        prop = BaseProperty(**data)
        assert prop.property_id == "12345"
        assert prop.rooms == 2.0
        assert prop.living_area == 75.0
    
    def test_price_validation(self):
        """Test price must be within valid range."""
        data = {
            "property_id": "12345",
            "property_type": "for_sale",
            "url": "https://www.hemnet.se/bostad/test",
            "address": "Test Street 1",
            "latitude": 55.6,
            "longitude": 13.0,
            "housing_type": "Lägenhet",
            "ownership_type": "Bostadsrätt",
            "rooms": 2.0,
            "living_area": 75.0,
            "association_fee": 5000,
        }
        
        # Valid price
        prop = BaseProperty(**data)
        assert prop.association_fee == 5000
        
        # Invalid: negative association fee
        with pytest.raises(ValidationError):
            BaseProperty(**{**data, "association_fee": -100})
    
    def test_coordinate_validation(self):
        """Test coordinate validation."""
        data = {
            "property_id": "12345",
            "property_type": "for_sale",
            "url": "https://www.hemnet.se/bostad/test",
            "address": "Test Street 1",
            "housing_type": "Lägenhet",
            "ownership_type": "Bostadsrätt",
            "rooms": 2.0,
            "living_area": 75.0,
        }
        
        # Valid coordinates
        prop = BaseProperty(**{**data, "latitude": 55.6, "longitude": 13.0})
        assert prop.latitude == 55.6
        assert prop.longitude == 13.0
        
        # Invalid latitude
        with pytest.raises(ValidationError):
            BaseProperty(**{**data, "latitude": 100.0, "longitude": 13.0})
        
        # Invalid longitude
        with pytest.raises(ValidationError):
            BaseProperty(**{**data, "latitude": 55.6, "longitude": 200.0})
    
    def test_area_validation(self):
        """Test area must be positive."""
        data = {
            "property_id": "12345",
            "property_type": "for_sale",
            "url": "https://www.hemnet.se/bostad/test",
            "address": "Test Street 1",
            "latitude": 55.6,
            "longitude": 13.0,
            "housing_type": "Lägenhet",
            "ownership_type": "Bostadsrätt",
            "rooms": 2.0,
        }
        
        # Valid area
        prop = BaseProperty(**{**data, "living_area": 75.0})
        assert prop.living_area == 75.0
        
        # Invalid: negative area
        with pytest.raises(ValidationError):
            BaseProperty(**{**data, "living_area": -10.0})
        
        # Invalid: zero area
        with pytest.raises(ValidationError):
            BaseProperty(**{**data, "living_area": 0.0})


class TestSoldProperty:
    """Test SoldProperty model."""
    
    def test_valid_sold_property(self):
        """Test creating a valid sold property."""
        data = {
            "property_id": "12345",
            "property_type": "sold",
            "url": "https://www.hemnet.se/salda/test",
            "address": "Test Street 1",
            "latitude": 55.6,
            "longitude": 13.0,
            "housing_type": "Lägenhet",
            "ownership_type": "Bostadsrätt",
            "rooms": 2.0,
            "living_area": 75.0,
            "asking_price": 2_500_000,
            "final_price": 2_600_000,
            "sold_date": date(2025, 1, 15),
        }
        
        prop = SoldProperty(**data)
        assert prop.asking_price == 2_500_000
        assert prop.final_price == 2_600_000
        assert prop.sold_date == date(2025, 1, 15)
    
    def test_calculate_derived_fields(self):
        """Test automatic calculation of derived fields."""
        data = {
            "property_id": "12345",
            "property_type": "sold",
            "url": "https://www.hemnet.se/salda/test",
            "address": "Test Street 1",
            "latitude": 55.6,
            "longitude": 13.0,
            "housing_type": "Lägenhet",
            "ownership_type": "Bostadsrätt",
            "rooms": 2.0,
            "living_area": 80.0,
            "asking_price": 2_400_000,
            "final_price": 2_500_000,
            "sold_date": date(2025, 1, 15),
        }
        
        prop = SoldProperty(**data)
        prop.calculate_derived_fields()
        
        # Price change
        assert prop.price_change == 100_000
        assert abs(prop.price_change_pct - 4.167) < 0.01
        
        # Price per sqm
        assert prop.price_per_sqm_final == 2_500_000 / 80.0


class TestForSaleProperty:
    """Test ForSaleProperty model."""
    
    def test_valid_for_sale_property(self):
        """Test creating a valid for-sale property."""
        data = {
            "property_id": "12345",
            "property_type": "for_sale",
            "url": "https://www.hemnet.se/bostad/test",
            "address": "Test Street 1",
            "latitude": 55.6,
            "longitude": 13.0,
            "housing_type": "Lägenhet",
            "ownership_type": "Bostadsrätt",
            "rooms": 2.0,
            "living_area": 75.0,
            "asking_price": 2_500_000,
            "listed_date": date(2025, 1, 1),
        }
        
        prop = ForSaleProperty(**data)
        assert prop.asking_price == 2_500_000
        assert prop.listed_date == date(2025, 1, 1)
    
    def test_calculate_derived_fields(self):
        """Test automatic calculation of price per sqm."""
        data = {
            "property_id": "12345",
            "property_type": "for_sale",
            "url": "https://www.hemnet.se/bostad/test",
            "address": "Test Street 1",
            "latitude": 55.6,
            "longitude": 13.0,
            "housing_type": "Lägenhet",
            "ownership_type": "Bostadsrätt",
            "rooms": 2.0,
            "living_area": 80.0,
            "asking_price": 2_400_000,
        }
        
        prop = ForSaleProperty(**data)
        prop.calculate_derived_fields()
        
        # Price per sqm
        assert prop.price_per_sqm == 2_400_000 / 80.0
    
    def test_viewing_times(self):
        """Test viewing times list."""
        data = {
            "property_id": "12345",
            "property_type": "for_sale",
            "url": "https://www.hemnet.se/bostad/test",
            "address": "Test Street 1",
            "latitude": 55.6,
            "longitude": 13.0,
            "housing_type": "Lägenhet",
            "ownership_type": "Bostadsrätt",
            "rooms": 2.0,
            "living_area": 75.0,
            "asking_price": 2_500_000,
            "viewing_times": [
                "2025-01-20 14:00-15:00",
                "2025-01-22 18:00-19:00"
            ]
        }
        
        prop = ForSaleProperty(**data)
        assert len(prop.viewing_times) == 2
        assert "14:00" in prop.viewing_times[0]
