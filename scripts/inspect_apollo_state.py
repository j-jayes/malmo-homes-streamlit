"""Check what fields are available in Apollo State for a sold property."""

from playwright.sync_api import sync_playwright
import json
import re

url = 'https://www.hemnet.se/salda/lagenhet-2,5rum-folkets-park-malmo-kommun-trelleborgsgatan-8a-8937784767841466942'

print("Fetching page...")
with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    page = browser.new_page()
    page.goto(url, wait_until='domcontentloaded')
    page.wait_for_timeout(2000)
    html = page.content()
    browser.close()

# Extract NEXT_DATA
match = re.search(r'<script id="__NEXT_DATA__" type="application/json">(.*?)</script>', html, re.DOTALL)
if match:
    next_data = json.loads(match.group(1))
    apollo = next_data.get('props', {}).get('apolloState', {})
    
    # Find the property
    property_data = None
    for key, value in apollo.items():
        if 'SoldPropertyListing' in key:
            property_data = value
            print('\n' + '='*70)
            print('MAIN PROPERTY OBJECT')
            print('='*70)
            
            # Show all keys with references
            print('\nKeys with __ref (pointing to other objects):')
            for k in sorted(value.keys()):
                val = value[k]
                if isinstance(val, dict) and '__ref' in val:
                    print(f'  {k} -> {val["__ref"]}')
            
            print('\nDirect values:')
            for k in sorted(value.keys()):
                val = value[k]
                if not isinstance(val, dict):
                    if isinstance(val, str) and len(val) > 80:
                        print(f'  {k}: {val[:80]}...')
                    else:
                        print(f'  {k}: {val}')
            break
    
    if property_data:
        # Now follow the references to find attributes
        print('\n' + '='*70)
        print('FOLLOWING REFERENCES')
        print('='*70)
        
        # Check for attributes reference
        if 'attributes' in property_data and isinstance(property_data['attributes'], dict):
            ref = property_data['attributes'].get('__ref')
            if ref and ref in apollo:
                print(f'\n*** ATTRIBUTES OBJECT ({ref}): ***')
                attr_obj = apollo[ref]
                for k, v in attr_obj.items():
                    print(f'  {k}: {v}')
        
        # Check for housing reference
        if 'housing' in property_data and isinstance(property_data['housing'], dict):
            ref = property_data['housing'].get('__ref')
            if ref and ref in apollo:
                print(f'\n*** HOUSING OBJECT ({ref}): ***')
                housing_obj = apollo[ref]
                for k, v in housing_obj.items():
                    if isinstance(v, str) and len(v) > 80:
                        print(f'  {k}: {v[:80]}...')
                    else:
                        print(f'  {k}: {v}')
        
        # Look for any object with floor, constructionYear, etc
        print('\n' + '='*70)
        print('SEARCHING ALL APOLLO STATE FOR BUILDING INFO')
        print('='*70)
        
        keywords = ['floor', 'constructionYear', 'buildingYear', 'energyClass', 'description']
        for key, value in apollo.items():
            if isinstance(value, dict):
                for kw in keywords:
                    if kw in value and value[kw]:
                        print(f'\nFound in {key}:')
                        print(f'  {kw}: {value[kw]}')
