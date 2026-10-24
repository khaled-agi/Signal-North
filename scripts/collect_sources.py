#!/usr/bin/env python3
"""Supplement Signal North's Google News discovery with independent source feeds.

This collector stores metadata only. It does not scrape or republish article bodies,
claim to verify allegations, or infer financial institution culpability.
Sources:
  * RCMP official news RSS (financial-crime relevance screened)
  * GDELT DOC 2.0 article discovery (Canadian-publisher news in EN/FR)
"""
from __future__ import annotations

import hashlib
import json
import re
import sys
import time
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from pathlib import Path
from urllib.parse import urlparse

import requests
from collect_news import (
    normalize, classify, headline_location, headline_claims, relevant,
)

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
FEED = DATA / "news.json"
HEALTH = DATA / "external_source_status.json"
RCMP_URLS = {
    "RCMP national news": "https://rcmp.ca/en/feed-flux/news-nouvelles",
    "RCMP British Columbia": "https://rcmp.ca/en/feed-flux/news-nouvelles/division/e",
    "RCMP Alberta": "https://rcmp.ca/en/feed-flux/news-nouvelles/division/k",
    "RCMP Manitoba": "https://rcmp.ca/en/feed-flux/news-nouvelles/division/d",
    "RCMP Saskatchewan": "https://rcmp.ca/en/feed-flux/news-nouvelles/division/f",
    "RCMP Nova Scotia": "https://rcmp.ca/en/feed-flux/news-nouvelles/division/h",
    "RCMP New Brunswick": "https://rcmp.ca/en/feed-flux/news-nouvelles/division/j",
    "RCMP Federal Central": "https://rcmp.ca/en/feed-flux/news-nouvelles/region/central",
}
GDELT_URL = "https://api.gdeltproject.org/api/v2/doc/doc"
# Conservative, narrowly targeted query slices to reduce irrelevant stories.
GDELT_QUERIES = {
    "Canadian banking fraud": '"bank fraud" sourcecountry:Canada',
    "Canadian scam cases": 'scam sourcecountry:Canada',
    "Money laundering": '"money laundering" sourcecountry:Canada',
    "French fraud coverage": 'fraude sourcecountry:Canada sourcelang:French',
}
CRIME = re.compile(
    r"\b(?:fraud|fraude|fraudulent|scam|arnaque|escroquerie|"
    r"money laundering|blanchiment|phishing|identity theft|"
    r"usurpation|financial exploitation|cyberfraud|ransomware|"
    r"business email compromise|investment scheme|money mule|"
    r"romance scam|financial crime)\b", re.I,
)
HEADERS = {
    "User-Agent": "SignalNorthResearch/0.4 (public metadata discovery; https://github.com/khaled-agi/Signal-North)",
    "Accept": "application/rss+xml,application/xml,application/json,*/*",
}

def stamp():
    return datetime.now(timezone.utc).isoformat(timespec="seconds")

def parse_rcmp_date(value):
    try:
        dt = parsedate_to_datetime(value)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(timezone.utc).isoformat(timespec="seconds")
    except (ValueError, TypeError, OverflowError):
        return None

def parse_gdelt_date(value):
    # GDELT seendate is *first observed by GDELT*, not confirmed publisher date.
    try:
        return datetime.strptime(str(value), "%Y%m%dT%H%M%SZ").replace(tzinfo=timezone.utc).isoformat(timespec="seconds")
    except (ValueError, TypeError):
        return None

def normalize_title(title):
    return re.sub(r"\s+", " ", title).strip()

def record(title, url, publisher, date_seen, channel, topic, **extra):
    title = normalize_title(title)
    if not title or not url.startswith("https://") or not CRIME.search(title):
        return None
    # Stable across repeated retrieval by channel; article-index stage combines providers.
    key = hashlib.sha256((publisher.casefold()+"|"+title.casefold()).encode()).hexdigest()[:20]
    coords = headline_location(title)
    return {
        "id": key,
        "title": title,
        "url": url,
        "publisher": publisher,
        "published_at": date_seen,
        "date_basis": extra.get("date_basis","reported_feed_publication"),
        "topics": [topic],
        "category": classify(title),
        "evidence_status": "unverified_news_lead",
        "discovery_source": channel,
        "institution": None,
        "reported_loss": None,
        "content_kind": "news_lead",
        "geographic_accuracy": "headline_only" if coords else "not_geocoded",
        **headline_claims(title),
        **coords,
        "first_seen_at": stamp(),
        "last_observed_at": stamp(),
        "notice": "Article metadata / headline discovery only. Any mentioned bank, sum or location is not independently corroborated.",
    }

