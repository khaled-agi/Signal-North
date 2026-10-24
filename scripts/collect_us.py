#!/usr/bin/env python3
"""U.S. public-source coverage for Signal North.

FinCEN/CFPB listings are official *records of actions*, not verified victim losses.
Google News RSS titles are unverified research leads. Never infer an incident
location or a firm's culpability from a headline or a publisher's home address.
All 50 states and D.C. are selectable; state queries rotate on each scan.
"""
from __future__ import annotations

import hashlib
import json
import re
import sys
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta, timezone
from email.utils import parsedate_to_datetime
from pathlib import Path
from urllib.parse import urlencode, urljoin, urlsplit
import requests
from bs4 import BeautifulSoup

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
STATES = json.loads((DATA / "us_states.json").read_text("utf-8"))["states"]
ACTIONS = DATA / "us_enforcement.json"
NEWS = DATA / "us_news.json"
STATUS = DATA / "us_status.json"
FINCEN = "https://www.fincen.gov/news/enforcement-actions"
CFPB = "https://www.consumerfinance.gov/enforcement/actions/"
HEADERS = {"User-Agent": "SignalNorthPublicResearch/0.2 (+https://github.com/khaled-agi/Signal-North)",
           "Accept": "text/html,application/rss+xml,application/xml"}
MIN_YEAR = 2020
SCAN_STATES = 8
MAX_NEWS = 5000

def now():
    return datetime.now(timezone.utc).isoformat(timespec="seconds")

def read(path, fallback):
    try:
        return json.loads(path.read_text("utf-8"))
    except (OSError, ValueError):
        return fallback

def write(path, document):
    path.write_text(json.dumps(document, ensure_ascii=False, indent=2) + "\n", "utf-8")

def text(node):
    return re.sub(r"\s+", " ", node.get_text(" ", strip=True) if hasattr(node, "get_text") else str(node or "")).strip()

def stable(source, url):
    return "us-" + hashlib.sha256((source+"|"+url).encode()).hexdigest()[:20]

def verified_link(href, expected):
    url = urljoin(expected, href or "")
    p = urlsplit(url)
    return url if p.scheme == "https" and p.hostname in expected else ""

def fetch(url, timeout=25):
    r = requests.get(url, headers=HEADERS, timeout=timeout)
    r.raise_for_status()
    return r.text

def parse_us_date(raw):
    raw = re.sub(r"\s+", " ", raw).strip()
    for pattern in ("%m/%d/%Y", "%b %d, %Y", "%B %d, %Y", "%Y-%m-%d"):
        try:
            return datetime.strptime(raw, pattern).date().isoformat()
        except ValueError:
            pass
    return None

def fincen_actions(html):
    soup = BeautifulSoup(html, "html.parser")
    records = []
    for row in soup.select("tr"):
        cols = row.find_all("td")
        if len(cols) < 3:
            continue
        anchor = cols[0].find("a", href=True)
        if not anchor:
            continue
        date = parse_us_date(text(cols[1]))
        if not date or int(date[:4]) < MIN_YEAR:
            continue
        url = verified_link(anchor["href"], FINCEN)
        if not url:
            continue
        name = text(anchor)
        if not name or len(name) < 8:
            continue
        matter = text(cols[2])
        sector = text(cols[3]) if len(cols) > 3 else "BSA-regulated entity"
        records.append({
            "id": stable("FinCEN", url), "source": "FinCEN", "source_url": url,
            "title": name, "institution": re.sub(r"^In the Matter of\s+", "", name, flags=re.I),
            "published_at": date, "case_number": matter, "sector": sector,
            "category": "BSA / AML enforcement", "evidence_level": "primary_regulator_index",
            "status": "FinCEN-listed enforcement action", "financial_measure": None,
            "geographic_scope": "federal", "state": None,
            "location_note": "No incident state inferred from institution identity or regulator address.",
            "summary": "FinCEN lists this Bank Secrecy Act enforcement action. Review the original notice for allegations, outcome, and monetary amounts."
        })
    return records

