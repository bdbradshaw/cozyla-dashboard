
"""Inspect publicly accessible menu viewer without changing dashboard or school data."""
import json, re
from datetime import datetime, timezone
from pathlib import Path
from playwright.sync_api import sync_playwright

SCHOOLS = {
 'angeline_washington': 'https://www.schoolnutritionandfitness.com/webmenus2/#/view?id=6a70e8564bbb862699036825&menuType=653bdc6ae96f1eea2394a6d8&siteCode=27634&siteCode2=94254&showAllNutrients=false',
 'walden_middle': 'https://www.schoolnutritionandfitness.com/webmenus2/#/view?id=6a70eee4743691263712ccdc&menuType=653bdc88e96f1e862894a3e8&siteCode=27635&siteCode2=88799&showAllNutrients=false',
}
OUT=Path('lunch-diagnostics');OUT.mkdir(exist_ok=True)
report={'checked_at':datetime.now(timezone.utc).isoformat(),'schools':{}}
with sync_playwright() as p:
 browser=p.chromium.launch(headless=True)
 for name,url in SCHOOLS.items():
  page=browser.new_page(viewport={'width':1365,'height':1000},accept_downloads=False)
  record={'source_url':url,'status':'not_verified','network':[],'frames':[],'clicks':[]}
  def on_response(response):
   try:
    ct=response.headers.get('content-type','')
    if ('json' in ct or '/api/' in response.url) and len(record['network'])<70:
     item={'url':response.url[:500],'status':response.status,'content_type':ct}
     if 'json' in ct:
      try:
       payload=response.json(); raw=json.dumps(payload,ensure_ascii=False)
       item['body_excerpt']=raw[:3000];item['body_length']=len(raw)
      except Exception as e:item['parse_error']=str(e)[:100]
     record['network'].append(item)
   except Exception:pass
  page.on('response',on_response)
  try:
   r=page.goto(url,wait_until='domcontentloaded',timeout=45000)
   page.wait_for_timeout(9000)
   record['http_status']=r.status if r else None
   record['page_title']=page.title()
   record['initial_text']=page.locator('body').inner_text(timeout=10000)[:9000]
   page.screenshot(path=str(OUT/f'{name}-before.png'),full_page=True)
   patterns=[r'I Agree',r'I Accept',r'Accept',r'Acknowledge',r'Continue',r'OK',r'Got it',r'Close']
   for pattern in patterns:
    for frame in page.frames:
     try:
      buttons=frame.get_by_role('button',name=re.compile(pattern,re.I))
      if buttons.count() and buttons.first.is_visible():
       buttons.first.click(timeout=3000);record['clicks'].append(pattern);page.wait_for_timeout(2000)
     except Exception:pass
   page.wait_for_timeout(5000)
   record['after_text']=page.locator('body').inner_text(timeout=10000)[:18000]
   for frame in page.frames:
    try:record['frames'].append({'url':frame.url[:500],'text':frame.locator('body').inner_text(timeout=5000)[:18000]})
    except Exception as e:record['frames'].append({'url':frame.url[:500],'error':str(e)[:200]})
   page.screenshot(path=str(OUT/f'{name}-after.png'),full_page=True)
   record['status']='captured'
  except Exception as e:record['status']='error';record['error']=str(e)[:800]
  finally:page.close()
  report['schools'][name]=record
 browser.close()
(OUT/'report.json').write_text(json.dumps(report,indent=2,ensure_ascii=False),encoding='utf-8')
print(json.dumps({k:{'status':v['status'],'clicks':v['clicks'],'network_responses':len(v['network']),'frames':len(v['frames'])} for k,v in report['schools'].items()},indent=2))
