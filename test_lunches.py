"""Non-destructive diagnostic for the two public Park Hill lunch menus."""
import json
from datetime import datetime, timezone
from pathlib import Path
from playwright.sync_api import sync_playwright

SCHOOLS = {
    'angeline_washington': 'https://www.schoolnutritionandfitness.com/webmenus2/#/view?id=6a70e8564bbb862699036825&menuType=653bdc6ae96f1eea2394a6d8&siteCode=27634&siteCode2=94254&showAllNutrients=false',
    'walden_middle': 'https://www.schoolnutritionandfitness.com/webmenus2/#/view?id=6a70eee4743691263712ccdc&menuType=653bdc88e96f1e862894a3e8&siteCode=27635&siteCode2=88799&showAllNutrients=false',
}

out = {'checked_at': datetime.now(timezone.utc).isoformat(), 'schools': {}}
Path('lunch-diagnostics').mkdir(exist_ok=True)
with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    for name, url in SCHOOLS.items():
        record = {'source_url': url, 'status': 'not_verified'}
        try:
            page = browser.new_page(viewport={'width': 1280, 'height': 900}, device_scale_factor=1)
            response = page.goto(url, wait_until='domcontentloaded', timeout=45000)
            page.wait_for_timeout(12000)
            record['http_status'] = response.status if response else None
            record['page_title'] = page.title()
            text = page.locator('body').inner_text(timeout=10000)
            record['visible_text_excerpt'] = text[:8000]
            record['page_images'] = page.locator('img').count()
            record['iframes'] = page.locator('iframe').count()
            record['status'] = 'page_loaded' if len(text.strip()) > 50 else 'page_empty'
            page.screenshot(path=f'lunch-diagnostics/{name}.png', full_page=True)
            page.close()
        except Exception as exc:
            record['status'] = 'error'
            record['error'] = str(exc)[:800]
        out['schools'][name] = record
Path('lunch-diagnostics/report.json').write_text(json.dumps(out, indent=2), encoding='utf-8')
print(json.dumps(out, indent=2))
