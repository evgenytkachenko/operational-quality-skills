"""Optional local UI check. Requires Playwright, a local Chromium, and local axe-core JS."""
import argparse,json
from pathlib import Path
from urllib.parse import urlparse
from playwright.sync_api import sync_playwright
p=argparse.ArgumentParser();p.add_argument('--url',default='http://127.0.0.1:8765');p.add_argument('--chromium',default='/usr/bin/chromium');p.add_argument('--axe',required=True);p.add_argument('--screenshots');a=p.parse_args()
u=urlparse(a.url)
assert u.scheme=='http' and u.hostname=='127.0.0.1' and u.username is None,'Loopback server only'
axe=Path(a.axe).read_text()
with sync_playwright() as pw:
 browser=pw.chromium.launch(headless=True,executable_path=a.chromium,args=['--no-sandbox'])
 context=browser.new_context(viewport={'width':1440,'height':1100})
 page=context.new_page();errors=[];requests=[];page.on('pageerror',lambda e:errors.append(str(e)));page.on('request',lambda r:requests.append((r.url,r.method)))
 page.goto(a.url);page.get_by_role('heading',name='REF-DEMO-001').wait_for()
 page.keyboard.press('Tab');assert page.evaluate('document.activeElement.textContent')=='Skip to workspace';page.keyboard.press('Enter');assert page.evaluate('document.activeElement.id')=='main'
 metrics=page.locator('#metrics').inner_text()
 page.get_by_role('button',name='REF-DEMO-003, Flagged, not reviewed',exact=True).click()
 assert page.evaluate('document.activeElement.id')=='detail-title'
 page.get_by_label('Confirm administrative gap').check();page.get_by_role('button',name='Record simulated review').click()
 assert 'No source system changed' in page.get_by_role('status').inner_text()
 assert page.locator('#metrics').inner_text()==metrics
 page.get_by_role('button',name='Missed · answer key',exact=True).click();assert page.locator('#case-list button').count()==1
 page.locator('#case-list button').click();assert page.get_by_role('heading',name='REF-DEMO-007').is_visible()
 page.get_by_text('Reveal synthetic answer key (not control input)',exact=True).click();assert page.get_by_text('The feed reported a matching receipt',exact=False).is_visible()
 page.get_by_role('button',name='Unknown',exact=True).click();page.locator('#case-list button').click();assert page.get_by_label('Confirm administrative gap').is_disabled()
 page.get_by_role('button',name='Reset simulation',exact=False).click()
 checks=[]
 for width,height,name in [(1440,1100,'desktop'),(390,844,'mobile'),(320,740,'narrow')]:
  page.set_viewport_size({'width':width,'height':height})
  for mode,nav in [('review','Review workspace'),('evaluation','Control evaluation')]:
   page.get_by_role('button',name=nav,exact=False).click()
   assert not page.evaluate('document.documentElement.scrollWidth>innerWidth'),(name,mode,'overflow')
   page.evaluate(axe)
   result=page.evaluate("async () => await axe.run(document,{runOnly:{type:'tag',values:['wcag2a','wcag2aa','wcag21aa']}})")
   issues=[{'id':v['id'],'impact':v['impact'],'targets':[n['target'] for n in v['nodes']]} for v in result['violations']]
   checks.append({'viewport':name,'view':mode,'violations':issues})
   if a.screenshots:
    d=Path(a.screenshots);d.mkdir(parents=True,exist_ok=True);page.screenshot(path=str(d/f'{name}-{mode}.png'),full_page=True)
 assert not errors,errors
 assert all(urlparse(url).hostname=='127.0.0.1' and method=='GET' for url,method in requests),requests
 page.reload();page.get_by_role('heading',name='REF-DEMO-001').wait_for();page.get_by_role('button',name='All',exact=True).click();page.get_by_role('button',name='REF-DEMO-003, Flagged, not reviewed',exact=True).wait_for()
 print(json.dumps({'browser_errors':errors,'accessibility':checks,'all_requests_loopback_get':True,'review_did_not_change_metrics':True,'refresh_restored_fixture':True},indent=2))
 assert not any(c['violations'] for c in checks),'Accessibility violations'
 browser.close()