def cfpb_actions(html):
    """Conservative listing parser: include only exact original case links WITH displayed filing dates."""
    soup = BeautifulSoup(html, "html.parser")
    found = {}
    for anchor in soup.select('a[href*="/enforcement/actions/"]'):
        href = anchor.get("href", "")
        url = verified_link(href, CFPB)
        if not url or urlsplit(url).path.rstrip("/") == "/enforcement/actions":
            continue
        name = text(anchor)
        if len(name) < 6 or len(name) > 300:
            continue
        ancestor = anchor
        date = None
        snippet = ""
        for _ in range(5):
            ancestor = ancestor.parent
            if ancestor is None:
                break
            snippet = text(ancestor)[:950]
            match = re.search(r"Date filed:?\s*([A-Za-z]{3,9}\s+\d{1,2},?\s+\d{4})", snippet, re.I)
            if match:
                date = parse_us_date(match.group(1).replace(",", ", "))
                break
        if not date or int(date[:4]) < MIN_YEAR:
            continue
        found[url] = {
            "id": stable("CFPB", url), "source": "CFPB", "source_url": url,
            "title": name, "institution": name, "published_at": date,
            "case_number": None, "sector": "Consumer financial services",
            "category": "Consumer financial enforcement",
            "evidence_level": "primary_regulator_index",
            "status": "CFPB-listed case; outcome not inferred",
            "financial_measure": None, "geographic_scope": "federal", "state": None,
            "location_note": "Headquarter or court location does not establish an incident state.",
            "summary": "CFPB lists this federal consumer-financial-law matter. An enforcement listing does not by itself establish a final liability finding."
        }
    return list(found.values())

def headline_state(title):
    """State named in title only; never derive location from RSS search or publisher."""
    if re.search(r"\b(?:Washington,?\s*D\.?C\.?|District of Columbia|D\.C\.)\b", title, re.I):
        return "DC"
    for abbr, obj in sorted(STATES.items(), key=lambda pair: -len(pair[1]["name"])):
        if abbr == "DC":
            continue
        name = obj["name"]
        if abbr == "WA":
            expression = r"\bWashington\s+(?:state|State)\b"
        elif abbr == "GA":
            expression = r"\bGeorgia\s+(?:state|State)\b|\bAtlanta\b"
        else:
            expression = r"(?<!\w)" + re.escape(name) + r"(?!\w)"
        if re.search(expression, title, re.I):
            return abbr
    return None

def category(title):
    t=title.casefold()
    for words, value in [
        (("money laundering","bsa","anti-money laundering"),"AML / laundering"),
        (("bank impersonation","phishing","spoofed"),"Impersonation / phishing"),
        (("identity theft","account takeover"),"Identity / account compromise"),
        (("investment","crypto","securities"),"Investment / crypto"),
        (("romance","pig butchering"),"Relationship / investment"),
        (("wire fraud","payment diversion","business email"),"Payment / wire fraud"),
        (("ransomware","data breach"),"Cyber / data compromise"),
        (("scam","fraud","fraudulent"),"Fraud reporting")
    ]:
        if any(w in t for w in words): return value
    return "Financial-crime lead"

CRIME_WORDS = re.compile(r"\b(?:fraud|scam|launder(?:ing)?|phish(?:ing)?|identity theft|ransomware|wire fraud|embezzl|ponzi|impersonat|defraud|cybercrime|financial crime)\b", re.I)
US_WORDS = re.compile(r"\b(?:U\.?S\.?A?\.?|United States|American|FBI|DOJ|FinCEN|CFPB|FTC|SEC|federal prosecutors)\b", re.I)
FOREIGN_WORDS = re.compile(r"\b(?:Canada|Canadian|Australia|Britain|British|United Kingdom|India|Nigeria|Brazil|Argentina)\b", re.I)

def relevant(title, state):
    if not CRIME_WORDS.search(title):
        return False
    if state or US_WORDS.search(title):
        return True
    # Unknown geography may remain as a clearly marked discovery lead, but
    # avoid obvious foreign-only events in the nationwide U.S. feed.
    return not FOREIGN_WORDS.search(title)

def pubdate(raw):
    try:
        d = parsedate_to_datetime(raw)
        if d.tzinfo is None: d=d.replace(tzinfo=timezone.utc)
        return d.astimezone(timezone.utc).isoformat(timespec="seconds")
    except (ValueError, TypeError):
        return None

def parse_feed(xml, channel):
    root = ET.fromstring(xml)
    results = []
    for item in root.findall("./channel/item"):
        title = (item.findtext("title") or "").strip()
        url = (item.findtext("link") or "").strip()
        if not urlsplit(url).scheme == "https":
            continue
        source = item.find("source")
        publisher = (source.text or "").strip() if source is not None else "Syndicated news"
        # RSS often appends the outlet to title; strip that presentation suffix.
        clean_title = title.rsplit(" - "+publisher, 1)[0].strip() if publisher else title
        state = headline_state(clean_title)
        if not relevant(clean_title,state):
            continue
        published = pubdate(item.findtext("pubDate") or "")
        if not published:
            continue
        results.append({
            "id": stable("US-news", url), "title": clean_title, "publisher": publisher,
            "url": url, "published_at": published, "category": category(clean_title),
            "state": state, "state_reference": STATES[state]["name"] if state else None,
            "location_role": "State named in headline; map marker is a state-capital reference, not the incident location." if state else "Not geographically located by source headline.",
            "geographic_evidence": "headline_state_mention" if state else "geography_unresolved",
            "evidence_level": "unverified_syndicated_headline", "source_channel": channel,
            "review_status": "requires_original_source_review"
        })
    return results

