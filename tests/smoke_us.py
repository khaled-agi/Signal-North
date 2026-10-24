#!/usr/bin/env python3
"""Exercise the United States workspace in a real browser without network source fetching."""
import functools
import http.server
import threading
from pathlib import Path
from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[1]
server = http.server.ThreadingHTTPServer(
    ("127.0.0.1", 0), functools.partial(http.server.SimpleHTTPRequestHandler, directory=str(ROOT)))
threading.Thread(target=server.serve_forever, daemon=True).start()
base = f"http://127.0.0.1:{server.server_port}/"
try:
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True, args=["--no-sandbox"])
        page = browser.new_page()
        errors = []
        page.on("pageerror", lambda e: errors.append(str(e)))
        page.goto(base+"us.html", wait_until="domcontentloaded", timeout=25000)
        page.wait_for_function("document.querySelectorAll('#usMetrics .metric').length === 4",timeout=20000)
        assert not errors, errors
        assert page.locator("#usState option").count() == 52
        assert page.locator("#usMapMode option").count() == 4
        assert "1,008,597" in page.locator("#usMetrics").inner_text()
        assert "$20.88B" in page.locator("#usMetrics").inner_text()
        page.locator("#usMapMode").select_option("ic3_count")
        assert page.locator("#usMapMode").input_value()=="ic3_count"
        page.locator("#usMapMode").select_option("ic3_loss")
        assert page.locator("#usMapMode").input_value()=="ic3_loss"
        page.locator("#usMapMode").select_option("ic3_rate")
        assert page.locator('[data-usview="reporting"]').count() >= 1
        assert "FinCEN" in page.locator("#usLatest").inner_text() or "CFPB" in page.locator("#usLatest").inner_text()
        assert "United States" in page.title() or "U.S." in page.title()
        page.locator('button.nav[data-usview="reporting"]').click()
        page.wait_for_function("document.querySelectorAll('#usRows .us-record').length >= 10")
        page.locator("#usSearch").fill("Early Warning Services")
        assert page.locator("#usRows .us-record").count() == 1
        page.locator("#usRows .us-record [data-usrecord]").first.click()
        assert "Dismissed with prejudice" in page.locator("#usDrawerBody").inner_text()
        assert page.locator("#usDrawerBody a[href^='https://www.consumerfinance.gov/']").count() == 1
        page.locator("#usClose").click()
        page.locator("#usSearch").fill("")
        page.locator("#usState").select_option("AK")
        assert "3,202" in page.locator("#usMetrics").inner_text()
        assert "Only headlines explicitly naming Alaska" in page.locator("#usReportExplain").inner_text()
        assert page.locator("#usRows .us-record").count() == 0
        page.locator("#usState").select_option("DC")
        assert page.locator("#usRows .us-record").count() == 0
        page.locator("#usClear").click()
        assert page.locator("#usState").input_value() == ""
        assert page.locator("#usRows .us-record").count() >= 10
        page.locator("#usType").select_option("official")
        assert page.locator("#usRows .us-record").count() >= 10
        page.locator("button[data-usview='trends']").click()
        assert "FinCEN" in page.locator("#us-trends").inner_text()
        assert page.locator("#usOfficialTrend .us-chart-row").count() >= 3
        assert page.locator("#usIC3Trend .us-ic3-row").count() >= 10
        page.locator("button[data-usview='organizations']").click()
        assert page.locator("#usOrgRows .us-org-entry").count() >= 10
        page.locator("#usOrgSearch").fill("Block")
        assert page.locator("#usOrgRows .us-org-entry").count() >= 1
        page.locator("button[data-usview='sources']").click()
        assert "50 states + D.C." in page.locator("#usSourceHealth").inner_text()
        assert "REFERENCE ONLY" in page.locator("#usSourceDirectory").inner_text()
        assert "COLLECTION ENABLED" in page.locator("#usSourceDirectory").inner_text()
        assert "CURATED OFFICIAL DATA" in page.locator("#usSourceDirectory").inner_text()
        assert page.locator("#usSourceDirectory a[href*='ic3.gov']").count() == 1
        page.goto(base+"index.html", wait_until="domcontentloaded", timeout=20000)
        assert page.locator('.us-country-switch a[href="./us.html"]').count() == 1
        # External Leaflet failure must not make the U.S. evidence explorer fail.
        offline=browser.new_page()
        offline.route("**/leaflet@1.9.4/dist/leaflet.js",lambda route:route.abort())
        offline.goto(base+"us.html",wait_until="domcontentloaded",timeout=20000)
        offline.wait_for_function("document.querySelectorAll('#usMetrics .metric').length === 4",timeout=16000)
        assert "map library has not loaded" in offline.locator("#usMap").inner_text()
        offline.locator('button.nav[data-usview="reporting"]').click()
        assert offline.locator("#usRows .us-record").count() >= 10
        offline.close()
        assert not errors, errors
        print("US nationwide browser coverage, federal-only legal status, agency sourcing, map fallback: PASS")
        browser.close()
finally:
    server.shutdown()
