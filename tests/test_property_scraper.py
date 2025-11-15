"""Tests for property scraper functionality."""

from src.scrapers.property_detail_scraper import PropertyScraper


class TestPropertyScraper:
    """Test PropertyScraper class."""
    
    def test_detect_property_type(self):
        """Test property type detection from URL."""
        scraper = PropertyScraper()
        
        # Test sold property
        sold_url = "https://www.hemnet.se/salda/lagenhet-3rum-malmo-test-123"
        assert scraper.detect_property_type(sold_url) == "sold"
        
        # Test for-sale property
        sale_url = "https://www.hemnet.se/bostad/lagenhet-2rum-malmo-test-456"
        assert scraper.detect_property_type(sale_url) == "for_sale"
        
        # Test invalid URL (should raise error)
        try:
            scraper.detect_property_type("https://www.hemnet.se/other/test")
            assert False, "Should have raised ValueError"
        except ValueError as e:
            assert "Unknown property type" in str(e)
    
    def test_extract_property_id(self):
        """Test property ID extraction from URL."""
        scraper = PropertyScraper()
        
        # Test typical URL
        url1 = "https://www.hemnet.se/bostad/lagenhet-2rum-malmo-test-21629409"
        assert scraper.extract_property_id(url1) == "21629409"
        
        # Test long ID
        url2 = "https://www.hemnet.se/salda/lagenhet-3rum-malmo-test-6303039936076543572"
        assert scraper.extract_property_id(url2) == "6303039936076543572"
    
    def test_extract_value_money(self):
        """Test extracting Money objects."""
        scraper = PropertyScraper()
        
        # Money object
        money_obj = {"__typename": "Money", "amount": 6787, "formatted": "6 787 kr"}
        assert scraper._extract_value(money_obj) == 6787
        
        # Direct value
        assert scraper._extract_value(5000) == 5000
        
        # None
        assert scraper._extract_value(None) is None
    
    def test_extract_value_housing_form(self):
        """Test extracting HousingForm objects."""
        scraper = PropertyScraper()
        
        # HousingForm with name
        form_obj = {"__typename": "HousingForm", "code": "APARTMENT", "name": "Lägenhet"}
        assert scraper._extract_value(form_obj) == "Lägenhet"
        
        # HousingForm without name (use code)
        form_obj2 = {"__typename": "HousingForm", "code": "APARTMENT"}
        assert scraper._extract_value(form_obj2) == "Apartment"
    
    def test_extract_value_tenure(self):
        """Test extracting Tenure objects."""
        scraper = PropertyScraper()
        
        # Tenure with name
        tenure_obj = {"__typename": "Tenure", "code": "TENANT_OWNERSHIP", "name": "Bostadsrätt"}
        assert scraper._extract_value(tenure_obj) == "Bostadsrätt"
        
        # Tenure without name (use code)
        tenure_obj2 = {"__typename": "Tenure", "code": "TENANT_OWNERSHIP"}
        assert scraper._extract_value(tenure_obj2) == "Tenant Ownership"


class TestIntegration:
    """Integration tests with real URLs (slow)."""
    
    def test_scrape_for_sale_property(self):
        """Test scraping a real for-sale property."""
        scraper = PropertyScraper(headless=True)
        url = "https://www.hemnet.se/bostad/lagenhet-2rum-slottsstaden-malmo-kommun-ostra-stallmastaregatan-5b-21629409"
        
        result = scraper.scrape_property(url)
        
        assert result is not None
        assert result.property_type == "for_sale"
        assert result.property_id == "21629409"
        assert result.address is not None
        assert result.latitude is not None
        assert result.longitude is not None
        assert result.asking_price is not None
        assert result.living_area is not None
    
    def test_scrape_sold_property(self):
        """Test scraping a real sold property."""
        scraper = PropertyScraper(headless=True)
        url = "https://www.hemnet.se/salda/lagenhet-3rum-vastra-hamnen-malmo-kommun-stormastgatan-5-6303039936076543572"
        
        result = scraper.scrape_property(url)
        
        assert result is not None
        assert result.property_type == "sold"
        assert result.property_id == "6303039936076543572"
        assert result.address is not None
        assert result.asking_price is not None
        assert result.final_price is not None
        assert result.sold_date is not None
