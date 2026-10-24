#!/usr/bin/env python3
"""Smoke-test Signal North in a real headless browser, with the committed data snapshot."""
import contextlib
import functools
import http.server
import json
import os
import threading
from pathlib import Path

from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[1]
EXPECTED = len(json.loads((ROOT / "data" / "events.json").read_text())["events"])
class Handler(http.server.SimpleHTTPRequestHandler):
    def log_message(self, *args):
        pass

server = http.server.ThreadingHTTPServer(
    ("127.0.0.1", 0), functools.partial(Handler, directory=str(ROOT))
)
thread = threading.Thread(target=server.serve_forever, daemon=True)
thread.start()
url = f"http://127.0.0.1:{server.server_port}/"

try:
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True, args=["--no-sandbox"])
        page = browser.new_page()
        errors = []
        resources = []
        page.on("pageerror", lambda e: errors.append(str(e)))
        page.on("response", lambda resp: resources.append(
            (resp.status, resp.url)) if "/data/events.json" in resp.url or resp.url.endswith("/app.js") else None)
        page.goto(url, wait_until="domcontentloaded", timeout=20000)
        try:
            page.wait_for_function("document.querySelectorAll('.metric').length === 4", timeout=20000)
        except Exception:
            print("BROWSER LOGS:", errors)
            print("RESOURCE RESPONSES:", resources)
            print("VISIBLE ERROR:", page.locator("#error").inner_text())
            print("BODY:", page.locator("body").inner_text()[:1800])
            raise
        actual = page.locator(".metric .value").nth(1).inner_text()
        print("Expected official notice count:", EXPECTED, "Dashboard official notice count:", actual)
        print("Network responses:", resources)
        print("Runtime errors:", errors)
        assert actual == str(EXPECTED), f"Expected {EXPECTED}, got {actual}"
        assert not errors, str(errors)
        page.locator("details.nav-datasets summary").click()
        page.locator('[data-tab="events"]').click()
        assert page.locator("#eventRows .event").count() == EXPECTED
        page.locator("#search").fill("RBC Unlikelyterm")
        assert page.locator("#eventRows .event").count() == 0
        page.locator('[data-tab="fraud"]').click()
        page.wait_for_function("document.querySelectorAll('#fraudNational .fraud-amount').length >= 2", timeout=10000)
        print("National fraud statistics:", page.locator("#fraudNational .fraud-amount").count())
        page.locator('[data-tab="losses"]').click()
        page.wait_for_function("document.querySelector('#lossYear').options.length > 0", timeout=10000)
        assert page.locator("#institutionLossRows").inner_text().strip()
        assert page.locator("#disclosedLossRows").inner_text().strip()
        print("Yearly penalties and disclosure explanation: PASS")
        page.locator('[data-tab="overview"]').click()
        page.wait_for_function("document.querySelectorAll('#featuredIncidents .case-item').length > 0", timeout=15000)
        assert page.locator("#majorOrders .event").count() > 0
        assert page.locator("#headlinesTop .breaking-story").count() > 0
        print("Featured reviewed incidents:", page.locator("#featuredIncidents .case-item").count())
        page.locator('[data-tab="incidents"]').click()
        page.wait_for_function("document.querySelectorAll('#incidentRows .case-item').length > 0", timeout=10000)
        assert page.locator("#incidentRows .case-item").count() >= 5
        page.locator("#incidentSearch").fill("Scotiabank")
        assert page.locator("#incidentRows .case-item").count() == 1
        page.locator('[data-tab="overview"]').click()
        page.locator('[data-mapmode="news"]').click()
        assert "mapped" in page.locator("#mapCaption").inner_text()
        assert page.locator("#mapProvince").count() == 1
        print("News, major orders, source-reviewed incidents, and map controls: PASS")
        page.wait_for_function("document.querySelectorAll('#mappedStories .map-story').length > 0", timeout=10000)
        assert page.locator("#mapMonth").count() == 1
        assert page.locator("#mapCoverage").inner_text().lower().find("indexed headlines") >= 0
        assert page.locator(".count-map-pin").count() > 0
        print("Geographic data coverage:", page.locator("#mapCoverage").inner_text())
        assert page.locator(".count-map-pin .count-pin-inner").first.inner_text().strip().isdigit()
        if page.locator("#mapStoryAll").is_visible():
            page.locator("#mapStoryAll").click()
            assert page.locator("#mappedStories .map-story").count() > 500
            print("All map-adjacent article titles are accessible: PASS")

        page.locator("#mapStoryScope").select_option("mapped")
        assert page.locator('#mappedStories button[data-mapfocus]').count() > 0
        page.locator("#mapStoryScope").select_option("all")
        page.locator("#mapMonth").fill("2026-03")
        assert "2026-03" in page.locator("#mapCaption").inner_text()
        page.locator("#mapClearMonth").click()
        page.locator('[data-tab="fraud"]').click()
        page.wait_for_function("document.querySelector('#newsYear').options.length > 1", timeout=15000)
        print("News archive count:", page.locator("#archiveCount").inner_text())
        if (ROOT / "data" / "news_archive.json").exists():
            archive = json.loads((ROOT / "data" / "news_archive.json").read_text())
            assert len(archive["leads"]) >= 300
            assert "historic discoveries" in page.locator("#archiveCount").inner_text()
            first_page = page.locator("#newsRows .news-item").count()
            assert first_page == 100, f"Expected paginated 100 stories, got {first_page}"
            page.locator("#newsMore").click()
            assert page.locator("#newsRows .news-item").count() == 200
            print("Historic archive pagination: PASS")
        if (ROOT / "data" / "article_index.json").exists():
            index = json.loads((ROOT / "data" / "article_index.json").read_text())
            assert index["unique_headlines"] == len(index["articles"])
            assert index["unique_headlines"] >= 500
            assert "unique indexed headlines" in page.locator("#archiveCount").inner_text()
            print("Unified multi-source article index:", index["unique_headlines"])


        if page.locator("#newsAll").is_visible():
            page.locator("#newsAll").click()
            assert page.locator("#newsRows .news-item").count() >= 200
            print("Full headline list: PASS")
        page.locator("#newsYear").select_option("2026")
        assert page.locator("#newsRows .news-item").count() > 0
        page.locator('[data-tab="clients"]').click()
        page.locator("#clientName").fill("Royal Bank of Canada")
        page.locator("#clientAdd").click()
        assert page.locator("#clientWatchlist .client-item").count() >= 1
        assert "Royal Bank of Canada" in page.locator("#clientWatchlist").inner_text()
        bg=page.evaluate("getComputedStyle(document.body).backgroundColor")
        assert bg in ("rgb(243, 246, 250)","rgb(255, 255, 255)","rgb(251, 252, 253)","rgb(245, 247, 248)"),f"Expected light theme, got {bg}"
        if (ROOT / "data" / "institution_intelligence.json").exists():
            page.locator('[data-tab="connections"]').click()
            page.wait_for_function("document.querySelectorAll('#connectInstitution option').length > 5", timeout=20000)
            page.locator("#connectSearch").fill("Royal Bank")
            page.locator("#connectInstitution").select_option("rbc")
            assert "Royal Bank of Canada" in page.locator("#connectContent").inner_text()
            assert page.locator("#connectContent .evidence-enforcement").count() > 0
            assert page.locator("#connectContent .evidence-incident").count() > 0
            assert page.locator("#reviewRows [data-review-status]").count() > 0
            page.locator("#reviewRows [data-review-status]").first.select_option("In review")
            assert page.locator("#reviewRows [data-review-status]").first.input_value() == "In review"
            with page.expect_download() as download_info:
                page.locator("#connectExport").click()
            download = download_info.value
            assert "rbc" in download.suggested_filename
            print("Source-linked research brief export: PASS")
            page.locator("#connectTrack").click()
            assert "Royal Bank of Canada" in page.locator("#clientWatchlist").inner_text()
            assert page.locator('#clientWatchlist button[data-open-connection]').count() > 0
            page.locator('[data-tab="connections"]').click()
            page.locator("#connectInstitution").select_option("rbc")
            page.locator("#connectMap").click()
            assert "Organization: Royal Bank of Canada" in page.locator("#mapCaption").inner_text()
            print("Institution graph, evidence provenance, triage, watchlist, alias-aware map: PASS")
        page.locator('[data-tab="reports"]').click()
        page.wait_for_function("document.querySelectorAll('#libraryRows .library-record').length >= 10", timeout=12000)
        assert page.locator("#lossTrend .loss-trend-row").count() >= 6
        page.locator("#librarySearch").fill("ombudsman")
        assert page.locator("#libraryRows .library-record").count() >= 1
        page.locator("#librarySearch").fill("")
        assert page.locator("#libraryCount").inner_text()
        page.locator('[data-tab="overview"]').click()
        assert page.locator(".sidebar > .nav").count() == 5
        assert page.locator("#metrics .metric").count() == 4
        page.locator('[data-tab="themes"]').click()
        page.wait_for_function("document.querySelectorAll('#themeGrid .theme-matrix-row').length >= 8", timeout=12000)
        assert page.locator("#themeYearCoverage > div").count() == 7
        page.locator("#themeChoose").select_option("Investment & crypto scams")
        assert "Investment & crypto" in page.locator("#themeExamplesTitle").inner_text()
        page.locator('[data-tab="sectors"]').click()
        page.wait_for_function("document.querySelectorAll('#sectorEntries .sector-item').length >= 10", timeout=12000)
        page.locator("#sectorSearch").fill("Wealthsimple")
        assert page.locator("#sectorEntries .sector-item").count() >= 2
        page.locator("#sectorSearch").fill("")
        page.locator("#sectorFilter").select_option("Casinos & gaming")
        assert page.locator("#sectorEntries .sector-item").count() >= 4
        page.locator('[data-tab="community"]').click()
        assert page.locator(".contribution-card").count() == 3
        assert "not anonymous" in page.locator("#community").inner_text().lower()
        assert page.locator('a[href*="template=public-source.yml"]').count() == 1
        page.locator('[data-tab="overview"]').click()
        assert page.locator('[data-tab="community"]').count() >= 1
        print("Themes, Wealthsimple, gaming, community safety and navigation: PASS")
        print("Research reports, CAFC historical trend, and simplified consultant workflow: PASS")
        print("Client watchlists, historical filters, linked map, light theme: PASS")
        # CDN failure may remove the basemap, but must not erase the archive.
        offline = browser.new_page()
        offline.route("**/leaflet@1.9.4/dist/leaflet.js", lambda route: route.abort())
        offline.goto(url, wait_until="domcontentloaded", timeout=20000)
        offline.wait_for_function("document.querySelector('#mapCoverage').textContent.includes('indexed headlines')", timeout=15000)
        assert offline.locator("#mappedStories .map-story").count() > 0
        assert "Map library unavailable" in offline.locator("#mapCaption").inner_text()
        offline.close()
        print("Map-CDN outage preserves the article archive: PASS")
        assert not errors, str(errors)
        print("Browser smoke test: PASS")
        browser.close()
finally:
    server.shutdown()
