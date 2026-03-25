from src.scrapers.property_detail_scraper import PropertyScraper


def test_extract_value_money_falls_back_to_formatted_amount() -> None:
    scraper = PropertyScraper(headless=True)
    value = scraper._extract_value({"__typename": "Money", "amount": None, "formatted": "6 787 000 kr"})
    assert value == 6787000


def test_extract_value_money_parses_string_amount() -> None:
    scraper = PropertyScraper(headless=True)
    value = scraper._extract_value({"__typename": "Money", "amount": "2 995 000", "formatted": "2 995 000 kr"})
    assert value == 2995000


def test_extract_value_money_normalizes_ksek_amounts() -> None:
    scraper = PropertyScraper(headless=True)
    value = scraper._extract_value({"__typename": "Money", "amount": 900, "formatted": "900 tkr"})
    assert value == 900000


def test_extract_value_money_normalizes_ksek_string_digits() -> None:
    scraper = PropertyScraper(headless=True)
    value = scraper._extract_value({"__typename": "Money", "amount": None, "formatted": "13 455"})
    assert value == 13455000
