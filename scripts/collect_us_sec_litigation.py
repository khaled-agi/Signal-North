#!/usr/bin/env python3
"""Collect SEC litigation-release publication leads from primary SEC sources.

This feed includes allegations, judgments and other court developments; one
release is not a proven regulatory violation or necessarily a financial firm.
Source health records a blocked SEC feed rather than counting zero cases.
"""
from __future__ import annotations
import hashlib
import json
import os
import re
import tempfile
from datetime import datetime, timezone
from urllib.parse import urljoin,urlparse
from pathlib import Path
from bs4 import BeautifulSoup
import feedparser
import requests

RSS="https://www.sec.gov/enforcement-litigation/litigation-releases/rss"
HTML="https://www.sec.gov/enforcement-litigation/litigation-releases"
OUT=Path("data/us_sec_litigation_releases.json")
HEALTH=Path("data/us_sec_source_health.json")

def safe_url(url):
 p=urlparse(url)
 return p.scheme=="https" and (p.hostname=="sec.gov" or (p.hostname or "").endswith(".sec.gov"))

def item(title,url,date=None,release=None):
 if not safe_url(url) or len(title.strip())<4:return None
 key=hashlib.sha256(url.encode()).hexdigest()[:22]
 return {"id":key,"agency":"SEC","jurisdiction":"US",
         "title":" ".join(title.split())[:350],"url":url,
         "publication_date":date,"release_number":release,
         "source_kind":"SEC_official_litigation_release",
         "legal_status":"court_litigation_publication_unreviewed",
         "note":"A litigation release can report allegations, procedural developments or final judgments. Read the document before attributing wrongdoing.",
         }

def from_rss(data):
 feed=feedparser.parse(data)
 out={}
 for entry in feed.entries:
  url=str(entry.get("link") or "").strip()
  title=str(entry.get("title") or "")
  stamp=entry.get("published_parsed") or entry.get("updated_parsed")
  date=f"{stamp.tm_year:04d}-{stamp.tm_mon:02d}-{stamp.tm_mday:02d}" if stamp else None
  r=item(title,url,date)
  if r:out[r["id"]]=r
 if not out:raise ValueError("SEC RSS returned no original-source litigation releases")
 return list(out.values())

def from_html(html):
 soup=BeautifulSoup(html,"html.parser")
 out={}
 for anchor in soup.select("a[href]"):
  url=urljoin(HTML,anchor.get("href","")).split("#")[0]
  if not safe_url(url):continue
  if not re.search(r"/(?:litigation|enforcement-litigation)/(?:litreleases|litigation-releases|lr[\d-])",url,re.I):
   continue
  title=" ".join(anchor.get_text(" ",strip=True).split())
  r=item(title,url)
  if r:out[r["id"]]=r
 if not out:raise ValueError("SEC HTML didn't include identifiable litigation releases")
 return list(out.values())

def atomic(path,obj):
 path.parent.mkdir(parents=True,exist_ok=True)
 with tempfile.NamedTemporaryFile("w",dir=path.parent,encoding="utf-8",delete=False) as f:
  json.dump(obj,f,ensure_ascii=False,separators=(",",":"))
  tmp=f.name
 os.replace(tmp,path)

def main():
 now=datetime.now(timezone.utc).isoformat(timespec="seconds")
 old={"records":[]}
 if OUT.exists():
  try:old=json.loads(OUT.read_text("utf-8"))
  except (OSError,ValueError):pass
 records={r["id"]:r for r in old.get("records",[])}
 status={"checked_at":now,"rss_source":RSS,"fallback_page":HTML}
 session=requests.Session()
 session.headers.update({"User-Agent":"SignalNorthResearch public-source-monitor/1.0 contact https://github.com/khaled-agi/Signal-North","Accept":"application/rss+xml,application/xml,text/html"})
 try:
  try:
   response=session.get(RSS,timeout=40);response.raise_for_status()
   results=from_rss(response.content)
   method="rss"
  except Exception:
   fallback=session.get(HTML,timeout=40);fallback.raise_for_status()
   results=from_html(fallback.text)
   method="html"
  for r in results:records[r["id"]]=r
  if len(records)<3:raise ValueError("SEC release feed below minimum")
  atomic(OUT,{"source":"SEC official litigation releases",
              "source_url":RSS,"retrieved_at":now,
              "record_count":len(records),"collection_method":method,
              "records":list(records.values())[:2500],
              "methodology":"Only SEC original publication links; publication is not a final enforcement finding and cannot be automatically attributed to a named financial firm."})
  status.update({"status":"success","last_success":now,"record_count":len(records),"collection_method":method})
  print(f"SEC litigation: {len(records)} official releases ({method})",flush=True)
 except Exception as e:
  status.update({"status":"failed_last_good_preserved" if OUT.exists() else "unavailable","error_type":type(e).__name__,"detail":str(e)[:180]})
  print(f"SEC litigation collector failed: {type(e).__name__}",flush=True)
 atomic(HEALTH,status)

if __name__=="__main__":main()
