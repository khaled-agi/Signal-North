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
        actual = page.locator(".metric .value").first.inner_text()
        print("Expected event count:", EXPECTED, "Dashboard count:", actual)
        print("Network responses:", resources)
        print("Runtime errors:", errors)
        assert actual == str(EXPECTED), f"Expected {EXPECTED}, got {actual}"
        assert not errors, str(errors)
        page.locator('[data-tab="events"]').click()
        assert page.locator("#eventRows .event").count() == EXPECTED
        page.locator("#search").fill("RBC Unlikelyterm")
        assert page.locator("#eventRows .event").count() == 0
        print("Browser smoke test: PASS")
        browser.close()
finally:
    server.shutdown()
