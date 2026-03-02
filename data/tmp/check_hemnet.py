from playwright.sync_api import sync_playwright
import time

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    page = browser.new_page()
    page.goto("https://www.hemnet.se/salda/bostader?item_types[]=bostadsratt&living_area_min=80&living_area_max=81&sold_age=1m")
    time.sleep(2)
    print(page.title())
    try:
        text = page.locator('text=/Visar .* av/').first.inner_text()
        print(text)
    except:
        print("Not found")
    browser.close()