def us_news_query(q):
    return "https://news.google.com/rss/search?" + urlencode({
        "q": q, "hl": "en-US", "gl": "US", "ceid": "US:en"
    })

def update():
    previous = read(STATUS,{})
    enforcement = read(ACTIONS, {"events":[]})
    headlines = read(NEWS, {"leads":[]})
    source_health = {}
    new = []

    for source, url, parser in (("FinCEN", FINCEN, fincen_actions), ("CFPB", CFPB, cfpb_actions)):
        try:
            items = parser(fetch(url))
            if not items:
                raise ValueError("No dated original-source records parsed; preserved previous snapshot")
            new.extend(items)
            source_health[source] = {"status":"ok", "scanned":len(items), "source_url":url}
        except Exception as exc:
            source_health[source] = {"status":"error", "error":str(exc)[:180], "source_url":url}

    # Keep past official notices when upstream pages paginate or temporarily fail.
    unique = {r["id"]:r for r in enforcement.get("events",[])}
    for record in new:
        unique[record["id"]] = record
    events = sorted(unique.values(), key=lambda x:x.get("published_at") or "", reverse=True)
    write(ACTIONS, {"updated_at":now(), "country":"US",
                    "source_scope":"Official federal enforcement action indexes only; NOT all U.S. regulators.",
                    "events":events})

    codes = list(STATES)
    start = int(previous.get("next_state_offset",0)) % len(codes)
    chosen = [codes[(start+i)%len(codes)] for i in range(SCAN_STATES)]
    queries = [
        ("National fraud", '"US" "bank fraud" OR "wire fraud" when:30d'),
        ("Federal investigations", '"FBI" "financial fraud" OR "scam" when:30d'),
        ("US consumer scams", '"FTC" "scam" OR "fraud" when:30d'),
    ]
    queries.extend((STATES[code]["name"], '"'+STATES[code]["name"]+'" fraud OR scam OR "money laundering" when:30d') for code in chosen)
    gathered = {}
    failures = 0
    for label, query in queries:
        try:
            for lead in parse_feed(fetch(us_news_query(query)),label):
                gathered[lead["id"]] = lead
        except (requests.RequestException, ET.ParseError, ValueError) as exc:
            failures += 1
            source_health["Google News RSS "+label] = {"status":"error","error":str(exc)[:140]}
    merged = {r["id"]:r for r in headlines.get("leads",[]) if r.get("id")}
    merged.update(gathered)
    # Only keep recent, de-duplicated discovery leads. Older source records
    # remain in the published national enforcement dataset.
    earliest = (datetime.now(timezone.utc)-timedelta(days=365)).isoformat()
    output = sorted((r for r in merged.values() if (r.get("published_at") or "")>=earliest),
                    key=lambda r:r["published_at"], reverse=True)[:MAX_NEWS]
    write(NEWS, {"updated_at":now(),"country":"US","leads":output,
                 "methodology":"Syndicated titles are unverified leads. State assignment only when literally named in headline; coordinates used only for reference markers."})
    scanned = dict(previous.get("states_last_scanned") or {})
    for state in chosen:
        scanned[state] = now()
    status = {
        "updated_at":now(), "country":"US", "enforcement_records":len(events),
        "unverified_news_leads":len(output), "new_leads_this_scan":len(gathered),
        "state_directory_count":len(codes), "states_scanned_this_run":chosen,
        "states_ever_scanned":len(scanned), "states_last_scanned":scanned,
        "next_state_offset":(start+SCAN_STATES)%len(codes),
        "source_health":source_health, "failed_rss_queries":failures,
        "source_limits":"No US state-by-state fraud incidence, local arrest coverage, or nationwide victim-loss totals inferred."
    }
    write(STATUS,status)
    print(json.dumps({key:status[key] for key in ("enforcement_records","unverified_news_leads","states_ever_scanned","failed_rss_queries")}))
    # Exit non-zero only when all primary sources fail and there is no usable
    # previously published source data, so deployment never wipes past records.
    if not events and all(source_health[s]["status"]!="ok" for s in ("FinCEN","CFPB")):
        raise RuntimeError("No confirmed U.S. enforcement source data available")

if __name__=="__main__":
    try: update()
    except Exception as e:
        print("US collection warning:", e, file=sys.stderr)
        sys.exit(1)
