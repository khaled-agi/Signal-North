#!/usr/bin/env python3
"""Gather new primary-source U.S. regulator publications, not final orders.

- Fed: enforcement-actions RSS
- OCC: news releases RSS (enforcement headlines only)
- NCUA: official press releases page (enforcement or closures only)
No attempt to infer affected bank names or treat news as proven misconduct.
"""
import hashlib
import json
import os
import re
import tempfile
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from pathlib import Path
from urllib.parse import urljoin, urlparse
import feedparser
import requests
from bs4 import BeautifulSoup

FEEDS={
 "federal_reserve_enforcement": {
   "url":"https://www.federalreserve.gov/feeds/press_enforcement.xml",
   "agency":"Federal Reserve","allowed":"federalreserve.gov","kind":"enforcement_publication",
 },
 "occ_news": {
   "url":"https://www.occ.gov/rss/occ_news.xml",
   "agency":"OCC","allowed":"occ.gov","kind":"enforcement_publication",
 },
 "ncua_press": {
   "url":"https://ncua.gov/news/press-releases",
   "agency":"NCUA","allowed":"ncua.gov","kind":"regulator_news",
 },
}
OUTPUT=Path("data/us_regulatory_signal_publications.json")
KEYWORDS=re.compile(r"enforcement|sanction|consent order|civil money penal|prohibit|cease.and.desist|closes|closure|conservator|liquidat",re.I)

def host_safe(url,domain):
 parsed=urlparse(url)
 host=parsed.hostname or ""
 return parsed.scheme=="https" and (host==domain or host.endswith("."+domain))

def from_feed(xml,source):
 feed=feedparser.parse(xml)
 records={}
 for e in feed.entries:
  title=" ".join(str(e.get("title") or "").split())
  url=str(e.get("link") or "").strip()
  if url.startswith("http://"):url="https://"+url[7:]
  if not host_safe(url,source["allowed"]):continue
  if source["agency"]=="OCC" and not KEYWORDS.search(title):continue
  if not title:continue
  try:date=parsedate_to_datetime(str(e.get("published") or e.get("updated"))).date().isoformat()
  except (ValueError,TypeError):date=None
  key=hashlib.sha256((source["agency"]+"|"+url).encode()).hexdigest()[:22]
  records[key]={"id":key,"agency":source["agency"],"jurisdiction":"US","title":title[:320],
    "url":url,"publication_date":date,"signal_type":source["kind"],
    "evidence_status":"official_publication_unreviewed",
    "scope_note":"An agency press release is not necessarily a final enforcement order; original documents must be reviewed."}
 if not records:
  raise ValueError("Official RSS contained no relevant entries")
 return list(records.values())

def from_ncua(html,source):
 soup=BeautifulSoup(html,"html.parser")
 out={}
 for a in soup.select("a[href]"):
  href=urljoin(source["url"],a["href"]).split("#")[0]
  if not host_safe(href,"ncua.gov") or not re.search(r"/newsroom/press-release/",href):continue
  title=" ".join(a.get_text(" ",strip=True).split())
  if not KEYWORDS.search(title) or len(title)<15:continue
  key=hashlib.sha256(("NCUA|"+href).encode()).hexdigest()[:22]
  out[key]={"id":key,"agency":"NCUA","jurisdiction":"US","title":title[:320],
     "url":href,"publication_date":None,
     "signal_type":"regulator_publication_enforcement_or_closure",
     "evidence_status":"official_publication_unreviewed",
     "scope_note":"Enforcement press releases can name individuals. A credit-union closure is a lifecycle event, not evidence of financial crime."}
 if not out:
  raise ValueError("No relevant NCUA official press release links found")
 return list(out.values())

def atomic(path,value):
 path.parent.mkdir(parents=True,exist_ok=True)
 with tempfile.NamedTemporaryFile("w",dir=path.parent,encoding="utf-8",delete=False) as f:
  json.dump(value,f,ensure_ascii=False,separators=(",",":"))
  stage=f.name
 os.replace(stage,path)

def main():
 prev={"records":[],"source_health":{}}
 if OUTPUT.exists():
  try:prev=json.loads(OUTPUT.read_text("utf-8"))
  except (ValueError,OSError):pass
 health=dict(prev.get("source_health",{}))
 records={x["id"]:x for x in prev.get("records",[])}
 now=datetime.now(timezone.utc).isoformat(timespec="seconds")
 session=requests.Session()
 session.headers.update({"User-Agent":"SignalNorthPublicResearch/1.0 (official regulator public RSS)"})
 for key,source in FEEDS.items():
  existing=health.get(key,{})
  if existing.get("status")=="success" and existing.get("last_success","")[:10]==now[:10] and os.getenv("SIGNALNORTH_FORCE_US_SIGNALS")!="1":
   continue
  try:
   r=session.get(source["url"],timeout=35);r.raise_for_status()
   if len(r.content)>3_000_000:raise ValueError("Unexpectedly large regulator source")
   additions=from_ncua(r.text,source) if key=="ncua_press" else from_feed(r.content,source)
   for item in additions:records[item["id"]]=item
   health[key]={"status":"success","last_success":now,"latest_items":len(additions),"source_url":source["url"]}
   print(key,len(additions),"official publication leads",flush=True)
  except Exception as exc:
   health[key]={"status":"failed_last_good_preserved" if any(x["agency"]==source["agency"] for x in records.values()) else "unavailable",
                "last_attempt":now,"error_type":type(exc).__name__,"source_url":source["url"]}
   print(key,"FAILED",type(exc).__name__,str(exc)[:100],flush=True)
 result={"generated_at":now,"records":sorted(records.values(),key=lambda x:x.get("publication_date") or "",reverse=True)[:3000],
         "source_health":health,
         "unit":"official_regulator_publication_not_adjudicated_action",
         "methodology":"Official agency headlines with links, not a validated legal finding or named-bank enforcement decision. Retains original source URL and prior records."}
 atomic(OUTPUT,result)

if __name__=="__main__":main()