def fetch_rcmp(session, url):
    response = session.get(url, timeout=35)
    response.raise_for_status()
    root = ET.fromstring(response.content)
    atom = "{http://www.w3.org/2005/Atom}"
    rows = root.findall(".//channel/item")
    is_atom = not rows
    if is_atom:
        rows = root.findall(".//"+atom+"entry")
    accepted = []
    for item in rows[:200]:
        if is_atom:
            title = normalize(item.findtext(atom+"title"))
            link_tag = item.find(atom+"link")
            link = normalize(link_tag.get("href","") if link_tag is not None else "")
            raw_date = item.findtext(atom+"published") or item.findtext(atom+"updated")
            try:
                published = datetime.fromisoformat(raw_date.replace("Z","+00:00")).astimezone(timezone.utc).isoformat(timespec="seconds")
            except (ValueError,TypeError,AttributeError):
                published = None
        else:
            title = normalize(item.findtext("title"))
            link = normalize(item.findtext("link"))
            published = parse_rcmp_date(item.findtext("pubDate"))
        if not link.startswith("https://rcmp.ca/") and not link.startswith("https://www.rcmp-grc.gc.ca/"):
            continue
        r = record(title, link, "Royal Canadian Mounted Police", published,
                   "rcmp_official_rss", "Police-reported financial crime",
                   date_basis="official_feed_publication")
        if r:
            accepted.append(r)
    return accepted, len(rows)

def fetch_gdelt(session, query):
    params = {
        "query": query, "mode": "artlist", "format": "json",
        "timespan": "3months", "maxrecords": 250, "sort": "datedesc",
    }
    response = session.get(GDELT_URL, params=params, timeout=50)
    response.raise_for_status()
    payload = response.json()
    articles = payload.get("articles", [])
    accepted = []
    for a in articles:
        title = normalize(a.get("title", ""))
        url = normalize(a.get("url", ""))
        if not url.startswith("https://"):
            continue
        # Canadian-publisher results, however publication geography is NOT incident geography.
        publisher = a.get("domain") or urlparse(url).netloc or "GDELT publisher"
        if not relevant(title,publisher) and not CRIME.search(title):
            continue
        dt = parse_gdelt_date(a.get("seendate"))
        item = record(title,url,publisher,dt,"gdelt_doc_2","Canadian publisher fraud coverage",
                      date_basis="gdelt_first_observed_not_event_date")
        if item:
            accepted.append(item)
    return accepted, len(articles)

def run():
    DATA.mkdir(parents=True, exist_ok=True)
    try:
        old = json.loads(FEED.read_text("utf-8")).get("leads", []) if FEED.exists() else []
    except (OSError, ValueError) as e:
        raise SystemExit("Refusing to modify unreadable prior history: " + str(e))
    saved = {r["id"]: r for r in old}
    gdelt_limited=False
    health = {"started_at": stamp(), "collectors": {}, "coverage_note":
              "RSS and GDELT coverage are neither exhaustive nor verified incident data."}
    with requests.Session() as session:
        session.headers.update(HEADERS)
        sources = [(name, (lambda url=url: fetch_rcmp(session,url))) for name,url in RCMP_URLS.items()]
        sources += [(name, (lambda query=q: fetch_gdelt(session, query))) for name,q in GDELT_QUERIES.items()]
        for name, fn in sources:
            if gdelt_limited and name not in RCMP_URLS:
                health["collectors"][name]={"status":"skipped_rate_limit","error":"GDELT requested backoff after HTTP 429"}
                continue
            try:
                entries, scanned = fn()
                for e in entries:
                    old_entry = saved.get(e["id"], {})
                    e["first_seen_at"] = old_entry.get("first_seen_at",e["first_seen_at"])
                    e["topics"] = sorted(set(e["topics"]+old_entry.get("topics",[])))
                    saved[e["id"]] = {**old_entry, **e}
                health["collectors"][name] = {"status":"ok" if scanned else "empty",
                                              "scanned":scanned,"accepted":len(entries)}
            except requests.HTTPError as exc:
                status_code=exc.response.status_code if exc.response is not None else 0
                if status_code==429 and name not in RCMP_URLS:
                    gdelt_limited=True
                health["collectors"][name] = {"status":"rate_limited" if status_code==429 else "failed","error":str(exc)[:300]}
            except Exception as exc:
                health["collectors"][name] = {"status":"failed","error":str(exc)[:300]}
            # GDELT recommends conservative request frequency; don't hammer its API.
            time.sleep(5.2 if name not in RCMP_URLS else .4)
    # Do not cap to 400; prior Google-only collector may cap on its own later.
    leads = sorted(saved.values(), key=lambda e:e.get("published_at") or "", reverse=True)
    FEED.write_text(json.dumps({"updated_at":stamp(),"leads":leads},
               ensure_ascii=False,indent=2)+"\n","utf-8")
    health["completed_at"] = stamp()
    health["record_count"] = len(leads)
    HEALTH.write_text(json.dumps(health,indent=2)+"\n","utf-8")
    print(json.dumps(health,indent=2))
    return 0 if leads else 1

if __name__ == "__main__":
    sys.exit(run())
