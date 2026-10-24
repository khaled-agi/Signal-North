#!/usr/bin/env python3
"""Collect regulator-published Canadian enforcement events for Signal North.

Primary regulator sources only. No unverified news articles are auto-published.
Record locations refer to explicitly stated institution locations, not incident sites.
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup
from dateutil import parser as date_parser

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
EVENT_FILE = DATA / "events.json"
STATUS_FILE = DATA / "status.json"

SOURCES = {
    "FINTRAC": "https://fintrac-canafe.canada.ca/pen/4-eng",
    "FCAC": "https://www.canada.ca/en/financial-consumer-agency/services/industry/commissioner-decisions.html",
}
CITIES = {
    ("Toronto", "Ontario"): (43.6532, -79.3832),
    ("Kitchener", "Ontario"): (43.4516, -80.4925),
    ("North Bay", "Ontario"): (46.3091, -79.4608),
    ("Lloydminster", "Saskatchewan"): (53.2784, -110.0050),
    ("Kamloops", "British Columbia"): (50.6745, -120.3273),
    ("Richmond", "British Columbia"): (49.1666, -123.1336),
    ("Glenevis", "Alberta"): (53.8004, -114.6128),
    ("Ottawa", "Ontario"): (45.4215, -75.6972),
    ("Oshawa", "Ontario"): (43.8971, -78.8658),
    ("London", "Ontario"): (42.9849, -81.2453),
    ("Mississauga", "Ontario"): (43.5890, -79.6441),
    ("Montreal", "Quebec"): (45.5019, -73.5674),
    ("Montréal", "Québec"): (45.5019, -73.5674),
    ("Quebec City", "Quebec"): (46.8139, -71.2080),
    ("Vancouver", "British Columbia"): (49.2827, -123.1207),
    ("Calgary", "Alberta"): (51.0447, -114.0719),
    ("Edmonton", "Alberta"): (53.5461, -113.4938),
    ("Winnipeg", "Manitoba"): (49.8951, -97.1384),
    ("Halifax", "Nova Scotia"): (44.6488, -63.5752),
    ("Regina", "Saskatchewan"): (50.4452, -104.6189),
    ("Saskatoon", "Saskatchewan"): (52.1332, -106.6700),
    ("Fredericton", "New Brunswick"): (45.9636, -66.6431),
    ("Moncton", "New Brunswick"): (46.0878, -64.7782),
    ("Caraquet", "New Brunswick"): (47.7925, -64.9386),
    ("St. John's", "Newfoundland and Labrador"): (47.5615, -52.7126),
    ("Charlottetown", "Prince Edward Island"): (46.2382, -63.1311),
}
PROVINCE_CODES = {
    "Ontario": "ON", "Quebec": "QC", "Québec": "QC",
    "British Columbia": "BC", "Alberta": "AB", "Manitoba": "MB",
    "New Brunswick": "NB", "Nova Scotia": "NS", "Saskatchewan": "SK",
    "Newfoundland and Labrador": "NL", "Prince Edward Island": "PE",
}
HEADERS = {
    "User-Agent": os.environ.get(
        "TRACKER_USER_AGENT",
        "SignalNorthResearch/0.1 (public source research; https://github.com/khaled-agi/Signal-North)",
    ),
    "Accept": "text/html,application/xhtml+xml",
}


def now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def date_string(raw: str) -> str | None:
    try:
        return date_parser.parse(raw, fuzzy=True).date().isoformat()
    except (TypeError, ValueError, OverflowError):
        return None


def clean(s: str) -> str:
    return re.sub(r"\s+", " ", s).strip()


def amount(raw: str) -> float | None:
    m = re.search(r"\$\s*([\d,]+(?:\.\d+)?)\s*(million|billion|thousand)?", raw, re.I)
    if not m:
        return None
    multiplier = {"million": 1_000_000, "billion": 1_000_000_000,
                  "thousand": 1_000}.get((m.group(2) or "").lower(), 1)
    return float(m.group(1).replace(",", "")) * multiplier


def supported_location(text: str) -> dict:
    # Only mark the location if an actual city/province pair occurs in the
    # institution-location clause. Do not map a regulator's own office.
    clause = re.search(
        r"(?:headquartered|based|located|operating)\s+in\s+([^.]{0,100})",
        text, flags=re.I,
    )
    if not clause:
        return {}
    snippet = clause.group(1)
    for (city, province), (lat, lon) in CITIES.items():
        if re.search(r"\b" + re.escape(city) + r"\s*,?\s*" + re.escape(province) + r"\b",
                     snippet, re.I):
            return {"location": city + ", " + province, "province": PROVINCE_CODES[province],
                    "latitude": lat, "longitude": lon, "location_role": "reported institution location"}
    return {}


def make(source: str, url: str, name: str, heading: str, summary: str,
         published: str | None, status: str, fine: float | None,
         action: str | None = None, location_text: str = "", event_id: str = "") -> dict:
    key = source + "|" + (event_id or url)
    record = {
        "id": hashlib.sha256(key.encode("utf-8")).hexdigest()[:20],
        "source": source,
        "source_url": url,
        "institution": name,
        "title": heading,
        "summary": summary[:1600],
        "published_at": published,
        "event_at": action,
        "category": "AML enforcement" if source == "FINTRAC" else "Consumer protection enforcement",
        "status": status,
        "role": "subject_of_enforcement",
        "penalty_cad": fine,
        "evidence_level": "primary regulator",
        "last_observed_at": now(),
    }
    record.update(supported_location(location_text))
    return record


def fetch(url: str) -> str:
    r = requests.get(url, headers=HEADERS, timeout=35)
    r.raise_for_status()
    return r.text


def fintrac(html: str) -> list[dict]:
    soup = BeautifulSoup(html, "html.parser")
    items = []
    for row in soup.select("tr"):
        cells = row.find_all("td", recursive=False)
        if len(cells) < 2:
            continue
        date = date_string(cells[0].get_text(" ", strip=True))
        body = clean(cells[1].get_text(" ", strip=True))
        if not date or "administrative monetary penalty" not in body.lower():
            continue
        link = cells[1].find("a", href=True)
        if not link:
            continue
        name = clean(link.get_text(" ", strip=True))
        if len(name) < 2:
            continue
        url = urljoin(SOURCES["FINTRAC"], link["href"])
        fine_match = re.search(r"(?:administrative monetary penalty of|penalty of)\s*(\$\s*[\d,.]+)", body, re.I)
        fine = amount(fine_match.group(1)) if fine_match else None
        low = body.lower()
        status = "penalty appealed" if "appealed" in low else (
            "penalty paid" if "paid" in low else "penalty imposed"
        )
        items.append(make("FINTRAC", url, name, name + ": FINTRAC administrative monetary penalty",
                          body, date, status, fine, location_text=body))
    return items


def fcac(html: str) -> list[dict]:
    soup = BeautifulSoup(html, "html.parser")
    main = soup.find("main") or soup
    text = clean(main.get_text(" ", strip=True))
    chunks = re.split(r"(?=Summary of proceeding\s*#\d+\b)", text, flags=re.I)
    items = []
    for part in chunks:
        proc = re.match(r"Summary of proceeding\s*#(\d+)\b", part, re.I)
        if not proc:
            continue
        post = re.search(r"Posted on\s+([A-Z][a-z]+\s+\d{1,2},\s+\d{4})", part)
        pay = re.search(r"On\s+([A-Z][a-z]+\s+\d{1,2},\s+\d{4}),?\s+(?:the\s+)?(.+?)\s+paid\s+(?:a\s+|the\s+)?(\$\s*[\d,.]+\s*(?:million|billion|thousand|[mMbBkK])?)\s+penalty", part)
        if not post or not pay:
            continue
        name = clean(pay.group(2))
        if not name or len(name) > 120:
            continue
        num = proc.group(1)
        link = next((a for a in main.find_all("a", href=True)
                     if re.fullmatch(r"Summary of proceeding\s*#" + num, clean(a.get_text(" ", strip=True)), re.I)), None)
        url = urljoin(SOURCES["FCAC"], link["href"]) if link else SOURCES["FCAC"]
        items.append(make("FCAC", url, name, name + ": FCAC proceeding #" + num,
                          part[:1600], date_string(post.group(1)), "penalty paid", amount(pay.group(3)),
                          action=date_string(pay.group(1)), event_id="proceeding:" + num))
    return items


def run() -> int:
    DATA.mkdir(exist_ok=True, parents=True)
    existing = []
    if EVENT_FILE.exists():
        try:
            loaded = json.loads(EVENT_FILE.read_text(encoding="utf-8"))
            existing = loaded["events"] if isinstance(loaded, dict) else loaded
        except (ValueError, KeyError) as exc:
            print("Existing history corrupted; refusing to overwrite: " + str(exc), file=sys.stderr)
            return 1
    by_id = {item["id"]: item for item in existing}
    status = {"last_attempt_at": now(), "sources": {}, "previous_records": len(by_id)}
    successful = 0
    for name, parse in (("FINTRAC", fintrac), ("FCAC", fcac)):
        try:
            entries = parse(fetch(SOURCES[name]))
            # An empty parse may indicate a changed regulator page. Don't delete history.
            status["sources"][name] = {"status": "ok" if entries else "empty_parse",
                                        "scanned": len(entries), "url": SOURCES[name]}
            if entries:
                successful += 1
            for event in entries:
                old = by_id.get(event["id"], {})
                event["first_seen_at"] = old.get("first_seen_at", now())
                by_id[event["id"]] = event
        except Exception as exc:
            status["sources"][name] = {"status": "failed", "error": str(exc)[:300],
                                        "url": SOURCES[name]}
    records = sorted(by_id.values(), key=lambda e: (e.get("published_at") or "", e["id"]), reverse=True)
    status["stored_records"] = len(records)
    status["last_completed_at"] = now()
    EVENT_FILE.write_text(json.dumps({"events": records, "updated_at": now()},
                                      ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    STATUS_FILE.write_text(json.dumps(status, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(status, indent=2))
    # Fail the action only when all sources fail AND no retained data.
    return 1 if not successful and not records else 0


if __name__ == "__main__":
    raise SystemExit(run())
