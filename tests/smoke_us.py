#!/usr/bin/env python3
"""Browser regression: U.S. and Canada must coexist in ONE Signal North page."""
import functools
import http.server
import threading
from pathlib import Path
from playwright.sync_api import sync_playwright

ROOT=Path(__file__).resolve().parents[1]
server=http.server.ThreadingHTTPServer(
 ("127.0.0.1",0),functools.partial(http.server.SimpleHTTPRequestHandler,directory=str(ROOT)))
threading.Thread(target=server.serve_forever,daemon=True).start()
url=f"http://127.0.0.1:{server.server_port}/index.html"
try:
 with sync_playwright() as p:
  browser=p.chromium.launch(headless=True,args=["--no-sandbox"])
  page=browser.new_page()
  errors=[]
  page.on("pageerror",lambda e:errors.append(str(e)))
  page.goto(url,wait_until="domcontentloaded",timeout=25000)
  page.wait_for_function("document.querySelectorAll('#metrics .metric').length===4",timeout=20000)
  page.wait_for_function("document.querySelector('#northInsight').textContent.includes('2025 FBI IC3')",timeout=20000)
  assert page.locator("#countryScope option").count()==3
  assert page.locator("#countryScope").input_value()=="all"
  assert page.locator("#mapMeasure option").count()==4
  assert "NORTH AMERICA" in page.locator("#countryLabel").inner_text().upper()
  assert page.locator(".sidebar > .nav").count()==5
  assert "Canada" in page.locator("#northInsight").inner_text() or "United States" in page.locator("#northInsight").inner_text()
  # There is no site / page handoff; each country updates the same map.
  page.locator("#countryScope").select_option("us")
  assert "UNITED STATES" in page.locator("#countryLabel").inner_text().upper()
  assert page.locator("#mapProvince option").count()==52
  assert "1,008,597" in page.locator("#metrics").inner_text()
  assert page.locator(".north-ca-scope").first.is_hidden()
  page.locator("#mapMeasure").select_option("ic3_rate")
  assert "FBI IC3" in page.locator("#mapCaption").inner_text()
  page.locator("#mapMeasure").select_option("ic3_loss")
  assert "reported USD losses" in page.locator("#mapCaption").inner_text()
  page.locator("#mapMeasure").select_option("records")
  page.locator("#mapProvince").select_option("US-AK")
  assert "Alaska" in page.locator("#mapCaption").inner_text()
  # Filter is truly unified: Canadian source records remain hidden in U.S. mode.
  assert "13" in page.locator("#metrics").inner_text()
  page.locator('[data-tab="events"]').first.click()
  assert page.locator("#northEnforcement .north-source-record").count()>=10
  assert page.locator("#eventRows").is_hidden()
  page.locator('#northEnforcement [data-northrecord]').first.click()
  assert "U.S. FEDERAL SOURCE" in page.locator("#drawerBody").inner_text()
  assert page.locator("#drawerBody a[href^='https://']").count()>=1
  page.locator("#close").click()
  page.locator('[data-tab="fraud"]').first.click()
  assert page.locator("#northReporting .north-source-record").count()>=10
  assert page.locator("#newsRows").is_hidden()
  page.locator("#northReportSearch").fill("Wise")
  assert page.locator("#northReportList .north-source-record").count()>=1
  page.locator("#northReportSearch").fill("")
  page.locator('[data-tab="themes"]').first.click()
  assert page.locator("#northTrends .north-bar").count()>=10
  page.locator('[data-tab="sources"]').first.click()
  assert "FBI IC3" in page.locator("#northSources").inner_text()
  assert "Reference only" in page.locator("#northSources").inner_text()
  page.locator("#countryScope").select_option("ca")
  assert page.locator("#mapProvince option").count()==11
  assert page.locator("#northSources").is_hidden()
  assert page.locator(".north-ca-scope").last.is_visible()
  page.locator("#countryScope").select_option("all")
  assert page.locator("#mapProvince option").count()==62
  page.locator('[data-tab="overview"]').first.click()
  assert page.locator("#metrics .metric").count()==4
  assert "111" in page.locator("#metrics").inner_text()
  assert page.locator("#northInsight").is_visible()
  assert page.locator("#mapStoryScope").count()==1
  assert not errors,errors
  browser.close()
  print("One unified Canada+US app, shared map, 51 states, filter, IC3, and research: PASS")
finally:
 server.shutdown()
