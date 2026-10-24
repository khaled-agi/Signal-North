#!/usr/bin/env python3
"""Test the actual public GitHub Pages site after deployment."""
import os
import sys
from playwright.sync_api import sync_playwright

TARGET = os.environ.get("SIGNAL_NORTH_URL", "https://khaled-agi.github.io/Signal-North/")
with sync_playwright() as p:
    browser = p.chromium.launch(headless=True, args=["--no-sandbox"])
    page = browser.new_page()
    failures, responses = [], []
    page.on("pageerror", lambda err: failures.append("JS: " + str(err)))
    page.on("console", lambda msg: failures.append("CONSOLE: " + msg.text) if msg.type == "error" else None)
    page.on("response", lambda r: responses.append({
        "status": r.status, "url": r.url,
        "cache": r.headers.get("cache-control", ""),
        "etag": r.headers.get("etag", ""),
    }) if ("app.js" in r.url or "events.json" in r.url or "status.json" in r.url or r.url.rstrip("/") == TARGET.rstrip("/")) else None)
    try:
        response = page.goto(TARGET + "?github_pages_probe=20261024", wait_until="domcontentloaded", timeout=30000)
        print("Page:", response.status if response else None, page.url)
        try:
            page.wait_for_function("document.querySelectorAll('.metric').length === 4", timeout=18000)
        except Exception as e:
            print("Dashboard bootstrap failed:", e)
        print("Browser JS errors:", failures)
        print("HTTP response details:", responses)
        print("Dashboard heading:", page.locator("#updated").inner_text())
        print("Metric count:", page.locator(".metric").count())
        print("Event cards:", page.locator("#recent .event").count())
        print("Mapped caption:", page.locator("#mapCaption").inner_text())
        print("Browser app.js resource:", page.evaluate("""() => Array.from(document.scripts).map(x => x.src)"""))
        if page.locator(".metric").count() != 4 or failures:
            sys.exit(1)
        print("PUBLIC SITE SMOKE TEST: PASS")
    finally:
        browser.close()
